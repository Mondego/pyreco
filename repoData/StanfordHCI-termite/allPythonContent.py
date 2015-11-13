__FILENAME__ = execute
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import ConfigParser
import logging

import time
import os
from pipeline.tokenize import Tokenize
from pipeline.import_mallet import ImportMallet
from pipeline.import_stmt import ImportStmt
from pipeline.compute_saliency import ComputeSaliency
from pipeline.compute_similarity import ComputeSimilarity
from pipeline.compute_seriation import ComputeSeriation
from pipeline.prepare_data_for_client import PrepareDataForClient

class Execute( object ):

	"""
	Runs entire data processing pipeline and sets up client.
	
	Execute data processing scripts in order:
		1. tokenize.py:				Tokenize corpus
		2. train_stmt/mallet.py:	Train model
		3. compute_saliency.py:		Compute term saliency
		4. compute_similarity.py:	Compute term similarity
		5. compute_seriation.py:	Seriates terms
		6. prepare_data_for_client.py:	Generates datafiles for client
		7. prepare_vis_for_client.py:	Copies necessary scripts for client
	
	Input is configuration file specifying target corpus and destination directory.
	
	Creates multiple directories that store files from each stage of the pipeline. 
	Among the directories is the public_html directory that holds all client files.
	"""
	
	DEFAULT_NUM_TOPICS = 25
	
	def __init__( self, logging_level ):
		self.logger = logging.getLogger( 'Execute' )
		self.logger.setLevel( logging_level )
		handler = logging.StreamHandler( sys.stderr )
		handler.setLevel( logging_level )
		self.logger.addHandler( handler )
	
	def execute( self, corpus_format, corpus_path, tokenization, model_library, model_path, data_path, num_topics, number_of_seriated_terms ):
		
		assert corpus_format is not None
		assert corpus_path is not None
		assert model_library is not None
		assert model_library == 'stmt' or model_library == 'mallet'
		assert model_path is not None
		assert data_path is not None
		if num_topics is None:
			num_topics = Execute.DEFAULT_NUM_TOPICS
		assert number_of_seriated_terms is not None
		
		self.logger.info( '--------------------------------------------------------------------------------' )
		self.logger.info( 'Tokenizing source corpus...'                                                      )
		self.logger.info( '    corpus_path = %s (%s)', corpus_path, corpus_format                            )
		self.logger.info( '    model_path = %s (%s)', model_path, model_library                              )
		self.logger.info( '    data_path = %s', data_path                                                    )
		self.logger.info( '    num_topics = %d', num_topics                                                  )
		self.logger.info( '    number_of_seriated_terms = %s', number_of_seriated_terms                      )
		self.logger.info( '--------------------------------------------------------------------------------' )
		self.logger.info( 'Current time = {}'.format( time.ctime() ) )
		
		Tokenize( self.logger.level ).execute( corpus_format, corpus_path, data_path, tokenization )
		self.logger.info( 'Current time = {}'.format( time.ctime() ) )
		
		if model_library == 'stmt':
			command = 'pipeline/train_stmt.sh {} {} {}'.format( data_path + '/tokens/tokens.txt', model_path, num_topics )
			os.system( command )
			ImportStmt( self.logger.level ).execute( model_library, model_path, data_path )
		if model_library == 'mallet':
			command = 'pipeline/train_mallet.sh {} {} {}'.format( data_path + '/tokens/tokens.txt', model_path, num_topics )
			os.system( command )
			ImportMallet( self.logger.level ).execute( model_library, model_path, data_path )
		self.logger.info( 'Current time = {}'.format( time.ctime() ) )
		
		ComputeSaliency( self.logger.level ).execute( data_path )
		self.logger.info( 'Current time = {}'.format( time.ctime() ) )

		ComputeSimilarity( self.logger.level ).execute( data_path )
		self.logger.info( 'Current time = {}'.format( time.ctime() ) )

		ComputeSeriation( self.logger.level ).execute( data_path, number_of_seriated_terms )
		self.logger.info( 'Current time = {}'.format( time.ctime() ) )

		PrepareDataForClient( self.logger.level ).execute( data_path )
		self.logger.info( 'Current time = {}'.format( time.ctime() ) )
		
		command = 'pipeline/prepare_vis_for_client.sh {}'.format( data_path )
		os.system( command )
		self.logger.info( 'Current time = {}'.format( time.ctime() ) )

#-------------------------------------------------------------------------------#

def main():
	parser = argparse.ArgumentParser( description = 'Prepare data for Termite.' )
	parser.add_argument( 'config_file'    , type = str, help = 'Termite configuration file.' )
	parser.add_argument( '--corpus-format', type = str, dest = 'corpus_format', help = 'Override corpus format in the config file.' )
	parser.add_argument( '--corpus-path'  , type = str, dest = 'corpus_path'  , help = 'Override corpus path in the config file.' )
	parser.add_argument( '--model-library', type = str, dest = 'model_library', help = 'Override model library in the config file.' )
	parser.add_argument( '--model-path'   , type = str, dest = 'model_path'   , help = 'Override model path in the config file.' )
	parser.add_argument( '--num-topcis'   , type = int, dest = 'num_topics'   , help = 'Override number of topics in the config file.' )
	parser.add_argument( '--data-path'    , type = str, dest = 'data_path'    , help = 'Override data path in the config file.' )
	parser.add_argument( '--number-of-seriated-terms', type = int, dest = 'number_of_seriated_terms', help = 'Override the number of terms to seriate.' )
	parser.add_argument( '--logging'      , type = int, dest = 'logging'      , help = 'Override logging level specified in config file.' )
	args = parser.parse_args()
	
	corpus_format = None
	corpus_path = None
	model_library = None
	model_path = None
	data_path = None
	num_topics = None
	number_of_seriated_terms = None
	logging_level = 20
	
	# Read in default values from the configuration file
	config = ConfigParser.RawConfigParser()
	config.read( args.config_file )
	if config.has_section( 'Corpus' ) and config.has_option( 'Corpus', 'format' ):
		corpus_format = config.get( 'Corpus', 'format' )
	if config.has_section( 'Corpus' ) and config.has_option( 'Corpus', 'path' ):
		corpus_path = config.get( 'Corpus', 'path' )
	if config.has_section( 'Corpus' ) and config.has_option( 'Corpus', 'tokenization' ):
		tokenization = config.get( 'Corpus', 'tokenization' )
	if config.has_section( 'TopicModel' ) and config.has_option( 'TopicModel', 'library' ):
		model_library = config.get( 'TopicModel', 'library' )
	if config.has_section( 'TopicModel' ) and config.has_option( 'TopicModel', 'path' ):
		model_path = config.get( 'TopicModel', 'path' )
	if config.has_section( 'TopicModel' ) and config.has_option( 'TopicModel', 'num_topics' ):
		num_topics = config.getint( 'TopicModel', 'num_topics' )
	if config.has_section( 'Termite' ) and config.has_option( 'Termite', 'path' ):
		data_path = config.get( 'Termite', 'path' )
	if config.has_section( 'Termite' ) and config.has_option( 'Termite', 'number_of_seriated_terms' ):
		number_of_seriated_terms = config.getint( 'Termite', 'number_of_seriated_terms' )
	if config.has_section( 'Misc' ) and config.has_option( 'Misc', 'logging' ):
		logging_level = config.getint( 'Misc', 'logging' )
	
	# Read in user-specifiec values from the program arguments
	if args.corpus_format is not None:
		corpus_format = args.corpus_format
	if args.corpus_path is not None:
		corpus_path = args.corpus_path
	if args.model_library is not None:
		model_library = args.model_library
	if args.model_path is not None:
		model_path = args.model_path
	if args.num_topics is not None:
		num_topics = args.num_topics
	if args.data_path is not None:
		data_path = args.data_path
	if args.number_of_seriated_terms is not None:
		number_of_seriated_terms = args.number_of_seriated_terms
	if args.logging is not None:
		logging_level = args.logging
	
	Execute( logging_level ).execute( corpus_format, corpus_path, tokenization, model_library, model_path, data_path, num_topics, number_of_seriated_terms )

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = api_utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
from io_utils import CheckAndMakeDirs
from io_utils import ReadAsList, ReadAsVector, ReadAsMatrix, ReadAsSparseVector, ReadAsSparseMatrix, ReadAsJson
from io_utils import WriteAsList, WriteAsVector, WriteAsMatrix, WriteAsSparseVector, WriteAsSparseMatrix, WriteAsJson, WriteAsTabDelimited
from utf8_utils import UnicodeReader, UnicodeWriter

class DocumentsAPI( object ):
	ACCEPTABLE_FORMATS = frozenset( [ 'file' ] )
	
	def __init__( self, format, path ):
		assert format in DocumentsAPI.ACCEPTABLE_FORMATS
		self.format = format
		self.path = path
		self.data = []
	
	def read( self ):
		self.data = {}
		filename = self.path
		with open( filename, 'r' ) as f:
			lines = f.read().decode( 'utf-8', 'ignore' ).splitlines()
			for line in lines:
				docID, docContent = line.split( '\t' )
				self.data[ docID ] = docContent

class TokensAPI( object ):
	SUBFOLDER = 'tokens'
	TOKENS = 'tokens.txt'
	
	def __init__( self, path ):
		self.path = '{}/{}/'.format( path, TokensAPI.SUBFOLDER )
		self.data = {}
	
	def read( self ):
		self.data = {}
		filename = self.path + TokensAPI.TOKENS
		with open( filename, 'r' ) as f:
			lines = UnicodeReader( f )
			for ( docID, docTokens ) in lines:
				self.data[ docID ] = docTokens.split( ' ' )
	
	def write( self ):
		CheckAndMakeDirs( self.path )
		filename = self.path + TokensAPI.TOKENS
		with open( filename, 'w' ) as f:
			writer = UnicodeWriter( f )
			for ( docID, docTokens ) in self.data.iteritems():
				writer.writerow( [ docID, ' '.join(docTokens) ] )

class ModelAPI( object ):
	SUBFOLDER = 'model'
	TOPIC_INDEX = 'topic-index.txt'
	TERM_INDEX = 'term-index.txt'
	TERM_TOPIC_MATRIX = 'term-topic-matrix.txt'
	
	def __init__( self, path ):
		self.path = '{}/{}/'.format( path, ModelAPI.SUBFOLDER )
		self.topic_index = []
		self.term_index = []
		self.topic_count = 0
		self.term_count = 0
		self.term_topic_matrix = []
	
	def read( self ):
		self.topic_index = ReadAsList( self.path + ModelAPI.TOPIC_INDEX )
		self.term_index = ReadAsList( self.path + ModelAPI.TERM_INDEX )
		self.term_topic_matrix = ReadAsMatrix( self.path + ModelAPI.TERM_TOPIC_MATRIX )
		self.verify()
	
	def verify( self ):
		self.topic_count = len( self.topic_index )
		self.term_count = len( self.term_index )
		
		assert self.term_count == len( self.term_topic_matrix )
		for row in self.term_topic_matrix:
			assert self.topic_count == len(row)
	
	def write( self ):
		self.verify()
		CheckAndMakeDirs( self.path )
		WriteAsList( self.topic_index, self.path + ModelAPI.TOPIC_INDEX )
		WriteAsList( self.term_index, self.path + ModelAPI.TERM_INDEX )
		WriteAsMatrix( self.term_topic_matrix, self.path + ModelAPI.TERM_TOPIC_MATRIX )

class SaliencyAPI( object ):
	SUBFOLDER = 'saliency'
	TOPIC_WEIGHTS = 'topic-info.json'
	TOPIC_WEIGHTS_TXT = 'topic-info.txt'
	TOPIC_WEIGHTS_FIELDS = [ 'term', 'saliency', 'frequency', 'distinctiveness', 'rank', 'visibility' ]
	TERM_SALIENCY = 'term-info.json'
	TERM_SALIENCY_TXT = 'term-info.txt'
	TERM_SALIENCY_FIELDS = [ 'topic', 'weight' ]
	
	def __init__( self, path ):
		self.path = '{}/{}/'.format( path, SaliencyAPI.SUBFOLDER )
		self.term_info = {}
		self.topic_info = {}
	
	def read( self ):
		self.term_info = ReadAsJson( self.path + SaliencyAPI.TERM_SALIENCY )
		self.topic_info = ReadAsJson( self.path + SaliencyAPI.TOPIC_WEIGHTS )
	
	def write( self ):
		CheckAndMakeDirs( self.path )
		WriteAsJson( self.term_info, self.path + SaliencyAPI.TERM_SALIENCY )
		WriteAsTabDelimited( self.term_info, self.path + SaliencyAPI.TERM_SALIENCY_TXT, SaliencyAPI.TOPIC_WEIGHTS_FIELDS )
		WriteAsJson( self.topic_info, self.path + SaliencyAPI.TOPIC_WEIGHTS )
		WriteAsTabDelimited( self.topic_info, self.path + SaliencyAPI.TOPIC_WEIGHTS_TXT, SaliencyAPI.TERM_SALIENCY_FIELDS )

class SimilarityAPI( object ):
	SUBFOLDER = 'similarity'
	DOCUMENT_OCCURRENCE = 'document-occurrence.txt'
	DOCUMENT_COOCCURRENCE = 'document-cooccurrence.txt'
	WINDOW_OCCURRENCE = 'window-occurrence.txt'
	WINDOW_COOCCURRENCE = 'window-cooccurrence.txt'
	UNIGRAM_COUNTS = 'unigram-counts.txt'
	BIGRAM_COUNTS = 'bigram-counts.txt'
	DOCUMENT_G2 = 'document-g2.txt'
	WINDOW_G2 = 'window-g2.txt'
	COLLOCATAPIN_G2 = 'collocation-g2.txt'
	COMBINED_G2 = 'combined-g2.txt'
	
	def __init__( self, path ):
		self.path = '{}/{}/'.format( path, SimilarityAPI.SUBFOLDER )
		self.document_occurrence = {}
		self.document_cooccurrence = {}
		self.window_occurrence = {}
		self.window_cooccurrence = {}
		self.unigram_counts = {}
		self.bigram_counts = {}
		self.document_g2 = {}
		self.window_g2 = {}
		self.collcation_g2 = {}
		self.combined_g2 = {}
	
	def read( self ):
#		self.document_occurrence = ReadAsSparseVector( self.path + SimilarityAPI.DOCUMENT_OCCURRENCE )
#		self.document_cooccurrence = ReadAsSparseMatrix( self.path + SimilarityAPI.DOCUMENT_COOCCURRENCE )
#		self.window_occurrence = ReadAsSparseVector( self.path + SimilarityAPI.WINDOW_OCCURRENCE )
#		self.window_cooccurrence = ReadAsSparseMatrix( self.path + SimilarityAPI.WINDOW_COOCCURRENCE )
#		self.unigram_counts = ReadAsSparseVector( self.path + SimilarityAPI.UNIGRAM_COUNTS )
#		self.bigram_counts = ReadAsSparseMatrix( self.path + SimilarityAPI.BIGRAM_COUNTS )
#		self.document_g2 = ReadAsSparseMatrix( self.path + SimilarityAPI.DOCUMENT_G2 )
#		self.window_g2 = ReadAsSparseMatrix( self.path + SimilarityAPI.WINDOW_G2 )
#		self.collocation_g2 = ReadAsSparseMatrix( self.path + SimilarityAPI.COLLOCATAPIN_G2 )
		self.combined_g2 = ReadAsSparseMatrix( self.path + SimilarityAPI.COMBINED_G2 )
	
	def write( self ):
		CheckAndMakeDirs( self.path )
#		WriteAsSparseVector( self.document_occurrence, self.path + SimilarityAPI.DOCUMENT_OCCURRENCE )
#		WriteAsSparseMatrix( self.document_cooccurrence, self.path + SimilarityAPI.DOCUMENT_COOCCURRENCE )
#		WriteAsSparseVector( self.window_occurrence, self.path + SimilarityAPI.WINDOW_OCCURRENCE )
#		WriteAsSparseMatrix( self.window_cooccurrence, self.path + SimilarityAPI.WINDOW_COOCCURRENCE )
#		WriteAsSparseVector( self.unigram_counts, self.path + SimilarityAPI.UNIGRAM_COUNTS )
#		WriteAsSparseMatrix( self.bigram_counts, self.path + SimilarityAPI.BIGRAM_COUNTS )
#		WriteAsSparseMatrix( self.document_g2, self.path + SimilarityAPI.DOCUMENT_G2 )
#		WriteAsSparseMatrix( self.window_g2, self.path + SimilarityAPI.WINDOW_G2 )
#		WriteAsSparseMatrix( self.collocation_g2, self.path + SimilarityAPI.COLLOCATAPIN_G2 )
		WriteAsSparseMatrix( self.combined_g2, self.path + SimilarityAPI.COMBINED_G2 )

class SeriationAPI( object ):
	SUBFOLDER = 'seriation'
	TERM_ORDERING = 'term-ordering.txt'
	TERM_ITER_INDEX = 'term-iter-index.txt'
	
	def __init__( self, path ):
		self.path = '{}/{}/'.format( path, SeriationAPI.SUBFOLDER )
		self.term_ordering = []
		self.term_iter_index = []
	
	def read( self ):
		self.term_ordering = ReadAsList( self.path + SeriationAPI.TERM_ORDERING )
		self.term_iter_index = ReadAsList( self.path + SeriationAPI.TERM_ITER_INDEX )
	
	def write( self ):
		CheckAndMakeDirs( self.path )
		WriteAsList( self.term_ordering, self.path + SeriationAPI.TERM_ORDERING )
		WriteAsList( self.term_iter_index, self.path + SeriationAPI.TERM_ITER_INDEX )

class ClientAPI( object ):
	SUBFOLDER = 'public_html/data'
	SERIATED_PARAMETERS = 'seriated-parameters.json'
	FILTERED_PARAMETERS = 'filtered-parameters.json'
	GLOBAL_TERM_FREQS = 'global-term-freqs.json'
	
	def __init__( self, path ):
		self.path = '{}/{}/'.format( path, ClientAPI.SUBFOLDER )
		self.seriated_parameters = {}
		self.filtered_parameters = {}
		self.global_term_freqs = {}
	
	def read( self ):
		self.seriated_parameters = ReadAsJson( self.path + ClientAPI.SERIATED_PARAMETERS )
		self.filtered_parameters = ReadAsJson( self.path + ClientAPI.FILTERED_PARAMETERS )
		self.global_term_freqs = ReadAsJson( self.path + ClientAPI.GLOBAL_TERM_FREQS )
	
	def write( self ):
		CheckAndMakeDirs( self.path )
		WriteAsJson( self.seriated_parameters, self.path + ClientAPI.SERIATED_PARAMETERS )
		WriteAsJson( self.filtered_parameters, self.path + ClientAPI.FILTERED_PARAMETERS )
		WriteAsJson( self.global_term_freqs, self.path + ClientAPI.GLOBAL_TERM_FREQS )

########NEW FILE########
__FILENAME__ = compute_saliency
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import ConfigParser
import logging

import math
from api_utils import ModelAPI, SaliencyAPI

class ComputeSaliency( object ):
	"""
	Distinctiveness and saliency.
	
	Compute term distinctiveness and term saliency, based on
	the term probability distributions associated with a set of
	latent topics.
	
	Input is term-topic probability distribution, stored in 3 separate files:
	    'term-topic-matrix.txt' contains the entries of the matrix.
	    'term-index.txt' contains the terms corresponding to the rows of the matrix.
	    'topic-index.txt' contains the topic labels corresponding to the columns of the matrix.
	
	Output is a list of term distinctiveness and saliency values,
	in two duplicate formats, a tab-delimited file and a JSON object:
	    'term-info.txt'
	    'term-info.json'
	
	An auxiliary output is a list topic weights (i.e., the number of
	tokens in the corpus assigned to each latent topic) in two
	duplicate formats, a tab-delimited file and a JSON object:
	    'topic-info.txt'
	    'topic-info.json'
	"""
	
	def __init__( self, logging_level ):
		self.logger = logging.getLogger( 'ComputeSaliency' )
		self.logger.setLevel( logging_level )
		handler = logging.StreamHandler( sys.stderr )
		handler.setLevel( logging_level )
		self.logger.addHandler( handler )
	
	def execute( self, data_path ):
		
		assert data_path is not None
		
		self.logger.info( '--------------------------------------------------------------------------------' )
		self.logger.info( 'Computing term saliency...'                                                       )
		self.logger.info( '    data_path = %s', data_path                                                    )
		
		self.logger.info( 'Connecting to data...' )
		self.model = ModelAPI( data_path )
		self.saliency = SaliencyAPI( data_path )
		
		self.logger.info( 'Reading data from disk...' )
		self.model.read()
		
		self.logger.info( 'Computing...' )
		self.computeTopicInfo()
		self.computeTermInfo()
		self.rankResults()
		
		self.logger.info( 'Writing data to disk...' )
		self.saliency.write()
		
		self.logger.info( '--------------------------------------------------------------------------------' )
	
	def computeTopicInfo( self ):
		topic_weights = [ sum(x) for x in zip( *self.model.term_topic_matrix ) ]
		topic_info = []
		for i in range(self.model.topic_count):
			topic_info.append( {
				'topic' : self.model.topic_index[i],
				'weight' : topic_weights[i]
			} )
		
		self.saliency.topic_info = topic_info
	
	def computeTermInfo( self ):
		"""Iterate over the list of terms. Compute frequency, distinctiveness, saliency."""
		
		topic_marginal = self.getNormalized( [ d['weight'] for d in self.saliency.topic_info ] )
		term_info = []
		for i in range(self.model.term_count):
			term = self.model.term_index[i]
			counts = self.model.term_topic_matrix[i]
			frequency = sum( counts )
			probs = self.getNormalized( counts )
			distinctiveness = self.getKLDivergence( probs, topic_marginal )
			saliency = frequency * distinctiveness
			term_info.append( {
				'term' : term,
				'saliency' : saliency,
				'frequency' : frequency,
				'distinctiveness' : distinctiveness,
				'rank' : None,
				'visibility' : 'default'
			} )
		self.saliency.term_info = term_info
	
	def getNormalized( self, counts ):
		"""Rescale a list of counts, so they represent a proper probability distribution."""
		tally = sum( counts )
		if tally == 0:
			probs = [ d for d in counts ]
		else:
			probs = [ d / tally for d in counts ]
		return probs
	
	def getKLDivergence( self, P, Q ):
		"""Compute KL-divergence from P to Q"""
		divergence = 0
		assert len(P) == len(Q)
		for i in range(len(P)):
			p = P[i]
			q = Q[i]
			assert p >= 0
			assert q >= 0
			if p > 0:
				divergence += p * math.log( p / q )
		return divergence
	
	def rankResults( self ):
		"""Sort topics by decreasing weight. Sort term frequencies by decreasing saliency."""
		self.saliency.topic_info = sorted( self.saliency.topic_info, key = lambda topic_weight : -topic_weight['weight'] )
		self.saliency.term_info = sorted( self.saliency.term_info, key = lambda term_freq : -term_freq['saliency'] )
		for i, element in enumerate( self.saliency.term_info ):
			element['rank'] = i

#-------------------------------------------------------------------------------#

def main():
	parser = argparse.ArgumentParser( description = 'Compute term saliency for TermiteVis.' )
	parser.add_argument( 'config_file', type = str, default = None    , help = 'Path of Termite configuration file.' )
	parser.add_argument( '--data-path', type = str, dest = 'data_path', help = 'Override data path.'                 )
	parser.add_argument( '--logging'  , type = int, dest = 'logging'  , help = 'Override logging level.'             )
	args = parser.parse_args()
	
	data_path = None
	logging_level = 20
	
	# Read in default values from the configuration file
	if args.config_file is not None:
		config = ConfigParser.RawConfigParser()
		config.read( args.config_file )
		if config.has_section( 'Termite' ) and config.has_option( 'Termite', 'path' ):
			data_path = config.get( 'Termite', 'path' )
		if config.has_section( 'Misc' ) and config.has_option( 'Misc', 'logging' ):
			logging_level = config.getint( 'Misc', 'logging' )
	
	# Read in user-specifiec values from the program arguments
	if args.data_path is not None:
		data_path = args.data_path
	if args.logging is not None:
		logging_level = args.logging
	
	ComputeSaliency( logging_level ).execute( data_path )

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = compute_seriation
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import ConfigParser
import logging

import time
from operator import itemgetter
from api_utils import SaliencyAPI, SimilarityAPI, SeriationAPI

class ComputeSeriation( object ):
	"""Seriation algorithm.

	Re-order words to improve promote the legibility of multi-word
	phrases and reveal the clustering of related terms.
	
	As output, the algorithm produces a list of seriated terms and its 'ranking'
	(i.e., the iteration in which a term was seriated).
	"""
	
	DEFAULT_NUM_SERIATED_TERMS = 100
	
	def __init__( self, logging_level ):
		self.logger = logging.getLogger( 'ComputeSeriation' )
		self.logger.setLevel( logging_level )
		handler = logging.StreamHandler( sys.stderr )
		handler.setLevel( logging_level )
		self.logger.addHandler( handler )
	
	def execute( self, data_path, numSeriatedTerms = None ):
		
		assert data_path is not None
		if numSeriatedTerms is None:
			numSeriatedTerms = ComputeSeriation.DEFAULT_NUM_SERIATED_TERMS
		
		self.logger.info( '--------------------------------------------------------------------------------' )
		self.logger.info( 'Computing term seriation...'                                                      )
		self.logger.info( '    data_path = %s', data_path                                                    )
		self.logger.info( '    number_of_seriated_terms = %d', numSeriatedTerms                              )
		
		self.logger.info( 'Connecting to data...' )
		self.saliency = SaliencyAPI( data_path )
		self.similarity = SimilarityAPI( data_path )
		self.seriation = SeriationAPI( data_path )
		
		self.logger.info( 'Reading data from disk...' )
		self.saliency.read()
		self.similarity.read()
		
		self.logger.info( 'Reshaping saliency data...' )
		self.reshape()
		
		self.logger.info( 'Computing seriation...' )
		self.compute( numSeriatedTerms )
		
		self.logger.info( 'Writing data to disk...' )
		self.seriation.write()
		
		self.logger.info( '--------------------------------------------------------------------------------' )
	
	def reshape( self ):
		self.candidateSize = 100
		self.orderedTermList = []
		self.termSaliency = {}
		self.termFreqs = {}
		self.termDistinct = {}
		self.termRank = {}
		self.termVisibility = {}
		for element in self.saliency.term_info:
			term = element['term']
			self.orderedTermList.append( term )
			self.termSaliency[term] = element['saliency']
			self.termFreqs[term] = element['frequency']
			self.termDistinct[term] = element['distinctiveness']
			self.termRank[term] = element['rank']
			self.termVisibility[term] = element['visibility']
	
	def compute( self, numSeriatedTerms ):
		# Elicit from user (1) the number of terms to output and (2) a list of terms that should be included in the output...
		# set in init (i.e. read from config file)
		
		# Seriate!
		start_time = time.time()
		candidateTerms = self.orderedTermList
		self.seriation.term_ordering = []
		self.seriation.term_iter_index = []
		self.buffers = [0,0]
		
		preBest = []
		postBest = []
		
		for iteration in range(numSeriatedTerms):
			print "Iteration no. ", iteration
			
			addedTerm = 0
			if len(self.seriation.term_iter_index) > 0:
				addedTerm = self.seriation.term_iter_index[-1]
			if iteration == 1:
				(preBest, postBest) = self.initBestEnergies(addedTerm, candidateTerms)
			(preBest, postBest, self.bestEnergies) = self.getBestEnergies(preBest, postBest, addedTerm)
			(candidateTerms, self.seriation.term_ordering, self.seriation.term_iter_index, self.buffers) = self.iterate_eff(candidateTerms, self.seriation.term_ordering, self.seriation.term_iter_index, self.buffers, self.bestEnergies, iteration)
			
			print "---------------"
		seriation_time = time.time() - start_time
		
		# Output consists of (1) a list of ordered terms, and (2) the iteration index in which a term was ordered
		#print "term_ordering: ", self.seriation.term_ordering
		#print "term_iter_index: ", self.seriation.term_iter_index   # Feel free to pick a less confusing variable name
		
		#print "similarity matrix generation time: ", compute_sim_time
		#print "seriation time: ", seriation_time
		self.logger.debug("seriation time: " +  str(seriation_time))

#-------------------------------------------------------------------------------#
# Helper Functions
	
	def initBestEnergies(self, firstTerm, candidateTerms):
		
		preBest = []
		postBest = []
		for candidate in candidateTerms:
			pre_score = 0
			post_score = 0
			
			# preBest
			if (candidate, firstTerm) in self.similarity.combined_g2:
				pre_score = self.similarity.combined_g2[(candidate, firstTerm)]
			# postBest
			if (firstTerm, candidate) in self.similarity.combined_g2:
				post_score = self.similarity.combined_g2[(firstTerm, candidate)]
			
			preBest.append((candidate, pre_score))
			postBest.append((candidate, post_score))
		
		return (preBest, postBest)
	
	def getBestEnergies(self, preBest, postBest, addedTerm):
		if addedTerm == 0:
			return (preBest, postBest, [])
		
		term_order = [x[0] for x in preBest]
		# compare candidate terms' bests against newly added term
		remove_index = -1
		for existingIndex in range(len(preBest)):
			term = term_order[existingIndex]
			if term == addedTerm:
				remove_index = existingIndex
			
			# check pre energies
			if (term, addedTerm) in self.similarity.combined_g2:
				if self.similarity.combined_g2[(term, addedTerm)] > preBest[existingIndex][1]:
					preBest[existingIndex] = (term, self.similarity.combined_g2[(term, addedTerm)])
			# check post energies
			if (addedTerm, term) in self.similarity.combined_g2:
				if self.similarity.combined_g2[(addedTerm, term)] > postBest[existingIndex][1]:
					postBest[existingIndex] = (term, self.similarity.combined_g2[(addedTerm, term)])
		
		# remove the added term's preBest and postBest scores
		if remove_index != -1:
			del preBest[remove_index]
			del postBest[remove_index]
		
		#create and sort the bestEnergies list
		energyMax = [sum(pair) for pair in zip([x[1] for x in preBest], [y[1] for y in postBest])]
		bestEnergies = zip([x[0] for x in preBest], energyMax)
		
		return (preBest, postBest, sorted(bestEnergies, key=itemgetter(1), reverse=True))
	
	def iterate_eff( self, candidateTerms, term_ordering, term_iter_index, buffers, bestEnergies, iteration_no ):
		maxEnergyChange = 0.0;
		maxTerm = "";
		maxPosition = 0;
		
		if len(bestEnergies) != 0:
			bestEnergy_terms = [x[0] for x in bestEnergies]
		else:
			bestEnergy_terms = candidateTerms
		
		breakout_counter = 0
		for candidate_index in range(len(bestEnergy_terms)):
			breakout_counter += 1
			candidate = bestEnergy_terms[candidate_index]
			for position in range(len(term_ordering)+1):
				current_buffer = buffers[position]
				candidateRank = self.termRank[candidate]
				if candidateRank <= (len(term_ordering) + self.candidateSize):
					current_energy_change = self.getEnergyChange(candidate, position, term_ordering, current_buffer, iteration_no)
					if current_energy_change > maxEnergyChange:
						maxEnergyChange = current_energy_change
						maxTerm = candidate
						maxPosition = position
			# check for early termination
			if candidate_index < len(bestEnergy_terms)-1 and len(bestEnergies) != 0:
				if maxEnergyChange >= (2*(bestEnergies[candidate_index][1] + current_buffer)):
					print "#-------- breaking out early ---------#"
					print "candidates checked: ", breakout_counter
					break;
		
		print "change in energy: ", maxEnergyChange
		print "maxTerm: ", maxTerm
		print "maxPosition: ", maxPosition
		
		candidateTerms.remove(maxTerm)
		
		# update buffers
		buf_score = 0
		if len(term_ordering) == 0:
			buffers = buffers
		elif maxPosition >= len(term_ordering):
			if (term_ordering[-1], maxTerm) in self.similarity.combined_g2:
				buf_score = self.similarity.combined_g2[(term_ordering[-1], maxTerm)]
			buffers.insert(len(buffers)-1, buf_score)
		elif maxPosition == 0:
			if (maxTerm, term_ordering[0]) in self.similarity.combined_g2:
				buf_score = self.similarity.combined_g2[(maxTerm, term_ordering[0])]
			buffers.insert(1, buf_score)
		else:
			if (term_ordering[maxPosition-1], maxTerm) in self.similarity.combined_g2:
				buf_score = self.similarity.combined_g2[(term_ordering[maxPosition-1], maxTerm)]
			buffers[maxPosition] = buf_score
			
			buf_score = 0
			if (maxTerm, term_ordering[maxPosition]) in self.similarity.combined_g2:
				buf_score = self.similarity.combined_g2[(maxTerm, term_ordering[maxPosition])]
			buffers.insert(maxPosition+1, buf_score)
		
		# update term ordering and ranking
		if maxPosition >= len(term_ordering):
			term_ordering.append(maxTerm)
		else:
			term_ordering.insert(maxPosition, maxTerm)
		term_iter_index.append(maxTerm)
			
		
		return (candidateTerms, term_ordering, term_iter_index, buffers)
	
	def getEnergyChange(self, candidateTerm, position, term_list, currentBuffer, iteration_no):
		prevBond = 0.0
		postBond = 0.0
		
		# first iteration only
		if iteration_no == 0:
			current_freq = 0.0
			current_saliency = 0.0
			
			if candidateTerm in self.termFreqs:
				current_freq = self.termFreqs[candidateTerm]
			if candidateTerm in self.termSaliency:
				current_saliency = self.termSaliency[candidateTerm]
			return 0.001 * current_freq * current_saliency
		
		# get previous term
		if position > 0:
			prev_term = term_list[position-1]
			if (prev_term, candidateTerm) in self.similarity.combined_g2:
				prevBond = self.similarity.combined_g2[(prev_term, candidateTerm)]
		
		# get next term
		if position < len(term_list):
			next_term = term_list[position]
			if (next_term, candidateTerm) in self.similarity.combined_g2:
				postBond = self.similarity.combined_g2[(candidateTerm, next_term)]
		
		return 2*(prevBond + postBond - currentBuffer)

#-------------------------------------------------------------------------------#

def main():
	parser = argparse.ArgumentParser( description = 'Compute term seriation for TermiteVis.' )
	parser.add_argument( 'config_file'               , type = str, default = None                   , help = 'Path of Termite configuration file.'      )
	parser.add_argument( '--data-path'               , type = str, dest = 'data_path'               , help = 'Override data path.'                      )
	parser.add_argument( '--number-of-seriated-terms', type = int, dest = 'number_of_seriated_terms', help = 'Override the number of terms to seriate.' )
	parser.add_argument( '--logging'                 , type = int, dest = 'logging'                 , help = 'Override logging level.'                  )
	args = parser.parse_args()
	
	data_path = None
	number_of_seriated_terms = None
	logging_level = 20
	
	# Read in default values from the configuration file
	if args.config_file is not None:
		config = ConfigParser.RawConfigParser()
		config.read( args.config_file )
		if config.has_section( 'Termite' ) and config.has_option( 'Termite', 'path' ):
			data_path = config.get( 'Termite', 'path' )
		if config.has_section( 'Termite' ) and config.has_option( 'Termite', 'number_of_seriated_terms' ):
			number_of_seriated_terms = config.getint( 'Termite', 'number_of_seriated_terms' )
		if config.has_section( 'Misc' ) and config.has_option( 'Misc', 'logging' ):
			logging_level = config.getint( 'Misc', 'logging' )
	
	# Read in user-specifiec values from the program arguments
	if args.data_path is not None:
		data_path = args.data_path
	if args.number_of_seriated_terms is not None:
		number_of_seriated_terms = args.number_of_seriated_terms
	if args.logging is not None:
		logging_level = args.logging
	
	ComputeSeriation( logging_level ).execute( data_path, number_of_seriated_terms )

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = compute_similarity
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import ConfigParser
import logging

import math
import itertools
from api_utils import TokensAPI, SimilarityAPI

class ComputeSimilarity( object ):
	"""
	Similarity measures.
	
	Compute term similarity based on co-occurrence and
	collocation likelihoods.
	"""
	
	DEFAULT_SLIDING_WINDOW_SIZE = 10
	MAX_FREQ = 100.0
	
	def __init__( self, logging_level ):
		self.logger = logging.getLogger( 'ComputeSimilarity' )
		self.logger.setLevel( logging_level )
		handler = logging.StreamHandler( sys.stderr )
		handler.setLevel( logging_level )
		self.logger.addHandler( handler )
	
	def execute( self, data_path, sliding_window_size = None ):
		
		assert data_path is not None
		if sliding_window_size is None:
			sliding_window_size = ComputeSimilarity.DEFAULT_SLIDING_WINDOW_SIZE
		
		self.logger.info( '--------------------------------------------------------------------------------' )
		self.logger.info( 'Computing term similarity...'                                                     )
		self.logger.info( '    data_path = %s', data_path                                                    )
		self.logger.info( '    sliding_window_size = %d', sliding_window_size                                )
		
		self.logger.info( 'Connecting to data...' )
		self.tokens = TokensAPI( data_path )
		self.similarity = SimilarityAPI( data_path )
		
		self.logger.info( 'Reading data from disk...' )
		self.tokens.read()
		
		self.logger.info( 'Computing document co-occurrence...' )
		self.computeDocumentCooccurrence()
		
		self.logger.info( 'Computing sliding-window co-occurrence...' )
		self.computeSlidingWindowCooccurrence( sliding_window_size )
		
		self.logger.info( 'Counting total number of tokens, unigrams, and bigrams in the corpus...' )
		self.computeTokenCounts()
		
		self.logger.info( 'Computing document co-occurrence likelihood...' )
		self.similarity.document_g2 = self.getG2Stats( self.document_count, self.similarity.document_occurrence, self.similarity.document_cooccurrence )
		
		self.logger.info( 'Computing sliding-window co-occurrence likelihood...' )
		self.similarity.window_g2 = self.getG2Stats( self.window_count, self.similarity.window_occurrence, self.similarity.window_cooccurrence )
		
		self.logger.info( 'Computing collocation likelihood...' )
		self.similarity.collocation_g2 = self.getG2Stats( self.token_count, self.similarity.unigram_counts, self.similarity.bigram_counts )
		
		self.combineSimilarityMatrices()
		
		self.logger.info( 'Writing data to disk...' )
		self.similarity.write()
		
		self.logger.info( '--------------------------------------------------------------------------------' )
	
	def incrementCount( self, occurrence, key ):
		if key not in occurrence:
			occurrence[ key ] = 1
		else:
			occurrence[ key ] += 1
	
	def computeDocumentCooccurrence( self ):
		document_count = 0
		occurrence = {}
		cooccurrence = {}
		for docID, docTokens in self.tokens.data.iteritems():
			self.logger.debug( '    %s (%d tokens)', docID, len(docTokens) )
			tokenSet = frozenset(docTokens)
			document_count += 1
			for token in tokenSet:
				self.incrementCount( occurrence, token )
			for aToken in tokenSet:
				for bToken in tokenSet:
					if aToken < bToken:
						self.incrementCount( cooccurrence, (aToken, bToken) )
		
		self.document_count = document_count
		self.similarity.document_occurrence = occurrence
		self.similarity.document_cooccurrence = cooccurrence
	
	def computeSlidingWindowCooccurrence( self, sliding_window_size ):
		window_count = 0
		occurrence = {}
		cooccurrence = {}
		for docID, docTokens in self.tokens.data.iteritems():
			allWindowTokens = self.getSlidingWindowTokens( docTokens, sliding_window_size )
			self.logger.debug( '    %s (%d tokens, %d windows)', docID, len(docTokens), len(allWindowTokens) )
			for windowTokens in allWindowTokens:
				tokenSet = frozenset(windowTokens)
				window_count += 1
				for token in tokenSet:
					self.incrementCount( occurrence, token )
				for aToken in tokenSet:
					for bToken in tokenSet:
						if aToken < bToken:
							self.incrementCount( cooccurrence, (aToken, bToken) )
		
		self.window_count = window_count
		self.similarity.window_occurrence = occurrence
		self.similarity.window_cooccurrence = cooccurrence
	
	def getSlidingWindowTokens( self, tokens, sliding_window_size ):
		allWindows = []
		aIndex = 0 - sliding_window_size
		bIndex = len(tokens) + sliding_window_size
		for index in range( aIndex, bIndex ):
			a = max( 0           , index - sliding_window_size )
			b = min( len(tokens) , index + sliding_window_size )
			allWindows.append( tokens[a:b] )
		return allWindows
	
	def computeTokenCounts( self ):
		token_count = sum( len(docTokens) for docTokens in self.tokens.data.itervalues() )
		
		unigram_counts = {}
		for docTokens in self.tokens.data.itervalues():
			for token in docTokens:
				self.incrementCount( unigram_counts, token )
		
		bigram_counts = {}
		for docTokens in self.tokens.data.itervalues():
			prevToken = None
			for currToken in docTokens:
				if prevToken is not None:
					self.incrementCount( bigram_counts, (prevToken, currToken) )
				prevToken = currToken
		
		self.token_count = token_count
		self.similarity.unigram_counts = unigram_counts
		self.similarity.bigram_counts = bigram_counts
	
	def getBinomial( self, B_given_A, any_given_A, B_given_notA, any_given_notA ):
		assert B_given_A >= 0
		assert B_given_notA >= 0
		assert any_given_A >= B_given_A
		assert any_given_notA >= B_given_notA
		
		a = float( B_given_A )
		b = float( B_given_notA )
		c = float( any_given_A )
		d = float( any_given_notA )
		E1 = c * ( a + b ) / ( c + d )
		E2 = d * ( a + b ) / ( c + d )
		
		g2a = 0
		g2b = 0
		if a > 0:
			g2a = a * math.log( a / E1 )
		if b > 0:
			g2b = b * math.log( b / E2 )
		return 2 * ( g2a + g2b )
	
	def getG2( self, freq_all, freq_ab, freq_a, freq_b ):
		assert freq_all >= freq_a
		assert freq_all >= freq_b
		assert freq_a >= freq_ab
		assert freq_b >= freq_ab
		assert freq_all >= 0
		assert freq_ab >= 0
		assert freq_a >= 0
		assert freq_b >= 0
		
		B_given_A = freq_ab
		B_given_notA = freq_b - freq_ab
		any_given_A = freq_a
		any_given_notA = freq_all - freq_a
		
		return self.getBinomial( B_given_A, any_given_A, B_given_notA, any_given_notA )
	
	def getG2Stats( self, max_count, occurrence, cooccurrence ):
		g2_stats = {}
		freq_all = max_count
		for ( firstToken, secondToken ) in cooccurrence:
			freq_a = occurrence[ firstToken ]
			freq_b = occurrence[ secondToken ]
			freq_ab = cooccurrence[ (firstToken, secondToken) ]
			
			scale = ComputeSimilarity.MAX_FREQ / freq_all
			rescaled_freq_all = freq_all * scale
			rescaled_freq_a = freq_a * scale
			rescaled_freq_b = freq_b * scale
			rescaled_freq_ab = freq_ab * scale
			if rescaled_freq_a > 1.0 and rescaled_freq_b > 1.0:
				g2_stats[ (firstToken, secondToken) ] = self.getG2( freq_all, freq_ab, freq_a, freq_b )
		return g2_stats
	
	def combineSimilarityMatrices( self ):
		self.logger.info( 'Combining similarity matrices...' )
		self.similarity.combined_g2 = {}
		
		keys_queued = []
		for key in self.similarity.document_g2:
			( firstToken, secondToken ) = key
			otherKey = ( secondToken, firstToken )
			keys_queued.append( key )
			keys_queued.append( otherKey )
		for key in self.similarity.window_g2:
			( firstToken, secondToken ) = key
			otherKey = ( secondToken, firstToken )
			keys_queued.append( key )
			keys_queued.append( otherKey )
		for key in self.similarity.collocation_g2:
			keys_queued.append( key )
		
		keys_processed = {}
		for key in keys_queued:
			keys_processed[ key ] = False
		
		for key in keys_queued:
			if not keys_processed[ key ]:
				keys_processed[ key ] = True
				
				( firstToken, secondToken ) = key
				if firstToken < secondToken:
					orderedKey = key
				else:
					orderedKey = ( secondToken, firstToken )
				score = 0.0
				if orderedKey in self.similarity.document_g2:
					score += self.similarity.document_g2[ orderedKey ]
				if orderedKey in self.similarity.window_g2:
					score += self.similarity.window_g2[ orderedKey ]
				if key in self.similarity.collocation_g2:
					score += self.similarity.collocation_g2[ key ]
				if score > 0.0:
					self.similarity.combined_g2[ key ] = score

#-------------------------------------------------------------------------------#

def main():
	parser = argparse.ArgumentParser( description = 'Compute term similarity for TermiteVis.' )
	parser.add_argument( 'config_file'          , type = str, default = None              , help = 'Path of Termite configuration file.' )
	parser.add_argument( '--data-path'          , type = str, dest = 'data_path'          , help = 'Override data path.'                 )
	parser.add_argument( '--sliding-window-size', type = int, dest = 'sliding_window_size', help = 'Override sliding window size.'       )
	parser.add_argument( '--logging'            , type = int, dest = 'logging'            , help = 'Override logging level.'             )
	args = parser.parse_args()
	
	data_path = None
	sliding_window_size = None
	logging_level = 20
	
	# Read in default values from the configuration file
	if args.config_file is not None:
		config = ConfigParser.RawConfigParser()
		config.read( args.config_file )
		if config.has_section( 'Termite' ) and config.has_option( 'Termite', 'path' ):
			data_path = config.get( 'Termite', 'path' )
		if config.has_section( 'Termite' ) and config.has_option( 'Termite', 'sliding_window_size' ):
			sliding_window_size = config.get( 'Termite', 'sliding_window_size' )
		if config.has_section( 'Misc' ) and config.has_option( 'Misc', 'logging' ):
			logging_level = config.getint( 'Misc', 'logging' )
	
	# Read in user-specifiec values from the program arguments
	if args.data_path is not None:
		data_path = args.data_path
	if args.sliding_window_size is not None:
		sliding_window_size = args.sliding_window_size
	if args.logging is not None:
		logging_level = args.logging
	
	ComputeSimilarity( logging_level ).execute( data_path, sliding_window_size )

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = import_mallet
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import ConfigParser
import logging

from utf8_utils import UnicodeReader
from api_utils import ModelAPI

class ImportMallet( object ):

	"""
	Copies mallet file formats into Termite internal format.
	"""
	
	# Files generated by Mallet
	TOPIC_WORD_WEIGHTS = 'topic-word-weights.txt'
	
	def __init__( self, logging_level ):
		self.logger = logging.getLogger( 'ImportMallet' )
		self.logger.setLevel( logging_level )
		handler = logging.StreamHandler( sys.stderr )
		handler.setLevel( logging_level )
		self.logger.addHandler( handler )
	
	def execute( self, model_library, model_path, data_path ):
		
		assert model_library is not None
		assert model_library == 'mallet'
		assert model_path is not None
		assert data_path is not None
		
		self.logger.info( '--------------------------------------------------------------------------------' )
		self.logger.info( 'Importing a Mallet model...'                                                      )
		self.logger.info( '    topic model = %s (%s)', model_path, model_library                             )
		self.logger.info( '    output = %s', data_path                                                       )
		
		self.logger.info( 'Connecting to data...' )
		self.model = ModelAPI( data_path )
		
		self.logger.info( 'Reading "%s" from Mallet...', ImportMallet.TOPIC_WORD_WEIGHTS )
		self.extractTopicWordWeights( model_path )
		
		self.logger.info( 'Writing data to disk...' )
		self.model.write()
		
		self.logger.info( '--------------------------------------------------------------------------------' )
	
	def extractTopicWordWeights( self, model_path ):
		data = {}
		words = []
		topics = []
		
		# Read in content of file (sparse matrix representation)
		filename = '{}/{}'.format( model_path, ImportMallet.TOPIC_WORD_WEIGHTS )
		with open( filename, 'r' ) as f:
			lines = UnicodeReader( f )
			for (topic, word, value) in lines:
				topic = int(topic)
				if topic not in data:
					data[ topic ] = {}
				data[ topic ][ word ] = float(value)
				words.append( word )
				topics.append( topic )
		
		# Get list of terms and topic indexes
		term_index = sorted( list( frozenset( words ) ) )
		topic_index = sorted( list( frozenset( topics ) ) )
		
		# Build dense matrix representation
		matrix = []
		for term in term_index :
			row = []
			for topic in topic_index :
				row.append( data[ topic ][ term ] )
			matrix.append( row )
		
		# Generate topic labels
		topic_str_index = [ 'Topic {}'.format(d) for d in topic_index ]
		
		self.model.term_topic_matrix = matrix
		self.model.term_index = term_index
		self.model.topic_index = topic_str_index

def main():
	parser = argparse.ArgumentParser( description = 'Import results from Mallet topic model library into Termite.' )
	parser.add_argument( 'config_file'          , type = str, default = None        , help = 'Path of Termite configuration file.' )
	parser.add_argument( '--topic-model-library', type = str, dest = 'model_library', help = 'Override topic model library.'       )
	parser.add_argument( '--topic-model-path'   , type = str, dest = 'model_path'   , help = 'Override topic model path.'          )
	parser.add_argument( '--data-path'          , type = str, dest = 'data_path'    , help = 'Override data path.'                 )
	parser.add_argument( '--logging'            , type = int, dest = 'logging'      , help = 'Override logging level.'             )
	args = parser.parse_args()
	
	model_library = None
	model_path = None
	data_path = None
	logging_level = 20
	
	# Read in default values from the configuration file
	config = ConfigParser.RawConfigParser()
	config.read( args.config_file )
	model_library = config.get( 'TopicModel', 'library' )
	model_path = config.get( 'TopicModel', 'path' )
	data_path = config.get( 'Termite', 'path' )
	if config.has_section( 'Misc' ):
		if config.has_option( 'Misc', 'logging' ):
			logging_level = config.getint( 'Misc', 'logging' )
	
	# Read in user-specifiec values from the program arguments
	if args.model_library is not None:
		model_library = args.model_library
	if args.model_path is not None:
		model_path = args.model_path
	if args.data_path is not None:
		data_path = args.data_path
	if args.logging is not None:
		logging_level = args.logging
	
	ImportMallet( logging_level ).execute( model_library, model_path, data_path )

if __name__ == '__main__':
	main()
########NEW FILE########
__FILENAME__ = import_stmt
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import ConfigParser
import logging

from utf8_utils import UnicodeReader
from api_utils import ModelAPI

class ImportStmt( object ):
	
	"""
	Copies STMT file formats into Termite internal format.
	"""
	
	# Files generated by STMT
	TERM_INDEX = 'term-index.txt'
	TOPIC_INDEX = 'topic-index.txt'
	DOCUMENT_INDEX = 'doc-index.txt'
	TOPIC_TERM = 'topic-term-distributions.csv'
	DOCUMENT_TOPIC = 'document-topic-distributions.csv'
	
	def __init__( self, logging_level ):
		self.logger = logging.getLogger( 'ImportStmt' )
		self.logger.setLevel( logging_level )
		handler = logging.StreamHandler( sys.stderr )
		handler.setLevel( logging_level )
		self.logger.addHandler( handler )
	
	def execute( self, model_library, model_path, data_path ):
		
		assert model_library is not None
		assert model_library == 'stmt'
		assert model_path is not None
		assert data_path is not None
		
		self.logger.info( '--------------------------------------------------------------------------------' )
		self.logger.info( 'Importing an STMT model...'                                                       )
		self.logger.info( '    topic model = %s (%s)', model_path, model_library                             )
		self.logger.info( '    output = %s', data_path                                                       )
		
		self.logger.info( 'Connecting to data...' )
		self.model = ModelAPI( data_path )
		
		self.logger.info( 'Reading "%s" from STMT output...', ImportStmt.TERM_INDEX )
		self.model.term_index  = self.readAsList( model_path, ImportStmt.TERM_INDEX )
		self.model.term_count = len(self.model.term_index)
		
		self.logger.info( 'Reading "%s" from STMT output...', ImportStmt.TOPIC_INDEX )
		self.model.topic_index = self.readAsList( model_path, ImportStmt.TOPIC_INDEX )
		self.model.topic_count = len(self.model.topic_index)
		
		self.logger.info( 'Reading "%s" from STMT output...', ImportStmt.DOCUMENT_INDEX )
		self.model.document_index = self.readAsList( model_path, ImportStmt.DOCUMENT_INDEX )
		self.model.document_count = len(self.model.document_index)
		
		self.logger.info( 'Reading "%s" from STMT output...', ImportStmt.TOPIC_TERM )
		self.topic_term_counts = self.readCsvAsMatrixStr( model_path, ImportStmt.TOPIC_TERM )
		
		self.logger.info( 'Reading "%s" from STMT output...', ImportStmt.DOCUMENT_TOPIC )
		self.document_topic_counts = self.readCsvAsMatrixStr( model_path, ImportStmt.DOCUMENT_TOPIC )
		
		self.logger.info( 'Extracting term-topic matrix...' )
		self.extractTermTopicMatrix()
		
		self.logger.info( 'Extracting document-topic matrix...' )
		self.extractDocumentTopicMatrix()
		
		self.logger.info( 'Writing data to disk...' )
		self.model.write()
	
	def readAsList( self, model_path, filename ):
		data = []
		filename = '{}/{}'.format( model_path, filename )
		with open( filename, 'r' ) as f:
			data = f.read().decode( 'utf-8' ).splitlines()
		return data
	
	# Need for STMT, which generates a mixed-string-float document-topic-distributions.csv file
	def readCsvAsMatrixStr( self, model_path, filename ):
		"""
		Return a matrix (list of list) of string values.
		Each row corresponds to a line of the input file.
		Each cell (in a row) corresponds to a comma-separated value (in each line).
		"""
		data = []
		filename = '{}/{}'.format( model_path, filename )
		with open( filename, 'r' ) as f:
			lines = UnicodeReader( f, delimiter = ',' )
			data = [ d for d in lines ]
		return data
	
	def extractDocumentTopicMatrix( self ):
		"""
		Extract document-topic matrix.
		Probability distributions are stored from the 2nd column onward in the document-topic distributions.
		"""
		matrix = []
		for line in self.document_topic_counts:
			matrix.append( map( float, line[1:self.model.topic_count+1] ) )
		self.model.document_topic_matrix = matrix
	
	def extractTermTopicMatrix( self ):
		"""
		Extract term-topic matrix.
		Transpose the input topic-term distributions.
		Ensure all values are greater than or equal to 0.
		"""
		matrix = [ [0] * self.model.topic_count ] * self.model.term_count
		for j, line in enumerate( self.topic_term_counts ):
			for i, value in enumerate(line):
				matrix[i][j] = max( 0, float(value) )
		self.model.term_topic_matrix = matrix

def main():
	parser = argparse.ArgumentParser( description = 'Import results from STMT (Stanford Topic-Modeling Toolbox) into Termite.' )
	parser.add_argument( 'config_file'          , type = str, default = None        , help = 'Path of Termite configuration file.' )
	parser.add_argument( '--topic-model-library', type = str, dest = 'model_library', help = 'Override topic model format'         )
	parser.add_argument( '--topic-model-path'   , type = str, dest = 'model_path'   , help = 'Override topic model path'           )
	parser.add_argument( '--data-path'          , type = str, dest = 'data_path'    , help = 'Override data path'                  )
	parser.add_argument( '--logging'            , type = int, dest = 'logging'      , help = 'Override logging level'              )
	args = parser.parse_args()
	
	model_library = None
	model_path = None
	data_path = None
	logging_level = 20
	
	# Read in default values from the configuration file
	config = ConfigParser.RawConfigParser()
	config.read( args.config_file )
	model_library = config.get( 'TopicModel', 'library' )
	model_path = config.get( 'TopicModel', 'path' )
	data_path = config.get( 'Termite', 'path' )
	if config.has_section( 'Misc' ):
		if config.has_option( 'Misc', 'logging' ):
			logging_level = config.getint( 'Misc', 'logging' )
	
	# Read in user-specifiec values from the program arguments
	if args.model_library is not None:
		model_library = args.model_library
	if args.model_path is not None:
		model_path = args.model_path
	if args.data_path is not None:
		data_path = args.data_path
	if args.logging is not None:
		logging_level = args.logging
	
	ImportStmt( logging_level ).execute( model_library, model_path, data_path )

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = io_utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
from utf8_utils import UnicodeReader, UnicodeWriter

def CheckAndMakeDirs( path ):
	if not os.path.exists( path ):
		os.makedirs( path )

def ReadAsList( filename ):
	"""
	Return a list of values.
	Each value corresponds to a line of the input file.
	"""
	data = []
	with open( filename, 'r' ) as f:
		lines = f.read().decode( 'utf-8' ).splitlines()
		for line in lines:
			data.append( line )
	return data

def ReadAsVector( filename ):
	vector = []
	with open( filename, 'r' ) as f:
		lines = f.read().decode( 'utf-8' ).splitlines()
		for line in lines:
			vector.append( float( line ) )
	return vector

def ReadAsMatrix( filename ):
	matrix = []
	with open( filename, 'r' ) as f:
		lines = UnicodeReader( f )
		for line in lines:
			matrix.append( map( float, line ) )
	return matrix

def ReadAsSparseVector( filename ):
	vector = {}
	with open( filename, 'r' ) as f:
		lines = UnicodeReader( f )
		for ( key, value ) in lines:
			vector[ key ] = float( value )
	return vector

def ReadAsSparseMatrix( filename ):
	matrix = {}
	with open( filename, 'r' ) as f:
		lines = UnicodeReader( f )
		for ( aKey, bKey, value ) in lines:
			matrix[ (aKey, bKey) ] = float( value )
	return matrix

def ReadAsJson( filename ):
	"""
	Expect a dict of values.
	Write dict as-is to disk as a JSON object.
	"""
	data = None
	with open( filename, 'r' ) as f:
		data = json.load( f, encoding = 'utf-8' )
	return data

def WriteAsList( data, filename ):
	with open( filename, 'w' ) as f:
		for element in data:
			f.write( element.encode( 'utf-8' ) + '\n' )

def WriteAsVector( vector, filename ):
	with open( filename, 'w' ) as f:
		for element in vector:
			f.write( str( vector ) + '\n' )

def WriteAsMatrix( matrix, filename ):
	with open( filename, 'w' ) as f:
		writer = UnicodeWriter( f )
		for row in matrix:
			writer.writerow( map( str, row ) )

def WriteAsSparseVector( vector, filename ):
	"""
	Expect a sparse vector (dict) of values.
	Generate a tab-delimited file, with 2 columns.
	Write key as the 1st column; write cell value as the 2nd column.
	"""
	sortedKeys = sorted( vector.keys(), key = lambda key : -vector[key] )
	with open( filename, 'w' ) as f:
		writer = UnicodeWriter( f )
		for key in sortedKeys:
			writer.writerow( [ key, str( vector[key] ) ] )

def WriteAsSparseMatrix( matrix, filename ):
	"""
	Expect a sparse matrix (two-level dict) of values.
	Generate a tab-delimited file, with 3 columns.
	Write two keys as the 1st and 2nd columns; write cell value as the 3rd column.
	"""
	sortedKeys = sorted( matrix.keys(), key = lambda key : -matrix[key] )
	with open( filename, 'w' ) as f:
		writer = UnicodeWriter( f )
		for ( aKey, bKey ) in sortedKeys:
			writer.writerow( [ aKey, bKey, str( matrix[ (aKey, bKey) ] ) ] )

def WriteAsJson( data, filename ):
	"""
	Expect a dict of values.
	Write dict as-is to disk as a JSON object.
	"""
	with open( filename, 'w' ) as f:
		json.dump( data, f, encoding = 'utf-8', indent = 2, sort_keys = True )

def WriteAsTabDelimited( data, filename, fields ):
	"""
	Expect a list of dict values.
	Take in a list of output fields.
	Write specified fields to disk, as a tab-delimited file (with header row).
	"""
	with open( filename, 'w' ) as f:
		writer = UnicodeWriter( f )
		writer.writerow( fields )
		for element in data:
			values = []
			for field in fields:
				if not type( element[field] ) is unicode:
					values.append( str( element[field] ) )
				else:
					values.append( element[field] )
			writer.writerow( values )

########NEW FILE########
__FILENAME__ = prepare_data_for_client
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import argparse
import ConfigParser
import logging

from api_utils import ModelAPI, SaliencyAPI, SeriationAPI, ClientAPI

class PrepareDataForClient( object ):
	"""
	Reformats data necessary for client to run. 
	
	Extracts a subset of the complete term list and term-topic matrix and writes
	the subset to a separate file. Also, generates JSON file that merges/packages term
	information with the actual term.
	
	Input is term-topic probability distribution and term information, stored in 4 files:
	    'term-topic-matrix.txt' contains the entries of the matrix.
	    'term-index.txt' contains the terms corresponding to the rows of the matrix.
	    'topic-index.txt' contains the topic labels corresponding to the columns of the matrix.
	    'term-info.txt' contains information about individual terms.
	
	Output is a subset of terms and matrix, as well as the term subset's information.
	Number of files created or copied: 5
		'submatrix-term-index.txt'
	    'submatrix-topic-index.txt'
	    'submatrix-term-topic.txt'
	    'term-info.json'
	    'term-info.txt'
	"""
	
	def __init__( self, logging_level ):
		self.logger = logging.getLogger( 'PrepareDataForClient' )
		self.logger.setLevel( logging_level )
		handler = logging.StreamHandler( sys.stderr )
		handler.setLevel( logging_level )
		self.logger.addHandler( handler )
	
	def execute( self, data_path ):
		
		assert data_path is not None
		
		self.logger.info( '--------------------------------------------------------------------------------' )
		self.logger.info( 'Preparing data for client...'                                                     )
		self.logger.info( '    data_path = %s', data_path                                                    )
		
		self.logger.info( 'Connecting to data...' )
		self.model = ModelAPI( data_path )
		self.saliency = SaliencyAPI( data_path )
		self.seriation = SeriationAPI( data_path )
		self.client = ClientAPI( data_path )
		
		self.logger.info( 'Reading data from disk...' )
		self.model.read()
		self.saliency.read()
		self.seriation.read()

		self.logger.info( 'Preparing parameters for seriated matrix...' )
		self.prepareSeriatedParameters()
		
		self.logger.info( 'Preparing parameters for filtered matrix...' )
		self.prepareFilteredParameters()
		
		self.logger.info( 'Preparing global term freqs...' )
		self. prepareGlobalTermFreqs()
		
		self.logger.info( 'Writing data to disk...' )
		self.client.write()

	def prepareSeriatedParameters( self ):
		topic_index = self.model.topic_index
		term_index = self.model.term_index
		term_topic_matrix = self.model.term_topic_matrix
		term_ordering = self.seriation.term_ordering
		term_topic_submatrix = []
		term_subindex = []
		for term in term_ordering:
			if term in term_index:
				index = term_index.index( term )
				term_topic_submatrix.append( term_topic_matrix[ index ] )
				term_subindex.append( term )
			else:
				self.logger.info( 'ERROR: Term (%s) does not appear in the list of seriated terms', term )

		self.client.seriated_parameters = {
			'termIndex' : term_subindex,
			'topicIndex' : topic_index,
			'matrix' : term_topic_submatrix
		}
	
	def prepareFilteredParameters( self ):
		term_rank_map = { term: value for value, term in enumerate( self.seriation.term_iter_index ) }
		term_order_map = { term: value for value, term in enumerate( self.seriation.term_ordering ) }
		term_saliency_map = { d['term']: d['saliency'] for d in self.saliency.term_info }
		term_distinctiveness_map = { d['term'] : d['distinctiveness'] for d in self.saliency.term_info }

		self.client.filtered_parameters = {
			'termRankMap' : term_rank_map,
			'termOrderMap' : term_order_map,
			'termSaliencyMap' : term_saliency_map,
			'termDistinctivenessMap' : term_distinctiveness_map
		}

	def prepareGlobalTermFreqs( self ):
		topic_index = self.model.topic_index
		term_index = self.model.term_index
		term_topic_matrix = self.model.term_topic_matrix
		term_ordering = self.seriation.term_ordering
		term_topic_submatrix = []
		term_subindex = []
		for term in term_ordering:
			if term in term_index:
				index = term_index.index( term )
				term_topic_submatrix.append( term_topic_matrix[ index ] )
				term_subindex.append( term )
			else:
				self.logger.info( 'ERROR: Term (%s) does not appear in the list of seriated terms', term )

		term_freqs = { d['term']: d['frequency'] for d in self.saliency.term_info }

		self.client.global_term_freqs = {
			'termIndex' : term_subindex,
			'topicIndex' : topic_index,
			'matrix' : term_topic_submatrix,
			'termFreqMap' : term_freqs
		}

def main():
	parser = argparse.ArgumentParser( description = 'Prepare data for client.' )
	parser.add_argument( 'config_file', type = str, default = None    , help = 'Path of Termite configuration file.' )
	parser.add_argument( '--data-path', type = str, dest = 'data_path', help = 'Override data path.'                 )
	parser.add_argument( '--logging'  , type = int, dest = 'logging'  , help = 'Override logging level.'             )
	args = parser.parse_args()
	
	args = parser.parse_args()
	
	data_path = None
	logging_level = 20
	
	# Read in default values from the configuration file
	if args.config_file is not None:
		config = ConfigParser.RawConfigParser()
		config.read( args.config_file )
		if config.has_section( 'Termite' ) and config.has_option( 'Termite', 'path' ):
			data_path = config.get( 'Termite', 'path' )
		if config.has_section( 'Misc' ) and config.has_option( 'Misc', 'logging' ):
			logging_level = config.getint( 'Misc', 'logging' )
	
	# Read in user-specifiec values from the program arguments
	if args.data_path is not None:
		data_path = args.data_path
	if args.logging is not None:
		logging_level = args.logging
	
	PrepareDataForClient( logging_level ).execute( data_path )

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = extract-doc-index
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

parser = argparse.ArgumentParser( description = 'Generate doc-index.txt from document-topic-distributions.csv' )
parser.add_argument( 'path', type = str, help = 'Path of STMT model output' )
args = parser.parse_args()
path = args.path

lines = open( '{}/document-topic-distributions.csv'.format( path ) ).read().splitlines()
writer = open( '{}/doc-index.txt'.format( path ), 'w' )
for line in lines :
	values = line.split( ',' )
	writer.write( '{}\n'.format( values[0] ) )
writer.close()

########NEW FILE########
__FILENAME__ = extract-term-freqs
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

parser = argparse.ArgumentParser( description = 'Generate label-term-distributions.csv from topic-term-distributions.csv.' )
parser.add_argument( 'path', type = str, help = 'Path of STMT model output' )
args = parser.parse_args()
path = args.path

lines = open( '{}/term-counts.csv'.format( path ) ).read().splitlines()
writer = open( '{}/term-freqs.txt'.format( path ), 'w' )
for line in lines :
	values = line.split( ',' )
	writer.write( '{}\t{}\n'.format( values[0], values[1] ) )
writer.close()

########NEW FILE########
__FILENAME__ = generate-label-term-distributions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import re

parser = argparse.ArgumentParser( description = 'Generate label-term-distributions.csv from topic-term-distributions.csv.' )
parser.add_argument( 'path', type = str, help = 'Path of STMT model output' )
args = parser.parse_args()
path = args.path

################################################################################

# Get topics
topics = []
f = '{}/final-iters/topic-index.txt'.format( path )
for line in open( f ).read().splitlines() :
	topics.append( line )

# Get labels (Skip BACKGROUND)
labels = []
f = '{}/final-iters/label-index.txt'.format( path )
for line in open( f ).read().splitlines() :
	if ( line != 'BACKGROUND' ) :
		labels.append( line )

################################################################################

# Match labels and topics
match = []
for i in range( len( topics ) ) :
	topic = topics[i]
	match.append( -1 )
	
	for j in range( len( labels ) ) :
		label = labels[j]
		m = re.match( r'{} \- \d+'.format( re.escape(label) ), topic )
		if m is not None:
			match[i] = j
	
	if ( match[i] == -1 ) :
		match[i] = len(labels)
		labels.append( "Topic{:02d}".format( len(labels)+1 ) )

#print labels
#print match

# Merge rows of TOPIC-term distributions
tally = []
for label in labels:
	tally.append( [] )

f = '{}/topic-term-distributions.csv'.format( path )
lines = open( f ).read().splitlines()
assert( len(lines) == len(topics) )
for i in range( len( topics ) ) :
	values = lines[i].split( ',' )
	for j in range( len( values ) ) :
		values[j] = float( values[j] )
	target = match[i]
	if ( len( tally[target] ) == 0 ) :
		tally[target] = values
	else :
		for j in range( len( values ) ) :
			tally[target][j] += values[j]

################################################################################

# Output topics
f = '{}/topic-index.txt'.format( path )
w = open( f, 'w' )
for topic in topics :
	w.write( topic + '\n' )
w.close()

# Output labels
f = '{}/label-index.txt'.format( path )
w = open( f, 'w' )
for label in labels :
	w.write( label + '\n' )
w.close()

# Output LABEL-term distributions
f = '{}/label-term-distributions.csv'.format( path )
w = open( f, 'w' )
for values in tally :
	for j in range( len( values ) ) :
		values[j] = str( values[j] )
	w.write( ','.join( values ) + '\n' )
w.close()


########NEW FILE########
__FILENAME__ = generate-topic-index
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

parser = argparse.ArgumentParser( description = 'Generate topic-index.txt' )
parser.add_argument( 'path', type = str, help = 'Path of STMT model output' )
parser.add_argument( 'topicCount', type = int, help = 'Number of topics' )
args = parser.parse_args()
path = args.path
topicCount = args.topicCount

f = "{}/topic-index.txt".format( path )
w = open( f, 'w' )
for i in range( topicCount ) :
	w.write( 'Topic {}\n'.format( i+1 ) )
w.close()

########NEW FILE########
__FILENAME__ = tokenize
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import argparse
import logging
import ConfigParser
from api_utils import DocumentsAPI, TokensAPI

class Tokenize( object ):

	"""
	Takes in the input corpus doc and writes it out as a list of tokens.
	
	Currently, supports only single document corpus with one document per line of format:
		doc_id<tab>document_content
	(Two fields delimited by tab.)
	
	Support for multiple files, directory(ies), and Lucene considered for future releases.
	"""
	
	WHITESPACE_TOKENIZATION = r'[^ ]+'
	ALPHANUMERIC_TOKENIZATION = r'[0-9A-Za-z_]*[A-Za-z_]+[0-9A-Za-z_]*'
	ALPHA_TOKENIZATION = r'[A-Za-z_]+'
	UNICODE_TOKENIZATION = r'[\w]+'
	DEFAULT_TOKENIZATION = ALPHA_TOKENIZATION
	
	def __init__( self, logging_level ):
		self.logger = logging.getLogger( 'Tokenize' )
		self.logger.setLevel( logging_level )
		handler = logging.StreamHandler( sys.stderr )
		handler.setLevel( logging_level )
		self.logger.addHandler( handler )
	
	def execute( self, corpus_format, corpus_path, data_path, tokenization ):		
		assert corpus_format is not None
		assert corpus_path is not None
		assert data_path is not None
		if tokenization is None:
			tokenization = Tokenize.DEFAULT_TOKENIZATION
		elif tokenization == 'unicode':
			tokenization = Tokenize.UNICODE_TOKENIZATION
		elif tokenization == 'whitespace':
			tokenization = Tokenize.WHITESPACE_TOKENIZATION
		elif tokenization == 'alpha':
			tokenization = Tokenize.ALPHA_TOKENIZATION
		elif tokenization == 'alphanumeric':
			tokenization = Tokenize.ALPHANUMERIC_TOKENIZATION
	
		self.logger.info( '--------------------------------------------------------------------------------' )
		self.logger.info( 'Tokenizing source corpus...'                                                      )
		self.logger.info( '    corpus_path = %s (%s)', corpus_path, corpus_format                            )
		self.logger.info( '    data_path = %s', data_path                                                    )
		self.logger.info( '    tokenization = %s', tokenization                                              )
		
		self.logger.info( 'Connecting to data...' )
		self.documents = DocumentsAPI( corpus_format, corpus_path )
		self.tokens = TokensAPI( data_path )
		
		self.logger.info( 'Reading from disk...' )
		self.documents.read()
		
		self.logger.info( 'Tokenizing...' )
		self.TokenizeDocuments( re.compile( tokenization, re.UNICODE ) )
		
		self.logger.info( 'Writing to disk...' )
		self.tokens.write()
		
		self.logger.info( '--------------------------------------------------------------------------------' )
	
	def TokenizeDocuments( self, tokenizer ):
		for docID, docContent in self.documents.data.iteritems():
			docTokens = self.TokenizeDocument( docContent, tokenizer )
			self.tokens.data[ docID ] = docTokens
	
	def TokenizeDocument( self, text, tokenizer ):
		tokens = []
		for token in re.findall( tokenizer, text ):
			tokens.append( token.lower() )
		return tokens

#-------------------------------------------------------------------------------#

def main():
	parser = argparse.ArgumentParser( description = 'Tokenize a document collection for Termite.' )
	parser.add_argument( 'config_file'    , type = str, default = None        , help = 'Path of Termite configuration file.'  )
	parser.add_argument( '--corpus-format', type = str, dest = 'corpus_format', help = 'Override corpus format.'              )
	parser.add_argument( '--corpus-path'  , type = str, dest = 'corpus_path'  , help = 'Override corpus path.'                )
	parser.add_argument( '--tokenization' , type = str, dest = 'tokenization' , help = 'Override tokenization regex pattern.' )
	parser.add_argument( '--data-path'    , type = str, dest = 'data_path'    , help = 'Override data path.'                  )
	parser.add_argument( '--logging'      , type = int, dest = 'logging'      , help = 'Override logging level.'              )
	args = parser.parse_args()
	
	# Declare parameters
	corpus_format = None
	corpus_path = None
	tokenization = None
	data_path = None
	logging_level = 20
	
	# Read in default values from the configuration file
	if args.config_file is not None:
		config = ConfigParser.RawConfigParser()
		config.read( args.config_file )
		if config.has_section( 'Corpus' ) and config.has_option( 'Corpus', 'format' ):
			corpus_format = config.get( 'Corpus', 'format' )
		if config.has_section( 'Corpus' ) and config.has_option( 'Corpus', 'path' ):
			corpus_path = config.get( 'Corpus', 'path' )
		if config.has_section( 'Corpus' ) and config.has_option( 'Corpus', 'tokenization' ):
			tokenization = config.get( 'Corpus', 'tokenization' )
		if config.has_section( 'Termite' ) and config.has_option( 'Termite', 'path' ):
			data_path = config.get( 'Termite', 'path' )
		if config.has_section( 'Misc' ) and config.has_option( 'Misc', 'logging' ):
			logging_level = config.getint( 'Misc', 'logging' )
	
	# Read in user-specifiec values from the program arguments
	if args.corpus_format is not None:
		corpus_format = args.corpus_format
	if args.corpus_path is not None:
		corpus_path = args.corpus_path
	if args.tokenization is not None:
		tokenization = args.tokenization
	if args.data_path is not None:
		data_path = args.data_path
	if args.logging is not None:
		logging_level = args.logging
	
	Tokenize( logging_level ).execute( corpus_format, corpus_path, data_path, tokenization )

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = utf8_utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Modified from 'The Python Standard Library'
13.1. csv — CSV File Reading and Writing
http://docs.python.org/2/library/csv.html
"""

import csv, codecs, cStringIO

class UTF8Recoder:
	"""
	Iterator that reads an encoded stream and reencodes the input to UTF-8
	"""
	def __init__(self, f, encoding):
		self.reader = codecs.getreader(encoding)(f)
	
	def __iter__(self):
		return self
	
	def next(self):
		return self.reader.next().encode("utf-8")

class UnicodeReader:
	"""
	A CSV reader which will iterate over lines in the CSV file "f",
	which is encoded in the given encoding.
	"""
	
	def __init__(self, f, dialect=csv.excel, encoding="utf-8", delimiter="\t", **kwds):
		f = UTF8Recoder(f, encoding)
		self.reader = csv.reader(f, dialect=dialect, delimiter=delimiter, **kwds)
	
	def next(self):
		row = self.reader.next()
		return [unicode(s, "utf-8") for s in row]
	
	def __iter__(self):
		return self

class UnicodeWriter:
	"""
	A CSV writer which will write rows to CSV file "f",
	which is encoded in the given encoding.
	"""
	
	def __init__(self, f, dialect=csv.excel, encoding="utf-8", delimiter="\t", **kwds):
		# Redirect output to a queue
		self.queue = cStringIO.StringIO()
		self.writer = csv.writer(self.queue, dialect=dialect, delimiter=delimiter, **kwds)
		self.stream = f
		self.encoder = codecs.getincrementalencoder(encoding)()
	
	def writerow(self, row):
		self.writer.writerow([s.encode("utf-8") for s in row])
		# Fetch UTF-8 output from the queue ...
		data = self.queue.getvalue()
		data = data.decode("utf-8", "ignore")
		# ... and reencode it into the target encoding
		data = self.encoder.encode(data)
		# write to the target stream
		self.stream.write(data)
		# empty queue
		self.queue.truncate(0)
	
	def writerows(self, rows):
		for row in rows:
			self.writerow(row)
########NEW FILE########
