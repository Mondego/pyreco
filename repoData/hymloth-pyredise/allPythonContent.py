__FILENAME__ = corpus_handler
#!/usr/bin/python2.6.5
# -*- coding: utf-8 -*-
#
# Copyright 2011 Christos Spiliopoulos.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



__authors__ = [
  '"Christos Spiliopoulos" <santos.koniordos@gmail.com>',
]



import re
import json
from collections import defaultdict

import index_handler



class CorpusHandler(index_handler.IndexHandler):
    '''    
    A class for dynamic manipulation of our corpus.
    
    It provides methods for document insertion and deletion which, in turn, update all
    relevant INDEX stuff in the background.
    
    '''
    

    
    def __init__(self, **kwargs):
        index_handler.IndexHandler.__init__(self, **kwargs)
        
        self.debug = kwargs.get('debug', False)
        self.pos = defaultdict(list)
        self.sanitized_text = []
        self.doc_len = 0
        self.delimiter = "!"
        self.internal_doc_id = ""
        
        



    def update_pos(self, item, pos):
        try: gap = pos - self.pos[item][-1]
        except: gap = pos
        self.pos[item].append(str(gap))
        


    def content_indexer(self, doc, doc_id,  index=True):

        for i, token in enumerate(re.sub(r"[.,:;!\-?\"']", " ", doc).split()):
            
            lower = token.lower()
            try: # no encoding errors
                if self.legal_token(lower):
                    item = self.stem(lower.decode("utf8", "ignore"))
                    if item:
                        self.update_pos(item, i)
                        self.sanitized_text.append(item)
            except: 
                if self.debug: print "Probable unicode error"  , lower
                
        self.doc_len = len(self.sanitized_text)  
        
        if index:
            for term, posting in self.pos.iteritems():     
                self.term_add_doc_id(term,  doc_id, float(len(posting))/self.doc_len )   
                self.term_add_doc_id_posting(term,  doc_id, ",".join(posting) )   
                
        else: # remove from index                  
            for term, posting in self.pos.iteritems():     
                self.term_remove_doc_id(term, doc_id)   
                self.term_remove_doc_id_posting(term, doc_id)          
 
              
    def title_indexer(self, title, doc_id, index=True):

        for i, token in enumerate(re.sub(r"[.,:;\-!?\"']", " ", title).split()):
            lower = token.lower()
            try: # no encoding errors
                if self.legal_token(lower):
                    item = self.stem(lower.decode("utf8", "ignore"))
                    if item:
                        if index: 
                            self.term_add_doc_id_title(item, doc_id)
                            self.term_add_doc_id_title_posting(item, doc_id, i)
                        else: 
                            self.term_remove_doc_id_title(item, doc_id)
                            self.term_remove_doc_id_title_posting(item, doc_id)
                    
            except: 
                if self.debug: print "Probable unicode error"  
     
   
             
    def index(self, doc, **kwargs):

        doc_id = str(doc["id"])
        title = doc["title"]
        content = doc["content"]


        self.clear()
        self.identify_language(content)
        
        
        if not self.doc_id_exists(doc_id):        
            self.internal_doc_id = self.get_next_id()
            self.add_doc_id(self.internal_doc_id, doc_id)
            self.content_indexer(content, self.internal_doc_id, index=True)
            self.title_indexer(title, self.internal_doc_id, index=True)
            #self.update_cardinality()
            self.flush() # at this point, the INDEX has been updated
            return True                
        else:
            if self.debug: print "This docID already exists in our corpus!"      
            return False
    
    
    
    def extract_features(self, **kwargs):
        '''
        Extracts vital info from current document
        Up to features_limit in length
        Using a tfidf threshold to filter the top of them
        '''
        export_value = kwargs.get('export', json.dumps)
        tfidf_threshold_absolute = kwargs.get('tfidf_threshold_absolute', 0.0000001)
        features_limit = kwargs.get('features_limit', 500)
        rnd = kwargs.get('rnd', 4)
        doc = kwargs.get('doc', None)

        # just in case, we chech if we have to re-tokenize the doc

        if not len(self.sanitized_text):
            if doc is None: 
                raise Exception, " No document given !! "
            self.clear()
            self.identify_language(doc)

            for i, token in enumerate(re.sub(r"[.,:;!\-?\"']", " ", doc).split()):
                lower = token.lower()
                try: 
                    if self.legal_token(lower):
                        item = self.stem(lower.decode("utf8", "ignore"))
                        if item:
                            self.update_pos(item, i)
                            self.sanitized_text.append(item)
                except Exception as e: 
                    #import traceback
                    #print traceback.format_exc()
                    if self.debug: print "Probable unicode error"  
                                
            self.doc_len = len(self.sanitized_text)    
        
        idfs = [i[1] for i in self.get_dfs(self.sanitized_text)]

        tfidf_tuple_list = []
        adapt_features = []

        for i in xrange(min(self.doc_len, len(idfs), features_limit)):
            tfidf = len(self.pos[self.sanitized_text[i]]) * idfs[i] / self.doc_len
            tup = (self.sanitized_text[i], str(round(tfidf , rnd)), i)
            tfidf_tuple_list.append(tup)
            
            if tfidf > tfidf_threshold_absolute: adapt_features.append(tup)
        
        self.clear()
        return export_value(tfidf_tuple_list), export_value(adapt_features)        
        
        
        


    def remove_document(self, doc, **kwargs):
        
        doc_id = str(doc["id"])
        title = doc["title"]
        content = doc["content"]
        
        self.clear()
        self.identify_language(content)


        if self.doc_id_exists(doc_id):  
            self.internal_doc_id = self.resolve_external_id(doc_id)
            self.remove_doc_id(self.internal_doc_id)
            self.content_indexer(content, self.internal_doc_id , index=False) 
            self.title_indexer(title, self.internal_doc_id, index=False)
            self.flush() # at this point, the INDEX has been updated 
            return True
        else:
            if self.debug: print "Removal Failed: This docID does not exist in our corpus!" 
            return False
 


    def clear(self):
        self.pos = defaultdict(list)
        self.sanitized_text = []
        self.doc_len = 0





if __name__=="__main__":
    
    import redis , time, json
    db = redis.Redis(host='192.168.1.3', port=6666, db=3)

    
    cp = CorpusHandler(debug=True, db=db)
    #cp.drop()
    '''articles = [
     {"content": "Να σε πώ και κάτι φιλαράκι, δεν σε λέω και τίποτα κιόλας", "title":"δεν σε λέω", "id": 1 },
     {"content": "De snelle bruine vos springt over de luie hond", "title":"luie hond", "id": 2 },
     {"content": "The quick brown fox jumps over the lazy dog", "title":"lazy dog", "id": 3 },
     {"content": "Le renard brun rapide saute par-dessus le chien paresseux", "title":"chien paresseux", "id": 4 },
     {"content": "Der schnelle braune Fuchs springt über den faulen Hund", "title":"faulen Hund", "id": 5 },
     {"content": "El rápido zorro marrón salta sobre el perro perezoso", "title":"perro perezoso", "id": 6 },
     {"content": "Журнал содержит более полусотни аналитических, тематических и новостных разделов, а также детальный архив и базу данных переписей населения, демографических показателей по регионам России", "title":"Демоскоп", "id": 457 }
     ]

    start = time.time()
    for n, i in enumerate(articles):
        print n,
        if not   cp.index(i):
            print "features:", cp.extract_features(doc = i["content"])'''
    
    
    '''import feedparser
    
    s = feedparser.parse("http://www.koutipandoras.gr/feed")
    
    for i, e in enumerate(s["entries"]):

        cp = CorpusHandler(debug=True, db=db)
        a = {"title":e["title"], "content":e["content"][0]["value"], "id":i+6}
        print cp.index(a)
        print cp.sanitized_text'''
            


















########NEW FILE########
__FILENAME__ = index_base
#!/usr/bin/python2.6.5
# -*- coding: utf-8 -*-
#
# Copyright 2011 Christos Spiliopoulos.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



__authors__ = [
  '"Christos Spiliopoulos" <santos.koniordos@gmail.com>',
]

from functools import partial



class IndexBase(object):
    '''
    A base class representing a "connection" with a redis server ( db ), providing some extra primitive functions for docIds manipulation
    
    Attributes:
    
       _max_id : a special key of _dict_key denoting the current maximum docID number
       _set_key : a special key holding our unique docIDs currently present in the corpus
       _docid_map : a special key holding a mapping between docIDs and physical numbers, starting from one
       _slots : a special key denoting some available ids for use ( < _max_id )
       db : the name of redis database (server)
       pipe : redis pipeline object
       

    NOTE: this class (and its descendants) is not thread-safe, thus create a new object every time you need its functionality, per process/thread.
          DO NOT EVER SHARE SUCH AN OBJECT !!!
    

    '''
    
    def __init__(self, **kwargs):
        self._max_id = "$MAXID$"
        self._set_key = "$DOCIDS$"
        self._docid_map = "$DOCIDMAP$"
        self._slots = "$SLOTS$"
        self.db = kwargs.get('db',"") 
        self.pipe = self.db.pipeline()
        
        
    def flush(self):
        ''' executes the pipeline, returns a list of results '''
        return self.pipe.execute()
    
    
    def drop(self):
        ''' drops the entire index '''
        return self.db.flushdb()   
    
    
    def get_cardinality(self, piped=True):
        if piped: self.pipe.scard(self._set_key)
        else: return self.db.scard(self._set_key)
        
        
    def set_max_id(self, value=1, piped=True):
        if piped: self.pipe.incr( self._max_id , value)
        else: self.db.incr( self._max_id , value)
        
        
    def get_max_id(self, piped=True):
        if piped: self.pipe.get(self._max_id)
        else: return self.db.get(self._max_id)   
    
    
    def set_slot(self, id, piped=True):
        if piped: self.pipe.sadd(self._slots, id)
        else: self.db.sadd(self._slots, id)
        
    
    def get_slot(self, piped=True):
        if piped: self.pipe.spop(self._slots)
        else: return self.db.spop(self._slots)     

    
    def store_doc_id(self, internal_doc_id, external_doc_id, piped=True):
        if piped: 
            self.pipe.hset(self._docid_map, internal_doc_id, external_doc_id)
            self.pipe.hset(self._docid_map, external_doc_id, internal_doc_id)
        else:    
            self.db.hset(self._docid_map, internal_doc_id, external_doc_id)
            self.db.hset(self._docid_map, external_doc_id, internal_doc_id)


    def purge_doc_id(self, internal_doc_id, piped=True):
        external_doc_id = self.db.hget(self._docid_map, internal_doc_id)
        if piped: 
            self.pipe.hdel(self._docid_map, internal_doc_id)
            self.pipe.hdel(self._docid_map, external_doc_id)
        else:    
            self.db.hdel(self._docid_map, internal_doc_id)  
            self.db.hdel(self._docid_map, external_doc_id)  
        self.set_slot(internal_doc_id, piped=piped)    


    def get_next_id(self):
        ''' 
        Decides which is the next id to use. This is either the (_max_id + 1) or an available slot.
        Note that an available slot is always preferred
        '''
        self.get_max_id(piped=True)
        self.get_slot(piped=True)
        res = self.flush()
        if res[1] and res[1] is not None: 
            return res[1]
        else:
            self.set_max_id(value=1,piped=False)
            try:return (int(res[0])+1)
            except: return 1    


    def resolve_external_id(self, doc_id):
        return self.db.hget(self._docid_map, doc_id) 


    def resolve_external_ids(self, doc_ids):
        return self.db.hmget(self._docid_map, doc_ids) 
    
    
    def legal_token(self, s, exclude_list=[], max_len=3):
        #if len(s.decode("utf-8")) <= max_len:
        #    return False
        if any(i in s for i in '<>/\{}|\+=_)(*&^%$#@~1234567890`'):
            return False
        if s in exclude_list:
            return False
        return True
    
    

        
    def identify_language(self, text):
        
        # we need different language detection on indexing vs quering (for speed)
        if self.__class__.__name__ == "QueryHandler":
            from sensitive_language_detection import check_lang
        else:
            from quick_language_detection import check_lang
        
        self.lang = check_lang(text)
        
        if self.lang == "greek":
            from stemmers.greek import stem, stopwords 
            self.stem = stem
            self.legal_token = partial(self.legal_token, exclude_list=stopwords)
        else:
            from nltk.stem import SnowballStemmer
            from nltk.corpus import stopwords
            self.stem = SnowballStemmer(self.lang).stem
            self.legal_token = partial(self.legal_token, exclude_list=stopwords.words(self.lang))
            

        if self.debug: print "LANG", self.lang#, "stemmer", self.stem
            

########NEW FILE########
__FILENAME__ = index_handler
#!/usr/bin/python2.6.5
# -*- coding: utf-8 -*-
#
# Copyright 2011 Christos Spiliopoulos.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



__authors__ = [
  '"Christos Spiliopoulos" <santos.koniordos@gmail.com>',
]



import index_base
import math
    

class IndexHandler(index_base.IndexBase):
    '''
    This class provides basic methods for INDEX manipulation
    '''
    
    def __init__(self, **kwargs):
        index_base.IndexBase.__init__(self, **kwargs)
        

    def term_add_doc_id(self, term, value, score):
        '''
	    score is tf
	    '''
        self.pipe.zadd(term, value, score)   
        
        
    def term_remove_doc_id(self, term, value):
        self.pipe.zrem(term, value) 
        
          
    def term_add_doc_id_posting(self, term, doc_id, posting):
        self.pipe.hset("&%s"%term, doc_id, posting)      
        
            
    def term_remove_doc_id_posting(self, term, doc_id):
        self.pipe.hdel("&%s"%term, doc_id)               


    def term_add_doc_id_title_posting(self, term, doc_id, posting):
        self.pipe.hset("&T%s"%term, doc_id, posting)      
        
            
    def term_remove_doc_id_title_posting(self, term, doc_id):
        self.pipe.hdel("&T%s"%term, doc_id)    


    def term_add_doc_id_title(self, term, doc_id):
        self.pipe.sadd("T%s"%term, doc_id)      
        
        
    def term_remove_doc_id_title(self, term, doc_id):
        self.pipe.srem("T%s"%term, doc_id)  


    def add_doc_id(self, internal_doc_id, external_doc_id):
        self.store_doc_id(internal_doc_id, external_doc_id, piped=True)
        self.pipe.sadd(self._set_key, internal_doc_id)   
        
        
    def remove_doc_id(self, doc_id):
        self.purge_doc_id(doc_id, piped=True)
        self.pipe.srem(self._set_key, doc_id)    


    def doc_id_exists(self, doc_id):
        internal_doc_id = self.resolve_external_id(doc_id)
        return self.db.sismember(self._set_key, internal_doc_id) 
        
                
    def get_term_df(self, term): 
        try: return math.log(  float(self.get_cardinality(piped=False)) / (float(self.db.zcard(term))) )
        except: return False
    
      
    def get_dfs(self, term_list):
        self.get_cardinality(piped=True)
        for term in term_list:  
            self.pipe.zcard(term)
        
        res = self.flush()
        # res[0] is cardinality and the rest are the dfs of every term 
        s = []
        cardinality = float(res[0])
        for i, item in enumerate(res[1:]):
            if item not in [None,0] : s.append( (term_list[i], math.log( cardinality/float(item))  ) )
 
        return s    

    
    def get_postings(self, term_list, docids_list):
        for term in term_list:  
            self.pipe.hmget("&%s"%term, docids_list)
        
        return self.flush()
    
  
    def get_title_hit(self, term_list, doc_ids_list):     
        _len = len(doc_ids_list)
        _sub_len = len(term_list)
        
        for term in term_list:
            for did in doc_ids_list:
                self.pipe.sismember("T%s"%term, did)

        res = self.flush()

        rank = []
        for i , v in enumerate(doc_ids_list):
            cnt = i
            sum = 0
            for i in xrange(_sub_len):
                sum += int(res[cnt])
                cnt += _len
            rank.append(sum)
            
        return rank    
            
            
            
            
            
            
            
            
            
            
            
            
            
########NEW FILE########
__FILENAME__ = lang
# -*- coding: utf-8 -*-

# code from http://misja.posterous.com/language-detection-with-python-nltk

from nltk.util import trigrams as nltk_trigrams
from nltk.tokenize import word_tokenize as nltk_word_tokenize
from nltk.probability import FreqDist
from nltk.corpus.util import LazyCorpusLoader
from nltk.corpus.reader.api import CorpusReader
from nltk.corpus.reader.util import StreamBackedCorpusView, concat



l_map = {"en": "english",
         "de": "german",
         "fr": "french",
         "es": "spanish",
         "nl": "dutch",
         "ru": "russian",
         "it": "italian",
         }


class LangIdCorpusReader(CorpusReader):
    '''
    LangID corpus reader
    '''
    CorpusView = StreamBackedCorpusView

    def _get_trigram_weight(self, line):
        '''
        Split a line in a trigram and its frequency count
        '''
        data = line.strip().split(' ')
        if len(data) == 2:
            return (data[1], int(data[0]))

    def _read_trigram_block(self, stream):
        '''
        Read a block of trigram frequencies
        '''
        freqs = []
        for i in range(20): # Read 20 lines at a time.
            freqs.append(self._get_trigram_weight(stream.readline()))
        return filter(lambda x: x != None, freqs)

    def freqs(self, fileids=None):
        '''
        Return trigram frequencies for a language from the corpus        
        '''
        return concat([self.CorpusView(path, self._read_trigram_block) 
                       for path in self.abspaths(fileids=fileids)])

class LangDetect(object):
    language_trigrams = {}
    langid            = LazyCorpusLoader('langid', LangIdCorpusReader, r'(?!\.).*\.txt')

    def __init__(self, languages=['nl', 'en', 'fr', 'de', 'es', "it"]):
        for lang in languages:
            self.language_trigrams[lang] = FreqDist()
            for f in self.langid.freqs(fileids=lang+"-3grams.txt"):
                self.language_trigrams[lang].inc(f[0], f[1])

    def detect(self, text):
        '''
        Detect the text's language
        '''
        words    = nltk_word_tokenize(text.lower())
        trigrams = {}
        scores   = dict([(lang, 0) for lang in self.language_trigrams.keys()])

        for match in words:
            for trigram in self.get_word_trigrams(match):
                if not trigram in trigrams.keys():
                    trigrams[trigram] = 0
                trigrams[trigram] += 1

        total = sum(trigrams.values())

        for trigram, count in trigrams.items():
            for lang, frequencies in self.language_trigrams.items():
                # normalize and add to the total score
                scores[lang] += (float(frequencies[trigram]) / float(frequencies.N())) * (float(count) / float(total))
        
        
        # special case
        # if all scores are 0.0 we return None
        s = 0.0
        for score in scores.itervalues():
            s += score

        if s == 0.0:
            return None

        return l_map[ sorted(scores.items(), key=lambda x: x[1], reverse=True)[0][0] ]
    
    

    def get_word_trigrams(self, match):
        return [''.join(trigram) for trigram in nltk_trigrams(match) if trigram != None]
    
    
    
    
    
    
    
    
    
    
    
if __name__=="__main__":
    import time
    
    texts = [
     "De snelle bruine vos springt over de luie hond",
     "The quick brown fox jumps over the lazy dog",
     "Le renard brun rapide saute par-dessus le chien paresseux",
     "Der schnelle braune Fuchs springt über den faulen Hund",
     "El rápido zorro marrón salta sobre el perro perezoso",
     "организовывал забастовки и демонстрации, поднимал рабочих на бакинских предприятия",
     "dette er hvad jeg kalder den store design af en perfekt lort",
     "di nuovo",
   ]

    ld = LangDetect()
    
    for text in texts:
        t = time.time()
        print text, "=>", ld.detect(text) , time.time() - t
########NEW FILE########
__FILENAME__ = lua_scripts
'''
BIG FAT DISCLAIMER:

This is my very first lua endeavor. Purely amateur code. 
'''



exec_multi_query_script="""

local function split(str, pat)
   local t = {}  -- NOTE: use {n = 0} in Lua-5.0
   local fpat = "(.-)" .. pat
   local last_end = 1
   local s, e, cap = str:find(fpat, 1)
   while s do
      if s ~= 1 or cap ~= "" then
     table.insert(t,cap)
      end
      last_end = e+1
      s, e, cap = str:find(fpat, last_end)
   end
   if last_end <= #str then
      cap = str:sub(last_end)
      table.insert(t, cap)
   end
   return t
end

-------------------------------------------------------------------------------

local function unfold_postings(list_of_lists)
   local new_list_of_lists = {}
   
   local transform = {}
   for i=1, #list_of_lists do
       table.insert(transform, split(list_of_lists[i], ",") )
   end
   
   for i=1, #transform do
       local nlist = {}
       local pos = 0
       for j=1, #transform[i] do
           pos = pos + transform[i][j]
           table.insert(nlist, pos)
       end
       table.insert(new_list_of_lists, nlist) 
         
    end

   return new_list_of_lists    
end

-------------------------------------------------------------------------------

local function comp(a,b)
  return #a > #b
end

-------------------------------------------------------------------------------

local function proximity_rank(list_of_lists)

        local _len = #list_of_lists

        --add padding to shorter posting
        local max = 0
        for i=1, #list_of_lists do
            if (#list_of_lists[i] > max) then max = #list_of_lists[i] end
        end
        
        
        
        local tt = {}
        
        for i, v in ipairs(list_of_lists) do
            if (#v < max) then 
               local m = v[1]
               local t = {}
                for j=#v+1, max do 
                    table.insert(t, m)
                end
                local ii=0
                for i=#t, #v+#t do
                    ii = ii + 1
                    t[i] = v[ii]
                end
                table.insert(tt, t)
            else
                 table.insert(tt, v)
            end
        end
        
        local score = 0
        local tuple = {}
        local drop = false
       
       
        while true do
            
            local tuple = {}
            for i=1, #tt do
                local a = table.remove(tt[i], 1)
                if (a and a ~= 0 ) then table.insert(tuple, a) else drop = true end
            end
            
            local i=2
            while i <= #tuple do
              if ((tuple[i] - tuple[i - 1]) < 0) then
                    table.remove(tuple, i)
                    local a = table.remove(tt[i], 1)
                    if (a and a ~= 0  and a ~= nil ) then 
                      table.insert(tuple, i, a) 
                    elseif  a == nil then
                       drop = true
                       break            
                    else 
                        i = i + 1
                    end 
              else
                  i = i + 1
              end
            end
 
            if drop then 
                break 
            else
                score = score + 1/(tuple[#tuple] - tuple[1] - _len + 1)
            end         

        end

        if score == math.huge then return 1 else
        return tostring(score)
        end
end

-------------------------------------------------------------------------------

local function weighted_ranking(tfidf, title, posting)
    local t = 0
    t = t + 0.33*tfidf + 0.33*title + 0.33*posting
    return tostring(t)

end


-------------------------------------------------------------------------------


local cardinality = redis.call('scard', '$DOCIDS$')

local terms = {}
local weights = {}
local size = #ARGV - 1
local limit = ARGV[size + 1]
local query_key = ""

for i=1, size  do
  local j = redis.call('zcard', ARGV[i])
  query_key = query_key .. ARGV[i]
  if (j ~= nil and j ~= 0) then
      table.insert(terms, ARGV[i])
      table.insert(weights, tostring(math.log((cardinality/j))))
  end
end

-- optimize, return {} if any weight is 0
if (#weights ~= size) then return {} end


local ids = {}
local tfidf = {}

-- limit query to use these ids only
if (#KEYS > 0) then

    
    for i=1, #KEYS do
      local id = redis.call('hget', "$DOCIDMAP$", KEYS[i])
      if (id) then table.insert(ids,id) end
    end
    
    
    for i=1, #ids do
        local t = 0
        for j=1, #terms do
            t = t + redis.call('zscore', terms[j], ids[i]) * weights[j]
        end
        table.insert(tfidf,t)
    end



-- normal query
else

    -- to much code to call a single zintersore
    local args = {'zinterstore', query_key, size, unpack(terms) }
    args[#args + 1] = 'WEIGHTS'
    
    for i=1, #weights do
        table.insert(args, weights[i])
    end
    
    
    redis.call(unpack(args))
    local res = redis.call('zrevrange', query_key, 0, limit, "WITHSCORES")
    
    
    

    for j=1, #res, 2 do
      table.insert(ids,res[j])
    end
    

    for j=2, #res, 2 do
      table.insert(tfidf,res[j])
    end

end


--RANKING

--RANK BY TITLE

local hits = {}

for i=1, #terms do
    for j=1, #ids do
      table.insert(hits,redis.call('sismember', 'T' .. terms[i], ids[j]))
    end
end

local t_rank = {}

for i=1, #ids do
   local cnt = i
   local sum = 0
   for j=1, #terms do
       sum = sum + hits[cnt]
       cnt = cnt + #ids
   end 
   table.insert(t_rank, sum)
end

--RANK BY POSTINGS
local post = {}
for i=1, #terms do
    table.insert(post, redis.call('hmget', '&' .. terms[i], unpack(ids)))
end

--decompose list of lists
local d_lists = {}
for i=1, #post[1] do
    local t = {}
    for j=1, #post do
        table.insert(t, post[j][i])
    end
    table.insert(d_lists, t)
end

local p_rank = {}

for i=1, #d_lists do
    table.insert(p_rank, proximity_rank(unfold_postings(d_lists[i])))
end

local results = {}


for i=1, #ids do
    table.insert(results, {redis.call('hget', "$DOCIDMAP$", ids[i]), weighted_ranking(tfidf[i], t_rank[i], p_rank[i])})
end


local function compare(a,b)
  return b[2] < a[2]
end
table.sort(results, compare)

return results

"""




exec_single_query_script = """
local query = ARGV[1]
local limit = ARGV[2]
local res = redis.call('zrevrange', query, 0, limit, "WITHSCORES")

local ids = {}
local size = #res

for i=1, size, 2 do
  table.insert(ids,{redis.call('hget', "$DOCIDMAP$", res[i]), tostring(redis.call('sismember', 'T' .. query, res[i]) + res[i+1])})
end

local function compare(a,b)
  return b[2] < a[2]
end


table.sort(ids, compare)

return ids
"""
########NEW FILE########
__FILENAME__ = query_handler
#!/usr/bin/python2.6.5
# -*- coding: utf-8 -*-
#
# Copyright 2011 Christos Spiliopoulos.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import index_handler


import re
import itertools
import operator
import math




try:
    import msgpack
    serializer = msgpack
except:
    import json
    serializer = json


from lua_scripts import *


import stringcheck  # super fast, C extension, returns True for alphanumerics only and non stopwords

FILTERS = {
           "complete": re.compile("/complete"),
           "pure_tfidf" : re.compile("/pure_tfidf"),
           "title_only" : re.compile("/title_only")
           }
           




class QueryHandler(index_handler.IndexHandler):
    '''
    A class that handles queries upon our INDEX.
    
    It provides functions to deal with boolean retrieval or vector space model retrieval.
        
    '''
    
    def __init__(self, **kwargs):
        index_handler.IndexHandler.__init__(self,  **kwargs)    
        self.limit = kwargs.get('limit',10) 
        self.query = "" 
        self.filters = set()
        self.known_filters = FILTERS
        self.debug = kwargs.get('debug',True)         
        self.res_cache_db = kwargs.get('res_cache_db',None)  
        self.res_cache_exp = kwargs.get('res_cache_exp',100)
        self.serializer = serializer
        self.tfidf_w = kwargs.get('tfidf_w',0.33)
        self.title_w = kwargs.get('title_w',0.33)
        self.posting_w = kwargs.get('posting_w',0.33)
        
        self.use_lua = kwargs.get('use_lua',False)
        if self.use_lua:
            self.exec_single_query_lua = self.db.register_script(exec_single_query_script)
            self.exec_multi_query_lua = self.db.register_script(exec_multi_query_script)
            



    def clear(self):
        self.filters = set()
        self.query = ""         
 
        
    def process_query(self, query, ids=[]):
        ''' entry point for query processing '''
        
        self.clear()
        self.identify_language(query)
        initial_query = query
        self.query = query
        
        if self.debug: print "INITIAL QUERY:", initial_query
        
        self.apply_filters()
        self.clean_stem_query()
                   
        if len(self.query.split()) == 1:             
            res = self.exec_single_query(self.query)    
        elif "title_only" in self.filters:             
            res = self.get_titles(self.query.split())                
        else:     
            if self.use_lua:
                args = self.query.split()
                args.append(self.limit)
                if not len(ids): 
                    return self.exec_multi_query_lua(args=args)
                else:
                    return self.exec_multi_query_lua(keys=ids, args=args)
            else:                                              
                weighted_terms = self.filter_query()  
                if not len(ids): 
                    res = self.vector_retrieval(weighted_terms)
                else:
                    res = self.limited_vector_retrieval(weighted_terms, ids)

        if res:   
            if not self.use_lua:
                external_ids = self.resolve_external_ids([i[0] for i in res])
                res = [(external_ids[i], res[i][1]) for i in xrange(len(res))]
            if self.res_cache_db:
                try:
                    self.res_cache_db.set(initial_query, self.serializer.dumps(res))
                except:
                    raise Exception, "CACHING SEARCH RESULT FAILED, UNREACHABLE DB"    
    
        return res
        



    def apply_filters(self):
        for i in self.known_filters:   
            if re.search(self.known_filters[i], self.query.split()[-1]):
                self.filters.add(i)
                self.query = re.sub(self.known_filters[i],"",self.query)   
                 
        if self.debug: print "WITH FILTERS:", self.filters        
        if not len(self.filters): self.filters.add("complete")
        
        

    def clean_stem_query(self):
        q = ""
        for token in re.sub(r"[.,:;\-!?\"']", " ", self.query).split():
            try: 
                lower = token.lower()
                if self.legal_token(lower):
                    item = self.stem(lower.decode("utf8", "ignore"))
                    if item:
                        q += item + " " 
                #if stringcheck.check(lower):
                #    q += self.stem(lower) + " "         
            except: 
                if self.debug: print "Probable unicode error in stemming query"  , q
                
        self.query = q    
        if self.debug: print "STEMMED QUERY:", self.query



    def filter_query(self):
        ''' 
        Discovers document frequencies of query terms
        Returns a list of tuples of all terms that appear in the index
        Format = (term,df)
        '''
        return self.get_dfs(self.query.split())


    def exec_single_query(self, query):
        ''' optimized for a single query '''
        if self.debug: print "In exec single query"
        q = query.strip()
        if "title_only" in self.filters:
            return [(i,1) for i in self.db.smembers("T%s"%q)]
        elif "pure_tfidf" in self.filters:    
            return self.db.zrevrange(q, 0, self.limit - 1 , withscores=True)
        else:
            if self.use_lua:
                return self.exec_single_query_lua(args=[q,self.limit])
            else:
                res = self.db.zrevrange(q, 0, self.limit - 1 , withscores=True)
                dids = list([i[0] for i in res])
                title_rank = self.get_title_hit([q], dids)
                new_doc_ids = []
                for i, stuff in enumerate(res):
                    new_doc_ids.append( (stuff[0], self.weighted_ranking(tfidf=stuff[1], title=title_rank[i])) )    
                    
                if self.debug: print "RESULTS " ,   sorted(new_doc_ids, key=operator.itemgetter(1), reverse=True)
                
                return sorted(new_doc_ids, key=operator.itemgetter(1), reverse=True)
        

    def get_titles(self, term_list):
        docs = list(self.db.sinter(["T%s"%term for term in term_list]))
        if docs:
            for term in term_list:  
                self.pipe.hmget("&T%s"%term, docs)
                
                
            ranked = []    
            for i, v in enumerate(itertools.izip_longest(*self.flush())): 
                score = 0
                for j in xrange(len(v) - 1):
                    score += 1.0/(float(v[j+1]) - float(v[j]))
                ranked.append((docs[i], score))
                
            return sorted(ranked, key=operator.itemgetter(1), reverse=True)
        
        return []


    def vector_retrieval(self, weighted_terms):
        ''' 
        A function to start vector space model retrieval
        Intersects all docIDs for every term in term_list
        Returns sorted tfidf-weighted docids
        '''
        if self.debug: print "performing vector retrieval on " , weighted_terms
        terms = [i[0] for i in weighted_terms]
        query_key = "".join(terms)

        self.pipe.zinterstore(query_key, dict(weighted_terms))
        self.pipe.zrevrange(query_key, 0, self.limit - 1 , withscores=True)
        
        doc_ids = self.flush()[1]
        if not len(doc_ids):
            return None
        return self.rank_results(doc_ids, terms) 


            
    def limited_vector_retrieval(self, weighted_terms, ids):
        ''' 
        Performs only on specific ids
        '''

        if self.debug: print "performing limited vector retrieval on " , weighted_terms
        terms = [i[0] for i in weighted_terms]
        

        internal_ids = [i for i in self.resolve_external_ids(ids) if i]
        _len = len(internal_ids)
        _tlen = len(terms)

        self.get_cardinality(piped=True)
        for id in internal_ids:
            for term in terms:
                self.pipe.zscore(term, id)
                
        res = self.flush()
        print res
        cardinality = res[0]
        r = res[1:]
        doc_ids = []

        for i, id in enumerate(internal_ids):
            t = 0.0
            for tf in r[i*_tlen:(i*_tlen + _tlen)]:
                if tf is None:
                    continue
                t += tf * float(weighted_terms[i%_tlen][1])
            if t > 0.0:
                doc_ids.append((id, t))


        return self.rank_results(doc_ids, terms) 
            
        

    def rank_results(self, doc_ids, terms):

        if "pure_tfidf" in self.filters:
            if self.debug: print "RESULTS ", doc_ids
            return doc_ids

        elif "complete" in self.filters:
            
            dids = list([i[0] for i in doc_ids])
            
            # rank by title
            title_rank = self.get_title_hit(terms, dids)
            
            # must do proximity ranking
            # get the posting lists
            sh = self.get_postings(terms, dids) # actually, I wanted to name this "shit"


            posting_rank = []

            for v in itertools.izip_longest(*sh):      # decompose list of lists  
                
                try: posting_rank.append( ( self.proximity_rank( self.unfold_postings([ [int(k) for k in j.split(",")] for j in v]) ) ) )
                except: posting_rank.append(0)
                
            new_doc_ids = []
            
            for i, stuff in enumerate(doc_ids):
                new_doc_ids.append( (stuff[0], self.weighted_ranking(tfidf=stuff[1], title=title_rank[i], posting=posting_rank[i] )) )    
                
            if self.debug: print "RESULTS " ,   sorted(new_doc_ids, key=operator.itemgetter(1), reverse=True)
            
            return sorted(new_doc_ids, key=operator.itemgetter(1), reverse=True)
        

    
    


  
            
        

#############################################################################################################
# RANKING FUNCTIONS
#############################################################################################################  


    def weighted_ranking(self, **kwargs):
        '''
        kwargs carry the scores to be multiplied
        '''
        tfidf = kwargs.get('tfidf', 0)
        title = kwargs.get('title', 0)
        posting = kwargs.get('posting', 0)
        
        return tfidf*self.tfidf_w + title*self.title_w + posting*self.posting_w
        


    def proximity_rank(self, list_of_lists):  
        '''
        A ranking function that calculates a score for words' proximity.
        This score is defined as the sum of 1/Prox for every continuous matches of them.
        Prox is a number indicating how close the words are
        
        example: for words A and B, their postings are [1,4,10] and [2,6,17]
        
                 then score = 1/(2 - 1 + 1) + 1/(6 - 4 + 1) + 1/(17 - 10 + 1)
        '''        
        def sub(*args):
            return reduce(lambda x, y: y-x, args )
        
        _len = len(list_of_lists) - 1
        
        # add padding to shorter lists
        biggest = max([len(i) for i in list_of_lists])
        
        for i in list_of_lists:
            while len(i) != biggest:
                i.insert(0,i[0])
                
        
        score = 0

        while True: 
            
            try:
                # get all heads
                _tuple = [i.pop(0) for i in list_of_lists]
                for i in xrange(1,len(_tuple)):
                    # ensure we keep order of postings
                    while _tuple[i] - _tuple[i-1] < 0:
                        _tuple.pop(i)
                        _tuple.insert(i, list_of_lists[i].pop(0))

                        
                
                score_vector =  [i - _len for i in map(sub, _tuple)]       
                #print _tuple  , score_vector[-1] - score_vector[0] - _len + 1
                score += 1.0/(score_vector[-1] - score_vector[0] - _len + 1) # ensure no division with 0

            except: break
            
        return score



                

#############################################################################################################
# HELPER FUNCTIONS
#############################################################################################################  

 
    def unfold_postings(self, list_of_lists):
        ''' reverses gap encoding '''
        new_list_of_lists = []
        
        for _list in list_of_lists:
            nlist = []
            pos = 0

            for p in _list:
                pos += p
                nlist.append(pos)
                
            new_list_of_lists.append(nlist)

        return new_list_of_lists      
   




    




########NEW FILE########
__FILENAME__ = quick_language_detection
# -*- coding: utf-8 -*-

try:
    from nltk.corpus import stopwords
except ImportError:
    print '[!] You need to install nltk (http://nltk.org/index.html)'
    
from HTMLParser import HTMLParser



class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)
    
    

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()



#----------------------------------------------------------------------
def _calculate_languages_ratios(words):
    """
    Calculate probability of given text to be written in several languages and
    return a dictionary that looks like {'french': 2, 'spanish': 4, 'english': 0}
    
    @param text: Text whose language want to be detected
    @type text: str
    
    @return: Dictionary with languages and unique stopwords seen in analyzed text
    @rtype: dict
    """

    languages_ratios = {}


    # Compute per language included in nltk number of unique stopwords appearing in analyzed text
    for language in stopwords.fileids():
        stopwords_set = set(stopwords.words(language))
        words_set = set(words)
        common_elements = words_set.intersection(stopwords_set)

        languages_ratios[language] = len(common_elements) # language "score"

    return languages_ratios


#----------------------------------------------------------------------
def detect_language(words):
    """
    Calculate probability of given text to be written in several languages and
    return the highest scored.
    
    It uses a stopwords based approach, counting how many unique stopwords
    are seen in analyzed text.
    
    @param text: Text whose language want to be detected
    @type text: str
    
    @return: Most scored language guessed
    @rtype: str
    """

    ratios = _calculate_languages_ratios(words)
    most_rated_language = max(ratios, key=ratios.get)
    return most_rated_language


langs = { "english" : set(["a", "b", "c", "d" , "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x","y", "z"]),
          "greek" : set([i.decode("utf-8") for i in ["α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "ι", "κ", "λ", "μ", "ν", "ξ", "ο", "π", "ρ", "σ", "τ", "υ", "φ" ,"χ", "ψ" ,"ω"]]),
          "russian" : set(["А", "Б", "В", "Г", "Д", "Е", "Ё", "Ж", "З", "И", "Й", "К", "Л", "М", "Н", "О", "П", "Р", "С", "Т", "У", "Ф", "Х", "Ц", "Ч", "Ш", "Щ", "Ъ", "Ы", "Ь", "Э", "Ю", "Я"]),
         }
from operator import itemgetter
from collections import defaultdict
def _check_lang(text, max_len=2000):
    
    cnt = defaultdict(int)
    t = strip_tags(text[:max_len])
    if type(t) is str:
        t = t.decode("utf-8","replace")

    
    for lang, letters in langs.iteritems():
        for i in t:
            if i != " " and i in letters:
                cnt[lang] += 1
                
            if cnt[lang] > len(text) / 2:
                return lang
            
    
    for key, v in sorted(cnt.iteritems(), key=itemgetter(1), reverse=True):
        return key


def check_lang(text, max_len=2000):
    t = strip_tags(text[:max_len])
    lang = _check_lang(t)

    if lang == "english":
        words = [i.encode("utf-8","ignore") for i in t.split()]
        lang = detect_language(words)
        
    return lang




if __name__=='__main__':


    
    import time
    
    texts = [
     "The quick brown fox jumps over the lazy dog and fucks the hell out of it",
     "Den raske brune reven hopper over den late hunden og knuller i helvete ut av det",
     "Den hurtige brune ræv hopper over den dovne hund og knepper fanden ud af det",
     "Быстрая коричневая лиса прыгает через ленивую собаку и трахает ад из этого",
     "De snelle bruine vos springt over de luie hond en neukt de hel van te maken",
     "Nopea ruskea kettu hyppää laiskan koiran yli ja vittuile helvettiin siitä",
     "Le rapide renard brun saute par dessus le chien paresseux et baise l'enfer hors de lui",
     "Der schnelle braune Fuchs springt über den faulen Hund und fickt die Hölle aus ihm heraus",
     "A gyors barna róka átugorja a lusta kutyát, és baszik a fenébe is",
     "La volpe veloce salta sul cane pigro e scopa l'inferno fuori di esso",
     "A ligeira raposa marrom ataca o cão preguiçoso e fode o inferno fora dele",
     "El rápido zorro marrón salta sobre el perro perezoso y folla el infierno fuera de él",
     "En snabb brun räv hoppar över den lata hunden och knullar skiten ur det",
     "Hızlı kahverengi tilki tembel köpeğin üstünden atlar ve bunun cehenneme sikikleri",
     "Η γρήγορη καφέ αλεπού πηδάει πάνω από το μεσημέρι και πηδάει την κόλαση έξω από αυτό"
     ]


    
    for text in texts:
        t = time.time()
        print check_lang(text), "=>", text, time.time() - t
########NEW FILE########
__FILENAME__ = sensitive_language_detection
#!/usr/bin/python2.6.5
# -*- coding: utf-8 -*-
#
# Copyright 2011 Christos Spiliopoulos.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



__authors__ = [
  '"Christos Spiliopoulos" <santos.koniordos@gmail.com>',
]




from collections import defaultdict
from operator import itemgetter
import re


# Simple (non-strict) rule to identify a language
# We keep a dictionary of the form {language_name: set([letters_of_this_language])}
# if the sum of the num of letters in some text are greater than 1>2 of the text's length, we declare it to be of this language

langs = { "english" : set(["a", "b", "c", "d" , "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x","y", "z"]),
          "greek" : set([i.decode("utf-8") for i in ["α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "ι", "κ", "λ", "μ", "ν", "ξ", "ο", "π", "ρ", "σ", "τ", "υ", "φ" ,"χ", "ψ" ,"ω"]]),
          "russian" : set(["А", "Б", "В", "Г", "Д", "Е", "Ё", "Ж", "З", "И", "Й", "К", "Л", "М", "Н", "О", "П", "Р", "С", "Т", "У", "Ф", "Х", "Ц", "Ч", "Ш", "Щ", "Ъ", "Ы", "Ь", "Э", "Ю", "Я"]),
         }


from lang import LangDetect


from HTMLParser import HTMLParser



class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)
    
    

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()



def _check_lang(text, max_len=2000):
    
    cnt = defaultdict(int)
    t = strip_tags(text[:max_len])
    if type(t) is str:
        t = t.decode("utf-8","replace")

    
    for lang, letters in langs.iteritems():
        for i in t:
            if i != " " and i in letters:
                cnt[lang] += 1
                
            if cnt[lang] > len(text) / 2:
                return lang
            
    
    for key, v in sorted(cnt.iteritems(), key=itemgetter(1), reverse=True):
        return key
    
    
    
    
'''def check_lang(text, max_len=2000):
    t = strip_tags(text[:max_len])
    ld = LangDetect()
    lang = ld.detect(t)
    if not lang:
        lang = _check_lang(t)
        
    return lang'''
    
def check_lang(text, max_len=2000):
    t = strip_tags(text[:max_len])
    lang = _check_lang(t)

    if lang == "english":
        ld = LangDetect()
        lang = ld.detect(t)
        
        
    return lang
    
    
if __name__=="__main__":
    import time
    
    texts = [
     "The quick brown fox jumps over the lazy dog and fucks the hell out of it",
     "Den raske brune reven hopper over den late hunden og knuller i helvete ut av det",
     "Den hurtige brune ræv hopper over den dovne hund og knepper fanden ud af det",
     "Быстрая коричневая лиса прыгает через ленивую собаку и трахает ад из этого",
     "De snelle bruine vos springt over de luie hond en neukt de hel van te maken",
     "Nopea ruskea kettu hyppää laiskan koiran yli ja vittuile helvettiin siitä",
     "Le rapide renard brun saute par dessus le chien paresseux et baise l'enfer hors de lui",
     "Der schnelle braune Fuchs springt über den faulen Hund und fickt die Hölle aus ihm heraus",
     "A gyors barna róka átugorja a lusta kutyát, és baszik a fenébe is",
     "La volpe veloce salta sul cane pigro e scopa l'inferno fuori di esso",
     "A ligeira raposa marrom ataca o cão preguiçoso e fode o inferno fora dele",
     "El rápido zorro marrón salta sobre el perro perezoso y folla el infierno fuera de él",
     "En snabb brun räv hoppar över den lata hunden och knullar skiten ur det",
     "Hızlı kahverengi tilki tembel köpeğin üstünden atlar ve bunun cehenneme sikikleri",
     "Η γρήγορη καφέ αλεπού πηδάει πάνω από το μεσημέρι και πηδάει την κόλαση έξω από αυτό"
     ]


    
    for text in texts:
        t = time.time()
        print check_lang(text), "=>", text, time.time() - t
        
        
    '''import feedparser
    
    a = feedparser.parse("http://www.koutipandoras.gr/feed")
    
    t = a["entries"][6]
    print check_lang(t["content"][0]["value"])'''
########NEW FILE########
__FILENAME__ = greek
# -*- coding: utf-8  -*-

stopwords = ["είναι", "θέλω","ἀλλά", "κατά", "αυτός", "αυτή", "αυτό", "μετά", "περί", "ούτε", "παρά", "εμείς", "εσείς", "αυτοί", "αυτές", "αυτά", "είσαι","ηταν", "είμαστε",
             "είσαστε", "όπως", "χωρίς", "στους","οποία", "τρεις", "ακόμα","περίπου", "έχουν", "οποίος"]

VOWELS = ['α', 'ε', 'η', 'ι', 'ο', 'υ', 'ω', 'ά', 'έ', 'ή', 'ί', 'ό', 'ύ', 'ώ', 'ϊ', 'ϋ']


replacements = {"Α":"α", "Β":"β", "Γ":"γ", "Δ":"δ", "Ε":"ε", "Ζ":"ζ", 'Η':'η', 'Θ':'θ', 'Ι':'ι', 
                'Κ':'κ','Λ':'λ','Μ':'μ','Ν':'ν','Ξ':'ξ','Ο':'ο','Π':'π','Ρ':'ρ','Σ':'σ','Τ':'τ','Υ':'υ','Φ':'φ',
                'Χ':'χ','Ψ':'ψ', 'Ω':'ω',
                'Ά':'α', 'Έ':'ε', 'Ή':'η', 'Ί':'ι', 'Ό':'ο', 'Ύ':'υ', 'Ώ':'ω', 'Ϊ':'ι', 'Ϋ':'υ',
                'ά':'α', 'έ':'ε', 'ή':'η', 'ί':'ι', 'ό':'ο', 'ύ':'υ', 'ώ':'ω', 'Ϊ':'ϊ', 'Ϋ':'ϋ'}


r = {}
for k, v in replacements.iteritems():
    r[k.decode("utf-8")] = v.decode("utf-8")

def ends_with(word, suffix):
    return word[len(word) - len(suffix):] == suffix

def stem(w):
    
    
    word = ""

    for i in w.decode("utf-8"):
        if i in r:
            word += r[i]
        else:
            word += i


    done = len(word) <= 3
    
    ##rule-set  1
    ##γιαγιαδεσ->γιαγ, ομαδεσ->ομαδ
    if not done:
        for suffix in ['ιαδες', 'αδες', 'αδων']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                remaining_part_does_not_end_on = True
                for s in ['οκ', 'μαμ', 'μαν', 'μπαμπ', 'πατερ', 'γιαγ', 'νταντ', 'κυρ', 'θει', 'πεθερ']:
                    if ends_with(word, s):
                        remaining_part_does_not_end_on = False
                        break
                if remaining_part_does_not_end_on:
                    word = word + 'αδ'
                done = True
                break

    ##rule-set  2
    ##καφεδεσ->καφ, γηπεδων->γηπεδ
    if not done:
        for suffix in ['εδες', 'εδων']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                for s in ['οπ', 'ιπ', 'εμπ', 'υπ', 'γηπ', 'δαπ', 'κρασπ', 'μιλ']:
                    if ends_with(word, s):
                        word = word + 'εδ'
                        break
                done = True
                break

    ##rule-set  3
    ##παππουδων->παππ, αρκουδεσ->αρκουδ
    if not done:
        for suffix in ['ουδες', 'ουδων']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                for s in ['αρκ', 'καλιακ', 'πεταλ', 'λιχ', 'πλεξ', 'σκ', 'ς', 'φλ', 'φρ', 'βελ', 'λουλ', 'χν', 'σπ', 'τραγ', 'φε']:
                    if ends_with(word, s):
                        word = word + 'ουδ'
                        break
                done = True
                break

    ##rule-set  4
    ##υποθεσεωσ->υποθεσ, θεων->θε
    if not done:
        for suffix in ['εως', 'εων']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                for s in ['θ', 'δ', 'ελ', 'γαλ', 'ν', 'π', 'ιδ', 'παρ']:
                    if ends_with(word, s):
                        word = word + 'ε'
                        break
                done = True
                break

    ##rule-set  5
    ##παιδια->παιδ, τελειου->τελει
    if not done:
        for suffix in ['ια', 'ιου', 'ιων']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                for s in VOWELS:
                    if ends_with(word, s):
                        word = word + 'ι'
                        break
                done = True
                break

    ##rule-set  6
    ##ζηλιαρικο->ζηλιαρ, αγροικοσ->αγροικ
    if not done:
        for suffix in ['ικα', 'ικου', 'ικων', 'ικος', 'ικο', 'ικη']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['αλ', 'αδ', 'ενδ', 'αμαν', 'αμμοχαλ', 'ηθ', 'ανηθ', 'αντιδ', 'φυς', 'βρωμ', 'γερ', 'εξωδ', 'καλπ',
                            'καλλιν', 'καταδ', 'μουλ', 'μπαν', 'μπαγιατ', 'μπολ', 'μπος', 'νιτ', 'ξικ', 'συνομηλ', 'πετς', 'πιτς',
                            'πικαντ', 'πλιατς', 'ποντ', 'ποστελν', 'πρωτοδ', 'σερτ', 'συναδ', 'τσαμ', 'υποδ', 'φιλον', 'φυλοδ',
                            'χας']:
                    word = word + 'ικ'
                else:
                    for s in VOWELS:
                        if ends_with(word, s):
                            word = word + 'ικ'
                            break
                done = True
                break

    ##rule-set  7
    ##αγαπαγαμε->αγαπ, αναπαμε->αναπαμ
    if not done:
        if word == 'αγαμε': word = 2*word
        for suffix in ['ηθηκαμε', 'αγαμε', 'ησαμε', 'ουσαμε', 'ηκαμε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['φ']:
                    word = word + 'αγαμ'
                done = True
                break
        if not done and ends_with(word, 'αμε'):
            word = word[:len(word) - len('αμε')]
            if word in ['αναπ', 'αποθ', 'αποκ', 'αποστ', 'βουβ', 'ξεθ', 'ουλ', 'πεθ', 'πικρ', 'ποτ', 'σιχ', 'χ']:
                word = word + 'αμ'
            done = True

    ##rule-set  8
    ##αγαπησαμε->αγαπ, τραγανε->τραγαν
    if not done:
        for suffix in ['ιουντανε', 'ιοντανε', 'ουντανε', 'ηθηκανε', 'ουσανε', 'ιοτανε', 'οντανε', 'αγανε', 'ησανε',
                       'οτανε', 'ηκανε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['τρ', 'τς', 'φ']:
                    word = word + 'αγαν'
                done = True
                break
        if not done and ends_with(word, 'ανε'):
            word = word[:len(word) - len('αμε')]
            if word in ['βετερ', 'βουλκ', 'βραχμ', 'γ', 'δραδουμ', 'θ', 'καλπουζ', 'καστελ', 'κορμορ', 'λαοπλ', 'μωαμεθ', 'μ',
                        'μουσουλμ', 'ν', 'ουλ', 'π', 'πελεκ', 'πλ', 'πολις', 'πορτολ', 'σαρακατς', 'σουλτ', 'τσαρλατ', 'ορφ',
                        'τσιγγ', 'τσοπ', 'φωτοστεφ', 'χ', 'ψυχοπλ', 'αγ', 'ορφ', 'γαλ', 'γερ', 'δεκ', 'διπλ', 'αμερικαν', 'ουρ',
                        'πιθ', 'πουριτ', 'ς', 'ζωντ', 'ικ', 'καστ', 'κοπ', 'λιχ', 'λουθηρ', 'μαιντ', 'μελ', 'σιγ', 'σπ', 'στεγ',
                        'τραγ', 'τσαγ', 'φ', 'ερ', 'αδαπ', 'αθιγγ', 'αμηχ', 'ανικ', 'ανοργ', 'απηγ', 'απιθ', 'ατσιγγ', 'βας',
                        'βασκ', 'βαθυγαλ', 'βιομηχ', 'βραχυκ', 'διατ', 'διαφ', 'ενοργ', 'θυς', 'καπνοβιομηχ', 'καταγαλ', 'κλιβ',
                        'κοιλαρφ', 'λιβ', 'μεγλοβιομηχ', 'μικροβιομηχ', 'νταβ', 'ξηροκλιβ', 'ολιγοδαμ', 'ολογαλ', 'πενταρφ',
                        'περηφ', 'περιτρ', 'πλατ', 'πολυδαπ', 'πολυμηχ', 'στεφ', 'ταβ', 'τετ', 'υπερηφ', 'υποκοπ', 'χαμηλοδαπ',
                        'ψηλοταβ']:
                word = word + 'αν'
            else:
                for s in VOWELS:
                    if ends_with(word, s):
                        word = word + 'αν'
                        break
            done = True

    ##rule-set  9
    ##αγαπησετε->αγαπ, βενετε->βενετ
    if not done:
        if ends_with(word, 'ησετε'):
            word = word[:len(word) - len('ησετε')]
            done = True
        elif ends_with(word, 'ετε'):
            word = word[:len(word) - len('ετε')]
            if word in ['αβαρ', 'βεν', 'εναρ', 'αβρ', 'αδ', 'αθ', 'αν', 'απλ', 'βαρον', 'ντρ', 'σκ', 'κοπ', 'μπορ', 'νιφ', 'παγ',
                        'παρακαλ', 'σερπ', 'σκελ', 'συρφ', 'τοκ', 'υ', 'δ', 'εμ', 'θαρρ', 'θ']:
                word = word + 'ετ'
            else:
                for s in ['οδ', 'αιρ', 'φορ', 'ταθ', 'διαθ', 'σχ', 'ενδ', 'ευρ', 'τιθ', 'υπερθ', 'ραθ', 'ενθ', 'ροθ', 'σθ', 'πυρ',
                          'αιν', 'συνδ', 'συν', 'συνθ', 'χωρ', 'πον', 'βρ', 'καθ', 'ευθ', 'εκθ', 'νετ', 'ρον', 'αρκ', 'βαρ', 'βολ',
                          'ωφελ'] + VOWELS:
                    if ends_with(word, s):
                        word = word + 'ετ'
                        break
            done = True

    ##rule-set 10
    ##αγαπωντασ->αγαπ, ξενοφωντασ->ξενοφων
    if not done:
        for suffix in ['οντας', 'ωντας']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['αρχ']:
                    word = word + 'οντ'
                elif word in ['ξενοφ', 'κρε']:
                    word = word + 'ωντ'
                done = True
                break

    ##rule-set 11
    ##αγαπιομαστε->αγαπ, ονομαστε->ονομαστ
    if not done:
        for suffix in ['ιομαστε', 'ομαστε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['ον']:
                    word = word + 'ομαστ'
                done = True
                break

    ##rule-set 12
    ##αγαπιεστε->αγαπ, πιεστε->πιεστ
    if not done:
        for suffix in ['ιεστε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['π', 'απ', 'συμπ', 'ασυμπ', 'καταπ', 'μεταμφ']:
                    word = word + 'ιεστ'
                done = True
                break
    if not done:
        for suffix in ['εστε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['αλ', 'αρ', 'εκτελ', 'ζ', 'μ', 'ξ', 'παρακαλ', 'αρ', 'προ', 'νις']:
                    word = word + 'εστ'
                done = True
                break

    ##rule-set 13
    ##χτιστηκε->χτιστ, διαθηκεσ->διαθηκ
    if not done:
        for suffix in ['ηθηκα', 'ηθηκες', 'ηθηκε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                done = True
                break
    if not done:
        for suffix in ['ηκα', 'ηκες', 'ηκε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['διαθ', 'θ', 'παρακαταθ', 'προσθ', 'συνθ']:
                    word = word + 'ηκ'
                else:
                    for suffix in ['σκωλ', 'σκουλ', 'ναρθ', 'σφ', 'οθ', 'πιθ']:
                        if ends_with(word, suffix):
                            word = word + 'ηκ'
                            break
                done = True
                break
            
    ##rule-set 14
    ##χτυπουσεσ->χτυπ, μεδουσεσ->μεδουσ
    if not done:
        for suffix in ['ουσα', 'ουσες', 'ουσε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['φαρμακ', 'χαδ', 'αγκ', 'αναρρ', 'βρομ', 'εκλιπ', 'λαμπιδ', 'λεχ', 'μ', 'πατ', 'ρ', 'λ', 'μεδ', 'μεσαζ',
                            'υποτειν', 'αμ', 'αιθ', 'ανηκ', 'δεσποζ', 'ενδιαφερ', 'δε', 'δευτερευ', 'καθαρευ', 'πλε', 'τσα']:
                    word = word + 'ους'
                else:
                    for s in ['ποδαρ', 'βλεπ', 'πανταχ', 'φρυδ', 'μαντιλ', 'μαλλ', 'κυματ', 'λαχ', 'ληγ', 'φαγ', 'ομ', 'πρωτ'] + VOWELS:
                        if ends_with(word, s):
                            word = word + 'ους'
                            break
                done = True
                break

    ##rule-set 15
    #κολλαγεσ->κολλ, αβασταγα->αβαστ
    if not done:
        for suffix in ['αγα', 'αγες', 'αγε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['αβαστ', 'πολυφ', 'αδηφ', 'παμφ', 'ρ', 'ασπ', 'αφ', 'αμαλ', 'αμαλλι', 'ανυστ', 'απερ', 'ασπαρ', 'αχαρ',
                            'δερβεν', 'δροσοπ', 'ξεφ', 'νεοπ', 'νομοτ', 'ολοπ', 'ομοτ', 'προστ', 'προσωποπ', 'συμπ', 'συντ', 'τ',
                            'υποτ', 'χαρ', 'αειπ', 'αιμοστ', 'ανυπ', 'αποτ', 'αρτιπ', 'διατ', 'εν', 'επιτ', 'κροκαλοπ', 'σιδηροπ',
                            'λ', 'ναυ', 'ουλαμ', 'ουρ', 'π', 'τρ', 'μ']:
                    word = word + 'αγ'
                else:
                    for s in ['οφ', 'πελ', 'χορτ', 'σφ', 'ρπ', 'φρ', 'πρ', 'λοχ', 'σμην']:
                        # αφαιρεθηκε: 'λλ'
                        if ends_with(word, s):
                            if not word in ['ψοφ', 'ναυλοχ']:
                                word = word + 'αγ'
                            break
                done = True
                break

    ##rule-set 16
    ##αγαπησε->αγαπ, νησου->νησ
    if not done:
        for suffix in ['ησε', 'ησου', 'ησα']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['ν', 'χερσον', 'δωδεκαν', 'ερημον', 'μεγαλον', 'επταν', 'αγαθον']:
                    word = word + 'ης'
                done = True
                break
            
    ##rule-set 17
    ##αγαπηστε->αγαπ, σβηστε->σβηστ
    if not done:
        for suffix in ['ηστε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['ασβ', 'σβ', 'αχρ', 'χρ', 'απλ', 'αειμν', 'δυσχρ', 'ευχρ', 'κοινοχρ', 'παλιμψ']:
                    word = word + 'ηστ'
                done = True
                break
            
    ##rule-set 18
    ##αγαπουνε->αγαπ, σπιουνε->σπιουν
    if not done:
        for suffix in ['ουνε', 'ησουνε', 'ηθουνε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['ν', 'ρ', 'σπι', 'στραβομουτς', 'κακομουτς', 'εξων']:
                    word = word + 'OYN'
                done = True
                break
            
    ##rule-set 19
    ##αγαπουμε->αγαπ, φουμε->φουμ
    if not done:
        for suffix in ['ουμε', 'ησουμε', 'ηθουμε']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                if word in ['παρασους', 'φ', 'χ', 'ωριοπλ', 'αζ', 'αλλοσους', 'ασους']:
                    word = word + 'ουμ'
                done = True
                break
            
    ##rule-set 20
    ##κυματα->κυμ, χωρατο->χωρατ
    if not done:
        for suffix in ['ματα', 'ματων', 'ματος']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                word = word + 'μ'
                done = True
                break
            
    ##rule-set 21
    if not done:
        for suffix in ['ιοντουσαν', 'ιουμαστε', 'ιομασταν', 'ιοσασταν', 'οντουσαν', 'ιοσαστε', 'ιεμαστε', 'ιεσαστε', 'ιομουνα',
                       'ιοσουνα', 'ιουνται', 'ιουνταν', 'ηθηκατε', 'ομασταν', 'οσασταν', 'ουμαστε', 'ιομουν', 'ιονταν', 'ιοσουν',
                       'ηθειτε', 'ηθηκαν', 'ομουνα', 'οσαστε', 'οσουνα', 'ουνται', 'ουνταν', 'ουσατε',  'αγατε', 'ειται', 'ιεμαι',
                       'ιεται', 'ιεσαι', 'ιοταν', 'ιουμα', 'ηθεις', 'ηθουν', 'ηκατε', 'ησατε', 'ησουν', 'ομουν',  'ονται',
                       'ονταν', 'οσουν', 'ουμαι', 'ουσαν',  'αγαν', 'αμαι', 'ασαι', 'αται', 'ειτε', 'εσαι', 'εται', 'ηδες',
                       'ηδων', 'ηθει', 'ηκαν', 'ησαν', 'ησει', 'ησες', 'ομαι', 'οταν',  'αει',  'εις',  'ηθω',  'ησω', 'ουν',
                       'ους',  'αν', 'ας', 'αω', 'ει', 'ες', 'ης', 'οι', 'ον', 'ος', 'ου', 'υς', 'ων', 'ως', 'α', 'ε', 'ι', 'η',
                       'ο',  'υ', 'ω']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                break

    ##rule-set 22
    ##πλησιεστατοσ->πλυσι, μεγαλυτερη->μεγαλ, κοντοτερο->κοντ
    if not done:
        for suffix in ['εστερ', 'εστατ', 'οτερ', 'οτατ', 'υτερ', 'υτατ', 'ωτερ', 'ωτατ']:
            if ends_with(word, suffix):
                word = word[:len(word) - len(suffix)]
                break
    
    if len(word.decode("utf-8")) >=3:   
        return word
    return ""


#print stem("γιαγιαδες")
########NEW FILE########
__FILENAME__ = test_langs
# -*- coding: utf-8 -*-
from pyredise import query_handler, corpus_handler, quick_language_detection, sensitive_language_detection


articles = [
"The quick brown fox jumps over the lazy dog and fucks the hell out of it",
 "Den raske brune reven hopper over den late hunden og knuller i helvete ut av det",
 "Den hurtige brune ræv hopper over den dovne hund og knepper fanden ud af det",
 "Быстрая коричневая лиса прыгает через ленивую собаку и трахает ад из этого",
 "De snelle bruine vos springt over de luie hond en neukt de hel van te maken",
 "Nopea ruskea kettu hyppää laiskan koiran yli ja vittuile helvettiin siitä",
 "Le rapide renard brun saute par dessus le chien paresseux et baise l'enfer hors de lui",
 "Der schnelle braune Fuchs springt über den faulen Hund und fickt die Hölle aus ihm heraus",
 "A gyors barna róka átugorja a lusta kutyát, és baszik a fenébe is",
 "La volpe veloce salta sul cane pigro e scopa l'inferno fuori di esso",
 "A ligeira raposa marrom ataca o cão preguiçoso e fode o inferno fora dele",
 "El rápido zorro marrón salta sobre el perro perezoso y folla el infierno fuera de él",
 "En snabb brun räv hoppar över den lata hunden och knullar skiten ur det",
 #"Hızlı kahverengi tilki tembel köpeğin üstünden atlar ve bunun cehenneme sikikleri",
 "Η γρήγορη καφέ αλεπού πηδάει πάνω από το μεσημέρι και πηδάει την κόλαση έξω από αυτό"
 ]
 




if __name__=="__main__":
    


    import redis , time, json
    db = redis.Redis(host='192.168.1.2', port=6666, db=3)
    from noocore.models.mongo_models import Article, Magazine    
    from mongoengine import connect
   
    DATABASE = "nootropia"
    USERNAME = "dummy"
    PASSWORD = "dummy"
     
    mdb = connect(DATABASE, username = USERNAME, password = PASSWORD)    
    
    cp = corpus_handler.CorpusHandler(debug=True, db=db)
    cp.drop()

    QH = query_handler.QueryHandler(debug=True, db=db, limit=200)
    
    for i, v in enumerate(articles):
        cp.index({"id":i, "title":v, "content":v})

    for i, v in enumerate(articles):
        print i
        try:
            print sensitive_language_detection.check_lang(v), QH.process_query(" ".join(v.split()[1:4]))
        except:
            print "err"
        

########NEW FILE########
