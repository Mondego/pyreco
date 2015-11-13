__FILENAME__ = alerters
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from smtplib import SMTP
import alerters
import settings


"""
Create any alerter you want here. The function will be invoked from trigger_alert.
Two arguments will be passed, both of them tuples: alert and metric.

alert: the tuple specified in your settings:
    alert[0]: The matched substring of the anomalous metric
    alert[1]: the name of the strategy being used to alert
    alert[2]: The timeout of the alert that was triggered
metric: information about the anomaly itself
    metric[0]: the anomalous value
    metric[1]: The full name of the anomalous metric
"""


def alert_smtp(alert, metric):

    # For backwards compatibility
    if '@' in alert[1]:
        sender = settings.ALERT_SENDER
        recipient = alert[1]
    else:
        sender = settings.SMTP_OPTS['sender']
        recipients = settings.SMTP_OPTS['recipients'][alert[0]]

    # Backwards compatibility
    if type(recipients) is str:
        recipients = [recipients]

    for recipient in recipients:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '[skyline alert] ' + metric[1]
        msg['From'] = sender
        msg['To'] = recipient
        link = settings.GRAPH_URL % (metric[1])
        body = 'Anomalous value: %s <br> Next alert in: %s seconds <a href="%s"><img src="%s"/></a>' % (metric[0], alert[2], link, link)
        msg.attach(MIMEText(body, 'html'))
        s = SMTP('127.0.0.1')
        s.sendmail(sender, recipient, msg.as_string())
        s.quit()


def alert_pagerduty(alert, metric):
    import pygerduty
    pager = pygerduty.PagerDuty(settings.PAGERDUTY_OPTS['subdomain'], settings.PAGERDUTY_OPTS['auth_token'])
    pager.trigger_incident(settings.PAGERDUTY_OPTS['key'], "Anomalous metric: %s (value: %s)" % (metric[1], metric[0]))


def alert_hipchat(alert, metric):
    import hipchat
    hipster = hipchat.HipChat(token=settings.HIPCHAT_OPTS['auth_token'])
    rooms = settings.HIPCHAT_OPTS['rooms'][alert[0]]
    link = settings.GRAPH_URL % (metric[1])

    for room in rooms:
        hipster.method('rooms/message', method='POST', parameters={'room_id': room, 'from': 'Skyline', 'color': settings.HIPCHAT_OPTS['color'], 'message': 'Anomaly: <a href="%s">%s</a> : %s' % (link, metric[1], metric[0])})


def trigger_alert(alert, metric):

    if '@' in alert[1]:
        strategy = 'alert_smtp'
    else:
        strategy = 'alert_' + alert[1]

    getattr(alerters, strategy)(alert, metric)

########NEW FILE########
__FILENAME__ = algorithms
import pandas
import numpy as np
import scipy
import statsmodels.api as sm
import traceback
import logging
from time import time
from msgpack import unpackb, packb
from redis import StrictRedis

from settings import (
    ALGORITHMS,
    CONSENSUS,
    FULL_DURATION,
    MAX_TOLERABLE_BOREDOM,
    MIN_TOLERABLE_LENGTH,
    STALE_PERIOD,
    REDIS_SOCKET_PATH,
    ENABLE_SECOND_ORDER,
    BOREDOM_SET_SIZE,
)

from algorithm_exceptions import *

logger = logging.getLogger("AnalyzerLog")
redis_conn = StrictRedis(unix_socket_path=REDIS_SOCKET_PATH)

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
    threshold = scipy.stats.t.isf(.05 / (2 * len_series), len_series - 2)
    threshold_squared = threshold * threshold
    grubbs_score = ((len_series - 1) / np.sqrt(len_series)) * np.sqrt(threshold_squared / (len_series - 2 + threshold_squared))

    return z_score > grubbs_score


def first_hour_average(timeseries):
    """
    Calcuate the simple average over one hour, FULL_DURATION seconds ago.
    A timeseries is anomalous if the average of the last three datapoints
    are outside of three standard deviations of this value.
    """
    last_hour_threshold = time() - (FULL_DURATION - 3600)
    series = pandas.Series([x[1] for x in timeseries if x[0] < last_hour_threshold])
    mean = (series).mean()
    stdDev = (series).std()
    t = tail_avg(timeseries)

    return abs(t - mean) > 3 * stdDev


def stddev_from_average(timeseries):
    """
    A timeseries is anomalous if the absolute value of the average of the latest
    three datapoint minus the moving average is greater than three standard
    deviations of the average. This does not exponentially weight the MA and so
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
    three datapoint minus the moving average is greater than three standard
    deviations of the moving average. This is better for finding anomalies with
    respect to the short term trends.
    """
    series = pandas.Series([x[1] for x in timeseries])
    expAverage = pandas.stats.moments.ewma(series, com=50)
    stdDev = pandas.stats.moments.ewmstd(series, com=50)

    return abs(series.iget(-1) - expAverage.iget(-1)) > 3 * stdDev.iget(-1)


def mean_subtraction_cumulation(timeseries):
    """
    A timeseries is anomalous if the value of the next datapoint in the
    series is farther than three standard deviations out in cumulative terms
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

    ks_d, ks_p_value = scipy.stats.ks_2samp(reference, probe)

    if ks_p_value < 0.05 and ks_d > 0.5:
        adf = sm.tsa.stattools.adfuller(reference, 10)
        if adf[1] < 0.05:
            return True

    return False


def is_anomalously_anomalous(metric_name, ensemble, datapoint):
    """
    This method runs a meta-analysis on the metric to determine whether the
    metric has a past history of triggering. TODO: weight intervals based on datapoint
    """
    # We want the datapoint to avoid triggering twice on the same data
    new_trigger = [time(), datapoint]

    # Get the old history
    raw_trigger_history = redis_conn.get('trigger_history.' + metric_name)
    if not raw_trigger_history:
        redis_conn.set('trigger_history.' + metric_name, packb([(time(), datapoint)]))
        return True

    trigger_history = unpackb(raw_trigger_history)

    # Are we (probably) triggering on the same data?
    if (new_trigger[1] == trigger_history[-1][1] and
            new_trigger[0] - trigger_history[-1][0] <= 300):
                return False

    # Update the history
    trigger_history.append(new_trigger)
    redis_conn.set('trigger_history.' + metric_name, packb(trigger_history))

    # Should we surface the anomaly?
    trigger_times = [x[0] for x in trigger_history]
    intervals = [
        trigger_times[i + 1] - trigger_times[i]
        for i, v in enumerate(trigger_times)
        if (i + 1) < len(trigger_times)
    ]

    series = pandas.Series(intervals)
    mean = series.mean()
    stdDev = series.std()

    return abs(intervals[-1] - mean) > 3 * stdDev


def run_selected_algorithm(timeseries, metric_name):
    """
    Filter timeseries and run selected algorithm.
    """
    # Get rid of short series
    if len(timeseries) < MIN_TOLERABLE_LENGTH:
        raise TooShort()

    # Get rid of stale series
    if time() - timeseries[-1][0] > STALE_PERIOD:
        raise Stale()

    # Get rid of boring series
    if len(set(item[1] for item in timeseries[-MAX_TOLERABLE_BOREDOM:])) == BOREDOM_SET_SIZE:
        raise Boring()

    try:
        ensemble = [globals()[algorithm](timeseries) for algorithm in ALGORITHMS]
        threshold = len(ensemble) - CONSENSUS
        if ensemble.count(False) <= threshold:
            if ENABLE_SECOND_ORDER:
                if is_anomalously_anomalous(metric_name, ensemble, timeseries[-1][1]):
                    return True, ensemble, timeseries[-1][1]
            else:
                return True, ensemble, timeseries[-1][1]

        return False, ensemble, timeseries[-1][1]
    except:
        logging.error("Algorithm error: " + traceback.format_exc())
        return False, [], 1

########NEW FILE########
__FILENAME__ = algorithm_exceptions
class TooShort(Exception):
    pass


class Stale(Exception):
    pass


class Boring(Exception):
    pass

########NEW FILE########
__FILENAME__ = analyzer-agent
import logging
import sys
import traceback
from os import getpid
from os.path import dirname, abspath, isdir
from daemon import runner
from time import sleep, time

# add the shared settings file to namespace
sys.path.insert(0, dirname(dirname(abspath(__file__))))
import settings

from analyzer import Analyzer


class AnalyzerAgent():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = settings.LOG_PATH + '/analyzer.log'
        self.stderr_path = settings.LOG_PATH + '/analyzer.log'
        self.pidfile_path = settings.PID_PATH + '/analyzer.pid'
        self.pidfile_timeout = 5

    def run(self):
        logger.info('starting skyline analyzer')
        Analyzer(getpid()).start()

        while 1:
            sleep(100)

if __name__ == "__main__":
    """
    Start the Analyzer agent.
    """
    if not isdir(settings.PID_PATH):
        print 'pid directory does not exist at %s' % settings.PID_PATH
        sys.exit(1)

    if not isdir(settings.LOG_PATH):
        print 'log directory does not exist at %s' % settings.LOG_PATH
        sys.exit(1)

    # Make sure we can run all the algorithms
    try:
        from algorithms import *
        timeseries = map(list, zip(map(float, range(int(time()) - 86400, int(time()) + 1)), [1] * 86401))
        ensemble = [globals()[algorithm](timeseries) for algorithm in settings.ALGORITHMS]
    except KeyError as e:
        print "Algorithm %s deprecated or not defined; check settings.ALGORITHMS" % e
        sys.exit(1)
    except Exception as e:
        print "Algorithm test run failed."
        traceback.print_exc()
        sys.exit(1)

    analyzer = AnalyzerAgent()

    logger = logging.getLogger("AnalyzerLog")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s :: %(process)s :: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(settings.LOG_PATH + '/analyzer.log')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        analyzer.run()
    else:
        daemon_runner = runner.DaemonRunner(analyzer)
        daemon_runner.daemon_context.files_preserve = [handler.stream]
        daemon_runner.do_action()

########NEW FILE########
__FILENAME__ = analyzer
import logging
from Queue import Empty
from redis import StrictRedis
from time import time, sleep
from threading import Thread
from collections import defaultdict
from multiprocessing import Process, Manager, Queue
from msgpack import Unpacker, unpackb, packb
from os import path, kill, getpid, system
from math import ceil
import traceback
import operator
import socket
import settings

from alerters import trigger_alert
from algorithms import run_selected_algorithm
from algorithm_exceptions import *

logger = logging.getLogger("AnalyzerLog")


class Analyzer(Thread):
    def __init__(self, parent_pid):
        """
        Initialize the Analyzer
        """
        super(Analyzer, self).__init__()
        self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
        self.daemon = True
        self.parent_pid = parent_pid
        self.current_pid = getpid()
        self.anomalous_metrics = Manager().list()
        self.exceptions_q = Queue()
        self.anomaly_breakdown_q = Queue()

    def check_if_parent_is_alive(self):
        """
        Self explanatory
        """
        try:
            kill(self.current_pid, 0)
            kill(self.parent_pid, 0)
        except:
            exit(0)

    def send_graphite_metric(self, name, value):
        if settings.GRAPHITE_HOST != '':
            sock = socket.socket()
            sock.connect((settings.GRAPHITE_HOST, settings.CARBON_PORT))
            sock.sendall('%s %s %i\n' % (name, value, time()))
            sock.close()
            return True

        return False

    def spin_process(self, i, unique_metrics):
        """
        Assign a bunch of metrics for a process to analyze.
        """
        # Discover assigned metrics
        keys_per_processor = int(ceil(float(len(unique_metrics)) / float(settings.ANALYZER_PROCESSES)))
        if i == settings.ANALYZER_PROCESSES:
            assigned_max = len(unique_metrics)
        else:
            assigned_max = i * keys_per_processor
        assigned_min = assigned_max - keys_per_processor
        assigned_keys = range(assigned_min, assigned_max)

        # Compile assigned metrics
        assigned_metrics = [unique_metrics[index] for index in assigned_keys]

        # Check if this process is unnecessary
        if len(assigned_metrics) == 0:
            return

        # Multi get series
        raw_assigned = self.redis_conn.mget(assigned_metrics)

        # Make process-specific dicts
        exceptions = defaultdict(int)
        anomaly_breakdown = defaultdict(int)

        # Distill timeseries strings into lists
        for i, metric_name in enumerate(assigned_metrics):
            self.check_if_parent_is_alive()

            try:
                raw_series = raw_assigned[i]
                unpacker = Unpacker(use_list = False)
                unpacker.feed(raw_series)
                timeseries = list(unpacker)

                anomalous, ensemble, datapoint = run_selected_algorithm(timeseries, metric_name)

                # If it's anomalous, add it to list
                if anomalous:
                    base_name = metric_name.replace(settings.FULL_NAMESPACE, '', 1)
                    metric = [datapoint, base_name]
                    self.anomalous_metrics.append(metric)

                    # Get the anomaly breakdown - who returned True?
                    for index, value in enumerate(ensemble):
                        if value:
                            algorithm = settings.ALGORITHMS[index]
                            anomaly_breakdown[algorithm] += 1

            # It could have been deleted by the Roomba
            except TypeError:
                exceptions['DeletedByRoomba'] += 1
            except TooShort:
                exceptions['TooShort'] += 1
            except Stale:
                exceptions['Stale'] += 1
            except Boring:
                exceptions['Boring'] += 1
            except:
                exceptions['Other'] += 1
                logger.info(traceback.format_exc())

        # Add values to the queue so the parent process can collate
        for key, value in anomaly_breakdown.items():
            self.anomaly_breakdown_q.put((key, value))

        for key, value in exceptions.items():
            self.exceptions_q.put((key, value))

    def run(self):
        """
        Called when the process intializes.
        """
        while 1:
            now = time()

            # Make sure Redis is up
            try:
                self.redis_conn.ping()
            except:
                logger.error('skyline can\'t connect to redis at socket path %s' % settings.REDIS_SOCKET_PATH)
                sleep(10)
                self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
                continue

            # Discover unique metrics
            unique_metrics = list(self.redis_conn.smembers(settings.FULL_NAMESPACE + 'unique_metrics'))

            if len(unique_metrics) == 0:
                logger.info('no metrics in redis. try adding some - see README')
                sleep(10)
                continue

            # Spawn processes
            pids = []
            for i in range(1, settings.ANALYZER_PROCESSES + 1):
                if i > len(unique_metrics):
                    logger.info('WARNING: skyline is set for more cores than needed.')
                    break

                p = Process(target=self.spin_process, args=(i, unique_metrics))
                pids.append(p)
                p.start()

            # Send wait signal to zombie processes
            for p in pids:
                p.join()

            # Grab data from the queue and populate dictionaries
            exceptions = dict()
            anomaly_breakdown = dict()
            while 1:
                try:
                    key, value = self.anomaly_breakdown_q.get_nowait()
                    if key not in anomaly_breakdown.keys():
                        anomaly_breakdown[key] = value
                    else:
                        anomaly_breakdown[key] += value
                except Empty:
                    break

            while 1:
                try:
                    key, value = self.exceptions_q.get_nowait()
                    if key not in exceptions.keys():
                        exceptions[key] = value
                    else:
                        exceptions[key] += value
                except Empty:
                    break

            # Send alerts
            if settings.ENABLE_ALERTS:
                for alert in settings.ALERTS:
                    for metric in self.anomalous_metrics:
                        if alert[0] in metric[1]:
                            cache_key = 'last_alert.%s.%s' % (alert[1], metric[1])
                            try:
                                last_alert = self.redis_conn.get(cache_key)
                                if not last_alert:
                                    self.redis_conn.setex(cache_key, alert[2], packb(metric[0]))
                                    trigger_alert(alert, metric)

                            except Exception as e:
                                logger.error("couldn't send alert: %s" % e)

            # Write anomalous_metrics to static webapp directory
            filename = path.abspath(path.join(path.dirname(__file__), '..', settings.ANOMALY_DUMP))
            with open(filename, 'w') as fh:
                # Make it JSONP with a handle_data() function
                anomalous_metrics = list(self.anomalous_metrics)
                anomalous_metrics.sort(key=operator.itemgetter(1))
                fh.write('handle_data(%s)' % anomalous_metrics)

            # Log progress
            logger.info('seconds to run    :: %.2f' % (time() - now))
            logger.info('total metrics     :: %d' % len(unique_metrics))
            logger.info('total analyzed    :: %d' % (len(unique_metrics) - sum(exceptions.values())))
            logger.info('total anomalies   :: %d' % len(self.anomalous_metrics))
            logger.info('exception stats   :: %s' % exceptions)
            logger.info('anomaly breakdown :: %s' % anomaly_breakdown)

            # Log to Graphite
            self.send_graphite_metric('skyline.analyzer.run_time', '%.2f' % (time() - now))
            self.send_graphite_metric('skyline.analyzer.total_analyzed', '%.2f' % (len(unique_metrics) - sum(exceptions.values())))

            # Check canary metric
            raw_series = self.redis_conn.get(settings.FULL_NAMESPACE + settings.CANARY_METRIC)
            if raw_series is not None:
                unpacker = Unpacker(use_list = False)
                unpacker.feed(raw_series)
                timeseries = list(unpacker)
                time_human = (timeseries[-1][0] - timeseries[0][0]) / 3600
                projected = 24 * (time() - now) / time_human

                logger.info('canary duration   :: %.2f' % time_human)
                self.send_graphite_metric('skyline.analyzer.duration', '%.2f' % time_human)
                self.send_graphite_metric('skyline.analyzer.projected', '%.2f' % projected)

            # Reset counters
            self.anomalous_metrics[:] = []

            # Sleep if it went too fast
            if time() - now < 5:
                logger.info('sleeping due to low run time...')
                sleep(10)

########NEW FILE########
__FILENAME__ = horizon-agent
import logging
import time
import sys
from os import getpid
from os.path import dirname, abspath, isdir
from multiprocessing import Queue
from daemon import runner

# add the shared settings file to namespace
sys.path.insert(0, dirname(dirname(abspath(__file__))))
import settings

from listen import Listen
from roomba import Roomba
from worker import Worker

# TODO: http://stackoverflow.com/questions/6728236/exception-thrown-in-multiprocessing-pool-not-detected


class Horizon():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = settings.LOG_PATH + '/horizon.log'
        self.stderr_path = settings.LOG_PATH + '/horizon.log'
        self.pidfile_path = settings.PID_PATH + '/horizon.pid'
        self.pidfile_timeout = 5

    def run(self):
        logger.info('starting horizon agent')
        listen_queue = Queue(maxsize=settings.MAX_QUEUE_SIZE)
        pid = getpid()

        #If we're not using oculus, don't bother writing to mini
        try:
            skip_mini = True if settings.OCULUS_HOST == '' else False
        except Exception:
            skip_mini = True

        # Start the workers
        for i in range(settings.WORKER_PROCESSES):
            if i == 0:
                Worker(listen_queue, pid, skip_mini, canary=True).start()
            else:
                Worker(listen_queue, pid, skip_mini).start()

        # Start the listeners
        Listen(settings.PICKLE_PORT, listen_queue, pid, type="pickle").start()
        Listen(settings.UDP_PORT, listen_queue, pid, type="udp").start()

        # Start the roomba
        Roomba(pid, skip_mini).start()

        # Warn the Mac users
        try:
            listen_queue.qsize()
        except NotImplementedError:
            logger.info('WARNING: Queue().qsize() not implemented on Unix platforms like Mac OS X. Queue size logging will be unavailable.')

        # Keep yourself occupied, sucka
        while 1:
            time.sleep(100)

if __name__ == "__main__":
    """
    Start the Horizon agent.
    """
    if not isdir(settings.PID_PATH):
        print 'pid directory does not exist at %s' % settings.PID_PATH
        sys.exit(1)

    if not isdir(settings.LOG_PATH):
        print 'log directory does not exist at %s' % settings.LOG_PATH
        sys.exit(1)

    horizon = Horizon()

    logger = logging.getLogger("HorizonLog")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s :: %(process)s :: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(settings.LOG_PATH + '/horizon.log')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        horizon.run()
    else:
        daemon_runner = runner.DaemonRunner(horizon)
        daemon_runner.daemon_context.files_preserve = [handler.stream]
        daemon_runner.do_action()

########NEW FILE########
__FILENAME__ = listen
import socket
from os import kill, getpid
from Queue import Full
from multiprocessing import Process
from struct import Struct, unpack
from msgpack import unpackb
from cPickle import loads

import logging
import settings

logger = logging.getLogger("HorizonLog")


class Listen(Process):
    """
    The listener is responsible for listening on a port.
    """
    def __init__(self, port, queue, parent_pid, type="pickle"):
        super(Listen, self).__init__()
        try:
            self.ip = settings.HORIZON_IP
        except AttributeError:
            # Default for backwards compatibility
            self.ip = socket.gethostname()
        self.port = port
        self.q = queue
        self.daemon = True
        self.parent_pid = parent_pid
        self.current_pid = getpid()
        self.type = type

    def gen_unpickle(self, infile):
        """
        Generate a pickle from a stream
        """
        try:
            bunch = loads(infile)
            yield bunch
        except EOFError:
            return

    def read_all(self, sock, n):
        """
        Read n bytes from a stream
        """
        data = ''
        while n > 0:
            buf = sock.recv(n)
            n -= len(buf)
            data += buf
        return data

    def check_if_parent_is_alive(self):
        """
        Self explanatory
        """
        try:
            kill(self.current_pid, 0)
            kill(self.parent_pid, 0)
        except:
            exit(0)

    def listen_pickle(self):
        """
        Listen for pickles over tcp
        """
        while 1:
            try:
                # Set up the TCP listening socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.ip, self.port))
                s.setblocking(1)
                s.listen(5)
                logger.info('listening over tcp for pickles on %s' % self.port)

                (conn, address) = s.accept()
                logger.info('connection from %s:%s' % (address[0], self.port))

                chunk = []
                while 1:
                    self.check_if_parent_is_alive()
                    try:
                        length = Struct('!I').unpack(self.read_all(conn, 4))
                        body = self.read_all(conn, length[0])

                        # Iterate and chunk each individual datapoint
                        for bunch in self.gen_unpickle(body):
                            for metric in bunch:
                                chunk.append(metric)

                                # Queue the chunk and empty the variable
                                if len(chunk) > settings.CHUNK_SIZE:
                                    try:
                                        self.q.put(list(chunk), block=False)
                                        chunk[:] = []

                                    # Drop chunk if queue is full
                                    except Full:
                                        logger.info('queue is full, dropping datapoints')
                                        chunk[:] = []

                    except Exception as e:
                        logger.info(e)
                        logger.info('incoming connection dropped, attempting to reconnect')
                        break

            except Exception as e:
                logger.info('can\'t connect to socket: ' + str(e))
                break

    def listen_udp(self):
        """
        Listen over udp for MessagePack strings
        """
        while 1:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.bind((self.ip, self.port))
                logger.info('listening over udp for messagepack on %s' % self.port)

                chunk = []
                while 1:
                    self.check_if_parent_is_alive()
                    data, addr = s.recvfrom(1024)
                    metric = unpackb(data)
                    chunk.append(metric)

                    # Queue the chunk and empty the variable
                    if len(chunk) > settings.CHUNK_SIZE:
                        try:
                            self.q.put(list(chunk), block=False)
                            chunk[:] = []

                        # Drop chunk if queue is full
                        except Full:
                            logger.info('queue is full, dropping datapoints')
                            chunk[:] = []

            except Exception as e:
                logger.info('can\'t connect to socket: ' + str(e))
                break

    def run(self):
        """
        Called when process intializes.
        """
        logger.info('started listener')

        if self.type == 'pickle':
            self.listen_pickle()
        elif self.type == 'udp':
            self.listen_udp()
        else:
            logging.error('unknown listener format')

########NEW FILE########
__FILENAME__ = roomba
from os import kill
from redis import StrictRedis, WatchError
from multiprocessing import Process
from threading import Thread
from msgpack import Unpacker, packb
from types import TupleType
from time import time, sleep

import logging
import settings

logger = logging.getLogger("HorizonLog")


class Roomba(Thread):
    """
    The Roomba is responsible for deleting keys older than DURATION.
    """
    def __init__(self, parent_pid, skip_mini):
        super(Roomba, self).__init__()
        self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
        self.daemon = True
        self.parent_pid = parent_pid
        self.skip_mini = skip_mini

    def check_if_parent_is_alive(self):
        """
        Self explanatory.
        """
        try:
            kill(self.parent_pid, 0)
        except:
            exit(0)

    def vacuum(self, i, namespace, duration):
        """
        Trim metrics that are older than settings.FULL_DURATION and
        purge old metrics.
        """
        begin = time()

        # Discover assigned metrics
        unique_metrics = list(self.redis_conn.smembers(namespace + 'unique_metrics'))
        keys_per_processor = len(unique_metrics) / settings.ROOMBA_PROCESSES
        assigned_max = i * keys_per_processor
        assigned_min = assigned_max - keys_per_processor
        assigned_keys = range(assigned_min, assigned_max)

        # Compile assigned metrics
        assigned_metrics = [unique_metrics[index] for index in assigned_keys]

        euthanized = 0
        blocked = 0
        for i in xrange(len(assigned_metrics)):
            self.check_if_parent_is_alive()

            pipe = self.redis_conn.pipeline()
            now = time()
            key = assigned_metrics[i]

            try:
                # WATCH the key
                pipe.watch(key)

                # Everything below NEEDS to happen before another datapoint
                # comes in. If your data has a very small resolution (<.1s),
                # this technique may not suit you.
                raw_series = pipe.get(key)
                unpacker = Unpacker(use_list = False)
                unpacker.feed(raw_series)
                timeseries = sorted([unpacked for unpacked in unpacker])

                # Put pipe back in multi mode
                pipe.multi()

                # There's one value. Purge if it's too old
                try:
                    if not isinstance(timeseries[0], TupleType):
                        if timeseries[0] < now - duration:
                            pipe.delete(key)
                            pipe.srem(namespace + 'unique_metrics', key)
                            pipe.execute()
                            euthanized += 1
                        continue
                except IndexError:
                    continue

                # Check if the last value is too old and purge
                if timeseries[-1][0] < now - duration:
                    pipe.delete(key)
                    pipe.srem(namespace + 'unique_metrics', key)
                    pipe.execute()
                    euthanized += 1
                    continue

                # Remove old datapoints and duplicates from timeseries
                temp = set()
                temp_add = temp.add
                delta = now - duration
                trimmed = [
                    tuple for tuple in timeseries
                    if tuple[0] > delta
                    and tuple[0] not in temp
                    and not temp_add(tuple[0])
                ]

                # Purge if everything was deleted, set key otherwise
                if len(trimmed) > 0:
                    # Serialize and turn key back into not-an-array
                    btrimmed = packb(trimmed)
                    if len(trimmed) <= 15:
                        value = btrimmed[1:]
                    elif len(trimmed) <= 65535:
                        value = btrimmed[3:]
                    else:
                        value = btrimmed[5:]
                    pipe.set(key, value)
                else:
                    pipe.delete(key)
                    pipe.srem(namespace + 'unique_metrics', key)
                    euthanized += 1

                pipe.execute()

            except WatchError:
                blocked += 1
                assigned_metrics.append(key)
            except Exception as e:
                # If something bad happens, zap the key and hope it goes away
                pipe.delete(key)
                pipe.srem(namespace + 'unique_metrics', key)
                pipe.execute()
                euthanized += 1
                logger.info(e)
                logger.info("Euthanizing " + key)
            finally:
                pipe.reset()

        logger.info('operated on %s in %f seconds' % (namespace, time() - begin))
        logger.info('%s keyspace is %d' % (namespace, (len(assigned_metrics) - euthanized)))
        logger.info('blocked %d times' % blocked)
        logger.info('euthanized %d geriatric keys' % euthanized)

        if (time() - begin < 30):
            logger.info('sleeping due to low run time...')
            sleep(10)

    def run(self):
        """
        Called when process initializes.
        """
        logger.info('started roomba')

        while 1:
            now = time()

            # Make sure Redis is up
            try:
                self.redis_conn.ping()
            except:
                logger.error('roomba can\'t connect to redis at socket path %s' % settings.REDIS_SOCKET_PATH)
                sleep(10)
                self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
                continue

            # Spawn processes
            pids = []
            for i in range(1, settings.ROOMBA_PROCESSES + 1):
                if not self.skip_mini:
                    p = Process(target=self.vacuum, args=(i, settings.MINI_NAMESPACE, settings.MINI_DURATION + settings.ROOMBA_GRACE_TIME))
                    pids.append(p)
                    p.start()

                p = Process(target=self.vacuum, args=(i, settings.FULL_NAMESPACE, settings.FULL_DURATION + settings.ROOMBA_GRACE_TIME))
                pids.append(p)
                p.start()

            # Send wait signal to zombie processes
            for p in pids:
                p.join()

########NEW FILE########
__FILENAME__ = worker
from os import kill, system
from redis import StrictRedis, WatchError
from multiprocessing import Process
from Queue import Empty
from msgpack import packb
from time import time, sleep

import logging
import socket
import settings

logger = logging.getLogger("HorizonLog")


class Worker(Process):
    """
    The worker processes chunks from the queue and appends
    the latest datapoints to their respective timesteps in Redis.
    """
    def __init__(self, queue, parent_pid, skip_mini, canary=False):
        super(Worker, self).__init__()
        self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
        self.q = queue
        self.parent_pid = parent_pid
        self.daemon = True
        self.canary = canary
        self.skip_mini = skip_mini

    def check_if_parent_is_alive(self):
        """
        Self explanatory.
        """
        try:
            kill(self.parent_pid, 0)
        except:
            exit(0)

    def in_skip_list(self, metric_name):
        """
        Check if the metric is in SKIP_LIST.
        """
        for to_skip in settings.SKIP_LIST:
            if to_skip in metric_name:
                return True

        return False

    def send_graphite_metric(self, name, value):
        if settings.GRAPHITE_HOST != '':
            sock = socket.socket()
            sock.connect((settings.GRAPHITE_HOST, settings.CARBON_PORT))
            sock.sendall('%s %s %i\n' % (name, value, time()))
            sock.close()
            return True

        return False

    def run(self):
        """
        Called when the process intializes.
        """
        logger.info('started worker')

        FULL_NAMESPACE = settings.FULL_NAMESPACE
        MINI_NAMESPACE = settings.MINI_NAMESPACE
        MAX_RESOLUTION = settings.MAX_RESOLUTION
        full_uniques = FULL_NAMESPACE + 'unique_metrics'
        mini_uniques = MINI_NAMESPACE + 'unique_metrics'
        pipe = self.redis_conn.pipeline()

        while 1:

            # Make sure Redis is up
            try:
                self.redis_conn.ping()
            except:
                logger.error('worker can\'t connect to redis at socket path %s' % settings.REDIS_SOCKET_PATH)
                sleep(10)
                self.redis_conn = StrictRedis(unix_socket_path = settings.REDIS_SOCKET_PATH)
                pipe = self.redis_conn.pipeline()
                continue

            try:
                # Get a chunk from the queue with a 15 second timeout
                chunk = self.q.get(True, 15)
                now = time()

                for metric in chunk:

                    # Check if we should skip it
                    if self.in_skip_list(metric[0]):
                        continue

                    # Bad data coming in
                    if metric[1][0] < now - MAX_RESOLUTION:
                        continue

                    # Append to messagepack main namespace
                    key = ''.join((FULL_NAMESPACE, metric[0]))
                    pipe.append(key, packb(metric[1]))
                    pipe.sadd(full_uniques, key)

                    if not self.skip_mini:
                        # Append to mini namespace
                        mini_key = ''.join((MINI_NAMESPACE, metric[0]))
                        pipe.append(mini_key, packb(metric[1]))
                        pipe.sadd(mini_uniques, mini_key)

                    pipe.execute()

                # Log progress
                if self.canary:
                    logger.info('queue size at %d' % self.q.qsize())
                    self.send_graphite_metric('skyline.horizon.queue_size', self.q.qsize())

            except Empty:
                logger.info('worker queue is empty and timed out')
            except WatchError:
                logger.error(key)
            except NotImplementedError:
                pass
            except Exception as e:
                logger.error("worker error: " + str(e))

########NEW FILE########
__FILENAME__ = webapp
import redis
import logging
import simplejson as json
import sys
from msgpack import Unpacker
from flask import Flask, request, render_template
from daemon import runner
from os.path import dirname, abspath

# add the shared settings file to namespace
sys.path.insert(0, dirname(dirname(abspath(__file__))))
import settings

REDIS_CONN = redis.StrictRedis(unix_socket_path=settings.REDIS_SOCKET_PATH)

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True


@app.route("/")
def index():
    return render_template('index.html'), 200


@app.route("/app_settings")
def app_settings():

    app_settings = {'GRAPH_URL': settings.GRAPH_URL,
                    'OCULUS_HOST': settings.OCULUS_HOST,
                    'FULL_NAMESPACE': settings.FULL_NAMESPACE,
                    }

    resp = json.dumps(app_settings)
    return resp, 200


@app.route("/api", methods=['GET'])
def data():
    metric = request.args.get('metric', None)
    try:
        raw_series = REDIS_CONN.get(metric)
        if not raw_series:
            resp = json.dumps({'results': 'Error: No metric by that name'})
            return resp, 404
        else:
            unpacker = Unpacker(use_list = False)
            unpacker.feed(raw_series)
            timeseries = [item[:2] for item in unpacker]
            resp = json.dumps({'results': timeseries})
            return resp, 200
    except Exception as e:
        error = "Error: " + e
        resp = json.dumps({'results': error})
        return resp, 500


class App():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = settings.LOG_PATH + '/webapp.log'
        self.stderr_path = settings.LOG_PATH + '/webapp.log'
        self.pidfile_path = settings.PID_PATH + '/webapp.pid'
        self.pidfile_timeout = 5

    def run(self):

        logger.info('starting webapp')
        logger.info('hosted at %s' % settings.WEBAPP_IP)
        logger.info('running on port %d' % settings.WEBAPP_PORT)

        app.run(settings.WEBAPP_IP, settings.WEBAPP_PORT)

if __name__ == "__main__":
    """
    Start the server
    """

    webapp = App()

    logger = logging.getLogger("AppLog")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s :: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler(settings.LOG_PATH + '/webapp.log')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        webapp.run()
    else:
        daemon_runner = runner.DaemonRunner(webapp)
        daemon_runner.daemon_context.files_preserve = [handler.stream]
        daemon_runner.do_action()

########NEW FILE########
__FILENAME__ = algorithms_test
import unittest2 as unittest
from mock import Mock, patch
from time import time

import sys
from os.path import dirname, abspath

sys.path.insert(0, dirname(dirname(abspath(__file__))) + '/src')
sys.path.insert(0, dirname(dirname(abspath(__file__))) + '/src/analyzer')

import algorithms
import settings


class TestAlgorithms(unittest.TestCase):
    """
    Test all algorithms with a common, simple/known anomalous data set
    """

    def _addSkip(self, test, reason):
        print reason

    def data(self, ts):
        """
        Mostly ones (1), with a final value of 1000
        """
        timeseries = map(list, zip(map(float, range(int(ts) - 86400, int(ts) + 1)), [1] * 86401))
        timeseries[-1][1] = 1000
        timeseries[-2][1] = 1
        timeseries[-3][1] = 1
        return ts, timeseries

    def test_tail_avg(self):
        _, timeseries = self.data(time())
        self.assertEqual(algorithms.tail_avg(timeseries), 334)

    def test_grubbs(self):
        _, timeseries = self.data(time())
        self.assertTrue(algorithms.grubbs(timeseries))

    @patch.object(algorithms, 'time')
    def test_first_hour_average(self, timeMock):
        timeMock.return_value, timeseries = self.data(time())
        self.assertTrue(algorithms.first_hour_average(timeseries))

    def test_stddev_from_average(self):
        _, timeseries = self.data(time())
        self.assertTrue(algorithms.stddev_from_average(timeseries))

    def test_stddev_from_moving_average(self):
        _, timeseries = self.data(time())
        self.assertTrue(algorithms.stddev_from_moving_average(timeseries))

    def test_mean_subtraction_cumulation(self):
        _, timeseries = self.data(time())
        self.assertTrue(algorithms.mean_subtraction_cumulation(timeseries))

    @patch.object(algorithms, 'time')
    def test_least_squares(self, timeMock):
        timeMock.return_value, timeseries = self.data(time())
        self.assertTrue(algorithms.least_squares(timeseries))

    def test_histogram_bins(self):
        _, timeseries = self.data(time())
        self.assertTrue(algorithms.histogram_bins(timeseries))

    @patch.object(algorithms, 'time')
    def test_run_selected_algorithm(self, timeMock):
        timeMock.return_value, timeseries = self.data(time())
        result, ensemble, datapoint = algorithms.run_selected_algorithm(timeseries, "test.metric")
        self.assertTrue(result)
        self.assertTrue(len(filter(None, ensemble)) >= settings.CONSENSUS)
        self.assertEqual(datapoint, 1000)

    @unittest.skip('Fails inexplicable in certain environments.')
    @patch.object(algorithms, 'CONSENSUS')
    @patch.object(algorithms, 'ALGORITHMS')
    @patch.object(algorithms, 'time')
    def test_run_selected_algorithm_runs_novel_algorithm(self, timeMock,
                                                         algorithmsListMock, consensusMock):
        """
        Assert that a user can add their own custom algorithm.

        This mocks out settings.ALGORITHMS and settings.CONSENSUS to use only a
        single custom-defined function (alwaysTrue)
        """
        algorithmsListMock.__iter__.return_value = ['alwaysTrue']
        consensusMock = 1
        timeMock.return_value, timeseries = self.data(time())

        alwaysTrue = Mock(return_value=True)
        with patch.dict(algorithms.__dict__, {'alwaysTrue': alwaysTrue}):
            result, ensemble, tail_avg = algorithms.run_selected_algorithm(timeseries)

        alwaysTrue.assert_called_with(timeseries)
        self.assertTrue(result)
        self.assertEqual(ensemble, [True])
        self.assertEqual(tail_avg, 334)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = continuity
import redis
import msgpack
import sys
import time
from os.path import dirname, abspath

# add the shared settings file to namespace
sys.path.insert(0, ''.join((dirname(dirname(abspath(__file__))), "/src")))
import settings

metric = 'horizon.test.udp'


def check_continuity(metric, mini = False):
    r = redis.StrictRedis(unix_socket_path=settings.REDIS_SOCKET_PATH)
    if mini:
        raw_series = r.get(settings.MINI_NAMESPACE + metric)
    else:
        raw_series = r.get(settings.FULL_NAMESPACE + metric)

    if raw_series is None:
        print 'key not found at %s ' + metric
        return 0, 0, 0, 0, 0

    unpacker = msgpack.Unpacker()
    unpacker.feed(raw_series)
    timeseries = list(unpacker)
    length = len(timeseries)

    start = time.ctime(int(timeseries[0][0]))
    end = time.ctime(int(timeseries[-1][0]))
    duration = (float(timeseries[-1][0]) - float(timeseries[0][0])) / 3600

    last = int(timeseries[0][0]) - 10
    total = 0
    bad = 0
    missing = 0
    for item in timeseries:
        total += 1
        if int(item[0]) - last != 10:
            bad += 1
            missing += int(item[0]) - last
        last = item[0]

    total_sum = sum(item[1] for item in timeseries[-50:])

    return length, total_sum, start, end, duration, bad, missing

if __name__ == "__main__":
    length, total_sum, start, end, duration, bad, missing = check_continuity(metric)
    print ""
    print "Stats for full %s:" % metric
    print "Length of %s" % length
    print "Total sum of last 50 datapoints: %s" % total_sum
    print "Start time: %s" % start
    print "End time: %s" % end
    print "Duration: %.2f hours" % duration
    print "Number of missing data periods: %s" % bad
    print "Total duration of missing data in seconds: %s" % missing

    length, total_sum, start, end, duration, bad, missing = check_continuity(metric, True)
    print ""
    print "Stats for mini %s:" % metric
    print "Length: %s" % length
    print "Total sum of last 50 datapoints: %s" % total_sum
    print "Start time: %s" % start
    print "End time: %s" % end
    print "Duration: %.2f hours" % duration
    print "Number of missing data periods: %s" % bad
    print "Total duration of missing data in seconds: %s" % missing

########NEW FILE########
__FILENAME__ = numpy_vs_msgpack
import time
import timeit
import msgpack
import numpy
import random

"""
Numpy decoding achieves faster results because of the reshape function.
It might be worth it to use Numpy encoding/decoding instead of MessagePack
at some point, for a sacrifice in operability.
"""

array = [[random.randint(1, 1000), random.randint(1, 1000)] for x in range(1, 8000)]
numpy_list = numpy.array(array).tostring()
msg_list = msgpack.packb(array)


def msgpack_decode():
    unpacker = msgpack.Unpacker()
    unpacker.feed(msg_list)
    timeseries = [unpacked for unpacked in unpacker]


def numpy_decode():
    raw = numpy.fromstring(numpy_list)
    s = raw.size
    timeseries = raw.reshape((s / 2, 2))


if __name__ == '__main__':
    import timeit
    print("MessagePack: " + str(timeit.timeit("msgpack_decode()", setup="from __main__ import msgpack_decode", number=3000)))
    print("Numpy: " + str(timeit.timeit("numpy_decode()", setup="from __main__ import numpy_decode", number=3000)))

########NEW FILE########
__FILENAME__ = seed_data
#!/usr/bin/env python

import json
import os
import pickle
import socket
import sys
import time
from os.path import dirname, join, realpath
from multiprocessing import Manager, Process, log_to_stderr
from struct import Struct, pack

import redis
import msgpack

# Get the current working directory of this file.
# http://stackoverflow.com/a/4060259/120999
__location__ = realpath(join(os.getcwd(), dirname(__file__)))

# Add the shared settings file to namespace.
sys.path.insert(0, join(__location__, '..', 'src'))
import settings


class NoDataException(Exception):
    pass


def seed():
    print 'Loading data over UDP via Horizon...'
    metric = 'horizon.test.udp'
    metric_set = 'unique_metrics'
    initial = int(time.time()) - settings.MAX_RESOLUTION

    with open(join(__location__, 'data.json'), 'r') as f:
        data = json.loads(f.read())
        series = data['results']
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        for datapoint in series:
            datapoint[0] = initial
            initial += 1
            packet = msgpack.packb((metric, datapoint))
            sock.sendto(packet, (socket.gethostname(), settings.UDP_PORT))

    print "Connecting to Redis..."
    r = redis.StrictRedis(unix_socket_path=settings.REDIS_SOCKET_PATH)
    time.sleep(5)

    try:
        x = r.smembers(settings.FULL_NAMESPACE + metric_set)
        if x is None:
            raise NoDataException

        x = r.get(settings.FULL_NAMESPACE + metric)
        if x is None:
            raise NoDataException

        #Ignore the mini namespace if OCULUS_HOST isn't set.
        if settings.OCULUS_HOST != "":
            x = r.smembers(settings.MINI_NAMESPACE + metric_set)
            if x is None:
                raise NoDataException

            x = r.get(settings.MINI_NAMESPACE + metric)
            if x is None:
                raise NoDataException

        print "Congratulations! The data made it in. The Horizon pipeline seems to be working."

    except NoDataException:
        print "Woops, looks like the metrics didn't make it into Horizon. Try again?"

if __name__ == "__main__":
    seed()

########NEW FILE########
__FILENAME__ = verify_alerts
#!/usr/bin/env python

import os
import sys
from os.path import dirname, join, realpath
from optparse import OptionParser

# Get the current working directory of this file.
# http://stackoverflow.com/a/4060259/120999
__location__ = realpath(join(os.getcwd(), dirname(__file__)))

# Add the shared settings file to namespace.
sys.path.insert(0, join(__location__, '..', 'src'))
import settings

# Add the analyzer file to namespace.
sys.path.insert(0, join(__location__, '..', 'src', 'analyzer'))
from alerters import trigger_alert

parser = OptionParser()
parser.add_option("-t", "--trigger", dest="trigger", default=False,
                  help="Actually trigger the appropriate alerts (default is False)")

parser.add_option("-m", "--metric", dest="metric", default='skyline.horizon.queue_size',
                  help="Pass the metric to test (default is skyline.horizon.queue_size)")

(options, args) = parser.parse_args()

try:
    alerts_enabled = settings.ENABLE_ALERTS
    alerts = settings.ALERTS
except:
    print "Exception: Check your settings file for the existence of ENABLE_ALERTS and ALERTS"
    sys.exit()

print 'Verifying alerts for: "' + options.metric + '"'

# Send alerts
if alerts_enabled:
    for alert in alerts:
        if alert[0] in options.metric:
            print '    Testing against "' + alert[0] + '" to send via ' + alert[1] + "...triggered"
            if options.trigger:
                trigger_alert(alert, options.metric)
        else:
            print '    Testing against "' + alert[0] + '" to send via ' + alert[1] + "..."
else:
    print 'Alerts are disabled'

########NEW FILE########
