__FILENAME__ = category_predictor
# Copyright 2011 Yelp and Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""An MRJob that constructs the data necessary to predict category
information
"""

import re

from mrjob.job import MRJob
from mrjob.protocol import JSONValueProtocol

# require at least this many occurences for a word to show up for a
# given category 
MINIMUM_OCCURENCES = 100

def words(text):
    """An iterator over tokens (words) in text. Replace this with a
    stemmer or other smarter logic.
    """

    for word in text.split():
        # normalize words by lowercasing and dropping non-alpha
        # characters
        normed = re.sub('[^a-z]', '', word.lower())

        if normed:
            yield normed

class CategoryPredictor(MRJob):
    """A very simple category predictor. Trains on review data and
    generates a simple naive-bayes model that can predict the category
    of some text.
    """

    # The input is the dataset - interpret each line as a single json
    # value (the key will be None)
    INPUT_PROTOCOL = JSONValueProtocol

    def review_category_mapper(self, _, data):
        """Visit reviews and businesses, yielding out (business_id,
        (review or category)).
        """
        if data['type'] == 'review':
            yield data['business_id'], ('review', data['text'])
        elif data['type'] == 'business':
            yield data['business_id'], ('categories', data['categories'])

    def add_categories_to_reviews_reducer(self, business_id, reviews_or_categories):
        """Yield out (category, review) for each category-review
        pair. We'll do the actual review tokenizing in the next
        mapper, since you typically have much more map-capacity than
        reduce-capacity.
        """
        categories = None
        reviews = []

        for data_type, data in reviews_or_categories:
            if data_type == 'review':
                reviews.append(data)
            else:
                categories = data

        # We either didn't find a matching business, or this biz
        # doesn't have any categories. In either case, we can drop
        # these reviews.
        if not categories:
            return

        # Yield out review counts in the same format as the
        # tokenize_reviews_mapper. We'll special case the 'all' key in
        # that method, but afterwards it will be treated the same.
        yield 'all', dict((cat, len(reviews)) for cat in categories)

        for category in categories:
            for review in reviews:
                yield category, review

    def tokenize_reviews_mapper(self, category, review):
        """Split reviews into words, yielding out (category, {word: count}) and
        ('all', {word: count}). We yield out a dictionary of counts
        rather than a single entry per-word to reduce the amount of
        i/o between mapper and reducer.
        """
        # special case - pass through category counts (which are
        # already formatted like the output of this mapper)
        if category == 'all':
            yield category, review
            return

        counts = {}
        for word in words(review):
            counts[word] = counts.get(word, 0) + 1

        yield category, counts

    def sum_counts(self, category, counts):
        """Sum up dictionaries of counts, filter out rare words
        (bucketing them into an unknown word bucket), and yield the
        counts.
        """
        raw_count = {}

        # sum up the individual counts
        for word_count in counts:
            for word, count in word_count.iteritems():
                raw_count[word] = raw_count.get(word, 0) + count

        # don't filter out low-mass categories
        if category == 'all':
            yield category, raw_count
            return

        # filter out low-count words; assign a very low mass to
        # unknown words
        filtered_counts = {}
        for word, count in raw_count.iteritems():
            if count > MINIMUM_OCCURENCES:
                filtered_counts[word] = count

        # don't include categories with every word filtered out
        if not filtered_counts:
            return

        # Assign a small mass to unknown tokens - check out
        # http://en.wikipedia.org/wiki/Laplacian_smoothing for background.
        filtered_counts['UNK'] = 0.01

        # emit the result
        yield category, filtered_counts

    def steps(self):
        return [self.mr(mapper=self.review_category_mapper, 
                reducer=self.add_categories_to_reviews_reducer),
            self.mr(mapper=self.tokenize_reviews_mapper, 
                reducer=self.sum_counts)] 


if __name__ == "__main__":
    CategoryPredictor().run()


########NEW FILE########
__FILENAME__ = predict
# Copyright 2011 Yelp and Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Use the output from the CategoryPredictor MRJob to predict the
category of text. This uses a simple naive-bayes model - see
http://en.wikipedia.org/wiki/Naive_Bayes_classifier for more details.
"""

from __future__ import with_statement

import math
import sys

import category_predictor

class ReviewCategoryClassifier(object):
	"""Predict categories for text using a simple naive-bayes classifier."""

	@classmethod
	def load_data(cls, input_file):
		"""Read the output of the CategoryPredictor mrjob, returning
		total category counts (count of # of reviews for each
		category), and counts of words for each category.
		"""

		job = category_predictor.CategoryPredictor()

		category_counts = None
		word_counts = {}

		with open(input_file) as src:
			for line in src:
				category, counts = job.parse_output_line(line)

				if category == 'all':
					category_counts = counts
				else:
					word_counts[category] = counts

		return category_counts, word_counts

	@classmethod
	def normalize_counts(cls, counts):
		"""Convert a dictionary of counts into a log-probability
		distribution.
		"""
		total = sum(counts.itervalues())
		lg_total = math.log(total)

		return dict((key, math.log(cnt) - lg_total) for key, cnt in counts.iteritems())

	def __init__(self, input_file):
		"""input_file: the output of the CategoryPredictor job."""
		category_counts, word_counts = self.load_data(input_file)

		self.word_given_cat_prob = {}
		for cat, counts in word_counts.iteritems():
			self.word_given_cat_prob[cat] = self.normalize_counts(counts)

		# filter out categories which have no words
		seen_categories = set(word_counts)
		seen_category_counts = dict((cat, count) for cat, count in category_counts.iteritems() \
										if cat in seen_categories)
		self.category_prob = self.normalize_counts(seen_category_counts)

	def classify(self, text):
		"""Classify some text using the result of the
		CategoryPredictor MRJob. We use a basic naive-bayes model,
		eg, argmax_category p(category) * p(words | category) ==
		p(category) * pi_{i \in words} p(word_i | category).

		p(category) is stored in self.category_prob, p(word | category
		is in self.word_given_cat_prob.
		"""
		# start with prob(category)
		lg_scores = self.category_prob.copy()

		# then multiply in the individual word probabilities
		# NOTE: we're actually adding here, but that's because our
		# distributions are made up of log probabilities, which are
		# more accurate for small probabilities. See
		# http://en.wikipedia.org/wiki/Log_probability for more
		# details.
		for word in category_predictor.words(text):
			for cat in lg_scores:
				cat_probs = self.word_given_cat_prob[cat]

				if word in cat_probs:
					lg_scores[cat] += cat_probs[word]
				else:
					lg_scores[cat] += cat_probs['UNK']

		# convert scores to a non-log value
		scores = dict((cat, math.exp(score)) for cat, score in lg_scores.iteritems())

		# normalize the scores again - this isnt' strictly necessary,
		# but it's nice to report probabilities with our guesses
		total = sum(scores.itervalues())
		return dict((cat, prob / total) for cat, prob in scores.iteritems())


if __name__ == "__main__":
	input_file = sys.argv[1]
	text = sys.argv[2]

	guesses = ReviewCategoryClassifier(input_file).classify(text)

	best_guesses = sorted(guesses.iteritems(), key=lambda (_, prob): prob, reverse=True)[:5]

	for guess, prob in best_guesses:
		print 'Category: "%s" - %.2f%% chance' % (guess, prob * 100)

########NEW FILE########
__FILENAME__ = simple_global_positivity
# Copyright 2011 Yelp and Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

from mrjob.job import MRJob
from mrjob.protocol import JSONValueProtocol

MINIMUM_OCCURENCES = 1000

def avg_and_total(iterable):
    """Compute the average over a numeric iterable."""
    items = 0
    total = 0.0

    for item in iterable:
        total += item
        items += 1

    return total / items, total

class PositiveWords(MRJob):
    """Find the most positive words in the dataset."""

    # The input is the dataset - interpret each line as a single json
    # value (the key will be None)
    INPUT_PROTOCOL = JSONValueProtocol

    def review_mapper(self, _, data):
        """Walk over reviews, emitting each word and its rating."""
        if data['type'] != 'review':
            return

        # normalize words by lowercasing and dropping non-alpha
        # characters
        norm = lambda word: re.sub('[^a-z]', '', word.lower())
        # only include a word once per-review (which de-emphasizes
        # proper nouns)
        words = set(norm(word) for word in data['text'].split())

        for word in words:
            yield word, data['stars']

    def positivity_reducer(self, word, ratings):
        """Emit average star rating, word in a format we can easily
        sort with the unix sort command: 
        [star average * 100, total count], word.
        """
        avg, total = avg_and_total(ratings)

        if total < MINIMUM_OCCURENCES:
            return

        yield (int(avg * 100), total), word

    def steps(self):
        return [self.mr(), # Split apart the dataset into multiple
                # chunks. In regular hadoop-land you could change the
                # splitter. This is normally < 30 seconds of work.
                self.mr(self.review_mapper, self.positivity_reducer)]


if __name__ == "__main__":
    PositiveWords().run()

########NEW FILE########
__FILENAME__ = weighted_category_positivity
# Copyright 2011 Yelp and Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

from mrjob.job import MRJob
from mrjob.protocol import JSONValueProtocol

def avg_and_total(iterable):
    """Compute the average over a numeric iterable."""
    items = 0
    total = 0.0

    for item in iterable:
        total += item
        items += 1

    return total / items, total

# Considerably lower than for the simple global script, since category
# data is much more sparse
MINIMUM_OCCURENCES = 50

# Require reviews from AT LEAST this many distinct businesses before
# we include a word (prevents very popular restaurant names from
# showing up in the list)
MINIMUM_BUSINESSES = 3

class WeightedPositiveWords(MRJob):
    """Find the most positive words in the dataset."""

    # The input is the dataset - interpret each line as a single json
    # value (the key will be None)
    INPUT_PROTOCOL = JSONValueProtocol

    def review_category_mapper(self, _, data):
        """Walk over reviews, emitting each word and its rating."""
        if data['type'] == 'review':
            yield data['business_id'], ('review', (data['text'], data['stars']))

        elif data['type'] == 'business':
            # skip businesses with no categories
            if data['categories']:
                yield data['business_id'], ('categories', data['categories'])

    def category_join_reducer(self, business_id, reviews_or_categories):
        """Take in business_id, ((review text and rating) or category information), emit
        category, (biz_id, (review, rating)).
        """
        categories = None
        reviews = []

        for data_type, data in reviews_or_categories:
            if data_type == 'review':
                reviews.append(data)
            else:
                categories = data

        # no categories found, skip this
        if not categories:
            return

        for category in categories:
            for review_positivity in reviews:
                yield category, (business_id, review_positivity)

    def review_mapper(self, category, biz_review_positivity):
        """Take in category, (biz_id, (review, rating)) and split the
        review into individual unique words. Emit 
        (category, word), (biz_id, rating), which will then be used to
        gather info about each category / word pair.
        """
        biz_id, (review, positivity) = biz_review_positivity

        # normalize words by lowercasing and dropping non-alpha
        # characters
        norm = lambda word: re.sub('[^a-z]', '', word.lower())
        # only include a word once per-review (which de-emphasizes
        # proper nouns)
        words = set(norm(word) for word in review.split())

        for word in words:
            yield (category, word), (biz_id, positivity)

    def positivity_reducer(self, category_word, biz_positivities):
        """Read (category, word), (biz_id, positivity), and compute
        the average positivity for the category-word pair. Skip words
        that don't occur frequently enough or for not enough unique
        businesses.

        Emits rating, (category, # reviews with word, word).
        """

        category, word = category_word

        businesses = set()
        positivities = []
        for biz_id, positivity in biz_positivities:
            businesses.add(biz_id)
            positivities.append(positivity)

        # don't include words that only show up for a few businesses
        if len(businesses) < MINIMUM_BUSINESSES:
            return

        avg, total = avg_and_total(positivities)

        if total < MINIMUM_OCCURENCES:
            return

        yield int(avg * 100), (category, total, word)

    def steps(self):
        return [ self.mr(self.review_category_mapper, self.category_join_reducer),
                self.mr(self.review_mapper, self.positivity_reducer)]


if __name__ == "__main__":
    WeightedPositiveWords().run()

########NEW FILE########
__FILENAME__ = autopilot
# Copyright 2011 Yelp and Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Gather the data necessary to generate reviews using a simple markov
model (see http://en.wikipedia.org/wiki/Markov_chain for more
details). We gather word-next word counts for each category,
eliminating rare pairs.
"""

import re

from mrjob.job import MRJob
from mrjob.protocol import JSONValueProtocol

# Chance that the review will end after any given word.
END_OF_REVIEW_RATE = 0.01

MINIMUM_PAIR_COUNT = 5
MINIMUM_FOLLOW_PERCENTAGE = 0.01

def words(text):
    """An iterator over tokens (words) in text. Replace this with a
    stemmer or other smarter logic.
    """

    for word in text.split():
        # normalize words by lowercasing and dropping non-alpha
        # characters
        normed = re.sub('[^a-z]', '', word.lower())

        if not normed:
            continue

        yield normed

def word_pairs(text):
    """Given some text, yield out pairs of words (eg bigrams)."""
    last_word = None

    for word in words(text):
        if last_word is not None:
            yield last_word, word
        last_word = word

    yield last_word, "<end>"

class ReviewAutoPilot(MRJob):
    """Very simple markov model for reviews, parameterized on business category."""

    INPUT_PROTOCOL = JSONValueProtocol

    def business_join_mapper(self, _, data):
        """Walk through reviews and businesses, yielding out the raw
        data.
        """
        if data['type'] == 'business':
            yield data['business_id'], ('business', data)
        elif data['type'] == 'review':
            yield data['business_id'], ('review', data['text'])

    def join_reviews_with_categories_reducer(self, business_id, reviews_or_biz):
        """Join reviews with the categories from the associated
        business.
        """
        categories = None
        reviews = []

        for data_type, data in reviews_or_biz:
            if data_type == 'business':
                categories = data['categories']
            else:
                reviews.append(data)

        # don't bother with these businesses
        if not categories:
            return

        for review in reviews:
            yield categories, review

    def review_split_mapper(self, categories, review):
        """Split a review into pairs of words and yield out 
        (start word, category), (follow word, count), combining
        repeated pairs into a single emission.
        """
        pair_counts = {}

        for pair in word_pairs(review):
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

        for (start, follow), count in pair_counts.iteritems():
            for category in categories:
                yield (start, category), (follow, count)

    def follow_probs_reducer(self, start_word_category, follow_word_counts):
        """Given a start word and a category, find the distribution
        over next words. When normalized, this count defines the
        transition probability for the markov chain.
        """
        start, category = start_word_category
        follow_counts = {}

        for follow_word, count in follow_word_counts:
            follow_counts[follow_word] = follow_counts.get(follow_word, 0) + count

        total_transitions = float(sum(follow_counts.itervalues()))

        include_word = lambda count: count > MINIMUM_PAIR_COUNT and count / total_transitions > MINIMUM_FOLLOW_PERCENTAGE
        thresholded_follow_counts = dict((word, count) for word, count in follow_counts.iteritems() if include_word(count))

        # filter out transitions where the transition has either
        # occurred a minimum number of times, or does not make up a
        # minimum percentage of outgoing transitions.
        if not thresholded_follow_counts:
            return

        # put a small weight on <end>, which means 'end of review'.
        thresholded_follow_counts['<end>'] = thresholded_follow_counts.get('<end>', 0.0) 
        thresholded_follow_counts['<end>'] += END_OF_REVIEW_RATE * float(sum(thresholded_follow_counts.itervalues()))

        # re-normalize the remaining transition weights.
        new_total = float(sum(thresholded_follow_counts.itervalues()))
        percentages = dict((follow, count / new_total) for follow, count in thresholded_follow_counts.iteritems())

        yield (category, start), percentages

    def steps(self):
        return [ self.mr(mapper=self.business_join_mapper, reducer=self.join_reviews_with_categories_reducer),
                self.mr(mapper=self.review_split_mapper, reducer=self.follow_probs_reducer)]

if __name__ == "__main__":
    ReviewAutoPilot().run()


########NEW FILE########
__FILENAME__ = generate
# Copyright 2011 Yelp and Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import with_statement

import random
import sys

import autopilot

class ReviewMarkovGenerator(object):
    """Generate the remainder of a review, given a category and some
    start text.
    """
    
    @classmethod
    def load_data(cls, input_file):
        """Read the output of the ReviewAutoPilot mrjob, returning a
        transition distribution. The transition distribution is a
        dictionary with category keys. Each category key points to
        another dictionary, which contains word keys, which contain
        another set of dictionaries, which contain the probability of
        transitioning to the the next word.

        Here's an example:

        category_transitions = {'Food': {'hot': {'dog': 1.0}}}

        This means that for the category Food, the word 'hot' has a
        100% probability of being followed by the word 'dog'.
        """
        job = autopilot.ReviewAutoPilot()

        category_transitions = {}

        with open(input_file) as src:
            for line in src:
                (category, start), transitions = job.parse_output_line(line)

                category_transitions.setdefault(category, {})[start] = transitions

        return category_transitions

    @classmethod
    def sample(cls, distribution):
        """Sample from a dictionary containing a probability
        distribution.
        """
        guess = random.random()

        for word, prob in distribution.iteritems():
            if guess <= prob:
                return word

            guess -= prob

        # random.random() returns a value between 0 and 1. The values
        # of distribution are assumed to sum to 1 (since distribution
        # is a probability distribution), so random.random() -
        # sum(values) == 0. If this is not the case, then distribution
        # is not a valid distribution.
        assert False, "distribution is not a valid probability distribution!"

    def __init__(self, input_file):
        """input_file: the output of the ReviewAutopilot job."""
        self.category_transitions = self.load_data(input_file)

    def complete(self, category, text):
        """Complete some text."""
        if category not in self.category_transitions:
            raise KeyError('Unknown category (invalid or not enough data): %s' % category)

        words = list(autopilot.words(text))

        last_word = words[-1]
        transitions = self.category_transitions[category]
        while True:
            next_word = self.sample(transitions[last_word])

            # the end-of-review token is None, which is JSON null,
            # which is coerced to the string "null" (since json
            # objects can only have strings as keys)
            if next_word == "<end>":
                break

            text += ' ' + next_word
            last_word = next_word

        return text


if __name__ == "__main__":
    input_file = sys.argv[1]
    category = sys.argv[2]
    text = sys.argv[3]

    print ReviewMarkovGenerator(input_file).complete(category, text)

########NEW FILE########
__FILENAME__ = test_autopilot
from __future__ import with_statement

import unittest
from unittest import TestCase
from StringIO import StringIO

from review_autopilot.autopilot import ReviewAutoPilot

# These are used to create stdin string data.
CATEGORY = 'Company'
REVIEW_TEMPLATE = '{"type":"review", "stars":3, "text":"%s",\
"business_id":"%s"}\n'
BUSINESS_TEMPLATE = '{"type":"business", "categories": "%s",\
"business_id":"%s"}\n'
TEXT = 'Hello!'
ID = 128411
BIZ = 'Yelp'
# This is used to pass around dict data, which is slightly different than
# the string data above.
DATA = [
    {'type':'business', 'business_id': ID, 'data':'Info here'},
    {'type': 'review', 'business_id':ID, 'text': TEXT}
]


class TestReviewAutoPilotCase(TestCase):

    def test_business_mapper(self):
        """tests the individual mappers of ReviewAutoPilot"""
        job = ReviewAutoPilot()
        biz_results = list(job.business_join_mapper(None, DATA[0]))
        review_results = list(job.business_join_mapper(None, DATA[1]))

        biz_after_results = [(ID, ('business', DATA[0]))]
        review_after_results = [(ID, ('review', DATA[1]['text']))] 

        self.assertEqual(biz_results, biz_after_results)
        self.assertEqual(review_results, review_after_results)

    def test_smoke(self):
        """Uses small, static dataset possible on local, since a full run takes
        too long."""

        # Random data to feed into the markov model.
        # I use long runs of foo to get through the threshold filters.
        text = ('foo bar foo baz foo car foo daz ' + ('foo ' * 10) + 'foofoo yelp'
            'foo yar foo foo bar bar dar')
        single_review = REVIEW_TEMPLATE % (text, BIZ)
        business = BUSINESS_TEMPLATE % (CATEGORY, BIZ)
        static_stdin = StringIO(single_review + business)

        job = ReviewAutoPilot(['-r', 'inline', '--no-conf', '-'])
        job.sandbox(stdin=static_stdin)

        results = []
        with job.make_runner() as runner:
            runner.run()
            for line in runner.stream_output():
                key, value = job.parse_output_line(line)
                results.append(value)

        # Normal output to compare
        result = {'foo': 0.99009900990099009, '<end>': 0.0099009900990099011}
        self.assertEqual(results[0], result)

    def test_categories_reducer(self):
        """Tests join_reviews_with_categories_reducer with null data and some
        static data."""
        job = ReviewAutoPilot()
        VALUES = (('business', {'categories': CATEGORY}), ('review', TEXT))
        category_results = list(job.join_reviews_with_categories_reducer(BIZ, VALUES))
        results = [(CATEGORY, TEXT)]
        self.assertEqual(category_results, results)

    def test_split_mapper(self):
        """Tests split_mapper reducer in autopilot"""
        job = ReviewAutoPilot()
        TEST_RETURN = (('hello', 'C'), ('<end>', 1))
        self.assertEqual(job.review_split_mapper(CATEGORY, TEXT).next(),
            TEST_RETURN)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_category_predictor
from __future__ import with_statement

import json
import unittest
from unittest import TestCase
from StringIO import StringIO

from category_predictor.category_predictor import CategoryPredictor

# These templates can be used to make a json string very easily.
REVIEW_TEMPLATE = '{"type":"review", "stars":3, "text":"%s",\
"business_id":"%s"}\n'
BUSINESS_TEMPLATE = '{"type":"business", "categories":["%s"], \
"business_id":"%s"}\n'
LONG_TEXT = "Hello world" * 101
TEXT = u"Hello"
BIZ_ID = u"Yelp"
CATEGORY = u'Company'


class TestCategoryPredictor(TestCase):

    def test_smoke(self):
        """Does a complete run with mock data"""
        business = BUSINESS_TEMPLATE % (CATEGORY, BIZ_ID)
        review = REVIEW_TEMPLATE % (LONG_TEXT, BIZ_ID)
        total_input = business + review
        static_stdin = StringIO(total_input)

        job = CategoryPredictor(['-r', 'inline', '--no-conf', '-'])
        job.sandbox(stdin=static_stdin)

        results = []
        with job.make_runner() as runner:
            runner.run()
            for line in runner.stream_output():
                key, value = job.parse_output_line(line)
                results.append(value)

        # Results should be the probability of that category being chosen.
        result = {CATEGORY: 1}
        self.assertEqual(results[0], result)

    def test_review_category(self):
        """Tests the category_mapper to make sure it is properly running"""
        business = BUSINESS_TEMPLATE % (CATEGORY, BIZ_ID)
        review = REVIEW_TEMPLATE % (TEXT, BIZ_ID)
        job = CategoryPredictor()
        review_results = list(job.review_category_mapper(None, json.loads(review)))
        biz_results = list(job.review_category_mapper(None, json.loads(business)))
        self.assertEqual(review_results, [(BIZ_ID, ('review', TEXT))])
        self.assertEqual(biz_results, [(BIZ_ID, ('categories', [CATEGORY]))])

    def test_categories_to_reviews(self):
        """Tests add_categories_to_reviews to make sure it is properly running"""
        category = [('categories', [CATEGORY]), ('review', TEXT)]

        job = CategoryPredictor()
        category_results = list(job.add_categories_to_reviews_reducer(BIZ_ID, category))
        result = [('all', {CATEGORY: 1}), (CATEGORY, TEXT)]
        self.assertEqual(category_results,result)

    def test_tokenize_reviews(self):
        """Tests tokenize_reviews_mapper to make sure it is properly running"""
        review = {CATEGORY: 1}

        job = CategoryPredictor()
        token_results = list(job.tokenize_reviews_mapper('all', review))
        result = [('all', {CATEGORY: 1})]
        self.assertEqual(token_results, result)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_weighted_positivity
from __future__ import with_statement

import json
import unittest
from unittest import TestCase
from StringIO import StringIO
import testify as T

from positive_category_words.weighted_category_positivity import WeightedPositiveWords


CATEGORY = u'Company'
REVIEW_TEMPLATE = ('{"type":"review", "stars":3, "text":"%s",'
'"business_id":"%s"}\n')
BUSINESS_TEMPLATE = ('{"type":"business", "categories":["%s"], '
'"business_id":"%s"}\n')
TEXT = u"Hello world"
BIZ_NAME = u'Qdoba'


class TestWeightedPositiveWords(TestCase):

    def test_smoke(self):
        """Does a full run of weighted positive words"""

        # Need 3 mock businesses to test
        business1 = BUSINESS_TEMPLATE % (CATEGORY, "Yelp")
        business2 = BUSINESS_TEMPLATE % (CATEGORY, "Target")
        business3 = BUSINESS_TEMPLATE % (CATEGORY, "Walmart") 
        # Need more than 1 review for weighted threshold
        review1 = REVIEW_TEMPLATE % (TEXT, "Yelp")
        review2 = REVIEW_TEMPLATE % (TEXT, "Target")
        review3 = REVIEW_TEMPLATE % (TEXT, "Walmart")

        # Need at least 50 occurrences of reviews, so multiply the first review by 20
        total_input = (business1 + business2 + business3
            + (review1 * 20) + review2 + review3)
        static_stdin = StringIO(total_input)

        job = WeightedPositiveWords(['-r', 'inline', '--no-conf', '-'])
        job.sandbox(stdin=static_stdin)

        results = []
        with job.make_runner() as runner:
            runner.run()
            for line in runner.stream_output():
                key, value = job.parse_output_line(line)
                results.append(value)
        end_result = [[CATEGORY, 66.0, 'hello'], [CATEGORY, 66.0, 'world']]
        self.assertEqual(results, end_result)

    def test_review_category(self):
        """Test the review_category_mapper function with a mock input"""

        review = REVIEW_TEMPLATE % (TEXT, BIZ_NAME)
        business = BUSINESS_TEMPLATE % (CATEGORY, BIZ_NAME)

        job = WeightedPositiveWords()
        review_results = list(job.review_category_mapper(None, json.loads(review)))
        biz_results = list(job.review_category_mapper(None, json.loads(business)))
        review_after_results = [(BIZ_NAME, ('review', (TEXT, 3)))]                
        biz_after_results = [(BIZ_NAME, ('categories', [CATEGORY]))]
        self.assertEqual(review_results, review_after_results)
        self.assertEqual(biz_results, biz_after_results)


    def test_category_join(self):
        """Test the category_join_reducer function with the same results
        from above. These tests should be used to isolate where an error
        will come from if a person changes any of the functions in the mr
        """
        review_or_categories = (('review', (TEXT, 3)),  ('categories', [CATEGORY]))

        job = WeightedPositiveWords()
        join_results = list(job.category_join_reducer(BIZ_NAME, review_or_categories))
        results = [(CATEGORY, (BIZ_NAME, (TEXT, 3)))]
        self.assertEqual(join_results, results)

    def test_review_mapper(self):
        """Test the review_mapper function to make sure that based on a mock input,
        it produces the correct calculated output
        """
        biz_review_positivity = (BIZ_NAME, (TEXT, 3))

        job = WeightedPositiveWords()
        review_results = list(job.review_mapper(CATEGORY, biz_review_positivity))
        results = [((CATEGORY, u'world'), (BIZ_NAME, 3)), ((CATEGORY, u'hello'), (BIZ_NAME, 3))]
        T.assert_sorted_equal(review_results, results)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
