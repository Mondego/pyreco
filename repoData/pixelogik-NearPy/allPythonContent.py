__FILENAME__ = angular
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy

from nearpy.distances.distance import Distance


class AngularDistance(Distance):
    """  Uses 1-cos(angle(x,y)) as distance measure. """

    def distance(self, x, y):
        """
        Computes distance measure between vectors x and y. Returns float.
        """
        return 1.0 - numpy.dot(x, y) / (numpy.linalg.norm(x) *
                                        numpy.linalg.norm(y))

########NEW FILE########
__FILENAME__ = distance
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


class Distance(object):
    """ Interface for distance functions. """

    def distance(self, x, y):
        """
        Computes distance measure between vectors x and y. Returns float.
        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = euclidean
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy

from nearpy.distances.distance import Distance


class EuclideanDistance(Distance):
    """ Euclidean distance """

    def distance(self, x, y):
        """
        Computes distance measure between vectors x and y. Returns float.
        """
        return numpy.linalg.norm(x-y)

########NEW FILE########
__FILENAME__ = engine
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import json

from nearpy.hashes import RandomBinaryProjections
from nearpy.filters import NearestFilter
from nearpy.distances import EuclideanDistance
from nearpy.storage import MemoryStorage


class Engine(object):
    """
    Objects with this type perform the actual ANN search and vector indexing.
    They can be configured by selecting implementations of the Hash, Distance,
    Filter and Storage interfaces.

    There are four different modes of the engine:

        (1) Full configuration - All arguments are defined.
                In this case the distance and vector filters
                are applied to the bucket contents to deliver the
                resulting list of filtered (vector, data, distance) tuples.
        (2) No distance - The distance argument is None.
                In this case only the vector filters are applied to
                the bucket contents and the result is a list of
                filtered (vector, data) tuples.
        (3) No vector filter - The vector_filter argument is None.
                In this case only the distance is applied to
                the bucket contents and the result is a list of
                unsorted/unfiltered (vector, data, distance) tuples.
        (4) No vector filter and no distance - Both arguments are None.
                In this case the result is just the content from the
                buckets as an unsorted/unfiltered list of (vector, data)
                tuples.
    """

    def __init__(self, dim, lshashes=[RandomBinaryProjections('default', 10)],
                 distance=EuclideanDistance(),
                 vector_filters=[NearestFilter(10)],
                 storage=MemoryStorage()):
        """ Keeps the configuration. """
        self.lshashes = lshashes
        self.distance = distance
        self.vector_filters = vector_filters
        self.storage = storage

        # Initialize all hashes for the data space dimension.
        for lshash in self.lshashes:
            lshash.reset(dim)

    def store_vector(self, v, data=None):
        """
        Hashes vector v and stores it in all matching buckets in the storage.
        The data argument must be JSON-serializable. It is stored with the
        vector and will be returned in search results.
        """
        # Store vector in each bucket of all hashes
        for lshash in self.lshashes:
            for bucket_key in lshash.hash_vector(v):
                self.storage.store_vector(lshash.hash_name, bucket_key,
                                          v, data)

    def neighbours(self, v):
        """
        Hashes vector v, collects all candidate vectors from the matching
        buckets in storage, applys the (optional) distance function and
        finally the (optional) filter function to construct the returned list
        of either (vector, data, distance) tuples or (vector, data) tuples.
        """
        # Collect candidates from all buckets from all hashes
        candidates = []
        for lshash in self.lshashes:
            for bucket_key in lshash.hash_vector(v):
                bucket_content = self.storage.get_bucket(lshash.hash_name,
                                                         bucket_key)
                candidates.extend(bucket_content)

        # Apply distance implementation if specified
        if self.distance:
            candidates = [(x[0], x[1], self.distance.distance(x[0], v)) for x
                          in candidates]

        # Apply vector filters if specified and return filtered list
        if self.vector_filters:
            filter_input = candidates
            for vector_filter in self.vector_filters:
                filter_input = vector_filter.filter_vectors(filter_input)
            # Return output of last filter
            return filter_input

        # If there is no vector filter, just return list of candidates
        return candidates

    def clean_all_buckets(self):
        """ Clears buckets in storage (removes all vectors and their data). """
        self.storage.clean_all_buckets()

    def clean_buckets(self, hash_name):
        """ Clears buckets in storage (removes all vectors and their data). """
        self.storage.clean_buckets(hash_name)

########NEW FILE########
__FILENAME__ = distanceratioexperiment
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from __future__ import print_function

import numpy
import scipy
import time
import sys

from scipy.spatial.distance import cdist

from nearpy.utils import numpy_array_from_list_or_numpy_array


class DistanceRatioExperiment(object):
    """
    Performs nearest neighbour experiments with custom vector data
    for all engines in the specified list.

    Distance ratio is the average distance of retrieved approximated
    neighbours, that are outside the radius of the real nearest N
    neighbours,  with respect to this radius.

    Let R be the radius of the real N nearest neighbours around the
    query vector. Then a distance ratio of 1.0 means, that the average
    approximated nearest neighbour is 2*R away from the query point.
    A distance_ratio of 0.0 means, all approximated neighbours are
    within the radius.

    This is a much better performance measure for ANN than recall or precision,
    because in ANN we are interested in spatial relations between query vector
    and the results.

    perform_experiment() returns list of (distance_ratio, result_size,
    search_time) tuple. These are the averaged values over all request
    vectors. search_time is the average retrieval/search time compared
    to the average exact search time. result_size is the size of the
    retrieved set of approximated neighbours.

    coverage_ratio determines how many of the vectors are used as query
    vectors for exact andapproximated search. Because the search comparance
    overhead is quite large, it is best with large data sets (>10000) to
    use a low coverage_ratio (like 0.1) to make the experiment fast. A
    coverage_ratio of 0.1 makes the experiment use 10% of all the vectors
    for querying, that is, it looks for 10% of all vectors for the nearest
    neighbours.
    """

    def __init__(self, N, vectors, coverage_ratio=0.2):
        """
        Performs exact nearest neighbour search on the data set.

        vectors can either be a numpy matrix with all the vectors
        as columns OR a python array containing the individual
        numpy vectors.
        """
        # We need a dict from vector string representation to index
        self.vector_dict = {}
        self.N = N
        self.coverage_ratio = coverage_ratio

        # Get numpy array representation of input
        self.vectors = numpy_array_from_list_or_numpy_array(vectors)

        # Build map from vector string representation to vector
        for index in range(self.vectors.shape[1]):
            self.vector_dict[self.__vector_to_string(
                self.vectors[:, index])] = index

        # Get transposed version of vector matrix, so that the rows
        # are the vectors (needed by cdist)
        vectors_t = numpy.transpose(self.vectors)

        # Determine the indices of query vectors used for comparance
        # with approximated search.
        query_count = numpy.floor(self.coverage_ratio *
                                  self.vectors.shape[1])
        self.query_indices = []
        for k in range(int(query_count)):
            index = numpy.floor(k*(self.vectors.shape[1]/query_count))
            index = min(index, self.vectors.shape[1]-1)
            self.query_indices.append(int(index))

        print('\nStarting exact search (query set size=%d)...\n' % query_count)

        # For each query vector get radius of closest N neighbours
        self.nearest_radius = {}
        self.exact_search_time_per_vector = 0.0

        for index in self.query_indices:

            v = vectors_t[index, :].reshape(1, self.vectors.shape[0])
            exact_search_start_time = time.time()
            D = cdist(v, vectors_t, 'euclidean')

            # Get radius of closest N neighbours
            self.nearest_radius[index] = scipy.sort(D)[0, N]

            # Save time needed for exact search
            exact_search_time = time.time() - exact_search_start_time
            self.exact_search_time_per_vector += exact_search_time

        print('\Done with exact search...\n')

        # Normalize search time
        self.exact_search_time_per_vector /= float(len(self.query_indices))

    def perform_experiment(self, engine_list):
        """
        Performs nearest neighbour experiments with custom vector data
        for all engines in the specified list.

        Returns self.result contains list of (distance_ratio, search_time)
        tuple. All are the averaged values over all request vectors.
        search_time is the average retrieval/search time compared to the
        average exact search time.
        """
        # We will fill this array with measures for all the engines.
        result = []

        # For each engine, first index vectors and then retrieve neighbours
        for engine in engine_list:
            print('Engine %d / %d' % (engine_list.index(engine),
                                      len(engine_list)))

            # Clean storage
            engine.clean_all_buckets()
            # Use this to compute average distance_ratio
            avg_distance_ratio = 0.0
            # Use this to compute average result set size
            avg_result_size = 0.0
            # Use this to compute average search time
            avg_search_time = 0.0

            # Index all vectors and store them
            for index in range(self.vectors.shape[1]):
                engine.store_vector(self.vectors[:, index],
                                    'data_%d' % index)

            # Look for N nearest neighbours for query vectors
            for index in self.query_indices:
                # We have to time the search
                search_time_start = time.time()

                # Get nearest N according to engine
                nearest = engine.neighbours(self.vectors[:, index])

                # Get search time
                search_time = time.time() - search_time_start

                # Get average distance ratio (with respect to radius
                # of real N closest neighbours)
                distance_ratio = 0.0
                for n in nearest:
                    # If the vector is outside the real neighbour radius
                    if n[2] > self.nearest_radius[index]:
                        # Compute distance to real neighbour radius
                        d = (n[2] - self.nearest_radius[index])
                        # And normalize it. 1.0 means: distance to
                        # real neighbour radius is identical to radius
                        d /= self.nearest_radius[index]
                        # If all neighbours are in the radius, the
                        # distance ratio is 0.0
                        distance_ratio += d
                # Normalize distance ratio over all neighbours
                distance_ratio /= len(nearest)

                # Add to accumulator
                avg_distance_ratio += distance_ratio

                # Add to accumulator
                avg_result_size += len(nearest)

                # Add to accumulator
                avg_search_time += search_time

            # Normalize distance ratio over query set
            avg_distance_ratio /= float(len(self.query_indices))

            # Normalize avg result size
            avg_result_size /= float(len(self.query_indices))

            # Normalize search time over query set
            avg_search_time = avg_search_time / float(len(self.query_indices))

            # Normalize search time with respect to exact search
            avg_search_time /= self.exact_search_time_per_vector

            print('  distance_ratio=%f, result_size=%f, time=%f' % (avg_distance_ratio,
                                                                    avg_result_size,
                                                                    avg_search_time))

            result.append((avg_distance_ratio, avg_result_size, avg_search_time))

        return result

    def __vector_to_string(self, vector):
        """ Returns string representation of vector. """
        return numpy.array_str(vector)

    def __index_of_vector(self, vector):
        """ Returns index of specified vector from test data set. """
        return self.vector_dict[self.__vector_to_string(vector)]

########NEW FILE########
__FILENAME__ = recallprecisionexperiment
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from __future__ import print_function

import numpy
import scipy
import time
import sys

from scipy.spatial.distance import cdist

from nearpy.utils import numpy_array_from_list_or_numpy_array


class RecallPrecisionExperiment(object):
    """
    Performs nearest neighbour recall experiments with custom vector data
    for all engines in the specified list.

    perform_experiment() returns list of (recall, precision, search_time)
    tuple. These are the averaged values over all request vectors. search_time
    is the average retrieval/search time compared to the average exact search
    time.

    coverage_ratio determines how many of the vectors are used as query
    vectors for exact andapproximated search. Because the search comparance
    overhead is quite large, it is best with large data sets (>10000) to
    use a low coverage_ratio (like 0.1) to make the experiment fast. A
    coverage_ratio of 0.1 makes the experiment use 10% of all the vectors
    for querying, that is, it looks for 10% of all vectors for the nearest
    neighbours.
    """

    def __init__(self, N, vectors, coverage_ratio=0.2):
        """
        Performs exact nearest neighbour search on the data set.

        vectors can either be a numpy matrix with all the vectors
        as columns OR a python array containing the individual
        numpy vectors.
        """
        # We need a dict from vector string representation to index
        self.vector_dict = {}
        self.N = N
        self.coverage_ratio = coverage_ratio

        # Get numpy array representation of input
        self.vectors = numpy_array_from_list_or_numpy_array(vectors)

        # Build map from vector string representation to vector
        for index in range(self.vectors.shape[1]):
            self.vector_dict[self.__vector_to_string(
                self.vectors[:, index])] = index

        # Get transposed version of vector matrix, so that the rows
        # are the vectors (needed by cdist)
        vectors_t = numpy.transpose(self.vectors)

        # Determine the indices of query vectors used for comparance
        # with approximated search.
        query_count = numpy.floor(self.coverage_ratio *
                                  self.vectors.shape[1])
        self.query_indices = []
        for k in range(int(query_count)):
            index = numpy.floor(k*(self.vectors.shape[1]/query_count))
            index = min(index, self.vectors.shape[1]-1)
            self.query_indices.append(int(index))

        print('\nStarting exact search (query set size=%d)...\n' % query_count)

        # For each query vector get the closest N neighbours
        self.closest = {}
        self.exact_search_time_per_vector = 0.0

        for index in self.query_indices:

            v = vectors_t[index, :].reshape(1, self.vectors.shape[0])
            exact_search_start_time = time.time()
            D = cdist(v, vectors_t, 'euclidean')
            self.closest[index] = scipy.argsort(D)[0, 1:N+1]

            # Save time needed for exact search
            exact_search_time = time.time() - exact_search_start_time
            self.exact_search_time_per_vector += exact_search_time

        print('\Done with exact search...\n')

        # Normalize search time
        self.exact_search_time_per_vector /= float(len(self.query_indices))

    def perform_experiment(self, engine_list):
        """
        Performs nearest neighbour recall experiments with custom vector data
        for all engines in the specified list.

        Returns self.result contains list of (recall, precision, search_time)
        tuple. All are the averaged values over all request vectors.
        search_time is the average retrieval/search time compared to the
        average exact search time.
        """
        # We will fill this array with measures for all the engines.
        result = []

        # For each engine, first index vectors and then retrieve neighbours
        for engine in engine_list:
            print('Engine %d / %d' % (engine_list.index(engine),
                                      len(engine_list)))

            # Clean storage
            engine.clean_all_buckets()
            # Use this to compute average recall
            avg_recall = 0.0
            # Use this to compute average precision
            avg_precision = 0.0
            # Use this to compute average search time
            avg_search_time = 0.0

            # Index all vectors and store them
            for index in range(self.vectors.shape[1]):
                engine.store_vector(self.vectors[:, index],
                                    'data_%d' % index)

            # Look for N nearest neighbours for query vectors
            for index in self.query_indices:
                # Get indices of the real nearest as set
                real_nearest = set(self.closest[index])

                # We have to time the search
                search_time_start = time.time()

                # Get nearest N according to engine
                nearest = engine.neighbours(self.vectors[:, index])

                # Get search time
                search_time = time.time() - search_time_start

                # For comparance we need their indices (as set)
                nearest = set([self.__index_of_vector(x[0]) for x in nearest])

                # Remove query index from search result to make sure that
                # recall and precision make sense in terms of "neighbours".
                # If ONLY the query vector is retrieved, we want recall to be
                # zero!
                nearest.remove(index)

                # If the result list is empty, recall and precision are 0.0
                if len(nearest) == 0:
                    recall = 0.0
                    precision = 0.0
                else:
                    # Get intersection count
                    inter_count = float(len(real_nearest.intersection(
                        nearest)))

                    # Normalize recall for this vector
                    recall = inter_count/float(len(real_nearest))

                    # Normalize precision for this vector
                    precision = inter_count/float(len(nearest))

                # Add to accumulator
                avg_recall += recall

                # Add to accumulator
                avg_precision += precision

                # Add to accumulator
                avg_search_time += search_time

            # Normalize recall over query set
            avg_recall = avg_recall / float(len(self.query_indices))

            # Normalize precision over query set
            avg_precision = avg_precision / float(len(self.query_indices))

            # Normalize search time over query set
            avg_search_time = avg_search_time / float(len(self.query_indices))

            # Normalize search time with respect to exact search
            avg_search_time /= self.exact_search_time_per_vector

            print('  recall=%f, precision=%f, time=%f' % (avg_recall,
                                                          avg_precision,
                                                          avg_search_time))

            result.append((avg_recall, avg_precision, avg_search_time))

        # Return (recall, precision, search_time) tuple
        return result

    def __vector_to_string(self, vector):
        """ Returns string representation of vector. """
        return numpy.array_str(vector)

    def __index_of_vector(self, vector):
        """ Returns index of specified vector from test data set. """
        return self.vector_dict[self.__vector_to_string(vector)]

########NEW FILE########
__FILENAME__ = distancethresholdfilter
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from nearpy.filters.vectorfilter import VectorFilter


class DistanceThresholdFilter(VectorFilter):
    """
    Rejects vectors with a distance over the threshold.
    """

    def __init__(self, distance_threshold):
        """
        Keeps the distance threshold
        """
        self.distance_threshold = distance_threshold

    def filter_vectors(self, input_list):
        """
        Returns subset of specified input list.
        """
        try:
            # Return filtered (vector, data, distance )tuple list. Will fail
            # if input is list of (vector, data) tuples.
            return [x for x in input_list if x[2] < self.distance_threshold]
        except:
            # Otherwise just return input list
            return input_list

########NEW FILE########
__FILENAME__ = nearestfilter
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from nearpy.filters.vectorfilter import VectorFilter


class NearestFilter(VectorFilter):
    """
    Sorts vectors with respect to distance and returns the N nearest.
    """

    def __init__(self, N):
        """
        Keeps the count threshold.
        """
        self.N = N

    def filter_vectors(self, input_list):
        """
        Returns subset of specified input list.
        """
        try:
            # Return filtered (vector, data, distance )tuple list. Will fail
            # if input is list of (vector, data) tuples.
            sorted_list = sorted(input_list, key=lambda x: x[2])
            return sorted_list[:self.N]
        except:
            # Otherwise just return input list
            return input_list

########NEW FILE########
__FILENAME__ = uniquefilter
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from __future__ import print_function

import numpy

from nearpy.filters.vectorfilter import VectorFilter


class UniqueFilter(VectorFilter):
    """
    Makes sure that each vectors is only once in the vector list. Works on
    both types of vector listst - (vector, data, distance) and
    (vector, data).

    This filter uses the 'data' as key for uniqueness. If you need some
    other feature for uniqueness, you can implement your own filter.

    You only need a uniqueness filter if your hash-configuration makes it
    possible that one vecor is saved in many buckets.
    """

    def __init__(self):
        pass

    def filter_vectors(self, input_list):
        """
        Returns subset of specified input list.
        """
        unique_dict = {}
        for v in input_list:
            unique_dict[v[1]] = v
        return list(unique_dict.values())

########NEW FILE########
__FILENAME__ = vectorfilter
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


class VectorFilter(object):
    """
    Interface for vector-list filters. They get either (vector, data, distance)
    tupes or (vector, data) tuples and return subsets of them.

    Some filters work on lists of (vector, data, distance) tuples, others work
    on lists of (vector, data) tuples and others work on both types.
    Depending on the configuration of the engine, you have to select the right
    filter chain.

    Filter are chained in the engine, if you specify more than one. This way
    you can combine their functionalities.

    The default filtes in the engine (see engine.py) are a UniqueFilter
    followed by a NearestFilter(10). The UniqueFilter makes sure, that the
    candidate list contains each vector only once and the NearestFilter(10)
    returns the 10 closest candidates (using the distance).

    Which kind you need is very simple to determine: If you use a Distance
    implementation, you have to use filters that take
    (vector, data, distance) tuples. If you however decide to not use Distance
    (Engine with distance=None), you have to use a vector filters that
    process lists of (vector, data) tuples.

    However all filters can handle both input types. They will just return the
    input list if their filter mechanism does not apply on the input type.
    """

    def filter_vectors(self, input_list):
        """
        Returns subset of specified input list.
        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = lshash
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


class LSHash(object):
    """ Interface for locality-sensitive hashes. """

    def __init__(self, hash_name):
        """
        The hash name is used in storage to store buckets of
        different hashes without collision.
        """
        self.hash_name = hash_name

    def reset(self, dim):
        """ Resets / Initializes the hash for the specified dimension. """
        raise NotImplementedError

    def hash_vector(self, v):
        """
        Hashes the vector and returns a list of bucket keys, that match the
        vector. Depending on the hash implementation this list can contain
        one or many bucket keys.
        """
        raise NotImplementedError


########NEW FILE########
__FILENAME__ = pcabinaryprojections
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy
import scipy

from nearpy.hashes.lshash import LSHash

from nearpy.utils import numpy_array_from_list_or_numpy_array, perform_pca


class PCABinaryProjections(LSHash):
    """
    Projects a vector on n first principal components and assigns
    a binary value to each projection depending on the sign. This
    divides the data set by each principal component hyperplane and
    generates a binary hash value in string form, which is being
    used as a bucket key for storage.
    """

    def __init__(self, hash_name, projection_count, training_set):
        """
        Computes principal components for training vector set. Uses
        first projection_count principal components for projections.

        Training set must be either a numpy matrix or a list of
        numpy vectors.
        """
        super(PCABinaryProjections, self).__init__(hash_name)
        self.projection_count = projection_count

        # Get numpy array representation of input
        training_set = numpy_array_from_list_or_numpy_array(training_set)

        # Get subspace size from training matrix
        self.dim = training_set.shape[0]

        # Get transposed training set matrix for PCA
        training_set_t = numpy.transpose(training_set)

        # Compute principal components
        (eigenvalues, eigenvectors) = perform_pca(training_set_t)

        # Get largest N eigenvalue/eigenvector indices
        largest_eigenvalue_indices = numpy.flipud(
            scipy.argsort(eigenvalues))[:projection_count]

        # Create matrix for first N principal components
        self.components = numpy.zeros((self.dim,
                                       len(largest_eigenvalue_indices)))

        # Put first N principal components into matrix
        for index in range(len(largest_eigenvalue_indices)):
            self.components[:, index] = \
                eigenvectors[:, largest_eigenvalue_indices[index]]

        # We need the component vectors to be in the rows
        self.components = numpy.transpose(self.components)

    def reset(self, dim):
        """ Resets / Initializes the hash for the specified dimension. """
        if self.dim != dim:
            raise Exception('PCA hash is trained for specific dimension!')

    def hash_vector(self, v):
        """
        Hashes the vector and returns the binary bucket key as string.
        """
        # Project vector onto all hyperplane normals
        projection = numpy.dot(self.components, v)
        # Return binary key
        return [''.join(['1' if x > 0.0 else '0' for x in projection])]

########NEW FILE########
__FILENAME__ = pcadiscretizedprojections
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy
import scipy

from nearpy.hashes.lshash import LSHash

from nearpy.utils import numpy_array_from_list_or_numpy_array, perform_pca


class PCADiscretizedProjections(LSHash):
    """
    Projects a vector on n first principal components and assigns
    a discrete value to each projection depending on the bin.
    """

    def __init__(self, hash_name, projection_count, training_set, bin_width):
        """
        Computes principal components for training vector set. Uses
        first projection_count principal components for projections.

        Training set must be either a numpy matrix or a list of
        numpy vectors.
        """
        super(PCADiscretizedProjections, self).__init__(hash_name)
        self.projection_count = projection_count
        self.bin_width = bin_width

        # Get numpy array representation of input
        training_set = numpy_array_from_list_or_numpy_array(training_set)

        # Get subspace size from training matrix
        self.dim = training_set.shape[0]

        # Get transposed training set matrix for PCA
        training_set_t = numpy.transpose(training_set)

        # Compute principal components
        (eigenvalues, eigenvectors) = perform_pca(training_set_t)

        # Get largest N eigenvalue/eigenvector indices
        largest_eigenvalue_indices = numpy.flipud(
            scipy.argsort(eigenvalues))[:projection_count]

        # Create matrix for first N principal components
        self.components = numpy.zeros((self.dim,
                                       len(largest_eigenvalue_indices)))

        # Put first N principal components into matrix
        for index in range(len(largest_eigenvalue_indices)):
            self.components[:, index] = \
                eigenvectors[:, largest_eigenvalue_indices[index]]

        # We need the component vectors to be in the rows
        self.components = numpy.transpose(self.components)

    def reset(self, dim):
        """ Resets / Initializes the hash for the specified dimension. """
        if self.dim != dim:
            raise Exception('PCA hash is trained for specific dimension!')

    def hash_vector(self, v):
        """
        Hashes the vector and returns the binary bucket key as string.
        """
        # Project vector onto components
        projection = numpy.dot(self.components, v)
        projection = numpy.floor(projection / self.bin_width)
        # Return key
        return ['_'.join([str(int(x)) for x in projection])]

########NEW FILE########
__FILENAME__ = randombinaryprojections
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy

from nearpy.hashes.lshash import LSHash


class RandomBinaryProjections(LSHash):
    """
    Projects a vector on n random hyperplane normals and assigns
    a binary value to each projection depending on the sign. This
    divides the data set by each hyperplane and generates a binary
    hash value in string form, which is being used as a bucket key
    for storage.
    """

    def __init__(self, hash_name, projection_count):
        """
        Creates projection_count random vectors, that are used for projections
        thus working as normals of random hyperplanes. Each random vector /
        hyperplane will result in one bit of hash.

        So if you for example decide to use projection_count=10, the bucket
        keys will have 10 digits and will look like '1010110011'.
        """
        super(RandomBinaryProjections, self).__init__(hash_name)
        self.projection_count = projection_count
        self.dim = None
        self.normals = None

    def reset(self, dim):
        """ Resets / Initializes the hash for the specified dimension. """
        self.dim = dim
        self.normals = numpy.random.randn(self.projection_count, dim)

    def hash_vector(self, v):
        """
        Hashes the vector and returns the binary bucket key as string.
        """
        # Project vector onto all hyperplane normals
        projection = numpy.dot(self.normals, v)
        # Return binary key
        return [''.join(['1' if x > 0.0 else '0' for x in projection])]

########NEW FILE########
__FILENAME__ = randomdiscretizedprojections
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy

from nearpy.hashes.lshash import LSHash


class RandomDiscretizedProjections(LSHash):
    """
    Projects a vector on n random vectors and assigns
    a discrete value to each projection depending on the location on the
    random vector using a bin width.
    """

    def __init__(self, hash_name, projection_count, bin_width):
        """
        Creates projection_count random vectors, that are used for projections.
        Each random vector will result in one discretized coordinate.

        So if you for example decide to use projection_count=3, the bucket
        keys will have 3 coordinates and look like '14_4_1' or '-4_18_-1'.
        """
        super(RandomDiscretizedProjections, self).__init__(hash_name)
        self.projection_count = projection_count
        self.dim = None
        self.vectors = None
        self.bin_width = bin_width

    def reset(self, dim):
        """ Resets / Initializes the hash for the specified dimension. """
        self.dim = dim
        self.vectors = numpy.random.randn(self.projection_count, dim)

    def hash_vector(self, v):
        """
        Hashes the vector and returns the binary bucket key as string.
        """
        # Project vector onto all hyperplane normals
        projection = numpy.dot(self.vectors, v)
        projection = numpy.floor(projection / self.bin_width)
        # Return key
        return ['_'.join([str(int(x)) for x in projection])]

########NEW FILE########
__FILENAME__ = unibucket
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy

from nearpy.hashes.lshash import LSHash


class UniBucket(LSHash):
    """
    Puts alls vectors in one bucket. This is used for testing
    the engines and experiments.
    """

    def __init__(self, hash_name):
        """ Just keeps the name. """
        super(UniBucket, self).__init__(hash_name)
        self.dim = None

    def reset(self, dim):
        """ Resets / Initializes the hash for the specified dimension. """
        self.dim = dim

    def hash_vector(self, v):
        """
        Hashes the vector and returns the bucket key as string.
        """
        # Return bucket key identical to vector string representation
        return [self.hash_name+'']

########NEW FILE########
__FILENAME__ = storage
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


class Storage(object):
    """ Interface for storage adapters. """

    def store_vector(self, hash_name, bucket_key, v, data):
        """
        Stores vector and JSON-serializable data in bucket with specified key.
        """
        raise NotImplementedError

    def get_bucket(self, hash_name, bucket_key):
        """
        Returns bucket content as list of tuples (vector, data).
        """
        raise NotImplementedError

    def clean_buckets(self, hash_name):
        """
        Removes all buckets and their content.
        """
        raise NotImplementedError

    def clean_all_buckets(self):
        """
        Removes all buckets and their content.
        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = storage_memory
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from nearpy.storage.storage import Storage


class MemoryStorage(Storage):
    """ Simple implementation using python dicts. """

    def __init__(self):
        self.buckets = {}

    def store_vector(self, hash_name, bucket_key, v, data):
        """
        Stores vector and JSON-serializable data in bucket with specified key.
        """

        if not hash_name in self.buckets:
            self.buckets[hash_name] = {}

        if not bucket_key in self.buckets[hash_name]:
            self.buckets[hash_name][bucket_key] = []
        self.buckets[hash_name][bucket_key].append((v, data))

    def get_bucket(self, hash_name, bucket_key):
        """
        Returns bucket content as list of tuples (vector, data).
        """
        if hash_name in self.buckets:
            if bucket_key in self.buckets[hash_name]:
                return self.buckets[hash_name][bucket_key]
        return []

    def clean_buckets(self, hash_name):
        """
        Removes all buckets and their content for specified hash.
        """
        self.buckets[hash_name] = {}

    def clean_all_buckets(self):
        """
        Removes all buckets from all hashes and their content.
        """
        self.buckets = {}

########NEW FILE########
__FILENAME__ = storage_mongo
# Planned...
########NEW FILE########
__FILENAME__ = storage_pickle
# Planned...

########NEW FILE########
__FILENAME__ = storage_redis
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import redis
import json
import numpy

from nearpy.storage.storage import Storage
from nearpy.utils import want_string


class RedisStorage(Storage):
    """ Storage using redis. """

    def __init__(self, redis_object):
        """ Uses specified redis object for storage. """
        self.redis_object = redis_object

    def store_vector(self, hash_name, bucket_key, v, data):
        """
        Stores vector and JSON-serializable data in bucket with specified key.
        """
        redis_key = 'nearpy_%s_%s' % (hash_name, bucket_key)

        # Make sure it is a 1d vector
        v = numpy.reshape(v, v.shape[0])

        val_dict = {'vector': v.tolist()}
        if data:
            val_dict['data'] = data

        self.redis_object.rpush(redis_key, json.dumps(val_dict))

    def get_bucket(self, hash_name, bucket_key):
        """
        Returns bucket content as list of tuples (vector, data).
        """
        redis_key = 'nearpy_%s_%s' % (hash_name, bucket_key)
        items = self.redis_object.lrange(redis_key, 0, -1)
        results = []
        for item_str in items:
            val_dict = json.loads(want_string(item_str))
            vector = numpy.fromiter(val_dict['vector'], dtype=numpy.float64)
            if 'data' in val_dict:
                results.append((vector, val_dict['data']))
            else:
                results.append((vector, None))

        return results

    def clean_buckets(self, hash_name):
        """
        Removes all buckets and their content for specified hash.
        """
        bucket_keys = self.redis_object.keys(pattern='nearpy_%s_*' % hash_name)
        for bucket_key in bucket_keys:
            self.redis_object.delete(bucket_key)

    def clean_all_buckets(self):
        """
        Removes all buckets from all hashes and their content.
        """
        bucket_keys = self.redis_object.keys(pattern='nearpy_*')
        for bucket_key in bucket_keys:
            self.redis_object.delete(bucket_key)

########NEW FILE########
__FILENAME__ = distances_tests
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy
import unittest

from nearpy.distances import EuclideanDistance, AngularDistance

########################################################################

# Helper functions

def equal_with_tolerance(x, y, tolerance):
    return x > (y-tolerance) and x < (y+tolerance)

def test_distance_symmetry(test_obj, distance):
    for k in range(100):
        x = numpy.random.randn(10)
        y = numpy.random.randn(10)
        d_xy = distance.distance(x, y)
        d_yx = distance.distance(y, x)

        # I had precision issues with a local install. This test is more tolerant to that.
        test_obj.assertTrue(equal_with_tolerance(d_xy, d_yx, 0.000000000000001))

def test_distance_triangle_inequality(test_obj, distance):
    for k in range(100):
        x = numpy.random.randn(10)
        y = numpy.random.randn(10)
        z = numpy.random.randn(10)

        d_xy = distance.distance(x, y)
        d_xz = distance.distance(x, z)
        d_yz = distance.distance(y, z)

        test_obj.assertTrue(d_xy <= d_xz + d_yz)

########################################################################


class TestEuclideanDistance(unittest.TestCase):

    def setUp(self):
        self.euclidean = EuclideanDistance()

    def test_triangle_inequality(self):
        test_distance_triangle_inequality(self, self.euclidean)

    def test_symmetry(self):
        test_distance_symmetry(self, self.euclidean)


class TestAngularDistance(unittest.TestCase):

    def setUp(self):
        self.angular = AngularDistance()

    def test_symmetry(self):
        test_distance_symmetry(self, self.angular)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = engine_tests
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy
import unittest

from nearpy import Engine


class TestEngine(unittest.TestCase):

    def setUp(self):
        self.engine = Engine(1000)

    def test_retrieval(self):
        for k in range(100):
            self.engine.clean_all_buckets()
            x = numpy.random.randn(1000)
            x_data = 'data'
            self.engine.store_vector(x, x_data)
            n = self.engine.neighbours(x)
            y = n[0][0]
            y_data = n[0][1]
            y_distance = n[0][2]
            self.assertTrue((y == x).all())
            self.assertEqual(y_data, x_data)
            self.assertEqual(y_distance, 0.0)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = experiments_tests
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
from __future__ import print_function

import numpy
import unittest

from nearpy.experiments import RecallPrecisionExperiment
from nearpy.hashes import UniBucket, RandomDiscretizedProjections, \
    RandomBinaryProjections, PCABinaryProjections
from nearpy.filters import NearestFilter, UniqueFilter
from nearpy.distances import AngularDistance

from nearpy import Engine


class TestRecallExperiment(unittest.TestCase):

    def test_experiment_with_unibucket_1(self):
        dim = 50
        vector_count = 100
        vectors = numpy.random.randn(dim, vector_count)
        unibucket = UniBucket('testHash')
        nearest = NearestFilter(10)
        engine = Engine(dim, lshashes=[unibucket],
                        vector_filters=[nearest])
        exp = RecallPrecisionExperiment(10, vectors)
        result = exp.perform_experiment([engine])

        # Both recall and precision must be one in this case
        self.assertEqual(result[0][0], 1.0)
        self.assertEqual(result[0][1], 1.0)

    def test_experiment_with_unibucket_2(self):
        dim = 50
        vector_count = 100
        vectors = numpy.random.randn(dim, vector_count)
        unibucket = UniBucket('testHash')
        nearest = NearestFilter(10)
        engine = Engine(dim, lshashes=[unibucket],
                        vector_filters=[nearest])
        exp = RecallPrecisionExperiment(5, vectors)
        result = exp.perform_experiment([engine])

        # In this case precision is only 0.5
        # because the engine returns 10 nearest, but
        # the experiment only looks for 5 nearest.
        self.assertEqual(result[0][0], 1.0)
        self.assertEqual(result[0][1], 0.5)

    def test_experiment_with_unibucket_3(self):
        dim = 50
        vector_count = 100
        vectors = numpy.random.randn(dim, vector_count)
        unibucket = UniBucket('testHash')
        nearest = NearestFilter(5)
        engine = Engine(dim, lshashes=[unibucket],
                        vector_filters=[nearest])
        exp = RecallPrecisionExperiment(10, vectors)
        result = exp.perform_experiment([engine])

        # In this case recall is only 0.5
        # because the engine returns 5 nearest, but
        # the experiment looks for 10 nearest.
        self.assertEqual(result[0][0], 0.5)
        self.assertEqual(result[0][1], 1.0)

    def test_experiment_with_list_1(self):
        dim = 50
        vector_count = 100
        vectors = []
        for index in range(vector_count):
            vectors.append(numpy.random.randn(dim))
        unibucket = UniBucket('testHash')
        nearest = NearestFilter(10)
        engine = Engine(dim, lshashes=[unibucket],
                        vector_filters=[nearest])
        exp = RecallPrecisionExperiment(10, vectors)
        result = exp.perform_experiment([engine])

        # Both recall and precision must be one in this case
        self.assertEqual(result[0][0], 1.0)
        self.assertEqual(result[0][1], 1.0)

    def test_experiment_with_list_2(self):
        dim = 50
        vector_count = 100
        vectors = []
        for index in range(vector_count):
            vectors.append(numpy.random.randn(dim))
        unibucket = UniBucket('testHash')
        nearest = NearestFilter(10)
        engine = Engine(dim, lshashes=[unibucket],
                        vector_filters=[nearest])
        exp = RecallPrecisionExperiment(5, vectors)
        result = exp.perform_experiment([engine])

        # In this case precision is only 0.5
        # because the engine returns 10 nearest, but
        # the experiment only looks for 5 nearest.
        self.assertEqual(result[0][0], 1.0)
        self.assertEqual(result[0][1], 0.5)

    def test_experiment_with_list_3(self):
        dim = 50
        vector_count = 100
        vectors = []
        for index in range(vector_count):
            vectors.append(numpy.random.randn(dim))
        unibucket = UniBucket('testHash')
        nearest = NearestFilter(5)
        engine = Engine(dim, lshashes=[unibucket],
                        vector_filters=[nearest])
        exp = RecallPrecisionExperiment(10, vectors)
        result = exp.perform_experiment([engine])

        # In this case recall is only 0.5
        # because the engine returns 5 nearest, but
        # the experiment looks for 10 nearest.
        self.assertEqual(result[0][0], 0.5)
        self.assertEqual(result[0][1], 1.0)

    def test_random_discretized_projections(self):
        dim = 4
        vector_count = 5000
        vectors = numpy.random.randn(dim, vector_count)

        # First get recall and precision for one 1-dim random hash
        rdp = RandomDiscretizedProjections('rdp', 1, 0.01)
        nearest = NearestFilter(10)
        engine = Engine(dim, lshashes=[rdp],
                        vector_filters=[nearest])
        exp = RecallPrecisionExperiment(10, vectors)
        result = exp.perform_experiment([engine])

        recall1 = result[0][0]
        precision1 = result[0][1]
        searchtime1 = result[0][2]

        print('\nRecall RDP: %f, Precision RDP: %f, SearchTime RDP: %f\n' % \
            (recall1, precision1, searchtime1))

        # Then get recall and precision for one 4-dim random hash
        rdp = RandomDiscretizedProjections('rdp', 2, 0.2)
        engine = Engine(dim, lshashes=[rdp],
                        vector_filters=[nearest])
        result = exp.perform_experiment([engine])

        recall2 = result[0][0]
        precision2 = result[0][1]
        searchtime2 = result[0][2]

        print('\nRecall RDP: %f, Precision RDP: %f, SearchTime RDP: %f\n' % \
            (recall2, precision2, searchtime2))

        # Many things are random here, but the precision should increase
        # with dimension
        self.assertTrue(precision2 > precision1)

    def test_random_binary_projections(self):
        dim = 4
        vector_count = 5000
        vectors = numpy.random.randn(dim, vector_count)

        # First get recall and precision for one 1-dim random hash
        rbp = RandomBinaryProjections('rbp', 32)
        nearest = NearestFilter(10)
        engine = Engine(dim, lshashes=[rbp],
                        vector_filters=[nearest])
        exp = RecallPrecisionExperiment(10, vectors)
        result = exp.perform_experiment([engine])

        recall1 = result[0][0]
        precision1 = result[0][1]
        searchtime1 = result[0][2]

        print('\nRecall RBP: %f, Precision RBP: %f, SearchTime RBP: %f\n' % \
            (recall1, precision1, searchtime1))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = filters_tests
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy
import unittest

from nearpy.filters import NearestFilter, DistanceThresholdFilter, UniqueFilter


class TestVectorFilters(unittest.TestCase):

    def setUp(self):
        self.V = []
        self.V.append((numpy.array([0]), 'data1', 0.4))
        self.V.append((numpy.array([1]), 'data2', 0.9))
        self.V.append((numpy.array([2]), 'data3', 1.4))
        self.V.append((numpy.array([3]), 'data4', 2.1))
        self.V.append((numpy.array([4]), 'data5', 0.1))
        self.V.append((numpy.array([5]), 'data6', 8.7))
        self.V.append((numpy.array([6]), 'data7', 3.4))
        self.V.append((numpy.array([7]), 'data8', 2.8))

        self.threshold_filter = DistanceThresholdFilter(1.0)
        self.nearest_filter = NearestFilter(5)
        self.unique = UniqueFilter()

    def test_thresholding(self):
        result = self.threshold_filter.filter_vectors(self.V)
        self.assertEqual(len(result), 3)
        self.assertTrue(self.V[0] in result)
        self.assertTrue(self.V[1] in result)
        self.assertTrue(self.V[4] in result)

    def test_nearest(self):
        result = self.nearest_filter.filter_vectors(self.V)
        self.assertEqual(len(result), 5)
        self.assertTrue(self.V[0] in result)
        self.assertTrue(self.V[1] in result)
        self.assertTrue(self.V[4] in result)
        self.assertTrue(self.V[2] in result)
        self.assertTrue(self.V[3] in result)

    def test_unique(self):
        W = self.V
        W.append((numpy.array([7]), 'data8', 2.8))
        W.append((numpy.array([0]), 'data1', 2.8))
        W.append((numpy.array([1]), 'data2', 2.8))
        W.append((numpy.array([6]), 'data7', 2.8))

        result = self.unique.filter_vectors(W)
        self.assertEqual(len(result), 8)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = hashes_tests
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy
import unittest

from nearpy.hashes import RandomBinaryProjections, \
    RandomDiscretizedProjections, \
    PCABinaryProjections


class TestRandomBinaryProjections(unittest.TestCase):

    def setUp(self):
        self.rbp = RandomBinaryProjections('testHash', 10)
        self.rbp.reset(100)

    def test_hash_format(self):
        h = self.rbp.hash_vector(numpy.random.randn(100))
        self.assertEqual(len(h), 1)
        self.assertEqual(type(h[0]), type(''))
        self.assertEqual(len(h[0]), 10)
        for c in h[0]:
            self.assertTrue(c == '1' or c == '0')

    def test_hash_deterministic(self):
        x = numpy.random.randn(100)
        first_hash = self.rbp.hash_vector(x)[0]
        for k in range(100):
            self.assertEqual(first_hash, self.rbp.hash_vector(x)[0])


class TestRandomDiscretizedProjections(unittest.TestCase):

    def setUp(self):
        self.rbp = RandomDiscretizedProjections('testHash', 10, 0.1)
        self.rbp.reset(100)

    def test_hash_format(self):
        h = self.rbp.hash_vector(numpy.random.randn(100))
        self.assertEqual(len(h), 1)
        self.assertEqual(type(h[0]), type(''))

    def test_hash_deterministic(self):
        x = numpy.random.randn(100)
        first_hash = self.rbp.hash_vector(x)[0]
        for k in range(100):
            self.assertEqual(first_hash, self.rbp.hash_vector(x)[0])


class TestPCABinaryProjections(unittest.TestCase):

    def setUp(self):
        self.vectors = numpy.random.randn(10, 100)
        self.pbp = PCABinaryProjections('pbp', 4, self.vectors)

    def test_hash_format(self):
        h = self.pbp.hash_vector(numpy.random.randn(10))
        self.assertEqual(len(h), 1)
        self.assertEqual(type(h[0]), type(''))
        self.assertEqual(len(h[0]), 4)
        for c in h[0]:
            self.assertTrue(c == '1' or c == '0')

    def test_hash_deterministic(self):
        x = numpy.random.randn(10)
        first_hash = self.pbp.hash_vector(x)[0]
        for k in range(100):
            self.assertEqual(first_hash, self.pbp.hash_vector(x)[0])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = storage_tests
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import numpy
import unittest

from redis import Redis

from nearpy.storage import MemoryStorage, RedisStorage


class TestStorage(unittest.TestCase):

    def setUp(self):
        self.memory = MemoryStorage()
        self.redis_object = Redis(host='localhost',
                                  port=6379, db=0)
        self.redis_storage = RedisStorage(self.redis_object)

    def test_memory_storage(self):
        x = numpy.random.randn(100, 1)
        bucket_key = '23749283743928748'
        x_data = ['one', 'two', 'three']
        self.memory.store_vector('testHash', bucket_key, x, x_data)
        X = self.memory.get_bucket('testHash', bucket_key)
        self.assertEqual(len(X), 1)
        y = X[0][0]
        y_data = X[0][1]
        self.assertEqual(len(y), len(x))
        self.assertEqual(type(x), type(y))
        for k in range(100):
            self.assertEqual(y[k], x[k])
        self.assertEqual(type(y_data), type(x_data))
        self.assertEqual(len(y_data), len(x_data))
        for k in range(3):
            self.assertEqual(y_data[k], x_data[k])
        self.memory.clean_all_buckets()
        self.assertEqual(self.memory.get_bucket('testHash', bucket_key), [])

    def test_redis_storage(self):
        self.redis_storage.clean_all_buckets()
        x = numpy.random.randn(100, 1)
        bucket_key = '23749283743928748'
        x_data = ['one', 'two', 'three']
        self.redis_storage.store_vector('testHash', bucket_key, x, x_data)
        X = self.redis_storage.get_bucket('testHash', bucket_key)
        self.assertEqual(len(X), 1)
        y = X[0][0]
        y_data = X[0][1]
        self.assertEqual(len(y), len(x))
        self.assertEqual(type(x), type(y))
        for k in range(100):
            self.assertEqual(y[k], x[k])
        self.assertEqual(type(y_data), type(x_data))
        self.assertEqual(len(y_data), len(x_data))
        for k in range(3):
            self.assertEqual(y_data[k], x_data[k])
        self.redis_storage.clean_all_buckets()
        self.assertEqual(self.redis_storage.get_bucket('testHash',
                                                       bucket_key), [])

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

# Copyright (c) 2013 Ole Krause-Sparmann

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import numpy



def numpy_array_from_list_or_numpy_array(vectors):
    """
    Returns numpy array representation of argument.

    Argument maybe numpy array (input is returned)
    or a list of numpy vectors.
    """
    # If vectors is not a numpy matrix, create one
    if not isinstance(vectors, numpy.ndarray):
        V = numpy.zeros((vectors[0].shape[0], len(vectors)))
        for index in range(len(vectors)):
            vector = vectors[index]
            V[:, index] = vector
        return V

    return vectors


def perform_pca(A):
    """
    Computes eigenvalues and eigenvectors of covariance matrix of A.
    The rows of a correspond to observations, the columns to variables.
    """
    # First subtract the mean
    M = (A-numpy.mean(A.T, axis=1)).T
    # Get eigenvectors and values of covariance matrix
    return numpy.linalg.eig(numpy.cov(M))


PY2 = sys.version_info[0] == 2
if PY2:
    bytes_type = str
else:
    bytes_type = bytes


def want_string(arg, encoding='utf-8'):
    if isinstance(arg, bytes_type):
        rv = arg.decode(encoding)
    else:
        rv = arg
    return rv

########NEW FILE########
__FILENAME__ = run_tests

import unittest

import nearpy.tests as tests

suite = unittest.TestLoader().loadTestsFromTestCase(
    tests.TestStorage)
unittest.TextTestRunner(verbosity=2).run(suite)

suite = unittest.TestLoader().loadTestsFromTestCase(
    tests.TestRandomBinaryProjections)
unittest.TextTestRunner(verbosity=2).run(suite)

suite = unittest.TestLoader().loadTestsFromTestCase(
    tests.TestRandomDiscretizedProjections)
unittest.TextTestRunner(verbosity=2).run(suite)

suite = unittest.TestLoader().loadTestsFromTestCase(
    tests.TestEngine)
unittest.TextTestRunner(verbosity=2).run(suite)

suite = unittest.TestLoader().loadTestsFromTestCase(
    tests.TestEuclideanDistance)
unittest.TextTestRunner(verbosity=2).run(suite)

suite = unittest.TestLoader().loadTestsFromTestCase(
    tests.TestAngularDistance)
unittest.TextTestRunner(verbosity=2).run(suite)

suite = unittest.TestLoader().loadTestsFromTestCase(
    tests.TestVectorFilters)
unittest.TextTestRunner(verbosity=2).run(suite)

suite = unittest.TestLoader().loadTestsFromTestCase(
    tests.TestPCABinaryProjections)
unittest.TextTestRunner(verbosity=2).run(suite)

# TODO: Experiment tests are out of date!
#suite = unittest.TestLoader().loadTestsFromTestCase(
#    tests.TestRecallExperiment)
#unittest.TextTestRunner(verbosity=2).run(suite)

########NEW FILE########
