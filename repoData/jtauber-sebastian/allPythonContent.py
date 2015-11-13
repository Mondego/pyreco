__FILENAME__ = example
#!/usr/bin/env python

from sebastian.lilypond.interp import parse
from sebastian.lilypond.write_lilypond import write
from sebastian.midi import write_midi, player
from sebastian.core import OSequence, HSeq, Point, DURATION_64
from sebastian.core.transforms import transpose, reverse, add, degree_in_key, midi_pitch, lilypond
from sebastian.core.notes import Key, major_scale

# construct sequences using lilypond syntax
seq1 = parse("c d e")
seq2 = parse("e f g")

# concatenate
seq3 = seq1 + seq2

# transpose and reverse
seq4 = seq3 | transpose(12) | reverse()

# merge
seq5 = seq3 // seq4

# play MIDI
player.play([seq5])

# write to MIDI
write_midi.write("seq5.mid", [seq5])

# contruct a horizontal sequence of scale degrees
seq6 = HSeq(Point(degree=degree) for degree in [1, 2, 3, 2, 1])

# put that sequence into C major, octave 4 quavers
C_MAJOR = Key("C", major_scale)
seq7 = seq6 | add({"octave": 4, DURATION_64: 8}) | degree_in_key(C_MAJOR)

# convert to MIDI pitch and play
player.play([OSequence(seq7 | midi_pitch())])


# sequence of first four degree of a scale
seq8 = HSeq(Point(degree=n) for n in [1, 2, 3, 4])

# add duration and octave
seq8 = seq8 | add({DURATION_64: 16, "octave": 5})

# put into C major
seq8 = seq8 | degree_in_key(C_MAJOR)

# annotate with lilypond
seq8 = seq8 | lilypond()

# write out lilypond file
write("example.ly", seq8)

########NEW FILE########
__FILENAME__ = alberti
#!/usr/bin/env python

## this is the beginning of an experiment for the next level of the algebra

from sebastian.core import DURATION_64
from sebastian.core import VSeq, HSeq, Point, OSequence
from sebastian.core.transforms import midi_pitch, degree_in_key_with_octave, add
from sebastian.core.notes import Key, major_scale

from sebastian.midi import write_midi


def alberti(triad):
    """
    takes a VSeq of 3 notes and returns an HSeq of those notes in an
    alberti figuration.
    """
    return HSeq(triad[i] for i in [0, 2, 1, 2])


# an abstract VSeq of 3 notes in root position (degree 1, 3 and 5)
root_triad = VSeq(Point(degree=n) for n in [1, 3, 5])

quaver_point = Point({DURATION_64: 8})

# an OSequence with alberti figuration repeated 16 times using quavers
alberti_osequence = OSequence(alberti(root_triad) * 16 | add(quaver_point))

C_major = Key("C", major_scale)

# note values filled-out for C major in octave 5 then MIDI pitches calculated
seq = alberti_osequence | degree_in_key_with_octave(C_major, 5) | midi_pitch()

# write to file:
write_midi.write("alberti.mid", [seq])

########NEW FILE########
__FILENAME__ = dynamics_example
#!/usr/bin/env python
"""
Generate ode to joy in the entire dynamic range "pppppp" -> "ffff". Also generate a crescendo from "ppp" to "ff" and a dimininuendo from "mf" to "ppp".

This will output numerous midi files, as well as three lilypond (*.ly) files with dynamic notation.
"""

from sebastian.lilypond.interp import parse
from sebastian.core.transforms import dynamics, lilypond, midi_to_pitch, add
from sebastian.midi import write_midi
from sebastian.lilypond import write_lilypond

# construct sequences using lilypond syntax
melody = parse("e4 e f g g f e d c c d e")
A = parse("e4. d8 d2")
Aprime = parse("d4. c8 c2")

two_bars = melody + A + melody + Aprime
two_bars = two_bars | midi_to_pitch()
two_bars = two_bars | add({"octave": 5})

velocities = ["pppppp", "ppppp", "pppp", "ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "ffff"]

for d in velocities:
    two_bars_with_dynamics = two_bars | dynamics(d)
    write_midi.write("ode_%s.mid" % (d,), [two_bars_with_dynamics])

two_bars_ff_lily = two_bars | dynamics("ff") | lilypond()
write_lilypond.write("ode_ff.ly", two_bars_ff_lily)

crescendo = two_bars | dynamics("ppp", "ff")
write_midi.write("ode_crescendo.mid", [crescendo])
write_lilypond.write("ode_crescendo.ly", crescendo | lilypond())

diminuendo = two_bars | dynamics("mf", "pppp")
write_midi.write("ode_diminuendo.mid", [diminuendo])
write_lilypond.write("ode_diminuendo.ly", diminuendo | lilypond())

########NEW FILE########
__FILENAME__ = game_of_thrones
"""
The main title theme to HBO's Game of Thrones by Ramin Djawadi
"""

from sebastian.core import Point, HSeq, OSequence
from sebastian.core.transforms import midi_pitch, degree_in_key, add
from sebastian.core.notes import Key, major_scale, minor_scale
from sebastian.midi import write_midi

C_Major = Key("C", major_scale)
C_minor = Key("C", minor_scale)

motive_degrees = HSeq(Point(degree=n) for n in [5, 1, 3, 4])

motive_rhythm_1 = HSeq(Point(duration_64=n) for n in [16, 16, 8, 8])
motive_rhythm_2 = HSeq(Point(duration_64=n) for n in [48, 48, 8, 8, 32, 32, 8, 8])

motive_1 = motive_degrees & motive_rhythm_1
motive_2 = (motive_degrees * 2) & motive_rhythm_2

# add key and octave
seq1 = (motive_1 * 4) | add({"octave": 5}) | degree_in_key(C_minor)
seq2 = (motive_1 * 4) | add({"octave": 5}) | degree_in_key(C_Major)
seq3 = motive_2 | add({"octave": 4}) | degree_in_key(C_minor)

seq = (seq1 + seq2 + seq3) | midi_pitch() | OSequence

write_midi.write("game_of_thrones.mid", [seq], instruments=[49], tempo=350000)

########NEW FILE########
__FILENAME__ = var1
#!/usr/bin/env python

from sebastian.lilypond.interp import parse
from sebastian.midi.write_midi import SMF

rh = parse(r"""
    \relative c'' {
        g16 fis g8 ~ g16 d16 e fis g a b cis
        d16 cis d8 ~ d16 a16 b cis d e fis d
        g16 fis g8 ~ g16 fis16 e d cis e a, g
        fis e d cis d fis a, g fis a d,8
    }""")

lh = parse(r"""
    \relative c {
        g8 b'16 a b8 g g, g'
        fis,8 fis'16 e fis8 d fis, d'
        e,8 e'16 d e8 g a, cis'
        d, fis16 e fis8 d d,
    }""")

# operator overloading FTW!
seq = rh // lh

if __name__ == "__main__":
    f = open("var1.mid", "w")
    s = SMF([seq])
    s.write(f)
    f.close()

########NEW FILE########
__FILENAME__ = hanon
#!/usr/bin/env python

from sebastian.midi.write_midi import SMF
from sebastian.core import OSequence, DURATION_64
from sebastian.core.notes import Key, major_scale
from sebastian.core.transforms import degree_in_key_with_octave, midi_pitch, transpose


# Hanon 1

up_degrees = [1, 3, 4, 5, 6, 5, 4, 3]
down_degrees = [6, 4, 3, 2, 1, 2, 3, 4]
final_degree = [1]

sections = [
    (up_degrees, 4, range(14)),
    (down_degrees, 4, range(13, -2, -1)),
    (final_degree, 32, range(1)),
]

hanon_1 = OSequence()

for section in sections:
    pattern, duration_64, offset = section
    for o in offset:
        for note in pattern:
            hanon_1.append({"degree": note + o, DURATION_64: duration_64})

hanon_1 = hanon_1 | degree_in_key_with_octave(Key("C", major_scale), 4) | midi_pitch()

hanon_rh_1 = hanon_1
hanon_lh_1 = hanon_1 | transpose(-12)

seq = hanon_lh_1 // hanon_rh_1


if __name__ == "__main__":
    f = open("hanon.mid", "w")
    s = SMF([seq])
    s.write(f)
    f.close()

########NEW FILE########
__FILENAME__ = in_c2midi
#!/usr/bin/env python

import random

from sebastian.lilypond.interp import parse
from sebastian.midi.write_midi import SMF
from sebastian.core import OSequence
from sebastian.core.transforms import transpose


patterns = [
    r"\relative c' { \acciaccatura c8 e4 \acciaccatura c8 e4 \acciaccatura c8 e4 }",  # 1
    r"\relative c' { \acciaccatura c8 e8 f8 e4 }",
    r"\relative c' { r8 e8 f8 e8 }",
    r"\relative c' { r8 e8 f8 g8 }",
    r"\relative c' { e8 f8 g8 r8 }",  # 5
    r"\relative c'' { c1~ c1 }",
    r"\relative c' { r4 r4 r4 r8 c16 c16 c8 r8 r4 r4 r4 r4 }",
    r"\relative c'' { g1. f1~ f1 }",
    r"\relative c'' { b16 g16 r8 r4 r4 r4 }",
    r"\relative c'' { b16 g16 }",  # 10
    r"\relative c' { f16 g16 b16 g16 b16 g16 }",
    r"\relative c' { f8 g8 b1 c4}",
    r"\relative c'' { b16 g8. g16 f16 g8 r8. g16~ g2. }",
    r"\relative c'' { c1 b1 g1 fis1 }",
    r"\relative c'' { g16 r8. r4 r4 r4 }",  # 15
    r"\relative c'' { g16 b16 c16 b16 }",
    r"\relative c'' { b16 c16 b16 c16 b16 r16 }",
    r"\relative c' { e16 fis16 e16 fis16 e8. e16 }",
    r"\relative c'' { r4. g'4. }",
    r"\relative c' { e16 fis16 e16 fis16 g,8. e'16 fis16 e16 fis16 e16 }",  # 20
    r"\relative c' { fis2.}",
    r"\relative c' { e4. e4. e4. e4. e4. fis4. g4. a4. b8 }",
    r"\relative c' { e8 fis4. fis4. fis4. fis4. fis4. g4. a4. b4 }",
    r"\relative c' { e8 fis8 g4. g4. g4. g4. g4. a4. b8 }",
    r"\relative c' { e8 fis8 g8 a4. a4. a4. a4. a4. b4. }",  # 25
    r"\relative c' { e8 fis8 g8 a8 b4. b4. b4. b4. b4. }",
    r"\relative c' { e16 fis16 e16 fis16 g8 e16 g16 fis16 e16 fis16 e16}",
    r"\relative c' { e16 fis16 e16 fis16 e8. e16 }",
    r"\relative c' { e2. g2. c2. }",
    r"\relative c' { c'1. }",  # 30
    r"\relative c'' { g16 f16 g16 b16 g16 b16 }",
    r"\relative c' { f16 g16 f16 g16 b16 f16~ f2. g4. }",
    r"\relative c'' { g16 f16 r8 }",
    r"\relative c'' { g16 f16 }",
    r"\relative c' { f16 g16 b16 g16 b16 g16 b16 g16 b16 g16 r8 r4 r4 r4 bes4 g'2. a8 g8~ g8 b8 a4. g8 e2. g8 fis8~ fis2. r4 r4 r8 e8~ e2 f1. }",  # 35
    r"\relative c' { f16 g16 b16 g16 b16 g16 }",
    r"\relative c' { f16 g16 }",
    r"\relative c' { f16 g16 b16 }",
    r"\relative c'' { b16 g16 f16 g16 b16 c16 }",
    r"\relative c'' { b16 f16 }",  # 40
    r"\relative c'' { b16 g16 }",
    r"\relative c'' { c1 b1 a1 c1 }",
    r"\relative c'' { f16 e16 f16 e16 e8 e8 e8 f16 e16 }",
    r"\relative c'' { f8 e8~ e8 e8 c4 }",
    r"\relative c'' { d4 d4 g,4 }",  # 45
    r"\relative c'' { g16 d'16 e16 d16 r8 g,8 r8 g8 r8 g8 g16 d'16 e16 d16 }",
    r"\relative c'' { d16 e16 d8 }",
    r"\relative c'' { g1. g1 f1~ f4 }",
    r"\relative c' { f16 g16 bes16 g16 bes16 g16 }",
    r"\relative c' { f16 g16 }",  # 50
    r"\relative c' { f16 g16 bes16 }",
    r"\relative c'' { g16 bes16 }",
    r"\relative c'' { bes16 g16 }",
]


# make a separate MIDI file for each pattern

def separate_files():
    for num, pattern in enumerate(patterns):
        sequence = parse(pattern)
        f = open("in_c_%s.mid" % (num + 1), "w")
        s = SMF([sequence])
        s.write(f)
        f.close()


# make a single MIDI file with all the patterns in a row

def one_file():
    seq = OSequence([])
    for num, pattern in enumerate(patterns):
        seq = seq + parse(pattern) * 10
    f = open("in_c_all.mid", "w")
    s = SMF([seq])
    s.write(f)
    f.close()

# performance


def performance():
    tracks = []
    for track_num in range(8):  # 8 tracks
        seq = OSequence([])
        for pattern in patterns:
            seq += parse(pattern) * random.randint(2, 5)  # repeat 2-5 times
        tracks.append(seq | transpose(random.choice([-12, 0, 12])))  # transpose -1, 0 or 1 octaves
    f = open("in_c_performance.mid", "w")
    s = SMF(tracks)
    s.write(f)
    f.close()


performance()

########NEW FILE########
__FILENAME__ = first_movement
"""
This script will build up the first movement of Mozart's C major Sonata (K545)
while trying out experimental features of Sebastian.
"""
from pprint import pprint
from sebastian.core import Point, HSeq, VSeq, OSequence, DURATION_64, DEGREE
from sebastian.core.transforms import midi_pitch, degree_in_key_with_octave, add, transform_sequence
from sebastian.core.notes import Key, major_scale
from sebastian.midi import write_midi


def transpose_degree(point, degree_delta):
    result = Point(point)
    result[DEGREE] = result[DEGREE] + degree_delta
    return result


@transform_sequence
def chord(point):
    children = [transpose_degree(point, i) for i in point.get('chord', (0, 2, 4))]
    point["sequence"] = VSeq(children)
    return point


@transform_sequence
def arpeggio(pattern, point):
    """
    turns each subsequence into an arpeggio matching the given ``pattern``.
    """
    point['sequence'] = HSeq(point['sequence'][i] for i in pattern)
    return point


@transform_sequence
def fill(duration, point):
    """
    fills the subsequence of the point with repetitions of its subsequence and
    sets the ``duration`` of each point.
    """
    point['sequence'] = point['sequence'] * (point[DURATION_64] / (8 * duration)) | add({DURATION_64: duration})
    return point


def expand(sequence):
    """
    expands a tree of sequences into a single, flat sequence, recursively.
    """
    expanse = []
    for point in sequence:
        if 'sequence' in point:
            expanse.extend(expand(point['sequence']))
        else:
            expanse.append(point)
    return sequence.__class__(expanse)


def debug(sequence):
    """
    adds information to the sequence for better debugging, currently only 
    an index property on each point in the sequence.
    """
    points = []
    for i, p in enumerate(sequence):
        copy = Point(p)
        copy['index'] = i
        points.append(copy)
    return sequence.__class__(points)


def build_movement():
    # Define our alberti bass signature.
    alberti = arpeggio([0, 2, 1, 2])

    # Create the basic interval pattern.
    intervals = HSeq({DEGREE: x} for x in [1, 5, 1, 4, 1, 5, 1])

    # Create the rhythm
    rhythm = HSeq({DURATION_64: x} for x in [128, 64, 64, 64, 64, 64, 64])

    # Set specific chords to be used in certain measures.
    intervals[1]["chord"] = (-3, -1, 0, 2)  # second inversion 7th
    intervals[3]["chord"] = (-3, 0, 2)      # second inversion
    intervals[5]["chord"] = (-5, -3, 0)     # first inversion

    # Combine the sequences, make them chords, produce alberti on the chords, 
    # fill with each being 8, expand it to a flat sequence.
    melody = intervals & rhythm | chord() | alberti | fill(8) | expand

    # Define our key
    C_major = Key("C", major_scale)

    #key(major_scale(-2))

    # Set the degree, add the midi pitch, make it an OSequence, add debugging information.
    return melody | degree_in_key_with_octave(C_major, 5) | midi_pitch() | OSequence | debug


if __name__ == "__main__":
    movement = build_movement()
    for point in movement:
        pprint(point)
    write_midi.write("first_movement.mid", [movement])

########NEW FILE########
__FILENAME__ = shortning_bread_1
#!/usr/bin/env python

## this is the beginning of an experiment for the next level of the algebra

from sebastian.core import DURATION_64
from sebastian.core import VSeq, HSeq, Point, OSequence
from sebastian.core.transforms import midi_pitch, degree_in_key_with_octave, add
from sebastian.core.notes import Key, major_scale

from sebastian.midi import write_midi

quaver_point = Point({DURATION_64: 8})
quarter_point = Point({DURATION_64: 16})

# this song uses only these notes
scale = VSeq(Point(degree=n) for n in [1,2,3,5,6,8])

# the following functions all create sequences of eighth notes
def h1(scale):
    return HSeq(scale[i] for i in [5, 4, 3, 4]) | add(quaver_point)

def h1_end1(scale):
    return HSeq(scale[i] for i in [5, 4]) | add(quaver_point) 

def end(scale):
    return HSeq(scale[i] for i in [2, 1]) | add(quaver_point)

def h2(scale):
    return HSeq(scale[i] for i in [0, 4, 3, 4]) | add(quaver_point)

def h2_end1(scale):
    return HSeq(scale[i] for i in [0, 4]) | add(quaver_point)

# there's two important quarter notes used at the ends of sections
e1 = HSeq(scale[3]) | add(quarter_point)
e2 = HSeq(scale[0]) | add(quarter_point)

partA = h1(scale) + h1_end1(scale) + e1 + h1(scale) + end(scale) + e2 
partB = h2(scale) + h2_end1(scale) + e1 + h2(scale) + end(scale) + e2

# here we see the basic structure of the song
oseq = OSequence((partA * 2) + (partB * 2))

C_major = Key("C", major_scale)

# note values filled-out for C major in octave 5 then MIDI pitches calculated
seq = oseq | degree_in_key_with_octave(C_major, 5) | midi_pitch()

# write to file:
write_midi.write("shortning_bread_1.mid", [seq])

########NEW FILE########
__FILENAME__ = shortning_bread_2
#!/usr/bin/env python

## this is the beginning of an experiment for the next level of the algebra

from sebastian.core import DURATION_64
from sebastian.core import VSeq, HSeq, Point, OSequence
from sebastian.core.transforms import midi_pitch, degree_in_key_with_octave, add
from sebastian.core.notes import Key, major_scale

from sebastian.midi import write_midi

# This is an example of another way to create the song 'shortning bread'

quaver_point = Point({DURATION_64: 8})
quarter_point = Point({DURATION_64: 16})

scale = VSeq(Point(degree=n) for n in [1,2,3,5,6,8])

def make_hseq(notes):
    return HSeq(Point(degree=n, duration_64=d) for n, d in notes)

# produces eighth and quarter notes
hlf = 16
qtr = 8 

# tuples specify pitch and duration
p1 = [(8,qtr),(6,qtr),(5,qtr),(6,qtr)]
p2 = [(8,qtr),(6,qtr),(5,hlf)]
p3 = [(3,qtr),(2,qtr),(1,hlf)]
p4 = [(1,qtr),(6,qtr),(5,qtr),(6,qtr)]
p5 = [(1,qtr),(6,qtr),(5,hlf)]

partA = p1 + p2 + p1 + p3
partB = p4 + p5 + p4 + p3
parts = partA + partA + partB + partB

hseq = make_hseq(parts)

oseq = OSequence(hseq)

C_major = Key("C", major_scale)

# note values filled-out for C major in octave 5 then MIDI pitches calculated
seq = oseq | degree_in_key_with_octave(C_major, 5) | midi_pitch()

write_midi.write("shortning_bread_2.mid", [seq])


########NEW FILE########
__FILENAME__ = three_blind_mice
#!/usr/bin/env python

from sebastian.lilypond.interp import parse
from sebastian.midi import write_midi

# construct sequences using lilypond syntax
seq1 = parse("e4. d c r")
seq2 = parse("g4. f4 f8 e4.")
seq2a = parse("r4.")
seq2b = parse("r4 g8")
seq3 = parse("c'4 c'8 b a b c'4 g8 g4")
seq3a = parse("g8")
seq3b = parse("f8")

# concatenate
mice = (seq1 * 2) + (seq2 + seq2a) + (seq2 + seq2b) + ((seq3 + seq3a) * 2) + (seq3 + seq3b) + seq1

# write to MIDI
write_midi.write("mice.mid", [mice])

########NEW FILE########
__FILENAME__ = elements
from collections import Iterable
import tempfile
import subprocess as sp

try:
    from IPython.core.display import Image, SVG
    ipython = True
except ImportError:
    ipython = False

from sebastian.lilypond import write_lilypond


class UnificationError(Exception):
    pass


class Point(dict):

    def unify(self, other):
        new = self.copy()
        for key, value in other.items():
            if key in new:
                if new[key] != value:
                    raise UnificationError(key)
            else:
                new[key] = value
        return Point(new)
    
    def tuple(self, *attributes):
        return tuple(self.get(attribute) for attribute in attributes)
    
    __mod__ = unify


class SeqBase(object):
    
    def __init__(self, *elements):
        if len(elements) == 1:
            if isinstance(elements[0], Point):
                elements = [elements[0]]
            elif isinstance(elements[0], Iterable):
                elements = list(elements[0])
        else:
            elements = list(elements)
        self._elements = []
        
        for point in elements:
            self.append(point)
    
    def __getitem__(self, item):
        return self._elements[item]
    
    def __len__(self):
        return len(self._elements)
    
    def __iter__(self):
        return iter(self._elements)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self._elements == other._elements
    
    def __ne__(self, other):
        return not (isinstance(other, self.__class__) and self._elements == other._elements)
    
    def map_points(self, func):
        return self.__class__([func(point=Point(point)) for point in self._elements])
    
    def transform(self, func):
        """
        applies function to a sequence to produce a new sequence
        """
        return func(self)
    
    def zip(self, other):
        """
        zips two sequences unifying the corresponding points. 
        """
        return self.__class__(p1 % p2 for p1, p2 in zip(self, other))
    
    __or__ = transform
    __and__ = zip
    
    def display(self, format="png"):
        """
        Return an object that can be used to display this sequence.
        This is used for IPython Notebook.

        :param format: "png" or "svg"
        """
        from sebastian.core.transforms import lilypond
        seq = HSeq(self) | lilypond()

        lily_output = write_lilypond.lily_format(seq)
        if not lily_output.strip():
            #In the case of empty lily outputs, return self to get a textual display
            return self

        if format == "png":
            suffix = ".preview.png"
            args = ["lilypond", "--png", "-dno-print-pages", "-dpreview"]
        elif format == "svg":
            suffix = ".preview.svg"
            args = ["lilypond", "-dbackend=svg", "-dno-print-pages", "-dpreview"]

        f = tempfile.NamedTemporaryFile(suffix=suffix)
        basename = f.name[:-len(suffix)]
        args.extend(["-o"+basename, "-"])

        #Pass shell=True so that if your $PATH contains ~ it will
        #get expanded. This also changes the way the arguments get
        #passed in. To work correctly, pass them as a string
        p = sp.Popen(" ".join(args), stdin=sp.PIPE, shell=True)
        stdout, stderr = p.communicate("{ %s }" % lily_output)
        if p.returncode != 0:
            # there was an error
            #raise IOError("Lilypond execution failed: %s%s" % (stdout, stderr))
            return None

        if not ipython:
            return f.read()
        if format == "png":
            return Image(data=f.read(), filename=f.name, format="png")
        else:
            return SVG(data=f.read(), filename=f.name)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._elements)

    def _repr_png_(self):
        f = self.display("png")
        if not isinstance(f, basestring):
            return f.data
        return f

    def _repr_svg_(self):
        f = self.display("svg")
        if not isinstance(f, basestring):
            return f.data
        return f

def OSeq(offset_attr, duration_attr):
    
    class _OSeq(SeqBase):
        
        def last_point(self):
            if len(self._elements) == 0:
                return Point({offset_attr: 0, duration_attr: 0})
            else:
                return sorted(self._elements, key=lambda x: x[offset_attr])[-1]
        
        def next_offset(self):
            point = self.last_point()
            return point[offset_attr] + point.get(duration_attr, 0)
        
        def append(self, point):
            """
            appends a copy of the given point to this sequence, calculating
            the next offset to use for it if it doesn't have one
            """
            point = Point(point)
            if offset_attr not in point:
                point[offset_attr] = self.next_offset()
            self._elements.append(point)
        
        def concatenate(self, next_seq):
            """
            concatenates two sequences to produce a new sequence
            """
            offset = self.next_offset()
            
            new_seq = _OSeq(self._elements)
            for point in next_seq._elements:
                new_point = Point(point)
                new_point[offset_attr] = new_point[offset_attr] + offset
                new_seq._elements.append(new_point)
            return new_seq
        
        def repeat(self, count):
            """
            repeat sequence given number of times to produce a new sequence
            """
            x = _OSeq()
            for i in range(count):
                x = x.concatenate(self)
            return x
        
        def merge(self, parallel_seq):
            """
            combine the points in two sequences, putting them in offset order
            """
            return _OSeq(sorted(self._elements + parallel_seq._elements, key=lambda x: x.get(offset_attr, 0)))

        def subseq(self, start_offset=0, end_offset=None):
            """
            Return a subset of the sequence
            starting at start_offset (defaulting to the beginning)
            ending at end_offset (None representing the end, whih is the default)
            """
            def subseq_iter(start_offset, end_offset):
                for point in self._elements:
                    #Skip until start
                    if point[offset_attr] < start_offset:
                        continue

                    #Yield points start_offset <=  point < end_offset
                    if end_offset is None or point[offset_attr] < end_offset:
                        yield point
                    else:
                        raise StopIteration
            return _OSeq(subseq_iter(start_offset, end_offset))

        __add__ = concatenate
        __mul__ = repeat
        __floordiv__ = merge
    
    return _OSeq


class HSeq(SeqBase):
    """
    a horizontal sequence where each element follows the previous
    """
    
    def append(self, point):
        """
        appends a copy of the given point to this sequence
        """
        point = Point(point)
        self._elements.append(point)
    
    def concatenate(self, next_seq):
        """
        concatenates two sequences to produce a new sequence
        """
        return HSeq(self._elements + next_seq._elements)
    
    def repeat(self, count):
        """
        repeat sequence given number of times to produce a new sequence
        """
        x = HSeq()
        for i in range(count):
            x = x.concatenate(self)
        return x

    def subseq(self, start_offset=0, end_offset=None):
        """
        Return a subset of the sequence
        starting at start_offset (defaulting to the beginning)
        ending at end_offset (None representing the end, whih is the default)
        Raises ValueError if duration_64 is missing on any element
        """
        from sebastian.core import DURATION_64

        def subseq_iter(start_offset, end_offset):
            cur_offset = 0
            for point in self._elements:
                try:
                    cur_offset += point[DURATION_64]
                except KeyError:
                    raise ValueError("HSeq.subseq requires all points to have a %s attribute" % DURATION_64)
                #Skip until start
                if cur_offset < start_offset:
                    continue

                #Yield points start_offset <=  point < end_offset
                if end_offset is None or cur_offset < end_offset:
                    yield point
                else:
                    raise StopIteration
        return HSeq(subseq_iter(start_offset, end_offset))
    
    __add__ = concatenate
    __mul__ = repeat


class VSeq(SeqBase):
    """
    a vertical sequence where each element is coincident with the others
    """
    
    def append(self, point):
        """
        appends a copy of the given point to this sequence
        """
        point = Point(point)
        self._elements.append(point)
    
    def merge(self, parallel_seq):
        """
        combine the points in two sequences
        """
        return VSeq(self._elements + parallel_seq._elements)
    
    __floordiv__ = merge

########NEW FILE########
__FILENAME__ = notes
# line of fifths with D at origin
#
# ... Fbb Cbb Gbb Dbb Abb Ebb Bbb Fb  Cb  Gb  Db  Ab  Eb  Bb  F   C   G   D
#     -17 -16 -15 -14 -13 -12 -11 -10 -9  -8  -7  -6  -5  -4  -3  -2  -1  0
#
# D   A   E   B   F#  C#  G#  D#  A#  E#  B#  Fx  Cx  Gx  Dx  Ax  Ex  Bx  ...
# 0   +1  +2  +3  +4  +5  +6  +7  +8  +9  +10 +11 +12 +13 +14 +15 +16 +17

def natural(val):
    return abs(val) < 4

def single_sharp(val):
    return 3 < val < 11

def single_flat(val):
    return -3 > val > -11

def double_sharp(val):
    return 10 < val < 18

def double_flat(val):
    return -10 > val > -18

def modifiers(val):
    return int(((val + 3) - ((val + 3) % 7)) / 7)

def mod_interval(mod):
    return 7 * mod

def letter(val):
    return "DAEBFCG"[val % 7]

def name(val):
    m = modifiers(val)
    if m == 0:
        m_name = ""
    elif m == 1:
        m_name = "#"
    elif m > 1:
        m_name = "x" * (m - 1)
    else: # m < 0
        m_name = "b" * -m
    return letter(val) + m_name

def value(name):
    letter = name[0]
    base = "FCGDAEB".find(letter) - 3
    if base == -4:
        raise ValueError
    mod = name[1:]
    if mod == "":
        m = 0
    elif mod == "#":
        m = 1
    elif mod == "x" * len(mod):
        m = len(mod) + 1
    elif mod == "b" * len(mod):
        m = -len(mod)
    else:
        raise ValueError
    return base + mod_interval(m)

# tone above, new letter
def tone_above(val): 
    return val + 2

# tone below, new letter
def tone_below(val): 
    return val - 2

# semitone above, new letter
def semitone_above(val): 
    return val - 5

# semitone above, new letter
def semitone_below(val): 
    return val + 5

# semitone above, same letter
def augment(val):
    return val + 7
    
# semitone below, same latter
def diminish(val):
    return val - 7

def enharmonic(val1, val2):
    return (abs(val1 - val2) % 12) == 0

# major scale

def major_scale(tonic):
    return [tonic + i for i in [0, 2, 4, -1, 1, 3, 5]]

def minor_scale(tonic):
    return [tonic + i for i in [0, 2, -3, -1, 1, -4, -2]]


class Key(object):
    def __init__(self, tonic, scale):
        self.notes = scale(value(tonic))
    
    def degree_to_pitch(self, degree):
        return self.notes[degree - 1]
    
    def degree_to_pitch_and_octave(self, degree):
        o, d = divmod(degree - 1, 7)
        return self.notes[d], o

########NEW FILE########
__FILENAME__ = transforms
from sebastian.core import MIDI_PITCH, OFFSET_64, DURATION_64
from sebastian.core import Point, OSequence

from sebastian.core.notes import modifiers, letter
from functools import wraps, partial


def transform_sequence(f):
    """
    A decorator to take a function operating on a point and
    turn it into a function returning a callable operating on a sequence.
    The functions passed to this decorator must define a kwarg called "point",
    or have point be the last positional argument
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        #The arguments here are the arguments passed to the transform,
        #ie, there will be no "point" argument

        #Send a function to seq.map_points with all of its arguments applied except
        #point
        return lambda seq: seq.map_points(partial(f, *args, **kwargs))

    return wrapper


@transform_sequence
def add(properties, point):
    point.update(properties)
    return point


@transform_sequence
def degree_in_key(key, point):
    degree = point["degree"]
    pitch = key.degree_to_pitch(degree)
    point["pitch"] = pitch
    return point


@transform_sequence
def degree_in_key_with_octave(key, base_octave, point):
    degree = point["degree"]
    pitch, octave = key.degree_to_pitch_and_octave(degree)
    point["pitch"] = pitch
    point["octave"] = octave + base_octave
    return point


#TODO: make a converter from semitones, so that you can easily
#transpose by a number of semitones
@transform_sequence
def transpose(interval, point):
    """
    Transpose a point by an interval, using the Sebastian interval system
    """
    if "pitch" in point:
        point["pitch"] = point["pitch"] + interval
    return point


@transform_sequence
def stretch(multiplier, point):
    point[OFFSET_64] = int(point[OFFSET_64] * multiplier)
    if DURATION_64 in point:
        point[DURATION_64] = int(point[DURATION_64] * multiplier)
    return point


@transform_sequence
def invert(midi_pitch_pivot, point):
    if MIDI_PITCH in point:
        interval = point[MIDI_PITCH] - midi_pitch_pivot
        point[MIDI_PITCH] = midi_pitch_pivot - interval
    return point


def reverse():
    def _(sequence):
        new_elements = []
        last_offset = sequence.next_offset()
        if sequence and sequence[0][OFFSET_64] != 0:
            old_sequence = OSequence([Point({OFFSET_64: 0})]) + sequence
        else:
            old_sequence = sequence
        for point in old_sequence:
            new_point = Point(point)
            new_point[OFFSET_64] = last_offset - new_point[OFFSET_64] - new_point.get(DURATION_64, 0)
            if new_point != {OFFSET_64: 0}:
                new_elements.append(new_point)
        return OSequence(sorted(new_elements, key=lambda x: x[OFFSET_64]))
    return _


def subseq(start_offset=0, end_offset=None):
    """
    Return a portion of the input sequence
    """
    def _(sequence):
        return sequence.subseq(start_offset, end_offset)
    return _


@transform_sequence
def midi_pitch(point):
    octave = point["octave"]
    pitch = point["pitch"]
    midi_pitch = [2, 9, 4, 11, 5, 0, 7][pitch % 7]
    midi_pitch += modifiers(pitch)
    midi_pitch += 12 * octave
    point[MIDI_PITCH] = midi_pitch
    return point


@transform_sequence
def midi_to_pitch(point):  # @@@ add key hint later
    if MIDI_PITCH not in point:
        return point
    midi_pitch = point[MIDI_PITCH]

    octave, pitch = divmod(midi_pitch, 12)
    pitch = [-2, 5, 0, -5, 2, -3, 4, -1, 6, 1, -4, 3][pitch]

    point["octave"] = octave
    point["pitch"] = pitch

    return point


@transform_sequence
def lilypond(point):
    """
    Generate lilypond representation for a point
    """
    #If lilypond already computed, leave as is
    if "lilypond" in point:
        return point

    #Defaults:
    pitch_string = ""
    octave_string = ""
    duration_string = ""
    preamble = ""
    dynamic_string = ""
    if "pitch" in point:
        octave = point["octave"]
        pitch = point["pitch"]
        if octave > 4:
            octave_string = "'" * (octave - 4)
        elif octave < 4:
            octave_string = "," * (4 - octave)
        else:
            octave_string = ""
        m = modifiers(pitch)
        if m > 0:
            modifier_string = "is" * m
        elif m < 0:
            modifier_string = "es" * -m
        else:
            modifier_string = ""
        pitch_string = letter(pitch).lower() + modifier_string

    if DURATION_64 in point:
        duration = point[DURATION_64]
        if duration > 0:
            if duration % 3 == 0:  # dotted note
                duration_string = str(192 // (2 * duration)) + "."
            else:
                duration_string = str(64 // duration)
        #TODO: for now, if we have a duration but no pitch, show a 'c' with an x note
        if duration_string:
            if not pitch_string:
                pitch_string = "c"
                octave_string = "'"
                preamble = r'\xNote '

    if "dynamic" in point:
        dynamic = point["dynamic"]
        if dynamic == "crescendo":
            dynamic_string = "\<"
        elif dynamic == "diminuendo":
            dynamic_string = "\>"
        else:
            dynamic_string = "\%s" % (dynamic,)

    point["lilypond"] = "%s%s%s%s%s" % (preamble, pitch_string, octave_string, duration_string, dynamic_string)

    return point

_dynamic_markers_to_velocity = {
    "pppppp": 10,
    "ppppp": 16,
    "pppp": 20,
    "ppp": 24,
    "pp": 36,
    "p": 48,
    "mp": 64,
    "mf": 74,
    "f": 84,
    "ff": 94,
    "fff": 114,
    "ffff": 127,
}


def dynamics(start, end=None):
    """
    Apply dynamics to a sequence. If end is specified, it will crescendo or diminuendo linearly from start to end dynamics.

    You can pass any of these strings as dynamic markers: ['pppppp', 'ppppp', 'pppp', 'ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff', ''ffff]

    Args:
        start: beginning dynamic marker, if no end is specified all notes will get this marker
        end: ending dynamic marker, if unspecified the entire sequence will get the start dynamic marker

    Example usage:

        s1 | dynamics('p')  # play a sequence in piano
        s2 | dynamics('p', 'ff')  # crescendo from p to ff
        s3 | dynamics('ff', 'p')  # diminuendo from ff to p
    """
    def _(sequence):
        if start in _dynamic_markers_to_velocity:
            start_velocity = _dynamic_markers_to_velocity[start]
            start_marker = start
        else:
            raise ValueError("Unknown start dynamic: %s, must be in %s" % (start, _dynamic_markers_to_velocity.keys()))

        if end is None:
            end_velocity = start_velocity
            end_marker = start_marker
        elif end in _dynamic_markers_to_velocity:
            end_velocity = _dynamic_markers_to_velocity[end]
            end_marker = end
        else:
            raise ValueError("Unknown end dynamic: %s, must be in %s" % (start, _dynamic_markers_to_velocity.keys()))

        retval = sequence.__class__([Point(point) for point in sequence._elements])

        velocity_interval = (float(end_velocity) - float(start_velocity)) / (len(retval) - 1) if len(retval) > 1 else 0
        velocities = [int(start_velocity + velocity_interval * pos) for pos in range(len(retval))]

        # insert dynamics markers for lilypond
        if start_velocity > end_velocity:
            retval[0]["dynamic"] = "diminuendo"
            retval[-1]["dynamic"] = end_marker
        elif start_velocity < end_velocity:
            retval[0]["dynamic"] = "crescendo"
            retval[-1]["dynamic"] = end_marker
        else:
            retval[0]["dynamic"] = start_marker

        for point, velocity in zip(retval, velocities):
            point["velocity"] = velocity

        return retval
    return _

########NEW FILE########
__FILENAME__ = interp
from sebastian import logger
from sebastian.core import OSequence, Point, OFFSET_64, MIDI_PITCH, DURATION_64

import re

MIDI_NOTE_VALUES = {
    "c": 0,
    "d": 2,
    "e": 4,
    "f": 5,
    "g": 7,
    "a": 9,
    "b": 11,
}


token_pattern = re.compile(r"""^\s*                 # INITIAL WHITESPACE
    (
        (                                           # NOTE
            (
                (?P<note>[abcdefg])                     # NOTE NAME
                ((?P<sharp>(is)+)|(?P<flat>(es)+)) ?    # ACCIDENTALS ?
                (?P<octave>'+|,+) ?                     # OCTAVE ?
                (=(?P<octave_check>'+|,+)) ?            # OCTAVE CHECK ?
                |                                       # or
                (?P<rest>r)                             # REST
            )
            (?P<duration>\d+\.*) ?                      # DURATION ?
            (\s*(?P<tie>~)) ?                           # TIE ?
        )
        |                                           # or
        \\(?P<command>(                             # COMMANDS
            relative | acciaccatura
        ))
        |                                           # or
        (?P<open_brace>{) | (?P<close_brace>})      # { or }
    )
    """, 
    re.VERBOSE
)


def tokenize(s):
    while True:
        if s:
            m = token_pattern.match(s)
            if m:
                yield m.groupdict()
            else:
                raise Exception("unknown token at: '%s'" % s[:20])
            s = s[m.end():]
        else:
            raise StopIteration


def note_tuple(token_dict, relative_note_tuple=None):
    note = token_dict["note"]
    octave_marker = token_dict["octave"]
    octave_check = token_dict["octave_check"]
    accidental_sharp = token_dict["sharp"]
    accidental_flat = token_dict["flat"]
    accidental_change = 0
    
    if relative_note_tuple:
        prev_note, prev_accidental_change, prev_octave = relative_note_tuple
        
        diff = MIDI_NOTE_VALUES[note] - prev_note
        if diff >= 7:
            base_octave = prev_octave - 1
        elif diff <= -7:
            base_octave = prev_octave + 1
        else:
            base_octave = prev_octave
    else:
        base_octave = 4
    
    if octave_marker is None:
        octave = base_octave
    elif "'" in octave_marker:
        octave = base_octave + len(octave_marker)
    elif "," in octave_marker:
        octave = base_octave - len(octave_marker)
    if accidental_sharp:
        accidental_change += len(accidental_sharp) / 2
    if accidental_flat:
        accidental_change -= len(accidental_flat) / 2
    
    if octave_check is None:
        pass
    elif "'" in octave_check:
        correct_octave = 4 + len(octave_check)
        if octave != correct_octave:
            logger.warn("failed octave check")
            octave = correct_octave
    elif "," in octave_check:
        correct_octave = 4 - len(octave_check)
        if octave != correct_octave:
            logger.warn("failed octave check")
            octave = correct_octave
    
    return MIDI_NOTE_VALUES[note], accidental_change, octave


def parse_duration(duration_marker):
    if "." in duration_marker:
        first_dot = duration_marker.find(".")
        core = int(duration_marker[:first_dot])
        # this doesn't actually check they are all dots, but regex wouldn't
        # match in the first place otherwise
        dots = len(duration_marker[first_dot:])
    else:
        core = int(duration_marker)
        dots = 0
    
    duration = int((2 - (2**-dots)) * 64 / core)
    
    return duration


def process_note(token_dict, relative_mode, prev_note_tuple):
    # @@@ there is still code duplication between here and the main parsing
    # further on
    # @@@ some of the args passed in above could be avoided if this and
    # parse_block were methods on a class
    
    duration_marker = token_dict["duration"]
    # duration must be explicit
    duration = parse_duration(duration_marker)
    
    if relative_mode:
        note_base, accidental_change, octave = note_tuple(token_dict, relative_note_tuple=prev_note_tuple)
    else:
        note_base, accidental_change, octave = note_tuple(token_dict)
    
    note_value = note_base + (12 * octave) + accidental_change
    
    return note_value, duration


def parse_block(token_generator, prev_note_tuple=None, relative_mode=False, offset=0):
    prev_duration = 16
    tie_deferred = False
    
    try:
        while True:
            token_dict = next(token_generator)
            
            command = token_dict["command"]
            open_brace = token_dict["open_brace"]
            close_brace = token_dict["close_brace"]
            
            if command:
                if command == "relative":
                    
                    token_dict = next(token_generator)
                    
                    base_note_tuple = note_tuple(token_dict)
                    
                    token_dict = next(token_generator)
                    if not token_dict["open_brace"]:
                        raise Exception("\\relative must be followed by note then {...} block")
                    
                    for obj in parse_block(token_generator, prev_note_tuple=base_note_tuple, relative_mode=True, offset=offset):
                        yield obj
                        last_offset = obj[OFFSET_64]
                    offset = last_offset
                elif command == "acciaccatura":
                    # @@@ there is much code duplication between here and the
                    # main parsing further on
                    
                    token_dict = next(token_generator)
                    note_value, duration = process_note(token_dict, relative_mode, prev_note_tuple)
                    yield Point({OFFSET_64: offset - duration / 2, MIDI_PITCH: note_value, DURATION_64: duration / 2})
                    
                    token_dict = next(token_generator)
                    note_value, duration = process_note(token_dict, relative_mode, prev_note_tuple)
                    yield Point({OFFSET_64: offset, MIDI_PITCH: note_value, DURATION_64: duration})
                    
                    offset += duration
                    prev_duration = duration
                    
                    # @@@ this should be uncommented but I'll wait until a
                    # unit test proves it should be uncommented!
                    # prev_note_tuple = note_base, accidental_change, octave
                    
            elif open_brace:
                for obj in parse_block(token_generator):
                    yield obj
            elif close_brace:
                raise StopIteration
            else:
                duration_marker = token_dict["duration"]
                rest = token_dict["rest"]
                tie = token_dict["tie"]
                
                if duration_marker is None:
                    duration = prev_duration
                else:
                    duration = parse_duration(duration_marker)
                
                if not rest:
                    if relative_mode:
                        note_base, accidental_change, octave = note_tuple(token_dict, relative_note_tuple=prev_note_tuple)
                    else:
                        note_base, accidental_change, octave = note_tuple(token_dict)
                    note_value = note_base + (12 * octave) + accidental_change
                    
                    if tie_deferred:
                        # if the previous note was deferred due to a tie
                        prev_note_value = prev_note_tuple[0] + (12 * prev_note_tuple[2]) + prev_note_tuple[1]
                        if note_value != prev_note_value:
                            raise Exception("ties are only supported between notes of same pitch")
                        duration += prev_duration
                        tie_deferred = False
                    
                    if tie:
                        # if there is a tie following this note, we defer it
                        tie_deferred = True
                    else:
                        yield Point({OFFSET_64: offset, MIDI_PITCH: note_value, DURATION_64: duration})
                    
                    prev_note_tuple = note_base, accidental_change, octave
                
                if not tie_deferred:
                    offset += duration
                
                prev_duration = duration
    except StopIteration:
        yield Point({OFFSET_64: offset})
        raise StopIteration


def parse(s, offset=0):
    return OSequence(list(parse_block(tokenize(s), offset=offset)))

########NEW FILE########
__FILENAME__ = write_lilypond
def lily_format(seq):
    return " ".join(point["lilypond"] for point in seq)


def output(seq):
    return "{ %s }" % lily_format(seq)


def write(filename, seq):
    with open(filename, "w") as f:
        f.write(output(seq))

########NEW FILE########
__FILENAME__ = midi
#!/usr/bin/env python

"""
A library for parsing Standard MIDI Files (SMFs).

Currently it just outputs the data it finds.
"""

from sebastian.core import OSequence, Point, OFFSET_64, MIDI_PITCH, DURATION_64


class Base(object):
    """
    Base is a generic base class for parsing binary files. It cannot be
    instantiated directly, you need to sub-class it and implement a parse()
    method.
    
    Your sub-class can then be instantiated with a single argument, a byte
    array.
    
    Base provides a number of basic methods for pulling data out of the byte
    array and incrementing the index appropriately.
    """
    
    def __init__(self, data, handler):
        self.data = data
        self.handler = handler
        self.index = 0
        self.init()
        self.parse()
    
    def init(self):
        pass

    def peek_byte(self):
        return self.data[self.index]
    
    def get_byte(self):
        data = self.data[self.index]
        self.index += 1
        return data
    
    def get_char(self, length=1):
        data = self.data[self.index:self.index + length]
        self.index += length
        return data
    
    def get_ushort(self):
        data = 0
        data += self.get_byte() << 8
        data += self.get_byte() << 0
        return data
    
    def get_ulong(self):
        data = 0
        data += self.get_byte() << 24
        data += self.get_byte() << 16
        data += self.get_byte() << 8
        data += self.get_byte() << 0
        return data
    
    def get_varlen(self):
        data = 0
        while True:
            next = self.get_byte()
            high_bit = next // 0x80
            data = (data << 7) + (next % 0x80)
            if not high_bit:
                return data


class SMF(Base):
    """
    A parser for Simple MIDI files.
    """
    
    def parse_chunk(self):
        chunk_id = self.get_char(4)
        length = self.get_ulong()
        data = self.get_char(length)
        return chunk_id, data
    
    def parse(self):
        while self.index < len(self.data):
            chunk_id, data = self.parse_chunk()
            if chunk_id == b"MThd":
                Thd(data, self.handler)
            elif chunk_id == b"MTrk":
                Trk(data, self.handler)
            else:
                raise Exception("unknown chunk type")


class Thd(Base):
    """
    A parser for the Thd chunk in a MIDI file.
    """
    
    def parse(self):
        format = self.get_ushort()
        num_tracks = self.get_ushort()
        division = self.get_ushort()
        self.handler.header(format, num_tracks, division)


class Trk(Base):
    """
    A parser for the Trk chunk in a MIDI file.
    """
    
    def init(self):
        self.note_started = {}

    def process_event(self, time_delta, status):
        if status == 0xFF:
            status2 = self.get_byte()
            varlen2 = self.get_varlen()
            data = self.get_char(varlen2)
            if status2 == 0x01:
                self.handler.text_event(data)
            elif status2 == 0x03:
                self.handler.track_name(data)
            elif status2 == 0x04:
                self.handler.instrument(data)
            elif status2 == 0x2F:
                assert varlen2 == 0, varlen2
                self.track_end = True
                self.handler.track_end()
            elif status2 == 0x51:
                assert varlen2 == 3, varlen2
                self.handler.tempo(data[0], data[1], data[2])
            elif status2 == 0x54:
                assert varlen2 == 5, varlen2
                self.handler.smpte(data[0], data[1], data[2], data[3], data[4])
            elif status2 == 0x58:
                assert varlen2 == 4, varlen2
                self.handler.time_signature(data[0], data[1], data[2], data[3])
            elif status2 == 0x59:
                assert varlen2 == 2, varlen2
                self.handler.key_signature(data[0], data[1])  # @@@ first arg signed?
            else:
                raise Exception("unknown metaevent status " + hex(status2))
        elif 0x80 <= status <= 0xEF:
            event_type, channel = divmod(status, 0x10)
            if event_type == 0x8:  # note off
                note_number = self.get_byte()
                velocity = self.get_byte()
                self.ticks += time_delta
                if note_number not in self.note_started:
                    # note was never started so ignore
                    pass
                else:
                    start_ticks, start_velocity = self.note_started.pop(note_number)
                    duration = self.ticks - start_ticks
                self.handler.note(start_ticks, channel + 1, note_number, duration)
            elif event_type == 0x9:  # note on
                note_number = self.get_byte()
                velocity = self.get_byte()
                self.ticks += time_delta
                
                if velocity > 0:
                    if note_number in self.note_started:
                        # new note at that pitch started before previous finished
                        # not sure it should happen but let's handle it anyway
                        start_ticks, start_velocity = self.note_started.pop(note_number)
                        duration = self.ticks - start_ticks
                        self.handler.note(start_ticks, channel + 1, note_number, duration)
                    self.note_started[note_number] = self.ticks, velocity
                else:  # note end
                    if note_number not in self.note_started:
                        # note was never started so ignore
                        pass
                    else:
                        start_ticks, start_velocity = self.note_started.pop(note_number)
                        duration = self.ticks - start_ticks
                    self.handler.note(start_ticks, channel + 1, note_number, duration)

                self.current_note = (channel + 1, note_number, self.ticks)
            elif event_type == 0xB:  # controller
                controller = self.get_byte()
                value = self.get_byte()
                self.handler.controller(time_delta, channel + 1, controller, value)
            elif event_type == 0xC:  # program change
                program = self.get_byte()
                self.handler.program_change(time_delta, channel + 1, program)
            else:
                raise Exception("unknown event type " + hex(event_type))
        else:
            raise Exception("unknown status " + hex(status))
    
    def parse(self):
        self.ticks = 0
        self.next_note = 0
        global track
        track += 1
        self.handler.track_start(track)
        self.track_end = False
        while self.index < len(self.data):
            if self.track_end:
                raise Exception("more data after track end")
            time_delta = self.get_varlen()
            next_byte = self.peek_byte()
            if next_byte >= 0x80:
                status = self.get_byte()
                self.process_event(time_delta, status)
            else:  # running status
                self.process_event(time_delta, status)  # previous status
        if not self.track_end:
            raise Exception("no track end")


class BaseHandler(object):
    
    def header(self, format, num_tracks, division):
        pass

    def text_event(self, text):
        pass

    def track_name(self, name):
        pass

    def instrument(self, name):
        pass

    def track_start(self, track_num):
        pass

    def track_end(self):
        pass

    def tempo(self, t1, t2, t3):
        pass

    def smpte(self, s1, s2, s3, s4, s5):
        pass

    def time_signature(self, t1, t2, t3, t4):
        pass

    def key_signature(self, k1, k2):
        pass

    def controller(self, time_delta, channel, controller, value):
        pass

    def program_change(self, time_delta, channel, program):
        pass

    def note(self, offset, channel, midi_pitch, duration):
        pass


class PrintHandler(BaseHandler):
    
    def header(self, format, num_tracks, division):
        print("Thd %d %d %d" % (format, num_tracks, division))

    def text_event(self, text):
        print("text event '%s'" % text)

    def track_name(self, name):
        print("sequence/track name '%s'" % name)

    def instrument(self, name):
        print("instrument '%s'" % name)

    def track_start(self, track_num):
        print("track start %d" % track_num)

    def track_end(self):
        print("track end")

    def tempo(self, t1, t2, t3):
        print("tempo %d %d %d" % (t1, t2, t3))

    def smpte(self, s1, s2, s3, s4, s5):
        print("smpte %d %d %d %d %d" % (s1, s2, s3, s4, s5))

    def time_signature(self, t1, t2, t3, t4):
        print("time signature %d %d %d %d" % (t1, t2, t3, t4))

    def key_signature(self, k1, k2):
        print("key signature %d %d" % (k1, k2))  # @@@ first arg signed?

    def controller(self, time_delta, channel, controller, value):
        print("controller %d %d %d %d" % (time_delta, channel, controller, value))

    def program_change(self, time_delta, channel, program):
        print("program change %d %d %d" % (time_delta, channel, program))

    def note(self, offset, channel, midi_pitch, duration):
        print("note %d %d %d %d" % (offset, channel, midi_pitch, duration))


class SebastianHandler(BaseHandler):

    def header(self, format, num_tracks, division):
        self.division = division
        self.tracks = [None] * num_tracks

    def track_start(self, track_num):
        self.current_sequence = OSequence()
        self.tracks[track_num] = self.current_sequence

    def note(self, offset, channel, midi_pitch, duration):
        offset_64 = 16 * offset // self.division
        duration_64 = 16 * duration // self.division
        point = Point({OFFSET_64: offset_64, MIDI_PITCH: midi_pitch, DURATION_64: duration_64})
        self.current_sequence.append(point)


def load_midi(filename):
    global track
    track = -1
    handler = SebastianHandler()
    SMF(bytearray(open(filename, "rb").read()), handler)
    return handler.tracks


if __name__ == "__main__":
    track = -1
    import sys
    filename = sys.argv[1]
    handler = SebastianHandler()
    SMF(bytearray(open(filename, "rb").read()), handler)

########NEW FILE########
__FILENAME__ = player
## The goal of this module is to eventually be to MIDI players what
## 'webbrowser' is to Web browsers.

import sys
import tempfile
import subprocess

from sebastian.midi import write_midi

OPEN = "open"
TIMIDITY = "timidity"


def play(tracks, program=""):
    f = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
    s = write_midi.SMF(tracks)
    s.write(f)
    f.close()
    if not program:
        if sys.platform == "darwin":
            program = OPEN
        elif sys.platform == "linux2":
            program = TIMIDITY
    if program:
        subprocess.call([program, f.name])
    else:
        print("A suitable program for your platform is unknown")

########NEW FILE########
__FILENAME__ = write_midi
#!/usr/bin/env python

from io import BytesIO
import six

from sebastian.core import OSequence, Point, OFFSET_64, MIDI_PITCH, DURATION_64


def write_chars(out, chars):
    out.write(chars.encode('ascii'))


def write_byte(out, b):
    out.write(six.int2byte(b))


def write_ushort(out, s):
    write_byte(out, (s >> 8) % 256)
    write_byte(out, (s >> 0) % 256)


def write_ulong(out, l):
    write_byte(out, (l >> 24) % 256)
    write_byte(out, (l >> 16) % 256)
    write_byte(out, (l >> 8) % 256)
    write_byte(out, (l >> 0) % 256)


def write_varlen(out, n):
    data = six.int2byte(n & 0x7F)
    while True:
        n = n >> 7
        if n:
            data = six.int2byte((n & 0x7F) | 0x80) + data
        else:
            break
    out.write(data)


class SMF(object):
    
    def __init__(self, tracks, instruments = None):
        self.tracks = tracks

        # instruments are specified per track, 0-127.
        if instruments is None:
            # default to every track uses inst. 0 (piano?)
            instruments = [0]*len(tracks)
        assert len(instruments) == len(tracks)
        self.instruments = instruments 
        
    def write(self
            , out
            , title = "untitled" # distinct from filename
            , time_signature = (4, 2, 24, 8) # (2nd arg is power of 2) 
            , key_signature = (0, 0) # C
            , tempo = 500000 # in microseconds per quarter note
        ):
        num_tracks = 1 + len(self.tracks)
        Thd(format=1, num_tracks=num_tracks, division=16).write(out)
        T = 1  # how to translate events times into time_delta using the
               # division above
        
        # first track will just contain time/key/tempo info
        t = Trk()
        
        t0, t1, t2, t3 = time_signature
        t.time_signature(t0, t1, t2, t3) 
        k0, k1 = key_signature
        t.key_signature(k0, k1)  
        t.tempo(tempo)  
        t.sequence_track_name(title)
        
        t.track_end()
        t.write(out)
       
        # each track is written to it's own channel
        for channel, track in enumerate(self.tracks):
            t = Trk()
           
            # set other track attributes here
            #t.instrument('my instrument')

            # set the instrument this channel is set for 
            t.program_change(channel, self.instruments[channel])

            # we make a list of events including note off events so we can sort by
            # offset including them (to avoid negative time deltas)
            # @@@ this may eventually be a feature of sequences rather than this
            # MIDI library
            
            events_with_noteoff = []
            for point in track:
                offset, note_value, duration = point.tuple(OFFSET_64, MIDI_PITCH, DURATION_64)
                velocity = 64 if 'velocity' not in point else point['velocity']
                if note_value is not None:
                    events_with_noteoff.append((True, offset, note_value, velocity))
                    events_with_noteoff.append((False, offset + duration, note_value, velocity))
            
            prev_offset = None
            for on, offset, note_value, velocity in sorted(events_with_noteoff, key=lambda x: x[1]):
                if prev_offset is None:
                    time_delta = 0
                else:
                    time_delta = (offset - prev_offset) * T
                if on:
                    t.start_note(time_delta, channel, note_value, velocity)
                else:
                    t.end_note(time_delta, channel, note_value)
                prev_offset = offset
                
            t.track_end()
            t.write(out)


class Thd(object):
    
    def __init__(self, format, num_tracks, division):
        self.format = format
        self.num_tracks = num_tracks
        self.division = division
        
    def write(self, out):
        write_chars(out, "MThd")
        write_ulong(out, 6)
        write_ushort(out, self.format)
        write_ushort(out, self.num_tracks)
        write_ushort(out, self.division)


class Trk(object):
    
    def __init__(self):
        self.data = BytesIO()
   
    def write_meta_info(self, byte1, byte2, data): 
        "Worker method for writing meta info"
        write_varlen(self.data, 0)  # tick
        write_byte(self.data, byte1)
        write_byte(self.data, byte2)
        write_varlen(self.data, len(data))
        write_chars(self.data, data)

    def instrument(self, inst):
        "This works, but does not affect the 'instrument' used."
        self.write_meta_info(0xFF, 0x04, inst)

    def program_name(self, name):
        self.write_meta_info(0xFF, 0x08, name)

    def sequence_track_name(self, name):
        self.write_meta_info(0xFF, 0x03, name)
    
    def time_signature(self, a, b, c, d):
        write_varlen(self.data, 0)  # tick
        write_byte(self.data, 0xFF)
        write_byte(self.data, 0x58)
        write_varlen(self.data, 4)
        write_byte(self.data, a)
        write_byte(self.data, b)
        write_byte(self.data, c)
        write_byte(self.data, d)
    
    def key_signature(self, a, b):
        write_varlen(self.data, 0)  # tick
        write_byte(self.data, 0xFF)
        write_byte(self.data, 0x59)
        write_varlen(self.data, 2)
        write_byte(self.data, a)
        write_byte(self.data, b)
    
    def tempo(self, t):
        write_varlen(self.data, 0)  # tick
        write_byte(self.data, 0xFF)
        write_byte(self.data, 0x51)
        write_varlen(self.data, 3)
        write_byte(self.data, (t >> 16) % 256)
        write_byte(self.data, (t >> 8) % 256)
        write_byte(self.data, (t >> 0) % 256)
    
    def program_change(self, channel, program):
        write_varlen(self.data, 0) # tick
        write_byte(self.data, 0xC0 + channel) 
        write_byte(self.data, program)
        
    def start_note(self, time_delta, channel, note_number, velocity=64):
        write_varlen(self.data, time_delta)
        write_byte(self.data, 0x90 + channel)
        write_byte(self.data, note_number)
        write_byte(self.data, max(min(velocity, 255), 0))  # velocity
    
    def end_note(self, time_delta, channel, note_number):
        write_varlen(self.data, time_delta)
        write_byte(self.data, 0x80 + channel)
        write_byte(self.data, note_number)
        write_byte(self.data, 0)  # velocity
    
    def track_end(self):
        write_varlen(self.data, 0)  # tick
        write_byte(self.data, 0xFF)
        write_byte(self.data, 0x2F)
        write_varlen(self.data, 0)
    
    def write(self, out):
        write_chars(out, "MTrk")
        d = self.data.getvalue()
        write_ulong(out, len(d))
        out.write(d)


def write(filename, tracks, instruments = None, **kws):
    with open(filename, "w") as f:
        s = SMF(tracks, instruments = instruments)
        # pass on some attributes, such as tempo, key, etc.
        s.write(f, **kws)

########NEW FILE########
__FILENAME__ = test_lilypond
from unittest import TestCase

## graded tests derived from lilypond documentation that are likely to be
## relevant to In C implementation

from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64, HSeq
from sebastian.core.transforms import add, lilypond
from sebastian.lilypond.interp import parse
from sebastian.lilypond.write_lilypond import output, write


class TestLilyPondParsing(TestCase):

    def eq(self, lilypond, answer):
        """ The first is a lilypond fragment. The second is
        the intended interpretation, a sequence of (offset, pitch, duration) tuples
        where offset and duration are in multiples of a 64th note and pitch is MIDI
        note number.
        """
        result = parse(lilypond)
        self.assertEqual(len(answer), len(result))
        for i, event in enumerate(answer):
            r = result[i].tuple(OFFSET_64, MIDI_PITCH, DURATION_64)
            self.assertEqual(event, r)

    def test_absolute_octave_entry(self):
        self.eq(
            "c d e f g a b c d e f g",
            [
                (0, 48, 16), (16, 50, 16), (32, 52, 16), (48, 53, 16),
                (64, 55, 16), (80, 57, 16), (96, 59, 16), (112, 48, 16),
                (128, 50, 16), (144, 52, 16), (160, 53, 16), (176, 55, 16),
                (192, None, None)
            ]
        )

        self.eq(
            "c' c'' e' g d'' d' d c c, c,, e, g d,, d, d c",
            [
                (0, 60, 16), (16, 72, 16), (32, 64, 16), (48, 55, 16),
                (64, 74, 16), (80, 62, 16), (96, 50, 16), (112, 48, 16),
                (128, 36, 16), (144, 24, 16), (160, 40, 16), (176, 55, 16),
                (192, 26, 16), (208, 38, 16), (224, 50, 16), (240, 48, 16),
                (256, None, None),
            ]
        )

    def test_duration(self):
        self.eq(
            "a a a2 a a4 a a1 a",
            [
                (0, 57, 16), (16, 57, 16), (32, 57, 32), (64, 57, 32),
                (96, 57, 16), (112, 57, 16), (128, 57, 64), (192, 57, 64),
                (256, None, None),
            ]
        )

    def test_more_durations(self):
        self.eq(
            "a4 b c4. b8 a4. b4.. c8.",
            [
                (0, 57, 16), (16, 59, 16), (32, 48, 24), (56, 59, 8),
                (64, 57, 24), (88, 59, 28), (116, 48, 12),
                (128, None, None),
            ]
        )

    def test_rests(self):

        self.eq(
            "c4 r4 r8 c8 c4",
            [
                (0, 48, 16), (40, 48, 8), (48, 48, 16),
                (64, None, None),
            ]
        )

        self.eq(
            "r8 c d e",
            [
                (8, 48, 8), (16, 50, 8), (24, 52, 8),
                (32, None, None),
            ]
        )

    def test_accidentals(self):
        self.eq(
            "ais1 aes aisis aeses",
            [
                (0, 58, 64), (64, 56, 64), (128, 59, 64), (192, 55, 64),
                (256, None, None),
            ]
        )

        self.eq(
            "a4 aes a2",
            [
                (0, 57, 16), (16, 56, 16), (32, 57, 32),
                (64, None, None),
            ]
        )

    def test_relative_octave_entry(self):

        self.eq(
            r"\relative c { c d e f g a b c d e f g }",
            [
                (0, 48, 16), (16, 50, 16), (32, 52, 16), (48, 53, 16),
                (64, 55, 16), (80, 57, 16), (96, 59, 16), (112, 60, 16),
                (128, 62, 16), (144, 64, 16), (160, 65, 16), (176, 67, 16),
                (192, None, None),
                (192, None, None),
            ]
        )

        self.eq(
            r"\relative c'' { c g c f, c' a, e'' c }",
            [
                (0, 72, 16), (16, 67, 16), (32, 72, 16), (48, 65, 16),
                (64, 72, 16), (80, 57, 16), (96, 76, 16), (112, 72, 16),
                (128, None, None),
                (128, None, None),
            ]
        )

        self.eq(
            r"\relative c { c f b e a d g c }",
            [
                (0, 48, 16), (16, 53, 16), (32, 59, 16), (48, 64, 16),
                (64, 69, 16), (80, 74, 16), (96, 79, 16), (112, 84, 16),
                (128, None, None),
                (128, None, None),
            ]
        )

        self.eq(
            r"\relative c'' { c2 fis c2 ges b2 eisis b2 feses }",
            [
                (0, 72, 32), (32, 78, 32), (64, 72, 32), (96, 66, 32),
                (128, 71, 32), (160, 78, 32), (192, 71, 32), (224, 63, 32),
                (256, None, None),
                (256, None, None),
            ]
        )

    def test_ties(self):
        self.eq(
            "a2 ~ a",
            [
                (0, 57, 64),
                (64, None, None),
            ]
        )

    def test_octave_check(self):
        import logging
        logging.disable(logging.WARN)
        self.eq(
            r"\relative c'' { c2 d='4 d e2 f }",
            [
                (0, 72, 32), (32, 62, 16), (48, 62, 16), (64, 64, 32), (96, 65, 32),
                (128, None, None),
                (128, None, None),
            ]
        )
        logging.disable(logging.NOTSET)

    def test_acciaccatura(self):
        self.eq(
            r"\acciaccatura d8 c4",
            [
                (-4, 50, 4), (0, 48, 16),
                (16, None, None),
            ]
        )

    def test_for_regression_of_a_bug_in_ordering_of_accidental_and_octave(self):
        self.eq(
            "fis'",
            [
                (0, 66, 16),
                (16, None, None),
            ]
        )


class TestLilyPondWriting(TestCase):

    def test_output(self):
        pitches = HSeq({"pitch": n} for n in [-2, 0, 2, -3])
        seq = pitches | add({"octave": 5, DURATION_64: 16}) | lilypond()
        self.assertEqual(output(seq), "{ c'4 d'4 e'4 f'4 }")

    def test_write(self):
        import tempfile
        pitches = HSeq({"pitch": n} for n in [-2, 0, 2, -3])
        seq = pitches | add({"octave": 5, DURATION_64: 16}) | lilypond()
        f = tempfile.NamedTemporaryFile(suffix=".ly", delete=False)
        write(f.name, seq)
        with open(f.name) as g:
            self.assertEqual(g.read(), "{ c'4 d'4 e'4 f'4 }")


class TestLilyPondDisplay(TestCase):

    def test_display_skipped_on_empty(self):
        """
        If all lilypond output is empty,
        ensure we don't call lilypond
        """
        empty = HSeq({"fake": n} for n in range(2))
        seq = empty | lilypond()
        displayed = seq.display()
        self.assertTrue(isinstance(displayed, HSeq))

########NEW FILE########
__FILENAME__ = test_midi
from unittest import TestCase

from sebastian.midi.midi import load_midi


class TestMidi(TestCase):

    def test_load_midi(self):
        import os.path
        filename = os.path.join(os.path.dirname(__file__), "scale.mid")
        self.assertEqual(
            list(load_midi(filename)[0]),
            [
                {'midi_pitch': 60, 'offset_64': 42, 'duration_64': 15},
                {'midi_pitch': 62, 'offset_64': 56, 'duration_64': 7},
                {'midi_pitch': 64, 'offset_64': 63, 'duration_64': 6},
                {'midi_pitch': 65, 'offset_64': 70, 'duration_64': 6},
                {'midi_pitch': 67, 'offset_64': 77, 'duration_64': 5},
                {'midi_pitch': 69, 'offset_64': 84, 'duration_64': 5},
                {'midi_pitch': 71, 'offset_64': 91, 'duration_64': 6},
                {'midi_pitch': 72, 'offset_64': 98, 'duration_64': 14},
                {'midi_pitch': 71, 'offset_64': 113, 'duration_64': 6},
                {'midi_pitch': 69, 'offset_64': 120, 'duration_64': 7},
                {'midi_pitch': 67, 'offset_64': 127, 'duration_64': 6},
                {'midi_pitch': 65, 'offset_64': 134, 'duration_64': 5},
                {'midi_pitch': 64, 'offset_64': 141, 'duration_64': 4},
                {'midi_pitch': 62, 'offset_64': 147, 'duration_64': 4},
                {'midi_pitch': 60, 'offset_64': 154, 'duration_64': 13},
            ]
        )

########NEW FILE########
__FILENAME__ = test_notes
from unittest import TestCase


class TestNotes(TestCase):

    def test_natural_values(self):
        from sebastian.core.notes import natural
        assert natural(-3)
        assert natural(2)
        assert natural(0)
        assert not natural(-4)
        assert not natural(5)

    def test_single_sharp(self):
        from sebastian.core.notes import single_sharp
        assert not single_sharp(0)
        assert not single_sharp(-5)
        assert single_sharp(4)
        assert not single_sharp(12)

    def test_modifiers(self):
        from sebastian.core.notes import modifiers
        assert modifiers(0) == 0
        assert modifiers(2) == 0
        assert modifiers(-1) == 0
        assert modifiers(-5) == -1
        assert modifiers(-11) == -2
        assert modifiers(-17) == -2
        assert modifiers(4) == 1
        assert modifiers(13) == 2
        assert modifiers(17) == 2

    def test_note_value(self):
        from sebastian.core.notes import value
        assert value("G#") == 6

    def test_note_names(self):
        from sebastian.core.notes import major_scale, value, name
        gsharp_major_names = [name(x) for x in major_scale(value("G#"))]
        assert gsharp_major_names == ['G#', 'A#', 'B#', 'C#', 'D#', 'E#', 'Fx']

########NEW FILE########
__FILENAME__ = test_point
from unittest import TestCase


class TestPoint(TestCase):

    def make_point(self):
        from sebastian.core import Point
        from sebastian.core import OFFSET_64, DURATION_64, MIDI_PITCH
        retval = Point({
            OFFSET_64: 16,
            MIDI_PITCH: 50,
            DURATION_64: 17,
        })
        return retval

    def test_point_tuple_arbitrary_data(self):
        """
        Ensure points can handle arbitrary data
        """
        from sebastian.core import Point
        p1 = Point(a=1, b="foo")

        self.assertEqual(p1.tuple("b", "a"), ("foo", 1))

    def test_point_equality(self):
        """
        Ensure equals works on points
        """
        from sebastian.core import Point
        p1 = Point(a=1, b="foo")
        p2 = Point(a=1, b="foo")

        self.assertEqual(p1, p2)

    def test_point_inequality(self):
        """
        Ensure not equals works on points
        """
        from sebastian.core import Point
        p1 = Point(a=1, b="foo")
        p2 = Point(a=1, b="foo", c=3)

        self.assertNotEqual(p1, p2)

    def test_point_unification(self):
        """
        Ensure point unification works happy path
        """
        from sebastian.core import Point
        p1 = Point(a=1, b="foo")
        p2 = Point(c=3)

        unified = p1 % p2
        self.assertEqual(Point(a=1, b="foo", c=3), unified)

    def test_unification_error(self):
        """
        Ensure invalid unifications make an error
        """
        from sebastian.core import Point
        from sebastian.core.elements import UnificationError
        p1 = Point(a=1, b="foo")
        p2 = Point(a=2, b="foo")
        try:
            p1 % p2
            self.assertTrue(False)
        except UnificationError:
            self.assertTrue(True)

    def test_reflexive_unification(self):
        """
        Ensure reflexive unification is a noop
        """
        from sebastian.core import Point
        p1 = Point(a=1, b="foo")
        p2 = Point(a=1, b="foo")
        unified = p1 % p2

        self.assertEqual(p1, unified)

    def test_point_tuple(self):
        """
        Ensure Point.tuple works in the nominal case
        """
        p1 = self.make_point()
        from sebastian.core import OFFSET_64, DURATION_64
        self.assertEqual(p1.tuple(OFFSET_64, DURATION_64), (16, 17))

    def test_point_tuple_empty(self):
        """
        Ensure Point.tuple works when passed no arguments
        """
        p1 = self.make_point()
        self.assertEqual(p1.tuple(), ())

    def test_point_flags_valid(self):
        """
        Ensure that OFFSET_64, DURATION_64, and MIDI_PITCH are not equal
        """
        import sebastian.core
        self.assertNotEqual(sebastian.core.OFFSET_64, sebastian.core.DURATION_64)
        self.assertNotEqual(sebastian.core.OFFSET_64, sebastian.core.MIDI_PITCH)
        self.assertNotEqual(sebastian.core.DURATION_64, sebastian.core.MIDI_PITCH)

    def test_point_flags_hashable(self):
        """
        Ensure the constant flags are hashable - by asserting their value
        """
        from sebastian.core import OFFSET_64, DURATION_64, MIDI_PITCH, DEGREE
        self.assertEqual(OFFSET_64, OFFSET_64)
        self.assertEqual(DURATION_64, DURATION_64)
        self.assertEqual(MIDI_PITCH, MIDI_PITCH)
        self.assertEqual(DEGREE, "degree")

########NEW FILE########
__FILENAME__ = test_sequences
from unittest import TestCase


class TestSequences(TestCase):

    def make_point(self, offset=0):
        from sebastian.core import Point
        from sebastian.core import OFFSET_64, DURATION_64, MIDI_PITCH
        retval = Point({
            OFFSET_64: 16 + offset,
            MIDI_PITCH: 50 + offset,
            DURATION_64: 17 + offset,
        })
        return retval

    def make_sequence(self, offset=0):
        points = [self.make_point(offset), self.make_point(offset + 3)]
        from sebastian.core import OSequence
        return OSequence(points)

    def test_make_sequence(self):
        """
        Ensure sequences are composed of notes in the correct order
        """
        p1 = self.make_point()
        p2 = self.make_point(offset=50)  # we need to dedupe somehow
        from sebastian.core import OSequence
        from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64
        sequence = OSequence([p1, p2])
        self.assertEqual(sequence._elements, [
            {DURATION_64: 17, OFFSET_64: 16, MIDI_PITCH: 50},
            {DURATION_64: 17 + 50, OFFSET_64: 16 + 50, MIDI_PITCH: 50 + 50}
        ])

    def test_sequence_ctors(self):
        """
        Ensure the various sequence ctors work ok
        """
        from sebastian.core import OSeq, Point
        OffsetSequence = OSeq("offset", "duration")

        p1 = Point(a=3, b="foo")
        p2 = Point(c=5)
        s2 = OffsetSequence([p1, p2])
        s3 = OffsetSequence(p1, p2)
        s4 = OffsetSequence(p1) + OffsetSequence(p2)
        self.assertEqual(s2, s3)
        self.assertEqual(s3, s4)
        self.assertEqual(s2, s4)

    def test_sequence_duration_and_offset_with_append(self):
        """
        Ensure sequences calculate durations correctly on append
        """
        from sebastian.core import OSeq, Point
        OffsetSequence = OSeq("offset", "duration")

        s1 = OffsetSequence()
        s1.append(Point(duration=10))
        s1.append(Point(duration=10))
        self.assertEqual(20, s1.next_offset())
        for point, offset in zip(s1, [0, 10]):
            self.assertEqual(point['offset'], offset)

    def test_vseq_doesnt_track_duration_on_append(self):
        """
        Ensure vseq dont do offset modification
        """
        from sebastian.core import VSeq, Point
        s1 = VSeq()
        s1.append(Point(duration=10))
        s1.append(Point(duration=10))
        for point in s1:
            self.assertTrue('offset' not in point)

    def test_hseq_doesnt_track_duration_on_append(self):
        """
        Ensure hseq doesnt do offset modification
        """
        from sebastian.core import HSeq, Point
        s1 = HSeq()
        s1.append(Point(duration=10))
        s1.append(Point(duration=10))
        for point in s1:
            self.assertTrue('offset' not in point)

    def test_sequence_last_point(self):
        """
        Ensure that OSequence.last_point returns the highest offset note
        """
        points = [self.make_point(offset=x) for x in range(100, -1, -10)]
        from sebastian.core import OSequence
        from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64
        sequence = OSequence(points)
        self.assertEqual(sequence.last_point(), {
            DURATION_64: 17 + 100, OFFSET_64: 16 + 100, MIDI_PITCH: 50 + 100
        })

    def test_sequence_last_point_empty(self):
        """
        Ensure OSequence.last_point doesn't barf when the sequence is empty
        """
        from sebastian.core import OSequence
        from sebastian.core import OFFSET_64, DURATION_64
        sequence = OSequence([])
        self.assertEqual(sequence.last_point(), {
            DURATION_64: 0, OFFSET_64: 0
        })

    def test_sequence_reflexive_concat(self):
        """
        Ensure sequences can concatenate reflexively
        """
        #from sebastian.core import OFFSET_64, DURATION_64, MIDI_PITCH
        s1 = self.make_sequence()
        concated = s1 + s1
        from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64
        self.assertEqual(concated._elements, [
            {MIDI_PITCH: 50, OFFSET_64: 16, DURATION_64: 17},
            {MIDI_PITCH: 53, OFFSET_64: 19, DURATION_64: 20},
            {MIDI_PITCH: 50, OFFSET_64: 55, DURATION_64: 17},
            {MIDI_PITCH: 53, OFFSET_64: 58, DURATION_64: 20}
        ])

    def test_hseq_concat(self):
        """
        Ensure hseq can concatenate
        """
        from sebastian.core import HSeq
        from sebastian.core import MIDI_PITCH
        s1 = HSeq([
            {MIDI_PITCH: 50},
            {MIDI_PITCH: 51},
        ])
        s2 = HSeq([
            {MIDI_PITCH: 60},
            {MIDI_PITCH: 59},
        ])

        expected = HSeq([
            {MIDI_PITCH: 50},
            {MIDI_PITCH: 51},
            {MIDI_PITCH: 60},
            {MIDI_PITCH: 59},
        ])

        self.assertEqual(expected, s1 + s2)

    def test_sequence_concat(self):
        """
        Ensure sequences can concatenate
        """
        s1 = self.make_sequence()
        s2 = self.make_sequence(offset=50)
        concated = s1 + s2
        from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64
        self.assertEqual(concated._elements, [
            {MIDI_PITCH: 50, OFFSET_64: 16, DURATION_64: 17},
            {MIDI_PITCH: 53, OFFSET_64: 19, DURATION_64: 20},
            {MIDI_PITCH: 100, OFFSET_64: 105, DURATION_64: 67},
            {MIDI_PITCH: 103, OFFSET_64: 108, DURATION_64: 70}
        ])

    def test_sequence_repeats(self):
        """
        Ensure sequences can be repeated
        """
        s1 = self.make_sequence()
        repeat = s1 * 2
        from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64
        self.assertEqual(repeat._elements, [
            {MIDI_PITCH: 50, OFFSET_64: 16, DURATION_64: 17},
            {MIDI_PITCH: 53, OFFSET_64: 19, DURATION_64: 20},
            {MIDI_PITCH: 50, OFFSET_64: 55, DURATION_64: 17},
            {MIDI_PITCH: 53, OFFSET_64: 58, DURATION_64: 20}
        ])

    def test_hseq_repeats(self):
        from sebastian.core import HSeq
        from sebastian.core import MIDI_PITCH
        s1 = HSeq([
            {MIDI_PITCH: 50},
            {MIDI_PITCH: 51},
        ])

        expected = HSeq([
            {MIDI_PITCH: 50},
            {MIDI_PITCH: 51},
            {MIDI_PITCH: 50},
            {MIDI_PITCH: 51},
        ])

        self.assertEqual(expected, s1 * 2)

    def test_sequence_ctor_with_merge(self):
        """
        Ensure sequences can be made from merged sequences.
        """
        from sebastian.core import OSeq, Point
        OffsetSequence = OSeq("offset", "duration")

        s1 = OffsetSequence(Point(a=1, offset=0), Point(a=2, offset=20)) // OffsetSequence(Point(a=3, offset=10))

        self.assertEqual(s1._elements[1]["a"], 3)

    def test_sequence_map(self):
        """
        Ensure map_points applys the function
        """
        from sebastian.core import HSeq, Point

        s1 = (HSeq(Point(a=3, c=5)) +
              HSeq([Point(d=x) for x in range(10)]) +
              HSeq(Point(a=5)))

        def double_a(point):
            if 'a' in point:
                point['a'] *= 2
            return point

        s2 = s1.map_points(double_a)

        self.assertEqual(s2[0]['a'], 6)
        self.assertEqual(s2[-1]['a'], 10)

    def test_sequence_repeats_more(self):
        """
        Ensure MOAR repetition works
        """
        s1 = self.make_sequence()
        repeat = s1 * 3

        from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64
        self.assertEqual(repeat._elements, [
            {MIDI_PITCH: 50, OFFSET_64: 16, DURATION_64: 17},
            {MIDI_PITCH: 53, OFFSET_64: 19, DURATION_64: 20},
            {MIDI_PITCH: 50, OFFSET_64: 55, DURATION_64: 17},
            {MIDI_PITCH: 53, OFFSET_64: 58, DURATION_64: 20},
            {MIDI_PITCH: 50, OFFSET_64: 94, DURATION_64: 17},
            {MIDI_PITCH: 53, OFFSET_64: 97, DURATION_64: 20}
        ])

    def test_sequence_merge(self):
        """
        Ensure two sequences can be merged into one sequence
        """
        s1 = self.make_sequence()
        s2 = self.make_sequence(offset=1)

        merged = s1 // s2
        from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64
        self.assertTrue(merged._elements, [
            {MIDI_PITCH: 50, OFFSET_64: 16, DURATION_64: 17},
            {MIDI_PITCH: 51, OFFSET_64: 17, DURATION_64: 18},
            {MIDI_PITCH: 53, OFFSET_64: 19, DURATION_64: 20},
            {MIDI_PITCH: 54, OFFSET_64: 20, DURATION_64: 21}
        ])

    def test_vseq_merge(self):
        from sebastian.core import VSeq
        from sebastian.core import MIDI_PITCH, OFFSET_64
        s1 = VSeq([
            {MIDI_PITCH: 50, OFFSET_64: 3},
            {MIDI_PITCH: 51, OFFSET_64: 3},
        ])
        s2 = VSeq([
            {MIDI_PITCH: 60, OFFSET_64: 3},
            {MIDI_PITCH: 59, OFFSET_64: 3},
        ])

        expected = VSeq([
            {MIDI_PITCH: 50, OFFSET_64: 3},
            {MIDI_PITCH: 51, OFFSET_64: 3},
            {MIDI_PITCH: 60, OFFSET_64: 3},
            {MIDI_PITCH: 59, OFFSET_64: 3},
        ])

        self.assertEqual(expected, s1 // s2)

    def test_empty_sequence_merge(self):
        """
        Ensure that an empty sequence merge is an identity operation
        """
        s1 = self.make_sequence()
        from sebastian.core import OSequence
        s2 = OSequence([])
        merged = s1 // s2
        from sebastian.core import OFFSET_64, DURATION_64, MIDI_PITCH
        self.assertEqual(merged._elements, [
            {MIDI_PITCH: 50, OFFSET_64: 16, DURATION_64: 17},
            {MIDI_PITCH: 53, OFFSET_64: 19, DURATION_64: 20}
        ])

    def test_basic_sequence_zip(self):
        """
        Ensure that two sequences can be zipped together, unifying its points.
        """
        from sebastian.core import HSeq
        from sebastian.core import MIDI_PITCH, DURATION_64
        s1 = HSeq([
            {MIDI_PITCH: 50},
            {MIDI_PITCH: 51},
            {MIDI_PITCH: 53},
            {MIDI_PITCH: 54}
        ])
        s2 = HSeq([
            {DURATION_64: 17},
            {DURATION_64: 18},
            {DURATION_64: 20},
            {DURATION_64: 21}
        ])

        s_zipped = s1 & s2
        self.assertEqual(s_zipped, HSeq([
            {MIDI_PITCH: 50, DURATION_64: 17},
            {MIDI_PITCH: 51, DURATION_64: 18},
            {MIDI_PITCH: 53, DURATION_64: 20},
            {MIDI_PITCH: 54, DURATION_64: 21}
        ]))

    def test_oseq_subseq_both_args(self):
        """
        Verify _oseq subseq works correctly
        """
        from sebastian.core import OSeq, Point
        OffsetSequence = OSeq("offset", "duration")

        s1 = OffsetSequence(
            Point(a=2, offset=0),
            Point(a=2, offset=20),
            Point(a=2, offset=25),
            Point(a=2, offset=30),
            Point(a=2, offset=50),
        )
        s2 = s1.subseq(20,50)
        self.assertEqual(
            s2,
            OffsetSequence(
                Point(a=2, offset=20),
                Point(a=2, offset=25),
                Point(a=2, offset=30),
            )
        )

    def test_oseq_subseq_start_args(self):
        """
        Verify _oseq subseq works correctly with just the start arg
        """
        from sebastian.core import OSeq, Point
        OffsetSequence = OSeq("offset", "duration")

        s1 = OffsetSequence(
            Point(a=2, offset=0),
            Point(a=2, offset=20),
            Point(a=2, offset=25),
            Point(a=2, offset=30),
            Point(a=2, offset=50),
        )
        s2 = s1.subseq(30)
        self.assertEqual(
            s2,
            OffsetSequence(
                Point(a=2, offset=30),
                Point(a=2, offset=50),
            )
        )

    def test_oseq_subseq_stop_args(self):
        """
        Verify _oseq subseq works correctly with just the stop arg
        """
        from sebastian.core import OSeq, Point
        OffsetSequence = OSeq("offset", "duration")

        s1 = OffsetSequence(
            Point(a=2, offset=0),
            Point(a=2, offset=20),
            Point(a=2, offset=25),
            Point(a=2, offset=30),
            Point(a=2, offset=50),
        )
        s2 = s1.subseq(end_offset=25)
        self.assertEqual(
            s2,
            OffsetSequence(
                Point(a=2, offset=0),
                Point(a=2, offset=20),
            )
        )

    def test_hseq_subseq(self):
        """
        Ensure that two sequences can be zipped together, unifying its points.
        """
        from sebastian.core import HSeq
        from sebastian.core import MIDI_PITCH, DURATION_64
        s1 = HSeq([
            {MIDI_PITCH: 50, DURATION_64: 10},
            {MIDI_PITCH: 51, DURATION_64: 10},
            {MIDI_PITCH: 52, DURATION_64: 10},
            {MIDI_PITCH: 53, DURATION_64: 10}
        ])

        s2 = s1.subseq(20,40)
        self.assertEqual(s2, HSeq([
            {MIDI_PITCH: 51, DURATION_64: 10},
            {MIDI_PITCH: 52, DURATION_64: 10},
        ]))

########NEW FILE########
__FILENAME__ = test_transforms
from unittest import TestCase


class TestTransforms(TestCase):

    def make_point(self, offset=0):
        from sebastian.core import Point
        from sebastian.core import OFFSET_64, DURATION_64
        retval = Point({
            OFFSET_64: 16 + offset,
            "pitch": 50 + offset,
            DURATION_64: 17 + offset,
        })
        return retval

    def make_sequence(self, offset=0):
        points = [self.make_point(offset), self.make_point(offset + 3)]
        from sebastian.core import OSequence
        return OSequence(points)

    def test_transpose(self):
        """
        Ensure transpose modifies the pitch
        """
        from sebastian.core.transforms import transpose
        s1 = self.make_sequence()
        transposed = s1 | transpose(12)
        from sebastian.core import OFFSET_64, DURATION_64

        self.assertEqual(transposed._elements, [
            {"pitch": 62, OFFSET_64: 16, DURATION_64: 17},
            {"pitch": 65, OFFSET_64: 19, DURATION_64: 20}
        ])

    def test_transponse_reversable(self):
        """
        Ensure that transpose is reversable
        """
        from sebastian.core.transforms import transpose
        s1 = self.make_sequence()
        transposed = s1 | transpose(5) | transpose(-5)
        self.assertEqual(s1, transposed)

    def test_reverse(self):
        """
        Ensure puts points in a sequence backwards
        """
        from sebastian.core.transforms import reverse
        s1 = self.make_sequence()
        reversed = s1 | reverse()
        from sebastian.core import OFFSET_64, DURATION_64

        self.assertEqual(reversed._elements, [
            {"pitch": 53, OFFSET_64: 0, DURATION_64: 20},
            {"pitch": 50, OFFSET_64: 6, DURATION_64: 17},
            {OFFSET_64: 39}
        ])

    def test_reversed_doesnt_modify_next_offset(self):
        """
        Ensure reversed sequences are the same length as their input
        """
        from sebastian.core.transforms import reverse
        s1 = self.make_sequence()
        reversed = s1 | reverse()
        self.assertEqual(s1.next_offset(), reversed.next_offset())

    def test_reverse_is_reversable(self):
        """
        Ensure that a double reverse of a sequence is idempotent
        """
        from sebastian.core.transforms import reverse
        s1 = self.make_sequence()
        reversed = s1 | reverse() | reverse()
        self.assertEqual(s1._elements, reversed._elements)

    def test_stretch(self):
        """
        Ensure that strech modifies a simple sequence
        """
        from sebastian.core.transforms import stretch
        s1 = self.make_sequence()
        streched = s1 | stretch(2)

        from sebastian.core import OFFSET_64, DURATION_64
        self.assertEqual(streched._elements, [
            {"pitch": 50, OFFSET_64: 32, DURATION_64: 34},
            {"pitch": 53, OFFSET_64: 38, DURATION_64: 40}
        ])

    def test_strech_is_reversable(self):
        """
        Ensure that stretch and contract is an identity operation
        """
        from sebastian.core.transforms import stretch
        s1 = self.make_sequence()
        stretched = s1 | stretch(2) | stretch(0.5)
        self.assertEqual(s1._elements, stretched._elements)

    def test_dynamics(self):
        from sebastian.core.transforms import dynamics
        s1 = self.make_sequence()
        dynamiced = s1 | dynamics("ff")
        self.assertEqual([p.tuple("velocity") for p in dynamiced], [(94,), (94,)])

    def test_all_dynamic_markers(self):
        from sebastian.core.transforms import dynamics
        s1 = self.make_sequence()
        velocities = ["pppppp", "ppppp", "pppp", "ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "ffff"]
        for velocity in velocities:
            dynamiced = s1 | dynamics(velocity)
            self.assertTrue("velocity" in dynamiced[0])

    def test_dynamics_linear_crecendo(self):
        from sebastian.core.transforms import dynamics
        s1 = self.make_sequence()
        s1 = s1 * 5
        velocitied = s1 | dynamics("ppp", "fff")
        self.assertEqual([p["velocity"] for p in velocitied], [24, 34, 44, 54, 64, 74, 84, 94, 104, 114])

    ## TODO: inversion tests don't make sense yet, since inversion
    ## will be rewritten
    # def test_invert_flips_a_sequence(self):
    #     """
    #     Ensure inverting a sequence modifies the pitch
    #     """
    #     from sebastian.core.transforms import invert
    #     s1 = self.make_sequence()
    #     inverted = s1 | invert(50)

    #     from sebastian.core import OFFSET_64, DURATION_64, MIDI_PITCH
    #     self.assertEqual(inverted._elements, [
    #         {MIDI_PITCH: 50, OFFSET_64: 16, DURATION_64: 17},
    #         {MIDI_PITCH: 47, OFFSET_64: 19, DURATION_64: 20}
    #     ])

    # def test_invert_is_reversable(self):
    #     """
    #     Ensure reversing twice generates the same sequence
    #     """
    #     from sebastian.core.transforms import invert
    #     s1 = self.make_sequence()
    #     inverted = s1 | invert(50) | invert(50)

    #     self.assertEqual(inverted._elements, s1._elements)

    def make_notes(self):
        return [1, 2, 3, 1]

    def make_horizontal_sequence(self):
        from sebastian.core import HSeq, Point
        return HSeq([Point(degree=degree) for degree in self.make_notes()])

    def test_hseq_list(self):
        """
        Ensure list of hseq returns reasonable results
        """
        h1 = self.make_horizontal_sequence()

        for point, degree in zip(list(h1), self.make_notes()):
            self.assertEqual(point, {'degree': degree})

    def test_add_transformation(self):
        """
        Ensure adding properties modifies the points
        """
        from sebastian.core.transforms import add
        h1 = self.make_horizontal_sequence()
        from sebastian.core import DURATION_64

        added = h1 | add({'octave': 4, DURATION_64: 8})

        expected = [{'degree': degree, DURATION_64: 8, 'octave': 4} for degree in self.make_notes()]

        self.assertEqual(list(added), expected)

    def test_degree_in_key(self):
        """
        Ensure that it plays in G major.
        """
        from sebastian.core.transforms import degree_in_key
        from sebastian.core.notes import Key, major_scale
        h1 = self.make_horizontal_sequence()
        keyed = h1 | degree_in_key(Key("G", major_scale))

        self.assertEqual(keyed._elements, [
            {'degree': 1, 'pitch': -1},
            {'degree': 2, 'pitch': 1},
            {'degree': 3, 'pitch': 3},
            {'degree': 1, 'pitch': -1},
        ])

    def test_degree_in_key_with_octave(self):
        """
        Ensure that degree in key with octave is sane
        """
        from sebastian.core.transforms import degree_in_key_with_octave
        from sebastian.core.notes import Key, major_scale

        h1 = self.make_horizontal_sequence()
        keyed = h1 | degree_in_key_with_octave(Key("C", major_scale), 4)

        self.assertEqual(keyed._elements, [
            {'degree': 1, 'octave': 4, 'pitch': -2},
            {'degree': 2, 'octave': 4, 'pitch': 0},
            {'degree': 3, 'octave': 4, 'pitch': 2},
            {'degree': 1, 'octave': 4, 'pitch': -2}
        ])

    def test_play_notes_in_midi_pitches(self):
        """
        Ensure that it plays in G major.
        """
        from sebastian.core.transforms import degree_in_key, midi_pitch, add
        from sebastian.core.notes import Key, major_scale
        from sebastian.core import MIDI_PITCH, DURATION_64
        h1 = self.make_horizontal_sequence()
        keyed = h1 | degree_in_key(Key("G", major_scale))
        positioned = keyed | add({'octave': 4, DURATION_64: 8})
        pitched = positioned | midi_pitch()

        self.assertEqual(pitched._elements, [
            {'degree': 1, 'pitch': -1, DURATION_64: 8, MIDI_PITCH: 55, 'octave': 4},
            {'degree': 2, 'pitch': 1, DURATION_64: 8, MIDI_PITCH: 57, 'octave': 4},
            {'degree': 3, 'pitch': 3, DURATION_64: 8, MIDI_PITCH: 59, 'octave': 4},
            {'degree': 1, 'pitch': -1, DURATION_64: 8, MIDI_PITCH: 55, 'octave': 4},
        ])

    def test_lilypond_transform(self):
        """
        Ensure that it plays in G major.
        """
        from sebastian.core.transforms import midi_pitch, add, lilypond
        from sebastian.core import DURATION_64
        from sebastian.core import HSeq, Point
        h1 = HSeq([Point(pitch=pitch) for pitch in [0, 1, 2, 3, 4, 11, -4, -11]])
        positioned = h1 | add({'octave': 4, DURATION_64: 8})
        pitched = positioned | midi_pitch()
        pitched[3]['octave'] = 5
        pitched[4]['octave'] = 3
        lilyed = pitched | lilypond()

        import pprint
        pprint.pprint(list(lilyed))

        self.assertEqual(lilyed._elements, [
            {'duration_64': 8,
                'lilypond': 'd8',
                'midi_pitch': 50,
                'octave': 4,
                'pitch': 0},
            {'duration_64': 8,
                'lilypond': 'a8',
                'midi_pitch': 57,
                'octave': 4,
                'pitch': 1},
            {'duration_64': 8,
                'lilypond': 'e8',
                'midi_pitch': 52,
                'octave': 4,
                'pitch': 2},
            {'duration_64': 8,
                'lilypond': "b'8",
                'midi_pitch': 59,
                'octave': 5,
                'pitch': 3},
            {'duration_64': 8,
                'lilypond': 'fis,8',
                'midi_pitch': 54,
                'octave': 3,
                'pitch': 4},
            {'duration_64': 8,
                'lilypond': 'fisis8',
                'midi_pitch': 55,
                'octave': 4,
                'pitch': 11},
            {'duration_64': 8,
                'lilypond': 'bes8',
                'midi_pitch': 58,
                'octave': 4,
                'pitch': -4},
            {'duration_64': 8,
                'lilypond': 'beses8',
                'midi_pitch': 57,
                'octave': 4,
                'pitch': -11}
        ])

    def test_lilypond_transform_rhythms(self):
        """
        Ensure points without pitches can render to lilypond
        """
        from sebastian.core.transforms import lilypond
        from sebastian.core import DURATION_64
        from sebastian.core import HSeq, Point
        h1 = HSeq([
            Point({DURATION_64: 64}),
            Point({DURATION_64: 0}),
            Point()
        ])
        h2 = h1 | lilypond()
        self.assertEqual(h2._elements[0]['lilypond'], r"\xNote c'1")
        self.assertEqual(h2._elements[1]['lilypond'], '')
        self.assertEqual(h2._elements[2]['lilypond'], '')

    def test_subseq(self):
        from sebastian.core.transforms import subseq
        from sebastian.core import OSeq, Point
        OffsetSequence = OSeq("offset", "duration")

        s1 = OffsetSequence(
            Point(a=2, offset=0),
            Point(a=2, offset=20),
            Point(a=2, offset=25),
            Point(a=2, offset=30),
            Point(a=2, offset=50),
        )
        s2 = s1 | subseq(20, 30)
        self.assertEqual(
            s2,
            OffsetSequence(
                Point(a=2, offset=20),
                Point(a=2, offset=25)
            )
        )

########NEW FILE########
__FILENAME__ = test_write_midi
from unittest import TestCase


class TestWriteMidi(TestCase):

    def test_write_midi(self):
        """
        Writing out test.mid to ensure midi processing works.

        This isn't really a test.
        """

        from sebastian.core import OSequence, Point
        from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64
        test = OSequence([
            Point({OFFSET_64: o, MIDI_PITCH: m, DURATION_64: d}) for (o, m, d) in [
                (0, 60, 16), (16, 72, 16), (32, 64, 16), (48, 55, 16),
                (64, 74, 16), (80, 62, 16), (96, 50, 16), (112, 48, 16),
                (128, 36, 16), (144, 24, 16), (160, 40, 16), (176, 55, 16),
                (192, 26, 16), (208, 38, 16), (224, 50, 16), (240, 48, 16)
            ]
        ])

        from sebastian.midi.write_midi import SMF
        from io import BytesIO
        out_fd = BytesIO(bytearray())

        expected_bytes = b'MThd\x00\x00\x00\x06\x00\x01\x00\x02\x00\x10MTrk\x00\x00\x00%\x00\xffX\x04\x04\x02\x18\x08\x00\xffY\x02\x00\x00\x00\xffQ\x03\x07\xa1 \x00\xff\x03\x08untitled\x00\xff/\x00MTrk\x00\x00\x00\x87\x00\xc0\x00\x00\x90<@\x10\x80<\x00\x00\x90H@\x10\x80H\x00\x00\x90@@\x10\x80@\x00\x00\x907@\x10\x807\x00\x00\x90J@\x10\x80J\x00\x00\x90>@\x10\x80>\x00\x00\x902@\x10\x802\x00\x00\x900@\x10\x800\x00\x00\x90$@\x10\x80$\x00\x00\x90\x18@\x10\x80\x18\x00\x00\x90(@\x10\x80(\x00\x00\x907@\x10\x807\x00\x00\x90\x1a@\x10\x80\x1a\x00\x00\x90&@\x10\x80&\x00\x00\x902@\x10\x802\x00\x00\x900@\x10\x800\x00\x00\xff/\x00'

        s = SMF([test], instruments=None)
        s.write(out_fd)
        actual_bytes = out_fd.getvalue()

        self.assertEqual(expected_bytes, actual_bytes)

    def test_write_midi_multi_tacks(self):
        """
        Writing out test.mid to ensure midi processing works.

        This isn't really a test.
        """
        from sebastian.core import OSequence, Point
        from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64
        test1 = OSequence([
            Point({OFFSET_64: o, MIDI_PITCH: m, DURATION_64: d}) for (o, m, d) in [
                (0, 60, 16), (16, 72, 16), (32, 64, 16), (48, 55, 16),
            ]
        ])
        test2 = OSequence([
            Point({OFFSET_64: o, MIDI_PITCH: m, DURATION_64: d}) for (o, m, d) in [
                (0, 55, 16), (16, 55, 16), (32, 64, 16), (48 + 16, 55, 16 * 10),
            ]
        ])

        from sebastian.midi.write_midi import SMF
        from io import BytesIO
        out_fd = BytesIO(bytearray())

        expected_bytes = b"""MThd\x00\x00\x00\x06\x00\x01\x00\x03\x00\x10MTrk\x00\x00\x00&\x00\xffX\x04\x04\x02\x18\x08\x00\xffY\x02\x00\x00\x00\xffQ\x03\x07\xa1 \x00\xff\x03\ttest song\x00\xff/\x00MTrk\x00\x00\x00'\x00\xc0\x00\x00\x90<@\x10\x80<\x00\x00\x90H@\x10\x80H\x00\x00\x90@@\x10\x80@\x00\x00\x907@\x10\x807\x00\x00\xff/\x00MTrk\x00\x00\x00(\x00\xc1\x10\x00\x917@\x10\x817\x00\x00\x917@\x10\x817\x00\x00\x91@@\x10\x81@\x00\x10\x917@\x81 \x817\x00\x00\xff/\x00"""
        s = SMF([test1, test2], instruments=[0, 16])
        s.write(out_fd, title="test song")
        actual_bytes = out_fd.getvalue()

        self.assertEqual(expected_bytes, actual_bytes)

    def test_velocity(self):
        from sebastian.midi.write_midi import Trk

        t = Trk()
        t.start_note(0, 1, 60, 10)
        self.assertEqual(b'\x00\x91\x3c\x0a', t.data.getvalue())

    def test_velocity_from_note(self):
        from sebastian.core import OSequence, Point
        from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64

        test = OSequence([
            Point({OFFSET_64: o, MIDI_PITCH: m, DURATION_64: d}) for (o, m, d) in [
                (0, 60, 16), (16, 72, 16), (32, 64, 16)
            ]
        ])

        test[0]['velocity'] = 10
        test[1]['velocity'] = 255

        from sebastian.midi.write_midi import SMF
        from io import BytesIO
        out_fd = BytesIO(bytearray())

        expected_bytes = b'MThd\x00\x00\x00\x06\x00\x01\x00\x02\x00\x10MTrk\x00\x00\x00&\x00\xffX\x04\x04\x02\x18\x08\x00\xffY\x02\x00\x00\x00\xffQ\x03\x07\xa1 \x00\xff\x03\ttest song\x00\xff/\x00MTrk\x00\x00\x00\x1f\x00\xc0\x00\x00\x90<\x0A\x10\x80<\x00\x00\x90H\xff\x10\x80H\x00\x00\x90@@\x10\x80@\x00\x00\xff/\x00'

        s = SMF([test])
        s.write(out_fd, title="test song")
        actual_bytes = out_fd.getvalue()

        self.assertEqual(expected_bytes, actual_bytes)

    def test_velocity_from_note_with_invalid_velocities(self):
        from sebastian.core import OSequence, Point
        from sebastian.core import OFFSET_64, MIDI_PITCH, DURATION_64

        test = OSequence([
            Point({OFFSET_64: o, MIDI_PITCH: m, DURATION_64: d}) for (o, m, d) in [
                (0, 60, 16), (16, 72, 16), (32, 64, 16)
            ]
        ])

        test[0]['velocity'] = -1
        test[1]['velocity'] = 300

        from sebastian.midi.write_midi import SMF
        from io import BytesIO
        out_fd = BytesIO(bytearray())

        expected_bytes = b'MThd\x00\x00\x00\x06\x00\x01\x00\x02\x00\x10MTrk\x00\x00\x00&\x00\xffX\x04\x04\x02\x18\x08\x00\xffY\x02\x00\x00\x00\xffQ\x03\x07\xa1 \x00\xff\x03\ttest song\x00\xff/\x00MTrk\x00\x00\x00\x1f\x00\xc0\x00\x00\x90<\x00\x10\x80<\x00\x00\x90H\xff\x10\x80H\x00\x00\x90@@\x10\x80@\x00\x00\xff/\x00'

        s = SMF([test])
        s.write(out_fd, title="test song")
        actual_bytes = out_fd.getvalue()

        self.assertEqual(expected_bytes, actual_bytes)

########NEW FILE########
