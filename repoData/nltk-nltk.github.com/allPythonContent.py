__FILENAME__ = code_add_cv_field
# Natural Language Toolkit: code_add_cv_field

from nltk.etree.ElementTree import SubElement

def cv(s):
    s = s.lower()
    s = re.sub(r'[^a-z]',     r'_', s)
    s = re.sub(r'[aeiou]',    r'V', s)
    s = re.sub(r'[^V_]',      r'C', s)
    return (s)

def add_cv_field(entry):
    for field in entry:
        if field.tag == 'lx':
            cv_field = SubElement(entry, 'cv')
            cv_field.text = cv(field.text)


########NEW FILE########
__FILENAME__ = code_anneal
# Natural Language Toolkit: code_anneal

from random import randint

def flip(segs, pos):
    return segs[:pos] + str(1-int(segs[pos])) + segs[pos+1:]

def flip_n(segs, n):
    for i in range(n):
        segs = flip(segs, randint(0,len(segs)-1))
    return segs

def anneal(text, segs, iterations, cooling_rate):
    temperature = float(len(segs))
    while temperature > 0.5:
        best_segs, best = segs, evaluate(text, segs)
        for i in range(iterations):
            guess = flip_n(segs, int(round(temperature)))
            score = evaluate(text, guess)
            if score < best:
                best, best_segs = score, guess
        score, segs = best, best_segs
        temperature = temperature / cooling_rate
        print evaluate(text, segs), segment(text, segs)
    print
    return segs


########NEW FILE########
__FILENAME__ = code_baseline_tagger
# Natural Language Toolkit: code_baseline_tagger

def performance(cfd, wordlist):
    lt = dict((word, cfd[word].max()) for word in wordlist)
    baseline_tagger = nltk.UnigramTagger(model=lt, backoff=nltk.DefaultTagger('NN'))
    return baseline_tagger.evaluate(brown.tagged_sents(categories='news'))

def display():
    import pylab
    words_by_freq = list(nltk.FreqDist(brown.words(categories='news')))
    cfd = nltk.ConditionalFreqDist(brown.tagged_words(categories='news'))
    sizes = 2 ** pylab.arange(15)
    perfs = [performance(cfd, words_by_freq[:size]) for size in sizes]
    pylab.plot(sizes, perfs, '-bo')
    pylab.title('Lookup Tagger Performance with Varying Model Size')
    pylab.xlabel('Model Size')
    pylab.ylabel('Performance')
    pylab.show()


########NEW FILE########
__FILENAME__ = code_bottom_up_chart_parsers
# Natural Language Toolkit: code_bottom_up_chart_parsers

inside_parser = nltk.InsideChartParser(grammar)
longest_parser = nltk.LongestChartParser(grammar)
beam_parser = nltk.InsideChartParser(grammar, beam_size=20)


########NEW FILE########
__FILENAME__ = code_brill_demo
# Natural Language Toolkit: code_brill_demo


########NEW FILE########
__FILENAME__ = code_cascaded_chunker
# Natural Language Toolkit: code_cascaded_chunker

grammar = r"""
  NP: {<DT|JJ|NN.*>+}          # Chunk sequences of DT, JJ, NN
  PP: {<IN><NP>}               # Chunk prepositions followed by NP
  VP: {<VB.*><NP|PP|CLAUSE>+$} # Chunk verbs and their arguments
  CLAUSE: {<NP><VP>}           # Chunk NP, VP
  """
cp = nltk.RegexpParser(grammar)
sentence = [("Mary", "NN"), ("saw", "VBD"), ("the", "DT"), ("cat", "NN"),
    ("sit", "VB"), ("on", "IN"), ("the", "DT"), ("mat", "NN")]


########NEW FILE########
__FILENAME__ = code_cfg1
# Natural Language Toolkit: code_cfg1

grammar1 = nltk.parse_cfg("""
  S -> NP VP
  VP -> V NP | V NP PP
  PP -> P NP
  V -> "saw" | "ate" | "walked"
  NP -> "John" | "Mary" | "Bob" | Det N | Det N PP
  Det -> "a" | "an" | "the" | "my"
  N -> "man" | "dog" | "cat" | "telescope" | "park"
  P -> "in" | "on" | "by" | "with"
  """)


########NEW FILE########
__FILENAME__ = code_cfg2
# Natural Language Toolkit: code_cfg2

grammar2 = nltk.parse_cfg("""
  S  -> NP VP
  NP -> Det Nom | PropN
  Nom -> Adj Nom | N
  VP -> V Adj | V NP | V S | V NP PP
  PP -> P NP
  PropN -> 'Buster' | 'Chatterer' | 'Joe'
  Det -> 'the' | 'a'
  N -> 'bear' | 'squirrel' | 'tree' | 'fish' | 'log'
  Adj  -> 'angry' | 'frightened' |  'little' | 'tall'
  V ->  'chased'  | 'saw' | 'said' | 'thought' | 'was' | 'put'
  P -> 'on'
  """)


########NEW FILE########
__FILENAME__ = code_check_parens
# Natural Language Toolkit: code_check_parens

def check_parens(tokens):
    stack = []
    for token in tokens:
        if token == '(':     # push
            stack.append(token)
        elif token == ')':   # pop
            stack.pop()
    return stack


########NEW FILE########
__FILENAME__ = code_chinker
# Natural Language Toolkit: code_chinker

grammar = r"""
  NP:
    {<.*>+}          # Chunk everything
    }<VBD|IN>+{      # Chink sequences of VBD and IN
  """
sentence = [("the", "DT"), ("little", "JJ"), ("yellow", "JJ"),
       ("dog", "NN"), ("barked", "VBD"), ("at", "IN"),  ("the", "DT"), ("cat", "NN")]
cp = nltk.RegexpParser(grammar)


########NEW FILE########
__FILENAME__ = code_chunker1
# Natural Language Toolkit: code_chunker1

grammar = r"""
  NP: {<DT|PP\$>?<JJ>*<NN>}   # chunk determiner/possessive, adjectives and nouns
      {<NNP>+}                # chunk sequences of proper nouns
"""
cp = nltk.RegexpParser(grammar)
sentence = [("Rapunzel", "NNP"), ("let", "VBD"), ("down", "RP"), # [_code-chunker1-ex]
                 ("her", "PP$"), ("long", "JJ"), ("golden", "JJ"), ("hair", "NN")]


########NEW FILE########
__FILENAME__ = code_chunkex
# Natural Language Toolkit: code_chunkex


########NEW FILE########
__FILENAME__ = code_chunk_toolbox
# Natural Language Toolkit: code_chunk_toolbox

from nltk_contrib import toolbox

grammar = r"""
      lexfunc: {<lf>(<lv><ln|le>*)*}
      example: {<rf|xv><xn|xe>*}
      sense:   {<sn><ps><pn|gv|dv|gn|gp|dn|rn|ge|de|re>*<example>*<lexfunc>*}
      record:   {<lx><hm><sense>+<dt>}
    """


########NEW FILE########
__FILENAME__ = code_classification_based_segmenter
# Natural Language Toolkit: code_classification_based_segmenter

def segment_sentences(words):
    start = 0
    sents = []
    for i, word in enumerate(words):
        if word in '.?!' and classifier.classify(punct_features(words, i)) == True:
            sents.append(words[start:i+1])
            start = i+1
    if start < len(words):
        sents.append(words[start:])
    return sents


########NEW FILE########
__FILENAME__ = code_classifier_chunker
# Natural Language Toolkit: code_classifier_chunker

class ConsecutiveNPChunkTagger(nltk.TaggerI): # [_consec-chunk-tagger]

    def __init__(self, train_sents):
        train_set = []
        for tagged_sent in train_sents:
            untagged_sent = nltk.tag.untag(tagged_sent)
            history = []
            for i, (word, tag) in enumerate(tagged_sent):
                featureset = npchunk_features(untagged_sent, i, history) # [_consec-use-fe]
                train_set.append( (featureset, tag) )
                history.append(tag)
        self.classifier = nltk.MaxentClassifier.train( # [_consec-use-maxent]
            train_set, algorithm='megam', trace=0)

    def tag(self, sentence):
        history = []
        for i, word in enumerate(sentence):
            featureset = npchunk_features(sentence, i, history)
            tag = self.classifier.classify(featureset)
            history.append(tag)
        return zip(sentence, history)

class ConsecutiveNPChunker(nltk.ChunkParserI): # [_consec-chunker]
    def __init__(self, train_sents):
        tagged_sents = [[((w,t),c) for (w,t,c) in
                         nltk.chunk.tree2conlltags(sent)]
                        for sent in train_sents]
        self.tagger = ConsecutiveNPChunkTagger(tagged_sents)

    def parse(self, sentence):
        tagged_sents = self.tagger.tag(sentence)
        conlltags = [(w,t,c) for ((w,t),c) in tagged_sents]
        return nltk.chunk.conlltags2tree(conlltags)


########NEW FILE########
__FILENAME__ = code_consecutive_pos_tagger
# Natural Language Toolkit: code_consecutive_pos_tagger

 def pos_features(sentence, i, history): # [_consec-pos-tag-features]
     features = {"suffix(1)": sentence[i][-1:],
                 "suffix(2)": sentence[i][-2:],
                 "suffix(3)": sentence[i][-3:]}
     if i == 0:
         features["prev-word"] = "<START>"
         features["prev-tag"] = "<START>"
     else:
         features["prev-word"] = sentence[i-1]
         features["prev-tag"] = history[i-1]
     return features

class ConsecutivePosTagger(nltk.TaggerI): # [_consec-pos-tagger]

    def __init__(self, train_sents):
        train_set = []
        for tagged_sent in train_sents:
            untagged_sent = nltk.tag.untag(tagged_sent)
            history = []
            for i, (word, tag) in enumerate(tagged_sent):
                featureset = pos_features(untagged_sent, i, history)
                train_set.append( (featureset, tag) )
                history.append(tag)
        self.classifier = nltk.NaiveBayesClassifier.train(train_set)

    def tag(self, sentence):
        history = []
        for i, word in enumerate(sentence):
            featureset = pos_features(sentence, i, history)
            tag = self.classifier.classify(featureset)
            history.append(tag)
        return zip(sentence, history)


########NEW FILE########
__FILENAME__ = code_convert_parens
# Natural Language Toolkit: code_convert_parens

def convert_parens(tokens):
    stack = [[]]
    for token in tokens:
        if token == '(':     # push
            sublist = []
            stack[-1].append(sublist)
            stack.append(sublist)
        elif token == ')':   # pop
            stack.pop()
        else:                # update top of stack
            stack[-1].append(token)
    return stack[0]


########NEW FILE########
__FILENAME__ = code_dictionary
# Natural Language Toolkit: code_dictionary


########NEW FILE########
__FILENAME__ = code_document_classify_fd
# Natural Language Toolkit: code_document_classify_fd

all_words = nltk.FreqDist(w.lower() for w in movie_reviews.words())
word_features = all_words.keys()[:2000] # [_document-classify-all-words]

def document_features(document): # [_document-classify-extractor]
    document_words = set(document) # [_document-classify-set]
    features = {}
    for word in word_features:
        features['contains(%s)' % word] = (word in document_words)
    return features


########NEW FILE########
__FILENAME__ = code_document_classify_use
# Natural Language Toolkit: code_document_classify_use

featuresets = [(document_features(d), c) for (d,c) in documents]
train_set, test_set = featuresets[100:], featuresets[:100]
classifier = nltk.NaiveBayesClassifier.train(train_set)


########NEW FILE########
__FILENAME__ = code_entropy
# Natural Language Toolkit: code_entropy

import math
def entropy(labels):
    freqdist = nltk.FreqDist(labels)
    probs = [freqdist.freq(l) for l in nltk.FreqDist(labels)]
    return -sum([p * math.log(p,2) for p in probs])


########NEW FILE########
__FILENAME__ = code_epytext
# Natural Language Toolkit: code_epytext

def accuracy(reference, test):
    """
    Calculate the fraction of test items that equal the corresponding reference items.

    Given a list of reference values and a corresponding list of test values,
    return the fraction of corresponding values that are equal.
    In particular, return the fraction of indexes
    {0<i<=len(test)} such that C{test[i] == reference[i]}.


########NEW FILE########
__FILENAME__ = code_evaluate
# Natural Language Toolkit: code_evaluate

def evaluate(text, segs):
    words = segment(text, segs)
    text_size = len(words)
    lexicon_size = len(' '.join(list(set(words))))
    return text_size + lexicon_size


########NEW FILE########
__FILENAME__ = code_feat0cfg
# Natural Language Toolkit: code_feat0cfg


########NEW FILE########
__FILENAME__ = code_featstructures
# Natural Language Toolkit: code_featstructures

fs1 = nltk.FeatStruct("[A = ?x, B= [C = ?x]]")
fs2 = nltk.FeatStruct("[B = [D = d]]")
fs3 = nltk.FeatStruct("[B = [C = d]]")
fs4 = nltk.FeatStruct("[A = (1)[B = b], C->(1)]")
fs5 = nltk.FeatStruct("[A = (1)[D = ?x], C = [E -> (1), F = ?x] ]")
fs6 = nltk.FeatStruct("[A = [D = d]]")
fs7 = nltk.FeatStruct("[A = [D = d], C = [F = [D = d]]]")
fs8 = nltk.FeatStruct("[A = (1)[D = ?x, G = ?x], C = [B = ?x, E -> (1)] ]")
fs9 = nltk.FeatStruct("[A = [B = b], C = [E = [G = e]]]")
fs10 = nltk.FeatStruct("[A = (1)[B = b], C -> (1)]")


########NEW FILE########
__FILENAME__ = code_featurecharttrace
# Natural Language Toolkit: code_featurecharttrace


########NEW FILE########
__FILENAME__ = code_findtags
# Natural Language Toolkit: code_findtags

 def findtags(tag_prefix, tagged_text):
     cfd = nltk.ConditionalFreqDist((tag, word) for (word, tag) in tagged_text
                                   if tag.startswith(tag_prefix))
     return dict((tag, cfd[tag].keys()[:5]) for tag in cfd.conditions())


########NEW FILE########
__FILENAME__ = code_freq_words1
# Natural Language Toolkit: code_freq_words1

def freq_words(url, freqdist, n):
    text = nltk.clean_url(url)
    for word in nltk.word_tokenize(text):
        freqdist.inc(word.lower())
    print freqdist.keys()[:n]


########NEW FILE########
__FILENAME__ = code_freq_words2
# Natural Language Toolkit: code_freq_words2

def freq_words(url):
    freqdist = nltk.FreqDist()
    text = nltk.clean_url(url)
    for word in nltk.word_tokenize(text):
        freqdist.inc(word.lower())
    return freqdist


########NEW FILE########
__FILENAME__ = code_gender_features_overfitting
# Natural Language Toolkit: code_gender_features_overfitting

def gender_features2(name):
    features = {}
    features["firstletter"] = name[0].lower()
    features["lastletter"] = name[-1].lower()
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        features["count(%s)" % letter] = name.lower().count(letter)
        features["has(%s)" % letter] = (letter in name.lower())
    return features


########NEW FILE########
__FILENAME__ = code_germancfg
# Natural Language Toolkit: code_germancfg


########NEW FILE########
__FILENAME__ = code_get_text
# Natural Language Toolkit: code_get_text

import re
def get_text(file):
    """Read text from a file, normalizing whitespace and stripping HTML markup."""
    text = open(file).read()
    text = re.sub('\s+', ' ', text)
    text = re.sub(r'<.*?>', ' ', text)
    return text


########NEW FILE########
__FILENAME__ = code_give
# Natural Language Toolkit: code_give

def give(t):
    return t.node == 'VP' and len(t) > 2 and t[1].node == 'NP'\
           and (t[2].node == 'PP-DTV' or t[2].node == 'NP')\
           and ('give' in t[0].leaves() or 'gave' in t[0].leaves())
def sent(t):
    return ' '.join(token for token in t.leaves() if token[0] not in '*-0')
def print_node(t, width):
        output = "%s %s: %s / %s: %s" %\
            (sent(t[0]), t[1].node, sent(t[1]), t[2].node, sent(t[2]))
        if len(output) > width:
            output = output[:width] + "..."
        print output


########NEW FILE########
__FILENAME__ = code_hill_climb
# Natural Language Toolkit: code_hill_climb

def flip(segs, pos):
    return segs[:pos] + `1-int(segs[pos])` + segs[pos+1:]
def hill_climb(text, segs, iterations):
    for i in range(iterations):
        pos, best = 0, evaluate(text, segs)
        for i in range(len(segs)):
            score = evaluate(text, flip(segs, i))
            if score < best:
                pos, best = i, score
        if pos != 0:
            segs = flip(segs, pos)
            print evaluate(text, segs), segment(text, segs)
    return segs


########NEW FILE########
__FILENAME__ = code_html2csv
# Natural Language Toolkit: code_html2csv

def lexical_data(html_file):
    SEP = '_ENTRY'
    html = open(html_file).read()
    html = re.sub(r'<p', SEP + '<p', html)
    text = nltk.clean_html(html)
    text = ' '.join(text.split())
    for entry in text.split(SEP):
        if entry.count(' ') > 2:
            yield entry.split(' ', 3)


########NEW FILE########
__FILENAME__ = code_modal_plot
# Natural Language Toolkit: code_modal_plot

colors = 'rgbcmyk' # red, green, blue, cyan, magenta, yellow, black
def bar_chart(categories, words, counts):
    "Plot a bar chart showing counts for each word by category"
    import pylab
    ind = pylab.arange(len(words))
    width = 1 / (len(categories) + 1)
    bar_groups = []
    for c in range(len(categories)):
        bars = pylab.bar(ind+c*width, counts[categories[c]], width,
                         color=colors[c % len(colors)])
        bar_groups.append(bars)
    pylab.xticks(ind+width, words)
    pylab.legend([b[0] for b in bar_groups], categories, loc='upper left')
    pylab.ylabel('Frequency')
    pylab.title('Frequency of Six Modal Verbs by Genre')
    pylab.show()


########NEW FILE########
__FILENAME__ = code_modal_tabulate
# Natural Language Toolkit: code_modal_tabulate

 def tabulate(cfdist, words, categories):
     print '%-16s' % 'Category',
     for word in words:                                  # column headings
         print '%6s' % word,
     print
     for category in categories:
         print '%-16s' % category,                       # row heading
         for word in words:                              # for each word
             print '%6d' % cfdist[category][word],       # print table cell
         print                                           # end the row


########NEW FILE########
__FILENAME__ = code_networkx
# Natural Language Toolkit: code_networkx

import networkx as nx
import matplotlib
from nltk.corpus import wordnet as wn

def traverse(graph, start, node):
    graph.depth[node.name] = node.shortest_path_distance(start)
    for child in node.hyponyms():
        graph.add_edge(node.name, child.name) # [_add-edge]
        traverse(graph, start, child) # [_recursive-traversal]

def hyponym_graph(start):
    G = nx.Graph() # [_define-graph]
    G.depth = {}
    traverse(G, start, start)
    return G

def graph_draw(graph):
    nx.draw_graphviz(graph,
         node_size = [16 * graph.degree(n) for n in graph],
         node_color = [graph.depth[n] for n in graph],
         with_labels = False)
    matplotlib.pyplot.show()


########NEW FILE########
__FILENAME__ = code_pcfg1
# Natural Language Toolkit: code_pcfg1

grammar = nltk.parse_pcfg("""
    S    -> NP VP              [1.0]
    VP   -> TV NP              [0.4]
    VP   -> IV                 [0.3]
    VP   -> DatV NP NP         [0.3]
    TV   -> 'saw'              [1.0]
    IV   -> 'ate'              [1.0]
    DatV -> 'gave'             [1.0]
    NP   -> 'telescopes'       [0.8]
    NP   -> 'Jack'             [0.2]
    """)


########NEW FILE########
__FILENAME__ = code_plural
# Natural Language Toolkit: code_plural

def plural(word):
    if word.endswith('y'):
        return word[:-1] + 'ies'
    elif word[-1] in 'sx' or word[-2:] in ['sh', 'ch']:
        return word + 'es'
    elif word.endswith('an'):
        return word[:-2] + 'en'
    else:
        return word + 's'


########NEW FILE########
__FILENAME__ = code_random_text
# Natural Language Toolkit: code_random_text

def generate_model(cfdist, word, num=15):
    for i in range(num):
        print word,
        word = cfdist[word].max()

text = nltk.corpus.genesis.words('english-kjv.txt')
bigrams = nltk.bigrams(text)
cfd = nltk.ConditionalFreqDist(bigrams) # [_bigram-condition]


########NEW FILE########
__FILENAME__ = code_rte_features
# Natural Language Toolkit: code_rte_features

def rte_features(rtepair):
    extractor = nltk.RTEFeatureExtractor(rtepair)
    features = {}
    features['word_overlap'] = len(extractor.overlap('word'))
    features['word_hyp_extra'] = len(extractor.hyp_extra('word'))
    features['ne_overlap'] = len(extractor.overlap('ne'))
    features['ne_hyp_extra'] = len(extractor.hyp_extra('ne'))
    return features


########NEW FILE########
__FILENAME__ = code_search_documents
# Natural Language Toolkit: code_search_documents

def raw(file):
    contents = open(file).read()
    contents = re.sub(r'<.*?>', ' ', contents)
    contents = re.sub('\s+', ' ', contents)
    return contents

def snippet(doc, term): # buggy
    text = ' '*30 + raw(doc) + ' '*30
    pos = text.index(term)
    return text[pos-30:pos+30]

print "Building Index..."
files = nltk.corpus.movie_reviews.abspaths()
idx = nltk.Index((w, f) for f in files for w in raw(f).split())

query = ''
while query != "quit":
    query = raw_input("query> ")
    if query in idx:
        for doc in idx[query]:
            print snippet(doc, query)
    else:
        print "Not found"


########NEW FILE########
__FILENAME__ = code_search_examples
# Natural Language Toolkit: code_search_examples

def search1(substring, words):
    result = []
    for word in words:
        if substring in word:
            result.append(word)
    return result

def search2(substring, words):
    for word in words:
        if substring in word:
            yield word

print "search1:"
for item in search1('zz', nltk.corpus.brown.words()):
    print item
print "search2:"
for item in search2('zz', nltk.corpus.brown.words()):
    print item


########NEW FILE########
__FILENAME__ = code_segment
# Natural Language Toolkit: code_segment

def segment(text, segs):
    words = []
    last = 0
    for i in range(len(segs)):
        if segs[i] == '1':
            words.append(text[last:i+1])
            last = i+1
    words.append(text[last:])
    return words


########NEW FILE########
__FILENAME__ = code_sentential_complement
# Natural Language Toolkit: code_sentential_complement

def filter(tree):
    child_nodes = [child.node for child in tree
                   if isinstance(child, nltk.Tree)]
    return  (tree.node == 'VP') and ('S' in child_nodes)


########NEW FILE########
__FILENAME__ = code_slashcfg
# Natural Language Toolkit: code_slashcfg


########NEW FILE########
__FILENAME__ = code_stemmer_indexing
# Natural Language Toolkit: code_stemmer_indexing

class IndexedText(object):

    def __init__(self, stemmer, text):
        self._text = text
        self._stemmer = stemmer
        self._index = nltk.Index((self._stem(word), i)
                                 for (i, word) in enumerate(text))

    def concordance(self, word, width=40):
        key = self._stem(word)
        wc = width/4                # words of context
        for i in self._index[key]:
            lcontext = ' '.join(self._text[i-wc:i])
            rcontext = ' '.join(self._text[i:i+wc])
            ldisplay = '%*s'  % (width, lcontext[-width:])
            rdisplay = '%-*s' % (width, rcontext[:width])
            print ldisplay, rdisplay

    def _stem(self, word):
        return self._stemmer.stem(word).lower()


########NEW FILE########
__FILENAME__ = code_strings_to_ints
# Natural Language Toolkit: code_strings_to_ints

def preprocess(tagged_corpus):
    words = set()
    tags = set()
    for sent in tagged_corpus:
        for word, tag in sent:
            words.add(word)
            tags.add(tag)
    wm = dict((w,i) for (i,w) in enumerate(words))
    tm = dict((t,i) for (i,t) in enumerate(tags))
    return [[(wm[w], tm[t]) for (w,t) in sent] for sent in tagged_corpus]


########NEW FILE########
__FILENAME__ = code_suffix_pos_tag
# Natural Language Toolkit: code_suffix_pos_tag

def pos_features(sentence, i): # [_suffix-pos-tag-fd]
    features = {"suffix(1)": sentence[i][-1:],
                "suffix(2)": sentence[i][-2:],
                "suffix(3)": sentence[i][-3:]}
    if i == 0:
        features["prev-word"] = "<START>"
    else:
        features["prev-word"] = sentence[i-1]
    return features


########NEW FILE########
__FILENAME__ = code_three_word_phrase
# Natural Language Toolkit: code_three_word_phrase

 from nltk.corpus import brown
 def process(sentence):
     for (w1,t1), (w2,t2), (w3,t3) in nltk.trigrams(sentence): # [_three-word]
         if (t1.startswith('V') and t2 == 'TO' and t3.startswith('V')): # [_verb-to-verb]
             print w1, w2, w3 # [_print-words]


########NEW FILE########
__FILENAME__ = code_toolbox_validation
# Natural Language Toolkit: code_toolbox_validation

grammar = nltk.parse_cfg('''
  S -> Head PS Glosses Comment Date Sem_Field Examples
  Head -> Lexeme Root
  Lexeme -> "lx"
  Root -> "rt" |
  PS -> "ps"
  Glosses -> Gloss Glosses |
  Gloss -> "ge" | "tkp" | "eng"
  Date -> "dt"
  Sem_Field -> "sf"
  Examples -> Example Ex_Pidgin Ex_English Examples |
  Example -> "ex"
  Ex_Pidgin -> "xp"
  Ex_English -> "xe"
  Comment -> "cmt" | "nt" |
  ''')

def validate_lexicon(grammar, lexicon, ignored_tags):
    rd_parser = nltk.RecursiveDescentParser(grammar)
    for entry in lexicon:
        marker_list = [field.tag for field in entry if field.tag not in ignored_tags]
        if rd_parser.nbest_parse(marker_list):
            print "+", ':'.join(marker_list) # [_accepted-entries]
        else:
            print "-", ':'.join(marker_list) # [_rejected-entries]


########NEW FILE########
__FILENAME__ = code_traverse
# Natural Language Toolkit: code_traverse

def traverse(t):
    try:
        t.node
    except AttributeError:
        print t,
    else:
        # Now we know that t.node is defined
        print '(', t.node,
        for child in t:
            traverse(child)
        print ')',


########NEW FILE########
__FILENAME__ = code_trie
# Natural Language Toolkit: code_trie

def insert(trie, key, value):
    if key:
        first, rest = key[0], key[1:]
        if first not in trie:
            trie[first] = {}
        insert(trie[first], rest, value)
    else:
        trie['value'] = value


########NEW FILE########
__FILENAME__ = code_unigram_chunker
# Natural Language Toolkit: code_unigram_chunker

class UnigramChunker(nltk.ChunkParserI):
    def __init__(self, train_sents): # [_code-unigram-chunker-constructor]
        train_data = [[(t,c) for w,t,c in nltk.chunk.tree2conlltags(sent)]
                      for sent in train_sents]
        self.tagger = nltk.UnigramTagger(train_data) # [_code-unigram-chunker-buildit]

    def parse(self, sentence): # [_code-unigram-chunker-parse]
        pos_tags = [pos for (word,pos) in sentence]
        tagged_pos_tags = self.tagger.tag(pos_tags)
        chunktags = [chunktag for (pos, chunktag) in tagged_pos_tags]
        conlltags = [(word, pos, chunktag) for ((word,pos),chunktag)
                     in zip(sentence, chunktags)]
        return nltk.chunk.conlltags2tree(conlltags)


########NEW FILE########
__FILENAME__ = code_unusual
# Natural Language Toolkit: code_unusual

 def unusual_words(text):
     text_vocab = set(w.lower() for w in text if w.isalpha())
     english_vocab = set(w.lower() for w in nltk.corpus.words.words())
     unusual = text_vocab.difference(english_vocab)
     return sorted(unusual)


########NEW FILE########
__FILENAME__ = code_virahanka
# Natural Language Toolkit: code_virahanka

def virahanka1(n):
    if n == 0:
        return [""]
    elif n == 1:
        return ["S"]
    else:
        s = ["S" + prosody for prosody in virahanka1(n-1)]
        l = ["L" + prosody for prosody in virahanka1(n-2)]
        return s + l

def virahanka2(n):
    lookup = [[""], ["S"]]
    for i in range(n-1):
        s = ["S" + prosody for prosody in lookup[i+1]]
        l = ["L" + prosody for prosody in lookup[i]]
        lookup.append(s + l)
    return lookup[n]

def virahanka3(n, lookup={0:[""], 1:["S"]}):
    if n not in lookup:
        s = ["S" + prosody for prosody in virahanka3(n-1)]
        l = ["L" + prosody for prosody in virahanka3(n-2)]
        lookup[n] = s + l
    return lookup[n]

from nltk import memoize
@memoize
def virahanka4(n):
    if n == 0:
        return [""]
    elif n == 1:
        return ["S"]
    else:
        s = ["S" + prosody for prosody in virahanka4(n-1)]
        l = ["L" + prosody for prosody in virahanka4(n-2)]
        return s + l


########NEW FILE########
__FILENAME__ = code_viterbi_parse
# Natural Language Toolkit: code_viterbi_parse

grammar = nltk.parse_pcfg('''
  NP  -> NNS [0.5] | JJ NNS [0.3] | NP CC NP [0.2]
  NNS -> "cats" [0.1] | "dogs" [0.2] | "mice" [0.3] | NNS CC NNS [0.4]
  JJ  -> "big" [0.4] | "small" [0.6]
  CC  -> "and" [0.9] | "or" [0.1]
  ''')
viterbi_parser = nltk.ViterbiParser(grammar)


########NEW FILE########
__FILENAME__ = code_wfst
# Natural Language Toolkit: code_wfst

 def init_wfst(tokens, grammar):
     numtokens = len(tokens)
     wfst = [[None for i in range(numtokens+1)] for j in range(numtokens+1)]
     for i in range(numtokens):
         productions = grammar.productions(rhs=tokens[i])
         wfst[i][i+1] = productions[0].lhs()
     return wfst

 def complete_wfst(wfst, tokens, grammar, trace=False):
     index = dict((p.rhs(), p.lhs()) for p in grammar.productions())
     numtokens = len(tokens)
     for span in range(2, numtokens+1):
         for start in range(numtokens+1-span):
             end = start + span
             for mid in range(start+1, end):
                 nt1, nt2 = wfst[start][mid], wfst[mid][end]
                 if nt1 and nt2 and (nt1,nt2) in index:
                     wfst[start][end] = index[(nt1,nt2)]
                     if trace:
                         print "[%s] %3s [%s] %3s [%s] ==> [%s] %3s [%s]" % \
                         (start, nt1, mid, nt2, end, start, index[(nt1,nt2)], end)
     return wfst

 def display(wfst, tokens):
     print '\nWFST ' + ' '.join([("%-4d" % i) for i in range(1, len(wfst))])
     for i in range(len(wfst)-1):
         print "%d   " % i,
         for j in range(1, len(wfst)):
             print "%-4s" % (wfst[i][j] or '.'),
         print


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# NLTK Book documentation build configuration file, created by
# sphinx-quickstart on Sun Oct  9 16:36:44 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.todo', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'book'

# General information about the project.
project = u'NLTK Book'
copyright = u'2011, Steven Bird, Ewan Klein, Edward Loper'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.0'
# The full version, including alpha/beta/rc tags.
release = '2.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'NLTKBookdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('book', 'NLTKBook.tex', u'NLTK Book Documentation',
   u'Steven Bird, Ewan Klein, Edward Loper', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('book', 'nltkbook', u'NLTK Book Documentation',
     [u'Steven Bird, Ewan Klein, Edward Loper'], 1)
]


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'NLTK Book'
epub_author = u'Steven Bird, Ewan Klein, Edward Loper'
epub_publisher = u'Steven Bird, Ewan Klein, Edward Loper'
epub_copyright = u'2011, Steven Bird, Ewan Klein, Edward Loper'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

########NEW FILE########
__FILENAME__ = code_add_cv_field
# Natural Language Toolkit: code_add_cv_field

from nltk.etree.ElementTree import SubElement

def cv(s):
    s = s.lower()
    s = re.sub(r'[^a-z]',     r'_', s)
    s = re.sub(r'[aeiou]',    r'V', s)
    s = re.sub(r'[^V_]',      r'C', s)
    return (s)

def add_cv_field(entry):
    for field in entry:
        if field.tag == 'lx':
            cv_field = SubElement(entry, 'cv')
            cv_field.text = cv(field.text)


########NEW FILE########
__FILENAME__ = code_anneal
# Natural Language Toolkit: code_anneal

from random import randint

def flip(segs, pos):
    return segs[:pos] + str(1-int(segs[pos])) + segs[pos+1:]

def flip_n(segs, n):
    for i in range(n):
        segs = flip(segs, randint(0, len(segs)-1))
    return segs

def anneal(text, segs, iterations, cooling_rate):
    temperature = float(len(segs))
    while temperature > 0.5:
        best_segs, best = segs, evaluate(text, segs)
        for i in range(iterations):
            guess = flip_n(segs, round(temperature))
            score = evaluate(text, guess)
            if score < best:
                best, best_segs = score, guess
        score, segs = best, best_segs
        temperature = temperature / cooling_rate
        print(evaluate(text, segs), segment(text, segs))
    print()
    return segs


########NEW FILE########
__FILENAME__ = code_baseline_tagger
# Natural Language Toolkit: code_baseline_tagger

def performance(cfd, wordlist):
    lt = dict((word, cfd[word].max()) for word in wordlist)
    baseline_tagger = nltk.UnigramTagger(model=lt, backoff=nltk.DefaultTagger('NN'))
    return baseline_tagger.evaluate(brown.tagged_sents(categories='news'))

def display():
    import pylab
    words_by_freq = list(nltk.FreqDist(brown.words(categories='news')))
    cfd = nltk.ConditionalFreqDist(brown.tagged_words(categories='news'))
    sizes = 2 ** pylab.arange(15)
    perfs = [performance(cfd, words_by_freq[:size]) for size in sizes]
    pylab.plot(sizes, perfs, '-bo')
    pylab.title('Lookup Tagger Performance with Varying Model Size')
    pylab.xlabel('Model Size')
    pylab.ylabel('Performance')
    pylab.show()


########NEW FILE########
__FILENAME__ = code_bottom_up_chart_parsers
# Natural Language Toolkit: code_bottom_up_chart_parsers

inside_parser = nltk.InsideChartParser(grammar)
longest_parser = nltk.LongestChartParser(grammar)
beam_parser = nltk.InsideChartParser(grammar, beam_size=20)


########NEW FILE########
__FILENAME__ = code_brill_demo
# Natural Language Toolkit: code_brill_demo


########NEW FILE########
__FILENAME__ = code_cascaded_chunker
# Natural Language Toolkit: code_cascaded_chunker

grammar = r"""
  NP: {<DT|JJ|NN.*>+}          # Chunk sequences of DT, JJ, NN
  PP: {<IN><NP>}               # Chunk prepositions followed by NP
  VP: {<VB.*><NP|PP|CLAUSE>+$} # Chunk verbs and their arguments
  CLAUSE: {<NP><VP>}           # Chunk NP, VP
  """
cp = nltk.RegexpParser(grammar)
sentence = [("Mary", "NN"), ("saw", "VBD"), ("the", "DT"), ("cat", "NN"),
    ("sit", "VB"), ("on", "IN"), ("the", "DT"), ("mat", "NN")]


########NEW FILE########
__FILENAME__ = code_cfg1
# Natural Language Toolkit: code_cfg1

grammar1 = nltk.parse_cfg("""
  S -> NP VP
  VP -> V NP | V NP PP
  PP -> P NP
  V -> "saw" | "ate" | "walked"
  NP -> "John" | "Mary" | "Bob" | Det N | Det N PP
  Det -> "a" | "an" | "the" | "my"
  N -> "man" | "dog" | "cat" | "telescope" | "park"
  P -> "in" | "on" | "by" | "with"
  """)


########NEW FILE########
__FILENAME__ = code_cfg2
# Natural Language Toolkit: code_cfg2

grammar2 = nltk.parse_cfg("""
  S  -> NP VP
  NP -> Det Nom | PropN
  Nom -> Adj Nom | N
  VP -> V Adj | V NP | V S | V NP PP
  PP -> P NP
  PropN -> 'Buster' | 'Chatterer' | 'Joe'
  Det -> 'the' | 'a'
  N -> 'bear' | 'squirrel' | 'tree' | 'fish' | 'log'
  Adj  -> 'angry' | 'frightened' |  'little' | 'tall'
  V ->  'chased'  | 'saw' | 'said' | 'thought' | 'was' | 'put'
  P -> 'on'
  """)


########NEW FILE########
__FILENAME__ = code_check_parens
# Natural Language Toolkit: code_check_parens

def check_parens(tokens):
    stack = []
    for token in tokens:
        if token == '(':     # push
            stack.append(token)
        elif token == ')':   # pop
            stack.pop()
    return stack


########NEW FILE########
__FILENAME__ = code_chinker
# Natural Language Toolkit: code_chinker

grammar = r"""
  NP:
    {<.*>+}          # Chunk everything
    }<VBD|IN>+{      # Chink sequences of VBD and IN
  """
sentence = [("the", "DT"), ("little", "JJ"), ("yellow", "JJ"),
       ("dog", "NN"), ("barked", "VBD"), ("at", "IN"),  ("the", "DT"), ("cat", "NN")]
cp = nltk.RegexpParser(grammar)


########NEW FILE########
__FILENAME__ = code_chunker1
# Natural Language Toolkit: code_chunker1

grammar = r"""
  NP: {<DT|PP\$>?<JJ>*<NN>}   # chunk determiner/possessive, adjectives and noun
      {<NNP>+}                # chunk sequences of proper nouns
"""
cp = nltk.RegexpParser(grammar)
sentence = [("Rapunzel", "NNP"), ("let", "VBD"), ("down", "RP"), # [_code-chunker1-ex]
                 ("her", "PP$"), ("long", "JJ"), ("golden", "JJ"), ("hair", "NN")]


########NEW FILE########
__FILENAME__ = code_chunkex
# Natural Language Toolkit: code_chunkex


########NEW FILE########
__FILENAME__ = code_chunk_toolbox
# Natural Language Toolkit: code_chunk_toolbox

from nltk_contrib import toolbox

grammar = r"""
      lexfunc: {<lf>(<lv><ln|le>*)*}
      example: {<rf|xv><xn|xe>*}
      sense:   {<sn><ps><pn|gv|dv|gn|gp|dn|rn|ge|de|re>*<example>*<lexfunc>*}
      record:   {<lx><hm><sense>+<dt>}
    """


########NEW FILE########
__FILENAME__ = code_classification_based_segmenter
# Natural Language Toolkit: code_classification_based_segmenter

def segment_sentences(words):
    start = 0
    sents = []
    for i, word in enumerate(words):
        if word in '.?!' and classifier.classify(punct_features(words, i)) == True:
            sents.append(words[start:i+1])
            start = i+1
    if start < len(words):
        sents.append(words[start:])
    return sents


########NEW FILE########
__FILENAME__ = code_classifier_chunker
# Natural Language Toolkit: code_classifier_chunker

class ConsecutiveNPChunkTagger(nltk.TaggerI): # [_consec-chunk-tagger]

    def __init__(self, train_sents):
        train_set = []
        for tagged_sent in train_sents:
            untagged_sent = nltk.tag.untag(tagged_sent)
            history = []
            for i, (word, tag) in enumerate(tagged_sent):
                featureset = npchunk_features(untagged_sent, i, history) # [_consec-use-fe]
                train_set.append( (featureset, tag) )
                history.append(tag)
        self.classifier = nltk.MaxentClassifier.train( # [_consec-use-maxent]
            train_set, algorithm='megam', trace=0)

    def tag(self, sentence):
        history = []
        for i, word in enumerate(sentence):
            featureset = npchunk_features(sentence, i, history)
            tag = self.classifier.classify(featureset)
            history.append(tag)
        return zip(sentence, history)

class ConsecutiveNPChunker(nltk.ChunkParserI): # [_consec-chunker]
    def __init__(self, train_sents):
        tagged_sents = [[((w,t),c) for (w,t,c) in
                         nltk.chunk.tree2conlltags(sent)]
                        for sent in train_sents]
        self.tagger = ConsecutiveNPChunkTagger(tagged_sents)

    def parse(self, sentence):
        tagged_sents = self.tagger.tag(sentence)
        conlltags = [(w,t,c) for ((w,t),c) in tagged_sents]
        return nltk.chunk.conlltags2tree(conlltags)


########NEW FILE########
__FILENAME__ = code_consecutive_pos_tagger
# Natural Language Toolkit: code_consecutive_pos_tagger

 def pos_features(sentence, i, history): # [_consec-pos-tag-features]
     features = {"suffix(1)": sentence[i][-1:],
                 "suffix(2)": sentence[i][-2:],
                 "suffix(3)": sentence[i][-3:]}
     if i == 0:
         features["prev-word"] = "<START>"
         features["prev-tag"] = "<START>"
     else:
         features["prev-word"] = sentence[i-1]
         features["prev-tag"] = history[i-1]
     return features

class ConsecutivePosTagger(nltk.TaggerI): # [_consec-pos-tagger]

    def __init__(self, train_sents):
        train_set = []
        for tagged_sent in train_sents:
            untagged_sent = nltk.tag.untag(tagged_sent)
            history = []
            for i, (word, tag) in enumerate(tagged_sent):
                featureset = pos_features(untagged_sent, i, history)
                train_set.append( (featureset, tag) )
                history.append(tag)
        self.classifier = nltk.NaiveBayesClassifier.train(train_set)

    def tag(self, sentence):
        history = []
        for i, word in enumerate(sentence):
            featureset = pos_features(sentence, i, history)
            tag = self.classifier.classify(featureset)
            history.append(tag)
        return zip(sentence, history)


########NEW FILE########
__FILENAME__ = code_convert_parens
# Natural Language Toolkit: code_convert_parens

def convert_parens(tokens):
    stack = [[]]
    for token in tokens:
        if token == '(':     # push
            sublist = []
            stack[-1].append(sublist)
            stack.append(sublist)
        elif token == ')':   # pop
            stack.pop()
        else:                # update top of stack
            stack[-1].append(token)
    return stack[0]


########NEW FILE########
__FILENAME__ = code_dictionary
# Natural Language Toolkit: code_dictionary


########NEW FILE########
__FILENAME__ = code_document_classify_fd
# Natural Language Toolkit: code_document_classify_fd

all_words = nltk.FreqDist(w.lower() for w in movie_reviews.words())
word_features = all_words.keys()[:2000] # [_document-classify-all-words]

def document_features(document): # [_document-classify-extractor]
    document_words = set(document) # [_document-classify-set]
    features = {}
    for word in word_features:
        features['contains(%s)' % word] = (word in document_words)
    return features


########NEW FILE########
__FILENAME__ = code_document_classify_use
# Natural Language Toolkit: code_document_classify_use

featuresets = [(document_features(d), c) for (d,c) in documents]
train_set, test_set = featuresets[100:], featuresets[:100]
classifier = nltk.NaiveBayesClassifier.train(train_set)


########NEW FILE########
__FILENAME__ = code_entropy
# Natural Language Toolkit: code_entropy

import math
def entropy(labels):
    freqdist = nltk.FreqDist(labels)
    probs = [freqdist.freq(l) for l in freqdist]
    return -sum([p * math.log(p,2) for p in probs])


########NEW FILE########
__FILENAME__ = code_epytext
# Natural Language Toolkit: code_epytext

def accuracy(reference, test):
    """
    Calculate the fraction of test items that equal the corresponding reference items.

    Given a list of reference values and a corresponding list of test values,
    return the fraction of corresponding values that are equal.
    In particular, return the fraction of indexes
    {0<i<=len(test)} such that C{test[i] == reference[i]}.


########NEW FILE########
__FILENAME__ = code_evaluate
# Natural Language Toolkit: code_evaluate

def evaluate(text, segs):
    words = segment(text, segs)
    text_size = len(words)
    lexicon_size = len(' '.join(set(words)))
    return text_size + lexicon_size


########NEW FILE########
__FILENAME__ = code_feat0cfg
# Natural Language Toolkit: code_feat0cfg


########NEW FILE########
__FILENAME__ = code_featstructures
# Natural Language Toolkit: code_featstructures

fs1 = nltk.FeatStruct("[A = ?x, B= [C = ?x]]")
fs2 = nltk.FeatStruct("[B = [D = d]]")
fs3 = nltk.FeatStruct("[B = [C = d]]")
fs4 = nltk.FeatStruct("[A = (1)[B = b], C->(1)]")
fs5 = nltk.FeatStruct("[A = (1)[D = ?x], C = [E -> (1), F = ?x] ]")
fs6 = nltk.FeatStruct("[A = [D = d]]")
fs7 = nltk.FeatStruct("[A = [D = d], C = [F = [D = d]]]")
fs8 = nltk.FeatStruct("[A = (1)[D = ?x, G = ?x], C = [B = ?x, E -> (1)] ]")
fs9 = nltk.FeatStruct("[A = [B = b], C = [E = [G = e]]]")
fs10 = nltk.FeatStruct("[A = (1)[B = b], C -> (1)]")


########NEW FILE########
__FILENAME__ = code_featurecharttrace
# Natural Language Toolkit: code_featurecharttrace


########NEW FILE########
__FILENAME__ = code_findtags
# Natural Language Toolkit: code_findtags

 def findtags(tag_prefix, tagged_text):
     cfd = nltk.ConditionalFreqDist((tag, word) for (word, tag) in tagged_text
                                   if tag.startswith(tag_prefix))
     return dict((tag, cfd[tag].most_common(5)) for tag in cfd.conditions())


########NEW FILE########
__FILENAME__ = code_freq_words1
# Natural Language Toolkit: code_freq_words1

from bs4 import BeautifulSoup
from urllib import request

def freq_words(url, freqdist, n):
    response = request.urlopen(url)
    html = response.read().decode('utf8')
    raw = BeautifulSoup(html).get_text()
    for word in word_tokenize(raw):
        freqdist[word.lower()] += 1
    print(freqdist.most_common(n))


########NEW FILE########
__FILENAME__ = code_freq_words2
# Natural Language Toolkit: code_freq_words2

def freq_words(url):
    text = nltk.clean_url(url)
    freqdist = nltk.FreqDist(word.lower() for word in word_tokenize(text))
    return freqdist


########NEW FILE########
__FILENAME__ = code_gender_features_overfitting
# Natural Language Toolkit: code_gender_features_overfitting

def gender_features2(name):
    features = {}
    features["first_letter"] = name[0].lower()
    features["last_letter"] = name[-1].lower()
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        features["count(%s)" % letter] = name.lower().count(letter)
        features["has(%s)" % letter] = (letter in name.lower())
    return features


########NEW FILE########
__FILENAME__ = code_germancfg
# Natural Language Toolkit: code_germancfg


########NEW FILE########
__FILENAME__ = code_get_text
# Natural Language Toolkit: code_get_text

import re
def get_text(file):
    """Read text from a file, normalizing whitespace and stripping HTML markup."""
    text = open(file).read()
    text = re.sub('\s+', ' ', text)
    text = re.sub(r'<.*?>', ' ', text)
    return text


########NEW FILE########
__FILENAME__ = code_give
# Natural Language Toolkit: code_give

def give(t):
    return t.label() == 'VP' and len(t) > 2 and t[1].label() == 'NP'\
           and (t[2].label() == 'PP-DTV' or t[2].label() == 'NP')\
           and ('give' in t[0].leaves() or 'gave' in t[0].leaves())
def sent(t):
    return ' '.join(token for token in t.leaves() if token[0] not in '*-0')
def print_node(t, width):
        output = "%s %s: %s / %s: %s" %\
            (sent(t[0]), t[1].label(), sent(t[1]), t[2].label(), sent(t[2]))
        if len(output) > width:
            output = output[:width] + "..."
        print(output)


########NEW FILE########
__FILENAME__ = code_hill_climb
# Natural Language Toolkit: code_hill_climb

def flip(segs, pos):
    return segs[:pos] + `1-int(segs[pos])` + segs[pos+1:]
def hill_climb(text, segs, iterations):
    for i in range(iterations):
        pos, best = 0, evaluate(text, segs)
        for i in range(len(segs)):
            score = evaluate(text, flip(segs, i))
            if score < best:
                pos, best = i, score
        if pos != 0:
            segs = flip(segs, pos)
            print evaluate(text, segs), segment(text, segs)
    return segs


########NEW FILE########
__FILENAME__ = code_html2csv
# Natural Language Toolkit: code_html2csv

def lexical_data(html_file):
    SEP = '_ENTRY'
    html = open(html_file).read()
    html = re.sub(r'<p', SEP + '<p', html)
    text = nltk.clean_html(html)
    text = ' '.join(text.split())
    for entry in text.split(SEP):
        if entry.count(' ') > 2:
            yield entry.split(' ', 3)


########NEW FILE########
__FILENAME__ = code_modal_plot
# Natural Language Toolkit: code_modal_plot

colors = 'rgbcmyk' # red, green, blue, cyan, magenta, yellow, black
def bar_chart(categories, words, counts):
    "Plot a bar chart showing counts for each word by category"
    import pylab
    ind = pylab.arange(len(words))
    width = 1 / (len(categories) + 1)
    bar_groups = []
    for c in range(len(categories)):
        bars = pylab.bar(ind+c*width, counts[categories[c]], width,
                         color=colors[c % len(colors)])
        bar_groups.append(bars)
    pylab.xticks(ind+width, words)
    pylab.legend([b[0] for b in bar_groups], categories, loc='upper left')
    pylab.ylabel('Frequency')
    pylab.title('Frequency of Six Modal Verbs by Genre')
    pylab.show()


########NEW FILE########
__FILENAME__ = code_modal_tabulate
# Natural Language Toolkit: code_modal_tabulate

 def tabulate(cfdist, words, categories):
     print('%-16s' % 'Category', end=' ')                    # column headings
     for word in words:
         print('%6s' % word, end=' ')
     print
     for category in categories:
         print('%-16s' % category, end=' ')                  # row heading
         for word in words:                                  # for each word
             print('%6d' % cfdist[category][word], end=' ')  # print table cell
         print                                               # end the row


########NEW FILE########
__FILENAME__ = code_networkx
# Natural Language Toolkit: code_networkx

import networkx as nx
import matplotlib
from nltk.corpus import wordnet as wn

def traverse(graph, start, node):
    graph.depth[node.name] = node.shortest_path_distance(start)
    for child in node.hyponyms():
        graph.add_edge(node.name, child.name) # [_add-edge]
        traverse(graph, start, child) # [_recursive-traversal]

def hyponym_graph(start):
    G = nx.Graph() # [_define-graph]
    G.depth = {}
    traverse(G, start, start)
    return G

def graph_draw(graph):
    nx.draw_graphviz(graph,
         node_size = [16 * graph.degree(n) for n in graph],
         node_color = [graph.depth[n] for n in graph],
         with_labels = False)
    matplotlib.pyplot.show()


########NEW FILE########
__FILENAME__ = code_pcfg1
# Natural Language Toolkit: code_pcfg1

grammar = nltk.parse_pcfg("""
    S    -> NP VP              [1.0]
    VP   -> TV NP              [0.4]
    VP   -> IV                 [0.3]
    VP   -> DatV NP NP         [0.3]
    TV   -> 'saw'              [1.0]
    IV   -> 'ate'              [1.0]
    DatV -> 'gave'             [1.0]
    NP   -> 'telescopes'       [0.8]
    NP   -> 'Jack'             [0.2]
    """)


########NEW FILE########
__FILENAME__ = code_plural
# Natural Language Toolkit: code_plural

def plural(word):
    if word.endswith('y'):
        return word[:-1] + 'ies'
    elif word[-1] in 'sx' or word[-2:] in ['sh', 'ch']:
        return word + 'es'
    elif word.endswith('an'):
        return word[:-2] + 'en'
    else:
        return word + 's'


########NEW FILE########
__FILENAME__ = code_random_text
# Natural Language Toolkit: code_random_text

def generate_model(cfdist, word, num=15):
    for i in range(num):
        print(word, end=' ')
        word = cfdist[word].max()

text = nltk.corpus.genesis.words('english-kjv.txt')
bigrams = nltk.bigrams(text)
cfd = nltk.ConditionalFreqDist(bigrams) # [_bigram-condition]


########NEW FILE########
__FILENAME__ = code_rte_features
# Natural Language Toolkit: code_rte_features

def rte_features(rtepair):
    extractor = nltk.RTEFeatureExtractor(rtepair)
    features = {}
    features['word_overlap'] = len(extractor.overlap('word'))
    features['word_hyp_extra'] = len(extractor.hyp_extra('word'))
    features['ne_overlap'] = len(extractor.overlap('ne'))
    features['ne_hyp_extra'] = len(extractor.hyp_extra('ne'))
    return features


########NEW FILE########
__FILENAME__ = code_search_documents
# Natural Language Toolkit: code_search_documents

def raw(file):
    contents = open(file).read()
    contents = re.sub(r'<.*?>', ' ', contents)
    contents = re.sub('\s+', ' ', contents)
    return contents

def snippet(doc, term): # buggy
    text = ' '*30 + raw(doc) + ' '*30
    pos = text.index(term)
    return text[pos-30:pos+30]

print("Building Index...")
files = nltk.corpus.movie_reviews.abspaths()
idx = nltk.Index((w, f) for f in files for w in raw(f).split())

query = ''
while query != "quit":
    query = raw_input("query> ")
    if query in idx:
        for doc in idx[query]:
            print(snippet(doc, query))
    else:
        print("Not found")


########NEW FILE########
__FILENAME__ = code_search_examples
# Natural Language Toolkit: code_search_examples

def search1(substring, words):
    result = []
    for word in words:
        if substring in word:
            result.append(word)
    return result

def search2(substring, words):
    for word in words:
        if substring in word:
            yield word


########NEW FILE########
__FILENAME__ = code_segment
# Natural Language Toolkit: code_segment

def segment(text, segs):
    words = []
    last = 0
    for i in range(len(segs)):
        if segs[i] == '1':
            words.append(text[last:i+1])
            last = i+1
    words.append(text[last:])
    return words


########NEW FILE########
__FILENAME__ = code_sentential_complement
# Natural Language Toolkit: code_sentential_complement

def filter(tree):
    child_nodes = [child.label() for child in tree
                   if isinstance(child, nltk.Tree)]
    return  (tree.label() == 'VP') and ('S' in child_nodes)


########NEW FILE########
__FILENAME__ = code_slashcfg
# Natural Language Toolkit: code_slashcfg


########NEW FILE########
__FILENAME__ = code_stemmer_indexing
# Natural Language Toolkit: code_stemmer_indexing

class IndexedText(object):

    def __init__(self, stemmer, text):
        self._text = text
        self._stemmer = stemmer
        self._index = nltk.Index((self._stem(word), i)
                                 for (i, word) in enumerate(text))

    def concordance(self, word, width=40):
        key = self._stem(word)
        wc = width/4                # words of context
        for i in self._index[key]:
            lcontext = ' '.join(self._text[i-wc:i])
            rcontext = ' '.join(self._text[i:i+wc])
            ldisplay = '%*s'  % (width, lcontext[-width:])
            rdisplay = '%-*s' % (width, rcontext[:width])
            print(ldisplay, rdisplay)

    def _stem(self, word):
        return self._stemmer.stem(word).lower()


########NEW FILE########
__FILENAME__ = code_strings_to_ints
# Natural Language Toolkit: code_strings_to_ints

def preprocess(tagged_corpus):
    words = set()
    tags = set()
    for sent in tagged_corpus:
        for word, tag in sent:
            words.add(word)
            tags.add(tag)
    wm = dict((w,i) for (i,w) in enumerate(words))
    tm = dict((t,i) for (i,t) in enumerate(tags))
    return [[(wm[w], tm[t]) for (w,t) in sent] for sent in tagged_corpus]


########NEW FILE########
__FILENAME__ = code_suffix_pos_tag
# Natural Language Toolkit: code_suffix_pos_tag

def pos_features(sentence, i): # [_suffix-pos-tag-fd]
    features = {"suffix(1)": sentence[i][-1:],
                "suffix(2)": sentence[i][-2:],
                "suffix(3)": sentence[i][-3:]}
    if i == 0:
        features["prev-word"] = "<START>"
    else:
        features["prev-word"] = sentence[i-1]
    return features


########NEW FILE########
__FILENAME__ = code_three_word_phrase
# Natural Language Toolkit: code_three_word_phrase

 from nltk.corpus import brown
 def process(sentence):
     for (w1,t1), (w2,t2), (w3,t3) in nltk.trigrams(sentence): # [_three-word]
         if (t1.startswith('V') and t2 == 'TO' and t3.startswith('V')): # [_verb-to-verb]
             print(w1, w2, w3) # [_print-words]


########NEW FILE########
__FILENAME__ = code_toolbox_validation
# Natural Language Toolkit: code_toolbox_validation

grammar = nltk.parse_cfg('''
  S -> Head PS Glosses Comment Date Sem_Field Examples
  Head -> Lexeme Root
  Lexeme -> "lx"
  Root -> "rt" |
  PS -> "ps"
  Glosses -> Gloss Glosses |
  Gloss -> "ge" | "tkp" | "eng"
  Date -> "dt"
  Sem_Field -> "sf"
  Examples -> Example Ex_Pidgin Ex_English Examples |
  Example -> "ex"
  Ex_Pidgin -> "xp"
  Ex_English -> "xe"
  Comment -> "cmt" | "nt" |
  ''')

def validate_lexicon(grammar, lexicon, ignored_tags):
    rd_parser = nltk.RecursiveDescentParser(grammar)
    for entry in lexicon:
        marker_list = [field.tag for field in entry if field.tag not in ignored_tags]
        if rd_parser.nbest_parse(marker_list):
            print "+", ':'.join(marker_list) # [_accepted-entries]
        else:
            print "-", ':'.join(marker_list) # [_rejected-entries]


########NEW FILE########
__FILENAME__ = code_traverse
# Natural Language Toolkit: code_traverse

def traverse(t):
    try:
        t.label()
    except AttributeError:
        print(t, end=" ")
    else:
        # Now we know that t.node is defined
        print('(', t.label(), end=" ")
        for child in t:
            traverse(child)
        print(')', end=" ")


########NEW FILE########
__FILENAME__ = code_trie
# Natural Language Toolkit: code_trie

def insert(trie, key, value):
    if key:
        first, rest = key[0], key[1:]
        if first not in trie:
            trie[first] = {}
        insert(trie[first], rest, value)
    else:
        trie['value'] = value


########NEW FILE########
__FILENAME__ = code_unigram_chunker
# Natural Language Toolkit: code_unigram_chunker

class UnigramChunker(nltk.ChunkParserI):
    def __init__(self, train_sents): # [_code-unigram-chunker-constructor]
        train_data = [[(t,c) for w,t,c in nltk.chunk.tree2conlltags(sent)]
                      for sent in train_sents]
        self.tagger = nltk.UnigramTagger(train_data) # [_code-unigram-chunker-buildit]

    def parse(self, sentence): # [_code-unigram-chunker-parse]
        pos_tags = [pos for (word,pos) in sentence]
        tagged_pos_tags = self.tagger.tag(pos_tags)
        chunktags = [chunktag for (pos, chunktag) in tagged_pos_tags]
        conlltags = [(word, pos, chunktag) for ((word,pos),chunktag)
                     in zip(sentence, chunktags)]
        return nltk.chunk.conlltags2tree(conlltags)


########NEW FILE########
__FILENAME__ = code_unusual
# Natural Language Toolkit: code_unusual

 def unusual_words(text):
     text_vocab = set(w.lower() for w in text if w.isalpha())
     english_vocab = set(w.lower() for w in nltk.corpus.words.words())
     unusual = text_vocab.difference(english_vocab)
     return sorted(unusual)


########NEW FILE########
__FILENAME__ = code_virahanka
# Natural Language Toolkit: code_virahanka

def virahanka1(n):
    if n == 0:
        return [""]
    elif n == 1:
        return ["S"]
    else:
        s = ["S" + prosody for prosody in virahanka1(n-1)]
        l = ["L" + prosody for prosody in virahanka1(n-2)]
        return s + l

def virahanka2(n):
    lookup = [[""], ["S"]]
    for i in range(n-1):
        s = ["S" + prosody for prosody in lookup[i+1]]
        l = ["L" + prosody for prosody in lookup[i]]
        lookup.append(s + l)
    return lookup[n]

def virahanka3(n, lookup={0:[""], 1:["S"]}):
    if n not in lookup:
        s = ["S" + prosody for prosody in virahanka3(n-1)]
        l = ["L" + prosody for prosody in virahanka3(n-2)]
        lookup[n] = s + l
    return lookup[n]

from nltk import memoize
@memoize
def virahanka4(n):
    if n == 0:
        return [""]
    elif n == 1:
        return ["S"]
    else:
        s = ["S" + prosody for prosody in virahanka4(n-1)]
        l = ["L" + prosody for prosody in virahanka4(n-2)]
        return s + l


########NEW FILE########
__FILENAME__ = code_viterbi_parse
# Natural Language Toolkit: code_viterbi_parse

grammar = nltk.parse_pcfg('''
  NP  -> NNS [0.5] | JJ NNS [0.3] | NP CC NP [0.2]
  NNS -> "cats" [0.1] | "dogs" [0.2] | "mice" [0.3] | NNS CC NNS [0.4]
  JJ  -> "big" [0.4] | "small" [0.6]
  CC  -> "and" [0.9] | "or" [0.1]
  ''')
viterbi_parser = nltk.ViterbiParser(grammar)


########NEW FILE########
__FILENAME__ = code_wfst
# Natural Language Toolkit: code_wfst

 def init_wfst(tokens, grammar):
     numtokens = len(tokens)
     wfst = [[None for i in range(numtokens+1)] for j in range(numtokens+1)]
     for i in range(numtokens):
         productions = grammar.productions(rhs=tokens[i])
         wfst[i][i+1] = productions[0].lhs()
     return wfst

 def complete_wfst(wfst, tokens, grammar, trace=False):
     index = dict((p.rhs(), p.lhs()) for p in grammar.productions())
     numtokens = len(tokens)
     for span in range(2, numtokens+1):
         for start in range(numtokens+1-span):
             end = start + span
             for mid in range(start+1, end):
                 nt1, nt2 = wfst[start][mid], wfst[mid][end]
                 if nt1 and nt2 and (nt1,nt2) in index:
                     wfst[start][end] = index[(nt1,nt2)]
                     if trace:
                         print("[%s] %3s [%s] %3s [%s] ==> [%s] %3s [%s]" % \
                         (start, nt1, mid, nt2, end, start, index[(nt1,nt2)], end))
     return wfst

 def display(wfst, tokens):
     print('\nWFST ' + ' '.join([("%-4d" % i) for i in range(1, len(wfst))]))
     for i in range(len(wfst)-1):
         print("%d   " % i, end=" ")
         for j in range(1, len(wfst)):
             print("%-4s" % (wfst[i][j] or '.'), end=" ")
         print()


########NEW FILE########
