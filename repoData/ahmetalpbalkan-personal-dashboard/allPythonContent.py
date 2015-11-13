__FILENAME__ = fixture
# coding: utf-8


"""
Example configuration for statistics retrieval tasks:

from tasks import twitter
from tasks import foursq

tasks = [
    (twitter.followers_count, ('*','10')),
    (foursq.checkins, ('*/2'))
]

~~~~

A single task looks like:

    (foursq.checkins, ('*/2', '30'))
     -------^-------   -----^-----
       task name        intervals

    task name:  in tasks/ directory you will find .py files which have tasks.
                In this case, tasks/foursq.py has checkins method

    intervals:  these are in (hour, minute, second) format, tells program to
                when to execute these tasks.

                ('*', '30', '00')
                  |     |     |
                  |     |     +---- second (optional)
                  |     +---------- minute (optional)
                  +---------------- hour

                Examples: ('*',)            every hour
                          ('*/2',)          every 2 hours (e.g. 10:00, 12:00)
                          ('22', '30')      everyday at 22:30 (24-hour format)
                          ('*', '*/30')     every 30 mins (e.g. 10:00, 10:30)
                          ('0', '0')        every midnight
                          ('*', '*', '*/5') every 5 seconds

                NOTE: If you are going to use only hour part, do not forget
                comma at the end, e.g: ('*',)
"""

tasks = [
]

# Sample configuration:
#     You can just uncomment the part below.
#     Note that the last task does not have a comma at the end of the line.
#
# from tasks import twitter
# from tasks import kloutcom
# from tasks import foursq
# from tasks import fb
# from tasks import runkeeper
# from tasks import atelog
# from tasks import reporting
# from tasks import tmp102
# from tasks import lastfm
# from tasks import jawboneup

# tasks = [
#     (twitter.followers_count, ('*', '59')),
#     (twitter.tweets_count, ('*', '59')),
#     (foursq.checkins, ('*', '59')),
#     (fb.friends_count, ('*/2',)),
#     (runkeeper.activities_and_calories, ('*', '59')),
#     (runkeeper.sleeps, ('*',)),
#     (runkeeper.weight, ('*/2',)),
#     (kloutcom.score, ('*/2',)),
#     (tmp102.temperature, ('*', '*/20')),
#     (atelog.coffees, ('*',)),
#     (lastfm.tracks_listened, ('*', '59')),
#     (jawboneup.sleeps, ('*', '*/30')),
#     (jawboneup.steps, ('*', '*/30')),
#     (jawboneup.caffeine, ('*', '*/30')),
#     (reporting.generate_and_upload, ('*', '*/20')),
# ]

########NEW FILE########
__FILENAME__ = taskhost
#!/usr/bin/env python
# coding: utf-8

import sys
import time
import json
import logging
import datetime
from apscheduler.scheduler import Scheduler
import simplegauges
import tasks


_tasks_config_file = 'tasks.config'


def main():
    configure_logging()
    logger = logging.getLogger('taskhost')
    config = {}

    try:
        with open(_tasks_config_file) as f:
            config = json.loads(f.read())
        logger.debug('Successfully read configuration file.')
    except Exception as e:
        logger.critical('Cannot read configuration file: {0}'
                        .format(_tasks_config_file))
        logger.critical(e)
        sys.exit(1)

    from simplegauges.datastores.azuretable import AzureGaugeDatastore
    gauges_ds = AzureGaugeDatastore(config['azure.account'],
                                    config['azure.key'], config['azure.table'])
    gauge_factory = simplegauges.gauge_factory(gauges_ds)
    tasks.set_simplegauges_factory(gauge_factory)
    tasks.set_config(config)

    import fixture  # should be imported after setting configs for decorators

    if not fixture.tasks:
        logger.error('No tasks found in the fixture.py')
        sys.exit(1)

    errors = False
    for task in fixture.tasks:
        method = task[0]
        name = '{0}.{1}'.format(method.__module__, method.__name__)
        try:
            task[0]()
            logger.info('Successfully bootstrapped: {0}'.format(name))
        except Exception as e:
            errors = True
            logger.error('Error while bootstrapping: {0}'.format(name))
            logger.error(e)

    if errors:
        logger.info('Starting scheduler in 10 seconds...')
        time.sleep(10)
    else:
        logger.info('Starting scheduler...')

    # at this point all tasks ran once successfully
    sched = Scheduler()

    # schedule tasks
    for task in fixture.tasks:
        cron_kwargs = parse_cron_tuple(task[1])
        sched.add_cron_job(task[0], **cron_kwargs)

    sched.start()
    logger.info('Scheduler started with {0} jobs.'
                .format(len(sched.get_jobs())))
    now = datetime.datetime.now()
    for j in sched.get_jobs():
        logger.debug('Scheduled: {0}.{1}, next run:{2}'
                     .format(j.func.__module__, j.func.__name__,
                             j.compute_next_run_time(now)))

    # deamonize the process
    while True:
        time.sleep(10)


def parse_cron_tuple(cron_tuple):
    """Parses (hour,minute,second) or (hour,minute) or (hour) cron
    scheduling defintions into kwargs dictionary
    """
    if type(cron_tuple) is not tuple:
        raise Exception('Given cron format is not tuple: {0}'
                        .format(cron_tuple))
    kwargs = {}
    l = len(cron_tuple)

    if l > 0:
        kwargs['hour'] = cron_tuple[0]
    if l > 1:
        kwargs['minute'] = cron_tuple[1]
    if l > 2:
        kwargs['second'] = cron_tuple[2]
    return kwargs


def configure_logging():
    logfmt = '[%(asctime)s] %(levelname)s [%(name)s] %(message)s'

    # configure to StreamHandler with log format
    logging.basicConfig(level=logging.DEBUG, format=logfmt)

    # reduce noise from 3rd party packages
    logging.getLogger('requests.packages.urllib3.connectionpool')\
        .setLevel(logging.CRITICAL)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = atelog
# coding: utf-8

from . import requires, today_utc
import feedparser
from dateutil import parser


"""Retrieves nutrition data from a tumblelog (Tumblr blog) RSS using
tags.
"""

COFFEE_TAG = 'coffee'


@requires('atelog.rss')
def coffees(gauge_factory, config, logger):
    gauge = gauge_factory('atelog.coffees')

    feed = feedparser.parse(config['atelog.rss'])
    entries = feed['entries']
    today = today_utc()

    coffees = len(filter(lambda x: parser.parse(x['published']).date() == today
                  and filter(lambda t: t.term == COFFEE_TAG, x['tags']),
                  entries))

    gauge.save(today, coffees)
    logger.info('Saved {0} coffee records for {1}'.format(coffees, today))

########NEW FILE########
__FILENAME__ = fb
# coding: utf-8

from . import requires, today_utc
import facebook


@requires('facebook.access_token')
def friends_count(gauge_factory, config, logger):
    #TODO does not refresh the existing long-living access token
    #TODO does not use paging (I have <5000 friends)
    gauge = gauge_factory('facebook.friends')

    graph = facebook.GraphAPI(config['facebook.access_token'])
    resp = graph.fql("SELECT friend_count FROM user WHERE uid = me()")
    friends = resp[0]['friend_count']

    gauge.save(today_utc(), friends)
    logger.info('Saved Facebook friend count: {0}'.format(friends))

########NEW FILE########
__FILENAME__ = foursq
# coding: utf-8

from . import requires, today_utc, epoch_for_day
from foursquare import Foursquare


@requires('foursquare.access_token')
def checkins(gauge_factory, config, logger):
    """Number of foursquare check-ins done since midnight today in UTC.
    """

    gauge = gauge_factory('foursquare.checkins')
    client = Foursquare(access_token=config['foursquare.access_token'])

    epoch = epoch_for_day(today_utc())
    checkins = client.users.checkins(params={'afterTimestamp': epoch})
    checkins = checkins['checkins']['items']

    gauge.save(today_utc(), len(checkins))
    logger.info('Saved {0} foursquare checkins'.format(len(checkins)))

########NEW FILE########
__FILENAME__ = jawboneup
# coding: utf-8
from . import requires, today_utc
import requests
from datetime import timedelta


DAYS_BACK = 2

@requires('jawboneup.access_token')
def sleeps(gauge_factory, config, logger):
    gauge = gauge_factory('jawbone.sleeps')
    access_token = config['jawboneup.access_token']

    headers = {'Authorization' : 'Bearer {0}'.format(access_token)}
    r = requests.get('https://jawbone.com/nudge/api/users/@me/sleeps',
                     headers=headers)

    for i in range(DAYS_BACK):
        day = today_utc() - timedelta(days=i)
        resp = r.json()
        sleeps = resp['data']['items']
        day_date = day.date()
        today_fmt = int(day_date.strftime('%Y%m%d'))
        today_sleeps = filter(lambda s: s['date'] == today_fmt, sleeps)
        
        duration = sum([s['details']['duration'] - s['details']['awake']
                       for s in today_sleeps]) / 60.0 # in minutes
        if duration == 0:
            logger.info('Sleeps not found on {0}, not saving.'.format(day_date))
        else:
            gauge.save(day, duration)
            logger.info('Saved {0}min sleep on {1}'.format(duration, day_date))


@requires('jawboneup.access_token')
def steps(gauge_factory, config, logger):
    gauge = gauge_factory('jawbone.steps')
    access_token = config['jawboneup.access_token']

    headers = {'Authorization' : 'Bearer {0}'.format(access_token)}
    r = requests.get('https://jawbone.com/nudge/api/users/@me/moves',
                     headers=headers)

    for i in range(DAYS_BACK):
        day = today_utc() - timedelta(days=i)
        resp = r.json()
        moves = resp['data']['items']
        day_date = day.date()
        today_fmt = int(day_date.strftime('%Y%m%d'))
        today_moves = filter(lambda m: m['date'] == today_fmt, moves)
        steps = sum([m['details']['steps'] for m in today_moves])

        if steps == 0:
            logger.info('Steps not found on {0}, not saving.'.format(day_date))
        else:
            gauge.save(day, steps)
            logger.info('Saved {0} steps on {1}'.format(steps, day_date))



@requires('jawboneup.access_token')
def caffeine(gauge_factory, config, logger):
    gauge = gauge_factory('jawbone.caffeine')
    access_token = config['jawboneup.access_token']

    headers = {'Authorization' : 'Bearer {0}'.format(access_token)}
    r = requests.get('https://jawbone.com/nudge/api/users/@me/meals',
                     headers=headers)

    for i in range(DAYS_BACK):
        day = today_utc() - timedelta(days=i)
        resp = r.json()
        meals = resp['data']['items']
        day_date = day.date()
        today_fmt = int(day_date.strftime('%Y%m%d'))
        today_meals = filter(lambda m: m['date'] == today_fmt, meals)
        caffeine = sum([m['details']['caffeine'] for m in today_meals])

        if caffeine == 0:
            logger.info('Caffeine not found on {0}, not saving.'.format(day_date))
        else:
            gauge.save(day, caffeine)
            logger.info('Saved {0}mg. caffeine  on {1}'.format(caffeine, day_date))

########NEW FILE########
__FILENAME__ = kloutcom
# coding: utf-8

from . import requires, today_utc
import klout


@requires('klout.api_key', 'klout.screen_name')
def score(gauge_factory, config, logger):
    gauge = gauge_factory('klout.score')
    k = klout.Klout(config['klout.api_key'])

    user = config['klout.screen_name']
    kloutId = k.identity.klout(screenName=user).get('id')
    if not kloutId:
        raise Exception("Klout id not found for screen name {0}".format(user))
    score = k.user.score(kloutId=kloutId).get('score')
    gauge.save(today_utc(), score)

    logger.info('Saved Klout score: {0}'.format(score))

########NEW FILE########
__FILENAME__ = lastfm
# coding: utf-8

from . import requires, today_utc, epoch_for_day
import requests


@requires('lastfm.api_key', 'lastfm.user')
def tracks_listened(gauge_factory, config, logger):
    """Number tracks listened today
    """

    gauge = gauge_factory('lastfm.listened')
    epoch_today = epoch_for_day(today_utc())

    params = {
        'method': 'user.getrecenttracks',
        'user': config['lastfm.user'],
        'api_key': config['lastfm.api_key'],
        'from': epoch_today,
        'format': 'json'
    }

    r = requests.get('http://ws.audioscrobbler.com/2.0', params=params)
    resp = r.json()['recenttracks']

    listened = int(resp['@attr']['total']) if '@attr' in resp else 0

    gauge.save(today_utc(), listened)
    logger.info('Saved {0} last.fm tracks for {1}'.format(listened, today_utc()))

########NEW FILE########
__FILENAME__ = reporting
# coding: utf-8

from . import requires, now_utc, today_utc
from simplegauges import interpolators, postprocessors, aggregators
import datetime
from datetime import timedelta
import json
from azure.storage import BlobService


JSONP_CALLBACK_NAME = 'renderData'

zero_fill_daily = lambda data: postprocessors.day_fill(data, 0)
zero_fill_weekly = lambda data: postprocessors.week_fill(data, 0)
monthly_max = lambda data: aggregators.monthly(data, max)
weekly_max = lambda data: aggregators.weekly(data, max)
weekly_min = lambda data: aggregators.weekly(data, min)
weekly_sum = lambda data: aggregators.weekly(data, sum)


@requires('azure.account', 'azure.key', 'azure.blob.container',
          'azure.blob.name')
def generate_and_upload(gauge_factory, config, logger):
    start = datetime.datetime.now()
    twitter_followers = gauge_factory('twitter.followers')
    twitter_tweets = gauge_factory('twitter.tweets')
    fb_friends = gauge_factory('facebook.friends')
    foursq_checkins = gauge_factory('foursquare.checkins')
    klout_score = gauge_factory('klout.score')
    runkeeper_activities = gauge_factory('runkeeper.activities')
    runkeeper_calories = gauge_factory('runkeeper.calories_burned')
    runkeeper_weight = gauge_factory('runkeeper.weight')
    tmp102_celsius = gauge_factory('tmp102.te  mperature', gauge_type='hourly')
    lastfm_listened = gauge_factory('lastfm.listened')
    jawbone_sleeps = gauge_factory('jawbone.sleeps')
    jawbone_steps = gauge_factory('jawbone.steps')
    jawbone_caffeine = gauge_factory('jawbone.caffeine')

    data = {}
    data_sources = [
        # (output key, gauge, days back, aggregator, postprocessors)
        ('twitter.followers', twitter_followers, 30, None,
            [zero_fill_daily, interpolators.linear]),
        ('twitter.tweets', twitter_tweets, 20, None, [zero_fill_daily]),
        ('facebook.friends', fb_friends, 180, monthly_max, None),
        ('foursquare.checkins', foursq_checkins, 14, None, [zero_fill_daily]),
        ('lastfm.listened', lastfm_listened, 14, None, [zero_fill_daily]),
        ('klout.score', klout_score, 30, weekly_max, [zero_fill_weekly,
                                                      interpolators.linear]),
        ('runkeeper.calories', runkeeper_calories, 60, weekly_sum,
            [zero_fill_weekly]),
        ('runkeeper.activities', runkeeper_activities, 60,weekly_sum,
            [zero_fill_weekly]),
        ('runkeeper.weight', runkeeper_weight, 180,weekly_min,
            [zero_fill_weekly, interpolators.linear]),
        ('sleeps', jawbone_sleeps, 14, None, [zero_fill_daily,
            interpolators.linear]),
        ('steps', jawbone_steps, 14, None, [zero_fill_daily,
            interpolators.linear]),
        ('caffeine', jawbone_caffeine, 30, None, [zero_fill_daily]),
        ('tmp102.temperature', tmp102_celsius, 2.5, None, None)
    ]

    for ds in data_sources:
        data[ds[0]] = ds[1].aggregate(today_utc() - timedelta(days=ds[2]),
                                      aggregator=ds[3],
                                      post_processors=ds[4])

    report = {
        'generated': str(now_utc()),
        'data': data,
        'took': (datetime.datetime.now() - start).seconds
    }
    report_json = json.dumps(report, indent=4, default=json_date_serializer)
    report_content = '{0}({1})'.format(JSONP_CALLBACK_NAME, report_json)
    
    blob_service = BlobService(config['azure.account'], config['azure.key'])
    blob_service.create_container(config['azure.blob.container'])
    blob_service.set_container_acl(config['azure.blob.container'],
                                   x_ms_blob_public_access='container')
    blob_service.put_blob(config['azure.blob.container'],
                          config['azure.blob.name'], report_content, 'BlockBlob')

    took = (datetime.datetime.now() - start).seconds
    logger.info('Report generated and uploaded. Took {0} s.'.format(took))


def json_date_serializer(obj):
    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
        return str(obj)
    return obj

########NEW FILE########
__FILENAME__ = runkeeper
# coding: utf-8

from . import requires, today_utc
from pytz import timezone, UTC
import healthgraph


@requires('runkeeper.access_token','runkeeper.local_tz')
def activities_and_calories(gauge_factory, config, logger):
    activity_gauge = gauge_factory('runkeeper.activities')
    calorie_gauge = gauge_factory('runkeeper.calories_burned')
    local_tz = timezone(config['runkeeper.local_tz'])

    user = healthgraph.User(session=healthgraph.
                            Session(config['runkeeper.access_token']))
    activities_iter = user.get_fitness_activity_iter()

    today = today_utc().date()
    today_activities = []
    for a in activities_iter:  # breaking early prevents loading all results
        activity_time = a['start_time'].replace(tzinfo=local_tz)
        activity_time_utc = UTC.normalize(activity_time)
        day = activity_time_utc.date()
        if day == today:
            today_activities.append(a)
        elif (today - day).days > 2:
            break

    total_activities = len(today_activities)
    total_calories = int(sum([a['total_calories'] for a in today_activities]))

    activity_gauge.save(today_utc(), total_activities)
    calorie_gauge.save(today_utc(), total_calories)
    logger.info('Saved {0} activities ({1} cal) for {2}'
                .format(total_activities, total_calories, today_utc()))


@requires('runkeeper.access_token')
def sleeps(gauge_factory, config, logger):
    gauge = gauge_factory('runkeeper.sleeps')

    user = healthgraph.User(session=healthgraph.
                            Session(config['runkeeper.access_token']))
    sleeps_iter = user.get_sleep_measurement_iter()
    today = today_utc().date()
    today_sleeps = []
    for s in sleeps_iter:  # breaking early prevents loading all results
        day = s['timestamp'].date()
        if day == today:
            today_sleeps.append(s)
        elif (today - day).days > 2:
            break

    total_sleep_mins = sum([s['total_sleep'] for s in today_sleeps])

    gauge.save(today_utc(), total_sleep_mins)
    logger.info('Saved {0} min. sleep for {1}'.format(total_sleep_mins,
                                                      today_utc()))


@requires('runkeeper.access_token')
def weight(gauge_factory, config, logger):
    """Saves last known weight (if any) for today
    """

    gauge = gauge_factory('runkeeper.weight')

    user = healthgraph.User(session=healthgraph.
                            Session(config['runkeeper.access_token']))

    weight = None
    weights_iter = user.get_weight_measurement_iter()

    # since items are loaded in descending order, first result is latest weight
    for w in weights_iter:
        weight = w['weight']
        break  # no need to load results further

    if weight:
        gauge.save(today_utc(), weight)
        logger.info('Saved {0} kg weight for {1}'.format(weight, today_utc()))
    else:
        logger.warning('Runkeeper has no weight measurement data.')

########NEW FILE########
__FILENAME__ = tmp102
# coding: utf-8

from . import requires
from pytz import timezone
from datetime import datetime
import smbus


"""Reads the instant temperature from TMP102 temperature sensor.
Requires packages:

    apt-get install i2c-tools
    apt-get install python-smbus

Configuration parameters:

    tmp102.tz: IANA timezone name to save the time of record. Use one of the
        strings from TZ column here for your local time:
        https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

    tmp102.bus: I2C bus number. if command "i2cdetect -y 1" shows anything
        use 1, or try 2 and so on
"""


@requires('tmp102.tz', 'tmp102.bus')
def temperature(gauge_factory, config, logger):
    """Saves current temperature in local time to hourly gauge.
    """

    gauge = gauge_factory('tmp102.temperature', gauge_type='hourly')
    tz = timezone(config['tmp102.tz'])

    # Code snippet taken from
    # http://bradsmc.blogspot.com/2013/04/reading-temperature-from-tmp02.html
    bus = smbus.SMBus(config['tmp102.bus'])
    data = bus.read_i2c_block_data(0x48, 0)
    msb = data[0]
    lsb = data[1]
    temp = (((msb << 8) | lsb) >> 4) * 0.0625
    now_local = datetime.now(tz)

    gauge.save(now_local, temp)
    logger.info('Saved temperature {0} C'.format(temp))

########NEW FILE########
__FILENAME__ = twitter
# coding: utf-8

from . import requires, today_utc
import tweepy


def twitter_api_handle(config):
    auth = tweepy.OAuthHandler(config['twitter.consumer_key'],
                               config['twitter.consumer_secret'])
    auth.set_access_token(config['twitter.access_token'],
                          config['twitter.access_secret'])
    return tweepy.API(auth)


@requires('twitter.consumer_key', 'twitter.consumer_secret',
          'twitter.access_token', 'twitter.access_secret')
def followers_count(gauge_factory, config, logger):
    gauge = gauge_factory('twitter.followers')
    api = twitter_api_handle(config)

    count = api.me().followers_count
    gauge.save(today_utc(), count)
    logger.info('Saved followers count: {0}'.format(count))


@requires('twitter.consumer_key', 'twitter.consumer_secret',
          'twitter.access_token', 'twitter.access_secret',
          'twitter.exclude_mentions')
def tweets_count(gauge_factory, config, logger):
    #TODO if you have tweeted 200+ tweets in a day, records as 200
    gauge = gauge_factory('twitter.tweets')
    api = twitter_api_handle(config)
    today = today_utc().date()

    timeline = api.user_timeline(count=200)
    timeline = filter(lambda st: st.created_at.date() == today, timeline)

    if config['twitter.exclude_mentions']:
      timeline = filter(lambda s: not s.text.startswith("@"), timeline)

    c = len(timeline)
    logger.info('Saved tweets count: {0} for {1}'.format(c, today))
    gauge.save(today_utc(), c)

########NEW FILE########
