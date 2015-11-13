__FILENAME__ = admin
from django.contrib import admin
from conceptnet.models import Frequency, Frame, RawAssertion, Concept,\
Assertion, Relation

for model in (RawAssertion, Concept, Assertion, Relation):
    admin.site.register(model)

class FrequencyAdmin(admin.ModelAdmin):
    list_display = ('language', 'text', 'value')
    list_filter = ('language',)
admin.site.register(Frequency, FrequencyAdmin)

class FrameAdmin(admin.ModelAdmin):
    list_display = ('id', 'language','relation','text','preferred')
    list_filter = ('language','relation')
    list_per_page = 100
    fields = ('relation', 'text', 'language', 'goodness', 'frequency')
admin.site.register(Frame, FrameAdmin)

########NEW FILE########
__FILENAME__ = analogyspace
raise ImportError("conceptnet.analogyspace is deprecated. See http://csc.media.mit.edu/docs/divisi2/tutorial_aspace.html for how to use Divisi2 to run AnalogySpace.")

########NEW FILE########
__FILENAME__ = analogyspace2
from csc import divisi2
from conceptnet.models import Assertion, Relation, RawAssertion, Feature
from conceptnet.corpus.models import Language
from math import log, sqrt
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('conceptnet.analogyspace2')

DEFAULT_IDENTITY_WEIGHT = 0
DEFAULT_CUTOFF = 5

log_2 = log(2)

def get_value(score, freq):
    """
    This function gives diminishing returns from higher scores, on a
    logarithmic scale. It also scales the resulting value according to the
    *frequency* value, which ranges from -10 to 10.
    """
    return (freq/10.0) * log(max((score+1, 1)))/log_2

### Getting quads of (concept1, relation, concept2, value) from the database.

def conceptnet_quads(query, cutoff=DEFAULT_CUTOFF):
    '''
    Generates a sequence of ((concept, relation, concept), value)
    triples for ConceptNet.
    
    Query can be a language identifier, in which case it will construct the
    default query for that language. It can also be a Django QuerySet
    containing Assertions, which it will use directly.
    '''
    if isinstance(query, (basestring, Language)):
        queryset = conceptnet_queryset(query, cutoff=cutoff)
    else:
        queryset = query

    for (relation, concept1, concept2, score, freq) in queryset.values_list(
        'relation__name', 'concept1__text', 'concept2__text', 'score', 'frequency__value').iterator():
        yield (concept1, relation, concept2, get_value(score, freq))

def conceptnet_queryset(lang=None, cutoff=DEFAULT_CUTOFF):
    """
    Construct a typical queryset for retrieving all relevant assertions
    from ConceptNet:

    - Limit it to a particular language, unless lang=None
    - Ensure that the reliability score is greater than 0
    - Use Assertion.useful to discard concepts that we have marked as invalid
    - Include only concepts that appear in a minimum number of assertions
      (the *cutoff*)
    """
    queryset = Assertion.useful.filter(score__gt=0)
    if lang is not None:
        queryset = queryset.filter(language=lang)
    if cutoff:
        queryset = queryset.filter(
            concept1__num_assertions__gte=cutoff,
            concept2__num_assertions__gte=cutoff)
    return queryset

def rating_quads(lang, cutoff=DEFAULT_CUTOFF, filter=None):
    '''
    Generates a quad for each rating (vote) on Assertions.

    A django.db.models.Q object passed to filter will be applied to
    the Vote queryset.
    '''
    from conceptnet.models import AssertionVote
    ratings = AssertionVote.objects.filter(
        assertion__concept1__num_assertions__gte=cutoff,
        assertion__concept2__num_assertions__gte=cutoff)
    if filter is not None:
        ratings = ratings.filter(filter)
    for concept1, rel, concept2, vote in ratings.values_list(
        'assertion__concept1__text', 'assertion__relation__name', 'assertion__concept2__text', 'vote').iterator():
        yield (concept1, rel, concept2, vote)

def rawassertion_quads(lang, cutoff=DEFAULT_CUTOFF):
    # Experiment: deal with RawAssertions only.
    from conceptnet.models import RawAssertion
    queryset = RawAssertion.objects.filter(
        score__gt=0,
        surface1__concept__num_assertions__gte=cutoff,
        surface2__concept__num_assertions__gte=cutoff,
        language=lang)
    for (rel, concept1, concept2, text1, text2, frame_id, score, freq) in queryset.values_list(
        'frame__relation__name', 'surface1__concept__text',  'surface2__concept__text', 'surface1__text', 'surface2__text', 'frame__id', 'score', 'frame__frequency__value'
        ).iterator():
        value = get_value(score, freq)

        # Raw
        yield (text1, frame_id, text2, value)

        # Assertion
        yield (concept1, rel, concept2, value)

        ## NormalizesTo
        yield (concept1, 'NormalizesTo', text1, 1)
        yield (concept2, 'NormalizesTo', text2, 1)
        yield (concept1, 'NormalizesTo', concept1, 1)
        yield (concept2, 'NormalizesTo', concept2, 1)

def to_value_concept_feature(quads):
    """
    Convert a stream of assertion quads into a stream of twice
    as many (value, concept, feature) triples.
    """
    for concept1, rel, concept2, value in quads:
        yield value, concept1, ('right', rel, concept2)
        yield value, concept2, ('left', rel, concept1)

def to_value_concept_concept(quads):
    """
    Convert a stream of assertion quads into a stream of twice
    as many (value, concept1, concept2) triples, ignoring the relation and
    simply treating all kinds of edges equally.
    """
    for concept1, rel, concept2, value in quads:
        yield value, concept1, concept2
        yield value, concept2, concept1

def to_value_pair_relation(quads):
    """
    Convert a stream of assertion quads into a stream of
    (value, conceptPair, relation) triples.
    """
    for concept1, rel, concept2, value in quads:
        concept1, rel, concept2 = triple
        yield value, (concept1, concept2), rel

def build_matrix(query, cutoff=DEFAULT_CUTOFF, identity_weight=DEFAULT_IDENTITY_WEIGHT, data_source=conceptnet_quads, transform=to_value_concept_feature):
    """
    Builds a Divisi2 SparseMatrix from relational data.

    One required argument is the `query`, which can be a QuerySet or just a
    language identifier.

    Optional arguments:

    - `cutoff`: specifies how common a concept has to be to appear in the
      matrix. Defaults to DEFAULT_CUTOFF=5.
    - `identity_weight`
    - `data_source`: a function that produces (concept1, rel, concept2, value)
      quads given the `query` and `cutoff`. Defaults to
      :meth:`conceptnet_quads`.
    - `transform`: the function for transforming quads into
      (value, row_name, column_name) triples. Defaults to
      :meth:`to_value_concept_feature`, which yields
      (value, concept, feature) triples.
    """
    logger.info("Performing ConceptNet query")
    quads = list(data_source(query, cutoff))
    # todo: separate this out into a customizable function
    
    if identity_weight > 0:
        logger.info("Adding identities")
        morequads = []
        concept_set = set(q[0] for q in quads)
        for concept in concept_set:
            morequads.append( (concept, 'InheritsFrom', concept, identity_weight) )
        for c1, rel, c2, val in quads:
            if rel == 'IsA':
                morequads.append( (c1, 'InheritsFrom', c1, val) )
        quads.extend(morequads)

    logger.info("Creating triples")
    triples = transform(quads)
    logger.info("Building matrix")
    matrix = divisi2.make_sparse(triples)
    logger.info("Squishing underused rows")
    return matrix.squish(cutoff)


########NEW FILE########
__FILENAME__ = colors
from csc.divisi.util import get_picklecached_thing
from csc.divisi.blend import Blend
from csc.divisi.flavors import ConceptByFeatureMatrix
from conceptnet.models import en
from conceptnet.analogyspace import conceptnet_2d_from_db, make_category
import os

try:
    FILEPATH = os.path.dirname(__file__) or '.'
except NameError:
    FILEPATH = '.'

def _make_color_matrix():
    matrixlist = []
    for file in os.listdir('./context'):
        color = file.split('.')[0]
        fstream = open('./context/' + file,'r')
        sets = [x.strip('\n') for x in fstream.readlines()]
        clist = ','.join(sets)
        words = clist.split(',')
        for word in words:
            word = word.strip()
            if word == '': continue
            print color, word
            matrixlist.append(((word, 'HasColor', color), 10))
            matrixlist.append(((word, 'HasProperty', 'colorful'), 10))
            matrixlist.append(((word, 'HasProperty', color), 10))
        matrixlist.append(((color, 'HasColor', color), 50))
        matrixlist.append(((color, 'HasProperty', color), 50))
    return ConceptByFeatureMatrix.from_triples(matrixlist)
              
def _get_color_blend():
    colors = get_picklecached_thing(FILEPATH+os.sep+'colormatrix.pickle.gz', _make_color_matrix)
    cnet = get_picklecached_thing(FILEPATH+os.sep+'cnet.pickle.gz', lambda: conceptnet_2d_from_db('en'))
    colorblend = Blend([colors, cnet]).normalized(mode=[0,1]).bake()
    return colorblend

colorblend = get_picklecached_thing(FILEPATH+os.sep+'colorblend.pickle.gz', _get_color_blend)
thesvd = colorblend.svd(k=100)
colorful_concepts = thesvd.u.label_list(0)
#print thesvd.summarize(10)
colorful_vec = thesvd.v[('right', u'HasProperty', u'colorful'), :]
colorlist = ['blue', 'black', 'brown', 'green', 'grey', 'orange', 'pink', 'purple', 'red', 'white', 'yellow']
rgb = {'blue': (0,0,255), 'black': (0,0,0), 'brown': (139, 69, 19), 'green': (0, 255, 0), 'grey': (100,100,100), 'orange': (255, 165,0), 'pink': (255,105,180), 'purple': (160, 32, 240), 'red': (255,0,0), 'white': (255, 255, 255), 'yellow': (255,255,0)}
#colorvecs = [(x, thesvd.weighted_u[x,:]) for x in colorlist]
colorvecs = [(x, thesvd.weighted_u[x,:]*.1 + thesvd.weighted_v[('right', 'HasColor', x),:]) for x in colorlist]

def how_colorful(word, thesvd):
    wordvc = thesvd.weighted_u[word,:]
    return wordvc.hat() * make_category(thesvd, concepts=rgb.keys())

def _get_color_mix(adhoc, thesvd):
    vec_dict = {}
    totalsim = 0.0
    for cur_color, vec in colorvecs:
        sim = adhoc.hat() * vec.hat()
        vec_dict[cur_color] = sim**3
        totalsim += sim**3
    if totalsim == 0.0: return vec_dict
    for color in vec_dict:
        vec_dict[color] /= totalsim
    return vec_dict

def _make_color(words, thesvd):
    feats = [('left', 'HasColor', word) for word in words]
    try:
#        words = [x for x in words if abs(how_colorful(x, thesvd)) > 0.001]
        adhoc = make_category(thesvd, concepts=words)
    except KeyError:
        return (128, 128, 128)
    mix = _get_color_mix(adhoc, thesvd)
    new_color = (0,0,0)
    for color, weight in mix.items():
        cur_color = tuple(item*weight for item in rgb[color])
        new_color = tuple(a+b for a,b in zip(cur_color, new_color))
        new_color = tuple(min(max(int(c), 0), 255) for c in new_color)
    return new_color

def _process_phrase(text, thesvd):
    parts = en.nl.extract_concepts(text, 3, True) 
    return _make_color(parts, thesvd)

def concept_color(concept):
    if hasattr(concept, 'text'): concept = concept.text
    else: concept = en.nl.normalize(concept)
    return _make_color([concept], thesvd)

def text_color(text):
    return _process_phrase(text, thesvd)

def colorize(sent):
    parts = en.nl.extract_concepts(sent, 2, True)
    parts = [x for x in parts if x in colorful_concepts]
    full_color = _make_color(parts, thesvd)
    outdict = {'sent*': full_color}
    for word in parts:
        wordcolor = _make_color([word], thesvd)
        colorstrength = how_colorful(word,thesvd)
        outdict[word] = (wordcolor, colorstrength)
    return outdict

def color_sent_and_some_parts(sentence):
    # Catherine's version, w/o bigrams
    parts = colorize(sentence)
    sent_color = parts['sent*']
    overall_color = text_color(sentence)
    htmltext = u'<div style="background-color: rgb(%d,%d,%d); padding: 1ex;">' % overall_color
    words = en.nl.tokenize(sentence).split()
    wordpos = 0
    while wordpos < len(words):
        word = words[wordpos]
        if word in parts.keys():
            if word == 'sent*': continue
            wordcolor = parts[word][0]
            strength = parts[word][1]
            if abs(strength) < 1:
                htmltext += word+' '
            else:
                print wordcolor
                htmltext += '<span style="background-color: rgb(%d,%d,%d)">' % wordcolor
                htmltext += word
                htmltext += '</span> '
        else:
            htmltext += word+' '
        wordpos += 1
    htmltext += '</div>'
    return htmltext
    
def html_color_sentence(sentence):
    # warning: this code sucks
    overall_color = text_color(sentence)
    htmltext = u'<div style="background-color: rgb(%d,%d,%d); padding: 1ex;">' % overall_color
    words = en.nl.tokenize(sentence).split()
    wordpos = 0
    while wordpos < len(words):
        word = words[wordpos]
        color = None
        if not en.nl.is_stopword(word):
            text = None
            for words_ahead in (3, 2, 1):
                if wordpos+words_ahead > len(words): continue
                if en.nl.is_stopword(words[wordpos+words_ahead-1]): continue
                text = ' '.join(words[wordpos:wordpos+words_ahead])
                if en.nl.normalize(text) in colorful_concepts:
                    color = concept_color(text)
                    break
            if color is None:
                htmltext += word+' '
            else:
                htmltext += '<span style="background-color: rgb(%d,%d,%d)">' % color
                htmltext += text
                htmltext += '</span> '
            wordpos += words_ahead
        else:
            htmltext += word+' '
            wordpos += 1
    htmltext += '</div>'
    return htmltext

def html_color_text(text):
    # TODO: better tokenizer
    sentences = text.split('\n')
    return u'\n'.join(color_sent_and_some_parts(s) for s in sentences)

import codecs

def html_color_file(filename):
    text = codecs.open(filename, encoding='utf-8').read()
    out = codecs.open(filename+'.html', 'w', encoding='utf-8')
    out.write('<!doctype html>\n')
    main_color = text_color(text)
    out.write('<html><body style="background-color: rgb(%d,%d,%d); color: #444;">\n' % main_color)
    out.write(html_color_text(text))
    out.write('</body></html>\n')
    out.close()

def demo():
    import sys
    try:
        filename = sys.argv[1]
    except IndexError:
        raise ValueError("To run this as a script, please give the filename of a text file.")
    html_color_file(filename)

if __name__ == '__main__': demo()

########NEW FILE########
__FILENAME__ = ConceptNetGUI
from Tkinter import *
import concepttools,sys

__version__ = "2.0"
__author__ = "hugo@media.mit.edu"
__url__ = 'www.conceptnet.org'
config_filename = 'ConceptNet.ini'
welcome_text = """
    ***************************************************
    Welcome to the ConceptNet v2 mini-browser!
    (for more info, please visit www.conceptnet.org)
    ***************************************************
    The purpose of this browser is to allow you to
    explore the ConceptNet API interactively!
    Instructions for browsing:
    - First, click on one of the light-green or yellow
    buttons to select a mode of browsing
    - In the red box, enter some input text
        - Light-green buttons signify "node-level" modes,
        so you may only input concepts like "apple" or
        "eat food". You'll notice that the query
        automatically executes when you press the space
        bar or the return key. In this mode, concepts
        must be given in normalized form (verbs in
        infinitive form, no plurals, no "the" or "a")
        - Yellow buttons signify "document-level" modes, so
        you can paste any amount of text into the red
        box (e.g. a sentence to a document) and the text
        doesn't have to be normalized. In this mode, you
        must press the return key to execute your query.
    - Results are displayed in the deep-green box and
    you may have to scroll to see all of the results
    - Most modes are self-explanatory, but for
    additional information, please consult the api's
    html documentation and www.conceptnet.org
    That's all! So enjoy!
"""

c = concepttools.ConceptTools()
root = Tk()
mode_var = StringVar()

root.title("conceptnet 2.0 mini-browser"),root.option_add('*Font',('Courier', 14, 'bold'))

frame1,win2,frame3 = Frame(root),Frame(root,height="1",bg="#CCFF99"),Frame(root)

frame1.pack(fill=BOTH,expand=NO),win2.pack(fill=BOTH,expand=NO),frame3.pack(fill=BOTH,expand=YES)

win,win3,win_scroll,win3_scroll = Text(frame1,bg="#FF3300",fg="white",height="3",wrap=WORD),Text(frame3,wrap=WORD,height="30",width="20",bg="#669933",fg="white"),Scrollbar(frame1),Scrollbar(frame3)

win_scroll.pack(side=RIGHT,fill=Y),win3_scroll.pack(side=RIGHT,fill=Y),win.pack(fill=BOTH,expand=NO),win2.pack(fill=BOTH,expand=NO),win3.pack(fill=BOTH,expand=1)

win.config(yscrollcommand=win_scroll.set),win3.config(yscrollcommand=win3_scroll.set),win_scroll.config(command=win.yview),win3_scroll.config(command=win3.yview)

Radiobutton(win2,text="BROWSE",variable=mode_var,value='browse',fg="#FF3399",bg='#CCFF99',indicatoron=0).pack(side=LEFT),Radiobutton(win2,text="CONTEXT",variable=mode_var,value='context',indicatoron=0,fg="#FF3399",bg='#CCFF99').pack(side=LEFT),Radiobutton(win2,text="PROJECTION",variable=mode_var,value='projection',indicatoron=0,fg="#FF3399",bg='#CCFF99').pack(side=LEFT),Radiobutton(win2,text="ANALOGY",variable=mode_var,value='analogy',indicatoron=0,fg="#FF3399",bg='#CCFF99').pack(side=LEFT),Radiobutton(win2,text="GUESS CONCEPT",variable=mode_var,value='guessconcept',indicatoron=0,fg="#FF3399",bg='#FFFF66').pack(side=LEFT),Radiobutton(win2,text="GUESS TOPIC",variable=mode_var,value='guesstopic',indicatoron=0,fg="#FF3399",bg='#FFFF66').pack(side=LEFT),Radiobutton(win2,text="GUESS MOOD",variable=mode_var,value='guessmood',indicatoron=0,fg="#FF3399",bg='#FFFF66').pack(side=LEFT),Radiobutton(win2,text="SUMMARIZE",variable=mode_var,value='summarize',indicatoron=0,fg="#FF3399",bg='#FFFF66').pack(side=LEFT)

win3.insert(0.0,welcome_text)

def execution1(x):
	#if mode_var.get() not in ['guessmood','guesstopic','guessconcept','summarize']:
	#	return execution2(x)
	#else:
		return False

def execution2(x):
	win3.delete(0.0,END)
	if win.get(0.0,END).strip()=='':
		win3.insert(0.0,welcome_text)
		return
	
	mode = mode_var.get() 
	input = win.get(0.0,END).encode('ascii','ignore').strip()
	concepts = [tok.strip() for tok in input.split(',')]
	if mode == 'context':
		result = '\n'.join(['%s (%d%%)' % (concept, weight*100) for concept, weight in c.spreading_activation(concepts)] ) +'\n\n'
	
	elif mode == 'projection':
		result = '\n\n'.join([ v[0].upper() + '\n' + '\n'.join( [ z[0] + ' (' + str(int(z[1]*100)) + '%)' for z in v[1] ] [:10]) for v in c.get_all_projections(concepts)] ) +'\n\n'

	elif mode == 'analogy':
		result = '\n\n'.join( ['[~' + match[0] + '] (' + str(match[2]) + ')\n  ' + '\n  '.join( ['==' + struct[0] + '==> ' + struct[1] + ' (' +str(struct[2]) + ') ' for struct in match[1]] ) for match in c.get_analogous_concepts(input)])

	elif mode == 'guessconcept':
		result = '\n\n'.join( [ '[is it: ' + match[0] + '?] (' + str(match[2]) + ')\n  ' + '\n  '.join([ '==' + struct[0] + '==> ' + struct[1] + ' (' + str(struct[2]) + ') ' for struct in match[1]] ) for match in c.nltools.guess_concept(input)])

	elif mode == 'guesstopic':
		result = '\n'.join( [ z[0] + ' (' + str(int(z[1]*100)) + '%)' for z in c.nltools.guess_topic(input)[1]]) + '\n\n'

	elif mode == 'guessmood':
		result = '\n'.join([ z[0] + ' (' + str(int(z[1]*100)) + '%)' for z in c.nltools.guess_mood(input) ] ) + '\n\n'

	elif mode == 'summarize':
		result = c.nltools.summarize_document(input) + '\n\n'

	elif mode == 'foo':
		result = ''
		
	else:
		result = c.display_node(input) + '\n\n'

	win3.insert(0.0,result)
	return True

win.bind('<space>',execution1),win.bind('<Return>',execution2)
root.mainloop()

########NEW FILE########
__FILENAME__ = concepttools

# We really want Python 2.5, but for 2.4 a hack will work.
try:
    from collections import defaultdict
except ImportError:
    class defaultdict(dict):
        def __init__(self, default_factory=None, *a, **kw):
            if (default_factory is not None and
                not hasattr(default_factory, '__call__')):
                raise TypeError('first argument must be callable')
            dict.__init__(self, *a, **kw)
            self.default_factory = default_factory
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return self.__missing__(key)
        def __missing__(self, key):
            if self.default_factory is None:
                raise KeyError(key)
            self[key] = value = self.default_factory()
            return value
        def __reduce__(self):
            if self.default_factory is None:
                args = tuple()
            else:
                args = self.default_factory,
            return type(self), args, None, None, self.items()
        def copy(self):
            return self.__copy__()
        def __copy__(self):
            return type(self)(self.default_factory, self)
        def __deepcopy__(self, memo):
            import copy
            return type(self)(self.default_factory,
                              copy.deepcopy(self.items()))
        def __repr__(self):
            return 'defaultdict(%s, %s)' % (self.default_factory,
                                            dict.__repr__(self))

import cPickle as pickle
from csamoa.corpus.models import Language
from csamoa.representation.presentation.models import Stem, Predicate
from csamoa.representation.parsing.tools.models import PredicateType

from types import StringType, DictType, IntType
import math

# Get only a set of values out of a QuerySet, in order specified
# Unused now.
def just_values(query, req):
    result = query.values(*req)
    return [tuple([res[x] for x in req]) for res in result]


class Datasource(object):
    '''Pulls directly from the database.'''
    @staticmethod
    def get_preds():
        return [(p['id'], p['relation'], p['concept1'], p['concept2'])
                for p in Predicate.objects.filter(score__gt=0, visible=True)
                .values('id','relation','concept1','concept2')]

class LoadOnceDataSource(Datasource):
    '''On first load, the class pulls the Predicates from the database, then
    keeps them cached statically. If you alter the predicates in the database,
    call reload() to update the cached copy.'''

    def __init__(self):
        Datasource.__init__(self)
        if not hasattr(LoadOnceDataSource, 'loaded'):
            LoadOnceDataSource.reload()

    @classmethod
    def reload(klass):
        base = '/tmp/csamoa_'
        try:
            print 'Loading:'
            print '- Predicates ...'
            klass.preds = pickle.load(open(base+'preds'))
            print '- Forward relations...'
            klass.fwd = defaultdict(list, pickle.load(open(base+'fwd')))
            print '- Reverse relations ...'
            klass.rev = defaultdict(list, pickle.load(open(base+'rev')))
        except:
            print 'Retrieving predicates from database...'
            klass.preds = Datasource.get_preds()

            print "Splitting into forward and reverse..."
            # Dictionaries that return empty lists on looking up
            # values that are not present.
            klass.fwd, klass.rev = defaultdict(list), defaultdict(list)
            for id,pt,s1,s2 in klass.preds:
                klass.fwd[s1].append((id, pt, s2))
                klass.rev[s2].append((id, pt, s1))

            print 'Packing...'
            fwd = dict((s1, tuple(s2s)) for s1, s2s in klass.fwd.items())
            rev = dict((s2, tuple(s1s)) for s2, s1s in klass.rev.items())

            print 'Saving for future use...'
            pickle.dump(klass.preds, open(base+'preds','w'), -1)
            pickle.dump(fwd, open(base+'fwd','w'), -1)
            pickle.dump(rev, open(base+'rev','w'), -1)

        print 'done.'
        klass.loaded = True


class ConceptTools:
    '''ConceptTools: a set of tools for getting information from ConceptNet.'''

    def __init__(self, datasource = LoadOnceDataSource):
        # Instantiate the datasource
        self.datasource = datasource()
        self.preds = datasource.preds
        self.fwd = datasource.fwd
        self.rev = datasource.rev
        self.word_hash = {}
        self.word_lookup = {}
        self.global_uid = 0
        self.node_hash = {}
        self.node_lookup = {}


    def zipped2nodeuid(self,zipped):
        node_hash = self.node_hash
        uid = node_hash.get(zipped,None)
        if not uid:
                uid = self.getuid()
                node_hash[zipped] = uid
                self.node_lookup[uid] = zipped
        return uid


    def encode_node(self,textnode):
        toks = textnode.split()
        output_toks = []
        word_hash,word_lookup = self.word_hash,self.word_lookup
        whget = self.word_hash.get
        getuid = self.getuid
        for word in toks:
            word_uid = whget(word,None)
            if not word_uid:
                word_uid = getuid()
                word_hash[word] = word_uid
                word_lookup[word_uid] = word
            output_toks.append(word_uid)
        return tuple(output_toks)


    # This is a stupid port straight from the old ConceptNet.
    # It should give identical results as the old verion, quirks and all,
    # except it uses the new corpus data.

    def spreading_activation(self,
                             origin_stemids,
                             origin_weights = None,
                             max_node_visits=500,
                             max_results=200,
                             linktype_weights=None):
        """Use spreading activation to get the context of a set of concepts.

        Required parameter:
        origin_stemids -- ids of the stems to start from

        Keyword parameters:
        origin_weights -- weight in range [0.0, 1.0] for the starting stems
        max_node_visits -- maximum number of nodes to visit
        max_results -- maximum number of results to return
        linktype_weights -- tuple of two dictionaries of:
          ConceptNet relation type -> weight in range [0.0, 1.0]

        The first dictionary is "forward" relations, i.e., those for which
        the stem is on the left. The second dictionary is for "reverse"
        relations.

        If a relation type is omitted, relations of that type will be ignored.
        """

        fwd_weights, rev_weights = self.get_weights(linktype_weights)

        # Construct the blacklists of link types to completely ignore.
        fwd_blacklist = [ptype for (ptype, weight) in fwd_weights.items()
                         if weight==0.0]
        rev_blacklist = [ptype for (ptype, weight) in rev_weights.items()
                         if weight==0.0]

        if origin_weights is None:
            origin_weights = [1 for id in origin_stemids]

        # Determine if we have to consider backward flows.
        backward_flow_p = len([x for x in rev_weights.items() if x[1] > 0]) > 0

        # Init discount factors
        distance_discount = 0.5
        # FIXME: magic formula comes from...?
        def branching_discount(bf, bf_mu=2.5, bf_sigma=1.0):
            return ((1./(bf_sigma*((2*math.pi)**0.5)))
                    *(math.e**(-(math.log(bf+5,5)-bf_mu)**2/(2*bf_sigma**2))))

        # FIXME: does this ever apply?
#         utter_echo_discount = \
#             lambda utter,echo:min(1.0,math.log(utter+0.5*echo+2,3))

        # Add the initial nodes to the queue, discounted by branching
#        origin_stemids = map(lambda x:(self.zipped2nodeuid(self.encode_node(x[0].strip())),x[1]),origin_stemids)
        (origin_stemids, origin_weights) = self.get_stemids(zip(origin_stemids, origin_weights))
        queue = [(stem_id,
                  weight*branching_discount(len(self.fwd[stem_id])))
                 for (stem_id, weight) in zip(origin_stemids, origin_weights)]

        # Do breadth-first search.
        visited = []
        nodes_seen = 1
        i = 0
        while len(queue)>0 and nodes_seen<max_node_visits:
            # Pop off the queue.
            cur_stem_id,cur_score = queue[0]
            visited.append(queue[0])
            del queue[0]

            # Get forward edges (format: (id, predicate type, stem 2 id))
            fes = self.fwd[cur_stem_id]
                        
            # Remove the links whose predicate types are blacklisted.
            fes = filter(lambda x:x[1] not in fwd_blacklist,fes)

            # Append the newly-discovered forward links to the queue.
            # Updated score used to have an extra factor: ued(x[2], x[3])
            # where ued = utter_echo_discount. That was when x[2] corresponded
            # to some 'f' value and x[3] was 'inferred'.
            def get_next_id_score(x, bd=branching_discount):
                #FIXME: This evil hack shouldn't be necessary - there should be no links whose types aren't in our weights dictionary
                if not x[1] in fwd_weights:
                    fwd_weights[x[1]] = 0
                return (x[2], distance_discount  * bd(len(self.fwd[x[2]])) * fwd_weights[x[1]] * cur_score)
            forward_next_nodeidscores = map(get_next_id_score, fes)
            queue += forward_next_nodeidscores

            # If there are any inverse linkages, look backwards.
            if backward_flow_p:
                bes = self.rev[cur_stem_id]
                bes = filter(lambda x:x[1] not in backward_linktype_blacklist,bes)
                backward_next_nodeidscores = map(lambda x,
                                                 bd=branching_discount:
                                                     (x[2],
                                                      distance_discount
                                                      *bd(len(self.rev[x[2]]))
                                                      *rev_weights[x[1]]
                                                      *cur_score),
                                                 bes)
                queue += backward_next_nodeidscores

            queue.sort(lambda x,y:int((y[1]-x[1])*10000))
            queue=queue[:500]
            nodes_seen += 1

        # Search finished. Add up the scores of everything we visited.
        node_dict = {}
        #print visited
        for nodeid, score in visited:
            # Ignore origin stems (a stem is not in its own context)
            if nodeid in origin_stemids: continue

            cur_score = node_dict.get(nodeid,0.0)
            # Update the score. FIXME: why this formula?
            new_score = max(score,cur_score) \
                + (1.0 - max(score,cur_score)) * min(score,cur_score)
            node_dict[nodeid] = new_score

        # Sort the rest and output them.
        items = node_dict.items()
        items.sort(lambda x,y:int((y[1]-x[1])*100))
        output = [(Stem.objects.get(id=x[0]), x[1]) for x in items[:max_results]]
        return output


    @staticmethod
    def get_stemids(textnodes,
                    lang=Language.objects.get(id='en')):
        # Find the starting nodes in ConceptNet, if they exist.
        stemids, weights = [], []
        for text, weight in textnodes:
            # Filter.
            text = text.strip().lower()
            if text == '': continue

            # Try to get the stem.
            try:
                stem_id = Stem.get(text, lang).id
                stemids.append(stem_id)
                weights.append(weight)
            except Stem.DoesNotExist:
                # Ignore stems that don't exist in ConceptNet.
                print "Warning: ignoring stem '%s' (not in ConceptNet)" % text
        return stemids, weights


    @staticmethod
    def get_weights(linktype_weights):
        # Get the full link-weight dictionary:
        # - If none is specified, use the default.
        # - Otherwise, default unspecified weights to 0.
        if not linktype_weights:
            fwd_weights, rev_weights = ConceptTools.default_linktype_weights
        else:
            # Unpack.
            fwd_weights, rev_weights = linktype_weights

            # Set unspecified linktype weights to 0.
            all_linktypes = ConceptTools.default_linktype_weights[0].keys()
            for linktype in all_linktypes:
                fwd_weights.setdefault(linktype, 0.0)
                rev_weights.setdefault(linktype, 0.0)

        # Convert link types into PredicateTypes.
        fwd_weights = ConceptTools._lookup_predtypes(fwd_weights)
        rev_weights = ConceptTools._lookup_predtypes(rev_weights)

        return fwd_weights, rev_weights


    default_linktype_weights = ({
            'AtLocation': 0.9,
            'CapableOf': 0.8,
            'Causes': 1.0,
            'CausesDesire': 1.0,
            'ConceptuallyRelatedTo': 1.0,
            'CreatedBy': 1.0,
            'DefinedAs': 1.0,
            'Desires': 1.0,
            'HasFirstSubevent': 1.0,
            'HasLastSubevent': 1.0,
            'HasPrerequisite': 1.0,
            'HasProperty': 1.0,
            'HasSubevent': 0.9,
            'IsA': 0.9,
            'MadeOf': 0.7,
            'MotivatedByGoal': 1.0,
            'PartOf': 1.0,
            'ReceivesAction': 0.6,
            'UsedFor': 1.0
            }, {
            'AtLocation': 0.0,
            'CapableOf': 0.0,
            'Causes': 0.0,
            'CausesDesire': 0.0,
            'ConceptuallyRelatedTo': 0.0,
            'CreatedBy': 0.0,
            'DefinedAs': 0.0,
            'Desires': 0.0,
            'HasFirstSubevent': 0.0,
            'HasLastSubevent': 0.0,
            'HasPrerequisite': 0.0,
            'HasProperty': 0.0,
            'HasSubevent': 0.0,
            'IsA': 0.0,
            'MadeOf': 0.0,
            'MotivatedByGoal': 0.0,
            'PartOf': 0.0,
            'ReceivesAction': 0.0,
            'UsedFor': 0.0})

    @staticmethod
    def _lookup_predtypes(pts):
        result = {}
        for ptype, weight in pts.iteritems():
            try:
                result[PredicateType.objects.get(name=ptype).id] = weight
            except PredicateType.DoesNotExist:
                print "Warning: Bad predicate type '%s'!" % ptype
        return result


    def project_affective(self,textnode_list):

        """
        -inputs a list of concepts
        -computes the affective projection, which is
        the emotional context and consequences underlying these concepts
        -returns a rank-ordered list of concepts and their scores
        e.g.: (('concept1',score1), ('concept2,score2), ...)
      """
        linktype_weights_dict = ({
            'Desires':1.0,
            'CausesDesire':1.0,
            'MotivatedByGoal':1.0
            },
            {})
        return self.spreading_activation(textnode_list,linktype_weights=linktype_weights_dict)

    def project_spatial(self,textnode_list):

        """
        -inputs a list of concepts
        -computes the spatial projection, which consists of
        relevant locations, relevant objects in the same scene.
        -returns a rank-ordered list of concepts and their scores
        e.g.: (('concept1',score1), ('concept2,score2), ...)
      """
        linktype_weights_dict = ({
            'AtLocation':1.0,
            'ConceptuallyRelatedTo':0.5
           },
           {})

        return self.spreading_activation(textnode_list,linktype_weights=linktype_weights_dict)

    def project_details(self,textnode_list):

        """
        -inputs a list of concepts
        -computes the detail projection, which consists of
        a thing's parts, materials, properties, and instances
        and an event's subevents
        -returns a rank-ordered list of concepts and their scores
        e.g.: (('concept1',score1), ('concept2,score2), ...)
      """
        linktype_weights_dict = ({
            'HasFirstSubevent':1.0,
            'HasLastSubevent':1.0,
            'HasSubevent':1.0,
            'MadeOf':1.0,
            'PartOf':1.0,
            'HasProperty':0.9
            },
            {})
        return self.spreading_activation(textnode_list,linktype_weights=linktype_weights_dict)

    def project_consequences(self,textnode_list):

        """
        -inputs a list of concepts
        -computes the causal projection, which consists of
        possible consequences of an event or possible actions
        resulting from the presence of a thing
        -returns a rank-ordered list of concepts and their scores
        e.g.: (('concept1',score1), ('concept2,score2), ...)
      """
        linktype_weights_dict = ({
            'CausesDesire':1.0,
            'UsedFor':0.4,
            'CapableOf':0.4,
            'ReceivesAction':0.3,
            'Causes':1.0
            },
            {})
        return self.spreading_activation(textnode_list,linktype_weights=linktype_weights_dict)

    def get_all_projections(self,textnode_list):

        """
        inputs a list of concepts
        computes all available contextual projections
        and returns a list of pairs, each of the form:
             ('ProjectionName',
                (('concept1',score1), ('concept2,score2), ...)
             )
      """
        output = []
        output += [('Consequences',self.project_consequences(textnode_list))]
        output += [('Details',self.project_details(textnode_list))]
        output += [('Spatial',self.project_spatial(textnode_list))]
        output += [('Affective',self.project_affective(textnode_list))]
        return output


    def display_node(self,textnode):

        """
        returns the pretty print of a node's contents
        """
      
        decode_node,encode_node,decode_word = self.decode_node,self.encode_node,self.decode_word
        zipped2nodeuid,nodeuid2zipped = self.zipped2nodeuid, self.nodeuid2zipped
        zipped2edgeuid,edgeuid2zipped = self.zipped2edgeuid, self.edgeuid2zipped
        fw_edges,bw_edges = self.fwd,self.rev
        textnode=textnode.strip()
        encoded_node = encode_node(textnode)
        node_uid = zipped2nodeuid(encoded_node)
        fes = map(edgeuid2zipped,fw_edges.get(node_uid,[])[:1000])
        fes.sort(lambda x,y:y[2]+y[3]-x[2]-x[3])
        print fes
        bes = map(edgeuid2zipped,bw_edges.get(node_uid,[])[:1000])
        bes.sort(lambda x,y:2*(y[2]-x[2])+1*(y[3]--x[3]))
        pp_fw_edges = map(lambda x:'=='+decode_word(x[0])+'==> '+decode_node(nodeuid2zipped(x[1]))+' '+str(x[2:])+'',fes)
        pp_bw_edges = map(lambda x:'<=='+decode_word(x[0])+'== '+decode_node(nodeuid2zipped(x[1]))+' '+str(x[2:])+'',bes)
        output = '['+textnode+']'
        output+= '\n'+ '**OUT:********'
        for line in pp_fw_edges:
            output+= '\n  '+line
        output+='\n'+ '**IN:*********'
        for line in pp_bw_edges:
            output+= '\n  '+line
        return output


    def get_analogous_concepts(self,textnode,simple_results_p=0):

        """
        -inputs a node
        -uses structure-mapping to generate a list of
        analogous concepts
        -each analogous concept shares some structural features
        with the input node
        -the strength of an analogy is determined by the number
        and weights of each feature. a weighting scheme is used
        to disproportionately weight different relation types
        and also weights a structural feature by the equation:
        math.log(f+f2+0.5*(i+i2)+2,4), where f=
        i =
        - outputs a list of RESULTs rank-ordered by relevance
        - each RESULT is a triple of the form:
                     ('analogous concept', SHARED_STRUCTURES, SCORE)
        - SCORE is a scalar valuation of quality of a result
          (for now, this number does not have much external meaning)
        - SHARED_STRUCTURES is a list of triples, each of the form:
                     ('RelationType', 'target node', SCORE2)
        - SCORE2 is a scalar valuation of the strength of a
        particular shared structure
        - if simple_results_p = 1, then output object is simply
        a list of rank-ordered concepts
      """
        decode_node,encode_node,encode_word,decode_word = self.decode_node,self.encode_node,self.encode_word,self.decode_word
        zipped2nodeuid,nodeuid2zipped = self.zipped2nodeuid, self.nodeuid2zipped
        zipped2edgeuid,edgeuid2zipped = self.zipped2edgeuid, self.edgeuid2zipped
        fw_edges,bw_edges = self.fwd,self.rev
        linktype_stoplist = ['ConceptuallyRelatedTo','ThematicKLine','SuperThematicKline']
        linktype_stoplist = map(encode_word,linktype_stoplist)
        linktype_weights = {'HasProperty':3.0,
                            'UsedFor':2.0,
                            'CapableOf':2.0,
                            'ReceivesAction':1.5}
        textnode=textnode.strip()
        encoded_node = encode_node(textnode)
        node_uid = zipped2nodeuid(encoded_node)
        fes = fw_edges.get(node_uid,[])
        print fw_edges
        fes = map(edgeuid2zipped,fes)
        candidates = {}
        for fe in fes:
            commonpred,commonnode,f,i = fe
            if commonpred in linktype_stoplist:
                continue
            bes = bw_edges.get(commonnode,[])
            bes = map(edgeuid2zipped,bes)
            bes = filter(lambda x:x[0]==commonpred and x[1]!=node_uid,bes)
            for be in bes:
                commonpred2,candidate,f2,i2 = be
                link_strength = math.log(f+f2+0.5*(i+i2)+2,4)
                weight = link_strength*linktype_weights.get(decode_word(commonpred),1.0)
                candidates[candidate] = candidates.get(candidate,[])+[(commonpred,commonnode,weight)]
        scored_candidates = map(lambda x:(x[0],x[1],sum(map(lambda y:y[2],x[1]))),candidates.items())
        scored_candidates.sort(lambda x,y:int(1000*(y[2]-x[2])))
        scored_candidates = map(lambda y:(decode_node(nodeuid2zipped(y[0])),map(lambda x:(decode_word(x[0]),decode_node(nodeuid2zipped(x[1])),weight),y[1]),y[2]),scored_candidates)
        if simple_results_p:
            return map(lambda x:x[0],scored_candidates)
        return scored_candidates


    def getuid(self):
        self.global_uid += 1
        return self.global_uid


    def nodeuid2zipped(self,uid):
        return self.node_lookup.get(uid,None)


    def zipped2edgeuid(self,edge):
        edge_hash = self.edge_hash
        edge_uid = edge_hash.get(edge,None)
        if not edge_uid:
            edge_uid = self.getuid()
            edge_hash[edge]=edge_uid
            self.edge_lookup[edge_uid] = edge
        return edge_uid


    def edgeuid2zipped(self,uid):
        return self.edge_lookup.get(uid,None)


    def encode_word(self,word):
        word_hash= self.word_hash
        word_uid = word_hash.get(word,None)
        if not word_uid:
            word_uid = self.getuid()
            word_hash[word] = word_uid
            self.word_lookup[word_uid] = word
        return word_uid


    def decode_word(self,word_uid):
        return self.word_lookup.get(word_uid,None)


    def decode_node(self,node_tuple):
        wl_get = self.word_lookup.get
        return ' '.join(map(lambda word_uid:wl_get(word_uid,'UNKNOWN'),node_tuple))

class ConceptNet_compat:
    @staticmethod
    def split_textnodes_weights(textnodes):
        # Make textnodes into a dict of (text, weight). Possible inputs:
        if isinstance(textnodes, dict):
            # a dictionary.
            return textnodes.keys(), textnodes.values()
        elif isinstance(textnodes, str):
            # a single item:
            return [textnodes], [1.0]
        elif isinstance(textnodes, list) and all([isinstance(x, str) for x in textnodes]):
            # probably a list of strings:
            textnodes = dict([(x, 1.0) for x in textnodes])
            return textnodes.keys(), textnodes.values()

    # Old-style to new-style translation
    _oldnew_translation = {
        'FirstSubeventOf':'HasFirstSubevent',
        'DesirousEffectOf':'CausesDesire',
        'ThematicKLine':'ConceptuallyRelatedTo',
        'SubeventOf':'HasSubevent',
        'SuperThematicKLine':'ConceptuallyRelatedTo',
        'LastSubeventOf':'HasLastSubevent',
        'LocationOf':'AtLocation',
        'CapableOfReceivingAction':'ReceivesAction',
        'PrerequisiteEventOf':'HasPrerequisite',
        'MotivationOf':'MotivatedByGoal',
        'PropertyOf':'HasProperty',
        'EffectOf':'Causes',
        'DesireOf':'Desires'
        }

    @staticmethod
    def _old_to_new(map):
        '''Converts linktype weights dictionaries from old form to new.'''
        fwdt = ((ptype, weight) for ptype, weight in map.items()
                if not ptype.endswith('Inverse'))
        revt = ((ptype[:-len('Inverse')], weight)
                for ptype, weight in map.items() if ptype.endswith('Inverse'))

        fwds = dict((ConceptTools.oldnew_translation.get(ptype, ptype), weight)
                    for ptype, weight in fwdt)
        revs = dict((ConceptTools.oldnew_translation.get(ptype, ptype), weight)
                    for ptype, weight in revt)
        return fwds, revs



if __name__ == '__main__':
    c = ConceptTools()
    print c.get_context('couch')

########NEW FILE########
__FILENAME__ = concept_tools_new
from conceptnet.models import Concept
from conceptnet.analogyspace import *
import operator
import cPickle as pickle
import os

class ConceptTools(object):
    
    def __init__(self, tensor):
        self.tensor = tensor

    def get_related_concepts(self, root_concepts, root_weights=None, max_visited_nodes=100, max_results=10, 
                             link_weights_forward=None, link_weights_reverse=None, prettyprint=True):
        '''
        root_concepts: a list of concept names to start from
        root_weights: a list of weights (0.0 to 1.0) specifying how to weight the concepts we're starting from

        max_visited_nodes: will not explore more than this number of concepts
        max_results: the number of results to display
        
        link_weights_forward: a dictionary mapping Relation to weight in range (0.0, 1.0), specifying how to weight forward relations (concept on left)
        link_weights_reverse: a dictionary mapping Relation to weight in range(0,0, 1.0), specifying how to weight reverse relatiosn (concept on right)
           If either are None, uses default ConceptTools weights

        '''

        
        #Concept_weights: maps a concept to a weight, specifying how to weigh its children
        concept_weights = {}
        if root_weights:
            assert(len(root_concepts) == len(root_weights))
            for concept, weight in zip(root_concepts, root_weights):
                concept_weights[concept] = weight
        else:
            for c in root_concepts:
                concept_weights[c] = 1

        
        #Concepts: maps concepts discovered to a tuple with the original score of the assertion, the weight we've assigned it, 
        #          and the level it was discovered on
        concepts = {}
       

        #Relation weights
        forward_relation_weights = {}
        reverse_relation_weights = {}
        
        #If link_weights_forward or reverse are None, use default weights
        if not(link_weights_forward):
            link_weights_forward = self.get_default_weights_forward()
        if not(link_weights_reverse):
            link_weights_reverse = self.get_default_weights_reverse()

        #Filter out the relations whose weights are equal to 0
        for relation in link_weights_forward:
            weight = link_weights_forward[relation]
            if weight != 0:
                forward_relation_weights[relation] = weight
        for relation in link_weights_reverse:
            weight = link_weights_reverse[relation]
            if weight != 0:
                reverse_relation_weights[relation] = weight


        visited_nodes = 0
        level = 1
        concept_queue = root_concepts

        #Concepts we've already expanded
        seen = {}


        #Function for getting the 'weighted average' of two weights; used when we run into a concept we've already seen before
        #distance is the difference in levels (concepts on the same level of search have distance of 0)
        def weighted_mean(previous_weight, current_weight, distance):
            w1 = (1.0 / (2 * (distance+1)))    #If on same level, should just compute arithmetic mean
            w2 = 1.0 - w1
            return w1*current_weight + w2*previous_weight


        #This formula was used in the previous version of concept tools....
        # Init discount factors
        #distance_discount = 0.5
        # FIXME: magic formula comes from...?
       # def branching_discount(bf, bf_mu=2.5, bf_sigma=1.0):
         #   return ((1./(bf_sigma*((2*math.pi)**0.5)))
          #          *(math.e**(-(math.log(bf+5,5)-bf_mu)**2/(2*bf_sigma**2))))

        while concept_queue:
            next_level_concepts = []

            i = 0
            while i < len(concept_queue) and visited_nodes <= max_visited_nodes:
                #Gets the next concept
                c = concept_queue[i]
                
                #If we've already expanded on this concept, or this concept isn't in the tensor, continue
                if c in seen or self.tensor[c,:] == 0:
                    i += 1
                    continue

                visited_nodes += 1
                
                #Gets the slice of the tensor dealing with the concept we're looking at
                slice = self.tensor[c, :]
                
                #Iterate over all assertions made about this concept
                for a in slice.iterkeys():
                    direction, relation, concept2  = a[0]
                    score = slice[a]

                    if score <= 0:
                        continue
                    
                    #Checks to see that this is a relation we care about
                    if relation in forward_relation_weights and direction == 'right':
                        next_level_concepts.append(concept2)
                        
                        #The weight to give this concept (how 'relevant' it is)
                        #Currently takes into account the parent concept's weight, the weight given to the relation, the assertion score, and the level we're on
                        parent_weight = concept_weights[c]
                        concept2_weight = (score * (1./level)  * parent_weight)*forward_relation_weights[relation]
                        
                        if concept2 in concepts:
                            #If we've already seen this concept, get the weighted average of the previous weight and the new weight
                            _, prev_weight, prev_level = concepts[concept2]
                            print "AVERAGING"
                            print "Concept2", concept2
                            print "Prev Weight", prev_weight
                            print "Current Wight", concept2_weight
                            print "Prev Level / Current Level", prev_level, level
                            print "Regular Average", ((prev_weight + concept2_weight)/2.0)
                            concept2_weight = weighted_mean(prev_weight, concept2_weight, (level - prev_level))
                            print "Weight Given", concept2_weight
                        #print "WEIGHT GIVEN", weight
                        concepts[concept2] = (score, concept2_weight, level)
                        concept_weights[concept2] = concept2_weight 

                    elif relation in reverse_relation_weights and direction == 'left':
                        next_level_concepts.append(concept2)

                        parent_weight = concept_weights[c]
                        concept2_weight = (score * (1./level) * parent_weight)*reverse_relation_weights[relation]

                        if concept2 in concepts:
                            _, prev_weight, prev_level = concepts[concept2]
                            concept2_weight = weighted_mean(prev_weight, concept2_weight, (level - prev_level))
                        concepts[concept2] = (score, concept2_weight, level)
                        concept_weights[concept2] = concept2_weight
                    
                    
                #Mark this concept as explored  
                seen[c] = True
                i += 1

            level += 1
            concept_queue = next_level_concepts
            
        #print concepts

        #Now get the top concepts
        concept_lst = sorted(concepts.items(), key=lambda x:(x[1][1], x[0]), reverse=True)
        
        if prettyprint and concept_lst:
            print "Top Related Concepts"
            print "-----------------------------"
            print "%-20s %s, %s" % ('concept', 'score', 'weight')
            for c, (score,weight,level) in concept_lst[:max_results]:
                str = "%-20s %s, %s" % (c, score, weight)
                print str


        return concept_lst
        


    def get_default_weights_forward(self):
        forward_link_weights = {'AtLocation': 0.9, 'CapableOf': 0.8, 'Causes': 1.0, 'CausesDesire': 1.0, 'ConceptuallyRelatedTo': 1.0, 'CreatedBy': 1.0,
            'DefinedAs': 1.0, 'Desires': 1.0, 'HasFirstSubevent': 1.0, 'HasLastSubevent': 1.0, 'HasPrerequisite': 1.0, 'HasProperty': 1.0,
            'HasSubevent': 0.9, 'IsA': 0.9, 'MadeOf': 0.7, 'MotivatedByGoal': 1.0,'PartOf': 1.0, 'ReceivesAction': 0.6, 'UsedFor': 1.0}
        return forward_link_weights
    def get_default_weights_reverse(self):
        reverse_link_weights = {'AtLocation': 0.0, 'CapableOf': 0.0, 'Causes': 0.0, 'CausesDesire': 0.0, 'ConceptuallyRelatedTo': 0.0, 'CreatedBy': 0.0,
            'DefinedAs': 0.0, 'Desires': 0.0, 'HasFirstSubevent': 0.0, 'HasLastSubevent': 0.0, 'HasPrerequisite': 0.0, 'HasProperty': 0.0,
            'HasSubevent': 0.0, 'IsA': 0.0,'MadeOf': 0.0, 'MotivatedByGoal': 0.0, 'PartOf': 0.0, 'ReceivesAction': 0.0, 'UsedFor': 0.0}
        return reverse_link_weights

    
    #Some examples
    def project_affective(self, root_concepts, root_weights=None):
        '''
        Gets the emotional context and consequences underlying thes root_concepts
        '''
        relation_weights_forward = {'Desires':1.0, 'CausesDesire': 1.0, 'MotivatedByGoal':1.0}
        self.get_related_concepts(root_concepts, root_weights, link_weights_forward=relation_weights_forward, link_weights_reverse={})

    def project_spatial(self, root_concepts, root_weights=None):
        '''
        Gets relevant locations and objects in the same scene as the root concepts
        '''
        relation_weights_forward = {'AtLocation':1.0, 'ConceptuallyRelatedTo': .5}
        self.get_related_concepts(root_concepts, root_weights, link_weights_forward=relation_weights_forward, link_weights_reverse={})
    
    def project_details(self, root_concepts, root_weights=None):
        '''
        Gets a thing's parts, materials, properties, and instances and an event's subevents
        '''
        relation_weights_forward = {'HasFirstSubevent':1.0,'HasLastSubevent':1.0, 'HasSubevent':1.0, 'MadeOf':1.0, 'PartOf':1.0, 'HasProperty':0.9}
        self.get_related_concepts(root_concepts, root_weights, link_weights_forward=relation_weights_forward, link_weights_reverse={})

    def project_consequences(self, root_concepts, root_weights = None):
        '''
        Gets the 'causal projection', which is possible consequences of an event or possible actions resulting from its presence
        '''
        relation_weights_forward = {'CausesDesire':1.0, 'UsedFor':0.4, 'CapableOf':0.4, 'ReceivesAction':0.3, 'Causes':1.0}
        self.get_related_concepts(root_concepts, root_weights, link_weights_forward=relation_weights_forward, link_weights_reverse={})

    def project_utility(self, root_concepts, root_weights = None):
        '''
        Gets the 'causal projection', which is possible consequences of an event or possible actions resulting from its presence
        '''
        relation_weights_forward = {'UsedFor':1.0, 'CapableOf':1.0}
        self.get_related_concepts(root_concepts, root_weights, link_weights_forward=relation_weights_forward, link_weights_reverse={})



#Loads the concepts from the database into a tensor
#I just added this without knowing about get_pickled_cached_thing so..this should obviously be changed
class LoadTensor():
    
    def __init__(self, lang='en', path='tmp.pkl'):
        self.language = lang
        self.file_name = path

    def reload(self):
        print "Refreshing Tensor"
        tensor = conceptnet_2d_from_db(self.language)
        fl = file(self.file_name, 'wb')
        pickle.dump(tensor, fl, False)
        print "Tensor refreshed"
        fl.close()

    def load(self):
        #Checks to see if the pickle file already exists
        if (os.path.exists(self.file_name) == False):
            #If not, reloads pickle
            self.reload()

        print "Loading Tensor"
        fl = file(self.file_name, 'rb')
        tensor = pickle.load(fl)
        fl.close()
        return tensor





if __name__ == '__main__':
    #--------Some example concepts to use
    #print "Getting test concepts"
    dog = Concept.get('dog', 'en').text
    leash = Concept.get('leash', 'en').text
    umb = Concept.get('umbrella', 'en').text
    cat = Concept.get('cat', 'en').text
    #pets = [dog, cat]

    #temple = Concept.get('temple', 'en').text
   # hindu = Concept.get('hindu', 'en').text
   # asia = Concept.get('asia', 'en').text
   # nepal = Concept.get('Nepal', 'en').text
   # spain = Concept.get('Spain', 'en').text
   #test = [temple, asia, nepal]

    #----------Load Tensor
    tensor = LoadTensor().load()

    
    #Sample relation dictionary
    atlocal = Relation.get('AtLocation').name
    usedfor = Relation.get('UsedFor').name
    desires = Relation.get('Desires').name
    #isa = Relation.get('IsA')
    #partof = Relation.get('PartOf')
    relation_weights_f = {atlocal: 1, usedfor: .5, desires: 0}
    relation_weights_r = {atlocal: 1, usedfor: .2, desires: 0}
    # relation_weights_f = {'IsA': 1, 'PartOf': .5, 'Desires': 0}
    #relation_weights_r = {'IsA': 1, 'PartOf': .5}

    #print "Building ConceptTools"
    #c = ConceptTools(tensor)
    #c = ConceptTools()

    #----------Sample ConceptTools stuff
    c.get_related_concepts([dog], [1], max_levels=1, link_weights_forward=relation_weights_f, link_weights_reverse=relation_weights_r)
    #c.get_related_concepts([spain], [1], max_levels=2, link_weights_forward=relation_weights_f, link_weights_reverse=relation_weights_r)
    #related_concepts = c.get_related_concepts([temple], [1], max_levels=2)
    #print "Project Affective"
    #project_affective(dog, tensor)

    c.project_affective([dog])
    #c.project_consequences([dog])
    #c.project_details([dog])
    #c.project_spatial([dog])
    #c.project_utility([leash])
    #c.project_utility([umb])

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from csamoa.representation.presentation.models import Predicate

urlpatterns = patterns('csamoa.realm.views',
    url(r'^concept/', 'get_stemid'),
    url(r'^concept/(?P<id>\d+)/all', 'get_stem_allforms'),
)

# URLs:
# GET /concept/?text={text,...}&language={language}
#  -> gets concept id(s) for text(s)
# GET /concept/{id}/canonical/ -> gets canonical form for concept
# GET /concept/{id}/all/ -> gets all forms for concept
# GET /concept/{id,...}/context -> gets context for the concept(s)


# # Programmatically define the API
# api = {
#     'concept': {
#         '__required': {
#             'language': TextField,
#             },
#         'id': Function(get_stemid,

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from conceptnet.corpus.models import Language, Sentence

admin.site.register(Language)
admin.site.register(Sentence)


########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from conceptnet.corpus.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'TaggedSentence'
        db.create_table('tagged_sentences', (
            ('text', orm['corpus.TaggedSentence:text']),
            ('language', orm['corpus.TaggedSentence:language']),
            ('sentence', orm['corpus.TaggedSentence:sentence']),
        ))
        db.send_create_signal('corpus', ['TaggedSentence'])
        
        # Adding model 'Language'
        db.create_table('corpus_language', (
            ('id', orm['corpus.Language:id']),
            ('name', orm['corpus.Language:name']),
            ('sentence_count', orm['corpus.Language:sentence_count']),
        ))
        db.send_create_signal('corpus', ['Language'])
        
        # Adding model 'DependencyParse'
        db.create_table('dependency_parses', (
            ('id', orm['corpus.DependencyParse:id']),
            ('sentence', orm['corpus.DependencyParse:sentence']),
            ('linktype', orm['corpus.DependencyParse:linktype']),
            ('word1', orm['corpus.DependencyParse:word1']),
            ('word2', orm['corpus.DependencyParse:word2']),
            ('index1', orm['corpus.DependencyParse:index1']),
            ('index2', orm['corpus.DependencyParse:index2']),
        ))
        db.send_create_signal('corpus', ['DependencyParse'])
        
        # Adding model 'Sentence'
        db.create_table('sentences', (
            ('id', orm['corpus.Sentence:id']),
            ('text', orm['corpus.Sentence:text']),
            ('creator', orm['corpus.Sentence:creator']),
            ('created_on', orm['corpus.Sentence:created_on']),
            ('language', orm['corpus.Sentence:language']),
            ('activity', orm['corpus.Sentence:activity']),
            ('score', orm['corpus.Sentence:score']),
        ))
        db.send_create_signal('corpus', ['Sentence'])
        
        # Adding model 'Frequency'
        db.create_table('nl_frequency', (
            ('id', orm['corpus.Frequency:id']),
            ('language', orm['corpus.Frequency:language']),
            ('text', orm['corpus.Frequency:text']),
            ('value', orm['corpus.Frequency:value']),
        ))
        db.send_create_signal('corpus', ['Frequency'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'TaggedSentence'
        db.delete_table('tagged_sentences')
        
        # Deleting model 'Language'
        db.delete_table('corpus_language')
        
        # Deleting model 'DependencyParse'
        db.delete_table('dependency_parses')
        
        # Deleting model 'Sentence'
        db.delete_table('sentences')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'corpus.dependencyparse': {
            'Meta': {'db_table': "'dependency_parses'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index1': ('django.db.models.fields.IntegerField', [], {}),
            'index2': ('django.db.models.fields.IntegerField', [], {}),
            'linktype': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'sentence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Sentence']"}),
            'word1': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'word2': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'corpus.language': {
            'id': ('django.db.models.fields.CharField', [], {'max_length': '16', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sentence_count': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'corpus.frequency': {
            'Meta': {'db_table': "'nl_frequency'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'value': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'text': ('django.db.models.fields.TextField', [], {}),
        },
        'corpus.sentence': {
            'Meta': {'db_table': "'sentences'"},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['events.Activity']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'votes': ('django.contrib.contenttypes.generic.GenericRelation', [], {'to': "orm['voting.Vote']"})
        },
        'corpus.taggedsentence': {
            'Meta': {'db_table': "'tagged_sentences'"},
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'sentence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Sentence']", 'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'events.activity': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {})
        },
        'voting.vote': {
            'Meta': {'unique_together': "(('user', 'content_type', 'object_id'),)", 'db_table': "'votes'"},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'vote': ('django.db.models.fields.SmallIntegerField', [], {})
        }
    }
    
    complete_apps = ['corpus']

########NEW FILE########
__FILENAME__ = 0002_rename_tables

from south.db import db
from django.db import models
from conceptnet.corpus.models import *

class Migration:
    
    def forwards(self, orm):
        db.rename_table('sentences', 'corpus_sentence')
        db.rename_table('tagged_sentences', 'corpus_taggedsentence')
        db.rename_table('dependency_parses', 'corpus_dependencyparse')
    
    def backwards(self, orm):
        db.rename_table('corpus_sentence', 'sentences')
        db.rename_table('corpus_taggedsentence', 'tagged_sentences')
        db.rename_table('corpus_dependencyparse', 'dependency_parses')
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'corpus.dependencyparse': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index1': ('django.db.models.fields.IntegerField', [], {}),
            'index2': ('django.db.models.fields.IntegerField', [], {}),
            'linktype': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'sentence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Sentence']"}),
            'word1': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'word2': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'corpus.language': {
            'id': ('django.db.models.fields.CharField', [], {'max_length': '16', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sentence_count': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'corpus.sentence': {
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['events.Activity']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'votes': ('django.contrib.contenttypes.generic.GenericRelation', [], {'to': "orm['voting.Vote']"})
        },
        'corpus.taggedsentence': {
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'sentence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Sentence']", 'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'events.activity': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {})
        },
        'voting.vote': {
            'Meta': {'unique_together': "(('user', 'content_type', 'object_id'),)", 'db_table': "'votes'"},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'vote': ('django.db.models.fields.SmallIntegerField', [], {})
        }
    }
    
    complete_apps = ['corpus']

########NEW FILE########
__FILENAME__ = models
__version__ = "4.0b2"
__author__ = "kcarnold@media.mit.edu, rspeer@media.mit.edu, jalonso@media.mit.edu, havasi@media.mit.edu, hugo@media.mit.edu"
__url__ = 'conceptnet.media.mit.edu'
from django.db import models
from django.contrib.auth.models import User
from django.utils.functional import memoize
from datetime import datetime
from voting.models import Vote
from events.models import Event, Activity
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from simplenlp import get_nl
import re

class ScoredModel(object):
    """
    A ScoredModel is one that users can vote on through a Django-based Web
    site.

    The score is cached in a column of the object's database table, and updated
    whenever necessary.

    This makes use of the `django-voting` library. However, if you alter votes
    by using the `django-voting` library directly, the score will not be
    updated correctly.
    """
    def get_rating(self, user):
        """
        Get the Vote object representing a certain user's vote on a certain
        object. Returns None if the user has not voted on that object.
        """
        return getattr(Vote.objects.get_for_user(self, user), 'vote', None)

    def set_rating(self, user, val, activity=None):
        """
        Set a user's Vote on a certain object. If the user has previously voted
        on that object, it removes the old vote.
        """
        Vote.objects.record_vote(self, user, val)
        if activity is not None:
            Event.record_event(self, user, activity)
        #self.update_score()

    def update_score(self):
        """
        Ensure that the `score` property of this object agrees with the sum of
        the votes it has received.
        """
        self.score = Vote.objects.get_score(self)['score']
        self.save()

# Register signals to make score updates happen automatically.
def denormalize_votes(sender, instance, created=False, **kwargs):
    """This recalculates the vote total for the object
    being voted on"""
    instance.object.update_score()

models.signals.post_save.connect(denormalize_votes, sender=Vote)
models.signals.post_delete.connect(denormalize_votes, sender=Vote)

cached_langs = {}
def get_lang(lang_code):
    """
    Get a Language instance for a particular language, and remember it so that
    it doesn't have to be looked up again.
    """
    return Language.objects.get(id=lang_code)
get_lang = memoize(get_lang, cached_langs, 1)

class Language(models.Model):
    """
    A database object representing a language.

    Instances of Language can be used in filter expressions to select only
    objects that apply to a particular language. For example:
    
    >>> en = Language.get('en')
    >>> english_sentences = Sentence.objects.filter(language=en)
    """
    id = models.CharField(max_length=16,primary_key=True)
    name = models.TextField(blank=True)
    sentence_count = models.IntegerField(default=0)

    def __str__(self):
        return "%s (%s)" % (self.name, self.id)

    @staticmethod
    def get(id):
        """
        Get a language from its ISO language code.

        Some relevant language codes::

            en = English
            pt = Portuguese
            ko = Korean
            ja = Japanese
            nl = Dutch
            es = Spanish
            fr = French
            ar = Arabic
            zh = Chinese
        """
        if isinstance(id,Language): return id
        return get_lang(id)

    @property
    def nl(self):
        """
        A collection of natural language tools for a language.

        See :mod:`simplenlp` for more information on using these tools.
        """
        return get_nl(self.id)

class Sentence(models.Model, ScoredModel):
    """
    A statement entered by a contributor, in unparsed natural language.
    """
    text = models.TextField(blank=False)
    creator = models.ForeignKey(User)
    created_on = models.DateTimeField(default=datetime.now)
    language = models.ForeignKey(Language)
    activity = models.ForeignKey(Activity)
    score = models.IntegerField(default=0)
    votes = generic.GenericRelation(Vote)

    def __unicode__(self):
        return  u'<' + self.language.id + u': ' + \
                u'"' + self.text + u'"' + \
                u'(by:' + unicode(self.creator_id) + \
                u' activity:' + self.activity.name + \
                u')>'
    

    def update_consistency(self):
        """
        Assume that the creator of this sentence voted for it, and calculate
        the score.
        """
        try:
            if self.creator is not None and self.get_rating(self.creator) is None:
                if self.creator.username != 'verbosity':
                    Vote.objects.record_vote(self, self.creator, 1)
            self.update_score()
        except User.DoesNotExist:
            self.creator = User.objects.get(username='_ghost')
            Vote.objects.record_vote(self, self.creator, 1)
            self.update_score()

class TaggedSentence(models.Model):
    """
    The results of running a sentence through a tagger such as MXPOST.

    We could use this as a step in parsing ConceptNet, but we currently don't.
    """
    text = models.TextField()
    language = models.ForeignKey(Language)
    sentence = models.ForeignKey(Sentence, primary_key=True)
    
    def tagged_words(self):
        for part in self.text.split(" "):
            word, tag = part.rsplit("/", 1)
            yield word, tag
    
    def __unicode__(self):
        return self.text
    
class DependencyParse(models.Model):
    """
    Each instance of DependencyParse is a single link in the Stanford
    dependency parse of a sentence.
    """
    sentence = models.ForeignKey('Sentence')
    linktype = models.CharField(max_length=20)
    word1 = models.CharField(max_length=100)
    word2 = models.CharField(max_length=100)
    index1 = models.IntegerField()
    index2 = models.IntegerField()
    
    _PARSE_RE = re.compile(r"(.+)\((.*)-(\d+)'*, (.*)-(\d+)'*\)")
    
    @staticmethod
    def from_string(sentence_id, depstring):
        try:
            link, w1, i1, w2, i2 = DependencyParse._PARSE_RE.match(depstring).groups()
        except AttributeError:
            raise ValueError("didn't match regex pattern: %s" % depstring)
        dep_obj = DependencyParse(sentence_id=sentence_id, linktype=link,
                                  word1=w1, index1=int(i1),
                                  word2=w2, index2=int(i2))
        return dep_obj

    def __unicode__(self):
        return u'%s(%s_%d, %s_%d) (sent %d)' % (
            self.linktype, self.word1, self.index1, self.word2, self.index2,
            self.sentence_id)

class Frequency(models.Model):
    """
    A Frequency is attached to an :class:`Assertion` to indicate how often
    it is the case. Each Frequency is attached to a natural-language modifier
    (generally an adverb), and has a value from -10 to 10.
    """
    language = models.ForeignKey(Language)
    text = models.CharField(max_length=50, blank=True,
                            help_text='The frequency adverb used (e.g., "always", "sometimes", "never"). Empty means that the sentence has no frequency adverb.')
    # FIXME: is this help text still valid?
    value = models.IntegerField(help_text='A number between -10 and 10 indicating a rough numerical frequency to associate with this word. "always" would be 10, "never" would be -10, and not specifying a frequency adverb in English is specified to be 5.')

    def __unicode__(self):
        return u'<%s: "%s" (%d)>' % (self.language.id, self.text, self.value)

    class Meta:
        unique_together = (('language', 'text'),)
        verbose_name = 'frequency adverb'
        verbose_name_plural = 'frequency adverbs'
        db_table = 'nl_frequency'

########NEW FILE########
__FILENAME__ = admin

########NEW FILE########
__FILENAME__ = adverbs
import yaml
from corpus.models import Language
from conceptnet4.models import Frequency
frequencies = {
    'never': -10,
    "n't": -5,
    "doesn't": -5,
    "not": -5,
    "no": -5,
    "can't": -5,
    "won't": -5,
    "don't": -5,
    "couldn't": -5,
    "wouldn't": -5,
    "didn't": -5,
    "shouldn't": -5,
    "cannot": -5,
    "isn't": -5,
    "wasn't": -5,
    "aren't": -5,
    "weren't": -5,
    'rarely': -2,
    'infrequently': -2,
    'few': -2,
    'seldom': -2,
    'hardly': -2,
    'occasionally': 2,
    'sometimes': 4,
    'possibly': 4,
    'some': 4,
    'generally': 6,
    'typically': 6,
    'likely': 6,
    'probably': 6,
    'often': 6,
    'oftentimes': 6,
    'frequently': 6,
    'usually': 8,
    'most': 8,
    'mostly': 8,
    'almost': 9,
    'always': 10,
    'every': 10,
    'all': 10,
}
en = Language.get('en')
dbfreqs = {
    -10: Frequency.objects.get(language=en, text=u"never"),
    -5: Frequency.objects.get(language=en, text=u"not"),
    -2: Frequency.objects.get(language=en, text=u"rarely"),
    2: Frequency.objects.get(language=en, text=u"occasionally"),
    4: Frequency.objects.get(language=en, text=u"sometimes"),
    5: Frequency.objects.get(language=en, text=u""),
    6: Frequency.objects.get(language=en, text=u"generally"),
    8: Frequency.objects.get(language=en, text=u"usually"),
    9: Frequency.objects.get(language=en, text=u"almost always"),
    10: Frequency.objects.get(language=en, text=u"always"),
}

def map_adverb(adv):
    words = [w.lower() for w in adv.split()]
    minfreq = 11
    for word in words:
        if word in frequencies:
            minfreq = min(minfreq, frequencies[word])
    if minfreq == 11: minfreq = 5
    return dbfreqs[minfreq]

def demo():
    adverbs = set()
    for entry in yaml.load_all(open('delayed_sentences.yaml')):
        if entry is None: continue
        matches = entry.get('matches', {})
        adv = matches.get('a')
        if adv and adv not in adverbs:
            print adv,
            print map_adverb(adv)
            adverbs.add(adv)


########NEW FILE########
__FILENAME__ = build
#!/usr/bin/env python
import sys, traceback
from conceptnet4.models import Assertion, Batch, RawAssertion, Frame,\
  Frequency, Relation, SurfaceForm, Concept, Rating
import conceptnet.models as cn3
from corpus.models import Sentence, Language, Activity
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from corpus.parse.adverbs import map_adverb
from itertools import islice
import yaml

csamoa4_activity = Activity.objects.get(name='csamoa4 self-rating')
good_acts = [ 16, 20, 22, 24, 28, 31, 32 ]

def process_yaml(entry, lang, batch):
    if entry is None: return []
    frametext, id, matches, reltext = (entry['frametext'], entry['id'],
    entry['matches'], entry['reltext'])
    sentence = Sentence.objects.get(id=id)
    print sentence.text.encode('utf-8')
    if sentence.activity.id in good_acts:
        print "(we have a better parse)"
        return []
    if (sentence.text.startswith('Situation:')
        or sentence.text.startswith('The statement')
        or sentence.text.startswith('To understand')
        or sentence.text.startswith('In the event')):
            print "* skipped *"
            return []
    if matches.get(2).startswith('do the following'):
        print "** skipped **"
        return []
    
    if reltext is None or reltext == 'junk': return []

    # quick fixes
    if reltext == 'AtLocation' and matches.get('a') == 'of': return []
    if reltext == 'AtLocation' and matches.get('a') == 'near':
        reltext = 'LocatedNear'
    if reltext in ['IsA', 'CapableOf'] and matches.get('a') in ['in', 'on', 'at', 'by']:
        reltext = 'AtLocation'
        matches['a'] = ''
    for val in matches.values():
        if len(val.split()) > 6:
            # we'd rather wait to parse this better.
            return []

    relation = Relation.objects.get(name=reltext)
    
    surface_forms = [SurfaceForm.get(matches[i], lang, auto_create=True)
                     for i in (1, 2)]
    concepts = [s.concept for s in surface_forms]

    # FIXME: english only so far
    freq = map_adverb(matches.get('a', ''))
    
    frame, _ = Frame.objects.get_or_create(relation=relation, language=lang,
                                           text=frametext,
                                           defaults=dict(frequency=freq, 
                                                         goodness=1))
    frame.save()
    
    raw_assertion, _ = RawAssertion.objects.get_or_create(
        surface1=surface_forms[0],
        surface2=surface_forms[1],
        frame=frame,
        language=lang,
        creator=sentence.creator,
        defaults=dict(batch=batch))
    # still need to set assertion_id
    
    assertion, _ = Assertion.objects.get_or_create(
        relation=relation,
        concept1=concepts[0],
        concept2=concepts[1],
        frequency=freq,
        language=lang,
        defaults=dict(score=0)
    )
    assertion.score += 1
    #assertion.save()
    
    raw_assertion.assertion = assertion
    raw_assertion.sentence = sentence
    raw_assertion.save()

    sentence.set_rating(sentence.creator, 1, csamoa4_activity)
    raw_assertion.set_rating(sentence.creator, 1, csamoa4_activity)
    assertion.set_rating(sentence.creator, 1, csamoa4_activity)

    for old_raw in cn3.RawAssertion.objects.filter(sentence=sentence):
        pred = old_raw.predicate
        if not pred: continue
        for rating in pred.rating_set.all():
            score = rating.rating_value.deltascore
            if score > 0: score = 1
            if score < 0: score = -1
            if rating.activity_id is None:
                rating_activity = Activity.objects.get(name='unknown')
            else:
                rating_activity = rating.activity
            sentence.set_rating(rating.user, score, rating_activity)
            raw_assertion.set_rating(rating.user, score, rating_activity)
            assertion.set_rating(rating.user, score, rating_activity)
    
    print '=>', unicode(assertion).encode('utf-8')
    return [assertion]

def run(user, lang, start_page=1):
    batch = Batch()
    batch.owner = user
    
    #generator = yaml.load_all(open('delayed_test.yaml'))
    #all_entries = list(generator)
    all_entries = pickle.load(open('yamlparsed.pickle'))
    paginator = Paginator(all_entries,100)
    #pages = ((i,paginator.page(i)) for i in range(start_page,paginator.num_pages))

    @transaction.commit_on_success
    def do_batch(entries):
        for entry in entries:
            try:
                preds = process_yaml(entry, lang, batch)
            # changed to an improbable exception for now
            except ZeroDivisionError, e:
                # Add entry
                e.entry = entry

                # Extract traceback
                e_type, e_value, e_tb = sys.exc_info()
                e.tb = "\n".join(traceback.format_exception( e_type, e_value, e_tb ))

                # Raise again
                raise e

    # Process entries
    page_range = [p for p in paginator.page_range if p >= start_page]
    for i in page_range:
        entries = paginator.page(i).object_list
        
        # Update progress
        batch.status = "process_entry_batch " + str(i) + "/" + str(paginator.num_pages)
        batch.progress_num = i
        batch.progress_den = paginator.num_pages
        batch.save()

        try: do_batch(entries)
        
        except ZeroDivisionError, e:
            batch.status = "process_entry_batch " + str(i) + "/" + str(paginator.num_pages) + " ERROR!"
            batch.remarks = str(e.entry) + "\n" + str(e) + "\n" + e.tb
            print "***TRACEBACK***"
            print batch.remarks
            batch.save()
            raise e

import migrate_templated
if __name__ == '__main__':
    user = User.objects.get(username='rspeer')
    lang = Language.get('en')
    run(user, lang, start_page=214)
    migrate_templated.run(user, start_page=1)


########NEW FILE########
__FILENAME__ = metapattern
from pymeta.grammar import OMeta, ParseError
from conceptnet.corpus.models import Sentence, TaggedSentence
from itertools import chain
import sys

class PatternParserBase(OMeta):
    def __init__(self, string, globals=None):
        OMeta.__init__(self, string, globals)
        self.assertion_patterns = []
        
    def text(self, string):
        for c in string:
            if c == ' ':
                self.rule_tag()
            else:
                head = self.input.head()
                if c.lower() == head.lower():
                    self.input = self.input.tail()
                else: raise ParseError
        self.rule_tag()
        return string
    rule_text = text
    
    def hastag(self, tag):
        word = self.rule_aword()
        tags = self.rule_tags()
        print word, tags
        if tag in tags: return word
        else: raise ParseError
    rule_hastag = hastag
        

def words(*lst):
    return ' '.join(str(x) for x in lst if x)

SLOT1 = '{1}'
SLOT2 = '{2}'

metapatterns = """
space ::= <spaces> | <end>
wordchar ::= ~'_' ~' ' <letter>:c  => c
aword ::= <wordchar>+:cs           => ''.join(cs)
tag ::= '_' (<letter> | '$')+ <space>
tag1 ::= '_' (<letter> | '$')+:t   => ''.join(t)
tags ::= <tag1>+:ts <space>        => ts

CD ::= <hastag "CD">
DT ::= <hastag "DT">
IN ::= <hastag "IN">
JJ ::= <hastag "JJ">
JJR ::= <hastag "DT">
JJS ::= <hastag "JJS">
MD ::= <hastag "MD">
NN ::= <hastag "NN">
NNS ::= <hastag "NNS">
NNP ::= <hastag "NNP">
POS ::= <hastag "POS">
PRP ::= <hastag "PRP">
PRPp ::= <hastag "PRP$">
RB ::= <hastag "RB">
RP ::= <hastag "RP">
RPR ::= <hastag "RPR">
TO ::= <hastag "TO">
VB ::= <hastag "VB">
VBG ::= <hastag "VBG">
VBN ::= <hastag "VBN">
VBP ::= <hastag "VBP">
VBZ ::= <hastag "VBZ">
WDT ::= <hastag "WDT">

N1  ::= (<NN> | <NNS>)+:ns                      => ' '.join(ns)
Npr ::= <NNP>+:ns                               => ' '.join(ns)
join ::= (<text ","> | <text "and">):w          => w
AP  ::= ( (<JJ> | <VBN> | <PRPp> | <JJR> | <JJS> | <CD>):w => w 
        | <AP>:a1 <join>:c <AP>:a2              => words(a1, c, a2)
        | <AP>:a1 <AP>:a2                       => words(a1, a2)
        )
NP  ::= ( <DT>?:d <AP>?:a <N1>:n                => words(d, a, n)
        | <Npr> | <PRP>
        | <VBG>:v <RB>:r                        => words(v, r)
        | <VBG>:v <NP>?:n <P>?:p                => words(v, n, p)
        | <NP>:n <PP>:p                         => words(n, p)
        | <NP>:n1 "and":c <tag> <NP>:n2         => words(n1, c, n2)
        )
P   ::= (<IN>|<TO>)
PP  ::= ( <P>:p <NP>:np                         => words(p, np)
        | <TO>:t <VP>:v                         => words(t, v)
        )
V   ::= ( (<VB> | <VBZ> | <VBP>):v              => v
        | <text "go">:g <text "and">?:a <VB>:v  => words(g, a, v)
        )
VP  ::= ( <ADVP>:ap <V>:v <NP>?:np <PP>?:pp     => words(ap, v, np, pp)
        | <ADVP>:a (<BE> | <CHANGE>):v (<NP> | <AP>):o  => words(a, v, o)
        | <V>:v <ADV>:rb                        => words(v, rb)
        )
POST ::= ( <VBN> <PP> | <WDT> <VP> | <WDT> <S> ) => ''
S   ::= <NP>:n <VP>:v                           => words(n, v)
XP  ::= <NP> | <VP> | <S>
PASV ::= <VBN>:v <PP>+:ps                       => words(*([v]+ps))
be_word ::= (<token "be"> | <token "is"> | <token "are"> | <token "was">
            | <token "being"> | <token "been"> | <token "'s">
            | <token "'re"> | <token "'m">):w   => w
BE  ::= (<be_word>:w <tag>                      => w
        |<MD>:m <RB>?:r <BE>:b                  => words(m, r, b)
        )
DO ::= (<text "do"> | <text "does"> | <text "did">):w => w

CHANGE ::= ( <text "get"> | <text "gets"> | <text "become">
           | <text "becomes"> )
ADV    ::= <RB> | <RP> | <RBR>
ADVP   ::= (<MD> | <DO>)?:m <RB>*:rs            => words(*([m]+rs))

assertion ::= (
  <text "The first thing you do when you"> <VP>:t1 <text "is"> <VP>:t2
    => dict(frame="The first thing you do when you {1} is {2}",
            relation="HasFirstSubevent",
            text1=t1, text2=t2)

| <text "The last thing you do when you"> <VP>:t1 <text "is"> <VP>:t2
    => dict(frame="The last thing you do when you {1} is {2}",
            relation="HasLastSubevent",
            text1=t1, text2=t2)

| <text "Something you need to do before you"> <VP>:t1 <text "is"> <VP>:t2
    => dict(frame="Something you need to do before you {1} is {2}",
            relation="HasPrerequisite",
            text1=t1, text2=t2)
| <NP>:t1 <text "requires"> <NP>:t2
    => dict(frame="{1} requires {2}",
            relation="HasPrerequisite",
            text1=t1, text2=t2)

| <text "If you want to"> <VP>:t1 <text "then you should"> <VP>:t2
    => dict(frame="If you want to {1} then you should {2}",
            relation="HasPrerequisite",
            text1=t1, text2=t2)

| <NP>:t1 <BE>:x1 <ADVP>?:adv <text "made of">:x2 <NP>:t2
    => dict(frame=words(SLOT1, x1, adv, x2, SLOT2),
            relation="MadeOf", text1=t1, text2=t2, adv=adv)

| <NP>:t1 <BE>:x1 (<text "a kind of"> | <text "a sort of">):x2 <NP>:t2 <POST>
    => dict(frame=words(SLOT1, x1, x2, SLOT2),
            relation="IsA", text1=t1, text2=t2)

| <text "Somewhere">:x1 <NP>:t1 <text "can be is">:x2 <P>:x3 <NP>:t2
    => dict(frame=words(x1, SLOT1, x2, x3, SLOT2),
            relation="AtLocation", text1=t1, text2=t2)

| <text "Something you might find">:x1 <P>:x2 <NP>:t2 <text "is">:x3 <NP>:t1
    => dict(frame=words(x1, x2, SLOT2, x3, SLOT1),
            relation="AtLocation", text1=t1, text2=t2)

| <text "Something you find">:x1 <P>:x2 <NP>:t2 <text "is">:x3 <NP>:t1
    => dict(frame=words(x1, x2, SLOT2, x3, SLOT1),
            relation="AtLocation", text1=t1, text2=t2)

| <text "Somewhere">:x1 <NP>:t1 <text "can be is">:x2 <P>:x3 <NP>:t2
    => dict(frame=words(x1, SLOT1, x2, x3, SLOT2),
            relation="AtLocation", text1=t1, text2=t2)

| <text "You are likely to find">:x1 <NP>:t1 <P>:x2 <NP>:t2
    => dict(frame=words(x1, SLOT1, x2, SLOT2),
            relation="AtLocation", text1=t1, text2=t2)

| <NP>:t1 <BE>:x1 <text "used for">:x2 <NP>:t2
    => dict(frame=words(SLOT1, x1, x2, t2),
            relation="UsedFor", text1=t1, text2=t2)

| <NP>:t1 <BE>:x1 <text "used to">:x2 <VP>:t2
    => dict(frame=words(SLOT1, x1, x2, t2),
            relation="UsedFor", text1=t1, text2=t2)

| (<text "You"> | <text "People">):x1 <text "can">?:x2 <text "use">:x3
  <NP>:t1 <text "for">:x4 <NP>:t2
    => dict(frame=words(x1, x2, x3, SLOT1, x4, SLOT2),
            relation="UsedFor", text1=t1, text2=t2)

| (<text "You"> | <text "People">):x1 <text "can">?:x2 <text "use">:x3
  <NP>:t1 <text "to">:x4 <VP>:t2
    => dict(frame=words(x1, x2, x3, SLOT1, x4, SLOT2),
            relation="UsedFor", text1=t1, text2=t2)

| <NP>:t1 <BE>:x1 <ADVP>?:adv <text "for">:x2 <VP>:t2
    => dict(frame=words(SLOT1, x1, adv, x2, SLOT2),
            relation="UsedFor", text1=t1, text2=t2, adv=adv)

| <NP>:t1 <BE>:x1 <text "capable of">:x2 <VP>:t2
    => dict(frame=words(SLOT1, x1, x2, SLOT2),
            relation="CapableOf", text1=t1, text2=t2)

| <text "An activity"> <NP>:t1 <text "can do is"> (<NP>|<VP>):t2
    => dict(frame="An activity {1} can do is {2}",
            relation="CapableOf", text1=t1, text2=t2)

| <text "You would"> <NP>:t1 <text "because you want to"> <VP>:t2
    => dict(frame="You would {1} because you want to {2}",
            relation="MotivatedByGoal", text1=t1, text2=t2)

| <text "You would"> <NP>:t1 <text "because you want"> <NP>:t2
    => dict(frame="You would {1} because you want {2}",
            relation="MotivatedByGoal", text1=t1, text2=t2)

| <NP>:t1 <ADVP>:adv (<text "wants to"> | <text "want to">):x1 <VP>:t2
    => dict(frame=words(SLOT1, adv, x1, SLOT2),
            relation="Desires", text1=t1, text2=t2)

| <NP>:t1 <ADVP>:adv (<text "wants"> | <text "want">):x1 <NP>:t2
    => dict(frame=words(SLOT1, adv, x1, SLOT2),
            relation="Desires", text1=t1, text2=t2)
| <NP>:t1 <BE>:x1 <text "defined as">:x2 <VP>:t2
    => dict(frame=words(SLOT1, x1, x2, SLOT2),
            relation="DefinedAs", text1=t1, text2=t2)

| <NP>:t1 <BE>:x1 <text "the">:x2 <NP>:t2
    => dict(frame=words(SLOT1, x1, x2, SLOT2),
            relation="DefinedAs", text1=t1, text2=t2)

| <NP>:t1 <BE>:x1 <DT>:x2 <text "symbol of">:x3 <NP>:t2
    => dict(frame=words(SLOT1, x1, x2, x3, SLOT2),
            relation="SymbolOf", text1=t1, text2=t2)

| <NP>:t1 <text "represents"> <NP>:t2
    => dict(frame="{1} represents {2}",
            relation="SymbolOf", text1=t1, text2=t2)

| <NP>:t1 <text "would make you want to"> <VP>:t2
    => dict(frame="{1} would make you want to {2}",
            relation="CausesDesire",
            text1=t1, text2=t2)

| <text "You would"> <VP>:t1 <text "because"> <XP>:t2
    => dict(frame="You would {1} because {2}",
            relation="CausesDesire",
            text1=t1, text2=t2)

| <text "The effect of"> <XP>:t1 <text "is that"> <S>:t2
    => dict(frame="The effect of {1} is that {2}",
            relation="Causes", text1=t1, text2=t2)

| <text "The effect of"> <XP>:t1 <text "is"> <NP>:t2
    => dict(frame="The effect of {1} is {2}",
            relation="Causes", text1=t1, text2=t2)

| <text "The consequence of"> <XP>:t1 <text "is that"> <S>:t2
    => dict(frame="The consequence of {1} is that {2}",
            relation="Causes", text1=t1, text2=t2)

| <text "The consequence of"> <XP>:t1 <text "is"> <NP>:t2
    => dict(frame="The consequence of {1} is {2}",
            relation="Causes", text1=t1, text2=t2)

| <text "Something that might happen as a consequence of">:x1
  <XP>:t1 <text "is">:x2 <text "that">?:x3 <XP>:t2
    => dict(frame=words(x1, SLOT1, x2, x3, SLOT2),
            relation="Causes", text1=t1, text2=t2)

| <ADVP>:adv <NP>:t1 <text "causes">:x1 <text "you to">?:x2 <XP>:t2
    => dict(frame=words(adv, SLOT1, x1, x2, SLOT2),
            relation="Causes", text1=t1, text2=t2, adv=adv)

| (<text "Something"> | <text "One of the things">):x1
  <text "that">?:x2
  (<text "you might do"> | <text "you do"> | <text "might happen">):x3
  (<text "while"> | <text "when you"> | <text "when">):x4
  <XP>:t1 <text "is">:x5 <XP>:t2
    => dict(frame=words(x1, x2, x3, x4, SLOT1, x5, SLOT2),
            relation="HasSubevent", text1=t1, text2=t2)

| <NP>:t1 <BE>:x1 <ADVP>?:adv <text "part of">:x2 <NP>:t2
    => dict(frame=words(SLOT1, x1, adv, x2, SLOT2),
            relation="PartOf", text1=t1, text2=t2, adv=adv)

| <text "You make"> <NP>:t1 <text "by"> <XP>:t2
    => dict(frame="You make {1} by {2}",
            relation="CreatedBy", text1=t1, text2=t2)

| <NP>:t1 <text "is created by"> <XP>:t2
    => dict(frame="{1} is created by {2}",
            relation="CreatedBy", text1=t1, text2=t2)

| <text "There">:x1 <BE>:x2 <NP>:t1 <P>:x3 <NP>:t2
    => dict(frame=words(x1, x2, SLOT1, x3, SLOT2),
            relation="AtLocation", text1=t1, text2=t2)

| <NP>:t1 <BE>:x1 <PASV>:t2
    => dict(frame=words(SLOT1, x1, SLOT2),
            relation="ReceivesAction", text1=t1, text2=t2)

| (<text "You can"> | <text "Someone can"> | <text "People can">):x1
  <ADVP>:adv <V>:t1 <NP>:t2
    => dict(frame=words(x1, adv, SLOT1, SLOT2),
            relation="ReceivesAction", text1=t1, text2=t2, adv=adv)

| <NP>:t1 <BE>:x1 <ADVP>:adv <P>:x2 <NP>:t2
    => dict(frame=words(SLOT1, x1, adv, x2, SLOT2),
            relation="AtLocation", text1=t1, text2=t2, adv=adv)
| <NP>:t1 <BE>:x1 <ADVP>:adv <AP>:t2
    => dict(frame=words(SLOT1, x1, adv, SLOT2),
            relation="AtLocation", text1=t1, text2=t2, adv=adv)

| <NP>:t1 <ADVP>:adv (<text "has"> | <text "have">):x1 <NP>:t2
    => dict(frame=words(SLOT1, adv, x1, SLOT2),
            relation="HasA", text1=t1, text2=t2, adv=adv)

| <NP>:t1 <ADVP>:adv (<text "contain"> | <text "contains">):x1 <NP>:t2
    => dict(frame=words(SLOT1, adv, x1, SLOT2),
            relation="HasA", text1=t1, text2=t2, adv=adv)

| <NP>:t1 <BE>:x1 <ADVP>:adv <NP>:t2 <POST>
    => dict(frame=words(SLOT1, x1, adv, SLOT2),
            relation="IsA", text1=t1, text2=t2, adv=adv)

| <NP>:t1 <text "can">:x2 <ADVP>:adv <VP>:t2
    => dict(frame=words(SLOT1, x2, adv, t2),
            relation="CapableOf", text1=t1, text2=t2)

| <NP>:t1 (<text "ca n't"> | <text "cannot">):x2 <VP>:t2
    => dict(frame=words(SLOT1, x2, t2),
            relation="CapableOf", text1=t1, text2=t2, adv="not")

| <NP>:t1 <ADVP>:adv <VP>:t2
    => dict(frame=words(SLOT1, adv, SLOT2),
            relation="CapableOf", text1=t1, text2=t2, adv=adv)
)
"""

parser = PatternParserBase.makeGrammar(metapatterns, globals(), name="Metachunker")
def parse(tagged_sent):
    try:
        return parser(tagged_sent).apply("assertion")
    except ParseError:
        return None
print parser("ball_NN").apply("NN")
print parser("Sometimes_RB ball_NN causes_VBZ competition_NN").apply("assertion")
for sent in TaggedSentence.objects.all():
    print sent.text
    print "=>", parse(sent.text)

########NEW FILE########
__FILENAME__ = migrate_templated
#!/usr/bin/env python
import sys, traceback
from conceptnet4.models import Assertion, Batch, RawAssertion, Frame,\
  Frequency, Relation, SurfaceForm, Concept, Rating
import conceptnet.models as cn3
from corpus.models import Sentence, Language, Activity
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from corpus.parse.adverbs import map_adverb
from itertools import islice
import yaml

csamoa4_activity = Activity.objects.get(name='csamoa4 self-rating')
good_acts = [ 16, 20, 22, 24, 28, 31, 32 ]
en = Language.get('en')

def process_predicate(pred, batch):
    frametext = pred.frame.text
    matches = {1: pred.text1, 2: pred.text2}
    if pred.polarity < 0: matches['a'] = 'not'
    relation = pred.relation
    sentence = pred.sentence
    lang = pred.language

    surface_forms = [SurfaceForm.get(matches[i], lang, auto_create=True)
                     for i in (1, 2)]
    concepts = [s.concept for s in surface_forms]
    
    # FIXME: english only so far
    freq = map_adverb(matches.get('a', ''))
    relation = Relation.objects.get(id=relation.id)
    frame, _ = Frame.objects.get_or_create(relation=relation, language=lang,
                                           text=frametext,
                                           defaults=dict(frequency=freq, 
                                                         goodness=1))
    frame.save()
    
    raw_assertion, _ = RawAssertion.objects.get_or_create(
        surface1=surface_forms[0],
        surface2=surface_forms[1],
        frame=frame,
        language=lang,
        creator=sentence.creator,
        defaults=dict(batch=batch))
    # still need to set assertion_id
    
    assertion, _ = Assertion.objects.get_or_create(
        relation=relation,
        concept1=concepts[0],
        concept2=concepts[1],
        frequency=freq,
        language=lang,
        defaults=dict(score=0)
    )
    #assertion.save()
    
    raw_assertion.assertion = assertion
    raw_assertion.sentence = sentence
    raw_assertion.save()

    sentence.set_rating(sentence.creator, 1, csamoa4_activity)
    raw_assertion.set_rating(sentence.creator, 1, csamoa4_activity)
    assertion.set_rating(sentence.creator, 1, csamoa4_activity)

    for rating in pred.rating_set.all():
        score = rating.rating_value.deltascore
        if score < -1: score = -1
        if score > 1: score = 1
        if rating.activity_id is None:
            rating_activity = Activity.objects.get(name='unknown')
        else:
            rating_activity = rating.activity
        sentence.set_rating(rating.user, score, rating_activity)
        raw_assertion.set_rating(rating.user, score, rating_activity)
        assertion.set_rating(rating.user, score, rating_activity)

    print '=>', unicode(assertion).encode('utf-8')
    return [assertion]

def run(user, start_page=1):
    batch = Batch()
    batch.owner = user
    
    #generator = yaml.load_all(open('delayed_test.yaml'))
    #all_entries = list(generator)
    all_preds = []
    for actid in good_acts:
        all_preds.extend(cn3.Predicate.objects.filter(sentence__activity__id=actid, language=en))
    paginator = Paginator(all_preds,100)
    #pages = ((i,paginator.page(i)) for i in range(start_page,paginator.num_pages))

    @transaction.commit_on_success
    def do_batch(entries):
        for entry in entries:
            try:
                preds = process_predicate(entry, batch)
            # changed to an improbable exception for now
            except ZeroDivisionError, e:
                # Add entry
                e.entry = entry

                # Extract traceback
                e_type, e_value, e_tb = sys.exc_info()
                e.tb = "\n".join(traceback.format_exception( e_type, e_value, e_tb ))

                # Raise again
                raise e

    # Process entries
    page_range = [p for p in paginator.page_range if p >= start_page]
    for i in page_range:
        entries = paginator.page(i).object_list
        
        # Update progress
        batch.status = "process_entry_batch " + str(i) + "/" + str(paginator.num_pages)
        batch.progress_num = i
        batch.progress_den = paginator.num_pages
        batch.save()

        try: do_batch(entries)
        
        except ZeroDivisionError, e:
            batch.status = "process_entry_batch " + str(i) + "/" + str(paginator.num_pages) + " ERROR!"
            batch.remarks = str(e.entry) + "\n" + str(e) + "\n" + e.tb
            print "***TRACEBACK***"
            print batch.remarks
            batch.save()
            raise e

if __name__ == '__main__':
    user = User.objects.get(username='rspeer')
    run(user, start_page=164)


########NEW FILE########
__FILENAME__ = migrate_templated_qs4e
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csamoa
from conceptnet4.models import Assertion, Batch, RawAssertion, Frame,\
  Frequency, Relation, SurfaceForm, Concept
import conceptnet.models as cn3
from corpus.models import Sentence, Language, Activity
from django.contrib.auth.models import User
from itertools import islice
import yaml
from csc_utils import queryset_foreach

csamoa4_activity = Activity.objects.get(name='csamoa4 self-rating')
def process_predicate(pred):
    frametext = pred.frame.text
    relation = Relation.objects.get(id=pred.relation.id)
    sentence = pred.sentence
    lang = pred.language
    if pred.polarity < 0:
        freq, c = Frequency.objects.get_or_create(value=-5, language=lang,
        defaults=dict(text='[negative]'))
    else:
        freq, c = Frequency.objects.get_or_create(value=5, language=lang,
        defaults=dict(text=''))
    if c: freq.save()

    frame, c = Frame.objects.get_or_create(relation=relation, language=lang,
                                           text=frametext,
                                           defaults=dict(frequency=freq, 
                                                         goodness=1))
    if c: frame.save()
    raw_assertion = RawAssertion.make(sentence.creator, frame, pred.text1,
    pred.text2, csamoa4_activity, 1)
    assertion = raw_assertion.assertion
    
    for rating in pred.rating_set.all():
        score = rating.rating_value.deltascore
        if score < -1: score = -1
        if score > 1: score = 1
        if rating.activity_id is None:
            rating_activity = Activity.objects.get(name='unknown')
        else:
            rating_activity = rating.activity
        sentence.set_rating(rating.user, score, rating_activity)
        raw_assertion.set_rating(rating.user, score, rating_activity)
        assertion.set_rating(rating.user, score, rating_activity)
    return raw_assertion

def run():
    #generator = yaml.load_all(open('delayed_test.yaml'))
    #all_entries = list(generator)

    #activity_filter = Q()
    #for actid in good_acts:
    #    activity_filter |= Q(sentence__activity__id=actid)
    for lang in ['it', 'fr', 'nl', 'es', 'pt']:
        queryset_foreach(cn3.Predicate.objects.filter(language__id=lang),
        process_predicate, batch_size=10)

if __name__ == '__main__':
    run()


########NEW FILE########
__FILENAME__ = models
from django.db import models
from conceptnet.corpus.models import Language
from conceptnet.models import Relation

class FunctionFamilyDetector(object):
    def __init__(self,kb,language,family):
        self.language = language
        self.kb = kb
        self.family = family

    def __str__(self):
        return '<' + self.language.id + ': ' + \
                'function words (family=' + self.family + ')>'

    def __call__(self,word):
        return (word in self.kb)


class FunctionWord(models.Model):
    """ a word of particular significance to a parser """
    language = models.ForeignKey(Language)
    word = models.TextField()
    unique_together = (('language', 'word'),)

    def __str__(self):
        return "<" + self.language.id + ":" + self.word + ">"

    class Meta:
        db_table = 'functionwords'

class FunctionFamily(models.Model):
    """ defines a family of function words """
    family = models.TextField()
    f_word = models.ForeignKey(FunctionWord)
    unique_together = (('family', 'f_word'),)

    def __str__(self):
        return self.family + ": " + str(self.f_word)

    class Meta:
        db_table = 'functionfamilies'

    @staticmethod
    def build_function_detector(language, family):
        # Prepare the kb
        words = list(FunctionFamily.objects.filter(family=family,f_word__language=language).values_list('f_word__word', flat=True))

        return FunctionFamilyDetector(words,language,family)

class ParsingPattern(models.Model):
    pattern = models.TextField(blank=False)
    predtype = models.ForeignKey(Relation)
    polarity = models.IntegerField()
    sort_order = models.IntegerField()
    language = models.ForeignKey(Language)

    class Meta:
        db_table = 'parsing_patterns'


class SecondOrderPattern(models.Model):
    regex = models.TextField()
    language = models.ForeignKey(Language)
    use_group = models.IntegerField(default=0)
    abort = models.BooleanField(default=False)

    def __str__(self):
        return "(" + self.language.id + ") /" + self.regex + "/"

    def compile(self):
        self._compiled_regex = re.compile( self.regex )

    def __call__(self, text):
        if not hasattr( self, '_compiled_regex' ): self.compile()
        return self._compiled_regex.search(text)

    class Meta:
        db_table = 'secondorderpatterns'

    class SecondOrderSplitter:
        def __init__(self,patterns,language):
            self.language = language
            self.patterns = patterns

        def __call__(self,text):
                 # FIXME: THIS IS A HIDEOUSLY USELESS ROUTINE
            for pattern in self.patterns:
                m = pattern(text)
                if m:
                    if pattern.abort: text = ''
                    else: text = m.groups()[pattern.use_group]
            return [text]

        def __str__(self):
            return "Second order splitter (" + self.language.id + ")"

    @staticmethod
    def build_splitter(language):
        return SecondOrderPattern.SecondOrderSplitter(language.secondorderpattern_set.all(), language)

########NEW FILE########
__FILENAME__ = offline_parser
#!/usr/bin/env python
import sys, traceback
from pcfgpattern import pattern_parse
import yaml
from conceptnet.models import Sentence, Language
from django.core.paginator import Paginator
#from django.db import transaction

def process_sentence(sentence):
    print sentence.text.encode('utf-8')
    _, frametext, reltext, matches = pattern_parse(sentence.text)
    if reltext is None or reltext == 'junk': return []
    else:
        return [dict(id=sentence.id, frametext=frametext, reltext=reltext,
        matches=matches)]

def run(file, start_page=1, end_page=1000000):
    all_sentences = Sentence.objects.filter(language=Language.get('en')).order_by('id')
    paginator = Paginator(all_sentences,100)
    #pages = ((i,paginator.page(i)) for i in range(start_page,paginator.num_pages))

    def do_batch(sentences):
        preds = []
        for sentence in sentences:
            try:
                preds.extend(process_sentence(sentence))
            # changed to an improbable exception for now
            except Exception, e:
                # Add sentence
                e.sentence = sentence

                # Extract traceback
                e_type, e_value, e_tb = sys.exc_info()
                e.tb = "\n".join(traceback.format_exception( e_type, e_value, e_tb ))

                # Raise again
                raise e
        file.write('\n--- ')
        yaml.dump_all(preds, file)

    # Process sentences
    page_range = [p for p in paginator.page_range if p >= start_page and p <
    end_page]
    for i in page_range:
        sentences = paginator.page(i).object_list
        do_batch(sentences)


if __name__ == '__main__':
    start_page = int(sys.argv[1])
    end_page = int(sys.argv[2])
    out = open(sys.argv[3], 'w+')
    run(out, start_page, end_page)


########NEW FILE########
__FILENAME__ = pcfgpattern
import nltk
from collections import defaultdict
from nltk.cfg import Nonterminal
from divisi.util import get_picklecached_thing
from conceptnet.corpus.models import Pattern, Sentence, Language
from simplenlp.euro import tokenize, untokenize
from nltk.corpus.reader import BracketParseCorpusReader
from nltk.corpus.util import LazyCorpusLoader
import string

treebank_brown = LazyCorpusLoader(
    'treebank/combined', BracketParseCorpusReader, r'c.*\.mrg')
#treebank_brown = None

en = Language.get('en')

# Patterns are 4-tuples of:
# (relative probability, predtype, polarity, expression)

patterns = [
(1.0, 'HasFirstSubevent', 'the first thing you do when you {VP:1} is {VP:2}'),
(1.0, 'HasLastSubevent', 'the last thing you do when you {VP:1} is {VP:2}'),
(1.0, 'HasPrerequisite', 'something you need to do before you {VP:1} is {VP:2}'),
(1.0, 'MadeOf', '{NP:1} {BE} {ADVP:a} made of {NP:2}'),
(1.0, 'IsA', '{NP:1} {BE} a kind of {NP:2} {POST:0}'),
(1.0, 'IsA', '{NP:1} {BE} a sort of {NP:2} {POST:0}'),
(1.0, 'IsA', '{NP:1} {BE} a type of {NP:2} {POST:0}'),
(1.0, 'AtLocation', 'somewhere {NP:1} can be is {P} {NP:2}'),
(1.0, 'AtLocation', 'somewhere {NP:1} can be is {NP:2}'),
(1.0, 'AtLocation', 'you are likely to find {NP:1} {P} {NP:2}'),
(0.1, 'AtLocation', '{NP:1} can be {P} {NP:2}'),
(1.0, 'UsedFor', '{NP:1} {BE} used for {NP:2}'),
(1.0, 'UsedFor', '{NP:1} {BE} used to {VP:2}'),
(1.0, 'CapableOf', '{NP:1} {BE} capable of {NP:2}'),
(1.0, 'CapableOf', 'an activity {NP:1} can do is {VP:2}'),
(1.0, 'CapableOf', 'an activity {NP:1} can do is {NP:2}'),
(1.0, 'MotivatedByGoal', 'you would {VP:1} because you want to {VP:2}'),
(1.0, 'MotivatedByGoal', 'you would {VP:1} because you want {NP:2}'),
(1.0, 'MotivatedByGoal', 'you would {VP:1} because {S:2}'),
(1.0, 'Desires', '{NP:1} {ADVP:a} wants to {VP:2}'),
(1.0, 'Desires', '{NP:1} {ADVP:a} wants {NP:2}'),
(1.0, 'Desires', '{NP:1} {ADVP:a} want to {VP:2}'),
(1.0, 'Desires', '{NP:1} {ADVP:a} want {NP:2}'),
(1.0, 'Desires', '{NP:1} {ADVP:a} likes to {VP:2}'),
(1.0, 'Desires', '{NP:1} {ADVP:a} like to {VP:2}'),
(1.0, 'DefinedAs', '{NP:1} {BE} defined as {NP:2}'),
(0.1, 'DefinedAs', '{NP:1} {BE} the {NP:2}'),
(0.1, 'DefinedAs', '{NP:2} {BE} called {NP:1}'),
(1.0, 'DefinedAs', 'the common name for {NP:2} is {NP:1}'),
(1.0, 'SymbolOf', '{NP:1} {BE} {DT} symbol of {NP:2}'),
(1.0, 'CausesDesire', '{NP:1} would make you want to {VP:2}'),
(1.0, 'Causes', 'the effect of {XP:1} is that {S:2}'),
(1.0, 'Causes', 'the effect of {XP:1} is {NP:2}'),
(1.0, 'Causes', 'the consequence of {XP:1} is that {XP:2}'),
(1.0, 'Causes', 'something that might happen as a consequence of {XP:1} is that {XP:2}'),
(1.0, 'Causes', 'something that might happen as a consequence of {XP:1} is {XP:2}'),
(1.0, 'Causes', '{ADVP:a} {NP:1} causes you to {VP:2}'),
(1.0, 'Causes', '{ADVP:a} {NP:1} causes {NP:2}'),
(1.0, 'HasSubevent', 'one of the things you do when you {VP:1} is {XP:2}'),
(1.0, 'HasSubevent', 'something that might happen when you {VP:1} is {XP:2}'),
(1.0, 'HasSubevent', 'something that might happen while {XP:1} is {XP:2}'),
(1.0, 'HasSubevent', 'something you might do while {XP:1} is {XP:2}'),
(1.0, 'HasSubevent', 'to {VP:1} you must {VP:2}'),
(0.8, 'HasSubevent', 'when you {VP:1} you {VP:2}'),
(1.0, 'HasSubevent', 'when you {VP:1} , you {VP:2}'),
(0.5, 'HasSubevent', 'when {S:1} , {S:2}'),
(0.1, 'ReceivesAction', '{NP:1} {BE} {PASV:2}'),
(1.0, 'PartOf', '{NP:1} {BE} part of {NP:2}'),
(1.0, 'CreatedBy', 'you make {NP:1} by {NP:2}'),
(1.0, 'CreatedBy', '{NP:1} {BE} created by {NP:2}'),
(1.0, 'CreatedBy', '{NP:1} {BE} made by {NP:2}'),
(1.0, 'CreatedBy', '{NP:1} {BE} created with {NP:2}'),
(1.0, 'CreatedBy', '{NP:1} {BE} made with {NP:2}'),
(1.0, 'CapableOf', "{NP:1} ca {n't:a} {VP:2}"),
(0.01, 'CapableOf', '{NP:1} can {ADVP2:a} {VP:2}'),
(0.001, 'CapableOf', '{NP:1} {ADVP1:a} {VP:2}'),
(1.0, 'UsedFor', 'you can use {NP:1} to {VP:2}'),
(1.0, 'AtLocation', 'something you might find {P} {NP:2} is {NP:1}'),
(1.0, 'AtLocation', 'something you find {P} {NP:2} is {NP:1}'),
(0.1, 'AtLocation', 'there are {NP:1} {P} {NP:2}'),
(1.0, 'HasA', '{NP:1} {ADVP:a} {HAVE} {NP:2}'),
(1.0, 'HasPrerequisite', '{NP:1} requires {NP:2}'),
(1.0, 'HasPrerequisite', 'if you want to {VP:1} then you should {VP:2}'),
(1.0, 'HasPrerequisite', '{VP:1} requires that you {VP:2}'),
(0.002, 'IsA', '{NP:1} {BE} {ADVP:a} {NP:2} {POST:0}'),
(0.02, 'IsA', 'to {VP:1} {BE} to {VP:2}'),
(0.3, 'HasProperty', '{NP:1} {BE} {ADVP:a} {AP:2}'),
(1.0, 'UsedFor', 'people use {NP:1} to {VP:2}'),
(1.0, 'UsedFor', '{NP:1} is for {XP:2}'),
(1.0, 'UsedFor', '{VP:1} is for {XP:2}'),
(1.0, 'junk', 'picture description : {XP:1}'),
(0.001, 'junk', '{NP:1}'),
(1.0, 'junk', 'things that are often found together are : {NP:1}'),
(1.0, 'junk', 'When you {VP:1} you do the following : 1'),
]

def defaultunigram(smoothing):
    x = defaultdict(int)
    x['NN'] = smoothing * 0.9
    x['VB'] = smoothing * 0.1
    return x

def get_lexicon(filename='LEXICON.BROWN.AND.WSJ'):
    f = open(filename)
    for line in f:
        parts = line.strip().split()
        if not parts: continue
        word = parts[0].lower()
        for tag in parts[1:]:
            # Pretend adverbs are a closed class. Otherwise lots of things
            # can inadvertently be adverbs.
            yield word, tag


class UnigramProbDist(object):
    def __init__(self, smoothing=0.01):
        self.counts = defaultdict(int)
        self.probs = defaultdict(lambda: defaultunigram(smoothing))
        self.smoothing = smoothing
        self.total = 0.0
    def inc(self, word, tag, closed_class=True):
        if word not in self.counts: self.total += self.smoothing
        if closed_class and tag in ['RB', 'MD', 'DO']: return
        self.probs[word][tag] += 1
        self.counts[word] += 1
        self.total += 1
    def probabilities(self, word):
        #count = float(self.counts[word]) + self.smoothing
        count = self.total
        if word != "'s":
            for tag, n in self.probs[word].items():
                yield tag, n/count
        else:
            yield "POS", 5000.0/count
    
    @classmethod
    def from_treebank(klass):
        from nltk.corpus import brown, treebank
        probdist = klass()
        for sent in treebank.tagged_sents():
            for word, tag in sent:
                probdist.inc(word.lower(), tag)
        for sent in treebank_brown.tagged_sents():
            for word, tag in sent:
                probdist.inc(word.lower(), tag)
        for word, tag in get_lexicon():
            probdist.inc(word, tag, closed_class=False)
        for i in range(10): probdist.inc('can', 'VB')
        return probdist

def match_production(rhs, start, chart, tokens=None):
    if len(rhs) == 0:
        yield start, 1.0
        return
    symb = str(rhs[0])
    group = None
    if symb[0] == "{":
        parts = symb[1:-1].split(':')
        symb = parts[0]
        if len(parts) > 1: group = parts[1]
    for next, prob in chart[symb][start].items():
        for end, prob2 in match_production(rhs[1:], next, chart):
            yield end, prob*prob2

def match_pattern(rhs, start, chart, tokens):
    if len(rhs) == 0:
        yield start, 1.0, [], {}
        return
    symb = str(rhs[0])
    group = None
    if symb[0] == "{":
        parts = symb[1:-1].split(':')
        symb = parts[0]
        if len(parts) > 1: group = parts[1]
    for next, prob in chart[symb][start].items():
        for end, prob2, frame, matchdict in match_pattern(rhs[1:], next, chart, tokens):
            if group is not None:
                if group in string.digits:    
                    chunk = ["{%s}" % group]
                    groupn = int(group)
                    if groupn == 0: chunk = []
                else:
                    chunk = tokens[start:next]
                    groupn = group
                matchdict[groupn] = untokenize(' '.join(tokens[start:next]))
            else: chunk = tokens[start:next]
            yield end, prob*prob2, chunk + frame, matchdict

def pattern_chart(tokens, grammar, unigrams, trace=0):
    # chart :: symbol -> start -> end -> prob
    chart = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    for i, token in enumerate(tokens):
        token = token.lower()
        chart[token][i][i+1] = 1.0
        if trace > 0:
            print "%s\t%s\t%s" % (token, (i, i+1), 1.0)
        for tag, prob in unigrams.probabilities(token):
            if tag == "''" or tag == "``": tag = "QUOT"
            if tag == 'PRP$': tag = "PRPp"
            chart[tag][i][i+1] = prob
            if trace > 0:
                print "%s\t%s\t%s" % (tag, (i, i+1), prob)
    
    changed = True
    while changed:
        changed = False
        for prod in grammar.productions():
            lhs = str(prod.lhs())
            for start in range(len(tokens)+1):
                for end, prob in match_production(prod.rhs(), start, chart):
                    p = prob * prod.prob()
                    if p > 1e-55 and p > chart[lhs][start][end]:
                        changed = True
                        chart[lhs][start][end] = p
                        if trace > 0:
                            print "%s\t%s\t%s" % (lhs, (start, end), p)
    return chart

thegrammar = nltk.data.load('file:patterns.pcfg')
theunigrams = UnigramProbDist.from_treebank()

def pattern_parse(sentence, trace=0):
    tokens = tokenize(sentence.split(". ")[0].strip("?!.")).split()
    chart = pattern_chart(tokens, thegrammar, theunigrams, trace)
    
    bestprob = 1e-60
    bestframe = None
    bestrel = None
    bestmatches = None
    for pprob, rel, pattern in patterns:
        ptok = pattern.split()
        for end, prob, frame, matchdict in match_pattern(ptok, 0, chart, tokens):
            prob *= pprob
            if end == len(tokens):
                if trace > 0:
                    print prob, pattern
                if prob > bestprob:
                    bestprob = prob
                    bestframe = untokenize(' '.join(frame))
                    bestrel = rel
                    bestmatches = matchdict
        #if bestpattern is not None: break
    return bestprob, bestframe, bestrel, bestmatches

def run_all():
    for sent in Sentence.objects.filter(language=en).order_by('id'):
        if (sentence.text.startswith('Situation:')
            or sentence.text.startswith('The statement')
            or sentence.text.startswith('To understand')
            or sentence.text.startswith('In the event')):
                print "* skipped *"
                continue
        print sent.text
        _, frame, rel, matches = pattern_parse(sent.text)
        print frame
        print rel, matches

if __name__ == '__main__': run_all()

########NEW FILE########
__FILENAME__ = run_parser
#!/usr/bin/env python
import sys, traceback
from conceptnet.models import Assertion, Batch, RawAssertion, Frame,\
  Frequency, Relation, SurfaceForm, Concept, Rating
from conceptnet.corpus.models import Sentence, Language, Activity
from django.contrib.auth.models import User
from pcfgpattern import pattern_parse
from django.core.paginator import Paginator
from django.db import transaction

csamoa4_activity = Activity.objects.get(name='csamoa4 self-rating')

def process_sentence_delayed(entry, lang, batch):
    frametext, id, matches, reltext = (entry['frametext'], entry['id'],
    entry['matches'], entry['reltext'])
    sentence = Sentence.objects.get(id=id)
    print sentence.text.encode('utf-8')
    
    if reltext is None or reltext == 'junk': return []
    relation = Relation.objects.get(name=reltext)
    text_factors = [lang.nl.lemma_factor(matches[i]) for i in (1, 2)]
    concepts = [Concept.objects.get_or_create(language=lang, text=stem)[0]
                for stem, residue in text_factors]
    for c in concepts: c.save()
    
    surface_forms = [SurfaceForm.objects.get_or_create(concept=concepts[i],
                                                  text=matches[i+1],
                                                  residue=text_factors[i][1],
                                                  language=lang)[0]
                     for i in (0, 1)]
    for s in surface_forms: s.save()
    
    freq, _ = Frequency.objects.get_or_create(text=matches.get('a', ''),
                                              language=lang,
                                              defaults=dict(value=50))
    freq.save()
    
    frame, _ = Frame.objects.get_or_create(relation=relation, language=lang,
                                           text=frametext, frequency=freq,
                                           defaults=dict(goodness=1))
    frame.save()
    
    raw_assertion, _ = RawAssertion.objects.get_or_create(
        surface1=surface_forms[0],
        surface2=surface_forms[1],
        frame=frame,
        language=lang,
        defaults=dict(batch=batch))
    # still need to set assertion_id
    
    assertion, _ = Assertion.objects.get_or_create(
        relation=relation,
        concept1=concepts[0],
        concept2=concepts[1],
        frequency=freq,
        language=lang,
        defaults=dict(score=0)
    )
    assertion.score += 1
    assertion.save()
    raw_assertion.assertion = assertion
    raw_assertion.save()
    
    rating1, _ = Rating.objects.get_or_create(
        user=sentence.creator, activity=csamoa4_activity,
        sentence=sentence, score=1
    )
    rating2, _ = Rating.objects.get_or_create(
        user=sentence.creator, activity=csamoa4_activity,
        raw_assertion=raw_assertion, score=1
    )
    rating1.save()
    rating2.save()

    print '=>', str(assertion).encode('utf-8')
    return [assertion]

def process_sentence(sentence, lang, batch):
    print sentence.text.encode('utf-8')
    _, frametext, reltext, matches = pattern_parse(sentence.text)
    
    if reltext is None or reltext == 'junk': return []
    relation = Relation.objects.get(name=reltext)
    text_factors = [lang.nl.lemma_factor(matches[i]) for i in (1, 2)]
    concepts = [Concept.objects.get_or_create(language=lang, text=stem)[0]
                for stem, residue in text_factors]
    for c in concepts: c.save()
    
    surface_forms = [SurfaceForm.objects.get_or_create(concept=concepts[i],
                                                  text=matches[i+1],
                                                  residue=text_factors[i][1],
                                                  language=lang)[0]
                     for i in (0, 1)]
    for s in surface_forms: s.save()
    
    freq, _ = Frequency.objects.get_or_create(text=matches.get('a', ''),
                                              language=lang,
                                              defaults=dict(value=50))
    freq.save()
    
    frame, _ = Frame.objects.get_or_create(relation=relation, language=lang,
                                           text=frametext, frequency=freq,
                                           defaults=dict(goodness=1))
    frame.save()
    
    raw_assertion, _ = RawAssertion.objects.get_or_create(
        surface1=surface_forms[0],
        surface2=surface_forms[1],
        frame=frame,
        language=lang,
        defaults=dict(batch=batch))
    # still need to set assertion_id
    
    assertion, _ = Assertion.objects.get_or_create(
        relation=relation,
        concept1=concepts[0],
        concept2=concepts[1],
        frequency=freq,
        language=lang,
        defaults=dict(score=0)
    )
    assertion.score += 1
    assertion.save()
    raw_assertion.assertion = assertion
    raw_assertion.save()
    
    rating1, _ = Rating.objects.get_or_create(
        user=sentence.creator, activity=csamoa4_activity,
        sentence=sentence, score=1
    )
    rating2, _ = Rating.objects.get_or_create(
        user=sentence.creator, activity=csamoa4_activity,
        raw_assertion=raw_assertion, score=1
    )
    rating1.save()
    rating2.save()

    print '=>', str(assertion).encode('utf-8')
    return [assertion]

def run(user, lang, start_page=1):
    batch = Batch()
    batch.owner = user
    
    all_sentences = Sentence.objects.filter(language=lang).order_by('id')
    paginator = Paginator(all_sentences,10)
    #pages = ((i,paginator.page(i)) for i in range(start_page,paginator.num_pages))

    @transaction.commit_on_success
    def do_batch(sentences):
        for sentence in sentences:
            try:
                preds = process_sentence(sentence, lang, batch)
            # changed to an improbable exception for now
            except Exception, e:
                # Add sentence
                e.sentence = sentence

                # Extract traceback
                e_type, e_value, e_tb = sys.exc_info()
                e.tb = "\n".join(traceback.format_exception( e_type, e_value, e_tb ))

                # Raise again
                raise e

    # Process sentences
    page_range = [p for p in paginator.page_range if p >= start_page]
    for i in page_range:
        sentences = paginator.page(i).object_list
        
        # Update progress
        batch.status = "process_sentence_batch " + str(i) + "/" + str(paginator.num_pages)
        batch.progress_num = i
        batch.progress_den = paginator.num_pages
        batch.save()

        try: do_batch(sentences)
        
        except Exception, e: #improbable exception for now
            batch.status = "process_sentence_batch " + str(i) + "/" + str(paginator.num_pages) + " ERROR!"
            batch.remarks = str(e.sentence) + "\n" + str(e) + "\n" + e.tb
            print "***TRACEBACK***"
            print batch.remarks
            batch.save()
            raise e


if __name__ == '__main__':
    user = User.objects.get(username='rspeer')
    lang = Language.get('en')
    run(user, lang, start_page=50000)


########NEW FILE########
__FILENAME__ = try_patterns
#!/usr/bin/env python
from conceptnet.corpus.parse.pcfgpattern import *
__test__ = False

def textrepr(rel, matchdict):
    if rel is None: return 'None'
    return "%s(%s, %s)" % (rel, matchdict.get(1), matchdict.get(2))

# A selection of sentences from OMCS that we should be able to parse correctly.
# This test suite does not vouch for the correctness or usefulness of the
# sentences it contains.

tests = [
    ("If you want to impanel a jury then you should ask questions.",
     "HasPrerequisite(impanel a jury, ask questions)"),
    ('"Lucy in the Sky with Diamonds" was a famous Beatles song',
     'IsA("Lucy in the Sky with Diamonds", a famous Beatles song)'),
    ("sound can be recorded",
     "ReceivesAction(sound, recorded)"),
    ("sounds can be soothing",
     "HasProperty(sounds, soothing)"),
    ("music can be recorded with a recording device",
     "ReceivesAction(music, recorded with a recording device)"),
    ("The first thing you do when you buy a shirt is try it on",
     "HasFirstSubevent(buy a shirt, try it on)"),
    ("One of the things you do when you water a plant is pour",
     "HasSubevent(water a plant, pour)"),
    ("A small sister can bug an older brother",
     "CapableOf(A small sister, bug an older brother)"),
    ("McDonald's hamburgers contain mayonnaise",
     "HasA(McDonald's hamburgers, mayonnaise)"),
    ("If you want to stab to death then you should get a knife.",
     "HasPrerequisite(stab to death, get a knife)"),
    ("carbon can cake hard",
     "CapableOf(carbon, cake hard)"),
    ("You would take a walk because your housemates were having sex in your bed.",
     "MotivatedByGoal(take a walk, your housemates were having sex in your bed)"),
    ("police can tail a suspect",
     "CapableOf(police, tail a suspect)"),
    ("people can race horses",
     "CapableOf(people, race horses)"),
    ("computer can mine data",
     "CapableOf(computer, mine data)"),
    ("to use a phone you must dial numbers",
     "HasSubevent(use a phone, dial numbers)"),
    ("People who are depressed are more likely to kill themselves",
     "HasProperty(People who are depressed, more likely to kill themselves)"),
    ("Bird eggs are good with toast and jam",
     "HasProperty(Bird eggs, good with toast and jam)"),
    ("housewife can can fruit",
     "CapableOf(housewife, can fruit)"),
    ("pictures can be showing nudity",
     "CapableOf(pictures, be showing nudity)"),
    ("a large house where the president of the US resides",
     "junk(a large house where the president of the US resides, None)"),
    ("girls are cute when they eat",
     "HasProperty(girls, cute when they eat)"),
    ("When books are on a bookshelf, you see only their spines.",
     "HasSubevent(books are on a bookshelf, you see only their spines)"),
    ("The effect of taking a phone call is finding out who is calling",
     "Causes(taking a phone call, finding out who is calling)"),
    ("There are 60 seconds in a minute",
     "AtLocation(60 seconds, a minute)"),
    ("Two wrongs don't make a right.",
     "CapableOf(Two wrongs, make a right)"),
    ("Somewhere someone can be is an art gallery",
     "AtLocation(someone, an art gallery)"),
    ("A person doesn't want war",
     "Desires(A person, war)"),
    ("That's weird",
     "junk(That's weird, None)"),
]

def run_tests():
    success = 0
    ntests = 0
    for testin, testout in tests:
        ntests += 1
        prob, frame, rel, matches = pattern_parse(testin)
        if textrepr(rel, matches) == testout:
            success += 1
            print "Success:", testin
        else:
            print "Failed:", testin
            print "Got:", textrepr(rel, matches)
            print "Expected:", testout
            pattern_parse(testin, 1)
            
    print "Tests complete: %d/%d" % (success, ntests)

run_tests.__test__ = False

if __name__ == '__main__':
    run_tests()


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = db_downloader
import urllib, os, sys
import tarfile
SQLITE_URL = "http://conceptnet.media.mit.edu/dist/ConceptNet-sqlite.tar.gz"

def prompt_for_download(filename):
    print """
You don't seem to have the ConceptNet database installed. (If you do,
I couldn't find the db_config.py file that says where it is.)

If you want, I can download the current database for you and save it as:
"""
    print '\t'+filename
    print
    print "This will be a large download -- around 450 megabytes."
    response = raw_input("Do you want to download the database? [Y/n] ")
    if response == '' or response.lower().startswith('y'):
        return download(SQLITE_URL, filename)
    else:
        print """
Not downloading the database.
The program will have to exit now. For information on setting up ConceptNet,
go to: http://csc.media.mit.edu/docs/conceptnet/install.html
"""
        return False

def _mkdir(newdir):
    """
    http://code.activestate.com/recipes/82465/
    
    works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("A file with the same name as the desired " \
                      "directory, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            _mkdir(head)
        if tail:
            os.mkdir(newdir)


def download(rem_filename, dest_filename):
    dir = os.path.dirname(dest_filename)
    member = os.path.basename(dest_filename)
    _mkdir(dir)
    tar_filename = dir + os.path.sep + 'ConceptNet-sqlite.tar.gz'
    def dlProgress(count, blockSize, totalSize):
        percent = int(count*blockSize*100/totalSize)
        sys.stdout.write("\r" + rem_filename + "... %2d%%" % percent)
        sys.stdout.flush()
    urllib.urlretrieve(rem_filename, tar_filename, reporthook=dlProgress)
    tar_obj = tarfile.open(tar_filename)
    print
    print "Extracting."
    tar_obj.extract(member, path=dir)
    return True



########NEW FILE########
__FILENAME__ = default_db_config
import os

# Don't use a "dot" directory on Windows. It might make Windows sad.
if os.name == 'nt':
    user_data_dir = os.path.expanduser('~/conceptnet/')
else:
    user_data_dir = os.path.expanduser('~/.conceptnet/')

DB_ENGINE = "sqlite3"
DB_NAME = user_data_dir + "ConceptNet.db"
DB_HOST = ""
DB_PORT = ""
DB_USER = ""
DB_PASSWORD = ""
DB_SCHEMAS = ""

DEBUG = True
SERVE_API = True

########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from events.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'Event'
        db.create_table('events_event', (
            ('id', orm['events.Event:id']),
            ('user', orm['events.Event:user']),
            ('content_type', orm['events.Event:content_type']),
            ('object_id', orm['events.Event:object_id']),
            ('activity', orm['events.Event:activity']),
            ('timestamp', orm['events.Event:timestamp']),
        ))
        db.send_create_signal('events', ['Event'])
        
        # Adding model 'Activity'
        db.create_table('events_activity', (
            ('id', orm['events.Activity:id']),
            ('name', orm['events.Activity:name']),
        ))
        db.send_create_signal('events', ['Activity'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'Event'
        db.delete_table('events_event')
        
        # Deleting model 'Activity'
        db.delete_table('events_activity')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'events.activity': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {})
        },
        'events.event': {
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['events.Activity']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }
    
    complete_apps = ['events']

########NEW FILE########
__FILENAME__ = models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.db import models
from datetime import datetime

class Activity(models.Model):
    name = models.TextField()
    def __unicode__(self):
        return self.name
    
    @staticmethod
    def get(name):
        activity, created = Activity.objects.get_or_create(name=name)
        return activity

    class Meta:
        verbose_name_plural = 'Activities'

class Event(models.Model):
    """
    Indicates that an object was created or possibly modified by an Activity.
    """
    user         = models.ForeignKey(User)
    content_type = models.ForeignKey(ContentType)
    object_id    = models.PositiveIntegerField()
    object       = generic.GenericForeignKey('content_type', 'object_id')
    activity     = models.ForeignKey(Activity)
    timestamp    = models.DateTimeField(default=datetime.now)

    @classmethod
    def record_event(cls, obj, user, activity):
        ctype = ContentType.objects.get_for_model(obj)
        event = cls.objects.create(user=user, content_type=ctype,
                           object_id=obj._get_pk_val(),
                           activity=activity)
        return event

    def __unicode__(self):
        return u'%s: %r/%r/%r' % (self.timestamp, self.user, self.object, self.activity)
    
    class Meta:
        ordering = ['-timestamp']

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from voting.models import Vote

admin.site.register(Vote)

########NEW FILE########
__FILENAME__ = managers
from django.conf import settings
from django.db import connection, models

try:
    from django.db.models.sql.aggregates import Aggregate
except ImportError:
    supports_aggregates = False
else:
    supports_aggregates = True

from django.contrib.contenttypes.models import ContentType

if supports_aggregates:
    class CoalesceWrapper(Aggregate):
        sql_template = 'COALESCE(%(function)s(%(field)s), %(default)s)'
    
        def __init__(self, lookup, **extra): 
            self.lookup = lookup
            self.extra = extra
    
        def _default_alias(self):
            return '%s__%s' % (self.lookup, self.__class__.__name__.lower())
        default_alias = property(_default_alias)
    
        def add_to_query(self, query, alias, col, source, is_summary):
            super(CoalesceWrapper, self).__init__(col, source, is_summary, **self.extra)
            query.aggregate_select[alias] = self


    class CoalesceSum(CoalesceWrapper):
        sql_function = 'SUM'


    class CoalesceCount(CoalesceWrapper):
        sql_function = 'COUNT'


class VoteManager(models.Manager):
    def get_score(self, obj):
        """
        Get a dictionary containing the total score for ``obj`` and
        the number of votes it's received.
        """
        ctype = ContentType.objects.get_for_model(obj)
        result = self.filter(object_id=obj._get_pk_val(),
                             content_type=ctype).extra(
            select={
                'score': 'COALESCE(SUM(vote), 0)',
                'num_votes': 'COALESCE(COUNT(vote), 0)',
        }).values_list('score', 'num_votes')[0]

        return {
            'score': int(result[0]),
            'num_votes': int(result[1]),
        }

    def get_scores_in_bulk(self, objects):
        """
        Get a dictionary mapping object ids to total score and number
        of votes for each object.
        """
        object_ids = [o._get_pk_val() for o in objects]
        if not object_ids:
            return {}
        
        ctype = ContentType.objects.get_for_model(objects[0])
        
        if supports_aggregates:
            queryset = self.filter(
                object_id__in = object_ids,
                content_type = ctype,
            ).values(
                'object_id',
            ).annotate(
                score = CoalesceSum('vote', default='0'),
                num_votes = CoalesceCount('vote', default='0'),
            )
        else:
            queryset = self.filter(
                object_id__in = object_ids,
                content_type = ctype,
                ).extra(
                    select = {
                        'score': 'COALESCE(SUM(vote), 0)',
                        'num_votes': 'COALESCE(COUNT(vote), 0)',
                    }
                ).values('object_id', 'score', 'num_votes')
            queryset.query.group_by.append('object_id')
        
        vote_dict = {}
        for row in queryset:
            vote_dict[row['object_id']] = {
                'score': int(row['score']),
                'num_votes': int(row['num_votes']),
            }
        
        return vote_dict

    def record_vote(self, obj, user, vote):
        """
        Record a user's vote on a given object. Only allows a given user
        to vote once, though that vote may be changed.

        A zero vote indicates that any existing vote should be removed.
        """
        if vote not in (+1, 0, -1):
            raise ValueError('Invalid vote (must be +1/0/-1)')
        ctype = ContentType.objects.get_for_model(obj)
        try:
            v = self.get(user=user, content_type=ctype,
                         object_id=obj._get_pk_val())
            if vote == 0:
                v.delete()
            else:
                v.vote = vote
                v.save()
        except models.ObjectDoesNotExist:
            if vote != 0:
                self.create(user=user, content_type=ctype,
                            object_id=obj._get_pk_val(), vote=vote)

    def get_top(self, Model, limit=10, reversed=False):
        """
        Get the top N scored objects for a given model.

        Yields (object, score) tuples.
        """
        ctype = ContentType.objects.get_for_model(Model)
        query = """
        SELECT object_id, SUM(vote) as %s
        FROM %s
        WHERE content_type_id = %%s
        GROUP BY object_id""" % (
            connection.ops.quote_name('score'),
            connection.ops.quote_name(self.model._meta.db_table),
        )

        # MySQL has issues with re-using the aggregate function in the
        # HAVING clause, so we alias the score and use this alias for
        # its benefit.
        if settings.DATABASE_ENGINE == 'mysql':
            having_score = connection.ops.quote_name('score')
        else:
            having_score = 'SUM(vote)'
        if reversed:
            having_sql = ' HAVING %(having_score)s < 0 ORDER BY %(having_score)s ASC LIMIT %%s'
        else:
            having_sql = ' HAVING %(having_score)s > 0 ORDER BY %(having_score)s DESC LIMIT %%s'
        query += having_sql % {
            'having_score': having_score,
        }

        cursor = connection.cursor()
        cursor.execute(query, [ctype.id, limit])
        results = cursor.fetchall()

        # Use in_bulk() to avoid O(limit) db hits.
        objects = Model.objects.in_bulk([id for id, score in results])

        # Yield each object, score pair. Because of the lazy nature of generic
        # relations, missing objects are silently ignored.
        for id, score in results:
            if id in objects:
                yield objects[id], int(score)

    def get_bottom(self, Model, limit=10):
        """
        Get the bottom (i.e. most negative) N scored objects for a given
        model.

        Yields (object, score) tuples.
        """
        return self.get_top(Model, limit, True)

    def get_for_user(self, obj, user):
        """
        Get the vote made on the given object by the given user, or
        ``None`` if no matching vote exists.
        """
        if not user.is_authenticated():
            return None
        ctype = ContentType.objects.get_for_model(obj)
        try:
            vote = self.get(content_type=ctype, object_id=obj._get_pk_val(),
                            user=user)
        except models.ObjectDoesNotExist:
            vote = None
        return vote

    def get_for_user_in_bulk(self, objects, user):
        """
        Get a dictionary mapping object ids to votes made by the given
        user on the corresponding objects.
        """
        vote_dict = {}
        if len(objects) > 0:
            ctype = ContentType.objects.get_for_model(objects[0])
            votes = list(self.filter(content_type__pk=ctype.id,
                                     object_id__in=[obj._get_pk_val() \
                                                    for obj in objects],
                                     user__pk=user.id))
            vote_dict = dict([(vote.object_id, vote) for vote in votes])
        return vote_dict

########NEW FILE########
__FILENAME__ = models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.db import models

from voting.managers import VoteManager

SCORES = (
    (u'+1', +1),
    (u'-1', -1),
)

class Vote(models.Model):
    """
    A vote on an object by a User.
    """
    user         = models.ForeignKey(User)
    content_type = models.ForeignKey(ContentType)
    object_id    = models.PositiveIntegerField()
    object       = generic.GenericForeignKey('content_type', 'object_id')
    vote         = models.SmallIntegerField(choices=SCORES)

    objects = VoteManager()

    class Meta:
        db_table = 'votes'
        # One vote per user per object
        unique_together = (('user', 'content_type', 'object_id'),)

    def __unicode__(self):
        return u'%s: %s on %s' % (self.user, self.vote, self.object)

    def is_upvote(self):
        return self.vote == 1

    def is_downvote(self):
        return self.vote == -1

########NEW FILE########
__FILENAME__ = voting_tags
from django import template
from django.utils.html import escape

from voting.models import Vote

register = template.Library()

# Tags

class ScoreForObjectNode(template.Node):
    def __init__(self, object, context_var):
        self.object = object
        self.context_var = context_var

    def render(self, context):
        try:
            object = template.resolve_variable(self.object, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_score(object)
        return ''

class ScoresForObjectsNode(template.Node):
    def __init__(self, objects, context_var):
        self.objects = objects
        self.context_var = context_var

    def render(self, context):
        try:
            objects = template.resolve_variable(self.objects, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_scores_in_bulk(objects)
        return ''

class VoteByUserNode(template.Node):
    def __init__(self, user, object, context_var):
        self.user = user
        self.object = object
        self.context_var = context_var

    def render(self, context):
        try:
            user = template.resolve_variable(self.user, context)
            object = template.resolve_variable(self.object, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_for_user(object, user)
        return ''

class VotesByUserNode(template.Node):
    def __init__(self, user, objects, context_var):
        self.user = user
        self.objects = objects
        self.context_var = context_var

    def render(self, context):
        try:
            user = template.resolve_variable(self.user, context)
            objects = template.resolve_variable(self.objects, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = Vote.objects.get_for_user_in_bulk(objects, user)
        return ''

class DictEntryForItemNode(template.Node):
    def __init__(self, item, dictionary, context_var):
        self.item = item
        self.dictionary = dictionary
        self.context_var = context_var

    def render(self, context):
        try:
            dictionary = template.resolve_variable(self.dictionary, context)
            item = template.resolve_variable(self.item, context)
        except template.VariableDoesNotExist:
            return ''
        context[self.context_var] = dictionary.get(item.id, None)
        return ''

def do_score_for_object(parser, token):
    """
    Retrieves the total score for an object and the number of votes
    it's received and stores them in a context variable which has
    ``score`` and ``num_votes`` properties.

    Example usage::

        {% score_for_object widget as score %}

        {{ score.score }}point{{ score.score|pluralize }}
        after {{ score.num_votes }} vote{{ score.num_votes|pluralize }}
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise template.TemplateSyntaxError("'%s' tag takes exactly three arguments" % bits[0])
    if bits[2] != 'as':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'as'" % bits[0])
    return ScoreForObjectNode(bits[1], bits[3])

def do_scores_for_objects(parser, token):
    """
    Retrieves the total scores for a list of objects and the number of
    votes they have received and stores them in a context variable.

    Example usage::

        {% scores_for_objects widget_list as score_dict %}
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise template.TemplateSyntaxError("'%s' tag takes exactly three arguments" % bits[0])
    if bits[2] != 'as':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'as'" % bits[0])
    return ScoresForObjectsNode(bits[1], bits[3])

def do_vote_by_user(parser, token):
    """
    Retrieves the ``Vote`` cast by a user on a particular object and
    stores it in a context variable. If the user has not voted, the
    context variable will be ``None``.

    Example usage::

        {% vote_by_user user on widget as vote %}
    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly five arguments" % bits[0])
    if bits[2] != 'on':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'on'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must be 'as'" % bits[0])
    return VoteByUserNode(bits[1], bits[3], bits[5])

def do_votes_by_user(parser, token):
    """
    Retrieves the votes cast by a user on a list of objects as a
    dictionary keyed with object ids and stores it in a context
    variable.

    Example usage::

        {% votes_by_user user on widget_list as vote_dict %}
    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly four arguments" % bits[0])
    if bits[2] != 'on':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'on'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must be 'as'" % bits[0])
    return VotesByUserNode(bits[1], bits[3], bits[5])

def do_dict_entry_for_item(parser, token):
    """
    Given an object and a dictionary keyed with object ids - as
    returned by the ``votes_by_user`` and ``scores_for_objects``
    template tags - retrieves the value for the given object and
    stores it in a context variable, storing ``None`` if no value
    exists for the given object.

    Example usage::

        {% dict_entry_for_item widget from vote_dict as vote %}
    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly five arguments" % bits[0])
    if bits[2] != 'from':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'from'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must be 'as'" % bits[0])
    return DictEntryForItemNode(bits[1], bits[3], bits[5])

register.tag('score_for_object', do_score_for_object)
register.tag('scores_for_objects', do_scores_for_objects)
register.tag('vote_by_user', do_vote_by_user)
register.tag('votes_by_user', do_votes_by_user)
register.tag('dict_entry_for_item', do_dict_entry_for_item)

# Simple Tags

def confirm_vote_message(object_description, vote_direction):
    """
    Creates an appropriate message asking the user to confirm the given vote
    for the given object description.

    Example usage::

        {% confirm_vote_message widget.title direction %}
    """
    if vote_direction == 'clear':
        message = 'Confirm clearing your vote for <strong>%s</strong>.'
    else:
        message = 'Confirm <strong>%s</strong> vote for <strong>%%s</strong>.' % vote_direction
    return message % (escape(object_description),)

register.simple_tag(confirm_vote_message)

# Filters

def vote_display(vote, arg=None):
    """
    Given a string mapping values for up and down votes, returns one
    of the strings according to the given ``Vote``:

    =========  =====================  =============
    Vote type   Argument               Outputs
    =========  =====================  =============
    ``+1``     ``"Bodacious,Bogus"``  ``Bodacious``
    ``-1``     ``"Bodacious,Bogus"``  ``Bogus``
    =========  =====================  =============

    If no string mapping is given, "Up" and "Down" will be used.

    Example usage::

        {{ vote|vote_display:"Bodacious,Bogus" }}
    """
    if arg is None:
        arg = 'Up,Down'
    bits = arg.split(',')
    if len(bits) != 2:
        return vote.vote # Invalid arg
    up, down = bits
    if vote.vote == 1:
        return up
    return down

register.filter(vote_display)
########NEW FILE########
__FILENAME__ = views
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.contrib.auth.views import redirect_to_login
from django.template import loader, RequestContext
from django.utils import simplejson

from voting.models import Vote

VOTE_DIRECTIONS = (('up', 1), ('down', -1), ('clear', 0))

def vote_on_object(request, model, direction, post_vote_redirect=None,
        object_id=None, slug=None, slug_field=None, template_name=None,
        template_loader=loader, extra_context=None, context_processors=None,
        template_object_name='object', allow_xmlhttprequest=False):
    """
    Generic object vote function.

    The given template will be used to confirm the vote if this view is
    fetched using GET; vote registration will only be performed if this
    view is POSTed.

    If ``allow_xmlhttprequest`` is ``True`` and an XMLHttpRequest is
    detected by examining the ``HTTP_X_REQUESTED_WITH`` header, the
    ``xmlhttp_vote_on_object`` view will be used to process the
    request - this makes it trivial to implement voting via
    XMLHttpRequest with a fallback for users who don't have JavaScript
    enabled.

    Templates:``<app_label>/<model_name>_confirm_vote.html``
    Context:
        object
            The object being voted on.
        direction
            The type of vote which will be registered for the object.
    """
    if allow_xmlhttprequest and request.is_ajax():
        return xmlhttprequest_vote_on_object(request, model, direction,
                                             object_id=object_id, slug=slug,
                                             slug_field=slug_field)

    if extra_context is None: extra_context = {}
    if not request.user.is_authenticated():
        return redirect_to_login(request.path)

    try:
        vote = dict(VOTE_DIRECTIONS)[direction]
    except KeyError:
        raise AttributeError("'%s' is not a valid vote type." % vote_type)

    # Look up the object to be voted on
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % model._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        raise AttributeError('Generic vote view must be called with either '
                             'object_id or slug and slug_field.')
    try:
        obj = model._default_manager.get(**lookup_kwargs)
    except ObjectDoesNotExist:
        raise Http404, 'No %s found for %s.' % (model._meta.app_label, lookup_kwargs)

    if request.method == 'POST':
        if post_vote_redirect is not None:
            next = post_vote_redirect
        elif request.REQUEST.has_key('next'):
            next = request.REQUEST['next']
        elif hasattr(obj, 'get_absolute_url'):
            if callable(getattr(obj, 'get_absolute_url')):
                next = obj.get_absolute_url()
            else:
                next = obj.get_absolute_url
        else:
            raise AttributeError('Generic vote view must be called with either '
                                 'post_vote_redirect, a "next" parameter in '
                                 'the request, or the object being voted on '
                                 'must define a get_absolute_url method or '
                                 'property.')
        Vote.objects.record_vote(obj, request.user, vote)
        return HttpResponseRedirect(next)
    else:
        if not template_name:
            template_name = '%s/%s_confirm_vote.html' % (
                model._meta.app_label, model._meta.object_name.lower())
        t = template_loader.get_template(template_name)
        c = RequestContext(request, {
            template_object_name: obj,
            'direction': direction,
        }, context_processors)
        for key, value in extra_context.items():
            if callable(value):
                c[key] = value()
            else:
                c[key] = value
        response = HttpResponse(t.render(c))
        return response

def json_error_response(error_message):
    return HttpResponse(simplejson.dumps(dict(success=False,
                                              error_message=error_message)))

def xmlhttprequest_vote_on_object(request, model, direction,
    object_id=None, slug=None, slug_field=None):
    """
    Generic object vote function for use via XMLHttpRequest.

    Properties of the resulting JSON object:
        success
            ``true`` if the vote was successfully processed, ``false``
            otherwise.
        score
            The object's updated score and number of votes if the vote
            was successfully processed.
        error_message
            Contains an error message if the vote was not successfully
            processed.
    """
    if request.method == 'GET':
        return json_error_response(
            'XMLHttpRequest votes can only be made using POST.')
    if not request.user.is_authenticated():
        return json_error_response('Not authenticated.')

    try:
        vote = dict(VOTE_DIRECTIONS)[direction]
    except KeyError:
        return json_error_response(
            '\'%s\' is not a valid vote type.' % direction)

    # Look up the object to be voted on
    lookup_kwargs = {}
    if object_id:
        lookup_kwargs['%s__exact' % model._meta.pk.name] = object_id
    elif slug and slug_field:
        lookup_kwargs['%s__exact' % slug_field] = slug
    else:
        return json_error_response('Generic XMLHttpRequest vote view must be '
                                   'called with either object_id or slug and '
                                   'slug_field.')
    try:
        obj = model._default_manager.get(**lookup_kwargs)
    except ObjectDoesNotExist:
        return json_error_response(
            'No %s found for %s.' % (model._meta.verbose_name, lookup_kwargs))

    # Vote and respond
    Vote.objects.record_vote(obj, request.user, vote)
    return HttpResponse(simplejson.dumps({
        'success': True,
        'score': Vote.objects.get_score(obj),
    }))

########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from south.models import MigrationHistory
from django.db import models
from conceptnet.models import *

class Migration:
    
    def forwards(self, orm):
        if MigrationHistory.objects.filter(app_name='conceptnet4', migration='0001_initial').count() > 0:
            print "Skipping initial migration: it was applied under the name 'conceptnet4'."
            return        
        
        # Adding model 'Assertion'
        db.create_table('assertions', (
            ('id', orm['conceptnet.Assertion:id']),
            ('language', orm['conceptnet.Assertion:language']),
            ('relation', orm['conceptnet.Assertion:relation']),
            ('concept1', orm['conceptnet.Assertion:concept1']),
            ('concept2', orm['conceptnet.Assertion:concept2']),
            ('score', orm['conceptnet.Assertion:score']),
            ('frequency', orm['conceptnet.Assertion:frequency']),
            ('best_surface1', orm['conceptnet.Assertion:best_surface1']),
            ('best_surface2', orm['conceptnet.Assertion:best_surface2']),
            ('best_raw_id', orm['conceptnet.Assertion:best_raw_id']),
            ('best_frame', orm['conceptnet.Assertion:best_frame']),
        ))
        db.send_create_signal('conceptnet', ['Assertion'])
        
        # Adding model 'UserData'
        db.create_table('conceptnet_userdata', (
            ('id', orm['conceptnet.UserData:id']),
            ('created', orm['conceptnet.UserData:created']),
            ('updated', orm['conceptnet.UserData:updated']),
            ('user', orm['conceptnet.UserData:user']),
            ('activity', orm['conceptnet.UserData:activity']),
        ))
        db.send_create_signal('conceptnet', ['UserData'])
        
        # Adding model 'RawAssertion'
        db.create_table('raw_assertions', (
            ('id', orm['conceptnet.RawAssertion:id']),
            ('created', orm['conceptnet.RawAssertion:created']),
            ('updated', orm['conceptnet.RawAssertion:updated']),
            ('sentence', orm['conceptnet.RawAssertion:sentence']),
            ('assertion', orm['conceptnet.RawAssertion:assertion']),
            ('creator', orm['conceptnet.RawAssertion:creator']),
            ('surface1', orm['conceptnet.RawAssertion:surface1']),
            ('surface2', orm['conceptnet.RawAssertion:surface2']),
            ('frame', orm['conceptnet.RawAssertion:frame']),
            ('batch', orm['conceptnet.RawAssertion:batch']),
            ('language', orm['conceptnet.RawAssertion:language']),
            ('score', orm['conceptnet.RawAssertion:score']),
        ))
        db.send_create_signal('conceptnet', ['RawAssertion'])
        
        # Adding model 'Concept'
        db.create_table('concepts', (
            ('id', orm['conceptnet.Concept:id']),
            ('language', orm['conceptnet.Concept:language']),
            ('text', orm['conceptnet.Concept:text']),
            ('num_assertions', orm['conceptnet.Concept:num_assertions']),
            ('words', orm['conceptnet.Concept:words']),
            ('visible', orm['conceptnet.Concept:visible']),
        ))
        db.send_create_signal('conceptnet', ['Concept'])
        
        # Adding model 'Frame'
        db.create_table('conceptnet_frames', (
            ('id', orm['conceptnet.Frame:id']),
            ('language', orm['conceptnet.Frame:language']),
            ('text', orm['conceptnet.Frame:text']),
            ('relation', orm['conceptnet.Frame:relation']),
            ('goodness', orm['conceptnet.Frame:goodness']),
            ('frequency', orm['conceptnet.Frame:frequency']),
            ('question_yn', orm['conceptnet.Frame:question_yn']),
            ('question1', orm['conceptnet.Frame:question1']),
            ('question2', orm['conceptnet.Frame:question2']),
        ))
        db.send_create_signal('conceptnet', ['Frame'])
        
        # Adding model 'Batch'
        db.create_table('parsing_batch', (
            ('id', orm['conceptnet.Batch:id']),
            ('created', orm['conceptnet.Batch:created']),
            ('updated', orm['conceptnet.Batch:updated']),
            ('owner', orm['conceptnet.Batch:owner']),
            ('status', orm['conceptnet.Batch:status']),
            ('remarks', orm['conceptnet.Batch:remarks']),
            ('progress_num', orm['conceptnet.Batch:progress_num']),
            ('progress_den', orm['conceptnet.Batch:progress_den']),
        ))
        db.send_create_signal('conceptnet', ['Batch'])
        
        # Adding model 'SurfaceForm'
        db.create_table('surface_forms', (
            ('id', orm['conceptnet.SurfaceForm:id']),
            ('language', orm['conceptnet.SurfaceForm:language']),
            ('concept', orm['conceptnet.SurfaceForm:concept']),
            ('text', orm['conceptnet.SurfaceForm:text']),
            ('residue', orm['conceptnet.SurfaceForm:residue']),
            ('use_count', orm['conceptnet.SurfaceForm:use_count']),
        ))
        db.send_create_signal('conceptnet', ['SurfaceForm'])
        
        # Adding model 'Relation'
        db.create_table('predicatetypes', (
            ('id', orm['conceptnet.Relation:id']),
            ('name', orm['conceptnet.Relation:name']),
            ('description', orm['conceptnet.Relation:description']),
        ))
        db.send_create_signal('conceptnet', ['Relation'])
        
        # Creating unique_together for [language, text] on SurfaceForm.
        db.create_unique('surface_forms', ['language_id', 'text'])
        
        # Creating unique_together for [relation, concept1, concept2, frequency, language] on Assertion.
        db.create_unique('assertions', ['relation_id', 'concept1_id', 'concept2_id', 'frequency_id', 'language_id'])
        
        # Creating unique_together for [language, text] on Concept.
        db.create_unique('concepts', ['language_id', 'text'])
        
    
    
    def backwards(self, orm):
        
        # Deleting unique_together for [language, text] on Concept.
        db.delete_unique('concepts', ['language_id', 'text'])
        
        # Deleting unique_together for [relation, concept1, concept2, frequency, language] on Assertion.
        db.delete_unique('assertions', ['relation_id', 'concept1_id', 'concept2_id', 'frequency_id', 'language_id'])
        
        # Deleting unique_together for [language, text] on SurfaceForm.
        db.delete_unique('surface_forms', ['language_id', 'text'])
        
        # Deleting model 'Assertion'
        db.delete_table('assertions')
        
        # Deleting model 'UserData'
        db.delete_table('conceptnet_userdata')
        
        # Deleting model 'RawAssertion'
        db.delete_table('raw_assertions')
        
        # Deleting model 'Concept'
        db.delete_table('concepts')
        
        # Deleting model 'Frame'
        db.delete_table('conceptnet_frames')
        
        # Deleting model 'Batch'
        db.delete_table('parsing_batch')
        
        # Deleting model 'SurfaceForm'
        db.delete_table('surface_forms')
        
        # Deleting model 'Relation'
        db.delete_table('predicatetypes')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'conceptnet.assertion': {
            'Meta': {'unique_together': "(('relation', 'concept1', 'concept2', 'frequency', 'language'),)", 'db_table': "'assertions'"},
            'best_frame': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conceptnet.Frame']", 'null': 'True'}),
            'best_raw_id': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'best_surface1': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'left_assertion_set'", 'null': 'True', 'to': "orm['conceptnet.SurfaceForm']"}),
            'best_surface2': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'right_assertion_set'", 'null': 'True', 'to': "orm['conceptnet.SurfaceForm']"}),
            'concept1': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'left_assertion_set'", 'to': "orm['conceptnet.Concept']"}),
            'concept2': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'right_assertion_set'", 'to': "orm['conceptnet.Concept']"}),
            'frequency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['nl.Frequency']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'relation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conceptnet.Relation']"}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'votes': ('django.contrib.contenttypes.generic.GenericRelation', [], {'to': "orm['voting.Vote']"})
        },
        'conceptnet.batch': {
            'Meta': {'db_table': "'parsing_batch'"},
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'progress_den': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'progress_num': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'remarks': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {})
        },
        'conceptnet.concept': {
            'Meta': {'unique_together': "(('language', 'text'),)", 'db_table': "'concepts'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'num_assertions': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'text': ('django.db.models.fields.TextField', [], {'db_index': 'True'}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'words': ('django.db.models.fields.IntegerField', [], {})
        },
        'conceptnet.frame': {
            'Meta': {'db_table': "'conceptnet_frames'"},
            'frequency': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['nl.Frequency']"}),
            'goodness': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'question1': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'question2': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'question_yn': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'relation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conceptnet.Relation']"}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'conceptnet.rawassertion': {
            'Meta': {'db_table': "'raw_assertions'"},
            'assertion': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conceptnet.Assertion']", 'null': 'True'}),
            'batch': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conceptnet.Batch']", 'null': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'frame': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conceptnet.Frame']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'sentence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Sentence']", 'null': 'True'}),
            'surface1': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'left_rawassertion_set'", 'to': "orm['conceptnet.SurfaceForm']"}),
            'surface2': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'right_rawassertion_set'", 'to': "orm['conceptnet.SurfaceForm']"}),
            'updated': ('django.db.models.fields.DateTimeField', [], {}),
            'votes': ('django.contrib.contenttypes.generic.GenericRelation', [], {'to': "orm['voting.Vote']"})
        },
        'conceptnet.relation': {
            'Meta': {'db_table': "'predicatetypes'"},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True'})
        },
        'conceptnet.surfaceform': {
            'Meta': {'unique_together': "(('language', 'text'),)", 'db_table': "'surface_forms'"},
            'concept': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conceptnet.Concept']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'residue': ('django.db.models.fields.TextField', [], {}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'use_count': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'conceptnet.userdata': {
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['events.Activity']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'corpus.language': {
            'id': ('django.db.models.fields.CharField', [], {'max_length': '16', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sentence_count': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'corpus.sentence': {
            'Meta': {'db_table': "'sentences'"},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['events.Activity']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'votes': ('django.contrib.contenttypes.generic.GenericRelation', [], {'to': "orm['voting.Vote']"})
        },
        'events.activity': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {})
        },
        'nl.frequency': {
            'Meta': {'unique_together': "(('language', 'text'),)", 'db_table': "'conceptnet_frequency'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'value': ('django.db.models.fields.IntegerField', [], {})
        },
        'voting.vote': {
            'Meta': {'unique_together': "(('user', 'content_type', 'object_id'),)", 'db_table': "'votes'"},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'vote': ('django.db.models.fields.SmallIntegerField', [], {})
        }
    }
    
    complete_apps = ['conceptnet']

########NEW FILE########
__FILENAME__ = 0002_rename_tables

from south.db import db
from django.db import models
from conceptnet.corpus.models import *

class Migration:
    
    def forwards(self, orm):
        db.rename_table('parsing_batch', 'conceptnet_batch')
        db.rename_table('predicatetypes', 'conceptnet_relation')
        db.rename_table('conceptnet_frames', 'conceptnet_frame')
        db.rename_table('concepts', 'conceptnet_concept')
        db.rename_table('surface_forms', 'conceptnet_surfaceform')
        db.rename_table('assertions', 'conceptnet_assertion')
        db.rename_table('raw_assertions', 'conceptnet_rawassertion')
    
    def backwards(self, orm):
        db.rename_table('conceptnet_batch', 'parsing_batch')
        db.rename_table('conceptnet_relation', 'predicatetypes')
        db.rename_table('conceptnet_frame', 'conceptnet_frames')
        db.rename_table('conceptnet_concept', 'concepts')
        db.rename_table('conceptnet_surfaceform', 'surface_forms')
        db.rename_table('conceptnet_assertion', 'assertions')
        db.rename_table('conceptnet_rawassertion', 'raw_assertions')
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'corpus.dependencyparse': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index1': ('django.db.models.fields.IntegerField', [], {}),
            'index2': ('django.db.models.fields.IntegerField', [], {}),
            'linktype': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'sentence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Sentence']"}),
            'word1': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'word2': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'corpus.language': {
            'id': ('django.db.models.fields.CharField', [], {'max_length': '16', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sentence_count': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'corpus.sentence': {
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['events.Activity']"}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'score': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'votes': ('django.contrib.contenttypes.generic.GenericRelation', [], {'to': "orm['voting.Vote']"})
        },
        'corpus.taggedsentence': {
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Language']"}),
            'sentence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['corpus.Sentence']", 'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'events.activity': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {})
        },
        'voting.vote': {
            'Meta': {'unique_together': "(('user', 'content_type', 'object_id'),)", 'db_table': "'votes'"},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'vote': ('django.db.models.fields.SmallIntegerField', [], {})
        }
    }
    
    complete_apps = ['corpus']

########NEW FILE########
__FILENAME__ = models
__version__ = "4.0rc2"
from django.db import models
from django.db.models import Q
from conceptnet.corpus.models import Language, Sentence, User, ScoredModel, Frequency
from events.models import Event, Activity
from voting.models import Vote, SCORES
from django.contrib.contenttypes import generic
from csc_utils.cache import cached
from datetime import datetime
from urllib import quote as urlquote
import re

DEFAULT_LANGUAGE = en = Language(id='en', name='English') 

class TimestampedModel(models.Model):
    created = models.DateTimeField(default=datetime.now)
    updated = models.DateTimeField()
    
    def save(self, **kwargs):
        self.updated = datetime.now()
        super(TimestampedModel, self).save(**kwargs)

    class Meta:
        abstract = True

class UserData(TimestampedModel):
    user = models.ForeignKey(User)
    activity = models.ForeignKey(Activity)
    
    class Meta:
        abstract = True

class Batch(TimestampedModel):
    owner = models.ForeignKey(User)
    status = models.CharField(max_length=255,blank=True)
    remarks = models.TextField(blank=True)
    progress_num = models.IntegerField(default=0)
    progress_den = models.IntegerField(default=0)

    def __unicode__(self):
        return u"Batch " + str(self.id) + " (owner: " + self.owner.username + ") <" + str(self.progress_num) + "/" + str(self.progress_den) + " " + self.status + ">"


class Relation(models.Model):
    name = models.CharField(max_length=128,unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)

    def __unicode__(self):
        return self.name

    @classmethod
    def get(cls, name):
        # Check if the parameter is already a Relation. We don't use
        # isinstance in case of accidental multiple imports (e.g.,
        # conceptnet.models vs conceptnet4.models).
        if hasattr(name, 'id'):
            return name
        return cls.objects.get(name=name)

class Frame(models.Model):
    """
    A Frame is a natural-language template containing two slots, representing a
    way that a :class:`Relation` could be expressed in language.
    
    It can be used
    for pattern matching to create a :class:`RawAssertion`, or to express an
    existing :class:`RawAssertion` as a sentence.
    """
    language = models.ForeignKey(Language)
    text = models.TextField()
    relation = models.ForeignKey(Relation)
    goodness = models.IntegerField()
    frequency = models.ForeignKey(Frequency)
    question_yn = models.TextField(null=True, blank=True)
    question1 = models.TextField(null=True, blank=True)
    question2 = models.TextField(null=True, blank=True)

    def preferred(self):
        return self.goodness > 2
    preferred.boolean = True
    
    def fill_in(self, a, b):
        """
        Fill in the slots of this frame with the strings *a* and *b*.
        """
        res = self.text.replace('{%}', '')
        res = res.replace('{1}', a, 1)
        return res.replace('{2}', b, 1)

    def __unicode__(self):
        return "%s (%s)" % (self.text, self.language.id)
    def re_pattern(self):
        if not hasattr(self, '_re_pattern'):
            self._re_pattern = re.compile(self.text.replace('{%}',
            '').replace('{1}', '(.+)').replace('{2}', '(.+)').strip('. '))
        return self._re_pattern
    def match(self, text):
        match = self.re_pattern().match(text)
        if match:
            return match.groups()
        else: return None
    def display(self):
        return self.fill_in('...', '...')
    
    @staticmethod
    def match_sentence(text, language):
        text = text.strip('. ')
        for frame in Frame.objects.filter(language=language,
        goodness__gte=2).order_by('-goodness'):
            result = frame.match(text)
            if result:
                return frame, result
        return None


class Feature(object):
    """
    Features are not models in the database, but they are useful ways to
    describe the knowledge contained in the edges of ConceptNet.

    A Feature is the combination of a :class:`Concept` and a :class:`Relation`.
    The combination of a Concept and a Feature, then, gives a
    :class:`Proposition`, a statement that can have a truth value; when given a
    truth value, this forms an :class:`Assertion`.

    As an example, the relation ``PartOf(cello, orchestra)`` breaks down into
    the concept ``cello`` and the feature ``PartOf(x, orchestra)``. It also
    breaks down into ``orchestra`` and ``PartOf(cello, x)``.

    Features can be *left features* or *right features*, depending on whether
    they include the left or right concept (that is, the first or second
    argument) in the Assertion. The Feature class itself is an abstract class,
    which is realized in the classes :class:`LeftFeature` and
    :class:`RightFeature`.
    
    Each Assertion can be described with its
    left concept (:attr:`concept1`) and its right feature, or its right concept
    (:attr:`concept2`) and its left feature.

    The notation is based on putting the relation in a "bucket". For
    example, ``PartOf(cello, orchestra) =
    cello\PartOf/orchestra``. Breaking this apart gives left and right
    features::

      cello: PartOf/orchestra (left concept and right feature)
      orchestra: cello\PartOf (right concept and left feature)
      
    """
    
    def __init__(self, relation, concept):
        """
        Create a LeftFeature or RightFeature (depending on which class you
        instantiate), with the given relation and concept.
        """
        if self.__class__ == Feature:
            raise NotImplementedError("Feature is an abstract class")
        if isinstance(relation, basestring):
            relation = Relation.objects.get(name=relation)
        #if isinstance(concept, basestring):
        #    concept = Concept.get(concept, auto_create=True)
        self.relation = relation
        self.concept = concept
        
    def to_tuple(self):
        return (self.tuple_key, self.relation.name, self.concept.text)
    @property
    def language(self):
        return self.concept.language
    def __hash__(self): # Features should be immutable.
        return hash((self.__class__.__name__, self.relation, self.concept))
    def __cmp__(self, other):
        if not isinstance(other, Feature): return -1
        return cmp((self.__class__, self.relation, self.concept),
                   (other.__class__, other.relation, other.concept))
    @staticmethod
    def from_tuple(tup, lang=DEFAULT_LANGUAGE, lemmatize=False):
        """
        Some systems such as AnalogySpace use a lower-level representation of
        features, representing them as a tuple of three strings:
        ``(left_or_right, relation, concept)``. This factory method takes in
        such a tuple and produces a proper Feature object.
        """
        typ, rel, txt = tup
        if lemmatize:
            c = Concept.get(txt, lang)
        else:
            c, _ = Concept.objects.get_or_create(text=txt, language=lang)
        r = Relation.objects.get(name=rel)
        return Feature.from_obj_tuple(typ, r, c)
    @staticmethod
    def from_obj_tuple(typ, relation, concept):
        classes = {'left': LeftFeature, 'right': RightFeature}
        if typ not in classes: raise ValueError
        return classes[typ](relation, concept)
        
    @property
    def frame(self):
        """
        Get a good natural-language frame for expressing this feature. For
        backward compatibility, this is a property.
        """
        return Frame.objects.filter(language=self.language,
                                    relation=self.relation).order_by('-goodness')[0]
    def fill_in(self, newconcept):
        """
        Fill in the blank of this feature with a :class:`Concept`. The result
        is a :class:`Proposition`.
        """
        raise NotImplementedError, "Feature is an abstract class"
    def matching_assertions(self):
        """
        Get all :class:`Assertions` that contain this feature.
        """
        raise NotImplementedError, "Feature is an abstract class"
    def matching_raw(self):
        """
        Get all :class:`RawAssertions` that contain this feature.
        """
        raise NotImplementedError, "Feature is an abstract class"
    def nl_frame(self, gap=None):
        """
        This code is kinda confused.
        """
        examples = self.matching_raw().filter(frame__frequency__value__gt=0, frame__goodness__gte=3)
        try:
            return examples[0].frame
        except IndexError:
            examples = self.matching_raw().filter(frame__frequency__value__gt=0, frame__goodness__gte=2)
            try:
                return examples[0].frame
            except IndexError:
                # If we can't find an example, just get the best frame
                return Frame.objects.filter(
                    language=self.language,
                    relation=self.relation,
                    frequency__value__gt=0
                ).order_by('-goodness')[0]

    def nl_statement(self, gap='...'):
        """
        Express this feature as a statement in natural language. The omitted
        concept is replaced by the value in *gap*.
        """
        frame, ftext, text1, text2 = self.nl_parts(gap)
        return frame.fill_in(text1, text2)
    def _matching_assertions(self):
        return Assertion.objects.filter(
          language=self.concept.language,
          score__gt=0,
          relation=self.relation)
    def _matching_raw(self):
        return RawAssertion.objects.filter(
          language=self.concept.language,
          assertion__relation=self.relation)
        
    @cached(lambda self, gap: 'nl_parts_'+unicode(self)+'_'+gap, cached.day)
    def nl_parts(self, gap='...'):
        """
        Get a 4-tuple, ``(frame, ftext, text1, text2)``, that contains the
        information needed to express this feature in natural language:

        - The Frame object that is best for expressing this feature.
        - The text of that frame.
        - The text that fills the first blank in the frame (which might be
          :param:`gap`).
        - The text that fills the second blank in the frame (which might be
          :param:`gap`).
        """
        frame = self.nl_frame()
        matching_raw = self.matching_raw()
        try:
            surface = matching_raw[0].surface(self.idx)
        except IndexError:
            surface = self.concept.some_surface() or self.concept
        if isinstance(self, LeftFeature):
            return (frame, frame.text.replace('{%}', ''), surface.text, gap)
        elif isinstance(self, RightFeature):
            return (frame, frame.text.replace('{%}', ''), gap, surface.text)
    
    @property
    def direction(self):
        return self.tuple_key
    
    def __repr__(self):
        return "<Feature: %s>" % unicode(self)
    
class LeftFeature(Feature):
    idx = 1
    tuple_key = 'left'
    def __unicode__(self):
        return '%s\\%s' % (self.concept.text, self.relation)
    def fill_in(self, newconcept):
        return Proposition(self.concept, self.relation, newconcept, self.concept.language)
    def matching_assertions(self):
        return self._matching_assertions().filter(concept1=self.concept)
    def matching_raw(self):
        return self._matching_raw().filter(surface1__concept=self.concept)

class RightFeature(Feature):
    idx = 2
    tuple_key = 'right'
    def __unicode__(self):
        return '%s/%s' % (self.relation, self.concept.text)
    def fill_in(self, newconcept):
        return Proposition(newconcept, self.relation, self.concept, self.concept.language)
    def matching_assertions(self):
        return self._matching_assertions().filter(concept2=self.concept)
    def matching_raw(self):
        return self._matching_raw().filter(assertion__concept2=self.concept)

def ensure_concept(concept):
    if isinstance(concept, Concept): return concept
    lang = DEFAULT_LANGUAGE
    if isinstance(concept, (tuple, list)):
        text, lang = concept
    else:
        text = concept
    return Concept.get(text, lang, auto_create=True)
    
class Proposition(object):
    """
    A Proposition represents a statement that may or may not be true. It is
    like an :class:`Assertion` without a truth value.
    """
    def __init__(self, concept1, rel, concept2, lang):
        self.concept1 = ensure_concept(concept1)
        self.relation = rel
        self.concept2 = ensure_concept(concept2)
        self.lang = lang
    def __unicode__(self):
        return '<Proposition: %s %s %s>' % (self.concept1, self.relation,
        self.concept2)
    def nl_question_bad(self):
        """
        Express this Proposition as a question in natural language, poorly.
        """
        frame = Frame.objects.filter(language=self.lang, relation=self.relation,
                                     goodness__gte=3)[0]
        same_c1 = RawAssertion.objects.filter(language=self.lang,
            frame__relation=self.relation, surface1__concept=self.concept1)
        try:
            surface1 = same_c1[0].surface1.text
        except IndexError:
            surface1 = self.concept1.some_surface() or self.concept1
            surface1 = surface1.text
        same_c2 = RawAssertion.objects.filter(language=self.lang,
            frame__relation=self.relation, surface2__concept=self.concept2)
        try:
            surface2 = same_c2[0].surface2.text
        except IndexError:
            surface2 = self.concept2.some_surface() or self.concept2
            surface2 = surface2.text
        # The wiki-like brackets should be replaced by appropriate formatting.
        surface1b = "[[%s]]" % surface1
        surface2b = "[[%s]]" % surface2

        if frame.question_yn:
            return frame.question_yn.replace('{1}', surface1b)\
                   .replace('{2}', surface2b)
        else:
            return frame.text.replace('{1}', surface1b)\
                   .replace('{2}', surface2b)\
                   .replace('{%}', '') + '?'
    def right_feature(self):
        return RightFeature(self.relation, self.concept2)
    def left_feature(self):
        return LeftFeature(self.relation, self.concept1)
    def nl_parts(self):
        """
        Get a 4-tuple, ``(frame, ftext, text1, text2)``, that contains the
        information needed to express this feature in natural language:

        - The Frame object that is best for expressing this feature.
        - The text of that frame.
        - The text that fills the first blank in the frame.
        - The text that fills the second blank in the frame.
        """
        # TODO: replace this with something cleverer but still sufficiently
        # fast
        try:
            frame = Frame.objects.filter(language=self.lang,
            relation=self.relation, goodness__gte=3)[0]
        except IndexError:
            frame = Frame.objects.filter(language=self.lang,
            relation=self.relation).order_by('-goodness')[0]

        #frame = self.right_feature().nl_frame()
        #surfaces = {}
        same_c1 = RawAssertion.objects.filter(frame__relation=self.relation,
                                              surface1__concept=self.concept1)
        try:
            surface1 = same_c1[0].surface1.text
        except IndexError:
            surface1 = self.concept1.some_surface() or self.concept1
            surface1 = surface1.text
        same_c2 = RawAssertion.objects.filter(language=self.lang,
            frame__relation=self.relation, surface2__concept=self.concept2)            
        try:
            surface2 = same_c2[0].surface2.text
        except IndexError:
            surface2 = self.concept2.some_surface() or self.concept2
            surface2 = surface2.text
        return (frame, frame.text, surface1, surface2)
        
    def nl_parts_topdown(self):
        frame = Frame.objects.filter(language=self.lang,
        relation=self.relation, goodness__gte=3)[0]
        #surfaces = {}
        same_c1 = RawAssertion.objects.filter(language=self.lang,
            frame__relation=self.relation, surface1__concept=self.concept1)
        try:
            surface1 = same_c1[0].surface1.text
        except IndexError:
            surface1 = self.concept1.some_surface() or self.concept1
            surface1 = surface1.text
        same_c2 = RawAssertion.objects.filter(language=self.lang,
            frame__relation=self.relation, surface2__concept=self.concept2)            
        try:
            surface2 = same_c2[0].surface2.text
        except IndexError:
            surface2 = self.concept2.some_surface() or self.concept2
            surface2 = surface2.text
        return (frame, frame.text, surface1, surface2)

class Concept(models.Model):
    """
    Concepts are the nodes of ConceptNet. They are the things that people have
    common sense knowledge about.
    
    Concepts are expressed in natural language with
    sets of related words and phrases: for example, "take a picture", "taking
    pictures", "to take pictures", and "you take a picture" are various
    `surface forms`_ of the same Concept.
    """
    language = models.ForeignKey(Language)
    text = models.TextField(db_index=True)
    num_assertions = models.IntegerField(default=0)
    # canonical_name = models.TextField()
    words = models.IntegerField()
    visible = models.BooleanField(default=True)

    def save(self, *a, **kw):
        ''' Ensures that a concept has a correct word count.  Called
        before saving a concept.
        '''
        self.words = len(self.text.split())
        super(Concept, self).save(*a, **kw)
    
    @property
    @cached(lambda self: 'concept_canonical_name_'+self.text, cached.week)
    def canonical_name(self):
        return self.some_surface().text

    def __unicode__(self):
        return u"<" + self.language.id + ": " + self.text + ">"
    
    def get_assertions(self, useful_only=True):
        '''Get all :class:`Assertions` about this concept.'''
        return Assertion.get_filtered(Q(concept1=self) | Q(concept2=self), useful_only=useful_only)

    def get_assertions_forward(self, useful_only=True):
        '''Get all :class:`Assertions` with this concept on the left.'''
        return Assertion.get_filtered(Q(concept1=self), useful_only=useful_only)

    def get_assertions_reverse(self, useful_only=True):
        '''Get all :class:`Assertions` with this concept on the right.'''
        return Assertion.get_filtered(Q(concept2=self), useful_only=useful_only)
    
    def raw_assertions(self):
        got = RawAssertion.objects.filter(
            (Q(assertion__concept1=self) | Q(assertion__concept2=self))
            & Q(score__gt=0) & Q(assertion__score__gt=0)
        )
        return got

    def raw_assertions_no_dupes(self, n=10, related=None):
        from django.db.models import F
        got = RawAssertion.objects.filter(
            (Q(assertion__concept1=self) | Q(assertion__concept2=self))
            & Q(score__gt=0) & Q(assertion__score__gt=0)
            & Q(assertion__best_raw_id=F('id'))
        )
        #all_raw = RawAssertion.objects.filter(
        #    (Q(assertion__concept1=self) | Q(assertion__concept2=self))
        #    & Q(score__gt=0) & Q(assertion__score__gt=0)
        #)
        #if related: all_raw = all_raw.select_related(**related)
        #used = set()
        #got = []
        #for raw in all_raw:
        #    if raw.assertion in used: continue
        #    used.add(raw.assertion)
        #    got.append(raw)
        #    if len(got) >= n: break
        return got
    
    def get_my_right_features(self, useful_only=True):
        '''
        Get all the RightFeatures that have been asserted about this concept.

        Returns a list of (feature, frequency, score, assertion) tuples.
        '''
        return [(RightFeature(a.relation, a.concept2), a.frequency, a.score, a)
                for a in self.get_assertions_forward(useful_only)]

    
    def get_my_left_features(self, useful_only=True):
        '''
        Get all the LeftFeatures that have been asserted about this concept.

        Returns a list of (feature, frequency, score, assertion) tuples.
        '''
        return [(LeftFeature(a.relation, a.concept1), a.frequency, a.score, a)
                for a in self.get_assertions_reverse(useful_only)]

    
    def has_feature(self, feature):
        '''
        Returns True if the concept has the given feature.
        '''
        score = self.score_for_feature(feature)
        return score is not None and score > 0

    def score_for_feature(self, feature):
        try:
            assertions = Assertion.objects.filter(relation=feature.relation)
            if feature.tuple_key == 'left':
                assertions = assertions.filter(concept1=feature.concept,
                                               concept2=self)
            else:
                assertions = assertions.filter(concept1=self,
                                               concept2=feature.concept)
            return max(a.score for a in assertions)
        except ValueError: # what max() throws for an empty sequence
            return None
    
    def group_assertions_by_feature(self, useful_only=True):
        forward_assertions = self.get_assertions_forward(useful_only)\
          .select_related('all_raw__surface2', 'frequency')
        reverse_assertions = self.get_assertions_reverse(useful_only)\
          .select_related('all_raw__surface1', 'frequency')
        thedict = {}
        for a in forward_assertions:
            # FIXME: seems that features no longer have polarity.
            thedict.setdefault(LeftFeature(a.relation, self, a.polarity), [])\
                .append((a.best_raw().surface2.text, a))
        for a in reverse_assertions:
            thedict.setdefault(RightFeature(a.relation, self, a.polarity), [])\
                .append((a.best_raw().surface1.text, a))
        return thedict
    
    def top_assertions_by_feature(self, limit=50, useful_only=True):
        results = []
        manager = Assertion.objects
        # forward relations
        for relation in Relation.objects.all():
            feature = LeftFeature(relation, self)
            filtered = manager.filter(concept1=self, relation=relation,
                                      best_surface2__isnull=False)
            if useful_only:
                filtered = filtered.filter(score__gt=0)
            expanded = filtered.select_related(
                'frequency', 'best_surface2'
            )
            best = expanded[:limit]
            
            described = [(a.best_surface2.text, a.frequency.text,
                          a.frequency.value > 0, a) for a in best]
            if len(described) > 0: results.append((feature, described))
        # backward relations
        for relation in Relation.objects.all():
            feature = RightFeature(relation, self)
            filtered = manager.filter(concept2=self, relation=relation,
                                      best_surface1__isnull=False)
            if useful_only:
                filtered = filtered.filter(score__gt=0)
            expanded = filtered.select_related(
                'frequency', 'best_surface1'
            )
            best = expanded[:limit]
            
            described = [(a.best_surface1.text, a.frequency.text,
                          a.frequency.value > 0, a) for a in best]
            if len(described) > 0: results.append((feature, described))
        results.sort(key=lambda x: -len(x[1]))
        return results

    def some_surface(self):
        """
        Get an arbitrary :class:`SurfaceForm` representing this concept.

        Returns None if the concept has no surface form.
        """
        try:
            return self.surfaceform_set.all()[0]
        except IndexError:
            return None
    
    @classmethod
    def get(cls, text, language, auto_create=False):
        """
        Get the Concept represented by a given string of text.

        If the Concept does not exist, this method will return None by default.
        However, if the parameter ``auto_create=True`` is given, then this will
        create the Concept (adding it to the database) instead.
        
        You should not run the string through a normalizer, or use a string
        which came from :attr:`Concept.text` (which is equivalent). If you
        have a normalized string, you should use :meth:`get_raw` instead.
        """
        if not isinstance(language, Language):
            language = Language.get(language)
        surface = SurfaceForm.get(text, language, auto_create)
        if surface is None:
            return Concept.get_raw(language.nl.normalize(text), language)
        return surface.concept

    @classmethod
    def get_raw(cls, normalized_text, language, auto_create=False):
        """
        Get the Concept whose normalized form is the given string.

        If the Concept does not exist, this method will raise a
        Concept.DoesNotExist exception.  However, if the parameter
        ``auto_create=True`` is given, then this will create the
        Concept (adding it to the database) instead.

        Normalized forms should not be assumed to be stable; they may change
        between releases.
        """
        if auto_create:
            concept_obj, created = cls.objects.get_or_create(text=normalized_text,language=language)
        else:
            concept_obj = cls.objects.get(text=normalized_text,language=language)
        return concept_obj

    @classmethod
    def exists(cls, text, language, is_raw=False):
        '''
        Determine if a concept exists in ConceptNet.

        If `is_raw` is True, `text` is considered to be already in the
        raw (normalized) concept form. Otherwise, it is normalized
        before being checked in the database.
        '''
        if not isinstance(language, Language):
            language = Language.get(language)
        if not is_raw:
            surface = SurfaceForm.get(text, language, False)
            if surface is not None: return True
            text = language.nl.normalize(text)

        return cls.exists_raw(text, language)

    @classmethod
    def exists_raw(cls, normalized_text, language):
        return bool(cls.objects.filter(text=normalized_text, language=language))
            
        
    @classmethod
    @cached(lambda cls, id: 'conceptbyid_%d' % id, cached.minute)
    def get_by_id(cls, id):
        return cls.objects.get(id=id)
    
    def update_num_assertions(self):
        self.num_assertions = self.get_assertions().count()
        self.save()

    # used in commons
    def get_absolute_url(self):
        return '/%s/concept/+%s/' % (self.language.id, urlquote(self.text))
    
    class Meta:
        unique_together = ('language', 'text')
    
        
class UsefulAssertionManager(models.Manager):
    def get_query_set(self):
        return super(UsefulAssertionManager, self).get_query_set().filter(
            score__gt=0, concept1__visible=True, concept2__visible=True
        )


class SurfaceForm(models.Model):
    """
    A SurfaceForm is a string used to express a :class:`Concept` in its natural
    language.
    """
    language = models.ForeignKey(Language)
    concept = models.ForeignKey(Concept)
    text = models.TextField()
    residue = models.TextField()
    use_count = models.IntegerField(default=0)
    
    @staticmethod
    def get(text, lang, auto_create=False):
        if isinstance(lang, basestring):
            lang = Language.get(lang)
        nl = lang.nl
        try:
            known = SurfaceForm.objects.get(language=lang, text=text)
            return known
        except SurfaceForm.DoesNotExist:
            if not auto_create:
                return None
            else:
                lemma, residue = nl.lemma_factor(text)
                concept, created = Concept.objects.get_or_create(language=lang, text=lemma)
                if created: concept.save()

                # use get_or_create so it's atomic
                surface_form, _ = SurfaceForm.objects.get_or_create(concept=concept,
                text=text, residue=residue, language=lang)
                return surface_form
    
    def update_raw(self):
        for raw in self.left_rawassertion_set.all():
            raw.update_assertion()
        for raw in self.right_rawassertion_set.all():
            raw.update_assertion()
    
    def update(self, stem, residue):
        self.concept = Concept.get_raw(stem, self.language, auto_create=True)
        self.residue = residue
        self.save()
        self.update_raw()
        return self
    
    @property
    def urltext(self):
        return urlquote(self.text)
    
    def __unicode__(self):
        return self.text
    
    class Meta:
        unique_together = (('language', 'text'),)
        ordering = ['-use_count']

class Assertion(models.Model, ScoredModel):
    # Managers
    objects = models.Manager()
    useful = UsefulAssertionManager()
    
    language = models.ForeignKey(Language)
    relation = models.ForeignKey(Relation)
    concept1 = models.ForeignKey(Concept, related_name='left_assertion_set')
    concept2 = models.ForeignKey(Concept, related_name='right_assertion_set')
    score = models.IntegerField(default=0)
    frequency = models.ForeignKey(Frequency)
    votes = generic.GenericRelation(Vote)
    
    best_surface1 = models.ForeignKey(SurfaceForm, null=True, related_name='left_assertion_set')
    best_surface2 = models.ForeignKey(SurfaceForm, null=True, related_name='right_assertion_set')
    best_raw_id = models.IntegerField(null=True)
    best_frame = models.ForeignKey(Frame, null=True)
    
    class Meta:
        unique_together = ('relation', 'concept1', 'concept2', 'frequency', 'language')
        ordering = ['-score']
        
    def best_raw(self):
        """
        Get the highest scoring :class:`RawAssertion` for this assertion.
        """
        return self.rawassertion_set.all()[0]
        
    def nl_repr(self, wrap_text=lambda assertion, text: text):
        # FIXME: use the raw cache
        try:
            return self.best_raw().nl_repr(wrap_text)
        except ValueError:
            raise ValueError(str(self))
            return '%s %s %s' % (wrap_text(self, self.concept1.text),
                                 self.relation.name,
                                 wrap_text(self, self.concept2.text))

    def update_raw_cache(self):
        try:
            best_raw = self.best_raw()
        except IndexError: return
        
        self.best_surface1 = best_raw.surface1
        self.best_surface2 = best_raw.surface2
        self.best_frame = best_raw.frame
        self.best_raw_id = best_raw.id
        self.save()
    
    def update_score(self):
        old_score = self.score
        ScoredModel.update_score(self)
        if (self.score == 0) != (old_score == 0):
            self.concept1.update_num_assertions()
            self.concept2.update_num_assertions()
  
    @property
    def creator(self):
        return self.best_raw().creator
        
    @property
    def polarity(self):
        if self.frequency.value >= 0: return 1
        else: return -1

    def __unicode__(self):
        #return "Assertion"
        return u"%s(%s, %s)[%s]" % (self.relation.name, self.concept1.text,
        self.concept2.text, self.frequency.text)
        
    @classmethod
    def get_filtered(cls, *a, **kw):
        useful_only = kw.pop('useful_only', True)
        if useful_only: return cls.useful.filter(*a, **kw)
        else: return cls.objects.filter(*a, **kw)
        
    def get_absolute_url(self):
        return '/%s/assertion/%s/' % (self.language.id, self.id)

# Register signals to make score updates happen automatically.
def denormalize_num_assertions(sender, instance, created=False, **kwargs):
    """
    Keep the num_assertions field up to date.
    """
    instance.concept1.update_num_assertions()
    instance.concept2.update_num_assertions()

## this one isn't actually necessary; redundant with Assertion.update_score
#models.signals.post_save.connect(denormalize_num_assertions, sender=Assertion)
models.signals.post_delete.connect(denormalize_num_assertions, sender=Assertion)

'''
class AssertionVote(models.Model):
    """
    A vote on an Assertion by a User.

    This is temporarily a view of the big Votes table:

    CREATE VIEW temp_assertion_votes AS
      SELECT id, user_id, object_id AS assertion_id, vote
        FROM votes WHERE content_type_id=68;
    """
    user         = models.ForeignKey(User)
    assertion    = models.ForeignKey(Assertion)
    vote         = models.SmallIntegerField(choices=SCORES)

    class Meta:
        db_table = 'temp_assertion_votes'
'''

class RawAssertion(TimestampedModel, ScoredModel):
    """
    A RawAssertion represents the connection between an :class:`Assertion` and
    natural language. Where an Assertion describes a :class:`Relation` between
    two :class:`Concepts`, a RawAssertion describes a sentence :class:`Frame`
    that connects the :class:`SurfaceForms` of those concepts.
    
    A RawAssertion also represents how a particular :class:`Sentence` can
    be interpreted to make an Assertion. :attr:`surface1` and :attr:`surface2`
    generally come from chunks of a sentence that someone entered into Open
    Mind.
    """
    sentence = models.ForeignKey(Sentence, null=True)
    assertion = models.ForeignKey(Assertion, null=True)
    creator = models.ForeignKey(User)
    surface1 = models.ForeignKey(SurfaceForm, related_name='left_rawassertion_set')
    surface2 = models.ForeignKey(SurfaceForm, related_name='right_rawassertion_set')
    frame = models.ForeignKey(Frame)    
    #batch = models.ForeignKey(Batch, null=True)
    language = models.ForeignKey(Language)
    score = models.IntegerField(default=0)
    votes = generic.GenericRelation(Vote)

    class Meta:
        unique_together = ('surface1', 'surface2', 'frame', 'language')
    
    @property
    def relation(self): return self.frame.relation
    @property
    def text1(self): return self.surface1.text
    @property
    def text2(self): return self.surface2.text
    
    def __unicode__(self):
        return u"%(language)s: ('%(text1)s' %(relation)s '%(text2)s') s=%(score)d" % dict(
            language=self.language.id, relation=self.relation.name,
            text1=self.text1, text2=self.text2, score=self.score)

    def nl_repr(self, wrap_text=lambda assertion, text: text):
        """Reconstruct the natural language representation.
        The text concepts are passed to the wrap_text function to
        allow a view to wrap them in a link (or do any other
        transformation.) The prototype for wrap_text is
        :samp:`wrap_text({assertion}, {text})`,
        where *assertion* is this RawAssertion object and *text* is the
        natural-language text of the concept (text1 or text2)."""

        text1 = wrap_text(self, self.surface1.text.strip())
        text2 = wrap_text(self, self.surface2.text.strip())
        return self.frame.fill_in(text1, text2)
        
    def main_sentence(self):
        return self.sentence
        #return self.sentences.all()[0]

    def surface(self, idx):
        """Get either surface1 or surface2, depending on the (1-based) idx."""
        if idx == 1: return self.surface1
        elif idx == 2: return self.surface2
        else: raise KeyError(idx)
    
    def correct_assertion(self, frame, surf1, surf2):
        self.frame = frame
        self.surface1 = surf1
        self.surface2 = surf2
        return self.update_assertion()

    def update_assertion(self):
        """
        Update the connection between this RawAssertion and its Assertion,
        if a Frame or SurfaceForm has changed.
        """
        try:
            matching = Assertion.objects.get(
                concept1=self.surface1.concept,
                concept2=self.surface2.concept,
                relation=self.frame.relation,
                frequency=self.frame.frequency
            )
            if matching is self.assertion:
                # Nothing to be done
                print '  no-op: tried to merge assertion with itself'
                return self.assertion
            # There's an assertion like this already. Merge the two assertions.
            print '  merging assertions'
            print '    '+str(matching)
            for vote in self.assertion.votes.all():
                nvotes = Vote.objects.filter(user=vote.user,
                object_id=matching.id)
                if nvotes == 0:
                    vote.object = matching
                    vote.save()
            self.assertion.update_score()
            self.assertion = matching
            self.assertion.update_score()
            self.save()
            return self.assertion
        except Assertion.DoesNotExist:
            # We can do this just by updating the existing assertion.
            self.assertion.concept1 = self.surface1.concept
            self.assertion.concept2 = self.surface2.concept
            self.assertion.relation = self.frame.relation
            self.assertion.save()
            return self.assertion
    
    @staticmethod
    def make(user, frame, text1, text2, activity, vote=1):
        """
        Create a RawAssertion and a corresponding :class:`Assertion`
        and :class:`Sentence` from user input. Assign votes appropriately.
        
        Requires the following arguments:
        
        - *user*: The user to credit the new assertion to.
        - *frame*: The :class:`Frame` that is being filled in.
        - *text1*: A string filling the first slot of the frame.
        - *text2*: A string filling the second slot of the frame.
        - *activity*: The event that produced this assertion.
        - *vote*: The user's vote on the assertion (often +1, but -1 can occur
          when the user is answering "no" to a question that has not been
          answered before).
        """
        assert text1 != text2
        lang = frame.language
        surface1 = SurfaceForm.get(text1, lang, auto_create=True)
        surface2 = SurfaceForm.get(text2, lang, auto_create=True)
        
        existing = RawAssertion.objects.filter(
            frame=frame,
            surface1=surface1,
            surface2=surface2,
            language=lang
        )
        if len(existing) > 0:
            raw_assertion = existing[0]
        else:
            raw_assertion = RawAssertion.objects.create(
                frame=frame,
                surface1=surface1,
                surface2=surface2,
                language=lang,
                score=0,
                creator=user
            )
        
        assertion, c = Assertion.objects.get_or_create(
            relation=frame.relation,
            concept1=surface1.concept,
            concept2=surface2.concept,
            frequency=frame.frequency,
            language=lang,
            defaults=dict(score=0)
        )
        if c: assertion.save()
        raw_assertion.assertion = assertion
        
        sentence, c = Sentence.objects.get_or_create(
            text=frame.fill_in(text1, text2),
            creator=user,
            language=lang,
            activity=activity,
            defaults=dict(score=0)
        )
        if c:
            lang.sentence_count += 1
            lang.save()
            sentence.save()
        
        Event.record_event(sentence, user, activity)
        sentence.set_rating(user, vote, activity)
        raw_assertion.set_rating(user, vote, activity)
        Event.record_event(raw_assertion, user, activity)
        assertion.set_rating(user, vote, activity)
        Event.record_event(assertion, user, activity)
        
        raw_assertion.sentence = sentence
        raw_assertion.update_score()
        raw_assertion.save()
        return raw_assertion
    
    def update_score(self):
        if self.assertion is not None:
            self.assertion.update_raw_cache()
        ScoredModel.update_score(self)
    
    def get_absolute_url(self):
        return '/%s/statement/%s/' % (self.language.id, self.id)
        
    class Meta:
        ordering = ['-score']
'''
class RawAssertionVote(models.Model):
    """
    A vote on an RawAssertion by a User.

    This is temporarily a view of the big Votes table:

    CREATE VIEW temp_rawassertion_votes AS
      SELECT id, user_id, object_id AS assertion_id, vote
        FROM votes WHERE content_type_id=66;
    """
    user          = models.ForeignKey(User)
    rawassertion = models.ForeignKey(RawAssertion)
    vote          = models.SmallIntegerField(choices=SCORES)

    class Meta:
        db_table = 'temp_rawassertion_votes'
'''

########NEW FILE########
__FILENAME__ = network
"""
Tools for working with ConceptNet as a generalized semantic network.

Requires the NetworkX library.
"""
import networkx as nx
import codecs
from conceptnet.models import Assertion

def make_network(lang):
    """
    Get the ConceptNet network for a particular language. It takes one
    parameter, which is `lang`, the language ID as a string.
    """
    assertions = Assertion.useful.filter(language__id=lang)
    graph = nx.MultiDiGraph()
    for text1, text2, rel, score, freq in assertions.values_list(
        'concept1__text', 'concept2__text', 'relation__name', 'score',
        'frequency__value').iterator():
        if text1 and text2 and text1 != text2:
            graph.add_edge(text1, text2, rel=rel, score=score, freq=freq)
    return graph

def export_gml(lang, filename):
    f = codecs.open(filename, 'w', encoding='utf-7')
    graph = make_network(lang)
    nx.write_gml(graph, f)
    f.close()

def export_edgelist(lang, filename):
    f = codecs.open(filename, 'w', encoding='utf-8')
    graph = make_network(lang)
    nx.write_edgelist(graph, f, data=True, delimiter='\t')
    f.close()


########NEW FILE########
__FILENAME__ = backends
from django.contrib.auth.models import User as DjangoUser, check_password
from conceptnet.pseudo_auth.models import LegacyUser

class LegacyBackend:
    def authenticate(self, username=None, password=None):
        try:
            # Load user object
            u = LegacyUser.objects.get(username=username)

            # Abort if Django should handle this
            if u.password.startswith('sha1$'): return None
            salt = u.salt

            # Build Django-compatible password string
            enc_password = 'sha1$--' + u.salt + '--$' + u.password

            # Check password
            if check_password(password+'--',enc_password):
                # Migrate them to new passwords.
                u.salt = None
                u.save()
                user = self.get_user(u.id)
                user.set_password(password)
                user.save()
                return user
        except LegacyUser.DoesNotExist:
            return None

        # Operation Complete!
        return None

    def get_user(self, user_id):
        try:
            return DjangoUser.objects.get(pk=user_id)
        except DjangoUser.DoesNotExist:
            return None

########NEW FILE########
__FILENAME__ = models
from django.db import models

class LegacyUser(models.Model):
    username = models.CharField(max_length=30)
    password = models.CharField(max_length=128)
    salt = models.CharField(max_length=128,null=True)

    def __unicode__(self):
        return self.username
    class Meta:
        db_table = 'auth_user'

########NEW FILE########
__FILENAME__ = docs
from conceptnet.models import *
from piston.handler import BaseHandler
from piston.doc import generate_doc
from conceptnet.webapi import handlers

from django.test.client import Client
from django.shortcuts import render_to_response
from django.template import RequestContext, Context, loader
from django.http import HttpResponse

from docutils.core import publish_string

API_BASE = 'http://openmind.media.mit.edu'

client = Client()
def documentation_view(request):
    docs = []
    for klass in handlers.__dict__.values():
        if isinstance(klass, type) and issubclass(klass, BaseHandler):
            doc = generate_doc(klass)
            if doc.get_resource_uri_template():
                doc.useful_methods = [m for m in doc.get_all_methods() if m.get_doc()]
                if hasattr(klass, 'example_args'):
                    args = klass.example_args
                    example_url = doc.get_resource_uri_template()
                    for arg, value in args.items():
                        example_url = example_url.replace('{%s}' % arg, str(value))
                    doc.example_url = example_url+'query.yaml'
                    doc.example_result = client.get(doc.example_url).content
                doc.uri_template = doc.get_resource_uri_template()
                docs.append(doc)
            elif hasattr(klass, 'example_uri'):
                doc = generate_doc(klass)
                example_url = klass.example_uri
                doc.example_url = example_url+'query.yaml'
                doc.example_result = client.get(doc.example_url).content
                doc.uri_template = klass.example_uri_template
                docs.append(doc)
    docs.sort(key=lambda doc: doc.uri_template)
    t = loader.get_template('documentation.txt')
    rst = t.render(Context({'docs': docs, 'API_BASE': API_BASE}))
    return HttpResponse(rst, mimetype='text/plain')

########NEW FILE########
__FILENAME__ = handlers
from piston.handler import BaseHandler, rc
from piston.doc import generate_doc
from piston.utils import throttle
from piston.authentication import HttpBasicAuthentication
from conceptnet.models import Concept, Relation, SurfaceForm, Frame,\
  Assertion, RawAssertion, LeftFeature, RightFeature, Feature
from conceptnet.corpus.models import Language, Sentence
from conceptnet.corpus.models import Frequency
from voting.models import Vote
from events.models import Activity
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from functools import wraps

BASE = "http://openmind.media.mit.edu/"
basic_auth = HttpBasicAuthentication()

class LanguageHandler(BaseHandler):
    """
    A GET request to this URL will show basic information about a language --
    its ID and how many sentences (parsed or unparsed) exist in the database
    for that language.

    The sentence count is a cached value. It might become out of sync with the
    actual number of sentences, but it's not supposed to.
    """
    allowed_methods = ('GET',)
    model = Language
    fields = ('id',)
    
    @throttle(600, 60, 'read')
    def read(self, request, lang):
        try:
            lang = Language.get(lang)
            return {'id': lang.id, 'sentence_count': lang.sentence_count}
        except Language.DoesNotExist:
            return rc.NOT_FOUND

    # This is how you make examples for things that don't announce their own
    # resource_uri.
    example_uri = '/api/ja/'
    example_uri_template = '/api/{lang}/'

class RelationHandler(BaseHandler):
    allowed_methods = ()
    model = Relation
    fields = ('name',)

def concept_lookup(concept, lang):
    return Concept.get_raw(concept, lang)

def check_authentication(request):
    user = None
    if 'username' in request.POST:
        user = authenticate(username=request.POST['username'],
                            password=request.POST['password'])
    elif 'username' in request.PUT:
        user = authenticate(username=request.PUT['username'],
                            password=request.PUT['password'])
    if user is not None and user.is_active:
        login(request, user)
    else:
        return basic_auth.challenge()

class ConceptHandler(BaseHandler):
    """
    A GET request to this URL will look up a Concept in ConceptNet.
    
    It may not be especially useful to use this query directly, as most of
    the information it gives you back is the information you needed to look it
    up in the first place. However, you can use this to test for a concept's
    existence, and this URL is a base for more interesting queries on concepts.
    """

    allowed_methods = ('GET',)
    model = Concept
    fields = ('text', 'language', 'canonical_name')
    
    @throttle(600, 60, 'read')
    def read(self, request, lang, concept):        
        try:
            return concept_lookup(concept, lang)
        except Concept.DoesNotExist:
            return rc.NOT_FOUND
    
    @staticmethod
    def resource_uri(*args):
        return ('concept_handler', ['language_id', 'text'])
    example_args = {'lang': 'en', 'concept': 'duck'}

class ConceptAssertionHandler(BaseHandler):
    """
    A GET request to this URL will look up all the
    :class:`Assertions <conceptnet.models.Assertion>` that this
    Concept participates in with a score of at least 1.
    
    The results will be limited to the *n* highest-scoring assertions.
    By default, this limit is 20, but you can set it up to 100 by changing
    the *limit* in the URL.
    """
    allowed_methods = ('GET',)

    @throttle(200, 60, 'search')
    def read(self, request, lang, concept, limit=20):
        limit = int(limit)
        if limit > 100: limit = 100
        try:
            return concept_lookup(concept, lang).get_assertions()[:limit]
        except Concept.DoesNotExist:
            return rc.NOT_FOUND

    @staticmethod
    def resource_uri(*args):
        return ('concept_assertion_handler', ['language_id', 'concept', 'limit'])
    example_args = {'lang': 'en', 'concept': 'web%20foot', 'limit': 5}

class ConceptSurfaceHandler(BaseHandler):
    """
    A GET request to this URL will look up all the
    :class:`SurfaceForms <conceptnet.models.SurfaceForm>` that
    correspond to this Concept -- that is, the phrases of natural language
    that are considered to reduce to this Concept.
    
    The results will be limited to *n* surface forms.
    By default, this limit is 20, but you can set it up to 100 by adding
    `limit:n/` to the URI.
    """
    allowed_methods = ('GET',)

    @throttle(200, 60, 'search')
    def read(self, request, lang, concept, limit=20):
        limit = int(limit)
        if limit > 100: limit = 100
        try:
            return concept_lookup(concept, lang).surfaceform_set.all()[:limit]
        except Concept.DoesNotExist:
            return rc.NOT_FOUND

    @staticmethod
    def resource_uri(*args):
        return ('concept_surface_handler', ['language_id', 'concept', 'limit'])
    example_args = {'lang': 'en', 'concept': 'web%20foot', 'limit': 5}

class FeatureHandler(BaseHandler):
    model = Feature
    fields = ('direction', 'relation', 'concept')

    @staticmethod
    def relation_form(lang, dir, relation_name, concept_name):
        return {'direction': dir,
                'relation': {'name': relation_name},
                'resource_uri': "/api/%(lang)s/%(dir)sfeature/%(relation_name)s/%(concept_name)s/" % locals()}

class ConceptFeatureHandler(BaseHandler):
    """
    A GET request to this URL will return a list of all existing
    :class:`Features <conceptnet.models.Features>` built on the given
    :class:`Concept <conceptnet.models.Concept>`.

    The features will be described in a short form: each feature will be a
    dictionary containing its *direction*, the *relation* involved, and the
    *resource_uri* for looking up more information about that feature. The
    concept will be omitted from each feature, because you already know it.
    """

    @throttle(600, 60, 'read')
    def read(self, request, lang, concept):
        try:
            concept = concept_lookup(concept, lang)
        except Concept.DoesNotExist:
            return rc.NOT_FOUND
        left_rels = Assertion.objects.filter(concept1=concept).order_by('relation').values_list('relation__name').distinct()
        right_rels = Assertion.objects.filter(concept2=concept).order_by('relation').values_list('relation__name').distinct()
        
        text = concept.text
        left_repr = [FeatureHandler.relation_form(lang, 'left', rel[0], text) for rel in left_rels]
        right_repr = [FeatureHandler.relation_form(lang, 'right', rel[0], text) for rel in right_rels]
        
        return left_repr + right_repr

    @staticmethod
    def resource_uri(*args):
        return ('concept_feature_handler', ['language_id', 'text'])
    example_args = {'lang': 'en', 'concept': 'moose'}

class FeatureQueryHandler(BaseHandler):
    """
    A GET request to this URL will look up the
    :class:`Assertions <conceptnet.models.Assertion>` that contain a
    certain :class:`Feature <conceptnet.models.Feature>`.
    
    The parameter "{dir}feature" means that the URL should contain either
    `leftfeature/` or `rightfeature/`, depending on what form of feature
    you are looking for. See the :class:`Feature <conceptnet.models.Feature>`
    documentation for more explanation.
    
    As with other queries that return a
    list, this returns 20 results by default, but you may ask for up to 100
    by changing the value of *limit*.
    """
    allowed_methods = ('GET',)

    @throttle(600, 60, 'read')
    def read(self, request, lang, dir, relation, concept, limit=20):
        limit = int(limit)
        if limit > 100: limit=20
        try:
            relation = Relation.objects.get(name=relation)
            concept = concept_lookup(concept, lang)
        except Relation.DoesNotExist:
            return rc.NOT_FOUND
        except Concept.DoesNotExist:
            return rc.NOT_FOUND
        
        if dir == 'left': fclass = LeftFeature
        elif dir == 'right': fclass = RightFeature
        else: return rc.NOT_FOUND
        
        feature = fclass(relation, concept)
        return feature.matching_assertions()[:limit]

    @staticmethod
    def resource_uri(*args):
        return ('feature_query_handler', ['language_id', 'dir', 'relation', 'concept', 'limit'])
    example_args = {'lang': 'en', 'dir': 'right', 'relation': 'HasA',
                    'concept': 'web%20foot', 'limit': 5}

class FrequencyHandler(BaseHandler):
    """
    A GET request to this URL will look up a Frequency modifier by name in
    ConceptNet's natural language module. Each Frequency has a value from
    -10 to 10, so for example, you can use this to determine that
    the English modifier "sometimes" has a value of 4 in ConceptNet.
    """
    
    allowed_methods = ('GET',)
    model = Frequency
    fields = ('text', 'value', 'language')
    
    @throttle(600, 60, 'read')
    def read(self, request, lang, text):
        try:
            return Frequency.objects.get(text=text, language__id=lang)
        except Frequency.DoesNotExist: return rc.NOT_FOUND
    
    @staticmethod
    def resource_uri(*args):
        return ('frequency_handler', ['language_id', 'text'])
    example_args = {'lang': 'en', 'text': 'sometimes'}

class SurfaceFormHandler(BaseHandler):
    """
    A GET request to this URL will look up a SurfaceForm in ConceptNet. The
    SurfaceForm must represent a phrase that someone has used at some point
    on ConceptNet.
    """

    allowed_methods = ('GET',)
    model = SurfaceForm
    fields = ('text', 'concept', 'residue', 'language')
    
    @throttle(600, 60, 'read')
    def read(self, request, lang, text):
        try:
            return SurfaceForm.get(text, lang)
        except SurfaceForm.DoesNotExist: return rc.NOT_FOUND

    @staticmethod
    def resource_uri(*args):
        return ('surface_form_handler', ['language_id', 'text'])
    example_args = {'lang': 'en', 'text': 'have%20webbed%20feet'}

class FrameHandler(BaseHandler):
    """
    A GET request to this URL will look up a sentence frame in a particular
    language, given its ID.
    
    This ID will appear in URLs of other objects,
    such as RawAssertions, that refer to this Frame.
    """
    allowed_methods = ('GET',)
    model = Frame
    fields = ('text', 'relation', 'frequency', 'goodness', 'language')
    
    @throttle(600, 60, 'read')
    def read(self, request, lang, id):
        try:
            return Frame.objects.get(id=id, language__id=lang)
        except Frame.DoesNotExist:
            return rc.NOT_FOUND

    @staticmethod
    def resource_uri(*args):
        return ('frame_handler', ['language_id', 'id'])
    example_args = {'lang': 'en', 'id': '7'}

class AssertionHandler(BaseHandler):
    """
    A GET request to this URL returns information about the Assertion with
    a particular ID.
    
    This ID will appear in URLs of other objects,
    such as RawAssertions, that refer to this Assertion.
    """
    allowed_methods = ('GET',)
    model = Assertion
    fields = ('relation', 'concept1', 'concept2', 'frequency', 'score',
    'language')
    
    def read(self, request, lang, id):
        try:
            a = Assertion.objects.get(
              id=id, language__id=lang
            )
            return a
        except Assertion.DoesNotExist:
            return rc.NOT_FOUND

    @staticmethod
    def resource_uri(*args):
        return ('assertion_handler', ['language_id', 'id'])
    example_args = {'lang': 'en', 'id': '25'}

class AssertionToRawHandler(BaseHandler):
    """
    A GET request to this URL will list the RawAssertions (natural language
    statements) associated with a given Assertion ID.
    """
    @throttle(200, 60, 'search')
    def read(self, request, lang, id):
        raw_list = RawAssertion.objects.filter(language__id=lang, assertion__id=id)
        return raw_list

    @staticmethod
    def resource_uri(*args):
        return ('assertion_to_raw_handler', ['language_id', 'assertion_id'])
    example_args = {'lang': 'en',
                    'id': 31445}

class AssertionFindHandler(BaseHandler):
    """
    A GET request to this URL will return an Assertion
    given the text of its two concepts and its relation.

    - `relation` is the name of the relation.
    - `text1` is the text of the first concept.
    - `text2` is the text of the second concept.
    
    The concept text can actually be any surface form that normalizes to that
    concept.

    If such an assertion exists, it will be returned. If not, you will get a
    404 response. You can use this to find out whether the assertion exists or
    not.
    """

    allowed_methods = ('GET',)

    @throttle(200, 60, 'search')
    def read(self, request, lang, relation, text1, text2):
        try:
            concept1 = concept_lookup(text1, lang)
            concept2 = concept_lookup(text2, lang)
            relation = Relation.objects.get(name=relation)
        except Concept.DoesNotExist:
            return rc.NOT_FOUND
        except Relation.DoesNotExist:
            return rc.NOT_FOUND

        assertion = Assertion.objects.filter(concept1=concept1, concept2=concept2, relation=relation).order_by('relation').distinct()

        return assertion


        
    @staticmethod
    def resource_uri(*args):
        return ('assertion_find_handler', ['language_id', 'relation', 'text1', 'text2'])
    example_args = {'lang': 'en', 'relation': 'IsA', 'text1': 'dog', 'text2': 'animal'}

        
class RatedObjectHandler(BaseHandler):
    """
    A GET request to this URL will look up an object that can be voted on
    by users, and show how users have voted on it.
    
    The "type" parameter should either be 'assertion', 'raw_assertion', or
    'sentence', and the "id" should be an object's ID within that type.
    
    This request will return a structure containing the object itself, its
    type, and its list of votes.
    
    A POST request to this URL lets you vote on the object, by supplying
    the parameter `vote` with a value of 1 or -1. You must either have a
    logged-in cookie or send `username` and `password` as additional parameters.
    
    Other optional parameters:
    
    * `activity`: a string identifying what activity or application this
      request is coming from.
    """
    allowed_methods = ('GET', 'POST')
    
    classes = {
        'assertion': Assertion,
        'raw_assertion': RawAssertion,
        'statement': RawAssertion,
        'sentence': Sentence
    }
    
    @throttle(600, 60, 'read')
    def read(self, request, type, lang, id):
        try:
            theclass = RatedObjectHandler.classes[type]
        except KeyError:
            return rc.NOT_FOUND
        try:
            theobj = theclass.objects.get(
                id=id, language__id=lang
            )
            return {'type': type,
                    type: theobj,
                    'votes': theobj.votes.all()}
        except theclass.DoesNotExist:
            return rc.NOT_FOUND

    @throttle(600, 60, 'vote')
    def create(self, request, type, lang, id):
        check_authentication(request)
        try:
            theclass = RatedObjectHandler.classes[type]
        except KeyError:
            return rc.NOT_FOUND
        try:
            theobj = theclass.objects.get(
                id=id, language__id=lang
            )
            user = request.user
            val = int(request.POST['value'])
            activity = Activity.get(request.POST.get('activity', 'Web API'))
            theobj.set_rating(user, val, activity)
            return {'type': type,
                    type: theobj,
                    'votes': theobj.votes.all(),
                    }
        except theclass.DoesNotExist:
            return rc.NOT_FOUND
        except (KeyError, ValueError):
            return rc.BAD_REQUEST

    @staticmethod
    def resource_uri(*args):
        return ('rated_object_handler', ['type', 'language_id', 'id'])
    example_args = {'type': 'assertion', 'lang': 'en', 'id': '25'}

class VoteHandler(BaseHandler):
    allowed_methods = ()
    model = Vote
    fields = ('user', 'vote')

class UserHandler(BaseHandler):
    """
    **Checking users**: A GET request to this URL will confirm whether a user
    exists. If the user exists, this returns a data structure containing their
    username. If the user does not exist, it returns a 404 response.

    **Creating users**: A POST request to this URL will create a user that does
    not already exist. This takes two additional POST parameters:

    - `password`: The password the new user should have.
    - `email`: (Optional and not very important) The e-mail address to be
      associated with the user in the database.

    Do not use high-security passwords here. You're sending them over plain
    HTTP, so they are not encrypted.
    """
    allowed_methods = ('GET', 'POST')
    model = User
    fields = ('username',)

    @throttle(600, 60, 'read')
    def read(self, request, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return rc.NOT_FOUND

    @throttle(200, 60, 'add')
    def create(self, request, username):
        password = request.POST['password']
        email = request.POST.get('email', '')
        exists = User.objects.filter(username=username).count()
        if exists > 0:
            return rc.DUPLICATE_ENTRY
        else:
            return User.objects.create_user(username, email, password)

    example_uri = '/api/user/verbosity/'
    example_uri_template = '/api/user/{username}/'

class RawAssertionHandler(BaseHandler):
    """
    A GET request to this URL returns information about the RawAssertion
    with a particular ID. This includes the Sentence and Assertion that it
    connects, if they exist.
    """
    allowed_methods = ('GET',)
    model = RawAssertion
    fields = ('frame', 'surface1', 'surface2', 'creator', 'sentence',
              'assertion', 'created', 'updated', 'language', 'score')

    @throttle(600, 60, 'read')
    def read(self, request, lang, id):
        try:
            r = RawAssertion.objects.get(
              id=id, language__id=lang
            )
            return r
        except RawAssertion.DoesNotExist:
            return rc.NOT_FOUND

    @staticmethod
    def resource_uri(*args):
        return ('raw_assertion_handler', ['language_id', 'id'])
    example_args = {'lang': 'en', 'id': '26'}
    
class RawAssertionByFrameHandler(BaseHandler):
    """
    **Getting assertions**: A GET request to this URL lists the RawAssertions
    that use a particular
    sentence frame, specified by its ID. As with other queries that return a
    list, this returns 20 results by default, but you can ask for up to 100
    by changing the value of *limit*.
    
    **Adding assertions**: A POST request to this URL submits new knowledge to
    Open Mind. The
    POST parameters `text1` and `text2` specify the text that fills the blanks.
    
    You must either have a logged-in cookie or send `username` and
    `password` as additional parameters.
    
    Other optional parameters:

    - `activity`: a string identifying what activity or application this
      request is coming from.
    - `vote`: either 1 or -1. This will vote for or against the assertion after
      you create it, something you often want to do.
    """
    allowed_methods = ('GET', 'POST')
    @throttle(200, 60, 'search')
    def read(self, request, lang, id, limit=20):
        limit = int(limit)
        if limit > 100: limit = 100
        try:
            return Frame.objects.get(id=id, language__id=lang).rawassertion_set.all()[:limit]
        except Frame.DoesNotExist:
            return rc.NOT_FOUND

    @throttle(200, 60, 'add')
    def create(self, request, lang, id, limit=None):
        check_authentication(request)
        try:
            frame = Frame.objects.get(id=id, language__id=lang)
        except Frame.DoesNotExist:
            return rc.NOT_FOUND
        
        user = request.user
        activity = Activity.get(request.POST.get('activity', 'Web API'))
        text1 = request.POST['text1']
        text2 = request.POST['text2']
        vote = int(request.POST.get('vote', 1))
        raw = RawAssertion.make(user, frame, text1, text2, activity, vote)
        return raw

    @staticmethod
    def resource_uri(*args):
        return ('raw_assertion_by_frame_handler', ['language_id', 'id', 'limit'])

class SentenceHandler(BaseHandler):
    allowed_methods = ()
    model = Sentence
    fields = ('text', 'creator', 'language', 'score', 'created_on')

import divisi2
import numpy as np
assoc_matrix = divisi2.network.conceptnet_assoc('en')
assocU, assocS, assocV = assoc_matrix.normalize_all().svd(k=150)
assocmat = assocU.multiply(np.exp(assocS)).normalize_rows(offset=.00001)

class SimilarityHandler(BaseHandler):
    """
    A GET request to this URL will take in a comma-separated list of concept
    names, and return a list of concepts that are the most similar.
    The concept names can have underscores that are translated
    to spaces, and @ signs that indicate a weight. For example:

        /api/en/similar_to/dog,cat,mouse@0.5,guinea_pig/limit:10
    
    The first argument is the language, and the second argument is the list
    of terms. The language must currently be 'en'.
    """
    allowed_methods = ('GET',)

    @throttle(60, 60, 'read')
    def read(self, request, lang, termlist, limit=20):
        limit = int(limit)
        if limit > 100: limit=20
        terms = []
        try:
            term_pieces = termlist.split(',')
            for piece in term_pieces:
                if '@' in piece:
                    term, weight = piece.split('@')
                    weight = float(weight)
                else:
                    term = piece
                    weight = 1.
                term = term.replace('_', ' ')
                terms.append((term, weight))
        except ValueError:
            return rc.BAD_REQUEST
        
        vec = divisi2.DenseVector(np.zeros((150,)))
        for term, weight in terms:
            if term in assocmat.row_labels:
                vec += assocmat.row_named(term) * weight
        similar = assocmat.dot(vec)
        top_items = similar.top_items(limit)

        results = []
        for concept, score in top_items:
            if score > 0:
                result = {
                    'concept': Concept.objects.get(text=concept, language__id='en'),
                    'score': float(score)
                }
                results.append(result)
        return results

    @staticmethod
    def resource_uri(*args):
        return ('similarity_handler', ['language_id', 'termlist', 'limit'])
    
    example_args = {'lang': 'en', 'termlist': 'dog,cat,mouse@0.5,guinea_pig', 'limit': '10'}
    


########NEW FILE########
__FILENAME__ = rest_client
"""
`rest_client.py`_ is a simple client for interacting with ConceptNet 4's REST
API.

.. _`rest_client.py`: http://openmind.media.mit.edu/media/rest_client.py

This client is not object-oriented. The data structures you work with are
dictionaries, of the form described in the API documentation. The main function
:func:`lookup` can be used to look up many different kinds of data. There are
also convenience functions for performing common operations on this data.

If you want to know what fields are contained in these dictionaries, read
the REST API documentation at
http://csc.media.mit.edu/docs/conceptnet/webapi.html#rest-requests .
"""

import urllib, urllib2

try:
    import json
except:
    import simplejson as json

SERVER_URL = 'http://openmind.media.mit.edu'
API_URL = 'http://openmind.media.mit.edu/api/'
CLIENT_VERSION = '1'

def lookup(type, language, key):
    """
    Get an object of a certain *type*, specified by the code for what
    *language* it is in and its *key*. The types currently supported are:

        `assertion`
            Use the `id` as the key.
        `concept`
            Use the concept's raw name as the key.
        `frame`
            Use the `id` as the key.
        `frequency`
            Use the adverb text as the key. For the default frequency, this
            will be the null string.
        `raw_assertion`
            Use the `id` as the key.
        `surface`
            A SurfaceForm. Use the text as the key.
        `leftfeature`
            This will return a list of assertions with a specified left
            feature. The key takes the form `relation/concept`. For example,
            the key `PartOf/wheel` looks up all assertions saying a wheel is
            part of something.
        `rightfeature`
            This, similarly, returns a list of assertions with a specified
            right feature. The key takes the form `relation/concept`. For
            example, the key `PartOf/car` looks up all assertions that say
            something is part of a car.
    
    The object will be returned as a dictionary, or in the case of features,
    a list.
    """
    return _get_json(language, type, key)

def lookup_concept_raw(language, concept_name):
    """
    Look up a Concept by its language and its raw name. For example,
    `lookup_concept_raw('en', 'webbed feet')` will get no results, but
    `lookup_concept_raw('en', 'web foot')` will.

    Use :func:`lookup_concept_from_surface` to look up a concept from an
    existing surface text, such as "webbed feet".

    Use :func:`lookup_concept_from_nl` to look up a concept from any natural
    language text. This requires the `simplenlp` module.
    """
    return lookup('concept', language, concept_name)

def lookup_concept_from_surface(language, surface_text):
    """
    Look up a concept, given a surface form of that concept that someone has
    entered into Open Mind. For example,
    `lookup_concept_from_surface('en', 'webbed feet')` will return the concept
    'web foot'.
    """
    surface = lookup('surface', language, surface_text)
    return surface['concept']

def lookup_concept_from_nl(language, text):
    """
    Look up a concept using any natural language text that represents it.
    This function requires the :mod:`simplenlp` module
    to normalize natural language text into a raw concept name.
    """
    import simplenlp
    nltools = simplenlp.get('en')

    normalized = nltools.normalize(text)
    return lookup_concept_raw(language, normalized)

def assertions_for_concept(concept, direction='all', limit=20):
    """
    Given a dictionary representing a concept, look up the assertions it
    appears in.

    By default, this returns all matching assertions. By setting the
    optional argument `direction` to "forward" or "backward", you can restrict
    it to only assertions that have that concept on the left or the right
    respectively.

    You may set the limit on the number of results up to 100. The default is
    20. This limit is applied before results are filtered for forward or
    backward assertions.
    """
    def assertion_filter(assertion):
        if direction == 'all': return True
        elif direction == 'forward':
            return assertion['concept1']['text'] == concept['text']
        elif direction == 'backward':
            return assertion['concept2']['text'] == concept['text']
        else:
            raise ValueError("Direction must be 'all', 'forward', or 'backward'")
        
    assertions = _refine_json(concept, 'assertions', 'limit:%d' % limit)
    return [a for a in assertions if assertion_filter(a)]

def surface_forms_for_concept(concept, limit=20):
    """
    Given a dictionary representing a concept, get a list of its surface
    forms (also represented as dictionaries).

    You may set the limit on the number of results up to 100. The default is
    20.
    """
    return _refine_json(concept, 'surfaceforms', 'limit:%d' % limit)

def votes_for(obj):
    """
    Given a dictionary representing any object that can be voted on -- such as
    an assertion or raw_assertion -- get a list of its votes.
    """
    return _refine_json(obj, 'votes')

def similar_to_concepts(concepts, limit=20):
    """
    `concepts` is a list of concept names or (concept name, weight) pairs.
    Given this, `similar_to_concepts` will find the `limit` most related
    concepts.

    These similar concepts are returned in dictionaries of the form:

        {'concept': concept, 'score': score}

    where `concept` is the data structure for a concept.
    """
    pieces = []
    for entry in concepts:
        if isinstance(entry, tuple):
            concept, weight = entry
        else:
            concept = entry
            weight = 1.
        if hasattr(concept, 'text'):
            concept = concept.text
        concept = concept.replace(' ', '_').encode('utf-8')
        pieces.append("%s@%s" % (concept, weight))
    termlist = ','.join(pieces)
    limitstr = 'limit:%d' % limit
    return _get_json('en', 'similar_to', termlist, limitstr)

def add_statement(language, frame_id, text1, text2, username, password):
    """
    Add a statement to Open Mind, or vote for it if it is there.

    Requires the following parameters:
        
        language
            The language code, such as 'en'.
        frame_id
            The numeric ID of the sentence frame to use.
        text1
            The text filling the first blank of the frame.
        text2
            The text filling the second blank of the frame.
        username
            Your Open Mind username.
        password
            Your Open Mind password.
    
    Example: 
    >>> frame = lookup('frame', 'en', 7)
    >>> frame['text']
    '{1} is for {2}'
    
    >>> add_statement('en', 7, 'election day', 'voting', 'rspeer', PASSWORD)
    (Result: rspeer adds the statement "election day is for voting", which
    is also returned as a raw_assertion.)
    """
    return _post_json([language, 'frame', frame_id, 'statements'], {
        'username': username,
        'password': password,
        'text1': text1,
        'text2': text2
    })


def _get_json(*url_parts):
    url = API_URL + '/'.join(urllib2.quote(str(p)) for p in url_parts) + '/query.json'
    return json.loads(_get_url(url))

def _post_json(url_parts, post_parts):
    url = API_URL + '/'.join(urllib2.quote(str(p)) for p in url_parts) + '/query.json'
    postdata = urllib.urlencode(post_parts)
    req = urllib2.Request(url, postdata)
    response = urllib2.urlopen(req)
    return json.loads(response.read())

def _extend_url(old_url, *url_parts):
    url = old_url + '/'.join(urllib2.quote(str(p)) for p in url_parts) + '/'
    return json.loads(_get_url(url))

def _get_url(url):
    conn = urllib2.urlopen(url)
    return conn.read()

def _refine_json(old_obj, *parts):
    return _extend_url(SERVER_URL + old_obj['resource_uri'], *parts)


########NEW FILE########
__FILENAME__ = rst
from django.template.defaultfilters import stringfilter
from django import template

register = template.Library()

@stringfilter
def indent(value, spaces):
    indentation = ' '*int(spaces)
    return '\n'.join(indentation+line for line in value.split('\n')).strip()
register.filter('indent', indent)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from piston.resource import Resource
from conceptnet.webapi.docs import documentation_view
from conceptnet.webapi.handlers import *

# This gives a way to accept "query.foo" on the end of the URL to set the
# format to 'foo'. "?format=foo" works as well.
Q = r'(query\.(?P<emitter_format>.+))?$'

urlpatterns = patterns('',
    url(r'^(?P<lang>[^/]+)/'+Q,
        Resource(LanguageHandler), name='language_handler'),
    url(r'^(?P<lang>.+)/concept/(?P<concept>[^/]*)/'+Q,
        Resource(ConceptHandler), name='concept_handler'),
    url(r'^(?P<lang>.+)/concept/(?P<concept>[^/]*)/assertions/'+Q,
        Resource(ConceptAssertionHandler), name='concept_assertion_handler_default'),
    url(r'^(?P<lang>.+)/concept/(?P<concept>[^/]*)/assertions/limit:(?P<limit>[0-9]+)/'+Q,
        Resource(ConceptAssertionHandler), name='concept_assertion_handler'),
    url(r'^(?P<lang>.+)/concept/(?P<concept>[^/]*)/surfaceforms/'+Q,
        Resource(ConceptSurfaceHandler), name='concept_surface_handler_default'),
    url(r'^(?P<lang>.+)/concept/(?P<concept>[^/]*)/surfaceforms/limit:(?P<limit>[0-9]+)/'+Q,
        Resource(ConceptSurfaceHandler), name='concept_surface_handler'),
    url(r'^(?P<lang>.+)/concept/(?P<concept>[^/]*)/features/'+Q,
        Resource(ConceptFeatureHandler), name='concept_feature_handler'),
    url(r'^(?P<lang>.+)/(?P<dir>left|right)feature/(?P<relation>[^/]+)/(?P<concept>[^/]+)/'+Q,
        Resource(FeatureQueryHandler), name='feature_query_handler_default'),
    url(r'^(?P<lang>.+)/(?P<dir>left|right)feature/(?P<relation>[^/]+)/(?P<concept>[^/]+)/limit:(?P<limit>[0-9]+)/'+Q,
        Resource(FeatureQueryHandler), name='feature_query_handler'),
    url(r'^(?P<lang>.+)/(?P<type>.+)/(?P<id>[0-9]+)/votes/'+Q,
        Resource(RatedObjectHandler), name='rated_object_handler'),
    url(r'^(?P<lang>.+)/surface/(?P<text>.+)/'+Q,
        Resource(SurfaceFormHandler), name='surface_form_handler'),
    url(r'^(?P<lang>.+)/frame/(?P<id>[0-9]+)/'+Q,
        Resource(FrameHandler), name='frame_handler'),
    url(r'^(?P<lang>.+)/frame/(?P<id>[0-9]+)/statements/'+Q,
        Resource(RawAssertionByFrameHandler),
        name='raw_assertion_by_frame_handler_default'),
    url(r'^(?P<lang>.+)/frame/(?P<id>[0-9]+)/statements/limit:(?P<limit>[0-9]+)/'+Q,
        Resource(RawAssertionByFrameHandler),
        name='raw_assertion_by_frame_handler'),
    url(r'^(?P<lang>.+)/assertion/(?P<id>[0-9]+)/'+Q,
        Resource(AssertionHandler), name='assertion_handler'),
    url(r'^(?P<lang>.+)/assertion/(?P<id>[0-9]+)/raw/'+Q,
        Resource(AssertionToRawHandler), name='assertion_to_raw_handler'),
    url(r'^(?P<lang>.+)/raw_assertion/(?P<id>[0-9]+)/'+Q,
        Resource(RawAssertionHandler), name='raw_assertion_handler'),
    url(r'^(?P<lang>.+)/frequency/(?P<text>[^/]*)/'+Q,
        Resource(FrequencyHandler), name='frequency_handler'),
    url(r'^(?P<lang>.+)/assertionfind/(?P<relation>[^/]+)/(?P<text1>[^/]+)/(?P<text2>[^/]+)/'+Q,
        Resource(AssertionFindHandler), name='assertion_find_handler'),
    url(r'^user/(?P<username>.+)/'+Q,
        Resource(UserHandler), name='user_handler'),
    url(r'^(?P<lang>.+)/similar_to/(?P<termlist>[^/]+)/limit:(?P<limit>[0-9]+)/'+Q,
        Resource(SimilarityHandler), name='similarity_handler'),
    url(r'^(?P<lang>.+)/similar_to/(?P<termlist>[^/]+)/'+Q,
        Resource(SimilarityHandler), name='similarity_handler_default'),
    url(r'docs.txt$',
        documentation_view, name='documentation_view')
)
# :vim:tw=0:nowrap:

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# ConceptNet documentation build configuration file, created by
# sphinx-quickstart on Fri Feb 27 17:56:32 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
sys.path.append(os.path.abspath('..'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'ConceptNet'
copyright = u'2009, Commonsense Computing Initiative'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '3.5'
# The full version, including alpha/beta/rc tags.
release = '3.5pre'

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
exclude_trees = []

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

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

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'ConceptNetdoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'ConceptNet.tex', ur'ConceptNet Documentation',
   ur'Commonsense Computing Initiative', 'manual'),
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


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/dev': None}

########NEW FILE########
__FILENAME__ = assign_scores_pt
from csc.util import queryset_foreach
from csc.conceptnet4.models import Sentence, Assertion, RawAssertion, Language, Vote

pt = Language.get('pt')
def process(raw):
    if pt.nl.is_blacklisted(raw.surface1.text) or pt.nl.is_blacklisted(raw.surface2.text):
        raw.votes.delete()
    else:
        Vote.objects.record_vote(raw, raw.sentence.creator, 1)

queryset_foreach(RawAssertion.objects.filter(language=pt), process, batch_size=100)


########NEW FILE########
__FILENAME__ = check_best_frame
from csc.util import queryset_foreach
from csc.conceptnet4.models import Frame, Assertion, RawAssertion, SurfaceForm
from django.db import connection

def check_frame(assertion):
    try:
        assertion.best_frame
    except Frame.DoesNotExist:
        print "No frame for:", assertion
        assertion.best_frame = None
        assertion.save()
    
    try:
        assertion.best_raw
        assertion.best_surface1
        assertion.best_surface2
    except (RawAssertion.DoesNotExist, SurfaceForm.DoesNotExist):
        print "No raw assertion for:", assertion
        assertion.best_raw = None
        assertion.best_surface1 = None
        assertion.best_surface2 = None
        assertion.save()

queryset_foreach(Assertion.objects.all(), check_frame,
  batch_size=100)


########NEW FILE########
__FILENAME__ = compare_sentences
#!/usr/bin/env python

from csc.conceptnet.models import *
from csc.corpus.models import *
#from django.contrib.auth import *
from django.db import transaction

def check_polarity():
    for a in Assertion.objects.all().select_related('raw'):
        if a.polarity != a.raw.polarity:
            print a.sentence
            print a.raw.sentence
            print a
            print a.raw
            print a.rating_set.all()
            print

#check_polarity()

# conclusion: not worth fixing. The cases where they conflict are all generally
# ugly, but the raw assertions (which we're keeping) are closer to correct.
#
# other conclusion: do not use the old csamoa ratings.

def basically_the_same(s1, s2):
    def canonical(s):
        return s.replace('  ', ' ').strip('. ')
    return canonical(s1) == canonical(s2)

def check_raw_mistakes():
    for ra in RawAssertion.objects.all().select_related('sentence'):
        rawsent = ra.nl_repr()
        sent = ra.sentence.text
        if not basically_the_same(rawsent, sent):
            print ra
            print repr(rawsent)
            print repr(sent)
            print "batch:", ra.batch
            print "predicate:", ra.predicate
            print "frame:", ra.frame.id, ra.frame
            betterone = False
            for r2 in ra.sentence.rawassertion_set.all():
                if basically_the_same(rawsent, r2.nl_repr()):
                    betterone = True
                break
            if ra.predicate is None and betterone:
                print "This raw predicate should be deleted."
            print

@transaction.commit_on_success
def unswitch_raw():
    evilbatch = Batch.objects.get(id=136)
    for ra in RawAssertion.objects.filter(batch=evilbatch).select_related('frame'):
        if ra.predicate is None and ra.frame.id in [1384, 1387, 1420]:
            text1 = ra.text2
            text2 = ra.text1
            ra.text1 = text1
            ra.text2 = text2
            ra.save()
            print ra
            
unswitch_raw()
########NEW FILE########
__FILENAME__ = 000_is_for
from csc.conceptnet.models import *
from csc.util import foreach

target_frame = Frame.objects.get(language=en, relation__name='UsedFor', text='{1} is for {2}')

def queryset1():
    frame = Frame.objects.get(text='{1} is {2}', language=en, relation__name='HasProperty')
    got = RawAssertion.objects.filter(language=en, frame=frame)
    return got

def queryset2():
    frame = Frame.objects.get(text='{1} is {2}', language=en, relation__name='ReceivesAction')
    got = RawAssertion.objects.filter(language=en, frame=frame)
    return got

def fix_is_for(s):
    if s.surface2.text.startswith('for '):
        print s
        newsurf = SurfaceForm.get(s.surface2.text[4:], 'en', auto_create=True)
        print "=>",
        print s.correct_assertion(target_frame, s.surface1, newsurf)

foreach(queryset1(), fix_is_for)


########NEW FILE########
__FILENAME__ = 001_is_like
from csc.conceptnet.models import *
from csc.util import foreach

target_frame = Frame.objects.get(language=en, relation__name='ConceptuallyRelatedTo', text='{1} is like {2}')

def queryset():
    frame = Frame.objects.get(text='{1} is {2}', language=en, relation__name='HasProperty')
    got = RawAssertion.objects.filter(language=en, frame=frame)
    return got

def fix(s):
    if s.surface2.text.startswith('like '):
        print s
        newsurf = SurfaceForm.get(s.surface2.text[4:], 'en', auto_create=True)
        print "=>",
        print s.correct_assertion(target_frame, s.surface1, newsurf)

foreach(queryset(), fix)


########NEW FILE########
__FILENAME__ = 002_are_for
from csc.conceptnet.models import *
from csc.util import foreach

target_frame = Frame.objects.get(language=en, relation__name='UsedFor', text='{1} is for {2}')

def queryset():
    frame = Frame.objects.get(text='{1} are {2}', language=en, relation__name='IsA')
    got = RawAssertion.objects.filter(language=en, frame=frame)
    return got

def fix(s):
    if s.surface2.text.startswith('for '):
        print s
        newsurf = SurfaceForm.get(s.surface2.text[4:], 'en', auto_create=True)
        print "=>",
        print s.correct_assertion(target_frame, s.surface1, newsurf)

foreach(queryset(), fix)


########NEW FILE########
__FILENAME__ = 003_bedume_is_silly
from csc.conceptnet.models import *
from csc.util import foreach

bedume = User.objects.get(username='bedume')
activity = Activity.objects.get(name='administrative fiat')
braw = [r for r in bedume.vote_set.all() if isinstance(r.object, RawAssertion)]
for b in braw:
    if b.object.assertion.relation.name == 'HasProperty':
        print b.object
        b.object.set_rating(bedume, 0, activity)
        b.object.assertion.set_rating(bedume, 0, activity)


########NEW FILE########
__FILENAME__ = 004_bedume_is_still_silly
from csc.conceptnet.models import *
from csc.conceptnet.analogyspace import *
from csc.util import foreach

cnet = conceptnet_2d_from_db('en')
aspace = cnet.svd()

bedume = User.objects.get(username='bedume')
activity = Activity.objects.get(name='administrative fiat')
braw = [r for r in bedume.vote_set.all() if isinstance(r.object, RawAssertion)]
for b in braw:
    if b.object.assertion.relation.name == 'IsA':
        print b.object
        concept = b.object.assertion.concept1.text
        if concept in aspace.u.label_list(0):
            sim = aspace.u[concept,:].hat() * aspace.u['debbie',:].hat()
            if sim > 0.9:
                print sim, b.object
                #b.object.set_rating(bedume, 0, activity)
                #b.object.assertion.set_rating(bedume, 0, activity)


########NEW FILE########
__FILENAME__ = count_assertions
#!/usr/bin/env python

from csc.conceptnet4.models import Concept
from csc.util import queryset_foreach

concepts_fixed = 0
significant = 0

def fix_concept(concept):
    global concepts_fixed, significant
    rels = concept.get_assertions(useful_only=True).count()
    if rels != concept.num_assertions:
        # print '%s: %d->%d' % (concept.canonical_name, concept.num_assertions, rels)
        concepts_fixed += 1
        if rels > 2:
            significant += 1
        concept.num_assertions = rels
        concept.save()
    if not concept.words:
        concept.words = len(concept.text.split())
        concept.save()

def update_assertion_counts(lang):
    '''Fix the num_assertions count for each concept'''
    status = queryset_foreach(Concept.objects.filter(language=lang), fix_concept)
    print 'Fixed %s of %s concepts (%s with >2 rels).' % (concepts_fixed, status.total, significant)
    return status

if __name__=='__main__':
    import sys
    lang = sys.argv[1]
    status = update_assertion_counts(lang)

########NEW FILE########
__FILENAME__ = count_surfaceforms
#!/usr/bin/env python

from csc.conceptnet4.models import SurfaceForm, RawAssertion
from csc.util import queryset_foreach
from django.db.models import Q

fixed = 0

def update_count(surface):
    global fixed
    num_raws = RawAssertion.objects.filter(Q(surface1=surface) | Q(surface2=surface)).count()
    if num_raws != surface.use_count:
        fixed += 1
        surface.use_count = num_raws
        surface.save()

def update_surfaceform_usecounts(lang):
    '''Fix the num_assertions count for each concept'''
    status = queryset_foreach(SurfaceForm.objects.filter(language=lang), update_count)
    print 'Updated counts on %d of %d surface forms' % (fixed, status.total)
    return status

if __name__=='__main__':
    import sys
    lang = sys.argv[1]
    status = update_surfaceform_usecounts(lang)

########NEW FILE########
__FILENAME__ = dump_csv
from csc.conceptnet.models import Concept, Assertion, Sentence, Frame
from csc.corpus.models import TaggedSentence
import csv

def dump_assertion_sentences(lang, f):
    writer = csv.writer(f)
    writer.writerow(('id', 'creator', 'score', 'text'))
    for id, username, score, text in Assertion.objects.filter(language=lang).values_list('id','creator__username', 'score','sentence__text').iterator():
        writer.writerow((id, username.encode('utf-8'), score, text.encode('utf-8')))

def dump_all_sentences(lang, f):
    writer = csv.writer(f)
    writer.writerow(('id', 'creator', 'created_on', 'activity', 'text'))
    for id, username, created_on, activity, text in Sentence.objects.filter(language=lang).values_list('id','creator__username','created_on', 'activity__name', 'text').iterator():
        writer.writerow((id, username.encode('utf-8'), created_on,
                         activity, text.encode('utf-8')))

def dump_concepts(lang, f):
    writer = csv.writer(f)
    writer.writerow(('id', 'num_assertions', 'normalized_text', 'canonical_name'))
    for c in Concept.objects.filter(language=lang).iterator():
        writer.writerow((c.id, c.num_predicates, c.text.encode('utf-8'),
                         c.canonical_name.encode('utf-8')))

def dump_assertions(lang, f):
    writer = csv.writer(f)
    writer.writerow(('id', 'sentence', 'relation_type', 'text1', 'text2', 'stem1_id', 'stem2_id', 'frame_id', 'score', 'creator'))
    for id, sentence, relation_type, text1, text2, stem1_id, stem2_id, frame_id, score, creator in Assertion.objects.filter(language=lang).values_list(
        'id', 'sentence__text', 'predtype__name', 'text1', 'text2',
        'stem1_id', 'stem2_id', 'frame_id', 'score', 'creator__username'
        ).iterator():
        writer.writerow((
                id, sentence.encode('utf-8'), relation_type,
                text1.encode('utf-8'), text2.encode('utf-8'),
                stem1_id, stem2_id, frame_id, score,
                creator.encode('utf-8')
                ))

def dump_frames(lang, f):
    writer = csv.writer(f)
    writer.writerow(('id', 'relation_type', 'text', 'goodness'))
    for id, relation_type, text, goodness in Frame.objects.filter(language=lang).values_list(
        'id', 'predtype__name', 'text', 'goodness'
        ).iterator():
        writer.writerow((
                id, relation_type,
                text.encode('utf-8'),
                goodness
                ))

def dump_tagged_sentences(lang, f):
    writer = csv.writer(f)
    writer.writerow(('id', 'text'))
    for id, text in TaggedSentence.objects.filter(language=lang).values_list(
        'id', 'text'
        ).iterator():
        writer.writerow((
                id, text.encode('utf-8')
                ))

if __name__=='__main__':
    import sys
    name, lang = sys.argv

    dump_assertion_sentences(lang, open(lang+'_assertion_sentences.csv','w'))
    dump_all_sentences(lang, open(lang+'_all_sentences.csv','w'))
    dump_concepts(lang, open(lang+'_concepts.csv','w'))
    dump_assertions(lang, open(lang+'_assertions.csv','w'))
    dump_frames(lang, open(lang+'_frames.csv','w'))

########NEW FILE########
__FILENAME__ = extract_concepts
#!/usr/bin/env python

from csc.conceptnet.models import Concept


from nltk import wordnet
def in_wordnet(word):
    base = wordnet.morphy(word)
    if base is None: base = word
    for d in wordnet.Dictionaries.values():
        if base in d: return True
        if word in d: return True
    return False


if __name__=='__main__':
    import sys
    lang = sys.argv[1]
    outfile = open(sys.argv[2], 'w')


    # Stopword detector
    from csc.representation.parsing.tools.models import FunctionFamily
    is_stopword = FunctionFamily.build_function_detector(lang, 'stop')

    import cPickle as pickle
    try:
        concepts = pickle.load(open('concepts_dict.pickle','rb'))
    except:
        concepts_qs = Concept.objects.filter(language=lang, num_predicates__gt=0)
        print >> sys.stderr, "Constructing concepts dictionary"
        concepts = dict(((c.text, c) for c in concepts_qs.iterator()))
        pickle.dump(concepts, open('concepts_dict.pickle','wb'), -1)

    print >> sys.stderr, "Filtering concepts"
    skipped1 = skipped2 = 0
    for stem_text, concept in concepts.iteritems():
        stem_words = stem_text.split(' ')
        if any(((word not in concepts) for word in stem_words)):
            print >> sys.stderr, "Skipped-1: "+ stem_text
            skipped1 += 1
            continue
        cname = concept.canonical_name
        if any(((not is_stopword(word) and not in_wordnet(word)) for word in cname.split(' '))):
            print >> sys.stderr, "Skipped-2: "+ stem_text
            skipped2 += 1
            continue
        print >> outfile, cname

    print "Skipped1: %d, Skipped2: %d, total: %d" % (skipped1, skipped2, len(concepts))

########NEW FILE########
__FILENAME__ = fix_abnormal_concepts
from csc.util import queryset_foreach
from csc.conceptnet.models import Concept, SurfaceForm, Language, Assertion
from django.db import connection

en = Language.get('en')

def fix_surface(surface):
    norm, residue = en.nl.lemma_split(surface.text)
    if norm != surface.concept.text:
        print
        print "surface:", surface.text.encode('utf-8')
        print "concept:", surface.concept.text.encode('utf-8')
        print "normal:", norm.encode('utf-8')
        surface.update(norm, residue)

queryset_foreach(SurfaceForm.objects.filter(language=en),
  fix_surface,
  batch_size=100)


# plan:
#  fix surface form -> concept mapping
#  remove obsolete concepts

########NEW FILE########
__FILENAME__ = fix_concept_counts
#!/usr/bin/env python

'''
Concepts keep track of their number of words. Or, they should.
'''

from csc.util.batch import queryset_foreach
from csc.conceptnet4.models import Concept
from django.db.models.query import Q

def fix_concept_counts():
    def fix_concept(concept):
        if concept.words: return
        concept.words = len(concept.text.split())
        concept.save()

    return queryset_foreach(
        Concept.objects.filter(Q(words=0) | Q(words__isnull=True)), fix_concept)

if __name__ == '__main__':
    fix_concept_counts()

########NEW FILE########
__FILENAME__ = fix_dup_frames
from csc.util import queryset_foreach
from csc.conceptnet4.models import Frame
from django.db import connection
def fix_dups(frame):
    dups = Frame.objects.filter(language=frame.language, text=frame.text,
                                relation=frame.relation)
    for dup in dups:
        if dup.id == frame.id:
            continue
        print dup
        cursor = connection.cursor()
        print("UPDATE raw_assertions SET frame_id=%s WHERE frame_id=%s" % (frame.id, dup.id))
        cursor.execute("UPDATE raw_assertions SET frame_id=%s WHERE frame_id=%s" % (frame.id, dup.id))
        dup.delete()
        print

queryset_foreach(Frame.objects.all().order_by('-goodness', 'id'),
  fix_dups,
  batch_size=100)


########NEW FILE########
__FILENAME__ = fix_people_person
from csc.conceptnet4.models import RawAssertion, Concept, Assertion,\
SurfaceForm
from django.db import transaction

people = Concept.get('people', 'en')
person = Concept.get('person', 'en')

@transaction.commit_on_success
def fix_all():
    for peopleform in people.surfaceform_set.all():
        print peopleform
        peopleform.concept = person
        peopleform.save()
        for raw in RawAssertion.objects.filter(surface1=peopleform):
            print raw.update_assertion()
        for raw in RawAssertion.objects.filter(surface2=peopleform):
            print raw.update_assertion()

if __name__ == '__main__': fix_all()


########NEW FILE########
__FILENAME__ = fix_raw_duplicates
from csc.util import queryset_foreach
from csc.conceptnet4.models import Sentence, Assertion, RawAssertion, Vote

def sort_and_check():
    all_raw = RawAssertion.objects.filter(language__id='zh-Hant').order_by('language', 'surface1__text', 'surface2__text', 'frame__id')
    print "Checking for duplicates."
    prev = None
    for raw in all_raw:
        print raw.id
        if equivalent(prev, raw):
            print (u"%s[%s] == %s[%s]" % (prev, prev.creator.username, raw, raw.creator.username)).encode('utf-8')
            prev = switch_raw(raw, prev)
        else:
            prev = raw

def equivalent(raw1, raw2):
    if raw1 is None: return False
    return (raw1.language.id == raw2.language.id
            and raw1.surface1.text == raw2.surface1.text
            and raw1.surface2.text == raw2.surface2.text
            and raw1.frame.id == raw2.frame.id)

def switch_raw(oldraw, newraw):
    # avoid the generic username when possible
    if newraw.creator.username == 'openmind':
        oldraw, newraw = newraw, oldraw
    for vote in oldraw.votes.all():
        nvotes = Vote.objects.filter(user=vote.user, object_id=newraw.id).count()
        if nvotes == 0:
            vote.object = newraw
            vote.save()
        else:
            vote.delete()
    oldraw.delete()
    newraw.update_score()
    newraw.save()
    return newraw

if __name__ == '__main__':
    sort_and_check()


########NEW FILE########
__FILENAME__ = fix_stray_spaces
from csc.conceptnet.models import *
from csc.util import foreach

def fix_spaces(s):
    if (s.surface1.text.startswith(' ') or s.surface2.text.startswith(' ')):
        print s
        newsurf1 = SurfaceForm.get(s.surface1.text.strip(), s.language,
          auto_create=True)
        newsurf2 = SurfaceForm.get(s.surface2.text.strip(), s.language,
          auto_create=True)
        print "=>",
        print s.correct_assertion(s.frame, newsurf1, newsurf2)
        s.save()

foreach(RawAssertion.objects.filter(language__id='zh-Hant'), fix_spaces)


########NEW FILE########
__FILENAME__ = fix_stray_spaces2
from csc.conceptnet.models import *
from csc.util import foreach

def fix_spaces(s):
    if (s.surface1.text.startswith(' ') or s.surface2.text.startswith(' ')):
        print s
        newsurf1 = SurfaceForm.get(s.surface1.text.strip(), s.language,
          auto_create=True)
        newsurf2 = SurfaceForm.get(s.surface2.text.strip(), s.language,
          auto_create=True)
        #print s.correct_assertion(s.frame, newsurf1, newsurf2)
        s.surface1=newsurf1
        s.surface2=newsurf2
        s.save()
        print "=>",
        print s

foreach(RawAssertion.objects.filter(language__id='zh-Hant'), fix_spaces)


########NEW FILE########
__FILENAME__ = generalize_dependencies
import sys
sys.path.insert(0, '..')
import settings

from util import queryset_foreach
from corpus.models import DependencyParse

def generalize_dep(dep):
    if dep.linktype.startswith('prep_') or dep.linktype.startswith('prepc_'):
        newlt = 'prep'
    elif dep.linktype.startswith('conj_'):
        newlt = 'conj'
    else: return

    newdep = DependencyParse(sentence_id=dep.sentence_id,
                             linktype=newlt,
                             word1=dep.word1,
                             word2=dep.word2,
                             index1=dep.index1,
                             index2=dep.index2)
    newdep.save()

def progress_callback(num, den):
    print num, '/', den

queryset_foreach(DependencyParse.objects.all(), generalize_dep)


########NEW FILE########
__FILENAME__ = import_conceptnet_zh
from csc.conceptnet.models import *
import codecs
activity, _ = Activity.objects.get_or_create(name='Pet game')
zh = Language.get('zh-Hant')
def run(filename):
    f = codecs.open(filename, encoding='utf-8')
    count = 0
    for line in f:
        if filename.endswith('1.txt') and count < 77600:
            count += 1
            continue
        line = line.strip()
        if not line: continue
        username, frame_id, text1, text2 = line.split(', ')
        user, _ = User.objects.get_or_create(username=username,
            defaults=dict(
                first_name='',
                last_name='',
                email='',
                password='-'
            )
        )
        frame = Frame.objects.get(id=int(frame_id))
        assert frame.language == zh
        try:
            got = RawAssertion.make(user, frame, text1, text2, activity)
            print got
        except RawAssertion.MultipleObjectsReturned:
            print "got multiple"
    f.close()

run('conceptnet_zh_part9.txt')
run('conceptnet_zh_part10.txt')
run('conceptnet_zh_api.txt')


########NEW FILE########
__FILENAME__ = nerf_a_user
from csc.conceptnet4.models import *
from django.db import transaction

def nerf(user):
    for vote in Vote.objects.filter(user=user):
        badass = vote.object
        vote.delete()
        badass.update_score()
        print badass

@transaction.commit_on_success
def nerf_bobman():
    bobman = User.objects.get(username='bobMan')
    crap = bobman.rawassertion_set.all()[0]
    lusers = [vote.user for vote in crap.votes.all() if vote.vote == 1]
    
    for luser in lusers:
        print
        print luser
        nerf(luser)
        
if __name__ == '__main__': nerf_bobman()
########NEW FILE########
__FILENAME__ = ratings_to_votes_to_events
import sys
sys.path.insert(0, '..')
import settings
from util import queryset_foreach
from events.models import Event
from voting.models import Vote
from datetime import datetime
from conceptnet4.models import Rating

def rating_to_vote(r):
    obj = r.sentence or r.raw_assertion or r.assertion
    score = 0
    if r.score > 0: score=1
    if r.score < 0: score=-1
    Vote.objects.record_vote(obj, r.user, score)
    ev = Event.record_event(obj, r.user, r.activity)
    ev.timestamp = r.updated
    ev.save()

def progress_callback(num, den):
    print num, '/', den

queryset_foreach(Rating.objects.all(), rating_to_vote)


########NEW FILE########
__FILENAME__ = reconcile_assertions
#!/usr/bin/env python
from csc.conceptnet.models import *
from csc.corpus.models import *
from django.contrib.auth import *
from django.db import transaction

den = Assertion.objects.filter(raw__isnull=True).count()

# Add raw assertions to predicates created on Ruby Commons.
if den > 0:
    batch = Batch(owner=User.objects.get(id=20003),
        remarks="creating raw assertions for ruby commons",
        progress_den=den)
    batch.save()
    
    num = 0
    for a in Assertion.objects.filter(raw__isnull=True):
        raw = RawAssertion(batch=batch, frame=a.frame, predtype=a.predtype,
                           text1=a.text1, text2=a.text2, polarity=a.polarity,
                           modality=a.modality, sentence=a.sentence,
                           language=a.language, predicate=a)
        raw.save()
        a.raw = raw
        a.save()
        num += 1
        batch.progress_num = num
        batch.save()
        print num, '/', den, raw

# Some raw assertions have text1 and text2 switched, and this was fixed after
# the fact in their predicates. Fix that.
@transaction.commit_on_success
def switch_raw():
    i = 0
    for a in Assertion.objects.all().select_related('raw'):
        if i % 1000 == 0: print i
        i += 1
        if (a.language.nl.normalize(a.text1) == a.language.nl.normalize(a.raw.text2) and
            a.language.nl.normalize(a.text2) == a.language.nl.normalize(a.raw.text1) and
            a.stem1.text != a.stem2.text):
            t1, t2 = a.raw.text2, a.raw.text1
            a.raw.text1 = t1
            a.raw.text2 = t2
            a.raw.save()
            print a
            print a.raw
            print

switch_raw()

#for a in Assertion.objects.all():
#    if a.text1 != a.raw.text1 or a.text2 != a.raw.text2:
#        print a.text1, '/', a.text2, a
#        print a.raw
#        print

########NEW FILE########
__FILENAME__ = remove_blacklisted
from csc.conceptnet.models import *

for concept in Concept.objects.all():
    if concept.language.nl.is_blacklisted(concept.text):
        concept.useful = False
        concept.save()

########NEW FILE########
__FILENAME__ = set_visible
from csc.util import queryset_foreach
from csc.conceptnet.models import Concept, Language

def set_visible(concept):
    if not concept.language.nl.is_blacklisted(concept.text):
        concept.visible=True
        concept.save()

def set_invisible(concept):
    if concept.language.nl.is_blacklisted(concept.text):
        concept.visible=False
        concept.save()
        
queryset_foreach(Concept.objects.filter(visible=False), set_visible)


########NEW FILE########
__FILENAME__ = simple_update_rawassertion_assertion_fkey
from csc.conceptnet.models import RawAssertion, Concept, Assertion
from django.db import transaction
import sys

no_assertion = set()
nonunique = set()

@transaction.commit_on_success
def main():
    updated_count = 0

    for raw in RawAssertion.objects.filter(predicate__id__isnull=True).iterator():
        assertions = list(Assertion.objects.filter(sentence__id=raw.sentence_id))
        if len(assertions) == 0:
            no_assertion.add(raw.id)
        elif len(assertions)==1:
            updated_count += 1
            if updated_count % 1000 == 1:
                sys.stderr.write('\r'+str(updated_count))
                sys.stderr.flush()
                transaction.commit_if_managed()
            raw.predicate = assertions[0]
            raw.save()
        else:
            nonunique.add(raw.id)

    print 'Updated', updated_count, 'assertions'
    print 'No assertion for', len(no_assertion), 'assertions'
    print 'Non-unique assertion for', len(nonunique), 'assertions'

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = undo_globalmind
from csc.conceptnet4.models import *
from events.models import Event, Activity
from voting.models import Vote
from csc.util import queryset_foreach

def nuke_it(event):
    object = event.object
    if object is None: return
    for vote in object.votes.all():
        vote.delete()
    object.delete()

#queryset_foreach(Event.objects.filter(content_type__id=92, activity__id=41),
#nuke_it, 50)
queryset_foreach(Event.objects.filter(content_type__id=90, activity__id=41),
nuke_it, 50)
queryset_foreach(Event.objects.filter(content_type__id=20, activity__id=41),
nuke_it, 50)


########NEW FILE########
__FILENAME__ = update_best_raw
from csc.conceptnet4.models import Sentence, Assertion, RawAssertion
from csc.util import queryset_foreach

queryset_foreach(Assertion.objects.all(), lambda a: a.update_raw_cache(),
batch_size=100)


########NEW FILE########
__FILENAME__ = update_rawassertion_assertion_fkey
from csc.conceptnet.models import RawAssertion, Concept, Assertion
from django.db import transaction

no_assertion = set()
nonunique = set()
failed = set()

@transaction.commit_on_success
def main():
    updated_count = 0
    for raw in RawAssertion.objects.filter(predicate__id__isnull=True)[:1000].iterator():
        try:
            concept1 = Concept.get(raw.text1, raw.language_id)
            concept2 = Concept.get(raw.text2, raw.language_id)
            assertions = list(Assertion.objects.filter(stem1=concept1,
                                                       stem2=concept2,
                                                       predtype__id=raw.predtype_id))
            if len(assertions) == 0:
                no_assertion.add(raw.id)
            elif len(assertions) == 1:
                updated_count += 1
                raw.predicate = assertions[0]
                raw.save()
            else:
                nonunique.add(raw.id)
        except:
            failed.add(raw.id)

    print 'Updated', updated_count, 'assertions'
    print 'No assertion for', len(no_assertion), 'assertions'
    print 'Non-unique assertion for', len(nonunique), 'assertions'
    print len(failed), 'failed.'

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = update_scores
from csc_utils.batch import queryset_foreach
from conceptnet.models import Sentence, Assertion, RawAssertion


def update_scores():
    queryset_foreach(Assertion, lambda x: x.update_score(),
    batch_size=100)
    queryset_foreach(RawAssertion, lambda x: x.update_score(),
    batch_size=100)
    # queryset_foreach(Sentence.objects.exclude(language__id='en'), lambda x: x.update_score(), batch_size=100)

def fix_raw_assertion_vote(raw):
    for vote in raw.votes.all():
        raw.assertion.set_rating(vote.user, vote.vote)

def update_votes():
    queryset_foreach(RawAssertion, lambda x: fix_raw_assertion_vote(x), batch_size=100)


########NEW FILE########
__FILENAME__ = update_sentences
from csc.util import queryset_foreach
from csc.corpus.models import Sentence

queryset_foreach(Sentence.objects.filter(id__lt=1367900).order_by('-id'),
  lambda x: x.update_consistency(),
  batch_size=100)


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    from csc import django_settings as settings 
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = pyyaml
"""
Improved YAML serializer by rspeer@mit.edu. Uses a stream of documents so that
it doesn't have to keep all database entries in memory.

Requires PyYaml (http://pyyaml.org/), but that's checked for in __init__.

To use it, add a line like this to your settings.py::
  
  SERIALIZATION_MODULES = {
      'yaml': 'path.to.import.this.module'
  }
"""

from StringIO import StringIO
import yaml
from django.utils.encoding import smart_unicode

try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal # Python 2.3 fallback

from django.db import models
from django.core.serializers.python import Serializer as PythonSerializer
from django.core.serializers.python import Deserializer as PythonDeserializer

class DjangoSafeDumper(yaml.SafeDumper):
    def represent_decimal(self, data):
        return self.represent_scalar('tag:yaml.org,2002:str', str(data))

DjangoSafeDumper.add_representer(decimal.Decimal, DjangoSafeDumper.represent_decimal)

class Serializer(PythonSerializer):
    """
    Convert a queryset to YAML.
    """
    
    internal_use_only = False
    
    def handle_field(self, obj, field):
        # A nasty special case: base YAML doesn't support serialization of time
        # types (as opposed to dates or datetimes, which it does support). Since
        # we want to use the "safe" serializer for better interoperability, we
        # need to do something with those pesky times. Converting 'em to strings
        # isn't perfect, but it's better than a "!!python/time" type which would
        # halt deserialization under any other language.
        if isinstance(field, models.TimeField) and getattr(obj, field.name) is not None:
            self._current[field.name] = str(getattr(obj, field.name))
        else:
            super(Serializer, self).handle_field(obj, field)
    
    def end_object(self, obj):
        the_object = {
            "model"  : smart_unicode(obj._meta),
            "pk"     : smart_unicode(obj._get_pk_val(), strings_only=True),
            "fields" : self._current
        }
        self._current = None
        dumpstr = yaml.dump(the_object, Dumper=DjangoSafeDumper,
        explicit_start=True, **self.options)
        self.stream.write(dumpstr)

    def start_serialization(self):
        self.options.pop('stream', None)
        self.options.pop('fields', None)
        PythonSerializer.start_serialization(self)

    def end_serialization(self):
        self.stream.close()

    def getvalue(self):
        return self.stream.getvalue()

def Deserializer(stream_or_string, **options):
    """
    Deserialize a stream or string of YAML data.
    """
    if isinstance(stream_or_string, basestring):
        stream = StringIO(stream_or_string)
    else:
        stream = stream_or_string
    for obj in PythonDeserializer(yaml.load_all(stream)):
        yield obj


########NEW FILE########
__FILENAME__ = test_analogyspace
from nose.tools import *
from csc.conceptnet4.analogyspace import *

def test_basic_analogyspace():
    mat = conceptnet_2d_from_db('en', cutoff=15)
    item = mat.iteritems().next()
    key, value = item
    concept1, feature = key
    filled_side, relation, concept2 = feature
    assert filled_side in ['left', 'right']
    assert relation[0] == relation[0].upper()
    

########NEW FILE########
__FILENAME__ = test_conceptnet_queries
from nose.tools import *
from conceptnet.models import *
from nose.plugins.attrib import *
def setup():
    en = Language.get('en')

def test_assertions_exist():
    Assertion.objects.filter(language=en)[0]
    Assertion.objects.filter(language=Language.get('pt'))[0]
    Assertion.objects.filter(language=Language.get('ja'))[0]
    Assertion.objects.filter(language=Language.get('ko'))[0]
    Assertion.objects.filter(language=Language.get('zh-Hant'))[0]

def test_relations():
    relations = [a.relation.name for a in Assertion.objects.filter(concept1__text='dog', concept2__text='bark', language=en)]
    assert u'CapableOf' in relations

def test_get():
    Concept.get('dog', 'en')
    Concept.get('the dog', 'en')
    Concept.get('dogs', 'en')
    Concept.get_raw('dog', 'en')

@raises(Concept.DoesNotExist)
def test_normalize():
    Concept.get_raw('the dog', 'en')

def test_surface_forms():
    surfaces = [s.text for s in SurfaceForm.objects.filter(concept__text='run', language=en)]
    assert u'run' in surfaces
    assert u'to run' in surfaces
    assert u'running' in surfaces

@attr('postgres')
def test_raw_assertion_search():
    raw = RawAssertion.objects.filter(surface1__concept__text='couch',
          surface2__concept__text='sit', language=en)
    assert len(raw) > 0


########NEW FILE########
__FILENAME__ = test_denormalized
from nose.tools import *
from csc.conceptnet.models import *
from nose.plugins.attrib import *

activity = Activity.objects.get_or_create(name="nosetests")[0]
user1 = User.objects.get(username='rspeer')
user2 = User.objects.get(username='kcarnold')

def test_denormalized():
    testconcept = Concept.get('test', 'en')

    raw = RawAssertion.make(
      user=user1,
      frame=Frame.objects.get(language=en, relation__name='HasProperty',
                              text='{1} is {2}'),
      text1='the test',
      text2='successful',
      activity=activity)
    raw.set_rating(user2, 0, activity)
    raw.set_rating(user1, 0, activity)
    raw.delete()
    raw.assertion.delete()

    testconcept.update_num_assertions()
    num = testconcept.num_assertions

    raw = RawAssertion.make(
      user=user1,
      frame=Frame.objects.get(language=en, relation__name='HasProperty',
                              text='{1} is {2}'),
      text1='the test',
      text2='successful',
      activity=activity)
    raw_id = raw.id 

    raw = RawAssertion.objects.get(id=raw_id)
    assert raw.score == 1
    
    testconcept = Concept.get('test', 'en')
    assert testconcept.num_assertions == (num + 1)

    raw.set_rating(user2, 1, activity)

    raw = RawAssertion.objects.get(id=raw_id)
    assert raw.score == 2
    
    testconcept = Concept.get('test', 'en')
    assert testconcept.num_assertions == (num + 1)

    raw.set_rating(user2, 0, activity)
    raw.set_rating(user1, 0, activity)
    raw.assertion.set_rating(user2, 0, activity)
    raw.assertion.set_rating(user1, 0, activity)

    testconcept = Concept.get('test', 'en')
    assert testconcept.num_assertions == num
    
    raw = RawAssertion.objects.get(id=raw_id)
    assert raw.score == 0

if __name__ == '__main__':
    test_denormalized()

########NEW FILE########
__FILENAME__ = test_ja_harness
#python-encoding: UTF-8

from csc.conceptnet4.models import Concept
from csc.nl.ja.system import *
from csc.corpus.models import *
import MeCab

def GetConcept(concept, lang):
    strings = []

    if not Concept.exists(concept, lang):
        print '{'
        print '\tword = "%s",' % concept
        print '\terror = "Word not found!",'
        print '}'
        return None

    result = Concept.get(concept, lang)

    lang       = result.language.name
    word       = result.text
    assertions = str(result.num_assertions)

    relations = {}

    for item in result.get_assertions():
        if not (item.relation.name in relations):
            relations[item.relation.name] = []

        relations[item.relation.name].append(
        {
            '-- comment': item.__str__(),
            'first':      item.concept1.text,
            'second':     item.concept2.text,
            'score':      item.score,
            'frequency':  item.frequency.value,
            'mods':       '',
        })

    print '{'
    print '\tword = "%s",'     % word
    print '\tlang = "%s",'     % lang
    print '\tassertions = %s,' % assertions

    for item.relation.name in relations:
        print '\t', item.relation.name, ' ='
        print '\t{'

        for v in relations[item.relation.name]:
            print '\t\t{'
            if v['first'] != word:
                print '\t\t\tfirst = "%s",' % v['first']
            else:
                print '\t\t\tsecond = "%s",' % v['second']

            if v['mods'] != '':
                print '\t\t\tmods = "%s",' % v['mods']

            print '\t\t\tscore = %d,' % v['score']
            print '\t\t\tfrequency = %d,' % v['frequency']

            print '\t\t},'

        print '\t},'

    print '}'

    return result

####################################################################################################
## Main ############################################################################################
####################################################################################################

j        = Language.get('ja')
j_s      = Sentence.objects.filter(language=j)
e        = Language.get('en')
e_s      = Sentence.objects.filter(language=e)
parser   = JaParser()

u = \
[
    parser.parse_string(v) for v in \
    [
        '赤いappleが9月に生える。',
        'が',
        'は',
        'を',
        '1月',
        '１月',
        '私の彼って、最近車買ったんだよぉ？明日は軽井沢へ連れて行ってくれるんだぁ',
        '外国人はよく社会問題の原因だとせめられ、差別されるものです。',
        'すてきな人に会いたい。',
        '大きな人に会いたい。',
        '大きい人に会いたい。',
        '赤い花は素敵。',
        'アメリカには白人がいっぱい住んでいます。',
        'テストには問題ない。',
        '夏休みに見に行った畑のいちごがとても赤かった。',
        '今すぐ行かなければならない。',
        '今日は寝てしまいました。',
        '君に今すぐ会いたい',
        'この毛布は暖かくなかった。',
        'この毛布は暖かくなるんだろう。',
        '彼女のかみが細かくて更々です。',
        '素敵な人に会いたい。',
        '教授が「分かった」とさけた。',
        '教授が「分かった」とさけた。',
        '事実はそうではなかった。',
        '米がやすくならなければならなくはないだろう。',
        'その帽子が綺麗です。',
        'その帽子が綺麗でした。',
        'その帽子が綺麗だ。',
        'その帽子が綺麗だった。',
        'その帽子が綺麗である。',
        'その帽子が綺麗であった。',
        '春は寒いであって寂しい時期である。',
        'この世の中じゃ、人間には説明できないことだってあるよ！',
        '赤い',
        '赤くない',
        '赤かった',
        '赤くなかった',
        '赤いです',
        '赤いではありません',
        '赤いじゃありません',
        '赤いではありませんでした',
        '顔が赤くなった',
        '顔が赤くなってしまいました',
        '顔が赤くならなかった',
        '君が面白くなりました',
        '君が結局面白くならなかった',
        'アメリカへのお客様にお知らせします。',
        '札幌には牛乳が人気である。',
        'コンピュータの世界では「モニタ」とは出力の仕方の一種だ。',
        '説明することが無理なときがある。',
        '8月にリンゴが赤くなる',
        '8月にリンゴを赤くする',
        '8月にリンゴを赤くしてやる',
        '8月にリンゴを赤くしておく',
        '人間は哺乳類の一種である',
        'あなたが会議の際にすることの一つは資料を配布するである．',
        'とうもろこしは地面でなくても育つことができる．',
        '',
    ]
]

def listUtterances(start = 0, count = -1):
    if count < 0: count = len(u)

    for i in range(start, count):
        print('[' + str(i) + '] : ' + u[i].surface)

def dumpUtterances(start = -1, count = -1):
    if start < 0 and count < 0:
        start = 0
        count = len(u)

    elif count == -1:
        count = 1

    count = min(len(u) - start, count)

    for i in range(start, start + count):
        u[i].dump(True)

listUtterances()

def objMethods(obj):
    out = filter(lambda k: True, obj.__class__.__dict__)
    out.sort()
    return out


def dumpSentences(lang):
    f   = file("/tmp/out_" + lang + ".txt", "w");
    div = 1000
    i   = 0

    for s in Sentence.objects.filter(language = lang):
        i += 1
        if not (i % div):
            print(str(i) + " sentences dumped")

        f.write(ja_enc(s.text))
        f.write("\n")


########NEW FILE########
__FILENAME__ = test_normalize
from csc.conceptnet4.models import *
def test_normalize():
    assert en.nl.normalize('they are running') == 'run'
    assert en.nl.normalize('went') == 'go'

########NEW FILE########
__FILENAME__ = test_users
from csc.conceptnet4.models import *

def test_users_do_not_explode():
    a = RawAssertion.objects.filter(language=en)[0]
    a.sentence.creator
    a.sentence.creator.username

########NEW FILE########
__FILENAME__ = cnet_n3
#!/usr/bin/env python

PREFIX = 'http://conceptnet.media.mit.edu'

from conceptnet.models import Assertion, Frame, RelationType, Concept

import codecs
ofile_raw = open('conceptnet_en_20080604.n3','w')
ofile = codecs.getwriter('utf-8')(ofile_raw)

print >>ofile, '@prefix conceptnet: <%s>.' % (PREFIX+'/')

def prefixed(type, rest):
    return '<%s/%s/%s>' % (PREFIX, type, rest)

def concept(id): return prefixed('concept', id)
def reltype(x): return prefixed('reltype', reltype_id2name[x])
def literal(x): return '"'+x.replace('"','_')+'"'
def _frame(id): return prefixed('frame', id)
def language(x): return prefixed('language', x)
def user(x): return prefixed('user', x)

def proplist(p):
    return u'; '.join(u'conceptnet:%s %s' % (prop, val)
                     for prop, val in p)

reltype_id2name = dict((x.id, x.name) for x in RelationType.objects.all())
frames = set()
concepts = set()

print 'Dumping assertions.'
for (id, stem1_id, reltype_id, stem2_id,
     text1, text2, frame_id, language_id, creator_id,
     score, sentence) in Assertion.useful.filter(language='en').values_list(
    'id', 'stem1_id', 'predtype_id', 'stem2_id',
    'text1', 'text2', 'frame_id', 'language_id', 'creator_id',
    'score', 'sentence__text').iterator():

    ofile.write('<%s/assertion/%s> ' % (PREFIX, id))
    ofile.write(proplist((
        ('LeftConcept', concept(stem1_id)),
        ('RelationType', reltype(reltype_id)),
        ('RightConcept', concept(stem2_id)),
        ('LeftText', literal(text1)),
        ('RightText', literal(text2)),
        ('FrameId', _frame(frame_id)),
        ('Language', language(language_id)),
        ('Creator', user(creator_id)),
        ('Score', score),
        ('Sentence', literal(sentence))
        )))
    ofile.write('.\n')

    frames.add(frame_id)
    concepts.add(stem1_id)
    concepts.add(stem2_id)

ofile.flush()

print 'Dumping frames.'
for id, frame in Frame.objects.in_bulk(list(frames)).iteritems():
    ofile.write(_frame(id)+' ')
    ofile.write(proplist((
                ('RelationType', reltype(frame.predtype_id)),
                ('FrameText', literal(frame.text)),
                ('FrameGoodness', literal(str(frame.goodness)))))
                )
    ofile.write('.\n')

ofile.flush()

print 'Dumping concepts.'
for id, c in Concept.objects.in_bulk(list(concepts)).iteritems():
    ofile.write(concept(id)+' ')
    ofile.write(proplist((
                ('NormalizedText', literal(c.text)),
                ('CanonicalName', literal(c.canonical_name))
                )))
    ofile.write('.\n')


print 'Done.'

ofile.close()

########NEW FILE########
__FILENAME__ = cnet_rdf
#!/usr/bin/env python

PREFIX = 'http://conceptnet.media.mit.edu/'

from conceptnet.models import Assertion, Frame

from rdflib.Graph import Graph
from rdflib.store import Store
from rdflib import Namespace, Literal, BNode, RDF, plugin, URIRef

store = plugin.get('SQLite', Store)()
store.open('db')
g = Graph(store, identifier=URIRef(PREFIX+'graph/en'))

base = Namespace(PREFIX)
concept = Namespace(PREFIX+'concepts/')
reltype = Namespace(PREFIX+'reltypes/')
frame = Namespace(PREFIX+'frames/')
user = Namespace(PREFIX+'users/')
language = Namespace(PREFIX+'language/')


#surface_form_ = base['SurfaceForm']
left_text_ = base['LeftText']
right_text = base['RightText']

def b(thing): return base[thing]

class SuperNode(BNode):
    def __init__(self):
        g.add((self, RDF.type, RDF.Statement))

    def say(self, type, obj):
        g.add((self, type, obj))

def add(subj, type, obj):
    stmt = SuperNode()
    stmt.say(RDF.subject, subj)
    stmt.say(RDF.predicate, type)
    stmt.say(RDF.object, obj)
    return stmt

print 'Dumping assertions.'
for stem1, predtype, stem2, text1, text2, frame_id, language_id, creator_id, score, sentence in Assertion.useful.filter(language='en').values_list('stem1__text', 'predtype__name', 'stem2__text',
                                                                                                 'text1', 'text2', 'frame_id', 'language_id', 'creator_id', 'score', 'sentence__text').iterator():
    stmt = add(concept[stem1], reltype[predtype], concept[stem2])
    stmt.say(b('LeftText'), Literal(text1))
    stmt.say(b('RightText'), Literal(text2))
    stmt.say(b('FrameId'), frame[str(frame_id)])
    stmt.say(b('Language'), language[str(language_id)])
    stmt.say(b('Creator'), user[str(creator_id)])
    stmt.say(b('Score'), Literal(score))
    stmt.say(b('Sentence'), Literal(sentence))

g.commit()
print 'Dumping frames.'
for id, predtype, text, goodness in Frame.objects.filter(language='en').values_list('id', 'predtype__name', 'text', 'goodness').iterator():
    ff = frame[str(id)]
    g.add((ff, b('RelationType'), reltype[predtype]))
    g.add((ff, b('FrameText'), Literal(text)))
    g.add((ff, b('FrameGoodness'), Literal(str(goodness))))


g.commit()

########NEW FILE########
__FILENAME__ = create_placeholder_users
#!/usr/bin/env python
import sys, os
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    print "Setting DJANGO_SETTINGS_MODULE=csamoa.settings temporarily."
    print "You may want to set that more permanently in your environment."
    print
    os.environ['DJANGO_SETTINGS_MODULE'] = 'csc.django_settings'

from csc.conceptnet.models import User
from csc.corpus.models import Sentence
from votes.models import Vote
from django.db import transaction, connection
from django.conf import settings

try:
    cursor = connection.cursor()
except:
    print "Problem while connecting to the database. Check your db_config.py."
    print "Original error:"
    raise

users_table_error = """
Use this script ONLY if you have just created a fresh ConceptNet
database, imported the dump from the website, and ran
`./manage.py syncdb` to add the Django tables.

When running `syncdb`, DO NOT create an admin user. It will conflict
with a user that this script will add.
"""

try:
    if User.objects.all().count() > 0:
        print "Refusing to run because you already have users in the database."
        print
        print users_table_error
        print "Original error:"
        sys.exit(1)
except:
    print """
Encountered a problem checking the users table (auth_user). Maybe it
doesn't exist?"""
    print
    print users_table_error
    print "Original error:"
    raise


## Now the real work.

print "Getting all known uids... ",
# All Assertions have Sentences, which have the same creator. So the Sentences
# is the most complete list of users.
print "(users...) ",
uids = set(Sentence.objects.all().values_list('creator__id', flat=True).iterator())
# But some users may have been raters only.
print "(ratings...) ",
for uid in Vote.objects.all().values_list('user__id', flat=True).iterator():
    uids.add(uid)
print

@transaction.commit_on_success
def make_users(uids):
    for uid in uids:
        User.objects.create(id=uid, username='user_%d' % uid)

print "Creating %d placeholder users..." % len(uids)
make_users(uids)

if settings.DATABASE_ENGINE in ('postgresql_psycopg2', 'postgresql'):
    print "Resetting id sequence for PostgreSQL..."
    seq = 'auth_user_id_seq'
    cursor.execute('ALTER SEQUENCE %s RESTART WITH %d;' % (seq, max(uids)+1))

########NEW FILE########
__FILENAME__ = dump_to_sqlite
#!/usr/bin/env python
# This one should run in the ConceptNet Django environment.
from conceptnet.models import Concept # just for the environment setup.
from django.db.models import get_models
from django.db.models.query import QuerySet
from csc_utils.batch import Status
import sys, sqlite3

models_to_dump = '''
Vote RawAssertion Frame SurfaceForm Assertion
Relation Frequency Concept Language
Sentence User ContentType Activity Batch
'''.strip().split()

models = dict((model.__name__, model) for model in get_models()
              if model.__name__ in models_to_dump)

def dump_to_sqlite(conn):
    cursor = conn.cursor()

    for idx, model_name in enumerate(models_to_dump):
        model = models[model_name]
        print >> sys.stderr, '(%2d/%2d) dumping %s' % (idx+1, len(models_to_dump), model_name)
        meta = model._meta
        db_table = meta.db_table

        truncate = 'DELETE FROM %s' % db_table
        print truncate
        cursor.execute(truncate)

        if model_name == 'User':
            # User is special because we don't want to dump private info.
            placeholder_timestamp = '1969-12-31 19:00:00'
            sql = 'INSERT INTO %s (id, username, last_login, date_joined, first_name, last_name, email, password, is_staff, is_active, is_superuser) VALUES (?, ?, %r, %r, "", "", "", "X", 0, 1, 0)' % (db_table, placeholder_timestamp, placeholder_timestamp)
            queryset = QuerySet(model).values_list('id', 'username')
        else:
            # Okay, so a field has a .serialize parameter on it. But the auto
            # id field has this set to False. Fail. Just serialize all the
            # local fields.
            fields = meta.local_fields
            field_names = [f.column for f in fields]

            sql = 'INSERT INTO %s (%s) VALUES (%s)' % (
                db_table,
                ', '.join(field_names),
                ', '.join('?'*len(fields)))
            queryset = QuerySet(model).values_list(*(field_names)) # hm, this might not work if the db names are different.

        print sql
        cursor.executemany(sql, Status.reporter(queryset, report_interval=1000))
        conn.commit()

    cursor.close()

if __name__ == '__main__':
    db_name = sys.argv[1]
    conn = sqlite3.connect(db_name)
    dump_to_sqlite(conn)


########NEW FILE########
__FILENAME__ = load_autocorrector
from csc.corpus.models import AutocorrectRule, Language
from django.db import transaction

print "Loading table..."
autocorrect_file = './autocorrect.txt'
autocorrect_kb = {}
items = filter(lambda line:line.strip()!='',open(autocorrect_file,'r').read().split('\n'))
lang_en = Language.objects.get(pk='EN')

def bulk_commit(lst):
    for obj in lst: obj.save()
bulk_commit_wrapped = transaction.commit_on_success(bulk_commit)

print "Building entries..."
ars = []
for entry in items:
    match = entry.split()[0]
    replace_with = ' '.join(entry.split()[1:])
    ar = AutocorrectRule()
    ar.language = lang_en
    ar.match = match
    ar.replace_with = replace_with
    ars.append(ar)

print "Bulk committing..."
bulk_commit_wrapped(ars)

########NEW FILE########
__FILENAME__ = make_sqlite
#!/usr/bin/env python
import sys
db_name = sys.argv[1]

from django.conf import settings
settings.configure(
    DATABASE_ENGINE = 'sqlite3',
    DATABASE_NAME = db_name,
    INSTALLED_APPS=(
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'conceptnet.corpus',
        'conceptnet',
        'simplenlp',
        'voting',
        'events',
        'south'))

from django.core.management import call_command
call_command('syncdb')
call_command('migrate')


########NEW FILE########
__FILENAME__ = stats
from conceptnet4.models import *
from operator import itemgetter

def relations_distribution(lang):
    return sorted(
        ((relation.name, relation.assertion_set.filter(language=lang).count())
         for relation in Relation.objects.filter(description__isnull=False)),
        key=itemgetter(1))

def sample_assertions(relation, n=10):
    return [assertion.nl_repr() for assertion in
            Relation.get(relation).assertion_set
            .filter(score__gt=0).order_by('?')[:n]]

def oldest_assertion(lang):
    return Assertion.objects.filter(language=lang).order_by('-rawassertion__created')[0]


if __name__ == '__main__':
    print relations_distribution('en')
    
        

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
     # Web API (REST)
     (r'^api/', include('csc.webapi.urls')),
     (r'', include('csc.webapi.urls')),

#     # ConceptTools (realm)
#     (r'^api/', include('realm.urls')),
)

########NEW FILE########
