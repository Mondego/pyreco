__FILENAME__ = 1 - Word splitting
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

from __future__ import unicode_literals

# <codecell>

text = '''"Word splitting shouldn't be hard," you might say. "Words are things separated by spaces."'''

# <codecell>

for word in text.split(' '):
    print word

# <codecell>

import re
for word in re.findall(r'[A-Za-z]+', text):
    print word

# <codecell>

import nltk

# <codecell>

for sent in nltk.sent_tokenize(text):
    print
    for word in nltk.word_tokenize(sent):
        print word

# <codecell>

from nltk.corpus import wordnet

# <codecell>

# Deal with suffixes
for sent in nltk.sent_tokenize(text):
    for word in nltk.word_tokenize(sent):
        word = word.lower()
        print wordnet.morphy(word) or word

# <codecell>

from metanl import english

# <codecell>

# Deal with even more suffixes
for word in english.normalize_list(text):
    print word

# <codecell>



########NEW FILE########
__FILENAME__ = 2 - Interesting n-grams
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

from nltk.book import *

# <codecell>

import nltk

# <codecell>

nltk.bigrams(text1[4712:4732])

# <codecell>

text1.collocations()

# <codecell>

text3.collocations()

# <codecell>

text2.collocations()

# <codecell>

text6.collocations()

# <codecell>



########NEW FILE########
__FILENAME__ = 3 - Movie review classifier
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

import nltk
from nltk.corpus import movie_reviews
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.naive_bayes import BernoulliNB, MultinomialNB
import numpy as np
import random

# <codecell>

# Get a list of (document text, category)
documents = [
    (movie_reviews.raw(fileid), category)
    for category in movie_reviews.categories()
    for fileid in movie_reviews.fileids(category)
]
random.seed(3)
random.shuffle(documents)

# <codecell>

reviewtext, rating = documents[0]
print reviewtext
print rating

# <codecell>

train_samples, test_samples = documents[:1000], documents[1000:]

# <codecell>

# Make feature vectors out of the documents, based on which words they contain
vectorizer = CountVectorizer(binary=True)
train_vectors = vectorizer.fit_transform([doc for doc, target in train_samples])
test_vectors = vectorizer.transform([doc for doc, target in test_samples])
train_targets = [target for doc, target in train_samples]
test_targets = [target for doc, target in test_samples]

# <codecell>

classifier = BernoulliNB()

# <codecell>

classifier.fit(train_vectors, train_targets)

# <codecell>

classifier.score(test_vectors, test_targets)

# <codecell>

# A helper function to see which features affect the classification the most
def show_most_informative_features(vectorizer, classifier, n=10):
    neg = classifier.feature_log_prob_[0]
    pos = classifier.feature_log_prob_[1]
    valence = (pos - neg)
    ordered = np.argsort(valence)
    interesting = np.hstack([ordered[:n], ordered[-n:]])
    feature_names = vectorizer.get_feature_names()
    for index in ordered[:n]:
        print "%+4.4f\t%s" % (valence[index], feature_names[index])
    print '\t...'
    for index in ordered[-n:]:
        print "%+4.4f\t%s" % (valence[index], feature_names[index])
    

# <codecell>

show_most_informative_features(vectorizer, classifier)

# <codecell>



########NEW FILE########
__FILENAME__ = 4 - Similarity over movie reviews
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

import nltk
from nltk.corpus import movie_reviews
import numpy as np

# <codecell>

documents = [
    list(movie_reviews.words(fileid))
    for category in movie_reviews.categories()
    for fileid in movie_reviews.fileids(category)
]

# <codecell>

print ' '.join(documents[1])

# <codecell>

from gensim import models, similarities, corpora

# <codecell>

dictionary = corpora.Dictionary(documents)
corpus = [dictionary.doc2bow(text) for text in documents]

# <codecell>

len(dictionary), len(corpus)

# <codecell>

tfidf = models.TfidfModel(corpus)
corpus_tfidf = tfidf[corpus]
lsi = models.LsiModel(corpus_tfidf, id2word=dictionary, num_topics=50)

# <codecell>

# Gives us an object where we put in an appropriate reduced
# bag of words, and it gives us similarity over all documents
similarity = similarities.MatrixSimilarity(lsi[corpus])

# <codecell>

# Here's a way to get a similarity vector.
def doc_similarities(doc):
    bag_of_words = dictionary.doc2bow(doc)
    return similarity[lsi[bag_of_words]]

# <codecell>

# A useful function for looking at what's going on.
#
# It takes in a vector of how similar N things are to some input.
# It also takes a 'display_func' to tell it how to show you what
# those N things actually are.
def show_similar(similarities, display_func):
    best_matches = np.argsort(similarities)[::-1][:10]
    for index in best_matches:
        print "%4.4f\t%s" % (similarities[index], display_func(index))

# <codecell>

# And here's the display_func we'll need.
def brief_document(index):
    doc = documents[index]
    return ' '.join(doc)[:200] + '...'

# <codecell>

show_similar(doc_similarities(documents[1]), brief_document)

# <codecell>



########NEW FILE########
__FILENAME__ = 5 - WordNet
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

from nltk.corpus import wordnet as wn

# <codecell>

[(synset, synset.definition) for synset in wn.synsets('dog')]

# <codecell>

dog = wn.synset('dog.n.01')
cat = wn.synset('cat.n.01')
toaster = wn.synset('toaster.n.01')

# <codecell>

wn.wup_similarity(dog, cat)

# <codecell>

wn.wup_similarity(cat, toaster)

# <codecell>

wn.morphy('dogs'), wn.morphy('barked')

# <codecell>

[(synset, synset.definition) for synset in wn.synsets('bark')]

# <codecell>

print wn.wup_similarity(wn.synset('dog.n.01'), wn.synset('bark.n.04'))

# <codecell>



########NEW FILE########
__FILENAME__ = 6 - ConceptNet
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

import requests
import json

# <codecell>

BASE = 'http://conceptnet5.media.mit.edu/data/5.2'

# <codecell>

def conceptnet_lookup(uri):
    return requests.get(BASE + uri).json()

# <codecell>

for edge in conceptnet_lookup('/c/en/learn')['edges']:
    print [edge['rel'], edge['start'], edge['end']]

# <codecell>

conceptnet_lookup('/assoc/list/en/good@1,bad@-1')

# <codecell>

conceptnet_lookup('/assoc/list/en/good@1,bad@-1?filter=/c/en')

# <codecell>

conceptnet_lookup('/assoc/list/en/good@-1,bad@1?filter=/c/en')

# <codecell>

conceptnet_lookup('/assoc/c/en/travel?filter=/c/en')

# <codecell>



########NEW FILE########
