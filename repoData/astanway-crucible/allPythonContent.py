__FILENAME__ = algorithms
import pandas
import numpy as np
import scipy
import statsmodels.api as sm
import matplotlib.pyplot as plt
import traceback
import os
from multiprocessing import Process
from time import time
from settings import ALGORITHMS
from os.path import dirname, join, abspath

"""
This is no man's land. Do anything you want in here,
as long as you return a boolean that determines whether the input
timeseries is anomalous or not.

To add an algorithm, define it here, and add its name to settings.ALGORITHMS.
"""

def tail_avg(timeseries):
    """
    This is a utility function used to calculate the average of the last three
    datapoints in the series as a measure, instead of just the last datapoint.
    It reduces noise, but it also reduces sensitivity and increases the delay
    to detection.
    """
    try:
        t = (timeseries[-1][1] + timeseries[-2][1] + timeseries[-3][1]) / 3
        return t
    except IndexError:
        return timeseries[-1][1]

def median_absolute_deviation(timeseries):
    """
    A timeseries is anomalous if the deviation of its latest datapoint with
    respect to the median is X times larger than the median of deviations.
    """

    series = pandas.Series([x[1] for x in timeseries])
    median = series.median()
    demedianed = np.abs(series - median)
    median_deviation = demedianed.median()

    # The test statistic is infinite when the median is zero,
    # so it becomes super sensitive. We play it safe and skip when this happens.
    if median_deviation == 0:
        return False

    test_statistic = demedianed.iget(-1) / median_deviation

    # Completely arbitary...triggers if the median deviation is
    # 6 times bigger than the median
    if test_statistic > 6:
        return True

def grubbs(timeseries):
    """
    A timeseries is anomalous if the Z score is greater than the Grubb's score.
    """

    series = scipy.array([x[1] for x in timeseries])
    stdDev = scipy.std(series)
    mean = np.mean(series)
    tail_average = tail_avg(timeseries)
    z_score = (tail_average - mean) / stdDev
    len_series = len(series)
    threshold = scipy.stats.t.isf(.05 / (2 * len_series) , len_series - 2)
    threshold_squared = threshold * threshold
    grubbs_score = ((len_series - 1) / np.sqrt(len_series)) * np.sqrt(threshold_squared / (len_series - 2 + threshold_squared))

    return z_score > grubbs_score

def first_hour_average(timeseries):
    """
    Calcuate the simple average over one hour, FULL_DURATION seconds ago.
    A timeseries is anomalous if the average of the last three datapoints
    are outside of three standard deviations of this value.
    """
    last_hour_threshold = time() - (86400 - 3600)
    series = pandas.Series([x[1] for x in timeseries if x[0] < last_hour_threshold])
    mean = (series).mean()
    stdDev = (series).std()
    t = tail_avg(timeseries)

    return abs(t - mean) > 3 * stdDev

def stddev_from_average(timeseries):
    """
    A timeseries is anomalous if the absolute value of the average of the latest
    three datapoint minus the moving average is greater than one standard
    deviation of the average. This does not exponentially weight the MA and so
    is better for detecting anomalies with respect to the entire series.
    """
    series = pandas.Series([x[1] for x in timeseries])
    mean = series.mean()
    stdDev = series.std()
    t = tail_avg(timeseries)

    return abs(t - mean) > 3 * stdDev

def stddev_from_moving_average(timeseries):
    """
    A timeseries is anomalous if the absolute value of the average of the latest
    three datapoint minus the moving average is greater than one standard
    deviation of the moving average. This is better for finding anomalies with
    respect to the short term trends.
    """
    series = pandas.Series([x[1] for x in timeseries])
    expAverage = pandas.stats.moments.ewma(series, com=50)
    stdDev = pandas.stats.moments.ewmstd(series, com=50)

    return abs(series.iget(-1) - expAverage.iget(-1)) > 3 * stdDev.iget(-1)

def mean_subtraction_cumulation(timeseries):
    """
    A timeseries is anomalous if the value of the next datapoint in the
    series is farther than a standard deviation out in cumulative terms
    after subtracting the mean from each data point.
    """

    series = pandas.Series([x[1] if x[1] else 0 for x in timeseries])
    series = series - series[0:len(series) - 1].mean()
    stdDev = series[0:len(series) - 1].std()
    expAverage = pandas.stats.moments.ewma(series, com=15)

    return abs(series.iget(-1)) > 3 * stdDev

def least_squares(timeseries):
    """
    A timeseries is anomalous if the average of the last three datapoints
    on a projected least squares model is greater than three sigma.
    """

    x = np.array([t[0] for t in timeseries])
    y = np.array([t[1] for t in timeseries])
    A = np.vstack([x, np.ones(len(x))]).T
    results = np.linalg.lstsq(A, y)
    residual = results[1]
    m, c = np.linalg.lstsq(A, y)[0]
    errors = []
    for i, value in enumerate(y):
    	projected = m * x[i] + c
    	error = value - projected
    	errors.append(error)

    if len(errors) < 3:
    	return False

    std_dev = scipy.std(errors)
    t = (errors[-1] + errors[-2] + errors[-3]) / 3

    return abs(t) > std_dev * 3 and round(std_dev) != 0 and round(t) != 0

def histogram_bins(timeseries):
    """
    A timeseries is anomalous if the average of the last three datapoints falls
    into a histogram bin with less than 20 other datapoints (you'll need to tweak
    that number depending on your data)

    Returns: the size of the bin which contains the tail_avg. Smaller bin size
    means more anomalous.
    """

    series = scipy.array([x[1] for x in timeseries])
    t = tail_avg(timeseries)
    h = np.histogram(series, bins=15)
    bins = h[1]
    for index, bin_size in enumerate(h[0]):
        if bin_size <= 20:
            # Is it in the first bin?
            if index == 0:
                if t <= bins[0]:
                    return True
            # Is it in the current bin?
            elif t >= bins[index] and t < bins[index + 1]:
                    return True

    return False

def ks_test(timeseries):
    """
    A timeseries is anomalous if 2 sample Kolmogorov-Smirnov test indicates
    that data distribution for last 10 minutes is different from last hour.
    It produces false positives on non-stationary series so Augmented
    Dickey-Fuller test applied to check for stationarity.
    """

    hour_ago = time() - 3600
    ten_minutes_ago = time() - 600
    reference = scipy.array([x[1] for x in timeseries if x[0] >= hour_ago and x[0] < ten_minutes_ago])
    probe = scipy.array([x[1] for x in timeseries if x[0] >= ten_minutes_ago])

    if reference.size < 20 or probe.size < 20:
        return False

    ks_d,ks_p_value = scipy.stats.ks_2samp(reference, probe)

    if ks_p_value < 0.05 and ks_d > 0.5:
        adf = sm.tsa.stattools.adfuller(reference, 10)
        if  adf[1] < 0.05:
            return True

    return False

def run_algorithms(timeseries, timeseries_name):
    """
    Iteratively run algorithms.
    """
    __results__ = abspath(join(dirname( __file__ ), '..', 'results'))

    try:
        for algorithm in ALGORITHMS:
            x_vals = np.arange(len(timeseries))
            y_vals = np.array([y[1] for y in timeseries])
            plt.plot(x_vals, y_vals)

            # Start a couple datapoints in for the tail average
            for index in range(10, len(timeseries)):
                sliced = timeseries[:index]
                anomaly = globals()[algorithm](sliced)
                
                # Point out the datapoint if it's anomalous
                if anomaly:
                    plt.plot([index], [sliced[-1][1]], 'ro')
                        
            plt.savefig(__results__ + "/"+ algorithm + "-" + timeseries_name + ".png")
            print algorithm
    except:
        print("Algorithm error: " + traceback.format_exc())

########NEW FILE########
__FILENAME__ = crucible
import logging
from time import time
from multiprocessing import Process
import os
from os.path import dirname, join, abspath, isfile
from sys import exit
import traceback
from settings import ALGORITHMS
import json
import shutil
from os import getcwd, listdir, makedirs

from algorithms import run_algorithms

class Crucible():

    def run(self):
        """
        Called when the process intializes.
        """
        __data__ = abspath(join(dirname( __file__ ), '..', 'data'))
        files = [ f for f in listdir(__data__) 
                    if isfile(join(__data__,f)) ]

        # Spawn processes
        pids = []
        for index, ts_name in enumerate(files):
            if ts_name == ".DS_Store":
            	continue

            __data__ = abspath(join(dirname( __file__ ), '..', 'data'))
            with open(join(__data__ + "/" + ts_name), 'r') as f:
                timeseries = json.loads(f.read())
                p = Process(target=run_algorithms, args=(timeseries, ts_name))
                pids.append(p)
                p.start()

        # Send wait signal to zombie processes
        for p in pids:
            p.join()

if __name__ == "__main__":
    """
    Start Crucible.
    """

    # Make sure we can run all the algorithms
    try:
        from algorithms import *
        timeseries = map(list, zip(map(float, range(int(time())-86400, int(time())+1)), [1]*86401))
        ensemble = [globals()[algorithm](timeseries) for algorithm in ALGORITHMS]
    except KeyError as e:
        print "Algorithm %s deprecated or not defined; check settings.ALGORITHMS" % e
        exit(1)
    except Exception as e:
        print "Algorithm test run failed."
        traceback.print_exc()
        exit(1)
    
    __results__ = abspath(join(dirname( __file__ ), '..', 'results'))

    try:
        shutil.rmtree(__results__)
        makedirs(__results__)
    except:
        makedirs(__results__)

    crucible = Crucible()
    crucible.run()

########NEW FILE########
__FILENAME__ = settings
# These are the algorithms that the Analyzer will run. To add a new algorithm,
# you must both define the algorithm in algorithms.py and add its name here.
ALGORITHMS = [
                'first_hour_average',
                'mean_subtraction_cumulation',
                'stddev_from_average',
                'stddev_from_moving_average',
                # 'least_squares',
                'grubbs',
                'histogram_bins',
                'median_absolute_deviation',
                'ks_test',
             ]
########NEW FILE########
__FILENAME__ = graphite-grab
# Grab a Graphite JSON formatted timeseries for use in Crucible
# usage: graphite-grab.py "http://graphite.etsycorp.com/render/?width=1400&from=-24hour&target=stats.timers.api.getPage.200.mean&format=json"
import json
import sys
import requests
import urlparse
import os
from os.path import dirname, join, abspath

url = sys.argv[1]

if "&format=json" not in url:
	url += "&format=json"

r = requests.get(url)
js = r.json()
datapoints = js[0]['datapoints']

converted = []
for datapoint in datapoints:
    try:
    	new_datapoint = [float(datapoint[1]), float(datapoint[0])]
    	converted.append(new_datapoint)
    except:
        continue

parsed = urlparse.urlparse(url)
target = urlparse.parse_qs(parsed.query)['target'][0]

data_folder = abspath(join(dirname( __file__ ), '..', 'data'))

with open(data_folder + "/" + target + '.json', 'w') as f:
    f.write(json.dumps(converted))
    f.close()

########NEW FILE########
