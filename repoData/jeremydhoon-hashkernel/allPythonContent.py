__FILENAME__ = fblearn
#!/usr/bin/env python

"""
fblearn -- train a hashkernel classifier on heterogenous Facebook data objects.
"""

import argparse
import copy
import json
import os
import shutil
import sys
import urllib2

import hashkernel

def get_url(field, access_token):
    return ("https://graph.facebook.com/me/%s?access_token=%s "
            % (field, access_token))

def fb_data_iterator(access_token, output_filename, fields=None):
    fields = fields or ["photos"]
    if os.path.exists(output_filename):
        shutil.copy(output_filename, output_filename + ".bak")
    with open(output_filename, "wb") as outfile:
        outfile.write("[\n")
        saw_prev = False
        for field in fields:
            url = get_url(field, access_token)
            while True:
                try:
                    doc = urllib2.urlopen(url, timeout=100000000)
                    feed = json.load(doc)
                    if "paging" not in feed:
                        break
                    url = feed["paging"]["next"]
                    if saw_prev:
                        outfile.write(",\n")
                    outfile.write(json.dumps(feed["data"], indent=4))
                    saw_prev = True
                except KeyboardInterrupt:
                    break
        outfile.write("]\n")

def load_fb_data(filename):
    return sum(json.load(open(filename, "r")), [])

def is_liked(item, threshold):
    if "likes" not in item:
        return False
    elif "count" not in item["likes"]:
        item["likes"]["count"] = len(item["likes"]["data"])
    likes = item.pop("likes")
    return likes["count"] >= threshold

def extract_labels(fb_data, threshold):
    return [(item, is_liked(item, threshold))
            for item in copy.deepcopy(fb_data)]

def train_test(instances, test_index, bits, salts):
    kernel = hashkernel.HashKernelLogisticRegression(
        bits=bits,
        salts=range(salts))
    test_instance, test_label = instances[test_index]
    for ix, (item, label) in enumerate(instances):
        if ix == test_index:
            continue
        kernel.add(item, label)
    return kernel.predict(test_instance), test_label

def main(argv):
    assert argv, "Invalid command line arguments"

    access_token_help = (
        "If specified, use this access token to load Facebook data. "
        "To obtain an access token, register as a Facebook Developer and "
        "visit https://developers.facebook.com/tools/explorer.")
    fb_file_help = (
        "File in which to read/write Facebook data. If an access token is "
        "also provided, then overwrites this file and subsequently reads "
        "its contents.")

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--access-token", dest="access_token",
                        action="store", type=str, default=None,
                        help=access_token_help)
    parser.add_argument("-f", "--fb-file", dest="fb_file",
                        action="store", type=str, default=None,
                        help=fb_file_help)
    parser.add_argument("-d", "--fields", dest="fields", action="store",
                        type=str, default="statuses",
                        help=("Types of FB data to fetch (only valid with "
                              "an access token). Comma-separated."))
    parser.add_argument("-n", "--like-threshold", dest="like_threshold",
                        action="store", type=int, default=1,
                        help=("Minimum number of likes an object must "
                              "recieve in order to be considered a positive "
                              "instance."))
    parser.add_argument("-s", "--salts", dest="salts", type=int, default=1,
                        help="Number of salts to use.")
    parser.add_argument("-b", "--bits", dest="bits", action="store", type=int,
                        default=14, help="Number of hash kernel bits to use.")
    args = parser.parse_args(argv[1:])

    if args.fb_file is None:
        args.fb_file = os.path.join(
            os.path.dirname(__file__),
            "data",
            "feed.json")
    if args.access_token:
        fields = args.fields.split(",")
        fb_data_iterator(args.access_token, args.fb_file, fields)
    if not os.path.exists(args.fb_file):
        parser.error(
            ("FB data file does not exist: %s. "
             "Supply an access token to generate a data file.") % args.fb_file)
        return 1

    fb_data = load_fb_data(args.fb_file)
    labeled_fb_data = extract_labels(fb_data, args.like_threshold)
    false_positive = 0
    false_negative = 0
    count = len(fb_data)
    num_liked = sum([int(label) for _, label in labeled_fb_data])
    for test_index in xrange(count):
        pred, label = train_test(
            labeled_fb_data,
            test_index,
            args.bits,
            args.salts)
        if pred and not label:
            false_positive += 1
        elif label and not pred:
            false_negative += 1
    print "failure rate:", float(false_positive + false_negative) / count
    print "fp/fn/total", false_positive, false_negative, count
    print "rate liked:", float(num_liked) / count


if __name__ == "__main__":
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = hashkernel
#!/usr/bin/env python

"""
hashkernel.py -- a convenient way to turn any set of input features into feature
vector.
"""

import argparse
import collections
import csv
import itertools
import os
import random
import zlib  # for crc32 hash

import numpy as np
from sklearn import linear_model

class HashKernelLogisticRegression(object):
    MAX_BITS = 26  # seriously, you don't need that many bits
    MAX_BUFFER_SIZE = 500
    def __init__(self, bits=10, salts=None):
        if bits > self.MAX_BITS:
            raise ValueError(
                ("Attempted to create a %s with %d bits, but a maximum of %d "
                 "is allowed") % (self.__class__, bits, self.MAX_BITS))
        if bits <= 0:
            raise ValueError(
                "%s requires a positive number of bits required."
                % self.__class__)
        self.bits = bits
        self.bitmask = (1 << self.bits) - 1
        self.clf = linear_model.LogisticRegression(penalty="l2")
        self.hash_buffer = np.zeros(
            (self.MAX_BUFFER_SIZE, 1 << self.bits),
            dtype=np.float)
        self.buffered_instances = []
        self.buffered_labels = set()
        self.salts = salts or [0]
        if not len(self.salts):
            raise ValueError("%s requires at least one salt." % self.__class__)

    def add(self, instance, label):
        self.buffered_instances.append((instance, label))
        self.buffered_labels.add(label)
        if len(self.buffered_instances) >= self.MAX_BUFFER_SIZE:
            self.flush()

    def flush(self):
        if not len(self.buffered_instances) or len(self.buffered_labels) < 2:
            return  # can't flush yet
        labels = []
        self.hash_buffer[:] = 0
        for row, (instance, label) in enumerate(self.buffered_instances):
            self._add_feature_to_row(row, instance)
            labels.append(label)
        self._update_from_buffer(labels)
        self.buffered_instances = []
        self.buffered_labels = set()

    def predict(self, instance):
        self.flush()
        self.hash_buffer[0,:] = 0
        self._add_feature_to_row(0, instance)
        return self.clf.predict(self.hash_buffer[0,:])[0]

    def _add_feature_to_row(self, row, instance, hashables=None):
        hashables = hashables or []
        if isinstance(instance, dict) or hasattr(instance, "__dict__"):
            if not isinstance(instance, dict):
                instance = instance.__dict__
            for key, feature in instance.iteritems():
                self._add_feature_to_row(
                    row,
                    feature,
                    hashables + ["dict_key_%s" % key])
        elif isinstance(instance, (list, tuple)):
            for ix, feature in enumerate(instance):
                self._add_feature_to_row(
                    row,
                    feature,
                    hashables + ["list_index_%d" % ix])
        elif isinstance(instance, basestring):
            if isinstance(instance, unicode):
                instance = instance.encode('utf-8')
            for word in instance.split():
                self._add_categorical(row, hashables + ["word_%s" % word])
        elif isinstance(instance, (int, long)):
            self._add_categorical(row, hashables + ["int_%d" % instance])
        elif isinstance(instance, float):
            self._add_continuous(row, hashables, instance)

    def _update_from_buffer(self, labels):
        self.clf.fit(self.hash_buffer[:len(labels),:], labels)

    def _hash_multiple(self, hashables, salt):
        return reduce(
            lambda hashed, hashable: self._hash_feature(hashable, hashed),
            hashables,
            salt)

    def _add_categorical(self, row, hashables):
        for salt in self.salts:
            feature_hash = self._hash_multiple(hashables, salt)
            self._add_hash(row, feature_hash, 1)

    def _add_continuous(self, row, hashables, value):
        for salt in self.salts:
            index_hash = self._hash_multiple(hashables, salt)
            self._add_hash(row, index_hash, value)

    def _hash_feature(self, hashable_value, previous_hash):
        return zlib.crc32(hashable_value, previous_hash)

    def _add_hash(self, row, feature_hash, value):
        sign = 2 * ((feature_hash & (1 << self.bits)) >> self.bits) - 1
        self.hash_buffer[row, feature_hash & self.bitmask] += sign * value

def select_features(features, num_omitted):
    to_omit = set(random.sample(range(len(features)), num_omitted))
    return [f if ix not in to_omit else '<unknown>'
            for ix, f in enumerate(features)]

def compute_error(predictions, labels):
    error_count = sum([int(p != l) for p, l in zip(predictions, labels)])
    return float(error_count) / len(predictions)

def open_data_file(basename):
    return open(os.path.join(os.path.dirname(__file__), "data", basename))

def clean_rows(rows_it):
    return itertools.ifilter(
        None,
        itertools.imap(lambda row: map(str.strip, row), csv.reader(rows_it)))

def test(kernel, instances, test_probability):
    test_instances = []
    for instance, label in instances:
        if random.random() < test_probability:
            test_instances.append((instance, label))
        else:
            kernel.add(instance, label)
    predictions = []
    labels = []
    for instance, label in test_instances:
        predictions.append(kernel.predict(instance))
        labels.append(label)
    return compute_error(predictions, labels)

def load_mushroom_dataset(num_omitted):
    with open_data_file("agaricus-lepiota.data") as row_iterable:
        for row in clean_rows(row_iterable):
            yield select_features(row[1:], num_omitted), row[0] == 'p'

def load_us_adult_dataset(num_omitted):
    with open_data_file("adult.data") as row_iterable:
        for row in clean_rows(row_iterable):
            yield select_features(row[:-1], num_omitted), row[-1] == ">50K"

def main(argv):
    parser = argparse.ArgumentParser(
        description="Run machine learning experiments on hash kernels")
    parser.add_argument("-b", "--bits", type=int, dest="bits", default=8,
                        action="store",
                        help="Number of bits in the kernel spaces")
    parser.add_argument("-m", "--missing", type=int, dest="missing", default=0,
                        action="store",
                        help="Number of features to remove at random")
    parser.add_argument("-t", "--test-fraction", type=float,
                        dest="test_fraction", default=0.10,
                        action="store",
                        help="Number of instances to hold out for testing")
    parser.add_argument("--mushroom", dest="loaders", action="append_const",
                        const=load_mushroom_dataset,
                        help="Run the Mushroom dataset")
    parser.add_argument("--us-adult", dest="loaders", action="append_const",
                        const=load_us_adult_dataset,
                        help="Run the US Adult dataset")
    parser.add_argument("-s", "--salts", dest="salt_count", type=int,
                        action="store", default=1,
                        help="Number of salts to use")

    args = parser.parse_args(argv[1:])
    if not args.loaders:
        parser.error("Must provide at least one dataset such as --mushroom")

    for loader in args.loaders:
        random.seed(0)
        instances = loader(args.missing)
        kernel = HashKernelLogisticRegression(
            args.bits,
            salts=range(args.salt_count))
        error_rate = test(kernel, instances, args.test_fraction)
        print "Error rate on %s: %.3f" % (loader.func_name, error_rate)

if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))

########NEW FILE########
