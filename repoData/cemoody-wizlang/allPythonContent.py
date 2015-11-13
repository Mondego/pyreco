__FILENAME__ = actions
import urllib2
import json
import string
import re
import httplib
import urlparse
import sets
import cPickle
import os.path
import time
import multiprocessing
import traceback
import socket
from multiprocessing import Manager
from sets import Set
import numexpr as ne
from wiki import *
from utils import *
import veclib

backend_url_nearest = r'http://localhost:5005/nearest/'
#backend_url_nearest = r'http://thisplusthat.me:5005/nearest/'
backend_url_farthest = r'http://localhost:5005/farthest/'
#backend_url_farthest = r'http://thisplusthat.me:5005/farthest/'

def eval_sign(query):
    """ This is a dumb parser that assign + or - to every character
        in an expression. We can then use this to lookup the sign of
        every token in the expression"""
    out = ""
    sign = '+' # defailt is positive
    for c in query:
        if c == '-': 
            sign = '-'
        elif c == '+':
            sign = '+'
        out += sign
    return out

def prettify(phrase):
    phrase = phrase.replace('_', ' ')
    phrase = phrase.replace('  ',' ')
    phrase = phrase.replace('  ',' ')
    phrase = phrase.replace('  ',' ')
    phrase = phrase.replace('  ',' ')
    text = ''
    for word in phrase.split(' '):
        try:
            word = word[0].upper() + word[1:]
        except:
            pass
        text += word + ' '
    return text

def countdig(word):
    return sum([w.isdigit() for w in word])

class Actor(object):
    """ This encapsulates all of the actions associated with a results 
        page. We test multiple Actor objects until validate(query) is True
        and then parse and evaluate the query, which is usually called 
        through run"""
    name = 'Actor'

    def validate(self, query):
        """Is the given query suitable for this Action"""
        return False

    def parse(self, query):
        """ Reduce the query into arguments for evaluate"""
        return 

    def evaluate(self, arg, **kwargs):
        """Evaluate the query and return a results object
           that gets plugged into the Jinja code in results.html.
           Defaults to a pass-through to OMDB"""
        return {}

    def run(self, query):
        start = time.time()
        if False:
            try:
                args, kwargs = self.parse(query)
                reps = self.evaluate(*args, **kwargs)
            except:
                traceback.print_exc()
                reps = {}
        else:
            args = self.parse(query)
            reps = self.evaluate(*args)
        reps['actor'] = self.name
        stop = time.time()
        reps['query_time'] = "%1.1f" %(stop - start)
        return reps


@timer
@persist_to_file
def result_chain(canonical):
    """Chain the decanonization, wiki lookup,
       wiki article lookup, and freebase all together"""
    title = canonical.replace('_', ' ')
    try:
        wikiname, article = pick_wiki(canonical)
    except:
        print "Error in ", canonical
        wikiname, article = None, None
    notable, types = None, []
    for search in (wikiname, title):
        try:
            notable, types = get_freebase_types(search)
            break
        except:
            pass
    return dict(wikiname=wikiname, article=article, notable=notable,
                types=types)

img = r"http://upload.wikimedia.org/wikipedia/commons/thumb/5/51/"
img += r"Warren_Buffett_KU_Visit.jpg/220px-Warren_Buffett_KU_Visit.jpg"
text =  "Warren Edward Buffett (August 30, 1930) is an American "
text += "business magnate, investor, and philanthropist. He is widely considered "
text += "the most successful investor of... the 20th century."
fake_results = [dict(info=dict(wikiname='Warren Buffet', 
                article=dict(description=text),
                types=['type1a', 'typ1b']), 
                themes=['type 1', 'type 2'], 
                url="http://en.wikipedia.org/wiki/Warren_buffet", 
                title="Warren Buffet",
                description=text,
                notable="Wealthy Person",
                img=img,
                similarity=0.56)]
fake_other   = dict(query='query', translated='translated query',
                    wikinames=[])

class Expression(Actor):
    name = "Expression"
    max = 2
    skip_similar = True

    @timer
    def __init__(self, preloaded_actor=None, subsampling=False, 
                 fast=False, test=True):
        """We need to load and preprocess all of the vectors into the 
           memory and persist them to cut down on IO costs"""
        if not preloaded_actor:
            # a= 'all'
            # w='wikipedia'
            trained = "data" 
            #fnw = '%s/vectors.fullwiki.1000.s50.5k.words' % trained
            fnw = '%s/vectors.fullwiki.1000.s50.words' % trained
            if False:
                wc2t = '%s/c2t' % './data'
                wt2c = '%s/t2c' % './data'
                # all word vecotor lib VL
                self.wc2t = cPickle.load(open(wc2t))
                self.wt2c = cPickle.load(open(wt2c))
                print "Loading...", 
                ks, vs  = [], []
                for k, v in self.wc2t.iteritems():
                    k = veclib.canonize(k, {}, match=False)
                    ks.append(k)
                    vs.append(v)
                for k, v in zip(ks, vs):
                    self.wc2t[k] = v
                print " done with veclib"
            # all words, word to index mappings w2i
            if os.path.exists(fnw + '.pickle'):
                self.aw2i , self.ai2w = cPickle.load(open(fnw + '.pickle'))
            else:
                self.aw2i , self.ai2w = veclib.get_words(fnw)
                cPickle.dump([self.aw2i, self.ai2w], open(fnw + '.pickle','w'))
            print " done with aw2i"
        else:
            # Wikipedia articles and their canonical transformations
            if False:
                self.wc2t = preloaded_actor.wc2t #Wiki dump article titles
                self.wt2c = preloaded_actor.wt2c
            # All vectors from word2vec
            self.aw2i = preloaded_actor.aw2i
            self.ai2w = preloaded_actor.ai2w

    def validate(self, query):
        return ',' not in query

    @timer
    def parse(self, query):
        """Debug with parallel=False, production use
        switch to multiprocessing"""
        # Split the query and find the signs of every word
        if query == 'None':
            return fake_results, fake_other
        words = query.replace('+', '|').replace('-', '|').replace(',', '|')
        words = words.replace(',','|')
        sign  = eval_sign(query)
        signs = ['+',]
        signs.extend([sign[match.start() + 1] \
                  for match in re.finditer('\|', words)])
        signs = [1.0 if s=='+' else -1.0 for s in signs]
        words = words.split('|')
        return signs, words

    @persist_to_file
    @timer
    def canonize(self, signs, words, parallel=True):
        # Get the canonical names for the query
        canon = self.aw2i.keys()
        if parallel:
            wc = lambda x: wiki_canonize(x, canon, use_wiki=False)
            rets  = [wiki_canonize(words[0], canon, use_wiki=True)]
            rets += parmap(wc, words[1:])
        else:
            rets  = [wiki_canonize(words[0], canon, use_wiki=True)]
            rets += [wiki_canonize(w, canon, use_wiki=False) for w in words[1:]]
        canonizeds, wikinames = zip(*rets)
        print rets
        if wikinames[0] is None:
            return '', [], [], []
        wikinames = [w if len(w)>0 else c for c, w in zip(canonizeds, wikinames)]
        # Make the translated query string
        translated = ""
        for sign, canonized in zip(signs, canonizeds):
            translated += "%+1.0f %s " %(sign, canonized)
        print 'translated: ', translated
        return translated, signs, canonizeds, wikinames

    @persist_to_file
    @timer
    def request(self, signs, canonizeds, parallel=True):
        # Format the vector lib request
        n = 8
        results = []
        iter = 0
        while len(results) < 2 and n < 21:
            args = []
            for sign, canonical in zip(signs, canonizeds):
                args.append([sign, canonical])
            send = json.dumps(dict(args=args))
            url = backend_url_nearest + urllib2.quote(send)
            response = json.load(urllib2.urlopen(url))
            # Decanonize the results and get freebase, article info
            if parallel:
                rv = parmap(result_chain, response['result'][:n])
            else:
                rv = [result_chain(x) for x in response['result'][:n]]
            args = (response['result'], response['similarity'], 
                    response['root_similarity'], rv)
            args = sorted(zip(*args), key=lambda x:x[1])[::-1]
            results = []
            for c, s, r, v in args:
                print '%1.3f %1.3f %s' % (s, r, v['wikiname'])
                if r > 0.90:
                    print 'Too similar to root'
                    continue
                if r > 0.75 and iter==0:
                    print 'Somewhat similar to root'
                    continue
                if v['wikiname'] is None:
                    print 'No wikiname'
                    continue
                if 'PA474' in v['wikiname']:
                    print 'skipping pa474'
                    continue
                ret = dict(canonical=c, similarity=s)
                ret.update(v)
                ret.update(ret.pop('article'))
                results.append(ret)
            n += 8
            iter += 1
        print "%i results" % len(results)
        return results, {}
    
    @timer
    def evaluate(self, query, translated, wikinames, results, other):
        temp = dict(query=query, translated=translated, 
                     wikinames=wikinames, query_text=query,
                     actor=self.name)
        other.update(temp)
        previous_titles = []
        rets = []
        for dresult in results:
            if len(rets) > self.max: break
            wikiname = dresult['wikiname']
            if self.skip_similar:
                if dresult['wikiname'] in other['wikinames']:
                    print 'Skipping direct in query', wikiname
                    continue
                if wikiname in previous_titles: 
                    print 'Skipping previous', wikiname
                    continue
            result = {}
            result['themes'] = dresult['types'][:3]
            if len(result['themes']) == 0:
                print 'Detected zero themes'
                del result['themes']
            result.update(dresult)
            if 'similarity' in result:
                result['similarity'] = "%1.2f" % result['similarity']
            if 'n1' in result:
                result['n1'] = "%1.2f" % result['n1']
            if 'title' not in result or result['title'] is None:
                result['title'] = resultresult['canonical']
            rets.append(result)
            previous_titles.append(wikiname)
        if len(rets) == 0:
            print 'no results kept'
            return {}
        else:
            reps = dict(results=rets)
            reps.update(other)
            return reps

    def run(self, query):
        start = time.time()
        signs, words = self.parse(query)
        translated, signs, canonizeds, wikinames = self.canonize(signs, words)
        if len(wikinames) > 0:
            results, other = self.request(signs, canonizeds)
            reps = self.evaluate(query, translated, wikinames, results, other)
            reps['actor'] = self.name
            reps['hostname'] = socket.gethostname()
            stop = time.time()
            reps['query_time'] = "%1.1f" %(stop - start)
            return reps
        else:
            reps = dict(translated="Wikipedia failed to respond; maybe wait a minute?")
            return reps

class Fraud(Expression):
    max = 2
    name = "Fraud"
    skip_similar = False
    def validate(self, query):
        return ',' in query

    @timer
    @persist_to_file
    def request(self, signs, canonizeds, parallel=True):
        # Format the vector lib request
        n = 6
        args = []
        for sign, canonical in zip(signs, canonizeds):
            args.append(canonical)
        send = json.dumps(dict(args=args))
        url = backend_url_farthest + urllib2.quote(send)
        response = json.load(urllib2.urlopen(url))
        args = response['args']
        self.max = len(args)
        # Decanonize the results and get freebase, article info
        if parallel:
            rv = parmap(result_chain, args[:n])
        else:
            rv = [result_chain(x) for x in args[:n]]
        results = []
        rw = response['right_word']
        r  = response['right']
        l  = response['left']
        print response['left_freebase']
        print response['inner']
        print response['right_freebase']
        for n1, w, v in zip(response['N1'], response['args'], rv):
            ret = {}
            m = 'x' if w == rw else 'o'
            print "%s %s %1.1f" % (m, w, n1)
            ret['mark'] = m
            ret['canonical'] = w
            ret['themes'] = r if m == 'x' else l
            ret['themes'] = ret['themes'][:4]
            ret['n1'] = n1
            ret.update(v)
            article = ret.pop('article')
            if article is not None:
                ret.update(article)
            results.append(ret)
        results = sorted(results, key=lambda x: x['n1'])
        left  = [prettify(lw) for lw in l if countdig(lw) < 2]
        right = [prettify(rw) for rw in r if countdig(rw) < 2]
        other = dict(left=left[:4], right=right[:4])
        return results, other


########NEW FILE########
__FILENAME__ = application
#!/usr/bin/env python
from flask import *
from actions import *
from werkzeug.contrib.profiler import ProfilerMiddleware
import sys
 
app = Flask(__name__,  static_folder='static', 
            static_url_path='', template_folder='templates')
expr = Expression()
criteria = [expr, Fraud(expr)]
@app.route('/results.html', methods=['GET', 'POST'])
@app.route('/search/<query>', methods=['GET', 'POST'])
def results(query="Jurassic Park"):
    if request.method == 'POST':
        query = request.form['query']
        quote = str(urllib2.quote(query))
        url = "/search/%s" % quote
        return redirect(url)
    else:
        reps = {}
        for actor in criteria:
            if actor.validate(query):
                print "Using Actor %s" % actor.name
                reps = actor.run(query)
                break
        return render_template('results.html', **reps)

@app.route('/wait/<query>')
def wait(query='', **kwargs):
    """ Throw up a wait page and immediately 
        redirect to query page
    """
    return render_template('wait.html', **reps)

@app.route('/', methods=['GET', 'POST'])
@app.route('/index.html', methods=['GET', 'POST'])
def index(query="Jurassic Park"):
    if request.method == 'POST':
        query = request.form['query']
        quote = str(urllib2.quote(query))
        url = "/search/%s" % quote
        return redirect(url)
    else:
        return render_template('index.html')

if __name__ == '__main__':
    #app.config['PROFILE'] = True
    #app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions = [30])
    twisted = True
    if twisted:
        from twisted.internet import reactor
        from twisted.web.server import Site
        from twisted.web.wsgi import WSGIResource

        resource = WSGIResource(reactor, reactor.getThreadPool(), app)
        site = Site(resource)
        reactor.listenTCP(8080, site, interface="0.0.0.0")
        reactor.run()
        print "Running"

    else:
        port = 5000
        try:
            port = int(sys.argv[-1])
            print "Serving port %i" % port
        except:
            pass
        app.run(host='0.0.0.0', port=port, use_reloader=False)

########NEW FILE########
__FILENAME__ = backend
from flask import *
from werkzeug.contrib.profiler import ProfilerMiddleware
from collections import defaultdict
import json
import sys
import cPickle
import os.path
import numpy as np

import veclib
from utils import *
 
app = Flask(__name__,  static_folder='static', 
            static_url_path='', template_folder='templates')

trained = "/home/ubuntu/data" 
fnv = '%s/vectors.fullwiki.1000.s50.num.npy' % trained
fnw = '%s/vectors.fullwiki.1000.s50.words' % trained
ffb = '%s/freebase_types_and_fullwiki.1000.s50.words' % trained
avl = veclib.get_vector_lib(fnv)
#avl = veclib.normalize(avl)
avl = veclib.split(veclib.normalize, avl)
if os.path.exists(fnw + '.pickle'):
    aw2i, ai2w = cPickle.load(open(fnw + '.pickle'))
else:
    aw2i, ai2w = veclib.get_words(fnw)
    cPickle.dump([aw2i, ai2w], open(fnw + '.pickle','w'))
frac = None
if frac:
    end = int(avl.shape[0] * frac)
    avl = avl[:end]
    for i in range(end, avl.shape):
        del aw2i[ai2w[i].pop()]

@app.route('/farthest/<raw_query>')
#@json_exception
def farthest(raw_query='{"args":["iphone", "ipad", "ipod", "walkman"]}'):
    """Given a list of arguments, calculate all the N^2 distance matrix
    and return the item farthest away. The total distance is just the 
    distance from a node to all other nodes seperately."""
    print 'QUERY'
    print raw_query
    query = json.loads(raw_query.strip("'"))
    nargs = len(query['args'])
    words = query['args']
    N2, N1, vectors = veclib.build_n2(words, avl, aw2i)
    inner, left, right = veclib.common_words(words, vectors, avl, aw2i, ai2w,
                                             N2, N1, blacklist=words)
    fb_words = [word.strip() for word in open(ffb).readlines()]
    fw2i = {w:i for i, w in enumerate(fb_words)}
    fi2w = {i:w for i, w in enumerate(fb_words)}
    idx = [aw2i[word] for word in fb_words]
    inner_fb, left_fb, right_fb = veclib.common_words(words, vectors, avl[idx], fw2i, fi2w,
                                             N2, N1, blacklist=words, n=1000)
    resp = {}
    resp['N1'] = [float(x) for x in N1]
    resp['args'] = words
    resp['inner'] = inner
    resp['inner_freebase'] = inner_fb[:50]
    resp['left'] = left
    resp['left_freebase'] = left_fb[:50]
    resp['right'] = right
    resp['right_freebase'] = right_fb[:50]
    resp['right_word'] = words[N1.argmin()]
    text = json.dumps(resp)
    return text

@app.route('/nearest/<raw_query>')
@timer
def nearest(raw_query='{"args": [[1.0, "jurassic_park"]]}'):
    """Given the expression, find the appropriate vectors, and evaluate it"""
    print 'QUERY'
    print raw_query
    try:
        query = json.loads(raw_query.strip("'"))
        total = None
        resp = defaultdict(lambda : list)
        resp['args'] = query['args']
        args_neighbors = []
        root_vectors = []
        for sign, word in query['args']:
            vector = avl[aw2i[word]]
            root_vectors.append(vector)
            if False:
                canon, vectors, sim = veclib.nearest_word(vector, avl, ai2w, n=20)
                args_neighbors.append(canon)
            else:
                args_neighbors.append([None])
            if total is None:
                total = vector * sign
            else:
                total += vector * sign
        total /= np.sum(total**2.0)
        canon, vectors, sim = veclib.nearest_word(total, avl, ai2w, n=20)
        root_sims = []
        for canonical, vector in zip(canon, vectors):
            sims = []
            for (sign, word), root_vector in zip(query['args'], root_vectors):
                total = (root_vector * vector).astype(np.float128)
                #total /= np.sqrt(np.sum(total ** 2.0))
                root_sim = np.sum(total,dtype=np.float128)
                sims.append(root_sim)
                print canonical, word, root_sim
            root_sims.append(np.max(sims))
            print canonical, max(sims)
        resp['result'] = canon
        resp['similarity'] = [float(s) for s in sim]
        resp['args_neighbors'] = args_neighbors
        resp['root_similarity'] = [float(s) for s in root_sims]
        send = {}
        send.update(resp)
        print resp
        text = json.dumps(send)
        print "RESPONSE"
        #print json.dumps(send, sort_keys=True,indent=4, separators=(',', ': '))
    except:
        print "ERROR"
        text = dict(error=str(sys.exc_info()))
        text = json.dumps(text)
        print text
    return text

if __name__ == '__main__':
    port = 5005
    try:
        port = int(sys.argv[-1])
        print "Serving port %i" % port
    except:
        pass
    use_flask = True
    if use_flask:
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
    else:
        from twisted.internet import reactor
        from twisted.web.server import Site
        from twisted.web.wsgi import WSGIResource

        resource = WSGIResource(reactor, reactor.getThreadPool(), app)
        site = Site(resource)
        reactor.listenTCP(port, site, interface="0.0.0.0")
        print "Running"
        reactor.run()

    #app.run(host='0.0.0.0', port=port)

########NEW FILE########
__FILENAME__ = shortdot_test
#!/usr/bin/env python
"""
simple test of the shortdot.pyx code
"""

import numpy as np
import shortdot
import time

test_rand = False

if test_rand:
    rows = int(1e5)
    dims = 1000
    A = np.random.normal(size=(rows, dims)).astype('f4')
    B = np.random.normal(size=(dims)).astype('f4')
    C = np.zeros(dims)
    thresh = -1.0
    print "created matrix"
else:
    A = np.load("/nobackupp5/cmoody3/data/ids/trained/vectors.fullwiki.1000.s50.num.npy")
    A = A.astype('f4')
    B = A[A.shape[0]/2]
    C = np.zeros(A.shape[0]).astype('f8')
    thresh = 0.0
    rows = A.shape[0]
    dims = A.shape[1]
C = C.astype('f4')
n = 20
start = time.time()
for i in range(n):
    C = np.zeros(rows).astype('f4')
    skipped = shortdot.shortdot(A, B, C, 50, thresh)
stop = time.time()
frac = skipped * 1.0 / (rows * dims)
print "finished cython, skipped %i, %1.1f%%"  % (skipped, frac * 100.0)
cy = (stop - start) * 1.0 / n * 1e6
print 'cython top 5:', np.sort(C)[-5:], np.argsort(C)[-5:]

start = time.time()
for i in range(n):
    x = np.zeros(rows).astype('f4')
    D = np.dot(A, B)
stop = time.time()
py = (stop - start) * 1.0 / n * 1e6
print 'numpy  top 5:', np.sort(D)[-5:], np.argsort(D)[-5:]
comp = np.where(np.argsort(D)[::-1] != np.argsort(C)[::-1])[0]
print "first inequal indices", comp[:10]

print "cython: %1.3ems" % cy
print "python: %1.3ems" % py
print "cython speed up %1.1f " % (py / cy)

########NEW FILE########
__FILENAME__ = utils
import time
import sys
from multiprocessing import Process, Pipe
from itertools import izip
import os.path
import json

# Courtesy of 
#http://stackoverflow.com/questions/3288595/multiprocessing-using-pool-map-on-a
#-function-defined-in-a-class
def spawn(f):
    def fun(pipe,x):
        pipe.send(f(x))
        pipe.close()
    return fun

def parmap(f,X):
    pipe=[Pipe() for x in X]
    proc=[Process(target=spawn(f),args=(c,x)) for x,(p,c) in izip(X,pipe)]
    [p.start() for p in proc]
    [p.join() for p in proc]
    return [p.recv() for (p,c) in pipe]


def timer(func):
    def wrapped(*args, **kwargs):
        start = time.time()
        rv = func(*args, **kwargs)
        print "%02.1fs in %s" % (time.time() - start, func.__name__)
        return rv
    return wrapped

def fail_print(func):
    def wrapped(*args, **kwargs):
        try:
            rv = func(*args, **kwargs)
        except:
            print sys.exc_info()[0]
            rv = None
        return rv
    return wrapped

def persist_to_file(original_func):
    """ Each query gets written out to a page
        Obviously, this is much slower than the save key-values
        to Redis. But it's quick and doesn't break too much"""
    n = 100
    def decorator(*args, **kwargs):
        file_name = "./cache/"
        file_name += original_func.__name__
        for arg in args:
            file_name += str(arg)[:n]
        keys = sorted(kwargs.keys())
        for k in keys:
            v = kwargs[k]
            v = str(v)[:n]
            temp = "%s_%s-" %(k, v)
            temp = temp.replace("'","")
            temp = temp.replace('"',"")
            temp = temp.replace('/',"")
            file_name += temp
        try:
            ret = json.load(open(file_name, 'r'))
        except (IOError, ValueError):
            ret = None
        if ret is None:
            ret = original_func(*args,**kwargs)
            try:
                json.dump(ret, open(file_name, 'w'))
            except:
                print "Failed to cache"
        return ret
    return decorator

def json_exception(original_func):
    def wrapper(*args, **kwargs):
        try:
            rv = original_func(*args, **kwargs)
        except:
            print "ERROR"
            dv = dict(error=str(sys.exc_info()))
            rv = json.dumps(dv)
        return rv
    return wrapper

class dummy_async():
    """This is faking an async result for debugging purposes"""
    def __init__(self, val):
        self.val = val
    def get(self):
        return self.val

########NEW FILE########
__FILENAME__ = veclib
from difflib import get_close_matches
import pandas as pd
import numpy as np
import os.path
import string
import difflib
import unicodedata
import numexpr as ne
import time
import shortdot
from sets import Set 
from utils import *

""" A library to lookup word vectors, reduce the vector list to a subset and
calculate the nearest word given a vector"""

trained = "/u/cmoody3/data2/ids/trained"
fnw = '%s/vectors.bin.008.words' % trained
fnv = '%s/vectors.bin.008.num' % trained
fnc = 'data/movies_canonical'
def distance(v1, v2, axis=None):
    if type(v1) is str:
        v1 = lookup_vector(v1)
    if type(v2) is str:
        v2 = lookup_vector(v2)
    if len(v1.shape[0]) > 1:
        axis = 1
    i = (v1.astype(np.float64) - v2.astype(np.float64))**2.0
    d = np.sqrt(np.sum(i, axis=axis, dtype=np.float128))
    return d

def reshape(v1):
    if len(v1.shape) == 1:
        shape = [1, v1.shape[0]]
        v1 = np.reshape(v1, shape)
    return v1

def mag(x):
    return np.sqrt(np.sum(x**2.0, axis=1))

mag2 = lambda x: np.sqrt(np.sum(x**2.0, axis=1))
mag1 = lambda x: np.sqrt(np.sum(x**2.0, axis=0))
def similarity(svec, total):
    smv = np.reshape(total, (1, total.shape[0]))
    top = svec * smv
    denom = mag2(svec) * mag1(total)
    denom = np.reshape(denom, (denom.shape[0], 1))
    sim = np.sum(top / denom, axis=1)
    return sim

def normalize(avl):
    vnorm = ne.evaluate('sum(avl**2.0, axis=1)')
    vnorm.shape = [vnorm.shape[0], 1]
    avl = ne.evaluate('avl / sqrt(vnorm)')
    return avl

@timer
def split(operation, data, i=300):
    a, b = 0, 0
    chunk = data.shape[0] / i
    for j in range(i):
        b += chunk
        data[a:b] = operation(data[a:b])
        a = b
    return data

def chunks(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def in_between(vectora, vectorb, vector_lib, index2word, n=10):
    #Measure rough dispersion in each dimension
    dispersion = np.abs(vectorb - vectora)
    vectora = np.reshape(vectora, (1, vectora.shape[0]))
    vectorb = np.reshape(vectorb, (1, vectorb.shape[0]))
    dist = np.minimum(np.abs(vector_lib - vectora),
                      np.abs(vector_lib - vectorb))
    idx = np.argsort(dist)
    words = [index2word[idx[i]] for i in range(n)]
    return dist / dispersion

def build_n2(words, avl, aw2i):
    nargs = len(words)
    N2 = np.zeros((nargs, nargs))
    vectors = {word:avl[aw2i[word]] for word in words}
    for i, worda in enumerate(words):
        vectora = vectors[worda]
        for j, wordb in enumerate(words):
            if j == i: continue
            vectorb = vectors[wordb]
            dist = (vectora * vectorb).sum(dtype=np.float128)
            N2[i, j] = dist
            print worda, wordb, dist
    N1 = np.sum(N2, axis=0)
    return N2, N1, vectors

def common_words(words, vectors, avl, aw2i, ai2w, N2, N1, 
                 blacklist=None, n=50):
    f = words[np.argmin(N1)]
    total = [v for w, v in vectors.iteritems() if not w==f]
    total = np.sum(total, axis=0)
    total /= np.sum(np.sqrt(total**2.0))
    wordsa, vectorsa, sima = nearest_word(total, avl, ai2w, n=n)
    wordsb, vectorsb, simb = nearest_word(vectors[f], avl, ai2w, n=n)
    wordsa = [w for w, s in zip(wordsa, sima) if s < 0.75]
    wordsb = [w for w, s in zip(wordsb, simb) if s < 0.75]
    if blacklist:
        wordsa = [w for w in wordsa if w not in blacklist]
        wordsb = [w for w in wordsb if w not in blacklist]
    inner = [w for w in wordsa if w in wordsb]
    left  = [w for w in wordsa if w not in wordsb]
    right = [w for w in wordsb if w not in wordsa]
    return inner, left, right

def max_similarity(words, checkwords, avl, aw2i):
    """
    For every word, calculate the most similar word
    in checkwords. Keep that similarity measure.
    """
    resp = []
    for word in words:
        sim = -1e99
        if type(word) is str:
            word = avl[aw2i[word]]
        for check in checkwords:
            if type(check) is str:
                check = avl[aw2i[check]]
            sim = max(np.sum(word * check), sim)
        resp.append(sim)
    return resp

@timer
def nearest_word(vector, vector_lib, index2word, n=5, skip=0, 
                 chunk_size=100000, use_ne=False, use_shortdot=True,
                 thresh=0.0):
    words = []
    if use_ne:
        d = ne.evaluate('sum(vector_lib * vector, axis=1)')
        idx = np.argsort(d)[::-1]
        words   = [index2word[i] for i in idx[:n]]
    elif use_shortdot:
        d = np.zeros(vector_lib.shape[0], dtype='f4')
        shortdot.shortdot(vector_lib, vector, d, 100, thresh)
        idx = np.argsort(d)[::-1]
        words   = [index2word[i] for i in idx[:n]]
    else:
        sims = []
        offset = 0
        for vl in chunks(vector_lib, chunk_size):
            d = similarity(vl, vector)
            da = np.argsort(d)[::-1]
            for idx in da[:n]:
                words.append(index2word[idx + offset])
                sims.append(d[idx])
            offset += chunk_size
        idx = np.argsort(sims)[::-1]
        words = [words[i] for i in idx[:n]]
    vectors = [vector_lib[i] for i in idx[:n] ]
    sim = [d[i] for i in idx[:n]]
    return words, vectors, sim

@timer
def subsample(avl, w2i, i2w, whitelist, n):
    subw2i = {}
    subi2w = {}
    count = 0
    for i in range(len(avl)):
        word = i2w[i]
        if count < n or '_' in word or word in whitelist:
            subi2w[i] = word
            subw2i[word] = count
            count +=1
    indices = subi2w.keys()
    subavl = avl[indices]
    return subavl, subw2i, subi2w

@timer
def lookup_vector(word, vector_lib, w2i, fuzzy=True):
    keys = w2i.keys()
    if word not in keys:
        key, = get_close_matches(word, keys, 1)
    else:
        key = word
    print 'Lookup: %s -> %s' % (word, key)
    return vector_lib[w2i[key]]

@timer
def get_canon_rep(fn):
    c2f, f2c = {}, {}
    with open(fn) as fh:
        for line in fh.readlines():
            line = line.strip()
            line = line.replace('  ', ' ')
            f, c = line.rsplit(',', 1)
            f, c = f.strip(), c.strip()
            c2f[c] = f
            f2c[f] = c
    return c2f, f2c


def canonize(phrase, c2f, match=True, n=1):
    phrase = phrase.replace('\n','').replace('\t','').replace('\r','')
    phrase = phrase.strip()
    phrase = phrase.replace(' ', '_')
    phrase = phrase.strip().lower()
    keys = Set(c2f.keys())
    for i in range(5):
        phrase = phrase.replace('  ', ' ')
    if phrase in keys: return phrase
    phrase = phrase.replace('-', '_')
    for p in string.punctuation:
        phrase = phrase.replace(p, '')
    if phrase in keys: return phrase
    phrase = phrase.replace(' ', '_')
    if phrase in keys: return phrase
    if not match:
        return phrase
    phrases = difflib.get_close_matches(phrase, sub, n)
    phrases = [unicodedata.normalize('NFKD', unicode(phrase)).encode('ascii','ignore') for phrase in phrases]
    return phrases[0]

@timer
def reduce_vectorlib(vector_lib, word2index, canon):
    indices = []
    w2i, i2w = {}, {}
    outindex = 0
    words = Set(word2index.keys())
    common = Set(canon).intersection(words)
    for name in common:
        index = word2index[name]
        indices.append(index)
        w2i[name] = outindex
        i2w[outindex] = name
        outindex += 1
    indices = np.array(indices)
    rvl = vector_lib[indices]
    return rvl, w2i, i2w

@timer
def get_names(fn=fnc):
    names = [x.replace('\n', '').strip() for x in fh.readlines()]
    text = ''.join(names)
    text = text.replace('\n', '')
    return text

@timer
def get_words(fn=fnw, subsample=None):
    words = open(fn).readlines()
    word2index = {}
    index2word = {}
    for v, k in enumerate(words):
        k = k.strip().replace('\n', '')
        if subsample:
            if v > subsample - 1:
                break
        index2word[v] = k
        word2index[k] = v
        k = canonize(k, {}, match=False)
        word2index[k] = v
    return word2index, index2word

@timer
def get_english(fn):
    words = []
    with open(fn) as fh:
        for line in fh.readlines():
            words.append(line.strip())
    return words

@timer
def get_vector_lib(fn=fnv):
    fnvn = fn.replace('.npy', '')
    if not os.path.exists(fn) and os.path.exists(fnvn):
        data = pd.read_csv(fn, sep=' ',
                           dtype='f4', na_filter=False)
        data = np.array(data, dtype=np.float32)
        np.save(fn, data)
        return data
    else:
        vectors = np.load(fn)
        return vectors

########NEW FILE########
__FILENAME__ = wiki
import urllib2
import json
import nltk
import unicodedata
import sets
import sys
import re
import time
import difflib
import string
from BeautifulSoup import BeautifulSoup
from utils import *


def exists(url):
    request = urllib2.Request(url)
    request.get_method = lambda : 'HEAD'
    try:
        response = urllib2.urlopen(request)
        return True
    except:
        return False

def get_omdb(name, google_images=False, check=False):
    """Search for the most relevant movie name on OMDB,
    then using that IMDB ID lookup get the rest of the
    information: description, actors, etc. Optionally 
    search Google Images for the poster image and hotlink
    it"""
    url = r"http://www.omdbapi.com/?t=%s" % urllib2.quote(name)
    response = urllib2.urlopen(url)
    odata = json.load(response)
    if 'Error' in odata.keys():
        print 'OMDB Error: %s' % name
        return None
    if check and not exists(odata['Poster']):
        print "IMDB Image not Found for %s" % name
        return None
    data = {k.lower():v for k, v in odata.iteritems()}
    return data

def to_title(title):
    out = ""
    for word in title.split(' '):
        word = word[0].upper() + word[1:]
        out += word + " "
    return out

@persist_to_file
def get_wiki_name(name, get_response=False):
    """Use the WP API to get the most likely diambiguation"""
    for i in range(1, 9):
        url = r"http://en.wikipedia.org/w/api.php?action=opensearch&search=" +\
              urllib2.quote(name) + \
              r"&limit=" + "%i"%i + "&format=json"
        response = urllib2.urlopen(url).read()
        odata = json.loads(response)
        try:
            ptitle = odata[1][0]
        except:
            print "failed wikipedia ", i, response, url
            time.sleep(0.1)
            continue
        if len(odata) > 1:
            break
        else:
            time.sleep(0.1)
    else:
        if get_response:
            return None, None
        else:
            return None
    ptitle = odata[1][0]
    ptitle = unicodedata.normalize('NFKD', ptitle).encode('ascii','ignore')
    if get_response:
        return ptitle, response
    else:
        return ptitle

def wiki_canonize(phrase, canon, n=1, use_wiki=True):
    phrase = phrase.replace('\n','').replace('\t','').replace('\r','')
    phrase = phrase.strip()
    wiki = ""
    if use_wiki:
        try:
            wiki = get_wiki_name(phrase)
        except:
            wiki = None
        if wiki is not None:
            phrase = wiki
    phrase = phrase.replace(' ', '_')
    phrase = phrase.strip().lower()
    for i in range(5):
        phrase = phrase.replace('  ', ' ')
    if phrase in canon: return phrase, wiki
    phrase = phrase.replace('-', '_')
    for p in string.punctuation:
        phrase = phrase.replace(p, '')
    if phrase in canon: return phrase, wiki
    phrase = phrase.replace(' ', '_')
    if phrase in canon: return phrase, wiki
    phrases = difflib.get_close_matches(phrase, canon, n)
    phrases = [unicodedata.normalize('NFKD', unicode(phrase)).encode('ascii','ignore') for phrase in phrases]
    return phrases[0], wiki

@persist_to_file
def wiki_decanonize(phrase, c2t, response=True, n=2):
    if phrase in c2t: return c2t[phrase], None
    phrase = phrase.replace('_', ' ')
    if phrase in c2t: return c2t[phrase], None
    phrase = phrase.capitalize()
    if phrase in c2t: return c2t[phrase], None
    wiki, response= get_wiki_name(phrase, get_response=True)
    if wiki is not None:
        return wiki, response 
    else:
        phrases = difflib.get_close_matches(phrase, c2t.values(), n)
        return phrases[0], None

@persist_to_file
def get_wiki_html(name):
    url = r"http://en.wikipedia.org/w/api.php?action=parse&page=" + \
            urllib2.quote(name) +\
            "&format=json&prop=text&section=0&redirects"
    text = urllib2.urlopen(url).read()
    response = json.loads(text)
    return response

@persist_to_file
def get_wiki_spell(name):
    url2  = r"http://en.wikipedia.org/w/api.php?action=opensearch&search="
    url2 += urllib2.quote(name)
    url2 += r"&format=json&callback=spellcheck"
    text = urllib2.urlopen(url2).read()
    text = text.strip(')').replace('spellcheck(','')
    response = json.loads(text)
    return response

@persist_to_file
def pick_wiki(name):
    candidates = get_wiki_spell(name)
    if len(candidates[1]) == 0:
        return None, None
    for candidate in candidates[1]:
        cleaned = process_wiki(candidate)
        text = cleaned['description']
        if 'Look up' in text:
            print 'skipped wiki look up', candidate
            continue
        elif 'may refer to' in text:
            print 'skipped wiki disambiguation', candidate
            continue            
        else:
            break
    return candidate, cleaned

@persist_to_file
def process_wiki(name, length=20, max_char=300, response=None):
    """Remove excess paragraphs, break out the images, etc."""
    #This gets the first section, gets the text of to a number of words
    # and gets the main image
    if response is None:
        response = get_wiki_html(name)
    html = response['parse']['text']['*']
    valid_tags = ['p']
    soup = BeautifulSoup(html)
    newhtml = ''
    for tag in soup.findAll(recursive=False):
        if len(newhtml.split(' ')) > length:
            continue
        if 'p' == tag.name:
            for c in tag.contents:
                newhtml += ' ' +unicode(c)
    description = nltk.clean_html(newhtml)
    description = re.sub(r'\([^)]*\)', '', description)
    description = re.sub(r'\[[^)]*\]', '', description)
    description = description.replace(' ,', ',')
    description = description.replace(' .', '.')
    if len(description) > max_char:
        description = description[:max_char] + '...'
    soup = BeautifulSoup(html)
    newhtml = ''
    for tag in soup.findAll(recursive=False):
        good = True
        if 'div' == tag.name or 'table' == tag.name:
            if len(tag.attrs) > 0:
                if any(['class' in a for a in tag.attrs]):
                    if 'meta' in tag['class']:
                        good = False
        if good:
            for c in tag.contents:
                newhtml += ' ' +unicode(c)
    img = "http://upload.wikimedia.org/wikipedia/en/b/bc/Wiki.png"
    for tag in BeautifulSoup(newhtml).findAll(recursive=True):
        if 'img' == tag.name:
            if tag['width'] > 70:
                img = "http:" + tag['src']
                break
    url = "http://en.wikipedia.org/wiki/" + name
    title = to_title(name)
    cleaned = dict(img=img, description=description, url=url,
                   title=title, name=name)
    return cleaned

apikey = r"AIzaSyA_9a3q72NzxKeAkkER9zSDJ-l0anluQKQ"
@persist_to_file
def get_freebase_types(name, trying = True):
    types = None
    name = urllib2.quote(name)
    url = r"https://www.googleapis.com/freebase/v1/search?filter=%28all+name%3A%22"
    url += name
    url += r"%22%29&output=%28type%29&key=AIzaSyA_9a3q72NzxKeAkkER9zSDJ-l0anluQKQ&limit=1"
    fh = urllib2.urlopen(url)
    response = json.load(fh)
    notable = response['result'][0]['notable']['name']
    types = [x['name'] for x in response['result'][0]['output']['type']["/type/object/type"]]
    types = [t for t in types if 'topic' not in t.lower()]
    types = [t for t in types if 'ontology' not in t.lower()]
    return notable, types

def reject_result(result, kwargs):
    if len(result['description']) < 10:
        print "Short description"
        return True
    title = result['title'].lower()
    if 'blacklist' in kwargs:
        if '_' in result:
            for word in title.split('_'):
                for black in kwargs['blacklist']:
                    if black in word or black==word:
                        print "skipping", black, word
                        return True
        else:
            word = title
            for black in kwargs['blacklist']:
                if black in word or black==word:
                    print "skipping", black, word
                    return True
    return False

########NEW FILE########
