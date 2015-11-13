__FILENAME__ = corpora


class Corpus:
  def __init__(self, corpus_name):
    self._name = corpus_name

  def docs(self, num_docs, train=True):
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = dirichlet_words
#!/usr/bin/python

# dirichlet_words.py: Class to store counts and compute probabilities over
# words in topics. Views process as a three level process. Each topic is drawn
# from a base distribution over words shared among all topics. The word
# distribution backs off to a monkey at a typwriter distribution.
#
# Written by Jordan Boyd-Graber and Jessy Cowan-Sharp
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from nltk import FreqDist
import string, random
import numpy as n

from math import log

CHAR_SMOOTHING = 1 / 10000.

def probability_vector(dims):
    ''' generates a randomized probability vector of the specified dimensions
    (sums up to one) '''
    values = [random.random() for d in xrange(dims)]
    return [v/sum(values) for v in values]

class DirichletWords(object):

  def initialize_index(self):
    self.word_to_int = {}
    self.int_to_word = {}


  def __init__(self, num_topics, alpha_topic = 1.0, alpha_word = 1.0, 
               max_tables = 50000, sanity_check=False, initialize=False,
               report_filename="topic_history.txt"):

    self.max_tables = max_tables
    self._alphabet = FreqDist()
    # store all words seen in a list so they are associated with a unique ID.

    self.initialize_index()

    self._words = FreqDist()

    self.alpha_topic = alpha_topic
    self.alpha_word = alpha_word

    self._num_updates = 0
    self._report = None
    if report_filename:
        self._report = open(report_filename, 'w')

    self.num_topics = num_topics
    self._topics = [FreqDist() for x in xrange(num_topics)]

    # the sanity_check flag is for testing only. 
    if initialize and sanity_check == True:
        self.deterministic_seed()
    elif initialize:
        self.initialize_topics()

  def deterministic_seed(self):
    ''' if sanity_check = True, this will seed the topics with enough variance
    to evolve but do so in the most basic and deterministic way possible, so a
    user can follow along each step of the algorithm'''

    chars = "abcdefghijklmnopqrstuvwxyz"
    for i in xrange(3):
      word = random.choice(chars)
      self.index(word)
      topic_weights = probability_vector(self.num_topics)
      for k in xrange(self.num_topics):
        self.update_count(word, k, topic_weights[k])

  def initialize_topics(self):
    ''' initializes the topics with some random seed words so that they have
        enough relative bias to evolve when new words are passed in.  '''
    # we are going to create some random string from /dev/urandom. to convert
    # them to a string, we need a translation table that is 256 characters. 
    translate_table = (string.letters*5)[:256]
    # /dev/urandom is technically not as random as /dev/random, but it doesn't
    # block. 
    r = open('/dev/urandom')
    # make random 'words' and add them to the topics. they'll never
    # realistically be seen again- which is good since we just want them to
    # seed the bias in the topics. 
    for i in xrange(self.num_topics):
        word_length = random.randint(9,20)
        word = r.read(word_length).translate(translate_table)
        self.index(word)
        topic_weights = probability_vector(self.num_topics)
        for k in xrange(self.num_topics):
            self.update_count(word, k, topic_weights[k])
    r.close()

  def __len__(self):
    return len(self._words)

  def num_words(self):
      return sum(1 for x in self._words if self._words[x] >= 1)

  def as_matrix(self):
    ''' Return a matrix of the probabilities of all words over all topics.
        note that because we are using topic_prob(), this is equivalent to he
        expectation of log beta, ie Elogbeta '''
    
    #  XXX TODO we should store this on the fly instead of recomputing it
    #  all the time!

    # create a numpy array here because that's what the e_step in streamLDA
    # expects

    num_words = self.num_words()
    print("%i words" % num_words)
    lambda_matrix = n.zeros((self.num_topics, num_words))

    for word_index, word in enumerate(x for x in self._words \
                                      if self._words[x] >= 1):
        topic_weights = [log(self.topic_prob(k, word)) \
                         for k in xrange(self.num_topics)]

        # topic weights for this word-- a column vector. 
        lambda_matrix[:,word_index] = topic_weights

    self._num_updates += 1
    if self._report:
        self._report.write("%i %i %i %i\n" % (self._num_updates,
                                              len(self._alphabet), \
                                              len(self._words),
                                              sum(x.B() for x in self._topics)))
        
    return lambda_matrix



  def forget(self, proportion):

    num_tables = len(self._words)      
    number_to_forget = proportion * num_tables
    if num_tables > self.max_tables:
      number_to_forget += (num_tables - self.max_tables)
    
    # change this to weight lower probability
    tables_to_forget = random.sample(xrange(num_tables), number_to_forget)
    words = self._words.keys()

    self.initialize_index()

    word_id = -1
    for ii in words:
      word_id += 1

      if not word_id in tables_to_forget:
        self.index(ii)
        continue

      count = self._words[ii]
      for jj in self._topics:
        self._topics[jj][ii] = 0
        del self._topics[jj][ii]

      for jj in ii:
        self._chars[jj] -= count
      self._words[ii] = 0
      del self._words[ii]

  def seq_prob(self, word):
    val = 1.0

    # Weighted monkeys at typewriter
    for ii in word:
      # Add in a threshold to make sure we don't have zero probability sequences
      val *= max(self._alphabet.freq(ii), CHAR_SMOOTHING) 

    # Normalize
    val /= 2**(len(word))
    return val

  def merge(self, otherlambda, rhot):
    ''' fold the word counts in another DirichletWords object into this
        one, weighted by rhot. assumes self.num_topics is the same for both
        objects. '''
    
    all_words = self._words.keys() + otherlambda._words.keys()
    distinct_words = list(set(all_words))

    # combines the probabilities, with otherlambda weighted by rho, and
    # generates a new count by combining the number of words in the old
    # (current) lambda with the number in the new. here we essentially take
    # the same steps as update_count but do so explicitly so we can weight the
    # terms appropriately. 
    total_words = float(self._words.N() + otherlambda._words.N())

    self_scale = (1.0-rhot)*total_words/float(self._words.N())
    other_scale = rhot*total_words/float(otherlambda._words.N())

    for word in distinct_words:
      self.index(word)
        
      # update word counts
      new_val = (self_scale*self._words[word] 
                 + other_scale*otherlambda._words[word])
      if new_val >= 1.0:
          self._words[word] = new_val
      else:
          self._words[word] = 0
          del self._words[word]
      
      # update topic counts
      for topic in xrange(self.num_topics):
        new_val = (self_scale*self._topics[topic][word] 
                   + other_scale*otherlambda._topics[topic][word])
        if new_val >= 1.0:
            self._topics[topic][word] = new_val
        else:
            self._topics[topic][word] = 0
            del self._topics[topic][word]
         
    # update sequence counts
    all_chars = self._alphabet.keys() + otherlambda._alphabet.keys()
    distinct_chars = list(set(all_chars))
 
    for ii in distinct_chars:
      self._alphabet[ii] = (self_scale*self._alphabet[ii] 
                            + other_scale*otherlambda._alphabet[ii])

  def word_prob(self, word):
    return (self._words[word] + self.alpha_word * self.seq_prob(word)) / \
           (self._words.N() + self.alpha_word)

  def topic_prob(self, topic, word):
    return (self._topics[topic][word] + \
            self.alpha_topic * self.word_prob(word)) / \
            (self._topics[topic].N() + self.alpha_topic)

  def update_count(self, word, topic, count):
    # create an index for the word
    self.index(word)
      
    # increment the frequency of the word in the specified topic
    self._topics[topic][word] += count
    # also keep a separate frequency count of the number of times this word has
    # appeared, across all documents. 
    self._words[word] += count
    # finally, keep track of the appearance of each character.
    # note that this does not assume any particular character set nor limit
    # recognized characters. if words contain punctuation, etc. then they will
    # be counted here. 
    for ii in word:
      self._alphabet[ii] += count

  def index(self, word):
      assert not isinstance(word, int)

      if not word in self.word_to_int:
          self.word_to_int[word] = len(self.word_to_int)
          self.int_to_word[self.word_to_int[word]] = word

      return self.word_to_int[word]

  def dictionary(self, word_id):
      assert isinstance(word_id, int)

      return self.int_to_word[word_id]

  def print_probs(self, word):
    print "----------------"
    print word
    for ii in xrange(self.num_topics):
      print ii, self.topic_prob(ii, word)
    print "WORD", self.word_prob(word)
    print "SEQ", self.seq_prob(word)

if __name__ == "__main__":
  test_assignments = [("one",    [0.1, 0.8, 0.1]),
                      ("fish",   [0.0, 0.1, 0.9]),
                      ("two",    [0.1, 0.8, 0.1]),
                      ("fish",   [0.0, 0.2, 0.8]),
                      ("red",    [1.0, 0.0, 0.0]),
                      ("fish",   [0.0, 0.1, 0.9]),
                      ("blue",   [0.25, 0.5, 0.25]),
                      ("fish",   [0.1, 0.5, 0.4])]

  num_topics = len(test_assignments[0][1])
  
  word_prob = DirichletProcessTopics(num_topics)
  for word, phi in test_assignments:
    word_prob.print_probs(word)

    for jj in xrange(num_topics):
      word_prob.update_count(word, jj ,phi[jj])

    word_prob.print_probs(word)

########NEW FILE########
__FILENAME__ = streamlda
# onlineldavb.py: Package of functions for fitting Latent Dirichlet
# Allocation (LDA) with online variational Bayes (VB).
#
# Copyright (C) 2010  Matthew D. Hoffman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, re, time, string
import numpy as n
from scipy.special import gammaln, psi
from dirichlet_words import DirichletWords
import time
from nltk.corpus import stopwords

n.random.seed(100000001)
meanchangethresh = 0.001

class ParameterError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def dirichlet_expectation(alpha):
    """
    alpha is a W by K dimensional matric. 
    For a vector theta ~ Dir(alpha), computes E[log(theta)] given alpha.
    Returns a W x K matrix. 
    """
    if (len(alpha.shape) == 1):
        return(psi(alpha) - psi(n.sum(alpha)))
    return(psi(alpha) - psi(n.sum(alpha, 1))[:, n.newaxis])

class StreamLDA:
    """
    Implements stream-based LDA as an extension to online Variational Bayes for
    LDA, as described in (Hoffman et al. 2010).  """

    def __init__(self, K, alpha, eta, tau0, kappa, sanity_check=False):
        """
        Arguments:
        K: Number of topics
        alpha: Hyperparameter for prior on weight vectors theta
        eta: Hyperparameter for prior on topics beta
        tau0: A (positive) learning parameter that downweights early iterations
        kappa: Learning rate: exponential decay rate---should be between
             (0.5, 1.0] to guarantee asymptotic convergence.

        Note that if you pass the same set of D documents in every time and
        set kappa=0 this class can also be used to do batch VB.
        """

        if not isinstance(K, int):
            raise ParameterError

        # set the model-level parameters
        self._K = K
        self._alpha = alpha
        self._eta = eta
        self._tau0 = tau0 + 1
        self._kappa = kappa
        self.sanity_check = sanity_check
        # number of documents seen *so far*. Updated each time a new batch is
        # submitted. 
        self._D = 0

        # number of batches processed so far. 
        self._batches_to_date = 0

        # cache the wordids and wordcts for the most recent batch so they don't
        # have to be recalculated when computing perplexity
        self.recentbatch = {'wordids': None, 'wordcts': None}

        # Initialize lambda as a DirichletWords object which has a non-zero
        # probability for any character sequence, even those unseen. 
        self._lambda = DirichletWords(self._K, sanity_check=self.sanity_check, initialize=True)
        self._lambda_mat = self._lambda.as_matrix()

        # set the variational distribution q(beta|lambda). 
        self._Elogbeta = self._lambda_mat # num_topics x num_words
        self._expElogbeta = n.exp(self._Elogbeta) # num_topics x num_words
        
    def parse_new_docs(self, new_docs):
        """
        Parse a document into a list of word ids and a list of counts,
        or parse a set of documents into two lists of lists of word ids
        and counts.

        Arguments: 
        new_docs:  List of D documents. Each document must be represented as
                   a single string. (Word order is unimportant.) 

        Returns a pair of lists of lists:

        The first, wordids, says what vocabulary tokens are present in
        each document. wordids[i][j] gives the jth unique token present in
        document i. (Don't count on these tokens being in any particular
        order.)

        The second, wordcts, says how many times each vocabulary token is
        present. wordcts[i][j] is the number of times that the token given
        by wordids[i][j] appears in document i.
        """

        # if a single doc was passed in, convert it to a list. 
        if type(new_docs) == str:
            new_docs = [new_docs,]
            
        D = len(new_docs)
        print 'parsing %d documents...' % D

        wordids = list()
        wordcts = list()
        for d in range(0, D):
            # remove non-alpha characters, normalize case and tokenize on
            # spaces
            new_docs[d] = new_docs[d].lower()
            new_docs[d] = re.sub(r'-', ' ', new_docs[d])
            new_docs[d] = re.sub(r'[^a-z ]', '', new_docs[d])
            new_docs[d] = re.sub(r' +', ' ', new_docs[d])
            words = string.split(new_docs[d])
            doc_counts = {}
            for word in words:
                # skip stopwords 
                if word in stopwords.words('english'):
                    continue
                # index returns the unique index for word. if word has not been
                # seen before, a new index is created. We need to do this check
                # on the existing lambda object so that word indices get
                # preserved across runs. 
                wordindex = self._lambda.index(word)
                doc_counts[wordindex] = doc_counts.get(wordindex, 0) + 1

            # if the document was empty, skip it. 
            if len(doc_counts) == 0:
                continue

            # wordids contains the ids of words seen in this batch, broken down
            # as one list of words per document in the batch. 
            wordids.append(doc_counts.keys())
            # wordcts contains counts of those same words, again per document. 
            wordcts.append(doc_counts.values())
            # Increment the count of total docs seen over all batches. 
            self._D += 1
       
        # cache these values so they don't need to be recomputed. 
        self.recentbatch['wordids'] = wordids
        self.recentbatch['wordcts'] = wordcts

        return((wordids, wordcts))

    def do_e_step(self, docs):
        """
        Given a mini-batch of documents, estimates the parameters
        gamma controlling the variational distribution over the topic
        weights for each document in the mini-batch.

        Arguments:
        docs:  List of D documents. Each document must be represented
               as a string. (Word order is unimportant.) Any
               words not in the vocabulary will be ignored.

        Returns a tuple containing the estimated values of gamma,
        as well as sufficient statistics needed to update lambda.
        """
        # This is to handle the case where someone just passes in a single
        # document, not in a list.
        if type(docs) == str: docs = [docs,]
       
        (wordids, wordcts) = self.parse_new_docs(docs)
        # don't use len(docs) here because if we encounter any empty documents,
        # they'll be skipped in the parse step above, and then batchD will be
        # longer than wordids list. 
        batchD = len(wordids)

        # Initialize the variational distribution q(theta|gamma) for
        # the mini-batch
        gamma = 1*n.random.gamma(100., 1./100., (batchD, self._K)) # batchD x K
        Elogtheta = dirichlet_expectation(gamma) # D x K
        expElogtheta = n.exp(Elogtheta)

        # create a new_lambda to store the stats for this batch
        new_lambda = DirichletWords(self._K, sanity_check=self.sanity_check)

        # Now, for each document d update that document's gamma and phi
        it = 0
        meanchange = 0
        for d in range(0, batchD):
            if d % 10 == 0:
              print 'Updating gamma and phi for document %d in batch' % d
            # These are mostly just shorthand (but might help cache locality)
            ids = wordids[d]
            cts = wordcts[d]
            gammad = gamma[d, :]
            Elogthetad = Elogtheta[d, :] # K x 1
            expElogthetad = expElogtheta[d, :] # k x 1 for this D. 
            # make sure exp/Elogbeta is initialized for all the needed indices. 
            self.Elogbeta_sizecheck(ids)
            expElogbetad = self._expElogbeta[:, ids] # dims(expElogbetad) = k x len(doc_vocab)
            # The optimal phi_{dwk} is proportional to 
            # expElogthetad_k * expElogbetad_w. phinorm is the normalizer.
            phinorm = n.dot(expElogthetad, expElogbetad) + 1e-100

            # Iterate between gamma and phi until convergence
            for it in range(0, 100):
                lastgamma = gammad
                # In these steps, phi is represented implicitly to save memory
                # and time.  Substituting the value of the optimal phi back
                # into the update for gamma gives this update. Cf. Lee&Seung
                # 2001.
                gammad = self._alpha + expElogthetad * \
                    n.dot(cts / phinorm, expElogbetad.T)
                Elogthetad = dirichlet_expectation(gammad)
                expElogthetad = n.exp(Elogthetad)
                phinorm = n.dot(expElogthetad, expElogbetad) + 1e-100
                # If gamma hasn't changed much, we're done.
                meanchange = n.mean(abs(gammad - lastgamma))
                if (meanchange < meanchangethresh):
                    break
            gamma[d, :] = gammad
            # Contribution of document d to the expected sufficient
            # statistics for the M step. Updates the statistics only for words
            # in ids list, with their respective counts in cts (also a list).
            # the multiplying factor from self._expElogbeta
            # lambda_stats is basically phi multiplied by the word counts, ie
            # lambda_stats_wk = n_dw * phi_dwk
            # the sum over documents shown in equation (5) happens as each
            # document is iterated over. 

            # lambda stats is K x len(ids), while the actual word ids can be
            # any integer, so we need a way to map word ids to their
            # lambda_stats (ie we can't just index into the lambda_stats array
            # using the wordid because it will be out of range). so we create
            # lambda_data, which contains a list of 2-tuples of length len(ids). 
            # the first tuple item contains the wordid, and the second contains
            # a numpy array with the statistics for each topic, for that word.

            lambda_stats = n.outer(expElogthetad.T, cts/phinorm) * expElogbetad
            lambda_data = zip(ids, lambda_stats.T)
            for wordid, stats in lambda_data:
              word = self._lambda.dictionary(wordid)
              for topic in xrange(self._K):
                stats_wk = stats[topic]
                new_lambda.update_count(word, topic, stats_wk)

        return((gamma, new_lambda))

    def update_lambda(self, docs):
        """
        The primary function called by the user. First does an E step on the
        mini-batch given in wordids and wordcts, then uses the result of that E
        step to update the variational parameter matrix lambda.

        docs is a list of D documents each represented as a string. (Word order
        is unimportant.) 

        Returns gamma, the parameters to the variational distribution over the
        topic weights theta for the documents analyzed in this update.

        Also returns an estimate of the variational bound for the entire corpus
        for the OLD setting of lambda based on the documents passed in. This
        can be used as a (possibly very noisy) estimate of held-out likelihood.  
        """

        # rhot will be between 0 and 1, and says how much to weight
        # the information we got from this mini-batch.
        rhot = pow(self._tau0 + self._batches_to_date, -self._kappa)
        self._rhot = rhot
        # Do an E step to update gamma, phi | lambda for this
        # mini-batch. This also returns the information about phi that
        # we need to update lambda.
        (gamma, new_lambda) = self.do_e_step(docs)
        # Estimate held-out likelihood for current values of lambda.
        bound = self.approx_bound(gamma)
        # Update lambda based on documents.
        self._lambda.merge(new_lambda, rhot)
        # update the value of lambda_mat so that it also reflect the changes we
        # just made. 
        self._lambda_mat = self._lambda.as_matrix()
        
        # do some housekeeping - is lambda getting too big?
        oversize_by = len(self._lambda._words) - self._lambda.max_tables
        if oversize_by > 0:
            percent_to_forget = oversize_by/len(self._lambda._words)
            self._lambda.forget(percent_to_forget)

        # update expected values of log beta from our lambda object
        self._Elogbeta = self._lambda_mat
#        print 'self lambda mat'
#        print self._lambda_mat
#        print 'self._Elogbeta from lambda_mat after merging'
#        print self._Elogbeta
        self._expElogbeta = n.exp(self._Elogbeta)
#        print 'and self._expElogbeta'
        self._expElogbeta
#        raw_input()
        self._batches_to_date += 1

        return(gamma, bound)

    def Elogbeta_sizecheck(self, ids):
        ''' Elogbeta is initialized with small random values. In an offline LDA
        setting, if a word has never been seen, even after n iterations, its value in
        Elogbeta would remain at this small random value. However, in offline LDA,
        the size of expElogbeta in the words dimension is always <= the number
        of distinct words in some new document. In stream LDA, this is not
        necessarily the case. So we still make sure to use the previous
        iteration's values of Elogbeta, but where a new word appears, we need
        to seed it. That is done here.  '''
        
        # since ids are added sequentially, then the appearance of some id = x
        # in the ids list guarantees that every ID from 0...x-1 also exists.
        # thus, we can take the max value of ids and extend Elogbeta to that
        # size. 
        columns_needed = max(ids)+ 1
        current_columns = self._Elogbeta.shape[1]
        if columns_needed > current_columns:
            self._Elogbeta = n.resize(self._Elogbeta, (self._K, columns_needed))
            # fill the new columns with appropriately small random numbers
            newdata = n.random.random((self._K, columns_needed-current_columns))
            newcols = range(current_columns, columns_needed)
            self._Elogbeta[:,newcols] = newdata
            self._expElogbeta = n.exp(self._Elogbeta)

    def approx_bound(self, gamma):
        """
        Estimates the variational bound over *all documents* using only
        the documents passed in as "docs." gamma is the set of parameters
        to the variational distribution q(theta) corresponding to the
        set of documents passed in.

        The output of this function is going to be noisy, but can be
        useful for assessing convergence.
        """
        wordids = self.recentbatch['wordids']
        wordcts = self.recentbatch['wordcts']
        batchD = len(wordids)

        score = self.batch_bound(gamma)

        # Compensate for the subsampling of the population of documents
        score = score * self._D / batchD

        # The below assume a multinomial topic distribution, and should be
        # updated for the CRP

        # E[log p(beta | eta) - log q (beta | lambda)]
        # score = score + n.sum((self._eta-self._lambda.as_matrix())*self._Elogbeta)
        # score = score + n.sum(gammaln(self._lambda_mat) - gammaln(self._eta))
        # score = score + n.sum(gammaln(self._eta*len(self._lambda)) - 
        #                       gammaln(n.sum(self._lambda_mat, 1)))

        return(score)


    def batch_bound(self, gamma):
        """
        Computes the estimate of held out probability using only the recent
        batch; doesn't try to estimate whole corpus.  If the recent batch isn't
        used to update lambda, then this is the held-out probability.
        """
        wordids = self.recentbatch['wordids']
        wordcts = self.recentbatch['wordcts']
        batchD = len(wordids)

        score = 0
        Elogtheta = dirichlet_expectation(gamma)
        expElogtheta = n.exp(Elogtheta)

        # E[log p(docs | theta, beta)]
        for d in range(0, batchD):
            gammad = gamma[d, :]
            ids = wordids[d]
            cts = n.array(wordcts[d])
            phinorm = n.zeros(len(ids))
            for i in range(0, len(ids)):
                # print d, i, Elogtheta[d, :], self._Elogbeta[:, ids[i]]
                temp = Elogtheta[d, :] + self._Elogbeta[:, ids[i]]
                tmax = max(temp)
                phinorm[i] = n.log(sum(n.exp(temp - tmax))) + tmax
            score += n.sum(cts * phinorm)

        # E[log p(theta | alpha) - log q(theta | gamma)]
        score += n.sum((self._alpha - gamma)*Elogtheta)
        score += n.sum(gammaln(gamma) - gammaln(self._alpha))
        score += sum(gammaln(self._alpha*self._K) - gammaln(n.sum(gamma, 1)))

        return score


########NEW FILE########
__FILENAME__ = stream_corpus
#!/usr/bin/python

# onlinewikipedia.py: Demonstrates the use of online VB for LDA to
# analyze a bunch of random Wikipedia articles.
#
# Copyright (C) 2010  Matthew D. Hoffman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import cPickle, string, numpy, getopt, sys, random, time, re, pprint

import streamlda
from wikirandom import WikipediaCorpus
from twenty_news import TwentyNewsCorpus
from util import print_topics

def main():
    """
    Applies streamLDA to test data, currently either 20 newsgroups or
    wikipedia. The wikipedia option downloads and analyzes a bunch of random
    Wikipedia articles using online VB for LDA. This is nice for breadth of
    examples, but is not precisely repeatable since the articles are random. 20
    newsgroups provides data on which a repeatable run can be performed.
    """

    # The number of documents to analyze each iteration
    batchsize = 10 #64
    # The number of topics
    K = 10

    assert len(sys.argv) == 3, "usage: ./stream_corpus corpus_name num_runs\ncorpus options: 20news, wikipedia"
    if sys.argv[1] == 'wikipedia':
        corpus = WikipediaCorpus()
    elif sys.argv[1] == '20news':
        corpus = TwentyNewsCorpus("20_news", "data/20_news_date", )
    else:
        print 'options not supported. please try again.'
        sys.exit()
    runs = int(sys.argv[2])        

    # Initialize the algorithm with alpha=1/K, eta=1/K, tau_0=1024, kappa=0.7
    slda = streamlda.StreamLDA(K, 1./K, 1./K, 1., 0.7)

    (test_set, test_names) = corpus.docs(batchsize * 5, False)

    for iteration in xrange(0, runs):
        print '-----------------------------------'
        print '         Iteration %d              ' % iteration
        print '-----------------------------------'
        
        # Get some new articles from the selected corpus
        (docset, articlenames) = \
            corpus.docs(batchsize)
        # Give them to online LDA
        (gamma, bound) = slda.update_lambda(docset)
        # Compute an estimate of held-out perplexity
        wordids = slda.recentbatch['wordids']
        wordcts = slda.recentbatch['wordcts']
        #(wordids, wordcts) = slda.parse_new_docs(docset)

        if iteration % 10 == 0:
          gamma_test, new_lambda = slda.do_e_step(test_set)
          new_lambda = None
          lhood = slda.batch_bound(gamma_test)

          print_topics(slda._lambda, 10)
          print "Held-out likelihood", lhood

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/python

''' a set of tests on some stupid-simple data for sanity checking '''

from streamlda import StreamLDA
from util import print_topics
import numpy as n
from matplotlib.pyplot import plot
from pylab import *
import random

# start out with some small docs that have zero vocabulary overlap. also make
# them somewhat intuitive so it's easier to read :)

doc1 = " green grass green grass green grass green grass green grass" 
doc2 = "space exploration space exploration space exploration space exploration" 

num_topics = 2
alpha =1.0/num_topics
eta = 1.0/num_topics
tau0 = 1
kappa =  0.7
slda = StreamLDA(num_topics, alpha, eta, tau0, kappa, sanity_check=False)

num_runs = 200
perplexities = []
perp = open('perplexities.dat','w') 
perp.write("Run, Perplexity\n")
this_run = 0
while this_run < num_runs:
    print "Run #%d..." % this_run
    # batch_docs = [random.choice([doc1,doc2]) for i in xrange(batchsize)]
    batch_docs = [doc1, doc2, doc1, doc2, doc2, doc1, doc1, doc1, doc2, doc1]
    (gamma, bound) = slda.update_lambda(batch_docs)
    (wordids, wordcts) = slda.parse_new_docs(batch_docs)
    perwordbound = bound * len(batch_docs) / (slda._D * sum(map(sum, wordcts)))
    perplexity = n.exp(-perwordbound)
    perplexities.append(perplexity)

#    if (this_run % 10 == 0):                                                         
#        n.savetxt('lambda-%d.dat' % this_run, slda._lambda.as_matrix())
#        n.savetxt('gamma-%d.dat' % this_run, gamma)

    print '%d:  rho_t = %f,  held-out perplexity estimate = %f' % \
        (this_run, slda._rhot, perplexity)
    perp.write("%d,%f\n" % (this_run, perplexity))
    perp.flush()
    this_run += 1
perp.close()
print_topics(slda._lambda, 50)


# set up a plot and show the results
xlabel('Run')
ylabel('Perplexity')
title('Perplexity Values - Sanity Check')
plot(range(num_runs), perplexities)
show()



########NEW FILE########
__FILENAME__ = twenty_news
# onlineldavb.py: Package of functions for fitting Latent Dirichlet
# Allocation (LDA) with online variational Bayes (VB).
#
# Copyright (C) 2011 Jordan Boyd-Graber
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from glob import glob
from random import sample

from corpora import Corpus

class TwentyNewsCorpus(Corpus):
  def __init__(self, corpus_name, path, deterministic=False):
    self._path = path
    self._deterministic = deterministic

    self._filenames = {}
    print "Searching %s/train/*/*" % self._path
    self._filenames[True] = glob("%s/train/*/*" % self._path)
    self._filenames[False] = glob("%s/test/*/*" % self._path)

    Corpus.__init__(self, corpus_name)

  def docs(self, num_docs, train=True):
    candidates = self._filenames[train]
    if num_docs > 0 and num_docs < len(candidates):
      if self._deterministic:
        selection = candidates[:num_docs]
      else:
        selection = sample(candidates, num_docs)
    else:
      selection = candidates

    return [open(x).read() for x in selection], selection

if __name__ == "__main__":
   c = TwentyNewsCorpus("20news", "data/20_news_date")

   (articles, articlenames) = c.docs(20)
   for ii in range(0, len(articles)):
     print articlenames[ii]

########NEW FILE########
__FILENAME__ = util
def print_topics(lambda_, topn):
    ''' prints the top n most frequent words from each topic in lambda '''
    topics = lambda_.num_topics
    for k in xrange(topics):
        this_topic = lambda_._topics[k]
        if topn < len(this_topic):
            printlines = topn
        else:
            printlines = len(this_topic)
    
        print 'Topic %d' % k
        print '---------------------------'
        for word in this_topic.keys(): # this_topic.items() is pre-sorted
            if printlines > 0:
                print '%20s  \t---\t  %.4f' % (word, this_topic.freq(word))
                printlines -= 1
            else:
                break
        print
        

########NEW FILE########
__FILENAME__ = wikirandom
# wikirandom.py: Functions for downloading random articles from Wikipedia
#
# Copyright (C) 2010  Matthew D. Hoffman
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, urllib2, re, string, time, threading
from corpora import Corpus

def get_random_wikipedia_article():
    """
    Downloads a randomly selected Wikipedia article (via
    http://en.wikipedia.org/wiki/Special:Random) and strips out (most
    of) the formatting, links, etc. 

    This function is a bit simpler and less robust than the code that
    was used for the experiments in "Online VB for LDA."
    """
    failed = True
    while failed:
        articletitle = None
        failed = False
        try:
            req = urllib2.Request('http://en.wikipedia.org/wiki/Special:Random',
                                  None, { 'User-Agent' : 'x'})
            f = urllib2.urlopen(req)
            while not articletitle:
                line = f.readline()
                result = re.search(r'title="Edit this page" href="/w/index.php\?title=(.*)\&amp;action=edit" /\>', line)
                if (result):
                    articletitle = result.group(1)
                    break
                elif (len(line) < 1):
                    sys.exit(1)

            req = urllib2.Request('http://en.wikipedia.org/w/index.php?title=Special:Export/%s&action=submit' \
                                      % (articletitle),
                                  None, { 'User-Agent' : 'x'})
            f = urllib2.urlopen(req)
            all = f.read()
        except (urllib2.HTTPError, urllib2.URLError):
            print 'oops. there was a failure downloading %s. retrying...' \
                % articletitle
            failed = True
            continue
        print 'downloaded %s. parsing...' % articletitle

        try:
            all = re.search(r'<text.*?>(.*)</text', all, flags=re.DOTALL).group(1)
            all = re.sub(r'\n', ' ', all)
            all = re.sub(r'\{\{.*?\}\}', r'', all)
            all = re.sub(r'\[\[Category:.*', '', all)
            all = re.sub(r'==\s*[Ss]ource\s*==.*', '', all)
            all = re.sub(r'==\s*[Rr]eferences\s*==.*', '', all)
            all = re.sub(r'==\s*[Ee]xternal [Ll]inks\s*==.*', '', all)
            all = re.sub(r'==\s*[Ee]xternal [Ll]inks and [Rr]eferences==\s*', '', all)
            all = re.sub(r'==\s*[Ss]ee [Aa]lso\s*==.*', '', all)
            all = re.sub(r'http://[^\s]*', '', all)
            all = re.sub(r'\[\[Image:.*?\]\]', '', all)
            all = re.sub(r'Image:.*?\|', '', all)
            all = re.sub(r'\[\[.*?\|*([^\|]*?)\]\]', r'\1', all)
            all = re.sub(r'\&lt;.*?&gt;', '', all)
        except:
            # Something went wrong, try again. (This is bad coding practice.)
            print 'oops. there was a failure parsing %s. retrying...' \
                % articletitle
            failed = True
            continue

    return(all, articletitle)

class WikiThread(threading.Thread):
    articles = list()
    articlenames = list()
    lock = threading.Lock()

    def run(self):
        (article, articlename) = get_random_wikipedia_article()
        WikiThread.lock.acquire()
        WikiThread.articles.append(article)
        WikiThread.articlenames.append(articlename)
        WikiThread.lock.release()

def get_random_wikipedia_articles(n):
    """
    Downloads n articles in parallel from Wikipedia and returns lists
    of their names and contents. Much faster than calling
    get_random_wikipedia_article() serially.
    """
    maxthreads = 8
    WikiThread.articles = list()
    WikiThread.articlenames = list()
    wtlist = list()
    for i in range(0, n, maxthreads):
        print 'downloaded %d/%d articles...' % (i, n)
        for j in range(i, min(i+maxthreads, n)):
            wtlist.append(WikiThread())
            wtlist[len(wtlist)-1].start()
        for j in range(i, min(i+maxthreads, n)):
            wtlist[j].join()
    return (WikiThread.articles, WikiThread.articlenames)

class WikipediaCorpus(Corpus):
  def __init__(self, name = "wiki"):
    Corpus.__init__(self, name)

  def docs(self, num_docs, train=True):
    return get_random_wikipedia_articles(num_docs)

if __name__ == '__main__':

    c = WikipediaCorpus()

    t0 = time.time()

    (articles, articlenames) = c.docs(1)
    for i in range(0, len(articles)):
        print articlenames[i]

    t1 = time.time()
    print 'took %f' % (t1 - t0)

########NEW FILE########
