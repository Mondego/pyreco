__FILENAME__ = idf_maker
# -*- coding: UTF-8 -*-
import sys, os, os.path
import codecs
from django.utils.encoding import force_unicode
from django.db.models import Count

import yaha
from yaha.analyse import ChineseAnalyzer 

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        from django.utils import simplejson as json

try:
    import whoosh
except ImportError:
    raise MissingDependency("The 'whoosh' backend requires the installation of 'Whoosh'. Please refer to the documentation.")

# Bubble up the correct error.
from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import Schema, IDLIST, STORED, TEXT, KEYWORD, NUMERIC, BOOLEAN, DATETIME, NGRAM, NGRAMWORDS
from whoosh.fields import ID as WHOOSH_ID
from whoosh import index, query, sorting, scoring
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.filedb.filestore import FileStorage, RamStorage
from whoosh.searching import ResultsPage
from whoosh.writing import AsyncWriter

def _from_python(value):
    """
    Converts Python values to a string for Whoosh.

    Code courtesy of pysolr.
    """
    if hasattr(value, 'strftime'):
        if not hasattr(value, 'hour'):
            value = datetime(value.year, value.month, value.day, 0, 0, 0)
    elif isinstance(value, bool):
        if value:
            value = 'true'
        else:
            value = 'false'
    elif isinstance(value, (list, tuple)):
        value = u','.join([force_unicode(v) for v in value])
    elif isinstance(value, (int, long, float)):
        # Leave it alone.
        pass
    else:
        value = force_unicode(value)
    return value

use_file_storage = True
storage = None
key_path = 'key_index'
if use_file_storage and not os.path.exists(key_path):
    os.mkdir(key_path)
storage = FileStorage(key_path)
index_fieldname = 'content'
schema_fields = {
        'id': WHOOSH_ID(stored=True, unique=True),
}
schema_fields[index_fieldname] = TEXT(stored=True, analyzer=ChineseAnalyzer())
schema = Schema(**schema_fields)

accepted_chars = re.compile(ur"[\u4E00-\u9FA5]+", re.UNICODE)
accepted_line = re.compile(ur"\d+-\d+-\d+")

def get_content(filename):
    accepted_line = re.compile(ur"\d+-\d+-\d+")
    file = codecs.open(filename, 'r', 'utf-8')
    content = ''
    names = []
    drop = 0
    for line in file.readlines():
        if accepted_line.match(line):
            line_names = accepted_chars.findall(line)
            for l_n in line_names:
                if l_n not in names:
                    names.append(l_n)
        else:
            drop += 1
            if drop % 8 == 0:
                content += line
    file.close()
    return (content, names)

def add_doc():
    index = storage.open_index(schema=schema)
    writer = index.writer()
    
    #parser = QueryParser(index_fieldname, schema=schema)
    #parsed_query = parser.parse('%s:%s' % ('id', qq_id))
    #parsed_query = parser.parse('%s:%s' % ('id', qq_id))
    #writer.delete_by_query(query)
    #writer.commit()

    content,names = get_content('qq7')
    
    doc = {}
    doc['id'] = _from_python(qq_id)
    doc[index_fieldname] = content
    
    try:
        writer.add_document(**doc)
        writer.commit()
        #writer.update_document(**doc)
    except Exception, e:
        raise

def write_db():
    index = storage.create_index(schema)
    writer = index.writer()
    
    # read doc from Database by using django
    for dou in Preview.objects.all():
        doc = {}
        doc['id'] = _from_python(str(dou.id))
        text = dou.description
        doc[index_fieldname] = text
        try:
            writer.update_document(**doc)
        except Exception, e:
            raise

    #add_doc(index, writer)
    writer.commit()

def search_db():
    index = storage.open_index(schema=schema)
    searcher = index.searcher()
    parser = QueryParser(index_fieldname, schema=schema)
    parsed_query = parser.parse('%s:%s' % ('id', qq_id))
    raw_results = searcher.search(parsed_query)
    
    _,names = get_content('qq7')

    corpus_filename = 'name_qq7'
    terms = {}
    corpus_file = codecs.open(corpus_filename, "r", "utf-8")
    for line in corpus_file:
        tokens = line.split(" ")
        term = tokens[0].strip()
        frequency = int(tokens[1].strip())
        terms[term] = frequency

    n_terms = {}
    corpus_filename = 'dict.txt'
    corpus_file = codecs.open(corpus_filename, "r", "utf-8")
    for line in corpus_file:
        tokens = line.split(" ")
        term = tokens[0].strip()
        if len(tokens) >= 3 and tokens[2].find('n')>=0:
            n_terms[term] = tokens[2]
        else:
            n_terms[term] = ''
    keys = []
    for keyword, score in raw_results.key_terms(index_fieldname, docs=1000, numterms=240):
        if keyword in names:
            continue
        if terms.has_key(keyword):
            if not n_terms.has_key(keyword):
                keys.append(keyword)
            elif n_terms.has_key(keyword) and n_terms[keyword].find('n')>=0:
                keys.append(keyword)
        #keys.append(keyword)
    print ', '.join(keys)
    #print len(raw_results)
    #for result in raw_results:
    #    print result[index_fieldname]

def key_all():
    index = storage.open_index(schema=schema)
    searcher = index.searcher()
    reader = searcher.reader()
    cnt = 0
    filename = 'idf.txt'
    accepted_chars = re.compile(ur"[\u4E00-\u9FA5]+", re.UNICODE)
    file = codecs.open(filename, "w", "utf-8")
    file.write('%s\n' % reader.doc_count_all() )
    for term in reader.field_terms('content'):
    #for term in reader.most_frequent_terms('content', 100):
        if not accepted_chars.match(term):
            continue
        term_info = reader.term_info('content', term)
        file.write('%s %d %d\n' % (term, term_info.doc_frequency(), term_info.max_weight()) )
    file.close()
write_db()
add_doc()
search_db()
key_all()

########NEW FILE########
__FILENAME__ = test_cuttor
# -*- coding=utf-8 -*-
import sys, re, codecs
import cProfile
from yaha import Cuttor, RegexCutting, SurnameCutting, SurnameCutting2, SuffixCutting
from yaha.wordmaker import WordDict
from yaha.analyse import extract_keywords, near_duplicate, summarize1, summarize2, summarize3

str = '唐成真是唐成牛的长寿乡是个1998love唐成真诺维斯基'
cuttor = Cuttor()

# Get 3 shortest paths for choise_best
#cuttor.set_topk(3)

# Use stage 1 to cut english and number 
cuttor.set_stage1_regex(re.compile('(\d+)|([a-zA-Z]+)', re.I|re.U))

# Or use stage 2 to cut english and number 
#cuttor.add_stage(RegexCutting(re.compile('\d+', re.I|re.U)))
#cuttor.add_stage(RegexCutting(re.compile('[a-zA-Z]+', re.I|re.U)))

# Use stage 3 to cut chinese name
#surname = SurnameCutting()
#cuttor.add_stage(surname)

# Or use stage 4 to cut chinese name
surname = SurnameCutting2()
cuttor.add_stage(surname)

# Use stage 4 to cut chinese address or english name
suffix = SuffixCutting()
cuttor.add_stage(suffix)

#seglist = cuttor.cut(str)
#print '\nCut with name \n%s\n' % ','.join(list(seglist))

#seglist = cuttor.cut_topk(str, 3)
#for seg in seglist:
#    print ','.join(seg)

#for s in cuttor.cut_to_sentence(str):
#    print s

#str = "伟大祖国是中华人民共和国"
#str = "九孔不好看来"
#str = "而迈入社会后..."
str = "工信处女干事每月经过下属科室都要亲口交代24口交换机等技术性器件的安装工作"

#You can set WORD_MAX to 8 for better match
#cuttor.WORD_MAX = 8

#Normal cut
seglist = cuttor.cut(str)
print 'Normal cut \n%s\n' % ','.join(list(seglist))

#All cut
seglist = cuttor.cut_all(str)
print 'All cut \n%s\n' % ','.join(list(seglist))

#Tokenize for search
print 'Cut for search (term,start,end)'
for term, start, end in cuttor.tokenize(str.decode('utf-8'), search=True):
    print term, start, end

re_line = re.compile("\W+|[a-zA-Z0-9]+", re.UNICODE)
def sentence_from_file(filename):
    with codecs.open(filename, 'r', 'utf-8') as file:
        for line in file:
            for sentence in re_line.split(line):
                yield sentence

def make_new_word(file_from, file_save):
    word_dict = WordDict()
    #word_dict.add_user_dict('www_qq0')
    for sentence in sentence_from_file(file_from):
        word_dict.learn(sentence)
    word_dict.learn_flush()
    
    str = '我们的读书会也顺利举办了四期'
    seg_list = word_dict.cut(str)
    print ', '.join(seg_list)

    word_dict.save_to_file(file_save)

#最大熵算法得到新词
#def test():
#   make_new_word('qq0', 'www_qq0')
#cProfile.run('test()')
#test()

#test: Get key words from file
def key_word_test():
    filename = 'key_test.txt'
    with codecs.open(filename, 'r', 'utf-8') as file:
        content = file.read()
        keys = extract_keywords(content)
        #print ','.join(keys)
        print summarize1(content)
        print summarize2(content)
        print summarize3(content)
#key_word_test()

#比较文本的相似度
def compare_file():
    file1 = codecs.open('f1.txt', 'r', 'utf-8')
    file2 = codecs.open('f2.txt', 'r', 'utf-8')
    print 'the near of two files is:', near_duplicate(file1.read(), file2.read())
#compare_file()

########NEW FILE########
__FILENAME__ = test_whoosh
# -*- coding: UTF-8 -*-
import sys,os
from whoosh.index import create_in,open_dir
from whoosh.fields import *
from whoosh.qparser import QueryParser

from yaha.analyse import ChineseAnalyzer 
from yaha.analyse import YahaCorrector,words_train

#copy this file from jieba project, just for testing

analyzer = ChineseAnalyzer()
str = u"我的好朋友是李明;我爱北京天安门;IBM和Microsoft;... I have a dream interesting"
for t in analyzer(str):
    print len(t.text), t.text

schema = Schema(title=TEXT(stored=True), path=ID(stored=True), content=TEXT(stored=True, analyzer=analyzer))
if not os.path.exists("tmp"):
    os.mkdir("tmp")

ix = create_in("tmp", schema) # for create new index
#ix = open_dir("tmp") # for read only
writer = ix.writer()

writer.add_document(
    title=u"document1", 
    path=u"/a",
    content=u"This is the first document we’ve added!"
)

writer.add_document(
    title=u"document2", 
    path=u"/b",
    content=u"The second one 你 中文测试中文 is even more interesting! 吃水果"
)

writer.add_document(
    title=u"document3", 
    path=u"/c",
    content=u"买水果然后来世博园。"
)

writer.add_document(
    title=u"document4", 
    path=u"/c",
    content=u"工信处女干事每月经过下属科室都要亲口交代24口交换机等技术性器件的安装工作"
)

writer.add_document(
    title=u"document4", 
    path=u"/c",
    content=u"咱俩交换一下吧。"
)

writer.commit()
searcher = ix.searcher()
parser = QueryParser("content", schema=ix.schema)

for keyword in (u"水果世博园",u"你",u"first",u"中文",u"交换机",u"交换"):
    print "result of ",keyword
    q = parser.parse(keyword)
    results = searcher.search(q)
    for hit in results:  
        print hit.highlights("content")
    print "="*10

words_train('movie.txt', 'movie_key.txt', 'movie.graph')
cor = YahaCorrector('movie_key.txt','movie.graph')
sugs = cor.suggest(u"刘牛德")
print " ".join(sugs)

########NEW FILE########
__FILENAME__ = analyzer
# -*- coding=utf-8 -*-
from whoosh.analysis import RegexAnalyzer,LowercaseFilter,StopFilter,StemFilter
from whoosh.analysis import Tokenizer,Token 
from whoosh.lang.porter import stem

from yaha import Cuttor, SurnameCutting, SuffixCutting, get_dict, DICTS
import re

STOP_WORDS = None
def __init_stop_words():
    global STOP_WORDS
    stop_words = []
    for t,v in get_dict(DICTS.EXT_STOPWORD).iteritems():
        stop_words.append(t)
    for t,v in get_dict(DICTS.STOPWORD).iteritems():
        stop_words.append(t)
    for t,v in get_dict(DICTS.STOP_SENTENCE).iteritems():
        stop_words.append(t)
    STOP_WORDS = frozenset(stop_words)
__init_stop_words()

accepted_chars = re.compile(ur"[\u4E00-\u9FA5]+")

_cuttor = Cuttor()
_cuttor.set_stage1_regex(re.compile('(\d+)|([a-zA-Z]+)', re.I|re.U))
_cuttor.add_stage(SurnameCutting())
_cuttor.add_stage(SuffixCutting())

class ChineseTokenizer(Tokenizer):
    def __call__(self,text,**kargs):
        words = _cuttor.tokenize(text, search=True)
        token  = Token()
        for (w,start_pos,stop_pos) in words:
            if not accepted_chars.match(w):
                if len(w)>1:
                    pass
                else:
                    continue
            token.original = token.text = w
            token.pos = start_pos
            token.startchar = start_pos
            token.endchar = stop_pos
            yield token

def ChineseAnalyzer(stoplist=STOP_WORDS,minsize=1,stemfn=stem,cachesize=50000):
    return ChineseTokenizer()|LowercaseFilter()|StopFilter(stoplist=stoplist,minsize=minsize)\
                                        |StemFilter(stemfn=stemfn, ignore=None,cachesize=cachesize)

########NEW FILE########
__FILENAME__ = spelling
# -*- coding=utf-8 -*-
import sys,os,codecs,re
import os.path
from whoosh import spelling as whoosh_spelling
from whoosh.automata import fst
from whoosh.filedb.filestore import FileStorage
from heapq import heappush, heapreplace
from yaha.wordmaker import WordDict as WordDict1
from yaha.wordmaker2 import WordDict as WordDict2

class YahaCorrector(whoosh_spelling.Corrector):
    """Suggests corrections based on the content of a raw
    :class:`whoosh.automata.fst.GraphReader` object.

    By default ranks suggestions based on the edit distance.
    """

    def __init__(self, word_file, graph_file):
        dirname = os.path.dirname(graph_file)
        st = FileStorage(dirname)
        f = st.open_file(graph_file)
        gr = fst.GraphReader(f)
        self.graph = gr

        self.dict = {}
        with codecs.open(word_file,'r','utf-8') as file:
            for line in file:
                tokens = line.split(" ")
                if len(tokens) >= 2:
                    self.dict[tokens[0].strip()] = int(tokens[1].strip())
    
    def suggest(self, text, limit=8, maxdist=2, prefix=1):
        _suggestions = self._suggestions

        heap = []
        seen = set()
        for k in xrange(1, maxdist + 1):
            for item in _suggestions(text, k, prefix):
                if item[1] in seen:
                    continue
                seen.add(item[1])

                # Note that the *higher* scores (item[0]) are better!
                if len(heap) < limit:
                    heappush(heap, item)
                elif item > heap[0]:
                    heapreplace(heap, item)

            # If the heap is already at the required length, don't bother going
            # to a higher edit distance
            if len(heap) >= limit:
                break

        sugs = sorted(heap, key=lambda item: (0 - item[0], item[1]))
        return [sug for _, sug in sugs]

    def _suggestions(self, text, maxdist, prefix):
        if self.dict.has_key(text):
            yield (len(text)*10 + self.dict.get(text,0)*5, text)
        for sug in fst.within(self.graph, text, k=maxdist, prefix=prefix):
            # Higher scores are better, so negate the edit distance
            yield ((0-maxdist)*100 + len(sug)*10 + self.dict.get(sug,0), sug)

re_line = re.compile("\W+|[a-zA-Z0-9]+", re.UNICODE)
def words_train(in_file, word_file, graph_file):

    # Can only use a exists word_file to make graph_file
    if in_file is not None:
        #Auto create words from in_file
        file_size = os.path.getsize(in_file)
        word_dict = None
        if file_size > 3*1024*1024:
            # A little more quick but inaccurate than WordDict1
            word_dict = WordDict2()
            print >> sys.stderr, 'please wait, getting words from file', in_file
        else:
            word_dict = WordDict1()
        with codecs.open(in_file, 'r', 'utf-8') as file:
            for line in file:
                for sentence in re_line.split(line):
                    word_dict.learn(sentence)
        word_dict.learn_flush()
        print >> sys.stderr, 'get all words, save word to file', word_file
        
        word_dict.save_to_file(word_file)
        print >> sys.stderr, 'save all words completely, create word graphp', graph_file

    words = []
    with codecs.open(word_file,'r','utf-8') as file:
        for line in file:
            tokens = line.split(" ")
            if len(tokens) >= 2:
                words.append(tokens[0].strip())
    words = sorted(words)

    whoosh_spelling.wordlist_to_graph_file(words, graph_file)
    print >> sys.stderr, 'words_train ok'

########NEW FILE########
__FILENAME__ = ksp_dijkstra
# -*- coding=utf-8 -*-
from operator import itemgetter
from prioritydictionary import priorityDictionary

class Graph:
    INFINITY = 100000
    UNDEFINDED = None

    def __init__(self, n, default_prob):
        self._data = {}
        self.N = n
        for i in xrange(0,n-1,1):
            self._data[i] = {}
            self._data[i][i+1] = default_prob
        self._data[n-1] = {}

    def __str__(self):
        return str(self._data)

    def __repr__(self):
        return (self._data)

    def __getitem__(self, node):
        if self._data.has_key(node):
            return self._data[node]
        else:
            return None
    
    def __iter__(self):
        return self._data.__iter__()

    def iteritems(self):
        return self._data.iteritems()
    
    def add_edge(self, node_from, node_to, cost=None):
        if not cost:
            cost = self.INFINITY

        self._data[node_from][node_to] = cost
        return
    
    def remove_edge(self, node_from, node_to, cost=None):
        if self._data[node_from].has_key(node_to):
            if not cost:
                cost = self._data[node_from][node_to]
                
                if cost == self.INFINITY:
                    return -1
                else:
                    self._data[node_from][node_to] = self.INFINITY
                    return cost
            elif self._data[node_from][node_to] == cost:
                self._data[node_from][node_to] = self.INFINITY
                
                return cost
            else:
                return -1
        else:
            return -1

def ksp_yen(graph, node_start, node_end, max_k=3):
    distances, previous = dijkstra(graph, node_start)
    #print 'distance=',distances
    #print 'previous=',previous
    
    A = [{'cost': distances[node_end], 
          'path': path(previous, node_start, node_end)}]
    B = []
    
    if not A[0]['path']: return A
    
    for k in range(1, max_k):
        for i in range(0, len(A[-1]['path']) - 1):
            node_spur = A[-1]['path'][i]
            path_root = A[-1]['path'][:i+1]
            
            edges_removed = []
            #print '\n A=', A
            for path_k in A:
                curr_path = path_k['path']
                if len(curr_path) > i and path_root == curr_path[:i+1]:
                    cost = graph.remove_edge(curr_path[i], curr_path[i+1])
                    #print 'remove ', cost, curr_path[i], curr_path[i+1]
                    if cost == -1:
                        continue
                    edges_removed.append([curr_path[i], curr_path[i+1], cost])
            
            path_spur = dijkstra(graph, node_spur, node_end)
            #print k,i,node_spur,node_end,'path_spur=',path_spur
            
            if path_spur['path']:
                path_total = path_root[:-1] + path_spur['path']
                dist_total = distances[node_spur] + path_spur['cost']
                potential_k = {'cost': dist_total, 'path': path_total}
            
                if not (potential_k in B):
                    B.append(potential_k)
            
            for edge in edges_removed:
                graph.add_edge(edge[0], edge[1], edge[2])
        
        if len(B):
            B = sorted(B, key=itemgetter('cost'))
            A.append(B[0])
            B.pop(0)
        else:
            break
    
    return A

def dijkstra(graph, node_start, node_end=None):
    distances = {}      
    previous = {}       
    Q = priorityDictionary()
    
    for v in graph:
        distances[v] = graph.INFINITY
        previous[v] = graph.UNDEFINDED
        Q[v] = graph.INFINITY
    
    distances[node_start] = 0
    Q[node_start] = 0
    
    for v in Q:
        if v == node_end: break

        for u in graph[v]:
            cost_vu = distances[v] + graph[v][u]
            
            if cost_vu < distances[u]:
                distances[u] = cost_vu
                Q[u] = cost_vu
                previous[u] = v

    if node_end:
        return {'cost': distances[node_end], 
                'path': path(previous, node_start, node_end)}
    else:
        return (distances, previous)

def path(previous, node_start, node_end):
    route = []

    node_curr = node_end    
    while True:
        route.append(node_curr)
        if previous[node_curr] == node_start:
            route.append(node_start)
            break
        elif previous[node_curr] == Graph.UNDEFINDED:
            return []
        
        node_curr = previous[node_curr]
    
    route.reverse()
    return route

# quick cut for one path
def quick_shortest(graph):
    N = graph.N-1
    distances = {} 
    previous = {}
    
    previous[0] = None
    distances[N] = 0.0

    for idx in xrange(N-1,-1,-1):
        Q = priorityDictionary()
        for x in graph[idx]:
            Q[x] = graph[idx][x] + distances[x]
        
        small = Q.smallest()
        previous[idx] = small
        distances[idx] = Q[small]
    # get path from previous 21/08/13 09:10:14
    paths = []
    paths.append(0)
    start = 0
    while start < N:
        paths.append(previous[start])
        start = previous[start]
    return (distances, paths)


########NEW FILE########
__FILENAME__ = ksp_dp
# -*- coding=utf-8 -*-
from operator import itemgetter
from prioritydictionary import priorityDictionary

class Graph:
    INFINITY = 10000
    UNDEFINDED = None

    def __init__(self, n):
        self._data = {}
        self.N = n
        for i in xrange(0,n,1):
            self._data[i] = {}

    def __str__(self):
        return str(self._data)

    def __repr__(self):
        return (self._data)

    def __getitem__(self, node):
        if self._data.has_key(node):
            return self._data[node]
        else:
            return None
    
    def __iter__(self):
        return self._data.__iter__()
    
    def add_edge(self, node_from, node_to, cost=None):
        if not cost:
            cost = self.INFINITY

        self._data[node_to][node_from] = cost
        return
    
    def remove_edge(self, node_from, node_to, cost=None):
        if self._data[node_to].has_key(node_from):
            if not cost:
                cost = self._data[node_to][node_from]
                
                if cost == self.INFINITY:
                    return -1
                else:
                    self._data[node_to][node_from] = self.INFINITY
                    return cost
            elif self._data[node_to][node_from] == cost:
                self._data[node_to][node_from] = self.INFINITY
                
                return cost
            else:
                return -1
        else:
            return -1

def ksp_yen(graph, node_start, node_end, max_k=3):
    distances, previous = dp_graph(graph, node_start)
    #print 'distance=',distances
    #print 'previous=',previous
    
    A = [{'cost': distances[node_end], 
          'path': path(previous, node_start, node_end)}]
    B = []
    
    if not A[0]['path']: return A
    
    for k in range(1, max_k):
        for i in range(0, len(A[-1]['path']) - 1):
            node_spur = A[-1]['path'][i]
            path_root = A[-1]['path'][:i+1]
            
            edges_removed = []
            #print '\n A=', A
            for path_k in A:
                curr_path = path_k['path']
                if len(curr_path) > i and path_root == curr_path[:i+1]:
                    cost = graph.remove_edge(curr_path[i], curr_path[i+1])
                    #print 'remove ', cost, curr_path[i], curr_path[i+1]
                    if cost == -1:
                        continue
                    edges_removed.append([curr_path[i], curr_path[i+1], cost])
            
            path_spur = dp_graph(graph, node_spur, node_end)
            #print k,i,node_spur,node_end,'path_spur=',path_spur
            
            if path_spur['path']:
                path_total = path_root[:-1] + path_spur['path']
                dist_total = distances[node_spur] + path_spur['cost']
                potential_k = {'cost': dist_total, 'path': path_total}
            
                if not (potential_k in B):
                    B.append(potential_k)
            
            for edge in edges_removed:
                graph.add_edge(edge[0], edge[1], edge[2])
        
        if len(B):
            B = sorted(B, key=itemgetter('cost'))
            A.append(B[0])
            B.pop(0)
        else:
            break
    
    return A

def dp_graph(graph, node_start, node_end=None):
    N = graph.N
    distances = {} 
    previous = {}
    
    previous[node_start] = None
    for idx in xrange(0, node_start+1, 1):
        distances[idx] = 0.0

    for idx in xrange(node_start+1,N,1):
        Q = priorityDictionary()
        for x in graph[idx]:
            Q[x] = distances[x] + graph[idx][x]
        small = Q.smallest()
        if small < node_start:
            previous[idx] = node_start
        else:
            previous[idx] = Q.smallest()
        distances[idx] = Q[small]
    
    if node_end:
        return {'cost': distances[node_end], 
                'path': path(previous, node_start, node_end)}
    else:
        return (distances, previous)

def path(previous, node_start, node_end):
    route = []

    node_curr = node_end    
    while True:
        route.append(node_curr)
        if previous[node_curr] == node_start:
            route.append(node_start)
            break
        elif previous[node_curr] == Graph.UNDEFINDED:
            return []
        
        node_curr = previous[node_curr]
    
    route.reverse()
    return route

########NEW FILE########
__FILENAME__ = prioritydictionary
# -*- coding: utf-8 -*-
#
#  prioritydictionary.py
#  
#  Copyright 2002 David Eppstein, UC Irvine
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
# http://code.activestate.com/recipes/117228/
# 
from __future__ import generators

class priorityDictionary(dict):
    def __init__(self):
        '''Initialize priorityDictionary by creating binary heap of pairs 
        (value,key).  Note that changing or removing a dict entry will not 
        remove the old pair from the heap until it is found by smallest() or
		until the heap is rebuilt.'''
        self.__heap = []
        dict.__init__(self)

    def smallest(self):
        '''Find smallest item after removing deleted items from heap.'''
        if len(self) == 0:
            raise IndexError, "smallest of empty priorityDictionary"
        heap = self.__heap
        while heap[0][1] not in self or self[heap[0][1]] != heap[0][0]:
            lastItem = heap.pop()
            insertionPoint = 0
            while 1:
                smallChild = 2*insertionPoint+1
                if smallChild+1 < len(heap) and \
                        heap[smallChild] > heap[smallChild+1]:
                    smallChild += 1
                if smallChild >= len(heap) or lastItem <= heap[smallChild]:
                    heap[insertionPoint] = lastItem
                    break
                heap[insertionPoint] = heap[smallChild]
                insertionPoint = smallChild
        return heap[0][1]
	
    def __iter__(self):
        '''Create destructive sorted iterator of priorityDictionary.'''
        def iterfn():
            while len(self) > 0:
                x = self.smallest()
                yield x
                del self[x]
        return iterfn()
	
    def __setitem__(self,key,val):
        '''Change value stored in dictionary and add corresponding pair to heap.  
        Rebuilds the heap if the number of deleted items grows too large, to 
        avoid memory leakage.'''
        dict.__setitem__(self,key,val)
        heap = self.__heap
        if len(heap) > 2 * len(self):
            self.__heap = [(v,k) for k,v in self.iteritems()]
            self.__heap.sort()  # builtin sort likely faster than O(n) heapify
        else:
            newPair = (val,key)
            insertionPoint = len(heap)
            heap.append(None)
            while insertionPoint > 0 and \
                    newPair < heap[(insertionPoint-1)//2]:
                heap[insertionPoint] = heap[(insertionPoint-1)//2]
                insertionPoint = (insertionPoint-1)//2
            heap[insertionPoint] = newPair
	
    def setdefault(self,key,val):
        '''Reimplement setdefault to call our customized __setitem__.'''
        if key not in self:
            self[key] = val
        return self[key]


########NEW FILE########
__FILENAME__ = wordmaker
# -*- coding=utf-8 -*-
import sys
import os, codecs, re, math
import collections
import threading
from yaha import BaseCuttor, WordBase, get_dict, DICTS

max_word_len = 5 
entropy_threshold = 1 
max_to_flush = 10000

class Word(WordBase):
    def __init__(self, id):
        super(WordBase, self).__init__()

        self.process_freq = 1
        self.total_freq = 1
        self.valid = 0
        self.process_ps = 0.0
        self.id = id
        self.l_len = 0
        self.r_len = 0
        self.l = collections.Counter()
        self.r = collections.Counter()
        self.base_freq = 0
        self.base_ps = 0.0
        self.curr_ps = 0.0

    def add(self):
        self.process_freq += 1
        self.total_freq += 1

    def add_l(self, word):
        if word in self.l:
            self.l[word] += 1
        else:
            self.l[word] = 1
        self.l_len += 1
    
    def add_r(self, word):
        if word in self.r:
            self.r[word] += 1
        else:
            self.r[word] = 1
        self.r_len += 1

    def reset(self, id):
        self.process_freq = 1
        self.id = id
        self.l_len = 0
        self.r_len = 0
        self.l = collections.Counter()
        self.r = collections.Counter()

# TODO has a better implement?
# How to add fields to Objects dynamically ?
MODIFY_LOCK = threading.RLock()
MODIFY_INIT = False
def modify_wordbase(word):
        word.process_freq = 1
        word.total_freq = 1
        word.valid = 0
        word.process_ps = 0.0
        word.id = id
        word.l_len = 0
        word.r_len = 0
        word.l = collections.Counter()
        word.r = collections.Counter()
        word.curr_ps = word.base_ps
        word.add = Word.add
        word.add_l = Word.add_l
        word.add_r = Word.add_r
        word.reset = Word.reset

def get_modified_dict():
    global MODIFY_INIT
    dict = get_dict(DICTS.MAIN)
    if MODIFY_INIT:
        return dict
    with MODIFY_LOCK:
        if MODIFY_INIT:
            return dict
        for word in dict:
            modify_wordbase(word)
        MODIFY_INIT = True
    return dict

def info_entropy(words, total):
    result = 0 
    for word, cnt in words.iteritems():
        p = float(cnt) / total
        result -= p * math.log(p)
    return result

class Process(object):
    def __init__(self, id):
        self.id = id
        self.words = []
        self.cache_lines = []
    
    def add_words(self, word):
        self.words.append(word)

    def do_sentence(self, sentence, word_dict):
        l = len(sentence)
        wl = min(l, max_word_len)
        self.cache_lines.append(sentence)
        for i in xrange(1, wl + 1): 
            for j in xrange(0, l - i + 1): 
                if j == 0:
                    if j < l-i:
                        word_dict.add_word_r(sentence[j:j+i], sentence[j+i])
                    else:
                        word_dict.add_word(sentence[j:j+i])
                else:
                    if j < l-i:
                        word_dict.add_word_lr(sentence[j:j + i], sentence[j-1], sentence[j+i])
                    else:
                        word_dict.add_word_l(sentence[j:j+i], sentence[j-1])

    def calc(self, word_dict):
        # calc all ps first
        for word in self.words:
            this_word = word_dict.get_word(word)
            this_word.process_ps = float(this_word.process_freq)/word_dict.process_total
    
        # then calc the ps around the word
        for word in self.words:
            this_word = word_dict.get_word(word)
            if len(word) > 1:
                p = 0
                for i in xrange(1, len(word)):
                    t = word_dict.ps(word[0:i]) * word_dict.ps(word[i:])
                    p = max(p, t)
                if p > 0 and this_word.process_freq >= 3 and this_word.process_ps / p > 100:
                    if this_word.l_len > 0 and info_entropy(this_word.l, this_word.l_len) < entropy_threshold:
                        continue
                    if this_word.r_len > 0 and info_entropy(this_word.r, this_word.r_len) < entropy_threshold:
                        continue
                    this_word.valid += 1
                    this_word.curr_ps = math.log(float(this_word.total_freq+this_word.base_freq)/float(word_dict.base_total+word_dict.total/word_dict.id))

class WordDict(BaseCuttor):

    def __init__(self, new_dict=True):
        super(WordDict, self).__init__()

        self.dict = {}
        self.total = 0
        self.base_total = 0
        self.id = 0
        self.process_total = 0
        self.current_line = 0
        
        self.WORD_MAX = 5
        
        '''with codecs.open(dict_file, "r", "utf-8") as file:
            for line in file:
                tokens = line.split(" ")
                word = tokens[0].strip()
                if len(tokens) >= 2:
                    this_word = Word(0)
                    freq = int(tokens[1].strip())
                    this_word.base_freq = freq
                    self.dict[word] = this_word
                    self.base_total += freq
        
        #normalize
        for word, term in self.dict.iteritems():
            term.base_ps = math.log(float(term.base_freq)/self.base_total)
            term.curr_ps = term.base_ps'''

        if not new_dict:
            # TODO for getting dict from MAIN_DICT
            self.dict = get_modified_dict()

        self.new_process()

    def add_user_dict(self, filename):
        with codecs.open(filename, "r", "utf-8") as file:
            for line in file:
                tokens = line.split(" ")
                word = tokens[0].strip()
                if len(tokens) >= 2:
                    freq = int(tokens[1].strip())
                    if word in self.dict:
                        this_word = self.dict[word]
                        this_word.base_freq += freq
                        self.base_total += freq
                    else:
                        this_word = Word(0)
                        this_word.base_freq = freq
                        self.dict[word] = this_word
                        self.base_total += freq
        #normalize
        for word, term in self.dict.iteritems():
            term.base_ps = math.log(float(term.base_freq)/self.base_total)
            term.curr_ps = term.base_ps
    
    def exist(self, word):
        if word not in self.dict:
            return False
        this_word = self.dict[word]
        return (this_word.curr_ps < 0.0) or (this_word.valid > self.id/2)

    def get_prob(self, word):
        if word in self.dict:
            return self.dict[word].curr_ps
        else:
            return 0.0
    
    def new_process(self):
        self.id += 1
        self.process = Process(self.id)
        self.process_total = 0
        return self.process
    
    def add_word(self, word):
        this_word = None
        if word in self.dict:
            this_word = self.dict[word]
            if self.id == this_word.id:
                this_word.add()
            else:
                this_word.reset(self.id)
                self.process.add_words(word)
        else:
            this_word = Word(self.id)
            self.dict[word] = this_word
            self.process.add_words(word)
        self.process_total += 1
        self.total += 1
        return this_word

    def learn(self, sentence):
        for s,need_cut in self.cut_to_sentence(sentence):
            if not need_cut:
                continue
            self.process.do_sentence(s, self)
            self.current_line += 1
            if self.current_line > max_to_flush:
                self.process.calc(self)
                self.new_process()
                self.current_line = 0

    def learn_flush(self):
        self.process.calc(self)
        self.new_process()
        self.current_line = 0

    def cut_and_learn(self, sentence):
        self.learn(sentence)
        self.cut(sentence)

    def add_word_l(self, word, l):
        w = self.add_word(word)
        w.add_l(l)
    
    def add_word_r(self, word, r):
        w = self.add_word(word)
        w.add_r(r)
    
    def add_word_lr(self, word, l, r):
        w = self.add_word(word)
        w.add_l(l)
        w.add_r(r)

    def ps(self, word):
        if word in self.dict and self.dict[word].id == self.id:
            return self.dict[word].process_ps
        else:
            return 0.0

    def get_word(self, word):
        return self.dict[word]

    def save_to_file(self, filename, sorted=False):
        word_dict = self
        if sorted:
            final_words = []
            for word, term in word_dict.dict.iteritems():
                #if term.valid > word_dict.id/2 and term.base_freq == 0:
                # Use this to save more word
                if term.valid > 0 and term.base_freq == 0:
                    final_words.append(word)

            final_words.sort(cmp = lambda x, y: cmp(word_dict.get_word(y).total_freq, word_dict.get_word(x).total_freq))
            
            with codecs.open(filename, 'w', 'utf-8') as file:
                for word in final_words:
                    v = word_dict.get_word(word).total_freq
                    file.write("%s %d\n" % (word,v))
        else:
            with codecs.open(filename,'w','utf-8') as file:
                for word, term in word_dict.dict.iteritems():
                    if term.valid > 0 and term.base_freq == 0:
                        file.write("%s %d\n" % (word,term.total_freq))


########NEW FILE########
__FILENAME__ = wordmaker2
# -*- coding=utf-8 -*-
import sys
import os, codecs, re, math
import collections
import threading
from yaha import BaseCuttor, WordBase, get_dict, DICTS

# A little more quick but inaccurate than workmaker.py

max_word_len = 5 
entropy_threshold = 1 
max_to_flush = 10000

class Word(WordBase):
    def __init__(self):
        super(WordBase, self).__init__()
        self.total_freq = 0
        self.valid = 0
        self.base_freq = 0
        self.base_ps = 0.0
        self.curr_ps = 0.0

class PWord(WordBase):
    def __init__(self):
        super(WordBase, self).__init__()

        self.process_freq = 1
        self.process_ps = 0.0
        self.l_len = 0
        self.r_len = 0
        self.l = collections.Counter()
        self.r = collections.Counter()
        self.base_freq = 0
        self.base_ps = 0.0
        self.curr_ps = 0.0

    def add(self):
        self.process_freq += 1

    def add_l(self, word):
        if word in self.l:
            self.l[word] += 1
        else:
            self.l[word] = 1
        self.l_len += 1
    
    def add_r(self, word):
        if word in self.r:
            self.r[word] += 1
        else:
            self.r[word] = 1
        self.r_len += 1

# TODO has a better implement?
# How to add fields to Objects dynamically ?
MODIFY_LOCK = threading.RLock()
MODIFY_INIT = False
def modify_wordbase(word):
        word.process_freq = 1
        word.total_freq = 1
        word.valid = 0
        word.process_ps = 0.0
        word.id = id
        word.l_len = 0
        word.r_len = 0
        word.l = collections.Counter()
        word.r = collections.Counter()
        word.curr_ps = word.base_ps
        word.add = Word.add
        word.add_l = Word.add_l
        word.add_r = Word.add_r
        word.reset = Word.reset

def get_modified_dict():
    global MODIFY_INIT
    dict = get_dict(DICTS.MAIN)
    if MODIFY_INIT:
        return dict
    with MODIFY_LOCK:
        if MODIFY_INIT:
            return dict
        for word in dict:
            modify_wordbase(word)
        MODIFY_INIT = True
    return dict

def info_entropy(words, total):
    result = 0 
    for word, cnt in words.iteritems():
        p = float(cnt) / total
        result -= p * math.log(p)
    return result

class Process(object):
    def __init__(self, id):
        self.id = id
        self.dict = {}
        self.process_total = 0
    
    def add_word(self, word):
        this_word = None
        if self.dict.has_key(word):
            this_word = self.dict[word]
            this_word.add()
        else:
            this_word = PWord()
            self.dict[word] = this_word
        self.process_total += 1
        return this_word
    
    def add_word_l(self, word, l):
        w = self.add_word(word)
        w.add_l(l)
    
    def add_word_r(self, word, r):
        w = self.add_word(word)
        w.add_r(r)
    
    def add_word_lr(self, word, l, r):
        w = self.add_word(word)
        w.add_l(l)
        w.add_r(r)

    def ps(self, word):
        if self.dict.has_key(word):
            return self.dict[word].process_ps
        else:
            return 0.0

    def do_sentence(self, sentence):
        l = len(sentence)
        wl = min(l, max_word_len)
        for i in xrange(1, wl + 1): 
            for j in xrange(0, l - i + 1): 
                if j == 0:
                    if j < l-i:
                        self.add_word_r(sentence[j:j+i], sentence[j+i])
                    else:
                        self.add_word(sentence[j:j+i])
                else:
                    if j < l-i:
                        self.add_word_lr(sentence[j:j + i], sentence[j-1], sentence[j+i])
                    else:
                        self.add_word_l(sentence[j:j+i], sentence[j-1])

    def calc(self, word_dict):
        # calc all ps first
        for word,this_word in self.dict.iteritems():
            this_word.process_ps = float(this_word.process_freq)/self.process_total
    
        # then calc the ps around the word
        for word,this_word in self.dict.iteritems():
            if len(word) > 1:
                p = 0
                for i in xrange(1, len(word)):
                    t = self.ps(word[0:i]) * self.ps(word[i:])
                    p = max(p, t)
                if p > 0 and this_word.process_freq >= 3 and this_word.process_ps / p > 100:
                    if this_word.l_len > 0 and info_entropy(this_word.l, this_word.l_len) < entropy_threshold:
                        continue
                    if this_word.r_len > 0 and info_entropy(this_word.r, this_word.r_len) < entropy_threshold:
                        continue
                    word_dict.add_valid(word, this_word)

class WordDict(BaseCuttor):

    def __init__(self, new_dict=True):
        super(WordDict, self).__init__()

        self.dict = {}
        self.total = 0
        self.base_total = 0
        self.id = 0
        self.process_total = 0
        self.current_line = 0
        
        self.WORD_MAX = 5
        
        '''with codecs.open(dict_file, "r", "utf-8") as file:
            for line in file:
                tokens = line.split(" ")
                word = tokens[0].strip()
                if len(tokens) >= 2:
                    this_word = Word(0)
                    freq = int(tokens[1].strip())
                    this_word.base_freq = freq
                    self.dict[word] = this_word
                    self.base_total += freq
        
        #normalize
        for word, term in self.dict.iteritems():
            term.base_ps = math.log(float(term.base_freq)/self.base_total)
            term.curr_ps = term.base_ps

        if not new_dict:
            # TODO for getting dict from MAIN_DICT
            self.dict = get_modified_dict()'''

        self.new_process()

    def add_user_dict(self, filename):
        with codecs.open(filename, "r", "utf-8") as file:
            for line in file:
                tokens = line.split(" ")
                word = tokens[0].strip()
                if len(tokens) >= 2:
                    freq = int(tokens[1].strip())
                    if word in self.dict:
                        this_word = self.dict[word]
                        this_word.base_freq += freq
                        self.base_total += freq
                    else:
                        this_word = Word(0)
                        this_word.base_freq = freq
                        self.dict[word] = this_word
                        self.base_total += freq
        #normalize
        for word, term in self.dict.iteritems():
            term.base_ps = math.log(float(term.base_freq)/self.base_total)
            term.curr_ps = term.base_ps

    def add_valid(self, word, pword):
        this_word = None
        if self.dict.has_key(word):
            this_word = self.dict[word]
        else:
            this_word = Word()
            self.dict[word] = this_word
        this_word.valid += 1
        this_word.total_freq += pword.process_freq
        self.total += pword.process_freq
        this_word.curr_ps = math.log(float(this_word.total_freq+this_word.base_freq)\
                /float(self.base_total+self.total/self.id))
    
    def exist(self, word):
        if word not in self.dict:
            return False
        this_word = self.dict[word]
        return (this_word.curr_ps < 0.0) or (this_word.valid > self.id/2)

    def get_prob(self, word):
        if word in self.dict:
            return self.dict[word].curr_ps
        else:
            return 0.0
    
    def new_process(self):
        self.id += 1
        self.process = Process(self.id)
        self.process_total = 0
        return self.process
    
    def learn(self, sentence):
        for s,need_cut in self.cut_to_sentence(sentence):
            if not need_cut:
                continue
            self.process.do_sentence(s)
            self.current_line += 1
            if self.current_line > max_to_flush:
                self.process.calc(self)
                self.new_process()
                self.current_line = 0

    def learn_flush(self):
        self.process.calc(self)
        self.new_process()
        self.current_line = 0

    def cut_and_learn(self, sentence):
        self.learn(sentence)
        self.cut(sentence)

    def get_word(self, word):
        return self.dict[word]

    def save_to_file(self, filename, sorted=False):
        word_dict = self
        if sorted:
            final_words = []
            for word, term in word_dict.dict.iteritems():
                #if term.valid > word_dict.id/2 and term.base_freq == 0:
                # Use this to save more word
                if term.valid > 0 and term.base_freq == 0:
                    final_words.append(word)

            final_words.sort(cmp = lambda x, y: cmp(word_dict.get_word(y).total_freq, word_dict.get_word(x).total_freq))
            
            with codecs.open(filename, 'w', 'utf-8') as file:
                for word in final_words:
                    v = word_dict.get_word(word).total_freq
                    file.write("%s %d\n" % (word,v))
        else:
            with codecs.open(filename,'w','utf-8') as file:
                for word, term in word_dict.dict.iteritems():
                    if term.valid > 0 and term.base_freq == 0:
                        file.write("%s %d\n" % (word,term.total_freq))


########NEW FILE########
