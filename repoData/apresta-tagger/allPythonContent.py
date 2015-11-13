__FILENAME__ = build_dict
#!/usr/bin/env python

# Copyright (C) 2011 by Alessandro Presta

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE


'''
Usage: build_dict.py -o <output file> -s <stopwords file> <list of files>
'''

from __future__ import division

from tagger import Stemmer
from extras import SimpleReader

def build_dict(corpus, stopwords=None, measure='IDF'):
    '''
    @param corpus:    a list of documents, represented as lists of (stemmed)
                      words
    @param stopwords: the list of (stemmed) words that should have zero weight
    @param measure:   the measure used to compute the weights ('IDF'
                      i.e. 'inverse document frequency' or 'ICF' i.e.
                      'inverse collection frequency'; defaults to 'IDF')

    @returns: a dictionary of weights in the interval [0,1]
    '''

    import collections
    import math

    dictionary = {}

    if measure == 'ICF':
        words = [w for doc in corpus for w in doc]
        
        term_count = collections.Counter(words)
        total_count = len(words)
        scale = math.log(total_count)
    
        for w, cnt in term_count.iteritems():
            dictionary[w] = math.log(total_count / (cnt + 1)) / scale

    elif measure == 'IDF':
        corpus_size = len(corpus)
        scale = math.log(corpus_size)

        term_count = collections.defaultdict(int)

        for doc in corpus:
            words = set(doc)
            for w in words:
                term_count[w] += 1

        for w, cnt in term_count.iteritems():
            dictionary[w] = math.log(corpus_size / (cnt + 1)) / scale
            
    if stopwords:
        for w in stopwords:
            dictionary[w] = 0.0
    
    return dictionary


def build_dict_from_files(output_file, corpus_files, stopwords_file=None,
                          reader=SimpleReader(), stemmer=Stemmer(),
                          measure='IDF', verbose=False):
    '''
    @param output_file:    the name of the file where the dictionary should be
                           saved
    @param corpus_files:   a list of files with words to process
    @param stopwords_file: a file containing a list of stopwords
    @param reader:         the L{Reader} object to be used
    @param stemmer:        the L{Stemmer} object to be used
    @param measure:        the measure used to compute the weights ('IDF'
                           i.e. 'inverse document frequency' or 'ICF' i.e.
                           'inverse collection frequency'; defaults to 'IDF')
    @param verbose:        whether information on the progress should be
                           printed on screen
    '''

    import pickle

    if verbose: print 'Processing corpus...'
    corpus = []
    for filename in corpus_files:
        with open(filename, 'r') as doc:
            corpus.append(reader(doc.read()))
    corpus = [[w.stem for w in map(stemmer, doc)] for doc in corpus]

    stopwords = None
    if stopwords_file:
        if verbose: print 'Processing stopwords...'
        with open(stopwords_file, 'r') as sw:
            stopwords = reader(sw.read())
        stopwords = [w.stem for w in map(stemmer, stopwords)]

    if verbose: print 'Building dictionary... '
    dictionary = build_dict(corpus, stopwords, measure)
    with open(output_file, 'wb') as out:
        pickle.dump(dictionary, out, -1) 
    

if __name__ == '__main__':

    import getopt
    import sys
    
    try:
        options = getopt.getopt(sys.argv[1:], 'o:s:')
        output_file = options[0][0][1]
        stopwords_file = options[0][1][1]
        corpus = options[1]
    except:
        print __doc__
        exit(1)

    build_dict_from_files(output_file, corpus, stopwords_file, verbose=True)
    
               


########NEW FILE########
__FILENAME__ = extras
# Copyright (C) 2011 by Alessandro Presta

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE


from tagger import *


class UnicodeReader(Reader):
    '''
    Reader subclass that converts Unicode strings to a close ASCII
    representation
    '''

    def __call__(self, text):
        import unicodedata
        
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore')
        return Reader.__call__(self, text)


class HTMLReader(UnicodeReader):
    '''
    Reader subclass that can parse HTML code from the input
    '''

    def __call__(self, html):
        import lxml.html

        text = lxml.html.fromstring(html).text_content()
        if isinstance(text, unicode):
            return UnicodeReader.__call__(self, text)
        else:
            return Reader.__call__(self, text)

    
class SimpleReader(Reader):
    '''
    Reader subclass that doesn't perform any advanced analysis of the text
    '''
    
    def __call__(self, text):
        text = text.lower()
        text = self.preprocess(text)
        words = self.match_words.findall(text)
        tags = [Tag(w) for w in words]
        return tags


class FastStemmer(Stemmer):
    '''
    Stemmer subclass that uses a much faster, but less correct algorithm
    '''

    def __init__(self):
        from stemming import porter
        
        Stemmer.__init__(self, porter)


class NaiveRater(Rater):
    '''
    Rater subclass that jusk ranks single-word tags by their frequency and
    weight
    '''

    def __call__(self, tags):
        self.rate_tags(tags)
        # we still get rid of one-character tags and stopwords
        unique_tags = set(t for t in tags
                          if len(t.string) > 1 and t.rating > 0.0)
        return sorted(unique_tags)
    
        
def build_dict_from_nltk(output_file, corpus=None, stopwords=None,
                         stemmer=Stemmer(), measure='IDF', verbose=False):
    '''
    @param output_file: the name of the file where the dictionary should be
                        saved
    @param corpus:      the NLTK corpus to use (defaults to nltk.corpus.reuters)
    @param stopwords:   a list of (not stemmed) stopwords (defaults to
                        nltk.corpus.reuters.words('stopwords'))
    @param stemmer:     the L{Stemmer} object to be used
    @param measure:     the measure used to compute the weights ('IDF'
                        i.e. 'inverse document frequency' or 'ICF' i.e.
                        'inverse collection frequency'; defaults to 'IDF')
    @param verbose:     whether information on the progress should be printed
                        on screen
    '''
    
    from build_dict import build_dict
    import nltk
    import pickle

    if not (corpus and stopwords):
        nltk.download('reuters')
        
    corpus = corpus or nltk.corpus.reuters
    stopwords = stopwords or nltk.corpus.reuters.words('stopwords')

    corpus_list = []
    
    if verbose: print 'Processing corpus...'
    for file in corpus.fileids():
        doc = [stemmer(Tag(w.lower())).stem for w in corpus.words(file)
               if w[0].isalpha()]
        corpus_list.append(doc)

    if verbose: print 'Processing stopwords...'
    stopwords = [stemmer(Tag(w.lower())).stem for w in stopwords]

    if verbose: print 'Building dictionary... '
    dictionary = build_dict(corpus_list, stopwords, measure)
    with open(output_file, 'wb') as out:
        pickle.dump(dictionary, out, -1) 



    

    

     

    

        

    





        

########NEW FILE########
__FILENAME__ = tagger
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2011 by Alessandro Presta

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE


'''
======
tagger
======

Module for extracting tags from text documents.
                   
Copyright (C) 2011 by Alessandro Presta

Configuration
=============

Dependencies:
python2.7, stemming, nltk (optional), lxml (optional), tkinter (optional)

You can install the stemming package with::

    $ easy_install stemming

Usage
=====

Tagging a text document from Python::

    import tagger
    weights = pickle.load(open('data/dict.pkl', 'rb')) # or your own dictionary
    myreader = tagger.Reader() # or your own reader class
    mystemmer = tagger.Stemmer() # or your own stemmer class
    myrater = tagger.Rater(weights) # or your own... (you got the idea)
    mytagger = Tagger(myreader, mystemmer, myrater)
    best_3_tags = mytagger(text_string, 3)

Running the module as a script::

    $ ./tagger.py <text document(s) to tag>

Example::

    $ ./tagger.py tests/*
    Loading dictionary... 
    Tags for  tests/bbc1.txt :
    ['bin laden', 'obama', 'pakistan', 'killed', 'raid']
    Tags for  tests/bbc2.txt :
    ['jo yeates', 'bristol', 'vincent tabak', 'murder', 'strangled']
    Tags for  tests/bbc3.txt :
    ['snp', 'party', 'election', 'scottish', 'labour']
    Tags for  tests/guardian1.txt :
    ['bin laden', 'al-qaida', 'killed', 'pakistan', 'al-fawwaz']
    Tags for  tests/guardian2.txt :
    ['clegg', 'tory', 'lib dem', 'party', 'coalition']
    Tags for  tests/post1.txt :
    ['sony', 'stolen', 'playstation network', 'hacker attack', 'lawsuit']
    Tags for  tests/wikipedia1.txt :
    ['universe', 'anthropic principle', 'observed', 'cosmological', 'theory']
    Tags for  tests/wikipedia2.txt :
    ['beetroot', 'beet', 'betaine', 'blood pressure', 'dietary nitrate']
    Tags for  tests/wikipedia3.txt :
    ['the lounge lizards', 'jazz', 'john lurie', 'musical', 'albums']
'''

from __future__ import division

import collections
import re


class Tag:
    '''
    General class for tags (small units of text)
    '''
    
    def __init__(self, string, stem=None, rating=1.0, proper=False,
                 terminal=False):
        '''
        @param string:   the actual representation of the tag
        @param stem:     the internal (usually stemmed) representation;
                         tags with the same stem are regarded as equal
        @param rating:   a measure of the tag's relevance in the interval [0,1]
        @param proper:   whether the tag is a proper noun
        @param terminal: set to True if the tag is at the end of a phrase
                         (or anyway it cannot be logically merged to the
                         following one)

        @returns: a new L{Tag} object
        '''
            
        self.string  = string
        self.stem = stem or string
        self.rating = rating
        self.proper = proper
        self.terminal = terminal
        
    def __eq__(self, other):
        return self.stem == other.stem

    def __repr__(self):
        return repr(self.string)

    def __lt__(self, other):
        return self.rating > other.rating

    def __hash__(self):
        return hash(self.stem)


class MultiTag(Tag):
    '''
    Class for aggregates of tags (usually next to each other in the document)
    '''
    
    def __init__(self, tail, head=None):
        '''
        @param tail: the L{Tag} object to add to the first part (head)
        @param head: the (eventually absent) L{MultiTag} to be extended

        @returns: a new L{MultiTag} object
        '''
        
        if not head:
            Tag.__init__(self, tail.string, tail.stem, tail.rating,
                         tail.proper, tail.terminal)
            self.size = 1
            self.subratings = [self.rating]
        else:
            self.string = ' '.join([head.string, tail.string])
            self.stem = ' '.join([head.stem, tail.stem])
            self.size = head.size + 1

            self.proper = (head.proper and tail.proper)
            self.terminal = tail.terminal

            self.subratings = head.subratings + [tail.rating]
            self.rating = self.combined_rating()
                                           
    def combined_rating(self):
        '''
        Method that computes the multitag's rating from the ratings of unit
        subtags

        (the default implementation uses the geometric mean - with a special
        treatment for proper nouns - but this method can be overridden)
        
        @returns: the rating of the multitag
        '''
        
        # by default, the rating of a multitag is the geometric mean of its
        # unit subtags' ratings
        product = reduce(lambda x, y: x * y, self.subratings, 1.0)
        root = self.size
        
        # but proper nouns shouldn't be penalized by stopwords
        if product == 0.0 and self.proper:
            nonzero = [r for r in self.subratings if r > 0.0]
            if len(nonzero) == 0:
                return 0.0
            product = reduce(lambda x, y: x * y, nonzero, 1.0)
            root = len(nonzero)
            
        return product ** (1.0 / root)

    
class Reader:
    '''
    Class for parsing a string of text to obtain tags

    (it just turns the string to lowercase and splits it according to
    whitespaces and punctuation, identifying proper nouns and terminal words;
    different rules and formats other than plain text could be used)
    '''

    match_apostrophes = re.compile(r'`|’')
    match_paragraphs = re.compile(r'[\.\?!\t\n\r\f\v]+')
    match_phrases = re.compile(r'[,;:\(\)\[\]\{\}<>]+')
    match_words = re.compile(r'[\w\-\'_/&]+')
    
    def __call__(self, text):
        '''
        @param text: the string of text to be tagged

        @returns: a list of tags respecting the order in the text
        '''

        text = self.preprocess(text)

        # split by full stops, newlines, question marks...
        paragraphs = self.match_paragraphs.split(text)

        tags = []

        for par in paragraphs:
            # split by commas, colons, parentheses...
            phrases = self.match_phrases.split(par)

            if len(phrases) > 0:
                # first phrase of a paragraph
                words = self.match_words.findall(phrases[0])
                if len(words) > 1:
                    tags.append(Tag(words[0].lower()))
                    for w in words[1:-1]:
                        tags.append(Tag(w.lower(), proper=w[0].isupper()))
                    tags.append(Tag(words[-1].lower(),
                                    proper=words[-1][0].isupper(),
                                    terminal=True))
                elif len(words) == 1:
                    tags.append(Tag(words[0].lower(), terminal=True))

            # following phrases
            for phr in phrases[1:]:
                words = self.match_words.findall(phr)
                if len(words) > 1:
                    for w in words[:-1]:
                        tags.append(Tag(w.lower(), proper=w[0].isupper()))
                if len(words) > 0:
                    tags.append(Tag(words[-1].lower(),
                                    proper=words[-1][0].isupper(),
                                    terminal=True))

        return tags

    def preprocess(self, text):
        '''
        @param text: a string containing the text document to perform any
                     required transformation before splitting

        @returns:    the processed text
        '''
        
        text = self.match_apostrophes.sub('\'', text)
        return text

    
class Stemmer:
    '''
    Class for extracting the stem of a word
    
    (by default it uses a simple open-source implementation of Porter's
    algorithm; this can be improved a lot, so experimenting with different ones
    is advisable; nltk.stem provides different algorithms for many languages)
    '''

    match_contractions = re.compile(r'(\w+)\'(m|re|d|ve|s|ll|t)?')
    match_hyphens = re.compile(r'\b[\-_]\b')

    def __init__(self, stemmer=None):
        '''
        @param stemmer: an object or module with a 'stem' method (defaults to
                        stemming.porter2)

        @returns: a new L{Stemmer} object
        '''
        
        if not stemmer:
            from stemming import porter2
            stemmer = porter2
        self.stemmer = stemmer

    def __call__(self, tag):
        '''
        @param tag: the tag to be stemmed

        @returns: the stemmed tag
        '''

        string = self.preprocess(tag.string)
        tag.stem = self.stemmer.stem(string)
        return tag    
        
    def preprocess(self, string):
        '''
        @param string: a string to be treated before passing it to the stemmer

        @returns: the processed string
        '''

        # delete hyphens and underscores
        string = self.match_hyphens.sub('', string)
        
        # get rid of contractions and possessive forms
        match = self.match_contractions.match(string)
        if match: string = match.group(1)
        
        return string
    

class Rater:
    '''
    Class for estimating the relevance of tags

    (the default implementation uses TF (term frequency) multiplied by weight,
    but any other reasonable measure is fine; a quite rudimental heuristic
    tries to discard redundant tags)
    '''

    def __init__(self, weights, multitag_size=3):
        '''
        @param weights:       a dictionary of weights normalized in the
                              interval [0,1]
        @param multitag_size: maximum size of tags formed by multiple unit
                              tags

        @returns: a new L{Rater} object
        '''
        
        self.weights = weights
        self.multitag_size = multitag_size
        
    def __call__(self, tags):
        '''
        @param tags: a list of (preferably stemmed) tags

        @returns: a list of unique (multi)tags sorted by relevance
        '''

        self.rate_tags(tags)
        multitags = self.create_multitags(tags)

        # keep most frequent version of each tag
        clusters = collections.defaultdict(collections.Counter)
        proper = collections.defaultdict(int)
        ratings = collections.defaultdict(float)
        
        for t in multitags:
            clusters[t][t.string] += 1
            if t.proper:
                proper[t] += 1
                ratings[t] = max(ratings[t], t.rating)

        term_count = collections.Counter(multitags)
                
        for t, cnt in term_count.iteritems():
            t.string = clusters[t].most_common(1)[0][0]
            proper_freq = proper[t] / cnt
            if proper_freq >= 0.5:
                t.proper = True
                t.rating = ratings[t]
        
        # purge duplicates, one-character tags and stopwords
        unique_tags = set(t for t in term_count
                          if len(t.string) > 1 and t.rating > 0.0)
        # remove redundant tags
        for t, cnt in term_count.iteritems():
            words = t.stem.split()
            for l in xrange(1, len(words)):
                for i in xrange(len(words) - l + 1):
                    s = Tag(' '.join(words[i:i + l]))
                    relative_freq = cnt / term_count[s]
                    if ((relative_freq == 1.0 and t.proper) or
                        (relative_freq >= 0.5 and t.rating > 0.0)):
                        unique_tags.discard(s)
                    else:
                        unique_tags.discard(t)
        
        return sorted(unique_tags)

    def rate_tags(self, tags):
        '''
        @param tags: a list of tags to be assigned a rating
        '''
        
        term_count = collections.Counter(tags)
        
        for t in tags:
            # rating of a single tag is term frequency * weight
            t.rating = term_count[t] / len(tags) * self.weights.get(t.stem, 1.0)
    
    def create_multitags(self, tags):
        '''
        @param tags: a list of tags (respecting the order in the text)

        @returns: a list of multitags
        '''
        
        multitags = []
        
        for i in xrange(len(tags)):
            t = MultiTag(tags[i])
            multitags.append(t)
            for j in xrange(1, self.multitag_size):
                if t.terminal or i + j >= len(tags):
                    break
                else:
                    t = MultiTag(tags[i + j], t)
                    multitags.append(t)

        return multitags
    
    
class Tagger:
    '''
    Master class for tagging text documents

    (this is a simple interface that should allow convenient experimentation
    by using different classes as building blocks)
    '''

    def __init__(self, reader, stemmer, rater):
        '''
        @param reader: a L{Reader} object
        @param stemmer: a L{Stemmer} object
        @param rater: a L{Rater} object

        @returns: a new L{Tagger} object
        '''
        
        self.reader = reader
        self.stemmer = stemmer
        self.rater = rater

    def __call__(self, text, tags_number=5):
        '''
        @param text:        the string of text to be tagged
        @param tags_number: number of best tags to be returned

        Returns: a list of (hopefully) relevant tags
        ''' 

        tags = self.reader(text)
        tags = map(self.stemmer, tags)
        tags = self.rater(tags)

        return tags[:tags_number]



if __name__ == '__main__':

    import glob
    import pickle
    import sys

    if len(sys.argv) < 2:
        print 'No arguments given, running tests: '
        documents = glob.glob('tests/*')
    else:
        documents = sys.argv[1:]
    
    print 'Loading dictionary... '
    weights = pickle.load(open('data/dict.pkl', 'rb'))

    tagger = Tagger(Reader(), Stemmer(), Rater(weights))

    for doc in documents:
        with open(doc, 'r') as file:
            print 'Tags for ', doc, ':'
            print tagger(file.read())
          

########NEW FILE########
