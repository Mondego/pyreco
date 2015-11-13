__FILENAME__ = lilypond_example
#!/usr/bin/env python   
# -*- coding: utf-8 -*-

from musthe import *


def lilypond_composer(bars, instrument='acoustic guitar (steel)', file_name='example.ly'):
    f = open(file_name, 'w')
    f.write('''\\score {
    \\new Voice \\relative c\' {
        \\set midiInstrument = #"'''+instrument+'"\n')
    for bar in bars:
        f.write('\t\t'+bar+'\n')
    f.write('''
    }
    \\midi{
        \\tempo 4 = 160
        \\context {
            \\Voice
            \\consists "Staff_performer"
        }
    }
    \\layout { }
}''')
    f.close()
    #timidity <input-file> -Ow -o <output-file>

def random_music():
    import random
    n = Note('Bb')
    pool = scale(n, 'minor_pentatonic')

    for total_bars in range(4):
        bar = []
        notes_in_bar = 2**random.randrange(1, 3)

        index = 0
        for _ in range(notes_in_bar):
            note = pool[index].lilypond_notation()+str(notes_in_bar)

            '''
            difference = (bar[-1].octave)-(pool[index].octave)
            if difference == 1:
                note+=','
            elif difference == -1:
                note+='\''
            '''

            bar.append(note)

            change = int(random.gauss(0,2))
            while not 0<index+change<=len(pool):
                change = int(random.gauss(0,2))
            index+=change
        yield ' '.join(bar)

lilypond_composer(random_music())

########NEW FILE########
__FILENAME__ = musthe
#!/usr/bin/env python   
# -*- coding: utf-8 -*- 

"""
Copyright (c) 2014 Gonzalo Ciruelos <gonzalo.ciruelos@gmail.com>
"""

import re


def scale(note, scale_name):
    scales = {
        'major' :           ['M2', 'M3', 'P4', 'P5', 'M6', 'M7', 'P8'],
        'natural_minor':    ['M2', 'm3', 'P4', 'P5', 'm6', 'm7', 'P8'],
        'harmonic_minor':   ['M2', 'm3', 'P4', 'P5', 'm6', 'M7', 'P8'],
        'melodic_minor':    ['M2', 'm3', 'P4', 'P5', 'M6', 'M7', 'P8'],
        'dorian':           ['M2', 'm3', 'P4', 'P5', 'M6', 'm7', 'P8'],
        'locrian':          ['m2', 'm3', 'P4', 'd5', 'm6', 'm7', 'P8'],
        'lydian':           ['M2', 'M3', 'A4', 'P5', 'M6', 'M7', 'P8'],
        'mixolydian':       ['M2', 'M3', 'P4', 'P5', 'M6', 'm7', 'P8'],
        'phrygian':         ['m2', 'm3', 'P4', 'P5', 'm6', 'm7', 'P8'],
        'major_pentatonic': ['M2', 'M3', 'P5', 'M6', 'P8'],
        'minor_pentatonic': ['m3', 'P4', 'P5', 'm7', 'P8']
    }
    if scale_name in scales:
        return [note] + [note+Interval(i) for i in scales[scale_name]]
    raise Exception('No scale named '+scale_name)


class Note():
    """
    The note class.

    The notes are to be parsed in th following way:
    * the letter name,
    * accidentals (up to 3),
    * octave (default is 4).

    For example, 'Ab', 'G9', 'B##7' are all valid notes. '#', 'A9b',
    'Dbbbb' are not.
    """
    def __init__(self, note):
        note_pattern = re.compile(r'^[A-G]([b#])?\1{0,2}?\d?$') #raw because of '\'
        if note_pattern.search(note) == None:
            raise Exception('Could not parse the note: '+note)

        self.tone = note[0]
        self.accidental = re.findall('[b#]{1,3}', note)
        self.octave = re.findall('[0-9]', note)

        if self.accidental == []:
            self.accidental = ''
        else:
            self.accidental = self.accidental[0]

        if self.octave == []:
            self.octave = 4
        else:
            self.octave = int(self.octave[0])

        self.note_id = {'C':0, 'D':2, 'E':4, 'F':5, 'G':7, 'A':9, 'B':11}[self.tone]
        for change in self.accidental:
            if change == '#': self.note_id += 1
            elif change == 'b': self.note_id -= 1
        self.note_id %= 12


    def __add__(self, interval):
        if not isinstance(interval, Interval):
            raise Exception('Cannot add '+type(interval)+' to a note.')

        # * _old_note is the index in the list of the old note tone.
        # * new_note_tone is calculated adding the interval_number-1 because
        # you have start counting in the current tone. e.g. the fifth of
        # E is: (E F G A) B.
        _old_tone = 'CDEFGABCDEFGABCDEFGAB'.index(self.tone)
        # Fixing Issue #7: Note('Ab')+Interval('m3') --> Exception
        if self.tone == 'A' and self.accidental.startswith('b') and interval.number == 3 and interval.semitones == 3:
            new_note_tone = 'B'
        else:
            new_note_tone = 'CDEFGABCDEFGABCDEFGAB'[_old_tone+interval.number-1]

        # %12 because it wraps in B->C and starts over.
        new_note_id = (self.note_id+interval.semitones)%12

        # First calculates the note, and then the difference from the note
        # without accidentals, then adds proper accidentals.
        difference = new_note_id - {'C':0, 'D':2, 'E':4, 'F':5, 'G':7, 'A':9, 'B':11}[new_note_tone]
        # In some cases, like G##+m3, difference is -11, and it should be
        # 1, so this corrects the error.
        if abs(difference)>3:
            difference = difference + 12

        if difference<0: accidental = 'b'*abs(difference)
        elif difference>0: accidental = '#'*abs(difference)
        else: accidental = ''


        # it calculates how many times it wrapped around B->C and adds.
        new_note_octave = (self.note_id+interval.semitones)//12+self.octave
        # corrects cases like B#, B##, B### and A###.
        # http://en.wikipedia.org/wiki/Scientific_pitch_notation#C-flat_and_B-sharp_problems
        if new_note_tone+accidental in ['B#', 'B##', 'B###', 'A###']:
            new_note_octave -= 1

        return Note(new_note_tone+accidental+str(new_note_octave))

    def frequency(self):
        """
        Returns frequency in Hz. It uses the method given in
        http://en.wikipedia.org/wiki/Note#Note_frequency_.28hertz.29
        """
        pass

    def lilypond_notation(self):
        return str(self).replace('b', 'es').replace('#', 'is').lower()

    def scientific_notation(self):
        return str(self)+str(self.octave)

    def __repr__(self):
        return "Note(\"%s\")" % self.scientific_notation()

    def __str__(self):
        return self.tone+self.accidental

    def __eq__(self, other):
        return self.scientific_notation() == other.scientific_notation()


class Interval():
    """
    The interval class.

    The notes are to be parsed in th following way:
    * the quality, (m, M, p, A, d)
    * the number. (1 to 8) [Compound intervals will be supported]

    For example, 'd8', 'P1', 'A5' are valid intervals. 'P3', '5' are not.
    """
    def __init__(self, interval):
        try:
            self.semitones = {'P1': 0, 'A1':1, 'd2':0, 'm2':1, 'M2':2, 'A2':3,
                              'd3':3, 'm3':3, 'M3':4, 'A3':5, 'd4':4, 'P4':5,
                              'A4':6, 'd5':6, 'P5':7, 'A5':8, 'd6':7, 'm6':8,
                              'M6':9, 'A6':10,'d7':9, 'm7':10, 'M7':11, 'A7':12,
                              'd8':11, 'P8':12}[interval]
        except:
            raise Exception('Could not parse the interval.')
        self.number = int(interval[1])


class Chord():
    chord_recipes = {'M': ['R', 'M3', 'P5'],
                     'm': ['R', 'm3', 'P5'],
                     'dim': ['R', 'm3', 'd5'],
                     'aug': ['R', 'M3', 'A5'],
                     }

    def __init__(self, root, chord_type='M'):
        self.notes = []

        try:
            self.notes.append(root)
        except:
            raise Exception('Invalid root note supplied.')

        if chord_type in self.chord_recipes.keys():
            self.chord_type = chord_type
        else:
            raise Exception('Invalid chord type supplied! current valid types: {} '.format(self.chord_recipes.keys()))

        self.build_chord()

    def build_chord(self):
        self.add_intervals(self.chord_recipes[self.chord_type][1:])

    def add_intervals(self, intervals):
        for i in intervals:
            self.notes.append(self.notes[0]+Interval(i))

    def __repr__(self):
        return "Chord(Note({!r}), {!r})".format(str(self.notes[0]), self.chord_type)

    def __str__(self):
        return "{}{}".format(str(self.notes[0]),self.chord_type)

    def __eq__(self, other):
        if len(self.notes) != len(other.notes):
            #if chords dont have the same number of notes, def not equal
            return False
        else:
            return all(self.notes[i] == other.notes[i] for i in range(len(self.notes)))

if __name__ == '__main__':
    add = Note('Ab')+Interval('m3')
    print add

########NEW FILE########
__FILENAME__ = tests

import unittest
from musthe import *


class TestsForJesus(unittest.TestCase):
    def test_note_parsing(self):
        self.assertEqual(str(Note('A4')), 'A')
        self.assertEqual(str(Note('Ab6')), 'Ab')
        self.assertEqual(str(Note('Dbb')), 'Dbb')
        self.assertEqual(str(Note('G###0')), 'G###')

        self.assertRaises(Exception, Note, 'A99')
        self.assertRaises(Exception, Note, 'Ab#')
        self.assertRaises(Exception, Note, 'E####')

    def test_interval_parsing(self):
        self.assertEqual(Interval('d5').semitones, 6)
        self.assertRaises(Exception, Interval, 'P3')

    def test_note_sum(self):
        self.assertEqual(str(Note('A4')+Interval('d5')), str(Note('Eb')))
        self.assertEqual(str(Note('A')+Interval('P1')), str(Note('A')))
        self.assertEqual(str(Note('G##')+Interval('m3')), str(Note('B#')))
        self.assertEqual(str(Note('F')+Interval('P5')), str(Note('C')))

    def test_note_scales(self):
        self.assertEqual(list(map(str, scale(Note('C'), 'major'))),          ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C'])
        self.assertEqual(list(map(str, scale(Note('C'), 'natural_minor'))),  ['C', 'D', 'Eb','F', 'G', 'Ab','Bb','C'])
        self.assertEqual(list(map(str, scale(Note('C'), 'harmonic_minor'))), ['C', 'D', 'Eb','F', 'G', 'Ab','B', 'C'])
        self.assertEqual(list(map(str, scale(Note('C'), 'melodic_minor'))),  ['C', 'D', 'Eb','F', 'G', 'A', 'B', 'C'])
        self.assertEqual(list(map(str, scale(Note('C'), 'dorian'))),         ['C', 'D', 'Eb','F', 'G', 'A', 'Bb','C'])
        self.assertEqual(list(map(str, scale(Note('C'), 'locrian'))),        ['C', 'Db','Eb','F', 'Gb','Ab','Bb','C'])
        self.assertEqual(list(map(str, scale(Note('C'), 'lydian'))),         ['C', 'D', 'E', 'F#','G', 'A', 'B', 'C'])
        self.assertEqual(list(map(str, scale(Note('C'), 'mixolydian'))),     ['C', 'D', 'E', 'F', 'G', 'A', 'Bb','C'])
        self.assertEqual(list(map(str, scale(Note('C'), 'phrygian'))),       ['C', 'Db','Eb','F', 'G', 'Ab','Bb','C'])
        self.assertEqual(list(map(str, scale(Note('C'),'major_pentatonic'))),['C', 'D', 'E', 'G', 'A', 'C'])
        self.assertEqual(list(map(str, scale(Note('C'),'minor_pentatonic'))),['C', 'Eb','F', 'G', 'Bb','C'])
        self.assertRaises(Exception, scale, Note('C'), 'non-existent scale')

class TestsForJesusChords(unittest.TestCase):
    def setUp(self):
        '''put here for later building of test chords, one for each
        chord_type in chord_recipes'''
        self.chord_types = [k for k in Chord(Note('Bb')).chord_recipes.keys()]
        self.chords = {k:Chord(Note('A'), k) for k in self.chord_types}
        self.rootNote = Note('A')

    def tearDown(self):
        self.chords = {}
        self.chord_types = []
        self.rootNote = None

    def test_chord_creation(self):
        #check __str__ returns
        self.assertEqual(str(Chord(Note('A'))), 'AM')
        self.assertEqual(str(Chord(Note('B'), 'm')), 'Bm')
        self.assertEqual(str(Chord(Note('C'), 'dim')), 'Cdim')
        self.assertEqual(str(Chord(Note('D'), 'aug')), 'Daug')
        self.assertEqual(str(Chord(Note('A#'))), 'A#M')
        self.assertEqual(str(Chord(Note('Bb'))), 'BbM')

        #check __repr__ returns
        #//todo
        
        #check __eq__
        #//todo

        #check faulty inputs
        self.assertRaises(Exception, Chord, 'A$')
        self.assertRaises(Exception, Chord, 'H')

        #check recipe notes
        self.assertEqual(self.chords['M'].notes,
                         [self.rootNote,
                          self.rootNote+Interval('M3'),
                          self.rootNote+Interval('P5')
                          ])
        self.assertEqual(self.chords['m'].notes,
                         [self.rootNote,
                          self.rootNote+Interval('m3'),
                          self.rootNote+Interval('P5')
                          ])
        self.assertEqual(self.chords['dim'].notes,
                         [self.rootNote,
                          self.rootNote+Interval('m3'),
                          self.rootNote+Interval('d5')
                          ])
        self.assertEqual(self.chords['aug'].notes,
                         [self.rootNote,
                          self.rootNote+Interval('M3'),
                          self.rootNote+Interval('A5')
                          ])

unittest.main()

########NEW FILE########
