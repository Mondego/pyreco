__FILENAME__ = ensemble
""" Amazon Access Challenge Starter Code

This was built using the code of Paul Duan <email@paulduan.com> as a starting
point (thanks to Paul).

It builds ensemble models using the original dataset and a handful of 
extracted features.

Author: Benjamin Solecki <bensolecki@gmail.com>
"""

from __future__ import division

import numpy as np
import pandas as pd
from sklearn.ensemble import (RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier)
from sklearn import (metrics, cross_validation, linear_model, preprocessing)

SEED = 42  # always use a seed for randomized procedures

def save_results(predictions, filename):
    """Given a vector of predictions, save results in CSV format."""
    with open(filename, 'w') as f:
        f.write("id,ACTION\n")
        for i, pred in enumerate(predictions):
            f.write("%d,%f\n" % (i + 1, pred))


"""
Fit models and make predictions.
We'll use one-hot encoding to transform our categorical features
into binary features.
y and X will be numpy array objects.
"""
# === load data in memory === #
print "loading data"
X = pd.read_csv('data/train.csv')
X = X.drop(['ROLE_CODE'], axis=1)
y = X['ACTION']
X = X.drop(['ACTION'], axis=1)
X_test = pd.read_csv('data/test.csv', index_col=0)
X_test = X_test.drop(['ROLE_CODE'], axis=1)
X_test['ACTION'] = 0
y_test = X_test['ACTION']
X_test = X_test.drop(['ACTION'], axis=1)

modelRF =RandomForestClassifier(n_estimators=1999, max_features='sqrt', max_depth=None, min_samples_split=9, compute_importances=True, random_state=SEED)#8803
modelXT =ExtraTreesClassifier(n_estimators=1999, max_features='sqrt', max_depth=None, min_samples_split=8, compute_importances=True, random_state=SEED) #8903
modelGB =GradientBoostingClassifier(n_estimators=50, learning_rate=0.20, max_depth=20, min_samples_split=9, random_state=SEED)  #8749
# 599: 20/90/08
#1999: 24/95/06

X_all = pd.concat([X_test,X], ignore_index=True)

# I want to combine role_title as a subset of role_familia and see if same results
X_all['ROLE_TITLE'] = X_all['ROLE_TITLE'] + (1000 * X_all['ROLE_FAMILY'])
X_all['ROLE_ROLLUPS'] = X_all['ROLE_ROLLUP_1'] + (10000 * X_all['ROLE_ROLLUP_2'])
X_all = X_all.drop(['ROLE_ROLLUP_1','ROLE_ROLLUP_2','ROLE_FAMILY'], axis=1)

# Count/freq
print "Counts"
for col in X_all.columns:
    X_all['cnt'+col] = 0
    groups = X_all.groupby([col])
    for name, group in groups:
        count = group[col].count()
        X_all['cnt'+col].ix[group.index] = count 
    X_all['cnt'+col] = X_all['cnt'+col].apply(np.log) # could check if this is neccesary, I think probably not

# Percent of dept that is this resource
for col in X_all.columns[1:6]:
    X_all['Duse'+col] = 0.0
    groups = X_all.groupby([col])
    for name, group in groups:
        grps = group.groupby(['RESOURCE'])
        for rsrc, grp in grps:
            X_all['Duse'+col].ix[grp.index] = float(len(grp.index)) / float(len(group.index) )

# Number of resources that a manager manages
for col in X_all.columns[0:1]:
    if col == 'MGR_ID':
        continue
    print col
    X_all['Mdeps'+col] = 0
    groups = X_all.groupby(['MGR_ID'])
    for name, group in groups:
        X_all['Mdeps'+col].ix[group.index] = len(group[col].unique()) 


X = X_all[:][X_all.index>=len(X_test.index)]
X_test = X_all[:][X_all.index<len(X_test.index)]

# === Combine Models === #
# Do a linear combination using a cross_validated data split
X_train, X_cv, y_train, y_cv = cross_validation.train_test_split(X, y, test_size=0.5, random_state=SEED)

modelRF.fit(X_cv, y_cv) 
modelXT.fit(X_cv, y_cv) 
modelGB.fit(X_cv, y_cv) 
predsRF = modelRF.predict_proba(X_train)[:, 1]
predsXT = modelXT.predict_proba(X_train)[:, 1]
predsGB = modelGB.predict_proba(X_train)[:, 1]
preds = np.hstack((predsRF, predsXT, predsGB)).reshape(3,len(predsGB)).transpose()
preds[preds>0.9999999]=0.9999999
preds[preds<0.0000001]=0.0000001
preds = -np.log((1-preds)/preds)
modelEN1 = linear_model.LogisticRegression()
modelEN1.fit(preds, y_train)
print modelEN1.coef_

modelRF.fit(X_train, y_train) 
modelXT.fit(X_train, y_train) 
modelGB.fit(X_train, y_train) 
predsRF = modelRF.predict_proba(X_cv)[:, 1]
predsXT = modelXT.predict_proba(X_cv)[:, 1]
predsGB = modelGB.predict_proba(X_cv)[:, 1]
preds = np.hstack((predsRF, predsXT, predsGB)).reshape(3,len(predsGB)).transpose()
preds[preds>0.9999999]=0.9999999
preds[preds<0.0000001]=0.0000001
preds = -np.log((1-preds)/preds)
modelEN2 = linear_model.LogisticRegression()
modelEN2.fit(preds, y_cv)
print modelEN2.coef_

coefRF = modelEN1.coef_[0][0] + modelEN2.coef_[0][0]
coefXT = modelEN1.coef_[0][1] + modelEN2.coef_[0][1]
coefGB = modelEN1.coef_[0][2] + modelEN2.coef_[0][2]

# === Predictions === #
# When making predictions, retrain the model on the whole training set
modelRF.fit(X, y)
modelXT.fit(X, y)
modelGB.fit(X, y)

### Combine here
predsRF = modelRF.predict_proba(X_test)[:, 1]
predsXT = modelXT.predict_proba(X_test)[:, 1]
predsGB = modelGB.predict_proba(X_test)[:, 1]
predsRF[predsRF>0.9999999]=0.9999999
predsXT[predsXT>0.9999999]=0.9999999
predsGB[predsGB>0.9999999]=0.9999999
predsRF[predsRF<0.0000001]=0.0000001
predsXT[predsXT<0.0000001]=0.0000001
predsGB[predsGB<0.0000001]=0.0000001
predsRF = -np.log((1-predsRF)/predsRF)
predsXT = -np.log((1-predsXT)/predsXT)
predsGB = -np.log((1-predsGB)/predsGB)
preds = coefRF * predsRF + coefXT * predsXT + coefGB * predsGB

filename = raw_input("Enter name for submission file: ")
save_results(preds, "submissions/en" + filename + ".csv")

########NEW FILE########
__FILENAME__ = logistic
"""
This program is based on code submitted by Miroslaw Horbal to the Kaggle 
forums, which was itself based on an earlier submission from Paul Doan.
My thanks to both.

Author: Benjamin Solecki <bensolucky@gmail.com>
"""

from numpy import array, hstack
from sklearn import metrics, cross_validation, linear_model
from sklearn import naive_bayes
from sklearn import preprocessing
from scipy import sparse
from itertools import combinations

from sets import Set
import numpy as np
import pandas as pd
import sys

#SEED = 55
SEED = int(sys.argv[2])

def group_data(data, degree=3, hash=hash):
    """ 
    numpy.array -> numpy.array
    
    Groups all columns of data into all combinations of triples
    """
    new_data = []
    m,n = data.shape
    for indicies in combinations(range(n), degree):
	if 5 in indicies and 7 in indicies:
	    print "feature Xd"
	elif 2 in indicies and 3 in indicies:
	    print "feature Xd"
	else:
            new_data.append([hash(tuple(v)) for v in data[:,indicies]])
    return array(new_data).T

def OneHotEncoder(data, keymap=None):
     """
     OneHotEncoder takes data matrix with categorical columns and
     converts it to a sparse binary matrix.
     
     Returns sparse binary matrix and keymap mapping categories to indicies.
     If a keymap is supplied on input it will be used instead of creating one
     and any categories appearing in the data that are not in the keymap are
     ignored
     """
     if keymap is None:
          keymap = []
          for col in data.T:
               uniques = set(list(col))
               keymap.append(dict((key, i) for i, key in enumerate(uniques)))
     total_pts = data.shape[0]
     outdat = []
     for i, col in enumerate(data.T):
          km = keymap[i]
          num_labels = len(km)
          spmat = sparse.lil_matrix((total_pts, num_labels))
          for j, val in enumerate(col):
               if val in km:
                    spmat[j, km[val]] = 1
          outdat.append(spmat)
     outdat = sparse.hstack(outdat).tocsr()
     return outdat, keymap

def create_test_submission(filename, prediction):
    content = ['id,ACTION']
    for i, p in enumerate(prediction):
        content.append('%i,%f' %(i+1,p))
    f = open(filename, 'w')
    f.write('\n'.join(content))
    f.close()
    print 'Saved'

# This loop essentially from Paul's starter code
# I (Ben) increased the size of train at the expense of test, because
# when train is small many features will not be found in train.
def cv_loop(X, y, model, N):
    mean_auc = 0.
    for i in range(N):
        X_train, X_cv, y_train, y_cv = cross_validation.train_test_split(
                                       X, y, test_size=1.0/float(N), 
                                       random_state = i*SEED)
        model.fit(X_train, y_train)
        preds = model.predict_proba(X_cv)[:,1]
        auc = metrics.auc_score(y_cv, preds)
        #print "AUC (fold %d/%d): %f" % (i + 1, N, auc)
        mean_auc += auc
    return mean_auc/N
    
learner = sys.argv[1]
print "Reading dataset..."
train_data = pd.read_csv('train.csv')
test_data = pd.read_csv('test.csv')
submit=learner + str(SEED) + '.csv'
all_data = np.vstack((train_data.ix[:,1:-1], test_data.ix[:,1:-1]))
num_train = np.shape(train_data)[0]

# Transform data
print "Transforming data..."
# Relabel the variable values to smallest possible so that I can use bincount
# on them later.
relabler = preprocessing.LabelEncoder()
for col in range(len(all_data[0,:])):
    relabler.fit(all_data[:, col])
    all_data[:, col] = relabler.transform(all_data[:, col])
########################## 2nd order features ################################
dp = group_data(all_data, degree=2) 
for col in range(len(dp[0,:])):
    relabler.fit(dp[:, col])
    dp[:, col] = relabler.transform(dp[:, col])
    uniques = len(set(dp[:,col]))
    maximum = max(dp[:,col])
    print col
    if maximum < 65534:
        count_map = np.bincount((dp[:, col]).astype('uint16'))
        for n,i in enumerate(dp[:, col]):
            if count_map[i] <= 1:
                dp[n, col] = uniques
            elif count_map[i] == 2:
                dp[n, col] = uniques+1
    else:
        for n,i in enumerate(dp[:, col]):
            if (dp[:, col] == i).sum() <= 1:
                dp[n, col] = uniques
            elif (dp[:, col] == i).sum() == 2:
                dp[n, col] = uniques+1
    print uniques # unique values
    uniques = len(set(dp[:,col]))
    print uniques
    relabler.fit(dp[:, col])
    dp[:, col] = relabler.transform(dp[:, col])
########################## 3rd order features ################################
dt = group_data(all_data, degree=3)
for col in range(len(dt[0,:])):
    relabler.fit(dt[:, col])
    dt[:, col] = relabler.transform(dt[:, col])
    uniques = len(set(dt[:,col]))
    maximum = max(dt[:,col])
    print col
    if maximum < 65534:
        count_map = np.bincount((dt[:, col]).astype('uint16'))
        for n,i in enumerate(dt[:, col]):
            if count_map[i] <= 1:
                dt[n, col] = uniques
            elif count_map[i] == 2:
                dt[n, col] = uniques+1
    else:
        for n,i in enumerate(dt[:, col]):
            if (dt[:, col] == i).sum() <= 1:
                dt[n, col] = uniques
            elif (dt[:, col] == i).sum() == 2:
                dt[n, col] = uniques+1
    print uniques
    uniques = len(set(dt[:,col]))
    print uniques
    relabler.fit(dt[:, col])
    dt[:, col] = relabler.transform(dt[:, col])
########################## 1st order features ################################
for col in range(len(all_data[0,:])):
    relabler.fit(all_data[:, col])
    all_data[:, col] = relabler.transform(all_data[:, col])
    uniques = len(set(all_data[:,col]))
    maximum = max(all_data[:,col])
    print col
    if maximum < 65534:
        count_map = np.bincount((all_data[:, col]).astype('uint16'))
        for n,i in enumerate(all_data[:, col]):
            if count_map[i] <= 1:
                all_data[n, col] = uniques
            elif count_map[i] == 2:
                all_data[n, col] = uniques+1
    else:
        for n,i in enumerate(all_data[:, col]):
            if (all_data[:, col] == i).sum() <= 1:
                all_data[n, col] = uniques
            elif (all_data[:, col] == i).sum() == 2:
                all_data[n, col] = uniques+1
    print uniques
    uniques = len(set(all_data[:,col]))
    print uniques
    relabler.fit(all_data[:, col])
    all_data[:, col] = relabler.transform(all_data[:, col])

# Collect the training features together
y = array(train_data.ACTION)
X = all_data[:num_train]
X_2 = dp[:num_train]
X_3 = dt[:num_train]

# Collect the testing features together
X_test = all_data[num_train:]
X_test_2 = dp[num_train:]
X_test_3 = dt[num_train:]

X_train_all = np.hstack((X, X_2, X_3))
X_test_all = np.hstack((X_test, X_test_2, X_test_3))
num_features = X_train_all.shape[1]
    
if learner == 'NB':
    model = naive_bayes.BernoulliNB(alpha=0.03)
else:
    model = linear_model.LogisticRegression(class_weight='auto', penalty='l2')
    
# Xts holds one hot encodings for each individual feature in memory
# speeding up feature selection 
Xts = [OneHotEncoder(X_train_all[:,[i]])[0] for i in range(num_features)]
    
print "Performing greedy feature selection..."
score_hist = []
N = 10
good_features = set([])
# Greedy feature selection loop
while len(score_hist) < 2 or score_hist[-1][0] > score_hist[-2][0]:
    scores = []
    for f in range(len(Xts)):
        if f not in good_features:
            feats = list(good_features) + [f]
            Xt = sparse.hstack([Xts[j] for j in feats]).tocsr()
            score = cv_loop(Xt, y, model, N)
            scores.append((score, f))
            print "Feature: %i Mean AUC: %f" % (f, score)
    good_features.add(sorted(scores)[-1][1])
    score_hist.append(sorted(scores)[-1])
    print "Current features: %s" % sorted(list(good_features))
    
# Remove last added feature from good_features
good_features.remove(score_hist[-1][1])
good_features = sorted(list(good_features))
print "Selected features %s" % good_features
gf = open("feats" + submit, 'w')
print >>gf, good_features
gf.close()
print len(good_features), " features"
    
print "Performing hyperparameter selection..."
# Hyperparameter selection loop
score_hist = []
Xt = sparse.hstack([Xts[j] for j in good_features]).tocsr()
if learner == 'NB':
    Cvals = [0.001, 0.003, 0.006, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.1]
else:
    Cvals = np.logspace(-4, 4, 15, base=2)  # for logistic
for C in Cvals:
    if learner == 'NB':
        model.alpha = C
    else:
        model.C = C
    score = cv_loop(Xt, y, model, N)
    score_hist.append((score,C))
    print "C: %f Mean AUC: %f" %(C, score)
bestC = sorted(score_hist)[-1][1]
print "Best C value: %f" % (bestC)
    
print "Performing One Hot Encoding on entire dataset..."
Xt = np.vstack((X_train_all[:,good_features], X_test_all[:,good_features]))
Xt, keymap = OneHotEncoder(Xt)
X_train = Xt[:num_train]
X_test = Xt[num_train:]
    
if learner == 'NB':
    model.alpha = bestC
else:
    model.C = bestC

print "Training full model..."
print "Making prediction and saving results..."
model.fit(X_train, y)
preds = model.predict_proba(X_test)[:,1]
create_test_submission(submit, preds)
preds = model.predict_proba(X_train)[:,1]
create_test_submission('Train'+submit, preds)

########NEW FILE########
__FILENAME__ = classifier
#!/usr/bin/env python

"""Amazon Access Challenge

This is my part of the code that produced the winning solution to the
Amazon Employee Access Challenge. See README.md for more details.

Author: Paul Duan <email@paulduan.com>
"""

from __future__ import division

import argparse
import logging

from sklearn import metrics, cross_validation, linear_model, ensemble
from helpers import ml, diagnostics
from helpers.data import load_data, save_results
from helpers.feature_extraction import create_datasets

logging.basicConfig(format="[%(asctime)s] %(levelname)s\t%(message)s",
                    filename="history.log", filemode='a', level=logging.DEBUG,
                    datefmt='%m/%d/%y %H:%M:%S')
formatter = logging.Formatter("[%(asctime)s] %(levelname)s\t%(message)s",
                              datefmt='%m/%d/%y %H:%M:%S')
console = logging.StreamHandler()
console.setFormatter(formatter)
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

logger = logging.getLogger(__name__)


def main(CONFIG):
    """
    The final model is a combination of several base models, which are then
    combined using StackedClassifier defined in the helpers.ml module.

    The list of models and associated datasets is generated automatically
    from their identifying strings. The format is as follows:
    A:b_c where A is the initials of the algorithm to use, b is the base
    dataset, and c is the feature set and the variants to use.
    """
    SEED = 42
    selected_models = [
        "LR:tuples_sf",
        "LR:greedy_sfl",
        "LR:greedy2_sfl",
        "LR:greedy3_sf",
        "RFC:basic_b",
        "RFC:tuples_f",
        "RFC:tuples_fd",
        "RFC:greedy_f",
        "RFC:greedy2_f",
        "GBC:basic_f",
        "GBC:tuples_f",
        "LR:greedy_sbl",
        "GBC:greedy_c",
        "GBC:tuples_cf",
        #"RFC:effects_f",  # experimental; added after the competition
    ]

    # Create the models on the fly
    models = []
    for item in selected_models:
        model_id, dataset = item.split(':')
        model = {'LR': linear_model.LogisticRegression,
                 'GBC': ensemble.GradientBoostingClassifier,
                 'RFC': ensemble.RandomForestClassifier,
                 'ETC': ensemble.ExtraTreesClassifier}[model_id]()
        model.set_params(random_state=SEED)
        models.append((model, dataset))

    datasets = [dataset for model, dataset in models]

    logger.info("loading data")
    y, X = load_data('train.csv')
    X_test = load_data('test.csv', return_labels=False)

    logger.info("preparing datasets (use_cache=%s)", str(CONFIG.use_cache))
    create_datasets(X, X_test, y, datasets, CONFIG.use_cache)

    # Set params
    for model, feature_set in models:
        model.set_params(**ml.find_params(model, feature_set, y,
                                          grid_search=CONFIG.grid_search))
    clf = ml.StackedClassifier(
        models, stack=CONFIG.stack, fwls=CONFIG.fwls,
        model_selection=CONFIG.model_selection,
        use_cached_models=CONFIG.use_cache)

    #  Metrics
    logger.info("computing cv score")
    mean_auc = 0.0
    for i in range(CONFIG.iter):
        train, cv = cross_validation.train_test_split(
            range(len(y)), test_size=.20, random_state=1+i*SEED)
        cv_preds = clf.fit_predict(y, train, cv, show_steps=CONFIG.verbose)

        fpr, tpr, _ = metrics.roc_curve(y[cv], cv_preds)
        roc_auc = metrics.auc(fpr, tpr)
        logger.info("AUC (fold %d/%d): %.5f", i + 1, CONFIG.iter, roc_auc)
        mean_auc += roc_auc

        if CONFIG.diagnostics and i == 0:  # only plot for first fold
            logger.info("plotting learning curve")
            diagnostics.learning_curve(clf, y, train, cv)
            diagnostics.plot_roc(fpr, tpr)
    if CONFIG.iter:
        logger.info("Mean AUC: %.5f",  mean_auc/CONFIG.iter)

    # Create submissions
    if CONFIG.outputfile:
        logger.info("making test submissions (CV AUC: %.4f)", mean_auc)
        preds = clf.fit_predict(y, show_steps=CONFIG.verbose)
        save_results(preds, CONFIG.outputfile + ".csv")

if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(description="Parameters for the script.")
    PARSER.add_argument('-d', "--diagnostics", action="store_true",
                        help="Compute diagnostics.")
    PARSER.add_argument('-i', "--iter", type=int, default=1,
                        help="Number of iterations for averaging.")
    PARSER.add_argument("-f", "--outputfile", default="",
                        help="Name of the file where predictions are saved.")
    PARSER.add_argument('-g', "--grid-search", action="store_true",
                        help="Use grid search to find best parameters.")
    PARSER.add_argument('-m', "--model-selection", action="store_true",
                        default=False, help="Use model selection.")
    PARSER.add_argument('-n', "--no-cache", action="store_false", default=True,
                        help="Use cache.", dest="use_cache")
    PARSER.add_argument("-s", "--stack", action="store_true",
                        help="Use stacking.")
    PARSER.add_argument('-v', "--verbose", action="store_true",
                        help="Show computation steps.")
    PARSER.add_argument("-w", "--fwls", action="store_true",
                        help="Use metafeatures.")
    PARSER.set_defaults(argument_default=False)
    CONFIG = PARSER.parse_args()

    CONFIG.stack = CONFIG.stack or CONFIG.fwls

    logger.debug('\n' + '='*50)
    main(CONFIG)

########NEW FILE########
__FILENAME__ = combine
"""combine.py

This is an ad-hoc script we used to find how to merge our submissions.
For this to work, the prediction vectors must be placed in the internal/
folder.

Author: Paul Duan <email@paulduan.com>
"""

import numpy as np
import math
from sklearn import linear_model, cross_validation, preprocessing

from ..helpers.data import load_data
from ..helpers.ml import compute_auc, AUCRegressor


def inverse_transform(X):
    def clamp(x):
        return min(max(x, .00000001), .99999999)
    return np.vectorize(lambda x: -math.log((1 - clamp(x))/clamp(x)))(X)


def print_param(obj, params, prefix=''):
    for param in params:
        if hasattr(obj, param):
            paramvalue = getattr(obj, param)
            if "coef" in param:
                paramvalue /= np.sum(paramvalue)
            print prefix + param + ": " + str(paramvalue)


mean_prediction = 0.0
y = load_data('train.csv')[0]
y = y[range(len(y) - 7770, len(y))]

files = ["log75", "ens", "paul"]
totransform = []

preds = []
for filename in files:
    with open("%s.csv" % filename) as f:
        pred = np.loadtxt(f, delimiter=',', usecols=[1], skiprows=1)
        if filename in totransform:
            pred = inverse_transform(pred)
        preds.append(pred)
X = np.array(preds).T

standardizer = preprocessing.StandardScaler()
X = standardizer.fit_transform(X)

print "============================================================"
print '\t\t'.join(files)
aucs = []
for filename in files:
    with open("%s.csv" % filename) as f:
        pred = np.loadtxt(f, delimiter=',', usecols=[1], skiprows=1)
        aucs.append("%.3f" % (compute_auc(y, pred) * 100))
print '\t\t'.join(aucs)
print "------------------------------------------------------------"

combiners = [
    linear_model.LinearRegression(),
    linear_model.Ridge(20),
    AUCRegressor(),
]

for combiner in combiners:
    mean_coefs = 0.0
    mean_auc = 0.0
    N = 10

    print "\n%s:" % combiner.__class__.__name__
    if hasattr(combiner, 'predict_proba'):
        combiner.predict = lambda X: combiner.predict_proba(X)[:, 1]

    combiner.fit(X, y)
    print_param(combiner, ["alpha_", "coef_"], "(post) ")
    print "Train AUC: %.3f" % (compute_auc(y, combiner.predict(X)) * 100)

    if isinstance(combiner, AUCRegressor):
        continue

    kfold = cross_validation.KFold(len(y), 3, shuffle=True)
    for train, test in kfold:
        X_train = X[train]
        X_test = X[test]
        y_train = y[train]
        y_test = y[test]

        combiner.fit(X_train, y_train)
        prediction = combiner.predict(X_test)
        mean_auc += compute_auc(y_test, prediction)/len(kfold)

        if len(combiner.coef_) == 1:
            mean_coefs += combiner.coef_[0]/len(files)
        else:
            mean_coefs += combiner.coef_/len(files)

    print "Mean AUC: %.3f" % (mean_auc * 100)

print "\n------------------------------------------------------------"

########NEW FILE########
__FILENAME__ = ben
""" Amazon Access Challenge Starter Code

This was built using the code of Paul Duan <email@paulduan.com> as a starting
point (thanks to Paul).

It builds ensemble models using the original dataset and a handful of
extracted features.

Author: Benjami Solecki <bensolucky@gmail.com>
"""

from __future__ import division

import numpy as np
import pandas as pd
from helpers.data import save_dataset


def create_features():
    print "loading data"
    X = pd.read_csv('data/train.csv')
    X = X.drop(['ROLE_CODE'], axis=1)
    X = X.drop(['ACTION'], axis=1)

    X_test = pd.read_csv('data/test.csv', index_col=0)
    X_test = X_test.drop(['ROLE_CODE'], axis=1)
    X_test['ACTION'] = 0
    X_test = X_test.drop(['ACTION'], axis=1)

    X_all = pd.concat([X_test, X], ignore_index=True)
    # I want to combine role_title as a subset of role_familia and
    X_all['ROLE_TITLE'] = X_all['ROLE_TITLE'] + (1000 * X_all['ROLE_FAMILY'])
    X_all['ROLE_ROLLUPS'] = X_all['ROLE_ROLLUP_1'] + (
        10000 * X_all['ROLE_ROLLUP_2'])
    X_all = X_all.drop(['ROLE_ROLLUP_1', 'ROLE_ROLLUP_2', 'ROLE_FAMILY'],
                       axis=1)

    # Count/freq
    for col in X_all.columns:
        X_all['cnt'+col] = 0
        groups = X_all.groupby([col])
        for name, group in groups:
            count = group[col].count()
            X_all['cnt'+col].ix[group.index] = count
        X_all['cnt'+col] = X_all['cnt'+col].apply(np.log)

    # Percent of dept that is this resource
    # And Counts of dept/resource occurancesa (tested, not used)
    for col in X_all.columns[1:6]:
        X_all['Duse'+col] = 0.0
        groups = X_all.groupby([col])
        for name, group in groups:
            grps = group.groupby(['RESOURCE'])
            for rsrc, grp in grps:
                X_all['Duse'+col].ix[grp.index] = \
                    float(len(grp.index)) / float(len(group.index))

    # Number of resources that a manager manages
    for col in X_all.columns[0:1]:
    #for col in X_all.columns[0:6]:
        if col == 'MGR_ID':
            continue
        X_all['Mdeps'+col] = 0
        groups = X_all.groupby(['MGR_ID'])
        for name, group in groups:
            X_all['Mdeps'+col].ix[group.index] = len(group[col].unique())

    X_all = X_all.drop(X_all.columns[0:6], axis=1)

    # Now X is the train, X_test is test and X_all is both together
    X = X_all[:][X_all.index >= len(X_test.index)]
    X_test = X_all[:][X_all.index < len(X_test.index)]
    # X is the train set alone, X_all is all features
    X = X.as_matrix()
    X_test = X_test.as_matrix()

    save_dataset('bsfeats', X, X_test)

########NEW FILE########
__FILENAME__ = greedy
""" Greedy feature selection
This file is a slightly modified version of Miroslaw's code.
It generates a dataset containing all 3rd order combinations
of the original columns, then performs greedy feature selection.

Original author: Miroslaw Horbal <miroslaw@gmail.com>
Permission was granted by Miroslaw to publish this snippet as part of
our code.
"""

from sklearn import metrics, cross_validation, linear_model
from scipy import sparse
from itertools import combinations
from helpers import data

import numpy as np
import pandas as pd

SEED = 333


def group_data(data, degree=3, hash=hash):
    new_data = []
    m, n = data.shape
    for indices in combinations(range(n), degree):
        new_data.append([hash(tuple(v)) for v in data[:, indices]])
    return np.array(new_data).T


def OneHotEncoder(data, keymap=None):
    """
    OneHotEncoder takes data matrix with categorical columns and
    converts it to a sparse binary matrix.

    Returns sparse binary matrix and keymap mapping categories to indicies.
    If a keymap is supplied on input it will be used instead of creating one
    and any categories appearing in the data that are not in the keymap are
    ignored
    """
    if keymap is None:
        keymap = []
        for col in data.T:
            uniques = set(list(col))
            keymap.append(dict((key, i) for i, key in enumerate(uniques)))
    total_pts = data.shape[0]
    outdat = []
    for i, col in enumerate(data.T):
        km = keymap[i]
        num_labels = len(km)
        spmat = sparse.lil_matrix((total_pts, num_labels))
        for j, val in enumerate(col):
            if val in km:
                spmat[j, km[val]] = 1
        outdat.append(spmat)
    outdat = sparse.hstack(outdat).tocsr()
    return outdat, keymap


def cv_loop(X, y, model, N):
    mean_auc = 0.
    for i in range(N):
        X_train, X_cv, y_train, y_cv = cross_validation.train_test_split(
            X, y, test_size=.20,
            random_state=i*SEED)
        model.fit(X_train, y_train)
        preds = model.predict_proba(X_cv)[:, 1]
        auc = metrics.auc_score(y_cv, preds)
        print "AUC (fold %d/%d): %f" % (i + 1, N, auc)
        mean_auc += auc
    return mean_auc/N


def create_features(train='data/train.csv', test='data/test.csv'):
    print "Reading dataset..."
    train_data = pd.read_csv(train)
    test_data = pd.read_csv(test)
    all_data = np.vstack((train_data.ix[:, 1:-1], test_data.ix[:, 1:-1]))

    num_train = np.shape(train_data)[0]

    # Transform data
    print "Transforming data..."
    dp = group_data(all_data, degree=2)
    dt = group_data(all_data, degree=3)

    y = np.array(train_data.ACTION)
    X = all_data[:num_train]
    X_2 = dp[:num_train]
    X_3 = dt[:num_train]

    X_test = all_data[num_train:]
    X_test_2 = dp[num_train:]
    X_test_3 = dt[num_train:]

    X_train_all = np.hstack((X, X_2, X_3))
    X_test_all = np.hstack((X_test, X_test_2, X_test_3))
    num_features = X_train_all.shape[1]

    model = linear_model.LogisticRegression()

    # Xts holds one hot encodings for each individual feature in memory
    # speeding up feature selection
    Xts = [OneHotEncoder(X_train_all[:, [i]])[0] for i in range(num_features)]

    print "Performing greedy feature selection..."
    score_hist = []
    N = 10
    good_features_list = [
        [0, 8, 9, 10, 19, 34, 36, 37, 38, 41, 42, 43, 47, 53, 55,
         60, 61, 63, 64, 67, 69, 71, 75, 81, 82, 85],
        [0, 1, 7, 8, 9, 10, 36, 37, 38, 41, 42, 43, 47, 51, 53,
         56, 60, 61, 63, 64, 66, 67, 69, 71, 75, 79, 85, 91],
        [0, 7, 9, 24, 36, 37, 41, 42, 47, 53, 61, 63, 64, 67, 69, 71, 75, 85],
        [0, 7, 9, 20, 36, 37, 38, 41, 42, 45, 47,
         53, 60, 63, 64, 67, 69, 71, 81, 85, 86]
    ]

    # Greedy feature selection loop
    if not good_features_list:
        good_features = set([])
        while len(score_hist) < 2 or score_hist[-1][0] > score_hist[-2][0]:
            scores = []
            for f in range(len(Xts)):
                if f not in good_features:
                    feats = list(good_features) + [f]
                    Xt = sparse.hstack([Xts[j] for j in feats]).tocsr()
                    score = cv_loop(Xt, y, model, N)
                    scores.append((score, f))
                    print "Feature: %i Mean AUC: %f" % (f, score)
            good_features.add(sorted(scores)[-1][1])
            score_hist.append(sorted(scores)[-1])
            print "Current features: %s" % sorted(list(good_features))

        # Remove last added feature from good_features
        good_features.remove(score_hist[-1][1])
        good_features = sorted(list(good_features))

    for i, good_features in enumerate(good_features_list):
        suffix = str(i + 1) if i else ''
        Xt = np.vstack((X_train_all[:, good_features],
                        X_test_all[:, good_features]))
        X_train = Xt[:num_train]
        X_test = Xt[num_train:]
        data.save_dataset("greedy%s" % suffix, X_train, X_test)

########NEW FILE########
__FILENAME__ = data
"""ml.py

Useful I/O functions.

Author: Paul Duan <email@paulduan.com>
"""

import logging
import numpy as np
from scipy import sparse
import cPickle as pickle

logger = logging.getLogger(__name__)


def load_data(filename, return_labels=True):
    """Load data from CSV files and return them in numpy format."""
    logging.debug("loading data from %s", filename)
    data = np.loadtxt(open("data/" + filename), delimiter=',',
                      usecols=range(1, 10), skiprows=1, dtype=int)
    if return_labels:
        labels = np.loadtxt(open("data/" + filename), delimiter=',',
                            usecols=[0], skiprows=1)
        return labels, data
    else:
        labels = np.zeros(data.shape[0])
        return data


def load_from_cache(filename, use_cache=True):
    """Attempt to load data from cache."""
    data = None
    read_mode = 'rb' if '.pkl' in filename else 'r'
    if use_cache:
        try:
            with open("cache/%s" % filename, read_mode) as f:
                data = pickle.load(f)
        except IOError:
            pass

    return data


def save_results(predictions, filename):
    """Save results in CSV format."""
    logging.info("saving data to file %s", filename)
    with open("submissions/%s" % filename, 'w') as f:
        f.write("id,ACTION\n")
        for i, pred in enumerate(predictions):
            f.write("%d,%f\n" % (i + 1, pred))


def save_dataset(filename, X, X_test, features=None, features_test=None):
    """Save the training and test sets augmented with the given features."""
    if features is not None:
        assert features.shape[1] == features_test.shape[1], "features mismatch"
        if sparse.issparse(X):
            features = sparse.lil_matrix(features)
            features_test = sparse.lil_matrix(features_test)
            X = sparse.hstack((X, features), 'csr')
            X_test = sparse.hstack((X_test, features_test), 'csr')
        else:
            X = np.hstack((X, features))
            X_test = np. hstack((X_test, features_test))

    logger.info("> saving %s to disk", filename)
    with open("cache/%s.pkl" % filename, 'wb') as f:
        pickle.dump((X, X_test), f, pickle.HIGHEST_PROTOCOL)


def get_dataset(feature_set='basic', train=None, cv=None):
    """
    Return the design matrices constructed with the specified feature set.
    If train is specified, split the training set according to train and
    cv (if cv is not given, subsample's complement will be used instead).
    If subsample is omitted, return both the full training and test sets.
    """
    try:
        with open("cache/%s.pkl" % feature_set, 'rb') as f:
            if train is not None:
                X, _ = pickle.load(f)
                if cv is None:
                    cv = [i for i in range(X.shape[0]) if i not in train]

                X_test = X[cv, :]
                X = X[train, :]
            else:
                X, X_test = pickle.load(f)
    except IOError:
        logging.warning("could not find feature set %s", feature_set)
        return False

    return X, X_test

########NEW FILE########
__FILENAME__ = diagnostics
"""diagnostics.py

Some methods to plot diagnostics.

Author: Paul Duan <email@paulduan.com>
"""

import matplotlib.pyplot as plt
from sklearn.metrics import hinge_loss


def plot_roc(fpr, tpr):
    """Plot ROC curve and display it."""
    plt.clf()
    plt.plot(fpr, tpr)
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.0])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve')


def learning_curve(classifier, y, train, cv, n=15):
    """Plot train and cv loss for increasing train sample sizes."""
    chunk = int(len(y)/n)
    n_samples = []
    train_losses = []
    cv_losses = []
    previous_cache_dir = classifier.cache_dir
    classifier.cache_dir = "diagnostics"

    for i in range(n):
        train_subset = train[:(i + 1)*chunk]
        preds_cv = classifier.fit_predict(y, train_subset, cv,
                                          show_steps=False)
        preds_train = classifier.fit_predict(y, train_subset, train_subset,
                                             show_steps=False)
        n_samples.append((i + 1)*chunk)
        cv_losses.append(hinge_loss(y[cv], preds_cv, neg_label=0))
        train_losses.append(hinge_loss(y[train_subset], preds_train,
                            neg_label=0))

    classifier.cache_dir = previous_cache_dir
    plt.clf()
    plt.plot(n_samples, train_losses, 'r--', n_samples, cv_losses, 'b--')
    plt.ylim([min(train_losses) - .01, max(cv_losses) + .01])

    plt.savefig('plots/learning_curve.png')
    plt.show()

########NEW FILE########
__FILENAME__ = feature_extraction
"""feature_extraction.py

Create the requested datasets.

Author: Paul Duan <email@paulduan.com>
"""

from __future__ import division

import logging
import cPickle as pickle
import numpy as np
import math

from scipy import sparse
from sklearn import preprocessing

from external import greedy, ben
from data import save_dataset
from ml import get_dataset

logger = logging.getLogger(__name__)
subformatter = logging.Formatter("[%(asctime)s] %(levelname)s\t> %(message)s")

COLNAMES = ["resource", "manager", "role1", "role2", "department",
            "title", "family_desc", "family"]
SELECTED_COLUMNS = [0, 1, 4, 5, 6, 7]

EXTERNAL_DATASETS = {
    "greedy": greedy,
    "greedy2": greedy,
    "greedy3": greedy,
    "bsfeats": ben
}


def sparsify(X, X_test):
    """Return One-Hot encoded datasets."""
    enc = OneHotEncoder()
    enc.fit(np.vstack((X, X_test)))
    return enc.transform(X), enc.transform(X_test)


def create_datasets(X, X_test, y, datasets=[], use_cache=True):
    """
    Generate datasets as needed with different sets of features
    and save them to disk.
    The datasets are created by combining a base feature set (combinations of
    the original variables) with extracted feature sets, with some additional
    variants.

    The nomenclature is as follows:
    Base datasets:
        - basic: the original columns, minus role1, role2, and role_code
        - tuples: all order 2 combinations of the original columns
        - triples: all order 3 combinations of the original columns
        - greedy[1,2,3]: three different datasets obtained by performing
            greedy feature selection with different seeds on the triples
            dataset
        - effects: experimental. Created to try out a suggestion by Gxav
            after the competition

    Feature sets and variants:
    (denoted by the letters after the underscore in the base dataset name):
        - s: the base dataset has been sparsified using One-Hot encoding
        - c: the rare features have been consolidated into one category
        - f: extracted features have been appended, with a different set for
            linear models than for tree-based models
        - b: Benjamin's extracted features.
        - d: interactions for the extracted feature set have been added
        - l: the extracted features have been log transformed
    """
    if use_cache:
        # Check if all files exist. If not, generate the missing ones
        DATASETS = []
        for dataset in datasets:
            try:
                with open("cache/%s.pkl" % dataset, 'rb'):
                    pass
            except IOError:
                logger.warning("couldn't load dataset %s, will generate it",
                               dataset)
                DATASETS.append(dataset.split('_')[0])
    else:
        DATASETS = ["basic", "tuples", "triples",
                    "greedy", "greedy2", "greedy3"]

    # Datasets that require external code to be generated
    for dataset, module in EXTERNAL_DATASETS.iteritems():
        if not get_dataset(dataset):
            module.create_features()

    # Generate the missing datasets
    if len(DATASETS):
        bsfeats, bsfeats_test = get_dataset('bsfeats')

        basefeats, basefeats_test = create_features(X, X_test, 3)
        save_dataset("base_feats", basefeats, basefeats_test)

        lrfeats, lrfeats_test = pre_process(*create_features(X, X_test, 0))
        save_dataset("lrfeats", lrfeats, lrfeats_test)

        feats, feats_test = pre_process(*create_features(X, X_test, 1))
        save_dataset("features", feats, feats_test)

        meta, meta_test = pre_process(*create_features(X, X_test, 2),
                                      normalize=False)
        save_dataset("metafeatures", meta, meta_test)

        X = X[:, SELECTED_COLUMNS]
        X_test = X_test[:, SELECTED_COLUMNS]
        save_dataset("basic", X, X_test)

        Xt = create_tuples(X)
        Xt_test = create_tuples(X_test)
        save_dataset("tuples", Xt, Xt_test)

        Xtr = create_tuples(X)
        Xtr_test = create_tuples(X_test)
        save_dataset("triples", Xtr, Xtr_test)

        Xe, Xe_test = create_effects(X, X_test, y)
        save_dataset("effects", Xe, Xe_test)

        feats_d, feats_d_test = pre_process(basefeats, basefeats_test,
                                            create_divs=True)
        bsfeats_d, bsfeats_d_test = pre_process(bsfeats, bsfeats_test,
                                                create_divs=True)
        feats_l, feats_l_test = pre_process(basefeats, basefeats_test,
                                            log_transform=True)
        lrfeats_l, lrfeats_l_test = pre_process(lrfeats, lrfeats_test,
                                                log_transform=True)
        bsfeats_l, bsfeats_l_test = pre_process(bsfeats, bsfeats_test,
                                                log_transform=True)

        for ds in DATASETS:
            Xg, Xg_test = get_dataset(ds)
            save_dataset(ds + '_b', Xg, Xg_test, bsfeats, bsfeats_test)
            save_dataset(ds + '_f', Xg, Xg_test, feats, feats_test)
            save_dataset(ds + '_fd', Xg, Xg_test, feats_d, feats_d_test)
            save_dataset(ds + '_bd', Xg, Xg_test, bsfeats_d, bsfeats_d_test)
            Xs, Xs_test = sparsify(Xg, Xg_test)
            save_dataset(ds + '_sf', Xs, Xs_test, lrfeats, lrfeats_test)
            save_dataset(ds + '_sfl', Xs, Xs_test, lrfeats_l, lrfeats_l_test)
            save_dataset(ds + '_sfd', Xs, Xs_test, feats_d, feats_d_test)
            save_dataset(ds + '_sb', Xs, Xs_test, bsfeats, bsfeats_test)
            save_dataset(ds + '_sbl', Xs, Xs_test, bsfeats_l, bsfeats_l_test)
            save_dataset(ds + '_sbd', Xs, Xs_test, bsfeats_d, bsfeats_d_test)

            if issubclass(Xg.dtype.type, np.integer):
                consolidate(Xg, Xg_test)
                save_dataset(ds + '_c', Xg, Xg_test)
                save_dataset(ds + '_cf', Xg, Xg_test, feats, feats_test)
                save_dataset(ds + '_cb', Xg, Xg_test, bsfeats, bsfeats_test)
                Xs, Xs_test = sparsify(Xg, Xg_test)
                save_dataset(ds + '_sc', Xs, Xs_test)
                save_dataset(ds + '_scf', Xs, Xs_test, feats, feats_test)
                save_dataset(ds + '_scfl', Xs, Xs_test, feats_l, feats_l_test)
                save_dataset(ds + '_scb', Xs, Xs_test, bsfeats, bsfeats_test)
                save_dataset(ds + '_scbl', Xs, Xs_test,
                             bsfeats_l, bsfeats_l_test)


def create_effects(X_train, X_test, y):
    """
    Create a dataset where the features are the effects of a
    logistic regression trained on sparsified data.
    This has been added post-deadline after talking with Gxav.
    """
    from sklearn import linear_model, cross_validation
    from itertools import izip
    Xe_train = np.zeros(X_train.shape)
    Xe_test = np.zeros(X_test.shape)
    n_cols = Xe_train.shape[1]

    model = linear_model.LogisticRegression(C=2)
    X_train, X_test = sparsify(X_train, X_test)

    kfold = cross_validation.KFold(len(y), 5)
    for train, cv in kfold:
        model.fit(X_train[train], y[train])
        colindices = X_test.nonzero()[1]
        for i, k in izip(cv, range(len(cv))):
            for j in range(n_cols):
                z = colindices[n_cols*k + j]
                Xe_train[i, j] = model.coef_[0, z]

    model.fit(X_train, y)
    colindices = X_test.nonzero()[1]
    for i in range(Xe_test.shape[0]):
        for j in range(n_cols):
            z = colindices[n_cols*i + j]
            Xe_test[i, j] = model.coef_[0, z]

    return Xe_train, Xe_test


def create_features(X_train, X_test, feature_set=0):
    """
    Extract features from the training and test set.
    Each feature set is defined as a list of lambda functions.
    """
    logger.info("performing feature extraction (feature_set=%d)", feature_set)
    features_train = []
    features_test = []
    dictionaries = get_pivottable(X_train, X_test)
    dictionaries_train = get_pivottable(X_train, X_test, use='train')
    dictionaries_test = get_pivottable(X_test, X_test, use='test')

    # 0: resource, 1: manager, 2: role1, 3: role2, 4: department,
    # 5: title, 6: family_desc, 7: family
    feature_lists = [
        [  # 0: LR features
            lambda x, row, j:
            x[COLNAMES[0]].get(row[0], 0) if j > 0 and j < 7 else 0,
            lambda x, row, j:
            x[COLNAMES[1]].get(row[1], 0) if j > 1 and j < 7 else 0,
            lambda x, row, j:
            x[COLNAMES[2]].get(row[2], 0) if j > 2 and j < 7 else 0,
            lambda x, row, j:
            x[COLNAMES[3]].get(row[3], 0) if j > 3 and j < 7 else 0,
            lambda x, row, j:
            x[COLNAMES[4]].get(row[4], 0) if j > 4 and j < 7 else 0,
            lambda x, row, j:
            x[COLNAMES[5]].get(row[5], 0) if j > 5 and j < 7 else 0,
            lambda x, row, j:
            x[COLNAMES[6]].get(row[6], 0) if j > 6 and j < 7 else 0,
            lambda x, row, j:
            x[COLNAMES[7]].get(row[7], 0) if j > 7 and j < 7 else 0,

            lambda x, row, j:
            x[COLNAMES[0]].get(row[0], 0)**2 if j in range(7) else 0,
            lambda x, row, j:
            x[COLNAMES[j]].get(row[0], 0)/x['total']
            if j > 0 and j < 7 else 0,

            lambda x, row, j:
            x[COLNAMES[j]].get(row[j], 0)/len(x[COLNAMES[j]].values()),

            lambda x, row, j:
            x[COLNAMES[j]].get(row[j], 0) / dictionaries[j]['total'],

            lambda x, row, j:
            math.log(x[COLNAMES[0]].get(row[0], 0)) if j in range(5) else 0,

            lambda x, row, j:
            int(row[j] not in dictionaries_train[j]),

            lambda x, row, j:
            int(row[j] not in dictionaries_test[j]),
        ],

        [  # 1: Tree features
            lambda x, row, j:
            x[COLNAMES[0]].get(row[0], 0),
            lambda x, row, j:
            x[COLNAMES[1]].get(row[1], 0),
            lambda x, row, j:
            x[COLNAMES[2]].get(row[2], 0),
            lambda x, row, j:
            x[COLNAMES[3]].get(row[3], 0),
            lambda x, row, j:
            x[COLNAMES[4]].get(row[4], 0),
            lambda x, row, j:
            x[COLNAMES[5]].get(row[5], 0),
            lambda x, row, j:
            x[COLNAMES[6]].get(row[6], 0),
            lambda x, row, j:
            x[COLNAMES[7]].get(row[7], 0),

            lambda x, row, j:
            x[COLNAMES[j]].get(row[0], 0)/x['total'] if j > 0 else 0,
        ],

        [  # 2: Metafeatures
            lambda x, row, j:
            dictionaries_train[j].get(row[j], {}).get('total', 0),
            lambda x, row, j:
            dictionaries_train[j].get(row[j], {}).get('total', 0) == 0,
        ],

        [  # 3: Base features
            lambda x, row, j:
            x['total'] if j == 0 else 0,

            lambda x, row, j:
            x[COLNAMES[0]].get(row[0], 0) if j > 0 else 0,
            lambda x, row, j:
            x[COLNAMES[1]].get(row[1], 0) if j > 1 else 0,
            lambda x, row, j:
            x[COLNAMES[2]].get(row[2], 0) if j > 2 else 0,
            lambda x, row, j:
            x[COLNAMES[3]].get(row[3], 0) if j > 3 else 0,
            lambda x, row, j:
            x[COLNAMES[4]].get(row[4], 0) if j > 4 else 0,
            lambda x, row, j:
            x[COLNAMES[5]].get(row[5], 0) if j > 5 else 0,
            lambda x, row, j:
            x[COLNAMES[6]].get(row[6], 0) if j > 6 else 0,
            lambda x, row, j:
            x[COLNAMES[7]].get(row[7], 0) if j > 7 else 0,

            lambda x, row, j:
            x[COLNAMES[0]].get(row[0], 0)**2 if j in range(8) else 0,
        ],
    ]

    feature_generator = feature_lists[feature_set]

    # create feature vectors
    logger.debug("creating feature vectors")
    features_train = []
    for row in X_train:
        features_train.append([])
        for j in range(len(COLNAMES)):
            for feature in feature_generator:
                feature_row = feature(dictionaries[j][row[j]], row, j)
                features_train[-1].append(feature_row)
    features_train = np.array(features_train)

    features_test = []
    for row in X_test:
        features_test.append([])
        for j in range(len(COLNAMES)):
            for feature in feature_generator:
                feature_row = feature(dictionaries[j][row[j]], row, j)
                features_test[-1].append(feature_row)
    features_test = np.array(features_test)

    return features_train, features_test


def pre_process(features_train, features_test,
                create_divs=False, log_transform=False, normalize=True):
    """
    Take lists of feature columns as input, pre-process them (eventually
    performing some transformation), then return nicely formatted numpy arrays.
    """
    logger.info("performing preprocessing")

    features_train = list(features_train.T)
    features_test = list(features_test.T)
    features_train = [list(feature) for feature in features_train]
    features_test = [list(feature) for feature in features_test]

    # remove constant features
    for i in range(len(features_train) - 1, -1, -1):
        if np.var(features_train[i]) + np.var(features_test[i]) == 0:
            features_train.pop(i)
            features_test.pop(i)
    n_features = len(features_train)

    # create some polynomial features
    if create_divs:
        for i in range(n_features):
            for j in range(1):
                features_train.append([round(a/(b + 1), 3) for a, b in zip(
                    features_train[i], features_train[j])])
                features_test.append([round(a/(b + 1), 3) for a, b in zip(
                    features_test[i], features_test[j])])

                features_train.append([round(a/(b + 1), 3) for a, b in zip(
                    features_train[j], features_train[i])])
                features_test.append([round(a/(b + 1), 3) for a, b in zip(
                    features_test[j], features_test[i])])

                features_train.append([a*b for a, b in zip(
                    features_train[j], features_train[i])])
                features_test.append([a*b for a, b in zip(
                    features_test[j], features_test[i])])

    if log_transform:
        tmp_train = []
        tmp_test = []
        for i in range(n_features):
            tmp_train.append([math.log(a + 1) if (a + 1) > 0 else 0
                             for a in features_train[i]])
            tmp_test.append([math.log(a + 1) if (a + 1) > 0 else 0
                             for a in features_test[i]])

            tmp_train.append([a**2 for a in features_train[i]])
            tmp_test.append([a**2 for a in features_test[i]])
            tmp_train.append([a**3 for a in features_train[i]])
            tmp_test.append([a**3 for a in features_test[i]])
        features_train = tmp_train
        features_test = tmp_test

    logger.info("created %d features", len(features_train))
    features_train = np.array(features_train).T
    features_test = np.array(features_test).T

    # normalize the new features
    if normalize:
        normalizer = preprocessing.StandardScaler()
        normalizer.fit(features_train)
        features_train = normalizer.transform(features_train)
        features_test = normalizer.transform(features_test)

    return features_train, features_test


def get_pivottable(X_train, X_test, use='all'):
    """
    Returns a list of dictionaries, one per feature in the
    basic data, containing cross-tabulated counts
    for each column and each value of the feature.
    """
    dictionaries = []
    if use == 'all':
        X = np.vstack((X_train, X_test))
        filename = "pivottable"
    elif use == 'train':
        X = X_train
        filename = "pivottable_train"
    else:
        X = X_test
        filename = "pivottable_test"

    for i in range(len(COLNAMES)):
        dictionaries.append({'total': 0})

    try:
        with open("cache/%s.pkl" % filename, 'rb') as f:
            logger.debug("loading cross-tabulated data from cache")
            dictionaries = pickle.load(f)
    except IOError:
        logger.debug("no cache found, cross-tabulating data")
        for i, row in enumerate(X):
            for j in range(len(COLNAMES)):
                dictionaries[j]['total'] += 1
                if row[j] not in dictionaries[j]:
                    dictionaries[j][row[j]] = {'total': 1}
                    for k, key in enumerate(COLNAMES):
                        dictionaries[j][row[j]][key] = {row[k]: 1}
                else:
                    dictionaries[j][row[j]]['total'] += 1
                    for k, key in enumerate(COLNAMES):
                        if row[k] not in dictionaries[j][row[j]][key]:
                            dictionaries[j][row[j]][key][row[k]] = 1
                        else:
                            dictionaries[j][row[j]][key][row[k]] += 1
        with open("cache/%s.pkl" % filename, 'wb') as f:
            pickle.dump(dictionaries, f, pickle.HIGHEST_PROTOCOL)

    return dictionaries


def create_tuples(X):
    logger.debug("creating feature tuples")
    cols = []
    for i in range(X.shape[1]):
        for j in range(i, X.shape[1]):
            cols.append(X[:, i] + X[:, j]*3571)
    return np.hstack((X, np.vstack(cols).T))


def create_triples(X):
    logger.debug("creating feature triples")
    cols = []
    for i in range(X.shape[1]):
        for j in range(i, X.shape[1]):
            for k in range(j, X.shape[1]):
                cols.append(X[:, i]*3461 + X[:, j]*5483 + X[:, k])
    return np.hstack((X, np.vstack(cols).T))


def consolidate(X_train, X_test):
    """
    Transform in-place the given dataset by consolidating
    rare features into a single category.
    """
    X = np.vstack((X_train, X_test))
    relabeler = preprocessing.LabelEncoder()

    for j in range(X.shape[1]):
        relabeler.fit(X[:, j])
        X[:, j] = relabeler.transform(X[:, j])
        X_train[:, j] = relabeler.transform(X_train[:, j])
        X_test[:, j] = relabeler.transform(X_test[:, j])

        raw_counts = np.bincount(X[:, j])
        indices = np.nonzero(raw_counts)[0]
        counts = dict((x, raw_counts[x]) for x in indices)
        max_value = np.max(X[:, j])

        for i in range(X_train.shape[0]):
            if counts[X_train[i, j]] <= 1:
                X_train[i, j] = max_value + 1

        for i in range(X_test.shape[0]):
            if counts[X_test[i, j]] <= 1:
                X_test[i, j] = max_value + 1


class OneHotEncoder():
    """
    OneHotEncoder takes data matrix with categorical columns and
    converts it to a sparse binary matrix.
    """
    def __init__(self):
        self.keymap = None

    def fit(self, X):
        self.keymap = []
        for col in X.T:
            uniques = set(list(col))
            self.keymap.append(dict((key, i) for i, key in enumerate(uniques)))

    def transform(self, X):
        if self.keymap is None:
            self.fit(X)

        outdat = []
        for i, col in enumerate(X.T):
            km = self.keymap[i]
            num_labels = len(km)
            spmat = sparse.lil_matrix((X.shape[0], num_labels))
            for j, val in enumerate(col):
                if val in km:
                    spmat[j, km[val]] = 1
            outdat.append(spmat)
        outdat = sparse.hstack(outdat).tocsr()
        return outdat

########NEW FILE########
__FILENAME__ = ml
"""ml.py

This is the file that does the heavy lifting.
It contains the ML algorithms themselves:
    - AUCRegressor: a custom class that optimizes AUC directly
    - MLR: a linear regression with non-negativity constraints
    - StackedClassifier: a custom class that combines several models

And some related functions:
    - find_params: sets the hyperparameters for a given model

Author: Paul Duan <email@paulduan.com>
"""

from __future__ import division

import cPickle as pickle
import itertools
import json
import logging
import multiprocessing
import scipy as sp
import numpy as np

from functools import partial
from operator import itemgetter

from sklearn.metrics import roc_curve, auc
from sklearn.grid_search import GridSearchCV
from sklearn import cross_validation, linear_model

from data import load_from_cache, get_dataset
from utils import stringify, compute_auc

logger = logging.getLogger(__name__)

N_TREES = 500

INITIAL_PARAMS = {
    'LogisticRegression': {'C': 2, 'penalty': 'l2', 'class_weight': 'auto'},
    'RandomForestClassifier': {
        'n_estimators': N_TREES, 'n_jobs': 4,
        'min_samples_leaf': 2, 'bootstrap': False,
        'max_depth': 30, 'min_samples_split': 5, 'max_features': .1
    },
    'ExtraTreesClassifier': {
        'n_estimators': N_TREES, 'n_jobs': 3, 'min_samples_leaf': 2,
        'max_depth': 30, 'min_samples_split': 5, 'max_features': .1,
        'bootstrap': False,
    },
    'GradientBoostingClassifier': {
        'n_estimators': N_TREES, 'learning_rate': .08, 'max_features': 7,
        'min_samples_leaf': 1, 'min_samples_split': 3, 'max_depth': 5,
    },
}

PARAM_GRID = {
    'LogisticRegression': {'C': [1.5, 2, 2.5, 3, 3.5, 5, 5.5],
                           'class_weight': ['auto']},
    'RandomForestClassifier': {
        'n_jobs': [1], 'max_depth': [15, 20, 25, 30, 35, None],
        'min_samples_split': [1, 3, 5, 7],
        'max_features': [3, 8, 11, 15],
    },
    'ExtraTreesClassifier': {'min_samples_leaf': [2, 3],
                             'n_jobs': [1],
                             'min_samples_split': [1, 2, 5],
                             'bootstrap': [False],
                             'max_depth': [15, 20, 25, 30],
                             'max_features': [1, 3, 5, 11]},
    'GradientBoostingClassifier': {'max_features': [4, 5, 6, 7],
                                   'learning_rate': [.05, .08, .1],
                                   'max_depth': [8, 10, 13]},
}


class AUCRegressor(object):
    def __init__(self):
        self.coef_ = 0

    def _auc_loss(self, coef, X, y):
        fpr, tpr, _ = roc_curve(y, sp.dot(X, coef))
        return -auc(fpr, tpr)

    def fit(self, X, y):
        lr = linear_model.LinearRegression()
        auc_partial = partial(self._auc_loss, X=X, y=y)
        initial_coef = lr.fit(X, y).coef_
        self.coef_ = sp.optimize.fmin(auc_partial, initial_coef)

    def predict(self, X):
        return sp.dot(X, self.coef_)

    def score(self, X, y):
        fpr, tpr, _ = roc_curve(y, sp.dot(X, self.coef_))
        return auc(fpr, tpr)


class MLR(object):
    def __init__(self):
        self.coef_ = 0

    def fit(self, X, y):
        self.coef_ = sp.optimize.nnls(X, y)[0]
        self.coef_ = np.array(map(lambda x: x/sum(self.coef_), self.coef_))

    def predict(self, X):
        predictions = np.array(map(sum, self.coef_ * X))
        return predictions

    def score(self, X, y):
        fpr, tpr, _ = roc_curve(y, sp.dot(X, self.coef_))
        return auc(fpr, tpr)


class StackedClassifier(object):
    """
    Implement stacking to combine several models.
    The base (stage 0) models can be either combined through
    simple averaging (fastest), or combined using a stage 1 generalizer
    (requires computing CV predictions on the train set).

    See http://ijcai.org/Past%20Proceedings/IJCAI-97-VOL2/PDF/011.pdf:
    "Stacked generalization: when does it work?", Ting and Witten, 1997

    For speed and convenience, both fitting and prediction are done
    in the same method fit_predict; this is done in order to enable
    one to compute metrics on the predictions after training each model without
    having to wait for all the models to be trained.

    Options:
    ------------------------------
    - models: a list of (model, dataset) tuples that represent stage 0 models
    - generalizer: an Estimator object. Must implement fit and predict
    - model_selection: boolean. Whether to use brute force search to find the
        optimal subset of models that produce the best AUC.
    """
    def __init__(self, models, generalizer=None, model_selection=True,
                 stack=False, fwls=False, use_cached_models=True):
        self.cache_dir = "main"
        self.models = models
        self.model_selection = model_selection
        self.stack = stack
        self.fwls = fwls
        self.generalizer = linear_model.RidgeCV(
            alphas=np.linspace(0, 200), cv=100)
        self.use_cached_models = use_cached_models

    def _combine_preds(self, X_train, X_cv, y, train=None, predict=None,
                       stack=False, fwls=False):
        """
        Combine preds, returning in order:
            - mean_preds: the simple average of all model predictions
            - stack_preds: the predictions of the stage 1 generalizer
            - fwls_preds: same as stack_preds, but optionally using more
                complex blending schemes (meta-features, different
                generalizers, etc.)
        """
        mean_preds = np.mean(X_cv, axis=1)
        stack_preds = None
        fwls_preds = None

        if stack:
            self.generalizer.fit(X_train, y)
            stack_preds = self.generalizer.predict(X_cv)

        if self.fwls:
            meta, meta_cv = get_dataset('metafeatures', train, predict)
            fwls_train = np.hstack((X_train, meta))
            fwls_cv = np.hstack((X_cv, meta))
            self.generalizer.fit(fwls_train)
            fwls_preds = self.generalizer.predict(fwls_cv)

        return mean_preds, stack_preds, fwls_preds

    def _find_best_subset(self, y, predictions_list):
        """Finds the combination of models that produce the best AUC."""
        best_subset_indices = range(len(predictions_list))

        pool = multiprocessing.Pool(processes=4)
        partial_compute_subset_auc = partial(compute_subset_auc,
                                             pred_set=predictions_list, y=y)
        best_auc = 0
        best_n = 0
        best_indices = []

        if len(predictions_list) == 1:
            return [1]

        for n in range(int(len(predictions_list)/2), len(predictions_list)):
            cb = itertools.combinations(range(len(predictions_list)), n)
            combination_results = pool.map(partial_compute_subset_auc, cb)
            best_subset_auc, best_subset_indices = max(
                combination_results, key=itemgetter(0))
            print "- best subset auc (%d models): %.4f > %s" % (
                n, best_subset_auc, n, list(best_subset_indices))
            if best_subset_auc > best_auc:
                best_auc = best_subset_auc
                best_n = n
                best_indices = list(best_subset_indices)
        pool.terminate()

        logger.info("best auc: %.4f", best_auc)
        logger.info("best n: %d", best_n)
        logger.info("best indices: %s", best_indices)
        for i, (model, feature_set) in enumerate(self.models):
            if i in best_subset_indices:
                logger.info("> model: %s (%s)", model.__class__.__name__,
                            feature_set)

        return best_subset_indices

    def _get_model_preds(self, model, X_train, X_predict, y_train, cache_file):
        """
        Return the model predictions on the prediction set,
        using cache if possible.
        """
        model_output = load_from_cache(
            "models/%s/%s.pkl" % (self.cache_dir, cache_file),
            self.use_cached_models)

        model_params, model_preds = model_output \
            if model_output is not None else (None, None)

        if model_preds is None or model_params != model.get_params():
            model.fit(X_train, y_train)
            model_preds = model.predict_proba(X_predict)[:, 1]
            with open("cache/models/%s/%s.pkl" % (
                    self.cache_dir, cache_file), 'wb') as f:
                pickle.dump((model.get_params(), model_preds), f)

        return model_preds

    def _get_model_cv_preds(self, model, X_train, y_train, cache_file):
        """
        Return cross-validation predictions on the training set, using cache
        if possible.
        This is used if stacking is enabled (ie. a second model is used to
        combine the stage 0 predictions).
        """
        stack_preds = load_from_cache(
            "models/%s/cv_preds/%s.pkl" % (self.cache_dir, cache_file),
            self.use_cached_models)

        if stack_preds is None:
            kfold = cross_validation.StratifiedKFold(y_train, 4)
            stack_preds = []
            indexes_cv = []
            for stage0, stack in kfold:
                model.fit(X_train[stage0], y_train[stage0])
                stack_preds.extend(list(model.predict_proba(
                    X_train[stack])[:, 1]))
                indexes_cv.extend(list(stack))
            stack_preds = np.array(stack_preds)[sp.argsort(indexes_cv)]

            with open("cache/models/%s/cv_preds/%s%d.pkl" % (
                    self.cache_dir, cache_file), 'wb') as f:
                pickle.dump(stack_preds, f, pickle.HIGHEST_PROTOCOL)

        return stack_preds

    def fit_predict(self, y, train=None, predict=None, show_steps=True):
        """
        Fit each model on the appropriate dataset, then return the average
        of their individual predictions. If train is specified, use a subset
        of the training set to train the models, then predict the outcome of
        either the remaining samples or (if given) those specified in cv.
        If train is omitted, train the models on the full training set, then
        predict the outcome of the full test set.

        Options:
        ------------------------------
        - y: numpy array. The full vector of the ground truths.
        - train: list. The indices of the elements to be used for training.
            If None, take the entire training set.
        - predict: list. The indices of the elements to be predicted.
        - show_steps: boolean. Whether to compute metrics after each stage
            of the computation.
        """
        y_train = y[train] if train is not None else y
        if train is not None and predict is None:
            predict = [i for i in range(len(y)) if i not in train]

        stage0_train = []
        stage0_predict = []
        for model, feature_set in self.models:
            X_train, X_predict = get_dataset(feature_set, train, predict)

            identifier = train[0] if train is not None else -1
            cache_file = stringify(model, feature_set) + str(identifier)

            model_preds = self._get_model_preds(
                model, X_train, X_predict, y_train, cache_file)
            stage0_predict.append(model_preds)

            # if stacking, compute cross-validated predictions on the train set
            if self.stack:
                model_cv_preds = self._get_model_cv_preds(
                    model, X_train, y_train, cache_file)
                stage0_train.append(model_cv_preds)

            # verbose mode: compute metrics after every model computation
            if show_steps:
                if train is not None:
                    mean_preds, stack_preds, fwls_preds = self._combine_preds(
                        np.array(stage0_train).T, np.array(stage0_predict).T,
                        y_train, train, predict,
                        stack=self.stack, fwls=self.fwls)

                    model_auc = compute_auc(y[predict], stage0_predict[-1])
                    mean_auc = compute_auc(y[predict], mean_preds)
                    stack_auc = compute_auc(y[predict], stack_preds) \
                        if self.stack else 0
                    fwls_auc = compute_auc(y[predict], fwls_preds) \
                        if self.fwls else 0

                    logger.info(
                        "> AUC: %.4f (%.4f, %.4f, %.4f) [%s]", model_auc,
                        mean_auc, stack_auc, fwls_auc,
                        stringify(model, feature_set))
                else:
                    logger.info("> used model %s:\n%s", stringify(
                        model, feature_set), model.get_params())

        if self.model_selection and predict is not None:
            best_subset = self._find_best_subset(y[predict], stage0_predict)
            stage0_train = [pred for i, pred in enumerate(stage0_train)
                            if i in best_subset]
            stage0_predict = [pred for i, pred in enumerate(stage0_predict)
                              if i in best_subset]

        mean_preds, stack_preds, fwls_preds = self._combine_preds(
            np.array(stage0_train).T, np.array(stage0_predict).T,
            y_train, stack=self.stack, fwls=self.fwls)

        if self.stack:
            selected_preds = stack_preds if not self.fwls else fwls_preds
        else:
            selected_preds = mean_preds

        return selected_preds


def compute_subset_auc(indices, pred_set, y):
    subset = [vect for i, vect in enumerate(pred_set) if i in indices]
    mean_preds = sp.mean(subset, axis=0)
    mean_auc = compute_auc(y, mean_preds)

    return mean_auc, indices


def find_params(model, feature_set, y, subsample=None, grid_search=False):
    """
    Return parameter set for the model, either predefined
    or found through grid search.
    """
    model_name = model.__class__.__name__
    params = INITIAL_PARAMS.get(model_name, {})
    y = y if subsample is None else y[subsample]

    try:
        with open('saved_params.json') as f:
            saved_params = json.load(f)
    except IOError:
        saved_params = {}

    if (grid_search and model_name in PARAM_GRID and stringify(
            model, feature_set) not in saved_params):
        X, _ = get_dataset(feature_set, subsample, [0])
        clf = GridSearchCV(model, PARAM_GRID[model_name], cv=10, n_jobs=6,
                           scoring="roc_auc")
        clf.fit(X, y)
        logger.info("found params (%s > %.4f): %s",
                    stringify(model, feature_set),
                    clf.best_score_, clf.best_params_)
        params.update(clf.best_params_)
        saved_params[stringify(model, feature_set)] = params
        with open('saved_params.json', 'w') as f:
            json.dump(saved_params, f, indent=4, separators=(',', ': '),
                      ensure_ascii=True, sort_keys=True)
    else:
        params.update(saved_params.get(stringify(model, feature_set), {}))
        if grid_search:
            logger.info("using params %s: %s", stringify(model, feature_set),
                        params)

    return params

########NEW FILE########
__FILENAME__ = utils
"""utils.py

Some useful functions.
Author: Paul Duan <email@paulduan.com>
"""

from re import sub
from sklearn.metrics import roc_curve, auc


def stringify(model, feature_set):
    """Given a model and a feature set, return a short string that will serve
    as identifier for this combination.
    Ex: (LogisticRegression(), "basic_s") -> "LR:basic_s"
    """
    return "%s:%s" % (sub("[a-z]", '', model.__class__.__name__), feature_set)


def compute_auc(y, y_pred):
    fpr, tpr, _ = roc_curve(y, y_pred)
    return auc(fpr, tpr)

########NEW FILE########
