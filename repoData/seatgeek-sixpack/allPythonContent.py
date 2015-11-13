__FILENAME__ = analysis
import cStringIO as StringIO
import csv


class ExportExperiment(object):

    def __init__(self, experiment=None):
        self.experiment = experiment

    def __call__(self):
        csvfile = StringIO.StringIO()
        writer = csv.writer(csvfile)
        writer.writerow(['Alternative Details'])
        writer.writerow(['date', 'alternative', 'participants', 'conversions'])
        obj = self.experiment.objectify_by_period('day')
        for alt in obj['alternatives']:
            for datum in alt['data']:
                writer.writerow([datum['date'], alt['name'], datum['participants'], datum['conversions']])
        writer.writerow([])

        writer.writerow(['"{0}" Summary'.format(obj['name'])])
        writer.writerow(['total participants', 'total_conversions', 'has_winner', 'description'])
        writer.writerow([obj['total_participants'], obj['total_conversions'], obj['has_winner'], obj['description']])

        writer.writerow([])
        writer.writerow(['Alternative Summary'])

        writer.writerow(['name', 'participant_count', 'completed_count'])
        for alt in obj['alternatives']:
            writer.writerow([alt['name'], alt['participant_count'], alt['completed_count']])

        return csvfile.getvalue()

########NEW FILE########
__FILENAME__ = api
from models import Experiment, Alternative, Client
from config import CONFIG as cfg


def participate(experiment, alternatives, client_id,
    force=None,
    traffic_fraction=None,
    alternative=None,
    datetime=None,
    redis=None):

    exp = Experiment.find_or_create(experiment, alternatives, traffic_fraction=traffic_fraction, redis=redis)

    alt = None
    if force and force in alternatives:
        alt = Alternative(force, exp, redis=redis)
    elif not cfg.get('enabled', True):
        alt = exp.control
    elif exp.winner is not None:
        alt = exp.winner
    else:
        client = Client(client_id, redis=redis)
        alt = exp.get_alternative(client, alternative=alternative, dt=datetime)

    return alt


def convert(experiment, client_id,
    kpi=None,
    datetime=None,
    redis=None):

    exp = Experiment.find(experiment, redis=redis)

    if cfg.get('enabled', True):
        client = Client(client_id, redis=redis)
        alt = exp.convert(client, dt=datetime, kpi=kpi)
    else:
        alt = exp.control

    return alt

########NEW FILE########
__FILENAME__ = config
import yaml
import os

from utils import to_bool

config_path = os.environ.get('SIXPACK_CONFIG', None)
if config_path:
    try:
        CONFIG = yaml.safe_load(open(config_path, 'r'))
    except IOError:
        raise RuntimeError('SIXPACK_CONFIG - {0} - is an invalid path'.format(config_path))
    except yaml.YAMLError, exc:
        raise RuntimeError('Error in configuration file: {0}'.format(str(exc)))
else:
    CONFIG = {
        'enabled': to_bool(os.environ.get('SIXPACK_CONFIG_ENABLED', 'True')),
        'redis_port': int(os.environ.get('SIXPACK_CONFIG_REDIS_PORT', '6379')),
        'redis_host': os.environ.get('SIXPACK_CONFIG_REDIS_HOST', "localhost"),
        'redis_password': os.environ.get('SIXPACK_CONFIG_REDIS_PASSWORD', None),
        'redis_prefix': os.environ.get('SIXPACK_CONFIG_REDIS_PREFIX', "sxp"),
        'redis_socket_timeout': os.environ.get('SIXPACK_CONFIG_REDIS_SOCKET_TIMEOUT', None),
        'redis_sentinel_service_name': os.environ.get('SIXPACK_CONFIG_REDIS_SENTINEL_SERVICE_NAME', None),
        'redis_db': int(os.environ.get('SIXPACK_CONFIG_REDIS_DB', '15')),
        'enable_whiplash': to_bool(os.environ.get('SIXPACK_CONFIG_WHIPLASH', 'False')),
        'robot_regex': os.environ.get('SIXPACK_CONFIG_ROBOT_REGEX', "$^|trivial|facebook|MetaURI|butterfly|google|"
                                                                    "amazon|goldfire|sleuth|xenu|msnbot|SiteUptime|"
                                                                    "Slurp|WordPress|ZIBB|ZyBorg|pingdom|bot|yahoo|"
                                                                    "slurp|java|fetch|spider|url|crawl|oneriot|abby|"
                                                                    "commentreader|twiceler"),
        'ignored_ip_addresses':os.environ.get('SIXPACK_CONFIG_IGNORE_IPS', "").split(","),
        'asset_path':os.environ.get('SIXPACK_CONFIG_ASSET_PATH', "gen"),
        'secret_key':os.environ.get('SIXPACK_CONFIG_SECRET', 'temp'),
    }

    if 'SIXPACK_CONFIG_REDIS_SENTINELS' in os.environ:
        sentinels = []
        for sentinel in os.environ['SIXPACK_CONFIG_REDIS_SENTINELS'].split(","):
            server,port = sentinel.split(":")
            sentinels.append([server, int(port)])
        CONFIG['redis_sentinels'] = sentinels

########NEW FILE########
__FILENAME__ = db
import redis
from redis.connection import PythonParser

from config import CONFIG as cfg

# Because of a bug (https://github.com/andymccurdy/redis-py/issues/318) with
# script reloading in `redis-py, we need to force the `PythonParser` to prevent
# sixpack from crashing if redis restarts (or scripts are flushed).
if cfg.get('redis_sentinels'):
    from redis.sentinel import Sentinel, SentinelConnectionPool
    service_name = cfg.get('redis_sentinel_service_name')
    sentinel = Sentinel(sentinels=cfg.get('redis_sentinels'),
                        password=cfg.get('redis_password', None),
                        socket_timeout=cfg.get('redis_socket_timeout'))
    pool = SentinelConnectionPool(service_name, sentinel,
                                db=cfg.get('redis_db'),
                                parser_class=PythonParser)
else:
    from redis.connection import ConnectionPool
    pool = ConnectionPool(host=cfg.get('redis_host'),
                        port=cfg.get('redis_port'),
                        password=cfg.get('redis_password', None),
                        db=cfg.get('redis_db'),
                        parser_class=PythonParser)

REDIS = redis.StrictRedis(connection_pool=pool)
DEFAULT_PREFIX = cfg.get('redis_prefix')


def _key(k):
    return "{0}:{1}".format(DEFAULT_PREFIX, k)


monotonic_zadd = REDIS.register_script("""
    local sequential_id = redis.call('zscore', KEYS[1], ARGV[1])
    if not sequential_id then
        sequential_id = redis.call('zcard', KEYS[1])
        redis.call('zadd', KEYS[1], sequential_id, ARGV[1])
    end
    return sequential_id
""")


def sequential_id(k, identifier):
    """Map an arbitrary string identifier to a set of sequential ids"""
    key = _key(k)
    return int(monotonic_zadd(keys=[key], args=[identifier]))


msetbit = REDIS.register_script("""
    for index, value in ipairs(KEYS) do
        redis.call('setbit', value, ARGV[(index - 1) * 2 + 1], ARGV[(index - 1) * 2 + 2])
    end
    return redis.status_reply('ok')
""")


first_key_with_bit_set = REDIS.register_script("""
    for index, value in ipairs(KEYS) do
        local bit = redis.call('getbit', value, ARGV[1])
        if bit == 1 then
             return value
        end
    end
    return false
""")

########NEW FILE########
__FILENAME__ = models
from datetime import datetime
from math import log
import operator
import random
import re

from config import CONFIG as cfg
from db import _key, msetbit, sequential_id, first_key_with_bit_set

# This is pretty restrictive, but we can always relax it later.
VALID_EXPERIMENT_ALTERNATIVE_RE = re.compile(r"^[a-z0-9][a-z0-9\-_]*$", re.I)
VALID_KPI_RE = re.compile(r"^[a-z0-9][a-z0-9\-_]*$", re.I)
RANDOM_SAMPLE = .2


class Client(object):

    def __init__(self, client_id, redis=None):
        self.redis = redis
        self.client_id = client_id


class Experiment(object):

    def __init__(self, name, alternatives,
        winner=False,
        traffic_fraction=False,
        redis=None):

        if len(alternatives) < 2:
            raise ValueError('experiments require at least two alternatives')

        self.name = name
        self.redis = redis
        self.random_sample = RANDOM_SAMPLE
        self.alternatives = self.initialize_alternatives(alternatives)
        self.kpi = None

        # False here is a sentinal value for "not looked up yet"
        self._winner = winner
        self._traffic_fraction = traffic_fraction
        self._sequential_ids = dict()

    def __repr__(self):
        return '<Experiment: {0})>'.format(self.name)

    def objectify_by_period(self, period):
        objectified = {
            'name': self.name,
            'period': period,
            'alternatives': [],
            'created_at': self.created_at,
            'total_participants': self.total_participants(),
            'total_conversions': self.total_conversions(),
            'description': self.description,
            'has_winner': self.winner is not None,
            'is_archived': self.is_archived(),
            'kpis': list(self.kpis),
            'kpi': self.kpi
        }

        for alternative in self.alternatives:
            objectified_alt = alternative.objectify_by_period(period)
            objectified['alternatives'].append(objectified_alt)

        return objectified

    def initialize_alternatives(self, alternatives):
        for alternative_name in alternatives:
            if not Alternative.is_valid(alternative_name):
                raise ValueError('invalid alternative name')

        return [Alternative(n, self, redis=self.redis) for n in alternatives]

    def save(self):
        pipe = self.redis.pipeline()
        if self.is_new_record():
            pipe.sadd(_key('e'), self.name)

        pipe.hset(self.key(), 'created_at', datetime.now())
        pipe.hset(self.key(), 'traffic_fraction', self._traffic_fraction)

        # reverse here and use lpush to keep consistent with using lrange
        for alternative in reversed(self.alternatives):
            pipe.lpush("{0}:alternatives".format(self.key()), alternative.name)

        pipe.execute()

    @property
    def control(self):
        return self.alternatives[0]

    @property
    def created_at(self):
        return self.redis.hget(self.key(), 'created_at')

    def get_alternative_names(self):
        return [alt.name for alt in self.alternatives]

    def is_new_record(self):
        return not self.redis.sismember(_key("e"), self.name)

    def total_participants(self):
        key = _key("p:{0}:_all:all".format(self.name))
        return self.redis.bitcount(key)

    def participants_by_day(self):
        return self._get_stats('participations', 'days')

    def participants_by_month(self):
        return self._get_stats('participations', 'months')

    def participants_by_year(self):
        return self._get_stats('participations', 'years')

    def total_conversions(self):
        key = _key("c:{0}:_all:users:all".format(self.kpi_key()))
        return self.redis.bitcount(key)

    def conversions_by_day(self):
        return self._get_stats('conversions', 'days')

    def conversions_by_month(self):
        return self._get_stats('conversions', 'months')

    def conversions_by_year(self):
        return self._get_stats('conversions', 'years')

    def _get_stats(self, stat_type, stat_range):
        if stat_type == 'participations':
            stat_type = 'p'
            exp_key = self.name
        elif stat_type == 'conversions':
            stat_type = 'c'
            exp_key = self.kpi_key()
        else:
            raise ValueError("Unrecognized stat type: {0}".format(stat_type))

        if stat_range not in ['days', 'months', 'years']:
            raise ValueError("Unrecognized stat range: {0}".format(stat_range))

        pipe = self.redis.pipe()

        stats = {}
        search_key = _key("{0}:{1}:{2}".format(stat_type, exp_key, stat_range))
        keys = self.redis.smembers(search_key)
        for k in keys:
            mod = '' if stat_type == 'p' else "users:"
            range_key = _key("{0}:{1}:_all:{2}{3}".format(stat_type, self.name, mod, k))
            pipe.bitcount(range_key)

        redis_results = pipe.execute()
        for idx, k in enumerate(keys):
            stats[k] = float(redis_results[idx])

        return stats

    def update_description(self, description=None):
        if description == '' or description is None:
            self.redis.hdel(self.key(), 'description')
        else:
            self.redis.hset(self.key(), 'description', description)

    @property
    def description(self):
        description = self.redis.hget(self.key(), 'description')
        if description:
            return description.decode("utf-8", "replace")
        else:
            return None

    def reset(self):
        self.delete()

        name = self.name
        alts = self.get_alternative_names()

        experiment = Experiment(name, alts, redis=self.redis)
        experiment.save()

    def delete(self):
        pipe = self.redis.pipeline()
        pipe.srem(_key('e'), self.name)
        pipe.delete(self.key())
        pipe.delete(_key(self.name))
        pipe.delete(_key('e:{0}'.format(self.name)))

        # Consider a 'non-keys' implementation of this
        keys = self.redis.keys('*:{0}:*'.format(self.name))
        for key in keys:
            pipe.delete(key)

        pipe.execute()

    def archive(self):
        self.redis.hset(self.key(), 'archived', 1)

    def unarchive(self):
        self.redis.hdel(self.key(), 'archived')

    def is_archived(self):
        return self.redis.hexists(self.key(), 'archived')

    def convert(self, client, dt=None, kpi=None):
        alternative = self.existing_alternative(client)
        if not alternative:
            raise ValueError('this client was not participaing')

        if kpi is not None:
            if not Experiment.validate_kpi(kpi):
                raise ValueError('invalid kpi name')
            self.add_kpi(kpi)

        if not self.existing_conversion(client):
            alternative.record_conversion(client, dt=dt)

        return alternative

    @property
    def kpis(self):
        return self.redis.smembers("{0}:kpis".format(self.key(include_kpi=False)))

    def set_kpi(self, kpi):
        self.kpi = None

        key = "{0}:kpis".format(self.key())
        if kpi not in self.redis.smembers(key):
            raise ValueError('invalid kpi')

        self.kpi = kpi

    def add_kpi(self, kpi):
        self.redis.sadd("{0}:kpis".format(self.key(include_kpi=False)), kpi)
        self.kpi = kpi

    @property
    def winner(self):
        if self._winner is False:
            self._winner = self.redis.get(self._winner_key)
        if self._winner:
            return Alternative(self._winner, self, redis=self.redis)

    def set_winner(self, alternative_name):
        if alternative_name not in self.get_alternative_names():
            raise ValueError('this alternative is not in this experiment')
        self._winner = alternative_name
        self.redis.set(self._winner_key, alternative_name)

    def reset_winner(self):
        self._winner = None
        self.redis.delete(self._winner_key)

    @property
    def _winner_key(self):
        return "{0}:winner".format(self.key())

    @property
    def traffic_fraction(self):
        if self._traffic_fraction is False:
            try:
                self._traffic_fraction = float(self.redis.hget(self.key(), 'traffic_fraction'))
            except (TypeError, ValueError) as e:
                self._traffic_fraction = 1
        return self._traffic_fraction

    def set_traffic_fraction(self, fraction):
        fraction = float(fraction)
        if not 0 < fraction <= 1:
            raise ValueError('invalid traffic fraction range')

        self._traffic_fraction = fraction

    def sequential_id(self, client):
        """Return the sequential id for this test for the passed in client"""
        if client.client_id not in self._sequential_ids:
            id_ = sequential_id("e:{0}:users".format(self.name), client.client_id)
            self._sequential_ids[client.client_id] = id_
        return self._sequential_ids[client.client_id]

    def get_alternative(self, client, alternative=None, dt=None):
        """Returns and records an alternative according to the following
        precedence:
          1. An existing alternative
          2. A client-chosen alternative
          3. A server-chosen alternative
        """
        if self.is_archived():
            return self.control

        chosen_alternative = self.existing_alternative(client)
        if not chosen_alternative:
            if alternative:
                chosen_alternative, participate = Alternative(alternative, self, redis=self.redis), True
            else:
                chosen_alternative, participate = self.choose_alternative(client)
            if participate:
                chosen_alternative.record_participation(client, dt=dt)

        return chosen_alternative

    def exclude_client(self, client):
        key = _key("e:{0}:excluded".format(self.name))
        self.redis.setbit(key, self.sequential_id(client), 1)

    def is_client_excluded(self, client):
        key = _key("e:{0}:excluded".format(self.name))
        return self.redis.getbit(key, self.sequential_id(client))

    def existing_alternative(self, client):
        if self.is_client_excluded(client):
            return self.control

        alts = self.get_alternative_names()
        keys = [_key("p:{0}:{1}:all".format(self.name, alt)) for alt in alts]
        altkey = first_key_with_bit_set(keys=keys, args=[self.sequential_id(client)])
        if altkey:
            idx = keys.index(altkey)
            return Alternative(alts[idx], self, redis=self.redis)

        return None

    def choose_alternative(self, client):
        rnd = round(random.uniform(1, 0.01), 2)
        if rnd >= self.traffic_fraction:
            self.exclude_client(client)
            return self.control, False

        if cfg.get('enable_whiplash') and random.random() >= self.random_sample:
            return Alternative(self._whiplash(), self, redis=self.redis), True

        return self._random_choice(), True

    def _random_choice(self):
        return random.choice(self.alternatives)

    def _whiplash(self):
        stats = {}
        for alternative in self.alternatives:
            participant_count = alternative.participant_count()
            completed_count = alternative.completed_count()
            stats[alternative.name] = self._arm_guess(participant_count, completed_count)

        return max(stats.iteritems(), key=operator.itemgetter(1))[0]

    def _arm_guess(self, participant_count, completed_count):
        fairness_score = 7

        a = max([participant_count, 0])
        b = max([participant_count - completed_count, 0])

        return random.betavariate(a + fairness_score, b + fairness_score)

    def existing_conversion(self, client):
        alts = self.get_alternative_names()
        keys = [_key("c:{0}:{1}:users:all".format(self.kpi_key(), alt)) for alt in alts]
        altkey = first_key_with_bit_set(keys=keys, args=[self.sequential_id(client)])
        if altkey:
            idx = keys.index(altkey)
            return Alternative(alts[idx], self, redis=self.redis)

        return None

    def kpi_key(self):
        if self.kpi is not None:
            return "{0}/{1}".format(self.name, self.kpi)
        else:
            return self.name

    def key(self, include_kpi=True):
        if include_kpi:
            return _key("e:{0}".format(self.kpi_key()))
        else:
            return _key("e:{0}".format(self.name))

    @classmethod
    def find(cls, experiment_name,
        redis=None):

        if not redis.sismember(_key("e"), experiment_name):
            raise ValueError('experiment does not exist')

        return cls(experiment_name,
                   Experiment.load_alternatives(experiment_name, redis),
                   redis=redis)

    @classmethod
    def find_or_create(cls, experiment_name, alternatives,
        traffic_fraction=None,
        redis=None):

        if len(alternatives) < 2:
            raise ValueError('experiments require at least two alternatives')

        if traffic_fraction is None:
            traffic_fraction = 1

        try:
            experiment = Experiment.find(experiment_name, redis=redis)
        except ValueError:
            experiment = cls(experiment_name, alternatives, redis=redis)
            # TODO: I want to revist this later
            experiment.set_traffic_fraction(traffic_fraction)
            experiment.save()

        # Make sure the alternative options are correct. If they are not,
        # raise an error.
        if sorted(experiment.get_alternative_names()) != sorted(alternatives):
            raise ValueError('experiment alternatives have changed. please delete in the admin')

        return experiment

    @staticmethod
    def all_names(redis=None):
        return redis.smembers(_key('e'))

    @staticmethod
    def all(exclude_archived=True, redis=None):
        experiments = []
        keys = redis.smembers(_key('e'))

        for key in keys:
            experiment = Experiment.find(key, redis=redis)
            if experiment.is_archived() and exclude_archived:
                continue
            experiments.append(experiment)
        return experiments

    @staticmethod
    def archived(redis=None):
        experiments = Experiment.all(exclude_archived=False, redis=redis)
        return [exp for exp in experiments if exp.is_archived()]

    @staticmethod
    def load_alternatives(experiment_name, redis=None):
        key = _key("e:{0}:alternatives".format(experiment_name))
        return redis.lrange(key, 0, -1)

    @staticmethod
    def is_valid(experiment_name):
        return (isinstance(experiment_name, basestring) and
                VALID_EXPERIMENT_ALTERNATIVE_RE.match(experiment_name) is not None)

    @staticmethod
    def validate_kpi(kpi):
        return (isinstance(kpi, basestring) and
                VALID_KPI_RE.match(kpi) is not None)


class Alternative(object):

    def __init__(self, name, experiment, redis=None):
        self.name = name
        self.experiment = experiment
        self.redis = redis

    def __repr__(self):
        return "<Alternative {0} (Experiment {1})>".format(repr(self.name), repr(self.experiment.name))

    def objectify_by_period(self, period):
        PERIOD_TO_METHOD_MAP = {
            'day': {
                'participants': self.participants_by_day,
                'conversions': self.conversions_by_day
            },
            'month': {
                'participants': self.participants_by_month,
                'conversions': self.conversions_by_month
            },
            'year': {
                'participants': self.participants_by_year,
                'conversions': self.conversions_by_year
            },
        }

        data = []
        conversion_fn = PERIOD_TO_METHOD_MAP[period]['conversions']
        participants_fn = PERIOD_TO_METHOD_MAP[period]['participants']

        conversions = conversion_fn()
        participants = participants_fn()

        dates = sorted(list(set(conversions.keys() + participants.keys())))
        for date in dates:
            _data = {
                'conversions': conversions.get(date, 0),
                'participants': participants.get(date, 0),
                'date': date
            }
            data.append(_data)

        objectified = {
            'name': self.name,
            'data': data,
            'conversion_rate': float('%.2f' % (self.conversion_rate() * 100)),
            'is_control': self.is_control(),
            'is_winner': self.is_winner(),
            'test_statistic': self.g_stat(),
            'participant_count': self.participant_count(),
            'completed_count': self.completed_count(),
            'confidence_level': self.confidence_level(),
            'confidence_interval': self.confidence_interval()
        }

        return objectified

    def is_control(self):
        return self.experiment.control.name == self.name

    def is_winner(self):
        winner = self.experiment.winner
        return winner and winner.name == self.name

    def participant_count(self):
        key = _key("p:{0}:{1}:all".format(self.experiment.name, self.name))
        return self.redis.bitcount(key)

    def participants_by_day(self):
        return self._get_stats('participations', 'days')

    def participants_by_month(self):
        return self._get_stats('participations', 'months')

    def participants_by_year(self):
        return self._get_stats('participations', 'years')

    def completed_count(self):
        key = _key("c:{0}:{1}:users:all".format(self.experiment.kpi_key(), self.name))
        return self.redis.bitcount(key)

    def conversions_by_day(self):
        return self._get_stats('conversions', 'days')

    def conversions_by_month(self):
        return self._get_stats('conversions', 'months')

    def conversions_by_year(self):
        return self._get_stats('conversions', 'years')

    def _get_stats(self, stat_type, stat_range):
        if stat_type == 'participations':
            stat_type = 'p'
            exp_key = self.experiment.name
        elif stat_type == 'conversions':
            stat_type = 'c'
            exp_key = self.experiment.kpi_key()
        else:
            raise ValueError("Unrecognized stat type: {0}".format(stat_type))

        if stat_range not in ['days', 'months', 'years']:
            raise ValueError("Unrecognized stat range: {0}".format(stat_range))

        stats = {}

        pipe = self.redis.pipeline()

        search_key = _key("{0}:{1}:{2}".format(stat_type, exp_key, stat_range))
        keys = self.redis.smembers(search_key)

        for k in keys:
            name = self.name if stat_type == 'p' else "{0}:users".format(self.name)
            range_key = _key("{0}:{1}:{2}:{3}".format(stat_type, exp_key, name, k))
            pipe.bitcount(range_key)

        redis_results = pipe.execute()
        for idx, k in enumerate(keys):
            stats[k] = float(redis_results[idx])

        return stats

    def record_participation(self, client, dt=None):
        """Record a user's participation in a test along with a given variation"""
        if dt is None:
            date = datetime.now()
        else:
            date = dt

        experiment_key = self.experiment.name

        pipe = self.redis.pipeline()

        pipe.sadd(_key("p:{0}:years".format(experiment_key)), date.strftime('%Y'))
        pipe.sadd(_key("p:{0}:months".format(experiment_key)), date.strftime('%Y-%m'))
        pipe.sadd(_key("p:{0}:days".format(experiment_key)), date.strftime('%Y-%m-%d'))

        pipe.execute()

        keys = [
            _key("p:{0}:_all:all".format(experiment_key)),
            _key("p:{0}:_all:{1}".format(experiment_key, date.strftime('%Y'))),
            _key("p:{0}:_all:{1}".format(experiment_key, date.strftime('%Y-%m'))),
            _key("p:{0}:_all:{1}".format(experiment_key, date.strftime('%Y-%m-%d'))),
            _key("p:{0}:{1}:all".format(experiment_key, self.name)),
            _key("p:{0}:{1}:{2}".format(experiment_key, self.name, date.strftime('%Y'))),
            _key("p:{0}:{1}:{2}".format(experiment_key, self.name, date.strftime('%Y-%m'))),
            _key("p:{0}:{1}:{2}".format(experiment_key, self.name, date.strftime('%Y-%m-%d'))),
        ]
        msetbit(keys=keys, args=([self.experiment.sequential_id(client), 1] * len(keys)))

    def record_conversion(self, client, dt=None):
        """Record a user's conversion in a test along with a given variation"""
        if dt is None:
            date = datetime.now()
        else:
            date = dt

        experiment_key = self.experiment.kpi_key()

        pipe = self.redis.pipeline()

        pipe.sadd(_key("c:{0}:years".format(experiment_key)), date.strftime('%Y'))
        pipe.sadd(_key("c:{0}:months".format(experiment_key)), date.strftime('%Y-%m'))
        pipe.sadd(_key("c:{0}:days".format(experiment_key)), date.strftime('%Y-%m-%d'))

        pipe.execute()

        keys = [
            _key("c:{0}:_all:users:all".format(experiment_key)),
            _key("c:{0}:_all:users:{1}".format(experiment_key, date.strftime('%Y'))),
            _key("c:{0}:_all:users:{1}".format(experiment_key, date.strftime('%Y-%m'))),
            _key("c:{0}:_all:users:{1}".format(experiment_key, date.strftime('%Y-%m-%d'))),
            _key("c:{0}:{1}:users:all".format(experiment_key, self.name)),
            _key("c:{0}:{1}:users:{2}".format(experiment_key, self.name, date.strftime('%Y'))),
            _key("c:{0}:{1}:users:{2}".format(experiment_key, self.name, date.strftime('%Y-%m'))),
            _key("c:{0}:{1}:users:{2}".format(experiment_key, self.name, date.strftime('%Y-%m-%d'))),
        ]
        msetbit(keys=keys, args=([self.experiment.sequential_id(client), 1] * len(keys)))

    def conversion_rate(self):
        try:
            return self.completed_count() / float(self.participant_count())
        except ZeroDivisionError:
            return 0

    def g_stat(self):
        # http://en.wikipedia.org/wiki/G-test

        if self.is_control():
            return 'N/A'

        control = self.experiment.control

        alt_conversions = self.completed_count()
        control_conversions = control.completed_count()
        alt_failures = self.participant_count() - alt_conversions
        control_failures = control.participant_count() - control_conversions

        total_conversions = alt_conversions + control_conversions

        if total_conversions < 20:
            # small sample size of conversions, see where it goes for a bit
            return 'N/A'

        total_participants = self.participant_count() + control.participant_count()

        expected_control_conversions = control.participant_count() * total_conversions / float(total_participants)
        expected_alt_conversions = self.participant_count() * total_conversions / float(total_participants)
        expected_control_failures = control.participant_count() - expected_control_conversions
        expected_alt_failures = self.participant_count() - expected_alt_conversions

        try:
            g_stat = 2 * (      alt_conversions * log(alt_conversions / expected_alt_conversions) \
                        +   alt_failures * log(alt_failures / expected_alt_failures) \
                        +   control_conversions * log(control_conversions / expected_control_conversions) \
                        +   control_failures * log(control_failures / expected_control_failures))

        except ZeroDivisionError:
            return 0

        return round(g_stat, 2)

    def z_score(self):
        if self.is_control():
            return 'N/A'

        control = self.experiment.control
        ctr_e = self.conversion_rate()
        ctr_c = control.conversion_rate()

        e = self.participant_count()
        c = control.participant_count()

        try:
            std_dev = pow(((ctr_e / pow(ctr_c, 3)) * ((e * ctr_e) + (c * ctr_c) - (ctr_c * ctr_e) * (c + e)) / (c * e)), 0.5)
            z_score = ((ctr_e / ctr_c) - 1) / std_dev
            return z_score
        except ZeroDivisionError:
            return 0

    def g_confidence_level(self):
        # g stat is approximated by chi-square, we will use
        # critical values from chi-square distribution with one degree of freedom

        g_stat = self.g_stat()
        if g_stat == 'N/A':
            return g_stat

        ret = ''
        if g_stat == 0.0:
            ret = 'No Change'
        elif g_stat < 3.841:
            ret = 'No Confidence'
        elif g_stat < 6.635:
            ret = '95% Confidence'
        elif g_stat < 10.83:
            ret = '99% Confidence'
        else:
            ret = '99.9% Confidence'

        return ret

    def z_confidence_level(self):
        z_score = self.z_score()
        if z_score == 'N/A':
            return z_score

        z_score = abs(round(z_score, 3))

        ret = ''
        if z_score == 0.0:
            ret = 'No Change'
        elif z_score < 1.96:
            ret = 'No Confidence'
        elif z_score < 2.57:
            ret = '95% Confidence'
        elif z_score < 3.27:
            ret = '99% Confidence'
        else:
            ret = '99.9% Confidence'

        return ret

    def confidence_level(self, conf_type="g"):
        if conf_type == "z":
            return self.z_confidence_level()
        else:
            return self.g_confidence_level()

    def confidence_interval(self):
        try:
            # 80% confidence
            p = self.conversion_rate()
            return pow(p * (1 - p) / self.participant_count(), 0.5) * 1.28 * 100
        except ZeroDivisionError:
            return 0

    def key(self):
        return _key("{0}:{1}".format(self.experiment.name, self.name))

    @staticmethod
    def is_valid(alternative_name):
        return (isinstance(alternative_name, basestring) and
                VALID_EXPERIMENT_ALTERNATIVE_RE.match(alternative_name) is not None)

########NEW FILE########
__FILENAME__ = server
import re
from socket import inet_aton
import sys
from urllib import unquote

import dateutil.parser
from redis import ConnectionError
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound

from . import __version__, participate, convert
from config import CONFIG as cfg

try:
    import db
except ConnectionError:
    print "Redis is currently unavailable or misconfigured"
    sys.exit()

from models import Experiment, Client
from utils import service_unavailable_on_connection_error, json_error, json_success


class Sixpack(object):

    def __init__(self, redis_conn):
        self.redis = redis_conn

        self.config = cfg

        self.url_map = Map([
            Rule('/', endpoint='home'),
            Rule('/_status', endpoint='status'),
            Rule('/participate', endpoint='participate'),
            Rule('/convert', endpoint='convert'),
            Rule('/favicon.ico', endpoint='favicon')
        ])

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except NotFound:
            return json_error({"message": "not found"}, request, 404)
        except HTTPException:
            return json_error({"message": "an internal error has occurred"}, request, 500)

    @service_unavailable_on_connection_error
    def on_status(self, request):
        self.redis.ping()
        return json_success({'version': __version__}, request)

    def on_home(self, request):
        dales = """
                 ,-"-.__,-"-.__,-"-..
                ( C>  )( C>  )( C>  ))
               /.`-_-'||`-_-'||`-_-'/
              /-"-.--,-"-.--,-"-.--/|
             ( C>  )( C>  )( C>  )/ |
            (|`-_-',.`-_-',.`-_-'/  |
             `-----++-----++----'|  |
             |     ||     ||     |-'
             |     ||     ||     |
             |     ||     ||     |
              `-_-'  `-_-'  `-_-'
        https://github.com/seatgeek/sixpack"""
        return Response(dales)

    def on_favicon(self, request):
        return Response()

    @service_unavailable_on_connection_error
    def on_convert(self, request):
        if should_exclude_visitor(request):
            return json_success({'excluded': 'true'}, request)

        experiment_name = request.args.get('experiment')
        client_id = request.args.get('client_id')
        kpi = request.args.get('kpi', None)

        if client_id is None or experiment_name is None:
            return json_error({'message': 'missing arguments'}, request, 400)

        dt = None
        if request.args.get("datetime"):
            dt = dateutil.parser.parse(request.args.get("datetime"))

        try:
            alt = convert(experiment_name, client_id, kpi=kpi, datetime=dt, redis=self.redis)
        except ValueError as e:
            return json_error({'message': str(e)}, request, 400)

        resp = {
            'alternative': {
                'name': alt.name
            },
            'experiment': {
                'name': alt.experiment.name,
            },
            'conversion': {
                'value': None,
                'kpi': kpi
            },
            'client_id': client_id
        }

        return json_success(resp, request)

    @service_unavailable_on_connection_error
    def on_participate(self, request):
        alts = request.args.getlist('alternatives')
        experiment_name = request.args.get('experiment')
        force = request.args.get('force')
        client_id = request.args.get('client_id')
        traffic_fraction = float(request.args.get('traffic_fraction', 1))
        client_chosen_alt = request.args.get('alternative', None)

        if client_id is None or experiment_name is None or alts is None:
            return json_error({'message': 'missing arguments'}, request, 400)

        dt = None
        if request.args.get("datetime"):
            dt = dateutil.parser.parse(request.args.get("datetime"))

        if should_exclude_visitor(request):
            exp = Experiment.find(experiment_name, redis=self.redis)
            if exp.winner is not None:
                alt = exp.winner
            else:
                alt = exp.control
        else:
            try:
                alt = participate(experiment_name, alts, client_id,
                                  force=force, traffic_fraction=traffic_fraction,
                                  alternative=client_chosen_alt, datetime=dt, redis=self.redis)
            except ValueError as e:
                return json_error({'message': str(e)}, request, 400)

        resp = {
            'alternative': {
                'name': alt.name
            },
            'experiment': {
                'name': alt.experiment.name,
            },
            'client_id': client_id,
            'status': 'ok'
        }

        return json_success(resp, request)


def should_exclude_visitor(request):
    user_agent = request.args.get('user_agent')
    ip_address = request.args.get('ip_address')

    return is_robot(user_agent) or is_ignored_ip(ip_address)


def is_robot(user_agent):
    if user_agent is None:
        return False
    regex = re.compile(r"{0}".format(cfg.get('robot_regex')), re.I)
    return regex.search(unquote(user_agent)) is not None


def is_ignored_ip(ip_address):
    # Ignore invalid/local IP addresses
    try:
        inet_aton(unquote(ip_address))
    except:
        return False  # TODO Same as above not sure of default

    return unquote(ip_address) in cfg.get('ignored_ip_addresses')


# Method to run with built-in server
def create_app():
    app = Sixpack(db.REDIS)
    return app


# Method to run with gunicorn
def start(environ, start_response):
    app = Sixpack(db.REDIS)
    return app(environ, start_response)

########NEW FILE########
__FILENAME__ = alternative_choice_test
import unittest
import json

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from sixpack.server import create_app
from sixpack.models import Experiment


class TestAlternativeChoice(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = Client(self.app, BaseResponse)

    def test_bots_get_winner_otherwise_control(self):
        e = Experiment.find_or_create("bots-get-winner", ["one", "two"], redis=self.app.redis)
        # control at first
        for i in range(3):
            data = json.loads(self.client.get("/participate?experiment=bots-get-winner&alternatives=one&alternatives=two&user_agent=GoogleBot&client_id=rand").data)
            self.assertEqual(data['alternative']['name'], 'one')
        # winner once one is set
        e.set_winner("two")
        for i in range(3):
            data = json.loads(self.client.get("/participate?experiment=bots-get-winner&alternatives=one&alternatives=two&user_agent=GoogleBot&client_id=rand").data)
            self.assertEqual(data['alternative']['name'], 'two')

    def test_force_param_always_wins(self):
        alts = ["one", "two", "three"]
        e = Experiment.find_or_create("force-param-always-wins", alts, redis=self.app.redis)

        def test_force():
            for f in alts:
                data = json.loads(self.client.get("/participate?experiment=force-param-always-wins&alternatives=one&alternatives=two&alternatives=three&client_id=rand&force={0}".format(f)).data)
                self.assertEqual(data['alternative']['name'], f)
        # before a winner
        test_force()
        e.set_winner("three")
        # after a winner
        test_force()

    def test_client_chosen_alternative(self):
        alts = ["one", "two", "three"]
        e = Experiment.find_or_create("client-chosen-alternative", alts, redis=self.app.redis)

        data = json.loads(self.client.get("/participate?experiment=client-chosen-alternative&alternatives=one&alternatives=two&alternatives=three&client_id=1&alternative=one").data)
        self.assertEqual(data['alternative']['name'], 'one')
        self.assertEqual(e.total_participants(), 1)

        data = json.loads(self.client.get("/participate?experiment=client-chosen-alternative&alternatives=one&alternatives=two&alternatives=three&client_id=2&alternative=two").data)
        self.assertEqual(data['alternative']['name'], 'two')
        self.assertEqual(e.total_participants(), 2)

########NEW FILE########
__FILENAME__ = alternative_model_test
import unittest
import fakeredis

from sixpack.models import Alternative, Experiment


class TestAlternativeModel(unittest.TestCase):

    unit = True

    def setUp(self):
        self.redis = fakeredis.FakeStrictRedis()
        self.client_id = 381

    def test_key(self):
        exp = Experiment('show-something', ['yes', 'no'], redis=self.redis)

        alt = Alternative('yes', exp, redis=self.redis)
        key = alt.key()
        self.assertEqual(key, 'sxp:show-something:yes')

    def test_is_valid(self):
        valid = Alternative.is_valid('1')
        self.assertTrue(valid)

        unicode_valid = Alternative.is_valid(u'valid')
        self.assertTrue(unicode_valid)

    def test_is_not_valid(self):
        not_valid = Alternative.is_valid(1)
        self.assertFalse(not_valid)

        not_valid = Alternative.is_valid(':123:name')
        self.assertFalse(not_valid)

        not_valid = Alternative.is_valid('_123name')
        self.assertFalse(not_valid)

        not_valid = Alternative.is_valid('&123name')
        self.assertFalse(not_valid)

    def test_is_control(self):
        exp = Experiment('trololo', ['yes', 'no'], redis=self.redis)
        exp.save()

        alt = Alternative('yes', exp, redis=self.redis)
        self.assertTrue(alt.is_control())
        exp.delete()

    def test_experiment(self):
        exp = Experiment('trololo', ['yes', 'no'], redis=self.redis)
        exp.save()

        alt = Alternative('yes', exp, redis=self.redis)
        self.assertTrue(alt.is_control())

    def test_participant_count(self):
        pass
        # self.redis.bitcount.return_value = 0

        # alt = Alternative('yes', 'show-something', self.redis)
        # count = alt.participant_count()

        # key = _key("participation:{0}:{1}".format(alt.experiment_name, alt.name))
        # self.redis.bitcount.assert_called_once_with(key)
        # self.assertTrue(isinstance(count, Number))

        # self.redis.reset_mock()

    def test_conversion_count(self):
        pass
        # self.redis.reset_mock()
        # self.redis.bitcount.return_value = 0

        # alt = Alternative('yes', 'show-something', self.redis)
        # count = alt.completed_count()

        # key = _key("c:{0}/1:{1}".format(alt.experiment_name, alt.name))
        # self.redis.bitcount.assert_called_once_with(key)
        # self.assertTrue(isinstance(count, Number))

        # self.redis.reset_mock()

    # TODO Test this
    def test_record_participation(self):
        pass
        # alt = Alternative('yes', 'show-something', self.redis)
        # alt.record_participation(self.client_id)

        # key = _key("participation:{0}:{1}".format(alt.experiment_name, alt.name))
        # self.redis.setbit.assert_called_once_with(key, self.client_id, 1)

    def test_record_conversion(self):
        pass
        # client = Client('xyz', self.redis)
        # alt = Alternative('yes', 'show-something', self.redis)
        # alt.record_conversion(client)

        # key = _key("conversion:{0}:{1}".format(alt.experiment_name, alt.name))
        # self.redis.setbit.assert_called_once_with(key, self.client_id, 1)

########NEW FILE########
__FILENAME__ = api_test
import unittest
from mock import patch, Mock

import sixpack
from sixpack.models import Experiment, Alternative


class TestApi(unittest.TestCase):

    @patch.object(Experiment, "find_or_create")
    def test_participate(self, mock_find_or_create):
        exp = Experiment("test", ["no", "yes"], winner=None)
        exp.get_alternative = Mock(return_value=Alternative("yes", exp))
        mock_find_or_create.return_value = exp
        alternative = sixpack.participate("test", ["no", "yes"], "id1")
        self.assertEqual("yes", alternative.name)
        self.assertEqual("test", alternative.experiment.name)

    @patch.object(Experiment, "find_or_create")
    def test_participate_with_forced_alternative(self, mock_find_or_create):
        mock_find_or_create.return_value = Experiment("test", ["no", "yes"], winner=None)
        alternative = sixpack.participate("test", ["no", "yes"], "id1", force="yes")
        self.assertEqual("yes", alternative.name)

    @patch.object(Experiment, "find_or_create")
    def test_participate_with_client_chosen_alternative(self, mock_find_or_create):
        exp = Experiment("test", ["no", "yes"], winner=None)
        exp.get_alternative = Mock(return_value=Alternative("yes", exp))
        mock_find_or_create.return_value = exp
        alternative = sixpack.participate("test", ["no", "yes"], "id1", alternative="yes")
        exp.get_alternative.assert_called_once()
        self.assertEqual("yes", alternative.name)

    @patch.object(Experiment, "find")
    def test_convert(self, mock_find):
        exp = Experiment("test", ["no", "yes"], winner=None)
        exp.convert = Mock(return_value=Alternative("yes", exp))
        mock_find.return_value = exp
        alternative = sixpack.convert("test", "id1")
        self.assertEqual("yes", alternative.name)
        self.assertEqual("test", alternative.experiment.name)

    @patch.object(Experiment, "find")
    def test_convert_with_kpi(self, mock_find):
        exp = Experiment("test", ["no", "yes"], winner=None)
        exp.convert = Mock(return_value=Alternative("yes", exp))
        mock_find.return_value = exp
        alternative = sixpack.convert("test", "id1", kpi="goal1")
        # TODO: we're not really asserting anything about the KPI
        self.assertEqual("yes", alternative.name)
        self.assertEqual("test", alternative.experiment.name)

########NEW FILE########
__FILENAME__ = bot_detection_test
import unittest
from sixpack.server import is_robot


user_agents = {
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)": True,
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/536.28.10 (KHTML, like Gecko) Version/6.0.3 Safari/536.28.10": False,
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; MDDR; .NET4.0C; .NET4.0E)": False,
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)": True,
    "Pingdom.com_bot_version_1.4_(http://www.pingdom.com/)": True,
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.65 Safari/537.31": False
}


class TestBotDetection(unittest.TestCase):

    unit = True

    def test_is_bot(self):
        for ua, is_bot in user_agents.items():
            self.assertEqual(is_robot(ua), is_bot)

########NEW FILE########
__FILENAME__ = experiment_lua_test
import unittest
import json

import dateutil.parser

from sixpack.server import create_app
from sixpack.models import Client, Experiment


class TestExperimentLua(unittest.TestCase):

    def setUp(self):
        self.app = create_app()

    def test_convert(self):
        exp = Experiment('test-convert', ['1', '2'], redis=self.app.redis)
        client = Client("eric", redis=self.app.redis)
        exp.get_alternative(client)
        exp.convert(client)
        self.assertEqual(exp.total_conversions(), 1)

    def test_cant_convert_twice(self):
        exp = Experiment('test-cant-convert-twice', ['1', '2'], redis=self.app.redis)
        client = Client("eric", redis=self.app.redis)
        alt = exp.get_alternative(client)
        exp.convert(client)
        self.assertEqual(exp.total_conversions(), 1)

        exp.convert(client, dt=dateutil.parser.parse("2012-01-01"))
        self.assertEqual(exp.total_conversions(), 1)

        data = exp.objectify_by_period("day")
        altdata = [a for a in data["alternatives"] if a["name"] == alt.name][0]["data"]
        total_participants = sum([d["participants"] for d in altdata])
        self.assertEqual(total_participants, 1)
        total_conversions = sum([d["conversions"] for d in altdata])
        self.assertEqual(total_conversions, 1)

    def test_find_existing_conversion(self):
        exp = Experiment('test-find-existing-conversion', ['1', '2'], redis=self.app.redis)
        client = Client("eric", redis=self.app.redis)
        alt = exp.get_alternative(client)
        exp.convert(client)
        alt2 = exp.existing_conversion(client)
        self.assertIsNotNone(alt2)
        self.assertTrue(alt.name == alt2.name)
        client2 = Client("zack", redis=self.app.redis)
        alt3 = exp.existing_conversion(client2)
        self.assertIsNone(alt3)

########NEW FILE########
__FILENAME__ = experiment_model_test
import unittest
# from numbers import Number
# from sixpack.db import _key
from datetime import datetime

import fakeredis

from sixpack.models import Experiment, Alternative, Client


class TestExperimentModel(unittest.TestCase):

    unit = True

    def setUp(self):
        self.redis = fakeredis.FakeStrictRedis()
        self.alternatives = ['yes', 'no']

        self.exp_1 = Experiment('show-something-awesome', self.alternatives, redis=self.redis)
        self.exp_2 = Experiment('dales-lagunitas', ['dales', 'lagunitas'], redis=self.redis)
        self.exp_3 = Experiment('mgd-budheavy', ['mgd', 'bud-heavy'], redis=self.redis)
        self.exp_1.save()
        self.exp_2.save()
        self.exp_3.save()

    def test_constructor(self):
        with self.assertRaises(ValueError):
            Experiment('not-enough-args', ['1'], redis=self.redis)

    def test_save(self):
        pass

    def test_control(self):
        control = self.exp_1.control
        self.assertEqual(control.name, 'yes')

    def test_created_at(self):
        exp = Experiment('bench-press', ['joe', 'think'], redis=self.redis)
        date = exp.created_at
        self.assertIsNone(date)
        exp.save()
        date = exp.created_at
        self.assertTrue(isinstance(date, datetime))

    def test_get_alternative_names(self):
        exp = Experiment('show-something', self.alternatives, redis=self.redis)
        names = exp.get_alternative_names()
        self.assertEqual(sorted(self.alternatives), sorted(names))

    def test_is_new_record(self):
        exp = Experiment('show-something-is-new-record', self.alternatives, redis=self.redis)
        self.assertTrue(exp.is_new_record())
        exp.save()
        self.assertFalse(exp.is_new_record())

    # fakeredis does not currently support bitcount
    # todo, fix fakeredis and
    def _test_total_participants(self):
        pass

    def _test_total_conversions(self):
        pass

    def test_description(self):
        exp = Experiment.find_or_create('never-gonna', ['give', 'you', 'up'], redis=self.redis)
        self.assertEqual(exp.description, None)

        exp.update_description('hallo')
        self.assertEqual(exp.description, 'hallo')

    def test_change_alternatives(self):
        exp = Experiment.find_or_create('never-gonna-x', ['let', 'you', 'down'], redis=self.redis)

        with self.assertRaises(ValueError):
            Experiment.find_or_create('never-gonna-x', ['let', 'you', 'down', 'give', 'you', 'up'], redis=self.redis)

        exp.delete()

        Experiment.find_or_create('never-gonna-x', ['let', 'you', 'down', 'give', 'you', 'up'], redis=self.redis)

    def test_delete(self):
        exp = Experiment('delete-me', self.alternatives, redis=self.redis)
        exp.save()

        exp.delete()
        with self.assertRaises(ValueError):
            Experiment.find('delete-me', redis=self.redis)

    def test_leaky_delete(self):
        exp = Experiment('delete-me-1', self.alternatives, redis=self.redis)
        exp.save()

        exp2 = Experiment('delete', self.alternatives, redis=self.redis)
        exp2.save()

        exp2.delete()
        exp3 = Experiment.find('delete-me-1', redis=self.redis)
        self.assertEqual(exp3.get_alternative_names(), self.alternatives)

    def test_archive(self):
        self.assertFalse(self.exp_1.is_archived())
        self.exp_1.archive()
        self.assertTrue(self.exp_1.is_archived())
        self.exp_1.unarchive()
        self.assertFalse(self.exp_1.is_archived())

    def test_unarchive(self):
        self.exp_1.archive()
        self.assertTrue(self.exp_1.is_archived())
        self.exp_1.unarchive()
        self.assertFalse(self.exp_1.is_archived())

    def test_set_winner(self):
        exp = Experiment('test-winner', ['1', '2'], redis=self.redis)
        exp.set_winner('1')
        self.assertTrue(exp.winner is not None)

        exp.set_winner('1')
        self.assertEqual(exp.winner.name, '1')

    def test_winner(self):
        exp = Experiment.find_or_create('test-get-winner', ['1', '2'], redis=self.redis)
        self.assertIsNone(exp.winner)

        exp.set_winner('1')
        self.assertEqual(exp.winner.name, '1')

    def test_reset_winner(self):
        exp = Experiment('show-something-reset-winner', self.alternatives, redis=self.redis)
        exp.save()
        exp.set_winner('yes')
        self.assertTrue(exp.winner is not None)
        self.assertEqual(exp.winner.name, 'yes')

        exp.reset_winner()
        self.assertIsNone(exp.winner)

    def test_winner_key(self):
        exp = Experiment.find_or_create('winner-key', ['win', 'lose'], redis=self.redis)
        self.assertEqual(exp._winner_key, "{0}:winner".format(exp.key()))

    def test_get_alternative(self):
        client = Client(10, redis=self.redis)

        exp = Experiment.find_or_create('archived-control', ['w', 'l'], redis=self.redis)
        exp.archive()

        # should return control on archived test with no winner
        alt = exp.get_alternative(client)
        self.assertEqual(alt.name, 'w')

        # should return current participation
        exp.unarchive()
        ### HACK TO SKIP WHIPLASH TESTS
        exp.random_sample = 1
        ### HACK TO SKIP WHIPLASH TESTS

        selected_for_client = exp.get_alternative(client)
        self.assertIn(selected_for_client.name, ['w', 'l'])

        # should check to see if client is participating and only return the same alt
        # unsure how to currently test since fakeredis obviously doesn't parse lua
        # most likely integration tests

    # See above note for the next 5 tests
    def _test_existing_alternative(self):
        pass

    def _test_has_converted_by_client(self):
        pass

    def _test_choose_alternative(self):
        pass

    def _test_random_choice(self):
        pass

    def _test_whiplash(self):
        pass

    def test_key(self):
        key = self.exp_1.key()
        self.assertEqual(key, 'sxp:e:show-something-awesome')

        key_2 = self.exp_2.key()
        self.assertEqual(key_2, 'sxp:e:dales-lagunitas')

        exp = Experiment('brews', ['mgd', 'bud-heavy'], redis=self.redis)
        key_3 = exp.key()
        self.assertEqual(key_3, 'sxp:e:brews')

    def test_find(self):
        exp = Experiment('crunches-situps', ['crunches', 'situps'], redis=self.redis)
        exp.save()

        with self.assertRaises(ValueError):
            Experiment.find('this-does-not-exist', redis=self.redis)

        try:
            Experiment.find('crunches-situps', redis=self.redis)
        except:
            self.fail('known exp not found')

    def test_find_or_create(self):
        # should throw a ValueError if alters are invalid
        with self.assertRaises(ValueError):
            Experiment.find_or_create('party-time', ['1'], redis=self.redis)

        with self.assertRaises(ValueError):
            Experiment.find_or_create('party-time', ['1', '*****'], redis=self.redis)

        # should create a -NEW- experiment if experiment has never been used
        with self.assertRaises(ValueError):
            Experiment.find('dance-dance', redis=self.redis)

    def test_all(self):
        # there are three created in setUp()
        all_of_them = Experiment.all(redis=self.redis)
        self.assertEqual(len(all_of_them), 3)

        exp_1 = Experiment('archive-this', ['archived', 'unarchive'], redis=self.redis)
        exp_1.save()

        all_again = Experiment.all(redis=self.redis)
        self.assertEqual(len(all_again), 4)

        exp_1.archive()
        all_archived = Experiment.all(redis=self.redis)
        self.assertEqual(len(all_archived), 3)

        all_with_archived = Experiment.all(exclude_archived=False, redis=self.redis)
        self.assertEqual(len(all_with_archived), 4)

        all_archived = Experiment.archived(redis=self.redis)
        self.assertEqual(len(all_archived), 1)

    def test_load_alternatives(self):
        exp = Experiment.find_or_create('load-alts-test', ['yes', 'no', 'call-me-maybe'], redis=self.redis)
        alts = Experiment.load_alternatives(exp.name, redis=self.redis)
        self.assertEqual(sorted(alts), sorted(['yes', 'no', 'call-me-maybe']))

    def test_differing_alternatives_fails(self):
        exp = Experiment.find_or_create('load-differing-alts', ['yes', 'zack', 'PBR'], redis=self.redis)
        alts = Experiment.load_alternatives(exp.name, redis=self.redis)
        self.assertEqual(sorted(alts), sorted(['PBR', 'yes', 'zack']))

        with self.assertRaises(ValueError):
            exp = Experiment.find_or_create('load-differing-alts', ['kyle', 'zack', 'PBR'], redis=self.redis)

    def _test_initialize_alternatives(self):
        # Should throw ValueError
        with self.assertRaises(ValueError):
            Experiment.initialize_alternatives('n', ['*'], redis=self.redis)

        # each item in list should be Alternative Instance
        alt_objs = Experiment.initialize_alternatives('n', ['1', '2', '3'])
        for alt in alt_objs:
            self.assertTrue(isinstance(alt, Alternative))
            self.assertTrue(alt.name in ['1', '2', '3'])

    def test_is_not_valid(self):
        not_valid = Experiment.is_valid(1)
        self.assertFalse(not_valid)

        not_valid = Experiment.is_valid(':123:name')
        self.assertFalse(not_valid)

        not_valid = Experiment.is_valid('_123name')
        self.assertFalse(not_valid)

        not_valid = Experiment.is_valid('&123name')
        self.assertFalse(not_valid)

    def test_valid_options(self):
        Experiment.find_or_create('red-white', ['red', 'white'], traffic_fraction=1, redis=self.redis)
        Experiment.find_or_create('red-white', ['red', 'white'], traffic_fraction=0, redis=self.redis)
        Experiment.find_or_create('red-white', ['red', 'white'], traffic_fraction=0.4, redis=self.redis)

    def test_invalid_traffic_fraction(self):
        with self.assertRaises(ValueError):
            Experiment.find_or_create('dist-2', ['dist', '2'], traffic_fraction=2, redis=self.redis)

        with self.assertRaises(ValueError):
            Experiment.find_or_create('dist-100', ['dist', '100'], traffic_fraction=101, redis=self.redis)

        with self.assertRaises(ValueError):
            Experiment.find_or_create('dist-100', ['dist', '100'], traffic_fraction="x", redis=self.redis)

    def test_valid_traffic_fractions_save(self):
        # test the hidden prop gets set
        exp = Experiment.find_or_create('dist-02', ['dist', '100'], traffic_fraction=0.02, redis=self.redis)
        self.assertEqual(exp._traffic_fraction, 0.02)

        exp = Experiment.find_or_create('dist-100', ['dist', '100'], traffic_fraction=0.4, redis=self.redis)
        self.assertEqual(exp._traffic_fraction, 0.40)

    # test is set in redis
    def test_traffic_fraction(self):
        exp = Experiment.find_or_create('d-test-10', ['d', 'c'], traffic_fraction=0.1, redis=self.redis)
        exp.save()
        self.assertEqual(exp.traffic_fraction, 0.1)

    def test_valid_kpi(self):
        ret = Experiment.validate_kpi('hello-jose')
        self.assertTrue(ret)
        ret = Experiment.validate_kpi('123')
        self.assertTrue(ret)
        ret = Experiment.validate_kpi('foreigner')
        self.assertTrue(ret)
        ret = Experiment.validate_kpi('boston')
        self.assertTrue(ret)
        ret = Experiment.validate_kpi('1_not-two-times-two-times')
        self.assertTrue(ret)

    def test_invalid_kpi(self):
        ret = Experiment.validate_kpi('!hello-jose')
        self.assertFalse(ret)
        ret = Experiment.validate_kpi('thunder storm')
        self.assertFalse(ret)
        ret = Experiment.validate_kpi('&!&&!&')
        self.assertFalse(ret)

    def test_set_kpi(self):
        exp = Experiment.find_or_create('multi-kpi', ['kpi', '123'], redis=self.redis)
        # We shouldn't beable to manually set a KPI. Only via web request
        with self.assertRaises(ValueError):
            exp.set_kpi('bananza')

        # simulate conversion via webrequest
        client = Client(100, redis=self.redis)
        # hack for disabling whiplash
        exp.random_sample = 1

        exp.get_alternative(client)
        exp.convert(client, None, 'bananza')

        exp2 = Experiment.find_or_create('multi-kpi', ['kpi', '123'], redis=self.redis)
        self.assertEqual(exp2.kpi, None)
        exp2.set_kpi('bananza')
        self.assertEqual(exp2.kpi, 'bananza')

    def test_add_kpi(self):
        exp = Experiment.find_or_create('multi-kpi-add', ['asdf', '999'], redis=self.redis)
        kpi = 'omg-pop'

        exp.add_kpi(kpi)
        key = "{0}:kpis".format(exp.key(include_kpi=False))
        self.assertIn(kpi, self.redis.smembers(key))
        exp.delete()

    def test_kpis(self):
        exp = Experiment.find_or_create('multi-kpi-add', ['asdf', '999'], redis=self.redis)
        kpis = ['omg-pop', 'zynga']

        exp.add_kpi(kpis[0])
        exp.add_kpi(kpis[1])
        ekpi = exp.kpis
        self.assertIn(kpis[0], ekpi)
        self.assertIn(kpis[1], ekpi)
        exp.delete()

########NEW FILE########
__FILENAME__ = server_logic_test
import unittest
from sixpack.server import is_robot


class TestServerLogic(unittest.TestCase):

    unit = True

    def test_is_robot(self):
        ret = is_robot('fetch')
        self.assertTrue(ret)

    def test_is_not_robot(self):
        ret = is_robot('Mozilla%2F5.0%20(Macintosh%3B%20Intel%20Mac%20OS%20X%2010_8_2)%20AppleWebKit%2F537.22%20(KHTML%2C%20like%20Gecko)%20Chrome%2F25.0.1364.45%20Safari%2F537.22')
        self.assertFalse(ret)

        ret = is_robot(None)
        self.assertFalse(ret)

########NEW FILE########
__FILENAME__ = server_test
import unittest
import json

from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from sixpack.server import create_app


class TestServer(unittest.TestCase):

    def setUp(self):
        # tried using fakeredis here but it barfed on scripts
        self.app = create_app()
        self.client = Client(self.app, BaseResponse)

    def test_base(self):
        self.assertEqual(200, self.client.get("/").status_code)

    def test_status(self):
        res = self.client.get("/_status")
        data = json.loads(res.data)
        self.assertEqual(200, res.status_code)
        self.assertTrue('status' in data)
        self.assertEqual('ok', data['status'])

    def test_404(self):
        res = self.client.get("/i-would-walk-five-thousand-miles")
        data = json.loads(res.data)
        self.assertEqual(404, res.status_code)
        self.assertTrue('message' in data)
        self.assertEqual('not found', data['message'])
        self.assertTrue('status' in data)
        self.assertEqual('failed', data['status'])

    def test_sans_callback(self):
        res = self.client.get("/participate?experiment=dummy&client_id=foo&alternatives=one&alternatives=two")
        self.assertEqual(200, res.status_code)
        self.assertEqual("application/json", dict(res.headers)["Content-Type"])
        self.assert_(res.data.startswith("{"))
        self.assert_(res.data.endswith("}"))

    def test_with_callback(self):
        res = self.client.get("/participate?experiment=dummy&client_id=foo&alternatives=one&alternatives=two&callback=seatgeek.cb")
        self.assertEqual(200, res.status_code)
        self.assertEqual("application/javascript", dict(res.headers)["Content-Type"])
        self.assert_(res.data.startswith("seatgeek.cb({"))
        self.assert_(res.data.endswith("})"))

    def test_with_bad_callback(self):
        # TODO error out here instead?
        res = self.client.get("/participate?experiment=dummy&client_id=foo&alternatives=one&alternatives=two&callback=alert();foo")
        self.assertEqual(200, res.status_code)
        self.assertEqual("application/json", dict(res.headers)["Content-Type"])
        self.assert_(res.data.startswith("{"))
        self.assert_(res.data.endswith("}"))

    def test_ok_participate(self):
        resp = self.client.get("/participate?experiment=dummy&client_id=foo&alternatives=one&alternatives=two")
        data = json.loads(resp.data)
        self.assertEqual(200, resp.status_code)
        self.assertTrue('alternative' in data)
        self.assertTrue('name' in data['alternative'])
        self.assertTrue('experiment' in data)
        self.assertTrue('name' in data['experiment'])
        self.assertTrue('client_id' in data)
        self.assertTrue('status' in data)
        self.assertEqual(data['status'], 'ok')

    def test_participate_useragent_filter(self):
        resp = self.client.get("/participate?experiment=dummy&client_id=foo&alternatives=one&alternatives=two&user_agent=fetch")
        data = json.loads(resp.data)
        self.assertEqual(200, resp.status_code)
        self.assertTrue('alternative' in data)
        self.assertTrue('experiment' in data)
        self.assertTrue('client_id' in data)
        self.assertTrue('status' in data)

    def test_convert_useragent_filter(self):
        resp = self.client.get("/convert?experiment=dummy&client_id=foo&user_agent=fetch")
        data = json.loads(resp.data)
        self.assertEqual(200, resp.status_code)
        self.assertTrue('status' in data)
        self.assertTrue('excluded' in data)
        self.assertEqual('true', data['excluded'])

    def test_convert(self):
        self.client.get("/participate?experiment=dummy&client_id=foo&alternatives=one&alternatives=two&callback=seatgeek.cb")
        resp = self.client.get("/convert?experiment=dummy&client_id=foo")
        data = json.loads(resp.data)
        self.assertEqual(200, resp.status_code)
        self.assertTrue('status' in data)
        self.assertEqual(data['status'], 'ok')
        self.assertTrue('alternative' in data)
        self.assertTrue('name' in data['alternative'])
        self.assertTrue('experiment' in data)
        self.assertTrue('name' in data['experiment'])
        self.assertTrue('client_id' in data)
        self.assertTrue('conversion' in data)
        self.assertTrue('value' in data['conversion'])
        self.assertTrue('kpi' in data['conversion'])
        self.assertEqual(data['conversion']['kpi'], None)

    def test_convert_with_kpi(self):
        self.client.get("/participate?experiment=dummy-kpi&client_id=foo&alternatives=one&alternatives=two")
        resp = self.client.get("/convert?experiment=dummy-kpi&client_id=foo&kpi=alligator")
        data = json.loads(resp.data)
        self.assertEqual(200, resp.status_code)
        self.assertTrue('status' in data)
        self.assertEqual(data['status'], 'ok')
        self.assertTrue('alternative' in data)
        self.assertTrue('name' in data['alternative'])
        self.assertTrue('experiment' in data)
        self.assertTrue('name' in data['experiment'])
        self.assertTrue('client_id' in data)
        self.assertTrue('conversion' in data)
        self.assertTrue('value' in data['conversion'])
        self.assertTrue('kpi' in data['conversion'])
        self.assertEqual(data['conversion']['kpi'], 'alligator')

    def test_convert_bad_kpi_failure(self):
        self.client.get("/participate?experiment=dummy-kpi&client_id=foo&alternatives=one&alternatives=two")
        resp = self.client.get("/convert?experiment=dummy-kpi&client_id=foo&kpi=&&^^!*(")
        data = json.loads(resp.data)
        self.assertEqual(400, resp.status_code)
        self.assertTrue('status' in data)
        self.assertEqual(data['message'], 'invalid kpi name')
        self.assertEqual(data['status'], 'failed')

    def test_convert_fail(self):
        resp = self.client.get("/convert?experiment=baz&client_id=bar")
        data = json.loads(resp.data)
        self.assertEqual(400, resp.status_code)
        self.assertTrue('status' in data)
        self.assertEqual(data['status'], 'failed')
        self.assertEqual(data['message'], 'experiment does not exist')

    def test_client_id(self):
        resp = self.client.get("/participate?experiment=dummy&alternatives=one&alternatives=two")
        data = json.loads(resp.data)
        self.assertEqual(400, resp.status_code)
        self.assertTrue('status' in data)
        self.assertEqual(data['status'], 'failed')
        self.assertEqual(data['message'], 'missing arguments')

########NEW FILE########
__FILENAME__ = utils_test
import unittest
from sixpack import utils


class TestServerLogic(unittest.TestCase):

    unit = True

    def test_number_to_percent(self):
        number = utils.number_to_percent(0.09)
        self.assertEqual(number, '9.00%')

        number = utils.number_to_percent(0.001)
        self.assertEqual(number, '0.10%')

    def test_number_format(self):
        number = utils.number_format(100)
        self.assertEqual(number, '100')

        number = utils.number_format(1000)
        self.assertEqual(number, '1,000')

        number = utils.number_format(1234567890)
        self.assertEqual(number, '1,234,567,890')

    def test_str_to_bool(self):
        self.assertTrue(utils.to_bool('y'))
        self.assertTrue(utils.to_bool('YES'))
        self.assertTrue(utils.to_bool('true'))
        self.assertTrue(utils.to_bool('TRUE'))
        self.assertTrue(utils.to_bool('Y'))
        self.assertFalse(utils.to_bool('rodger'))
        self.assertFalse(utils.to_bool('False'))
        self.assertFalse(utils.to_bool('FaLse'))
        self.assertFalse(utils.to_bool('no'))
        self.assertFalse(utils.to_bool('n'))

########NEW FILE########
__FILENAME__ = utils
import json
import re

import decorator
from redis import ConnectionError
from werkzeug.wrappers import Response


@decorator.decorator
def service_unavailable_on_connection_error(f, *args, **kwargs):
    try:
        return f(*args, **kwargs)
    except ConnectionError:
        return json_error({"message": "redis is not available"}, None, 503)


def json_error(resp, request, status=None):
    default = {'status': 'failed'}
    resp = dict(default.items() + resp.items())

    return _json_resp(resp, request, status)


def json_success(resp, request):
    default = {'status': 'ok'}
    resp = dict(default.items() + resp.items())

    return _json_resp(resp, request, 200)  # Always a 200 when success is called


def _json_resp(in_dict, request, status=None):
    headers = {'Content-Type': 'application/json'}
    data = json.dumps(in_dict)
    callback = request and request.args.get('callback')
    if callback and re.match("^\w[\w'\-\.]*$", callback):
        headers["Content-Type"] = "application/javascript"
        data = "%s(%s)" % (callback, data)

    return Response(data, status=status, headers=headers)


def number_to_percent(number, precision=2):
    return "%.2f%%" % round(number * 100, precision)


def number_format(number):
    return "{:,}".format(number)

def to_bool(val):
    return val.lower() in ['y', 'true', 'yes']

########NEW FILE########
__FILENAME__ = web
from flask import Flask
from flask import render_template, abort, request, url_for, redirect, jsonify, make_response
from flask.ext.seasurf import SeaSurf
from flask.ext.assets import Environment, Bundle
from flask_debugtoolbar import DebugToolbarExtension
from markdown import markdown

from . import __version__
from config import CONFIG as cfg
import db
from models import Experiment
from analysis import ExportExperiment
import utils

app = Flask(__name__)
csrf = SeaSurf(app)

js = Bundle('js/vendor/jquery.js', 'js/vendor/d3.js',
            'js/vendor/bootstrap.js', 'js/experiment.js', 'js/chart.js',
            'js/sixpack.js', 'js/vendor/underscore-min.js', 'js/vendor/spin.min.js',
            'js/vendor/waypoints.min.js', 'js/vendor/zeroclipboard.min.js',
            filters=['closure_js'],
            output="{0}/sixpack.js".format(cfg.get('asset_path', 'gen')))

css = Bundle('css/vendor/bootstrap.css',
             'css/vendor/bootstrap-responsive.css', 'css/sixpack.css',
             filters=['yui_css'],
             output="{0}/sixpack.css".format(cfg.get('asset_path', 'gen')))

assets = Environment(app)
assets.register('js_all', js)
assets.register('css_all', css)


@app.route('/_status')
@utils.service_unavailable_on_connection_error
def status():
    db.REDIS.ping()
    return utils.json_success({'version': __version__}, request)


@app.route("/")
def hello():
    experiments = Experiment.all(exclude_archived=True, redis=db.REDIS)
    experiments = [exp.name for exp in experiments]
    return render_template('dashboard.html', experiments=experiments, page='home')


@app.route('/archived')
def archived():
    experiments = Experiment.all(exclude_archived=False, redis=db.REDIS)
    experiments = [exp.name for exp in experiments if exp.is_archived()]
    return render_template('dashboard.html', experiments=experiments, page='archived')


@app.route('/experiments.json')
def experiment_list():
    experiments = Experiment.all(db.REDIS)
    period = determine_period()
    experiments = [simple_markdown(exp.objectify_by_period(period)) for exp in experiments]
    return jsonify({'experiments': experiments})


# Details for experiment
@app.route("/experiments/<experiment_name>/")
def details(experiment_name):
    experiment = find_or_404(experiment_name)
    return render_template('details.html', experiment=experiment)


@app.route("/experiments/<experiment_name>.json")
def json_details(experiment_name):
    experiment = find_or_404(experiment_name)
    period = determine_period()
    obj = simple_markdown(experiment.objectify_by_period(period))
    return jsonify(obj)


@app.route("/experiments/<experiment_name>/export", methods=['POST'])
def export(experiment_name):
    experiment = find_or_404(experiment_name)

    export = ExportExperiment(experiment=experiment)
    response = make_response(export())
    response.headers["Content-Type"] = "text/csv"
    # force a download with the content-disposition headers
    filename = "sixpack_export_{0}".format(experiment_name)
    response.headers["Content-Disposition"] = "attachment; filename={0}.csv".format(filename)

    return response


# Set winner for an experiment
@app.route("/experiments/<experiment_name>/winner/", methods=['POST'])
def set_winner(experiment_name):
    experiment = find_or_404(experiment_name)
    experiment.set_winner(request.form['alternative_name'])

    return redirect(url_for('details', experiment_name=experiment.name))


# Reset experiment
@app.route("/experiments/<experiment_name>/reset/", methods=['POST'])
def reset_experiment(experiment_name):
    experiment = find_or_404(experiment_name)
    experiment.reset()

    return redirect(url_for('details', experiment_name=experiment.name))


# Reset experiment winner
@app.route("/experiments/<experiment_name>/winner/reset/", methods=['POST'])
def reset_winner(experiment_name):
    experiment = find_or_404(experiment_name)
    experiment.reset_winner()

    return redirect(url_for('details', experiment_name=experiment.name))


# Delete experiment
@app.route("/experiments/<experiment_name>/delete/", methods=['POST'])
def delete_experiment(experiment_name):
    experiment = find_or_404(experiment_name)
    experiment.delete()

    return redirect(url_for('hello'))


# Archive experiment
@app.route("/experiments/<experiment_name>/archive", methods=['POST'])
def toggle_experiment_archive(experiment_name):
    experiment = find_or_404(experiment_name)
    if experiment.is_archived():
        experiment.unarchive()
    else:
        experiment.archive()

    return redirect(url_for('details', experiment_name=experiment.name))


@app.route("/experiments/<experiment_name>/description", methods=['POST'])
def update_experiment_description(experiment_name):
    experiment = find_or_404(experiment_name)

    experiment.update_description(request.form['description'])

    return redirect(url_for('details', experiment_name=experiment.name))


@app.route('/favicon.ico')
def favicon():
    return ''


@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500


def find_or_404(experiment_name):
    try:
        exp = Experiment.find(experiment_name, db.REDIS)
        if request.args.get('kpi'):
            exp.set_kpi(request.args.get('kpi'))
        return exp
    except ValueError:
        abort(404)


def determine_period():
    period = request.args.get('period', 'day')
    if period not in ['day', 'week', 'month', 'year']:
        err = {'error': 'invalid argument: {0}'.format(period), 'status': 400}
        abort(400, jsonify(err))
    return period


def simple_markdown(experiment):
    description = experiment['description']
    if description and description != '':
        experiment['pretty_description'] = markdown(description)
    return experiment


app.secret_key = cfg.get('secret_key')
app.jinja_env.filters['number_to_percent'] = utils.number_to_percent
app.jinja_env.filters['number_format'] = utils.number_format
toolbar = DebugToolbarExtension(app)


def start(environ, start_response):
    return app(environ, start_response)

########NEW FILE########
