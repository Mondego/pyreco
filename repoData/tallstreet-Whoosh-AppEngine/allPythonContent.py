__FILENAME__ = hello
import cgi

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from whoosh import store
from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.index import getdatastoreindex
from whoosh.qparser import QueryParser, MultifieldParser
import logging

SEARCHSCHEMA = Schema(content=TEXT(stored=True))


class MainPage(webapp.RequestHandler):
  def get(self):
    self.response.out.write('<html><body>')
    self.response.out.write("""
          <form action="/search" method="get">
            <div><input name="query" type="text" value=""><input type="submit" value="Search"></div>
          </form>
        </body>
      </html>""")     

    # Write the submission form and the footer of the page
    self.response.out.write("""
          <form action="/sign" method="post">
            <div><textarea name="content" rows="3" cols="60"></textarea></div>
            <div><input type="submit" value="Sign Guestbook"></div>
          </form>
        </body>
      </html>""")
      
class SearchPage(webapp.RequestHandler):
  def get(self):
    self.response.out.write('<html><body>')
    self.response.out.write("""
          <form action="/search" method="get">
            <div><input name="query" type="text" value=""><input type="submit" value="Search"></div>
          </form>
        </body>
      </html>""")       
    ix = getdatastoreindex("hello", schema=SEARCHSCHEMA)
    parser = QueryParser("content", schema = ix.schema)
    q = parser.parse(self.request.get('query'))
    results = ix.searcher().search(q)

    for result in results:
      self.response.out.write('<blockquote>%s</blockquote>' %
                              cgi.escape(result['content']))

    # Write the submission form and the footer of the page
    self.response.out.write("""
          <form action="/sign" method="post">
            <div><textarea name="content" rows="3" cols="60"></textarea></div>
            <div><input type="submit" value="Sign Guestbook"></div>
          </form>
        </body>
      </html>""")      

class Guestbook(webapp.RequestHandler):
  def post(self):
    ix = getdatastoreindex("hello", schema=SEARCHSCHEMA)
    writer = ix.writer()
    writer.add_document(content=u"%s" %  self.request.get('content'))
    writer.commit()
    self.redirect('/')

application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/search', SearchPage),
                                      ('/sign', Guestbook)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

########NEW FILE########
__FILENAME__ = analysis
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""
Classes and functions for turning a piece of text into
an indexable stream of "tokens" (usually equivalent to words). There are
three general types of classes/functions involved in analysis:

    - Tokenizers are always at the start of the text processing pipeline.
      They take a string and yield Token objects (actually, the same token
      object over and over, for performance reasons) corresponding to the
      tokens (words) in the text.
      
      Every tokenizer is a callable that takes a string and returns a
      generator of tokens.
      
    - Filters take the tokens from the tokenizer and perform various
      transformations on them. For example, the LowercaseFilter converts
      all tokens to lowercase, which is usually necessary when indexing
      regular English text.
      
      Every filter is a callable that takes a token generator and returns
      a token generator.
      
    - Analyzers are convenience functions/classes that "package up" a
      tokenizer and zero or more filters into a single unit, so you
      don't have to construct the tokenizer-filter-filter-etc. pipeline
      yourself. For example, the StandardAnalyzer combines a RegexTokenizer,
      LowercaseFilter, and StopFilter.
    
      Every analyzer is a callable that takes a string and returns a
      token generator. (So Tokenizers can be used as Analyzers if you
      don't need any filtering).
"""

import copy, re

from whoosh.lang.porter import stem

# Default list of stop words (words so common it's usually
# wasteful to index them). This list is used by the StopFilter
# class, which allows you to supply an optional list to override
# this one.

STOP_WORDS = frozenset(("the", "to", "of", "a", "and", "is", "in", "this",
                        "you", "for", "be", "on", "or", "will", "if", "can", "are",
                        "that", "by", "with", "it", "as", "from", "an", "when",
                        "not", "may", "tbd", "us", "we", "yet"))


# Utility functions

def unstopped(tokenstream):
    """Removes tokens from a token stream where token.stopped = True."""
    return (t for t in tokenstream if not t.stopped)


# Token object

class Token(object):
    """
    Represents a "token" (usually a word) extracted from the source text
    being indexed.
    
    Because object instantiation in Python is slow, tokenizers should create
    ONE SINGLE Token object and YIELD IT OVER AND OVER, changing the attributes
    each time.
    
    This trick means that consumers of tokens (i.e. filters) must
    never try to hold onto the token object between loop iterations, or convert
    the token generator into a list.
    Instead, save the attributes between iterations, not the object::
    
        def RemoveDuplicatesFilter(self, stream):
            # Removes duplicate words.
            lasttext = None
            for token in stream:
                # Only yield the token if its text doesn't
                # match the previous token.
                if lasttext != token.text:
                    yield token
                lasttext = token.text
    
    The Token object supports the following attributes:
    
        - text (string): The text of this token.
        - original (string): The original text of the token, set by the tokenizer
          and never modified by filters.
        - positions (boolean): whether this token contains a position. If this
          is True, the 'pos' attribute should be set to the index of the token
          (e.g. for the first token, pos = 0, for the second token, pos = 1, etc.)
        - chars (boolean): whether this token contains character offsets. If this
          is True, the 'startchar' and 'endchar' attributes should be set to the
          starting character offset and the ending character offset of this token.
        - stopped (boolean): whether this token has been stopped by a stop-word
          filter (not currently used).
        - boosts (boolean): whether this token contains a per-token boost. If this
          is True, the 'boost' attribute should be set to the current boost factor.
        - removestops (boolean): whether stopped tokens should be removed from
          the token stream. If this is true, the 'stopped' attribute will indicate
          whether the current token is a "stop" word.
    """
    
    def __init__(self, positions = False, chars = False, boosts = False, removestops = True,
                 **kwargs):
        """
        :positions: Whether this token should have the token position in
            the 'pos' attribute.
        :chars: Whether this token should have the token's character offsets
            in the 'startchar' and 'endchar' attributes.
        """
        
        self.positions = positions
        self.chars = chars
        self.boosts = boosts
        self.stopped = False
        self.boost = 1.0
        self.removestops = removestops
        self.__dict__.update(kwargs)
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           ", ".join(["%s=%r" % (name, value)
                                      for name, value in self.__dict__.iteritems()]))
        
    def copy(self):
        return copy.copy(self)


# Tokenizers

def IDTokenizer(value, positions = False, chars = False,
                keeporiginal = False, removestops = True,
                start_pos = 0, start_char = 0):
    """
    Yields the entire input string as a single token. For use
    in indexed but untokenized fields, such as a document's path.
    """
    
    t = Token(positions, chars, removestops = removestops)
    t.text = value
    if keeporiginal:
        t.original = value
    if positions:
        t.pos = start_pos + 1
    if chars:
        t.startchar = start_char
        t.endchar = start_char + len(value)
    yield t
    

class RegexTokenizer(object):
    """
    Uses a regular expression to extract tokens from text.
    """
    
    _default_expression = re.compile(r"\w+(\.?\w+)*", re.UNICODE)
    
    def __init__(self, expression = None):
        """
        :expression: A compiled regular expression object. Each match
            of the expression equals a token. For example, the expression
            re.compile("[A-Za-z0-9]+") would give tokens that only contain
            letters and numbers. Group 0 (the entire matched text) is used
            as the text of the token. If you require more complicated handling
            of the expression match, simply write your own tokenizer.
        """
        
        self.expression = expression or self._default_expression
    
    def __call__(self, value, positions = False, chars = False,
                 keeporiginal = False, removestops = True,
                 start_pos = 0, start_char = 0):
        """
        :value: The unicode string to tokenize.
        :positions: Whether to record token positions in the token.
        :chars: Whether to record character offsets in the token.
        :start_pos: The position number of the first token. For example,
            if you set start_pos=2, the tokens will be numbered 2,3,4,...
            instead of 0,1,2,...
        :start_char: The offset of the first character of the first
            token. For example, if you set start_char=2, the text "aaa bbb"
            will have chars (2,5),(6,9) instead (0,3),(4,7).
        """
        
        t = Token(positions, chars, removestops = removestops)
        
        for pos, match in enumerate(self.expression.finditer(value)):
            t.text = match.group(0)
            if keeporiginal:
                t.original = t.text
            t.stopped = False
            if positions:
                t.pos = start_pos + pos
            if chars:
                t.startchar = start_char + match.start()
                t.endchar = start_char + match.end()
            yield t


class SpaceSeparatedTokenizer(RegexTokenizer):
    """Splits tokens by whitespace.
    """
    
    _default_expression = re.compile("[^ \t\r\n]+")


class CommaSeparatedTokenizer(RegexTokenizer):
    """Splits tokens by commas surrounded by optional whitespace.
    """
    
    _default_expression = re.compile("[^,]+")
    
    def __call__(self, value, **kwargs):
        for t in super(self.__class__, self).__call__(value, **kwargs):
            t.text = t.text.strip()
            yield t


class NgramTokenizer(object):
    """Splits input text into N-grams instead of words. For example,
    NgramTokenizer(3, 4)("hello") will yield token texts
    "hel", "hell", "ell", "ello", "llo".
    
    Note that this tokenizer does NOT use a regular expression to extract words,
    so the grams emitted by it will contain whitespace, punctuation, etc. You may
    want to massage the input or add a custom filter to this tokenizer's output.
    
    Alternatively, if you only want sub-word grams without whitespace, you
    could use RegexTokenizer with NgramFilter instead.
    """
    
    def __init__(self, minsize, maxsize = None):
        """
        :minsize: The minimum size of the N-grams.
        :maxsize: The maximum size of the N-grams. If you omit
            this parameter, maxsize == minsize.
        """
        
        self.min = minsize
        self.max = maxsize or minsize
        
    def __call__(self, value, positions = False, chars = False,
                 keeporiginal = False, removestops = True,
                 start_pos = 0, start_char = 0):
        inlen = len(value)
        t = Token(positions, chars, removestops = removestops)
        
        pos = start_pos
        for start in xrange(0, inlen - self.min + 1):
            for size in xrange(self.min, self.max + 1):
                end = start + size
                if end > inlen: continue
                
                t.text = value[start:end]
                if keeporiginal:
                    t.original = t.text
                t.stopped = False
                if positions:
                    t.pos = pos
                if chars:
                    t.startchar = start_char + start
                    t.endchar = start_char + end
                
                yield t
            pos += 1
                    

# Filters

def PassFilter(tokens):
    """An identity filter: passes the tokens through untouched.
    """
    for t in tokens:
        yield t


class NgramFilter(object):
    """Splits token text into N-grams. For example,
    NgramFilter(3, 4), for token "hello" will yield token texts
    "hel", "hell", "ell", "ello", "llo".
    """
    
    def __init__(self, minsize, maxsize = None):
        """
        :minsize: The minimum size of the N-grams.
        :maxsize: The maximum size of the N-grams. If you omit
            this parameter, maxsize == minsize.
        """
        
        self.min = minsize
        self.max = maxsize or minsize
        
    def __call__(self, tokens):
        for t in tokens:
            text, chars = t.text, t.chars
            if chars:
                startchar = t.startchar
            # Token positions don't mean much for N-grams,
            # so we'll leave the token's original position
            # untouched.
            
            for start in xrange(0, len(text) - self.min):
                for size in xrange(self.min, self.max + 1):
                    end = start + size
                    if end > len(text): continue
                    
                    t.text = text[start:end]
                    
                    if chars:
                        t.startchar = startchar + start
                        t.endchar = startchar + end
                        
                    yield t


class StemFilter(object):
    """Stems (removes suffixes from) the text of tokens using the Porter stemming
    algorithm. Stemming attempts to reduce multiple forms of the same root word
    (for example, "rendering", "renders", "rendered", etc.) to a single word in
    the index.
    
    Note that I recommend you use a strategy of morphologically expanding the
    query terms (see query.Variations) rather than stemming the indexed words.
    """
    
    def __init__(self, ignore = None):
        """
        :ignore: a set/list of words that should not be stemmed. This
            is converted into a frozenset. If you omit this argument, all tokens
            are stemmed.
        """
        
        self.cache = {}
        if ignore is None:
            self.ignores = frozenset()
        else:
            self.ignores = frozenset(ignore)
    
    def clear(self):
        """
        This filter memoizes previously stemmed words to greatly speed up
        stemming. This method clears the cache of previously stemmed words.
        """
        self.cache.clear()
    
    def __call__(self, tokens):
        cache = self.cache
        ignores = self.ignores
        
        for t in tokens:
            if t.stopped:
                yield t
                continue
            
            text = t.text
            if text in ignores:
                yield t
            elif text in cache:
                t.text = cache[text]
                yield t
            else:
                t.text = s = stem(text)
                cache[text] = s
                yield t


_camel_exp = re.compile("[A-Z][a-z]*|[a-z]+|[0-9]+")
def CamelFilter(tokens):
    """Splits CamelCased words into multiple words. For example,
    the string "getProcessedToken" yields tokens
    "getProcessedToken", "get", "Processed", and "Token".
    
    Obviously this filter needs to precede LowercaseFilter in a filter
    chain.
    """
    
    for t in tokens:
        yield t
        text = t.text
        
        if text and not text.islower() and not text.isupper() and not text.isdigit():
            chars = t.chars
            if chars:
                oldstart = t.startchar
            
            for match in _camel_exp.finditer(text):
                sub = match.group(0)
                if sub != text:
                    t.text = sub
                    if chars:
                        t.startchar = oldstart + match.start()
                        t.endchar = oldstart + match.end()
                    yield t


_underscore_exp = re.compile("[A-Z][a-z]*|[a-z]+|[0-9]+")
def UnderscoreFilter(tokens):
    """Splits words with underscores into multiple words. For example,
    the string "get_processed_token" yields tokens
    "get_processed_token", "get", "processed", and "token".
    
    Obviously you should not split words on underscores in the
    tokenizer if you want to use this filter.
    """
    
    for t in tokens:
        yield t
        text = t.text
        
        if text:
            chars = t.chars
            if chars:
                oldstart = t.startchar
            
            for match in _underscore_exp.finditer(text):
                sub = match.group(0)
                if sub != text:
                    t.text = sub
                    if chars:
                        t.startchar = oldstart + match.start()
                        t.endchar = oldstart + match.end()
                    yield t


class StopFilter(object):
    """Marks "stop" words (words too common to index) in the stream (and by default
    removes them).
    """

    def __init__(self, stoplist = STOP_WORDS, minsize = 2,
                 renumber = True):
        """
        :stoplist: A collection of words to remove from the stream.
            This is converted to a frozenset. The default is a list of
            common stop words.
        :minsize: The minimum length of token texts. Tokens with
            text smaller than this will be stopped.
        :renumber: Change the 'pos' attribute of unstopped tokens
            to reflect their position with the stopped words removed.
        :remove: Whether to remove the stopped words from the stream
            entirely. This is not normally necessary, since the indexing
            code will ignore tokens it receives with stopped=True.
        """
        
        if stoplist is None:
            self.stops = frozenset()
        else:
            self.stops = frozenset(stoplist)
        self.min = minsize
        self.renumber = renumber
    
    def __call__(self, tokens):
        stoplist = self.stops
        minsize = self.min
        renumber = self.renumber
        
        pos = None
        for t in tokens:
            text = t.text
            if len(text) >= minsize and text not in stoplist:
                # This is not a stop word
                if renumber and t.positions:
                    if pos is None:
                        pos = t.pos
                    else:
                        pos += 1
                    t.pos = pos
                t.stopped = False
                yield t
            else:
                # This is a stop word
                if not t.removestops:
                    # This IS a stop word, but we're not removing them
                    t.stopped = True
                    yield t


def LowercaseFilter(tokens):
    """Uses str.lower() to lowercase token text. For example, tokens
    "This","is","a","TEST" become "this","is","a","test".
    """
    
    for t in tokens:
        t.text = t.text.lower()
        yield t


class BoostTextFilter(object):
    """Advanced filter. Looks for embedded boost markers in the actual text of
    each token and extracts them to set the token's boost. This might be useful
    to let users boost individual terms.
    
    For example, if you added a filter:
    
      BoostTextFilter("\\^([0-9.]+)$")
    
    The user could then write keywords with an optional boost encoded in them,
    like this:
    
      image render^2 file^0.5
    
    (Of course, you might want to write a better pattern for the number part.)
    
     - Note that the pattern is run on EACH TOKEN, not the source text as a whole.
     
     - Because this filter runs a regular expression match on every token,
       for performance reasons it is probably only suitable for short fields.
       
     - You may use this filter in a Frequency-formatted field, where
       the Frequency format object has boost_as_freq = True. Bear in mind that
       in that case, you can only use integer "boosts".
    """
    
    def __init__(self, expression, group = 1, default = 1.0):
        """
        :expression: a compiled regular expression object representing
        the pattern to look for within each token.
        :group: the group name or number to use as the boost number
            (what to pass to match.group()). The string value of this group is
            passed to float().
        :default: the default boost to use for tokens that don't have
            the marker.
        """
        
        self.expression = expression
        self.default = default
        
    def __call__(self, tokens):
        expression = self.expression
        default = self.default
    
        for t in tokens:
            text = t.text
            m = expression.match(text)
            if m:
                text = text[:m.start()] + text[m.end():]
                t.boost = float(m.group(1))
            else:
                t.boost = default
                
            yield t

# Analyzers

class Analyzer(object):
    """
    Abstract base class for analyzers.
    """
    
    def __repr__(self):
        return "%s()" % self.__class__.__name__

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.__dict__ == other.__dict__

    def __call__(self, value):
        raise NotImplementedError
    
    def clean(self):
        pass


class IDAnalyzer(Analyzer):
    """
    Yields the original text as a single token. This is useful for fields
    you don't want to tokenize, such as the path of a file.
    """
    
    def __init__(self, strip = True, lowercase = False):
        """
        :strip: Whether to use str.strip() to strip whitespace
            from the value before yielding it as a token.
        :lowercase: Whether to convert the token to lowercase
            before indexing.
        """
        self.strip = strip
        self.lowercase = lowercase
    
    def __call__(self, value, **kwargs):
        if self.strip: value = value.strip()
        if self.lowercase:
            return LowercaseFilter(IDTokenizer(value, **kwargs))
        else:
            return IDTokenizer(value, **kwargs)


class KeywordAnalyzer(Analyzer):
    """Parses space-separated tokens.
    """
    
    def __init__(self, lowercase = False, commas = False):
        self.lowercase = lowercase
        if commas:
            self.tokenizer = CommaSeparatedTokenizer()
        else:
            self.tokenizer = SpaceSeparatedTokenizer()
    
    def __call__(self, value, **kwargs):
        if self.lowercase:
            return LowercaseFilter(self.tokenizer(value, **kwargs))
        else:
            return self.tokenizer(value, **kwargs)


class RegexAnalyzer(Analyzer):
    """Uses a RegexTokenizer, applies no filters.
    
    :expression: The regular expression pattern to use to extract tokens.
    """
    
    def __init__(self, expression = None):
        self.tokenizer = RegexTokenizer(expression = expression)
        
    def __call__(self, value, **kwargs):
        return self.tokenizer(value, **kwargs)


class SimpleAnalyzer(Analyzer):
    """Uses a RegexTokenizer and applies a LowercaseFilter.
    
    :expression: The regular expression pattern to use to extract tokens.
    """
    
    def __init__(self, expression = None):
        self.tokenizer = RegexTokenizer(expression = expression)
        
    def __call__(self, value, **kwargs):
        return LowercaseFilter(self.tokenizer(value, **kwargs))


class StemmingAnalyzer(Analyzer):
    def __init__(self, stoplist = STOP_WORDS, minsize = 2):
        self.tokenizer = RegexTokenizer()
        self.stemfilter = StemFilter()
        self.stopper = None
        if stoplist is not None:
            self.stopper = StopFilter(stoplist = stoplist, minsize = minsize)
        
    def clean(self):
        self.stemfilter.clear()
        
    def __call__(self, value, **kwargs):
        gen = LowercaseFilter(self.tokenizer(value, **kwargs))
        if self.stopper:
            gen = self.stopper(gen)
        return self.stemfilter(gen)


class StandardAnalyzer(Analyzer):
    """Uses a RegexTokenizer and applies a LowercaseFilter and StopFilter.
    """
    
    def __init__(self, stoplist = STOP_WORDS, minsize = 2):
        """
        :stoplist: See analysis.StopFilter.
        :minsize: See analysis.StopFilter.
        """
        
        self.tokenizer = RegexTokenizer()
        self.stopper = None
        if stoplist is not None:
            self.stopper = StopFilter(stoplist = stoplist, minsize = minsize)
    
    def __call__(self, value, **kwargs):
        gen = LowercaseFilter(self.tokenizer(value, **kwargs))
        if self.stopper:
            return self.stopper(gen)
        else:
            return gen


class FancyAnalyzer(Analyzer):
    """Uses a RegexTokenizer and applies a CamelFilter,
    UnderscoreFilter, LowercaseFilter, and StopFilter.
    """
    
    def __init__(self, stoplist = STOP_WORDS, minsize = 2):
        """
        :stoplist: See analysis.StopFilter.
        :minsize: See analysis.StopFilter.
        """
        
        self.tokenizer = RegexTokenizer()
        self.stopper = StopFilter(stoplist = stoplist, minsize = minsize)
        
    def __call__(self, value, **kwargs):
        return self.stopper(UnderscoreFilter(
                            LowercaseFilter(
                            CamelFilter(
                            self.tokenizer(value, **kwargs)))))


class NgramAnalyzer(Analyzer):
    """Uses an NgramTokenizer and applies a LowercaseFilter.
    """
    
    def __init__(self, minsize, maxsize = None):
        """
        See analysis.NgramTokenizer.
        """
        self.tokenizer = NgramTokenizer(minsize, maxsize = maxsize)
        
    def __call__(self, value, **kwargs):
        return LowercaseFilter(self.tokenizer(value, **kwargs))
    

if __name__ == '__main__':
    import time
    txt = open("/Volumes/Storage/Development/help/documents/nodes/sop/copy.txt", "rb").read().decode("utf8")
    st = time.time()
    print [t.text for t in StopFilter()(LowercaseFilter(RegexTokenizer()(txt, positions = True)))]
    print time.time() - st

    st = time.time()
    print [t.text for t in StopFilter(remove = False)(LowercaseFilter(RegexTokenizer()(txt, positions = True)))]
    print time.time() - st

########NEW FILE########
__FILENAME__ = classify
#===============================================================================
# Copyright 2008 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""Classes and functions for classifying and extracting information from documents.
"""

from __future__ import division, with_statement
from collections import defaultdict
from math import log


# Expansion models

class ExpansionModel(object):
    def __init__(self, searcher, fieldname):
        self.N = searcher.doc_count_all()
        self.collection_total = searcher.field_length(fieldname)
        self.mean_length = self.collection_total / self.N
    
    def normalizer(self, maxweight, top_total):
        raise NotImplementedError
    
    def score(self, weight_in_top, weight_in_collection, top_total):
        raise NotImplementedError


class Bo1Model(ExpansionModel):
    def normalizer(self, maxweight, top_total):
        f = maxweight / self.N
        return (maxweight * log((1.0 + f) / f) + log(1.0 + f)) / log(2.0)
    
    def score(self, weight_in_top, weight_in_collection, top_total):
        f = weight_in_collection / self.N
        return weight_in_top * log((1.0 + f) / f, 2) + log(1.0 + f, 2)

 
class Bo2Model(ExpansionModel):
    def normalizer(self, maxweight, top_total):
        f = maxweight * self.N / self.collection_total
        return (maxweight * log((1.0 + f) / f, 2) + log(1.0 + f, 2))
    
    def score(self, weight_in_top, weight_in_collection, top_total):
        f = weight_in_top * top_total / self.collection_total
        return weight_in_top * log((1.0 + f) / f, 2) + log(1.0 + f, 2)


class KLModel(ExpansionModel):
    def normalizer(self, maxweight, top_total):
        return maxweight * log(self.collection_total / top_total) / log(2.0) * top_total
    
    def score(self, weight_in_top, weight_in_collection, top_total):
        wit_over_tt = weight_in_top / top_total
        wic_over_ct = weight_in_collection / self.collection_total
        
        if wit_over_tt < wic_over_ct:
            return 0
        else:
            return wit_over_tt * log((wit_over_tt) / (weight_in_top / self.collection_total), 2)


class Expander(object):
    """Uses an ExpansionModel to expand the set of query terms based on
    the top N result documents.
    """
    
    def __init__(self, searcher, fieldname, model = Bo1Model):
        """
        :searcher: A searching.Searcher object for the index.
        :fieldname: The name of the field in which to search.
        :model: (classify.ExpansionModel) The model to use for expanding
            the query terms. If you omit this parameter, the expander uses
            scoring.Bo1Model by default.
        """
        
        self.fieldname = fieldname
        
        if callable(model):
            model = model(searcher, fieldname)
        self.model = model
        
        # Cache the collection frequency of every term in this
        # field. This turns out to be much faster than reading each
        # individual weight from the term index as we add words.
        term_reader = searcher.term_reader
        self.collection_freq = dict((word, freq) for word, _, freq
                                      in term_reader.iter_field(fieldname))
        
        # Maps words to their weight in the top N documents.
        self.topN_weight = defaultdict(float)
        
        # Total weight of all terms in the top N documents.
        self.top_total = 0
        
    def add(self, vector):
        """Adds forward-index information about one of the "top N" documents.
        
        :vector: A series of (text, weight) tuples, such as is
            returned by DocReader.vector_as(docnum, fieldnum, "weight").
        """
        
        total_weight = 0
        topN_weight = self.topN_weight
        
        for word, weight in vector:
            total_weight += weight
            topN_weight[word] += weight
            
        self.top_total += total_weight
    
    def expanded_terms(self, number, normalize = True):
        """Returns the N most important terms in the vectors added so far.
        
        :number: The number of terms to return.
        :normalize: Whether to normalize the weights.
        :*returns*: A list of ("term", weight) tuples.
        """
        
        model = self.model
        tlist = []
        maxweight = 0
        collection_freq = self.collection_freq
        
        for word, weight in self.topN_weight.iteritems():
            score = model.score(weight, collection_freq[word], self.top_total)
            if score > maxweight: maxweight = score
            tlist.append((score, word))
        
        if normalize:
            norm = model.normalizer(maxweight, self.top_total)
        else:
            norm = maxweight
        tlist = [(weight / norm, t) for weight, t in tlist]
        tlist.sort(reverse = True)
        
        return [(t, weight) for weight, t in tlist[:number]]

########NEW FILE########
__FILENAME__ = fields
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""
This module contains functions and classes related to fields.


"""

import re
from collections import defaultdict

from whoosh.analysis import unstopped, IDAnalyzer, RegexAnalyzer, KeywordAnalyzer, StandardAnalyzer, NgramAnalyzer

# Exceptions

class FieldConfigurationError(Exception):
    pass
class UnknownFieldError(Exception):
    pass

# Field Types

class FieldType(object):
    """
    Represents a field configuration.
    
    The FieldType object supports the following attributes:
    
        - format (fields.Format): the storage format for the field's contents.
        
        - vector (fields.Format): the storage format for the field's vectors
          (forward index), or None if the field should not store vectors.
        
        - scorable (boolean): whether searches against this field may be scored.
          This controls whether the index stores per-document field lengths for
          this field.
          
        - stored (boolean): whether the content of this field is stored for each
          document. For example, in addition to indexing the title of a document,
          you usually want to store the title so it can be presented as part of
          the search results.
          
        - unique (boolean): whether this field's value is unique to each document.
          For example, 'path' or 'ID'. IndexWriter.update_document() will use
          fields marked as 'unique' to find the previous version of a document
          being updated.
      
    The constructor for the base field type simply lets you supply your
    own configured field format, vector format, and scorable and stored
    values. Subclasses may configure some or all of this for you.
    """
    
    format = vector = scorable = stored = unique = None
    
    def __init__(self, format, vector = None,
                 scorable = False, stored = False,
                 unique = False):
        self.format = format
        self.vector = vector
        self.scorable = scorable
        self.stored = stored
        self.unique = unique
    
    def __repr__(self):
        return "%s(format=%r, vector=%r, scorable=%s, stored=%s, unique=%s)"\
        % (self.__class__.__name__, self.format, self.vector,
           self.scorable, self.stored, self.unique)
    
    def __eq__(self, other):
        return all((isinstance(other, FieldType),
                    (self.format == other.format),
                    (self.vector == other.vector),
                    (self.scorable == other.scorable),
                    (self.stored == other.stored),
                    (self.unique == other.unique)))
    
    def clean(self):
        if self.format and hasattr(self.format, "clean"):
            self.format.clean()
        if self.vector and hasattr(self.vector, "clean"):
            self.vector.clean()


class ID(FieldType):
    """
    Configured field type that indexes the entire value of the field as one
    token. This is useful for data you don't want to tokenize, such as the
    path of a file.
    """
    
    def __init__(self, stored = False, unique = False):
        """
        :stored: Whether the value of this field is stored with the document.
        """
        self.format = Existence(analyzer = IDAnalyzer())
        self.stored = stored
        self.unique = unique


class IDLIST(FieldType):
    """Configured field type for fields containing IDs separated by whitespace
    and/or puntuation.
    
    :stored: Whether the value of this field is stored with the document.
    :unique: Whether the value of this field is unique per-document.
    :expression: The regular expression object to use to extract tokens.
        The default expression breaks tokens on CRs, LFs, tabs, spaces, commas,
        and semicolons.
    """
    
    def __init__(self, stored = False, unique = False, expression = None):
        expression = expression or re.compile(r"[^\r\n\t ,;]+")
        analyzer = RegexAnalyzer(expression = expression)
        self.format = Existence(analyzer = analyzer)
        self.stored = stored
        self.unique = unique


class STORED(FieldType):
    """
    Configured field type for fields you want to store but not index.
    """
    
    def __init__(self):
        self.format = Stored()
        self.stored = True


class KEYWORD(FieldType):
    """
    Configured field type for fields containing space-separated or comma-separated
    keyword-like data (such as tags). The default is to not store positional information
    (so phrase searching is not allowed in this field) and to not make the field scorable.
    """
    
    def __init__(self, stored = False, lowercase = False, commas = False,
                 scorable = False, unique = False, field_boost = 1.0):
        """
        :stored: Whether to store the value of the field with the document.
        :comma: Whether this is a comma-separated field. If this is False
            (the default), it is treated as a space-separated field.
        :scorable: Whether this field is scorable.
        """
        
        ana = KeywordAnalyzer(lowercase = lowercase, commas = commas)
        self.format = Frequency(analyzer = ana, field_boost = field_boost)
        self.scorable = scorable
        self.stored = stored
        self.unique = unique


class TEXT(FieldType):
    """
    Configured field type for text fields (for example, the body text of an article). The
    default is to store positional information to allow phrase searching. This field type
    is always scorable.
    """
    
    def __init__(self, analyzer = None, phrase = True, vector = None,
                 stored = False, field_boost = 1.0):
        """
        :stored: Whether to store the value of this field with the document. Since
            this field type generally contains a lot of text, you should avoid storing it
            with the document unless you need to, for example to allow fast excerpts in the
            search results.
        :phrase: Whether the store positional information to allow phrase searching.
        :analyzer: The analysis.Analyzer to use to index the field contents. See the
            analysis module for more information. If you omit this argument, the field uses
            analysis.StandardAnalyzer.
        """
        
        ana = analyzer or StandardAnalyzer()
        
        if phrase:
            formatclass = Positions
        else:
            formatclass = Frequency
        self.format = formatclass(analyzer = ana, field_boost = field_boost)
        self.vector = vector
        
        self.scorable = True
        self.stored = stored


class NGRAM(FieldType):
    """
    Configured field that indexes text as N-grams. For example, with a field type
    NGRAM(3,4), the value "hello" will be indexed as tokens
    "hel", "hell", "ell", "ello", "llo".
    """
    
    def __init__(self, minsize = 2, maxsize = 4, stored = False):
        """
        :stored: Whether to store the value of this field with the document. Since
            this field type generally contains a lot of text, you should avoid storing it
            with the document unless you need to, for example to allow fast excerpts in the
            search results.
        :minsize: The minimum length of the N-grams.
        :maxsize: The maximum length of the N-grams.
        """
        
        self.format = Frequency(analyzer = NgramAnalyzer(minsize, maxsize))
        self.scorable = True
        self.stored = stored


# Schema class

class Schema(object):
    """
    Represents the collection of fields in an index. Maps field names to
    FieldType objects which define the behavior of each field.
    
    Low-level parts of the index use field numbers instead of field names
    for compactness. This class has several methods for converting between
    the field name, field number, and field object itself.
    """
    
    def __init__(self, **fields):
        """
        All keyword arguments to the constructor are treated as fieldname = fieldtype
        pairs. The fieldtype can be an instantiated FieldType object, or a FieldType
        sub-class (in which case the Schema will instantiate it with the default
        constructor before adding it).
        
        For example::
        
            s = Schema(content = TEXT,
                       title = TEXT(stored = True),
                       tags = KEYWORD(stored = True))
        """
        
        self._by_number = []
        self._names = []
        self._by_name = {}
        self._numbers = {}
        
        for name in sorted(fields.keys()):
            self.add(name, fields[name])
    
    def __eq__(self, other):
        if not isinstance(other, Schema): return False
        return self._by_name == other._by_name
    
    def __repr__(self):
        return "<Schema: %s>" % repr(self._names)
    
    def __iter__(self):
        """
        Yields the sequence of fields in this schema.
        """
        
        return iter(self._by_number)
    
    def __getitem__(self, id):
        """
        Returns the field associated with the given field name or number.
        
        :id: A field name or field number.
        """
        
        if isinstance(id, basestring):
            return self._by_name[id]
        return self._by_number[id]
    
    def __len__(self):
        """
        Returns the number of fields in this schema.
        """
        return len(self._by_number)
    
    def __contains__(self, fieldname):
        """
        Returns True if a field by the given name is in this schema.
        
        :fieldname: The name of the field.
        """
        return fieldname in self._by_name
    
    def field_by_name(self, name):
        """
        Returns the field object associated with the given name.
        
        :name: The name of the field to retrieve.
        """
        return self._by_name[name]
    
    def field_by_number(self, number):
        """
        Returns the field object associated with the given number.
        
        :number: The number of the field to retrieve.
        """
        return self._by_number[number]
    
    def fields(self):
        """
        Yields ("fieldname", field_object) pairs for the fields
        in this schema.
        """
        return self._by_name.iteritems()
    
    def field_names(self):
        """
        Returns a list of the names of the fields in this schema.
        """
        return self._names
    
    def add(self, name, fieldtype):
        """
        Adds a field to this schema.
        
        :name: The name of the field.
        :fieldtype: An instantiated fields.FieldType object, or a FieldType subclass.
            If you pass an instantiated object, the schema will use that as the field
            configuration for this field. If you pass a FieldType subclass, the schema
            will automatically instantiate it with the default constructor.
        """
        
        if name.startswith("_"):
            raise FieldConfigurationError("Field names cannot start with an underscore")
        elif name in self._by_name:
            raise FieldConfigurationError("Schema already has a field named %s" % name)
        
        if callable(fieldtype):
            fieldtype = fieldtype()
        if not isinstance(fieldtype, FieldType):
            raise FieldConfigurationError("%r is not a FieldType object" % fieldtype)
        
        fnum = len(self._by_number)
        self._numbers[name] = fnum
        self._by_number.append(fieldtype)
        self._names.append(name)
        self._by_name[name] = fieldtype
    
    def to_number(self, id):
        """Given a field name or number, returns the field's number.
        """
        if isinstance(id, int): return id
        return self.name_to_number(id)
    
    def name_to_number(self, name):
        """Given a field name, returns the field's number.
        """
        return self._numbers[name]
    
    def number_to_name(self, number):
        """Given a field number, returns the field's name.
        """
        return self._names[number]
    
    def has_vectored_fields(self):
        """Returns True if any of the fields in this schema store term vectors.
        """
        return any(ftype.vector for ftype in self._by_number)
    
    def vectored_fields(self):
        """Returns a list of field numbers corresponding to the fields that are
        vectored.
        """
        return [i for i, ftype in enumerate(self._by_number) if ftype.vector]
    
    def scorable_fields(self):
        """Returns a list of field numbers corresponding to the fields that
        store length information.
        """
        return [i for i, field in enumerate(self) if field.scorable]

    def stored_field_names(self):
        """Returns the names, in order, of fields that are stored."""
        
        bn = self._by_name
        return [name for name in self._names if bn[name].stored]

    def analyzer(self, fieldname):
        """Returns the content analyzer for the given fieldname, or None if
        the field has no analyzer
        """
        
        field = self[fieldname]
        if field.format and field.format.analyzer:
            return field.format.analyzer
        

# Format base class

class Format(object):
    """Abstract base class representing a storage format for a field or vector.
    Format objects are responsible for writing and reading the low-level
    representation of a field. It controls what kind/level of information
    to store about the indexed fields.
    """
    
    def __init__(self, analyzer, field_boost = 1.0, **options):
        """
        :analyzer: The analysis.Analyzer object to use to index this field.
            See the analysis module for more information. If this value
            is None, the field is not indexed/searchable.
        :field_boost: A constant boost factor to scale to the score
            of all queries matching terms in this field.
        """
        
        self.analyzer = analyzer
        self.field_boost = field_boost
        self.options = options
    
    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.__dict__ == other.__dict__
    
    def __repr__(self):
        return "%s(%r, boost = %s)" % (self.__class__.__name__,
                                       self.analyzer, self.field_boost)
    
    def clean(self):
        if self.analyzer:
            self.analyzer.clean()
    
    def word_datas(self, value, **kwargs):
        """Takes the text value to be indexed and yields a series of
        ("tokentext", frequency, data) tuples, where frequency is the number
        of times "tokentext" appeared in the value, and data is field-specific
        posting data for the token. For example, in a Frequency format, data
        would be the same as frequency; in a Positions format, data would be a
        list of token positions at which "tokentext" occured.
        
        :value: The unicode text to index.
        """
        raise NotImplementedError
    
    def write_postvalue(self, stream, data):
        """Writes a posting to a filestream."""
        raise NotImplementedError
    
    def read_postvalue(self, stream):
        """Reads a posting from a filestream."""
        raise NotImplementedError
    
    def read_weight(self, stream):
        """Shortcut to read a posting from a filestream and return only the
        weight, rather than all the data. This is equivalent to:
        
          self.data_to_weight(self.read_postvalue(stream))
          
        ..and in fact, that is the default implementation. However, subclassed
        Formats can be more clever about skipping reads when all the caller
        wants is the weight.
        """
        
        return self.data_to_weight(self.read_postvalue(stream))
    
    def supports(self, name):
        """Returns True if this format supports interpreting its posting
        data as 'name' (e.g. "frequency" or "positions").
        """
        return hasattr(self, "data_to_" + name)
    
    def interpreter(self, name):
        """Returns the bound method for interpreting data as 'name',
        where 'name' is for example "frequency" or "positions". This
        object must have a corresponding .data_to_<name>() method.
        """
        return getattr(self, "data_to_" + name)
    
    def data_to(self, data, name):
        """Interprets the given data as 'name', where 'name' is for example
        "frequency" or "positions". This object must have a corresponding
        .data_to_<name>() method.
        """
        return self.interpreter(name)(data)
    

# Concrete field classes

class Stored(Format):
    """A field that's stored but not indexed."""
    
    analyzer = None
    
    def __init__(self, **options):
        self.options = options
        
    def __repr__(self):
        return "%s()" % self.__class__.__name__
        

class Existence(Format):
    """Only indexes whether a given term occurred in
    a given document; it does not store frequencies or positions.
    This is useful for fields that should be searchable but not
    scorable, such as file path.
    """
    
    def __init__(self, analyzer, field_boost = 1.0, **options):
        self.analyzer = analyzer
        self.field_boost = field_boost
        self.options = options
    
    def word_datas(self, value, **kwargs):
        seen = set()
        for t in unstopped(self.analyzer(value)):
            seen.add(t.text)
        
        return ((w, 1, None) for w in seen)
    
    def write_postvalue(self, stream, data):
        return 0
    
    def read_postvalue(self, stream):
        return None
    
    def data_to_frequency(self, data):
        return 1
    
    def data_to_weight(self, data):
        return self.field_boost

# Backwards compatibility for a stupid spelling mistake
Existance = Existence


class Frequency(Format):
    """Stores frequency information for each posting.
    """
    
    def __init__(self, analyzer, field_boost = 1.0, boost_as_freq = False, **options):
        """
        :analyzer: The analysis.Analyzer object to use to index this field.
            See the analysis module for more information. If this value
            is None, the field is not indexed/searchable.
        :field_boost: A constant boost factor to scale to the score
            of all queries matching terms in this field.
        :boost_as_freq: if True, take the integer value of each token's
            boost attribute and use it as the token's frequency.
        """
        
        self.analyzer = analyzer
        self.field_boost = field_boost
        self.boost_as_freq = boost_as_freq
        self.options = options
        
    def word_datas(self, value, **kwargs):
        seen = defaultdict(int)
        if self.boost_as_freq:
            for t in unstopped(self.analyzer(value, boosts = True)):
                seen[t.text] += int(t.boost)
        else:
            for t in unstopped(self.analyzer(value)):
                seen[t.text] += 1
            
        return ((w, freq, freq) for w, freq in seen.iteritems())

    def write_postvalue(self, stream, data):
        stream.write_varint(data)
        
        # Write_postvalue returns the term frequency, which is
        # what the data is.
        return data
        
    def read_postvalue(self, stream):
        return stream.read_varint()
    
    def read_weight(self, stream):
        return stream.read_varint() * self.field_boost
    
    def data_to_frequency(self, data):
        return data
    
    def data_to_weight(self, data):
        return data * self.field_boost
    

class DocBoosts(Frequency):
    """A Field that stores frequency and per-document boost information
    for each posting.
    """
    
    def word_datas(self, value, doc_boost = 1.0, **kwargs):
        seen = defaultdict(int)
        for t in unstopped(self.analyzer(value)):
            seen[t.text] += 1
        
        return ((w, freq, (freq, doc_boost)) for w, freq in seen.iteritems())
    
    def write_postvalue(self, stream, data):
        stream.write_varint(data[0])
        stream.write_8bitfloat(data[1])
        return data[0]
        
    def read_postvalue(self, stream):
        return (stream.read_varint(), stream.read_8bitfloat())
    
    def data_to_frequency(self, data):
        return data[0]
    
    def data_to_weight(self, data):
        return data[0] * data[1] * self.field_boost
    

# Vector formats

class Positions(Format):
    """A vector that stores position information in each posting, to
    allow phrase searching and "near" queries.
    """
    
    def word_datas(self, value, start_pos = 0, **kwargs):
        seen = defaultdict(list)
        for t in unstopped(self.analyzer(value, positions = True, start_pos = start_pos)):
            seen[t.text].append(start_pos + t.pos)
        
        return ((w, len(poslist), poslist) for w, poslist in seen.iteritems())
    
    def write_postvalue(self, stream, data):
        pos_base = 0
        stream.write_varint(len(data))
        
        if len(data) > 10:
            streampos = stream.tell()
            stream.write_ulong(0)
            postingstart = stream.tell()
            
        for pos in data:
            stream.write_varint(pos - pos_base)
            pos_base = pos
            
        if len(data) > 10:
            postingend = stream.tell()
            stream.seek(streampos)
            stream.write_ulong(postingend - postingstart)
            stream.seek(postingend)
        
        return len(data)
    
    def read_postvalue(self, stream):
        pos_base = 0
        pos_list = []
        rv = stream.read_varint
        freq = rv()
        
        if freq > 10:
            stream.read_ulong()
        
        for _ in xrange(freq):
            pos_base += rv()
            pos_list.append(pos_base)
        
        return pos_list
    
    def read_weight(self, stream):
        rv = stream.read_varint
        freq = rv()
        
        if freq > 10:
            length = stream.read_ulong()
            stream.seek(length, 1)
        else:
            for _ in xrange(0, freq): rv()
        
        return freq * self.field_boost
    
    def data_to_frequency(self, data):
        return len(data)
    
    def data_to_weight(self, data):
        return len(data) * self.field_boost
    
    def data_to_positions(self, data):
        return data
    

class Characters(Format):
    """Stores token position and character start and end information
    for each posting.
    """
    
    def word_datas(self, value, start_pos = 0, start_char = 0, **kwargs):
        seen = defaultdict(list)
        
        for t in unstopped(self.analyzer(value, positions = True, chars = True,
                                         start_pos = start_pos, start_char = start_char)):
            seen[t.text].append((t.pos, start_char + t.startchar, start_char + t.endchar))
        
        return ((w, len(ls), ls) for w, ls in seen.iteritems())
    
    def write_postvalue(self, stream, data):
        pos_base = 0
        char_base = 0
        stream.write_varint(len(data))
        
        if len(data) > 10:
            streampos = stream.tell()
            stream.write_ulong(0)
            postingstart = stream.tell()
        
        for pos, startchar, endchar in data:
            stream.write_varint(pos - pos_base)
            pos_base = pos
            
            stream.write_varint(startchar - char_base)
            stream.write_varint(endchar - startchar)
            char_base = endchar
            
        if len(data) > 10:
            postingend = stream.tell()
            stream.seek(streampos)
            stream.write_ulong(postingend - postingstart)
            stream.seek(postingend)
        
        return len(data)
    
    def read_postvalue(self, stream):
        pos_base = 0
        char_base = 0
        ls = []
        freq = stream.read_varint()
        
        if freq > 10:
            stream.read_ulong()
        
        for i in xrange(freq): #@UnusedVariable
            pos_base += stream.read_varint()
            
            char_base += stream.read_varint()
            startchar = char_base
            char_base += stream.read_varint() # End char
            
            ls.append((pos_base, startchar, char_base))
        
        return ls
    
    def read_weight(self, stream):
        rv = stream.read_varint
        freq = rv()
        
        if freq > 10:
            length = stream.read_ulong()
            stream.seek(length, 1)
        else:
            for _ in xrange(0, freq): rv()
        
        return freq * self.field_boost
    
    def data_to_frequency(self, data):
        return len(data)
    
    def data_to_weight(self, data):
        return len(data) * self.field_boost
    
    def data_to_positions(self, data):
        return (pos for pos, _, _ in data)
    
    def data_to_characters(self, data):
        return ((sc, ec) for _, sc, ec in data)


class PositionBoosts(Format):
    """A format that stores positions and per-position boost information
    in each posting.
    """
    
    def word_datas(self, value, start_pos = 0, **kwargs):
        seen = defaultdict(iter)
        for t in unstopped(self.analyzer(value, positions = True, boosts = True,
                                         start_pos = start_pos)):
            pos = t.pos
            boost = t.boost
            seen[t.text].append((pos, boost))
        
        return ((w, len(poslist), poslist) for w, poslist in seen.iteritems())
    
    def write_postvalue(self, stream, data):
        pos_base = 0
        stream.write_varint(len(data))
        for pos, boost in data:
            stream.write_varint(pos - pos_base)
            stream.write_8bitfloat(boost)
            pos_base = pos
        return len(data)

    def read_postvalue(self, stream):
        freq = stream.read_varint()
        pos_base = 0
        pos_list = []
        for _ in xrange(freq):
            pos_base += stream.read_varint()
            pos_list.append((pos_base, stream.read_8bitfloat()))
        return (freq, pos_list)

    def data_to_frequency(self, data):
        return len(data)
    
    def data_to_weight(self, data):
        return sum(d[1] for d in data) * self.field_boost

    def data_to_positions(self, data):
        return [d[0] for d in data]

    def data_to_position_boosts(self, data):
        return data
    

class CharacterBoosts(Format):
    """A format that stores positions, character start and end, and
    per-position boost information in each posting.
    """
    
    def word_datas(self, value, start_pos = 0, start_char = 0, **kwargs):
        seen = defaultdict(iter)
        for t in unstopped(self.analyzer(value, positions = True, characters = True,
                                         boosts = True,
                                         start_pos = start_pos, start_char = start_char)):
            seen[t.text].append((t.pos,
                                 start_char + t.startchar, start_char + t.endchar,
                                 t.boost))
        
        return ((w, len(poslist), poslist) for w, poslist in seen.iteritems())
    
    def write_postvalue(self, stream, data):
        pos_base = 0
        char_base = 0
        stream.write_varint(len(data))
        for pos, startchar, endchar, boost in data:
            stream.write_varint(pos - pos_base)
            pos_base = pos
            
            stream.write_varint(startchar - char_base)
            stream.write_varint(endchar - startchar)
            char_base = endchar
            
            stream.write_8bitfloat(boost)
        
        return len(data)

    def read_postvalue(self, stream):
        pos_base = 0
        char_base = 0
        ls = []
        for _ in xrange(stream.read_varint()):
            pos_base += stream.read_varint()
            
            char_base += stream.read_varint()
            startchar = char_base
            char_base += stream.read_varint() # End char
            boost = stream.read_8bitfloat()
            
            ls.append((pos_base, startchar, char_base, boost))
        
        return ls

    def data_to_frequency(self, data):
        return len(data)
    
    def data_to_weight(self, data):
        return sum(d[3] for d in data) * self.field_boost

    def data_to_positions(self, data):
        return [d[0] for d in data]

    def data_to_position_boosts(self, data):
        return [(pos, boost) for pos, _, _, boost in data]

    def data_to_character_boosts(self, data):
        return data



if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = generalcounter
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from google.appengine.api import memcache 
from google.appengine.ext import db
import random

class GeneralCounterShardConfig(db.Model):
  """Tracks the number of shards for each named counter."""
  name = db.StringProperty(required=True)
  num_shards = db.IntegerProperty(required=True, default=20)


class GeneralCounterShard(db.Model):
  """Shards for each named counter"""
  name = db.StringProperty(required=True)
  count = db.IntegerProperty(required=True, default=0)
  
            
def get_count(name):
  """Retrieve the value for a given sharded counter.
  
  Parameters:
    name - The name of the counter  
  """
  total = memcache.get(name)
  if total is None:
    total = 0
    for counter in GeneralCounterShard.all().filter('name = ', name):
      total += counter.count
    memcache.add(name, str(total), 60)
  return total

  
def increment(name):
  """Increment the value for a given sharded counter.
  
  Parameters:
    name - The name of the counter  
  """
  config = GeneralCounterShardConfig.get_or_insert(name, name=name)
  def txn():
    index = random.randint(0, config.num_shards - 1)
    shard_name = name + str(index)
    counter = GeneralCounterShard.get_by_key_name(shard_name)
    if counter is None:
      counter = GeneralCounterShard(key_name=shard_name, name=name)
    counter.count += 1
    counter.put()
  db.run_in_transaction(txn)
  memcache.incr(name)

  
def increase_shards(name, num):  
  """Increase the number of shards for a given sharded counter.
  Will never decrease the number of shards.
  
  Parameters:
    name - The name of the counter
    num - How many shards to use
    
  """
  config = GeneralCounterShardConfig.get_or_insert(name, name=name)
  def txn():
    if config.num_shards < num:
      config.num_shards = num
      config.put()    
  db.run_in_transaction(txn)

########NEW FILE########
__FILENAME__ = highlight
#===============================================================================
# Copyright 2008 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

from __future__ import division
from heapq import nlargest


# Fragment object

class Fragment(object):
    def __init__(self, tokens, charsbefore = 0, charsafter = 0, textlen = 999999):
        self.startchar = max(0, tokens[0].startchar - charsbefore)
        self.endchar = min(textlen, tokens[-1].endchar + charsafter)
        self.matches = [t for t in tokens if t.matched]
        self.matched_terms = frozenset(t.text for t in self.matches)
    
    def __len__(self):
        return self.endchar - self.startchar
    
    def overlaps(self, fragment):
        sc = self.startchar
        ec = self.endchar
        fsc = fragment.startchar
        fec = fragment.endchar
        return (fsc > sc and fsc < ec) or (fec > sc and fec < ec)
    
    def overlapped_length(self, fragment):
        sc = self.startchar
        ec = self.endchar
        fsc = fragment.startchar
        fec = fragment.endchar
        return max(ec, fec) - min(sc, fsc)
    
    def has_matches(self):
        return any(t.matched for t in self.tokens)
    

# Filters

def copyandmatchfilter(termset, tokens):
    for t in tokens:
        t = t.copy()
        t.matched = t.text in termset
        yield t

# Fragmenters

def NullFragmenter(text, termset, tokens):
    """Doesn't fragment the token stream. This object just
    returns the entire stream as one "fragment". This is useful if
    you want to highlight the entire text.
    """
    return Fragment(list(tokens))


class SimpleFragmenter(object):
    """Simply splits the text into roughly equal sized chunks.
    """
    
    def __init__(self, size = 70):
        """
        :size: size (in characters) to chunk to. The chunking is based on
            tokens, so the fragments will usually be smaller.
        """
        self.size = 70
        
    def __call__(self, text, tokens):
        size = self.size
        first = None
        frag = []
        
        for t in tokens:
            if first is None:
                first = t.startchar
            
            if t.endchar - first > size:
                first = None
                if frag:
                    yield Fragment(frag)
                frag = []
            
            frag.append(t)
            
        if frag:
            yield Fragment(frag)


class SentenceFragmenter(object):
    """"Breaks the text up on sentence end punctuation characters (".", "!", or "?").
    This object works by looking in the original text for a sentence end as the next
    character after each token's 'endchar'.
    """
    
    def __init__(self, maxchars = 200, sentencechars = ".!?"):
        """
        :maxchars: The maximum number of characters allowed in a fragment.
        """
        
        self.maxchars = maxchars
        self.sentencechars = frozenset(sentencechars)
    
    def __call__(self, text, tokens):
        maxchars = self.maxchars
        sentencechars = self.sentencechars
        textlen = len(text)
        first = None
        frag = []
        
        for t in tokens:
            if first is None:
                first = t.startchar
            endchar = t.endchar
            
            if endchar - first > maxchars:
                first = None
                if frag:
                    yield Fragment(frag)
                frag = []
            
            frag.append(t)
            if frag and endchar < textlen and text[endchar] in sentencechars:
                # Don't break for two periods in a row (e.g. ignore "...")
                if endchar+1 < textlen and text[endchar + 1] in sentencechars:
                    continue
                
                yield Fragment(frag, charsafter = 1)
                frag = []
                first = None
        
        if frag:
            yield Fragment(frag)


class ContextFragmenter(object):
    """Looks for matched terms and aggregates them with their
    surrounding context.
    
    This fragmenter only yields fragments that contain matched terms.    
    """
    
    def __init__(self, termset, maxchars = 200, charsbefore = 20, charsafter = 20):
        """
        :termset: A collection (probably a set or frozenset) containing the
            terms you want to match to token.text attributes.
        :maxchars: The maximum number of characters allowed in a fragment.
        :charsbefore: The number of extra characters of context to add before
            the first matched term.
        :charsafter: The number of extra characters of context to add after
            the last matched term.
        """
        
        self.maxchars = maxchars
        self.charsbefore = charsbefore
        self.charsafter = charsafter
        
    def __call__(self, text, tokens):
        maxchars = self.maxchars
        charsbefore = self.charsbefore
        charsafter = self.charsafter
        
        current = []
        currentlen = 0
        countdown = -1
        for t in tokens:
            if t.matched:
                countdown = charsafter
            
            current.append(t)
            
            length = t.endchar - t.startchar
            currentlen += length
            
            if countdown >= 0:
                countdown -= length
                
                if countdown < 0 or currentlen >= maxchars:
                    yield Fragment(current)
                    current = []
                    currentlen = 0
            
            else:
                while current and currentlen > charsbefore:
                    t = current.pop(0)
                    currentlen -= t.endchar - t.startchar

        if countdown >= 0:
            yield Fragment(current)


#class VectorFragmenter(object):
#    def __init__(self, termmap, maxchars = 200, charsbefore = 20, charsafter = 20):
#        """
#        :termmap: A dictionary mapping the terms you're looking for to
#            lists of either (posn, startchar, endchar) or
#            (posn, startchar, endchar, boost) tuples.
#        :maxchars: The maximum number of characters allowed in a fragment.
#        :charsbefore: The number of extra characters of context to add before
#            the first matched term.
#        :charsafter: The number of extra characters of context to add after
#            the last matched term.
#        """
#        
#        self.termmap = termmap
#        self.maxchars = maxchars
#        self.charsbefore = charsbefore
#        self.charsafter = charsafter
#    
#    def __call__(self, text, tokens):
#        maxchars = self.maxchars
#        charsbefore = self.charsbefore
#        charsafter = self.charsafter
#        textlen = len(text)
#        
#        vfrags = []
#        for term, data in self.termmap.iteritems():
#            if len(data) == 3:
#                t = Token(startchar = data[1], endchar = data[2])
#            elif len(data) == 4:
#                t = Token(startchar = data[1], endchar = data[2], boost = data[3])
#            else:
#                raise ValueError(repr(data))
#            
#            newfrag = VFragment([t], charsbefore, charsafter, textlen)
#            added = False
#            
#            for vf in vfrags:
#                if vf.overlaps(newfrag) and vf.overlapped_length(newfrag) < maxchars:
#                    vf.merge(newfrag)
#                    added = True
#                    break


# Fragment scorers

def BasicFragmentScorer(f):
    # Add up the boosts for the matched terms in this passage
    score = sum(t.boost for t in f.matches)
    
    # Favor diversity: multiply score by the number of separate
    # terms matched
    score *= len(f.matched_terms) * 100
    
    return score


# Fragment sorters

def SCORE(fragment):
    "Sorts higher scored passages first."
    return None
def FIRST(fragment):
    "Sorts passages from earlier in the document first."
    return fragment.startchar
def LONGER(fragment):
    "Sorts longer passages first."
    return 0 - len(fragment)
def SHORTER(fragment):
    "Sort shorter passages first."
    return len(fragment)


# Formatters

class UppercaseFormatter(object):
    def __init__(self, between = "..."):
        self.between = between
        
    def _format_fragment(self, text, fragment):
        output = []
        index = fragment.startchar
        
        for t in fragment.matches:
            if t.startchar > index:
                output.append(text[index:t.startchar])
            
            ttxt = text[t.startchar:t.endchar]
            if t.matched: ttxt = ttxt.upper()
            output.append(ttxt)
            index = t.endchar
        
        output.append(text[index:fragment.endchar])
        return "".join(output)

    def __call__(self, text, fragments):
        return self.between.join((self._format_fragment(text, fragment)
                                  for fragment in fragments))


class GenshiFormatter(object):
    def __init__(self, qname, between = "..."):
        self.qname = qname
        self.between = between
        
        from genshi.core import START, END, TEXT, Attrs, Stream #@UnresolvedImport
        self.START, self.END, self.TEXT, self.Attrs, self.Stream = (START, END, TEXT, Attrs, Stream)

    def _add_text(self, text, output):
        if output and output[-1][0] == self.TEXT:
            output[-1] = (self.TEXT, output[-1][1] + text, output[-1][2])
        else:
            output.append((self.TEXT, text, (None, -1, -1)))

    def _format_fragment(self, text, fragment):
        START, TEXT, END, Attrs = self.START, self.TEXT, self.END, self.Attrs
        qname = self.qname
        output = []
        
        index = fragment.startchar
        lastmatched = False
        for t in fragment.matches:
            if t.startchar > index:
                if lastmatched:
                    output.append((END, qname, (None, -1, -1)))
                    lastmatched = False
                self._add_text(text[index:t.startchar], output)
            
            ttxt = text[t.startchar:t.endchar]
            if not lastmatched:
                output.append((START, (qname, Attrs()), (None, -1, -1)))
                lastmatched = True
            output.append((TEXT, ttxt, (None, -1, -1)))
                                    
            index = t.endchar
        
        if lastmatched:
            output.append((END, qname, (None, -1, -1)))
        
        return output

    def __call__(self, text, fragments):
        output = []
        first = True
        for fragment in fragments:
            if not first:
                self._add_text(self.between, output)
            first = False
            output += self._format_fragment(text, fragment)
        
        return self.Stream(output)


# Highlighting

def top_fragments(text, terms, analyzer, fragmenter, top = 3,
                  scorer = BasicFragmentScorer, minscore = 1):
    termset = frozenset(terms)
    tokens = copyandmatchfilter(termset,
                                analyzer(text, chars = True, keeporiginal = True))
    
    scored_frags = nlargest(top, ((scorer(f), f) for f in fragmenter(text, tokens)))
    return [sf for score, sf in scored_frags if score > minscore]


def highlight(text, terms, analyzer, fragmenter, formatter, top=3,
              scorer = BasicFragmentScorer, minscore = 1,
              order = FIRST):
    
    fragments = top_fragments(text, terms, analyzer, fragmenter,
                              top = top, minscore = minscore)
    fragments.sort(key = order)
    return formatter(text, fragments)
    

if __name__ == '__main__':
    import re, time
    from whoosh import analysis
    #from genshi import QName
    
    sa = analysis.StemmingAnalyzer()
    txt = open("/Volumes/Storage/Development/help/documents/nodes/sop/copy.txt").read().decode("utf8")
    txt = re.sub("[\t\r\n ]+", " ", txt)
    t = time.time()
    fs = highlight(txt, ["templat", "geometri"], sa, SentenceFragmenter(), UppercaseFormatter())
    print time.time() - t
    print fs

########NEW FILE########
__FILENAME__ = index
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""Contains the main functions/classes for creating, maintaining, and using
an index.
"""

from __future__ import division
import os.path, re
from sys import byteorder
from bisect import bisect_right
import cPickle
from threading import Lock
from array import array

import generalcounter

from whoosh import fields, store


_DEF_INDEX_NAME = "MAIN"
_EXTENSIONS = "dci|dcz|tiz|fvz"

_index_version = -101

_int_size = array("i").itemsize
_ulong_size = array("L").itemsize
_float_size = array("f").itemsize

# Exceptions

class OutOfDateError(Exception):
    """Raised when you try to commit changes to an index which is not
    the latest generation.
    """
    pass

class EmptyIndexError(Exception):
    """Raised when you try to work with an index that has no indexed terms.
    """
    pass

class IndexLockedError(Exception):
    """Raised when you try to write to or lock an already-locked index (or
    one that was accidentally left in a locked state).
    """
    pass

class IndexError(Exception):
    """Generic index error."""
    pass


# Utility functions

def _toc_pattern(indexname):
    """Returns a regular expression object that matches TOC filenames.
    name is the name of the index.
    """
    
    return re.compile("_%s_([0-9]+).toc" % indexname)

def _segment_pattern():
    """Returns a regular expression object that matches segment filenames.
    name is the name of the index.
    """
    
    return re.compile("([0-9]+).(%s)" % (_EXTENSIONS))

def getdatastoreindex(name, schema = None, indexname = None, **kwargs):
    """Convenience function to create an index in a directory. Takes care of creating
    a FileStorage object for you. dirname is the filename of the directory in
    which to create the index. schema is a fields.Schema object describing the
    index's fields. indexname is the name of the index to create; you only need to
    specify this if you are creating multiple indexes within the
    same storage object.
    
    If you specify both a schema and keyword arguments, the schema wins.
    
    Returns an Index object.
    """
    if not indexname:
        indexname = _DEF_INDEX_NAME
    
    storage = store.DataStoreStorage(name)
    try:
        return Index(storage, indexname = indexname)
    except EmptyIndexError:
        if kwargs and not schema:
            schema = fields.Schema(**kwargs)
        elif not schema and not kwargs:
            raise Exception("You must specify either a schema or keyword arguments.")
        return Index(storage, schema = schema, indexname = indexname, create = True)

def create_in(dirname, schema = None, indexname = None, **kwargs):
    """Convenience function to create an index in a directory. Takes care of creating
    a FileStorage object for you. dirname is the filename of the directory in
    which to create the index. schema is a fields.Schema object describing the
    index's fields. indexname is the name of the index to create; you only need to
    specify this if you are creating multiple indexes within the
    same storage object.
    
    If you specify both a schema and keyword arguments, the schema wins.
    
    Returns an Index object.
    """
    
    if not indexname:
        indexname = _DEF_INDEX_NAME
    
    storage = store.FileStorage(dirname)
    if kwargs and not schema:
        schema = fields.Schema(**kwargs)
    elif not schema and not kwargs:
        raise Exception("You must specify either a schema or keyword arguments.")
    
    return Index(storage, schema = schema, indexname = indexname, create = True)

def open_dir(dirname, indexname = None):
    """Convenience function for opening an index in a directory. Takes care of creating
    a FileStorage object for you. dirname is the filename of the directory in
    containing the index. indexname is the name of the index to create; you only need to
    specify this if you have multiple indexes within the same storage object.
    
    Returns an Index object.
    """
    
    if indexname is None:
        indexname = _DEF_INDEX_NAME
    
    return Index(store.FileStorage(dirname), indexname = indexname)

def exists_in(dirname, indexname = None):
    """Returns True if dirname contains a Whoosh index."""
    
    if indexname is None:
        indexname = _DEF_INDEX_NAME
    
    if os.path.exists(dirname):
        try:
            ix = open_dir(dirname)
            return ix.latest_generation() > -1
        except EmptyIndexError:
            pass

    return False

def exists(storage, indexname):
    if indexname is None:
        indexname = _DEF_INDEX_NAME
        
    try:
        ix = Index(storage, indexname = indexname)
        return ix.latest_generation() > -1
    except EmptyIndexError:
        pass
    
    return False


# A mix-in that adds methods for deleting
# documents from self.segments. These methods are on IndexWriter as
# well as Index for convenience, so they're broken out here.

class DeletionMixin(object):
    """Mix-in for classes that support deleting documents from self.segments."""
    
    def delete_document(self, docnum, delete = True):
        """Deletes a document by number."""
        self.segments.delete_document(docnum, delete = delete)
    
    def deleted_count(self):
        """Returns the total number of deleted documents in this index.
        """
        return self.segments.deleted_count()
    
    def is_deleted(self, docnum):
        """Returns True if a given document number is deleted but
        not yet optimized out of the index.
        """
        return self.segments.is_deleted(docnum)
    
    def has_deletions(self):
        """Returns True if this index has documents that are marked
        deleted but haven't been optimized out of the index yet.
        """
        return self.segments.has_deletions()
    
    def delete_by_term(self, fieldname, text):
        """Deletes any documents containing "term" in the "fieldname"
        field. This is useful when you have an indexed field containing
        a unique ID (such as "pathname") for each document.
        
        :*returns*: the number of documents deleted.
        """
        
        from whoosh.query import Term
        q = Term(fieldname, text)
        return self.delete_by_query(q)
    
    def delete_by_query(self, q):
        """Deletes any documents matching a query object.
        
        :*returns*: the number of documents deleted.
        """
        
        count = 0
        for docnum in q.docs(self._searcher):
            self.delete_document(docnum)
            count += 1
        return count


# Index class

class Index(DeletionMixin):
    """Represents an indexed collection of documents.
    """
    
    def __init__(self, storage, schema = None, create = False, indexname = _DEF_INDEX_NAME):
        """
        :storage: The store.Storage object in which this index resides.
            See the store module for more details.
        :schema: A fields.Schema object defining the fields of this index. If you omit
            this argument for an existing index, the object will load the pickled Schema
            object that was saved with the index. If you are creating a new index
            (create = True), you must supply this argument.
        :create: Whether to create a new index. If this is True, you must supply
            a Schema instance using the schema keyword argument.
        :indexname: An optional name to use for the index. Use this if you need
            to keep multiple indexes in the same storage object.
        """
        
        self.storage = storage
        self.indexname = indexname
        
        if schema is not None and not isinstance(schema, fields.Schema):
            raise ValueError("%r is not a Schema object" % schema)
        
        self.generation = self.latest_generation()
        
        if create:
            if schema is None:
                raise IndexError("To create an index you must specify a schema")
            
            self.schema = schema
            self.generation = 0
            self.segment_counter = 0
            self.segments = SegmentSet()
            
            # Clear existing files
            self.unlock()
            prefix = "_%s_" % self.indexname
            for filename in self.storage:
                if filename.startswith(prefix):
                    storage.delete_file(filename)
            
            self._write()
        elif self.generation >= 0:
            self._read(schema)
        else:
            raise EmptyIndexError
        
        # Open a searcher for this index. This is used by the
        # deletion methods, but mostly it's to keep the underlying
        # files open so they don't get deleted from underneath us.
        self._searcher = self.searcher()
        
        self.segment_num_lock = Lock()
    
    def __del__(self):
        if hasattr(self, "_searcher") and self._searcher and not self._searcher.is_closed:
            self._searcher.close()
    
    def close(self):
        self._searcher.close()
    
    def latest_generation(self):
        """Returns the generation number of the latest generation of this
        index.
        """
        
        pattern = _toc_pattern(self.indexname)
        
        max = -1
        for filename in self.storage:
            m = pattern.match(filename)
            if m:
                num = int(m.group(1))
                if num > max: max = num
        return max
    
    def refresh(self):
        """Returns a new Index object representing the latest generation
        of this index (if this object is the latest generation, returns
        self).
        :*returns*: index.Index
        """
        
        if not self.up_to_date():
            return self.__class__(self.storage, indexname = self.indexname)
        else:
            return self
    
    def up_to_date(self):
        """Returns True if this object represents the latest generation of
        this index. Returns False if this object is not the latest
        generation (that is, someone else has updated the index since
        you opened this object).
        """
        return self.generation == self.latest_generation()
    
    def _write(self):
        # Writes the content of this index to the .toc file.
        for field in self.schema:
            field.clean()
        stream = self.storage.create_file(self._toc_filename())
        
        stream.write_varint(_int_size)
        stream.write_varint(_ulong_size)
        stream.write_varint(_float_size)
        stream.write_string(byteorder)
        
        stream.write_int(_index_version)
        stream.write_string(cPickle.dumps(self.schema, -1))
        stream.write_int(self.generation)
        stream.write_int(self.segment_counter)
        stream.write_pickle(self.segments)
        stream.close()
    
    def _read(self, schema):
        # Reads the content of this index from the .toc file.
        stream = self.storage.open_file(self._toc_filename())
        
        if stream.read_varint() != _int_size or \
           stream.read_varint() != _ulong_size or \
           stream.read_varint() != _float_size or \
           stream.read_string() != byteorder:
            raise IndexError("Index was created on a different architecture")
        
        version = stream.read_int()
        if version != _index_version:
            raise IndexError("Don't know how to read index version %s" % version)
        
        # If the user supplied a schema object with the constructor,
        # don't load the pickled schema from the saved index.
        if schema:
            self.schema = schema
            stream.skip_string()
        else:
            self.schema = cPickle.loads(stream.read_string())
        
        generation = stream.read_int()
        assert generation == self.generation
        self.segment_counter = stream.read_int()
        self.segments = stream.read_pickle()
        stream.close()
    
    def _next_segment_name(self):
        #Returns the name of the next segment in sequence.
        generalcounter.increment("nextsegment")
        return str(generalcounter.get_count("nextsegment"))
    
    def _toc_filename(self):
        # Returns the computed filename of the TOC for this
        # index name and generation.
        return "_%s_%s.toc" % (self.indexname, self.generation)
    
    def last_modified(self):
        """Returns the last modified time of the .toc file.
        """
        return self.storage.file_modified(self._toc_filename())
    
    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self.storage, self.indexname)
    
    def lock(self):
        """Locks this index for writing, or raises an error if the index
        is already locked. Returns true if the index was successfully
        locked.
        """
        return self.storage.lock("_%s_LOCK" % self.indexname)
    
    def unlock(self):
        """Unlocks the index. Only call this if you were the one who locked
        it (without getting an exception) in the first place!
        """
        self.storage.unlock("_%s_LOCK" % self.indexname)
    
    def is_empty(self):
        """Returns True if this index is empty (that is, it has never
        had any documents successfully written to it.
        """
        return len(self.segments) == 0
    
    def optimize(self):
        """Optimizes this index's segments. This will fail if the index
        is already locked for writing.
        """
        
        if len(self.segments) < 2 and not self.segments.has_deletions():
            return
        
        from whoosh import writing
        w = writing.IndexWriter(self)
        w.commit(writing.OPTIMIZE)
    
    def commit(self, new_segments = None):
        """Commits pending edits (such as deletions) to this index object.
        Raises OutOfDateError if this index is not the latest generation
        (that is, if someone has updated the index since you opened
        this object).
        
        :new_segments: a replacement SegmentSet. This is used by
            IndexWriter to update the index after it finishes
            writing.
        """
        
        self._searcher.close()
        
        if not self.up_to_date():
            raise OutOfDateError
        
        if new_segments:
            self.segments = new_segments
        
        self.generation += 1
        self._write()
        self.clean_files()
        
        self._searcher = self.searcher()
    
    def clean_files(self):
        """Attempts to remove unused index files (called when a new generation
        is created). If existing Index and/or reader objects have the files
        open, they may not get deleted immediately (i.e. on Windows)
        but will probably be deleted eventually by a later call to clean_files.
        """
        
        storage = self.storage
        current_segment_names = set([s.name for s in self.segments])
        
        tocpattern = _toc_pattern(self.indexname)
        segpattern = _segment_pattern()
        
        for filename in storage:
            m = tocpattern.match(filename)
            if m:
                num = int(m.group(1))
                if num != self.generation:
                    try:
                        storage.delete_file(filename)
                    except WindowsError:
                        # Another process still has this file open
                        pass
            else:
                m = segpattern.match(filename)
                if m:
                    name = m.group(1)
                    if name not in current_segment_names:
                        try:
                            storage.delete_file(filename)
                        except WindowsError:
                            # Another process still has this file open
                            pass
    
    def doc_count_all(self):
        """Returns the total number of documents, DELETED OR UNDELETED,
        in this index.
        """
        return self.segments.doc_count_all()
    
    def doc_count(self):
        """Returns the total number of UNDELETED documents in this index.
        """
        return self.segments.doc_count()
    
    def max_weight(self):
        """Returns the maximum term weight in this index.
        This is used by some scoring algorithms.
        """
        return self.segments.max_weight()
    
    def field_length(self, fieldid):
        """Returns the total number of terms in a given field.
        This is used by some scoring algorithms. Note that this
        necessarily includes terms in deleted documents.
        """
        
        fieldnum = self.schema.to_number(fieldid)
        return sum(s.field_length(fieldnum) for s in self.segments)
    
    def term_reader(self):
        """Returns a TermReader object for this index.
        
        :*returns*: reading.TermReader
        """
        
        from whoosh import reading
        segments = self.segments
        
        if len(segments) == 1:
            return reading.TermReader(self.storage, segments[0], self.schema)
        else:
            term_readers = [reading.TermReader(self.storage, s, self.schema)
                            for s in segments]
            doc_offsets = segments.doc_offsets()
            return reading.MultiTermReader(term_readers, doc_offsets, self.schema)
    
    def doc_reader(self):
        """Returns a DocReader object for this index.
        
        :*returns*: reading.DocReader
        """
        
        from whoosh import reading
        schema = self.schema
        segments = self.segments
        if len(segments) == 1:
            return reading.DocReader(self.storage, segments[0], schema)
        else:
            doc_readers = [reading.DocReader(self.storage, s, self.schema)
                           for s in segments]
            doc_offsets = segments.doc_offsets()
            return reading.MultiDocReader(doc_readers, doc_offsets, schema)
    
    def searcher(self, **kwargs):
        """Returns a Searcher object for this index. Keyword arguments
        are passed to the Searcher object's constructor.
        
        :*returns*: searching.Searcher
        """
        
        from whoosh.searching import Searcher
        return Searcher(self, **kwargs)
    
    def writer(self, **kwargs):
        """Returns an IndexWriter object for this index.
        
        :*returns*: writing.IndexWriter
        """
        from whoosh.writing import IndexWriter
        return IndexWriter(self, **kwargs)
    
    def find(self, querystring, parser = None, **kwargs):
        """Parses querystring, runs the query in this index, and returns a
        Result object. Any additional keyword arguments are passed to
        Searcher.search() along with the parsed query.

        :querystring: The query string to parse and search for.
        :parser: A Parser object to use to parse 'querystring'.
            The default is to use a standard qparser.QueryParser.
            This object must implement a parse(str) method which returns a
            query.Query instance.
        :*returns*: searching.Results
        """

        if parser is None:
            from whoosh.qparser import QueryParser
            parser = QueryParser(self.schema)
            
        return self._searcher.search(parser.parse(querystring), **kwargs)


# SegmentSet object

class SegmentSet(object):
    """This class is never instantiated by the user. It is used by the Index
    object to keep track of the segments in the index.
    """

    def __init__(self, segments = None):
        if segments is None:
            self.segments = []
        else:
            self.segments = segments
        
        self._doc_offsets = self.doc_offsets()
    
    def __repr__(self):
        return repr(self.segments)
    
    def __len__(self):
        """:*returns*: the number of segments in this set."""
        return len(self.segments)
    
    def __iter__(self):
        return iter(self.segments)
    
    def __getitem__(self, n):
        return self.segments.__getitem__(n)
    
    def append(self, segment):
        """Adds a segment to this set."""
        
        self.segments.append(segment)
        self._doc_offsets = self.doc_offsets()
    
    def _document_segment(self, docnum):
        """Returns the index.Segment object containing the given document
        number.
        """
        
        offsets = self._doc_offsets
        if len(offsets) == 1: return 0
        return bisect_right(offsets, docnum) - 1
    
    def _segment_and_docnum(self, docnum):
        """Returns an (index.Segment, segment_docnum) pair for the
        segment containing the given document number.
        """
        
        segmentnum = self._document_segment(docnum)
        offset = self._doc_offsets[segmentnum]
        segment = self.segments[segmentnum]
        return segment, docnum - offset
    
    def copy(self):
        """:*returns*: a deep copy of this set."""
        return self.__class__([s.copy() for s in self.segments])
    
    def doc_offsets(self):
        # Recomputes the document offset list. This must be called if you
        # change self.segments.
        offsets = []
        base = 0
        for s in self.segments:
            offsets.append(base)
            base += s.doc_count_all()
        return offsets
    
    def doc_count_all(self):
        """
        :*returns*: the total number of documents, DELETED or
            UNDELETED, in this set.
        """
        return sum(s.doc_count_all() for s in self.segments)
    
    def doc_count(self):
        """
        :*returns*: the number of undeleted documents in this set.
        """
        return sum(s.doc_count() for s in self.segments)
    
    
    def max_weight(self):
        """
        :*returns*: the maximum frequency of any term in the set.
        """
        
        if not self.segments:
            return 0
        return max(s.max_weight for s in self.segments)
    
    def has_deletions(self):
        """
        :*returns*: True if this index has documents that are marked
            deleted but haven't been optimized out of the index yet.
            This includes deletions that haven't been written to disk
            with Index.commit() yet.
        """
        return any(s.has_deletions() for s in self.segments)
    
    def delete_document(self, docnum, delete = True):
        """Deletes a document by number.

        You must call Index.commit() for the deletion to be written to disk.
        """
        
        segment, segdocnum = self._segment_and_docnum(docnum)
        segment.delete_document(segdocnum, delete = delete)
    
    def deleted_count(self):
        """
        :*returns*: the total number of deleted documents in this index.
        """
        return sum(s.deleted_count() for s in self.segments)
    
    def is_deleted(self, docnum):
        """
        :*returns*: True if a given document number is deleted but not yet
            optimized out of the index.
        """
        
        segment, segdocnum = self._segment_and_docnum(docnum)
        return segment.is_deleted(segdocnum)
    

class Segment(object):
    """Do not instantiate this object directly. It is used by the Index
    object to hold information about a segment. A list of objects of this
    class are pickled as part of the TOC file.
    
    The TOC file stores a minimal amount of information -- mostly a list of
    Segment objects. Segments are the real reverse indexes. Having multiple
    segments allows quick incremental indexing: just create a new segment for
    the new documents, and have the index overlay the new segment over previous
    ones for purposes of reading/search. "Optimizing" the index combines the
    contents of existing segments into one (removing any deleted documents
    along the way).
    """
    
    def __init__(self, name, max_doc, max_weight, field_length_totals,
                 deleted = None):
        """
        :name: The name of the segment (the Index object computes this from its
            name and the generation).
        :max_doc: The maximum document number in the segment.
        :term_count: Total count of all terms in all documents.
        :max_weight: The maximum weight of any term in the segment. This is used
            by some scoring algorithms.
        :field_length_totals: A dictionary mapping field numbers to the total
            number of terms in that field across all documents in the segment.
        :deleted: A collection of deleted document numbers, or None
            if no deleted documents exist in this segment.
        """
        
        self.name = name
        self.max_doc = max_doc
        self.max_weight = max_weight
        self.field_length_totals = field_length_totals
        self.deleted = deleted
        
        self.doclen_filename = self.name + ".dci"
        self.docs_filename = self.name + ".dcz"
        self.term_filename = self.name + ".tiz"
        self.vector_filename = self.name + ".fvz"
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.name)
    
    def copy(self):
        return Segment(self.name, self.max_doc,
                       self.max_weight, self.field_length_totals,
                       self.deleted)
    
    def doc_count_all(self):
        """
        :*returns*: the total number of documents, DELETED OR UNDELETED,
            in this segment.
        """
        return self.max_doc
    
    def doc_count(self):
        """:*returns*: the number of (undeleted) documents in this segment."""
        return self.max_doc - self.deleted_count()
    
    def has_deletions(self):
        """:*returns*: True if any documents in this segment are deleted."""
        return self.deleted_count() > 0
    
    def deleted_count(self):
        """:*returns*: the total number of deleted documents in this segment."""
        if self.deleted is None: return 0
        return len(self.deleted)
    
    def field_length(self, fieldnum):
        """
        :fieldnum: the internal number of the field.
        :*returns*: the total number of terms in the given field across all
            documents in this segment.
        """
        return self.field_length_totals.get(fieldnum, 0)
    
    def delete_document(self, docnum, delete = True):
        """Deletes the given document number. The document is not actually
        removed from the index until it is optimized.

        :docnum: The document number to delete.
        :delete: If False, this undeletes a deleted document.
        """
        
        if delete:
            if self.deleted is None:
                self.deleted = set()
            elif docnum in self.deleted:
                raise KeyError("Document %s in segment %r is already deleted"
                               % (docnum, self.name))
            
            self.deleted.add(docnum)
        else:
            if self.deleted is None or docnum not in self.deleted:
                raise KeyError("Document %s is not deleted" % docnum)
            
            self.deleted.remove(docnum)
    
    def is_deleted(self, docnum):
        """:*returns*: True if the given document number is deleted."""
        
        if self.deleted is None: return False
        return docnum in self.deleted

# Debugging functions

        
if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = morph_en
import re

# Rule exceptions

exceptions = [
        "a",
        "abandoner abandon abandons abandoned abandoning abandonings abandoners",
        "abdomen abdomens",
        "about",
        "above",
        "acid acids acidic acidity acidities",
        "across",
        "act acts acted acting actor actors",
        "ad ads", 
        "add adds added adding addings addition additions adder adders",
        "advertise advertises advertised advertising advertiser advertisers advertisement advertisements advertisings",
        "after",
        "again",
        "against",
        "ago",
        "all",
        "almost",
        "along",
        "already",
        "also",
        "although",
        "alumna alumnae alumnus alumni",
        "always",
        "amen amens",
        "amidships",
        "amid amidst",
        "among amongst",
        "an",
        "analysis analyses",
        "and",
        "another other others",
        "antenna antennas antennae",
        "antitheses antithesis",
        "any",
        "anyone anybody",
        "anything",
        "appendix appendixes appendices",
        "apropos",
        "aquarium aquariums aquaria",
        "argument arguments argue argues argued arguing arguings arguer arguers",
        "arise arises arose arisen ariser arisers arising arisings",
        "around",
        "as",
        "asbestos",
        "at",
        "atlas atlases",
        "auger augers augered augering augerings augerer augerers",
        "augment augments augmented augmenting augmentings augmentation augmentations augmenter augmenters",
        "automata automaton automatons",
        "automation automating automate automates automated automatic",
        "avoirdupois",
        "awake awakes awoke awaked awoken awaker awakers awaking awakings awakening awakenings",
        "away",
        "awful awfully awfulness",
        "axis axes axises",
        "bacillus bacilli",
        "bacterium bacteria",
        "bad worse worst badly badness",
        "bas",
        "bases basis",
        "bases base based basing basings basely baseness basenesses basement basements baseless basic basics",
        "be am are is was were been being",
        "bear bears bore borne bearing bearings bearer bearers",
        "beat beats beaten beating beatings beater beaters",
        "because",
        "become becomes became becoming",
        "beef beefs beeves beefed beefing",
        "beer beers",
        "before",
        "begin begins began begun beginning beginnings beginner beginners",
        "behalf behalves",
        "being beings",
        "bend bends bent bending bendings bender benders",
        "bereave bereaves bereaved bereft bereaving bereavings bereavement bereavements",
        "beside besides",
        "best bests bested besting",
        "bet bets betting bettor bettors",
        "betimes",
        "between",
        "beyond",
        "bid bids bade bidden bidding biddings bidder bidders",
        "bier biers",
        "bind binds bound binding bindings binder binders",
        "bit bits",
        "bite bites bit bitten biting bitings biter biters",
        "blackfoot blackfeet",
        "bleed bleeds bled bleeding bleedings bleeder bleeders",
        "blow blows blew blown blowing blowings blower blowers",
        "bookshelf bookshelves",
        "both",
        "bound bounds bounded bounding boundings bounder bounders boundless", 
        "bourgeois bourgeoisie",
        "bra bras",
        "brahman brahmans",
        "break breaks broke broken breaking breakings breaker breakers",
        "breed breeds bred breeding breedings breeder breeders",
        "bring brings brought bringing bringings bringer bringers",
        "build builds built building buildings builder builders",
        "bus buses bused bussed busing bussing busings bussings buser busers busser bussers",
        "buss busses bussed bussing bussings busser bussers",
        "but",
        "buy buys bought buying buyings buyer buyers",
        "by",
        "calf calves calved calving calvings calver calvers",
        "can cans canned canning cannings canner canners",
        "can could cannot",
        "canoes canoe canoed canoeing canoeings canoer canoers",
        "catch catches caught catching catchings catcher catchers",
        "cement cements cemented cementing cementings cementer cementers",
        "cent cents",
        "center centers centered centering centerings centerless",
        "child children childless childish childishly",
        "choose chooses chose chosen choosing choosings chooser choosers",
        "cling clings clung clinging clingings clinger clingers",
        "colloquium colloquia colloquiums",
        "come comes came coming comings comer comers",
        "comment comments commented commenting commentings commenter commenters",
        "compendium compendia compendiums",
        "complement complements complemented complementing complementings complementer complementers complementary",
        "compliment compliments complimented complimenting complimentings complimenter complimenters complimentary",
        "concerto concertos concerti",
        "condiment condiments",
        "corps",
        "cortex cortices cortexes cortical",
        "couscous",
        "creep creeps crept creeping creepings creeper creepers creepy",
        "crisis crises",
        "criterion criteria criterial",
        "cryptanalysis cryptanalyses",
        "curriculum curricula curriculums curricular",
        "datum data",
        "day days daily",
        "deal deals dealt dealing dealings dealer dealers",
        "decrement decrements decremented decrementing decrementings decrementer decrementers decremental",
        "deer deers",
        "demented dementia",
        "desideratum desiderata",
        "diagnosis diagnoses diagnose diagnosed diagnosing diagnostic",
        "dialysis dialyses",
        "dice dices diced dicing dicings dicer dicers",
        "die dice",
        "die dies died dying dyings",
        "dig digs dug digging diggings digger diggers",
        "dive dives diver divers dove dived diving divings",
        "divest divests divester divesters divested divesting divestings divestment divestments",
        "do does did done doing doings doer doers",
        "document documents documented documenting documentings documenter documenters documentation documentations documentary",
        "doe does",
        "dove doves",
        "downstairs",
        "dozen",
        "draw draws drew drawn drawing drawings drawer drawers",
        "drink drinks drank drunk drinking drinkings drinker drinkers",
        "drive drives drove driven driving drivings driver drivers driverless",
        "due dues duly",
        "during",
        "e",
        "each",
        "eager eagerer eagerest eagerly eagerness eagernesses",
        "early earlier earliest",
        "easement easements",
        "eat eats ate eaten eating eatings eater eaters",
        "effluvium effluvia",
        "either",
        "element elements elementary",
        "elf elves elfen",
        "ellipse ellipses elliptic elliptical elliptically",
        "ellipsis ellipses elliptic elliptical elliptically",
        "else",
        "embolus emboli embolic embolism",
        "emolument emoluments",
        "emphasis emphases",
        "employ employs employed employing employer employers employee employees employment employments employable",
        "enough",
        "equilibrium equilibria equilibriums",
        "erratum errata",
        "ever",
        "every",
        "everything",
        "exotic exotically exoticness exotica",
        "experiment experiments experimented experimenting experimentings experimenter experimenters experimentation experimental",
        "extra extras",
        "fall falls fell fallen falling fallings faller fallers",
        "far farther farthest",
        "fee fees feeless",
        "feed feeds fed feeding feedings feeder feeders",
        "feel feels felt feeling feelings feeler feelers",
        "ferment ferments fermented fermenting fermentings fermentation fermentations fermenter fermenters",
        "few fewer fewest",
        "fight fights fought fighting fightings fighter fighters",
        "figment figments",
        "filament filaments",
        "find finds found finding findings finder finders",
        "firmament firmaments",
        "flee flees fled fleeing fleeings",
        "fling flings flung flinging flingings flinger flingers",
        "floe floes",
        "fly flies flew flown flying flyings flier fliers flyer flyers",
        "focus foci focuses focused focusing focusses focussed focussing focuser focal",
        "foment foments fomented fomenting fomentings fomenter fomenters",
        "foot feet",
        "foot foots footed footing footer footers",
        "footing footings footer footers",
        "for",
        "forbid forbids forbade forbidden forbidding forbiddings forbidder forbidders",
        "foresee foresaw foreseen foreseeing foreseeings foreseer foreseers",
        "forest forests forester foresting forestation forestations",
        "forget forgets forgot forgotten forgetting forgettings forgetter forgetters forgetful",
        "forsake forsakes forsook forsaken forsaking forsakings forsaker forsakers",
        "found founds founded founding foundings founder founders",
        "fragment fragments fragmented fragmenting fragmentings fragmentation fragmentations fragmenter fragmenters",
        "free frees freer freest freed freeing freely freeness freenesses",
        "freeze freezes froze frozen freezing freezings freezer freezers",
        "from",
        "full fully fuller fullest",
        "fuller fullers full fulls fulled fulling fullings",
        "fungus fungi funguses fungal",
        "gallows",
        "ganglion ganglia ganglions ganglionic",
        "garment garments",
        "gas gasses gassed gassing gassings gasser gassers",
        "gas gases gasses gaseous gasless",
        "gel gels gelled gelling gellings geller gellers",
        "german germans germanic germany German Germans Germanic Germany",
        "get gets got gotten getting gettings getter getters",
        "give gives gave given giving givings giver givers",
        "gladiolus gladioli gladioluses gladiola gladiolas gladiolae",
        "glans glandes",
        "gluiness gluey glue glues glued gluing gluings gluer gluers",
        "go goes went gone going goings goer goers",
        "godchild godchildren",
        "good better best goodly goodness goodnesses",
        "goods",
        "goose geese",
        "goose gooses goosed goosing goosings gooser goosers",
        "grandchild grandchildren",
        "grind grinds ground grinding grindings grinder grinders",
        "ground grounds grounded grounding groundings grounder grounders groundless",
        "grow grows grew grown growing growings grower growers growth",
        "gum gums gummed gumming gummings gummer gummers",
        "half halves",
        "halve halves halved halving halvings halver halvers",
        "hang hangs hung hanged hanging hangings hanger hangers",
        "have has had having havings haver havers",
        "he him his himself",
        "hear hears heard hearing hearings hearer hearers",
        "here",
        "hide hides hid hidden hiding hidings hider hiders",
        "hippopotamus hippopotami hippopotamuses", 
        "hold holds held holding holdings holder holders",
        "honorarium honoraria honorariums",
        "hoof hoofs hooves hoofed hoofing hoofer hoofers",
        "how",
        "hum hums hummed humming hummings hummer hummers",
        "hymen hymens hymenal",
        "hypotheses hypothesis hypothesize hypothesizes hypothesized hypothesizer hypothesizing hypothetical hypothetically",
        "i",
        "if iffy",
        "impediment impediments",
        "implement implements implemented implementing implementings implementation implementations implementer implementers",
        "imply implies implied implying implyings implier impliers",
        "in inner",
        "inclement",
        "increment increments incremented incrementing incrementings incrementer incrementers incremental incrementally",
        "index indexes indexed indexing indexings indexer indexers",
        "index indexes indices indexical indexicals",
        "indoor indoors",
        "instrument instruments instrumented instrumenting instrumentings instrumenter instrumenters instrumentation instrumentations instrumental",
        "integument integumentary",
        "into",
        "it its itself",
            "java",
        "july julys",
        "keep keeps kept keeping keepings keeper keepers",
        "knife knifes knifed knifing knifings knifer knifers",
        "knife knives",
        "know knows knew known knowing knowings knower knowers knowledge",
        "lament laments lamented lamenting lamentings lamentation lamentations lamenter lamenters lamentable lamentably",
        "larva larvae larvas larval",
        "late later latest lately lateness",
        "latter latterly",
        "lay lays laid laying layer layers",
        "layer layers layered layering layerings",
        "lead leads led leading leadings leader leaders leaderless",
        "leaf leafs leafed leafing leafings leafer leafers",
        "leaf leaves leafless",
        "leave leaves left leaving leavings leaver leavers",
        "lend lends lent lending lendings lender lenders",
        "less lesser least",
        "let lets letting lettings",
        "lie lies lay lain lying lier liers",
        "lie lies lied lying liar liars",
        "life lives lifeless",
        "light lights lit lighted lighting lightings lightly lighter lighters lightness lightnesses lightless",
        "likely likelier likeliest",
        "limen limens",
        "lineament lineaments",
        "liniment liniments",
        "live alive living",
        "live lives lived living livings",
        "liver livers",
        "loaf loafs loafed loafing loafings loafer loafers",
        "loaf loaves",
        "logic logics logical logically",
        "lose loses lost losing loser losers loss losses",
        "louse lice",
        "lumen lumens",
        "make makes made making makings maker makers",
        "man mans manned manning mannings",
        "man men",
        "manly manlier manliest manliness manful manfulness manhood",
        "manic manically",
        "manner manners mannered mannerly mannerless mannerful",
        "many",
        "matrix matrices matrixes",
        "may might",
        "maximum maxima maximums maximal maximize maximizes maximized maximizing",
        "mean means meant meaning meanings meaningless meaningful",
        "mean meaner meanest meanly meanness meannesses",
        "median medians medianly medial",
        "medium media mediums",
        "meet meets met meeting meetings",
        "memorandum memoranda memorandums",
        "mere merely",
        "metal metals metallic",
        "might mighty mightily",
        "millenium millennia milleniums millennial",
        "mine mines mined mining minings miner miners",
        "mine my our ours",
        "minimum minima minimums minimal",
        "minus minuses",
        "miscellaneous miscellanea miscellaneously miscellaneousness miscellany",
        "molest molests molested molesting molestings molester molesters",
        "moment moments",
        "monument monuments monumental",
        "more most",
        "mouse mice mouseless",
        "much",
        "multiply multiplies multiplier multipliers multiple multiples multiplying multiplyings multiplication multiplications",
        "mum mums mummed mumming mummings mummer mummers",
        "must musts",
        "neither",
        "nemeses nemesis",
        "neurosis neuroses neurotic neurotics",
        "nomen",
        "none",
        "nos no noes",
        "not",
        "nothing nothings nothingness",
        "now",
        "nowadays",
        "nucleus nuclei nucleuses nuclear",
        "number numbers numbered numbering numberings numberless",
        "nutriment nutriments nutrient nutrients nutrition nutritions",
        "oasis oases",
        "octopus octopi octopuses",
        "of",
        "off",
        "offer offers offered offering offerings offerer offerers offeror offerors",
        "often",
        "oftentimes",
        "ointment ointments",
        "omen omens",
        "on",
        "once",
        "only",
        "ornament ornaments ornamented ornamenting ornamentings ornamentation ornamenter ornamenters ornamental",
        "outdoor outdoors",
        "outlay outlays",
        "outlie outlies outlay outlied outlain outlying outlier outliers",
        "ovum ova",
        "ox oxen",
        "parentheses parenthesis",
        "parliament parliaments parliamentary",
        "passerby passer-by passersby passers-by",
        "past pasts",
        "pay pays paid paying payings payer payers payee payees payment payments",
        "per",
        "perhaps",
        "person persons people",
        "phenomenon phenomena phenomenal",
        "pi",
        "picnic picnics picnicker picnickers picnicked picnicking picnickings",
        "pigment pigments pigmented pigmenting pigmentings pigmenter pigmenters pigmentation pigmentations",
        "please pleases pleased pleasing pleasings pleaser pleasers pleasure pleasures pleasuring pleasurings pleasant pleasantly pleasureless pleasureful",
        "plus pluses plusses",
        "polyhedra polyhedron polyhedral",
        "priest priests priestly priestlier priestliest priestliness priestless",
        "prognosis prognoses",
        "prostheses prosthesis",
        "prove proves proved proving provings proofs proof prover provers provable",
        "psychosis psychoses psychotic psychotics",
        "qed",
        "quiz quizzes quizzed quizzing quizzings quizzer quizzers",
        "raiment",
        "rather",
        "re",
        "real really",
        "redo redoes redid redone redoing redoings redoer redoers",
        "regiment regiments regimented regimenting regimenter regimenters regimentation regimental",
        "rendezvous",
        "requiz requizzes requizzed requizzing requizzings requizzer requizzers",
        "ride rides rode ridden riding ridings rider riders rideless",
        "ring rings rang rung ringing ringings ringer ringers ringless",
        "rise rises rose risen rising risings riser risers",
        "rose roses",
        "rudiment rudiments rudimentary",
        "rum rums rummed rumming rummings rummer rummers",
        "run runs ran running runnings runner runners",
        "sacrament sacraments sacramental",
        "same sameness",
        "sans",
        "saw saws sawed sawn sawing sawings sawyer sawyers",
        "say says said saying sayings sayer sayers",
        "scarf scarfs scarves scarfless",
        "schema schemata schemas",
        "sediment sediments sedimentary sedimentation sedimentations",
        "see sees saw seen seeing seeings seer seers",
        "seek seeks sought seeking seekings seeker seekers",
        "segment segments segmented segmenting segmentings segmenter segmenters segmentation segmentations",
        "self selves selfless",
        "sell sells sold selling sellings seller sellers",
        "semen",
        "send sends sent sending sendings sender senders",
        "sentiment sentiments sentimental",
        "series",
        "set sets setting settings",
        "several severally",
        "sew sews sewed sewn sewing sewings sewer sewers",
        "sewer sewers sewerless",
        "shake shakes shook shaken shaking shakings shaker shakers",
        "shall should",
        "shaman shamans",
        "shave shaves shaved shaven shaving shavings shaver shavers shaveless",
        "she her hers herself",
        "sheaf sheaves sheafless",
        "sheep",
        "shelf shelves shelved shelfing shelvings shelver shelvers shelfless",
        "shine shines shined shone shining shinings shiner shiners shineless",
        "shoe shoes shoed shod shoeing shoeings shoer shoers shoeless",
        "shoot shoots shot shooting shootings shooter shooters",
        "shot shots",
        "show shows showed shown showing showings shower showers",
        "shower showers showery showerless",
        "shrink shrinks shrank shrunk shrinking shrinkings shrinker shrinkers shrinkable",
        "sideways",
        "simply simple simpler simplest",
        "since",
        "sing sings sang sung singing singings singer singers singable",
        "sink sinks sank sunk sinking sinkings sinker sinkers sinkable",
        "sit sits sat sitting sittings sitter sitters",
        "ski skis skied skiing skiings skier skiers skiless skiable",
        "sky skies",
        "slay slays slew slain slaying slayings slayer slayers",
        "sleep sleeps slept sleeping sleepings sleeper sleepers sleepless",
        "so",
        "some",
        "something",
        "sometime sometimes",
        "soon",
        "spa spas",
        "speak speaks spoke spoken speaking speakings speaker speakers",
        "species specie",
        "spectrum spectra spectrums",
        "speed speeds sped speeded speeding speedings speeder speeders",
        "spend spends spent spending spendings spender spenders spendable",
        "spin spins spun spinning spinnings spinner spinners",
        "spoke spokes",
        "spring springs sprang sprung springing springings springer springers springy springiness",
        "staff staffs staves staffed staffing staffings staffer staffers",
        "stand stands stood standing standings",
        "stasis stases",
        "steal steals stole stolen stealing stealings stealer stealers",
        "stick sticks stuck sticking stickings sticker stickers",
        "stigma stigmata stigmas stigmatize stigmatizes stigmatized stigmatizing",
        "stimulus stimuli",
        "sting stings stung stinging stingings stinger stingers",
        "stink stinks stank stunk stinking stinkings stinker stinkers",
        "stomach stomachs",
        "stratum strata stratums",
        "stride strides strode stridden striding stridings strider striders",
        "string strings strung stringing stringings stringer stringers stringless",
        "strive strives strove striven striving strivings striver strivers",
        "strum strums strummed strumming strummings strummer strummers strummable",
        "such",
        "suffer suffers suffered suffering sufferings sufferer sufferers sufferable",
        "suggest suggests suggested suggesting suggestings suggester suggesters suggestor suggestors suggestive suggestion suggestions suggestible suggestable",
        "sum sums summed summing summings summer summers",
        "summer summers summered summering summerings",
        "supplement supplements supplemented supplementing supplementings supplementation supplementer supplementers supplementary supplemental",
        "supply supplies supplied supplying supplyings supplier suppliers",
        "swear swears swore sworn swearing swearings swearer swearers",
        "sweep sweeps swept sweeping sweepings sweeper sweepers",
        "swell swells swelled swollen swelling swellings",
        "swim swims swam swum swimming swimmings swimmer swimmers swimable",
        "swine",
        "swing swings swung swinging swingings swinger swingers",
        "syllabus syllabi syllabuses",
        "symposium symposia symposiums",
        "synapse synapses",
        "synapsis synapses",
        "synopsis synopses",
        "synthesis syntheses",
        "tableau tableaux tableaus",
        "take takes took taken taking takings taker takers takable",
        "teach teaches taught teaching teachings teacher teachers teachable",
        "tear tears tore torn tearing tearings tearer tearers tearable",
        "tegument teguments",
        "tell tells told telling tellings teller tellers tellable",
        "temperament temperaments temperamental temperamentally",
        "tenement tenements",
        "the",
        "there theres",
        "theses thesis",
        "they them their theirs themselves",
        "thief thieves thieving thievings",
        "think thinks thought thinking thinker thinkers thinkable",
        "this that these those",
        "thought thoughts thougtful thoughtless",
        "throw throws threw thrown throwing throwings thrower throwers throwable",
        "tic tics",
        "tie ties tied tying tyings tier tiers tieable tieless",
        "tier tiers tiered tiering tierings tierer tierers",
        "to",
        "toe toes toed toeing toeings toer toers toeless",
        "together togetherness",
        "too",
        "tooth teeth toothless",
        "topaz topazes",
        "torment torments tormented tormenting tormentings tormenter tormenters tormentable",
        "toward towards",
        "tread treads trod trodden treading treadings treader treaders",
        "tread treads treadless retread retreads",
        "true truly trueness",
        "two twos",
        "u",
        "under",
        "underlay underlays underlaid underlaying underlayings underlayer underlayers",
        "underlie underlies underlay underlain underlying underlier underliers",
        "undo undoes undid undone undoing undoings undoer undoers undoable",
        "unrest unrestful",
        "until",
        "unto",
        "up",
        "upon",
        "upstairs",
        "use uses user users used using useful useless",
        "various variously",
        "vehement vehemently vehemence",
        "versus",
        "very",
        "visit visits visited visiting visitings visitor visitors",
        "vortex vortexes vortices",
        "wake wakes woke waked woken waking wakings waker wakers wakeful wakefulness wakefulnesses wakeable",
        "wear wears wore worn wearing wearings wearer wearers wearable",
        "weather weathers weathered weathering weatherly",
        "weave weaves wove woven weaving weavings weaver weavers weaveable",
        "weep weeps wept weeping weepings weeper weepers",
        "wharf wharfs wharves",
        "where wheres",
        "whereas whereases",
        "whether whethers",
        "while whiles whilst whiled whiling",
        "whiz whizzes whizzed whizzing whizzings whizzer whizzers",
        "who whom whos whose whoses",
        "why whys",
        "wife wives wifeless",
        "will wills willed willing willings willful",
        "will would",
        "win wins won winning winnings winner winners winnable",
        "wind winds wound winding windings winder winders windable",
        "wind winds windy windless",
        "with",
        "within",
        "without",
        "wolf wolves",
        "woman women womanless womanly",
        "wound wounds wounded wounding woundings",
        "write writes wrote written writing writings writer writers writeable",
        "yeses yes",
        "yet yets",
        "you your yours yourself"
        ]

_exdict = {}
for exlist in exceptions:
    for ex in exlist.split(" "):
        _exdict[ex] = exlist

# Programmatic rules

vowels = "aeiouy"
cons = "bcdfghjklmnpqrstvwxyz"

rules = (
         # Words ending in S
         
         # (e.g., happiness, business)
         (r"[%s].*[%s](iness)" % (vowels, cons), "y,ies,ier,iers,iest,ied,ying,yings,ily,inesses,iment,iments,iless,iful"),
         # (e.g., baseless, shoeless)
         (r"[%s].*(eless)" % vowels, "e,es,er,ers,est,ed,ing,ings,eing,eings,ely,eness,enesses,ement,ements,eness,enesses,eful"),
         # (e.g., gutless, hatless, spotless)
         (r"[%s][%s][bdgklmnprt]?(less)" % (cons, vowels), ",s,&er,&ers,&est,&ed,&ing,&ings,ly,ness,nesses,ment,ments,ful"),
         # (e.g., thoughtless, worthless)
         (r"[%s].*?(less)" % vowels, ",s,er,ers,est,ed,ing,ings,ly,ness,nesses,ment,ments,ful"),
         # (e.g., baseness, toeness)
         (r"[%s].*(eness)" % vowels, "e,es,er,ers,est,ed,ing,ings,eing,eings,ely,enesses,ement,ements,eless,eful"),
         # (e.g., bluntness, grayness)
         (r"[%s].*(ness)" % vowels, ",s,er,ers,est,ed,ing,ings,ly,nesses,ment,ments,less,ful"),
         # (e.g., albatross, kiss)
         (r"[%s]ss" % vowels, "es,er,ers,est,ed,ing,ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., joyous, fractious, gaseous)
         (r"[%s].*(ous)" % vowels, "ly,ness"),
         # (e.g., tries, unties, jollies, beauties)
         (r"(ies)", "y,ie,yer,yers,ier,iers,iest,ied,ying,yings,yness,iness,ieness,ynesses,inesses,ienesses,iment,iement,iments,iements,yless,iless,ieless,yful,iful,ieful"),
         # (e.g., crisis, kinesis)
         (r"[%s].*(sis)" % vowels, "ses,sises,sisness,sisment,sisments,sisless,sisful"),
         # (e.g., bronchitis, bursitis)
         (r"[%s].*(is)" % vowels, "es,ness,ment,ments,less,ful"),
         (r"[%s].*[cs]h(es)" % vowels, ",e,er,ers,est,ed,ing,ings,ly,ely,ness,eness,nesses,enesses,ment,ement,ments,ements,less,eless,ful,eful"),
         # (e.g., tokenizes) // adds British variations
         (r"[%s].*[%s](izes)" % (vowels, cons), "ize,izes,izer,izers,ized,izing,izings,ization,izations,ise,iser,isers,ised,ising,isings,isation,isations"),
         # (e.g., tokenises) // British variant  // ~expertise
         (r"[%s].*[%s](ises)" % (vowels, cons), "ize,izes,izer,izers,ized,izing,izings,ization,izations,ise,iser,isers,ised,ising,isings,isation,isations"),
         # (e.g., aches, arches)
         (r"[%s].*[jsxz](es)" % vowels, ",e,er,ers,est,ed,ing,ings,ly,ely,ness,eness,nesses,enesses,ment,ement,ments,ements,less,eless,ful,eful"),
         # (e.g., judges, abridges)
         (r"[%s].*dg(es)" % vowels, "e,er,ers,est,ed,ing,ings,ely,eness,enesses,ment,ments,ement,ements,eless,eful"),
         # (e.g., trees, races, likes, agrees) covers all other -es words
         (r"e(s)", ",*"),
         # (e.g., segments, bisegments, cosegments)
         (r"segment(s)", ",*"),
         # (e.g., pigments, depigments, repigments)
         (r"pigment(s)", ",*"),
         # (e.g., judgments, abridgments)
         (r"[%s].*dg(ments)" % vowels, "ment,*ments"),
         # (e.g., merriments, embodiments) -iment in turn will generate y and *y (redo y)
         (r"[%s].*[%s]iment(s)" % (vowels, cons), ",*"),
         # (e.g., atonements, entrapments)
         (r"[%s].*ment(s)" % vowels, ",*"),
         # (e.g., viewers, meters, traders, transfers)
         (r"[%s].*er(s)" % vowels, ",*"),
         # (e.g., unflags) polysyllables
         (r"[%s].*[%s][%s][bdglmnprt](s)" % (vowels, cons, vowels), ",*"),
         # (e.g., frogs) monosyllables
         (r"[%s][%s][bdglmnprt](s)" % (vowels, cons), ",*"),
         # (e.g., killings, muggings)
         (r"[%s].*ing(s)" % vowels, ",*"),
         # (e.g., hulls, tolls)
         (r"[%s].*ll(s)" % vowels, ",*"),
         # e.g., boas, polkas, spas) don't generate latin endings
         (r"a(s)", ",er,ers,est,ed,ing,ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., beads, toads)
         (r"[%s].*[%s].*(s)" % (vowels, cons), ",*"),
         # (e.g., boas, zoos)
         (r"[%s].*[%s](s)" % (cons, vowels), ",er,ers,est,ed,ing,ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., ss, sss, ssss) no vowel (vowel case is already handled above)
         (r"ss()", ""),
         # (e.g., cds, lcds, m-16s) no vowel (can be a plural noun, but not verb)
         (r"[%s].*[%s1234567890](s)" % (cons, cons), ""),
         
         # Words ending in E
         
         # (e.g., apple, so it doesn't include apply)
         (r"appl(e)", "es,er,ers,est,ed,ing,ings,ely,eness,enesses,ement,ements,eless,eful"),
         # (e.g., supple, so it doesn't include supply)
         (r"suppl(e)", "es,er,ers,est,ed,ing,ings,ely,eness,enesses,ement,ements,eless,eful"),
         # (e.g., able, abominable, fungible, table, enable, idle, subtle)
         (r"[%s].*[%s]l(e)" % (vowels, cons), "es,er,ers,est,ed,ing,ings,y,ely,eness,enesses,ement,ements,eless,eful"),
         # (e.g., bookie, magpie, vie)
         (r"(ie)", "ies,ier,iers,iest,ied,ying,yings,iely,ieness,ienesses,iement,iements,ieless,ieful"),
         # (e.g., dye, redye, redeye)
         (r"ye()", "s,r,rs,st,d,ing,ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., judge, abridge)
         (r"[%s].*dg(e)" % vowels, "es,er,ers,est,ed,ing,ings,ely,eness,enesses,ment,ments,less,ful,ement,ements,eless,eful"),
         # (e.g., true, due, imbue)
         (r"u(e)", "es,er,ers,est,ed,ing,ings,eing,eings,ly,ely,eness,enesses,ment,ments,less,ful,ement,ements,eless,eful"),
         # (e.g., tokenize) // adds British variations
         (r"[%s].*[%s](ize)" % (vowels, cons), "izes,izer,izers,ized,izing,izings,ization,izations,ise,ises,iser,isers,ised,ising,isings,isation,isations"),
         # (e.g., tokenise) // British variant  // ~expertise
         (r"[%s].*[%s](ise)" % (vowels, cons), "ize,izes,izer,izers,ized,izing,izings,ization,izations,ises,iser,isers,ised,ising,isings,isation,isations"),
         # (e.g., tree, agree, rage, horse, hoarse)
         (r"[%s].*[%s](e)", "es,er,ers,est,ed,ing,ings,eing,eings,ely,eness,enesses,ement,ements,eless,eful"),
         
         # Words ending in -ED
         
         # (e.g., agreed, freed, decreed, treed)
         (r"ree(d)", "ds,der,ders,ded,ding,dings,dly,dness,dnesses,dment,dments,dless,dful,,*"),
         # (e.g., feed, seed, Xweed)
         (r"ee(d)", "ds,der,ders,ded,ding,dings,dly,dness,dnesses,dment,dments,dless,dful"),
         # (e.g., tried)
         (r"[%s](ied)" % cons, "y,ie,ies,ier,iers,iest,ying,yings,ily,yly,iness,yness,inesses,ynesses,iment,iments,iless,iful,yment,yments,yless,yful"),
         # (e.g., controlled, fulfilled, rebelled)
         (r"[%s].*[%s].*l(led)" % (vowels, cons), ",s,er,ers,est,ing,ings,ly,ness,nesses,ment,ments,less,ful,&,&s,&er,&ers,&est,&ing,&ings,&y,&ness,&nesses,&ment,&ments,&ful"),
         # (e.g., pulled, filled, fulled)
         (r"[%s].*l(led)" % vowels, "&,&s,&er,&ers,&est,&ing,&ings,&y,&ness,&nesses,&ment,&ments,&ful"),
         # (e.g., hissed, grossed)
         (r"[%s].*s(sed)" % vowels, "&,&es,&er,&ers,&est,&ing,&ings,&ly,&ness,&nesses,&ment,&ments,&less,&ful"),
         # (e.g., hugged, trekked)
         (r"[%s][%s](?P<ed1>[bdgklmnprt])((?P=ed1)ed)", ",s,&er,&ers,&est,&ing,&ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., tokenize) // adds British variations
         (r"[%s].*[%s](ized)" % (vowels, cons), "izes,izer,izers,ize,izing,izings,ization,izations,ise,ises,iser,isers,ised,ising,isings,isation,isations"),
         # (e.g., tokenise) // British variant  // ~expertise
         (r"[%s].*[%s](ized)" % (vowels, cons), "ize,izes,izer,izers,ized,izing,izings,ization,izations,ises,iser,isers,ise,ising,isings,isation,isations"),
         # (e.g., spoiled, tooled, tracked, roasted, atoned, abridged)
         (r"[%s].*(ed)" % vowels, ",e,s,es,er,ers,est,ing,ings,ly,ely,ness,eness,nesses,enesses,ment,ement,ments,ements,less,eless,ful,eful"),
         # (e.g., bed, sled) words with a single e as the only vowel
         (r"ed()", "s,&er,&ers,&est,&ed,&ing,&ings,ly,ness,nesses,ment,ments,less,ful"),
         
         # Words ending in -ER
         
         # (e.g., altimeter, ammeter, odometer, perimeter)
         (r"meter()", "s,er,ers,ed,ing,ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., agreer, beer, budgeteer, engineer, freer)
         (r"eer()", "eers,eered,eering,eerings,eerly,eerness,eernesses,eerment,eerments,eerless,eerful,ee,ees,eest,eed,eeing,eeings,eely,eeness,eenesses,eement,eements,eeless,eeful,eerer,eerers,eerest"),
         # (e.g., acidifier, saltier)
         (r"[%s].*[%s](ier)" % (vowels, cons), "y,ie,ies,iest,ied,ying,yings,ily,yly,iness,yness,inesses,ynesses,yment,yments,yless,yful,iment,iments,iless,iful,iers,iered,iering,ierings,ierly,ierness,iernesses,ierment,ierments,ierless,ierful,ierer,ierers,ierest"),
         # (e.g., puller, filler, fuller)
         (r"[%s].*l(ler)" % vowels, "&,&s,&est,&ed,&ing,&ings,ly,lely,&ness,&nesses,&ment,&ments,&ful,&ers,&ered,&ering,&erings,&erly,&erness,&ernesses,&erments,&erless,&erful"),
         # (e.g., hisser, grosser)
         (r"[%s].*s(ser)" % vowels, "&,&es,&est,&ed,&ing,&ings,&ly,&ness,&nesses,&ment,&ments,&less,&ful,&ers,&ered,&ering,&erings,&erly,&erness,&ernesses,&erment,&erments,&erless,&erful"),
         # (e.g., bigger, trekker, hitter)
         (r"[%s][%s](?P<er1>[bdgkmnprt])((?P=er1)er)" % (cons, vowels), "s,&est,&ed,&ing,&ings,ly,ness,nesses,ment,ments,less,ful,&ers,&ered,&ering,&erings,&erly,&erness,&ernesses,&erments,&erless,&erful"),
         # (e.g., tokenize) // adds British variations
         (r"[%s].*[%s](izer)" % (vowels, cons), "izes,ize,izers,ized,izing,izings,ization,izations,ise,ises,iser,isers,ised,ising,isings,isation,isations"),
         # (e.g., tokenise) // British variant  // ~expertise
         (r"[%s].*[%s](iser)" % (vowels, cons), "ize,izes,izer,izers,ized,izing,izings,ization,izations,ises,ise,isers,ised,ising,isings,isation,isations"),
         #(e.g., actioner, atoner, icer, trader, accruer, churchgoer, prefer)
         (r"[%s].*(er)" % vowels, ",e,s,es,est,ed,ing,ings,ly,ely,ness,eness,nesses,enesses,ment,ments,less,ful,ement,ements,eless,eful,ers,ered,erred,ering,erring,erings,errings,erly,erness,ernesses,erment,erments,erless,erful,erer,erers,erest,errer,errers,errest"),
         
         # Words ending in -EST
         
         # (e.g., sliest, happiest, wittiest)
         (r"[%s](iest)" % cons, "y,ies,ier,iers,ied,ying,yings,ily,yly,iness,yness,inesses,ynesses,iment,iments,iless,iful"),
         # (e.g., fullest)
         (r"[%s].*l(lest)" % vowels, "&,&s,&er,&ers,&ed,&ing,&ings,ly,&ness,&nesses,&ment,&ments,&ful"),
         # (e.g.,  grossest)
         (r"[%s].*s(sest)" % vowels, "&,&es,&er,&ers,&ed,&ing,&ings,&ly,&ness,&nesses,&ment,&ments,&less,&ful"),
         # (e.g., biggest)
         (r"[%s][%s](?P<est1>[bdglmnprst])((?P=est1)est)" % (cons, vowels), ",s,&er,&ers,&ed,&ing,&ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., basest, archest, rashest)
         (r"[%s].*([cs]h|[jsxz])(est)" % vowels, "e,es,er,ers,ed,ing,ings,ly,ely,ness,eness,nesses,enesses,ment,ments,less,ful,ement,ements,eless,eful,ests,ester,esters,ested,esting,estings,estly,estness,estnesses,estment,estments,estless,estful"),
         # (e.g., severest, Xinterest, merest)
         (r"er(est)", "e,es,er,ers,ed,eing,eings,ely,eness,enesses,ement,ements,eless,eful,ests,ester,esters,ested,esting,estings,estly,estness,estnesses,estment,estments,estless,estful"),
         # (e.g., slickest, coolest, ablest, amplest, protest, quest)
         (r"[%s].*(est)" % vowels, ",e,s,es,er,ers,ed,ing,ings,ly,ely,ness,eness,nesses,enesses,ment,ments,less,ful,ement,ements,eless,eful,ests,ester,esters,ested,esting,estings,estly,estness,estnesses,estment,estments,estless,estful"),
         # (e.g., rest, test)
         (r"est", "s,er,ers,ed,ing,ings,ly,ness,nesses,ment,ments,less,ful"),
         
         # Words ending in -FUL
         
         # (e.g., beautiful, plentiful)
         (r"[%s].*[%s](iful)" % (vowels, cons), "ifully,ifulness,*y"),
         # (e.g., hopeful, sorrowful)
         (r"[%s].*(ful)" % vowels, "fully,fulness,,*"),
         
         # Words ending in -ICAL
         
         (r"[%s].*(ical)" % vowels, "ic,ics,ically"),
         
         # Words ending in -IC
         
         (r"[%s].*(ic)" % vowels, "ics,ical,ically"),
         
         # Words ending in -ING
         
         # (e.g., dying, crying, supplying)
         (r"[%s](ying)" % cons, "yings,ie,y,ies,ier,iers,iest,ied,iely,yly,ieness,yness,ienesses,ynesses,iment,iments,iless,iful"),
         # (e.g., pulling, filling, fulling)
         (r"[%s].*l(ling)" % vowels, ",*,&,&s,&er,&ers,&est,&ed,&ings,&ness,&nesses,&ment,&ments,&ful"),
         # (e.g., hissing, grossing, processing)
         (r"[%s].*s(sing)" % vowels, "&,&s,&er,&ers,&est,&ed,&ings,&ly,&ness,&nesses,&ment,&ments,&less,&ful"),
         # (e.g., hugging, trekking)
         (r"[%s][%s](?P<ing1>[bdgklmnprt])((?P=ing1)ing)" % (cons, vowels), ",s,&er,&ers,&est,&ed,&ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., freeing, agreeing)
         (r"eeing()", "ee,ees,eer,eers,eest,eed,eeings,eely,eeness,eenesses,eement,eements,eeless,eeful"),
         # (e.g., ageing, aweing)
         (r"[%s].*(eing)" % vowels, "e,es,er,ers,est,ed,eings,ely,eness,enesses,ement,ements,eless,eful"),
         # (e.g., toying, playing)
         (r"[%s].*y(ing)" % vowels, ",s,er,ers,est,ed,ings,ly,ingly,ness,nesses,ment,ments,less,ful"),
         # (e.g., editing, crediting, expediting, siting, exciting)
         (r"[%s].*[%s][eio]t(ing)" % (vowels, cons), ",*,*e,ings,inger,ingers,ingest,inged,inging,ingings,ingly,ingness,ingnesses,ingment,ingments,ingless,ingful"),
         # (e.g., robing, siding, doling, translating, flaking)
         (r"[%s][%s][bdgklmt](ing)" % (cons, vowels), "*e,ings,inger,ingers,ingest,inged,ingly,ingness,ingnesses,ingment,ingments,ingless,ingful"),
         # (e.g., tokenize) // adds British variations
         (r"[%s].*[%s](izing)" % (vowels, cons), "izes,izer,izers,ized,ize,izings,ization,izations,ise,ises,iser,isers,ised,ising,isings,isation,isations"),
         # (e.g., tokenise) // British variant  // ~expertise
         (r"[%s].*[%s](ising)" % (vowels, cons), "ize,izes,izer,izers,ized,izing,izings,ization,izations,ises,iser,isers,ised,ise,isings,isation,isations"),
         # (e.g., icing, aging, achieving, amazing, housing)
         (r"[%s][cgsvz](ing)" % vowels, "*e,ings,inger,ingers,ingest,inged,inging,ingings,ingly,ingness,ingnesses,ingment,ingments,ingless,ingful"),
         # (e.g., dancing, troubling, arguing, bluing, carving)
         (r"[%s][clsuv](ing)" % cons, "*e,ings,inger,ingers,ingest,inged,inging,ingings,ingly,ingness,ingnesses,ingment,ingments,ingless,ingful"),
         # (e.g., charging, bulging)
         (r"[%s].*[lr]g(ing)" % vowels, "*e,ings,inger,ingers,ingest,inged,inging,ingings,ingly,ingness,ingnesses,ingment,ingments,ingless,ingful"),
         # (e.g., farming, harping, interesting, bedspring, redwing)
         (r"[%s].*[%s][bdfjkmnpqrtwxz](ing)" % (vowels, cons), ",*,ings,inger,ingers,ingest,inged,inging,ingings,ingly,ingness,ingnesses,ingment,ingments,ingless,ingful"),
         # (e.g., spoiling, reviling, autoing, egging, hanging, hingeing)
         (r"[%s].*(ing)" % vowels, ",*,*e,ings,inger,ingers,ingest,inged,inging,ingings,ingly,ingness,ingnesses,ingment,ingments,ingless,ingful"),
         # (e.g., wing, thing) monosyllables
         (r"(ing)", "ings,inger,ingers,ingest,inged,inging,ingings,ingly,ingness,ingnesses,ingment,ingments,ingless,ingful"),
         
         # -LEAF rules omitted
         
         # Words ending in -MAN
         # (e.g., policewomen, hatchetmen, dolmen)
         (r"(man)", "man,mens,mener,meners,menest,mened,mening,menings,menly,menness,mennesses,menless,menful"),
         
         # Words ending in -MENT
         
         # (e.g., segment, bisegment, cosegment, pigment, depigment, repigment)
         (r"segment|pigment", "s,ed,ing,ings,er,ers,ly,ness,nesses,less,ful"),
         # (e.g., judgment, abridgment)
         (r"[%s].*dg(ment)" % vowels, "*e"),
         # (e.g., merriment, embodiment)
         (r"[%s].*[%s](iment)" % (vowels, cons), "*y"),
         # (e.g., atonement, entrapment)
         (r"[%s].*[%s](ment)" % (vowels, cons), ",*"),
         
         # Words ending in -O
         
         # (e.g., taboo, rodeo)
         (r"[%s]o()" % vowels, "s,er,ers,est,ed,ing,ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., tomato, bonito)
         (r"[%s].*o()" % vowels, "s,es,er,ers,est,ed,ing,ings,ly,ness,nesses,ment,ments,less,ful"),
         
         # Words ending in -UM
         
         # (e.g., datum, quantum, tedium, strum, [oil]drum, vacuum)
         (r"[%s].*(um)" % vowels, "a,ums,umer,ummer,umers,ummers,umed,ummed,uming,umming,umings,ummings,umness,umments,umless,umful"),
         
         # Words ending in -Y
         
         # (e.g., ably, horribly, wobbly)
         (r"[%s].*b(ly)" % vowels, "le,les,ler,lers,lest,led,ling,lings,leness,lenesses,lement,lements,leless,leful"),
         # (e.g., happily, dizzily)
         (r"[%s].*[%s](ily)" % (vowels, cons), "y,ies,ier,iers,iest,ied,ying,yings,yness,iness,ynesses,inesses,iment,iments,iless,iful"),
         # (e.g., peaceful+ly)
         (r"[%s].*ful(ly)" % vowels, ",*"),
         # (e.g., fully, folly, coolly, fatally, dally)
         (r"[%s].*l(ly)" % vowels, ",*,lies,lier,liers,liest,lied,lying,lyings,liness,linesses,liment,liments,liless,liful,*l"),
         # (e.g., monopoly, Xcephaly, holy)
         (r"[%s](ly)" % vowels, "lies,lier,liers,liest,lied,lying,lyings,liness,linesses,liment,liments,liless,liful"),
         # (e.g., frequently, comely, deeply, apply, badly)
         (r"[%s].*(ly)" % vowels, ",*,lies,lier,liers,liest,lied,lying,lyings,liness,linesses,lyless,lyful"),
         # (e.g., happy, ply, spy, cry)
         (r"[%s](y)" % cons, "ies,ier,iers,iest,ied,ying,yings,ily,yness,iness,ynesses,inesses,iment,iments,iless,iful,yment,yments,yless,yful"),
         # (e.g., betray, gay, stay)
         (r"[%s]y()" % vowels, "s,er,ers,est,ed,ing,ings,ly,ness,nesses,ment,ments,less,ful"),
         
         # Root rules
         
         # (e.g., fix, arch, rash)
         (r"[%s].*(ch|sh|[jxz])()" % vowels, "es,er,ers,est,ed,ing,ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., unflag, open, besot)
         (r"[%s].*[%s][%s][bdglmnprt]()" % (vowels, cons, vowels), "s,er,ers,est,ed,ing,ings,&er,&ers,&est,&ed,&ing,&ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., bed, cop)
         (r"[%s][%s][bdglmnprt]()" % (cons, vowels), "s,&er,&ers,&est,&ed,&ing,&ings,ly,ness,nesses,ment,ments,less,ful"),
         # (e.g., schemata, automata)
         (r"[%s].*[%s][%s]ma(ta)" % (vowels, cons, vowels), ",s,tas,tum,tums,ton,tons,tic,tical"),
         # (e.g., chordata, data, errata, sonata, toccata)
         (r"[%s].*t(a)" % vowels, "as,ae,um,ums,on,ons,ic,ical"),
         # (e.g., polka, spa, schema, ova, polyhedra)
         (r"[%s].*[%s](a)" % (vowels, cons), "as,aed,aing,ae,ata,um,ums,on,ons,al,atic,atical"),
         # (e.g., full)
         (r"[%s].*ll()" % vowels, "s,er,ers,est,ed,ing,ings,y,ness,nesses,ment,ments,-less,ful"),
         # (e.g., spoon, rhythm)
         (r"[%s].*()", "s,er,ers,est,ed,ing,ings,ly,ness,nesses,ment,ments,less,ful"),
         )

# There are a limited number of named groups available in a single
# regular expression, so we'll partition the list of rules into
# smaller chunks.

_partition_size = 20
_partitions = []
for p in xrange(0, len(rules) // _partition_size + 1):
    start = p * _partition_size
    end = (p+1) * _partition_size
    pattern = "|".join("(?P<_g%s>%s)$" % (i, r[0]) for i,r in enumerate(rules[start:end]))
    _partitions.append(re.compile(pattern))

#print "\n".join(p.pattern for p in _partitions)

def variations(word):
    if word in _exdict:
        return _exdict[word].split(" ")

    for i, p in enumerate(_partitions):
        match = p.search(word)
        if match:
            # Get the named group that matched
            num = int([k for k, v in match.groupdict().iteritems()
                       if v is not None and k.startswith("_g")][0][2:])
            # Get the positional groups for the matched group (all other
            # positional groups are None)
            groups = [g for g in match.groups() if g is not None]
            ending = groups[-1]
            root = word[:0-len(ending)] if ending else word 

            out = set((word, ))
            results = rules[i * _partition_size + num][1]
            for result in results.split(","):
                if result.startswith("&"):
                    out.add(root + root[-1] + result[1:])
                elif result.startswith("*"):
                    out.union(variations(root + result[1:]))
                else:
                    out.add(root + result)
            return set(out)

    return [word]


if __name__ == '__main__':
    import time
    t = time.clock()
    s = variations("rendering")
    print time.clock() - t
    print len(s)
    

########NEW FILE########
__FILENAME__ = porter
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
"""

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


class Singleton:
    """Quicky singleton class to provide a stem() function"""
    def __init__(self):
        self.p = PorterStemmer()
    def __call__(self, s):
        return self.p.stem(s, 0, len(s) - 1)
stem = Singleton()
    


########NEW FILE########
__FILENAME__ = passages
#===============================================================================
# Copyright 2008 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================


# Translated Minion passages functions
#
#def calculate_penalty(posns, missing_penalty = 10.0, gap_penalty = 0.1, ooo_penalty = 0.25):
#    penalty = 0.0
#    prev = -1
#    
#    dev = 0
#    count = sum(1 for p in posns if p >= 0)
#    avg = sum(p for p in posns if p >= 0) / count
#    for pos in posns:
#        if pos < 0:
#            penalty += missing_penalty
#            continue
#        
#        dev += abs(pos - avg)
#        if prev > 0:
#            diff = pos - prev
#            if diff < 0:
#                # Out of order penalty
#                penalty += (gap_penalty * -diff) + ooo_penalty
#            elif diff > 1:
#                penalty += gap_penalty * (diff - 1)
#        
#        prev = pos
#        
#    # Add mean deviation
#    penalty += (dev / count) * 0.1
#    
#    return penalty
#
#
#def find_passages(words, poslist, maxmissing = None, minwindow = 0, maxwindow = 350):
#    """Low-level passage scoring function. Yields a series of
#    (score, hit_positions) tuples, where hit_positions is a list of positions
#    at which search words are found in the passage.
#    
#    Translated into Python from the passages engine of the Minion search engine.
#    
#    :words: List of the search words.
#    :poslist: List of lists, where each sublist contains the positions
#        at which the corresponding search word (from the 'words' list) was found.
#    :maxmissing: The maximum number of missing words allowed. The default
#        is the number of words in 'words'. Set this to 0 to only find passages
#        containing all the search words.
#    :minwindow: The minimum size for passages (in words).
#    :maxwindow: The maximum size for passages (in words).
#    """
#    
#    if maxmissing is None:
#        maxmissing = len(words)
#    
#    mincol = -1
#    minpos = 0
#    maxpos = -9999
#    missing = 0
#    penalty = 0.0
#    current = [0] * len(words)
#    top = [-1] * len(words)
#    pens = [0.0] * len(words)
#    
#    for i in xrange(0, len(words)):
#        if poslist[i]:
#            firstpos = top[i] = poslist[i][0]
#            if firstpos > maxpos: maxpos = firstpos
#        
#    while True:
#        if mincol != -1:
#            # Replace the top element we removed the last time
#            pos = current[mincol]
#            if pos < len(poslist[mincol]):
#                newpos = poslist[mincol][pos]
#                top[mincol] = newpos
#                pens[mincol] = 0
#                
#                if newpos > maxpos:
#                    maxpos = newpos
#            else:
#                top[mincol] = -1
#                
#        missing = mincol = 0
#        penalty = 0.0
#        minpos = 9999999
#        
#        for i, currtop in enumerate(top):
#            if currtop >= 0:
#                if currtop < minpos:
#                    mincol = i
#                    minpos = currtop
#                    
#                penalty += 0
#            else:
#                missing += 1
#                # TODO: fix for term frequency
#                penalty += 10
#        
#        if missing > maxmissing or missing == len(words):
#            break
#        
#        cover = maxpos - minpos
#        if cover > maxwindow or cover < minwindow:
#            current[mincol] += 1
#            continue
#        
#        penalty += calculate_penalty(top)
#        
#        if penalty >= 100:
#            current[mincol] += 1
#            continue
#        
#        score = (100 - penalty) / 100
#        yield (score, tuple(top))
#        
#        current[mincol] += 1


if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = postpool

#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""Support functions and classes implementing the KinoSearch-like external sort
merging model. This module does not contain any user-level objects.
"""

import os, struct, tempfile
from marshal import dumps, loads
from heapq import heapify, heapreplace, heappop

from whoosh import structfile

_int_size = struct.calcsize("!i")

# Utility functions

def encode_posting(fieldNum, text, doc, data):
    """Encodes a posting as a string, for sorting."""
    
    return "".join([struct.pack("!i", fieldNum),
                    text.encode("utf8"),
                    chr(0),
                    struct.pack("!i", doc),
                    dumps(data)
                    ])

def decode_posting(posting):
    """Decodes an encoded posting string into a
    (field_number, text, document_number, data) tuple.
    """
    
    field_num = struct.unpack("!i", posting[:_int_size])[0]
    
    zero = posting.find(chr(0), _int_size)
    text = posting[_int_size:zero].decode("utf8")
    
    docstart = zero + 1
    docend = docstart + _int_size
    doc = struct.unpack("!i", posting[docstart:docend])[0]
    
    data = loads(posting[docend:])
    
    return field_num, text, doc, data

def merge(run_readers, max_chunk_size):
    # Initialize a list of terms we're "current"ly
    # looking at, by taking the first posting from
    # each buffer.
    #
    # The format of the list is
    # [("encoded_posting", reader_number), ...]
    #
    # The list is sorted, and the runs are already
    # sorted, so the first term in this list should
    # be the absolute "lowest" term.
    
    current = [(r.next(), i) for i, r
               in enumerate(run_readers)]
    heapify(current)
    
    # The number of active readers (readers with more
    # postings to available), initially equal
    # to the total number of readers/buffers.
    
    active = len(run_readers)
    
    # Initialize the output buffer, and a variable to
    # keep track of the output buffer size. This buffer
    # accumulates postings from the various buffers in
    # proper sorted order.
    
    output = []
    outputBufferSize = 0
    
    while active > 0:
        # Get the first ("encoded_posting", reader_number)
        # pair and add it to the output buffer.
        
        p, i = current[0]
        output.append(p)
        outputBufferSize += len(p)
        
        # If the output buffer is full, "flush" it by yielding
        # the accumulated postings back to the parent writer
        # and clearing the output buffer.
        
        if outputBufferSize > max_chunk_size:
            for p in output:
                yield decode_posting(p)
            output = []
            outputBufferSize = 0
        
        # We need to replace the posting we just added to the output
        # by getting the next posting from the same buffer.
        
        if run_readers[i] is not None:
            # Take the first posting from buffer i and insert it into the
            # "current" list in sorted order.
            # The current list must always stay sorted, so the first item
            # is always the lowest.
            
            p = run_readers[i].next()
            if p:
                heapreplace(current, (p, i))
            else:
                heappop(current)
                active -= 1
    
    # If there are still terms in the "current" list after all the
    # readers are empty, dump them into the output buffer.
    
    if len(current) > 0:
        output.extend([p for p, i in current])
    
    # If there's still postings in the output buffer, yield
    # them all to the parent writer.
    
    if len(output) > 0:
        for p in output:
            yield decode_posting(p)


# Classes

class RunReader(object):
    """An iterator that yields posting strings from a "run" on disk.
    This class buffers the reads to improve efficiency.
    """
    
    def __init__(self, stream, count, buffer_size):
        """
        :stream: the file from which to read.
        :count: the number of postings in the stream.
        :buffer_size: the size (in bytes) of the read buffer to use.
        """
        
        self.stream = stream
        self.count = count
        self.buffer_size = buffer_size
        
        self.buffer = []
        self.pointer = 0
        self.finished = False
    
    def close(self):
        self.stream.close()
    
    def _fill(self):
        # Clears and refills the buffer.
        
        # If this reader is exhausted, do nothing.
        if self.finished:
            return
        
        # Clear the buffer.
        buffer = self.buffer = []
        
        # Reset the index at which the next() method
        # reads from the buffer.
        self.pointer = 0
        
        # How much we've read so far.
        so_far = 0
        count = self.count
        
        while so_far < self.buffer_size:
            if count <= 0:
                break
            p = self.stream.read_string()
            buffer.append(p)
            so_far += len(p)
            count -= 1
        
        self.count = count
    
    def __iter__(self):
        return self
    
    def next(self):
        assert self.pointer <= len(self.buffer)
        
        if self.pointer == len(self.buffer):
            self._fill()
        
        # If after refilling the buffer is still empty, we're
        # at the end of the file and should stop. Probably this
        # should raise StopIteration instead of returning None.
        if len(self.buffer) == 0:
            self.finished = True
            return None
        
        r = self.buffer[self.pointer]
        self.pointer += 1
        return r


class PostingPool(object):
    """Represents the "pool" of all postings to be sorted. As documents are added,
    this object writes out "runs" of sorted encoded postings. When all documents
    have been added, this object merge sorts the runs from disk, yielding decoded
    postings to the SegmentWriter.
    """
    
    def __init__(self, limit):
        """
        :limit: the maximum amount of memory to use at once
            for adding postings and the merge sort.
        """
        
        self.limit = limit
        self.size = 0
        self.postings = []
        self.finished = False
        
        self.runs = []
        self.count = 0
    
    def add_posting(self, field_num, text, doc, data):
        """Adds a posting to the pool."""
        
        if self.finished:
            raise Exception("Can't add postings after you iterate over the pool")
        
        if self.size >= self.limit:
            print "Flushing..."
            self._flush_run()
        
        posting = encode_posting(field_num, text, doc, data)
        self.size += len(posting)
        self.postings.append(posting)
        self.count += 1
    
    def _flush_run(self):
        # Called when the memory buffer (of size self.limit) fills up.
        # Sorts the buffer and writes the current buffer to a "run" on disk.
        
        if self.size > 0:
            tempfd, tempname = tempfile.mkstemp(".run")
            runfile = structfile.StructFile(os.fdopen(tempfd, "w+b"))
            
            self.postings.sort()
            for p in self.postings:
                runfile.write_string(p)
            runfile.flush()
            runfile.seek(0)
            
            self.runs.append((runfile, self.count))
            print "Flushed run:", self.runs
            
            self.postings = []
            self.size = 0
            self.count = 0
    
    def __iter__(self):
        # Iterating the PostingPool object performs a merge sort of
        # the runs that have been written to disk and yields the
        # sorted, decoded postings.
        
        if self.finished:
            raise Exception("Tried to iterate on PostingPool twice")
        
        run_count = len(self.runs)
        if self.postings and run_count == 0:
            # Special case: we never accumulated enough postings to flush
            # to disk, so the postings are still in memory: just yield
            # them from there.
            
            self.postings.sort()
            for p in self.postings:
                yield decode_posting(p)
            return
        
        if not self.postings and run_count == 0:
            # No postings at all
            return
        
        if self.postings:
            self._flush_run()
            run_count = len(self.runs)
        
        #This method does an external merge to yield postings
        #from the (n > 1) runs built up during indexing and
        #merging.
        
        # Divide up the posting pool's memory limit between the
        # number of runs plus an output buffer.
        max_chunk_size = int(self.limit / (run_count + 1))
        
        run_readers = [RunReader(run_file, count, max_chunk_size)
                       for run_file, count in self.runs]
        
        for decoded_posting in merge(run_readers, max_chunk_size):
            yield decoded_posting
        
        for rr in run_readers:
            assert rr.count == 0
            rr.close()
        
        # And we're done.
        self.finished = True

#class RamPostingPool(object):
#    """
#    An experimental alternate implementation of PostingPool that
#    just keeps everything in memory instead of doing an external
#    sort on disk. This is very memory inefficient and, as it turns
#    out, not much faster.
#    """
#
#    def __init__(self):
#        self.postings = []
#
#    def add_posting(self, field_num, text, doc, data):
#        self.postings.append((field_num, text, doc, data))
#
#    def __iter__(self):
#        return iter(sorted(self.postings))

########NEW FILE########
__FILENAME__ = qparser
import re

from whoosh.support.pyparsing import alphanums, printables, \
CharsNotIn, Literal, Group, Combine, Suppress, Regex, OneOrMore, Forward, Word, Keyword, \
Empty, StringEnd, ParserElement
from whoosh import analysis, query

"""
This module contains the default search query parser.

This uses the excellent Pyparsing module 
(http://pyparsing.sourceforge.net/) to parse search query strings
into nodes from the query module.

This parser handles:

    - 'and', 'or', 'not'
    - grouping with parentheses
    - quoted phrase searching
    - wildcards at the end of a search prefix, e.g. help*
    - ranges, e.g. a..b

This parser is based on the searchparser example code available at:

http://pyparsing.wikispaces.com/space/showimage/searchparser.py

The code upon which this parser is based was made available by the authors under
the following copyright and conditions:

# Copyright (c) 2006, Estrate, the Netherlands
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation 
#   and/or other materials provided with the distribution.
# * Neither the name of Estrate nor the names of its contributors may be used
#   to endorse or promote products derived from this software without specific
#   prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; 
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON 
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT 
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS 
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# CONTRIBUTORS:
# - Steven Mooij
# - Rudolph Froger
# - Paul McGuire
"""

def _make_default_parser():
    ParserElement.setDefaultWhitespaceChars(" \n\t\r'")
    
    escapechar = "\\"
    wordtext = Regex(r"(\w|/)+(\.?(\w|\-|/)+)*", re.UNICODE)
    #escape = Suppress(escapechar) + Word(printables, exact=1)
    #wordToken = OneOrMore(escape | wordtext)
    #wordToken.setParseAction(lambda tokens: ''.join(tokens))
    wordToken = wordtext
    
    # A plain old word.
    plainWord = Group(wordToken).setResultsName("Word")
    
    # A word ending in a star (e.g. 'render*'), indicating that
    # the search should do prefix expansion.
    prefixWord = Group(Combine(wordToken + Suppress('*'))).setResultsName("Prefix")
    
    # A wildcard word containing * or ?.
    wildcard = Group(Regex(r"\w*(?:[\?\*]\w*)+")).setResultsName("Wildcard")
    
    # A range of terms
    range = Group(plainWord + Suppress("..") + plainWord).setResultsName("Range")
    
    # A word-like thing
    generalWord = range | prefixWord | wildcard | plainWord
    
    # A quoted phrase
    quotedPhrase = Group(Suppress('"') + CharsNotIn('"') + Suppress('"')).setResultsName("Quotes")
    
    expression = Forward()
    
    # Parentheses can enclose (group) any expression
    parenthetical = Group((Suppress("(") + expression + Suppress(")"))).setResultsName("Group")

    boostableUnit = quotedPhrase | generalWord
    boostedUnit = Group(boostableUnit + Suppress("^") + Word("0123456789", ".0123456789")).setResultsName("Boost")

    # The user can flag that a parenthetical group, quoted phrase, or word
    # should be searched in a particular field by prepending 'fn:', where fn is
    # the name of the field.
    fieldableUnit = parenthetical | boostedUnit | boostableUnit
    fieldedUnit = Group(Word(alphanums + "_") + Suppress(':') + fieldableUnit).setResultsName("Field")
    
    # Units of content
    unit = fieldedUnit | fieldableUnit

    # A unit may be "not"-ed.
    operatorNot = Group(Suppress(Keyword("not", caseless=True)) + unit).setResultsName("Not")
    generalUnit = operatorNot | unit

    andToken = Keyword("and", caseless=True)
    orToken = Keyword("or", caseless=True)
    
    operatorAnd = Group(generalUnit + Suppress(andToken) + expression).setResultsName("And")
    operatorOr = Group(generalUnit + Suppress(orToken) + expression).setResultsName("Or")

    expression << (OneOrMore(operatorAnd | operatorOr | generalUnit) | Empty())
    
    toplevel = Group(expression).setResultsName("Toplevel") + StringEnd()
    
    return toplevel.parseString


def _make_simple_parser():
    ParserElement.setDefaultWhitespaceChars(" \n\t\r'")
    
    wordToken = Regex(r"(\w|/)+(\.?(\w|\-|/)+)*", re.UNICODE)
    
    # A word-like thing
    generalWord = Group(wordToken).setResultsName("Word")
    
    # A quoted phrase
    quotedPhrase = Group(Suppress('"') + CharsNotIn('"') + Suppress('"')).setResultsName("Quotes")
    
    # Units of content
    fieldableUnit = quotedPhrase | generalWord
    fieldedUnit = Group(Word(alphanums) + Suppress(':') + fieldableUnit).setResultsName("Field")
    unit = fieldedUnit | fieldableUnit

    # A unit may be "not"-ed.
    operatorNot = Group(Suppress(Literal("-")) + unit).setResultsName("Not")
    
    # A unit may be required
    operatorReqd = Group(Suppress(Literal("+")) + unit).setResultsName("Required")
    
    generalUnit = operatorNot | operatorReqd | unit

    expression = (OneOrMore(generalUnit) | Empty())
    toplevel = Group(expression).setResultsName("Toplevel") + StringEnd()
    
    return toplevel.parseString


DEFAULT_PARSER_FN = _make_default_parser()
SIMPLE_PARSER_FN = _make_simple_parser()

# Query parser objects

class PyparsingBasedParser(object):
    def _analyzer(self, fieldname):
        if self.schema and fieldname in self.schema:
            return self.schema.analyzer(fieldname)
    
    def _analyze(self, fieldname, text):
        analyzer = self._analyzer(fieldname)
        if analyzer:
            texts = [t.text for t in analyzer(text)]
            return texts[0]
        else:
            return text
    
    def parse(self, input, normalize = True):
        """Parses the input string and returns a Query object/tree.
        
        This method may return None if the input string does not result in any
        valid queries. It may also raise a variety of exceptions if the input
        string is malformed.
        
        :input: the unicode string to parse.
        :normalize: whether to call normalize() on the query object/tree
            before returning it. This should be left on unless you're trying to
            debug the parser output.
        """
        
        self.stopped_words = set()
        
        ast = self.parser(input)[0]
        q = self._eval(ast, None)
        if q and normalize:
            q = q.normalize()
        return q
    
    # These methods are called by the parsing code to generate query
    # objects. They are useful for subclassing.

    def make_term(self, fieldname, text):
        fieldname = fieldname or self.default_field
        analyzer = self._analyzer(fieldname)
        if analyzer:
            tokens = [t.copy() for t in analyzer(text, removestops = False)]
            self.stopped_words.update((t.text for t in tokens if t.stopped))
            texts = [t.text for t in tokens if not t.stopped]
            if len(texts) < 1:
                return None
            elif len(texts) == 1:
                return self.termclass(fieldname, texts[0])
            else:
                return self.make_multiterm(fieldname, texts)
        else:
            return self.termclass(fieldname, text)
    
    def make_multiterm(self, fieldname, texts):
        return query.Or([self.termclass(fieldname, text)
                         for text in texts])
    
    def make_phrase(self, fieldname, text):
        fieldname = fieldname or self.default_field
        analyzer = self._analyzer(fieldname)
        if analyzer:
            tokens = [t.copy() for t in analyzer(text, removestops = False)]
            self.stopped_words.update((t.text for t in tokens if t.stopped))
            texts = [t.text for t in tokens if not t.stopped]
        else:
            texts = text.split(" ")
        
        return query.Phrase(fieldname, texts)
    
    def _eval(self, node, fieldname):
        # Get the name of the AST node and call the corresponding
        # method to get a query object
        name = node.getName()
        return getattr(self, "_" + name)(node, fieldname)


class QueryParser(PyparsingBasedParser):
    """The default parser for Whoosh, implementing a powerful fielded
    query language similar to Lucene's.
    """
    
    def __init__(self, default_field,
                 conjunction = query.And,
                 termclass = query.Term,
                 schema = None):
        """
        :default_field: Use this as the field for any terms without
            an explicit field. For example, if the query string is
            "hello f1:there" and the default field is "f2", the parsed
            query will be as if the user had entered "f2:hello f1:there".
            This argument is required.
        :conjuction: Use this query.Query class to join together clauses
            where the user has not explictly specified a join. For example,
            if this is query.And, the query string "a b c" will be parsed as
            "a AND b AND c". If this is query.Or, the string will be parsed as
            "a OR b OR c".
        :termclass: Use this query.Query class for bare terms. For example,
            query.Term or query.Variations.
        :schema: An optional fields.Schema object. If this argument is present,
            the analyzer for the appropriate field will be run on terms/phrases
            before they are turned into query objects.
        """

        self.default_field = default_field
        self.conjunction = conjunction
        self.termclass = termclass
        self.schema = schema
        self.stopped_words = None
        self.parser = DEFAULT_PARSER_FN
    
    def make_prefix(self, fieldname, text):
        fieldname = fieldname or self.default_field
        text = self._analyze(fieldname, text)
        return query.Prefix(fieldname, text)
    
    def make_wildcard(self, fieldname, text):
        fieldname = fieldname or self.default_field
        return query.Wildcard(fieldname or self.default_field, text)
    
    def make_range(self, fieldname, range):
        start, end = range
        fieldname = fieldname or self.default_field
        start = self._analyze(fieldname, start)
        end = self._analyze(fieldname, end)
        return query.TermRange(fieldname or self.default_field, (start, end))
    
    def make_and(self, qs):
        return query.And(qs)
    
    def make_or(self, qs):
        return query.Or(qs)
    
    def make_not(self, q):
        return query.Not(q)
    
    # These methods take the AST from pyparsing, extract the
    # relevant data, and call the appropriate make_* methods to
    # create query objects.

    def _Toplevel(self, node, fieldname):
        return self.conjunction([self._eval(s, fieldname) for s in node])

    def _Word(self, node, fieldname):
        return self.make_term(fieldname, node[0])
    
    def _Quotes(self, node, fieldname):
        return self.make_phrase(fieldname, node[0])

    def _Prefix(self, node, fieldname):
        return self.make_prefix(fieldname, node[0])
    
    def _Range(self, node, fieldname):
        return self.make_range(fieldname, (node[0][0], node[1][0]))
    
    def _Wildcard(self, node, fieldname):
        return self.make_wildcard(fieldname, node[0])
    
    def _And(self, node, fieldname):
        return self.make_and([self._eval(s, fieldname) for s in node])
    
    def _Or(self, node, fieldname):
        return self.make_or([self._eval(s, fieldname) for s in node])
    
    def _Not(self, node, fieldname):
        return self.make_not(self._eval(node[0], fieldname))
    
    def _Group(self, node, fieldname):
        return self.conjunction([self._eval(s, fieldname) for s in node])
    
    def _Field(self, node, fieldname):
        return self._eval(node[1], node[0])
    
    def _Boost(self, node, fieldname):
        obj = self._eval(node[0], fieldname)
        obj.boost = float(node[1])
        return obj


class MultifieldParser(QueryParser):
    """A subclass of QueryParser. Instead of assigning unfielded clauses
    to a default field, this class transforms them into an OR clause that
    searches a list of fields. For example, if the list of multi-fields
    is "f1", "f2" and the query string is "hello there", the class will
    parse "(f1:hello OR f2:hello) (f1:there OR f2:there)". This is very
    useful when you have two textual fields (e.g. "title" and "content")
    you want to search by default.
    """

    def __init__(self, fieldnames, **kwargs):
        super(MultifieldParser, self).__init__(fieldnames[0],
                                               **kwargs)
        self.fieldnames = fieldnames
    
    # Override the superclass's make_* methods with versions that convert
    # the clauses to multifield ORs.

    def _make(self, method, fieldname, data):
        if fieldname is not None:
            return method(fieldname, data)
        
        return query.Or([method(fn, data)
                         for fn in self.fieldnames])
    
    def make_term(self, fieldname, text):
        return self._make(super(self.__class__, self).make_term, fieldname, text)
    
    def make_prefix(self, fieldname, text):
        return self._make(super(self.__class__, self).make_prefix, fieldname, text)
    
    def make_range(self, fieldname, range):
        return self._make(super(self.__class__, self).make_range, fieldname, range)
    
    def make_wildcard(self, fieldname, text):
        return self._make(super(self.__class__, self).make_wildcard, fieldname, text)
    
    def make_phrase(self, fieldname, text):
        return self._make(super(self.__class__, self).make_phrase, fieldname, text)
        

class SimpleParser(PyparsingBasedParser):
    """A simple, AltaVista-like parser. Does not support nested groups, operators,
    prefixes, ranges, etc. Only supports bare words and quoted phrases. By default
    always ORs terms/phrases together. Put a plus sign (+) in front of a term/phrase
    to require it. Put a minus sign (-) in front of a term/phrase to forbid it.
    """
    
    def __init__(self, default_field, termclass = query.Term, schema = None):
        """
        :default_field: Use this as the field for any terms without
            an explicit field. For example, if the query string is
            "hello f1:there" and the default field is "f2", the parsed
            query will be as if the user had entered "f2:hello f1:there".
            This argument is required.
        :termclass: Use this query class for bare terms. For example,
            query.Term or query.Variations.
        :schema: An optional fields.Schema object. If this argument is present,
            the analyzer for the appropriate field will be run on terms/phrases
            before they are turned into query objects.
        """

        self.default_field = default_field
        self.termclass = termclass
        self.schema = schema
        self.stopped_words = None
        self.parser = SIMPLE_PARSER_FN
    
    # These methods take the AST from pyparsing, extract the
    # relevant data, and call the appropriate make_* methods to
    # create query objects.

    def make_not(self, q):
        return query.Not(q)

    def _Toplevel(self, node, fieldname):
        queries = [self._eval(s, fieldname) for s in node]
        reqds = [q[0] for q in queries if isinstance(q, tuple)]
        if reqds:
            nots = [q for q in queries if isinstance(q, query.Not)]
            opts = [q for q in queries
                    if not isinstance(q, query.Not) and not isinstance(q, tuple)]
            return query.AndMaybe([query.And(reqds + nots), query.Or(opts)])
        else:
            return query.Or(queries)

    def _Word(self, node, fieldname):
        return self.make_term(fieldname, node[0])
    
    def _Quotes(self, node, fieldname):
        return self.make_phrase(fieldname, node[0])

    def _Required(self, node, fieldname):
        return (self._eval(node[0], fieldname), )

    def _Not(self, node, fieldname):
        return self.make_not(self._eval(node[0], fieldname))
    
    def _Field(self, node, fieldname):
        return self._eval(node[1], node[0])


class SimpleNgramParser(object):
    """A simple parser that only allows searching a single Ngram field. Breaks the input
    text into grams. It can either discard grams containing spaces, or compose them as
    optional clauses to the query.
    """
    
    def __init__(self, fieldname, minchars, maxchars, discardspaces = False,
                 analyzerclass = analysis.NgramAnalyzer):
        """
        :fieldname: The field to search.
        :minchars: The minimum gram size the text was indexed with.
        :maxchars: The maximum gram size the text was indexed with.
        :discardspaces: If False, grams containing spaces are made into optional
            clauses of the query. If True, grams containing spaces are ignored.
        :analyzerclass: An analyzer class. The default is the standard NgramAnalyzer.
            The parser will instantiate this analyzer with the gram size set to the maximum
            usable size based on the input string.
        """
        
        self.fieldname = fieldname
        self.minchars = minchars
        self.maxchars = maxchars
        self.discardspaces = discardspaces
        self.analyzerclass = analyzerclass
    
    def parse(self, input):
        """Parses the input string and returns a Query object/tree.
        
        This method may return None if the input string does not result in any
        valid queries. It may also raise a variety of exceptions if the input
        string is malformed.
        
        :input: the unicode string to parse.
        """
        
        required = []
        optional = []
        gramsize = max(self.minchars, min(self.maxchars, len(input)))
        if gramsize > len(input):
            return None
        
        discardspaces = self.discardspaces
        for t in self.analyzerclass(gramsize)(input):
            gram = t.text
            if " " in gram:
                if not discardspaces:
                    optional.append(gram)
            else:
                required.append(gram)
        
        if required:
            fieldname = self.fieldname
            andquery = query.And([query.Term(fieldname, g) for g in required])
            if optional:
                orquery = query.Or([query.Term(fieldname, g) for g in optional])
                return query.AndMaybe([andquery, orquery])
            else:
                return andquery
        else:
            return None



if __name__=='__main__':
    from whoosh.fields import Schema, TEXT, NGRAM, ID
    s = Schema(content = TEXT, path=ID)
    
    qp = QueryParser("content", schema = s)
    pn = qp.parse(u'hello there', normalize = False)
    print "pn=", pn
    if pn:
        nn = pn.normalize()
        print "nn=", nn

########NEW FILE########
__FILENAME__ = query
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""
This module contains objects that query the search index. These query
objects are composable to form complex query trees. The query parser
in the qparser module generates trees of these objects from user query
strings.
"""

from __future__ import division
from array import array
from bisect import bisect_left, bisect_right
from collections import defaultdict
import fnmatch, re

from whoosh.support.bitvector import BitVector
from whoosh.lang.morph_en import variations

# Utility functions

def _not_vector(notqueries, searcher, sourcevector):
    # Returns a BitVector where the positions are docnums
    # and True means the docnum is banned from the results.
    # 'sourcevector' is the incoming exclude_docs. This
    # function makes a copy of it and adds the documents
    # from notqueries
    
    if sourcevector is None:
        nvector = BitVector(searcher.doc_count_all())
    else:
        nvector = sourcevector.copy()
    
    for nquery in notqueries:
        for docnum in nquery.docs(searcher):
            nvector.set(docnum)
            
    return nvector

# 

class QueryError(Exception):
    """
    Error encountered while running a query.
    """
    pass


class Query(object):
    """
    Abstract base class for all queries.
    """
    
    def __or__(self, query):
        return Or([self, query]).normalize()
    
    def __and__(self, query):
        return And([self, query]).normalize()
    
    def __sub__(self, query):
        q = And([self, Not(query)])
        return q.normalize()
    
    def all_terms(self, termset):
        """
        Adds the term(s) in this query (and its subqueries, where
        applicable) to termset. Note that unlike existing_terms(),
        this method will not add terms from queries that require
        a TermReader to calculate their terms, such as Prefix and
        Wildcard.
        """
        pass
    
    def existing_terms(self, searcher, termset, reverse = False):
        """
        Adds the term(s) in the query (and its subqueries, where
        applicable) IF AND AS EXIST IN THE INDEX to termset.
        If reverse is True, this method returns MISSING terms rather
        than existing terms.
        """
        raise NotImplementedError
    
    def estimate_size(self, searcher):
        """
        Returns an estimate of how many documents this query could potentially
        match (for example, the estimated size of a simple term query is the
        document frequency of the term). It is permissible to overestimate, but
        not to underestimate.
        """
        raise NotImplementedError
    
    def docs(self, searcher, exclude_docs = None):
        """
        Runs this query on the index represented by 'searcher'.
        Yields a sequence of docnums. The base method simply forwards to
        doc_scores() and throws away the scores, but if possible specific
        implementations should use a more efficient method to avoid scoring
        the hits.
        
        exclude_docs is a BitVector of documents to exclude from the results.
        """
        
        return (docnum for docnum, _ in self.doc_scores(searcher,
                                                        exclude_docs = exclude_docs))
    
    def doc_scores(self, searcher, weighting = None, exclude_docs = None):
        """
        Runs this query on the index represented by 'searcher'.
        Yields a sequence of (docnum, score) pairs.
        
        exclude_docs is a BitVector of documents to exclude from the results.
        """
        raise NotImplementedError
    
    def normalize(self):
        """
        Returns a recursively "normalized" form of this query. The normalized
        form removes redundancy and empty queries. For example,
        AND(AND(a, b), c, Or()) -> AND(a, b, c).
        """
        return self
    
    def replace(self, oldtext, newtext):
        """
        Returns a copy of this query with oldtext replaced by newtext
        (if oldtext was in this query).
        """
        return self
    

class MultifieldTerm(Query):
    def __init__(self, fieldnames, text, boost = 1.0):
        self.fieldnames = fieldnames
        self.text = text
        self.boost = boost
            
    def __repr__(self):
        return "%s(%r, %r, boost = %s)" % (self.fieldnames, self.text, self.boost)

    def __unicode__(self):
        return u"(%s):%s" % (u"|".join(self.fieldnames), self.text)
    
    def all_terms(self, termset):
        for fn in self.fieldnames:
            termset.add((fn, self.text))
    
    def existing_terms(self, searcher, termset, reverse = False):
        for fn in self.fieldnames:
            t = (fn, self.text)
            contains = t in searcher
            if reverse: contains = not contains
            if contains:
                termset.add(t)
    
    def estimate_size(self, searcher):
        max_df = 0
        text = self.text
        
        for fieldname in self.fieldnames:
            fieldnum = searcher.fieldname_to_num(fieldname)
            df = searcher.doc_frequency(fieldnum, text)
            if df > max_df:
                max_df = df
                
        return max_df
    
    def docs(self, searcher, exclude_docs = None):
        vector = BitVector(searcher.doc_count_all())
        text = self.text
        
        for fieldname in self.fieldnames:
            fieldnum = searcher.fieldname_to_num(fieldname)
            
            if (fieldnum, text) in searcher:
                for docnum, _ in searcher.postings(fieldnum, self.text,
                                                      exclude_docs = exclude_docs):
                    vector.set(docnum)
                
        return iter(vector)
    
    def doc_scores(self, searcher, weighting = None, exclude_docs = None):
        text = self.text
        weighting = weighting or searcher.weighting
        
        accumulators = defaultdict(float)
        for fieldname in self.fieldnames:
            fieldnum = searcher.fieldname_to_num(fieldname)
            if (fieldnum, text) in searcher:
                for docnum, weight in searcher.weights(fieldnum, text,
                                                       exclude_docs = exclude_docs,
                                                       boost = self.boost):
                    accumulators[docnum] += weighting.score(searcher, fieldnum, text, docnum, weight)
        
        return accumulators.iteritems()
    

class SimpleQuery(Query):
    """
    Abstract base class for simple (single term) queries.
    """
    
    def __init__(self, fieldname, text, boost = 1.0):
        """
        fieldname is the name of the field to search. text is the text
        of the term to search for. boost is a boost factor to apply to
        the raw scores of any documents matched by this query.
        """
        
        self.fieldname = fieldname
        self.text = text
        self.boost = boost
    
    def __repr__(self):
        return "%s(%r, %r, boost=%r)" % (self.__class__.__name__,
                                         self.fieldname, self.text, self.boost)

    def __unicode__(self):
        t = u"%s:%s" % (self.fieldname, self.text)
        if self.boost != 1:
            t += u"^" + unicode(self.boost)
        return t
    
    def all_terms(self, termset):
        termset.add((self.fieldname, self.text))
    
    def existing_terms(self, searcher, termset, reverse = False):
        fieldname, text = self.fieldname, self.text
        fieldnum = searcher.fieldname_to_num(fieldname)
        contains = (fieldnum, text) in searcher
        if reverse: contains = not contains
        if contains:
            termset.add((fieldname, text))


class Term(SimpleQuery):
    """
    Matches documents containing the given term (fieldname+text pair).
    """
    
    def replace(self, oldtext, newtext):
        if self.text == oldtext:
            return Term(self.fieldname, newtext, boost = self.boost)
        else:
            return self
    
    def estimate_size(self, searcher):
        fieldnum = searcher.fieldname_to_num(self.fieldname)
        return searcher.doc_frequency(fieldnum, self.text)
    
    def docs(self, searcher, exclude_docs = None):
        fieldnum = searcher.fieldname_to_num(self.fieldname)
        text = self.text
        
        if (fieldnum, text) in searcher:
            for docnum, _ in searcher.postings(fieldnum, text, exclude_docs = exclude_docs):
                yield docnum
    
    def doc_scores(self, searcher, weighting = None, exclude_docs = None):
        fieldnum = searcher.fieldname_to_num(self.fieldname)
        text = self.text
        boost = self.boost
        if (fieldnum, text) in searcher:
            weighting = weighting or searcher.weighting
            for docnum, weight in searcher.weights(fieldnum, self.text,
                                                   exclude_docs = exclude_docs):
                yield docnum, weighting.score(searcher, fieldnum, text, docnum,
                                              weight * boost)


class CompoundQuery(Query):
    """
    Abstract base class for queries that combine or manipulate the results of
    multiple sub-queries .
    """
    
    def __init__(self, subqueries, boost = 1.0):
        """
        subqueries is a list of queries to combine.
        boost is a boost factor that should be applied to the raw score of
        results matched by this query.
        """
        
        self.subqueries = subqueries
        self._notqueries = None
        self.boost = boost
    
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.subqueries)

    def __unicode__(self):
        r = u"("
        r += (self.JOINT).join([unicode(s) for s in self.subqueries])
        r += u")"
        return r

    def _split_queries(self):
        if self._notqueries is None:
            self._subqueries = [q for q in self.subqueries if not isinstance(q, Not)]
            self._notqueries = [q for q in self.subqueries if isinstance(q, Not)]

    def replace(self, oldtext, newtext):
        return self.__class__([q.replace(oldtext, newtext) for q in self.subqueries],
                              boost = self.boost)

    def all_terms(self, termset):
        for q in self.subqueries:
            q.all_terms(termset)

    def existing_terms(self, searcher, termset, reverse = False):
        for q in self.subqueries:
            q.existing_terms(searcher, termset, reverse = reverse)

    def normalize(self):
        # Do an initial check for Nones.
        subqueries = [q for q in self.subqueries if q is not None]
        
        if not subqueries:
            return None
        
        if len(subqueries) == 1:
            return subqueries[0].normalize()
        
        # Normalize the subqueries and eliminate duplicate terms.
        subqs = []
        seenterms = set()
        for s in subqueries:
            s = s.normalize()
            if s is None:
                continue
            
            if isinstance(s, Term):
                term = (s.fieldname, s.text)
                if term in seenterms:
                    continue
                seenterms.add(term)
                
            if isinstance(s, self.__class__):
                subqs += s.subqueries
            else:
                subqs.append(s)
        
        return self.__class__(subqs)
    

class Require(CompoundQuery):
    """Binary query returns results from the first query that also appear in the
    second query, but only uses the scores from the first query. This lets you
    filter results without affecting scores.
    """
    
    JOINT = " REQUIRE "
    
    def __init__(self, subqueries, boost = 1.0):
        assert len(subqueries) == 2
        self.subqueries = subqueries
        self.boost = boost
        
    def docs(self, searcher, exclude_docs = None):
        return And(self.subqueries).docs(searcher, exclude_docs = exclude_docs)
    
    def doc_scores(self, searcher, weighting = None, exclude_docs = None):
        query, filterquery = self.subqueries
        
        filter = BitVector(searcher.doc_count_all())
        for docnum in filterquery.docs(searcher, exclude_docs = exclude_docs):
            filter.set(docnum)
            
        for docnum, score in query.doc_scores(searcher, weighting = weighting):
            if docnum not in filter: continue
            yield docnum, score


class AndMaybe(CompoundQuery):
    """Binary query requires results from the first query. If and only if the
    same document also appears in the results from the second query, the score
    from the second query will be added to the score from the first query.
    """
    
    JOINT = " ANDMAYBE "
    
    def __init__(self, subqueries, boost = 1.0):
        assert len(subqueries) == 2
        self.subqueries = subqueries
        self.boost = boost
    
    def docs(self, searcher, exclude_docs = None):
        return self.subqueries[0].docs(searcher, exclude_docs = exclude_docs)
    
    def doc_scores(self, searcher, weighting = None, exclude_docs = None):
        query, maybequery = self.subqueries
        
        maybescores = dict(maybequery.doc_scores(searcher, weighting = weighting,
                                                 exclude_docs = exclude_docs))
        
        for docnum, score in query.doc_scores(searcher, weighting = weighting,
                                              exclude_docs = exclude_docs):
            if docnum in maybescores:
                score += maybescores[docnum]
            yield (docnum, score)


class And(CompoundQuery):
    """
    Matches documents that match ALL of the subqueries.
    """
    
    # This is used by the superclass's __unicode__ method.
    JOINT = " AND "
    
    def estimate_size(self, searcher):
        return min(q.estimate_size(searcher) for q in self.subqueries)
    
    def docs(self, searcher, exclude_docs = None):
        if not self.subqueries:
            return []
        
        self._split_queries()
        if self._notqueries:
            exclude_docs = _not_vector(self._notqueries, searcher, exclude_docs)
        
        target = len(self.subqueries)
        
        # Create an array representing the number of subqueries that hit each
        # document.
        if target <= 255:
            type = "B"
        else:
            type = "i"
        counters = array(type, (0 for _ in xrange(0, searcher.doc_count_all())))
        for q in self._subqueries:
            for docnum in q.docs(searcher, exclude_docs = exclude_docs):
                counters[docnum] += 1
        
        # Return the doc numbers where the correspoding number of "hits" in
        # the array equal the number of subqueries.
        return (i for i, count in enumerate(counters) if count == target)
    
    def doc_scores(self, searcher, weighting = None, exclude_docs = None):
        if not self.subqueries:
            return []
        
        self._split_queries()
        if self._notqueries:
            exclude_docs = _not_vector(self._notqueries, searcher, exclude_docs)
        
        # Sort the subqueries by their estimated size, smallest to
        # largest. Can't just do .sort(key = ) because I want to check
        # the smallest value later and I don't want to call estimate_size()
        # twice because it is potentially expensive.
        subqs = [(q.estimate_size(searcher), q) for q in self._subqueries]
        subqs.sort()
        
        # If the smallest estimated size is 0, nothing will match.
        if subqs[0][0] == 0:
            return []
        
        # Removed the estimated sizes, leaving just the sorted subqueries.
        subqs = [q for _, q in subqs]
        
        counters = {}
        scores = {}
        
        first = True
        for q in subqs:
            atleastone = first
            for docnum, score in q.doc_scores(searcher, weighting = weighting, exclude_docs = exclude_docs):
                if first:
                    scores[docnum] = score
                    counters[docnum] = 1
                elif docnum in scores:
                    scores[docnum] += score
                    counters[docnum] += 1
                    atleastone = True
            
            first = False
                
            if not atleastone:
                return []
        
        target = len(subqs)
        return ((docnum, score) for docnum, score in scores.iteritems()
                if counters[docnum] == target)


class Or(CompoundQuery):
    """
    Matches documents that match ANY of the subqueries.
    """
    
    # This is used by the superclass's __unicode__ method.
    JOINT = " OR "
    
    def estimate_size(self, searcher):
        return sum(q.estimate_size(searcher) for q in self.subqueries)
    
    def docs(self, searcher, exclude_docs = None):
        if not self.subqueries:
            return
        
        hits = BitVector(searcher.doc_count_all())
        
        self._split_queries()
        if self._notqueries:
            exclude_docs = _not_vector(self._notqueries, searcher, exclude_docs)
        
        getbit = hits.__getitem__
        setbit = hits.set
        for q in self._subqueries:
            for docnum in q.docs(searcher, exclude_docs = exclude_docs):
                if not getbit(docnum):
                    yield docnum
                setbit(docnum)
    
    def doc_scores(self, searcher, weighting = None, exclude_docs = None):
        if not self.subqueries:
            return []
        
        self._split_queries()
        if self._notqueries:
            exclude_docs = _not_vector(self._notqueries, searcher, exclude_docs)
        
        scores = defaultdict(float)
        #scores = array("f", [0] * searcher.doc_count_all())
        for query in self._subqueries:
            for docnum, weight in query.doc_scores(searcher, weighting = weighting, exclude_docs = exclude_docs):
                scores[docnum] += weight
        
        return scores.iteritems()
        #return ((i, score) for i, score in enumerate(scores) if score)


class Not(Query):
    """
    Excludes any documents that match the subquery.
    """
    
    def __init__(self, query, boost = 1.0):
        """
        query is a Query object, the results of which should be excluded from
        a parent query.
        boost is a boost factor that should be applied to the raw score of
        results matched by this query.
        """
        
        self.query = query
        self.boost = boost
        
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                                     repr(self.query))
    
    def __unicode__(self):
        return u"NOT " + unicode(self.query)
    
    def normalize(self):
        if self.query is None:
            return None
        return self
    
    def docs(self, searcher):
        return self.query.docs(searcher)
    
    def replace(self, oldtext, newtext):
        return Not(self.query.replace(oldtext, newtext), boost = self.boost)
    
    def all_terms(self, termset):
        self.query.all_terms(termset)
        
    def existing_terms(self, searcher, termset, reverse = False):
        self.query.existing_terms(searcher, termset, reverse = reverse)


class AndNot(Query):
    """
    Binary boolean query of the form 'a AND NOT b', where documents that match
    b are removed from the matches for a. This form can lead to counter-intuitive
    results when there is another "not" query on the right side (so the double-
    negative leads to documents the user might have meant to exclude being
    included). For this reason, you probably want to use Not() (which excludes the
    results of a subclause) instead of this logical operator, especially when
    parsing user input.
    """
    
    def __init__(self, positive, negative, boost = 1.0):
        """
        :positive: query to INCLUDE.
        :negative: query whose matches should be EXCLUDED.
        :boost: boost factor that should be applied to the raw score of
            results matched by this query.
        """
        
        self.positive = positive
        self.negative = negative
        self.boost = boost
    
    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__,
                               self.positive, self.negative)
    
    def __unicode__(self):
        return u"%s ANDNOT %s" % (self.postive, self.negative)
    
    def normalize(self):
        if self.positive is None:
            return None
        elif self.negative is None:
            return self.positive.normalize()
        
        pos = self.positive.normalize()
        neg = self.negative.normalize()
        
        if pos is None:
            return None
        elif neg is None:
            return pos
        
        return AndNot(pos, neg, boost = self.boost)
    
    def replace(self, oldtext, newtext):
        return AndNot(self.positive.replace(oldtext, newtext),
                      self.negative.replace(oldtext, newtext),
                      boost = self.boost)
    
    def all_terms(self, termset):
        self.positive.all_terms(termset)
        
    def existing_terms(self, searcher, termset, reverse = False):
        self.positive.existing_terms(searcher, termset, reverse = reverse)
    
    def docs(self, searcher, exclude_docs = None):
        excl = _not_vector([self.negative], searcher, exclude_docs)
        return self.positive.docs(searcher, exclude_docs = excl)
    
    def doc_scores(self, searcher, exclude_docs = None):
        excl = _not_vector([self.negative], searcher, exclude_docs)
        return self.positive.doc_scores(searcher, exclude_docs = excl)


class MultiTerm(Query):
    """
    Abstract base class for queries that operate on multiple
    terms in the same field
    """
    
    def __init__(self, fieldname, words, boost = 1.0):
        self.fieldname = fieldname
        self.words = words
        self.boost = boost
    
    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__,
                               self.fieldname, self.words)
    
    def _or_query(self, searcher):
        fn = self.fieldname
        return Or([Term(fn, word) for word in self._words(searcher)])
    
    def normalize(self):
        return self.__class__(self.fieldname,
                              [w for w in self.words if w is not None],
                              boost = self.boost)
    
    def _words(self, searcher):
        return self.words
    
    def all_terms(self, termset):
        fieldname = self.fieldname
        for word in self.words:
            termset.add(fieldname, word)
    
    def existing_terms(self, searcher, termset, reverse = False):
        fieldname = self.fieldname
        for word in self._words(searcher):
            t = (fieldname, word)
            contains = t in searcher
            if reverse: contains = not contains
            if contains:
                termset.add(t)
    
    def estimate_size(self, searcher):
        fieldnum = searcher.fieldname_to_num(self.fieldname)
        return sum(searcher.doc_frequency(fieldnum, text)
                   for text in self._words(searcher))

    def docs(self, searcher, exclude_docs = None):
        return self._or_query(searcher).docs(searcher, exclude_docs = exclude_docs)

    def doc_scores(self, searcher, weighting = None, exclude_docs = None):
        return self._or_query(searcher).doc_scores(searcher,
                                                               weighting = weighting,
                                                               exclude_docs = exclude_docs)


class ExpandingTerm(MultiTerm):
    """
    Abstract base class for queries that take one term and expand it into
    multiple terms, such as Prefix and Wildcard.
    """
    
    def __init__(self, fieldname, text, boost = 1.0):
        self.fieldname = fieldname
        self.text = text
        self.boost = boost
    
    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__,
                               self.fieldname, self.text)
    
    def __unicode__(self):
        return "%s:%s*" % (self.fieldname, self.text)

    def all_terms(self, termset):
        termset.add((self.fieldname, self.text))
    
    def normalize(self):
        return self


class Prefix(ExpandingTerm):
    """
    Matches documents that contain any terms that start with the given text.
    """
    
    def _words(self, searcher):
        return searcher.expand_prefix(self.fieldname, self.text)


_wildcard_exp = re.compile("(.*?)([?*]|$)");
class Wildcard(ExpandingTerm):
    """
    Matches documents that contain any terms that match a wildcard expression.
    """
    
    def __init__(self, fieldname, text, boost = 1.0):
        """
        fieldname is the field to search in. text is an expression to
        search for, which may contain ? and/or * wildcard characters.
        Note that matching a wildcard expression that starts with a wildcard
        is very inefficent, since the query must test every term in the field.
        boost is a boost factor that should be applied to the raw score of
        results matched by this query.
        """
        
        self.fieldname = fieldname
        self.text = text
        self.boost = boost
        
        self.expression = re.compile(fnmatch.translate(text))
        
        # Get the "prefix" -- the substring before the first wildcard.
        qm = text.find("?")
        st = text.find("*")
        if qm < 0 and st < 0:
            self.prefix = ""
        elif qm < 0:
            self.prefix = text[:st]
        elif st < 0:
            self.prefix = text[:qm]
        else:
            self.prefix = text[:min(st, qm)]
    
    def _words(self, searcher):
        if self.prefix:
            candidates = searcher.expand_prefix(self.fieldname, self.prefix)
        else:
            candidates = searcher.lexicon(self.fieldname)
        
        exp = self.expression
        for text in candidates:
            if exp.match(text):
                yield text
                
    def normalize(self):
        # If there are no wildcard characters in this "wildcard",
        # turn it into a simple Term.
        if self.text.find("*") < 0 and self.text.find("?") < 0:
            return Term(self.fieldname, self.text, boost = self.boost)
        else:
            return self


class TermRange(MultiTerm):
    """
    Matches documents containing any terms in a given range.
    """
    
    def __init__(self, fieldname, words, boost = 1.0):
        """
        fieldname is the name of the field to search. start and end are the
        lower and upper (inclusive) bounds of the range of tokens to match.
        boost is a boost factor that should be applied to the raw score of
        results matched by this query.
        """
        
        self.fieldname = fieldname
        if len(words) < 2 or len(words) > 2:
            raise QueryError("TermRange argument %r should be [startword, endword]" % words)
        self.start = words[0]
        self.end = words[1]
        self.words = words
        self.boost = boost
    
    def __repr__(self):
        return '%s(%r, %r, %r)' % (self.__class__.__name__, self.fieldname,
                                   self.start, self.end)
    
    def __unicode__(self):
        return u"%s:%s..%s" % (self.fieldname, self.start, self.end)
    
    def replace(self, oldtext, newtext):
        if self.start == oldtext:
            return TermRange(self.fieldname, (newtext, self.end), boost = self.boost)
        elif self.end == oldtext:
            return TermRange(self.fieldname, (self.start, newtext), boost = self.boost)
        else:
            return self
    
    def _words(self, searcher):
        fieldnum = searcher.fieldname_to_num(self.fieldname)
        end = self.end
        
        for fnum, t, _, _ in searcher.iter_from(fieldnum, self.start):
            while fnum == fieldnum and t <= end:
                yield t
    
    def all_terms(self, searcher, termset):
        pass
    

class Variations(ExpandingTerm):
    """
    Query that automatically searches for morphological variations
    of the given word in the same field.
    """
    
    def __init__(self, fieldname, text, boost = 1.0):
        self.fieldname = fieldname
        self.text = text
        self.boost = boost
        self.words = variations(self.text)
    
    def __unicode__(self):
        return u"<%s>" % self.text
    
    def docs(self, searcher, exclude_docs = None):
        return self._or_query(searcher).docs(searcher, exclude_docs = exclude_docs)
    
    def doc_scores(self, searcher, weighting = None, exclude_docs = None):
        return self._or_query(searcher).doc_scores(searcher,
                                                   weighting = weighting,
                                                   exclude_docs = exclude_docs)


class Phrase(MultiTerm):
    """
    Matches documents containing a given phrase.
    """
    
    def __init__(self, fieldname, words, slop = 1, boost = 1.0):
        """
        fieldname is the field to search.
        words is a list of tokens (the phrase to search for).
        slop is the number of words allowed between each "word" in
        the phrase; the default of 1 means the phrase must match exactly.
        boost is a boost factor that should be applied to the raw score of
        results matched by this query.
        """
        
        for w in words:
            if not isinstance(w, unicode):
                raise ValueError("'%s' is not unicode" % w)
        
        self.fieldname = fieldname
        self.words = words
        self.slop = slop
        self.boost = boost
    
    def __unicode__(self):
        return u'%s:"%s"' % (self.fieldname, u" ".join(self.words))
    
    def normalize(self):
        if len(self.words) == 1:
            return Term(self.fieldname, self.words[0])
            
        return self.__class__(self.fieldname, [w for w in self.words if w is not None],
                              slop = self.slop, boost = self.boost)
    
    def replace(self, oldtext, newtext):
        def rep(w):
            if w == oldtext:
                return newtext
            else:
                return w
        
        return Phrase(self.fieldname, [rep(w) for w in self.words],
                      slop = self.slop, boost = self.boost)
    
    def _and_query(self):
        fn = self.fieldname
        return And([Term(fn, word) for word in self.words])
    
    def estimate_size(self, searcher):
        return self._and_query().estimate_size(searcher)
    
    def docs(self, searcher, exclude_docs = None):
        return (docnum for docnum, _ in self.doc_scores(searcher,
                                                        exclude_docs = exclude_docs))
    
    def _posting_impl(self, searcher, fieldnum, weighting, exclude_docs):
        words = self.words
        slop = self.slop
        
        # Get the set of documents that contain all the words
        docs = frozenset(self._and_query().docs(searcher))
        
        # Maps docnums to lists of valid positions
        current = {}
        # Maps docnums to scores
        scores = {}
        first = True
        for word in words:
            #print "word=", word
            for docnum, positions in searcher.positions(fieldnum, word, exclude_docs = exclude_docs):
                if docnum not in docs: continue
                #print "  docnum=", docnum
                
                # TODO: Use position boosts if available
                if first:
                    current[docnum] = positions
                    #print "    *current=", positions
                    scores[docnum] = weighting.score(searcher, fieldnum, word, docnum, 1.0)
                elif docnum in current:
                    currentpositions = current[docnum]
                    #print "    current=", currentpositions
                    #print "    positions=", positions
                    newpositions = []
                    for newpos in positions:
                        start = bisect_left(currentpositions, newpos - slop)
                        end = bisect_right(currentpositions, newpos + slop)
                        for curpos in currentpositions[start:end]:
                            if abs(newpos - curpos) <= slop:
                                newpositions.append(newpos)
                    
                    #print "    newpositions=", newpositions
                    if not newpositions:
                        del current[docnum]
                        del scores[docnum]
                    else:
                        current[docnum] = newpositions
                        scores[docnum] += weighting.score(searcher, fieldnum, word, docnum, 1.0)
            
            first = False
        
        #print "scores=", scores
        return scores.iteritems()
    
    def _vector_impl(self, searcher, fieldnum, weighting, exclude_docs):
        dr = searcher.doc_reader
        words = self.words
        wordset = frozenset(words)
        maxword = max(wordset)
        slop = self.slop
        
        aq = self._and_query()
        for docnum, score in aq.doc_scores(searcher, weighting = weighting, exclude_docs = exclude_docs):
            positions = {}
            for w, poslist in dr.vector_as(docnum, fieldnum, "positions"):
                if w in wordset:
                    positions[w] = poslist
                elif w > maxword:
                    break
            
            current = positions[words[0]]
            if not current:
                return
            
            for w in words[1:]:
                poslist = positions[w]
                newcurrent = []
                for pos in poslist:
                    start = bisect_left(current, pos - slop)
                    end = bisect_right(current, pos + slop)
                    for cpos in current[start:end]:
                        if abs(cpos - pos) <= slop:
                            newcurrent.append(pos)
                            break
                
                current = newcurrent
                if not current:
                    break
        
            if current:
                yield docnum, score * len(current)
    
    def doc_scores(self, searcher, weighting = None, exclude_docs = None):
        fieldnum = searcher.fieldname_to_num(self.fieldname)
        
        # Shortcut the query if one of the words doesn't exist.
        for word in self.words:
            if (fieldnum, word) not in searcher: return []
        
        field = searcher.field(self.fieldname)
        weighting = weighting or searcher.weighting
        if field.format and field.format.supports("positions"):
            return self._posting_impl(searcher, fieldnum, weighting, exclude_docs)
        elif field.vector and field.vector.supports("positions"):
            return self._vector_impl(searcher, fieldnum, weighting, exclude_docs)
        else:
            raise QueryError("Phrase search: %r field has no positions" % self.fieldname)
        
        

if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = reading
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""
This module contains classes that allow reading from an index.
"""

from bisect import bisect_right
from heapq import heapify, heapreplace, heappop, nlargest
from threading import Lock, RLock

from whoosh.util import ClosableMixin, protected
from whoosh.fields import FieldConfigurationError, UnknownFieldError

# Exceptions

class TermNotFound(Exception):
    pass

# Reader classes

class DocReader(ClosableMixin):
    """
    Do not instantiate this object directly. Instead use Index.doc_reader().
    
    Reads document-related information from a segment. The main
    interface is to either iterate on this object to yield the document
    stored fields, or use e.g. docreader[10] to get the stored
    fields for a specific document number.
    
    Each DocReader represents two open files. Be sure to close() the
    reader when you're finished with it.
    """
    
    def __init__(self, storage, segment, schema):
        self.storage = storage
        self.segment = segment
        self.schema = schema
        self._scorable_fields = schema.scorable_fields()
        
        self.doclength_table = storage.open_records(segment.doclen_filename)
        self.docs_table = storage.open_table(segment.docs_filename)
        #self.cache = FifoCache()
        
        self.vector_table = None
        self.is_closed = False
        self._sync_lock = Lock()
        
        self._fieldnum_to_pos = dict((fieldnum, i) for i, fieldnum
                                     in enumerate(schema.scorable_fields()))
    
    def _open_vectors(self):
        if not self.vector_table:
            self.vector_table = self.storage.open_table(self.segment.vector_filename)
    
    @protected
    def __getitem__(self, docnum):
        """Returns the stored fields for the given document.
        """
        return self.docs_table.get(docnum)
    
    @protected
    def __iter__(self):
        """Yields the stored fields for all documents.
        """
        
        is_deleted = self.segment.is_deleted
        for docnum in xrange(0, self.segment.max_doc):
            if not is_deleted(docnum):
                yield self.docs_table.get(docnum)
    
    def close(self):
        """Closes the open files associated with this reader.
        """
        
        self.doclength_table.close()
        self.docs_table.close()
        if self.vector_table:
            self.vector_table.close()
        self.is_closed = True
    
    def doc_count_all(self):
        """Returns the total number of documents, DELETED OR UNDELETED,
        in this reader.
        """
        return self.segment.doc_count_all()
    
    def doc_count(self):
        """Returns the total number of UNDELETED documents in this reader.
        """
        return self.segment.doc_count()
    
    def field_length(self, fieldid):
        """Returns the total number of terms in the given field.
        """
        
        fieldid = self.schema.to_number(fieldid)
        return self.segment.field_length(fieldid)
    
    @protected
    def doc_field_length(self, docnum, fieldid):
        """Returns the number of terms in the given field in the
        given document. This is used by some scoring algorithms.
        """
        
        fieldid = self.schema.to_number(fieldid)
        if fieldid not in self._scorable_fields:
            raise FieldConfigurationError("Field %r does not store lengths" % fieldid)
        
        pos = self._fieldnum_to_pos[fieldid]
        return self.doclength_table.get(docnum, pos)
    
    @protected
    def doc_field_lengths(self, docnum):
        """Returns an array corresponding to the lengths of the
        scorable fields in the given document. It's up to the
        caller to correlate the positions of the numbers in the
        array with the scorable fields in the schema.
        """
        
        return self.doclength_table.get_record(docnum)
    
    def vector_format(self, fieldnum):
        """
        Returns the vector format object associated with the given
        field, or None if the field is not vectored.
        """
        return self.schema.field_by_number(fieldnum).vector
    
    def vector_supports(self, fieldnum, name):
        """
        Returns true if the vector format for the given field supports
        the data interpretation.
        """
        format = self.vector_format(fieldnum)
        if format is None: return False
        return format.supports(name)
    
    @protected
    def vector(self, docnum, fieldnum):
        """Yields a sequence of raw (text, data) tuples representing
        the term vector for the given document and field.
        """
        
        self._open_vectors()
        readfn = self.vector_format(fieldnum).read_postvalue
        return self.vector_table.postings((docnum, fieldnum), readfn)
    
    def vector_as(self, docnum, fieldnum, astype):
        """Yields a sequence of interpreted (text, data) tuples
        representing the term vector for the given document and
        field.
        
        This method uses the vector format object's 'data_to_*'
        method to interpret the data. For example, if the vector
        format has a 'data_to_positions()' method, you can use
        vector_as(x, y, "positions") to get a positions vector.
        """
        
        format = self.vector_format(fieldnum)
        
        if format is None:
            raise FieldConfigurationError("Field %r is not vectored" % self.schema.number_to_name(fieldnum))
        elif not format.supports(astype):
            raise FieldConfigurationError("Field %r does not support %r" % (self.schema.number_to_name(fieldnum),
                                                                            astype))
        
        interpreter = format.interpreter(astype)
        for text, data in self.vector(docnum, fieldnum):
            yield (text, interpreter(data))
    

class MultiDocReader(DocReader):
    """
    Do not instantiate this object directly. Instead use Index.doc_reader().
    
    Reads document-related information by aggregating the results from
    multiple segments. The main interface is to either iterate on this
    object to yield the document stored fields, or use getitem (e.g. docreader[10])
    to get the stored fields for a specific document number.
    
    Each MultiDocReader represents (number of segments * 2) open files.
    Be sure to close() the reader when you're finished with it.
    """
    
    def __init__(self, doc_readers, doc_offsets, schema):
        self.doc_readers = doc_readers
        self.doc_offsets = doc_offsets
        self.schema = schema
        self._scorable_fields = self.schema.scorable_fields()
        
        self.is_closed = False
        self._sync_lock = Lock()
        
    def __getitem__(self, docnum):
        segmentnum, segmentdoc = self._segment_and_docnum(docnum)
        return self.doc_readers[segmentnum].__getitem__(segmentdoc)
    
    def __iter__(self):
        for reader in self.doc_readers:
            for result in reader:
                yield result
    
    def close(self):
        """Closes the open files associated with this reader.
        """
        
        for d in self.doc_readers:
            d.close()
        self.is_closed = True
    
    def doc_count_all(self):
        return sum(dr.doc_count_all() for dr in self.doc_readers)
    
    def doc_count(self):
        return sum(dr.doc_count() for dr in self.doc_readers)
    
    def field_length(self, fieldnum):
        return sum(dr.field_length(fieldnum) for dr in self.doc_readers)
    
    def doc_field_length(self, docnum, fieldid):
        fieldid = self.schema.to_number(fieldid)
        segmentnum, segmentdoc = self._segment_and_docnum(docnum)
        return self.doc_readers[segmentnum].doc_field_length(segmentdoc, fieldid)
    
    def doc_field_lengths(self, docnum):
        segmentnum, segmentdoc = self._segment_and_docnum(docnum)
        return self.doc_readers[segmentnum].doc_field_lengths(segmentdoc)
    
    def unique_count(self, docnum):
        segmentnum, segmentdoc = self._segment_and_docnum(docnum)
        return self.doc_readers[segmentnum].unique_count(segmentdoc)
    
    def _document_segment(self, docnum):
        return max(0, bisect_right(self.doc_offsets, docnum) - 1)
    
    def _segment_and_docnum(self, docnum):
        segmentnum = self._document_segment(docnum)
        offset = self.doc_offsets[segmentnum]
        return segmentnum, docnum - offset
    
    def vector(self, docnum):
        segmentnum, segmentdoc = self._segment_and_docnum(docnum)
        return self.doc_readers[segmentnum].vector(segmentdoc)
    
    def _doc_info(self, docnum, key):
        segmentnum, segmentdoc = self._segment_and_docnum(docnum)
        return self.doc_readers[segmentnum]._doc_info(segmentdoc, key)
    

class TermReader(ClosableMixin):
    """
    Do not instantiate this object directly. Instead use Index.term_reader().
    
    Reads term information from a segment.
    
    Each TermReader represents two open files. Remember to close() the reader when
    you're done with it.
    """
    
    def __init__(self, storage, segment, schema):
        """
        :storage: The storage object in which the segment resides.
        :segment: The segment to read from.
        :schema: The index's schema object.
        """
        
        self.segment = segment
        self.schema = schema
        
        self.term_table = storage.open_table(segment.term_filename)
        self.is_closed = False
        self._sync_lock = Lock()
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.segment)
    
    @protected
    def __iter__(self):
        """Yields (fieldnum, token, docfreq, indexfreq) tuples for
        each term in the reader, in lexical order.
        """
        
        tt = self.term_table
        for (fn, t), termcount in tt:
            yield (fn, t, tt.posting_count((fn, t)), termcount)
    
    @protected
    def __contains__(self, term):
        """Returns True if the given term tuple (fieldid, text) is
        in this reader.
        """
        return (self.schema.to_number(term[0]), term[1]) in self.term_table
    
    def close(self):
        """Closes the open files associated with this reader.
        """
        self.term_table.close()
        self.is_closed = True
    
    def format(self, fieldname):
        """Returns the Format object corresponding to the given field name.
        """
        if fieldname in self.schema:
            return self.schema.field_by_name(fieldname).format
        else:
            raise UnknownFieldError(fieldname)
    
    @protected
    def _term_info(self, fieldnum, text):
        try:
            return self.term_table.get((fieldnum, text))
        except KeyError:
            raise TermNotFound("%s:%r" % (fieldnum, text))
    
    @protected
    def doc_frequency(self, fieldid, text):
        """Returns the document frequency of the given term (that is,
        how many documents the term appears in).
        """
        
        fieldid = self.schema.to_number(fieldid)
        if (fieldid, text) not in self.term_table:
            return 0
        return self.term_table.posting_count((fieldid, text))
    
    @protected
    def frequency(self, fieldid, text):
        """Returns the total number of instances of the given term
        in the collection.
        """
        
        fieldid = self.schema.to_number(fieldid)
        if (fieldid, text) not in self.term_table:
            return 0
        return self.term_table.get((fieldid, text))
    
    def doc_count_all(self):
        """Returns the total number of documents, DELETED OR UNDELETED,
        in this reader.
        """
        return self.segment.doc_count_all()
    
    @protected
    def iter_from(self, fieldnum, text):
        """Yields (field_num, text, doc_freq, collection_frequency) tuples
        for all terms in the reader, starting at the given term.
        """
        
        tt = self.term_table
        postingcount = tt.posting_count
        for (fn, t), termcount in tt.iter_from((fieldnum, text)):
            yield (fn, t, postingcount((fn, t)), termcount)
    
    def expand_prefix(self, fieldid, prefix):
        """Yields terms in the given field that start with the given prefix.
        """
        
        fieldid = self.schema.to_number(fieldid)
        for fn, t, _, _ in self.iter_from(fieldid, prefix):
            if fn != fieldid or not t.startswith(prefix):
                return
            yield t
    
    def all_terms(self):
        """Yields (fieldname, text) tuples for every term in the index.
        """
        
        num2name = self.schema.number_to_name
        current_fieldnum = None
        current_fieldname = None
        
        for fn, t, _, _ in self:
            # Only call self.schema.number_to_name when the
            # field number changes.
            if fn != current_fieldnum:
                current_fieldnum = fn
                current_fieldname = num2name(fn)
            yield (current_fieldname, t)
    
    def iter_field(self, fieldid):
        """Yields (text, doc_frequency, term_frequency) tuples for
        all terms in the given field.
        """
        
        fieldid = self.schema.to_number(fieldid)
        for fn, t, docfreq, freq in self.iter_from(fieldid, ''):
            if fn != fieldid:
                return
            yield t, docfreq, freq
    
    def lexicon(self, fieldid):
        """Yields all terms in the given field."""
        
        for t, _, _ in self.iter_field(fieldid):
            yield t
    
    def most_frequent_terms(self, fieldid, number = 5):
        """Yields the top 'number' most frequent terms in the given field as
        a series of (frequency, text) tuples.
        """
        return nlargest(number,
                        ((indexfreq, token)
                         for token, _, indexfreq
                         in self.iter_field(fieldid)))
    
    # Posting retrieval methods
    
    @protected
    def postings(self, fieldnum, text, exclude_docs = None):
        """
        Yields raw (docnum, data) tuples for each document containing
        the current term.
        
        :exclude_docs:
            a set of document numbers to ignore. This
            is used by queries to skip documents that have already been
            eliminated from consideration.
        :boost: a factor by which to multiply each weight.
        """
        
        is_deleted = self.segment.is_deleted
        no_exclude = exclude_docs is None
        
        # The format object is actually responsible for parsing the
        # posting data from disk.
        readfn = self.schema.field_by_number(fieldnum).format.read_postvalue
        
        for docnum, data in self.term_table.postings((fieldnum, text), readfn = readfn):
            if not is_deleted(docnum)\
               and (no_exclude or docnum not in exclude_docs):
                yield docnum, data
    
    def weights(self, fieldnum, text, exclude_docs = None, boost = 1.0):
        """
        Yields (docnum, term_weight) tuples for each document containing
        the given term. The current field must have stored term weights
        for this to work.
        
        :exclude_docs:
            a set of document numbers to ignore. This
            is used by queries to skip documents that have already been
            eliminated from consideration.
        :boost: a factor by which to multiply each weight.
        """
        
        
        is_deleted = self.segment.is_deleted
        no_exclude = exclude_docs is None
        
        # The format object is actually responsible for parsing the
        # posting data from disk.
        readfn = self.schema.field_by_number(fieldnum).format.read_weight
        
        for docnum, weight in self.term_table.postings((fieldnum, text), readfn = readfn):
            if not is_deleted(docnum)\
               and (no_exclude or docnum not in exclude_docs):
                yield docnum, weight * boost
    
    def postings_as(self, fieldnum, text, astype, exclude_docs = None):
        """Yields interpreted data for each document containing
        the given term. The current field must have stored positions
        for this to work.
        
        :astype:
            how to interpret the posting data, for example
            "positions". The field must support the interpretation.
        :exclude_docs:
            a set of document numbers to ignore. This
            is used by queries to skip documents that have already been
            eliminated from consideration.
        :boost: a factor by which to multiply each weight.
        """
        
        format = self.schema.field_by_number(fieldnum).format
        
        if not format.supports(astype):
            raise FieldConfigurationError("Field %r format does not support %r" % (self.schema.name_to_number(fieldnum),
                                                                                   astype))
        
        interp = format.interpreter(astype)
        for docnum, data in self.postings(fieldnum, text, exclude_docs = exclude_docs):
            yield (docnum, interp(data))
    
    def positions(self, fieldnum, text, exclude_docs = None):
        """Yields (docnum, [positions]) tuples for each document containing
        the given term. The current field must have stored positions
        for this to work.
        
        :exclude_docs:
            a set of document numbers to ignore. This
            is used by queries to skip documents that have already been
            eliminated from consideration.
        :boost: a factor by which to multiply each weight.
        """
        
        return self.postings_as(fieldnum, text, "positions", exclude_docs = exclude_docs)


class MultiTermReader(TermReader):
    """Do not instantiate this object directly. Instead use Index.term_reader().
    
    Reads term information by aggregating the results from
    multiple segments.
    
    Each MultiTermReader represents (number of segments * 2) open files.
    Be sure to close() the reader when you're finished with it.
    """
    
    def __init__(self, term_readers, doc_offsets, schema):
        self.term_readers = term_readers
        self.doc_offsets = doc_offsets
        self.schema = schema
        
        self.is_closed = False
        self._sync_lock = Lock()
    
    def __contains__(self, term):
        return any(tr.__contains__(term) for tr in self.term_readers)
    
    def __iter__(self):
        return self._merge_iters([iter(r) for r in self.term_readers])
    
    def iter_from(self, fieldnum, text):
        return self._merge_iters([r.iter_from(fieldnum, text) for r in self.term_readers])
    
    def close(self):
        """
        Closes the open files associated with this reader.
        """
        
        for tr in self.term_readers:
            tr.close()
        self.is_closed = True
    
    def doc_frequency(self, fieldnum, text):
        if (fieldnum, text) not in self:
            return 0
        
        return sum(r.doc_frequency(fieldnum, text) for r in self.term_readers)
    
    def frequency(self, fieldnum, text):
        if (fieldnum, text) not in self:
            return 0
        
        return sum(r.frequency(fieldnum, text) for r in self.term_readers)
    
    def _merge_iters(self, iterlist):
        # Merge-sorts terms coming from a list of
        # term iterators (TermReader.__iter__() or
        # TermReader.iter_from()).
        
        # Fill in the list with the head term from each iterator.
        # infos is a list of [headterm, iterator] lists.
        
        current = []
        for it in iterlist:
            fnum, text, docfreq, termcount = it.next()
            current.append((fnum, text, docfreq, termcount, it))
        heapify(current)
        
        # Number of active iterators
        active = len(current)
        while active > 0:
            # Peek at the first term in the sorted list
            fnum, text = current[0][:2]
            docfreq = 0
            termcount = 0
            
            # Add together all terms matching the first
            # term in the list.
            while current and current[0][0] == fnum and current[0][1] == text:
                docfreq += current[0][2]
                termcount += current[0][3]
                it = current[0][4]
                try:
                    fn, t, df, tc = it.next()
                    heapreplace(current, (fn, t, df, tc, it))
                except StopIteration:
                    heappop(current)
                    active -= 1
                
            # Yield the term with the summed frequency and
            # term count.
            yield (fnum, text, docfreq, termcount)
    
    def postings(self, fieldnum, text, exclude_docs = None):
        """Yields raw (docnum, data) tuples for each document containing
        the current term. This is useful if you simply want to know
        which documents contain the current term. Use weights() or
        positions() if you need to term weight or positions in each
        document.
        
        exclude_docs can be a set of document numbers to ignore. This
        is used by queries to skip documents that have already been
        eliminated from consideration.
        """
        
        for i, r in enumerate(self.term_readers):
            offset = self.doc_offsets[i]
            if (fieldnum, text) in r:
                for docnum, data in r.postings(fieldnum, text, exclude_docs = exclude_docs):
                    yield (docnum + offset, data)
                    
    def weights(self, fieldnum, text, exclude_docs = None, boost = 1.0):
        for i, r in enumerate(self.term_readers):
            offset = self.doc_offsets[i]
            if (fieldnum, text) in r:
                for docnum, weight in r.weights(fieldnum, text,
                                                exclude_docs = exclude_docs, boost = boost):
                    yield (docnum + offset, weight)



if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = scoring
#===============================================================================
# Copyright 2008 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""This module contains classes for scoring (and sorting) search results.
"""

from __future__ import division
from array import array
from math import log, pi
import weakref


class Weighting(object):
    """Abstract base class for weighting objects. A weighting
    object implements a scoring algorithm.
    
    Concrete subclasses must implement the score() method, which
    returns a score given a term and a document in which that term
    appears.
    """
    
    #self.doc_count = searcher.doc_count_all()
    #self.max_doc_freq = ix.max_doc_freq()
    #self.unique_term_count = ix.unique_term_count()
    #self.avg_doc_length = self.index_length / self.doc_count

    def __init__(self):
        self._idf_cache = {}
    
    def idf(self, searcher, fieldnum, text):
        """Calculates the Inverse Document Frequency of the
        current term. Subclasses may want to override this.
        """
        
        cache = self._idf_cache
        term = (fieldnum, text)
        if term in cache: return cache[term]
        
        df = searcher.doc_frequency(fieldnum, text)
        idf = log(searcher.doc_count_all() / (df + 1)) + 1.0
        cache[term] = idf
        return idf

    def avg_field_length(self, searcher, fieldnum):
        """Returns the average length of the field per document.
        (i.e. total field length / total number of documents)
        """
        return searcher.field_length(fieldnum) / searcher.doc_count_all()
    
    def fl_over_avfl(self, searcher, docnum, fieldnum):
        """Returns the length of the current field in the current
        document divided by the average length of the field
        across all documents. This is used by some scoring algorithms.
        """
        return searcher.doc_field_length(docnum, fieldnum) / self.avg_field_length(searcher, fieldnum)
    
    def score(self, searcher, fieldnum, text, docnum, weight, QTF = 1):
        """Returns the score for a given term in the given document.
        
        :searcher: the searcher doing the scoring.
        :fieldnum: the field number of the term being scored.
        :text: the text of the term being scored.
        :docnum: the doc number of the document being scored.
        :weight: the frequency * boost of the term in this document.
        :QTF: the frequency of the term in the query.
        """
        raise NotImplementedError

# Scoring classes

class BM25F(Weighting):
    """Generates a BM25F score.
    """
    
    def __init__(self, B = 0.75, K1 = 1.2, field_B = None):
        """B and K1 are free parameters, see the BM25 literature.
        field_B can be a dictionary mapping fieldnums to field-specific B values.
        field_boost can be a dictionary mapping fieldnums to field boost factors.
        """
        
        super(self.__class__, self).__init__()
        self.K1 = K1
        self.B = B
        
        if field_B is None: field_B = {}
        self._field_B = field_B
    
    def score(self, searcher, fieldnum, text, docnum, weight, QTF = 1):
        if not searcher.scorable(fieldnum): return weight
        
        B = self._field_B.get(fieldnum, self.B)
        avl = self.avg_field_length(searcher, fieldnum)
        idf = self.idf(searcher, fieldnum, text)
        l = searcher.doc_field_length(docnum, fieldnum)
        
        w = weight / ((1 - B) + B * (l / avl))
        return idf * (w / (self.K1 + w))
        

# The following scoring algorithms are translated from classes in
# the Terrier search engine's uk.ac.gla.terrier.matching.models package.

class Cosine(Weighting):
    """A cosine vector-space scoring algorithm similar to Lucene's.
    """
    
    def score(self, searcher, fieldnum, text, docnum, weight, QTF = 1):
        idf = self.idf(searcher, fieldnum, text)
        
        DTW = (1.0 + log(weight)) * idf
        QMF = 1.0 # TODO: Fix this
        QTW = ((0.5 + (0.5 * QTF / QMF))) * idf
        return DTW * QTW


class DFree(Weighting):
    """The DFree probabilistic weighting algorithm, translated into Python
    from Terrier's Java implementation.
    """
    
    def score(self, searcher, fieldnum, text, docnum, weight, QTF = 1):
        if not searcher.scorable(fieldnum): return weight
        
        fieldlen = searcher.doc_field_length(docnum, fieldnum)
        prior = weight / fieldlen
        post = (weight + 1.0) / fieldlen
        invprior = searcher.field_length(fieldnum) / searcher.frequency(fieldnum, text)
        norm = weight * log(post / prior, 2)
        
        return QTF\
                * norm\
                * (weight * (- log(prior * invprior, 2))
                   + (weight + 1.0) * (+ log(post * invprior, 2)) + 0.5 * log(post/prior, 2))


class DLH13(Weighting):
    """The DLH13 probabilistic weighting algorithm, translated into Python
    from Terrier's Java implementation.
    """
    
    def __init__(self, k = 0.5):
        super(self.__class__, self).__init__()
        self.k = k

    def score(self, searcher, fieldnum, text, docnum, weight, QTF = 1):
        if not searcher.scorable(fieldnum): return weight
        
        k = self.k
        dl = searcher.doc_field_length(docnum, fieldnum)
        f = weight / dl
        tc = searcher.frequency(fieldnum, text)
        dc = searcher.doc_count_all()
        avl = self.avg_field_length(searcher, fieldnum)
        
        return QTF * (weight * log((weight * avl / dl) * (dc / tc), 2) + 0.5 * log(2.0 * pi * weight * (1.0 - f))) / (weight + k)


class Hiemstra_LM(Weighting):
    """The Hiemstra LM probabilistic weighting algorithm, translated into Python
    from Terrier's Java implementation.
    """
    
    def __init__(self, c = 0.15):
        super(self.__class__, self).__init__()
        self.c = c
        
    def score(self, searcher, fieldnum, text, docnum, weight, QTF = 1):
        if not searcher.scorable(fieldnum): return weight
        
        c = self.c
        tc = searcher.frequency(fieldnum, text)
        dl = searcher.doc_field_length(docnum, fieldnum)
        return log(1 + (c * weight * searcher.field_length(fieldnum)) / ((1 - c) * tc * dl))


class InL2(Weighting):
    """The InL2 LM probabilistic weighting algorithm, translated into Python
    from Terrier's Java implementation.
    """
    
    def __init__(self, c = 1.0):
        super(self.__class__, self).__init__()
        self.c = c
    
    def score(self, searcher, fieldnum, text, docnum, weight, QTF = 1):
        if not searcher.scorable(fieldnum): return weight
        
        dl = searcher.doc_field_length(docnum, fieldnum)
        TF = weight * log(1.0 + (self.c * self.avg_field_length(searcher, fieldnum)) / dl)
        norm = 1.0 / (TF + 1.0)
        df = searcher.doc_frequency(fieldnum, text)
        idf_dfr = log((searcher.doc_count_all() + 1) / (df + 0.5), 2)
        
        return TF * idf_dfr * QTF * norm


class TF_IDF(Weighting):
    """Instead of doing any real scoring, this simply returns tf * idf.
    """
    
    def score(self, searcher, fieldnum, text, docnum, weight, QTF = 1):
        return weight * self.idf(searcher, fieldnum, text)


class Frequency(Weighting):
    """Instead of doing any real scoring, simply returns the
    term frequency. This may be useful when you don't care about
    normalization and weighting.
    """
    
    def score(self, searcher, fieldnum, text, docnum, weight, QTF = 1):
        return searcher.frequency(fieldnum, text)


# Sorting classes

class Sorter(object):
    """Abstract base class for sorter objects. See the 'sortedby'
    keyword argument to searching.Searcher.search().
    
    Concrete subclasses must implement the order() method, which
    takes a sequence of doc numbers and returns it sorted.
    """
    
    def order(self, searcher, docnums, reverse = False):
        """Returns a sorted list of document numbers.
        """
        raise NotImplementedError


class NullSorter(Sorter):
    """Sorter that does nothing."""
    
    def order(self, searcher, docnums, reverse = False):
        """Returns docnums as-is. The 'reverse' keyword is ignored."""
        return docnums


class FieldSorter(Sorter):
    """Used by searching.Searcher to sort document results based on the
    value of an indexed field, rather than score. See the 'sortedby'
    keyword argument to searching.Searcher.search().
    
    This object creates a cache of document orders for the given field.
    Creating the cache may make the first sorted search of a field
    seem slow, but subsequent sorted searches of the same field will
    be much faster.
    """
    
    def __init__(self, fieldname, missingfirst = False):
        """
        :fieldname: The name of the field to sort by.
        :missingfirst: Place documents which don't have the given
            field first in the sorted results. The default is to put those
            documents last (after all documents that have the given field).
        """
        
        self.fieldname = fieldname
        self.missingfirst = missingfirst
        self._searcher = None
        self._cache = None

    def _make_cache(self, searcher):
        # Is this searcher already cached?
        if self._cache and self._searcher and self._searcher() is searcher:
            return
        
        fieldnum = searcher.fieldname_to_num(self.fieldname)
        
        # Create an array of an int for every document in the index.
        N = searcher.doc_count_all()
        if self.missingfirst:
            default = -1
        else:
            default = N + 1
        cache = array("i", [default] * N)
        
        # For every document containing every term in the field, set
        # its array value to the term's (inherently sorted) position.
        i = -1
        for i, word in enumerate(searcher.lexicon(fieldnum)):
            for docnum, _ in searcher.postings(fieldnum, word):
                cache[docnum] = i
        
        self.limit = i
        self._cache = cache
        self._searcher = weakref.ref(searcher, self._delete_cache)
    
    def _delete_cache(self, obj):
        # Callback function, called by the weakref implementation when
        # the searcher we're using to do the ordering goes away.
        self._cache = self._searcher = None
    
    def order(self, searcher, docnums, reverse = False):
        """Takes a sequence of docnums (as produced by query.docs()) and
        returns a list of docnums sorted by the field values.
        """
        
        self._make_cache(searcher)
        return sorted(docnums,
                      key = self._cache.__getitem__,
                      reverse = reverse)


class MultiFieldSorter(FieldSorter):
    """Used by searching.Searcher to sort document results based on the
    value of an indexed field, rather than score. See the 'sortedby'
    keyword argument to searching.Searcher.search().
    
    This sorter uses multiple fields, so if for two documents the first
    field has the same value, it will use the second field to sort them,
    and so on.
    """
    
    def __init__(self, fieldnames, missingfirst = False):
        """
        :fieldnames: A list of field names to sort by.
        :missingfirst: Place documents which don't have the given
            field first in the sorted results. The default is to put those
            documents last (after all documents that have the given field).
        """
        
        self.fieldnames = fieldnames
        self.sorters = [FieldSorter(fn)
                        for fn in fieldnames]
        self.missingfirst = missingfirst
    
    def order(self, searcher, docnums, reverse = False):
        sorters = self.sorters
        missingfirst = self.missingfirst
        for s in sorters:
            s._make_cache(searcher, missingfirst)
        
        return sorted(docnums,
                      key = lambda x: tuple((s._cache[x] for s in sorters)),
                      reverse = reverse)

########NEW FILE########
__FILENAME__ = searching
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

from __future__ import division
import time

from whoosh import classify, query, scoring, util
from whoosh.support.bitvector import BitVector
from whoosh.util import TopDocs

"""This module contains classes and functions related to searching the index.
"""

# Searcher class

class Searcher(util.ClosableMixin):
    """Object for searching an index. Produces Results objects.
    """
    
    def __init__(self, ix, weighting = scoring.BM25F):
        """
        :ix: the index.Index object to search.
        :weighting: a scoring.Weighting implementation to use to
            score the hits. If this is a class it will automatically be
            instantiated.
        """
        
        self.term_reader = ix.term_reader()
        self.doc_reader = ix.doc_reader()
        self.schema = ix.schema
        self._max_weight = ix.max_weight()
        self._doc_count_all = self.doc_reader.doc_count_all()
        
        if callable(weighting):
            weighting = weighting()
        self.weighting = weighting
        
        self.is_closed = False
        
        self._copy_methods()
    
    def __del__(self):
        if not self.is_closed:
            self.close()
    
    def __iter__(self):
        return iter(self.term_reader)
    
    def __contains__(self, term):
        return term in self.term_reader
    
    def _copy_methods(self):
        # Copy methods from child doc_reader and term_reader objects onto this
        # object.
        for name in ("field_length", "doc_field_length"):
            setattr(self, name, getattr(self.doc_reader, name))
            
        for name in ("lexicon", "expand_prefix", "iter_from", "doc_frequency",
                     "frequency", "postings", "weights", "positions"):
            setattr(self, name, getattr(self.term_reader, name))
    
    def doc_count_all(self):
        return self._doc_count_all
    
    def max_weight(self):
        return self._max_weight
    
    def close(self):
        self.term_reader.close()
        self.doc_reader.close()
        self.is_closed = True
    
    def document(self, **kw):
        """
        Convenience function returns the stored fields of a document
        matching the given keyword arguments, where the keyword keys are
        field names and the values are terms that must appear in the field.
        
        Where Searcher.documents() returns a generator, this function returns
        either a dictionary or None. Use it when you assume the given keyword
        arguments either match zero or one documents (i.e. at least one of the
        fields is a unique key).
        """
        
        for p in self.documents(**kw):
            return p
    
    def documents(self, **kw):
        """
        Convenience function returns the stored fields of a document
        matching the given keyword arguments, where the keyword keys are
        field names and the values are terms that must appear in the field.
        
        Returns a generator of dictionaries containing the
        stored fields of any documents matching the keyword arguments.
        """
        
        q = query.And([query.Term(k, v) for k, v in kw.iteritems()])
        doc_reader = self.doc_reader
        return (doc_reader[docnum] for docnum in q.docs(self))
    
    def search(self, query, limit = 5000,
               weighting = None,
               sortedby = None, reverse = False):
        """Runs the query represented by the query object and returns a Results object.
        
        :query: a query.Query object representing the search query. You can translate
            a query string into a query object with e.g. qparser.QueryParser.
        :limit: the maximum number of documents to score. If you're only interested in
            the top N documents, you can set limit=N to limit the scoring for a faster
            search.
        :weighting: if this parameter is not None, use this weighting object to score the
            results instead of the default.
        :sortedby: if this parameter is not None, the results are sorted instead of scored.
            If this value is a string, the results are sorted by the field named in the string.
            If this value is a list or tuple, it is assumed to be a sequence of strings and the
            results are sorted by the fieldnames in the sequence. Otherwise 'sortedby' should be
            a scoring.Sorter object.
            
            The fields you want to sort by must be indexed.
            
            For example, to sort the results by the 'path' field::
            
                searcher.search(q, sortedby = "path")
                
            To sort the results by the 'path' field and then the 'category' field::
                
                searcher.search(q, sortedby = ("path", "category"))
                
            To use a sorting object::
            
                searcher.search(q, sortedby = scoring.NullSorter)
        
        :reverse: if 'sortedby' is not None, this reverses the direction of the sort.
        """
        
        doc_reader = self.doc_reader
        
        t = time.time()
        if sortedby is not None:
            if isinstance(sortedby, basestring):
                sortedby = scoring.FieldSorter(sortedby)
            elif isinstance(sortedby, (list, tuple)):
                sortedby = scoring.MultiFieldSorter(sortedby)
            elif callable(sortedby):
                sortedby = sortedby()
            
            scored_list = sortedby.order(self, query.docs(self), reverse = reverse)
            docvector = BitVector(doc_reader.doc_count_all(),
                                  source = scored_list)
            if len(scored_list) > limit:
                scored_list = list(scored_list)[:limit]
        else:
            # Sort by scores
            topdocs = TopDocs(limit, doc_reader.doc_count_all())
            topdocs.add_all(query.doc_scores(self, weighting = weighting or self.weighting))
            
            best = topdocs.best()
            if best:
                # topdocs.best() returns a list like
                # [(docnum, score), (docnum, score), ... ]
                # This unpacks that into two lists: docnums and scores
                scored_list, scores = zip(*topdocs.best())
            else:
                scored_list = []
                scores = []
            
            docvector = topdocs.docs
        t = time.time() - t
            
        return Results(self,
                       query,
                       scored_list,
                       docvector,
                       runtime = t,
                       scores = scores)
    
    def fieldname_to_num(self, fieldname):
        return self.schema.name_to_number(fieldname)
    
    def field(self, fieldname):
        return self.schema.field_by_name(fieldname)
    
    def scorable(self, fieldid):
        return self.schema[fieldid].scorable
    
    def stored_fields(self, docnum):
        return self.doc_reader[docnum]
    
#    def field_length(self, fieldid):
#        return self.doc_reader.field_length(fieldid)
#    
#    def doc_length(self, docnum):
#        return self.doc_reader.doc_length(docnum)
#    
#    def doc_field_length(self, docnum, fieldid):
#        return self.doc_reader.doc_field_length(docnum, fieldid)
#    
#    def doc_unique_count(self, docnum):
#        return self.doc_reader.unique_count(docnum)
#    
#    def lexicon(self, fieldid):
#        return self.term_reader.lexicon(fieldid)
#    
#    def expand_prefix(self, fieldid, prefix):
#        return self.term_reader.expand_prefix(fieldid, prefix)
#    
#    def iter_from(self, fieldid, text):
#        return self.term_reader.iter_from(fieldid, text)
#    
#    def doc_frequency(self, fieldid, text):
#        return self.term_reader.doc_frequency(fieldid, text)
#    
#    def frequency(self, fieldid, text):
#        return self.term_reader.frequency(fieldid, text)
#    
#    def postings(self, fieldid, text, exclude_docs = None):
#        return self.term_reader.postings(fieldid, text, exclude_docs = exclude_docs)
#    
#    def weights(self, fieldid, text, exclude_docs = None):
#        return self.term_reader.weights(fieldid, text, exclude_docs = exclude_docs)
#    
#    def positions(self, fieldid, text, exclude_docs = None):
#        return self.term_reader.positions(fieldid, text, exclude_docs = exclude_docs)


# Results class

class Results(object):
    """
    This object is not instantiated by the user; it is returned by a Searcher.
    This object represents the results of a search query. You can mostly
    use it as if it was a list of dictionaries, where each dictionary
    is the stored fields of the document at that position in the results.
    """
    
    def __init__(self, searcher, query, scored_list, docvector,
                 scores = None, runtime = 0):
        """
        :doc_reader: a reading.DocReader object from which to fetch
            the fields for result documents.
        :query: the original query that created these results.
        :scored_list: an ordered list of document numbers
            representing the 'hits'.
        :docvector: a BitVector object where the indices are
            document numbers and an 'on' bit means that document is
            present in the results.
        :runtime: the time it took to run this search.
        """
        
        self.searcher = searcher
        self.query = query
        
        self.scored_list = scored_list
        self.scores = scores
        self.docs = docvector
        self.runtime = runtime
    
    def __repr__(self):
        return "<%s/%s Results for %r runtime=%s>" % (len(self), self.docs.count(),
                                                      self.query,
                                                      self.runtime)
    
    def __len__(self):
        """Returns the TOTAL number of documents found by this search. Note this
        may be greater than the number of ranked documents.
        """
        return self.docs.count()
    
    def __getitem__(self, n):
        doc_reader = self.searcher.doc_reader
        if isinstance(n, slice):
            return [doc_reader[i] for i in self.scored_list.__getitem__(n)] 
        else:
            return doc_reader[self.scored_list[n]] 
    
    def __iter__(self):
        """Yields the stored fields of each result document in ranked order.
        """
        doc_reader = self.searcher.doc_reader
        for docnum in self.scored_list:
            yield doc_reader[docnum]
    
    def score(self, n):
        """Returns the score for the document at the Nth position in the
        list of results. If the search was not scored, returns None."""
        
        if self.scores:
            return self.scores[n]
        else:
            return None
    
    def scored_length(self):
        """Returns the number of RANKED documents. Note this may be fewer
        than the total number of documents the query matched, if you used
        the 'limit' keyword of the Searcher.search() method to limit the
        scoring."""
        
        return len(self.scored_list)
    
    def docnum(self, n):
        """Returns the document number of the result at position n in the
        list of ranked documents. Use __getitem__ (i.e. Results[n]) to
        get the stored fields directly.
        """
        return self.scored_list[n]
    
    def key_terms(self, fieldname, docs = 10, terms = 5,
                  model = classify.Bo1Model, normalize = True):
        """Returns the 'numterms' most important terms from the top 'numdocs' documents
        in these results. "Most important" is generally defined as terms that occur
        frequently in the top hits but relatively infrequently in the collection as
        a whole.
        
        :fieldname: Look at the terms in this field. This field must store vectors.
        :docs: Look at this many of the top documents of the results.
        :terms: Return this number of important terms.
        :model: The classify.ExpansionModel to use. See the classify module.
        """
        
        docs = max(docs, self.scored_length())
        if docs <= 0: return
        
        doc_reader = self.searcher.doc_reader
        fieldnum = self.searcher.fieldname_to_num(fieldname)
        
        expander = classify.Expander(self.searcher, fieldname, model = model)
        for docnum in self.scored_list[:docs]:
            expander.add(doc_reader.vector_as(docnum, fieldnum, "weight"))
        
        return expander.expanded_terms(terms, normalize = normalize)

    def extend(self, results):
        """Appends hits from 'results' (that are not already in this
        results object) to the end of these results.
        
        :results: another results object.
        """
        
        docs = self.docs
        self.scored_list.extend(docnum for docnum in results.scored_list
                                if docnum not in docs)
        self.docs = docs | results.docs
        
        # TODO: merge the query terms?
    
    def filter(self, results):
        """Removes any hits that are not also in the other results object.
        """
        
        docs = self.docs & results.docs
        self.scored_list = [docnum for docnum in self.scored_list if docnum in docs]
        self.docs = docs
    
    def upgrade(self, results, reverse = False):
        """Re-sorts the results so any hits that are also in 'results' appear before
        hits not in 'results', otherwise keeping their current relative positions.
        This does not add the documents in the other results object to this one.
        
        :results: another results object.
        :reverse: if True, lower the position of hits in the other
            results object instead of raising them.
        """
        
        scored_list = self.scored_list
        otherdocs = results.docs
        arein = [docnum for docnum in scored_list if docnum in otherdocs]
        notin = [docnum for docnum in scored_list if docnum not in otherdocs]
        
        if reverse:
            self.scored_list = notin + arein
        else:
            self.scored_list = arein + notin
            
    def upgrade_and_extend(self, results):
        """Combines the effects of extend() and increase(): hits that are
        also in 'results' are raised. Then any hits from 'results' that are
        not in this results object are appended to the end of these
        results.
        
        :results: another results object.
        """
        
        docs = self.docs
        otherdocs = results.docs
        scored_list = self.scored_list
        
        arein = [docnum for docnum in scored_list if docnum in otherdocs]
        notin = [docnum for docnum in scored_list if docnum not in otherdocs]
        other = [docnum for docnum in results.scored_list if docnum not in docs]
        
        self.docs = docs | otherdocs
        self.scored_list = arein + notin + other
        

# Utilities

class Paginator(object):
    """
    Helper class that divides search results into pages, for use in
    displaying the results.
    """
    
    def __init__(self, results, perpage = 10):
        """
        :results: the searching.Results object from a search.
        :perpage: the number of hits on each page.
        """
        
        self.results = results
        self.perpage = perpage
    
    def from_to(self, pagenum):
        """Returns the lowest and highest indices on the given
        page. For example, with 10 results per page, from_to(1)
        would return (0, 9).
        """
        
        lr = len(self.results)
        perpage = self.perpage
        
        lower = (pagenum - 1) * perpage
        upper = lower + perpage
        if upper > lr:
            upper = lr
        
        return (lower, upper)
    
    def pagecount(self):
        """Returns the total number of pages of results.
        """
        
        return len(self.results) // self.perpage + 1
    
    def page(self, pagenum):
        """Returns a list of the stored fields for the documents
        on the given page.
        """
        
        lower, upper = self.from_to(pagenum)
        return self.results[lower:upper]



if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = spelling
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""This module contains functions/classes using a Whoosh index
as a backend for a spell-checking engine.
"""

from collections import defaultdict

from whoosh import analysis, fields, query, searching, writing
from whoosh.support.levenshtein import relative, distance

class SpellChecker(object):
    """Implements a spell-checking engine using a search index for the
    backend storage and lookup. This class is based on the Lucene
    contributed spell-checker code.
    
    To use this object::
    
        st = store.FileStorage("spelldict")
        sp = SpellChecker(st)
        
        sp.add_words([u"aardvark", u"manticore", u"zebra", ...])
        # or
        ix = index.open_dir("index")
        sp.add_field(ix, "content")
        
        suggestions = sp.suggest(u"ardvark", number = 2)
    """
    
    def __init__(self, storage, indexname = "SPELL",
                 booststart = 2.0, boostend = 1.0,
                 mingram = 3, maxgram = 4,
                 minscore = 0.5):
        """
        :storage: The storage object in which to create the
            spell-checker's dictionary index.
        :indexname: The name to use for the spell-checker's
            dictionary index. You only need to change this if you
            have multiple spelling indexes in the same storage.
        :booststart: How much to boost matches of the first
            N-gram (the beginning of the word).
        :boostend: How much to boost matches of the last
            N-gram (the end of the word).
        :mingram: The minimum gram length to store.
        :maxgram: The maximum gram length to store.
        :minscore: The minimum score matches much achieve to
            be returned.
        """
        
        self.storage = storage
        self.indexname = indexname
        
        self._index = None
        
        self.booststart = booststart
        self.boostend = boostend
        self.mingram = mingram
        self.maxgram = maxgram
    
    def index(self):
        """Returns the backend index of this object (instantiating it if
        it didn't already exist).
        """
        
        import index
        if not self._index:
            create = not index.exists(self.storage, indexname = self.indexname)
            self._index = index.Index(self.storage, create = create,
                                      schema = self._schema(), indexname = self.indexname)
        return self._index
    
    def _schema(self):
        # Creates a schema given this object's mingram and maxgram attributes.
        
        from fields import Schema, FieldType, Frequency, ID, STORED
        from analysis import SimpleAnalyzer
        
        idtype = ID()
        freqtype = FieldType(Frequency(SimpleAnalyzer()))
        
        fls = [("word", STORED), ("score", STORED)]
        for size in xrange(self.mingram, self.maxgram + 1):
            fls.extend([("start%s" % size, idtype),
                        ("end%s" % size, idtype),
                        ("gram%s" % size, freqtype)])
            
        return Schema(**dict(fls))
    
    def suggest(self, text, number = 3, usescores = False):
        """Returns a list of suggested alternative spellings of 'text'. You must
        add words to the dictionary (using add_field, add_words, and/or add_scored_words)
        before you can use this.
        
        :text: The word to check.
        :number: The maximum number of suggestions to return.
        :usescores: Use the per-word score to influence the suggestions.
        :*returns*: list
        """
        
        grams = defaultdict(list)
        for size in xrange(self.mingram, self.maxgram + 1):
            key = "gram%s" % size
            nga = analysis.NgramAnalyzer(size)
            for t in nga(text):
                grams[key].append(t.text)
        
        queries = []
        for size in xrange(self.mingram, min(self.maxgram + 1, len(text))):
            key = "gram%s" % size
            gramlist = grams[key]
            queries.append(query.Term("start%s" % size, gramlist[0], boost = self.booststart))
            queries.append(query.Term("end%s" % size, gramlist[-1], boost = self.boostend))
            for gram in gramlist:
                queries.append(query.Term(key, gram))
        
        q = query.Or(queries)
        ix = self.index()
        
        s = searching.Searcher(ix)
        try:
            results = s.search(q)
            
            length = len(results)
            if len(results) > number*2:
                length = len(results)//2
            fieldlist = results[:length]
            
            suggestions = [(fs["word"], fs["score"])
                           for fs in fieldlist
                           if fs["word"] != text]
            
            if usescores:
                def keyfn(a):
                    return 0 - (1/distance(text, a[0])) * a[1]
            else:
                def keyfn(a):
                    return distance(text, a[0])
            
            suggestions.sort(key = keyfn)
        finally:
            s.close()
        
        return [word for word, _ in suggestions[:number]]
        
    def add_field(self, ix, fieldname):
        """Adds the terms in a field from another index to the backend dictionary.
        This method calls add_scored_words() and uses each term's frequency as the
        score. As a result, more common words will be suggested before rare words.
        If you want to calculate the scores differently, use add_scored_words()
        directly.
        
        :ix: The index.Index object from which to add terms.
        :fieldname: The field name (or number) of a field in the source
            index. All the indexed terms from this field will be added to the
            dictionary.
        """
        
        tr = ix.term_reader()
        try:
            self.add_scored_words((w, freq) for w, _, freq in tr.iter_field(fieldname))
        finally:
            tr.close()
    
    def add_words(self, ws, score = 1):
        """Adds a list of words to the backend dictionary.
        
        :ws: A sequence of words (strings) to add to the dictionary.
        :score: An optional score to use for ALL the words in 'ws'.
        """
        self.add_scored_words((w, score) for w in ws)
    
    def add_scored_words(self, ws):
        """Adds a list of ("word", score) tuples to the backend dictionary.
        Associating words with a score lets you use the 'usescores' keyword
        argument of the suggest() method to order the suggestions using the
        scores.
        
        :ws: A sequence of ("word", score) tuples.
        """
        
        writer = writing.IndexWriter(self.index())
        for text, score in ws:
            if text.isalpha():
                fields = {"word": text, "score": score}
                for size in xrange(self.mingram, self.maxgram + 1):
                    nga = analysis.NgramAnalyzer(size)
                    gramlist = [t.text for t in nga(text)]
                    if len(gramlist) > 0:
                        fields["start%s" % size] = gramlist[0]
                        fields["end%s" % size] = gramlist[-1]
                        fields["gram%s" % size] = " ".join(gramlist)
                writer.add_document(**fields)
        writer.commit()
    
if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = store
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""This module contains objects that implement storage of index files.
Abstracting storage behind this simple interface allows indexes to
be stored in other media besides as a folder of files. For example,
RamStorage keeps the "files" in memory.
"""

import os
from cStringIO import StringIO
from threading import Lock

from whoosh import tables
from whoosh.structfile import StructFile
import logging

from google.appengine.api import memcache 
from google.appengine.ext import db

class LockError(Exception):
    pass



class Storage(object):
    """Abstract base class for storage objects.
    """
    
    def __iter__(self):
        return iter(self.list())
    
    def create_table(self, name, **kwargs):
        f = self.create_file(name)
        return tables.TableWriter(f, **kwargs)
    
    def create_arrays(self, name, typecode, **kwargs):
        f = self.create_file(name)
        return tables.ArrayWriter(f, typecode, **kwargs)
    
    def create_records(self, name, typecode, length, **kwargs):
        f = self.create_file(name)
        return tables.RecordWriter(f, typecode, length, **kwargs)
    
    def open_table(self, name, **kwargs):
        f = self.open_file(name)
        return tables.TableReader(f, **kwargs)

    def open_arrays(self, name, **kwargs):
        f = self.open_file(name)
        return tables.ArrayReader(f, **kwargs)

    def open_records(self, name, **kwargs):
        f = self.open_file(name)
        return tables.RecordReader(f, **kwargs)

    def close(self):
        pass
    
    def optimize(self):
        pass


class FileStorage(Storage):
    """Storage object that stores the index as files in a directory on disk.
    """
    
    def __init__(self, path):
        self.folder = path
        
        if not os.path.exists(path):
            raise IOError("Directory %s does not exist" % path)
    
    def _fpath(self, fname):
        return os.path.join(self.folder, fname)
    
    def clean(self):
        path = self.folder
        if not os.path.exists(path):
            os.mkdir(path)
        
        files = self.list()
        for file in files:
            os.remove(os.path.join(path,file))
    
    def list(self):
        try:
            files = os.listdir(self.folder)
        except IOError:
            files = []
            
        return files
    
    def file_exists(self, name):
        return os.path.exists(self._fpath(name))
    def file_modified(self, name):
        return os.path.getmtime(self._fpath(name))
    def file_length(self, name):
        return os.path.getsize(self._fpath(name))
    
    def delete_file(self, name):
        os.remove(self._fpath(name))
        
    def rename_file(self, frm, to):
        if os.path.exists(self._fpath(to)):
            os.remove(self._fpath(to))
        os.rename(self._fpath(frm),self._fpath(to))
        
    def create_file(self, name):
        f = StructFile(open(self._fpath(name), "wb"))
        f._name = name
        return f
    
    def open_file(self, name, compressed = False):
        f = StructFile(open(self._fpath(name), "rb"))
        f._name = name
        return f
    
    def lock(self, name):
        os.mkdir(self._fpath(name))
        return True
    
    def unlock(self, name):
        fpath = self._fpath(name)
        if os.path.exists(fpath):
            os.rmdir(fpath)
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self.folder))


#class SqliteStorage(FileStorage):
#    """
#    Storage object that keeps tables in a sqlite database.
#    """
#    
#    def __init__(self, path):
#        super(SqliteStorage, self).__init__(path)
#        self.con = sqlite3.connect(os.path.join(path, "tables.db"))
#
#    def create_table(self, name, postings = False, **kwargs):
#        name = name.replace(".", "_")
#        if postings:
#            self.con.execute("CREATE TABLE %s (key TEXT, offset INTEGER, length INTEGER, count INTEGER, value BLOB)" % name)
#            posting_file = self.create_file("%s_postings" % name)
#            return tables.PostingSQLWriter(self.con, name, posting_file, **kwargs)
#        else:
#            self.con.execute("CREATE TABLE %s (key TEXT, value BLOB)" % name)
#            return tables.SQLWriter(self.con, name, **kwargs)
#            
#    def open_table(self, name, postings = False, **kwargs):
#        name = name.replace(".", "_")
#        if postings:
#            posting_file = self.open_file("%s_postings" % name)
#            return tables.PostingSQLReader(self.con, name, posting_file, **kwargs)
#        else:
#            return tables.SQLReader(self.con, name, **kwargs)
#        
#    def lock(self, name):
#        return True
#    
#    def unlock(self, name):
#        pass
        

class RamStorage(Storage):
    """Storage object that keeps the index in memory.
    """
    
    def __init__(self):
        self.files = {}
        self.locks = {}
    
    def __iter__(self):
        return iter(self.list())
    
    def list(self):
        return self.files.keys()

    def clean(self):
        self.files = {}

    def total_size(self):
        return sum(self.file_length(f) for f in self.list())

    def file_exists(self, name):
        return name in self.files
    
    def file_length(self, name):
        if name not in self.files:
            raise NameError
        return len(self.files[name])

    def delete_file(self, name):
        if name not in self.files:
            raise NameError
        del self.files[name]

    def rename_file(self, name, newname):
        if name not in self.files:
            raise NameError
        content = self.files[name]
        del self.files[name]
        self.files[newname] = content

    def create_file(self, name):
        def onclose_fn(sfile):
            self.files[name] = sfile.file.getvalue()
        f = StructFile(StringIO(), name = name, onclose = onclose_fn)
        return f

    def open_file(self, name):
        if name not in self.files:
            raise NameError
        return StructFile(StringIO(self.files[name]))
    
    def lock(self, name):
        if name not in self.locks:
            self.locks[name] = Lock()
        if not self.locks[name].acquire(False):
            raise LockError("Could not lock %r" % name)
        return True
    
    def unlock(self, name):
        if name in self.locks:
            self.locks[name].release()

class DatastoreFile(db.Model):
  value = db.BlobProperty()
  
  def __init__(self, *args, **kwargs):
    super(DatastoreFile, self).__init__(*args, **kwargs)
    self.data = StringIO()
  
  @classmethod
  def loadfile(cls, name):
    value = memcache.get(name, namespace="DatastoreFile")
    if value is None:
      file = cls.get_by_key_name(name)
      memcache.set(name, file.value, namespace="DatastoreFile")
    else:
      file = cls(value=value)
    file.data = StringIO(file.value)
    return file
    
  def close(self):
    oldvalue = self.value
    self.value = self.getvalue()
    if oldvalue != self.value:
      self.put()
      memcache.set(self.key().id_or_name(), self.value, namespace="DatastoreFile")
       
  def tell(self):
    return self.data.tell()

  def write(self, data):
    return self.data.write(data)
   
  def read(self, length):
    return self.data.read(length)
  
  def seek(self, *args):
    return self.data.seek(*args)

  def readline(self):
    return self.data.readline()
   
  def getvalue(self):
    return self.data.getvalue()
   
class DataStoreStorage(Storage):
    """
    Storage object that keeps tables in a the appengine datastore
    """
    
    def __init__(self, name):
        self.name = name
        self.locks = {}
            
    def __iter__(self):
        return iter(self.list())
       
    def list(self):
        query = DatastoreFile.all()
        keys = []
        for file in query:
            keys.append(file.key().id_or_name().replace(self.name, "")) 
        return keys
       
    def clean(self):
        pass

    def total_size(self):
        return sum(self.file_length(f) for f in self.list())

    def file_exists(self, name):
        return DatastoreFile.get_by_key_name("%s%s" % (self.name, name)) != None
    
    def file_length(self, name):
        return len(DatastoreFile.get_by_key_name("%s%s" % (self.name, name)).value)

    def delete_file(self, name):
        return DatastoreFile.get_by_key_name("%s%s" % (self.name, name)).delete()

    def rename_file(self, name, newname):
        file = DatastoreFile.get_by_key_name("%s%s" % (self.name, name))
        newfile = DatastoreFile(key_name="%s%s" % (self.name, newname))
        newfile.value = file.value
        newfile.put()
        file.delete()

    def create_file(self, name):
        def onclose_fn(sfile):
            sfile.file.close()
        f = StructFile(DatastoreFile(key_name="%s%s" % (self.name, name)), name = name, onclose = onclose_fn)
        return f

    def open_file(self, name):
        return StructFile(DatastoreFile.loadfile("%s%s" % (self.name, name)))
    
    def lock(self, name):
        if name not in self.locks:
            self.locks[name] = Lock()
        if not self.locks[name].acquire(False):
            raise LockError("Could not lock %r" % name)
        return True
    
    def unlock(self, name):
        if name in self.locks:
            self.locks[name].release()
    

def copy_to_ram(storage):
    """Copies the given storage object into a new
    RamStorage object.
    :*returns*: storage.RamStorage
    """
    
    import shutil #, time
    #t = time.time()
    ram = RamStorage()
    for name in storage.list():
        f = storage.open_file(name)
        r = ram.create_file(name)
        shutil.copyfileobj(f.file, r.file)
        f.close()
        r.close()
    #print time.time() - t, "to load index into ram"
    return ram


########NEW FILE########
__FILENAME__ = structfile
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""Contains a class for reading/writing a data stream to a file using binary
encoding and compression methods such as variable-length encoded integers.
"""

from cPickle import dump as dump_pickle
from cPickle import load as load_pickle
from marshal import dump as dump_marshal
from marshal import load as load_marshal
from struct import calcsize, pack, unpack
from array import array


_INT_SIZE = calcsize("i")
_USHORT_SIZE = calcsize("H")
_ULONG_SIZE = calcsize("L")
_FLOAT_SIZE = calcsize("f")

# Utility functions

def float_to_byte(value, mantissabits = 5, zeroexp = 2):
    # Assume int size == float size
    
    fzero = (63 - zeroexp) << mantissabits
    bits = unpack("i", pack("f", value))[0]
    smallfloat = bits >> (24 - mantissabits)
    if smallfloat < fzero:
        # Map negative numbers and 0 to 0
        # Map underflow to next smallest non-zero number
        if bits <= 0:
            return 0
        else:
            return 1
    elif smallfloat >= fzero + 0x100:
        # Map overflow to largest number
        return 255
    else:
        return smallfloat - fzero
    
def byte_to_float(b, mantissabits = 5, zeroexp = 2):
    if b == 0:
        return 0.0
    
    bits = (b & 0xff) << (24 - mantissabits)
    bits += (63 - zeroexp) << 24
    return unpack("f", pack("i", bits))[0]
    

# Varint cache

# Build a cache of the varint byte sequences for the first
# N integers, so we don't have to constantly recalculate them
# on the fly. This makes a small but noticeable difference.

def encode_varint(i):
    s = ""
    while (i & ~0x7F) != 0:
        s += chr((i & 0x7F) | 0x80)
        i = i >> 7
    s += chr(i)
    return s

_varint_cache_size = 512
_varint_cache = []
for i in xrange(0, _varint_cache_size):
    _varint_cache.append(encode_varint(i))
_varint_cache = tuple(_varint_cache)


# Main class

class StructFile(object):
    """Wraps a normal file (or file-like) object and provides additional
    methods for reading and writing indexes, especially variable-length
    integers (varints) for efficient space usage.
    
    The underlying file-like object only needs to implement write() and
    tell() for writing, and read(), tell(), and seek() for reading.
    
    IMPORTANT: This class is *fundamentally thread UNSAFE*. It is intended
    that higher-level code calling this object will use locks to protect
    access to it.
    """
    
    def __init__(self, fileobj, name = None, onclose = None):
        """
        file is the file-like object to wrap.
        """
        
        self.file = fileobj
        self.onclose = onclose
        self._name = name
        
        self.tell = self.file.tell
        self.seek = self.file.seek
        if hasattr(self.file, "read"):
            self.read = self.file.read
        else:
            self.read = None
        if hasattr(self.file, "write"):
            self.write = self.file.write
        else:
            self.write = None
            
        self.is_closed = False
        
        self.sbyte_array = array("b", [0])
        self.int_array = array("i", [0])
        self.ushort_array = array("H", [0])
        self.ulong_array = array("L", [0])
        self.float_array = array("f", [0.0])
        
        # If this is wrapping a real file object (not a file-like object),
        # replace with faster variants that only work on real files.
        if isinstance(fileobj, file):
            for typename in ("sbyte", "int", "ushort", "ulong", "float", "array"):
                setattr(self, "write_"+typename, getattr(self, "_write_"+typename))
                setattr(self, "read_"+typename, getattr(self, "_read_"+typename))
                
        self._type_writers = {"b": self.write_sbyte,
                              "B": self.write_byte,
                              "i": self.write_int,
                              "H": self.write_ushort,
                              "L": self.write_ulong,
                              "f": self.write_float}
        self._type_readers = {"b": self.read_sbyte,
                              "B": self.read_byte,
                              "i": self.read_int,
                              "H": self.read_ushort,
                              "L": self.read_ulong,
                              "f": self.read_float}
    
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._name)
    
    def __del__(self):
        if not self.is_closed:
            self.close()
    
    def write_value(self, typecode, n):
        """Writes a value 'n' of type 'typecode'.
        """
        self._type_writers[typecode](n)
    
    def read_value(self, typecode):
        """Writes a value of type 'typecode'.
        """
        return self._type_readers[typecode]()
    
    def write_byte(self, n):
        """Writes a single byte to the wrapped file, shortcut for
        file.write(chr(n)).
        """
        self.file.write(chr(n))
    
    def write_sbyte(self, n):
        """Writes a signed byte value to the wrapped file.
        """
        self.sbyte_array[0] = n
        self.file.write(self.sbyte_array.tostring())
    
    def write_int(self, n):
        """Writes a binary integer value to the wrapped file,.
        """
        self.int_array[0] = n
        self.file.write(self.int_array.tostring())
    
    def write_ushort(self, n):
        """Writes an unsigned binary short integer to the wrapped file.
        """
        self.ushort_array[0] = n
        self.file.write(self.ushort_array.tostring())
    
    def write_ulong(self, n):
        """Writes an unsigned binary integer value to the wrapped file.
        """
        self.ulong_array[0] = n
        self.file.write(self.ulong_array.tostring())
    
    def write_float(self, n):
        """Writes a binary float value to the wrapped file.
        """
        self.float_array[0] = n
        self.file.write(self.float_array.tostring())
    
    def write_array(self, arry):
        """Writes an array to the wrapped file.
        """
        self.file.write(arry.tostring())
    
    # These variants are faster but only work on built-in "file" objects
    # (not on any file-like object with a write() method). They are swapped in
    # for the methods above when this object is wrapping a real file.
    
    def _write_sbyte(self, n):
        """Writes a signed byte value to the wrapped file.
        """
        self.sbyte_array[0] = n
        self.sbyte_array.tofile(self.file)
    def _write_int(self, n):
        """Writes a binary integer value to the wrapped file,.
        """
        self.int_array[0] = n
        self.int_array.tofile(self.file)
    def _write_ushort(self, n):
        """Writes an unsigned binary short integer value to the wrapped file.
        """
        self.ushort_array[0] = n
        self.ushort_array.tofile(self.file)
    def _write_ulong(self, n):
        """Writes an unsigned binary integer value to the wrapped file.
        """
        self.ulong_array[0] = n
        self.ulong_array.tofile(self.file)
    def _write_float(self, n):
        """Writes a binary float value to the wrapped file.
        """
        self.float_array[0] = n
        self.float_array.tofile(self.file)
    def _write_array(self, arry):
        """Writes an array to the wrapped file.
        """
        arry.tofile(self.file)
    
    def write_string(self, s):
        """Writes a string to the wrapped file. This method writes the
        length of the string first, so you can read the string back
        without having to know how long it was.
        """
        self.write_varint(len(s))
        self.file.write(s)
    
    def write_pickle(self, obj):
        """Writes a pickled representation of obj to the wrapped file.
        """
        dump_pickle(obj, self.file, -1)
    
    def write_marshal(self, obj):
        dump_marshal(obj, self.file)
    
    def write_8bitfloat(self, f, mantissabits = 5, zeroexp = 2):
        """Writes a byte-sized representation of floating point value
        f to the wrapped file.
        mantissabits is the number of bits to use for the mantissa
        (with the rest used for the exponent).
        zeroexp is the zero point for the exponent.
        """
        
        self.write_byte(float_to_byte(f, mantissabits, zeroexp))
    
    def write_varint(self, i):
        """Writes a variable-length integer to the wrapped file.
        """
        assert i >= 0
        if i < len(_varint_cache):
            self.file.write(_varint_cache[i])
            return
        s = ""
        while (i & ~0x7F) != 0:
            s += chr((i & 0x7F) | 0x80)
            i = i >> 7
        s += chr(i)
        self.file.write(s)
    
    def write_struct(self, format, data):
        """Writes struct data to the wrapped file.
        """
        self.file.write(pack(format, *data))
    
    def read_byte(self):
        """Reads a single byte value from the wrapped file,
        shortcut for ord(file.read(1)).
        """
        return ord(self.file.read(1))
    
    def read_sbyte(self):
        """Reads a signed byte value from the wrapped file.
        """
        self.sbyte_array.fromstring(self.file.read(1))
        return self.sbyte_array.pop()
    
    def read_int(self):
        """Reads a binary integer value from the wrapped file.
        """
        self.int_array.fromstring(self.file.read(_INT_SIZE))
        return self.int_array.pop()
    
    def read_ushort(self):
        """Reads an unsigned binary short integer value from the wrapped file.
        """
        self.ushort_array.fromstring(self.file.read(_USHORT_SIZE))
        return self.ushort_array.pop()
    
    def read_ulong(self):
        """Reads an unsigned binary integer value from the wrapped file.
        """
        self.ulong_array.fromstring(self.file.read(_ULONG_SIZE))
        return self.ulong_array.pop()
    
    def read_float(self):
        """Reads a binary floating point value from the wrapped file.
        """
        self.float_array.fromstring(self.file.read(_FLOAT_SIZE))
        return self.float_array.pop()
    
    def read_array(self, typecode, length):
        """Reads an array of 'length' items from the wrapped file.
        """
        arry = array(typecode)
        arry.fromstring(self.file.read(arry.itemsize * length))
        return arry
    
    # These variants are faster but only work on built-in "file" objects
    # (not on any file-like object with a read() method). They are swapped in
    # for the methods above when this object is wrapping a real file.
    
    def _read_sbyte(self):
        """Reads a signed byte value from the wrapped file.
        """
        self.sbyte_array.fromfile(self.file, 1)
        return self.sbyte_array.pop()
    def _read_int(self):
        """Reads a binary integer value from the wrapped file.
        """
        self.int_array.fromfile(self.file, 1)
        return self.int_array.pop()
    def _read_ushort(self):
        """Reads an unsigned binary short integer value from the wrapped file.
        """
        self.ushort_array.fromfile(self.file, 1)
        return self.ushort_array.pop()
    def _read_ulong(self):
        """Reads an unsigned binary integer value from the wrapped file.
        """
        self.ulong_array.fromfile(self.file, 1)
        return self.ulong_array.pop()
    def _read_float(self):
        """Reads a binary floating point value from the wrapped file.
        """
        self.float_array.fromfile(self.file, 1)
        return self.float_array.pop()
    def _read_array(self, typecode, length):
        """Reads an array of 'length' items from the wrapped file.
        """
        arry = array(typecode)
        arry.fromfile(self.file, length)
        return arry
    
    def read_string(self):
        """Reads a string from the wrapped file.
        """
        return self.file.read(self.read_varint())
    
    def skip_string(self):
        """Skips a string value by seeking past it.
        """
        length = self.read_varint()
        self.file.seek(length, 1)
    
    def read_pickle(self):
        """Reads a pickled object from the wrapped file.
        """
        return load_pickle(self.file)
    
    def read_marshal(self):
        return load_marshal(self.file)
    
    def read_8bitfloat(self, mantissabits = 5, zeroexp = 2):
        """Reads a byte-sized representation of a floating point value.
        mantissabits is the number of bits to use for the mantissa
        (with the rest used for the exponent).
        zeroexp is the zero point for the exponent.
        """
        return byte_to_float(self.read_byte(), mantissabits, zeroexp)
    
    def read_varint(self):
        """Reads a variable-length encoded integer from the wrapped
        file.
        """
        read = self.read_byte
        b = read()
        i = b & 0x7F

        shift = 7
        while b & 0x80 != 0:
            b = read()
            i |= (b & 0x7F) << shift
            shift += 7
        return i
    
    def read_struct(self, format):
        """Reads a struct from the wrapped file.
        """
        length = calcsize(format)
        return unpack(format, self.file.read(length))
    
    def flush(self):
        """Flushes the buffer of the wrapped file. This is a no-op
        if the wrapped file does not have a flush method.
        """
        if hasattr(self.file, "flush"):
            self.file.flush()
    
    def close(self):
        """Closes the wrapped file. This is a no-op
        if the wrapped file does not have a close method.
        """
        if self.onclose:
            self.onclose(self)
        if hasattr(self.file, "close"):
            self.file.close()
        self.is_closed = True
        

if __name__ == '__main__':
    x = 0.0
    for i in xrange(0, 200):
        x += 0.25
        print x, byte_to_float(float_to_byte(x))

########NEW FILE########
__FILENAME__ = bitvector
import operator
from array import array

# Table of the number of '1' bits in each byte (0-255)
BYTE_COUNTS = array('B',[
    0, 1, 1, 2, 1, 2, 2, 3, 1, 2, 2, 3, 2, 3, 3, 4,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
    4, 5, 5, 6, 5, 6, 6, 7, 5, 6, 6, 7, 6, 7, 7, 8])


class BitVector(object):
    def __init__(self, size, bits = None, source = None):
        self.size = size
        
        if bits:
            self.bits = bits
        else:
            self.bits = array("B", ([0x00] * ((size >> 3) + 1)))
        
        if source:
            for num in source:
                self.set(num)
        
        self.bcount = None
        
    def __len__(self):
        return self.size
    
    def __contains__(self, index):
        return self[index]
    
    def __iter__(self):
        get = self.__getitem__
        for i in xrange(0, self.size):
            if get(i):
                yield i
    
    def __repr__(self):
        return "<BitVector %s>" % self.__str__()
    
    def __str__(self):
        get = self.__getitem__
        return "".join("1" if get(i) else "0"
                       for i in xrange(0, self.size)) 
    
    def __getitem__(self, index):
        return self.bits[index >> 3] & (1 << (index & 7)) != 0
    
    def __setitem__(self, index, value):
        if value:
            self.set(index)
        else:
            self.clear(index)
    
    def _logic(self, op, bitv):
        if self.size != bitv.size:
            raise ValueError("Can't combine bitvectors of different sizes")
        res = BitVector(size = self.size )
        lpb = map(op, self.bits, bitv.bits)
        res.bits = array('B', lpb )
        return res
    
    def __and__(self, bitv):
        return self._logic(operator.__and__, bitv)
    
    def __or__(self, bitv):
        return self._logic(operator.__or__, bitv)
    
    def __xor__(self, bitv):
        return self._logic(operator.__xor__, bitv)
    
    def count(self):
        if self.bcount is None:
            c = 0
            for b in self.bits:
                c += BYTE_COUNTS[b & 0xFF]
            
            self.bcount = c
        return self.bcount
    
    def set(self, index):
        self.bits[index >> 3] |= 1 << (index & 7)
        self.bcount = None
        
    def clear(self, index):
        self.bits[index >> 3] &= ~(1 << (index & 7))
        self.bcount = None
        
    def copy(self):
        return BitVector(self.size, bits = self.bits)


if __name__ == "__main__":
    b = BitVector(10)
    b.set(1)
    b.set(9)
    b.set(5)
    print b
    print b[2]
    print b[5]
    b.clear(5)
    print b[5]
    print b
    
    c = BitVector(10)
    c.set(1)
    c.set(5)
    print " ", b
    print "^", c
    print "=", b ^ c

########NEW FILE########
__FILENAME__ = levenshtein
def relative(a, b):
    """
    Computes a relative distance between two strings. Its in the range
    [0-1] where 1 means total equality.
    """
    d = distance(a,b)
    longer = float(max((len(a), len(b))))
    shorter = float(min((len(a), len(b))))    
    r = ((longer - d) / longer) * (shorter / longer)
    return r

def distance(s, t):
    m, n = len(s), len(t)
    d = [range(n+1)]
    d += [[i] for i in range(1,m+1)]
    for i in range(0,m):
        for j in range(0,n):
            cost = 1
            if s[i] == t[j]: cost = 0
            d[i+1].append(min(d[i][j+1]+1,  # deletion
                              d[i+1][j]+1,  # insertion
                              d[i][j]+cost) # substitution
                         )
    return d[m][n]


########NEW FILE########
__FILENAME__ = pyparsing
# module pyparsing.py
#
# Copyright (c) 2003-2008  Paul T. McGuire
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
#from __future__ import generators

__doc__ = \
"""
pyparsing module - Classes and methods to define and execute parsing grammars

The pyparsing module is an alternative approach to creating and executing simple grammars,
vs. the traditional lex/yacc approach, or the use of regular expressions.  With pyparsing, you
don't need to learn a new syntax for defining grammars or matching expressions - the parsing module
provides a library of classes that you use to construct the grammar directly in Python.

Here is a program to parse "Hello, World!" (or any greeting of the form "<salutation>, <addressee>!")::

    from pyparsing import Word, alphas

    # define grammar of a greeting
    greet = Word( alphas ) + "," + Word( alphas ) + "!"

    hello = "Hello, World!"
    print hello, "->", greet.parseString( hello )

The program outputs the following::

    Hello, World! -> ['Hello', ',', 'World', '!']

The Python representation of the grammar is quite readable, owing to the self-explanatory
class names, and the use of '+', '|' and '^' operators.

The parsed results returned from parseString() can be accessed as a nested list, a dictionary, or an
object with named attributes.

The pyparsing module handles some of the problems that are typically vexing when writing text parsers:
 - extra or missing whitespace (the above program will also handle "Hello,World!", "Hello  ,  World  !", etc.)
 - quoted strings
 - embedded comments
"""

__version__ = "1.5.1"
__versionTime__ = "2 October 2008 00:44"
__author__ = "Paul McGuire <ptmcg@users.sourceforge.net>"

import string
from weakref import ref as wkref
import copy
import sys
import warnings
import re
import sre_constants
#~ sys.stderr.write( "testing pyparsing module, version %s, %s\n" % (__version__,__versionTime__ ) )

__all__ = [
'And', 'CaselessKeyword', 'CaselessLiteral', 'CharsNotIn', 'Combine', 'Dict', 'Each', 'Empty',
'FollowedBy', 'Forward', 'GoToColumn', 'Group', 'Keyword', 'LineEnd', 'LineStart', 'Literal',
'MatchFirst', 'NoMatch', 'NotAny', 'OneOrMore', 'OnlyOnce', 'Optional', 'Or',
'ParseBaseException', 'ParseElementEnhance', 'ParseException', 'ParseExpression', 'ParseFatalException',
'ParseResults', 'ParseSyntaxException', 'ParserElement', 'QuotedString', 'RecursiveGrammarException',
'Regex', 'SkipTo', 'StringEnd', 'StringStart', 'Suppress', 'Token', 'TokenConverter', 'Upcase',
'White', 'Word', 'WordEnd', 'WordStart', 'ZeroOrMore',
'alphanums', 'alphas', 'alphas8bit', 'anyCloseTag', 'anyOpenTag', 'cStyleComment', 'col',
'commaSeparatedList', 'commonHTMLEntity', 'countedArray', 'cppStyleComment', 'dblQuotedString',
'dblSlashComment', 'delimitedList', 'dictOf', 'downcaseTokens', 'empty', 'getTokensEndLoc', 'hexnums',
'htmlComment', 'javaStyleComment', 'keepOriginalText', 'line', 'lineEnd', 'lineStart', 'lineno',
'makeHTMLTags', 'makeXMLTags', 'matchOnlyAtCol', 'matchPreviousExpr', 'matchPreviousLiteral',
'nestedExpr', 'nullDebugAction', 'nums', 'oneOf', 'opAssoc', 'operatorPrecedence', 'printables',
'punc8bit', 'pythonStyleComment', 'quotedString', 'removeQuotes', 'replaceHTMLEntity', 
'replaceWith', 'restOfLine', 'sglQuotedString', 'srange', 'stringEnd',
'stringStart', 'traceParseAction', 'unicodeString', 'upcaseTokens', 'withAttribute',
'indentedBlock', 'originalTextFor',
]


"""
Detect if we are running version 3.X and make appropriate changes
Robert A. Clark
"""
if sys.version_info[0] > 2:
    _PY3K = True
    _MAX_INT = sys.maxsize
    basestring = str
else:
    _PY3K = False
    _MAX_INT = sys.maxint

if not _PY3K:
    def _ustr(obj):
        """Drop-in replacement for str(obj) that tries to be Unicode friendly. It first tries
           str(obj). If that fails with a UnicodeEncodeError, then it tries unicode(obj). It
           then < returns the unicode object | encodes it with the default encoding | ... >.
        """
        try:
            # If this works, then _ustr(obj) has the same behaviour as str(obj), so
            # it won't break any existing code.
            return str(obj)

        except UnicodeEncodeError:
            # The Python docs (http://docs.python.org/ref/customization.html#l2h-182)
            # state that "The return value must be a string object". However, does a
            # unicode object (being a subclass of basestring) count as a "string
            # object"?
            # If so, then return a unicode object:
            return unicode(obj)
            # Else encode it... but how? There are many choices... :)
            # Replace unprintables with escape codes?
            #return unicode(obj).encode(sys.getdefaultencoding(), 'backslashreplace_errors')
            # Replace unprintables with question marks?
            #return unicode(obj).encode(sys.getdefaultencoding(), 'replace')
            # ...
else:
    _ustr = str
    unichr = chr

def _str2dict(strg):
    return dict( [(c,0) for c in strg] )
    #~ return set( [c for c in strg] )

def _xml_escape(data):
    """Escape &, <, >, ", ', etc. in a string of data."""

    # ampersand must be replaced first
    from_symbols = '&><"\''
    to_symbols = ['&'+s+';' for s in "amp gt lt quot apos".split()]
    for from_,to_ in zip(from_symbols, to_symbols):
        data = data.replace(from_, to_)
    return data

class _Constants(object):
    pass

if not _PY3K:
    alphas     = string.lowercase + string.uppercase
else:
    alphas     = string.ascii_lowercase + string.ascii_uppercase
nums       = string.digits
hexnums    = nums + "ABCDEFabcdef"
alphanums  = alphas + nums
_bslash = chr(92)
printables = "".join( [ c for c in string.printable if c not in string.whitespace ] )

class ParseBaseException(Exception):
    """base exception class for all parsing runtime exceptions"""
    __slots__ = ( "loc","msg","pstr","parserElement" )
    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, pstr, loc=0, msg=None, elem=None ):
        self.loc = loc
        if msg is None:
            self.msg = pstr
            self.pstr = ""
        else:
            self.msg = msg
            self.pstr = pstr
        self.parserElement = elem

    def __getattr__( self, aname ):
        """supported attributes by name are:
            - lineno - returns the line number of the exception text
            - col - returns the column number of the exception text
            - line - returns the line containing the exception text
        """
        if( aname == "lineno" ):
            return lineno( self.loc, self.pstr )
        elif( aname in ("col", "column") ):
            return col( self.loc, self.pstr )
        elif( aname == "line" ):
            return line( self.loc, self.pstr )
        else:
            raise AttributeError(aname)

    def __str__( self ):
        return "%s (at char %d), (line:%d, col:%d)" % \
                ( self.msg, self.loc, self.lineno, self.column )
    def __repr__( self ):
        return _ustr(self)
    def markInputline( self, markerString = ">!<" ):
        """Extracts the exception line from the input string, and marks
           the location of the exception with a special symbol.
        """
        line_str = self.line
        line_column = self.column - 1
        if markerString:
            line_str = "".join( [line_str[:line_column],
                                markerString, line_str[line_column:]])
        return line_str.strip()
    def __dir__(self):
        return "loc msg pstr parserElement lineno col line " \
               "markInputLine __str__ __repr__".split()

class ParseException(ParseBaseException):
    """exception thrown when parse expressions don't match class;
       supported attributes by name are:
        - lineno - returns the line number of the exception text
        - col - returns the column number of the exception text
        - line - returns the line containing the exception text
    """
    pass

class ParseFatalException(ParseBaseException):
    """user-throwable exception thrown when inconsistent parse content
       is found; stops all parsing immediately"""
    pass

class ParseSyntaxException(ParseFatalException):
    """just like ParseFatalException, but thrown internally when an
       ErrorStop indicates that parsing is to stop immediately because
       an unbacktrackable syntax error has been found"""
    def __init__(self, pe):
        super(ParseSyntaxException, self).__init__(
                                    pe.pstr, pe.loc, pe.msg, pe.parserElement)

#~ class ReparseException(ParseBaseException):
    #~ """Experimental class - parse actions can raise this exception to cause
       #~ pyparsing to reparse the input string:
        #~ - with a modified input string, and/or
        #~ - with a modified start location
       #~ Set the values of the ReparseException in the constructor, and raise the
       #~ exception in a parse action to cause pyparsing to use the new string/location.
       #~ Setting the values as None causes no change to be made.
       #~ """
    #~ def __init_( self, newstring, restartLoc ):
        #~ self.newParseText = newstring
        #~ self.reparseLoc = restartLoc

class RecursiveGrammarException(Exception):
    """exception thrown by validate() if the grammar could be improperly recursive"""
    def __init__( self, parseElementList ):
        self.parseElementTrace = parseElementList

    def __str__( self ):
        return "RecursiveGrammarException: %s" % self.parseElementTrace

class _ParseResultsWithOffset(object):
    def __init__(self,p1,p2):
        self.tup = (p1,p2)
    def __getitem__(self,i):
        return self.tup[i]
    def __repr__(self):
        return repr(self.tup)
    def setOffset(self,i):
        self.tup = (self.tup[0],i)

class ParseResults(object):
    """Structured parse results, to provide multiple means of access to the parsed data:
       - as a list (len(results))
       - by list index (results[0], results[1], etc.)
       - by attribute (results.<resultsName>)
       """
    __slots__ = ( "__toklist", "__tokdict", "__doinit", "__name", "__parent", "__accumNames", "__weakref__" )
    def __new__(cls, toklist, name=None, asList=True, modal=True ):
        if isinstance(toklist, cls):
            return toklist
        retobj = object.__new__(cls)
        retobj.__doinit = True
        return retobj

    # Performance tuning: we construct a *lot* of these, so keep this
    # constructor as small and fast as possible
    def __init__( self, toklist, name=None, asList=True, modal=True ):
        if self.__doinit:
            self.__doinit = False
            self.__name = None
            self.__parent = None
            self.__accumNames = {}
            if isinstance(toklist, list):
                self.__toklist = toklist[:]
            else:
                self.__toklist = [toklist]
            self.__tokdict = dict()

        if name:
            if not modal:
                self.__accumNames[name] = 0
            if isinstance(name,int):
                name = _ustr(name) # will always return a str, but use _ustr for consistency
            self.__name = name
            if not toklist in (None,'',[]):
                if isinstance(toklist,basestring):
                    toklist = [ toklist ]
                if asList:
                    if isinstance(toklist,ParseResults):
                        self[name] = _ParseResultsWithOffset(toklist.copy(),0)
                    else:
                        self[name] = _ParseResultsWithOffset(ParseResults(toklist[0]),0)
                    self[name].__name = name
                else:
                    try:
                        self[name] = toklist[0]
                    except (KeyError,TypeError):
                        self[name] = toklist

    def __getitem__( self, i ):
        if isinstance( i, (int,slice) ):
            return self.__toklist[i]
        else:
            if i not in self.__accumNames:
                return self.__tokdict[i][-1][0]
            else:
                return ParseResults([ v[0] for v in self.__tokdict[i] ])

    def __setitem__( self, k, v ):
        if isinstance(v,_ParseResultsWithOffset):
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [v]
            sub = v[0]
        elif isinstance(k,int):
            self.__toklist[k] = v
            sub = v
        else:
            self.__tokdict[k] = self.__tokdict.get(k,list()) + [_ParseResultsWithOffset(v,0)]
            sub = v
        if isinstance(sub,ParseResults):
            sub.__parent = wkref(self)

    def __delitem__( self, i ):
        if isinstance(i,(int,slice)):
            mylen = len( self.__toklist )
            del self.__toklist[i]

            # convert int to slice
            if isinstance(i, int):
                if i < 0:
                    i += mylen
                i = slice(i, i+1)
            # get removed indices
            removed = list(range(*i.indices(mylen)))
            removed.reverse()
            # fixup indices in token dictionary
            for name in self.__tokdict:
                occurrences = self.__tokdict[name]
                for j in removed:
                    for k, (value, position) in enumerate(occurrences):
                        occurrences[k] = _ParseResultsWithOffset(value, position - (position > j))
        else:
            del self.__tokdict[i]

    def __contains__( self, k ):
        return k in self.__tokdict

    def __len__( self ): return len( self.__toklist )
    def __bool__(self): return len( self.__toklist ) > 0
    __nonzero__ = __bool__
    def __iter__( self ): return iter( self.__toklist )
    def __reversed__( self ): return iter( reversed(self.__toklist) )
    def keys( self ):
        """Returns all named result keys."""
        return self.__tokdict.keys()

    def pop( self, index=-1 ):
        """Removes and returns item at specified index (default=last).
           Will work with either numeric indices or dict-key indicies."""
        ret = self[index]
        del self[index]
        return ret

    def get(self, key, defaultValue=None):
        """Returns named result matching the given key, or if there is no
           such name, then returns the given defaultValue or None if no
           defaultValue is specified."""
        if key in self:
            return self[key]
        else:
            return defaultValue

    def insert( self, index, insStr ):
        self.__toklist.insert(index, insStr)
        # fixup indices in token dictionary
        for name in self.__tokdict:
            occurrences = self.__tokdict[name]
            for k, (value, position) in enumerate(occurrences):
                occurrences[k] = _ParseResultsWithOffset(value, position + (position > index))

    def items( self ):
        """Returns all named result keys and values as a list of tuples."""
        return [(k,self[k]) for k in self.__tokdict]

    def values( self ):
        """Returns all named result values."""
        return [ v[-1][0] for v in self.__tokdict.values() ]

    def __getattr__( self, name ):
        if name not in self.__slots__:
            if name in self.__tokdict:
                if name not in self.__accumNames:
                    return self.__tokdict[name][-1][0]
                else:
                    return ParseResults([ v[0] for v in self.__tokdict[name] ])
            else:
                return ""
        return None

    def __add__( self, other ):
        ret = self.copy()
        ret += other
        return ret

    def __iadd__( self, other ):
        if other.__tokdict:
            offset = len(self.__toklist)
            addoffset = ( lambda a: (a<0 and offset) or (a+offset) )
            otheritems = other.__tokdict.items()
            otherdictitems = [(k, _ParseResultsWithOffset(v[0],addoffset(v[1])) )
                                for (k,vlist) in otheritems for v in vlist]
            for k,v in otherdictitems:
                self[k] = v
                if isinstance(v[0],ParseResults):
                    v[0].__parent = wkref(self)
            
        self.__toklist += other.__toklist
        self.__accumNames.update( other.__accumNames )
        del other
        return self

    def __repr__( self ):
        return "(%s, %s)" % ( repr( self.__toklist ), repr( self.__tokdict ) )

    def __str__( self ):
        out = "["
        sep = ""
        for i in self.__toklist:
            if isinstance(i, ParseResults):
                out += sep + _ustr(i)
            else:
                out += sep + repr(i)
            sep = ", "
        out += "]"
        return out

    def _asStringList( self, sep='' ):
        out = []
        for item in self.__toklist:
            if out and sep:
                out.append(sep)
            if isinstance( item, ParseResults ):
                out += item._asStringList()
            else:
                out.append( _ustr(item) )
        return out

    def asList( self ):
        """Returns the parse results as a nested list of matching tokens, all converted to strings."""
        out = []
        for res in self.__toklist:
            if isinstance(res,ParseResults):
                out.append( res.asList() )
            else:
                out.append( res )
        return out

    def asDict( self ):
        """Returns the named parse results as dictionary."""
        return dict( self.items() )

    def copy( self ):
        """Returns a new copy of a ParseResults object."""
        ret = ParseResults( self.__toklist )
        ret.__tokdict = self.__tokdict.copy()
        ret.__parent = self.__parent
        ret.__accumNames.update( self.__accumNames )
        ret.__name = self.__name
        return ret

    def asXML( self, doctag=None, namedItemsOnly=False, indent="", formatted=True ):
        """Returns the parse results as XML. Tags are created for tokens and lists that have defined results names."""
        nl = "\n"
        out = []
        namedItems = dict( [ (v[1],k) for (k,vlist) in self.__tokdict.items()
                                                            for v in vlist ] )
        nextLevelIndent = indent + "  "

        # collapse out indents if formatting is not desired
        if not formatted:
            indent = ""
            nextLevelIndent = ""
            nl = ""

        selfTag = None
        if doctag is not None:
            selfTag = doctag
        else:
            if self.__name:
                selfTag = self.__name

        if not selfTag:
            if namedItemsOnly:
                return ""
            else:
                selfTag = "ITEM"

        out += [ nl, indent, "<", selfTag, ">" ]

        worklist = self.__toklist
        for i,res in enumerate(worklist):
            if isinstance(res,ParseResults):
                if i in namedItems:
                    out += [ res.asXML(namedItems[i],
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
                else:
                    out += [ res.asXML(None,
                                        namedItemsOnly and doctag is None,
                                        nextLevelIndent,
                                        formatted)]
            else:
                # individual token, see if there is a name for it
                resTag = None
                if i in namedItems:
                    resTag = namedItems[i]
                if not resTag:
                    if namedItemsOnly:
                        continue
                    else:
                        resTag = "ITEM"
                xmlBodyText = _xml_escape(_ustr(res))
                out += [ nl, nextLevelIndent, "<", resTag, ">",
                                                xmlBodyText,
                                                "</", resTag, ">" ]

        out += [ nl, indent, "</", selfTag, ">" ]
        return "".join(out)

    def __lookup(self,sub):
        for k,vlist in self.__tokdict.items():
            for v,loc in vlist:
                if sub is v:
                    return k
        return None

    def getName(self):
        """Returns the results name for this token expression."""
        if self.__name:
            return self.__name
        elif self.__parent:
            par = self.__parent()
            if par:
                return par.__lookup(self)
            else:
                return None
        elif (len(self) == 1 and
               len(self.__tokdict) == 1 and
               self.__tokdict.values()[0][0][1] in (0,-1)):
            return self.__tokdict.keys()[0]
        else:
            return None

    def dump(self,indent='',depth=0):
        """Diagnostic method for listing out the contents of a ParseResults.
           Accepts an optional indent argument so that this string can be embedded
           in a nested display of other data."""
        out = []
        out.append( indent+_ustr(self.asList()) )
        keys = self.items()
        keys.sort()
        for k,v in keys:
            if out:
                out.append('\n')
            out.append( "%s%s- %s: " % (indent,('  '*depth), k) )
            if isinstance(v,ParseResults):
                if v.keys():
                    #~ out.append('\n')
                    out.append( v.dump(indent,depth+1) )
                    #~ out.append('\n')
                else:
                    out.append(_ustr(v))
            else:
                out.append(_ustr(v))
        #~ out.append('\n')
        return "".join(out)

    # add support for pickle protocol
    def __getstate__(self):
        return ( self.__toklist,
                 ( self.__tokdict.copy(),
                   self.__parent is not None and self.__parent() or None,
                   self.__accumNames,
                   self.__name ) )

    def __setstate__(self,state):
        self.__toklist = state[0]
        self.__tokdict, \
        par, \
        inAccumNames, \
        self.__name = state[1]
        self.__accumNames = {}
        self.__accumNames.update(inAccumNames)
        if par is not None:
            self.__parent = wkref(par)
        else:
            self.__parent = None

    def __dir__(self):
        return dir(super(ParseResults,self)) + self.keys()

def col (loc,strg):
    """Returns current column within a string, counting newlines as line separators.
   The first column is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See L{I{ParserElement.parseString}<ParserElement.parseString>} for more information
   on parsing strings containing <TAB>s, and suggested methods to maintain a
   consistent view of the parsed string, the parse location, and line and column
   positions within the parsed string.
   """
    return (loc<len(strg) and strg[loc] == '\n') and 1 or loc - strg.rfind("\n", 0, loc)

def lineno(loc,strg):
    """Returns current line number within a string, counting newlines as line separators.
   The first line is number 1.

   Note: the default parsing behavior is to expand tabs in the input string
   before starting the parsing process.  See L{I{ParserElement.parseString}<ParserElement.parseString>} for more information
   on parsing strings containing <TAB>s, and suggested methods to maintain a
   consistent view of the parsed string, the parse location, and line and column
   positions within the parsed string.
   """
    return strg.count("\n",0,loc) + 1

def line( loc, strg ):
    """Returns the line of text containing loc within a string, counting newlines as line separators.
       """
    lastCR = strg.rfind("\n", 0, loc)
    nextCR = strg.find("\n", loc)
    if nextCR > 0:
        return strg[lastCR+1:nextCR]
    else:
        return strg[lastCR+1:]

def _defaultStartDebugAction( instring, loc, expr ):
    print ("Match " + _ustr(expr) + " at loc " + _ustr(loc) + "(%d,%d)" % ( lineno(loc,instring), col(loc,instring) ))

def _defaultSuccessDebugAction( instring, startloc, endloc, expr, toks ):
    print ("Matched " + _ustr(expr) + " -> " + str(toks.asList()))

def _defaultExceptionDebugAction( instring, loc, expr, exc ):
    print ("Exception raised:" + _ustr(exc))

def nullDebugAction(*args):
    """'Do-nothing' debug action, to suppress debugging output during parsing."""
    pass

class ParserElement(object):
    """Abstract base level parser element class."""
    DEFAULT_WHITE_CHARS = " \n\t\r"

    def setDefaultWhitespaceChars( chars ):
        """Overrides the default whitespace chars
        """
        ParserElement.DEFAULT_WHITE_CHARS = chars
    setDefaultWhitespaceChars = staticmethod(setDefaultWhitespaceChars)

    def __init__( self, savelist=False ):
        self.parseAction = list()
        self.failAction = None
        #~ self.name = "<unknown>"  # don't define self.name, let subclasses try/except upcall
        self.strRepr = None
        self.resultsName = None
        self.saveAsList = savelist
        self.skipWhitespace = True
        self.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        self.copyDefaultWhiteChars = True
        self.mayReturnEmpty = False # used when checking for left-recursion
        self.keepTabs = False
        self.ignoreExprs = list()
        self.debug = False
        self.streamlined = False
        self.mayIndexError = True # used to optimize exception handling for subclasses that don't advance parse index
        self.errmsg = ""
        self.modalResults = True # used to mark results names as modal (report only last) or cumulative (list all)
        self.debugActions = ( None, None, None ) #custom debug actions
        self.re = None
        self.callPreparse = True # used to avoid redundant calls to preParse
        self.callDuringTry = False

    def copy( self ):
        """Make a copy of this ParserElement.  Useful for defining different parse actions
           for the same parsing pattern, using copies of the original parse element."""
        cpy = copy.copy( self )
        cpy.parseAction = self.parseAction[:]
        cpy.ignoreExprs = self.ignoreExprs[:]
        if self.copyDefaultWhiteChars:
            cpy.whiteChars = ParserElement.DEFAULT_WHITE_CHARS
        return cpy

    def setName( self, name ):
        """Define name for this expression, for use in debugging."""
        self.name = name
        self.errmsg = "Expected " + self.name
        if hasattr(self,"exception"):
            self.exception.msg = self.errmsg
        return self

    def setResultsName( self, name, listAllMatches=False ):
        """Define name for referencing matching tokens as a nested attribute
           of the returned parse results.
           NOTE: this returns a *copy* of the original ParserElement object;
           this is so that the client can define a basic element, such as an
           integer, and reference it in multiple places with different names.
        """
        newself = self.copy()
        newself.resultsName = name
        newself.modalResults = not listAllMatches
        return newself

    def setBreak(self,breakFlag = True):
        """Method to invoke the Python pdb debugger when this element is
           about to be parsed. Set breakFlag to True to enable, False to
           disable.
        """
        if breakFlag:
            _parseMethod = self._parse
            def breaker(instring, loc, doActions=True, callPreParse=True):
                import pdb
                pdb.set_trace()
                return _parseMethod( instring, loc, doActions, callPreParse )
            breaker._originalParseMethod = _parseMethod
            self._parse = breaker
        else:
            if hasattr(self._parse,"_originalParseMethod"):
                self._parse = self._parse._originalParseMethod
        return self

    def _normalizeParseActionArgs( f ):
        """Internal method used to decorate parse actions that take fewer than 3 arguments,
           so that all parse actions can be called as f(s,l,t)."""
        STAR_ARGS = 4

        try:
            restore = None
            if isinstance(f,type):
                restore = f
                f = f.__init__
            if not _PY3K:
                codeObj = f.func_code
            else:
                codeObj = f.code
            if codeObj.co_flags & STAR_ARGS:
                return f
            numargs = codeObj.co_argcount
            if not _PY3K:
                if hasattr(f,"im_self"):
                    numargs -= 1
            else:
                if hasattr(f,"__self__"):
                    numargs -= 1
            if restore:
                f = restore
        except AttributeError:
            try:
                if not _PY3K:
                    call_im_func_code = f.__call__.im_func.func_code
                else:
                    call_im_func_code = f.__code__

                # not a function, must be a callable object, get info from the
                # im_func binding of its bound __call__ method
                if call_im_func_code.co_flags & STAR_ARGS:
                    return f
                numargs = call_im_func_code.co_argcount
                if not _PY3K:
                    if hasattr(f.__call__,"im_self"):
                        numargs -= 1
                else:
                    if hasattr(f.__call__,"__self__"):
                        numargs -= 0
            except AttributeError:
                if not _PY3K:
                    call_func_code = f.__call__.func_code
                else:
                    call_func_code = f.__call__.__code__
                # not a bound method, get info directly from __call__ method
                if call_func_code.co_flags & STAR_ARGS:
                    return f
                numargs = call_func_code.co_argcount
                if not _PY3K:
                    if hasattr(f.__call__,"im_self"):
                        numargs -= 1
                else:
                    if hasattr(f.__call__,"__self__"):
                        numargs -= 1


        #~ print ("adding function %s with %d args" % (f.func_name,numargs))
        if numargs == 3:
            return f
        else:
            if numargs > 3:
                def tmp(s,l,t):
                    return f(f.__call__.__self__, s,l,t)
            if numargs == 2:
                def tmp(s,l,t):
                    return f(l,t)
            elif numargs == 1:
                def tmp(s,l,t):
                    return f(t)
            else: #~ numargs == 0:
                def tmp(s,l,t):
                    return f()
            try:
                tmp.__name__ = f.__name__
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            try:
                tmp.__doc__ = f.__doc__
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            try:
                tmp.__dict__.update(f.__dict__)
            except (AttributeError,TypeError):
                # no need for special handling if attribute doesnt exist
                pass
            return tmp
    _normalizeParseActionArgs = staticmethod(_normalizeParseActionArgs)

    def setParseAction( self, *fns, **kwargs ):
        """Define action to perform when successfully matching parse element definition.
           Parse action fn is a callable method with 0-3 arguments, called as fn(s,loc,toks),
           fn(loc,toks), fn(toks), or just fn(), where:
            - s   = the original string being parsed (see note below)
            - loc = the location of the matching substring
            - toks = a list of the matched tokens, packaged as a ParseResults object
           If the functions in fns modify the tokens, they can return them as the return
           value from fn, and the modified list of tokens will replace the original.
           Otherwise, fn does not need to return any value.

           Note: the default parsing behavior is to expand tabs in the input string
           before starting the parsing process.  See L{I{parseString}<parseString>} for more information
           on parsing strings containing <TAB>s, and suggested methods to maintain a
           consistent view of the parsed string, the parse location, and line and column
           positions within the parsed string.
           """
        self.parseAction = list(map(self._normalizeParseActionArgs, list(fns)))
        self.callDuringTry = ("callDuringTry" in kwargs and kwargs["callDuringTry"])
        return self

    def addParseAction( self, *fns, **kwargs ):
        """Add parse action to expression's list of parse actions. See L{I{setParseAction}<setParseAction>}."""
        self.parseAction += list(map(self._normalizeParseActionArgs, list(fns)))
        self.callDuringTry = self.callDuringTry or ("callDuringTry" in kwargs and kwargs["callDuringTry"])
        return self

    def setFailAction( self, fn ):
        """Define action to perform if parsing fails at this expression.
           Fail acton fn is a callable function that takes the arguments
           fn(s,loc,expr,err) where:
            - s = string being parsed
            - loc = location where expression match was attempted and failed
            - expr = the parse expression that failed
            - err = the exception thrown
           The function returns no value.  It may throw ParseFatalException
           if it is desired to stop parsing immediately."""
        self.failAction = fn
        return self

    def _skipIgnorables( self, instring, loc ):
        exprsFound = True
        while exprsFound:
            exprsFound = False
            for e in self.ignoreExprs:
                try:
                    while 1:
                        loc,dummy = e._parse( instring, loc )
                        exprsFound = True
                except ParseException:
                    pass
        return loc

    def preParse( self, instring, loc ):
        if self.ignoreExprs:
            loc = self._skipIgnorables( instring, loc )

        if self.skipWhitespace:
            wt = self.whiteChars
            instrlen = len(instring)
            while loc < instrlen and instring[loc] in wt:
                loc += 1

        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        return loc, []

    def postParse( self, instring, loc, tokenlist ):
        return tokenlist

    #~ @profile
    def _parseNoCache( self, instring, loc, doActions=True, callPreParse=True ):
        debugging = ( self.debug ) #and doActions )

        if debugging or self.failAction:
            #~ print ("Match",self,"at loc",loc,"(%d,%d)" % ( lineno(loc,instring), col(loc,instring) ))
            if (self.debugActions[0] ):
                self.debugActions[0]( instring, loc, self )
            if callPreParse and self.callPreparse:
                preloc = self.preParse( instring, loc )
            else:
                preloc = loc
            tokensStart = loc
            try:
                try:
                    loc,tokens = self.parseImpl( instring, preloc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            except ParseBaseException, err:
                #~ print ("Exception raised:", err)
                if self.debugActions[2]:
                    self.debugActions[2]( instring, tokensStart, self, err )
                if self.failAction:
                    self.failAction( instring, tokensStart, self, err )
                raise
        else:
            if callPreParse and self.callPreparse:
                preloc = self.preParse( instring, loc )
            else:
                preloc = loc
            tokensStart = loc
            if self.mayIndexError or loc >= len(instring):
                try:
                    loc,tokens = self.parseImpl( instring, preloc, doActions )
                except IndexError:
                    raise ParseException( instring, len(instring), self.errmsg, self )
            else:
                loc,tokens = self.parseImpl( instring, preloc, doActions )

        tokens = self.postParse( instring, loc, tokens )

        retTokens = ParseResults( tokens, self.resultsName, asList=self.saveAsList, modal=self.modalResults )
        if self.parseAction and (doActions or self.callDuringTry):
            if debugging:
                try:
                    for fn in self.parseAction:
                        tokens = fn( instring, tokensStart, retTokens )
                        if tokens is not None:
                            retTokens = ParseResults( tokens,
                                                      self.resultsName,
                                                      asList=self.saveAsList and isinstance(tokens,(ParseResults,list)),
                                                      modal=self.modalResults )
                except ParseBaseException, err:
                    #~ print "Exception raised in user parse action:", err
                    if (self.debugActions[2] ):
                        self.debugActions[2]( instring, tokensStart, self, err )
                    raise
            else:
                for fn in self.parseAction:
                    tokens = fn( instring, tokensStart, retTokens )
                    if tokens is not None:
                        retTokens = ParseResults( tokens,
                                                  self.resultsName,
                                                  asList=self.saveAsList and isinstance(tokens,(ParseResults,list)),
                                                  modal=self.modalResults )

        if debugging:
            #~ print ("Matched",self,"->",retTokens.asList())
            if (self.debugActions[1] ):
                self.debugActions[1]( instring, tokensStart, loc, self, retTokens )

        return loc, retTokens

    def tryParse( self, instring, loc ):
        try:
            return self._parse( instring, loc, doActions=False )[0]
        except ParseFatalException:
            raise ParseException( instring, loc, self.errmsg, self)

    # this method gets repeatedly called during backtracking with the same arguments -
    # we can cache these arguments and save ourselves the trouble of re-parsing the contained expression
    def _parseCache( self, instring, loc, doActions=True, callPreParse=True ):
        lookup = (self,instring,loc,callPreParse,doActions)
        if lookup in ParserElement._exprArgCache:
            value = ParserElement._exprArgCache[ lookup ]
            if isinstance(value,Exception):
                raise value
            return value
        else:
            try:
                value = self._parseNoCache( instring, loc, doActions, callPreParse )
                ParserElement._exprArgCache[ lookup ] = (value[0],value[1].copy())
                return value
            except ParseBaseException, pe:
                ParserElement._exprArgCache[ lookup ] = pe
                raise

    _parse = _parseNoCache

    # argument cache for optimizing repeated calls when backtracking through recursive expressions
    _exprArgCache = {}
    def resetCache():
        ParserElement._exprArgCache.clear()
    resetCache = staticmethod(resetCache)

    _packratEnabled = False
    def enablePackrat():
        """Enables "packrat" parsing, which adds memoizing to the parsing logic.
           Repeated parse attempts at the same string location (which happens
           often in many complex grammars) can immediately return a cached value,
           instead of re-executing parsing/validating code.  Memoizing is done of
           both valid results and parsing exceptions.

           This speedup may break existing programs that use parse actions that
           have side-effects.  For this reason, packrat parsing is disabled when
           you first import pyparsing.  To activate the packrat feature, your
           program must call the class method ParserElement.enablePackrat().  If
           your program uses psyco to "compile as you go", you must call
           enablePackrat before calling psyco.full().  If you do not do this,
           Python will crash.  For best results, call enablePackrat() immediately
           after importing pyparsing.
        """
        if not ParserElement._packratEnabled:
            ParserElement._packratEnabled = True
            ParserElement._parse = ParserElement._parseCache
    enablePackrat = staticmethod(enablePackrat)

    def parseString( self, instring, parseAll=False ):
        """Execute the parse expression with the given string.
           This is the main interface to the client code, once the complete
           expression has been built.

           If you want the grammar to require that the entire input string be
           successfully parsed, then set parseAll to True (equivalent to ending
           the grammar with StringEnd()).

           Note: parseString implicitly calls expandtabs() on the input string,
           in order to report proper column numbers in parse actions.
           If the input string contains tabs and
           the grammar uses parse actions that use the loc argument to index into the
           string being parsed, you can ensure you have a consistent view of the input
           string by:
            - calling parseWithTabs on your grammar before calling parseString
              (see L{I{parseWithTabs}<parseWithTabs>})
            - define your parse action using the full (s,loc,toks) signature, and
              reference the input string using the parse action's s argument
            - explictly expand the tabs in your input string before calling
              parseString
        """
        ParserElement.resetCache()
        if not self.streamlined:
            self.streamline()
            #~ self.saveAsList = True
        for e in self.ignoreExprs:
            e.streamline()
        if not self.keepTabs:
            instring = instring.expandtabs()
        loc, tokens = self._parse( instring, 0 )
        if parseAll:
            loc = self.preParse( instring, loc )
            StringEnd()._parse( instring, loc )
        return tokens

    def scanString( self, instring, maxMatches=_MAX_INT ):
        """Scan the input string for expression matches.  Each match will return the
           matching tokens, start location, and end location.  May be called with optional
           maxMatches argument, to clip scanning after 'n' matches are found.

           Note that the start and end locations are reported relative to the string
           being parsed.  See L{I{parseString}<parseString>} for more information on parsing
           strings with embedded tabs."""
        if not self.streamlined:
            self.streamline()
        for e in self.ignoreExprs:
            e.streamline()

        if not self.keepTabs:
            instring = _ustr(instring).expandtabs()
        instrlen = len(instring)
        loc = 0
        preparseFn = self.preParse
        parseFn = self._parse
        ParserElement.resetCache()
        matches = 0
        while loc <= instrlen and matches < maxMatches:
            try:
                preloc = preparseFn( instring, loc )
                nextLoc,tokens = parseFn( instring, preloc, callPreParse=False )
            except ParseException:
                loc = preloc+1
            else:
                matches += 1
                yield tokens, preloc, nextLoc
                loc = nextLoc

    def transformString( self, instring ):
        """Extension to scanString, to modify matching text with modified tokens that may
           be returned from a parse action.  To use transformString, define a grammar and
           attach a parse action to it that modifies the returned token list.
           Invoking transformString() on a target string will then scan for matches,
           and replace the matched text patterns according to the logic in the parse
           action.  transformString() returns the resulting transformed string."""
        out = []
        lastE = 0
        # force preservation of <TAB>s, to minimize unwanted transformation of string, and to
        # keep string locs straight between transformString and scanString
        self.keepTabs = True
        for t,s,e in self.scanString( instring ):
            out.append( instring[lastE:s] )
            if t:
                if isinstance(t,ParseResults):
                    out += t.asList()
                elif isinstance(t,list):
                    out += t
                else:
                    out.append(t)
            lastE = e
        out.append(instring[lastE:])
        return "".join(map(_ustr,out))

    def searchString( self, instring, maxMatches=_MAX_INT ):
        """Another extension to scanString, simplifying the access to the tokens found
           to match the given parse expression.  May be called with optional
           maxMatches argument, to clip searching after 'n' matches are found.
        """
        return ParseResults([ t for t,s,e in self.scanString( instring, maxMatches ) ])

    def __add__(self, other ):
        """Implementation of + operator - returns And"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return And( [ self, other ] )

    def __radd__(self, other ):
        """Implementation of + operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other + self

    def __sub__(self, other):
        """Implementation of - operator, returns And with error stop"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return And( [ self, And._ErrorStop(), other ] )

    def __rsub__(self, other ):
        """Implementation of - operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other - self

    def __mul__(self,other):
        if isinstance(other,int):
            minElements, optElements = other,0
        elif isinstance(other,tuple):
            other = (other + (None, None))[:2]
            if other[0] is None:
                other = (0, other[1])
            if isinstance(other[0],int) and other[1] is None:
                if other[0] == 0:
                    return ZeroOrMore(self)
                if other[0] == 1:
                    return OneOrMore(self)
                else:
                    return self*other[0] + ZeroOrMore(self)
            elif isinstance(other[0],int) and isinstance(other[1],int):
                minElements, optElements = other
                optElements -= minElements
            else:
                raise TypeError("cannot multiply 'ParserElement' and ('%s','%s') objects", type(other[0]),type(other[1]))
        else:
            raise TypeError("cannot multiply 'ParserElement' and '%s' objects", type(other))

        if minElements < 0:
            raise ValueError("cannot multiply ParserElement by negative value")
        if optElements < 0:
            raise ValueError("second tuple value must be greater or equal to first tuple value")
        if minElements == optElements == 0:
            raise ValueError("cannot multiply ParserElement by 0 or (0,0)")

        if (optElements):
            def makeOptionalList(n):
                if n>1:
                    return Optional(self + makeOptionalList(n-1))
                else:
                    return Optional(self)
            if minElements:
                if minElements == 1:
                    ret = self + makeOptionalList(optElements)
                else:
                    ret = And([self]*minElements) + makeOptionalList(optElements)
            else:
                ret = makeOptionalList(optElements)
        else:
            if minElements == 1:
                ret = self
            else:
                ret = And([self]*minElements)
        return ret

    def __rmul__(self, other):
        return self.__mul__(other)

    def __or__(self, other ):
        """Implementation of | operator - returns MatchFirst"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return MatchFirst( [ self, other ] )

    def __ror__(self, other ):
        """Implementation of | operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other | self

    def __xor__(self, other ):
        """Implementation of ^ operator - returns Or"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return Or( [ self, other ] )

    def __rxor__(self, other ):
        """Implementation of ^ operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other ^ self

    def __and__(self, other ):
        """Implementation of & operator - returns Each"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return Each( [ self, other ] )

    def __rand__(self, other ):
        """Implementation of & operator when left operand is not a ParserElement"""
        if isinstance( other, basestring ):
            other = Literal( other )
        if not isinstance( other, ParserElement ):
            warnings.warn("Cannot combine element of type %s with ParserElement" % type(other),
                    SyntaxWarning, stacklevel=2)
            return None
        return other & self

    def __invert__( self ):
        """Implementation of ~ operator - returns NotAny"""
        return NotAny( self )

    def __call__(self, name):
        """Shortcut for setResultsName, with listAllMatches=default::
             userdata = Word(alphas).setResultsName("name") + Word(nums+"-").setResultsName("socsecno")
           could be written as::
             userdata = Word(alphas)("name") + Word(nums+"-")("socsecno")
           """
        return self.setResultsName(name)

    def suppress( self ):
        """Suppresses the output of this ParserElement; useful to keep punctuation from
           cluttering up returned output.
        """
        return Suppress( self )

    def leaveWhitespace( self ):
        """Disables the skipping of whitespace before matching the characters in the
           ParserElement's defined pattern.  This is normally only used internally by
           the pyparsing module, but may be needed in some whitespace-sensitive grammars.
        """
        self.skipWhitespace = False
        return self

    def setWhitespaceChars( self, chars ):
        """Overrides the default whitespace chars
        """
        self.skipWhitespace = True
        self.whiteChars = chars
        self.copyDefaultWhiteChars = False
        return self

    def parseWithTabs( self ):
        """Overrides default behavior to expand <TAB>s to spaces before parsing the input string.
           Must be called before parseString when the input grammar contains elements that
           match <TAB> characters."""
        self.keepTabs = True
        return self

    def ignore( self, other ):
        """Define expression to be ignored (e.g., comments) while doing pattern
           matching; may be called repeatedly, to define multiple comment or other
           ignorable patterns.
        """
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                self.ignoreExprs.append( other )
        else:
            self.ignoreExprs.append( Suppress( other ) )
        return self

    def setDebugActions( self, startAction, successAction, exceptionAction ):
        """Enable display of debugging messages while doing pattern matching."""
        self.debugActions = (startAction or _defaultStartDebugAction,
                             successAction or _defaultSuccessDebugAction,
                             exceptionAction or _defaultExceptionDebugAction)
        self.debug = True
        return self

    def setDebug( self, flag=True ):
        """Enable display of debugging messages while doing pattern matching.
           Set flag to True to enable, False to disable."""
        if flag:
            self.setDebugActions( _defaultStartDebugAction, _defaultSuccessDebugAction, _defaultExceptionDebugAction )
        else:
            self.debug = False
        return self

    def __str__( self ):
        return self.name

    def __repr__( self ):
        return _ustr(self)

    def streamline( self ):
        self.streamlined = True
        self.strRepr = None
        return self

    def checkRecursion( self, parseElementList ):
        pass

    def validate( self, validateTrace=[] ):
        """Check defined expressions for valid structure, check for infinite recursive definitions."""
        self.checkRecursion( [] )

    def parseFile( self, file_or_filename, parseAll=False ):
        """Execute the parse expression on the given file or filename.
           If a filename is specified (instead of a file object),
           the entire file is opened, read, and closed before parsing.
        """
        try:
            file_contents = file_or_filename.read()
        except AttributeError:
            f = open(file_or_filename, "rb")
            file_contents = f.read()
            f.close()
        return self.parseString(file_contents, parseAll)

    def getException(self):
        return ParseException("",0,self.errmsg,self)

    def __getattr__(self,aname):
        if aname == "myException":
            self.myException = ret = self.getException();
            return ret;
        else:
            raise AttributeError("no such attribute " + aname)

    def __eq__(self,other):
        if isinstance(other, basestring):
            try:
                (self + StringEnd()).parseString(_ustr(other))
                return True
            except ParseBaseException:
                return False
        else:
            return super(ParserElement,self)==other

    def __ne__(self,other):
        return not (self == other)

    def __hash__(self):
        return hash(id(self))

    def __req__(self,other):
        return self == other

    def __rne__(self,other):
        return not (self == other)


class Token(ParserElement):
    """Abstract ParserElement subclass, for defining atomic matching patterns."""
    def __init__( self ):
        super(Token,self).__init__( savelist=False )
        #self.myException = ParseException("",0,"",self)

    def setName(self, name):
        s = super(Token,self).setName(name)
        self.errmsg = "Expected " + self.name
        #s.myException.msg = self.errmsg
        return s


class Empty(Token):
    """An empty token, will always match."""
    def __init__( self ):
        super(Empty,self).__init__()
        self.name = "Empty"
        self.mayReturnEmpty = True
        self.mayIndexError = False


class NoMatch(Token):
    """A token that will never match."""
    def __init__( self ):
        super(NoMatch,self).__init__()
        self.name = "NoMatch"
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.errmsg = "Unmatchable token"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc


class Literal(Token):
    """Token to exactly match a specified string."""
    def __init__( self, matchString ):
        super(Literal,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Literal; use Empty() instead",
                            SyntaxWarning, stacklevel=2)
            self.__class__ = Empty
        self.name = '"%s"' % _ustr(self.match)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        #self.myException.msg = self.errmsg
        self.mayIndexError = False

    # Performance tuning: this routine gets called a *lot*
    # if this is a single character match string  and the first character matches,
    # short-circuit as quickly as possible, and avoid calling startswith
    #~ @profile
    def parseImpl( self, instring, loc, doActions=True ):
        if (instring[loc] == self.firstMatchChar and
            (self.matchLen==1 or instring.startswith(self.match,loc)) ):
            return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc
_L = Literal

class Keyword(Token):
    """Token to exactly match a specified string as a keyword, that is, it must be
       immediately followed by a non-keyword character.  Compare with Literal::
         Literal("if") will match the leading 'if' in 'ifAndOnlyIf'.
         Keyword("if") will not; it will only match the leading 'if in 'if x=1', or 'if(y==2)'
       Accepts two optional constructor arguments in addition to the keyword string:
       identChars is a string of characters that would be valid identifier characters,
       defaulting to all alphanumerics + "_" and "$"; caseless allows case-insensitive
       matching, default is False.
    """
    DEFAULT_KEYWORD_CHARS = alphanums+"_$"

    def __init__( self, matchString, identChars=DEFAULT_KEYWORD_CHARS, caseless=False ):
        super(Keyword,self).__init__()
        self.match = matchString
        self.matchLen = len(matchString)
        try:
            self.firstMatchChar = matchString[0]
        except IndexError:
            warnings.warn("null string passed to Keyword; use Empty() instead",
                            SyntaxWarning, stacklevel=2)
        self.name = '"%s"' % self.match
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = False
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.caseless = caseless
        if caseless:
            self.caselessmatch = matchString.upper()
            identChars = identChars.upper()
        self.identChars = _str2dict(identChars)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.caseless:
            if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
                 (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) and
                 (loc == 0 or instring[loc-1].upper() not in self.identChars) ):
                return loc+self.matchLen, self.match
        else:
            if (instring[loc] == self.firstMatchChar and
                (self.matchLen==1 or instring.startswith(self.match,loc)) and
                (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen] not in self.identChars) and
                (loc == 0 or instring[loc-1] not in self.identChars) ):
                return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

    def copy(self):
        c = super(Keyword,self).copy()
        c.identChars = Keyword.DEFAULT_KEYWORD_CHARS
        return c

    def setDefaultKeywordChars( chars ):
        """Overrides the default Keyword chars
        """
        Keyword.DEFAULT_KEYWORD_CHARS = chars
    setDefaultKeywordChars = staticmethod(setDefaultKeywordChars)

class CaselessLiteral(Literal):
    """Token to match a specified string, ignoring case of letters.
       Note: the matched results will always be in the case of the given
       match string, NOT the case of the input text.
    """
    def __init__( self, matchString ):
        super(CaselessLiteral,self).__init__( matchString.upper() )
        # Preserve the defining literal.
        self.returnString = matchString
        self.name = "'%s'" % self.returnString
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[ loc:loc+self.matchLen ].upper() == self.match:
            return loc+self.matchLen, self.returnString
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class CaselessKeyword(Keyword):
    def __init__( self, matchString, identChars=Keyword.DEFAULT_KEYWORD_CHARS ):
        super(CaselessKeyword,self).__init__( matchString, identChars, caseless=True )

    def parseImpl( self, instring, loc, doActions=True ):
        if ( (instring[ loc:loc+self.matchLen ].upper() == self.caselessmatch) and
             (loc >= len(instring)-self.matchLen or instring[loc+self.matchLen].upper() not in self.identChars) ):
            return loc+self.matchLen, self.match
        #~ raise ParseException( instring, loc, self.errmsg )
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class Word(Token):
    """Token for matching words composed of allowed character sets.
       Defined with string containing all allowed initial characters,
       an optional string containing allowed body characters (if omitted,
       defaults to the initial character set), and an optional minimum,
       maximum, and/or exact length.  The default value for min is 1 (a
       minimum value < 1 is not valid); the default values for max and exact
       are 0, meaning no maximum or exact length restriction.
    """
    def __init__( self, initChars, bodyChars=None, min=1, max=0, exact=0, asKeyword=False ):
        super(Word,self).__init__()
        self.initCharsOrig = initChars
        self.initChars = _str2dict(initChars)
        if bodyChars :
            self.bodyCharsOrig = bodyChars
            self.bodyChars = _str2dict(bodyChars)
        else:
            self.bodyCharsOrig = initChars
            self.bodyChars = _str2dict(initChars)

        self.maxSpecified = max > 0

        if min < 1:
            raise ValueError("cannot specify a minimum length < 1; use Optional(Word()) if zero-length word is permitted")

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.asKeyword = asKeyword

        if ' ' not in self.initCharsOrig+self.bodyCharsOrig and (min==1 and max==0 and exact==0):
            if self.bodyCharsOrig == self.initCharsOrig:
                self.reString = "[%s]+" % _escapeRegexRangeChars(self.initCharsOrig)
            elif len(self.bodyCharsOrig) == 1:
                self.reString = "%s[%s]*" % \
                                      (re.escape(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            else:
                self.reString = "[%s][%s]*" % \
                                      (_escapeRegexRangeChars(self.initCharsOrig),
                                      _escapeRegexRangeChars(self.bodyCharsOrig),)
            if self.asKeyword:
                self.reString = r"\b"+self.reString+r"\b"
            try:
                self.re = re.compile( self.reString )
            except:
                self.re = None

    def parseImpl( self, instring, loc, doActions=True ):
        if self.re:
            result = self.re.match(instring,loc)
            if not result:
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc

            loc = result.end()
            return loc,result.group()

        if not(instring[ loc ] in self.initChars):
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        start = loc
        loc += 1
        instrlen = len(instring)
        bodychars = self.bodyChars
        maxloc = start + self.maxLen
        maxloc = min( maxloc, instrlen )
        while loc < maxloc and instring[loc] in bodychars:
            loc += 1

        throwException = False
        if loc - start < self.minLen:
            throwException = True
        if self.maxSpecified and loc < instrlen and instring[loc] in bodychars:
            throwException = True
        if self.asKeyword:
            if (start>0 and instring[start-1] in bodychars) or (loc<instrlen and instring[loc] in bodychars):
                throwException = True

        if throwException:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(Word,self).__str__()
        except:
            pass


        if self.strRepr is None:

            def charsAsStr(s):
                if len(s)>4:
                    return s[:4]+"..."
                else:
                    return s

            if ( self.initCharsOrig != self.bodyCharsOrig ):
                self.strRepr = "W:(%s,%s)" % ( charsAsStr(self.initCharsOrig), charsAsStr(self.bodyCharsOrig) )
            else:
                self.strRepr = "W:(%s)" % charsAsStr(self.initCharsOrig)

        return self.strRepr


class Regex(Token):
    """Token for matching strings that match a given regular expression.
       Defined with string specifying the regular expression in a form recognized by the inbuilt Python re module.
    """
    def __init__( self, pattern, flags=0):
        """The parameters pattern and flags are passed to the re.compile() function as-is. See the Python re module for an explanation of the acceptable patterns and flags."""
        super(Regex,self).__init__()

        if len(pattern) == 0:
            warnings.warn("null string passed to Regex; use Empty() instead",
                    SyntaxWarning, stacklevel=2)

        self.pattern = pattern
        self.flags = flags

        try:
            self.re = re.compile(self.pattern, self.flags)
            self.reString = self.pattern
        except sre_constants.error:
            warnings.warn("invalid pattern (%s) passed to Regex" % pattern,
                SyntaxWarning, stacklevel=2)
            raise

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        result = self.re.match(instring,loc)
        if not result:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        loc = result.end()
        d = result.groupdict()
        ret = ParseResults(result.group())
        if d:
            for k in d:
                ret[k] = d[k]
        return loc,ret

    def __str__( self ):
        try:
            return super(Regex,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "Re:(%s)" % repr(self.pattern)

        return self.strRepr


class QuotedString(Token):
    """Token for matching strings that are delimited by quoting characters.
    """
    def __init__( self, quoteChar, escChar=None, escQuote=None, multiline=False, unquoteResults=True, endQuoteChar=None):
        """
           Defined with the following parameters:
            - quoteChar - string of one or more characters defining the quote delimiting string
            - escChar - character to escape quotes, typically backslash (default=None)
            - escQuote - special quote sequence to escape an embedded quote string (such as SQL's "" to escape an embedded ") (default=None)
            - multiline - boolean indicating whether quotes can span multiple lines (default=False)
            - unquoteResults - boolean indicating whether the matched text should be unquoted (default=True)
            - endQuoteChar - string of one or more characters defining the end of the quote delimited string (default=None => same as quoteChar)
        """
        super(QuotedString,self).__init__()

        # remove white space from quote chars - wont work anyway
        quoteChar = quoteChar.strip()
        if len(quoteChar) == 0:
            warnings.warn("quoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
            raise SyntaxError()

        if endQuoteChar is None:
            endQuoteChar = quoteChar
        else:
            endQuoteChar = endQuoteChar.strip()
            if len(endQuoteChar) == 0:
                warnings.warn("endQuoteChar cannot be the empty string",SyntaxWarning,stacklevel=2)
                raise SyntaxError()

        self.quoteChar = quoteChar
        self.quoteCharLen = len(quoteChar)
        self.firstQuoteChar = quoteChar[0]
        self.endQuoteChar = endQuoteChar
        self.endQuoteCharLen = len(endQuoteChar)
        self.escChar = escChar
        self.escQuote = escQuote
        self.unquoteResults = unquoteResults

        if multiline:
            self.flags = re.MULTILINE | re.DOTALL
            self.pattern = r'%s(?:[^%s%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        else:
            self.flags = 0
            self.pattern = r'%s(?:[^%s\n\r%s]' % \
                ( re.escape(self.quoteChar),
                  _escapeRegexRangeChars(self.endQuoteChar[0]),
                  (escChar is not None and _escapeRegexRangeChars(escChar) or '') )
        if len(self.endQuoteChar) > 1:
            self.pattern += (
                '|(?:' + ')|(?:'.join(["%s[^%s]" % (re.escape(self.endQuoteChar[:i]),
                                               _escapeRegexRangeChars(self.endQuoteChar[i]))
                                    for i in range(len(self.endQuoteChar)-1,0,-1)]) + ')'
                )
        if escQuote:
            self.pattern += (r'|(?:%s)' % re.escape(escQuote))
        if escChar:
            self.pattern += (r'|(?:%s.)' % re.escape(escChar))
            self.escCharReplacePattern = re.escape(self.escChar)+"(.)"
        self.pattern += (r')*%s' % re.escape(self.endQuoteChar))

        try:
            self.re = re.compile(self.pattern, self.flags)
            self.reString = self.pattern
        except sre_constants.error:
            warnings.warn("invalid pattern (%s) passed to Regex" % self.pattern,
                SyntaxWarning, stacklevel=2)
            raise

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg
        self.mayIndexError = False
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        result = instring[loc] == self.firstQuoteChar and self.re.match(instring,loc) or None
        if not result:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        loc = result.end()
        ret = result.group()

        if self.unquoteResults:

            # strip off quotes
            ret = ret[self.quoteCharLen:-self.endQuoteCharLen]

            if isinstance(ret,basestring):
                # replace escaped characters
                if self.escChar:
                    ret = re.sub(self.escCharReplacePattern,"\g<1>",ret)

                # replace escaped quotes
                if self.escQuote:
                    ret = ret.replace(self.escQuote, self.endQuoteChar)

        return loc, ret

    def __str__( self ):
        try:
            return super(QuotedString,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "quoted string, starting with %s ending with %s" % (self.quoteChar, self.endQuoteChar)

        return self.strRepr


class CharsNotIn(Token):
    """Token for matching words composed of characters *not* in a given set.
       Defined with string containing all disallowed characters, and an optional
       minimum, maximum, and/or exact length.  The default value for min is 1 (a
       minimum value < 1 is not valid); the default values for max and exact
       are 0, meaning no maximum or exact length restriction.
    """
    def __init__( self, notChars, min=1, max=0, exact=0 ):
        super(CharsNotIn,self).__init__()
        self.skipWhitespace = False
        self.notChars = notChars

        if min < 1:
            raise ValueError("cannot specify a minimum length < 1; use Optional(CharsNotIn()) if zero-length char group is permitted")

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

        self.name = _ustr(self)
        self.errmsg = "Expected " + self.name
        self.mayReturnEmpty = ( self.minLen == 0 )
        #self.myException.msg = self.errmsg
        self.mayIndexError = False

    def parseImpl( self, instring, loc, doActions=True ):
        if instring[loc] in self.notChars:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        start = loc
        loc += 1
        notchars = self.notChars
        maxlen = min( start+self.maxLen, len(instring) )
        while loc < maxlen and \
              (instring[loc] not in notchars):
            loc += 1

        if loc - start < self.minLen:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]

    def __str__( self ):
        try:
            return super(CharsNotIn, self).__str__()
        except:
            pass

        if self.strRepr is None:
            if len(self.notChars) > 4:
                self.strRepr = "!W:(%s...)" % self.notChars[:4]
            else:
                self.strRepr = "!W:(%s)" % self.notChars

        return self.strRepr

class White(Token):
    """Special matching class for matching whitespace.  Normally, whitespace is ignored
       by pyparsing grammars.  This class is included when some whitespace structures
       are significant.  Define with a string containing the whitespace characters to be
       matched; default is " \\t\\n".  Also takes optional min, max, and exact arguments,
       as defined for the Word class."""
    whiteStrs = {
        " " : "<SPC>",
        "\t": "<TAB>",
        "\n": "<LF>",
        "\r": "<CR>",
        "\f": "<FF>",
        }
    def __init__(self, ws=" \t\r\n", min=1, max=0, exact=0):
        super(White,self).__init__()
        self.matchWhite = ws
        self.setWhitespaceChars( "".join([c for c in self.whiteChars if c not in self.matchWhite]) )
        #~ self.leaveWhitespace()
        self.name = ("".join([White.whiteStrs[c] for c in self.matchWhite]))
        self.mayReturnEmpty = True
        self.errmsg = "Expected " + self.name
        #self.myException.msg = self.errmsg

        self.minLen = min

        if max > 0:
            self.maxLen = max
        else:
            self.maxLen = _MAX_INT

        if exact > 0:
            self.maxLen = exact
            self.minLen = exact

    def parseImpl( self, instring, loc, doActions=True ):
        if not(instring[ loc ] in self.matchWhite):
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        start = loc
        loc += 1
        maxloc = start + self.maxLen
        maxloc = min( maxloc, len(instring) )
        while loc < maxloc and instring[loc] in self.matchWhite:
            loc += 1

        if loc - start < self.minLen:
            #~ raise ParseException( instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

        return loc, instring[start:loc]


class _PositionToken(Token):
    def __init__( self ):
        super(_PositionToken,self).__init__()
        self.name=self.__class__.__name__
        self.mayReturnEmpty = True
        self.mayIndexError = False

class GoToColumn(_PositionToken):
    """Token to advance to a specific column of input text; useful for tabular report scraping."""
    def __init__( self, colno ):
        super(GoToColumn,self).__init__()
        self.col = colno

    def preParse( self, instring, loc ):
        if col(loc,instring) != self.col:
            instrlen = len(instring)
            if self.ignoreExprs:
                loc = self._skipIgnorables( instring, loc )
            while loc < instrlen and instring[loc].isspace() and col( loc, instring ) != self.col :
                loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        thiscol = col( loc, instring )
        if thiscol > self.col:
            raise ParseException( instring, loc, "Text not in expected column", self )
        newloc = loc + self.col - thiscol
        ret = instring[ loc: newloc ]
        return newloc, ret

class LineStart(_PositionToken):
    """Matches if current position is at the beginning of a line within the parse string"""
    def __init__( self ):
        super(LineStart,self).__init__()
        self.setWhitespaceChars( ParserElement.DEFAULT_WHITE_CHARS.replace("\n","") )
        self.errmsg = "Expected start of line"
        #self.myException.msg = self.errmsg

    def preParse( self, instring, loc ):
        preloc = super(LineStart,self).preParse(instring,loc)
        if instring[preloc] == "\n":
            loc += 1
        return loc

    def parseImpl( self, instring, loc, doActions=True ):
        if not( loc==0 or
            (loc == self.preParse( instring, 0 )) or
            (instring[loc-1] == "\n") ): #col(loc, instring) != 1:
            #~ raise ParseException( instring, loc, "Expected start of line" )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        return loc, []

class LineEnd(_PositionToken):
    """Matches if current position is at the end of a line within the parse string"""
    def __init__( self ):
        super(LineEnd,self).__init__()
        self.setWhitespaceChars( ParserElement.DEFAULT_WHITE_CHARS.replace("\n","") )
        self.errmsg = "Expected end of line"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc<len(instring):
            if instring[loc] == "\n":
                return loc+1, "\n"
            else:
                #~ raise ParseException( instring, loc, "Expected end of line" )
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        elif loc == len(instring):
            return loc+1, []
        else:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

class StringStart(_PositionToken):
    """Matches if current position is at the beginning of the parse string"""
    def __init__( self ):
        super(StringStart,self).__init__()
        self.errmsg = "Expected start of text"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc != 0:
            # see if entire string up to here is just whitespace and ignoreables
            if loc != self.preParse( instring, 0 ):
                #~ raise ParseException( instring, loc, "Expected start of text" )
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        return loc, []

class StringEnd(_PositionToken):
    """Matches if current position is at the end of the parse string"""
    def __init__( self ):
        super(StringEnd,self).__init__()
        self.errmsg = "Expected end of text"
        #self.myException.msg = self.errmsg

    def parseImpl( self, instring, loc, doActions=True ):
        if loc < len(instring):
            #~ raise ParseException( instring, loc, "Expected end of text" )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        elif loc == len(instring):
            return loc+1, []
        elif loc > len(instring):
            return loc, []
        else:
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc

class WordStart(_PositionToken):
    """Matches if the current position is at the beginning of a Word, and
       is not preceded by any character in a given set of wordChars
       (default=printables). To emulate the \b behavior of regular expressions,
       use WordStart(alphanums). WordStart will also match at the beginning of
       the string being parsed, or at the beginning of a line.
    """
    def __init__(self, wordChars = printables):
        super(WordStart,self).__init__()
        self.wordChars = _str2dict(wordChars)
        self.errmsg = "Not at the start of a word"

    def parseImpl(self, instring, loc, doActions=True ):
        if loc != 0:
            if (instring[loc-1] in self.wordChars or
                instring[loc] not in self.wordChars):
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        return loc, []

class WordEnd(_PositionToken):
    """Matches if the current position is at the end of a Word, and
       is not followed by any character in a given set of wordChars
       (default=printables). To emulate the \b behavior of regular expressions,
       use WordEnd(alphanums). WordEnd will also match at the end of
       the string being parsed, or at the end of a line.
    """
    def __init__(self, wordChars = printables):
        super(WordEnd,self).__init__()
        self.wordChars = _str2dict(wordChars)
        self.skipWhitespace = False
        self.errmsg = "Not at the end of a word"

    def parseImpl(self, instring, loc, doActions=True ):
        instrlen = len(instring)
        if instrlen>0 and loc<instrlen:
            if (instring[loc] in self.wordChars or
                instring[loc-1] not in self.wordChars):
                #~ raise ParseException( instring, loc, "Expected end of word" )
                exc = self.myException
                exc.loc = loc
                exc.pstr = instring
                raise exc
        return loc, []


class ParseExpression(ParserElement):
    """Abstract subclass of ParserElement, for combining and post-processing parsed tokens."""
    def __init__( self, exprs, savelist = False ):
        super(ParseExpression,self).__init__(savelist)
        if isinstance( exprs, list ):
            self.exprs = exprs
        elif isinstance( exprs, basestring ):
            self.exprs = [ Literal( exprs ) ]
        else:
            self.exprs = [ exprs ]
        self.callPreparse = False

    def __getitem__( self, i ):
        return self.exprs[i]

    def append( self, other ):
        self.exprs.append( other )
        self.strRepr = None
        return self

    def leaveWhitespace( self ):
        """Extends leaveWhitespace defined in base class, and also invokes leaveWhitespace on
           all contained expressions."""
        self.skipWhitespace = False
        self.exprs = [ e.copy() for e in self.exprs ]
        for e in self.exprs:
            e.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseExpression, self).ignore( other )
                for e in self.exprs:
                    e.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseExpression, self).ignore( other )
            for e in self.exprs:
                e.ignore( self.ignoreExprs[-1] )
        return self

    def __str__( self ):
        try:
            return super(ParseExpression,self).__str__()
        except:
            pass

        if self.strRepr is None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.exprs) )
        return self.strRepr

    def streamline( self ):
        super(ParseExpression,self).streamline()

        for e in self.exprs:
            e.streamline()

        # collapse nested And's of the form And( And( And( a,b), c), d) to And( a,b,c,d )
        # but only if there are no parse actions or resultsNames on the nested And's
        # (likewise for Or's and MatchFirst's)
        if ( len(self.exprs) == 2 ):
            other = self.exprs[0]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = other.exprs[:] + [ self.exprs[1] ]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError  |= other.mayIndexError

            other = self.exprs[-1]
            if ( isinstance( other, self.__class__ ) and
                  not(other.parseAction) and
                  other.resultsName is None and
                  not other.debug ):
                self.exprs = self.exprs[:-1] + other.exprs[:]
                self.strRepr = None
                self.mayReturnEmpty |= other.mayReturnEmpty
                self.mayIndexError  |= other.mayIndexError

        return self

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(ParseExpression,self).setResultsName(name,listAllMatches)
        return ret

    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        for e in self.exprs:
            e.validate(tmp)
        self.checkRecursion( [] )

class And(ParseExpression):
    """Requires all given ParseExpressions to be found in the given order.
       Expressions may be separated by whitespace.
       May be constructed using the '+' operator.
    """

    class _ErrorStop(Empty):
        def __init__(self, *args, **kwargs):
            super(Empty,self).__init__(*args, **kwargs)
            self.leaveWhitespace()

    def __init__( self, exprs, savelist = True ):
        super(And,self).__init__(exprs, savelist)
        self.mayReturnEmpty = True
        for e in self.exprs:
            if not e.mayReturnEmpty:
                self.mayReturnEmpty = False
                break
        self.setWhitespaceChars( exprs[0].whiteChars )
        self.skipWhitespace = exprs[0].skipWhitespace
        self.callPreparse = True

    def parseImpl( self, instring, loc, doActions=True ):
        # pass False as last arg to _parse for first element, since we already
        # pre-parsed the string as part of our And pre-parsing
        loc, resultlist = self.exprs[0]._parse( instring, loc, doActions, callPreParse=False )
        errorStop = False
        for e in self.exprs[1:]:
            if isinstance(e, And._ErrorStop):
                errorStop = True
                continue
            if errorStop:
                try:
                    loc, exprtokens = e._parse( instring, loc, doActions )
                except ParseSyntaxException:
                    raise
                except ParseBaseException, pe:
                    raise ParseSyntaxException(pe)
                except IndexError, ie:
                    raise ParseSyntaxException( ParseException(instring, len(instring), self.errmsg, self) )
            else:
                loc, exprtokens = e._parse( instring, loc, doActions )
            if exprtokens or exprtokens.keys():
                resultlist += exprtokens
        return loc, resultlist

    def __iadd__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #And( [ self, other ] )

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )
            if not e.mayReturnEmpty:
                break

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr


class Or(ParseExpression):
    """Requires that at least one ParseExpression is found.
       If two expressions match, the expression that matches the longest string will be used.
       May be constructed using the '^' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(Or,self).__init__(exprs, savelist)
        self.mayReturnEmpty = False
        for e in self.exprs:
            if e.mayReturnEmpty:
                self.mayReturnEmpty = True
                break

    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        maxMatchLoc = -1
        maxException = None
        for e in self.exprs:
            try:
                loc2 = e.tryParse( instring, loc )
            except ParseException, err:
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)
            else:
                if loc2 > maxMatchLoc:
                    maxMatchLoc = loc2
                    maxMatchExp = e

        if maxMatchLoc < 0:
            if maxException is not None:
                raise maxException
            else:
                raise ParseException(instring, loc, "no defined alternatives to match", self)

        return maxMatchExp._parse( instring, loc, doActions )

    def __ixor__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #Or( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " ^ ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class MatchFirst(ParseExpression):
    """Requires that at least one ParseExpression is found.
       If two expressions match, the first one listed is the one that will match.
       May be constructed using the '|' operator.
    """
    def __init__( self, exprs, savelist = False ):
        super(MatchFirst,self).__init__(exprs, savelist)
        if exprs:
            self.mayReturnEmpty = False
            for e in self.exprs:
                if e.mayReturnEmpty:
                    self.mayReturnEmpty = True
                    break
        else:
            self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        maxExcLoc = -1
        maxException = None
        for e in self.exprs:
            try:
                ret = e._parse( instring, loc, doActions )
                return ret
            except ParseException, err:
                if err.loc > maxExcLoc:
                    maxException = err
                    maxExcLoc = err.loc
            except IndexError:
                if len(instring) > maxExcLoc:
                    maxException = ParseException(instring,len(instring),e.errmsg,self)
                    maxExcLoc = len(instring)

        # only got here if no expression matched, raise exception for match that made it the furthest
        else:
            if maxException is not None:
                raise maxException
            else:
                raise ParseException(instring, loc, "no defined alternatives to match", self)

    def __ior__(self, other ):
        if isinstance( other, basestring ):
            other = Literal( other )
        return self.append( other ) #MatchFirst( [ self, other ] )

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " | ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class Each(ParseExpression):
    """Requires all given ParseExpressions to be found, but in any order.
       Expressions may be separated by whitespace.
       May be constructed using the '&' operator.
    """
    def __init__( self, exprs, savelist = True ):
        super(Each,self).__init__(exprs, savelist)
        self.mayReturnEmpty = True
        for e in self.exprs:
            if not e.mayReturnEmpty:
                self.mayReturnEmpty = False
                break
        self.skipWhitespace = True
        self.initExprGroups = True

    def parseImpl( self, instring, loc, doActions=True ):
        if self.initExprGroups:
            self.optionals = [ e.expr for e in self.exprs if isinstance(e,Optional) ]
            self.multioptionals = [ e.expr for e in self.exprs if isinstance(e,ZeroOrMore) ]
            self.multirequired = [ e.expr for e in self.exprs if isinstance(e,OneOrMore) ]
            self.required = [ e for e in self.exprs if not isinstance(e,(Optional,ZeroOrMore,OneOrMore)) ]
            self.required += self.multirequired
            self.initExprGroups = False
        tmpLoc = loc
        tmpReqd = self.required[:]
        tmpOpt  = self.optionals[:]
        matchOrder = []

        keepMatching = True
        while keepMatching:
            tmpExprs = tmpReqd + tmpOpt + self.multioptionals + self.multirequired
            failed = []
            for e in tmpExprs:
                try:
                    tmpLoc = e.tryParse( instring, tmpLoc )
                except ParseException:
                    failed.append(e)
                else:
                    matchOrder.append(e)
                    if e in tmpReqd:
                        tmpReqd.remove(e)
                    elif e in tmpOpt:
                        tmpOpt.remove(e)
            if len(failed) == len(tmpExprs):
                keepMatching = False

        if tmpReqd:
            missing = ", ".join( [ _ustr(e) for e in tmpReqd ] )
            raise ParseException(instring,loc,"Missing one or more required elements (%s)" % missing )

        # add any unmatched Optionals, in case they have default values defined
        matchOrder += [ e for e in self.exprs if isinstance(e,Optional) and e.expr in tmpOpt ]

        resultlist = []
        for e in matchOrder:
            loc,results = e._parse(instring,loc,doActions)
            resultlist.append(results)

        finalResults = ParseResults([])
        for r in resultlist:
            dups = {}
            for k in r.keys():
                if k in finalResults.keys():
                    tmp = ParseResults(finalResults[k])
                    tmp += ParseResults(r[k])
                    dups[k] = tmp
            finalResults += ParseResults(r)
            for k,v in dups.items():
                finalResults[k] = v
        return loc, finalResults

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + " & ".join( [ _ustr(e) for e in self.exprs ] ) + "}"

        return self.strRepr

    def checkRecursion( self, parseElementList ):
        subRecCheckList = parseElementList[:] + [ self ]
        for e in self.exprs:
            e.checkRecursion( subRecCheckList )


class ParseElementEnhance(ParserElement):
    """Abstract subclass of ParserElement, for combining and post-processing parsed tokens."""
    def __init__( self, expr, savelist=False ):
        super(ParseElementEnhance,self).__init__(savelist)
        if isinstance( expr, basestring ):
            expr = Literal(expr)
        self.expr = expr
        self.strRepr = None
        if expr is not None:
            self.mayIndexError = expr.mayIndexError
            self.mayReturnEmpty = expr.mayReturnEmpty
            self.setWhitespaceChars( expr.whiteChars )
            self.skipWhitespace = expr.skipWhitespace
            self.saveAsList = expr.saveAsList
            self.callPreparse = expr.callPreparse
            self.ignoreExprs.extend(expr.ignoreExprs)

    def parseImpl( self, instring, loc, doActions=True ):
        if self.expr is not None:
            return self.expr._parse( instring, loc, doActions, callPreParse=False )
        else:
            raise ParseException("",loc,self.errmsg,self)

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        self.expr = self.expr.copy()
        if self.expr is not None:
            self.expr.leaveWhitespace()
        return self

    def ignore( self, other ):
        if isinstance( other, Suppress ):
            if other not in self.ignoreExprs:
                super( ParseElementEnhance, self).ignore( other )
                if self.expr is not None:
                    self.expr.ignore( self.ignoreExprs[-1] )
        else:
            super( ParseElementEnhance, self).ignore( other )
            if self.expr is not None:
                self.expr.ignore( self.ignoreExprs[-1] )
        return self

    def streamline( self ):
        super(ParseElementEnhance,self).streamline()
        if self.expr is not None:
            self.expr.streamline()
        return self

    def checkRecursion( self, parseElementList ):
        if self in parseElementList:
            raise RecursiveGrammarException( parseElementList+[self] )
        subRecCheckList = parseElementList[:] + [ self ]
        if self.expr is not None:
            self.expr.checkRecursion( subRecCheckList )

    def validate( self, validateTrace=[] ):
        tmp = validateTrace[:]+[self]
        if self.expr is not None:
            self.expr.validate(tmp)
        self.checkRecursion( [] )

    def __str__( self ):
        try:
            return super(ParseElementEnhance,self).__str__()
        except:
            pass

        if self.strRepr is None and self.expr is not None:
            self.strRepr = "%s:(%s)" % ( self.__class__.__name__, _ustr(self.expr) )
        return self.strRepr


class FollowedBy(ParseElementEnhance):
    """Lookahead matching of the given parse expression.  FollowedBy
    does *not* advance the parsing position within the input string, it only
    verifies that the specified parse expression matches at the current
    position.  FollowedBy always returns a null token list."""
    def __init__( self, expr ):
        super(FollowedBy,self).__init__(expr)
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        self.expr.tryParse( instring, loc )
        return loc, []


class NotAny(ParseElementEnhance):
    """Lookahead to disallow matching with the given parse expression.  NotAny
    does *not* advance the parsing position within the input string, it only
    verifies that the specified parse expression does *not* match at the current
    position.  Also, NotAny does *not* skip over leading whitespace. NotAny
    always returns a null token list.  May be constructed using the '~' operator."""
    def __init__( self, expr ):
        super(NotAny,self).__init__(expr)
        #~ self.leaveWhitespace()
        self.skipWhitespace = False  # do NOT use self.leaveWhitespace(), don't want to propagate to exprs
        self.mayReturnEmpty = True
        self.errmsg = "Found unwanted token, "+_ustr(self.expr)
        #self.myException = ParseException("",0,self.errmsg,self)

    def parseImpl( self, instring, loc, doActions=True ):
        try:
            self.expr.tryParse( instring, loc )
        except (ParseException,IndexError):
            pass
        else:
            #~ raise ParseException(instring, loc, self.errmsg )
            exc = self.myException
            exc.loc = loc
            exc.pstr = instring
            raise exc
        return loc, []

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "~{" + _ustr(self.expr) + "}"

        return self.strRepr


class ZeroOrMore(ParseElementEnhance):
    """Optional repetition of zero or more of the given expression."""
    def __init__( self, expr ):
        super(ZeroOrMore,self).__init__(expr)
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        tokens = []
        try:
            loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    preloc = self._skipIgnorables( instring, loc )
                else:
                    preloc = loc
                loc, tmptokens = self.expr._parse( instring, preloc, doActions )
                if tmptokens or tmptokens.keys():
                    tokens += tmptokens
        except (ParseException,IndexError):
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]..."

        return self.strRepr

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(ZeroOrMore,self).setResultsName(name,listAllMatches)
        ret.saveAsList = True
        return ret


class OneOrMore(ParseElementEnhance):
    """Repetition of one or more of the given expression."""
    def parseImpl( self, instring, loc, doActions=True ):
        # must be at least one
        loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
        try:
            hasIgnoreExprs = ( len(self.ignoreExprs) > 0 )
            while 1:
                if hasIgnoreExprs:
                    preloc = self._skipIgnorables( instring, loc )
                else:
                    preloc = loc
                loc, tmptokens = self.expr._parse( instring, preloc, doActions )
                if tmptokens or tmptokens.keys():
                    tokens += tmptokens
        except (ParseException,IndexError):
            pass

        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "{" + _ustr(self.expr) + "}..."

        return self.strRepr

    def setResultsName( self, name, listAllMatches=False ):
        ret = super(OneOrMore,self).setResultsName(name,listAllMatches)
        ret.saveAsList = True
        return ret

class _NullToken(object):
    def __bool__(self):
        return False
    __nonzero__ = __bool__
    def __str__(self):
        return ""

_optionalNotMatched = _NullToken()
class Optional(ParseElementEnhance):
    """Optional matching of the given expression.
       A default return string can also be specified, if the optional expression
       is not found.
    """
    def __init__( self, exprs, default=_optionalNotMatched ):
        super(Optional,self).__init__( exprs, savelist=False )
        self.defaultValue = default
        self.mayReturnEmpty = True

    def parseImpl( self, instring, loc, doActions=True ):
        try:
            loc, tokens = self.expr._parse( instring, loc, doActions, callPreParse=False )
        except (ParseException,IndexError):
            if self.defaultValue is not _optionalNotMatched:
                if self.expr.resultsName:
                    tokens = ParseResults([ self.defaultValue ])
                    tokens[self.expr.resultsName] = self.defaultValue
                else:
                    tokens = [ self.defaultValue ]
            else:
                tokens = []
        return loc, tokens

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        if self.strRepr is None:
            self.strRepr = "[" + _ustr(self.expr) + "]"

        return self.strRepr


class SkipTo(ParseElementEnhance):
    """Token for skipping over all undefined text until the matched expression is found.
       If include is set to true, the matched expression is also consumed.  The ignore
       argument is used to define grammars (typically quoted strings and comments) that
       might contain false matches.
    """
    def __init__( self, other, include=False, ignore=None, failOn=None ):
        super( SkipTo, self ).__init__( other )
        if ignore is not None:
            self.expr = self.expr.copy()
            self.expr.ignore(ignore)
        self.mayReturnEmpty = True
        self.mayIndexError = False
        self.includeMatch = include
        self.asList = False
        if failOn is not None and isinstance(failOn, basestring):
            self.failOn = Literal(failOn)
        else:
            self.failOn = failOn
        self.errmsg = "No match found for "+_ustr(self.expr)
        #self.myException = ParseException("",0,self.errmsg,self)

    def parseImpl( self, instring, loc, doActions=True ):
        startLoc = loc
        instrlen = len(instring)
        expr = self.expr
        failParse = False
        while loc <= instrlen:
            try:
                if self.failOn:
                    failParse = True
                    self.failOn.tryParse(instring, loc)
                    failParse = False
                loc = expr._skipIgnorables( instring, loc )
                expr._parse( instring, loc, doActions=False, callPreParse=False )
                skipText = instring[startLoc:loc]
                if self.includeMatch:
                    loc,mat = expr._parse(instring,loc,doActions,callPreParse=False)
                    if mat:
                        skipRes = ParseResults( skipText )
                        skipRes += mat
                        return loc, [ skipRes ]
                    else:
                        return loc, [ skipText ]
                else:
                    return loc, [ skipText ]
            except (ParseException,IndexError):
                if failParse:
                    raise
                else:
                    loc += 1
        exc = self.myException
        exc.loc = loc
        exc.pstr = instring
        raise exc

class Forward(ParseElementEnhance):
    """Forward declaration of an expression to be defined later -
       used for recursive grammars, such as algebraic infix notation.
       When the expression is known, it is assigned to the Forward variable using the '<<' operator.

       Note: take care when assigning to Forward not to overlook precedence of operators.
       Specifically, '|' has a lower precedence than '<<', so that::
          fwdExpr << a | b | c
       will actually be evaluated as::
          (fwdExpr << a) | b | c
       thereby leaving b and c out as parseable alternatives.  It is recommended that you
       explicitly group the values inserted into the Forward::
          fwdExpr << (a | b | c)
    """
    def __init__( self, other=None ):
        super(Forward,self).__init__( other, savelist=False )

    def __lshift__( self, other ):
        if isinstance( other, basestring ):
            other = Literal(other)
        self.expr = other
        self.mayReturnEmpty = other.mayReturnEmpty
        self.strRepr = None
        self.mayIndexError = self.expr.mayIndexError
        self.mayReturnEmpty = self.expr.mayReturnEmpty
        self.setWhitespaceChars( self.expr.whiteChars )
        self.skipWhitespace = self.expr.skipWhitespace
        self.saveAsList = self.expr.saveAsList
        self.ignoreExprs.extend(self.expr.ignoreExprs)
        return None

    def leaveWhitespace( self ):
        self.skipWhitespace = False
        return self

    def streamline( self ):
        if not self.streamlined:
            self.streamlined = True
            if self.expr is not None:
                self.expr.streamline()
        return self

    def validate( self, validateTrace=[] ):
        if self not in validateTrace:
            tmp = validateTrace[:]+[self]
            if self.expr is not None:
                self.expr.validate(tmp)
        self.checkRecursion([])

    def __str__( self ):
        if hasattr(self,"name"):
            return self.name

        self._revertClass = self.__class__
        self.__class__ = _ForwardNoRecurse
        try:
            if self.expr is not None:
                retString = _ustr(self.expr)
            else:
                retString = "None"
        finally:
            self.__class__ = self._revertClass
        return self.__class__.__name__ + ": " + retString

    def copy(self):
        if self.expr is not None:
            return super(Forward,self).copy()
        else:
            ret = Forward()
            ret << self
            return ret

class _ForwardNoRecurse(Forward):
    def __str__( self ):
        return "..."

class TokenConverter(ParseElementEnhance):
    """Abstract subclass of ParseExpression, for converting parsed results."""
    def __init__( self, expr, savelist=False ):
        super(TokenConverter,self).__init__( expr )#, savelist )
        self.saveAsList = False

class Upcase(TokenConverter):
    """Converter to upper case all matching tokens."""
    def __init__(self, *args):
        super(Upcase,self).__init__(*args)
        warnings.warn("Upcase class is deprecated, use upcaseTokens parse action instead",
                       DeprecationWarning,stacklevel=2)

    def postParse( self, instring, loc, tokenlist ):
        return list(map( string.upper, tokenlist ))


class Combine(TokenConverter):
    """Converter to concatenate all matching tokens to a single string.
       By default, the matching patterns must also be contiguous in the input string;
       this can be disabled by specifying 'adjacent=False' in the constructor.
    """
    def __init__( self, expr, joinString="", adjacent=True ):
        super(Combine,self).__init__( expr )
        # suppress whitespace-stripping in contained parse expressions, but re-enable it on the Combine itself
        if adjacent:
            self.leaveWhitespace()
        self.adjacent = adjacent
        self.skipWhitespace = True
        self.joinString = joinString

    def ignore( self, other ):
        if self.adjacent:
            ParserElement.ignore(self, other)
        else:
            super( Combine, self).ignore( other )
        return self

    def postParse( self, instring, loc, tokenlist ):
        retToks = tokenlist.copy()
        del retToks[:]
        retToks += ParseResults([ "".join(tokenlist._asStringList(self.joinString)) ], modal=self.modalResults)

        if self.resultsName and len(retToks.keys())>0:
            return [ retToks ]
        else:
            return retToks

class Group(TokenConverter):
    """Converter to return the matched tokens as a list - useful for returning tokens of ZeroOrMore and OneOrMore expressions."""
    def __init__( self, expr ):
        super(Group,self).__init__( expr )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        return [ tokenlist ]

class Dict(TokenConverter):
    """Converter to return a repetitive expression as a list, but also as a dictionary.
       Each element can also be referenced using the first token in the expression as its key.
       Useful for tabular report scraping when the first column can be used as a item key.
    """
    def __init__( self, exprs ):
        super(Dict,self).__init__( exprs )
        self.saveAsList = True

    def postParse( self, instring, loc, tokenlist ):
        for i,tok in enumerate(tokenlist):
            if len(tok) == 0:
                continue
            ikey = tok[0]
            if isinstance(ikey,int):
                ikey = _ustr(tok[0]).strip()
            if len(tok)==1:
                tokenlist[ikey] = _ParseResultsWithOffset("",i)
            elif len(tok)==2 and not isinstance(tok[1],ParseResults):
                tokenlist[ikey] = _ParseResultsWithOffset(tok[1],i)
            else:
                dictvalue = tok.copy() #ParseResults(i)
                del dictvalue[0]
                if len(dictvalue)!= 1 or (isinstance(dictvalue,ParseResults) and dictvalue.keys()):
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue,i)
                else:
                    tokenlist[ikey] = _ParseResultsWithOffset(dictvalue[0],i)

        if self.resultsName:
            return [ tokenlist ]
        else:
            return tokenlist


class Suppress(TokenConverter):
    """Converter for ignoring the results of a parsed expression."""
    def postParse( self, instring, loc, tokenlist ):
        return []

    def suppress( self ):
        return self


class OnlyOnce(object):
    """Wrapper for parse actions, to ensure they are only called once."""
    def __init__(self, methodCall):
        self.callable = ParserElement._normalizeParseActionArgs(methodCall)
        self.called = False
    def __call__(self,s,l,t):
        if not self.called:
            results = self.callable(s,l,t)
            self.called = True
            return results
        raise ParseException(s,l,"")
    def reset(self):
        self.called = False

def traceParseAction(f):
    """Decorator for debugging parse actions."""
    f = ParserElement._normalizeParseActionArgs(f)
    def z(*paArgs):
        thisFunc = f.func_name
        s,l,t = paArgs[-3:]
        if len(paArgs)>3:
            thisFunc = paArgs[0].__class__.__name__ + '.' + thisFunc
        sys.stderr.write( ">>entering %s(line: '%s', %d, %s)\n" % (thisFunc,line(l,s),l,t) )
        try:
            ret = f(*paArgs)
        except Exception, exc:
            sys.stderr.write( "<<leaving %s (exception: %s)\n" % (thisFunc,exc) )
            raise
        sys.stderr.write( "<<leaving %s (ret: %s)\n" % (thisFunc,ret) )
        return ret
    try:
        z.__name__ = f.__name__
    except AttributeError:
        pass
    return z

#
# global helpers
#
def delimitedList( expr, delim=",", combine=False ):
    """Helper to define a delimited list of expressions - the delimiter defaults to ','.
       By default, the list elements and delimiters can have intervening whitespace, and
       comments, but this can be overridden by passing 'combine=True' in the constructor.
       If combine is set to True, the matching tokens are returned as a single token
       string, with the delimiters included; otherwise, the matching tokens are returned
       as a list of tokens, with the delimiters suppressed.
    """
    dlName = _ustr(expr)+" ["+_ustr(delim)+" "+_ustr(expr)+"]..."
    if combine:
        return Combine( expr + ZeroOrMore( delim + expr ) ).setName(dlName)
    else:
        return ( expr + ZeroOrMore( Suppress( delim ) + expr ) ).setName(dlName)

def countedArray( expr ):
    """Helper to define a counted list of expressions.
       This helper defines a pattern of the form::
           integer expr expr expr...
       where the leading integer tells how many expr expressions follow.
       The matched tokens returns the array of expr tokens as a list - the leading count token is suppressed.
    """
    arrayExpr = Forward()
    def countFieldParseAction(s,l,t):
        n = int(t[0])
        arrayExpr << (n and Group(And([expr]*n)) or Group(empty))
        return []
    return ( Word(nums).setName("arrayLen").setParseAction(countFieldParseAction, callDuringTry=True) + arrayExpr )

def _flatten(L):
    if type(L) is not list: return [L]
    if L == []: return L
    return _flatten(L[0]) + _flatten(L[1:])

def matchPreviousLiteral(expr):
    """Helper to define an expression that is indirectly defined from
       the tokens matched in a previous expression, that is, it looks
       for a 'repeat' of a previous expression.  For example::
           first = Word(nums)
           second = matchPreviousLiteral(first)
           matchExpr = first + ":" + second
       will match "1:1", but not "1:2".  Because this matches a
       previous literal, will also match the leading "1:1" in "1:10".
       If this is not desired, use matchPreviousExpr.
       Do *not* use with packrat parsing enabled.
    """
    rep = Forward()
    def copyTokenToRepeater(s,l,t):
        if t:
            if len(t) == 1:
                rep << t[0]
            else:
                # flatten t tokens
                tflat = _flatten(t.asList())
                rep << And( [ Literal(tt) for tt in tflat ] )
        else:
            rep << Empty()
    expr.addParseAction(copyTokenToRepeater, callDuringTry=True)
    return rep

def matchPreviousExpr(expr):
    """Helper to define an expression that is indirectly defined from
       the tokens matched in a previous expression, that is, it looks
       for a 'repeat' of a previous expression.  For example::
           first = Word(nums)
           second = matchPreviousExpr(first)
           matchExpr = first + ":" + second
       will match "1:1", but not "1:2".  Because this matches by
       expressions, will *not* match the leading "1:1" in "1:10";
       the expressions are evaluated first, and then compared, so
       "1" is compared with "10".
       Do *not* use with packrat parsing enabled.
    """
    rep = Forward()
    e2 = expr.copy()
    rep << e2
    def copyTokenToRepeater(s,l,t):
        matchTokens = _flatten(t.asList())
        def mustMatchTheseTokens(s,l,t):
            theseTokens = _flatten(t.asList())
            if  theseTokens != matchTokens:
                raise ParseException("",0,"")
        rep.setParseAction( mustMatchTheseTokens, callDuringTry=True )
    expr.addParseAction(copyTokenToRepeater, callDuringTry=True)
    return rep

def _escapeRegexRangeChars(s):
    #~  escape these chars: ^-]
    for c in r"\^-]":
        s = s.replace(c,_bslash+c)
    s = s.replace("\n",r"\n")
    s = s.replace("\t",r"\t")
    return _ustr(s)

def oneOf( strs, caseless=False, useRegex=True ):
    """Helper to quickly define a set of alternative Literals, and makes sure to do
       longest-first testing when there is a conflict, regardless of the input order,
       but returns a MatchFirst for best performance.

       Parameters:
        - strs - a string of space-delimited literals, or a list of string literals
        - caseless - (default=False) - treat all literals as caseless
        - useRegex - (default=True) - as an optimization, will generate a Regex
          object; otherwise, will generate a MatchFirst object (if caseless=True, or
          if creating a Regex raises an exception)
    """
    if caseless:
        isequal = ( lambda a,b: a.upper() == b.upper() )
        masks = ( lambda a,b: b.upper().startswith(a.upper()) )
        parseElementClass = CaselessLiteral
    else:
        isequal = ( lambda a,b: a == b )
        masks = ( lambda a,b: b.startswith(a) )
        parseElementClass = Literal

    if isinstance(strs,(list,tuple)):
        symbols = strs[:]
    elif isinstance(strs,basestring):
        symbols = strs.split()
    else:
        warnings.warn("Invalid argument to oneOf, expected string or list",
                SyntaxWarning, stacklevel=2)

    i = 0
    while i < len(symbols)-1:
        cur = symbols[i]
        for j,other in enumerate(symbols[i+1:]):
            if ( isequal(other, cur) ):
                del symbols[i+j+1]
                break
            elif ( masks(cur, other) ):
                del symbols[i+j+1]
                symbols.insert(i,other)
                cur = other
                break
        else:
            i += 1

    if not caseless and useRegex:
        #~ print (strs,"->", "|".join( [ _escapeRegexChars(sym) for sym in symbols] ))
        try:
            if len(symbols)==len("".join(symbols)):
                return Regex( "[%s]" % "".join( [ _escapeRegexRangeChars(sym) for sym in symbols] ) )
            else:
                return Regex( "|".join( [ re.escape(sym) for sym in symbols] ) )
        except:
            warnings.warn("Exception creating Regex for oneOf, building MatchFirst",
                    SyntaxWarning, stacklevel=2)


    # last resort, just use MatchFirst
    return MatchFirst( [ parseElementClass(sym) for sym in symbols ] )

def dictOf( key, value ):
    """Helper to easily and clearly define a dictionary by specifying the respective patterns
       for the key and value.  Takes care of defining the Dict, ZeroOrMore, and Group tokens
       in the proper order.  The key pattern can include delimiting markers or punctuation,
       as long as they are suppressed, thereby leaving the significant key text.  The value
       pattern can include named results, so that the Dict results can include named token
       fields.
    """
    return Dict( ZeroOrMore( Group ( key + value ) ) )

def originalTextFor(expr, asString=True):
    """Helper to return the original, untokenized text for a given expression.  Useful to
       restore the parsed fields of an HTML start tag into the raw tag text itself, or to
       revert separate tokens with intervening whitespace back to the original matching
       input text. Simpler to use than the parse action keepOriginalText, and does not
       require the inspect module to chase up the call stack.  By default, returns a 
       string containing the original parsed text.  
       
       If the optional asString argument is passed as False, then the return value is a 
       ParseResults containing any results names that were originally matched, and a 
       single token containing the original matched text from the input string.  So if 
       the expression passed to originalTextFor contains expressions with defined
       results names, you must set asString to False if you want to preserve those
       results name values."""
    locMarker = Empty().setParseAction(lambda s,loc,t: loc)
    matchExpr = locMarker("_original_start") + expr + locMarker("_original_end")
    if asString:
        extractText = lambda s,l,t: s[t._original_start:t._original_end]
    else:
        def extractText(s,l,t):
            del t[:]
            t.insert(0, s[t._original_start:t._original_end])
            del t["_original_start"]
            del t["_original_end"]
    matchExpr.setParseAction(extractText)
    return matchExpr
    
# convenience constants for positional expressions
empty       = Empty().setName("empty")
lineStart   = LineStart().setName("lineStart")
lineEnd     = LineEnd().setName("lineEnd")
stringStart = StringStart().setName("stringStart")
stringEnd   = StringEnd().setName("stringEnd")

_escapedPunc = Word( _bslash, r"\[]-*.$+^?()~ ", exact=2 ).setParseAction(lambda s,l,t:t[0][1])
_printables_less_backslash = "".join([ c for c in printables if c not in  r"\]" ])
_escapedHexChar = Combine( Suppress(_bslash + "0x") + Word(hexnums) ).setParseAction(lambda s,l,t:unichr(int(t[0],16)))
_escapedOctChar = Combine( Suppress(_bslash) + Word("0","01234567") ).setParseAction(lambda s,l,t:unichr(int(t[0],8)))
_singleChar = _escapedPunc | _escapedHexChar | _escapedOctChar | Word(_printables_less_backslash,exact=1)
_charRange = Group(_singleChar + Suppress("-") + _singleChar)
_reBracketExpr = Literal("[") + Optional("^").setResultsName("negate") + Group( OneOrMore( _charRange | _singleChar ) ).setResultsName("body") + "]"

_expanded = lambda p: (isinstance(p,ParseResults) and ''.join([ unichr(c) for c in range(ord(p[0]),ord(p[1])+1) ]) or p)

def srange(s):
    r"""Helper to easily define string ranges for use in Word construction.  Borrows
       syntax from regexp '[]' string range definitions::
          srange("[0-9]")   -> "0123456789"
          srange("[a-z]")   -> "abcdefghijklmnopqrstuvwxyz"
          srange("[a-z$_]") -> "abcdefghijklmnopqrstuvwxyz$_"
       The input string must be enclosed in []'s, and the returned string is the expanded
       character set joined into a single string.
       The values enclosed in the []'s may be::
          a single character
          an escaped character with a leading backslash (such as \- or \])
          an escaped hex character with a leading '\0x' (\0x21, which is a '!' character)
          an escaped octal character with a leading '\0' (\041, which is a '!' character)
          a range of any of the above, separated by a dash ('a-z', etc.)
          any combination of the above ('aeiouy', 'a-zA-Z0-9_$', etc.)
    """
    try:
        return "".join([_expanded(part) for part in _reBracketExpr.parseString(s).body])
    except:
        return ""

def matchOnlyAtCol(n):
    """Helper method for defining parse actions that require matching at a specific
       column in the input text.
    """
    def verifyCol(strg,locn,toks):
        if col(locn,strg) != n:
            raise ParseException(strg,locn,"matched token not at column %d" % n)
    return verifyCol

def replaceWith(replStr):
    """Helper method for common parse actions that simply return a literal value.  Especially
       useful when used with transformString().
    """
    def _replFunc(*args):
        return [replStr]
    return _replFunc

def removeQuotes(s,l,t):
    """Helper parse action for removing quotation marks from parsed quoted strings.
       To use, add this parse action to quoted string using::
         quotedString.setParseAction( removeQuotes )
    """
    return t[0][1:-1]

def upcaseTokens(s,l,t):
    """Helper parse action to convert tokens to upper case."""
    return [ tt.upper() for tt in map(_ustr,t) ]

def downcaseTokens(s,l,t):
    """Helper parse action to convert tokens to lower case."""
    return [ tt.lower() for tt in map(_ustr,t) ]

def keepOriginalText(s,startLoc,t):
    """Helper parse action to preserve original parsed text,
       overriding any nested parse actions."""
    try:
        endloc = getTokensEndLoc()
    except ParseException:
        raise ParseFatalException("incorrect usage of keepOriginalText - may only be called as a parse action")
    del t[:]
    t += ParseResults(s[startLoc:endloc])
    return t

def getTokensEndLoc():
    """Method to be called from within a parse action to determine the end
       location of the parsed tokens."""
    import inspect
    fstack = inspect.stack()
    try:
        # search up the stack (through intervening argument normalizers) for correct calling routine
        for f in fstack[2:]:
            if f[3] == "_parseNoCache":
                endloc = f[0].f_locals["loc"]
                return endloc
        else:
            raise ParseFatalException("incorrect usage of getTokensEndLoc - may only be called from within a parse action")
    finally:
        del fstack

def _makeTags(tagStr, xml):
    """Internal helper to construct opening and closing tag expressions, given a tag name"""
    if isinstance(tagStr,basestring):
        resname = tagStr
        tagStr = Keyword(tagStr, caseless=not xml)
    else:
        resname = tagStr.name

    tagAttrName = Word(alphas,alphanums+"_-:")
    if (xml):
        tagAttrValue = dblQuotedString.copy().setParseAction( removeQuotes )
        openTag = Suppress("<") + tagStr + \
                Dict(ZeroOrMore(Group( tagAttrName + Suppress("=") + tagAttrValue ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    else:
        printablesLessRAbrack = "".join( [ c for c in printables if c not in ">" ] )
        tagAttrValue = quotedString.copy().setParseAction( removeQuotes ) | Word(printablesLessRAbrack)
        openTag = Suppress("<") + tagStr + \
                Dict(ZeroOrMore(Group( tagAttrName.setParseAction(downcaseTokens) + \
                Optional( Suppress("=") + tagAttrValue ) ))) + \
                Optional("/",default=[False]).setResultsName("empty").setParseAction(lambda s,l,t:t[0]=='/') + Suppress(">")
    closeTag = Combine(_L("</") + tagStr + ">")

    openTag = openTag.setResultsName("start"+"".join(resname.replace(":"," ").title().split())).setName("<%s>" % tagStr)
    closeTag = closeTag.setResultsName("end"+"".join(resname.replace(":"," ").title().split())).setName("</%s>" % tagStr)

    return openTag, closeTag

def makeHTMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for HTML, given a tag name"""
    return _makeTags( tagStr, False )

def makeXMLTags(tagStr):
    """Helper to construct opening and closing tag expressions for XML, given a tag name"""
    return _makeTags( tagStr, True )

def withAttribute(*args,**attrDict):
    """Helper to create a validating parse action to be used with start tags created
       with makeXMLTags or makeHTMLTags. Use withAttribute to qualify a starting tag
       with a required attribute value, to avoid false matches on common tags such as
       <TD> or <DIV>.

       Call withAttribute with a series of attribute names and values. Specify the list
       of filter attributes names and values as:
        - keyword arguments, as in (class="Customer",align="right"), or
        - a list of name-value tuples, as in ( ("ns1:class", "Customer"), ("ns2:align","right") )
       For attribute names with a namespace prefix, you must use the second form.  Attribute
       names are matched insensitive to upper/lower case.

       To verify that the attribute exists, but without specifying a value, pass
       withAttribute.ANY_VALUE as the value.
       """
    if args:
        attrs = args[:]
    else:
        attrs = attrDict.items()
    attrs = [(k,v) for k,v in attrs]
    def pa(s,l,tokens):
        for attrName,attrValue in attrs:
            if attrName not in tokens:
                raise ParseException(s,l,"no matching attribute " + attrName)
            if attrValue != withAttribute.ANY_VALUE and tokens[attrName] != attrValue:
                raise ParseException(s,l,"attribute '%s' has value '%s', must be '%s'" %
                                            (attrName, tokens[attrName], attrValue))
    return pa
withAttribute.ANY_VALUE = object()

opAssoc = _Constants()
opAssoc.LEFT = object()
opAssoc.RIGHT = object()

def operatorPrecedence( baseExpr, opList ):
    """Helper method for constructing grammars of expressions made up of
       operators working in a precedence hierarchy.  Operators may be unary or
       binary, left- or right-associative.  Parse actions can also be attached
       to operator expressions.

       Parameters:
        - baseExpr - expression representing the most basic element for the nested
        - opList - list of tuples, one for each operator precedence level in the
          expression grammar; each tuple is of the form
          (opExpr, numTerms, rightLeftAssoc, parseAction), where:
           - opExpr is the pyparsing expression for the operator;
              may also be a string, which will be converted to a Literal;
              if numTerms is 3, opExpr is a tuple of two expressions, for the
              two operators separating the 3 terms
           - numTerms is the number of terms for this operator (must
              be 1, 2, or 3)
           - rightLeftAssoc is the indicator whether the operator is
              right or left associative, using the pyparsing-defined
              constants opAssoc.RIGHT and opAssoc.LEFT.
           - parseAction is the parse action to be associated with
              expressions matching this operator expression (the
              parse action tuple member may be omitted)
    """
    ret = Forward()
    lastExpr = baseExpr | ( Suppress('(') + ret + Suppress(')') )
    for i,operDef in enumerate(opList):
        opExpr,arity,rightLeftAssoc,pa = (operDef + (None,))[:4]
        if arity == 3:
            if opExpr is None or len(opExpr) != 2:
                raise ValueError("if numterms=3, opExpr must be a tuple or list of two expressions")
            opExpr1, opExpr2 = opExpr
        thisExpr = Forward()#.setName("expr%d" % i)
        if rightLeftAssoc == opAssoc.LEFT:
            if arity == 1:
                matchExpr = FollowedBy(lastExpr + opExpr) + Group( lastExpr + OneOrMore( opExpr ) )
            elif arity == 2:
                if opExpr is not None:
                    matchExpr = FollowedBy(lastExpr + opExpr + lastExpr) + Group( lastExpr + OneOrMore( opExpr + lastExpr ) )
                else:
                    matchExpr = FollowedBy(lastExpr+lastExpr) + Group( lastExpr + OneOrMore(lastExpr) )
            elif arity == 3:
                matchExpr = FollowedBy(lastExpr + opExpr1 + lastExpr + opExpr2 + lastExpr) + \
                            Group( lastExpr + opExpr1 + lastExpr + opExpr2 + lastExpr )
            else:
                raise ValueError("operator must be unary (1), binary (2), or ternary (3)")
        elif rightLeftAssoc == opAssoc.RIGHT:
            if arity == 1:
                # try to avoid LR with this extra test
                if not isinstance(opExpr, Optional):
                    opExpr = Optional(opExpr)
                matchExpr = FollowedBy(opExpr.expr + thisExpr) + Group( opExpr + thisExpr )
            elif arity == 2:
                if opExpr is not None:
                    matchExpr = FollowedBy(lastExpr + opExpr + thisExpr) + Group( lastExpr + OneOrMore( opExpr + thisExpr ) )
                else:
                    matchExpr = FollowedBy(lastExpr + thisExpr) + Group( lastExpr + OneOrMore( thisExpr ) )
            elif arity == 3:
                matchExpr = FollowedBy(lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr) + \
                            Group( lastExpr + opExpr1 + thisExpr + opExpr2 + thisExpr )
            else:
                raise ValueError("operator must be unary (1), binary (2), or ternary (3)")
        else:
            raise ValueError("operator must indicate right or left associativity")
        if pa:
            matchExpr.setParseAction( pa )
        thisExpr << ( matchExpr | lastExpr )
        lastExpr = thisExpr
    ret << lastExpr
    return ret

dblQuotedString = Regex(r'"(?:[^"\n\r\\]|(?:"")|(?:\\x[0-9a-fA-F]+)|(?:\\.))*"').setName("string enclosed in double quotes")
sglQuotedString = Regex(r"'(?:[^'\n\r\\]|(?:'')|(?:\\x[0-9a-fA-F]+)|(?:\\.))*'").setName("string enclosed in single quotes")
quotedString = Regex(r'''(?:"(?:[^"\n\r\\]|(?:"")|(?:\\x[0-9a-fA-F]+)|(?:\\.))*")|(?:'(?:[^'\n\r\\]|(?:'')|(?:\\x[0-9a-fA-F]+)|(?:\\.))*')''').setName("quotedString using single or double quotes")
unicodeString = Combine(_L('u') + quotedString.copy())

def nestedExpr(opener="(", closer=")", content=None, ignoreExpr=quotedString):
    """Helper method for defining nested lists enclosed in opening and closing
       delimiters ("(" and ")" are the default).

       Parameters:
        - opener - opening character for a nested list (default="("); can also be a pyparsing expression
        - closer - closing character for a nested list (default=")"); can also be a pyparsing expression
        - content - expression for items within the nested lists (default=None)
        - ignoreExpr - expression for ignoring opening and closing delimiters (default=quotedString)

       If an expression is not provided for the content argument, the nested
       expression will capture all whitespace-delimited content between delimiters
       as a list of separate values.

       Use the ignoreExpr argument to define expressions that may contain
       opening or closing characters that should not be treated as opening
       or closing characters for nesting, such as quotedString or a comment
       expression.  Specify multiple expressions using an Or or MatchFirst.
       The default is quotedString, but if no expressions are to be ignored,
       then pass None for this argument.
    """
    if opener == closer:
        raise ValueError("opening and closing strings cannot be the same")
    if content is None:
        if isinstance(opener,basestring) and isinstance(closer,basestring):
            if len(opener) == 1 and len(closer)==1:
                if ignoreExpr is not None:
                    content = (Combine(OneOrMore(~ignoreExpr +
                                    CharsNotIn(opener+closer+ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
                else:
                    content = (empty+CharsNotIn(opener+closer+ParserElement.DEFAULT_WHITE_CHARS
                                ).setParseAction(lambda t:t[0].strip()))
            else:
                if ignoreExpr is not None:
                    content = (Combine(OneOrMore(~ignoreExpr + 
                                    ~Literal(opener) + ~Literal(closer) +
                                    CharsNotIn(ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
                else:
                    content = (Combine(OneOrMore(~Literal(opener) + ~Literal(closer) +
                                    CharsNotIn(ParserElement.DEFAULT_WHITE_CHARS,exact=1))
                                ).setParseAction(lambda t:t[0].strip()))
        else:
            raise ValueError("opening and closing arguments must be strings if no content expression is given")
    ret = Forward()
    if ignoreExpr is not None:
        ret << Group( Suppress(opener) + ZeroOrMore( ignoreExpr | ret | content ) + Suppress(closer) )
    else:
        ret << Group( Suppress(opener) + ZeroOrMore( ret | content )  + Suppress(closer) )
    return ret

def indentedBlock(blockStatementExpr, indentStack, indent=True):
    """Helper method for defining space-delimited indentation blocks, such as
       those used to define block statements in Python source code.

       Parameters:
        - blockStatementExpr - expression defining syntax of statement that
            is repeated within the indented block
        - indentStack - list created by caller to manage indentation stack
            (multiple statemensearchhIndentedBlock expressions within a single grammar
            should share a common indentStack)
        - indent - boolean indicating whether block must be indented beyond the
            the current level; set to False for block of left-most statements
            (default=True)

       A valid block must contain at least one blockStatement.
    """
    def checkPeerIndent(s,l,t):
        if l >= len(s): return
        curCol = col(l,s)
        if curCol != indentStack[-1]:
            if curCol > indentStack[-1]:
                raise ParseFatalException(s,l,"illegal nesting")
            raise ParseException(s,l,"not a peer entry")

    def checkSubIndent(s,l,t):
        curCol = col(l,s)
        if curCol > indentStack[-1]:
            indentStack.append( curCol )
        else:
            raise ParseException(s,l,"not a subentry")

    def checkUnindent(s,l,t):
        if l >= len(s): return
        curCol = col(l,s)
        if not(indentStack and curCol < indentStack[-1] and curCol <= indentStack[-2]):
            raise ParseException(s,l,"not an unindent")
        indentStack.pop()

    NL = OneOrMore(LineEnd().setWhitespaceChars("\t ").suppress())
    INDENT = Empty() + Empty().setParseAction(checkSubIndent)
    PEER   = Empty().setParseAction(checkPeerIndent)
    UNDENT = Empty().setParseAction(checkUnindent)
    if indent:
        smExpr = Group( Optional(NL) +
            FollowedBy(blockStatementExpr) +
            INDENT + (OneOrMore( PEER + Group(blockStatementExpr) + Optional(NL) )) + UNDENT)
    else:
        smExpr = Group( Optional(NL) +
            (OneOrMore( PEER + Group(blockStatementExpr) + Optional(NL) )) )
    blockStatementExpr.ignore(_bslash + LineEnd())
    return smExpr

alphas8bit = srange(r"[\0xc0-\0xd6\0xd8-\0xf6\0xf8-\0xff]")
punc8bit = srange(r"[\0xa1-\0xbf\0xd7\0xf7]")

anyOpenTag,anyCloseTag = makeHTMLTags(Word(alphas,alphanums+"_:"))
commonHTMLEntity = Combine(_L("&") + oneOf("gt lt amp nbsp quot").setResultsName("entity") +";")
_htmlEntityMap = dict(zip("gt lt amp nbsp quot".split(),'><& "'))
replaceHTMLEntity = lambda t : t.entity in _htmlEntityMap and _htmlEntityMap[t.entity] or None

# it's easy to get these comment structures wrong - they're very common, so may as well make them available
cStyleComment = Regex(r"/\*(?:[^*]*\*+)+?/").setName("C style comment")

htmlComment = Regex(r"<!--[\s\S]*?-->")
restOfLine = Regex(r".*").leaveWhitespace()
dblSlashComment = Regex(r"\/\/(\\\n|.)*").setName("// comment")
cppStyleComment = Regex(r"/(?:\*(?:[^*]*\*+)+?/|/[^\n]*(?:\n[^\n]*)*?(?:(?<!\\)|\Z))").setName("C++ style comment")

javaStyleComment = cppStyleComment
pythonStyleComment = Regex(r"#.*").setName("Python style comment")
_noncomma = "".join( [ c for c in printables if c != "," ] )
_commasepitem = Combine(OneOrMore(Word(_noncomma) +
                                  Optional( Word(" \t") +
                                            ~Literal(",") + ~LineEnd() ) ) ).streamline().setName("commaItem")
commaSeparatedList = delimitedList( Optional( quotedString | _commasepitem, default="") ).setName("commaSeparatedList")


if __name__ == "__main__":

    def test( teststring ):
        try:
            tokens = simpleSQL.parseString( teststring )
            tokenlist = tokens.asList()
            print (teststring + "->"   + str(tokenlist))
            print ("tokens = "         + str(tokens))
            print ("tokens.columns = " + str(tokens.columns))
            print ("tokens.tables = "  + str(tokens.tables))
            print (tokens.asXML("SQL",True))
        except ParseBaseException,err:
            print (teststring + "->")
            print (err.line)
            print (" "*(err.column-1) + "^")
            print (err)
        print()

    selectToken    = CaselessLiteral( "select" )
    fromToken      = CaselessLiteral( "from" )

    ident          = Word( alphas, alphanums + "_$" )
    columnName     = delimitedList( ident, ".", combine=True ).setParseAction( upcaseTokens )
    columnNameList = Group( delimitedList( columnName ) )#.setName("columns")
    tableName      = delimitedList( ident, ".", combine=True ).setParseAction( upcaseTokens )
    tableNameList  = Group( delimitedList( tableName ) )#.setName("tables")
    simpleSQL      = ( selectToken + \
                     ( '*' | columnNameList ).setResultsName( "columns" ) + \
                     fromToken + \
                     tableNameList.setResultsName( "tables" ) )

    test( "SELECT * from XYZZY, ABC" )
    test( "select * from SYS.XYZZY" )
    test( "Select A from Sys.dual" )
    test( "Select AA,BB,CC from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Select A, B, C from Sys.dual" )
    test( "Xelect A, B, C from Sys.dual" )
    test( "Select A, B, C frox Sys.dual" )
    test( "Select" )
    test( "Select ^^^ frox Sys.dual" )
    test( "Select A, B, C from Sys.dual, Table2   " )

########NEW FILE########
__FILENAME__ = tables
#===============================================================================
# Copyright 2008 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""
Generic storage classes for creating static files that support
FAST key-value (Table*) and key-value-postings (PostingTable*) storage.

These objects require that you add rows in increasing order of their
keys. They will raise an exception you try to add keys out-of-order.

These objects use a simple file format. The first 4 bytes are an unsigned
long ("!L" struct) pointing to the directory data.
The next 4 bytes are a pointer to the posting data, if any. In a table without
postings, this is 0.
Following that are N pickled objects (the blocks of rows).
Following the objects is the directory, which is a pickled list of
(key, filepos) pairs. Because the keys are pickled as part of the directory,
they can be any pickle-able object. (The keys must also be hashable because
they are used as dictionary keys. It's best to use value types for the
keys: tuples, numbers, and/or strings.)

This module also contains simple implementations for writing and reading
static "Record" files made up of fixed-length records based on the
struct module.
"""

import shutil, tempfile
from array import array
from bisect import bisect_left, bisect_right
from marshal import loads
from marshal import dumps

try:
    from zlib import compress, decompress
    has_zlib = True
except ImportError:
    has_zlib = False

from whoosh.structfile import _USHORT_SIZE, StructFile

# Utility functions

def copy_data(treader, inkey, twriter, outkey, postings = False, buffersize = 32 * 1024):
    """
    Copies the data associated with the key from the
    "reader" table to the "writer" table, along with the
    raw postings if postings = True.
    """
    
    if postings:
        (offset, length), postcount, data = treader._get(inkey)
        super(twriter.__class__, twriter).add_row(outkey, ((twriter.offset, length), postcount, data))
        
        # Copy the raw posting data
        infile = treader.table_file
        infile.seek(treader.postpos + offset)
        outfile = twriter.posting_file
        if length <= buffersize:
            outfile.write(infile.read(length))
        else:
            sofar = 0
            while sofar < length:
                readsize = min(buffersize, length - sofar)
                outfile.write(infile.read(readsize))
                sofar += readsize
        
        twriter.offset = outfile.tell()
    else:
        twriter.add_row(outkey, treader[inkey])


# Table writer classes

class TableWriter(object):
    def __init__(self, table_file, blocksize = 16 * 1024,
                 compressed = 0, prefixcoding = False,
                 postings = False, stringids = False,
                 checksize = True):
        self.table_file = table_file
        self.blocksize = blocksize
        
        if compressed > 0 and not has_zlib:
            raise Exception("zlib is not available: cannot compress table")
        self.compressed = compressed
        self.prefixcoding = prefixcoding
        
        self.haspostings = postings
        if postings:
            self.offset = 0
            self.postcount = 0
            self.lastpostid = None
            self.stringids = stringids
            self.posting_file = StructFile(tempfile.TemporaryFile())
        
        self.rowbuffer = []
        self.lastkey = None
        self.blockfilled = 0
        
        self.keys = []
        self.pointers = array("L")
        
        # Remember where we started writing
        self.start = table_file.tell()
        # Save space for a pointer to the directory
        table_file.write_ulong(0)
        # Save space for a pointer to the postings
        table_file.write_ulong(0)
        
        self.options = {"haspostings": postings,
                        "compressed": compressed,
                        "prefixcoding": prefixcoding,
                        "stringids": stringids}
    
    def close(self):
        # If there is still a block waiting to be written, flush it out
        if self.rowbuffer:
            self._write_block()
        
        tf = self.table_file
        haspostings = self.haspostings
        
        # Remember where we started writing the directory
        dirpos = tf.tell()
        # Write the directory
        tf.write_pickle(self.keys)
        tf.write_array(self.pointers)
        tf.write_pickle(self.options)
        
        if haspostings:
            # Remember where we started the postings
            postpos = tf.tell()
            # Seek back to the beginning of the postings and
            # copy them onto the end of the table file.
            self.posting_file.seek(0)
            shutil.copyfileobj(self.posting_file, tf)
            self.posting_file.close()
        
        # Seek back to where we started writing and write a
        # pointer to the directory
        tf.seek(self.start)
        tf.write_ulong(dirpos)
        
        if haspostings:
            # Write a pointer to the postings
            tf.write_ulong(postpos)
        
        tf.close()
    
    def _write_block(self):
        buf = self.rowbuffer
        key = buf[0][0]
        compressed = self.compressed
        
        self.keys.append(key)
        self.pointers.append(self.table_file.tell())
        if compressed:
            pck = dumps(buf)
            self.table_file.write_string(compress(pck, compressed))
        else:
            self.table_file.write_pickle(buf)
        
        self.rowbuffer = []
        self.blockfilled = 0
    
    def write_posting(self, id, data, writefn):
        # IDs must be added in increasing order
        if id <= self.lastpostid:
            raise IndexError("IDs must increase: %r..%r" % (self.lastpostid, id))
        
        pf = self.posting_file
        if self.stringids:
            pf.write_string(id.encode("utf8"))
        else:
            lastpostid = self.lastpostid or 0
            pf.write_varint(id - lastpostid)
        
        self.lastpostid = id
        self.postcount += 1
        
        return writefn(pf, data)
    
    def add_row(self, key, data):
        # Note: call this AFTER you add any postings!
        # Keys must be added in increasing order
        if key <= self.lastkey:
            raise IndexError("Keys must increase: %r..%r" % (self.lastkey, key))
        
        rb = self.rowbuffer
        
        if isinstance(data, array):
            self.blockfilled += len(data) * data.itemsize
        else:
            # Ugh! We're pickling twice! At least it's fast.
            self.blockfilled += len(dumps(data))
        self.lastkey = key
        
        if self.haspostings:
            # Add the posting info to the stored row data
            endoffset = self.posting_file.tell()
            length = endoffset - self.offset
            rb.append((key, (self.offset, length, self.postcount, data)))
            
            # Reset the posting variables
            self.offset = endoffset
            self.postcount = 0
            self.lastpostid = None
        else:
            rb.append((key, data))
        
        # If this row filled up a block, flush it out
        if self.blockfilled >= self.blocksize:
            #print len(rb)
            self._write_block()


# Table reader classes

class TableReader(object):
    def __init__(self, table_file):
        self.table_file = table_file
        
        # Read the pointer to the directory
        dirpos = table_file.read_ulong()
        # Read the pointer to the postings (0 if there are no postings)
        self.postpos = table_file.read_ulong()
        
        # Seek to where the directory begins and read it
        table_file.seek(dirpos)
        self.blockindex = table_file.read_pickle()
        self.blockcount = len(self.blockindex)
        self.blockpositions = table_file.read_array("L", self.blockcount)
        options = table_file.read_pickle()
        self.__dict__.update(options)
        
        if self.compressed > 0 and not has_zlib:
            raise Exception("zlib is not available: cannot decompress table")
        
        # Initialize cached block
        self.currentblock = None
        self.itemlist = None
        self.itemdict = None
        
        if self.haspostings:
            if self.stringids:
                self._read_id = self._read_id_string
            else:
                self._read_id = self._read_id_varint
            self.get = self._get_ignore_postinfo
        else:
            self.get = self._get_plain
    
    def __contains__(self, key):
        if key < self.blockindex[0]:
            return False
        self._load_block(key)
        return key in self.itemdict
    
    def _get_ignore_postinfo(self, key):
        self._load_block(key)
        return self.itemdict[key][3]
    
    def _get_plain(self, key):
        self._load_block(key)
        return self.itemdict[key]
    
    def __iter__(self):
        if self.haspostings:
            for i in xrange(0, self.blockcount):
                self._load_block_num(i)
                for key, value in self.itemlist:
                    yield (key, value[3])
        else:
            for i in xrange(0, self.blockcount):
                self._load_block_num(i)
                for key, value in self.itemlist:
                    yield (key, value)
    
    def _read_id_varint(self, lastid):
        return lastid + self.table_file.read_varint()
    
    def _read_id_string(self, lastid):
        return self.table_file.read_string().decode("utf8")
    
    def iter_from(self, key):
        postings = self.haspostings
        
        self._load_block(key)
        blockcount = self.blockcount
        itemlist = self.itemlist
        
        p = bisect_left(itemlist, (key, None))
        if p >= len(itemlist):
            if self.currentblock >= blockcount - 1:
                return
            self._load_block_num(self.currentblock + 1)
            itemlist = self.itemlist
            p = 0
        
        # Yield the rest of the rows
        while True:
            kv = itemlist[p]
            if postings:
                yield (kv[0], kv[1][3])
            else:
                yield kv
            
            p += 1
            if p >= len(itemlist):
                if self.currentblock >= blockcount - 1:
                    return
                self._load_block_num(self.currentblock + 1)
                itemlist = self.itemlist
                p = 0
    
    def close(self):
        self.table_file.close()
    
    def keys(self):
        return (key for key, _ in self)
    
    def values(self):
        return (value for _, value in self)
    
    def posting_count(self, key):
        if not self.haspostings: raise Exception("This table does not have postings")
        return self._get_plain(key)[2]
    
    def postings(self, key, readfn):
        postfile = self.table_file
        _read_id = self._read_id
        id = 0
        for _ in xrange(0, self._seek_postings(key)):
            id = _read_id(id)
            yield (id, readfn(postfile))
    
    def _load_block_num(self, bn):
        blockcount = len(self.blockindex)
        if bn < 0 or bn >= blockcount:
            raise ValueError("Block number %s/%s" % (bn, blockcount))
        
        pos = self.blockpositions[bn]
        self.table_file.seek(pos)
        
        # Sooooooo sloooooow...
        if self.compressed:
            pck = self.table_file.read_string()
            itemlist = loads(decompress(pck))
        else:
            itemlist = self.table_file.read_pickle()
        
        self.itemlist = itemlist
        self.itemdict = dict(itemlist)
        self.currentblock = bn
        self.minkey = itemlist[0][0]
        self.maxkey = itemlist[-1][0]
    
    def _load_block(self, key):
        if self.currentblock is None or key < self.minkey or key > self.maxkey:
            bn = max(0, bisect_right(self.blockindex, key) - 1)
            self._load_block_num(bn)

    def _seek_postings(self, key):
        offset, length, count = self._get_plain(key)[:3] #@UnusedVariable
        self.table_file.seek(self.postpos + offset)
        return count


# An array table only stores numeric arrays and does not support postings.

class ArrayWriter(object):
    def __init__(self, table_file, typecode, bufferlength=4*1024):
        if typecode not in table_file._type_writers:
            raise Exception("Can't (yet) write an array table of type %r" % typecode)
        
        self.table_file = table_file
        self.typecode = typecode
        self.bufferlength = bufferlength
        self.dir = {}
        self.buffer = array(typecode)
        
        # Remember where we started writing
        self.start = table_file.tell()
        # Save space for a pointer to the directory
        table_file.write_ulong(0)
    
    def _flush(self):
        buff = self.buffer
        if buff:
            self.table_file.write_array(buff)
        self.buffer = array(self.typecode)
    
    def close(self):
        self._flush()
        tf = self.table_file
        
        # Remember where we started writing the directory
        dirpos = tf.tell()
        # Write the directory
        tf.write_pickle((self.typecode, self.dir))
        
        # Seek back to where we started writing and write a
        # pointer to the directory
        tf.seek(self.start)
        tf.write_ulong(dirpos)
        
        tf.close()
        
    def add_row(self, key, values = None):
        self._flush()
        self.dir[key] = self.table_file.tell()
        if values:
            self.extend(values)
        
    def append(self, value):
        buff = self.buffer
        buff.append(value)
        if len(buff) > self.bufferlength:
            self._flush()
            
    def extend(self, values):
        buff = self.buffer
        buff.extend(values)
        if len(buff) > self.bufferlength:
            self._flush()
            
    def from_file(self, fobj):
        self._flush()
        shutil.copyfileobj(fobj, self.table_file)


class ArrayReader(object):
    def __init__(self, table_file):
        self.table_file = table_file
        
        # Read the pointer to the directory
        dirpos = table_file.read_ulong()
        # Seek to where the directory begins and read it
        table_file.seek(dirpos)
        typecode, self.dir = table_file.read_pickle()
        
        # Set the "read()" method of this object to the appropriate
        # read method of the underlying StructFile for the table's
        # data type.
        try:
            self.read = self.table_file._type_readers[typecode]
        except KeyError:
            raise Exception("Can't (yet) read an array table of type %r" % self.typecode)
        
        self.typecode = typecode
        self.itemsize = array(typecode).itemsize
    
    def __contains__(self, key):
        return key in self.dir
    
    def get(self, key, offset):
        tf = self.table_file
        pos = self.dir[key]
        tf.seek(pos + offset * self.itemsize)
        return self.read()
    
    def close(self):
        self.table_file.close()
        
    def to_file(self, key, fobj):
        raise NotImplementedError


class RecordWriter(object):
    def __init__(self, table_file, typecode, length):
        self.table_file = table_file
        self.typecode = typecode
        self.length = length
        
        table_file.write(typecode[0])
        table_file.write_ushort(length)
    
    def close(self):
        self.table_file.close()
        
    def append(self, arry):
        assert arry.typecode == self.typecode
        assert len(arry) == self.length
        self.table_file.write_array(arry)
        

class RecordReader(object):
    def __init__(self, table_file):
        self.table_file = table_file
        self.typecode = table_file.read(1)
        
        try:
            self.read = self.table_file._type_readers[self.typecode]
        except KeyError:
            raise Exception("Can't (yet) read an array table of type %r" % self.typecode)
        
        self.length = table_file.read_ushort()
        self.itemsize = array(self.typecode).itemsize
        self.recordsize = self.length * self.itemsize
    
    def close(self):
        self.table_file.close()
    
    def get(self, recordnum, itemnum):
        assert itemnum < self.length
        self.table_file.seek(1 + _USHORT_SIZE +\
                             recordnum * self.recordsize +\
                             itemnum * self.itemsize)
        return self.read()
    
    def get_record(self, recordnum):
        tf = self.table_file
        tf.seek(1 + _USHORT_SIZE + recordnum * self.recordsize)
        return tf.read_array(self.typecode, self.length)


class StringListWriter(object):
    def __init__(self, table_file, listlength):
        self.table_file = table_file
        self.listlength = listlength
        self.positions = array("L")
        
        table_file.write_ulong(0)
    
    def close(self):
        tf = self.table_file
        directory_pos = tf.tell()
        tf.write_array(self.positions)
        tf.seek(0)
        tf.write_ulong(directory_pos)
        tf.close()
    
    def append(self, ustrings):
        assert len(ustrings) == self.listlength
        tf = self.table_file
        
        self.positions.append(tf.tell())
        
        encoded = [ustring.encode("utf8") for ustring in ustrings]
        lenarray = array("I", (len(s) for s in encoded))
        tf.write_array(lenarray)
        tf.write("".join(encoded))
        

class StringListReader(object):
    def __init__(self, table_file, listlength, size):
        self.table_file = table_file
        self.listlength = listlength
        self.size = size
        
        self.positions = table_file.read_array("L", size)
        
    def close(self):
        self.table_file.close()
    
    def get(self, num):
        tf = self.table_file
        listlength = self.listlength
        
        tf.seek(self.positions[num])
        lens = tf.read_array("I", listlength)
        string = tf.read(sum(lens))
        
        p = 0
        decoded = []
        for ln in lens:
            decoded.append(string[p:p+ln].decode("utf8"))
            p += ln
        return decoded


if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = util
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""
Miscellaneous utility functions and classes.
"""

from functools import wraps
from heapq import heappush, heapreplace

from whoosh.support.bitvector import BitVector

# Functions

_fib_cache = {}
def fib(n):
    """Returns the nth value in the Fibonacci sequence."""
    
    if n <= 2: return n
    if n in _fib_cache: return _fib_cache[n]
    result = fib(n - 1) + fib(n - 2)
    _fib_cache[n] = result
    return result

def permute(ls):
    """Yields all permutations of a list."""
    
    if len(ls) == 1:
        yield ls
    else:
        for i in range(len(ls)):
            this = ls[i]
            rest = ls[:i] + ls[i+1:]
            for p in permute(rest):
                yield [this] + p

def first_diff(a, b):
    """Returns the position of the first differing character in the strings
    a and b. For example, first_diff('render', 'rending') == 4. This
    function limits the return value to 255 so the difference can be encoded
    in a single byte.
    """
    
    i = -1
    for i in xrange(0, len(a)):
        if a[i] != b[1]:
            return i
        if i == 255: return i
    return i + 1

def prefix_encode(a, b):
    """Compresses string b as an integer (encoded in a byte) representing
    the prefix it shares with a, followed by the suffix encoded as UTF-8.
    """
    i = first_diff(a, b)
    return chr(i) + b[i:].encode("utf8")

def prefix_encode_all(ls):
    """Compresses the given list of (unicode) strings by storing each string
    (except the first one) as an integer (encoded in a byte) representing
    the prefix it shares with its predecessor, followed by the suffix encoded
    as UTF-8.
    """
    
    last = u''
    for w in ls:
        i = first_diff(last, w)
        yield chr(i) + w[i:].encode("utf8")
        last = w
        
def prefix_decode_all(ls):
    """Decompresses a list of strings compressed by prefix_encode().
    """
    
    last = u''
    for w in ls:
        i = ord(w[0])
        decoded = last[:i] + w[1:].decode("utf8")
        yield decoded
        last = decoded


# Classes

class TopDocs(object):
    """This is like a list that only remembers the top N values that are added
    to it. This increases efficiency when you only want the top N values, since
    you don't have to sort most of the values (once the object reaches capacity
    and the next item to consider has a lower score than the lowest item in the
    collection, you can just throw it away).
    
    The reason we use this instead of heapq.nlargest is this object keeps
    track of all docnums that were added, even if they're not in the "top N".
    """
    
    def __init__(self, capacity, max_doc, docvector = None):
        self.capacity = capacity
        self.docs = docvector or BitVector(max_doc)
        self.heap = []
        self._total = 0

    def __len__(self):
        return len(self.sorted)

    def add_all(self, sequence):
        heap = self.heap
        docs = self.docs
        capacity = self.capacity
        
        subtotal = 0
        for docnum, score in sequence:
            docs.set(docnum)
            subtotal += 1
            
            if len(heap) >= capacity:
                if score <= heap[0][0]:
                    continue
                else:
                    heapreplace(heap, (score, docnum))
            else:
                heappush(heap, (score, docnum))
        
        self._total += subtotal

    def total(self):
        return self._total

    def best(self):
        """
        Returns the "top N" items. Note that this call
        involves sorting and reversing the internal queue, so you may
        want to cache the results rather than calling this method
        multiple times.
        """
        
        # Throw away the score and just return a list of items
        return [(item, score) for score, item in reversed(sorted(self.heap))]
    

# Mix-in for objects with a close() method that allows them to be
# used as a context manager.

class ClosableMixin(object):
    """Mix-in for classes with a close() method to allow them to be
    used as a context manager.
    """
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc_info):
        self.close()


def protected(func):
    """Decorator for storage-access methods. This decorator
    (a) checks if the object has already been closed, and
    (b) synchronizes on a threading lock. The parent object must
    have 'is_closed' and '_sync_lock' attributes.
    """
    
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.is_closed:
            raise Exception("This object has been closed")
        if self._sync_lock.acquire(False):
            try:
                return func(self, *args, **kwargs)
            finally:
                self._sync_lock.release()
        else:
            raise Exception("Could not acquire sync lock")
    
    return wrapper

########NEW FILE########
__FILENAME__ = writing
#===============================================================================
# Copyright 2007 Matt Chaput
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#===============================================================================

"""
This module contains classes for writing to an index.
"""

from array import array
from collections import defaultdict
from tempfile import TemporaryFile

from whoosh import index, postpool, reading, structfile, tables
from whoosh.fields import UnknownFieldError
from whoosh.util import fib

# Exceptions

class IndexingError(Exception):
    pass


DOCLENGTH_TYPE = "H"
DOCLENGTH_LIMIT = 2**16-1


# Merge policies

# A merge policy is a callable that takes the Index object,
# the SegmentWriter object, and the current SegmentSet
# (not including the segment being written), and returns an
# updated SegmentSet (not including the segment being
# written).

def NO_MERGE(ix, writer, segments):
    """This policy does not merge any existing segments.
    """
    return segments


def MERGE_SMALL(ix, writer, segments):
    """This policy merges small segments, where small is
    defined using a heuristic based on the fibonacci sequence.
    """
    
    newsegments = index.SegmentSet()
    sorted_segment_list = sorted((s.doc_count_all(), s) for s in segments)
    total_docs = 0
    for i, (count, seg) in enumerate(sorted_segment_list):
        if count > 0:
            total_docs += count
            if total_docs < fib(i + 5):
                writer.add_segment(ix, seg)
            else:
                newsegments.append(seg)
    return newsegments


def OPTIMIZE(ix, writer, segments):
    """This policy merges all existing segments.
    """
    for seg in segments:
        writer.add_segment(ix, seg)
    return index.SegmentSet()


# Writing classes

class IndexWriter(index.DeletionMixin):
    """High-level object for writing to an index. This object takes care of
    instantiating a SegmentWriter to create a new segment as you add documents,
    as well as merging existing segments (if necessary) when you finish.
    
    You can use this object as a context manager. If an exception is thrown
    from within the context it calls cancel(), otherwise it calls commit()
    when the context ends.
    """
    
    # This class is mostly a shell for SegmentWriter. It exists to handle
    # multiple SegmentWriters during merging/optimizing.
    
    def __init__(self, ix, postlimit = 4 * 1024 * 1024,
                 term_blocksize = 1 * 1024, doc_blocksize = 8 * 1024,
                 vector_blocksize = 8 * 1024):
        """
        :ix: the Index object you want to write to.
        :blocksize: the block size for tables created by this writer.
        """
        
        # Obtain a lock
        self.locked = ix.lock()
        
        self.index = ix
        self.segments = ix.segments.copy()
        self.postlimit = postlimit
        self.term_blocksize = term_blocksize
        self.doc_blocksize = doc_blocksize
        self.vector_blocksize = vector_blocksize
        self._segment_writer = None
        self._searcher = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.cancel()
        else:
            self.commit()
    
    def _finish(self):
        self._close_searcher()
        self._segment_writer = None
        # Release the lock
        if self.locked:
            self.index.unlock()
    
    def segment_writer(self):
        """Returns the underlying SegmentWriter object."""
        
        if not self._segment_writer:
            self._segment_writer = SegmentWriter(self.index, self.postlimit,
                                                 self.term_blocksize,
                                                 self.doc_blocksize, self.vector_blocksize)
        return self._segment_writer
    
    def searcher(self):
        """Returns a searcher for the existing index."""
        if not self._searcher:
            self._searcher = self.index.searcher()
        return self._searcher
    
    def _close_searcher(self):
        if self._searcher:
            self._searcher.close()
            self._searcher = None
    
    def start_document(self):
        """Starts recording information for a new document. This should be followed by
        add_field() calls, and must be followed by an end_document() call.
        Alternatively you can use add_document() to add all fields at once.
        """
        self.segment_writer().start_document()
        
    def add_field(self, fieldname, text, stored_value = None):
        """Adds a the value of a field to the document opened with start_document().
        
        :fieldname: The name of the field in which to index/store the text.
        :text: The unicode text to index.
        """
        self.segment_writer().add_field(fieldname, text, stored_value = stored_value)
        
    def end_document(self):
        """
        Closes a document opened with start_document().
        """
        self.segment_writer().end_document()
    
    def add_document(self, **fields):
        """Adds all the fields of a document at once. This is an alternative to calling
        start_document(), add_field() [...], end_document().
        
        The keyword arguments map field names to the values to index/store.
        
        For fields that are both indexed and stored, you can specify an alternate
        value to store using a keyword argument in the form "_stored_<fieldname>".
        For example, if you have a field named "title" and you want to index the
        text "a b c" but store the text "e f g", use keyword arguments like this::
        
            add_document(title=u"a b c", _stored_title=u"e f g")
        """
        self.segment_writer().add_document(fields)
    
    def update_document(self, **fields):
        """Adds or replaces a document. At least one of the fields for which you
        supply values must be marked as 'unique' in the index's schema.
        
        The keyword arguments map field names to the values to index/store.
        
        For fields that are both indexed and stored, you can specify an alternate
        value to store using a keyword argument in the form "_stored_<fieldname>".
        For example, if you have a field named "title" and you want to index the
        text "a b c" but store the text "e f g", use keyword arguments like this::
        
            update_document(title=u"a b c", _stored_title=u"e f g")
        """
        
        # Check which of the supplied fields are unique
        unique_fields = [name for name, field
                         in self.index.schema.fields()
                         if name in fields and field.unique]
        if not unique_fields:
            raise IndexingError("None of the fields in %r are unique" % fields.keys())
        
        # Delete documents in which the supplied unique fields match
        s = self.searcher()
        for name in unique_fields:
            self.delete_by_term(name, fields[name])
        
        # Add the given fields
        self.add_document(**fields)
    
    def commit(self, mergetype = MERGE_SMALL):
        """Finishes writing and unlocks the index.
        
        :mergetype: How to merge existing segments. One of
            writing.NO_MERGE, writing.MERGE_SMALL, or writing.OPTIMIZE.
        """
        
        self._close_searcher()
        if self._segment_writer or mergetype is OPTIMIZE:
            self._merge_segments(mergetype)
        self.index.commit(self.segments)
        self._finish()
        
    def cancel(self):
        """Cancels any documents/deletions added by this object
        and unlocks the index.
        """
        self._finish()
    
    def _merge_segments(self, mergetype):
        sw = self.segment_writer()
        new_segments = mergetype(self.index, sw, self.segments)
        sw.close()
        new_segments.append(sw.segment())
        self.segments = new_segments


class SegmentWriter(object):
    """
    Do not instantiate this object directly; it is created by the IndexWriter object.
    
    Handles the actual writing of new documents to the index: writes stored fields,
    handles the posting pool, and writes out the term index.
    """
    
    class DocumentState(object):
        def __init__(self, scorable_fields):
            self._scorable_fields = scorable_fields
            self._fieldnum_to_pos = dict((fnum, i) for i, fnum in enumerate(scorable_fields))
            self.reset()
        
        def add_to_length(self, fieldnum, n):
            pos = self._fieldnum_to_pos[fieldnum]
            current = self.field_lengths[pos]
            if current >= DOCLENGTH_LIMIT: return
            self.field_lengths[pos] = min(current + n, DOCLENGTH_LIMIT)
        
        def reset(self):
            #: Whether a document is currently in progress
            self.active = False
            #: Maps field names to stored field contents for this document
            self.stored_fields = {}
            #: Keeps track of the last field that was added
            self.prev_fieldnum = None
            #: Keeps track of field lengths in this document
            self.field_lengths = array(DOCLENGTH_TYPE, [0] * len(self._scorable_fields))
    
    def __init__(self, ix, postlimit,
                 term_blocksize, doc_blocksize, vector_blocksize,
                 name = None):
        """
        :ix: the Index object in which to write the new segment.
        :postlimit: the maximum size for a run in the posting pool.
        :name: the name of the segment.
        :blocksize: the block size to use for tables created by this writer.
        """
        
        self.index = ix
        self.schema = ix.schema
        self.storage = ix.storage
        self.name = name or ix._next_segment_name()
        
        self.max_doc = 0
        self.max_weight = 0
        
        self.pool = postpool.PostingPool(limit = postlimit)
        self._scorable_fields = self.schema.scorable_fields()
        
        # Create a temporary segment object just so we can access
        # its *_filename attributes (so if we want to change the
        # naming convention, we only have to do it in one place).
        tempseg = index.Segment(self.name, 0, 0, None)
        
        # Open files for writing
        self.term_table = self.storage.create_table(tempseg.term_filename, postings = True,
                                                    blocksize = term_blocksize)
        
        self.doclength_table = self.storage.create_records(tempseg.doclen_filename,
                                                           DOCLENGTH_TYPE,
                                                           len(self._scorable_fields))
        
        self.docs_table = self.storage.create_table(tempseg.docs_filename,
                                                    blocksize = doc_blocksize, compressed = 9)
        
        self.vector_table = None
        if self.schema.has_vectored_fields():
            self.vector_table = self.storage.create_table(tempseg.vector_filename,
                                                          postings = True,
                                                          stringids = True,
                                                          blocksize = vector_blocksize)
        
        # Keep track of the total number of tokens (across all docs)
        # in each field
        self.field_length_totals = defaultdict(int)
        # Records the state of the writer's current document
        self._doc_state = SegmentWriter.DocumentState(self._scorable_fields)
            
    def segment(self):
        """Returns an index.Segment object for the segment being written."""
        return index.Segment(self.name, self.max_doc, self.max_weight,
                             dict(self.field_length_totals))
    
    def close(self):
        """Finishes writing the segment (flushes the posting pool out to disk) and
        closes all open files.
        """
        
        if self._doc_state.active:
            raise IndexingError("Called SegmentWriter.close() with a document still opened")
        
        self._flush_pool()
        
        self.doclength_table.close()
        
        self.docs_table.close()
        self.term_table.close()
        
        if self.vector_table:
            self.vector_table.close()
        
    def add_index(self, other_ix):
        """Adds the contents of another Index object to this segment.
        This currently does NO checking of whether the schemas match up.
        """
        
        for seg in other_ix.segments:
            self.add_segment(other_ix, seg)

    def add_segment(self, ix, segment):
        """Adds the contents of another segment to this one. This is used
        to merge existing segments into the new one before deleting them.
        
        :ix: The index.Index object containing the segment to merge.
        :segment: The index.Segment object to merge into this one.
        """
        
        start_doc = self.max_doc
        has_deletions = segment.has_deletions()
        
        if has_deletions:
            doc_map = {}
        
        # Merge document info
        docnum = 0
        schema = ix.schema
        
        doc_reader = reading.DocReader(ix.storage, segment, schema)
        try:
            vectored_fieldnums = ix.schema.vectored_fields()
            if vectored_fieldnums:
                doc_reader._open_vectors()
                inv = doc_reader.vector_table
                outv = self.vector_table
            
            ds = SegmentWriter.DocumentState(self._scorable_fields)
            for docnum in xrange(0, segment.max_doc):
                if not segment.is_deleted(docnum):
                    ds.stored_fields = doc_reader[docnum]
                    ds.field_lengths = doc_reader.doc_field_lengths(docnum)
                    
                    if has_deletions:
                        doc_map[docnum] = self.max_doc
                    
                    for fieldnum in vectored_fieldnums:
                        if (docnum, fieldnum) in inv:
                            tables.copy_data(inv, (docnum, fieldnum),
                                             outv, (self.max_doc, fieldnum),
                                             postings = True)
                    
                    self._write_doc_entry(ds)
                    self.max_doc += 1
                
                docnum += 1
        
            # Add field length totals
            for fieldnum, total in segment.field_length_totals.iteritems():
                self.field_length_totals[fieldnum] += total
        
        finally:
            doc_reader.close()
        
        # Merge terms
        term_reader = reading.TermReader(ix.storage, segment, ix.schema)
        try:
            for fieldnum, text, _, _ in term_reader:
                for docnum, data in term_reader.postings(fieldnum, text):
                    if has_deletions:
                        newdoc = doc_map[docnum]
                    else:
                        newdoc = start_doc + docnum
                    
                    self.pool.add_posting(fieldnum, text, newdoc, data)
        finally:
            term_reader.close()

    def start_document(self):
        ds = self._doc_state
        if ds.active:
            raise IndexingError("Called start_document() when a document was already opened")
        ds.active = True
        
    def end_document(self):
        ds = self._doc_state
        if not ds.active:
            raise IndexingError("Called end_document() when a document was not opened")
        
        self._write_doc_entry(ds)
        ds.reset()
        self.max_doc += 1

    def add_document(self, fields):
        self.start_document()
        fieldnames = [name for name in fields.keys() if not name.startswith("_")]
        
        schema = self.schema
        for name in fieldnames:
            if name not in schema:
                raise UnknownFieldError("There is no field named %r" % name)
        
        fieldnames.sort(key = schema.name_to_number)
        for name in fieldnames:
            value = fields.get(name)
            if value:
                self.add_field(name, value, stored_value = fields.get("_stored_%s" % name))
        self.end_document()
    
    def add_field(self, fieldname, value, stored_value = None,
                  start_pos = 0, start_char = 0, **kwargs):
        if value is None:
            return
        
        # Get the field information
        schema = self.schema
        if fieldname not in schema:
            raise UnknownFieldError("There is no field named %r" % fieldname)
        fieldnum = schema.name_to_number(fieldname)
        field = schema.field_by_name(fieldname)
        format = field.format
        
        # Check that the user added the fields in schema order
        docstate = self._doc_state
        if fieldnum < docstate.prev_fieldnum:
            raise IndexingError("Added field %r out of order (add fields in schema order)" % fieldname)
        docstate.prev_fieldnum = fieldnum

        # If the field is indexed, add the words in the value to the index
        if format.analyzer:
            if not isinstance(value, unicode):
                raise ValueError("%r in field %s is not unicode" % (value, fieldname))
            
            # Count of all terms in the value
            count = 0
            # Count of UNIQUE terms in the value
            unique = 0
            for w, freq, data in format.word_datas(value,
                                                   start_pos = start_pos, start_char = start_char,
                                                   **kwargs):
                assert w != ""
                self.pool.add_posting(fieldnum, w, self.max_doc, data)
                count += freq
                unique += 1
            
            # Add the term count to the total for this field
            self.field_length_totals[fieldnum] += count
            # Add the term count to the per-document field length
            if field.scorable:
                docstate.add_to_length(fieldnum, count)
        
        # If the field is vectored, add the words in the value to
        # the vector table
        vector = field.vector
        if vector:
            vtable = self.vector_table
            vdata = dict((w, data) for w, freq, data
                          in vector.word_datas(value,
                                               start_pos = start_pos, start_char = start_char,
                                               **kwargs))
            write_postvalue = vector.write_postvalue
            for word in sorted(vdata.keys()):
                vtable.write_posting(word, vdata[word], writefn = write_postvalue)
            vtable.add_row((self.max_doc, fieldnum), None)
        
        # If the field is stored, add the value to the doc state
        if field.stored:
            if stored_value is None: stored_value = value
            docstate.stored_fields[fieldname] = stored_value
        
    def _write_doc_entry(self, ds):
        docnum = self.max_doc
        self.doclength_table.append(ds.field_lengths)
        self.docs_table.add_row(docnum, ds.stored_fields)

    def _flush_pool(self):
        # This method pulls postings out of the posting pool (built up
        # as documents are added) and writes them to the posting file.
        # Each time it encounters a posting for a new term, it writes
        # the previous term to the term index (by waiting to write the
        # term entry, we can easily count the document frequency and
        # sum the terms by looking at the postings).
        
        term_table = self.term_table
        
        write_posting_method = None
        current_fieldnum = None # Field number of the current term
        current_text = None # Text of the current term
        first = True
        current_weight = 0
        
        # Loop through the postings in the pool.
        # Postings always come out of the pool in field number/alphabetic order.
        for fieldnum, text, docnum, data in self.pool:
            # If we're starting a new term, reset everything
            if write_posting_method is None or fieldnum > current_fieldnum or text > current_text:
                if fieldnum != current_fieldnum:
                    write_posting_method = self.schema.field_by_number(fieldnum).format.write_postvalue
                
                # If we've already written at least one posting, write the
                # previous term to the index.
                if not first:
                    term_table.add_row((current_fieldnum, current_text), current_weight)
                    
                    if current_weight > self.max_weight:
                        self.max_weight = current_weight
                
                # Reset term variables
                current_fieldnum = fieldnum
                current_text = text
                current_weight = 0
                first = False
            
            elif fieldnum < current_fieldnum or (fieldnum == current_fieldnum and text < current_text):
                # This should never happen!
                raise Exception("Postings are out of order: %s:%s .. %s:%s" %
                                (current_fieldnum, current_text, fieldnum, text))
            
            current_weight += term_table.write_posting(docnum, data, write_posting_method)
        
        # Finish up the last term
        if not first:
            term_table.add_row((current_fieldnum, current_text), current_weight)
            if current_weight > self.max_weight:
                self.max_weight = current_weight



if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = test_fields
import unittest

from whoosh import fields, index

class TestSchema(unittest.TestCase):
    def test_schema_eq(self):
        a = fields.Schema()
        b = fields.Schema()
        self.assertEqual(a, b)

        a = fields.Schema(id=fields.ID)
        b = fields.Schema(id=fields.ID)
        self.assertEqual(a[0], b[0])
        self.assertEqual(a, b)

        c = fields.Schema(id=fields.TEXT)
        self.assertNotEqual(a, c)
        
    def test_creation1(self):
        s = fields.Schema()
        s.add("content", fields.TEXT(phrase = True))
        s.add("title", fields.TEXT(stored = True))
        s.add("path", fields.ID(stored = True))
        s.add("tags", fields.KEYWORD(stored = True))
        s.add("quick", fields.NGRAM)
        s.add("note", fields.STORED)
        
        self.assertEqual(s.field_names(), ["content", "title", "path", "tags", "quick", "note"])
        self.assert_("content" in s)
        self.assertFalse("buzz" in s)
        self.assert_(isinstance(s["tags"], fields.KEYWORD))
        self.assert_(isinstance(s[3], fields.KEYWORD))
        self.assert_(s[0] is s.field_by_number(0))
        self.assert_(s["title"] is s.field_by_name("title"))
        self.assert_(s.name_to_number("path") == 2)
        self.assert_(s.number_to_name(4) == "quick")
        self.assertEqual(s.scorable_fields(), [0, 1, 4])
        
    def test_creation2(self):
        s = fields.Schema(content = fields.TEXT(phrase = True),
                          title = fields.TEXT(stored = True),
                          path = fields.ID(stored = True),
                          tags = fields.KEYWORD(stored = True),
                          quick = fields.NGRAM)
        

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_indexing
import unittest
from os import mkdir
from os.path import exists
from shutil import rmtree

from whoosh import fields, index, qparser, store, writing

class TestIndexing(unittest.TestCase):
    def make_index(self, dirname, schema):
        if not exists(dirname):
            mkdir(dirname)
        st = store.FileStorage(dirname)
        ix = index.Index(st, schema, create = True)
        return ix
    
    def destroy_index(self, dirname):
        if exists(dirname):
            rmtree(dirname)
    
    def test_creation(self):
        s = fields.Schema()
        s.add("content", fields.TEXT(phrase = True))
        s.add("title", fields.TEXT(stored = True))
        s.add("path", fields.ID(stored = True))
        s.add("tags", fields.KEYWORD(stored = True))
        s.add("quick", fields.NGRAM)
        s.add("note", fields.STORED)
        st = store.RamStorage()
        
        ix = index.Index(st, s, create = True)
        w = writing.IndexWriter(ix)
        w.add_document(title = u"First", content = u"This is the first document", path = u"/a",
                       tags = u"first second third", quick = u"First document", note = u"This is the first document")
        w.start_document()
        w.add_field("content", u"Let's try this again")
        w.add_field("title", u"Second")
        w.add_field("path", u"/b")
        w.add_field("tags", u"Uno Dos Tres")
        w.add_field("quick", u"Second document")
        w.add_field("note", u"This is the second document")
        w.end_document()
        
        w.commit()
        
    def test_integrity(self):
        s = fields.Schema(name = fields.TEXT, value = fields.TEXT)
        st = store.RamStorage()
        ix = index.Index(st, s, create = True)
        
        w = writing.IndexWriter(ix)
        w.add_document(name = u"Yellow brown", value = u"Blue red green purple?")
        w.add_document(name = u"Alpha beta", value = u"Gamma delta epsilon omega.")
        w.commit()
        
        w = writing.IndexWriter(ix)
        w.add_document(name = u"One two", value = u"Three four five.")
        w.commit()
        
        tr = ix.term_reader()
        self.assertEqual(ix.doc_count_all(), 3)
        self.assertEqual(list(tr.lexicon("name")), ["alpha", "beta", "brown", "one", "two", "yellow"])
    
    def test_lengths(self):
        s = fields.Schema(f1 = fields.KEYWORD(stored = True, scorable = True),
                          f2 = fields.KEYWORD(stored = True, scorable = True))
        ix = self.make_index("testindex", s)
        
        try:
            w = ix.writer()
            tokens = u"ABCDEFG"
            from itertools import cycle, islice
            lengths = [10, 20, 2, 102, 45, 3, 420, 2]
            for length in lengths:
                w.add_document(f2 = u" ".join(islice(cycle(tokens), length)))
            w.commit()
            dr = ix.doc_reader()
            ls1 = [dr.doc_field_length(i, "f1") for i in xrange(0, len(lengths))]
            ls2 = [dr.doc_field_length(i, "f2") for i in xrange(0, len(lengths))]
            self.assertEqual(ls1, [0]*len(lengths))
            self.assertEqual(ls2, lengths)
            dr.close()
            
            ix.close()
        finally:
            self.destroy_index("testindex")
    
    def test_lengths_ram(self):
        s = fields.Schema(f1 = fields.KEYWORD(stored = True, scorable = True),
                          f2 = fields.KEYWORD(stored = True, scorable = True))
        st = store.RamStorage()
        ix = index.Index(st, s, create = True)
        w = writing.IndexWriter(ix)
        w.add_document(f1 = u"A B C D E", f2 = u"X Y Z")
        w.add_document(f1 = u"B B B B C D D Q", f2 = u"Q R S T")
        w.add_document(f1 = u"D E F", f2 = u"U V A B C D E")
        w.commit()
        
        dr = ix.doc_reader()
        ls1 = [dr.doc_field_length(i, "f1") for i in xrange(0, 3)]
        ls2 = [dr.doc_field_length(i, "f2") for i in xrange(0, 3)]
        self.assertEqual(dr[0]["f1"], "A B C D E")
        self.assertEqual(dr.doc_field_length(0, "f1"), 5)
        self.assertEqual(dr.doc_field_length(1, "f1"), 8)
        self.assertEqual(dr.doc_field_length(2, "f1"), 3)
        self.assertEqual(dr.doc_field_length(0, "f2"), 3)
        self.assertEqual(dr.doc_field_length(1, "f2"), 4)
        self.assertEqual(dr.doc_field_length(2, "f2"), 7)
        
        self.assertEqual(ix.field_length("f1"), 16)
        self.assertEqual(ix.field_length("f2"), 14)
        
    def test_merged_lengths(self):
        s = fields.Schema(f1 = fields.KEYWORD(stored = True, scorable = True),
                          f2 = fields.KEYWORD(stored = True, scorable = True))
        st = store.RamStorage()
        ix = index.Index(st, s, create = True)
        w = writing.IndexWriter(ix)
        w.add_document(f1 = u"A B C", f2 = u"X")
        w.add_document(f1 = u"B C D E", f2 = u"Y Z")
        w.commit()
        
        w = writing.IndexWriter(ix)
        w.add_document(f1 = u"A", f2 = u"B C D E X Y")
        w.add_document(f1 = u"B C", f2 = u"X")
        w.commit(writing.NO_MERGE)
        
        w = writing.IndexWriter(ix)
        w.add_document(f1 = u"A B X Y Z", f2 = u"B C")
        w.add_document(f1 = u"Y X", f2 = u"A B")
        w.commit(writing.NO_MERGE)
        
        dr = ix.doc_reader()
        self.assertEqual(dr[0]["f1"], u"A B C")
        self.assertEqual(dr.doc_field_length(0, "f1"), 3)
        self.assertEqual(dr.doc_field_length(2, "f2"), 6)
        self.assertEqual(dr.doc_field_length(4, "f1"), 5)
        
    def test_frequency_keyword(self):
        s = fields.Schema(content = fields.KEYWORD)
        st = store.RamStorage()
        ix = index.Index(st, s, create = True)
        
        w = ix.writer()
        w.add_document(content = u"A B C D E")
        w.add_document(content = u"B B B B C D D")
        w.add_document(content = u"D E F")
        w.commit()
        
        tr = ix.term_reader()
        self.assertEqual(tr.doc_frequency("content", u"B"), 2)
        self.assertEqual(tr.frequency("content", u"B"), 5)
        self.assertEqual(tr.doc_frequency("content", u"E"), 2)
        self.assertEqual(tr.frequency("content", u"E"), 2)
        self.assertEqual(tr.doc_frequency("content", u"A"), 1)
        self.assertEqual(tr.frequency("content", u"A"), 1)
        self.assertEqual(tr.doc_frequency("content", u"D"), 3)
        self.assertEqual(tr.frequency("content", u"D"), 4)
        self.assertEqual(tr.doc_frequency("content", u"F"), 1)
        self.assertEqual(tr.frequency("content", u"F"), 1)
        self.assertEqual(tr.doc_frequency("content", u"Z"), 0)
        self.assertEqual(tr.frequency("content", u"Z"), 0)
        self.assertEqual(list(tr), [(0, u"A", 1, 1), (0, u"B", 2, 5),
                                    (0, u"C", 2, 2), (0, u"D", 3, 4),
                                    (0, u"E", 2, 2), (0, u"F", 1, 1)])
        
    def test_frequency_text(self):
        s = fields.Schema(content = fields.KEYWORD)
        st = store.RamStorage()
        ix = index.Index(st, s, create = True)
        
        w = ix.writer()
        w.add_document(content = u"alfa bravo charlie delta echo")
        w.add_document(content = u"bravo bravo bravo bravo charlie delta delta")
        w.add_document(content = u"delta echo foxtrot")
        w.commit()
        
        tr = ix.term_reader()
        self.assertEqual(tr.doc_frequency("content", u"bravo"), 2)
        self.assertEqual(tr.frequency("content", u"bravo"), 5)
        self.assertEqual(tr.doc_frequency("content", u"echo"), 2)
        self.assertEqual(tr.frequency("content", u"echo"), 2)
        self.assertEqual(tr.doc_frequency("content", u"alfa"), 1)
        self.assertEqual(tr.frequency("content", u"alfa"), 1)
        self.assertEqual(tr.doc_frequency("content", u"delta"), 3)
        self.assertEqual(tr.frequency("content", u"delta"), 4)
        self.assertEqual(tr.doc_frequency("content", u"foxtrot"), 1)
        self.assertEqual(tr.frequency("content", u"foxtrot"), 1)
        self.assertEqual(tr.doc_frequency("content", u"zulu"), 0)
        self.assertEqual(tr.frequency("content", u"zulu"), 0)
        self.assertEqual(list(tr), [(0, u"alfa", 1, 1), (0, u"bravo", 2, 5),
                                    (0, u"charlie", 2, 2), (0, u"delta", 3, 4),
                                    (0, u"echo", 2, 2), (0, u"foxtrot", 1, 1)])
    
    def test_deletion(self):
        s = fields.Schema(key = fields.ID, name = fields.TEXT, value = fields.TEXT)
        st = store.RamStorage()
        ix = index.Index(st, s, create = True)
        
        w = writing.IndexWriter(ix)
        w.add_document(key = u"A", name = u"Yellow brown", value = u"Blue red green purple?")
        w.add_document(key = u"B", name = u"Alpha beta", value = u"Gamma delta epsilon omega.")
        w.add_document(key = u"C", name = u"One two", value = u"Three four five.")
        w.commit()
        
        count = ix.delete_by_term("key", u"B")
        self.assertEqual(count, 1)
        ix.commit()
        
        self.assertEqual(ix.doc_count_all(), 3)
        self.assertEqual(ix.doc_count(), 2)
        
        ix.optimize()
        self.assertEqual(ix.doc_count(), 2)
        tr = ix.term_reader()
        self.assertEqual(list(tr.lexicon("name")), ["brown", "one", "two", "yellow"])

    def test_update(self):
        # Test update with multiple unique keys
        SAMPLE_DOCS = [{"id": u"test1", "path": u"/test/1", "text": u"Hello"},
                       {"id": u"test2", "path": u"/test/2", "text": u"There"},
                       {"id": u"test3", "path": u"/test/3", "text": u"Reader"},
                       ]
        
        schema = fields.Schema(id=fields.ID(unique=True, stored=True),
                               path=fields.ID(unique=True, stored=True),
                               text=fields.TEXT)
        ix = self.make_index("testindex", schema)
        try:
            writer = ix.writer()
            for doc in SAMPLE_DOCS:
                writer.add_document(**doc)
            writer.commit()
            
            writer = ix.writer()
            writer.update_document(**{"id": u"test2",
                                      "path": u"test/1",
                                      "text": u"Replacement"})
            writer.commit()
            ix.close()
        finally:
            self.destroy_index("testindex")

    def test_reindex(self):
        SAMPLE_DOCS = [
            {'id': u'test1', 'text': u'This is a document. Awesome, is it not?'},
            {'id': u'test2', 'text': u'Another document. Astounding!'},
            {'id': u'test3', 'text': u'A fascinating article on the behavior of domestic steak knives.'},
        ]

        schema = fields.Schema(text=fields.TEXT(stored=True),
                               id=fields.ID(unique=True, stored=True))
        ix = self.make_index("testindex", schema)
        try:
            def reindex():
                writer = ix.writer()
            
                for doc in SAMPLE_DOCS:
                    writer.update_document(**doc)
            
                writer.commit()

            reindex()
            self.assertEqual(ix.doc_count_all(), 3)
            reindex()
            
            ix.close()
            
        finally:
            self.destroy_index("testindex")



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_parsing
import unittest
from os import mkdir
from os.path import exists
from shutil import rmtree

from whoosh import fields, index, qparser, query, store

class TestQueryParser(unittest.TestCase):
    def make_index(self, dirname, schema):
        if not exists(dirname):
            mkdir(dirname)
        st = store.FileStorage(dirname)
        ix = index.Index(st, schema, create = True)
        return ix
    
    def destroy_index(self, dirname):
        if exists(dirname):
            rmtree(dirname)
    
    def test_boost(self):
        qp = qparser.QueryParser("content")
        q = qp.parse("this^3 fn:that^0.5 5.67")
        self.assertEqual(q.subqueries[0].boost, 3.0)
        self.assertEqual(q.subqueries[1].boost, 0.5)
        self.assertEqual(q.subqueries[1].fieldname, "fn")
        self.assertEqual(q.subqueries[2].text, "5.67")
        
    def test_wildcard(self):
        qp = qparser.QueryParser("content")
        q = qp.parse("hello *the?e* ?star*s? test")
        self.assertEqual(len(q.subqueries), 4)
        self.assertNotEqual(q.subqueries[0].__class__.__name__, "Wildcard")
        self.assertEqual(q.subqueries[1].__class__.__name__, "Wildcard")
        self.assertEqual(q.subqueries[2].__class__.__name__, "Wildcard")
        self.assertNotEqual(q.subqueries[3].__class__.__name__, "Wildcard")
        self.assertEqual(q.subqueries[1].text, "*the?e*")
        self.assertEqual(q.subqueries[2].text, "?star*s?")

    def test_fieldname_underscores(self):
        s = fields.Schema(my_name=fields.ID(stored=True), my_value=fields.TEXT)
        ix = self.make_index("testindex", s)
        
        try:
            w = ix.writer()
            w.add_document(my_name=u"Green", my_value=u"It's not easy being green")
            w.add_document(my_name=u"Red", my_value=u"Hopping mad like a playground ball")
            w.commit()
            
            qp = qparser.QueryParser("my_value", schema=ix.schema)
            s = ix.searcher()
            r = s.search(qp.parse("my_name:Green"))
            self.assertEqual(r[0]['my_name'], "Green")
            s.close()
            ix.close()
        finally:
            self.destroy_index("testindex")
    
    def test_endstar(self):
        qp = qparser.QueryParser("text")
        q = qp.parse("word*")
        self.assertEqual(q.__class__.__name__, "Prefix")
        self.assertEqual(q.text, "word")
    
    def test_escaping(self):
        qp = qparser.QueryParser("text")
        
        #q = qp.parse(r'http\:example')
        #self.assertEqual(q.__class__, query.Term)
        #self.assertEqual(q.fieldname, "text")
        #self.assertEqual(q.text, "http:example")
        
        # The following test currently fails because
        # pyparsing swallows escaped whitespace for some
        # reason.
        
        #q = qp.parse(r'hello\ there')
        #self.assertEqual(q.__class__, query.Term)
        #self.assertEqual(q.fieldname, "text")
        #self.assertEqual(q.text, "hello there")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_reading
import unittest

from whoosh import analysis, fields, index, store, writing

class TestReading(unittest.TestCase):
    def _create_index(self):
        s = fields.Schema(f1 = fields.KEYWORD(stored = True),
                          f2 = fields.KEYWORD,
                          f3 = fields.KEYWORD)
        st = store.RamStorage()
        ix = index.Index(st, s, create = True)
        return ix
    
    def _one_segment_index(self):
        ix = self._create_index()
        w = writing.IndexWriter(ix)
        w.add_document(f1 = u"A B C", f2 = u"1 2 3", f3 = u"X Y Z")
        w.add_document(f1 = u"D E F", f2 = u"4 5 6", f3 = u"Q R S")
        w.add_document(f1 = u"A E C", f2 = u"1 4 6", f3 = u"X Q S")
        w.add_document(f1 = u"A A A", f2 = u"2 3 5", f3 = u"Y R Z")
        w.add_document(f1 = u"A B", f2 = u"1 2", f3 = u"X Y")
        w.commit()
        
        return ix
    
    def _multi_segment_index(self):
        ix = self._create_index()
        w = writing.IndexWriter(ix)
        w.add_document(f1 = u"A B C", f2 = u"1 2 3", f3 = u"X Y Z")
        w.add_document(f1 = u"D E F", f2 = u"4 5 6", f3 = u"Q R S")
        w.commit()
        
        w = writing.IndexWriter(ix)
        w.add_document(f1 = u"A E C", f2 = u"1 4 6", f3 = u"X Q S")
        w.add_document(f1 = u"A A A", f2 = u"2 3 5", f3 = u"Y R Z")
        w.commit(writing.NO_MERGE)
        
        w = writing.IndexWriter(ix)
        w.add_document(f1 = u"A B", f2 = u"1 2", f3 = u"X Y")
        w.commit(writing.NO_MERGE)
        
        return ix
    
    def test_readers(self):
        target = [(0, u'A', 4, 6), (0, u'B', 2, 2), (0, u'C', 2, 2),
                  (0, u'D', 1, 1), (0, u'E', 2, 2), (0, u'F', 1, 1),
                  (1, u'1', 3, 3), (1, u'2', 3, 3), (1, u'3', 2, 2),
                  (1, u'4', 2, 2), (1, u'5', 2, 2), (1, u'6', 2, 2),
                  (2, u'Q', 2, 2), (2, u'R', 2, 2), (2, u'S', 2, 2),
                  (2, u'X', 3, 3), (2, u'Y', 3, 3), (2, u'Z', 2, 2)]
        
        stored = [{"f1": "A B C"}, {"f1": "D E F"}, {"f1": "A E C"},
                  {"f1": "A A A"}, {"f1": "A B"}]
        
        def t(ix):
            tr = ix.term_reader()
            self.assertEqual(list(tr), target)
            
            dr = ix.doc_reader()
            self.assertEqual(list(dr), stored)
        
        ix = self._one_segment_index()
        self.assertEqual(len(ix.segments), 1)
        t(ix)
        
        ix = self._multi_segment_index()
        self.assertEqual(len(ix.segments), 3)
        t(ix)
        
    def test_vector_postings(self):
        s = fields.Schema(id=fields.ID(stored=True, unique=True),
                          content=fields.TEXT(vector=fields.Positions(analyzer=analysis.StandardAnalyzer())))
        st = store.RamStorage()
        ix = index.Index(st, s, create = True)
        
        writer = ix.writer()
        writer.add_document(id=u'1', content=u'the quick brown fox jumped over the lazy dogs')
        writer.commit()
        dr = ix.doc_reader()
        
        terms = list(dr.vector_as(0, 0, "weight"))
        self.assertEqual(terms, [(u'brown', 1.0),
                                 (u'dogs', 1.0),
                                 (u'fox', 1.0),
                                 (u'jumped', 1.0),
                                 (u'lazy', 1.0),
                                 (u'over', 1.0),
                                 (u'quick', 1.0),
                                 ])

        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_searching
import unittest

from whoosh import fields, index, qparser, searching, scoring, store, writing
from whoosh.query import *

class TestReading(unittest.TestCase):
    def setUp(self):
        s = fields.Schema(key = fields.ID(stored = True),
                          name = fields.TEXT,
                          value = fields.TEXT)
        st = store.RamStorage()
        ix = index.Index(st, s, create = True)
        
        w = writing.IndexWriter(ix)
        w.add_document(key = u"A", name = u"Yellow brown", value = u"Blue red green render purple?")
        w.add_document(key = u"B", name = u"Alpha beta", value = u"Gamma delta epsilon omega.")
        w.add_document(key = u"C", name = u"One two", value = u"Three rendered four five.")
        w.add_document(key = u"D", name = u"Quick went", value = u"Every red town.")
        w.add_document(key = u"E", name = u"Yellow uptown", value = u"Interest rendering outer photo!")
        w.commit()
        
        self.ix = ix
    
    def _get_keys(self, stored_fields):
        return sorted([d.get("key") for d in stored_fields])
    
    def _docs(self, q, s):
        return self._get_keys([s.stored_fields(docnum) for docnum
                               in q.docs(s)])
    
    def _doc_scores(self, q, s, w):
        return self._get_keys([s.stored_fields(docnum) for docnum, score
                               in q.doc_scores(s, weighting = w)])
    
    def test_empty_index(self):
        schema = fields.Schema(key = fields.ID(stored=True), value = fields.TEXT)
        st = store.RamStorage()
        self.assertRaises(index.EmptyIndexError, index.Index, st, schema)
    
    def test_docs_method(self):
        s = self.ix.searcher()
        
        self.assertEqual(self._get_keys(s.documents(name = "yellow")), [u"A", u"E"])
        self.assertEqual(self._get_keys(s.documents(value = "red")), [u"A", u"D"])
    
    def test_queries(self):
        s = self.ix.searcher()
        
        tests = [
                 (Term("name", u"yellow"),
                  [u"A", u"E"]),
                 (Term("value", u"red"),
                  [u"A", u"D"]),
                 (Term("value", u"zeta"),
                  []),
                 (Require([Term("value", u"red"), Term("name", u"yellow")]),
                  [u"A"]),
                 (And([Term("value", u"red"), Term("name", u"yellow")]),
                  [u"A"]),
                 (Or([Term("value", u"red"), Term("name", u"yellow")]),
                  [u"A", u"D", u"E"]),
                 (Or([Term("value", u"red"), Term("name", u"yellow"), Not(Term("name", u"quick"))]),
                  [u"A", u"E"]),
                 (AndNot(Term("name", u"yellow"), Term("value", u"purple")),
                  [u"E"]),
                 (Variations("value", u"render"), [u"A", u"C", u"E"]),
                 (Or([Wildcard('value', u'*red*'), Wildcard('name', u'*yellow*')]),
                  [u"A", u"C", u"D", u"E"]),
                ]
        
        for query, result in tests:
            self.assertEqual(self._docs(query, s), result)
        
        for wcls in dir(scoring):
            if wcls is scoring.Weighting: continue
            if isinstance(wcls, scoring.Weighting):
                for query, result in tests:
                    self.assertEqual(self._doc_scores(query, s, wcls), result)
        
        for methodname in ("_docs", "_doc_scores"):
            method = getattr(self, methodname)

    def test_score_retrieval(self):
        schema = fields.Schema(title=fields.TEXT(stored=True),
                               content=fields.TEXT(stored=True))
        storage = store.RamStorage()
        ix = index.Index(storage, schema, create=True)
        writer = ix.writer()
        writer.add_document(title=u"Miss Mary",
                            content=u"Mary had a little white lamb its fleece was white as snow")
        writer.add_document(title=u"Snow White",
                            content=u"Snow white lived in the forrest with seven dwarfs")
        writer.commit()
        
        searcher = ix.searcher()
        results = searcher.search(Term("content", "white"))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['title'], u"Miss Mary")
        self.assertEqual(results[1]['title'], u"Snow White")
        self.assertNotEqual(results.score(0), None)
        self.assertNotEqual(results.score(0), 0)
        self.assertNotEqual(results.score(0), 1)

    def test_missing_field_scoring(self):
        schema = fields.Schema(name=fields.TEXT(stored=True), hobbies=fields.TEXT(stored=True))
        storage = store.RamStorage()
        idx = index.Index(storage, schema, create=True)
        writer = idx.writer() 
        writer.add_document(name=u'Frank', hobbies=u'baseball, basketball')
        writer.commit()
        self.assertEqual(idx.segments[0].field_length(0), 2) # hobbies
        self.assertEqual(idx.segments[0].field_length(1), 1) # name
        
        writer = idx.writer()
        writer.add_document(name=u'Jonny') 
        writer.commit()
        self.assertEqual(len(idx.segments), 1)
        self.assertEqual(idx.segments[0].field_length(0), 2) # hobbies
        self.assertEqual(idx.segments[0].field_length(1), 2) # name
        
        parser = qparser.MultifieldParser(['name', 'hobbies'], schema=schema)
        searcher = idx.searcher()
        result = searcher.search(parser.parse(u'baseball'))
        self.assertEqual(len(result), 1)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_spelling
import unittest

from whoosh import index, spelling, store


class TestSpelling(unittest.TestCase):
    def test_spelling(self):
        st = store.RamStorage()
        
        sp = spelling.SpellChecker(st, mingram=2)
        
        wordlist = ["render", "animation", "animate", "shader",
                    "shading", "zebra", "koala", "lamppost",
                    "ready", "kismet", "reaction", "page",
                    "delete", "quick", "brown", "fox", "jumped",
                    "over", "lazy", "dog", "wicked", "erase",
                    "red", "team", "yellow", "under", "interest",
                    "open", "print", "acrid", "sear", "deaf",
                    "feed", "grow", "heal", "jolly", "kilt",
                    "low", "zone", "xylophone", "crown",
                    "vale", "brown", "neat", "meat"]
        
        sp.add_words([unicode(w) for w in wordlist])
        
        sugs = sp.suggest(u"reoction")
        self.assert_(sugs)
        self.assertEqual(sugs, [u"reaction", u"animation", u"red"])


if __name__ == '__main__':
    unittest.main()
    print 10 + 20
########NEW FILE########
