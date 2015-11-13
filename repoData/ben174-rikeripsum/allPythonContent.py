__FILENAME__ = rikeripsum
#!/usr/bin/env python

import pickle
import random
import os
import argparse

lines = None

_ROOT = os.path.abspath(os.path.dirname(__file__))

def get_data(path):
    return os.path.join(_ROOT, 'data', path)


def generate_paragraph(sentence_count=None): 
    """Generates a 'paragraph' consisting of sentence_count 'sentences'.
    If sentence_count is not provided, a random number between two and
    ten will be chosen.
    
    """
    if not sentence_count:
        sentence_count = random.choice(range(2, 10))
    paragraph = ''
    for i in range(sentence_count): 
        paragraph += ' ' + generate_sentence()
    return paragraph.strip()


def generate_sentence(word_count=None): 
    """Returns a 'sentence'. A sentence is actually one line of dialog
    by William Riker, and may in fact consiste of multiple sentences.
    If a word_count is provided, the generator will attempt to return 
    a sentence with that number of words. Or come as close as possible. 
    Note that higher numbers of word will become increasingly unique to
    the distribution and may result in a less 'random' sentence. 

    """
    global lines
    if not lines: 
        lines = load_pickle()
    if not word_count: 
        return random.choice(lines)['text']

    potential_matches = [line for line in lines if 
        line['word_count'] == word_count]
    if potential_matches: 
        return random.choice(potential_matches)['text']
    else: 
        if word_count == 1:
            raise ImpossibleSentenceError('Couldn\'t generate a sentence with \
                the requested number of words.')
        # recursive callback, trying one less words each time. 
        return generate_sentence(word_count - 1)


def load_pickle(): 
    """Loads up sentence data. All methods in this class which use 
    phrase data should call this if global lines == None.

    """
    f = open(get_data('riker.pickle'))
    return pickle.load(f)


class ImpossibleSentenceError(Exception):
    """Called when the engine is unable to fufill the request due to lack 
    of potential data. This would usually be raised if a number of sentences 
    was requested which the engine did not have data to fulfill.

    """
    def __init__(self, message, Errors):
        Exception.__init__(self, message)


def main():

    parser = argparse.ArgumentParser(description='Print Riker quotes.')
    parser.add_argument('-c', '--count', dest='count', type=int,
                       help='minimum number of words in the sentence')

    args = parser.parse_args()
    print generate_sentence(args.count)


if __name__ == '__main__': 
    main()

########NEW FILE########
__FILENAME__ = script-stripper-all
#!/usr/bin/env python
import re
import os, os.path
import pickle

num_words = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',]

_ROOT = os.path.abspath(os.path.dirname(__file__))


def get_data(path):
    return os.path.join(_ROOT, 'data', path)

def main():
    lines = {}
    for season_num in range(1, 7): #check every script for all seasons
        season_dir = 'scripts/season%s' % num_words[season_num]
        for script_file in os.listdir(season_dir): 
            record = False
            dbuffer = ""
            charname = ""
            f = open('scripts/season%s/%s' % (num_words[season_num], script_file))
            for data in f.readlines(): #look for pattern indicating charector name
                if "<p>" in data and "<br>" in data:
                    splited = data.split("<p>")[-1].split("<br>")[0]
                    splited = splited.split("'S")[0].split(" ")
                    if len(splited) > 5: #long list of words probably isnt a name
                        continue
                    for name in splited:
                        if name.isupper(): # charector names are uppercase
                            charname = name
                            record = True
                            dbuffer = ""
                            break
                elif record: #if name was just found, extract dialog until </p>
                    dbuffer += data
                    if "</p>" in data:
                        dbuffer = dbuffer.replace("<br>","").replace("</p>","")
                        dbuffer = dbuffer.replace("\r","").replace("\n","")
                        dbuffer = dbuffer.replace("\a","").strip()
                        dbuffer = ' '.join(dbuffer.split())
                        line = {"text" : dbuffer, 
                                "episode" : script_file.replace('.htm', ''),
                                "word_count" : len(dbuffer.split())}
                        record = False
                        if charname in lines:
                            lines[charname].append(line)
                        else:
                            lines[charname] = [line]
        
    pickle_file = open(get_data('all_charectors.pickle'), 'wb')
    pickle.dump(lines, pickle_file)
    pickle_file.close()
    
    stats = []
    for name in lines:
        stats.append([len(lines[name]), name])
    stats.sort()
    
    for num_lines, name in stats:
        print name, ": ", num_lines, "lines parsed"
    


if __name__ == '__main__': 
    main()

########NEW FILE########
__FILENAME__ = script-stripper
#!/usr/bin/env python
import re
import os, os.path
import pickle

character = 'RIKER'
num_words = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',]

_ROOT = os.path.abspath(os.path.dirname(__file__))


def get_data(path):
    return os.path.join(_ROOT, 'data', path)


def main():
    lines = []
    for season_num in range(1, 7):
        season_dir = 'scripts/season%s' % num_words[season_num]
        for script_file in os.listdir(season_dir): 
            curr_lines = extract_riker_lines(season_num, script_file)
            lines.extend(curr_lines)
    lines.sort()

    pickle_file = open(get_data('%s.pickle' % character.lower()), 'wb')
    pickle.dump(lines, pickle_file)
    pickle_file.close()

    for line in lines: 
        print line


def extract_riker_lines(season_num, filename): 
    lines = []
    f = open('scripts/season%s/%s' % (num_words[season_num], filename))
    body = f.read()
    body = body.replace('\n', '').replace('\r', '')
    matches = re.findall(r'<p> ' + character + r'<br>[ ]+(.*?)</p>', body)
    for match in matches: 
        line = {}
        line['text'] = ' '.join(match.split())
        line['text'] = re.sub(r'\(.*?\)', '', line['text'])
        line['text'] = line['text'].replace('<br>', '').strip()
        line['text'] = line['text'].replace('&quot;', '"')
        line['episode'] = filename.replace('.htm', '')
        line['word_count'] = len(line['text'].split())
        lines.append(line)
    return lines 


if __name__ == '__main__': 
    main()

########NEW FILE########
