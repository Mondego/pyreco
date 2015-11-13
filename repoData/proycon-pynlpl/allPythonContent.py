__FILENAME__ = algorithms

###############################################################9
# PyNLPl - Algorithms
#   by Maarten van Gompel
#   Centre for Language Studies
#   Radboud University Nijmegen
#   http://www.github.com/proycon/pynlpl
#   proycon AT anaproy DOT nl
#
#       Licensed under GPLv3
#
###############################################################

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

def sum_to_n(n, size, limit=None): #from http://stackoverflow.com/questions/2065553/python-get-all-numbers-that-add-up-to-a-number
    """Produce all lists of `size` positive integers in decreasing order
    that add up to `n`."""
    if size == 1:
        yield [n]
        return
    if limit is None:
        limit = n
    start = (n + size - 1) // size
    stop = min(limit, n - size + 1) + 1
    for i in range(start, stop):
        for tail in sum_to_n(n - i, size - 1, i):
            yield [i] + tail


def consecutivegaps(n, leftmargin = 0, rightmargin = 0):
    """Compute all possible single consecutive gaps in any sequence of the specified length. Returns
    (beginindex, length) tuples. Runs in  O(n(n+1) / 2) time. Argument is the length of the sequence rather than the sequence itself"""
    begin = leftmargin
    while begin < n:
        length = (n - rightmargin) - begin
        while length > 0:
            yield (begin, length)
            length -= 1
        begin += 1


def bytesize(n):
    """Return the required size in bytes to encode the specified integer"""
    for i in range(1, 1000):
        if n < 2**(8*i):
            return i





########NEW FILE########
__FILENAME__ = cornetto
# -*- coding: utf-8 -*-

###############################################################
#  PyNLPl - Remote Cornetto Client
#       Adapted from code by Fons Laan (ILPS-ISLA, UvA)
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#       
#       Licensed under GPLv3
# 
# This is a Python library for connecting to a Cornetto database.
# Originally coded by Fons Laan (ILPS-ISLA, University of Amsterdam) 
# for DutchSemCor.
#
# The library currently has only a minimal set of functionality compared
# to the original. It will be extended on a need-to basis.
#
###############################################################


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import    
    

import sys
import httplib2                    # version 0.6.0+
if sys.version < '3':
    import urlparse
    import httplib                    
else:
    from urllib import parse as urlparse # renamed to urllib.parse in Python 3.0
    import http.client as httplib #renamed in Python 3 
import urllib, base64
from sys import stderr 
#import pickle

printf = lambda x: sys.stdout.write(x+ "\n")

from lxml import etree


class CornettoClient(object):
    def __init__(self, user='gast',password='gast',host='debvisdic.let.vu.nl', port=9002, path = '/doc', scheme='https',debug=False):
        self.host = host
        self.port = port
        self.path = path
        self.scheme = scheme
        self.debug = debug
        self.userid = user
        self.passwd = password

    def connect(self):
        if self.debug:
            printf( "cornettodb/views/remote_open()" )
        # permission denied on cornetto with apache
        #    http = httplib2.Http( ".cache" )
        try:
            http = httplib2.Http(disable_ssl_certificate_validation=True)
        except TypeError:
            print >>stderr, "[CornettoClient] WARNING: Older version of httplib2! Can not disable_ssl_certificate_validation" 
            http = httplib2.Http() #for older httplib2 

        # VU DEBVisDic authentication
        http.add_credentials( self.userid, self.passwd )


        params   = ""
    #    query    = "action=init"                    # obsolete
        query    = "action=connect"
        fragment = ""

        db_url_tuple = ( self.scheme, self.host + ':' + str(self.port), self.path, params, query, fragment )
        db_url = urlparse.urlunparse( db_url_tuple )

        if self.debug:
            printf( "db_url: %s" % db_url )
            printf( "http.request()..." );

        try:
            resp, content = http.request( db_url, "GET" )
            if self.debug:
                printf( "resp:\n%s" % resp )
                printf( "content:\n%s" % content )
        except:
            printf( "...failed." );
            # when CORNETTO_HOST is off-line, we do not have a response
            resp = None
            content = None

        return http, resp, content

    def get_syn_ids_by_lemma(self, lemma):
        """Returns a list of synset IDs based on a lemma"""
        if not isinstance(lemma,unicode):
            lemma = unicode(lemma,'utf-8')


        http, resp, content = self.connect()

        params   = ""
        fragment = ""

        path = "cdb_syn"
        if self.debug:
            printf( "cornettodb/views/query_remote_syn_lemma: db_opt: %s" % path )

        query_opt = "dict_search"
        if self.debug:
            printf( "cornettodb/views/query_remote_syn_lemma: query_opt: %s" % query_opt )
    
        qdict = {}
        qdict[ "action" ] = "queryList"
        qdict[ "word" ]   = lemma.encode('utf-8')


        query = urllib.urlencode( qdict )

        db_url_tuple = ( self.scheme, self.host + ':' + str(self.port), path, params, query, fragment )
        db_url = urlparse.urlunparse( db_url_tuple )
        if self.debug:
            printf( "db_url: %s" % db_url )

        resp, content = http.request( db_url, "GET" )
        if self.debug:
            printf( "resp:\n%s" % resp )
            printf( "content:\n%s" % content )
        #    printf( "content is of type: %s" % type( content ) )

        dict_list = []
        dict_list = eval( content )        # string to list

        synsets = []
        items = len( dict_list )
        if self.debug:
            printf( "items: %d" % items )

        # syn dict: like lu dict, but without pos: part-of-speech
        for dict in dict_list:
            if self.debug:
                printf( dict )

            seq_nr = dict[ "seq_nr" ]   # sense number
            value  = dict[ "value" ]    # lexical unit identifier
            form   = dict[ "form" ]     # lemma
            label  = dict[ "label" ]    # label to be shown

            if self.debug:
                printf( "seq_nr: %s" % seq_nr )
                printf( "value:  %s" % value )
                printf( "form:   %s" % form )
                printf( "label:  %s" % label )

            if value != "":
                synsets.append( value )

        return synsets


    def get_lu_ids_by_lemma(self, lemma, targetpos = None):
        """Returns a list of lexical unit IDs based on a lemma and a pos tag"""
        if not isinstance(lemma,unicode):
            lemma = unicode(lemma,'utf-8')


        http, resp, content = self.connect()

        params   = ""
        fragment = ""

        path = "cdb_lu"

        query_opt = "dict_search"

        qdict = {}
        qdict[ "action" ] = "queryList"
        qdict[ "word" ]   = lemma.encode('utf-8')


        query = urllib.urlencode( qdict )

        db_url_tuple = ( self.scheme, self.host + ':' + str(self.port), path, params, query, fragment )
        db_url = urlparse.urlunparse( db_url_tuple )
        if self.debug:
            printf( "db_url: %s" % db_url )

        resp, content = http.request( db_url, "GET" )
        if self.debug:
            printf( "resp:\n%s" % resp )
            printf( "content:\n%s" % content )
        #    printf( "content is of type: %s" % type( content ) )

        dict_list = []
        dict_list = eval( content )        # string to list

        ids = []
        items = len( dict_list )
        if self.debug:
            printf( "items: %d" % items )

        for d in dict_list:
            if self.debug:
                printf( d )

            seq_nr = d[ "seq_nr" ]   # sense number
            value  = d[ "value" ]    # lexical unit identifier
            form   = d[ "form" ]     # lemma
            label  = d[ "label" ]    # label to be shown
            pos  = d[ "pos" ]    # label to be shown

            if self.debug:
                printf( "seq_nr: %s" % seq_nr )
                printf( "value:  %s" % value )
                printf( "form:   %s" % form )
                printf( "label:  %s" % label )

            if value != "" and ((not targetpos) or (targetpos and pos == targetpos)):
                ids.append( value )

        return ids



    def get_synset_xml(self,syn_id):
        """
        call cdb_syn with synset identifier -> returns the synset xml;
        """

        http, resp, content = self.connect()

        params   = ""
        fragment = ""

        path = "cdb_syn"
        if self.debug:
            printf( "cornettodb/views/query_remote_syn_id: db_opt: %s" % path )

        # output_opt: plain, html, xml
        # 'xml' is actually xhtml (with markup), but it is not valid xml!
        # 'plain' is actually valid xml (without markup)
        output_opt = "plain"
        if self.debug:
            printf( "cornettodb/views/query_remote_syn_id: output_opt: %s" % output_opt )

        action = "runQuery"
        if self.debug:
            printf( "cornettodb/views/query_remote_syn_id: action: %s" % action )
            printf( "cornettodb/views/query_remote_syn_id: query: %s" % syn_id )

        qdict = {}
        qdict[ "action" ]  = action
        qdict[ "query" ]   = syn_id
        qdict[ "outtype" ] = output_opt

        query = urllib.urlencode( qdict )

        db_url_tuple = ( self.scheme, self.host + ':' + str(self.port), path, params, query, fragment )
        db_url = urlparse.urlunparse( db_url_tuple )
        if self.debug:
            printf( "db_url: %s" % db_url )

        resp, content = http.request( db_url, "GET" )
        if self.debug:
            printf( "resp:\n%s" % resp )
        #    printf( "content:\n%s" % content )
        #    printf( "content is of type: %s" % type( content ) )        #<type 'str'>

        xml_data = eval( content )
        return etree.fromstring( xml_data )


    def get_lus_from_synset(self, syn_id):
        """Returns a list of (word, lu_id) tuples given a synset ID"""

        root = self.get_synset_xml(syn_id)
        elem_synonyms = root.find( ".//synonyms" )


        lus = []
        for elem_synonym in elem_synonyms:
            synonym_str = elem_synonym.get( "c_lu_id-previewtext" )        # get "c_lu_id-previewtext" attribute
            # synonym_str ends with ":<num>"
            synonym = synonym_str.split( ':' )[ 0 ].strip()
            lus.append( (synonym, elem_synonym.get( "c_lu_id") ) )
        return lus


    def get_lu_from_synset(self, syn_id, lemma = None):
        """Returns (lu_id, synonyms=[(word, lu_id)] ) tuple given a synset ID and a lemma"""
        if not lemma:
            return self.get_lus_from_synset(syn_id) #alias
        if not isinstance(lemma,unicode):
            lemma = unicode(lemma,'utf-8')

        root = self.get_synset_xml(syn_id)
        elem_synonyms = root.find( ".//synonyms" )

        lu_id = None
        synonyms = []
        for elem_synonym in elem_synonyms:
            synonym_str = elem_synonym.get( "c_lu_id-previewtext" )        # get "c_lu_id-previewtext" attribute
            # synonym_str ends with ":<num>"
            synonym = synonym_str.split( ':' )[ 0 ].strip()

            if synonym != lemma:
                synonyms.append( (synonym, elem_synonym.get("c_lu_id")) )
                if self.debug:
                    printf( "synonym add: %s" % synonym )
            else:
                lu_id = elem_synonym.get( "c_lu_id" )        # get "c_lu_id" attribute
                if self.debug:
                    printf( "lu_id: %s" % lu_id )
                    printf( "synonym skip lemma: %s" % synonym )
        return lu_id, synonyms



##################################################################################################################
#            ORIGINAL AND AS-OF-YET UNUSED CODE (included for later porting)
##################################################################################################################

"""
--------------------------------------------------------------------------------
Original Author:     Fons Laan, ILPS-ISLA, University of Amsterdam
Original Project:    DutchSemCor
Original Name:        cornettodb/views.py
Original Version:    0.2
Goal:        Cornetto views definitions

Original functions:
    index( request )
    local_open()
    remote_open( self.debug )
    search( request )
    search_local( dict_in, search_query )
    search_remote( dict_in, search_query )
    cornet_check_lusyn( utf8_lemma )
    query_remote_lusyn_id( syn_id_self.debug, http, utf8_lemma, syn_id )
    query_cornet( keyword, category )
    query_remote_syn_lemma( self.debug, http, utf8_lemma )
    query_remote_syn_id( self.debug, http, utf8_lemma, syn_id, domains_abbrev )
    query_remote_lu_lemma( self.debug, http, utf8_lemma )
    query_remote_lu_id( self.debug, http, lu_id )
FL-04-Sep-2009: Created
FL-03-Nov-2009: Removed http global: sometimes it was None; missed initialization?
FL-01-Feb-2010: Added Category filtering
FL-15-Feb-2010: Tag counts -> separate qx query
FL-07-Apr-2010: Merge canonical + textual examples
FL-10-Jun-2010: Latest Change
MvG-29-Sep-2010: Turned into minimal CornettoClient class, some new functions added, many old ones disabled until necessary
"""

#    def query_remote(self, dict_in, search_query ):
#        if self.debug: printf( "cornettodb/views/query_remote" )

#        http, resp, content = self.remote_open()

#        if resp is None:
#            raise Exception("No response")


#        status = int( resp.get( "status" ) )
#        if self.debug: printf( "status: %d" % status )

#        if status != 200:
#            # e.g. 400: Bad Request, 404: Not Found
#            raise Exception("Error in request")


#        path = dict_in[ 'dbopt' ]
#        if self.debug: printf( "cornettodb/views/query_remote: db_opt: %s" % path )

#        output_opt = dict_in[ 'outputopt' ]
#        if self.debug: printf( "cornettodb/views/query_remote: output_opt: %s" % output_opt )

#        query_opt = dict_in[ 'queryopt' ]
#        if self.debug: printf( "cornettodb/views/query_remote: query_opt: %s" % query_opt )

#        params   = ""
#        fragment = ""

#        qdict = {}
#        if query_opt == "dict_search":
#        #    query = "action=queryList&word=" + search_query
#            qdict[ "action" ] = "queryList"
#            qdict[ "word" ]   = search_query

#        elif query_opt == "query_entry":
#        #    query = "action=runQuery&query=" + search_query
#        #    query += "&outtype=" + output_opt
#            qdict[ "action" ]  = "runQuery"
#            qdict[ "query" ]   = search_query
#            qdict[ "outtype" ] = output_opt

#        # instead of "subtree" there is also "tree" and "full subtree"
#        elif query_opt == "subtree_entry":
#        #    query = "action=subtree&query=" + search_query
#        #    query += "&arg=ILR"            # ILR = Internal Language Relations, RILR = Reversed ...
#        #    query += "&outtype=" + output_opt
#            qdict[ "action" ]  = "subtree"
#            qdict[ "query" ]   = search_query
#            qdict[ "arg" ]     = "ILR"    # ILR = Internal Language Relations, RILR = Reversed ...
#            qdict[ "outtype" ] = output_opt

#        # More functions, see DEBVisDic docu:
#        #    Save entry
#        #    Delete entry
#        #    Next sense number
#        #    "Translate" synsets 

#        query = urllib.urlencode( qdict )

#        db_url_tuple = ( self.scheme, self.host+ ':' + str(self.post), self.path, params, query, fragment )
#        db_url = urlparse.urlunparse( db_url_tuple )
#        if self.debug: printf( "db_url: %s" % db_url )

#        resp, content = http.request( db_url, "GET" )
#        printf( "resp:\n%s" % resp )
#        if self.debug: printf( "content:\n%s" % content )

#        if content.startswith( '[' ) and content.endswith( ']' ):
#            reply = eval( content )        # string -> list
#            islist = True
#        else:
#            reply = content
#            islist = False

#        return reply


#    def cornet_check_lusyn( self, utf8_lemma ):
#        http, resp, content = remote_open( self.debug )

#        # get the raw (unfiltered) lexical unit identifiers for this lemma
#        lu_ids_lemma = query_remote_lu_lemma( http, utf8_lemma )

#        # get the synset identifiers for this lemma
#        syn_ids_lemma = query_remote_syn_lemma( http, utf8_lemma )

#        lu_ids_syn = []
#        for syn_id in syn_ids_lemma:
#            lu_id = query_remote_lusyn_id( http, utf8_lemma, syn_id )
#            lu_ids_syn.append( lu_id )

#        return lu_ids_lemma, syn_ids_lemma, lu_ids_syn



#    def query_remote_lusyn_id( http, utf8_lemma, syn_id ):
#        """
#        query_remote_lusyn_id\
#        call cdb_syn with synset identifier -> synset xml -> lu_id lemma
#        """
#        scheme   = settings.CORNETTO_PROTOCOL
#        netloc   = settings.CORNETTO_HOST + ':' +  str( settings.CORNETTO_PORT )
#        params   = ""
#        fragment = ""

#        path = "cdb_syn"
#        if self.debug:
#            printf( "cornettodb/views/query_remote_lusyn_id: db_opt: %s" % path )

#        # output_opt: plain, html, xml
#        # 'xml' is actually xhtml (with markup), but it is not valid xml!
#        # 'plain' is actually valid xml (without markup)
#        output_opt = "plain"
#        if self.debug:
#            printf( "cornettodb/views/query_remote_lusyn_id: output_opt: %s" % output_opt )

#        action = "runQuery"
#        if self.debug:
#            printf( "cornettodb/views/query_remote_lusyn_id: action: %s" % action )
#            printf( "cornettodb/views/query_remote_lusyn_id: query: %s" % syn_id )
#    
#        qdict = {}
#        qdict[ "action" ]  = action
#        qdict[ "query" ]   = syn_id
#        qdict[ "outtype" ] = output_opt

#        query = urllib.urlencode( qdict )

#        db_url_tuple = ( scheme, netloc, path, params, query, fragment )
#        db_url = urlparse.urlunparse( db_url_tuple )
#        if self.debug:
#            printf( "db_url: %s" % db_url )

#        resp, content = http.request( db_url, "GET" )
#        if self.debug:
#            printf( "resp:\n%s" % resp )
#        #    printf( "content:\n%s" % content )
#        #    printf( "content is of type: %s" % type( content ) )        # <type 'str'>

#        xml_data = eval( content )
#        root = etree.fromstring( xml_data )

#        synonyms = []
#        # find <synonyms> anywhere in the tree
#        elem_synonyms = root.find( ".//synonyms" )
#        for elem_synonym in elem_synonyms:
#            synonym_str = elem_synonym.get( "c_lu_id-previewtext" )        # get "c_lu_id-previewtext" attribute
#            # synonym_str ends with ":<num>"
#            synonym = synonym_str.split( ':' )[ 0 ].strip()

#            utf8_synonym = synonym.encode( 'utf-8' )
#            if utf8_synonym != utf8_lemma:
#                synonyms.append( synonym )
#                if self.debug:
#                    printf( "synonym add: %s" % synonym )
#            else:
#                lu_id = elem_synonym.get( "c_lu_id" )                    # get "c_lu_id" attribute
#                if self.debug:
#                    printf( "lu_id: %s" % lu_id )
#                    printf( "synonym skip lemma: %s" % synonym )

#        return lu_id



#    def query_cornet( annotator_id, utf8_lemma, category ):
#        """\
#        cornet_query()
#        A variant of query_remote(), combining several queries for the dutchsemcor GUI
#        -1- call cdb_syn with lemma -> syn_ids;
#        -2- for each syn_id, call cdb_syn ->synset xml
#        -3- for each synset xml, find lu_id
#        -4- for each lu_id, call cdb_lu ->lu xml
#        -5- collect required info from lu & syn xml    
#        """

#        self.debug = False    # this function

#        printf( "cornettodb/views/cornet_query()" )
#        if utf8_lemma is None or utf8_lemma == "":
#            printf( "No lemma" )
#            return
#        else:
#            printf( "lemma: %s" % utf8_lemma.decode( 'utf-8' ).encode( 'latin-1' ) )
#            printf( "category: %s" % category )

#        http, resp, content = remote_open( self.debug )

#        if resp is None:
#            template = "cornettodb/error.html"
#            dictionary = { 'DSC_HOME' : settings.DSC_HOME }
#            return template, dictionary


#        status = int( resp.get( "status" ) )
#        printf( "status: %d" % status )

#        if status != 200:
#            # e.g. 400: Bad Request, 404: Not Found
#            printf( "status: %d\nreason: %s" % ( resp.status, resp.reason ) )
#            dict_err = \
#            { 
#                "status" : settings.CORNETTO_HOST + " error: " + str(status),
#                "msg"    : resp.reason
#            }
#            return dict_err

#        # read the domain cvs file, and return the dictionaries
#        domains_dutch, domains_abbrev = get_domains()

#        syn_ids    = []    # used syn_ids, skipping filtered
#        lu_ids     = []    # used lu_ids, skipping filtered
#        lu_ids_syn = []    # lu_ids derived from syn_ids, unfiltered

#        # get the raw (unfiltered) synset identifiers for this lemma
#        syn_lemma_self.debug = False
#        syn_ids_raw = query_remote_syn_lemma( syn_lemma_self.debug, http, utf8_lemma )

#        # get the raw (unfiltered) lexical unit identifiers for this lemma
#        lu_lemma_self.debug = False
#        lu_ids_raw = query_remote_lu_lemma( lu_lemma_self.debug, http, utf8_lemma )

#        # required lu info from the lu xml:
#        resumes_lu = []
#        morphos_lu = []
#        examplestext_lulist = []    # list-of-lists
#        examplestype_lulist = []    # list-of-lists
#        examplessubtype_lulist = []    # list-of-lists

#        # required syn info from the synset xml:
#        definitions_syn    = []        # list
#        differentiaes_syn  = []        # list
#        synonyms_synlist   = []        # list-of-lists
#        relations_synlist  = []        # list-of-lists
#        hyperonyms_synlist = []        # list-of-lists
#        hyponyms_synlist   = []        # list-of-lists
#        relations_synlist  = []        # list-of-lists
#        relnames_synlist   = []        # list-of-lists
#        domains_synlist    = []        # list-of-lists

#        remained = 0    # maybe less than lu_ids because of category filtering

#        for syn_id in syn_ids_raw:
#            if self.debug:
#                printf( "syn_id: %s" % syn_id )

#            syn_id_self.debug = False
#            lu_id, definition, differentiae, synonyms, hyperonyms, hyponyms, relations, relnames, domains = \
#                query_remote_syn_id( syn_id_self.debug, http, utf8_lemma, syn_id, domains_abbrev )

#            lu_ids_syn.append( lu_id )

#            lui_id_self.debug = False
#            if self.debug:
#                printf( "lu_id: %s" % lu_id )
#            formcat, morpho, resume, examples_text, examples_type, examples_subtype = \
#                query_remote_lu_id( lui_id_self.debug, http, lu_id )

#            if not ( \
#                ( category == '?' )                       or \
#                ( category == 'a' and formcat == 'adj' )  or \
#                ( category == 'n' and formcat == 'noun' ) or \
#                ( category == 'v' and formcat == 'verb' ) ):
#                if self.debug:
#                    printf( "filtered category: formcat=%s, lu_id=%s" % (formcat, lu_id) )
#                continue

#            # collect all information
#            syn_ids.append( syn_id )
#            lu_ids.append( lu_id )

#            definitions_syn.append( definition )
#            differentiaes_syn.append( differentiae )
#            synonyms_synlist.append( synonyms )
#            hyperonyms_synlist.append( hyperonyms )
#            relations_synlist.append( relations )
#            relnames_synlist.append( relnames )
#            hyponyms_synlist.append( hyponyms )
#            domains_synlist.append( domains )

#            resumes_lu.append( resume )
#            morphos_lu.append( morpho )

#            examplestext_lulist.append( examples_text )
#            examplestype_lulist.append( examples_type )
#            examplessubtype_lulist.append( examples_subtype )

#            if self.debug:
#                printf( "morpho: %s\nresume: %s\nexamples:" % (morpho, resume) )
#                for canoexample in canoexamples:
#                    printf( canoexample.encode('latin-1') )    # otherwise fails with non-ascii chars
#                for textexample in textexamples:
#                    printf( textexample.encode('latin-1') )    # otherwise fails with non-ascii chars

#        lusyn_mismatch = False    # assume no problem
#        # Compare number of lu ids with syn_ids
#        if len( lu_ids_raw ) != len( syn_ids_raw):    # length mismatch
#            lusyn_mismatch = True
#            printf( "query_cornet: %d lu ids, %d syn ids: NO MATCH" % (len(lu_ids_raw), len(syn_ids_raw) ) )

#        # Check lu_ids from syn to lu_ids_raw (from lemma)
#        for i in range( len( lu_ids_raw ) ):
#            lu_id_raw = lu_ids_raw[ i ]
#            try:
#                idx = lu_ids_syn.index( lu_id_raw )
#                if lu_ids_syn.count( lu_id_raw ) != 1:
#                    lusyn_mismatch = True
#                    printf( "query_cornet: %s lu id: DUPLICATES" % lu_id_raw )
#            except:
#                lusyn_mismatch = True
#                printf( "query_cornet: %s lu id: NOT FOUND" % lu_id_raw )


#        dictlist = []

#        for i in range( len( syn_ids ) ):
#        #    printf( "i: %d" % i )

#            dict = {}
#            dict[ "no" ] = i

#            lu_id = lu_ids[ i ]
#            dict[ "lu_id" ] = lu_id

#            syn_id = syn_ids[ i ]
#            dict[ "syn_id" ] = syn_id

#            dict[ "tag_count" ] = '?'

#            resume = resumes_lu[ i ]
#            dict[ "resume" ] = resume

#            morpho = morphos_lu[ i ]
#            dict[ "morpho" ] = morpho

#            examplestext = examplestext_lulist[ i ]
#            dict[ "examplestext"] = examplestext

#            examplestype = examplestype_lulist[ i ]
#            dict[ "examplestype"] = examplestype

#            examplessubtype = examplessubtype_lulist[ i ]
#            dict[ "examplessubtype"] = examplessubtype

#            definition = definitions_syn[ i ]
#            dict[ "definition" ] = definition

#            differentiae = differentiaes_syn[ i ]
#            dict[ "differentiae" ] = differentiae

#            synonyms = synonyms_synlist[ i ]
#            dict[ "synonyms"] = synonyms

#            hyperonyms = hyperonyms_synlist[ i ]
#            dict[ "hyperonyms"] = hyperonyms

#            hyponyms = hyponyms_synlist[ i ]
#            dict[ "hyponyms"] = hyponyms

#            relations = relations_synlist[ i ]
#            dict[ "relations"] = relations

#            relnames = relnames_synlist[ i ]
#            dict[ "relnames"] = relnames

#            domains = domains_synlist[ i ]
#            dict[ "domains"] = domains

#            dictlist.append( dict )    

#        # pack in "superdict"
#        result = \
#        { 
#            "status"          : "ok",
#            "source"          : "cornetto",
#            "lusyn_mismatch"  : lusyn_mismatch,
#            "lusyn_retrieved" : len( syn_ids_raw ),
#            "lusyn_remained"  : len( syn_ids ),
#            "lists_data"      : dictlist
#        }

#        return result



#    def query_remote_lu_lemma( utf8_lemma ):
#        """\
#        call cdb_lu with lemma -> yields lexical units
#        """
#        scheme   = settings.CORNETTO_PROTOCOL
#        netloc   = settings.CORNETTO_HOST + ':' +  str( settings.CORNETTO_PORT )
#        params   = ""
#        fragment = ""

#        path = "cdb_lu"
#        if self.debug:
#            printf( "cornettodb/views/query_remote_lu_lemma: db_opt: %s" % path )

#        action = "queryList"
#        if self.debug:
#            printf( "cornettodb/views/query_remote_lu_lemma: action: %s" % action )

#        qdict = {}
#        qdict[ "action" ] = action
#        qdict[ "word" ]   = utf8_lemma

#        query = urllib.urlencode( qdict )

#        db_url_tuple = ( scheme, netloc, path, params, query, fragment )
#        db_url = urlparse.urlunparse( db_url_tuple )
#        if self.debug:
#            printf( "db_url: %s" % db_url )

#        resp, content = http.request( db_url, "GET" )
#        if self.debug:
#            printf( "resp:\n%s" % resp )
#            printf( "content:\n%s" % content )
#        #    printf( "content is of type: %s" % type( content ) )

#        dict_list = []
#        dict_list = eval( content )        # string to list

#        ids = []
#        items = len( dict_list )
#        if self.debug:
#            printf( "items: %d" % items )

#        # lu dict: like syn dict, but with pos: part-of-speech
#        for dict in dict_list:
#            if self.debug:
#                printf( dict )

#            seq_nr = dict[ "seq_nr" ]   # sense number
#            value  = dict[ "value" ]    # lexical unit identifier
#            form   = dict[ "form" ]     # lemma
#            pos    = dict[ "pos" ]      # part of speech
#            label  = dict[ "label" ]    # label to be shown

#            if self.debug:
#                printf( "seq_nr: %s" % seq_nr )
#                printf( "value:  %s" % value )
#                printf( "form:   %s" % form )
#                printf( "pos:    %s" % pos )
#                printf( "label:  %s" % label )

#            if value != "":
#                ids.append( value )

#        return ids



#    def lemma2formcats( utf8_lemma ):
#        """\
#        get the form-cats for this lemma.
#        """
#        self.debug = False

#        http, resp, content = remote_open( self.debug )

#        if resp is None:
#            template = "cornettodb/error.html"
#            dictionary = { 'DSC_HOME' : settings.DSC_HOME }
#            return template, dictionary


#        status = int( resp.get( "status" ) )
#        if status != 200:
#            # e.g. 400: Bad Request, 404: Not Found
#            printf( "status: %d\nreason: %s" % ( resp.status, resp.reason ) )
#            template = "cornettodb/error.html"
#            message = "Cornetto " + _( "initialization" )
#            dict = \
#            { 
#                'DSC_HOME':    settings.DSC_HOME,
#                'message':    message,
#                'status':    resp.status,
#                'reason':    resp.reason, \
#            }
#            return template, dictionary


#        # get the lexical unit identifiers for this lemma
#        lu_ids = query_remote_lu_lemma( self.debug, http, utf8_lemma )

#        scheme   = settings.CORNETTO_PROTOCOL
#        netloc   = settings.CORNETTO_HOST + ':' +  str( settings.CORNETTO_PORT )
#        params   = ""
#        fragment = ""

#        path = "cdb_lu"
#        if self.debug:
#            printf( "cornettodb/views/query_remote_lu_id_formcat: db_opt: %s" % path )

#        output_opt = "plain"
#        if self.debug:
#            printf( "cornettodb/views/query_remote_lu_id_formcat: output_opt: %s" % output_opt )

#        action = "runQuery"
#        if self.debug:
#            printf( "cornettodb/views/query_remote_lu_id_formcat: action: %s" % action )

#        formcats = []
#        for lu_id in lu_ids:
#            if self.debug:
#                printf( "cornettodb/views/query_remote_lu_id_formcat: query: %s" % lu_id )

#            qdict = {}
#            qdict[ "action" ]  = action
#            qdict[ "query" ]   = lu_id
#            qdict[ "outtype" ] = output_opt

#            query = urllib.urlencode( qdict )

#            db_url_tuple = ( scheme, netloc, path, params, query, fragment )
#            db_url = urlparse.urlunparse( db_url_tuple )
#            if self.debug:
#                printf( "db_url: %s" % db_url )

#            resp, content = http.request( db_url, "GET" )
#            if self.debug:
#                printf( "resp:\n%s" % resp )

#            xml_data = eval( content )
#            root = etree.fromstring( xml_data )

#            # morpho
#            morpho = ""
#            elem_form = root.find( ".//form" )
#            if elem_form is not None:
#                formcat = elem_form.get( "form-cat" )        # get "form-cat" attribute
#                if formcat is None:
#                    formcat = '?'

#                count = formcats.count( formcat )
#                if count == 0:
#                    formcats.append( formcat )

#        return formcats



#    def query_remote_lu_id(lu_id ):
#        """\
#        call cdb_lu with lexical unit identifier -> yields the lexical unit xml;
#        from the xml collect the morpho-syntax, resumes+definitions, examples.
#        """
#        scheme   = settings.CORNETTO_PROTOCOL
#        netloc   = settings.CORNETTO_HOST + ':' +  str( settings.CORNETTO_PORT )
#        params   = ""
#        fragment = ""

#        path = "cdb_lu"
#        if self.debug:
#            printf( "cornettodb/views/query_remote_lu_id: db_opt: %s" % path )

#        # output_opt: plain, html, xml
#        # 'xml' is actually xhtml (with markup), but it is not valid xml!
#        # 'plain' is actually valid xml (without markup)
#        output_opt = "plain"
#        if self.debug:
#            printf( "cornettodb/views/query_remote_lu_id: output_opt: %s" % output_opt )

#        action = "runQuery"
#        if self.debug:
#            printf( "cornettodb/views/query_remote_lu_id: action: %s" % action )
#            printf( "cornettodb/views/query_remote_lu_id: query: %s" % lu_id )
#    
#        qdict = {}
#        qdict[ "action" ]  = action
#        qdict[ "query" ]   = lu_id
#        qdict[ "outtype" ] = output_opt

#        query = urllib.urlencode( qdict )

#        db_url_tuple = ( scheme, netloc, path, params, query, fragment )
#        db_url = urlparse.urlunparse( db_url_tuple )
#        if self.debug:
#            printf( "db_url: %s" % db_url )

#        resp, content = http.request( db_url, "GET" )
#        if self.debug:
#            printf( "resp:\n%s" % resp )
#        #    printf( "content:\n%s" % content )
#        #    printf( "content is of type: %s" % type( content ) )        #<type 'str'>

#        xml_data = eval( content )
#        root = etree.fromstring( xml_data )

#        # morpho
#        morpho = ""
#        elem_form = root.find( ".//form" )
#        if elem_form is not None:
#            formcat = elem_form.get( "form-cat" )        # get "form-cat" attribute
#            if formcat is not None:
#                if formcat == "adj":
#                    morpho = 'a'

#                elif formcat == "noun":
#                    morpho = 'n'

#                    elem_article = root.find( ".//sy-article" )
#                    if elem_article is not None and elem_article.text is not None:
#                        article = elem_article.text        # lidwoord
#                        morpho += "-" + article

#                    elem_count = root.find( ".//sem-countability" )
#                    if elem_count is not None and elem_count.text is not None:
#                        countability = elem_count.text
#                        if countability == "count":
#                            morpho += "-t"
#                        elif countability == "uncount":
#                            morpho += "-nt"

#                elif formcat == "verb":
#                    morpho = 'v'

#                    elem_trans = root.find( ".//sy-trans" )
#                    if elem_trans is not None and elem_trans.text is not None:
#                        transitivity = elem_trans.text
#                        if transitivity == "tran":
#                            morpho += "-tr"
#                        elif transitivity == "intr":
#                            morpho += "-intr"
#                        else:        # should not occur
#                            morpho += "-"
#                            morpho += transitivity

#                    elem_separ = root.find( ".//sy-separ" )
#                    if elem_separ is not None and elem_separ.text is not None:
#                        separability = elem_separ.text
#                        if separability == "sch":
#                            morpho += "-sch"
#                        elif separability == "onsch":
#                            morpho += "-onsch"
#                        else:        # should not occur
#                            morpho += "-"
#                            morpho += separability

#                    elem_reflexiv = root.find( ".//sy-reflexiv" )
#                    if elem_reflexiv is not None and elem_reflexiv.text is not None:
#                        reflexivity = elem_reflexiv.text
#                        if reflexivity == "refl":
#                            morpho += "-refl"
#                        elif reflexivity == "nrefl":
#                            morpho += "-nrefl"
#                        else:        # should not occur
#                            morpho += "-"
#                            morpho += reflexivity

#                elif formcat == "adverb":
#                    morpho = 'd'

#                else:
#                    morpho = '?'

#        # find <sem-resume> anywhere in the tree
#        elem_resume = root.find( ".//sem-resume" )
#        if elem_resume is not None:
#            resume = elem_resume.text
#        else:
#            resume = ""

#        examples_text = []
#        examples_type = []
#        examples_subtype = []

#        # find <form_example> anywhere in the tree
#        examples = root.findall( ".//example" )
#        for example in examples:
#            example_id = example.get( "r_ex_id" )

#            elem_type = example.find( "syntax_example/sy-type" )
#            if elem_type is not None:
#                type_text = elem_type.text
#                if type_text is None:
#                    type_text = ""
#            else:
#                type_text = ""

#            elem_subtype = example.find( "syntax_example/sy-subtype" )
#            if elem_subtype is not None:
#                subtype_text = elem_subtype.text
#                if subtype_text is None:
#                    subtype_text = ""
#            else:
#                subtype_text = ""

#            # there can be a canonical and/or textual example, 
#            # they share the type and subtype
#            elem_canonical = example.find( "form_example/canonicalform" )    # find <canonicalform> child
#            if elem_canonical is not None and elem_canonical.text is not None:
#                example_text = elem_canonical.text
#                example_out = example_text.encode( "iso-8859-1", "replace" )

#                if self.debug:
#                    printf( "subtype, r_ex_id: %s: %s" % ( example_id, example_out ) )
#                if subtype_text != "idiom":
#                    examples_text.append( example_text )
#                    examples_type.append( type_text )
#                    examples_subtype.append( subtype_text )
#                else:
#                    if self.debug:
#                        printf( "filter idiom: %s" % example_out)
#    
#            elem_textual = example.find( "form_example/textualform" )        # find <textualform> child
#            if elem_textual is not None and elem_textual.text is not None:
#                example_text = elem_textual.text
#                example_out = example_text.encode( "iso-8859-1", "replace" )

#                if self.debug:
#                    printf( "subtype r_ex_id: %s: %s" % ( example_id, example_out ) )
#                if subtype_text != "idiom":
#                    examples_text.append( example_text )
#                    examples_type.append( type_text )
#                    examples_subtype.append( subtype_text )
#                else:
#                    if self.debug:
#                        printf( "filter idiom: %s" % example_out)

#        return formcat, morpho, resume, examples_text, examples_type, examples_subtype


        

#    def get_synset(self, syn_id, utf8_lemma, domains_abbrev ):
#        """Parse synset data"""
#        root = self.get_synset_xml(syn_id)

#        synonyms = []
#        # find <synonyms> anywhere in the tree
#        elem_synonyms = root.find( ".//synonyms" )
#        for elem_synonym in elem_synonyms:
#            synonym_str = elem_synonym.get( "c_lu_id-previewtext" )        # get "c_lu_id-previewtext" attribute
#            # synonym_str ends with ":<num>"
#            synonym = synonym_str.split( ':' )[ 0 ].strip()

#            utf8_synonym = synonym.encode( 'utf-8' )
#            if utf8_synonym != utf8_lemma:
#                synonyms.append( synonym )
#                if self.debug:
#                    printf( "synonym add: %s" % synonym )
#            else:
#                lu_id = elem_synonym.get( "c_lu_id" )        # get "c_lu_id" attribute
#                if self.debug:
#                    printf( "lu_id: %s" % lu_id )
#                    printf( "synonym skip lemma: %s" % synonym )

#        definition = ""
#        elem_definition = root.find( ".//definition" )
#        if elem_definition is not None and elem_definition.text is not None:
#            definition = elem_definition.text

#        differentiae = ""
#        elem_differentiae = root.find( "./differentiae/" )
#        if elem_differentiae is not None and elem_differentiae.text is not None:
#            differentiae = elem_differentiae.text

#        if self.debug:
#            print( "definition: %s" % definition.encode( 'utf-8' ) )
#            print( "differentiae: %s" % differentiae.encode( 'utf-8' ) )

#        hyperonyms = []
#        hyponyms = []
#        relations_all = []
#        relnames_all = []
#        # find internal <wn_internal_relations> anywhere in the tree
#        elem_intrelations = root.find( ".//wn_internal_relations" )
#        for elem_relation in elem_intrelations:
#            relations = []
#            relation_str = elem_relation.get( "target-previewtext" )    # get "target-previewtext" attribute
#            name = elem_relation.get( "relation_name" )
#            target = elem_relation.get( "targer" )
#            relation_list = relation_str.split( ',' )
#            for relation_str in relation_list:
#                relation = relation_str.split( ':' )[ 0 ].strip()
#                relations.append( relation )

#                relations_all.append( relation )
#                relnames_all.append( name )

#            if name == "HAS_HYPERONYM":
#                if self.debug:
#                    printf( "target: %s" % target )
#                hyperonyms.append( relations )
#            elif name == "HAS_HYPONYM":
#                if self.debug:
#                    printf( "target: %s" % target )
#                hyponyms.append( relations )

#        # we could keep the relation sub-lists separate on the basis of their "target" attribute
#        # but for now we flatten the lists
#        hyperonyms = flatten( hyperonyms )
#        hyponyms   = flatten( hyponyms )
#        if self.debug:
#            printf( "hyperonyms: %s" % hyperonyms )
#            printf( "hyponyms: %s" % hyponyms )

#        domains = []
#        # find <wn_domains> anywhere in the tree
#        wn_domains = root.find( ".//wn_domains" )
#        for dom_relation in wn_domains:
#            domains_en = dom_relation.get( "term" )                        # get "term" attribute
#            if self.debug:
#                if domains_en:
#                    printf( "domain: %s" % domains_en )
#        
#            # use dutch domain name[s], abbreviated
#            domain_list = domains_en.split( ' ' )
#            for domain_en in domain_list:
#                try:
#                    domain_nl = domains_abbrev[ domain_en ]
#                    if domain_nl.endswith( '.' ):        # remove trailing '.'
#                        domain_nl = domain_nl[ : -1]    # remove last character
#                except:
#                    printf( "failed to convert domain: %s" % domain_en )
#                    domain_nl = domain_en

#                if domains.count( domain_nl ) == 0:        # append if new
#                    domains.append( domain_nl )

#        return lu_id, definition, differentiae, synonyms, hyperonyms, hyponyms, relations_all, relnames_all, domains




########NEW FILE########
__FILENAME__ = freeling
###############################################################
#  PyNLPl - FreeLing Library
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Radboud University Nijmegen
#       
#       Licensed under GPLv3
# 
# This is a Python library for on-the-fly communication with
# a FreeLing server. Allowing on-the-fly lemmatisation and
# PoS-tagging. It is recommended to pass your data on a 
# sentence-by-sentence basis to FreeLingClient.process()
#
# Make sure to start Freeling (analyzer)  with the --server 
# and --flush flags !!!!!
#
###############################################################

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import    
from pynlpl.common import u
    
import socket
import sys

class FreeLingClient(object):
    def __init__(self, host, port, encoding='utf-8', timeout=120.0):
        """Initialise the client, set channel to the path and filename where the server's .in and .out pipes are (without extension)"""
        self.encoding = encoding
        self.BUFSIZE = 10240
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        self.socket.connect( (host,int(port)) )
        self.encoding = encoding
        self.socket.sendall('RESET_STATS\0')
        r = self.socket.recv(self.BUFSIZE)
        if not r.strip('\0') == 'FL-SERVER-READY':
            raise Exception("Server not ready")

        
    def process(self, sourcewords, debug=False):
        """Process a list of words, passing it to the server and realigning the output with the original words"""

        if isinstance( sourcewords, list ) or isinstance( sourcewords, tuple ):
            sourcewords_s = " ".join(sourcewords)            
        else:
            sourcewords_s = sourcewords
            sourcewords = sourcewords.split(' ')
        
        self.socket.sendall(sourcewords_s.encode(self.encoding) +'\n\0')
        if debug: print("Sent:",sourcewords_s.encode(self.encoding),file=sys.stderr)
        
        results = []
        done = False
        while not done:    
            data = b""
            while not data:
                buffer = self.socket.recv(self.BUFSIZE)
                if debug: print("Buffer: ["+repr(buffer)+"]",file=sys.stderr)
                if buffer[-1] == '\0':
                    data += buffer[:-1]
                    done = True
                    break
                else:
                    data += buffer

            
            data = u(data,self.encoding)
            if debug: print("Received:",data,file=sys.stderr) 

            for i, line in enumerate(data.strip(' \t\0\r\n').split('\n')):
                if not line.strip():
                    done = True
                    break
                else:
                    cols = line.split(" ")
                    subwords = cols[0].lower().split("_")
                    if len(cols) > 2: #this seems a bit odd?
                        for word in subwords: #split multiword expressions
                            results.append( (word, cols[1], cols[2], i, len(subwords) > 1 ) ) #word, lemma, pos, index, multiword?

        sourcewords = [ w.lower() for w in sourcewords ]          

        alignment = []
        for i, sourceword in enumerate(sourcewords):
            found = False
            best = 0  
            distance = 999999          
            for j, (targetword, lemma, pos, index, multiword) in enumerate(results):
                if sourceword == targetword and abs(i-j) < distance:
                    found = True
                    best = j
                    distance = abs(i-j)

            if found:
                alignment.append(results[best])
            else:                
                alignment.append((None,None,None,None,False)) #no alignment found
        return alignment


########NEW FILE########
__FILENAME__ = frogclient
###############################################################
#  PyNLPl - Frog Client - Version 1.4.1
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#
#       Derived from code by Rogier Kraf
#
#       Licensed under GPLv3
#
# This is a Python library for on-the-fly communication with
# a Frog/Tadpole Server. Allowing on-the-fly lemmatisation and
# PoS-tagging. It is recommended to pass your data on a
# sentence-by-sentence basis to FrogClient.process()
#
###############################################################

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from pynlpl.common import u

import socket

class FrogClient:
    def __init__(self,host="localhost",port=12345, server_encoding="utf-8", returnall=False, timeout=120.0, ner=False):
        """Create a client connecting to a Frog or Tadpole server."""
        self.BUFSIZE = 4096
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        self.socket.connect( (host,int(port)) )
        self.server_encoding = server_encoding
        self.returnall = returnall




    def process(self,input_data, source_encoding="utf-8", return_unicode = True, oldfrog=False):
        """Receives input_data in the form of a str or unicode object, passes this to the server, with proper consideration for the encodings, and returns the Frog output as a list of tuples: (word,pos,lemma,morphology), each of these is a proper unicode object unless return_unicode is set to False, in which case raw strings will be returned. Return_unicode is no longer optional, it is fixed to True, parameter is still there only for backwards-compatibility."""
        if isinstance(input_data, list) or isinstance(input_data, tuple):
            input_data = " ".join(input_data)



        input_data = u(input_data, source_encoding) #decode (or preferably do this in an earlier stage)
        input_data = input_data.strip(' \t\n')

        s = input_data.encode(self.server_encoding) +b'\r\n'
        if not oldfrog: s += b'EOT\r\n'
        self.socket.sendall(s) #send to socket in desired encoding
        output = []

        done = False
        while not done:
            data = b""
            while not data or data[-1] != b'\n':
                moredata = self.socket.recv(self.BUFSIZE)
                if not moredata: break
                data += moredata


            data = u(data,self.server_encoding)


            for line in data.strip(' \t\r\n').split('\n'):
                if line == "READY":
                    done = True
                    break
                elif line:
                    line = line.split('\t') #split on tab
                    if len(line) > 4 and line[0].isdigit(): #first column is token number
                        if line[0] == '1' and output:
                            if self.returnall:
                                output.append( (None,None,None,None, None,None,None, None) )
                            else:
                                output.append( (None,None,None,None) )
                        fields = line[1:]
                        parse1=parse2=ner=chunk=""
                        word,lemma,morph,pos = fields[0:4]
                        if len(fields) > 5:
                            ner = fields[5]
                        if len(fields) > 6:
                            chunk = fields[6]

                        if len(fields) < 5:
                            raise Exception("Can't process response line from Frog: ", repr(line), " got unexpected number of fields ", str(len(fields) + 1))

                        if self.returnall:
                            output.append( (word,lemma,morph,pos,ner,chunk,parse1,parse2) )
                        else:
                            output.append( (word,lemma,morph,pos) )

        return output

    def process_aligned(self,input_data, source_encoding="utf-8", return_unicode = True):
        output = self.process(input_data, source_encoding, return_unicode)
        outputwords = [ x[0] for x in output ]
        inputwords = input_data.strip(' \t\n').split(' ')
        alignment = self.align(inputwords, outputwords)
        for i, _ in enumerate(inputwords):
            targetindex = alignment[i]
            if targetindex == None:
                if self.returnall:
                    yield (None,None,None,None,None,None,None,None)
                else:
                    yield (None,None,None,None)
            else:
                yield output[targetindex]

    def align(self,inputwords, outputwords):
        """For each inputword, provides the index of the outputword"""
        alignment = []
        cursor = 0
        for inputword in inputwords:
            if len(outputwords) > cursor and outputwords[cursor] == inputword:
                alignment.append(cursor)
                cursor += 1
            elif len(outputwords) > cursor+1 and outputwords[cursor+1] == inputword:
                alignment.append(cursor+1)
                cursor += 2
            else:
                alignment.append(None)
                cursor += 1
        return alignment


    def __del__(self):
        self.socket.close()


########NEW FILE########
__FILENAME__ = common
#!/usr/bin/env python
#-*- coding:utf-8 -*-

###############################################################9
# PyNLPl - Common functions
#   by Maarten van Gompel
#   Centre for Language Studies
#   Radboud University Nijmegen
#   http://www.github.com/proycon/pynlpl
#   proycon AT anaproy DOT nl
#
#       Licensed under GPLv3
#
# This contains very common functions and language extensions
#
###############################################################

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

import datetime
from sys import stderr, version

## From http://code.activestate.com/recipes/413486/ (r7)
def Enum(*names):
   ##assert names, "Empty enums are not supported" # <- Don't like empty enums? Uncomment!

   class EnumClass(object):
      __slots__ = names
      def __iter__(self):        return iter(constants)
      def __len__(self):         return len(constants)
      def __getitem__(self, i):  return constants[i]
      def __repr__(self):        return 'Enum' + str(names)
      def __str__(self):         return 'enum ' + str(constants)

   class EnumValue(object):
      __slots__ = ('__value')
      def __init__(self, value): self.__value = value
      Value = property(lambda self: self.__value)
      EnumType = property(lambda self: EnumType)
      def __hash__(self):        return hash(self.__value)
      def __cmp__(self, other):
         # C fans might want to remove the following assertion
         # to make all enums comparable by ordinal value {;))
         assert self.EnumType is other.EnumType, "Only values from the same enum are comparable"
         return cmp(self.__value, other.__value)
      def __invert__(self):      return constants[maximum - self.__value]
      def __bool__(self):     return bool(self.__value)
      def __nonzero__(self):     return bool(self.__value) #Python 2.x
      def __repr__(self):        return str(names[self.__value])

   maximum = len(names) - 1
   constants = [None] * len(names)
   for i, each in enumerate(names):
      val = EnumValue(i)
      setattr(EnumClass, each, val)
      constants[i] = val
   constants = tuple(constants)
   EnumType = EnumClass()
   return EnumType


def u(s, encoding = 'utf-8', errors='strict'):
    #ensure s is properly unicode.. wrapper for python 2.6/2.7,
    if version < '3':
        #ensure the object is unicode
        if isinstance(s, unicode):
            return s
        else:
            return unicode(s, encoding,errors=errors)
    else:
        #will work on byte arrays
        if isinstance(s, str):
            return s
        else:
            return str(s,encoding,errors=errors)

def b(s):
    #ensure s is bytestring
    if version < '3':
        #ensure the object is unicode
        if isinstance(s, str):
            return s
        else:
            return s.encode('utf-8')
    else:
        #will work on byte arrays
        if isinstance(s, bytes):
            return s
        else:
            return s.encode('utf-8')

def isstring(s): #Is this a proper string?
    return isinstance(s, str) or (version < '3' and isinstance(s, unicode))

def log(msg, **kwargs):
    """Generic log method. Will prepend timestamp.

    Keyword arguments:
      system   - Name of the system/module
      indent   - Integer denoting the desired level of indentation
      streams  - List of streams to output to
      stream   - Stream to output to (singleton version of streams)
    """
    if 'debug' in kwargs:
        if 'currentdebug' in kwargs:
            if kwargs['currentdebug'] < kwargs['debug']:
                return False
        else:
            return False #no currentdebug passed, assuming no debug mode and thus skipping message

    s = "[" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "] "
    if 'system' in kwargs:
        s += "[" + system + "] "


    if 'indent' in kwargs:
        s += ("\t" * int(kwargs['indent']))

    s += u(msg)

    if s[-1] != '\n':
        s += '\n'

    if 'streams' in kwargs:
        streams = kwargs['streams']
    elif 'stream' in kwargs:
        streams = [kwargs['stream']]
    else:
        streams = [stderr]

    for stream in streams:
        stream.write(s)
    return s

########NEW FILE########
__FILENAME__ = datatypes
#---------------------------------------------------------------
# PyNLPl - Data Types
#   by Maarten van Gompel
#   Centre for Language Studies
#   Radboud University Nijmegen
#   http://www.github.com/proycon/pynlpl
#   proycon AT anaproy DOT nl
#
#   Based in large part on MIT licensed code from
#    AI: A Modern Appproach : http://aima.cs.berkeley.edu/python/utils.html
#    Peter Norvig
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------

"""This library contains various extra data types, based to a certain extend on MIT-licensed code from Peter Norvig, AI: A Modern Appproach : http://aima.cs.berkeley.edu/python/utils.html"""

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from pynlpl.common import u

import random
import bisect
import array
from sys import version as PYTHONVERSION


class Queue(object): #from AI: A Modern Appproach : http://aima.cs.berkeley.edu/python/utils.html
    """Queue is an abstract class/interface. There are three types:
        Python List: A Last In First Out Queue (no Queue object necessary).
        FIFOQueue(): A First In First Out Queue.
        PriorityQueue(lt): Queue where items are sorted by lt, (default <).
    Each type supports the following methods and functions:
        q.append(item)  -- add an item to the queue
        q.extend(items) -- equivalent to: for item in items: q.append(item)
        q.pop()         -- return the top item from the queue
        len(q)          -- number of items in q (also q.__len())."""

    def extend(self, items):
        """Append all elements from items to the queue"""
        for item in items: self.append(item)


#note: A Python list is a LIFOQueue / Stack

class FIFOQueue(Queue): #adapted from AI: A Modern Appproach : http://aima.cs.berkeley.edu/python/utils.html
    """A First-In-First-Out Queue"""
    def __init__(self, data = []):
        self.data = data
        self.start = 0

    def append(self, item):
        self.data.append(item)

    def __len__(self):
        return len(self.data) - self.start

    def extend(self, items):
        """Append all elements from items to the queue"""
        self.data.extend(items)

    def pop(self):
        """Retrieve the next element in line, this will remove it from the queue"""
        e = self.data[self.start]
        self.start += 1
        if self.start > 5 and self.start > len(self.data)//2:
            self.data = self.data[self.start:]
            self.start = 0
        return e

class PriorityQueue(Queue): #Heavily adapted/extended, originally from AI: A Modern Appproach : http://aima.cs.berkeley.edu/python/utils.html
    """A queue in which the maximum (or minumum) element is returned first,
    as determined by either an external score function f (by default calling
    the objects score() method). If minimize=True, the item with minimum f(x) is
    returned first; otherwise is the item with maximum f(x) or x.score().

    length can be set to an integer > 0. Items will only be added to the queue if they're better or equal to the worst scoring item. If set to zero, length is unbounded.
    blockworse can be set to true if you want to prohibit adding worse-scoring items to the queue. Only items scoring better than the *BEST* one are added.
    blockequal can be set to false if you also want to prohibit adding equally-scoring items to the queue.
    (Both parameters default to False)
    """
    def __init__(self, data =[], f = lambda x: x.score, minimize=False, length=0, blockworse=False, blockequal=False,duplicates=True):
        self.data = []
        self.f = f
        self.minimize=minimize
        self.length = length
        self.blockworse=blockworse
        self.blockequal=blockequal
        self.duplicates= duplicates
        self.bestscore = None
        for item in data:
            self.append(item)

    def append(self, item):
        """Adds an item to the priority queue (in the right place), returns True if successfull, False if the item was blocked (because of a bad score)"""
        f = self.f(item)
        if callable(f):
            score = f()
        else:
            score = f

        if not self.duplicates:
            for s, i in self.data:
                if s == score and item == i:
                    #item is a duplicate, don't add it
                    return False

        if self.length and len(self.data) == self.length:
                #Fixed-length priority queue, abort when queue is full and new item scores worst than worst scoring item.
                if self.minimize:
                    worstscore = self.data[-1][0]
                    if score >= worstscore:
                        return False
                else:
                    worstscore = self.data[0][0]
                    if score <= worstscore:
                        return False

        if self.blockworse and self.bestscore != None:
            if self.minimize:
                if score > self.bestscore:
                    return False
            else:
                if score < self.bestscore:
                    return False
        if self.blockequal and self.bestscore != None:
            if self.bestscore == score:
                return False
        if (self.bestscore == None) or (self.minimize and score < self.bestscore) or (not self.minimize and score > self.bestscore):
            self.bestscore = score
        bisect.insort(self.data, (score, item))
        if self.length:
            #fixed length queue: queue is now too long, delete worst items
            while len(self.data) > self.length:
                if self.minimize:
                    del self.data[-1]
                else:
                    del self.data[0]
        return True

    def __exists__(self, item):
        return (item in self.data)

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        """Iterate over all items, in order from best to worst!"""
        if self.minimize:
            f = lambda x: x
        else:
            f = reversed
        for score, item in f(self.data):
            yield item

    def __getitem__(self, i):
        """Item 0 is always the best item!"""
        if isinstance(i, slice):
            indices = i.indices(len(self))
            if self.minimize:
                return PriorityQueue([ self.data[j][1] for j in range(*indices) ],self.f, self.minimize, self.length, self.blockworse, self.blockequal)
            else:
                return PriorityQueue([ self.data[(-1 * j) - 1][1] for j in range(*indices) ],self.f, self.minimize, self.length, self.blockworse, self.blockequal)
        else:
            if self.minimize:
                return self.data[i][1]
            else:
                return self.data[(-1 * i) - 1][1]

    def pop(self):
        """Retrieve the next element in line, this will remove it from the queue"""
        if self.minimize:
            return self.data.pop(0)[1]
        else:
            return self.data.pop()[1]


    def score(self, i):
        """Return the score for item x (cheap lookup), Item 0 is always the best item"""
        if self.minimize:
            return self.data[i][0]
        else:
            return self.data[(-1 * i) - 1][0]

    def prune(self, n):
        """prune all but the first (=best) n items"""
        if self.minimize:
            self.data = self.data[:n]
        else:
            self.data = self.data[-1 * n:]


    def randomprune(self,n):
        """prune down to n items at random, disregarding their score"""
        self.data = random.sample(self.data, n)

    def stochasticprune(self,n):
        """prune down to n items, chance of an item being pruned is reverse proportional to its score"""
        raise NotImplemented


    def prunebyscore(self, score, retainequalscore=False):
        """Deletes all items below/above a certain score from the queue, depending on whether minimize is True or False. Note: It is recommended (more efficient) to use blockworse=True / blockequal=True instead! Preventing the addition of 'worse' items."""
        if retainequalscore:
            if self.minimize:
                f = lambda x: x[0] <= score
            else:
                f = lambda x: x[0] >= score
        else:
            if self.minimize:
                f = lambda x: x[0] < score
            else:
                f = lambda x: x[0] > score
        self.data = filter(f, self.data)

    def __eq__(self, other):
        return (self.data == other.data) and (self.minimize == other.minimize)


    def __repr__(self):
        return repr(self.data)

    def __add__(self, other):
        """Priority queues can be added up, as long as they all have minimize or maximize (rather than mixed). In case of fixed-length queues, the FIRST queue in the operation will be authorative for the fixed lengthness of the result!"""
        assert (isinstance(other, PriorityQueue) and self.minimize == other.minimize)
        return PriorityQueue(self.data + other.data, self.f, self.minimize, self.length, self.blockworse, self.blockequal)

class Tree(object):
    """Simple tree structure. Nodes are themselves trees."""

    def __init__(self, value = None, children = None):
        self.parent = None
        self.value = value
        if not children:
            self.children = None
        else:
            for c in children:
                self.append(c)

    def leaf(self):
        """Is this a leaf node or not?"""
        return not self.children

    def __len__(self):
        if not self.children:
            return 0
        else:
            return len(self.children)

    def __bool__(self):
        return True

    def __iter__(self):
        """Iterate over all items in the tree"""
        for c in self.children:
            return c

    def append(self, item):
        """Add an item to the Tree"""
        if not isinstance(item, Tree):
            return ValueError("Can only append items of type Tree")
        if not self.children: self.children = []
        item.parent = self
        self.children.append(item)

    def __getitem__(self, index):
        """Retrieve a specific item, by index, from the Tree"""
        assert isinstance(index,int)
        try:
            return self.children[index]
        except:
            raise

    def __str__(self):
        return str(self.value)

    def __unicode__(self): #Python 2.x
        return u(self.value)




class Trie(object):
    """Simple trie structure. Nodes are themselves tries, values are stored on the edges, not the nodes."""

    def __init__(self, sequence = None):
        self.parent = None
        self.children = None
        self.value = None
        if sequence:
            self.append(sequence)

    def leaf(self):
        """Is this a leaf node or not?"""
        return not self.children

    def root(self):
        """Returns True if this is the root of the Trie"""
        return not self.parent

    def __len__(self):
        if not self.children:
            return 0
        else:
            return len(self.children)

    def __bool__(self):
        return True

    def __iter__(self):
        if self.children:
            for key in self.children.keys():
                yield key

    def items(self):
        if self.children:
            for key, trie in self.children.items():
                yield key, trie

    def __setitem__(self, key, subtrie):
        if not isinstance(subtrie, Trie):
            return ValueError("Can only set items of type Trie, got " + str(type(subtrie)))
        if not self.children: self.children = {}
        subtrie.value = key
        subtrie.parent = self
        self.children[key] = subtrie

    def append(self, sequence):
        if not sequence:
            return self
        if not self.children:
            self.children = {}
        if not (sequence[0] in self.children):
            self.children[sequence[0]] = Trie()
            return self.children[sequence[0]].append( sequence[1:] )
        else:
            return self.children[sequence[0]].append( sequence[1:] )

    def find(self, sequence):
        if not sequence:
            return self
        elif self.children and sequence[0] in self.children:
            return self.children[sequence[0]].find(sequence[1:])
        else:
            return False

    def __contains__(self, key):
        return (key in self.children)


    def __getitem__(self, key):
        try:
            return self.children[key]
        except:
            raise


    def size(self):
        """Size is number of nodes under the trie, including the current node"""
        if self.children:
            return sum( ( c.size() for c in self.children.values() ) ) + 1
        else:
            return 1

    def path(self):
        """Returns the path to the current node"""
        if self.parent:
            return (self,) + self.parent.path()
        else:
            return (self,)

    def depth(self):
        """Returns the depth of the current node"""
        if self.parent:
            return 1 + self.parent.depth()
        else:
            return 1

    def sequence(self):
        if self.parent:
            if self.value:
                return (self.value,) + self.parent.sequence()
            else:
                return self.parent.sequence()
        else:
            return (self,)


    def walk(self, leavesonly=True, maxdepth=None, _depth = 0):
        """Depth-first search, walking through trie, returning all encounterd nodes (by default only leaves)"""
        if self.children:
            if not maxdepth or (maxdepth and _depth < maxdepth):
                for key, child in self.children.items():
                    if child.leaf():
                        yield child
                    else:
                        for results in child.walk(leavesonly, maxdepth, _depth + 1):
                            yield results


FIXEDGAP = 128
DYNAMICGAP = 129

if PYTHONVERSION > '3':
    #only available for Python 3

    class Pattern:
        def __init__(self, data, classdecoder=None):
            assert isinstance(data, bytes)
            self.data = data
            self.classdecoder = classdecoder

        @staticmethod
        def fromstring(s, classencoder): #static
            data = b''
            for s in s.split():
                data += classencoder[s]
            return Pattern(data)

        def __str__(self):
            s = ""
            for cls in self:
                s += self.classdecoder[int.from_bytes(cls)]

        def iterbytes(self, begin=0, end=0):
            i = 0
            l = len(self.data)
            n = 0
            if (end != begin):
                slice = True
            else:
                slice = False

            while i < l:
                size = self.data[i]
                if (size < 128): #everything from 128 onward is reserved for markers
                    if not slice:
                        yield self.data[i+1:i+1+size]
                    else:
                        n += 1
                        if n >= begin and n < end:
                            yield self.data[i+1:i+1+size]
                    i += 1 + size
                else:
                    raise ValueError("Size >= 128")


        def __iter__(self):
            for b in self.iterbytes():
                yield Pattern(b, self.classdecoder)

        def __bytes__(self):
            return self.data

        def __len__(self):
            """Return n"""
            i = 0
            l = len(self.data)
            n = 0
            while i < l:
                size = self.data[i]
                if (size < 128):
                    n += 1
                    i += 1 + size
                else:
                    raise ValueError("Size >= 128")

        def __getitem__(self, index):
            assert isinstance(index, int)
            for b in self.iterbytes(index,index+1):
                return Pattern(b, self.classdecoder)

        def __getslice__(self, begin, end):
            slice = b''
            for b in self.iterbytes(begin,end):
                slice += b
            return slice

        def __add__(self, other):
            assert isinstance(other, Pattern)
            return Pattern(self.data + other.data, self.classdecoder)

        def __eq__(self, other):
            return self.data == other.data

    class PatternSet:
        def __init__(self):
            self.data = set()

        def add(self, pattern):
            self.data.add(pattern.data)

        def remove(self, pattern):
            self.data.remove(pattern.data)

        def __len__(self):
            return len(self.data)

        def __bool__(self):
            return len(self.data) > 0

        def __contains__(self, pattern):
            return pattern.data in self.data

        def __iter__(self):
            for patterndata in self.data:
                yield Pattern(patterndata)


    class PatternMap:
        def __init__(self, default=None):
            self.data = {}
            self.default = default

        def __getitem__(self, pattern):
            assert isinstance(pattern, Pattern)
            if not self.default is None:
                try:
                    return self.data[pattern.data]
                except KeyError:
                    return self.default
            else:
                return self.data[pattern.data]

        def __setitem__(self, pattern, value):
            self.data[pattern.data] = value

        def __delitem__(self, pattern):
            del self.data[pattern.data]

        def __len__(self):
            return len(self.data)

        def __bool__(self):
            return len(self.data) > 0

        def __contains__(self, pattern):
            return pattern.data in self.data

        def __iter__(self):
            for patterndata in self.data:
                yield Pattern(patterndata)

        def items(self):
            for patterndata, value in self.data.items():
                yield Pattern(patterndata), value




#class SuffixTree(object):
#   def __init__(self):
#       self.data = {}
#
#
#   def append(self, seq):
#       if len(seq) > 1:
#           for item in seq:
#                self.append(item)
#        else:
#
#
#    def compile(self, s):

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# PyNLPl documentation build configuration file, created by
# sphinx-quickstart on Tue Jul  6 22:07:20 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
from pynlpl import VERSION
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest',] # 'sphinx.ext.todo']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'PyNLPl'
copyright = u'2013, Maarten van Gompel'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = VERSION
# The full version, including alpha/beta/rc tags.
release = VERSION

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'PyNLPldoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
latex_paper_size = 'a4'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'PyNLPl.tex', u'PyNLPl Documentation',
   u'Maarten van Gompel', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = evaluation
###############################################################
#  PyNLPl - Evaluation Library
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#
#       Licensed under GPLv3
#
# This is a Python library with classes and functions for evaluation
# and experiments .
#
###############################################################

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from pynlpl.common import u
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout
import io


from pynlpl.statistics import FrequencyList
from collections import defaultdict
import numpy as np
import subprocess
import itertools
import time
import random
import copy
import datetime
import os.path


def auc(x, y, reorder=False): #from sklearn, http://scikit-learn.org, licensed under BSD License
    """Compute Area Under the Curve (AUC) using the trapezoidal rule

    This is a general fuction, given points on a curve.  For computing the area
    under the ROC-curve, see :func:`auc_score`.

    Parameters
    ----------
    x : array, shape = [n]
        x coordinates.

    y : array, shape = [n]
        y coordinates.

    reorder : boolean, optional (default=False)
        If True, assume that the curve is ascending in the case of ties, as for
        an ROC curve. If the curve is non-ascending, the result will be wrong.

    Returns
    -------
    auc : float

    Examples
    --------
    >>> import numpy as np
    >>> from sklearn import metrics
    >>> y = np.array([1, 1, 2, 2])
    >>> pred = np.array([0.1, 0.4, 0.35, 0.8])
    >>> fpr, tpr, thresholds = metrics.roc_curve(y, pred, pos_label=2)
    >>> metrics.auc(fpr, tpr)
    0.75

    See also
    --------
    auc_score : Computes the area under the ROC curve

    """
    # XXX: Consider using  ``scipy.integrate`` instead, or moving to
    # ``utils.extmath``
    if not isinstance(x, np.ndarray): x = np.array(x)
    if not isinstance(x, np.ndarray): y = np.array(y)
    if x.shape[0] < 2:
        raise ValueError('At least 2 points are needed to compute'
                         ' area under curve, but x.shape = %s' % x.shape)

    if reorder:
        # reorder the data points according to the x axis and using y to
        # break ties
        x, y = np.array(sorted(points for points in zip(x, y))).T
        h = np.diff(x)
    else:
        h = np.diff(x)
        if np.any(h < 0):
            h *= -1
            assert not np.any(h < 0), ("Reordering is not turned on, and "
                                       "The x array is not increasing: %s" % x)

    area = np.sum(h * (y[1:] + y[:-1])) / 2.0
    return area


class ProcessFailed(Exception):
    pass


class ConfusionMatrix(FrequencyList):
    """Confusion Matrix"""

    def __str__(self):
        """Print Confusion Matrix in table form"""
        o = "== Confusion Matrix == (hor: goals, vert: observations)\n\n"

        keys = sorted( set( ( x[1] for x in self._count.keys()) ) )

        linemask = "%20s"
        cells = ['']
        for keyH in keys:
                l = len(keyH)
                if l < 4:
                    l = 4
                elif l > 15:
                    l = 15

                linemask += " %" + str(l) + "s"
                cells.append(keyH)
        linemask += "\n"
        o += linemask % tuple(cells)

        for keyV in keys:
            linemask = "%20s"
            cells = [keyV]
            for keyH in keys:
                l = len(keyH)
                if l < 4:
                    l = 4
                elif l > 15:
                    l = 15
                linemask += " %" + str(l) + "d"
                try:
                    count = self._count[(keyH, keyV)]
                except:
                    count = 0
                cells.append(count)
            linemask += "\n"
            o += linemask % tuple(cells)

        return o




class ClassEvaluation(object):
    def __init__(self,  goals = [], observations = [], missing = {}, encoding ='utf-8'):
        assert len(observations) == len(goals)
        self.observations = copy.copy(observations)
        self.goals = copy.copy(goals)

        self.classes = set(self.observations + self.goals)

        self.tp = defaultdict(int)
        self.fp = defaultdict(int)
        self.tn = defaultdict(int)
        self.fn = defaultdict(int)
        self.missing = missing

        self.encoding = encoding

        self.computed = False

        if self.observations:
            self.compute()

    def append(self, goal, observation):
        self.goals.append(goal)
        self.observations.append(observation)
        self.classes.add(goal)
        self.classes.add(observation)
        self.computed = False

    def precision(self, cls=None, macro=False):
        if not self.computed: self.compute()
        if cls:
            if self.tp[cls] + self.fp[cls] > 0:
                return self.tp[cls] / (self.tp[cls] + self.fp[cls])
            else:
                #return float('nan')
                return 0
        else:
            if len(self.observations) > 0:
                if macro:
                    return sum( ( self.precision(x) for x in set(self.goals) ) ) / len(set(self.classes))
                else:
                    return sum( ( self.precision(x) for x in self.goals ) ) / len(self.goals)
            else:
                #return float('nan')
                return 0

    def recall(self, cls=None, macro=False):
        if not self.computed: self.compute()
        if cls:
            if self.tp[cls] + self.fn[cls] > 0:
                return self.tp[cls] / (self.tp[cls] + self.fn[cls])
            else:
                #return float('nan')
                return 0
        else:
            if len(self.observations) > 0:
                if macro:
                    return sum( ( self.recall(x) for x in set(self.goals) ) ) / len(set(self.classes))
                else:
                    return sum( ( self.recall(x) for x in self.goals ) ) / len(self.goals)
            else:
                #return float('nan')
                return 0

    def specificity(self, cls=None, macro=False):
        if not self.computed: self.compute()
        if cls:
            if self.tn[cls] + self.fp[cls] > 0:
                return self.tn[cls] / (self.tn[cls] + self.fp[cls])
            else:
                #return float('nan')
                return 0
        else:
            if len(self.observations) > 0:
                if macro:
                    return sum( ( self.specificity(x) for x in set(self.goals) ) ) / len(set(self.classes))
                else:
                    return sum( ( self.specificity(x) for x in self.goals ) ) / len(self.goals)
            else:
                #return float('nan')
                return 0

    def accuracy(self, cls=None):
        if not self.computed: self.compute()
        if cls:
            if self.tp[cls] + self.tn[cls] + self.fp[cls] + self.fn[cls] > 0:
                return (self.tp[cls]+self.tn[cls]) / (self.tp[cls] + self.tn[cls] + self.fp[cls] + self.fn[cls])
            else:
                #return float('nan')
                return 0
        else:
            if len(self.observations) > 0:
                return sum( ( self.tp[x] for x in self.tp ) ) / len(self.observations)
            else:
                #return float('nan')
                return 0

    def fscore(self, cls=None, beta=1, macro=False):
        if not self.computed: self.compute()
        if cls:
            prec = self.precision(cls)
            rec =  self.recall(cls)
            if prec * rec > 0:
                return (1 + beta*beta) * ((prec * rec) / (beta*beta * prec + rec))
            else:
                #return float('nan')
                return 0
        else:
            if len(self.observations) > 0:
                if macro:
                    return sum( ( self.fscore(x,beta) for x in set(self.goals) ) ) / len(set(self.classes))
                else:
                    return sum( ( self.fscore(x,beta) for x in self.goals ) ) / len(self.goals)
            else:
                #return float('nan')
                return 0

    def tp_rate(self, cls=None, macro=False):
        if not self.computed: self.compute()
        if cls:
            if self.tp[cls] > 0:
                return self.tp[cls] / (self.tp[cls] + self.fn[cls])
            else:
                return 0
        else:
            if len(self.observations) > 0:
                if macro:
                    return sum( ( self.tp_rate(x) for x in set(self.goals) ) ) / len(set(self.classes))
                else:
                    return sum( ( self.tp_rate(x) for x in self.goals ) ) / len(self.goals)
            else:
                #return float('nan')
                return 0

    def fp_rate(self, cls=None, macro=False):
        if not self.computed: self.compute()
        if cls:
            if self.fp[cls] > 0:
                return self.fp[cls] / (self.tn[cls] + self.fp[cls])
            else:
                return 0
        else:
            if len(self.observations) > 0:
                if macro:
                    return sum( ( self.fp_rate(x) for x in set(self.goals) ) ) / len(set(self.classes))
                else:
                    return sum( ( self.fp_rate(x) for x in self.goals ) ) / len(self.goals)
            else:
                #return float('nan')
                return 0

    def auc(self, cls=None, macro=False):
        if not self.computed: self.compute()
        if cls:
            tpr = self.tp_rate(cls)
            fpr =  self.fp_rate(cls)
            return auc([0,fpr,1], [0,tpr,1])
        else:
            if len(self.observations) > 0:
                if macro:
                    return sum( ( self.auc(x) for x in set(self.goals) ) ) / len(set(self.classes))
                else:
                    return sum( ( self.auc(x) for x in self.goals ) ) / len(self.goals)
            else:
                #return float('nan')
                return 0

    def __iter__(self):
        for g,o in zip(self.goals, self.observations):
             yield g,o

    def compute(self):
        self.tp = defaultdict(int)
        self.fp = defaultdict(int)
        self.tn = defaultdict(int)
        self.fn = defaultdict(int)
        for cls, count in self.missing.items():
            self.fn[cls] = count

        for goal, observation in self:
            if goal == observation:
                self.tp[observation] += 1
            elif goal != observation:
                self.fp[observation] += 1
                self.fn[goal] += 1


        l = len(self.goals) + sum(self.missing.values())
        for o in self.classes:
            self.tn[o] = l - self.tp[o] - self.fp[o] - self.fn[o]

        self.computed = True


    def confusionmatrix(self, casesensitive =True):
        return ConfusionMatrix(zip(self.goals, self.observations), casesensitive)

    def outputmetrics(self):
        o = "Accuracy:              " + str(self.accuracy()) + "\n"
        o += "Samples:               " + str(len(self.goals)) + "\n"
        o += "Correct:               " + str(sum(  ( self.tp[x] for x in set(self.goals)) ) ) + "\n"
        o += "Recall      (microav): "+ str(self.recall()) + "\n"
        o += "Recall      (macroav): "+ str(self.recall(None,True)) + "\n"
        o += "Precision   (microav): " + str(self.precision()) + "\n"
        o += "Precision   (macroav): "+ str(self.precision(None,True)) + "\n"
        o += "Specificity (microav): " + str(self.specificity()) + "\n"
        o += "Specificity (macroav): "+ str(self.specificity(None,True)) + "\n"
        o += "F-score1    (microav): " + str(self.fscore()) + "\n"
        o += "F-score1    (macroav): " + str(self.fscore(None,1,True)) + "\n"
        return o


    def __str__(self):
        if not self.computed: self.compute()
        o =  "%-15s TP\tFP\tTN\tFN\tAccuracy\tPrecision\tRecall(TPR)\tSpecificity(TNR)\tF-score\n" % ("")
        for cls in sorted(set(self.classes)):
            cls = u(cls)
            o += "%-15s %d\t%d\t%d\t%d\t%4f\t%4f\t%4f\t%4f\t%4f\n" % (cls, self.tp[cls], self.fp[cls], self.tn[cls], self.fn[cls], self.accuracy(cls), self.precision(cls), self.recall(cls),self.specificity(cls),  self.fscore(cls) )
        return o + "\n" + self.outputmetrics()

    def __unicode__(self): #Python 2.x
        return str(self)


class AbstractExperiment(object):

    def __init__(self, inputdata = None, **parameters):
        self.inputdata = inputdata
        self.parameters = self.defaultparameters()
        for parameter, value in parameters.items():
            self.parameters[parameter] = value
        self.process = None
        self.creationtime = datetime.datetime.now()
        self.begintime = self.endtime = 0

    def defaultparameters(self):
        return {}

    def duration(self):
        if self.endtime and self.begintime:
            return self.endtime - self.begintime
        else:
            return 0

    def start(self):
        """Start as a detached subprocess, immediately returning execution to caller."""
        raise Exception("Not implemented yet, make sure to overload the start() method in your Experiment class")

    def done(self, warn=True):
        """Is the subprocess done?"""
        if not self.process:
            raise Exception("Not implemented yet or process not started yet, make sure to overload the done() method in your Experiment class")
        self.process.poll()
        if self.process.returncode == None:
            return False
        elif self.process.returncode > 0:
            raise ProcessFailed()
        else:
            self.endtime = datetime.datetime.now()
            return True

    def run(self):
        if hasattr(self,'start'):
            self.start()
            self.wait()
        else:
            raise Exception("Not implemented yet, make sure to overload the run() method!")

    def startcommand(self, command, cwd, stdout, stderr, *arguments, **parameters):
        argdelimiter=' '
        printcommand = True

        cmd = command
        if arguments:
            cmd += ' ' + " ".join([ u(x) for x in arguments])
        if parameters:
            for key, value in parameters.items():
                if key == 'argdelimiter':
                    argdelimiter = value
                elif key == 'printcommand':
                    printcommand = value
                elif isinstance(value, bool) and value == True:
                    cmd += ' ' + key
                elif key[-1] != '=':
                    cmd += ' ' + key + argdelimiter + str(value)
                else:
                    cmd += ' ' + key + str(value)
        if printcommand:
            print("STARTING COMMAND: " + cmd, file=stderr)

        self.begintime = datetime.datetime.now()
        if not cwd:
            self.process = subprocess.Popen(cmd, shell=True,stdout=stdout,stderr=stderr)
        else:
            self.process = subprocess.Popen(cmd, shell=True,cwd=cwd,stdout=stdout,stderr=stderr)
        #pid = process.pid
        #os.waitpid(pid, 0) #wait for process to finish
        return self.process

    def wait(self):
        while not self.done():
           time.sleep(1)
           pass

    def score(self):
        raise Exception("Not implemented yet, make sure to overload the score() method")


    def delete(self):
        pass

    def sample(self, size):
        """Return a sample of the input data"""
        raise Exception("Not implemented yet, make sure to overload the sample() method")

class ExperimentPool(object):
    def __init__(self, size):
        self.size = size
        self.queue = []
        self.running = []

    def append(self, experiment):
        assert isinstance(experiment, AbstractExperiment)
        self.queue.append( experiment )

    def __len__(self):
        return len(self.queue)

    def __iter__(self):
        return iter(self.queue)

    def start(self, experiment):
        experiment.start()
        self.running.append( experiment )

    def poll(self, haltonerror=True):
        done = []
        for experiment in self.running:
            try:
                if experiment.done():
                    done.append( experiment )
            except ProcessFailed:
                print("ERROR: One experiment in the pool failed: " + repr(experiment.inputdata) + repr(experiment.parameters), file=stderr)
                if haltonerror:
                    raise
                else:
                    done.append( experiment )
        for experiment in done:
                self.running.remove( experiment )
        return done

    def run(self, haltonerror=True):
        while True:
            #check how many processes are done
            done = self.poll(haltonerror)

            for experiment in done:
                yield experiment
            #start new processes
            while self.queue and len(self.running) < self.size:
                self.start( self.queue.pop(0) )
            if not self.queue and not self.running:
                break



class WPSParamSearch(object):
    """ParamSearch with support for Wrapped Progressive Sampling"""

    def __init__(self, experimentclass, inputdata, size, parameterscope, poolsize=1, sizefunc=None, prunefunc=None, constraintfunc = None, delete=True): #parameterscope: {'parameter':[values]}
        self.ExperimentClass = experimentclass
        self.inputdata = inputdata
        self.poolsize = poolsize #0 or 1: sequential execution (uses experiment.run() ), >1: parallel execution using ExperimentPool (uses experiment.start() )
        self.maxsize = size
        self.delete = delete #delete intermediate experiments

        if self.maxsize == -1:
            self.sizefunc = lambda x,y: self.maxsize
        else:
            if sizefunc != None:
                self.sizefunc = sizefunc
            else:
                self.sizefunc = lambda i, maxsize: round((maxsize/100.0)*i*i)

        #prunefunc should return a number between 0 and 1, indicating how much is pruned. (for example: 0.75 prunes three/fourth of all combinations, retaining only 25%)
        if prunefunc != None:
            self.prunefunc = prunefunc
        else:
            self.prunefunc = lambda i: 0.5

        if constraintfunc != None:
            self.constraintfunc = constraintfunc
        else:
            self.constraintfunc = lambda x: True

        #compute all parameter combinations:
        if isinstance(parameterscope, dict):
            verboseparameterscope = [ self._combine(x,y) for x,y in parameterscope.items() ]
        else:
            verboseparameterscope = [ self._combine(x,y) for x,y in parameterscope ]
        self.parametercombinations = [ (x,0) for x in itertools.product(*verboseparameterscope) if self.constraintfunc(dict(x)) ] #generator

    def _combine(self,name, values): #TODO: can't we do this inline in a list comprehension?
        l = []
        for value in values:
            l.append( (name, value) )
        return l

    def searchbest(self):
        solution = None
        for s in iter(self):
            solution = s
        return solution[0]


    def test(self,i=None):
        #sample size elements from inputdata
        if i is None or self.maxsize == -1:
            data = self.inputdata
        else:
            size = int(self.sizefunc(i, self.maxsize))
            if size > self.maxsize:
                return []

            data = self.ExperimentClass.sample(self.inputdata, size)


        #run on ALL available parameter combinations and retrieve score
        newparametercombinations = []
        if self.poolsize <= 1:
            #Don't use experiment pool, sequential execution
            for parameters,score in self.parametercombinations:
                experiment = self.ExperimentClass(data, **dict(parameters))
                experiment.run()
                newparametercombinations.append( (parameters, experiment.score()) )
                if self.delete:
                    experiment.delete()
        else:
            #Use experiment pool, parallel execution
            pool = ExperimentPool(self.poolsize)
            for parameters,score in self.parametercombinations:
                pool.append( self.ExperimentClass(data, **dict(parameters)) )
            for experiment in pool.run(False):
                newparametercombinations.append( (experiment.parameters, experiment.score()) )
                if self.delete:
                    experiment.delete()

        return newparametercombinations


    def __iter__(self):
        i = 0
        while True:
            i += 1

            newparametercombinations = self.test(i)

            #prune the combinations, keeping only the best
            prune = int(round(self.prunefunc(i) * len(newparametercombinations)))
            self.parametercombinations = sorted(newparametercombinations, key=lambda v: v[1])[prune:]

            yield [ x[0] for x in self.parametercombinations ]
            if len(self.parametercombinations) <= 1:
                break

class ParamSearch(WPSParamSearch):
    """A simpler version of ParamSearch without Wrapped Progressive Sampling"""
    def __init__(self, experimentclass, inputdata, parameterscope, poolsize=1, constraintfunc = None, delete=True): #parameterscope: {'parameter':[values]}
        prunefunc = lambda x: 0
        super(ParamSearch, self).__init__(experimentclass, inputdata, -1, parameterscope, poolsize, None,prunefunc, constraintfunc, delete)

    def __iter__(self):
         for parametercombination, score in sorted(self.test(), key=lambda v: v[1]):
             yield parametercombination, score


def filesampler(files, testsetsize = 0.1, devsetsize = 0, trainsetsize = 0, outputdir = '', encoding='utf-8'):
        """Extract a training set, test set and optimally a development set from one file, or multiple *interdependent* files (such as a parallel corpus). It is assumed each line contains one instance (such as a word or sentence for example)."""

        if not isinstance(files, list):
            files = list(files)

        total = 0
        for filename in files:
            f = io.open(filename,'r', encoding=encoding)
            count = 0
            for line in f:
                count += 1
            f.close()
            if total == 0:
                total = count
            elif total != count:
                raise Exception("Size mismatch, when multiple files are specified they must contain the exact same amount of lines!")

        #support for relative values:
        if testsetsize < 1:
            testsetsize = int(total * testsetsize)
        if devsetsize < 1 and devsetsize > 0:
            devsetsize = int(total * devsetsize)


        if testsetsize >= total or devsetsize >= total or testsetsize + devsetsize >= total:
            raise Exception("Test set and/or development set too large! No samples left for training set!")


        trainset = {}
        testset = {}
        devset = {}
        for i in range(1,total+1):
            trainset[i] = True
        for i in random.sample(trainset.keys(), testsetsize):
            testset[i] = True
            del trainset[i]

        if devsetsize > 0:
            for i in random.sample(trainset.keys(), devsetsize):
                devset[i] = True
                del trainset[i]

        if trainsetsize > 0:
            newtrainset = {}
            for i in random.sample(trainset.keys(), trainsetsize):
                newtrainset[i] = True
            trainset = newtrainset

        for filename in files:
            if not outputdir:
                ftrain = io.open(filename + '.train','w',encoding=encoding)
            else:
                ftrain = io.open(outputdir + '/' +  os.path.basename(filename) + '.train','w',encoding=encoding)
            if not outputdir:
                ftest = io.open(filename + '.test','w',encoding=encoding)
            else:
                ftest = io.open(outputdir + '/' + os.path.basename(filename) + '.test','w',encoding=encoding)
            if devsetsize > 0:
                if not outputdir:
                    fdev = io.open(filename + '.dev','w',encoding=encoding)
                else:
                    fdev = io.open(outputdir + '/' +  os.path.basename(filename) + '.dev','w',encoding=encoding)

            f = io.open(filename,'r',encoding=encoding)
            for linenum, line in enumerate(f):
                if linenum+1 in trainset:
                    ftrain.write(line)
                elif linenum+1 in testset:
                    ftest.write(line)
                elif devsetsize > 0 and linenum+1 in devset:
                    fdev.write(line)
            f.close()

            ftrain.close()
            ftest.close()
            if devsetsize > 0: fdev.close()





########NEW FILE########
__FILENAME__ = freqlist
#!/usr/bin/env python
#-*- coding:utf-8 -*-

from pynlpl.textprocessors import Windower, crude_tokenizer
from pynlpl.statistics import FrequencyList, Distribution

import sys
import codecs

with codecs.open(sys.argv[1],'r','utf-8') as file:
    freqlist = FrequencyList()
    for line in file:
        freqlist.append(Windower(crude_tokenizer(line),2))


print "Type/Token Ratio: ", freqlist.typetokenratio()

### uncomment if you want to output the full frequency list:
#for line in freqlist.output():
#    print line.encode('utf-8')

dist = Distribution(freqlist)
for line in dist.output():
    print line.encode('utf-8')


########NEW FILE########
__FILENAME__ = make_sonar_lm
#!/usr/bin/env python
#-*- coding:utf-8 -*-

#Create a language model based on SoNaR

import sys
import os
sys.path.append(sys.path[0] + '/../..')
os.environ['PYTHONPATH'] = sys.path[0] + '/../..'


from pynlpl.formats.sonar import Corpus
from pynlpl.lm.lm import SimpleLanguageModel

#syntax: ./make_sonar_lm.py sonar_dir output_file n [category]

outputfile = sys.argv[2]


n=3
restrictcollection=""
try:
    n = int(sys.argv[3])
    restrictcollection = sys.argv[4]
except:
    pass

lm = SimpleLanguageModel(n)

for doc in Corpus(sys.argv[1],'tok',restrictcollection):
    for sentence_id, sentence in doc.sentences():
	print sentence_id
        words = [ word for word, id, pos, lemma in sentence ]
        lm.append(words)
lm.save(outputfile)





########NEW FILE########
__FILENAME__ = query_lm
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import os
sys.path.append(sys.path[0] + '/../..')
os.environ['PYTHONPATH'] = sys.path[0] + '/../..'

from pynlpl.lm.lm import SimpleLanguageModel

#syntax: ./query_lm.py lm_file sentence

lmfile = sys.argv[1]

lm = SimpleLanguageModel()
lm.load(lmfile)
print lm.scoresentence(sys.argv[2:])

########NEW FILE########
__FILENAME__ = cgn
#-*- coding:utf-8 -*-

###############################################################
#  PyNLPl - Corpus Gesproken Nederlands
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#       
#       Licensed under GPLv3
# 
# Classes for reading CGN (still to be added). Most notably, contains a function for decoding
# PoS features like "N(soort,ev,basis,onz,stan)" into a data structure.
#
###############################################################

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import  
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout
    
from pynlpl.formats import folia
from pynlpl.common import Enum


class InvalidTagException(Exception):
    pass
    
class InvalidFeatureException(Exception):
    pass

subsets = {
    'ntype': ['soort','eigen'],
    'getal': ['ev','mv','getal',],
    'genus': ['zijd','onz','masc','fem','genus'],
    'naamval': ['stan','gen','dat','nomin','obl','bijz'],
    'spectype': ['afgebr','afk','deeleigen','symb','vreemd','enof','meta','achter','comment','onverst'],
    'conjtype': ['neven','onder'],
    'vztype': ['init','versm','fin'],
    'npagr': ['agr','evon','rest','evz','mv','agr3','evmo','rest3','evf'],
    'lwtype': ['bep','onbep'],
    'vwtype': ['pers','pr','refl','recip','bez','vb','vrag','betr','excl','aanw','onbep'], 
    'pdtype':  ['adv-pron','pron','det','grad'],
    'status': ['vol','red','nadr'],
    'persoon': ['1','2','2v','2b','3','3p','3m','3v','3o','persoon'],
    'positie': ['prenom','postnom', 'nom','vrij'],
    'buiging': ['zonder','met-e','met-s'],
    'getal-n' : ['zonder-v','mv-n','zonder-n'],
    'graad' : ['basis','comp','sup','dim'],
    'wvorm': ['pv','inf','vd','od'],
    'pvtijd': ['tgw','verl','conj'],
    'pvagr':  ['ev','mv','met-t'],
    'numtype': ['hoofd','rang'],
    'dial': ['dial'],
}
constraints = {
    'getal':['N','VNW'],
    'npagr':['VNW','LID'],
    'pvagr':['WW'],    
}

def parse_cgn_postag(rawtag, raisefeatureexceptions = False):
    global subsets, constraints
    """decodes PoS features like "N(soort,ev,basis,onz,stan)" into a PosAnnotation data structure 
    based on CGN tag overview compiled by Matje van de Camp"""
    
    
    begin = rawtag.find('(')
    if rawtag[-1] == ')' and begin > 0:
        tag = folia.PosAnnotation(None, cls=rawtag,set='http://ilk.uvt.nl/folia/sets/cgn')

        
        head = rawtag[0:begin]
        tag.append( folia.Feature, subset='head',cls=head)

        rawfeatures = rawtag[begin+1:-1].split(',')
        for rawfeature in rawfeatures:            
            if rawfeature:
                found = False
                for subset, classes in subsets.items():
                    if rawfeature in classes:
                        if subset in constraints:
                            if not head in constraints[subset]:
                                continue #constraint not met!
                        found = True
                        tag.append( folia.Feature, subset=subset,cls=rawfeature)
                        break
                if not found:
                    print("\t\tUnknown feature value: " + rawfeature + " in " + rawtag, file=stderr)
                    if raisefeatureexceptions:
                        raise InvalidFeatureException("Unknown feature value: " + rawfeature + " in " + rawtag)
                    else:    
                        continue
        return tag
    else:
        raise InvalidTagException("Not a valid CGN tag")






########NEW FILE########
__FILENAME__ = dutchsemcor
#-*- coding:utf-8 -*-

###############################################################
# PyNLPl - DutchSemCor
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#       
#       Licensed under GPLv3
#
#  Modified by Ruben Izquierdo
#  We need also to store the TIMBL distance to the nearest neighboor  
# 
# Collection of formats for the DutchSemCor project
#
###############################################################

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import  
from pynlpl.common import u
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout

from pynlpl.formats.timbl import TimblOutput
from pynlpl.statistics import Distribution
import io


class WSDSystemOutput(object):
    def __init__(self, filename = None):
        self.data = {}
        self.distances={}
        self.maxDistance=1
        if filename:
            self.load(filename)

    def append(self, word_id, senses,distance=0):
       # Commented by Ruben, there are some ID's that are repeated in all sonar test files...            
       #assert (not word_id in self.data)
       if isinstance(senses, Distribution):
            self.data[word_id] = ( (x,y) for x,y in senses ) #PATCH UNDONE (#TODO: this is a patch, something's not right in Distribution?)
            self.distances[word_id]=distance
            if distance > self.maxDistance:
              self.maxDistance=distance
            return
       else:
           assert isinstance(senses, list) and len(senses) >= 1

       self.distances[word_id]=distance
       if distance > self.maxDistance:
        self.maxDistance=distance
                             
       
       if len(senses[0]) == 1:
            #not a (sense_id, confidence) tuple! compute equal confidence for all elements automatically:
            confidence = 1 / float(len(senses))
            self.data[word_id]  = [ (x,confidence) for x in senses ]
       else: 
          fulldistr = True
          for sense, confidence in senses:
            if confidence == None:
                fulldistr = False
                break

          if fulldistr:
               self.data[word_id] = Distribution(senses)
          else:
               self.data[word_id] = senses
        

    def getMaxDistance(self):
        return self.maxDistance
    
    def __iter__(self):
        for word_id, senses in  self.data.items():
            yield word_id, senses,self.distances[word_id]

    def __len__(self):
        return len(self.data)

    def __getitem__(self, word_id):
        """Returns the sense distribution for the given word_id"""
        return self.data[word_id]

    def load(self, filename):
        f = io.open(filename,'r',encoding='utf-8')
        for line in f:
            fields = line.strip().split(" ")
            word_id = fields[0]
            if len(fields[1:]) == 1:
                #only one sense, no confidence expressed:
                self.append(word_id, [(fields[1],None)])
            else:
                senses = []
                distance=-1
                for i in range(1,len(fields),2):
                    if i+1==len(fields):
                        #The last field is the distance
                        if fields[i][:4]=='+vdi': #Support for previous format of wsdout
                            distance=float(fields[i][4:])
                        else:
                            distance=float(fields[i])
                    else:
                        if fields[i+1] == '?': fields[i+1] = None
                        senses.append( (fields[i], fields[i+1]) )
                self.append(word_id, senses,distance)
                
        f.close()

    def save(self, filename):
        f = io.open(filename,'w',encoding='utf-8')
        for word_id, senses,distance in self:
            f.write(word_id)
            for sense, confidence in senses:
                if confidence == None: confidence = "?"
                f.write(" " + str(sense) + " " + str(confidence))
            if word_id in self.distances.keys():
                f.write(' '+str(self.distances[word_id]))
            f.write("\n")
        f.close()

    def out(self, filename):
        for word_id, senses,distance in self:
            print(word_id,distance,end="")
            for sense, confidence in senses:
                if confidence == None: confidence = "?"
                print(" " + sense + " " + str(confidence),end="")
            print()

    def senses(self, bestonly=False):
        """Returns a list of all predicted senses"""
        l = []
        for word_id, senses,distance in self:
            for sense, confidence in senses:
                if not sense in l: l.append(sense)
                if bestonly:
                    break
        return l


    def loadfromtimbl(self, filename):
        timbloutput = TimblOutput(io.open(filename,'r',encoding='utf-8'))
        for i, (features, referenceclass, predictedclass, distribution, distance) in enumerate(timbloutput):
            if distance != None:
                #distance='+vdi'+str(distance)
                distance=float(distance)
            if len(features) == 0:
                print("WARNING: Empty feature vector in " + filename + " (line " + str(i+1) + ") skipping!!",file=stderr)
                continue
            word_id = features[0] #note: this is an assumption that must be adhered to!
            if distribution:
                self.append(word_id, distribution,distance)

    def fromTimblToWsdout(self,fileTimbl,fileWsdout):
        timbloutput = TimblOutput(io.open(fileTimbl,'r',encoding='utf-8'))
        wsdoutfile = io.open(fileWsdout,'w',encoding='utf-8')
        for i, (features, referenceclass, predictedclass, distribution, distance) in enumerate(timbloutput):
            if len(features) == 0:
                print("WARNING: Empty feature vector in " + fileTimbl + " (line " + str(i+1) + ") skipping!!",file=stderr)
                continue
            word_id = features[0] #note: this is an assumption that must be adhered to!
            if distribution:
                wsdoutfile.write(word_id+' ')
                for sense, confidence in distribution:
                    if confidence== None: confidence='?'
                    wsdoutfile.write(sense+' '+str(confidence)+' ')
                wsdoutfile.write(str(distance)+'\n')
        wsdoutfile.close()
                                                    


class DataSet(object): #for testsets/trainingsets
    def __init__(self, filename):
        self.sense = {} #word_id => (sense_id, lemma,pos)
        self.targetwords = {} #(lemma,pos) => [sense_id]
        f = io.open(filename,'r',encoding='utf-8')
        for line in f:
            if len(line) > 0 and line[0] != '#':
                fields = line.strip('\n').split('\t')
                word_id = fields[0]
                sense_id = fields[1]
                lemma = fields[2]
                pos = fields[3]
                self.sense[word_id] = (sense_id, lemma, pos)
                if not (lemma,pos) in self.targetwords:
                    self.targetwords[(lemma,pos)] = []
                if not sense_id in self.targetwords[(lemma,pos)]:
                    self.targetwords[(lemma,pos)].append(sense_id)
        f.close()

    def __getitem__(self, word_id):
        return self.sense[self._sanitize(word_id)]

    def getsense(self, word_id):
        return self.sense[self._sanitize(word_id)][0]

    def getlemma(self, word_id):
        return self.sense[self._sanitize(word_id)][1]

    def getpos(self, word_id):
        return self.sense[self._sanitize(word_id)][2]

    def _sanitize(self, word_id):
        return u(word_id)

    def __contains__(self, word_id):
        return (self._sanitize(word_id) in self.sense)


    def __iter__(self):
        for word_id, (sense, lemma, pos) in self.sense.items():
            yield (word_id, sense, lemma, pos)

    def senses(self, lemma, pos):
        return self.targetwords[(lemma,pos)]

########NEW FILE########
__FILENAME__ = folia
#---------------------------------------------------------------
# PyNLPl - FoLiA Format Module
#   by Maarten van Gompel
#   Centre for Language Studies
#   Radboud University Nijmegen
#   http://proycon.github.com/folia
#   http://www.github.com/proycon/pynlpl
#   proycon AT anaproy DOT nl
#
#   Module for reading, editing and writing FoLiA XML
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from pynlpl.common import u, isstring
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout

from lxml import etree as ElementTree
LXE=True
#import xml.etree.cElementTree as ElementTree
#LXE = False

from lxml.builder import ElementMaker
if sys.version < '3':
    from StringIO import StringIO
    from urllib import urlopen
else:
    from io import StringIO,  BytesIO
    from urllib.request import urlopen #pylint: disable=E0611


from copy import copy, deepcopy
from pynlpl.formats.imdi import RELAXNG_IMDI
from datetime import datetime
#from dateutil.parser import parse as parse_datetime
import pynlpl.algorithms
import inspect
import glob
import os
import re
try:
    import io
except ImportError:
    #old-Python 2.6 fallback
    import codecs as io
import multiprocessing
import threading
import bz2
import gzip


FOLIAVERSION = '0.11.0'
LIBVERSION = '0.11.0.46' #== FoLiA version + library revision


#0.9.1.31 is the first version with Python 3 support

NSFOLIA = "http://ilk.uvt.nl/folia"
NSDCOI = "http://lands.let.ru.nl/projects/d-coi/ns/1.0"
nslen = len(NSFOLIA) + 2
nslendcoi = len(NSDCOI) + 2

TMPDIR = "/tmp/" #will be used for downloading temporary data (external subdocuments)

defaultignorelist = [] #Will be set at end of file! Only here so pylint won't complain
#default ignore list for token annotation
defaultignorelist_annotations = [] #Will be set at end of file! Only here so pylint won't complain
defaultignorelist_structure = [] #Will be set at end of file! Only here so pylint won't complain

ILLEGAL_UNICODE_CONTROL_CHARACTERS = {} #XML does not like unicode control characters
for ordinal in range(0x20):
    if chr(ordinal) not in '\t\r\n':
        ILLEGAL_UNICODE_CONTROL_CHARACTERS[ordinal] = None

class Mode:
    MEMORY = 0 #The entire FoLiA structure will be loaded into memory. This is the default and is required for any kind of document manipulation.
    XPATH = 1 #The full XML structure will be loaded into memory, but conversion to FoLiA objects occurs only upon querying. The full power of XPath is available.
    ITERATIVE = 2 #XML element are loaded and conveted to FoLiA objects iteratively on a need-to basis. A subset of XPath is supported. (not implemented, obsolete)

class AnnotatorType:
    UNSET = 0
    AUTO = 1
    MANUAL = 2


class Attrib:
    ID, CLASS, ANNOTATOR, CONFIDENCE, N, DATETIME, SETONLY = range(7) #BEGINTIME, ENDTIME, SRC, SRCOFFSET, SPEAKER = range(12) #for later

Attrib.ALL = (Attrib.ID,Attrib.CLASS,Attrib.ANNOTATOR, Attrib.N, Attrib.CONFIDENCE, Attrib.DATETIME)

class AnnotationType:
    TEXT, TOKEN, DIVISION, PARAGRAPH, LIST, FIGURE, WHITESPACE, LINEBREAK, SENTENCE, POS, LEMMA, DOMAIN, SENSE, SYNTAX, CHUNKING, ENTITY, CORRECTION, SUGGESTION, ERRORDETECTION, ALTERNATIVE, PHON, SUBJECTIVITY, MORPHOLOGICAL, EVENT, DEPENDENCY, TIMESEGMENT, GAP, NOTE, ALIGNMENT, COMPLEXALIGNMENT, COREFERENCE, SEMROLE, METRIC, LANG, STRING, TABLE, STYLE = range(37)


    #Alternative is a special one, not declared and not used except for ID generation

class TextCorrectionLevel: #THIS IS NOW COMPLETELY OBSOLETE AND ONLY HERE FOR BACKWARD COMPATIBILITY!
    CORRECTED, UNCORRECTED, ORIGINAL, INLINE = range(4)

class MetaDataType:
    NATIVE, CMDI, IMDI = range(3)

class NoSuchAnnotation(Exception):
    """Exception raised when the requested type of annotation does not exist for the selected element"""
    pass

class NoSuchText(Exception):
    """Exception raised when the requestion type of text content does not exist for the selected element"""
    pass

class DuplicateAnnotationError(Exception):
    pass

class DuplicateIDError(Exception):
    """Exception raised when an identifier that is already in use is assigned again to another element"""
    pass

class NoDefaultError(Exception):
    pass

class NoDescription(Exception):
    pass

class UnresolvableTextContent(Exception):
    pass

class MalformedXMLError(Exception):
    pass

class DeepValidationError(Exception):
    pass

class SetDefinitionError(DeepValidationError):
    pass

class ModeError(Exception):
    pass


#There is a leak in lxml :( , specialise file handler to replace xml:id to id, ugly hack (especially for Python2)
if sys.version < '3':
    if 1 == 2 and hasattr(io,'FileIO'): #DISABLED
        #Python 2.6 with io, 2.7
        class BypassLeakFile(io.FileIO):
            def read(self,n=0):
                try:
                    s = unicode(super(BypassLeakFile,self).read(n),'utf-8')
                except UnicodeDecodeError as e:
                    byte = str(e).split()[5]
                    position = int(str(e).split()[8].strip(':'))
                    self.seek(0)
                    s = super(BypassLeakFile,self).read(position)
                    linenum = s.count("\n") + 1
                    print("In line " + str(linenum) +" : ... ", repr(s[-25:]),file=stderr)
                    raise e
                return s.replace('xml:id','id').encode('utf-8')

            def readline(self):
                s = unicode(super(BypassLeakFile,self).readline(),'utf-8')
                return s.replace('xml:id','id').encode('utf-8')
    else:
        #Python 2.6 without io
        class BypassLeakFile(file):
            def read(self,n=0): #pylint: disable=E1003
                s = unicode(super(BypassLeakFile,self).read(n),'utf-8')
                return s.replace('xml:id','id').encode('utf-8')

            def readline(self): #pylint: disable=E1003
                s = unicode(super(BypassLeakFile,self).readline(),'utf-8')
                return s.replace('xml:id','id').encode('utf-8')
else:
    #Python 3
    class BypassLeakFile(io.FileIO):
        def read(self,n=0): #pylint: disable=E1003
            s = super(BypassLeakFile,self).read(n)
            return s.replace(b'xml:id',b'id')

        def readline(self):  #pylint: disable=E1003
            s = super(BypassLeakFile,self).readline()
            return s.replace(b'xml:id',b'id')

def parsecommonarguments(object, doc, annotationtype, required, allowed, **kwargs):
    """Internal function, parses common FoLiA attributes and sets up the instance accordingly"""

    object.doc = doc #The FoLiA root document
    supported = required + allowed


    if 'generate_id_in' in kwargs:
        kwargs['id'] = kwargs['generate_id_in'].generate_id(object.__class__)
        del kwargs['generate_id_in']



    if 'id' in kwargs:
        if not Attrib.ID in supported:
            raise ValueError("ID is not supported on " + object.__class__.__name__)
        isncname(kwargs['id'])
        object.id = kwargs['id']
        del kwargs['id']
    elif Attrib.ID in required:
        raise ValueError("ID is required for " + object.__class__.__name__)
    else:
        object.id = None

    if 'set' in kwargs:
        if not Attrib.CLASS in supported and not Attrib.SETONLY in supported:
            raise ValueError("Set is not supported on " + object.__class__.__name__)
        if not kwargs['set']:
            object.set ="undefined";
        else:
            object.set = kwargs['set']
        del kwargs['set']

        if object.set:
            if doc and (not (annotationtype in doc.annotationdefaults) or not (object.set in doc.annotationdefaults[annotationtype])):
                if doc.autodeclare:
                    doc.annotations.append( (annotationtype, object.set ) )
                    doc.annotationdefaults[annotationtype] = {object.set: {} }
                else:
                    raise ValueError("Set '" + object.set + "' is used for " + object.__class__.__name__ + ", but has no declaration!")
    elif annotationtype in doc.annotationdefaults and len(doc.annotationdefaults[annotationtype]) == 1:
        object.set = list(doc.annotationdefaults[annotationtype].keys())[0]
    elif object.ANNOTATIONTYPE == AnnotationType.TEXT:
        object.set = "undefined"; #text content needs never be declared (for backward compatibility) and is in set 'undefined'
    elif Attrib.CLASS in required or Attrib.SETONLY in required:
        raise ValueError("Set is required for " + object.__class__.__name__)
    else:
        object.set = None


    if 'class' in kwargs:
        if not Attrib.CLASS in supported:
            raise ValueError("Class is not supported for " + object.__class__.__name__)
        object.cls = kwargs['class']
        del kwargs['class']
    elif 'cls' in kwargs:
        if not Attrib.CLASS in supported:
            raise ValueError("Class is not supported on " + object.__class__.__name__)
        object.cls = kwargs['cls']
        del kwargs['cls']
    elif Attrib.CLASS in required:
        raise ValueError("Class is required for " + object.__class__.__name__)
    else:
        object.cls = None

    if object.cls and not object.set:
        if doc and doc.autodeclare:
            if not (annotationtype, 'undefined') in doc.annotations:
                doc.annotations.append( (annotationtype, 'undefined') )
                doc.annotationdefaults[annotationtype] = {'undefined': {} }
            object.set = 'undefined'
        else:
            raise ValueError("Set is required for " + object.__class__.__name__ +  ". Class '" + object.cls + "' assigned without set.")





    if 'annotator' in kwargs:
        if not Attrib.ANNOTATOR in supported:
            raise ValueError("Annotator is not supported for " + object.__class__.__name__)
        object.annotator = kwargs['annotator']
        del kwargs['annotator']
    elif doc and annotationtype in doc.annotationdefaults and object.set in doc.annotationdefaults[annotationtype] and 'annotator' in doc.annotationdefaults[annotationtype][object.set]:
        object.annotator = doc.annotationdefaults[annotationtype][object.set]['annotator']
    elif Attrib.ANNOTATOR in required:
        raise ValueError("Annotator is required for " + object.__class__.__name__)
    else:
        object.annotator = None


    if 'annotatortype' in kwargs:
        if not Attrib.ANNOTATOR in supported:
            raise ValueError("Annotatortype is not supported for " + object.__class__.__name__)
        if kwargs['annotatortype'] == 'auto' or kwargs['annotatortype'] == AnnotatorType.AUTO:
            object.annotatortype = AnnotatorType.AUTO
        elif kwargs['annotatortype'] == 'manual' or kwargs['annotatortype']  == AnnotatorType.MANUAL:
            object.annotatortype = AnnotatorType.MANUAL
        else:
            raise ValueError("annotatortype must be 'auto' or 'manual', got "  + repr(kwargs['annotatortype']))
        del kwargs['annotatortype']
    elif doc and annotationtype in doc.annotationdefaults and object.set in doc.annotationdefaults[annotationtype] and 'annotatortype' in doc.annotationdefaults[annotationtype][object.set]:
        object.annotatortype = doc.annotationdefaults[annotationtype][object.set]['annotatortype']
    elif Attrib.ANNOTATOR in required:
        raise ValueError("Annotatortype is required for " + object.__class__.__name__)
    else:
        object.annotatortype = None


    if 'confidence' in kwargs:
        if not Attrib.CONFIDENCE in supported:
            raise ValueError("Confidence is not supported")
        try:
            object.confidence = float(kwargs['confidence'])
            assert (object.confidence >= 0.0 and object.confidence <= 1.0)
        except:
            raise ValueError("Confidence must be a floating point number between 0 and 1, got " + repr(kwargs['confidence']) )
        del kwargs['confidence']
    elif Attrib.CONFIDENCE in required:
        raise ValueError("Confidence is required for " + object.__class__.__name__)
    else:
        object.confidence = None



    if 'n' in kwargs:
        if not Attrib.N in supported:
            raise ValueError("N is not supported")
        object.n = kwargs['n']
        del kwargs['n']
    elif Attrib.N in required:
        raise ValueError("N is required")
    else:
        object.n = None

    if 'datetime' in kwargs:
        if not Attrib.DATETIME in supported:
            raise ValueError("Datetime is not supported")
        if isinstance(kwargs['datetime'], datetime):
            object.datetime = kwargs['datetime']
        else:

            #try:
            object.datetime = parse_datetime(kwargs['datetime'])
            #except:
            #    raise ValueError("Unable to parse datetime: " + str(repr(kwargs['datetime'])))
        del kwargs['datetime']
    elif doc and annotationtype in doc.annotationdefaults and object.set in doc.annotationdefaults[annotationtype] and 'datetime' in doc.annotationdefaults[annotationtype][object.set]:
        object.datetime = doc.annotationdefaults[annotationtype][object.set]['datetime']
    elif Attrib.DATETIME in required:
        raise ValueError("Datetime is required")
    else:
        object.datetime = None

    if 'auth' in kwargs:
        object.auth = bool(kwargs['auth'])
        del kwargs['auth']
    else:
        object.auth = True



    if 'text' in kwargs:
        if kwargs['text']:
            object.settext(kwargs['text'])
        del kwargs['text']

    if doc and doc.debug >= 2:
        print("   @id           = ", repr(object.id),file=stderr)
        print("   @set          = ", repr(object.set),file=stderr)
        print("   @class        = ", repr(object.cls),file=stderr)
        print("   @annotator    = ", repr(object.annotator),file=stderr)
        print("   @annotatortype= ", repr(object.annotatortype),file=stderr)
        print("   @confidence   = ", repr(object.confidence),file=stderr)
        print("   @n            = ", repr(object.n),file=stderr)
        print("   @datetime     = ", repr(object.datetime),file=stderr)



    #set index
    if object.id and doc:
        if object.id in doc.index:
            if doc.debug >= 1: print("[PyNLPl FoLiA DEBUG] Duplicate ID not permitted:" + object.id,file=stderr)
            raise DuplicateIDError("Duplicate ID not permitted: " + object.id)
        else:
            if doc.debug >= 1: print("[PyNLPl FoLiA DEBUG] Adding to index: " + object.id,file=stderr)
            doc.index[object.id] = object

    #Parse feature attributes (shortcut for feature specification for some elements)
    for c in object.ACCEPTED_DATA:
        if issubclass(c, Feature):
            if c.SUBSET in kwargs and kwargs[c.SUBSET]:
                object.append(c,cls=kwargs[c.SUBSET])
                del kwargs[c.SUBSET]

    return kwargs



def parse_datetime(s): #source: http://stackoverflow.com/questions/2211362/how-to-parse-xsddatetime-format
  """Returns (datetime, tz offset in minutes) or (None, None)."""
  m = re.match(""" ^
    (?P<year>-?[0-9]{4}) - (?P<month>[0-9]{2}) - (?P<day>[0-9]{2})
    T (?P<hour>[0-9]{2}) : (?P<minute>[0-9]{2}) : (?P<second>[0-9]{2})
    (?P<microsecond>\.[0-9]{1,6})?
    (?P<tz>
      Z | (?P<tz_hr>[-+][0-9]{2}) : (?P<tz_min>[0-9]{2})
    )?
    $ """, s, re.X)
  if m is not None:
    values = m.groupdict()
    if values["tz"] in ("Z", None):
      tz = 0
    else:
      tz = int(values["tz_hr"]) * 60 + int(values["tz_min"])
    if values["microsecond"] is None:
      values["microsecond"] = 0
    else:
      values["microsecond"] = values["microsecond"][1:]
      values["microsecond"] += "0" * (6 - len(values["microsecond"]))
    values = dict((k, int(v)) for k, v in values.items() if not k.startswith("tz"))
    try:
      return datetime(**values) # , tz
    except ValueError:
      pass
  return None


def xmltreefromstring(s, bypassleak=False):
       #Internal method, deals with different Python versions, unicode strings versus bytes, and with the leak bug in lxml
       if sys.version < '3':
            #Python 2
            if isinstance(s,str):
                if bypassleak:
                    s = unicode(s,'utf-8')
                    s = s.replace(' xml:id=', ' XMLid=')
                    s = s.encode('utf-8')
            elif isinstance(s,unicode):
                if bypassleak: s = s.replace(' xml:id=', ' XMLid=')
                s = s.encode('utf-8')
            else:
                raise Exception("Expected string, got " + type(s))
            return ElementTree.parse(StringIO(s))
       else:
            #Python 3
            if isinstance(s,bytes):
                if bypassleak:
                    s = str(s,'utf-8')
                    s = s.replace(' xml:id=', ' XMLid=')
                    s = s.encode('utf-8')
            elif isinstance(s,str):
                if bypassleak: s = s.replace(' xml:id=', ' XMLid=')
                s = s.encode('utf-8')
            return ElementTree.parse(BytesIO(s))

def xmltreefromfile(filename,bypassleak=False):
    if bypassleak:
        f = BypassLeakFile(filename,'rb')
        tree = ElementTree.parse(f)
        f.close()
        return tree
    else:
        return ElementTree.parse(file)

def makeelement(E, tagname, **kwargs):
    if sys.version < '3':
        try:
            kwargs2 = {}
            for k,v in kwargs.items():
                kwargs2[k.encode('utf-8')] = v.encode('utf-8')
                #return E._makeelement(tagname.encode('utf-8'), **{ k.encode('utf-8'): v.encode('utf-8') for k,v in kwargs.items() } )   #In one go fails on some older Python 2.6s
            return E._makeelement(tagname.encode('utf-8'), **kwargs2 )
        except ValueError as e:
            try:
                #older versions of lxml may misbehave, compensate:
                e =  E._makeelement(tagname.encode('utf-8'))
                for k,v in kwargs.items():
                    e.attrib[k.encode('utf-8')] = v
                return e
            except ValueError as e2:
                print(e,file=stderr)
                print("tagname=",tagname,file=stderr)
                print("kwargs=",kwargs,file=stderr)
                raise e
    else:
        return E._makeelement(tagname,**kwargs)


class AbstractElement(object):
    """This is the abstract base class from which all FoLiA elements are derived. This class should not be instantiated directly, but can useful if you want to check if a variable is an instance of any FoLiA element: isinstance(x, AbstractElement). It contains methods and variables also commonly inherited."""


    REQUIRED_ATTRIBS = () #List of required attributes (Members from the Attrib class)
    OPTIONAL_ATTRIBS = () #List of optional attributes (Members from the Attrib class)
    ACCEPTED_DATA = () #List of accepted data, classes inherited from AbstractElement
    ANNOTATIONTYPE = None #Annotation type (Member of AnnotationType class)
    XMLTAG = None #XML-tag associated with this element
    OCCURRENCES = 0 #Number of times this element may occur in its parent (0=unlimited, default=0)
    OCCURRENCESPERSET = 1 #Number of times this element may occur per set (0=unlimited, default=1)

    TEXTDELIMITER = None #Delimiter to use when dynamically gathering text from child elements
    PRINTABLE = False #Is this element printable (aka, can its text method be called?)
    AUTH = True #Authoritative by default. Elements the parser should skip on normal queries are non-authoritative (such as original, alternative)
    TEXTCONTAINER = False #Text containers directly take textual content. (t is a TEXTCONTAINER)

    ROOTELEMENT = True #Is this the main/root element representaive of the annotation type? Not including annotation layers

    def __init__(self, doc, *args, **kwargs):
        if not isinstance(doc, Document) and not doc is None:
            raise Exception("Expected first parameter to be instance of Document, got " + str(type(doc)))
        self.doc = doc
        self.parent = None
        self.data = []

        if self.TEXTCONTAINER:
            self.value = "" #full textual value (no elements), value will be populated by postappend()

        kwargs = parsecommonarguments(self, doc, self.ANNOTATIONTYPE, self.REQUIRED_ATTRIBS, self.OPTIONAL_ATTRIBS,**kwargs)
        for child in args:
            self.append(child)
        if 'contents' in kwargs:
            if isinstance(kwargs['contents'], list):
                for child in kwargs['contents']:
                    self.append(child)
            else:
                self.append(kwargs['contents'])
            del kwargs['contents']

        for key in kwargs:
            raise ValueError("Parameter '" + key + "' not supported by " + self.__class__.__name__)


    #def __del__(self):
    #    if self.doc and self.doc.debug:
    #        print >>stderr, "[PyNLPl FoLiA DEBUG] Removing " + repr(self)
    #    for child in self.data:
    #        del child
    #    self.doc = None
    #    self.parent = None
    #    del self.data


    def description(self):
        """Obtain the description associated with the element, will raise NoDescription if there is none"""
        for e in self:
            if isinstance(e, Description):
                return e.value
        raise NoDescription

    def textcontent(self, cls='current'):
        """Get the text explicitly associated with this element (of the specified class).
        Returns the TextContent instance rather than the actual text. Raises NoSuchText exception if
        not found.

        Unlike text(), this method does not recurse into child elements (with the sole exception of the Correction/New element), and it returns the TextContent instance rather than the actual text!
        """
        if not self.PRINTABLE: #only printable elements can hold text
            raise NoSuchText


        #Find explicit text content (same class)
        for e in self:
            if isinstance(e, TextContent):
                if e.cls == cls:
                    return e
            elif isinstance(e, Correction):
                try:
                    return e.textcontent(cls)
                except NoSuchText:
                    pass
        raise NoSuchText



    def stricttext(self, cls='current'):
        """Get the text strictly associated with this element (of the specified class). Does not recurse into children, with the sole exception of Corection/New"""
        return self.textcontent(cls).value

    def toktext(self,cls='current'):
        """Alias for text with retaintokenisation=True"""
        return self.text(cls,True)

    def text(self, cls='current', retaintokenisation=False, previousdelimiter=""):
        """Get the text associated with this element (of the specified class), will always be a unicode instance.
        If no text is directly associated with the element, it will be obtained from the children. If that doesn't result
        in any text either, a NoSuchText exception will be raised.

        If retaintokenisation is True, the space attribute on words will be ignored, otherwise it will be adhered to and text will be detokenised as much as possible.
        """


        if self.TEXTCONTAINER:
            return self.value
        if not self.PRINTABLE: #only printable elements can hold text
            raise NoSuchText


        #print >>stderr, repr(self) + '.text()'

        if self.hastext(cls):
            s = self.textcontent(cls).value
            #print >>stderr, "text content: " + s
        else:
            #Not found, descend into children
            delimiter = ""
            s = ""
            for e in self:
                if e.PRINTABLE and not isinstance(e, TextContent):
                    try:
                        s += e.text(cls,retaintokenisation, delimiter)
                        delimiter = e.gettextdelimiter(retaintokenisation)
                        #delimiter will be buffered and only printed upon next iteration, this prevent the delimiter being output at the end of a sequence
                        #print >>stderr, "Delimiter for " + repr(e) + ": " + repr(delimiter)
                    except NoSuchText:
                        continue

        s = s.strip(' \r\n\t')
        if s and previousdelimiter:
            #print >>stderr, "Outputting previous delimiter: " + repr(previousdelimiter)
            return previousdelimiter + s
        elif s:
            return s
        else:
            #No text found at all :`(
            raise NoSuchText



    def originaltext(self):
        """Alias for retrieving the original uncorrect text"""
        return self.text('original')

    def gettextdelimiter(self, retaintokenisation=False):
        """May return a customised text delimiter instead of the default for this class."""
        if self.TEXTDELIMITER is None:
            delimiter = ""
            #no text delimite rof itself, recurse into children to inherit delimiter
            for child in reversed(self):
                return child.gettextdelimiter(retaintokenisation)
            return delimiter
        else:
            return self.TEXTDELIMITER

    def feat(self,subset):
        """Obtain the feature value of the specific subset. If a feature occurs multiple times, the values will be returned in a list.

        Example::

            sense = word.annotation(folia.Sense)
            synset = sense.feat('synset')
        """
        r = None
        for f in self:
            if isinstance(f, Feature) and f.subset == subset:
                if r: #support for multiclass features
                    if isinstance(r,list):
                        r.append(f.cls)
                    else:
                        r = [r, f.cls]
                else:
                    r = f.cls
        if r is None:
            raise NoSuchAnnotation
        else:
            return r

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        if self.doc and self.doc.debug: print("[PyNLPl FoLiA DEBUG] AbstractElement Equality Check - " + repr(self) + " vs " + repr(other),file=stderr)

        #Check if we are of the same time
        if type(self) != type(other):
            if self.doc and self.doc.debug: print("[PyNLPl FoLiA DEBUG] AbstractElement Equality Check - Type mismatch: " + str(type(self)) + " vs " + str(type(other)),file=stderr)
            return False

        #Check FoLiA attributes
        if self.id != other.id:
            if self.doc and self.doc.debug: print("[PyNLPl FoLiA DEBUG] AbstractElement Equality Check - ID mismatch: " + str(self.id) + " vs " + str(other.id),file=stderr)
            return False
        if self.set != other.set:
            if self.doc and self.doc.debug: print("[PyNLPl FoLiA DEBUG] AbstractElement Equality Check - Set mismatch: " + str(self.set) + " vs " + str(other.set),file=stderr)
            return False
        if self.cls != other.cls:
            if self.doc and self.doc.debug: print("[PyNLPl FoLiA DEBUG] AbstractElement Equality Check - Class mismatch: " + repr(self.cls) + " vs " + repr(other.cls),file=stderr)
            return False
        if self.annotator != other.annotator:
            if self.doc and self.doc.debug: print("[PyNLPl FoLiA DEBUG] AbstractElement Equality Check - Annotator mismatch: " + repr(self.annotator) + " vs " + repr(other.annotator),file=stderr)
            return False
        if self.annotatortype != other.annotatortype:
            if self.doc and self.doc.debug: print("[PyNLPl FoLiA DEBUG] AbstractElement Equality Check - Annotator mismatch: " + repr(self.annotatortype) + " vs " + repr(other.annotatortype),file=stderr)
            return False

        #Check if we have same amount of children:
        mychildren = list(self)
        yourchildren = list(other)
        if len(mychildren) != len(yourchildren):
            if self.doc and self.doc.debug: print("[PyNLPl FoLiA DEBUG] AbstractElement Equality Check - Unequal amount of children",file=stderr)
            return False

        #Now check equality of children
        for mychild, yourchild in zip(mychildren, yourchildren):
            if mychild != yourchild:
                if self.doc and self.doc.debug: print("[PyNLPl FoLiA DEBUG] AbstractElement Equality Check - Child mismatch: " + repr(mychild) + " vs " + repr(yourchild) + " (in " + repr(self) + ", id: " + str(self.id) + ")",file=stderr)
                return False

        #looks like we made it! \o/
        return True

    def __len__(self):
        """Returns the number of child elements under the current element"""
        return len(self.data)

    def __nonzero__(self): #Python 2.x
        return True

    def __bool__(self):
        return True

    def __hash__(self):
        if self.id:
            return hash(self.id)
        else:
            raise TypeError("FoLiA elements are only hashable if they have an ID")

    def __iter__(self):
        """Iterate over all children of this element"""
        return iter(self.data)


    def __contains__(self, element):
        """Tests if the specified element is part of the children of the element"""
        return element in self.data

    def __getitem__(self, key):
        try:
            return self.data[key]
        except KeyError:
            raise

    def __unicode__(self): #Python 2 only
        """Alias for text()"""
        return self.text()

    def __str__(self):
        return self.text()

    def copy(self, newdoc=None):
        """Make a deep copy"""
        c = deepcopy(self)
        c.setparents()
        c.setdoc(newdoc)
        return c

    def setparents(self):
        """Correct all parent relations for elements within the scope, usually no need to call this directly, invoked implicitly by copy()"""
        for c in self:
            if isinstance(c, AbstractElement):
                c.parent = self
                c.setparents()

    def setdoc(self,newdoc):
        """Set a different document, usually no need to call this directly, invoked implicitly by copy()"""
        self.doc = newdoc
        for c in self:
            if isinstance(c, AbstractElement):
                c.setdoc(newdoc)

    def hastext(self,cls='current'):
        """Does this element have text (of the specified class)"""
        try:
            r = self.textcontent(cls)
            return True
        except NoSuchText:
            return False

    def settext(self, text, cls='current'):
        """Set the text for this element (and class)"""
        self.replace(TextContent, value=text, cls=cls)

    def setdocument(self, doc):
        """Associate a document with this element"""
        assert isinstance(doc, Document)

        if not self.doc:
            self.doc = doc
            if self.id:
                if self.id in doc:
                    raise DuplicateIDError(self.id)
                else:
                    self.doc.index[id] = self

        for e in self: #recursive for all children
            e.setdocument(doc)

    @classmethod
    def addable(Class, parent, set=None, raiseexceptions=True):
        """Tests whether a new element of this class can be added to the parent. Returns a boolean or raises ValueError exceptions (unless set to ignore)!

         This will use ``OCCURRENCES``, but may be overidden for more customised behaviour.

         This method is mostly for internal use.
         """


        if not Class in parent.ACCEPTED_DATA:
            #Class is not in accepted data, but perhaps any of its ancestors is?
            found = False
            c = Class
            try:
                while c.__base__:
                    if c.__base__ in parent.ACCEPTED_DATA:
                        found = True
                        break
                    c = c.__base__
            except:
                pass
            if not found:
                if raiseexceptions:
                    if parent.id:
                        extra = ' (id=' + parent.id + ')'
                    else:
                        extra = ''
                    raise ValueError("Unable to add object of type " + Class.__name__ + " to " + parent.__class__.__name__ + " " + extra + ". Type not allowed as child.")
                else:
                    return False



        if Class.OCCURRENCES > 0:
            #check if the parent doesn't have too many already
            count = len(parent.select(Class,None,True,[True, AbstractStructureElement])) #never descend into embedded structure annotatioton
            if count >= Class.OCCURRENCES:
                if raiseexceptions:
                    if parent.id:
                        extra = ' (id=' + parent.id + ')'
                    else:
                        extra = ''
                    raise DuplicateAnnotationError("Unable to add another object of type " + Class.__name__ + " to " + parent.__class__.__name__ + " " + extra + ". There are already " + str(count) + " instances of this class, which is the maximum.")
                else:
                    return False

        if Class.OCCURRENCESPERSET > 0 and set and Attrib.CLASS in Class.REQUIRED_ATTRIBS:
            count = len(parent.select(Class,set,True, [True, AbstractStructureElement]))
            if count >= Class.OCCURRENCESPERSET:
                if raiseexceptions:
                    if parent.id:
                        extra = ' (id=' + parent.id + ')'
                    else:
                        extra = ''
                    raise DuplicateAnnotationError("Unable to add another object of set " + set + " and type " + Class.__name__ + " to " + parent.__class__.__name__ + " " + extra + ". There are already " + str(count) + " instances of this class, which is the maximum for the set.")
                else:
                    return False


        return True


    def postappend(self):
        """This method will be called after an element is added to another. It can do extra checks and if necessary raise exceptions to prevent addition. By default makes sure the right document is associated.

        This method is mostly for internal use.
        """

        #If the element was not associated with a document yet, do so now (and for all unassociated children:
        if not self.doc and self.parent.doc:
            self.setdocument(self.parent.doc)

        if self.doc and self.doc.deepvalidation:
            self.deepvalidation()


    def deepvalidation(self):
        if self.doc and self.doc.deepvalidation and self.set and self.set[0] != '_':
            try:
                self.doc.setdefinitions[self.set].testclass(self.cls)
            except KeyError:
                if not self.doc.allowadhocsets:
                    raise DeepValidationError("Set definition for " + self.set + " not loaded!")

    def append(self, child, *args, **kwargs):
        """Append a child element. Returns the added element

        Arguments:
            * ``child``            - Instance or class

        If an *instance* is passed as first argument, it will be appended
        If a *class* derived from AbstractElement is passed as first argument, an instance will first be created and then appended.

        Keyword arguments:
            * ``alternative=``     - If set to True, the element will be made into an alternative.

        Generic example, passing a pre-generated instance::

            word.append( folia.LemmaAnnotation(doc,  cls="house", annotator="proycon", annotatortype=folia.AnnotatorType.MANUAL ) )

        Generic example, passing a class to be generated::

            word.append( folia.LemmaAnnotation, cls="house", annotator="proycon", annotatortype=folia.AnnotatorType.MANUAL )

        Generic example, setting text with a class:

            word.append( "house", cls='original' )


        """



        #obtain the set (if available, necessary for checking addability)
        if 'set' in kwargs:
            set = kwargs['set']
        else:
            try:
                set = child.set
            except:
                set = None

        #Check if a Class rather than an instance was passed
        Class = None #do not set to child.__class__
        if inspect.isclass(child):
            Class = child
            if Class.addable(self, set):
                if not 'id' in kwargs and not 'generate_id_in' in kwargs and (Attrib.ID in Class.REQUIRED_ATTRIBS):
                    kwargs['generate_id_in'] = self
                child = Class(self.doc, *args, **kwargs)
        elif args:
            raise Exception("Too many arguments specified. Only possible when first argument is a class and not an instance")


        dopostappend = True

        #Do the actual appending
        if not Class and isstring(child):
            if self.TEXTCONTAINER:
                #element is a text container and directly allows strings as content, add the string as such:
                self.data.append(u(child))
                self.value += u(child)
                dopostappend = False
            elif TextContent in self.ACCEPTED_DATA:
                #you can pass strings directly (just for convenience), will be made into textcontent automatically.
                child = TextContent(self.doc, child )
                self.data.append(child)
                child.parent = self
            else:
                raise ValueError("Unable to append object of type " + child.__class__.__name__ + " to " + self.__class__.__name__ + ". Type not allowed as child.")
        elif Class or (isinstance(child, AbstractElement) and child.__class__.addable(self, set)): #(prevents calling addable again if already done above)
            if 'alternative' in kwargs and kwargs['alternative']:
                child = Alternative(self.doc, child, generate_id_in=self)
            self.data.append(child)
            child.parent = self
            if self.TEXTCONTAINER and isinstance(child, AbstractTextMarkup):
                if self.value:
                    self.value += child.TEXTDELIMITER + child.value #TEXTDELIMITER will be "" for most AbstractTextMarkup element (except Linebreak)
                else:
                    self.value = child.value
        else:
            raise ValueError("Unable to append object of type " + child.__class__.__name__ + " to " + self.__class__.__name__ + ". Type not allowed as child.")

        if dopostappend: child.postappend()
        return child

    def insert(self, index, child, *args, **kwargs):
        """Insert a child element at specified index. Returns the added element

        If an *instance* is passed as first argument, it will be appended
        If a *class* derived from AbstractElement is passed as first argument, an instance will first be created and then appended.

        Arguments:
            * index
            * ``child``            - Instance or class

        Keyword arguments:
            * ``alternative=``     - If set to True, the element will be made into an alternative.
            * ``corrected=``       - Used only when passing strings to be made into TextContent elements.

        Generic example, passing a pre-generated instance::

            word.insert( 3, folia.LemmaAnnotation(doc,  cls="house", annotator="proycon", annotatortype=folia.AnnotatorType.MANUAL ) )

        Generic example, passing a class to be generated::

            word.insert( 3, folia.LemmaAnnotation, cls="house", annotator="proycon", annotatortype=folia.AnnotatorType.MANUAL )

        Generic example, setting text::

            word.insert( 3, "house" )


        """

        #obtain the set (if available, necessary for checking addability)
        if 'set' in kwargs:
            set = kwargs['set']
        else:
            try:
                set = child.set
            except:
                set = None

        #Check if a Class rather than an instance was passed
        Class = None #do not set to child.__class__
        if inspect.isclass(child):
            Class = child
            if Class.addable(self, set):
                if not 'id' in kwargs and not 'generate_id_in' in kwargs and (Attrib.ID in Class.REQUIRED_ATTRIBS or Attrib.ID in Class.OPTIONAL_ATTRIBS):
                    kwargs['generate_id_in'] = self
                child = Class(self.doc, *args, **kwargs)
        elif args:
            raise Exception("Too many arguments specified. Only possible when first argument is a class and not an instance")

        #Do the actual appending
        if not Class and (isinstance(child,str) or (sys.version < '3' and isinstance(child,unicode))) and TextContent in self.ACCEPTED_DATA:
            #you can pass strings directly (just for convenience), will be made into textcontent automatically.
            child = TextContent(self.doc, child )
            self.data.insert(index, child)
            child.parent = self
        elif Class or (isinstance(child, AbstractElement) and child.__class__.addable(self, set)): #(prevents calling addable again if already done above)
            if 'alternative' in kwargs and kwargs['alternative']:
                child = Alternative(self.doc, child, generate_id_in=self)
            self.data.insert(index, child)
            child.parent = self
        else:
            raise ValueError("Unable to append object of type " + child.__class__.__name__ + " to " + self.__class__.__name__ + ". Type not allowed as child.")

        child.postappend()
        return child


    @classmethod
    def findreplaceables(Class, parent, set=None,**kwargs):
        """Find replaceable elements. Auxiliary function used by replace(). Can be overriden for more fine-grained control. Mostly for internal use."""
        return parent.select(Class,set,False)



    def recomputevalue(self):
        """Internal method, recompute textual value. Only for elements that are a TEXTCONTAINER"""
        if self.TEXTCONTAINER:
            self.value = ""
            for child in self:
                if isinstance(child, AbstractElement):
                    child.recomputevalue()
                    self.value += child.value
                elif isstring(child):
                    self.value += child

    def replace(self, child, *args, **kwargs):
        """Appends a child element like ``append()``, but replaces any existing child element of the same type and set. If no such child element exists, this will act the same as append()

        Keyword arguments:
            * ``alternative`` - If set to True, the *replaced* element will be made into an alternative. Simply use ``append()`` if you want the added element
            to be an alternative.

        See ``append()`` for more information.
        """

        if 'set' in kwargs:
            set = kwargs['set']
            del kwargs['set']
        else:
            try:
                set = child.set
            except:
                set = None

        if inspect.isclass(child):
            Class = child
            replace = Class.findreplaceables(self, set, **kwargs)
        elif self.TEXTCONTAINER and isstring(child):
            #replace will replace ALL text content, removing text markup along the way!
            self.data = []
            return self.append(child, *args,**kwargs)
        else:
            Class = child.__class__
            kwargs['instance'] = child
            replace = Class.findreplaceables(self,set,**kwargs)
            del kwargs['instance']

        kwargs['set'] = set #was deleted temporarily for findreplaceables

        if len(replace) == 0:
            #nothing to replace, simply call append
            if 'alternative' in kwargs:
                del kwargs['alternative'] #has other meaning in append()
            return self.append(child, *args, **kwargs)
        elif len(replace) > 1:
            raise Exception("Unable to replace. Multiple candidates found, unable to choose.")
        elif len(replace) == 1:
            if 'alternative' in kwargs and kwargs['alternative']:
                #old version becomes alternative
                if replace[0] in self.data:
                    self.data.remove(replace[0])
                alt = self.append(Alternative)
                alt.append(replace[0])
                del kwargs['alternative'] #has other meaning in append()
            else:
                #remove old version competely
                self.remove(replace[0])
            e = self.append(child, *args, **kwargs)
            self.recomputevalue()
            return e

    def ancestors(self, Class=None):
        """Generator yielding all ancestors of this element, effectively back-tracing its path to the root element."""
        e = self
        while e:
            if e.parent:
                e = e.parent
                if not Class or isinstance(e,Class):
                    yield e
            else:
                break

    def ancestor(self, Class):
        """Find the most immediate ancestor of the specified type"""
        for e in self.ancestors():
            if isinstance(e, Class):
                return e
        raise NoSuchAnnotation


    def xml(self, attribs = None,elements = None, skipchildren = False):
        """Serialises the FoLiA element to XML, by returning an XML Element (in lxml.etree) for this element and all its children. For string output, consider the xmlstring() method instead."""
        global NSFOLIA
        E = ElementMaker(namespace=NSFOLIA,nsmap={None: NSFOLIA, 'xml' : "http://www.w3.org/XML/1998/namespace"})

        if not attribs: attribs = {}
        if not elements: elements = []

        if self.id:
            if self.doc and self.doc.bypassleak:
                attribs['XMLid'] = self.id
            else:
                attribs['{http://www.w3.org/XML/1998/namespace}id'] = self.id

        #Some attributes only need to be added if they are not the same as what's already set in the declaration
        if not '{' + NSFOLIA + '}set' in attribs: #do not override if overloaded function already set it
            try:
                if self.set:
                    if not self.ANNOTATIONTYPE in self.doc.annotationdefaults or len(self.doc.annotationdefaults[self.ANNOTATIONTYPE]) != 1 or list(self.doc.annotationdefaults[self.ANNOTATIONTYPE].keys())[0] != self.set:
                        if self.set != None:
                            attribs['{' + NSFOLIA + '}set'] = self.set
            except AttributeError:
                pass

        if not '{' + NSFOLIA + '}class' in attribs: #do not override if caller already set it
            try:
                if self.cls:
                    attribs['{' + NSFOLIA + '}class'] = self.cls
            except AttributeError:
                pass

        if not '{' + NSFOLIA + '}annotator' in attribs: #do not override if caller already set it
            try:
                if self.annotator and ((not (self.ANNOTATIONTYPE in self.doc.annotationdefaults)) or (not ( 'annotator' in self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set])) or (self.annotator != self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set]['annotator'])):
                    attribs['{' + NSFOLIA + '}annotator'] = self.annotator
                if self.annotatortype and ((not (self.ANNOTATIONTYPE in self.doc.annotationdefaults)) or (not ('annotatortype' in self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set])) or (self.annotatortype != self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set]['annotatortype'])):
                    if self.annotatortype == AnnotatorType.AUTO:
                        attribs['{' + NSFOLIA + '}annotatortype'] = 'auto'
                    elif self.annotatortype == AnnotatorType.MANUAL:
                        attribs['{' + NSFOLIA + '}annotatortype'] = 'manual'
            except AttributeError:
                pass

        if not '{' + NSFOLIA + '}confidence' in attribs: #do not override if caller already set it
            try:
                if self.confidence:
                    attribs['{' + NSFOLIA + '}confidence'] = str(self.confidence)
            except AttributeError:
                pass

        if not '{' + NSFOLIA + '}n' in attribs: #do not override if caller already set it
            try:
                if self.n:
                    attribs['{' + NSFOLIA + '}n'] = str(self.n)
            except AttributeError:
                pass

        if not '{' + NSFOLIA + '}auth' in attribs: #do not override if caller already set it
            try:
                if not self.AUTH or not self.auth: #(former is static, latter isn't)
                    attribs['{' + NSFOLIA + '}auth'] = 'no'
            except AttributeError:
                pass

        if not '{' + NSFOLIA + '}datetime' in attribs: #do not override if caller already set it
            try:
                if self.datetime and ((not (self.ANNOTATIONTYPE in self.doc.annotationdefaults)) or (not ( 'datetime' in self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set])) or (self.datetime != self.doc.annotationdefaults[self.ANNOTATIONTYPE][self.set]['datetime'])):
                    attribs['{' + NSFOLIA + '}datetime'] = self.datetime.strftime("%Y-%m-%dT%H:%M:%S")
            except AttributeError:
                pass


        omitchildren =  []

        #Are there predetermined Features in ACCEPTED_DATA?
        for c in self.ACCEPTED_DATA:
            if issubclass(c, Feature) and c.SUBSET:
                #Do we have any of those?
                for c2 in self.data:
                    if c2.__class__ is c and c.SUBSET == c2.SUBSET and c2.cls:
                        #Yes, serialize them as attributes
                        attribs[c2.SUBSET] = c2.cls
                        omitchildren.append(c2) #and skip them as elements
                        break #only one

        e  = makeelement(E, '{' + NSFOLIA + '}' + self.XMLTAG, **attribs)



        if not skipchildren and self.data:
            #append children,
            # we want make sure that text elements are in the right order, 'current' class first
            # so we first put them in  a list
            textelements = []
            otherelements = []
            for child in self:
                if isinstance(child, TextContent):
                    if child.cls == 'current':
                        textelements.insert(0, child)
                    else:
                        textelements.append(child)
                elif not (child in omitchildren):
                    otherelements.append(child)
            for child in textelements+otherelements:
                if self.TEXTCONTAINER and isstring(child):
                    if len(e) == 0:
                        if e.text:
                            e.text += child
                        else:
                            e.text = child
                    else:
                        #add to tail of last child
                        if e[-1].tail:
                            e[-1].tail += child
                        else:
                            e[-1].tail = child

                else:
                    e.append(child.xml())

        if elements: #extra elements
            for e2 in elements:
                e.append(e2)
        return e


    def json(self, attribs=None, recurse=True):
        jsonnode = {}

        jsonnode['type'] = self.XMLTAG
        if self.id:
            jsonnode['id'] = self.id
        if self.set:
            jsonnode['set'] = self.set
        if self.cls:
            jsonnode['class'] = self.cls
        if self.annotator:
            jsonnode['annotator'] = self.annotator
        if self.annotatortype:
            if self.annotatortype == AnnotatorType.AUTO:
                jsonnode['annotatortype'] = "auto"
            elif self.annotatortype == AnnotatorType.MANUAL:
                jsonnode['annotatortype'] = "manual"
        if self.confidence:
            jsonnode['confidence'] = self.confidence
        if self.n:
            jsonnode['n'] = self.n
        if self.auth:
            jsonnode['auth'] = self.auth
        if self.datetime:
            jsonnode['datetime'] = self.datetime.strftime("%Y-%m-%dT%H:%M:%S")

        if recurse:
            jsonnode['children'] = []
            for child in self:
                if self.TEXTCONTAINER and isstring(child):
                    jsonnode['text'] = child #TODO: won't work in text <x/> text scenarios
                else:
                    jsonnode['children'].append(child.json())

        if attribs:
            for attrib in attribs:
                jsonnode[attrib] = attribs

        return jsonnode



    def xmlstring(self, pretty_print=False):
        """Serialises this FoLiA element to XML, returns a (unicode) string with XML representation for this element and all its children."""
        global LXE
        s = ElementTree.tostring(self.xml(), xml_declaration=False, pretty_print=pretty_print, encoding='utf-8')
        if sys.version < '3':
            if isinstance(s, str):
                s = unicode(s,'utf-8')
        else:
            if isinstance(s,bytes):
                s = str(s,'utf-8')

        if self.doc and self.doc.bypassleak:
            s = s.replace('XMLid=','xml:id=')
        s = s.replace('ns0:','') #ugly patch to get rid of namespace prefix
        s = s.replace(':ns0','')
        return s


    def select(self, Class, set=None, recursive=True,  ignore=True, node=None):
        """Select child elements of the specified class.

        A further restriction can be made based on set. Whether or not to apply recursively (by default enabled) can also be configured, optionally with a list of elements never to recurse into.

        Arguments:
            * ``Class``: The class to select; any python class subclassed off `'AbstractElement``
            * ``set``: The set to match against, only elements pertaining to this set will be returned. If set to None (default), all elements regardless of set will be returned.
            * ``recursive``: Select recursively? Descending into child
              elements? Boolean defaulting to True.
            * ``ignore``: A list of Classes to ignore, if set to True instead
                of a list, all non-authoritative elements will be skipped.
                It is common not to
               want to recurse into the following elements:
               ``folia.Alternative``, ``folia.AlternativeLayer``,
               ``folia.Suggestion``, and ``folia.Original``. These elements
               contained in these are never *authorative*.
               set to the boolean True rather than a list, this will be the default list. You may also include the boolean True as a member of a list, if you want to skip additional tags along non-authoritative ones.
            * ``node``: Reserved for internal usage, used in recursion.

        Returns:
            A list of elements (instances)

        Example::

            text.select(folia.Sense, 'cornetto', True, [folia.Original, folia.Suggestion, folia.Alternative] )

        """

        #if ignorelist is True:
        #    ignorelist = defaultignorelist

        l = []
        if not node:
            node = self
        for e in self.data:
            if not self.TEXTCONTAINER or isinstance(e, AbstractElement):
                if ignore is True:
                    try:
                        if not e.auth:
                            continue
                    except AttributeError:
                        #not all elements have auth attribute..
                        pass
                elif ignore: #list
                    doignore = False
                    for c in ignore:
                        if c is True:
                            try:
                                if not e.auth:
                                    doignore =True
                                    break
                            except AttributeError:
                                #not all elements have auth attribute..
                                pass
                        elif c == e.__class__ or issubclass(e.__class__,c):
                            doignore = True
                            break
                    if doignore:
                        continue

                if isinstance(e, Class):
                    if not set is None:
                        try:
                            if e.set != set:
                                continue
                        except:
                            continue
                    l.append(e)
                if recursive:
                    for e2 in e.select(Class, set, recursive, ignore, e):
                        if not set is None:
                            try:
                                if e2.set != set:
                                    continue
                            except:
                                continue
                        l.append(e2)
        return l


    def xselect(self, Class, recursive=True, node=None): #obsolete?
        """Same as ``select()``, but this is a generator instead of returning a list"""
        if not node:
            node = self
        for e in self:
            if not self.TEXTCONTAINER or isinstance(e, AbstractElement):
                if isinstance(e, Class):
                    if not set is None:
                        try:
                            if e.set != set:
                                continue
                        except:
                            continue
                    yield e
                elif recursive:
                    for e2 in e.select(Class, recursive, e):
                        if not set is None:
                            try:
                                if e2.set != set:
                                    continue
                            except:
                                continue
                        yield e2

    def items(self, founditems=[]):
        """Returns a depth-first flat list of *all* items below this element (not limited to AbstractElement)"""
        l = []
        for e in self.data:
            if not e in founditems: #prevent going in recursive loops
                l.append(e)
                if isinstance(e, AbstractElement):
                    l += e.items(l)
        return l


    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None, origclass = None):
            """Returns a RelaxNG definition for this element (as an XML element (lxml.etree) rather than a string)"""

            global NSFOLIA
            E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace",'a':"http://relaxng.org/ns/annotation/0.9" })

            if origclass: cls = origclass

            preamble = []
            try:
                if cls.__doc__:
                    E2 = ElementMaker(namespace="http://relaxng.org/ns/annotation/0.9", nsmap={'a':'http://relaxng.org/ns/annotation/0.9'} )
                    preamble.append(E2.documentation(cls.__doc__))
            except AttributeError:
                pass


            attribs = []
            if Attrib.ID in cls.REQUIRED_ATTRIBS:
                attribs.append( E.attribute(name='id', ns="http://www.w3.org/XML/1998/namespace") )
            elif Attrib.ID in cls.OPTIONAL_ATTRIBS:
                attribs.append( E.optional( E.attribute(name='id', ns="http://www.w3.org/XML/1998/namespace") ) )
            if Attrib.CLASS in cls.REQUIRED_ATTRIBS:
                #Set is a tough one, we can't require it as it may be defined in the declaration: we make it optional and need schematron to resolve this later
                attribs.append( E.attribute(name='class') )
                attribs.append( E.optional( E.attribute( name='set' ) ) )
            elif Attrib.CLASS in cls.OPTIONAL_ATTRIBS:
                attribs.append( E.optional( E.attribute(name='class') ) )
                attribs.append( E.optional( E.attribute( name='set' ) ) )
            if Attrib.ANNOTATOR in cls.REQUIRED_ATTRIBS or Attrib.ANNOTATOR in cls.OPTIONAL_ATTRIBS:
               #Similarly tough
               attribs.append( E.optional( E.attribute(name='annotator') ) )
               attribs.append( E.optional( E.attribute(name='annotatortype') ) )
            if Attrib.CONFIDENCE in cls.REQUIRED_ATTRIBS:
               attribs.append(  E.attribute(E.data(type='double',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='confidence') )
            elif Attrib.CONFIDENCE in cls.OPTIONAL_ATTRIBS:
               attribs.append(  E.optional( E.attribute(E.data(type='double',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='confidence') ) )
            if Attrib.N in cls.REQUIRED_ATTRIBS:
               attribs.append( E.attribute( name='n') )
            elif Attrib.N in cls.OPTIONAL_ATTRIBS:
               attribs.append( E.optional( E.attribute( name='n') ) )
            if Attrib.DATETIME in cls.REQUIRED_ATTRIBS:
               attribs.append( E.attribute(E.data(type='dateTime',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'), name='datetime') )
            elif Attrib.DATETIME in cls.OPTIONAL_ATTRIBS:
               attribs.append( E.optional( E.attribute( E.data(type='dateTime',datatypeLibrary='http://www.w3.org/2001/XMLSchema-datatypes'),  name='datetime') ) )

            attribs.append( E.optional( E.attribute( name='auth' ) ) )

            #if cls.ALLOWTEXT:
            #    attribs.append( E.optional( E.ref(name='t') ) ) #yes, not actually an attrib, I know, but should go here

            if extraattribs:
                    for e in extraattribs:
                        attribs.append(e) #s


            elements = [] #(including attributes)
            if cls.TEXTCONTAINER:
                elements.append( E.text() )
            done = {}
            if includechildren:
                for c in cls.ACCEPTED_DATA:
                    if c.__name__[:8] == 'Abstract' and inspect.isclass(c):
                        for c2 in globals().values():
                            try:
                                if inspect.isclass(c2) and issubclass(c2, c):
                                    try:
                                        if c2.XMLTAG and not (c2.XMLTAG in done):
                                            if c2.OCCURRENCES == 1:
                                                elements.append( E.optional( E.ref(name=c2.XMLTAG) ) )
                                            else:
                                                elements.append( E.zeroOrMore( E.ref(name=c2.XMLTAG) ) )
                                            done[c2.XMLTAG] = True
                                    except AttributeError:
                                        continue
                            except TypeError:
                                pass
                    elif issubclass(c, Feature) and c.SUBSET:
                        attribs.append( E.optional( E.attribute(name=c.SUBSET)))  #features as attributes
                    else:
                        try:
                            if c.XMLTAG and not (c.XMLTAG in done):
                                if c.OCCURRENCES == 1:
                                    elements.append( E.optional( E.ref(name=c.XMLTAG) ) )
                                else:
                                    elements.append( E.zeroOrMore( E.ref(name=c.XMLTAG) ) )
                                done[c.XMLTAG] = True
                        except AttributeError:
                            continue

            if extraelements:
                    for e in extraelements:
                        elements.append( e )

            if elements:
                if len(elements) > 1:
                    attribs.append( E.interleave(*elements) )
                else:
                    attribs.append( *elements )

            if not attribs:
                attribs.append( E.empty() )

            return E.define( E.element(*(preamble + attribs), **{'name': cls.XMLTAG}), name=cls.XMLTAG, ns=NSFOLIA)

    @classmethod
    def parsexml(Class, node, doc):
        """Internal class method used for turning an XML element into an instance of the Class.

        Args:
            * ``node`' - XML Element
            * ``doc`` - Document

        Returns:
            An instance of the current Class.
        """

        assert issubclass(Class, AbstractElement)
        global NSFOLIA, NSDCOI
        dcoi = node.tag.startswith('{' + NSDCOI + '}')
        args = []
        kwargs = {}
        text = None #for dcoi support
        if Class.TEXTCONTAINER and node.text:
            args.append(node.text)
        for subnode in node:
            if not isinstance(subnode, ElementTree._Comment): #don't trip over comments
                if subnode.tag.startswith('{' + NSFOLIA + '}'):
                    if doc.debug >= 1: print("[PyNLPl FoLiA DEBUG] Processing subnode " + subnode.tag[nslen:],file=stderr)
                    args.append(doc.parsexml(subnode, Class) )
                    if Class.TEXTCONTAINER and subnode.tail:
                        args.append(subnode.tail)
                elif subnode.tag.startswith('{' + NSDCOI + '}'):
                    #Dcoi support
                    if Class is Text and subnode.tag[nslendcoi:] == 'body':
                        for subsubnode in subnode:
                            if doc.debug >= 1: print("[PyNLPl FoLiA DEBUG] Processing DCOI subnode " + subnode.tag[nslendcoi:],file=stderr)
                            args.append(doc.parsexml(subsubnode, Class) )
                    else:
                        if doc.debug >= 1: print( "[PyNLPl FoLiA DEBUG] Processing DCOI subnode " + subnode.tag[nslendcoi:],file=stderr)
                        args.append(doc.parsexml(subnode, Class) )
                elif doc.debug >= 1:
                    print("[PyNLPl FoLiA DEBUG] Ignoring subnode outside of FoLiA namespace: " + subnode.tag,file=stderr)



        id = None
        if dcoi:
            dcoipos = dcoilemma = dcoicorrection = dcoicorrectionoriginal = None
        for key, value in node.attrib.items():
            if key[0] == '{' or key =='XMLid':
                if key == '{http://www.w3.org/XML/1998/namespace}id' or key == 'XMLid':
                    id = value
                    key = 'id'
                elif key.startswith( '{' + NSFOLIA + '}'):
                    key = key[nslen:]
                    if key == 'id':
                        #ID in FoLiA namespace is always a reference, passed in kwargs as follows:
                        key = 'idref'
                elif key.startswith('{' + NSDCOI + '}'):
                    key = key[nslendcoi:]

            #D-Coi support:
            if dcoi:
                if Class is Word and key == 'pos':
                    dcoipos = value
                    continue
                elif Class is Word and  key == 'lemma':
                    dcoilemma = value
                    continue
                elif Class is Word and  key == 'correction':
                    dcoicorrection = value #class
                    continue
                elif Class is Word and  key == 'original':
                    dcoicorrectionoriginal = value
                    continue
                elif Class is Gap and  key == 'reason':
                    key = 'class'
                elif Class is Gap and  key == 'hand':
                    key = 'annotator'
                elif Class is Division and  key == 'type':
                    key = 'cls'

            kwargs[key] = value

        #D-Coi support:
        if dcoi and TextContent in Class.ACCEPTED_DATA and node.text:
            text = node.text.strip()

            kwargs['text'] = text
            if not AnnotationType.TOKEN in doc.annotationdefaults:
                doc.declare(AnnotationType.TOKEN, set='http://ilk.uvt.nl/folia/sets/ilktok.foliaset')

        if doc.debug >= 1: print("[PyNLPl FoLiA DEBUG] Found " + node.tag[nslen:],file=stderr)
        instance = Class(doc, *args, **kwargs)
        #if id:
        #    if doc.debug >= 1: print >>stderr, "[PyNLPl FoLiA DEBUG] Adding to index: " + id
        #    doc.index[id] = instance
        if dcoi:
            if dcoipos:
                if not AnnotationType.POS in doc.annotationdefaults:
                    doc.declare(AnnotationType.POS, set='http://ilk.uvt.nl/folia/sets/cgn-legacy.foliaset')
                instance.append( PosAnnotation(doc, cls=dcoipos) )
            if dcoilemma:
                if not AnnotationType.LEMMA in doc.annotationdefaults:
                    doc.declare(AnnotationType.LEMMA, set='http://ilk.uvt.nl/folia/sets/mblem-nl.foliaset')
                instance.append( LemmaAnnotation(doc, cls=dcoilemma) )
            if dcoicorrection and dcoicorrectionoriginal and text:
                if not AnnotationType.CORRECTION in doc.annotationdefaults:
                    doc.declare(AnnotationType.CORRECTION, set='http://ilk.uvt.nl/folia/sets/dcoi-corrections.foliaset')
                instance.correct(generate_id_in=instance, cls=dcoicorrection, original=dcoicorrectionoriginal, new=text)
        return instance

    def resolveword(self, id):
        return None

    def remove(self, child):
        """Removes the child element"""
        if not isinstance(child, AbstractElement):
            raise ValueError("Expected AbstractElement, got " + str(type(child)))
        if child.parent == self:
            child.parent = None
        self.data.remove(child)
        #delete from index
        if child.id and self.doc and child.id in self.doc.index:
            del self.doc.index[child.id]

class Description(AbstractElement):
    """Description is an element that can be used to associate a description with almost any other FoLiA element"""
    XMLTAG = 'desc'
    OCCURRENCES = 1

    def __init__(self,doc, *args, **kwargs):
        """Required keyword arguments:
                * ``value=``: The text content for the description (``str`` or ``unicode``)
        """
        if 'value' in kwargs:
            if kwargs['value'] is None:
                self.value = ""
            elif isstring(kwargs['value']):
                self.value = u(kwargs['value'])
            else:
                if sys.version < '3':
                    raise Exception("value= parameter must be unicode or str instance, got " + str(type(kwargs['value'])))
                else:
                    raise Exception("value= parameter must be str instance, got " + str(type(kwargs['value'])))
            del kwargs['value']
        else:
            raise Exception("Description expects value= parameter")
        super(Description,self).__init__(doc, *args, **kwargs)

    def __nonzero__(self): #Python 2.x
        return bool(self.value)

    def __bool__(self):
        return bool(self.value)

    def __unicode__(self):
        return self.value

    def __str__(self):
        return self.value


    def xml(self, attribs = None,elements = None, skipchildren = False):
        global NSFOLIA
        E = ElementMaker(namespace=NSFOLIA,nsmap={None: NSFOLIA, 'xml' : "http://www.w3.org/XML/1998/namespace"})

        if not attribs:
            attribs = {}

        return E.desc(self.value, **attribs)

    def json(self,attribs =None, recurse=True):
        jsonnode = {'type': self.XMLTAG, 'value': self.value}
        if attribs:
            for attrib in attribs:
                jsonnode[attrib] = attrib
        return jsonnode

    @classmethod
    def parsexml(Class, node, doc):
        global NSFOLIA
        kwargs = {}
        kwargs['value'] = node.text
        return Description(doc, **kwargs)


    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        global NSFOLIA
        E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace"})
        return E.define( E.element(E.text(), name=cls.XMLTAG), name=cls.XMLTAG, ns=NSFOLIA)

class AllowCorrections(object):
    def correct(self, **kwargs):
        """Apply a correction (TODO: documentation to be written still)"""

        if 'reuse' in kwargs:
            #reuse an existing correction instead of making a new one
            if isinstance(kwargs['reuse'], Correction):
                c = kwargs['reuse']
            else: #assume it's an index
                try:
                    c = self.doc.index[kwargs['reuse']]
                    assert isinstance(c, Correction)
                except:
                    raise ValueError("reuse= must point to an existing correction (id or instance)! Got " + str(kwargs['reuse']))

            suggestionsonly = (not c.hasnew() and not c.hasoriginal() and c.hassuggestions())

            if 'new' in kwargs and c.hascurrent():
                #can't add new if there's current, so first set original to current, and then delete current

                if 'current' in kwargs:
                    raise Exception("Can't set both new= and current= !")
                if not 'original' in kwargs:
                    kwargs['original'] = c.current()

                c.remove(c.current())
        else:
            if not 'id' in kwargs and not 'generate_id_in' in kwargs:
                kwargs['generate_id_in'] = self
            kwargs2 = copy(kwargs)
            for x in ['new','original','suggestion', 'suggestions','current', 'insertindex']:
                if x in kwargs2:
                    del kwargs2[x]
            c = Correction(self.doc, **kwargs2)

        addnew = False
        if 'insertindex' in kwargs:
            insertindex = int(kwargs['insertindex'])
            del kwargs['insertindex']
        else:
            insertindex = -1 #append

        if 'current' in kwargs:
            if 'original' in kwargs or 'new' in kwargs: raise Exception("When setting current=, original= and new= can not be set!")
            if not isinstance(kwargs['current'], list) and not isinstance(kwargs['current'], tuple): kwargs['current'] = [kwargs['current']] #support both lists (for multiple elements at once), as well as single element
            c.replace(Current(self.doc, *kwargs['current']))
            for o in kwargs['current']: #delete current from current element
                if o in self and isinstance(o, AbstractElement):
                    if insertindex == -1: insertindex = self.data.index(o)
                    self.remove(o)
            del kwargs['current']
        if 'new' in kwargs:
            if not isinstance(kwargs['new'], list) and not isinstance(kwargs['new'], tuple): kwargs['new'] = [kwargs['new']] #support both lists (for multiple elements at once), as well as single element
            addnew = New(self.doc, *kwargs['new'])
            c.replace(addnew)
            for current in c.select(Current): #delete current if present
                c.remove(current)
            del kwargs['new']
        if 'original' in kwargs:
            if not isinstance(kwargs['original'], list) and not isinstance(kwargs['original'], tuple): kwargs['original'] = [kwargs['original']] #support both lists (for multiple elements at once), as well as single element
            c.replace(Original(self.doc, *kwargs['original']))
            for o in kwargs['original']: #delete original from current element
                if o in self and isinstance(o, AbstractElement):
                    if insertindex == -1: insertindex = self.data.index(o)
                    self.remove(o)
            for current in c.select(Current):  #delete current if present
                c.remove(current)
            del kwargs['original']
        elif addnew:
            #original not specified, find automagically:
            original = []
            for new in addnew:
                kwargs2 = {}
                if isinstance(new, TextContent):
                    kwargs2['cls'] = new.cls
                try:
                    set = new.set
                except:
                    set = None
                #print("DEBUG: Finding replaceables within " + str(repr(self)) + " for ", str(repr(new)), " set " ,set , " args " ,repr(kwargs2),file=sys.stderr)
                replaceables = new.__class__.findreplaceables(self, set, **kwargs2)
                #print("DEBUG: " , len(replaceables) , " found",file=sys.stderr)
                original += replaceables
            if not original:
                #print("DEBUG: ", self.xmlstring(),file=sys.stderr)
                raise Exception("No original= specified and unable to automatically infer on " + str(repr(self)) + " for " + str(repr(new)) + " with set " + set)
            else:
                c.replace( Original(self.doc, *original))
                for current in c.select(Current):  #delete current if present
                    c.remove(current)

        if addnew:
            for original in c.original():
                if original in self:
                    self.remove(original)

        if 'suggestion' in kwargs:
            kwargs['suggestions'] = [kwargs['suggestion']]
            del kwargs['suggestion']
        if 'suggestions' in kwargs:
            for suggestion in kwargs['suggestions']:
                if isinstance(suggestion, Suggestion):
                    c.append(suggestion)
                elif isinstance(suggestion, list) or isinstance(suggestion, tuple):
                    c.append(Suggestion(self.doc, *suggestion))
                else:
                    c.append(Suggestion(self.doc, suggestion))
            del kwargs['suggestions']




        if 'reuse' in kwargs:
            if addnew and suggestionsonly:
                #What was previously only a suggestion, now becomes a real correction
                #If annotator, annotatortypes
                #are associated with the correction as a whole, move it to the suggestions
                #correction-wide annotator, annotatortypes might be overwritten
                for suggestion in c.suggestions():
                    if c.annotator and not suggestion.annotator:
                        suggestion.annotator = c.annotator
                    if c.annotatortype and not suggestion.annotatortype:
                        suggestion.annotatortype = c.annotatortype

            if 'annotator' in kwargs:
                c.annotator = kwargs['annotator']
            if 'annotatortype' in kwargs:
                c.annotatortype = kwargs['annotatortype']
            if 'confidence' in kwargs:
                c.confidence = float(kwargs['confidence'])
            del kwargs['reuse']
        else:
            if insertindex == -1:
                self.append(c)
            else:
                self.insert(insertindex, c)
        return c


class AllowTokenAnnotation(AllowCorrections):
    """Elements that allow token annotation (including extended annotation) must inherit from this class"""


    def annotations(self,Class,set=None):
        """Obtain annotations. Very similar to ``select()`` but raises an error if the annotation was not found.

        Arguments:
            * ``Class`` - The Class you want to retrieve (e.g. PosAnnotation)
            * ``set``   - The set you want to retrieve (defaults to None, which selects irregardless of set)

        Returns:
            A list of elements

        Raises:
            ``NoSuchAnnotation`` if the specified annotation does not exist.
        """
        l = self.select(Class,set,True,defaultignorelist_annotations)
        if not l:
            raise NoSuchAnnotation()
        else:
            return l

    def hasannotation(self,Class,set=None):
        """Returns an integer indicating whether such as annotation exists, and if so, how many. See ``annotations()`` for a description of the parameters."""
        l = self.select(Class,set,True,defaultignorelist_annotations)
        return len(l)

    def annotation(self, type, set=None):
        """Will return a **single** annotation (even if there are multiple). Raises a ``NoSuchAnnotation`` exception if none was found"""
        l = self.select(type,set,True,defaultignorelist_annotations)
        if len(l) >= 1:
            return l[0]
        else:
            raise NoSuchAnnotation()

    def alternatives(self, Class=None, set=None):
        """Obtain a list of alternatives, either all or only of a specific annotation type, and possibly restrained also by set.

        Arguments:
            * ``Class`` - The Class you want to retrieve (e.g. PosAnnotation). Or set to None to select all alternatives regardless of what type they are.
            * ``set``   - The set you want to retrieve (defaults to None, which selects irregardless of set)

        Returns:
            List of Alternative elements
        """
        l = []

        for e in self.select(Alternative,None, True, []):
            if Class is None:
                l.append(e)
            elif len(e) >= 1: #child elements?
                for e2 in e:
                    try:
                        if isinstance(e2, Class):
                            try:
                                if set is None or e2.set == set:
                                    found = True
                                    l.append(e) #not e2
                                    break #yield an alternative only once (in case there are multiple matches)
                            except AttributeError:
                                continue
                    except AttributeError:
                        continue
        return l


class AllowGenerateID(object):
    """Classes inherited from this class allow for automatic ID generation, using the convention of adding a period, the name of the element , another period, and a sequence number"""

    def _getmaxid(self, xmltag):
        try:
            if xmltag in self.maxid:
                return self.maxid[xmltag]
            else:
                return 0
        except:
            return 0


    def _setmaxid(self, child):
        #print "set maxid on " + repr(self) + " for " + repr(child)
        try:
            self.maxid
        except AttributeError:
            self.maxid = {}
        try:
            if child.id and child.XMLTAG:
                fields = child.id.split(self.doc.IDSEPARATOR)
                if len(fields) > 1 and fields[-1].isdigit():
                    if not child.XMLTAG in self.maxid:
                        self.maxid[child.XMLTAG] = int(fields[-1])
                        #print "set maxid on " + repr(self) + ", " + child.XMLTAG + " to " + fields[-1]
                    else:
                        if self.maxid[child.XMLTAG] < int(fields[-1]):
                           self.maxid[child.XMLTAG] = int(fields[-1])
                           #print "set maxid on " + repr(self) + ", " + child.XMLTAG + " to " + fields[-1]

        except AttributeError:
            pass



    def generate_id(self, cls):
        if isinstance(cls,str):
            xmltag = cls
        else:
            try:
                xmltag = cls.XMLTAG
            except:
                raise Exception("Expected a class such as Alternative, Correction, etc...")


        maxid = self._getmaxid(xmltag)

        id = None
        if self.id:
            id = self.id
        else:
            #this element has no ID, fall back to closest parent ID:
            e = self
            while e.parent:
                if e.id:
                    id = e.id
                    break
                e = e.parent

        while True:
            maxid += 1
            id = id + '.' + xmltag + '.' + str(maxid)
            if not self.doc or id not in self.doc.index: #extra check
                break

        try:
            self.maxid
        except AttributeError:
            self.maxid = {}
        self.maxid[xmltag] = maxid #Set MAX ID
        return id

        #i = 0
        #while True:
        #    i += 1
        #    print i
        #    if self.id:
        #        id = self.id
        #    else:
        #        #this element has no ID, fall back to closest parent ID:
        #        e = self
        #        while e.parent:
        #            if e.id:
        #                id = e.id
        #                break
        #            e = e.parent
        #    id = id + '.' + xmltag + '.' + str(self._getmaxid(xmltag) + i)
        #    if not id in self.doc.index:
        #        return id


class AbstractStructureElement(AbstractElement, AllowTokenAnnotation, AllowGenerateID):
    """Abstract element, all structure elements inherit from this class. Never instantiated directly."""

    PRINTABLE = True
    TEXTDELIMITER = "\n\n" #bigger gap between structure elements
    OCCURRENCESPERSET = 0 #Number of times this element may occur per set (0=unlimited, default=1)

    REQUIRED_ATTRIBS = (Attrib.ID,)
    OPTIONAL_ATTRIBS = Attrib.ALL


    def __init__(self, doc, *args, **kwargs):
        super(AbstractStructureElement,self).__init__(doc, *args, **kwargs)

    def resolveword(self, id):
        for child in self:
            r =  child.resolveword(id)
            if r:
                return r
        return None

    def append(self, child, *args, **kwargs):
        """See ``AbstractElement.append()``"""
        e = super(AbstractStructureElement,self).append(child, *args, **kwargs)
        self._setmaxid(e)
        return e


    def words(self, index = None):
        """Returns a list of Word elements found (recursively) under this element.

        Arguments:
            * ``index``: If set to an integer, will retrieve and return the n'th element (starting at 0) instead of returning the list of all
        """
        if index is None:
            return self.select(Word,None,True,defaultignorelist_structure)
        else:
            return self.select(Word,None,True,defaultignorelist_structure)[index]


    def paragraphs(self, index = None):
        """Returns a list of Paragraph elements found (recursively) under this element.

        Arguments:
            * ``index``: If set to an integer, will retrieve and return the n'th element (starting at 0) instead of returning the list of all
        """
        if index is None:
            return self.select(Paragraph,None,True,defaultignorelist_structure)
        else:
            return self.select(Paragraph,None,True,defaultignorelist_structure)[index]

    def sentences(self, index = None):
        """Returns a list of Sentence elements found (recursively) under this element

        Arguments:
            * ``index``: If set to an integer, will retrieve and return the n'th element (starting at 0) instead of returning the list of all
        """
        if index is None:
            return self.select(Sentence,None,True,defaultignorelist_structure)
        else:
            return self.select(Sentence,None,True,defaultignorelist_structure)[index]

    def layers(self, annotationtype=None,set=None):
        """Returns a list of annotation layers found *directly* under this element, does not include alternative layers"""
        if inspect.isclass(annotationtype): annotationtype = annotationtype.ANNOTATIONTYPE
        return [ x for x in self.select(AbstractAnnotationLayer,set,False,True) if annotationtype is None or x.ANNOTATIONTYPE == annotationtype ]

    def hasannotationlayer(self, annotationtype=None,set=None):
        """Does the specified annotation layer exist?"""
        l = self.layers(annotationtype, set)
        return (len(l) > 0)

    def __eq__(self, other):
        return super(AbstractStructureElement, self).__eq__(other)

class AbstractAnnotation(AbstractElement):
    pass

class AbstractTokenAnnotation(AbstractAnnotation, AllowGenerateID):
    """Abstract element, all token annotation elements are derived from this class"""

    OCCURRENCESPERSET = 1 #Do not allow duplicates within the same set

    REQUIRED_ATTRIBS = (Attrib.CLASS,)
    OPTIONAL_ATTRIBS = Attrib.ALL

    def append(self, child, *args, **kwargs):
        """See ``AbstractElement.append()``"""
        e = super(AbstractTokenAnnotation,self).append(child, *args, **kwargs)
        self._setmaxid(e)
        return e

class AbstractExtendedTokenAnnotation(AbstractTokenAnnotation):
    pass


class AbstractTextMarkup(AbstractAnnotation):
    PRINTABLE = True
    TEXTDELIMITER = ""
    #ACCEPTED_DATA is defined after this class

    REQUIRED_ATTRIBS = ()
    OPTIONAL_ATTRIBS = Attrib.ALL
    TEXTCONTAINER = True #This element is a direct text container
    ROOTELEMENT = False

    def __init__(self, doc, *args, **kwargs):
        if 'idref' in kwargs:
            self.idref = kwargs['idref']
            del kwargs['idref']
        else:
            self.idref = None
        super(AbstractTextMarkup,self).__init__(doc, *args, **kwargs)

        if self.value and (self.value != self.value.translate(ILLEGAL_UNICODE_CONTROL_CHARACTERS)):
            raise ValueError("There are illegal unicode control characters present in Text Markup Content: " + repr(self.value))

    def resolve(self):
        if self.idref:
            return self.doc[self.idref]
        else:
            return self

    def xml(self, attribs = None,elements = None, skipchildren = False):
        if not attribs: attribs = {}
        if self.idref:
            attribs['id'] = self.idref
        return super(AbstractTextMarkup,self).xml(attribs,elements, skipchildren)

    def json(self,attribs =None, recurse=True):
        if not attribs: attribs = {}
        if self.idref:
            attribs['id'] = self.idref
        return super(AbstractTextMarkup,self).json(attribs,recurse)

    @classmethod
    def parsexml(Class, node, doc):
        global NSFOLIA
        if 'id' in node.attrib:
            idref = node.attrib['id']
            del node.attrib['id']
        else:
            idref = None
        instance = super(AbstractTextMarkup,Class).parsexml(node, doc)
        if idref:
            instance.idref = idref
        return instance

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        global NSFOLIA
        E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace",'a':"http://relaxng.org/ns/annotation/0.9" })
        if not extraattribs: extraattribs = []
        extraattribs.append( E.optional(E.attribute(name='id' ))) #id reference
        return super(AbstractTextMarkup, cls).relaxng(includechildren, extraattribs, extraelements)

AbstractTextMarkup.ACCEPTED_DATA = (AbstractTextMarkup,)

class TextMarkupString(AbstractTextMarkup):
    ANNOTATIONTYPE = AnnotationType.STRING
    XMLTAG = 't-str'

class TextMarkupGap(AbstractTextMarkup):
    ANNOTATIONTYPE = AnnotationType.GAP
    XMLTAG = 't-gap'

class TextMarkupCorrection(AbstractTextMarkup):
    ANNOTATIONTYPE = AnnotationType.CORRECTION
    XMLTAG = 't-correction'

    def __init__(self, doc, *args, **kwargs):
        if 'original' in kwargs:
            self.original = kwargs['original']
            del kwargs['original']
        else:
            self.original = None
        super(TextMarkupCorrection,self).__init__(doc, *args, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False):
        if not attribs: attribs = {}
        if self.original:
            attribs['original'] = self.original
        return super(TextMarkupCorrection,self).xml(attribs,elements, skipchildren)

    def json(self,attribs =None, recurse=True):
        if not attribs: attribs = {}
        if self.original:
            attribs['original'] = self.original
        return super(TextMarkupCorrection,self).json(attribs,recurse)

    @classmethod
    def parsexml(Class, node, doc):
        global NSFOLIA
        if 'original' in node.attrib:
            original = node.attrib['original']
            del node.attrib['original']
        else:
            original = None
        instance = super(TextMarkupCorrection,Class).parsexml(node, doc)
        if original:
            instance.original = original
        return instance

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        global NSFOLIA
        E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace",'a':"http://relaxng.org/ns/annotation/0.9" })
        if not extraattribs: extraattribs = []
        extraattribs.append( E.optional(E.attribute(name='original' )))
        return super(TextMarkupCorrection, cls).relaxng(includechildren, extraattribs, extraelements)


class TextMarkupError(AbstractTextMarkup):
    ANNOTATIONTYPE = AnnotationType.ERRORDETECTION
    XMLTAG = 't-error'

class TextMarkupStyle(AbstractTextMarkup):
    ANNOTATIONTYPE = AnnotationType.STYLE
    XMLTAG = 't-style'



class TextContent(AbstractElement):
    """Text content element (``t``), holds text to be associated with whatever element the text content element is a child of.

    Text content elements
    on structure elements like ``Paragraph`` and ``Sentence`` are by definition untokenised. Only on ``Word`` level and deeper they are by definition tokenised.

    Text content elements can specify offset that refer to text at a higher parent level. Use the following keyword arguments:
        * ``ref=``: The instance to point to, this points to the element holding the text content element, not the text content element itself.
        * ``offset=``: The offset where this text is found, offsets start at 0
    """
    XMLTAG = 't'
    OPTIONAL_ATTRIBS = (Attrib.CLASS,Attrib.ANNOTATOR,Attrib.CONFIDENCE, Attrib.DATETIME)
    ANNOTATIONTYPE = AnnotationType.TEXT
    OCCURRENCES = 0 #Number of times this element may occur in its parent (0=unlimited)
    OCCURRENCESPERSET = 0 #Number of times this element may occur per set (0=unlimited)

    TEXTCONTAINER = True #This element is a direct text container
    ACCEPTED_DATA = (AbstractTextMarkup,)
    ROOTELEMENT = True


    def __init__(self, doc, *args, **kwargs):
        global ILLEGAL_UNICODE_CONTROL_CHARACTERS
        """Required keyword arguments:

                * ``value=``: Set to a unicode or str containing the text

            Example::

                text = folia.TextContent(doc, 'test')

                text = folia.TextContent(doc, 'test',cls='original')

        """

        if 'value' in kwargs:
            #for backward compatibility
            kwargs['contents'] = kwargs['value']
            del kwargs['value']


        if 'offset' in kwargs: #offset
            self.offset = int(kwargs['offset'])
            del kwargs['offset']
        else:
            self.offset = None

        if 'ref' in kwargs: #reference to offset
            if isinstance(self.ref, AbstractElement):
                self.ref = kwargs['ref']
            else:
                try:
                    self.ref = doc.index[kwargs['ref']]
                except:
                    raise UnresolvableTextContent("Unable to resolve textcontent reference: " + kwargs['ref'] + " (class=" + self.cls+")")
            del kwargs['ref']
        else:
            self.ref = None #will be set upon parent.append()

        #If no class is specified, it defaults to 'current'. (FoLiA uncharacteristically predefines two classes for t: current and original)
        if not ('cls' in kwargs) and not ('class' in kwargs):
            kwargs['cls'] = 'current'

        super(TextContent,self).__init__(doc, *args, **kwargs)

        if not self.value:
            raise ValueError("Empty text content elements are not allowed")
        if (self.value != self.value.translate(ILLEGAL_UNICODE_CONTROL_CHARACTERS)):
            raise ValueError("There are illegal unicode control characters present in TextContent: " + repr(self.value))


    def text(self):
        """Obtain the text (unicode instance)"""
        return super(TextContent,self).text() #AbstractElement will handle it now, merely overridden to get rid of parameters that dont make sense in this context

    def validateref(self):
        """Validates the Text Content's references. Raises UnresolvableTextContent when invalid"""

        if self.offset is None: return True #nothing to test
        if self.ref:
            ref = self.ref
        else:
            ref = self.finddefaultreference()

        if not ref:
            raise UnresolvableTextContent("Default reference for textcontent not found!")
        elif ref.hastext(self.cls):
            raise UnresolvableTextContent("Reference has no such text (class=" + self.cls+")")
        elif self.value != ref.textcontent(self.cls).value[self.offset:self.offset+len(self.value)]:
            raise UnresolvableTextContent("Referenced found but does not match!")
        else:
            #finally, we made it!
            return True






    def __unicode__(self):
        return self.value

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, TextContent):
            return self.value == other.value
        elif isstring(other):
            return self.value == u(other)
        else:
            return False

    #append is implemented, the default suffices

    def postappend(self):
        """(Method for internal usage, see ``AbstractElement.postappend()``)"""
        if isinstance(self.parent, Original):
            if self.cls == 'current': self.cls = 'original'

        #assert (self.testreference() == True)
        super(TextContent, self).postappend()


    def finddefaultreference(self):
        """Find the default reference for text offsets:
          The parent of the current textcontent's parent (counting only Structure Elements and Subtoken Annotation Elements)

          Note: This returns not a TextContent element, but its parent. Whether the textcontent actually exists is checked later/elsewhere
        """

        depth = 0
        e = self
        while True:
            if e.parent:
                e = e.parent
            else:
                #no parent, breaking
                return False

            if isinstance(e,AbstractStructureElement) or isinstance(e,AbstractSubtokenAnnotation):
                depth += 1
                if depth == 2:
                    return e


        return False

    #Change in behaviour (FoLiA 0.10), iter() no longer iterates over the text itself!!


    #Change in behaviour (FoLiA 0.10), len() no longer return the length of the text!!


    @classmethod
    def findreplaceables(Class, parent, set, **kwargs):
        """(Method for internal usage, see AbstractElement)"""
        #some extra behaviour for text content elements, replace also based on the 'corrected' attribute:
        if not 'cls' in kwargs:
            kwargs['cls'] = 'current'
        replace = super(TextContent, Class).findreplaceables(parent, set, **kwargs)
        replace = [ x for x in replace if x.cls == kwargs['cls']]
        del kwargs['cls'] #always delete what we processed
        return replace


    @classmethod
    def parsexml(Class, node, doc):
        """(Method for internal usage, see AbstractElement)"""
        global NSFOLIA

        e = super(TextContent,Class).parsexml(node,doc)
        if 'offset' in node.attrib:
            e.offset = int(node.attrib['offset'])
        if 'ref' in node.attrib:
            e.ref = node.attrib['ref']
        return e



    def xml(self, attribs = None,elements = None, skipchildren = False):
        global NSFOLIA
        E = ElementMaker(namespace=NSFOLIA,nsmap={None: NSFOLIA, 'xml' : "http://www.w3.org/XML/1998/namespace"})

        attribs = {}
        if not self.offset is None:
            attribs['{' + NSFOLIA + '}offset'] = str(self.offset)
        if self.parent and self.ref:
            attribs['{' + NSFOLIA + '}ref'] = self.ref.id

        #if self.cls != 'current' and not (self.cls == 'original' and any( isinstance(x, Original) for x in self.ancestors() )  ):
        #    attribs['{' + NSFOLIA + '}class'] = self.cls
        #else:
        #    if '{' + NSFOLIA + '}class' in attribs:
        #        del attribs['{' + NSFOLIA + '}class']
        #return E.t(self.value, **attribs)

        e = super(TextContent,self).xml(attribs,elements,skipchildren)
        if '{' + NSFOLIA + '}class' in e.attrib and e.attrib['{' + NSFOLIA + '}class'] == "current":
            #delete 'class=current'
            del e.attrib['{' + NSFOLIA + '}class']

        return e

    def json(self, attribs =None, recurse =True):
        attribs = {}
        if not self.offset is None:
            attribs['offset'] = self.offset
        if self.parent and self.ref:
            attribs['ref'] = self.ref.id
        return super(TextContent,self).json(attribs, recurse)


    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        global NSFOLIA
        E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace",'a':"http://relaxng.org/ns/annotation/0.9" })
        if not extraattribs: extraattribs = []
        extraattribs.append( E.optional(E.attribute(name='offset' )))
        extraattribs.append( E.optional(E.attribute(name='ref' )))
        return super(TextContent, cls).relaxng(includechildren, extraattribs, extraelements)




class Content(AbstractElement):     #used for raw content, subelement for Gap
    OCCURRENCES = 1
    XMLTAG = 'content'

    def __init__(self,doc, *args, **kwargs):
        if 'value' in kwargs:
            if isstring(kwargs['value']):
                self.value = u(kwargs['value'])
            elif kwargs['value'] is None:
                self.value = ""
            else:
                raise Exception("value= parameter must be unicode or str instance")
            del kwargs['value']
        else:
            raise Exception("Description expects value= parameter")
        super(Content,self).__init__(doc, *args, **kwargs)

    def __nonzero__(self):
        return bool(self.value)

    def __bool__(self):
        return bool(self.value)

    def __unicode__(self):
        return self.value

    def __str__(self):
        return self.value

    def xml(self, attribs = None,elements = None, skipchildren = False):
        global NSFOLIA
        E = ElementMaker(namespace=NSFOLIA,nsmap={None: NSFOLIA, 'xml' : "http://www.w3.org/XML/1998/namespace"})

        if not attribs:
            attribs = {}

        return E.content(self.value, **attribs)

    def json(self,attribs =None, recurse=True):
        jsonnode = {'type': self.XMLTAG, 'value': self.value}
        if attribs:
            for attrib in attribs:
                jsonnode[attrib] = attrib
        return jsonnode


    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        global NSFOLIA
        E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace"})
        return E.define( E.element(E.text(), name=cls.XMLTAG), name=cls.XMLTAG, ns=NSFOLIA)

    @classmethod
    def parsexml(Class, node, doc):
        global NSFOLIA
        kwargs = {}
        kwargs['value'] = node.text
        return Content(doc, **kwargs)

class Gap(AbstractElement):
    """Gap element. Represents skipped portions of the text. Contains Content and Desc elements"""
    ACCEPTED_DATA = (Content, Description)
    OPTIONAL_ATTRIBS = (Attrib.ID,Attrib.CLASS,Attrib.ANNOTATOR,Attrib.CONFIDENCE,Attrib.N,)
    ANNOTATIONTYPE = AnnotationType.GAP
    XMLTAG = 'gap'

    def __init__(self, doc, *args, **kwargs):
        if 'content' in kwargs:
            self.content = kwargs['content']
            del kwargs['content']
        elif 'description' in kwargs:
            self.description = kwargs['description']
            del kwargs['description']
        super(Gap,self).__init__(doc, *args, **kwargs)

    def content(self):
        for e in self:
            if isinstance(e, Content):
                return e.value
        return ""


class Linebreak(AbstractStructureElement, AbstractTextMarkup): #this element has a double role!!
    """Line break element, signals a line break"""
    REQUIRED_ATTRIBS = ()
    ACCEPTED_DATA = ()
    XMLTAG = 'br'
    ANNOTATIONTYPE = AnnotationType.LINEBREAK
    TEXTDELIMITER = "\n"

TextContent.ACCEPTED_DATA = TextContent.ACCEPTED_DATA + (Linebreak,) #shouldn't be necessary because of the multiple inheritance, but something's wrong and this quickly patches it

class Whitespace(AbstractStructureElement):
    """Whitespace element, signals a vertical whitespace"""
    REQUIRED_ATTRIBS = ()
    ACCEPTED_DATA = ()
    XMLTAG = 'whitespace'
    ANNOTATIONTYPE = AnnotationType.WHITESPACE

    TEXTDELIMITER = "\n\n"

class Word(AbstractStructureElement, AllowCorrections):
    """Word (aka token) element. Holds a word/token and all its related token annotations."""
    XMLTAG = 'w'
    ANNOTATIONTYPE = AnnotationType.TOKEN
    #ACCEPTED_DATA DEFINED LATER (after Correction)

    #will actually be determined by gettextdelimiter()

    def __init__(self, doc, *args, **kwargs):
        """Keyword arguments:

            * ``space=``: Boolean indicating whether this token is followed by a space (defaults to True)

            Example::

                sentence.append( folia.Word, 'This')
                sentence.append( folia.Word, 'is')
                sentence.append( folia.Word, 'a')
                sentence.append( folia.Word, 'test', space=False)
                sentence.append( folia.Word, '.')
        """
        self.space = True

        if 'space' in kwargs:
            self.space = kwargs['space']
            del kwargs['space']
        super(Word,self).__init__(doc, *args, **kwargs)


    def sentence(self):
        """Obtain the sentence this word is a part of, otherwise return None"""
        e = self;
        while e.parent:
            if isinstance(e, Sentence):
                return e
            e = e.parent
        return None


    def paragraph(self):
        """Obtain the paragraph this word is a part of, otherwise return None"""
        e = self;
        while e.parent:
            if isinstance(e, Paragraph):
                return e
            e = e.parent
        return None

    def division(self):
        """Obtain the deepest division this word is a part of, otherwise return None"""
        e = self;
        while e.parent:
            if isinstance(e, Division):
                return e
            e = e.parent
        return None



    def incorrection(self):
        """Is this word part of a correction? If it is, it returns the Correction element (evaluating to True), otherwise it returns None"""
        e = self

        while not e.parent is None:
                if isinstance(e, Correction):
                    return e
                if isinstance(e, Sentence):
                    break
                e = e.parent

        return None



    def pos(self,set=None):
        """Shortcut: returns the FoLiA class of the PoS annotation (will return only one if there are multiple!)"""
        return self.annotation(PosAnnotation,set).cls

    def lemma(self, set=None):
        """Shortcut: returns the FoLiA class of the lemma annotation (will return only one if there are multiple!)"""
        return self.annotation(LemmaAnnotation,set).cls

    def sense(self,set=None):
        """Shortcut: returns the FoLiA class of the sense annotation (will return only one if there are multiple!)"""
        return self.annotation(SenseAnnotation,set).cls

    def domain(self,set=None):
        """Shortcut: returns the FoLiA class of the domain annotation (will return only one if there are multiple!)"""
        return self.annotation(DomainAnnotation,set).cls

    def morphemes(self,set=None):
        """Generator yielding all morphemes (in a particular set if specified). For retrieving one specific morpheme by index, use morpheme() instead"""
        for layer in self.select(MorphologyLayer):
            for m in layer.select(Morpheme, set):
                yield m

    def morpheme(self,index, set=None):
        """Returns a specific morpheme, the n'th morpheme (given the particular set if specified)."""
        for layer in self.select(MorphologyLayer):
            for i, m in enumerate(layer.select(Morpheme, set)):
                if index == i:
                    return m
        raise NoSuchAnnotation



    def gettextdelimiter(self, retaintokenisation=False):
        """Returns the text delimiter"""
        if self.space or retaintokenisation:
            return ' '
        else:
            return ''

    def resolveword(self, id):
        if id == self.id:
            return self
        else:
            return None

    def getcorrection(self,set=None,cls=None):
        try:
            return self.getcorrections(set,cls)[0]
        except:
            raise NoSuchAnnotation

    def getcorrections(self, set=None,cls=None):
        try:
            l = []
            for correction in self.annotations(Correction):
                if ((not set or correction.set == set) and (not cls or correction.cls == cls)):
                    l.append(correction)
            return l
        except NoSuchAnnotation:
            raise

    @classmethod
    def parsexml(Class, node, doc):
        assert Class is Word
        global NSFOLIA
        instance = super(Word,Class).parsexml(node, doc)
        if 'space' in node.attrib:
            if node.attrib['space'] == 'no':
                instance.space = False
        return instance


    def xml(self, attribs = None,elements = None, skipchildren = False):
        if not attribs: attribs = {}
        if not self.space:
            attribs['space'] = 'no'
        return super(Word,self).xml(attribs,elements, False)

    def json(self,attribs =None, recurse=True):
        if not attribs: attribs = {}
        if not self.space:
            attribs['space'] = 'no'
        return super(Word,self).json(attribs, recurse)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        global NSFOLIA
        E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace"})
        if not extraattribs:
            extraattribs = [ E.optional(E.attribute(name='space')) ]
        else:
            extraattribs.append( E.optional(E.attribute(name='space')) )
        return AbstractStructureElement.relaxng(includechildren, extraattribs, extraelements, cls)



    def split(self, *newwords, **kwargs):
        self.sentence().splitword(self, *newwords, **kwargs)


    def next(self):
        """Returns the next word in the sentence, or None if no next word was found. This method does not cross sentence boundaries."""
        words = self.sentence().words()
        i = words.index(self) + 1
        if i < len(words):
            return words[i]
        else:
            return None


    def previous(self):
        """Returns the previous word in the sentence, or None if no next word was found. This method does not cross sentence boundaries."""
        words = self.sentence().words()
        i = words.index(self) - 1
        if i >= 0:
            return words[i]
        else:
            return None

    def leftcontext(self, size, placeholder=None):
        """Returns the left context for a word. This method crosses sentence/paragraph boundaries"""
        if size == 0: return [] #for efficiency
        words = self.doc.words()
        i = words.index(self)
        begin = i - size
        if begin < 0:
            return [placeholder] * (begin * -1) + words[0:i]
        else:
            return words[begin:i]

    def rightcontext(self, size, placeholder=None):
        """Returns the right context for a word. This method crosses sentence/paragraph boundaries"""
        if size == 0: return [] #for efficiency
        words = self.doc.words()
        i = words.index(self)
        begin = i+1
        end = begin + size
        rightcontext = words[begin:end]
        if len(rightcontext) < size:
            rightcontext += (size - len(rightcontext)) * [placeholder]
        return rightcontext


    def context(self, size, placeholder=None):
        """Returns this word in context, {size} words to the left, the current word, and {size} words to the right"""
        return self.leftcontext(size, placeholder) + [self] + self.rightcontext(size, placeholder)

    def findspans(self, type,set=None):
        """Find span annotation of the specified type that include this word"""
        assert issubclass(type, AbstractAnnotationLayer)
        l = []
        e = self
        while True:
            if not e.parent: break
            e = e.parent
            for layer in e.select(type,set,False):
                for e2 in layer:
                    if isinstance(e2, AbstractSpanAnnotation):
                        if self in e2.wrefs():
                            l.append(e2)
        return l


class Feature(AbstractElement):
    """Feature elements can be used to associate subsets and subclasses with almost any
    annotation element"""

    OCCURRENCESPERSET = 0 #unlimited
    XMLTAG = 'feat'
    SUBSET = None

    def __init__(self,doc, *args, **kwargs):
        """Required keyword arguments:

           * ``subset=``: the subset
           * ``cls=``: the class
        """

        self.id = None
        self.set = None
        self.data = []
        self.annotator = None
        self.annotatortype = None
        self.confidence = None
        self.n = None
        self.datetime = None
        if not isinstance(doc, Document) and not (doc is None):
            raise Exception("First argument of Feature constructor must be a Document instance, not " + str(type(doc)))
        self.doc = doc


        if self.SUBSET:
            self.subset = self.SUBSET
        elif 'subset' in kwargs:
            self.subset = kwargs['subset']
        else:
            raise Exception("No subset specified for " + + self.__class__.__name__)
        if 'cls' in kwargs:
            self.cls = kwargs['cls']
        elif 'class' in kwargs:
            self.cls = kwargs['class']
        else:
            raise Exception("No class specified for " + self.__class__.__name__)

        if isinstance(self.cls, datetime):
            self.cls = self.cls.strftime("%Y-%m-%dT%H:%M:%S")

    def xml(self):
        global NSFOLIA
        E = ElementMaker(namespace=NSFOLIA,nsmap={None: NSFOLIA, 'xml' : "http://www.w3.org/XML/1998/namespace"})
        attribs = {}
        if self.subset != self.SUBSET:
            attribs['{' + NSFOLIA + '}subset'] = self.subset
        attribs['{' + NSFOLIA + '}class'] =  self.cls
        return makeelement(E,'{' + NSFOLIA + '}' + self.XMLTAG, **attribs)

    def json(self,attribs=None, recurse=True):
        jsonnode= {'type': self.XMLTAG}
        jsonnode['subset'] = self.subset
        jsonnode['class'] = self.cls
        return jsonnode

    @classmethod
    def relaxng(cls, includechildren=True, extraattribs = None, extraelements=None):
        global NSFOLIA
        E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace"})
        return E.define( E.element(E.attribute(name='subset'), E.attribute(name='class'),name=cls.XMLTAG), name=cls.XMLTAG,ns=NSFOLIA)


class ValueFeature(Feature):
    """Value feature, to be used within Metric"""
    #XMLTAG = 'synset'
    XMLTAG = None
    SUBSET = 'value' #associated subset

class Metric(AbstractElement):
    """Metric elements allow the annotatation of any kind of metric with any kind of annotation element. Allowing for example statistical measures to be added to elements as annotation,"""
    XMLTAG = 'metric'
    ANNOTATIONTYPE = AnnotationType.METRIC
    REQUIRED_ATTRIB = (Attrib.CLASS,)
    OPTIONAL_ATTRIBS = Attrib.ALL
    ACCEPTED_DATA = (Feature, ValueFeature, Description)

class AbstractSubtokenAnnotation(AbstractAnnotation, AllowGenerateID):
    """Abstract element, all subtoken annotation elements are derived from this class"""

    REQUIRED_ATTRIBS = ()
    OPTIONAL_ATTRIBS = Attrib.ALL
    OCCURRENCESPERSET = 0 #Allow duplicates within the same set
    PRINTABLE = True

class AbstractSpanAnnotation(AbstractAnnotation, AllowGenerateID):
    """Abstract element, all span annotation elements are derived from this class"""

    REQUIRED_ATTRIBS = ()
    OPTIONAL_ATTRIBS = Attrib.ALL
    OCCURRENCESPERSET = 0 #Allow duplicates within the same set
    PRINTABLE = True


    def xml(self, attribs = None,elements = None, skipchildren = False):
        global NSFOLIA
        if not attribs: attribs = {}
        E = ElementMaker(namespace="http://ilk.uvt.nl/folia",nsmap={None: "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace"})
        e = super(AbstractSpanAnnotation,self).xml(attribs, elements, True)
        for child in self:
            if isinstance(child, Word) or isinstance(child, Morpheme):
                #Include REFERENCES to word items instead of word items themselves
                attribs['{' + NSFOLIA + '}id'] = child.id
                if child.text:
                    attribs['{' + NSFOLIA + '}t'] = child.text()
                e.append( E.wref(**attribs) )
            elif not (isinstance(child, Feature) and child.SUBSET): #Don't add pre-defined features, they are already added as attributes
                e.append( child.xml() )
        return e



    def append(self, child, *args, **kwargs):
        if (isinstance(child, Word) or isinstance(child, Morpheme))  and WordReference in self.ACCEPTED_DATA:
            #Accept Word instances instead of WordReference, references will be automagically used upon serialisation
            self.data.append(child)
            return child
        else:
            return super(AbstractSpanAnnotation,self).append(child, *args, **kwargs)

    def hasannotation(self,Class,set=None):
        """Returns an integer indicating whether such as annotation exists, and if so, how many. See ``annotations()`` for a description of the parameters."""
        l = self.select(Class,set,True,defaultignorelist_annotations)
        return len(l)

    def annotation(self, type, set=None):
        """Will return a **single** annotation (even if there are multiple). Raises a ``NoSuchAnnotation`` exception if none was found"""
        l = self.select(type,set,True,defaultignorelist_annotations)
        if len(l) >= 1:
            return l[0]
        else:
            raise NoSuchAnnotation()

    def _helper_wrefs(self, targets):
        """Internal helper function"""
        for c in self:
            if isinstance(c,Word) or isinstance(c,Morpheme): #TODO: add phoneme when it becomes available
                targets.append(c)
            elif isinstance(c, AbstractSpanAnnotation):
                c._helper_wrefs(targets)

    def wrefs(self, index = None):
        """Returns a list of word references, these can be Words but also Morphemes or Phonemes.

        Arguments:
            * ``index``: If set to an integer, will retrieve and return the n'th element (starting at 0) instead of returning the list of all
        """
        targets =[]
        self._helper_wrefs(targets)
        if index is None:
            return targets
        else:
            return targets[index]



class AbstractAnnotationLayer(AbstractElement, AllowGenerateID):
    """Annotation layers for Span Annotation are derived from this abstract base class"""
    OPTIONAL_ATTRIBS = (Attrib.SETONLY,)
    PRINTABLE = False
    ROOTELEMENT = False #only annotation elements are considered

    def __init__(self, doc, *args, **kwargs):
        if 'set' in kwargs:
            self.set = kwargs['set']
        elif self.ANNOTATIONTYPE in doc.annotationdefaults and len(doc.annotationdefaults[self.ANNOTATIONTYPE]) == 1:
            self.set = list(doc.annotationdefaults[self.ANNOTATIONTYPE].keys())[0]
        else:
            self.set = False
            # ok, let's not raise an error yet, may may still be able to derive a set from elements that are appended
        super(AbstractAnnotationLayer,self).__init__(doc, *args, **kwargs)


    def xml(self, attribs = None,elements = None, skipchildren = False):
        if self.set is False or self.set is None:
            if len(self.data) == 0: #just skip if there are no children
                return ""
            else:
                raise ValueError("No set specified or derivable for annotation layer " + self.__class__.__name__)
        return super(AbstractAnnotationLayer, self).xml(attribs, elements, skipchildren)

    def append(self, child, *args, **kwargs):
        if self.set is False or self.set is None:
            if inspect.isclass(child):
                if 'set' in kwargs:
                    self.set = kwargs['set']
            elif isinstance(child, AbstractElement):
                if child.set:
                    self.set = child.set
            #print "DEBUG AFTER APPEND: set=", self.set
        return super(AbstractAnnotationLayer, self).append(child, *args, **kwargs)

    def annotations(self,Class,set=None):
        """Obtain annotations. Very similar to ``select()`` but raises an error if the annotation was not found.

        Arguments:
            * ``Class`` - The Class you want to retrieve (e.g. PosAnnotation)
            * ``set``   - The set you want to retrieve (defaults to None, which selects irregardless of set)

        Returns:
            A list of elements

        Raises:
            ``NoSuchAnnotation`` if the specified annotation does not exist.
        """
        l = self.select(Class,set,True,defaultignorelist_annotations)
        if not l:
            raise NoSuchAnnotation()
        else:
            return l

    def hasannotation(self,Class,set=None):
        """Returns an integer indicating whether such as annotation exists, and if so, how many. See ``annotations()`` for a description of the parameters."""
        l = self.select(Class,set,True,defaultignorelist_annotations)
        return len(l)

    def annotation(self, type, set=None):
        """Will return a **single** annotation (even if there are multiple). Raises a ``NoSuchAnnotation`` exception if none was found"""
        l = self.select(type,set,True,defaultignorelist_annotations)
        if len(l) >= 1:
            return l[0]
        else:
            raise NoSuchAnnotation()

    def alternatives(self, Class=None, set=None):
        """Obtain a list of alternatives, either all or only of a specific annotation type, and possibly restrained also by set.

        Arguments:
            * ``Class`` - The Class you want to retrieve (e.g. PosAnnotation). Or set to None to select all alternatives regardless of what type they are.
            * ``set``   - The set you want to retrieve (defaults to None, which selects irregardless of set)

        Returns:
            List of Alternative elements
        """
        l = []

        for e in self.select(AlternativeLayers,None, True, ['Original','Suggestion']):
            if Class is None:
                l.append(e)
            elif len(e) >= 1: #child elements?
                for e2 in e:
                    try:
                        if isinstance(e2, Class):
                            try:
                                if set is None or e2.set == set:
                                    found = True
                                    l.append(e) #not e2
                                    break #yield an alternative only once (in case there are multiple matches)
                            except AttributeError:
                                continue
                    except AttributeError:
                        continue
        return l

    def findspan(self, *words):
        """Returns the span element which spans over the specified words or morphemes"""

        for span in self.select(AbstractSpanAnnotation,None,True):
            if tuple(span.wrefs()) == words:
               return span
        raise NoSuchAnnotation

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None, origclass = None):
        """Returns a RelaxNG definition for this element (as an XML element (lxml.etree) rather than a string)"""

        global NSFOLIA
        E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace",'a':"http://relaxng.org/ns/annotation/0.9" })
        if not extraattribs:
            extraattribs = []
        extraattribs.append(E.optional(E.attribute(E.text(), name='set')) )
        return AbstractElement.relaxng(includechildren, extraattribs, extraelements, cls)

# class AbstractSubtokenAnnotationLayer(AbstractElement, AllowGenerateID):
    # """Annotation layers for Subtoken Annotation are derived from this abstract base class"""
    # OPTIONAL_ATTRIBS = ()
    # PRINTABLE = False

    # def __init__(self, doc, *args, **kwargs):
        # if 'set' in kwargs:
            # self.set = kwargs['set']
            # del kwargs['set']
        # super(AbstractSubtokenAnnotationLayer,self).__init__(doc, *args, **kwargs)



class String(AbstractElement, AllowTokenAnnotation):
   """String"""
   #ACCEPTED_DATA = DEFINED LATER!!
   XMLTAG = 'str'
   REQUIRED_ATTRIBS = ()
   OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.CLASS,Attrib.ANNOTATOR,Attrib.CONFIDENCE, Attrib.DATETIME)
   ANNOTATIONTYPE = AnnotationType.STRING
   OCCURRENCES = 0 #Number of times this element may occur in its parent (0=unlimited)
   OCCURRENCESPERSET = 0 #Number of times this element may occur per set (0=unlimited)
   PRINTABLE = True

class AbstractCorrectionChild(AbstractElement):
    OPTIONAL_ATTRIBS = (Attrib.ANNOTATOR,Attrib.CONFIDENCE,Attrib.DATETIME,Attrib.N)
    ACCEPTED_DATA = (AbstractTokenAnnotation, Word, TextContent, String, Description, Metric)
    TEXTDELIMITER = None
    PRINTABLE = True
    ROOTELEMENT = False


class Reference(AbstractStructureElement):
    ACCEPTED_DATA = (TextContent, String, Description, Metric)
    REQUIRED_ATTRIBS = ()
    OPTIONAL_ATTRIBS = (Attrib.ID, Attrib.ANNOTATOR,Attrib.CONFIDENCE, Attrib.DATETIME)
    PRINTABLE = True
    XMLTAG = 'ref'

    def __init__(self, doc, *args, **kwargs):
        if 'idref' in kwargs:
            self.idref = kwargs['idref']
            del kwargs['idref']
        else:
            self.idref = None
        if 'type' in kwargs:
            self.type = kwargs['type']
            del kwargs['type']
        else:
            self.type = None
        super(Reference,self).__init__(doc, *args, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False):
        if not attribs: attribs = {}
        if self.idref:
            attribs['id'] = self.idref
        if self.type:
            attribs['type'] = self.type
        return super(Reference,self).xml(attribs,elements, skipchildren)

    def resolve(self):
        if self.idref:
            return self.doc[self.idref]
        else:
            return self

    @classmethod
    def parsexml(Class, node, doc):
        global NSFOLIA
        if 'id' in node.attrib:
            idref = node.attrib['id']
            del node.attrib['id']
        else:
            idref = None
        if 'type' in node.attrib:
            t = node.attrib['type']
            del node.attrib['type']
        else:
            idref = None
        instance = super(Reference,Class).parsexml(node, doc)
        if idref:
            instance.idref = idref
        if t:
            instance.type =  t
        return instance


    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        global NSFOLIA
        E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace",'a':"http://relaxng.org/ns/annotation/0.9" })
        if not extraattribs: extraattribs = []
        extraattribs.append( E.attribute(name='id'))
        extraattribs.append( E.optional(E.attribute(name='type' ))) #id reference
        return super(Reference, cls).relaxng(includechildren, extraattribs, extraelements)

class AlignReference(AbstractElement):
    REQUIRED_ATTRIBS = (Attrib.ID,)
    XMLTAG = 'aref'

    def __init__(self, doc, *args, **kwargs):
        #Special constructor, not calling super constructor
        if not 'id' in kwargs:
            raise Exception("ID required for AlignReference")
        if not 'type' in kwargs:
            raise Exception("Type required for AlignReference")
        elif not inspect.isclass(kwargs['type']):
            raise Exception("Type must be a FoLiA element (python class)")
        self.type = kwargs['type']
        if 't' in kwargs:
            self.t = kwargs['t']
        else:
            self.t = None
        assert(isinstance(doc,Document))
        self.doc = doc
        self.id = kwargs['id']
        self.annotator = None
        self.annotatortype = None
        self.confidence = None
        self.n = None
        self.datetime = None
        self.auth = False
        self.set = None
        self.cls = None
        self.data = []

        if 'href' in kwargs:
            self.href = kwargs['href']
        else:
            self.href = None

    @classmethod
    def parsexml(Class, node, doc):
        global NSFOLIA
        assert Class is AlignReference or issubclass(Class, AlignReference)

        #special handling for word references
        id = node.attrib['id']
        if not 'type' in node.attrib:
            raise ValueError("No type in alignment reference")
        try:
            type = XML2CLASS[node.attrib['type']]
        except KeyError:
            raise ValueError("No such type: " + node.attrib['type'])
        return AlignReference(doc, id=id, type=type)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
            global NSFOLIA
            E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace"})
            return E.define( E.element(E.attribute(E.text(), name='id'), E.optional(E.attribute(E.text(), name='t')), E.attribute(E.text(), name='type'), name=cls.XMLTAG), name=cls.XMLTAG, ns=NSFOLIA)

    def resolve(self, alignmentcontext):
        if not alignmentcontext.href:
            #no target document, same document
            return self.doc[self.id]
        else:
            raise NotImplementedError

    def xml(self, attribs = None,elements = None, skipchildren = False):
        global NSFOLIA
        E = ElementMaker(namespace=NSFOLIA,nsmap={None: NSFOLIA, 'xml' : "http://www.w3.org/XML/1998/namespace"})

        if not attribs:
            attribs = {}
        attribs['id'] = self.id
        attribs['type'] = self.type.XMLTAG
        if self.t: attribs['t'] = self.t

        return E.aref( **attribs)

    def json(self, attribs=None, recurse=True):
        return {} #alignment not supported yet, TODO

class Alignment(AbstractElement):
    REQUIRED_ATTRIBS = ()
    OPTIONAL_ATTRIBS = Attrib.ALL
    OCCURRENCESPERSET = 0 #Allow duplicates within the same set (0= unlimited)
    XMLTAG = 'alignment'
    ANNOTATIONTYPE = AnnotationType.ALIGNMENT
    ACCEPTED_DATA = (AlignReference, Description, Metric)
    PRINTABLE = False

    def __init__(self, doc, *args, **kwargs):
        if 'href' in kwargs:
            self.href =kwargs['href']
            del kwargs['href']
        else:
            self.href = None
        super(Alignment,self).__init__(doc, *args, **kwargs)

    @classmethod
    def parsexml(Class, node, doc):
        global NSFOLIA
        assert Class is Alignment or issubclass(Class, Alignment)

        instance = super(Alignment,Class).parsexml(node, doc)

        if '{http://www.w3.org/1999/xlink}href' in node.attrib:
            instance.href = node.attrib['{http://www.w3.org/1999/xlink}href']
        else:
            instance.href = None

        return instance

    def xml(self, attribs = None,elements = None, skipchildren = False):
        if not attribs: attribs = {}
        if self.href:
            attribs['{http://www.w3.org/1999/xlink}href'] = self.href
            attribs['{http://www.w3.org/1999/xlink}type'] = 'simple'
        return super(Alignment,self).xml(attribs,elements, False)

    def json(self, attribs =None):
        return {} #alignment not supported yet, TODO

    def resolve(self):
        l = []
        for x in self.select(AlignReference,None,True,False):
            l.append( x.resolve(self) )
        return l




class ErrorDetection(AbstractExtendedTokenAnnotation):
    ANNOTATIONTYPE = AnnotationType.ERRORDETECTION
    XMLTAG = 'errordetection'
    OCCURRENCESPERSET = 0 #Allow duplicates within the same set (0= unlimited)
    ROOTELEMENT = True



class Suggestion(AbstractCorrectionChild):
    ANNOTATIONTYPE = AnnotationType.SUGGESTION
    XMLTAG = 'suggestion'
    OCCURRENCES = 0 #unlimited
    OCCURRENCESPERSET = 0 #Allow duplicates within the same set (0= unlimited)
    AUTH = False


class New(AbstractCorrectionChild):
    REQUIRED_ATTRIBS = (),
    OPTIONAL_ATTRIBS = (),
    OCCURRENCES = 1
    XMLTAG = 'new'


    @classmethod
    def addable(Class, parent, set=None, raiseexceptions=True):
        if not super(New,Class).addable(parent,set,raiseexceptions): return False
        if any( ( isinstance(c, Current) for c in parent ) ):
            if raiseexceptions:
                raise ValueError("Can't add New element to Correction if there is a Current item")
            else:
                return False
        return True

class Original(AbstractCorrectionChild):
    REQUIRED_ATTRIBS = (),
    OPTIONAL_ATTRIBS = (),
    OCCURRENCES = 1
    XMLTAG = 'original'
    AUTH = False

    @classmethod
    def addable(Class, parent, set=None, raiseexceptions=True):
        if not super(Original,Class).addable(parent,set,raiseexceptions): return False
        if any( ( isinstance(c, Current)  for c in parent ) ):
             if raiseexceptions:
                raise Exception("Can't add Original item to Correction if there is a Current item")
             else:
                return False
        return True


class Current(AbstractCorrectionChild):
    REQUIRED_ATTRIBS = (),
    OPTIONAL_ATTRIBS = (),
    OCCURRENCES = 1
    XMLTAG = 'current'

    @classmethod
    def addable(Class, parent, set=None, raiseexceptions=True):
        if not super(Current,Class).addable(parent,set,raiseexceptions): return False
        if any( ( isinstance(c, New) or isinstance(c, Original) for c in parent ) ):
            if raiseexceptions:
                raise Exception("Can't add Current element to Correction if there is a New or Original element")
            else:
                return False
        return True

class Correction(AbstractExtendedTokenAnnotation):
    REQUIRED_ATTRIBS = ()
    ACCEPTED_DATA = (New,Original,Current, Suggestion, Description, Metric)
    ANNOTATIONTYPE = AnnotationType.CORRECTION
    XMLTAG = 'correction'
    OCCURRENCESPERSET = 0 #Allow duplicates within the same set (0= unlimited)
    TEXTDELIMITER = None
    PRINTABLE = True
    ROOTELEMENT = True

    def hasnew(self):
        return bool(self.select(New,None,False, False))

    def hasoriginal(self):
        return bool(self.select(Original,None,False, False))

    def hascurrent(self):
        return bool(self.select(Current,None,False, False))

    def hassuggestions(self):
        return bool(self.select(Suggestion,None,False, False))

    def textcontent(self, cls='current'):
        """Get the text explicitly associated with this element (of the specified class).
        Returns the TextContent instance rather than the actual text. Raises NoSuchText exception if
        not found.

        Unlike text(), this method does not recurse into child elements (with the sole exception of the Correction/New element), and it returns the TextContent instance rather than the actual text!
        """
        if cls == 'current':
            for e in self:
                if isinstance(e, New) or isinstance(e, Current):
                    return e.textcontent(cls)
        elif cls == 'original':
            for e in self:
                if isinstance(e, Original):
                    return e.textcontent(cls)
        raise NoSuchText



    def text(self, cls = 'current', retaintokenisation=False, previousdelimiter=""):
        if cls == 'current':
            for e in self:
                if isinstance(e, New) or isinstance(e, Current):
                    return previousdelimiter + e.text(cls, retaintokenisation)
        elif cls == 'original':
            for e in self:
                if isinstance(e, Original):
                    return previousdelimiter + e.text(cls, retaintokenisation)
        raise NoSuchText

    def gettextdelimiter(self, retaintokenisation=False):
        """May return a customised text delimiter instead of the default for this class."""
        for e in self:
            if isinstance(e, New) or isinstance(e, Current):
                d =  e.gettextdelimiter(retaintokenisation)
                return d
        return ""


    def new(self,index = None):
        if index is None:
            try:
                return self.select(New,None,False)[0]
            except IndexError:
                raise NoSuchAnnotation
        else:
            l = self.select(New,None,False)
            if len(l) == 0:
                raise NoSuchAnnotation
            else:
                return l[0][index]

    def original(self,index=None):
        if index is None:
            try:
                return self.select(Original,None,False, False)[0]
            except IndexError:
                raise NoSuchAnnotation
        else:
            l = self.select(Original,None,False, False)
            if len(l) == 0:
                raise NoSuchAnnotation
            else:
                return l[0][index]

    def current(self,index=None):
        if index is None:
            try:
                return self.select(Current,None,False)[0]
            except IndexError:
                raise NoSuchAnnotation
        else:
            l =  self.select(Current,None,False)
            if len(l) == 0:
                raise NoSuchAnnotation
            else:
                return l[0][index]

    def suggestions(self,index=None):
        if index is None:
            return self.select(Suggestion,None,False, False)
        else:
            return self.select(Suggestion,None,False, False)[index]


    def __unicode__(self):
        return str(self)

    def __str__(self):
        for e in self:
            if isinstance(e, New) or isinstance(e, Current):
                return str(e)


    #obsolete
    #def select(self, cls, set=None, recursive=True,  ignorelist=[], node=None):
    #    """Select on Correction only descends in either "NEW" or "CURRENT" branch"""
    #    if ignorelist is False:
    #        #to override and go into all branches, set ignorelist explictly to False
    #        return super(Correction,self).select(cls,set,recursive, ignorelist, node)
    #    else:
    #        if ignorelist is True:
    #            ignorelist = copy(defaultignorelist)
    #        else:
    #            ignorelist = copy(ignorelist) #we don't want to alter a passed ignorelist (by ref)
    #        ignorelist.append(Original)
    #        ignorelist.append(Suggestion)
    #        return super(Correction,self).select(cls,set,recursive, ignorelist, node)

Original.ACCEPTED_DATA = (AbstractTokenAnnotation, Word, TextContent,String, Correction, Description, Metric)



String.ACCEPTED_DATA = (TextContent,Alignment,Description, Metric, Correction, AbstractExtendedTokenAnnotation)

class Alternative(AbstractElement, AllowTokenAnnotation, AllowGenerateID):
    """Element grouping alternative token annotation(s). Multiple alternative elements may occur, each denoting a different alternative. Elements grouped inside an alternative block are considered dependent."""
    REQUIRED_ATTRIBS = ()
    OPTIONAL_ATTRIBS = Attrib.ALL
    ACCEPTED_DATA = [AbstractTokenAnnotation, Correction] #adding MorphlogyLayer later
    ANNOTATIONTYPE = AnnotationType.ALTERNATIVE
    XMLTAG = 'alt'
    PRINTABLE = False
    AUTH = False



class AlternativeLayers(AbstractElement):
    """Element grouping alternative subtoken annotation(s). Multiple altlayers elements may occur, each denoting a different alternative. Elements grouped inside an alternative block are considered dependent."""
    REQUIRED_ATTRIBS = ()
    OPTIONAL_ATTRIBS = Attrib.ALL
    ACCEPTED_DATA = (AbstractAnnotationLayer,)
    XMLTAG = 'altlayers'
    PRINTABLE = False
    AUTH = False

Word.ACCEPTED_DATA = (AbstractTokenAnnotation, TextContent,String, Alternative, AlternativeLayers, Description, AbstractAnnotationLayer, Alignment, Metric, Reference)


class External(AbstractElement):
    REQUIRED_ATTRIBS = ()
    OPTIONAL_ATTRIBS = ()
    ACCEPTED_DATA = []
    XMLTAG = 'external'
    PRINTABLE = True
    AUTH = True


    def __init__(self, doc, *args, **kwargs):
        #Special constructor, not calling super constructor
        if not 'source' in kwargs:
            raise Exception("Source required for External")
        assert(isinstance(doc,Document))
        self.doc = doc
        self.id = None
        self.source = kwargs['source']
        if 'include' in kwargs and kwargs['include'] != 'no':
            self.include = bool(kwargs['include'])
        else:
            self.include = False
        self.annotator = None
        self.annotatortype = None
        self.confidence = None
        self.n = None
        self.datetime = None
        self.auth = False
        self.data = []
        self.subdoc = None

        if self.include:
            if doc.debug >= 1: print("[PyNLPl FoLiA DEBUG] Loading subdocument for inclusion: " + self.source,file=stderr)
            #load subdocument

            #check if it is already loaded, if multiple references are made to the same doc we reuse the instance
            if self.source in self.doc.subdocs:
                self.subdoc = self.doc.subdocs[self.source]
            elif self.source[:7] == 'http://' or self.source[:8] == 'https://':
                #document is remote, download (in memory)
                try:
                    f = urlopen(self.source)
                except:
                    raise DeepValidationError("Unable to download subdocument for inclusion: " + self.source)
                try:
                    content = u(f.read())
                except IOError:
                    raise DeepValidationError("Unable to download subdocument for inclusion: " + self.source)
                f.close()
                self.subdoc = Document(string=content, parentdoc = self.doc, setdefinitions=self.doc.setdefinitions)
            elif os.path.exists(self.source):
                #document is on disk:
                self.subdoc = Document(file=self.source, parentdoc = self.doc, setdefinitions=self.doc.setdefinitions)
            else:
                #document not found
                raise DeepValidationError("Unable to find subdocument for inclusion: " + self.source)

            self.subdoc.parentdoc = self.doc
            self.doc.subdocs[self.source] = self.subdoc
            #TODO: verify there are no clashes in declarations between parent and child
            #TODO: check validity of elements under subdoc/text with respect to self.parent


    @classmethod
    def parsexml(Class, node, doc):
        global NSFOLIA
        assert Class is External or issubclass(Class, External)
        #special handling for external
        source = node.attrib['src']
        if 'include' in node.attrib:
            include = node.attrib['include']
        else:
            include = False
        if doc.debug >= 1: print("[PyNLPl FoLiA DEBUG] Found external",file=stderr)
        return External(doc, source=source, include=include)

    def xml(self, attribs = None,elements = None, skipchildren = False):
        if not attribs:
            attribs= {}

        attribs['src'] = self.source

        if self.include:
            attribs['include']  = 'yes'
        else:
            attribs['include']  = 'no'

        return super(External, self).xml(attribs, elements, skipchildren)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        global NSFOLIA
        E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace"})
        return E.define( E.element(E.attribute(E.text(), name='src'), E.optional(E.attribute(E.text(), name='include')), name=cls.XMLTAG), name=cls.XMLTAG, ns=NSFOLIA)


    def select(self, Class, set=None, recursive=True,  ignore=True, node=None):
        if self.include:
            return self.subdoc.data[0].select(Class,set,recursive, ignore, node) #pass it on to the text node of the subdoc
        else:
            return []


class WordReference(AbstractElement):
    """Word reference. Use to refer to words or morphemes from span annotation elements. The Python class will only be used when word reference can not be resolved, if they can, Word or Morpheme objects will be used"""
    REQUIRED_ATTRIBS = (Attrib.ID,)
    XMLTAG = 'wref'
    #ANNOTATIONTYPE = AnnotationType.TOKEN

    def __init__(self, doc, *args, **kwargs):
        #Special constructor, not calling super constructor
        if not 'idref' in kwargs and not 'id' in kwargs:
            raise Exception("ID required for WordReference")
        assert(isinstance(doc,Document))
        self.doc = doc
        if 'idref' in kwargs:
            self.id = kwargs['idref']
        else:
            self.id = kwargs['id']
        self.annotator = None
        self.annotatortype = None
        self.confidence = None
        self.n = None
        self.datetime = None
        self.auth = False
        self.data = []

    @classmethod
    def parsexml(Class, node, doc):
        global NSFOLIA
        assert Class is WordReference or issubclass(Class, WordReference)
        #special handling for word references
        id = node.attrib['id']
        if doc.debug >= 1: print("[PyNLPl FoLiA DEBUG] Found word reference",file=stderr)
        try:
            return doc[id]
        except KeyError:
            if doc.debug >= 1: print("[PyNLPl FoLiA DEBUG] ...Unresolvable!",file=stderr)
            return WordReference(doc, id=id)

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
            global NSFOLIA
            E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace"})
            return E.define( E.element(E.attribute(E.text(), name='id'), E.optional(E.attribute(E.text(), name='t')), name=cls.XMLTAG), name=cls.XMLTAG, ns=NSFOLIA)



class SyntacticUnit(AbstractSpanAnnotation):
    """Syntactic Unit, span annotation element to be used in SyntaxLayer"""
    REQUIRED_ATTRIBS = ()
    ANNOTATIONTYPE = AnnotationType.SYNTAX
    XMLTAG = 'su'

SyntacticUnit.ACCEPTED_DATA = (SyntacticUnit,WordReference, Description, Feature, Metric)

class Chunk(AbstractSpanAnnotation):
    """Chunk element, span annotation element to be used in ChunkingLayer"""
    REQUIRED_ATTRIBS = ()
    ACCEPTED_DATA = (WordReference, Description, Feature, Metric)
    ANNOTATIONTYPE = AnnotationType.CHUNKING
    XMLTAG = 'chunk'

class Entity(AbstractSpanAnnotation):
    """Entity element, for named entities, span annotation element to be used in EntitiesLayer"""
    REQUIRED_ATTRIBS = ()
    ACCEPTED_DATA = (WordReference, Description, Feature, Metric)
    ANNOTATIONTYPE = AnnotationType.ENTITY
    XMLTAG = 'entity'




class Headspan(AbstractSpanAnnotation): #generic head element
    REQUIRED_ATTRIBS = ()
    OPTIONAL_ATTRIBS = ()
    ACCEPTED_DATA = (WordReference,Description, Feature, Alignment, Metric)
    #ANNOTATIONTYPE = AnnotationType.DEPENDENCY
    XMLTAG = 'hd'
    ROOTELEMENT = False

DependencyHead = Headspan #alias, backwards compatibility with FoLiA 0.8


class DependencyDependent(AbstractSpanAnnotation):
    REQUIRED_ATTRIBS = ()
    OPTIONAL_ATTRIBS = ()
    ACCEPTED_DATA = (WordReference,Description, Feature, Alignment, Metric)
    ANNOTATIONTYPE = AnnotationType.DEPENDENCY
    XMLTAG = 'dep'
    ROOTELEMENT = False

class Dependency(AbstractSpanAnnotation):
    REQUIRED_ATTRIBS = ()
    ACCEPTED_DATA = (Description, Feature,Headspan, DependencyDependent, Alignment, Metric)
    ANNOTATIONTYPE = AnnotationType.DEPENDENCY
    XMLTAG = 'dependency'

    def head(self):
        """Returns the head of the dependency relation. Instance of DependencyHead"""
        return self.select(DependencyHead)[0]

    def dependent(self):
        """Returns the dependent of the dependency relation. Instance of DependencyDependent"""
        return self.select(DependencyDependent)[0]


class ModalityFeature(Feature):
    """Modality feature, to be used with coreferences"""
    SUBSET = 'modality' #associated subset
    XMLTAG = None

class TimeFeature(Feature):
    """Time feature, to be used with coreferences"""
    SUBSET = 'time' #associated subset
    XMLTAG = None

class LevelFeature(Feature):
    """Level feature, to be used with coreferences"""
    SUBSET = 'level' #associated subset
    XMLTAG = None

class CoreferenceLink(AbstractSpanAnnotation):
    """Coreference link. Used in coreferencechain."""
    REQUIRED_ATTRIBS = ()
    OPTIONAL_ATTRIBS = (Attrib.ANNOTATOR, Attrib.N, Attrib.DATETIME)
    ACCEPTED_DATA = (WordReference, Description, Headspan, Alignment, ModalityFeature, TimeFeature,LevelFeature, Metric)
    ANNOTATIONTYPE = AnnotationType.COREFERENCE
    XMLTAG = 'coreferencelink'
    ROOTELEMENT = False

class CoreferenceChain(AbstractSpanAnnotation):
    """Coreference chain. Consists of coreference links."""
    REQUIRED_ATTRIBS = ()
    ACCEPTED_DATA = (CoreferenceLink,Description, Metric)
    ANNOTATIONTYPE = AnnotationType.COREFERENCE
    XMLTAG = 'coreferencechain'

class SemanticRole(AbstractSpanAnnotation):
    """Semantic Role"""
    REQUIRED_ATTRIBS = (Attrib.CLASS,)
    ACCEPTED_DATA = (WordReference, Description, Headspan, Alignment, Metric)
    ANNOTATIONTYPE = AnnotationType.SEMROLE
    XMLTAG = 'semrole'

class FunctionFeature(Feature):
    """Function feature, to be used with morphemes"""
    SUBSET = 'function' #associated subset
    XMLTAG = None

class Morpheme(AbstractStructureElement):
    """Morpheme element, represents one morpheme in morphological analysis, subtoken annotation element to be used in MorphologyLayer"""
    REQUIRED_ATTRIBS = (),
    OPTIONAL_ATTRIBS = Attrib.ALL
    ACCEPTED_DATA = (FunctionFeature, Feature,TextContent, String,Metric, Alignment, AbstractTokenAnnotation, Description)
    ANNOTATIONTYPE = AnnotationType.MORPHOLOGICAL
    XMLTAG = 'morpheme'



#class Subentity(AbstractSubtokenAnnotation):
#    """Subentity element, for named entities within a single token, subtoken annotation element to be used in SubentitiesLayer"""
#    ACCEPTED_DATA = (Feature,TextContent, Metric)
#    ANNOTATIONTYPE = AnnotationType.SUBENTITY
#    XMLTAG = 'subentity'




class SyntaxLayer(AbstractAnnotationLayer):
    """Syntax Layer: Annotation layer for SyntacticUnit span annotation elements"""
    ACCEPTED_DATA = (SyntacticUnit,Description)
    XMLTAG = 'syntax'
    ANNOTATIONTYPE = AnnotationType.SYNTAX

class ChunkingLayer(AbstractAnnotationLayer):
    """Chunking Layer: Annotation layer for Chunk span annotation elements"""
    ACCEPTED_DATA = (Chunk,Description)
    XMLTAG = 'chunking'
    ANNOTATIONTYPE = AnnotationType.CHUNKING

class EntitiesLayer(AbstractAnnotationLayer):
    """Entities Layer: Annotation layer for Entity span annotation elements. For named entities."""
    ACCEPTED_DATA = (Entity,Description)
    XMLTAG = 'entities'
    ANNOTATIONTYPE = AnnotationType.ENTITY

class DependenciesLayer(AbstractAnnotationLayer):
    """Dependencies Layer: Annotation layer for Dependency span annotation elements. For dependency entities."""
    ACCEPTED_DATA = (Dependency,Description)
    XMLTAG = 'dependencies'
    ANNOTATIONTYPE = AnnotationType.DEPENDENCY

class MorphologyLayer(AbstractAnnotationLayer):
    """Morphology Layer: Annotation layer for Morpheme subtoken annotation elements. For morphological analysis."""
    ACCEPTED_DATA = (Morpheme,)
    XMLTAG = 'morphology'
    ANNOTATIONTYPE = AnnotationType.MORPHOLOGICAL

Alternative.ACCEPTED_DATA.append( MorphologyLayer)
#class SubentitiesLayer(AbstractSubtokenAnnotationLayer):
#    """Subentities Layer: Annotation layer for Subentity subtoken annotation elements. For named entities within a single token."""
#    ACCEPTED_DATA = (Subentity,)
#    XMLTAG = 'subentities'

class CoreferenceLayer(AbstractAnnotationLayer):
    """Syntax Layer: Annotation layer for SyntacticUnit span annotation elements"""
    ACCEPTED_DATA = (CoreferenceChain,Description)
    XMLTAG = 'coreferences'
    ANNOTATIONTYPE = AnnotationType.COREFERENCE

class SemanticRolesLayer(AbstractAnnotationLayer):
    """Syntax Layer: Annotation layer for SemnaticRole span annotation elements"""
    ACCEPTED_DATA = (SemanticRole,Description)
    XMLTAG = 'semroles'
    ANNOTATIONTYPE = AnnotationType.SEMROLE

class HeadFeature(Feature):
    """Synset feature, to be used within PosAnnotation"""
    SUBSET = 'head' #associated subset
    XMLTAG = None

class PosAnnotation(AbstractTokenAnnotation):
    """Part-of-Speech annotation:  a token annotation element"""
    ANNOTATIONTYPE = AnnotationType.POS
    ACCEPTED_DATA = (Feature,HeadFeature,Description, Metric)
    XMLTAG = 'pos'

class LemmaAnnotation(AbstractTokenAnnotation):
    """Lemma annotation:  a token annotation element"""
    ANNOTATIONTYPE = AnnotationType.LEMMA
    ACCEPTED_DATA = (Feature,Description, Metric)
    XMLTAG = 'lemma'

class LangAnnotation(AbstractExtendedTokenAnnotation):
    """Language annotation:  an extended token annotation element"""
    ANNOTATIONTYPE = AnnotationType.LANG
    ACCEPTED_DATA = (Feature,Description, Metric)
    XMLTAG = 'lang'

#class PhonAnnotation(AbstractTokenAnnotation): #DEPRECATED in v0.9
#    """Phonetic annotation:  a token annotation element"""
#    ANNOTATIONTYPE = AnnotationType.PHON
#    ACCEPTED_DATA = (Feature,Description, Metric)
#    XMLTAG = 'phon'


class DomainAnnotation(AbstractExtendedTokenAnnotation):
    """Domain annotation:  an extended token annotation element"""
    ANNOTATIONTYPE = AnnotationType.DOMAIN
    ACCEPTED_DATA = (Feature,Description, Metric)
    XMLTAG = 'domain'

class SynsetFeature(Feature):
    """Synset feature, to be used within Sense"""
    #XMLTAG = 'synset'
    XMLTAG = None
    SUBSET = 'synset' #associated subset

class ActorFeature(Feature):
    """Actor feature, to be used within Event"""
    #XMLTAG = 'actor'
    XMLTAG = None
    SUBSET = 'actor' #associated subset

class BegindatetimeFeature(Feature):
    """Begindatetime feature, to be used within Event"""
    #XMLTAG = 'begindatetime'
    XMLTAG = None
    SUBSET = 'begindatetime' #associated subset

class EnddatetimeFeature(Feature):
    """Enddatetime feature, to be used within Event"""
    #XMLTAG = 'enddatetime'
    XMLTAG = None
    SUBSET = 'enddatetime' #associated subset

class StyleFeature(Feature):
    XMLTAG = None
    SUBSET = "style"

class Event(AbstractStructureElement):
    #ACCEPTED_DATA set at bottom
    ANNOTATIONTYPE = AnnotationType.EVENT
    XMLTAG = 'event'
    OCCURRENCESPERSET = 0

class Note(AbstractStructureElement):
    #ACCEPTED_DATA set at bottom
    ANNOTATIONTYPE = AnnotationType.NOTE
    XMLTAG = 'note'
    OCCURRENCESPERSET = 0

class TimeSegment(AbstractSpanAnnotation):
    ACCEPTED_DATA = (WordReference, Description, Feature, ActorFeature, BegindatetimeFeature, EnddatetimeFeature, Metric)
    ANNOTATIONTYPE = AnnotationType.TIMESEGMENT
    XMLTAG = 'timesegment'
    OCCURRENCESPERSET = 0

TimedEvent = TimeSegment #alias for FoLiA 0.8 compatibility

class TimingLayer(AbstractAnnotationLayer):
    """Dependencies Layer: Annotation layer for Dependency span annotation elements. For dependency entities."""
    ANNOTATIONTYPE = AnnotationType.TIMESEGMENT
    ACCEPTED_DATA = (TimedEvent,Description)
    XMLTAG = 'timing'


class SenseAnnotation(AbstractTokenAnnotation):
    """Sense annotation: a token annotation element"""
    ANNOTATIONTYPE = AnnotationType.SENSE
    ACCEPTED_DATA = (Feature,SynsetFeature, Description, Metric)
    XMLTAG = 'sense'

class SubjectivityAnnotation(AbstractTokenAnnotation):
    """Subjectivity annotation/Sentiment analysis: a token annotation element"""
    ANNOTATIONTYPE = AnnotationType.SUBJECTIVITY
    ACCEPTED_DATA = (Feature, Description, Metric)
    XMLTAG = 'subjectivity'


class Quote(AbstractStructureElement):
    """Quote: a structure element. For quotes/citations. May hold words or sentences."""
    REQUIRED_ATTRIBS = ()
    XMLTAG = 'quote'


    #ACCEPTED DATA defined later below

    def __init__(self,  doc, *args, **kwargs):
        super(Quote,self).__init__(doc, *args, **kwargs)


    def resolveword(self, id):
        for child in self:
            r =  child.resolveword(id)
            if r:
                return r
        return None

    def append(self, child, *args, **kwargs):
        if inspect.isclass(child):
            if child is Sentence:
                kwargs['auth'] = False
        elif isinstance(child, Sentence):
            child.auth = False #Sentences under quotes are non-authoritative
        return super(Quote, self).append(child, *args, **kwargs)

    def gettextdelimiter(self, retaintokenisation=False):
        #no text delimite rof itself, recurse into children to inherit delimiter
        for child in reversed(self):
            if isinstance(child, Sentence):
                return "" #if a quote ends in a sentence, we don't want any delimiter
            else:
                return child.gettextdelimiter(retaintokenisation)
        return delimiter


class Sentence(AbstractStructureElement):
    """Sentence element. A structure element. Represents a sentence and holds all its words (and possibly other structure such as LineBreaks, Whitespace and Quotes)"""

    ACCEPTED_DATA = (Word, Quote, AbstractExtendedTokenAnnotation, Correction, TextContent, String,Gap, Description,  Linebreak, Whitespace, Event, Note, Reference, Alignment, Metric, Alternative, AlternativeLayers, AbstractAnnotationLayer)
    XMLTAG = 's'
    TEXTDELIMITER = ' '
    ANNOTATIONTYPE = AnnotationType.SENTENCE

    def __init__(self,  doc, *args, **kwargs):
        """

            Example 1::

                sentence = paragraph.append( folia.Sentence)

                sentence.append( folia.Word, 'This')
                sentence.append( folia.Word, 'is')
                sentence.append( folia.Word, 'a')
                sentence.append( folia.Word, 'test', space=False)
                sentence.append( folia.Word, '.')

            Example 2::

                sentence = folia.Sentence( doc, folia.Word(doc, 'This'),  folia.Word(doc, 'is'),  folia.Word(doc, 'a'),  folia.Word(doc, 'test', space=False),  folia.Word(doc, '.') )
                paragraph.append(sentence)

        """
        super(Sentence,self).__init__(doc, *args, **kwargs)


    def resolveword(self, id):
        for child in self:
            r =  child.resolveword(id)
            if r:
                return r
        return None

    def corrections(self):
        """Are there corrections in this sentence?"""
        return bool(self.select(Correction))

    def paragraph(self):
        """Obtain the paragraph this sentence is a part of (None otherwise)"""
        e = self;
        while e.parent:
            if isinstance(e, Paragraph):
                return e
            e = e.parent
        return None

    def division(self):
        """Obtain the division this sentence is a part of (None otherwise)"""
        e = self;
        while e.parent:
            if isinstance(e, Division):
                return e
            e = e.parent
        return None


    def correctwords(self, originalwords, newwords, **kwargs):
        """Generic correction method for words. You most likely want to use the helper functions
           splitword() , mergewords(), deleteword(), insertword() instead"""
        for w in originalwords:
            if not isinstance(w, Word):
                raise Exception("Original word is not a Word instance: " + str(type(w)))
            elif w.sentence() != self:
                raise Exception("Original not found as member of sentence!")
        for w in newwords:
            if not isinstance(w, Word):
                raise Exception("New word is not a Word instance: " + str(type(w)))
        if 'suggest' in kwargs and kwargs['suggest']:
            del kwargs['suggest']
            return self.correct(suggestion=newwords,current=originalwords, **kwargs)
        else:
            return self.correct(original=originalwords, new=newwords, **kwargs)



    def splitword(self, originalword, *newwords, **kwargs):
        """TODO: Write documentation"""
        if isstring(originalword):
            originalword = self.doc[u(originalword)]
        return self.correctwords([originalword], newwords, **kwargs)



    def mergewords(self, newword, *originalwords, **kwargs):
        """TODO: Write documentation"""
        return self.correctwords(originalwords, [newword], **kwargs)

    def deleteword(self, word, **kwargs):
        """TODO: Write documentation"""
        if isstring(word):
            word = self.doc[u(word)]
        return self.correctwords([word], [], **kwargs)


    def insertword(self, newword, prevword, **kwargs):
        if prevword:
            if isstring(prevword):
                prevword = self.doc[u(prevword)]
            if not prevword in self or not isinstance(prevword, Word):
                raise Exception("Previous word not found or not instance of Word!")
            if isinstance(newword, list) or isinstance(newword, tuple):
                if not all([ isinstance(x, Word) for x in newword ]):
                    raise Exception("New word (iterable) constains non-Word instances!")
            elif not isinstance(newword, Word):
                raise Exception("New word no instance of Word!")

            kwargs['insertindex'] = self.data.index(prevword) + 1
        else:
            kwargs['insertindex'] = 0
        if isinstance(newword, list) or isinstance(newword, tuple):
            return self.correctwords([], newword, **kwargs)
        else:
            return self.correctwords([], [newword], **kwargs)


    def insertwordleft(self, newword, nextword, **kwargs):
        if nextword:
            if isstring(nextword):
                nextword = self.doc[u(nextword)]
            if not nextword in self or not isinstance(nextword, Word):
                raise Exception("Next word not found or not instance of Word!")
            if isinstance(newword, list) or isinstance(newword, tuple):
                if not all([ isinstance(x, Word) for x in newword ]):
                    raise Exception("New word (iterable) constains non-Word instances!")
            elif not isinstance(newword, Word):
                raise Exception("New word no instance of Word!")

            kwargs['insertindex'] = self.data.index(nextword)
        else:
            kwargs['insertindex'] = 0
        if isinstance(newword, list) or isinstance(newword, tuple):
            return self.correctwords([], newword, **kwargs)
        else:
            return self.correctwords([], [newword], **kwargs)

Quote.ACCEPTED_DATA = (Word, Sentence, Quote, TextContent, String,Gap, Description, Alignment, Metric, Alternative, AlternativeLayers, AbstractAnnotationLayer)


class Caption(AbstractStructureElement):
    """Element used for captions for figures or tables, contains sentences"""
    ACCEPTED_DATA = (Sentence, Reference, Description, TextContent,String,Alignment,Gap, Metric, Alternative, Alternative, AlternativeLayers, AbstractAnnotationLayer)
    OCCURRENCES = 1
    XMLTAG = 'caption'


class Label(AbstractStructureElement):
    """Element used for labels. Mostly in within list item. Contains words."""
    ACCEPTED_DATA = (Word, Reference, Description, TextContent,String,Alignment, Metric, Alternative, Alternative, AlternativeLayers, AbstractAnnotationLayer,AbstractExtendedTokenAnnotation)
    XMLTAG = 'label'


class ListItem(AbstractStructureElement):
    """Single element in a List. Structure element. Contained within List element."""
    #ACCEPTED_DATA = (List, Sentence) #Defined below
    XMLTAG = 'listitem'
    ANNOTATIONTYPE = AnnotationType.LIST


class List(AbstractStructureElement):
    """Element for enumeration/itemisation. Structure element. Contains ListItem elements."""
    ACCEPTED_DATA = (ListItem,Description, Caption, Event, Note, Reference, TextContent, String,Alignment, Metric, Alternative, Alternative, AlternativeLayers, AbstractAnnotationLayer,AbstractExtendedTokenAnnotation)
    XMLTAG = 'list'
    TEXTDELIMITER = '\n'
    ANNOTATIONTYPE = AnnotationType.LIST

ListItem.ACCEPTED_DATA = (List, Sentence, Description, Label, Event, Note, Reference, TextContent,String,Gap,Alignment, Metric, Alternative, AlternativeLayers, AbstractAnnotationLayer,AbstractExtendedTokenAnnotation)

class Figure(AbstractStructureElement):
    """Element for the representation of a graphical figure. Structure element."""
    ACCEPTED_DATA = (Sentence, Description, Caption, TextContent,String, Alignment, Metric, Alternative, Alternative, AlternativeLayers, AbstractAnnotationLayer)
    XMLTAG = 'figure'
    ANNOTATIONTYPE = AnnotationType.FIGURE

    def __init__(self, doc, *args, **kwargs):
        if 'src' in kwargs:
            self.src = kwargs['src']
            del kwargs['src']

        else:
            self.src = None

        super(Figure, self).__init__(doc, *args, **kwargs)

    def xml(self, attribs = None,elements = None, skipchildren = False):
        global NSFOLIA
        if self.src:
            if not attribs: attribs = {}
            attribs['{' + NSFOLIA + '}src'] = self.src
        return super(Figure, self).xml(attribs, elements, skipchildren)

    def json(self, attribs = None, recurse=True):
        if self.src:
            if not attribs: attribs = {}
            attribs['src'] = self.src
        return super(Figure, self).json(attribs, recurse)

    def caption(self):
        try:
            caption = self.select(Caption)[0]
            return caption.text()
        except:
            raise NoSuchText

    @classmethod
    def relaxng(cls, includechildren=True,extraattribs = None, extraelements=None):
        global NSFOLIA
        E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace"})
        if not extraattribs:
            extraattribs = [ E.optional(E.attribute(name='src')) ]
        else:
            extraattribs.append( E.optional(E.attribute(name='src')) )
        return AbstractStructureElement.relaxng(includechildren, extraattribs, extraelements, cls)



class Paragraph(AbstractStructureElement):
    """Paragraph element. A structure element. Represents a paragraph and holds all its sentences (and possibly other structure Whitespace and Quotes)."""

    ACCEPTED_DATA = (Sentence, AbstractExtendedTokenAnnotation, Correction, TextContent,String, Description, Linebreak, Whitespace, Gap, List, Figure, Event, Note, Reference,Alignment, Metric, Alternative, AlternativeLayers, AbstractAnnotationLayer)
    XMLTAG = 'p'
    TEXTDELIMITER = "\n\n"
    ANNOTATIONTYPE = AnnotationType.PARAGRAPH

class Head(AbstractStructureElement):
    """Head element. A structure element. Acts as the header/title of a division. There may be one per division. Contains sentences."""

    ACCEPTED_DATA = (Sentence, Word, Description, Event, Reference, TextContent,String,Alignment, Metric, Linebreak, Whitespace,Gap,  Alternative, AlternativeLayers, AbstractAnnotationLayer, AbstractExtendedTokenAnnotation)
    OCCURRENCES = 1
    TEXTDELIMITER = ' '
    XMLTAG = 'head'

class Cell(AbstractStructureElement):
    ACCEPTED_DATA = (Paragraph,Head,Sentence,Word, Correction, Event, Note, Reference, Linebreak, Whitespace, Gap, AbstractAnnotationLayer, AlternativeLayers, AbstractExtendedTokenAnnotation)
    XMLTAG = 'cell'
    TEXTDELIMITER = " | "
    REQUIRED_ATTRIBS = (),
    ANNOTATIONTYPE = AnnotationType.TABLE

class Row(AbstractStructureElement):
    ACCEPTED_DATA = (Cell,AbstractAnnotationLayer, AlternativeLayers,AbstractExtendedTokenAnnotation)
    XMLTAG = 'row'
    TEXTDELIMITER = "\n"
    REQUIRED_ATTRIBS = (),
    ANNOTATIONTYPE = AnnotationType.TABLE


class TableHead(AbstractStructureElement):
    ACCEPTED_DATA = (Row,AbstractAnnotationLayer, AlternativeLayers,AbstractExtendedTokenAnnotation)
    XMLTAG = 'tablehead'
    REQUIRED_ATTRIBS = (),
    ANNOTATIONTYPE = AnnotationType.TABLE


class Table(AbstractStructureElement):
    ACCEPTED_DATA = (TableHead, Row, AbstractAnnotationLayer, AlternativeLayers,AbstractExtendedTokenAnnotation)
    XMLTAG = 'table'
    ANNOTATIONTYPE = AnnotationType.TABLE


class Query(object):
    """An XPath query on one or more FoLiA documents"""
    def __init__(self, files, expression):
        if isstring(files):
            self.files = [u(files)]
        else:
            assert hasattr(files,'__iter__')
            self.files = files
        self.expression = expression

    def __iter__(self):
        for filename in self.files:
            doc = Document(file=filename, mode=Mode.XPATH)
            for result in doc.xpath(self.expression):
                yield result

class RegExp(object):
    def __init__(self, regexp):
        self.regexp = re.compile(regexp)

    def __eq__(self, value):
        return self.regexp.match(value)


class Pattern(object):
    """
    This class describes a pattern over words to be searched for. The ``Document.findwords()`` method can subsequently be called with this pattern, and it will return all the words that match. An example will best illustrate this, first a trivial example of searching for one word::

        for match in doc.findwords( folia.Pattern('house') ):
            for word in match:
                print word.id
            print "----"

    The same can be done for a sequence::

        for match in doc.findwords( folia.Pattern('a','big', 'house') ):
            for word in match:
                print word.id
            print "----"

    The boolean value ``True`` acts as a wildcard, matching any word::

        for match in doc.findwords( folia.Pattern('a',True,'house') ):
            for word in match:
                print word.id, word.text()
            print "----"

    Alternatively, and more constraning, you may also specify a tuple of alternatives::


        for match in doc.findwords( folia.Pattern('a',('big','small'),'house') ):
            for word in match:
                print word.id, word.text()
            print "----"

    Or even a regular expression using the ``folia.RegExp`` class::


        for match in doc.findwords( folia.Pattern('a', folia.RegExp('b?g'),'house') ):
            for word in match:
                print word.id, word.text()
            print "----"


    Rather than searching on the text content of the words, you can search on the
    classes of any kind of token annotation using the keyword argument
    ``matchannotation=``::

        for match in doc.findwords( folia.Pattern('det','adj','noun',matchannotation=folia.PosAnnotation ) ):
            for word in match:
                print word.id, word.text()
            print "----"

    The set can be restricted by adding the additional keyword argument
    ``matchannotationset=``. Case sensitivity, by default disabled, can be enabled by setting ``casesensitive=True``.

    Things become even more interesting when different Patterns are combined. A
    match will have to satisfy all patterns::

        for match in doc.findwords( folia.Pattern('a', True, 'house'), folia.Pattern('det','adj','noun',matchannotation=folia.PosAnnotation ) ):
            for word in match:
                print word.id, word.text()
            print "----"


    The ``findwords()`` method can be instructed to also return left and/or right context for any match. This is done using the ``leftcontext=`` and ``rightcontext=`` keyword arguments, their values being an integer number of the number of context words to include in each match. For instance, we can look for the word house and return its immediate neighbours as follows::

        for match in doc.findwords( folia.Pattern('house') , leftcontext=1, rightcontext=1):
            for word in match:
                print word.id
            print "----"

    A match here would thus always consist of three words instead of just one.

    Last, ``Pattern`` also has support for variable-width gaps, the asterisk symbol
    has special meaning to this end::


        for match in doc.findwords( folia.Pattern('a','*','house') ):
            for word in match:
                print word.id
            print "----"

    Unlike the pattern ``('a',True,'house')``, which by definition is a pattern of
    three words, the pattern in the example above will match gaps of any length (up
    to a certain built-in maximum), so this might include matches such as *a very
    nice house*.

    Some remarks on these methods of querying are in order. These searches are
    pretty exhaustive and are done by simply iterating over all the words in the
    document. The entire document is loaded in memory and no special indices are involved.
    For single documents this is okay, but when iterating over a corpus of
    thousands of documents, this method is too slow, especially for real-time
    applications. For huge corpora, clever indexing and database management systems
    will be required. This however is beyond the scope of this library.

    """


    def __init__(self, *args, **kwargs):
        if not all( ( (x is True or isinstance(x,RegExp) or isstring(x) or isinstance(x, list) or isinstance(x, tuple)) for x in args )):
            raise TypeError
        self.sequence = args

        if 'matchannotation' in kwargs:
            self.matchannotation = kwargs['matchannotation']
            del kwargs['matchannotation']
        else:
            self.matchannotation = None
        if 'matchannotationset' in kwargs:
            self.matchannotationset = kwargs['matchannotationset']
            del kwargs['matchannotationset']
        else:
            self.matchannotationset = None
        if 'casesensitive' in kwargs:
            self.casesensitive = bool(kwargs['casesensitive'])
            del kwargs['casesensitive']
        else:
            self.casesensitive = False
        for key in kwargs.keys():
            raise Exception("Unknown keyword parameter: " + key)

        if not self.casesensitive:
            if all( ( isstring(x) for x in self.sequence) ):
                self.sequence = [ u(x).lower() for x in self.sequence ]

    def __nonzero__(self): #Python 2.x
        return True

    def __bool__(self):
        return True

    def __len__(self):
        return len(self.sequence)

    def __getitem__(self, index):
        return self.sequence[index]

    def __getslice__(self, begin,end):
        return self.sequence[begin:end]

    def variablesize(self):
        return ('*' in self.sequence)

    def variablewildcards(self):
        wildcards = []
        for i,x in enumerate(self.sequence):
            if x == '*':
                wildcards.append(i)
        return wildcards


    def __repr__(self):
        return repr(self.sequence)


    def resolve(self,size, distribution):
        """Resolve a variable sized pattern to all patterns of a certain fixed size"""
        if not self.variablesize():
            raise Exception("Can only resize patterns with * wildcards")

        nrofwildcards = 0
        for i,x in enumerate(self.sequence):
            if x == '*':
                nrofwildcards += 1

        assert (len(distribution) == nrofwildcards)

        wildcardnr = 0
        newsequence = []
        for i,x in enumerate(self.sequence):
            if x == '*':
                newsequence += [True] * distribution[wildcardnr]
                wildcardnr += 1
            else:
                newsequence.append(x)
        d = { 'matchannotation':self.matchannotation, 'matchannotationset':self.matchannotationset, 'casesensitive':self.casesensitive }
        yield Pattern(*newsequence, **d )



class NativeMetaData(object):
    def __init__(self, *args, **kwargs):
        self.data = {}
        self.order = []
        for key, value in kwargs.items():
            self[key] = value

    def __setitem__(self, key, value):
        exists = key in self.data
        self.data[key] = value
        if not exists: self.order.append(key)

    def __iter__(self):
        for x in self.order:
            yield x

    def __contains__(self, x):
        return x in self.data

    def items(self):
        for key in self.order:
            yield key, self.data[key]

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def __delitem__(self,key):
        del self.data[key]
        self.order.remove(key)


class Document(object):
    """This is the FoLiA Document, all elements have to be associated with a FoLiA document. Besides holding elements, the document hold metadata including declaration, and an index of all IDs."""

    IDSEPARATOR = '.'

    def __init__(self, *args, **kwargs):
        global FOLIAVERSION
        """Start/load a FoLiA document:

        There are four sources of input for loading a FoLiA document::

        1) Create a new document by specifying an *ID*::

            doc = folia.Document(id='test')

        2) Load a document from FoLiA or D-Coi XML file::

            doc = folia.Document(file='/path/to/doc.xml')

        3) Load a document from an XML string::

            doc = folia.Document(string='<FoLiA>....</FoLiA>')

        4) Load a document by passing a parse xml tree (lxml.etree):

            doc = folia.Document(tree=xmltree)

        Additionally, there are three modes that can be set with the mode= keyword argument:

             * folia.Mode.MEMORY - The entire FoLiA Document will be loaded into memory. This is the default mode and the only mode in which documents can be manipulated and saved again.
             * folia.Mode.XPATH - The full XML tree will still be loaded into memory, but conversion to FoLiA classes occurs only when queried. This mode can be used when the full power of XPath is required.
             * folia.Mode.ITERATIVE - Not implemented, obsolete. Use Reader class instead


        Optional keyword arguments:

            ``debug=``:  Boolean to enable/disable debug
        """


        self.version = FOLIAVERSION

        self.data = [] #will hold all texts (usually only one)

        self.annotationdefaults = {}
        self.annotations = [] #Ordered list of incorporated annotations ['token','pos', etc..]

        #Add implicit declaration for TextContent
        self.annotations.append( (AnnotationType.TEXT,'undefined') )
        self.annotationdefaults[AnnotationType.TEXT] = {'undefined': {} }

        self.index = {} #all IDs go here
        self.declareprocessed = False # Will be set to True when declarations have been processed

        self.metadata = NativeMetaData() #will point to XML Element holding IMDI or CMDI metadata
        self.metadatatype = MetaDataType.NATIVE
        self.metadatafile = None #reference to external metadata file

        self.autodeclare = False #Automatic declarations in case of undeclared elements (will be enabled for DCOI, since DCOI has no declarations)

        if 'setdefinitions' in kwargs:
            self.setdefinitions = kwargs['setdefinitions'] #to re-use a shared store
        else:
            self.setdefinitions = {} #key: set name, value: SetDefinition instance (only used when deepvalidation=True)

        #The metadata fields FoLiA is directly aware of:
        self._title = self._date = self._publisher = self._license = self._language = None


        if 'debug' in kwargs:
            self.debug = kwargs['debug']
        else:
            self.debug = False

        if 'mode' in kwargs:
            self.mode = int(kwargs['mode'])
        else:
            self.mode = Mode.MEMORY #Load all in memory


        if 'parentdoc' in kwargs:  #for subdocuments
            assert isinstance(kwargs['parentdoc'], Document)
            self.parentdoc = kwargs['parentdoc']
        else:
            self.parentdoc = None

        self.subdocs = {} #will hold all subdocs (sourcestring => document) , needed so the index can resolve IDs in subdocs
        self.standoffdocs = {} #will hold all standoffdocs (type => set => sourcestring => document)

        if 'external' in kwargs:
            self.external = kwargs['external']
        else:
            self.external = False

        if self.external and not self.parentdoc:
            raise DeepValidationError("Document is marked as external and should not be loaded independently. However, no parentdoc= has been specified!")


        if 'loadsetdefinitions' in kwargs:
            self.loadsetdefinitions = bool(kwargs['loadsetdefinitions'])
        else:
            self.loadsetdefinitions = False

        if 'deepvalidation' in kwargs:
            self.deepvalidation = bool(kwargs['deepvalidation'])
            self.loadsetdefinitions = True
        else:
            self.deepvalidation = False

        if 'allowadhocsets' in kwargs:
            self.allowadhocsets = bool(kwargs['allowadhocsets'])
        else:
            if self.deepvalidation:
                self.allowadhocsets = False
            else:
                self.allowadhocsets = True

        if 'autodeclare' in kwargs:
            self.autodeclare = True

        if 'bypassleak' in kwargs:
            self.bypassleak = bool(kwargs['bypassleak'])
        else:
            self.bypassleak = True


        if 'id' in kwargs:
            isncname(kwargs['id'])
            self.id = kwargs['id']
        elif 'file' in kwargs:
            self.filename = kwargs['file']
            if self.filename[-4:].lower() == '.bz2':
                f = bz2.BZ2File(self.filename)
                contents = f.read()
                f.close()
                self.tree = xmltreefromstring(contents,self.bypassleak)
                del contents
                self.parsexml(self.tree.getroot())
            elif self.filename[-3:].lower() == '.gz':
                f = gzip.GzipFile(self.filename)
                contents = f.read()
                f.close()
                self.tree = xmltreefromstring(contents,self.bypassleak)
                del contents
                self.parsexml(self.tree.getroot())
            else:
                self.load(self.filename)
        elif 'string' in kwargs:
            self.tree = xmltreefromstring(kwargs['string'],self.bypassleak)
            del kwargs['string']
            self.parsexml(self.tree.getroot())
            if self.mode != Mode.XPATH:
                #XML Tree is now obsolete (only needed when partially loaded for xpath queries)
                self.tree = None
        elif 'tree' in kwargs:
            self.parsexml(kwargs['tree'])
        else:
            raise Exception("No ID, filename or tree specified")

        if self.mode != Mode.XPATH:
            #XML Tree is now obsolete (only needed when partially loaded for xpath queries), free memory
            self.tree = None

    #def __del__(self):
    #    del self.index
    #    for child in self.data:
    #        del child
    #    del self.data

    def load(self, filename):
        """Load a FoLiA or D-Coi XML file"""
        global LXE
        #if LXE and self.mode != Mode.XPATH:
        #    #workaround for xml:id problem (disabled)
        #    #f = open(filename)
        #    #s = f.read().replace(' xml:id=', ' id=')
        #    #f.close()
        #    self.tree = ElementTree.parse(filename)
        #else:
        self.tree = xmltreefromfile(filename, self.bypassleak)
        self.parsexml(self.tree.getroot())
        if self.mode != Mode.XPATH:
            #XML Tree is now obsolete (only needed when partially loaded for xpath queries)
            self.tree = None

    def items(self):
        """Returns a depth-first flat list of all items in the document"""
        l = []
        for e in self.data:
            l += e.items()
        return l

    def xpath(self, query):
        """Run Xpath expression and parse the resulting elements. Don't forget to use the FoLiA namesapace in your expressions, using folia: or the short form f: """
        for result in self.tree.xpath(query,namespaces={'f': 'http://ilk.uvt.nl/folia','folia': 'http://ilk.uvt.nl/folia' }):
            yield self.parsexml(result)


    def findwords(self, *args, **kwargs):
        for x in findwords(self,self.words,*args,**kwargs):
            yield x

    def save(self, filename=None):
        """Save the document to FoLiA XML.

        Arguments:
            * ``filename=``: The filename to save to. If not set (None), saves to the same file as loaded from.
        """
        if not filename:
            filename = self.filename
        if not filename:
            raise Exception("No filename specified")
        if filename[-4:].lower() == '.bz2':
            f = bz2.BZ2File(filename,'wb')
            f.write(self.xmlstring().encode('utf-8'))
            f.close()
        elif filename[-3:].lower() == '.gz':
            f = gzip.GzipFile(filename,'wb')
            f.write(self.xmlstring().encode('utf-8'))
            f.close()
        else:
            f = io.open(filename,'w',encoding='utf-8')
            f.write(self.xmlstring())
            f.close()

    def setcmdi(self,filename):
        self.metadatatype = MetaDataType.CMDI
        self.metadatafile = filename
        self.metadata = {}
        #TODO: Parse CMDI


    def __len__(self):
        return len(self.data)

    def __nonzero__(self): #Python 2.x
        return True

    def __bool__(self):
        return True

    def __iter__(self):
        for text in self.data:
            yield text


    def __contains__(self, key):
        """Tests if the specified ID is in the document index"""
        if key in self.index:
            return True
        elif self.subdocs:
            for subdoc in self.subdocs.values():
                if key in subdoc:
                    return True
            return False
        else:
            return False

    def __getitem__(self, key):
        """Obtain an element by ID from the document index.

        Example::

            word = doc['example.p.4.s.10.w.3']
        """
        if isinstance(key, int):
            return self.data[key]
        else:
            try:
                return self.index[key]
            except KeyError:
                if self.subdocs: #perhaps the key is in one of our subdocs?
                    for subdoc in self.subdocs.values():
                        try:
                            return subdoc[key]
                        except KeyError:
                            pass
                else:
                    raise


    def append(self,text):
        """Add a text to the document:

        Example 1::

            doc.append(folia.Text)

        Example 2::
            doc.append( folia.Text(doc, id='example.text') )


        """
        if text is Text:
            text = Text(self, id=self.id + '.text.' + str(len(self.data)+1) )
        else:
            assert isinstance(text, Text)
        self.data.append(text)
        return text

    def create(self, Class, *args, **kwargs):
        """Create an element associated with this Document. This method may be obsolete and removed later."""
        return Class(self, *args, **kwargs)

    def xmldeclarations(self):
        l = []
        E = ElementMaker(namespace="http://ilk.uvt.nl/folia",nsmap={None: "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace"})

        for annotationtype, set in self.annotations:
            label = None
            #Find the 'label' for the declarations dynamically (aka: AnnotationType --> String)
            for key, value in vars(AnnotationType).items():
                if value == annotationtype:
                    label = key
                    break
            #gather attribs

            if annotationtype == AnnotationType.TEXT and set == 'undefined' and len(self.annotationdefaults[annotationtype][set]) == 0:
                #this is the implicit TextContent declaration, no need to output it explicitly
                continue

            attribs = {}
            if set and set != 'undefined':
                attribs['{' + NSFOLIA + '}set'] = set


            for key, value in self.annotationdefaults[annotationtype][set].items():
                if key == 'annotatortype':
                    if value == AnnotatorType.MANUAL:
                        attribs['{' + NSFOLIA + '}' + key] = 'manual'
                    elif value == AnnotatorType.AUTO:
                        attribs['{' + NSFOLIA + '}' + key] = 'auto'
                elif key == 'datetime':
                     attribs['{' + NSFOLIA + '}' + key] = value.strftime("%Y-%m-%dT%H:%M:%S") #proper iso-formatting
                elif value:
                    attribs['{' + NSFOLIA + '}' + key] = value
            if label:
                l.append( makeelement(E,'{' + NSFOLIA + '}' + label.lower() + '-annotation', **attribs) )
            else:
                raise Exception("Invalid annotation type")
        return l

    def jsondeclarations(self):
        l = []
        for annotationtype, set in self.annotations:
            label = None
            #Find the 'label' for the declarations dynamically (aka: AnnotationType --> String)
            for key, value in vars(AnnotationType).items():
                if value == annotationtype:
                    label = key
                    break
            #gather attribs

            if annotationtype == AnnotationType.TEXT and set == 'undefined' and len(self.annotationdefaults[annotationtype][set]) == 0:
                #this is the implicit TextContent declaration, no need to output it explicitly
                continue

            jsonnode = {'annotationtype': label.lower()}
            if set and set != 'undefined':
                jsonnode['set'] = set


            for key, value in self.annotationdefaults[annotationtype][set].items():
                if key == 'annotatortype':
                    if value == AnnotatorType.MANUAL:
                        jsonnode[key] = 'manual'
                    elif value == AnnotatorType.AUTO:
                        jsonnode[key] = 'auto'
                elif key == 'datetime':
                     jsonnode[key] = value.strftime("%Y-%m-%dT%H:%M:%S") #proper iso-formatting
                elif value:
                    jsonnode[key] = value
            if label:
                l.append( jsonnode  )
            else:
                raise Exception("Invalid annotation type")
        return l

    def xml(self):
        global LIBVERSION, FOLIAVERSION
        E = ElementMaker(namespace="http://ilk.uvt.nl/folia",nsmap={None: "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace", 'xlink':"http://www.w3.org/1999/xlink"})
        attribs = {}
        if self.bypassleak:
            attribs['XMLid'] = self.id
        else:
            attribs['{http://www.w3.org/XML/1998/namespace}id'] = self.id

        if self.version:
            attribs['version'] = self.version
        else:
            attribs['version'] = FOLIAVERSION

        attribs['generator'] = 'pynlpl.formats.folia-v' + LIBVERSION

        metadataattribs = {}
        if self.metadatatype == MetaDataType.NATIVE:
            metadataattribs['{' + NSFOLIA + '}type'] = 'native'
        elif self.metadatatype == MetaDataType.IMDI:
            metadataattribs['{' + NSFOLIA + '}type'] = 'imdi'
            if self.metadatafile:
                metadataattribs['{' + NSFOLIA + '}src'] = self.metadatafile
        elif self.metadatatype == MetaDataType.CMDI:
            metadataattribs['{' + NSFOLIA + '}type'] = 'cmdi'
            metadataattribs['{' + NSFOLIA + '}src'] = self.metadatafile

        e = E.FoLiA(
            E.metadata(
                E.annotations(
                    *self.xmldeclarations()
                ),
                *self.xmlmetadata(),
                **metadataattribs
            )
        , **attribs)
        for text in self.data:
            e.append(text.xml())
        return e

    def json(self):
        jsondoc = {'id': self.id, 'children': [], 'declarations': self.jsondeclarations() }
        if self.version:
            jsondoc['version'] = self.version
        else:
            jsondoc['version'] = FOLIAVERSION
        jsondoc['generator'] = 'pynlpl.formats.folia-v' + LIBVERSION

        for text in self.data:
            jsondoc['children'].append(text.json())
        return jsondoc

    def xmlmetadata(self):
        E = ElementMaker(namespace="http://ilk.uvt.nl/folia",nsmap={None: "http://ilk.uvt.nl/folia", 'xml' : "http://www.w3.org/XML/1998/namespace"})
        if self.metadatatype == MetaDataType.NATIVE:
            e = []
            if not self.metadatafile:
                for key, value in self.metadata.items():
                    e.append(E.meta(value,id=key) )
            return e
        elif self.metadatatype == MetaDataType.IMDI:
            if self.metadatafile:
                return [] #external
            elif self.metadata:
                return [xmltreefromstring(self.metadata).getroot()] #inline
            else:
                return []
        elif self.metadatatype == MetaDataType.CMDI: #CMDI, by definition external
            return []




    def parsexmldeclarations(self, node):
        if self.debug >= 1:
            print("[PyNLPl FoLiA DEBUG] Processing Annotation Declarations",file=stderr)
        self.declareprocessed = True
        for subnode in node:
            if subnode.tag[:25] == '{' + NSFOLIA + '}' and subnode.tag[-11:] == '-annotation':
                prefix = subnode.tag[25:][:-11]
                type = None
                if prefix.upper() in vars(AnnotationType):
                    type = vars(AnnotationType)[prefix.upper()]
                else:
                    raise Exception("Unknown declaration: " + subnode.tag)

                if 'set' in subnode.attrib and subnode.attrib['set']:
                    set = subnode.attrib['set']
                else:
                    set = 'undefined'

                if (type,set) in self.annotations:
                    if type == AnnotationType.TEXT:
                        #explicit Text declaration, remove the implicit declaration:
                        a = []
                        for t,s in self.annotations:
                            if not (t == AnnotationType.TEXT and s == 'undefined'):
                                a.append( (t,s) )
                        self.annotations = a
                    #raise ValueError("Double declaration of " + subnode.tag + ", set '" + set + "' + is already declared")    //doubles are okay says Ko
                else:
                    self.annotations.append( (type, set) )

                #Load set definition
                if set and self.loadsetdefinitions and not set in self.setdefinitions:
                    if set[:7] == "http://" or set[:8] == "https://" or set[:6] == "ftp://":
                        try:
                            self.setdefinitions[set] = loadsetdefinition(set) #will raise exception on error
                        except DeepValidationError:
                            print("WARNING: Set " + set + " could not be downloaded, ignoring!",file=sys.stderr) #warning and ignore
                            pass

                #Set defaults
                if type in self.annotationdefaults and set in self.annotationdefaults[type]:
                    #handle duplicate. If ambiguous: remove defaults
                    if 'annotator' in subnode.attrib:
                        if not ('annotator' in self.annotationdefaults[type][set]):
                            self.annotationdefaults[type][set]['annotator'] = subnode.attrib['annotator']
                        elif self.annotationdefaults[type][set]['annotator'] != subnode.attrib['annotator']:
                            del self.annotationdefaults[type][set]['annotator']
                    if 'annotatortype' in subnode.attrib:
                        if not ('annotatortype' in self.annotationdefaults[type][set]):
                            self.annotationdefaults[type][set]['annotatortype'] = subnode.attrib['annotatortype']
                        elif self.annotationdefaults[type][set]['annotatortype'] != subnode.attrib['annotatortype']:
                            del self.annotationdefaults[type][set]['annotatortype']
                else:
                    defaults = {}
                    if 'annotator' in subnode.attrib:
                        defaults['annotator'] = subnode.attrib['annotator']
                    if 'annotatortype' in subnode.attrib:
                        if subnode.attrib['annotatortype'] == 'auto':
                            defaults['annotatortype'] = AnnotatorType.AUTO
                        else:
                            defaults['annotatortype'] = AnnotatorType.MANUAL
                    if 'datetime' in subnode.attrib:
                        if isinstance(subnode.attrib['datetime'], datetime):
                            defaults['datetime'] = subnode.attrib['datetime']
                        else:
                            defaults['datetime'] = parse_datetime(subnode.attrib['datetime'])

                    if not type in self.annotationdefaults:
                        self.annotationdefaults[type] = {}
                    self.annotationdefaults[type][set] = defaults


                if 'external' in subnode.attrib and subnode.attrib['external']:
                    if self.debug >= 1:
                        print("[PyNLPl FoLiA DEBUG] Loading external document: " + subnode.attrib['external'],file=stderr)
                    if not type in self.standoffdocs:
                        self.standoffdocs[type] = {}
                    self.standoffdocs[type][set] = {}

                    #check if it is already loaded, if multiple references are made to the same doc we reuse the instance
                    standoffdoc = None
                    for t in self.standoffdocs:
                        for s in self.standoffdocs[t]:
                            for source in self.standoffdocs[t][s]:
                                if source == subnode.attrib['external']:
                                    standoffdoc = self.standoffdocs[t][s]
                                    break
                            if standoffdoc: break
                        if standoffdoc: break

                    if not standoffdoc:
                        if subnode.attrib['external'][:7] == 'http://' or subnode.attrib['external'][:8] == 'https://':
                            #document is remote, download (in memory)
                            try:
                                f = urlopen(subnode.attrib['external'])
                            except:
                                raise DeepValidationError("Unable to download standoff document: " + subnode.attrib['external'])
                            try:
                                content = u(f.read())
                            except IOError:
                                raise DeepValidationError("Unable to download standoff document: " + subnode.attrib['external'])
                            f.close()
                            standoffdoc = Document(string=content, parentdoc=self, setdefinitions=self.setdefinitions)
                        elif os.path.exists(subnode.attrib['external']):
                            #document is on disk:
                            standoffdoc = Document(file=subnode.attrib['external'], parentdoc=self, setdefinitions=self.setdefinitions)
                        else:
                            #document not found
                            raise DeepValidationError("Unable to find standoff document: " + subnode.attrib['external'])

                    self.standoffdocs[type][set][subnode.attrib['external']] = standoffdoc
                    standoffdoc.parentdoc = self

                if self.debug >= 1:
                    print("[PyNLPl FoLiA DEBUG] Found declared annotation " + subnode.tag + ". Defaults: " + repr(defaults),file=stderr)




    def setimdi(self, node):
        global LXE
        #TODO: node or filename
        ns = {'imdi': 'http://www.mpi.nl/IMDI/Schema/IMDI'}
        self.metadatatype = MetaDataType.IMDI
        if LXE:
            self.metadata = ElementTree.tostring(node, xml_declaration=False, pretty_print=True, encoding='utf-8')
        else:
            self.metadata = ElementTree.tostring(node, encoding='utf-8')
        n = node.xpath('imdi:Session/imdi:Title', namespaces=ns)
        if n and n[0].text: self._title = n[0].text
        n = node.xpath('imdi:Session/imdi:Date', namespaces=ns)
        if n and n[0].text: self._date = n[0].text
        n = node.xpath('//imdi:Source/imdi:Access/imdi:Publisher', namespaces=ns)
        if n and n[0].text: self._publisher = n[0].text
        n = node.xpath('//imdi:Source/imdi:Access/imdi:Availability', namespaces=ns)
        if n and n[0].text: self._license = n[0].text
        n = node.xpath('//imdi:Languages/imdi:Language/imdi:ID', namespaces=ns)
        if n and n[0].text: self._language = n[0].text

    def declare(self, annotationtype, set, **kwargs):
        if inspect.isclass(annotationtype):
            annotationtype = annotationtype.ANNOTATIONTYPE
        if not (annotationtype, set) in self.annotations:
            self.annotations.append( (annotationtype,set) )
            if set and self.loadsetdefinitions and not set in self.setdefinitions:
                if set[:7] == "http://" or set[:8] == "https://" or set[:6] == "ftp://":
                    self.setdefinitions[set] = loadsetdefinition(set) #will raise exception on error
        if not annotationtype in self.annotationdefaults:
            self.annotationdefaults[annotationtype] = {}
        self.annotationdefaults[annotationtype][set] = kwargs

    def declared(self, annotationtype, set):
        if inspect.isclass(annotationtype) and isinstance(annotationtype,AbstractElement): annotationtype = annotationtype.ANNOTATIONTYPE
        return ( (annotationtype,set) in self.annotations)


    def defaultset(self, annotationtype):
        if inspect.isclass(annotationtype) and isinstance(annotationtype,AbstractElement): annotationtype = annotationtype.ANNOTATIONTYPE
        try:
            return list(self.annotationdefaults[annotationtype].keys())[0]
        except IndexError:
            raise NoDefaultError


    def defaultannotator(self, annotationtype, set=None):
        if inspect.isclass(annotationtype) and isinstance(annotationtype,AbstractElement): annotationtype = annotationtype.ANNOTATIONTYPE
        if not set: set = self.defaultset(annotationtype)
        try:
            return self.annotationdefaults[annotationtype][set]['annotator']
        except KeyError:
            raise NoDefaultError

    def defaultannotatortype(self, annotationtype,set=None):
        if inspect.isclass(annotationtype) and isinstance(annotationtype,AbstractElement): annotationtype = annotationtype.ANNOTATIONTYPE
        if not set: set = self.defaultset(annotationtype)
        try:
            return self.annotationdefaults[annotationtype][set]['annotatortype']
        except KeyError:
            raise NoDefaultError


    def defaultdatetime(self, annotationtype,set=None):
        if inspect.isclass(annotationtype) and isinstance(annotationtype,AbstractElement): annotationtype = annotationtype.ANNOTATIONTYPE
        if not set: set = self.defaultset(annotationtype)
        try:
            return self.annotationdefaults[annotationtype][set]['datetime']
        except KeyError:
            raise NoDefaultError





    def title(self, value=None):
        """No arguments: Get the document's title from metadata
           Argument: Set the document's title in metadata
        """
        if not (value is None):
            if (self.metadatatype == MetaDataType.NATIVE):
                 self.metadata['title'] = value
            else:
                self._title = value
        if (self.metadatatype == MetaDataType.NATIVE):
            if 'title' in self.metadata:
                return self.metadata['title']
            else:
                return None
        else:
            return self._title

    def date(self, value=None):
        """No arguments: Get the document's date from metadata
           Argument: Set the document's date in metadata
        """
        if not (value is None):
            if (self.metadatatype == MetaDataType.NATIVE):
                 self.metadata['date'] = value
            else:
                self._date = value
        if (self.metadatatype == MetaDataType.NATIVE):
            if 'date' in self.metadata:
                return self.metadata['date']
            else:
                return None
        else:
            return self._date

    def publisher(self, value=None):
        """No arguments: Get the document's publisher from metadata
           Argument: Set the document's publisher in metadata
        """
        if not (value is None):
            if (self.metadatatype == MetaDataType.NATIVE):
                 self.metadata['publisher'] = value
            else:
                self._publisher = value
        if (self.metadatatype == MetaDataType.NATIVE):
            if 'publisher' in self.metadata:
                return self.metadata['publisher']
            else:
                return None
        else:
            return self._publisher

    def license(self, value=None):
        """No arguments: Get the document's license from metadata
           Argument: Set the document's license in metadata
        """
        if not (value is None):
            if (self.metadatatype == MetaDataType.NATIVE):
                 self.metadata['license'] = value
            else:
                self._license = value
        if (self.metadatatype == MetaDataType.NATIVE):
            if 'license' in self.metadata:
                return self.metadata['license']
            else:
                return None
        else:
            return self._license

    def language(self, value=None):
        """No arguments: Get the document's language (ISO-639-3) from metadata
           Argument: Set the document's language (ISO-639-3) in metadata
        """
        if not (value is None):
            if (self.metadatatype == MetaDataType.NATIVE):
                 self.metadata['language'] = value
            else:
                self._language = value
        if (self.metadatatype == MetaDataType.NATIVE):
            if 'language' in self.metadata:
                return self.metadata['language']
            else:
                return None
        else:
            return self._language

    def parsemetadata(self, node):
        if self.debug >= 1: print >>stderr, "[PyNLPl FoLiA DEBUG] Found Metadata"
        if 'type' in node.attrib and node.attrib['type'] == 'imdi':
            self.metadatatype = MetaDataType.IMDI
        elif 'type' in node.attrib and  node.attrib['type'] == 'cmdi':
            self.metadatatype = MetaDataType.CMDI
        elif 'type' in node.attrib and node.attrib['type'] == 'native':
            self.metadatatype = MetaDataType.NATIVE
        else:
            #no type specified, default to native
            self.metadatatype = MetaDataType.NATIVE


        self.metadata = NativeMetaData()
        self.metadatafile = None

        if 'src' in node.attrib:
            self.metadatafile =  node.attrib['src']

        for subnode in node:
            if subnode.tag == '{http://www.mpi.nl/IMDI/Schema/IMDI}METATRANSCRIPT':
                self.metadatatype = MetaDataType.IMDI
                self.setimdi(subnode)
            if subnode.tag == '{' + NSFOLIA + '}annotations':
                self.parsexmldeclarations(subnode)
            if subnode.tag == '{' + NSFOLIA + '}meta':
                if subnode.text:
                    self.metadata[subnode.attrib['id']] = subnode.text

    def parsexml(self, node, ParentClass = None):
        """Main XML parser, will invoke class-specific XML parsers. For internal use."""
        global XML2CLASS, NSFOLIA, NSDCOI, LXE


        if (LXE and isinstance(node,ElementTree._ElementTree)) or (not LXE and isinstance(node, ElementTree.ElementTree)):
            node = node.getroot()
        elif isstring(node):
            node = xmltreefromstring(node).getroot()

        if node.tag.startswith('{' + NSFOLIA + '}'):
            foliatag = node.tag[nslen:]
            if foliatag == "FoLiA":
                if self.debug >= 1: print("[PyNLPl FoLiA DEBUG] Found FoLiA document",file=stderr)
                try:
                    self.id = node.attrib['{http://www.w3.org/XML/1998/namespace}id']
                except KeyError:
                    try:
                        self.id = node.attrib['XMLid']
                    except KeyError:
                        try:
                            self.id = node.attrib['id']
                        except KeyError:
                            raise Exception("FoLiA Document has no ID!")
                if 'version' in node.attrib:
                    self.version = node.attrib['version']
                else:
                    self.version = None

                if 'external' in node.attrib:
                    if node.attrib['external'] == 'yes':
                        self.external = True
                    else:
                        self.external = False

                    if self.external and not self.parentdoc:
                        raise DeepValidationError("Document is marked as external and should not be loaded independently. However, no parentdoc= has been specified!")


                for subnode in node:
                    if subnode.tag == '{' + NSFOLIA + '}metadata':
                        self.parsemetadata(subnode)
                    elif subnode.tag == '{' + NSFOLIA + '}text' and self.mode == Mode.MEMORY:
                        if self.debug >= 1: print("[PyNLPl FoLiA DEBUG] Found Text",file=stderr)
                        self.data.append( self.parsexml(subnode) )
            else:
                #generic handling (FoLiA)
                if not foliatag in XML2CLASS:
                        raise Exception("Unknown FoLiA XML tag: " + foliatag)
                Class = XML2CLASS[foliatag]
                return Class.parsexml(node,self)
        elif node.tag == '{' + NSDCOI + '}DCOI':
            if self.debug >= 1: print("[PyNLPl FoLiA DEBUG] Found DCOI document",file=stderr)
            self.autodeclare = True
            try:
                self.id = node.attrib['{http://www.w3.org/XML/1998/namespace}id']
            except KeyError:
                try:
                    self.id = node.attrib['id']
                except KeyError:
                    try:
                        self.id = node.attrib['XMLid']
                    except KeyError:
                        raise Exception("D-Coi Document has no ID!")
            for subnode in node:
                if subnode.tag == '{http://www.mpi.nl/IMDI/Schema/IMDI}METATRANSCRIPT':
                    self.metadatatype = MetaDataType.IMDI
                    self.setimdi(subnode)
                elif subnode.tag == '{' + NSDCOI + '}text':
                    if self.debug >= 1: print("[PyNLPl FoLiA DEBUG] Found Text",file=stderr)
                    self.data.append( self.parsexml(subnode) )
        elif node.tag.startswith('{' + NSDCOI + '}'):
            #generic handling (D-Coi)
            if node.tag[nslendcoi:] in XML2CLASS:
                Class = XML2CLASS[node.tag[nslendcoi:]]
                return Class.parsexml(node,self)
            elif node.tag[nslendcoi:][0:3] == 'div': #support for div0, div1, etc:
                Class = Division
                return Class.parsexml(node,self)
            elif node.tag[nslendcoi:] == 'item': #support for listitem
                Class = ListItem
                return Class.parsexml(node,self)
            elif node.tag[nslendcoi:] == 'figDesc': #support for description in figures
                Class = Description
                return Class.parsexml(node,self)
            else:
                raise Exception("Unknown DCOI XML tag: " + node.tag)
        else:
            raise Exception("Unknown FoLiA XML tag: " + node.tag)


    def select(self, Class, set=None):
        if self.mode == Mode.MEMORY:
            return sum([ t.select(Class,set,True ) for t in self.data ],[])



    def paragraphs(self, index = None):
        """Return a list of all paragraphs found in the document.

        If an index is specified, return the n'th paragraph only (starting at 0)"""
        if index is None:
            return sum([ t.select(Paragraph) for t in self.data ],[])
        else:
            return sum([ t.select(Paragraph) for t in self.data ],[])[index]

    def sentences(self, index = None):
        """Return a list of all sentence found in the document. Except for sentences in quotes.

        If an index is specified, return the n'th sentence only (starting at 0)"""
        if index is None:
            return sum([ t.select(Sentence,None,True,[Quote]) for t in self.data ],[])
        else:
            return sum([ t.select(Sentence,None,True,[Quote]) for t in self.data ],[])[index]


    def words(self, index = None):
        """Return a list of all active words found in the document. Does not descend into annotation layers, alternatives, originals, suggestions.

        If an index is specified, return the n'th word only (starting at 0)"""
        if index is None:
            return sum([ t.select(Word,None,True,defaultignorelist_structure) for t in self.data ],[])
        else:
            return sum([ t.select(Word,None,True,defaultignorelist_structure) for t in self.data ],[])[index]


    def text(self, retaintokenisation=False):
        """Returns the text of the entire document (returns a unicode instance)"""
        s = ""
        for c in self.data:
            if s: s += "\n\n\n"
            try:
                s += c.text('current',retaintokenisation)
            except NoSuchText:
                continue
        return s

    def xmlstring(self):
        s = ElementTree.tostring(self.xml(), xml_declaration=True, pretty_print=True, encoding='utf-8')
        if sys.version < '3':
            if isinstance(s, str):
                s = unicode(s,'utf-8')
        else:
            if isinstance(s,bytes):
                s = str(s,'utf-8')

        if self.bypassleak:
            s = s.replace('XMLid=','xml:id=')
        s = s.replace('ns0:','') #ugly patch to get rid of namespace prefix
        s = s.replace(':ns0','')
        return s


    def __unicode__(self):
        """Returns the text of the entire document"""
        return self.text()

    def __str__(self):
        """Returns the text of the entire document"""
        return self.text()

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        if len(self.data) != len(other.data):
            if self.debug: print("[PyNLPl FoLiA DEBUG] Equality check - Documents have unequal amount of children",file=stderr)
            return False
        for e,e2 in zip(self.data,other.data):
            if e != e2:
                return False
        return True










class Division(AbstractStructureElement):
    """Structure element representing some kind of division. Divisions may be nested at will, and may include almost all kinds of other structure elements."""
    #Accepted_data set later
    REQUIRED_ATTRIBS = (Attrib.ID,)
    OPTIONAL_ATTRIBS = (Attrib.CLASS,Attrib.N)
    XMLTAG = 'div'
    ANNOTATIONTYPE = AnnotationType.DIVISION
    TEXTDELIMITER = "\n\n\n"

    def head(self):
        for e in self.data:
            if isinstance(e, Head):
                return e
        raise NoSuchAnnotation()



class Text(AbstractStructureElement):
    """A full text. This is a high-level element (not to be confused with TextContent!). This element may contain divisions, paragraphs, sentences, etc.."""

    REQUIRED_ATTRIBS = (Attrib.ID,)
    OPTIONAL_ATTRIBS = (Attrib.N,)
    ACCEPTED_DATA = (Gap, Event, Division, Paragraph, Sentence, Word,  List, Figure, Table, Note, Reference, AbstractAnnotationLayer, AbstractExtendedTokenAnnotation, Description, TextContent,String, Metric)
    XMLTAG = 'text'
    TEXTDELIMITER = "\n\n\n"


#==============================================================================
#Setting Accepted data that has been postponed earlier (to allow circular references)

Division.ACCEPTED_DATA = (Division, Gap, Event, Head, Paragraph, Sentence, List, Figure, Table, Note, Reference,AbstractExtendedTokenAnnotation, Description, Linebreak, Whitespace, Alternative, AlternativeLayers, AbstractAnnotationLayer)
Event.ACCEPTED_DATA = (Paragraph, Sentence, Word, Head,List, Figure, Table, Reference, Feature, ActorFeature, BegindatetimeFeature, EnddatetimeFeature, TextContent, String, Metric,AbstractExtendedTokenAnnotation)
Note.ACCEPTED_DATA = (Paragraph, Sentence, Word, Head, List, Figure, Table, Reference, Feature, TextContent,String, Metric,AbstractExtendedTokenAnnotation)


#==============================================================================

class Corpus:
    """A corpus of various FoLiA documents. Yields a Document on each iteration. Suitable for sequential processing."""

    def __init__(self,corpusdir, extension = 'xml', restrict_to_collection = "", conditionf=lambda x: True, ignoreerrors=False, **kwargs):
        self.corpusdir = corpusdir
        self.extension = extension
        self.restrict_to_collection = restrict_to_collection
        self.conditionf = conditionf
        self.ignoreerrors = ignoreerrors
        self.kwargs = kwargs

    def __iter__(self):
        if not self.restrict_to_collection:
            for f in glob.glob(self.corpusdir+"/*." + self.extension):
                if self.conditionf(f):
                    try:
                        yield Document(file=f, **self.kwargs )
                    except Exception as e:
                        print("Error, unable to parse " + f + ": " + e.__class__.__name__  + " - " + str(e),file=stderr)
                        if not self.ignoreerrors:
                            raise
        for d in glob.glob(self.corpusdir+"/*"):
            if (not self.restrict_to_collection or self.restrict_to_collection == os.path.basename(d)) and (os.path.isdir(d)):
                for f in glob.glob(d+ "/*." + self.extension):
                    if self.conditionf(f):
                        try:
                            yield Document(file=f, **self.kwargs)
                        except Exception as e:
                            print("Error, unable to parse " + f + ": " + e.__class__.__name__  + " - " + str(e),file=stderr)
                            if not self.ignoreerrors:
                                raise


class CorpusFiles(Corpus):
    """A corpus of various FoLiA documents. Yields the filenames on each iteration."""

    def __iter__(self):
        if not self.restrict_to_collection:
            for f in glob.glob(self.corpusdir+"/*." + self.extension):
                if self.conditionf(f):
                    try:
                        yield f
                    except Exception as e:
                        print("Error, unable to parse " + f+ ": " + e.__class__.__name__  + " - " + str(e),file=stderr)
                        if not self.ignoreerrors:
                            raise
        for d in glob.glob(self.corpusdir+"/*"):
            if (not self.restrict_to_collection or self.restrict_to_collection == os.path.basename(d)) and (os.path.isdir(d)):
                for f in glob.glob(d+ "/*." + self.extension):
                    if self.conditionf(f):
                        try:
                            yield f
                        except Exception as e:
                            print("Error, unable to parse " + f+ ": " + e.__class__.__name__  + " - " + str(e),file=stderr)
                            if not self.ignoreerrors:
                                raise





class CorpusProcessor(object):
    """Processes a corpus of various FoLiA documents using a parallel processing. Calls a user-defined function with the three-tuple (filename, args, kwargs) for each file in the corpus. The user-defined function is itself responsible for instantiating a FoLiA document! args and kwargs, as received by the custom function, are set through the run() method, which yields the result of the custom function on each iteration."""

    def __init__(self,corpusdir, function, threads = None, extension = 'xml', restrict_to_collection = "", conditionf=lambda x: True, maxtasksperchild=100, preindex = False, ordered=True, chunksize = 1):
        self.function = function
        self.threads = threads #If set to None, will use all available cores by default
        self.corpusdir = corpusdir
        self.extension = extension
        self.restrict_to_collection = restrict_to_collection
        self.conditionf = conditionf
        self.ignoreerrors = True
        self.maxtasksperchild = maxtasksperchild #This should never be set too high due to lxml leaking memory!!!
        self.preindex = preindex
        self.ordered = ordered
        self.chunksize = chunksize
        if preindex:
            self.index = list(CorpusFiles(self.corpusdir, self.extension, self.restrict_to_collection, self.conditionf, True))
            self.index.sort()


    def __len__(self):
        if self.preindex:
            return len(self.index)
        else:
            return ValueError("Can only retrieve length if instantiated with preindex=True")

    def execute(self):
        for output in self.run():
            pass

    def run(self, *args, **kwargs):
        if not self.preindex:
            self.index = CorpusFiles(self.corpusdir, self.extension, self.restrict_to_collection, self.conditionf, True) #generator
        pool = multiprocessing.Pool(self.threads,None,None, self.maxtasksperchild)
        if self.ordered:
            return pool.imap( self.function,  ( (filename, args, kwargs) for filename in self.index), self.chunksize)
        else:
            return pool.imap_unordered( self.function,  ( (filename, args, kwargs) for filename in self.index), self.chunksize)
        #pool.close()



    def __iter__(self):
        return self.run()



class SetType:
    CLOSED, OPEN, MIXED = range(3)

class AbstractDefinition(object):
    pass

class ConstraintDefinition(object):
    def __init__(self, id,  restrictions = {}, exceptions = {}):
        self.id = id
        self.restrictions = restrictions
        self.exceptions = exceptions

    @classmethod
    def parsexml(Class, node, constraintindex):
        global NSFOLIA
        assert node.tag == '{' + NSFOLIA + '}constraint'

        if 'ref' in node.attrib:
            try:
                return constraintindex[node.attrib['ref']]
            except KeyError:
                raise KeyError("Unresolvable constraint: " + node.attrib['ref'])



        restrictions = []
        exceptions = []
        for subnode in node:
            if subnode.tag == '{' + NSFOLIA + '}restrict':
                if 'subset' in subnode.attrib:
                    restrictions.append( (subnode.attrib['subset'], subnode.attrib['class']) )
                else:
                    restrictions.append( (None, subnode.attrib['class']) )
            elif subnode.tag == '{' + NSFOLIA + '}except':
                if 'subset' in subnode.attrib:
                    exceptions.append( (subnode.attrib['subset'], subnode.attrib['class']) )
                else:
                    exceptions.append( (None, subnode.attrib['class']) )

        if '{http://www.w3.org/XML/1998/namespace}id' in node.attrib:
            id = node.attrib['{http://www.w3.org/XML/1998/namespace}id']
            instance = ConstraintDefinition(id, restrictions,exceptions)
            constraintindex[id] = instance
        else:
            instance = ConstraintDefinition(None, restrictions,exceptions)
        return instance


    def json(self):
        return {'id': self.id} #TODO: Implement

class ClassDefinition(AbstractDefinition):
    def __init__(self,id, label, constraints=[]):
        self.id = id
        self.label = label
        self.constraints = constraints

    @classmethod
    def parsexml(Class, node, constraintindex):
        global NSFOLIA
        assert node.tag == '{' + NSFOLIA + '}class'
        if 'label' in node.attrib:
            label = node.attrib['label']
        else:
            label = ""

        constraints = []
        for subnode in node:
            if subnode.tag == '{' + NSFOLIA + '}constraint':
                constraints.append( ConstraintDefinition.parsexml(subnode, constraintindex) )
            elif subnode.tag[:len(NSFOLIA) +2] == '{' + NSFOLIA + '}':
                raise Exception("Invalid tag in Class definition: " + subnode.tag)

        return ClassDefinition(node.attrib['{http://www.w3.org/XML/1998/namespace}id'],label, constraints)

    def json(self):
        jsonnode = {'id': self.id, 'label': self.label}
        jsonnode['constraints'] = []
        for constraint in self.constraints:
            jsonnode['constaints'].append(constraint.json())
        return jsonnode

class SubsetDefinition(AbstractDefinition):
    def __init__(self, id, type, classes = [], constraints = []):
        self.id = id
        self.type = type
        self.classes = classes
        self.constraints = constraints

    @classmethod
    def parsexml(Class, node, constraintindex= {}):
        global NSFOLIA
        assert node.tag == '{' + NSFOLIA + '}subset'

        if 'type' in node.attrib:
            if node.attrib['type'] == 'open':
                type = SetType.OPEN
            elif node.attrib['type'] == 'closed':
                type = SetType.CLOSED
            elif node.attrib['type'] == 'mixed':
                type = SetType.MIXED
            else:
                raise Exception("Invalid set type: ", type)
        else:
            type = SetType.MIXED

        classes = []
        constraints = []
        for subnode in node:
            if subnode.tag == '{' + NSFOLIA + '}class':
                classes.append( ClassDefinition.parsexml(subnode, constraintindex) )
            elif subnode.tag == '{' + NSFOLIA + '}constraint':
                constraints.append( ConstraintDefinition.parsexml(subnode, constraintindex) )
            elif subnode.tag[:len(NSFOLIA) +2] == '{' + NSFOLIA + '}':
                raise Exception("Invalid tag in Set definition: " + subnode.tag)

        return SubsetDefinition(node.attrib['{http://www.w3.org/XML/1998/namespace}id'],type,classes, constraints)


    def json(self):
        jsonnode = {'id': self.id}
        if self.type == SetType.OPEN:
            jsonnode['type'] = 'open'
        elif self.type == SetType.CLOSED:
            jsonnode['type'] = 'closed'
        elif self.type == SetType.MIXED:
            jsonnode['type'] = 'mixed'
        jsonnode['constraints'] = []
        for constraint in self.constraints:
            jsonnode['constraints'].append(constraint.json())
        jsonnode['classes'] = {}
        for c in self.classes:
            jsonnode['classes'][c.id] = c.json()
        return jsonnode

class SetDefinition(AbstractDefinition):
    def __init__(self, id, type, classes = [], subsets = [], constraintindex = {}):
        isncname(id)
        self.id = id
        self.type = type
        self.classes = classes
        self.subsets = subsets
        self.constraintindex = constraintindex


    @classmethod
    def parsexml(Class, node):
        global NSFOLIA
        assert node.tag == '{' + NSFOLIA + '}set'
        classes = []
        subsets= []
        constraintindex = {}
        if 'type' in node.attrib:
            if node.attrib['type'] == 'open':
                type = SetType.OPEN
            elif node.attrib['type'] == 'closed':
                type = SetType.CLOSED
            elif node.attrib['type'] == 'mixed':
                type = SetType.MIXED
            else:
                raise Exception("Invalid set type: ", type)
        else:
            type = SetType.MIXED

        for subnode in node:
            if subnode.tag == '{' + NSFOLIA + '}class':
                classes.append( ClassDefinition.parsexml(subnode, constraintindex) )
            elif subnode.tag == '{' + NSFOLIA + '}subset':
                subsets.append( ClassDefinition.parsexml(subnode, constraintindex) )
            elif subnode.tag[:len(NSFOLIA) +2] == '{' + NSFOLIA + '}':
                raise SetDefinitionError("Invalid tag in Set definition: " + subnode.tag)

        return SetDefinition(node.attrib['{http://www.w3.org/XML/1998/namespace}id'],type,classes, subsets, constraintindex)

    def testclass(self,cls):
        raise NotImplementedError #TODO, IMPLEMENT!

    def testsubclass(self, cls, subset, subclass):
        raise NotImplementedError #TODO, IMPLEMENT!

    def json(self):
        jsonnode = {'id': self.id}
        if self.type == SetType.OPEN:
            jsonnode['type'] = 'open'
        elif self.type == SetType.CLOSED:
            jsonnode['type'] = 'closed'
        elif self.type == SetType.MIXED:
            jsonnode['type'] = 'mixed'
        jsonnode['subsets'] = {}
        for subset in self.subsets:
            jsonnode['subsets'][subset.id] = subset.json()
        jsonnode['classes'] = {}
        for c in self.classes:
            jsonnode['classes'][c.id] = c.json()
        return jsonnode



def loadsetdefinition(filename):
    global NSFOLIA
    if filename[0] == '/' or filename[0] == '.':
        tree = ElementTree.parse(filename)
    else:
        try:
            f = urlopen(filename)
        except:
            raise DeepValidationError("Unable to download " + filename)
        try:
            tree = xmltreefromstring(u(f.read()))
        except IOError:
            raise DeepValidationError("Unable to download " + filename)
        f.close()
    root = tree.getroot()
    if root.tag != '{' + NSFOLIA + '}set':
        raise SetDefinitionError("Not a FoLiA Set Definition! Unexpected root tag:"+ root.tag)

    return SetDefinition.parsexml(root)


def relaxng_declarations():
    global NSFOLIA
    E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': NSFOLIA, 'xml' : "http://www.w3.org/XML/1998/namespace"})
    for key, value in vars(AnnotationType).items():
        if key[0] != '_':
            yield E.element( E.optional( E.attribute(name='set')) , E.optional(E.attribute(name='annotator')) , E.optional( E.attribute(name='annotatortype') ) , E.optional( E.attribute(name='datetime') )  , name=key.lower() + '-annotation')


def relaxng(filename=None):
    global NSFOLIA, LXE
    E = ElementMaker(namespace="http://relaxng.org/ns/structure/1.0",nsmap={None:'http://relaxng.org/ns/structure/1.0' , 'folia': NSFOLIA, 'xml' : "http://www.w3.org/XML/1998/namespace"})
    grammar = E.grammar( E.start ( E.element( #FoLiA
                E.attribute(name='id',ns="http://www.w3.org/XML/1998/namespace"),
                E.optional( E.attribute(name='version') ),
                E.optional( E.attribute(name='generator') ),
                E.element( #metadata
                    E.optional(E.attribute(name='type')),
                    E.optional(E.attribute(name='src')),
                    E.element( E.zeroOrMore( E.choice( *relaxng_declarations() ) ) ,name='annotations'),
                    E.zeroOrMore(
                        E.element(E.attribute(name='id'), E.text(), name='meta'),
                    ),
                    #E.optional(
                    #    E.ref(name='METATRANSCRIPT')
                    #),
                    name='metadata',
                    #ns=NSFOLIA,
                ),
                E.oneOrMore(
                    E.ref(name='text'),
                ),
                name='FoLiA',
                ns = NSFOLIA
            ) ),
            )

    done = {}
    for c in globals().values():
        if 'relaxng' in dir(c):
            if c.relaxng and c.XMLTAG and not c.XMLTAG in done:
                done[c.XMLTAG] = True
                grammar.append( c.relaxng() )

    #for e in relaxng_imdi():
    #    grammar.append(e)
    if filename:
        f = io.open(filename,'w',encoding='utf-8')
        if LXE:
            f.write( ElementTree.tostring(relaxng(),pretty_print=True).replace("</define>","</define>\n\n") )
        else:
            f.write( ElementTree.tostring(relaxng()).replace("</define>","</define>\n\n") )
        f.close()

    return grammar



def findwords(doc, worditerator, *args, **kwargs):
        if 'leftcontext' in kwargs:
            leftcontext = int(kwargs['leftcontext'])
            del kwargs['leftcontext']
        else:
            leftcontext = 0
        if 'rightcontext' in kwargs:
            rightcontext =  int(kwargs['rightcontext'])
            del kwargs['rightcontext']
        else:
            rightcontext = 0
        if 'maxgapsize' in kwargs:
            maxgapsize = int(kwargs['maxgapsize'])
            del kwargs['maxgapsize']
        else:
            maxgapsize = 10
        for key in kwargs.keys():
            raise Exception("Unknown keyword parameter: " + key)

        matchcursor = 0
        matched = []

        #shortcut for when no Pattern is passed, make one on the fly
        if len(args) == 1 and not isinstance(args[0], Pattern):
            if not isinstance(args[0], list) and not isinstance(args[0], tuple):
                args[0] = [args[0]]
            args[0] = Pattern(*args[0])



        unsetwildcards = False
        variablewildcards = None
        prevsize = -1
        minsize = 99999
        #sanity check
        for i, pattern in enumerate(args):
            if not isinstance(pattern, Pattern):
                raise TypeError("You must pass instances of Sequence to findwords")
            if prevsize > -1 and len(pattern) != prevsize:
                raise Exception("If multiple patterns are provided, they must all have the same length!")
            if pattern.variablesize():
                if not variablewildcards and i > 0:
                    unsetwildcards = True
                else:
                    if variablewildcards and pattern.variablewildcards() != variablewildcards:
                        raise Exception("If multiple patterns are provided with variable wildcards, then these wildcards must all be in the same positions!")
                    variablewildcards = pattern.variablewildcards()
            elif variablewildcards:
                unsetwildcards = True
            prevsize = len(pattern)

        if unsetwildcards:
            #one pattern determines a fixed length whilst others are variable, rewrite all to fixed length
            #converting multi-span * wildcards into single-span 'True' wildcards
            for pattern in args:
                if pattern.variablesize():
                    pattern.sequence = [ True if x == '*' else x for x in pattern.sequence ]
            variablesize = False

        if variablewildcards:
            #one or more items have a * wildcard, which may span multiple tokens. Resolve this to a wider range of simpler patterns

            #we're not commited to a particular size, expand to various ones
            for size in range(len(variablewildcards), maxgapsize+1):
                for distribution in  pynlpl.algorithms.sum_to_n(size, len(variablewildcards)): #gap distributions, (amount) of 'True' wildcards
                    patterns = []
                    for pattern in args:
                        if pattern.variablesize():
                            patterns += list(pattern.resolve(size,distribution))
                        else:
                            patterns.append( pattern )
                    for match in findwords(doc, worditerator,*patterns, **{'leftcontext':leftcontext,'rightcontext':rightcontext}):
                        yield match

        else:
            patterns = args
            buffers = []

            for word in worditerator():
                buffers.append( [] ) #Add a new empty buffer for every word
                match = [None] * len(buffers)
                for pattern in patterns:
                    #find value to match against
                    if not pattern.matchannotation:
                        value = word.text()
                    else:
                        if pattern.matchannotationset:
                            items = word.select(pattern.matchannotation, pattern.matchannotationset, True, [Original, Suggestion, Alternative])
                        else:
                            try:
                                set = doc.defaultset(pattern.matchannotation.ANNOTATIONTYPE)
                                items = word.select(pattern.matchannotation, set, True, [Original, Suggestion, Alternative] )
                            except KeyError:
                                continue
                        if len(items) == 1:
                            value = items[0].cls
                        else:
                            continue

                    if not pattern.casesensitive:
                        value = value.lower()


                    for i, buffer in enumerate(buffers):
                        if match[i] is False:
                            continue
                        matchcursor = len(buffer)
                        if (value == pattern.sequence[matchcursor] or pattern.sequence[matchcursor] is True or (isinstance(pattern.sequence[matchcursor], tuple) and value in pattern.sequence[matchcursor])):
                            match[i] = True
                        else:
                            match[i] = False


                for buffer, matches in list(zip(buffers, match)):
                    if matches:
                        buffer.append(word) #add the word
                        if len(buffer) == len(pattern.sequence):
                            yield buffer[0].leftcontext(leftcontext) + buffer + buffer[-1].rightcontext(rightcontext)
                            buffers.remove(buffer)
                    else:
                        buffers.remove(buffer) #remove buffer

class Reader(object):
    """Streaming FoLiA reader. The reader allows you to read a FoLiA Document without holding the whole tree structure in memory. The document will be read and the elements you seek returned as they are found. If you are querying a corpus of large FoLiA documents for a specific structure, then it is strongly recommend to use the Reader rather than the standard Document!"""


    def __init__(self, filename, target, *args, **kwargs):
        """Read a FoLiA document in a streaming fashion. You select a specific target element and all occurrences of this element, including all  contents (so all elements within), will be returned.

        Arguments:

            * ``filename``: The filename of the document to read
            * ``target``: The FoLiA element you want to read, passed as a class. For example: ``folia.Sentence``.
            * ``bypassleak'': Boolean indicating whether to bypass a memory leak in lxml. Set this to true if you are processing a large number of files sequentially! This comes at the cost of a higher memory footprint, as the raw contents of the file, as opposed to the tree structure, *will* be loaded in memory.

        """

        self.target = target
        if not issubclass(self.target, AbstractElement):
            raise ValueError("Target must be subclass of FoLiA element")
        if 'bypassleak' in kwargs:
            self.bypassleak = bool(kwargs['bypassleak'])
        else:
            self.bypassleak = True

        self.openstream(filename)
        self.initdoc()



    def findwords(self, *args, **kwargs):
        self.target = Word
        for x in findwords(self.doc,self.__iter__,*args,**kwargs):
            yield x

    def openstream(self, filename):
        if sys.version < '3' or not self.bypassleak:
            self.stream = io.open(filename,'rb') #no bypassleak!!!!
        elif self.bypassleak:
            self.stream = BypassLeakFile(filename,'rb')

    def initdoc(self):
        self.doc = None
        metadata = False
        parser = ElementTree.iterparse(self.stream, events=("start","end"))
        for action, node in parser:
            if action == "start" and node.tag == "{" + NSFOLIA + "}FoLiA":
                if '{http://www.w3.org/XML/1998/namespace}id' in node.attrib:
                    id = node.attrib['{http://www.w3.org/XML/1998/namespace}id']
                else:
                    id = node.attrib['id']
                self.doc = Document(id=id)
                if 'version' in node.attrib:
                    self.doc.version = node.attrib['version']
            if action == "end" and node.tag == "{" + NSFOLIA + "}metadata":
                if not self.doc:
                    raise MalformedXMLError("Metadata found, but no document? Impossible")
                metadata = True
                self.doc.parsemetadata(node)
                break

        if not self.doc:
            raise MalformedXMLError("No FoLiA Document found!")
        elif not metadata:
            raise MalformedXMLError("No metadata found!")

        self.stream.seek(0) #reset

    def __iter__(self):
        """Iterating over a Reader instance will cause the FoLiA document to be read. This is a generator yielding instances of the object you specified"""

        parser = ElementTree.iterparse(self.stream, events=("end",), tag="{" + NSFOLIA + "}" + self.target.XMLTAG  )
        for action, node in parser:
            element = self.target.parsexml(node, self.doc)
            node.clear() #clean up children
            while node.getprevious() is not None:
                del node.getparent()[0]  # clean up preceding siblings
            yield element

        self.stream.close()


#class WordIndexer(object):
#    def __init__(self, doc, *args, **kwargs)
#        self.doc = doc
#
#    def __iter__(self):
#
#
#    def savecsv(self, filename):
#
#
#    def savesql(self, filename):
# in-place prettyprint formatter

def isncname(name):
    #not entirely according to specs http://www.w3.org/TR/REC-xml/#NT-Name , but simplified:
    for i, c in enumerate(name):
        if i == 0:
            if not c.isalpha():
                raise ValueError('Invalid XML NCName identifier: ' + name + ' (at position ' + str(i+1)+')')
        else:
            if not c.isalnum() and not (c in ['-','_','.']):
                raise ValueError('Invalid XML NCName identifier: ' + name + ' (at position ' + str(i+1)+')')
    return True



def validate(filename,schema=None,deep=False):
    if not os.path.exists(filename):
        raise IOError("No such file")

    try:
        doc = ElementTree.parse(filename)
    except:
        raise MalformedXMLError("Malformed XML!")

    #See if there's inline IMDI and strip it off prior to validation (validator doesn't do IMDI)
    m = doc.xpath('//folia:metadata', namespaces={'f': 'http://ilk.uvt.nl/folia','folia': 'http://ilk.uvt.nl/folia' })
    if m:
        metadata = m[0]
        m = metadata.find('{http://www.mpi.nl/IMDI/Schema/IMDI}METATRANSCRIPT')
        if m is not None:
            metadata.remove(m)

    if not schema:
        schema = ElementTree.RelaxNG(relaxng())


    schema.assertValid(doc) #will raise exceptions

    if deep:
        doc = Document(tree=doc, deepvalidation=True)

XML2CLASS = {}
ANNOTATIONTYPE2CLASS = {}
ANNOTATIONTYPE2XML = {}
ANNOTATIONTYPE2LAYERCLASS = {}
for c in list(vars().values()):
    try:
        if c.XMLTAG:
            XML2CLASS[c.XMLTAG] = c
            if c.ROOTELEMENT:
                ANNOTATIONTYPE2CLASS[c.ANNOTATIONTYPE] = c
                ANNOTATIONTYPE2XML[c.ANNOTATIONTYPE] = c.XMLTAG
            if isinstance(c,AbstractAnnotationLayer):
                ANNOTATIONTYPE2LAYERCLASS[c.ANNOTATIONTYPE] = c
    except:
        continue

defaultignorelist = [Original,Suggestion,Alternative, AlternativeLayers]
#default ignore list for token annotation
defaultignorelist_annotations = [Original,Suggestion,Alternative, AlternativeLayers,MorphologyLayer]
defaultignorelist_structure = [Original,Suggestion,Alternative, AlternativeLayers,AbstractAnnotationLayer]

########NEW FILE########
__FILENAME__ = giza
# -*- coding: utf-8 -*-

###############################################################
#  PyNLPl - WordAlignment Library for reading GIZA++ A3 files
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#
#       In part using code by Sander Canisius
#
#       Licensed under GPLv3
#
#
# This library reads GIZA++ A3 files. It contains three classes over which
# you can iterate to obtain (sourcewords,targetwords,alignment) pairs.
#
#   - WordAlignment  - Reads target-source.A3.final files, in which each source word is aligned to one target word
#   - MultiWordAlignment  - Reads source-target.A3.final files, in which each source word may be aligned to multiple target target words
#   - IntersectionAlignment  - Computes the intersection between the above two alignments
#
#
###############################################################

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from pynlpl.common import u

import bz2
import gzip
import copy
import io
from sys import stderr

class GizaSentenceAlignment(object):

    def __init__(self, sourceline, targetline, index):
        self.index = index
        self.alignment = []
        if sourceline:
            self.source = self._parsesource(sourceline.strip())
        else:
            self.source = []
        self.target = targetline.strip().split(' ')

    def _parsesource(self, line):
        cleanline = ""

        inalignment = False
        begin = 0
        sourceindex = 0

        for i in range(0,len(line)):
            if line[i] == ' ' or i == len(line) - 1:
                if i == len(line) - 1:
                    offset = 1
                else:
                    offset = 0

                word = line[begin:i+offset]
                if word == '})':
                    inalignment = False
                    begin = i + 1
                    continue
                elif word == "({":
                    inalignment = True
                    begin = i + 1
                    continue
                if word.strip() and word != 'NULL':
                    if not inalignment:
                        sourceindex += 1
                        if cleanline: cleanline += " "
                        cleanline += word
                    else:
                        targetindex = int(word)
                        self.alignment.append( (sourceindex-1, targetindex-1) )
                begin = i + 1

        return cleanline.split(' ')


    def intersect(self,other):
        if other.target != self.source:
            print("GizaSentenceAlignment.intersect(): Mismatch between self.source and other.target: " + repr(self.source) + " -- vs -- " + repr(other.target),file=stderr)
            return None

        intersection = copy.copy(self)
        intersection.alignment = []

        for sourceindex, targetindex in self.alignment:
            for targetindex2, sourceindex2 in other.alignment:
                if targetindex2 == targetindex and sourceindex2 == sourceindex:
                    intersection.alignment.append( (sourceindex, targetindex) )

        return intersection

    def __repr__(self):
        s = " ".join(self.source)+ " ||| "
        s += " ".join(self.target) + " ||| "
        for S,T in sorted(self.alignment):
            s += self.source[S] + "->" + self.target[T] + " ; "
        return s


    def getalignedtarget(self, index):
        """Returns target range only if source index aligns to a single consecutive range of target tokens."""
        targetindices = []
        target = None
        foundindex = -1
        for sourceindex, targetindex in self.alignment:
            if sourceindex == index:
                targetindices.append(targetindex)
        if len(targetindices) > 1:
            for i in range(1,len(targetindices)):
                if abs(targetindices[i] - targetindices[i-1]) != 1:
                    break  # not consecutive
            foundindex = (min(targetindices), max(targetindices))
            target = ' '.join(self.target[min(targetindices):max(targetindices)+1])
        elif targetindices:
            foundindex = targetindices[0]
            target = self.target[foundindex]

        return target, foundindex

class GizaModel(object):
    def __init__(self, filename, encoding= 'utf-8'):
        if filename.split(".")[-1] == "bz2":
            self.f = bz2.BZ2File(filename,'r')
        elif filename.split(".")[-1] == "gz":
            self.f = gzip.GzipFile(filename,'r')
        else:
            self.f = io.open(filename,'r',encoding=encoding)
        self.nextlinebuffer = None


    def __iter__(self):
        self.f.seek(0)
        nextlinebuffer = u(next(self.f))
        sentenceindex = 0

        done = False
        while not done:
            sentenceindex += 1
            line = nextlinebuffer
            if line[0] != '#':
                raise Exception("Error parsing GIZA++ Alignment at sentence " +  str(sentenceindex) + ", expected new fragment, found: " + repr(line))

            targetline = u(next(self.f))
            sourceline = u(next(self.f))

            yield GizaSentenceAlignment(sourceline, targetline, sentenceindex)

            try:
                nextlinebuffer = u(next(self.f))
            except StopIteration:
                done = True


    def __del__(self):
        if self.f: self.f.close()


#------------------ OLD -------------------

def parseAlignment(tokens): #by Sander Canisius
    assert tokens.pop(0) == "NULL"
    while tokens.pop(0) != "})":
        pass

    while tokens:
        word = tokens.pop(0)
        assert tokens.pop(0) == "({"
        positions = []
        token = tokens.pop(0)
        while token != "})":
            positions.append(int(token))
            token = tokens.pop(0)

        yield word, positions


class WordAlignment:
    """Target to Source alignment: reads target-source.A3.final files, in which each source word is aligned to one target word"""

    def __init__(self,filename, encoding=False):
        """Open a target-source GIZA++ A3 file. The file may be bzip2 compressed. If an encoding is specified, proper unicode strings will be returned"""

        if filename.split(".")[-1] == "bz2":
            self.stream = bz2.BZ2File(filename,'r')
        else:
            self.stream = open(filename)
        self.encoding = encoding


    def __del__(self):
        self.stream.close()

    def __iter__(self): #by Sander Canisius
        line = self.stream.readline()
        while line:
            assert line.startswith("#")
            src = self.stream.readline().split()
            trg = []
            alignment = [None for i in xrange(len(src))]

            for i, (targetWord, positions) in enumerate(parseAlignment(self.stream.readline().split())):

                trg.append(targetWord)

                for pos in positions:
                    assert alignment[pos - 1] is None
                    alignment[pos - 1] = i

            if self.encoding:
                yield [ u(w,self.encoding) for w in src ], [ u(w,self.encoding) for w in trg ], alignment
            else:
                yield src, trg, alignment

            line = self.stream.readline()


    def targetword(self, index, targetwords, alignment):
        """Return the aligned targetword for a specified index in the source words"""
        if alignment[index]:
            return targetwords[alignment[index]]
        else:
            return None

    def reset(self):
        self.stream.seek(0)

class MultiWordAlignment:
    """Source to Target alignment: reads source-target.A3.final files, in which each source word may be aligned to multiple target words (adapted from code by Sander Canisius)"""

    def __init__(self,filename, encoding = False):
        """Load a target-source GIZA++ A3 file. The file may be bzip2 compressed. If an encoding is specified, proper unicode strings will be returned"""

        if filename.split(".")[-1] == "bz2":
            self.stream = bz2.BZ2File(filename,'r')
        else:
            self.stream = open(filename)
        self.encoding = encoding

    def __del__(self):
        self.stream.close()

    def __iter__(self):
        line = self.stream.readline()
        while line:
            assert line.startswith("#")
            trg = self.stream.readline().split()
            src = []
            alignment = []

            for i, (word, positions) in enumerate(parseAlignment(self.stream.readline().split())):
                src.append(word)
                alignment.append( [ p - 1 for p in positions ] )


            if self.encoding:
                yield [ unicode(w,self.encoding) for w in src ], [ unicode(w,self.encoding) for w in trg ], alignment
            else:
                yield src, trg, alignment

            line = self.stream.readline()

    def targetword(self, index, targetwords, alignment):
        """Return the aligned targeword for a specified index in the source words. Multiple words are concatenated together with a space in between"""
        return " ".join(targetwords[alignment[index]])

    def targetwords(self, index, targetwords, alignment):
        """Return the aligned targetwords for a specified index in the source words"""
        return [ targetwords[x] for x in alignment[index] ]

    def reset(self):
        self.stream.seek(0)


class IntersectionAlignment:

    def __init__(self,source2target,target2source,encoding=False):
        self.s2t = MultiWordAlignment(source2target, encoding)
        self.t2s = WordAlignment(target2source, encoding)
        self.encoding = encoding

    def __iter__(self):
        for (src, trg, alignment), (revsrc, revtrg, revalignment) in zip(self.s2t,self.t2s): #will take unnecessary memory in Python 2.x, optimal in Python 3
            if src != revsrc or trg != revtrg:
                raise Exception("Files are not identical!")
            else:
                #keep only those alignments that are present in both
                intersection = []
                for i, x in enumerate(alignment):
                    if revalignment[i] and revalignment[i] in x:
                        intersection.append(revalignment[i])
                    else:
                        intersection.append(None)

                yield src, trg, intersection

    def reset(self):
        self.s2t.reset()
        self.t2s.reset()


########NEW FILE########
__FILENAME__ = imdi
RELAXNG_IMDI = """
<!--
	XML Schema for IMDI
	
	Version 3.0.13
	
	Max-Planck Institute for Psycholinguistics
-->
<!--
	
3.0.15, 2009-11-17, Alexander Koenig
	in session
	Changed maxOccurs for the Content fields SubGenre, Task, Modalities and Subject from unbounded to 1

3.0.14, 2009-08-17, Dieter Van Uytvanck
	Addition of an optional CatalogueHandle attribute to Corpus

3.0.13, 2009-08-06, Evelyn Richter
	In catalogue
	Allowed projects to occur multiple times because one corpus could be collected from different projects (decision with Paul Trilsbeek)
	
3.0.12, 2009-07-13, Evelyn Richter
	In catalogue
	Deleted BeginYear and EndYear elements, data to be put into Date element in format YYYY/YYYY (decision with Daan Broeder)
	Changed Authors element to "Author" in the singular (not compatible with 3-4 existing catalogue files, users have to be informed, decision with Daan Broeder)
	Allowed multiple Publisher elements (decision with Dieter van Uytvanck)
	Allowed multiple author elements (decision with Daan Broeder)
	Added Image as subelement of Format (decision with Paul Trilsbeek)
	Added Text and Image as subelements of Quality (decision with Daan Broeder)

3.0.11, 2009-06-18, Peter Withers
	In session
	Added Link, DefaultLink and Type attributes to Boolean_Type

3.0.10, 2009-06-15, Evelyn Richter
	In catalogue
	Allowed multiple content types and multiple locations and 
	added elements "ContactPerson", "BeginYear", "EndYear", 
	"ReferenceLink", "MetadataLink", "Publications" in Catalogue 
	schema to accommodate for CLARIN resources 
	(multiple resource types and countries possible for CLARIN resources,
	frequent occurrence of information for which elements were created)
	Allowed multiple publisher elements in catalogue after discussion with Dieter van Uytvanck

3.0.9, 2009-04-17
	made ISO-3 language codes possible

3.0.8, 2008-08-05, Daan Broeder
	In lexicon resource  en lexicon component
	removed schema reference 
	made description in Lexiconresource optional
	made description in MetaLanguages optional
	made language in MetaLanguages optional

3.0.7, 2008-03-04, Jacquelijn Ringersma
	In lexicon resource bundle 
	MediaResourceLink vervangen door ReferenceResourceLink
	en Multiple schemareferences mogelijk gemaakt 	

-->
<rng:grammar xmlns:rng="http://relaxng.org/ns/structure/1.0" xmlns:a="http://relaxng.org/ns/compatibility/annotations/1.0" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:imdi="http://www.mpi.nl/IMDI/Schema/IMDI" ns="http://www.mpi.nl/IMDI/Schema/IMDI" datatypeLibrary="http://www.w3.org/2001/XMLSchema-datatypes">
	<!-- 
		Main schema
	-->
	<rng:start combine="choice">
<rng:ref name="METATRANSCRIPT"/>
</rng:start>
<rng:define name="METATRANSCRIPT">
<rng:element name="METATRANSCRIPT">
<rng:ref name="METATRANSCRIPT_Type"/>
		<a:documentation>
			The root element for IMDI descriptions
		</a:documentation>
	</rng:element>
</rng:define>
	<!-- 
		Schema for vocabulary definition
	-->
	<rng:start combine="choice">
<rng:ref name="VocabularyDef"/>
</rng:start>
<rng:define name="VocabularyDef">
<rng:element name="VocabularyDef">
<rng:ref name="VocabularyDef_Type"/>
		<a:documentation>
			Instantiation of a VocabularyDef_Type
		</a:documentation>
	</rng:element>
</rng:define>
	<!-- 
		METATRANSCRIPT
	-->
	<rng:define name="METATRANSCRIPT_Type">
		
			<rng:optional>
<rng:element name="History">
<rng:ref name="String_Type"/>
				<a:documentation>
					Revision history of the metadata description
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:choice>
				<rng:oneOrMore>
<rng:element name="Session">
<rng:ref name="Session_Type"/>
</rng:element>
</rng:oneOrMore>
				<rng:oneOrMore>
<rng:element name="Corpus">
<rng:ref name="Corpus_Type"/>
</rng:element>
</rng:oneOrMore>
				<rng:element name="Catalogue">
<rng:ref name="Catalogue_Type"/>
</rng:element>
			</rng:choice>
		
		<rng:optional>
<rng:attribute name="Profile">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:attribute name="Date">
<rng:data type="date"/>
</rng:attribute>
		<rng:optional>
<rng:attribute name="Originator">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:attribute name="Version">
<rng:data type="string"/>
</rng:attribute>
		<rng:attribute name="FormatId">
<rng:data type="string"/>
</rng:attribute>
		<rng:optional>
<rng:attribute name="History">
<rng:data type="anyURI"/>
</rng:attribute>
</rng:optional>
		<rng:attribute name="Type">
<rng:ref name="Metatranscript_Value_Type"/>
</rng:attribute>
		<rng:optional>
<rng:attribute name="ArchiveHandle">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Location
	-->
	<rng:define name="Location_Type">
		<a:documentation>
			Information on creation location for this data
		</a:documentation>
		
			<rng:element name="Continent">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The name of a continent
				</a:documentation>
			</rng:element>
			<rng:element name="Country">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The name of a country
				</a:documentation>
			</rng:element>
			<rng:zeroOrMore>
<rng:element name="Region">
<rng:ref name="String_Type"/>
				<a:documentation>
					The name of a geographic region
				</a:documentation>
			</rng:element>
</rng:zeroOrMore>
			<rng:optional>
<rng:element name="Address">
<rng:ref name="String_Type"/>
				<a:documentation>
					The address
				</a:documentation>
			</rng:element>
</rng:optional>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!--
		Key
	-->
	<rng:define name="Key_Type">
		
			
				<rng:attribute name="Name">
<rng:data type="string"/>
</rng:attribute>
			
		
	</rng:define>
	<!-- 
		Keys
	-->
	<rng:define name="Keys_Type">
		<a:documentation>
			List of a number of key name value pairs. Should be used to add information that is not covered by other metadata elements at this level
		</a:documentation>
		
			<rng:zeroOrMore>
<rng:element name="Key">
<rng:ref name="Key_Type"/>
</rng:element>
</rng:zeroOrMore>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Languages
	-->
	<rng:define name="Languages_Type">
		<a:documentation>
			Groups information about the languages used in the session
		</a:documentation>
		
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
				<a:documentation>
					Description for the list of languages spoken by this participant
				</a:documentation>
			</rng:element>
</rng:zeroOrMore>
			<rng:zeroOrMore>
<rng:element name="Language">
<rng:ref name="Language_Type"/>
</rng:element>
</rng:zeroOrMore>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!--
		Access
	-->
	<rng:define name="Access_Type">
		<a:documentation>
			Groups information about access rights for this data
		</a:documentation>
		
			<rng:element name="Availability">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					Availability of the data
				</a:documentation>
			</rng:element>
			<rng:element name="Date">
<rng:ref name="Date_Type"/>
				<a:documentation>
					Date when access rights were evaluated
				</a:documentation>
			</rng:element>
			<rng:element name="Owner">
<rng:ref name="String_Type"/>
				<a:documentation>
					Name of owner resource
				</a:documentation>
			</rng:element>
			<rng:element name="Publisher">
<rng:ref name="String_Type"/>
				<a:documentation>
					Publisher responsible for distribution of this data
				</a:documentation>
			</rng:element>
			<rng:element name="Contact">
<rng:ref name="Contact_Type"/>
</rng:element>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
</rng:element>
</rng:zeroOrMore>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		External Resource Reference
	-->
	<rng:define name="ExternalResourceReference_Type">
		<a:documentation>
			Resource is preferably a metadata resource. In the case of a well-defined merged metadata/content format such as TEI or legacy resources for which no further metadata is available it is the resource itself. If the external resource is an IMDI session with written resources Type &amp; SubType will be the same as the Type &amp; SubType of the primary written resource in that session. If it is a session with IMDI multi-media resources the Type of the Media
				File will designate it. SubType is used only for written resources. Non-IMDI metadata resource types need to be mapped to IMDI types
		</a:documentation>
		
			<rng:element name="Type">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The type of the external (metadata) resource
				</a:documentation>
			</rng:element>
			<rng:optional>
<rng:element name="SubType">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The sub type of the external (metadata) resource. Only used in case its metadata for a written resource
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:element name="Format">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The metadata format
				</a:documentation>
			</rng:element>
			<rng:element name="Link">
<rng:data type="anyURI">
				<a:documentation>
					The URL of the external metadata record
				</a:documentation>
			</rng:data>
</rng:element>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Project
	-->
	<rng:define name="Project_Type">
		<a:documentation>
			Project Information
		</a:documentation>
		
			<rng:element name="Name">
<rng:ref name="String_Type"/>
				<a:documentation>
					A short name or abbreviation for the project
				</a:documentation>
			</rng:element>
			<rng:element name="Title">
<rng:ref name="String_Type"/>
				<a:documentation>
					The full title of the project
				</a:documentation>
			</rng:element>
			<rng:element name="Id">
<rng:ref name="String_Type"/>
				<a:documentation>
					A unique identifier for the project
				</a:documentation>
			</rng:element>
			<rng:element name="Contact">
<rng:ref name="Contact_Type"/>
				<a:documentation>
					Contact information for this project
				</a:documentation>
			</rng:element>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
				<a:documentation>
					Description for this project
				</a:documentation>
			</rng:element>
</rng:zeroOrMore>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Metadata Group
	-->
	<rng:define name="MDGroupType">
		<a:documentation>
			Type for group of metadata pertaining to a session
		</a:documentation>
		
			<rng:element name="Location">
<rng:ref name="Location_Type"/>
				<a:documentation>
					Groups information about the location where the session was created
				</a:documentation>
			</rng:element>
			<rng:oneOrMore>
<rng:element name="Project">
<rng:ref name="Project_Type"/>
				<a:documentation>
					Groups information about the project for which the session was (originally) created
				</a:documentation>
			</rng:element>
</rng:oneOrMore>
			<rng:element name="Keys">
<rng:ref name="Keys_Type"/>
				<a:documentation>
					Project keys
				</a:documentation>
			</rng:element>
			<rng:element name="Content">
<rng:ref name="Content_Type"/>
				<a:documentation>
					Groups information about the content of the session. The content description takes place in several (overlapping) dimensions
				</a:documentation>
			</rng:element>
			<rng:element name="Actors">
<rng:ref name="Actors_Type"/>
				<a:documentation>
					Groups information about all actors in the session
				</a:documentation>
			</rng:element>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Content
	-->
	<rng:define name="Content_Type">
		
			<rng:element name="Genre">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					Major genre classification
				</a:documentation>
			</rng:element>
			<rng:optional>
<rng:element name="SubGenre">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					Sub genre classification
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="Task">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					List of he major tasks carried out in the session
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="Modalities">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					List of modalities used in the session
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="Subject">
				<a:documentation>
					Classifies the subject of the session. Uses preferably an existing library classification scheme such as LCSH. The element has a scheme attribute that indicates what scheme is used. Comments: The element can be repeated but the user should guarantee consistency
				</a:documentation>
				
					
						
							
							<rng:attribute name="Encoding">
<rng:data type="string"/>
</rng:attribute>
						
					
				
			</rng:element>
</rng:optional>
			<rng:element name="CommunicationContext">
				<a:documentation>
					This groups information concerning the context of communication
				</a:documentation>
				
					
						<rng:optional>
<rng:element name="Interactivity">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								degree of interactivity
							</a:documentation>
						</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="PlanningType">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								Degree of planning of the event
							</a:documentation>
						</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="Involvement">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								Indicates in how far the researcher was involved in the linguistic event
							</a:documentation>
						</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="SocialContext">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								Indicates the social context the event took place in
							</a:documentation>
						</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="EventStructure">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								Indicates the structure of the communication event
							</a:documentation>
						</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="Channel">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								Indicates the channel of the communication
							</a:documentation>
						</rng:element>
</rng:optional>
					
				
			</rng:element>
			<rng:element name="Languages">
<rng:ref name="Languages_Type"/>
</rng:element>
			<rng:element name="Keys">
<rng:ref name="Keys_Type"/>
</rng:element>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
				<a:documentation>
					Description for the content of this session
				</a:documentation>
			</rng:element>
</rng:zeroOrMore>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Actors
	-->
	<rng:define name="Actors_Type">
		
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
				<a:documentation>
					Description about the actors as a group
				</a:documentation>
			</rng:element>
</rng:zeroOrMore>
			<rng:zeroOrMore>
<rng:element name="Actor">
<rng:ref name="Actor_Type"/>
				<a:documentation>
					Group of actors
				</a:documentation>
			</rng:element>
</rng:zeroOrMore>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Actor
	-->
	<rng:define name="Actor_Type">
		
			<rng:element name="Role">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					Functional role of the actor e.g. consultant, contributor, interviewer, researcher, publisher, collector, translator
				</a:documentation>
			</rng:element>
			<rng:oneOrMore>
<rng:element name="Name">
<rng:ref name="String_Type"/>
				<a:documentation>
					Name of the actor as used by others in the transcription
				</a:documentation>
			</rng:element>
</rng:oneOrMore>
			<rng:element name="FullName">
<rng:ref name="String_Type"/>
				<a:documentation>
					Official name of the actor
				</a:documentation>
			</rng:element>
			<rng:element name="Code">
<rng:ref name="String_Type"/>
				<a:documentation>
					Short unique code to identify the actor as used in the transcription
				</a:documentation>
			</rng:element>
			<rng:element name="FamilySocialRole">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The family social role of the actor
				</a:documentation>
			</rng:element>
			<rng:element name="Languages">
<rng:ref name="Languages_Type"/>
				<a:documentation>
					The actor languages
				</a:documentation>
			</rng:element>
			<rng:element name="EthnicGroup">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The ethnic groups of the actor
				</a:documentation>
			</rng:element>
			<rng:element name="Age">
<rng:ref name="AgeRange_Type"/>
				<a:documentation>
					The age of the actor
				</a:documentation>
			</rng:element>
			<rng:element name="BirthDate">
<rng:ref name="Date_Type"/>
				<a:documentation>
					The birthdate of the actor
				</a:documentation>
			</rng:element>
			<rng:element name="Sex">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The sex of the actor
				</a:documentation>
			</rng:element>
			<rng:element name="Education">
<rng:ref name="String_Type"/>
				<a:documentation>
					The education of the actor
				</a:documentation>
			</rng:element>
			<rng:element name="Anonymized">
<rng:ref name="Boolean_Type"/>
				<a:documentation>
					Indicates if real names or anonymized codes are used to identify the actor
				</a:documentation>
			</rng:element>
			<rng:optional>
<rng:element name="Contact">
<rng:ref name="Contact_Type"/>
				<a:documentation>
					Contact information of the actor
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:element name="Keys">
<rng:ref name="Keys_Type"/>
				<a:documentation>
					Actor keys
				</a:documentation>
			</rng:element>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
				<a:documentation>
					Description for this individual actor
				</a:documentation>
			</rng:element>
</rng:zeroOrMore>
		
		<rng:optional>
<rng:attribute name="ResourceRef">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Corpus
	-->
	<rng:define name="Corpus_Type">
		<a:documentation>
			Type for a corpus that points to either other corpora or sessions
		</a:documentation>
		
			<rng:element name="Name">
<rng:ref name="String_Type"/>
				<a:documentation>
					Name of the (sub-)corpus
				</a:documentation>
			</rng:element>
			<rng:element name="Title">
<rng:ref name="String_Type"/>
				<a:documentation>
					Title for the (sub-)corpus
				</a:documentation>
			</rng:element>
			<rng:oneOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
				<a:documentation>
					Description of the (sub-)corpus
				</a:documentation>
			</rng:element>
</rng:oneOrMore>
			<rng:optional>
<rng:element name="MDGroup">
<rng:ref name="MDGroupType"/>
</rng:element>
</rng:optional>
			<rng:zeroOrMore>
<rng:element name="CorpusLink">
<rng:ref name="CorpusLink_Type"/>
</rng:element>
</rng:zeroOrMore>
		
		<rng:optional>
<rng:attribute name="SearchService">
<rng:data type="anyURI"/>
</rng:attribute>
</rng:optional>
		<rng:optional>
<rng:attribute name="CorpusStructureService">
<rng:data type="anyURI"/>
</rng:attribute>
</rng:optional>
		<rng:optional>
<rng:attribute name="CatalogueLink">
<rng:data type="anyURI"/>
</rng:attribute>
</rng:optional>
		<rng:optional>
<rng:attribute name="CatalogueHandle">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Corpus Link
	-->
	<rng:define name="CorpusLink_Type">
		<a:documentation>
			Link to other resource. Attribute name is for the benefit of browsing
		</a:documentation>
		
			
				<rng:attribute name="Name">
<rng:data type="string"/>
</rng:attribute>
			
		
	</rng:define>
	<!--
		Catalogue
	-->
	<rng:define name="Catalogue_Type">
		<a:documentation>
			Type for group metadata pertaining to published corpora
		</a:documentation>
		
			<rng:element name="Name">
<rng:ref name="String_Type"/>
				<a:documentation>
					Name of the published corpus
				</a:documentation>
			</rng:element>
			<rng:element name="Title">
<rng:ref name="String_Type"/>
				<a:documentation>
					Title of the published corpus
				</a:documentation>
			</rng:element>
			<rng:oneOrMore>
<rng:element name="Id">
<rng:ref name="String_Type"/>
				<a:documentation>
					Identifier of the published corpus
				</a:documentation>
			</rng:element>
</rng:oneOrMore>
			<rng:oneOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
				<a:documentation>
					Description of the published corpus
				</a:documentation>
			</rng:element>
</rng:oneOrMore>
			<rng:element name="DocumentLanguages">
				<a:documentation>
					The languages used for documentation of the corpus
				</a:documentation>
				
					
						<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
							<a:documentation>
								Description for the list of languages
							</a:documentation>
						</rng:element>
</rng:zeroOrMore>
						<rng:zeroOrMore>
<rng:element name="Language">
<rng:ref name="SimpleLanguageType"/>
</rng:element>
</rng:zeroOrMore>
					
					<rng:ref name="ProfileAttributes"/>
				
			</rng:element>
			<rng:element name="SubjectLanguages">
				<a:documentation>
					The languages in the corpus that are subject of analysis
				</a:documentation>
				
					
						<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
							<a:documentation>
								Description for the list of languages
							</a:documentation>
						</rng:element>
</rng:zeroOrMore>
						<rng:zeroOrMore>
<rng:element name="Language">
<rng:ref name="SubjectLanguageType"/>
</rng:element>
</rng:zeroOrMore>
					
					<rng:ref name="ProfileAttributes"/>
				
			</rng:element>
			<rng:oneOrMore>
<rng:element name="Location">
<rng:ref name="Location_Type"/>
</rng:element>
</rng:oneOrMore>
			<rng:oneOrMore>
<rng:element name="ContentType">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					Content type of the published corpus
				</a:documentation>
			</rng:element>
</rng:oneOrMore>
			<rng:element name="Format">
				
					<rng:interleave>
<rng:optional>
<rng:optional>
<rng:element name="Text">
<rng:ref name="Vocabulary_Type"/>
</rng:element>
</rng:optional>
</rng:optional>
<rng:optional>
<rng:optional>
<rng:element name="Audio">
<rng:ref name="Vocabulary_Type"/>
</rng:element>
</rng:optional>
</rng:optional>
<rng:optional>
<rng:optional>
<rng:element name="Video">
<rng:ref name="Vocabulary_Type"/>
</rng:element>
</rng:optional>
</rng:optional>
<rng:optional>
<rng:optional>
<rng:element name="Image">
<rng:ref name="Vocabulary_Type"/>
</rng:element>
</rng:optional>
</rng:optional>
</rng:interleave>
				
			</rng:element>
			<rng:element name="Quality">
				
					<rng:interleave>
<rng:optional>
<rng:optional>
<rng:element name="Text">
<rng:ref name="Quality_Value_Type"/>
</rng:element>
</rng:optional>
</rng:optional>
<rng:optional>
<rng:optional>
<rng:element name="Audio">
<rng:ref name="Quality_Value_Type"/>
</rng:element>
</rng:optional>
</rng:optional>
<rng:optional>
<rng:optional>
<rng:element name="Video">
<rng:ref name="Quality_Value_Type"/>
</rng:element>
</rng:optional>
</rng:optional>
<rng:optional>
<rng:optional>
<rng:element name="Image">
<rng:ref name="Quality_Value_Type"/>
</rng:element>
</rng:optional>
</rng:optional>
</rng:interleave>
					<rng:ref name="ProfileAttributes"/>
				
			</rng:element>
			<rng:element name="SmallestAnnotationUnit">
<rng:ref name="Vocabulary_Type"/>
</rng:element>
			<rng:element name="Applications">
<rng:ref name="Vocabulary_Type"/>
</rng:element>
			<rng:element name="Date">
<rng:ref name="Date_Type"/>
</rng:element>
			<rng:oneOrMore>
<rng:element name="Project">
<rng:ref name="Project_Type"/>
</rng:element>
</rng:oneOrMore>
			<rng:oneOrMore>
<rng:element name="Publisher">
<rng:ref name="String_Type"/>
				<a:documentation>
					Publisher responsible for distribution of the published corpus
				</a:documentation>
			</rng:element>
</rng:oneOrMore>
			<rng:oneOrMore>
<rng:element name="Author">
<rng:ref name="CommaSeparatedString_Type"/>
				<a:documentation>
					Authors for the resources
				</a:documentation>
			</rng:element>
</rng:oneOrMore>
			<rng:element name="Size">
<rng:ref name="String_Type"/>
				<a:documentation>
					Human readabusle string that indicates total size of corpus
				</a:documentation>
			</rng:element>
			<rng:element name="DistributionForm">
<rng:ref name="Vocabulary_Type"/>
</rng:element>
			<rng:element name="Access">
<rng:ref name="Access_Type"/>
</rng:element>
			<rng:element name="Pricing">
<rng:ref name="String_Type"/>
				<a:documentation>
					Pricing info of the corpus
				</a:documentation>
			</rng:element>
			<rng:optional>
<rng:element name="ContactPerson">
<rng:ref name="String_Type"/>
				<a:documentation>
					Person to be contacted about the resource
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="ReferenceLink">
<rng:ref name="String_Type"/>
				<a:documentation>
					URL to the resource
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="MetadataLink">
<rng:ref name="String_Type"/>
				<a:documentation>
					URL to the metadata for the resource
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="Publications">
<rng:ref name="String_Type"/>
				<a:documentation>
					List of any publications related to the resource
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:element name="Keys">
<rng:ref name="Keys_Type"/>
</rng:element>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Session
	-->
	<rng:define name="Session_Type">
		
			<rng:element name="Name">
<rng:ref name="String_Type"/>
</rng:element>
			<rng:element name="Title">
<rng:ref name="String_Type"/>
</rng:element>
			<rng:element name="Date">
<rng:ref name="DateRange_Type"/>
</rng:element>
			<rng:zeroOrMore>
<rng:element name="ExternalResourceReference">
<rng:ref name="ExternalResourceReference_Type"/>
</rng:element>
</rng:zeroOrMore>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
</rng:element>
</rng:zeroOrMore>
			<rng:element name="MDGroup">
<rng:ref name="MDGroupType"/>
</rng:element>
			<rng:element name="Resources">
				<a:documentation>
					Groups information of language resources connected to the session
				</a:documentation>
				
					
						<rng:zeroOrMore>
<rng:element name="MediaFile">
<rng:ref name="MediaFile_Type"/>
							<a:documentation>
								Groups all media resources
							</a:documentation>
						</rng:element>
</rng:zeroOrMore>
						<rng:zeroOrMore>
<rng:element name="WrittenResource">
<rng:ref name="WrittenResource_Type"/>
							<a:documentation>
								Groups information about a Written Resource
							</a:documentation>
						</rng:element>
</rng:zeroOrMore>
						<rng:zeroOrMore>
<rng:element name="LexiconResource">
<rng:ref name="LexiconResource_Type"/>
							<a:documentation>
								Groups information only pertaining to a Lexical resource
							</a:documentation>
						</rng:element>
</rng:zeroOrMore>
						<rng:zeroOrMore>
<rng:element name="LexiconComponent">
<rng:ref name="LexiconComponent_Type"/>
							<a:documentation>
								Groups information only pertaining to a lexiconComponent
							</a:documentation>
						</rng:element>
</rng:zeroOrMore>
						<rng:zeroOrMore>
<rng:element name="Source">
<rng:ref name="Source_Type"/>
							<a:documentation>
								Groups information about the source; e.g. media-carrier, book, newspaper archive etc.
							</a:documentation>
						</rng:element>
</rng:zeroOrMore>
						<rng:optional>
<rng:element name="Anonyms">
<rng:ref name="Anonyms_Type"/>
							<a:documentation>
								Groups data about name conversions for persons who are anonymised
							</a:documentation>
						</rng:element>
</rng:optional>
					
					<rng:ref name="ProfileAttributes"/>
				
			</rng:element>
			<rng:optional>
<rng:element name="References">
				<a:documentation>
					Groups information about external documentation associated with this session
				</a:documentation>
				
					
						<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
							<a:documentation>
								Every description is a reference
							</a:documentation>
						</rng:element>
</rng:zeroOrMore>
					
					<rng:ref name="ProfileAttributes"/>
				
			</rng:element>
</rng:optional>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		MediaFile
	-->
	<rng:define name="MediaFile_Type">
		<a:documentation>
			Groups information about the media file
		</a:documentation>
		
			<rng:element name="ResourceLink">
<rng:ref name="ResourceLink_Type"/>
				<a:documentation>
					URL to media file
				</a:documentation>
			</rng:element>
			<rng:element name="Type">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					Major part of mime-type
				</a:documentation>
			</rng:element>
			<rng:element name="Format">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					Minor part of mime-type
				</a:documentation>
			</rng:element>
			<rng:element name="Size">
<rng:ref name="String_Type"/>
				<a:documentation>
					Size of media file
				</a:documentation>
			</rng:element>
			<rng:element name="Quality">
<rng:ref name="Quality_Type"/>
				<a:documentation>
					Quality of the recording
				</a:documentation>
			</rng:element>
			<rng:element name="RecordingConditions">
<rng:ref name="String_Type"/>
				<a:documentation>
					describes technical conditions of recording
				</a:documentation>
			</rng:element>
			<rng:element name="TimePosition">
<rng:ref name="TimePositionRange_Type"/>
</rng:element>
			<rng:element name="Access">
<rng:ref name="Access_Type"/>
</rng:element>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
</rng:element>
</rng:zeroOrMore>
			<rng:element name="Keys">
<rng:ref name="Keys_Type"/>
</rng:element>
		
		<rng:optional>
<rng:attribute name="ResourceId">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Written Resource
	-->
	<rng:define name="WrittenResource_Type">
		<a:documentation>
			Groups information about a Written Resource
		</a:documentation>
		
			<rng:element name="ResourceLink">
<rng:ref name="ResourceLink_Type"/>
				<a:documentation>
					URL to file containing the annotations/transcription
				</a:documentation>
			</rng:element>
			<rng:element name="MediaResourceLink">
<rng:ref name="ResourceLink_Type"/>
				<a:documentation>
					URL to media file from which the annotations/transcriptions originate 
				</a:documentation>
			</rng:element>
			<rng:element name="Date">
				<a:documentation>
					Date when Written Resource was created
				</a:documentation>
				
					
						
					
				
			</rng:element>
			<rng:element name="Type">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The type of the WrittenResource
				</a:documentation>
			</rng:element>
			<rng:element name="SubType">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The subtype of the WrittenResource
				</a:documentation>
			</rng:element>
			<rng:element name="Format">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					File format used for Written Resource
				</a:documentation>
			</rng:element>
			<rng:element name="Size">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The size of the Written Resource file. Integer value with addition of M (mega) or K (kilo)
				</a:documentation>
			</rng:element>
			<rng:element name="Validation">
<rng:ref name="Validation_Type"/>
</rng:element>
			<rng:element name="Derivation">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					How this document relates to another resource
				</a:documentation>
			</rng:element>
			<rng:element name="CharacterEncoding">
<rng:ref name="String_Type"/>
				<a:documentation>
					Character encoding used in the written resource
				</a:documentation>
			</rng:element>
			<rng:element name="ContentEncoding">
<rng:ref name="String_Type"/>
				<a:documentation>
					Content encoding used in the written resource
				</a:documentation>
			</rng:element>
			<rng:element name="LanguageId">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					Language used in the resource
				</a:documentation>
			</rng:element>
			<rng:element name="Anonymized">
<rng:ref name="Boolean_Type"/>
				<a:documentation>
					Indicates if data has been anonymised. CV boolean
				</a:documentation>
			</rng:element>
			<rng:element name="Access">
<rng:ref name="Access_Type"/>
</rng:element>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
</rng:element>
</rng:zeroOrMore>
			<rng:element name="Keys">
<rng:ref name="Keys_Type"/>
</rng:element>
		
		<rng:optional>
<rng:attribute name="ResourceId">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Lexicon Resource
	-->
	<rng:define name="LexiconResource_Type">
		<a:documentation>
			Groups information only pertaining to a Lexical resource
		</a:documentation>
		
			<rng:element name="ResourceLink">
<rng:ref name="ResourceLink_Type"/>
				<a:documentation>
					URL to lexical resource
				</a:documentation>
			</rng:element>
			<rng:element name="Date">
<rng:ref name="Date_Type"/>
				<a:documentation>
					Date when lexical resource was created
				</a:documentation>
			</rng:element>
			<rng:element name="Type">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The type of the WrittenResource
				</a:documentation>
			</rng:element>
			<rng:element name="Format">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The format of the LexicalResource
				</a:documentation>
			</rng:element>
			<rng:element name="CharacterEncoding">
<rng:ref name="String_Type"/>
				<a:documentation>
					The character encoding of the LexicalResource
				</a:documentation>
			</rng:element>
			<rng:element name="Size">
				<a:documentation>
					The size of the LexicalResource in bytes
				</a:documentation>
				
					
						
							<rng:ref name="ProfileAttributes"/>
						
					
				
			</rng:element>
			<rng:element name="NoHeadEntries">
<rng:ref name="Integer_Type"/>
				<a:documentation>
					The number of head entries of the LexicalResource
				</a:documentation>
			</rng:element>
			<rng:element name="NoSubEntries">
<rng:ref name="Integer_Type"/>
				<a:documentation>
					The number of sub entries of the LexicalResource
				</a:documentation>
			</rng:element>
			<rng:oneOrMore>
<rng:element name="LexicalEntry">
				
					
						<rng:element name="HeadWordType">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								OCV: Sentence, Phrase, Wordform, Lemma, ...
							</a:documentation>
						</rng:element>
						<rng:element name="Orthography">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								OCV: HyphenatedSpelling, SyllabifiedSpelling, ...
							</a:documentation>
						</rng:element>
						<rng:element name="Morphology">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								OCV: Stem,StemALlomorphy, Segmentation, ...
							</a:documentation>
						</rng:element>
						<rng:element name="MorphoSyntax">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								OCV: POS, Inflexion, Countability, ...
							</a:documentation>
						</rng:element>
						<rng:element name="Syntax">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								OCV: Complementation, Alternation, Modification, ...
							</a:documentation>
						</rng:element>
						<rng:element name="Phonology">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								OCV: Transcription, IPA Transcription, CV pattern, ...
							</a:documentation>
						</rng:element>
						<rng:element name="Semantics">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								OCV: Sense dstinction
							</a:documentation>
						</rng:element>
						<rng:element name="Etymology">
<rng:ref name="Vocabulary_Type"/>
</rng:element>
						<rng:element name="Usage">
<rng:ref name="Vocabulary_Type"/>
</rng:element>
						<rng:element name="Frequency">
<rng:ref name="String_Type"/>
</rng:element>
					
					<rng:ref name="ProfileAttributes"/>
				
			</rng:element>
</rng:oneOrMore>
			<rng:element name="MetaLanguages">
				<a:documentation>
					A block to describe the languages that are used to define terms, to describe meaning
				</a:documentation>
				
					
						<rng:zeroOrMore>
<rng:element name="Language">
<rng:ref name="Vocabulary_Type"/>
</rng:element>
</rng:zeroOrMore>
						<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
</rng:element>
</rng:zeroOrMore>
					
					<rng:ref name="ProfileAttributes"/>
				
			</rng:element>
			<rng:element name="Access">
<rng:ref name="Access_Type"/>
</rng:element>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
</rng:element>
</rng:zeroOrMore>
			<rng:element name="Keys">
<rng:ref name="Keys_Type"/>
</rng:element>
		
		<rng:optional>
<rng:attribute name="ResourceId">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- LMF compliant Lexicon component -->
	<rng:define name="LexiconComponent_Type">
		<a:documentation>
			Groups information only pertaining to a lexiconComponent
		</a:documentation>
		
			<rng:element name="ResourceLink">
<rng:ref name="ResourceLink_Type"/>
				<a:documentation>
					URL to lexiconComponent
				</a:documentation>
			</rng:element>
			<rng:element name="Date">
<rng:ref name="Date_Type"/>
				<a:documentation>
					Date when lexiconComponent was created
				</a:documentation>
			</rng:element>
			<rng:element name="Type">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The type of the lexiconComponent
				</a:documentation>
			</rng:element>
			<!-- Type element is not very relevant for lexiconComponent, since the IMDI type will be 'unspecified' -->
			<rng:element name="Format">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					The format of the lexiconComponent
				</a:documentation>
			</rng:element>
			<rng:element name="CharacterEncoding">
<rng:ref name="String_Type"/>
				<a:documentation>
					The character encoding of the lexiconComponent
				</a:documentation>
			</rng:element>
			<rng:element name="Size">
				<a:documentation>
					The size of the lexiconComponent in bytes
				</a:documentation>
				
					
						
							<rng:ref name="ProfileAttributes"/>
						
					
				
			</rng:element>
			<rng:element name="Component">
				<a:documentation>
					Describes the tree in which the component can be embedded
				</a:documentation>
				
					
						<rng:element name="possibleParents">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								Describes the possible parents of the lexiconComponent in the schema tree
							</a:documentation>
						</rng:element>
						<rng:optional>
<rng:element name="preferredParent">
<rng:ref name="Vocabulary_Type"/>
							<a:documentation>
								Descibes the preferred parent of the lexiconComponent in the schema tree
							</a:documentation>
						</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="childNodes">
							
								
									<rng:optional>
<rng:element name="childComponents">
<rng:ref name="Vocabulary_Type"/>
										<a:documentation>
											Describes the possible component children of the lexiconComponent in the schema tree
										</a:documentation>
									</rng:element>
</rng:optional>
									<rng:optional>
<rng:element name="childCategories">
<rng:ref name="Vocabulary_Type"/>
										<a:documentation>
											Describes the possible category children of the lexiconComponent in the schema tree
										</a:documentation>
									</rng:element>
</rng:optional>
								
							
						</rng:element>
</rng:optional>
					
					<rng:ref name="ProfileAttributes"/>
				
			</rng:element>
			<rng:optional>
<rng:element name="LexicalInfo">
				<a:documentation>
					Gives information on the lexical applications of the lexiconComponent
				</a:documentation>
				
					
						<rng:optional>
<rng:element name="Orthography">
<rng:data type="boolean">
							<a:documentation>
								Describes whether the lexiconComponent can be used to add orthography to the lexicon schema
							</a:documentation>
						</rng:data>
</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="Morphology">
<rng:data type="boolean">
							<a:documentation>
								Describes whether the lexiconComponent can be used to add morphology to the lexicon schema.
							</a:documentation>
						</rng:data>
</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="MorphoSyntax">
<rng:data type="boolean">
							<a:documentation>
								Describes whether the lexiconComponent can be used to add morphosyntactic features to the lexicon schema
							</a:documentation>
						</rng:data>
</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="Syntax">
<rng:data type="boolean">
							<a:documentation>
								Describes whether the lexiconComponent can be used to add syntactic features to the lexicon schema
							</a:documentation>
						</rng:data>
</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="Phonology">
<rng:data type="boolean">
							<a:documentation>
								Describes whether the lexiconComponent can be used to add phonology to the lexicon schema.
							</a:documentation>
						</rng:data>
</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="Semantics">
<rng:data type="boolean">
							<a:documentation>
								Describes whether the lexiconComponent can be used to add a semantic element to the lexicon schema
							</a:documentation>
						</rng:data>
</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="Etymology">
<rng:data type="boolean"/>
</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="Usage">
<rng:data type="boolean"/>
</rng:element>
</rng:optional>
						<rng:optional>
<rng:element name="Frequency">
<rng:data type="boolean"/>
</rng:element>
</rng:optional>
					
				
			</rng:element>
</rng:optional>
			<rng:element name="MetaLanguages">
				<a:documentation>
					A block to describe the languages that are used to define terms, to describe meaning
				</a:documentation>
				
					
						<rng:element name="Language">
<rng:ref name="Vocabulary_Type"/>
</rng:element>
						<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
</rng:element>
</rng:zeroOrMore>
					
					<rng:ref name="ProfileAttributes"/>
				
			</rng:element>
			<rng:element name="Access">
<rng:ref name="Access_Type"/>
</rng:element>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
</rng:element>
</rng:zeroOrMore>
			<rng:element name="Keys">
<rng:ref name="Keys_Type"/>
</rng:element>
		
		<rng:optional>
<rng:attribute name="ResourceId">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!--
		Source
	-->
	<rng:define name="Source_Type">
		<a:documentation>
			Groups information about the original source; e.g. media-carrier, book, newspaper archive etc.
		</a:documentation>
		
			<rng:element name="Id">
				<a:documentation>
					Unique code to identify the original source
				</a:documentation>
				
					
						
							<rng:ref name="ProfileAttributes"/>
						
					
				
			</rng:element>
			<rng:element name="Format">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					Physical storage format of the source
				</a:documentation>
			</rng:element>
			<rng:element name="Quality">
<rng:ref name="Quality_Type"/>
				<a:documentation>
					Quality of original recording
				</a:documentation>
			</rng:element>
			<rng:optional>
<rng:element name="CounterPosition">
<rng:ref name="CounterPosition_Type"/>
</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="TimePosition">
<rng:ref name="TimePositionRange_Type"/>
</rng:element>
</rng:optional>
			<rng:element name="Access">
<rng:ref name="Access_Type"/>
</rng:element>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
				<a:documentation>
					Description for the original source
				</a:documentation>
			</rng:element>
</rng:zeroOrMore>
			<rng:element name="Keys">
<rng:ref name="Keys_Type"/>
</rng:element>
		
		<rng:ref name="ProfileAttributes"/>
		<rng:optional>
<rng:attribute name="ResourceRefs">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
	</rng:define>
	<!-- 
		Anonyms
	-->
	<rng:define name="Anonyms_Type">
		<a:documentation>
			Groups data about name conversions for persons who are anonymised
		</a:documentation>
		
			<rng:element name="ResourceLink">
<rng:ref name="ResourceLink_Type"/>
				<a:documentation>
					URL to information to convert pseudo named to real-names
				</a:documentation>
			</rng:element>
			<rng:element name="Access">
<rng:ref name="Access_Type"/>
</rng:element>
		
	</rng:define>
	<!-- 
		Vocabulary Definition
	-->
	<rng:define name="VocabularyDef_Type">
		<a:documentation>
			The definition of a vocabulary. Attributes: Date of creattion, Link to origin. Contails a Description be element to descr+++ ibe the domain of the vocabulary and a (unspecified) number of value enries
		</a:documentation>
		
			<rng:oneOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
</rng:element>
</rng:oneOrMore>
			<rng:oneOrMore>
<rng:element name="Entry">
				
					
						
							<rng:attribute name="Tag">
<rng:data type="string"/>
</rng:attribute>
							<rng:attribute name="Value">
<rng:data type="string"/>
</rng:attribute>
						
					
				
			</rng:element>
</rng:oneOrMore>
		
		<rng:attribute name="Name">
<rng:data type="string"/>
</rng:attribute>
		<rng:attribute name="Date">
<rng:data type="date"/>
</rng:attribute>
		<rng:optional>
<rng:attribute name="Tag">
<rng:data type="date"/>
</rng:attribute>
</rng:optional>
		<rng:attribute name="Link">
<rng:ref name="Link_Value_Type"/>
</rng:attribute>
	</rng:define>
	<!-- 
		Description
	-->
	<rng:define name="Description_Type">
		<a:documentation>
			Human readable description in the form of a text with language id specification and/or a link to a file with a description and language id specification. The name attribute is to name the link (if present)
		</a:documentation>
		
			
				<rng:attribute name="LanguageId">
<rng:ref name="LanguageId_Value_Type"/>
</rng:attribute>
				<rng:attribute name="Name">
<rng:data type="string"/>
</rng:attribute>
				<rng:attribute name="ArchiveHandle">
<rng:data type="string"/>
</rng:attribute>
				<rng:attribute name="Link">
<rng:data type="anyURI"/>
</rng:attribute>
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!--
		Contact
	-->
	<rng:define name="Contact_Type">
		<a:documentation>
			Contact information for this data
		</a:documentation>
		
			<rng:optional>
<rng:element name="Name">
<rng:ref name="String_Type"/>
</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="Address">
<rng:ref name="String_Type"/>
</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="Email">
<rng:ref name="String_Type"/>
</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="Organisation">
<rng:ref name="String_Type"/>
</rng:element>
</rng:optional>
		
	</rng:define>
	<!-- 
		Validation
	-->
	<rng:define name="Validation_Type">
		<a:documentation>
			The validation used for the resource
		</a:documentation>
		
			<rng:element name="Type">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					CV: content, type, manual, automatic, semi-automatic
				</a:documentation>
			</rng:element>
			<rng:element name="Methodology">
<rng:ref name="Vocabulary_Type"/>
				<a:documentation>
					Validation methodology
				</a:documentation>
			</rng:element>
			<rng:optional>
<rng:element name="Level">
<rng:ref name="Integer_Type"/>
				<a:documentation>
					Percentage of resource validated
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
</rng:element>
</rng:zeroOrMore>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Age
	-->
	<rng:define name="Age_Type">
		<a:documentation>
			Specifies age of a person with differerent counting methods
		</a:documentation>
		
			
				<rng:attribute xmlns:ns_1="http://relaxng.org/ns/compatibility/annotations/1.0" name="AgeCountingMethod" ns_1:defaultValue="SinceBirth">
<rng:ref name="AgeCountingMethod_Value_Type"/>
</rng:attribute>
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!-- 
		Age Range
	-->
	<rng:define name="AgeRange_Type">
		<a:documentation>
			Specifies age of a person in the form of a range
		</a:documentation>
		
			
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!-- 
		Language Type
		At the moment this type is used both as a sub element of Actor and of Project.
		Future versions of this schema should ensure that different Language Types are used, so that for example MotherTongue cannot be set when the Language refers to a Project.
	-->
	<rng:define name="Language_Type">
		<a:documentation>
			An element from a set of languages used in the session
		</a:documentation>
		
			<rng:element name="Id">
<rng:ref name="LanguageId_Type"/>
				<a:documentation>
					Unique code to identify a language
				</a:documentation>
			</rng:element>
			<rng:oneOrMore>
<rng:element name="Name">
<rng:ref name="LanguageName_Type"/>
				<a:documentation>
					Name of the language
				</a:documentation>
			</rng:element>
</rng:oneOrMore>
			<rng:optional>
<rng:element name="MotherTongue">
<rng:ref name="Boolean_Type"/>
				<a:documentation>
					Is it the speakers mother tongue. Only applicable if used in the context of a speakers language
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="PrimaryLanguage">
<rng:ref name="Boolean_Type"/>
				<a:documentation>
					Is it the speakers primary language. Only applicable if used in the context of a speakers language
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="Dominant">
<rng:ref name="Boolean_Type"/>
				<a:documentation>
					Is it the most frequently used language in the document. Only applicable if used in the context of the resource's language
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="SourceLanguage">
<rng:ref name="Boolean_Type"/>
				<a:documentation>
					Direction of translation. Only applicable in case it is the context of a lexicon resource
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:optional>
<rng:element name="TargetLanguage">
<rng:ref name="Boolean_Type"/>
				<a:documentation>
					Direction of translation. Only applicable in case it is the context of a lexicon resource
				</a:documentation>
			</rng:element>
</rng:optional>
			<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
				<a:documentation>
					Description for this particular language
				</a:documentation>
			</rng:element>
</rng:zeroOrMore>
		
		<rng:optional>
<rng:attribute name="ResourceRef">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Subject Language
	-->
	<rng:define name="SubjectLanguageType">
		
			<rng:ref name="SimpleLanguageType"/>
				
					<rng:optional>
<rng:element name="Dominant">
<rng:ref name="Boolean_Type"/>
						<a:documentation>
							Indicates if language is dominant language
						</a:documentation>
					</rng:element>
</rng:optional>
					<rng:optional>
<rng:element name="SourceLanguage">
<rng:ref name="Boolean_Type"/>
						<a:documentation>
							Indicates if language is source language
						</a:documentation>
					</rng:element>
</rng:optional>
					<rng:optional>
<rng:element name="TargetLanguage">
<rng:ref name="Boolean_Type"/>
						<a:documentation>
							Indicates if language is target language
						</a:documentation>
					</rng:element>
</rng:optional>
					<rng:zeroOrMore>
<rng:element name="Description">
<rng:ref name="Description_Type"/>
						<a:documentation>
							Description of the language
						</a:documentation>
					</rng:element>
</rng:zeroOrMore>
				
			
		
	</rng:define>
	<!-- 
		Simple Language
	-->
	<rng:define name="SimpleLanguageType">
		<a:documentation>
			Information on language name and id
		</a:documentation>
		
			<rng:element name="Id">
<rng:ref name="LanguageId_Type"/>
				<a:documentation>
					Unique code to identify a language
				</a:documentation>
			</rng:element>
			<rng:element name="Name">
<rng:ref name="LanguageName_Type"/>
				<a:documentation>
					The name of the language
				</a:documentation>
			</rng:element>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!--
		Language Id
	-->
	<rng:define name="LanguageId_Type">
		
			
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!--
		Language Name
	-->
	<rng:define name="LanguageName_Type">
		
			
		
	</rng:define>
	<!--
		Basic Types 
	-->
	<!-- 
		Boolean
	-->
	<rng:define name="Boolean_Type">
		
			
				<rng:ref name="ProfileAttributes"/>
				<rng:attribute xmlns:ns_1="http://relaxng.org/ns/compatibility/annotations/1.0" name="Type" ns_1:defaultValue="ClosedVocabulary">
<rng:ref name="VocabularyType_Value_Type"/>
</rng:attribute>
				<rng:attribute name="DefaultLink">
<rng:ref name="Link_Value_Type"/>
</rng:attribute>
				<rng:attribute name="Link">
<rng:ref name="Link_Value_Type"/>
</rng:attribute>
			
		
	</rng:define>
	<!-- 
		String
	-->
	<rng:define name="String_Type">
		<a:documentation>
			String type for single spaced, single line strings
		</a:documentation>
		
			
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!-- 
		Comma Separated String
	-->
	<rng:define name="CommaSeparatedString_Type">
		<a:documentation>
			Comma separated string
		</a:documentation>
		
			
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!-- 
		Integer
	-->
	<rng:define name="Integer_Type">
		
			
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!--
		Date
	-->
	<rng:define name="Date_Type">
		
			
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!-- 
		Date Range
	-->
	<rng:define name="DateRange_Type">
		
			
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!-- 
		Age Value
	-->
	<rng:define name="Age_Value_Type">
		<a:documentation>
			The age of a person
		</a:documentation>
		<rng:data type="string">
			<rng:param name="pattern">([0-9]+)*(;[0-9]+)*(.[0-9]+)*|Unknown|Unspecified</rng:param>
		</rng:data>
	</rng:define>
	<!-- 
		Age Range Value
	-->
	<rng:define name="AgeRange_Value_Type">
		<a:documentation>
			The age of a person given as a range
		</a:documentation>
		<rng:data type="string">
			<rng:param name="pattern">([0-9]+)?(;[0-9]+)?(.[0-9]+)?(/([0-9]+)?(;[0-9]+)?(.[0-9]+)?)?|Unknown|Unspecified</rng:param>
		</rng:data>
	</rng:define>
	<!-- 
		Age Counting Method Value
	-->
	<rng:define name="AgeCountingMethod_Value_Type">
		<a:documentation>
			The age counting method
		</a:documentation>
		<rng:choice>
			<rng:value>SinceConception</rng:value>
			<rng:value>SinceBirth</rng:value>
		</rng:choice>
	</rng:define>
	<!--
		Resource Link
	-->
	<rng:define name="ResourceLink_Type">
		
			
				<rng:ref name="ProfileAttributes"/>
				<rng:attribute name="ArchiveHandle">
<rng:data type="string"/>
</rng:attribute>
			
		
	</rng:define>
	<!-- 
		Vocabulary
	-->
	<rng:define name="Vocabulary_Type">
		<a:documentation>
			Vocabulary content and attributes
		</a:documentation>
		
			
				<rng:attribute xmlns:ns_1="http://relaxng.org/ns/compatibility/annotations/1.0" name="Type" ns_1:defaultValue="OpenVocabulary">
<rng:ref name="VocabularyType_Value_Type"/>
</rng:attribute>
				<rng:attribute name="DefaultLink">
<rng:ref name="Link_Value_Type"/>
</rng:attribute>
				<rng:attribute name="Link">
<rng:ref name="Link_Value_Type"/>
					<a:documentation>
						Link to a vocabulary definition
					</a:documentation>
				</rng:attribute>
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!-- 
		Counter Position
	-->
	<rng:define name="CounterPosition_Type">
		<a:documentation>
			Position (start (+end) ) on a old fashioned tape without time indication
		</a:documentation>
		
			<rng:element name="Start">
<rng:ref name="Integer_Type"/>
</rng:element>
			<rng:optional>
<rng:element name="End">
<rng:ref name="Integer_Type"/>
</rng:element>
</rng:optional>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Time Position
	-->
	<rng:define name="TimePosition_Type">
		
			
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!-- 
		Time Position Range
	-->
	<rng:define name="TimePositionRange_Type">
		<a:documentation>
			Position in a media file or modern tape
		</a:documentation>
		
			<rng:element name="Start">
<rng:ref name="TimePosition_Type"/>
				<a:documentation>
					The start time position of a recording
				</a:documentation>
			</rng:element>
			<rng:optional>
<rng:element name="End">
<rng:ref name="TimePosition_Type"/>
				<a:documentation>
					The end time position of a recording
				</a:documentation>
			</rng:element>
</rng:optional>
		
		<rng:ref name="ProfileAttributes"/>
	</rng:define>
	<!-- 
		Quality
	-->
	<rng:define name="Quality_Type">
		<a:documentation>
			Quality indication
		</a:documentation>
		
			
				<rng:ref name="ProfileAttributes"/>
			
		
	</rng:define>
	<!--
		Value Types
	-->
	<!-- 
		Empty Value
	-->
	<rng:define name="Empty_Value_Type">
		<a:documentation>
			Unspecified is a non-existing (null) value. Unknown is a informational value indicating that the real value is not known
		</a:documentation>
		<rng:choice>
			<rng:value>Unknown</rng:value>
			<rng:value>Unspecified</rng:value>
		</rng:choice>
	</rng:define>
	<!-- 
		Empty String Value
	-->
	<rng:define name="EmptyString_Value_Type">
		<a:documentation>
			empty string definition
		</a:documentation>
		<rng:data type="string">
			<rng:param name="maxLength">0</rng:param>
		</rng:data>
	</rng:define>
	<!-- 
		Comma Separated String Value
	-->
	<rng:define name="CommaSeparatedString_Value_Type">
		<a:documentation>
			Comma seperated string
		</a:documentation>
		<rng:data type="string">
			<rng:param name="pattern">[^,]*(,[^,]+)*</rng:param>
		</rng:data>
	</rng:define>
	<!-- 
		Boolean Value
	-->
	<rng:define name="Boolean_Value_Type">
		<a:documentation>
			Loose boolean value where empty values are allowed
		</a:documentation>
		<rng:choice>
<rng:data type="boolean">xsd:boolean imdi:Empty_Value_Type</rng:data>
<rng:ref name="Empty_Value_Type"/>xsd:boolean imdi:Empty_Value_Type</rng:choice>
	</rng:define>	
	<!--
		Integer Value
	-->
	<rng:define name="Integer_Value_Type">
		<a:documentation>
			integer + Unspecified and Unknown
		</a:documentation>
		<rng:choice>
<rng:data type="unsignedInt">xsd:unsignedInt imdi:Empty_Value_Type</rng:data>
<rng:ref name="Empty_Value_Type"/>xsd:unsignedInt imdi:Empty_Value_Type</rng:choice>
	</rng:define>
	<!-- 
		Date Value
		For future versions: A date field should never be empty, only Unknown or Unspecified
	-->
	<rng:define name="Date_Value_Type">
		<a:documentation>
			Defines a date that can also be empty or Unknown or Unspecified
		</a:documentation>
		<rng:choice>
<rng:ref name="DateRange_Value_Type"/>imdi:DateRange_Value_Type imdi:EmptyString_Value_Type imdi:Empty_Value_Type<rng:ref name="EmptyString_Value_Type"/>imdi:DateRange_Value_Type imdi:EmptyString_Value_Type imdi:Empty_Value_Type<rng:ref name="Empty_Value_Type"/>imdi:DateRange_Value_Type imdi:EmptyString_Value_Type imdi:Empty_Value_Type</rng:choice>
	</rng:define>
	<!-- 
		Date Range Value
	-->
	<rng:define name="DateRange_Value_Type">
		<a:documentation>
			Defines a date range that can also be Unspecified or Unknown
		</a:documentation>
		<rng:data type="string">
			<rng:param name="pattern">([0-9]+)((-[0-9]+)(-[0-9]+)?)?(/([0-9]+)((-[0-9]+)(-[0-9]+)?)?)?|Unknown|Unspecified</rng:param>
		</rng:data>
	</rng:define>
	<!-- 
		LanguageId Value
	-->
	<rng:define name="LanguageId_Value_Type">
		<a:documentation>
			Language identifiers
		</a:documentation>
		<rng:data type="token">
			<rng:param name="pattern">(ISO639(-1|-2|-3)?:.*)?</rng:param>
			<rng:param name="pattern">(RFC3066:.*)?</rng:param>
			<rng:param name="pattern">(RFC1766:.*)?</rng:param>
			<rng:param name="pattern">(SIL:.*)?</rng:param>
			<rng:param name="pattern">Unknown</rng:param>
			<rng:param name="pattern">Unspecified</rng:param>
		</rng:data>
	</rng:define>
	<!--
		TimePosition Value
	-->
	<rng:define name="TimePosition_Value_Type">
		<a:documentation>
			Time position in the hh:mm:ss:ff format
		</a:documentation>
		<rng:data type="string">
			<rng:param name="pattern">[0-9][0-9]:[0-9][0-9]:[0-9][0-9]:?[0-9]*|Unknown|Unspecified</rng:param>
		</rng:data>
	</rng:define>
	<!-- 
		Quality Value
	-->
	<rng:define name="Quality_Value_Type">
		<a:documentation>
			Quality values (1 .. 5) also allows empty values
		</a:documentation>
		<rng:choice>
			
				<rng:choice>
					<rng:value>1</rng:value>
					<rng:value>2</rng:value>
					<rng:value>3</rng:value>
					<rng:value>4</rng:value>
					<rng:value>5</rng:value>
				</rng:choice>
			
			
				<rng:ref name="Empty_Value_Type"/>
			
		</rng:choice>
	</rng:define>
	<!-- 
		Vocabulary Type Value
	-->
	<rng:define name="VocabularyType_Value_Type">
		<a:documentation>
			All possible vocabulary type values
		</a:documentation>
		<rng:choice>
			<rng:value>ClosedVocabulary</rng:value>
			<rng:value>ClosedVocabularyList</rng:value>
			<rng:value>OpenVocabulary</rng:value>
			<rng:value>OpenVocabularyList</rng:value>
		</rng:choice>
	</rng:define>
	<!-- 
		Link Value
	-->
	<rng:define name="Link_Value_Type">
		<rng:data type="anyURI"/>
	</rng:define>
	<!--
		Metatranscript Value
	-->
	<rng:define name="Metatranscript_Value_Type">
		<a:documentation>
			Allowed values for metadata transcripts
		</a:documentation>
		<rng:choice>
			<rng:value>SESSION</rng:value>
			<rng:value>SESSION.Profile</rng:value>
			<rng:value>LEXICON_RESOURCE_BUNDLE</rng:value>
			<rng:value>LEXICON_RESOURCE_BUNDLE.Profile</rng:value>
			<rng:value>CATALOGUE</rng:value>
			<rng:value>CATALOGUE.Profile</rng:value>
			<rng:value>CORPUS</rng:value>
			<rng:value>CORPUS.Profile</rng:value>
		</rng:choice>
	</rng:define>
	<!-- 
		Special attributes for profiles
	-->
	<rng:define name="ProfileAttributes">
		<a:documentation>
			Attributes allowed for profiles
		</a:documentation>
		<rng:optional>
<rng:attribute name="XXX-Type">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:optional>
<rng:attribute name="XXX-Multiple">
<rng:data type="boolean"/>
</rng:attribute>
</rng:optional>
		<rng:optional>
<rng:attribute name="XXX-Visible">
<rng:data type="boolean"/>
</rng:attribute>
</rng:optional>
		<rng:optional>
<rng:attribute name="XXX-Tag">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:optional>
<rng:attribute name="XXX-HelpText">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
		<rng:optional>
<rng:attribute name="XXX-FollowUpDepend">
<rng:data type="string"/>
</rng:attribute>
</rng:optional>
	</rng:define>
</rng:grammar>
"""

########NEW FILE########
__FILENAME__ = moses
###############################################################
#  PyNLPl - Moses formats
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#
#       Licensed under GPLv3
#
# This is a Python library classes and functions for
# reading file-formats produced by Moses. Currently
# contains only a class for reading a Moses PhraseTable.
# (migrated to pynlpl from pbmbmt)
#
###############################################################


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from pynlpl.common import u

import sys
import bz2
import gzip
import datetime
import socket
import io

try:
    from twisted.internet import protocol, reactor #No Python 3 support yet :(
    from twisted.protocols import basic
    twistedimported = True
except:
    print("WARNING: Twisted could not be imported",file=sys.stderr)
    twistedimported = False


class PhraseTable(object):
    def __init__(self,filename, quiet=False, reverse=False, delimiter="|||", score_column = 3, max_sourcen = 0,sourceencoder=None, targetencoder=None, scorefilter=None):
        """Load a phrase table from file into memory (memory intensive!)"""
        self.phrasetable = {}
        self.sourceencoder = sourceencoder
        self.targetencoder = targetencoder


        if filename.split(".")[-1] == "bz2":
            f = bz2.BZ2File(filename,'r')
        elif filename.split(".")[-1] == "gz":
            f = gzip.GzipFile(filename,'r')
        else:
            f = io.open(filename,'r',encoding='utf-8')
        linenum = 0
        prevsource = None
        targets = []

        while True:
            if not quiet:
                linenum += 1
                if (linenum % 100000) == 0:
                    print("Loading phrase-table: @%d" % linenum, "\t(" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ")",file=sys.stderr)
            line = u(f.readline())
            if not line:
                break

            #split into (trimmed) segments
            segments = [ segment.strip() for segment in line.split(delimiter) ]

            if len(segments) < 3:
                print("Invalid line: ", line, file=sys.stderr)
                continue

            #Do we have a score associated?
            if score_column > 0 and len(segments) >= score_column:
                scores = tuple( ( float(x) for x in segments[score_column-1].strip().split() ) )
            else:
                scores = tuple()

            #if align2_column > 0:
            #    try:
            #        null_alignments = segments[align2_column].count("()")
            #    except:
            #        null_alignments = 0
            #else:
            #    null_alignments = 0

            if scorefilter:
                if not scorefilter(scores): continue

            if reverse:
                if max_sourcen > 0 and segments[1].count(' ') + 1 > max_sourcen:
                    continue

                if self.sourceencoder:
                    source = self.sourceencoder(segments[1]) #tuple(segments[1].split(" "))
                else:
                    source = segments[1]
                if self.targetencoder:
                    target = self.targetencoder(segments[0]) #tuple(segments[0].split(" "))
                else:
                    target = segments[0]
            else:
                if max_sourcen > 0 and segments[0].count(' ') + 1 > max_sourcen:
                    continue

                if self.sourceencoder:
                    source = self.sourceencoder(segments[0]) #tuple(segments[0].split(" "))
                else:
                    source = segments[0]
                if self.targetencoder:
                    target = self.targetencoder(segments[1]) #tuple(segments[1].split(" "))
                else:
                    target = segments[1]


            if prevsource and source != prevsource and targets:
                self.phrasetable[prevsource] = tuple(targets)
                targets = []

            targets.append( (target,scores) )
            prevsource = source

        #don't forget last one:
        if prevsource and targets:
            self.phrasetable[prevsource] = tuple(targets)

        f.close()


    def __contains__(self, phrase):
        """Query if a certain phrase exist in the phrase table"""
        if self.sourceencoder: phrase = self.sourceencoder(phrase)
        return (phrase in self.phrasetable)
        #d = self.phrasetable
        #for word in phrase:
        #    if not word in d:
        #        return False
        #    d = d[word
        #return ("" in d)

    def __iter__(self):
        for phrase, targets in self.phrasetable.items():
            yield phrase, targets

    def __len__(self):
        return len(self.phrasetable)

    def __bool__(self):
        return bool(self.phrasetable)

    def __getitem__(self, phrase): #same as translations
        """Return a list of (translation, scores) tuples"""
        if self.sourceencoder: phrase = self.sourceencoder(phrase)
        return self.phrasetable[phrase]


        #d = self.phrasetable
        #for word in phrase:
        #    if not word in d:
        #        raise KeyError
        #    d = d[word]

        #if "" in d:
        #    return d[""]
        #else:
        #    raise KeyError

if twistedimported:
    class PTProtocol(basic.LineReceiver):
        def lineReceived(self, phrase):
            try:
                for target,Pst,Pts,null_alignments in self.factory.phrasetable[phrase]:
                    self.sendLine(target+"\t"+str(Pst)+"\t"+str(Pts)+"\t"+str(null_alignments))
            except KeyError:
                self.sendLine("NOTFOUND")

    class PTFactory(protocol.ServerFactory):
        protocol = PTProtocol
        def __init__(self, phrasetable):
            self.phrasetable = phrasetable

    class PhraseTableServer(object):
        def __init__(self, phrasetable, port=65432):
            reactor.listenTCP(port, PTFactory(phrasetable))
            reactor.run()




class PhraseTableClient(object):

    def __init__(self,host= "localhost",port=65432):
        self.BUFSIZE = 4048
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM) #Create the socket
        self.socket.settimeout(120)
        self.socket.connect((host, port)) #Connect to server
        self.lastresponse = ""
        self.lastquery = ""

    def __getitem__(self, phrase):
        solutions = []
        if phrase != self.lastquery:
            self.socket.send(phrase+ "\r\n")

            data = b""
            while not data or data[-1] != '\n':
                data += self.socket.recv(self.BUFSIZE)
        else:
            data = self.lastresponse

        data = u(data)

        for line in data.split('\n'):
            line = line.strip('\r\n')
            if line == "NOTFOUND":
                raise KeyError(phrase)
            elif line:
                fields = tuple(line.split("\t"))
                if len(fields) == 4:
                    solutions.append( fields )
                else:
                    print >>sys.stderr,"PHRASETABLECLIENT WARNING: Unable to parse response line"

        self.lastresponse = data
        self.lastquery = phrase

        return solutions

    def __contains__(self, phrase):
        self.socket.send(phrase.encode('utf-8')+ b"\r\n")\


        data = b""
        while not data or data[-1] != '\n':
            data += self.socket.recv(self.BUFSIZE)

        data = u(data)

        for line in data.split('\n'):
            line = line.strip('\r\n')
            if line == "NOTFOUND":
                return False

        self.lastresponse = data
        self.lastquery = phrase

        return True


########NEW FILE########
__FILENAME__ = sonar
#---------------------------------------------------------------
# PyNLPl - Simple Read library for D-Coi/SoNaR format
#   by Maarten van Gompel, ILK, Universiteit van Tilburg
#   http://ilk.uvt.nl/~mvgompel
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#
# This library facilitates parsing and reading corpora in
# the SoNaR/D-Coi format.
#
#----------------------------------------------------------------

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import    


import io
import re
import glob
import os.path
import sys

from lxml import etree as ElementTree

from StringIO import StringIO


namespaces = {
    'dcoi': "http://lands.let.ru.nl/projects/d-coi/ns/1.0",
    'standalone':"http://ilk.uvt.nl/dutchsemcor-standalone",
    'dsc':"http://ilk.uvt.nl/dutchsemcor",
    'xml':"http://www.w3.org/XML/1998/namespace"
}

class CorpusDocument(object):
    """This class represent one document/text of the Corpus (read-only)"""

    def __init__(self, filename, encoding = 'iso-8859-15'):
        self.filename = filename
        self.id = os.path.basename(filename).split(".")[0]
        self.f = io.open(filename,'r', encoding=encoding)
        self.metadata = {}

    def _parseimdi(self,line):
        r = re.compile('<imdi:Title>(.*)</imdi:Title>')
        matches = r.findall(line)
        if matches:
            self.metadata['title'] = matches[0]
        if not 'date' in self.metadata:
            r = re.compile('<imdi:Date>(.*)</imdi:Date>')
            matches = r.findall(line)
            if matches:
                self.metadata['date'] = matches[0]

        
    def __iter__(self):
        """Iterate over all words, a four-tuple (word,id,pos,lemma), in the document"""
        
        r = re.compile('<w.*xml:id="([^"]*)"(.*)>(.*)</w>')
        for line in self.f.readlines():
            matches = r.findall(line)
            for id, attribs, word in matches:
                pos = lemma = None
                m = re.findall('pos="([^"]+)"', attribs)
                if m: pos = m[0]

                m = re.findall('lemma="([^"]+)"', attribs)
                if m: lemma = m[0]
        
                yield word, id, pos, lemma
            if line.find('imdi:') != -1:
                self._parseimdi(line)
    
    def words(self):
        #alias
        return iter(self) 


    def sentences(self):
        """Iterate over all sentences (sentence_id, sentence) in the document, sentence is a list of 4-tuples (word,id,pos,lemma)"""
        prevp = 0
        prevs = 0
        sentence = [];
        sentence_id = ""
        for word, id, pos, lemma in iter(self):
            try:
                doc_id, ptype, p, s, w = re.findall('([\w\d-]+)\.(p|head)\.(\d+)\.s\.(\d+)\.w\.(\d+)',id)[0]            
                if ((p != prevp) or (s != prevs)) and sentence:
                    yield sentence_id, sentence
                    sentence = []
                    sentence_id = doc_id + '.' + ptype + '.' + str(p) + '.s.' + str(s)
                prevp = p
            except IndexError:
                doc_id, s, w = re.findall('([\w\d-]+)\.s\.(\d+)\.w\.(\d+)',id)[0]            
                if s != prevs and sentence:
                    yield sentence_id, sentence
                    sentence = []
                    sentence_id = doc_id + '.s.' + str(s)
            sentence.append( (word,id,pos,lemma) )     
            prevs = s
        if sentence:
            yield sentence_id, sentence 
            
    def paragraphs(self, with_id = False):
        """Extracts paragraphs, returns list of plain-text(!) paragraphs"""
        prevp = 0
        partext = []
        for word, id, pos, lemma in iter(self):
            doc_id, ptype, p, s, w = re.findall('([\w\d-]+)\.(p|head)\.(\d+)\.s\.(\d+)\.w\.(\d+)',id)[0]
            if prevp != p and partext:
                    yield ( doc_id + "." + ptype + "." + prevp , " ".join(partext) )
                    partext = []
            partext.append(word)
            prevp = p   
        if partext:
            yield (doc_id + "." + ptype + "." + prevp, " ".join(partext) )
                
class Corpus:
    def __init__(self,corpusdir, extension = 'pos', restrict_to_collection = "", conditionf=lambda x: True, ignoreerrors=False):
        self.corpusdir = corpusdir
        self.extension = extension
        self.restrict_to_collection = restrict_to_collection
        self.conditionf = conditionf
        self.ignoreerrors = ignoreerrors

    def __iter__(self):
        if not self.restrict_to_collection:
            for f in glob.glob(self.corpusdir+"/*." + self.extension):
                if self.conditionf(f):
                    try:
                        yield CorpusDocument(f)
                    except:
                        print("Error, unable to parse " + f,file=sys.stderr)
                        if not self.ignoreerrors:
                            raise
        for d in glob.glob(self.corpusdir+"/*"):
            if (not self.restrict_to_collection or self.restrict_to_collection == os.path.basename(d)) and (os.path.isdir(d)):
                for f in glob.glob(d+ "/*." + self.extension):
                    if self.conditionf(f):
                        try:
                            yield CorpusDocument(f)
                        except:
                            print("Error, unable to parse " + f,file=sys.stderr)
                            if not self.ignoreerrors:
                                raise


#######################################################

def ns(namespace):
    """Resolves the namespace identifier to a full URL""" 
    global namespaces
    return '{'+namespaces[namespace]+'}'


class CorpusFiles(Corpus):
    def __iter__(self):
        if not self.restrict_to_collection:
            for f in glob.glob(self.corpusdir+"/*." + self.extension):
                if self.conditionf(f):
                    yield f
        for d in glob.glob(self.corpusdir+"/*"):
            if (not self.restrict_to_collection or self.restrict_to_collection == os.path.basename(d)) and (os.path.isdir(d)):
                for f in glob.glob(d+ "/*." + self.extension):
                    if self.conditionf(f):
                        yield f
                        
                        
class CorpusX(Corpus):
    def __iter__(self):
        if not self.restrict_to_collection:
            for f in glob.glob(self.corpusdir+"/*." + self.extension):
                if self.conditionf(f):
                    try:
                        yield CorpusDocumentX(f)
                    except:
                        print("Error, unable to parse " + f,file=sys.stderr)
                        if not self.ignoreerrors:
                            raise 
        for d in glob.glob(self.corpusdir+"/*"):
            if (not self.restrict_to_collection or self.restrict_to_collection == os.path.basename(d)) and (os.path.isdir(d)):
                for f in glob.glob(d+ "/*." + self.extension):
                    if self.conditionf(f):
                        try:
                            yield CorpusDocumentX(f)
                        except:
                            print("Error, unable to parse " + f,file=sys.stderr)
                            if not self.ignoreerrors:
                                raise
                               


class CorpusDocumentX:
    """This class represent one document/text of the Corpus, loaded into memory at once and retaining the full structure"""

    def __init__(self, filename, tree = None, index=True ):
        global namespaces
        self.filename = filename
        if not tree:
            self.tree = ElementTree.parse(self.filename)
            self.committed = True
        elif isinstance(tree, ElementTree._Element):
            self.tree = tree
            self.committed = False

        #Grab root element and determine if we run inline or standalone
        self.root =  self.xpath("/dcoi:DCOI")
        if self.root:
            self.root = self.root[0] 
            self.inline = True
        else:
            raise Exception("Not in DCOI/SoNaR format!")
            #self.root = self.xpath("/standalone:text")
            #self.inline = False
            #if not self.root:
            #    raise FormatError()            

        #build an index
        self.index = {}
        if index:
            self._index(self.root)

    def _index(self,node):
        if ns('xml') + 'id' in node.attrib:
                self.index[node.attrib[ns('xml') + 'id']] = node
        for subnode in node: #TODO: can we do this with xpath instead?
            self._index(subnode)

    def validate(self, formats_dir="../formats/"):
        """checks if the document is valid"""
        #TODO: download XSD from web
        if self.inline:
            xmlschema = ElementTree.XMLSchema(ElementTree.parse(StringIO("\n".join(open(formats_dir+"dcoi-dsc.xsd").readlines()))))
            xmlschema.assertValid(self.tree)
            #return xmlschema.validate(self)
        else:
            xmlschema = ElementTree.XMLSchema(ElementTree.parse(StringIO("\n".join(open(formats_dir+"dutchsemcor-standalone.xsd").readlines()))))
            xmlschema.assertValid(self.tree)
            #return xmlschema.validate(self)

    def xpath(self, expression):
        """Executes an xpath expression using the correct namespaces"""
        global namespaces
        return self.tree.xpath(expression, namespaces=namespaces)


    def __exists__(self, id):
        return (id in self.index)

    def __getitem__(self, id):
        return self.index[id]


    def paragraphs(self, node=None):
        """iterate over paragraphs"""
        if node == None: node = self
        return node.xpath("//dcoi:p")

    def sentences(self, node=None):
        """iterate over sentences"""
        if node == None: node = self
        return node.xpath("//dcoi:s")

    def words(self,node=None):
        """iterate over words"""
        if node == None: node = self
        return node.xpath("//dcoi:w")

    def save(self, filename=None, encoding='iso-8859-15'):
        if not filename: filename = self.filename
        self.tree.write(filename, encoding=encoding, method='xml', pretty_print=True, xml_declaration=True)



########NEW FILE########
__FILENAME__ = taggerdata
#-*- coding:utf-8 -*-

###############################################################
#  PyNLPl - Read tagger data
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#       
#       Licensed under GPLv3
#
#
###############################################################

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import    

import io

class Taggerdata(object):
    def __init__(self,filename, encoding = 'utf-8', mode ='r'):
        self.filename = filename
        self.encoding = encoding
        assert (mode == 'r' or mode == 'w')
        self.mode = mode
        self.reset()
        self.firstiter = True
        self.indexed = False
        self.writeindex = 0

    def __iter__(self):
        words = []
        lemmas = []
        postags = []
        for line in self.f:
            line = line.strip()
            if self.firstiter:
                self.indexed = (line == "#0")
                self.firstiter = False
            if not line and not self.indexed:
                yield (words, lemmas, postags)
                words = []
                lemmas = []
                postags = []
            elif self.indexed and len(line) > 1 and line[0] == '#' and line[1:].isdigit():
                if line != "#0":
                    yield (words, lemmas, postags)
                    words = []
                    lemmas = []
                    postags = []
            elif line:
                try:
                    word, lemma, pos = line.split("\t")
                except:
                    word = lemma = pos = "NONE"
                if word == "NONE": word = None
                if lemma == "NONE": lemma = None
                if pos == "NONE": pos = None
                words.append(word)
                lemmas.append(lemma)
                postags.append(pos)
        if words:
            yield (words, lemmas, postags)

    def next(self):
        words = []
        lemmas = []
        postags = []
        while True:
            try:
                line = self.f.next().strip()
            except StopIteration:
                if words:
                    return (words, lemmas, postags)
                else:
                    raise
            if self.firstiter:
                self.indexed = (line == "#0")
                self.firstiter = False
            if not line and not self.indexed:
                return (words, lemmas, postags)
            elif self.indexed and len(line) > 1 and line[0] == '#' and line[1:].isdigit():
                if line != "#0":
                    return (words, lemmas, postags)
            elif line:
                try:
                    word, lemma, pos = line.split("\t")
                except:
                    word = lemma = pos = "NONE"
                if word == "NONE": word = None
                if lemma == "NONE": lemma = None
                if pos == "NONE": pos = None
                words.append(word)
                lemmas.append(lemma)
                postags.append(pos)

    def align(self, referencewords, datatuple):
        """align the reference sentence with the tagged data"""
        targetwords = []
        for i, (word,lemma,postag) in enumerate(zip(datatuple[0],datatuple[1],datatuple[2])):
            if word:
                subwords = word.split("_")
                for w in subwords: #split multiword expressions
                    targetwords.append( (w, lemma, postag, i, len(subwords) > 1 ) ) #word, lemma, pos, index, multiword? 

        referencewords = [ w.lower() for w in referencewords ]          
        alignment = []
        for i, referenceword in enumerate(referencewords):
            found = False
            best = 0  
            distance = 999999          
            for j, (targetword, lemma, pos, index, multiword) in enumerate(targetwords):
                if referenceword == targetword and abs(i-j) < distance:
                    found = True
                    best = j
                    distance = abs(i-j)

            if found:
                alignment.append(targetwords[best])
            else:                
                alignment.append((None,None,None,None,False)) #no alignment found        
        
        return alignment   

    def reset(self):
        self.f = io.open(self.filename,self.mode, encoding=self.encoding)


    def write(self, sentence):
        self.f.write("#" + str(self.writeindex)+"\n")
        for word, lemma, pos in sentence:
           if not word: word = "NONE"
           if not lemma: lemma = "NONE"
           if not pos: pos = "NONE"
           self.f.write( word + "\t" + lemma + "\t" + pos + "\n" )                
        self.writeindex += 1

    def close(self):
        self.f.close()


########NEW FILE########
__FILENAME__ = timbl
###############################################################
#  PyNLPl - Timbl Classifier Output Library
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#       
#       Derived from code by Sander Canisius
#
#       Licensed under GPLv3
# 
# This library offers a TimblOutput class for reading Timbl
# classifier output. It supports full distributions (+v+db) and comment (#)
#
###############################################################    


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import  
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout 

from pynlpl.statistics import Distribution


class TimblOutput(object):
    """A class for reading Timbl classifier output, supports the +v+db option and ignores comments starting with #"""

    def __init__(self, stream, delimiter = ' ', ignorecolumns = [], ignorevalues = []):
        self.stream = stream
        self.delimiter = delimiter
        self.ignorecolumns = ignorecolumns #numbers, ignore the specified FEATURE columns: first column is 1
        self.ignorevalues = ignorevalues #Ignore columns with the following values

    def __iter__(self):
        # Note: distance parsing (+v+di) works only if distributions (+v+db) are also enabled!
        
        
        for line in self.stream:
            endfvec = None
            line = line.strip()
            if line and line[0] != '#': #ignore empty lines and comments
                segments = [ x for i, x in enumerate(line.split(self.delimiter)) if x not in self.ignorevalues and i+1 not in self.ignorecolumns ]
                              
                #segments = [ x for x in line.split() if x != "^" and not (len(x) == 3 and x[0:2] == "n=") ]  #obtain segments, and filter null fields and "n=?" feature (in fixed-feature configuration)
                

                if not endfvec:
                    try:
                        # Modified by Ruben. There are some cases where one of the features is a {, and then
                        # the module is not able to obtain the distribution of scores and senses
                        # We have to look for the last { in the vector, and due to there is no rindex method
                        # we obtain the reverse and then apply index.
                        aux=list(reversed(segments)).index("{")
                        endfvec=len(segments)-aux-1
                        #endfvec = segments.index("{")            
                    except ValueError:
                        endfvec = None
                            
                if endfvec > 2: #only for +v+db
                    try:
                        enddistr = segments.index('}',endfvec)
                    except ValueError:
                        raise
                    distribution = self.parseDistribution(segments, endfvec, enddistr)
                    if len(segments) > enddistr + 1:
                        distance = float(segments[-1])
                    else:
                        distance = None
                else:
                    endfvec = len(segments)
                    distribution = None
                    distance = None
                                    
                #features, referenceclass, predictedclass, distribution, distance
                yield segments[:endfvec - 2], segments[endfvec - 2], segments[endfvec - 1], distribution, distance    
           

    def parseDistribution(self, instance, start,end= None):
        dist = {}
        i = start + 1

        if not end:
            end = len(instance) - 1

        while i < end:  #instance[i] != "}":
            label = instance[i]
            try:
                score = float(instance[i+1].rstrip(","))
                dist[label] = score
            except:
                print("ERROR: pynlpl.input.timbl.TimblOutput -- Could not fetch score for class '" + label + "', expected float, but found '"+instance[i+1].rstrip(",")+"'. Instance= " + " ".join(instance)+ ".. Attempting to compensate...",file=stderr)
                i = i - 1
            i += 2

            
        if not dist:
            print("ERROR: pynlpl.input.timbl.TimblOutput --  Did not find class distribution for ", instance,file=stderr)

        return Distribution(dist)


########NEW FILE########
__FILENAME__ = client
#!/usr/bin/env python
#-*- coding:utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import    

import socket

class LMClient(object):

    def __init__(self,host= "localhost",port=12346,n = 0):        
        self.BUFSIZE = 1024
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM) #Create the socket
        self.socket.settimeout(120)
        assert isinstance(port,int) 
        self.socket.connect((host, port)) #Connect to server
        assert isinstance(n,int)
        self.n = n

    def scoresentence(self, sentence):
        if self.n > 0:
            raise Exception("This client instance has been set to send only " + str(self.n) +  "-grams")
        if isinstance(sentence,list) or isinstance(sentence,tuple):
            sentence = " ".join(sentence)
        self.socket.send(sentence+ "\r\n")
        return float(self.socket.recv(self.BUFSIZE).strip())

    def __getitem__(self, ngram):
        if self.n == 0:
            raise Exception("This client  has been set to send only full sentence, not n-grams")
        if isinstance(ngram,str) or isinstance(ngram,unicode):
            ngram = ngram.split(" ")
        if len(ngram) != self.n:
            raise Exception("This client instance has been set to send only " + str(self.n) +  "-grams.")
        ngram = " ".join(ngram)
        if (sys.version < '3' and isinstance(ngram,unicode)) or( sys.version == '3' and isinstance(ngram,str)):
            ngram = ngram.encode('utf-8')        
        self.socket.send(ngram + b"\r\n")
        return float(self.socket.recv(self.BUFSIZE).strip())
        
        
        
        

########NEW FILE########
__FILENAME__ = lm
#---------------------------------------------------------------
# PyNLPl - Language Models
#   by Maarten van Gompel, ILK, Universiteit van Tilburg
#   http://ilk.uvt.nl/~mvgompel
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io
import math
import sys

from pynlpl.statistics import FrequencyList, product
from pynlpl.textprocessors import Windower

if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout


class SimpleLanguageModel:
    """This is a simple unsmoothed language model. This class can both hold and compute the model."""

    def __init__(self, n=2, casesensitive = True, beginmarker = "<begin>", endmarker = "<end>"):
        self.casesensitive = casesensitive
        self.freqlistN = FrequencyList(None, self.casesensitive)
        self.freqlistNm1 = FrequencyList(None, self.casesensitive)

        assert isinstance(n,int) and n >= 2
        self.n = n
        self.beginmarker = beginmarker
        self.endmarker = endmarker
        self.sentences = 0

        if self.beginmarker:
            self._begingram = tuple([self.beginmarker] * (n-1))
        if self.endmarker:
            self._endgram = tuple([self.endmarker] * (n-1))

    def append(self, sentence):
        if isinstance(sentence, str) or isinstance(sentence, unicode):
            sentence = sentence.strip().split(' ')
        self.sentences += 1
        for ngram in Windower(sentence,self.n, self.beginmarker, self.endmarker):
            self.freqlistN.count(ngram)
        for ngram in Windower(sentence,self.n-1, self.beginmarker, self.endmarker):
            self.freqlistNm1.count(ngram)


    def load(self, filename):
        self.freqlistN = FrequencyList(None, self.casesensitive)
        self.freqlistNm1 = FrequencyList(None, self.casesensitive)
        f = io.open(filename,'r',encoding='utf-8')
        mode = False
        for line in f.readlines():
            line = line.strip()
            if line:
                if not mode:
                    if line != "[simplelanguagemodel]":
                        raise Exception("File is not a SimpleLanguageModel")
                    else:
                        mode = 1
                elif mode == 1:
                    if line[:2] == 'n=':
                        self.n = int(line[2:])
                    elif line[:12] == 'beginmarker=':
                        self.beginmarker = line[12:]
                    elif line[:10] == 'endmarker=':
                        self.endmarker = line[10:]
                    elif line[:10] == 'sentences=':
                        self.sentences = int(line[10:])
                    elif line[:14] == 'casesensitive=':
                        self.casesensitive = bool(int(line[14:]))
                        self.freqlistN = FrequencyList(None, self.casesensitive)
                        self.freqlistNm1 = FrequencyList(None, self.casesensitive)
                    elif line == "[freqlistN]":
                        mode = 2
                    else:
                        raise Exception("Syntax error in language model file: ", line)
                elif mode == 2:
                    if line == "[freqlistNm1]":
                        mode = 3
                    else:
                        try:
                            type, count = line.split("\t")
                            self.freqlistN.count(type.split(' '),int(count))
                        except:
                            print("Warning, could not parse line whilst loading frequency list: ", line,file=stderr)
                elif mode == 3:
                        try:
                            type, count = line.split("\t")
                            self.freqlistNm1.count(type.split(' '),int(count))
                        except:
                            print("Warning, could not parse line whilst loading frequency list: ", line,file=stderr)

        if self.beginmarker:
            self._begingram = [self.beginmarker] * (self.n-1)
        if self.endmarker:
            self._endgram = [self.endmarker] * (self.n-1)


    def save(self, filename):
        f = io.open(filename,'w',encoding='utf-8')
        f.write("[simplelanguagemodel]\n")
        f.write("n="+str(self.n)+"\n")
        f.write("sentences="+str(self.sentences)+"\n")
        f.write("beginmarker="+self.beginmarker+"\n")
        f.write("endmarker="+self.endmarker+"\n")
        f.write("casesensitive="+str(int(self.casesensitive))+"\n")
        f.write("\n")
        f.write("[freqlistN]\n")
        for line in self.freqlistN.output():
            f.write(line+"\n")
        f.write("[freqlistNm1]\n")
        for line in self.freqlistNm1.output():
            f.write(line+"\n")
        f.close()


    def scoresentence(self, sentence):
        return product([self[x] for x in Windower(sentence, self.n, self.beginmarker, self.endmarker)])


    def __getitem__(self, ngram):
        assert len(ngram) == self.n

        nm1gram = ngram[:-1]

        if (self.beginmarker and nm1gram == self._begingram) or (self.endmarker and nm1gram == self._endgram):
            return self.freqlistN[ngram] / float(self.sentences)
        else:
            return self.freqlistN[ngram] / float(self.freqlistNm1[nm1gram])


class ARPALanguageModel(object):

    """Full back-off language model, loaded from file in ARPA format.

    This class does not build the model but allows you to use a pre-computed one.
    You can use the tool ngram-count from for instance SRILM to actually build the model.

    """

    def __init__(self, filename, encoding='utf-8', encoder=None, base_e=True, dounknown=True, debug=False):
        self.ngrams = {}
        self.backoff = {}
        self.total = {}
        self.base_e = base_e
        self.dounknown = dounknown
        self.debug = debug

        if encoder is None:
            self.encoder = lambda x: x
        else:
            self.encoder = encoder

        with io.open(filename, 'r', encoding=encoding) as f:
            for line in f:
                line = line.strip()
                if line == '\\data\\':
                    order = 0
                elif line == '\\end\\':
                    break
                elif line and line[0] == '\\' and line[-1] == ':':
                    for i in range(1, 10):
                        if line == '\\' + str(i) + '-grams:':
                            order = i
                elif line:
                    if order == 0:
                        if line[0:6] == "ngram":
                            n = int(line[6])
                            v = int(line[8])
                            self.total[n] = v
                    elif order > 0:
                        fields = line.split('\t')
                        if base_e:
                            # * log(10) does log10 to log_e conversion
                            logprob = float(fields[0]) * math.log(10)
                        else:
                            logprob = float(fields[0])
                        ngram = self.encoder(tuple(fields[1].split()))
                        self.ngrams[ngram] = logprob
                        if len(fields) > 2:
                            if base_e:
                                backoffprob = float(fields[2]) * math.log(10)
                            else:
                                backoffprob = float(fields[2])
                            self.backoff[ngram] = backoffprob
                            if self.debug:
                                msg = "Adding to LM: {}\t{}\t{}"
                                print(msg.format(ngram, logprob, backoffprob), file=stderr)
                        elif self.debug:
                            msg = "Adding to LM: {}\t{}"
                            print(msg.format(ngram, logprob), file=stderr)
                    elif self.debug:
                        print("Unable to parse ARPA LM line: " + line, file=stderr)

        self.order = order

    def score(self, data, history=None):
        result = 0
        for word in data:
            result += self.scoreword(word, history)
            if history:
                history += (word,)
            else:
                history = (word,)
        return result

    def scoreword(self, word, history=None):
        if isinstance(word, str) or (sys.version < '3' and isinstance(word, unicode)):
            word = (word,)

        if history:
            lookup = history + word
        else:
            lookup = word

        if len(lookup) > self.order:
            lookup = lookup[-self.order:]

        try:
            return self.ngrams[lookup]
        except KeyError:
            # not found, back off
            if not history:
                if self.dounknown:
                    try:
                        return self.ngrams[('<unk>',)]
                    except KeyError:
                        msg = "Word {} not found. And no history specified and model has no <unk>."
                        raise KeyError(msg.format(word))
                else:
                    msg = "Word {} not found. And no history specified."
                    raise KeyError(msg.format(word))

            try:
                backoffweight = self.backoff[history]
            except KeyError:
                backoffweight = 0  # backoff weight will be 0 if not found
            return backoffweight + self.scoreword(word, history[1:])

    def __len__(self):
        return len(self.ngrams)

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
#-*- coding:utf-8 -*-

#---------------------------------------------------------------
# PyNLPl - Language Models
#   by Maarten van Gompel, ILK, Universiteit van Tilburg
#   http://ilk.uvt.nl/~mvgompel
#   proycon AT anaproy DOT nl
#
#   Generic Server for Language Models
#
#----------------------------------------------------------------

#No Python 3 support for twisted yet...

from twisted.internet import protocol, reactor
from twisted.protocols import basic

class LMSentenceProtocol(basic.LineReceiver):
    def lineReceived(self, sentence):
        try:
            score = self.factory.lm.scoresentence(sentence)
        except:
            score = 0.0
        self.sendLine(str(score))

class LMSentenceFactory(protocol.ServerFactory):
    protocol = LMSentenceProtocol

    def __init__(self, lm):
        self.lm = lm
        
class LMNGramProtocol(basic.LineReceiver):
    def lineReceived(self, ngram):
        ngram = ngram.split(" ")    
        try:
            score = self.factory.lm[ngram]
        except:
            score = 0.0
        self.sendLine(str(score))    
        
class LMNGramFactory(protocol.ServerFactory):
    protocol = LMNGramProtocol

    def __init__(self, lm):
        self.lm = lm        
        
        

class LMServer:
    """Language Model Server"""
    def __init__(self, lm, port=12346, n=0):
        """n indicates the n-gram size, if set to 0 (which is default), the server will expect to only receive whole sentence, if set to a particular value, it will only expect n-grams of that value"""
        if n == 0:
            reactor.listenTCP(port, LMSentenceFactory(lm))
        else:
            reactor.listenTCP(port, LMNGramFactory(lm))
        reactor.run()


########NEW FILE########
__FILENAME__ = srilm
#---------------------------------------------------------------
# PyNLPl - SRILM Language Model
#   by Maarten van Gompel, ILK, Universiteit van Tilburg
#   http://ilk.uvt.nl/~mvgompel
#   proycon AT anaproy DOT nl
#
#   Adapted from code by Sander Canisius
#
#   Licensed under GPLv3
#
#
# This library enables using SRILM as language model
#
#----------------------------------------------------------------

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import    

import srilmcc
from pynlpl.textprocessors import Windower

class SRILM:
    def __init__(self, filename, n):
        self.model = srilmcc.LanguageModel(filename, n)
        self.n = n

    def scoresentence(self, sentence, unknownwordprob=-12):
        score = 0
        for ngram in Windower(sentence, self.n, "<s>", "</s>"):
            try:
               score += self.logscore(ngram)
            except KeyError:
               score += unknownwordprob
        return 10**score

    def __getitem__(self, ngram):
        return 10**self.logscore(ngram)

    def __contains__(self, key):
        return self.model.exists( key )

    def logscore(self, ngram):
        #Bug work-around
        #if "" in ngram or "_" in ngram or "__" in ngram:
        #    print >> sys.stderr, "WARNING: Invalid word in n-gram! Ignoring", ngram 
        #    return -999.9

        if len(ngram) == self.n:
            if all( (self.model.exists(x) for x in ngram) ):
                #no phrases, basic trigram, compute directly
                return self.model.wordProb(*ngram)
            else:
                raise KeyError
        else:
            raise Exception("Not an " + str(self.n) + "-gram")


########NEW FILE########
__FILENAME__ = wordalign
from pynlpl.statistics import FrequencyList, Distribution


class WordAlignment(object):

    def __init__(self, casesensitive = False):
        self.casesensitive = casesensitive

    def train(self, sourcefile, targetfile):
        sourcefile = open(sourcefile)
        targetfile = open(targetfile)

        self.sourcefreqlist = FrequencyList(None, self.casesensitive)
        self.targetfreqlist = FrequencyList(None, self.casesensitive)

        #frequency lists
        self.source2target = {}
        self.target2source = {}

        for sourceline, targetline in zip(sourcefile, targetfile):
            sourcetokens = sourceline.split()
            targettokens = targetline.split()

            self.sourcefreqlist.append(sourcetokens)
            self.targetfreqlist.append(targettokens)

            for sourcetoken in sourcetokens:
                if not sourcetoken in self.source2target:
                    self.source2target[sourcetoken] = FrequencyList(targettokens,self.casesensitive)
                else:
                    self.source2target[sourcetoken].append(targettokens)

            for targettoken in targettokens:
                if not targettoken in self.target2source:
                    self.target2source[targettoken] = FrequencyList(sourcetokens,self.casesensitive)
                else:
                    self.target2source[targettoken].append(sourcetokens)

        sourcefile.close()
        targetfile.close()

    def test(self, sourcefile, targetfile):
        sourcefile = open(sourcefile)
        targetfile = open(targetfile)


        #stage 2
        for sourceline, targetline in zip(sourcefile, targetfile):
            sourcetokens = sourceline.split()
            targettokens = targetline.split()

            S2Talignment = []
            T2Salignment = []

            for sourcetoken in sourcetokens:
                #which of the target-tokens is most frequent?
                besttoken = None
                bestscore = -1
                for i, targettoken in enumerate(targettokens):
                    if targettoken in self.source2target[sourcetoken]:
                        score = self.source2target[sourcetoken][targettoken] / float(self.targetfreqlist[targettoken])
                        if score > bestscore:
                            bestscore = self.source2target[sourcetoken][targettoken]
                            besttoken = i
                S2Talignment.append(besttoken) #TODO: multi-alignment?

            for targettoken in targettokens:
                besttoken = None
                bestscore = -1
                for i, sourcetoken in enumerate(sourcetokens):
                    if sourcetoken in self.target2source[targettoken]:
                        score = self.target2source[targettoken][sourcetoken] / float(self.sourcefreqlist[sourcetoken])
                        if score > bestscore:
                            bestscore = self.target2source[targettoken][sourcetoken]
                            besttoken = i
                T2Salignment.append(besttoken) #TODO: multi-alignment?

            yield sourcetokens, targettokens, S2Talignment, T2Salignment

        sourcefile.close()
        targetfile.close()


########NEW FILE########
__FILENAME__ = net
#-*- coding:utf-8 -*-

#---------------------------------------------------------------
# PyNLPl - Network utilities
#   by Maarten van Gompel
#   Centre for Language Studies
#   Radboud University Nijmegen
#   http://www.github.com/proycon/pynlpl
#   proycon AT anaproy DOT nl
#
#   Generic Server for Language Models
#
#----------------------------------------------------------------

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from pynlpl.common import u,b
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout
from twisted.internet import protocol, reactor # will fail on Python 3 for now
from twisted.protocols import basic
import shlex



class GWSNetProtocol(basic.LineReceiver):
    def connectionMade(self):
        print("Client connected", file=stderr)
        self.factory.connections += 1
        if self.factory.connections != 1:
            self.transport.loseConnection()
        else:
            self.sendLine(b("READY"))

    def lineReceived(self, line):
        try:
            print("Client in: " + line,file=stderr)
        except UnicodeDecodeError:
            print("Client in: (unicodeerror)",file=stderr)
        self.factory.processprotocol.transport.write(b(line +'\n'))
        self.factory.processprotocol.currentclient = self

    def connectionLost(self, reason):
        self.factory.connections -= 1
        if self.factory.processprotocol.currentclient == self:
            self.factory.processprotocol.currentclient = None

class GWSFactory(protocol.ServerFactory):
    protocol = GWSNetProtocol

    def __init__(self, processprotocol):
        self.connections = 0
        self.processprotocol = processprotocol


class GWSProcessProtocol(protocol.ProcessProtocol):
    def __init__(self, printstderr=True, sendstderr= False, filterout = None, filtererr = None):
        self.currentclient = None
        self.printstderr = printstderr
        self.sendstderr = sendstderr
        if not filterout:
            self.filterout = lambda x: x
        else:
            self.filterout = filterout
        if not filtererr:
            self.filtererr = lambda x: x
        else:
            self.filtererr = filtererr

    def connectionMade(self):
        pass

    def outReceived(self, data):
        try:
            print("Process out " + data,file=stderr)
        except UnicodeDecodeError:
            print("Process out (unicodeerror)",file=stderr)
        for line in b(data).strip().split(b('\n')):
            line = self.filterout(line.strip())
            if self.currentclient and line:
                self.currentclient.sendLine(line)

    def errReceived(self, data):
        try:
            print("Process err " + data,file=stderr)
        except UnicodeDecodeError:
            print("Process out (unicodeerror)",file=stderr)
        if self.printstderr and data:
            print(data.strip(),file=stderr)
        for line in b(data).strip().split(b('\n')):
            line = self.filtererr(line.strip())
            if self.sendstderr and self.currentclient and line:
                self.currentclient.sendLine(line)


    def processExited(self, reason):
        print("Process exited",file=stderr)


    def processEnded(self, reason):
        print("Process ended",file=stderr)
        if self.currentclient:
            self.currentclient.transport.loseConnection()
        reactor.stop()


class GenericWrapperServer:
    """Generic Server around a stdin/stdout based CLI tool. Only accepts one client at a time to prevent concurrency issues !!!!!"""
    def __init__(self, cmdline, port, printstderr= True, sendstderr= False, filterout = None, filtererr = None):
        gwsprocessprotocol = GWSProcessProtocol(printstderr, sendstderr, filterout, filtererr)
        cmdline = shlex.split(cmdline)
        reactor.spawnProcess(gwsprocessprotocol, cmdline[0], cmdline)

        gwsfactory = GWSFactory(gwsprocessprotocol)
        reactor.listenTCP(port, gwsfactory)
        reactor.run()

########NEW FILE########
__FILENAME__ = search
#---------------------------------------------------------------
# PyNLPl - Search Algorithms
#   by Maarten van Gompel
#   Centre for Language Studies
#   Radboud University Nijmegen
#   http://www.github.com/proycon/pynlpl
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------

"""This module contains various search algorithms."""

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
#from pynlpl.common import u
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout
from pynlpl.datatypes import FIFOQueue, PriorityQueue
from collections import deque
from bisect import bisect_left


class AbstractSearchState(object):
    def __init__(self,  parent = None, cost = 0):
        self.parent = parent        
        self.cost = cost

    def test(self, goalstates = None):
        """Checks whether this state is a valid goal state, returns a boolean. If no goalstate is defined, then all states will test positively, this is what you usually want for optimisation problems."""
        if goalstates:
            return (self in goalstates)
        else:
            return True
            #raise Exception("Classes derived from AbstractSearchState must define a test() method!")

    def score(self):
        """Should return a heuristic value. This needs to be set if you plan to used an informed search algorithm."""
        raise Exception("Classes derived from AbstractSearchState must define a score() method if used in informed search algorithms!")

    def expand(self):
        """Generates successor states, implement your custom operators in the derived method."""
        raise Exception("Classes derived from AbstractSearchState must define an expand() method!")

    def __eq__(self):
        """Implement an equality test in the derived method, based only on the state's content (not its path etc!)"""
        raise Exception("Classes derived from AbstractSearchState must define an __eq__() method!")

    def __lt__(self, other):
        assert isinstance(other, AbstractSearchState)
        return self.score() < other.score()

    def __gt__(self, other):
        assert isinstance(other, AbstractSearchState)
        return self.score() > other.score()

    
    def __hash__(self):
        """Return a unique hash for this state, based on its ID"""
        raise Exception("Classes derived from AbstractSearchState must define a __hash__() method if the search space is a graph and visited nodes to be are stored in memory!")        


    def depth(self):
        if not self.parent:
            return 0
        else:
            return self.parent.depth() + 1            

    #def __len__(self):
    #    return len(self.path())

    def path(self):
        if not self.parent:
            return [self]
        else: 
            return self.parent.path() + [self]

    def pathcost(self):
        if not self.parent:
            return self.cost
        else: 
            return self.parent.pathcost() + self.cost


        

    #def __cmp__(self, other):
    #    if self.score < other.score:
    #        return -1
    #    elif self.score > other.score:
    #        return 1
    #    else:
    #        return 0

class AbstractSearch(object): #not a real search, just a base class for DFS and BFS
    def __init__(self, **kwargs):
        """For graph-searches graph=True is required (default), otherwise the search may loop forever. For tree-searches, set tree=True for better performance"""
        self.usememory = True
        self.poll = lambda x: x.pop
        self.maxdepth = False #unlimited
        self.minimize = False #minimize rather than maximize the score function? default: no
        self.keeptraversal = False
        self.goalstates = None
        self.exhaustive = False #only some subclasses use this
        self.traversed = 0 #Count of number of nodes visited
        self.solutions = 0 #Counts the number of solutions
        self.debug = 0

        for key, value in kwargs.items():
            if key == 'graph':
                self.usememory = value #search space is a graph? memory required to keep visited states
            elif key == 'tree':
                self.usememory = not value;  #search space is a tree? memory not required
            elif key == 'poll':
                self.poll = value #function
            elif key == 'maxdepth':
                self.maxdepth = value
            elif key == 'minimize':
                self.minimize = value
            elif key == 'maximize':
                self.minimize = not value
            elif key == 'keeptraversal': #remember entire traversal?
                self.keeptraversal = value
            elif key == 'goal' or key == 'goals':
                if isinstance(value, list) or isinstance(value, tuple):
                    self.goalstates = value
                else:
                    self.goalstates = [value]
            elif key == 'exhaustive':
                self.exhaustive = True
            elif key == 'debug':
                self.debug = value
        self._visited = {}
        self._traversal = []
        self.incomplete = False
        self.traversed = 0

    def reset(self):
        self._visited = {}
        self._traversal = []
        self.incomplete = False
        self.traversed = 0 #Count of all visited nodes
        self.solutions = 0 #Counts the number of solutions found     

    def traversal(self):
        """Returns all visited states (only when keeptraversal=True), note that this is not equal to the path, but contains all states that were checked!"""
        if self.keeptraversal:
            return self._traversal
        else:
            raise Exception("No traversal available, algorithm not started with keeptraversal=True!")
    
    def traversalsize(self):
        """Returns the number of nodes visited  (also when keeptravel=False). Note that this is not equal to the path, but contains all states that were checked!"""
        return self.traversed
        

    def visited(self, state):
        if self.usememory:
            return (hash(state) in self._visited)
        else:
            raise Exception("No memory kept, algorithm not started with graph=True!")
        
    def __iter__(self):
        """Generator yielding *all* valid goalstates it can find,"""
        n = 0
        while len(self.fringe) > 0:
            n += 1
            if self.debug: print("\t[pynlpl debug] *************** ITERATION #" + str(n) + " ****************",file=stderr)
            if self.debug: print("\t[pynlpl debug] FRINGE: ", self.fringe,file=stderr)
            state = self.poll(self.fringe)()
            if self.debug:
                try:
                    print("\t[pynlpl debug] CURRENT STATE (depth " + str(state.depth()) + "): " + str(state),end="",file=stderr)
                except AttributeError:
                    print("\t[pynlpl debug] CURRENT STATE: " + str(state),end="",file=stderr)
                    
                print(" hash="+str(hash(state)),file=stderr)
                try:
                    print(" score="+str(state.score()),file=stderr)
                except:
                    pass
 

            #If node not visited before (or no memory kept):
            if not self.usememory or (self.usememory and not hash(state) in self._visited):
                
                #Evaluate the current state
                self.traversed += 1
                if state.test(self.goalstates):
                    if self.debug: print("\t[pynlpl debug] Valid goalstate, yielding",file=stderr)
                    yield state
                elif self.debug:
                    print("\t[pynlpl debug] (no goalstate, not yielding)",file=stderr)
                
                #Expand the specified state and add to the fringe

                
                #if self.debug: print >>stderr,"\t[pynlpl debug] EXPANDING:"
                statecount = 0
                for i, s in enumerate(state.expand()):
                    statecount += 1
                    if self.debug >= 2:
                        print("\t[pynlpl debug] (Iteration #" + str(n) +") Expanded state #" + str(i+1) + ", adding to fringe: " + str(s),end="",file=stderr)
                        try:
                            print(s.score(),file=stderr)
                        except:
                            print("ERROR SCORING!",file=stderr)
                            pass
                    if not self.maxdepth or s.depth() <= self.maxdepth:
                        self.fringe.append(s)
                    else:
                        if self.debug: print("\t[pynlpl debug] (Iteration #" + str(n) +") Not adding to fringe, maxdepth exceeded",file=stderr)
                        self.incomplete = True
                if self.debug:
                    print("\t[pynlpl debug] Expanded " + str(statecount) + " states, offered to fringe",file=stderr)
                if self.keeptraversal: self._traversal.append(state)
                if self.usememory: self._visited[hash(state)] = True
                self.prune(state) #calls prune method
            else:
                if self.debug:
                    print("\t[pynlpl debug] State already visited before, not expanding again...(hash="+str(hash(state))+")",file=stderr)
        if self.debug:
            print("\t[pynlpl debug] Search complete: " + str(self.solutions) + " solution(s), " + str(self.traversed) + " states traversed in " + str(n) + " rounds",file=stderr)
    
    def searchfirst(self):
        """Returns the very first result (regardless of it being the best or not!)"""
        for solution in self:
            return solution

    def searchall(self):
        """Returns a list of all solutions"""
        return list(iter(self))

    def searchbest(self):
        """Returns the single best result (if multiple have the same score, the first match is returned)"""
        finalsolution = None
        bestscore = None
        for solution in self:
            if bestscore == None:
                bestscore = solution.score()
                finalsolution = solution
            elif self.minimize:
                score = solution.score()
                if score < bestscore:
                    bestscore = score
                    finalsolution = solution
            elif not self.minimize:
                score = solution.score()
                if score > bestscore:
                    bestscore = score
                    finalsolution = solution                
        return finalsolution

    def searchtop(self,n=10):
        """Return the top n best resulta (or possibly less if not enough is found)"""            
        solutions = PriorityQueue([], lambda x: x.score, self.minimize, length=n, blockworse=False, blockequal=False,duplicates=False)
        for solution in self:
            solutions.append(solution)
        return solutions

    def searchlast(self,n=10):
        """Return the last n results (or possibly less if not found). Note that the last results are not necessarily the best ones! Depending on the search type."""            
        solutions = deque([], n)
        for solution in self:
            solutions.append(solution)
        return solutions

    def prune(self, state):
        """Pruning method is called AFTER expansion of each node"""
        #pruning nothing by default
        pass

class DepthFirstSearch(AbstractSearch):

    def __init__(self, state, **kwargs):
        assert isinstance(state, AbstractSearchState)
        self.fringe = [ state ]
        super(DepthFirstSearch,self).__init__(**kwargs)         



class BreadthFirstSearch(AbstractSearch):


    def __init__(self, state, **kwargs):
        assert isinstance(state, AbstractSearchState)
        self.fringe = FIFOQueue([state])
        super(BreadthFirstSearch,self).__init__(**kwargs)         


class IterativeDeepening(AbstractSearch):

    def __init__(self, state, **kwargs):
        assert isinstance(state, AbstractSearchState)
        self.state = state
        self.kwargs = kwargs
        self.traversed = 0

    def __iter__(self):
        self.traversed = 0
        d = 0
        while not 'maxdepth' in self.kwargs or d <= self.kwargs['maxdepth']:
            dfs = DepthFirstSearch(self.state, **self.kwargs)
            self.traversed += dfs.traversalsize()
            for match in dfs:
                yield match
            if dfs.incomplete:
                d +=1 
            else:
                break

    def traversal(self):
        #TODO: add
        raise Exception("not implemented yet")

    def traversalsize(self):
        return self.traversed


class BestFirstSearch(AbstractSearch):

    def __init__(self, state, **kwargs):
        super(BestFirstSearch,self).__init__(**kwargs)
        assert isinstance(state, AbstractSearchState)
        self.fringe = PriorityQueue([state], lambda x: x.score, self.minimize, length=0, blockworse=False, blockequal=False,duplicates=False)

class BeamSearch(AbstractSearch):
    """Local beam search algorithm"""

    def __init__(self, states, beamsize, **kwargs):
        if isinstance(states, AbstractSearchState):
            states = [states]
        else:
            assert all( ( isinstance(x, AbstractSearchState) for x in states) )
        self.beamsize = beamsize      
        if 'eager' in kwargs:
            self.eager = kwargs['eager']
        else:
            self.eager = False
        super(BeamSearch,self).__init__(**kwargs)
        self.incomplete = True
        self.duplicates = kwargs['duplicates'] if 'duplicates' in kwargs else False
        self.fringe = PriorityQueue(states, lambda x: x.score, self.minimize, length=0, blockworse=False, blockequal=False,duplicates= self.duplicates)

    def __iter__(self):
        """Generator yielding *all* valid goalstates it can find"""
        i = 0
        while len(self.fringe) > 0:
            i +=1 
            if self.debug: print("\t[pynlpl debug] *************** STARTING ROUND #" + str(i) + " ****************",file=stderr)
            
            b = 0
            #Create a new empty fixed-length priority queue (this implies there will be pruning if more items are offered than it can hold!)
            successors = PriorityQueue([], lambda x: x.score, self.minimize, length=self.beamsize, blockworse=False, blockequal=False,duplicates= self.duplicates)
            
            while len(self.fringe) > 0:
                b += 1
                if self.debug: print("\t[pynlpl debug] *************** ROUND #" + str(i) + " BEAM# " + str(b) + " ****************",file=stderr)
                #if self.debug: print >>stderr,"\t[pynlpl debug] FRINGE: ", self.fringe

                state = self.poll(self.fringe)()
                if self.debug:
                    try:
                        print("\t[pynlpl debug] CURRENT STATE (depth " + str(state.depth()) + "): " + str(state),end="",file=stderr)
                    except AttributeError:
                        print("\t[pynlpl debug] CURRENT STATE: " + str(state),end="",file=stderr)
                    print(" hash="+str(hash(state)),file=stderr)
                    try:
                        print(" score="+str(state.score()),file=stderr)
                    except:
                        pass


                if not self.usememory or (self.usememory and not hash(state) in self._visited):
                    
                    self.traversed += 1
                    #Evaluate state
                    if state.test(self.goalstates):
                        if self.debug: print("\t[pynlpl debug] Valid goalstate, yielding",file=stderr)
                        self.solutions += 1 #counts the number of solutions
                        yield state
                    elif self.debug:
                        print("\t[pynlpl debug] (no goalstate, not yielding)",file=stderr)

                    if self.eager:
                        score = state.score()                    

                    #Expand the specified state and offer to the fringe
                    
                    statecount = offers = 0
                    for j, s in enumerate(state.expand()):
                        statecount += 1
                        if self.debug >= 2:
                            print("\t[pynlpl debug] (Round #" + str(i) +" Beam #" + str(b) + ") Expanded state #" + str(j+1) + ", offering to successor pool: " + str(s),end="",file=stderr)
                            try:
                                print(s.score(),end="",file=stderr)
                            except:
                                print("ERROR SCORING!",end="",file=stderr)
                                pass
                        if not self.maxdepth or s.depth() <= self.maxdepth:
                            if not self.eager:
                                #use all successors (even worse ones than the current state)
                                offers += 1
                                accepted = successors.append(s)
                            else:
                                #use only equal or better successors
                                if s.score() >= score:
                                    offers += 1
                                    accepted = successors.append(s)
                                else:
                                    accepted = False
                            if self.debug >= 2:
                                if accepted:
                                    print(" ACCEPTED",file=stderr)
                                else:
                                    print(" REJECTED",file=stderr)
                        else:                            
                            if self.debug >= 2:
                                print(" REJECTED, MAXDEPTH EXCEEDED.",file=stderr)
                            elif self.debug:
                                print("\t[pynlpl debug] Not offered to successor pool, maxdepth exceeded",file=stderr)
                    if self.debug:
                        print("\t[pynlpl debug] Expanded " + str(statecount) + " states, " + str(offers) + " offered to successor pool",file=stderr)
                    if self.keeptraversal: self._traversal.append(state)
                    if self.usememory: self._visited[hash(state)] = True
                    self.prune(state) #calls prune method (does nothing by default in this search!!!)

                else:
                    if self.debug:
                        print("\t[pynlpl debug] State already visited before, not expanding again... (hash=" + str(hash(state))  +")",file=stderr)
            #AFTER EXPANDING ALL NODES IN THE FRINGE/BEAM:
            
            #set fringe for next round
            self.fringe = successors

            #Pruning is implicit, successors was a fixed-size priority queue
            if self.debug: 
                print("\t[pynlpl debug] (Round #" + str(i) + ") Implicitly pruned with beamsize " + str(self.beamsize) + "...",file=stderr)
            #self.fringe.prune(self.beamsize)
            if self.debug: print(" (" + str(offers) + " to " + str(len(self.fringe)) + " items)",file=stderr)
        
        if self.debug:
            print("\t[pynlpl debug] Search complete: " + str(self.solutions) + " solution(s), " + str(self.traversed) + " states traversed in " + str(i) + " rounds with " + str(b) + "  beams",file=stderr)            
        
        
        

class EarlyEagerBeamSearch(AbstractSearch):
    """A beam search that prunes early (after each state expansion) and eagerly (weeding out worse successors)"""
    
    def __init__(self, state, beamsize, **kwargs):
        assert isinstance(state, AbstractSearchState)
        self.beamsize = beamsize       
        super(EarlyEagerBeamSearch,self).__init__(**kwargs)
        self.fringe = PriorityQueue(state, lambda x: x.score, self.minimize, length=0, blockworse=False, blockequal=False,duplicates= kwargs['duplicates'] if 'duplicates' in kwargs else False)
        self.incomplete = True
    
    
    def prune(self, state):
        if self.debug: 
            l = len(self.fringe)
            print("\t[pynlpl debug] pruning with beamsize " + str(self.beamsize) + "...",end="",file=stderr)
        self.fringe.prunebyscore(state.score(), retainequalscore=True)
        self.fringe.prune(self.beamsize)
        if self.debug: print(" (" + str(l) + " to " + str(len(self.fringe)) + " items)",file=stderr)


class BeamedBestFirstSearch(BeamSearch):
    """Best first search with a beamsize (non-optimal!)"""
    
    def prune(self, state):
        if self.debug: 
            l = len(self.fringe)
            print("\t[pynlpl debug] pruning with beamsize " + str(self.beamsize) + "...",end="",file=stderr)
        self.fringe.prune(self.beamsize)
        if self.debug: print(" (" + str(l) + " to " + str(len(self.fringe)) + " items)",file=stderr)

class StochasticBeamSearch(BeamSearch):
    
    def prune(self, state):
        if self.debug: 
            l = len(self.fringe)
            print("\t[pynlpl debug] pruning with beamsize " + str(self.beamsize) + "...",end="",file=stderr)
        if not self.exhaustive:
            self.fringe.prunebyscore(state.score(), retainequalscore=True)
        self.fringe.stochasticprune(self.beamsize)
        if self.debug: print(" (" + str(l) + " to " + str(len(self.fringe)) + " items)",file=stderr)
            

class HillClimbingSearch(AbstractSearch): #TODO: TEST
    """(identical to beamsearch with beam 1, but implemented differently)"""

    def __init__(self, state, **kwargs):
        assert isinstance(state, AbstractSearchState)
        super(HillClimbingSearch,self).__init__(**kwargs)
        self.fringe = PriorityQueue([state], lambda x: x.score, self.minimize, length=0, blockworse=True, blockequal=False,duplicates=False)

#From http://stackoverflow.com/questions/212358/binary-search-in-python
def binary_search(a, x, lo=0, hi=None):   # can't use a to specify default for hi 
    hi = hi if hi is not None else len(a) # hi defaults to len(a)   
    pos = bisect_left(a,x,lo,hi)          # find insertion position
    return (pos if pos != hi and a[pos] == x else -1) # don't walk off the end

########NEW FILE########
__FILENAME__ = statistics
###############################################################
#  PyNLPp - Statistics & Information Theory Library
#   by Maarten van Gompel
#   Centre for Language Studies
#   Radboud University Nijmegen
#   http://www.github.com/proycon/pynlpl
#   proycon AT anaproy DOT nl
#       
#       Also contains MIT licensed code from
#        AI: A Modern Appproach : http://aima.cs.berkeley.edu/python/utils.html
#        Peter Norvig
#
#       Licensed under GPLv3
#
###############################################################


"""This is a Python library containing classes for Statistic and Information Theoretical computations. It also contains some code from Peter Norvig, AI: A Modern Appproach : http://aima.cs.berkeley.edu/python/utils.html"""

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from pynlpl.common import u, isstring
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout
import io

import math
import random
import operator
from collections import Counter



class FrequencyList(object):
    """A frequency list (implemented using dictionaries)"""

    def __init__(self, tokens = None, casesensitive = True, dovalidation = True):
        self._count = Counter()
        self._ranked = {}
        self.total = 0 #number of tokens
        self.casesensitive = casesensitive
        self.dovalidation = dovalidation
        if tokens: self.append(tokens)

    
    def load(self, filename):
        """Load a frequency list from file (in the format produced by the save method)"""
        f = io.open(filename,'r',encoding='utf-8')
        for line in f:            
            data = line.strip().split("\t")
            type, count = data[:2]            
            self.count(type,count)
        f.close()
            

    def save(self, filename, addnormalised=False):
        """Save a frequency list to file, can be loaded later using the load method"""
        f = io.open(filename,'w',encoding='utf-8')
        for line in self.output("\t", addnormalised):
            f.write(line + '\n')
        f.close()

    def _validate(self,type):
        if isinstance(type,list):
            type = tuple(type)
        if isinstance(type,tuple):
            if not self.casesensitive: 
                return tuple([x.lower() for x in type])
            else:
                return type
        else:
            if not self.casesensitive: 
                return type.lower()
            else:
                return type

    def append(self,tokens):
        """Add a list of tokens to the frequencylist. This method will count them for you."""
        for token in tokens:
            self.count(token)


    def count(self, type, amount = 1):
        """Count a certain type. The counter will increase by the amount specified (defaults to one)"""        
        if self.dovalidation: type = self._validate(type)
        if self._ranked: self._ranked = None
        if type in self._count:
            self._count[type] += amount
        else:
            self._count[type] = amount
        self.total += amount

    def sum(self):
        """Returns the total amount of tokens"""
        return self.total

    def _rank(self):
        if not self._ranked: self._ranked = self._count.most_common()

    def __iter__(self):
        """Iterate over the frequency lists, in order (frequent to rare). This is a generator that yields (type, count) pairs. The first time you iterate over the FrequencyList, the ranking will be computed. For subsequent calls it will be available immediately, unless the frequency list changed in the meantime."""
        self._rank()
        for type, count in self._ranked:
            yield type, count

    def items(self):
        """Returns an *unranked* list of (type, count) pairs. Use this only if you are not interested in the order."""
        for type, count in  self._count.items():
            yield type, count

    def __getitem__(self, type):
        if self.dovalidation: type = self._validate(type)
        try:
            return self._count[type]
        except KeyError:
            return 0

    def __setitem__(self, type, value):
        """alias for count, but can only be called once"""
        if self.dovalidation: type = self._validate(type)
        if not type in self._count:
            self.count(type,value)     
        else:
            raise ValueError("This type is already set!")
            
    def __delitem__(self, type):
        if self.dovalidation: type = self._validate(type)
        del self._count[type]
        if self._ranked: self._ranked = None
        
    
    def typetokenratio(self):
        """Computes the type/token ratio"""
        return len(self._count) / float(self.total)

    def __len__(self):
        """Returns the total amount of types"""
        return len(self._count)

    def tokens(self):
        """Returns the total amount of tokens"""
        return self.total

    def mode(self):
        """Returns the type that occurs the most frequently in the frequency list"""
        self._rank()
        return self._ranked[0][0]


    def p(self, type): 
        """Returns the probability (relative frequency) of the token"""
        if self.dovalidation: type = self._validate(type)
        return self._count[type] / float(self.total)


    def __eq__(self, otherfreqlist):
        return (self.total == otherfreqlist.total and self._count == otherfreqlist._count)

    def __contains__(self, type):
        """Checks if the specified type is in the frequency list"""
        if self.dovalidation: type = self._validate(type)
        return type in self._count

    def __add__(self, otherfreqlist):
        """Multiple frequency lists can be added together"""
        assert isinstance(otherfreqlist,FrequencyList)
        product = FrequencyList(None,)
        for type, count in self.items():
            product.count(type,count)        
        for type, count in otherfreqlist.items():
            product.count(type,count)        
        return product

    def output(self,delimiter = '\t', addnormalised=False):
        """Print a representation of the frequency list"""
        for type, count in self:
            if isinstance(type,tuple) or isinstance(type,list):
                if addnormalised:
                    yield " ".join((u(x) for x in type)) + delimiter + str(count) + delimiter + str(count/self.total)
                else:
                    yield " ".join((u(x) for x in type)) + delimiter + str(count)
            elif isstring(type):
                if addnormalised:
                    yield type + delimiter + str(count) + delimiter + str(count/self.total)
                else:
                    yield type + delimiter + str(count)
            else:
                if addnormalised:
                    yield str(type) + delimiter + str(count) + delimiter + str(count/self.total)
                else:
                    yield str(type) + delimiter + str(count)

    def __repr__(self):
        return repr(self._count)
        
    def __unicode__(self): #Python 2
        return str(self)   
        
    def __str__(self):
        return "\n".join(self.output())        
        
    def values(self):
        return self._count.values()

    def dict(self):
        return self._count
    

#class FrequencyTrie:
#    def __init__(self):
#        self.data = Tree()
#        
#    def count(self, sequence):
#            
#        
#        self.data.append( Tree(item) )
    
    
        

class Distribution(object):
    """A distribution can be created over a FrequencyList or a plain dictionary with numeric values. It will be normalized automatically. This implemtation uses dictionaries/hashing"""

    def __init__(self, data, base = 2):
        self.base = base #logarithmic base: can be set to 2, 10 or math.e (or anything else). when set to None, it's set to e automatically
        self._dist = {}
        if isinstance(data, FrequencyList):
            for type, count in data.items():
                self._dist[type] = count / data.total
        elif isinstance(data, dict) or isinstance(data, list):
            if isinstance(data, list):
                self._dist = {}
                for key,value in data:
                    self._dist[key] = float(value)
            else:
                self._dist = data 
            total = sum(self._dist.values())
            if total < 0.999 or total > 1.000:
                #normalize again
                for key, value in self._dist.items():
                    self._dist[key] = value / total                       
        else:
            raise Exception("Can't create distribution")
        self._ranked = None
        


    def _rank(self):
        if not self._ranked: self._ranked = sorted(self._dist.items(),key=lambda x: x[1], reverse=True )

    def information(self, type):
        """Computes the information content of the specified type: -log_e(p(X))"""
        if not self.base:
            return -math.log(self._dist[type])
        else:
            return -math.log(self._dist[type], self.base)

    def poslog(self, type):
        """alias for information content"""
        return self.information(type)

    def entropy(self, base = 2):
        """Compute the entropy of the distribution"""
        entropy = 0
        if not base and self.base: base = self.base
        for type in self._dist:
            if not base:
                entropy += self._dist[type] * -math.log(self._dist[type])     
            else:
                entropy += self._dist[type] * -math.log(self._dist[type], base)     
        return entropy

    def perplexity(self, base=2):
        return base ** self.entropy(base)

    def mode(self):
        """Returns the type that occurs the most frequently in the probability distribution"""
        self._rank()
        return self._ranked[0][0]

    def maxentropy(self, base = 2):     
        """Compute the maximum entropy of the distribution: log_e(N)"""   
        if not base and self.base: base = self.base
        if not base:
            return math.log(len(self._dist))
        else:
            return math.log(len(self._dist), base)

    def __len__(self):
        """Returns the number of types"""
        return len(self._dist)

    def __getitem__(self, type):
        """Return the probability for this type"""
        return self._dist[type]

    def __iter__(self):
        """Iterate over the *ranked* distribution, returns (type, probability) pairs"""       
        self._rank()
        for type, p in self._ranked:
            yield type, p

    def items(self):
        """Returns an *unranked* list of (type, prob) pairs. Use this only if you are not interested in the order."""
        for type, count in  self._dist.items():
            yield type, count

    def output(self,delimiter = '\t', freqlist = None):
        """Generator yielding formatted strings expressing the time and probabily for each item in the distribution"""
        for type, prob in self:   
            if freqlist:
                if isinstance(type,list) or isinstance(type, tuple):
                    yield " ".join(type) + delimiter + str(freqlist[type]) + delimiter + str(prob)
                else:
                    yield type + delimiter + str(freqlist[type]) + delimiter + str(prob)
            else:
                if isinstance(type,list) or isinstance(type, tuple):
                    yield " ".join(type) + delimiter + str(prob)
                else:
                    yield type + delimiter + str(prob)
                

    def __unicode__(self):
        return str(self)

    def __str__(self):
        return "\n".join(self.output())

    def __repr__(self):
        return repr(self._dist)
    
    def keys(self):
        return self._dist.keys()    
        
    def values(self):
        return self._dist.values()
        
        
class MarkovChain(object):
    def __init__(self, startstate, endstate = None):
        self.nodes = set()
        self.edges_out = {}
        self.startstate = startstate
        self.endstate = endstate
        
    def settransitions(self, state, distribution):
        self.nodes.add(state)
        if not isinstance(distribution, Distribution):
            distribution = Distribution(distribution)
        self.edges_out[state] = distribution
        self.nodes.update(distribution.keys())
        
    def __iter__(self):
        for state, distribution in self.edges_out.items():
            yield state, distribution
            
    def __getitem__(self, state):
        for distribution in self.edges_out[state]:
            yield distribution
        
    def size(self):
        return len(self.nodes)
        
    def accessible(self,fromstate, tostate):
        """Is state tonode directly accessible (in one step) from state fromnode? (i.e. is there an edge between the nodes). If so, return the probability, else zero"""
        if (not (fromstate in self.nodes)) or (not (tostate in self.nodes)) or not (fromstate in self.edges_out):
            return 0
        if tostate in self.edges_out[fromstate]:
            return self.edges_out[fromstate][tostate]
        else:
            return 0
        
        
    def communicates(self,fromstate, tostate, maxlength=999999):
        """See if a node communicates (directly or indirectly) with another. Returns the probability of the *shortest* path (probably, but not necessarily the highest probability)"""
        if (not (fromstate in self.nodes)) or (not (tostate in self.nodes)):
            return 0
        assert (fromstate != tostate)   
        
            
        def _test(node,length,prob):            
            if length > maxlength:
                return 0
            if node == tostate:
                prob *= self.edges_out[node][tostate]
                return True
            
            for child in self.edges_out[node].keys():
                if not child in visited:
                    visited.add(child)
                    if child == tostate:
                        return prob * self.edges_out[node][tostate]
                    else:
                        r = _test(child, length+1, prob * self.edges_out[node][tostate])
                        if r: 
                            return r
            return 0
                            
        visited = set(fromstate)
        return _test(fromstate,1,1)
            
    def p(self, sequence, subsequence=True):
        """Returns the probability of the given sequence or subsequence (if subsequence=True, default)."""
        if sequence[0] != self.startstate:
            if isinstance(sequence, tuple):
                sequence = (self.startstate,) + sequence
            else:
                sequence = (self.startstate,) + tuple(sequence)
        if self.endstate:
            if sequence[-1] != self.endstate:
                if isinstance(sequence, tuple):
                    sequence = sequence + (self.endstate,) 
                else:    
                    sequence = tuple(sequence) + (self.endstate,) 
        
        prevnode = None
        prob = 1
        for node in sequence:
            if prevnode:
                try:
                    prob *= self.edges_out[prevnode][node]
                except: 
                    return 0
        return prob


    def __contains__(self, sequence):
        """Is the given sequence generated by the markov model? Does not work for subsequences!"""
        return bool(self.p(sequence,False))
    
    
    
    def reducible(self):
        #TODO: implement
        raise NotImplementedError

        
        
        
class HiddenMarkovModel(MarkovChain):
    def __init__(self, startstate, endstate = None):
        self.observablenodes = set()
        self.edges_toobservables = {}
        super(HiddenMarkovModel, self).__init__(startstate,endstate)
        
    def setemission(self, state, distribution):
        self.nodes.add(state)
        if not isinstance(distribution, Distribution):
            distribution = Distribution(distribution)
        self.edges_toobservables[state] = distribution
        self.observablenodes.update(distribution.keys())        

    def print_dptable(self, V):
        print("    ",end="",file=stdout)
        for i in range(len(V)): print("%7s" % ("%d" % i),end="",file=stdout)
        print(file=stdout)
     
        for y in V[0].keys():
            print("%.5s: " % y, end="",file=stdout)
            for t in range(len(V)):
                print("%.7s" % ("%f" % V[t][y]),end="",file=stdout)
            print(file=stdout)
     
    #Adapted from: http://en.wikipedia.org/wiki/Viterbi_algorithm 
    def viterbi(self,observations, doprint=False):
        #states, start_p, trans_p, emit_p):
        
        V = [{}] #Viterbi matrix
        path = {}
     
        # Initialize base cases (t == 0)
        for node in self.edges_out[self.startstate].keys():
            try:
                V[0][node] = self.edges_out[self.startstate][node] * self.edges_toobservables[node][observations[0]]
                path[node] = [node]
            except KeyError:
                pass #will be 0, don't store
     
        # Run Viterbi for t > 0
        for t in range(1,len(observations)):
            V.append({})
            newpath = {}
     
            for node in self.nodes:
                column = []
                for prevnode in V[t-1].keys():
                    try:
                        column.append( (V[t-1][prevnode] * self.edges_out[prevnode][node] * self.edges_toobservables[node][observations[t]],  prevnode ) )
                    except KeyError:
                        pass #will be 0 
                
                if column:
                    (prob, state) = max(column)
                    V[t][node] = prob
                    newpath[node] = path[state] + [node]
     
            # Don't need to remember the old paths
            path = newpath
     
        if doprint: self.print_dptable(V)
        
        if not V[len(observations) - 1]:
            return (0,[])
        else:
            (prob, state) = max([(V[len(observations) - 1][node], node) for node in V[len(observations) - 1].keys()])
            return (prob, path[state])

    

# ********************* Common Functions ******************************

def product(seq):
    """Return the product of a sequence of numerical values.
    >>> product([1,2,6])
    12
    """
    if len(seq) == 0:
        return 0
    else:
        product = 1
        for x in seq:
            product *= x
        return product



# All below functions are mathematical functions from  AI: A Modern Approach, see: http://aima.cs.berkeley.edu/python/utils.html 

def histogram(values, mode=0, bin_function=None): #from AI: A Modern Appproach 
    """Return a list of (value, count) pairs, summarizing the input values.
    Sorted by increasing value, or if mode=1, by decreasing count.
    If bin_function is given, map it over values first."""
    if bin_function: values = map(bin_function, values)
    bins = {}
    for val in values:
        bins[val] = bins.get(val, 0) + 1
    if mode:
        return sorted(bins.items(), key=lambda v: v[1], reverse=True)
    else:
        return sorted(bins.items())
 
def log2(x):  #from AI: A Modern Appproach 
    """Base 2 logarithm.
    >>> log2(1024)
    10.0
    """
    return math.log(x, 2)

def mode(values):  #from AI: A Modern Appproach 
    """Return the most common value in the list of values.
    >>> mode([1, 2, 3, 2])
    2
    """
    return histogram(values, mode=1)[0][0]

def median(values):  #from AI: A Modern Appproach 
    """Return the middle value, when the values are sorted.
    If there are an odd number of elements, try to average the middle two.
    If they can't be averaged (e.g. they are strings), choose one at random.
    >>> median([10, 100, 11])
    11
    >>> median([1, 2, 3, 4])
    2.5
    """
    n = len(values)
    values = sorted(values)
    if n % 2 == 1:
        return values[n/2]
    else:
        middle2 = values[(n/2)-1:(n/2)+1]
        try:
            return mean(middle2)
        except TypeError:
            return random.choice(middle2)

def mean(values):  #from AI: A Modern Appproach 
    """Return the arithmetic average of the values."""
    return sum(values) / len(values)

def stddev(values, meanval=None):  #from AI: A Modern Appproach 
    """The standard deviation of a set of values.
    Pass in the mean if you already know it."""
    if meanval == None: meanval = mean(values)
    return math.sqrt( sum([(x - meanval)**2 for x in values]) / (len(values)-1) )

def dotproduct(X, Y):  #from AI: A Modern Appproach 
    """Return the sum of the element-wise product of vectors x and y.
    >>> dotproduct([1, 2, 3], [1000, 100, 10])
    1230
    """
    return sum([x * y for x, y in zip(X, Y)])

def vector_add(a, b):  #from AI: A Modern Appproach 
    """Component-wise addition of two vectors.
    >>> vector_add((0, 1), (8, 9))
    (8, 10)
    """
    return tuple(map(operator.add, a, b))



def normalize(numbers, total=1.0):  #from AI: A Modern Appproach 
    """Multiply each number by a constant such that the sum is 1.0 (or total).
    >>> normalize([1,2,1])
    [0.25, 0.5, 0.25]
    """
    k = total / sum(numbers)
    return [k * n for n in numbers]

###########################################################################################

def levenshtein(s1, s2):
    """Computes the levenshtein distance between two strings. From:  http://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python"""
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




########NEW FILE########
__FILENAME__ = tagger
#! /usr/bin/env python
# -*- coding: utf8 -*-


###############################################################
#  PyNLPl - FreeLing Library
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Radboud University Nijmegen
#       
#       Licensed under GPLv3
# 
# Generic Tagger interface for PoS-tagging and lemmatisation,
# offers an interface to various software
#
###############################################################

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from pynlpl.common import u
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout

import io
import codecs
import json
import getopt
import subprocess
    
class Tagger(object):    
     def __init__(self, *args):        
        global WSDDIR
        self.tagger = None
        self.mode = args[0]
        if args[0] == "file":
            if len(args) != 2:
                raise Exception("Syntax: file:[filename]")            
            self.tagger = codecs.open(args[1],'r','utf-8') 
        elif args[0] == "frog":
            if len(args) != 3:
                raise Exception("Syntax: frog:[host]:[port]")
            from pynlpl.clients.frogclient import FrogClient
            port = int(args[2])
            self.tagger = FrogClient(args[1],port)                
        elif args[0] == "freeling":
            if len(args) != 3:
                raise Exception("Syntax: freeling:[host]:[port]")
            from pynlpl.clients.freeling import FreeLingClient
            host = args[1]
            port = int(args[2])
            self.tagger = FreeLingClient(host,port)            
        elif args[0] == "corenlp":
            if len(args) != 1:
                raise Exception("Syntax: corenlp")
            import corenlp
            print("Initialising Stanford Core NLP",file=stderr)
            self.tagger = corenlp.StanfordCoreNLP()
        elif args[0] == 'treetagger':                        
            if not len(args) == 2:
                raise Exception("Syntax: treetagger:[treetagger-bin]")
            self.tagger = args[1]            
        elif args[0] == "durmlex":
            if not len(args) == 2:
                raise Exception("Syntax: durmlex:[filename]")
            print("Reading durm lexicon: ", args[1],file=stderr)
            self.mode = "lookup"
            self.tagger = {}
            f = codecs.open(args[1],'r','utf-8')
            for line in f:
                fields = line.split('\t')
                wordform = fields[0].lower()
                lemma = fields[4].split('.')[0]
                self.tagger[wordform] = (lemma, 'n')
            f.close()
            print("Loaded ", len(self.tagger), " wordforms",file=stderr)
        elif args[0] == "oldlex":
            if not len(args) == 2:
                raise Exception("Syntax: oldlex:[filename]")
            print("Reading OLDLexique: ", args[1],file=stderr)
            self.mode = "lookup"
            self.tagger = {}
            f = codecs.open(args[1],'r','utf-8')
            for line in f:
                fields = line.split('\t')
                wordform = fields[0].lower()                
                lemma = fields[1]
                if lemma == '=': 
                    lemma == fields[0]
                pos = fields[2][0].lower()
                self.tagger[wordform] = (lemma, pos)
                print("Loaded ", len(self.tagger), " wordforms",file=stderr)
            f.close()        
        else:
            raise Exception("Invalid mode: " + args[0])
        
     def __iter__(self):
        if self.mode != 'file':
            raise Exception("Iteration only possible in file mode")
        line = self.tagger.next()
        newwords = []
        postags = []
        lemmas = []    
        for item in line:            
            word,lemma,pos = item.split('|')
            newwords.append(word)
            postags.append(pos)
            lemmas.append(lemma)
        yield newwords, postags, lemmas        
        
     def reset(self):
        if self.mode == 'file':
            self.tagger.seek(0)
        
        
     def process(self, words, debug=False):
        if self.mode == 'file':
            line = self.tagger.next()
            newwords = []
            postags = []
            lemmas = []    
            for item in line.split(' '):                            
                if item.strip():
                    try:
                        word,lemma,pos = item.split('|')
                    except:
                        raise Exception("Unable to parse word|lemma|pos in " + item)
                    newwords.append(word)
                    postags.append(pos)
                    lemmas.append(lemma)
            return newwords, postags, lemmas
        elif self.mode == "frog":
            newwords = []
            postags = []
            lemmas = []             
            for fields in self.tagger.process(' '.join(words)):
                word,lemma,morph,pos = fields[:4]
                newwords.append(word)
                postags.append(pos)
                lemmas.append(lemma)
            return newwords, postags, lemmas                
        elif self.mode == "freeling":
            postags = []
            lemmas = []
            for fields in self.tagger.process(words, debug):
                word, lemma,pos = fields[:3]
                postags.append(pos)
                lemmas.append(lemma)
            return words, postags, lemmas            
        elif self.mode == "corenlp":            
            data = json.loads(self.tagger.parse(" ".join(words)))
            words = []
            postags = []
            lemmas = []
            for sentence in data['sentences']:
                for word, worddata in sentence['words']:
                    words.append(word)
                    lemmas.append(worddata['Lemma'])
                    postags.append(worddata['PartOfSpeech'])
            return words, postags, lemmas
        elif self.mode == 'lookup':
            postags = []
            lemmas = []
            for word in words:
                try:
                    lemma, pos = self.tagger[word.lower()]
                    lemmas.append(lemma)
                    postags.append(pos)
                except KeyError: 
                    lemmas.append(word)
                    postags.append('?')
            return words, postags, lemmas
        elif self.mode == 'treetagger':
            s = " ".join(words)
            s = u(s)
            
            p = subprocess.Popen([self.tagger], shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)            
            (out, err) = p.communicate(s.encode('utf-8'))

            newwords = []
            postags = []
            lemmas = []
            for line in out.split('\n'):
                line = line.strip()
                if line:
                    fields = line.split('\t')
                    newwords.append( unicode(fields[0],'utf-8') )
                    postags.append( unicode(fields[1],'utf-8') )
                    lemmas.append( unicode(fields[2],'utf-8') )
                                        
            if p.returncode != 0:
                print(err,file=stderr)
                raise OSError('TreeTagger failed')
        
            return newwords, postags, lemmas
        else:
            raise Exception("Unknown mode")
    
    
     
    
     def treetagger_tag(self, f_in, f_out,oneperline=False, debug=False):
        
        def flush(sentences):
            if sentences:
                print("Processing " + str(len(sentences)) + " lines",file=stderr)                
                for sentence in sentences:
                    out = ""
                    p = subprocess.Popen([self.tagger], shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    (results, err) = p.communicate("\n".join(sentences).encode('utf-8'))
                    for line in results.split('\n'):
                        line = line.strip()
                        if line:
                            fields = line.split('\t')
                            word = fields[0]
                            pos = fields[1]
                            lemma = fields[2]
                            if oneperline:
                                if out: out += "\n"
                                out += word + "\t" + lemma + "\t" + pos
                            else: 
                                if out: out += " "
                                if '|' in word:
                                    word = word.replace('|','_')
                                if '|' in lemma:
                                    lemma = lemma.replace('|','_') 
                                if '|' in pos:
                                    pos = pos.replace('|','_') 
                            out += word + "|" + lemma + "|" + pos
                            if pos[0] == '$':
                                out = u(out)
                                f_out.write(out + "\n")        
                                if oneperline: f_out.write("\n")
                                out = ""
                            
                if out:
                   out = u(out)
                   f_out.write(out + "\n")   
                   if oneperline: f_out.write("\n")
                

        #buffered tagging
        sentences = []
        linenum = 0
        
        for line in f_in:                        
            linenum += 1
            print(" Buffering input @" + str(linenum),file=stderr)
            line = line.strip()
            if not line or ('.' in line[:-1] or '?' in line[:-1] or '!' in line[:-1]) or (line[-1] != '.' and line[-1] != '?' and line[-1] != '!'): 
                flush(sentences)
                sentences = []
                if not line.strip():
                    f_out.write("\n")
                    if oneperline: f_out.write("\n") 
            sentences.append(line)
        flush(sentences)
                        
    
     def tag(self, f_in, f_out,oneperline=False, debug=False):
        if self.mode == 'treetagger':
            self.treetagger_tag(f_in, f_out,oneperline=False, debug=False) 
        else:
            linenum = 0
            for line in f_in:
                linenum += 1
                print(" Tagger input @" + str(linenum),file=stderr)
                if line.strip():
                    words = line.strip().split(' ')
                    words, postags, lemmas = self.process(words, debug)
                    out = ""
                    for word, pos, lemma in zip(words,postags, lemmas):
                       if word is None: word = ""
                       if lemma is None: lemma = "?"
                       if pos is None: pos = "?"                    
                       if oneperline:
                            if out: out += "\n"
                            out += word + "\t" + lemma + "\t" + pos
                       else: 
                            if out: out += " "
                            if '|' in word:
                                word = word.replace('|','_')
                            if '|' in lemma:
                                lemma = lemma.replace('|','_') 
                            if '|' in pos:
                                pos = pos.replace('|','_') 
                            out += word + "|" + lemma + "|" + pos
                    if not isinstance(out, unicode):
                        out = unicode(out, 'utf-8')
                    f_out.write(out + "\n")
                    if oneperline:
                        f_out.write("\n")
                else:
                    f_out.write("\n")

def usage():
    print("tagger.py -c [conf] -f [input-filename] -o [output-filename]",file=stderr) 

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:c:o:D")
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err),file=stderr)
        usage()
        sys.exit(2)   
    
    taggerconf = None
    filename = None
    outfilename = None        
    oneperline = False
    debug = False
        
    for o, a in opts:
        if o == "-c":	
            taggerconf = a
        elif o == "-f":	
            filename = a
        elif o == '-o':
            outfilename =a
        elif o == '-l':
            oneperline = True
        elif o == '-D':
            debug = True
        else: 
            print >>sys.stderr,"Unknown option: ", o
            sys.exit(2)
    

    if not taggerconf:
        print("ERROR: Specify a tagger configuration with -c",file=stderr)
        sys.exit(2)
    if not filename:
        print("ERROR: Specify a filename with -f",file=stderr)
        sys.exit(2)
    
        
    if outfilename: 
        f_out = io.open(outfilename,'w',encoding='utf-8')
    else:
        f_out = stdout;
        
    f_in = io.open(filename,'r',encoding='utf-8')
    
    tagger = Tagger(*taggerconf.split(':'))
    tagger.tag(f_in, f_out, oneperline, debug)
    
    f_in.close()
    if outfilename:
        f_out.close()
    
      
            
        

########NEW FILE########
__FILENAME__ = cgn
#!/usr/bin/env python
#-*- coding:utf-8 -*-


#---------------------------------------------------------------
# PyNLPl - Test Units for CGN 
#   by Maarten van Gompel, ILK, Universiteit van Tilburg
#   http://ilk.uvt.nl/~mvgompel
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

import sys
import os
import unittest


if sys.version < '3':
    from StringIO import StringIO
else:
    from io import StringIO
    
import lxml.etree
from pynlpl.formats import cgn

class CGNtest(unittest.TestCase):
    def test(self):        
        """CGN - Splitting PoS tags into features"""
        global CLASSES
        #Do it again, but supress exceptions (only stderr output for missing features so we have one big list)
        for poscls in CLASSES.split('\n'):
            if poscls:
                cgn.parse_cgn_postag(poscls, False)

        #Do it again, raising an exception this time
        for poscls in CLASSES.split('\n'):
            if poscls:
                cgn.parse_cgn_postag(poscls, True)    
                
    
CLASSES = """
TSW(dial)
N(soort,dial)
N(eigen,dial)
ADJ(dial)
WW(dial)
TW(hoofd,dial)
TW(rang,dial)
VNW(pers,pron,dial)
VNW(refl,pron,dial)
VNW(recip,pron,dial)
VNW(bez,det,dial)
VNW(vrag,pron,dial)
VNW(vrag,det,dial)
VNW(betr,pron,dial)
VNW(betr,det,dial)
VNW(excl,pron,dial)
VNW(excl,det,dial)
VNW(aanw,pron,dial)
VNW(aanw,det,dial)
VNW(onbep,pron,dial)
VNW(onbep,det,dial)
LID(bep,dial)
LID(onbep,dial)
VZ(init,dial)
VZ(fin,dial)
VG(neven,dial)
VG(onder,dial)
BW(dial)
TSW()
SPEC(afgebr)
SPEC(onverst)
SPEC(vreemd)
SPEC(deeleigen)
SPEC(meta)
LET()
SPEC(comment)
SPEC(achter)
SPEC(afk)
SPEC(symb)
N(soort,ev,basis,zijd,stan)
N(soort,ev,basis,onz,stan)
N(soort,ev,dim,onz,stan)
N(soort,ev,basis,gen)
N(soort,ev,dim,gen)
N(soort,ev,basis,dat)
N(soort,mv,basis)
N(soort,mv,dim)
N(eigen,ev,basis,zijd,stan)
N(eigen,ev,basis,onz,stan)
N(eigen,ev,dim,onz,stan)
N(eigen,ev,basis,gen)
N(eigen,ev,dim,gen)
N(eigen,ev,basis,dat)
N(eigen,mv,basis)
N(eigen,mv,dim)
ADJ(prenom,basis,zonder)
ADJ(prenom,basis,met-e,stan)
ADJ(prenom,basis,met-e,bijz)
ADJ(prenom,comp,zonder)
ADJ(prenom,comp,met-e,stan)
ADJ(prenom,comp,met-e,bijz)
ADJ(prenom,sup,zonder)
ADJ(prenom,sup,met-e,stan)
ADJ(prenom,sup,met-e,bijz)
ADJ(nom,basis,zonder,zonder-n)
ADJ(nom,basis,zonder,mv-n)
ADJ(nom,basis,met-e,zonder-n,stan)
ADJ(nom,basis,met-e,zonder-n,bijz)
ADJ(nom,basis,met-e,mv-n)
ADJ(nom,comp,zonder,zonder-n)
ADJ(nom,comp,met-e,zonder-n,stan)
ADJ(nom,comp,met-e,zonder-n,bijz)
ADJ(nom,comp,met-e,mv-n)
ADJ(nom,sup,zonder,zonder-n)
ADJ(nom,sup,met-e,zonder-n,stan)
ADJ(nom,sup,met-e,zonder-n,bijz)
ADJ(nom,sup,met-e,mv-n)
ADJ(postnom,basis,zonder)
ADJ(postnom,basis,met-s)
ADJ(postnom,comp,zonder)
ADJ(postnom,comp,met-s)
ADJ(vrij,basis,zonder)
ADJ(vrij,comp,zonder)
ADJ(vrij,sup,zonder)
ADJ(vrij,dim,zonder)
WW(pv,tgw,ev)
WW(pv,tgw,mv)
WW(pv,tgw,met-t)
WW(pv,verl,ev)
WW(pv,verl,mv)
WW(pv,verl,met-t)
WW(pv,conj,ev)
WW(inf,prenom,zonder)
WW(inf,prenom,met-e)
WW(inf,nom,zonder,zonder-n)
WW(inf,vrij,zonder)
WW(vd,prenom,zonder)
WW(vd,prenom,met-e)
WW(vd,nom,met-e,zonder-n)
WW(vd,nom,met-e,mv-n)
WW(vd,vrij,zonder)
WW(od,prenom,zonder)
WW(od,prenom,met-e)
WW(od,nom,met-e,zonder-n)
WW(od,nom,met-e,mv-n)
WW(od,vrij,zonder)
TW(hoofd,prenom,stan)
TW(hoofd,prenom,bijz)
TW(hoofd,nom,zonder-n,basis)
TW(hoofd,nom,mv-n,basis)
TW(hoofd,nom,zonder-n,dim)
TW(hoofd,nom,mv-n,dim)
TW(hoofd,vrij)
TW(rang,prenom,stan)
TW(rang,prenom,bijz)
TW(rang,nom,zonder-n)
TW(rang,nom,mv-n)
VNW(pers,pron,nomin,vol,1,ev)
VNW(pers,pron,nomin,nadr,1,ev)
VNW(pers,pron,nomin,red,1,ev)
VNW(pers,pron,nomin,vol,1,mv)
VNW(pers,pron,nomin,nadr,1,mv)
VNW(pers,pron,nomin,red,1,mv)
VNW(pers,pron,nomin,vol,2v,ev)
VNW(pers,pron,nomin,nadr,2v,ev)
VNW(pers,pron,nomin,red,2v,ev)
VNW(pers,pron,nomin,nadr,3m,ev,masc)
VNW(pers,pron,nomin,vol,3v,ev,fem)
VNW(pers,pron,nomin,nadr,3v,ev,fem)
VNW(pers,pron,obl,vol,2v,ev)
VNW(pers,pron,obl,nadr,3m,ev,masc)
VNW(pers,pron,gen,vol,1,ev)
VNW(pers,pron,gen,vol,1,mv)
VNW(pers,pron,gen,vol,3m,ev)
VNW(bez,det,gen,vol,1,ev,prenom,zonder,evmo)
VNW(bez,det,gen,vol,1,mv,prenom,met-e,evmo)
VNW(bez,det,gen,vol,3v,ev,prenom,zonder,evmo)
VNW(bez,det,dat,vol,1,ev,prenom,met-e,evmo)
VNW(bez,det,dat,vol,1,ev,prenom,met-e,evf)
VNW(bez,det,dat,vol,1,mv,prenom,met-e,evmo)
VNW(bez,det,dat,vol,1,mv,prenom,met-e,evf)
VNW(bez,det,dat,vol,2v,ev,prenom,met-e,evf)
VNW(bez,det,dat,vol,3v,ev,prenom,met-e,evmo)
VNW(bez,det,dat,vol,3v,ev,prenom,met-e,evf)
VNW(bez,det,dat,vol,1,ev,nom,met-e,zonder-n)
VNW(bez,det,dat,vol,1,mv,nom,met-e,zonder-n)
VNW(bez,det,dat,vol,3m,ev,nom,met-e,zonder-n)
VNW(bez,det,dat,vol,3v,ev,nom,met-e,zonder-n)
VNW(betr,pron,gen,vol,3o,ev)
VNW(aanw,pron,gen,vol,3m,ev)
VNW(aanw,pron,gen,vol,3o,ev)
VNW(aanw,det,dat,prenom,met-e,evmo)
VNW(aanw,det,dat,prenom,met-e,evf)
VNW(aanw,det,gen,nom,met-e,zonder-n)
VNW(aanw,det,dat,nom,met-e,zonder-n)
VNW(onbep,det,gen,prenom,met-e,mv)
VNW(onbep,det,dat,prenom,met-e,evmo)
VNW(onbep,det,dat,prenom,met-e,evf)
VNW(onbep,det,gen,nom,met-e,mv-n)
VNW(onbep,grad,gen,nom,met-e,mv-n,basis)
LID(bep,stan,evon)
LID(bep,stan,rest)
LID(bep,gen,evmo)
LID(bep,dat,evmo)
LID(bep,dat,evf)
LID(bep,dat,mv)
LID(onbep,gen,evf)
VZ(init)
VZ(fin)
VZ(versm)
VG(neven)
VG(onder)
BW()
N(soort,ev,basis,genus,stan)
N(eigen,ev,basis,genus,stan)
VNW(pers,pron,nomin,vol,2b,getal)
VNW(pers,pron,nomin,nadr,2b,getal)
VNW(pers,pron,nomin,vol,2,getal)
VNW(pers,pron,nomin,nadr,2,getal)
VNW(pers,pron,nomin,red,2,getal)
VNW(pers,pron,nomin,vol,3,ev,masc)
VNW(pers,pron,nomin,red,3,ev,masc)
VNW(pers,pron,nomin,red,3p,ev,masc)
VNW(pers,pron,nomin,vol,3p,mv)
VNW(pers,pron,nomin,nadr,3p,mv)
VNW(pers,pron,obl,vol,3,ev,masc)
VNW(pers,pron,obl,red,3,ev,masc)
VNW(pers,pron,obl,vol,3,getal,fem)
VNW(pers,pron,obl,nadr,3v,getal,fem)
VNW(pers,pron,obl,red,3v,getal,fem)
VNW(pers,pron,obl,vol,3p,mv)
VNW(pers,pron,obl,nadr,3p,mv)
VNW(pers,pron,stan,nadr,2v,mv)
VNW(pers,pron,stan,red,3,ev,onz)
VNW(pers,pron,stan,red,3,ev,fem)
VNW(pers,pron,stan,red,3,mv)
VNW(pers,pron,gen,vol,2,getal)
VNW(pers,pron,gen,vol,3v,getal)
VNW(pers,pron,gen,vol,3p,mv)
VNW(pr,pron,obl,vol,1,ev)
VNW(pr,pron,obl,nadr,1,ev)
VNW(pr,pron,obl,red,1,ev)
VNW(pr,pron,obl,vol,1,mv)
VNW(pr,pron,obl,nadr,1,mv)
VNW(pr,pron,obl,red,2v,getal)
VNW(pr,pron,obl,nadr,2v,getal)
VNW(pr,pron,obl,vol,2,getal)
VNW(pr,pron,obl,nadr,2,getal)
VNW(refl,pron,obl,red,3,getal)
VNW(refl,pron,obl,nadr,3,getal)
VNW(recip,pron,obl,vol,persoon,mv)
VNW(recip,pron,gen,vol,persoon,mv)
VNW(bez,det,stan,vol,1,ev,prenom,zonder,agr)
VNW(bez,det,stan,vol,1,ev,prenom,met-e,rest)
VNW(bez,det,stan,red,1,ev,prenom,zonder,agr)
VNW(bez,det,stan,vol,1,mv,prenom,zonder,evon)
VNW(bez,det,stan,vol,1,mv,prenom,met-e,rest)
VNW(bez,det,stan,vol,2,getal,prenom,zonder,agr)
VNW(bez,det,stan,vol,2,getal,prenom,met-e,rest)
VNW(bez,det,stan,vol,2v,ev,prenom,zonder,agr)
VNW(bez,det,stan,red,2v,ev,prenom,zonder,agr)
VNW(bez,det,stan,nadr,2v,mv,prenom,zonder,agr)
VNW(bez,det,stan,vol,3,ev,prenom,zonder,agr)
VNW(bez,det,stan,vol,3m,ev,prenom,met-e,rest)
VNW(bez,det,stan,vol,3v,ev,prenom,met-e,rest)
VNW(bez,det,stan,red,3,ev,prenom,zonder,agr)
VNW(bez,det,stan,vol,3,mv,prenom,zonder,agr)
VNW(bez,det,stan,vol,3p,mv,prenom,met-e,rest)
VNW(bez,det,stan,red,3,getal,prenom,zonder,agr)
VNW(bez,det,gen,vol,1,ev,prenom,met-e,rest3)
VNW(bez,det,gen,vol,1,mv,prenom,met-e,rest3)
VNW(bez,det,gen,vol,2,getal,prenom,zonder,evmo)
VNW(bez,det,gen,vol,2,getal,prenom,met-e,rest3)
VNW(bez,det,gen,vol,2v,ev,prenom,met-e,rest3)
VNW(bez,det,gen,vol,3,ev,prenom,zonder,evmo)
VNW(bez,det,gen,vol,3,ev,prenom,met-e,rest3)
VNW(bez,det,gen,vol,3v,ev,prenom,met-e,rest3)
VNW(bez,det,gen,vol,3p,mv,prenom,zonder,evmo)
VNW(bez,det,gen,vol,3p,mv,prenom,met-e,rest3)
VNW(bez,det,dat,vol,2,getal,prenom,met-e,evmo)
VNW(bez,det,dat,vol,2,getal,prenom,met-e,evf)
VNW(bez,det,dat,vol,3,ev,prenom,met-e,evmo)
VNW(bez,det,dat,vol,3,ev,prenom,met-e,evf)
VNW(bez,det,dat,vol,3p,mv,prenom,met-e,evmo)
VNW(bez,det,dat,vol,3p,mv,prenom,met-e,evf)
VNW(bez,det,stan,vol,1,ev,nom,met-e,zonder-n)
VNW(bez,det,stan,vol,1,mv,nom,met-e,zonder-n)
VNW(bez,det,stan,vol,2,getal,nom,met-e,zonder-n)
VNW(bez,det,stan,vol,2v,ev,nom,met-e,zonder-n)
VNW(bez,det,stan,vol,3m,ev,nom,met-e,zonder-n)
VNW(bez,det,stan,vol,3v,ev,nom,met-e,zonder-n)
VNW(bez,det,stan,vol,3p,mv,nom,met-e,zonder-n)
VNW(bez,det,stan,vol,1,ev,nom,met-e,mv-n)
VNW(bez,det,stan,vol,1,mv,nom,met-e,mv-n)
VNW(bez,det,stan,vol,2,getal,nom,met-e,mv-n)
VNW(bez,det,stan,vol,2v,ev,nom,met-e,mv-n)
VNW(bez,det,stan,vol,3m,ev,nom,met-e,mv-n)
VNW(bez,det,stan,vol,3v,ev,nom,met-e,mv-n)
VNW(bez,det,stan,vol,3p,mv,nom,met-e,mv-n)
VNW(bez,det,dat,vol,2,getal,nom,met-e,zonder-n)
VNW(bez,det,dat,vol,3p,mv,nom,met-e,zonder-n)
VNW(vrag,pron,stan,nadr,3o,ev)
VNW(betr,pron,stan,vol,persoon,getal)
VNW(betr,pron,stan,vol,3,ev)
VNW(betr,det,stan,nom,zonder,zonder-n)
VNW(betr,det,stan,nom,met-e,zonder-n)
VNW(betr,pron,gen,vol,3o,getal)
VNW(vb,pron,stan,vol,3p,getal)
VNW(vb,pron,stan,vol,3o,ev)
VNW(vb,pron,gen,vol,3m,ev)
VNW(vb,pron,gen,vol,3v,ev)
VNW(vb,pron,gen,vol,3p,mv)
VNW(vb,adv-pron,obl,vol,3o,getal)
VNW(excl,pron,stan,vol,3,getal)
VNW(vb,det,stan,prenom,zonder,evon)
VNW(vb,det,stan,prenom,met-e,rest)
VNW(vb,det,stan,nom,met-e,zonder-n)
VNW(excl,det,stan,vrij,zonder)
VNW(aanw,pron,stan,vol,3o,ev)
VNW(aanw,pron,stan,nadr,3o,ev)
VNW(aanw,pron,stan,vol,3,getal)
VNW(aanw,adv-pron,obl,vol,3o,getal)
VNW(aanw,adv-pron,stan,red,3,getal)
VNW(aanw,det,stan,prenom,zonder,evon)
VNW(aanw,det,stan,prenom,zonder,rest)
VNW(aanw,det,stan,prenom,zonder,agr)
VNW(aanw,det,stan,prenom,met-e,rest)
VNW(aanw,det,gen,prenom,met-e,rest3)
VNW(aanw,det,stan,nom,met-e,zonder-n)
VNW(aanw,det,stan,nom,met-e,mv-n)
VNW(aanw,det,stan,vrij,zonder)
VNW(onbep,pron,stan,vol,3p,ev)
VNW(onbep,pron,stan,vol,3o,ev)
VNW(onbep,pron,gen,vol,3p,ev)
VNW(onbep,adv-pron,obl,vol,3o,getal)
VNW(onbep,adv-pron,gen,red,3,getal)
VNW(onbep,det,stan,prenom,zonder,evon)
VNW(onbep,det,stan,prenom,zonder,agr)
VNW(onbep,det,stan,prenom,met-e,evz)
VNW(onbep,det,stan,prenom,met-e,mv)
VNW(onbep,det,stan,prenom,met-e,rest)
VNW(onbep,det,stan,prenom,met-e,agr)
VNW(onbep,grad,stan,prenom,zonder,agr,basis)
VNW(onbep,grad,stan,prenom,met-e,agr,basis)
VNW(onbep,grad,stan,prenom,met-e,mv,basis)
VNW(onbep,grad,stan,prenom,zonder,agr,comp)
VNW(onbep,grad,stan,prenom,met-e,agr,sup)
VNW(onbep,grad,stan,prenom,met-e,agr,comp)
VNW(onbep,det,stan,nom,met-e,mv-n)
VNW(onbep,det,stan,nom,met-e,zonder-n)
VNW(onbep,det,stan,nom,zonder,zonder-n)
VNW(onbep,grad,stan,nom,met-e,zonder-n,basis)
VNW(onbep,grad,stan,nom,met-e,mv-n,basis)
VNW(onbep,grad,stan,nom,met-e,zonder-n,sup)
VNW(onbep,grad,stan,nom,met-e,mv-n,sup)
VNW(onbep,grad,stan,nom,zonder,mv-n,dim)
VNW(onbep,det,stan,vrij,zonder)
VNW(onbep,grad,stan,vrij,zonder,basis)
VNW(onbep,grad,stan,vrij,zonder,sup)
VNW(onbep,grad,stan,vrij,zonder,comp)
LID(bep,gen,rest3)
LID(onbep,stan,agr)
VNW(onbep,grad,stan,nom,zonder,zonder-n,sup)
SPEC(enof)
"""

    
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = datatypes
#!/usr/bin/env python
#-*- coding:utf-8 -*-

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from pynlpl.common import u

import os
import sys
import unittest


from pynlpl.datatypes import PriorityQueue

values = [3,6,6,1,8,2]
mintomax = sorted(values)
maxtomin = list(reversed(mintomax))


class PriorityQueueTest(unittest.TestCase):
    def test_append_minimized(self):
        """Minimized PriorityQueue"""
        global values
        pq = PriorityQueue(values, lambda x: x, True,0,False,False)
        result = list(iter(pq))
        self.assertEqual(result, mintomax)

    def test_append_maximized(self):
        """Maximized PriorityQueue"""
        global values
        pq = PriorityQueue(values, lambda x: x, False,0,False,False)
        result = list(iter(pq))
        self.assertEqual(result, maxtomin)

    def test_append_maximized_blockworse(self):
        """Maximized PriorityQueue (with blockworse)"""
        global values
        pq = PriorityQueue(values, lambda x: x, False,0,True,False)
        result = list(iter(pq))
        self.assertEqual(result, [8,6,6,3])

    def test_append_maximized_blockworse_blockequal(self):
        """Maximized PriorityQueue (with blockworse + blockequal)"""
        global values
        pq = PriorityQueue(values, lambda x: x, False,0,True,True)
        result = list(iter(pq))
        self.assertEqual(result, [8,6,3])

    def test_append_minimized_blockworse(self):
        """Minimized PriorityQueue (with blockworse)"""
        global values
        pq = PriorityQueue(values, lambda x: x, True,0,True,False)
        result = list(iter(pq))
        self.assertEqual(result, [1,3])
        

    def test_append_minimized_fixedlength(self):
        """Fixed-length priority queue (min)"""
        global values
        pq = PriorityQueue(values, lambda x: x, True,4, False,False)
        result = list(iter(pq))
        self.assertEqual(result, mintomax[:4])        

    def test_append_maximized_fixedlength(self):
        """Fixed-length priority queue (max)"""
        global values
        pq = PriorityQueue(values, lambda x: x, False,4,False,False)
        result = list(iter(pq))
        self.assertEqual(result, maxtomin[:4])                


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = evaluation
#!/usr/bin/env python
#-*- coding:utf-8 -*-

#---------------------------------------------------------------
# PyNLPl - Test Units for Evaluation
#   by Maarten van Gompel, ILK, Universiteit van Tilburg
#   http://ilk.uvt.nl/~mvgompel
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#
#-------------------------------------------------------------

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from pynlpl.common import u

import sys
import os
import unittest
import random

from pynlpl.evaluation import AbstractExperiment, WPSParamSearch, ExperimentPool, ClassEvaluation

class ParamExperiment(AbstractExperiment):
    def defaultparameters(self):
        return {'a':1,'b':1,'c':1}

    def run(self):
        self.result = 0
        for line in self.inputdata:
            self.result += int(line) * self.parameters['a'] * self.parameters['b'] - self.parameters['c']

    def score(self):
        return self.result

    @staticmethod
    def sample(inputdata,n):
        n = int(n)
        if n > len(inputdata):
            return inputdata
        else:
            return random.sample(inputdata,int(n))

class PoolExperiment(AbstractExperiment):
    def start(self):
        self.startcommand('sleep',None,None,None,str(self.parameters['duration']))
        print("STARTING: sleep " + str(self.parameters['duration']))


class WPSTest(unittest.TestCase):
    def test_wps(self):
        inputdata = [ 1,2,3,4,5,6 ]
        parameterscope = [ ('a',[2,4]), ('b',[2,5,8]),  ('c',[3,6,9]) ]
        search = WPSParamSearch(ParamExperiment, inputdata, len(inputdata), parameterscope)
        solution = search.searchbest()
        self.assertEqual(solution,  (('a', 4), ('b', 8), ('c', 3)) )



class ExperimentPoolTest(unittest.TestCase):
    def test_pool(self):
        pool = ExperimentPool(4)
        for i in range(0,15):
            pool.append( PoolExperiment(None, duration=random.randint(1,6)) )
        for experiment in pool.run():
            print("DONE: sleep " + str(experiment.parameters['duration']))
        
        self.assertTrue(True) #if we got here, no exceptions were raised and it's okay 
        
class ClassEvaluationTest2(unittest.TestCase):
    def setUp(self):
        self.goals = ['sun','sun','rain','cloudy','sun','rain']
        self.observations = ['cloudy','cloudy','cloudy','rain','sun','sun']
    
       
    def test001(self):
        e = ClassEvaluation(self.goals, self.observations)
        print()
        print(e)
        print(e.confusionmatrix())
    
    
class ClassEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.goals =        ['cat','cat','cat','cat','cat','cat','cat','cat',    'dog',  'dog','dog','dog','dog','dog'      ,'rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit']
        self.observations = ['cat','cat','cat','cat','cat','dog','dog','dog',  'cat','cat','rabbit','dog','dog','dog'   ,'rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','rabbit','dog','dog']
    
        
    def test001(self):
        """Class evaluation test -- (See also http://en.wikipedia.org/wiki/Confusion_matrix , using same data)"""
        e = ClassEvaluation(self.goals, self.observations)
        
        print
        print(e)
        print(e.confusionmatrix())
    
                
        self.assertEqual(e.tp['cat'], 5)
        self.assertEqual(e.fp['cat'], 2)
        self.assertEqual(e.tn['cat'], 17)
        self.assertEqual(e.fn['cat'], 3)
        
        self.assertEqual(e.tp['rabbit'], 11)
        self.assertEqual(e.fp['rabbit'], 1)
        self.assertEqual(e.tn['rabbit'], 13)
        self.assertEqual(e.fn['rabbit'], 2)
        
        self.assertEqual(e.tp['dog'], 3)
        self.assertEqual(e.fp['dog'], 5)
        self.assertEqual(e.tn['dog'], 16)
        self.assertEqual(e.fn['dog'], 3)
        
        self.assertEqual( round(e.precision('cat'),6), 0.714286)
        self.assertEqual( round(e.precision('rabbit'),6), 0.916667)
        self.assertEqual( round(e.precision('dog'),6), 0.375000)

        self.assertEqual( round(e.recall('cat'),6), 0.625000)
        self.assertEqual( round(e.recall('rabbit'),6), 0.846154)
        self.assertEqual( round(e.recall('dog'),6),0.500000)

        self.assertEqual( round(e.fscore('cat'),6), 0.666667)
        self.assertEqual( round(e.fscore('rabbit'),6), 0.880000)
        self.assertEqual( round(e.fscore('dog'),6),0.428571)

        self.assertEqual( round(e.accuracy(),6), 0.703704)
        
        

if __name__ == '__main__':
    unittest.main()



########NEW FILE########
__FILENAME__ = folia
#!/usr/bin/env python
#-*- coding:utf-8 -*-


#---------------------------------------------------------------
# PyNLPl - Test Units for FoLiA
#   by Maarten van Gompel, ILK, Universiteit van Tilburg
#   http://ilk.uvt.nl/~mvgompel
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from pynlpl.common import u, isstring
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout

import sys
import os
import unittest
import io
import gzip
import bz2


FOLIAPATH = '../../FoLiA/'
if sys.version < '3':
    from StringIO import StringIO
else:
    from io import StringIO, BytesIO
from datetime import datetime
import lxml.objectify
from pynlpl.formats import folia
if folia.LXE:
    from lxml import etree as ElementTree
else:
    import xml.etree.cElementTree as ElementTree


def xmlcheck(xml,expect):
    #obj1 = lxml.objectify.fromstring(expect)
    #expect = lxml.etree.tostring(obj1)
    f = open('/tmp/foliatest.fragment.expect.xml','w')
    f.write(expect)
    f.close()
    f = open('/tmp/foliatest.fragment.out.xml','w')
    f.write(xml)
    f.close()

    retcode = os.system('xmldiff /tmp/foliatest.fragment.expect.xml /tmp/foliatest.fragment.out.xml')
    passed = (retcode == 0)

    #obj2 = lxml.objectify.fromstring(xml)
    #xml = lxml.etree.tostring(obj2)
    #passed = (expect == xml)
    if not passed:
        print("XML fragments don't match:",file=stderr)
        print("--------------------------REFERENCE-------------------------------------",file=stderr)
        print(expect,file=stderr)
        print("--------------------------ACTUAL RESULT---------------------------------",file=stderr)
        print(xml,file=stderr)
        print("------------------------------------------------------------------------",file=stderr)
    return passed


class Test1Read(unittest.TestCase):

    def test1_readfromfile(self):
        """Reading from file"""
        global FOLIAEXAMPLE
        #write example to file
        f = io.open('/tmp/foliatest.xml','w',encoding='utf-8')
        f.write(FOLIAEXAMPLE)
        f.close()

        doc = folia.Document(file='/tmp/foliatest.xml')
        self.assertTrue(isinstance(doc,folia.Document))

        #sanity check: reading from file must yield the exact same data as reading from string
        doc2 = folia.Document(string=FOLIAEXAMPLE)
        self.assertEqual( doc, doc2)

    def test1a_readfromfile(self):
        """Reading from GZ file"""
        global FOLIAEXAMPLE
        #write example to file
        f = gzip.GzipFile('/tmp/foliatest.xml.gz','w')
        f.write(FOLIAEXAMPLE.encode('utf-8'))
        f.close()

        doc = folia.Document(file='/tmp/foliatest.xml.gz')
        self.assertTrue(isinstance(doc,folia.Document))

        #sanity check: reading from file must yield the exact same data as reading from string
        doc2 = folia.Document(string=FOLIAEXAMPLE)
        self.assertEqual( doc, doc2)


    def test1b_readfromfile(self):
        """Reading from BZ2 file"""
        global FOLIAEXAMPLE
        #write example to file
        f = bz2.BZ2File('/tmp/foliatest.xml.bz2','w')
        f.write(FOLIAEXAMPLE.encode('utf-8'))
        f.close()

        doc = folia.Document(file='/tmp/foliatest.xml.bz2')
        self.assertTrue(isinstance(doc,folia.Document))

        #sanity check: reading from file must yield the exact same data as reading from string
        doc2 = folia.Document(string=FOLIAEXAMPLE)
        self.assertEqual( doc, doc2)


    def test2_readfromstring(self):
        """Reading from string (unicode)"""
        global FOLIAEXAMPLE
        doc = folia.Document(string=FOLIAEXAMPLE)
        self.assertTrue(isinstance(doc,folia.Document))

    def test2_readfromstring(self):
        """Reading from string (bytes)"""
        global FOLIAEXAMPLE
        doc = folia.Document(string=FOLIAEXAMPLE.encode('utf-8'))
        self.assertTrue(isinstance(doc,folia.Document))

    def test3_readfromstring(self):
        """Reading from pre-parsed XML tree (as unicode(Py2)/str(Py3) obj)"""
        global FOLIAEXAMPLE
        if sys.version < '3':
            doc = folia.Document(tree=ElementTree.parse(StringIO(FOLIAEXAMPLE.encode('utf-8'))))
        else:
            doc = folia.Document(tree=ElementTree.parse(BytesIO(FOLIAEXAMPLE.encode('utf-8'))))
        self.assertTrue(isinstance(doc,folia.Document))


    def test4_readdcoi(self):
        """Reading D-Coi file"""
        global DCOIEXAMPLE
        doc = folia.Document(string=DCOIEXAMPLE)
        #doc = folia.Document(tree=lxml.etree.parse(StringIO(DCOIEXAMPLE.encode('iso-8859-15'))))
        self.assertTrue(isinstance(doc,folia.Document))
        self.assertEqual(len(doc.words()),1465)

class Test2Sanity(unittest.TestCase):

    def setUp(self):
        self.doc = folia.Document(string=FOLIAEXAMPLE)

    def test000_count_text(self):
        """Sanity check - One text """
        self.assertEqual( len(self.doc), 1)
        self.assertTrue( isinstance( self.doc[0], folia.Text ))

    def test001_count_paragraphs(self):
        """Sanity check - Paragraph count"""
        self.assertEqual( len(self.doc.paragraphs()) , 1)

    def test002_count_sentences(self):
        """Sanity check - Sentences count"""
        self.assertEqual( len(self.doc.sentences()) , 14)

    def test003a_count_words(self):
        """Sanity check - Word count"""
        self.assertEqual( len(self.doc.words()) , 176)

    def test003b_iter_words(self):
        """Sanity check - Words"""
        self.assertEqual( [x.id for x in self.doc.words() ], ['WR-P-E-J-0000000001.head.1.s.1.w.1', 'WR-P-E-J-0000000001.p.1.s.1.w.1', 'WR-P-E-J-0000000001.p.1.s.1.w.2', 'WR-P-E-J-0000000001.p.1.s.1.w.3', 'WR-P-E-J-0000000001.p.1.s.1.w.4', 'WR-P-E-J-0000000001.p.1.s.1.w.5', 'WR-P-E-J-0000000001.p.1.s.1.w.6', 'WR-P-E-J-0000000001.p.1.s.1.w.7', 'WR-P-E-J-0000000001.p.1.s.1.w.8', 'WR-P-E-J-0000000001.p.1.s.2.w.1', 'WR-P-E-J-0000000001.p.1.s.2.w.2', 'WR-P-E-J-0000000001.p.1.s.2.w.3', 'WR-P-E-J-0000000001.p.1.s.2.w.4', 'WR-P-E-J-0000000001.p.1.s.2.w.5', 'WR-P-E-J-0000000001.p.1.s.2.w.6', 'WR-P-E-J-0000000001.p.1.s.2.w.7', 'WR-P-E-J-0000000001.p.1.s.2.w.8', 'WR-P-E-J-0000000001.p.1.s.2.w.9', 'WR-P-E-J-0000000001.p.1.s.2.w.10', 'WR-P-E-J-0000000001.p.1.s.2.w.11', 'WR-P-E-J-0000000001.p.1.s.2.w.12', 'WR-P-E-J-0000000001.p.1.s.2.w.13', 'WR-P-E-J-0000000001.p.1.s.2.w.14', 'WR-P-E-J-0000000001.p.1.s.2.w.15', 'WR-P-E-J-0000000001.p.1.s.2.w.16', 'WR-P-E-J-0000000001.p.1.s.2.w.17', 'WR-P-E-J-0000000001.p.1.s.2.w.18', 'WR-P-E-J-0000000001.p.1.s.2.w.19', 'WR-P-E-J-0000000001.p.1.s.2.w.20', 'WR-P-E-J-0000000001.p.1.s.2.w.21', 'WR-P-E-J-0000000001.p.1.s.2.w.22', 'WR-P-E-J-0000000001.p.1.s.2.w.23', 'WR-P-E-J-0000000001.p.1.s.2.w.24-25', 'WR-P-E-J-0000000001.p.1.s.2.w.26', 'WR-P-E-J-0000000001.p.1.s.2.w.27', 'WR-P-E-J-0000000001.p.1.s.2.w.28', 'WR-P-E-J-0000000001.p.1.s.2.w.29', 'WR-P-E-J-0000000001.p.1.s.3.w.1', 'WR-P-E-J-0000000001.p.1.s.3.w.2', 'WR-P-E-J-0000000001.p.1.s.3.w.3', 'WR-P-E-J-0000000001.p.1.s.3.w.4', 'WR-P-E-J-0000000001.p.1.s.3.w.5', 'WR-P-E-J-0000000001.p.1.s.3.w.6', 'WR-P-E-J-0000000001.p.1.s.3.w.7', 'WR-P-E-J-0000000001.p.1.s.3.w.8', 'WR-P-E-J-0000000001.p.1.s.3.w.9', 'WR-P-E-J-0000000001.p.1.s.3.w.10', 'WR-P-E-J-0000000001.p.1.s.3.w.11', 'WR-P-E-J-0000000001.p.1.s.3.w.12', 'WR-P-E-J-0000000001.p.1.s.3.w.13', 'WR-P-E-J-0000000001.p.1.s.3.w.14', 'WR-P-E-J-0000000001.p.1.s.3.w.15', 'WR-P-E-J-0000000001.p.1.s.3.w.16', 'WR-P-E-J-0000000001.p.1.s.3.w.17', 'WR-P-E-J-0000000001.p.1.s.3.w.18', 'WR-P-E-J-0000000001.p.1.s.3.w.19', 'WR-P-E-J-0000000001.p.1.s.3.w.20', 'WR-P-E-J-0000000001.p.1.s.3.w.21', 'WR-P-E-J-0000000001.p.1.s.4.w.1', 'WR-P-E-J-0000000001.p.1.s.4.w.2', 'WR-P-E-J-0000000001.p.1.s.4.w.3', 'WR-P-E-J-0000000001.p.1.s.4.w.4', 'WR-P-E-J-0000000001.p.1.s.4.w.5', 'WR-P-E-J-0000000001.p.1.s.4.w.6', 'WR-P-E-J-0000000001.p.1.s.4.w.7', 'WR-P-E-J-0000000001.p.1.s.4.w.8', 'WR-P-E-J-0000000001.p.1.s.4.w.9', 'WR-P-E-J-0000000001.p.1.s.4.w.10', 'WR-P-E-J-0000000001.p.1.s.5.w.1', 'WR-P-E-J-0000000001.p.1.s.5.w.2', 'WR-P-E-J-0000000001.p.1.s.5.w.3', 'WR-P-E-J-0000000001.p.1.s.5.w.4', 'WR-P-E-J-0000000001.p.1.s.5.w.5', 'WR-P-E-J-0000000001.p.1.s.5.w.6', 'WR-P-E-J-0000000001.p.1.s.5.w.7', 'WR-P-E-J-0000000001.p.1.s.5.w.8', 'WR-P-E-J-0000000001.p.1.s.5.w.9', 'WR-P-E-J-0000000001.p.1.s.5.w.10', 'WR-P-E-J-0000000001.p.1.s.5.w.11', 'WR-P-E-J-0000000001.p.1.s.5.w.12', 'WR-P-E-J-0000000001.p.1.s.5.w.13', 'WR-P-E-J-0000000001.p.1.s.5.w.14', 'WR-P-E-J-0000000001.p.1.s.5.w.15', 'WR-P-E-J-0000000001.p.1.s.5.w.16', 'WR-P-E-J-0000000001.p.1.s.5.w.17', 'WR-P-E-J-0000000001.p.1.s.5.w.18', 'WR-P-E-J-0000000001.p.1.s.5.w.19', 'WR-P-E-J-0000000001.p.1.s.5.w.20', 'WR-P-E-J-0000000001.p.1.s.5.w.21', 'WR-P-E-J-0000000001.p.1.s.6.w.1', 'WR-P-E-J-0000000001.p.1.s.6.w.2', 'WR-P-E-J-0000000001.p.1.s.6.w.3', 'WR-P-E-J-0000000001.p.1.s.6.w.4', 'WR-P-E-J-0000000001.p.1.s.6.w.5', 'WR-P-E-J-0000000001.p.1.s.6.w.6', 'WR-P-E-J-0000000001.p.1.s.6.w.7', 'WR-P-E-J-0000000001.p.1.s.6.w.8', 'WR-P-E-J-0000000001.p.1.s.6.w.9', 'WR-P-E-J-0000000001.p.1.s.6.w.10', 'WR-P-E-J-0000000001.p.1.s.6.w.11', 'WR-P-E-J-0000000001.p.1.s.6.w.12', 'WR-P-E-J-0000000001.p.1.s.6.w.13', 'WR-P-E-J-0000000001.p.1.s.6.w.14', 'WR-P-E-J-0000000001.p.1.s.6.w.15', 'WR-P-E-J-0000000001.p.1.s.6.w.16', 'WR-P-E-J-0000000001.p.1.s.6.w.17', 'WR-P-E-J-0000000001.p.1.s.6.w.18', 'WR-P-E-J-0000000001.p.1.s.6.w.19', 'WR-P-E-J-0000000001.p.1.s.6.w.20', 'WR-P-E-J-0000000001.p.1.s.6.w.21', 'WR-P-E-J-0000000001.p.1.s.6.w.22', 'WR-P-E-J-0000000001.p.1.s.6.w.23', 'WR-P-E-J-0000000001.p.1.s.6.w.24', 'WR-P-E-J-0000000001.p.1.s.6.w.25', 'WR-P-E-J-0000000001.p.1.s.6.w.26', 'WR-P-E-J-0000000001.p.1.s.6.w.27', 'WR-P-E-J-0000000001.p.1.s.6.w.28', 'WR-P-E-J-0000000001.p.1.s.6.w.29', 'WR-P-E-J-0000000001.p.1.s.6.w.30', 'WR-P-E-J-0000000001.p.1.s.6.w.31', 'WR-P-E-J-0000000001.p.1.s.6.w.32', 'WR-P-E-J-0000000001.p.1.s.6.w.33', 'WR-P-E-J-0000000001.p.1.s.6.w.34', 'WR-P-E-J-0000000001.p.1.s.7.w.1', 'WR-P-E-J-0000000001.p.1.s.7.w.2', 'WR-P-E-J-0000000001.p.1.s.7.w.3', 'WR-P-E-J-0000000001.p.1.s.7.w.4', 'WR-P-E-J-0000000001.p.1.s.7.w.5', 'WR-P-E-J-0000000001.p.1.s.7.w.6', 'WR-P-E-J-0000000001.p.1.s.7.w.7', 'WR-P-E-J-0000000001.p.1.s.7.w.8', 'WR-P-E-J-0000000001.p.1.s.7.w.9', 'WR-P-E-J-0000000001.p.1.s.7.w.10', 'WR-P-E-J-0000000001.p.1.s.8.w.1', 'WR-P-E-J-0000000001.p.1.s.8.w.2', 'WR-P-E-J-0000000001.p.1.s.8.w.3', 'WR-P-E-J-0000000001.p.1.s.8.w.4', 'WR-P-E-J-0000000001.p.1.s.8.w.5', 'WR-P-E-J-0000000001.p.1.s.8.w.6', 'WR-P-E-J-0000000001.p.1.s.8.w.7', 'WR-P-E-J-0000000001.p.1.s.8.w.8', 'WR-P-E-J-0000000001.p.1.s.8.w.9', 'WR-P-E-J-0000000001.p.1.s.8.w.10', 'WR-P-E-J-0000000001.p.1.s.8.w.11', 'WR-P-E-J-0000000001.p.1.s.8.w.12', 'WR-P-E-J-0000000001.p.1.s.8.w.13', 'WR-P-E-J-0000000001.p.1.s.8.w.14', 'WR-P-E-J-0000000001.p.1.s.8.w.15', 'WR-P-E-J-0000000001.p.1.s.8.w.16', 'WR-P-E-J-0000000001.p.1.s.8.w.17', 'sandbox.list.1.listitem.1.s.1.w.1', 'sandbox.list.1.listitem.1.s.1.w.2', 'sandbox.list.1.listitem.2.s.1.w.1', 'sandbox.list.1.listitem.2.s.1.w.2', 'sandbox.figure.1.caption.s.1.w.1', 'sandbox.figure.1.caption.s.1.w.2', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.1', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.2', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.3', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.4', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.5', 'WR-P-E-J-0000000001.sandbox.2.s.1.w.6', 'example.table.1.w.1', 'example.table.1.w.2', 'example.table.1.w.3', 'example.table.1.w.4', 'example.table.1.w.5', 'example.table.1.w.6', 'example.table.1.w.7', 'example.table.1.w.8', 'example.table.1.w.9', 'example.table.1.w.10', 'example.table.1.w.11', 'example.table.1.w.12', 'example.table.1.w.13', 'example.table.1.w.14'] )

    def test004_first_word(self):
        """Sanity check - First word"""
        #grab first word
        w = self.doc.words(0) # shortcut for doc.words()[0]
        self.assertTrue( isinstance(w, folia.Word) )
        self.assertEqual( w.id , 'WR-P-E-J-0000000001.head.1.s.1.w.1' )
        self.assertEqual( w.text() , "Stemma" )
        self.assertEqual( str(w) , "Stemma" ) #should be unicode object also in Py2!
        if sys.version < '3':
            self.assertEqual( unicode(w) , "Stemma" )


    def test005_last_word(self):
        """Sanity check - Last word"""
        #grab last word
        w = self.doc.words(-1) # shortcut for doc.words()[0]
        self.assertTrue( isinstance(w, folia.Word) )
        self.assertEqual( w.id , "example.table.1.w.14" )
        self.assertEqual( w.text() , "University" )
        self.assertEqual( str(w) , "University" )

    def test006_second_sentence(self):
        """Sanity check - Sentence"""
        #grab second sentence
        s = self.doc.sentences(1)
        self.assertTrue( isinstance(s, folia.Sentence) )
        self.assertEqual( s.id, 'WR-P-E-J-0000000001.p.1.s.1' )
        self.assertFalse( s.hastext() )
        self.assertEqual( str(s), "Stemma is een ander woord voor stamboom ." )

    def test006b_sentencetest(self):
        """Sanity check - Sentence text (including retaining tokenisation)"""
        #grab second sentence
        s = self.doc['WR-P-E-J-0000000001.p.1.s.5']
        self.assertTrue( isinstance(s, folia.Sentence) )
        self.assertFalse( s.hastext() )
        self.assertEqual( s.text(), "De andere handschriften krijgen ook een letter die verband kan houden met hun plaats van oorsprong óf plaats van bewaring.")
        self.assertEqual( s.text('current',True), "De andere handschriften krijgen ook een letter die verband kan houden met hun plaats van oorsprong óf plaats van bewaring .") #not detokenised
        self.assertEqual( s.toktext(), "De andere handschriften krijgen ook een letter die verband kan houden met hun plaats van oorsprong óf plaats van bewaring .") #just an alias for the above

    def test007_index(self):
        """Sanity check - Index"""
        #grab something using the index
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        self.assertTrue( isinstance(w, folia.Word) )
        self.assertEqual( self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7'] , self.doc.index['WR-P-E-J-0000000001.p.1.s.2.w.7'] )
        self.assertEqual( w.id , 'WR-P-E-J-0000000001.p.1.s.2.w.7' )
        self.assertEqual( w.text() , "stamboom" )

    def test008_division(self):
        """Sanity check - Division + head"""

        #grab something using the index
        div = self.doc['WR-P-E-J-0000000001.div0.1']
        self.assertTrue( isinstance(div, folia.Division) )
        self.assertEqual( div.head() , self.doc['WR-P-E-J-0000000001.head.1'] )
        self.assertEqual( len(div.head()) ,1 ) #Head contains one element (one sentence)

    def test009_pos(self):
        """Sanity check - Token Annotation - Pos"""
        #grab first word
        w = self.doc.words(0)


        self.assertEqual( w.annotation(folia.PosAnnotation), w.select(folia.PosAnnotation)[0] ) #w.annotation() selects the single first annotation of that type, select is the generic method to retrieve pretty much everything
        self.assertTrue( isinstance(w.annotation(folia.PosAnnotation), folia.PosAnnotation) )
        self.assertTrue( issubclass(folia.PosAnnotation, folia.AbstractTokenAnnotation) )

        self.assertEqual( w.annotation(folia.PosAnnotation).cls, 'N(soort,ev,basis,onz,stan)' ) #cls is used everywhere instead of class, since class is a reserved keyword in python
        self.assertEqual( w.pos(),'N(soort,ev,basis,onz,stan)' ) #w.pos() is just a direct shortcut for getting the class
        self.assertEqual( w.annotation(folia.PosAnnotation).set, 'cgn-combinedtags' )
        self.assertEqual( w.annotation(folia.PosAnnotation).annotator, 'tadpole' )
        self.assertEqual( w.annotation(folia.PosAnnotation).annotatortype, folia.AnnotatorType.AUTO )


    def test010_lemma(self):
        """Sanity check - Token Annotation - Lemma"""
        #grab first word
        w = self.doc.words(0)

        self.assertEqual( w.annotation(folia.LemmaAnnotation), w.annotation(folia.LemmaAnnotation) ) #w.lemma() is just a shortcut
        self.assertEqual( w.annotation(folia.LemmaAnnotation), w.select(folia.LemmaAnnotation)[0] ) #w.annotation() selects the single first annotation of that type, select is the generic method to retrieve pretty much everything
        self.assertTrue( isinstance(w.annotation(folia.LemmaAnnotation), folia.LemmaAnnotation))

        self.assertEqual( w.annotation(folia.LemmaAnnotation).cls, 'stemma' )
        self.assertEqual( w.lemma(),'stemma' ) #w.lemma() is just a direct shortcut for getting the class
        self.assertEqual( w.annotation(folia.LemmaAnnotation).set, 'lemmas-nl' )
        self.assertEqual( w.annotation(folia.LemmaAnnotation).annotator, 'tadpole' )
        self.assertEqual( w.annotation(folia.LemmaAnnotation).annotatortype, folia.AnnotatorType.AUTO )

    def test011_tokenannot_notexist(self):
        """Sanity check - Token Annotation - Non-existing element"""
        #grab first word
        w = self.doc.words(0)

        self.assertEqual( len(w.select(folia.SenseAnnotation)), 0)  #list
        self.assertRaises( folia.NoSuchAnnotation, w.annotation, folia.SenseAnnotation) #exception



    def test012_correction(self):
        """Sanity check - Correction - Text"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.6.w.31']
        c = w.annotation(folia.Correction)

        self.assertEqual( len(c.new()), 1)
        self.assertEqual( len(c.original()), 1)

        self.assertEqual( w.text(), 'vierkante')
        self.assertEqual( c.new(0), 'vierkante')
        self.assertEqual( c.original(0) , 'vierkant')

    def test013_correction(self):
        """Sanity check - Correction - Token Annotation"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.6.w.32']
        c = w.annotation(folia.Correction)

        self.assertEqual( len(c.new()), 1)
        self.assertEqual( len(c.original()), 1)

        self.assertEqual( w.annotation(folia.LemmaAnnotation).cls , 'haak')
        self.assertEqual( c.new(0).cls, 'haak')
        self.assertEqual( c.original(0).cls, 'haaak')


    def test014_correction(self):
        """Sanity check - Correction - Suggestions (text)"""
        #grab first word
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.14']
        c = w.annotation(folia.Correction)
        self.assertTrue( isinstance(c, folia.Correction) )
        self.assertEqual( len(c.suggestions()), 2 )
        self.assertEqual( str(c.suggestions(0).text()), 'twijfelachtige' )
        self.assertEqual( str(c.suggestions(1).text()), 'ongewisse' )

    def test015_parenttest(self):
        """Sanity check - Checking if all elements know who's their daddy"""

        def check(parent, indent = ''):

            for child in parent:
                if isinstance(child, folia.AbstractElement) and not (isinstance(parent, folia.AbstractSpanAnnotation) and (isinstance(child, folia.Word) or isinstance(child, folia.Morpheme))): #words and morphemes are exempted in abstractspanannotation
                    #print indent + repr(child), child.id, child.cls
                    self.assertTrue( child.parent is parent)
                    check(child, indent + '  ')
            return True

        self.assertTrue( check(self.doc.data[0],'  ') )

    def test016a_description(self):
        """Sanity Check - Description"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.1.w.6']
        self.assertEqual( w.description(), 'Dit woordje is een voorzetsel, het is maar dat je het weet...')

    def test016b_description(self):
        """Sanity Check - Error on non-existing description"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.1.w.7']
        self.assertRaises( folia.NoDescription,  w.description)

    def test017_gap(self):
        """Sanity Check - Gap"""
        gap = self.doc["WR-P-E-J-0000000001.gap.1"]
        self.assertEqual( gap.content().strip()[:11], 'De tekst is')
        self.assertEqual( gap.cls, 'backmatter')
        self.assertEqual( gap.description(), 'Backmatter')

    def test018_subtokenannot(self):
        """Sanity Check - Subtoken annotation (part of speech)"""
        w= self.doc['WR-P-E-J-0000000001.p.1.s.2.w.5']
        p = w.annotation(folia.PosAnnotation)
        self.assertEqual( p.feat('role'), 'pv' )
        self.assertEqual( p.feat('tense'), 'tgw' )
        self.assertEqual( p.feat('form'), 'met-t' )

    def test019_alignment(self):
        """Sanity Check - Alignment in same document"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.3.w.10']
        a = w.annotation(folia.Alignment)
        target = a.resolve()[0]
        self.assertEqual( target, self.doc['WR-P-E-J-0000000001.p.1.s.3.w.5'] )


    def test020a_spanannotation(self):
        """Sanity Check - Span Annotation (Syntax)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']
        l = s.annotation(folia.SyntaxLayer)

        self.assertTrue( isinstance(l[0], folia.SyntacticUnit ) )
        self.assertEqual( l[0].cls,  'sentence' )
        self.assertEqual( l[0][0].cls,  'subject' )
        self.assertEqual( l[0][0].text(),  'Stemma' )
        self.assertEqual( l[0][1].cls,  'verb' )
        self.assertEqual( l[0][2].cls,  'predicate' )
        self.assertEqual( l[0][2][0].cls,  'np' )
        self.assertEqual( l[0][2][1].cls,  'pp' )
        self.assertEqual( l[0][2][1].text(),  'voor stamboom' )
        self.assertEqual( l[0][2].text(),  'een ander woord voor stamboom' )

    def test020b_spanannotation(self):
        """Sanity Check - Span Annotation (Chunking)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']
        l = s.annotation(folia.ChunkingLayer)

        self.assertTrue( isinstance(l[0], folia.Chunk ) )
        self.assertEqual( l[0].text(),  'een ander woord' )
        self.assertEqual( l[1].text(),  'voor stamboom' )

    def test020c_spanannotation(self):
        """Sanity Check - Span Annotation (Entities)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']
        l = s.annotation(folia.EntitiesLayer)

        self.assertTrue( isinstance(l[0], folia.Entity) )
        self.assertEqual( l[0].text(),  'ander woord' )


    def test020d_spanannotation(self):
        """Sanity Check - Span Annotation (Dependencies)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']
        l = s.annotation(folia.DependenciesLayer)

        self.assertTrue( isinstance(l[0], folia.Dependency) )
        self.assertEqual( l[0].head().text(),  'is' )
        self.assertEqual( l[0].dependent().text(),  'Stemma' )
        self.assertEqual( l[0].cls,  'su' )

        self.assertTrue( isinstance(l[1], folia.Dependency) )
        self.assertEqual( l[1].head().text(),  'is' )
        self.assertEqual( l[1].dependent().text(),  'woord' )
        self.assertEqual( l[1].cls,'predc' )

        self.assertTrue( isinstance(l[2], folia.Dependency) )
        self.assertEqual( l[2].head().text(),  'woord' )
        self.assertEqual( l[2].dependent().text(),  'een' )
        self.assertEqual( l[2].cls,'det' )

        self.assertTrue( isinstance(l[3], folia.Dependency) )
        self.assertEqual( l[3].head().text(),  'woord' )
        self.assertEqual( l[3].dependent().text(),  'ander' )
        self.assertEqual( l[3].cls,'mod' )

        self.assertTrue( isinstance(l[4], folia.Dependency) )
        self.assertEqual( l[4].head().text(),  'woord' )
        self.assertEqual( l[4].dependent().text(),  'voor' )
        self.assertEqual( l[4].cls,'mod' )

        self.assertTrue( isinstance(l[5], folia.Dependency) )
        self.assertEqual( l[5].head().text(),  'voor' )
        self.assertEqual( l[5].dependent().text(),  'stamboom' )
        self.assertEqual( l[5].cls,'obj1' )

    def test020e_spanannotation(self):
        """Sanity Check - Span Annotation (Timedevent)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']
        l = s.annotation(folia.TimingLayer)

        self.assertTrue( isinstance(l[0], folia.TimeSegment ) )
        self.assertEqual( l[0].text(),  'een ander woord' )
        self.assertEqual( l[1].cls, 'cough' )
        self.assertEqual( l[2].text(),  'voor stamboom' )

    def test020f_spanannotation(self):
        """Sanity Check - Co-Reference"""
        div = self.doc["WR-P-E-J-0000000001.div0.1"]
        deplayer = div.annotation(folia.DependenciesLayer)
        deps = list(deplayer.annotations(folia.Dependency))

        self.assertEqual( deps[0].cls,  'su' )
        self.assertEqual( deps[1].cls,  'predc' )
        self.assertEqual( deps[2].cls,  'det' )
        self.assertEqual( deps[3].cls,  'mod' )
        self.assertEqual( deps[4].cls,  'mod' )
        self.assertEqual( deps[5].cls,  'obj1' )

        self.assertEqual( deps[2].head().wrefs(0), self.doc['WR-P-E-J-0000000001.p.1.s.1.w.5'] )
        self.assertEqual( deps[2].dependent().wrefs(0), self.doc['WR-P-E-J-0000000001.p.1.s.1.w.3'] )


    def test020g_spanannotation(self):
        """Sanity Check - Semantic Role Labelling"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.7']
        semrolelayer = s.annotation(folia.SemanticRolesLayer)
        roles = list(semrolelayer.annotations(folia.SemanticRole))

        self.assertEqual( roles[0].cls,  'actor' )
        self.assertEqual( roles[1].cls,  'patient' )

        self.assertEqual( roles[0].wrefs(0), self.doc['WR-P-E-J-0000000001.p.1.s.7.w.3'] )
        self.assertEqual( roles[1].wrefs(0), self.doc['WR-P-E-J-0000000001.p.1.s.7.w.4'] )
        self.assertEqual( roles[1].wrefs(1), self.doc['WR-P-E-J-0000000001.p.1.s.7.w.5'] )


    def test021_previousword(self):
        """Sanity Check - Obtaining previous word"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        prevw = w.previous()
        self.assertTrue( isinstance(prevw, folia.Word) )
        self.assertEqual( prevw.text(),  "zo'n" )

    def test022_nextword(self):
        """Sanity Check - Obtaining next word"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        nextw = w.next()
        self.assertTrue( isinstance(nextw, folia.Word) )
        self.assertEqual( nextw.text(),  "," )

    def test023_leftcontext(self):
        """Sanity Check - Obtaining left context"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        context = w.leftcontext(3)
        self.assertEqual( [ x.text() for x in context ], ['wetenschap','wordt',"zo'n"] )

    def test024_rightcontext(self):
        """Sanity Check - Obtaining right context"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        context = w.rightcontext(3)
        self.assertEqual( [ x.text() for x in context ], [',','onder','de'] )

    def test025_fullcontext(self):
        """Sanity Check - Obtaining full context"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.7']
        context = w.context(3)
        self.assertEqual( [ x.text() for x in context ], ['wetenschap','wordt',"zo'n",'stamboom',',','onder','de'] )

    def test026_feature(self):
        """Sanity Check - Features"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.6.w.1']
        pos = w.annotation(folia.PosAnnotation)
        self.assertTrue( isinstance(pos, folia.PosAnnotation) )
        self.assertEqual(pos.cls,'WW(vd,prenom,zonder)')
        self.assertEqual( len(pos),  1)
        features = pos.select(folia.Feature)
        self.assertEqual( len(features),  1)
        self.assertTrue( isinstance(features[0], folia.Feature))
        self.assertEqual( features[0].subset, 'head')
        self.assertEqual( features[0].cls, 'WW')

    def test027_datetime(self):
        """Sanity Check - Time stamp"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.15']

        pos = w.annotation(folia.PosAnnotation)
        self.assertEqual( pos.datetime, datetime(2011, 7, 20, 19, 0, 1) )

        self.assertTrue( xmlcheck(pos.xmlstring(), '<pos xmlns="http://ilk.uvt.nl/folia" class="N(soort,ev,basis,zijd,stan)" datetime="2011-07-20T19:00:01"/>') )

    def test028_wordparents(self):
        """Sanity Check - Finding parents of word"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.15']

        s = w.sentence()
        self.assertTrue( isinstance(s, folia.Sentence) )
        self.assertEqual( s.id, 'WR-P-E-J-0000000001.p.1.s.8')

        p = w.paragraph()
        self.assertTrue( isinstance(p, folia.Paragraph) )
        self.assertEqual( p.id, 'WR-P-E-J-0000000001.p.1')

        div = w.division()
        self.assertTrue( isinstance(div, folia.Division) )
        self.assertEqual( div.id, 'WR-P-E-J-0000000001.div0.1')

        self.assertEqual( w.incorrection(), None)

    def test0029_quote(self):
        """Sanity Check - Quote"""
        q = self.doc['WR-P-E-J-0000000001.p.1.s.8.q.1']
        self.assertTrue( isinstance(q, folia.Quote) )
        self.assertEqual(q.text(), 'volle lijn')

        s = self.doc['WR-P-E-J-0000000001.p.1.s.8']
        self.assertEqual(s.text(), 'Een volle lijn duidt op een verwantschap , terweil een stippelijn op een onzekere verwantschap duidt .') #(spelling errors are present in sentence)

        #a word from the quote
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.2']
        #check if sentence matches
        self.assertTrue( (w.sentence() is s) )

    def test030_textcontent(self):
        """Sanity check - Text Content"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.4']

        self.assertEqual( s.text(), 'De hoofdletter A wordt gebruikt voor het originele handschrift.')
        self.assertEqual( s.stricttext(), 'De hoofdletter A wordt gebruikt voor het originele handschrift.')
        self.assertEqual( s.textcontent().value, 'De hoofdletter A wordt gebruikt voor het originele handschrift.')
        self.assertEqual( s.text('original'), 'De hoofdletter A wordt gebruikt voor het originele handschrift.')
        self.assertRaises( folia.NoSuchText, s.text, 'BLAH' )


        w = self.doc['WR-P-E-J-0000000001.p.1.s.4.w.2']
        self.assertEqual( w.text(), 'hoofdletter')

        self.assertEqual( w.textcontent().value, 'hoofdletter')
        self.assertEqual( w.textcontent().offset, 3)

        w2 = self.doc['WR-P-E-J-0000000001.p.1.s.6.w.31']
        self.assertEqual( w2.text(), 'vierkante')
        self.assertEqual( w2.stricttext(), 'vierkante')


    def test030b_textcontent(self):
        """Sanity check - Text Content (2)"""
        s = self.doc['sandbox.3.head']
        t = s.textcontent()
        self.assertEqual( len(t), 3)
        self.assertEqual( t.value, "De FoLiA developers zijn:")
        self.assertEqual( t.text(), "De FoLiA developers zijn:")
        self.assertEqual( t[0], "De ")
        self.assertTrue( isinstance(t[1], folia.TextMarkupString) )
        self.assertEqual( t[1].value, "FoLiA developers")
        self.assertEqual( t[2], " zijn:")


    def test031_sense(self):
        """Sanity Check - Lexical Semantic Sense Annotation"""
        w = self.doc['sandbox.list.1.listitem.1.s.1.w.1']
        sense = w.annotation(folia.SenseAnnotation)

        self.assertEqual( sense.cls , 'some.sense.id')
        self.assertEqual( sense.feat('synset') , 'some.synset.id')

    def test032_event(self):
        """Sanity Check - Events"""
        l= self.doc['sandbox.list.1']
        event = l.annotation(folia.Event)

        self.assertEqual( event.cls , 'applause')
        self.assertEqual( event.feat('actor') , 'audience')

    def test033_list(self):
        """Sanity Check - List"""
        l = self.doc['sandbox.list.1']
        self.assertTrue( isinstance( l[0], folia.ListItem) )
        self.assertEqual( l[0].n, '1' ) #testing common n attribute
        self.assertEqual( l[0].text(), 'Eerste testitem')
        self.assertTrue( isinstance( l[-1], folia.ListItem) )
        self.assertEqual( l[-1].text(), 'Tweede testitem')
        self.assertEqual( l[-1].n, '2' )

    def test034_figure(self):
        """Sanity Check - Figure"""
        fig = self.doc['sandbox.figure.1']
        self.assertEqual( fig.src, "http://upload.wikimedia.org/wikipedia/commons/8/8e/Family_tree.svg")
        self.assertEqual( fig.caption(), 'Een stamboom')

    def test035_event(self):
        """Sanity Check - Event"""
        e = self.doc['sandbox.event.1']
        self.assertEqual( e.feat('actor'), 'proycon')
        self.assertEqual( e.feat('begindatetime'), '2011-12-15T19:01')
        self.assertEqual( e.feat('enddatetime'), '2011-12-15T19:05')

    def test036_parsen(self):
        """Sanity Check - Paragraph and Sentence annotation"""
        p = self.doc['WR-P-E-J-0000000001.p.1']
        self.assertEqual( p.cls, 'firstparagraph' )
        s = self.doc['WR-P-E-J-0000000001.p.1.s.6']
        self.assertEqual( s.cls, 'sentence' )


    def test037a_feat(self):
        """Sanity Check - Feature test (including shortcut)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="0.8" generator="libfolia-v0.4">
<metadata src="test.cmdi.xml" type="cmdi">
<annotations>
    <pos-annotation set="test"/>
</annotations>
</metadata>
<text xml:id="test.text">
    <div xml:id="div">
    <head xml:id="head">
        <s xml:id="head.1.s.1">
            <w xml:id="head.1.s.1.w.1">
                <t>blah</t>
                <pos class="NN(blah)" head="NN" />
            </w>
        </s>
    </head>
    <p xml:id="p.1">
        <s xml:id="p.1.s.1">
            <w xml:id="p.1.s.1.w.1">
                <t>blah</t>
                <pos class="NN(blah)">
                    <feat subset="head" class="NN" />
                </pos>
            </w>
        </s>
    </p>
    </div>
</text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertEqual( doc['head.1.s.1.w.1'].pos() , 'NN(blah)')
        self.assertEqual( doc['head.1.s.1.w.1'].annotation(folia.PosAnnotation).feat('head') , 'NN')
        self.assertEqual( doc['p.1.s.1.w.1'].pos() , 'NN(blah)')
        self.assertEqual( doc['p.1.s.1.w.1'].annotation(folia.PosAnnotation).feat('head') , 'NN')

    def test037b_multiclassfeat(self):
        """Sanity Check - Multiclass feature"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="0.8" generator="libfolia-v0.4">
<metadata src="test.cmdi.xml" type="cmdi">
<annotations>
    <pos-annotation set="test"/>
</annotations>
</metadata>
<text xml:id="test.text">
    <div xml:id="div">
    <p xml:id="p.1">
        <s xml:id="p.1.s.1">
            <w xml:id="p.1.s.1.w.1">
                <t>blah</t>
                <pos class="NN(a,b,c)">
                    <feat subset="x" class="a" />
                    <feat subset="x" class="b" />
                    <feat subset="x" class="c" />
                </pos>
            </w>
        </s>
    </p>
    </div>
</text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertEqual( doc['p.1.s.1.w.1'].pos() , 'NN(a,b,c)')
        self.assertEqual( doc['p.1.s.1.w.1'].annotation(folia.PosAnnotation).feat('x') , ['a','b','c'] )

    def test038a_morphemeboundary(self):
        """Sanity check - Obtaining annotation should not descend into morphology layer"""
        self.assertRaises( folia.NoSuchAnnotation,  self.doc['WR-P-E-J-0000000001.sandbox.2.s.1.w.2'].annotation , folia.PosAnnotation)

    def test038b_morphemeboundary(self):
        """Sanity check - Obtaining morphemes and token annotation under morphemes"""

        w = self.doc['WR-P-E-J-0000000001.sandbox.2.s.1.w.2']
        l = list(w.morphemes()) #get all morphemes
        self.assertEqual(len(l), 2)
        m = w.morpheme(1) #get second morpheme
        self.assertEqual(m.annotation(folia.PosAnnotation).cls, 'n')

    def test039_findspan(self):
        """Sanity Check - Find span on layer"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.7']
        semrolelayer = s.annotation(folia.SemanticRolesLayer)
        roles = list(semrolelayer.annotations(folia.SemanticRole))
        self.assertEqual(semrolelayer.findspan( self.doc['WR-P-E-J-0000000001.p.1.s.7.w.4'], self.doc['WR-P-E-J-0000000001.p.1.s.7.w.5']), roles[1] )

    def test040_spaniter(self):
        """Sanity Check - Iteration over spans"""
        t = []
        sentence = self.doc["WR-P-E-J-0000000001.p.1.s.1"]
        for layer in sentence.select(folia.EntitiesLayer):
            for entity in layer.select(folia.Entity):
                for word in entity.wrefs():
                    t.append(word.text())
        self.assertEqual(t, ['ander','woord'])

    def test041_findspans(self):
        """Sanity check - Find spans given words"""
        t = []
        word = self.doc["WR-P-E-J-0000000001.p.1.s.1.w.4"]
        for entity in word.findspans(folia.EntitiesLayer):
            for word in entity.wrefs():
                t.append(word.text())
        self.assertEqual(t, ['ander','woord'])

    def test042_table(self):
        """Sanity check - Table"""
        table = self.doc["example.table.1"]
        self.assertTrue( isinstance(table, folia.Table))
        self.assertTrue( isinstance(table[0], folia.TableHead))
        self.assertTrue( isinstance(table[0][0], folia.Row))
        self.assertEqual( len(table[0][0]), 2) #two cells
        self.assertTrue( isinstance(table[0][0][0], folia.Cell))
        self.assertEqual( table[0][0][0].text(), "Naam" )
        self.assertEqual( table[0][0].text(), "Naam | Universiteit" ) #text of whole row


    def test043_string(self):
        """Sanity check - String"""
        s = self.doc["sandbox.3.head"]
        self.assertTrue( s.hasannotation(folia.String) )
        st = s.select(folia.String)[0]
        self.assertEqual( st.text(), "FoLiA developers")
        self.assertEqual( st.annotation(folia.LangAnnotation).cls, "eng")

    def test044_textmarkup(self):
        """Sanity check - Text Markup"""
        s = self.doc["sandbox.3.head"]
        t = s.textcontent()
        self.assertEqual( len(s.select(folia.TextMarkupString)), 1)
        self.assertEqual( len(t.select(folia.TextMarkupString)), 1)

        st = t.select(folia.TextMarkupString)[0]
        self.assertEqual( st.value, "FoLiA developers" ) #testing value (full text value)

        self.assertEqual( st.resolve(), self.doc['sandbox.3.str']) #testing resolving references


        self.assertTrue( isinstance( self.doc['WR-P-E-J-0000000001.p.1.s.6'].textcontent()[-1], folia.Linebreak) )  #did we get the linebreak properly?

        #testing nesting
        self.assertEqual( len(st), 2)
        self.assertEqual( st[0], self.doc['sandbox.3.str.bold'])

        #testing TextMarkup.text()
        self.assertEqual( st[0].text(), 'FoLiA' )

        #resolving returns self if it's not a reference
        self.assertEqual( self.doc['sandbox.3.str.bold'].resolve(), self.doc['sandbox.3.str.bold'])


    def test099_write(self):
        """Sanity Check - Writing to file"""
        self.doc.save('/tmp/foliasavetest.xml')

    def test099b_write(self):
        """Sanity Check - Writing to GZ file"""
        self.doc.save('/tmp/foliasavetest.xml.gz')

    def test099c_write(self):
        """Sanity Check - Writing to BZ2 file"""
        self.doc.save('/tmp/foliasavetest.xml.bz2')

    def test100a_sanity(self):
        """Sanity Check - A - Checking output file against input (should be equal)"""
        global FOLIAEXAMPLE
        f = io.open('/tmp/foliatest.xml','w',encoding='utf-8')
        f.write(FOLIAEXAMPLE)
        f.close()
        self.doc.save('/tmp/foliatest100.xml')
        self.assertEqual(  folia.Document(file='/tmp/foliatest100.xml',debug=False), self.doc )

    def test100b_sanity_xmldiff(self):
        """Sanity Check - B - Checking output file against input using xmldiff (should be equal)"""
        global FOLIAEXAMPLE
        f = io.open('/tmp/foliatest.xml','w',encoding='utf-8')
        f.write(FOLIAEXAMPLE)
        f.close()
        #use xmldiff to compare the two:
        self.doc.save('/tmp/foliatest100.xml')
        retcode = os.system('xmldiff /tmp/foliatest.xml /tmp/foliatest100.xml')
        #retcode = 1 #disabled (memory hog)
        self.assertEqual( retcode, 0)

    def test101a_metadataextref(self):
        """Sanity Check - Metadata external reference (CMDI)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="0.8" generator="libfolia-v0.4">
<metadata src="test.cmdi.xml" type="cmdi">
<annotations>
    <event-annotation set="test"/>
</annotations>
</metadata>
<text xml:id="test.text" />
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertEqual( doc.metadatatype, folia.MetaDataType.CMDI )
        self.assertEqual( doc.metadatafile, 'test.cmdi.xml' )

    def test101b_metadataextref2(self):
        """Sanity Check - Metadata external reference (IMDI)"""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<FoLiA xmlns="http://ilk.uvt.nl/folia" xmlns:xlink="http://www.w3.org/1999/xlink" xml:id="test" version="0.8" generator="libfolia-v0.4">
<metadata src="test.imdi.xml" type="imdi">
<annotations>
    <event-annotation set="test"/>
</annotations>
</metadata>
<text xml:id="test.text" />
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertEqual( doc.metadatatype, folia.MetaDataType.IMDI )
        self.assertEqual( doc.metadatafile, 'test.imdi.xml' )


    def test102a_declarations(self):
        """Sanity Check - Declarations - Default set"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" />
  </text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertEqual( doc['example.text.1'].select(folia.Gap)[0].set, 'gap-set' )


    def test102a2_declarations(self):
        """Sanity Check - Declarations - Default set, no further defaults"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
      <gap-annotation set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" annotator="proycon" annotatortype="manual" />
  </text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertEqual( doc['example.text.1'].select(folia.Gap)[0].set, 'gap-set' )
        self.assertEqual( doc['example.text.1'].select(folia.Gap)[0].annotator, 'proycon' )
        self.assertEqual( doc['example.text.1'].select(folia.Gap)[0].annotatortype, folia.AnnotatorType.MANUAL)

    def test102b_declarations(self):
        """Sanity Check - Declarations - Set mismatching """
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="extended-gap-set" />
  </text>
</FoLiA>"""
        self.assertRaises( ValueError,  folia.Document, string=xml)


    def test102c_declarations(self):
        """Sanity Check - Declarations - Multiple sets for the same annotation type"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="extended-gap-set"/>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="gap-set"/>
    <gap class="Y" set="extended-gap-set"/>
  </text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertEqual( doc['example.text.1'].select(folia.Gap)[0].set, 'gap-set' )
        self.assertEqual( doc['example.text.1'].select(folia.Gap)[1].set, 'extended-gap-set' )

    def test102d1_declarations(self):
        """Sanity Check - Declarations - Multiple sets for the same annotation type (testing failure)"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="extended-gap-set"/>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="gap-set"/>
    <gap class="Y" />
  </text>
</FoLiA>"""
        self.assertRaises(ValueError,  folia.Document, string=xml )





    def test102d2_declarations(self):
        """Sanity Check - Declarations - Multiple sets for the same annotation type (testing failure)"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="extended-gap-set"/>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="gap-set"/>
    <gap class="Y" set="gip-set"/>
  </text>
</FoLiA>"""
        self.assertRaises(ValueError,  folia.Document, string=xml )

    def test102d3_declarations(self):
        """Sanity Check - Declarations - Ignore Duplicates"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
      <gap-annotation annotator="sloot" set="gap-set"/>
      <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="gap-set"/>
  </text>
</FoLiA>"""

        doc = folia.Document(string=xml)
        self.assertEqual( doc.defaultset(folia.AnnotationType.GAP), 'gap-set' )
        self.assertEqual( doc.defaultannotator(folia.AnnotationType.GAP), "sloot" )


    def test102e_declarations(self):
        """Sanity Check - Declarations - Missing declaration"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="extended-gap-set" />
  </text>
</FoLiA>"""
        self.assertRaises( ValueError,  folia.Document, string=xml)

    def test102f_declarations(self):
        """Sanity Check - Declarations - Declaration not needed"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap />
  </text>
</FoLiA>"""
        doc = folia.Document(string=xml)


    def test102g_declarations(self):
        """Sanity Check - Declarations - 'Undefined' set in declaration"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
        <gap-annotation annotator="sloot" />
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X"  />
  </text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertEqual( doc['example.text.1'].select(folia.Gap)[0].set, 'undefined' )

    def test102h_declarations(self):
        """Sanity Check - Declarations - Double ambiguous declarations unset default"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
         <gap-annotation annotator="sloot" set="gap-set"/>
         <gap-annotation annotator="proycon" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap />
  </text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertRaises(folia.NoDefaultError, doc.defaultannotator, folia.AnnotationType.GAP)


    def test102i_declarations(self):
        """Sanity Check - Declarations - miscellanious trouble"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
         <gap-annotation annotator="sloot" set="gap1-set"/>
         <gap-annotation annotator="sloot" set="gap2-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" set="gap1-set"/>
  </text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertEqual( doc.defaultannotator(folia.AnnotationType.GAP,"gap1-set"), "sloot" )
        doc.declare(folia.AnnotationType.GAP, "gap1-set", annotator='proycon' ) #slightly different behaviour from libfolia: here this overrides the earlier default
        self.assertEqual( doc.defaultannotator(folia.AnnotationType.GAP,"gap1-set"), "proycon" )
        self.assertEqual( doc.defaultannotator(folia.AnnotationType.GAP,"gap2-set"), "sloot" )

        text = doc["example.text.1"]
        text.append( folia.Gap(doc, set='gap1-set', cls='Y', annotator='proycon') )
        text.append( folia.Gap(doc, set='gap1-set', cls='Z1' ) )
        text.append( folia.Gap(doc, set='gap2-set', cls='Z2' ) )
        text.append( folia.Gap(doc, set='gap2-set', cls='Y2', annotator='onbekend' ) )
        gaps = text.select(folia.Gap)
        self.assertTrue( xmlcheck(gaps[0].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" annotator="sloot" class="X" set="gap1-set"/>' ) )
        self.assertTrue( xmlcheck(gaps[1].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="Y" set="gap1-set"/>') )
        self.assertTrue( xmlcheck(gaps[2].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="Z1" set="gap1-set"/>') )
        self.assertTrue( xmlcheck(gaps[3].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="Z2" set="gap2-set"/>') )
        self.assertTrue( xmlcheck(gaps[4].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" annotator="onbekend" class="Y2" set="gap2-set"/>') )


    def test102j_declarations(self):
        """Sanity Check - Declarations - Adding a declaration in other set."""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
         <gap-annotation annotator="sloot" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" />
  </text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        text = doc["example.text.1"]
        doc.declare(folia.AnnotationType.GAP, "other-set", annotator='proycon' )
        text.append( folia.Gap(doc, set='other-set', cls='Y', annotator='proycon') )
        text.append( folia.Gap(doc, set='other-set', cls='Z' ) )

        gaps = text.select(folia.Gap)
        self.assertEqual( gaps[0].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="X" set="gap-set"/>' )
        self.assertEqual( gaps[1].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="Y" set="other-set"/>' )
        self.assertEqual( gaps[2].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="Z" set="other-set"/>' )


    def test102k_declarations(self):
        """Sanity Check - Declarations - Several annotator types."""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
         <gap-annotation annotatortype="auto" set="gap-set"/>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" />
  </text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertEqual( doc.defaultannotatortype(folia.AnnotationType.GAP, 'gap-set'),  folia.AnnotatorType.AUTO)
        text = doc["example.text.1"]
        gaps = text.select(folia.Gap)
        self.assertTrue( xmlcheck(gaps[0].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="X"/>' ) )

        doc.declare(folia.AnnotationType.GAP, "gap-set", annotatortype=folia.AnnotatorType.MANUAL )
        self.assertEqual( doc.defaultannotatortype(folia.AnnotationType.GAP), folia.AnnotatorType.MANUAL )
        self.assertRaises( ValueError, folia.Gap, doc, set='gap-set', cls='Y', annotatortype='unknown' )

        text.append( folia.Gap(doc, set='gap-set', cls='Y', annotatortype='manual' ) )
        text.append( folia.Gap(doc, set='gap-set', cls='Z', annotatortype='auto' ) )

        gaps = text.select(folia.Gap)
        self.assertTrue( xmlcheck(gaps[0].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" annotatortype="auto" class="X" />') )
        self.assertTrue( xmlcheck(gaps[1].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" class="Y" />') )
        self.assertTrue( xmlcheck(gaps[2].xmlstring(), '<gap xmlns="http://ilk.uvt.nl/folia" annotatortype="auto" class="Z" />') )



    def test102l_declarations(self):
        """Sanity Check - Declarations - Datetime default."""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
         <gap-annotation set="gap-set" datetime="2011-12-15T19:00" />
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <gap class="X" />
  </text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertEqual( doc.defaultdatetime(folia.AnnotationType.GAP, 'gap-set'),  folia.parse_datetime('2011-12-15T19:00') )

        self.assertEqual( doc["example.text.1"].select(folia.Gap)[0].datetime ,  folia.parse_datetime('2011-12-15T19:00') )





    def test103_namespaces(self):
        """Sanity Check - Alien namespaces - Checking whether properly ignored"""
        xml = """<?xml version="1.0"?>\n
<FoLiA xmlns:xlink="http://www.w3.org/1999/xlink"
xmlns="http://ilk.uvt.nl/folia" xmlns:alien="http://somewhere.else" xml:id="example" generator="lib
folia-v0.8" version="0.8">
  <metadata type="native">
    <annotations>
    </annotations>
  </metadata>
  <text xml:id="example.text.1">
    <s xml:id="example.text.1.s.1">
        <alien:blah>
            <w xml:id="example.text.1.s.1.alienword">
                <t>blah</t>
            </w>
        </alien:blah>
        <w xml:id="example.text.1.s.1.w.1">
            <t>word</t>
            <alien:invasion number="99999" />
        </w>
    </s>
  </text>
</FoLiA>"""
        doc = folia.Document(string=xml)
        self.assertTrue( len(doc['example.text.1.s.1'].words()) == 1 ) #second word is in alien namespace, not read
        self.assertRaises( KeyError,  doc.__getitem__, 'example.text.1.s.1.alienword') #doesn't exist


class Test4Edit(unittest.TestCase):

    def setUp(self):
        global FOLIAEXAMPLE
        self.doc = folia.Document(string=FOLIAEXAMPLE)

    def test001_addsentence(self):
        """Edit Check - Adding a sentence to last paragraph (verbose)"""

        #grab last paragraph
        p = self.doc.paragraphs(-1)

        #how many sentences?
        tmp = len(p.sentences())

        #make a sentence
        s = folia.Sentence(self.doc, generate_id_in=p)
        #add words to the sentence
        s.append( folia.Word(self.doc, text='Dit',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        s.append( folia.Word(self.doc, text='is',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        s.append( folia.Word(self.doc, text='een',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        s.append( folia.Word(self.doc, text='nieuwe',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        s.append( folia.Word(self.doc, text='zin',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO, space=False ) )
        s.append( folia.Word(self.doc, text='.',generate_id_in=s, annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )

        #add the sentence
        p.append(s)

        #ID check
        self.assertEqual( s[0].id, s.id + '.w.1' )
        self.assertEqual( s[1].id, s.id + '.w.2' )
        self.assertEqual( s[2].id, s.id + '.w.3' )
        self.assertEqual( s[3].id, s.id + '.w.4' )
        self.assertEqual( s[4].id, s.id + '.w.5' )
        self.assertEqual( s[5].id, s.id + '.w.6' )

        #index check
        self.assertEqual( self.doc[s.id], s )
        self.assertEqual( self.doc[s.id + '.w.3'], s[2] )

        #attribute check
        self.assertEqual( s[0].annotator, 'testscript' )
        self.assertEqual( s[0].annotatortype, folia.AnnotatorType.AUTO )

        #addition to paragraph correct?
        self.assertEqual( len(p.sentences()) , tmp + 1)
        self.assertEqual( p[-1] , s)

        # text() ok?
        self.assertEqual( s.text(), "Dit is een nieuwe zin." )

        # xml() ok?
        self.assertTrue( xmlcheck( s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.9"><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.1" annotator="testscript"><t>Dit</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.2" annotator="testscript"><t>is</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.3" annotator="testscript"><t>een</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.4" annotator="testscript"><t>nieuwe</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.5" annotator="testscript" space="no"><t>zin</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.6" annotator="testscript"><t>.</t></w></s>') )

    def test001b_addsentence(self):
        """Edit Check - Adding a sentence to last paragraph (shortcut)"""

        #grab last paragraph
        p = self.doc.paragraphs(-1)

        #how many sentences?
        tmp = len(p.sentences())

        s = p.append(folia.Sentence)
        s.append(folia.Word,'Dit')
        s.append(folia.Word,'is')
        s.append(folia.Word,'een')
        s.append(folia.Word,'nieuwe')
        w = s.append(folia.Word,'zin')
        w2 = s.append(folia.Word,'.',cls='PUNCTUATION')

        self.assertEqual( len(s.words()), 6 ) #number of words in sentence
        self.assertEqual( w.text(), 'zin' ) #text check
        self.assertEqual( self.doc[w.id], w ) #index check

        #addition to paragraph correct?
        self.assertEqual( len(p.sentences()) , tmp + 1)
        self.assertEqual( p[-1] , s)

        self.assertTrue( xmlcheck(s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.9"><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.1"><t>Dit</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.2"><t>is</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.3"><t>een</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.4"><t>nieuwe</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.5"><t>zin</t></w><w xml:id="WR-P-E-J-0000000001.p.1.s.9.w.6" class="PUNCTUATION"><t>.</t></w></s>'))



    def test002_addannotation(self):
        """Edit Check - Adding a token annotation (pos, lemma) (pre-generated instances)"""

        #grab a word (naam)
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.11']

        self.doc.declare(folia.PosAnnotation, 'adhocpos')
        self.doc.declare(folia.LemmaAnnotation, 'adhoclemma')

        #add a pos annotation (in a different set than the one already present, to prevent conflict)
        w.append( folia.PosAnnotation(self.doc, set='adhocpos', cls='NOUN', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        w.append( folia.LemmaAnnotation(self.doc, set='adhoclemma', cls='NAAM', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO, datetime=datetime(1982, 12, 15, 19, 0, 1) ) )

        #retrieve and check
        p = w.annotation(folia.PosAnnotation, 'adhocpos')
        self.assertTrue( isinstance(p, folia.PosAnnotation) )
        self.assertEqual( p.cls, 'NOUN' )

        l = w.annotation(folia.LemmaAnnotation, 'adhoclemma')
        self.assertTrue( isinstance(l, folia.LemmaAnnotation) )
        self.assertEqual( l.cls, 'NAAM' )

        self.assertTrue( xmlcheck(w.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.2.w.11"><t>naam</t><pos class="N(soort,ev,basis,zijd,stan)" set="cgn-combinedtags"/><lemma class="naam" set="lemmas-nl"/><pos class="NOUN" set="adhocpos" annotatortype="auto" annotator="testscript"/><lemma set="adhoclemma" class="NAAM" datetime="1982-12-15T19:00:01" annotatortype="auto" annotator="testscript"/></w>') )

    def test002b_addannotation(self):
        """Edit Check - Adding a token annotation (pos, lemma) (instances generated on the fly)"""

        #grab a word (naam)
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.11']

        self.doc.declare(folia.PosAnnotation, 'adhocpos')
        self.doc.declare(folia.LemmaAnnotation, 'adhoclemma')

        #add a pos annotation (in a different set than the one already present, to prevent conflict)
        w.append( folia.PosAnnotation, set='adhocpos', cls='NOUN', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)
        w.append( folia.LemmaAnnotation, set='adhoclemma', cls='NAAM', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO )

        #retrieve and check
        p = w.annotation(folia.PosAnnotation, 'adhocpos')
        self.assertTrue( isinstance(p, folia.PosAnnotation) )
        self.assertEqual( p.cls, 'NOUN' )

        l = w.annotation(folia.LemmaAnnotation, 'adhoclemma')
        self.assertTrue( isinstance(l, folia.LemmaAnnotation) )
        self.assertEqual( l.cls, 'NAAM' )

        self.assertTrue( xmlcheck(w.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.2.w.11"><t>naam</t><pos class="N(soort,ev,basis,zijd,stan)" set="cgn-combinedtags"/><lemma class="naam" set="lemmas-nl"/><pos class="NOUN" set="adhocpos" annotatortype="auto" annotator="testscript"/><lemma class="NAAM" set="adhoclemma" annotatortype="auto" annotator="testscript"/></w>'))


    def test004_addinvalidannotation(self):
        """Edit Check - Adding a token default-set annotation that clashes with the existing one"""
        #grab a word (naam)
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.11']

        #add a pos annotation without specifying a set (should take default set), but this will clash with existing tag!

        self.assertRaises( folia.DuplicateAnnotationError, w.append, folia.PosAnnotation(self.doc,  cls='N', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO) )
        self.assertRaises( folia.DuplicateAnnotationError, w.append, folia.LemmaAnnotation(self.doc, cls='naam', annotator='testscript', annotatortype=folia.AnnotatorType.AUTO ) )

    def test005_addalternative(self):
        """Edit Check - Adding an alternative token annotation"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.2.w.11']
        w.append( folia.Alternative(self.doc, generate_id_in=w, contents=folia.PosAnnotation(self.doc, cls='V')))

        #reobtaining it:
        alt = list(w.alternatives()) #all alternatives

        set = self.doc.defaultset(folia.AnnotationType.POS)

        alt2 = w.alternatives(folia.PosAnnotation, set)

        self.assertEqual( alt[0],alt2[0] )
        self.assertEqual( len(alt),1 )
        self.assertEqual( len(alt2),1 )
        self.assertTrue( isinstance(alt[0].annotation(folia.PosAnnotation, set), folia.PosAnnotation) )

        self.assertTrue( xmlcheck(w.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.2.w.11"><t>naam</t><pos class="N(soort,ev,basis,zijd,stan)"/><lemma class="naam"/><alt xml:id="WR-P-E-J-0000000001.p.1.s.2.w.11.alt.1" auth="no"><pos class="V"/></alt></w>'))


    def test006_addcorrection(self):
        """Edit Check - Correcting Text"""
        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn

        w.correct(new='stippellijn', set='corrections',cls='spelling',annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)
        self.assertEqual( w.annotation(folia.Correction).original(0).text() ,'stippelijn' )
        self.assertEqual( w.annotation(folia.Correction).new(0).text() ,'stippellijn' )
        self.assertEqual( w.text(), 'stippellijn')

        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><pos class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotatortype="auto" annotator="testscript"><new><t>stippellijn</t></new><original auth="no"><t class="original">stippelijn</t></original></correction></w>'))

    def test006b_addcorrection(self):
        """Edit Check - Correcting Text (2)"""
        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn

        w.correct(new=folia.TextContent(self.doc,value='stippellijn',set='undefined',cls='current'), set='corrections',cls='spelling',annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)
        self.assertEqual( w.annotation(folia.Correction).original(0).text() ,'stippelijn' )
        self.assertEqual( w.annotation(folia.Correction).new(0).text() ,'stippellijn' )
        self.assertEqual( w.text(), 'stippellijn')

        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><pos class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotatortype="auto" annotator="testscript"><new><t>stippellijn</t></new><original auth="no"><t class="original">stippelijn</t></original></correction></w>'))

    def test007_addcorrection2(self):
        """Edit Check - Correcting a Token Annotation element"""
        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn
        oldpos = w.annotation(folia.PosAnnotation)
        newpos = folia.PosAnnotation(self.doc, cls='N(soort,ev,basis,zijd,stan)')
        w.correct(original=oldpos,new=newpos, set='corrections',cls='spelling',annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)

        self.assertEqual( w.annotation(folia.Correction).original(0) ,oldpos )
        self.assertEqual( w.annotation(folia.Correction).new(0),newpos )

        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><t>stippelijn</t><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotatortype="auto" annotator="testscript"><new><pos class="N(soort,ev,basis,zijd,stan)"/></new><original auth="no"><pos class="FOUTN(soort,ev,basis,zijd,stan)"/></original></correction><lemma class="stippelijn"/></w>'))

    def test008_addsuggestion(self):
        """Edit Check - Suggesting a text correction"""
        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn
        w.correct(suggestion='stippellijn', set='corrections',cls='spelling',annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)

        self.assertTrue( isinstance(w.annotation(folia.Correction), folia.Correction) )
        self.assertEqual( w.annotation(folia.Correction).suggestions(0).text() , 'stippellijn' )
        self.assertEqual( w.text(), 'stippelijn')

        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><t>stippelijn</t><pos class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotatortype="auto" annotator="testscript"><suggestion auth="no"><t>stippellijn</t></suggestion></correction></w>'))

def test009a_idclash(self):
    """Edit Check - Checking for exception on adding a duplicate ID"""
    w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11']

    self.assertRaises( folia.DuplicateIDError,  w.sentence().append, folia.Word, id='WR-P-E-J-0000000001.p.1.s.8.w.11', text='stippellijn')


#def test009b_textcorrectionlevel(self):
#    """Edit Check - Checking for exception on an adding TextContent of wrong level"""
#    w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11']
#
#    self.assertRaises(  ValueError, w.append, folia.TextContent, value='blah', corrected=folia.TextCorrectionLevel.ORIGINAL )
#

#def test009c_duptextcontent(self):
#    """Edit Check - Checking for exception on an adding duplicate textcontent"""
#    w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11']
#
#    self.assertRaises(  folia.DuplicateAnnotationError, w.append, folia.TextContent, value='blah', corrected=folia.TextCorrectionLevel.PROCESSED )

def test010_documentlesselement(self):
    """Edit Check - Creating an initially document-less tokenannotation element and adding it to a word"""

    #not associated with any document yet (first argument is None instead of Document instance)
    pos = folia.PosAnnotation(None, set='fakecgn', cls='N')

    w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11']
    w.append(pos)

    self.assertEqual( w.annotation(folia.PosAnnotation,'fakecgn'), pos)
    self.assertEqual( pos.parent, w)
    self.assertEqual( pos.doc, w.doc)

    self.assertTrue( xmlcheck(w.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><t>stippelijn</t><pos class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><pos class="N" set="fakecgn"/></w>'))

    def test011_subtokenannot(self):
        """Edit Check - Adding morphemes"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.5.w.3']
        l = w.append( folia.MorphologyLayer )
        l.append( folia.Morpheme(self.doc, folia.TextContent(self.doc, value='handschrift', offset=0), folia.LemmaAnnotation(self.doc, cls='handschrift'), cls='stem',function='lexical'  ))
        l.append( folia.Morpheme(self.doc, folia.TextContent(self.doc, value='en', offset=11), cls='suffix',function='inflexional' ))


        self.assertEqual( len(l), 2) #two morphemes
        self.assertTrue( isinstance(l[0], folia.Morpheme ) )
        self.assertEqual( l[0].text(), 'handschrift' )
        self.assertEqual( l[0].cls , 'stem' )
        self.assertEqual( l[0].feat('function'), 'lexical' )
        self.assertEqual( l[1].text(), 'en' )
        self.assertEqual( l[1].cls, 'suffix' )
        self.assertEqual( l[1].feat('function'), 'inflexional' )



        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.5.w.3"><t>handschriften</t><pos class="N(soort,mv,basis)"/><lemma class="handschrift"/><morphology><morpheme function="lexical" class="stem"><t offset="0">handschrift</t><lemma class="handschrift"/></morpheme><morpheme function="inflexional" class="suffix"><t offset="11">en</t></morpheme></morphology></w>'))

    def test012_alignment(self):
        """Edit Check - Adding Alignment"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.6.w.8']

        a = w.append( folia.Alignment, cls="coreference")
        a.append( folia.AlignReference, id='WR-P-E-J-0000000001.p.1.s.6.w.1', type=folia.Word)
        a.append( folia.AlignReference, id='WR-P-E-J-0000000001.p.1.s.6.w.2', type=folia.Word)

        self.assertEqual( a.resolve()[0], self.doc['WR-P-E-J-0000000001.p.1.s.6.w.1'] )
        self.assertEqual( a.resolve()[1], self.doc['WR-P-E-J-0000000001.p.1.s.6.w.2'] )

        self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.6.w.8"><t>ze</t><pos class="VNW(pers,pron,stan,red,3,mv)"/><lemma class="ze"/><alignment class="coreference"><aref type="w" id="WR-P-E-J-0000000001.p.1.s.6.w.1"/><aref type="w" id="WR-P-E-J-0000000001.p.1.s.6.w.2"/></alignment></w>'))

    def test013_spanannot(self):
        """Edit Check - Adding Span Annotatation (syntax)"""

        s = self.doc['WR-P-E-J-0000000001.p.1.s.4']
        #sentence: 'De hoofdletter A wordt gebruikt voor het originele handschrift .'
        layer = s.append(folia.SyntaxLayer)
        layer.append(
            folia.SyntacticUnit(self.doc,cls='s',contents=[
                folia.SyntacticUnit(self.doc,cls='np', contents=[
                    folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.1'] ,cls='det'),
                    folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.2'], cls='n'),
                    folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.3'], cls='n'),
                ]),
                folia.SyntacticUnit(self.doc,cls='vp',contents=[
                    folia.SyntacticUnit(self.doc,cls='vp',contents=[
                        folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.4'], cls='v'),
                        folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.5'], cls='participle'),
                    ]),
                    folia.SyntacticUnit(self.doc, cls='pp',contents=[
                        folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.6'], cls='prep'),
                        folia.SyntacticUnit(self.doc, cls='np',contents=[
                            folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.7'], cls='det'),
                            folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.8'], cls='adj'),
                            folia.SyntacticUnit(self.doc, self.doc['WR-P-E-J-0000000001.p.1.s.4.w.9'], cls='n'),
                        ])
                    ])
                ])
            ])
        )

        self.assertTrue( xmlcheck(layer.xmlstring(),'<syntax xmlns="http://ilk.uvt.nl/folia"><su class="s"><su class="np"><su class="det"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.1" t="De"/></su><su class="n"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.2" t="hoofdletter"/></su><su class="n"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.3" t="A"/></su></su><su class="vp"><su class="vp"><su class="v"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.4" t="wordt"/></su><su class="participle"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.5" t="gebruikt"/></su></su><su class="pp"><su class="prep"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.6" t="voor"/></su><su class="np"><su class="det"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.7" t="het"/></su><su class="adj"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.8" t="originele"/></su><su class="n"><wref id="WR-P-E-J-0000000001.p.1.s.4.w.9" t="handschrift"/></su></su></su></su></su></syntax>'))

    def test014_replace(self):
        """Edit Check - Replacing an annotation"""
        word = self.doc['WR-P-E-J-0000000001.p.1.s.3.w.14']
        word.replace(folia.PosAnnotation(self.doc, cls='BOGUS') )

        self.assertEqual( len(list(word.annotations(folia.PosAnnotation))), 1)
        self.assertEqual( word.annotation(folia.PosAnnotation).cls, 'BOGUS')

        self.assertTrue( xmlcheck(word.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.3.w.14"><t>plaats</t><lemma class="plaats"/><pos class="BOGUS"/></w>'))

    def test015_remove(self):
        """Edit Check - Removing an annotation"""
        word = self.doc['WR-P-E-J-0000000001.p.1.s.3.w.14']
        word.remove( word.annotation(folia.PosAnnotation) )

        self.assertRaises( folia.NoSuchAnnotation, word.annotations, folia.PosAnnotation )

        self.assertTrue( xmlcheck(word.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.3.w.14"><t>plaats</t><lemma class="plaats"/></w>'))

    def test016_datetime(self):
        """Edit Check - Time stamp"""
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.16']
        pos = w.annotation(folia.PosAnnotation)
        pos.datetime = datetime(1982, 12, 15, 19, 0, 1) #(the datetime of my joyful birth)

        self.assertTrue( xmlcheck(pos.xmlstring(), '<pos xmlns="http://ilk.uvt.nl/folia" class="WW(pv,tgw,met-t)" datetime="1982-12-15T19:00:01"/>'))

    def test017_wordtext(self):
        """Edit Check - Altering word text"""

        #Important note: directly altering text is usually bad practise, you'll want to use proper corrections instead.
        w = self.doc['WR-P-E-J-0000000001.p.1.s.8.w.9']
        self.assertEqual(w.text(), 'terweil')

        w.settext('terwijl')
        self.assertEqual(w.text(), 'terwijl')

    def test018a_sentencetext(self):
        """Edit Check - Altering sentence text (untokenised by definition)"""
        s = self.doc['WR-P-E-J-0000000001.p.1.s.1']

        self.assertEqual(s.text(), 'Stemma is een ander woord voor stamboom .') #text is obtained from children, since there is no direct text associated

        self.assertFalse(s.hastext()) #no text DIRECTLY associated with the sentence

        #associating text directly with the sentence: de-tokenised by definition!
        s.settext('Stemma is een ander woord voor stamboom.')
        self.assertTrue(s.hastext())
        self.assertEqual(s.text(), 'Stemma is een ander woord voor stamboom.')

    def test018b_sentencetext(self):
        """Edit Check - Altering sentence text (untokenised by definition)"""

        s = self.doc['WR-P-E-J-0000000001.p.1.s.8']

        self.assertEqual( s.text(), 'Een volle lijn duidt op een verwantschap , terweil een stippelijn op een onzekere verwantschap duidt .' ) #dynamic from children


        s.settext('Een volle lijn duidt op een verwantschap, terwijl een stippellijn op een onzekere verwantschap duidt.' )
        s.settext('Een volle lijn duidt op een verwantschap, terweil een stippelijn op een onzekere verwantschap duidt.', 'original' )

        self.assertEqual( s.text(), 'Een volle lijn duidt op een verwantschap, terwijl een stippellijn op een onzekere verwantschap duidt.' ) #processed version by default
        self.assertEqual( s.text('original'), 'Een volle lijn duidt op een verwantschap, terweil een stippelijn op een onzekere verwantschap duidt.' )
        self.assertTrue( s.hastext('original') )

        self.assertTrue( xmlcheck(s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8"><t>Een volle lijn duidt op een verwantschap, terwijl een stippellijn op een onzekere verwantschap duidt.</t><t class="original">Een volle lijn duidt op een verwantschap, terweil een stippelijn op een onzekere verwantschap duidt.</t><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.1"><t>Een</t><pos class="LID(onbep,stan,agr)"/><lemma class="een"/></w><quote xml:id="WR-P-E-J-0000000001.p.1.s.8.q.1"><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.2"><t>volle</t><pos class="ADJ(prenom,basis,met-e,stan)"/><lemma class="vol"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.3"><t>lijn</t><pos class="N(soort,ev,basis,zijd,stan)"/><lemma class="lijn"/></w></quote><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.4"><t>duidt</t><pos class="WW(pv,tgw,met-t)"/><lemma class="duiden"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.5"><t>op</t><pos class="VZ(init)"/><lemma class="op"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.6"><t>een</t><pos class="LID(onbep,stan,agr)"/><lemma class="een"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.7"><t>verwantschap</t><pos class="N(soort,ev,basis,zijd,stan)"/><lemma class="verwantschap"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.8"><t>,</t><pos class="LET()"/><lemma class=","/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.9"><t>terweil</t><errordetection class="spelling"/><pos class="VG(onder)"/><lemma class="terweil"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.10"><t>een</t><pos class="LID(onbep,stan,agr)"/><lemma class="een"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><t>stippelijn</t><pos class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.12"><t>op</t><pos class="VZ(init)"/><lemma class="op"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.13"><t>een</t><pos class="LID(onbep,stan,agr)"/><lemma class="een"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.14"><t>onzekere</t><pos class="ADJ(prenom,basis,met-e,stan)"/><lemma class="onzeker"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.14.c.1" class="spelling"><suggestion  auth="no"><t>twijfelachtige</t></suggestion><suggestion  auth="no"><t>ongewisse</t></suggestion></correction></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.15"><t>verwantschap</t><pos class="N(soort,ev,basis,zijd,stan)" datetime="2011-07-20T19:00:01"/><lemma class="verwantschap"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.16"><t>duidt</t><pos class="WW(pv,tgw,met-t)"/><lemma class="duiden"/></w><w xml:id="WR-P-E-J-0000000001.p.1.s.8.w.17"><t>.</t><pos class="LET()"/><lemma class="."/></w></s>'))

    def test019_adderrordetection(self):
        """Edit Check - Error Detection"""
        w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn

        w.append( folia.ErrorDetection(self.doc, cls="spelling", annotator="testscript", annotatortype=folia.AnnotatorType.AUTO) )
        self.assertEqual( w.annotation(folia.ErrorDetection).cls ,'spelling' )

        #self.assertTrue( xmlcheck(w.xmlstring(),'<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><pos class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotatortype="auto" annotator="testscript"><new><t>stippellijn</t></new><original auth="no"><t>stippelijn</t></original></correction></w>'))

    #def test008_addaltcorrection(self):
    #    """Edit Check - Adding alternative corrections"""
    #    w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn
    #    w.correcttext('stippellijn', set='corrections',cls='spelling',annotator='testscript', annotatortype='auto', alternative=True)
    #
    #    alt = w.alternatives(folia.AnnotationType.CORRECTION)
    #    self.assertEqual( alt[0].annotation(folia.Correction).original[0] ,'stippelijn' )
    #    self.assertEqual( alt[0].annotation(folia.Correction).new[0] ,'stippellijn' )

    #def test009_addaltcorrection2(self):
    #    """Edit Check - Adding an alternative and a selected correction"""
    #    w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn
    #    w.correcttext('stippel-lijn', set='corrections',cls='spelling',annotator='testscript', annotatortype='auto', alternative=True)

    #    w.correcttext('stippellijn', set='corrections',cls='spelling',annotator='testscript', annotatortype='auto')

    #    alt = w.alternatives(folia.AnnotationType.CORRECTION)
    #    self.assertEqual( alt[0].annotation(folia.Correction).id ,'WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1' )
    #    self.assertEqual( alt[0].annotation(folia.Correction).original[0] ,'stippelijn' )
    #    self.assertEqual( alt[0].annotation(folia.Correction).new[0] ,'stippel-lijn' )

    #    self.assertEqual( w.annotation(folia.Correction).id ,'WR-P-E-J-0000000001.p.1.s.8.w.11.correction.2' )
    #    self.assertEqual( w.annotation(folia.Correction).original[0] ,'stippelijn' )
    #    self.assertEqual( w.annotation(folia.Correction).new[0] ,'stippellijn' )
    #    self.assertEqual( w.text(), 'stippellijn')

class Test4Create(unittest.TestCase):
        def test001_create(self):
            """Creating a FoLiA Document from scratch"""
            self.doc = folia.Document(id='example')
            self.doc.declare(folia.AnnotationType.TOKEN, 'adhocset',annotator='proycon')

            self.assertEqual(self.doc.defaultset(folia.AnnotationType.TOKEN), 'adhocset')
            self.assertEqual(self.doc.defaultannotator(folia.AnnotationType.TOKEN, 'adhocset'), 'proycon')

            text = folia.Text(self.doc, id=self.doc.id + '.text.1')
            self.doc.append( text )

            text.append(
                folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="De"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="site"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="staat"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="online"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text=".")
                ]
                )
            )

            self.assertEqual( len(self.doc.index[self.doc.id + '.s.1']), 5)

class Test5Correction(unittest.TestCase):
        def setUp(self):
            self.doc = folia.Document(id='example')
            self.doc.declare(folia.AnnotationType.TOKEN, set='adhocset',annotator='proycon')
            self.text = folia.Text(self.doc, id=self.doc.id + '.text.1')
            self.doc.append( self.text )


        def test001_splitcorrection(self):
            """Correction - Split correction"""

            self.text.append(
                folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="De"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="site"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="staat"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="online"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text=".")
                ]
                )
            )


            w = self.doc.index[self.doc.id + '.s.1.w.4']

            w.split( folia.Word(self.doc, id=self.doc.id + '.s.1.w.4a', text="on"), folia.Word(self.doc, id=self.doc.id + '.s.1.w.4b', text="line") )

            s = self.doc.index[self.doc.id + '.s.1']
            self.assertEqual( s.words(-3).text(), 'on' )
            self.assertEqual( s.words(-2).text(), 'line' )
            self.assertEqual( s.text(), 'De site staat on line .' )
            self.assertEqual( len(s.words()), 6 )
            self.assertTrue( xmlcheck(s.xmlstring(),  '<s xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1"><w xml:id="example.s.1.w.1"><t>De</t></w><w xml:id="example.s.1.w.2"><t>site</t></w><w xml:id="example.s.1.w.3"><t>staat</t></w><correction xml:id="example.s.1.correction.1"><new><w xml:id="example.s.1.w.4a"><t>on</t></w><w xml:id="example.s.1.w.4b"><t>line</t></w></new><original auth="no"><w xml:id="example.s.1.w.4"><t>online</t></w></original></correction><w xml:id="example.s.1.w.5"><t>.</t></w></s>'))


        def test001_splitcorrection2(self):
            """Correction - Split suggestion"""

            self.text.append(
                folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="De"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="site"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="staat"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="online"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text=".")
                ]
                )
            )


            w = self.doc.index[self.doc.id + '.s.1.w.4']

            s = self.doc.index[self.doc.id + '.s.1']
            w.split( folia.Word(self.doc, generate_id_in=s, text="on"), folia.Word(self.doc, generate_id_in=s, text="line"), suggest=True )

            self.assertEqual( len(s.words()), 5 )
            self.assertEqual( s.words(-2).text(), 'online' )
            self.assertEqual( s.text(), 'De site staat online .' )

            self.assertTrue( xmlcheck(s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1"><w xml:id="example.s.1.w.1"><t>De</t></w><w xml:id="example.s.1.w.2"><t>site</t></w><w xml:id="example.s.1.w.3"><t>staat</t></w><correction xml:id="example.s.1.correction.1"><current><w xml:id="example.s.1.w.4"><t>online</t></w></current><suggestion auth="no"><w xml:id="example.s.1.w.6"><t>on</t></w><w xml:id="example.s.1.w.7"><t>line</t></w></suggestion></correction><w xml:id="example.s.1.w.5"><t>.</t></w></s>'))


        def test002_mergecorrection(self):
            """Correction - Merge corrections"""
            self.text.append(
                folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="De"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="site"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="staat"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="on"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text="line"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.6', text=".")
                ]
                )
            )

            s = self.doc.index[self.doc.id + '.s.1']


            s.mergewords( folia.Word(self.doc, 'online', id=self.doc.id + '.s.1.w.4-5') , self.doc.index[self.doc.id + '.s.1.w.4'], self.doc.index[self.doc.id + '.s.1.w.5'] )

            self.assertEqual( len(s.words()), 5 )
            self.assertEqual( s.text(), 'De site staat online .')

            #incorrection() test, check if newly added word correctly reports being part of a correction
            w = self.doc.index[self.doc.id + '.s.1.w.4-5']
            self.assertTrue( isinstance(w.incorrection(), folia.Correction) ) #incorrection return the correction the word is part of, or None if not part of a correction,


            self.assertTrue( xmlcheck(s.xmlstring(),  '<s xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1"><w xml:id="example.s.1.w.1"><t>De</t></w><w xml:id="example.s.1.w.2"><t>site</t></w><w xml:id="example.s.1.w.3"><t>staat</t></w><correction xml:id="example.s.1.correction.1"><new><w xml:id="example.s.1.w.4-5"><t>online</t></w></new><original auth="no"><w xml:id="example.s.1.w.4"><t>on</t></w><w xml:id="example.s.1.w.5"><t>line</t></w></original></correction><w xml:id="example.s.1.w.6"><t>.</t></w></s>'))


        def test003_deletecorrection(self):
            """Correction - Deletion"""

            self.text.append(
                folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="Ik"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="zie"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="een"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="groot"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text="huis"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.6', text=".")
                ]
                )
            )
            s = self.doc.index[self.doc.id + '.s.1']
            s.deleteword(self.doc.index[self.doc.id + '.s.1.w.4'])
            self.assertEqual( len(s.words()), 5 )
            self.assertEqual( s.text(), 'Ik zie een huis .')

            self.assertTrue( xmlcheck(s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1"><w xml:id="example.s.1.w.1"><t>Ik</t></w><w xml:id="example.s.1.w.2"><t>zie</t></w><w xml:id="example.s.1.w.3"><t>een</t></w><correction xml:id="example.s.1.correction.1"><new/><original auth="no"><w xml:id="example.s.1.w.4"><t>groot</t></w></original></correction><w xml:id="example.s.1.w.5"><t>huis</t></w><w xml:id="example.s.1.w.6"><t>.</t></w></s>') )

        def test004_insertcorrection(self):
            """Correction - Insert"""
            self.text.append(
                folia.Sentence(self.doc,id=self.doc.id + '.s.1', contents=[
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.1', text="Ik"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.2', text="zie"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.3', text="een"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.4', text="huis"),
                    folia.Word(self.doc,id=self.doc.id + '.s.1.w.5', text=".")
                ]
                )
            )
            s = self.doc.index[self.doc.id + '.s.1']
            s.insertword( folia.Word(self.doc, id=self.doc.id+'.s.1.w.3b',text='groot'),  self.doc.index[self.doc.id + '.s.1.w.3'])
            self.assertEqual( len(s.words()), 6 )

            self.assertEqual( s.text(), 'Ik zie een groot huis .')
            self.assertTrue( xmlcheck( s.xmlstring(), '<s xmlns="http://ilk.uvt.nl/folia" xml:id="example.s.1"><w xml:id="example.s.1.w.1"><t>Ik</t></w><w xml:id="example.s.1.w.2"><t>zie</t></w><w xml:id="example.s.1.w.3"><t>een</t></w><correction xml:id="example.s.1.correction.1"><new><w xml:id="example.s.1.w.3b"><t>groot</t></w></new><original auth="no"/></correction><w xml:id="example.s.1.w.4"><t>huis</t></w><w xml:id="example.s.1.w.5"><t>.</t></w></s>'))

        def test005_reusecorrection(self):
            """Correction - Re-using a correction with only suggestions"""
            global FOLIAEXAMPLE
            self.doc = folia.Document(string=FOLIAEXAMPLE)

            w = self.doc.index['WR-P-E-J-0000000001.p.1.s.8.w.11'] #stippelijn
            w.correct(suggestion='stippellijn', set='corrections',cls='spelling',annotator='testscript', annotatortype=folia.AnnotatorType.AUTO)
            c = w.annotation(folia.Correction)

            self.assertTrue( isinstance(w.annotation(folia.Correction), folia.Correction) )
            self.assertEqual( w.annotation(folia.Correction).suggestions(0).text() , 'stippellijn' )
            self.assertEqual( w.text(), 'stippelijn')

            w.correct(new='stippellijn',set='corrections',cls='spelling',annotator='John Doe', annotatortype=folia.AnnotatorType.MANUAL,reuse=c.id)

            self.assertEqual( w.text(), 'stippellijn')
            self.assertEqual( len(list(w.annotations(folia.Correction))), 1 )
            self.assertEqual( w.annotation(folia.Correction).suggestions(0).text() , 'stippellijn' )
            self.assertEqual( w.annotation(folia.Correction).suggestions(0).annotator , 'testscript' )
            self.assertEqual( w.annotation(folia.Correction).suggestions(0).annotatortype , folia.AnnotatorType.AUTO)
            self.assertEqual( w.annotation(folia.Correction).new(0).text() , 'stippellijn' )
            self.assertEqual( w.annotation(folia.Correction).annotator , 'John Doe' )
            self.assertEqual( w.annotation(folia.Correction).annotatortype , folia.AnnotatorType.MANUAL)

            self.assertTrue( xmlcheck(w.xmlstring(), '<w xmlns="http://ilk.uvt.nl/folia" xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11"><pos class="FOUTN(soort,ev,basis,zijd,stan)"/><lemma class="stippelijn"/><correction xml:id="WR-P-E-J-0000000001.p.1.s.8.w.11.correction.1" class="spelling" annotator="John Doe"><suggestion annotator="testscript" auth="no" annotatortype="auto"><t>stippellijn</t></suggestion><new><t>stippellijn</t></new><original auth="no"><t class="original">stippelijn</t></original></correction></w>'))


class Test6Query(unittest.TestCase):
    def setUp(self):
        global FOLIAEXAMPLE
        self.doc = folia.Document(string=FOLIAEXAMPLE)

    def test001_findwords_simple(self):
        """Querying - Find words (simple)"""
        matches = list(self.doc.findwords( folia.Pattern('van','het','alfabet') ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 3 )
        self.assertEqual( matches[0][0].text(), 'van' )
        self.assertEqual( matches[0][1].text(), 'het' )
        self.assertEqual( matches[0][2].text(), 'alfabet' )


    def test002_findwords_wildcard(self):
        """Querying - Find words (with wildcard)"""
        matches = list(self.doc.findwords( folia.Pattern('van','het',True) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 3 )

        self.assertEqual( matches[0][0].text(), 'van' )
        self.assertEqual( matches[0][1].text(), 'het' )
        self.assertEqual( matches[0][2].text(), 'alfabet' )

    def test003_findwords_annotation(self):
        """Querying - Find words by annotation"""
        matches = list(self.doc.findwords( folia.Pattern('de','historisch','wetenschap','worden', matchannotation=folia.LemmaAnnotation) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )



    def test004_findwords_multi(self):
        """Querying - Find words using a conjunction of multiple patterns """
        matches = list(self.doc.findwords( folia.Pattern('de','historische',True, 'wordt'), folia.Pattern('de','historisch','wetenschap','worden', matchannotation=folia.LemmaAnnotation) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )

    def test005_findwords_none(self):
        """Querying - Find words that don't exist"""
        matches = list(self.doc.findwords( folia.Pattern('bli','bla','blu')))
        self.assertEqual( len(matches), 0)

    def test006_findwords_overlap(self):
        """Querying - Find words with overlap"""
        doc = folia.Document(id='test')
        text = folia.Text(doc, id='test.text')

        text.append(
            folia.Sentence(doc,id=doc.id + '.s.1', contents=[
                folia.Word(doc,id=doc.id + '.s.1.w.1', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.2', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.3', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.4', text="A"),
                folia.Word(doc,id=doc.id + '.s.1.w.5', text="b"),
                folia.Word(doc,id=doc.id + '.s.1.w.6', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.7', text="a"),
            ]
            )
        )
        doc.append(text)

        matches = list(doc.findwords( folia.Pattern('a','a')))
        self.assertEqual( len(matches), 4)
        matches = list(doc.findwords( folia.Pattern('a','a',casesensitive=True)))
        self.assertEqual( len(matches), 3)

    def test007_findwords_context(self):
        """Querying - Find words with context"""
        matches = list(self.doc.findwords( folia.Pattern('van','het','alfabet'), leftcontext=3, rightcontext=3 ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 9 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'laatste' )
        self.assertEqual( matches[0][2].text(), 'letters' )
        self.assertEqual( matches[0][3].text(), 'van' )
        self.assertEqual( matches[0][4].text(), 'het' )
        self.assertEqual( matches[0][5].text(), 'alfabet' )
        self.assertEqual( matches[0][6].text(), 'en' )
        self.assertEqual( matches[0][7].text(), 'worden' )
        self.assertEqual( matches[0][8].text(), 'tussen' )

    def test008_findwords_disjunction(self):
        """Querying - Find words with disjunctions"""
        matches = list(self.doc.findwords( folia.Pattern('de',('historische','hedendaagse'),'wetenschap','wordt') ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )

    def test009_findwords_regexp(self):
        """Querying - Find words with regular expressions"""
        matches = list(self.doc.findwords( folia.Pattern('de',folia.RegExp('hist.*'),folia.RegExp('.*schap'),folia.RegExp('w[oae]rdt')) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )


    def test010a_findwords_variablewildcard(self):
        """Querying - Find words with variable wildcard"""
        matches = list(self.doc.findwords( folia.Pattern('de','laatste','*','alfabet') ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 6 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'laatste' )
        self.assertEqual( matches[0][2].text(), 'letters' )
        self.assertEqual( matches[0][3].text(), 'van' )
        self.assertEqual( matches[0][4].text(), 'het' )
        self.assertEqual( matches[0][5].text(), 'alfabet' )

    def test010b_findwords_varwildoverlap(self):
        """Querying - Find words with variable wildcard and overlap"""
        doc = folia.Document(id='test')
        text = folia.Text(doc, id='test.text')

        text.append(
            folia.Sentence(doc,id=doc.id + '.s.1', contents=[
                folia.Word(doc,id=doc.id + '.s.1.w.1', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.2', text="b"),
                folia.Word(doc,id=doc.id + '.s.1.w.3', text="c"),
                folia.Word(doc,id=doc.id + '.s.1.w.4', text="d"),
                folia.Word(doc,id=doc.id + '.s.1.w.5', text="a"),
                folia.Word(doc,id=doc.id + '.s.1.w.6', text="b"),
                folia.Word(doc,id=doc.id + '.s.1.w.7', text="c"),
            ]
            )
        )
        doc.append(text)

        matches = list(doc.findwords( folia.Pattern('a','*', 'c')))
        self.assertEqual( len(matches), 3)


    def test011_findwords_annotation_na(self):
        """Querying - Find words by non existing annotation"""
        matches = list(self.doc.findwords( folia.Pattern('bli','bla','blu', matchannotation=folia.SenseAnnotation) ))
        self.assertEqual( len(matches), 0 )



class Test9Reader(unittest.TestCase):
    def setUp(self):
        self.reader = folia.Reader("/tmp/foliatest.xml", folia.Word)

    def test000_worditer(self):
        """Stream reader - Iterating over words"""
        count = 0
        for word in self.reader:
            count += 1
        self.assertEqual(count, 178)

    def test001_findwords_simple(self):
        """Querying using stream reader - Find words (simple)"""
        matches = list(self.reader.findwords( folia.Pattern('van','het','alfabet') ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 3 )
        self.assertEqual( matches[0][0].text(), 'van' )
        self.assertEqual( matches[0][1].text(), 'het' )
        self.assertEqual( matches[0][2].text(), 'alfabet' )


    def test002_findwords_wildcard(self):
        """Querying using stream reader - Find words (with wildcard)"""
        matches = list(self.reader.findwords( folia.Pattern('van','het',True) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 3 )

        self.assertEqual( matches[0][0].text(), 'van' )
        self.assertEqual( matches[0][1].text(), 'het' )
        self.assertEqual( matches[0][2].text(), 'alfabet' )

    def test003_findwords_annotation(self):
        """Querying using stream reader - Find words by annotation"""
        matches = list(self.reader.findwords( folia.Pattern('de','historisch','wetenschap','worden', matchannotation=folia.LemmaAnnotation) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )



    def test004_findwords_multi(self):
        """Querying using stream reader - Find words using a conjunction of multiple patterns """
        matches = list(self.reader.findwords( folia.Pattern('de','historische',True, 'wordt'), folia.Pattern('de','historisch','wetenschap','worden', matchannotation=folia.LemmaAnnotation) ))
        self.assertEqual( len(matches), 1 )
        self.assertEqual( len(matches[0]), 4 )
        self.assertEqual( matches[0][0].text(), 'de' )
        self.assertEqual( matches[0][1].text(), 'historische' )
        self.assertEqual( matches[0][2].text(), 'wetenschap' )
        self.assertEqual( matches[0][3].text(), 'wordt' )

    def test005_findwords_none(self):
        """Querying using stream reader - Find words that don't exist"""
        matches = list(self.reader.findwords( folia.Pattern('bli','bla','blu')))
        self.assertEqual( len(matches), 0)


    def test011_findwords_annotation_na(self):
        """Querying using stream reader - Find words by non existing annotation"""
        matches = list(self.reader.findwords( folia.Pattern('bli','bla','blu', matchannotation=folia.SenseAnnotation) ))
        self.assertEqual( len(matches), 0 )

class Test7XpathQuery(unittest.TestCase):
    def test050_findwords_xpath(self):
        """Xpath Querying - Collect all words (including non-authoritative)"""
        count = 0
        for word in folia.Query('/tmp/foliatest.xml','//f:w'):
            count += 1
            self.assertTrue( isinstance(word, folia.Word) )
        self.assertEqual(count, 178)

    def test051_findwords_xpath(self):
        """Xpath Querying - Collect all words (authoritative only)"""
        count = 0
        for word in folia.Query('/tmp/foliatest.xml','//f:w[not(ancestor-or-self::*/@auth)]'):
            count += 1
            self.assertTrue( isinstance(word, folia.Word) )
        self.assertEqual(count, 176)


class Test8Validation(unittest.TestCase):
      def test000_relaxng(self):
        """Validation - RelaxNG schema generation"""
        folia.relaxng()

      def test001_shallowvalidation(self):
        """Validation - Shallow validation against automatically generated RelaxNG schema"""
        folia.validate('/tmp/foliasavetest.xml')

      def test002_loadsetdefinitions(self):
        """Validation - Loading of set definitions"""
        doc = folia.Document(file='/tmp/foliatest.xml', loadsetdefinitions=True)
        assert isinstance( doc.setdefinitions["http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml"], folia.SetDefinition)

      def test003_deepvalidation(self):
        """Validation - Deep Validation"""
        doc = folia.Document(file='/tmp/foliatest.xml', deepvalidation=True, allowadhocsets=True)
        assert isinstance( doc.setdefinitions["http://raw.github.com/proycon/folia/master/setdefinitions/namedentities.foliaset.xml"], folia.SetDefinition)

f = io.open(FOLIAPATH + '/test/example.xml', 'r',encoding='utf-8')
FOLIAEXAMPLE = f.read()
f.close()


DCOIEXAMPLE="""<?xml version="1.0" encoding="iso-8859-15"?>
<DCOI xmlns:imdi="http://www.mpi.nl/IMDI/Schema/IMDI" xmlns="http://lands.let.ru.nl/projects/d-coi/ns/1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:d-coi="http://lands.let.ru.nl/projects/d-coi/ns/1.0" xsi:schemaLocation="http://lands.let.ru.nl/projects/d-coi/ns/1.0 dcoi.xsd" xml:id="WR-P-E-J-0000125009">
  <imdi:METATRANSCRIPT xmlns:imdi="http://www.mpi.nl/IMDI/Schema/IMDI" Date="2009-01-27" Type="SESSION" Version="1">
    <imdi:Session>
      <imdi:Name>WR-P-E-J-0000125009</imdi:Name>
      <imdi:Title>Aspirine 3D model van Aspirine</imdi:Title>
      <imdi:Date>2009-01-27</imdi:Date>
      <imdi:Description/>
      <imdi:MDGroup>
        <imdi:Location>
          <imdi:Continent>Europe</imdi:Continent>
          <imdi:Country>NL/B</imdi:Country>
        </imdi:Location>
        <imdi:Keys/>
        <imdi:Project>
          <imdi:Name>D-Coi</imdi:Name>
          <imdi:Title/>
          <imdi:Id/>
          <imdi:Contact/>
          <imdi:Description/>
        </imdi:Project>
        <imdi:Collector>
          <imdi:Name/>
          <imdi:Contact/>
          <imdi:Description/>
        </imdi:Collector>
        <imdi:Content>
          <imdi:Task/>
          <imdi:Modalities/>
          <imdi:CommunicationContext>
            <imdi:Interactivity/>
            <imdi:PlanningType/>
            <imdi:Involvement/>
          </imdi:CommunicationContext>
          <imdi:Genre>
            <imdi:Interactional/>
            <imdi:Discursive/>
            <imdi:Performance/>
          </imdi:Genre>
          <imdi:Languages>
            <imdi:Language>
              <imdi:Id/>
              <imdi:Name>Dutch</imdi:Name>
              <imdi:Description/>
            </imdi:Language>
          </imdi:Languages>
          <imdi:Keys/>
        </imdi:Content>
        <imdi:Participants/>
      </imdi:MDGroup>
      <imdi:Resources>
        <imdi:MediaFile>
          <imdi:ResourceLink/>
          <imdi:Size>162304</imdi:Size>
          <imdi:Type/>
          <imdi:Format/>
          <imdi:Quality>Unknown</imdi:Quality>
          <imdi:RecordingConditions/>
          <imdi:TimePosition Start="Unknown"/>
          <imdi:Access>
            <imdi:Availability/>
            <imdi:Date/>
            <imdi:Owner/>
            <imdi:Publisher/>
            <imdi:Contact/>
            <imdi:Description/>
          </imdi:Access>
          <imdi:Description/>
        </imdi:MediaFile>
        <imdi:AnnotationUnit>
          <imdi:ResourceLink/>
          <imdi:MediaResourceLink/>
          <imdi:Annotator/>
          <imdi:Date/>
          <imdi:Type/>
          <imdi:Format/>
          <imdi:ContentEncoding/>
          <imdi:CharacterEncoding/>
          <imdi:Access>
            <imdi:Availability/>
            <imdi:Date/>
            <imdi:Owner/>
            <imdi:Publisher/>
            <imdi:Contact/>
            <imdi:Description/>
          </imdi:Access>
          <imdi:LanguageId/>
          <imdi:Anonymous>false</imdi:Anonymous>
          <imdi:Description/>
        </imdi:AnnotationUnit>
        <imdi:Source>
          <imdi:Id/>
          <imdi:Format/>
          <imdi:Quality>Unknown</imdi:Quality>
          <imdi:TimePosition Start="Unknown"/>
          <imdi:Access>
            <imdi:Availability>GNU Free Documentation License</imdi:Availability>
            <imdi:Date/>
            <imdi:Owner/>
            <imdi:Publisher>Wikimedia Foundation (NL/B)</imdi:Publisher>
            <imdi:Contact/>
            <imdi:Description/>
          </imdi:Access>
          <imdi:Description/>
        </imdi:Source>
      </imdi:Resources>
    </imdi:Session>
  </imdi:METATRANSCRIPT>
  <text xml:id="WR-P-E-J-0000125009.text">
    <body>
      <div xml:id="WR-P-E-J-0000125009.div.1">
        <head xml:id="WR-P-E-J-0000125009.head.1">
          <s xml:id="WR-P-E-J-0000125009.head.1.s.1">
            <w xml:id="WR-P-E-J-0000125009.head.1.s.1.w.1" pos="N(eigen,ev,basis,zijd,stan)" lemma="Aspirine">Aspirine</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.head.1.s.2">
            <w xml:id="WR-P-E-J-0000125009.head.1.s.2.w.1" pos="TW(hoofd,prenom,stan)" lemma="3D">3D</w>
            <w xml:id="WR-P-E-J-0000125009.head.1.s.2.w.2" pos="N(soort,ev,basis,onz,stan)" lemma="model">model</w>
            <w xml:id="WR-P-E-J-0000125009.head.1.s.2.w.3" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.head.1.s.2.w.4" pos="N(eigen,ev,basis,zijd,stan)" lemma="Aspirine">Aspirine</w>
          </s>
        </head>
        <p xml:id="WR-P-E-J-0000125009.p.1">
          <s xml:id="WR-P-E-J-0000125009.p.1.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.1.s.1.w.1" pos="N(eigen,ev,basis,zijd,stan)" lemma="Aspirine">Aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.1.w.2" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.1.w.3" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.1.w.4" pos="N(soort,ev,basis,zijd,stan)" lemma="merknaam">merknaam</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.1.w.5" pos="VZ(init)" lemma="voor">voor</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.1.w.6" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.1.w.7" pos="N(soort,ev,basis,zijd,stan)" lemma="medicijn">medicijn</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.1.w.8" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.1.w.9" pos="N(eigen,ev,basis,zijd,stan)" lemma="Bayer">Bayer</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.1.w.10" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.1.s.2">
            <w xml:id="WR-P-E-J-0000125009.p.1.s.2.w.1" pos="LID(bep,stan,rest)" lemma="de">De</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.2.w.2" pos="ADJ(prenom,basis,met-e,stan)" lemma="werkzaam">werkzame</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.2.w.3" pos="N(soort,ev,basis,zijd,stan)" lemma="stof">stof</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.2.w.4" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.2.w.5" pos="N(soort,ev,basis,onz,stan)" lemma="acetylsalicylzuur">acetylsalicylzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.2.w.6" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.1.s.3">
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.1" pos="N(eigen,ev,basis,zijd,stan)" lemma="Aspirine">Aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.2" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.3" pos="BW()" lemma="ook">ook</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.4" pos="ADJ(vrij,basis,zonder)" lemma="bekend">bekend</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.5" pos="VZ(init)" lemma="onder">onder</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.6" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.7" pos="N(soort,ev,basis,zijd,stan)" lemma="naam">naam</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="acetosal">acetosal</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.9" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.10" pos="N(soort,mv,basis)" lemma="aspro">aspro</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.11" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.12" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dat">dat</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.13" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.14" pos="N(soort,ev,basis,zijd,stan)" lemma="merknaam">merknaam</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.15" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.16" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.17" pos="SPEC(deeleigen)" lemma="_">Nicholas</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.18" pos="SPEC(deeleigen)" lemma="_">Ltd.</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.19" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">Het</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.20" pos="WW(pv,tgw,met-t)" lemma="werken">werkt</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.21" pos="ADJ(vrij,basis,zonder)" lemma="pijnstillend">pijnstillend</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.22" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.23" pos="ADJ(vrij,basis,zonder)" lemma="koortsverlagend">koortsverlagend</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.24" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.25" pos="ADJ(vrij,basis,zonder)" lemma="ontstekingsremmend">ontstekingsremmend</w>
            <w xml:id="WR-P-E-J-0000125009.p.1.s.3.w.26" pos="LET()" lemma=".">.</w>
          </s>
        </p>
        <p xml:id="WR-P-E-J-0000125009.p.2">
          <s xml:id="WR-P-E-J-0000125009.p.2.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.1" pos="ADJ(vrij,basis,zonder)" lemma="Oorspronkelijk">Oorspronkelijk</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.2" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.3" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.4" pos="N(soort,ev,basis,zijd,stan)" lemma="werking">werking</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.5" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.6" pos="N(soort,ev,basis,onz,stan)" lemma="salicylzuur">salicylzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.7" pos="VZ(init)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="pijnstiller">pijnstiller</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.9" pos="WW(vd,vrij,zonder)" lemma="ontdekken">ontdekt</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.10" pos="VG(onder)" lemma="doordat">doordat</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.11" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.12" pos="WW(pv,verl,ev)" lemma="worden">werd</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.13" pos="WW(vd,vrij,zonder)" lemma="identificeren">geïdentificeerd</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.14" pos="VZ(init)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.15" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.16" pos="ADJ(prenom,basis,met-e,stan)" lemma="werkzaam">werkzame</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.17" pos="N(soort,ev,basis,zijd,stan)" lemma="stof">stof</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.18" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.19" pos="N(soort,ev,basis,zijd,stan)" lemma="wilgenbast">wilgenbast</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.1.w.20" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.2.s.2">
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.1" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">Het</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="zuur">zuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.3" pos="BW()" lemma="zelf">zelf</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.4" pos="WW(pv,verl,ev)" lemma="worden">werd</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.5" pos="BW()" lemma="echter">echter</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.6" pos="ADJ(prenom,basis,zonder)" lemma="bijzonder">bijzonder</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.7" pos="ADJ(vrij,basis,zonder)" lemma="slecht">slecht</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.8" pos="VZ(init)" lemma="door">door</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.9" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.10" pos="N(soort,ev,basis,zijd,stan)" lemma="maag">maag</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.11" pos="WW(vd,vrij,zonder)" lemma="tolereren">getolereerd</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.2.w.12" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.2.s.3">
            <w xml:id="WR-P-E-J-0000125009.p.2.s.3.w.1" pos="LID(bep,stan,rest)" lemma="de">De</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.3.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="acetyl-ester">acetyl-ester</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.3.w.3" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.3.w.4" pos="BW()" lemma="daarin">daarin</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.3.w.5" pos="VNW(onbep,grad,stan,vrij,zonder,basis)" lemma="veel">veel</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.3.w.6" pos="ADJ(vrij,comp,zonder)" lemma="goed">beter</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.3.w.7" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.2.s.4">
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.1" pos="VNW(aanw,det,stan,prenom,met-e,rest)" lemma="deze">Deze</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="stof">stof</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.3" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.4" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.5" pos="ADJ(prenom,basis,met-e,stan)" lemma="zuiver">zuivere</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="toestand">toestand</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.7" pos="VG(neven)" lemma="of">of</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.8" pos="VZ(init)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.9" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.10" pos="VNW(onbep,pron,stan,vol,3o,ev)" lemma="iets">iets</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.11" pos="VNW(onbep,grad,stan,vrij,zonder,comp)" lemma="minder">minder</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.12" pos="ADJ(prenom,basis,met-e,stan)" lemma="maagprikkelende">maagprikkelende</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="calciumzout">calciumzout</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.14" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.15" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.16" pos="N(soort,ev,basis,zijd,stan)" lemma="markt">markt</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.17" pos="WW(vd,vrij,zonder)" lemma="brengen">gebracht</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.18" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.19" pos="N(soort,ev,basis,zijd,stan)" lemma="ascal">ascal</w>
            <w xml:id="WR-P-E-J-0000125009.p.2.s.4.w.20" pos="LET()" lemma=")">)</w>
          </s>
        </p>
        <p xml:id="WR-P-E-J-0000125009.p.3">
          <s xml:id="WR-P-E-J-0000125009.p.3.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.1" pos="LID(bep,stan,rest)" lemma="de">De</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="werking">werking</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.3" pos="BW()" lemma="zelf">zelf</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.4" pos="WW(pv,tgw,ev)" lemma="berusten">berust</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.5" pos="BW()" lemma="erop">erop</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.6" pos="VG(onder)" lemma="dat">dat</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.7" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">Aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.8" pos="ADJ(vrij,basis,zonder)" lemma="irreversibel">irreversibel</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.9" pos="WW(pv,tgw,met-t)" lemma="binden">bindt</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.10" pos="VZ(init)" lemma="aan">aan</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.11" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.12" pos="N(soort,ev,basis,onz,stan)" lemma="enzym">enzym</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="cyclo-oxygenase">cyclo-oxygenase</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.14" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.15" pos="N(soort,ev,basis,zijd,stan)" lemma="cox">COX</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.16" pos="LET()" lemma=")">)</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.17" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.18" pos="BW()" lemma="waardoor">waardoor</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.19" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dit">dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.20" pos="BW()" lemma="niet">niet</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.21" pos="VNW(onbep,grad,stan,vrij,zonder,comp)" lemma="veel">meer</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.22" pos="WW(pv,tgw,ev)" lemma="kunnen">kan</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.23" pos="WW(inf,vrij,zonder)" lemma="helpen">helpen</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.24" pos="N(soort,ev,basis,zijd,stan)" lemma="arachidonzuur">arachidonzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.25" pos="VZ(init)" lemma="om">om</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.26" pos="VZ(init)" lemma="te">te</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.27" pos="WW(inf,vrij,zonder)" lemma="zetten">zetten</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.28" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.29" pos="N(soort,mv,basis)" lemma="prostaglandine">prostaglandines</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.30" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.31" pos="N(soort,mv,basis)" lemma="stof">stoffen</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.32" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.33" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.34" pos="N(soort,mv,basis)" lemma="zenuwuiteinde">zenuwuiteinden</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.35" pos="ADJ(vrij,basis,zonder)" lemma="gevoelig">gevoelig</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.36" pos="WW(pv,tgw,mv)" lemma="maken">maken</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.37" pos="VZ(init)" lemma="voor">voor</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.38" pos="N(soort,mv,basis)" lemma="prikkel">prikkels</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.1.w.39" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.3.s.2">
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.1" pos="LID(bep,stan,rest)" lemma="de">De</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.2" pos="WW(vd,prenom,met-e)" lemma="vermelden">vermelde</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.3" pos="N(soort,mv,basis)" lemma="maagprobleem">maagproblemen</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.4" pos="WW(pv,tgw,mv)" lemma="ontstaan">ontstaan</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.5" pos="VZ(init)" lemma="door">door</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.6" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.7" pos="ADJ(prenom,basis,met-e,stan)" lemma="irreversibel">irreversibele</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="binding">binding</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.9" pos="VZ(init)" lemma="aan">aan</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.10" pos="N(eigen,ev,basis,zijd,stan)" lemma="Cox-1">COX-1</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.11" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.12" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="variant">variant</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.14" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.15" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.16" pos="N(soort,ev,basis,onz,stan)" lemma="enzym">enzym</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.17" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.18" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.19" pos="N(soort,ev,basis,zijd,stan)" lemma="rolspeelt">rolspeelt</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.20" pos="VZ(init)" lemma="bij">bij</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.21" pos="N(soort,ev,basis,zijd,stan)" lemma="bescherming">bescherming</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.22" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.23" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.24" pos="N(soort,ev,basis,zijd,stan)" lemma="maag">maag</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.25" pos="VZ(init)" lemma="tegen">tegen</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.26" pos="VNW(bez,det,stan,vol,3,ev,prenom,zonder,agr)" lemma="zijn">zijn</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.27" pos="ADJ(prenom,basis,zonder)" lemma="eigen">eigen</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.28" pos="ADJ(prenom,basis,met-e,stan)" lemma="zuur">zure</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.29" pos="N(soort,ev,basis,zijd,stan)" lemma="inhoud">inhoud</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.2.w.30" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.3.s.3">
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.1" pos="BW()" lemma="ook">Ook</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.2" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.3" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dit">dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.4" pos="N(eigen,ev,basis,zijd,stan)" lemma="Cox-1">COX-1</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.5" pos="ADJ(vrij,basis,zonder)" lemma="aanwezig">aanwezig</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.6" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.7" pos="N(soort,mv,basis)" lemma="bloedplaatjes">bloedplaatjes</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.8" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.9" pos="BW()" lemma="vandaar">vandaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.10" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.11" pos="ADJ(prenom,basis,met-e,stan)" lemma="trombocytenaggregatieremmende">trombocytenaggregatieremmende</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.12" pos="N(soort,ev,basis,zijd,stan)" lemma="werking">werking</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.3.w.13" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.3.s.4">
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.1" pos="BW()" lemma="vandaar">Vandaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.2" pos="VG(onder)" lemma="dat">dat</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.3" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.4" pos="ADJ(prenom,basis,met-e,stan)" lemma="farmaceutisch">farmaceutische</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.5" pos="N(soort,ev,basis,zijd,stan)" lemma="industrie">industrie</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.6" pos="VNW(refl,pron,obl,red,3,getal)" lemma="zich">zich</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.7" pos="WW(pv,tgw,ev)" lemma="richten">richt</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.8" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.9" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.10" pos="N(soort,ev,basis,zijd,stan)" lemma="ontwikkeling">ontwikkeling</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.11" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.12" pos="N(eigen,ev,basis,zijd,stan)" lemma="Cox-2">COX-2</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.13" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.14" pos="N(soort,ev,basis,zijd,stan)" lemma="induceerbaar">induceerbaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.15" pos="N(soort,ev,basis,zijd,stan)" lemma="cox">COX</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.16" pos="LET()" lemma=")">)</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.17" pos="ADJ(prenom,basis,met-e,stan)" lemma="specifiek">specifieke</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.18" pos="N(soort,mv,basis)" lemma="pijnstiller">pijnstillers</w>
            <w xml:id="WR-P-E-J-0000125009.p.3.s.4.w.19" pos="LET()" lemma=".">.</w>
          </s>
        </p>
      </div>
      <div xml:id="WR-P-E-J-0000125009.div.2">
        <head xml:id="WR-P-E-J-0000125009.head.2">
          <s xml:id="WR-P-E-J-0000125009.head.2.s.1">
            <w xml:id="WR-P-E-J-0000125009.head.2.s.1.w.1" pos="N(soort,ev,basis,zijd,stan)" lemma="geschiedenis">Geschiedenis</w>
            <w xml:id="WR-P-E-J-0000125009.head.2.s.1.w.2" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.head.2.s.1.w.3" pos="N(eigen,ev,basis,zijd,stan)" lemma="Aspirine">Aspirine</w>
          </s>
        </head>
        <p xml:id="WR-P-E-J-0000125009.p.4">
          <s xml:id="WR-P-E-J-0000125009.p.4.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.1" pos="LID(bep,stan,rest)" lemma="de">De</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="ontdekking">ontdekking</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.3" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.4" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.5" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.6" pos="ADJ(prenom,basis,zonder)" lemma="algemeen">algemeen</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.7" pos="WW(vd,vrij,zonder)" lemma="toeschrijven">toegeschreven</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.8" pos="VZ(init)" lemma="aan">aan</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.9" pos="SPEC(deeleigen)" lemma="_">Felix</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.10" pos="SPEC(deeleigen)" lemma="_">Hoffmann</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.11" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.12" pos="ADJ(vrij,basis,zonder)" lemma="werkzaam">werkzaam</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.13" pos="VZ(init)" lemma="bij">bij</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.14" pos="N(eigen,ev,basis,zijd,stan)" lemma="Bayer">Bayer</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.15" pos="VZ(init)" lemma="te">te</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.16" pos="N(soort,ev,basis,onz,stan)" lemma="elberfeld">Elberfeld</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.1.w.17" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.2">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.1" pos="VZ(init)" lemma="uit">Uit</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.2" pos="N(soort,ev,basis,onz,stan)" lemma="onderzoek">onderzoek</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.3" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.4" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.5" pos="N(soort,mv,basis)" lemma="labjournaal">labjournaals</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.6" pos="VZ(init)" lemma="bij">bij</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.7" pos="N(eigen,ev,basis,zijd,stan)" lemma="Bayer">Bayer</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.8" pos="WW(pv,tgw,met-t)" lemma="blijken">blijkt</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.9" pos="BW()" lemma="echter">echter</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.10" pos="VG(onder)" lemma="dat">dat</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.11" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.12" pos="ADJ(prenom,basis,met-e,stan)" lemma="werkelijk">werkelijke</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="ontdekker">ontdekker</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.14" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.15" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.16" pos="SPEC(deeleigen)" lemma="_">Arthur</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.17" pos="SPEC(deeleigen)" lemma="_">Eichengrün</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.18" pos="WW(pv,verl,ev)" lemma="zijn">was</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.19" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.20" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.21" pos="N(soort,ev,basis,onz,stan)" lemma="onderzoek">onderzoek</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.22" pos="WW(pv,verl,ev)" lemma="doen">deed</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.23" pos="VZ(init)" lemma="naar">naar</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.24" pos="ADJ(prenom,comp,met-e,stan)" lemma="goed">betere</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.25" pos="N(soort,mv,basis)" lemma="pijnstiller">pijnstillers</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.2.w.26" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.3">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.3.w.1" pos="SPEC(deeleigen)" lemma="_">Felix</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.3.w.2" pos="SPEC(deeleigen)" lemma="_">Hoffmann</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.3.w.3" pos="WW(pv,verl,ev)" lemma="werken">werkte</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.3.w.4" pos="VZ(init)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.3.w.5" pos="N(soort,ev,basis,zijd,stan)" lemma="laboratorium-assistent">laboratorium-assistent</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.3.w.6" pos="VZ(init)" lemma="onder">onder</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.3.w.7" pos="WW(pv,tgw,mv)" lemma="zijn">zijn</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.3.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="leiding">leiding</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.3.w.9" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.4">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.1" pos="VZ(init)" lemma="door">Door</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.2" pos="VNW(bez,det,stan,vol,3,ev,prenom,zonder,agr)" lemma="zijn">zijn</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.3" pos="ADJ(prenom,basis,met-e,stan)" lemma="joods">joodse</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.4" pos="N(soort,ev,basis,zijd,stan)" lemma="achtergrond">achtergrond</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.5" pos="WW(pv,verl,ev)" lemma="worden">werd</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.6" pos="N(soort,mv,basis)" lemma="eichengrün">Eichengrün</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.7" pos="VZ(init)" lemma="door">door</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.8" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.9" pos="N(soort,ev,basis,zijd,stan)" lemma="nazis">Nazis</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.10" pos="VZ(init)" lemma="uit">uit</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.11" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.12" pos="N(soort,mv,basis)" lemma="annalen">annalen</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.13" pos="WW(vd,vrij,zonder)" lemma="schrappen">geschrapt</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.14" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.15" pos="WW(pv,verl,ev)" lemma="worden">werd</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.16" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.17" pos="N(soort,ev,basis,onz,stan)" lemma="verhaal">verhaal</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.18" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.19" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.20" pos="ADJ(prenom,basis,zonder)" lemma="rheumatisch">rheumatisch</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.21" pos="N(soort,ev,basis,zijd,stan)" lemma="vader">vader</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.22" pos="WW(vd,vrij,zonder)" lemma="bedenken">bedacht</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.4.w.23" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.5">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.1" pos="VZ(init)" lemma="in">In</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.2" pos="TW(hoofd,vrij)" lemma="1949">1949</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.3" pos="WW(pv,verl,ev)" lemma="publiceren">publiceerde</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.4" pos="N(soort,mv,basis)" lemma="eigengrün">Eigengrün</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.5" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.6" pos="N(soort,ev,basis,onz,stan)" lemma="artikel">artikel</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.7" pos="BW()" lemma="waarin">waarin</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.8" pos="VNW(pers,pron,nomin,vol,3,ev,masc)" lemma="hij">hij</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.9" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.10" pos="N(soort,ev,basis,zijd,stan)" lemma="uitvinding">uitvinding</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.11" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.12" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="claimde">claimde</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.5.w.14" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.6">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.1" pos="VNW(aanw,det,stan,prenom,met-e,rest)" lemma="deze">Deze</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="claim">claim</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.3" pos="WW(pv,verl,ev)" lemma="worden">werd</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.4" pos="WW(vd,vrij,zonder)" lemma="bevestigen">bevestigd</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.5" pos="VZ(init)" lemma="na">na</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.6" pos="N(soort,ev,basis,onz,stan)" lemma="onderzoek">onderzoek</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.7" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.8" pos="SPEC(deeleigen)" lemma="_">Walter</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.9" pos="SPEC(deeleigen)" lemma="_">Sneader</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.10" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.11" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.12" pos="N(soort,ev,basis,zijd,stan)" lemma="universiteit">universiteit</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.13" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.14" pos="N(eigen,ev,basis,zijd,stan)" lemma="Glasgow">Glasgow</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.15" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.16" pos="TW(hoofd,vrij)" lemma="1999">1999</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.6.w.17" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.7">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.1" pos="N(soort,mv,basis)" lemma="salicylzuur">Salicylzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.2" pos="WW(pv,verl,ev)" lemma="worden">werd</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.3" pos="BW()" lemma="al">al</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.4" pos="WW(vd,vrij,zonder)" lemma="gebruiken">gebruikt</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.5" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.6" pos="BW()" lemma="zelfs">zelfs</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.7" pos="N(eigen,ev,basis,zijd,stan)" lemma="Hippocrates">Hippocrates</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.8" pos="WW(pv,verl,ev)" lemma="kennen">kende</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.9" pos="VNW(aanw,adv-pron,stan,red,3,getal)" lemma="er">er</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.10" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.11" pos="N(soort,ev,basis,zijd,stan)" lemma="werking">werking</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.12" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.13" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.14" pos="VG(neven)" lemma="maar">maar</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.15" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.16" pos="WW(pv,verl,ev)" lemma="zijn">was</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.17" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.18" pos="ADJ(prenom,basis,zonder)" lemma="walgelijk">walgelijk</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.19" pos="N(soort,ev,dim,onz,stan)" lemma="goed">goedje</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.20" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dat">dat</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.21" pos="ADJ(vrij,basis,zonder)" lemma="erg">erg</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.22" pos="ADJ(vrij,basis,zonder)" lemma="slecht">slecht</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.23" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.24" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.25" pos="N(soort,ev,basis,zijd,stan)" lemma="maag">maag</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.26" pos="WW(pv,verl,ev)" lemma="liggen">lag</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.7.w.27" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.8">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.1" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dit">Dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="zuur">zuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.3" pos="WW(pv,verl,ev)" lemma="worden">werd</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.4" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.5" pos="TW(rang,prenom,stan)" lemma="eerste">eerste</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="instantie">instantie</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.7" pos="ADJ(vrij,basis,zonder)" lemma="geëxtraheerd">geëxtraheerd</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.8" pos="VZ(init)" lemma="uit">uit</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.9" pos="N(soort,ev,basis,zijd,stan)" lemma="bast">bast</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.10" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.11" pos="N(soort,mv,basis)" lemma="lid">leden</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.12" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.13" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.14" pos="N(soort,ev,basis,zijd,stan)" lemma="plantenfamilie">plantenfamilie</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.15" pos="LID(bep,gen,rest3)" lemma="de">der</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.16" pos="N(soort,mv,basis)" lemma="wilg">wilgen</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.17" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.18" pos="ADJ(prenom,basis,met-e,stan)" lemma="Latijns">Latijnse</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.19" pos="N(soort,ev,basis,zijd,stan)" lemma="gelachtsnaam">gelachtsnaam</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.20" pos="N(soort,ev,basis,onz,stan)" lemma="salix">Salix</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.21" pos="LET()" lemma=")">)</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.22" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.23" pos="BW()" lemma="vandaar">vandaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.24" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.25" pos="N(soort,ev,basis,zijd,stan)" lemma="naam">naam</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.26" pos="N(soort,ev,basis,onz,stan)" lemma="salicylzuur">salicylzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.8.w.27" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.9">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.1" pos="ADJ(vrij,basis,zonder)" lemma="Hetzelfde">Hetzelfde</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="zuur">zuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.3" pos="WW(pv,verl,ev)" lemma="zijn">was</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.4" pos="VZ(init)" lemma="te">te</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.5" pos="WW(inf,vrij,zonder)" lemma="vinden">vinden</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.6" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.7" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="moerasspirea">Moerasspirea</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.9" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.10" pos="BW()" lemma="vandaar">vandaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.11" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.12" pos="LET()" lemma="'">'</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="spir">spir</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.14" pos="LET()" lemma="'">'</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.15" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.16" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.9.w.17" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.10">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.1" pos="N(eigen,ev,basis,zijd,stan)" lemma="Hoffmann">Hoffmann</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.2" pos="WW(pv,verl,ev)" lemma="gaan">ging</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.3" pos="ADJ(vrij,basis,zonder)" lemma="systematisch">systematisch</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.4" pos="VZ(init)" lemma="te">te</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.5" pos="N(soort,ev,basis,onz,stan)" lemma="werk">werk</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.6" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.7" pos="WW(pv,verl,ev)" lemma="zoeken">zocht</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.8" pos="ADJ(vrij,basis,zonder)" lemma="hardnekkig">hardnekkig</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.9" pos="VZ(init)" lemma="naar">naar</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.10" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.11" pos="ADJ(prenom,basis,met-e,stan)" lemma="nieuw">nieuwe</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.12" pos="N(soort,ev,basis,zijd,stan)" lemma="verbinding">verbinding</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.13" pos="VZ(init)" lemma="om">om</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.14" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.15" pos="N(soort,ev,basis,onz,stan)" lemma="middel">middel</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.16" pos="ADJ(vrij,comp,zonder)" lemma="goed">beter</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.17" pos="ADJ(vrij,basis,zonder)" lemma="verteerbaar">verteerbaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.18" pos="VZ(init)" lemma="te">te</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.19" pos="WW(inf,vrij,zonder)" lemma="maken">maken</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.10.w.20" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.11">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.1" pos="VZ(init)" lemma="volgens">Volgens</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.2" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.3" pos="N(soort,ev,basis,onz,stan)" lemma="principe">principe</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.4" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.5" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="veredeling">veredeling</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.7" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.8" pos="WW(od,prenom,met-e)" lemma="bestaan">bestaande</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.9" pos="N(soort,mv,basis)" lemma="geneesmiddel">geneesmiddelen</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.10" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.11" pos="BW()" lemma="waarmee">waarmee</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.12" pos="VNW(pers,pron,nomin,vol,3,ev,masc)" lemma="hij">hij</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.13" pos="BW()" lemma="al">al</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.14" pos="BW()" lemma="eerder">eerder</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.15" pos="N(soort,ev,basis,onz,stan)" lemma="succes">succes</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.16" pos="WW(pv,tgw,met-t)" lemma="hebben">heeft</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.17" pos="WW(vd,vrij,zonder)" lemma="boeken">geboekt</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.18" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.19" pos="WW(pv,tgw,met-t)" lemma="ontdekken">ontdekt</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.20" pos="VNW(pers,pron,nomin,vol,3,ev,masc)" lemma="hij">hij</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.21" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.22" pos="TW(hoofd,vrij)" lemma="1897">1897</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.23" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.24" pos="N(soort,ev,basis,zijd,stan)" lemma="oplossing">oplossing</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.25" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.26" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.27" pos="N(soort,ev,basis,onz,stan)" lemma="probleem">probleem</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.28" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.29" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.30" pos="N(soort,ev,basis,zijd,stan)" lemma="acetylering">acetylering</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.31" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.32" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.33" pos="N(soort,ev,basis,onz,stan)" lemma="salicylzuur">salicylzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.11.w.34" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.12">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.1" pos="VZ(init)" lemma="op">Op</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.2" pos="TW(hoofd,vrij)" lemma="10">10</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.3" pos="N(eigen,ev,basis,zijd,stan)" lemma="augustus">augustus</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.4" pos="WW(pv,tgw,met-t)" lemma="beschrijven">beschrijft</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.5" pos="VNW(pers,pron,nomin,vol,3,ev,masc)" lemma="hij">hij</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.6" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.7" pos="WW(pv,tgw,mv)" lemma="zijn">zijn</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="laboratoriumdagboek">laboratoriumdagboek</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.9" pos="BW()" lemma="hoe">hoe</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.10" pos="VNW(pers,pron,nomin,vol,3,ev,masc)" lemma="hij">hij</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.11" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.12" pos="N(soort,ev,basis,onz,stan)" lemma="acetylsalicylzuur">acetylsalicylzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.13" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.14" pos="ADJ(vrij,basis,zonder)" lemma="chemisch">chemisch</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.15" pos="ADJ(prenom,basis,met-e,stan)" lemma="zuiver">zuivere</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.16" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.17" pos="ADJ(prenom,basis,met-e,stan)" lemma="bewaarbaar">bewaarbare</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.18" pos="N(soort,ev,basis,zijd,stan)" lemma="vorm">vorm</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.19" pos="WW(pv,tgw,met-t)" lemma="hebben">heeft</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.20" pos="WW(vd,vrij,zonder)" lemma="samengesteld">samengesteld</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.12.w.21" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.13">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.1" pos="VG(onder)" lemma="nadat">Nadat</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.2" pos="VNW(pers,pron,nomin,vol,3,ev,masc)" lemma="hij">hij</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.3" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.4" pos="ADJ(prenom,basis,met-e,stan)" lemma="nieuw">nieuwe</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.5" pos="N(soort,ev,basis,zijd,stan)" lemma="stof">stof</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.6" pos="BW()" lemma="samen">samen</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.7" pos="VZ(init)" lemma="met">met</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="dokter">dokter</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.9" pos="SPEC(deeleigen)" lemma="_">Heinrich</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.10" pos="SPEC(deeleigen)" lemma="_">Dreser</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.11" pos="ADJ(vrij,basis,zonder)" lemma="uitbreiden">uitgebreid</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.12" pos="WW(vd,vrij,zonder)" lemma="testen">getest</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.13" pos="WW(pv,tgw,met-t)" lemma="hebben">heeft</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.14" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.15" pos="N(soort,mv,basis)" lemma="dier">dieren</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.16" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.17" pos="WW(pv,tgw,met-t)" lemma="komen">komt</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.18" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.19" pos="N(soort,ev,basis,zijd,stan)" lemma="stof">stof</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.20" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.21" pos="TW(hoofd,vrij)" lemma="1899">1899</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.22" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.23" pos="N(soort,ev,basis,zijd,stan)" lemma="poedervorm">poedervorm</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.24" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.25" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.26" pos="N(soort,ev,basis,zijd,stan)" lemma="markt">markt</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.13.w.27" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.14">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.14.w.1" pos="LID(onbep,stan,agr)" lemma="een">Een</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.14.w.2" pos="N(soort,ev,basis,onz,stan)" lemma="jaar">jaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.14.w.3" pos="ADJ(vrij,comp,zonder)" lemma="laat">later</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.14.w.4" pos="WW(pv,tgw,mv)" lemma="zijn">zijn</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.14.w.5" pos="VNW(aanw,adv-pron,stan,red,3,getal)" lemma="er">er</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.14.w.6" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.14.w.7" pos="ADJ(prenom,basis,met-e,stan)" lemma="gedoseerde">gedoseerde</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.14.w.8" pos="N(soort,mv,basis)" lemma="tablet">tabletten</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.14.w.9" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.4.s.15">
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.1" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">Het</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.2" pos="N(soort,ev,basis,onz,stan)" lemma="wereldverbruik">wereldverbruik</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.3" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.4" pos="BW()" lemma="vandaag">vandaag</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.5" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.6" pos="N(soort,mv,basis)" lemma="dag">dag</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.7" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.8" pos="ADJ(vrij,basis,zonder)" lemma="vijftigduizend">vijftigduizend</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.9" pos="N(soort,ev,basis,zijd,stan)" lemma="ton">ton</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.10" pos="VG(neven)" lemma="of">of</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.11" pos="BW()" lemma="ongeveer">ongeveer</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.12" pos="TW(hoofd,prenom,stan)" lemma="honderd">honderd</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.13" pos="N(soort,ev,basis,onz,stan)" lemma="miljard">miljard</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.14" pos="N(soort,mv,basis)" lemma="tablet">tabletten</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.15" pos="VZ(init)" lemma="per">per</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.16" pos="N(soort,ev,basis,onz,stan)" lemma="jaar">jaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.17" pos="WW(vd,vrij,zonder)" lemma="schatten">geschat</w>
            <w xml:id="WR-P-E-J-0000125009.p.4.s.15.w.18" pos="LET()" lemma=".">.</w>
          </s>
        </p>
      </div>
      <div xml:id="WR-P-E-J-0000125009.div.3">
        <head xml:id="WR-P-E-J-0000125009.head.3">
          <s xml:id="WR-P-E-J-0000125009.head.3.s.1">
            <w xml:id="WR-P-E-J-0000125009.head.3.s.1.w.1" pos="N(soort,ev,basis,zijd,stan)" lemma="geschiedenis">Geschiedenis</w>
            <w xml:id="WR-P-E-J-0000125009.head.3.s.1.w.2" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.head.3.s.1.w.3" pos="N(soort,ev,basis,zijd,stan)" lemma="aspro">Aspro</w>
          </s>
        </head>
        <p xml:id="WR-P-E-J-0000125009.p.5">
          <s xml:id="WR-P-E-J-0000125009.p.5.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.1" pos="VZ(init)" lemma="tijdens">Tijdens</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.2" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.3" pos="ADJ(prenom,basis,met-e,stan)" lemma="1ste">1ste</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.4" pos="N(soort,ev,basis,zijd,stan)" lemma="wereldoorlog">Wereldoorlog</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.5" pos="WW(pv,verl,ev)" lemma="loven">loofde</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.6" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.7" pos="ADJ(prenom,basis,met-e,stan)" lemma="Brits">Britse</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="regering">regering</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.9" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.10" pos="N(soort,ev,basis,zijd,stan)" lemma="prijs">prijs</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.11" pos="VZ(fin)" lemma="uit">uit</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.12" pos="VZ(init)" lemma="voor">voor</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="eenieder">eenieder</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.14" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.15" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.16" pos="ADJ(prenom,basis,met-e,stan)" lemma="nieuw">nieuwe</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.17" pos="N(soort,ev,basis,zijd,stan)" lemma="formule">formule</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.18" pos="WW(pv,verl,ev)" lemma="kunnen">kon</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.19" pos="WW(inf,vrij,zonder)" lemma="vinden">vinden</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.20" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.21" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.22" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.23" pos="VZ(init)" lemma="gezien">gezien</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.24" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.25" pos="N(soort,ev,basis,onz,stan)" lemma="feit">feit</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.26" pos="VG(onder)" lemma="dat">dat</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.27" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.28" pos="N(soort,ev,basis,zijd,stan)" lemma="invoer">invoer</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.29" pos="VZ(init)" lemma="uit">uit</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.30" pos="N(eigen,ev,basis,onz,stan)" lemma="Duitsland">Duitsland</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.31" pos="ADJ(vrij,basis,zonder)" lemma="stil">stil</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.32" pos="WW(pv,verl,ev)" lemma="liggen">lag</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.1.w.33" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.5.s.2">
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.1" pos="LID(onbep,stan,agr)" lemma="een">Een</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="chemicus">chemicus</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.3" pos="VZ(init)" lemma="uit">uit</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.4" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.5" pos="ADJ(prenom,basis,met-e,stan)" lemma="Australisch">Australische</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="melbourne">Melbourne</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.7" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.8" pos="SPEC(deeleigen)" lemma="_">George</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.9" pos="SPEC(deeleigen)" lemma="_">Nicholas</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.10" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.11" pos="WW(pv,verl,ev)" lemma="ontdekken">ontdekte</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.12" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.13" pos="TW(hoofd,vrij)" lemma="1915">1915</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.14" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.15" pos="ADJ(prenom,basis,met-e,stan)" lemma="synthetisch">synthetische</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.16" pos="N(soort,ev,basis,zijd,stan)" lemma="oplossing">oplossing</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.17" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.18" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.19" pos="BW()" lemma="zelfs">zelfs</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.20" pos="ADJ(vrij,comp,zonder)" lemma="zuiver">zuiverder</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.21" pos="WW(pv,verl,ev)" lemma="zijn">was</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.22" pos="BW()" lemma="dan">dan</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.23" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.24" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.25" pos="ADJ(prenom,basis,zonder)" lemma="oplosbaar">oplosbaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.26" pos="WW(pv,verl,ev)" lemma="zijn">was</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.2.w.27" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.5.s.3">
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.1" pos="VNW(pers,pron,nomin,vol,3,ev,masc)" lemma="hij">Hij</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.2" pos="WW(pv,verl,ev)" lemma="noemen">noemde</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.3" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dit">dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.4" pos="SPEC(deeleigen)" lemma="_">Aspro</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.5" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.6" pos="VNW(vb,pron,stan,vol,3o,ev)" lemma="wat">wat</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.7" pos="ADJ(vrij,comp,zonder)" lemma="laat">later</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.8" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.9" pos="ADJ(prenom,basis,met-e,stan)" lemma="geheel">gehele</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.10" pos="N(soort,ev,basis,zijd,stan)" lemma="wereld">wereld</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.11" pos="WW(pv,verl,ev)" lemma="veroveren">veroverde</w>
            <w xml:id="WR-P-E-J-0000125009.p.5.s.3.w.12" pos="LET()" lemma=".">.</w>
          </s>
        </p>
      </div>
      <div xml:id="WR-P-E-J-0000125009.div.4">
        <head xml:id="WR-P-E-J-0000125009.head.4">
          <s xml:id="WR-P-E-J-0000125009.head.4.s.1">
            <w xml:id="WR-P-E-J-0000125009.head.4.s.1.w.1" pos="ADJ(prenom,basis,met-e,stan)" lemma="Pijnstillende">Pijnstillende</w>
            <w xml:id="WR-P-E-J-0000125009.head.4.s.1.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="werking">werking</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.head.4.s.2">
            <w xml:id="WR-P-E-J-0000125009.head.4.s.2.w.1" pos="N(eigen,ev,basis,zijd,stan)" lemma="Aspirine">Aspirine</w>
          </s>
        </head>
        <p xml:id="WR-P-E-J-0000125009.p.6">
          <s xml:id="WR-P-E-J-0000125009.p.6.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.1.w.1" pos="N(soort,ev,basis,zijd,stan)" lemma="pijn">Pijn</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.1.w.2" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.1.w.3" pos="WW(pv,tgw,met-t)" lemma="veroorzaken">veroorzaakt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.1.w.4" pos="VZ(init)" lemma="door">door</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.1.w.5" pos="ADJ(prenom,basis,met-e,stan)" lemma="verschillend">verschillende</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.1.w.6" pos="N(soort,mv,basis)" lemma="stof">stoffen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.1.w.7" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.1.w.8" pos="N(soort,mv,basis)" lemma="vrijkomen">vrijkomen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.1.w.9" pos="VZ(init)" lemma="bij">bij</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.1.w.10" pos="N(soort,mv,basis)" lemma="beschadiging">beschadigingen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.1.w.11" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.2">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.1" pos="ADJ(prenom,basis,met-e,stan)" lemma="Werkende">Werkende</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.2" pos="N(soort,mv,basis)" lemma="cel">cellen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.3" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.4" pos="WW(vd,prenom,zonder)" lemma="beschadigen">beschadigd</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.5" pos="N(soort,ev,basis,onz,stan)" lemma="weefsel">weefsel</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.6" pos="WW(pv,tgw,mv)" lemma="geven">geven</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.7" pos="VNW(aanw,det,stan,prenom,zonder,rest)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.8" pos="N(soort,mv,basis)" lemma="stof">stoffen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.9" pos="VZ(fin)" lemma="af">af</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.10" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.11" pos="VZ(init)" lemma="onder">onder</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.12" pos="N(soort,ev,basis,zijd,stan)" lemma="invloed">invloed</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.13" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.14" pos="BW()" lemma="o.a.">o.a.</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.15" pos="N(soort,mv,basis)" lemma="cytokine">cytokinen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.16" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.17" pos="N(soort,mv,basis)" lemma="mitogeen">mitogenen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.2.w.18" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.3">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.1" pos="VNW(aanw,det,stan,prenom,met-e,rest)" lemma="deze">Deze</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.2" pos="N(soort,mv,basis)" lemma="stof">stoffen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.3" pos="WW(pv,tgw,mv)" lemma="werken">werken</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.4" pos="BW()" lemma="dan">dan</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.5" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.6" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.7" pos="N(soort,mv,basis)" lemma="zenuwuiteinde">zenuwuiteinden</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.8" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.9" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.10" pos="N(soort,ev,basis,onz,stan)" lemma="pijnsignaal">pijnsignaal</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.11" pos="VZ(init)" lemma="naar">naar</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.12" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.13" pos="N(soort,mv,basis)" lemma="hersenen">hersenen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.14" pos="WW(inf,vrij,zonder)" lemma="doorsturen">doorsturen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.3.w.15" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.4">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.1" pos="LID(onbep,stan,agr)" lemma="een">Een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.2" pos="N(soort,ev,basis,onz,stan)" lemma="hormoon">hormoon</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.3" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.4" pos="VG(onder)" lemma="dat">dat</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.5" pos="BW()" lemma="daarin">daarin</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.6" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.7" pos="ADJ(prenom,basis,met-e,stan)" lemma="belangrijk">belangrijke</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="rol">rol</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.9" pos="WW(pv,tgw,met-t)" lemma="spelen">speelt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.10" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.11" pos="N(soort,ev,basis,zijd,stan)" lemma="prostaglandine">prostaglandine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.4.w.12" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.5">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.1" pos="N(soort,ev,basis,zijd,stan)" lemma="prostaglandine">Prostaglandine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.2" pos="WW(pv,tgw,met-t)" lemma="geven">geeft</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.3" pos="BW()" lemma="niet">niet</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.4" pos="BW()" lemma="alleen">alleen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.5" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="pijnsignaal">pijnsignaal</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.7" pos="VZ(fin)" lemma="af">af</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.8" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.9" pos="VG(neven)" lemma="maar">maar</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.10" pos="WW(pv,tgw,met-t)" lemma="spelen">speelt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.11" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.12" pos="ADJ(prenom,basis,met-e,stan)" lemma="belangrijk">belangrijke</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="rol">rol</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.14" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.15" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.16" pos="ADJ(prenom,basis,met-e,stan)" lemma="heel">hele</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.17" pos="N(soort,ev,basis,onz,stan)" lemma="lichaam">lichaam</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.5.w.18" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.6">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.6.w.1" pos="BW()" lemma="daarom">Daarom</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.6.w.2" pos="BW()" lemma="eerst">eerst</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.6.w.3" pos="VNW(onbep,pron,stan,vol,3o,ev)" lemma="wat">wat</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.6.w.4" pos="VNW(onbep,grad,stan,vrij,zonder,comp)" lemma="veel">meer</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.6.w.5" pos="VZ(init)" lemma="over">over</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.6.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="prostaglandine">Prostaglandine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.6.w.7" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.7">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.1" pos="N(soort,ev,basis,zijd,stan)" lemma="prostaglandine">Prostaglandine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.2" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.3" pos="WW(vd,vrij,zonder)" lemma="produceren">geproduceerd</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.4" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.5" pos="N(soort,mv,basis)" lemma="cel">cellen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.6" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.7" pos="WW(pv,tgw,met-t)" lemma="werken">werkt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.8" pos="BW()" lemma="alleen">alleen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.9" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.10" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.11" pos="N(soort,ev,basis,zijd,stan)" lemma="buurt">buurt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.12" pos="VNW(vb,adv-pron,obl,vol,3o,getal)" lemma="waar">waar</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.13" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.14" pos="WW(vd,vrij,zonder)" lemma="produceren">geproduceerd</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.15" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.16" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.17" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.18" pos="BW()" lemma="dan">dan</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.19" pos="WW(vd,vrij,zonder)" lemma="afbreken">afgebroken</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.7.w.20" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.8">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.1" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">Het</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.2" pos="WW(pv,tgw,met-t)" lemma="stimuleren">stimuleert</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.3" pos="VZ(init)" lemma="naast">naast</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.4" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.5" pos="N(soort,ev,basis,zijd,stan)" lemma="pijnreactie">pijnreactie</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.6" pos="BW()" lemma="ook">ook</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.7" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="ontstekingsreactie">ontstekingsreactie</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.9" pos="VG(onder)" lemma="wanneer">wanneer</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.10" pos="VNW(aanw,adv-pron,stan,red,3,getal)" lemma="er">er</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.11" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.12" pos="N(soort,ev,basis,zijd,stan)" lemma="infectie">infectie</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.13" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.14" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.15" pos="WW(pv,tgw,met-t)" lemma="zorgen">zorgt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.16" pos="VZ(init)" lemma="voor">voor</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.17" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.18" pos="N(soort,ev,basis,zijd,stan)" lemma="verhoging">verhoging</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.19" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.20" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.21" pos="N(soort,ev,basis,zijd,stan)" lemma="lichaamstemperatuur">lichaamstemperatuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.8.w.22" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.9">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.1" pos="VZ(init)" lemma="in">In</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.2" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.3" pos="N(soort,mv,basis)" lemma="cel">cellen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.4" pos="WW(pv,tgw,met-t)" lemma="spelen">speelt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.5" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="cyclooxygenase">cyclooxygenase</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.7" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="cox">COX</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.9" pos="LET()" lemma=")">)</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.10" pos="N(soort,ev,basis,zijd,stan)" lemma="enzym">enzym</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.11" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.12" pos="ADJ(prenom,basis,met-e,stan)" lemma="onmisbaar">onmisbare</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="rol">rol</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.14" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.15" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.16" pos="WW(inf,nom,zonder,zonder-n)" lemma="maken">maken</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.17" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.18" pos="N(soort,ev,basis,zijd,stan)" lemma="prostaglandine">prostaglandine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.9.w.19" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.10">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.1" pos="N(soort,ev,basis,zijd,stan)" lemma="cyclooxygenase">Cyclooxygenase</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.2" pos="WW(pv,tgw,met-t)" lemma="katalyseren">katalyseert</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.3" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.4" pos="N(soort,ev,basis,zijd,stan)" lemma="omzetting">omzetting</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.5" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="arachidonzuur">arachidonzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.7" pos="VZ(init)" lemma="naar">naar</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="prostaglandine">prostaglandine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.9" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.10" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.11" pos="N(soort,ev,basis,zijd,stan)" lemma="reactie">reactie</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.12" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.13" pos="BW()" lemma="ander">anders</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.14" pos="BW()" lemma="vrijwel">vrijwel</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.15" pos="BW()" lemma="niet">niet</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.16" pos="WW(pv,tgw,met-t)" lemma="verlopen">verloopt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.10.w.17" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.11">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.1" pos="LID(bep,stan,rest)" lemma="de">De</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.3" pos="WW(pv,tgw,met-t)" lemma="voorkomen">voorkomt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.4" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.5" pos="N(soort,ev,basis,zijd,stan)" lemma="werking">werking</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.6" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.7" pos="N(eigen,ev,basis,onz,stan)" lemma="Cyclooxygenase">Cyclooxygenase</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.8" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.9" pos="WW(pv,tgw,met-t)" lemma="voorkomen">voorkomt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.10" pos="BW()" lemma="daarmee">daarmee</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.11" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.12" pos="N(soort,ev,basis,zijd,stan)" lemma="vorming">vorming</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.13" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.14" pos="N(soort,ev,basis,zijd,stan)" lemma="prostaglandine">prostaglandine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.15" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.16" pos="BW()" lemma="waardoor">waardoor</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.17" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.18" pos="ADJ(prenom,basis,zonder)" lemma="groot">groot</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.19" pos="N(soort,ev,basis,onz,stan)" lemma="gedeelte">gedeelte</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.20" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.21" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.22" pos="N(soort,ev,basis,zijd,stan)" lemma="pijn">pijn</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.23" pos="WW(pv,tgw,met-t)" lemma="verdwijnen">verdwijnt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.24" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.25" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.26" pos="BW()" lemma="ook">ook</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.27" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.28" pos="N(soort,ev,basis,zijd,stan)" lemma="koorts">koorts</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.29" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.30" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.31" pos="N(soort,ev,basis,zijd,stan)" lemma="ontsteking">ontsteking</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.32" pos="WW(vd,vrij,zonder)" lemma="remmen">geremd</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.33" pos="WW(pv,tgw,mv)" lemma="worden">worden</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.34" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.35" pos="VG(onder)" lemma="omdat">omdat</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.36" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dat">dat</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.37" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.38" pos="N(soort,ev,basis,zijd,stan)" lemma="prostaglandine">prostaglandine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.39" pos="VNW(aanw,det,stan,prenom,met-e,rest)" lemma="deze">deze</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.40" pos="N(soort,mv,basis)" lemma="reactie">reacties</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.41" pos="BW()" lemma="niet">niet</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.42" pos="VNW(onbep,grad,stan,vrij,zonder,comp)" lemma="veel">meer</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.43" pos="WW(pv,tgw,ev)" lemma="kunnen">kan</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.44" pos="WW(inf,vrij,zonder)" lemma="veroorzaken">veroorzaken</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.11.w.45" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.12">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.1" pos="N(eigen,ev,basis,zijd,stan)" lemma="Aspirine">Aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.2" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.3" pos="BW()" lemma="dus">dus</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.4" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.5" pos="N(soort,ev,basis,zijd,stan)" lemma="inhibitor">inhibitor</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.6" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.7" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="stof">stof</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.9" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.10" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.11" pos="N(soort,ev,basis,zijd,stan)" lemma="werking">werking</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.12" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.13" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.14" pos="N(soort,ev,basis,onz,stan)" lemma="eiwit">eiwit</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.15" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.16" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.17" pos="VNW(aanw,det,stan,prenom,zonder,evon)" lemma="dit">dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.18" pos="N(soort,ev,basis,onz,stan)" lemma="geval">geval</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.19" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.20" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.21" pos="N(soort,ev,basis,zijd,stan)" lemma="cox">COX</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.22" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.23" pos="WW(pv,tgw,met-t)" lemma="remmen">remt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.24" pos="VG(neven)" lemma="of">of</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.25" pos="WW(pv,tgw,met-t)" lemma="stoppen">stopt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.12.w.26" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.13">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.1" pos="BW()" lemma="daarnaast">Daarnaast</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.2" pos="WW(pv,tgw,met-t)" lemma="spelen">speelt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.3" pos="N(soort,ev,basis,zijd,stan)" lemma="prostaglandine">prostaglandine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.4" pos="BW()" lemma="ook">ook</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.5" pos="BW()" lemma="nog">nog</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.6" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.7" pos="N(soort,ev,basis,zijd,stan)" lemma="rol">rol</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.8" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.9" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.10" pos="ADJ(prenom,basis,zonder)" lemma="normaal">normaal</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.11" pos="WW(inf,vrij,zonder)" lemma="functioneren">functioneren</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.13.w.12" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.14">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.1" pos="LID(bep,stan,rest)" lemma="de">De</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="prostaglandine">prostaglandine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.3" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.4" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.5" pos="WW(vd,vrij,zonder)" lemma="maken">gemaakt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.6" pos="VZ(init)" lemma="door">door</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.7" pos="N(eigen,ev,basis,zijd,stan)" lemma="Cox-1">COX-1</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.8" pos="WW(pv,tgw,met-t)" lemma="werken">werkt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.9" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.10" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.11" pos="ADJ(prenom,basis,met-e,stan)" lemma="normaal">normale</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.12" pos="N(soort,mv,basis)" lemma="proces">processen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.13" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.14" pos="VZ(init)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.15" pos="N(soort,ev,basis,zijd,stan)" lemma="boodschapper">boodschapper</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.14.w.16" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.15">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.1" pos="LID(bep,stan,rest)" lemma="de">De</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="prostaglandine">prostaglandine</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.3" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.4" pos="WW(pv,tgw,met-t)" lemma="werken">werkt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.5" pos="VZ(init)" lemma="bij">bij</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="beschadiging">beschadiging</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.7" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.8" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.9" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.10" pos="N(soort,ev,basis,zijd,stan)" lemma="rol">rol</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.11" pos="WW(pv,tgw,met-t)" lemma="spelen">speelt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.12" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.13" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.14" pos="N(soort,ev,basis,onz,stan)" lemma="pijnsignaal">pijnsignaal</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.15" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.16" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.17" pos="WW(vd,vrij,zonder)" lemma="maken">gemaakt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.18" pos="VZ(init)" lemma="door">door</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.19" pos="N(eigen,ev,basis,zijd,stan)" lemma="Cox-2">COX-2</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.15.w.20" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.16">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.16.w.1" pos="N(eigen,ev,basis,zijd,stan)" lemma="Cox-1">COX-1</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.16.w.2" pos="WW(pv,tgw,ev)" lemma="kunnen">kan</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.16.w.3" pos="VG(onder)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.16.w.4" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.16.w.5" pos="BW()" lemma="niet">niet</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.16.w.6" pos="WW(pv,tgw,met-t)" lemma="functioneren">functioneert</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.16.w.7" pos="N(soort,mv,basis)" lemma="maagbloeding">maagbloedingen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.16.w.8" pos="SPEC(afk)" lemma="_">e.d.</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.16.w.9" pos="WW(inf,vrij,zonder)" lemma="veroorzaken">veroorzaken</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.16.w.10" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.17">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.1" pos="VNW(aanw,adv-pron,stan,red,3,getal)" lemma="er">Er</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.2" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.3" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.4" pos="VZ(init)" lemma="sinds">sinds</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.5" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.6" pos="N(soort,ev,basis,onz,stan)" lemma="aantal">aantal</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.7" pos="N(soort,mv,basis)" lemma="jaar">jaren</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.8" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.9" pos="N(soort,ev,basis,onz,stan)" lemma="aantal">aantal</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.10" pos="ADJ(prenom,basis,met-e,stan)" lemma="ander">andere</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.11" pos="N(soort,mv,basis)" lemma="geneesmiddel">geneesmiddelen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.12" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.13" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.14" pos="N(soort,ev,basis,zijd,stan)" lemma="markt">markt</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.15" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.16" pos="ADJ(vrij,basis,zonder)" lemma="selectief">selectief</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.17" pos="N(eigen,ev,basis,zijd,stan)" lemma="Cox-2">COX-2</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.18" pos="WW(inf,vrij,zonder)" lemma="remmen">remmen</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.17.w.19" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.6.s.18">
            <w xml:id="WR-P-E-J-0000125009.p.6.s.18.w.1" pos="WW(pv,tgw,ev)" lemma="zien">Zie</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.18.w.2" pos="N(eigen,ev,basis,zijd,stan)" lemma="Cox-2">COX-2</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.18.w.3" pos="N(soort,mv,basis)" lemma="remmer">remmers</w>
            <w xml:id="WR-P-E-J-0000125009.p.6.s.18.w.4" pos="LET()" lemma=".">.</w>
          </s>
        </p>
      </div>
      <div xml:id="WR-P-E-J-0000125009.div.5">
        <head xml:id="WR-P-E-J-0000125009.head.5">
          <s xml:id="WR-P-E-J-0000125009.head.5.s.1">
            <w xml:id="WR-P-E-J-0000125009.head.5.s.1.w.1" pos="ADJ(prenom,basis,met-e,stan)" lemma="ander">Andere</w>
            <w xml:id="WR-P-E-J-0000125009.head.5.s.1.w.2" pos="N(soort,mv,basis)" lemma="werking">werkingen</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.head.5.s.2">
            <w xml:id="WR-P-E-J-0000125009.head.5.s.2.w.1" pos="N(soort,ev,basis,zijd,stan)" lemma="werking">Werking</w>
            <w xml:id="WR-P-E-J-0000125009.head.5.s.2.w.2" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.head.5.s.2.w.3" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.head.5.s.2.w.4" pos="N(soort,mv,dim)" lemma="bloedplaatje">bloedplaatjes</w>
          </s>
        </head>
        <p xml:id="WR-P-E-J-0000125009.p.7">
          <s xml:id="WR-P-E-J-0000125009.p.7.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.1" pos="N(eigen,ev,basis,zijd,stan)" lemma="Aspirine">Aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.2" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.3" pos="BW()" lemma="niet">niet</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.4" pos="BW()" lemma="alleen">alleen</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.5" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.6" pos="N(soort,ev,basis,onz,stan)" lemma="analgeticum">analgeticum</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.7" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.8" pos="ADJ(prenom,basis,zonder)" lemma="pijnstillend">pijnstillend</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.9" pos="N(soort,ev,basis,onz,stan)" lemma="middel">middel</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.10" pos="LET()" lemma=")">)</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.11" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.12" pos="VG(neven)" lemma="maar">maar</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.13" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.14" pos="WW(pv,tgw,met-t)" lemma="hebben">heeft</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.15" pos="BW()" lemma="ook">ook</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.16" pos="BW()" lemma="nog">nog</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.17" pos="ADJ(prenom,basis,met-e,stan)" lemma="ander">andere</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.18" pos="N(soort,mv,basis)" lemma="effect">effecten</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.19" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.20" pos="VNW(pr,pron,obl,vol,1,mv)" lemma="ons">ons</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.21" pos="N(soort,ev,basis,onz,stan)" lemma="lichaam">lichaam</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.1.w.22" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.7.s.2">
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.1" pos="N(eigen,ev,basis,zijd,stan)" lemma="Aspirine">Aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.2" pos="WW(pv,tgw,met-t)" lemma="hebben">heeft</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.3" pos="TW(hoofd,vrij)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.4" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.5" pos="ADJ(prenom,basis,zonder)" lemma="onomkeerbaar">onomkeerbaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.6" pos="LET()" lemma=")">)</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.7" pos="N(soort,ev,basis,onz,stan)" lemma="effect">effect</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.8" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.9" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.10" pos="N(soort,mv,dim)" lemma="bloedplaatje">bloedplaatjes</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.11" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.12" pos="WW(pv,tgw,met-t)" lemma="belemmeren">belemmert</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.13" pos="VNW(aanw,det,stan,prenom,met-e,rest)" lemma="deze">deze</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.14" pos="VZ(init)" lemma="om">om</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.15" pos="BW()" lemma="samen">samen</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.16" pos="VZ(init)" lemma="te">te</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.17" pos="WW(inf,vrij,zonder)" lemma="klonteren">klonteren</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.18" pos="LET()" lemma=":">:</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.19" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.20" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.21" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.22" pos="N(soort,ev,basis,zijd,stan)" lemma="trombocytenaggregatieremmer">trombocytenaggregatieremmer</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.2.w.23" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.7.s.3">
            <w xml:id="WR-P-E-J-0000125009.p.7.s.3.w.1" pos="BW()" lemma="hierdoor">Hierdoor</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.3.w.2" pos="WW(pv,tgw,met-t)" lemma="verminderen">vermindert</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.3.w.3" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.3.w.4" pos="ADJ(prenom,basis,zonder)" lemma="stelpend">stelpend</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.3.w.5" pos="N(soort,ev,basis,onz,stan)" lemma="vermogen">vermogen</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.3.w.6" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.3.w.7" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.3.w.8" pos="N(soort,ev,basis,onz,stan)" lemma="bloed">bloed</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.3.w.9" pos="VZ(init)" lemma="bij">bij</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.3.w.10" pos="N(soort,ev,basis,zijd,stan)" lemma="bloedvatbeschadiging">bloedvatbeschadiging</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.3.w.11" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.7.s.4">
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.1" pos="LID(bep,stan,rest)" lemma="de">De</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.2" pos="BW()" lemma="vaak">vaak</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.3" pos="WW(vd,prenom,met-e)" lemma="gebruiken">gebruikte</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.4" pos="N(soort,ev,basis,zijd,stan)" lemma="benaming">benaming</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.5" pos="LET()" lemma="'">'</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="bloedverdunner">bloedverdunner</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.7" pos="LET()" lemma="'">'</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.8" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.9" pos="ADJ(vrij,basis,zonder)" lemma="onjuist">onjuist</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.10" pos="LET()" lemma="-">-</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.11" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.12" pos="N(soort,ev,basis,onz,stan)" lemma="bloed">bloed</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.13" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.14" pos="BW()" lemma="niet">niet</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.15" pos="ADJ(vrij,comp,zonder)" lemma="dun">dunner</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.4.w.16" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.7.s.5">
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.1" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dit">Dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.2" pos="N(soort,ev,basis,onz,stan)" lemma="effect">effect</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.3" pos="WW(pv,tgw,met-t)" lemma="treden">treedt</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.4" pos="BW()" lemma="al">al</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.5" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.6" pos="VZ(init)" lemma="na">na</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.7" pos="TW(hoofd,prenom,stan)" lemma="1/4">1/4</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.8" pos="N(soort,ev,basis,onz,stan)" lemma="aspirinetablet">aspirinetablet</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.9" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.10" pos="WW(pv,tgw,met-t)" lemma="houden">houdt</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.11" pos="VZ(init)" lemma="aan">aan</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.12" pos="VZ(init)" lemma="tot">tot</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.13" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.14" pos="ADJ(prenom,basis,met-e,stan)" lemma="uitgeschakelde">uitgeschakelde</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.15" pos="N(soort,mv,dim)" lemma="bloedplaatje">bloedplaatjes</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.16" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.17" pos="VZ(init)" lemma="na">na</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.18" pos="BW()" lemma="ongeveer">ongeveer</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.19" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.20" pos="N(soort,ev,basis,zijd,stan)" lemma="week">week</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.21" pos="LET()" lemma=")">)</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.22" pos="BW()" lemma="allemaal">allemaal</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.23" pos="WW(pv,tgw,mv)" lemma="zijn">zijn</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.24" pos="WW(vd,vrij,zonder)" lemma="vervangen">vervangen</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.5.w.25" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.7.s.6">
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.1" pos="VZ(init)" lemma="voor">Voor</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.2" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dit">dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.3" pos="ADJ(prenom,sup,met-e,stan)" lemma="laat">laatste</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.4" pos="N(soort,ev,basis,onz,stan)" lemma="effect">effect</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.5" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.6" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.7" pos="N(soort,ev,basis,onz,stan)" lemma="middel">middel</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.8" pos="ADJ(vrij,basis,zonder)" lemma="tegenwoordig">tegenwoordig</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.9" pos="BW()" lemma="zeer">zeer</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.10" pos="VNW(onbep,grad,stan,vrij,zonder,basis)" lemma="veel">veel</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.11" pos="WW(vd,vrij,zonder)" lemma="voorschrijven">voorgeschreven</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.12" pos="VZ(init)" lemma="aan">aan</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.13" pos="N(soort,mv,basis)" lemma="mens">mensen</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.14" pos="VNW(betr,pron,stan,vol,persoon,getal)" lemma="die">die</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.15" pos="BW()" lemma="eerder">eerder</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.16" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.17" pos="N(soort,ev,basis,zijd,stan)" lemma="beroerte">beroerte</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.18" pos="VG(neven)" lemma="of">of</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.19" pos="N(soort,ev,basis,zijd,stan)" lemma="hartaanval">hartaanval</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.20" pos="WW(pv,tgw,mv)" lemma="hebben">hebben</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.21" pos="WW(vd,vrij,zonder)" lemma="hebben">gehad</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.22" pos="LET()" lemma=";">;</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.23" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.24" pos="WW(pv,tgw,met-t)" lemma="verminderen">vermindert</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.25" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.26" pos="N(soort,mv,basis)" lemma="kan">kans</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.27" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.28" pos="N(soort,ev,basis,zijd,stan)" lemma="herhaling">herhaling</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.29" pos="VZ(init)" lemma="met">met</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.30" pos="BW()" lemma="ca">ca</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.31" pos="TW(hoofd,prenom,stan)" lemma="40">40</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.32" pos="N(soort,ev,basis,onz,stan)" lemma="%">%</w>
            <w xml:id="WR-P-E-J-0000125009.p.7.s.6.w.33" pos="LET()" lemma=".">.</w>
          </s>
        </p>
      </div>
      <div xml:id="WR-P-E-J-0000125009.div.6">
        <head xml:id="WR-P-E-J-0000125009.head.6">
          <s xml:id="WR-P-E-J-0000125009.head.6.s.1">
            <w xml:id="WR-P-E-J-0000125009.head.6.s.1.w.1" pos="ADJ(prenom,basis,met-e,stan)" lemma="ander">Andere</w>
          </s>
        </head>
        <p xml:id="WR-P-E-J-0000125009.p.8">
          <s xml:id="WR-P-E-J-0000125009.p.8.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.1" pos="BW()" lemma="ook">Ook</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.2" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.3" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.4" pos="N(soort,ev,basis,onz,stan)" lemma="gebied">gebied</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.5" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.6" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.7" pos="N(soort,ev,basis,zijd,stan)" lemma="kanker-preventie">kanker-preventie</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.8" pos="WW(pv,tgw,mv)" lemma="liggen">liggen</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.9" pos="VNW(aanw,adv-pron,stan,red,3,getal)" lemma="er">er</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.10" pos="ADJ(vrij,basis,zonder)" lemma="mogelijk">mogelijk</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.11" pos="N(soort,mv,basis)" lemma="toepassing">toepassingen</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.12" pos="VZ(init)" lemma="voor">voor</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.14" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.15" pos="VG(onder)" lemma="aangezien">aangezien</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.16" pos="VNW(aanw,det,stan,prenom,met-e,rest)" lemma="deze">deze</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.17" pos="N(soort,ev,basis,zijd,stan)" lemma="tumorvorming">tumorvorming</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.18" pos="N(soort,ev,basis,zijd,stan)" lemma="tegengaat">tegengaat</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.1.w.19" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.8.s.2">
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.1" pos="LID(bep,stan,evon)" lemma="het">Het</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.2" pos="ADJ(prenom,basis,zonder)" lemma="dagelijks">dagelijks</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.3" pos="N(soort,ev,basis,onz,stan)" lemma="slikken">slikken</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.4" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.5" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.6" pos="ADJ(prenom,basis,met-e,stan)" lemma="klein">kleine</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.7" pos="N(soort,ev,basis,zijd,stan)" lemma="dosis">dosis</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.9" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.10" pos="VZ(init)" lemma="gedurende">gedurende</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.11" pos="TW(hoofd,vrij)" lemma="5">5</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.12" pos="N(soort,ev,basis,onz,stan)" lemma="jaar">jaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.13" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.14" pos="WW(pv,verl,ev)" lemma="zullen">zou</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.15" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.16" pos="N(soort,mv,basis)" lemma="kan">kans</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.17" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.18" pos="N(soort,mv,basis)" lemma="tumor">tumoren</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.19" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.20" pos="N(soort,ev,basis,zijd,stan)" lemma="slokdarm">slokdarm</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.21" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.22" pos="N(soort,ev,basis,onz,stan)" lemma="darmstelsel">darmstelsel</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.23" pos="VZ(init)" lemma="met">met</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.24" pos="TW(hoofd,prenom,stan)" lemma="twee">twee</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.25" pos="TW(rang,prenom,stan)" lemma="derde">derde</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.26" pos="WW(pv,tgw,mv)" lemma="doen">doen</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.27" pos="WW(inf,vrij,zonder)" lemma="afnemen">afnemen</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.2.w.28" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.8.s.3">
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.1" pos="VZ(init)" lemma="naar">Naar</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.2" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.3" pos="WW(pv,tgw,met-t)" lemma="schijnen">schijnt</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.4" pos="WW(pv,tgw,met-t)" lemma="hebben">heeft</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.5" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.6" pos="BW()" lemma="ook">ook</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.7" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.8" pos="ADJ(prenom,basis,met-e,stan)" lemma="positief">positieve</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.9" pos="N(soort,ev,basis,zijd,stan)" lemma="werking">werking</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.10" pos="VZ(init)" lemma="tegen">tegen</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.11" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.12" pos="N(soort,ev,basis,zijd,stan)" lemma="ziekte">ziekte</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.13" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.14" pos="N(soort,ev,basis,onz,stan)" lemma="alzheimer">Alzheimer</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.15" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.16" pos="SPEC(afgebr)" lemma="_">zwangerschaps-</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.17" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.18" pos="SPEC(afgebr)" lemma="_">darm-</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.19" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.20" pos="SPEC(afgebr)" lemma="_">hart-</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.21" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.22" pos="N(soort,mv,basis)" lemma="vaatziekte">vaatziekten</w>
            <w xml:id="WR-P-E-J-0000125009.p.8.s.3.w.23" pos="LET()" lemma=".">.</w>
          </s>
        </p>
      </div>
      <div xml:id="WR-P-E-J-0000125009.div.7">
        <head xml:id="WR-P-E-J-0000125009.head.7">
          <s xml:id="WR-P-E-J-0000125009.head.7.s.1">
            <w xml:id="WR-P-E-J-0000125009.head.7.s.1.w.1" pos="N(soort,mv,basis)" lemma="bijwerking">Bijwerkingen</w>
          </s>
        </head>
        <p xml:id="WR-P-E-J-0000125009.p.9">
          <s xml:id="WR-P-E-J-0000125009.p.9.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.1" pos="N(eigen,ev,basis,zijd,stan)" lemma="Aspirine">Aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.2" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.3" pos="BW()" lemma="vrij">vrij</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.4" pos="ADJ(vrij,basis,zonder)" lemma="sterk">sterk</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.5" pos="ADJ(vrij,basis,zonder)" lemma="maagprikkelend">maagprikkelend</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.6" pos="LET()" lemma=":">:</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.7" pos="VZ(init)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.8" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.9" pos="BW()" lemma="nu">nu</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.10" pos="VZ(init)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.11" pos="ADJ(prenom,basis,zonder)" lemma="nieuw">nieuw</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.12" pos="N(soort,ev,basis,onz,stan)" lemma="geneesmiddel">geneesmiddel</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.13" pos="WW(pv,verl,ev)" lemma="zullen">zou</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.14" pos="WW(pv,tgw,mv)" lemma="moeten">moeten</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.15" pos="WW(inf,vrij,zonder)" lemma="worden">worden</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.16" pos="WW(inf,vrij,zonder)" lemma="geregistreerd">geregistreerd</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.17" pos="VZ(init)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.18" pos="N(soort,ev,basis,zijd,stan)" lemma="pijnstiller">pijnstiller</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.19" pos="WW(pv,verl,ev)" lemma="zullen">zou</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.20" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dat">dat</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.21" pos="ADJ(vrij,basis,zonder)" lemma="waarschijnlijk">waarschijnlijk</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.22" pos="BW()" lemma="niet">niet</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.23" pos="WW(inf,vrij,zonder)" lemma="lukken">lukken</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.1.w.24" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.9.s.2">
            <w xml:id="WR-P-E-J-0000125009.p.9.s.2.w.1" pos="VZ(init)" lemma="bij">Bij</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.2.w.2" pos="N(soort,ev,basis,onz,stan)" lemma="gebruik">gebruik</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.2.w.3" pos="WW(pv,tgw,mv)" lemma="kunnen">kunnen</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.2.w.4" pos="N(soort,mv,basis)" lemma="maag-klacht">maag-klachten</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.2.w.5" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.2.w.6" pos="BW()" lemma="zelfs">zelfs</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.2.w.7" pos="N(soort,mv,basis)" lemma="maagbloeding">maagbloedingen</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.2.w.8" pos="WW(pv,tgw,mv)" lemma="ontstaan">ontstaan</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.2.w.9" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.9.s.3">
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.1" pos="N(eigen,ev,basis,zijd,stan)" lemma="Aspirine">Aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.2" pos="WW(pv,tgw,met-t)" lemma="hebben">heeft</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.3" pos="BW()" lemma="vooral">vooral</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.4" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.5" pos="ADJ(prenom,basis,met-e,stan)" lemma="hoog">hoge</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.6" pos="N(soort,mv,basis)" lemma="dosering">doseringen</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.7" pos="ADJ(prenom,basis,met-e,stan)" lemma="ernstig">ernstige</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.8" pos="N(soort,mv,basis)" lemma="bijwerking">bijwerkingen</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.9" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.10" pos="VZ(init)" lemma="met">met</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.11" pos="N(soort,ev,basis,dat)" lemma="naam">name</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.12" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.13" pos="BW()" lemma="al">al</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.14" pos="WW(vd,prenom,met-e)" lemma="noemen">genoemde</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.15" pos="N(soort,mv,basis)" lemma="maagbloeding">maagbloedingen</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.16" pos="VG(neven)" lemma="maar">maar</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.17" pos="BW()" lemma="ook">ook</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.18" pos="N(soort,mv,basis)" lemma="oorsuizen">oorsuizen</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.19" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.20" pos="N(soort,ev,basis,zijd,stan)" lemma="doofheid">doofheid</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.21" pos="WW(pv,tgw,mv)" lemma="kunnen">kunnen</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.22" pos="WW(inf,vrij,zonder)" lemma="optreden">optreden</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.3.w.23" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.9.s.4">
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.1" pos="BW()" lemma="ook">Ook</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.2" pos="WW(pv,tgw,ev)" lemma="weten">weet</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.3" pos="VNW(pers,pron,nomin,red,3p,ev,masc)" lemma="men">men</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.4" pos="VG(onder)" lemma="dat">dat</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.5" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.6" pos="N(soort,ev,basis,onz,stan)" lemma="gebruik">gebruik</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.7" pos="BW()" lemma="ervan">ervan</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.8" pos="ADJ(vrij,basis,zonder)" lemma="tijdelijk">tijdelijk</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.9" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.10" pos="N(soort,ev,basis,zijd,stan)" lemma="aanmaak">aanmaak</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.11" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.12" pos="N(soort,ev,basis,onz,stan)" lemma="testosteron">testosteron</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.13" pos="WW(pv,tgw,met-t)" lemma="verminderen">vermindert</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.14" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.15" pos="VG(neven)" lemma="maar">maar</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.16" pos="VNW(aanw,det,stan,prenom,zonder,evon)" lemma="dit">dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.17" pos="N(soort,ev,basis,onz,stan)" lemma="neveneffect">neveneffect</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.18" pos="WW(pv,tgw,met-t)" lemma="hebben">heeft</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.19" pos="VNW(onbep,det,stan,prenom,zonder,agr)" lemma="geen">geen</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.20" pos="WW(od,prenom,met-e)" lemma="blijven">blijvende</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.21" pos="VG(neven)" lemma="of">of</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.22" pos="ADJ(vrij,basis,zonder)" lemma="erg">erg</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.23" pos="ADJ(prenom,basis,met-e,stan)" lemma="schadelijk">schadelijke</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.24" pos="N(soort,ev,basis,zijd,stan)" lemma="werking">werking</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.4.w.25" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.9.s.5">
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.1" pos="VZ(init)" lemma="naast">Naast</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.2" pos="N(soort,ev,basis,onz,stan)" lemma="gebruik">gebruik</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.3" pos="VZ(init)" lemma="bij">bij</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.4" pos="N(soort,ev,basis,zijd,stan)" lemma="zwangerschap">zwangerschap</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.5" pos="VG(neven)" lemma="of">of</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="toediening">toediening</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.7" pos="VZ(init)" lemma="aan">aan</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.8" pos="N(soort,mv,basis)" lemma="baby">baby's</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.9" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.10" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.11" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.12" pos="BW()" lemma="lief">liefst</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.13" pos="BW()" lemma="ook">ook</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.14" pos="BW()" lemma="niet">niet</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.15" pos="VZ(init)" lemma="met">met</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.16" pos="N(soort,ev,basis,zijd,stan)" lemma="alcohol">alcohol</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.17" pos="WW(pv,tgw,met-t)" lemma="gebruiken">gebruikt</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.18" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.19" pos="VG(onder)" lemma="omdat">omdat</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.20" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dit">dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.21" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.22" pos="N(soort,mv,basis)" lemma="kan">kans</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.23" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.24" pos="N(soort,mv,basis)" lemma="maagklacht">maagklachten</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.25" pos="WW(pv,tgw,ev)" lemma="kunnen">kan</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.26" pos="WW(inf,vrij,zonder)" lemma="verhogen">verhogen</w>
            <w xml:id="WR-P-E-J-0000125009.p.9.s.5.w.27" pos="LET()" lemma=".">.</w>
          </s>
        </p>
        <p xml:id="WR-P-E-J-0000125009.p.10">
          <s xml:id="WR-P-E-J-0000125009.p.10.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.10.s.1.w.1" pos="N(soort,ev,basis,onz,stan)" lemma="advies">Advies</w>
            <w xml:id="WR-P-E-J-0000125009.p.10.s.1.w.2" pos="VZ(init)" lemma="voor">voor</w>
            <w xml:id="WR-P-E-J-0000125009.p.10.s.1.w.3" pos="N(soort,ev,basis,onz,stan)" lemma="gebruik">gebruik</w>
            <w xml:id="WR-P-E-J-0000125009.p.10.s.1.w.4" pos="VZ(init)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.10.s.1.w.5" pos="N(soort,ev,basis,zijd,stan)" lemma="pijnstiller">pijnstiller</w>
          </s>
        </p>
        <p xml:id="WR-P-E-J-0000125009.p.11">
          <s xml:id="WR-P-E-J-0000125009.p.11.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.1" pos="VZ(init)" lemma="voor">Voor</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.2" pos="N(soort,ev,basis,onz,stan)" lemma="gebruik">gebruik</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.3" pos="VZ(init)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.4" pos="ADJ(prenom,basis,met-e,stan)" lemma="eenvoudig">eenvoudige</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.5" pos="N(soort,ev,basis,zijd,stan)" lemma="pijnstiller">pijnstiller</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.6" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.7" pos="ADJ(prenom,basis,zonder)" lemma="medisch">medisch</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.8" pos="WW(vd,prenom,zonder)" lemma="zien">gezien</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.9" pos="ADJ(nom,basis,zonder,zonder-n)" lemma="algemeen">algemeen</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.10" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.11" pos="N(soort,ev,basis,zijd,stan)" lemma="voorkeur">voorkeur</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.12" pos="WW(vd,vrij,zonder)" lemma="geven">gegeven</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.13" pos="VZ(init)" lemma="aan">aan</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.14" pos="N(soort,ev,basis,zijd,stan)" lemma="paracetamol">paracetamol</w>
            <w xml:id="WR-P-E-J-0000125009.p.11.s.1.w.15" pos="LET()" lemma=".">.</w>
          </s>
        </p>
      </div>
      <div xml:id="WR-P-E-J-0000125009.div.8">
        <head xml:id="WR-P-E-J-0000125009.head.8">
          <s xml:id="WR-P-E-J-0000125009.head.8.s.1">
            <w xml:id="WR-P-E-J-0000125009.head.8.s.1.w.1" pos="N(soort,ev,basis,zijd,stan)" lemma="synthese">Synthese</w>
            <w xml:id="WR-P-E-J-0000125009.head.8.s.1.w.2" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.head.8.s.1.w.3" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
          </s>
        </head>
        <p xml:id="WR-P-E-J-0000125009.p.12">
          <s xml:id="WR-P-E-J-0000125009.p.12.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.1" pos="VZ(init)" lemma="bij">Bij</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.2" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.3" pos="WW(inf,nom,zonder,zonder-n)" lemma="maken">maken</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.4" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.5" pos="N(soort,ev,basis,onz,stan)" lemma="acetylsalicylzuur">acetylsalicylzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.6" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.7" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.8" pos="LET()" lemma=")">)</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.9" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.10" pos="N(soort,ev,basis,onz,stan)" lemma="laboratorium">laboratorium</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.11" pos="N(soort,ev,basis,zijd,stan)" lemma="schaal">schaal</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.12" pos="WW(pv,tgw,met-t)" lemma="gaan">gaat</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.13" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.14" pos="VZ(init)" lemma="om">om</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.15" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.16" pos="N(soort,ev,basis,zijd,stan)" lemma="opbrengst">opbrengst</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.17" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.18" pos="VNW(onbep,det,stan,prenom,met-e,rest)" lemma="enkel">enkele</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.19" pos="N(soort,mv,basis)" lemma="gram">grammen</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.1.w.20" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.12.s.2">
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.1" pos="VZ(init)" lemma="bij">Bij</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.2" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.3" pos="N(soort,ev,basis,zijd,stan)" lemma="bereiding">bereiding</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.4" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.5" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.6" pos="WW(pv,tgw,ev)" lemma="kunnen">kan</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.7" pos="WW(inf,vrij,zonder)" lemma="worden">worden</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.8" pos="WW(vd,vrij,zonder)" lemma="uitgaan">uitgegaan</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.9" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.10" pos="ADJ(prenom,basis,met-e,stan)" lemma="verschillend">verschillende</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.11" pos="N(soort,ev,basis,onz,stan)" lemma="begin">begin</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.12" pos="N(soort,mv,basis)" lemma="product">producten</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.13" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.14" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.15" pos="VNW(aanw,det,stan,prenom,met-e,rest)" lemma="deze">deze</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.16" pos="N(soort,ev,basis,zijd,stan)" lemma="beschrijving">beschrijving</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.17" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.18" pos="WW(vd,vrij,zonder)" lemma="uitgaan">uitgegaan</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.19" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.20" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.21" pos="N(soort,ev,basis,zijd,stan)" lemma="beginstof">beginstof</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.22" pos="N(soort,ev,basis,onz,stan)" lemma="salicylzuur">salicylzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.2.w.23" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.12.s.3">
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.1" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dit">Dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.2" pos="WW(pv,tgw,met-t)" lemma="hebben">heeft</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.3" pos="VZ(init)" lemma="als">als</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.4" pos="N(soort,ev,basis,onz,stan)" lemma="voordeel">voordeel</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.5" pos="VG(onder)" lemma="dat">dat</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.6" pos="VNW(aanw,adv-pron,stan,red,3,getal)" lemma="er">er</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.7" pos="BW()" lemma="maar">maar</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.8" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.9" pos="N(soort,ev,basis,zijd,stan)" lemma="synthese">synthese</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.10" pos="N(soort,ev,basis,zijd,stan)" lemma="stap">stap</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.11" pos="WW(vd,vrij,zonder)" lemma="uitvoeren">uitgevoerd</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.12" pos="WW(pv,tgw,met-t)" lemma="hoeven">hoeft</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.13" pos="VZ(init)" lemma="te">te</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.14" pos="WW(inf,vrij,zonder)" lemma="worden">worden</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.3.w.15" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.12.s.4">
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.1" pos="VZ(init)" lemma="uitgaande">Uitgaande</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.2" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.3" pos="N(soort,ev,basis,onz,stan)" lemma="salicylzuur">salicylzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.4" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.5" pos="N(soort,ev,basis,zijd,stan)" lemma="azijnzuuranhydride">azijnzuuranhydride</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.6" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.7" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.8" pos="N(soort,ev,basis,onz,stan)" lemma="salicylzuur">salicylzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.9" pos="ADJ(vrij,basis,zonder)" lemma="veresterd">veresterd</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.10" pos="VZ(init)" lemma="volgens">volgens</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.11" pos="ADJ(prenom,basis,met-e,stan)" lemma="nevenstaand">nevenstaande</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.12" pos="N(soort,ev,basis,zijd,stan)" lemma="reactie">reactie</w>
            <w xml:id="WR-P-E-J-0000125009.p.12.s.4.w.13" pos="LET()" lemma=":">:</w>
          </s>
        </p>
        <p xml:id="WR-P-E-J-0000125009.p.13">
          <s xml:id="WR-P-E-J-0000125009.p.13.s.1">
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.1" pos="VG(onder)" lemma="zoals">Zoals</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.2" pos="VZ(init)" lemma="te">te</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.3" pos="WW(inf,vrij,zonder)" lemma="zien">zien</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.4" pos="VZ(init)" lemma="boven">boven</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.5" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="reactiepijl">reactiepijl</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.7" pos="WW(pv,tgw,met-t)" lemma="vinden">vindt</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.8" pos="VNW(aanw,det,stan,prenom,met-e,rest)" lemma="deze">deze</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.9" pos="N(soort,ev,basis,zijd,stan)" lemma="synthese">synthese</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.10" pos="N(soort,ev,basis,zijd,stan)" lemma="plaats">plaats</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.11" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.12" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="zuur">zuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.14" pos="N(soort,ev,basis,onz,stan)" lemma="milieu">milieu</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.1.w.15" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.13.s.2">
            <w xml:id="WR-P-E-J-0000125009.p.13.s.2.w.1" pos="VZ(init)" lemma="in">In</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.2.w.2" pos="VNW(aanw,det,stan,prenom,zonder,evon)" lemma="dit">dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.2.w.3" pos="N(soort,ev,basis,onz,stan)" lemma="geval">geval</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.2.w.4" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.2.w.5" pos="WW(vd,vrij,zonder)" lemma="kiezen">gekozen</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.2.w.6" pos="VZ(init)" lemma="voor">voor</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.2.w.7" pos="WW(vd,prenom,zonder)" lemma="concentreren">geconcentreerd</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.2.w.8" pos="N(soort,ev,basis,onz,stan)" lemma="fosforzuur">fosforzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.2.w.9" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.13.s.3">
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.1" pos="VZ(init)" lemma="na">Na</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.2" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.3" pos="N(soort,ev,basis,zijd,stan)" lemma="reactie">reactie</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.4" pos="WW(pv,tgw,ev)" lemma="moeten">moet</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.5" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="hoofdproduct">hoofdproduct</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.7" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.8" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.9" pos="LET()" lemma=")">)</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.10" pos="WW(vd,vrij,zonder)" lemma="scheiden">gescheiden</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.11" pos="WW(inf,vrij,zonder)" lemma="worden">worden</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.12" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.13" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.14" pos="N(soort,mv,basis)" lemma="bijproduct">bijproducten</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.15" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.16" pos="N(soort,ev,basis,zijd,stan)" lemma="azijnzuur">azijnzuur</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.17" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.18" pos="BW()" lemma="niet">niet</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.19" pos="ADJ(prenom,basis,met-e,stan)" lemma="gereageerde">gereageerde</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.20" pos="N(soort,mv,basis)" lemma="reactant">reactanten</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.21" pos="LET()" lemma=")">)</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.22" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.23" pos="VNW(aanw,pron,stan,vol,3o,ev)" lemma="dit">dit</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.24" pos="WW(pv,tgw,met-t)" lemma="gebeuren">gebeurt</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.25" pos="VZ(init)" lemma="door">door</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.26" pos="N(soort,ev,basis,onz,stan)" lemma="middel">middel</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.27" pos="VZ(init)" lemma="van">van</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.28" pos="N(soort,ev,basis,zijd,stan)" lemma="herkristallisatie">herkristallisatie</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.3.w.29" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.13.s.4">
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.1" pos="LID(bep,stan,rest)" lemma="de">De</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.2" pos="N(soort,ev,basis,zijd,stan)" lemma="herkristallisatie">herkristallisatie</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.3" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.4" pos="WW(vd,vrij,zonder)" lemma="uitvoeren">uitgevoerd</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.5" pos="VZ(init)" lemma="door">door</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.6" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.7" pos="ADJ(prenom,basis,met-e,stan)" lemma="ruw">ruwe</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.8" pos="N(soort,ev,basis,onz,stan)" lemma="product">product</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.9" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.10" pos="VZ(init)" lemma="te">te</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.11" pos="WW(inf,vrij,zonder)" lemma="lossen">lossen</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.12" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.13" pos="N(soort,ev,basis,zijd,stan)" lemma="methanol">methanol</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.14" pos="LET()" lemma="(">(</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.15" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.16" pos="LID(onbep,stan,agr)" lemma="een">een</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.17" pos="N(soort,ev,basis,zijd,stan)" lemma="reflux">reflux</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.18" pos="N(soort,ev,basis,zijd,stan)" lemma="opstelling">opstelling</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.19" pos="LET()" lemma=")">)</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.20" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.21" pos="BW()" lemma="dan">dan</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.22" pos="BW()" lemma="net">net</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.23" pos="BW()" lemma="genoeg">genoeg</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.24" pos="N(soort,ev,basis,onz,stan)" lemma="water">water</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.25" pos="VZ(init)" lemma="toe">toe</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.26" pos="VZ(init)" lemma="te">te</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.27" pos="WW(inf,vrij,zonder)" lemma="voegen">voegen</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.28" pos="VG(onder)" lemma="zodat">zodat</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.29" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.30" pos="N(soort,mv,basis)" lemma="verontreiniging">verontreinigingen</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.31" pos="WW(inf,vrij,zonder)" lemma="uitkristalliseren">uitkristalliseren</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.32" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.33" pos="VG(neven)" lemma="maar">maar</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.34" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.35" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.36" pos="BW()" lemma="niet">niet</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.4.w.37" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.13.s.5">
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.1" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">Het</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.2" pos="ADJ(prenom,basis,met-e,stan)" lemma="heet">hete</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.3" pos="N(soort,ev,basis,onz,stan)" lemma="mengsel">mengsel</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.4" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.5" pos="BW()" lemma="nu">nu</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.6" pos="WW(vd,vrij,zonder)" lemma="filtreren">gefiltreerd</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.7" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.8" pos="BW()" lemma="waardoor">waardoor</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.9" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.10" pos="N(soort,mv,basis)" lemma="verontreiniging">verontreinigingen</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.11" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.12" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.13" pos="N(soort,ev,basis,onz,stan)" lemma="filter">filter</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.14" pos="WW(pv,tgw,mv)" lemma="achterblijven">achterblijven</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.15" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.16" pos="BW()" lemma="alleen">alleen</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.17" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.18" pos="ADJ(prenom,basis,met-e,stan)" lemma="zuiver">zuivere</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.19" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.20" pos="VZ(init)" lemma="in">in</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.21" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.22" pos="N(soort,ev,basis,onz,stan)" lemma="filtraat">filtraat</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.23" pos="WW(pv,tgw,met-t)" lemma="komen">komt</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.5.w.24" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.13.s.6">
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.1" pos="VZ(init)" lemma="na">Na</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.2" pos="VNW(aanw,det,stan,prenom,met-e,rest)" lemma="deze">deze</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.3" pos="N(soort,ev,basis,zijd,stan)" lemma="filtratie">filtratie</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.4" pos="WW(pv,tgw,met-t)" lemma="worden">wordt</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.5" pos="VNW(pers,pron,stan,red,3,ev,onz)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.6" pos="N(soort,ev,basis,zijd,stan)" lemma="filtraat">filtraat</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.7" pos="ADJ(vrij,basis,zonder)" lemma="gekoeld">gekoeld</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.8" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.9" pos="BW()" lemma="opnieuw">opnieuw</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.10" pos="WW(vd,vrij,zonder)" lemma="filtreren">gefiltreerd</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.11" pos="LET()" lemma=",">,</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.12" pos="LID(bep,stan,rest)" lemma="de">de</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.13" pos="ADJ(prenom,basis,met-e,stan)" lemma="gezuiverde">gezuiverde</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.14" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.15" pos="WW(pv,tgw,met-t)" lemma="blijven">blijft</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.16" pos="BW()" lemma="nu">nu</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.17" pos="VZ(init)" lemma="achter">achter</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.18" pos="VZ(init)" lemma="op">op</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.19" pos="LID(bep,stan,evon)" lemma="het">het</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.20" pos="N(soort,ev,basis,onz,stan)" lemma="filter">filter</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.6.w.21" pos="LET()" lemma=".">.</w>
          </s>
          <s xml:id="WR-P-E-J-0000125009.p.13.s.7">
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.1" pos="LID(bep,stan,rest)" lemma="de">De</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.2" pos="WW(vd,prenom,zonder)" lemma="verkrijgen">verkregen</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.3" pos="N(soort,ev,basis,zijd,stan)" lemma="aspirine">aspirine</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.4" pos="WW(pv,tgw,ev)" lemma="kunnen">kan</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.5" pos="BW()" lemma="nu">nu</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.6" pos="WW(pv,tgw,mv)" lemma="worden">worden</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.7" pos="WW(vd,vrij,zonder)" lemma="drogen">gedroogd</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.8" pos="VG(neven)" lemma="en">en</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.9" pos="WW(pv,tgw,ev)" lemma="zijn">is</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.10" pos="ADJ(vrij,basis,zonder)" lemma="klaar">klaar</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.11" pos="VZ(init)" lemma="voor">voor</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.12" pos="N(soort,ev,basis,zijd,stan)" lemma="verpakking">verpakking</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.13" pos="VG(neven)" lemma="of">of</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.14" pos="N(soort,ev,basis,onz,stan)" lemma="gebruik">gebruik</w>
            <w xml:id="WR-P-E-J-0000125009.p.13.s.7.w.15" pos="LET()" lemma=".">.</w>
          </s>
        </p>
      </div>
    </body>
    <gap reason="backmatter" hand="proycon">
       <desc>Backmatter</desc>
       <content>
bli bli bla, bla bla bli
       </content>
    </gap>
  </text>
</DCOI>"""


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = formats
import sys
import os
import unittest

sys.path.append(sys.path[0] + '/../../')
os.environ['PYTHONPATH'] = sys.path[0] + '/../../'
from pynlpl.formats.timbl import TimblOutput
from StringIO import StringIO

class TimblTest(unittest.TestCase):
    
    def test1_simple(self):
        """Timbl - simple output"""
        s = StringIO("a b ? c\nc d ? e\n")
        for i, (features, referenceclass, predictedclass, distribution, distance) in enumerate(TimblOutput(s)):
            if i == 0:
                self.assertEqual(features,['a','b'])
                self.assertEqual(referenceclass,'?')
                self.assertEqual(predictedclass,'c')
                self.assertEqual(distribution,None)
                self.assertEqual(distance,None)
            elif i == 1:
                self.assertEqual(features,['c','d'])
                self.assertEqual(referenceclass,'?')
                self.assertEqual(predictedclass,'e')
                self.assertEqual(distribution,None)
                self.assertEqual(distance,None)            
                        

    def test2_db(self):
        """Timbl - Distribution output"""
        s = StringIO("a c ? c { c 1.00000, d 1.00000 }\na b ? c { c 1.00000 }\na d ? c { c 1.00000, e 1.00000 }")
        for i, (features, referenceclass, predictedclass, distribution, distance) in enumerate(TimblOutput(s)):
            if i == 0:
                self.assertEqual(features,['a','c'])
                self.assertEqual(referenceclass,'?')
                self.assertEqual(predictedclass,'c')
                self.assertEqual(distribution['c'], 0.5)
                self.assertEqual(distribution['d'], 0.5)
                self.assertEqual(distance,None)
            elif i == 1:
                self.assertEqual(features,['a','b'])
                self.assertEqual(referenceclass,'?')
                self.assertEqual(predictedclass,'c')
                self.assertEqual(distribution['c'], 1)
                self.assertEqual(distance,None)            
            elif i == 2:                        
                self.assertEqual(features,['a','d'])
                self.assertEqual(referenceclass,'?')
                self.assertEqual(predictedclass,'c')
                self.assertEqual(distribution['c'], 0.5)
                self.assertEqual(distribution['e'], 0.5)
                self.assertEqual(distance,None)         


    def test3_dbdi(self):
        """Timbl - Distribution + Distance output"""
        s = StringIO("a c ? c { c 1.00000, d 1.00000 }        1.0000000000000\na b ? c { c 1.00000 }        0.0000000000000\na d ? c { c 1.00000, e 1.00000 }        1.0000000000000")
        for i, (features, referenceclass, predictedclass, distribution, distance) in enumerate(TimblOutput(s)):
            if i == 0:
                self.assertEqual(features,['a','c'])
                self.assertEqual(referenceclass,'?')
                self.assertEqual(predictedclass,'c')
                self.assertEqual(distribution['c'], 0.5)
                self.assertEqual(distribution['d'], 0.5)
                self.assertEqual(distance,1.0)
            elif i == 1:
                self.assertEqual(features,['a','b'])
                self.assertEqual(referenceclass,'?')
                self.assertEqual(predictedclass,'c')
                self.assertEqual(distribution['c'], 1)
                self.assertEqual(distance,0.0)            
            elif i == 2:                        
                self.assertEqual(features,['a','d'])
                self.assertEqual(referenceclass,'?')
                self.assertEqual(predictedclass,'c')
                self.assertEqual(distribution['c'], 0.5)
                self.assertEqual(distribution['e'], 0.5)
                self.assertEqual(distance,1.0)         

########NEW FILE########
__FILENAME__ = search
#!/usr/bin/env python
#-*- coding:utf-8 -*-


#---------------------------------------------------------------
# PyNLPl - Test Units for Search Algorithms
#   by Maarten van Gompel, ILK, Universiteit van Tilburg
#   http://ilk.uvt.nl/~mvgompel
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------

import sys
import os
import unittest

sys.path.append(sys.path[0] + '/../../')
os.environ['PYTHONPATH'] = sys.path[0] + '/../../'

from pynlpl.search import AbstractSearchState, DepthFirstSearch, BreadthFirstSearch, IterativeDeepening, HillClimbingSearch, BeamSearch


class ReorderSearchState(AbstractSearchState):
    def __init__(self, tokens, parent = None):
        self.tokens = tokens
        super(ReorderSearchState, self).__init__(parent)

    def expand(self):
        #Operator: Swap two consecutive pairs
        l = len(self.tokens)
        for i in range(0,l - 1):
            newtokens = self.tokens[:i]
            newtokens.append(self.tokens[i + 1])
            newtokens.append(self.tokens[i])
            if i+2 < l:
                newtokens += self.tokens[i+2:]
            yield ReorderSearchState(newtokens, self)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def __str__(self):
        return " ".join(self.tokens)

class InformedReorderSearchState(ReorderSearchState):
    def __init__(self, tokens, goal = None, parent = None):
        self.tokens = tokens
        self.goal = goal
        super(ReorderSearchState, self).__init__(parent)

    def score(self):
        """Compute distortion"""
        totaldistortion = 0
        for i, token in enumerate(self.goal.tokens):
            tokendistortion = 9999999
            for j, token2 in enumerate(self.tokens):
                if token == token2 and abs(i - j) < tokendistortion:
                    tokendistortion = abs(i - j)
            totaldistortion += tokendistortion
        return totaldistortion

    def expand(self):
        #Operator: Swap two consecutive pairs
        l = len(self.tokens)
        for i in range(0,l - 1):
            newtokens = self.tokens[:i]
            newtokens.append(self.tokens[i + 1])
            newtokens.append(self.tokens[i])
            if i+2 < l:
                newtokens += self.tokens[i+2:]
            yield InformedReorderSearchState(newtokens, self.goal, self)

inputstate = ReorderSearchState("a This test . sentence is".split(' '))
goalstate = ReorderSearchState("This is a test sentence .".split(' '))

class DepthFirstSearchTest(unittest.TestCase):
    def test_solution(self):
        """Depth First Search"""
        global inputstate, goalstate
        search = DepthFirstSearch(inputstate ,graph=True, goal=goalstate)
        solution = search.searchfirst()
        #print "DFS:", search.traversalsize(), "nodes visited |",
        self.assertEqual(solution, goalstate)




class BreadthFirstSearchTest(unittest.TestCase):
    def test_solution(self):
        """Breadth First Search"""
        global inputstate, goalstate
        search = BreadthFirstSearch(inputstate ,graph=True, goal=goalstate)
        solution = search.searchfirst()
        #print "BFS:", search.traversalsize(), "nodes visited |",
        self.assertEqual(solution, goalstate)


class IterativeDeepeningTest(unittest.TestCase):
    def test_solution(self):
        """Iterative Deepening DFS"""
        global inputstate, goalstate
        search = IterativeDeepening(inputstate ,graph=True, goal=goalstate)
        solution = search.searchfirst()
        #print "It.Deep:", search.traversalsize(), "nodes visited |",
        self.assertEqual(solution, goalstate)



informedinputstate = InformedReorderSearchState("a This test . sentence is".split(' '), goalstate)
#making a simple language model

class HillClimbingTest(unittest.TestCase):
    def test_solution(self):
        """Hill Climbing"""
        global informedinputstate
        search = HillClimbingSearch(informedinputstate, graph=True, minimize=True,debug=False)
        solution = search.searchbest()
        self.assertTrue(solution) #TODO: this is not a test!

class BeamSearchTest(unittest.TestCase):
    def test_minimizeC1(self):
        """Beam Search needle-in-haystack problem (beam=2, minimize)"""
        #beamsize has been set to the minimum that yields the correct solution
        global informedinputstate, solution, goalstate
        search = BeamSearch(informedinputstate, beamsize=2, graph=True, minimize=True,debug=0, goal=goalstate)
        solution = search.searchbest()
        self.assertEqual( str(solution), str(goalstate) )
        self.assertEqual( search.solutions, 1 )
    
    
    def test_minimizeA1(self):
        """Beam Search optimisation problem A (beam=2, minimize)"""
        #beamsize has been set to the minimum that yields the correct solution
        global informedinputstate, solution, goalstate
        search = BeamSearch(informedinputstate, beamsize=2, graph=True, minimize=True,debug=0)
        solution = search.searchbest()
        self.assertEqual( str(solution), str(goalstate) )
        self.assertTrue( search.solutions > 1 ) #everything is a solution

        
    def test_minimizeA2(self):
        """Beam Search optimisation problem A (beam=100, minimize)"""
        #if a small beamsize works, a very large one should too
        global informedinputstate, solution, goalstate
        search = BeamSearch(informedinputstate, beamsize=100, graph=True, minimize=True,debug=0)
        solution = search.searchbest()
        self.assertEqual( str(solution), str(goalstate) )   
        self.assertTrue( search.solutions > 1 ) #everything is a solution
    
    #def test_minimizeA3(self):    
    #    """Beam Search optimisation problem A (eager mode, beam=2, minimize)"""
    #    #beamsize has been set to the minimum that yields the correct solution
    #    global informedinputstate, solution, goalstate
    #    search = BeamSearch(informedinputstate, beamsize=50, graph=True, minimize=True,eager=True,debug=2)
    #    solution = search.searchbest()
    #    self.assertEqual( str(solution), str(goalstate) )


    def test_minimizeB1(self):
        """Beam Search optimisation problem (longer) (beam=3, minimize)"""
        #beamsize has been set to the minimum that yields the correct solution
        goalstate = InformedReorderSearchState("This is supposed to be a very long sentence .".split(' '))
        informedinputstate = InformedReorderSearchState("a long very . sentence supposed to be This is".split(' '), goalstate)
        search = BeamSearch(informedinputstate, beamsize=3, graph=True, minimize=True,debug=False)
        solution = search.searchbest()
        self.assertEqual(str(solution),str(goalstate))
        
        

if __name__ == '__main__':
    unittest.main()




########NEW FILE########
__FILENAME__ = statistics
#!/usr/bin/env python
#-*- coding:utf-8 -*-

#---------------------------------------------------------------
# PyNLPl - Test Units for Statistics and Information Theory
#   by Maarten van Gompel, ILK, Universiteit van Tilburg
#   http://ilk.uvt.nl/~mvgompel
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

import sys
import os
import unittest

from pynlpl.statistics import FrequencyList, HiddenMarkovModel
from pynlpl.textprocessors import Windower


sentences = ["This is a sentence .".split(' '),"Moreover , this sentence is a test .".split(' ')]

class FrequencyListTest(unittest.TestCase):
    def test_freqlist_casesens(self):
        """Frequency List (case sensitive)"""
        global sentences
        f= FrequencyList()
        for sentence in sentences:
            f.append(sentence)
        self.assertTrue(( f['sentence'] == 2 and  f['this'] == 1 and f['test'] == 1 )) 

    def test_freqlist_caseinsens(self):
        """Frequency List (case insensitive)"""
        global sentences
        f= FrequencyList(None, False)
        for sentence in sentences:
            f.append(sentence)
        self.assertTrue(( f['sentence'] == 2 and  f['this'] == 2 and f['Test'] == 1 )) 

    def test_freqlist_tokencount(self):
        """Frequency List (count tokens)"""
        global sentences
        f= FrequencyList()
        for sentence in sentences:
            f.append(sentence)
        self.assertEqual(f.total,13) 

    def test_freqlist_typecount(self):
        """Frequency List (count types)"""
        global sentences
        f= FrequencyList()
        for sentence in sentences:
            f.append(sentence)
        self.assertEqual(len(f),9) 

class BigramFrequencyListTest(unittest.TestCase):
    def test_freqlist_casesens(self):
        """Bigram Frequency List (case sensitive)"""
        global sentences
        f= FrequencyList()
        for sentence in sentences:
            f.append(Windower(sentence,2))
        self.assertTrue(( f[('is','a')] == 2 and  f[('This','is')] == 1))

    def test_freqlist_caseinsens(self):
        """Bigram Frequency List (case insensitive)"""
        global sentences
        f= FrequencyList(None, False)
        for sentence in sentences:
            f.append(Windower(sentence,2))
        self.assertTrue(( f[('is','a')] == 2 and  f[('this','is')] == 1))

class HMMTest(unittest.TestCase):
    def test_viterbi(self):
        """Viterbi decode run on Hidden Markov Model"""
        hmm = HiddenMarkovModel('start')
        hmm.settransitions('start',{'rainy':0.6,'sunny':0.4})
        hmm.settransitions('rainy',{'rainy':0.7,'sunny':0.3})
        hmm.settransitions('sunny',{'rainy':0.4,'sunny':0.6}) 
        hmm.setemission('rainy', {'walk': 0.1, 'shop': 0.4, 'clean': 0.5})
        hmm.setemission('sunny', {'walk': 0.6, 'shop': 0.3, 'clean': 0.1})
        observations = ['walk', 'shop', 'clean']
        prob, path = hmm.viterbi(observations)
        self.assertEqual( path, ['sunny', 'rainy', 'rainy'])
        self.assertEqual( prob, 0.01344)
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = textprocessors
#!/usr/bin/env python
#-*- coding:utf-8 -*-


#---------------------------------------------------------------
# PyNLPl - Test Units for Text Processors
#   by Maarten van Gompel, ILK, Universiteit van Tilburg
#   http://ilk.uvt.nl/~mvgompel
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

import sys
import os
import unittest

from pynlpl.textprocessors import Windower, tokenise, strip_accents, calculate_overlap

text = "This is a test .".split(" ")

class WindowerTest(unittest.TestCase):
    def test_unigrams(self):
        """Windower (unigrams)"""
        global text
        result = list(iter(Windower(text,1)))
        self.assertEqual(result,[("This",),("is",),("a",),("test",),(".",)])

    def test_bigrams(self):
        """Windower (bigrams)"""
        global text
        result = list(iter(Windower(text,2)))
        self.assertEqual(result,[("<begin>","This"),("This","is"),("is","a"),("a","test"),("test","."),(".","<end>")])

    def test_trigrams(self):
        """Windower (trigrams)"""
        global text
        result = list(iter(Windower(text,3)))
        self.assertEqual(result,[('<begin>', '<begin>', 'This'), ('<begin>', 'This', 'is'), ('This', 'is', 'a'), ('is', 'a', 'test'), ('a', 'test', '.'), ('test', '.', '<end>'), ('.', '<end>', '<end>')])


    def test_trigrams_word(self):
        """Windower (trigrams) (on single word)"""
        global text
        result = list(iter(Windower(["hi"],3)))
        self.assertEqual(result,[('<begin>', '<begin>', 'hi'), ('<begin>', 'hi', '<end>'), ('hi', '<end>', '<end>')])



        
class TokenizerTest(unittest.TestCase):
    def test_tokenize(self):
        """Tokeniser - One sentence"""
        self.assertEqual(tokenise("This is a test."),"This is a test .".split(" "))    
    
    def test_tokenize_sentences(self):
        """Tokeniser - Multiple sentences"""
        self.assertEqual(tokenise("This, is the first sentence! This is the second sentence."),"This , is the first sentence ! This is the second sentence .".split(" "))     
    
    def test_tokenize_noeos(self):
        """Tokeniser - Missing EOS Marker"""
        self.assertEqual(tokenise("This is a test"),"This is a test".split(" "))
    
    def test_tokenize_url(self):
        """Tokeniser - URL"""
        global text
        self.assertEqual(tokenise("I go to http://www.google.com when I need to find something."),"I go to http://www.google.com when I need to find something .".split(" "))        

    def test_tokenize_mail(self):
        """Tokeniser - Mail"""
        global text
        self.assertEqual(tokenise("Write me at proycon@anaproy.nl."),"Write me at proycon@anaproy.nl .".split(" "))        

    def test_tokenize_numeric(self):
        """Tokeniser - numeric"""
        global text
        self.assertEqual(tokenise("I won € 300,000.00!"),"I won € 300,000.00 !".split(" "))        

    def test_tokenize_quotes(self):
        """Tokeniser - quotes"""
        global text
        self.assertEqual(tokenise("Hij zegt: \"Wat een lief baby'tje is dat!\""),"Hij zegt : \" Wat een lief baby'tje is dat ! \"".split(" "))     


class StripAccentTest(unittest.TestCase):
    def test_strip_accents(self):
        """Strip Accents"""        
        self.assertEqual(strip_accents("áàâãāĝŭçñßt"),"aaaaagucnt")

class OverlapTest(unittest.TestCase):
    def test_overlap_subset(self):
        """Overlap - Subset"""
        h = [4,5,6,7]
        n = [5,6]
        self.assertEqual(calculate_overlap(h,n),  [((5,6),0)])
        
    def test_overlap_equal(self):
        """Overlap - Equal"""
        h = [4,5,6,7]
        n = [4,5,6,7]
        self.assertEqual(calculate_overlap(h,n),  [((4,5,6,7),2)])        
        
    def test_overlap_none(self):
        """Overlap - None"""
        h = [4,5,6,7]
        n = [8,9,10]
        self.assertEqual(calculate_overlap(h,n),  [])            
    
    def test_overlap_leftpartial(self):
        """Overlap - Left partial"""
        h = [4,5,6,7]
        n = [1,2,3,4,5]
        self.assertEqual(calculate_overlap(h,n),  [((4,5),-1)] ) 
        
    def test_overlap_rightpartial(self):
        """Overlap - Right partial"""
        h = [4,5,6,7]
        n = [6,7,8,9]
        self.assertEqual(calculate_overlap(h,n),  [((6,7),1)] )        
        
    def test_overlap_leftpartial2(self):
        """Overlap - Left partial (2)"""
        h = [1,2,3,4,5]
        n = [0,1,2]
        self.assertEqual(calculate_overlap(h,n),  [((1,2),-1)] ) 
        
    def test_overlap_rightpartial2(self):
        """Overlap - Right partial (2)"""
        h = [1,2,3,4,5]
        n = [4,5,6]
        self.assertEqual(calculate_overlap(h,n),  [((4,5),1)] )        
    
    
    def test_overlap_leftfull(self):
        """Overlap - Left full"""
        h = [1,2,3,4,5]
        n = [1,2]
        self.assertEqual(calculate_overlap(h,n),  [((1,2),-1)] ) 
        
    def test_overlap_rightfull(self):
        """Overlap - Right full"""
        h = [1,2,3,4,5]
        n = [4,5]
        self.assertEqual(calculate_overlap(h,n),  [((4,5),1)] )        
    

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = textprocessors
# -*- coding: utf8 -*-

###############################################################
#  PyNLPl - Text Processors
#   by Maarten van Gompel
#   Centre for Language Studies
#   Radboud University Nijmegen
#   http://www.github.com/proycon/pynlpl
#   proycon AT anaproy DOT nl
#
#       Licensed under GPLv3
#
# This is a Python library containing text processors
#
###############################################################


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from pynlpl.common import isstring
import sys
if sys.version < '3':
    from codecs import getwriter
    stderr = getwriter('utf-8')(sys.stderr)
    stdout = getwriter('utf-8')(sys.stdout)
else:
    stderr = sys.stderr
    stdout = sys.stdout

import unicodedata
import string
import io
import array
import re
from itertools import permutations
from pynlpl.statistics import FrequencyList
from pynlpl.formats import folia
from pynlpl.algorithms import bytesize

WHITESPACE = [" ", "\t", "\n", "\r","\v","\f"]
EOSMARKERS = ('.','?','!','。',';','؟','｡','？','！','।','։','՞','።','᙮','។','៕')
REGEXP_URL = re.compile(r"^(?:(?:https?):(?:(?://)|(?:\\\\))|www\.)(?:[\w\d:#@%/;$()~_?\+-=\\\.&](?:#!)?)*")
REGEXP_MAIL = re.compile(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+(?:\.[a-zA-Z]+)+") #email
TOKENIZERRULES = (REGEXP_URL, REGEXP_MAIL)


class Windower(object):
    """Moves a sliding window over a list of tokens, upon iteration in yields all n-grams of specified size in a tuple.

    Example without markers:

    >>> for ngram in Windower("This is a test .",3, None, None):
    ...     print(" ".join(ngram))
    This is a
    is a test
    a test .

    Example with default markers:

    >>> for ngram in Windower("This is a test .",3):
    ...     print(" ".join(ngram))
    <begin> <begin> This
    <begin> This is
    This is a
    is a test
    a test .
    test . <end>
    . <end> <end>
    """

    def __init__(self, tokens, n=1, beginmarker = "<begin>", endmarker = "<end>"):
        """
        Constructor for Windower

        :param tokens: The tokens to iterate over. Should be an itereable. Strings will be split on spaces automatically.
        :type tokens: iterable
        :param n: The size of the n-grams to extract
        :type n: integer
        :param beginmarker: The marker for the beginning of the sentence, defaults to "<begin>". Set to None if no markers are desired.
        :type beginmarker: string or None
        :param endmarker: The marker for the end of the sentence, defaults to "<end>". Set to None if no markers are desired.
        :type endmarker: string or None
        """


        if isinstance(tokens, str) or (sys.version < '3' and isinstance(tokens, unicode)):
            self.tokens = tuple(tokens.split())
        else:
            self.tokens = tuple(tokens)
        assert isinstance(n, int)
        self.n = n
        self.beginmarker = beginmarker
        self.endmarker = endmarker

    def __len__(self):
        """Returns the number of n-grams in the data (quick computation without iteration)

        Without markers:

        >>> len(Windower("This is a test .",3, None, None))
        3

        >>> len(Windower("This is a test .",2, None, None))
        4

        >>> len(Windower("This is a test .",1, None, None))
        5

        With default markers:

        >>> len(Windower("This is a test .",3))
        7

        """

        c = (len(self.tokens) - self.n) + 1
        if self.beginmarker: c += self.n-1
        if self.endmarker: c += self.n-1
        return c


    def __iter__(self):
        """Yields an n-gram (tuple) at each iteration"""
        l = len(self.tokens)

        if self.beginmarker:
            beginmarker = (self.beginmarker),  #tuple
        if self.endmarker:
            endmarker = (self.endmarker),  #tuple

        for i in range(-(self.n - 1),l):
            begin = i
            end = i + self.n
            if begin >= 0 and end <= l:
                yield tuple(self.tokens[begin:end])
            elif begin < 0 and end > l:
                if not self.beginmarker or not self.endmarker:
                    continue
                else:
                   yield tuple(((begin * -1) * beginmarker  ) + self.tokens + ((end - l) * endmarker ))
            elif begin < 0:
                if not self.beginmarker:
                   continue
                else:
                   yield tuple(((begin * -1) * beginmarker ) + self.tokens[0:end])
            elif end > l:
                if not self.endmarker:
                   continue
                else:
                   yield tuple(self.tokens[begin:] + ((end - l) * endmarker))

class MultiWindower(object):
    "Extract n-grams of various configurations from a sequence"

    def __init__(self,tokens, min_n = 1, max_n = 9, beginmarker=None, endmarker=None):
        if isinstance(tokens, str) or (sys.version < '3' and isinstance(tokens, unicode)):
            self.tokens = tuple(tokens.split())
        else:
            self.tokens = tuple(tokens)
        assert isinstance(min_n, int)
        assert isinstance(max_n, int)
        self.min_n = min_n
        self.max_n = max_n
        self.beginmarker = beginmarker
        self.endmarker = endmarker

    def __iter__(self):
        for n in range(self.min_n, self.max_n + 1):
            for ngram in Windower(self.tokens,n, self.beginmarker, self.endmarker):
                yield ngram


class ReflowText(object):
    """Attempts to re-flow a text that has arbitrary line endings in it. Also undoes hyphenisation"""

    def __init__(self, stream, filternontext=True):
        self.stream = stream
        self.filternontext = filternontext

    def __iter__(self):
        eosmarkers = ('.',':','?','!','"',"'","„","”","’")
        emptyline = 0
        buffer = ""
        for line in self.stream:

            line = line.strip()
            if line:
                if emptyline:
                    if buffer:
                        yield buffer
                        yield ""
                        emptyline = 0
                        buffer = ""

                if buffer: buffer += ' '
                if (line[-1] in eosmarkers):
                    buffer += line
                    yield buffer
                    buffer = ""
                    emptyline = 0
                elif len(line) > 2 and line[-1] == '-' and line[-2].isalpha():
                    #undo hyphenisation
                    buffer += line[:-1]
                else:
                    if self.filternontext:
                        hastext = False
                        for c in line:
                            if c.isalpha():
                                hastext = True
                                break
                    else:
                        hastext = True

                    if hastext:
                        buffer += line
            else:
                emptyline += 1

            #print "BUFFER=[" + buffer.encode('utf-8') + "] emptyline=" + str(emptyline)

        if buffer:
            yield buffer



def calculate_overlap(haystack, needle, allowpartial=True):
    """Calculate the overlap between two sequences. Yields (overlap, placement) tuples (multiple because there may be multiple overlaps!). The former is the part of the sequence that overlaps, and the latter is -1 if the overlap is on the left side, 0 if it is a subset, 1 if it overlaps on the right side, 2 if its an identical match"""
    needle = tuple(needle)
    haystack = tuple(haystack)
    solutions = []

    #equality check
    if needle == haystack:
        return [(needle, 2)]

    if allowpartial:
        minl =1
    else:
        minl = len(needle)

    for l in range(minl,min(len(needle), len(haystack))+1):
        #print "LEFT-DEBUG", l,":", needle[-l:], " vs ", haystack[:l]
        #print "RIGHT-DEBUG", l,":", needle[:l], " vs ", haystack[-l:]
        #Search for overlap left (including partial overlap!)
        if needle[-l:] == haystack[:l]:
            #print "LEFT MATCH"
            solutions.append( (needle[-l:], -1) )
        #Search for overlap right (including partial overlap!)
        if needle[:l] == haystack[-l:]:
            #print "RIGHT MATCH"
            solutions.append( (needle[:l], 1) )

    if len(needle) <= len(haystack):
        options = list(iter(Windower(haystack,len(needle),beginmarker=None,endmarker=None)))
        for option in options[1:-1]:
            if option == needle:
                #print "SUBSET MATCH"
                solutions.append( (needle, 0) )

    return solutions




class Tokenizer(object):
    """A tokenizer and sentence splitter, which acts on a file/stream-like object and when iterating over the object it yields
    a lists of tokens (in case the sentence splitter is active (default)), or a token (if the sentence splitter is deactivated).
    """

    def __init__(self, stream, splitsentences=True, onesentenceperline=False, regexps=TOKENIZERRULES):
        """
        Constructor for Tokenizer

        :param stream: An iterable or file-object containing the data to tokenize
        :type stream: iterable or file-like object
        :param splitsentences: Enable sentence splitter? (default=_True_)
        :type splitsentences: bool
        :param onesentenceperline: Assume input has one sentence per line? (default=_False_)
        :type onesentenceperline: bool
        :param regexps: Regular expressions to use as tokeniser rules in tokenisation (default=_pynlpl.textprocessors.TOKENIZERRULES_)
        :type regexps:  Tuple/list of regular expressions to use in tokenisation
        """

        self.stream = stream
        self.regexps = regexps
        self.splitsentences=splitsentences
        self.onesentenceperline = onesentenceperline

    def __iter__(self):
        buffer = ""
        for line in self.stream:
            line = line.strip()
            if line:
                if buffer: buffer += "\n"
                buffer += line

            if (self.onesentenceperline or not line) and buffer:
                if self.splitsentences:
                    yield split_sentences(tokenize(buffer))
                else:
                    for token in tokenize(buffer, self.regexps):
                        yield token
                buffer = ""

        if buffer:
            if self.splitsentences:
                yield split_sentences(tokenize(buffer))
            else:
                for token in tokenize(buffer, self.regexps):
                    yield token




def tokenize(text, regexps=TOKENIZERRULES):
    """Tokenizes a string and returns a list of tokens

    :param text: The text to tokenise
    :type text: string
    :param regexps: Regular expressions to use as tokeniser rules in tokenisation (default=_pynlpl.textprocessors.TOKENIZERRULES_)
    :type regexps:  Tuple/list of regular expressions to use in tokenisation
    :rtype: Returns a list of tokens

    Examples:

    >>> for token in tokenize("This is a test."):
    ...    print(token)
    This
    is
    a
    test
    .


    """

    for i,regexp in list(enumerate(regexps)):
        if isstring(regexp):
            regexps[i] = re.compile(regexp)

    tokens = []
    begin = 0
    for i, c in enumerate(text):
        if begin > i:
            continue
        elif i == begin:
            m = False
            for regexp in regexps:
                m = regexp.findall(text[i:i+300])
                if m:
                    tokens.append(m[0])
                    begin = i + len(m[0])
                    break
            if m: continue

        if c in string.punctuation or c in WHITESPACE:
            prev = text[i-1] if i > 0 else ""
            next = text[i+1] if i < len(text)-1 else ""

            if (c == '.' or c == ',') and prev.isdigit() and next.isdigit():
                #punctuation in between numbers, keep as one token
                pass
            elif (c == "'" or c == "`") and prev.isalpha() and next.isalpha():
                #quote in between chars, keep...
                pass
            elif c not in WHITESPACE and next == c: #group clusters of identical punctuation together
                continue
            elif c == '\r' and prev == '\n':
                #ignore
                begin = i+1
                continue
            else:
                token = text[begin:i]
                if token: tokens.append(token)

                if c not in WHITESPACE:
                    tokens.append(c) #anything but spaces and newlines (i.e. punctuation) counts as a token too
                begin = i + 1 #set the begin cursor

    if begin <= len(text) - 1:
        token = text[begin:]
        tokens.append(token)

    return tokens


def crude_tokenizer(text):
    """Replaced by tokenize(). Alias"""
    return tokenize(text) #backwards-compatibility, not so crude anymore

def tokenise(text, regexps=TOKENIZERRULES): #for the British
    """Alias for the British"""
    return tokenize(text)

def is_end_of_sentence(tokens,i ):
    # is this an end-of-sentence marker? ... and is this either
    # the last token or the next token is NOT an end of sentence
    # marker as well? (to deal with ellipsis etc)
    return tokens[i] in EOSMARKERS and (i == len(tokens) - 1 or not tokens[i+1] in EOSMARKERS)

def split_sentences(tokens):
    """Split sentences (based on tokenised data), returns sentences as a list of lists of tokens, each sentence is a list of tokens"""
    begin = 0
    for i, token in enumerate(tokens):
        if is_end_of_sentence(tokens, i):
            yield tokens[begin:i+1]
            begin = i+1
    if begin <= len(tokens)-1:
        yield tokens[begin:]



def strip_accents(s, encoding= 'utf-8'):
    """Strip characters with diacritics and return a flat ascii representation"""
    if sys.version < '3':
        if isinstance(s,unicode):
           return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore')
        else:
           return unicodedata.normalize('NFKD', unicode(s,encoding)).encode('ASCII', 'ignore')
    else:
        if isinstance(s,bytes): s = str(s,encoding)
        return str(unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore'),'ascii')

def swap(tokens, maxdist=2):
    """Perform a swap operation on a sequence of tokens, exhaustively swapping all tokens up to the maximum specified distance. This is a subset of all permutations."""
    assert maxdist >= 2
    tokens = list(tokens)
    if maxdist > len(tokens):
        maxdist = len(tokens)
    l = len(tokens)
    for i in range(0,l - 1):
        for permutation in permutations(tokens[i:i+maxdist]):
            if permutation != tuple(tokens[i:i+maxdist]):
                newtokens = tokens[:i]
                newtokens += permutation
                newtokens += tokens[i+maxdist:]
                yield newtokens
        if maxdist == len(tokens):
            break


def find_keyword_in_context(tokens, keyword, contextsize=1):
    """Find a keyword in a particular sequence of tokens, and return the local context. Contextsize is the number of words to the left and right. The keyword may have multiple word, in which case it should to passed as a tuple or list"""
    if isinstance(keyword,tuple) and isinstance(keyword,list):
        l = len(keyword)
    else:
        keyword = (keyword,)
        l = 1
    n = l + contextsize*2
    focuspos = contextsize + 1
    for ngram in Windower(tokens,n,None,None):
        if ngram[focuspos:focuspos+l] == keyword:
            yield ngram[:focuspos], ngram[focuspos:focuspos+l],ngram[focuspos+l+1:]

if sys.version > '3':
    #Python 3 only

    class ClassEncoder:

        def __init__(self, filename="", autoadd=False, allowunknown=False,syncwithdecoder=None):
            self.newestclass = 5
            self.data = { "\n": 1, "{UNKNOWN}": 2 }
            self.filename = filename
            self.autoadd = autoadd
            self.allowunknown = allowunknown
            self.syncwithdecoder = syncwithdecoder

            if filename:
                with open(filename,'r',encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            cls, word = line.strip().split('\t')
                            cls = int(cls)
                            self.data[word] = cls
                            if not self.syncwithdecoder is None:
                                self.syncwithdecoder.data[cls] = word
                            if cls > self.newestclass:
                                self.newestclass = cls

        def save(self, filename=""):
            if not filename: filename = self.filename
            with open(filename, 'w',encoding='utf-8') as f:
                for word, cls in self:
                    if cls > 2:
                        f.write( str(cls) + "\t" + word + "\n")


        def buildfromtext(self, files, encoding='utf-8'):
            freqlist = FrequencyList()
            if isinstance(files, str): files = [files]
            for filename in files:
                with open(filename, 'r',encoding=encoding) as f:
                    for line in f:
                        tokens = line.strip().split()
                        freqlist.append(tokens)

            self.buildfromfreqlist(freqlist)

        def buildfromfreqlist(self, freqlist):
            for word, count in freqlist:
                if not word in self.data:
                    self.newestclass += 1
                    self.data[word] = self.newestclass


        def buildfromfolia(self, files, encoding='utf-8'):
            freqlist = FrequencyList()
            if isinstance(files, str): files = [files]
            for filename in files:
                f = folia.Document(file=filename)
                for sentence in f.sentences():
                    tokens = sentence.toktext().split(' ')
                    freqlist.append(tokens)


            self.buildfromfreqlist(freqlist)

        def __iter__(self):
            for word, cls in self.data.items():
                yield word, cls

        def __len__(self):
            return self.data

        def __getitem__(self, word):
            if self.autoadd:
                try:
                    return self.data[word]
                except KeyError:
                    self.newestclass += 1
                    self.data[self.newestclass] = word
                    if self.syncwithdecoder:
                        self.syncwithdecoder.data[self.newestclass] = word
                    return self.newestclass
            else:
                return self.data[word]

        def __contains__(self, word):
            return word in self.data


        def encodefile(self, files,targetfilename, encoding='utf-8'):
            if isinstance(files, str): files = [files]
            o = self.newencodedfile(targetfilename)
            for filename in files:
                with open(filename,'r',encoding=encoding) as f:
                    for line in f:
                        self.encodesentence(line.strip().split(), o)
            o.close()

        def newencodedfile(self, targetfilename):
            o = open(targetfilename,'wb')
            o.write(b'\x00') #first byte contains version number!
            return o

        def encodesentence(self, tokens, stream=None):
            for token in tokens:
                try:
                    cls = self[token]
                    b = int.to_bytes(cls, bytesize(cls), 'big' )
                except KeyError:
                    if self.autoadd:
                        self.newestclass += 1
                        b = int.to_bytes(self.newestclass, bytesize(self.newestclass),'big')
                        self.data[token] = self.newestclass
                        if self.syncwithdecoder:
                            self.syncwithdecoder.data[self.newestclass] = token
                    elif self.allowunknown:
                        b = b'\x02'
                    else:
                        raise
                assert len(b) < 128
                size = int.to_bytes(len(b),1,'big')
                stream.write(size)
                stream.write(b)
            stream.write(b'\x01\x01') #newline


    class ClassDecoder:

        def __init__(self, filename="", allowunknown=False):
            self.newestclass = 5
            self.data = { 1: "\n", 2: "{UNKNOWN}"}
            self.filename = filename
            self.allowunknown=allowunknown


            if filename:
                with open(filename,'r',encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                cls, word = line.strip().split('\t')
                            except:
                                print("WARNING: Unable to parse line:", line,file=sys.stderr)
                            cls = int(cls)
                            self.data[cls] = word
                            if cls > self.newestclass:
                                self.newestclass = cls


        def __iter__(self):
            for cls, word in self.data:
                yield cls, word

        def __len__(self):
            return self.data

        def __getitem__(self, cls):
            if self.allowunknown:
                try:
                    return self.data[cls]
                except:
                    return "{UNKNOWN}"
            else:
                return self.data[cls]

        def __contains__(self, cls):
            return cls in self.data

        def decodefile(self, files, targetfilename = None, encoding='utf-8'):
            if targetfilename:
                o = open(targetfilename,'w',encoding=encoding)

            if isinstance(files, str): files = [files]
            nextspace = False
            for filename in files:
                with open(filename,'rb') as f:
                    version = f.read(1)
                    assert (version == b'\x00')
                    while True:
                        size = f.read(1)
                        if not size:
                            break #EOF
                        b = f.read(int.from_bytes(size,'big'))
                        cls = int.from_bytes(b,'big' )
                        if targetfilename:
                            if nextspace: o.write(" ")
                            o.write(self[cls])
                        else:
                            if nextspace: print(" ", end="")
                            print(self[cls],end="")
                        if cls != 1:
                            nextspace = True
                        else:
                            nextspace = False


            if targetfilename:
                o.close()



if __name__ == "__main__":
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = classdecoder
#!/usr/bin/env python3
#-*- coding:utf-8 -*-


from pynlpl.textprocessors import ClassDecoder
import sys
import os
import argparse



def main():
    """pynlpl-classdecoder
    by Maarten van Gompel (proycon)
    Centre for Language Studies, Radboud University Nijmegen
    2013 - Licensed under GPLv3

    This tool decodes files from a  more compressed binary format, in which each word-type gets assigned a numeric class value, back to plain text.

    Usage: pynlpl-classdecoder [files]
    """

    parser = argparse.ArgumentParser(prog="pynlpl-classdecoder", description='This tool converts one or more tokenised plain text files, with one sentence per line, to a more compressed binary format in which each word-type gets assigned a numeric class value.  Instead of plain text files, FoLiA XML files are also supported as valid input. Certain other NLP tools may make use of this format to conserve memory and attain higher performance.')
    parser.add_argument("-s","--singleoutput", type=str, help="Decode all files to a single file, set filename to - to decode to standard output")
    parser.add_argument("--encoding",type=str,default="utf-8",help="Encoding of plain-text input files")
    parser.add_argument("-u","--unknown",action='store_true',default=False,help="Unknown classes will be assigned a special 'unknown' class (used with -c)")

    parser.add_argument('classfile', type=str, help="Class file (*.cls)")
    parser.add_argument('files', nargs='+', help="The encoded corpus files (*.clsenc)")
    args = parser.parse_args()

    classdecoder = ClassDecoder(args.classfile, args.unknown)

    if args.singleoutput:
        print("Decoding all files to " + args.singleoutput+"...", file=sys.stderr)
        classdecoder.decodefile(args.files, args.singleoutput if args.singleoutput != '-' else None, args.encoding)
    else:
        for filename in args.files:
            targetfile = os.path.basename(filename).replace('.clsenc','') + '.txt'
            print("Decoding " + filename + " to " + targetfilename+"...", file=sys.stderr)
            classdecoder.decodefile(filename, targetfile)


########NEW FILE########
__FILENAME__ = classencoder
#!/usr/bin/env python3
#-*- coding:utf-8 -*-


#Python 3 by definition

from pynlpl.textprocessors import ClassEncoder
from pynlpl.statistics import FrequencyList
from pynlpl.formats import folia
import argparse
import sys
import os
assert sys.version > '3'

def main():
    """pynlpl-classencoder
    by Maarten van Gompel (proycon)
    Centre for Language Studies, Radboud University Nijmegen
    2013 - Licensed under GPLv3

    This tool converts one or more tokenised plain text files, with one sentence per line, to a more compressed binary format in which each word-type gets assigned a numeric class value.
    Instead of plain text files, FoLiA XML files are also supported as valid input. Certain other NLP tools may make use of this format to conserve memory and attain higher performance.

    Usage: pynlpl-classencoder [files]
    """

    parser = argparse.ArgumentParser(prog="pynlpl-classencoder", description='This tool converts one or more tokenised plain text files, with one sentence per line, to a more compressed binary format in which each word-type gets assigned a numeric class value.  Instead of plain text files, FoLiA XML files are also supported as valid input. Certain other NLP tools may make use of this format to conserve memory and attain higher performance.')
    parser.add_argument("-x","--xml", help="Input is FoLiA XML instead of plain-text")
    parser.add_argument("-c","--classfile", type=str,help="Load and use existing class model instead of building a new one")
    parser.add_argument("-o","--output", type=str, default="classes.cls", help="Filename of the class file")
    parser.add_argument("-s","--singleoutput", type=str, help="Encode all files to a single file")
    parser.add_argument("-e","--extend",action='store_true',default=False,help="Extend existing class model with (used with -c)")
    parser.add_argument("-a","--autoadd",action='store_true',default=False,help="Automatically add newly found classes to existing class file (used with -c)")
    parser.add_argument("-u","--unknown",action='store_true',default=False,help="Unknown classes will be assigned a special 'unknown' class (used with -c)")
    parser.add_argument("--encoding",type=str,default="utf-8",help="Encoding of plain-text input files")

    parser.add_argument('files', nargs='+')
    args = parser.parse_args()


    if args.classfile:
        classencoder = ClassEncoder(args.classfile, args.autoadd or args.extend, args.unknown)
    else:
        classencoder = ClassEncoder(None, args.autoadd or args.extend, args.unknown)

    if not args.classfile or args.extend:
        if args.xml:
            for filename in args.files:
                doc = folia.Document(file=filename)

        else:
            print("Building classes...", file=sys.stderr)
            if args.xml:
                classencoder.buildfromfolia(args.files)
            else:
                classencoder.buildfromtext(args.files)

    if not args.classfile:
        print("Writing classes to ", args.output, file=sys.stderr)
        classencoder.save(args.output)

    if args.singleoutput:
        print("Encoding all files in " + args.singleoutput + "...", file=sys.stderr)
        classencoder.encodefile(args.files, args.singleoutput, args.encoding)
    else:
        for filename in args.files:
            targetfilename = os.path.basename(filename).replace('.txt','').replace('.xml','') + '.clsenc'
            print("Encoding " + filename + " in " + targetfilename + "...",file=sys.stderr)
            classencoder.encodefile(filename, targetfilename)

    if args.classfile and args.autoadd:
        print("Writing classes to ", args.classfile, file=sys.stderr)
        classencoder.save(args.classfile)



if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = computepmi
#!/usr/bin/env python3


from __future__ import print_function, unicode_literals, division, absolute_import

import argparse
import sys
from math import log

from collections import defaultdict

def pmi(sentences1, sentences2,discount = 0):
    jointcount = len(sentences1 & sentences2) - discount
    if jointcount <= 0: return None
    return log( jointcount / (len(sentences1) * len(sentences2))), jointcount+discount

def npmi(sentences1, sentences2,discount=0):
    jointcount = len(sentences1 & sentences2) - discount
    if jointcount <= 0: return None
    return log( jointcount / (len(sentences1) * len(sentences2))) / -log(jointcount), jointcount+discount

def main():
    parser = argparse.ArgumentParser(description="Simple cooccurence computation", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-f','--inputtext', type=str,help="Input file (plaintext, tokenised, utf-8, one sentence per line)", action='store',default="",required=True)
    parser.add_argument('-s','--sorted', help="Output sorted by co-occurrence score", action='store_true',default=False)
    parser.add_argument('-t','--threshold', help="Joined occurrence threshold, do not consider words occuring less than this", type=int, action='store',default=1)
    parser.add_argument('-a','--adjacency', help="Compute the adjacency fraction (how many co-occurrence are immediate bigrams)", action='store_true',default=False)
    parser.add_argument('-A','--discountadjacency', help="Do not take immediately adjacent fragments (bigrams) into account when computing mutual information (requires -a)", action='store_true',default=False)
    parser.add_argument('--pmi',help="Compute pointwise mutual information", action='store_true',default=False)
    parser.add_argument('--npmi',help="Compute normalised pointwise mutual information", action='store_true',default=False)
    parser.add_argument('--jaccard',help="Compute jaccard similarity coefficient", action='store_true',default=False)
    parser.add_argument('--dice',help="Compute dice coefficient", action='store_true',default=False)

    args = parser.parse_args()
    if not args.pmi and not args.npmi and not args.jaccard and not args.dice:
        args.pmi = True

    count = defaultdict(int)
    cooc = defaultdict(lambda: defaultdict(int))
    adjacent = defaultdict(lambda: defaultdict(int))
    total = 0

    f = open(args.inputtext,'r',encoding='utf-8')
    for i, line in enumerate(f):
        sentence = i + 1
        if sentence % 1000 == 0: print("Indexing @" + str(sentence),file=sys.stderr)
        if line:
            words = list(enumerate(line.split()))
            for pos, word in words:
                count[word] += 1
                total += 1
                for pos2, word2 in words:
                    if pos2 > pos:
                        cooc[word][word2] += 1
                        if args.adjacency and pos2 == pos + len(word.split()):
                            adjacent[word][word2] += 1
    f.close()


    l = len(cooc)
    output = []
    for i, (word, coocdata) in enumerate(cooc.items()):
        print("Computing mutual information @" + str(i+1) + "/" + str(l) + ": \"" + word + "\" , co-occurs with " + str(len(coocdata)) + " words",file=sys.stderr)
        for word2, jointcount in coocdata.items():
            if jointcount> args.threshold:
                if args.adjacency and word in adjacent and word2 in adjacent[word]:
                    adjcount = adjacent[word][word2]
                else:
                    adjcount = 0

                if args.discountadjacency:
                    discount = adjcount
                else:
                    discount = 0

                if args.pmi:
                    score = log( ((jointcount-discount)/total)  / ((count[word]/total) * (count[word2]/total)))
                elif args.npmi:
                    score = log( ((jointcount-discount)/total) / ((count[word]/total) * (count[word2]/total))) / -log((jointcount-discount)/total)
                elif args.jaccard or args.dice:
                    score = (jointcount-discount) / (count[word] + count[word2] - (jointcount - discount) )
                    if args.dice:
                        score = 2*score / (1+score)

                if args.sorted:
                    outputdata = (word,word2,score, jointcount, adjcount, adjcount / jointcount if args.adjacency else None)
                    output.append(outputdata)
                else:
                    if args.adjacency:
                        print(word + "\t" + word2 + "\t" + str(score) + "\t" + str(jointcount) + "\t" + str(adjcount) + "\t" + str(adjcount / jointcount))
                    else:
                        print(word + "\t" + word2 + "\t" + str(score) + "\t" + str(jointcount))


    if args.sorted:
        print("Outputting " + str(len(output)) + " pairs",file=sys.stderr)
        if args.adjacency:
            print("#WORD\tWORD2\tSCORE\tJOINTCOUNT\tBIGRAMCOUNT\tBIGRAMRATIO")
        else:
            print("#WORD\tWORD2\tSCORE\tJOINTCOUNT\tBIGRAMCOUNT\tBIGRAMRATIO")
        if args.npmi:
            sign = 1
        else:
            sign = -1
        for word,word2,score,jointcount,adjcount, adjratio in sorted(output, key=lambda x: sign * x[2]):
            if args.adjacency:
                print(word + "\t" + word2 + "\t" + str(score) + "\t" + str(jointcount) + "\t" + str(adjcount) + "\t" + str(adjratio) )
            else:
                print(word + "\t" + word2 + "\t" + str(score) + "\t" + str(jointcount))




if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = foliasplitcgnpostags
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import glob
import sys
import os


if __name__ == "__main__":
    sys.path.append(sys.path[0] + '/../..')
    os.environ['PYTHONPATH'] = sys.path[0] + '/../..'

from pynlpl.formats import folia
from pynlpl.formats import cgn
import lxml.etree

def process(target):
    print "Processing " + target
    if os.path.isdir(target):
        print "Descending into directory " + target
        for f in glob.glob(target + '/*'):
            process(f)
    elif os.path.isfile(target) and target[-4:] == '.xml':            
        print "Loading " + target
        try:
            doc = folia.Document(file=target)
        except lxml.etree.XMLSyntaxError:
            print >>sys.stderr, "UNABLE TO LOAD " + target + " (XML SYNTAX ERROR!)"
            return None
        changed = False
        for word in doc.words():
            try:
                pos = word.annotation(folia.PosAnnotation)                
            except folia.NoSuchAnnotation:
                continue
            try:
                word.replace( cgn.parse_cgn_postag(pos.cls) )
                changed = True
            except cgn.InvalidTagException:
                print >>sys.stderr, "WARNING: INVALID TAG " + pos.cls
                continue
        if changed:
            print "Saving..."
            doc.save()

target = sys.argv[1]
process(target)
   

########NEW FILE########
__FILENAME__ = freqlist
#!/usr/bin/env python
#-*- coding:utf-8 -*-

###############################################################
#  PyNLPl - Frequency List Generator
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#
#       Licensed under GPLv3
#
###############################################################


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

import getopt
import sys
import codecs

from pynlpl.statistics import FrequencyList, Distribution
from pynlpl.textprocessors import Windower, crude_tokenizer

def usage():
    print("freqlist.py -n 1  file1 (file2) etc..",file=sys.stderr)
    print("\t-n number   n-gram size (default: 1)",file=sys.stderr)
    print("\t-i          case-insensitve",file=sys.stderr)
    print("\t-e encoding (default: utf-8)",file=sys.stderr)

def main():
    try:
        opts, files = getopt.getopt(sys.argv[1:], "hn:ie:", ["help"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err),file=sys.stderr)
        usage()
        sys.exit(2)

    testsetsize = devsetsize = 0
    casesensitive = True
    encoding = 'utf-8'
    n = 1

    for o, a in opts:
        if o == "-n":
            n = int(a)
        elif o == "-i":
            casesensitive =  False
        elif o == "-e":
            encoding = a
        else:
            print("ERROR: Unknown option:",o,file=sys.stderr)
            sys.exit(1)

    if not files:
        print >>sys.stderr, "No files specified"
        sys.exit(1)

    freqlist = FrequencyList(None, casesensitive)
    for filename in files:
        f = codecs.open(filename,'r',encoding)
        for line in f:
            if n > 1:
                freqlist.append(Windower(crude_tokenizer(line),n))
            else:
                freqlist.append(crude_tokenizer(line))

        f.close()

    dist = Distribution(freqlist)
    for type, count in freqlist:
        if isinstance(type,tuple) or isinstance(type,list):
            type = " ".join(type)
        s =  type + "\t" + str(count) + "\t" + str(dist[type]) + "\t" + str(dist.information(type))
        print(s)

    print("Tokens:           ", freqlist.tokens(),file=sys.stderr)
    print("Types:            ", len(freqlist),file=sys.stderr)
    print("Type-token ratio: ", freqlist.typetokenratio(),file=sys.stderr)
    print("Entropy:          ", dist.entropy(),file=sys.stderr)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = frogwrapper
#!/usr/bin/env python
#-*- coding:utf-8 -*-


#Frog Wrapper with XML input and FoLiA output support

import getopt
import lxml.etree
import sys
import os
import codecs

if __name__ == "__main__":
    sys.path.append(sys.path[0] + '/../..')
    os.environ['PYTHONPATH'] = sys.path[0] + '/../..'


import pynlpl.formats.folia as folia
from pynlpl.clients.frogclient import FrogClient

def legacyout(i, word,lemma,morph,pos):
    if word:
        out = str(i + 1) + "\t" + word + "\t" + lemma + "\t" + morph + "\t" + pos
        print out.encode('utf-8')
    else:
        print

def usage():
    print >>sys.stderr,"frogwrapper.py  [options]"
    print >>sys.stderr,"------------------------------------------------------"
    print >>sys.stderr,"Input file:"
    print >>sys.stderr,"\t--txt=[file]       Plaintext input"
    print >>sys.stderr,"\t--xml=[file]       XML Input"        
    print >>sys.stderr,"\t--folia=[file]     FoLiA XML Input"
    print >>sys.stderr,"Frog settings:"
    print >>sys.stderr,"\t-p [port]          Port the Frog server is running on"    
    print >>sys.stderr,"Output type:"
    print >>sys.stderr,"\t--id=[ID]          ID for outputted FoLiA XML Document"
    print >>sys.stderr,"\t--legacy           Use legacy columned output instead of FoLiA"
    print >>sys.stderr,"\t-o                 Write output to input file (only works for --folia)"
    print >>sys.stderr,"XML Input:"
    print >>sys.stderr,"\t--selectsen=[expr] Use xpath expression to select sentences"
    print >>sys.stderr,"\t--selectpar=[expr] Use xpath expression to select paragraphs"
    print >>sys.stderr,"\t--idattrib=[attrb] Copy ID from this attribute"
    print >>sys.stderr,"Text Input:"
    print >>sys.stderr,"\t-N                 No structure"
    print >>sys.stderr,"\t-S                 One sentence per line (strict)"
    print >>sys.stderr,"\t-P                 One paragraph per line"
    print >>sys.stderr,"\t-I                 Value in first column (tab seperated) is ID!"
    print >>sys.stderr,"\t-E [encoding]      Encoding of input file (default: utf-8)"
    
try:
    opts, files = getopt.getopt(sys.argv[1:], "hSPINEp:o", ["txt=","xml=", "folia=","id=",'legacy','tok','selectsen=','selectpar=','idattrib='])
except getopt.GetoptError, err:
    # print help information and exit:
    print str(err)
    usage()
    sys.exit(1)


textfile = xmlfile = foliafile = None
foliaid = 'UNTITLED'
legacy = None
tok = False
idinfirstcolumn = False
encoding = 'utf-8'
mode='s'
xpathselect = ''
idattrib=''
port = None
save = False 

for o, a in opts:
    if o == "-h":
        usage()
        sys.exit(0)
    elif o == "-I":
        idinfirstcolumn = True
    elif o == "-S":
        mode = 's'
    elif o == "-P":
        mode = 'p'
    elif o == "-p":        
        port = int(a)
    elif o == "-N":
        mode = 'n'
    elif o == "-E":
        encoding = a
    elif o == "--selectsen":
        mode='s'
        xpathselect = a
    elif o == "--selectpar":
        mode='p'
        xpathselect = a
    elif o == "--idattrib":
        idattrib = a
    elif o == "--txt":
        textfile = a
    elif o == "--xml":
        xmlfile = a
    elif o == "--folia":
        foliafile = a
    elif o == "--id":
        foliaid = a #ID
    elif o == "-o":
        save = True
    elif o == "--legacy":
        legacy = True
    elif o == "--tok":
        tok = True
    else:
        print >>sys.stderr, "ERROR: Unknown option:",o
        sys.exit(1)
        
if not port:
    print >> sys.stderr,"ERROR: No port specified to connect to Frog server"    
    sys.exit(2)
elif (not textfile and not xmlfile and not foliafile):
    print >> sys.stderr,"ERROR: Specify a file with either --txt, --xml or --folia"
    sys.exit(2)
elif xmlfile and not xpathselect:
    print >> sys.stderr,"ERROR: You need to specify --selectsen or --selectpar when using --xml"
    sys.exit(2)

frogclient = FrogClient('localhost',port)

idmap = []
data = []

if textfile:
    f = codecs.open(textfile, 'r', encoding)
    for line in f.readlines():
        if idinfirstcolumn:
            id, line = line.split('\t',1)
            idmap.append(id.strip())
        else:
            idmap.append(None)
        data.append(line.strip())        
    f.close()
        
if xmlfile:
    xmldoc = lxml.etree.parse(xmlfile)
    for node in xmldoc.xpath(xpathselect):
        if idattrib:
            if idattrib in node.attrib:
                idmap.append(node.attrib[idattrib])
            else:
                print >>sys.stderr,"WARNING: Attribute " + idattrib + " not found on node!"
                idmap.append(None)
        else:
            idmap.append(None)
        data.append(node.text)
        
if foliafile:
    foliadoc = folia.Document(file=foliafile)
    if not foliadoc.declared(folia.AnnotationType.TOKEN):
        foliadoc.declare(folia.AnnotationType.TOKEN, set='http://ilk.uvt.nl/folia/sets/ucto-nl.foliaset', annotator='Frog',annotatortype=folia.AnnotatorType.AUTO)
    if not foliadoc.declared(folia.AnnotationType.POS):        
        foliadoc.declare(folia.AnnotationType.POS, set='http://ilk.uvt.nl/folia/sets/cgn-legacy.foliaset', annotator='Frog',annotatortype=folia.AnnotatorType.AUTO)
    if not foliadoc.declared(folia.AnnotationType.LEMMA):                
        foliadoc.declare(folia.AnnotationType.LEMMA, set='http://ilk.uvt.nl/folia/sets/mblem-nl.foliaset', annotator='Frog',annotatortype=folia.AnnotatorType.AUTO)        
    foliadoc.language('nld')    
    text = foliadoc.data[-1]
    
    for p in foliadoc.paragraphs():    
        found_s = False  
        for s in p.sentences():
            found_w = False
            for w in s.words():
                found_w = True
            found_s = True
            if found_w:
                #pass tokenised sentence
                words = s.words()
                response = frogclient.process(" ".join([unicode(w) for w in words]))
                for i, (word, lemma, morph, pos) in enumerate(response):
                    if legacy: legacyout(i,word,lemma,morph,pos)                    
                    if unicode(words[i]) == word:
                        if lemma:
                            words[i].append( folia.LemmaAnnotation(foliadoc, cls=lemma) )
                        if pos:
                            words[i].append( folia.PosAnnotation(foliadoc, cls=pos) )  
                    else:
                        print >>sys.stderr,"WARNING: Out of sync after calling Frog! ", i, word
                    
            else:
                #pass untokenised sentence
                try:
                    sentext = s.text()
                except folia.NoSuchText:
                    continue
                response = frogclient.process(sentext)
                for i, (word, lemma, morph, pos) in enumerate(response):
                    if legacy: legacyout(i,word,lemma,morph,pos)                             
                    if word:
                        w = folia.Word(foliadoc, text=word, generate_id_in=s)                                                
                        if lemma:
                            w.append( folia.LemmaAnnotation(foliadoc, cls=lemma) ) 
                        if pos:
                            w.append( folia.PosAnnotation(foliadoc, cls=pos) )  
                        s.append(w) 
                
            if not found_s:
                #pass paragraph
                try:
                    partext = p.text()
                except folia.NoSuchText:
                    continue
                    
                s = folia.Sentence(foliadoc, generate_id_in=p)         
                response = frogclient.process(partext)
                for i, (word, lemma, morph, pos) in enumerate(response):
                    if (not word or i == len(response) - 1) and len(s) > 0:
                        #gap or end of response: terminate sentence      
                        p.append(s)
                        s = folia.Sentence(foliadoc, generate_id_in=p)         
                    elif word:
                        w = folia.Word(foliadoc, text=word, generate_id_in=s)                                                
                        if lemma:
                            w.append( folia.LemmaAnnotation(foliadoc, cls=lemma) ) 
                        if pos:
                            w.append( folia.PosAnnotation(foliadoc, cls=pos) )  
                        s.append(w) 
            
    
else:        
    foliadoc = folia.Document(id=foliaid)
    foliadoc.declare(folia.AnnotationType.TOKEN, set='http://ilk.uvt.nl/folia/sets/ucto-nl.foliaset', annotator='Frog',annotatortype=folia.AnnotatorType.AUTO)
    foliadoc.declare(folia.AnnotationType.POS, set='http://ilk.uvt.nl/folia/sets/cgn-legacy.foliaset', annotator='Frog',annotatortype=folia.AnnotatorType.AUTO)
    foliadoc.declare(folia.AnnotationType.LEMMA, set='http://ilk.uvt.nl/folia/sets/mblem-nl.foliaset', annotator='Frog',annotatortype=folia.AnnotatorType.AUTO)
    foliadoc.language('nld')
    text = folia.Text(foliadoc, id=foliadoc.id + '.text.1') 
    foliadoc.append(text)


    curid = None
    for (fragment, id) in zip(data,idmap):
        if mode == 's' or mode == 'n':
            if id:
                s = folia.Sentence(foliadoc, id=id)            
            else:
                s = folia.Sentence(foliadoc, generate_id_in=text) 
        elif mode == 'p':
            if id:
                p = folia.Paragraph(foliadoc, id=id)            
            else:
                p = folia.Paragraph(foliadoc, generate_id_in=text) 
            s = folia.Sentence(foliadoc, generate_id_in=p)         
        
        curid = s.id
        response = frogclient.process(fragment)
        for i, (word, lemma, morph, pos) in enumerate(response):
            if legacy: 
                legacyout(i,word,lemma,morph,pos)                
                continue
                
            if word:
                w = folia.Word(foliadoc, text=word, generate_id_in=s)                                                
                if lemma:
                    w.append( folia.LemmaAnnotation(foliadoc, cls=lemma) ) 
                if pos:
                    w.append( folia.PosAnnotation(foliadoc, cls=pos) )  
                s.append(w)
            if (not word or i == len(response) - 1) and len(s) > 0:
                #gap or end of response: terminate sentence
                if mode == 'p':
                    p.append(s)
                    if (i == len(response) - 1):
                        text.append(p)                    
                elif mode == 'n' or (mode == 's' and i == len(response) - 1):
                    text.append(s)
                elif mode == 's':
                    continue
                    
                if i < len(response) - 1: #not done yet?
                    #create new sentence
                    if mode == 'p':                        
                        s = folia.Sentence(foliadoc, generate_id_in=p)
                    elif mode == 'n' and id:
                        #no id for this unforeseen sentence, make something up
                        s = folia.Sentence(foliadoc, id=curid+'.X')           
                        print >>sys.stderr,"WARNING: Sentence found that was not in original"                     

if not legacy:
    print foliadoc.xmlstring()
if save and foliafile:
    foliadoc.save()

########NEW FILE########
__FILENAME__ = phrasetableserver
#!/usr/bin/env python
#-*- coding:utf-8 -*-

###############################################################
#  PyNLPl - Phrase Table Server
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#
#       Licensed under GPLv3
#
###############################################################   


import sys
import os

if __name__ == "__main__":
    sys.path.append(sys.path[0] + '/../..')
    os.environ['PYTHONPATH'] = sys.path[0] + '/../..'
    
from pynlpl.formats.moses import PhraseTable, PhraseTableServer




if len(sys.argv) != 3:
    print >>sys.stderr,"Syntax: phrasetableserver.py phrasetable port"
    sys.exit(2)
else:    
    port = int(sys.argv[2])
    PhraseTableServer(PhraseTable(sys.argv[1]), port)

########NEW FILE########
__FILENAME__ = reflow
#! /usr/bin/env python
# -*- coding: utf8 -*-


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

import sys
import io
import getopt

from pynlpl.textprocessors import ReflowText


def main():
    for filename in sys.argv[1:]:
        f = io.open(filename, 'r', encoding='utf-8')
        for line in ReflowText(f):
            print(line)
        f.close()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = sampler
#!/usr/bin/env python
#-*- coding:utf-8 -*-

###############################################################
#  PyNLPl - Sampler
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#
#       Licensed under GPLv3
#
# This tool can be used to split a file (or multiple interdependent
# files, such as a parallel corpus) into a train, test and development
# set.
#
###############################################################


from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

import getopt
import sys

import random
from pynlpl.evaluation import filesampler


def usage():
    print("sampler.py [ -t testsetsize ] [ -d devsetsize ] [ -S seed] file1 (file2) etc..",file=sys.stderr)
    print("\tNote: testsetsize and devsetsize may be fractions (< 1) or absolute (>=1)",file=sys.stderr)

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ht:d:S:", ["help"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err),file=sys.stderr)
        usage()
        sys.exit(2)

    testsetsize = devsetsize = 0

    for o, a in opts:
        if o == "-t":
            try:
                testsetsize = int(a)
            except:
                try:
                    testsetsize = float(a)
                except:
                    print("ERROR: Invalid testsize",file=sys.stderr)
                    sys.exit(2)
        elif o == "-d":
            try:
                devsetsize = int(a)
            except:
                try:
                    devsetsize = float(a)
                except:
                    print("ERROR: Invalid devsetsize",file=sys.stderr)
                    sys.exit(2)
        elif o == "-S":
            random.seed(int(a))
        elif o == "-h":
            usage()
            sys.exit(0)
        else:
            print("ERROR: No such option: ",o,file=sys.stderr)
            sys.exit(2)

    if testsetsize == 0:
        print("ERROR: Specify at least a testset size!",file=sys.stderr)
        usage()
        sys.exit(2)
    elif len(args) == 0:
        print("ERROR: Specify at least one file!",file=sys.stderr)
        usage()
        sys.exit(2)

    filesampler(args, testsetsize, devsetsize)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = sonar2folia
#!/usr/bin/env python
#-*- coding:utf-8 -*-

#---------------------------------------------------------------
# PyNLPl - Conversion script for converting SoNaR/D-Coi from D-Coi XML to FoLiA XML
#   by Maarten van Gompel, ILK, Tilburg University
#   http://ilk.uvt.nl/~mvgompel
#   proycon AT anaproy DOT nl
#
#   Licensed under GPLv3
#
#----------------------------------------------------------------

# Usage: sonar2folia.py sonar-input-dir output-dir nr-of-threads

import sys
import os

if __name__ == "__main__":
    sys.path.append(sys.path[0] + '/../..')
    os.environ['PYTHONPATH'] = sys.path[0] + '/../..'

import pynlpl.formats.folia as folia
import pynlpl.formats.sonar as sonar
from multiprocessing import Pool, Process
import datetime
import codecs


def process(data):
    i, filename = data
    category = os.path.basename(os.path.dirname(filename))
    progress = round((i+1) / float(len(index)) * 100,1)    
    print "#" + str(i+1) + " " + filename + ' ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' +  str(progress) + '%'
    try:
        doc = folia.Document(file=filename)
    except Exception as e:
        print >> sys.stderr,"ERROR loading " + filename + ":" + str(e)
        return False
    filename = filename.replace(sonardir,'')
    if filename[0] == '/':
        filename = filename[1:]
    if filename[-4:] == '.pos':
        filename = filename[:-4]
    if filename[-4:] == '.tok':
        filename = filename[:-4]    
    if filename[-4:] == '.ilk':
        filename = filename[:-4]    
    #Load document prior to tokenisation
    try:
        pretokdoc = folia.Document(file=sonardir + '/' + filename)
    except:
        print >> sys.stderr,"WARNING unable to load pretokdoc " + filename
        pretokdoc = None
    if pretokdoc:
        for p2 in pretokdoc.paragraphs():
            try:
                p = doc[p2.id]        
            except:
                print >> sys.stderr,"ERROR: Paragraph " + p2.id + " not found. Tokenised and pre-tokenised versions out of sync?"
                continue
            if p2.text:
                p.text = p2.text                     
    try:
        os.mkdir(foliadir + os.path.dirname(filename))
    except:
        pass
        
    try:        
        doc.save(foliadir + filename)
    except:
        print >> sys.stderr,"ERROR saving " + foliadir + filename
    
    try:
        f = codecs.open(foliadir + filename.replace('.xml','.tok.txt'),'w','utf-8')
        f.write(unicode(doc))    
        f.close()        
    except:
        print >> sys.stderr,"ERROR saving " + foliadir + filename.replace('.xml','.tok.txt')

            
    sys.stdout.flush()
    sys.stderr.flush()
    return True
    
def outputexists(filename, sonardir, foliadir):
    filename = filename.replace(sonardir,'')
    if filename[0] == '/':
        filename = filename[1:]
    if filename[-4:] == '.pos':
        filename = filename[:-4]
    if filename[-4:] == '.tok':
        filename = filename[:-4]    
    if filename[-4:] == '.ilk':
        filename = filename[:-4]     
    return os.path.exists(foliadir + filename)


if __name__ == '__main__':    
    sonardir = sys.argv[1]
    foliadir = sys.argv[2]
    threads = int(sys.argv[3])
    if foliadir[-1] != '/': foliadir += '/'
    try:
        os.mkdir(foliadir[:-1])
    except:
        pass
            
    print "Building index..."
    index = list(enumerate([ x for x in sonar.CorpusFiles(sonardir,'pos', "", lambda x: True, True) if not outputexists(x, sonardir, foliadir) ]))

    print "Processing..."
    p = Pool(threads)
    p.map(process, index )


########NEW FILE########
__FILENAME__ = sonarfreqlist
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import os

if __name__ == "__main__":
    sys.path.append(sys.path[0] + '/../..')
    os.environ['PYTHONPATH'] = sys.path[0] + '/../..'

from pynlpl.formats.sonar import CorpusFiles, Corpus
from pynlpl.statistics import FrequencyList

sonardir = sys.argv[1]


freqlist = FrequencyList()
lemmapos_freqlist = FrequencyList()
poshead_freqlist = FrequencyList()
pos_freqlist = FrequencyList()

for i, doc in enumerate(Corpus(sonardir)):
    print >>sys.stderr, "#" + str(i) + " Processing " + doc.filename
    for word, id, pos, lemma in doc:
        freqlist.count(word)
        if lemma and pos:
            poshead = pos.split('(')[0]
            lemmapos_freqlist.count(lemma+'.'+poshead)
            poshead_freqlist.count(poshead)
            pos_freqlist.count(pos)

freqlist.save('sonarfreqlist.txt')
lemmapos_freqlist.save('sonarlemmaposfreqlist.txt')
poshead_freqlist.save('sonarposheadfreqlist.txt')
pos_freqlist.save('sonarposfreqlist.txt')

            
print unicode(freqlist).encode('utf-8')

########NEW FILE########
__FILENAME__ = sonarlemmafreqlist
#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import os

if __name__ == "__main__":
    sys.path.append(sys.path[0] + '/../..')
    os.environ['PYTHONPATH'] = sys.path[0] + '/../..'

from pynlpl.formats.sonar import CorpusFiles, Corpus
from pynlpl.statistics import FrequencyList

sonardir = sys.argv[1]

freqlist = FrequencyList()
lemmapos_freqlist = FrequencyList()
poshead_freqlist = FrequencyList()
pos_freqlist = FrequencyList()

for i, doc in enumerate(Corpus(sonardir)):
    print >>sys.stderr, "#" + str(i) + " Processing " + doc.filename
    for word, id, pos, lemma in doc:
        freqlist.count(word)
        if lemma and pos:
            poshead = pos.split('(')[0]
            lemmapos_freqlist.count(lemma+'.'+poshead)
            poshead_freqlist.count(poshead)
            pos_freqlist.count(pos)
      
freqlist.save('sonarfreqlist.txt')
lemmapos_freqlist.save('sonarlemmaposfreqlist.txt')
poshead_freqlist.save('sonarposheadfreqlist.txt')
pos_freqlist.save('sonarposfreqlist.txt')
            
print unicode(freqlist).encode('utf-8')

########NEW FILE########
__FILENAME__ = timbl_distr_stats
#!/usr/bin/env python
#-*- coding:utf-8 -*-

###############################################################
#  PyNLPl - Frequency List Generator
#       by Maarten van Gompel (proycon)
#       http://ilk.uvt.nl/~mvgompel
#       Induction for Linguistic Knowledge Research Group
#       Universiteit van Tilburg
#
#       Licensed under GPLv3
#
###############################################################   

from pynlpl.formats.timbl import TimblOutput
from pynlpl.statistics import mean,mode,median
import sys
import os


print "Filename          \tmax\tmin\tmean\tmedian\tmode"
for filename in sys.argv[1:]:
    observations = []
    for _,_,_,distribution in TimblOutput(open(filename,'r')):
        observations.append(len(distribution))
    print os.path.basename(filename) + "\t" + str(max(observations)) + "\t" + str(min(observations)) + "\t"  + str(mean(observations)) + "\t" + str(median(observations)) + "\t" + str(mode(observations))

########NEW FILE########
__FILENAME__ = web
import sys
if sys.version == '3':
    raise ImportError("Pattern does not yet support Python 3")
from pattern.web import Google, Bing, plaintext


def bingcorpsearch(word,concfilter = '', extraquery='',license=None, start=1, count=50):
    """Searches the web for sentences containing a certain keyword, and possibly a co-occurence word. Generator yielding (leftcontext,word,rightcontext,url) tuples.
       First queries Google, and then retrieves the pages of the top search results.
       Uses 'pattern' (CLiPS, Antwerpen University)
       """
    if not concfilter:
        query = word
    else:
        query = word + ' ' + concfilter
    if extraquery:
       query += ' ' + extraquery

    engine = Bing(license=license)
        
    processed = {}
    
    for result in engine.search(query, start=start,count=count):
        if not result.url in processed:
            processed[result.url] = True
            try:
                content = plaintext(result.download())
            except:
                continue
                
            begin = 0
            wordindex = None
            wordlength = 0
            concindex = None            
            for i in range(1,len(content)):
                if content[i] == '.' or content[i] == '?' or content[i] == '!' or content[i] == '\n':
                    if wordindex >= begin and ((concfilter and concindex >= begin) or (not concfilter)):
                        if len(content[begin:wordindex].strip()) > 5 or len(content[wordindex+wordlength:i+1].strip()) > 5:
                            yield (content[begin:wordindex].strip(), content[wordindex:wordindex+wordlength].strip(), content[wordindex+wordlength:i+1], result.url)
                    wordindex = concindex = None
                    begin = i + 1
                if len(word)+i <= len(content) and content[i:i+len(word)].lower() == word.lower():
                    wordindex = i
                    wordlength = len(word)
                    for j in range(len(word),len(content)):                        
                        if i+j < len(content) and (content[i+j] == ' ' or  content[i+j] == '?' or content[i+j] == '!' or content[i+j] == '\n'):
                            wordlength = j
                            break                                                                
                if concfilter and content[i:len(concfilter)].lower() == concfilter.lower():
                    concindex = i


def googlecorpsearch(word,concfilter = '', extraquery='',license=None, start=1, count=8):
    """Searches the web for sentences containing a certain keyword, and possibly a co-occurence word. Generator yielding (leftcontext,word,rightcontext,url) tuples.
       First queries Google, and then retrieves the pages of the top search results.
       Uses 'pattern' (CLiPS, Antwerpen University)
       """
    if not concfilter:
        query = 'allintext: ' + word 
    else:
        query = 'allintext: "' + word + ' * ' + concfilter + '" OR "' + concfilter + ' * ' + word + '"'
    if extraquery:
        query += ' ' + extraquery
        

    engine = Google(license=license)
        
    processed = {}
    
    for result in engine.search(query, start=start,count=count):
        if not result.url in processed:
            processed[result.url] = True
            try:
                content = plaintext(result.download())
            except:
                continue
                
            begin = 0
            wordindex = None
            wordlength = 0
            concindex = None            
            for i in range(1,len(content)):
                if content[i] == '.' or content[i] == '?' or content[i] == '!' or content[i] == '\n':
                    if wordindex >= begin and ((concfilter and concindex >= begin) or (not concfilter)):
                        if len(content[begin:wordindex].strip()) > 5 or len(content[wordindex+wordlength:i+1].strip()) > 5:
                            yield (content[begin:wordindex].strip(), content[wordindex:wordindex+wordlength].strip(), content[wordindex+wordlength:i+1], result.url)
                    wordindex = concindex = None
                    begin = i + 1
                if len(word)+i <= len(content) and content[i:i+len(word)].lower() == word.lower():
                    wordindex = i
                    wordlength = len(word)
                    for j in range(len(word),len(content)):                        
                        if i+j < len(content) and (content[i+j] == ' ' or  content[i+j] == '?' or content[i+j] == '!' or content[i+j] == '\n'):
                            wordlength = j
                            break                                                                
                if concfilter and content[i:len(concfilter)].lower() == concfilter.lower():
                    concindex = i

########NEW FILE########
