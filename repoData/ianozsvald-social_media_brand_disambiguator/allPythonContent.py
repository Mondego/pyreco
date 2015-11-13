__FILENAME__ = production
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Production configuration (imported by __init__.py)"""

sqldb = "data/annotations.sqlite"

########NEW FILE########
__FILENAME__ = testing
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Testing configuration (imported by __init__.py)"""

sqldb = ":memory:"

########NEW FILE########
__FILENAME__ = export_classified_tweets
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Annotate tweets by hand to create a gold standard"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import sys
import sql_convenience
import unicodecsv

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tweet annotator')
    parser.add_argument('keyword', help='Keyword we wish to disambiguate (determines table name and used to filter tweets)')
    parser.add_argument('--csv', default=None, help='CSV filename to write to (e.g. output.csv), defaults to stdout')
    args = parser.parse_args()

    if args.csv is None:
        writer_stream = sys.stdout
    else:
        writer_stream = open(args.csv, "w")

    writer = unicodecsv.writer(writer_stream, encoding='utf-8')

    classifications_and_tweets = sql_convenience.extract_classifications_and_tweets(args.keyword)
    for cls, tweet_id, tweet in classifications_and_tweets:
        writer.writerow((cls, tweet))

    if not writer_stream.isatty():
        # close the file (but not stdout if that's what we're using!)
        writer_stream.close()

########NEW FILE########
__FILENAME__ = export_inclass_outclass
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export in-class and out-class tweets to separate files as data for ML system"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import os
import unicodecsv
import sql_convenience


def writer(class_name, table, cls_to_accept):
    class_writer = unicodecsv.writer(open(class_name, 'w'), encoding='utf-8')
    class_writer.writerow(("tweet_id", "tweet_text"))
    for cls, tweet_id, tweet_text in sql_convenience.extract_classifications_and_tweets(args.table):
        if cls == cls_to_accept:
            # remove carriage returns
            tweet_text = tweet_text.replace("\n", " ")
            class_writer.writerow((tweet_id, tweet_text))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Score results against a gold standard')
    parser.add_argument('table', help='Name of table to export (e.g. annotations_apple)')
    args = parser.parse_args()

    data_dir = "data"
    in_class_name = os.path.join(data_dir, args.table + '_in_class.csv')
    out_class_name = os.path.join(data_dir, args.table + '_out_class.csv')

    print("Writing in-class examples to: {}".format(in_class_name))
    writer(in_class_name, args.table, sql_convenience.CLASS_IN)
    print("Writing out-of-class examples to: {}".format(out_class_name))
    writer(out_class_name, args.table, sql_convenience.CLASS_OUT)

########NEW FILE########
__FILENAME__ = learn1
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""First simple sklearn classifier"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import os
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn import linear_model
from sklearn import cross_validation
from sklearn.metrics import roc_curve, auc, precision_recall_curve
from matplotlib import pyplot as plt
from matplotlib import cm
from nltk.corpus import stopwords
import unicodecsv
import sql_convenience


############
# NOTE
# this is a basic LogisticRegression classifier, using 5-fold cross validation
# and a cross entropy error measure (which should nicely fit this binary
# decision classification problem).
# do not trust this code to do anything useful in the real world!
############


def reader(class_name):
    class_reader = unicodecsv.reader(open(class_name), encoding='utf-8')
    row0 = next(class_reader)
    assert row0 == ["tweet_id", "tweet_text"]
    lines = []
    for tweet_id, tweet_text in class_reader:
        txt = tweet_text.strip()
        if len(txt) > 0:
            lines.append(txt)
    return lines


def label_learned_set(vectorizer, clfl, threshold, validation_table):
    for row in sql_convenience.extract_classifications_and_tweets(validation_table):
        cls, tweet_id, tweet_text = row
        spd = vectorizer.transform([tweet_text]).todense()
        predicted_cls = clfl.predict(spd)
        predicted_class = predicted_cls[0]  # turn 1D array of 1 item into 1 item
        predicted_proba = clfl.predict_proba(spd)[0][predicted_class]
        if predicted_proba < threshold and predicted_class == 1:
            predicted_class = 0  # force to out-of-class if we don't trust our answer
        sql_convenience.update_class(tweet_id, validation_table, predicted_class)


def check_classification(vectorizer, clfl):
    spd0 = vectorizer.transform([u'really enjoying how the apple\'s iphone makes my ipad look small']).todense()
    print("1?", clfl.predict(spd0), clfl.predict_proba(spd0))  # -> 1 which is set 1 (is brand)
    spd1 = vectorizer.transform([u'i like my apple, eating it makes me happy']).todense()
    print("0?", clfl.predict(spd1), clfl.predict_proba(spd1))  # -> 0 which is set 0 (not brand)


def cross_entropy_error(Y, probas_):
    # compute Cross Entropy using the Natural Log:
    # ( -tln(y) ) − ( (1−t)ln(1−y) )
    probas_class1 = probas_[:, 1]  # get the class 1 probabilities
    cross_entropy_errors = ((-Y) * (np.log(probas_class1))) - ((1 - Y) * (np.log(1 - probas_class1)))
    return cross_entropy_errors


def show_cross_validation_errors(cross_entropy_errors_by_fold):
    print("Cross validation cross entropy errors:" + str(cross_entropy_errors_by_fold))
    print("Cross entropy (lower is better): %0.3f (+/- %0.3f)" % (cross_entropy_errors_by_fold.mean(), cross_entropy_errors_by_fold.std() / 2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple sklearn implementation, example usage "learn1.py scikit_testtrain_apple --validation_table=learn1_validation_apple"')
    parser.add_argument('table', help='Name of in and out of class data to read (e.g. scikit_validation_app)')
    parser.add_argument('--validation_table', help='Table of validation data - get tweets and write predicted class labels back (e.g. learn1_validation_apple)')
    parser.add_argument('--roc', default=False, action="store_true", help='Plot a Receiver Operating Characterics graph for the learning results')
    parser.add_argument('--pr', default=False, action="store_true", help='Plot a Precision/Recall graph for the learning results')
    parser.add_argument('--termmatrix', default=False, action="store_true", help='Draw a 2D matrix of tokens vs binary presence (or absence) using all training documents')
    args = parser.parse_args()

    data_dir = "data"
    in_class_name = os.path.join(data_dir, args.table + '_in_class.csv')
    out_class_name = os.path.join(data_dir, args.table + '_out_class.csv')

    in_class_lines = reader(in_class_name)
    out_class_lines = reader(out_class_name)

    # put all items into the training set
    train_set = out_class_lines + in_class_lines
    target = np.array([0] * len(out_class_lines) + [1] * len(in_class_lines))

    # choose a vectorizer to turn the tokens in tweets into a matrix of
    # examples (we can plot this further below using --termmatrix)
    stopWords = stopwords.words('english')
    MIN_DF = 2
    vectorizer_binary = CountVectorizer(stop_words=stopWords, min_df=MIN_DF, binary=True)
    vectorizer_tfidf = TfidfVectorizer(stop_words=stopWords, min_df=MIN_DF)
    #vectorizer = vectorizer_tfidf
    vectorizer = vectorizer_binary

    trainVectorizerArray = vectorizer.fit_transform(train_set).toarray()
    print("Feature names (first 20):", vectorizer.get_feature_names()[:20], "...")
    print("Vectorized %d features" % (len(vectorizer.get_feature_names())))

    clf = linear_model.LogisticRegression()

    kf = cross_validation.KFold(n=len(target), n_folds=5, shuffle=True)
    # using a score isn't so helpful here (I think) as I want to know the
    # distance from the desired categories and a >0.5 threshold isn't
    # necessaryily the right thing to measure (I care about precision when
    # classifying, not recall, so the threshold matters)
    #cross_val_scores = cross_validation.cross_val_score(clf, trainVectorizerArray, target, cv=kf, n_jobs=-1)
    #print("Cross validation in/out of class test scores:" + str(cross_val_scores))
    #print("Accuracy: %0.3f (+/- %0.3f)" % (cross_val_scores.mean(), cross_val_scores.std() / 2))

    # try the idea of calculating a cross entropy score per fold
    cross_entropy_errors_test_by_fold = np.zeros(len(kf))
    cross_entropy_errors_train_by_fold = np.zeros(len(kf))
    for i, (train_rows, test_rows) in enumerate(kf):
        Y_train = target[train_rows]
        X_train = trainVectorizerArray[train_rows]
        X_test = trainVectorizerArray[test_rows]
        probas_test_ = clf.fit(X_train, Y_train).predict_proba(X_test)
        probas_train_ = clf.fit(X_train, Y_train).predict_proba(X_train)
        # compute cross entropy for all trained and tested items in this fold
        Y_test = target[test_rows]

        cross_entropy_errors_test = cross_entropy_error(Y_test, probas_test_)
        cross_entropy_errors_train = cross_entropy_error(Y_train, probas_train_)
        cross_entropy_errors_test_by_fold[i] = np.average(cross_entropy_errors_test)
        cross_entropy_errors_train_by_fold[i] = np.average(cross_entropy_errors_train)
    #import pdb; pdb.set_trace()
    print("Training:")
    show_cross_validation_errors(cross_entropy_errors_train_by_fold)
    print("Testing:")
    show_cross_validation_errors(cross_entropy_errors_test_by_fold)

    if args.termmatrix:
        fig = plt.figure()
        # to plot the word vector on the training data use:
        plt.title("{} matrix of features per sample for {}".format(str(vectorizer.__class__).split('.')[-1][:-2], args.table))
        plt.imshow(trainVectorizerArray, cmap=cm.gray, interpolation='nearest', origin='lower')
        nbr_features = trainVectorizerArray.shape[1]
        plt.xlabel("{} Features".format(nbr_features))
        last_class_0_index = len(out_class_lines) - 1
        plt.ylabel("Samples (Class 0: 0-{}, Class 1: {}-{})".format(last_class_0_index, last_class_0_index + 1, trainVectorizerArray.shape[0] - 1))
        plt.hlines([last_class_0_index], 0, nbr_features, colors='r', alpha=0.8)
        plt.show()

    # plot a Receiver Operating Characteristics plot from the cross validation
    # sets
    if args.roc:
        fig = plt.figure()
        for i, (train, test) in enumerate(kf):
            probas_ = clf.fit(trainVectorizerArray[train], target[train]).predict_proba(trainVectorizerArray[test])
            fpr, tpr, thresholds = roc_curve(target[test], probas_[:, 1])
            roc_auc = auc(fpr, tpr)
            plt.plot(fpr, tpr, lw=1, alpha=0.8, label='ROC fold %d (area = %0.2f)' % (i, roc_auc))

        plt.plot([0, 1], [0, 1], '--', color=(0.6, 0.6, 0.6), label='Luck')

        plt.xlim([-0.05, 1.05])
        plt.ylim([-0.05, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('Receiver operating characteristics')  # , Mean ROC (area = %0.2f)' % (mean_auc))
        plt.legend(loc="lower right")
        plt.show()

    # plot a Precision/Recall line chart from the cross validation sets
    if args.pr:
        fig = plt.figure()
        for i, (train, test) in enumerate(kf):
            probas_ = clf.fit(trainVectorizerArray[train], target[train]).predict_proba(trainVectorizerArray[test])
            precision, recall, thresholds = precision_recall_curve(target[test], probas_[:, 1])
            pr_auc = auc(recall, precision)
            plt.plot(recall, precision, label='Precision-Recall curve %d (area = %0.2f)' % (i, pr_auc))

        plt.xlabel('Recall')
        plt.ylabel('Precision')
        plt.ylim([-0.05, 1.05])
        plt.xlim([-0.05, 1.05])
        plt.title('Precision-Recall curves')
        plt.legend(loc="lower left")
        plt.show()

    # write validation results to specified table
    if args.validation_table:
        # make sparse training set using all of the test/train data (combined into
        # one set)
        train_set_sparse = vectorizer.transform(train_set)
        # instantiate a local classifier
        clfl = clf.fit(train_set_sparse.todense(), target)

        # check and print out two classifications as sanity checks
        check_classification(vectorizer, clfl)
        # use a threshold (arbitrarily chosen at present), test against the
        # validation set and write classifications to DB for reporting
        chosen_threshold = 0.92
        label_learned_set(vectorizer, clfl, chosen_threshold, args.validation_table)

########NEW FILE########
__FILENAME__ = learn1_biasvar
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Use a decision tree classifier to plot overfitting due to allowing too deep a tree"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import os
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import precision_score
from sklearn import tree
from sklearn import cross_validation
from matplotlib import pyplot as plt
from nltk.corpus import stopwords
import unicodecsv


def reader(class_name):
    class_reader = unicodecsv.reader(open(class_name), encoding='utf-8')
    row0 = next(class_reader)
    assert row0 == ["tweet_id", "tweet_text"]
    lines = []
    for tweet_id, tweet_text in class_reader:
        txt = tweet_text.strip()
        if len(txt) > 0:
            lines.append(txt)
    return lines


def cross_entropy_error(Y, probas_):
    # compute Cross Entropy using the Natural Log:
    # ( -tln(y) ) − ( (1−t)ln(1−y) )
    probas_class1 = probas_[:, 1]  # get the class 1 probabilities
    # force any 1.0 (100%) probabilities to be fractionally smaller, so
    # np.log(1-1) doesn't generate a NaN
    probas_class1[np.where(probas_class1 == 1.0)] = 0.999999999999999
    probas_class1[np.where(probas_class1 == 0.0)] = 0.000000000000001
    #import pdb; pdb.set_trace()
    cross_entropy_errors = ((-Y) * (np.log(probas_class1))) - ((1 - Y) * (np.log(1 - probas_class1)))
    return cross_entropy_errors


def show_errors(cross_entropy_errors_by_fold, method="cross entropy", lower_is_better=True):
    print("Cross validation %s errors:" % (method) + str(cross_entropy_errors_by_fold))
    if lower_is_better:
        note = "(lower is better)"
    else:
        note = "(higher is better)"

    print("%s %s: %0.2f (+/- %0.2f)" % (method, note, cross_entropy_errors_by_fold.mean(), cross_entropy_errors_by_fold.std() / 2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple sklearn implementation, example usage "learn1.py scikit_testtrain_apple --validation_table=learn1_validation_apple"')
    parser.add_argument('table', help='Name of in and out of class data to read (e.g. scikit_validation_app)')
    #parser.add_argument('--validation_table', help='Table of validation data - get tweets and write predicted class labels back (e.g. learn1_validation_apple)')
    #parser.add_argument('--roc', default=False, action="store_true", help='Plot a Receiver Operating Characterics graph for the learning results')
    #parser.add_argument('--pr', default=False, action="store_true", help='Plot a Precision/Recall graph for the learning results')
    #parser.add_argument('--termmatrix', default=False, action="store_true", help='Draw a 2D matrix of tokens vs binary presence (or absence) using all training documents')
    args = parser.parse_args()

    data_dir = "data"
    in_class_name = os.path.join(data_dir, args.table + '_in_class.csv')
    out_class_name = os.path.join(data_dir, args.table + '_out_class.csv')

    in_class_lines = reader(in_class_name)
    out_class_lines = reader(out_class_name)

    # put all items into the training set
    train_set = np.array(out_class_lines + in_class_lines)
    target = np.array([0] * len(out_class_lines) + [1] * len(in_class_lines))

    f = plt.figure(1)
    f.clf()
    kf = cross_validation.KFold(n=len(target), n_folds=5, shuffle=True)
    max_branch_depth = range(1, 60, 2)
    all_precisions_train = []
    all_precisions_test = []
    for n in max_branch_depth:
        vectorizer = CountVectorizer(stop_words=stopwords.words('english'), ngram_range=(1, 3), min_df=2, binary=True, lowercase=True)
        trainVectorizerArray = vectorizer.fit_transform(train_set).toarray()
        # get list of feature_names, these occur > 1 time in the dataset
        print("-----------------")
        #print("Feature names (first 20):", vectorizer.get_feature_names()[:20], "...")
        print("Vectorized %d features" % (len(vectorizer.get_feature_names())))

        clf = tree.DecisionTreeClassifier(max_depth=n)

        precisions_train = []
        precisions_test = []
        for i, (train_rows, test_rows) in enumerate(kf):
            Y_train = target[train_rows]
            X_train = trainVectorizerArray[train_rows]
            X_test = trainVectorizerArray[test_rows]
            clf.fit(X_train, Y_train)
            predicted_test = clf.predict(X_test)
            predicted_train = clf.predict(X_train)
            Y_test = target[test_rows]

            precision_train = precision_score(Y_train, predicted_train)
            precision_test = precision_score(Y_test, predicted_test)

            precisions_train.append(precision_train)
            precisions_test.append(precision_test)

        precisions_train = 1 - np.array(precisions_train)
        precisions_test = 1 - np.array(precisions_test)
        test_labels = plt.plot([n] * len(precisions_test), precisions_test, 'og', alpha=0.8, label="Test errors")
        train_labels = plt.plot([n] * len(precisions_train), precisions_train, 'xr', alpha=0.8, label="Training errors")
        plt.draw()

        all_precisions_train.append(np.average(precisions_train))
        all_precisions_test.append(np.average(precisions_test))

    plt.plot(max_branch_depth, all_precisions_test, 'g')
    plt.plot(max_branch_depth, all_precisions_train, 'r')
    plt.xlabel("Decision tree max depth")
    plt.ylabel("Error (1.0-precision)")
    plt.legend((train_labels[0], test_labels[0]), (train_labels[0].get_label(), test_labels[0].get_label()))

    plt.show()

########NEW FILE########
__FILENAME__ = learn1_coefficients
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""First simple sklearn classifier"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import os
import copy
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn import linear_model
from sklearn import naive_bayes
from sklearn import cross_validation
from matplotlib import pyplot as plt
from nltk.corpus import stopwords
import unicodecsv
import sql_convenience


############
# NOTE
# this is a basic LogisticRegression classifier, using 5-fold cross validation
# and a cross entropy error measure (which should nicely fit this binary
# decision classification problem).
# do not trust this code to do anything useful in the real world!
############


def reader(class_name):
    class_reader = unicodecsv.reader(open(class_name), encoding='utf-8')
    row0 = next(class_reader)
    assert row0 == ["tweet_id", "tweet_text"]
    lines = []
    for tweet_id, tweet_text in class_reader:
        txt = tweet_text.strip()
        if len(txt) > 0:
            lines.append(txt)
    return lines


def label_learned_set(vectorizer, clfl, threshold, validation_table):
    for row in sql_convenience.extract_classifications_and_tweets(validation_table):
        cls, tweet_id, tweet_text = row
        spd = vectorizer.transform([tweet_text]).todense()
        predicted_cls = clfl.predict(spd)
        predicted_class = predicted_cls[0]  # turn 1D array of 1 item into 1 item
        predicted_proba = clfl.predict_proba(spd)[0][predicted_class]
        if predicted_proba < threshold and predicted_class == 1:
            predicted_class = 0  # force to out-of-class if we don't trust our answer
        sql_convenience.update_class(tweet_id, validation_table, predicted_class)


def check_classification(vectorizer, clfl):
    spd0 = vectorizer.transform([u'really enjoying how the apple\'s iphone makes my ipad look small']).todense()
    print("1?", clfl.predict(spd0), clfl.predict_proba(spd0))  # -> 1 which is set 1 (is brand)
    spd1 = vectorizer.transform([u'i like my apple, eating it makes me happy']).todense()
    print("0?", clfl.predict(spd1), clfl.predict_proba(spd1))  # -> 0 which is set 0 (not brand)


def annotate_tokens(indices_for_large_coefficients, clf, vectorizer, plt):
    y = clf.coef_[0][indices_for_large_coefficients]
    tokens = np.array(vectorizer.get_feature_names())[indices_for_large_coefficients]
    for x, y, token in zip(indices_for_large_coefficients, y, tokens):
        plt.text(x, y, token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple sklearn implementation, example usage "learn1.py scikit_testtrain_apple --validation_table=learn1_validation_apple"')
    parser.add_argument('table', help='Name of in and out of class data to read (e.g. scikit_validation_app)')
    parser.add_argument('--validation_table', help='Table of validation data - get tweets and write predicted class labels back (e.g. learn1_validation_apple)')
    parser.add_argument('--roc', default=False, action="store_true", help='Plot a Receiver Operating Characterics graph for the learning results')
    parser.add_argument('--pr', default=False, action="store_true", help='Plot a Precision/Recall graph for the learning results')
    parser.add_argument('--termmatrix', default=False, action="store_true", help='Draw a 2D matrix of tokens vs binary presence (or absence) using all training documents')
    args = parser.parse_args()

    data_dir = "data"
    in_class_name = os.path.join(data_dir, args.table + '_in_class.csv')
    out_class_name = os.path.join(data_dir, args.table + '_out_class.csv')

    in_class_lines = reader(in_class_name)
    out_class_lines = reader(out_class_name)

    # put all items into the training set
    train_set = out_class_lines + in_class_lines
    target = np.array([0] * len(out_class_lines) + [1] * len(in_class_lines))

    # choose a vectorizer to turn the tokens in tweets into a matrix of
    # examples (we can plot this further below using --termmatrix)
    stopWords = stopwords.words('english')
    MIN_DF = 2
    vectorizer_binary = CountVectorizer(stop_words=stopWords, min_df=MIN_DF, binary=True)
    vectorizer_tfidf = TfidfVectorizer(stop_words=stopWords, min_df=MIN_DF)
    #vectorizer = vectorizer_tfidf
    vectorizer = vectorizer_binary

    trainVectorizerArray = vectorizer.fit_transform(train_set).toarray()
    print("Feature names (first 20):", vectorizer.get_feature_names()[:20], "...")
    print("Vectorized %d features" % (len(vectorizer.get_feature_names())))

    MAX_PLOTS = 3
    f = plt.figure(1)
    plt.clf()
    f = plt.subplot(MAX_PLOTS, 1, 0)

    for n in range(MAX_PLOTS):
        if n == 0:
            clf = naive_bayes.BernoulliNB()
            title = "Bernoulli Naive Bayes"
        if n == 1:
            clf = linear_model.LogisticRegression()
            title = "Logistic Regression l2 error"
        if n == 2:
            clf = linear_model.LogisticRegression(penalty='l1')
            title = "Logistic Regression l1 error"

        kf = cross_validation.KFold(n=len(target), n_folds=5, shuffle=True)
        # using a score isn't so helpful here (I think) as I want to know the
        # distance from the desired categories and a >0.5 threshold isn't
        # necessaryily the right thing to measure (I care about precision when
        # classifying, not recall, so the threshold matters)
        #cross_val_scores = cross_validation.cross_val_score(clf, trainVectorizerArray, target, cv=kf, n_jobs=-1)
        #print("Cross validation in/out of class test scores:" + str(cross_val_scores))
        #print("Accuracy: %0.3f (+/- %0.3f)" % (cross_val_scores.mean(), cross_val_scores.std() / 2))

        f = plt.subplot(MAX_PLOTS, 1, n + 1)
        plt.title(title)

        for i, (train_rows, test_rows) in enumerate(kf):
            Y_train = target[train_rows]
            X_train = trainVectorizerArray[train_rows]
            X_test = trainVectorizerArray[test_rows]
            probas_test_ = clf.fit(X_train, Y_train).predict_proba(X_test)
            probas_train_ = clf.fit(X_train, Y_train).predict_proba(X_train)

            # plot the Logistic Regression coefficients

            if n == 1 or n == 2:
                coef = clf.coef_[0]
            if n == 0:
                coef = clf.coef_
            plt.plot(coef, 'b', alpha=0.3)
            plt.ylabel("Coefficient value")
        xmax = coef.shape[0]
        plt.xlim(xmax=xmax)

    plt.xlabel("Coefficient per term")
    # plot the tokens with the largest coefficients
    coef = copy.copy(clf.coef_[0])
    coef.sort()
    annotate_tokens(np.where(clf.coef_ >= coef[-10])[1], clf, vectorizer, plt)
    annotate_tokens(np.where(clf.coef_ < coef[10])[1], clf, vectorizer, plt)

    #f = plt.subplot(MAX_PLOTS, 1, 1)
    #plt.title("{}: l2 penalty (top) vs l1 penalty (bottom) for {} cross fold models on {}".format(str(clf.__class__).split('.')[-1][:-2], len(kf), args.table))
    plt.show()

########NEW FILE########
__FILENAME__ = learn1_experiments
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""First simple sklearn classifier"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import os
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import precision_score
from sklearn import linear_model
from sklearn import naive_bayes
from sklearn import tree
from sklearn import ensemble
from sklearn import svm
from sklearn import neighbors
from sklearn import cross_validation
#from sklearn.metrics import roc_curve, auc, precision_recall_curve
from matplotlib import pyplot as plt
#from matplotlib import cm
from nltk.corpus import stopwords
import unicodecsv


############
# NOTE
# this is a basic LogisticRegression classifier, using 5-fold cross validation
# and a cross entropy error measure (which should nicely fit this binary
# decision classification problem).
# do not trust this code to do anything useful in the real world!
############


def reader(class_name):
    class_reader = unicodecsv.reader(open(class_name), encoding='utf-8')
    row0 = next(class_reader)
    assert row0 == ["tweet_id", "tweet_text"]
    lines = []
    for tweet_id, tweet_text in class_reader:
        txt = tweet_text.strip()
        if len(txt) > 0:
            lines.append(txt)
    return lines


def cross_entropy_error(Y, probas_):
    # compute Cross Entropy using the Natural Log:
    # ( -tln(y) ) − ( (1−t)ln(1−y) )
    probas_class1 = probas_[:, 1]  # get the class 1 probabilities
    # force any 1.0 (100%) probabilities to be fractionally smaller, so
    # np.log(1-1) doesn't generate a NaN
    probas_class1[np.where(probas_class1 == 1.0)] = 0.999999999999999
    probas_class1[np.where(probas_class1 == 0.0)] = 0.000000000000001
    #import pdb; pdb.set_trace()
    cross_entropy_errors = ((-Y) * (np.log(probas_class1))) - ((1 - Y) * (np.log(1 - probas_class1)))
    return cross_entropy_errors


def show_errors(cross_entropy_errors_by_fold, method="cross entropy", lower_is_better=True):
    print("Cross validation %s errors:" % (method) + str(cross_entropy_errors_by_fold))
    if lower_is_better:
        note = "(lower is better)"
    else:
        note = "(higher is better)"

    print("%s %s: %0.2f (+/- %0.2f)" % (method, note, cross_entropy_errors_by_fold.mean(), cross_entropy_errors_by_fold.std() / 2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple sklearn implementation, example usage "learn1.py scikit_testtrain_apple --validation_table=learn1_validation_apple"')
    parser.add_argument('table', help='Name of in and out of class data to read (e.g. scikit_validation_app)')
    #parser.add_argument('--validation_table', help='Table of validation data - get tweets and write predicted class labels back (e.g. learn1_validation_apple)')
    #parser.add_argument('--roc', default=False, action="store_true", help='Plot a Receiver Operating Characterics graph for the learning results')
    #parser.add_argument('--pr', default=False, action="store_true", help='Plot a Precision/Recall graph for the learning results')
    #parser.add_argument('--termmatrix', default=False, action="store_true", help='Draw a 2D matrix of tokens vs binary presence (or absence) using all training documents')
    args = parser.parse_args()

    data_dir = "data"
    in_class_name = os.path.join(data_dir, args.table + '_in_class.csv')
    out_class_name = os.path.join(data_dir, args.table + '_out_class.csv')

    in_class_lines = reader(in_class_name)
    out_class_lines = reader(out_class_name)

    # put all items into the training set
    train_set = np.array(out_class_lines + in_class_lines)
    target = np.array([0] * len(out_class_lines) + [1] * len(in_class_lines))

    # choose a vectorizer to turn the tokens in tweets into a matrix of
    # examples (we can plot this further below using --termmatrix)
    stopWords = stopwords.words('english')
    MIN_DF = 2
    NGRAM_RANGE = (1, 2)
    vectorizer_binary = CountVectorizer(stop_words=stopWords, min_df=MIN_DF, binary=True, ngram_range=NGRAM_RANGE)

    #vectorizer_binary = CountVectorizer(stop_words=stopWords, min_df=MIN_DF, binary=True, ngram_range=(1, 2))
    #vectorizer_binary = CountVectorizer(stop_words=stopWords, min_df=MIN_DF, binary=True, ngram_range=(1, 3))
    vectorizer_tfidf = TfidfVectorizer(stop_words=stopWords, min_df=MIN_DF, ngram_range=NGRAM_RANGE)
    #vectorizer = vectorizer_tfidf
    vectorizer = vectorizer_binary
    print(vectorizer)

    #clf = linear_model.LogisticRegression(penalty='l2', C=1.2)
    _ = linear_model.LogisticRegression()
    _ = svm.LinearSVC()
    _ = naive_bayes.BernoulliNB()  # useful for binary inputs (MultinomialNB is useful for counts)
    _ = naive_bayes.GaussianNB()
    _ = naive_bayes.MultinomialNB()
    _ = ensemble.AdaBoostClassifier(n_estimators=100, base_estimator=tree.DecisionTreeClassifier(max_depth=2, criterion='entropy'))
    #clf = ensemble.AdaBoostClassifier(n_estimators=100, base_estimator=tree.DecisionTreeClassifier(max_depth=2))
    _ = tree.DecisionTreeClassifier(max_depth=50, min_samples_leaf=5)
    #clf = tree.DecisionTreeClassifier(max_depth=2, min_samples_leaf=5, criterion='entropy')
    #clf = ensemble.RandomForestClassifier(max_depth=20, min_samples_leaf=5, n_estimators=10, oob_score=False, n_jobs=-1, criterion='entropy')
    _ = ensemble.RandomForestClassifier(max_depth=10, min_samples_leaf=5, n_estimators=50, n_jobs=-1, criterion='entropy')
    #clf = ensemble.RandomForestClassifier(max_depth=30, min_samples_leaf=5, n_estimators=100, oob_score=True, n_jobs=-1)
    clf = neighbors.KNeighborsClassifier(n_neighbors=11)

    print(clf)

    kf = cross_validation.KFold(n=len(target), n_folds=5, shuffle=True)

    f = plt.figure(1)
    f.clf()

    # try the idea of calculating a cross entropy score per fold
    cross_entropy_errors_test_by_fold = np.zeros(len(kf))
    cross_entropy_errors_train_by_fold = np.zeros(len(kf))

    precisions_by_fold = np.zeros(len(kf))
    # build arrays of all the class 0 and 1 probabilities (matching the class 0
    # and 1 gold tags)
    probabilities_class_0_Y_test_all_folds = np.array([])
    probabilities_class_1_Y_test_all_folds = np.array([])
    # list of all the false positives for later diagnostic
    all_false_positives_zipped = []
    for i, (train_rows, test_rows) in enumerate(kf):
        tweets_train_rows = train_set[train_rows]  # select training rows
        tweets_test_rows = train_set[test_rows]  # select testing rows
        Y_train = target[train_rows]
        Y_test = target[test_rows]
        X_train = vectorizer.fit_transform(tweets_train_rows).toarray()
        X_test = vectorizer.transform(tweets_test_rows).todense()

        clf.fit(X_train, Y_train)
        probas_test_ = clf.predict_proba(X_test)

        predictions_test = clf.predict(X_test)
        # figure out false positive rows from X_test (which is a subset from
        # train_set)
        false_positive_locations = np.where(Y_test - predictions_test == -1)  # 0 (truth) - 1 (prediction) == -1 which is a false positive
        false_positive_tweet_rows = test_rows[np.where(Y_test - predictions_test == -1)]
        false_positive_tweets = train_set[false_positive_tweet_rows]
        bag_of_words_false_positive_tweets = vectorizer.inverse_transform(X_test[false_positive_locations])
        false_positives_zipped = zip(false_positive_tweets, bag_of_words_false_positive_tweets)
        all_false_positives_zipped.append(false_positives_zipped)
        #import pdb; pdb.set_trace()

        # select and concatenate the class 0 and 1 probabilities to their
        # respective arrays for later investigation
        probabilities_class_1_Y_test = probas_test_[np.where(Y_test == 1)]  # get all probabilities for class 1
        nbr_features_X_test = [np.sum(row) for row in X_test[np.where(Y_test == 1)]]
        class_1_labels = plt.scatter(nbr_features_X_test, probabilities_class_1_Y_test[:, 1], c='c', edgecolor='none', label="Class 1")
        probabilities_class_0_Y_test = probas_test_[np.where(Y_test == 0)]  # get all probabilities for class 0
        nbr_features_X_test = [np.sum(row) for row in X_test[np.where(Y_test == 0)]]
        class_0_labels = plt.scatter(nbr_features_X_test, probabilities_class_0_Y_test[:, 1], c='k', edgecolor='none', label="Class 0")

        probas_train_ = clf.predict_proba(X_train)
        # compute cross entropy for all trained and tested items in this fold
        if True:
            cross_entropy_errors_test = cross_entropy_error(Y_test, probas_test_)
            cross_entropy_errors_train = cross_entropy_error(Y_train, probas_train_)
            cross_entropy_errors_test_by_fold[i] = np.average(cross_entropy_errors_test)
            cross_entropy_errors_train_by_fold[i] = np.average(cross_entropy_errors_train)
        precisions_by_fold[i] = precision_score(Y_test, clf.predict(X_test))

        print(len(test_rows))
        probabilities_class_0_Y_test_all_folds = np.concatenate((probabilities_class_0_Y_test_all_folds, probabilities_class_0_Y_test[:, 1]))
        probabilities_class_1_Y_test_all_folds = np.concatenate((probabilities_class_1_Y_test_all_folds, probabilities_class_1_Y_test[:, 1]))

    plt.legend((class_1_labels, class_0_labels), (class_1_labels.get_label(), class_0_labels.get_label()), scatterpoints=2, loc=7)
    plt.xlim(xmin=-1)
    plt.ylim(-0.05, 1.05)
    plt.xlabel('Number of features for example')
    plt.ylabel('Probability of class 1 for example')
    plt.title("{} class probabilities with {} features".format(str(clf.__class__).split('.')[-1][:-2], len(vectorizer.get_feature_names())))
    plt.show()

    # trial of grid search
    #from sklearn.grid_search import GridSearchCV
    #grid_search = GridSearchCV(linear_model.LogisticRegression(), {'C': np.power(10.0, np.arange(-3, 3, step=0.5))}, n_jobs=-1, verbose=1)
    #res=grid_search.fit(X_train, Y_train)
    #res.best_params_

    if isinstance(clf, tree.DecisionTreeClassifier):
        # print the most important features
        feature_importances = zip(clf.feature_importances_, vectorizer.get_feature_names())
        feature_importances.sort(reverse=True)
        print("Most important features:", feature_importances[:10])

        with open("dectree.dot", 'w') as f:
            f = tree.export_graphviz(clf, out_file=f, feature_names=vectorizer.get_feature_names())
        os.system("dot -Tpdf dectree.dot -o dectree.pdf")  # turn dot into PDF for visual
            # diagnosis

    print("Training:")
    show_errors(cross_entropy_errors_train_by_fold)
    print("Testing:")
    show_errors(cross_entropy_errors_test_by_fold)
    print("Precisions:")
    show_errors(precisions_by_fold, method="precision", lower_is_better=False)

########NEW FILE########
__FILENAME__ = learn1_experiments_tfidfproper
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""First simple sklearn classifier"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import os
import numpy as np
from sklearn.metrics import precision_score
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn import linear_model
#from sklearn import svm
from sklearn import cross_validation
from nltk.corpus import stopwords
import unicodecsv


############
# NOTE
# this is a basic LogisticRegression classifier, using 5-fold cross validation
# and a cross entropy error measure (which should nicely fit this binary
# decision classification problem).
# do not trust this code to do anything useful in the real world!
#
# this code creates a TF-IDF model inside a cross validation loop
############


def reader(class_name):
    class_reader = unicodecsv.reader(open(class_name), encoding='utf-8')
    row0 = next(class_reader)
    assert row0 == ["tweet_id", "tweet_text"]
    lines = []
    for tweet_id, tweet_text in class_reader:
        txt = tweet_text.strip()
        if len(txt) > 0:
            lines.append(txt)
    return lines


def cross_entropy_error(Y, probas_):
    # compute Cross Entropy using the Natural Log:
    # ( -tln(y) ) − ( (1−t)ln(1−y) )
    probas_class1 = probas_[:, 1]  # get the class 1 probabilities
    cross_entropy_errors = ((-Y) * (np.log(probas_class1))) - ((1 - Y) * (np.log(1 - probas_class1)))
    return cross_entropy_errors


def show_errors(cross_entropy_errors_by_fold, method="cross entropy", lower_is_better=True):
    print("Cross validation %s errors:" % (method) + str(cross_entropy_errors_by_fold))
    if lower_is_better:
        note = "(lower is better)"
    else:
        note = "(higher is better)"

    print("%s %s: %0.2f (+/- %0.2f)" % (method, note, cross_entropy_errors_by_fold.mean(), cross_entropy_errors_by_fold.std() / 2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple sklearn implementation, example usage "learn1.py scikit_testtrain_apple --validation_table=learn1_validation_apple"')
    parser.add_argument('table', help='Name of in and out of class data to read (e.g. scikit_validation_app)')
    parser.add_argument('--validation_table', help='Table of validation data - get tweets and write predicted class labels back (e.g. learn1_validation_apple)')
    parser.add_argument('--roc', default=False, action="store_true", help='Plot a Receiver Operating Characterics graph for the learning results')
    parser.add_argument('--pr', default=False, action="store_true", help='Plot a Precision/Recall graph for the learning results')
    parser.add_argument('--termmatrix', default=False, action="store_true", help='Draw a 2D matrix of tokens vs binary presence (or absence) using all training documents')
    args = parser.parse_args()

    data_dir = "data"
    in_class_name = os.path.join(data_dir, args.table + '_in_class.csv')
    out_class_name = os.path.join(data_dir, args.table + '_out_class.csv')

    in_class_lines = reader(in_class_name)
    out_class_lines = reader(out_class_name)

    # put all items into the training set
    train_set = np.array(out_class_lines + in_class_lines)
    target = np.array([0] * len(out_class_lines) + [1] * len(in_class_lines))

    # choose a vectorizer to turn the tokens in tweets into a matrix of
    # examples (we can plot this further below using --termmatrix)
    stopWords = stopwords.words('english')
    MIN_DF = 2
    vectorizer_binary = CountVectorizer(stop_words=stopWords, min_df=MIN_DF, binary=True, ngram_range=(1, 3))
    #vectorizer_binary = CountVectorizer(stop_words=stopWords, min_df=MIN_DF, binary=True, ngram_range=(1, 2))
    #vectorizer_binary = CountVectorizer(stop_words=stopWords, min_df=MIN_DF, binary=True, ngram_range=(1, 3))
    vectorizer_tfidf = TfidfVectorizer(stop_words=stopWords, min_df=MIN_DF, ngram_range=(1, 3))#, sublinear_tf=True)
    vectorizer = vectorizer_tfidf
    #vectorizer = vectorizer_binary
    print(vectorizer)

    clf = linear_model.LogisticRegression()
    #clf = svm.LinearSVC()
    #clf = linear_model.LogisticRegression(penalty='l2', C=1.2)

    kf = cross_validation.KFold(n=len(target), n_folds=5, shuffle=True)

    # try the idea of calculating a cross entropy score per fold
    cross_entropy_errors_test_by_fold = np.zeros(len(kf))
    cross_entropy_errors_train_by_fold = np.zeros(len(kf))
    precisions_by_fold = np.zeros(len(kf))
    for i, (train_rows, test_rows) in enumerate(kf):
        tweets_train_rows = train_set[train_rows]  # select training rows
        tweets_test_rows = train_set[test_rows]  # select testing rows
        Y_train = target[train_rows]
        Y_test = target[test_rows]
        X_train = vectorizer.fit_transform(tweets_train_rows).toarray()
        X_test = vectorizer.transform(tweets_test_rows).todense()

        clf.fit(X_train, Y_train)
        probas_test_ = clf.predict_proba(X_test)
        probas_train_ = clf.predict_proba(X_train)
        # compute cross entropy for all trained and tested items in this fold
        cross_entropy_errors_test = cross_entropy_error(Y_test, probas_test_)
        cross_entropy_errors_train = cross_entropy_error(Y_train, probas_train_)
        cross_entropy_errors_test_by_fold[i] = np.average(cross_entropy_errors_test)
        cross_entropy_errors_train_by_fold[i] = np.average(cross_entropy_errors_train)
        precisions_by_fold[i] = precision_score(Y_test, clf.predict(X_test))

    print("Training:")
    show_errors(cross_entropy_errors_train_by_fold)
    print("Testing:")
    show_errors(cross_entropy_errors_test_by_fold)
    print("Precisions:")
    show_errors(precisions_by_fold, method="precision", lower_is_better=False)

########NEW FILE########
__FILENAME__ = make_db_subset
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Copy a set of rows to a new table in sqlite"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import random
import config
import sql_convenience


def copy_data_to_subsets(cls, source_table, nbr_testtrain, testtrain_table, nbr_validation, validation_table, drop, config):
    cursor = config.db_conn.cursor()
    sql = "SELECT * FROM {} WHERE class=={}".format(source_table, cls)
    cursor.execute(sql)
    rows = cursor.fetchall()
    random.shuffle(rows)
    rows_validation = rows[:nbr_validation]
    rows_traintest = rows[nbr_validation:nbr_validation + nbr_testtrain]

    #print(rows_traintest[0][b'tweet_id'])
    #print(rows_validation[0][b'tweet_id'])
    # move this n using sql to a new table

    sql_convenience.create_results_table(config.db_conn, testtrain_table, force_drop_table=drop)
    sql_convenience.create_results_table(config.db_conn, validation_table, force_drop_table=drop)

    for row in rows_traintest:
        sql_convenience.insert_api_response(row[b'tweet_id'], row[b'tweet_text'], "", cls, config.db_conn, testtrain_table)
    for row in rows_validation:
        sql_convenience.insert_api_response(row[b'tweet_id'], row[b'tweet_text'], "", cls, config.db_conn, validation_table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tweet annotator')
    parser.add_argument('source_table')
    parser.add_argument('nbr_testtrain', type=int, help="Number of rows to be copied for testing/training")
    parser.add_argument('testtrain_table')
    parser.add_argument('nbr_validation', type=int, help="Number of rows to be copied for validation")
    parser.add_argument('validation_table')
    parser.add_argument('--drop', default=False, action="store_true", help="If added then testtrain_table and validation_table and dropped before the copies")
    args = parser.parse_args()

    # load all ids for a class (table_name, class)
    cls = 0
    copy_data_to_subsets(cls, args.source_table, args.nbr_testtrain, args.testtrain_table, args.nbr_validation, args.validation_table, args.drop, config)
    cls = 1
    copy_data_to_subsets(cls, args.source_table, args.nbr_testtrain, args.testtrain_table, args.nbr_validation, args.validation_table, False, config)

########NEW FILE########
__FILENAME__ = ner_annotator
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Annotate tweets using OpenCalais"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import config
from ner_apis.opencalais import opencalais_ner
import sql_convenience

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tweet annotator using external NER engine')
    parser.add_argument('keyword', help='Keyword we wish to disambiguate (determines table name and used to filter tweets)')
    parser.add_argument('nerengine', help='NER engine type (only "opencalais" at present)')
    parser.add_argument('--drop', default=False, action="store_true", help='Drops the keyword destination table so we do all annotations again')

    args = parser.parse_args()
    print(args)

    if args.nerengine == "opencalais":
        ner = opencalais_ner.OpenCalaisNER
    else:
        1 / 0

    annotations_table = "annotations_{}".format(args.keyword)
    destination_table = "{}_{}".format(args.nerengine, args.keyword)
    cursor = config.db_conn.cursor()

    if args.drop:
        sql = "DROP TABLE IF EXISTS {}".format(destination_table)
        print("Dropping table: {}".format(sql))
        cursor.execute(sql)
    annotations_table, destination_table = sql_convenience.create_all_tables(args.keyword)

    engine = ner(annotations_table, destination_table)
    engine.annotate_all_messages()

########NEW FILE########
__FILENAME__ = ner_api_caller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# http://www.python.org/dev/peps/pep-0263/
"""Base class to call Named Entity Recognition APIs"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import random
import json
import config
import sql_convenience


class NERAPICaller(object):
    def __init__(self, source_table, destination_table):
        self.source_table = source_table
        self.destination_table = destination_table
        self.brand = "apple"  # the brand we're testing

    def annotate_all_messages(self):
        while True:
            msg = self.get_unannotated_message()
            if msg is not None:
                tweet_id = msg[b'tweet_id']
                tweet_text = msg[b'tweet_text']
                config.logging.info('Asking API for results for "%r"' % (repr(tweet_text)))
                response = self.call_api(tweet_text)
                self.store_raw_response(msg, response)
                if self.is_brand_of(self.brand, tweet_id):
                    cls = sql_convenience.CLASS_IN
                else:
                    cls = sql_convenience.CLASS_OUT
                # assign class to this tweet
                sql_convenience.update_class(tweet_id, self.destination_table, cls)
            else:
                break

    def get_unannotated_message(self):
        """Return 1 not-yet-annotated message from the source_table"""
        cursor = config.db_conn.cursor()
        # select a tweet where the tweet isn't already in the destination_table
        # http://stackoverflow.com/questions/367863/sql-find-records-from-one-table-which-dont-exist-in-another
        sql = "SELECT tweet_id, tweet_text FROM {} WHERE tweet_id NOT IN (SELECT tweet_id FROM {})".format(self.source_table, self.destination_table)
        cursor.execute(sql)
        all_rows = cursor.fetchall()
        # return a random item or None if there are no messages left
        # unannotated
        if len(all_rows) > 0:
            return random.choice(all_rows)
        else:
            return None

    def call_api(self, message):
        """Return a simulated call to an API"""
        return "NERAPICaller base class:{}".format(message)

    def is_brand_of(self, brand, tweet_id):
        """By default we assume all tweets have no brand in this base class"""
        return False

    def store_raw_response(self, source_details, response_text):
        """Store raw response from API provider using source_details"""
        cls = sql_convenience.CLASS_NOT_INVESTIGATED
        json_response = json.dumps(response_text)
        sql_convenience.insert_api_response(source_details[b'tweet_id'], source_details[b'tweet_text'], json_response, cls, config.db_conn, self.destination_table)

########NEW FILE########
__FILENAME__ = calais
"""
python-calais v.1.4 -- Python interface to the OpenCalais API
Author: Jordan Dimov (jdimov@mlke.net)
Last-Update: 01/12/2009
"""

import httplib, urllib, re
import simplejson as json
from StringIO import StringIO

PARAMS_XML = """
<c:params xmlns:c="http://s.opencalais.com/1/pred/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"> <c:processingDirectives %s> </c:processingDirectives> <c:userDirectives %s> </c:userDirectives> <c:externalMetadata %s> </c:externalMetadata> </c:params>
"""

STRIP_RE = re.compile('<script.*?</script>|<noscript.*?</noscript>|<style.*?</style>', re.IGNORECASE)

__version__ = "1.4"

class AppURLopener(urllib.FancyURLopener):
    version = "Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.0.5) Gecko/2008121623 Ubuntu/8.10 (intrepid)Firefox/3.0.5" # Lie shamelessly to Wikipedia.
urllib._urlopener = AppURLopener()

class Calais():
    """
    Python class that knows how to talk to the OpenCalais API.  Use the analyze() and analyze_url() methods, which return CalaisResponse objects.  
    """
    api_key = None
    processing_directives = {"contentType":"TEXT/RAW", "outputFormat":"application/json", "reltagBaseURL":None, "calculateRelevanceScore":"true", "enableMetadataType":None, "discardMetadata":None, "omitOutputtingOriginalText":"true"}
    user_directives = {"allowDistribution":"false", "allowSearch":"false", "externalID":None}
    external_metadata = {}

    def __init__(self, api_key, submitter="python-calais client v.%s" % __version__):
        self.api_key = api_key
        self.user_directives["submitter"]=submitter

    def _get_params_XML(self):
        return PARAMS_XML % (" ".join('c:%s="%s"' % (k,v) for (k,v) in self.processing_directives.items() if v), " ".join('c:%s="%s"' % (k,v) for (k,v) in self.user_directives.items() if v), " ".join('c:%s="%s"' % (k,v) for (k,v) in self.external_metadata.items() if v))

    def rest_POST(self, content):
        params = urllib.urlencode({'licenseID':self.api_key, 'content':content, 'paramsXML':self._get_params_XML()})
        headers = {"Content-type":"application/x-www-form-urlencoded"}
        conn = httplib.HTTPConnection("api.opencalais.com:80")
        conn.request("POST", "/enlighten/rest/", params, headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return (data)

    def get_random_id(self):
        """
        Creates a random 10-character ID for your submission.  
        """
        import string
        from random import choice
        chars = string.letters + string.digits
        np = ""
        for i in range(10):
            np = np + choice(chars)
        return np

    def get_content_id(self, text):
        """
        Creates a SHA1 hash of the text of your submission.  
        """
        import hashlib
        h = hashlib.sha1()
        h.update(text)
        return h.hexdigest()

    def preprocess_html(self, html):
        html = html.replace('\n', '')
        html = STRIP_RE.sub('', html)
        return html

    def analyze(self, content, content_type="TEXT/RAW", external_id=None):
        if not (content and  len(content.strip())):
            return None
        self.processing_directives["contentType"]=content_type
        if external_id:
            self.user_directives["externalID"] = external_id
        return CalaisResponse(self.rest_POST(content))

    def analyze_url(self, url):
        f = urllib.urlopen(url)
        html = self.preprocess_html(f.read())
        return self.analyze(html, content_type="TEXT/HTML", external_id=url)

    def analyze_file(self, fn):
        import mimetypes
        try:
            filetype = mimetypes.guess_type(fn)[0]
        except:
            raise ValueError("Can not determine file type for '%s'" % fn)
        if filetype == "text/plain":
            content_type="TEXT/RAW"
            f = open(fn)
            content = f.read()
            f.close()
        elif filetype == "text/html":
            content_type = "TEXT/HTML"
            f = open(fn)
            content = self.preprocess_html(f.read())
            f.close()
        else:
            raise ValueError("Only plaintext and HTML files are currently supported.  ")
        return self.analyze(content, content_type=content_type, external_id=fn)

class CalaisResponse():
    """
    Encapsulates a parsed Calais response and provides easy pythonic access to the data.
    """
    raw_response = None
    simplified_response = None
    
    def __init__(self, raw_result):
        try:
            self.raw_response = json.load(StringIO(raw_result))
        except:
            raise ValueError(raw_result)
        self.simplified_response = self._simplify_json(self.raw_response)
        self.__dict__['doc'] = self.raw_response['doc']
        for k,v in self.simplified_response.items():
            self.__dict__[k] = v

    def _simplify_json(self, json):
        result = {}
        # First, resolve references
        for element in json.values():
            for k,v in element.items():
                if isinstance(v, unicode) and v.startswith("http://") and json.has_key(v):
                    element[k] = json[v]
        for k, v in json.items():
            if v.has_key("_typeGroup"):
                group = v["_typeGroup"]
                if not result.has_key(group):
                    result[group]=[]
                del v["_typeGroup"]
                v["__reference"] = k
                result[group].append(v)
        return result

    def print_summary(self):
        if not hasattr(self, "doc"):
            return None
        info = self.doc['info']
        print "Calais Request ID: %s" % info['calaisRequestID']
        if info.has_key('externalID'): 
            print "External ID: %s" % info['externalID']
        if info.has_key('docTitle'):
            print "Title: %s " % info['docTitle']
        print "Language: %s" % self.doc['meta']['language']
        print "Extractions: "
        for k,v in self.simplified_response.items():
            print "\t%d %s" % (len(v), k)

    def print_entities(self):
        if not hasattr(self, "entities"):
            return None
        for item in self.entities:
            print "%s: %s (%.2f)" % (item['_type'], item['name'], item['relevance'])

    def print_topics(self):
        if not hasattr(self, "topics"):
            return None
        for topic in self.topics:
            print topic['categoryName']

    def print_relations(self):
        if not hasattr(self, "relations"):
            return None
        for relation in self.relations:
            print relation['_type']
            for k,v in relation.items():
                if not k.startswith("_"):
                    if isinstance(v, unicode):
                        print "\t%s:%s" % (k,v)
                    elif isinstance(v, dict) and v.has_key('name'):
                        print "\t%s:%s" % (k, v['name'])

########NEW FILE########
__FILENAME__ = opencalais_ner
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# http://www.python.org/dev/peps/pep-0263/
"""Call OpenCalais NER"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
from ..ner_api_caller import NERAPICaller
from . import calais
import sql_convenience
import config
from . import opencalais_key  # you need to add a 1 line file containing API_KEY=<key>


class OpenCalaisNER(NERAPICaller):
    def __init__(self, source_table, destination_table):
        super(OpenCalaisNER, self).__init__(source_table, destination_table)
        # Create an OpenCalais object.
        self.api = calais.Calais(opencalais_key.API_KEY, submitter="python-calais demo")

    def call_api(self, message):
        """Return dict of results from an NER call to OpenCalais"""
        message_utf8_string = message.encode('utf-8', 'replace')
        entities = []
        try:
            result = self.api.analyze(message_utf8_string)
            try:
                entities = result.entities
            except AttributeError:
                pass
        except ValueError as err:
            config.logging.error("OpenCalais reports %r" % (repr(err)))
        return entities

    def _get_list_of_companies(self, response):
        """Process response, extract companies"""
        companies = []
        for entity in response:
            if entity['_type'] == 'Company':
                companies.append(entity['name'])
        return companies

    def is_brand_of(self, brand_to_check, tweet_id):
        """Does tweet_id's tweet_text reference brand_to_check as the Company name?"""
        # deserialise_response
        response = sql_convenience.deserialise_response(tweet_id, self.destination_table)
        companies = self._get_list_of_companies(response)
        is_in_list = brand_to_check in set([item.lower() for item in companies])
        return is_in_list

########NEW FILE########
__FILENAME__ = test_opencalais_ner
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""

import unittest
import config
from ner_apis.opencalais import opencalais_ner
import sql_convenience

ENTITIES1 = [
    {'__reference': 'http://d.opencalais.com/comphash-1/705cd5cf-93e1-323c-8d4e-1ea3200d37e4',
     '_type': 'Company',
     '_typeReference': 'http://s.opencalais.com/1/type/em/e/Company',
     'instances': [{'detection': '[and bought some hair gel, then I went to the ]Apple[ store and bought a Macbook Air and an iPod, iPod]',
                    'exact': 'Apple',
                    'length': 5,
                    'offset': 61,
                    'prefix': 'and bought some hair gel, then I went to the ',
                    'suffix': ' store and bought a Macbook Air and an iPod, iPod'}],
     'name': 'Apple',
     'nationality': 'N/A',
     'relevance': 0.629,
     'resolutions': [{'id': 'http://d.opencalais.com/er/company/ralg-tr1r/23d07771-c50b-315b-8050-3cdaf47ac0d0',
                      'name': 'APPLE INC.',
                      'score': 1,
                      'shortname': 'Apple',
                      'symbol': 'AAPL.OQ',
                      'ticker': 'AAPL'}]},
    {'__reference': 'http://d.opencalais.com/genericHasher-1/3a0f3359-b89a-3959-a958-a9141e8c1f9d',
     '_type': 'Product',
     '_typeReference': 'http://s.opencalais.com/1/type/em/e/Product',
     'instances': [{'detection': '[ bought a Macbook Air and an iPod, iPod Touch and ]iPhone[ 4s]',
                    'exact': 'iPhone',
                    'length': 6,
                    'offset': 126,
                    'prefix': ' bought a Macbook Air and an iPod, iPod Touch and ',
                    'suffix': ' 4s'}],
     'name': 'iPhone',
     'producttype': 'Electronics',
     'relevance': 0.629}
]

# MESSAGE1 includes a unicode string that needs encoding for OpenCalais
MESSAGE1 = u"I wish that Apple iPhones were more fun\U0001f34e"

USER1 = {'id': 123, 'name': 'ianozsvald'}
TWEET1 = {'text': MESSAGE1, 'id': 234, 'created_at': "Tue Mar 09 14:01:21 +0000 2010", 'user': USER1}
TWEET1CLASS = 1


class Test(unittest.TestCase):
    def setUp(self):
        self.source_table = "annotations_apple"
        self.destination_table = "api_apple"
        sql_convenience.create_tables(config.db_conn, self.source_table, self.destination_table, force_drop_table=True)
        self.api = opencalais_ner.OpenCalaisNER(self.source_table, self.destination_table)
        self.cursor = config.db_conn.cursor()

    def test_get_list_of_companies(self):
        list_of_companies = self.api._get_list_of_companies(ENTITIES1)
        self.assertEqual(["Apple"], list_of_companies)

    def test_call_api(self):
        entities = self.api.call_api(MESSAGE1)
        self.assertTrue(len(entities) == 1, "We expect 1 (not {}) items".format(len(entities)))
        list_of_companies = self.api._get_list_of_companies(entities)
        self.assertEqual(["Apple"], list_of_companies)
        #import pdb; pdb.set_trace()

    def check_we_have_only_n_record(self, table, nbr_expected):
        sql = "SELECT COUNT(*) FROM {}".format(table)
        self.cursor.execute(sql)
        all_rows = self.cursor.fetchall()
        count = all_rows[0][0]
        self.assertEqual(count, nbr_expected, "Check we have 1 new record (we have {})".format(count))

    def test_full_loop(self):
        """Check that annotate_all_messages processes all messages"""
        # add a tweet to the source_table
        sql_convenience.insert_tweet(TWEET1, TWEET1CLASS, config.db_conn, self.source_table)

        self.check_we_have_only_n_record(self.source_table, 1)
        ## get all tweets from source_table, via annotation, into
        ## destination_table
        self.api.annotate_all_messages()

        self.assertTrue(self.api.is_brand_of('apple', 234))
        self.assertFalse(self.api.is_brand_of('orange', 234))


########NEW FILE########
__FILENAME__ = test_ner_api_caller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""

import unittest
import config
from ner_apis import ner_api_caller
import sql_convenience

        #from nose.tools import set_trace; set_trace()

# simple fixtures
user1 = {'id': 123, 'name': 'ianozsvald'}
tweet1 = {'text': u'example tweet', 'id': 234, 'created_at': "Tue Mar 09 14:01:21 +0000 2010", 'user': user1}
tweet2 = {'text': u'example tweet2', 'id': 235, 'created_at': "Tue Mar 09 14:01:21 +0000 2010", 'user': user1}
tweet3 = {'text': u'example tweet3', 'id': 236, 'created_at': "Tue Mar 09 14:01:21 +0000 2010", 'user': user1}
tweet1class = 0


class Test(unittest.TestCase):
    def setUp(self):
        self.source_table = "annotations_apple"
        self.destination_table = "api_apple"
        sql_convenience.create_tables(config.db_conn, self.source_table, self.destination_table, force_drop_table=True)
        self.ner_api = ner_api_caller.NERAPICaller(self.source_table, self.destination_table)
        self.cursor = config.db_conn.cursor()

    def test1(self):
        """Check we can fetch an unannotated tweet, annotate it and store the result"""
        # check we get a None as we have no messages
        unannotated_message = self.ner_api.get_unannotated_message()
        self.assertEqual(unannotated_message, None)

        # add a tweet to the source_table
        self.insert_tweet(tweet1)
        self.check_we_have_only_n_record(self.source_table, 1)

        # check we get a valid unannotated message
        unannotated_message = self.ner_api.get_unannotated_message()
        self.assertNotEqual(unannotated_message, None)

        #from nose.tools import set_trace; set_trace()
        msg = unannotated_message[str('tweet_text')]
        api_result = self.ner_api.call_api(msg)
        self.assertTrue(api_result.startswith("NERAPICaller base"))

        self.ner_api.store_raw_response(unannotated_message, api_result)
        sql = "SELECT COUNT(*) FROM {}".format(self.destination_table)
        self.cursor.execute(sql)
        all_rows = self.cursor.fetchall()
        #from nose.tools import set_trace; set_trace()
        count = all_rows[0][0]
        self.assertEqual(count, 1, "Check we have 1 new record (we have {})".format(count))

        # check that we cannot store a duplicate item
        self.ner_api.store_raw_response(unannotated_message, api_result)
        sql = "SELECT COUNT(*) FROM {}".format(self.destination_table)
        self.cursor.execute(sql)
        all_rows = self.cursor.fetchall()
        #from nose.tools import set_trace; set_trace()
        count = all_rows[0][0]
        self.assertEqual(count, 1, "Check we have 1 new record (we have {})".format(count))

    def insert_tweet(self, tweet):
        # add a tweet to the source_table
        sql_convenience.insert_tweet(tweet, tweet1class, config.db_conn, self.source_table)

    def check_we_have_only_n_record(self, table, nbr_expected):
        sql = "SELECT COUNT(*) FROM {}".format(table)
        self.cursor.execute(sql)
        all_rows = self.cursor.fetchall()
        count = all_rows[0][0]
        self.assertEqual(count, nbr_expected, "Check we have 1 new record (we have {})".format(count))

    def test2(self):
        """Check that annotate_all_messages does the same job as we've just performed in test1"""
        # add a tweet to the source_table
        self.insert_tweet(tweet1)
        self.check_we_have_only_n_record(self.source_table, 1)
        ## get all tweets from source_table, via annotation, into
        ## destination_table
        self.ner_api.annotate_all_messages()

        sql = "SELECT COUNT(*) FROM {}".format(self.destination_table)
        self.cursor.execute(sql)
        all_rows = self.cursor.fetchall()
        #from nose.tools import set_trace; set_trace()
        count = all_rows[0][0]
        self.assertEqual(count, 1, "Check we have 1 new record (we have {})".format(count))

        self.insert_tweet(tweet2)
        self.insert_tweet(tweet3)
        self.check_we_have_only_n_record(self.source_table, 3)
        ## get all tweets from source_table, via annotation, into
        ## destination_table
        self.ner_api.annotate_all_messages()

        self.check_we_have_only_n_record(self.destination_table, 3)

########NEW FILE########
__FILENAME__ = score_results
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Compare two tables, generate a set of scores"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import sql_convenience

if __name__ == "__main__":
    # gold_std table, comparison_table
    parser = argparse.ArgumentParser(description='Score results against a gold standard')
    parser.add_argument('gold_standard_table', help='Name of the gold standard table (e.g. annotations_apple)')
    parser.add_argument('comparison_table', help='Name of the table we will score against the gold_standard_table (e.g. scikit_apple)')
    args = parser.parse_args()

    # counters for the 4 types of classification
    tp = 0  # True Positives (predicted in class and are actually in class)
    tn = 0  # True Negatives (predicted out of class and are actually out of class)
    fp = 0  # False Positives (predicted in class but are actually out of class)
    fn = 0  # False Negatives (predicted out of class but are actually in class)

    # for each tweet in comparison table, get tweet_id and cls
    classifications_and_tweets = sql_convenience.extract_classifications_and_tweets(args.gold_standard_table)
    for gold_class, tweet_id, tweet in classifications_and_tweets:
        cls, _, _ = sql_convenience.extract_classification_and_tweet(args.comparison_table, tweet_id)
        if gold_class == sql_convenience.CLASS_IN:
            if cls == sql_convenience.CLASS_IN:
                tp += 1
            else:
                assert cls == sql_convenience.CLASS_OUT
                fn += 1
        else:
            assert gold_class == sql_convenience.CLASS_OUT
            if cls == sql_convenience.CLASS_OUT:
                tn += 1
            else:
                assert cls == sql_convenience.CLASS_IN
                fp += 1

    print("True pos {}, False pos {}, True neg {}, False neg {}".format(tp, fp, tn, fn))
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    print("Precision {}, Recall {}".format(precision, recall))

########NEW FILE########
__FILENAME__ = sql_convenience
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# http://www.python.org/dev/peps/pep-0263/
"""Base class to call Named Entity Recognition APIs"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import sqlite3
import datetime
import json
from dateutil import parser as dt_parser
import config

CLASS_OUT = 0  # out-of-class (not what we want to learn)
CLASS_IN = 1  # in-class (what we want to learn)
CLASS_UNKNOWN = 2  # investigated but label not chosen
CLASS_MIXED = 3  # usage has more than 1 class
CLASS_NOT_INVESTIGATED = None  # default before we assign one of 0..3


def create_all_tables(keyword):
    """Entry point to setup tables"""
    annotations_table = "annotations_{}".format(keyword)
    opencalais_table = "opencalais_{}".format(keyword)
    create_tables(config.db_conn, annotations_table, opencalais_table)
    return annotations_table, opencalais_table


def create_results_table(db_conn, table_name, force_drop_table=False):
    cursor = db_conn.cursor()
    if force_drop_table:
        # drop table if we don't need it
        sql = "DROP TABLE IF EXISTS {}".format(table_name)
        cursor.execute(sql)
        db_conn.commit()
    sql = "CREATE TABLE IF NOT EXISTS {} (tweet_id INTEGER UNIQUE, tweet_text TEXT, response_fetched_at DATE, class INT, response TEXT)".format(table_name)
    cursor.execute(sql)
    db_conn.commit()


def create_tables(db_conn, annotations_table, opencalais_table, force_drop_table=False):
    cursor = db_conn.cursor()
    if force_drop_table:
        # drop table if we don't need it
        for table_name in [annotations_table]:
            sql = "DROP TABLE IF EXISTS {}".format(table_name)
            cursor.execute(sql)
        db_conn.commit()

    # Odd - large ints are not displayed correctly in SQLite Manager but they
    # are in sqlite (cmd line and via python)
    # Hah! Bug 3 for SQLite Manager (Firefox) states that the problem is with
    # big integers in JavaScript!
    # https://code.google.com/p/sqlite-manager/issues/detail?can=2&start=0&num=100&q=&colspec=ID%20Type%20Status%20Priority%20Milestone%20Owner%20Summary&groupby=&sort=&id=3
    # so there was nothing wrong with my code. I'm leaving this note here as a
    # reminder to myself. An example large tweet_id int would be 306093154619240448
    sql = "CREATE TABLE IF NOT EXISTS {} (tweet_id INTEGER UNIQUE, tweet_text TEXT, tweet_created_at DATE, class INT, user_id INT, user_name TEXT)".format(annotations_table)
    cursor.execute(sql)
    db_conn.commit()
    #sql = "CREATE TABLE IF NOT EXISTS {} (tweet_id INTEGER UNIQUE, tweet_text TEXT, response_fetched_at DATE, class INT, response TEXT)".format(opencalais_table)
    #cursor.execute(sql)
    create_results_table(db_conn, opencalais_table, force_drop_table)


def extract_classification_and_tweet(table, tweet_id):
    """Return the desired tuple (classification, tweet_id, tweet) in table"""
    cursor = config.db_conn.cursor()
    sql = "SELECT * FROM {} WHERE tweet_id=={}".format(table, tweet_id)
    cursor.execute(sql)
    result = cursor.fetchone()
    return (result[b'class'], result[b'tweet_id'], result[b'tweet_text'])


def extract_classifications_and_tweets(table):
    """Yield list of tuples of (classification, tweet_id, tweet) in table"""
    cursor = config.db_conn.cursor()
    sql = "SELECT * FROM {} ORDER BY tweet_id".format(table)
    cursor.execute(sql)
    results = cursor.fetchall()
    for result in results:
        yield(result[b'class'], result[b'tweet_id'], result[b'tweet_text'])


def check_if_tweet_exists(tweet_id, table):
    """Check if the specified tweet_id exists in our table"""
    cursor = config.db_conn.cursor()
    sql = "SELECT count(*) FROM {} WHERE tweet_id=={}".format(table, tweet_id)
    cursor.execute(sql)
    result = cursor.fetchone()
    count = result[b'count(*)']
    return count


def insert_tweet(tweet, cls, db_conn, annotations_table):
    """Insert tweet into database"""
    tweet_id = tweet['id']
    config.logging.info("Inserting tweet_id '{}'".format(tweet_id))
    tweet_text = unicode(tweet['text'])
    user_id = tweet['user']['id']
    user_name = tweet['user']['name'].lower()
    tweet_created_at = dt_parser.parse(tweet['created_at'])
    insert_tweet_details(tweet_id, tweet_text, tweet_created_at, cls, user_id, user_name, db_conn, annotations_table)


def insert_tweet_details(tweet_id, tweet_text, tweet_created_at, cls, user_id, user_name, db_conn, annotations_table):
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO {}(tweet_id, tweet_text, tweet_created_at, class, user_id, user_name) values (?, ?, ?, ?, ?, ?)".format(annotations_table),
                   (tweet_id, tweet_text, tweet_created_at, cls, user_id, user_name))
    db_conn.commit()


def insert_api_response(tweet_id, tweet_text, response, cls, db_conn, destination_table):
    """Insert api response into database"""
    try:
        response_fetched_at = datetime.datetime.utcnow()
        cursor = config.db_conn.cursor()
        cursor.execute("INSERT INTO {}(tweet_id, tweet_text, response_fetched_at, class, response) values (?, ?, ?, ?, ?)".format(destination_table),
                       (tweet_id, tweet_text, response_fetched_at, cls, response))
        config.db_conn.commit()
    except sqlite3.IntegrityError:
        pass  # ignore duplicate insert errors (as we're expecting to run with >1 process)


def deserialise_response(tweet_id, table):
    """Get serialised response from table, deserialise the JSON"""
    cursor = config.db_conn.cursor()
    sql = "SELECT * FROM {} WHERE tweet_id=={}".format(table, tweet_id)
    cursor.execute(sql)
    result = cursor.fetchone()
    result_dict = json.loads(result[b'response'])
    return result_dict


def update_class(tweet_id, table, cls):
    """Update the class for tweet_id"""
    cursor = config.db_conn.cursor()
    sql = "UPDATE {} SET class={} WHERE tweet_id=={}".format(table, cls, tweet_id)
    cursor.execute(sql)
    config.db_conn.commit()

########NEW FILE########
__FILENAME__ = test_tweet_annotator
#!/usr/bin/env python
"""Tests for start_here"""
# -*- coding: utf-8 -*-
# http://www.python.org/dev/peps/pep-0263/
import unittest
import tweet_annotator
import config
import sql_convenience

# simple fixtures
user1 = {'id': 123, 'name': 'ianozsvald'}
tweet1 = {'text': u'example tweet', 'id': 1, 'created_at': "Tue Mar 09 14:01:21 +0000 2010", 'user': user1}


class Test(unittest.TestCase):
    def setUp(self):
        self.annotations_table = "annotations_apple"
        sql_convenience.create_tables(config.db_conn, self.annotations_table, "table_not_needed_here", force_drop_table=True)

    def test_add_1_annotated_row(self):
        cls = 0
        sql_convenience.insert_tweet(tweet1, cls, config.db_conn, self.annotations_table)

        # now check we have the expected 1 row
        cursor = config.db_conn.cursor()
        sql = "SELECT * FROM {}".format(self.annotations_table)
        cursor.execute(sql)
        all_rows = cursor.fetchall()
        self.assertEqual(len(all_rows), 1, "We expect just 1 row")

        count = tweet_annotator.count_nbr_annotated_rows(config.db_conn, self.annotations_table)
        #from nose.tools import set_trace; set_trace()

        self.assertEqual(count, 1)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = tweet_annotator
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Annotate tweets by hand to create a gold standard"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import config  # assumes env var DISAMBIGUATOR_CONFIG is configured
import tweet_generators
import sql_convenience
import cld  # https://pypi.python.org/pypi/chromium_compact_language_detector


def determine_class(tweet, keyword):
    """Determine which class our tweet belongs to"""
    tweet_text = unicode(tweet['text'])
    GREEN_COLOUR = '\033[92m'
    END_COLOUR = '\033[0m'
    coloured_keyword = GREEN_COLOUR + keyword + END_COLOUR  # colour the keyword green
    #coloured_tweet_text = tweet_text.replace(keyword, coloured_keyword)

    import re
    sub = re.compile(re.escape(keyword), re.IGNORECASE)
    coloured_tweet_text = sub.sub(coloured_keyword, tweet_text)
    print("--------")
    print(tweet_text)
    print(coloured_tweet_text)
    inp = raw_input("0 for out-of-class, {}1 for in-class (i.e. this is the brand){},\n<return> to ignore (e.g. for non-English or irrelevant tweets):".format(GREEN_COLOUR, END_COLOUR))
    cls = sql_convenience.CLASS_UNKNOWN
    if inp.strip() == "0":
        print("out of class")
        cls = sql_convenience.CLASS_OUT
    if inp.strip() == "1":
        print("in class")
        cls = sql_convenience.CLASS_IN
    #print("Put into class", cls)
    return cls


def determine_class_and_insert_tweet(tweet, db_conn, annotations_table, keyword):
    cls = determine_class(tweet, keyword)
    if cls != sql_convenience.CLASS_UNKNOWN:
        sql_convenience.insert_tweet(tweet, cls, db_conn, annotations_table)


def count_nbr_annotated_rows(db_conn, annotations_table):
    cursor = db_conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM {}".format(annotations_table))
    return cursor.fetchone()[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tweet annotator')
    parser.add_argument('tweet_file', help='JSON tweets file for annotation')
    parser.add_argument('keyword', help='Keyword we wish to disambiguate (determines table name and used to filter tweets)')
    parser.add_argument('--skipto', default=None, type=int, help="Skip forwards to this tweet id, continue from the next tweet")
    args = parser.parse_args()
    print("These are our args:")
    print(args)
    print(args.tweet_file, args.keyword)

    annotations_table, spotlight_table = sql_convenience.create_all_tables(args.keyword)
    tweets = tweet_generators.get_tweets(open(args.tweet_file))

    # we can skip through Tweets we've already seen in the same file by
    # specifying a tweet id to jump to
    if args.skipto is not None:
        for tweet in tweets:
            if tweet['id'] == args.skipto:
                break  # continue after this tweet

    for tweet in tweets:
        tweet_text = unicode(tweet['text'])
        annotate = True
        # determine if this is an English tweet or not
        tweet_text_bytesutf8 = tweet_text.encode('utf-8')
        language_name, language_code, is_reliable, text_bytes_found, details = cld.detect(tweet_text_bytesutf8)
        # example: ('SPANISH', 'es', True, 69, [('SPANISH', 'es', 100, 93.45794392523365)])
        print("---")
        print(language_name, language_code, is_reliable)
        if language_code not in set(["en", "un"]):
            annotate = False

        tweet_id = tweet['id']
        if sql_convenience.check_if_tweet_exists(tweet_id, annotations_table) == 0:
            # check our keyword is present as Twitter can provide tweets 'relevant
            # to your keyword' which don't actually contain the keyword (but it
            # might be linked in a t.co title or body text)
            nbr_keywords = tweet_text.lower().count(args.keyword)
            nbr_keywords_hash = tweet_text.lower().count("#" + args.keyword)
            print(nbr_keywords, nbr_keywords_hash)
            if nbr_keywords == nbr_keywords_hash:
                annotate = False
            if annotate:
                determine_class_and_insert_tweet(tweet, config.db_conn, annotations_table, args.keyword)

########NEW FILE########
__FILENAME__ = tweet_generators
#!/usr/bin/env python
"""1 liner to explain this project"""
# -*- coding: utf-8 -*-
import ujson as json
import logging
from dateutil import parser as dt_parser


def get_tweets(tweets):
    """Generator to return entry from valid JSON lines"""
    for tweet in tweets:
        # load with json to validate
        try:
            tw = json.loads(tweet)
            yield tw
        except ValueError as err:
            logging.debug("Odd! We have a ValueError when json.loads(tweet): %r" % repr(err))


#def filter_http(tweets):
    #"""Ignore links with http links (can be useful to ignore spam)"""
    #for tweet in tweets:
        #try:
            #if 'http' not in tweet['text']:
                #yield tweet
        #except KeyError as err:
            #logging.debug("Odd! We have a KeyError: %r" % repr(err))


def get_tweet_body(tweets):
    """Get tweets, ignore ReTweets"""
    for tweet in tweets:
        try:
            if 'text' in tweet:
                if not tweet['text'].startswith('RT'):
                    tweet['created_at'] = dt_parser.parse(tweet['created_at'])
                    yield tweet
        except KeyError as err:
            logging.debug("Odd! We have a KeyError: %r" % repr(err))


def files(file_list):
    """Yield lines from a list of input json data files"""
    for filename in file_list:
        f = open(filename)
        for line in f:
            yield line

########NEW FILE########
__FILENAME__ = visualisations
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""First simple sklearn classifier"""
from __future__ import division  # 1/2 == 0.5, as in Py3
from __future__ import absolute_import  # avoid hiding global modules with locals
from __future__ import print_function  # force use of print("hello")
from __future__ import unicode_literals  # force unadorned strings "" to be unicode without prepending u""
import argparse
import os
import learn1
from matplotlib import pyplot as plt
import Levenshtein  # via https://pypi.python.org/pypi/python-Levenshtein/
from collections import Counter

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simple visualisations of the test/train data')
    parser.add_argument('table', help='Name of in and out of class data to read (e.g. scikit_testtrain_apple)')
    args = parser.parse_args()

    data_dir = "data"
    in_class_name = os.path.join(data_dir, args.table + '_in_class.csv')
    out_class_name = os.path.join(data_dir, args.table + '_out_class.csv')

    in_class_lines = learn1.reader(in_class_name)
    out_class_lines = learn1.reader(out_class_name)

    if True:
        # investigate most frequently repeated tweets in each class
        c_in = Counter(in_class_lines)
        c_out = Counter(out_class_lines)

    # some hard-coded display routines for playing with the data...
    if False:
        plt.figure()
        plt.ion()
        if False:  # histogram of tweet lengths
            lengths_in_class = [len(s) for s in in_class_lines]
            lengths_out_class = [len(s) for s in out_class_lines]
            plt.title("Histogram of tweet lengths for classes in " + args.table)
            plt.xlabel("Bins of tweet lengths")
            plt.ylabel("Counts")
            tweet_lengths = (0, 140)
            filename_pattern = "histogram_tweet_lengths_{}.png"
        # note - tried counting spaces with s.count(" ") but this seems to mirror
        # tweet-length
        if True:  # counting number of capital letters
            lengths_in_class = [Levenshtein.hamming(s, s.lower()) for s in in_class_lines]
            lengths_out_class = [Levenshtein.hamming(s, s.lower()) for s in out_class_lines]
            plt.title("Histogram of number of capitals for classes in " + args.table)
            tweet_lengths = (0, 40)
            filename_pattern = "nbr_capitals_{}.png"
        plt.hist(lengths_in_class, range=tweet_lengths, color="blue", label="in-class", histtype="step")
        plt.hist(lengths_out_class, range=tweet_lengths, color="green", label="out-class", histtype="step")
        UPPER_LEFT = 2
        plt.legend(loc=UPPER_LEFT)
        plt.savefig(filename_pattern.format(args.table))

########NEW FILE########
