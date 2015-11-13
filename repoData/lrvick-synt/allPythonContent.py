__FILENAME__ = accuracy
# -*- coding: utf-8 -*-
import nltk.classify.util
from synt.utils.db import get_samples, RedisManager
from synt.utils.text import normalize_text
from synt.utils.extractors import get_extractor
from synt.guesser import Guesser

def test_accuracy(db_name='', test_samples=0, neutral_range=0, offset=0):
    """
    Returns two accuracies and classifier:
    NLTK accuracy is the internal accuracy of the classifier
    Manual Accuracy is the accuracy when compared to pre-flagged/known samples and label.

    Keyword Arguments:
    db_name (str) -- Samples database to use, by default this is the same as your trained database
                     with an offset to ensure unseen data. Should be a string
                     database name located in ~/.synt.

    test_samples (int) -- Amount of samples to use, by default this will be 25% of the training set amount.

    neutral_range (float) -- Will be used to drop "neutrals" to see how real-world accuracy will look.
                             For example in the case where neutral range is 0.2 if the sentiment
                             guessed is not greater than 0.2 or less than -0.2 it is not considered.
                             Leaving this set to 0 will not cause the special case drops and will by default
                             categorize text as either positive or negative. This may be undesired as the classifier
                             will treat 0.0001 as positive even though it is not a strong indication.

    offset (int) -- By default the offset is decided from the end of the the trained amount, i.e
                    if you've trained on 1000 and you have 250 testing samples the samples retrieved
                    will be from 1000-1250, you can override this offset if you wish to use a different
                    subset.
    """

    m = RedisManager()
    trained_classifier = m.r.get('trained_classifier') #retrieve the trained classifier

    if not trained_classifier:
        print("Accuracy needs a classifier, have you trained?")
        return

    classifier = m.pickle_load(trained_classifier)

    #we want to make sure we are testing on a new set of samples therefore
    #we use the trained_to as our offset and proceed to use the samples
    #thereafter, unless an offset is otherwise specified
    trained_to = int(m.r.get('trained_to'))

    if not offset:
        offset = trained_to

    if test_samples <= 0: #if no testing samples provided use 25% of our training number
        test_samples = int(trained_to * .25)

    if not db_name:
        db_name = m.r.get('trained_db') #use the trained samples database

    test_samples = get_samples(db_name, test_samples, offset=offset)

    testfeats = []
    trained_ext = m.r.get('trained_extractor')

    feat_ex = get_extractor(trained_ext)()

    #normalization and extraction
    for text, label in test_samples:
        tokens = normalize_text(text)
        bag_of_words = feat_ex.extract(tokens)

        if bag_of_words:
            testfeats.append((bag_of_words, label))

    nltk_accuracy = nltk.classify.util.accuracy(classifier, gold=testfeats) * 100 # percentify

    total_guessed = 0
    total_correct = 0
    total_incorrect = 0

    g = Guesser(extractor_type=trained_ext)

    #compare the guessed sentiments with our samples database to determine manual accuracy
    for text, label in test_samples:
        guessed = g.guess(text)
        if abs(guessed) < neutral_range:
            continue

        if (guessed > 0) == label.startswith('pos'):
            total_correct += 1
        else:
            #print text, label, guessed
            total_incorrect += 1

        total_guessed += 1

    assert total_guessed, "There were no guesses, make sure you've trained on the same database you're testing."

    manual_accuracy =  total_correct * 100.0 / total_guessed

    #TODO: precision and recall

    return (nltk_accuracy, manual_accuracy, classifier)

if __name__ == "__main__":
    #example accuracy
    import time

    neutral_range = 0.2

    print("Testing accuracy with neutral range: {}.".format(neutral_range))
    start = time.time()

    n_accur, m_accur, c = test_accuracy(neutral_range=neutral_range)

    c.show_most_informative_features(30)

    print("NLTK Accuracy: {}".format(n_accur))
    print("Manual Accuracy: {}".format(m_accur))

    print("Successfully tested in {} seconds.".format(time.time() - start))

########NEW FILE########
__FILENAME__ = collector
# -*- coding: utf-8 -*-
import time, datetime
import os
import bz2
import urllib2
from sqlite3 import IntegrityError
from cStringIO import StringIO
from synt.utils.db import db_init
from synt import config

def collect(db_name='', commit_every=1000, max_collect=400000, query_file=''):
    """
    Will continuously populate the sample database if it exists
    else it will create a new one.

    Keyword Arguments:
    db_name (str) -- Custom name for database.
    commit_every (int) -- Commit to sqlite after commit_every executes.
    max_collect (int) -- Will stop collecting at this number.
    query_file (str) -- If query file is provided should be absolute path to text file.
    """

    #collect requires kral
    try:
        from kral import stream
    except ImportError:
        raise ImportError("Requires the kral package in order to collect.")

    if not db_name:
        d = datetime.datetime.now()
        #if no dbname is provided we'll store a timestamped db name
        db_name = "samples-%s-%s-%s.db" % (d.year, d.month, d.day)

    db = db_init(db=db_name)
    cursor = db.cursor()

    queries = {}

    if query_file:
        if not os.path.exists(query_file):
            return "Query file path does not exist."

        f = open(query_file)
        words = [line.strip() for line in f.readlines()]
        label = words[0]
        for w in words:
            queries[w] = label

    else:
        queries[':)'] =  'positive'
        queries[':('] =  'negative'

    #collect on twitter with kral
    g = stream(query_list=queries.keys(), service_list="twitter")

    c = 0
    for item in g:

        text = unicode(item['text'])

        sentiment = queries.get(item['query'], None)

        if sentiment:
            try:
                cursor.execute('INSERT INTO item VALUES (NULL,?,?)', [text, sentiment])
                c += 1
                if c % commit_every == 0:
                    db.commit()
                    print("Commited {}".format(commit_every))
                if c == max_collect:
                    break
            except IntegrityError: #skip duplicates
                continue

    db.close()

def import_progress():
    global logger, output_count, prcount
    try:
        prcount
        output_count
    except:
        prcount=0
        output_count = 500000
    prcount += 20
    output_count += 20
    if output_count >= 500000:
        output_count = 0
        percent = round((float(prcount) / 40423300 )*100, 2)
        print("Processed %s of 40423300 records (%0.2f%%)" % (prcount,percent))
    return 0

def fetch(db_name='samples.db'):
    """
    Pre-populates training database from public archive of ~2mil tweets.
    Stores training database as db_name in ~/.synt/

    Keyword Arguments:
    db_name (str) -- Custom name for database.

    """

    response = urllib2.urlopen('https://github.com/downloads/Tawlk/synt/sample_data.bz2')

    total_bytes = int(response.info().getheader('Content-Length').strip())
    saved_bytes = 0
    start_time = time.time()
    last_seconds = 0
    last_seconds_start = 0
    data_buffer = StringIO()

    decompressor = bz2.BZ2Decompressor()

    fp = os.path.join(os.path.expanduser(config.SYNT_PATH), db_name)

    if os.path.exists(fp):
        os.remove(fp)

    db = db_init(db=db_name, create=False)
    db.set_progress_handler(import_progress,20)

    while True:
        seconds = (time.time() - start_time)
        chunk = response.read(8192)

        if not chunk:
            break

        saved_bytes += len(chunk)
        data_buffer.write(decompressor.decompress(chunk))

        if seconds > 1:
            percent = round((float(saved_bytes) / total_bytes)*100, 2)
            speed = round((float(total_bytes / seconds ) / 1024),2)
            speed_type = 'Kb/s'

            if speed > 1000:
                speed = round((float(total_bytes / seconds ) / 1048576),2)
                speed_type = 'Mb/s'

            if last_seconds >= 0.5:
                last_seconds = 0
                last_seconds_start = time.time()
                print("Downloaded %d of %d Mb, %s%s (%0.2f%%)\r" % (saved_bytes/1048576, total_bytes/1048576, speed, speed_type, percent))
            else:
                last_seconds = (time.time() - last_seconds_start)

        if saved_bytes == total_bytes:
            print("Downloaded %d of %d Mb, %s%s (100%%)\r" % (saved_bytes/1048576, total_bytes/1048576, speed, speed_type))

            try:
                db.executescript(data_buffer.getvalue())
            except Exception, e:
                print("Sqlite3 import failed with: %s" % e)
                break


if __name__ == '__main__':
    max_collect = 2000000
    commit_every = 500
    qf = 'negwords.txt'

    collect(commit_every = commit_every, max_collect = max_collect, queries_file=qf)


########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
#Config for the synt project

import os
import nltk

PROJECT_PATH = os.path.realpath(os.path.dirname(__file__))
#Where collected databases and user config are stored by default
SYNT_PATH = os.path.expanduser("~/.synt")
USER_CONFIG_PATH = os.path.join(SYNT_PATH, 'config.py')

#Emoticons may serve as useful indicatiors in classifying sentiment.
#These are the set of default emoticons to use, you may use your own or
#disregard emoticons entirely they are optional.
EMOTICONS = [
    ':-L', ':L', '<3', '8)', '8-)', '8-}', '8]', '8-]', '8-|', '8(', '8-(',
    '8-[', '8-{', '-.-', 'xx', '</3', ':-{', ': )', ': (', ';]', ':{', '={',
    ':-}', ':}', '=}', ':)', ';)', ':/', '=/', ';/', 'x(', 'x)', ':D', 'T_T',
    'O.o', 'o.o', 'o_O', 'o.-', 'O.-', '-.o', '-.O', 'X_X', 'x_x', 'XD', 'DX',
    ':-$', ':|', '-_-', 'D:', ':-)', '^_^', '=)', '=]', '=|', '=[', '=(', ':(',
    ':-(', ':, (', ':\'(', ':-]', ':-[', ':]', ':[', '>.>', '<.<'
]


#Default classifiers supported
CLASSIFIERS = {
    'naivebayes'   : nltk.NaiveBayesClassifier,
}

#If the user config is in place, use settings from there instead.
if os.path.exists(USER_CONFIG_PATH):
    execfile(USER_CONFIG_PATH)

########NEW FILE########
__FILENAME__ = guesser
# -*- coding: utf-8 -*-
from synt.utils.db import RedisManager
from synt.utils.extractors import get_extractor
from synt.utils.text import normalize_text

class Guesser(object):

    def __init__(self, classifier_type='naivebayes', extractor_type='stopwords'):
        self.classifier_type = classifier_type
        self.extractor = get_extractor(extractor_type)()
        self.normalizer = normalize_text

    def load_classifier(self):
        """
        Gets the classifier when it is first required.
        """
        if not hasattr(self, 'classifier'):
            manager = RedisManager()
            self.classifier = manager.pickle_load(self.classifier_type)

    def guess(self, text):
        """
        Returns the sentiment score between -1 and 1.

        Arguments:
        text (str) -- Text to classify.

        """
        self.load_classifier()

        assert self.classifier, "Guess needs a classifier!"

        tokens = self.normalizer(text)

        bag_of_words = self.extractor.extract(tokens)

        score = 0.0

        if bag_of_words:

            prob = self.classifier.prob_classify(bag_of_words)

            #return a -1 .. 1 score
            score = prob.prob('positive') - prob.prob('negative')

            #if score doesn't fall within -1 and 1 return 0.0
            if not (-1 <= score <= 1):
                pass

        return score

if __name__ == '__main__':
    #example usage of guess

    g = Guesser()

    print("Enter something to calculate the synt of it!")
    print("Just press enter to quit.")

    while True:
        text = raw_input("synt> ")
        if not text:
            break
        print('Guessed: {}'.format(g.guess(text)))

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
import unittest
from synt.trainer import train
from synt.guesser import Guesser
from synt import config

class TrainerTestCase(unittest.TestCase):

    def test_train_success(self):
        train('samples.db', 1000, best_features=None, purge=True, redis_db=config.REDIS_TEST_DB)

    def test_train_bestwords_success(self):
        train('samples.db', 1000, best_features=250, purge=True, redis_db=config.REDIS_TEST_DB)

    def test_train_bad_db(self):
        self.assertRaises(ValueError, train, 'xyz123.db', redis_db=config.REDIS_TEST_DB, purge=True)

    def test_train_unsupported_classifier(self):
        self.assertRaises(ValueError, train, 'samples.db', classifier_type='xyz', redis_db=config.REDIS_TEST_DB)

class GuesserTestCase(unittest.TestCase):

    def setUp(self):
        train('samples.db', 1000, classifier_type='naivebayes', purge=True, redis_db=config.REDIS_TEST_DB)
        self.g = Guesser().guess

    def test_guess_with_text(self):
        score = self.g('some random text')
        self.assertTrue(-1.0 <= score <= 1.0)

    def test_guess_no_text(self):
        score = self.g('')
        self.assertEqual(score, 0.0)

    def test_guess_unicode(self):
        score = self.g("FOE JAPANが粘り強く主張していた避難の権利")
        self.assertTrue(-1.0 <= score <= 1.0)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = trainer
# -*- coding: utf-8 -*-
from nltk import FreqDist, ELEProbDist
from utils.db import RedisManager, get_samples, db_exists
from collections import defaultdict
from synt.utils.extractors import get_extractor
from synt import config

def train(db_name, samples=200000, classifier_type='naivebayes', extractor_type='words',
    best_features=10000, processes=8, purge=False):
    """
    Train with samples from sqlite database and stores the resulting classifier in Redis.

    Arguments:
    db_name (str) -- Name of the training database to use stored in ~/.synt

    Keyword arguments:
    samples (int) -- Amount of samples to train on.
    classifier_type (str) -- Type of classifier to use. Available classifiers are 'naivebayes'.
    extractor_type (str) -- Type of extractor to use. Available extractors are 'words', 'stopwords', 'bestwords'.
    best_features (int) -- Amount of highly informative features to store.
    processes (int) -- The amount of processes to be used for counting features in parallel.
    purge (bool) -- If true will flush the redis database.
    """
    m = RedisManager(purge=purge)

    extractor = get_extractor(extractor_type)

    if not db_exists(db_name):
        raise ValueError("Database '%s' does not exist." % db_name)

    if classifier_type in m.r.keys():
        print("Classifier exists in Redis. Purge to re-train.")
        return

    classifier = config.CLASSIFIERS.get(classifier_type)
    if not classifier: #classifier not supported
        raise ValueError("Classifier '%s' not supported." % classifier_type)

    #retrieve training samples from database
    train_samples = get_samples(db_name, samples)

    m.store_feature_counts(train_samples, processes=processes)
    m.store_feature_scores()

    if best_features and best_features > 1:
        m.store_best_features(best_features)

    label_freqdist = FreqDist()
    feature_freqdist = defaultdict(FreqDist)

    #retreieve the actual samples processed for label
    neg_processed, pos_processed = m.r.get('negative_processed'), m.r.get('positive_processed')
    label_freqdist.inc('negative', int(neg_processed))
    label_freqdist.inc('positive', int(pos_processed))

    labeled_feature_freqs = m.pickle_load('labeled_feature_freqs')
    labels = labeled_feature_freqs.keys()

    #feature extraction
    feat_ex = extractor()
    extracted_set = set([feat_ex.extract(labeled_feature_freqs[label].keys(), as_list=True) for label in labels][0])

    #increment the amount of times a given feature for label occured and fill in the missing occurences with Falses
    for label in labels:
        samples = label_freqdist[label]
        for fname in extracted_set:
            trues = labeled_feature_freqs[label].get(fname, 0)
            falses = samples - trues
            feature_freqdist[label, fname].inc(True, trues)
            feature_freqdist[label, fname].inc(False, falses)

    #create the P(label) distribution
    estimator = ELEProbDist
    label_probdist = estimator(label_freqdist)

    #create the P(fval|label, fname) distribution
    feature_probdist = {}
    for ((label, fname), freqdist) in feature_freqdist.items():
        probdist = estimator(freqdist, bins=2)
        feature_probdist[label,fname] = probdist

    #TODO: naivebayes supports this prototype, future classifiers will most likely not
    trained_classifier = classifier(label_probdist, feature_probdist)

    m.pickle_store(classifier_type, trained_classifier)
    m.r.set('trained_to', samples)
    m.r.set('trained_db', db_name)
    m.r.set('trained_classifier', classifier_type)
    m.r.set('trained_extractor', extractor_type)

if __name__ == "__main__":
    #example train
    import time

    db_name       = 'samples.db'
    samples       = 10000
    best_features = 5000
    processes     = 8
    purge         = True
    extractor     = 'words'

    print("Beginning train on {} samples using '{}' db..".format(samples, db_name))
    start = time.time()
    train(
            db_name       = db_name,
            samples       = samples,
            best_features = best_features,
            extractor_type= extractor,
            processes     = processes,
            purge         = purge,
    )
    print("Successfully trained in {} seconds.".format(time.time() - start))

########NEW FILE########
__FILENAME__ = user_config
#User config for Synt

#The database that will house the classifer data.
REDIS_DB = 5

#The database used for tests.
REDIS_TEST_DB = 10

REDIS_HOST = 'localhost'

REDIS_PASSWORD = None

########NEW FILE########
__FILENAME__ = db
# -*- coding: utf-8 -*-
"""Tools to interact with databases."""

import os
import sqlite3
import redis
import cPickle as pickle
from nltk.metrics import BigramAssocMeasures
from synt.utils.text import normalize_text
from synt.utils.processing import batch_job
from synt import config

def db_exists(name):
    """
    Returns true if the database exists in our path defined by SYNT_PATH.

    Arguments:
    name (str) -- Database name.

    """
    path = os.path.join(config.SYNT_PATH, name)
    return True if os.path.exists(path) else False

def db_init(db, create=True):
    """
    Initializes the sqlite3 database.

    Keyword Arguments:
    db (str) -- Name of the database to use.
    create (bool) -- If creating the database for the first time.

    """

    if not os.path.exists(config.SYNT_PATH):
        os.makedirs(config.SYNT_PATH)

    fp = os.path.join(config.SYNT_PATH, db)

    if not db_exists(db):
        conn = sqlite3.connect(fp)
        cursor = conn.cursor()
        if create:
            cursor.execute('''CREATE TABLE item (id integer primary key, text text unique, sentiment text)''')
    else:
        conn = sqlite3.connect(fp)
    return conn


def redis_feature_consumer(samples, **kwargs):
    """
    Stores feature and counts to redis via a pipeline.
    """

    rm = RedisManager()
    pipeline = rm.r.pipeline()

    neg_processed, pos_processed = 0, 0

    for text, label in samples:

        count_label = label + '_feature_counts'

        tokens = normalize_text(text)

        if tokens:
            if label.startswith('pos'):
                pos_processed += 1
            else:
                neg_processed += 1

            for word in set(tokens): #make sure we only add word once
                pipeline.zincrby(count_label, word)

    pipeline.incr('negative_processed', neg_processed)
    pipeline.incr('positive_processed', pos_processed)

    pipeline.execute()

class RedisManager(object):
    def __init__(self, purge=False):
        self.db = config.REDIS_DB
        self.host = config.REDIS_HOST
        self.password = config.REDIS_PASSWORD
        self.r = redis.Redis(db=self.db, host=self.host, password=self.password)
        if purge is True:
            self.r.flushdb()

    def store_feature_counts(self, samples, chunksize=10000, processes=None):
        """
        Stores feature:count histograms for samples in Redis with the ability to increment.

        Arguments:
        samples (list) -- List of samples in the format (text, label)

        Keyword Arguments:
        chunksize (int) -- Amount of samples to process at a time.
        processes (int) -- Amount of processors to use with multiprocessing.

        """

        if 'positive_feature_counts' and 'negative_feature_counts' in self.r.keys():
            return

        #do this with multiprocessing
        batch_job(samples, redis_feature_consumer, chunksize=chunksize, processes=processes)


    def store_feature_scores(self):
        """
        Build scores based on chi-sq and store from stored features then save their scores to Redis.
        """

        pos_words = self.r.zrange('positive_feature_counts', 0, -1, withscores=True, desc=True)
        neg_words = self.r.zrange('negative_feature_counts', 0, -1, withscores=True, desc=True)

        assert pos_words and neg_words, 'Requires feature counts to be stored in redis.'

        feature_freqs = {}
        labeled_feature_freqs = {'positive': {}, 'negative': {}}
        labels = labeled_feature_freqs.keys()

        #build a condtional freqdist with the feature counts per label
        for feature,freq in pos_words:
            feature_freqs[feature] = freq
            labeled_feature_freqs['positive'].update({feature : freq})

        for feature,freq in neg_words:
            feature_freqs[feature] = freq
            labeled_feature_freqs['negative'].update({feature : freq})

        scores = {}

        pos_feature_count = len(labeled_feature_freqs['positive'])
        neg_feature_count = len(labeled_feature_freqs['negative'])
        total_feature_count = pos_feature_count + neg_feature_count

        for label in labels:
            for feature,freq in feature_freqs.items():
                pos_score = BigramAssocMeasures.chi_sq(
                        labeled_feature_freqs['positive'].get(feature, 0),
                        (freq, pos_feature_count),
                        total_feature_count
                )
                neg_score = BigramAssocMeasures.chi_sq(
                        labeled_feature_freqs['negative'].get(feature, 0),
                        (freq, neg_feature_count),
                        total_feature_count
                )

                scores[feature] = pos_score + neg_score

        self.pickle_store('feature_freqs', feature_freqs)
        self.pickle_store('labeled_feature_freqs', labeled_feature_freqs)
        self.pickle_store('scores', scores)

    def store_best_features(self, n=10000):
        """
        Stores the best features in Redis.

        Keyword Arguments:
        n (int) -- Amount of features to store as best features.

        """
        if not n: return

        feature_scores = self.pickle_load('scores')

        assert feature_scores, "Feature scores need to exist."

        best = sorted(feature_scores.items(), key=lambda (w,s): s, reverse=True)[:n]

        self.pickle_store('best_features',  best)

    def get_best_features(self):
        """
        Return stored best features.
        """
        best_features = self.pickle_load('best_features')

        if best_features:
            return set([feature for feature,score in best_features])

    def pickle_store(self, name, data):
        dump = pickle.dumps(data, protocol=1) #highest_protocol breaks with NLTKs FreqDist
        self.r.set(name, dump)

    def pickle_load(self, name):
        return pickle.loads(self.r.get(name))

def get_sample_limit(db):
    """
    Returns the limit of samples so that both positive and negative samples
    will remain balanced.

    Keyword Arguments:
    db (str) -- Name of the database to use.

    """

    #this is an expensive operation in case of a large database
    #therefore we store the limit in redis and use that when we can
    m = RedisManager()
    if 'limit' in m.r.keys():
        return int(m.r.get('limit'))

    db = db_init(db=db)
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM item where sentiment = 'positive'")
    pos_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM item where sentiment = 'negative'")
    neg_count = cursor.fetchone()[0]
    if neg_count > pos_count:
        limit = pos_count
    else:
        limit = neg_count

    m.r.set('limit', limit)

    return limit

def get_samples(db, limit, offset=0):
    """
    Returns a combined list of negative and positive samples in a (text, label) format.

    Arguments:
    db (str) -- Name of the databse to use.
    limit (int) -- Amount of samples to retrieve.

    Keyword Arguments:
    offset (int) -- Where to start getting samples from.

    """
    conn = db_init(db=db)
    cursor = conn.cursor()

    sql =  "SELECT text, sentiment FROM item WHERE sentiment = ? LIMIT ? OFFSET ?"

    if limit < 2: limit = 2

    if limit > get_sample_limit(db):
        limit = get_sample_limit(db)

    if limit % 2 != 0:
        limit -= 1 #we want an even number

    limit = limit / 2
    offset = offset / 2

    cursor.execute(sql, ["negative", limit, offset])
    neg_samples = cursor.fetchall()

    cursor.execute(sql, ["positive", limit, offset])
    pos_samples = cursor.fetchall()

    return pos_samples + neg_samples

########NEW FILE########
__FILENAME__ = extractors
# -*- coding: utf-8 -*-
"""Tools for extracting features and text processing."""

from nltk.corpus import stopwords

try:
    stopwords.words
except LookupError:
    import nltk
    print("Downloading needed nltk data...")
    nltk.download('all')

from synt.utils.db import RedisManager

def get_extractor(type):
    """
    Return the extractor for type.

    Arguments:
    type (str) -- A name/type of extractor.

    """

    extractors = {
            'words'     : WordExtractor,
            'stopwords' : StopWordExtractor,
            'bestwords' : BestWordExtractor,
            }

    if type not in extractors:
        raise KeyError("Extractor of type %s doesn't exist." % type)
    return extractors[type]

class WordExtractor(object):

    def extract(self, words, as_list=False):
        """
        Returns a base bag of words.

        Arguments:
        words (list) -- A list of words.

        Keyword Arguments:
        as_list (bool) -- By default we return a dict, unless you want to leave it as a list.

        """

        if not words: return

        if as_list:
            return [word for word in words]

        return dict([(word, True) for word in words])

class StopWordExtractor(WordExtractor):

    def __init__(self, stop_words=None):
        if stop_words:
            self.stop_words = stop_words
        else:
            self.stop_words = set(stopwords.words('english'))

    def extract(self, words, as_list=False):
        """
        Returns a bag of words for words that are not in stop words.

        Arguments:
        words (list) -- A list of words.

        Keyword Arguments:
        as_list (bool) -- By default we return a dict, unless you want to leave it as a list.

        """

        assert self.stop_words, "This extractor relies on a set of stop words."

        if not words: return

        if as_list:
            return [word for word in words if word not in self.stop_words]

        return dict([(word,True) for word in words if word not in self.stop_words])

class BestWordExtractor(WordExtractor):

    def __init__(self, best_words=None):
        if best_words:
            self.best_words = best_words
        else:
            self.best_words = RedisManager().get_best_features()

    def extract(self, words, as_list=False):
        """
        Returns a bag of words for words that are in best words.

        Arguments:
        words (list) -- A list of words.

        Keyword Arguments:
        as_list (bool) -- By default we return a dict, unless you want to leave it as a list.

        """

        assert self.best_words, "This extractor relies on best words."

        if not words: return

        if as_list:
            return [word for word in words if word in self.best_words]

        return dict([(word, True) for word in words if word in self.best_words])

########NEW FILE########
__FILENAME__ = processing
# -*- coding: utf-8 -*-
"""Tools to deal with multi-processing."""

import multiprocessing

def batch_job(producer, consumer, chunksize=10000, processes=None, consumer_args={}):
    """
    Call consumer on everything that is produced from producer, using a pool.

    Arguments:
    producer (func/list) -- Produces the events that are fed to the consumer.
    consumer (func) -- Function called with values recieved from the producer.

    Keyword Arguments:
    chunksize (int) -- How many values to request from the producer.
    processes (int) -- How many processes should be created to handle jobs.
    consumer_args (dict) -- Arguments to pass along to the consumer.

    """
    p = producer

    if type(producer) in [list,tuple]:
        #replace the list or tuple with a dummy producer function
        def tmp(offset, length):
            """
            A wraper for lists to allow them to be used as producers.
            """
            return producer[offset:offset+length]

        p = tmp

    if not processes:
        processes = multiprocessing.cpu_count()

    offset = 0

    finished = False

    pool = multiprocessing.Pool(processes)

    while not finished:

        for i in range(1, processes + 1):

            samples = p(offset, chunksize)

            if not samples:
                finished = True
                break

            pool.apply_async(consumer, [samples], consumer_args)


            offset += len(samples)

    pool.close()
    pool.join() #wait for workers to finish

if __name__=="__main__":
    #example usage

    def producer(offset, length):
        if offset >= 50:
            return []
        return range(offset, offset + length)

    #or producer can be a list
    #producer = range(100)

    queue = multiprocessing.Queue()
    def consumer(data):
        global queue

        for i in data:
            queue.put(i)

    batch_job(producer, consumer, 10)

    out = []

    while not queue.empty():
        out.append(queue.get())
    print out

########NEW FILE########
__FILENAME__ = text
# -*- coding: utf-8 -*-
"""Tools to deal with text processing."""
import re
import string
from nltk.tokenize import WhitespaceTokenizer
from synt import config

#ordinal -> none character mapping
PUNC_MAP = dict([(ord(x),None) for x in string.punctuation])

def normalize_text(text):
    """
    Formats text to strip unneccesary:words, punctuation and whitespace. Returns a tokenized list.

    Arguments:
    text (str) -- Text to process.

    >>> text = "ommmmmmg how'r u!? visi t  <html> <a href='http://google.com'> my</a> site @ http://www.coolstuff.com haha"
    >>> normalize_text(text)
    [u'ommg', u'howr', u'visi', u'my', u'site', u'haha']

    >>> normalize_text("FOE JAPAN が粘り強く主張していた避難の権利")
    [u'foe', u'japan', u'\u304c\u7c98\u308a\u5f37\u304f\u4e3b\u5f35\u3057\u3066\u3044\u305f\u907f\u96e3\u306e\u6a29\u5229']

    >>> normalize_text('no ')
    [u'no']

    >>> normalize_text('')
    >>>
    """

    if not text: return

    if not isinstance(text, unicode):
        #make sure we're using unicode
        text = unicode(text, 'utf-8')

    text = text.lower()

    format_pats = (
            ("@[A-Za-z0-9_]+", ''), #remove re-tweets
            ("#[A-Za-z0-9_]+", ''), #remove hash tags
            ("(\w)\\1{2,}", "\\1\\1"), #remove occurences of more than two consecutive repeating characters
            ("<[^<]+?>", ''), #remove html tags
            ("(http|www)[^ ]*", ''), #get rid of any left over urls
            )

    for pat in format_pats:
        text = re.sub(pat[0], pat[1], text)


    emoticons = getattr(config, 'EMOTICONS', '')
    _tmp = set()
    if emoticons:
        for e in emoticons:
            if e in text:
                _tmp.add(e)

    text = text.translate(PUNC_MAP).strip() + ' ' #remove punctuation
    if _tmp:
        text += ' '.join([e for e in _tmp]) #attach emoticons back

    if text:
        #tokenize on words longer than 1 char
        words = [w for w in WhitespaceTokenizer().tokenize(text) if len(w) > 1]

        return words

if __name__ == '__main__':
    import doctest
    doctest.testmod()


########NEW FILE########
