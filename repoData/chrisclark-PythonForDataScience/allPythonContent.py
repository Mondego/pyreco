__FILENAME__ = crossValidate
from sklearn.ensemble import RandomForestClassifier
from sklearn import cross_validation
import logloss
import numpy as np

def main():
    #read in  data, parse into training and target sets
    dataset = np.genfromtxt(open('Data/train.csv','r'), delimiter=',', dtype='f8')[1:]    
    target = np.array([x[0] for x in dataset])
    train = np.array([x[1:] for x in dataset])

    #In this case we'll use a random forest, but this could be any classifier
    cfr = RandomForestClassifier(n_estimators=100)

    #Simple K-Fold cross validation. 5 folds.
    cv = cross_validation.KFold(len(train), k=5, indices=False)

    #iterate through the training and test cross validation segments and
    #run the classifier on each one, aggregating the results into a list
    results = []
    for traincv, testcv in cv:
        probas = cfr.fit(train[traincv], target[traincv]).predict_proba(train[testcv])
        results.append( logloss.llfun(target[testcv], [x[1] for x in probas]) )

    #print out the mean of the cross-validated results
    print "Results: " + str( np.array(results).mean() )

if __name__=="__main__":
    main()
########NEW FILE########
__FILENAME__ = logloss
import scipy as sp
def llfun(act, pred):
    epsilon = 1e-15
    pred = sp.maximum(epsilon, pred)
    pred = sp.minimum(1-epsilon, pred)
    ll = sum(act*sp.log(pred) + sp.subtract(1,act)*sp.log(sp.subtract(1,pred)))
    ll = ll * -1.0/len(act)
    return ll
########NEW FILE########
__FILENAME__ = makeSubmission
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


def main():
    # create the training & test sets
    dataset = pd.read_csv('Data/train.csv')

    target = dataset.Activity.values
    train = dataset.drop('Activity', axis=1).values

    test = pd.read_csv('Data/test.csv').values

    # create and train the random forest
    # n_jobs set to -1 will use the number of cores present on your system.
    rf = RandomForestClassifier(n_estimators=100, n_jobs=-1)
    rf.fit(train, target)
    predicted_probs = [x[1] for x in rf.predict_proba(test)]
    predicted_probs = pd.Series(predicted_probs)

    predicted_probs.to_csv('Data/submission.csv', index=False,
                            float_format="%f")

if __name__ == "__main__":
    main()

########NEW FILE########
