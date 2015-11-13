__FILENAME__ = add_blips
#!/usr/bin/env python
# encoding: utf=8
#
# by Douglas Repetto, 10 June 2009
# plus code from various other examples and fixes by remix devs

"""
add_blips.py

Add a blip to any combination of each tatum/beat/bar in a song.

"""
import sys
import os.path
import numpy

import echonest.remix.audio as audio

usage="""
Usage:
python add_blips.py <inputfilename><outputfilename> [tatums] [beats] [bars]

where 
    tatums == add blips to tatums
    beats == add blips to beats (default)
    bars == add blips to bars

Example:
python add_blips.py bootsy.mp3 bootsy_blips.mp3 beats bars

"""

blip_filenames = ('sounds/blip_low.wav', 'sounds/blip_med.wav', 'sounds/blip_high.wav')

#the blip.wav files are stored in the sounds/ directory relative to the 
#script. if the script is run from another directory those sounds won't
#be found. this fixes that problem.
prefix = os.path.dirname(os.path.abspath(sys.argv[0]))
blip_filenames = map(lambda x: os.path.join(prefix, x), blip_filenames)

def main(input_filename, output_filename, tatums, beats, bars):

    audiofile = audio.LocalAudioFile(input_filename)
    num_channels = audiofile.numChannels
    sample_rate = audiofile.sampleRate
    
    # mono files have a shape of (len,) 
    out_shape = list(audiofile.data.shape)
    out_shape[0] = len(audiofile)
    out = audio.AudioData(shape=out_shape, sampleRate=sample_rate,numChannels=num_channels)

    # same hack to change shape: we want blip_files[0] as a short, silent blip
    null_shape = list(audiofile.data.shape)
    null_shape[0] = 2
    null_audio = audio.AudioData(shape=null_shape)
    null_audio.endindex = len(null_audio)
    
    low_blip = audio.AudioData(blip_filenames[0])
    med_blip = audio.AudioData(blip_filenames[1])
    high_blip = audio.AudioData(blip_filenames[2])
    
    all_tatums = audiofile.analysis.tatums
    all_beats = audiofile.analysis.beats
    all_bars = audiofile.analysis.bars
            
    if not all_tatums:
        print "Didn't find any tatums in this analysis!"
        print "No output."
        sys.exit(-1)
    
    print "going to add blips..."
    
    for tatum in all_tatums:
        mix_list = [audiofile[tatum], null_audio, null_audio, null_audio]
        if tatums:
            print "match! tatum start time:" + str(tatum.start)
            mix_list[1] = low_blip

        if beats:
            for beat in all_beats:
                if beat.start == tatum.start:
                    print "match! beat start time: " + str(beat.start)
                    mix_list[2] = med_blip
                    break

        if bars:
            for bar in all_bars:
                if bar.start == tatum.start:
                    print "match! bar start time: " + str(bar.start)
                    mix_list[3] = high_blip
                    break
        out_data = audio.megamix(mix_list)
        out.append(out_data)
        del(out_data)
    print "blips added, going to encode", output_filename, "..."
    out.encode(output_filename)
    print "Finito, Benito!"


if __name__=='__main__':
    tatums = False
    beats = False
    bars = False
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
        if len(sys.argv) == 3:
            bars = 1
            print "blipping bars by default."
        for arg in sys.argv[3:len(sys.argv)]:
            if arg == "tatums":
                tatums = True
                print "blipping tatums."
            if arg == "beats":
                beats = True
                print "blipping beats."
            if arg == "bars":
                bars = True
                print "blipping bars."
    except:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename, tatums, beats, bars)

########NEW FILE########
__FILENAME__ = afromb
#!/usr/bin/env python
# encoding: utf=8

"""
afromb.py

Re-synthesize song A using the segments of song B.

By Ben Lacker, 2009-02-24.
"""
import numpy
import sys
import time
import echonest.remix.audio as audio

usage="""
Usage:
    python afromb.py <inputfilenameA> <inputfilenameB> <outputfilename> <Mix> [env]

Example:
    python afromb.py BillieJean.mp3 CryMeARiver.mp3 BillieJeanFromCryMeARiver.mp3 0.9 env

The 'env' flag applies the volume envelopes of the segments of A to those
from B.

Mix is a number 0-1 that determines the relative mix of the resynthesized
song and the original input A. i.e. a mix value of 0.9 yields an output that
is mostly the resynthesized version.

"""

class AfromB(object):
    def __init__(self, input_filename_a, input_filename_b, output_filename):
        self.input_a = audio.LocalAudioFile(input_filename_a)
        self.input_b = audio.LocalAudioFile(input_filename_b)
        self.segs_a = self.input_a.analysis.segments
        self.segs_b = self.input_b.analysis.segments
        self.output_filename = output_filename

    def calculate_distances(self, a):
        distance_matrix = numpy.zeros((len(self.segs_b), 4),
                                        dtype=numpy.float32)
        pitch_distances = []
        timbre_distances = []
        loudmax_distances = []
        for b in self.segs_b:
            pitch_diff = numpy.subtract(b.pitches,a.pitches)
            pitch_distances.append(numpy.sum(numpy.square(pitch_diff)))
            timbre_diff = numpy.subtract(b.timbre,a.timbre)
            timbre_distances.append(numpy.sum(numpy.square(timbre_diff)))
            loudmax_diff = b.loudness_begin - a.loudness_begin
            loudmax_distances.append(numpy.square(loudmax_diff))
        distance_matrix[:,0] = pitch_distances
        distance_matrix[:,1] = timbre_distances
        distance_matrix[:,2] = loudmax_distances
        distance_matrix[:,3] = range(len(self.segs_b))
        distance_matrix = self.normalize_distance_matrix(distance_matrix)
        return distance_matrix

    def normalize_distance_matrix(self, mat, mode='minmed'):
        """ Normalize a distance matrix on a per column basis.
        """
        if mode == 'minstd':
            mini = numpy.min(mat,0)
            m = numpy.subtract(mat, mini)
            std = numpy.std(mat,0)
            m = numpy.divide(m, std)
            m = numpy.divide(m, mat.shape[1])
        elif mode == 'minmed':
            mini = numpy.min(mat,0)
            m = numpy.subtract(mat, mini)
            med = numpy.median(m)
            m = numpy.divide(m, med)
            m = numpy.divide(m, mat.shape[1])
        elif mode == 'std':
            std = numpy.std(mat,0)
            m = numpy.divide(mat, std)
            m = numpy.divide(m, mat.shape[1])
        return m

    def run(self, mix=0.5, envelope=False):
        dur = len(self.input_a.data) + 100000 # another two seconds
        # determine shape of new array
        if len(self.input_a.data.shape) > 1:
            new_shape = (dur, self.input_a.data.shape[1])
            new_channels = self.input_a.data.shape[1]
        else:
            new_shape = (dur,)
            new_channels = 1
        out = audio.AudioData(shape=new_shape,
                            sampleRate=self.input_b.sampleRate,
                            numChannels=new_channels)
        for a in self.segs_a:
            seg_index = a.absolute_context()[0]
            # find best match from segs in B
            distance_matrix = self.calculate_distances(a)
            distances = [numpy.sqrt(x[0]+x[1]+x[2]) for x in distance_matrix]
            match = self.segs_b[distances.index(min(distances))]
            segment_data = self.input_b[match]
            reference_data = self.input_a[a]
            if segment_data.endindex < reference_data.endindex:
                if new_channels > 1:
                    silence_shape = (reference_data.endindex,new_channels)
                else:
                    silence_shape = (reference_data.endindex,)
                new_segment = audio.AudioData(shape=silence_shape,
                                        sampleRate=out.sampleRate,
                                        numChannels=segment_data.numChannels)
                new_segment.append(segment_data)
                new_segment.endindex = len(new_segment)
                segment_data = new_segment
            elif segment_data.endindex > reference_data.endindex:
                index = slice(0, int(reference_data.endindex), 1)
                segment_data = audio.AudioData(None,segment_data.data[index],
                                        sampleRate=segment_data.sampleRate)
            if envelope:
                # db -> voltage ratio http://www.mogami.com/e/cad/db.html
                linear_max_volume = pow(10.0,a.loudness_max/20.0)
                linear_start_volume = pow(10.0,a.loudness_begin/20.0)
                if(seg_index == len(self.segs_a)-1): # if this is the last segment
                    linear_next_start_volume = 0
                else:
                    linear_next_start_volume = pow(10.0,self.segs_a[seg_index+1].loudness_begin/20.0)
                    pass
                when_max_volume = a.time_loudness_max
                # Count # of ticks I wait doing volume ramp so I can fix up rounding errors later.
                ss = 0
                # Set volume of this segment. Start at the start volume, ramp up to the max volume , then ramp back down to the next start volume.
                cur_vol = float(linear_start_volume)
                # Do the ramp up to max from start
                samps_to_max_loudness_from_here = int(segment_data.sampleRate * when_max_volume)
                if(samps_to_max_loudness_from_here > 0):
                    how_much_volume_to_increase_per_samp = float(linear_max_volume - linear_start_volume)/float(samps_to_max_loudness_from_here)
                    for samps in xrange(samps_to_max_loudness_from_here):
                        try:
                            segment_data.data[ss] *= cur_vol
                        except IndexError:
                            pass
                        cur_vol = cur_vol + how_much_volume_to_increase_per_samp
                        ss = ss + 1
                # Now ramp down from max to start of next seg
                samps_to_next_segment_from_here = int(segment_data.sampleRate * (a.duration-when_max_volume))
                if(samps_to_next_segment_from_here > 0):
                    how_much_volume_to_decrease_per_samp = float(linear_max_volume - linear_next_start_volume)/float(samps_to_next_segment_from_here)
                    for samps in xrange(samps_to_next_segment_from_here):
                        cur_vol = cur_vol - how_much_volume_to_decrease_per_samp
                        try:
                            segment_data.data[ss] *= cur_vol
                        except IndexError:
                            pass
                        ss = ss + 1
            mixed_data = audio.mix(segment_data,reference_data,mix=mix)
            out.append(mixed_data)
        out.encode(self.output_filename)

def main():
    try:
        input_filename_a = sys.argv[1]
        input_filename_b = sys.argv[2]
        output_filename = sys.argv[3]
        mix = sys.argv[4]
        if len(sys.argv) == 6:
            env = True
        else:
            env = False
    except:
        print usage
        sys.exit(-1)
    AfromB(input_filename_a, input_filename_b, output_filename).run(mix=mix,
                                                                envelope=env)

if __name__=='__main__':
    tic = time.time()
    main()
    toc = time.time()
    print "Elapsed time: %.3f sec" % float(toc-tic)

########NEW FILE########
__FILENAME__ = capsule
#!/usr/bin/env python
# encoding: utf=8

"""
capsule.py

accepts songs on the commandline, order them, beatmatch them, and output an audio file

Created by Tristan Jehan and Jason Sundram.
"""

import os
import sys
from optparse import OptionParser

from echonest.remix.action import render, make_stereo
from echonest.remix.audio import LocalAudioFile
from pyechonest import util

from capsule_support import order_tracks, equalize_tracks, resample_features, timbre_whiten, initialize, make_transition, terminate, FADE_OUT, display_actions, is_valid


def tuples(l, n=2):
    """ returns n-tuples from l.
        e.g. tuples(range(4), n=2) -> [(0, 1), (1, 2), (2, 3)]
    """
    return zip(*[l[i:] for i in range(n)])

def do_work(audio_files, options):

    inter = float(options.inter)
    trans = float(options.transition)
    order = bool(options.order)
    equal = bool(options.equalize)
    verbose = bool(options.verbose)
    
    # Get pyechonest/remix objects
    analyze = lambda x : LocalAudioFile(x, verbose=verbose, sampleRate = 44100, numChannels = 2)
    tracks = map(analyze, audio_files)
    
    # decide on an initial order for those tracks
    if order == True:
        if verbose: print "Ordering tracks..."
        tracks = order_tracks(tracks)
    
    if equal == True:
        equalize_tracks(tracks)
        if verbose:
            print
            for track in tracks:
                print "Vol = %.0f%%\t%s" % (track.gain*100.0, track.filename)
            print
    
    valid = []
    # compute resampled and normalized matrices
    for track in tracks: 
        if verbose: print "Resampling features for", track.filename
        track.resampled = resample_features(track, rate='beats')
        track.resampled['matrix'] = timbre_whiten(track.resampled['matrix'])
        # remove tracks that are too small
        if is_valid(track, inter, trans):
            valid.append(track)
        # for compatibility, we make mono tracks stereo
        track = make_stereo(track)
    tracks = valid
    
    if len(tracks) < 1: return []
    # Initial transition. Should contain 2 instructions: fadein, and playback.
    if verbose: print "Computing transitions..."
    start = initialize(tracks[0], inter, trans)
    
    # Middle transitions. Should each contain 2 instructions: crossmatch, playback.
    middle = []
    [middle.extend(make_transition(t1, t2, inter, trans)) for (t1, t2) in tuples(tracks)]
    
    # Last chunk. Should contain 1 instruction: fadeout.
    end = terminate(tracks[-1], FADE_OUT)
    
    return start + middle + end

def get_options(warn=False):
    usage = "usage: %s [options] <list of mp3s>" % sys.argv[0]
    parser = OptionParser(usage=usage)
    parser.add_option("-t", "--transition", default=8, help="transition (in seconds) default=8")
    parser.add_option("-i", "--inter", default=8, help="section that's not transitioning (in seconds) default=8")
    parser.add_option("-o", "--order", action="store_true", help="automatically order tracks")
    parser.add_option("-e", "--equalize", action="store_true", help="automatically adjust volumes")
    parser.add_option("-v", "--verbose", action="store_true", help="show results on screen")        
    parser.add_option("-p", "--pdb", default=True, help="dummy; here for not crashing when using nose")
    
    (options, args) = parser.parse_args()
    if warn and len(args) < 2: 
        parser.print_help()
    return (options, args)
    
def main():
    options, args = get_options(warn=True);
    actions = do_work(args, options)
    verbose = bool(options.verbose)
    
    if verbose:
        display_actions(actions)
        print "Output Duration = %.3f sec" % sum(act.duration for act in actions)
    
        print "Rendering..."
    # Send to renderer
    render(actions, 'capsule.mp3', verbose)
    return 1
    
if __name__ == "__main__":
    main()
    # for profiling, do this:
    #import cProfile
    #cProfile.run('main()', 'capsule_prof')
    # then in ipython:
    #import pstats
    #p = pstats.Stats('capsule_prof')
    #p.sort_stats('cumulative').print_stats(30)

########NEW FILE########
__FILENAME__ = capsule_support
#!/usr/bin/env python
# encoding: utf=8

"""
capsule_support.py

Created by Tristan Jehan and Jason Sundram.
"""

import numpy as np
from copy import deepcopy
from echonest.remix.action import Crossfade, Playback, Crossmatch, Fadein, Fadeout, humanize_time
from utils import rows, flatten

# constants for now
X_FADE = 3
FADE_IN = 0.25
FADE_OUT = 6
MIN_SEARCH = 4
MIN_MARKERS = 2
MIN_ALIGN_DURATION = 3
LOUDNESS_THRESH = -8
FUSION_INTERVAL = .06   # this is what we use in the analyzer
AVG_PEAK_OFFSET = 0.025 # Estimated time between onset and peak of segment.

# TODO: this should probably be in actions?
def display_actions(actions):
    total = 0
    print
    for a in actions:
        print "%s\t  %s" % (humanize_time(total), unicode(a))
        total += a.duration
    print

def evaluate_distance(mat1, mat2):
    return np.linalg.norm(mat1.flatten() - mat2.flatten())

def upsample_matrix(m):
    """ Upsample matrices by a factor of 2."""
    r, c = m.shape
    out = np.zeros((2*r, c), dtype=np.float32)
    for i in xrange(r):
        out[i*2  , :] = m[i, :]
        out[i*2+1, :] = m[i, :]
    return out

def upsample_list(l, rate=2):
    """ Upsample lists by a factor of 2."""
    if rate != 2: return l[:]
    # Assume we're an AudioQuantumList.
    def split(x):
        a = deepcopy(x)
        a.duration = x.duration / 2
        b = deepcopy(a)
        b.start = x.start + a.duration
        return a, b
    
    return flatten(map(split, l))

def average_duration(l):
    return sum([i.duration for i in l]) / float(len(l))

def align(track1, track2, mat1, mat2):
    """ Constrained search between a settled section and a new section.
        Outputs location in mat2 and the number of rows used in the transition.
    """
    # Get the average marker duration.
    marker1 = average_duration(getattr(track1.analysis, track1.resampled['rate'])[track1.resampled['index']:track1.resampled['index']+rows(mat1)])
    marker2 = average_duration(getattr(track2.analysis, track2.resampled['rate'])[track2.resampled['index']:track2.resampled['index']+rows(mat2)])

    def get_adjustment(tr1, tr2):
        """Update tatum rate if necessary"""
        dist = np.log2(tr1 / tr2)
        if  dist < -0.5: return (1, 2)
        elif dist > 0.5: return (2, 1)
        else:            return (1, 1)
    
    rate1, rate2 = get_adjustment(marker1, marker2)
    if rate1 == 2: mat1 = upsample_matrix(mat1)
    if rate2 == 2: mat2 = upsample_matrix(mat2)
    
    # Update sizes.
    rows2 = rows(mat2)
    rows1 = min( rows(mat1), max(rows2 - MIN_SEARCH, MIN_MARKERS)) # at least the best of MIN_SEARCH choices
    
    # Search for minimum.
    def dist(i):
        return evaluate_distance(mat1[0:rows1,:], mat2[i:i+rows1,:])
    
    min_loc = min(xrange(rows2 - rows1), key=dist)
    min_val = dist(min_loc)
    
    # Let's make sure track2 ends its transition on a regular tatum.
    if rate2 == 2 and (min_loc + rows1) & 1: 
        rows1 -= 1
    
    return min_loc, rows1, rate1, rate2

def equalize_tracks(tracks):
    
    def db_2_volume(loudness):
        return (1.0 - LOUDNESS_THRESH * (LOUDNESS_THRESH - loudness) / 100.0)
    
    for track in tracks:
        loudness = track.analysis.loudness
        track.gain = db_2_volume(loudness)
    
def order_tracks(tracks):
    """ Finds the smoothest ordering between tracks, based on tempo only."""
    tempos = [track.analysis.tempo['value'] for track in tracks]
    median = np.median(tempos)
    def fold(t):
        q = np.log2(t / median)
        if  q < -.5: return t * 2.0
        elif q > .5: return t / 2.0
        else:        return t
        
    new_tempos = map(fold, tempos)
    order = np.argsort(new_tempos)
    return [tracks[i] for i in order]

def is_valid(track, inter, transition):
    markers = getattr(track.analysis, track.resampled['rate'])
    if len(markers) < 1:
        dur = track.duration
    else:
        dur = markers[-1].start + markers[-1].duration - markers[0].start
    return inter + 2 * transition < dur

def get_central(analysis, member='segments'):
    """ Returns a tuple: 
        1) copy of the members (e.g. segments) between end_of_fade_in and start_of_fade_out.
        2) the index of the first retained member.
    """
    def central(s):
        return analysis.end_of_fade_in <= s.start and (s.start + s.duration) < analysis.start_of_fade_out
    
    members = getattr(analysis, member) # this is nicer than data.__dict__[member]
    ret = filter(central, members[:]) 
    index = members.index(ret[0]) if ret else 0
    
    return ret, index

def get_mean_offset(segments, markers):
    if segments == markers:
        return 0
    
    index = 0
    offsets = []
    try:
        for marker in markers:
            while segments[index].start < marker.start + FUSION_INTERVAL:
                offset = abs(marker.start - segments[index].start)
                if offset < FUSION_INTERVAL:
                    offsets.append(offset)
                index += 1
    except IndexError, e:
        pass
    
    return np.average(offsets) if offsets else AVG_PEAK_OFFSET
    
def resample_features(data, rate='tatums', feature='timbre'):
    """
    Resample segment features to a given rate within fade boundaries.
    @param data: analysis object.
    @param rate: one of the following: segments, tatums, beats, bars.
    @param feature: either timbre or pitch.
    @return A dictionary including a numpy matrix of size len(rate) x 12, a rate, and an index
    """
    ret = {'rate': rate, 'index': 0, 'cursor': 0, 'matrix': np.zeros((1, 12), dtype=np.float32)}
    segments, ind = get_central(data.analysis, 'segments')
    markers, ret['index'] = get_central(data.analysis, rate)

    if len(segments) < 2 or len(markers) < 2:
        return ret
        
    # Find the optimal attack offset
    meanOffset = get_mean_offset(segments, markers)
    tmp_markers = deepcopy(markers)
    
    # Apply the offset
    for m in tmp_markers:
        m.start -= meanOffset
        if m.start < 0: m.start = 0
    
    # Allocate output matrix, give it alias mat for convenience.
    mat = ret['matrix'] = np.zeros((len(tmp_markers)-1, 12), dtype=np.float32)
    
    # Find the index of the segment that corresponds to the first marker
    f = lambda x: tmp_markers[0].start < x.start + x.duration
    index = (i for i,x in enumerate(segments) if f(x)).next()
    
    # Do the resampling
    try:
        for (i, m) in enumerate(tmp_markers):
            while segments[index].start + segments[index].duration < m.start + m.duration:
                dur = segments[index].duration
                if segments[index].start < m.start:
                    dur -= m.start - segments[index].start
                
                C = min(dur / m.duration, 1)
                
                mat[i, 0:12] += C * np.array(getattr(segments[index], feature))
                index += 1
                
            C = min( (m.duration + m.start - segments[index].start) / m.duration, 1)
            mat[i, 0:12] += C * np.array(getattr(segments[index], feature))
    except IndexError, e:
        pass # avoid breaking with index > len(segments)
        
    return ret

def column_whiten(mat):
    """ Zero mean, unit variance on a column basis"""
    m = mat - np.mean(mat,0)
    return m / np.std(m,0)

def timbre_whiten(mat):
    if rows(mat) < 2: return mat
    m = np.zeros((rows(mat), 12), dtype=np.float32)
    m[:,0] = mat[:,0] - np.mean(mat[:,0],0)
    m[:,0] = m[:,0] / np.std(m[:,0],0)
    m[:,1:] = mat[:,1:] - np.mean(mat[:,1:].flatten(),0)
    m[:,1:] = m[:,1:] / np.std(m[:,1:].flatten(),0) # use this!
    return m

def move_cursor(track, duration, cursor, buf=MIN_MARKERS):
    dur = 0
    while dur < duration and cursor < rows(track.resampled['matrix']) - buf:
        markers = getattr(track.analysis, track.resampled['rate'])    
        dur += markers[track.resampled['index'] + cursor].duration
        cursor += 1
    return dur, cursor

def get_mat_out(track, transition):
    """ Find and output the matrix to use in the next alignment.
        Assumes that track.resampled exists.
    """
    cursor = track.resampled['cursor']
    mat = track.resampled['matrix']
    # update cursor location to after the transition
    duration, cursor = move_cursor(track, transition, cursor)
    # output matrix with a proper number of rows, from beginning of transition
    return mat[track.resampled['cursor']:cursor,:]

def get_mat_in(track, transition, inter):
    """ Find and output the search matrix to use in the next alignment.
        Assumes that track.resampled exists.
    """
    # search from the start
    cursor = 0
    track.resampled['cursor'] = cursor
    mat = track.resampled['matrix']
    
    # compute search zone by anticipating what's playing after the transition
    marker_end = getattr(track.analysis, track.resampled['rate'])[track.resampled['index'] + rows(mat)].start
    marker_start = getattr(track.analysis, track.resampled['rate'])[track.resampled['index']].start
    search_dur = (marker_end - marker_start) - inter - 2 * transition
    
    if search_dur < 0: 
        return mat[:MIN_MARKERS,:]
    
    # find what the location is in rows
    duration, cursor = move_cursor(track, search_dur, cursor)
    
    return mat[:cursor,:]

def make_crossfade(track1, track2, inter):

    markers1 = getattr(track1.analysis, track1.resampled['rate'])    
    
    if len(markers1) < MIN_SEARCH:
        start1 = track1.resampled['cursor']
    else:
        start1 = markers1[track1.resampled['index'] + track1.resampled['cursor']].start

    start2 = max((track2.analysis.duration - (inter + 2 * X_FADE)) / 2, 0)
    markers2 = getattr(track2.analysis, track2.resampled['rate'])
    
    if len(markers2) < MIN_SEARCH:
        track2.resampled['cursor'] = start2 + X_FADE + inter
        dur = min(track2.analysis.duration - 2 * X_FADE, inter)
    else:
        duration, track2.resampled['cursor'] = move_cursor(track2, start2+X_FADE+inter, 0)
        dur = markers2[track2.resampled['index'] + track2.resampled['cursor']].start - X_FADE - start2

    xf = Crossfade((track1, track2), (start1, start2), X_FADE)
    pb = Playback(track2, start2 + X_FADE, dur)

    return [xf, pb]

def make_crossmatch(track1, track2, rate1, rate2, loc2, rows):
    markers1 = upsample_list(getattr(track1.analysis, track1.resampled['rate']), rate1)
    markers2 = upsample_list(getattr(track2.analysis, track2.resampled['rate']), rate2)
    
    def to_tuples(l, i, n):
        return [(t.start, t.duration) for t in l[i : i + n]]
    
    start1 = rate1 * (track1.resampled['index'] + track1.resampled['cursor'])
    start2 = loc2 + rate2 * track2.resampled['index'] # loc2 has already been multiplied by rate2

    return Crossmatch((track1, track2), (to_tuples(markers1, start1, rows), to_tuples(markers2, start2, rows)))
    
def make_transition(track1, track2, inter, transition):
    # the minimal transition is 2 markers
    # the minimal inter is 0 sec
    markers1 = getattr(track1.analysis, track1.resampled['rate'])
    markers2 = getattr(track2.analysis, track2.resampled['rate'])
    
    if len(markers1) < MIN_SEARCH or len(markers2) < MIN_SEARCH:
        return make_crossfade(track1, track2, inter)
    
    # though the minimal transition is 2 markers, the alignment is on at least 3 seconds
    mat1 = get_mat_out(track1, max(transition, MIN_ALIGN_DURATION))
    mat2 = get_mat_in(track2, max(transition, MIN_ALIGN_DURATION), inter)
    
    try:
        loc, n, rate1, rate2 = align(track1, track2, mat1, mat2)
    except:
        return make_crossfade(track1, track2, inter)
        
    if transition < MIN_ALIGN_DURATION:
        duration, cursor = move_cursor(track2, transition, loc)
        n = max(cursor-loc, MIN_MARKERS)
    
    xm = make_crossmatch(track1, track2, rate1, rate2, loc, n)
    # loc and n are both in terms of potentially upsampled data. 
    # Divide by rate here to get end_crossmatch in terms of the original data.
    end_crossmatch = (loc + n) / rate2
    
    if markers2[-1].start < markers2[end_crossmatch].start + inter + transition:
        inter = max(markers2[-1].start - transition, 0)
        
    # move_cursor sets the cursor properly for subsequent operations, and gives us duration.
    dur, track2.resampled['cursor'] = move_cursor(track2, inter, end_crossmatch)
    pb = Playback(track2, sum(xm.l2[-1]), dur)
    
    return [xm, pb]

def initialize(track, inter, transition):
    """find initial cursor location"""
    mat = track.resampled['matrix']
    markers = getattr(track.analysis, track.resampled['rate'])

    try:
        # compute duration of matrix
        mat_dur = markers[track.resampled['index'] + rows(mat)].start - markers[track.resampled['index']].start
        start = (mat_dur - inter - transition - FADE_IN) / 2
        dur = start + FADE_IN + inter
        # move cursor to transition marker
        duration, track.resampled['cursor'] = move_cursor(track, dur, 0)
        # work backwards to find the exact locations of initial fade in and playback sections
        fi = Fadein(track, markers[track.resampled['index'] + track.resampled['cursor']].start - inter - FADE_IN, FADE_IN)
        pb = Playback(track, markers[track.resampled['index'] + track.resampled['cursor']].start - inter, inter)
    except:
        track.resampled['cursor'] = FADE_IN + inter
        fi = Fadein(track, 0, FADE_IN)
        pb = Playback(track, FADE_IN, inter)

    return [fi, pb]
    
def terminate(track, fade):
    """ Deal with last fade out"""
    cursor = track.resampled['cursor']
    markers = getattr(track.analysis, track.resampled['rate'])
    if MIN_SEARCH <= len(markers):
        cursor = markers[track.resampled['index'] + cursor].start
    return [Fadeout(track, cursor, min(fade, track.duration-cursor))]

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# encoding: utf-8
"""
utils.py

Created by Jason Sundram, on 2010-04-05.
Copyright (c) 2010 The Echo Nest. All rights reserved.
"""

def flatten(l):
    """ Converts a list of tuples to a flat list.
        e.g. flatten([(1,2), (3,4)]) => [1,2,3,4]
    """
    return [item for pair in l for item in pair]

def tuples(l, n=2):
    """ returns n-tuples from l.
        e.g. tuples(range(4), n=2) -> [(0, 1), (1, 2), (2, 3)]
    """
    return zip(*[l[i:] for i in range(n)])

def rows(m):
    """returns the # of rows in a numpy matrix"""
    return m.shape[0]
########NEW FILE########
__FILENAME__ = cowbell
# By Rob Ochshorn and Adam Baratz.
# Slightly refactored by Joshua Lifton.
import numpy
import os
import random
import time

import echonest.remix.audio as audio

usage = """
Usage: 
    python cowbell.py <inputFilename> <outputFilename> <cowbellIntensity> <walkenIntensity>

Example:
    python cowbell.py YouCanCallMeAl.mp3 YouCanCallMeCow.mp3 0.2 0.5

Reference:
    http://www.youtube.com/watch?v=ZhSkRHXTKlw
"""

# constants
COWBELL_THRESHOLD = 0.85
COWBELL_OFFSET = -0.005

# samples
soundsPath = "sounds/"

cowbellSounds = map(lambda x: audio.AudioData(os.path.join(soundsPath, "cowbell%s.wav" % x), sampleRate=44100, numChannels=2), range(5))
walkenSounds = map(lambda x: audio.AudioData(os.path.join(soundsPath, "walken%s.wav" % x), sampleRate=44100, numChannels=2), range(16))
trill = audio.AudioData(os.path.join(soundsPath, "trill.wav"), sampleRate=44100, numChannels=2)

def linear(input, in1, in2, out1, out2):
    return ((input-in1) / (in2-in1)) * (out2-out1) + out1

def exp(input, in1, in2, out1, out2, coeff):
    if (input <= in1):
        return out1
    if (input >= in2):
        return out2
    return pow( ((input-in1) / (in2-in1)) , coeff ) * (out2-out1) + out1

class Cowbell:
    def __init__(self, input_file):
        self.audiofile = audio.LocalAudioFile(input_file)
        self.audiofile.data *= linear(self.audiofile.analysis.loudness, -2, -12, 0.5, 1.5) * 0.75

    def run(self, cowbell_intensity, walken_intensity, out):
        if cowbell_intensity != -1:
            self.cowbell_intensity = cowbell_intensity
            self.walken_intensity = walken_intensity
        t1 = time.time()
        sequence = self.sequence(cowbellSounds)
        print "Sequence and mixed in %g seconds" % (time.time() - t1)
        self.audiofile.encode(out)

    def sequence(self, chops):
        # add cowbells on the beats
        for beat in self.audiofile.analysis.beats:
            volume = linear(self.cowbell_intensity, 0, 1, 0.1, 0.3)
            # mix in cowbell on beat
            if self.cowbell_intensity == 1:
                self.mix(beat.start+COWBELL_OFFSET, seg=cowbellSounds[random.randint(0,1)], volume=volume)
            else:
                self.mix(beat.start+COWBELL_OFFSET, seg=cowbellSounds[random.randint(2,4)], volume=volume)
            # divide beat into quarters
            quarters = (numpy.arange(1,4) * beat.duration) / 4. + beat.start
            # mix in cowbell on quarters
            for quarter in quarters:
                volume = exp(random.random(), 0.5, 0.1, 0, self.cowbell_intensity, 0.8) * 0.3
                pan = linear(random.random(), 0, 1, -self.cowbell_intensity, self.cowbell_intensity)
                if self.cowbell_intensity < COWBELL_THRESHOLD:
                    self.mix(quarter+COWBELL_OFFSET, seg=cowbellSounds[2], volume=volume)
                else:
                    randomCowbell = linear(random.random(), 0, 1, COWBELL_THRESHOLD, 1)
                    if randomCowbell < self.cowbell_intensity:
                        self.mix(start=quarter+COWBELL_OFFSET, seg=cowbellSounds[random.randint(0,1)], volume=volume)
                    else:
                        self.mix(start=quarter+COWBELL_OFFSET, seg=cowbellSounds[random.randint(2,4)], volume=volume)
        # add trills / walken on section changes
        for section in self.audiofile.analysis.sections[1:]:
            if random.random() > self.walken_intensity:
                sample = trill
                volume = 0.3
            else:
                sample = walkenSounds[random.randint(0, len(walkenSounds)-1)]
                volume = 1.5
            self.mix(start=section.start+COWBELL_OFFSET, seg=sample, volume=volume)

    def mix(self, start=None, seg=None, volume=0.3, pan=0.):
        # this assumes that the audios have the same frequency/numchannels
        startsample = int(start * self.audiofile.sampleRate)
        seg = seg[0:]
        seg.data *= (volume-(pan*volume), volume+(pan*volume)) # pan + volume
        if self.audiofile.data.shape[0] - startsample > seg.data.shape[0]:
            self.audiofile.data[startsample:startsample+len(seg.data)] += seg.data[0:]


def main(inputFilename, outputFilename, cowbellIntensity, walkenIntensity ) :
    c = Cowbell(inputFilename)
    print 'cowbelling...'
    c.run(cowbellIntensity, walkenIntensity, outputFilename)

if __name__ == '__main__':
    import sys
    try :
        inputFilename = sys.argv[1]
        outputFilename = sys.argv[2]
        cowbellIntensity = float(sys.argv[3])
        walkenIntensity = float(sys.argv[4])
    except :
        print usage
        sys.exit(-1)
    main(inputFilename, outputFilename, cowbellIntensity, walkenIntensity)

########NEW FILE########
__FILENAME__ = drums
#!/usr/bin/env python
# encoding: utf=8
"""
drums.py

Add drums to a song.

At the moment, only works with songs in 4, and endings are rough.

By Ben Lacker, 2009-02-24.
"""
import numpy
import sys
import time

import echonest.remix.audio as audio

usage="""
Usage:
    python drums.py <inputfilename> <breakfilename> <outputfilename> <beatsinbreak> <barsinbreak> [<drumintensity>]

Example:
    python drums.py HereComesTheSun.mp3 breaks/AmenBrother.mp3 HereComeTheDrums.mp3 64 4 0.6

Drum instenity defaults to 0.5
"""

def mono_to_stereo(audio_data):
    data = audio_data.data.flatten().tolist()
    new_data = numpy.array((data,data))
    audio_data.data = new_data.swapaxes(0,1)
    audio_data.numChannels = 2
    return audio_data

def split_break(breakfile,n):
    drum_data = []
    start = 0
    for i in range(n):
        start = int((len(breakfile) * (i))/n)
        end = int((len(breakfile) * (i+1))/n)
        ndarray = breakfile.data[start:end]
        new_data = audio.AudioData(ndarray=ndarray,
                                    sampleRate=breakfile.sampleRate,
                                    numChannels=breakfile.numChannels)
        drum_data.append(new_data)
    return drum_data
    

def main(input_filename, output_filename, break_filename, break_parts,
            measures, mix):
    audiofile = audio.LocalAudioFile(input_filename)
    sample_rate = audiofile.sampleRate
    breakfile = audio.LocalAudioFile(break_filename)
    if breakfile.numChannels == 1:
        breakfile = mono_to_stereo(breakfile)
    num_channels = audiofile.numChannels
    drum_data = split_break(breakfile,break_parts)
    hits_per_beat = int(break_parts/(4 * measures))
    bars = audiofile.analysis.bars
    out_shape = (len(audiofile)+100000,num_channels)
    out = audio.AudioData(shape=out_shape, sampleRate=sample_rate,
                            numChannels=num_channels)
    if not bars:
        print "Didn't find any bars in this analysis!"
        print "No output."
        sys.exit(-1)
    for bar in bars[:-1]:
        beats = bar.children()
        for i in range(len(beats)):
            try:
                break_index = ((bar.local_context()[0] %\
                                measures) * 4) + (i % 4)
            except ValueError:
                break_index = i % 4
            tats = range((break_index) * hits_per_beat,
                        (break_index + 1) * hits_per_beat)
            drum_samps = sum([len(drum_data[x]) for x in tats])
            beat_samps = len(audiofile[beats[i]])
            beat_shape = (beat_samps,num_channels)
            tat_shape = (float(beat_samps/hits_per_beat),num_channels)
            beat_data= audio.AudioData(shape=beat_shape,
                                        sampleRate=sample_rate,
                                        numChannels=num_channels)
            for j in tats:
                tat_data= audio.AudioData(shape=tat_shape,
                                            sampleRate=sample_rate,
                                            numChannels=num_channels)
                if drum_samps > beat_samps/hits_per_beat:
                    # truncate drum hits to fit beat length
                    tat_data.data = drum_data[j].data[:len(tat_data)]
                elif drum_samps < beat_samps/hits_per_beat:
                    # space out drum hits to fit beat length
                    #temp_data = add_fade_out(drum_data[j])
                    tat_data.append(drum_data[j])
                tat_data.endindex = len(tat_data)
                beat_data.append(tat_data)
                del(tat_data)
            # account for rounding errors
            beat_data.endindex = len(beat_data)
            mixed_beat = audio.mix(beat_data, audiofile[beats[i]], mix=mix)
            del(beat_data)
            out.append(mixed_beat)
    finale = bars[-1].start + bars[-1].duration
    last = audio.AudioQuantum(audiofile.analysis.bars[-1].start,
                            audiofile.analysis.duration - 
                              audiofile.analysis.bars[-1].start)
    last_data = audio.getpieces(audiofile,[last])
    out.append(last_data)
    out.encode(output_filename)

if __name__=='__main__':
    try:
        input_filename = sys.argv[1]
        break_filename = sys.argv[2]
        output_filename = sys.argv[3]
        break_parts = int(sys.argv[4])
        measures = int(sys.argv[5])
        if len(sys.argv) == 7:
            mix = float(sys.argv[6])
        else:
            mix = 0.5
    except:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename, break_filename, break_parts,
            measures, mix)

########NEW FILE########
__FILENAME__ = earworm
#!/usr/bin/env python
# encoding: utf=8

"""
earworm.py
(name suggested by Jonathan Feinberg on 03/10/10)

Accepts a song and duration on the commandline, and makes a new audio file of that duration.
Creates an optimal loop if specified for looping.

Created by Tristan Jehan and Jason Sundram.
"""

from copy import deepcopy
from optparse import OptionParser
import numpy as np
from numpy.matlib import repmat, repeat
from numpy import sqrt
import operator
import os
import sys

try:
    import networkx as nx
except ImportError:
    print """earworm.py requires networkx. 
    
If setuptools is installed on your system, simply:
easy_install networkx 

Otherwise, you can get it here: http://pypi.python.org/pypi/networkx

Get the source, unzip it, cd to the directory it is in and run:
    python setup.py install
"""
    sys.exit(1)

from echonest.remix.action import Playback, Jump, Fadeout, render, display_actions
from echonest.remix.audio import LocalAudioFile
# from echonest.remix.cloud_support import AnalyzedAudioFile

from earworm_support import evaluate_distance, timbre_whiten, resample_features
from utils import rows, tuples, flatten


DEF_DUR = 600
MAX_SIZE = 800
MIN_RANGE = 16
MIN_JUMP = 16
MIN_ALIGN = 16
MAX_EDGES = 8
FADE_OUT = 3
RATE = 'beats'

def read_graph(name="graph.gpkl"):
    if os.path.splitext(name)[1] == ".gml": 
        return nx.read_gml(name)
    else: 
        return nx.read_gpickle(name)

def save_graph(graph, name="graph.gpkl"):
    if os.path.splitext(name)[1] == ".gml": 
        nx.write_gml(graph, name)
    else: 
        nx.write_gpickle(graph, name)

def print_screen(paths):
    for i, p in enumerate(paths):
        print i, [l[0] - i for l in p]

def save_plot(graph, name="graph.png"):
    """save plot with index numbers rather than timing"""
    edges = graph.edges(data=True)
    nodes = [edge[2]['source'] for edge in edges]
    order = np.argsort(nodes)
    edges =  [edges[i] for i in order.tolist()]
    new_edges = []
    for edge in edges:
        v = edge[2]['target'] - edge[2]['source']-1
        new_edges.append((edge[2]['source'], edge[2]['target']))
    DG = nx.DiGraph()
    DG.add_edges_from(new_edges)
    A = nx.to_agraph(DG)
    A.layout()
    A.draw(name)
    
def make_graph(paths, markers):
    DG = nx.DiGraph()
    # add nodes
    for i in xrange(len(paths)):
        DG.add_node(markers[i].start)
    # add edges
    edges = []
    for i in xrange(len(paths)):
        if i != len(paths)-1:
            edges.append((markers[i].start, markers[i+1].start, {'distance':0, 'duration': markers[i].duration, 'source':i, 'target':i+1})) # source and target for plots only
        edges.extend([(markers[i].start, markers[l[0]+1].start, {'distance':l[1], 'duration': markers[i].duration, 'source':i, 'target':l[0]+1}) for l in paths[i]])
    DG.add_edges_from(edges)
    return DG

def make_similarity_matrix(matrix, size=MIN_ALIGN):
    singles = matrix.tolist()
    points = [flatten(t) for t in tuples(singles, size)]
    numPoints = len(points)
    distMat = sqrt(np.sum((repmat(points, numPoints, 1) - repeat(points, numPoints, axis=0))**2, axis=1, dtype=np.float32))
    return distMat.reshape((numPoints, numPoints))

def get_paths(matrix, size=MIN_RANGE):
    mat = make_similarity_matrix(matrix, size=MIN_ALIGN)
    paths = []
    for i in xrange(rows(mat)):
        paths.append(get_loop_points(mat[i,:], size))
    return paths

def get_paths_slow(matrix, size=MIN_RANGE):
    paths = []
    for i in xrange(rows(matrix)-MIN_ALIGN+1):
        vector = np.zeros((rows(matrix)-MIN_ALIGN+1,), dtype=np.float32)
        for j in xrange(rows(matrix)-MIN_ALIGN+1):
            vector[j] = evaluate_distance(matrix[i:i+MIN_ALIGN,:], matrix[j:j+MIN_ALIGN,:])
        paths.append(get_loop_points(vector, size))
    return paths

# can this be made faster?
def get_loop_points(vector, size=MIN_RANGE, max_edges=MAX_EDGES):
    res = set()
    m = np.mean(vector)
    s = np.std(vector)
    for i in xrange(vector.size-size):
        sub = vector[i:i+size]
        j = np.argmin(sub)
        if sub[j] < m-s and j != 0 and j != size-1 and sub[j] < sub[j-1] and sub[j] < sub[j+1] and sub[j] != 0:
            res.add((i+j, sub[j]))
            i = i+j # we skip a few steps
    # let's remove clusters of minima
    res = sorted(res, key=operator.itemgetter(0))
    out = set()
    i = 0
    while i < len(res):
        tmp = [res[i]]
        j = 1
        while i+j < len(res):
            if res[i+j][0]-res[i+j-1][0] < MIN_RANGE:
                tmp.append(res[i+j])
                j = j+1
            else:
                break
        tmp = sorted(tmp, key=operator.itemgetter(1))
        out.add(tmp[0])
        i = i+j
    out = sorted(out, key=operator.itemgetter(1))
    return out[:max_edges]

def path_intersect(timbre_paths, pitch_paths):
    assert(len(timbre_paths) == len(pitch_paths))
    paths = []
    for i in xrange(len(timbre_paths)):
        t_list = timbre_paths[i]
        p_list = pitch_paths[i]
        t = [l[0] for l in t_list]
        p = [l[0] for l in p_list]
        r = filter(lambda x:x in t,p)
        res = [(v, t_list[t.index(v)][1] + p_list[p.index(v)][1]) for v in r]
        paths.append(res)
    return paths

def get_jumps(graph, mode='backward'):
    loops = []
    edges = graph.edges(data=True)
    for edge in edges:
        if mode == 'infinite' and edge[1] < edge[0] or edge[2]['distance'] == 0:
            loops.append(edge)
        if mode == 'backward' and edge[1] < edge[0]: 
            loops.append(edge)
        if mode == 'forward' and edge[0] < edge[1] and 1 < edge[2]['target']-edge[2]['source']:
            loops.append(edge)
    if mode == 'infinite':
        order = np.argsort([l[0] for l in loops]).tolist()
    if mode == 'backward': 
        order = np.argsort([l[0]-l[1]+l[2]['duration'] for l in loops]).tolist()
        order.reverse() # we want long loops first
    if mode == 'forward': 
        order = np.argsort([l[1]-l[0]-l[2]['duration'] for l in loops]).tolist()
        order.reverse() # we want long loops first
    loops =  [loops[i] for i in order]
    return loops

def trim_graph(graph):
    
    # trim first_node if necessary
    first_node = min(graph.nodes())
    deg = graph.degree(first_node)
    while deg <= 1:
        graph.remove_node(first_node)
        first_node = min(graph.nodes())
        deg = graph.degree(first_node)
        
    # trim last node if necessary
    last_node = max(graph.nodes())
    deg = graph.degree(last_node)
    while deg <= 1:
        graph.remove_node(last_node)
        last_node = max(graph.nodes())
        deg = graph.degree(last_node)
    
    return graph, first_node, last_node

def collect(edges, path):
    # kind slow but fine
    res = []
    for p in path:
        for e in edges:
            if (p[0], p[1]) == (e[0], e[1]):
                if e[2]['target']-e[2]['source'] == 1:
                    res.append(p)
                else:
                    res.append(e)
    return res
    
def infinite(graph, track, target):
    DG = nx.DiGraph()
    loops = get_jumps(graph, mode='backward')
    DG.add_edges_from(loops)
    DG, first_node, last_node = trim_graph(DG)
    
    def dist(node1, node2): return node2-node1
    
    # search for shortest path from last to first node
    alt = True
    path = []
    while path == []:
        edges = DG.edges(data=True)
        try:
            path = tuples(nx.astar_path(DG, last_node, first_node, dist))
        except:
            if alt == True:
                DG.remove_node(first_node)
                alt = False
            else:
                DG.remove_node(last_node)
                alt = True
            DG, first_node, last_node = trim_graph(DG)
            
    assert(path != []) # FIXME -- maybe find a few loops and deal with them
    
    res = collect(edges, path)
    res_dur = 0
    for r in res:
        if r[1] < r[0]: res_dur += r[2]['duration']
        else: res_dur += r[1]-r[0]
    
    # trim graph to DG size
    f_n = min(graph.nodes())
    while f_n < first_node:
        graph.remove_node(f_n)
        f_n = min(graph.nodes())
    l_n = max(graph.nodes())
    while last_node < l_n:
        graph.remove_node(l_n)
        l_n = max(graph.nodes())
    
    # find optimal path
    path = compute_path(graph, max(target-res_dur, 0))    
    path = path + res
    # build actions
    actions = make_jumps(path, track)
    actions.pop(-1)
    jp = Jump(track, actions[-1].source, actions[-1].target, actions[-1].duration)
    actions.pop(-1)
    actions.append(jp)
    return actions

def remove_short_loops(graph, mlp):
    edges = graph.edges(data=True)
    for e in edges:
        dist = e[2]['target'] - e[2]['source']
        if dist == 1: continue
        if mlp < dist: continue
        if dist <= -mlp+1: continue
        graph.remove_edge(e[0], e[1])

def one_loop(graph, track, mode='shortest'):
    jumps = get_jumps(graph, mode='backward')
    if len(jumps) == 0: return []
    loop = None
    if mode == 'longest':
        loop = jumps[0]
    else:
        jumps.reverse()
        for jump in jumps:
            if jump[1] < jump[0]:
                loop = jump
                break
    if loop == None: return []
    # Let's capture a bit of the attack
    OFFSET = 0.025 # 25 ms
    pb = Playback(track, loop[1]-OFFSET, loop[0]-loop[1])
    jp = Jump(track, loop[0]-OFFSET, loop[1]-OFFSET, loop[2]['duration'])
    return [pb, jp]
    
def compute_path(graph, target):

    first_node = min(graph.nodes())
    last_node = max(graph.nodes())
        
    # find the shortest direct path from first node to last node
    if target == 0:
        def dist(node1, node2): return node2-node1 # not sure why, but it works
        # we find actual jumps
        edges = graph.edges(data=True)
        path = tuples(nx.astar_path(graph, first_node, last_node, dist))
        res = collect(edges, path)
        return res
    
    duration = last_node - first_node
    if target < duration: 
        # build a list of sorted jumps by length.
        remaining = duration-target
        # build a list of sorted loops by length.
        loops = get_jumps(graph, mode='forward')
        
        def valid_jump(jump, jumps, duration):
            for j in jumps:
                if j[0] < jump[0] and jump[0] < j[1]:
                    return False
                if j[0] < jump[1] and jump[1] < j[1]:
                    return False
                if duration - (jump[1]-jump[0]+jump[2]['duration']) < 0:
                    return False
            if duration - (jump[1]-jump[0]+jump[2]['duration']) < 0:
                return False
            return True
        
        res = []
        while 0 < remaining:
            if len(loops) == 0: break
            for l in loops:
                if valid_jump(l, res, remaining) == True:
                    res.append(l)
                    remaining -= (l[1]-l[0]+l[2]['duration'])
                    loops.remove(l)
                    break
                if l == loops[-1]:
                    loops.remove(l)
                    break
        res = sorted(res, key=operator.itemgetter(0))
        
    elif duration < target:
        remaining = target-duration
        loops = get_jumps(graph, mode='backward')
        tmp_loops = deepcopy(loops)
        res = []
        # this resolution value is about the smallest denominator
        resolution = loops[-1][1]-loops[-1][0]-loops[-1][2]['duration']
        while remaining > 0:
            if len(tmp_loops) == 0: 
                tmp_loops = deepcopy(loops)
            d = -9999999999999999
            i = 0
            while d < resolution and i+1 <= len(tmp_loops):
                l = tmp_loops[i]
                d = remaining - (l[0]-l[1]+l[2]['duration'])
                i += 1
            res.append(l)
            remaining -= (l[0]-l[1]+l[2]['duration'])
            tmp_loops.remove(l)
        order = np.argsort([l[0] for l in res]).tolist()
        res =  [res[i] for i in order]
        
    else:
        return [(first_node, last_node)]
        
    def dist(node1, node2): return 0 # not sure why, but it works
    start = tuples(nx.astar_path(graph, first_node, res[0][0], dist))
    end = tuples(nx.astar_path(graph, res[-1][1], last_node, dist))
    
    return start + res + end

def make_jumps(path, track):
    actions = []
    source = path[0][0]
    #pb = Playback(track, 0, 10)
    for p in path:
        try:
            if p[2]['target']-p[2]['source'] == 1: 
                raise
            target = p[0]
            if 0 < target-source:
                actions.append(Playback(track, source, target-source))
            actions.append(Jump(track, p[0], p[1], p[2]['duration']))
            source = p[1]
        except:
            target = p[1]
    if 0 < target-source:
        actions.append(Playback(track, source, target-source))
    return actions

def terminate(dur_intro, middle, dur_outro, duration, lgh):
    # merge intro
    if isinstance(middle[0], Playback):
        middle[0].start = 0
        middle[0].duration += dur_intro
        start = []
    else:
        start = [Playback(middle[0].track, 0, dur_intro)]
    # merge outro
    if isinstance(middle[-1], Playback):
        middle[-1].duration += dur_outro
        end = []
    else:
        end = [Playback(middle[-1].track, middle[-1].start + middle[-1].duration, dur_outro)]
    # combine
    actions = start + middle + end
    if lgh == False:
        return actions
    excess = sum(inst.duration for inst in actions)-duration
    if excess == 0:
        return actions
    # trim the end with fadeout
    if actions[-1].duration <= FADE_OUT+excess:
        start = actions[-1].start
        dur = FADE_OUT
        actions.remove(actions[-1])
    else:
        actions[-1].duration -= FADE_OUT+excess
        start = actions[-1].start+actions[-1].duration
        dur = FADE_OUT
    actions.append(Fadeout(middle[0].track, start, dur))
    return actions

def do_work(track, options):
    
    dur = float(options.duration)
    mlp = int(options.minimum)
    lgh = bool(options.length)
    inf = bool(options.infinite)
    pkl = bool(options.pickle)
    gml = bool(options.graph)
    plt = bool(options.plot)
    fce = bool(options.force)
    sho = bool(options.shortest)
    lon = bool(options.longest)
    vbs = bool(options.verbose)
    
    mp3 = track.filename
    try:
        if fce == True:
            raise
        graph = read_graph(mp3+".graph.gpkl")
    except:
        # compute resampled and normalized matrix
        timbre = resample_features(track, rate=RATE, feature='timbre')
        timbre['matrix'] = timbre_whiten(timbre['matrix'])
        pitch = resample_features(track, rate=RATE, feature='pitches')
        
        # pick a tradeoff between speed and memory size
        if rows(timbre['matrix']) < MAX_SIZE:
            # faster but memory hungry. For euclidean distances only.
            t_paths = get_paths(timbre['matrix'])
            p_paths = get_paths(pitch['matrix'])
        else:
            # slower but memory efficient. Any distance possible.
            t_paths = get_paths_slow(timbre['matrix'])
            p_paths = get_paths_slow(pitch['matrix'])
            
        # intersection of top timbre and pitch results
        paths = path_intersect(t_paths, p_paths)
        # TEMPORARY -- check that the data looks good
        if vbs == True:
            print_screen(paths)
        # make graph
        markers = getattr(track.analysis, timbre['rate'])[timbre['index']:timbre['index']+len(paths)]
        graph = make_graph(paths, markers)
        
    # remove smaller loops for quality results
    if 0 < mlp:
        remove_short_loops(graph, mlp)
    # plot graph
    if plt == True:
        save_plot(graph, mp3+".graph.png")
    # save graph
    if pkl == True:
        save_graph(graph, mp3+".graph.gpkl")
    if gml == True:
        save_graph(graph, mp3+".graph.gml")
    # single loops
    if sho == True:
        return one_loop(graph, track, mode='shortest')
    if lon == True:
        return one_loop(graph, track, mode='longest')
    # other infinite loops
    if inf == True:
        if vbs == True:
            print "\nInput Duration:", track.analysis.duration
        # get the optimal path for a given duration
        return infinite(graph, track, dur)
        
    dur_intro = min(graph.nodes())
    dur_outro = track.analysis.duration - max(graph.nodes())
    
    if vbs == True:
        print "Input Duration:", track.analysis.duration
    # get the optimal path for a given duration
    path = compute_path(graph, max(dur-dur_intro-dur_outro, 0))
    # build actions
    middle = make_jumps(path, track)
    # complete list of actions
    actions = terminate(dur_intro, middle, dur_outro, dur, lgh)
    
    return actions

def main():
    usage = "usage: %s [options] <one_single_mp3>" % sys.argv[0]
    parser = OptionParser(usage=usage)
    parser.add_option("-d", "--duration", default=DEF_DUR, help="target duration (argument in seconds) default=600")
    parser.add_option("-m", "--minimum", default=MIN_JUMP, help="minimal loop size (in beats) default=8")
    parser.add_option("-i", "--infinite", action="store_true", help="generate an infinite loop (outputs a wav file)")
    parser.add_option("-l", "--length", action="store_true", help="length must be accurate")
    parser.add_option("-k", "--pickle", action="store_true", help="output graph as a pickle object")
    parser.add_option("-g", "--graph", action="store_true", help="output graph as a gml text file")
    parser.add_option("-p", "--plot", action="store_true", help="output graph as png image")
    parser.add_option("-f", "--force", action="store_true", help="force (re)computing the graph")
    parser.add_option("-S", "--shortest", action="store_true", help="output the shortest loop")
    parser.add_option("-L", "--longest", action="store_true", help="output the longest loop")
    parser.add_option("-v", "--verbose", action="store_true", help="show results on screen")
    
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        return -1
    
    verbose = options.verbose
    track = LocalAudioFile(args[0], verbose=verbose)
    
    # this is where the work takes place
    actions = do_work(track, options)
    
    if verbose:
        display_actions(actions)
        print "Output Duration = %.3f sec" % sum(act.duration for act in actions)
    
    # Send to renderer
    name = os.path.splitext(os.path.basename(args[0]))
    
    # Output wav for loops in order to remain sample accurate
    if bool(options.infinite) == True: 
        name = name[0]+'_'+str(int(options.duration))+'_loop.wav'
    elif bool(options.shortest) == True: 
        name = name[0]+'_'+str(int(sum(act.duration for act in actions)))+'_shortest.wav'
    elif bool(options.longest) == True: 
        name = name[0]+'_'+str(int(sum(act.duration for act in actions)))+'_longest.wav'
    else: 
        name = name[0]+'_'+str(int(options.duration))+'.mp3'
    
    if options.verbose:
        print "Rendering..."
    render(actions, name, verbose=verbose)
    return 1


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = earworm_support
#!/usr/bin/env python
# encoding: utf-8

"""
earworm_support.py

Created by Tristan Jehan and Jason Sundram.
"""

import numpy as np
from copy import deepcopy
from utils import rows

FUSION_INTERVAL = .06   # This is what we use in the analyzer
AVG_PEAK_OFFSET = 0.025 # Estimated time between onset and peak of segment.


def evaluate_distance(mat1, mat2):
    return np.linalg.norm(mat1.flatten() - mat2.flatten())

def timbre_whiten(mat):
    if rows(mat) < 2: return mat
    m = np.zeros((rows(mat), 12), dtype=np.float32)
    m[:,0] = mat[:,0] - np.mean(mat[:,0],0)
    m[:,0] = m[:,0] / np.std(m[:,0],0)
    m[:,1:] = mat[:,1:] - np.mean(mat[:,1:].flatten(),0)
    m[:,1:] = m[:,1:] / np.std(m[:,1:].flatten(),0) # use this!
    return m


def get_central(analysis, member='segments'):
    """ Returns a tuple: 
        1) copy of the members (e.g. segments) between end_of_fade_in and start_of_fade_out.
        2) the index of the first retained member.
    """
    def central(s):
        return analysis.end_of_fade_in <= s.start and (s.start + s.duration) < analysis.start_of_fade_out
    
    members = getattr(analysis, member)
    ret = filter(central, members[:]) 
    index = members.index(ret[0]) if ret else 0
    
    return ret, index


def get_mean_offset(segments, markers):
    if segments == markers:
        return 0
    
    index = 0
    offsets = []
    try:
        for marker in markers:
            while segments[index].start < marker.start + FUSION_INTERVAL:
                offset = abs(marker.start - segments[index].start)
                if offset < FUSION_INTERVAL:
                    offsets.append(offset)
                index += 1
    except IndexError, e:
        pass
    
    return np.average(offsets) if offsets else AVG_PEAK_OFFSET


def resample_features(data, rate='tatums', feature='timbre'):
    """
    Resample segment features to a given rate within fade boundaries.
    @param data: analysis object.
    @param rate: one of the following: segments, tatums, beats, bars.
    @param feature: either timbre or pitch.
    @return A dictionary including a numpy matrix of size len(rate) x 12, a rate, and an index
    """
    ret = {'rate': rate, 'index': 0, 'cursor': 0, 'matrix': np.zeros((1, 12), dtype=np.float32)}
    segments, ind = get_central(data.analysis, 'segments')
    markers, ret['index'] = get_central(data.analysis, rate)
    
    if len(segments) < 2 or len(markers) < 2:
        return ret
        
    # Find the optimal attack offset
    meanOffset = get_mean_offset(segments, markers)
    # Make a copy for local use
    tmp_markers = deepcopy(markers)
    
    # Apply the offset
    for m in tmp_markers:
        m.start -= meanOffset
        if m.start < 0: m.start = 0
        
    # Allocate output matrix, give it alias mat for convenience.
    mat = ret['matrix'] = np.zeros((len(tmp_markers)-1, 12), dtype=np.float32)
    
    # Find the index of the segment that corresponds to the first marker
    f = lambda x: tmp_markers[0].start < x.start + x.duration
    index = (i for i,x in enumerate(segments) if f(x)).next()
    
    # Do the resampling
    try:
        for (i, m) in enumerate(tmp_markers):
            while segments[index].start + segments[index].duration < m.start + m.duration:
                dur = segments[index].duration
                if segments[index].start < m.start:
                    dur -= m.start - segments[index].start
                
                C = min(dur / m.duration, 1)
                
                mat[i, 0:12] += C * np.array(getattr(segments[index], feature))
                index += 1
            
            C = min( (m.duration + m.start - segments[index].start) / m.duration, 1)
            mat[i, 0:12] += C * np.array(getattr(segments[index], feature))
    except IndexError, e:
        pass # avoid breaking with index > len(segments)
    
    return ret
########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# encoding: utf-8
"""
utils.py

Created by Jason Sundram, on 2010-04-05.
"""

def flatten(l):
    """ Converts a list of tuples to a flat list.
        e.g. flatten([(1,2), (3,4)]) => [1,2,3,4]
    """
    return [item for pair in l for item in pair]

def tuples(l, n=2):
    """ returns n-tuples from l.
        e.g. tuples(range(4), n=2) -> [(0, 1), (1, 2), (2, 3)]
    """
    return zip(*[l[i:] for i in range(n)])

def rows(m):
    """returns the # of rows in a numpy matrix"""
    return m.shape[0]
########NEW FILE########
__FILENAME__ = filter
#!/usr/bin/env/python
#encoding: utf=8
"""
filter.py

Filters lists of  AudioQuanta (bars, beats, tatums, segments) 
by various proporties, and resynthesizes them

'pitch' takes an integer a finds chunks that have a pitch maximum in the given index
'pitches' takes a list of integers (be sure to quote them on the command line:  "[0, 4, 7]")
 and finds chunks that have pitch maxima in those pitches - a simple chord-finder
'duration' takes a pair of integers (be sure to quote them on the command line:  "[7, 14]")
 or floats and finds chunks that overlap / are within that range in time
'louder' and 'softer' take a float and finds chunks that are louder or softer than the number
 (in dBFS, so 0.0 is the loudest)

By Thor Kell, 2012-11-14
"""

import echonest.remix.audio as audio

usage = """
    python filter.py <bars|beats|tatums|segments> <pitch|pitches|duration|louder|softer> <value> <input_filename> <output_filename>

"""
def main(units, key, value, input_filename, output_filename):
    audiofile = audio.LocalAudioFile(input_filename)
    chunks = audiofile.analysis.__getattribute__(units)
    
    if key == 'pitch':
        value = int(value);
    if key == 'pitches':
        value = eval(value)
        if type(value) != list:
            print usage
            sys.exit(-1)
    if key == 'duration':
        value = eval(value)
        duration_start = value[0]
        duration_end = value[1]
    if key == 'louder' or key == 'softer':
        value = float(value)
    
    filtered_chunks = []
    for chunk in chunks:
        if key == 'pitch':      
            pitches = chunk.mean_pitches()
            if pitches.index(max(pitches)) == value:        
                filtered_chunks.append(chunk)
   
        if key == 'pitches':
            max_indexes = []
            pitches = chunk.mean_pitches()
            max_pitches = sorted(pitches, reverse=True)
            for pitch in max_pitches:
                 max_indexes.append(pitches.index(pitch)) 
            
            if set(value) == set(max_indexes[0:len(value)]):
                filtered_chunks.append(chunk)

        if key == 'duration':
            if chunk.start < duration_end and chunk.end > duration_start:
                filtered_chunks.append(chunk)
            elif chunk.start > duration_end:
                break

        if key == 'louder':
            if chunk.mean_loudness() > value:
                filtered_chunks.append(chunk)

        if key == 'softer':
            if chunk.mean_loudness() < value:
                filtered_chunks.append(chunk)

    out = audio.getpieces(audiofile, filtered_chunks)
    out.encode(output_filename)

if __name__ == '__main__':
    import sys
    try:
        unit = sys.argv[1]
        key = sys.argv[2]
        value = sys.argv[3]
        input_filename = sys.argv[4]
        output_filename = sys.argv[5]

    except:
        print usage
        sys.exit(-1)
    main(unit, key, value, input_filename, output_filename)

########NEW FILE########
__FILENAME__ = jingler
# By Tristan Jehan, based on cowbell.py, itself based on previous jingler code.
# This script takes an mp3 file and produces an mp3 file dubbed with synchronized sleighbells
# and other christmassy sounds.
import numpy
import os
import random
import time

import echonest.remix.audio as audio

usage = """
Usage: 
    python jingler.py <inputFilename> <outputFilename>
Example:
    python jingler.py aha.mp3 aha_Jingled.mp3
Reference:
    http://www.thejingler.com
"""

# constants
SLEIGH_OFFSET = [-0.2, -0.075] # seconds
SIGNAL_OFFSET = -1.0 # seconds
SANTA_OFFSET = -6.25 # seconds
SLEIGH_THRESHOLD = 0.420 # seconds
MIN_BEAT_DURATION = 0.280 # seconds
MAX_BEAT_DURATION = 0.560 # seconds
LIMITER_THRESHOLD = 29491 # 90% of the dynamic range
LIMITER_COEFF = 0.2 # compresion curve

# samples
soundsPath = "sounds/"

snowSantaSounds  = map(lambda x: audio.AudioData(os.path.join(soundsPath, "snowSanta%s.wav" % x), sampleRate=44100, numChannels=2), range(1))
sleighBellSounds = map(lambda x: audio.AudioData(os.path.join(soundsPath, "sleighBell%s.wav" % x), sampleRate=44100, numChannels=2), range(2))
signalBellSounds = map(lambda x: audio.AudioData(os.path.join(soundsPath, "signalBell%s.wav" % x), sampleRate=44100, numChannels=2), range(3))

# some math useful for normalization
def linear(input, in1, in2, out1, out2):
    return ((input-in1) / (in2-in1)) * (out2-out1) + out1

class Jingler:
    def __init__(self, input_file):
        self.audiofile = audio.LocalAudioFile(input_file)
        self.audiofile.data *= linear(self.audiofile.analysis.loudness, 
                                        -2, -12, 0.5, 1.5) * 0.75
        # Check that there are beats in the song
        if len(self.audiofile.analysis.beats) < 5: 
            print 'not enough beats in this song...'
            sys.exit(-2)
        self.duration = len(self.audiofile.data) / self.audiofile.sampleRate

    def run(self, out):
        # sequence and mix
        t1 = time.time()
        print "Sequencing and mixing..."
        self.sequence(sleighBellSounds)
        print "Normalizing audio output..."
        #self.limiter() # slow but can be used in place of self.normalize()
        self.normalize() # remove this line if you use self.limiter() instead
        # at this point self.audiofile.data is down to a int16 array
        print "Sequenced, mixed and normalized in %.3f secs" % (time.time() - t1)
        # save
        t1 = time.time()
        print "Encoding mp3..."
        self.audiofile.encode(out)
        print "Encoded in %.3f secs" % (time.time() - t1)

    def normalize(self):
        # simple normalization that prevents clipping. There can be a little bit of a volume drop.
        # to prevent volume drops, use self.limiter() instead, however it is slower.
        factor = 32767.0 / numpy.max(numpy.absolute(self.audiofile.data.flatten()))
        if factor < 1:
            # we return to 16 bit arrays
            self.audiofile.data = numpy.array(self.audiofile.data * factor, dtype=numpy.int16)

    def sequence(self, chops):
        # adjust sounds and durations
        if self.audiofile.analysis.beats[4].duration < MIN_BEAT_DURATION:
            stride = 2
        else:
            stride = 1
        if self.audiofile.analysis.beats[4].duration > MAX_BEAT_DURATION:
            multiplier = 0.5
        else:
            multiplier = 1
        if self.audiofile.analysis.beats[4].duration * stride * multiplier > SLEIGH_THRESHOLD:
            sleighBellIndex = 0
        else:
            sleighBellIndex = 1
        # add sleigh bells on the beats
        for i in range(0,len(self.audiofile.analysis.beats),stride):
            beat = self.audiofile.analysis.beats[i]
            # let's put a little bit of jitter in the volume
            vol = 0.6 + random.randint(-100, 100) / 1000.0
            sample = sleighBellSounds[sleighBellIndex]
            # let's stop jingling 5 seconds before the end anyhow
            if beat.start + SLEIGH_OFFSET[sleighBellIndex] + 5.0 < self.duration:
                self.mix(beat.start + SLEIGH_OFFSET[sleighBellIndex], seg=sample, volume=vol)
            if multiplier == 0.5:
                self.mix(beat.start + beat.duration/2.0 + SLEIGH_OFFSET[sleighBellIndex], seg=sample, volume=vol/2.0)
        # add signal bells on section changes
        for section in self.audiofile.analysis.sections[1:]:
            sample = signalBellSounds[random.randint(0,1)]
            self.mix(start=section.start+SIGNAL_OFFSET, seg=sample, volume=0.5)
        # add other signals in case there's some silence at the beginning
        if self.audiofile.analysis.end_of_fade_in > 0.5:
            sample = signalBellSounds[2]
            self.mix(start=max(0,self.audiofile.analysis.end_of_fade_in-1.0), seg=sample, volume=1.0)
        # add santa walking at the end of the track
        sample = snowSantaSounds[0]
        self.mix(start=self.duration+SANTA_OFFSET, seg=sample, volume=1.0)

    def mix(self, start=None, seg=None, volume=0.3, pan=0.):
        # this assumes that the audios have the same samplerate/numchannels
        startsample = int(start * self.audiofile.sampleRate)
        seg = seg[0:]
        seg.data *= (volume-(pan*volume), volume+(pan*volume)) # pan and volume
        if start > 0 and self.audiofile.data.shape[0] - startsample > seg.data.shape[0]:
            self.audiofile.data[startsample:startsample+len(seg.data)] += seg.data[0:]

    def curve_int16(self, x):
        return int(numpy.power((x-LIMITER_THRESHOLD)/3276, LIMITER_COEFF) * 3276 + LIMITER_THRESHOLD)

    def limit_int16(self, x):
        if x > LIMITER_THRESHOLD:
            tmp = self.curve_int16(x)
            if tmp > 32767: return 32767
            else: return tmp
        elif x < -LIMITER_THRESHOLD:
            value = -x
            tmp = self.curve_int16(value)
            if tmp > 32767: return -32767
            else: return -tmp
        return x

    def limiter(self):
        # simple attempt at compressing and limiting the mixed signal to avoid clipping
        # this is a bit slower than I would like (roughly 10 secs) but it works fine
        vec_limiter = numpy.vectorize(self.limit_int16, otypes=[numpy.int16])
        self.audiofile.data = vec_limiter(self.audiofile.data)


def main(inputFilename, outputFilename):
    j = Jingler(inputFilename)
    print 'jingling...'
    j.run(outputFilename)
    print 'Done.'

if __name__ == '__main__':
    import sys
    try :
        inputFilename = sys.argv[1]
        outputFilename = sys.argv[2]
    except :
        print usage
        sys.exit(-1)
    main(inputFilename, outputFilename)

########NEW FILE########
__FILENAME__ = lopside
#!/usr/bin/env python
# encoding: utf=8

"""
lopside.py

Cut out the final beat or group of tatums in each bar.
Demonstrates the beat hierarchy navigation in AudioQuantum

Originally by Adam Lindsay, 2009-01-19.
"""
import echonest.remix.audio as audio
import sys

usage = """
Usage: 
    python lopside.py [tatum|beat] <inputFilename> <outputFilename>
Beat is selected by default.

Example:
    python lopside.py beat aha.mp3 ahawaltz.mp3
"""


def main(units, inputFile, outputFile):
    audiofile = audio.LocalAudioFile(inputFile)
    collect = audio.AudioQuantumList()
    if not audiofile.analysis.bars:
        print "No bars found in this analysis!"
        print "No output."
        sys.exit(-1)
    for b in audiofile.analysis.bars[0:-1]:                
        # all but the last beat
        collect.extend(b.children()[0:-1])
        if units.startswith("tatum"):
            # all but the last half (round down) of the last beat
            half = - (len(b.children()[-1].children()) // 2)
            collect.extend(b.children()[-1].children()[0:half])
    # endings were rough, so leave everything after the start
    # of the final bar intact:
    last = audio.AudioQuantum(audiofile.analysis.bars[-1].start,
                              audiofile.analysis.duration - 
                                audiofile.analysis.bars[-1].start)
    collect.append(last)
    out = audio.getpieces(audiofile, collect)
    out.encode(outputFile)

if __name__ == '__main__':
    try:
        units = sys.argv[-3]
        inputFilename = sys.argv[-2]
        outputFilename = sys.argv[-1]
    except:
        print usage
        sys.exit(-1)
    main(units, inputFilename, outputFilename)

########NEW FILE########
__FILENAME__ = enToMIDI
#!/usr/bin/env python
# encoding: utf-8
"""
enToMIDI.py

Created by Brian Whitman on 2008-11-25.
Copyright (c) 2008 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import echonest.remix.audio as audio
from copy import copy
from echonest.remix.support import midi
from echonest.remix.support.midi.MidiOutFile import MidiOutFile
from math import pow

def main():
    # Examples:
    # TRLYNOP11DE633DD31 church bells
    # TRWMWTX11DE6393849 a7 unt by lithops
    # TRMTWYL11DD5A1D829 valley hi by stereolab
    #a = audio.ExistingTrack("TRMTWYL11DD5A1D829").analysis 
    a = audio.LocalAudioFile(sys.argv[1]).analysis
    midi = MidiOutFile('output.mid')
    midi.header()
    midi.start_of_track()
    midi.tempo(int(60000000.00 / 60.0)) # 60 BPM, one Q per second, 96 ticks per Q, 96 ticks per second.)
    BOOST = 30 # Boost volumes if you want

    # Do you want the channels to be split by timbre or no? 
    splitChannels = True

    for seg_index in xrange(len(a.segments)):
        s = a.segments[seg_index]

        if(splitChannels):
            # Figure out a channel to assign this segment to. Let PCA do the work here... we'll just take the sign of coeffs 1->5 as a 4-bit #
            bits = [0,0,0,0]
            for i in xrange(4):
                # Can't use the first coeff because it's (always?) positive.
                if(s.timbre[i+1]>=0): bits[i] =1
            channel = bits[0]*8 + bits[1]*4 + bits[2]*2 + bits[3]*1
        else:
            channel = 0
    
        # Get the loudnesses in MIDI cc #7 vals for the start of the segment, the loudest part, and the start of the next segment.
        # db -> voltage ratio http://www.mogami.com/e/cad/db.html
        linearMaxVolume = int(pow(10.0,s.loudness_max/20.0)*127.0)+BOOST
        linearStartVolume = int(pow(10.0,s.loudness_begin/20.0)*127.0)+BOOST
        if(seg_index == len(a.segments)-1): # if this is the last segment
            linearNextStartVolume = 0
        else:
            linearNextStartVolume = int(pow(10.0,a.segments[seg_index+1].loudness_begin/20.0)*127.0)+BOOST
        whenMaxVolume = s.time_loudness_max

        # Count the # of ticks I wait in doing the volume ramp so I can fix up rounding errors later.
        tt = 0
        
        # take pitch vector and hit a note on for each pitch at its relative volume. That's 12 notes per segment.
        for note in xrange(12):
            volume = int(s.pitches[note]*127.0)
            midi.update_time(0)
            midi.note_on(channel=channel, note=0x3C+note, velocity=volume)
        midi.update_time(0)
        
        # Set volume of this segment. Start at the start volume, ramp up to the max volume , then ramp back down to the next start volume.
        curVol = float(linearStartVolume)
        
        # Do the ramp up to max from start
        ticksToMaxLoudnessFromHere = int(96.0 * whenMaxVolume)
        if(ticksToMaxLoudnessFromHere > 0):
            howMuchVolumeToIncreasePerTick = float(linearMaxVolume - linearStartVolume)/float(ticksToMaxLoudnessFromHere)
            for ticks in xrange(ticksToMaxLoudnessFromHere):
                midi.continuous_controller(channel,7,int(curVol))
                curVol = curVol + howMuchVolumeToIncreasePerTick
                tt = tt + 1
                midi.update_time(1)
        
        # Now ramp down from max to start of next seg
        ticksToNextSegmentFromHere = int(96.0 * (s.duration-whenMaxVolume))
        if(ticksToNextSegmentFromHere > 0):
            howMuchVolumeToDecreasePerTick = float(linearMaxVolume - linearNextStartVolume)/float(ticksToNextSegmentFromHere)
            for ticks in xrange(ticksToNextSegmentFromHere):
                curVol = curVol - howMuchVolumeToDecreasePerTick
                if curVol < 0:
                    curVol = 0
                midi.continuous_controller(channel, 7 ,int(curVol))
                tt = tt + 1
                midi.update_time(1)

        # Account for rounding error if any
        midi.update_time(int(96.0*s.duration)-tt)

        # Send the note off
        for note in xrange(12):
            midi.note_off(channel=channel, note=0x3C+note)
            midi.update_time(0)

    midi.update_time(0)
    midi.end_of_track() 
    midi.eof()

        

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = kernels
#!/usr/bin/env python
# encoding: utf=8

"""
kernels.py

Take a whole directory of audio files and smash them together, by
beat, with a fairly simple algorithm. Demonstrates the use of 
deferred audio file loading used in conjunction with render_serially(),
which allow one to remix countless files without running out of memory
too soon.

Originally by Adam Lindsay, 2000-05-05.
"""

import os, sys, os.path
import time
from math import sqrt

import echonest.remix.audio as audio

usage = """
Usage: 
    python kernels.py <inputDirectory> <outputFilename> <beats>

Example:
    python kernels.py /path/to/mp3s popped.mp3 320
"""

SLEEPTIME = 0.5

def main(num_beats, directory, outfile):
    # register the two special effects we need. Since we only make 
    #  AudioQuanta shorter, TimeTruncate is a good choice.
    aud = []
    ff = os.listdir(directory)
    for f in ff:
        # collect the files
        if f.rsplit('.', 1)[1].lower() in ['mp3', 'aif', 'aiff', 'aifc', 'wav']:
            # the new defer kwarg doesn't load the audio until needed
            filename = os.path.join(directory, f)
            aud.append(audio.LocalAudioFile(filename, defer= True))
        # mind the rate limit
    
    num_files = len(aud)
    
    print >> sys.stderr, "Sorting files by key..."
    # sort by key signature: with enough files, it'll sound 
    # like it's always going up in pitch
    aud.sort(key=keysig)
    
    x = audio.AudioQuantumList()
    
    print >> sys.stderr, "Assembling beats.",
    for w in range(num_beats):
        print >> sys.stderr, '.',
        
        # cycle through the audio files (with a different period)
        ssong = aud[w%(num_files-1)].analysis
        
        # cycle through the beats
        s = ssong.beats[w%len(ssong.beats)]
        
        # run an accelerando, and truncate the beats if the reference is shorter
        new_dur = pow(2, -3.0 * w / num_beats)
        if new_dur < s.duration:
            shorter = audio.TimeTruncateLength(new_dur)
            s = shorter(s)
        
        # sort-of normalize based on overall track volume with a crescendo
        level_change = audio.LevelDB(-15 - ssong.loudness + (6.0 * w / num_beats))
        s = level_change(s)
        
        # cycle through the songs (out of phase with 's')
        tsong = aud[(w-1)%num_files].analysis
        
        # cycle through the beats (out of phase)
        t = tsong.beats[w%len(tsong.beats)]
        
        # have a more dramatic volume change
        level_change = audio.LevelDB(-18 - tsong.loudness + (9.0 * w / num_beats))
        t = level_change(t)
        # also note that there will be significant overlap of the un-truncated 't' beats 
        #  by the end, making things louder overall
        
        # glue the two beats together
        x.append(audio.Simultaneous([s, t]))
        
    print >> sys.stderr, "\nStarting rendering pass..."
    
    then = time.time()
    # call render_sequentially() with no arguments, and then it calls itself with
    #  contextual arguments for each source, for each AudioQuantum. It's a lot of
    #  tree-walking, but each source file gets loaded once (and takes itself from)
    #  memory when its rendering pass finishes.
    x.render().encode(outfile)
    
    print >> sys.stderr, "%f sec for rendering" % (time.time() - then,)
    
    print >> sys.stderr, "Outputting XML: each source makes an API call for its metadata."

def keysig(audiofile):
    return int(audiofile.analysis.key['value'])

if __name__ == '__main__':
    try:
        directory = sys.argv[-3]
        outfile = sys.argv[-2]
        num_beats = int(sys.argv[-1])
    except:
        print usage
        sys.exit(-1)
    main(num_beats, directory, outfile)


########NEW FILE########
__FILENAME__ = multitest
#!/usr/bin/env python
# encoding: utf=8

"""
multitest.py

Take a whole directory of audio files and smash them together, by
beat, with a fairly simple algorithm. Demonstrates the use of 
deferred audio file loading used in conjunction with render_serially(),
which allow one to remix countless files without running out of memory
too soon.

Originally by Adam Lindsay, 2000-05-05.
"""

import os, sys
import time
from math import sqrt

from echonest.remix import audio

usage = """
Usage: 
    python multitest.py <inputDirectory> <outputFilename> <beats>

Example:
    python multitest.py ../music mashedbeats.mp3 40
"""

def main(num_beats, directory, outfile):
    
    aud = []
    ff = os.listdir(directory)
    for f in ff:
        # collect the files
        if f.rsplit('.', 1)[1].lower() in ['mp3', 'aif', 'aiff', 'aifc', 'wav']:
            aud.append(audio.LocalAudioFile(os.path.join(directory,f)))
            # mind the rate limit
    
    num_files = len(aud)
    x = audio.AudioQuantumList()
    
    print >> sys.stderr, "Assembling beats.",
    for w in range(num_beats):
        print >> sys.stderr, '.',
        ssong = aud[w%num_files].analysis
        s = ssong.beats[w%len(ssong.beats)]
        tsong = aud[(w-1)%num_files].analysis
        t = tsong.beats[w%len(tsong.beats)]
        
        x.append(audio.Simultaneous([s,t]))
    
    print >> sys.stderr, "\nStarting rendering pass..."
    
    then = time.time()
    # call render_sequentially() with no arguments, and then it calls itself with
    #  contextual arguments for each source, for each AudioQuantum. It's a lot of
    #  tree-walking, but each source file gets loaded once (and takes itself from)
    #  memory when its rendering pass finishes.
    x.render().encode(outfile)
    
    print >> sys.stderr, "%f sec for rendering" % (time.time() - then,)

if __name__ == '__main__':
    try:
        directory = sys.argv[-3]
        outfile = sys.argv[-2]
        num_beats = int(sys.argv[-1])
    except:
        print usage
        sys.exit(-1)
    main(num_beats, directory, outfile)


########NEW FILE########
__FILENAME__ = multivideo
#!/usr/bin/env python
# encoding: utf=8
"""
multivideo.py

Take a whole directory of video files and smash them together, by
beat, with a fairly simple algorithm.

By Ben Lacker, based on multitest.py by Adam Lindsay.
"""
import os, sys
from math import sqrt

from echonest.remix import audio, video

usage = """
Usage: 
    python multivideo.py <inputSong> <inputDirectory> <outputFilename>

Example:
    python multivideo.py ../music/SingleLadies.mp3 ../videos mashedbeats.mpg
"""

def main(infile, directory, outfile):
    afile = audio.LocalAudioFile(infile)
    av = []
    ff = os.listdir(directory)
    for f in ff:
        # collect the files
        if f.rsplit('.', 1)[1].lower() in ['mp3', 'aif', 'aiff', 'aifc', 'wav', 'mpg', 'flv', 'mov', 'mp4']:
            av.append(video.loadav(os.path.join(directory,f)))
    num_files = len(av)
    # not sure the best way to handle these settings
    newv = video.EditableFrames(settings=av[0].video.settings)
    print >> sys.stderr, "Assembling beats.",
    for i, beat in enumerate(afile.analysis.beats):
        print >> sys.stderr, '.',
        vid = av[i%num_files]
        if beat.end > vid.audio.duration:
            # do something smart
            continue
        newv += vid.video[beat]
    outav = video.SynchronizedAV(audio=afile, video=newv)
    outav.save(outfile)

if __name__ == '__main__':
    try:
        infile = sys.argv[-3]
        directory = sys.argv[-2]
        outfile = sys.argv[-1]
    except:
        print usage
        sys.exit(-1)
    main(infile, directory, outfile)

########NEW FILE########
__FILENAME__ = one
#!/usr/bin/env python
# encoding: utf=8
"""
one.py

Digest only the first beat of every bar.

By Ben Lacker, 2009-02-18.
"""
import echonest.remix.audio as audio

usage = """
Usage: 
    python one.py <input_filename> <output_filename>

Example:
    python one.py EverythingIsOnTheOne.mp3 EverythingIsReallyOnTheOne.mp3
"""

def main(input_filename, output_filename):
    audiofile = audio.LocalAudioFile(input_filename)
    bars = audiofile.analysis.bars
    collect = audio.AudioQuantumList()
    for bar in bars:
        collect.append(bar.children()[0])
    out = audio.getpieces(audiofile, collect)
    out.encode(output_filename)

if __name__ == '__main__':
    import sys
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename)

########NEW FILE########
__FILENAME__ = quanta
#!/usr/bin/env python
# encoding: utf=8

"""
quanta.py

Insert silences between a song's segments, tatums, beats, or sections.
Demonstrates the Remix API's handling of audio quanta.

By Ben Lacker 2009-3-4, updated by Thor Kell, 2012-9-26
"""
import sys

import echonest.remix.audio as audio

usage = """
Usage: 
    python quanta.py <segments|tatums|beats|bars|sections> <inputfilename> <outputfilename> [e]

Example:
    python quanta.py beats SingleLadies.mp3 SingleLadiesBeats.mp3
    
The 'e' flag, inserts a silence equal in duration to the preceding audio quantum.
Otherwise, each silence is one second long.
"""

ACCEPTED_UNITS = ["segments", "tatums", "beats", "bars", "sections"]

def main(input_filename, output_filename, units, equal_silence):
    audio_file = audio.LocalAudioFile(input_filename)   
    chunks = audio_file.analysis.__getattribute__(units)
    num_channels = audio_file.numChannels
    sample_rate = audio_file.sampleRate
    if equal_silence:
        new_shape = ((audio_file.data.shape[0] * 2) + 100000,
                        audio_file.data.shape[1])
    else:
        new_shape = (audio_file.data.shape[0]+(len(chunks) * 44100) + 10000,
                        audio_file.data.shape[1])
    out = audio.AudioData(shape=new_shape, sampleRate=sample_rate, numChannels=num_channels)

    for chunk in chunks:
        chunk_data = audio_file[chunk]
        if equal_silence:
            silence_shape = chunk_data.data.shape
        else:
            silence_shape = (44100, audio_file.data.shape[1])
        silence = audio.AudioData(shape=silence_shape, sampleRate=sample_rate, numChannels=num_channels)
        silence.endindex = silence.data.shape[0]

        out.append(chunk_data)
        out.append(silence)
    out.encode(output_filename)

if __name__ == '__main__':
    try:
        units = sys.argv[1]
        input_filename = sys.argv[2]
        output_filename = sys.argv[3]
        if len(sys.argv) == 5:
            equal_silence = True
        else:
            equal_silence = False
    except:
        print usage
        sys.exit(-1)
    if not units in ACCEPTED_UNITS:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename, units, equal_silence)

########NEW FILE########
__FILENAME__ = reverse
#!/usr/bin/env python
# encoding: utf=8

"""
reverse.py

Reverse the beats or segments of a song.

Originally created by Robert Ochshorn on 2008-06-11.  Refactored by
Joshua Lifton 2008-09-07.
"""

import echonest.remix.audio as audio

usage = """
Usage: 
    python reverse.py <beats|segments> <inputFilename> <outputFilename.wav>

Example:
    python reverse.py beats YouCanCallMeAl.mp3 AlMeCallCanYou.mp3
"""

def main(toReverse, inputFilename, outputFilename):
    audioFile = audio.LocalAudioFile(inputFilename)
    if toReverse == 'beats' :
        chunks = audioFile.analysis.beats
    elif toReverse == 'segments' :
        chunks = audioFile.analysis.segments
    else :
        print usage
        return
    chunks.reverse()
    reversedAudio = audio.getpieces(audioFile, chunks)
    reversedAudio.encode(outputFilename)

if __name__ == '__main__':
    import sys
    try :
        toReverse = sys.argv[1]
        inputFilename = sys.argv[2]
        outputFilename = sys.argv[3]
    except :
        print usage
        sys.exit(-1)
    if not toReverse in ["beats", "segments"]:
        print usage
        sys.exit(-1)
    main(toReverse, inputFilename, outputFilename)

########NEW FILE########
__FILENAME__ = save
#!/usr/bin/env python
# encoding: utf=8
"""
save.py

Save an Echo Nest analysis as a local file. You can save analysis by using .save()
You can then load them by simply calling audio.LocalAudioFile('the_file.analysis.en')

Note that save() saves to the same location as the initial file, and 
creates a corresponding .wav file.  Moving the .wav file will break things!

By Thor Kell, 10-2012
"""

usage = """
Usage: 
    python save.py <input_filename>

Example:
    python save.py SaveMe.mp3 
"""

import echonest.remix.audio as audio

def main(input_filename):
    audiofile = audio.LocalAudioFile(input_filename)
    audiofile.save()
    print "Saved anaylsis for %s" % input_filename


if __name__ == '__main__':
    import sys
    try:
        input_filename = sys.argv[1]
    except: 
        print usage
        sys.exit(-1)
    main(input_filename)


########NEW FILE########
__FILENAME__ = tonic
#!/usr/bin/env python
# encoding: utf=8

"""
tonic.py

Digest all beats, tatums, or bars that start in the key of the song.
Demonstrates content-based selection filtering via AudioQuantumLists

Originally by Adam Lindsay, 2008-09-15.
Refactored by Thor Kell, 2012-11-01
"""
import echonest.remix.audio as audio

usage = """
Usage: 
    python tonic.py <tatums|beats|bars> <inputFilename> <outputFilename>

Example:
    python tonic.py beats HereComesTheSun.mp3 HereComesTheTonic.mp3
"""

ACCEPTED_UNITS = ["tatums", "beats", "bars"]

def main(units, inputFile, outputFile):
    audiofile = audio.LocalAudioFile(inputFile)
    tonic = audiofile.analysis.key['value']
    
    chunks = audiofile.analysis.__getattribute__(units)
    
    # Get the segments    
    all_segments = audiofile.analysis.segments
    
    # Find tonic segments
    tonic_segments = audio.AudioQuantumList(kind="segment")
    for segment in all_segments:
        pitches = segment.pitches
        if pitches.index(max(pitches)) == tonic:
            tonic_segments.append(segment)

    # Find each chunk that matches each segment
    out_chunks = audio.AudioQuantumList(kind=units) 
    for chunk in chunks:
        for segment in tonic_segments:
            if chunk.start >= segment.start and segment.end >= chunk.start:
                out_chunks.append(chunk)
                break
    
    out = audio.getpieces(audiofile, out_chunks)
    out.encode(outputFile)

if __name__ == '__main__':
    import sys
    try:
        units = sys.argv[-3]
        inputFilename = sys.argv[-2]
        outputFilename = sys.argv[-1]
    except:
        print usage
        sys.exit(-1)
    if not units in ACCEPTED_UNITS:
        print usage
        sys.exit(-1)
    main(units, inputFilename, outputFilename)

########NEW FILE########
__FILENAME__ = sorting
#!/usr/bin/env/python
#encoding: utf=8
"""
sorting.py

Sorts AudioQuanta (bars, beats, tatums, segments) by various qualities, and resynthesizes them.

By Thor Kell, 2012-11-02
"""
import echonest.remix.audio as audio
usage = """
    python sorting.py <bars|beats|tatums|segments> <confidence|duration|loudness>  <input_filename> <output_filename> [reverse]

"""
def main(units, key, input_filename, output_filename):
    audiofile = audio.LocalAudioFile(input_filename)
    chunks = audiofile.analysis.__getattribute__(units)

    # Define the sorting function
    if key == 'duration':
        def sorting_function(chunk):
            return chunk.duration

    if key == 'confidence':
        def sorting_function(chunk):
            if units != 'segments':
                return chunk.confidence
            else:
                # Segments have no confidence, so we grab confidence from the tatum
                return chunk.tatum.confidence

    if key == 'loudness':
        def sorting_function(chunk):
            return chunk.mean_loudness()
    
    sorted_chunks = sorted(chunks, key=sorting_function, reverse=reverse)

    out = audio.getpieces(audiofile, sorted_chunks)
    out.encode(output_filename)

if __name__ == '__main__':
    import sys
    try:
        unit = sys.argv[1]
        key = sys.argv[2]
        input_filename = sys.argv[3]
        output_filename = sys.argv[4]
        if len(sys.argv) == 6 and sys.argv[5] == 'reverse':
            reverse = True  
        else:
            reverse = False    
    except:
        print usage
        sys.exit(-1)
    main(unit, key, input_filename, output_filename)

########NEW FILE########
__FILENAME__ = sorting_pitch
#!/usr/bin/env/python
#encoding: utf=8
"""
sorting_pitch.py

Sorts AudioQuanta (bars, beats, tatums, segments) by the maximum pitch.
Results can be modded by 0-11 to sort relative to C, C#, D, D#, etc.

By Thor Kell, 2012-11-02
"""

import echonest.remix.audio as audio
usage = """
    python sorting_pitch.py <bars|beats|tatums|segments> <0-11> <input_filename> <output_filename> [reverse]

"""
def main(units, key, input_filename, output_filename):
    audiofile = audio.LocalAudioFile(input_filename)
    chunks = audiofile.analysis.__getattribute__(units)
    key = int(key)
    
    def sorting_function(chunk):
        pitches = chunk.mean_pitches()
        return pitches.index(max(pitches)) - key % 12

    sorted_chunks = sorted(chunks, key=sorting_function, reverse=reverse)

    out = audio.getpieces(audiofile, sorted_chunks)
    out.encode(output_filename)

if __name__ == '__main__':
    import sys
    try:
        unit = sys.argv[1]
        key = sys.argv[2]
        input_filename = sys.argv[3]
        output_filename = sys.argv[4]
        if len(sys.argv) == 6 and sys.argv[5] == 'reverse':
            reverse = True  
        else:
            reverse = False

    except:
        print usage
        sys.exit(-1)
    main(unit, key, input_filename, output_filename)

########NEW FILE########
__FILENAME__ = sorting_timbre
#!/usr/bin/env/python
#encoding: utf=8
"""
sorting_timbre.py

Sorts AudioQuanta (bars, beats, tatums, segments) by timbral bin (0-11).
By Thor Kell, 2012-11-14
"""

import echonest.remix.audio as audio
usage = """
    python sorting.py <bars|beats|tatums|segments> <0-11> <input_filename> <output_filename> [reverse]

"""
def main(units, timbre_bin, input_filename, output_filename):
    audiofile = audio.LocalAudioFile(input_filename)
    chunks = audiofile.analysis.__getattribute__(units)
    timbre_bin = int(timbre_bin)
    
    # For any chunk, return the timbre value of the given bin
    def sorting_function(chunk):
        timbre = chunk.mean_timbre()
        return timbre[timbre_bin]

    sorted_chunks = sorted(chunks, key=sorting_function, reverse=reverse)

    import pdb
    #pdb.set_trace()

    out = audio.getpieces(audiofile, sorted_chunks)
    out.encode(output_filename)

if __name__ == '__main__':
    import sys
    try:
        unit = sys.argv[1]
        timbre_bin = sys.argv[2]
        input_filename = sys.argv[3]
        output_filename = sys.argv[4]
        if len(sys.argv) == 6 and sys.argv[5] == 'reverse':
            reverse = True  
        else:
            reverse = False

    except:
        print usage
        sys.exit(-1)
    main(unit, timbre_bin, input_filename, output_filename)

########NEW FILE########
__FILENAME__ = step-by-pitch
#!/usr/bin/env python
# encoding: utf=8

"""
step.py

For each bar, take one of the nearest (in timbre) beats 
to the last beat, chosen from all of the beats that fall
on the one. Repeat for all the twos, etc.

The variation parameter, (_v_) means there's a roughly 
one in _v_ chance that the actual next beat is chosen. The 
length is the length in bars you want it to go on.

Originally by Adam Lindsay, 2009-03-10.
Refactored by Thor Kell, 2012-12-12
"""

import random
import numpy
import echonest.remix.audio as audio

usage = """
Usage:
    python step.py inputFilename outputFilename [variation [length]]

variation is the number of near candidates chosen from. [default=4]
length is the number of bars in the final product. [default=40]

Example:
    python step.py Discipline.mp3 Undisciplined.mp3 4 100
"""

def main(infile, outfile, choices=4, bars=40):
    audiofile = audio.LocalAudioFile(infile)
    meter = audiofile.analysis.time_signature['value']
    fade_in = audiofile.analysis.end_of_fade_in
    fade_out = audiofile.analysis.start_of_fade_out

    beats = []
    for b in audiofile.analysis.beats:
        if b.start > fade_in or b.end < fade_out:
            beats.append(b)
    output = audio.AudioQuantumList()
    
    beat_array = []
    for m in range(meter):
        metered_beats = []
        for b in beats:
            if beats.index(b) % meter == m:
                metered_beats.append(b)
        beat_array.append(metered_beats)
    
    # Always start with the first beat
    output.append(beat_array[0][0]);
    for x in range(1, bars * meter):
        meter_index = x % meter
        next_candidates = beat_array[meter_index]

        def sorting_function(chunk, target_chunk=output[-1]):
            timbre = chunk.mean_pitches()
            target_timbre = target_chunk.mean_pitches()
            timbre_distance = numpy.linalg.norm(numpy.array(timbre) - numpy.array(target_timbre))
            return timbre_distance

        next_candidates = sorted(next_candidates, key=sorting_function)
        next_index = random.randint(0, min(choices, len(next_candidates) -1 ))
        output.append(next_candidates[next_index])
    
    out = audio.getpieces(audiofile, output)
    out.encode(outfile)
    

if __name__ == '__main__':
    import sys
    try:
        inputFilename = sys.argv[1]
        outputFilename = sys.argv[2]
        if len(sys.argv) > 3:
            variation = int(sys.argv[3])
        else:
            variation = 4
        if len(sys.argv) > 4:
            length = int(sys.argv[4])
        else:
            length = 40
    except:
        print usage
        sys.exit(-1)
    main(inputFilename, outputFilename, variation, length)

########NEW FILE########
__FILENAME__ = step-by-section
#!/usr/bin/env python
# encoding: utf=8

"""
step.py

For each bar, take one of the nearest (in timbre) beats 
to the last beat, chosen from all of the beats that fall
on the one in this section. Repeat for all the twos, etc.

This version divides things by section, retaining the 
structure and approximate length of the original. The 
variation parameter, (_v_) means there's a roughly 
one in _v_ chance that the actual next beat is chosen. A 
musical M-x dissociated-press.

Originally by Adam Lindsay, 2009-03-10.
Refactored by Thor Kell, 2012-12-12
"""

import random
import numpy
import echonest.remix.audio as audio

usage = """
Usage:
    python step.py inputFilename outputFilename [variation]

variation is the number of near candidates chosen from. [default=4]

Example:
    python step.py Discipline.mp3 Undisciplined.mp3 4 
"""

def main(infile, outfile, choices=4):
    audiofile = audio.LocalAudioFile(infile)
    meter = audiofile.analysis.time_signature['value']
    sections = audiofile.analysis.sections
    output = audio.AudioQuantumList()

    for section in sections:
        beats = []
        bars = section.children()
        for bar in bars:
            beats.extend(bar.children())
    
        beat_array = []
        for m in range(meter):
            metered_beats = []
            for b in beats:
                if beats.index(b) % meter == m:
                    metered_beats.append(b)
            beat_array.append(metered_beats)

        # Always start with the first beat
        output.append(beat_array[0][0]);
        for x in range(1, len(bars) * meter):
            meter_index = x % meter
            next_candidates = beat_array[meter_index]

            def sorting_function(chunk, target_chunk=output[-1]):
                timbre = chunk.mean_timbre()
                target_timbre = target_chunk.mean_timbre()
                timbre_distance = numpy.linalg.norm(numpy.array(timbre) - numpy.array(target_timbre))
                return timbre_distance

            next_candidates = sorted(next_candidates, key=sorting_function)
            next_index = random.randint(0, min(choices, len(next_candidates) - 1))
            output.append(next_candidates[next_index])

    out = audio.getpieces(audiofile, output)
    out.encode(outfile)
    

if __name__ == '__main__':
    import sys
    try:
        inputFilename = sys.argv[1]
        outputFilename = sys.argv[2]
        if len(sys.argv) > 3:
            variation = int(sys.argv[3])
        else:
            variation = 4
    except:
        print usage
        sys.exit(-1)
    main(inputFilename, outputFilename, variation)

########NEW FILE########
__FILENAME__ = step
#!/usr/bin/env python
# encoding: utf=8

"""
step.py

For each bar, take one of the nearest (in timbre) beats 
to the last beat, chosen from all of the beats that fall
on the one. Repeat for all the twos, etc.

The variation parameter, (_v_) means there's a roughly 
one in _v_ chance that the actual next beat is chosen. The 
length is the length in bars you want it to go on.

Originally by Adam Lindsay, 2009-03-10.
Refactored by Thor Kell, 2012-12-12
"""

import random
import numpy
import echonest.remix.audio as audio

usage = """
Usage:
    python step.py inputFilename outputFilename [variation [length]]

variation is the number of near candidates chosen from. [default=4]
length is the number of bars in the final product. [default=40]

Example:
    python step.py Discipline.mp3 Undisciplined.mp3 4 100
"""

def main(infile, outfile, choices=4, bars=40):
    audiofile = audio.LocalAudioFile(infile)
    meter = audiofile.analysis.time_signature['value']
    fade_in = audiofile.analysis.end_of_fade_in
    fade_out = audiofile.analysis.start_of_fade_out

    beats = []
    for b in audiofile.analysis.beats:
        if b.start > fade_in or b.end < fade_out:
            beats.append(b)
    output = audio.AudioQuantumList()
    
    beat_array = []
    for m in range(meter):
        metered_beats = []
        for b in beats:
            if beats.index(b) % meter == m:
                metered_beats.append(b)
        beat_array.append(metered_beats)
    
    # Always start with the first beat
    output.append(beat_array[0][0]);
    for x in range(1, bars * meter):
        meter_index = x % meter
        next_candidates = beat_array[meter_index]

        def sorting_function(chunk, target_chunk=output[-1]):
            timbre = chunk.mean_timbre()
            target_timbre = target_chunk.mean_timbre()
            timbre_distance = numpy.linalg.norm(numpy.array(timbre) - numpy.array(target_timbre))
            return timbre_distance

        next_candidates = sorted(next_candidates, key=sorting_function)
        next_index = random.randint(0, min(choices, len(next_candidates) - 1))
        output.append(next_candidates[next_index])
    
    out = audio.getpieces(audiofile, output)
    out.encode(outfile)
    

if __name__ == '__main__':
    import sys
    try:
        inputFilename = sys.argv[1]
        outputFilename = sys.argv[2]
        if len(sys.argv) > 3:
            variation = int(sys.argv[3])
        else:
            variation = 4
        if len(sys.argv) > 4:
            length = int(sys.argv[4])
        else:
            length = 40
    except:
        print usage
        sys.exit(-1)
    main(inputFilename, outputFilename, variation, length)

########NEW FILE########
__FILENAME__ = beatshift
#!/usr/bin/env python
# encoding: utf-8
"""
beatshift.py

Pitchshift each beat based on its position in the bar.
Beat one is unchanged, beat two is shifted down one half step,
beat three is shifted down two half steps, etc.

Created by Ben Lacker on 2009-06-24.
Refactored by Thor Kell on 2013-03-06.
"""
import numpy
import os
import random
import sys
import time

from echonest.remix import audio, modify

usage = """
Usage:
    python beatshift.py <input_filename> <output_filename>
Exampel:
    python beatshift.py CryMeARiver.mp3 CryMeAShifty.mp3
"""

def main(input_filename, output_filename):
    soundtouch = modify.Modify()
    audiofile = audio.LocalAudioFile(input_filename)
    beats = audiofile.analysis.beats
    out_shape = (len(audiofile.data),)
    out_data = audio.AudioData(shape=out_shape, numChannels=1, sampleRate=44100)
    
    for i, beat in enumerate(beats):
        data = audiofile[beat].data
        number = beat.local_context()[0] % 12
        new_beat = soundtouch.shiftPitchSemiTones(audiofile[beat], number*-1)
        out_data.append(new_beat)
    
    out_data.encode(output_filename)

if __name__ == '__main__':
    import sys
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename)

########NEW FILE########
__FILENAME__ = cycle_dirac
#!/usr/bin/env python
# encoding: utf-8
"""
cycle.py

Periodically time-compress and time-stretch the beats in each measure.
Each measure starts fast and ends slow.

Created by Thor Kell on 2013-05-06, based on code by Ben Lacker.
"""
import math
import os
import sys
import dirac
from echonest.remix import audio

usage = """
Usage:
    python cycle.py <input_filename> <output_filename>
Exampel:
    python cycle.py CryMeARiver.mp3 CryCycle.mp3
"""

def main(input_filename, output_filename):
    audiofile = audio.LocalAudioFile(input_filename)
    bars = audiofile.analysis.bars
    collect = []

    for bar in bars:
        bar_ratio = (bars.index(bar) % 4) / 2.0
        beats = bar.children()
        for beat in beats:
            beat_index = beat.local_context()[0]
            ratio = beat_index / 2.0 + 0.5
            ratio = ratio + bar_ratio # dirac can't compress by less than 0.5!
            beat_audio = beat.render()
            scaled_beat = dirac.timeScale(beat_audio.data, ratio)
            ts = audio.AudioData(ndarray=scaled_beat, shape=scaled_beat.shape, 
                            sampleRate=audiofile.sampleRate, numChannels=scaled_beat.shape[1])
            collect.append(ts)

    out = audio.assemble(collect, numChannels=2)
    out.encode(output_filename)

if __name__ == '__main__':
    import sys
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename)


########NEW FILE########
__FILENAME__ = cycle_soundtouch
#!/usr/bin/env python
# encoding: utf-8
"""
cycle.py

Periodically time-compress and time-stretch the beats in each measure.
Each measure starts fast and ends slow.

Created by Ben Lacker on 2009-06-16.
Refactored by Thor Kell on 2013-03-06.
"""
import math
import os
import sys

from echonest.remix import audio, modify

usage = """
Usage:
    python cycle.py <input_filename> <output_filename>
Exampel:
    python cycle.py CryMeARiver.mp3 CryCycle.mp3
"""

def main(input_filename, output_filename):

    audiofile = audio.LocalAudioFile(input_filename)
    soundtouch = modify.Modify()
    beats = audiofile.analysis.beats
    collect = []

    for beat in beats:
        context = beat.local_context()
        ratio = (math.cos(math.pi * 2 * context[0]/float(context[1])) / 2) + 1
        new = soundtouch.shiftTempo(audiofile[beat], ratio)
        collect.append(new)
    
    out = audio.assemble(collect)
    out.encode(output_filename)

if __name__ == '__main__':
    import sys
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename)

########NEW FILE########
__FILENAME__ = simple_stretch
#!/usr/bin/env python
# encoding: utf-8
"""
simple_stretch.py

Compress or exapand the entire track, beat by beat.  

Created by Thor Kell on 2013-11-18
"""
import math
import os
import sys
import dirac
from echonest.remix import audio

usage = """
Usage:
    python simple_stretch.py <input_filename> <output_filename> <ratio> 
Example:
    python simple_stretch.py CryMeARiver.mp3 StrechMeARiver.mp3
Notes:
    Ratio must be greater than 0.5
"""

def main(input_filename, output_filename, ratio):
    audiofile = audio.LocalAudioFile(input_filename)
    beats = audiofile.analysis.beats
    collect = []

    for beat in beats:
        beat_audio = beat.render()
        scaled_beat = dirac.timeScale(beat_audio.data, ratio)
        ts = audio.AudioData(ndarray=scaled_beat, shape=scaled_beat.shape, 
                        sampleRate=audiofile.sampleRate, numChannels=scaled_beat.shape[1])
        collect.append(ts)

    out = audio.assemble(collect, numChannels=2)
    out.encode(output_filename)

if __name__ == '__main__':
    import sys
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
        ratio = float(sys.argv[3])
        if ratio < 0.5:
            print "Error:  Ratio must be greater than 0.5!"
            sys.exit(-1)
    except:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename, ratio)

########NEW FILE########
__FILENAME__ = summary
#!/usr/bin/env python
# encoding: utf=8

"""
summary.py

Digest only the first or only the second tatum of every beat.

By Ben Lacker, 2009-02-18.
"""
import sys
import echonest.remix.audio as audio

usage = """
Usage: 
    python summary.py [and] <input_filename> <output_filename>

Example:
    python summary.py RichGirl.mp3 RichSummary.mp3
"""


def main(input_filename, output_filename, index):
    audio_file = audio.LocalAudioFile(input_filename)
    beats = audio_file.analysis.beats
    collect = audio.AudioQuantumList()
    for beat in beats:
        tata = beat.children()
        if len(tata)>1:
            tat = tata[index]
        else:
            tat = tata[0]
        collect.append(tat)
    out = audio.getpieces(audio_file, collect)
    out.encode(output_filename)


if __name__ == '__main__':
    try:
        if sys.argv[1]=='and':
            index = 1
        else:
            index = 0
        input_filename = sys.argv[-2]
        output_filename = sys.argv[-1]
    except:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename, index)

########NEW FILE########
__FILENAME__ = swinger
#!/usr/bin/env python
# encoding: utf=8

"""
swinger.py
(name suggested by Jason Sundram)

Make your music swing (or un-swing).
Created by Tristan Jehan.
"""

from optparse import OptionParser
import os, sys
import dirac

from echonest.remix.audio import LocalAudioFile, AudioData
from echonest.remix.action import render, Playback, display_actions

def do_work(track, options):
    
    verbose = bool(options.verbose)
    
    # swing factor
    swing = float(options.swing)
    if swing < -0.9: swing = -0.9
    if swing > +0.9: swing = +0.9
    
    if swing == 0:
        return Playback(track, 0, track.analysis.duration)
    
    beats = track.analysis.beats
    offset = int(beats[0].start * track.sampleRate)

    # compute rates
    rates = []
    for beat in beats[:-1]:
        # put swing
        if 0 < swing:
            rate1 = 1+swing
            dur = beat.duration/2.0
            stretch = dur * rate1
            rate2 = (beat.duration-stretch)/dur
        # remove swing
        else:
            rate1 = 1 / (1+abs(swing))
            dur = (beat.duration/2.0) / rate1
            stretch = dur * rate1
            rate2 = (beat.duration-stretch)/(beat.duration-dur)
        # build list of rates
        start1 = int(beat.start * track.sampleRate)
        start2 = int((beat.start+dur) * track.sampleRate)
        rates.append((start1-offset, rate1))
        rates.append((start2-offset, rate2))
        if verbose:
            args = (beats.index(beat), dur, beat.duration-dur, stretch, beat.duration-stretch)
            print "Beat %d — split [%.3f|%.3f] — stretch [%.3f|%.3f] seconds" % args
    
    # get audio
    vecin = track.data[offset:int(beats[-1].start * track.sampleRate),:]
    # time stretch
    if verbose: 
        print "\nTime stretching..."
    vecout = dirac.timeScale(vecin, rates, track.sampleRate, 0)
    # build timestretch AudioData object
    ts = AudioData(ndarray=vecout, shape=vecout.shape, 
                    sampleRate=track.sampleRate, numChannels=vecout.shape[1], 
                    verbose=verbose)
    # initial and final playback
    pb1 = Playback(track, 0, beats[0].start)
    pb2 = Playback(track, beats[-1].start, track.analysis.duration-beats[-1].start)

    return [pb1, ts, pb2]

def main():
    usage = "usage: %s [options] <one_single_mp3>" % sys.argv[0]
    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--swing", default=0.33, help="swing factor default=0.33")
    parser.add_option("-v", "--verbose", action="store_true", help="show results on screen")
    
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        return -1
    
    verbose = options.verbose
    track = None
    
    track = LocalAudioFile(args[0], verbose=verbose)
    if verbose:
        print "Computing swing . . ."
    # this is where the work takes place
    actions = do_work(track, options)
    
    if verbose:
        display_actions(actions)
    
    # Send to renderer
    name = os.path.splitext(os.path.basename(args[0]))
    sign = ('-','+')[float(options.swing) >= 0]
    name = name[0] + '_swing' + sign + str(int(abs(float(options.swing))*100)) +'.mp3'
    name = name.replace(' ','') 
    name = os.path.join(os.getcwd(), name) # TODO: use sys.path[0] instead of getcwd()?
    
    if verbose:
        print "Rendering... %s" % name
    render(actions, name, verbose=verbose)
    if verbose:
        print "Success!"
    return 1


if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        print e

########NEW FILE########
__FILENAME__ = videolizer
#!/usr/bin/env python
# encoding: utf=8

"""
videolizer.py

Sync up some video sequences to a song.
Created by Tristan Jehan.
"""
import echonest.remix.audio as aud
from sys import stdout
import subprocess
import random
import shutil
import glob
import sys
import os

VIDEO_FOLDER = 'videos'
IMAGE_FOLDER = 'images'
AUDIO_FOLDER = 'audio'
AUDIO_EXAMPLE = '../music/Tracky_Birthday-Newish_Disco.mp3'
TMP_FOLDER = IMAGE_FOLDER+'/tmp'
VIDEO_CSV = 'video.csv'
EXTENSION = '.mp4'
TMP_CSV = 'tmp.csv'
NUM_BEATS_RANGE = (16,32)
EPSILON = 10e-9
BITRATE = 1000000
FPS = 30

def display_in_place(line):
    stdout.write('\r%s' % line)
    stdout.flush()

def time_to_frame(time):
    return int(time * FPS)

def frame_to_time(frame):
    return float(frame) / float(FPS)

def process_videos(folder, csv_file):
    files = glob.glob(folder+'/*'+EXTENSION)
    print "Converting videos to images..."
    for f in files:
        print "> %s..." % f
        convert_video_to_images(f, IMAGE_FOLDER)
    print "Extracting audio from video..."
    for f in files:
        print "> %s..." % f
        convert_video_to_audio(f)
    print "Analyzing video beats..."
    if os.path.exists(TMP_CSV):
        os.remove(TMP_CSV)
    for f in files:
        print "> %s..." % f
        analyze_video_beats(f, TMP_CSV)
    os.rename(TMP_CSV, csv_file)

def video_to_audio(video):
    if not os.path.exists(AUDIO_FOLDER):
        os.makedirs(AUDIO_FOLDER)
    ext = os.path.splitext(video)[1]
    audio = video.replace(ext,'.m4a').replace(VIDEO_FOLDER, AUDIO_FOLDER)
    return audio

def convert_video_to_images(video, output):
    ext = os.path.splitext(video)[1]
    name = os.path.basename(video.replace(ext,'')).split('.')[0]
    folder = output+'/'+name
    if not os.path.exists(folder):
        os.makedirs(folder)
        command = 'en-ffmpeg -loglevel panic -i \"%s\" -r %d -f image2 \"%s/%%05d.png\"' % (video, FPS, folder)
        cmd = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        cmd.wait()

def convert_video_to_audio(video):
    audio = video_to_audio(video)
    if not os.path.exists(audio):
        command = 'en-ffmpeg -loglevel panic -y -i \"%s\" -vn -acodec copy \"%s\"' % (video, audio)
        cmd = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        cmd.wait()

def analyze_video_beats(video, csv_file):
    audio = video_to_audio(video)
    track = aud.LocalAudioFile(audio, verbose=True)
    beats = track.analysis.beats
    mini = 0
    maxi = sys.maxint
    l = video.split('.')
    if len(l) > 3:
        if l[-3].isdigit() and int(l[-3]) is not 0:
            mini = int(l[-3])
        if l[-2].isdigit() and int(l[-2]) is not 0:
            maxi = int(l[-2])
    line = video
    for beat in beats:
        if mini < beat.start and beat.start < maxi:
            line = line+',%.5f' % beat.start
    fid = open(csv_file, 'a')
    fid.write(line+'\n')
    fid.close()

def crop_audio(audio_file, beats):
    ext = os.path.splitext(audio_file)[1]
    name = os.path.basename(audio_file)
    output = AUDIO_FOLDER+'/'+name.replace(ext,'.cropped'+ext)
    if not os.path.exists(output):
        print "Cropping audio to available beats..."
        duration = float(beats[-1].start) - float(beats[0].start)
        command = 'en-ffmpeg -loglevel panic -y -ss %f -t %f -i \"%s\" \"%s\"' % (float(beats[0].start), duration, audio_file, output)
        cmd = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        cmd.wait()
    return output

def combine_audio_and_images(audio_file, images_folder, output):
    print "Making final video out of image sequences..."
    tmp_video = VIDEO_FOLDER+'/tmp'+EXTENSION
    command = 'en-ffmpeg -loglevel panic -f image2 -r %d -i \"%s/%%05d.png\" -b %d \"%s\"' % (FPS, images_folder, BITRATE, tmp_video)
    cmd = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    cmd.wait()
    print "Combining final video with cropped audio..."
    command = 'en-ffmpeg -loglevel panic -vcodec copy -y -i \"%s\" -i \"%s\" \"%s\"' % (audio_file, tmp_video, output)
    cmd = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    cmd.wait()
    os.remove(tmp_video)

def select_sequences(number_beats, data):
    sequences = []
    count_beats = 0
    keys = data.keys()
    while count_beats < number_beats:
        video = random.choice(keys)
        nbeats = random.randint(NUM_BEATS_RANGE[0], NUM_BEATS_RANGE[1])
        vbeats = data[video]
        if nbeats >= len(vbeats):
            nbeats = len(vbeats)
        if count_beats + nbeats > number_beats:
            nbeats = number_beats - count_beats
        start = random.randint(0, len(vbeats)-nbeats-1)
        count_beats += nbeats
        sequences.append((video, start, nbeats))
    return sequences

def resample_sequences(source_beats, sequences, data, tmp_folder):
    print "Building new video as a sequence of images..."
    audio_beats = [float(b.start) for b in source_beats]
    jitter = 0
    counter_beats = 0
    counter_images = 0
    for seq in sequences:
        ext = os.path.splitext(seq[0])[1]
        name = os.path.basename(seq[0].replace(ext,'')).split('.')[0]
        src_folder = IMAGE_FOLDER+'/'+name
        video_beats = data[seq[0]]
        video_time = float(video_beats[seq[1]])
        audio_time = float(audio_beats[counter_beats])
        for beats in zip(audio_beats[counter_beats+1:counter_beats+seq[2]+1], video_beats[seq[1]+1:seq[1]+seq[2]+1]):
            audio_beat_dur = beats[0] - audio_time
            video_beat_dur = beats[1] - video_time    
            rate = audio_beat_dur / video_beat_dur
            num_frames_float = video_beat_dur * rate * FPS
            num_frames = int(num_frames_float)
            jitter += num_frames_float - num_frames
            if jitter >= 1-EPSILON:
                num_frames += int(jitter)
                jitter -= int(jitter)
            for i in range(0, num_frames):
                counter_images += 1
                src = '%s/%05d.png' % (src_folder, time_to_frame(video_time + frame_to_time(i/rate)))
                dst =  '%s/%05d.png' % (tmp_folder, counter_images)
                display_in_place('Copying %s to %s' % (src, dst))
                shutil.copyfile(src, dst)
            video_time = beats[1] - frame_to_time(jitter)
            audio_time = beats[0]
        counter_beats += seq[2]
    print

def process_csv(csv_file):
    data = {}
    fid = open(csv_file,'r')
    for line in fid:
        l = line.strip().split(',')
        data[l[0]] = [float(v) for v in l[1:]]
    fid.close()
    return data

def videolize(file_in, file_ou):
    if not os.path.exists(VIDEO_CSV):
        process_videos(VIDEO_FOLDER, VIDEO_CSV)
    data = process_csv(VIDEO_CSV)
    track = aud.LocalAudioFile(file_in, verbose=True)
    beats = track.analysis.beats
    if os.path.exists(TMP_FOLDER):
        shutil.rmtree(TMP_FOLDER)
    os.makedirs(TMP_FOLDER)
    sequences = select_sequences(len(beats)-1, data)
    resample_sequences(beats, sequences, data, TMP_FOLDER)
    file_cropped = crop_audio(file_in, beats)
    combine_audio_and_images(file_cropped, TMP_FOLDER, file_ou)
    shutil.rmtree(TMP_FOLDER)

def main():
    usage = "usage:\tpython %s <file.mp3>\ntry:\tpython %s %s\
    \nnote:\tvideo filename format is name.<time_start>.<time_end>.mp4\n\
    \twith <time_start> and <time_end> in seconds, where 0 means ignore" % (sys.argv[0], sys.argv[0], AUDIO_EXAMPLE)
    if len(sys.argv) < 2:
        print usage
        return -1
    file_in = sys.argv[1]
    ext = os.path.splitext(file_in)[1]
    name = os.path.basename(file_in.replace(ext,''))
    file_ou = name+EXTENSION
    videolize(file_in, file_ou)

if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        print e

########NEW FILE########
__FILENAME__ = vafroma
#!/usr/bin/env python
# encoding: utf=8

"""
vafroma.py

Re-synthesize video A using the segments of song A.

By Ben Lacker, P. Lamere
"""
import numpy
import sys
import time
import echonest.remix.audio as audio
import echonest.remix.video as video
import echonest.remix.modify as modify

usage="""
Usage:
    python vafroma.py <input_filename>

Example:
    python vafroma.py BillieJeanMusicVideo.mp4
"""


dur_weight = 1000
#dur_weight = 100
timbre_weight = .001
pitch_weight = 10
loudness_weight = 1

class AfromA(object):
    def __init__(self, input_filename, output_filename):
        self.av = video.loadav(input_filename)
        self.segs = self.av.audio.analysis.segments
        self.output_filename = output_filename

    def get_distance_from(self, seg):
        distances = []
        for a in self.segs:
            ddur = numpy.square(seg.duration - a.duration)
            dloud = numpy.square(seg.loudness_max - a.loudness_max)

            timbre_diff = numpy.subtract(seg.timbre, a.timbre)
            dtimbre = (numpy.sum(numpy.square(timbre_diff)))

            pitch_diff = numpy.subtract(seg.pitches, a.pitches)
            dpitch = (numpy.sum(numpy.square(pitch_diff)))

            #print dur_weight * ddur, timbre_weight * dtimbre, \
            #      pitch_weight * dpitch, loudness_weight * dloud
            distance =    dur_weight * ddur \
                        + loudness_weight * dloud \
                        + timbre_weight * dtimbre \
                        + pitch_weight * dpitch;
            distances.append(distance)

        return distances
            

    def run(self):
        st = modify.Modify()
        collect = audio.AudioQuantumList()
        for a in self.segs:
            seg_index = a.absolute_context()[0]

            distances = self.get_distance_from(a)

            distances[seg_index] = sys.maxint

            match_index = distances.index(min(distances))
            match = self.segs[match_index]
            print seg_index, match_index
            # make the length of the new seg match the length
            # of the old seg
            collect.append(match)
        out = video.getpieces(self.av, collect)
        out.save(self.output_filename)

def main():
    try:
        input_filename = sys.argv[1]
        if len(sys.argv) > 2:
            output_filename = sys.argv[2]
        else:
            output_filename = "aa_" + input_filename
    except:
        print usage
        sys.exit(-1)
    AfromA(input_filename, output_filename).run()


if __name__=='__main__':
    tic = time.time()
    main()
    toc = time.time()
    print "Elapsed time: %.3f sec" % float(toc-tic)

########NEW FILE########
__FILENAME__ = vafroma2
#!/usr/bin/env python
# encoding: utf=8

"""
vafroma2.py

Re-synthesize video A using the segments of song A.
Same as vafroma.py, but avoids re-using segments.

By Ben Lacker, P. Lamere
"""
import numpy
import sys
import time
import echonest.remix.audio as audio
import echonest.remix.video as video
import echonest.remix.modify as modify

usage="""
Usage:
    python vafroma2.py <input_filename>

Example:
    python vafroma2.py BillieJeanMusicVideo.mp4
"""


dur_weight = 1000
#dur_weight = 100
timbre_weight = .001
pitch_weight = 10
loudness_weight = 1

class AfromA(object):
    def __init__(self, input_filename, output_filename):
        self.av = video.loadav(input_filename)
        self.segs = self.av.audio.analysis.segments
        self.output_filename = output_filename

    def get_distance_from(self, seg):
        distances = []
        for a in self.segs:
            ddur = numpy.square(seg.duration - a.duration)
            dloud = numpy.square(seg.loudness_max - a.loudness_max)

            timbre_diff = numpy.subtract(seg.timbre, a.timbre)
            dtimbre = (numpy.sum(numpy.square(timbre_diff)))

            pitch_diff = numpy.subtract(seg.pitches, a.pitches)
            dpitch = (numpy.sum(numpy.square(pitch_diff)))

            #print dur_weight * ddur, timbre_weight * dtimbre, \
            #      pitch_weight * dpitch, loudness_weight * dloud
            distance =    dur_weight * ddur \
                        + loudness_weight * dloud \
                        + timbre_weight * dtimbre \
                        + pitch_weight * dpitch;
            distances.append(distance)

        return distances
            

    def run(self):
        st = modify.Modify()
        collect = audio.AudioQuantumList()
        used = []
        for a in self.segs:
            seg_index = a.absolute_context()[0]

            distances = self.get_distance_from(a)

            distances[seg_index] = sys.maxint
            for u in used:
                distances[u] = sys.maxint

            match_index = distances.index(min(distances))
            match = self.segs[match_index]
            print seg_index, match_index
            # make the length of the new seg match the length
            # of the old seg
            collect.append(match)
            used.append(match_index)
        out = video.getpieces(self.av, collect)
        out.save(self.output_filename)

def main():
    try:
        input_filename = sys.argv[1]
        if len(sys.argv) > 2:
            output_filename = sys.argv[2]
        else:
            output_filename = "aa2_" + input_filename
    except:
        print usage
        sys.exit(-1)
    AfromA(input_filename, output_filename).run()


if __name__=='__main__':
    tic = time.time()
    main()
    toc = time.time()
    print "Elapsed time: %.3f sec" % float(toc-tic)

########NEW FILE########
__FILENAME__ = vafroma3

#!/usr/bin/env python
# encoding: utf=8

"""
vafroma3.py

Re-synthesize video A using the segments of song A.
Tries to use longer sequences of video by boosting the distance neighbors of similar segments.

By Ben Lacker, P. Lamere
"""
import numpy
import sys
import time
import echonest.remix.audio as audio
import echonest.remix.video as video
import echonest.remix.modify as modify

usage="""
Usage:
    python vafroma3.py <input_filename>

Example:
    python vafroma3.py BillieJeanMusicVideo.mp4
"""


dur_weight = 1000
#dur_weight = 100
timbre_weight = .001
pitch_weight = 10
loudness_weight = 1

class AfromA(object):
    def __init__(self, input_filename, output_filename):
        self.av = video.loadav(input_filename)
        self.segs = self.av.audio.analysis.segments
        self.output_filename = output_filename

    def get_distance_from(self, seg):
        distances = []
        for a in self.segs:
            ddur = numpy.square(seg.duration - a.duration)
            dloud = numpy.square(seg.loudness_max - a.loudness_max)

            timbre_diff = numpy.subtract(seg.timbre, a.timbre)
            dtimbre = (numpy.sum(numpy.square(timbre_diff)))

            pitch_diff = numpy.subtract(seg.pitches, a.pitches)
            dpitch = (numpy.sum(numpy.square(pitch_diff)))

            #print dur_weight * ddur, timbre_weight * dtimbre, \
            #      pitch_weight * dpitch, loudness_weight * dloud
            distance =    dur_weight * ddur \
                        + loudness_weight * dloud \
                        + timbre_weight * dtimbre \
                        + pitch_weight * dpitch;
            distances.append(distance)

        return distances
            

    def run(self):
        st = modify.Modify()
        last_index = 0
        collect = audio.AudioQuantumList()
        match_index = -1
        for a in self.segs:
            seg_index = a.absolute_context()[0]

            distances = self.get_distance_from(a)

            distances[seg_index] = sys.maxint

            if match_index < len(distances) -1:
                distances[match_index + 1] *= .3

            match_index = distances.index(min(distances))
            match = self.segs[match_index]
            print seg_index, match_index
            # make the length of the new seg match the length
            # of the old seg
            collect.append(match)
        out = video.getpieces(self.av, collect)
        out.save(self.output_filename)

def main():
    try:
        input_filename = sys.argv[1]
        if len(sys.argv) > 2:
            output_filename = sys.argv[2]
        else:
            output_filename = "aa3_" + input_filename
    except:
        print usage
        sys.exit(-1)
    AfromA(input_filename, output_filename).run()


if __name__=='__main__':
    tic = time.time()
    main()
    toc = time.time()
    print "Elapsed time: %.3f sec" % float(toc-tic)

########NEW FILE########
__FILENAME__ = vafromb
#!/usr/bin/env python
# encoding: utf=8

"""
vafromb.py

Re-synthesize video A using the segments of video B.

By Ben Lacker, 2009-02-24.
"""
import numpy
import sys
import time

from echonest.remix import action, audio, video

usage="""
Usage:
    python vafromb.py <inputfilenameA> <inputfilenameB> <outputfilename> <Mix> [env]

Example:
    python vafromb.py BillieJean.mp4 CryMeARiver.mp4 BillieJeanFromCryMeARiver.mp4 0.9 env

The 'env' flag applies the volume envelopes of the segments of A to those
from B.

Mix is a number 0-1 that determines the relative mix of the resynthesized
song and the original input A. i.e. a mix value of 0.9 yields an output that
is mostly the resynthesized version.

"""

class AfromB(object):
    def __init__(self, input_filename_a, input_filename_b, output_filename):
        "Synchronizes slavebundle on masterbundle, writes to outbundle"
        self.master = video.loadav(input_filename_a)
        # convert slave so it matches master's settings
        converted = video.convertmov(input_filename_b, settings=self.master.video.settings)
        self.slave = video.loadav(converted)
        self.out = output_filename
        
        self.input_a = self.master.audio
        self.input_b = self.slave.audio
        self.segs_a = self.input_a.analysis.segments
        self.segs_b = self.input_b.analysis.segments
        self.output_filename = output_filename
    
    def calculate_distances(self, a):
        distance_matrix = numpy.zeros((len(self.segs_b), 4), dtype=numpy.float32)
        pitch_distances = []
        timbre_distances = []
        loudmax_distances = []
        for b in self.segs_b:
            pitch_diff = numpy.subtract(b.pitches,a.pitches)
            pitch_distances.append(numpy.sum(numpy.square(pitch_diff)))
            timbre_diff = numpy.subtract(b.timbre,a.timbre)
            timbre_distances.append(numpy.sum(numpy.square(timbre_diff)))
            loudmax_diff = b.loudness_begin - a.loudness_begin
            loudmax_distances.append(numpy.square(loudmax_diff))
        distance_matrix[:,0] = pitch_distances
        distance_matrix[:,1] = timbre_distances
        distance_matrix[:,2] = loudmax_distances
        distance_matrix[:,3] = range(len(self.segs_b))
        distance_matrix = self.normalize_distance_matrix(distance_matrix)
        return distance_matrix
    
    def normalize_distance_matrix(self, mat, mode='minmed'):
        """ Normalize a distance matrix on a per column basis.
        """
        if mode == 'minstd':
            mini = numpy.min(mat,0)
            m = numpy.subtract(mat, mini)
            std = numpy.std(mat,0)
            m = numpy.divide(m, std)
            m = numpy.divide(m, mat.shape[1])
        elif mode == 'minmed':
            mini = numpy.min(mat,0)
            m = numpy.subtract(mat, mini)
            med = numpy.median(m)
            m = numpy.divide(m, med)
            m = numpy.divide(m, mat.shape[1])
        elif mode == 'std':
            std = numpy.std(mat,0)
            m = numpy.divide(mat, std)
            m = numpy.divide(m, mat.shape[1])
        return m
    
    def run(self, mix=0.5, envelope=False):
        dur = len(self.input_a.data) + 100000 # another two seconds
        # determine shape of new array. 
        # do everything in mono; I'm not fancy.
        new_shape = (dur,)
        new_channels = 1
        self.input_a = action.make_mono(self.input_a)
        self.input_b = action.make_mono(self.input_b)
        out = audio.AudioData(shape=new_shape, sampleRate=self.input_b.sampleRate, numChannels=new_channels)
        for a in self.segs_a:
            seg_index = a.absolute_context()[0]
            # find best match from segs in B
            distance_matrix = self.calculate_distances(a)
            distances = [numpy.sqrt(x[0]+x[1]+x[2]) for x in distance_matrix]
            match = self.segs_b[distances.index(min(distances))]
            segment_data = self.input_b[match]
            reference_data = self.input_a[a]
            if segment_data.endindex < reference_data.endindex:
                if new_channels > 1:
                    silence_shape = (reference_data.endindex,new_channels)
                else:
                    silence_shape = (reference_data.endindex,)
                new_segment = audio.AudioData(shape=silence_shape,
                                        sampleRate=out.sampleRate,
                                        numChannels=segment_data.numChannels)
                new_segment.append(segment_data)
                new_segment.endindex = len(new_segment)
                segment_data = new_segment
            elif segment_data.endindex > reference_data.endindex:
                index = slice(0, int(reference_data.endindex), 1)
                segment_data = audio.AudioData(None,segment_data.data[index],
                                        sampleRate=segment_data.sampleRate)

            chopvideo = self.slave.video[match] # get editableframes object
            masterchop = self.master.video[a]
            startframe = self.master.video.indexvoodo(a.start) # find start index
            endframe = self.master.video.indexvoodo(a.start + a.duration)
            for i in xrange(len(chopvideo.files)):
                if startframe+i < len(self.master.video.files):
                    self.master.video.files[startframe+i] = chopvideo.files[i]
            last_frame = chopvideo.files[i]
            for i in xrange(len(chopvideo.files), len(masterchop.files)):
                if startframe+i < len(self.master.video.files):
                    self.master.video.files[startframe+i] = last_frame
                
            if envelope:
                # db -> voltage ratio http://www.mogami.com/e/cad/db.html
                linear_max_volume = pow(10.0,a.loudness_max/20.0)
                linear_start_volume = pow(10.0,a.loudness_begin/20.0)
                if(seg_index == len(self.segs_a)-1): # if this is the last segment
                    linear_next_start_volume = 0
                else:
                    linear_next_start_volume = pow(10.0,self.segs_a[seg_index+1].loudness_begin/20.0)
                    pass
                when_max_volume = a.time_loudness_max
                # Count # of ticks I wait doing volume ramp so I can fix up rounding errors later.
                ss = 0
                # Set volume of this segment. Start at the start volume, ramp up to the max volume , then ramp back down to the next start volume.
                cur_vol = float(linear_start_volume)
                # Do the ramp up to max from start
                samps_to_max_loudness_from_here = int(segment_data.sampleRate * when_max_volume)
                if(samps_to_max_loudness_from_here > 0):
                    how_much_volume_to_increase_per_samp = float(linear_max_volume - linear_start_volume)/float(samps_to_max_loudness_from_here)
                    for samps in xrange(samps_to_max_loudness_from_here):
                        try:
                            segment_data.data[ss] *= cur_vol
                        except IndexError:
                            pass
                        cur_vol = cur_vol + how_much_volume_to_increase_per_samp
                        ss = ss + 1
                # Now ramp down from max to start of next seg
                samps_to_next_segment_from_here = int(segment_data.sampleRate * (a.duration-when_max_volume))
                if(samps_to_next_segment_from_here > 0):
                    how_much_volume_to_decrease_per_samp = float(linear_max_volume - linear_next_start_volume)/float(samps_to_next_segment_from_here)
                    for samps in xrange(samps_to_next_segment_from_here):
                        cur_vol = cur_vol - how_much_volume_to_decrease_per_samp
                        try:
                            segment_data.data[ss] *= cur_vol
                        except IndexError:
                            pass
                        ss = ss + 1
            mixed_data = audio.mix(segment_data,reference_data,mix=mix)
            out.append(mixed_data)
        self.master.audio = out
        self.master.save(self.output_filename)

def main():
    try:
        input_filename_a = sys.argv[1]
        input_filename_b = sys.argv[2]
        output_filename = sys.argv[3]
        mix = sys.argv[4]
        if len(sys.argv) == 6:
            env = True
        else:
            env = False
    except Exception:
        print usage
        sys.exit(-1)
    AfromB(input_filename_a, input_filename_b, output_filename).run(mix=mix, envelope=env)

if __name__=='__main__':
    tic = time.time()
    main()
    toc = time.time()
    print "Elapsed time: %.3f sec" % float(toc-tic)

########NEW FILE########
__FILENAME__ = vdissoc
#!/usr/bin/env python
# encoding: utf=8

"""
vdissoc.py

The video version of step-by-section.py.

For each bar, take one of the nearest (in timbre) beats 
to the last beat, chosen from all of the beats that fall
on the one in this section. Repeat for all the twos, etc.

This version divides things by section, retaining the 
structure and approximate length of the original. The 
variation parameter, (_v_) means there's a roughly 
one in _v_ chance that the actual next beat is chosen. A 
musical M-x dissociated-press.

Originally by Adam Lindsay, 2009-06-27.
Refactored by Thor Kell, 2012-15-12
"""
import random
import numpy
from echonest.remix import video, audio

usage = """
Usage:
    python vdissoc.py inputFilenameOrUrl outputFilename [variation]

variation is the number of near candidates chosen from. [default=4]

Example:
    python vdissoc.py 'http://www.youtube.com/watch?v=Es7mk19wMrk' Seventh.mp4
"""
def main(infile, outfile, choices=4):
    if infile.startswith("http://"):
        av = video.loadavfromyoutube(infile)
    else:
        av = video.loadav(infile)

    meter = av.audio.analysis.time_signature['value']
    sections = av.audio.analysis.sections
    output = audio.AudioQuantumList()

    for section in sections:
        beats = []
        bars = section.children()
        for bar in bars:
            beats.extend(bar.children())
    
        if not bars or not beats:
            continue

        beat_array = []
        for m in range(meter):
            metered_beats = []
            for b in beats:
                if beats.index(b) % meter == m:
                    metered_beats.append(b)
            beat_array.append(metered_beats)

        # Always start with the first beat
        output.append(beat_array[0][0]);
        for x in range(1, len(bars) * meter):
            meter_index = x % meter
            next_candidates = beat_array[meter_index]

            def sorting_function(chunk, target_chunk=output[-1]):
                timbre = chunk.mean_timbre()
                target_timbre = target_chunk.mean_timbre()
                timbre_distance = numpy.linalg.norm(numpy.array(timbre) - numpy.array(target_timbre))
                return timbre_distance

            next_candidates = sorted(next_candidates, key=sorting_function)
            next_index = random.randint(0, min(choices, len(next_candidates) - 1))
            output.append(next_candidates[next_index])
    
    out = video.getpieces(av, output)
    out.save(outfile)

if __name__ == '__main__':
    import sys
    try:
        inputFilename = sys.argv[1]
        outputFilename = sys.argv[2]
        if len(sys.argv) > 3:
            variation = int(sys.argv[3])
        else:
            variation = 4
    except:
        print usage
        sys.exit(-1)
    main(inputFilename, outputFilename, variation)

########NEW FILE########
__FILENAME__ = vone
#!/usr/bin/env python
# encoding: utf-8
"""
vone.py

Created by Ben Lacker on 2009-06-19.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
import os

from echonest.remix import audio, video

usage = """
Usage: 
    python vone.py <input_filename> <output_filename>

Example:
    python vone.py EverythingIsOnTheOne.mpg EverythingIsReallyOnTheOne.mpg
"""


def main(input_filename, output_filename):
    if input_filename.startswith("http://"):
        av = video.loadavfromyoutube(input_filename)
    else:
        av = video.loadav(input_filename)
    collect = audio.AudioQuantumList()
    for bar in av.audio.analysis.bars:
        collect.append(bar.children()[0])
    out = video.getpieces(av, collect)
    out.save(output_filename)


if __name__ == '__main__':
    import sys
    try:
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        print usage
        sys.exit(-1)
    main(input_filename, output_filename)

########NEW FILE########
__FILENAME__ = vreverse
#!/usr/bin/env python
# encoding: utf-8
"""
vreverse.py

Created by Ben Lacker on 2009-06-19.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
import os

from echonest.remix import video

usage = """
Usage: 
    python vreverse.py <beats|tatums> <inputFilename> <outputFilename>

Example:
    python vreverse.py beats YouCanCallMeAl.mpg AlMeCallCanYou.mpg
"""


def main(toReverse, inputFilename, outputFilename):
    if inputFilename.startswith("http://"):
        av = video.loadavfromyoutube(inputFilename)
    else:
        av = video.loadav(inputFilename)
    if toReverse == 'tatums':
        chunks = av.audio.analysis.tatums
    elif toReverse == 'beats':
        chunks = av.audio.analysis.beats
    chunks.reverse()
    out = video.getpieces(av, chunks)
    out.save(outputFilename)

if __name__ == '__main__':
    try :
        toReverse = sys.argv[1]
        inputFilename = sys.argv[2]
        outputFilename = sys.argv[3]
    except :
        print usage
        sys.exit(-1)
    if not toReverse in ["beats", "tatums"]:
        print usage
        sys.exit(-1)
    main(toReverse, inputFilename, outputFilename)

########NEW FILE########
__FILENAME__ = waltzify
#!/usr/bin/env python
# encoding: utf=8

"""
waltzify.py

Turn 4/4 music into 3/4
Modified approach suggested by Mary Farbood.
Created by Tristan Jehan.
"""

import os, sys
import dirac, math
from optparse import OptionParser
from echonest.remix.audio import LocalAudioFile, AudioData
from echonest.remix.action import render, Playback, display_actions


def select_tempo(index, num_beats, min_tempo, max_tempo, rate):
    v = math.atan(float(rate)*float(index)/float(num_beats))/1.57
    return min_tempo + v * float(max_tempo-min_tempo)


def do_work(track, options):
    
    # manage options
    verbose = bool(options.verbose)    
    low_tempo = float(options.low)    
    high_tempo = float(options.high)    
    rate_tempo = float(options.rate)    
    rubato = float(options.rubato)    
    tempo = float(options.tempo)    

    # acceleration or not
    if rate_tempo == 0:
        if tempo == 0:
            low_tempo = track.analysis.tempo['value']
            high_tempo = low_tempo
        else:
            low_tempo = tempo
            high_tempo = tempo

    rates = []
    count = min(max(0,int(options.offset)),1)
    beats = track.analysis.beats
    offset = int(beats[0].start * track.sampleRate)

    # for every beat
    for beat in beats[:-1]:

        # get a tempo, particularly for accelerando
        target_tempo = select_tempo(beats.index(beat), len(beats), low_tempo, high_tempo, rate_tempo)

        # calculate rates
        if count == 0:
            dur = beat.duration/2.0
            rate1 = 60.0 / (target_tempo * dur)
            stretch = dur * rate1
            rate2 = rate1 + rubato
        elif count == 1:
            rate1 = 60.0 / (target_tempo * beat.duration)

        # add a change of rate at a given time
        start1 = int(beat.start * track.sampleRate)
        rates.append((start1-offset, rate1))
        if count == 0:
            start2 = int((beat.start+dur) * track.sampleRate)
            rates.append((start2-offset, rate2))

        # show on screen
        if verbose:
            if count == 0:
                args = (beats.index(beat), count, beat.duration, dur*rate1, dur*rate2, 60.0/(dur*rate1), 60.0/(dur*rate2))
                print "Beat %d (%d) | stretch %.3f sec into [%.3f|%.3f] sec | tempo = [%d|%d] bpm" % args
            elif count == 1:
                args = (beats.index(beat), count, beat.duration, beat.duration*rate1, 60.0/(beat.duration*rate1))
                print "Beat %d (%d) | stretch %.3f sec into %.3f sec | tempo = %d bpm" % args
        
        count = (count + 1) % 2
   
    # get audio
    vecin = track.data[offset:int(beats[-1].start * track.sampleRate),:]

    # time stretch
    if verbose: 
        print "\nTime stretching..."
    vecout = dirac.timeScale(vecin, rates, track.sampleRate, 0)
    
    # build timestretch AudioData object
    ts = AudioData(ndarray=vecout, shape=vecout.shape, 
                    sampleRate=track.sampleRate, numChannels=vecout.shape[1], 
                    verbose=verbose)
    
    # initial and final playback
    pb1 = Playback(track, 0, beats[0].start)
    pb2 = Playback(track, beats[-1].start, track.analysis.duration-beats[-1].start)

    return [pb1, ts, pb2]


def main():
    usage = "usage: %s [options] <one_single_mp3>" % sys.argv[0]
    parser = OptionParser(usage=usage)
    parser.add_option("-o", "--offset", default=0, help="offset where to start counting")
    parser.add_option("-l", "--low", default=100, help="low tempo")
    parser.add_option("-H", "--high", default=192, help="high tempo")
    parser.add_option("-r", "--rate", default=0, help="acceleration rate (try 30)")
    parser.add_option("-R", "--rubato", default=0, help="rubato on second beat (try 0.2)")
    parser.add_option("-t", "--tempo", default=0, help="target tempo (try 160)")
    parser.add_option("-v", "--verbose", action="store_true", help="show results on screen")
    
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        return -1
    
    verbose = options.verbose

    # get Echo Nest analysis for this file
    track = LocalAudioFile(args[0], verbose=verbose)
    
    if verbose:
        print "Waltzifying..."

    # this is where the work takes place
    actions = do_work(track, options)

    if verbose:
        display_actions(actions)
    
    # new name
    name = os.path.splitext(os.path.basename(args[0]))
    name = str(name[0] + '_waltz_%d' % int(options.offset) +'.mp3')
    
    if verbose:
        print "Rendering... %s" % name

    # send to renderer
    render(actions, name, verbose=verbose)
    
    if verbose:
        print "Success!"

    return 1


if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        print e

########NEW FILE########
__FILENAME__ = test_dirac
#!/usr/bin/env python
# encoding: utf-8
"""
test_dirac.py

Test Dirac LE Time Stretcher.

Created by Tristan Jehan on 2010-04-22.
"""
import math, os, sys
from echonest import audio

import dirac
    
USAGE = """
Usage:
    python test_dirac.py <input_filename>
Example:
    python test_dirac.py will.wav
"""

def main():
    
    try:
        in_filename = sys.argv[1]
    except Exception:
        print USAGE
        sys.exit(-1)

    afile = audio.LocalAudioFile(in_filename)
    vecin = afile.data
    
    # ------------------------------------------------------------------------------------
    # Single time-stretch
    # ------------------------------------------------------------------------------------
    rate = 1.25 # 25% slower
    quality = 0 # fast processing
    
    print "Time Stretching with single rate", rate
    # arguments are:
    # 1) a numpy array of size N x C, where N is a number of samples, and C the number of channels (1 or 2)
    # 2) a float representing the time-stretching rate, e.g. 0.5 for twice as short, and 2.0 for twice as long
    # 3) an integer representing the sample rate of the input signal, e.g. 44100
    # 4) an optional integer representing the processing quality and speed between the default 0 (fastest, lowest quality) and 2 (slowest, highest quality)
    vecout = dirac.timeScale(vecin, rate, afile.sampleRate, quality)
    
    # output audio
    out = audio.AudioData(ndarray=vecout, shape=vecout.shape, sampleRate=afile.sampleRate, numChannels=vecout.shape[1])
    out_filename = 'out_single_rate.wav'
    print "Writing file", out_filename
    out.encode(out_filename)
    
    # ------------------------------------------------------------------------------------
    # Varying time-stretch
    # ------------------------------------------------------------------------------------
    # This example will linearly change the speed from 'rate' to 1.0 in 'numChunks' chunks
    numChunks = 16 # divide the signal into 16 chunks
    sizeChunk = int(vecin.shape[0] / numChunks)
    incRate = (1.0-rate) / (numChunks-1)
    
    # first tuple must start at index 0
    index = 0
    rates = [(index, rate)]
    for i in xrange(numChunks-1):
        index += sizeChunk
        rate += incRate
        rates.append((index, rate))
    
    print "Time Stretching with list of rates", rates
    # arguments are:
    # 1) a numpy array of size N x C, where N is a number of samples, and C the number of channels (1 or 2)
    # 2) a list of tuples each representing (a sample index, a rate). First index must be 0.
    # 3) an integer representing the sample rate of the input signal, e.g. 44100
    # 4) an optional integer representing the processing quality and speed between the default 0 (fastest, lowest quality) and 2 (slowest, highest quality)
    vecout = dirac.timeScale(vecin, rates, afile.sampleRate, quality)
    out = audio.AudioData(ndarray=vecout, shape=vecout.shape, sampleRate=afile.sampleRate, numChannels=vecout.shape[1])

    out_filename = 'out_list_rates.wav'
    print "Writing file", out_filename
    out.encode(out_filename)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = fix_develop_install
#!/usr/bin/env python
# Fixes the paths due to package dirs being ignored by setup.py develop:
# https://bitbucket.org/tarek/distribute/issue/177/setuppy-develop-doesnt-support-package_dir

# Run this, with sudo, after running python setup.py develop.  

import sys
import os
import shutil

# Get the location of easy-install.pth
temp_path = sys.path
final_python_path =  list(set(temp_path))
for path in final_python_path:
    try:
        files = os.listdir(path)
        if "easy-install.pth" in files:
            path_to_easy_install = path
            break
    except OSError: # In case sys.path has dirs that have been deleted
        pass

# Get the location of the remix installaton.
f = open(path_to_easy_install + os.sep + 'remix.egg-link', 'r')
for line in f:
    if os.sep in line:
        path_to_remix = line.strip()
        break
f.close()

# Do the modfication:
easy_install_path = path_to_easy_install + os.sep + 'easy-install.pth'
remix_source_string = path_to_remix + os.sep + "src\n"
pyechonest_source_string = path_to_remix + os.sep + "pyechonest\n"

print "Adding %s and %s to %s" % (remix_source_string, pyechonest_source_string, easy_install_path)
f = open(easy_install_path, 'a')
f.write(remix_source_string)
f.write(pyechonest_source_string)
f.close()

# Copy youtube-dl out
print "Copying youtube-dl to /usr/local/bin"
# If we're in a virtualenv:
if 'real_prefix' in dir(sys):
    data_path = os.path.join(sys.prefix, "local/bin/youtube-dl")
else:
    data_path = '/usr/local/bin/youtube-dl'
shutil.copyfile('external/youtube-dl/youtube-dl', data_path)
os.chmod(data_path, 0755)


########NEW FILE########
__FILENAME__ = action
#!/usr/bin/env python
# encoding: utf-8
"""
action.py

Created by Tristan Jehan and Jason Sundram.
"""
import os
from numpy import zeros, multiply, float32, mean, copy
from math import atan, pi
import sys

from echonest.remix.audio import assemble, AudioData
from cAction import limit, crossfade, fadein, fadeout

import dirac

def rows(m):
    """returns the # of rows in a numpy matrix"""
    return m.shape[0]

def make_mono(track):
    """Converts stereo tracks to mono; leaves mono tracks alone."""
    if track.data.ndim == 2:
        mono = mean(track.data,1)
        track.data = mono
        track.numChannels = 1
    return track

def make_stereo(track):
    """If the track is mono, doubles it. otherwise, does nothing."""
    if track.data.ndim == 1:
        stereo = zeros((len(track.data), 2))
        stereo[:,0] = copy(track.data)
        stereo[:,1] = copy(track.data)
        track.data = stereo
        track.numChannels = 2
    return track
    
def render(actions, filename, verbose=True):
    """Calls render on each action in actions, concatenates the results, 
    renders an audio file, and returns a path to the file"""
    pieces = [a.render() for a in actions]
    # TODO: allow numChannels and sampleRate to vary.
    out = assemble(pieces, numChannels=2, sampleRate=44100, verbose=verbose)
    return out, out.encode(filename)


class Playback(object):
    """A snippet of the given track with start and duration. Volume leveling 
    may be applied."""
    def __init__(self, track, start, duration):
        self.track = track
        self.start = float(start)
        self.duration = float(duration)
    
    def render(self):
        # self has start and duration, so it is a valid index into track.
        output = self.track[self]
        # Normalize volume if necessary
        gain = getattr(self.track, 'gain', None)
        if gain != None:
            # limit expects a float32 vector
            output.data = limit(multiply(output.data, float32(gain)))
            
        return output
    
    def __repr__(self):
        return "<Playback '%s'>" % self.track.filename
    
    def __str__(self):
        args = (self.start, self.start + self.duration, 
                self.duration, self.track.filename)
        return "Playback\t%.3f\t-> %.3f\t (%.3f)\t%s" % args


class Fadeout(Playback):
    """Fadeout"""
    def render(self):
        gain = getattr(self.track, 'gain', 1.0)
        output = self.track[self]
        # second parameter is optional -- in place function for now
        output.data = fadeout(output.data, gain)
        return output
    
    def __repr__(self):
        return "<Fadeout '%s'>" % self.track.filename
    
    def __str__(self):
        args = (self.start, self.start + self.duration, 
                self.duration, self.track.filename)
        return "Fade out\t%.3f\t-> %.3f\t (%.3f)\t%s" % args


class Fadein(Playback):
    """Fadein"""
    def render(self):
        gain = getattr(self.track, 'gain', 1.0)
        output = self.track[self]
        # second parameter is optional -- in place function for now
        output.data = fadein(output.data, gain)
        return output
    
    def __repr__(self):
        return "<Fadein '%s'>" % self.track.filename
    
    def __str__(self):
        args = (self.start, self.start + self.duration, 
                self.duration, self.track.filename)
        return "Fade in\t%.3f\t-> %.3f\t (%.3f)\t%s" % args


class Edit(object):
    """Refer to a snippet of audio"""
    def __init__(self, track, start, duration):
        self.track = track
        self.start = float(start)
        self.duration = float(duration)
    
    def __str__(self):
        args = (self.start, self.start + self.duration, 
                self.duration, self.track.filename)
        return "Edit\t%.3f\t-> %.3f\t (%.3f)\t%s" % args
    
    def get(self):
        return self.track[self]
    
    @property
    def end(self):
        return self.start + self.duration


class Crossfade(object):
    """Crossfades between two tracks, at the start points specified, 
    for the given duration"""
    def __init__(self, tracks, starts, duration, mode='linear'):
        self.t1, self.t2 = [Edit(t, s, duration) for t,s in zip(tracks, starts)]
        self.duration = self.t1.duration
        self.mode = mode
    
    def render(self):
        t1, t2 = map(make_stereo, (self.t1.get(), self.t2.get()))
        vecout = crossfade(t1.data, t2.data, self.mode)
        audio_out = AudioData(ndarray=vecout, shape=vecout.shape, 
                                sampleRate=t1.sampleRate, 
                                numChannels=vecout.shape[1])
        return audio_out
    
    def __repr__(self):
        args = (self.t1.track.filename, self.t2.track.filename)
        return "<Crossfade '%s' and '%s'>" % args
    
    def __str__(self):
        args = (self.t1.start, self.t2.start + self.duration, self.duration, 
                self.t1.track.filename, self.t2.track.filename)
        return "Crossfade\t%.3f\t-> %.3f\t (%.3f)\t%s -> %s" % args


class Jump(Crossfade):
    """Move from one point """
    def __init__(self, track, source, target, duration):
        self.track = track
        self.t1, self.t2 = (Edit(track, source, duration), 
                            Edit(track, target - duration, duration))
        self.duration = float(duration)
        self.mode = 'equal_power'
        self.CROSSFADE_COEFF = 0.6
    
    @property
    def source(self):
        return self.t1.start
    
    @property
    def target(self):
        return self.t2.end 
    
    def __repr__(self):
        return "<Jump '%s'>" % (self.t1.track.filename)
    
    def __str__(self):
        args = (self.t1.start, self.t2.end, self.duration, 
                self.t1.track.filename)
        return "Jump\t\t%.3f\t-> %.3f\t (%.3f)\t%s" % args


class Blend(object):
    """Mix together two lists of beats"""
    def __init__(self, tracks, lists):
        self.t1, self.t2 = tracks
        self.l1, self.l2 = lists
        assert(len(self.l1) == len(self.l2))
        
        self.calculate_durations()
    
    def calculate_durations(self):
        zipped = zip(self.l1, self.l2)
        self.durations = [(d1 + d2) / 2.0 for ((s1, d1), (s2, d2)) in zipped]
        self.duration = sum(self.durations)
    
    def render(self):
        # use self.durations already computed
        # build 2 AudioQuantums
        # call Mix
        pass
    
    def __repr__(self):
        args = (self.t1.filename, self.t2.filename)
        return "<Blend '%s' and '%s'>" % args
    
    def __str__(self):
        # start and end for each of these lists.
        s1, e1 = self.l1[0][0], sum(self.l1[-1])
        s2, e2 = self.l2[0][0], sum(self.l2[-1])
        n1, n2 = self.t1.filename, self.t2.filename # names
        args = (s1, s2, e1, e2, self.duration, n1, n2)
        return "Blend [%.3f, %.3f] -> [%.3f, %.3f] (%.3f)\t%s + %s" % args


class Crossmatch(Blend):
    """Makes a beat-matched crossfade between the two input tracks."""
    def calculate_durations(self):
        c, dec = 1.0, 1.0 / float(len(self.l1)+1)
        self.durations = []
        for ((s1, d1), (s2, d2)) in zip(self.l1, self.l2):
            c -= dec
            self.durations.append(c * d1 + (1 - c) * d2)
        self.duration = sum(self.durations)
    
    def stretch(self, t, l):
        """t is a track, l is a list"""
        signal_start = int(l[0][0] * t.sampleRate)
        signal_duration = int((sum(l[-1]) - l[0][0]) * t.sampleRate)
        vecin = t.data[signal_start:signal_start + signal_duration,:]
        
        rates = []
        for i in xrange(len(l)):
            rate = (int(l[i][0] * t.sampleRate) - signal_start, 
                    self.durations[i] / l[i][1])
            rates.append(rate)
        
        vecout = dirac.timeScale(vecin, rates, t.sampleRate, 0)
        if hasattr(t, 'gain'):
            vecout = limit(multiply(vecout, float32(t.gain)))
        
        audio_out = AudioData(ndarray=vecout, shape=vecout.shape, 
                                sampleRate=t.sampleRate, 
                                numChannels=vecout.shape[1])
        return audio_out
    
    def render(self):
        # use self.durations already computed
        # 1) stretch the duration of each item in t1 and t2
        # to the duration prescribed in durations.
        out1 = self.stretch(self.t1, self.l1)
        out2 = self.stretch(self.t2, self.l2)
        
        # 2) cross-fade the results
        # out1.duration, out2.duration, and self.duration should be about 
        # the same, but it never hurts to be safe.
        duration = min(out1.duration, out2.duration, self.duration)
        c = Crossfade([out1, out2], [0, 0], duration, mode='equal_power')
        return c.render()
    
    def __repr__(self):
        args = (self.t1.filename, self.t2.filename)
        return "<Crossmatch '%s' and '%s'>" % args
    
    def __str__(self):
        # start and end for each of these lists.
        s1, e1 = self.l1[0][0], sum(self.l1[-1])
        s2, e2 = self.l2[0][0], sum(self.l2[-1])
        n1, n2 = self.t1.filename, self.t2.filename # names
        args = (s1, e2, self.duration, n1, n2)
        return "Crossmatch\t%.3f\t-> %.3f\t (%.3f)\t%s -> %s" % args


def humanize_time(secs):
    """Turns seconds into a string of the form HH:MM:SS, 
    or MM:SS if less than one hour."""
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    if 0 < hours: 
        return '%02d:%02d:%02d' % (hours, mins, secs)
    
    return '%02d:%02d' % (mins, secs)


def display_actions(actions):
    total = 0
    print
    for a in actions:
        print "%s\t  %s" % (humanize_time(total), unicode(a))
        total += a.duration
    print

########NEW FILE########
__FILENAME__ = audio
"""
The main `Echo Nest`_ `Remix API`_ module for manipulating audio files and
their associated `Echo Nest`_ `Analyze API`_ analyses.

AudioData, and getpieces by Robert Ochshorn on 2008-06-06.  
Some refactoring and everything else by Joshua Lifton 2008-09-07.  
Refactoring by Ben Lacker 2009-02-11. 
Other contributions by Adam Lindsay. 
Additional functions and cleanup by Peter Sobot on 2012-11-01.

:group Base Classes: AudioAnalysis, AudioRenderable, AudioData, AudioData32
:group Audio-plus-Analysis Classes: AudioFile, LocalAudioFile, LocalAnalysis
:group Building Blocks: AudioQuantum, AudioSegment, AudioQuantumList, ModifiedRenderable
:group Effects: AudioEffect, LevelDB, AmplitudeFactor, TimeTruncateFactor, TimeTruncateLength, Simultaneous
:group Exception Classes: FileTypeError, EchoNestRemixError

:group Audio helper functions: getpieces, mix, assemble, megamix
:group Utility functions: _dataParser, _attributeParser, _segmentsParser

.. _Analyze API: http://developer.echonest.com/
.. _Remix API: https://github.com/echonest/remix
.. _Echo Nest: http://the.echonest.com/
"""

__version__ = "$Revision: 0 $"
# $Source$

import hashlib
import numpy
import os
import sys
import errno
import cPickle
import shutil
import struct
import tempfile
import logging
import wave
import time
import traceback
import cStringIO
import xml.etree.ElementTree as etree
import xml.dom.minidom as minidom
import weakref

from pyechonest import track
from pyechonest.util import EchoNestAPIError
import pyechonest.util
import pyechonest.config as config
from support.ffmpeg import ffmpeg, ffmpeg_downconvert


MP3_BITRATE = 128

log = logging.getLogger(__name__)


class AudioAnalysis(object):
    """
    This class uses (but does not wrap) `pyechonest.track` to allow
    transparent caching of the audio analysis of an audio file.

    For example, the following script will display the bars of a track
    twice::

        from echonest import *
        a = audio.AudioAnalysis('YOUR_TRACK_ID_HERE')
        a.bars
        a.bars

    The first time `a.bars` is called, a network request is made of the
    `Echo Nest`_ `Analyze API`_.  The second time time `a.bars` is called, the
    cached value is returned immediately.

    An `AudioAnalysis` object can be created using an existing ID, as in
    the example above, or by specifying the audio file to upload in
    order to create the ID, as in::

        a = audio.AudioAnalysis('FULL_PATH_TO_AUDIO_FILE')

    .. _Analyze API: http://developer.echonest.com/pages/overview?version=2
    .. _Echo Nest: http://the.echonest.com/
    """

    @classmethod
    def __get_cache_path(cls, identifier):
        return "cache/%s.pickle" % identifier

    def __new__(cls, *args, **kwargs):
        if len(args):
            initializer = args[0]
            if type(initializer) is str and len(initializer) == 32:
                path = cls.__get_cache_path(initializer)
                if os.path.exists(path):
                    return cPickle.load(open(path, 'r'))
        return object.__new__(cls, *args, **kwargs)

    def __init__(self, initializer, filetype = None, lastTry = False):
        """
        Constructor.  If the argument is a valid local path or a URL,
        the track ID is generated by uploading the file to the `Echo Nest`_
        `Analyze API`_\.  Otherwise, the argument is assumed to be
        the track ID.

        :param path_or_identifier_or_file:
            A string representing either a path to a local
            file, or the ID of a file that has already
            been uploaded for analysis, or an open file-like object.

        .. _Analyze API: http://developer.echonest.com/docs/v4/track.html
        .. _Echo Nest: http://the.echonest.com/
        """
        if type(initializer) not in [str, unicode] and not hasattr(initializer, 'read'):
            # Argument is invalid.
            raise TypeError("Argument 'initializer' must be a string \
                            representing either a filename, track ID, or MD5, or \
                            instead, a file-like object.")

        __save_to_cache = False
        try:
            if isinstance(initializer, basestring):
                # see if path_or_identifier is a path or an ID
                if os.path.isfile(initializer):
                    # it's a filename
                    self.pyechonest_track = track.track_from_filename(initializer)
                    self.pyechonest_track.get_analysis()
                else:
                    if initializer.startswith('music://') or \
                       (initializer.startswith('TR') and
                        len(initializer) == 18):
                        # it's an id
                        self.pyechonest_track = track.track_from_id(initializer)
                        self.pyechonest_track.get_analysis()
                    elif len(initializer) == 32:
                        # it's an md5
                        self.pyechonest_track = track.track_from_md5(initializer)
                        self.pyechonest_track.get_analysis()
                        __save_to_cache = True
            else:
                assert(filetype is not None)
                initializer.seek(0)
                try:
                    self.pyechonest_track = track.track_from_file(initializer, filetype)
                    self.pyechonest_track.get_analysis()
                except (IOError, pyechonest.util.EchoNestAPIError) as e:
                    if lastTry:
                        raise

                    if (isinstance(e, IOError)
                        and (e.errno in [errno.EPIPE, errno.ECONNRESET]))\
                    or (isinstance(e, pyechonest.util.EchoNestAPIError)
                        and any([("Error %s" % x) in str(e) for x in [-1, 5, 6]])):
                        logging.getLogger(__name__).warning("Upload to EN failed - transcoding and reattempting.")
                        self.__init__(ffmpeg_downconvert(initializer, filetype), 'mp3', lastTry=True)
                        return
                    elif (isinstance(e, pyechonest.util.EchoNestAPIError)
                            and any([("Error %s" % x) in str(e) for x in [3]])):
                        logging.getLogger(__name__).warning("EN API limit hit. Waiting 10 seconds.")
                        time.sleep(10)
                        self.__init__(initializer, filetype, lastTry=True)
                        return
                    else:
                        logging.getLogger(__name__).warning("Got unhandlable EN exception. Raising:\n%s",
                                                            traceback.format_exc())
                        raise
        except Exception as e:
            if lastTry or type(initializer) is str:
                raise

            if "the track is still being analyzed" in str(e)\
            or "there was an error analyzing the track" in str(e):
                logging.getLogger(__name__).warning("Could not analyze track - truncating last byte and trying again.")
                try:
                    initializer.seek(-1, os.SEEK_END)
                    initializer.truncate()
                    initializer.seek(0)
                except IOError:
                    initializer.seek(-1, os.SEEK_END)
                    new_len = initializer.tell()
                    initializer.seek(0)
                    initializer = cStringIO.StringIO(initializer.read(new_len))
                self.__init__(initializer, filetype, lastTry=True)
                return
            else:
                logging.getLogger(__name__).warning("Got a further unhandlable EN exception. Raising:\n%s",
                                                    traceback.format_exc())
                raise

        if self.pyechonest_track is None:
            #   This is an EN-side error that will *not* be solved by repeated calls
            if type(initializer) is str:
                raise EchoNestRemixError('Could not find track %s' % initializer)
            else:
                raise EchoNestRemixError('Could not find analysis for track!')

        self.source = None

        self._bars = None
        self._beats = None
        self._tatums = None
        self._sections = None
        self._segments = None

        self.identifier = self.pyechonest_track.id
        # Patching around the fact that sometimes pyechonest doesn't give back metadata
        # As of 11/2012, metadata is not used by remix
        try:
            self.metadata = self.pyechonest_track.meta
        except AttributeError:
            self.metadata = None
            print >> sys.stderr, "Warning:  no metadata returned for track."

        for attribute in ('time_signature', 'mode', 'tempo', 'key'):
            d = {'value': getattr(self.pyechonest_track, attribute),
                 'confidence': getattr(self.pyechonest_track, attribute + '_confidence')}
            setattr(self, attribute, d)

        for attribute in ('end_of_fade_in', 'start_of_fade_out', 'duration', 'loudness'):
            setattr(self, attribute, getattr(self.pyechonest_track, attribute))

        if __save_to_cache:
            path = self.__get_cache_path(initializer)
            if not os.path.isfile(path) and os.path.isdir(os.path.dirname(path)):
                cPickle.dump(self, open(path, 'w'), 2)

    @property
    def bars(self):
        if self._bars is None:
            self._bars = _dataParser('bar', self.pyechonest_track.bars)
            self._bars.attach(self)
        return self._bars

    @property
    def beats(self):
        if self._beats is None:
            self._beats = _dataParser('beat', self.pyechonest_track.beats)
            self._beats.attach(self)
        return self._beats

    @property
    def tatums(self):
        if self._tatums is None:
            self._tatums = _dataParser('tatum', self.pyechonest_track.tatums)
            self._tatums.attach(self)
        return self._tatums

    @property
    def sections(self):
        if self._sections is None:
            self._sections = _attributeParser('section', self.pyechonest_track.sections)
            self._sections.attach(self)
        return self._sections

    @property
    def segments(self):
        if self._segments is None:
            self._segments = _segmentsParser(self.pyechonest_track.segments)
            self._segments.attach(self)
        return self._segments

    def __getstate__(self):
        """
        Eliminates the circular reference for pickling.
        """
        dictclone = self.__dict__.copy()
        del dictclone['source']
        return dictclone

    def __setstate__(self, state):
        """
        Recreates circular references after unpickling.
        """
        self.__dict__.update(state)
        if hasattr(AudioAnalysis, 'CACHED_VARIABLES'):
            for cached_var in AudioAnalysis.CACHED_VARIABLES:
                if type(object.__getattribute__(self, cached_var)) == AudioQuantumList:
                    object.__getattribute__(self, cached_var).attach(self)


class AudioRenderable(object):
    """
    An object that gives an `AudioData` in response to a call to its `render`\()
    method.
    Intended to be an abstract class that helps enforce the `AudioRenderable`
    protocol. Picked up a couple of convenience methods common to many descendants.

    Every `AudioRenderable` must provide three things:

    render()
        A method returning the `AudioData` for the object. The rhythmic duration (point
        at which any following audio is appended) is signified by the `endindex` accessor,
        measured in samples.
    source
        An accessor pointing to the `AudioData` that contains the original sample data of
        (a superset of) this audio object.
    duration
        An accessor returning the rhythmic duration (in seconds) of the audio object.
    """
    def resolve_source(self, alt):
        """
        Given an alternative, fallback `alt` source, return either `self`'s
        source or the alternative. Throw an informative error if no source
        is found.

        Utility code that ended up being replicated in several places, so
        it ended up here. Not necessary for use in the RenderableAudioObject
        protocol.
        """
        if hasattr(self, 'source'):
            source = self.source
        else:
            if isinstance(alt, AudioData):
                source = alt
            else:
                print >> sys.stderr, self.__repr__()
                raise EchoNestRemixError("%s has no implicit or explicit source \
                                                during rendering." %
                                                (self.__class__.__name__, ))
        return source

    @staticmethod
    def init_audio_data(source, num_samples):
        """
        Convenience function for rendering: return a pre-allocated, zeroed
        `AudioData`.
        """
        if source.numChannels > 1:
            newchans = source.numChannels
            newshape = (num_samples, newchans)
        else:
            newchans = 1
            newshape = (num_samples,)
        return AudioData32(shape=newshape, sampleRate=source.sampleRate,
                            numChannels=newchans, defer=False)

    def sources(self):
        return set([self.source])

    def encode(self, filename):
        """
        Shortcut function that takes care of the need to obtain an `AudioData`
        object first, through `render`.
        """
        self.render().encode(filename)


class AudioData(AudioRenderable):
    """
    Handles audio data transparently. A smart audio container
    with accessors that include:

    sampleRate
        samples per second
    numChannels
        number of channels
    data
        a `numpy.array`_

    .. _numpy.array: http://docs.scipy.org/doc/numpy/reference/generated/numpy.array.html
    """
    def __init__(self, filename=None, ndarray = None, shape=None, sampleRate=None, numChannels=None, defer=False, verbose=True):
        """
        Given an input `ndarray`, import the sample values and shape
        (if none is specified) of the input `numpy.array`.

        Given a `filename` (and an input ndarray), use ffmpeg to convert
        the file to wave, then load the file into the data,
        auto-detecting the sample rate, and number of channels.

        :param filename: a path to an audio file for loading its sample
            data into the AudioData.data
        :param ndarray: a `numpy.array`_ instance with sample data
        :param shape: a tuple of array dimensions
        :param sampleRate: sample rate, in Hz
        :param numChannels: number of channels

        .. _numpy.array: http://docs.scipy.org/doc/numpy/reference/generated/numpy.array.html
        """
        self.verbose = verbose
        self.defer = defer
        self.filename = filename
        self.sampleRate = sampleRate
        self.numChannels = numChannels
        self.convertedfile = None
        self.endindex = 0
        if shape is None and isinstance(ndarray, numpy.ndarray) and not self.defer:
            self.data = numpy.zeros(ndarray.shape, dtype=numpy.int16)
        elif shape is not None and not self.defer:
            self.data = numpy.zeros(shape, dtype=numpy.int16)
        elif not self.defer and self.filename:
            self.data = None
            self.load()
        else:
            self.data = None
        if ndarray is not None and self.data is not None:
            self.endindex = len(ndarray)
            self.data[0:self.endindex] = ndarray

    def load(self):
        if isinstance(self.data, numpy.ndarray):
            return
        temp_file_handle = None
        if self.filename.lower().endswith(".wav") and (self.sampleRate, self.numChannels) == (44100, 2):
            file_to_read = self.filename
        elif self.convertedfile:
            file_to_read = self.convertedfile
        else:
            temp_file_handle, self.convertedfile = tempfile.mkstemp(".wav")
            self.sampleRate, self.numChannels = ffmpeg(self.filename, self.convertedfile, overwrite=True,
                    numChannels=self.numChannels, sampleRate=self.sampleRate, verbose=self.verbose)
            file_to_read = self.convertedfile

        w = wave.open(file_to_read, 'r')
        numFrames = w.getnframes()
        raw = w.readframes(numFrames)
        sampleSize = numFrames * self.numChannels
        data = numpy.frombuffer(raw, dtype="<h", count=sampleSize)
        ndarray = numpy.array(data, dtype=numpy.int16)
        if self.numChannels > 1:
            ndarray.resize((numFrames, self.numChannels))
        self.data = numpy.zeros(ndarray.shape, dtype=numpy.int16)
        self.endindex = 0
        if ndarray is not None:
            self.endindex = len(ndarray)
            self.data = ndarray
        if temp_file_handle is not None:
            os.close(temp_file_handle)
        w.close()

    def __getitem__(self, index):
        """
        Fetches a frame or slice. Returns an individual frame (if the index
        is a time offset float or an integer sample number) or a slice if
        the index is an `AudioQuantum` (or quacks like one).
        """
        if not isinstance(self.data, numpy.ndarray) and self.defer:
            self.load()
        if isinstance(index, float):
            index = int(index * self.sampleRate)
        elif hasattr(index, "start") and hasattr(index, "duration"):
            index =  slice(float(index.start), index.start + index.duration)

        if isinstance(index, slice):
            if (hasattr(index.start, "start") and
                 hasattr(index.stop, "duration") and
                 hasattr(index.stop, "start")):
                index = slice(index.start.start, index.stop.start + index.stop.duration)

        if isinstance(index, slice):
            return self.getslice(index)
        else:
            return self.getsample(index)

    def getslice(self, index):
        "Help `__getitem__` return a new AudioData for a given slice"
        if not isinstance(self.data, numpy.ndarray) and self.defer:
            self.load()
        if isinstance(index.start, float):
            index = slice(int(index.start * self.sampleRate),
                            int(index.stop * self.sampleRate), index.step)
        return AudioData(None, self.data[index], sampleRate=self.sampleRate,
                            numChannels=self.numChannels, defer=False)

    def getsample(self, index):
        """
        Help `__getitem__` return a frame (all channels for a given
        sample index)
        """
        if not isinstance(self.data, numpy.ndarray) and self.defer:
            self.load()
        if isinstance(index, int):
            return self.data[index]
        else:
            #let the numpy array interface be clever
            return AudioData(None, self.data[index], defer=False)

    def pad_with_zeros(self, num_samples):
        if num_samples > 0:
            if self.numChannels == 1:
                extra_shape = (num_samples,)
            else:
                extra_shape = (num_samples, self.numChannels)
            self.data = numpy.append(self.data,
                                     numpy.zeros(extra_shape, dtype=numpy.int16), axis=0)

    def append(self, another_audio_data):
        "Appends the input to the end of this `AudioData`."
        extra = len(another_audio_data.data) - (len(self.data) - self.endindex)
        self.pad_with_zeros(extra)
        self.data[self.endindex : self.endindex + len(another_audio_data)] += another_audio_data.data
        self.endindex += another_audio_data.endindex

    def sum(self, another_audio_data):
        extra = len(another_audio_data.data) - len(self.data)
        self.pad_with_zeros(extra)
        compare_limit = min(len(another_audio_data.data), len(self.data)) - 1
        self.data[: compare_limit] += another_audio_data.data[: compare_limit]

    def add_at(self, time, another_audio_data):
        """
        Adds the input `another_audio_data` to this `AudioData` 
        at the `time` specified in seconds. If `another_audio_data` has fewer channels than
        this `AudioData`, the `another_audio_data` will be resampled to match.
        In this case, this method will modify `another_audio_data`.

        """
        offset = int(time * self.sampleRate)
        extra = offset + len(another_audio_data.data) - len(self.data)
        self.pad_with_zeros(extra)
        if another_audio_data.numChannels < self.numChannels:
            # Resample another_audio_data
            another_audio_data.data = numpy.repeat(another_audio_data.data, self.numChannels).reshape(len(another_audio_data), self.numChannels)
            another_audio_data.numChannels = self.numChannels
        self.data[offset : offset + len(another_audio_data.data)] += another_audio_data.data 

    def __len__(self):
        if self.data is not None:
            return len(self.data)
        else:
            return 0

    def __add__(self, other):
        """Supports stuff like this: sound3 = sound1 + sound2"""
        return assemble([self, other], numChannels=self.numChannels,
                            sampleRate=self.sampleRate)

    def encode(self, filename=None, mp3=None):
        """
        Outputs an MP3 or WAVE file to `filename`.
        Format is determined by `mp3` parameter.
        """
        if not mp3 and filename.lower().endswith('.wav'):
            mp3 = False
        else:
            mp3 = True
        if mp3:
            foo, tempfilename = tempfile.mkstemp(".wav")
            os.close(foo)
        else:
            tempfilename = filename
        fid = open(tempfilename, 'wb')
        # Based on Scipy svn
        # http://projects.scipy.org/pipermail/scipy-svn/2007-August/001189.html
        fid.write('RIFF')
        fid.write(struct.pack('<i', 0))  # write a 0 for length now, we'll go back and add it later
        fid.write('WAVE')
        # fmt chunk
        fid.write('fmt ')
        if self.data.ndim == 1:
            noc = 1
        else:
            noc = self.data.shape[1]
        bits = self.data.dtype.itemsize * 8
        sbytes = self.sampleRate * (bits / 8) * noc
        ba = noc * (bits / 8)
        fid.write(struct.pack('<ihHiiHH', 16, 1, noc, self.sampleRate, sbytes, ba, bits))
        # data chunk
        fid.write('data')
        fid.write(struct.pack('<i', self.data.nbytes))
        self.data.tofile(fid)
        # Determine file size and place it in correct
        # position at start of the file.
        size = fid.tell()
        fid.seek(4)
        fid.write(struct.pack('<i', size - 8))
        fid.close()
        if not mp3:
            return tempfilename
        # now convert it to mp3
        if not filename.lower().endswith('.mp3'):
            filename = filename + '.mp3'
        try:
            bitRate = MP3_BITRATE
        except NameError:
            bitRate = 128
        ffmpeg(tempfilename, filename, bitRate=bitRate, verbose=self.verbose)
        if tempfilename != filename:
            if self.verbose:
                print >> sys.stderr, "Deleting: %s" % tempfilename
            os.remove(tempfilename)
        return filename

    def unload(self):
        self.data = None
        if self.convertedfile:
            if self.verbose:
                print >> sys.stderr, "Deleting: %s" % self.convertedfile
            os.remove(self.convertedfile)
            self.convertedfile = None

    def render(self, start=0.0, to_audio=None, with_source=None):
        if not to_audio:
            return self
        if with_source != self:
            return
        to_audio.add_at(start, self)
        return

    @property
    def duration(self):
        return float(self.endindex) / self.sampleRate

    @property
    def source(self):
        return self


class AudioData32(AudioData):
    """A 32-bit variant of AudioData, intended for data collection on
    audio rendering with headroom."""
    def __init__(self, filename=None, ndarray = None, shape=None, sampleRate=None, numChannels=None, defer=False, verbose=True):
        """
        Special form of AudioData to allow for headroom when collecting samples.
        """
        self.verbose = verbose
        self.defer = defer
        self.filename = filename
        self.sampleRate = sampleRate
        self.numChannels = numChannels
        self.convertedfile = None
        if shape is None and isinstance(ndarray, numpy.ndarray) and not self.defer:
            self.data = numpy.zeros(ndarray.shape, dtype=numpy.int32)
        elif shape is not None and not self.defer:
            self.data = numpy.zeros(shape, dtype=numpy.int32)
        elif not self.defer and self.filename:
            self.load()
        else:
            self.data = None
        self.endindex = 0
        if ndarray is not None and self.data is not None:
            self.endindex = len(ndarray)
            self.data[0:self.endindex] = ndarray

    def load(self):
        if isinstance(self.data, numpy.ndarray):
            return
        temp_file_handle = None
        if self.filename.lower().endswith(".wav") and (self.sampleRate, self.numChannels) == (44100, 2):
            file_to_read = self.filename
        elif self.convertedfile:
            file_to_read = self.convertedfile
        else:
            temp_file_handle, self.convertedfile = tempfile.mkstemp(".wav")
            self.sampleRate, self.numChannels = ffmpeg(self.filename, self.convertedfile, overwrite=True,
                    numChannels=self.numChannels, sampleRate=self.sampleRate, verbose=self.verbose)
            file_to_read = self.convertedfile

        w = wave.open(file_to_read, 'r')
        numFrames = w.getnframes()
        raw = w.readframes(numFrames)
        sampleSize = numFrames * self.numChannels
        data = numpy.frombuffer(raw, dtype="<h", count=sampleSize)
        ndarray = numpy.array(data, dtype=numpy.int16)
        if self.numChannels > 1:
            ndarray.resize((numFrames, self.numChannels))
        self.data = numpy.zeros(ndarray.shape, dtype=numpy.int32)
        self.endindex = 0
        if ndarray is not None:
            self.endindex = len(ndarray)
            self.data[0:self.endindex] = ndarray
        if temp_file_handle is not None:
            os.close(temp_file_handle)
        w.close()

    def encode(self, filename=None, mp3=None):
        """
        Outputs an MP3 or WAVE file to `filename`.
        Format is determined by `mp3` parameter.
        """
        normalized = self.normalized()
        temp_file_handle = None
        if not mp3 and filename.lower().endswith('.wav'):
            mp3 = False
        else:
            mp3 = True
        if mp3:
            temp_file_handle, tempfilename = tempfile.mkstemp(".wav")
        else:
            tempfilename = filename
        fid = open(tempfilename, 'wb')
        # Based on Scipy svn
        # http://projects.scipy.org/pipermail/scipy-svn/2007-August/001189.html
        fid.write('RIFF')
        fid.write(struct.pack('<i', 0))  # write a 0 for length now, we'll go back and add it later
        fid.write('WAVE')
        # fmt chunk
        fid.write('fmt ')
        if normalized.ndim == 1:
            noc = 1
        else:
            noc = normalized.shape[1]
        bits = normalized.dtype.itemsize * 8
        sbytes = self.sampleRate * (bits / 8) * noc
        ba = noc * (bits / 8)
        fid.write(struct.pack('<ihHiiHH', 16, 1, noc, self.sampleRate, sbytes, ba, bits))
        # data chunk
        fid.write('data')
        fid.write(struct.pack('<i', normalized.nbytes))
        normalized.tofile(fid)
        # Determine file size and place it in correct
        # position at start of the file.
        size = fid.tell()
        fid.seek(4)
        fid.write(struct.pack('<i', size - 8))
        fid.close()
        if not mp3:
            return tempfilename
        # now convert it to mp3
        if not filename.lower().endswith('.mp3'):
            filename = filename + '.mp3'
        try:
            bitRate = MP3_BITRATE
        except NameError:
            bitRate = 128
        ffmpeg(tempfilename, filename, bitRate=bitRate, verbose=self.verbose)
        if tempfilename != filename:
            if self.verbose:
                print >> sys.stderr, "Deleting: %s" % tempfilename
            os.remove(tempfilename)
        if temp_file_handle is not None:
            os.close(temp_file_handle)
        return filename

    def normalized(self):
        """Return to 16-bit for encoding."""
        factor = 32767.0 / numpy.max(numpy.absolute(self.data.flatten()))
        # If the max was 32768, don't bother scaling:
        if factor < 1.000031:
            return (self.data * factor).astype(numpy.int16)
        else:
            return self.data.astype(numpy.int16)

    def pad_with_zeros(self, num_samples):
        if num_samples > 0:
            if self.numChannels == 1:
                extra_shape = (num_samples,)
            else:
                extra_shape = (num_samples, self.numChannels)
            self.data = numpy.append(self.data,
                                     numpy.zeros(extra_shape, dtype=numpy.int32), axis=0)

def getpieces(audioData, segs):
    """
    Collects audio samples for output.
    Returns a new `AudioData` where the new sample data is assembled
    from the input audioData according to the time offsets in each
    of the elements of the input segs (commonly an `AudioQuantumList`).

    :param audioData: an `AudioData` object
    :param segs: an iterable containing objects that may be accessed
        as slices or indices for an `AudioData`
    """

    # Ensure that we have data
    if audioData.data == None or audioData.defer:
        audioData.data = None
        audioData.load()

    dur = 0
    for s in segs:
        dur += int(s.duration * audioData.sampleRate)
    # if I wanted to add some padding to the length, I'd do it here

    #determine shape of new array
    if len(audioData.data.shape) > 1:
        newshape = (dur, audioData.data.shape[1])
        newchans = audioData.data.shape[1]
    else:
        newshape = (dur,)
        newchans = 1

    #make accumulator segment
    newAD = AudioData(shape=newshape, sampleRate=audioData.sampleRate,
                    numChannels=newchans, defer=False, verbose=audioData.verbose)

    #concatenate segs to the new segment
    for s in segs:
        newAD.append(audioData[s])
    # audioData.unload()
    return newAD


def assemble(audioDataList, numChannels=1, sampleRate=44100, verbose=True):
    """
    Collects audio samples for output.
    Returns a new `AudioData` object assembled
    by concatenating all the elements of audioDataList.

    :param audioDataList: a list of `AudioData` objects
    """
    return AudioData(ndarray=numpy.concatenate([a.data for a in audioDataList]),
                        numChannels=numChannels,
                        sampleRate=sampleRate, defer=False, verbose=verbose)


def mix(dataA, dataB, mix=0.5):
    """
    Mixes two `AudioData` objects. Assumes they have the same sample rate
    and number of channels.

    Mix takes a float 0-1 and determines the relative mix of two audios.
    i.e., mix=0.9 yields greater presence of dataA in the final mix.
    """
    if dataA.endindex > dataB.endindex:
        newdata = AudioData(ndarray=dataA.data, sampleRate=dataA.sampleRate, numChannels=dataA.numChannels, defer=False)
        newdata.data *= float(mix)
        newdata.data[:dataB.endindex] += dataB.data[:] * (1 - float(mix))
    else:
        newdata = AudioData(ndarray=dataB.data, sampleRate=dataB.sampleRate, numChannels=dataB.numChannels, defer=False)
        newdata.data *= 1 - float(mix)
        newdata.data[:dataA.endindex] += dataA.data[:] * float(mix)
    return newdata


def normalize(audio):
    """
    For compatibility with some legacy Wub Machine calls.
    """
    return audio.normalized()


def __genFade(fadeLength, dimensions=1):
    """
    Internal helper for fadeEdges()
    """
    fadeOut = numpy.linspace(1.0, 0.0, fadeLength) ** 2
    if dimensions == 2:
        return fadeOut[:, numpy.newaxis]
    return fadeOut


def fadeEdges(input_, fadeLength=50):
    """
    Fade in/out the ends of an audioData to prevent clicks/pops at edges.
    Optional fadeLength argument is the number of samples to fade in/out.
    """
    if isinstance(input_, AudioData):
        ad = input_.data
    elif isinstance(input_, numpy.ndarray):
        ad = input_
    else:
        raise Exception("Cannot fade edges of unknown datatype.")
    fadeOut = __genFade(min(fadeLength, len(ad)), ad.shape[1])
    ad[0:fadeLength] *= fadeOut[::-1]
    ad[-1 * fadeLength:] *= fadeOut
    return input_


def truncatemix(dataA, dataB, mix=0.5):
    """
    Mixes two `AudioData` objects. Assumes they have the same sample rate
    and number of channels.

    Mix takes a float 0-1 and determines the relative mix of two audios.
    i.e., mix=0.9 yields greater presence of dataA in the final mix.

    If dataB is longer than dataA, dataB is truncated to dataA's length.
    Note that if dataA is longer than dataB, dataA will not be truncated.
    """
    newdata = AudioData(ndarray=dataA.data, sampleRate=dataA.sampleRate,
                        numChannels=dataA.numChannels, verbose=False)
    newdata.data *= float(mix)
    if dataB.endindex > dataA.endindex:
        newdata.data[:] += dataB.data[:dataA.endindex] * (1 - float(mix))
    else:
        newdata.data[:dataB.endindex] += dataB.data[:] * (1 - float(mix))
    return newdata


def megamix(dataList):
    """
    Mix together any number of `AudioData` objects. Keep the shape of
    the first one in the list. Assume they all have the same sample rate
    and number of channels.
    """
    if not isinstance(dataList, list):
        raise TypeError('input must be a list of AudioData objects')
    newdata = AudioData(shape=dataList[0].data.shape, sampleRate=dataList[0].sampleRate,
                            numChannels=dataList[0].numChannels, defer=False)
    for adata in dataList:
        if not isinstance(adata, AudioData):
            raise TypeError('input must be a list of AudioData objects')
        if len(adata) > len(newdata):
            newseg = AudioData(ndarray=adata[:newdata.endindex].data,
                                numChannels=newdata.numChannels,
                                sampleRate=newdata.sampleRate, defer=False)
            newseg.endindex = newdata.endindex
        else:
            newseg = AudioData(ndarray=adata.data,
                                numChannels=newdata.numChannels,
                                sampleRate=newdata.sampleRate, defer=False)
            newseg.endindex = adata.endindex
        newdata.data[:newseg.endindex] += (newseg.data / float(len(dataList))).astype(newdata.data.dtype)
    newdata.endindex = len(newdata)
    return newdata


class LocalAudioFile(AudioData):
    """
    The basic do-everything class for remixing. Acts as an `AudioData`
    object, but with an added `analysis` selector which is an
    `AudioAnalysis` object. It conditionally uploads the file
    it was initialized with. If the file is already known to the
    Analyze API, then it does not bother uploading the file.
    """

    def __new__(cls, filename, verbose=True, defer=False, sampleRate=None, numChannels=None):
        # There must be a better way to avoid collisions between analysis files and .wav files
        if filename is not None and '.analysis.en' in filename:
            print >> sys.stderr, "Reading analysis from local file " + filename
            f = open(filename, 'rb')
            audiofile = cPickle.load(f)
            f.close()
            return audiofile
        else:
            # This just creates the object and goes straight on to initializing it
            return AudioData.__new__(cls, filename=filename, verbose=verbose, defer=defer, sampleRate=sampleRate)

    def __init__(self, filename, verbose=True, defer=False, sampleRate=None, numChannels=None):
        """
        :param filename: path to a local MP3 file
        """
        # We have to skip the initialization here as the local file is already a complete object
        if '.analysis.en' in filename:
            self.is_local = True
        else:
            AudioData.__init__(self, filename=filename, verbose=verbose, defer=defer,
                                sampleRate=sampleRate, numChannels=numChannels)
            track_md5 = hashlib.md5(file(self.filename, 'rb').read()).hexdigest()

            if verbose:
                print >> sys.stderr, "Computed MD5 of file is " + track_md5
            try:
                if verbose:
                    print >> sys.stderr, "Probing for existing analysis"
                tempanalysis = AudioAnalysis(track_md5)
            except Exception:
                if verbose:
                    print >> sys.stderr, "Analysis not found. Uploading..."
                tempanalysis = AudioAnalysis(filename)

            self.analysis = tempanalysis
            self.analysis.source = self
            self.is_local = False

    # Save out as a pickled file.
    def save(self):
        # If we loaded from a local file, there's no need to save
        if self.is_local is True:
            print >> sys.stderr, "Analysis was loaded from local file, not saving"
        else:
            input_path = os.path.split(self.filename)[0]
            input_file = os.path.split(self.filename)[1]
            path_to_wave = self.convertedfile
            wav_filename = input_file + '.wav'
            new_path = os.path.abspath(input_path) + os.path.sep
            wav_path = new_path + wav_filename
            try:
                shutil.copyfile(path_to_wave, wav_path)
            except shutil.Error:
                print >> sys.stderr, "Error when moving .wav file:  the same file may already exist in this folder"
                return
            self.convertedfile = wav_path
            analysis_filename = input_file + '.analysis.en'
            analysis_path = new_path + analysis_filename
            print >> sys.stderr, "Saving analysis to local file " + analysis_path
            f = open(analysis_path, 'wb')
            cPickle.dump(self, f)
            f.close()

    def toxml(self, context=None):
        raise NotImplementedError

    @property
    def duration(self):
        """
        Since we consider `AudioFile` to be an evolved version of
        `AudioData`, we return the measured duration from the analysis.
        """
        return self.analysis.duration

    def __setstate__(self, state):
        """
        Recreates circular reference after unpickling.
        """
        self.__dict__.update(state)
        self.analysis.source = weakref.proxy(self)


class LocalAnalysis(object):
    """
    Like `LocalAudioFile`, it conditionally uploads the file with which
    it was initialized. Unlike `LocalAudioFile`, it is not a subclass of
    `AudioData`, so contains no sample data.
    """
    def __init__(self, filename, verbose=True):
        """
        :param filename: path to a local MP3 file
        """

        track_md5 = hashlib.md5(file(filename, 'rb').read()).hexdigest()
        if verbose:
            print >> sys.stderr, "Computed MD5 of file is " + track_md5
        try:
            if verbose:
                print >> sys.stderr, "Probing for existing analysis"
            tempanalysis = AudioAnalysis(track_md5)
        except Exception:
            if verbose:
                print >> sys.stderr, "Analysis not found. Uploading..."
            tempanalysis = AudioAnalysis(filename)

        self.analysis = tempanalysis
        self.analysis.source = self

class AudioQuantum(AudioRenderable):
    """
    A unit of musical time, identified at minimum with a start time and
    a duration, both in seconds. It most often corresponds with a `section`,
    `bar`, `beat`, `tatum`, or (by inheritance) `segment` obtained from an Analyze
    API call.

    Additional properties include:

    end
        computed time offset for convenience: `start` + `duration`
    container
        a circular reference to the containing `AudioQuantumList`,
        created upon creation of the `AudioQuantumList` that covers
        the whole track
    """
    def __init__(self, start=0, duration=0, kind=None, confidence=None, source=None) :
        """
        Initializes an `AudioQuantum`.

        :param start: offset from the start of the track, in seconds
        :param duration: length of the `AudioQuantum`
        :param kind: string containing what kind of rhythm unit it came from
        :param confidence: float between zero and one
        """
        self.start = start
        self.duration = duration
        self.kind = kind
        self.confidence = confidence
        self._source = source

    def get_end(self):
        return self.start + self.duration

    end = property(get_end, doc="""
    A computed property: the sum of `start` and `duration`.
    """)

    def get_source(self):
        "Returns itself or its parent."
        if self._source:
            return self._source
        else:
            source = None
            try:
                source = self.container.source
            except AttributeError:
                source = None
            return source

    def set_source(self, value):
        if isinstance(value, AudioData):
            self._source = value
        else:
            raise TypeError("Source must be an instance of echonest.remix.audio.AudioData")

    source = property(get_source, set_source, doc="""
    The `AudioData` source for the AudioQuantum.
    """)

    def parent(self):
        """
        Returns the containing `AudioQuantum` in the rhythm hierarchy:
        a `tatum` returns a `beat`, a `beat` returns a `bar`, and a `bar` returns a
        `section`.
        Note that some AudioQuantums have no parent.  None will be returned in this case.
        """
        parent_dict = {'tatum': 'beats',
                       'beat':  'bars',
                       'bar':   'sections'}
        try:
            all_chunks = getattr(self.container.container, parent_dict[self.kind])
            for chunk in all_chunks:
                if self.start < chunk.end and self.end > chunk.start:
                    return chunk
            return None
        except LookupError:
            # Might not be in pars, might not have anything in parent.
            return None

    def children(self):
        """
        Returns an `AudioQuantumList` of the AudioQuanta that it contains,
        one step down the hierarchy. A `beat` returns `tatums`, a `bar` returns
        `beats`, and a `section` returns `bars`.
        """
        children_dict = {'beat':    'tatums',
                         'bar':     'beats',
                         'section': 'bars'}
        try:
            all_chunks = getattr(self.container.container, children_dict[self.kind])
            child_chunks = AudioQuantumList(kind=children_dict[self.kind])
            for chunk in all_chunks:
                if chunk.start >= self.start and chunk.end <= self.end: 
                    child_chunks.append(chunk)
                    continue
            return child_chunks
        except LookupError:
            return None

    @property
    def segments(self):
        """
        Returns any segments that overlap or are in the same timespan as the AudioQuantum.
        Note that this means that some segments will appear in more than one AudioQuantum.
        This function, thus, is NOT suited to rhythmic modifications.
        """
        # If this is a segment, return it in a list so we can iterate over it
        if self.kind == 'segment':
            return [self]

        all_segments = self.source.analysis.segments
        filtered_segments = AudioQuantumList(kind="segment")
        
        # Filter and then break once we've got the needed segments
        for segment in all_segments:
            if segment.start < self.end and segment.end > self.start:
                filtered_segments.append(segment)
            elif len(filtered_segments) != 0:
                break
        return filtered_segments

    def mean_pitches(self):
        """
        Returns a pitch vector that is the mean of the pitch vectors of any segments 
        that overlap this AudioQuantum.
        Note that this means that some segments will appear in more than one AudioQuantum.
        """
        temp_pitches = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        segments = self.segments
        for segment in segments:
            for index, pitch in enumerate(segment.pitches):
                temp_pitches[index] = temp_pitches[index] + pitch
            mean_pitches = [pitch / len(segments) for pitch in temp_pitches]
            return mean_pitches
    
    def mean_timbre(self):
        """
        Returns a timbre vector that is the mean of the pitch vectors of any segments 
        that overlap this AudioQuantum.
        Note that this means that some segments will appear in more than one AudioQuantum.
        """
        temp_timbre = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        segments = self.segments
        for segment in segments:
            for index, timbre in enumerate(segment.timbre):
                temp_timbre[index] = temp_timbre[index] + timbre
            mean_timbre = [timbre / len(segments) for timbre in temp_timbre]
            return mean_timbre


    def mean_loudness(self):
        """
        Returns the mean of the maximum loudness of any segments that overlap this AudioQuantum. 
        Note that this means that some segments will appear in more than one AudioQuantum.
        """
        loudness_average = 0
        segments = self.segments
        for segment in self.segments:
            loudness_average = loudness_average + segment.loudness_max
        return loudness_average / len(segments)

    def group(self):
        """
        Returns the `children`\() of the `AudioQuantum`\'s `parent`\().
        In other words: 'siblings'. If no parent is found, then return the
        `AudioQuantumList` for the whole track.
        """
        if self.parent():
            return self.parent().children()
        else:
            return self.container

    def prev(self, step=1):
        """
        Step backwards in the containing `AudioQuantumList`.
        Returns `self` if a boundary is reached.
        """
        group = self.container
        try:
            loc = group.index(self)
            new = max(loc - step, 0)
            return group[new]
        except Exception:
            return self

    def next(self, step=1):
        """
        Step forward in the containing `AudioQuantumList`.
        Returns `self` if a boundary is reached.
        """
        group = self.container
        try:
            loc = group.index(self)
            new = min(loc + step, len(group))
            return group[new]
        except Exception:
            return self

    def __str__(self):
        """
        Lists the `AudioQuantum`.kind with start and
        end times, in seconds, e.g.::

            "segment (20.31 - 20.42)"
        """
        return "%s (%.2f - %.2f)" % (self.kind, self.start, self.end)

    def __repr__(self):
        """
        A string representing a constructor, including kind, start time,
        duration, and (if it exists) confidence, e.g.::

            "AudioQuantum(kind='tatum', start=42.198267, duration=0.1523394)"
        """
        if self.confidence is not None:
            return "AudioQuantum(kind='%s', start=%f, duration=%f, confidence=%f)" % (self.kind, self.start, self.duration, self.confidence)
        else:
            return "AudioQuantum(kind='%s', start=%f, duration=%f)" % (self.kind, self.start, self.duration)

    def local_context(self):
        """
        Returns a tuple of (*index*, *length*) within rhythm siblings, where
        *index* is the (zero-indexed) position within its `group`\(), and
        *length* is the number of siblings within its `group`\().
        """
        group = self.group()
        count = len(group)
        try:
            loc  = group.index(self)
        except Exception:  # seem to be some uncontained beats
            loc = 0
        return (loc, count,)

    def absolute_context(self):
        """
        Returns a tuple of (*index*, *length*) within the containing
        `AudioQuantumList`, where *index* is the (zero-indexed) position within
        its container, and *length* is the number of siblings within the
        container.
        """
        group = self.container
        count = len(group)
        loc = group.index(self)
        return (loc, count,)

    def context_string(self):
        """
        Returns a one-indexed, human-readable version of context.
        For example::

            "bar 4 of 142, beat 3 of 4, tatum 2 of 3"
        """
        if self.parent() and self.kind != "bar":
            return "%s, %s %i of %i" % (self.parent().context_string(),
                                  self.kind, self.local_context()[0] + 1,
                                  self.local_context()[1])
        else:
            return "%s %i of %i" % (self.kind, self.absolute_context()[0] + 1,
                                  self.absolute_context()[1])

    def __getstate__(self):
        """
        Eliminates the circular reference for pickling.
        """
        dictclone = self.__dict__.copy()
        if 'container' in dictclone:
            del dictclone['container']
        return dictclone

    def toxml(self, context=None):
        attributedict = {'duration': str(self.duration),
                         'start': str(self.start)}
        try:
            if not(hasattr(context, 'source') and self.source == context.source):
                attributedict['source'] = self.source.analysis.identifier
        except Exception:
            pass
        xml = etree.Element(self.kind, attrib=attributedict)
        if context:
            return xml
        else:
            return minidom.parseString(xml).toprettyxml()

    def render(self, start=0.0, to_audio=None, with_source=None):
        if not to_audio:
            source = self.resolve_source(with_source)
            return source[self]
        if with_source != self.source:
            return
        to_audio.add_at(start, with_source[self])
        return


class AudioSegment(AudioQuantum):
    """
    Subclass of `AudioQuantum` for the data-rich segments returned by
    the Analyze API.
    """
    def __init__(self, start=0., duration=0., pitches = None, timbre = None,
                 loudness_begin=0., loudness_max=0., time_loudness_max=0.,
                 loudness_end=None, kind='segment', source=None):
        """
        Initializes an `AudioSegment`.

        :param start: offset from start of the track, in seconds
        :param duration: duration of the `AudioSegment`, in seconds
        :param pitches: a twelve-element list with relative loudnesses of each
                pitch class, from C (pitches[0]) to B (pitches[11])
        :param timbre: a twelve-element list with the loudness of each of a
                principal component of time and/or frequency profile
        :param kind: string identifying the kind of AudioQuantum: "segment"
        :param loudness_begin: loudness in dB at the start of the segment
        :param loudness_max: loudness in dB at the loudest moment of the
                segment
        :param time_loudness_max: time (in sec from start of segment) of
                loudest moment
        :param loudness_end: loudness at end of segment (if it is given)
        """
        self.start = start
        self.duration = duration
        self.pitches = pitches or []
        self.timbre = timbre or []
        self.loudness_begin = loudness_begin
        self.loudness_max = loudness_max
        self.time_loudness_max = time_loudness_max
        if loudness_end:
            self.loudness_end = loudness_end
        self.kind = kind
        self.confidence = None
        self._source = source
        

    @property
    def tatum(self):
        """
        Returns the tatum that overlaps most with the segment
        Note that some segments have NO overlapping tatums.
        If this is the case, None will be returned.
        """
        all_tatums = self.source.analysis.tatums
        filtered_tatums = []
        for tatum in all_tatums:
            # If the segment contains the tatum
            if self.start < tatum.start and self.end > tatum.end:
                filtered_tatums.append((tatum, tatum.duration))
            # If the tatum contains the segment
            elif tatum.start < self.start and tatum.end > self.end:
                filtered_tatums.append((tatum, self.duration))
            # If the tatum overlaps and starts before the segment
            elif tatum.start < self.start and tatum.end > self.start:
                filtered_tatums.append((tatum, tatum.end - self.start))
            # If the tatum overlaps and starts after the segment
            elif tatum.start < self.end and tatum.end > self.end:
                filtered_tatums.append((tatum, self.end - tatum.start))
            # If we're past the segment, stop
            elif tatum.start > self.end:
                break

        # Sort and get the tatum with the maximum overlap
        sorted_tatums = sorted(filtered_tatums, key=lambda tatum: tatum[1], reverse=True)
        if not sorted_tatums:
            return None
        else:
            return sorted_tatums[0][0]

    @property
    def beat(self):
        return self.tatum.parent



class ModifiedRenderable(AudioRenderable):
    """Class that contains any AudioRenderable, but overrides the
    render() method with nested effects, called sequentially on the
    result of the preceeding effect."""
    def __init__(self, original, effects=[]):
        if isinstance(original, ModifiedRenderable):
            self._original = original._original
            self._effects = original._effects + effects
        else:
            self._original = original
            self._effects = effects

    @property
    def duration(self):
        dur = self._original.duration
        for effect in self._effects:
            if hasattr(effect, 'duration'):
                dur = effect.duration(dur)
        return dur

    @property
    def source(self):
        return self._original.source

    @property
    def sources(self):
        return self._original.sources

    def render(self, start=0.0, to_audio=None, with_source=None):
        if not to_audio:
            base = self._original.render(with_source=with_source)
            copy = AudioData32(ndarray=base.data, sampleRate=base.sampleRate, numChannels=base.numChannels, defer=False)
            for effect in self._effects:
                copy = effect.modify(copy)
            return copy
        if with_source != self.source:
            return
        base = self._original.render(with_source=with_source)
        copy = AudioData32(ndarray=base.data, shape=base.data.shape, sampleRate=base.sampleRate, numChannels=base.numChannels, defer=False)
        for effect in self._effects:
            copy = effect.modify(copy)
        to_audio.add_at(start, copy)
        return

    def toxml(self, context=None):
        outerattributedict = {'duration': str(self.duration)}
        node = etree.Element("modified_audioquantum", attrib=outerattributedict)

        innerattributedict = {'duration': str(self._original.duration),
                              'start': str(self._original.start)}
        try:
            if not(hasattr(context, 'source') and self.source == context.source):
                innerattributedict['source'] = self.source.analysis.identifier
        except Exception:
            pass
        orignode = etree.Element(self._original.kind, attrib=innerattributedict)
        node.append(orignode)
        fx = etree.Element('effects')
        for effect in self._effects:
            fxdict = {'id': '%s.%s' % (effect.__module__, effect.__class__.__name__)}
            fxdict.update(effect.__dict__)
            fx.append(etree.Element('effect', attrib=fxdict))
        node.append(fx)
        if context:
            return node
        else:
            return minidom.parseString(node).toprettyxml()


class AudioEffect(object):
    def __call__(self, aq):
        return ModifiedRenderable(aq, [self])


class LevelDB(AudioEffect):
    def __init__(self, change):
        self.change = change

    def modify(self, adata):
        adata.data *= pow(10., self.change / 20.)
        return adata


class AmplitudeFactor(AudioEffect):
    def __init__(self, change):
        self.change = change

    def modify(self, adata):
        adata.data *= self.change
        return adata


class TimeTruncateFactor(AudioEffect):
    def __init__(self, factor):
        self.factor = factor

    def duration(self, old_duration):
        return old_duration * self.factor

    def modify(self, adata):
        endindex = int(self.factor * len(adata))
        if self.factor > 1:
            adata.pad_with_zeros(endindex - len(adata))
        adata.endindex = endindex
        return adata[:endindex]


class TimeTruncateLength(AudioEffect):
    def __init__(self, new_duration):
        self.new_duration = new_duration

    def duration(self, old_duration):
        return self.new_duration

    def modify(self, adata):
        endindex = int(self.new_duration * adata.sampleRate)
        if self.new_duration > adata.duration:
            adata.pad_with_zeros(endindex - len(adata))
        adata.endindex = endindex
        return adata[:endindex]


class AudioQuantumList(list, AudioRenderable):
    """
    A container that enables content-based selection and filtering.
    A `List` that contains `AudioQuantum` objects, with additional methods
    for manipulating them.

    When an `AudioQuantumList` is created for a track via a call to the
    Analyze API, `attach`\() is called so that its container is set to the
    containing `AudioAnalysis`, and the container of each of the
    `AudioQuantum` list members is set to itself.

    Additional accessors now include AudioQuantum elements such as
    `start`, `duration`, and `confidence`, which each return a List of the
    corresponding properties in the contained AudioQuanta. A special name
    is `kinds`, which returns a List of the `kind` of each `AudioQuantum`.
    If `AudioQuantumList.kind` is "`segment`", then `pitches`, `timbre`,
    `loudness_begin`, `loudness_max`, `time_loudness_max`, and `loudness_end`
    are available.
    """
    def __init__(self, initial = None, kind = None, container = None, source = None):
        """
        Initializes an `AudioQuantumList`. All parameters are optional.

        :param initial: a `List` type with the initial contents
        :param kind: a label for the kind of `AudioQuantum` contained
            within
        :param container: a reference to the containing `AudioAnalysis`
        :param source: a reference to the `AudioData` with the corresponding samples
            and time base for the contained AudioQuanta
        """
        list.__init__(self)
        self.kind = None
        self._source = None
        if isinstance(initial, AudioQuantumList):
            self.kind = initial.kind
            self.container = initial.container
            self._source = initial.source
        if kind:
            self.kind = kind
        if container:
            self.container = container
        if source:
            self._source = source
        if initial:
            self.extend(initial)

    def get_many(attribute):
        def fun(self):
            """
            Returns a list of %s for each `AudioQuantum`.
            """ % attribute
            return [getattr(x, attribute) for x in list.__iter__(self)]
        return fun

    def get_many_if_segment(attribute):
        def fun(self):
            """
            Returns a list of %s for each `Segment`.
            """ % attribute
            if self.kind == 'segment':
                return [getattr(x, attribute) for x in list.__iter__(self)]
            else:
                raise AttributeError("<%s> only accessible for segments" % (attribute,))
        return fun

    def get_duration(self):
        return sum(self.durations)
        #return sum([x.duration for x in self])

    def get_source(self):
        "Returns its own or its parent's source."
        if len(self) < 1:
            return
        if self._source:
            return self._source
        else:
            try:
                source = self.container.source
            except AttributeError:
                source = self[0].source
            return source

    def set_source(self, value):
        "Checks input to see if it is an `AudioData`."
        if isinstance(value, AudioData):
            self._source = value
        else:
            raise TypeError("Source must be an instance of echonest.remix.audio.AudioData")

    durations  = property(get_many('duration'))
    kinds      = property(get_many('kind'))
    start      = property(get_many('start'))
    confidence = property(get_many('confidence'))

    pitches           = property(get_many_if_segment('pitches'))
    timbre            = property(get_many_if_segment('timbre'))
    loudness_begin    = property(get_many_if_segment('loudness_begin'))
    loudness_max      = property(get_many_if_segment('loudness_max'))
    time_loudness_max = property(get_many_if_segment('time_loudness_max'))
    loudness_end      = property(get_many_if_segment('loudness_end'))

    source = property(get_source, set_source, doc="""
    The `AudioData` source for the `AudioQuantumList`.
    """)

    duration = property(get_duration, doc="""
    Total duration of the `AudioQuantumList`.
    """)

    def sources(self):
        ss = set()
        for aq in list.__iter__(self):
            ss.update(aq.sources())
        return ss

    def attach(self, container):
        """
        Create circular references to the containing `AudioAnalysis` and for the
        contained `AudioQuantum` objects.
        """
        self.container = container
        for i in self:
            i.container = self

    def __getstate__(self):
        """
        Eliminates the circular reference for pickling.
        """
        dictclone = self.__dict__.copy()
        if 'container' in dictclone:
            del dictclone['container']
        return dictclone

    def toxml(self, context=None):
        xml = etree.Element("sequence")
        xml.attrib['duration'] = str(self.duration)
        if not context:
            xml.attrib['source'] = self.source.analysis.identifier
            for s in self.sources():
                xml.append(s.toxml())
        elif self._source:
            try:
                if self.source != context.source:
                    xml.attrib['source'] = self.source.analysis.identifier
            except Exception:
                pass
        for x in list.__iter__(self):
            xml.append(x.toxml(context=self))
        if context:
            return xml
        else:
            return minidom.parseString(xml).toprettyxml()

    def render(self, start=0.0, to_audio=None, with_source=None):
        if len(self) < 1:
            return
        if not to_audio:
            dur = 0
            tempsource = self.source or list.__getitem__(self, 0).source
            for aq in list.__iter__(self):
                dur += int(aq.duration * tempsource.sampleRate)
            to_audio = self.init_audio_data(tempsource, dur)
        if not hasattr(with_source, 'data'):
            for tsource in self.sources():
                this_start = start
                for aq in list.__iter__(self):
                    aq.render(start=this_start, to_audio=to_audio, with_source=tsource)
                    this_start += aq.duration
                if tsource.defer:
                    tsource.unload()
            return to_audio
        else:
            if with_source not in self.sources():
                return
            for aq in list.__iter__(self):
                aq.render(start=start, to_audio=to_audio, with_source=with_source)
                start += aq.duration


class Simultaneous(AudioQuantumList):
    """
    Stacks all contained AudioQuanta atop one another, adding their respective
    samples. The rhythmic length of the segment is the duration of the first
    `AudioQuantum`, but there can be significant overlap caused by the longest
    segment.

    Sample usage::
        Simultaneous(a.analysis.bars).encode("my.mp3")
    """
    def __init__(self, *args, **kwargs):
        AudioQuantumList.__init__(self, *args, **kwargs)

    def get_duration(self):
        try:
            return self[0].duration
        except Exception:
            return 0.

    duration = property(get_duration, doc="""
        Rhythmic duration of the `Simultaneous` AudioQuanta: the
        same as the duration of the first in the list.
        """)

    def toxml(self, context=None):
        xml = etree.Element("parallel")
        xml.attrib['duration'] = str(self.duration)
        if not context:
            xml.attrib['source'] = self.source.analysis.identifier
        elif self.source != context.source:
            try:
                xml.attrib['source'] = self.source.analysis.identifier
            except Exception:
                pass
        for x in list.__iter__(self):
            xml.append(x.toxml(context=self))
        if context:
            return xml
        else:
            return minidom.parseString(xml).toprettyxml()

    def render(self, start=0.0, to_audio=None, with_source=None):
        if not to_audio:
            tempsource = self.source or list.__getitem__(self, 0).source
            dur = int(max(self.durations) * tempsource.sampleRate)
            to_audio = self.init_audio_data(tempsource, dur)
        if not hasattr(with_source, 'data'):
            for source in self.sources():
                for aq in list.__iter__(self):
                    aq.render(start=start, to_audio=to_audio, with_source=source)
                if source.defer:
                    source.unload()
            return to_audio
        else:
            if with_source not in self.sources():
                return
            else:
                for aq in list.__iter__(self):
                    aq.render(start=start, to_audio=to_audio, with_source=with_source)


def _dataParser(tag, nodes):
    out = AudioQuantumList(kind=tag)
    for n in nodes:
        out.append(AudioQuantum(start=n['start'], kind=tag, confidence=n['confidence']))
    if len(out) > 1:
        for i in range(len(out) - 1) :
            out[i].duration = out[i + 1].start - out[i].start
        out[-1].duration = out[-2].duration
    return out


def _attributeParser(tag, nodes):
    out = AudioQuantumList(kind=tag)
    for n in nodes :
        out.append(AudioQuantum(n['start'], n['duration'], tag))
    return out


def _segmentsParser(nodes):
    out = AudioQuantumList(kind='segment')
    for n in nodes:
        out.append(AudioSegment(start=n['start'], duration=n['duration'],
                                pitches=n['pitches'], timbre=n['timbre'],
                                loudness_begin=n['loudness_start'],
                                loudness_max=n['loudness_max'],
                                time_loudness_max=n['loudness_max_time'],
                                loudness_end=n.get('loudness_end')))
    return out

class FileTypeError(Exception):
    def __init__(self, filename, message):
        self.filename = filename
        self.message = message

    def __str__(self):
        return self.message + ': ' + self.filename


class EchoNestRemixError(Exception):
    """
    Error raised by the Remix API.
    """
    pass

########NEW FILE########
__FILENAME__ = modify
#!/usr/bin/env python
# encoding: utf-8
"""
modify.py

Created by Ben Lacker on 2009-06-12.
Stereo modifications by Peter Sobot on 2011-08-24
"""
from echonest.remix.audio import *
import numpy
import soundtouch

class Modify(soundtouch.SoundTouch):
    def __init__(self, sampleRate=44100, numChannels=1, blockSize = 10000):
        self.setSampleRate(sampleRate)
        self.setChannels(numChannels)
        self.sampleRate = sampleRate
        self.numChannels = numChannels
        self.blockSize = blockSize

    def doInBlocks(self, f, in_data, arg):
        if self.numChannels == 2:
            c = numpy.empty( ( in_data.size, ), dtype=in_data.dtype )
            c[0::2] = in_data[:, 0]
            c[1::2] = in_data[:, 1]
            in_data = c
        elif in_data.ndim > 1:
            in_data = in_data[:, 0]
        collect = []
        if len(in_data) > self.blockSize:
            for x in range(len(in_data)/self.blockSize):
                start = x * self.blockSize
                data = in_data[start:start + self.blockSize -1]
                collect.append(self.processAudio(f, data, arg))
            data = in_data[-1*(len(in_data) % self.blockSize):]
            collect.append(self.processAudio(f, data, arg))
        else:
            collect.append(self.processAudio(f, in_data, arg))
        return assemble(collect, numChannels=self.numChannels, sampleRate=self.sampleRate)

    def processAudio(self, f, data, arg):
        f(arg)
        self.putSamples(data)
        out_data = numpy.array(numpy.zeros((len(data)*2,), dtype=numpy.float32))
        out_samples = self.receiveSamples(out_data)
        shape = (out_samples, )
        if self.numChannels == 2:
            nd = numpy.array( numpy.zeros( ( out_samples, self.numChannels ), dtype=numpy.float32 ) )
            nd[:, 0] = out_data[0::2][:out_samples]
            nd[:, 1] = out_data[1::2][:out_samples]
            out_data = nd
            shape = (out_samples, 2)
        new_ad = AudioData(ndarray=out_data[:out_samples*self.numChannels], shape=shape, 
                    sampleRate=self.sampleRate, numChannels=self.numChannels)
        return new_ad

    def shiftRate(self, audio_data, ratio=1):
        if not isinstance(audio_data, AudioData):
            raise TypeError('First argument must be an AudioData object.')
        if not (isinstance(ratio, int) or isinstance(ratio, float)):
            raise ValueError('Ratio must be an int or float.')
        if (ratio < 0) or (ratio > 10):
            raise ValueError('Ratio must be between 0 and 10.')
        return self.doInBlocks(self.setRate, audio_data.data, ratio)

    def shiftTempo(self, audio_data, ratio):
        if not isinstance(audio_data, AudioData):
            raise TypeError('First argument must be an AudioData object.')
        if not (isinstance(ratio, int) or isinstance(ratio, float)):
            raise ValueError('Ratio must be an int or float.')
        if (ratio < 0) or (ratio > 10):
            raise ValueError('Ratio must be between 0 and 10.')
        return self.doInBlocks(self.setTempo, audio_data.data, ratio)

    def shiftRateChange(self, audio_data, percent):
        if not isinstance(audio_data, AudioData):
            raise TypeError('First argument must be an AudioData object.')
        if not (isinstance(percent, int) or isinstance(percent, float)):
            raise ValueError('Percent must be an int or float.')
        if (percent < -50) or (percent > 100):
            raise ValueError('Percent must be between -50 and 100.')
        return self.doInBlocks(self.setRateChange, audio_data.data, percent)

    def shiftTempoChange(self, audio_data, percent):
        if not isinstance(audio_data, AudioData):
            raise TypeError('First argument must be an AudioData object.')
        if not (isinstance(percent, int) or isinstance(percent, float)):
            raise ValueError('Percent must be an int or float.')
        if (percent < -50) or (percent > 100):
            raise ValueError('Percent must be between -50 and 100.')
        return self.doInBlocks(self.setTempoChange, audio_data.data, percent)

    def shiftPitchSemiTones(self, audio_data, semitones=0):
        if not isinstance(audio_data, AudioData):
            raise TypeError('First argument must be an AudioData object.')
        if not isinstance(semitones, int):
            raise TypeError('Second argument must be an integer.')
        # I think this is right, but maybe it has to be between -12 and 12?
        if abs(semitones) > 60:
            raise ValueError('Semitones argument must be an int between -60 and 60.')
        return self.doInBlocks(self.setPitchSemiTones, audio_data.data, semitones)

    def shiftPitchOctaves(self, audio_data, octaves=0):
        if not isinstance(audio_data, AudioData):
            raise TypeError('First argument must be an AudioData object.')
        if not (isinstance(octaves, int) or isinstance(octaves, float)):
            raise ValueError('Octaves must be an int or float.')
        if abs(octaves) > 5:
            raise ValueError('Octaves argument must be between -5 and 5.')
        # what are the limits? Nothing in soundtouch documentation...
        return self.doInBlocks(self.setPitchOctaves, audio_data.data, octaves)
    
    def shiftPitch(self, audio_data, ratio=1):
        if not isinstance(audio_data, AudioData):
            raise TypeError('First argument must be an AudioData object.')
        if not (isinstance(ratio, int) or isinstance(ratio, float)):
            raise ValueError('Ratio must be an int or float.')
        if (ratio < 0) or (ratio > 10):
            raise ValueError('Ratio must be between 0 and 10.')
        return self.doInBlocks(self.setPitch, audio_data.data, ratio)


########NEW FILE########
__FILENAME__ = exceptionthread
"""
ExceptionThread.py
by Peter Sobot, 2012-04-23
https://gist.github.com/2386993

Base class for a thread that tracks its own exceptions and
raises them when joined by the main thread. Can check for
an exception by doing .join(0) from another thread.
"""

import Queue
import threading
import sys

__author__ = 'psobot'


class ExceptionThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.__status_queue = Queue.Queue()

    def run(self, *args, **kwargs):
        try:
            threading.Thread.run(self)
        except Exception:
            self.__status_queue.put(sys.exc_info())
        self.__status_queue.put(None)

    def join(self, num=None):
        if not self.__status_queue:
            return
        try:
            exc_info = self.__status_queue.get(True, num)
            if exc_info:
                raise exc_info[1], None, exc_info[2]
        except Queue.Empty:
            return
        self.__status_queue = None

########NEW FILE########
__FILENAME__ = ffmpeg
import os
import sys
import time
import numpy
import logging
import tempfile
import subprocess
import cStringIO
from exceptionthread import ExceptionThread

log = logging.getLogger(__name__)

def get_os():
    """returns is_linux, is_mac, is_windows"""
    if hasattr(os, 'uname'):
        if os.uname()[0] == "Darwin":
            return False, True, False
        return True, False, False
    return False, False, True

def ensure_valid(filename):
    command = "en-ffmpeg -i %s -acodec copy -f null -" % filename

    if os.path.getsize(filename) == 0:
        raise ValueError("Input file contains 0 bytes")

    log.info("Calling ffmpeg: %s", command)

    o = subprocess.call(command.split(),
                        stdout=open(os.devnull, 'wb'),
                        stderr=open(os.devnull, 'wb'))
    if o == 0:
        return True
    else:
        raise ValueError("FFMPEG failed to read the file (%d)" % o)


def ffmpeg(infile, outfile=None, overwrite=True, bitRate=None,
          numChannels=None, sampleRate=None, verbose=True, lastTry=False):
    """
    Executes ffmpeg through the shell to convert or read media files.
    If passed a file object, give it to FFMPEG via pipe. Otherwise, allow
    FFMPEG to read the file from disk.

    If `outfile` is passed in, this will return the sampling frequency and
    number of channels in the output file. Otherwise, it will return an
    ndarray object filled with the raw PCM data.
    """
    start = time.time()
    filename = None
    if type(infile) is str or type(infile) is unicode:
        filename = str(infile)

    command = "en-ffmpeg"
    if filename:
        command += " -i \"%s\"" % infile
    else:
        command += " -i pipe:0"

    if overwrite:
        command += " -y"

    if bitRate is not None:
        command += " -ab " + str(bitRate) + "k"

    if numChannels is not None:
        command += " -ac " + str(numChannels)
    else:
        command += " -ac 2"

    if sampleRate is not None:
        command += " -ar " + str(sampleRate)
    else:
        command += " -ar 44100" 

    if outfile is not None:
        command += " \"%s\"" % outfile
    else:
        command += " pipe:1"
    if verbose:
        print >> sys.stderr, command

    (lin, mac, win) = get_os()
    p = subprocess.Popen(
            command,
            shell=True,
            stdin=(None if filename else subprocess.PIPE),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=(not win)
    )

    if filename:
        f, e = p.communicate()
    else:
        try:
            infile.seek(0)
        except:  # if the file is not seekable
            pass
        f, e = p.communicate(infile.read())
        try:
            infile.seek(0)
        except:  # if the file is not seekable
            pass
    #   If FFMPEG couldn't read that, let's write to a temp file
    #   For some reason, this always seems to work from file (but not pipe)
    if 'Could not find codec parameters' in e and not lastTry:
        log.warning("FFMPEG couldn't find codec parameters - writing to temp file.")
        fd, name = tempfile.mkstemp('.audio')
        handle = os.fdopen(fd, 'w')
        infile.seek(0)
        handle.write(infile.read())
        handle.close()
        r = ffmpeg(name,
                   bitRate=bitRate,
                   numChannels=numChannels,
                   sampleRate=sampleRate,
                   verbose=verbose,
                   lastTry=True)
        log.info("Unlinking temp file at %s...", name)
        os.unlink(name)
        return r

    ffmpeg_error_check(e)
    mid = time.time()
    log.info("Decoded in %ss.", (mid - start))
    if outfile:
        return settings_from_ffmpeg(e)
    else:
        return numpy.frombuffer(f, dtype=numpy.int16).reshape((-1, 2))


def ffmpeg_downconvert(infile, lastTry=False):
    """
    Downconvert the given filename (or file-like) object to 32kbps MP3 for analysis.
    Works well if the original file is too large to upload to the Analyze API.
    """
    start = time.time()

    filename = None
    if type(infile) is str or type(infile) is unicode:
        filename = str(infile)

    command = "en-ffmpeg" \
            + (" -i \"%s\"" % infile if filename else " -i pipe:0") \
            + " -b 32k -f mp3 pipe:1"
    log.info("Calling ffmpeg: %s", command)

    (lin, mac, win) = get_os()
    p = subprocess.Popen(
        command,
        shell=True,
        stdin=(None if filename else subprocess.PIPE),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=(not win)
    )
    if filename:
        f, e = p.communicate()
    else:
        infile.seek(0)
        f, e = p.communicate(infile.read())
        infile.seek(0)

    if 'Could not find codec parameters' in e and not lastTry:
        log.warning("FFMPEG couldn't find codec parameters - writing to temp file.")
        fd, name = tempfile.mkstemp('.')
        handle = os.fdopen(fd, 'w')
        infile.seek(0)
        handle.write(infile.read())
        handle.close()
        r = ffmpeg_downconvert(name, lastTry=True)
        log.info("Unlinking temp file at %s...", name)
        os.unlink(name)
        return r
    ffmpeg_error_check(e)

    io = cStringIO.StringIO(f)
    end = time.time()
    io.seek(0, os.SEEK_END)
    bytesize = io.tell()
    io.seek(0)
    log.info("Transcoded to 32kbps mp3 in %ss. Final size: %s bytes.",
             (end - start), bytesize)
    return io


def settings_from_ffmpeg(parsestring):
    """
    Parses the output of ffmpeg to determine sample rate and frequency of
    an audio file.
    """
    parse = parsestring.split('\n')
    freq, chans = 44100, 2
    for line in parse:
        if "Stream #0" in line and "Audio" in line:
            segs = line.split(", ")
            for s in segs:
                if "Hz" in s:
                    #print "Found: "+str(s.split(" ")[0])+"Hz"
                    freq = int(s.split(" ")[0])
                elif "stereo" in s:
                    #print "stereo"
                    chans = 2
                elif "mono" in s:
                    #print "mono"
                    chans = 1
    return freq, chans

ffmpeg_install_instructions = """
en-ffmpeg not found! Please make sure ffmpeg is installed and create a link as follows:
    sudo ln -s `which ffmpeg` /usr/local/bin/en-ffmpeg
"""

def ffmpeg_error_check(parsestring):
    "Looks for known errors in the ffmpeg output"
    parse = parsestring.split('\n')
    error_cases = ["Unknown format",        # ffmpeg can't figure out format of input file
                   "error occur",           # an error occurred
                   "Could not open",        # user doesn't have permission to access file
                   "not found"              # could not find encoder for output file
                   "Invalid data",          # bad input data
                   "Could not find codec",  # corrupted, incomplete, or otherwise bad file
                    ]
    for num, line in enumerate(parse):
        if "command not found" in line or "en-ffmpeg: not found" in line:
            raise RuntimeError(ffmpeg_install_instructions)
        for error in error_cases:
            if error in line:
                report = "\n\t".join(parse[num:])
                raise RuntimeError("ffmpeg conversion error:\n\t" + report)

########NEW FILE########
__FILENAME__ = constants
# -*- coding: ISO-8859-1 -*-

###################################################
## Definitions of the different midi events



###################################################
## Midi channel events (The most usual events)
## also called "Channel Voice Messages"

NOTE_OFF = 0x80
# 1000cccc 0nnnnnnn 0vvvvvvv (channel, note, velocity)

NOTE_ON = 0x90
# 1001cccc 0nnnnnnn 0vvvvvvv (channel, note, velocity)

AFTERTOUCH = 0xA0
# 1010cccc 0nnnnnnn 0vvvvvvv (channel, note, velocity)

CONTINUOUS_CONTROLLER = 0xB0 # see Channel Mode Messages!!!
# 1011cccc 0ccccccc 0vvvvvvv (channel, controller, value)

PATCH_CHANGE = 0xC0
# 1100cccc 0ppppppp (channel, program)

CHANNEL_PRESSURE = 0xD0
# 1101cccc 0ppppppp (channel, pressure)

PITCH_BEND = 0xE0
# 1110cccc 0vvvvvvv 0wwwwwww (channel, value-lo, value-hi)


###################################################
##  Channel Mode Messages (Continuous Controller)
##  They share a status byte.
##  The controller makes the difference here

# High resolution continuous controllers (MSB)

BANK_SELECT = 0x00
MODULATION_WHEEL = 0x01
BREATH_CONTROLLER = 0x02
FOOT_CONTROLLER = 0x04
PORTAMENTO_TIME = 0x05
DATA_ENTRY = 0x06
CHANNEL_VOLUME = 0x07
BALANCE = 0x08
PAN = 0x0A
EXPRESSION_CONTROLLER = 0x0B
EFFECT_CONTROL_1 = 0x0C
EFFECT_CONTROL_2 = 0x0D
GEN_PURPOSE_CONTROLLER_1 = 0x10
GEN_PURPOSE_CONTROLLER_2 = 0x11
GEN_PURPOSE_CONTROLLER_3 = 0x12
GEN_PURPOSE_CONTROLLER_4 = 0x13

# High resolution continuous controllers (LSB)

BANK_SELECT = 0x20
MODULATION_WHEEL = 0x21
BREATH_CONTROLLER = 0x22
FOOT_CONTROLLER = 0x24
PORTAMENTO_TIME = 0x25
DATA_ENTRY = 0x26
CHANNEL_VOLUME = 0x27
BALANCE = 0x28
PAN = 0x2A
EXPRESSION_CONTROLLER = 0x2B
EFFECT_CONTROL_1 = 0x2C
EFFECT_CONTROL_2 = 0x2D
GENERAL_PURPOSE_CONTROLLER_1 = 0x30
GENERAL_PURPOSE_CONTROLLER_2 = 0x31
GENERAL_PURPOSE_CONTROLLER_3 = 0x32
GENERAL_PURPOSE_CONTROLLER_4 = 0x33

# Switches

SUSTAIN_ONOFF = 0x40
PORTAMENTO_ONOFF = 0x41
SOSTENUTO_ONOFF = 0x42
SOFT_PEDAL_ONOFF = 0x43
LEGATO_ONOFF = 0x44
HOLD_2_ONOFF = 0x45

# Low resolution continuous controllers

SOUND_CONTROLLER_1 = 0x46                  # (TG: Sound Variation;   FX: Exciter On/Off)
SOUND_CONTROLLER_2 = 0x47                  # (TG: Harmonic Content;   FX: Compressor On/Off)
SOUND_CONTROLLER_3 = 0x48                  # (TG: Release Time;   FX: Distortion On/Off)
SOUND_CONTROLLER_4 = 0x49                  # (TG: Attack Time;   FX: EQ On/Off)
SOUND_CONTROLLER_5 = 0x4A                  # (TG: Brightness;   FX: Expander On/Off)75	SOUND_CONTROLLER_6   (TG: Undefined;   FX: Reverb OnOff)
SOUND_CONTROLLER_7 = 0x4C                  # (TG: Undefined;   FX: Delay OnOff)
SOUND_CONTROLLER_8 = 0x4D                  # (TG: Undefined;   FX: Pitch Transpose OnOff)
SOUND_CONTROLLER_9 = 0x4E                  # (TG: Undefined;   FX: Flange/Chorus OnOff)
SOUND_CONTROLLER_10 = 0x4F                 # (TG: Undefined;   FX: Special Effects OnOff)
GENERAL_PURPOSE_CONTROLLER_5 = 0x50
GENERAL_PURPOSE_CONTROLLER_6 = 0x51
GENERAL_PURPOSE_CONTROLLER_7 = 0x52
GENERAL_PURPOSE_CONTROLLER_8 = 0x53
PORTAMENTO_CONTROL = 0x54                  # (PTC)   (0vvvvvvv is the source Note number)   (Detail)
EFFECTS_1 = 0x5B                           # (Ext. Effects Depth)
EFFECTS_2 = 0x5C                           # (Tremelo Depth)
EFFECTS_3 = 0x5D                           # (Chorus Depth)
EFFECTS_4 = 0x5E                           # (Celeste Depth)
EFFECTS_5 = 0x5F                           # (Phaser Depth)
DATA_INCREMENT = 0x60                      # (0vvvvvvv is n/a; use 0)
DATA_DECREMENT = 0x61                      # (0vvvvvvv is n/a; use 0)
NON_REGISTERED_PARAMETER_NUMBER = 0x62     # (LSB)
NON_REGISTERED_PARAMETER_NUMBER = 0x63     # (MSB)
REGISTERED_PARAMETER_NUMBER = 0x64         # (LSB)
REGISTERED_PARAMETER_NUMBER = 0x65         # (MSB)

# Channel Mode messages - (Detail)

ALL_SOUND_OFF = 0x78
RESET_ALL_CONTROLLERS = 0x79
LOCAL_CONTROL_ONOFF = 0x7A
ALL_NOTES_OFF = 0x7B
OMNI_MODE_OFF = 0x7C          # (also causes ANO)
OMNI_MODE_ON = 0x7D           # (also causes ANO)
MONO_MODE_ON = 0x7E           # (Poly Off; also causes ANO)
POLY_MODE_ON = 0x7F           # (Mono Off; also causes ANO)



###################################################
## System Common Messages, for all channels

SYSTEM_EXCLUSIVE = 0xF0
# 11110000 0iiiiiii 0ddddddd ... 11110111

MTC = 0xF1 # MIDI Time Code Quarter Frame
# 11110001

SONG_POSITION_POINTER = 0xF2
# 11110010 0vvvvvvv 0wwwwwww (lo-position, hi-position)

SONG_SELECT = 0xF3
# 11110011 0sssssss (songnumber)

#UNDEFINED = 0xF4
## 11110100

#UNDEFINED = 0xF5
## 11110101

TUNING_REQUEST = 0xF6
# 11110110

END_OFF_EXCLUSIVE = 0xF7 # terminator
# 11110111 # End of system exclusive


###################################################
## Midifile meta-events

SEQUENCE_NUMBER = 0x00      # 00 02 ss ss (seq-number)
TEXT            = 0x01      # 01 len text...
COPYRIGHT       = 0x02      # 02 len text...
SEQUENCE_NAME   = 0x03      # 03 len text...
INSTRUMENT_NAME = 0x04      # 04 len text...
LYRIC           = 0x05      # 05 len text...
MARKER          = 0x06      # 06 len text...
CUEPOINT        = 0x07      # 07 len text...
PROGRAM_NAME    = 0x08      # 08 len text...
DEVICE_NAME     = 0x09      # 09 len text...

MIDI_CH_PREFIX  = 0x20      # MIDI channel prefix assignment (unofficial)

MIDI_PORT       = 0x21      # 21 01 port, legacy stuff but still used
END_OF_TRACK    = 0x2F      # 2f 00
TEMPO           = 0x51      # 51 03 tt tt tt (tempo in us/quarternote)
SMTP_OFFSET     = 0x54      # 54 05 hh mm ss ff xx
TIME_SIGNATURE  = 0x58      # 58 04 nn dd cc bb
KEY_SIGNATURE   = 0x59      # ??? len text...
SPECIFIC        = 0x7F      # Sequencer specific event

FILE_HEADER     = 'MThd'
TRACK_HEADER    = 'MTrk'

###################################################
## System Realtime messages
## I don't supose these are to be found in midi files?!

TIMING_CLOCK   = 0xF8
# undefined    = 0xF9
SONG_START     = 0xFA
SONG_CONTINUE  = 0xFB
SONG_STOP      = 0xFC
# undefined    = 0xFD
ACTIVE_SENSING = 0xFE
SYSTEM_RESET   = 0xFF


###################################################
## META EVENT, it is used only in midi files.
## In transmitted data it means system reset!!!

META_EVENT     = 0xFF
# 11111111


###################################################
## Helper functions

def is_status(byte):
    return (byte & 0x80) == 0x80 # 1000 0000



########NEW FILE########
__FILENAME__ = DataTypeConverters
# -*- coding: ISO-8859-1 -*-

from struct import pack, unpack

"""
This module contains functions for reading and writing the special data types
that a midi file contains.
"""

"""
nibbles are four bits. A byte consists of two nibles.
hiBits==0xF0, loBits==0x0F Especially used for setting
channel and event in 1. byte of musical midi events
"""



def getNibbles(byte):
    """
    Returns hi and lo bits in a byte as a tuple
    >>> getNibbles(142)
    (8, 14)
    
    Asserts byte value in byte range
    >>> getNibbles(256)
    Traceback (most recent call last):
        ...
    ValueError: Byte value out of range 0-255: 256
    """
    if not 0 <= byte <= 255:
        raise ValueError('Byte value out of range 0-255: %s' % byte)
    return (byte >> 4 & 0xF, byte & 0xF)


def setNibbles(hiNibble, loNibble):
    """
    Returns byte with value set according to hi and lo bits
    Asserts hiNibble and loNibble in range(16)
    >>> setNibbles(8, 14)
    142
    
    >>> setNibbles(8, 16)
    Traceback (most recent call last):
        ...
    ValueError: Nible value out of range 0-15: (8, 16)
    """
    if not (0 <= hiNibble <= 15) or not (0 <= loNibble <= 15):
        raise ValueError('Nible value out of range 0-15: (%s, %s)' % (hiNibble, loNibble))
    return (hiNibble << 4) + loNibble



def readBew(value):
    """
    Reads string as big endian word, (asserts len(value) in [1,2,4])
    >>> readBew('a���')
    1642193635L
    >>> readBew('a�')
    25057
    """
    return unpack('>%s' % {1:'B', 2:'H', 4:'L'}[len(value)], value)[0]


def writeBew(value, length):
    """
    Write int as big endian formatted string, (asserts length in [1,2,4])
    Difficult to print the result in doctest, so I do a simple roundabout test.
    >>> readBew(writeBew(25057, 2))
    25057
    >>> readBew(writeBew(1642193635L, 4))
    1642193635L
    """
    return pack('>%s' % {1:'B', 2:'H', 4:'L'}[length], value)



"""
Variable Length Data (varlen) is a data format sprayed liberally throughout
a midi file. It can be anywhere from 1 to 4 bytes long.
If the 8'th bit is set in a byte another byte follows. The value is stored
in the lowest 7 bits of each byte. So max value is 4x7 bits = 28 bits.
"""


def readVar(value):
    """
    Converts varlength format to integer. Just pass it 0 or more chars that
    might be a varlen and it will only use the relevant chars.
    use varLen(readVar(value)) to see how many bytes the integer value takes.
    asserts len(value) >= 0
    >>> readVar('�@')
    64
    >>> readVar('���a')
    205042145
    """
    sum = 0
    for byte in unpack('%sB' % len(value), value):
        sum = (sum << 7) + (byte & 0x7F)
        if not 0x80 & byte: break # stop after last byte
    return sum



def varLen(value):
    """
    Returns the the number of bytes an integer will be when
    converted to varlength
    """
    if value <= 127:
        return 1
    elif value <= 16383:
        return 2
    elif value <= 2097151:
        return 3
    else:
        return 4


def writeVar(value):
    "Converts an integer to varlength format"
    sevens = to_n_bits(value, varLen(value))
    for i in range(len(sevens)-1):
        sevens[i] = sevens[i] | 0x80
    return fromBytes(sevens)


def to_n_bits(value, length=1, nbits=7):
    "returns the integer value as a sequence of nbits bytes"
    bytes = [(value >> (i*nbits)) & 0x7F for i in range(length)]
    bytes.reverse()
    return bytes


def toBytes(value):
    "Turns a string into a list of byte values"
    return unpack('%sB' % len(value), value)


def fromBytes(value):
    "Turns a list of bytes into a string"
    if not value:
        return ''
    return pack('%sB' % len(value), *value)



if __name__ == '__main__':

#    print to7bits(0, 3)
#    print to7bits(127, 3)
#    print to7bits(255, 3)
#    print to7bits(65536, 3)

    # simple test cases
    
#    print 'getHiLoHex', getNibbles(16)
#    print 'setHiLoHex', setNibbles(1,0)
#    
#    print 'readBew', readBew('a���')
#    print 'writeBew', writeBew(1642193635, 4)
#
#    print 'varLen', varLen(1)
#
    print 'readVar', readVar('�@')
    print 'writeVar', writeVar(8192)
    
    print 'readVar', readVar('���a')
    print 'writeVar', writeVar(205058401)
#    
#    vartest = '\x82\xF7\x80\x00'
#    print 'toBytes', toBytes(vartest)
#    print 'fromBytes', fromBytes([48, 49, 50,])
    
    
#    instr = '\xFF\xFF\xFF\x00'
#    print 'readVar', readVar(instr)
#    inst2 = 268435455
#    print inst2
#    print writeVar(inst2)
#    print writeVar(readVar(instr))

    s1 = 0x00000000
    print '%08X -' % s1, '00',  writeVar(s1)
    s2 = 0x00000040
    print '%08X -' % s2, '40',  writeVar(s2)
    s3 = 0x0000007F
    print '%08X -' % s3, '7F',  writeVar(s3)
    s4 = 0x00000080
    print '%08X -' % s4, '81 00',  writeVar(s4)
    s5 = 0x00002000
    print '%08X -' % s5, 'C0 00',  writeVar(s5)
    s6 = 0x00003FFF
    print '%08X -' % s6, 'FF 7F',  writeVar(s6)
    s7 = 0x00004000
    print '%08X -' % s7, '81 80 00',  writeVar(s7)
    s8 = 0x00100000
    print '%08X -' % s8, 'C0 80 00',  writeVar(s8)
    s9 = 0x001FFFFF
    print '%08X -' % s9, 'FF FF 7F',  writeVar(s9)
    s10 = 0x00200000
    print '%08X -' % s10, '81 80 80 00', writeVar(s10)
    s11 = 0x08000000
    print '%08X -' % s11, 'C0 80 80 00', writeVar(s11)
    s12 = 0x0FFFFFFF
    print '%08X -' % s12, 'FF FF FF 7F', writeVar(s12)
              
              
              
             
             
             
           
           
           
          
          
          
########NEW FILE########
__FILENAME__ = EventDispatcher
# -*- coding: ISO-8859-1 -*-

# std library
from struct import unpack

# custom
from DataTypeConverters import readBew, readVar, varLen, toBytes

# uhh I don't really like this, but there are so many constants to 
# import otherwise
from constants import *


class EventDispatcher:


    def __init__(self, outstream):
        
        """
        
        The event dispatcher generates events on the outstream.
        
        """
        
        # internal values, don't mess with 'em directly
        self.outstream = outstream
        
        # public flags

        # A note_on with a velocity of 0x00 is actually the same as a 
        # note_off with a velocity of 0x40. When 
        # "convert_zero_velocity" is set, the zero velocity note_on's 
        # automatically gets converted into note_off's. This is a less 
        # suprising behaviour for those that are not into the intimate 
        # details of the midi spec.
        self.convert_zero_velocity = 1
        
        # If dispatch_continuos_controllers is true, continuos 
        # controllers gets dispatched to their defined handlers. Else 
        # they just trigger the "continuous_controller" event handler.
        self.dispatch_continuos_controllers = 1 # NOT IMPLEMENTED YET
        
        # If dispatch_meta_events is true, meta events get's dispatched 
        # to their defined events. Else they all they trigger the 
        # "meta_event" handler.
        self.dispatch_meta_events = 1



    def header(self, format, nTracks, division):
        "Triggers the header event"
        self.outstream.header(format, nTracks, division)


    def start_of_track(self, current_track):
        "Triggers the start of track event"
        
        # I do this twice so that users can overwrite the 
        # start_of_track event handler without worrying whether the 
        # track number is updated correctly.
        self.outstream.set_current_track(current_track)
        self.outstream.start_of_track(current_track)
        
    
    def sysex_event(self, data):
        "Dispatcher for sysex events"
        self.outstream.sysex_event(data)
    
    
    def eof(self):
        "End of file!"
        self.outstream.eof()


    def update_time(self, new_time=0, relative=1):
        "Updates relative/absolute time."
        self.outstream.update_time(new_time, relative)
        
        
    def reset_time(self):
        "Updates relative/absolute time."
        self.outstream.reset_time()
        
        
    # Event dispatchers for similar types of events
    
    
    def channel_messages(self, hi_nible, channel, data):
    
        "Dispatches channel messages"
        
        stream = self.outstream
        data = toBytes(data)
        
        if (NOTE_ON & 0xF0) == hi_nible:
            note, velocity = data
            # note_on with velocity 0x00 are same as note 
            # off with velocity 0x40 according to spec!
            if velocity==0 and self.convert_zero_velocity:
                stream.note_off(channel, note, 0x40)
            else:
                stream.note_on(channel, note, velocity)
        
        elif (NOTE_OFF & 0xF0) == hi_nible:
            note, velocity = data
            stream.note_off(channel, note, velocity)
        
        elif (AFTERTOUCH & 0xF0) == hi_nible:
            note, velocity = data
            stream.aftertouch(channel, note, velocity)
        
        elif (CONTINUOUS_CONTROLLER & 0xF0) == hi_nible:
            controller, value = data
            # A lot of the cc's are defined, so we trigger those directly
            if self.dispatch_continuos_controllers:
                self.continuous_controllers(channel, controller, value)
            else:
                stream.continuous_controller(channel, controller, value)
            
        elif (PATCH_CHANGE & 0xF0) == hi_nible:
            program = data[0]
            stream.patch_change(channel, program)
            
        elif (CHANNEL_PRESSURE & 0xF0) == hi_nible:
            pressure = data[0]
            stream.channel_pressure(channel, pressure)
            
        elif (PITCH_BEND & 0xF0) == hi_nible:
            hibyte, lobyte = data
            value = (hibyte<<7) + lobyte
            stream.pitch_bend(channel, value)

        else:

            raise ValueError, 'Illegal channel message!'



    def continuous_controllers(self, channel, controller, value):
    
        "Dispatches channel messages"

        stream = self.outstream
        
        # I am not really shure if I ought to dispatch continuous controllers
        # There's so many of them that it can clutter up the OutStream 
        # classes.
        
        # So I just trigger the default event handler
        stream.continuous_controller(channel, controller, value)



    def system_commons(self, common_type, common_data):
    
        "Dispatches system common messages"
        
        stream = self.outstream
        
        # MTC Midi time code Quarter value
        if common_type == MTC:
            data = readBew(common_data)
            msg_type = (data & 0x07) >> 4
            values = (data & 0x0F)
            stream.midi_time_code(msg_type, values)
        
        elif common_type == SONG_POSITION_POINTER:
            hibyte, lobyte = toBytes(common_data)
            value = (hibyte<<7) + lobyte
            stream.song_position_pointer(value)

        elif common_type == SONG_SELECT:
            data = readBew(common_data)
            stream.song_select(data)

        elif common_type == TUNING_REQUEST:
            # no data then
            stream.tuning_request(time=None)



    def meta_event(self, meta_type, data):
        
        "Dispatches meta events"
        
        stream = self.outstream
        
        # SEQUENCE_NUMBER = 0x00 (00 02 ss ss (seq-number))
        if meta_type == SEQUENCE_NUMBER:
            number = readBew(data)
            stream.sequence_number(number)
        
        # TEXT = 0x01 (01 len text...)
        elif meta_type == TEXT:
            stream.text(data)
        
        # COPYRIGHT = 0x02 (02 len text...)
        elif meta_type == COPYRIGHT:
            stream.copyright(data)
        
        # SEQUENCE_NAME = 0x03 (03 len text...)
        elif meta_type == SEQUENCE_NAME:
            stream.sequence_name(data)
        
        # INSTRUMENT_NAME = 0x04 (04 len text...)
        elif meta_type == INSTRUMENT_NAME:
            stream.instrument_name(data)
        
        # LYRIC = 0x05 (05 len text...)
        elif meta_type == LYRIC:
            stream.lyric(data)
        
        # MARKER = 0x06 (06 len text...)
        elif meta_type == MARKER:
            stream.marker(data)
        
        # CUEPOINT = 0x07 (07 len text...)
        elif meta_type == CUEPOINT:
            stream.cuepoint(data)
        
        # PROGRAM_NAME = 0x08 (05 len text...)
        elif meta_type == PROGRAM_NAME:
            stream.program_name(data)
        
        # DEVICE_NAME = 0x09 (09 len text...)
        elif meta_type == DEVICE_NAME:
            stream.device_name(data)
        
        # MIDI_CH_PREFIX = 0x20 (20 01 channel)
        elif meta_type == MIDI_CH_PREFIX:
            channel = readBew(data)
            stream.midi_ch_prefix(channel)
        
        # MIDI_PORT  = 0x21 (21 01 port (legacy stuff))
        elif meta_type == MIDI_PORT:
            port = readBew(data)
            stream.midi_port(port)
        
        # END_OFF_TRACK = 0x2F (2F 00)
        elif meta_type == END_OF_TRACK:
            stream.end_of_track()
        
        # TEMPO = 0x51 (51 03 tt tt tt (tempo in us/quarternote))
        elif meta_type == TEMPO:
            b1, b2, b3 = toBytes(data)
            # uses 3 bytes to represent time between quarter 
            # notes in microseconds
            stream.tempo((b1<<16) + (b2<<8) + b3)
        
        # SMTP_OFFSET = 0x54 (54 05 hh mm ss ff xx)
        elif meta_type == SMTP_OFFSET:
            hour, minute, second, frame, framePart = toBytes(data)
            stream.smtp_offset(
                    hour, minute, second, frame, framePart)
        
        # TIME_SIGNATURE = 0x58 (58 04 nn dd cc bb)
        elif meta_type == TIME_SIGNATURE:
            nn, dd, cc, bb = toBytes(data)
            stream.time_signature(nn, dd, cc, bb)
        
        # KEY_SIGNATURE = 0x59 (59 02 sf mi)
        elif meta_type == KEY_SIGNATURE:
            sf, mi = toBytes(data)
            stream.key_signature(sf, mi)
        
        # SPECIFIC = 0x7F (Sequencer specific event)
        elif meta_type == SPECIFIC:
            meta_data = toBytes(data)
            stream.sequencer_specific(meta_data)
        
        # Handles any undefined meta events
        else: # undefined meta type
            meta_data = toBytes(data)
            stream.meta_event(meta_type, meta_data)





if __name__ == '__main__':


    from MidiToText import MidiToText
    
    outstream = MidiToText()
    dispatcher = EventDispatcher(outstream)
    dispatcher.channel_messages(NOTE_ON, 0x00, '\x40\x40')
########NEW FILE########
__FILENAME__ = example_mimimal_type0
from MidiOutFile import MidiOutFile

"""
This is an example of the smallest possible type 0 midi file, where 
all the midi events are in the same track.
"""

out_file = 'midiout/minimal_type0.mid'
midi = MidiOutFile(out_file)

# non optional midi framework
midi.header()
midi.start_of_track() 


# musical events

midi.update_time(0)
midi.note_on(channel=0, note=0x40)

midi.update_time(192)
midi.note_off(channel=0, note=0x40)


# non optional midi framework
midi.update_time(0)
midi.end_of_track()

midi.eof()

########NEW FILE########
__FILENAME__ = example_print_channel_0
from MidiOutStream import MidiOutStream
from MidiInFile import MidiInFile

"""
This prints all note on events on midi channel 0
"""


class Transposer(MidiOutStream):
    
    "Transposes all notes by 1 octave"
    
    def note_on(self, channel=0, note=0x40, velocity=0x40):
        if channel == 0:
            print channel, note, velocity, self.rel_time()


event_handler = Transposer()

in_file = 'midiout/minimal_type0.mid'
midi_in = MidiInFile(event_handler, in_file)
midi_in.read()


########NEW FILE########
__FILENAME__ = example_print_events
from MidiToText import MidiToText

"""
This is an example that uses the MidiToText eventhandler. When an 
event is triggered on it, it prints the event to the console.
"""

midi = MidiToText()

# non optional midi framework
midi.header()
midi.start_of_track() 


# musical events

midi.update_time(0)
midi.note_on(channel=0, note=0x40)

midi.update_time(192)
midi.note_off(channel=0, note=0x40)


# non optional midi framework
midi.update_time(0)
midi.end_of_track() # not optional!

midi.eof()

########NEW FILE########
__FILENAME__ = example_print_file
"""
This is an example that uses the MidiToText eventhandler. When an 
event is triggered on it, it prints the event to the console.

It gets the events from the MidiInFile.

So it prints all the events from the infile to the console. great for 
debugging :-s
"""


# get data
test_file = 'test/midifiles/minimal-cubase-type0.mid'

# do parsing
from MidiInFile import MidiInFile
from MidiToText import MidiToText # the event handler
midiIn = MidiInFile(MidiToText(), test_file)
midiIn.read()

########NEW FILE########
__FILENAME__ = example_transpose_octave
from MidiOutFile import MidiOutFile
from MidiInFile import MidiInFile

"""
This is an example of the smallest possible type 0 midi file, where 
all the midi events are in the same track.
"""


class Transposer(MidiOutFile):
    
    "Transposes all notes by 1 octave"
    
    def _transp(self, ch, note):
        if ch != 9: # not the drums!
            note += 12
            if note > 127:
                note = 127
        return note


    def note_on(self, channel=0, note=0x40, velocity=0x40):
        note = self._transp(channel, note)
        MidiOutFile.note_on(self, channel, note, velocity)
        
        
    def note_off(self, channel=0, note=0x40, velocity=0x40):
        note = self._transp(channel, note)
        MidiOutFile.note_off(self, channel, note, velocity)


out_file = 'midiout/transposed.mid'
midi_out = Transposer(out_file)

#in_file = 'midiout/minimal_type0.mid'
#in_file = 'test/midifiles/Lola.mid'
in_file = 'test/midifiles/tennessee_waltz.mid'
midi_in = MidiInFile(midi_out, in_file)
midi_in.read()


########NEW FILE########
__FILENAME__ = EventDispatcherBase
class EventDispatcherBase:


    def __init__(self, outstream):
        """
        The event dispatcher generates events on the outstream. This 
        is the base implementation. It is more like an interface for 
        how the EventDispatcher. It has the methods that are used by 
        the Midi Parser.
        """
        # internal values, don't mess with 'em directly
        self.outstream = outstream


    def eof(self):
        "End of file!"
        self.outstream.eof()


    def update_time(self, new_time=0, relative=1):
        "Updates relative/absolute time."
        self.outstream.update_time(new_time, relative)

    # 'official' midi events

    def header(self, format, nTracks, division):
        "Triggers the header event"
        self.outstream.header(format, nTracks, division)


    def start_of_track(self, current_track):
        "Triggers the start of track event"
        
        # I do this twice so that users can overwrite the 
        # start_of_track event handler without worrying whether the 
        # track number is updated correctly.
        self.outstream.set_current_track(current_track)
        self.outstream.start_of_track(current_track)

    # Event dispatchers for midi events

    def channel_messages(self, hi_nible, channel, data):
        "Dispatches channel messages"
        self.outstream.channel_message(hi_nible, channel, data)


    def continuous_controllers(self, channel, controller, value):
        "Dispatches channel messages"
        self.outstream.continuous_controller(channel, controller, value)
    
    
    def system_commons(self, common_type, common_data):
        "Dispatches system common messages"
        self.outstream.system_common(common_type, common_data)


    def meta_event(self, meta_type, data):
        "Dispatches meta events"
        self.outstream.meta_event(meta_type, data)


    def sysex_events(self, data):
        "Dispatcher for sysex events"
        self.outstream.sysex_event(data)



if __name__ == '__main__':


    from MidiToText import MidiToText
    from constants import NOTE_ON
    
    outstream = MidiToText()
    dispatcher = EventDispatcherBase(outstream)
    dispatcher.channel_messages(NOTE_ON, 0x00, '\x40\x40')
########NEW FILE########
__FILENAME__ = MidiOutPassThrough
from MidiOutStream import MidiOutStream

class MidiOutPassThrough(MidiOutStream):


    """

    This class i mainly used for testing the event dispatcher. The 
    methods just returns the passed parameters as a tupple.

    """


    #####################
    ## Midi channel events


    def note_on(self, channel, note, velocity, time=None):
        return channel, note, velocity, time


    def note_off(self, channel, note, velocity, time=None):
        return channel, note, velocity, time


    def aftertouch(self, channel, note, velocity, time=None):
        return channel, note, velocity, time

        
    def continuous_controller(self, channel, controller, value, time=None):
        return channel, controller, value, time


    def patch_change(self, channel, patch, time=None):
        return channel, patch, time


    def channel_pressure(self, channel, pressure, time=None):
        return channel, pressure, time


    #####################
    ## defined continuous controller events
    
#    def cc_

    #####################
    ## Common events

    def system_exclusive(self, data, time=None):
        return data, time


    def song_position_pointer(self, hiPos, loPos, time=None):
        return hiPos, loPos, time


    def song_select(self, songNumber, time=None):
        return songNumber, time


    def tuning_request(self, time=None):
        return time



    #########################
    # header does not really belong here. But anyhoo!!!
    
    def header(self, format, nTracks, division):
        return format, nTracks, division


    def eof(self):
        return 'eof'


    #####################
    ## meta events

    def start_of_track(self, n_track=0):
        return n_track


    def end_of_track(self, n_track=0, time=None):
        return n_track, time


    def sequence_number(self, hiVal, loVal, time=None):
        return hiVal, loVal, time


    def text(self, text, time=None):
        return text, time


    def copyright(self, text, time=None):
        return text, time


    def sequence_name(self, text, time=None):
        return text, time


    def instrument_name(self, text, time=None):
        return text, time


    def lyric(self, text, time=None):
        return text, time


    def marker(self, text, time=None):
        return text, time


    def cuepoint(self, text, time=None):
        return text, time


    def midi_port(self, value, time=None):
        return value, time


    def tempo(self, value, time=None):
        return value, time

    def smtp_offset(self, hour, minute, second, frame, framePart, time=None):
        return hour, minute, second, frame, framePart, time


    def time_signature(self, nn, dd, cc, bb, time=None):
        return nn, dd, cc, bb, time


    def key_signature(self, sf, mi, time=None):
        return sf, mi, time


    def sequencer_specific(self, data, time=None):
        return data, time




    #####################
    ## realtime events

    def timing_clock(self, time=None):
        return time


    def song_start(self, time=None):
        return time


    def song_stop(self, time=None):
        return time


    def song_continue(self, time=None):
        return time


    def active_sensing(self, time=None):
        return time


    def system_reset(self, time=None):
        return time





if __name__ == '__main__':

    midiOut = MidiOutStream()
    midiOut.note_on(0, 63, 127, 0)
    midiOut.note_off(0, 63, 127, 384)

    
########NEW FILE########
__FILENAME__ = MidiOutStreamBase
class MidiOutStreamBase:


    """

    MidiOutStreamBase is Basically an eventhandler. It is the most central
    class in the Midi library. You use it both for writing events to
    an output stream, and as an event handler for an input stream.

    This makes it extremely easy to take input from one stream and
    send it to another. Ie. if you want to read a Midi file, do some
    processing, and send it to a midiport.

    All time values are in absolute values from the opening of a
    stream. To calculate time values, please use the MidiTime and
    MidiDeltaTime classes.

    """

    def __init__(self):
        
        # the time is rather global, so it needs to be stored 
        # here. Otherwise there would be no really simple way to 
        # calculate it. The alternative would be to have each event 
        # handler do it. That sucks even worse!
        self._absolute_time = 0
        self._relative_time = 0
        self._current_track = 0

    # time handling event handlers. They should overwritten with care

    def update_time(self, new_time=0, relative=1):
        """
        Updates the time, if relative is true, new_time is relative, 
        else it's absolute.
        """
        if relative:
            self._relative_time = new_time
            self._absolute_time += new_time
        else:
            self._absolute_time = new_time
            self._relative_time = new_time - self._absolute_time

    def rel_time(self):
        "Returns the relative time"
        return self._relative_time

    def abs_time(self):
        "Returns the absolute time"
        return self._absolute_time

    # track handling event handlers
    
    def set_current_track(self, new_track):
        "Sets the current track number"
        self._current_track = new_track
    
    def get_current_track(self):
        "Returns the current track number"
        return self._current_track
    
    
    #####################
    ## Midi events


    def channel_message(self, message_type, channel, data):
        """The default event handler for channel messages"""
        pass


    #####################
    ## Common events

    def system_exclusive(self, data):

        """The default event handler for system_exclusive messages"""
        pass


    def system_common(self, common_type, common_data):

        """The default event handler for system common messages"""
        pass


    #########################
    # header does not really belong here. But anyhoo!!!
    
    def header(self, format, nTracks, division):

        """
        format: type of midi file in [1,2]
        nTracks: number of tracks
        division: timing division
        """
        pass


    def start_of_track(self, n_track=0):

        """
        n_track: number of track
        """
        pass


    def eof(self):

        """
        End of file. No more events to be processed.
        """
        pass


    #####################
    ## meta events


    def meta_event(self, meta_type, data, time):
        
        """The default event handler for meta_events"""
        pass




if __name__ == '__main__':

    midiOut = MidiOutStreamBase()
    midiOut.update_time(0,0)
    midiOut.note_on(0, 63, 127)
    midiOut.note_off(0, 63, 127)

    
########NEW FILE########
__FILENAME__ = MidiFileParser
# -*- coding: ISO-8859-1 -*-

# std library
from struct import unpack

# uhh I don't really like this, but there are so many constants to 
# import otherwise
from constants import *

from EventDispatcher import EventDispatcher

class MidiFileParser:

    """
    
    The MidiFileParser is the lowest level parser that see the data as 
    midi data. It generates events that gets triggered on the outstream.
    
    """

    def __init__(self, raw_in, outstream):

        """
        raw_data is the raw content of a midi file as a string.
        """

        # internal values, don't mess with 'em directly
        self.raw_in = raw_in
        self.dispatch = EventDispatcher(outstream)

        # Used to keep track of stuff
        self._running_status = None




    def parseMThdChunk(self):
        
        "Parses the header chunk"
        
        raw_in = self.raw_in

        header_chunk_type = raw_in.nextSlice(4)
        header_chunk_zise = raw_in.readBew(4)

        # check if it is a proper midi file
        if header_chunk_type != 'MThd':
            raise TypeError, "It is not a valid midi file!"

        # Header values are at fixed locations, so no reason to be clever
        self.format = raw_in.readBew(2)
        self.nTracks = raw_in.readBew(2)
        self.division = raw_in.readBew(2)
        
        # Theoretically a header larger than 6 bytes can exist
        # but no one has seen one in the wild
        # But correctly ignore unknown data if it is though
        if header_chunk_zise > 6:
            raw_in.moveCursor(header_chunk_zise-6)

        # call the header event handler on the stream
        self.dispatch.header(self.format, self.nTracks, self.division)



    def parseMTrkChunk(self):
        
        "Parses a track chunk. This is the most important part of the parser."
        
        # set time to 0 at start of a track
        self.dispatch.reset_time()
        
        dispatch = self.dispatch
        raw_in = self.raw_in
        
        # Trigger event at the start of a track
        dispatch.start_of_track(self._current_track)
        # position cursor after track header
        raw_in.moveCursor(4)
        # unsigned long is 4 bytes
        tracklength = raw_in.readBew(4)
        track_endposition = raw_in.getCursor() + tracklength # absolute position!

        while raw_in.getCursor() < track_endposition:
        
            # find relative time of the event
            time = raw_in.readVarLen()
            dispatch.update_time(time)
            
            # be aware of running status!!!!
            peak_ahead = raw_in.readBew(move_cursor=0)
            if (peak_ahead & 0x80): 
                # the status byte has the high bit set, so it
                # was not running data but proper status byte
                status = self._running_status = raw_in.readBew()
            else:
                # use that darn running status
                status = self._running_status
                # could it be illegal data ?? Do we need to test for that?
                # I need more example midi files to be shure.
                
                # Also, while I am almost certain that no realtime 
                # messages will pop up in a midi file, I might need to 
                # change my mind later.

            # we need to look at nibbles here
            hi_nible, lo_nible = status & 0xF0, status & 0x0F
            
            # match up with events

            # Is it a meta_event ??
            # these only exists in midi files, not in transmitted midi data
            # In transmitted data META_EVENT (0xFF) is a system reset
            if status == META_EVENT:
                meta_type = raw_in.readBew()
                meta_length = raw_in.readVarLen()
                meta_data = raw_in.nextSlice(meta_length)
                dispatch.meta_event(meta_type, meta_data)


            # Is it a sysex_event ??
            elif status == SYSTEM_EXCLUSIVE:
                # ignore sysex events
                sysex_length = raw_in.readVarLen()
                # don't read sysex terminator
                sysex_data = raw_in.nextSlice(sysex_length-1)
                # only read last data byte if it is a sysex terminator
                # It should allways be there, but better safe than sorry
                if raw_in.readBew(move_cursor=0) == END_OFF_EXCLUSIVE:
                    eo_sysex = raw_in.readBew()
                dispatch.sysex_event(sysex_data)
                # the sysex code has not been properly tested, and might be fishy!


            # is it a system common event?
            elif hi_nible == 0xF0: # Hi bits are set then
                data_sizes = {
                    MTC:1,
                    SONG_POSITION_POINTER:2,
                    SONG_SELECT:1,
                }
                data_size = data_sizes.get(hi_nible, 0)
                common_data = raw_in.nextSlice(data_size)
                common_type = lo_nible
                dispatch.system_common(common_type, common_data)
            

            # Oh! Then it must be a midi event (channel voice message)
            else:
                data_sizes = {
                    PATCH_CHANGE:1,
                    CHANNEL_PRESSURE:1,
                    NOTE_OFF:2,
                    NOTE_ON:2,
                    AFTERTOUCH:2,
                    CONTINUOUS_CONTROLLER:2,
                    PITCH_BEND:2,
                }
                data_size = data_sizes.get(hi_nible, 0)
                channel_data = raw_in.nextSlice(data_size)
                event_type, channel = hi_nible, lo_nible
                dispatch.channel_messages(event_type, channel, channel_data)


    def parseMTrkChunks(self):
        "Parses all track chunks."
        for t in range(self.nTracks):
            self._current_track = t
            self.parseMTrkChunk() # this is where it's at!
        self.dispatch.eof()



if __name__ == '__main__':

    # get data
    test_file = 'test/midifiles/minimal.mid'
    test_file = 'test/midifiles/cubase-minimal.mid'
    test_file = 'test/midifiles/Lola.mid'
#    f = open(test_file, 'rb')
#    raw_data = f.read()
#    f.close()
#    
#    
#    # do parsing
    from MidiToText import MidiToText
    from RawInstreamFile import RawInstreamFile

    midi_in = MidiFileParser(RawInstreamFile(test_file), MidiToText())
    midi_in.parseMThdChunk()
    midi_in.parseMTrkChunks()
    
########NEW FILE########
__FILENAME__ = MidiInFile
# -*- coding: ISO-8859-1 -*-

from RawInstreamFile import RawInstreamFile
from MidiFileParser import MidiFileParser


class MidiInFile:

    """
    
    Parses a midi file, and triggers the midi events on the outStream 
    object.
    
    Get example data from a minimal midi file, generated with cubase.
    >>> test_file = 'C:/Documents and Settings/maxm/Desktop/temp/midi/src/midi/tests/midifiles/minimal-cubase-type0.mid'
    
    Do parsing, and generate events with MidiToText,
    so we can see what a minimal midi file contains
    >>> from MidiToText import MidiToText
    >>> midi_in = MidiInFile(MidiToText(), test_file)
    >>> midi_in.read()
    format: 0, nTracks: 1, division: 480
    ----------------------------------
    <BLANKLINE>
    Start - track #0
    sequence_name: Type 0
    tempo: 500000
    time_signature: 4 2 24 8
    note_on  - ch:00,  note:48,  vel:64 time:0
    note_off - ch:00,  note:48,  vel:40 time:480
    End of track
    <BLANKLINE>
    End of file
    
    
    """

    def __init__(self, outStream, infile):
        # these could also have been mixins, would that be better? Nah!
        self.raw_in = RawInstreamFile(infile)
        self.parser = MidiFileParser(self.raw_in, outStream)


    def read(self):
        "Start parsing the file"
        p = self.parser
        p.parseMThdChunk()
        p.parseMTrkChunks()


    def setData(self, data=''):
        "Sets the data from a plain string"
        self.raw_in.setData(data)
    
    

########NEW FILE########
__FILENAME__ = MidiInStream
# -*- coding: ISO-8859-1 -*-

from MidiOutStream import MidiOutStream

class MidiInStream:

    """
    Takes midi events from the midi input and calls the apropriate
    method in the eventhandler object
    """

    def __init__(self, midiOutStream, device):

        """

        Sets a default output stream, and sets the device from where
        the input comes

        """

        if midiOutStream is None:
            self.midiOutStream = MidiOutStream()
        else:
            self.midiOutStream = midiOutStream


    def close(self):

        """
        Stop the MidiInstream
        """


    def read(self, time=0):

        """

        Start the MidiInstream.

        "time" sets timer to specific start value.

        """


    def resetTimer(self, time=0):
        """

        Resets the timer, probably a good idea if there is some kind
        of looping going on

        """


########NEW FILE########
__FILENAME__ = MidiOutFile
# -*- coding: ISO-8859-1 -*-

from MidiOutStream import MidiOutStream
from RawOutstreamFile import RawOutstreamFile

from constants import *
from DataTypeConverters import fromBytes, writeVar

class MidiOutFile(MidiOutStream):


    """
    MidiOutFile is an eventhandler that subclasses MidiOutStream.
    """


    def __init__(self, raw_out=''):

        self.raw_out = RawOutstreamFile(raw_out)
        MidiOutStream.__init__(self)
        
    
    def write(self):
        self.raw_out.write()


    def event_slice(self, slc):
        """
        Writes the slice of an event to the current track. Correctly 
        inserting a varlen timestamp too.
        """
        trk = self._current_track_buffer
        trk.writeVarLen(self.rel_time())
        trk.writeSlice(slc)
        
    
    #####################
    ## Midi events


    def note_on(self, channel=0, note=0x40, velocity=0x40):

        """
        channel: 0-15
        note, velocity: 0-127
        """
        slc = fromBytes([NOTE_ON + channel, note, velocity])
        self.event_slice(slc)


    def note_off(self, channel=0, note=0x40, velocity=0x40):

        """
        channel: 0-15
        note, velocity: 0-127
        """
        slc = fromBytes([NOTE_OFF + channel, note, velocity])
        self.event_slice(slc)


    def aftertouch(self, channel=0, note=0x40, velocity=0x40):

        """
        channel: 0-15
        note, velocity: 0-127
        """
        slc = fromBytes([AFTERTOUCH + channel, note, velocity])
        self.event_slice(slc)


    def continuous_controller(self, channel, controller, value):

        """
        channel: 0-15
        controller, value: 0-127
        """
        slc = fromBytes([CONTINUOUS_CONTROLLER + channel, controller, value])
        self.event_slice(slc)
        # These should probably be implemented
        # http://users.argonet.co.uk/users/lenny/midi/tech/spec.html#ctrlnums


    def patch_change(self, channel, patch):

        """
        channel: 0-15
        patch: 0-127
        """
        slc = fromBytes([PATCH_CHANGE + channel, patch])
        self.event_slice(slc)


    def channel_pressure(self, channel, pressure):

        """
        channel: 0-15
        pressure: 0-127
        """
        slc = fromBytes([CHANNEL_PRESSURE + channel, pressure])
        self.event_slice(slc)


    def pitch_bend(self, channel, value):

        """
        channel: 0-15
        value: 0-16383
        """
        msb = (value>>7) & 0xFF
        lsb = value & 0xFF
        slc = fromBytes([PITCH_BEND + channel, msb, lsb])
        self.event_slice(slc)




    #####################
    ## System Exclusive

#    def sysex_slice(sysex_type, data):
#        ""
#        sysex_len = writeVar(len(data)+1)
#        self.event_slice(SYSTEM_EXCLUSIVE + sysex_len + data + END_OFF_EXCLUSIVE)
#
    def system_exclusive(self, data):

        """
        data: list of values in range(128)
        """
        sysex_len = writeVar(len(data)+1)
        self.event_slice(chr(SYSTEM_EXCLUSIVE) + sysex_len + data + chr(END_OFF_EXCLUSIVE))


    #####################
    ## Common events

    def midi_time_code(self, msg_type, values):
        """
        msg_type: 0-7
        values: 0-15
        """
        value = (msg_type<<4) + values
        self.event_slice(fromBytes([MIDI_TIME_CODE, value]))


    def song_position_pointer(self, value):

        """
        value: 0-16383
        """
        lsb = (value & 0x7F)
        msb = (value >> 7) & 0x7F
        self.event_slice(fromBytes([SONG_POSITION_POINTER, lsb, msb]))


    def song_select(self, songNumber):

        """
        songNumber: 0-127
        """
        self.event_slice(fromBytes([SONG_SELECT, songNumber]))


    def tuning_request(self):

        """
        No values passed
        """
        self.event_slice(chr(TUNING_REQUEST))

            
    #########################
    # header does not really belong here. But anyhoo!!!
    
    def header(self, format=0, nTracks=1, division=96):

        """
        format: type of midi file in [0,1,2]
        nTracks: number of tracks. 1 track for type 0 file
        division: timing division ie. 96 ppq.
        
        """        
        raw = self.raw_out
        raw.writeSlice('MThd')
        bew = raw.writeBew
        bew(6, 4) # header size
        bew(format, 2)
        bew(nTracks, 2)
        bew(division, 2)


    def eof(self):

        """
        End of file. No more events to be processed.
        """
        # just write the file then.
        self.write()


    #####################
    ## meta events


    def meta_slice(self, meta_type, data_slice):
        "Writes a meta event"
        slc = fromBytes([META_EVENT, meta_type]) + \
                         writeVar(len(data_slice)) +  data_slice
        self.event_slice(slc)


    def meta_event(self, meta_type, data):
        """
        Handles any undefined meta events
        """
        self.meta_slice(meta_type, fromBytes(data))


    def start_of_track(self, n_track=0):
        """
        n_track: number of track
        """
        self._current_track_buffer = RawOutstreamFile()
        self.reset_time()
        self._current_track += 1


    def end_of_track(self):
        """
        Writes the track to the buffer.
        """
        raw = self.raw_out
        raw.writeSlice(TRACK_HEADER)
        track_data = self._current_track_buffer.getvalue()
        # wee need to know size of track data.
        eot_slice = writeVar(self.rel_time()) + fromBytes([META_EVENT, END_OF_TRACK, 0])
        raw.writeBew(len(track_data)+len(eot_slice), 4)
        # then write
        raw.writeSlice(track_data)
        raw.writeSlice(eot_slice)
        


    def sequence_number(self, value):

        """
        value: 0-65535
        """
        self.meta_slice(meta_type, writeBew(value, 2))


    def text(self, text):
        """
        Text event
        text: string
        """
        self.meta_slice(TEXT, text)


    def copyright(self, text):

        """
        Copyright notice
        text: string
        """
        self.meta_slice(COPYRIGHT, text)


    def sequence_name(self, text):
        """
        Sequence/track name
        text: string
        """
        self.meta_slice(SEQUENCE_NAME, text)


    def instrument_name(self, text):

        """
        text: string
        """
        self.meta_slice(INSTRUMENT_NAME, text)


    def lyric(self, text):

        """
        text: string
        """
        self.meta_slice(LYRIC, text)


    def marker(self, text):

        """
        text: string
        """
        self.meta_slice(MARKER, text)


    def cuepoint(self, text):

        """
        text: string
        """
        self.meta_slice(CUEPOINT, text)


    def midi_ch_prefix(self, channel):

        """
        channel: midi channel for subsequent data
        (deprecated in the spec)
        """
        self.meta_slice(MIDI_CH_PREFIX, chr(channel))


    def midi_port(self, value):

        """
        value: Midi port (deprecated in the spec)
        """
        self.meta_slice(MIDI_CH_PREFIX, chr(value))


    def tempo(self, value):

        """
        value: 0-2097151
        tempo in us/quarternote
        (to calculate value from bpm: int(60,000,000.00 / BPM))
        """
        hb, mb, lb = (value>>16 & 0xff), (value>>8 & 0xff), (value & 0xff)
        self.meta_slice(TEMPO, fromBytes([hb, mb, lb]))


    def smtp_offset(self, hour, minute, second, frame, framePart):

        """
        hour,
        minute,
        second: 3 bytes specifying the hour (0-23), minutes (0-59) and 
                seconds (0-59), respectively. The hour should be 
                encoded with the SMPTE format, just as it is in MIDI 
                Time Code.
        frame: A byte specifying the number of frames per second (one 
               of : 24, 25, 29, 30).
        framePart: A byte specifying the number of fractional frames, 
                   in 100ths of a frame (even in SMPTE-based tracks 
                   using a different frame subdivision, defined in the 
                   MThd chunk).
        """
        self.meta_slice(SMTP_OFFSET, fromBytes([hour, minute, second, frame, framePart]))



    def time_signature(self, nn, dd, cc, bb):

        """
        nn: Numerator of the signature as notated on sheet music
        dd: Denominator of the signature as notated on sheet music
            The denominator is a negative power of 2: 2 = quarter 
            note, 3 = eighth, etc.
        cc: The number of MIDI clocks in a metronome click
        bb: The number of notated 32nd notes in a MIDI quarter note 
            (24 MIDI clocks)        
        """
        self.meta_slice(TIME_SIGNATURE, fromBytes([nn, dd, cc, bb]))




    def key_signature(self, sf, mi):

        """
        sf: is a byte specifying the number of flats (-ve) or sharps 
            (+ve) that identifies the key signature (-7 = 7 flats, -1 
            = 1 flat, 0 = key of C, 1 = 1 sharp, etc).
        mi: is a byte specifying a major (0) or minor (1) key.
        """
        self.meta_slice(KEY_SIGNATURE, fromBytes([sf, mi]))



    def sequencer_specific(self, data):

        """
        data: The data as byte values
        """
        self.meta_slice(SEQUENCER_SPECIFIC, data)





#    #####################
#    ## realtime events

#    These are of no use in a midi file, so they are ignored!!!

#    def timing_clock(self):
#    def song_start(self):
#    def song_stop(self):
#    def song_continue(self):
#    def active_sensing(self):
#    def system_reset(self):



if __name__ == '__main__':

    out_file = 'test/midifiles/midiout.mid'
    midi = MidiOutFile(out_file)

#format: 0, nTracks: 1, division: 480
#----------------------------------
#
#Start - track #0
#sequence_name: Type 0
#tempo: 500000
#time_signature: 4 2 24 8
#note_on  - ch:00,  note:48,  vel:64 time:0
#note_off - ch:00,  note:48,  vel:40 time:480
#End of track
#
#End of file


    midi.header(0, 1, 480)
    
    midi.start_of_track()
    midi.sequence_name('Type 0')
    midi.tempo(750000)
    midi.time_signature(4, 2, 24, 8)
    ch = 0
    for i in range(127):
        midi.note_on(ch, i, 0x64)
        midi.update_time(96)
        midi.note_off(ch, i, 0x40)
        midi.update_time(0)
    
    midi.update_time(0)
    midi.end_of_track()
    
    midi.eof() # currently optional, should it do the write instead of write??


    midi.write()
########NEW FILE########
__FILENAME__ = MidiOutStream
# -*- coding: ISO-8859-1 -*-

class MidiOutStream:


    """

    MidiOutstream is Basically an eventhandler. It is the most central
    class in the Midi library. You use it both for writing events to
    an output stream, and as an event handler for an input stream.

    This makes it extremely easy to take input from one stream and
    send it to another. Ie. if you want to read a Midi file, do some
    processing, and send it to a midiport.

    All time values are in absolute values from the opening of a
    stream. To calculate time values, please use the MidiTime and
    MidiDeltaTime classes.

    """

    def __init__(self):
        
        # the time is rather global, so it needs to be stored 
        # here. Otherwise there would be no really simple way to 
        # calculate it. The alternative would be to have each event 
        # handler do it. That sucks even worse!
        self._absolute_time = 0
        self._relative_time = 0
        self._current_track = 0
        self._running_status = None

    # time handling event handlers. They should be overwritten with care

    def update_time(self, new_time=0, relative=1):
        """
        Updates the time, if relative is true, new_time is relative, 
        else it's absolute.
        """
        if relative:
            self._relative_time = new_time
            self._absolute_time += new_time
        else:
            self._relative_time = new_time - self._absolute_time
            self._absolute_time = new_time

    def reset_time(self):
        """
        reset time to 0
        """
        self._relative_time = 0
        self._absolute_time = 0
        
    def rel_time(self):
        "Returns the relative time"
        return self._relative_time

    def abs_time(self):
        "Returns the absolute time"
        return self._absolute_time

    # running status methods
    
    def reset_run_stat(self):
        "Invalidates the running status"
        self._running_status = None

    def set_run_stat(self, new_status):
        "Set the new running status"
        self._running_status = new_status

    def get_run_stat(self):
        "Set the new running status"
        return self._running_status

    # track handling event handlers
    
    def set_current_track(self, new_track):
        "Sets the current track number"
        self._current_track = new_track
    
    def get_current_track(self):
        "Returns the current track number"
        return self._current_track
    
    
    #####################
    ## Midi events


    def channel_message(self, message_type, channel, data):
        """The default event handler for channel messages"""
        pass


    def note_on(self, channel=0, note=0x40, velocity=0x40):

        """
        channel: 0-15
        note, velocity: 0-127
        """
        pass


    def note_off(self, channel=0, note=0x40, velocity=0x40):

        """
        channel: 0-15
        note, velocity: 0-127
        """
        pass


    def aftertouch(self, channel=0, note=0x40, velocity=0x40):

        """
        channel: 0-15
        note, velocity: 0-127
        """
        pass


    def continuous_controller(self, channel, controller, value):

        """
        channel: 0-15
        controller, value: 0-127
        """
        pass


    def patch_change(self, channel, patch):

        """
        channel: 0-15
        patch: 0-127
        """
        pass


    def channel_pressure(self, channel, pressure):

        """
        channel: 0-15
        pressure: 0-127
        """
        pass


    def pitch_bend(self, channel, value):

        """
        channel: 0-15
        value: 0-16383

        """
        pass




    #####################
    ## System Exclusive

    def system_exclusive(self, data):

        """
        data: list of values in range(128)
        """
        pass


    #####################
    ## Common events

    def song_position_pointer(self, value):

        """
        value: 0-16383
        """
        pass


    def song_select(self, songNumber):

        """
        songNumber: 0-127
        """
        pass


    def tuning_request(self):

        """
        No values passed
        """
        pass

            
    def midi_time_code(self, msg_type, values):
        """
        msg_type: 0-7
        values: 0-15
        """
        pass


    #########################
    # header does not really belong here. But anyhoo!!!
    
    def header(self, format=0, nTracks=1, division=96):

        """
        format: type of midi file in [1,2]
        nTracks: number of tracks
        division: timing division
        """
        pass


    def eof(self):

        """
        End of file. No more events to be processed.
        """
        pass


    #####################
    ## meta events


    def meta_event(self, meta_type, data):
        
        """
        Handles any undefined meta events
        """
        pass


    def start_of_track(self, n_track=0):

        """
        n_track: number of track
        """
        pass


    def end_of_track(self):

        """
        n_track: number of track
        """
        pass


    def sequence_number(self, value):

        """
        value: 0-16383
        """
        pass


    def text(self, text):

        """
        Text event
        text: string
        """
        pass


    def copyright(self, text):

        """
        Copyright notice
        text: string
        """
        pass


    def sequence_name(self, text):

        """
        Sequence/track name
        text: string
        """
        pass


    def instrument_name(self, text):

        """
        text: string
        """
        pass


    def lyric(self, text):

        """
        text: string
        """
        pass


    def marker(self, text):

        """
        text: string
        """
        pass


    def cuepoint(self, text):

        """
        text: string
        """
        pass


    def midi_ch_prefix(self, channel):

        """
        channel: midi channel for subsequent data (deprecated in the spec)
        """
        pass


    def midi_port(self, value):

        """
        value: Midi port (deprecated in the spec)
        """
        pass


    def tempo(self, value):

        """
        value: 0-2097151
        tempo in us/quarternote
        (to calculate value from bpm: int(60,000,000.00 / BPM))
        """
        pass


    def smtp_offset(self, hour, minute, second, frame, framePart):

        """
        hour,
        minute,
        second: 3 bytes specifying the hour (0-23), minutes (0-59) and 
                seconds (0-59), respectively. The hour should be 
                encoded with the SMPTE format, just as it is in MIDI 
                Time Code.
        frame: A byte specifying the number of frames per second (one 
               of : 24, 25, 29, 30).
        framePart: A byte specifying the number of fractional frames, 
                   in 100ths of a frame (even in SMPTE-based tracks 
                   using a different frame subdivision, defined in the 
                   MThd chunk).
        """
        pass



    def time_signature(self, nn, dd, cc, bb):

        """
        nn: Numerator of the signature as notated on sheet music
        dd: Denominator of the signature as notated on sheet music
            The denominator is a negative power of 2: 2 = quarter 
            note, 3 = eighth, etc.
        cc: The number of MIDI clocks in a metronome click
        bb: The number of notated 32nd notes in a MIDI quarter note 
            (24 MIDI clocks)        
        """
        pass



    def key_signature(self, sf, mi):

        """
        sf: is a byte specifying the number of flats (-ve) or sharps 
            (+ve) that identifies the key signature (-7 = 7 flats, -1 
            = 1 flat, 0 = key of C, 1 = 1 sharp, etc).
        mi: is a byte specifying a major (0) or minor (1) key.
        """
        pass



    def sequencer_specific(self, data):

        """
        data: The data as byte values
        """
        pass




    #####################
    ## realtime events

    def timing_clock(self):

        """
        No values passed
        """
        pass



    def song_start(self):

        """
        No values passed
        """
        pass



    def song_stop(self):

        """
        No values passed
        """
        pass



    def song_continue(self):

        """
        No values passed
        """
        pass



    def active_sensing(self):

        """
        No values passed
        """
        pass



    def system_reset(self):

        """
        No values passed
        """
        pass



if __name__ == '__main__':

    midiOut = MidiOutStream()
    midiOut.update_time(0,0)
    midiOut.note_on(0, 63, 127)
    midiOut.note_off(0, 63, 127)

    
########NEW FILE########
__FILENAME__ = MidiToText
# -*- coding: ISO-8859-1 -*-

from MidiOutStream import MidiOutStream
class MidiToText(MidiOutStream):


    """
    This class renders a midi file as text. It is mostly used for debugging
    """

    #############################
    # channel events
    
    
    def channel_message(self, message_type, channel, data):
        """The default event handler for channel messages"""
        print 'message_type:%X, channel:%X, data size:%X' % (message_type, channel, len(data))


    def note_on(self, channel=0, note=0x40, velocity=0x40):
        print 'note_on  - ch:%02X,  note:%02X,  vel:%02X time:%s' % (channel, note, velocity, self.rel_time())

    def note_off(self, channel=0, note=0x40, velocity=0x40):
        print 'note_off - ch:%02X,  note:%02X,  vel:%02X time:%s' % (channel, note, velocity, self.rel_time())

    def aftertouch(self, channel=0, note=0x40, velocity=0x40):
        print 'aftertouch', channel, note, velocity


    def continuous_controller(self, channel, controller, value):
        print 'controller - ch: %02X, cont: #%02X, value: %02X' % (channel, controller, value)


    def patch_change(self, channel, patch):
        print 'patch_change - ch:%02X, patch:%02X' % (channel, patch)


    def channel_pressure(self, channel, pressure):
        print 'channel_pressure', channel, pressure


    def pitch_bend(self, channel, value):
        print 'pitch_bend ch:%s, value:%s' % (channel, value)



    #####################
    ## Common events


    def system_exclusive(self, data):
        print 'system_exclusive - data size: %s' % len(date)


    def song_position_pointer(self, value):
        print 'song_position_pointer: %s' % value


    def song_select(self, songNumber):
        print 'song_select: %s' % songNumber


    def tuning_request(self):
        print 'tuning_request'


    def midi_time_code(self, msg_type, values):
        print 'midi_time_code - msg_type: %s, values: %s' % (msg_type, values)



    #########################
    # header does not really belong here. But anyhoo!!!

    def header(self, format=0, nTracks=1, division=96):
        print 'format: %s, nTracks: %s, division: %s' % (format, nTracks, division)
        print '----------------------------------'
        print ''

    def eof(self):
        print 'End of file'


    def start_of_track(self, n_track=0):
        print 'Start - track #%s' % n_track


    def end_of_track(self):
        print 'End of track'
        print ''



    ###############
    # sysex event

    def sysex_event(self, data):
        print 'sysex_event - datasize: %X' % len(data)


    #####################
    ## meta events

    def meta_event(self, meta_type, data):
        print 'undefined_meta_event:', meta_type, len(data)


    def sequence_number(self, value):
        print 'sequence_number', number


    def text(self, text):
        print 'text', text


    def copyright(self, text):
        print 'copyright', text


    def sequence_name(self, text):
        print 'sequence_name:', text


    def instrument_name(self, text):
        print 'instrument_name:', text


    def lyric(self, text):
        print 'lyric', text


    def marker(self, text):
        print 'marker', text


    def cuepoint(self, text):
        print 'cuepoint', text


    def midi_ch_prefix(self, channel):
        print 'midi_ch_prefix', channel


    def midi_port(self, value):
        print 'midi_port:', value


    def tempo(self, value):
        print 'tempo:', value


    def smtp_offset(self, hour, minute, second, frame, framePart):
        print 'smtp_offset', hour, minute, second, frame, framePart


    def time_signature(self, nn, dd, cc, bb):
        print 'time_signature:', nn, dd, cc, bb


    def key_signature(self, sf, mi):
        print 'key_signature', sf, mi


    def sequencer_specific(self, data):
        print 'sequencer_specific', len(data)



if __name__ == '__main__':

    # get data
    test_file = 'test/midifiles/minimal.mid'
    f = open(test_file, 'rb')
    
    # do parsing
    from MidiInFile import MidiInFile
    midiIn = MidiInFile(MidiToText(), f)
    midiIn.read()
    f.close()

########NEW FILE########
__FILENAME__ = RawInstreamFile
# -*- coding: ISO-8859-1 -*-

# standard library imports
from types import StringType
from struct import unpack

# custom import
from DataTypeConverters import readBew, readVar, varLen


class RawInstreamFile:
    
    """
    
    It parses and reads data from an input file. It takes care of big 
    endianess, and keeps track of the cursor position. The midi parser 
    only reads from this object. Never directly from the file.
    
    """
    
    def __init__(self, infile=''):
        """ 
        If 'file' is a string we assume it is a path and read from 
        that file.
        If it is a file descriptor we read from the file, but we don't 
        close it.
        Midi files are usually pretty small, so it should be safe to 
        copy them into memory.
        """
        if infile:
            if isinstance(infile, StringType):
                infile = open(infile, 'rb')
                self.data = infile.read()
                infile.close()
            else:
                # don't close the f
                self.data = infile.read()
        else:
            self.data = ''
        # start at beginning ;-)
        self.cursor = 0


    # setting up data manually
    
    def setData(self, data=''):
        "Sets the data from a string."
        self.data = data
    
    # cursor operations

    def setCursor(self, position=0):
        "Sets the absolute position if the cursor"
        self.cursor = position


    def getCursor(self):
        "Returns the value of the cursor"
        return self.cursor
        
        
    def moveCursor(self, relative_position=0):
        "Moves the cursor to a new relative position"
        self.cursor += relative_position

    # native data reading functions
        
    def nextSlice(self, length, move_cursor=1):
        "Reads the next text slice from the raw data, with length"
        c = self.cursor
        slc = self.data[c:c+length]
        if move_cursor:
            self.moveCursor(length)
        return slc
        
        
    def readBew(self, n_bytes=1, move_cursor=1):
        """
        Reads n bytes of date from the current cursor position.
        Moves cursor if move_cursor is true
        """
        return readBew(self.nextSlice(n_bytes, move_cursor))


    def readVarLen(self):
        """
        Reads a variable length value from the current cursor position.
        Moves cursor if move_cursor is true
        """
        MAX_VARLEN = 4 # Max value varlen can be
        var = readVar(self.nextSlice(MAX_VARLEN, 0))
        # only move cursor the actual bytes in varlen
        self.moveCursor(varLen(var))
        return var



if __name__ == '__main__':

    test_file = 'test/midifiles/minimal.mid'
    fis = RawInstreamFile(test_file)
    print fis.nextSlice(len(fis.data))

    test_file = 'test/midifiles/cubase-minimal.mid'
    cubase_minimal = open(test_file, 'rb')
    fis2 = RawInstreamFile(cubase_minimal)
    print fis2.nextSlice(len(fis2.data))
    cubase_minimal.close()

########NEW FILE########
__FILENAME__ = RawOutstreamFile
# -*- coding: ISO-8859-1 -*-

# standard library imports
import sys
from types import StringType
from struct import unpack
from cStringIO import StringIO

# custom import
from DataTypeConverters import writeBew, writeVar, fromBytes

class RawOutstreamFile:
    
    """
    
    Writes a midi file to disk.
    
    """

    def __init__(self, outfile=''):
        self.buffer = StringIO()
        self.outfile = outfile


    # native data reading functions


    def writeSlice(self, str_slice):
        "Writes the next text slice to the raw data"
        self.buffer.write(str_slice)
        
        
    def writeBew(self, value, length=1):
        "Writes a value to the file as big endian word"
        self.writeSlice(writeBew(value, length))


    def writeVarLen(self, value):
        "Writes a variable length word to the file"
        var = self.writeSlice(writeVar(value))


    def write(self):
        "Writes to disc"
        if self.outfile:
            if isinstance(self.outfile, StringType):
                outfile = open(self.outfile, 'wb')
                outfile.write(self.getvalue())
                outfile.close()
            else:
                self.outfile.write(self.getvalue())
        else:
            sys.stdout.write(self.getvalue())
                
    def getvalue(self):
        return self.buffer.getvalue()


if __name__ == '__main__':

    out_file = 'test/midifiles/midiout.mid'
    out_file = ''
    rawOut = RawOutstreamFile(out_file)
    rawOut.writeSlice('MThd')
    rawOut.writeBew(6, 4)
    rawOut.writeBew(1, 2)
    rawOut.writeBew(2, 2)
    rawOut.writeBew(15360, 2)
    rawOut.write()

########NEW FILE########
__FILENAME__ = video
#!/usr/bin/env python
# encoding: utf=8
"""
video.py

Framework that turns video into silly putty.

Created by Robert Ochshorn on 2008-5-30.
Refactored by Ben Lacker on 2009-6-18.
Copyright (c) 2008 The Echo Nest Corporation. All rights reserved.
"""
from numpy import *
import os
import re
import shutil
import subprocess
import sys
import tempfile

from echonest.remix import audio
from pyechonest import config


class ImageSequence():
    def __init__(self, sequence=None, settings=None):
        "builds sequence from a filelist, or another ImageSequence object"
        self.files, self.settings = [], VideoSettings()
        if isinstance(sequence, ImageSequence) or issubclass(sequence.__class__, ImageSequence): #from ImageSequence
           self.settings, self.files = sequence.settings, sequence.files
        if isinstance(sequence, list): #from filelist
            self.files = sequence
        if settings is not None:
            self.settings = settings
        self._init()

    def _init(self):
        "extra init settings/options (can override...)"
        return
        
    def __len__(self):
        "how many frames are in this sequence?"
        return len(self.files)

    def __getitem__(self, index):
        index = self.indexvoodo(index)
        if isinstance(index, slice):
            return self.getslice(index)
        else:
            raise TypeError("must provide an argument of type 'slice'")

    def getslice(self, index):
        "returns a slice of the frames as a new instance"
        if isinstance(index.start, float):
            index = slice(int(index.start*self.settings.fps), int(index.stop*self.settings.fps), index.step)
        return self.__class__(self.files[index], self.settings)

    def indexvoodo(self, index):
        "converts index to frame from a variety of forms"
        if isinstance(index, float):
            return int(index*self.settings.fps)
        return self._indexvoodoo(index)

    def _indexvoodoo(self, index):
        #obj to slice
        if not isinstance(index, slice) and hasattr(index, "start") and hasattr(index, "duration"):
            sl =  slice(index.start, index.start+index.duration)
            return sl
        #slice of objs: return slice(start.start, start.end.start+start.end.duration)
        if isinstance(index, slice):
            if hasattr(index.start, "start") and hasattr(index.stop, "duration") and hasattr(index.stop, "start"):
                sl = slice(index.start.start, index.stop.start+index.stop.duration)
                return sl
        return index

    def __add__(self, imseq2):
        """returns an ImageSequence with the second seq appended to this
        one. uses settings of the self."""
        self.render()
        imseq2.render() #todo: should the render be applied here? is it destructive? can it render in the new sequence?
        return self.__class__(self.files + imseq2.files, self.settings)

    def duration(self):
        "duration of a clip in seconds"
        return len(self) / float(self.settings.fps)

    def frametoim(self, index):
        "return a PIL image"
        return self.__getitem__(index)

    def renderframe(self, index, dest=None, replacefileinseq=True):
        "renders frame to destination directory. can update sequence with rendered image (default)"
        if dest is None:
            #handle, dest = tempfile.mkstemp()
            dest = tempfile.NamedTemporaryFile().name
        #copy file without loading
        shutil.copyfile(self.files[index], dest)
        #symlink file...
        #os.symlink(self.files[index], dest)
        if replacefileinseq:
            self.files[index] = dest
        
    def render(self, direc=None, pre="image", replacefiles=True):
        "renders sequence to stills. can update sequence with rendered images (default)"
        if direc is None: 
            #nothing to render...
            return
        dest = None
        for i in xrange(len(self.files)):
            if direc is not None:
                dest = os.path.join(direc, pre+'%(#)06d.' % {'#':i})+self.settings.imageformat()
            self.renderframe(i, dest, replacefiles)


class EditableFrames(ImageSequence):
    "Collection of frames that can be easily edited"

    def fadein(self, frames):
        "linear fade in"
        for i in xrange(frames):
            self[i] *= (float(i)/frames) #todo: can i do this without floats?

    def fadeout(self, frames):
        "linear fade out"
        for i in xrange(frames):
            self[len(self)-i-1] *= (float(i)/frames)


class VideoSettings():
    "simple container for video settings"
    def __init__(self):
        self.fps = None #SS.MM
        self.size = None #(w,h)
        self.aspect = None #(x,y) -> x:y
        self.bitrate = None #kb/s
        self.uncompressed = False

    def __str__(self):
        "format as ffmpeg commandline settings"
        cmd = ""
        if self.bitrate is not None:
            #bitrate
            cmd += " -b "+str(self.bitrate)+"k"
        if self.fps is not None:
            #framerate
            cmd += " -r "+str(self.fps)
        if self.size is not None:
            #size
            cmd += " -s "+str(self.size[0])+"x"+str(self.size[1])
        if self.aspect is not None:
            #aspect
            cmd += " -aspect "+str(self.aspect[0])+":"+str(self.aspect[1])
        return cmd

    def imageformat(self):
        "return a string indicating to PIL the image format"
        if self.uncompressed:
            return "ppm"
        else:
            return "jpeg"


class SynchronizedAV():
    "SynchronizedAV has audio and video; cuts return new SynchronizedAV objects"

    def __init__(self, audio=None, video=None):
        self.audio = audio
        self.video = video

    def __getitem__(self, index):
        "Returns a slice as synchronized AV"
        if isinstance(index, slice):
            return self.getslice(index)
        else:
            print >> sys.stderr, "WARNING: frame-based sampling not supported for synchronized AV"
            return None
    
    def getslice(self, index):
        return SynchronizedAV(audio=self.audio[index], video=self.video[index])
    
    def save(self, filename):
        audio_filename = filename + '.wav'
        audioout = self.audio.encode(audio_filename, mp3=False)
        self.video.render()
        res = sequencetomovie(filename, self.video, audioout)
        os.remove(audio_filename)
        return res
    
    def saveAsBundle(self, outdir):
        videodir = os.path.join(outdir, "video")
        videofile = os.path.join(outdir, "source.flv")
        audiofile = os.path.join(outdir, "audio.wav")
        os.makedirs(videodir)
        # audio.wav
        audioout = self.audio.encode(audiofile, mp3=False)
        # video frames (some may be symlinked)
        self.video.render(dir=videodir)
        # video file
        print sequencetomovie(videofile, self.video, audioout)


def loadav(videofile, verbose=True):
    foo, audio_file = tempfile.mkstemp(".mp3")        
    cmd = "en-ffmpeg -y -i \"" + videofile + "\" " + audio_file
    if verbose:
        print >> sys.stderr, cmd
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    res = out.communicate()
    ffmpeg_error_check(res[1])
    a = audio.LocalAudioFile(audio_file)
    v = sequencefrommov(videofile)
    return SynchronizedAV(audio=a, video=v)


def loadavfrombundle(dir):
    # video
    videopath = os.path.join(dir, "video")
    videosettings = VideoSettings()
    videosettings.fps = 25
    videosettings.size = (320, 240)
    video = sequencefromdir(videopath, settings=videosettings)
    # audio
    audiopath = os.path.join(dir, "audio.wav")
    analysispath = os.path.join(dir, "analysis.xml")
    myaudio = audio.LocalAudioFile(audiopath, analysis=analysispath, samplerate=22050, numchannels=1)
    return SynchronizedAV(audio=myaudio, video=video)


def loadavfromyoutube(url, verbose=True):
    """returns an editable sequence from a youtube video"""
    #todo: cache youtube videos?
    foo, yt_file = tempfile.mkstemp()        
    # https://github.com/rg3/youtube-dl/
    cmd = "youtube-dl -o " + "temp.video" + " " + url
    if verbose:
        print >> sys.stderr, cmd
    print "Downloading video..."
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (res, err) = out.communicate()
    print res, err

    # hack around the /tmp/ issue
    cmd = "mv -f temp.video yt_file"
    out = subprocess.Popen(['mv', '-f', 'temp.video', yt_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    (res, err) = out.communicate()
    return loadav(yt_file)


def youtubedl(url, verbose=True):
    """downloads a video from youtube and returns the file object"""
    foo, yt_file = tempfile.mkstemp()        
    # https://github.com/rg3/youtube-dl/
    cmd = "youtube-dl -o " + yt_file + " " + url
    if verbose:
        print >> sys.stderr, cmd
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    res = out.communicate()
    return yt_file


def getpieces(video, segs):
    a = audio.getpieces(video.audio, segs)
    newv = EditableFrames(settings=video.video.settings)
    for s in segs:
        newv += video.video[s]
    return SynchronizedAV(audio=a, video=newv)


def sequencefromyoutube(url, settings=None, dir=None, pre="frame-", verbose=True):
    """returns an editable sequence from a youtube video"""
    #todo: cache youtube videos?
    foo, yt_file = tempfile.mkstemp()
    # http://bitbucket.org/rg3/youtube-dl
    cmd = "youtube-dl -o " + yt_file + " " + url
    if verbose:
        print >> sys.stderr, cmd
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out.communicate()
    return sequencefrommov(yt_file, settings, dir, pre)


def sequencefromdir(dir, ext=None, settings=None):
    """returns an image sequence with lexographically-ordered images from
    a directory"""
    listing = os.listdir(dir)
    #remove files without the chosen extension
    if ext is not None:
        listing = filter(lambda x: x.split(".")[-1]==ext, listing)
    listing.sort()
    #full file paths, please
    listing = map(lambda x: os.path.join(dir, x), listing)
    return EditableFrames(listing, settings)


def sequencefrommov(mov, settings=None, direc=None, pre="frame-", verbose=True):
    """full-quality video import from stills. will save frames to
    tempspace if no directory is given"""
    if direc is None:
        #make directory for jpegs
        direc = tempfile.mkdtemp()
    format = "jpeg"
    if settings is not None:
        format = settings.imageformat()
    cmd = "en-ffmpeg -i " + mov + " -an -sameq " + os.path.join(direc, pre + "%06d." + format)
    if verbose:
        print >> sys.stderr, cmd
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    res = out.communicate()
    ffmpeg_error_check(res[1])
    settings = settingsfromffmpeg(res[1])
    seq =  sequencefromdir(direc, format, settings)
    #parse ffmpeg output for to find framerate and image size
    #todo: did this actually happen? errorcheck ffmpeg...
    return seq


def sequencetomovie(outfile, seq, audio=None, verbose=True):
    "renders sequence to a movie file, perhaps with an audio track"
    direc = tempfile.mkdtemp()
    seq.render(direc, "image-", False)
    cmd = "en-ffmpeg -y " + str(seq.settings) + " -i " + os.path.join(direc, "image-%06d." + seq.settings.imageformat())
    if audio:
        cmd += " -i " + audio
    cmd += " -sameq " + outfile
    if verbose:
        print >> sys.stderr, cmd
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    res = out.communicate()
    ffmpeg_error_check(res[1])


def convertmov(infile, outfile=None, settings=None, verbose=True):
    """
    Converts a movie file to a new movie file with different settings.
    """
    if settings is None:
        settings = VideoSettings()
        settings.fps = 29.97
        settings.size = (320, 180)
        settings.bitrate = 200
    if not isinstance(settings, VideoSettings):
        raise TypeError("settings arg must be a VideoSettings object")
    if outfile is None:
        foo, outfile = tempfile.mkstemp(".flv")
    cmd = "en-ffmpeg -y -i " + infile + " " + str(settings) + " -sameq " + outfile
    if verbose:
        print >> sys.stderr, cmd
    out = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    res = out.communicate()
    ffmpeg_error_check(res[1])
    return outfile


def settingsfromffmpeg(parsestring):
    """takes ffmpeg output and returns a VideoSettings object mimicking
    the input video"""
    settings = VideoSettings()
    parse = parsestring.split('\n')
    for line in parse:
        if "Stream #0.0" in line and "Video" in line:
            segs = line.split(", ")
            for seg in segs:
                if re.match("\d*x\d*", seg):
                    #dimensions found
                    settings.size = map(int, seg.split(" ")[0].split('x'))
                    if "DAR " in seg:
                        #display aspect ratio
                        start = seg.index("DAR ")+4
                        end = seg.index("]", start)
                        settings.aspect = map(int, seg[start:end].split(":"))
                elif re.match("(\d*\.)?\d+[\s]((fps)|(tbr)|(tbc)).*", seg):
                    #fps found
                    #todo: what's the difference between tb(r) and tb(c)?
                    settings.fps = float(seg.split(' ')[0])
                elif re.match("\d*.*kb.*s", seg):
                    #bitrate found. assume we want the same bitrate
                    settings.bitrate = int(seg[:seg.index(" ")])
    return settings

def ffmpeg_error_check(parsestring):
    parse = parsestring.split('\n')
    for num, line in enumerate(parse):
        if "Unknown format" in line or "error occur" in line:
            raise RuntimeError("en-ffmpeg conversion error:\n\t" + "\n\t".join(parse[num:]))


########NEW FILE########
__FILENAME__ = test_ffmpeg
#!/usr/bin/env python
# encoding: utf-8
"""
Test that an Echo-Nest-Remix-compatible version of ffmpeg is installed.

Run the tests like this:
    python test_ffmpeg.py
    
If you want to test that your version of ffmpeg can handle a particular file, 
(like if you're planning on analyzing OggVorbis files and want to make sure
your ffmpeg can decode them), run like this:
    python test_ffmpeg.py my_crazy_audio_file.mp47
"""

import os
import sys
import tempfile

from echonest import audio

def main():
    """Run some tests"""
    if len(sys.argv) > 1:
        input_filename = sys.argv[1]
    else:
	    input_filename = 'input_file.mp3'
    test_en_ffmpeg_exists(input_filename)
    test_round_trip(input_filename)

def test_en_ffmpeg_exists(input_filename):
    """Don't do any conversion, just see if en-ffmpeg, the command used
    by Remix, is installed."""
    result = audio.ffmpeg(input_filename, overwrite=False, verbose=True)
    audio.ffmpeg_error_check(result[1])

def test_round_trip(input_filename):
    """Convert the input file to a wav file, then back to an mp3 file."""
    result = audio.ffmpeg(input_filename, overwrite=False, verbose=True)
    audio.ffmpeg_error_check(result[1])
    sampleRate, numChannels = audio.settings_from_ffmpeg(result[1])
    
    temp_file_handle, temp_filename = tempfile.mkstemp(".wav")
    result = audio.ffmpeg(input_filename, temp_filename, overwrite=True, 
        numChannels=numChannels, sampleRate=sampleRate, verbose=True)
    audio.ffmpeg_error_check(result[1])
    
    temp_filesize = os.path.getsize(temp_filename)
    print 'temp file size: %s bytes' % temp_filesize
    
    output_filename = 'output_file.mp3'
    result = audio.ffmpeg(temp_filename, output_filename, overwrite=True, 
        numChannels=numChannels, sampleRate=sampleRate, verbose=True)
    audio.ffmpeg_error_check(result[1])
    
    if temp_file_handle is not None:
        os.close(temp_file_handle)
        os.remove(temp_filename)
    
    input_filesize = os.path.getsize(input_filename)
    output_filesize = os.path.getsize(output_filename)
    difference = output_filesize - input_filesize
    args = (input_filesize, output_filesize, difference)
    print 'input file size: %s bytes | output file size: %s bytes | difference: %s bytes ' % args
    if abs(int(difference)) > 1000:
        print 'input and output files are different sizes. something might be wrong with your ffmpeg.'
    else:
        print 'Ok!'

if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = afromb
#!/usr/bin/env python
# encoding: utf=8

"""
afromb.py

Re-synthesize song A using the segments of song B.

By Ben Lacker, 2009-02-24.
"""
# These lines import other things. 
import numpy
import sys
import time

# This line imports remix! 
import echonest.remix.audio as audio

usage="""
Usage:
    python afromb.py <inputfilenameA> <inputfilenameB> <outputfilename> <Mix> [env]

Example:
    python afromb.py BillieJean.mp3 CryMeARiver.mp3 BillieJeanFromCryMeARiver.mp3 0.9 env

The 'env' flag applies the volume envelopes of the segments of A to those
from B.

Mix is a number 0-1 that determines the relative mix of the resynthesized
song and the original input A. i.e. a mix value of 0.9 yields an output that
is mostly the resynthesized version.

"""

# AfromB is much more complex than the prior examples!  
# Hold on, and we'll try to make everything make sense
# AfromB uses chunks of track B to make a version of track A.
# It does this by splitting both tracks into their component segments.
# Then, for each segment in track A, it tries to find the closest segment in track B.
# It does this by comparing pitch, timbre, and loudness.
# The closest segment is added to a list.
# This list is then used to create the output file.
    
# This is the class that does the work of resynthesizing the audio
class AfromB(object):

    # This sets up the variables
    def __init__(self, input_filename_a, input_filename_b, output_filename):
        self.input_a = audio.LocalAudioFile(input_filename_a)
        self.input_b = audio.LocalAudioFile(input_filename_b)
        self.segs_a = self.input_a.analysis.segments
        self.segs_b = self.input_b.analysis.segments
        self.output_filename = output_filename

    # This words out the distance matrix in terms of pitch, timbre, and loudness
    # It gets used when picking segments in the main loop in run()
    def calculate_distances(self, a):
        distance_matrix = numpy.zeros((len(self.segs_b), 4),
                                        dtype=numpy.float32)
        pitch_distances = []
        timbre_distances = []
        loudmax_distances = []
        for b in self.segs_b:
            pitch_diff = numpy.subtract(b.pitches,a.pitches)
            pitch_distances.append(numpy.sum(numpy.square(pitch_diff)))
            timbre_diff = numpy.subtract(b.timbre,a.timbre)
            timbre_distances.append(numpy.sum(numpy.square(timbre_diff)))
            loudmax_diff = b.loudness_begin - a.loudness_begin
            loudmax_distances.append(numpy.square(loudmax_diff))
        distance_matrix[:,0] = pitch_distances
        distance_matrix[:,1] = timbre_distances
        distance_matrix[:,2] = loudmax_distances
        distance_matrix[:,3] = range(len(self.segs_b))
        distance_matrix = self.normalize_distance_matrix(distance_matrix)
        return distance_matrix

    # This normalizes the distance matrix.  It gets used when calculating the distance matrix, above.
    def normalize_distance_matrix(self, mat, mode='minmed'):
        """ Normalize a distance matrix on a per column basis.
        """
        if mode == 'minstd':
            mini = numpy.min(mat,0)
            m = numpy.subtract(mat, mini)
            std = numpy.std(mat,0)
            m = numpy.divide(m, std)
            m = numpy.divide(m, mat.shape[1])
        elif mode == 'minmed':
            mini = numpy.min(mat,0)
            m = numpy.subtract(mat, mini)
            med = numpy.median(m)
            m = numpy.divide(m, med)
            m = numpy.divide(m, mat.shape[1])
        elif mode == 'std':
            std = numpy.std(mat,0)
            m = numpy.divide(mat, std)
            m = numpy.divide(m, mat.shape[1])
        return m

    # This is the function that starts things off
    def run(self, mix=0.5, envelope=False):
        # This chunk creates a new array of AudioData to put the resulting resynthesis in:

        # Add two seconds to the length, just in case
        dur = len(self.input_a.data) + 100000 

        # This determines the 'shape' of new array.
        # (Shape is a tuple (x, y) that indicates the length per channel of the audio file)
        # If we have a stereo shape, copy that shape
        if len(self.input_a.data.shape) > 1:
            new_shape = (dur, self.input_a.data.shape[1])
            new_channels = self.input_a.data.shape[1]
        # If not, make a mono shape
        else:
            new_shape = (dur,)
            new_channels = 1
        # This creates the new AudioData array, based on the new shape
        out = audio.AudioData(shape=new_shape,
                            sampleRate=self.input_b.sampleRate,
                            numChannels=new_channels)

        # Now that we have a properly formed array to put chunks of audio in, 
        # we can start deciding what chunks to put in!

        # This loops over each segment in file A and finds the best matching segment from file B
        for a in self.segs_a:
            seg_index = a.absolute_context()[0]

            # This works out the distances
            distance_matrix = self.calculate_distances(a)
            distances = [numpy.sqrt(x[0]+x[1]+x[2]) for x in distance_matrix]

            # This gets the best match
            match = self.segs_b[distances.index(min(distances))]
            segment_data = self.input_b[match]
            reference_data = self.input_a[a]

            # This corrects for length:  if our new segment is shorter, we add silence
            if segment_data.endindex < reference_data.endindex:
                if new_channels > 1:
                    silence_shape = (reference_data.endindex,new_channels)
                else:
                    silence_shape = (reference_data.endindex,)
                new_segment = audio.AudioData(shape=silence_shape,
                                        sampleRate=out.sampleRate,
                                        numChannels=segment_data.numChannels)
                new_segment.append(segment_data)
                new_segment.endindex = len(new_segment)
                segment_data = new_segment

            # Or, if our new segment is too long, we make it shorter
            elif segment_data.endindex > reference_data.endindex:
                index = slice(0, int(reference_data.endindex), 1)
                segment_data = audio.AudioData(None,segment_data.data[index],
                                        sampleRate=segment_data.sampleRate)
            
            # This applies the volume envelopes from each segment of A to the segment from B.
            if envelope:
                # This gets the maximum volume and starting volume for the segment from A:
                # db -> voltage ratio http://www.mogami.com/e/cad/db.html
                linear_max_volume = pow(10.0,a.loudness_max/20.0)
                linear_start_volume = pow(10.0,a.loudness_begin/20.0)
        
                # This gets the starting volume for the next segment
                if(seg_index == len(self.segs_a)-1): # If this is the last segment, the next volume is zero
                    linear_next_start_volume = 0
                else:
                    linear_next_start_volume = pow(10.0,self.segs_a[seg_index+1].loudness_begin/20.0)
                    pass

                # This gets when the maximum volume occurs in A
                when_max_volume = a.time_loudness_max

                # Count # of ticks I wait doing volume ramp so I can fix up rounding errors later.
                ss = 0
                # This sets the starting volume volume of this segment. 
                cur_vol = float(linear_start_volume)
                # This  ramps up to the maximum volume from start
                samps_to_max_loudness_from_here = int(segment_data.sampleRate * when_max_volume)
                if(samps_to_max_loudness_from_here > 0):
                    how_much_volume_to_increase_per_samp = float(linear_max_volume - linear_start_volume)/float(samps_to_max_loudness_from_here)
                    for samps in xrange(samps_to_max_loudness_from_here):
                        try:
                            # This actally applies the volume modification
                            segment_data.data[ss] *= cur_vol
                        except IndexError:
                            pass
                        cur_vol = cur_vol + how_much_volume_to_increase_per_samp
                        ss = ss + 1
                # This ramp down to the volume for the start of the next segent
                samps_to_next_segment_from_here = int(segment_data.sampleRate * (a.duration-when_max_volume))
                if(samps_to_next_segment_from_here > 0):
                    how_much_volume_to_decrease_per_samp = float(linear_max_volume - linear_next_start_volume)/float(samps_to_next_segment_from_here)
                    for samps in xrange(samps_to_next_segment_from_here):
                        cur_vol = cur_vol - how_much_volume_to_decrease_per_samp
                        try:
                            # This actally applies the volume modification
                            segment_data.data[ss] *= cur_vol
                        except IndexError:
                            pass
                        ss = ss + 1
            
            # This mixes the segment from B with the segment from A, and adds it to the output
            mixed_data = audio.mix(segment_data,reference_data,mix=mix)
            out.append(mixed_data)

        # This writes the newly created audio to the given file.  Phew!
        out.encode(self.output_filename)


    # The main function. 
def main():
    try:
        # This gets the files to read from and write to, and sets the mix and envelope
        input_filename_a = sys.argv[1]
        input_filename_b = sys.argv[2]
        output_filename = sys.argv[3]
        mix = sys.argv[4]
        if len(sys.argv) == 6:
            env = True
        else:
            env = False
    except:
        # If things go wrong, exit!
        print usage
        sys.exit(-1)

    # If things don't go wrong, go!
    AfromB(input_filename_a, input_filename_b, output_filename).run(mix=mix,
                                                                envelope=env)
    
    # This is where things start.  It just sets up a timer so we know how long the process took.
if __name__=='__main__':
    tic = time.time()
    main()
    toc = time.time()
    print "Elapsed time: %.3f sec" % float(toc-tic)


########NEW FILE########
__FILENAME__ = cowbell
# By Rob Ochshorn and Adam Baratz.
# Slightly refactored by Joshua Lifton.
import numpy
import os
import random
import time

import echonest.remix.audio as audio

usage = """
Usage: 
    python cowbell.py <inputFilename> <outputFilename> <cowbellIntensity> <walkenIntensity>

Example:
    python cowbell.py YouCanCallMeAl.mp3 YouCanCallMeCow.mp3 0.2 0.5

Reference:
    http://www.youtube.com/watch?v=ZhSkRHXTKlw
"""

# constants
COWBELL_THRESHOLD = 0.85
COWBELL_OFFSET = -0.005

# samples
soundsPath = "sounds/"

cowbellSounds = map(lambda x: audio.AudioData(os.path.join(soundsPath, "cowbell%s.wav" % x), sampleRate=44100, numChannels=2), range(5))
walkenSounds = map(lambda x: audio.AudioData(os.path.join(soundsPath, "walken%s.wav" % x), sampleRate=44100, numChannels=2), range(16))
trill = audio.AudioData(os.path.join(soundsPath, "trill.wav"), sampleRate=44100, numChannels=2)

def linear(input, in1, in2, out1, out2):
    return ((input-in1) / (in2-in1)) * (out2-out1) + out1

def exp(input, in1, in2, out1, out2, coeff):
    if (input <= in1):
        return out1
    if (input >= in2):
        return out2
    return pow( ((input-in1) / (in2-in1)) , coeff ) * (out2-out1) + out1

class Cowbell:
    def __init__(self, input_file):
        self.audiofile = audio.LocalAudioFile(input_file)
        self.audiofile.data *= linear(self.audiofile.analysis.loudness, -2, -12, 0.5, 1.5) * 0.75

    def run(self, cowbell_intensity, walken_intensity, out):
        if cowbell_intensity != -1:
            self.cowbell_intensity = cowbell_intensity
            self.walken_intensity = walken_intensity
        t1 = time.time()
        sequence = self.sequence(cowbellSounds)
        print "Sequence and mixed in %g seconds" % (time.time() - t1)
        self.audiofile.encode(out)

    def sequence(self, chops):
        # add cowbells on the beats
        for beat in self.audiofile.analysis.beats:
            volume = linear(self.cowbell_intensity, 0, 1, 0.1, 0.3)
            # mix in cowbell on beat
            if self.cowbell_intensity == 1:
                self.mix(beat.start+COWBELL_OFFSET, seg=cowbellSounds[random.randint(0,1)], volume=volume)
            else:
                self.mix(beat.start+COWBELL_OFFSET, seg=cowbellSounds[random.randint(2,4)], volume=volume)
            # divide beat into quarters
            quarters = (numpy.arange(1,4) * beat.duration) / 4. + beat.start
            # mix in cowbell on quarters
            for quarter in quarters:
                volume = exp(random.random(), 0.5, 0.1, 0, self.cowbell_intensity, 0.8) * 0.3
                pan = linear(random.random(), 0, 1, -self.cowbell_intensity, self.cowbell_intensity)
                if self.cowbell_intensity < COWBELL_THRESHOLD:
                    self.mix(quarter+COWBELL_OFFSET, seg=cowbellSounds[2], volume=volume)
                else:
                    randomCowbell = linear(random.random(), 0, 1, COWBELL_THRESHOLD, 1)
                    if randomCowbell < self.cowbell_intensity:
                        self.mix(start=quarter+COWBELL_OFFSET, seg=cowbellSounds[random.randint(0,1)], volume=volume)
                    else:
                        self.mix(start=quarter+COWBELL_OFFSET, seg=cowbellSounds[random.randint(2,4)], volume=volume)
        # add trills / walken on section changes
        for section in self.audiofile.analysis.sections[1:]:
            if random.random() > self.walken_intensity:
                sample = trill
                volume = 0.3
            else:
                sample = walkenSounds[random.randint(0, len(walkenSounds)-1)]
                volume = 1.5
            self.mix(start=section.start+COWBELL_OFFSET, seg=sample, volume=volume)

    def mix(self, start=None, seg=None, volume=0.3, pan=0.):
        # this assumes that the audios have the same frequency/numchannels
        startsample = int(start * self.audiofile.sampleRate)
        seg = seg[0:]
        seg.data *= (volume-(pan*volume), volume+(pan*volume)) # pan + volume
        if self.audiofile.data.shape[0] - startsample > seg.data.shape[0]:
            self.audiofile.data[startsample:startsample+len(seg.data)] += seg.data[0:]


def main(inputFilename, outputFilename, cowbellIntensity, walkenIntensity ) :
    c = Cowbell(inputFilename)
    print 'cowbelling...'
    c.run(cowbellIntensity, walkenIntensity, outputFilename)

if __name__ == '__main__':
    import sys
    try :
        inputFilename = sys.argv[1]
        outputFilename = sys.argv[2]
        cowbellIntensity = float(sys.argv[3])
        walkenIntensity = float(sys.argv[4])
    except :
        print usage
        sys.exit(-1)
    main(inputFilename, outputFilename, cowbellIntensity, walkenIntensity)

########NEW FILE########
__FILENAME__ = cowbell
# By Rob Ochshorn and Adam Baratz.
# Slightly refactored by Joshua Lifton.

# These lines import other things. 
import numpy
import os
import random
import time
# This line imports remix! 
import echonest.remix.audio as audio

usage = """
Usage: 
    python cowbell.py <inputFilename> <outputFilename> <cowbellIntensity> <walkenIntensity>

Example:
    python cowbell.py YouCanCallMeAl.mp3 YouCanCallMeCow.mp3 0.2 0.5

Reference:
    http://www.youtube.com/watch?v=ZhSkRHXTKlw
"""

# Cowbell is pretty complex!
# Hold on, and we'll try to make everything make sense
# Cowbell adds a cowbell sample to each beat of the track,
# and add Christopher Walken samples at the end of each section.
# It does this by splitting the track into its component beats.
# Then, for each beat in the track, it mixes in one or more cowbell samples.
# To add the Walken samples, it does the same process for each section of the track.  

# These are constants for how the cowbell is added
COWBELL_THRESHOLD = 0.85
COWBELL_OFFSET = -0.005

# This is the path to the samples
soundsPath = "sounds/"
# This gets the samples into remix
cowbellSounds = map(lambda x: audio.AudioData(os.path.join(soundsPath, "cowbell%s.wav" % x), sampleRate=44100, numChannels=2), range(5))
walkenSounds = map(lambda x: audio.AudioData(os.path.join(soundsPath, "walken%s.wav" % x), sampleRate=44100, numChannels=2), range(16))
trill = audio.AudioData(os.path.join(soundsPath, "trill.wav"), sampleRate=44100, numChannels=2)

    # Helper function for dealing with volume
def linear(input, in1, in2, out1, out2):
    return ((input-in1) / (in2-in1)) * (out2-out1) + out1
    # Helper function for dealing with volume
def exp(input, in1, in2, out1, out2, coeff):
    if (input <= in1):
        return out1
    if (input >= in2):
        return out2
    return pow( ((input-in1) / (in2-in1)) , coeff ) * (out2-out1) + out1

    # The main class
class Cowbell:
        # This gets the input file into remix, and scales the loudness down to avoid clipping
    def __init__(self, input_file):
        self.audiofile = audio.LocalAudioFile(input_file)
        self.audiofile.data *= linear(self.audiofile.analysis.loudness, -2, -12, 0.5, 1.5) * 0.75

        # This sets up the intensities, and then sequences the file
    def run(self, cowbell_intensity, walken_intensity, out):
        # This sets the intensities
        if cowbell_intensity != -1:
            self.cowbell_intensity = cowbell_intensity
            self.walken_intensity = walken_intensity
        t1 = time.time()
        # This calls sequence, which adds the cowbell sounds
        sequence = self.sequence(cowbellSounds)
        print "Sequence and mixed in %g seconds" % (time.time() - t1)
        # This writes the newly created audio to the given file.  
        self.audiofile.encode(out)

        # Where the magic happens:  
    def sequence(self, chops):
        # This adds cowbell to each beat
        for beat in self.audiofile.analysis.beats:
            volume = linear(self.cowbell_intensity, 0, 1, 0.1, 0.3)
            # Mix the audio
            if self.cowbell_intensity == 1:
                self.mix(beat.start+COWBELL_OFFSET, seg=cowbellSounds[random.randint(0,1)], volume=volume)
            else:
                self.mix(beat.start+COWBELL_OFFSET, seg=cowbellSounds[random.randint(2,4)], volume=volume)
            
            # This splits the beat into quarters (16th notes)
            quarters = (numpy.arange(1,4) * beat.duration) / 4. + beat.start
            # This adds occasional extra cowbell hits on the 16th notes
            for quarter in quarters:
                volume = exp(random.random(), 0.5, 0.1, 0, self.cowbell_intensity, 0.8) * 0.3
                pan = linear(random.random(), 0, 1, -self.cowbell_intensity, self.cowbell_intensity)
                # If we're over the cowbell threshold, add a cowbell
                if self.cowbell_intensity < COWBELL_THRESHOLD:
                    self.mix(quarter+COWBELL_OFFSET, seg=cowbellSounds[2], volume=volume)
                else:
                    randomCowbell = linear(random.random(), 0, 1, COWBELL_THRESHOLD, 1)
                    if randomCowbell < self.cowbell_intensity:
                        self.mix(start=quarter+COWBELL_OFFSET, seg=cowbellSounds[random.randint(0,1)], volume=volume)
                    else:
                        self.mix(start=quarter+COWBELL_OFFSET, seg=cowbellSounds[random.randint(2,4)], volume=volume)
        
        # This adds cowbell trills or Walken samples when sections change
        for section in self.audiofile.analysis.sections[1:]:
            # This chooses a cowbell trill or a Walken sample
            if random.random() > self.walken_intensity:
                sample = trill
                volume = 0.3
            else:
                sample = walkenSounds[random.randint(0, len(walkenSounds)-1)]
                volume = 1.5
            # Mix the audio
            self.mix(start=section.start+COWBELL_OFFSET, seg=sample, volume=volume)

        # This function mixes the input audio with the cowbell audio.  (audio.mix also does this!)
    def mix(self, start=None, seg=None, volume=0.3, pan=0.):
        # this assumes that the audios have the same frequency/numchannels
        startsample = int(start * self.audiofile.sampleRate)
        seg = seg[0:]
        seg.data *= (volume-(pan*volume), volume+(pan*volume)) # pan + volume
        if self.audiofile.data.shape[0] - startsample > seg.data.shape[0]:
            self.audiofile.data[startsample:startsample+len(seg.data)] += seg.data[0:]

    # Creates a 'Cowbell' object, and then runs it.
def main(inputFilename, outputFilename, cowbellIntensity, walkenIntensity ) :
    c = Cowbell(inputFilename)
    print 'cowbelling...'
    c.run(cowbellIntensity, walkenIntensity, outputFilename)

    # The wrapper for the script.  
if __name__ == '__main__':
    import sys
    try :
        # This gets the filenames to read from and write to, 
        # and sets how loud the cowbell and walken samples will be
        inputFilename = sys.argv[1]
        outputFilename = sys.argv[2]
        cowbellIntensity = float(sys.argv[3])
        walkenIntensity = float(sys.argv[4])
    except :
        # If things go wrong, exit!
        print usage
        sys.exit(-1)
    main(inputFilename, outputFilename, cowbellIntensity, walkenIntensity)


########NEW FILE########
__FILENAME__ = drums
#!/usr/bin/env python
# encoding: utf=8
"""
drums.py

Add drums to a song.

At the moment, only works with songs in 4, and endings are rough.

By Ben Lacker, 2009-02-24.
"""
# These lines import other things. 
import numpy
import sys
import time

# This line imports remix! 
import echonest.remix.audio as audio

usage="""
Usage:
    python drums.py <inputfilename> <breakfilename> <outputfilename> <beatsinbreak> <barsinbreak> [<drumintensity>]

Example:
    python drums.py HereComesTheSun.mp3 breaks/AmenBrother.mp3 HereComeTheDrums.mp3 64 4 0.6

Drum intensity defaults to 0.5
"""

# Drums is pretty complex!
# Hold on, and we'll try to make everything make sense.
# Drums adds a new drum break to the track.  
# It does this by splitting the drum break into its component beats and tatums.
# Then, for every tatum in the input track, it mixes in the appropriate tatum of the break.
# That is to say, it is mapping every beat of the break to the beat of the input track.


    # This converts a mono file to stereo. It is used in main() to make sure that the input break stereo
def mono_to_stereo(audio_data):
    data = audio_data.data.flatten().tolist()
    new_data = numpy.array((data,data))
    audio_data.data = new_data.swapaxes(0,1)
    audio_data.numChannels = 2
    return audio_data

    # This splits the break into each beat
def split_break(breakfile,n):
    drum_data = []
    start = 0
    for i in range(n):
        start = int((len(breakfile) * (i))/n)
        end = int((len(breakfile) * (i+1))/n)
        ndarray = breakfile.data[start:end]
        new_data = audio.AudioData(ndarray=ndarray,
                                    sampleRate=breakfile.sampleRate,
                                    numChannels=breakfile.numChannels)
        drum_data.append(new_data)
    return drum_data
    

    # This is where things happen
def main(input_filename, output_filename, break_filename, break_parts, measures, mix):

    # This takes the input tracks, sends them to the analyzer, and returns the results.  
    audiofile = audio.LocalAudioFile(input_filename)
    sample_rate = audiofile.sampleRate
    breakfile = audio.LocalAudioFile(break_filename)

    # This converts the break to stereo, if it is mono
    if breakfile.numChannels == 1:
        breakfile = mono_to_stereo(breakfile)

    # This gets the number of channels in the main file
    num_channels = audiofile.numChannels

    # This splits the break into each beat
    drum_data = split_break(breakfile, break_parts)
    hits_per_beat = int(break_parts/(4 * measures))
    # This gets the bars from the input track
    bars = audiofile.analysis.bars
    
    # This creates the 'shape' of new array.
    # (Shape is a tuple (x, y) that indicates the length per channel of the audio file)
    out_shape = (len(audiofile)+100000,num_channels)
    # This creates a new AudioData array to write data to
    out = audio.AudioData(shape=out_shape, sampleRate=sample_rate,
                            numChannels=num_channels)
    if not bars:
        # If the analysis can't find any bars, stop!
        # (This might happen with really ambient music)
        print "Didn't find any bars in this analysis!"
        print "No output."
        sys.exit(-1)

    # This is where the magic happens:
    # For every beat in every bar except the last bar, 
    # map the tatums of the break to the tatums of the beat
    for bar in bars[:-1]:
        # This gets the beats in the bar, and loops over them
        beats = bar.children()
        for i in range(len(beats)):
            # This gets the index of matching beat in the break
            try:
                break_index = ((bar.local_context()[0] %\
                                measures) * 4) + (i % 4)
            except ValueError:
                break_index = i % 4
            # This gets the tatums from the beat of the break
            tats = range((break_index) * hits_per_beat,
                        (break_index + 1) * hits_per_beat)
            # This gets the number of samples in each tatum
            drum_samps = sum([len(drum_data[x]) for x in tats])

            # This gets the number of sample and the shape of the beat from the original track
            beat_samps = len(audiofile[beats[i]])
            beat_shape = (beat_samps,num_channels)
            
            # This get the shape of each tatum
            tat_shape = (float(beat_samps/hits_per_beat),num_channels)
        
            # This creates the new AudioData that will be filled with chunks of the drum break
            beat_data= audio.AudioData(shape=beat_shape,
                                        sampleRate=sample_rate,
                                        numChannels=num_channels)
            for j in tats:
                # This creates an audioData for each tatum
                tat_data= audio.AudioData(shape=tat_shape,
                                            sampleRate=sample_rate,
                                            numChannels=num_channels)
                # This corrects for length / timing:
                # If the original is shorter than the break, truncate drum hits to fit beat length
                if drum_samps > beat_samps/hits_per_beat:
                    tat_data.data = drum_data[j].data[:len(tat_data)]
                # If the original is longer, space out drum hits to fit beat length
                elif drum_samps < beat_samps/hits_per_beat:
                    tat_data.append(drum_data[j])

                # This adds each new tatum to the new beat.
                tat_data.endindex = len(tat_data)
                beat_data.append(tat_data)
                del(tat_data)

            # This corrects for rounding errors
            beat_data.endindex = len(beat_data)

            # This mixes the new beat data with the input data, and appends it to the final file
            mixed_beat = audio.mix(beat_data, audiofile[beats[i]], mix=mix)
            del(beat_data)
            out.append(mixed_beat)

    # This works out the last beat and appends it to the final file
    finale = bars[-1].start + bars[-1].duration
    last = audio.AudioQuantum(audiofile.analysis.bars[-1].start,
                            audiofile.analysis.duration - 
                              audiofile.analysis.bars[-1].start)
    last_data = audio.getpieces(audiofile,[last])
    out.append(last_data)
    
    # This writes the newly created audio to the given file.  
    out.encode(output_filename)

    # The wrapper for the script.  
if __name__=='__main__':
    try:
        # This gets the filenames to read from and write to, 
        # and sets the number of beats and bars in the break, and the mix level
        input_filename = sys.argv[1]
        break_filename = sys.argv[2]
        output_filename = sys.argv[3]
        break_parts = int(sys.argv[4])
        measures = int(sys.argv[5])
        if len(sys.argv) == 7:
            mix = float(sys.argv[6])
        else:
            mix = 0.5
    except:
        # If things go wrong, exit!
        print usage
        sys.exit(-1)
    main(input_filename, output_filename, break_filename, break_parts,
            measures, mix)

########NEW FILE########
__FILENAME__ = lopside
#!/usr/bin/env python
# encoding: utf=8

"""
lopside.py

Cut out the final beat or group of tatums in each bar.
Demonstrates the beat hierarchy navigation in AudioQuantum

Originally by Adam Lindsay, 2009-01-19.
"""

# This line imports remix! 
import echonest.remix.audio as audio
import sys

usage = """
Usage: 
    python lopside.py [tatum|beat] <inputFilename> <outputFilename>
Beat is selected by default.

Example:
    python lopside.py beat aha.mp3 ahawaltz.mp3
"""

# Lopside changes the meter of a track!
# It does this by removing the last beat of every bar.
# So a song that is in 4 will be in 3.
# It does this by looping over the component bars of the track.
# Then, it adds all but the last beat of each bar to a list.
# That list is then used to create the output audio file.

def main(units, inputFile, outputFile):
    # This takes your input track, sends it to the analyzer, and returns the results. 
    audiofile = audio.LocalAudioFile(inputFile)

    # This makes a new list of "AudioQuantums".  
    # Those are just any discrete chunk of audio:  bars, beats, etc
    collect = audio.AudioQuantumList()

    # If the analysis can't find any bars, stop!
    # (This might happen with really ambient music)
    if not audiofile.analysis.bars:
        print "No bars found in this analysis!"
        print "No output."
        sys.exit(-1)

    # This loop puts all but the last of each bar into the new list! 
    for b in audiofile.analysis.bars[0:-1]:                
        collect.extend(b.children()[0:-1])

        # If we're using tatums instead of beats, we want all but the last half (round down) of the last beat
        # A tatum is the smallest rhythmic subdivision of a beat -- http://en.wikipedia.org/wiki/Tatum_grid     
        if units.startswith("tatum"):
            half = - (len(b.children()[-1].children()) // 2)
            collect.extend(b.children()[-1].children()[0:half])

    # Endings were rough, so leave everything after the start of the final bar intact:
    last = audio.AudioQuantum(audiofile.analysis.bars[-1].start,
                              audiofile.analysis.duration - 
                                audiofile.analysis.bars[-1].start)
    collect.append(last)

    # This assembles the pieces of audio defined in collect from the analyzed audio file.
    out = audio.getpieces(audiofile, collect)

    # This writes the newly created audio to the given file.  
    out.encode(outputFile)

    # The wrapper for the script.  
if __name__ == '__main__':
    try:
        # This gets the units type, and the filenames to read from and write to.
        units = sys.argv[-3]
        inputFilename = sys.argv[-2]
        outputFilename = sys.argv[-1]
    except:
        # If things go wrong, exit!
        print usage
        sys.exit(-1)
    main(units, inputFilename, outputFilename)

########NEW FILE########
__FILENAME__ = one
#!/usr/bin/env python
# encoding: utf=8
"""
one.py

Digest only the first beat of every bar.

By Ben Lacker, 2009-02-18.  
"""
# This line imports remix! 
import echonest.remix.audio as audio

usage = """
Usage: 
    python one.py <input_filename> <output_filename>

Example:
    python one.py EverythingIsOnTheOne.mp3 EverythingIsReallyOnTheOne.mp3
"""

# One outputs only the first beat of each bar!
# It does this by looping over the component bars of the track.
# Then, it adds the first beat of each bar to a list.
# That list is then used to create the output audio file.

def main(input_filename, output_filename):
    # This takes your input track, sends it to the analyzer, and returns the results.  
    audiofile = audio.LocalAudioFile(input_filename)

    # This gets a list of every bar in the track.  
    # You can manipulate this just like any other Python list!
    bars = audiofile.analysis.bars

    # This makes a new list of "AudioQuantums".  
    # Those are just any discrete chunk of audio:  bars, beats, etc.
    collect = audio.AudioQuantumList()

    # This loop puts the first item in the children of each bar into the new list. 
    # A bar's children are beats!  Simple as that. 
    for bar in bars:
        collect.append(bar.children()[0])

    # This assembles the pieces of audio defined in collect from the analyzed audio file.
    out = audio.getpieces(audiofile, collect)
    
    # This writes the newly created audio to the given file.  
    out.encode(output_filename)


    # The wrapper for the script.  
if __name__ == '__main__':
    import sys
    try:
        # This gets the filenames to read from and write to.
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        # If things go wrong, exit!
        print usage
        sys.exit(-1)
    main(input_filename, output_filename)

########NEW FILE########
__FILENAME__ = reverse
#!/usr/bin/env python
# encoding: utf=8

"""
reverse.py

Reverse the beats or segments of a song.

Originally created by Robert Ochshorn on 2008-06-11.  Refactored by
Joshua Lifton 2008-09-07.
"""

import echonest.remix.audio as audio

usage = """
Usage: 
    python reverse.py <beats|segments> <inputFilename> <outputFilename.wav>

Example:
    python reverse.py beats YouCanCallMeAl.mp3 AlMeCallCanYou.mp3
"""

# Reverse plays the beats or segments of a sound backwards!
# It does this by getting a list of every beat or segment in a track.
# Then, it reverses the list.
# This reversed list is used to create the output file.

def main(toReverse, inputFilename, outputFilename):
    # This takes your input track, sends it to the analyzer, and returns the results.  
    audioFile = audio.LocalAudioFile(inputFilename)

    # Checks what sort of reversing we're doing.
    if toReverse == 'beats' :
        # This gets a list of every beat in the track.  
        chunks = audioFile.analysis.beats
    elif toReverse == 'segments' :
        # This gets a list of every segment in the track.  
        # Segments are the smallest chunk of audio that Remix deals with
        chunks = audioFile.analysis.segments
    else :
        print usage
        return

    # Reverse the list!
    chunks.reverse()

    # This assembles the pieces of audio defined in chunks from the analyzed audio file.
    reversedAudio = audio.getpieces(audioFile, chunks)
    # This writes the newly created audio to the given file.  
    reversedAudio.encode(outputFilename)

    # The wrapper for the script.  
if __name__ == '__main__':
    import sys
    try :
        # This gets what sort of reversing we're doing, and the filenames to read from and write to.
        toReverse = sys.argv[1]
        inputFilename = sys.argv[2]
        outputFilename = sys.argv[3]
    except :
        # If things go wrong, exit!
        print usage
        sys.exit(-1)
    if not toReverse in ["beats", "segments"]:
        print usage
        sys.exit(-1)
    main(toReverse, inputFilename, outputFilename)

########NEW FILE########
__FILENAME__ = tonic
#!/usr/bin/env python
# encoding: utf=8

"""
tonic.py

Digest all beats, tatums, or bars that start in the key of the song.
Demonstrates content-based selection filtering via AudioQuantumLists

Originally by Adam Lindsay, 2008-09-15.
Refactored by Thor Kell, 2012-11-01
"""
import echonest.remix.audio as audio

usage = """
Usage: 
    python tonic.py <tatums|beats|bars> <inputFilename> <outputFilename>

Example:
    python tonic.py beats HereComesTheSun.mp3 HereComesTheTonic.mp3
"""

# Tonic plays only the beats of a song that are playing the tonic note!
# It does this by getting a list of every segment in a track
# Then, it checks to see which segments are playing the tonic.
# Then, any beats that include those segments are added to a list.
# This list is used to create the output track.

ACCEPTED_UNITS = ["tatums", "beats", "bars"]

def main(units, inputFile, outputFile):
    audiofile = audio.LocalAudioFile(inputFile)
    tonic = audiofile.analysis.key['value']
    
    chunks = audiofile.analysis.__getattribute__(units)
    
    # Get the segments    
    all_segments = audiofile.analysis.segments
    
    # Find tonic segments
    tonic_segments = audio.AudioQuantumList(kind="segment")
    for segment in all_segments:
        pitches = segment.pitches
        if pitches.index(max(pitches)) == tonic:
            tonic_segments.append(segment)

    # Find each chunk that matches each segment
    out_chunks = audio.AudioQuantumList(kind=units) 
    for chunk in chunks:
        for segment in tonic_segments:
            if chunk.start >= segment.start and segment.end >= chunk.start:
                out_chunks.append(chunk)
                break
    
    out = audio.getpieces(audiofile, out_chunks)
    out.encode(outputFile)

if __name__ == '__main__':
    import sys
    try:
        units = sys.argv[-3]
        inputFilename = sys.argv[-2]
        outputFilename = sys.argv[-1]
    except:
        print usage
        sys.exit(-1)
    if not units in ACCEPTED_UNITS:
        print usage
        sys.exit(-1)
    main(units, inputFilename, outputFilename)

########NEW FILE########
__FILENAME__ = beatshift
#!/usr/bin/env python
# encoding: utf-8
"""
beatshift.py

Pitchshift each beat based on its position in the bar.
Beat one is unchanged, beat two is shifted down one half step,
beat three is shifted down two half steps, etc.

Created by Ben Lacker on 2009-06-24.
Refactored by Thor Kell on 2013-03-06.
"""

# Import other things
import numpy
import os
import random
import sys
import time

# This line imports remix! 
from echonest.remix import audio, modify

usage = """
Usage:
    python beatshift.py <input_filename> <output_filename>
Exampel:
    python beatshift.py CryMeARiver.mp3 CryMeAShifty.mp3
"""

# Beatshift changes the pitch of each beat!
# It does this by looping over the component beats of the track.
# Then, it pitchshifts each beat relative to it's position in the bar
# This pitch-shifted beat is added to a list.
# That list is then used to create the output audio file.

def main(input_filename, output_filename):
    # Just a local alias to the soundtouch library, which handles the pitch shifting.
    soundtouch = modify.Modify()

    # This takes your input track, sends it to the analyzer, and returns the results.  
    audiofile = audio.LocalAudioFile(input_filename)

    # This gets a list of every beat in the track.  
    # You can manipulate this just like any other Python list!
    beats = audiofile.analysis.beats

    # This creates a new chunk of audio that is the same size and shape as the input file
    # We can do this because we know that our output will be the same size as our input
    out_shape = (len(audiofile.data),)
    out_data = audio.AudioData(shape=out_shape, numChannels=1, sampleRate=44100)
    
    # This loop pitch-shifts each beat and adds it to the new file!
    for i, beat in enumerate(beats):
        # Pitch shifting only works on the data from each beat, not the beat objet itself
        data = audiofile[beat].data
        # The amount to pitch shift each beat.
        # local_context just returns a tuple the position of a beat within its parent bar.
        # (0, 4) for the first beat of a bar, for example
        number = beat.local_context()[0] % 12
        # Do the shift!
        new_beat = soundtouch.shiftPitchSemiTones(audiofile[beat], number*-1)
        out_data.append(new_beat)
    
    # Write the new file
    out_data.encode(output_filename)

    # The wrapper for the script.  
if __name__ == '__main__':
    import sys
    try:
        # This gets the filenames to read from and write to.
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        # If things go wrong, exit!
        print usage
        sys.exit(-1)
    main(input_filename, output_filename)

########NEW FILE########
__FILENAME__ = cycle_dirac
#!/usr/bin/env python
# encoding: utf-8
"""
cycle.py

Periodically time-compress and timestretch the beats in each measure.
Things start fast and ends slow.
This version uses the dirac timestretching library.  
It is slower than SoundTouch, but is higher quality.

Created by Thor Kell on 2013-05-06, based on code by Ben Lacker.
"""
# Import other things
import math
import os
import sys
# Import the timestretching library.  
import dirac
# This line imports remix! 
from echonest.remix import audio

usage = """
Usage:
    python cycle.py <input_filename> <output_filename>
Exampel:
    python cycle.py CryMeARiver.mp3 CryCycle.mp3
"""

# Cycle timestreches each beat!

# Remix has two timestreching libraries, dirac and SoundTouch.  
# This version uses the dirac timeScale function.
# Dirac is slower, but higher quality.   

# Cycle works by looping over every bar and beat within each bar.
# A stretch ratio is calculate based on what beat and bar it is.
# Then the data is timestretched by this ratio, and added to the output.  

def main(input_filename, output_filename):
    # This takes your input track, sends it to the analyzer, and returns the results.  
    audiofile = audio.LocalAudioFile(input_filename)

    # This gets a list of every bar in the track.  
    bars = audiofile.analysis.bars

    # The output array
    collect = []

    # This loop streches each beat by a varying ratio, and then re-assmbles them.
    for bar in bars:
        # Caculate a stretch ratio that repeats every four bars.
        bar_ratio = (bars.index(bar) % 4) / 2.0
        # Get the beats in the bar
        beats = bar.children()
        for beat in beats:
            # Find out where in the bar the beat is.
            beat_index = beat.local_context()[0]
            # Calculate a stretch ratio based on where in the bar the beat is
            ratio = beat_index / 2.0 + 0.5
            # Note that dirac can't compress by less than 0.5!
            ratio = ratio + bar_ratio 
            # Get the raw audio data from the beat and scale it by the ratio
            # dirac only works on raw data, and only takes floating-point ratios
            beat_audio = beat.render()
            scaled_beat = dirac.timeScale(beat_audio.data, ratio)
            # Create a new AudioData object from the scaled data
            ts = audio.AudioData(ndarray=scaled_beat, shape=scaled_beat.shape, 
                            sampleRate=audiofile.sampleRate, numChannels=scaled_beat.shape[1])
            # Append the new data to the output list!
            collect.append(ts)

    # Assemble and write the output data
    out = audio.assemble(collect, numChannels=2)
    out.encode(output_filename)


    # The wrapper for the script.  
if __name__ == '__main__':
    import sys
    try:
        # This gets the filenames to read from and write to.
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        # If things go wrong, exit!
        print usage
        sys.exit(-1)
    main(input_filename, output_filename)


########NEW FILE########
__FILENAME__ = cycle_soundtouch
#!/usr/bin/env python
# encoding: utf-8
"""
cycle.py

Periodically time-compress and time-stretch the beats in each measure.
Each measure starts fast and ends slow.
This version uses the SoundTouch timestretching library.  
It is faster than dirac, but is lower quality.

Created by Ben Lacker on 2009-06-16.
Refactored by Thor Kell on 2013-03-06.
"""
import math
import os
import sys

from echonest.remix import audio, modify

usage = """
Usage:
    python cycle.py <input_filename> <output_filename>
Exampel:
    python cycle.py CryMeARiver.mp3 CryCycle.mp3
"""

# Cycle timestreches each beat!

# Remix has two timestreching libraries, dirac and SoundTouch.  
# This version uses the SoundTouch timeScale function.
# SoundTouch is faster, but lower quality.   
# Cycle works by looping beat within each bar.
# A stretch ratio is calculate based on what beat it is.
# Then the data is timestretched by this ratio, and added to the output.  

def main(input_filename, output_filename):
    # This takes your input track, sends it to the analyzer, and returns the results.
    audiofile = audio.LocalAudioFile(input_filename)

    # Just a local alias to the soundtouch library, which handles the pitch shifting.
    soundtouch = modify.Modify()

    # This gets a list of every bar in the track.  
    # You can manipulate this just like any other Python list!
    beats = audiofile.analysis.beats

    # The output array
    collect = []

    # This loop streches each beat by a varying ratio, and then re-assmbles them.
    for beat in beats:
        # Find out where in the bar the beat is, and calculate a ratio based on that.
        context = beat.local_context()
        ratio = (math.cos(math.pi * 2 * context[0]/float(context[1])) / 2) + 1
        # Stretch the beat!  SoundTouch returns an AudioData object
        new = soundtouch.shiftTempo(audiofile[beat], ratio)
        # Append the stretched beat to the list of beats
        collect.append(new)
    
    # Assemble and write the output data
    out = audio.assemble(collect)
    out.encode(output_filename)


    # The wrapper for the script.  
if __name__ == '__main__':
    import sys
    try:
        # This gets the filenames to read from and write to.
        input_filename = sys.argv[1]
        output_filename = sys.argv[2]
    except:
        # If things go wrong, exit!
        print usage
        sys.exit(-1)
    main(input_filename, output_filename)

########NEW FILE########
__FILENAME__ = swinger
#!/usr/bin/env python
# encoding: utf=8

"""
swinger.py
(name suggested by Jason Sundram)

Make your music swing (or un-swing).
Created by Tristan Jehan.
"""

# These lines import other things.  
from optparse import OptionParser
import os, sys
import dirac

# These line import specific things from Remix! 
from echonest.remix.audio import LocalAudioFile, AudioData
from echonest.action import render, Playback, display_actions


# Swinger is much more complex than the prior examples!  
# Hold on, and we'll try to make everything make sense
# Swinger returns a swung version of the track.
# That is to say, that every second eighth note in the track is swung:  
# they occur later later than they otherwise would.
# It does this by timestretching the first eighth note to make it longer,
# and by timestretching the second eighth note to make it shorter.

    # This is the function that does the swingin'
def do_work(track, options):
    
    verbose = bool(options.verbose)
    
    # This gets the swing factor
    swing = float(options.swing)
    if swing < -0.9: swing = -0.9
    if swing > +0.9: swing = +0.9
    
    # If there's no swing, return the original tune
    if swing == 0:
        return Playback(track, 0, track.analysis.duration)
    
    # This gets the beat and the where the beats strt
    beats = track.analysis.beats
    offset = int(beats[0].start * track.sampleRate)

    # compute rates
    rates = []
    # This is where the magic happens:
    # For each beat, compute how much to stretch / compress each half of each beat
    for beat in beats[:-1]:
        # This adds swing:
        if 0 < swing:
            rate1 = 1+swing
            dur = beat.duration/2.0
            stretch = dur * rate1
            rate2 = (beat.duration-stretch)/dur
        # This removes swing
        else:
            rate1 = 1 / (1+abs(swing))
            dur = (beat.duration/2.0) / rate1
            stretch = dur * rate1
            rate2 = (beat.duration-stretch)/(beat.duration-dur)
        # This builds the list of swing rates for each beat
        start1 = int(beat.start * track.sampleRate)
        start2 = int((beat.start+dur) * track.sampleRate)
        rates.append((start1-offset, rate1))
        rates.append((start2-offset, rate2))
        if verbose:
            args = (beats.index(beat), dur, beat.duration-dur, stretch, beat.duration-stretch)
            print "Beat %d — split [%.3f|%.3f] — stretch [%.3f|%.3f] seconds" % args
    
    # This gets all the audio, from the
    vecin = track.data[offset:int(beats[-1].start * track.sampleRate),:]
    # This block does the time stretching
    if verbose: 
        print "\nTime stretching..."
    # Dirac is a timestretching tool that comes with remix.
    vecout = dirac.timeScale(vecin, rates, track.sampleRate, 0)
    # This builds the timestretched AudioData object
    ts = AudioData(ndarray=vecout, shape=vecout.shape, 
                    sampleRate=track.sampleRate, numChannels=vecout.shape[1], 
                    verbose=verbose)
     # Create playback objects (just a collection of audio) for the first and last beat
    pb1 = Playback(track, 0, beats[0].start)
    pb2 = Playback(track, beats[-1].start, track.analysis.duration-beats[-1].start)
    
    # Return the first beat, the timestreched beats, and the last beat
    return [pb1, ts, pb2]

    # The main function!
def main():
    # This setups up a parser for the various options
    usage = "usage: %s [options] <one_single_mp3>" % sys.argv[0]
    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--swing", default=0.33, help="swing factor default=0.33")
    parser.add_option("-v", "--verbose", action="store_true", help="show results on screen")
    
    # If we don't have enough options, exit!
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        return -1
    
    # Set up the track and verbose-ness
    verbose = options.verbose
    track = None
    track = LocalAudioFile(args[0], verbose=verbose)
    if verbose:
        print "Computing swing . . ."

    # This is where the work takes place
    actions = do_work(track, options)
    
    if verbose:
        display_actions(actions)
    
    # This renders the audio out to the new file
    name = os.path.splitext(os.path.basename(args[0]))
    sign = ('-','+')[float(options.swing) >= 0]
    name = name[0] + '_swing' + sign + str(int(abs(float(options.swing))*100)) +'.mp3'
    name = name.replace(' ','') 
    name = os.path.join(os.getcwd(), name) # TODO: use sys.path[0] instead of getcwd()?
    
    if verbose:
        print "Rendering... %s" % name
    render(actions, name, verbose=verbose)
    if verbose:
        print "Success!"
    return 1

    # The wrapper for the script.  
if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        print e


########NEW FILE########
__FILENAME__ = waltzify
#!/usr/bin/env python
# encoding: utf=8

"""
waltzify.py

Turn 4/4 music into 3/4
Modified approach suggested by Mary Farbood.
Created by Tristan Jehan.
"""

# These lines import other things.  
import os, sys
import dirac, math
from optparse import OptionParser

# These line import specific things from Remix! 
from echonest.remix.audio import LocalAudioFile, AudioData
from echonest.action import render, Playback, display_actions

# Waltzify is much more complex than the prior examples!  
# Hold on, and we'll try to make everything make sense
# Waltzify changes the meter of a track from 4 to 3.
# It makes it a waltz, basically.  
# It does this by stretching every second beat into two beats!

# This picks a tempo to set each beat to.
def select_tempo(index, num_beats, min_tempo, max_tempo, rate):
    v = math.atan(float(rate)*float(index)/float(num_beats))/1.57
    return min_tempo + v * float(max_tempo-min_tempo)

    # This is the function that does the waltzifying
def do_work(track, options):
    
    # This manages the various input options
    verbose = bool(options.verbose)    
    low_tempo = float(options.low)    
    high_tempo = float(options.high)    
    rate_tempo = float(options.rate)    
    rubato = float(options.rubato)    
    tempo = float(options.tempo)    

    # This set the tempo and applies acceleration or not
    if rate_tempo == 0:
        if tempo == 0:
            low_tempo = track.analysis.tempo['value']
            high_tempo = low_tempo
        else:
            low_tempo = tempo
            high_tempo = tempo
    
    rates = []
    count = min(max(0,int(options.offset)),1)
    beats = track.analysis.beats
    offset = int(beats[0].start * track.sampleRate)

    # For every beat, we get a tempo, and apply a time stretch
    for beat in beats[:-1]:

        # Get a tempo for the beat
        target_tempo = select_tempo(beats.index(beat), len(beats), low_tempo, high_tempo, rate_tempo)

        # Calculate rates for time stretching each beat.
        # 
        if count == 0:
            dur = beat.duration/2.0
            rate1 = 60.0 / (target_tempo * dur)
            stretch = dur * rate1
            rate2 = rate1 + rubato
        elif count == 1:
            rate1 = 60.0 / (target_tempo * beat.duration)

        # Add a change of rate at a given time
        start1 = int(beat.start * track.sampleRate)
        rates.append((start1-offset, rate1))
        if count == 0:
            start2 = int((beat.start+dur) * track.sampleRate)
            rates.append((start2-offset, rate2))

        # This prints what's happening, if verbose mode is on.
        if verbose:
            if count == 0:
                args = (beats.index(beat), count, beat.duration, dur*rate1, dur*rate2, 60.0/(dur*rate1), 60.0/(dur*rate2))
                print "Beat %d (%d) | stretch %.3f sec into [%.3f|%.3f] sec | tempo = [%d|%d] bpm" % args
            elif count == 1:
                args = (beats.index(beat), count, beat.duration, beat.duration*rate1, 60.0/(beat.duration*rate1))
                print "Beat %d (%d) | stretch %.3f sec into %.3f sec | tempo = %d bpm" % args
        
        count = (count + 1) % 2
   
    # This gets the audio
    vecin = track.data[offset:int(beats[-1].start * track.sampleRate),:]

    # This does the time stretch
    if verbose: 
        print "\nTime stretching..."
    # Dirac is a timestretching tool that comes with remix.
    vecout = dirac.timeScale(vecin, rates, track.sampleRate, 0)
    
    # This builds the timestretched AudioData object
    ts = AudioData(ndarray=vecout, shape=vecout.shape, 
                    sampleRate=track.sampleRate, numChannels=vecout.shape[1], 
                    verbose=verbose)
    
    # Create playback objects (just a collection of audio) for the first and last beat
    pb1 = Playback(track, 0, beats[0].start)
    pb2 = Playback(track, beats[-1].start, track.analysis.duration-beats[-1].start)
    
    # Return the first beat, the timestreched beats, and the last beat
    return [pb1, ts, pb2]

    # The main function!
def main():
    # This setups up a parser for the various input options
    usage = "usage: %s [options] <one_single_mp3>" % sys.argv[0]
    parser = OptionParser(usage=usage)
    parser.add_option("-o", "--offset", default=0, help="offset where to start counting")
    parser.add_option("-l", "--low", default=100, help="low tempo")
    parser.add_option("-H", "--high", default=192, help="high tempo")
    parser.add_option("-r", "--rate", default=0, help="acceleration rate (try 30)")
    parser.add_option("-R", "--rubato", default=0, help="rubato on second beat (try 0.2)")
    parser.add_option("-t", "--tempo", default=0, help="target tempo (try 160)")
    parser.add_option("-v", "--verbose", action="store_true", help="show results on screen")
    
    # If we don't have enough options, exit!
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        return -1
    
    verbose = options.verbose

    # This gets the analysis for this file
    track = LocalAudioFile(args[0], verbose=verbose)
    
    if verbose:
        print "Waltzifying..."

    # This is where the work takes place
    actions = do_work(track, options)

    if verbose:
        display_actions(actions)
    
    # This makes the new name for the output file
    name = os.path.splitext(os.path.basename(args[0]))
    name = str(name[0] + '_waltz_%d' % int(options.offset) +'.mp3')
    
    if verbose:
        print "Rendering... %s" % name

    # This renders the audio out to the output file
    render(actions, name, verbose=verbose)
    if verbose:
        print "Success!"
    return 1

    # The wrapper for the script.  
if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        print e


########NEW FILE########
