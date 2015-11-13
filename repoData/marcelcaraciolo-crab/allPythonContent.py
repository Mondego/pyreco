__FILENAME__ = statistics
#-*- coding:utf-8 -*-


#========================================================================
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#========================================================================
"""
:mod:`statistics` -- the statistics module
================================================================

    This module contains basic implementations that encapsulate
    retrieval-related statistics about the quality of the recommender's
    recommendations.
"""
from random import random
from math import sqrt, log
from interfaces import RecommenderEvaluator
from models.datamodel import DictDataModel
from recommender.recommender import SlopeOneRecommender
from numpy import std, array, mean


class AverageAbsoluteDifferenceRecommenderEvaluator(RecommenderEvaluator):
    '''
    A Recommender Evaluator which computes the average absolute difference
    between predicted and actual ratings for users.
    '''

    def evaluate(self, recommender, dataModel, trainingPercentage,
            evaluationPercentage):
        if trainingPercentage > 1.0 or trainingPercentage < 0.0:
            raise Exception('Training Percentage is above/under the limit.')

        if evaluationPercentage > 1.0 or evaluationPercentage < 0.0:
            raise Exception('Evaluation Percentage is above/under the limit.')
        # numUsers = dataModel.NumUsers()
        trainingUsers = {}
        testUserPrefs = {}
        self.total = 0
        self.diffs = 0.0

        for userID in dataModel.UserIDs():
            if random() < evaluationPercentage:
                self.processOneUser(trainingPercentage, trainingUsers,
                        testUserPrefs, userID, dataModel)

        trainingModel = DictDataModel(trainingUsers)

        recommender.model = trainingModel

        if isinstance(recommender, SlopeOneRecommender):
            recommender.reset()

        result = self.getEvaluation(testUserPrefs, recommender)

        return result

    def processOneUser(self, trainingPercentage, trainingUsers, testUserPrefs,
            userID, dataModel):
        trainingPrefs = []
        testPrefs = []
        prefs = dataModel.PreferencesFromUser(userID)
        for pref in prefs:
            if random() < trainingPercentage:
                trainingPrefs.append(pref)
            else:
                testPrefs.append(pref)

        if trainingPrefs:
            trainingUsers[userID] = dict(trainingPrefs)
        if testPrefs:
            testUserPrefs[userID] = dict(testPrefs)

    def getEvaluation(self, testUserPrefs, recommender):
        for userID, prefs in testUserPrefs.iteritems():
            estimatedPreference = None
            for pref in prefs:
                try:
                    estimatedPreference = recommender.estimatePreference(
                            userID=userID, itemID=pref,
                            similarity=recommender.similarity)
                except:
                    # It is possible that an item exists in the test data but
                    # not training data in which case an exception will be
                    # throw. Just ignore it and move on.
                    pass
                if estimatedPreference is not None:
                    estimatedPreference = \
                            self.capEstimatePreference(estimatedPreference)
                    self.processOneEstimate(estimatedPreference, prefs[pref])

        return self.diffs / float(self.total)

    def processOneEstimate(self, estimatedPref, realPref):
        self.diffs += abs(realPref - estimatedPref)
        self.total += 1

    def capEstimatePreference(self, estimate):
        if estimate > self.maxPreference:
            return self.maxPreference
        elif estimate < self.minPreference:
            return self.minPreference
        else:
            return estimate


class RMSRecommenderEvaluator(AverageAbsoluteDifferenceRecommenderEvaluator):
    '''
    A Recommender Evaluator which computes the root mean squared difference
    between predicted and actual ratings for users. This is the square root of
    the average of this difference, squared.
    '''

    def processOneEstimate(self, estimatedPref, realPref):
        diff = realPref - estimatedPref
        self.diffs += (diff * diff)
        self.total += 1

    def getEvaluation(self, testUserPrefs, recommender):
        for userID, prefs in testUserPrefs.iteritems():
            estimatedPreference = None
            for pref in prefs:
                try:
                    estimatedPreference = \
                            recommender.estimatePreference(userID=userID,
                                    itemID=pref,
                                    similarity=recommender.similarity)
                except:
                    # It is possible that an item exists in the test data but
                    # not training data in which case an exception will be
                    # throw. Just ignore it and move on.
                    pass
                if estimatedPreference is not None:
                    estimatedPreference = \
                            self.capEstimatePreference(estimatedPreference)
                    self.processOneEstimate(estimatedPreference, prefs[pref])

        return sqrt(self.diffs / float(self.total))


class IRStatsRecommenderEvaluator(RecommenderEvaluator):
    """
    For each user, this evaluator determine the top n preferences, then
    evaluate the IR statistics based on a DataModel that does not have these
    values. This number n is the 'at' value, as in 'precision at 5'.  For
    example this would mean precision evaluated by removing the top 5
    preferences for a user and then finding the percentage of those 5 items
    included in the top 5 recommendations for that user.
    """

    def evaluate(self, recommender, dataModel, at, evaluationPercentage,
            relevanceThreshold=None):
        if evaluationPercentage > 1.0 or evaluationPercentage < 0.0:
            raise Exception('Evaluation Percentage is above/under the limit.')
        if at < 1:
            raise Exception('at must be at leaste 1.')

        irStats = {'precision': None, 'recall': None, 'fallOut': None,
                   'nDCG': None}
        irFreqs = {'precision': 0, 'recall': 0, 'fallOut': 0, 'nDCG': 0}

        nItems = dataModel.NumItems()

        for userID in dataModel.UserIDs():
            if random() < evaluationPercentage:
                prefs = dataModel.PreferencesFromUser(userID)
                if len(prefs) < 2 * at:
                    # Really not enough prefs to meaningfully evaluate the user
                    continue

                relevantItemIDs = []

                # List some most-preferred items that would count as most
                # relevant results
                relevanceThreshold = relevanceThreshold if relevanceThreshold \
                                        else self.computeThreshold(prefs)

                prefs = sorted(prefs, key=lambda x: x[1], reverse=True)

                for index, pref in enumerate(prefs):
                    if index < at:
                        if pref[1] >= relevanceThreshold:
                            relevantItemIDs.append(pref[0])

                if len(relevantItemIDs) == 0:
                    continue

                trainingUsers = {}
                for otherUserID in dataModel.UserIDs():
                    self.processOtherUser(userID, relevantItemIDs,
                            trainingUsers, otherUserID, dataModel)

                trainingModel = DictDataModel(trainingUsers)

                recommender.model = trainingModel

                if isinstance(recommender, SlopeOneRecommender):
                    recommender.reset()

                try:
                    prefs = trainingModel.PreferencesFromUser(userID)
                    if not prefs:
                        continue
                except:
                    #Excluded all prefs for the user. move on.
                    continue

                recommendedItems = recommender.recommend(userID, at)
                intersectionSize = len([recommendedItem
                                        for recommendedItem in recommendedItems
                                        if recommendedItem in relevantItemIDs])

                print intersectionSize
                for key in irStats.keys():
                    irStats[key] = 0.0

                # Precision
                if len(recommendedItems) > 0:
                    irStats['precision'] += \
                            (intersectionSize / float(len(recommendedItems)))
                    irFreqs['precision'] += 1

                # Recall
                irStats['recall'] += \
                        (intersectionSize / float(len(relevantItemIDs)))
                irFreqs['recall'] += 1

                # Fall-Out
                if len(relevantItemIDs) < len(prefs):
                    irStats['fallOut'] += \
                            (len(recommendedItems) - intersectionSize) / \
                            float(nItems - len(relevantItemIDs))
                    irFreqs['fallOut'] += 1

                # nDCG. In computing, assume relevant IDs have relevance 1 and
                # others 0.
                cumulativeGain = 0.0
                idealizedGain = 0.0
                for index, recommendedItem in enumerate(recommendedItems):
                    discount = 1.0 if index == 0 \
                                else 1.0 / self.log2(index + 1)
                    if recommendedItem in relevantItemIDs:
                        cumulativeGain += discount
                    # Otherwise we are multiplying discount by relevance 0 so
                    # it does nothing.  Ideally results would be ordered with
                    # all relevant ones first, so this theoretical ideal list
                    # starts with number of relevant items equal to the total
                    # number of relevant items
                    if index < len(relevantItemIDs):
                        idealizedGain += discount
                irStats['nDCG'] += float(cumulativeGain) / idealizedGain \
                                    if idealizedGain else 0.0
                irFreqs['nDCG'] += 1

        for key in irFreqs:
            irStats[key] = irStats[key] / float(irFreqs[key]) \
                                if irFreqs[key] > 0 else None
        sum_score = irStats['precision'] + irStats['recall'] \
                if irStats['precision'] is not None and \
                        irStats['recall'] is not None \
                else None
        irStats['f1Score'] = None if not sum_score else \
                (2.0) * irStats['precision'] * irStats['recall'] / sum_score

        return irStats

    def processOtherUser(self, userID, relevantItemIDs, trainingUsers,
            otherUserID, dataModel):
        prefs = dataModel.PreferencesFromUser(otherUserID)

        if userID == otherUserID:
            prefsOtherUser = [pref for pref in prefs
                                if pref[0] not in relevantItemIDs]
            if prefsOtherUser:
                trainingUsers[otherUserID] = dict(prefsOtherUser)

        else:
            trainingUsers[otherUserID] = dict(prefs)

    def computeThreshold(self, prefs):
        if len(prefs) < 2:
            #Not enough data points: return a threshold that allows everything
            return - 10000000
        data = [pref[1] for pref in prefs]
        return mean(array(data)) + std(array(data))

    def log2(self, value):
        return log(value) / log(2.0)

########NEW FILE########
__FILENAME__ = interfaces
#-*- coding:utf-8 -*-


#========================================================================
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#========================================================================
"""
:mod:`interfaces` -- the interfaces module
================================================================

    This module contains basic interfaces used throughout the crab package.
    The interfaces are realized as abstract base classes (ie., some optional
    functionality is provided in the interface itself, so that the interfaces
    can be subclassed).
"""

# Base classes


class Similarity(object):
    """
    Similarity Class - for similarity searches over a set of items/users.

    In all instances, there is a data model against which we want to perform
    the similarity search.

    For each similarity search, the input is a item/user and the output are its
    similarities to individual items/users.

    Similarity queries are realized by calling ``self[query_item]``.  There is
    also a convenience wrapper, where iterating over `self` yields similarities
    of each object in the model against the whole data model (ie., the query is
    each item/user in turn).
    """

    def __init__(self, model, distance, numBest=None):
        """ The constructor of Similarity class

        `model` defines the data model where data is fetched.

        `distance` The similarity measured (function) between two vectors.

        If `numBest` is left unspecified, similarity queries return a full list
        (one float for every item in the model, including the query item).

        If `numBest` is set, queries return `numBest` most similar items, as a
        sorted list.

        """
        self.model = model
        self.distance = distance
        self.numBest = numBest

    def getSimilarity(self, vec1, vec2):
        """
        Return similarity of a vector `vec1` to a specific vector `vec2` in the
        model.  The vector is assumed to be either of unit length or empty.

        """
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def getSimilarities(self, vec):
        """

        Return similarity of a vector `vec` to all vectors in the model.
        The vector is assumed to be either of unit length or empty.

        """
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def __getitem__(self, vec):
        """
        Get similarities of a vector `vec` to all items in the model
        """
        allSims = self.getSimilarities(vec)

        # return either all similarities as a list, or only self.numBest most
        # similar, depending on settings from the constructor

        if self.numBest is None:
            return allSims
        else:
            tops = [(label, sim) for label, sim in allSims]
            # sort by -sim => highest sim first
            tops = sorted(tops, key=lambda item: -item[1])
            # return at most numBest top 2-tuples (label, sim)
            return tops[: self.numBest]


class Recommender(object):
    """
    Recommender Class - Base interface for recommending items for a user.

    Implementations will likely take advantage of serveral classes in other
    packages to compute this.

    """

    def __init__(self, model):
        """ The constructor of Similarity class

        `model` defines the data model where data is fetched.

        """
        self.model = model

    def recommend(self, userID, howMany, rescorer=None):
        '''
        Return a list of recommended items, ordered from most strongly
        recommend to least.

        `userID`   user for which recommendations are to be computed.

        `howMany`  desired number of recommendations

        `rescorer` rescoring function to apply before final list of
        recommendations is determined.

        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def estimatePreference(self, **args):
        '''
        Return an estimated preference if the user has not expressed a
        preference for the item, or else the user's actual preference for the
        item. If a preference cannot be estimated, returns None.

        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def allOtherItems(self, userID):
        '''
        Return all items in the `model` for which the user has not expressed
        the preference and could possibly be recommended to the user
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def setPreference(self, userID, itemID, value):
        '''
        Set a new preference of a user for a specific item with a certain
        magnitude.
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def removePreference(self, userID, itemID):
        '''
        Remove a preference of a user for a specific item
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")


class UserBasedRecommender(Recommender):

    def __init__(self, model):
        """ The constructor of Similarity class

        `model` defines the data model where data is fetched.

        """
        Recommender.__init__(self, model)

    def mostSimilarUserIDs(self, userID, howMany, rescorer=None):
        '''
        Return users most similar to the given user.

        `userID` ID of the user for which to find most similar users to find.
        `howMany` the number of most similar users to find
        `rescorer`  which can adjust user-user similarity estimates used to
        determine most similar
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")


class ItemBasedRecommender(Recommender):
    '''
    Interface implemented by "item-based" recommenders.
    '''

    def __init__(self, model):
        """ The constructor of Similarity class

        `model` defines the data model where data is fetched.

        """
        Recommender.__init__(self, model)

    def mostSimilarItems(self, itemIDs, howMany, rescorer=None):
        '''
         Returns items most similar to the given item, ordered from most
         similar to least.

        `itemIDs` IDs of item for which to find most similar other items.
        `howMany` the number of most similar items to find
        `rescorer`  which can adjust item-item similarity estimates used to
        determine most similar

        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def recommendedBecause(self, userID, itemID, howMany, rescorer=None):
        '''
        Return a list of recommended items, ordered from most influential in
        recommended the given item to least

        `userID`  ID of the user who was recommended the item
        `itemID` IDs of item was recommended.
        `howMany` the maximum number of items
        `rescorer`  which can adjust item-item similarity estimates used to
        determine most similar
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")


class Neighborhood(object):
    '''
    Implementations of this interface compute a "neighborhood" of users like a
    given user. This neighborhood can be used to compute recommendations then.
    '''
    def __init__(self, similarity, dataModel, samplingRate):
        ''' Base Constructor Class '''
        self.model = dataModel
        self.samplingRate = samplingRate
        self.similarity = similarity

    def userNeighborhood(self, userID):
        '''
        Return IDs of users in the neighborhood
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")


class CandidateItemsStrategy(object):
    '''
     Used to retrieve all items that could possibly be recommended to the user
    '''

    def candidateItems(self, userID, model):
        raise NotImplementedError("cannot instantiate Abstract Base Class")


class Scorer(object):
    '''
    Implementations of this interface computes a new 'score' to a object such
    as an ID of an item or user which a Recommender is considering returning as
    a top recommendation.
    '''

    def rescore(self, thing, score):
        '''
        Return modified score.
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")


class RecommenderEvaluator(object):
    """
    Evaluates the quality of Recommender recommendations. The range of values
    that may be returned depends on the implementation. but lower values must
    mean better recommendations, with 0 being the lowest / best possible
    evaluation, meaning a perfect match.

    Implementations will take a certain percentage of the preferences supplied
    by the given DataModel as "training" data.  This is commonly most of the
    data, like 90%. This data is used to produce recommendations, and the rest
    of the data is compared against estimated preference values to see how much
    the recommender's predicted preferences match the user's real preferences.
    Specifically, for each user, this percentage of the user's ratings are used
    to produce recommendation, and for each user, the remaining preferences are
    compareced against the user's real preferences

    For large datasets, it may be desirable to only evaluate based on a small
    percentage of the data. Evaluation Percentage controls how many of the
    DataModel's users are used in the evaluation.

    To be clear, TrainingPercentage and EvaluationPercentage are not relatred.
    They do not need to add up to 1.0, for example.

    """

    def __init__(self, minPreference=0, maxPreference=5):
        self.minPreference = minPreference
        self.maxPreference = maxPreference

    def evaluate(self, recommender, dataModel, trainingPercentage,
            evaluationPercentage):
        '''
        `recommender`  defines the Recommender to test.
        `dataModel`  defines the dataset to test on
        `trainingPercentage`  percentage of each user's preferences to use to
        produce recommendations; the rest are compared to estimated preference
        values to evaluate 'evaluationPercentage'  percentage of users to use
        in evaluation

        Returns a score representing how well the recommender estimated the
        preferences match real values; Lower Scores mean a better match and 0
        is a perfect match

        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def MaxPreference(self):
        return self.maxPreference

    def setMaxPreference(self, maxPreference):
        self.maxPreference = maxPreference

    def MinPreference(self):
        return self.minPreference

    def setMinPreference(self, minPreference):
        self.minPreference = minPreference

########NEW FILE########
__FILENAME__ = datamodel
#-*- coding:utf-8 -*-


#========================================================================
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#========================================================================

# REVISION HISTORY

# 0.1 2010-11-01  Initial version.
# 0.2 2010-11-11 Changed the method preferenceValue implementation to use
#   get(userID) and get(itemID)

"""
:mod:`datamodel` -- the data model module
================================================================

    This module contains models that represent a repository of information a
     bout users and their associated preferences for items.

"""


class DataModel(object):
    '''
    Base Data Model Class that represents the basic repository of
    information about users and their associated preferences
    for items.
    '''

    def UserIDs(self):
        '''
        Return all user IDs in the model, in order
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def PreferencesFromUser(self, userID, orderByID=True):
        '''
        Return user's preferences, ordered by user ID (if orderByID is True)
        or by the preference values (if orderById is False), as an array.
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def ItemIDsFromUser(self, userID):
        '''
        Return IDs of items user expresses a preference for
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def ItemIDs(self):
        '''
        Return a iterator of all item IDs in the model, in order
         '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def PreferencesForItem(self, itemID, orderByID=True):
        '''
        Return all existing Preferences expressed for that item,
        ordered by user ID (if orderByID is True) or by the preference values
        (if orderById is False), as an array.
         '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def PreferenceValue(self, userID, itemID):
        '''
        Retrieves the preference value for a single user and item.
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def PreferenceTime(self, userID, itemID):
        '''
        Retrieves the time at which a preference value from a user and item was
        set, if known.  Time is expressed in the usual way, as a number of
        milliseconds since the epoch.
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def NumUsers(self):
        '''
        Return total number of users known to the model.
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def NumItems(self):
        '''
        Return total number of items known to the model.
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def NumUsersWithPreferenceFor(self, *itemIDs):
        '''
        Return the number of users who have expressed a preference for all of
        the items
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def setPreference(self, userID, itemID, value):
        '''
        Sets a particular preference (item plus rating) for a user.
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def removePreference(self, userID, itemID):
        '''
        Removes a particular preference for a user.
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def convertItemID2name(self, itemID):
        """Given item id number return item name"""
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def convertUserID2name(self, userID):
        """Given user id number return user name"""
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def hasPreferenceValues(self):
        '''
        Return True if this implementation actually it is not a 'boolean'
        DataModel.  Otherwise returns False.
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def MaxPreference(self):
        '''
        Return the maximum preference value that is possible in the current
        problem domain being evaluated.  For example, if the domain is movie
        ratings on a scale of 1 to 5, this should be 5. While  a recommender
        may estimate a preference value above 5.0, it isn't "fair" to consider
        that the system is actually suggesting an impossible rating of, say,
        5.4 stars.  In practice the application would cap this estimate to 5.0.
        Since evaluators evaluate the difference between estimated and actual
        value, this at least prevents this effect from unfairly penalizing a
        Recommender.
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")

    def MinPreference(self):
        '''
        Returns the minimum preference value that is possible in the current
        problem domain being evaluated
        '''
        raise NotImplementedError("cannot instantiate Abstract Base Class")


class DictDataModel(DataModel):
    '''
    A DataModel backed by a python dict structured data. This class expects a
    simple dictionary where each element contains a userID, followed by itemID,
    followed by preference value and optional timestamp.

    {userID: {itemID:preference, itemID2:preference2},
     userID2:{itemID:preference3, itemID4:preference5}}

    Preference value is the parameter that the user simply expresses the degree
    of preference for an item.

    '''
    def __init__(self, dataS):
        ''' DictDataModel Constructor '''
        DataModel.__init__(self)
        self.dataU = dataS
        self.buildModel()

    def __getitem__(self, userID):
        return self.PreferencesFromUser(userID)

    def __iter__(self):
        for num, user in enumerate(self.userIDs):
            yield user, self[user]

    def buildModel(self):
        ''' Build the model '''
        self.userIDs = self.dataU.keys()
        self.userIDs.sort()

        self.itemIDs = []
        for userID in self.userIDs:
            items = self.dataU[userID]
            self.itemIDs.extend(items.keys())

        self.itemIDs = list(set(self.itemIDs))
        self.itemIDs.sort()

        self.maxPref = -100000000
        self.minPref = 100000000

        self.dataI = {}
        for user in self.dataU:
            for item in self.dataU[user]:
                self.dataI.setdefault(item, {})
                self.dataI[item][user] = self.dataU[user][item]
                if self.dataU[user][item] > self.maxPref:
                    self.maxPref = self.dataU[user][item]
                if  self.dataU[user][item] < self.minPref:
                    self.minPref = self.dataU[user][item]

    def UserIDs(self):
        return self.userIDs

    def ItemIDs(self):
        return self.itemIDs

    def PreferencesFromUser(self, userID, orderByID=True):
        userPrefs = self.dataU.get(userID, None)

        if userPrefs is None:
            raise ValueError(
                    'User not found. Change for a suitable exception here!')

        userPrefs = userPrefs.items()

        if not orderByID:
            userPrefs.sort(key=lambda userPref: userPref[1], reverse=True)
        else:
            userPrefs.sort(key=lambda userPref: userPref[0])

        return userPrefs

    def ItemIDsFromUser(self, userID):
        prefs = self.PreferencesFromUser(userID)
        return [key for key, value in prefs]

    def PreferencesForItem(self, itemID, orderByID=True):
        itemPrefs = self.dataI.get(itemID, None)

        if not itemPrefs:
            raise ValueError(
                    'User not found. Change for a suitable exception here!')

        itemPrefs = itemPrefs.items()

        if not orderByID:
            itemPrefs.sort(key=lambda itemPref: itemPref[1], reverse=True)
        else:
            itemPrefs.sort(key=lambda itemPref: itemPref[0])

        return itemPrefs

    def PreferenceValue(self, userID, itemID):
        return self.dataU.get(userID).get(itemID, None)

    def NumUsers(self):
        return len(self.dataU)

    def NumItems(self):
        return len(self.dataI)

    def NumUsersWithPreferenceFor(self, *itemIDs):
        if len(itemIDs) > 2 or len(itemIDs) == 0:
            raise ValueError('Illegal number of IDs')

        prefs1 = dict(self.PreferencesForItem(itemIDs[0]))

        if not prefs1:
            return 0

        if len(itemIDs) == 1:
            return len(prefs1)

        prefs2 = dict(self.PreferencesForItem(itemIDs[1]))

        if not prefs2:
            return 0

        nUsers = len([user for user in prefs1  if user in prefs2])

        return nUsers

    def hasPreferenceValues(self):
        return True

    def MaxPreference(self):
        return self.maxPref

    def MinPreference(self):
        return self.minPref

########NEW FILE########
__FILENAME__ = itemstrategies
#-*- coding:utf-8 -*-


#========================================================================
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#========================================================================
"""
:mod:`itemstrategies` -- the item strategies modules
================================================================

This module contains functions and classes to retrieve all items that could
possibly be recommended to the user

"""

from interfaces import CandidateItemsStrategy


class PreferredItemsNeighborhoodStrategy(CandidateItemsStrategy):
    '''
    Returns all items that have not been rated by the user and that were
    preferred by another user that has preferred at least one item that the
    current user has preferred too
    '''

    def candidateItems(self, userID, model):
        possibleItemIDs = []
        itemIDs = model.ItemIDsFromUser(userID)
        for itemID in itemIDs:
            prefs2 = model.PreferencesForItem(itemID)
            for otherUserID, pref in prefs2:
                possibleItemIDs.extend(model.ItemIDsFromUser(otherUserID))

        possibleItemIDs = list(set(possibleItemIDs))

        return [itemID for itemID in possibleItemIDs if itemID not in itemIDs]

########NEW FILE########
__FILENAME__ = neighborhood
#-*- coding:utf-8 -*-


#========================================================================
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#========================================================================

# REVISION HISTORY

#0.1 2010-11-04  Initial version.

"""
:mod:`neighborhood` -- the neighborhood modules
================================================================

This module contains functions and classes to compute the neighborhood given an
user.

"""

from interfaces import Neighborhood
from recommender.topmatches import topUsers
import random


class NearestNUserNeighborhood(Neighborhood):

    def __init__(self, similarity, model, numUsers, minSimilarity,
            samplingRate=1):
        ''' Constructor Class

        `numUsers` neighborhood size; capped at the number of users in the data
        model

        `samplingRate`  percentage of users to consider when building
        neighborhood

        `minSimilarity`  minimal similarity required for neighbors
        '''
        Neighborhood.__init__(self, similarity, model, samplingRate)
        nUsers = model.NumUsers()
        self.numUsers = nUsers if numUsers > nUsers else numUsers
        self.minSimilarity = minSimilarity

    def estimatePreference(self, **args):
        #@TODO: How to improve this architecture for estimatePreference as a
        # method for topMatches.
        userID = args.get('thingID', None) or args.get('userID', None)
        otherUserID = args.get('otherUserID', None)
        similarity = args.get('similarity', self.similarity)

        # Don't consider the user itself as possible most similar user
        if userID == otherUserID:
            return None

        estimated = similarity.getSimilarity(userID, otherUserID)
        return estimated

    def userNeighborhood(self, userID, rescorer=None):
        ''' Return the most similar users to the given userID'''
        # Sampling
        userIDs = self.getSampleUserIDs()

        if not userIDs:
            return []

        rec_users = topUsers(userID, userIDs, self.numUsers,
                self.estimatePreference, self.similarity, rescorer)

        return rec_users

    def getSampleUserIDs(self):
        userIDs = self.model.UserIDs()

        numberOfUsers = int(float(self.samplingRate) * len(userIDs))

        if numberOfUsers == len(userIDs):
            return userIDs
        elif numberOfUsers == 0:
            return []
        else:
            total_users = 0
            length = len(userIDs) - numberOfUsers
            while total_users < length:
                random.shuffle(userIDs)
                userIDs.pop()
                total_users += 1

            return userIDs

########NEW FILE########
__FILENAME__ = recommender
#-*- coding:utf-8 -*-


#========================================================================
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#========================================================================
"""
:mod:`recommender` -- the recommender modules
================================================================

This module contains functions and classes to produce recommendations.

"""

from interfaces import UserBasedRecommender, ItemBasedRecommender, Recommender
from topmatches import topUsers, topItems
from utils import DiffStorage


class UserRecommender(UserBasedRecommender):
    '''
    A simple Recommender which uses a given dataModel and NeighborHood
    to produce recommendations.

    '''
    def __init__(self, model, similarity, neighborhood, capper=True):
        ''' UserBasedRecommender Class Constructor

            `model` is the data source model

            `neighborhood` is the neighborhood strategy for computing the most
            similar users.

            `similarity` is the class used for computing the similarities over
            the users.

            `capper` a normalizer for Maximum/Minimum Preferences range.

        '''
        UserBasedRecommender.__init__(self, model)
        self.neighborhood = neighborhood
        self.similarity = similarity
        self.capper = capper

    def recommend(self, userID, howMany, rescorer=None):
        nearestN = self.neighborhood.userNeighborhood(userID, rescorer)

        if not nearestN:
            return []

        allItemIDs = self.allOtherItems(userID, nearestN)

        rec_items = topItems(userID, allItemIDs, howMany,
                self.estimatePreference, self.similarity, rescorer)

        return rec_items

    def estimatePreference(self, **args):
        userID = args.get('thingID', None) or args.get('userID', None)
        itemID = args.get('itemID', None)
        similarity = args.get('similarity', self.similarity)
        nHood = args.get('neighborhood', None)
        rescorer = args.get('rescorer', None)

        if not nHood:
            pref = self.model.PreferenceValue(userID, itemID)
            if pref is not None:
                return pref

            nHood = self.neighborhood.userNeighborhood(userID=userID,
                    rescorer=rescorer)

        if not nHood:
            return None

        preference = 0.0
        totalSimilarity = 0.0
        count = 0
        for usrID in nHood:
            if usrID != userID:
                pref = self.model.PreferenceValue(usrID, itemID)
                if pref is not None:
                    sim = similarity.getSimilarity(usrID, userID)
                    if sim is not None:
                        preference += sim * pref
                        totalSimilarity += sim
                        count += 1

        # Throw out the estimate if it was based on no data points, of course,
        # but also if based on just one. This is a bit of a band-aid on the
        # 'stock' item-based algorithm for the moment.  The reason is that in
        # this case the estimate is, simply, the user's rating for one item
        # that happened to have a defined similarity. The similarity score
        # doesn't matter, and that seems like a bad situation.
        if count <= 1 or totalSimilarity == 0.0:
            return None

        estimated = float(preference) / totalSimilarity

        if self.capper:
            # TODO: Maybe put this in a separated function.
            max = self.model.MaxPreference()
            min = self.model.MinPreference()
            estimated = max if estimated > max else \
                    min if estimated < min else estimated

        return estimated

    def mostSimilarUserIDs(self, userID, howMany, rescorer=None):
        return topUsers(userID, self.model.UserIDs(), howMany,
                self.neighborhood.estimatePreference, self.similarity,
                rescorer)

    def allOtherItems(self, userID, neighborhood):
        possibleItemIDs = []
        for usrID in neighborhood:
            possibleItemIDs.extend(self.model.ItemIDsFromUser(usrID))

        itemIds = self.model.ItemIDsFromUser(userID)
        possibleItemIDs = list(set(possibleItemIDs))

        return [itemID for itemID in possibleItemIDs if itemID not in itemIds]


class SlopeOneRecommender(Recommender):
    """
    A basic "slope one" recommender. This is a recommender specially suitable
    when user preferencces are updating frequently as it can incorporate this
    information without expensive recomputation.  It can also be used as a
    weighted slope one recommender.
    """
    def __init__(self, model, weighted=True, stdDevWeighted=True,
            toPrune=True):
        '''
        SlopeOneRecommender Class Constructor

       `model` is the data source model

       `weighted` is a flag that if it is True, it act as a weighted slope one
       recommender.

       `stdDevWeighted` is a flag that if it is True, use standard deviation
       weighting of diffs

       `toPrune` is a flag that if it is True, it will prune the irrelevant
       diffs, represented by one data point.
        '''
        Recommender.__init__(self, model)
        self.weighted = weighted
        self.stdDevWeighted = stdDevWeighted
        self.storage = DiffStorage(self.model, self.stdDevWeighted, toPrune)

    def recommend(self, userID, howMany, rescore=None):
        possibleItemIDs = self.possibleItemIDs(userID)
        rec_items = topItems(userID, possibleItemIDs, howMany,
                self.estimatePreference, None, None)
        return rec_items

    def possibleItemIDs(self, userID):
        preferences = self.model.ItemIDsFromUser(userID)
        recommendableItems = self.storage.recommendableItems()
        return [itemID for itemID in recommendableItems
                if itemID not in preferences]

    def estimatePreference(self, **args):
        userID = args.get('thingID', None) or args.get('userID', None)
        itemID = args.get('itemID', None)
        #similarity = args.get('similarity', None)
        nHood = args.get('neighborhood', None)
        #rescorer = args.get('rescorer', None)

        if not nHood:
            pref = self.model.PreferenceValue(userID, itemID)
            if pref is not None:
                return pref

        count = 0
        totalPreference = 0.0
        prefs = self.model.PreferencesFromUser(userID)
        averages = self.storage.diffsAverage(userID, itemID, prefs)
        for i in range(len(prefs)):
            averageDiffValue = averages[i]
            if averageDiffValue is not None:
                if self.weighted:
                    weight = self.storage.count(itemID, prefs[i][0])
                    if self.stdDevWeighted:
                        stdev = self.storage.standardDeviation(
                                itemID, prefs[i][0])
                        if stdev is not None:
                            weight /= 1.0 + stdev
                            # If stdev is None, it is because count is 1. Since
                            # we are weighting by count the weight is already
                            # low. So we assume stdev is 0.0.
                    totalPreference += \
                            weight * (prefs[i][1] + averageDiffValue)
                    count += weight
                else:
                    totalPreference += prefs[i][1] + averageDiffValue
                    count += 1

        if count <= 0:
            return None
            # BUGFIX
            # itemAverage = self.storage.AverageItemPref(itemID)
            # if itemAverage is not None:
            #    itemAverage = itemAverage.Average()
            #    return itemAverage
            # else:
            #    return None
        else:
            return totalPreference / float(count)


class ItemRecommender(ItemBasedRecommender):
    '''
    A simple recommender which uses a given DataModel and ItemSimilarity to
    produce recommendations. This class represents a support for item based
    recommenders.
    '''
    def __init__(self, model, similarity, itemStrategy, capper=True):
        '''
        UserBasedRecommender Class Constructor

        `model` is the data source model

        `itemStrategy` is the candidate item strategy for computing the most
        similar items.

        `similarity` is the class used for computing the similarities over
        the items.

        `capper` a normalizer for Maximum/Minimum Preferences range.
        '''
        ItemBasedRecommender.__init__(self, model)
        self.strategy = itemStrategy
        self.similarity = similarity
        self.capper = capper

    def recommend(self, userID, howMany, rescorer=None):
        if self.numPreferences(userID) == 0:
            return []

        possibleItemIDs = self.allOtherItems(userID)

        rec_items = topItems(userID, possibleItemIDs, howMany,
                self.estimatePreference, self.similarity, rescorer)

        return rec_items

    def allOtherItems(self, userID):
        return self.strategy.candidateItems(userID, self.model)

    def estimateMultiItemsPreference(self, **args):
        toItemIDs = args.get('thingID', None)
        itemID = args.get('itemID', None)
        similarity = args.get('similarity', self.similarity)
        rescorer = args.get('rescorer', None)

        sum = 0.0
        total = 0

        for toItemID in toItemIDs:
            preference = similarity.getSimilarity(itemID, toItemID)

            rescoredPref = rescorer.rescore((itemID, toItemID), preference) \
                                if rescorer else preference

            sum += rescoredPref
            total += 1

        return sum / total

    def numPreferences(self, userID):
        return len(self.model.PreferencesFromUser(userID))

    def estimatePreference(self, **args):
        userID = args.get('thingID', None) or args.get('userID', None)
        itemID = args.get('itemID', None)
        similarity = args.get('similarity', self.similarity)

        preference = self.model.PreferenceValue(userID, itemID)

        if preference is not None:
            return preference

        totalSimilarity = 0.0
        preference = 0.0
        count = 0

        prefs = self.model.PreferencesFromUser(userID)
        for toItemID, pref in prefs:
            if toItemID != itemID:
                sim = similarity.getSimilarity(itemID, toItemID)
                if sim is not None:
                    preference += sim * pref
                    totalSimilarity += sim
                    count += 1

        # Throw out the estimate if it was based on no data points, of course,
        # but also if based on just one. This is a bit of a band-aid on the
        # 'stock' item-based algorithm for the moment.  The reason is that in
        # this case the estimate is, simply, the user's rating for one item
        # that happened to have a defined similarity. The similarity score
        # doesn't matter, and that seems like a bad situation.
        if count <= 1 or totalSimilarity == 0.0:
            return None

        estimated = float(preference) / totalSimilarity

        if self.capper:
            # TODO: Maybe put this in a separated function.
            max = self.model.MaxPreference()
            min = self.model.MinPreference()
            estimated = max if estimated > max else \
                        min if estimated < min else estimated

        return estimated

    def estimateBecausePreference(self, **args):
        userID = args.get('thingID') or args.get('userID')
        itemID = args.get('itemID')
        similarity = args.get('similarity', self.similarity)
        recommendedItemID = args.get('recommendedItemID')

        pref = self.model.PreferenceValue(userID, itemID)

        if pref is None:
            return None

        simValue = similarity.getSimilarity(itemID, recommendedItemID)

        return (1.0 + simValue) * pref

    def recommendedBecause(self, userID, itemID, howMany, rescorer=None):
        prefs = self.model.PreferencesFromUser(userID)
        allUserItems = [otherItemID for otherItemID, pref in prefs
                        if otherItemID != itemID]
        allUserItems = list(set(allUserItems))

        return topItems(thingID=userID, possibleItemIDs=allUserItems,
                howMany=howMany,
                preferenceEstimator=self.estimateBecausePreference,
                similarity=self.similarity, rescorer=None,
                recommendedItemID=itemID)

    def mostSimilarItems(self, itemIDs, howMany, rescorer=None):
        possibleItemIDs = []
        for itemID in itemIDs:
            prefs = self.model.PreferencesForItem(itemID)
            for userID, pref in prefs:
                possibleItemIDs.extend(self.model.ItemIDsFromUser(userID))

        possibleItemIDs = list(set(possibleItemIDs))

        pItems = [itemID for itemID in possibleItemIDs
                  if itemID not in itemIDs]

        return topItems(itemIDs, pItems, howMany,
                self.estimateMultiItemsPreference, self.similarity, rescorer)

########NEW FILE########
__FILENAME__ = topmatches
#-*- coding:utf-8 -*-


#========================================================================
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#========================================================================

# REVISION HISTORY

#0.1 2010-11-09  Initial version.
"""
:mod:`topmatches` -- the topmatches  module
================================================================

This module contains functions that implements the find top N things logic.

"""

NO_IDS = []


def topUsers(thingID, allUserIDs, howMany, preferenceEstimator, similarity,
        rescorer=None, **extra):
    ''' Find Top N Users

    `thingID` ID of the user/item for which to find most similar users to find.

    `allUserIDs` the set of userIDs from the data model.

    `howMany` the number of most similar users to find.

    `preferenceEstimator` : a function for estimate the preference given a
    userID and otherUserID.

    `similarity` the similarity between users.

    `rescorer` a Scorer Class for rescore the preference for a thing (user or
    item).
    '''
    topNRecs = []

    extra.update({'rescorer': rescorer})

    for otherUserID in allUserIDs:
        preference = preferenceEstimator(thingID=thingID,
                similarity=similarity, otherUserID=otherUserID, **extra)

        if preference is None:
            continue

        rescoredPref = rescorer.rescore(thingID, preference) \
                        if rescorer else preference

        if rescoredPref is not None:
            topNRecs.append((otherUserID, rescoredPref))

    topNRecs = sorted(topNRecs, key=lambda item: -item[1])

    topNRecs = [item[0] for item in topNRecs]

    return topNRecs[0:howMany] if topNRecs and len(topNRecs) > howMany \
            else topNRecs if topNRecs else NO_IDS


def topItems(thingID, possibleItemIDs, howMany, preferenceEstimator,
        similarity, rescorer=None, **extra):
    '''
    Find Top N items

    `thingID` ID of the item or user  for which to find most similar items to
    find.

    `possibleItemIDs` the set of possible itemIDs from data model.

    `howMany` the number of most similar items to find.

    `preferenceEstimator` : a function for estimate the preference given an
    itemID and otherItemID.

    `similarity` the similarity between items.

    `rescorer` a Scorer Class for rescore the preference for a thing (user or
    item).
    '''
    topNRecs = []

    extra.update({'rescorer': rescorer})

    for otherItemID in possibleItemIDs:
        preference = preferenceEstimator(thingID=thingID,
                similarity=similarity, itemID=otherItemID, **extra)

        if preference is None:
            continue

        rescoredPref = rescorer.rescore(thingID, preference) \
                        if rescorer else preference

        if rescoredPref is not None:
            topNRecs.append((otherItemID, rescoredPref))

    topNRecs = sorted(topNRecs, key=lambda item: -item[1])

    topNRecs = [item[0] for item in topNRecs]

    return topNRecs[0:howMany] if topNRecs and len(topNRecs) > howMany \
            else topNRecs if topNRecs else []

########NEW FILE########
__FILENAME__ = utils
#-*- coding:utf-8 -*-


#========================================================================
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#========================================================================
"""
:mod:`utils` -- the utils recommendation modules
================================================================

This module contains functions and classes to help the recommendation process.

"""


class DiffStorage(object):
    '''
    An implementation of DiffStorage that merely stores item-item diffs in
    memory. Caution: It may consume a great deal of memory due to larger
    datasets.
    '''
    def __init__(self, model, stdDevWeighted, toPrune=True):
        '''
        DiffStorage Class Constructor

        `model` is the data source model

        `stdDevWeighted` is a flag that if it is True, use standard deviation
        weighting of diffs

        `toPrune` is a flag that if it is True, it will prune the irrelevant
        diffs, represented by one data point.
        '''
        self.model = model
        self.stdDevWeighted = stdDevWeighted
        self.toPrune = toPrune
        self._diffStorage = {}
        self._diffStorageStdDev = {}
        self._freqs = {}
        self._recommendableItems = []
        self._buildAverageDiffs()

    def _buildAverageDiffs(self):
        self._diffStorage = {}
        for userID in self.model.UserIDs():
            self.processOneUser(userID)
        if self.toPrune:
            self.pruneDiffs()
        self.updateAllRecommendableItems()
        if self.stdDevWeighted:
            self.evaluateStandardDeviation()
        self.evaluateAverage()

    def recommendableItems(self):
        return self._recommendableItems

    def updateAllRecommendableItems(self):
        self._recommendableItems = []
        for itemID in self._diffStorage:
            self._recommendableItems.append(itemID)
        self._recommendableItems.sort()

    def evaluateAverage(self):
        for itemIDA, ratings in self._diffStorage.iteritems():
            for itemIDB in ratings:
                ratings[itemIDB] /= self._freqs[itemIDA][itemIDB]

    def diffsAverage(self, userID, itemID, prefs):
        return [self.diff(itemID, itemID2) if itemID2 in self._freqs[itemID]
                else -self.diff(itemID, itemID2)
                if self.diff(itemID, itemID2) is not None
                else None
                for itemID2, rating in prefs]

    def diff(self, itemIDA, itemIDB):
        if itemIDA in self._diffStorage:
            if itemIDB in self._diffStorage[itemIDA]:
                return self._diffStorage[itemIDA][itemIDB]
            elif itemIDB in self._diffStorage:
                if itemIDA in self._diffStorage[itemIDB]:
                    return self._diffStorage[itemIDB][itemIDA]
                else:
                    return None
            else:
                return None

    def evaluateStandardDeviation(self):
        for itemIDA, ratings in self._diffStorage.iteritems():
            for itemIDB in ratings:
                pass

    def standardDeviation(self, itemID, itemID2):
        return 0.0

    def count(self, itemID, itemID2):
        try:
            return self._freqs[itemID][itemID2]
        except KeyError:
            return self._freqs[itemID2][itemID]

    def pruneDiffs(self):
        '''
        Go back and prune irrelevant diffs. Irrelevant means here, represented
        by one data point, so possibly unreliable
        '''
        for item1 in self._freqs.keys():
            for item2 in self._freqs[item1].keys():
                if self._freqs[item1][item2] <= 1:
                    del self._freqs[item1][item2]
                    del self._diffStorage[item1][item2]
                    if len(self._diffStorage[item1]) == 0:
                        break

    def processOneUser(self, userID):
        userPreferences = self.model.PreferencesFromUser(userID)
        for indexA, preferenceA in enumerate(userPreferences):
            itemID1, rating1 = preferenceA
            self._diffStorage.setdefault(itemID1, {})
            self._freqs.setdefault(itemID1, {})
            for indexB, preferenceB in enumerate(userPreferences[indexA + 1:]):
                itemID2, rating2 = preferenceB
                self._diffStorage[itemID1].setdefault(itemID2, 0.0)
                self._freqs[itemID1].setdefault(itemID2, 0)
                self._diffStorage[itemID1][itemID2] += (rating1 - rating2)
                self._freqs[itemID1][itemID2] += 1

########NEW FILE########
__FILENAME__ = scorer
#-*- coding:utf-8 -*-


#========================================================================
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#========================================================================

# REVISION HISTORY

#0.1 2010-11-09 Initial version.
"""
:mod:`scorer` -- the scoring classes and functions
================================================================

This module contains functions and classes to compute the new score for a
preference given an thing (user or item).

"""

from interfaces import Scorer
from math import tanh


class NaiveScorer(Scorer):
    '''
    A simple Scorer which always returns the original score.
    '''

    def rescore(self, thing, score):
        '''
        return same originalScore as new score, always
        '''
        return  score


class TanHScorer(Scorer):
    '''
    A simple Scorer which returns the score normalized betweeen 0 and 1 where 1
    is most similar and 0 dissimilar.  '''

    def rescore(self, thing, score):
        return  1 - tanh(score)

########NEW FILE########
__FILENAME__ = similarity
#-*- coding:utf-8 -*-

#========================================================================
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#========================================================================

# REVISION HISTORY

#0.1 2010-10-31  Initial version.
"""
:mod:`similarity_distance` -- the similarity distances table
================================================================

This module contains functions and classes for computing similarities across a
collection of vectors.

"""


from interfaces import Similarity


class UserSimilarity(Similarity):
    '''
    Returns the degree of similarity, of two users, based on the their
    preferences. Implementations of this class define a notion of similarity
    between two users.  Implementations should  return values in the range 0.0
    to 1.0, with 1.0 representing perfect similarity.
    '''

    def __init__(self, model, distance, numBest=None):
        Similarity.__init__(self, model, distance, numBest)

    def getSimilarity(self, vec1, vec2):
        usr1Prefs = dict(self.model.PreferencesFromUser(vec1))
        usr2Prefs = dict(self.model.PreferencesFromUser(vec2))

        # Evaluate the similarity between the two users vectors.
        return self.distance(usr1Prefs, usr2Prefs)

    def getSimilarities(self, vec):
        return [(other, self.getSimilarity(vec, other))
                for other, v in self.model]

    def __iter__(self):
        """
        For each object in model, compute the similarity function against all
        other objects and yield the result.  """
        for num, user, vec in enumerate(self.model):
            yield self[user]


class ItemSimilarity(Similarity):
    '''
    Returns the degree of similarity, of two items, based on its preferences by
    the users.  Implementations of this class define a notion of similarity
    between two items.  Implementations should  return values in the range 0.0
    to 1.0, with 1.0 representing perfect similarity.
    '''
    def __init__(self, model, distance, numBest=None):
        Similarity.__init__(self, model, distance, numBest)

    def getSimilarity(self, vec1, vec2):
        item1Prefs = dict(self.model.PreferencesForItem(vec1))
        item2Prefs = dict(self.model.PreferencesForItem(vec2))

        # Evaluate the similarity between the two users vectors.
        return self.distance(item1Prefs, item2Prefs)

    def getSimilarities(self, vec):
        return [(other, self.getSimilarity(vec, other))
                for other in self.model.ItemIDs()]

    def __iter__(self):
        """
        For each object in model, compute the similarity function against all
        other objects and yield the result.
        """
        for num, item in enumerate(self.model.ItemIDs()):
            yield item, self.PreferencesForItem(userID)

########NEW FILE########
__FILENAME__ = similarity_distance
#-*- coding:utf-8 -*-

'''

* Licensed to the Apache Software Foundation (ASF) under one or more
* contributor license agreements.  See the NOTICE file distributed with
* this work for additional information regarding copyright ownership.
* The ASF licenses this file to You under the Apache License, Version 2.0
* (the "License"); you may not use this file except in compliance with
* the License.  You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.


0.1 2010-10-11 Initial version.
               Added sim_euclidian , sim_pearson, sim_spearman
0.11 2010-10-13 Added sim_cosine, sim_tanimoto
0.12 2010-10-16 Added sim_loglikehood
0.13 2010-10-17 Added  sim_sorensen
0.14 2010-10-20 Added sim_manhattan
0.15 2010-10-26 Reformulated all design of the similarities.
0.16 2010-10-28 Added sim_jaccard.



'''

"""
:mod:`similarity_distance` -- the similarity distances table
================================================================

    This module is responsible of joining all similariy distances funcions.


"""

try:
    from numpy import sqrt, log
except ImportError:
    from math import sqrt, log


def sim_euclidian(vector1, vector2, **args):
    '''
    An implementation of a "similarity" based on the Euclidean "distance"
    between two vectors X and Y. Thinking of items as dimensions and
    preferences as points along those dimensions, a distance is computed using
    all items (dimensions) where both users have expressed a preference for
    that item. This is simply the square root of the sum of the squares of
    differences in position (preference) along each dimension. The similarity
    is then computed as 1 / (1 + distance), so the resulting values are in the
    range (0,1].

    Parameters:
        vector1: The vector you want to compare
        vector2: The second vector you want to compare
        args: optional arguments

    The value returned is in [0,1].
    '''
    # Using Content Mode.
    if type(vector1) == type({}):
        sim = {}
        [sim.update({item:1}) for item in vector1 if item in vector2]

        if len(sim) == 0.0:
            return 0.0

        sum_of_squares = sum([pow(vector1[item] - vector2[item], 2.0)
                           for item in vector1 if item in vector2])
    else:
        # Using Value Mode.
        if len(vector1) != len(vector2):
            raise ValueError('Dimmensions vector1 != Dimmensions vector2')

        sum_of_squares = sum([pow(vector1[i] - vector2[i], 2.0)
                              for i in range(len(vector1))])

        if not sum_of_squares:
            return 0.0

    return 1 / (1 + sqrt(sum_of_squares))


def sim_pearson(vector1, vector2, **args):
    '''
    This correlation implementation is equivalent to the cosine similarity
    since the data it receives is assumed to be centered -- mean is 0. The
    correlation may be interpreted as the cosine of the angle between the two
    vectors defined by the users' preference values.

    Parameters:
        vector1: The vector you want to compare
        vector2: The second vector you want to compare
        args: optional arguments

    The value returned is in [0,1].

    '''
    # Using Content Mode.
    if type(vector1) == type({}):
        sim = {}
        [sim.update({item:1})  for item in vector1  if item in vector2]
        n = len(sim)

        if n == 0:
            return 0.0

        sum1 = sum([vector1[it]  for it in sim])
        sum2 = sum([vector2[it]  for it in sim])

        sum1Sq = sum([pow(vector1[it], 2.0) for it in sim])
        sum2Sq = sum([pow(vector2[it], 2.0) for it in sim])

        pSum = sum(vector1[it] * vector2[it] for it in sim)

        num = pSum - (sum1 * sum2 / float(n))

        den = sqrt((sum1Sq - pow(sum1, 2.0) / n) *
                   (sum2Sq - pow(sum2, 2.0) / n))

        if den == 0.0:
            return 0.0

        return num / den
    else:
        # Using Value Mode.
        if len(vector1) != len(vector2):
            raise ValueError('Dimmensions vector1 != Dimmensions vector2')

        if len(vector1) == 0 or len(vector2) == 0:
            return 0.0

        sum1 = sum(vector1)
        sum2 = sum(vector2)

        sum1q = sum([pow(v, 2) for v in vector1])
        sum2q = sum([pow(v, 2) for v in vector2])

        pSum = sum([vector1[i] * vector2[i] for i in range(len(vector1))])

        num = pSum - (sum1 * sum2 / len(vector1))

        den = sqrt((sum1q - pow(sum1, 2) / len(vector1)) *
                   (sum2q - pow(sum2, 2) / len(vector1)))

        if den == 0.0:
            return 0.0

        return num / den


def sim_spearman(vector1, vector2, **args):
    '''
    Like  sim_pearson , but compares relative ranking of preference values
    instead of preference values themselves. That is, each user's preferences
    are sorted and then assign a rank as their preference value, with 1 being
    assigned to the least preferred item.

    Parameters:
        vector1: The vector you want to compare
        vector2: The second vector you want to compare
        args: optional arguments

    The value returned is in [0,1].

    '''

    if type(vector1) == type([]):
        raise TypeError('It still not yet implemented.')

    simP1 = {}
    simP2 = {}
    rank = 1.0

    # First order from the lowest to greatest value.
    vector1_items = sorted(vector1.items(), lambda x, y: cmp(x[1], y[1]))
    vector2_items = sorted(vector2.items(), lambda x, y: cmp(x[1], y[1]))

    for key, value in vector1_items:
        if key in vector2:
            simP1.update({key: rank})
            rank += 1

    rank = 1.0
    for key, values in vector2_items:
        if key in vector2:
            simP2.update({key: rank})
            rank += 1

    sumDiffSq = 0.0
    for key, rank in simP1.items():
        if key in simP2:
            sumDiffSq += pow((rank - simP2[key]), 2.0)

    n = len(simP1)

    if n == 0:
        return 0.0

    return 1.0 - ((6.0 * sumDiffSq) / (n * (n * n - 1)))


def sim_tanimoto(vector1, vector2, **args):
    '''
      An implementation of a "similarity" based on the Tanimoto coefficient,
    or extended Jaccard coefficient.

    This is intended for "binary" data sets where a user either expresses a
    generic "yes" preference for an item or has no preference. The actual
    preference values do not matter here, only their presence or absence.

    Parameters:
        the prefs: The preferences in dict format.
        person1: The user profile you want to compare
        person2: The second user profile you want to compare

    The value returned is in [0,1].

    '''
    simP1P2 = [item for item in vector1 if item in vector2]
    if len(simP1P2) == 0:
        return 0.0

    return float(len(simP1P2)) / (len(vector1) + len(vector2) - len(simP1P2))


def sim_cosine(vector1, vector2, **args):
    '''
     An implementation of the cosine similarity. The result is the cosine of
     the angle formed between the two preference vectors.  Note that this
     similarity does not "center" its data, shifts the user's preference values
     so that each of their means is 0. For this behavior, use Pearson
     Coefficient, which actually is mathematically equivalent for centered
     data.

    Parameters:
        vector1: The vector you want to compare
        vector2: The second vector you want to compare
        args: optional arguments

    The value returned is in [0,1].
    '''

    if len(vector1) == 0 or len(vector2) == 0:
        return 0.0

    # Using Content Mode.
    if type(vector1) == type({}):
        try:
            from numpy import dot, norm
            v = [(vector1[item], vector2[item]) for item in vector1
                 if item in vector2]
            vector1 = [vec[0] for vec in v]
            vector2 = [vec[1] for vec in v]
        except ImportError:
            def dot(p1, p2):
                return sum([p1.get(item, 0) * p2.get(item, 0) for item in p2])

            def norm(p):
                return sqrt(sum([p.get(item, 0) * p.get(item, 0)
                                 for item in p]))
    else:
        try:
            from numpy import dot, norm
        except ImportError:
            def dot(p1, p2):
                return sum([p1[i] * p2[i] for i in xrange(len(p1))])

            def norm(p):
                return sqrt(sum([p[i] * p[i] for i in xrange(len(p))]))

    return dot(vector1, vector2) / (norm(vector1) * norm(vector2))


def sim_loglikehood(n, vector1, vector2, **args):
    '''
    See http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.14.5962 and
    http://tdunning.blogspot.com/2008/03/surprise-and-coincidence.html .

    Parameters:
        n : Total  Number of items
        vector1: The vector you want to compare
        vector2: The second vector you want to compare
        args: optional arguments

    The value returned is in [0,1].
    '''

    def safeLog(d):
        if d <= 0.0:
            return 0.0
        else:
            return log(d)

    def logL(p, k, n):
        return k * safeLog(p) + (n - k) * safeLog(1.0 - p)

    def twoLogLambda(k1, k2, n1, n2):
        p = (k1 + k2) / (n1 + n2)
        return 2.0 * (logL(k1 / n1, k1, n1) + logL(k2 / n2, k2, n2)
                      - logL(p, k1, n1) - logL(p, k2, n2))

    # Using Content Mode.
    if type(vector1) == type({}):
        simP1P2 = {}
        [simP1P2.update({item: 1}) for item in vector1 if item in vector2]

        if len(simP1P2) == 0:
            return 0.0

        nP1P2 = len(simP1P2)
        nP1 = len(vector1)
        nP2 = len(vector2)
    else:
        nP1P2 = len([item  for item in vector1 if item in vector2])

        if nP1P2 == 0:
            return 0.0

        nP1 = len(vector1)
        nP2 = len(vector2)

    if (nP1 - nP1P2 == 0)  or (n - nP2 == 0):
        return 1.0

    logLikeliHood = twoLogLambda(float(nP1P2), float(nP1 - nP1P2),
                                 float(nP2), float(n - nP2))

    return 1.0 - 1.0 / (1.0 + float(logLikeliHood))


def sim_sorensen(vector1, vector2, **args):
    '''
    The Sørensen index, also known as Sørensen’s similarity coefficient, is a
    statistic used for comparing the similarity of two samples.  It was
    developed by the botanist Thorvald Sørensen and published in 1948.[1] See
    the link: http://en.wikipedia.org/wiki/S%C3%B8rensen_similarity_index

    This is intended for "binary" data sets where a user either expresses a
    generic "yes" preference for an item or has no preference. The actual
    preference values do not matter here, only their presence or absence.

    Parameters:
        vector1: The vector you want to compare
        vector2: The second vector you want to compare
        args: optional arguments

    The value returned is in [0,1].

    '''
    nP1P2 = len([item  for item in vector1 if item in vector2])

    if len(vector1) + len(vector2) == 0:
        return 0.0

    return float(2.0 * nP1P2 / (len(vector1) + len(vector2)))


def sim_manhattan(vector1, vector2, **args):
    """The distance between two points in a grid based on a strictly horizontal
    and/or vertical path (that is, along the grid lines as opposed to the
    diagonal or "as the crow flies" distance.  The Manhattan distance is the
    simple sum of the horizontal and vertical components, whereas the diagonal
    distance might be computed by applying the Pythagorean theorem.

    Parameters:
        vector1: The vector you want to compare
        vector2: The second vector you want to compare
        args: optional arguments

    The value returned is in [0,1].

    """
    # Content Mode
    if type(vector1) == type({}):
        nP1P2 = len([item  for item in vector1 if item in vector2])
        distance = sum([abs(vector1[key] - vector2[key])
                        for key in vector1 if key in vector2])
    else:
        nP1P2 = len(vector1)
        distance = sum([abs(vector1[i] - vector2[i])
                        for i in xrange(len(vector1))])

    if nP1P2 > 0:
        return 1 - (float(distance) / nP1P2)
    else:
        return 0.0


def sim_jaccard(vector1, vector2, **args):
    """
    Jaccard similarity coefficient is a statistic used for comparing the
    similarity and diversity of sample sets.  The Jaccard coefficient measures
    similarity between sample sets, and is defined as the size of the
    intersection divided by the size of the union of the sample sets.

    Parameters:
        vector1: The vector you want to compare
        vector2: The second vector you want to compare
        args: optional arguments

    The value returned is in [0,1].
    """

    # Content Mode
    if type(vector1) == type({}):
        simP1P2 = {}

        [simP1P2.update({item:1}) for item in vector1 if item in vector2]

        nP1P2 = len(simP1P2)
    else:
        nP1P2 = len([item  for item in vector1 if item in vector2])

    if len(vector1) == 0 and len(vector2) == 0:
        return 0.0

    return float(nP1P2) / (len(vector1) + len(vector2) - nP1P2)

########NEW FILE########
__FILENAME__ = models_test
#-*- coding:utf-8 -*-

'''

* Licensed to the Apache Software Foundation (ASF) under one or more
* contributor license agreements.  See the NOTICE file distributed with
* this work for additional information regarding copyright ownership.
* The ASF licenses this file to You under the Apache License, Version 2.0
* (the "License"); you may not use this file except in compliance with
* the License.  You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.


0.1 2010-11-01 Initial version.

'''

__author__ = 'marcel@orygens.com'

import unittest

from models.datamodel import *


class TestDictModel(unittest.TestCase):

    def setUp(self):
        # SIMILARITY BY RATES.
        self.movies = {
                'Marcel Caraciolo': {
                    'Lady in the Water': 2.5,
                    'Snakes on a Plane': 3.5,
                    'Just My Luck': 3.0,
                    'Superman Returns': 3.5,
                    'You, Me and Dupree': 2.5,
                    'The Night Listener': 3.0},
                'Luciana Nunes': {
                    'Lady in the Water': 3.0,
                    'Snakes on a Plane': 3.5,
                    'Just My Luck': 1.5,
                    'Superman Returns': 5.0,
                    'The Night Listener': 3.0,
                    'You, Me and Dupree': 3.5},
                'Leopoldo Pires': {
                    'Lady in the Water': 2.5,
                    'Snakes on a Plane': 3.0,
                    'Superman Returns': 3.5,
                    'The Night Listener': 4.0},
                'Lorena Abreu': {
                    'Snakes on a Plane': 3.5,
                    'Just My Luck': 3.0,
                    'The Night Listener': 4.5,
                    'Superman Returns': 4.0,
                    'You, Me and Dupree': 2.5},
                'Steve Gates': {
                    'Lady in the Water': 3.0,
                    'Snakes on a Plane': 4.0,
                    'Just My Luck': 2.0,
                    'Superman Returns': 3.0,
                    'The Night Listener': 3.0,
                    'You, Me and Dupree': 2.0},
                'Sheldom': {
                    'Lady in the Water': 3.0,
                    'Snakes on a Plane': 4.0,
                    'The Night Listener': 3.0,
                    'Superman Returns': 5.0,
                    'You, Me and Dupree': 3.5},
                'Penny Frewman': {
                    'Snakes on a Plane': 4.5,
                    'You, Me and Dupree': 1.0,
                    'Superman Returns': 4.0},
                'Maria Gabriela': {}}

    def test_create_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(self.movies, model.dataU)

    def test_UserIDs_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(
                ['Leopoldo Pires', 'Lorena Abreu', 'Luciana Nunes',
                 'Marcel Caraciolo', 'Maria Gabriela', 'Penny Frewman',
                 'Sheldom', 'Steve Gates'],
                model.UserIDs())

    def test_ItemIDs_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(
                ['Just My Luck', 'Lady in the Water', 'Snakes on a Plane',
                 'Superman Returns', 'The Night Listener',
                 'You, Me and Dupree'],
                model.ItemIDs())

    def test_PreferencesFromUser_Existing_UserDictModel(self):
        model = DictDataModel(self.movies)
        # Ordered by ItemID
        self.assertEquals([('Just My Luck', 3.0),
                           ('Snakes on a Plane', 3.5),
                           ('Superman Returns', 4.0),
                           ('The Night Listener', 4.5),
                           ('You, Me and Dupree', 2.5)],
                          model.PreferencesFromUser('Lorena Abreu'))
        # Ordered by Rate (Reverse)
        self.assertEquals([('The Night Listener', 4.5),
                           ('Superman Returns', 4.0),
                           ('Snakes on a Plane', 3.5),
                           ('Just My Luck', 3.0),
                           ('You, Me and Dupree', 2.5)],
                   model.PreferencesFromUser('Lorena Abreu', orderByID=False))

    def test_PreferencesFromUser_Existing_User_No_PreferencesDictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals([], model.PreferencesFromUser('Maria Gabriela'))

    def test_PreferencesFromUser_Non_Existing_User_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertRaises(ValueError, model.PreferencesFromUser, 'Flavia')

    def test_ItemIDsFromUser_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(['Just My Luck', 'Lady in the Water',
                           'Snakes on a Plane', 'Superman Returns',
                           'The Night Listener', 'You, Me and Dupree'],
                           model.ItemIDsFromUser('Marcel Caraciolo'))

    def test_PreferencesForItem_Existing_Item_DictModel(self):
        model = DictDataModel(self.movies)
        # Ordered by ItemID
        self.assertEquals([('Leopoldo Pires', 3.5),
                           ('Lorena Abreu', 4.0),
                           ('Luciana Nunes', 5.0),
                           ('Marcel Caraciolo', 3.5),
                           ('Penny Frewman', 4.0),
                           ('Sheldom', 5.0),
                           ('Steve Gates', 3.0)],
                          model.PreferencesForItem('Superman Returns'))
        # Ordered by Rate (Reverse)
        self.assertEquals([('Luciana Nunes', 5.0),
                           ('Sheldom', 5.0),
                           ('Penny Frewman', 4.0),
                           ('Lorena Abreu', 4.0),
                           ('Leopoldo Pires', 3.5),
                           ('Marcel Caraciolo', 3.5),
                           ('Steve Gates', 3.0)],
              model.PreferencesForItem('Superman Returns', orderByID=False))

    def test_PreferencesForItem_Existing_Item_No_PreferencesDictModel(self):
        model = DictDataModel(self.movies)
        # BUG ? If there is an item without rating in the model, it must return
        # [] or raise an Exception ?
        self.assertRaises(ValueError,
                model.PreferencesFromUser, 'Night Listener')

    def test_PreferencesForItem_Non_Existing_Item_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertRaises(ValueError,
                model.PreferencesFromUser, 'Back to the Future')

    def test_PreferenceValue_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(3.5,
                model.PreferenceValue('Marcel Caraciolo', 'Superman Returns'))

    def test_NumUsers_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(8, model.NumUsers())

    def test_NumItems_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(6, model.NumItems())

    def test_NumUsersWithPreferenceFor_Invalid_User_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertRaises(ValueError, model.NumUsersWithPreferenceFor)
        self.assertRaises(ValueError, model.NumUsersWithPreferenceFor,
                'SuperMan Returns', 'Just My Luck', 'Lady in The Water')
        self.assertRaises(ValueError, model.NumUsersWithPreferenceFor,
                'SuperMan Returns', 'Back to the future')

    def test_NumUsersWithPreferenceFor_One_User_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(7,
                model.NumUsersWithPreferenceFor('Superman Returns'))

    def test_NumUsersWithPreferenceFor_Two_Users_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(4, model.NumUsersWithPreferenceFor(
                    'Superman Returns', 'Just My Luck'))

    def test_hasPreferenceValues_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(True, model.hasPreferenceValues())

    def test_MaxPreference_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(5.0, model.MaxPreference())

    def test_MinPreference_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals(1.0, model.MinPreference())

    def test_get_item_DictModel(self):
        model = DictDataModel(self.movies)
        self.assertEquals([('Just My Luck', 3.0),
                           ('Lady in the Water', 2.5),
                           ('Snakes on a Plane', 3.5),
                           ('Superman Returns', 3.5),
                           ('The Night Listener', 3.0),
                           ('You, Me and Dupree', 2.5)],
                          model['Marcel Caraciolo'])

    def test_iter_DictModel(self):
        model = DictDataModel(self.movies)
        elements = [pref  for pref in model]
        self.assertEquals(('Leopoldo Pires', [('Lady in the Water', 2.5),
                                              ('Snakes on a Plane', 3.0),
                                              ('Superman Returns', 3.5),
                                              ('The Night Listener', 4.0)]),
                          elements[0])


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(TestDictModel))

    return suite

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = similarities_test
#-*- coding:utf-8 -*-

'''

* Licensed to the Apache Software Foundation (ASF) under one or more
* contributor license agreements.  See the NOTICE file distributed with
* this work for additional information regarding copyright ownership.
* The ASF licenses this file to You under the Apache License, Version 2.0
* (the "License"); you may not use this file except in compliance with
* the License.  You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.


0.1 2010-10-11 Initial version.
                Added tests for sim_euclidian, sim_pearson and sim_spearman
0.11 2010-10-13 Added tests for sim_tanimoto, sim_cosine
0.12 2010-10-17 Added tests for sim_loglikehood
0.13 2010-10-17 Added tests for sim_sorensen
0.14 2010-10-20 Added testes for sim_manhattan
0.15 2010-10-28 Added testes for sim_jaccard

'''

"""
:mod:`similarities_test` -- the similarity evaluation tests
================================================================


"""

__author__ = 'marcel@orygens.com'

import unittest

from similarities.similarity import *
from similarities.similarity_distance import *
from models.datamodel import *


class TestSimilarityDistance(unittest.TestCase):

    def setUp(self):

        # SIMILARITY BY RATES.
        movies = {'Marcel Caraciolo': {
                      'Lady in the Water': 2.5,
                      'Snakes on a Plane': 3.5,
                      'Just My Luck': 3.0,
                      'Superman Returns': 3.5,
                      'You, Me and Dupree': 2.5,
                      'The Night Listener': 3.0},
                  'Luciana Nunes': {
                      'Lady in the Water': 3.0,
                      'Snakes on a Plane': 3.5,
                      'Just My Luck': 1.5,
                      'Superman Returns': 5.0,
                      'The Night Listener': 3.0,
                      'You, Me and Dupree': 3.5},
                  'Leopoldo Pires': {
                      'Lady in the Water': 2.5,
                      'Snakes on a Plane': 3.0,
                      'Superman Returns': 3.5,
                      'The Night Listener': 4.0},
                  'Lorena Abreu': {
                      'Snakes on a Plane': 3.5,
                      'Just My Luck': 3.0,
                      'The Night Listener': 4.5,
                      'Superman Returns': 4.0,
                      'You, Me and Dupree': 2.5},
                  'Steve Gates': {
                      'Lady in the Water': 3.0,
                      'Snakes on a Plane': 4.0,
                      'Just My Luck': 2.0,
                      'Superman Returns': 3.0,
                      'The Night Listener': 3.0,
                      'You, Me and Dupree': 2.0},
                  'Sheldom': {
                      'Lady in the Water': 3.0,
                      'Snakes on a Plane': 4.0,
                      'The Night Listener': 3.0,
                      'Superman Returns': 5.0,
                      'You, Me and Dupree': 3.5},
                  'Penny Frewman': {
                      'Snakes on a Plane': 4.5,
                      'You, Me and Dupree': 1.0,
                      'Superman Returns': 4.0},
                  'Maria Gabriela': {}}

        self.model = DictDataModel(movies)

    # EUCLIDIAN Tests
    def test_dict_basic_rate_euclidian_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        self.assertAlmostEquals(0.29429805508554946,
                sim_euclidian(usr1Prefs, usr2Prefs))

    def test_identity_euclidian_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        self.assertAlmostEquals(1.0, sim_euclidian(usr1Prefs, usr2Prefs))

    def test_value_basic_rate_euclidian_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        vector = [(usr1Prefs[item], usr2Prefs[item])
                   for item in usr1Prefs if item in usr2Prefs]
        vector1 = [v1 for v1, v2 in vector]
        vector2 = [v2 for v1, v2 in vector]
        self.assertAlmostEquals(0.29429805508554946,
                sim_euclidian(vector1, vector2))

    def test_dict_empty_rate_euclidian_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Maria Gabriela'))
        self.assertAlmostEquals(0.0, sim_euclidian(usr1Prefs, usr2Prefs))

    def test_values_empty_rate_euclidian_similarity(self):
        self.assertAlmostEquals(0.0, sim_euclidian([], []))

    def test_different_sizes_values_rate_euclidian_similarity(self):
        self.assertRaises(ValueError, sim_euclidian, [3.5, 3.2], [2.0])

    # PEARSON Tests
    def test_dict_basic_rate_pearson_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        self.assertAlmostEquals(0.396059017, sim_pearson(usr1Prefs, usr2Prefs))

    def test_identity_pearson_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        self.assertAlmostEquals(1.0, sim_pearson(usr1Prefs, usr2Prefs))

    def test_value_basic_rate_pearson_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        vector = [(usr1Prefs[item], usr2Prefs[item])
                  for item in usr1Prefs if item in usr2Prefs]
        vector1 = [v1 for v1, v2 in vector]
        vector2 = [v2 for v1, v2 in vector]
        self.assertAlmostEquals(0.396059017, sim_pearson(vector1, vector2))

    def test_dict_empty_rate_pearson_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Maria Gabriela'))
        self.assertAlmostEquals(0.0, sim_pearson(usr1Prefs, usr2Prefs))

    def test_values_empty_rate_pearson_similarity(self):
        self.assertAlmostEquals(0.0, sim_pearson([], []))

    def test_different_sizes_values_rate_pearson_similarity(self):
        self.assertRaises(ValueError, sim_pearson, [3.5, 3.2], [2.0])

    # SPEARMAN Tests
    def test_identity_spearman_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        self.assertAlmostEquals(1.0, sim_spearman(usr1Prefs, usr2Prefs))

    def test_basic_rate_spearman_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        self.assertAlmostEquals(0.5428571428,
                sim_spearman(usr1Prefs, usr2Prefs))

    def test_empty_rate_spearman_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Maria Gabriela'))
        self.assertAlmostEquals(0.0, sim_spearman(usr1Prefs, usr2Prefs))

    def test_different_sizes_values_rate_pearson_similarity(self):
        self.assertRaises(TypeError, sim_spearman, [3.5, 3.2], [2.0])

    # TANIMOTO Tests

    def test_identity_tanimoto_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        self.assertAlmostEquals(1.0, sim_tanimoto(usr1Prefs, usr2Prefs))

    def test_dict_basic_rate_tanimoto_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        self.assertAlmostEquals(1.0, sim_tanimoto(usr1Prefs, usr2Prefs))

    def test_value_basic_rate_tanimoto_similarity(self):
        usr1Prefs = self.model.ItemIDsFromUser('Marcel Caraciolo')
        usr2Prefs = self.model.ItemIDsFromUser('Luciana Nunes')
        self.assertAlmostEquals(1.0, sim_tanimoto(usr1Prefs, usr2Prefs))

    def test_dict_empty_rate_tanimoto_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Maria Gabriela'))
        self.assertAlmostEquals(0.0, sim_tanimoto(usr1Prefs, usr2Prefs))

    def test_values_empty_rate_tanimoto_similarity(self):
        self.assertAlmostEquals(0.0, sim_tanimoto([], []))

    # COSINE Tests

    def test_identity_cosine_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        self.assertAlmostEquals(1.0, sim_cosine(usr1Prefs, usr2Prefs))

    def test_dict_basic_rate_cosine_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        self.assertAlmostEquals(0.960646301, sim_cosine(usr1Prefs, usr2Prefs))

    def test_values_basic_rate_cosine_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        vector = [(usr1Prefs[item], usr2Prefs[item])
                   for item in usr1Prefs if item in usr2Prefs]
        vector1 = [v1 for v1, v2 in vector]
        vector2 = [v2 for v1, v2 in vector]
        self.assertAlmostEquals(0.960646301, sim_cosine(vector1, vector2))

    def test_dict_empty_rate_cosine_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Maria Gabriela'))
        self.assertAlmostEquals(0.0, sim_cosine(usr1Prefs, usr2Prefs))

    def test_values_empty_rate_cosine_similarity(self):
        self.assertAlmostEquals(0.0, sim_cosine([], []))

    # LOGLIKEHOOD Tests

    def test_identity_sim_loglikehood_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        self.assertAlmostEquals(1.0,
                sim_loglikehood(self.model.NumItems(), usr1Prefs, usr2Prefs))

    def test_dict_basic_rate_sim_loglikehood_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Lorena Abreu'))
        self.assertAlmostEquals(0.0,
                sim_loglikehood(self.model.NumItems(), usr1Prefs, usr2Prefs))

    def test_values_basic_rate_sim_loglikehood_similarity(self):
        usr1Prefs = self.model.ItemIDsFromUser('Marcel Caraciolo')
        usr2Prefs = self.model.ItemIDsFromUser('Lorena Abreu')
        self.assertAlmostEquals(0.0,
                sim_loglikehood(self.model.NumItems(), usr1Prefs, usr2Prefs))

    def test_dict_empty_rate_sim_loglikehood_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Maria Gabriela'))
        self.assertAlmostEquals(0.0,
                sim_loglikehood(self.model.NumItems(), usr1Prefs, usr2Prefs))

    def test_values_empty_rate_sim_loglikehood_similarity(self):
        self.assertAlmostEquals(0.0,
                sim_loglikehood(self.model.NumItems(), [], []))

    # SORENSEN Tests

    def test_identity_rate_sorensen_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        self.assertAlmostEquals(1.0, sim_sorensen(usr1Prefs, usr2Prefs))

    def test_dict_basic_rate_sorensen_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        self.assertAlmostEquals(1.0, sim_sorensen(usr1Prefs, usr2Prefs))

    def test_values_basic_rate_sorensen_similarity(self):
        usr1Prefs = self.model.ItemIDsFromUser('Marcel Caraciolo')
        usr2Prefs = self.model.ItemIDsFromUser('Luciana Nunes')
        self.assertAlmostEquals(1.0, sim_sorensen(usr1Prefs, usr2Prefs))

    def test_dict_empty_rate_sorensen_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Maria Gabriela'))
        self.assertAlmostEquals(0.0, sim_sorensen(usr1Prefs, usr2Prefs))

    def test_values_empty_rate_sorensen_similarity(self):
        self.assertAlmostEquals(0.0, sim_sorensen([], []))

    # Manhanttan Tests

    def test_identity_rate_manhattan_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        self.assertAlmostEquals(1.0, sim_manhattan(usr1Prefs, usr2Prefs))

    def test_dict_basic_rate_manhattan_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        self.assertAlmostEquals(0.25, sim_manhattan(usr1Prefs, usr2Prefs))

    def test_values_basic_rate_manhattan_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        vector = [(usr1Prefs[item], usr2Prefs[item])
                  for item in usr1Prefs if item in usr2Prefs]
        vector1 = [v1 for v1, v2 in vector]
        vector2 = [v2 for v1, v2 in vector]
        self.assertAlmostEquals(0.25, sim_manhattan(vector1, vector2))

    def test_dict_empty_rate_manhattan_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Maria Gabriela'))
        self.assertAlmostEquals(0.0, sim_manhattan(usr1Prefs, usr2Prefs))

    def test_values_empty_rate_manhattan_similarity(self):
        self.assertAlmostEquals(0.0, sim_manhattan([], []))

    # Jaccard Tests

    def test_identity_rate_jaccard_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        self.assertAlmostEquals(1.0, sim_jaccard(usr1Prefs, usr2Prefs))

    def test_dict_basic_rate_jaccard_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Luciana Nunes'))
        self.assertAlmostEquals(1.0, sim_jaccard(usr1Prefs, usr2Prefs))

    def test_values_basic_rate_jaccard_similarity(self):
        usr1Prefs = self.model.ItemIDsFromUser('Marcel Caraciolo')
        usr2Prefs = self.model.ItemIDsFromUser('Luciana Nunes')
        self.assertAlmostEquals(1.0, sim_jaccard(usr1Prefs, usr2Prefs))

    def test_dict_empty_rate_jaccard_similarity(self):
        usr1Prefs = dict(self.model.PreferencesFromUser('Marcel Caraciolo'))
        usr2Prefs = dict(self.model.PreferencesFromUser('Maria Gabriela'))
        self.assertAlmostEquals(0.0, sim_jaccard(usr1Prefs, usr2Prefs))

    def test_values_empty_rate_jaccard_similarity(self):
        self.assertAlmostEquals(0.0, sim_jaccard([], []))


class TestUserSimilarity(unittest.TestCase):

    def setUp(self):
        # SIMILARITY BY RATES.
        movies = {
                'Marcel Caraciolo': {
                    'Lady in the Water': 2.5,
                    'Snakes on a Plane': 3.5,
                    'Just My Luck': 3.0,
                    'Superman Returns': 3.5,
                    'You, Me and Dupree': 2.5,
                    'The Night Listener': 3.0},
                'Luciana Nunes': {
                    'Lady in the Water': 3.0,
                    'Snakes on a Plane': 3.5,
                    'Just My Luck': 1.5,
                    'Superman Returns': 5.0,
                    'The Night Listener': 3.0,
                    'You, Me and Dupree': 3.5},
                'Leopoldo Pires': {
                    'Lady in the Water': 2.5,
                    'Snakes on a Plane': 3.0,
                    'Superman Returns': 3.5,
                    'The Night Listener': 4.0},
                'Lorena Abreu': {
                    'Snakes on a Plane': 3.5,
                    'Just My Luck': 3.0,
                    'The Night Listener': 4.5,
                    'Superman Returns': 4.0,
                    'You, Me and Dupree': 2.5},
                'Steve Gates': {
                    'Lady in the Water': 3.0,
                    'Snakes on a Plane': 4.0,
                    'Just My Luck': 2.0,
                    'Superman Returns': 3.0,
                    'The Night Listener': 3.0,
                    'You, Me and Dupree': 2.0},
                'Sheldom': {
                    'Lady in the Water': 3.0,
                    'Snakes on a Plane': 4.0,
                    'The Night Listener': 3.0,
                    'Superman Returns': 5.0,
                    'You, Me and Dupree': 3.5},
                'Penny Frewman': {
                    'Snakes on a Plane': 4.5,
                    'You, Me and Dupree': 1.0,
                    'Superman Returns': 4.0},
                'Maria Gabriela': {}}

        self.model = DictDataModel(movies)

    # User Basic Similarity
    def test_user_all_similarity(self):
        # Cosine
        matrix = UserSimilarity(self.model, sim_cosine, 3)
        self.assertEquals(
                [('Marcel Caraciolo', 1.0),
                 ('Steve Gates', 0.98183138566416928),
                 ('Luciana Nunes', 0.96064630139802409)],
                matrix['Marcel Caraciolo'])
        # Tanimoto
        matrix = UserSimilarity(self.model, sim_tanimoto, 4)
        self.assertEquals(
                [('Luciana Nunes', 1.0),
                 ('Marcel Caraciolo', 1.0),
                 ('Steve Gates', 1.0),
                 ('Lorena Abreu', 0.83333333333333337)],
                matrix['Marcel Caraciolo'])

    def test_user_one_similarity(self):
        matrix = UserSimilarity(self.model, sim_cosine, 3)
        self.assertAlmostEquals(0.960646301398,
                matrix.getSimilarity('Marcel Caraciolo', 'Luciana Nunes'))

    def test_user_empty_similarity(self):
        matrix = UserSimilarity(self.model, sim_cosine, 3)
        self.assertAlmostEquals(0.0,
                matrix.getSimilarity('Marcel Caraciolo', 'Maria Gabriela'))


class TestItemSimilarity(unittest.TestCase):

    def setUp(self):
        # SIMILARITY BY RATES.
        movies = {'Marcel Caraciolo': {
                      'Lady in the Water': 2.5,
                      'Snakes on a Plane': 3.5,
                      'Just My Luck': 3.0,
                      'Superman Returns': 3.5,
                      'You, Me and Dupree': 2.5,
                      'The Night Listener': 3.0},
                  'Luciana Nunes': {
                      'Lady in the Water': 3.0,
                      'Snakes on a Plane': 3.5,
                      'Just My Luck': 1.5,
                      'Superman Returns': 5.0,
                      'The Night Listener': 3.0,
                      'You, Me and Dupree': 3.5},
                  'Leopoldo Pires': {
                      'Lady in the Water': 2.5,
                      'Snakes on a Plane': 3.0,
                      'Superman Returns': 3.5,
                      'The Night Listener': 4.0},
                  'Lorena Abreu': {
                      'Snakes on a Plane': 3.5,
                      'Just My Luck': 3.0,
                      'The Night Listener': 4.5,
                      'Superman Returns': 4.0,
                      'You, Me and Dupree': 2.5},
                  'Steve Gates': {
                      'Lady in the Water': 3.0,
                      'Snakes on a Plane': 4.0,
                      'Just My Luck': 2.0,
                      'Superman Returns': 3.0,
                      'The Night Listener': 3.0,
                      'You, Me and Dupree': 2.0},
                  'Sheldom': {
                      'Lady in the Water': 3.0,
                      'Snakes on a Plane': 4.0,
                      'The Night Listener': 3.0,
                      'Superman Returns': 5.0,
                      'You, Me and Dupree': 3.5},
                  'Penny Frewman': {
                      'Snakes on a Plane': 4.5,
                      'You, Me and Dupree': 1.0,
                      'Superman Returns': 4.0},
        'Maria Gabriela': {}}

        self.model = DictDataModel(movies)

    # User Basic Similarity
    def test_item_all_similarity(self):
        # Cosine
        matrix = ItemSimilarity(self.model, sim_cosine, 3)
        self.assertEquals(
                [('Superman Returns', 1.0),
                 ('Snakes on a Plane', 0.97987805999365596),
                 ('You, Me and Dupree', 0.91530229603963964)],
                matrix['Superman Returns'])
        # Tanimoto
        matrix = ItemSimilarity(self.model, sim_tanimoto, 4)
        self.assertEquals(
                [('Snakes on a Plane', 1.0),
                 ('Superman Returns', 1.0),
                 ('The Night Listener', 0.8571428571428571),
                 ('You, Me and Dupree', 0.8571428571428571)],
                matrix['Superman Returns'])

    def test_item_one_similarity(self):
        matrix = ItemSimilarity(self.model, sim_cosine, 3)
        self.assertAlmostEquals(0.91530229603963964,
                matrix.getSimilarity('Superman Returns', 'You, Me and Dupree'))

    def test_item_empty_similarity(self):
        matrix = ItemSimilarity(self.model, sim_cosine, 3)
        self.assertAlmostEquals(0.97987805999365596,
                matrix.getSimilarity('Superman Returns', 'Snakes on a Plane'))


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(TestSimilarityDistance))
    suite.addTests(unittest.makeSuite(TestUserSimilarity))

    return suite

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_evaluator
#-*- coding:utf-8 -*-

'''

* Licensed to the Apache Software Foundation (ASF) under one or more
* contributor license agreements.  See the NOTICE file distributed with
* this work for additional information regarding copyright ownership.
* The ASF licenses this file to You under the Apache License, Version 2.0
* (the "License"); you may not use this file except in compliance with
* the License.  You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.


0.1 2010-11-08 Initial version.
'''

__author__ = 'marcel@orygens.com'

import unittest
import sys
from math import sqrt

sys.path.append('/Users/marcelcaraciolo/Desktop/crab/crab/crab')


from models.datamodel import *
from recommender.topmatches import *
from recommender.recommender import UserRecommender, ItemRecommender, SlopeOneRecommender
from recommender.utils import DiffStorage
from similarities.similarity import UserSimilarity, ItemSimilarity
from similarities.similarity_distance import *
from scoring.scorer import TanHScorer, NaiveScorer
from neighborhood.neighborhood import NearestNUserNeighborhood
from neighborhood.itemstrategies import  PreferredItemsNeighborhoodStrategy
from evaluation.statistics import *



class TestAverageAbsoluteDistanceRecommenderEvaluator(unittest.TestCase):
    def setUp(self):
        #SIMILARITY BY RATES.
        movies={'Marcel Caraciolo': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
         'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 
         'The Night Listener': 3.0},
        'Luciana Nunes': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 
         'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0, 
         'You, Me and Dupree': 3.5}, 
        'Leopoldo Pires': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
         'Superman Returns': 3.5, 'The Night Listener': 4.0},
        'Lorena Abreu': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
         'The Night Listener': 4.5, 'Superman Returns': 4.0, 
         'You, Me and Dupree': 2.5},
        'Steve Gates': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 
         'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
         'You, Me and Dupree': 2.0}, 
        'Sheldom': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
         'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},
        'Penny Frewman': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0},
        'Maria Gabriela': {}}

        self.model = DictDataModel(movies)
        self.similarity = UserSimilarity(self.model,sim_euclidian)
        self.neighbor = NearestNUserNeighborhood(self.similarity,self.model,4,0.0)
        self.similarity_item = ItemSimilarity(self.model,sim_euclidian)
        self.strategy = PreferredItemsNeighborhoodStrategy()

    def test_Create_AvgAbsDistanceRecSys(self):
        evaluator = AverageAbsoluteDifferenceRecommenderEvaluator()
        self.assertEquals(evaluator.minPreference,0.0)
        self.assertEquals(evaluator.maxPreference,5.0)
  
    def test_evaluate_AvgAbsDistanceRecSys(self):
        evaluator = AverageAbsoluteDifferenceRecommenderEvaluator()
        
        recommender  = UserRecommender(self.model,self.similarity,self.neighbor,True)
        evaluationPercentage = 1.0
        trainingPercentage = 0.7
    
        numUsers = self.model.NumUsers()
        trainingUsers = {}
        testUserPrefs = {}
        self.total = 0
        self.diffs = 0.0

        for userID in self.model.UserIDs():
            if random() < evaluationPercentage:
                evaluator.processOneUser(trainingPercentage,trainingUsers,testUserPrefs,userID,self.model)        

        total_training =  sum([ len([pref  for pref in prefs]) for user,prefs in trainingUsers.iteritems()])
        total_testing =  sum([ len([pref  for pref in prefs]) for user,prefs in testUserPrefs.iteritems()])
        
        #self.assertAlmostEquals(total_training/float(total_training+total_testing), 0.7)
        #self.assertAlmostEquals(total_testing/float(total_training+total_testing), 0.3)
        
        
        trainingModel = DictDataModel(trainingUsers)
        
        self.assertEquals(sorted(trainingModel.UserIDs()), sorted([user for user in trainingUsers]))

        recommender.model = trainingModel

        self.assertEquals(recommender.model,trainingModel)
        
        for userID,prefs in testUserPrefs.iteritems():
            estimatedPreference = None
            for pref in prefs:
                try:
                    estimatedPreference = recommender.estimatePreference(userID=userID,similarity=self.similarity,itemID=pref)
                except:
                    pass
                if estimatedPreference is not None:
                    estimatedPreference = evaluator.capEstimatePreference(estimatedPreference)
                    self.assert_(estimatedPreference <= evaluator.maxPreference and estimatedPreference >= evaluator.minPreference)
                    self.diffs +=  abs(prefs[pref] - estimatedPreference)
                    self.total += 1
        
  
        result = self.diffs / float(self.total)


    def test_User_AvgDistanceRecSys(self):
        evaluator = AverageAbsoluteDifferenceRecommenderEvaluator()
        recommender  = UserRecommender(self.model,self.similarity,self.neighbor,True)
        result = evaluator.evaluate(recommender,self.model,0.7,1.0)
        #print result
    
    def test_Item_AvgDistanceRecSys(self):
        evaluator = AverageAbsoluteDifferenceRecommenderEvaluator()
        recommender = ItemRecommender(self.model,self.similarity_item,self.strategy,False)
        result = evaluator.evaluate(recommender,self.model,0.7,1.0)
        #print result

    def test_Slope_AvgDistanceRecSys(self):
        evaluator = AverageAbsoluteDifferenceRecommenderEvaluator()
        recommender = SlopeOneRecommender(self.model,True,False,False)
        result = evaluator.evaluate(recommender,self.model,0.7,1.0)
        #print result

    def test_limits_AvgDistanceRecSys(self):
        evaluator = AverageAbsoluteDifferenceRecommenderEvaluator()
        recommender = SlopeOneRecommender(self.model,True,False,False)
        self.assertRaises(Exception,evaluator.evaluate,recommender,self.model,1.3,-0.3)


class TestRMSRecommenderEvaluator(unittest.TestCase):
    
    def setUp(self):
        #SIMILARITY BY RATES.
        movies={'Marcel Caraciolo': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
         'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 
         'The Night Listener': 3.0},
        'Luciana Nunes': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 
         'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0, 
         'You, Me and Dupree': 3.5}, 
        'Leopoldo Pires': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
         'Superman Returns': 3.5, 'The Night Listener': 4.0},
        'Lorena Abreu': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
         'The Night Listener': 4.5, 'Superman Returns': 4.0, 
         'You, Me and Dupree': 2.5},
        'Steve Gates': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 
         'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
         'You, Me and Dupree': 2.0}, 
        'Sheldom': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
         'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},
        'Penny Frewman': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0},
        'Maria Gabriela': {}}

        self.model = DictDataModel(movies)
        self.similarity = UserSimilarity(self.model,sim_euclidian)
        self.neighbor = NearestNUserNeighborhood(self.similarity,self.model,4,0.0)
        self.similarity_item = ItemSimilarity(self.model,sim_euclidian)
        self.strategy = PreferredItemsNeighborhoodStrategy()

    def test_Create_RMSRecommenderEvaluator(self):
        evaluator = RMSRecommenderEvaluator()
        self.assertEquals(evaluator.minPreference,0.0)
        self.assertEquals(evaluator.maxPreference,5.0)
  
    def test_evaluate_RMSRecommenderEvaluator(self):
        evaluator = RMSRecommenderEvaluator()
        
        recommender  = UserRecommender(self.model,self.similarity,self.neighbor,True)
        evaluationPercentage = 1.0
        trainingPercentage = 0.7
    
        numUsers = self.model.NumUsers()
        trainingUsers = {}
        testUserPrefs = {}
        self.total = 0
        self.diffs = 0.0

        for userID in self.model.UserIDs():
            if random() < evaluationPercentage:
                evaluator.processOneUser(trainingPercentage,trainingUsers,testUserPrefs,userID,self.model)        

        total_training =  sum([ len([pref  for pref in prefs]) for user,prefs in trainingUsers.iteritems()])
        total_testing =  sum([ len([pref  for pref in prefs]) for user,prefs in testUserPrefs.iteritems()])
        
        #self.assertAlmostEquals(total_training/float(total_training+total_testing), 0.7)
        #self.assertAlmostEquals(total_testing/float(total_training+total_testing), 0.3)
        
        
        trainingModel = DictDataModel(trainingUsers)
        
        self.assertEquals(sorted(trainingModel.UserIDs()), sorted([user for user in trainingUsers]))

        recommender.model = trainingModel

        self.assertEquals(recommender.model,trainingModel)
        
        for userID,prefs in testUserPrefs.iteritems():
            estimatedPreference = None
            for pref in prefs:
                try:
                    estimatedPreference = recommender.estimatePreference(userID=userID,similarity=self.similarity,itemID=pref)
                except:
                    pass
                if estimatedPreference is not None:
                    estimatedPreference = evaluator.capEstimatePreference(estimatedPreference)
                    self.assert_(estimatedPreference <= evaluator.maxPreference and estimatedPreference >= evaluator.minPreference)
                    diff =  prefs[pref] - estimatedPreference
                    self.diffs+= (diff * diff)
                    self.total += 1
        
  
        result = sqrt(self.diffs / float(self.total))


    def test_User_RMSRecommenderEvaluator(self):
        evaluator = RMSRecommenderEvaluator()
        recommender  = UserRecommender(self.model,self.similarity,self.neighbor,True)
        result = evaluator.evaluate(recommender,self.model,0.7,1.0)
        #print result
    
    def test_Item_RMSRecommenderEvaluator(self):
        evaluator = RMSRecommenderEvaluator()
        recommender = ItemRecommender(self.model,self.similarity_item,self.strategy,False)
        result = evaluator.evaluate(recommender,self.model,0.7,1.0)
        #print result

    def test_Slope_RMSRecommenderEvaluator(self):
        evaluator = RMSRecommenderEvaluator()
        recommender = SlopeOneRecommender(self.model,True,False,False)
        result = evaluator.evaluate(recommender,self.model,0.7,1.0)
        #print result

    def test_limits_RMSRecommenderEvaluator(self):
        evaluator = RMSRecommenderEvaluator()
        recommender = SlopeOneRecommender(self.model,True,False,False)
        self.assertRaises(Exception,evaluator.evaluate,recommender,self.model,1.3,-0.3)



class TestIRStatsRecommenderEvaluator(unittest.TestCase):

    def setUp(self):
        #SIMILARITY BY RATES.
        movies={'Marcel Caraciolo': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
         'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 
         'The Night Listener': 3.0},
        'Luciana Nunes': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 
         'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0, 
         'You, Me and Dupree': 3.5}, 
        'Leopoldo Pires': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
         'Superman Returns': 3.5, 'The Night Listener': 4.0},
        'Lorena Abreu': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
         'The Night Listener': 4.5, 'Superman Returns': 4.0, 
         'You, Me and Dupree': 2.5},
        'Steve Gates': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 
         'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
         'You, Me and Dupree': 2.0}, 
        'Sheldom': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
         'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},
        'Penny Frewman': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0},
        'Maria Gabriela': {}}

        self.model = DictDataModel(movies)
        self.similarity = UserSimilarity(self.model,sim_euclidian)
        self.neighbor = NearestNUserNeighborhood(self.similarity,self.model,4,0.0)
        self.similarity_item = ItemSimilarity(self.model,sim_euclidian)
        self.strategy = PreferredItemsNeighborhoodStrategy()

    def test_Create_IRStatsRecommenderEvaluator(self):
        evaluator = IRStatsRecommenderEvaluator()
        self.assertEquals(evaluator.minPreference,0.0)
        self.assertEquals(evaluator.maxPreference,5.0)

    def test_evaluate_at_not_enough_IRStatsRecommenderEvaluator(self):
        evaluator = IRStatsRecommenderEvaluator()
        recommender  = UserRecommender(self.model,self.similarity,self.neighbor,True)
        result = evaluator.evaluate(recommender,self.model,4,1.0)
        self.assertEquals(result,{'nDCG': None, 'recall': None, 'f1Score': None, 'precision': None, 'fallOut': None})

    def test_User_IRStatsRecommenderEvaluator(self):
        evaluator = IRStatsRecommenderEvaluator()
        recommender  = UserRecommender(self.model,self.similarity,self.neighbor,True)
        result = evaluator.evaluate(recommender,self.model,2,1.0)
        #print result

    def test_Item_IRStatsRecommenderEvaluator(self):
        evaluator = IRStatsRecommenderEvaluator()
        recommender = ItemRecommender(self.model,self.similarity_item,self.strategy,False)
        result = evaluator.evaluate(recommender,self.model,2,1.0)
        print result

    def test_Slope_IRStatsRecommenderEvaluator(self):
        evaluator = IRStatsRecommenderEvaluator()
        recommender = SlopeOneRecommender(self.model,True,False,False)
        result = evaluator.evaluate(recommender,self.model,2,1.0)
        print result


    def test_evaluate_IRStatsRecommenderEvaluator(self):
        evaluator = IRStatsRecommenderEvaluator()

        recommender  = UserRecommender(self.model,self.similarity,self.neighbor,True)
        evaluationPercentage = 1.0
        relevanceThreshold = None
        at = 2
              
        irStats = {'precision': 0.0, 'recall': 0.0, 'fallOut': 0.0, 'nDCG': 0.0}
        irFreqs = {'precision': 0, 'recall': 0, 'fallOut': 0, 'nDCG': 0}
        
        nItems = self.model.NumItems()
        self.assertEquals(nItems,6)


        for userID in self.model.UserIDs():
            if random() < evaluationPercentage:
                prefs = self.model.PreferencesFromUser(userID)
                if len(prefs)  < 2 * at:
                    #Really not enough prefs to meaningfully evaluate the user
                    self.assert_(userID in ['Leopoldo Pires', 'Penny Frewman', 'Maria Gabriela'])
                    continue 
                
                relevantItemIDs = []
                
                #List some most-preferred items that would count as most relevant results
                relevanceThreshold =  relevanceThreshold if relevanceThreshold else  evaluator.computeThreshold(prefs)
                
                prefs = sorted(prefs,key=lambda x: x[1], reverse=True)
                
                self.assertEquals(max([pref[1] for pref in prefs]), prefs[0][1])
                
                for index,pref in enumerate(prefs):
                    if index < at:
                        if pref[1] >= relevanceThreshold:
                            relevantItemIDs.append(pref[0])
                
                self.assertEquals(relevantItemIDs, [ p[0] for p in sorted([ pref for pref in prefs if pref[1] >= relevanceThreshold],key=lambda x: x[1], reverse=True)[:at] ] )    
                

                if len(relevantItemIDs) == 0:
                    continue
                
                trainingUsers = {}
                for otherUserID in self.model.UserIDs():
                    evaluator.processOtherUser(userID,relevantItemIDs,trainingUsers,otherUserID,self.model)
                
                

                trainingModel = DictDataModel(trainingUsers)
                
                recommender.model = trainingModel
                
                try:
                    prefs = trainingModel.PreferencesFromUser(userID)
                    if not prefs:
                        continue
                except:
                    #Excluded all prefs for the user. move on.
                    continue
                
                recommendedItems = recommender.recommend(userID,at)


                self.assert_(len(recommendedItems)<= 2)

                intersectionSize = len([ recommendedItem  for recommendedItem in recommendedItems if recommendedItem in relevantItemIDs])
                
                
                #Precision
                if len(recommendedItems) > 0:
                    irStats['precision']+= (intersectionSize / float(len(recommendedItems)))
                    irFreqs['precision']+=1
                    
                #Recall
                irStats['recall'] += (intersectionSize/ float(len(relevantItemIDs)))
                irFreqs['recall']+=1
                
                #Fall-Out
                if len(relevantItemIDs) < len(prefs):
                    irStats['fallOut'] +=   (len(recommendedItems)  - intersectionSize) / float( nItems - len(relevantItemIDs))
                    irFreqs['fallOut'] +=1

                    
                #nDCG
                #In computing , assume relevant IDs have relevance 1 and others 0.
                cumulativeGain = 0.0
                idealizedGain = 0.0
                for index,recommendedItem in enumerate(recommendedItems):
                    discount =  1.0 if index == 0 else 1.0/ evaluator.log2(index+1)
                    if recommendedItem in relevantItemIDs:
                        cumulativeGain+=discount
                    #Otherwise we are multiplying discount by relevance 0 so it does nothing.
                    #Ideally results would be ordered with all relevant ones first, so this theoretical
                    #ideal list starts with number of relevant items equal to the total number of relevant items
                    if index < len(relevantItemIDs):
                        idealizedGain+= discount
                irStats['nDCG'] +=  float(cumulativeGain) / idealizedGain
                irFreqs['nDCG'] +=1
        
        for key in irFreqs:
            irStats[key] = irStats[key] / float(irFreqs[key])

        sum_score = irStats['precision'] + irStats['recall']  if irStats['precision'] is not None and irStats['recall'] is not None else None
        irStats['f1Score'] =   None   if not sum_score else (2.0) * irStats['precision'] * irStats['recall'] / sum_score 

        #print irStats



    def test_limits_RMSRecommenderEvaluator(self):
        evaluator = RMSRecommenderEvaluator()
        recommender = SlopeOneRecommender(self.model,True,False,False)
        self.assertRaises(Exception,evaluator.evaluate,recommender,self.model,0,-0.3)


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(TestAverageAbsoluteDistanceRecommenderEvaluator))
    suite.addTests(unittest.makeSuite(TestRMSRecommenderEvaluator))
    suite.addTests(unittest.makeSuite(TestIRStatsRecommenderEvaluator))
    return suite

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_itemstrategies
#-*- coding:utf-8 -*-

'''

* Licensed to the Apache Software Foundation (ASF) under one or more
* contributor license agreements.  See the NOTICE file distributed with
* this work for additional information regarding copyright ownership.
* The ASF licenses this file to You under the Apache License, Version 2.0
* (the "License"); you may not use this file except in compliance with
* the License.  You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.


0.1 2010-11-16 Initial version.
'''

__author__ = 'marcel@orygens.com'

import unittest

from models.datamodel import *
from neighborhood.itemstrategies import PreferredItemsNeighborhoodStrategy


class TestPreferredItemsNeighborhoodStrategy(unittest.TestCase):
	
	def setUp(self):
		#SIMILARITY BY RATES.
		movies={'Marcel Caraciolo': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
		 'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 
		 'The Night Listener': 3.0},
		'Luciana Nunes': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 
		 'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0, 
		 'You, Me and Dupree': 3.5}, 
		'Leopoldo Pires': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
		 'Superman Returns': 3.5, 'The Night Listener': 4.0},
		'Lorena Abreu': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
		 'The Night Listener': 4.5, 'Superman Returns': 4.0, 
		 'You, Me and Dupree': 2.5},
		'Steve Gates': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 
		 'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
		 'You, Me and Dupree': 2.0}, 
		'Sheldom': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
		 'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},
		'Penny Frewman': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0},
		'Maria Gabriela': {}}

		self.model = DictDataModel(movies)

	
	
	def test_empty_candidateItems(self):
		userID = 'Maria Gabriela'
		strategy = PreferredItemsNeighborhoodStrategy()
		self.assertEquals([],strategy.candidateItems(userID,self.model))


	def test_full_candidateItems(self):
		userID = 'Marcel Caraciolo'
		strategy = PreferredItemsNeighborhoodStrategy()
		self.assertEquals([],strategy.candidateItems(userID,self.model))
		

	def test_semi_candidateItems(self):
		userID = 'Leopoldo Pires'
		strategy = PreferredItemsNeighborhoodStrategy()
		self.assertEquals(['Just My Luck', 'You, Me and Dupree'],strategy.candidateItems(userID,self.model))
		

	def suite():
		suite = unittest.TestSuite()
		suite.addTests(unittest.makeSuite(TestNearestNUserNeighborhood))

		return suite

if __name__ == '__main__':
	unittest.main()
########NEW FILE########
__FILENAME__ = test_neighborhood
#-*- coding:utf-8 -*-

'''

* Licensed to the Apache Software Foundation (ASF) under one or more
* contributor license agreements.  See the NOTICE file distributed with
* this work for additional information regarding copyright ownership.
* The ASF licenses this file to You under the Apache License, Version 2.0
* (the "License"); you may not use this file except in compliance with
* the License.  You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.


0.1 2010-11-08 Initial version.
'''

__author__ = 'marcel@orygens.com'

import unittest

from models.datamodel import *
from neighborhood.neighborhood import NearestNUserNeighborhood
from similarities.similarity import UserSimilarity
from similarities.similarity_distance import *
from scoring.scorer import TanHScorer, NaiveScorer

class TestNearestNUserNeighborhood(unittest.TestCase):
	
	def setUp(self):
		#SIMILARITY BY RATES.
		movies={'Marcel Caraciolo': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
		 'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 
		 'The Night Listener': 3.0},
		'Luciana Nunes': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 
		 'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0, 
		 'You, Me and Dupree': 3.5}, 
		'Leopoldo Pires': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
		 'Superman Returns': 3.5, 'The Night Listener': 4.0},
		'Lorena Abreu': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
		 'The Night Listener': 4.5, 'Superman Returns': 4.0, 
		 'You, Me and Dupree': 2.5},
		'Steve Gates': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 
		 'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
		 'You, Me and Dupree': 2.0}, 
		'Sheldom': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
		 'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},
		'Penny Frewman': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0},
		'Maria Gabriela': {}}

		self.model = DictDataModel(movies)
		self.similarity = UserSimilarity(self.model,sim_euclidian)
	
	
	def test_create_nearestNUserNeighborhood(self):
		numUsers = 4
		minSimilarity = 0.5
		samplingRate = 0.4
		n = NearestNUserNeighborhood(self.similarity,self.model,numUsers,minSimilarity,samplingRate)				
		self.assertEquals(n.similarity,self.similarity)
		self.assertEquals(n.samplingRate,samplingRate)
		self.assertEquals(n.numUsers,numUsers)
		self.assertEquals(self.model,n.model)
		
	def test_maximum_limit_getSampleUserIDs(self):
		numUsers = 9
		minSimilarity = 0.0
		n = NearestNUserNeighborhood(self.similarity,self.model,numUsers,minSimilarity)				
		self.assertEquals(8,n.numUsers)

	def test_min_numUsers_getSampleUserIDs(self):
		numUsers = 4
		minSimilarity = 0.0
		n = NearestNUserNeighborhood(self.similarity,self.model,numUsers,minSimilarity)				
		self.assertEquals(8,len(n.getSampleUserIDs()))

	def test_sampling_rate_getSampleUserIDs(self):
		numUsers = 4
		minSimilarity = 0.0
		samplingRate = 0.4
		n = NearestNUserNeighborhood(self.similarity,self.model,numUsers,minSimilarity,samplingRate)				
		self.assertEquals(3,len(n.getSampleUserIDs()))
		
	def test_empty_sampling_rate_getSampleUserIDs(self):
		numUsers = 4
		minSimilarity = 0.0
		samplingRate = 0.0
		n = NearestNUserNeighborhood(self.similarity,self.model,numUsers,minSimilarity,samplingRate)				
		self.assertEquals(0,len(n.getSampleUserIDs()))
	
	def test_estimatePreference(self):
		numUsers = 4
		userID = 'Marcel Caraciolo'
		otherUserID = 'Luciana Nunes'
		minSimilarity = 0.0
		n = NearestNUserNeighborhood(self.similarity,self.model,numUsers,minSimilarity)
		self.assertAlmostEquals(0.294298055,n.estimatePreference(thingID=userID,similarity=self.similarity,otherUserID=otherUserID))

	def test_identity_estimatePreference(self):
		numUsers = 4
		userID = 'Marcel Caraciolo'
		otherUserID = 'Marcel Caraciolo'
		minSimilarity = 0.0
		n = NearestNUserNeighborhood(self.similarity,self.model,numUsers,minSimilarity)
		self.assertEquals(None,n.estimatePreference(thingID=userID,similarity=self.similarity,otherUserID=otherUserID))

	def test_user_dissimilar_estimatePreference(self):
		numUsers = 4
		userID = 'Marcel Caraciolo'
		otherUserID = 'Maria Gabriela'
		minSimilarity = 0.0
		n = NearestNUserNeighborhood(self.similarity,self.model,numUsers,minSimilarity)
		self.assertAlmostEquals(0.0,n.estimatePreference(thingID=userID,similarity=self.similarity,otherUserID=otherUserID))

	def test_otherUserNeighborhood(self):
		numUsers = 4
		userID = 'Luciana Nunes'
		minSimilarity = 0.0
		scorer = TanHScorer()
		n = NearestNUserNeighborhood(self.similarity,self.model,numUsers,minSimilarity)
		self.assertEquals(['Maria Gabriela', 'Penny Frewman', 'Steve Gates', 'Lorena Abreu'],n.userNeighborhood(userID,scorer))
		
	def test_userNeighborhood(self):
		numUsers = 4
		userID = 'Marcel Caraciolo'
		minSimilarity = 0.0
		scorer =  NaiveScorer()
		self.similarity = UserSimilarity(self.model,sim_tanimoto)
		n = NearestNUserNeighborhood(self.similarity,self.model,numUsers,minSimilarity)
		self.assertEquals(['Luciana Nunes', 'Steve Gates', 'Lorena Abreu', 'Sheldom'],n.userNeighborhood(userID,scorer))

	def test_invalid_UserID_userNeighborhood(self):
		numUsers = 4
		userID = 'Marcel'
		minSimilarity = 0.0
		scorer =  NaiveScorer()
		self.similarity = UserSimilarity(self.model,sim_tanimoto)
		n = NearestNUserNeighborhood(self.similarity,self.model,numUsers,minSimilarity)
		self.assertRaises(ValueError,n.userNeighborhood,userID,scorer)

	
	def suite():
		suite = unittest.TestSuite()
		suite.addTests(unittest.makeSuite(TestNearestNUserNeighborhood))

		return suite

if __name__ == '__main__':
	unittest.main()
########NEW FILE########
__FILENAME__ = test_recommender
#-*- coding:utf-8 -*-

'''

* Licensed to the Apache Software Foundation (ASF) under one or more
* contributor license agreements.  See the NOTICE file distributed with
* this work for additional information regarding copyright ownership.
* The ASF licenses this file to You under the Apache License, Version 2.0
* (the "License"); you may not use this file except in compliance with
* the License.  You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.


0.1 2010-11-08 Initial version.
'''

__author__ = 'marcel@orygens.com'

import unittest
import sys


from models.datamodel import *
from recommender.topmatches import *
from recommender.recommender import UserRecommender, ItemRecommender, SlopeOneRecommender
from recommender.utils import DiffStorage
from similarities.similarity import UserSimilarity, ItemSimilarity
from similarities.similarity_distance import *
from scoring.scorer import TanHScorer, NaiveScorer
from neighborhood.neighborhood import NearestNUserNeighborhood
from neighborhood.itemstrategies import  PreferredItemsNeighborhoodStrategy


class TestUserBasedRecommender(unittest.TestCase):
	
	def setUp(self):
		#SIMILARITY BY RATES.
		movies={'Marcel Caraciolo': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
		 'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 
		 'The Night Listener': 3.0},
		'Luciana Nunes': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 
		 'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0, 
		 'You, Me and Dupree': 3.5}, 
		'Leopoldo Pires': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
		 'Superman Returns': 3.5, 'The Night Listener': 4.0},
		'Lorena Abreu': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
		 'The Night Listener': 4.5, 'Superman Returns': 4.0, 
		 'You, Me and Dupree': 2.5},
		'Steve Gates': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 
		 'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
		 'You, Me and Dupree': 2.0}, 
		'Sheldom': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
		 'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},
		'Penny Frewman': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0},
		'Maria Gabriela': {}}

		self.model = DictDataModel(movies)
		self.similarity = UserSimilarity(self.model,sim_euclidian)
		self.neighbor = NearestNUserNeighborhood(self.similarity,self.model,4,0.0)
		
	
	def test_create_UserBasedRecommender(self):
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,True)
		self.assertEquals(recSys.similarity,self.similarity)
		self.assertEquals(recSys.capper,True)
		self.assertEquals(recSys.neighborhood,self.neighbor)
		self.assertEquals(recSys.model,self.model)
	
	
	def test_all_watched_allOtherItems(self):
		userID = 'Luciana Nunes'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,True)
		nearestN = self.neighbor.userNeighborhood(userID)
		self.assertEquals([],recSys.allOtherItems(userID,nearestN))	
		
	def test_semi_watched_allOtherItems(self):
		userID = 'Leopoldo Pires'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,True)
		nearestN = self.neighbor.userNeighborhood(userID)
		self.assertEquals(['Just My Luck', 'You, Me and Dupree'],recSys.allOtherItems(userID,nearestN))	

	def test_non_watched_allOtherItems(self):
		userID = 'Maria Gabriela'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,True)
		nearestN = self.neighbor.userNeighborhood(userID)
		self.assertEquals(['Lady in the Water', 'Snakes on a Plane', 'Just My Luck', 'Superman Returns', 
							'You, Me and Dupree', 'The Night Listener'],recSys.allOtherItems(userID,nearestN))

	def test_mostSimilarUserIDs(self):
		userID = 'Marcel Caraciolo'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,True)
		self.assertEquals(['Leopoldo Pires', 'Steve Gates', 'Lorena Abreu', 'Penny Frewman'],recSys.mostSimilarUserIDs(userID,4))	
	
	def test_user_no_preference_mostSimilarUserIDs(self):
		userID = 'Maria Gabriela'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,True)
		self.assertEquals(['Leopoldo Pires', 'Lorena Abreu', 'Luciana Nunes', 'Marcel Caraciolo'],recSys.mostSimilarUserIDs(userID,4))
	
	
	def test_empty_mostSimilarUserIDs(self):
		userID = 'Maria Gabriela'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,True)
		self.assertEquals([],recSys.mostSimilarUserIDs(userID,0))
	
	def test_local_estimatePreference(self):
		userID = 'Marcel Caraciolo'
		itemID = 'Superman Returns'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,True)
		self.assertAlmostEquals(3.5,recSys.estimatePreference(userID=userID,similarity=self.similarity,itemID=itemID))
		
		
	def test_local_not_existing_estimatePreference(self):
		userID = 'Leopoldo Pires'
		itemID = 'You, Me and Dupree'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,True)
		self.assertAlmostEquals(2.065394689,recSys.estimatePreference(userID=userID,similarity=self.similarity,itemID=itemID))
		

	def test_local_not_existing_capper_False_estimatePreference(self):
		userID = 'Leopoldo Pires'
		itemID = 'You, Me and Dupree'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,False)
		self.assertAlmostEquals(2.065394689,recSys.estimatePreference(userID=userID,similarity=self.similarity,itemID=itemID))
	
	
	def test_local_not_existing_rescorer_estimatePreference(self):
		userID = 'Leopoldo Pires'
		itemID = 'You, Me and Dupree'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,False)
		scorer = TanHScorer()
		self.assertAlmostEquals(2.5761016605,recSys.estimatePreference(userID=userID,similarity=self.similarity,itemID=itemID,rescorer=scorer))

	def test_recommend(self):
		userID = 'Leopoldo Pires'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,False)
		self.assertEquals(['Just My Luck', 'You, Me and Dupree'],recSys.recommend(userID,4))
		
	
	def test_empty_recommend(self):
		userID = 'Marcel Caraciolo'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,False)
		self.assertEquals([],recSys.recommend(userID,4))
	
	def test_full_recommend(self):
		userID = 'Maria Gabriela'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,False)
		self.assertEquals([],recSys.recommend(userID,4))

	def test_semi_recommend(self):
		userID = 'Leopoldo Pires'
		recSys = UserRecommender(self.model,self.similarity,self.neighbor,False)
		self.assertEquals(['Just My Luck'],recSys.recommend(userID,1))
		
		
		
class TestSlopeOneRecommender(unittest.TestCase):
	
	def setUp(self):
		#SIMILARITY BY RATES.
		movies={'Marcel Caraciolo': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
		 'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 
		 'The Night Listener': 3.0},
		'Luciana Nunes': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 
		 'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0, 
		 'You, Me and Dupree': 3.5}, 
		'Leopoldo Pires': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
		 'Superman Returns': 3.5, 'The Night Listener': 4.0},
		'Lorena Abreu': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
		 'The Night Listener': 4.5, 'Superman Returns': 4.0, 
		 'You, Me and Dupree': 2.5},
		'Steve Gates': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 
		 'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
		 'You, Me and Dupree': 2.0}, 
		'Sheldom': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
		 'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},
		'Penny Frewman': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0},
		'Maria Gabriela': {}}

		self.model = DictDataModel(movies)	
		
	def test_create_diffStorage(self):
		storage = DiffStorage(self.model,False)
		self.assertEquals(storage.stdDevWeighted,False)
		self.assertEquals(storage.model,self.model)
	
	def test_buildAveragesDiff(self):
		storage = DiffStorage(self.model,False)
		self.assertEquals(storage._diffStorage,{'Lady in the Water': {'Snakes on a Plane': -0.80000000000000004, 'You, Me and Dupree': 0.0, 'Superman Returns': -1.2, 'The Night Listener': -0.40000000000000002}, 
		                                       'Snakes on a Plane': {'You, Me and Dupree': 1.3333333333333333, 'Superman Returns': -0.2857142857142857, 'The Night Listener': 0.16666666666666666},
		                                       'Just My Luck': {'Snakes on a Plane': -1.25, 'Lady in the Water': -0.66666666666666663, 'You, Me and Dupree': -0.25, 'Superman Returns': -1.5, 'The Night Listener': -1.0},
		                                       'Superman Returns': {'You, Me and Dupree': 1.5833333333333333, 'The Night Listener': 0.58333333333333337},
		                                        'You, Me and Dupree': {}, 'The Night Listener': {'You, Me and Dupree': 0.5}})
		
		self.assertEquals(storage._freqs,{'Lady in the Water': {'Snakes on a Plane': 5, 'You, Me and Dupree': 4, 'Superman Returns': 5, 'The Night Listener': 5},
		             'Snakes on a Plane': {'You, Me and Dupree': 6, 'Superman Returns': 7, 'The Night Listener': 6}, 
		             'Just My Luck': {'Snakes on a Plane': 4, 'Lady in the Water': 3, 'You, Me and Dupree': 4, 'Superman Returns': 4, 'The Night Listener': 4},
		             'Superman Returns': {'You, Me and Dupree': 6, 'The Night Listener': 6}, 
		             'You, Me and Dupree': {}, 'The Night Listener': {'You, Me and Dupree': 5}} )
		
		self.assertEquals(storage._recommendableItems,['Just My Luck', 'Lady in the Water', 'Snakes on a Plane', 'Superman Returns', 'The Night Listener', 'You, Me and Dupree'])
		
		
		storage = DiffStorage(DictDataModel({}),False)
		self.assertEquals(storage._diffStorage,{})
		self.assertEquals(storage._freqs,{})
		self.assertEquals(storage._recommendableItems,[])
				
		storage = DiffStorage(DictDataModel({}),False)
		self.assertEquals(storage._diffStorage,{})
		self.assertEquals(storage._freqs,{})
		self.assertEquals(storage._recommendableItems,[])
		
		storage = DiffStorage(DictDataModel({'Maria':{'A':4.0}}),False)
		self.assertEquals(storage._diffStorage,{'A': {}})
		self.assertEquals(storage._freqs,{'A': {} })
		self.assertEquals(storage._recommendableItems,['A'])

		storage = DiffStorage(DictDataModel({'Maria':{'A':4.0}, 'Joao':{'B': 5.0} }),False)
		self.assertEquals(storage._diffStorage,{'A': {}, 'B':{}})
		self.assertEquals(storage._freqs,{'A': {}, 'B': {} })
		self.assertEquals(storage._recommendableItems,['A','B'])
			
		storage = DiffStorage(DictDataModel({'Maria':{'A':4.0, 'B': 2.0}, 'Joao':{'B': 5.0} }),False)
		self.assertEquals(storage._diffStorage,{'A': {}, 'B':{}})
		self.assertEquals(storage._freqs,{'A': {}, 'B': {} })
		self.assertEquals(storage._recommendableItems,['A','B'])
		
		storage = DiffStorage(DictDataModel({'Maria':{'A':4.0, 'B': 2.0}, 'Joao':{'B': 5.0, 'A':5.0}, 'Flavia':{'A': 2.0, 'C': 3.0} }),False)
		self.assertEquals(storage._diffStorage,{'A': {'B': 1.0}, 'B':{}, 'C':{}})
		self.assertEquals(storage._freqs,{'A': {'B':2}, 'B': {}, 'C': {} })
		self.assertEquals(storage._recommendableItems,['A','B', 'C'])
	
	
	def test_create_ItemBasedRecommender(self):
		recSys = SlopeOneRecommender(self.model,True,True)
		self.assertEquals(recSys.weighted,True)
		self.assertEquals(recSys.stdDevWeighted,True)
		self.assertEquals(recSys.model,self.model)

	def test_local_estimatePreference(self):
		userID = 'Marcel Caraciolo'
		itemID = 'Superman Returns'
		recSys = SlopeOneRecommender(self.model,False,False)
		self.assertAlmostEquals(3.5,recSys.estimatePreference(userID=userID,itemID=itemID))		

	def test_local_not_existing_estimatePreference(self):
		userID = 'Leopoldo Pires'
		itemID = 'You, Me and Dupree'
		#Weighted - With Prune
		recSys = SlopeOneRecommender(self.model,True,False,True)
		self.assertAlmostEquals(2.333333333333,recSys.estimatePreference(userID=userID,itemID=itemID))	
		#Weighted - No Prune
		recSys = SlopeOneRecommender(self.model,True,False,False)
		self.assertAlmostEquals(2.333333333333,recSys.estimatePreference(userID=userID,itemID=itemID))
		#No Weighted - No Prune
		recSys = SlopeOneRecommender(self.model,False,False,False)
		self.assertAlmostEquals(2.395833333333,recSys.estimatePreference(userID=userID,itemID=itemID))
		#No Weighted - With Prune
		recSys = SlopeOneRecommender(self.model,False,False,True)
		self.assertAlmostEquals(2.39583333333,recSys.estimatePreference(userID=userID,itemID=itemID))
		
		#Weighted - StdDev - With Prune
		recSys = SlopeOneRecommender(self.model,True,True,True)
		self.assertAlmostEquals(2.333333333333,recSys.estimatePreference(userID=userID,itemID=itemID))
		#Weighted - StdDev - No Prune
		recSys = SlopeOneRecommender(self.model,True,True,False)
		self.assertAlmostEquals(2.333333333333,recSys.estimatePreference(userID=userID,itemID=itemID))
		
		#Without Prune- Weighted
		recSys = SlopeOneRecommender(DictDataModel({'John':{'A': 5.0, 'B': 3.0, 'C': 2.0}, 'Mark':{'A':3.0, 'B': 4.0}, 'Lucy':{'B':2.0, 'C':5.0}}),True,False,False)
		self.assertAlmostEquals(4.3333333333333,recSys.estimatePreference(userID='Lucy',itemID='A'))
	
	def test_empty_recommend(self):
		userID = 'Marcel Caraciolo'
		recSys = SlopeOneRecommender(self.model,True,False,False)
		self.assertEquals([],recSys.recommend(userID,4))
		recSys = SlopeOneRecommender(self.model,True,False,True)
		self.assertEquals([],recSys.recommend(userID,4))

	def test_recommend(self):
		userID = 'Leopoldo Pires'
		recSys = SlopeOneRecommender(self.model,True,False,False)
		self.assertEquals([ 'You, Me and Dupree', 'Just My Luck'],recSys.recommend(userID,4))
		recSys = SlopeOneRecommender(self.model,True,False,True)
		self.assertEquals(['You, Me and Dupree','Just My Luck' ],recSys.recommend(userID,4))

		recSys = SlopeOneRecommender(DictDataModel({'John':{'A': 5.0, 'B': 3.0, 'C': 2.0}, 'Mark':{'A':3.0, 'B': 4.0}, 'Lucy':{'B':2.0, 'C':5.0}}),True,False,False)
		self.assertEquals(['A'],recSys.recommend('Lucy',4))
		
		users2 = {"Amy": {"Dr. Dog": 4, "Lady Gaga": 3, "Phoenix": 4},          
		              "Ben": {"Dr. Dog": 5, "Lady Gaga": 2},          
		"Clara": {"Lady Gaga": 3.5, "Phoenix": 4}}		
		recSys = SlopeOneRecommender(DictDataModel(users2),True,False,False)
		self.assertEquals(['Phoenix'],recSys.recommend('Ben',1))
		
		

	def test_full_recommend(self):
		userID = 'Maria Gabriela'
		recSys = SlopeOneRecommender(self.model,True,False,False)
		self.assertEquals([],recSys.recommend(userID,4))
		recSys = SlopeOneRecommender(self.model,True,False,True)
		self.assertEquals([],recSys.recommend(userID,4))
		
	def test_semi_recommend(self):
		userID = 'Leopoldo Pires'
		recSys = SlopeOneRecommender(self.model,True,False,False)
		self.assertEquals(['You, Me and Dupree'],recSys.recommend(userID,1))
		recSys = SlopeOneRecommender(self.model,True,False,True)
		self.assertEquals(['You, Me and Dupree'],recSys.recommend(userID,1))
				

class TestItemBasedRecommender(unittest.TestCase):
		
	def setUp(self):
		#SIMILARITY BY RATES.
		movies={'Marcel Caraciolo': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
		 'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 
		 'The Night Listener': 3.0},
		'Luciana Nunes': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 
		 'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0, 
		 'You, Me and Dupree': 3.5}, 
		'Leopoldo Pires': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
		 'Superman Returns': 3.5, 'The Night Listener': 4.0},
		'Lorena Abreu': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
		 'The Night Listener': 4.5, 'Superman Returns': 4.0, 
		 'You, Me and Dupree': 2.5},
		'Steve Gates': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 
		 'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
		 'You, Me and Dupree': 2.0}, 
		'Sheldom': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
		 'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},
		'Penny Frewman': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0},
		'Maria Gabriela': {}}

		self.model = DictDataModel(movies)
		self.similarity = ItemSimilarity(self.model,sim_euclidian)
		self.strategy = PreferredItemsNeighborhoodStrategy()
		
	
	def test_create_ItemBasedRecommender(self):
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,True)
		self.assertEquals(recSys.similarity,self.similarity)
		self.assertEquals(recSys.capper,True)
		self.assertEquals(recSys.strategy,self.strategy)
		self.assertEquals(recSys.model,self.model)
	
	
	def test_oneItem_mostSimilarItems(self):
		itemIDs = ['Superman Returns']
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,True)
		self.assertEquals(['Snakes on a Plane', 'The Night Listener', 'Lady in the Water', 'Just My Luck'],recSys.mostSimilarItems(itemIDs,4))
	
	def test_multipeItems_mostSimilarItems(self):
		itemIDs = ['Superman Returns','Just My Luck']
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,True)
		self.assertEquals(['Lady in the Water', 'Snakes on a Plane', 'The Night Listener', 'You, Me and Dupree'],recSys.mostSimilarItems(itemIDs,4))
	
	def test_semiItem_mostSimilarItems(self):
		itemIDs = ['Superman Returns','Just My Luck','Snakes on a Plane',  'The Night Listener',  'You, Me and Dupree']
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,True)
		self.assertEquals(['Lady in the Water'],recSys.mostSimilarItems(itemIDs,4))
	
	def test_allItem_mostSimilarItems(self):
		itemIDs = ['Superman Returns','Just My Luck','Snakes on a Plane',  'The Night Listener',  'You, Me and Dupree','Lady in the Water']
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,True)
		self.assertEquals([],recSys.mostSimilarItems(itemIDs,4))
		
		
	def test_local_estimatePreference(self):
		userID = 'Marcel Caraciolo'
		itemID = 'Superman Returns'
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,True)
		self.assertAlmostEquals(3.5,recSys.estimatePreference(userID=userID,similarity=self.similarity,itemID=itemID))


	def test_local_not_existing_estimatePreference(self):
		userID = 'Leopoldo Pires'
		itemID = 'You, Me and Dupree'
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,True)
		self.assertAlmostEquals(3.14717875510,recSys.estimatePreference(userID=userID,similarity=self.similarity,itemID=itemID))


	def test_local_not_existing_capper_False_estimatePreference(self):
		userID = 'Leopoldo Pires'
		itemID = 'You, Me and Dupree'
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,False)
		self.assertAlmostEquals(3.14717875510,recSys.estimatePreference(userID=userID,similarity=self.similarity,itemID=itemID))


	def test_local_not_existing_rescorer_estimatePreference(self):
		userID = 'Leopoldo Pires'
		itemID = 'You, Me and Dupree'
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,False)
		scorer = TanHScorer()
		self.assertAlmostEquals(3.1471787551,recSys.estimatePreference(userID=userID,similarity=self.similarity,itemID=itemID,rescorer=scorer))


	def test_empty_recommend(self):
		userID = 'Marcel Caraciolo'
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,False)
		self.assertEquals([],recSys.recommend(userID,4))

		
	def test_recommend(self):
		userID = 'Leopoldo Pires'
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,False)
		self.assertEquals(['Just My Luck', 'You, Me and Dupree'],recSys.recommend(userID,4))

		
	def test_full_recommend(self):
		userID = 'Maria Gabriela'
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,False)
		self.assertEquals([],recSys.recommend(userID,4))


	def test_semi_recommend(self):
		userID = 'Leopoldo Pires'
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,False)
		self.assertEquals(['Just My Luck'],recSys.recommend(userID,1))


	def test_recommendedBecause(self):
		userID = 'Leopoldo Pires'
		itemID = 'Just My Luck'
		recSys = ItemRecommender(self.model,self.similarity,self.strategy,False)
		self.assertEquals(['The Night Listener', 'Superman Returns'],recSys.recommendedBecause(userID,itemID,2))
		
	
def suite():
	suite = unittest.TestSuite()
	suite.addTests(unittest.makeSuite(TestUserBasedRecommender))
	suite.addTests(unittest.makeSuite(TestItemBasedRecommender))
	suite.addTests(unittest.makeSuite(TestSlopeOneRecommender))
	

	return suite

if __name__ == '__main__':
	unittest.main()
########NEW FILE########
__FILENAME__ = test_topitems
#-*- coding:utf-8 -*-

'''

* Licensed to the Apache Software Foundation (ASF) under one or more
* contributor license agreements.  See the NOTICE file distributed with
* this work for additional information regarding copyright ownership.
* The ASF licenses this file to You under the Apache License, Version 2.0
* (the "License"); you may not use this file except in compliance with
* the License.  You may obtain a copy of the License at
*
*     http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.


0.1 2010-11-08 Initial version.
'''

__author__ = 'marcel@orygens.com'

import unittest

from models.datamodel import *
from recommender.topmatches import *
from neighborhood.neighborhood import NearestNUserNeighborhood
from similarities.similarity import UserSimilarity
from similarities.similarity_distance import *
from scoring.scorer import TanHScorer, NaiveScorer


def estimateUserUser(**args):
	userID = args['thingID'] or args.get('userID',None)
	otherUserID = args['otherUserID']
	similarity = args['similarity']
	
	if userID == otherUserID:
		return None
			
	estimated = similarity.getSimilarity(userID,otherUserID)
		
	return estimated


def estimateUserItem(**args):
	userID = args.get('thingID',None) or args.get('userID',None)
	itemID = args.get('itemID',None)
	similarity = args.get('similarity',None)
	nHood = args.get('neighborhood',None)
	model =args.get('model',None)
	rescorer = args.get('rescorer',None)
	capper = args.get('capper',False)
	
	pref = model.PreferenceValue(userID,itemID)
	if pref is not None:
		return pref

	nHood = nHood.userNeighborhood(userID=userID,rescorer=rescorer)
	
	if not nHood:
		return None
	
	preference = 0.0
	totalSimilarity = 0.0
	count = 0
	for usrID in nHood:
		if usrID != userID:
			pref = model.PreferenceValue(usrID,itemID)
			if pref is not None:
				sim = similarity.getSimilarity(usrID, userID)
				if sim is not None:
					preference+= sim*pref
					totalSimilarity += sim
					count+=1
	
	#Throw out the estimate if it was based on no data points, of course, but also if based on
	#just one. This is a bit of a band-aid on the 'stock' item-based algorithm for the moment.
	#The reason is that in this case the estimate is, simply, the user's rating for one item
	#that happened to have a defined similarity. The similarity score doesn't matter, and that
	#seems like a bad situation.
	if count <=1:
		return None
	
	estimated = float(preference) / totalSimilarity
	
		
	if capper:
		#TODO: Maybe put this in a separated function.
		max = self.model.MaxPreference()
		min = self.model.MinPreference()
		estimated =  max if estimated > max else min if estimated < min else estimated
				
	return estimated



class TestTopMatches(unittest.TestCase):
	
	def setUp(self):
		#SIMILARITY BY RATES.
		movies={'Marcel Caraciolo': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
		 'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 
		 'The Night Listener': 3.0},
		'Luciana Nunes': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 
		 'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0, 
		 'You, Me and Dupree': 3.5}, 
		'Leopoldo Pires': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
		 'Superman Returns': 3.5, 'The Night Listener': 4.0},
		'Lorena Abreu': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
		 'The Night Listener': 4.5, 'Superman Returns': 4.0, 
		 'You, Me and Dupree': 2.5},
		'Steve Gates': {'Lady in  the Water': 3.0, 'Snakes on a Plane': 4.0, 
		 'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
		 'You, Me and Dupree': 2.0}, 
		'Sheldom': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
		 'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},
		'Penny Frewman': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0},
		'Maria Gabriela': {}}

		self.model = DictDataModel(movies)
		self.similarity = UserSimilarity(self.model,sim_euclidian)
			
	def test_topUsers(self):
		userID = 'Luciana Nunes'
		numUsers = 4
		allUserIDs = self.model.UserIDs()
		preferenceEstimator = estimateUserUser
		rescorer = NaiveScorer()		
		self.assertEquals(['Sheldom', 'Leopoldo Pires', 'Marcel Caraciolo', 'Lorena Abreu'] ,topUsers(userID,allUserIDs,numUsers,preferenceEstimator,self.similarity))


	def test_rescorer_topUsers(self):
		userID = 'Luciana Nunes'
		numUsers = 4
		allUserIDs = self.model.UserIDs()
		preferenceEstimator = estimateUserUser
		rescorer  = TanHScorer()	
		self.assertEquals(['Maria Gabriela', 'Penny Frewman', 'Steve Gates', 'Lorena Abreu'] ,topUsers(userID,allUserIDs,numUsers,preferenceEstimator,self.similarity,rescorer))

	def test_maxUsers_topUsers(self):
		userID = 'Luciana Nunes'
		numUsers = 9
		allUserIDs = self.model.UserIDs()
		preferenceEstimator = estimateUserUser
		rescorer  = TanHScorer()	
		self.assertEquals(['Maria Gabriela', 'Penny Frewman', 'Steve Gates', 'Lorena Abreu', 'Marcel Caraciolo', 'Leopoldo Pires', 'Sheldom'],topUsers(userID,allUserIDs,numUsers,preferenceEstimator,self.similarity,rescorer))

	def test_minUsers_topUsers(self):
		userID = 'Luciana Nunes'
		numUsers = 0
		allUserIDs = self.model.UserIDs()
		preferenceEstimator = estimateUserUser
		rescorer  = TanHScorer()	
		self.assertEquals([],topUsers(userID,allUserIDs,numUsers,preferenceEstimator,self.similarity,rescorer))
	
	def test_UserItem_topItems(self):
		userID = 'Leopoldo Pires'
		numItems = 4
		allItemIDs = self.model.ItemIDs()
		preferenceEstimator = estimateUserItem
		rescorer = NaiveScorer()	
		n = NearestNUserNeighborhood(self.similarity,self.model,4,0.0)								
		self.assertEquals(['The Night Listener', 'Superman Returns', 'Snakes on a Plane', 'Just My Luck'],
			topItems(userID,allItemIDs,numItems, preferenceEstimator,self.similarity,None,model=self.model,neighborhood=n))
			
	def test_rescorer_UserItem_topItems(self):
		userID = 'Leopoldo Pires'
		numItems = 4
		allItemIDs = self.model.ItemIDs()
		preferenceEstimator = estimateUserItem
		rescorer = TanHScorer()	
		n = NearestNUserNeighborhood(self.similarity,self.model,4,0.0)								
		self.assertEquals(['Lady in the Water', 'You, Me and Dupree', 'Snakes on a Plane', 'Superman Returns'],
			topItems(userID,allItemIDs,numItems, preferenceEstimator,self.similarity,rescorer,model=self.model,neighborhood=n))

	def test_maxItems_UserItem_topItems(self):
		userID = 'Leopoldo Pires'
		numItems = 9
		allItemIDs = self.model.ItemIDs()
		preferenceEstimator = estimateUserItem
		n = NearestNUserNeighborhood(self.similarity,self.model,4,0.0)								
		self.assertEquals(['The Night Listener', 'Superman Returns', 'Snakes on a Plane', 'Just My Luck', 
				'Lady in the Water', 'You, Me and Dupree'], topItems(userID,allItemIDs,numItems, preferenceEstimator,self.similarity,None,model=self.model,neighborhood=n,))


	def test_minItems_UserItem_topItems(self):
		userID = 'Leopoldo Pires'
		numItems = 0
		allItemIDs = self.model.ItemIDs()
		preferenceEstimator = estimateUserItem
		n = NearestNUserNeighborhood(self.similarity,self.model,4,0.0)								
		self.assertEquals([], topItems(userID,allItemIDs,numItems, preferenceEstimator,self.similarity,None,model=self.model,neighborhood=n,))


	def suite():
		suite = unittest.TestSuite()
		suite.addTests(unittest.makeSuite(TestNearestNUserNeighborhood))

		return suite

if __name__ == '__main__':
	unittest.main()
########NEW FILE########
