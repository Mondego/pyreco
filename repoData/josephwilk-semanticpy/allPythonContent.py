__FILENAME__ = matrix_formatter
class MatrixFormatter:

    def __init__(self, matrix):
        self.matrix = matrix

    def pretty_print(self):
        """ Make the matrix look pretty """
        out = ""

        rows,cols = self.matrix.shape

        for row in xrange(0,rows):
            out += "["

            for col in xrange(0,cols):
                out += "%+0.2f "%self.matrix[row][col]
            out += "]\n"

        return out
########NEW FILE########
__FILENAME__ = parser
import os
from porter_stemmer import PorterStemmer
import os

class Parser:
    STOP_WORDS_FILE = '%s/../data/english.stop' %  os.path.dirname(os.path.realpath(__file__))

    stemmer = None
    stopwords = []

    def __init__(self, stopwords_io_stream = None):
    	self.stemmer = PorterStemmer()
        
        if(not stopwords_io_stream):
    	  stopwords_io_stream = open(Parser.STOP_WORDS_FILE, 'r')

        self.stopwords = stopwords_io_stream.read().split()

    def tokenise_and_remove_stop_words(self, document_list):
        if not document_list:
          return []
          
    	vocabulary_string = " ".join(document_list)
                
    	tokenised_vocabulary_list = self._tokenise(vocabulary_string)
    	clean_word_list = self._remove_stop_words(tokenised_vocabulary_list)
        return clean_word_list

    def _remove_stop_words(self, list):
    	""" Remove common words which have no search value """
    	return [word for word in list if word not in self.stopwords ]


    def _tokenise(self, string):
    	""" break string up into tokens and stem words """
    	string = self._clean(string)
    	words = string.split(" ")
		
    	return [self.stemmer.stem(word, 0, len(word)-1) for word in words]

    def _clean(self, string):
    	""" remove any nasty grammar tokens from string """
    	string = string.replace(".","")
    	string = string.replace("\s+"," ")
    	string = string.lower()
    	return string

########NEW FILE########
__FILENAME__ = porter_stemmer
#!/usr/bin/env python

"""Porter Stemming Algorithm
This is the Porter stemming algorithm, ported to Python from the
version coded up in ANSI C by the author. It may be be regarded
as canonical, in that it follows the algorithm presented in

Porter, 1980, An algorithm for suffix stripping, Program, Vol. 14,
no. 3, pp 130-137,

only differing from it at the points maked --DEPARTURE-- below.

See also http://www.tartarus.org/~martin/PorterStemmer

The algorithm as described in the paper could be exactly replicated
by adjusting the points of DEPARTURE, but this is barely necessary,
because (a) the points of DEPARTURE are definitely improvements, and
(b) no encoding of the Porter stemmer I have seen is anything like
as exact as this version, even with the points of DEPARTURE!

Vivake Gupta (v@nano.com)

Release 1: January 2001

Further adjustments by Santiago Bruno (bananabruno@gmail.com)
to allow word input not restricted to one word per line, leading
to:

release 2: July 2008
"""

import sys

class PorterStemmer:

    def __init__(self):
        """The main part of the stemming algorithm starts here.
        b is a buffer holding a word to be stemmed. The letters are in b[k0],
        b[k0+1] ... ending at b[k]. In fact k0 = 0 in this demo program. k is
        readjusted downwards as the stemming progresses. Zero termination is
        not in fact used in the algorithm.

        Note that only lower case sequences are stemmed. Forcing to lower case
        should be done before stem(...) is called.
        """

        self.b = ""  # buffer for word to be stemmed
        self.k = 0
        self.k0 = 0
        self.j = 0   # j is a general offset into the string

    def cons(self, i):
        """cons(i) is TRUE <=> b[i] is a consonant."""
        if self.b[i] == 'a' or self.b[i] == 'e' or self.b[i] == 'i' or self.b[i] == 'o' or self.b[i] == 'u':
            return 0
        if self.b[i] == 'y':
            if i == self.k0:
                return 1
            else:
                return (not self.cons(i - 1))
        return 1

    def m(self):
        """m() measures the number of consonant sequences between k0 and j.
        if c is a consonant sequence and v a vowel sequence, and <..>
        indicates arbitrary presence,

           <c><v>       gives 0
           <c>vc<v>     gives 1
           <c>vcvc<v>   gives 2
           <c>vcvcvc<v> gives 3
           ....
        """
        n = 0
        i = self.k0
        while 1:
            if i > self.j:
                return n
            if not self.cons(i):
                break
            i = i + 1
        i = i + 1
        while 1:
            while 1:
                if i > self.j:
                    return n
                if self.cons(i):
                    break
                i = i + 1
            i = i + 1
            n = n + 1
            while 1:
                if i > self.j:
                    return n
                if not self.cons(i):
                    break
                i = i + 1
            i = i + 1

    def vowelinstem(self):
        """vowelinstem() is TRUE <=> k0,...j contains a vowel"""
        for i in range(self.k0, self.j + 1):
            if not self.cons(i):
                return 1
        return 0

    def doublec(self, j):
        """doublec(j) is TRUE <=> j,(j-1) contain a double consonant."""
        if j < (self.k0 + 1):
            return 0
        if (self.b[j] != self.b[j-1]):
            return 0
        return self.cons(j)

    def cvc(self, i):
        """cvc(i) is TRUE <=> i-2,i-1,i has the form consonant - vowel - consonant
        and also if the second c is not w,x or y. this is used when trying to
        restore an e at the end of a short  e.g.

           cav(e), lov(e), hop(e), crim(e), but
           snow, box, tray.
        """
        if i < (self.k0 + 2) or not self.cons(i) or self.cons(i-1) or not self.cons(i-2):
            return 0
        ch = self.b[i]
        if ch == 'w' or ch == 'x' or ch == 'y':
            return 0
        return 1

    def ends(self, s):
        """ends(s) is TRUE <=> k0,...k ends with the string s."""
        length = len(s)
        if s[length - 1] != self.b[self.k]: # tiny speed-up
            return 0
        if length > (self.k - self.k0 + 1):
            return 0
        if self.b[self.k-length+1:self.k+1] != s:
            return 0
        self.j = self.k - length
        return 1

    def setto(self, s):
        """setto(s) sets (j+1),...k to the characters in the string s, readjusting k."""
        length = len(s)
        self.b = self.b[:self.j+1] + s + self.b[self.j+length+1:]
        self.k = self.j + length

    def r(self, s):
        """r(s) is used further down."""
        if self.m() > 0:
            self.setto(s)

    def step1ab(self):
        """step1ab() gets rid of plurals and -ed or -ing. e.g.

           caresses  ->  caress
           ponies    ->  poni
           ties      ->  ti
           caress    ->  caress
           cats      ->  cat

           feed      ->  feed
           agreed    ->  agree
           disabled  ->  disable

           matting   ->  mat
           mating    ->  mate
           meeting   ->  meet
           milling   ->  mill
           messing   ->  mess

           meetings  ->  meet
        """
        if self.b[self.k] == 's':
            if self.ends("sses"):
                self.k = self.k - 2
            elif self.ends("ies"):
                self.setto("i")
            elif self.b[self.k - 1] != 's':
                self.k = self.k - 1
        if self.ends("eed"):
            if self.m() > 0:
                self.k = self.k - 1
        elif (self.ends("ed") or self.ends("ing")) and self.vowelinstem():
            self.k = self.j
            if self.ends("at"):   self.setto("ate")
            elif self.ends("bl"): self.setto("ble")
            elif self.ends("iz"): self.setto("ize")
            elif self.doublec(self.k):
                self.k = self.k - 1
                ch = self.b[self.k]
                if ch == 'l' or ch == 's' or ch == 'z':
                    self.k = self.k + 1
            elif (self.m() == 1 and self.cvc(self.k)):
                self.setto("e")

    def step1c(self):
        """step1c() turns terminal y to i when there is another vowel in the stem."""
        if (self.ends("y") and self.vowelinstem()):
            self.b = self.b[:self.k] + 'i' + self.b[self.k+1:]

    def step2(self):
        """step2() maps double suffices to single ones.
        so -ization ( = -ize plus -ation) maps to -ize etc. note that the
        string before the suffix must give m() > 0.
        """
        if self.b[self.k - 1] == 'a':
            if self.ends("ational"):   self.r("ate")
            elif self.ends("tional"):  self.r("tion")
        elif self.b[self.k - 1] == 'c':
            if self.ends("enci"):      self.r("ence")
            elif self.ends("anci"):    self.r("ance")
        elif self.b[self.k - 1] == 'e':
            if self.ends("izer"):      self.r("ize")
        elif self.b[self.k - 1] == 'l':
            if self.ends("bli"):       self.r("ble") # --DEPARTURE--
            # To match the published algorithm, replace this phrase with
            #   if self.ends("abli"):      self.r("able")
            elif self.ends("alli"):    self.r("al")
            elif self.ends("entli"):   self.r("ent")
            elif self.ends("eli"):     self.r("e")
            elif self.ends("ousli"):   self.r("ous")
        elif self.b[self.k - 1] == 'o':
            if self.ends("ization"):   self.r("ize")
            elif self.ends("ation"):   self.r("ate")
            elif self.ends("ator"):    self.r("ate")
        elif self.b[self.k - 1] == 's':
            if self.ends("alism"):     self.r("al")
            elif self.ends("iveness"): self.r("ive")
            elif self.ends("fulness"): self.r("ful")
            elif self.ends("ousness"): self.r("ous")
        elif self.b[self.k - 1] == 't':
            if self.ends("aliti"):     self.r("al")
            elif self.ends("iviti"):   self.r("ive")
            elif self.ends("biliti"):  self.r("ble")
        elif self.b[self.k - 1] == 'g': # --DEPARTURE--
            if self.ends("logi"):      self.r("log")
        # To match the published algorithm, delete this phrase

    def step3(self):
        """step3() dels with -ic-, -full, -ness etc. similar strategy to step2."""
        if self.b[self.k] == 'e':
            if self.ends("icate"):     self.r("ic")
            elif self.ends("ative"):   self.r("")
            elif self.ends("alize"):   self.r("al")
        elif self.b[self.k] == 'i':
            if self.ends("iciti"):     self.r("ic")
        elif self.b[self.k] == 'l':
            if self.ends("ical"):      self.r("ic")
            elif self.ends("ful"):     self.r("")
        elif self.b[self.k] == 's':
            if self.ends("ness"):      self.r("")

    def step4(self):
        """step4() takes off -ant, -ence etc., in context <c>vcvc<v>."""
        if self.b[self.k - 1] == 'a':
            if self.ends("al"): pass
            else: return
        elif self.b[self.k - 1] == 'c':
            if self.ends("ance"): pass
            elif self.ends("ence"): pass
            else: return
        elif self.b[self.k - 1] == 'e':
            if self.ends("er"): pass
            else: return
        elif self.b[self.k - 1] == 'i':
            if self.ends("ic"): pass
            else: return
        elif self.b[self.k - 1] == 'l':
            if self.ends("able"): pass
            elif self.ends("ible"): pass
            else: return
        elif self.b[self.k - 1] == 'n':
            if self.ends("ant"): pass
            elif self.ends("ement"): pass
            elif self.ends("ment"): pass
            elif self.ends("ent"): pass
            else: return
        elif self.b[self.k - 1] == 'o':
            if self.ends("ion") and (self.b[self.j] == 's' or self.b[self.j] == 't'): pass
            elif self.ends("ou"): pass
            # takes care of -ous
            else: return
        elif self.b[self.k - 1] == 's':
            if self.ends("ism"): pass
            else: return
        elif self.b[self.k - 1] == 't':
            if self.ends("ate"): pass
            elif self.ends("iti"): pass
            else: return
        elif self.b[self.k - 1] == 'u':
            if self.ends("ous"): pass
            else: return
        elif self.b[self.k - 1] == 'v':
            if self.ends("ive"): pass
            else: return
        elif self.b[self.k - 1] == 'z':
            if self.ends("ize"): pass
            else: return
        else:
            return
        if self.m() > 1:
            self.k = self.j

    def step5(self):
        """step5() removes a final -e if m() > 1, and changes -ll to -l if
        m() > 1.
        """
        self.j = self.k
        if self.b[self.k] == 'e':
            a = self.m()
            if a > 1 or (a == 1 and not self.cvc(self.k-1)):
                self.k = self.k - 1
        if self.b[self.k] == 'l' and self.doublec(self.k) and self.m() > 1:
            self.k = self.k -1

    def stem(self, p, i, j):
        """In stem(p,i,j), p is a char pointer, and the string to be stemmed
        is from p[i] to p[j] inclusive. Typically i is zero and j is the
        offset to the last character of a string, (p[j+1] == '\0'). The
        stemmer adjusts the characters p[i] ... p[j] and returns the new
        end-point of the string, k. Stemming never increases word length, so
        i <= k <= j. To turn the stemmer into a module, declare 'stem' as
        extern, and delete the remainder of this file.
        """
        # copy the parameters into statics
        self.b = p
        self.k = j
        self.k0 = i
        if self.k <= self.k0 + 1:
            return self.b # --DEPARTURE--

        # With this line, strings of length 1 or 2 don't go through the
        # stemming process, although no mention is made of this in the
        # published algorithm. Remove the line to match the published
        # algorithm.

        self.step1ab()
        self.step1c()
        self.step2()
        self.step3()
        self.step4()
        self.step5()
        return self.b[self.k0:self.k+1]
########NEW FILE########
__FILENAME__ = LDA
from semanticpy.transform.transform import Transform
from vendor.onlineldavb.onlineldavb import OnlineLDA

class LDA(Transform):
    NUMBER_OF_TOPICS = 100

    def __init__(self, matrix):
        Transform.__init__(self, matrix)
        self.document_total = len(self.matrix)

    def transform(self):
        lda = OnlineLDA(vocab, NUMBER_OF_TOPICS, self.document_total, 1./NUMBER_OF_TOPICS, 1./NUMBER_OF_TOPICS, 1024., 0.7)


########NEW FILE########
__FILENAME__ = lsa
from scipy import linalg,dot

from transform import Transform

class LSA(Transform):
    """ Latent Semantic Analysis(LSA).
	    Apply transform to a document-term matrix to bring out latent relationships.
	    These are found by analysing relationships between the documents and the terms they 
	    contain.
    """

    def transform(self, dimensions=1):
		""" Calculate SVD of objects matrix: U . SIGMA . VT = MATRIX 
		    Reduce the dimension of sigma by specified factor producing sigma'. 
		    Then dot product the matrices:  U . SIGMA' . VT = MATRIX'
		"""
		rows,cols = self.matrix.shape

		if dimensions <= rows: #Its a valid reduction

			#Sigma comes out as a list rather than a matrix
			u,sigma,vt = linalg.svd(self.matrix)

			#Dimension reduction, build SIGMA'
			for index in xrange(rows - dimensions, rows):
				sigma[index] = 0

			#Reconstruct MATRIX'
			transformed_matrix = dot(dot(u, linalg.diagsvd(sigma, len(self.matrix), len(vt))) ,vt)

			return transformed_matrix

		else:
			print "dimension reduction cannot be greater than %s" % rows
########NEW FILE########
__FILENAME__ = tfidf
from math import *
from transform import Transform

class TFIDF(Transform):

    def __init__(self, matrix):
        Transform.__init__(self, matrix)
        self.document_total = len(self.matrix)


    def transform(self):
        """ Apply TermFrequency(tf)*inverseDocumentFrequency(idf) for each matrix element.
        This evaluates how important a word is to a document in a corpus

        With a document-term matrix: matrix[x][y]
        tf[x][y] = frequency of term y in document x / frequency of all terms in document x
        idf[x][y] = log( abs(total number of documents in corpus) / abs(number of documents with term y)  )
        Note: This is not the only way to calculate tf*idf
        """

        rows,cols = self.matrix.shape
        transformed_matrix = self.matrix.copy()

        for row in xrange(0, rows): #For each document

            word_total = reduce(lambda x, y: x+y, self.matrix[row] )
            word_total = float(word_total)

            for col in xrange(0, cols): #For each term
                transformed_matrix[row,col] = float(transformed_matrix[row,col])

                if transformed_matrix[row][col] != 0:
                    transformed_matrix[row,col] = self._tf_idf(row, col, word_total)

        return transformed_matrix


    def _tf_idf(self, row, col, word_total):
        term_frequency = self.matrix[row][col] / float(word_total)
        inverse_document_frequency = log(abs(self.document_total / float(self._get_term_document_occurences(col))))
        return term_frequency * inverse_document_frequency


    def _get_term_document_occurences(self, col):
        """ Find how many documents a term occurs in"""

        term_document_occurrences = 0

        rows, cols = self.matrix.shape

        for n in xrange(0,rows):
            if self.matrix[n][col] > 0: #Term appears in document
                term_document_occurrences +=1
        return term_document_occurrences

########NEW FILE########
__FILENAME__ = transform
from semanticpy.matrix_formatter import MatrixFormatter
from scipy import array

class Transform:
    def __init__(self, matrix):
        self.matrix = array(matrix, dtype=float)

    def __repr__(self):
        MatrixFormatter(self.matrix).pretty_print

########NEW FILE########
__FILENAME__ = vector_space
from semanticpy.parser import Parser
from semanticpy.transform.lsa import LSA
from semanticpy.transform.tfidf import TFIDF

import sys


try:
	from numpy import dot
	from numpy.linalg import norm
except:
	print "Error: Requires numpy from http://www.scipy.org/. Have you installed scipy?"
	sys.exit() 

class VectorSpace:
    """ A algebraic model for representing text documents as vectors of identifiers. 
    A document is represented as a vector. Each dimension of the vector corresponds to a 
    separate term. If a term occurs in the document, then the value in the vector is non-zero.
    """

    collection_of_document_term_vectors = []
    vector_index_to_keyword_mapping = []

    parser = None

    def __init__(self, documents = [], transforms = [TFIDF, LSA]):
    	self.collection_of_document_term_vectors = []
    	self.parser = Parser()
    	if len(documents) > 0:
    		self._build(documents, transforms)


    def related(self, document_id):
        """ find documents that are related to the document indexed by passed Id within the document Vectors"""
        ratings = [self._cosine(self.collection_of_document_term_vectors[document_id], document_vector) for document_vector in self.collection_of_document_term_vectors]
        ratings.sort(reverse = True)
        return ratings


    def search(self, searchList):
        """ search for documents that match based on a list of terms """
        queryVector = self._build_query_vector(searchList)

        ratings = [self._cosine(queryVector, documentVector) for documentVector in self.collection_of_document_term_vectors]
        ratings.sort(reverse=True)
        return ratings


    def _build(self, documents, transforms):
    	""" Create the vector space for the passed document strings """
    	self.vector_index_to_keyword_mapping = self._get_vector_keyword_index(documents)

    	matrix = [self._make_vector(document) for document in documents]
        matrix = reduce(lambda matrix,transform: transform(matrix).transform(), transforms, matrix)
        self.collection_of_document_term_vectors = matrix

    def _get_vector_keyword_index(self, document_list):
    	""" create the keyword associated to the position of the elements within the document vectors """
    	vocabulary_list = self.parser.tokenise_and_remove_stop_words(document_list)
        unique_vocabulary_list = self._remove_duplicates(vocabulary_list)
		
    	vector_index={}
    	offset=0
    	#Associate a position with the keywords which maps to the dimension on the vector used to represent this word
    	for word in unique_vocabulary_list:
    		vector_index[word] = offset
    		offset += 1
    	return vector_index  #(keyword:position)


    def _make_vector(self, word_string):
    	""" @pre: unique(vectorIndex) """

    	vector = [0] * len(self.vector_index_to_keyword_mapping)

    	word_list = self.parser.tokenise_and_remove_stop_words(word_string.split(" "))

    	for word in word_list:
            vector[self.vector_index_to_keyword_mapping[word]] += 1; #Use simple Term Count Model
    	return vector


    def _build_query_vector(self, term_list):
    	""" convert query string into a term vector """
    	query = self._make_vector(" ".join(term_list))
    	return query


    def _remove_duplicates(self, list):
        """ remove duplicates from a list """
        return set((item for item in list))
    
        
    def _cosine(self, vector1, vector2):
    	""" related documents j and q are in the concept space by comparing the vectors :
    		cosine  = ( V1 * V2 ) / ||V1|| x ||V2|| """
    	return float(dot(vector1,vector2) / (norm(vector1) * norm(vector2)))

########NEW FILE########
__FILENAME__ = test_semantic_py
from unittest import TestCase
from semanticpy.vector_space import VectorSpace
from nose.tools import *


class TestSemanticPy(TestCase):
    def setUp(self):
        self.documents = ["The cat in the hat disabled", "A cat is a fine pet ponies.", "Dogs and cats make good pets.","I haven't got a hat."]
    
    def it_should_search_test(self):
        vectorSpace = VectorSpace(self.documents)
  	
        eq_(vectorSpace.search(["cat"]), [0.14487566959813258, 0.1223402602604157, 0.07795622058966725, 0.05586504042763477])

    def it_should_find_return_similarity_rating_test(self):
        vectorSpace = VectorSpace(self.documents)

        eq_(vectorSpace.related(0), [1.0, 0.9922455760198575, 0.08122814162371816, 0.0762173599906487])
########NEW FILE########
__FILENAME__ = parser_test
from unittest import TestCase
from semanticpy.parser import Parser
from nose.tools import *

class ParserTest(TestCase):
  class FakeStopWords:
    def __init__(self, stop_words=''):
      self.stop_words = stop_words

    def read(self):
      return self.stop_words

  def create_parser_with_stopwords(self, words_string):
    return Parser(ParserTest.FakeStopWords(words_string))
  
  def create_parser(self):
    return Parser(ParserTest.FakeStopWords())
    
  def it_should_remove_the_stopwords_test(self):
    parser = self.create_parser_with_stopwords('a')
    
    parsed_words = parser.tokenise_and_remove_stop_words(["a", "sheep"])
    
    eq_(parsed_words, ["sheep"])
  
  def it_should_stem_words_test(self):
    parser = self.create_parser()
    
    parsed_words = parser.tokenise_and_remove_stop_words(["monkey"])
    
    eq_(parsed_words, ["monkei"])

  def it_should_remove_grammar_test(self):
    parser = self.create_parser()
    
    parsed_words = parser.tokenise_and_remove_stop_words(["sheep..."])
    
    eq_(parsed_words, ["sheep"])
    
  def it_should_return_an_empty_list__when_words_string_is_empty_test(self):
    parser = self.create_parser()
    
    parsed_words = parser.tokenise_and_remove_stop_words([])
    
    eq_(parsed_words, [])
########NEW FILE########
__FILENAME__ = lda_test
from unittest import TestCase
from semanticpy.transform.lda import LDA

class LDATest(TestCase):
    def it_should_do_lsa_test(self):
        pass
########NEW FILE########
__FILENAME__ = lsa_test
from unittest import TestCase
from semanticpy.transform.lsa import LSA
from nose.tools import *
import numpy

class LSATest(TestCase):
   """ """
   EPSILON = 4.90815310617e-09

   @classmethod
   def same(self, matrix1, matrix2):
    difference = matrix1 - matrix2
    max = numpy.max(difference)
    return (max <= LSATest.EPSILON)

   def it_should_do_lsa_test(self):
     matrix = [[0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0],
               [0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0],
               [1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
               [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]

     expected = [[ 0.02284739,  0.06123732,  1.20175485,  0.02284739,  0.02284739, 0.88232986,  0.03838993,  0.03838993,  0.82109254],
                 [-0.00490259,  0.98685971, -0.04329252, -0.00490259, -0.00490259, 1.02524964,  0.99176229,  0.99176229,  0.03838993],
                 [ 0.99708227,  0.99217968, -0.02576511,  0.99708227,  0.99708227, 1.01502707, -0.00490259, -0.00490259,  0.02284739],
                 [-0.0486125 , -0.13029496,  0.57072519, -0.0486125 , -0.0486125 , 0.25036735, -0.08168246, -0.08168246,  0.3806623 ]]

     expected = numpy.array(expected)
     lsa = LSA(matrix)
     new_matrix = lsa.transform()

     eq_(LSATest.same(new_matrix, expected), True)
########NEW FILE########
__FILENAME__ = tfidf_test
from unittest import TestCase
from semanticpy.transform.tfidf import TFIDF
from nose.tools import *
import numpy

class TFIDFTest(TestCase):
    """ """
    EPSILON = 4.90815310617e-09


    @classmethod
    def same(self, matrix1, matrix2):
        difference = matrix1 - matrix2
        max = numpy.max(difference)
        return (max <= TFIDFTest.EPSILON)


    def it_should_do_tfidf_test(self):
        matrix = [[0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0],
                  [0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0],
                  [1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
                  [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]

        expected = [[0.,         0.,             0.23104906, 0.,         0.,         0.09589402, 0.,         0.,         0.46209812],
                    [0.,         0.1732868,      0.,         0.,         0.,         0.07192052, 0.34657359, 0.34657359, 0.        ],
                    [0.27725887, 0.13862944,     0.,         0.27725887, 0.27725887, 0.05753641, 0.,         0.,         0.        ],
                    [0.,         0.,             0.69314718, 0.,         0.,         0.,         0.,         0.,         0.        ]]

        expected = numpy.array(expected)

        tfidf = TFIDF(matrix)
        new_matrix = tfidf.transform()

        eq_(TFIDFTest.same(new_matrix, expected), True)

########NEW FILE########
__FILENAME__ = vector_space_test
from unittest import TestCase
from semanticpy.vector_space import VectorSpace
from pprint import pprint
from nose.tools import *

class VectorSpaceTest(TestCase):

    documents = ["cat", "cat dog","hat"]

    def it_should_search_test(self):
        vector_space = VectorSpace(self.documents, transforms = [])

        eq_(vector_space.search(["cat"]), [1.0, 0.7071067811865475, 0.0])

    def it_should_find_related_test(self):
        vector_space = VectorSpace(self.documents)

        eq_(vector_space.related(0), [1.0000000000000002, 0.9999999999999998, 0.0])
########NEW FILE########
__FILENAME__ = onlineldavb
# onlineldavb.py: Package of functions for fitting Latent Dirichlet
# Allocation (LDA) with online variational Bayes (VB).
#
# Copyright (C) 2010  Matthew D. Hoffman
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, re, time, string
import numpy as n
from scipy.special import gammaln, psi

n.random.seed(100000001)
meanchangethresh = 0.001

def dirichlet_expectation(alpha):
    """
    For a vector theta ~ Dir(alpha), computes E[log(theta)] given alpha.
    """
    if (len(alpha.shape) == 1):
        return(psi(alpha) - psi(n.sum(alpha)))
    return(psi(alpha) - psi(n.sum(alpha, 1))[:, n.newaxis])

def parse_doc_list(docs, vocab):
    """
    Parse a document into a list of word ids and a list of counts,
    or parse a set of documents into two lists of lists of word ids
    and counts.

    Arguments: 
    docs:  List of D documents. Each document must be represented as
           a single string. (Word order is unimportant.) Any
           words not in the vocabulary will be ignored.
    vocab: Dictionary mapping from words to integer ids.

    Returns a pair of lists of lists. 

    The first, wordids, says what vocabulary tokens are present in
    each document. wordids[i][j] gives the jth unique token present in
    document i. (Don't count on these tokens being in any particular
    order.)

    The second, wordcts, says how many times each vocabulary token is
    present. wordcts[i][j] is the number of times that the token given
    by wordids[i][j] appears in document i.
    """
    if (type(docs).__name__ == 'str'):
        temp = list()
        temp.append(docs)
        docs = temp

    D = len(docs)
    
    wordids = list()
    wordcts = list()
    for d in range(0, D):
        docs[d] = docs[d].lower()
        docs[d] = re.sub(r'-', ' ', docs[d])
        docs[d] = re.sub(r'[^a-z ]', '', docs[d])
        docs[d] = re.sub(r' +', ' ', docs[d])
        words = string.split(docs[d])
        ddict = dict()
        for word in words:
            if (word in vocab):
                wordtoken = vocab[word]
                if (not wordtoken in ddict):
                    ddict[wordtoken] = 0
                ddict[wordtoken] += 1
        wordids.append(ddict.keys())
        wordcts.append(ddict.values())

    return((wordids, wordcts))

class OnlineLDA:
    """
    Implements online VB for LDA as described in (Hoffman et al. 2010).
    """

    def __init__(self, vocab, K, D, alpha, eta, tau0, kappa):
        """
        Arguments:
        K: Number of topics
        vocab: A set of words to recognize. When analyzing documents, any word
           not in this set will be ignored.
        D: Total number of documents in the population. For a fixed corpus,
           this is the size of the corpus. In the truly online setting, this
           can be an estimate of the maximum number of documents that
           could ever be seen.
        alpha: Hyperparameter for prior on weight vectors theta
        eta: Hyperparameter for prior on topics beta
        tau0: A (positive) learning parameter that downweights early iterations
        kappa: Learning rate: exponential decay rate---should be between
             (0.5, 1.0] to guarantee asymptotic convergence.

        Note that if you pass the same set of D documents in every time and
        set kappa=0 this class can also be used to do batch VB.
        """
        self._vocab = dict()
        for word in vocab:
            word = word.lower()
            word = re.sub(r'[^a-z]', '', word)
            self._vocab[word] = len(self._vocab)

        self._K = K
        self._W = len(self._vocab)
        self._D = D
        self._alpha = alpha
        self._eta = eta
        self._tau0 = tau0 + 1
        self._kappa = kappa
        self._updatect = 0

        # Initialize the variational distribution q(beta|lambda)
        self._lambda = 1*n.random.gamma(100., 1./100., (self._K, self._W))
        self._Elogbeta = dirichlet_expectation(self._lambda)
        self._expElogbeta = n.exp(self._Elogbeta)

    def do_e_step(self, docs):
        """
        Given a mini-batch of documents, estimates the parameters
        gamma controlling the variational distribution over the topic
        weights for each document in the mini-batch.

        Arguments:
        docs:  List of D documents. Each document must be represented
               as a string. (Word order is unimportant.) Any
               words not in the vocabulary will be ignored.

        Returns a tuple containing the estimated values of gamma,
        as well as sufficient statistics needed to update lambda.
        """
        # This is to handle the case where someone just hands us a single
        # document, not in a list.
        if (type(docs).__name__ == 'string'):
            temp = list()
            temp.append(docs)
            docs = temp

        (wordids, wordcts) = parse_doc_list(docs, self._vocab)
        batchD = len(docs)

        # Initialize the variational distribution q(theta|gamma) for
        # the mini-batch
        gamma = 1*n.random.gamma(100., 1./100., (batchD, self._K))
        Elogtheta = dirichlet_expectation(gamma)
        expElogtheta = n.exp(Elogtheta)

        sstats = n.zeros(self._lambda.shape)
        # Now, for each document d update that document's gamma and phi
        it = 0
        meanchange = 0
        for d in range(0, batchD):
            # These are mostly just shorthand (but might help cache locality)
            ids = wordids[d]
            cts = wordcts[d]
            gammad = gamma[d, :]
            Elogthetad = Elogtheta[d, :]
            expElogthetad = expElogtheta[d, :]
            expElogbetad = self._expElogbeta[:, ids]
            # The optimal phi_{dwk} is proportional to 
            # expElogthetad_k * expElogbetad_w. phinorm is the normalizer.
            phinorm = n.dot(expElogthetad, expElogbetad) + 1e-100
            # Iterate between gamma and phi until convergence
            for it in range(0, 100):
                lastgamma = gammad
                # We represent phi implicitly to save memory and time.
                # Substituting the value of the optimal phi back into
                # the update for gamma gives this update. Cf. Lee&Seung 2001.
                gammad = self._alpha + expElogthetad * \
                    n.dot(cts / phinorm, expElogbetad.T)
                Elogthetad = dirichlet_expectation(gammad)
                expElogthetad = n.exp(Elogthetad)
                phinorm = n.dot(expElogthetad, expElogbetad) + 1e-100
                # If gamma hasn't changed much, we're done.
                meanchange = n.mean(abs(gammad - lastgamma))
                if (meanchange < meanchangethresh):
                    break
            gamma[d, :] = gammad
            # Contribution of document d to the expected sufficient
            # statistics for the M step.
            sstats[:, ids] += n.outer(expElogthetad.T, cts/phinorm)

        # This step finishes computing the sufficient statistics for the
        # M step, so that
        # sstats[k, w] = \sum_d n_{dw} * phi_{dwk} 
        # = \sum_d n_{dw} * exp{Elogtheta_{dk} + Elogbeta_{kw}} / phinorm_{dw}.
        sstats = sstats * self._expElogbeta

        return((gamma, sstats))

    def update_lambda(self, docs):
        """
        First does an E step on the mini-batch given in wordids and
        wordcts, then uses the result of that E step to update the
        variational parameter matrix lambda.

        Arguments:
        docs:  List of D documents. Each document must be represented
               as a string. (Word order is unimportant.) Any
               words not in the vocabulary will be ignored.

        Returns gamma, the parameters to the variational distribution
        over the topic weights theta for the documents analyzed in this
        update.

        Also returns an estimate of the variational bound for the
        entire corpus for the OLD setting of lambda based on the
        documents passed in. This can be used as a (possibly very
        noisy) estimate of held-out likelihood.
        """

        # rhot will be between 0 and 1, and says how much to weight
        # the information we got from this mini-batch.
        rhot = pow(self._tau0 + self._updatect, -self._kappa)
        self._rhot = rhot
        # Do an E step to update gamma, phi | lambda for this
        # mini-batch. This also returns the information about phi that
        # we need to update lambda.
        (gamma, sstats) = self.do_e_step(docs)
        # Estimate held-out likelihood for current values of lambda.
        bound = self.approx_bound(docs, gamma)
        # Update lambda based on documents.
        self._lambda = self._lambda * (1-rhot) + \
            rhot * (self._eta + self._D * sstats / len(docs))
        self._Elogbeta = dirichlet_expectation(self._lambda)
        self._expElogbeta = n.exp(self._Elogbeta)
        self._updatect += 1

        return(gamma, bound)

    def approx_bound(self, docs, gamma):
        """
        Estimates the variational bound over *all documents* using only
        the documents passed in as "docs." gamma is the set of parameters
        to the variational distribution q(theta) corresponding to the
        set of documents passed in.

        The output of this function is going to be noisy, but can be
        useful for assessing convergence.
        """

        # This is to handle the case where someone just hands us a single
        # document, not in a list.
        if (type(docs).__name__ == 'string'):
            temp = list()
            temp.append(docs)
            docs = temp

        (wordids, wordcts) = parse_doc_list(docs, self._vocab)
        batchD = len(docs)

        score = 0
        Elogtheta = dirichlet_expectation(gamma)
        expElogtheta = n.exp(Elogtheta)

        # E[log p(docs | theta, beta)]
        for d in range(0, batchD):
            gammad = gamma[d, :]
            ids = wordids[d]
            cts = n.array(wordcts[d])
            phinorm = n.zeros(len(ids))
            for i in range(0, len(ids)):
                temp = Elogtheta[d, :] + self._Elogbeta[:, ids[i]]
                tmax = max(temp)
                phinorm[i] = n.log(sum(n.exp(temp - tmax))) + tmax
            score += n.sum(cts * phinorm)
#             oldphinorm = phinorm
#             phinorm = n.dot(expElogtheta[d, :], self._expElogbeta[:, ids])
#             print oldphinorm
#             print n.log(phinorm)
#             score += n.sum(cts * n.log(phinorm))

        # E[log p(theta | alpha) - log q(theta | gamma)]
        score += n.sum((self._alpha - gamma)*Elogtheta)
        score += n.sum(gammaln(gamma) - gammaln(self._alpha))
        score += sum(gammaln(self._alpha*self._K) - gammaln(n.sum(gamma, 1)))

        # Compensate for the subsampling of the population of documents
        score = score * self._D / len(docs)

        # E[log p(beta | eta) - log q (beta | lambda)]
        score = score + n.sum((self._eta-self._lambda)*self._Elogbeta)
        score = score + n.sum(gammaln(self._lambda) - gammaln(self._eta))
        score = score + n.sum(gammaln(self._eta*self._W) - 
                              gammaln(n.sum(self._lambda, 1)))

        return(score)

########NEW FILE########
__FILENAME__ = onlinewikipedia
#!/usr/bin/python

# onlinewikipedia.py: Demonstrates the use of online VB for LDA to
# analyze a bunch of random Wikipedia articles.
#
# Copyright (C) 2010  Matthew D. Hoffman
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import cPickle, string, numpy, getopt, sys, random, time, re, pprint

import onlineldavb
import wikirandom

def main():
    """
    Downloads and analyzes a bunch of random Wikipedia articles using
    online VB for LDA.
    """

    # The number of documents to analyze each iteration
    batchsize = 64
    # The total number of documents in Wikipedia
    D = 3.3e6
    # The number of topics
    K = 100

    # How many documents to look at
    if (len(sys.argv) < 2):
        documentstoanalyze = int(D/batchsize)
    else:
        documentstoanalyze = int(sys.argv[1])

    # Our vocabulary
    vocab = file('./dictnostops.txt').readlines()
    W = len(vocab)

    # Initialize the algorithm with alpha=1/K, eta=1/K, tau_0=1024, kappa=0.7
    olda = onlineldavb.OnlineLDA(vocab, K, D, 1./K, 1./K, 1024., 0.7)
    # Run until we've seen D documents. (Feel free to interrupt *much*
    # sooner than this.)
    for iteration in range(0, documentstoanalyze):
        # Download some articles
        (docset, articlenames) = \
            wikirandom.get_random_wikipedia_articles(batchsize)
        # Give them to online LDA
        (gamma, bound) = olda.update_lambda(docset)
        # Compute an estimate of held-out perplexity
        (wordids, wordcts) = onlineldavb.parse_doc_list(docset, olda._vocab)
        perwordbound = bound * len(docset) / (D * sum(map(sum, wordcts)))
        print '%d:  rho_t = %f,  held-out perplexity estimate = %f' % \
            (iteration, olda._rhot, numpy.exp(-perwordbound))

        # Save lambda, the parameters to the variational distributions
        # over topics, and gamma, the parameters to the variational
        # distributions over topic weights for the articles analyzed in
        # the last iteration.
        if (iteration % 10 == 0):
            numpy.savetxt('lambda-%d.dat' % iteration, olda._lambda)
            numpy.savetxt('gamma-%d.dat' % iteration, gamma)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = printtopics
#!/usr/bin/python

# printtopics.py: Prints the words that are most prominent in a set of
# topics.
#
# Copyright (C) 2010  Matthew D. Hoffman
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, os, re, random, math, urllib2, time, cPickle
import numpy

import onlineldavb

def main():
    """
    Displays topics fit by onlineldavb.py. The first column gives the
    (expected) most prominent words in the topics, the second column
    gives their (expected) relative prominence.
    """
    vocab = str.split(file(sys.argv[1]).read())
    testlambda = numpy.loadtxt(sys.argv[2])

    for k in range(0, len(testlambda)):
        lambdak = list(testlambda[k, :])
        lambdak = lambdak / sum(lambdak)
        temp = zip(lambdak, range(0, len(lambdak)))
        temp = sorted(temp, key = lambda x: x[0], reverse=True)
        print 'topic %d:' % (k)
        # feel free to change the "53" here to whatever fits your screen nicely.
        for i in range(0, 53):
            print '%20s  \t---\t  %.4f' % (vocab[temp[i][1]], temp[i][0])
        print

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = wikirandom
# wikirandom.py: Functions for downloading random articles from Wikipedia
#
# Copyright (C) 2010  Matthew D. Hoffman
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, urllib2, re, string, time, threading

def get_random_wikipedia_article():
    """
    Downloads a randomly selected Wikipedia article (via
    http://en.wikipedia.org/wiki/Special:Random) and strips out (most
    of) the formatting, links, etc. 

    This function is a bit simpler and less robust than the code that
    was used for the experiments in "Online VB for LDA."
    """
    failed = True
    while failed:
        articletitle = None
        failed = False
        try:
            req = urllib2.Request('http://en.wikipedia.org/wiki/Special:Random',
                                  None, { 'User-Agent' : 'x'})
            f = urllib2.urlopen(req)
            while not articletitle:
                line = f.readline()
                result = re.search(r'title="Edit this page" href="/w/index.php\?title=(.*)\&amp;action=edit" /\>', line)
                if (result):
                    articletitle = result.group(1)
                    break
                elif (len(line) < 1):
                    sys.exit(1)

            req = urllib2.Request('http://en.wikipedia.org/w/index.php?title=Special:Export/%s&action=submit' \
                                      % (articletitle),
                                  None, { 'User-Agent' : 'x'})
            f = urllib2.urlopen(req)
            all = f.read()
        except (urllib2.HTTPError, urllib2.URLError):
            print 'oops. there was a failure downloading %s. retrying...' \
                % articletitle
            failed = True
            continue
        print 'downloaded %s. parsing...' % articletitle

        try:
            all = re.search(r'<text.*?>(.*)</text', all, flags=re.DOTALL).group(1)
            all = re.sub(r'\n', ' ', all)
            all = re.sub(r'\{\{.*?\}\}', r'', all)
            all = re.sub(r'\[\[Category:.*', '', all)
            all = re.sub(r'==\s*[Ss]ource\s*==.*', '', all)
            all = re.sub(r'==\s*[Rr]eferences\s*==.*', '', all)
            all = re.sub(r'==\s*[Ee]xternal [Ll]inks\s*==.*', '', all)
            all = re.sub(r'==\s*[Ee]xternal [Ll]inks and [Rr]eferences==\s*', '', all)
            all = re.sub(r'==\s*[Ss]ee [Aa]lso\s*==.*', '', all)
            all = re.sub(r'http://[^\s]*', '', all)
            all = re.sub(r'\[\[Image:.*?\]\]', '', all)
            all = re.sub(r'Image:.*?\|', '', all)
            all = re.sub(r'\[\[.*?\|*([^\|]*?)\]\]', r'\1', all)
            all = re.sub(r'\&lt;.*?&gt;', '', all)
        except:
            # Something went wrong, try again. (This is bad coding practice.)
            print 'oops. there was a failure parsing %s. retrying...' \
                % articletitle
            failed = True
            continue

    return(all, articletitle)

class WikiThread(threading.Thread):
    articles = list()
    articlenames = list()
    lock = threading.Lock()

    def run(self):
        (article, articlename) = get_random_wikipedia_article()
        WikiThread.lock.acquire()
        WikiThread.articles.append(article)
        WikiThread.articlenames.append(articlename)
        WikiThread.lock.release()

def get_random_wikipedia_articles(n):
    """
    Downloads n articles in parallel from Wikipedia and returns lists
    of their names and contents. Much faster than calling
    get_random_wikipedia_article() serially.
    """
    maxthreads = 8
    WikiThread.articles = list()
    WikiThread.articlenames = list()
    wtlist = list()
    for i in range(0, n, maxthreads):
        print 'downloaded %d/%d articles...' % (i, n)
        for j in range(i, min(i+maxthreads, n)):
            wtlist.append(WikiThread())
            wtlist[len(wtlist)-1].start()
        for j in range(i, min(i+maxthreads, n)):
            wtlist[j].join()
    return (WikiThread.articles, WikiThread.articlenames)

if __name__ == '__main__':
    t0 = time.time()

    (articles, articlenames) = get_random_wikipedia_articles(1)
    for i in range(0, len(articles)):
        print articlenames[i]

    t1 = time.time()
    print 'took %f' % (t1 - t0)

########NEW FILE########
