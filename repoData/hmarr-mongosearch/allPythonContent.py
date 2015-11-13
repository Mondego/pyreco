__FILENAME__ = searchfeeds
#!/usr/bin/env python

import sys
import os
import time
from operator import itemgetter
from heapq import nlargest
from mongoengine.document import Document
from mongoengine import fields, connect
import feedparser

sys.path.insert(0, '..')

import mongosearch


class BlogPost(Document):
    """A sample blog post document that will be indexed and searched. The title
    is more important than the content so should be weighted higher.
    """
    title = fields.StringField()
    content = fields.StringField()


def get_feed_entries(feed_path):
    """Parse the individual items out of a locally-stored RSS feed.
    """
    document = feedparser.parse(feed_path)

    entries = {}
    for entry in document.entries:
        guid = entry.get('guid') or entry.get('link')
        if guid in entries:
            continue

        # Use content if summary is not present
        summary = entry.get('summary')
        if not summary:
            summary = entry.get('content', [{}])[0].get('value', '')

        entries[guid] = (entry.title, summary)

    return entries

def quit_with_usage():
    print >> sys.stderr, 'Usage: %s <query>' % sys.argv[0]
    sys.exit(1)

def main():
    try:
        query = ' '.join(sys.argv[1:])
    except IndexError:
        quit_with_usage()

    if not query.strip():
        quit_with_usage()

    connect('mongosearch-example')

    # Ensure that no data exists from a previous run of this example
    BlogPost.drop_collection()

    # Create an index for the blog post and add the fields to be indexed
    index = mongosearch.SearchIndex(BlogPost)
    index.add_field('title', html=True, weight=1.5)
    index.add_field('content', html=True)

    # In this example we are loading our test data from downloaded RSS feeds
    # in the 'data' directory
    feeds = ['df.xml', 'register.atom', 'github.xml']
    feed_paths = [os.path.join('fixtures', feed) for feed in feeds]
    for feed_path in feed_paths:
        # Parse the feed and save it to the DB
        entries = get_feed_entries(feed_path)
        for guid, entry in entries.items():
            post = BlogPost(title=entry[0], content=entry[1])
            post.save()

    # Index the collection
    t0 = time.time()
    index.generate_index()
    print 'Indexing took %s seconds' % (time.time() - t0)

    # Query the collection
    t0 = time.time()
    results = index.search(query)
    top_matches = nlargest(10, results.iteritems(), itemgetter(1))
    time_taken = time.time() - t0
    print 'Querying took %s seconds' % time_taken

    # Write the results to results.htm as HTML
    outfile = open('results.htm', 'w')
    outfile.write('<html><head><style>body{font-size: 70%;}</style>')
    outfile.write('<meta http-equiv="Content-Type" content="text/html; ')
    outfile.write('charset=UTF-8"/>')
    outfile.write('</head><body>')
    outfile.write('<h1>Search results for "%s"</h1>' % query)
    outfile.write('<p><em>Query took %s seconds</em></p>' % time_taken)
    for doc_id, score in top_matches:
        doc = BlogPost.objects(id=doc_id).first()
        outfile.write('<h2>[%s] %s</h2>' % (score, doc.title.encode('utf8')))
        outfile.write('<p>%s</p>' % doc.content.encode('utf8'))
        outfile.write('<br />')
    outfile.write('</body></html>')

    print 'Processed %s items' % BlogPost.objects.count()

    print 'Results saved in results.htm'

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = mongosearch
import re
from itertools import groupby
from operator import itemgetter
from math import log

import lxml.html
from Stemmer import Stemmer
from mongoengine.document import Document, EmbeddedDocument
from mongoengine import fields

STOP_WORDS = (
    "a,able,about,across,after,all,almost,also,am,among,an,and,any,are,as,at,"
    "be,because,been,but,by,can,cannot,could,dear,did,do,does,either,else,"
    "ever,every,for,from,get,got,had,has,have,he,her,hers,him,his,how,however,"
    "i,if,in,into,is,it,its,just,least,let,like,likely,may,me,might,most,must,"
    "my,neither,no,nor,not,of,off,often,on,only,or,other,our,own,rather,said,"
    "say,says,she,should,since,so,some,than,that,the,their,them,then,there,"
    "these,they,this,tis,to,too,twas,us,wants,was,we,were,what,when,where,"
    "which,while,who,whom,why,will,with,would,yet,you,your"
).split(',')


class SearchTerm(EmbeddedDocument):
    """A term linked to its weight - one of these is stored for each term in
    each document. The weight 
    """
    term = fields.StringField(db_field='t')
    weight = fields.FloatField(db_field='w')
    meta = {'allow_inheritance': False}


class SearchIndex(object):

    SEARCH_JS = """
    function() {
        var results = {};
        // Iterate over each document to calculate the document's score
        db[collection].find(query).forEach(function(doc) {
            var score = 0;
            // Iterate over each term in the document, calculating the 
            // score for the term, which will be added to the doc's score
            doc[~terms].forEach(function(term) {
                // Only look at the term if it is part of the query
                if (options.queryTerms.indexOf(term[~terms.term]) != -1) {
                    // The meat of the BM25 ranking function
                    // (See http://en.wikipedia.org/wiki/Okapi_BM25)
                    //
                    // term.w (weight) is equivalent to the term's 
                    // frequency in the document
                    //
                    // f(qi, D) * (k1 + 1)
                    var dividend = term[~terms.weight] * (options.k + 1);
                    // |D| / avgdl
                    var relDocSize = doc.length / options.avgDocLength;
                    // (1 - b + b * |D| / avgdl)
                    var divisor = 1.0 - options.b + options.b * relDocSize;
                    // f(qi, D) + k1 * (1 - b + b * |D| / avgdl)
                    divisor = term[~terms.weight] + divisor * options.k
                    // Divide the top half by the bottom half
                    var termScore = dividend / divisor;
                    // Then scale by the inverse document frequency
                    termScore *= options.idfs[term[~terms.term]];
                    // The document's score is the sum of its terms scores
                    score += termScore;
                }
            });
            results[doc[~doc_id]] = score;
        });
        return results;
    }
    """
    
    def __init__(self, document, use_term_index=True):
        self.document = document
        # Make index document for the document provided
        index_meta = {
            'allow_inheritance': False,
            'collection': '%sindex' % document._meta['collection'],
        }
        if use_term_index:
            index_meta['indexes'] = ['terms.term']

        class DocumentIndex(Document):
            doc_id = fields.StringField(primary_key=True)
            terms = fields.ListField(fields.EmbeddedDocumentField(SearchTerm))
            length = fields.IntField()
            meta = index_meta

        self.document_index = DocumentIndex
        self.fields = {}

    def add_field(self, name, weight=1.0, html=False):
        self.fields[name] = {'weight': weight, 'html': html}

    def get_queryset(self, document):
        return document.objects

    def generate_index(self):
        """Generate the index for the indexed collection. This will remove any
        existing index, and regenerate everything from scratch.
        """
        # Reset the index as we are regenerating it from scratch
        self.document_index.drop_collection()
        # Add an index entry for each document
        for doc in self.get_queryset(self.document):
            self.add_to_index(doc)

    def add_to_index(self, doc):
        """Add an individual document to the index.
        """
        terms = []
        for field_name, field_settings in self.fields.items():
            # Make sure the value is actually a string
            if isinstance(doc[field_name], basestring):
                if field_settings['html']:
                    field_terms = self._prepare_html(doc[field_name])
                else:
                    field_terms = self._prepare_text(doc[field_name])

                # Add terms for this field to the document's terms
                weight = field_settings['weight']
                for term in field_terms:
                    terms.append((term, weight))

        doc_len = len(terms)

        terms.sort(key=itemgetter(0))
        unique_terms = []
        for term, like_terms in groupby(terms, itemgetter(0)):
            # Combine the weights of like terms
            weight = sum(itemgetter(1)(t) for t in like_terms)
            unique_terms.append(SearchTerm(term=term, weight=weight))

        doc_index = self.document_index(doc_id=unicode(doc.id), 
                                        terms=unique_terms, length=doc_len)
        doc_index.save()

    def _prepare_html(self, html):
        """Strips tags, entities, etc, then tokenizes and stems content.
        """
        text = lxml.html.fromstring(html).text_content()
        return self._prepare_text(text)

    def _prepare_text(self, text):
        """Extracts and stems the words from some given text.
        """
        words = re.findall('[a-z0-9\']+', text.lower())
        words = [word for word in words if word not in STOP_WORDS]
        stemmer = Stemmer('english')
        stemmed_words = stemmer.stemWords(words)
        return stemmed_words

    def search(self, query, html=False):
        """Search the index using a text query.
        """
        # Tokenize query
        if html:
            query_terms = self._prepare_html(query)
        else:
            query_terms = self._prepare_text(query)
        
        # Calculate the inverse document frequency for each term
        idfs = {}
        num_docs = self.document_index.objects.count()
        for term in query_terms:
            term_docs = self.document_index.objects(terms__term=term).count()
            idfs[term] = log((num_docs - term_docs + 0.5) / (term_docs + 0.5))

        # Get the average document length
        avg_doc_length = self.document_index.objects.average('length')

        # Only look for documents that actually contain the terms
        query = self.document_index.objects(terms__term__in=query_terms)
        options = {
            'idfs': idfs,
            'avgDocLength': avg_doc_length, 
            'queryTerms': query_terms,
            # BM25 variables
            'k': 2.0,
            'b': 0.75,
        }
        results = query.exec_js(self.SEARCH_JS, 'doc_id', 'terms', **options)
        return results


########NEW FILE########
