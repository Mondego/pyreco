__FILENAME__ = canon
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append(sys.path[0] + '/../melopy/')

from melopy import *

if __name__ == "__main__":
    m = Melopy('canon', 50)
    melody = []

    for start in ['d4', 'a3', 'b3m', 'f#3m', 'g3', 'd3', 'g3', 'a3']:
        if start.endswith('m'):
            scale = minor_scale(start[:-1])
        else:
            scale = major_scale(start)

        scale.insert(0, scale[0][:-1] + str(int(scale[0][-1]) - 1))

        [melody.append(note) for note in scale]

    m.add_melody(melody, 0.2)
    m.add_rest(0.4)
    m.add_note('d4', 0.4)
    m.add_rest(0.1)
    m.add_note(['d4', 'a4', 'd5'], 0.8)

    m.render()

# Licensed under The MIT License (MIT)
# See LICENSE file for more


########NEW FILE########
__FILENAME__ = entertainer
from melopy import Melopy
import os

def main():
    m = Melopy('entertainer')
    m.tempo = 140
    d = os.path.dirname(__file__)
    if len(d):
        m.parsefile(d + '/scores/entertainer.mlp')
    else:
        m.parsefile('scores/entertainer.mlp')
    m.render()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = fifths
#!/usr/bin/python

from melopy import *

def frequency_up_fifth(f):
    # returns a frequency of the fifth note up from the given frequency
    return key_to_frequency(frequency_to_key(f) + 5)

def fifth_saw(f, t):
    # sawtooth wave representing a note and its fifth
    return sawtooth(f, t) + sawtooth(frequency_up_fifth(f), t)

if __name__ == '__main__':
    m = Melopy('fifths')

    # change the wave_type
    m.wave_type = fifth_saw

    m.parse('C Eb G G Eb [C]')
    m.render()

########NEW FILE########
__FILENAME__ = furelise
from melopy import Melopy
import os

def main():
    m = Melopy('furelise')
    d = os.path.dirname(__file__)
    if len(d):
        m.parsefile(d + '/scores/furelise.mlp')
    else:
        m.parsefile('scores/furelise.mlp')
    m.render()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = mary
from melopy import Melopy
import os

def main():
    m = Melopy('mary')
    d = os.path.dirname(__file__)
    if len(d):
        m.parsefile(d + '/scores/mary.mlp')
    else:
        m.parsefile('scores/mary.mlp')
    m.render()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = menuet
from melopy import Melopy
import os

def main():
    m = Melopy('menuet')
    d = os.path.dirname(__file__)
    if len(d):
        m.parsefile(d + '/scores/menuet.mlp')
    else:
        m.parsefile('scores/menuet.mlp')
    m.render()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = parser
#!/usr/bin/python

# generic parser for Melopy
#
#  $ python examples/parser.py entertainer < examples/scores/entertainer.mlp

from melopy import *
from sys import argv, exit

if len(argv) < 2:
    fn = 'melody'
else:
    fn = argv[1]

m = Melopy(fn)
buff = raw_input()
data = buff

while True:
    try:
        buff = raw_input()
        data += '\n' + buff
    except EOFError:
        break

m.parse(data)
m.render()

########NEW FILE########
__FILENAME__ = twinkle
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys; sys.path.append(sys.path[0] + '/../melopy/')

from melopy import *

if __name__ == "__main__":
    song = Melopy('twinkle', 50)

    song.tempo = 160
    song.wave_type = square

    part1notes = ['C', 'G', 'A', 'G', 'F', 'E', 'D', 'C']
    part2notes = ['G', 'F', 'E', 'D']

    def twinkle(notes):
        for i in range(len(notes)):
            song.add_quarter_note(notes[i])
            if i % 4 == 3:
                song.add_quarter_rest()
            else:
                song.add_quarter_note(notes[i])

    twinkle(part1notes)
    twinkle(part2notes)
    twinkle(part2notes)
    twinkle(part1notes)

    song.render()

# Licensed under The MIT License (MIT)
# See LICENSE file for more

########NEW FILE########
__FILENAME__ = chords
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utility import note_to_key, key_to_note, iterate
from exceptions import MelopyGenericError

CHORD_INTERVALS = {
    'maj': [4,3],
    'min': [3,4],
    'aug' : [4,4],
    'dim' : [3,3],
    '7': [4,3,3],
    'maj7': [4,3,4],
    'min7': [3,4,3],
    'minmaj7': [3,4,4],
    'dim7': [3,3,3,3]
}

def _get_inversion(chord, inversion):
    return chord[inversion:] + chord[:inversion]

def generateChord(name, tonic, inversion=0, rType='list', octaves=True):
    if name in CHORD_INTERVALS:
        steps = CHORD_INTERVALS[name]
        return _get_inversion(iterate(tonic, steps, rType, octaves),inversion)
    else:
        raise MelopyGenericError("Unknown Chord:"+str(name))

# Licensed under The MIT License (MIT)
# See LICENSE file for more

########NEW FILE########
__FILENAME__ = exceptions
class MelopyGenericError(Exception): pass
class MelopyValueError(ValueError): pass

########NEW FILE########
__FILENAME__ = melopy
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import wave, struct, random, math
import os, sys

from utility import *
from scales  import *

# same included wave functions
# a function of frequency and tick
#   each function accepts the frequency and tick,
#   and returns a value from -1 to 1

sine     = lambda f, t: math.sin(2 * math.pi * t * f / 44100.0)
square   = lambda f, t: 0.6 * ((t % (44100 / f) >= ((44100 / f)/2)) * 2 - 1)
sawtooth = lambda f, t: (t % (44100 / f)) / (44100 / f) * 2 - 1
def triangle(f, t):
    v = 2 * (t % (44100 / f)) / (44100 / f)
    if t % (44100 / f) >= (44100 / (2 * f)):
        v = 2 * 1 - v
    v = 2 * v - 1
    return v

class Melopy:
    def __init__(self, title='sound', volume=20, tempo=120, octave=4):
        self.title = title.lower()
        self.rate = 44100
        self.volume = volume
        self.data = []

        self.tempo = tempo
        self.octave = octave
        self.wave_type = sine

    def add_wave(self, frequency, length, location='END', level=None):
        if location == 'END':
            location = len(self.data)
        elif location < 0:
            location = 0
        elif location * 44100 > len(self.data):
            location = len(self.data) / 44100.0

        # location is a time, so let's adjust
        location = int(location * 44100)

        if level == None:
            level = self.volume
        elif level > 100:
            level = 100
        elif level < 0:
            level = 0

        for n in range(0, int(44100 * length)):
            val = self.wave_type(frequency, n)
            val *= level / 100.0 * 32767

            if location + n >= len(self.data):
                self.data.append(val)
            else:
                current_val = self.data[location + n]
                if current_val + val > 32767:
                    val = 32767
                elif current_val + val < -32768:
                    val = -32768
                else:
                    val += current_val

                self.data[location + n] = val

    def add_note(self, note, length, location='END', volume=None):
        """Add a note, or if a list, add a chord."""
        if not isinstance(note, list):
            note = [note]

        if location == 'END':
            location = len(self.data) / 44100.0

        if not isinstance(volume, list):
            volume = [volume]
        if volume[0] == None:
            volume = [float(self.volume)/len(note)] * len(note)
            #By default, when adding a chord, set equal level for each
            #component note, such that the sum volume is self.volume
        else:
            volume = volume + [volume[-1]]*(len(note) - len(volume))
            #Otherwise, pad volume by repeating the final level so that we have
            #enough level values for each note

        for item, level in zip(note, volume):
            if item[-1] not in '0123456789':
                item += str(self.octave)

            self.add_wave(note_to_frequency(item, self.octave), length, location, level)

    def add_melody(self, melody, length):
        for note in melody:
            if note[-1] not in '0123456789':
                note += self.octave
            self.add_wave(note_to_frequency(note), length)

    def add_whole_note(self, note, location='END', volume=None):
        """Add a whole note"""
        self.add_fractional_note(note, 1.0, location, volume)

    def add_half_note(self, note, location='END', volume=None):
        """Add a half note"""
        self.add_fractional_note(note, 1.0 / 2, location, volume)

    def add_quarter_note(self, note, location='END', volume=None):
        """Add a quarter note"""
        self.add_fractional_note(note, 1.0 / 4, location, volume)

    def add_eighth_note(self, note, location='END', volume=None):
        """Add a eigth note"""
        self.add_fractional_note(note, 1.0 / 8, location, volume)

    def add_sixteenth_note(self, note, location='END', volume=None):
        """Add a sixteenth note"""
        self.add_fractional_note(note, 1.0 / 16, location, volume)

    def add_fractional_note(self, note, fraction, location='END', volume=None):
        """Add a fractional note (smaller then 1/16 notes)"""
        self.add_note(note, 60.0 / self.tempo * (fraction * 4), location, volume)

    def add_rest(self, length):
        for i in range(int(self.rate * length)):
            self.data.append(0)

    def add_whole_rest(self):
        self.add_fractional_rest(1.0)

    def add_half_rest(self):
        self.add_fractional_rest(1.0 / 2)

    def add_quarter_rest(self):
        self.add_fractional_rest(1.0 / 4)

    def add_eighth_rest(self):
        self.add_fractional_rest(1.0 / 8)

    def add_sixteenth_rest(self):
        self.add_fractional_rest(1.0 / 16)

    def add_fractional_rest(self, fraction):
        self.add_rest(60.0 / self.tempo * (fraction * 4))

    def parse(self, string, location='END'):
        tracks = string.split('&&&')

        # special case for multiple tracks
        if len(tracks) > 1:
            t = len(self.data) / 44100.0
            for track in tracks:
                self.parse(track, t)
            return

        cf = 0.25                    # start with a quarter note, change accordingly
        in_comment = False

        for i, char in enumerate(string):        # divide melody into fragments
            # / this is a comment /
            if char == '/':
                in_comment = not in_comment

            if in_comment:
                continue
            elif char in 'ABCDEFG':
                if (i+1 < len(string)) and (string[i+1] in '#b'):
                    # check if the next item in the array is
                    #    a sharp or flat, make sure we include it
                    char += string[i+1]

                self.add_fractional_note(char, cf, location)
                if location != 'END':
                    location += (60.0 / self.tempo * (cf * 4))
            elif char in map(str, range(0, 20)):
                self.octave = int(char)
            elif char == '+' or char == '^':
                self.octave += 1
            elif char == 'V' or char == 'v' or char == '-':
                self.octave -= 1
            elif char == '(' or char == ']':
                cf /= 2
            elif char == ')' or char == '[':
                cf *= 2
            elif char == '_':
                self.add_fractional_rest(cf)
                if location != 'END':
                    location += (60.0 / self.tempo * (cf * 4))

    def parsefile(self, filename, location='END'):
        fr = open(filename, 'r')
        s = fr.read()
        fr.close()

        self.parse(s, location)

    def render(self):
        """Render a playable song out to a .wav file"""
        melopy_writer = wave.open(self.title + '.wav', 'w')
        melopy_writer.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
        p = -1
        data_frames = []

        for i in range(len(self.data)):
            q = 100 * i / len(self.data)
            if p != q:
                sys.stdout.write("\r[%s] %d%%" % (('='*int((float(i)/len(self.data)*50))+'>').ljust(50), 100 * i / len(self.data)))
                sys.stdout.flush()
                p = q
            packed_val = struct.pack('h', int(self.data[i]))
            data_frames.append(packed_val)
            data_frames.append(packed_val)

        melopy_writer.writeframes(''.join(data_frames))

        sys.stdout.write("\r[%s] 100%%" % ('='*50))
        sys.stdout.flush()
        sys.stdout.write("\nDone\n")
        melopy_writer.close()

    def play(self):
        """Opens the song in the os default program"""
        os.startfile(self.title + '.wav')

# Licensed under The MIT License (MIT)
# See LICENSE file for more

########NEW FILE########
__FILENAME__ = scales
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utility import note_to_key, key_to_note, iterate
from exceptions import MelopyGenericError

SCALE_STEPS = {
    "major":[2,2,1,2,2,2,1],
    "melodic_minor":[2,1,2,2,2,2,1],
    "harmonic_minor":[2,1,2,2,2,1,2],
    "chromatic":[1,1,1,1,1,1,1,1,1,1,1],
    "major_pentatonic":[2,2,3,2],
    "minor_pentatonic":[3,2,2,3]
}

def _get_mode(steps, mode):
    """ Gets the correct mode step list by rotating the list """
    mode = mode - 1
    res = steps[mode:] + steps[:mode]
    return res

def generateScale(scale, note, mode=1, rType="list", octaves=True): #scale, start, type
    """
    Generate a scale
    scale (string): major,  melodic_minor, harmonic_minor, chromatic, major_pentatonic
    note: start note
    """
    if scale in SCALE_STEPS:
        steps = _get_mode(SCALE_STEPS[scale], mode)
        return iterate(note, steps, rType, octaves)
    else:
        raise MelopyGenericError("Unknown scale type:" + str(scale))

# Licensed under The MIT License (MIT)
# See LICENSE file for more

########NEW FILE########
__FILENAME__ = utility
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from math import log
from exceptions import MelopyGenericError, MelopyValueError

def key_to_frequency(key):
    """Returns the frequency of the note (key) keys from A0"""
    return 440 * 2 ** ((key - 49) / 12.0)

def key_to_note(key, octaves=True):
    """Returns a string representing a note which is (key) keys from A0"""
    notes = ['a','a#','b','c','c#','d','d#','e','f','f#','g','g#']
    octave = (key + 8) / 12
    note = notes[(key - 1) % 12]

    if octaves:
        return note.upper() + str(octave)
    else:
        return note.upper()

def note_to_frequency(note, default=4):
    """Returns the frequency of a note represented by a string"""
    return key_to_frequency(note_to_key(note, default))

def note_to_key(note, default=4):
    """Returns the key number (keys from A0) from a note represented by a string"""
    indices = { 'C':0, 'D':2, 'E':4, 'F':5, 'G':7, 'A':9, 'B':11 }

    octave = default

    if note[-1] in '012345678':
        octave = int(note[-1])

    tone = indices[note[0].upper()]
    key = 12 * octave + tone

    if len(note) > 1 and note[1] == '#':
        key += 1
    elif len(note) > 1 and note[1] == 'b':
        key -= 1

    return key - 8;

def frequency_to_key(frequency):
    return int(12 * log(frequency/440.0) / log(2) + 49)

def frequency_to_note(frequency):
    return key_to_note(frequency_to_key(frequency))

def bReturn(output, Type):
    """Returns a selected output assuming input is a list"""
    if isinstance(output, list):
        if Type.lower() == "list":
            return output
        elif Type.lower() == "tuple":
            return tuple([i for i in output])
        elif Type.lower() == "dict":
            O = {}
            for i in range(len(output)):
                O[i] = output[i]
            return O
        elif Type.lower() == "string":
            return ''.join(output)
        elif Type.lower() == "stringspace":
            return ' '.join(output)
        elif Type.lower() == "delemiter":
            return ','.join(output)
        else:
            raise MelopyGenericError("Unknown type: " + Type)
    else:
        raise MelopyGenericError("Input to bReturn is not a list! Input: " + str(output))

def iterate(start, pattern, rType="list", octaves=True):
    """Iterates over a pattern starting at a given note"""
    start_key = note_to_key(start)
    ret = [start_key]
    for step in pattern:
        ret.append(ret[-1] + step)

    for i, item in enumerate(ret):
        ret[i] = key_to_note(ret[i], octaves)

    return bReturn(ret, rType)


# Licensed under The MIT License (MIT)
# See LICENSE file for more

########NEW FILE########
__FILENAME__ = melopy_tests
#!/usr/bin/env
# -*- coding: utf-8 -*-

import unittest

from melopy import chords, scales, utility, exceptions

def data_provider(data):
    def decorator(fn):
        def repl(self, *args):
            for i in data():
                fn(self, *i)
        return repl
    return decorator

class LibraryFunctionsTests(unittest.TestCase):
    def test_key_to_frequency(self):
        key = 49
        self.assertEqual(440, utility.key_to_frequency(key))

    def test_note_to_frequency(self):
        note = 'A4'
        self.assertEqual(440, utility.note_to_frequency(note))

    def test_note_to_key(self):
        note = 'A4'
        self.assertEqual(49, utility.note_to_key(note))

    def test_key_to_note(self):
        key = 49
        self.assertEqual('A4', utility.key_to_note(key))

    def test_iterate(self):
        start = 'D4'
        pattern = [2, 2, 1, 2, 2, 2]
        should_be = ['D4', 'E4', 'F#4', 'G4', 'A4', 'B4', 'C#5']
        self.assertEqual(should_be, utility.iterate(start, pattern))

    def test_generate_major_scales(self):
        start = 'D4'
        should_be = ['D4', 'E4', 'F#4', 'G4', 'A4', 'B4', 'C#5','D5']
        self.assertEqual(should_be, scales.generateScale('major', start))

    def test_generate_chromatic_scales(self):
        start = 'C5'
        should_be= ['C5', 'C#5', 'D5', 'D#5', 'E5', 'F5', 'F#5', 'G5', 'G#5', 'A5', 'A#5', 'B5']
        self.assertEqual(should_be, scales.generateScale('chromatic', start))

    def test_generate_major_pentatonic_scales(self):
        start = 'C5'
        should_be = ['C5', 'D5', 'E5', 'G5', 'A5']
        self.assertEqual(should_be, scales.generateScale('major_pentatonic', start))

    def test_generate_minor_pentatonic_scales(self):
        start = 'A5'
        should_be = ['A5', 'C6', 'D6', 'E6', 'G6']
        self.assertEqual(should_be, scales.generateScale('minor_pentatonic', start))

    def test_generate_dorian_mode(self):
        start = 'D5'
        should_be = ['D5','E5','F5','G5','A5','B5','C6','D6']
        self.assertEqual(should_be, scales.generateScale('major', start, mode=2))

    def test_generate_phrygian_mode(self):
        start = 'E5'
        should_be = ['E5','F5','G5','A5','B5','C6','D6','E6']
        self.assertEqual(should_be, scales.generateScale('major', start, mode=3))

    def test_generate_lydian_mode(self):
        start = 'C5'
        should_be = ['C5','D5','E5','F#5','G5','A5','B5','C6']
        self.assertEqual(should_be, scales.generateScale('major', start, mode=4))

    def test_generate_mixolydian_mode(self):
        start = 'C5'
        should_be = ['C5','D5','E5','F5','G5','A5','A#5','C6']
        self.assertEqual(should_be, scales.generateScale('major', start, mode=5))

    def test_generate_dorian_flat_nine(self):
        start = 'D5'
        should_be = ['D5','D#5','F5','G5','A5','B5','C6','D6']
        self.assertEqual(should_be, scales.generateScale('melodic_minor', start, mode=2))

    def test_generate_lydian_augmented(self):
        start = 'C5'
        should_be = ['C5','D5','E5','F#5','G#5','A5','B5','C6']
        self.assertEqual(should_be, scales.generateScale('melodic_minor', start, mode=3))

    def test_generate_lydian_dominant(self):
        start = 'C5'
        should_be = ['C5','D5','E5','F#5','G5','A5','A#5','C6']
        self.assertEqual(should_be, scales.generateScale('melodic_minor', start, mode=4))

    def test_generate_major_triad(self):
        start = 'C5'
        should_be = ['C5','E5','G5']
        self.assertEqual(should_be, chords.generateChord('maj', start))

    def test_generate_min_triad(self):
        start = 'C5'
        should_be = ['C5','D#5','G5']
        self.assertEqual(should_be, chords.generateChord('min', start))

    def test_generate_maj_first_inversion(self):
        start = 'C5'
        should_be = ['E5','G5','C5']
        self.assertEqual(should_be, chords.generateChord('maj', start, inversion=1))

    def test_generate_maj_second_inversion(self):
        start = 'C5'
        should_be = ['G5','C5','E5']
        self.assertEqual(should_be, chords.generateChord('maj', start, inversion=2))

    def test_generate_maj_seven(self):
        start = 'C5'
        should_be = ['C5','E5','G5','B5']
        self.assertEqual(should_be, chords.generateChord('maj7', start))

    def test_generate_maj_seven(self):
        start = 'C5'
        should_be = ['C5','E5','G5','B5']
        self.assertEqual(should_be, chords.generateChord('maj7', start))

    def test_generate_aug(self):
        start = 'C5'
        should_be = ['C5','E5','G#5']
        self.assertEqual(should_be, chords.generateChord('aug', start))

    def test_generate_dim(self):
        start = 'C5'
        should_be = ['C5','D#5','F#5']
        self.assertEqual(should_be, chords.generateChord('dim', start))

    def test_generate_seven(self):
        start = 'C5'
        should_be = ['C5','E5','G5','A#5']
        self.assertEqual(should_be, chords.generateChord('7', start))


if __name__ == '__main__':
    unittest.main()

# Licensed under The MIT License (MIT)
# See LICENSE file for more

########NEW FILE########
