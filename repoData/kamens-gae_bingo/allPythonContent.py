__FILENAME__ = api
import copy
import itertools
import logging
import os

from google.appengine.ext.webapp import RequestHandler

from .gae_bingo import choose_alternative, delete_experiment, resume_experiment
from .gae_bingo import archive_experiment, modulo_choose, ExperimentController
from .models import _GAEBingoExperimentNotes
from .cache import BingoCache
from .stats import describe_result_in_words
from .config import config
from .jsonify import jsonify
from .plots import get_experiment_timeline_data
from .identity import can_control_experiments, identity
import instance_cache
import request_cache

class GAEBingoAPIRequestHandler(RequestHandler):
    """Request handler for all GAE/Bingo API requests.

    Each individual GAE/Bingo API request is either interacting with live data
    or archived data. Live and archived data are stored and cached differently,
    and this request handler can load each set of data as specified by the
    request.
    """

    def is_requesting_archives(self):
        """True if request is interacting with archived data."""
        return self.request.get("archives") == "1"

    def flush_in_app_caches(self):
        """Flush in-app request and instance caches of gae/bingo state."""
        request_cache.flush_request_cache()
        instance_cache.flush()

    def request_bingo_cache(self):
        """Return BingoCache object for live/archived data, as appropriate.

        A BingoCache obect acts as the datastore for experiments and
        alternatives for the length of an API request. If loaded from archives,
        the experiments will be inactive and read-only unless permanently
        deleting them.
        """
        # Flush in-app caches so we load the latest shared experiment state
        self.flush_in_app_caches()

        if self.is_requesting_archives():
            return BingoCache.load_from_datastore(archives=True)
        else:
            return BingoCache.get()


def experiments_from_cache(bingo_cache, requesting_archives):
    """Retrieve experiments data for consumption via the API.

    Arguments:
        bingo_cache - the cache where the data is to be retrieved from
        requesting_archives - whether or not archived experiments should be
            returned or non-archived experiments
    """
    experiment_results = {}

    for canonical_name in bingo_cache.experiment_names_by_canonical_name:
        experiments, alternative_lists = bingo_cache.experiments_and_alternatives_from_canonical_name(canonical_name)

        if not experiments or not alternative_lists:
            continue

        for experiment, alternatives in itertools.izip(
                experiments, alternative_lists):

            # Combine related experiments and alternatives into a single
            # canonical experiment for response
            if experiment.canonical_name not in experiment_results:
                experiment.alternatives = alternatives
                experiment_results[experiment.canonical_name] = experiment

    # Sort by status primarily, then name or date
    results = experiment_results.values()

    if requesting_archives:
        results.sort(key=lambda ex: ex.dt_started, reverse=True)
    else:
        results.sort(key=lambda ex: ex.pretty_canonical_name)

    results.sort(key=lambda ex: ex.live, reverse=True)
    return results


class Experiments(GAEBingoAPIRequestHandler):

    def get(self):

        if not can_control_experiments():
            return

        bingo_cache = self.request_bingo_cache()
        results = experiments_from_cache(
                bingo_cache, self.is_requesting_archives())
        context = { "experiment_results": results }

        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(jsonify(context))

class ExperimentSummary(GAEBingoAPIRequestHandler):

    def get(self):

        if not can_control_experiments():
            return

        bingo_cache = self.request_bingo_cache()
        canonical_name = self.request.get("canonical_name")
        experiments, alternatives = bingo_cache.experiments_and_alternatives_from_canonical_name(canonical_name)

        if not experiments:
            raise Exception("No experiments matching canonical name: %s" % canonical_name)

        context = {}
        prev = None
        prev_dict = {}

        experiment_notes = _GAEBingoExperimentNotes.get_for_experiment(experiments[0])
        if experiment_notes:
            context["notes"] = experiment_notes.notes
            context["emotions"] = experiment_notes.emotions

        experiments = sorted(experiments, key=lambda experiment: experiment.conversion_name)
        for experiment in experiments:
            if "canonical_name" not in context:
                context["canonical_name"] = experiment.canonical_name

            if "live" not in context:
                context["live"] = experiment.live

            if "multiple_experiments" not in context:
                context["multiple_experiments"] = len(experiments) > 1

            if "experiments" not in context:
                context["experiments"] = []

            exp_dict = {
                "conversion_name": experiment.conversion_name,
                "experiment_name": experiment.name,
                "pretty_conversion_name": experiment.pretty_conversion_name,
                "archived": experiment.archived,
            }

            if prev and prev.conversion_group == experiment.conversion_group:
                if "conversion_group" not in prev_dict:
                    prev_dict["start_conversion_group"] = True
                    prev_dict["conversion_group"] = prev.conversion_group
                exp_dict["conversion_group"] = experiment.conversion_group
            else:
                if "conversion_group" in prev_dict:
                    prev_dict["end_conversion_group"] = True

            context["experiments"].append(exp_dict)
            prev_dict = exp_dict
            prev = experiment

        if "conversion_group" in prev_dict:
            prev_dict["end_conversion_group"] = True

        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(jsonify(context))

class ExperimentConversions(GAEBingoAPIRequestHandler):

    def get(self):
        if not can_control_experiments():
            return

        bingo_cache = self.request_bingo_cache()
        expt_name = self.request.get("experiment_name")

        data = self.get_context(bingo_cache, expt_name)

        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(jsonify(data))

    @staticmethod
    def get_context(bingo_cache, expt_name):
        expt = bingo_cache.get_experiment(expt_name)
        alts = bingo_cache.get_alternatives(expt_name)
        if not expt or not alts:
            raise Exception("No experiment matching name: %s" % expt_name)

        short_circuit_number = -1

        # Make a deep copy of these alternatives so we can modify their
        # participants and conversion counts below for an up-to-date dashboard
        # without impacting counts in shared memory.
        alts = copy.deepcopy(alts)
        for alt in alts:
            if not expt.live and expt.short_circuit_content == alt.content:
                short_circuit_number = alt.number

            # Load the latest alternative counts into these copies of
            # alternative models for up-to-date dashboard counts.
            alt.participants = alt.latest_participants_count()
            alt.conversions = alt.latest_conversions_count()

        return {
            "canonical_name": expt.canonical_name,
            "hashable_name": expt.hashable_name,
            "live": expt.live,
            "total_participants": sum(a.participants for a in alts),
            "total_conversions": sum(a.conversions for a in alts),
            "alternatives": alts,
            "significance_test_results": describe_result_in_words(alts),
            "y_axis_title": expt.y_axis_title,
            "timeline_series": get_experiment_timeline_data(expt, alts),
            "short_circuit_number": short_circuit_number
        }

class ControlExperiment(GAEBingoAPIRequestHandler):

    def post(self):
        if not can_control_experiments():
            return

        canonical_name = self.request.get("canonical_name")
        action = self.request.get("action")

        if self.is_requesting_archives() and action != "delete":
            # Can only delete archived experiments
            return

        if not action or not canonical_name:
            return

        # Flush the in app caches to make sure we're operating on the most
        # recent experiments.
        self.flush_in_app_caches()

        with ExperimentController():
            if action == "choose_alternative":
                choose_alternative(
                        canonical_name,
                        int(self.request.get("alternative_number")))
            elif action == "delete":
                delete_experiment(
                        canonical_name,
                        self.is_requesting_archives())
            elif action == "resume":
                resume_experiment(canonical_name)
            elif action == "archive":
                archive_experiment(canonical_name)

        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(jsonify(True))

class NoteExperiment(GAEBingoAPIRequestHandler):
    """Request handler for saving experiments' notes and list of emotions."""

    def post(self):

        if not can_control_experiments():
            return

        bingo_cache = self.request_bingo_cache()
        canonical_name = self.request.get("canonical_name")
        experiments, alternative_lists = bingo_cache.experiments_and_alternatives_from_canonical_name(canonical_name)

        if not experiments:
            raise Exception("No experiments matching name: %s" % canonical_name)

        notes = self.request.get("notes")
        emotions = self.request.get_all("emotions[]")

        _GAEBingoExperimentNotes.save(experiments[0], notes, emotions)

        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(jsonify(True))

class Alternatives(GAEBingoAPIRequestHandler):

    def get(self):

        if not can_control_experiments():
            return

        query = self.request.get("query")
        if query:
            id = config.retrieve_identity(query)
        else:
            id = identity()

        if not id:
            raise Exception("Error getting identity for query: %s" % str(query))

        bingo_cache = self.request_bingo_cache()

        chosen_alternatives = {}

        for experiment_name in bingo_cache.experiments:
            experiment = bingo_cache.get_experiment(experiment_name)

            if experiment.canonical_name not in chosen_alternatives:
                alternatives = bingo_cache.get_alternatives(experiment_name)
                alternative = modulo_choose(experiment, alternatives, id)
                chosen_alternatives[experiment.canonical_name] = str(alternative.content)

        context = {
            "identity": id,
            "alternatives": chosen_alternatives,
        }

        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(jsonify(context))

########NEW FILE########
__FILENAME__ = blotter
"""Blotter is a bingo callback for use from the client side 

GETs allow you to check the user's experiment status from within js while 
POSTs allow you to score conversions for a given test

"""
import os

from google.appengine.ext.webapp import RequestHandler

from .gae_bingo import bingo, ab_test
from .cache import BingoCache
from .identity import can_control_experiments

# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

class AB_Test(RequestHandler):
    """request user alternative/state for an experiment by passing 
    { canonical_name : "experiment_name" }
    
    successful requests return 200 and a json object { "experiment_name" : "state" }
    where state is a jsonified version of the user's state in the experiment
    
    if a user can_control_experiments, requests may create experiments on the server
    similar to calling ab_test directly. You should pass in:
        { 
            "canonical_name": <string>,
            "alternative_params": <json_obj | json_list>,
            "conversion_name": <json_list>
        }
    *q.v. gae_bingo.ab_test*
    
    Creating a new experiment will return a 201 and the 
    jsonified state of the user calling ab_test
    
    Simply querying an experiment successfully will return a 200
    
    failed requests return 404 if the experiment is not found and
    return a 400 if the params are passed incorrectly
    """
    
    def post(self):
        
        experiment_name = self.request.get("canonical_name", None)
        alternative_params = self.request.get("alternative_params", None)
        
        if alternative_params:
            alternative_params = json.loads(alternative_params)
        
        bingo_cache = BingoCache.get()
        conversion_name = self.request.get("conversion_name", None)
        
        if conversion_name:
            conversion_name = json.loads(conversion_name)
        
        self.response.headers['Content-Type'] = 'text/json'
        
        status = 200
        response = None
        
        if experiment_name:
            
            if experiment_name not in bingo_cache.experiments:
                
                if can_control_experiments():
                    # create the given ab_test with passed params, etc
                    response = ab_test(experiment_name, alternative_params, conversion_name)
                    status = 201
                
                else:
                    # experiment not found (and not being created)
                    status = 404
            
            # return status for experiment (200 implicit)
            else:
                response = ab_test(experiment_name)
        
        else:
            # no params passed, sorry broheim
            status = 400
            response = "hc svnt dracones"
        
        
        self.response.set_status(status)
        response = json.dumps(response)
        if response is not 'null':
            self.response.out.write(response)
        return



class Bingo(RequestHandler):
    """post a conversion to gae_bingo by passing
    { convert : "conversion_name_1\tconversion_name_2\t..." }
    
    successful conversions return HTTP 204
    
    failed conversions return a 404 (i.e. experiment for any conversion name not
    found in reverse-lookup)
    
    no params returns a 400 error
    """

    def post(self):
        
        bingo_cache = BingoCache.get()
        
        conversion_names = self.request.get("convert", '""').split("\t")

        self.response.headers['Content-Type'] = 'text/json'

        found_experiments = any(
                bingo_cache.get_experiment_names_by_conversion_name(name)
                for name in conversion_names)

        status = 200
        response = None
        
        if conversion_names:
            
            if found_experiments:
                # send null message and score the conversion
                status = 204
                bingo(conversion_names)
            
            else:
                # send error, conversion not found
                status = 404
        
        else:
            # no luck, compadre
            status = 400
            response = "hc svnt dracones"
        
        self.response.set_status(status)
        if response:
            self.response.out.write(json.dumps(response))
        

########NEW FILE########
__FILENAME__ = cache
"""Tools for caching the state of all bingo experiments.

There are two main objects cached by bingo: BingoCache and BingoIdentityCache.

BingoCache caches the state of all Experiment and Alternative models, and it is
shared among all users.

BingoIdentityCache caches individual users' participation and conversion
histories, and one exists for every user.

Each of them are cached at multiple layers, summarized below:
    BingoCache itself is cached in:
        request_cache (so we only retrieve it once per request)
        instance_cache (so we only load it from memcache once every minute)
        memcache (when instance_cache is empty, we load from memcache)
        datastore (if memcache is empty, we load all Experiment/Alternative
            models from the datastore)

    BingoIdentityCaches are cached in:
        request_cache (so we only retrieve it once per request)
        memcache (when a user becomes active, we hope to keep their bingo
            history in memcache)
        datastore (whenever an individual user's history isn't in memcache, we
            load it from a cached-in-datastore model, _GAEBingoIdentityRecord)

    This sequence of cache loading and expiration is handled by CacheLayers.
"""

import hashlib
import logging
import zlib

from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.api import memcache
from google.appengine.datastore import entity_pb
from google.appengine.ext.webapp import RequestHandler

from .models import _GAEBingoExperiment, _GAEBingoAlternative, _GAEBingoIdentityRecord, _GAEBingoSnapshotLog
from config import config
from identity import identity
import instance_cache
import pickle_util
import request_cache
import synchronized_counter


NUM_IDENTITY_BUCKETS = 51


class CacheLayers(object):
    """Gets and sets BingoCache/BingoIdentityCaches in multiple cache layers.

    BingoCache and BingoIdentityCache use CacheLayers.get to load themselves.

    Since these objects are cached in multiple layers (request cache, instance
    cache, memcache, and the datastore), CacheLayers handles the logic for
    loading these objects on each request.

    Each request loads both the BingoCache (a collection of experiments and
    alternatives) and the current user's BingoIdentityCache (a collection of
    current user's participation in various experiments). BingoCache's state
    can be safely shared among multiple users.

    The loading and caching logic works like this:

        1) Prefetch both BingoCache and BingoIdentityCache from memcache.

            1a) If BingoCache is already in the current instance's instance
            cache and the instance cache hasn't expired (1-minute expiry), then
            only BingoIdentityCache will be loaded from memcache.

        2) If either cache is still missing, load them from the datastore. Both
            BingoCache and BingoIdentityCache implement their own
            load_from_datastore methods.

        3) Store both BingoCache and BingoIdentityCache in the request cache so
        we don't have to look them up again for the rest of the request.

            3a) Store BingoCache in the instance cache with a 1-minute expiry
            so it doesn't need to be loaded from memcache again for a bit.

    Note: The use of instance caching for BingoCache, even with a 1-min expiry,
    means that sometimes when controlling a bingo experiment (say, by choosing
    a specific alternative for all users), old instances won't see the new
    state of the experiment until the cache expires. This means some users may
    experience "flopping" back and forth between two versions of an experiment
    when, say, an alternative is chosen by the gae/bingo admin control panel
    and they issue multiple requests which are sent to App Engine instances w/
    different cached states. We consider this an acceptable tradeoff, for now.

    TODO(kamens): improve the above 1-minute version "flopping" if necessary.
    """

    INSTANCE_SECONDS = 60  # number of secs BingoCache stays in instance cache

    @staticmethod
    def fill_request_cache():
        """Load BingoCache/BingoIdentityCache from instance cache/memcache.

        This loads the shared BingoCache and the individual BingoIdentityCache
        for the current request's bingo identity and stores them both in the
        request cache.
        """
        if not request_cache.cache.get("bingo_request_cache_filled"):

            # Assume that we're going to grab both BingoCache and
            # BingoIdentityCache from memcache
            memcache_keys = [
                BingoCache.CACHE_KEY,
                BingoIdentityCache.key_for_identity(identity())
            ]

            # Try to grab BingoCache from instance cache
            bingo_instance = instance_cache.get(BingoCache.CACHE_KEY)
            if bingo_instance:
                # If successful, use instance cached version...
                request_cache.cache[BingoCache.CACHE_KEY] = bingo_instance
                # ...and don't load BingoCache from memcache
                memcache_keys.remove(BingoCache.CACHE_KEY)

            # Load necessary caches from memcache
            dict_memcache = memcache.get_multi(memcache_keys)

            # Decompress BingoCache if we loaded it from memcache
            if BingoCache.CACHE_KEY in dict_memcache:
                dict_memcache[BingoCache.CACHE_KEY] = CacheLayers.decompress(
                        dict_memcache[BingoCache.CACHE_KEY])

            # Update request cache with values loaded from memcache
            request_cache.cache.update(dict_memcache)

            if not bingo_instance:
                # And if BingoCache wasn't in the instance cache already, store
                # it with a 1-minute expiry
                instance_cache.set(BingoCache.CACHE_KEY,
                        request_cache.cache.get(BingoCache.CACHE_KEY),
                        expiry=CacheLayers.INSTANCE_SECONDS)

            request_cache.cache["bingo_request_cache_filled"] = True

    @staticmethod
    def compress(value):
        """Compress value so it'll fit in a single memcache value."""
        pickled = pickle_util.dump(value)
        return zlib.compress(pickled)

    @staticmethod
    def decompress(data):
        """Decompress value from its compressed memcache state."""
        pickled = zlib.decompress(data)
        return pickle_util.load(pickled)

    @staticmethod
    def set(key, value):
        """Set value in instance cache and a compressed version in memcache.
        
        BingoCache is always only stored in instance cache for up to 1 minute.
        """
        instance_cache.set(key, value, expiry=CacheLayers.INSTANCE_SECONDS)
        memcache.set(key, CacheLayers.compress(value))

        logging.info("Set BingoCache in instance cache and memcache")

    @staticmethod
    def get(key, fxn_load):
        """Load BingoCache or BingoIdentityCache into request cache.

        This will first try to prefetch the expected entities from memcache.

        If the requested BingoCache or BingoIdentityCache key still isn't in
        the current request cache after prefetching, load the key's value from
        the datastore using the passed-in loader function and update the
        current request cache.

        Args:
            key: cache key of BingoCache or specific user's BingoIdentityCache
            fxn_load: function to run that loads desired cache in the event of
                a memcache and instance cache miss during prefetch.
        """
        CacheLayers.fill_request_cache()

        if not request_cache.cache.get(key):
            request_cache.cache[key] = fxn_load()

        return request_cache.cache[key]


class BingoCache(object):
    """Stores all shared bingo experiment and alternative data."""
    CACHE_KEY = "_gae_bingo_compressed_cache"

    @staticmethod
    def get():
        return CacheLayers.get(BingoCache.CACHE_KEY,
                BingoCache.load_from_datastore)

    def __init__(self):
        self.dirty = False
        self.storage_disabled = False # True if loading archives that shouldn't be cached

        self.experiments = {} # Protobuf version of experiments for extremely fast (de)serialization
        self.experiment_models = {} # Deserialized experiment models

        self.alternatives = {} # Protobuf version of alternatives for extremely fast (de)serialization
        self.alternative_models = {} # Deserialized alternative models

        self.experiment_names_by_conversion_name = {} # Mapping of conversion names to experiment names
        self.experiment_names_by_canonical_name = {} # Mapping of canonical names to experiment names

    def store_if_dirty(self):
        # Only write cache if a change has been made
        if getattr(self, "storage_disabled", False) or not self.dirty:
            return

        # Wipe out deserialized models before serialization for speed
        self.experiment_models = {}
        self.alternative_models = {}

        # No longer dirty
        self.dirty = False

        CacheLayers.set(self.CACHE_KEY, self)

    def persist_to_datastore(self):
        """Persist current state of experiment and alternative models.

        This persists the entire BingoCache state to the datastore. Individual
        participants/conversions sums might be slightly out-of-date during any
        given persist, but hopefully not by much. This can be caused by
        memcache being cleared at unwanted times between a participant or
        conversion count increment and a persist.
        TODO(kamens): make persistence not rely on memcache so heavily.

        This persistence should be run constantly in the background via chained
        task queues.
        """

        # Start putting the experiments asynchronously.
        experiments_to_put = []
        for experiment_name in self.experiments:
            experiment_model = self.get_experiment(experiment_name)
            experiments_to_put.append(experiment_model)
        async_experiments = db.put_async(experiments_to_put)

        # Fetch all current counts available in memcache...
        counter_keys = []
        for experiment_name in self.experiments:
            experiment_model = self.get_experiment(experiment_name)
            counter_keys.append(experiment_model.participants_key)
            counter_keys.append(experiment_model.conversions_key)

        # ...and when we grab the current counts, reset the currently
        # accumulating counters at the same time.
        count_results = synchronized_counter.SynchronizedCounter.pop_counters(
                counter_keys)

        # Now add the latest accumulating counters to each alternative.
        alternatives_to_put = []
        for experiment_name in self.alternatives:

            experiment_model = self.get_experiment(experiment_name)
            alternative_models = self.get_alternatives(experiment_name)
            participants = count_results[experiment_model.participants_key]
            conversions = count_results[experiment_model.conversions_key]

            for alternative_model in alternative_models:

                # When persisting to datastore, we want to update with the most
                # recent accumulated counter from memcache.
                if alternative_model.number < len(participants):
                    delta_participants = participants[alternative_model.number]
                    alternative_model.participants += delta_participants

                if alternative_model.number < len(conversions):
                    delta_conversions = conversions[alternative_model.number]
                    alternative_model.conversions += delta_conversions

                alternatives_to_put.append(alternative_model)
                self.update_alternative(alternative_model)

        # When periodically persisting to datastore, first make sure memcache
        # has relatively up-to-date participant/conversion counts for each
        # alternative.
        self.dirty = True
        self.store_if_dirty()

        # Once memcache is done, put alternatives.
        async_alternatives = db.put_async(alternatives_to_put)

        async_experiments.get_result()
        async_alternatives.get_result()

    def log_cache_snapshot(self):

        # Log current data on live experiments to the datastore
        log_entries = []

        for experiment_name in self.experiments:
            experiment_model = self.get_experiment(experiment_name)
            if experiment_model and experiment_model.live:
                log_entries += self.log_experiment_snapshot(experiment_model)

        db.put(log_entries)

    def log_experiment_snapshot(self, experiment_model):

        log_entries = []

        alternative_models = self.get_alternatives(experiment_model.name)
        for alternative_model in alternative_models:
            # When logging, we want to store the most recent value we've got
            log_entry = _GAEBingoSnapshotLog(parent=experiment_model, alternative_number=alternative_model.number, conversions=alternative_model.latest_conversions_count(), participants=alternative_model.latest_participants_count())
            log_entries.append(log_entry)

        return log_entries

    @staticmethod
    def load_from_datastore(archives=False):
        """Load BingoCache from the datastore, using archives if specified."""

        # This shouldn't happen often (should only happen when memcache has
        # been completely evicted), but we still want to be as fast as
        # possible.

        bingo_cache = BingoCache()

        if archives:
            # Disable cache writes if loading from archives
            bingo_cache.storage_disabled = True

        experiment_dict = {}
        alternatives_dict = {}

        # Kick both of these off w/ run() so they'll prefetch asynchronously
        experiments = _GAEBingoExperiment.all().filter(
                "archived =", archives).run(batch_size=400)
        alternatives = _GAEBingoAlternative.all().filter(
                "archived =", archives).run(batch_size=400)

        for experiment in experiments:
            experiment_dict[experiment.name] = experiment

        alternatives = sorted(list(alternatives), key=lambda alt: alt.number)

        for alternative in alternatives:
            if alternative.experiment_name not in alternatives_dict:
                alternatives_dict[alternative.experiment_name] = []
            alternatives_dict[alternative.experiment_name].append(alternative)

        for experiment_name in experiment_dict:
            ex, alts = (experiment_dict.get(experiment_name),
                        alternatives_dict.get(experiment_name))
            if ex and alts:
                bingo_cache.add_experiment(ex, alts)

        # Immediately store in memcache as soon as possible after loading from
        # datastore to minimize # of datastore loads
        bingo_cache.store_if_dirty()

        return bingo_cache

    def add_experiment(self, experiment, alternatives):

        if not experiment or not alternatives:
            raise Exception("Cannot add empty experiment or empty alternatives to BingoCache")

        self.experiment_models[experiment.name] = experiment
        self.experiments[experiment.name] = db.model_to_protobuf(experiment).Encode()

        if not experiment.conversion_name in self.experiment_names_by_conversion_name:
            self.experiment_names_by_conversion_name[experiment.conversion_name] = []
        self.experiment_names_by_conversion_name[experiment.conversion_name].append(experiment.name)

        if not experiment.canonical_name in self.experiment_names_by_canonical_name:
            self.experiment_names_by_canonical_name[experiment.canonical_name] = []
        self.experiment_names_by_canonical_name[experiment.canonical_name].append(experiment.name)

        for alternative in alternatives:
            self.update_alternative(alternative)

        self.dirty = True

    def update_experiment(self, experiment):
        self.experiment_models[experiment.name] = experiment
        self.experiments[experiment.name] = db.model_to_protobuf(experiment).Encode()

        self.dirty = True

    def update_alternative(self, alternative):
        if not alternative.experiment_name in self.alternatives:
            self.alternatives[alternative.experiment_name] = {}

        self.alternatives[alternative.experiment_name][alternative.number] = db.model_to_protobuf(alternative).Encode()

        # Clear out alternative models cache so they'll be re-grabbed w/ next .get_alternatives
        if alternative.experiment_name in self.alternative_models:
            del self.alternative_models[alternative.experiment_name]

        self.dirty = True

    def remove_from_cache(self, experiment):
        # Remove from current cache
        if experiment.name in self.experiments:
            del self.experiments[experiment.name]

        if experiment.name in self.experiment_models:
            del self.experiment_models[experiment.name]

        if experiment.name in self.alternatives:
            del self.alternatives[experiment.name]

        if experiment.name in self.alternative_models:
            del self.alternative_models[experiment.name]

        if experiment.conversion_name in self.experiment_names_by_conversion_name:
            self.experiment_names_by_conversion_name[experiment.conversion_name].remove(experiment.name)

        if experiment.canonical_name in self.experiment_names_by_canonical_name:
            self.experiment_names_by_canonical_name[experiment.canonical_name].remove(experiment.name)

        self.dirty = True

        # Immediately store in memcache as soon as possible after deleting from datastore
        self.store_if_dirty()

    @db.transactional(xg=True)
    def delete_experiment_and_alternatives(self, experiment):
        """Permanently delete specified experiment and all alternatives."""
        if not experiment:
            return

        # First delete from datastore
        experiment.delete()
        experiment.reset_counters()

        for alternative in self.get_alternatives(experiment.name):
            alternative.delete()

        self.remove_from_cache(experiment)

    @db.transactional(xg=True)
    def archive_experiment_and_alternatives(self, experiment):
        """Permanently archive specified experiment and all alternatives.

        Archiving an experiment maintains its visibility for historical
        purposes, but it will no longer be loaded into the cached list of
        active experiments.

        Args:
            experiment: experiment entity to be archived.
        """
        if not experiment:
            return

        experiment.archived = True
        experiment.live = False
        experiment.put()

        alts = self.get_alternatives(experiment.name)
        for alternative in alts:
            alternative.archived = True
            alternative.live = False

        db.put(alts)

        self.remove_from_cache(experiment)

    def experiments_and_alternatives_from_canonical_name(self, canonical_name):
        experiment_names = self.get_experiment_names_by_canonical_name(canonical_name)

        return [self.get_experiment(experiment_name) for experiment_name in experiment_names], \
                [self.get_alternatives(experiment_name) for experiment_name in experiment_names]

    def get_experiment(self, experiment_name):
        if experiment_name not in self.experiment_models:
            if experiment_name in self.experiments:
                self.experiment_models[experiment_name] = db.model_from_protobuf(entity_pb.EntityProto(self.experiments[experiment_name]))

        return self.experiment_models.get(experiment_name)

    def get_alternatives(self, experiment_name):
        if experiment_name not in self.alternative_models:
            if experiment_name in self.alternatives:
                self.alternative_models[experiment_name] = []
                for alternative_number in self.alternatives[experiment_name]:
                    self.alternative_models[experiment_name].append(db.model_from_protobuf(entity_pb.EntityProto(self.alternatives[experiment_name][alternative_number])))

        return self.alternative_models.get(experiment_name) or []

    def get_experiment_names_by_conversion_name(self, conversion_name):
        return self.experiment_names_by_conversion_name.get(conversion_name) or []

    def get_experiment_names_by_canonical_name(self, canonical_name):
        return sorted(self.experiment_names_by_canonical_name.get(canonical_name) or [])


class BingoIdentityCache(object):
    """Stores conversion and participation data in tests for a bingo identity.

    This is stored in several layers of caches, including memcache. It is
    persisted using _GAEBingoIdentityRecord.
    """
    CACHE_KEY = "_gae_bingo_identity_cache:%s"

    @staticmethod
    def key_for_identity(ident):
        return BingoIdentityCache.CACHE_KEY % ident

    @staticmethod
    def get(identity_val=None):
        key = BingoIdentityCache.key_for_identity(identity(identity_val))
        return CacheLayers.get(key,
                lambda: BingoIdentityCache.load_from_datastore(identity_val))

    def store_for_identity_if_dirty(self, ident):
        if not self.dirty:
            return

        # No longer dirty
        self.dirty = False

        # memcache.set_async isn't exposed; make a Client so we can use it
        client = memcache.Client()
        future = client.set_multi_async(
            {BingoIdentityCache.key_for_identity(ident): self})

        # Always fire off a task queue to persist bingo identity cache
        # since there's no cron job persisting these objects like BingoCache.
        self.persist_to_datastore(ident)
        # TODO(alpert): If persist_to_datastore has more than 50 identities and
        # creates a deferred task AND that task runs before the above memcache
        # set finishes then we could lose a tiny bit of data for a user, but
        # that's extremely unlikely to happen.

        future.get_result()

    def persist_to_datastore(self, ident):

        # Add the memcache value to a memcache bucket which
        # will be persisted to the datastore when it overflows
        # or when the periodic cron job is run
        sig = hashlib.md5(str(ident)).hexdigest()
        sig_num = int(sig, base=16)
        bucket = sig_num % NUM_IDENTITY_BUCKETS
        key = "_gae_bingo_identity_bucket:%s" % bucket

        list_identities = memcache.get(key) or []
        list_identities.append(ident)

        if len(list_identities) > 50:

            # If over 50 identities are waiting for persistent storage, 
            # go ahead and kick off a deferred task to do so
            # in case it'll be a while before the cron job runs.
            deferred.defer(persist_gae_bingo_identity_records, list_identities, _queue=config.QUEUE_NAME)

            # There are race conditions here such that we could miss persistence
            # of some identities, but that's not a big deal as long as
            # there is no statistical correlation b/w the experiment and those
            # being lost.
            memcache.set(key, [])

        else:

            memcache.set(key, list_identities)

    @staticmethod
    def persist_buckets_to_datastore():
        # Persist all memcache buckets to datastore
        dict_buckets = memcache.get_multi(["_gae_bingo_identity_bucket:%s" % bucket for bucket in range(0, NUM_IDENTITY_BUCKETS)])

        for key in dict_buckets:
            if len(dict_buckets[key]) > 0:
                deferred.defer(persist_gae_bingo_identity_records, dict_buckets[key], _queue=config.QUEUE_NAME)
                memcache.set(key, [])

    @staticmethod
    def load_from_datastore(identity_val=None):
        ident = identity(identity_val)
        bingo_identity_cache = _GAEBingoIdentityRecord.load(ident)

        if bingo_identity_cache:
            bingo_identity_cache.purge()
            bingo_identity_cache.dirty = True
            bingo_identity_cache.store_for_identity_if_dirty(ident)
        else:
            bingo_identity_cache = BingoIdentityCache()

        return bingo_identity_cache

    def __init__(self):
        self.dirty = False

        self.participating_tests = [] # List of test names currently participating in
        self.converted_tests = {} # Dict of test names:number of times user has successfully converted

    def purge(self):
        bingo_cache = BingoCache.get()

        for participating_test in self.participating_tests:
            if not participating_test in bingo_cache.experiments:
                self.participating_tests.remove(participating_test)

        for converted_test in self.converted_tests.keys():
            if not converted_test in bingo_cache.experiments:
                del self.converted_tests[converted_test]

    def participate_in(self, experiment_name):
        self.participating_tests.append(experiment_name)
        self.dirty = True

    def convert_in(self, experiment_name):
        if experiment_name not in self.converted_tests:
            self.converted_tests[experiment_name] = 1 
        else:
            self.converted_tests[experiment_name] += 1
        self.dirty = True


def bingo_and_identity_cache(identity_val=None):
    return BingoCache.get(), BingoIdentityCache.get(identity_val)


def store_if_dirty():
    # Only load from request cache here -- if it hasn't been loaded from memcache previously, it's not dirty.
    bingo_cache = request_cache.cache.get(BingoCache.CACHE_KEY)
    bingo_identity_cache = request_cache.cache.get(BingoIdentityCache.key_for_identity(identity()))

    if bingo_cache:
        bingo_cache.store_if_dirty()

    if bingo_identity_cache:
        bingo_identity_cache.store_for_identity_if_dirty(identity())


def persist_gae_bingo_identity_records(list_identities):

    dict_identity_caches = memcache.get_multi([BingoIdentityCache.key_for_identity(ident) for ident in list_identities])

    for ident in list_identities:
        identity_cache = dict_identity_caches.get(BingoIdentityCache.key_for_identity(ident))

        if identity_cache:
            bingo_identity = _GAEBingoIdentityRecord(
                        key_name = _GAEBingoIdentityRecord.key_for_identity(ident),
                        identity = ident,
                        pickled = pickle_util.dump(identity_cache),
                    )
            bingo_identity.put()


class LogSnapshotToDatastore(RequestHandler):
    def get(self):
        BingoCache.get().log_cache_snapshot()


########NEW FILE########
__FILENAME__ = cache_test
from google.appengine.api import memcache

from testutil import gae_model

from . import cache

class CacheTest(gae_model.GAEModelTestCase):
    def test_bingo_identity_bucket_max(self):
        # If the number of buckets changes then the magic number for the ident
        # needs to change. 166 is the lowest number that hashes to bucket 50.
        #
        # The magic number is derived from brute force application of the
        # bucketing hash function:
        #
        #  import hashlib
        #  num_buckets = 51
        #  next(i for i in xrange(0, 10000)
        #       if (num_buckets - 1) == (int(hashlib.md5(str(i)).hexdigest(),
        #                                    base=16) % num_buckets))
        self.assertEqual(51, cache.NUM_IDENTITY_BUCKETS)
        max_bucket_key = "_gae_bingo_identity_bucket:50"
        ident = 166

        ident_cache = cache.BingoIdentityCache()
        self.assertIsNone(memcache.get(max_bucket_key))
        # This puts the identity cache in memcache.
        ident_cache.persist_to_datastore(ident)
        self.assertEqual(1, len(memcache.get(max_bucket_key)))
        # This persists buckets in memcache to the datastore then clears them
        # from memcache.
        cache.BingoIdentityCache.persist_buckets_to_datastore()
        self.assertEqual(0, len(memcache.get(max_bucket_key)))

########NEW FILE########
__FILENAME__ = config
from google.appengine.api import lib_config


class _ConfigDefaults(object):
    # CUSTOMIZE set queue_name to something other than "default"
    # if you'd like to use a non-default task queue.
    QUEUE_NAME = "default"

    # CUSTOMIZE can_see_experiments however you want to specify
    # whether or not the currently-logged-in user has access
    # to the experiment dashboard.
    def can_control_experiments():
        return False

    # CUSTOMIZE current_logged_in_identity to make your a/b sessions
    # stickier and more persistent per user.
    #
    # This should return one of the following:
    #
    #   A) a db.Model that identifies the current user, like
    #      user_models.UserData.current()
    #   B) a unique string that consistently identifies the current user, like
    #      users.get_current_user().user_id()
    #   C) None, if your app has no way of identifying the current user for the
    #      current request. In this case gae_bingo will automatically use a random
    #      unique identifier.
    #
    # Ideally, this should be connected to your app's existing identity system.
    #
    # To get the strongest identity tracking even when switching from a random, not
    # logged-in user to a logged in user, return a model that inherits from
    # GaeBingoIdentityModel.  See docs for details.
    #
    # Examples:
    #   return user_models.UserData.current()
    #         ...or...
    #   from google.appengine.api import users
    #   user = users.get_current_user()
    #   return user.user_id() if user else None
    def current_logged_in_identity():
        return None

    # Optionally, you can provide a function that will retrieve the identitiy given
    # a query.  If not used, simply return None.
    def retrieve_identity(query):
        return None

    # CUSTOMIZE is_safe_hostname to whitelist hostnames for gae_bingo.redirect
    def is_safe_hostname(hostname):
        return False

    # CUSTOMIZE wrap_wsgi_app if you want to add middleware around all of the
    # /gae_bingo endpoints, such as to clear a global per-request cache that
    # can_control_experiments uses. If not used, simply return app.
    #
    # Examples:
    #   return app  # No middleware
    #
    #   return RequestCacheMiddleware(app)
    def wrap_wsgi_app(app):
        return app


# TODO(chris): move config to the toplevel. Right now callers do
# config.config.VALUE rather than simply config.VALUE.  I wanted to
# avoid introspecting _ConfigDefaults and exporting values into the
# module namespace.  Until then use "from config import config".
config = lib_config.register('gae_bingo', _ConfigDefaults.__dict__)

########NEW FILE########
__FILENAME__ = cookies
import Cookie
import logging
import os

def get_cookie_value(key):
    cookies = None
    try:
        cookies = Cookie.BaseCookie(os.environ.get('HTTP_COOKIE',''))
    except Cookie.CookieError, error:
        logging.debug("Ignoring Cookie Error, skipping get cookie: '%s'" % error)

    if not cookies:
        return None

    cookie = cookies.get(key)

    if not cookie:
        return None

    return cookie.value

# Cookie handling from http://appengine-cookbook.appspot.com/recipe/a-simple-cookie-class/
def set_cookie_value(key, value='', max_age=None,
               path='/', domain=None, secure=None, httponly=False,
               version=None, comment=None):
    cookies = Cookie.BaseCookie()
    cookies[key] = value
    for var_name, var_value in [
        ('max-age', max_age),
        ('path', path),
        ('domain', domain),
        ('secure', secure),
        #('HttpOnly', httponly), Python 2.6 is required for httponly cookies
        ('version', version),
        ('comment', comment),
        ]:
        if var_value is not None and var_value is not False:
            cookies[key][var_name] = str(var_value)
    if max_age is not None:
        cookies[key]['expires'] = max_age

    cookies_header = cookies[key].output(header='').lstrip()

    if httponly:
        # We have to manually add this part of the header until GAE uses Python 2.6.
        cookies_header += "; HttpOnly"

    return cookies_header


########NEW FILE########
__FILENAME__ = custom_exceptions
class InvalidRedirectURLError(Exception):
    """Raised when there is a redirect attempt to an absolute url."""
    pass

########NEW FILE########
__FILENAME__ = dashboard
import logging
import csv
import os
import StringIO
import urllib

from google.appengine.ext.webapp import RequestHandler
from .identity import can_control_experiments
from .cache import BingoCache
from .stats import describe_result_in_words

class Dashboard(RequestHandler):

    def get(self):

        if not can_control_experiments():
            self.redirect("/")
            return

        path = os.path.join(os.path.dirname(__file__),
                "templates/bootstrap.html")

        f = None
        try:
            f = open(path, "r")
            html = f.read()
        finally:
            if f:
                f.close()

        self.response.out.write(html)


class Export(RequestHandler):

    def get(self):

        if not can_control_experiments():
            self.redirect("/")
            return

        bingo_cache = BingoCache.get()

        canonical_name = self.request.get("canonical_name")
        experiments, alternatives = bingo_cache.experiments_and_alternatives_from_canonical_name(canonical_name)

        if not experiments:
            raise Exception("No experiments matching canonical name: %s" % canonical_name)

        f = StringIO.StringIO()

        try:

            writer = csv.writer(f, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

            writer.writerow(["EXPERIMENT: %s" % canonical_name])
            writer.writerow([])
            writer.writerow([])

            for experiment, alternatives in zip(experiments, alternatives):

                writer.writerow(["CONVERSION NAME: %s" % experiment.conversion_name])
                writer.writerow([])

                writer.writerow(["ALTERNATIVE NUMBER", "CONTENT", "PARTICIPANTS", "CONVERSIONS", "CONVERSION RATE"])
                for alternative in alternatives:
                    writer.writerow([alternative.number, alternative.content, alternative.participants, alternative.conversions, alternative.conversion_rate])

                writer.writerow([])
                writer.writerow(["SIGNIFICANCE TEST RESULTS: %s" % describe_result_in_words(alternatives)])
                writer.writerow([])

                writer.writerow([])
                writer.writerow([])

            self.response.headers["Content-Type"] = "text/csv"
            self.response.headers["Content-Disposition"] = "attachment; filename=gae_bingo-%s.csv" % urllib.quote(canonical_name)
            self.response.out.write(f.getvalue())

        finally:

            f.close()

########NEW FILE########
__FILENAME__ = gae_bingo
import datetime
import hashlib
import logging
import re
import time
import urllib

from google.appengine.api import memcache
from google.appengine.ext import ndb

import cache
from .cache import BingoCache, BingoIdentityCache, bingo_and_identity_cache
from .models import create_experiment_and_alternatives, ConversionTypes
from .identity import can_control_experiments, identity
from .cookies import get_cookie_value
from .persist import PersistLock

# gae/bingo supports up to four alternatives per experiment due to
# synchronized_counter's limit of 4 synchronized counters per combination.
# See synchronized_counter.py for more.
MAX_ALTERNATIVES_PER_EXPERIMENT = 4

def create_unique_experiments(canonical_name,
                              alternative_params,
                              conversion_names,
                              conversion_types,
                              family_name,
                              unique_experiment_names,
                              bingo_cache,
                              experiments):
    """Once we have a lock, create all of the unique experiments.

       canonical_name to family_name are all as in ab_test, except that
       conversion_names, conversion_types must be lists.

       unique_experiment_names are names unique to each experiment,
       generated in ab_test.

       bingo_cache and experiments are created in ab_test and passed to here,
       giving the current bingo_cache and current cached list of experiments.

    """

    if not(len(conversion_names) ==
                len(conversion_types) ==
                len(unique_experiment_names)):
        # The arguments should be correct length, since ab_test ensures that.
        # If they're not the same length, we don't know that ab_test ran
        # successfully, so we should abort (we might not even have a lock!)
        raise Exception("create_unique_experiments called with"
                        "arguments of mismatched length!")

    for i in range(len(conversion_names)):
        # We don't want to create a unique_experiment more than once
        # (note: it's fine to add experiments to one canonical name,
        #  which is how we can have one experiment with multiple conversions)
        if unique_experiment_names[i] not in experiments:
            exp, alts = create_experiment_and_alternatives(
                            unique_experiment_names[i],
                            canonical_name,
                            alternative_params,
                            conversion_names[i],
                            conversion_types[i],
                            family_name)

            bingo_cache.add_experiment(exp, alts)

    bingo_cache.store_if_dirty()


@ndb.tasklet
def participate_in_experiments_async(experiments,
                                     alternative_lists,
                                     bingo_identity_cache):
    """ Given a list of experiments (with unique names), alternatives for each,
        and an identity cache:
        --Enroll the current user in each experiment
        --return a value indicating which bucket a user is sorted into
            (this will be one of the entries in alternative_lists)

    """
    returned_content = [None]

    @ndb.tasklet
    def participate_async(experiment, alternatives):
        if not experiment.live:
            # Experiment has ended. Short-circuit and use selected winner
            # before user has had a chance to remove relevant ab_test code.
            returned_content[0] = experiment.short_circuit_content

        else:
            alternative = _find_alternative_for_user(experiment,
                                                    alternatives)

            if experiment.name not in bingo_identity_cache.participating_tests:
                if (yield alternative.increment_participants_async()):
                    bingo_identity_cache.participate_in(experiment.name)

            # It shouldn't matter which experiment's alternative content
            # we send back -- alternative N should be the same across
            # all experiments w/ same canonical name.
            returned_content[0] = alternative.content

    yield [participate_async(e, a)
           for e, a in zip(experiments, alternative_lists)]

    raise ndb.Return(returned_content[0])


def participate_in_experiments(*args):
    return participate_in_experiments_async(*args).get_result()


def ab_test(canonical_name,
            alternative_params = None,
            conversion_name = None,
            conversion_type = ConversionTypes.Binary,
            family_name = None):

    if (alternative_params is not None and
            len(alternative_params) > MAX_ALTERNATIVES_PER_EXPERIMENT):
        raise Exception("Cannot ab test with more than 4 alternatives")

    bingo_cache, bingo_identity_cache = bingo_and_identity_cache()

    # Make sure our conversion names and types are lists so that
    # we can more simply create one experiment for each one later.
    if isinstance(conversion_name, list):
        conversion_names = conversion_name
    else:
        conversion_names = [conversion_name]

    if isinstance(conversion_type, list):
        conversion_types = conversion_type
    else:
        conversion_types = [conversion_type] * len(conversion_names)


    # Unique name will have both canonical name and conversion.
    # This way, order of arguments in input list doesn't matter and
    # we still have unique experiment names.
    unique_experiment_names = ["%s (%s)" % (canonical_name, conv)
            if conv != None else canonical_name for conv in conversion_names]

    # Only create the experiment if it's necessary
    if any([conv not in bingo_cache.experiments
                    for conv in unique_experiment_names]):
        # Creation logic w/ high concurrency protection
        client = memcache.Client()
        lock_key = "_gae_bingo_test_creation_lock"
        got_lock = False
        try:

            # Make sure only one experiment gets created
            while not got_lock:
                locked = client.gets(lock_key)

                while locked is None:
                    # Initialize the lock if necessary
                    client.set(lock_key, False)
                    locked = client.gets(lock_key)

                if not locked:
                    # Lock looks available, try to take it with compare
                    # and set (expiration of 10 seconds)
                    got_lock = client.cas(lock_key, True, time=10)

                if not got_lock:
                    # If we didn't get it, wait a bit and try again
                    time.sleep(0.1)

            # We have the lock, go ahead and create the experiment
            experiments = BingoCache.get().experiments


            if len(conversion_names) != len(conversion_types):
                # we were called improperly with mismatched lists lengths.
                # Default everything to Binary
                logging.warning("ab_test(%s) called with lists of mismatched"
                                "length. Defaulting all conversions to binary!"
                                % canonical_name)
                conversion_types = ([ConversionTypes.Binary] *
                                        len(conversion_names))

            # Handle multiple conversions for a single experiment by just
            # quietly creating multiple experiments (one for each conversion).
            create_unique_experiments(canonical_name,
                                     alternative_params,
                                     conversion_names,
                                     conversion_types,
                                     family_name,
                                     unique_experiment_names,
                                     bingo_cache,
                                     experiments)

        finally:
            if got_lock:
                # Release the lock
                client.set(lock_key, False)

    # We might have multiple experiments connected to this single canonical
    # experiment name if it was started w/ multiple conversion possibilities.
    experiments, alternative_lists = (
            bingo_cache.experiments_and_alternatives_from_canonical_name(
                canonical_name))

    if not experiments or not alternative_lists:
        raise Exception(
            "Could not find experiment or alternatives with experiment_name %s"
            % canonical_name)

    return participate_in_experiments(experiments,
                                      alternative_lists,
                                      bingo_identity_cache)


def bingo(param, identity_val=None):
    bingo_async(param, identity_val).get_result()


@ndb.tasklet
def bingo_async(param, identity_val=None):

    if isinstance(param, list):
        # Bingo for all conversions in list
        yield [bingo_async(conversion_name, identity_val)
               for conversion_name in param]

    else:
        conv_name = str(param)
        bingo_cache = BingoCache.get()
        experiments = bingo_cache.get_experiment_names_by_conversion_name(
                conv_name)

        # Bingo for all experiments associated with this conversion
        yield [score_conversion_async(e, identity_val) for e in experiments]


@ndb.tasklet
def score_conversion_async(experiment_name, identity_val=None):
    bingo_cache, bingo_identity_cache = bingo_and_identity_cache(identity_val)

    if experiment_name not in bingo_identity_cache.participating_tests:
        return

    experiment = bingo_cache.get_experiment(experiment_name)

    if not experiment or not experiment.live:
        # Don't count conversions for short-circuited
        # experiments that are no longer live
        return

    if (experiment.conversion_type != ConversionTypes.Counting and
            experiment_name in bingo_identity_cache.converted_tests):
        # Only allow multiple conversions for
        # ConversionTypes.Counting experiments
        return

    alternative = _find_alternative_for_user(
                      experiment,
                      bingo_cache.get_alternatives(experiment_name),
                      identity_val)

    # TODO(kamens): remove this! Temporary protection from an experiment that
    # has more than 4 alternatives while we migrate to the new gae/bingo
    # alternative restriction.
    if alternative.number >= 4:
        return

    if (yield alternative.increment_conversions_async()):
        bingo_identity_cache.convert_in(experiment_name)


class ExperimentModificationException(Exception):
    """An exception raised when calls to control or modify an experiment
    is unable to do so safely due to contention with background tasks.

    If there is too much contention between mutating an experiment and
    constantly running persist tasks, this exception is raised.

    See ExperimentController for more details.
    """
    pass


class ExperimentController(object):
    """A context that can be used to build monitors to modify experiments.

    Since modifications of the bingo data need to happen atomically across
    multiple items, the constantly running persist tasks could interfere with
    clients attempting to do control operations that modify experiments.

    Use this in conjunction with a with statement before calling any
    experiment modifying methods. This context will also flush the bingo
    cache on exit.
    """

    _lock_set = False

    def __enter__(self):
        self.lock = PersistLock()
        if not self.lock.spin_and_take():
            raise ExperimentModificationException(
                    "Unable to acquire lock to modify experiments")
        ExperimentController._lock_set = True

    def __exit__(self, exc_type, exc_value, traceback):
        # Forcefully flush the cache, since this must be done inside of
        # the monitor. The mutation methods (e.g. choose_alternative) are
        # implemented in such a way that they rely on the gae/bingo middleware
        # to flush the data. But by that point the lock will have been released
        cache.store_if_dirty()
        ExperimentController._lock_set = False
        logging.info(
                "Exiting monitor from ExperimentController. About to "
                "release the lock (current value: [%s])" %
                self.lock.is_active())
        self.lock.release()

    @staticmethod
    def assert_safe():
        """Assert that caller is in a monitor that can modify experiments."""
        if not ExperimentController._lock_set:
            raise ExperimentModificationException(
                    "Attempting to modify experiment outside of monitor. "
                    "Use with ExperimentController(): ... around "
                    "your snippet.")

def choose_alternative(canonical_name, alternative_number):
    ExperimentController.assert_safe()
    bingo_cache = BingoCache.get()

    # Need to end all experiments that may have been kicked off
    # by an experiment with multiple conversions
    experiments, alternative_lists = (
            bingo_cache.experiments_and_alternatives_from_canonical_name(
                canonical_name))

    if not experiments or not alternative_lists:
        return

    for i in range(len(experiments)):
        experiment, alternatives = experiments[i], alternative_lists[i]

        alternative_chosen = filter(
                lambda alt: alt.number == alternative_number,
                alternatives)

        if len(alternative_chosen) == 1:
            experiment.live = False
            experiment.set_short_circuit_content(
                    alternative_chosen[0].content)
            bingo_cache.update_experiment(experiment)
        else:
            logging.warning(
                    "Skipping choose alternative for %s (chosen: %s)" %
                    (experiment.name, alternative_chosen))

def delete_experiment(canonical_name, retrieve_archives=False):
    ExperimentController.assert_safe()

    if retrieve_archives:
        bingo_cache = BingoCache.load_from_datastore(archives=True)
    else:
        bingo_cache = BingoCache.get()

    # Need to delete all experiments that may have been kicked off
    # by an experiment with multiple conversions
    experiments, alternative_lists = (
            bingo_cache.experiments_and_alternatives_from_canonical_name(
                canonical_name))

    if not experiments or not alternative_lists:
        return

    for experiment in experiments:
        bingo_cache.delete_experiment_and_alternatives(experiment)

def archive_experiment(canonical_name):
    """Archive named experiment permanently, removing it from active cache."""

    ExperimentController.assert_safe()
    bingo_cache = BingoCache.get()

    # Need to archive all experiments that may have been kicked off
    # by an experiment with multiple conversions
    experiments, alternative_lists = (
            bingo_cache.experiments_and_alternatives_from_canonical_name(
                canonical_name))

    if not experiments or not alternative_lists:
        logging.error("Can't find experiments named %s" % canonical_name)
        return

    for experiment in experiments:
        if not experiment:
            logging.error("Found empty experiment under %s" % canonical_name)
        else:
            logging.info("Archiving %s" % experiment.name)
        bingo_cache.archive_experiment_and_alternatives(experiment)

def resume_experiment(canonical_name):
    ExperimentController.assert_safe()
    bingo_cache = BingoCache.get()

    # Need to resume all experiments that may have been kicked off
    # by an experiment with multiple conversions
    experiments, alternative_lists = (
            bingo_cache.experiments_and_alternatives_from_canonical_name(
                canonical_name))

    if not experiments or not alternative_lists:
        return

    for experiment in experiments:
        experiment.live = True
        bingo_cache.update_experiment(experiment)


def get_experiment_participation(identity_val=None):
    """Get the the experiments and alternatives the user participated in.

    Returns a dict of canonical name: alternative for every experiment that
    this user participated in, even if the experiment has ended.
    """
    bingo_cache, bingo_identity_cache = bingo_and_identity_cache(identity_val)

    tests = bingo_identity_cache.participating_tests

    # HACK: tests is actually a list of conversions, so try to reduce them to
    # canonical names. Just use the full name if there's no paren.
    expts = set()
    for t in tests:
        i = t.rfind(" (")
        expts.add(t if i == -1 else t[0:i])

    # now get the alternative this user is participating in, as long as it is
    # actually a canonical name (just skip the ones that are not)
    return {e: find_alternative_for_user(e, identity_val) for e in expts
            if e in bingo_cache.experiment_names_by_canonical_name}


def find_alternative_for_user(canonical_name, identity_val):
    """ Returns the alternative that the specified bingo identity belongs to.
    If the experiment does not exist, this will return None.
    If the experiment has ended, this will return the chosen alternative.
    Note that the user may not have been opted into the experiment yet - this
    is just a way to probe what alternative will be selected, or has been
    selected for the user without causing side effects.

    If an experiment has multiple instances (because it was created with
    different alternative sets), will operate on the last experiment.

    canonical_name -- the canonical name of the experiment
    identity_val -- a string or instance of GAEBingoIdentity

    """

    bingo_cache = BingoCache.get()
    experiment_names = bingo_cache.get_experiment_names_by_canonical_name(
            canonical_name)

    if not experiment_names:
        return None

    experiment_name = experiment_names[-1]
    experiment = bingo_cache.get_experiment(experiment_name)

    if not experiment:
        return None

    if not experiment.live:
        # Experiment has ended - return result that was selected.
        return experiment.short_circuit_content

    return _find_alternative_for_user(experiment,
                bingo_cache.get_alternatives(experiment_name),
                identity_val).content


def find_cookie_val_for_user(experiment_name):
    """ For gae_bingo admins, return the value of a cookie associated with the
    given experiment name. """
    if not can_control_experiments():
        return None

    # This escaping must be consistent with what's done in
    # static/js/dashboard.js
    cookie_val = get_cookie_value(
        "GAEBingo_%s" % re.sub(r'\W', '+', experiment_name))
    if not cookie_val:
        return None
    return int(cookie_val)


def find_cookie_alt_param_for_user(experiment_name, alternative_params):
    """ If gae_bingo administrator, allow possible override of alternative.

    Return the cookie value set when gae_bingo adminstrators click the
    "preview" button for an experiment alternative in the gae_bingo dashboard.
    """
    index = find_cookie_val_for_user(experiment_name)
    if index is None or index >= len(alternative_params):
        return None
    return alternative_params[index]


def _find_cookie_alternative_for_user(experiment, alternatives):
    index = find_cookie_val_for_user(experiment.hashable_name)
    if index is None:
        return None
    return next((x for x in alternatives if x.number == index), None)


def _find_alternative_for_user(experiment,
                               alternatives,
                               identity_val=None):
    return (_find_cookie_alternative_for_user(experiment, alternatives) or
            modulo_choose(experiment, alternatives, identity(identity_val)))


def modulo_choose(experiment, alternatives, identity):

    alternatives_weight = sum(map(lambda alt: alt.weight, alternatives))

    sig = hashlib.md5(experiment.hashable_name + str(identity)).hexdigest()
    sig_num = int(sig, base=16)
    index_weight = sig_num % alternatives_weight
    current_weight = alternatives_weight

    # TODO(eliana) remove once current expts end
    if experiment.dt_started > datetime.datetime(2013, 3, 26, 18, 0, 0, 0):
        sorter = lambda alt: (alt.weight, alt.number)
    else:
        sorter = lambda alt: alt.weight

    for alternative in sorted(alternatives,
                              key=sorter,
                              reverse=True):

        current_weight -= alternative.weight
        if index_weight >= current_weight:
            return alternative

def create_redirect_url(destination, conversion_names):
    """ Create a URL that redirects to destination after scoring conversions
    in all listed conversion names
    """

    result = "/gae_bingo/redirect?continue=%s" % urllib.quote(destination)

    if type(conversion_names) != list:
        conversion_names = [conversion_names]

    for conversion_name in conversion_names:
        result += "&conversion_name=%s" % urllib.quote(conversion_name)

    return result

def _iri_to_uri(iri):
    """Convert an Internationalized Resource Identifier (IRI) for use in a URL.

    This function follows the algorithm from section 3.1 of RFC 3987 and is
    idempotent, iri_to_uri(iri_to_uri(s)) == iri_to_uri(s)

    Args:
        iri: A unicode string.

    Returns:
        An ASCII string with the encoded result. If iri is not unicode it
        is returned unmodified.
    """
    # Implementation heavily inspired by django.utils.encoding.iri_to_uri()
    # for its simplicity. We make the further assumption that the incoming
    # argument is a unicode string or is ignored.
    #
    # See also werkzeug.urls.iri_to_uri() for a more complete handling of
    # internationalized domain names.
    if isinstance(iri, unicode):
        byte_string = iri.encode("utf-8")
        return urllib.quote(byte_string, safe="/#%[]=:;$&()+,!?*@'~")
    return iri

########NEW FILE########
__FILENAME__ = identity
from __future__ import absolute_import

import base64
import logging
import os
import re

from google.appengine.ext import db

from gae_bingo.config import config
from gae_bingo import cookies
from gae_bingo import request_cache
from .models import GAEBingoIdentityModel

IDENTITY_COOKIE_KEY = "gae_b_id"
IDENTITY_COOKIE_AGE = 365 * 24 * 60 * 60  # ~1 year in seconds

CAN_CONTROL_CACHE_KEY = "CAN_CONTROL_CACHE"
IDENTITY_CACHE_KEY = "IDENTITY_CACHE"
LOGGED_IN_IDENTITY_CACHE_KEY = "LOGGED_IN_IDENTITY_CACHE"
ID_TO_PUT_CACHE_KEY = "ID_TO_PUT"


def can_control_experiments():
    if request_cache.cache.get(CAN_CONTROL_CACHE_KEY) is None:
        request_cache.cache[CAN_CONTROL_CACHE_KEY] = (
                config.can_control_experiments())

    return request_cache.cache[CAN_CONTROL_CACHE_KEY]


def logged_in_bingo_identity():
    if request_cache.cache.get(LOGGED_IN_IDENTITY_CACHE_KEY) is None:
        request_cache.cache[LOGGED_IN_IDENTITY_CACHE_KEY] = config.current_logged_in_identity()

    return request_cache.cache[LOGGED_IN_IDENTITY_CACHE_KEY]


def flush_caches():
    """Flush the caches associated with the logged in identity.

    This is useful if the logged in identity changed for some reason
    mid-request.
    """
    request_cache.cache.pop(CAN_CONTROL_CACHE_KEY, None)
    request_cache.cache.pop(IDENTITY_CACHE_KEY, None)
    request_cache.cache.pop(LOGGED_IN_IDENTITY_CACHE_KEY, None)
    request_cache.cache.pop(ID_TO_PUT_CACHE_KEY, None)


def identity(identity_val=None):
    """ Determines the Bingo identity for the specified user. If no user
    is specified, this will attempt to infer one based on cookies/logged in user


    identity_val -- a string or instance of GAEBingoIdentityModel specifying
    which bingo identity to retrieve.
    """
    if identity_val:
        # Don't cache for arbitrarily passed in identity_val
        return bingo_identity_for_value(identity_val, associate_with_cookie=False)

    if request_cache.cache.get(IDENTITY_CACHE_KEY) is None:

        if is_bot():

            # Just make all bots identify as the same single user so they don't
            # bias results. Following simple suggestion in
            # http://www.bingocardcreator.com/abingo/faq
            request_cache.cache[IDENTITY_CACHE_KEY] = "_gae_bingo_bot"

        else:

            # Try to get unique (hopefully persistent) identity from user's implementation,
            # otherwise grab the current cookie value, otherwise grab random value.
            request_cache.cache[IDENTITY_CACHE_KEY] = str(get_logged_in_bingo_identity_value() or get_identity_cookie_value() or get_random_identity_value())

    return request_cache.cache[IDENTITY_CACHE_KEY]

def using_logged_in_bingo_identity():
    return identity() and identity() == get_logged_in_bingo_identity_value()

def get_logged_in_bingo_identity_value():
    val = logged_in_bingo_identity()
    return bingo_identity_for_value(val)

def bingo_identity_for_value(val, associate_with_cookie=True):
    # We cache the ID we generate here, to put only at the end of the request

    if val is None:
        return None

    if isinstance(val, db.Model):

        if isinstance(val, GAEBingoIdentityModel):
            # If it's a db.Model that inherited from GAEBingoIdentityModel, return bingo identity

            if not val.gae_bingo_identity:

                if (is_random_identity_value(get_identity_cookie_value()) and
                    associate_with_cookie):
                    # If the current model doesn't have a bingo identity associated w/ it
                    # and we have a random cookie value already set, associate it with this identity model.
                    #
                    # This keeps the user's experience consistent between using the site pre- and post-login.
                    request_cache.cache[ID_TO_PUT_CACHE_KEY] = get_identity_cookie_value()
                else:
                    # Otherwise just use the key, it's guaranteed to be unique
                    request_cache.cache[ID_TO_PUT_CACHE_KEY] = str(val.key())


            return val.gae_bingo_identity

        # If it's just a normal db instance, just use its unique key
        return str(val.key())

    # Otherwise it's just a plain unique string
    return str(val)

def get_random_identity_value():
    return "_gae_bingo_random:%s" % base64.urlsafe_b64encode(os.urandom(30))

def is_random_identity_value(val):
    return val and val.startswith("_gae_bingo_random")

def get_identity_cookie_value():
    cookie_val = cookies.get_cookie_value(IDENTITY_COOKIE_KEY)

    if cookie_val:
        try:
            return base64.urlsafe_b64decode(cookie_val)
        except:
            pass

    return None

def put_id_if_necessary():
    """To be called at the end of a request.
    Check to see if we should put() the gae_bingo_identity, and put() it if so.

    """
    id_to_put = request_cache.cache.get(ID_TO_PUT_CACHE_KEY)
    if id_to_put:
        val = config.current_logged_in_identity()
        if val is None:
            return
        if isinstance(val, GAEBingoIdentityModel):
            if val.gae_bingo_identity and id_to_put != val.gae_bingo_identity:
                logging.warning(
                        "val.gae_bingo_identity got set to %s unexpectedly,"
                        "but id_to_put is %s"
                        % (val.gae_bingo_identity, id_to_put))
            else:
                # If the UserData has been updated in the course of this
                # request current_logged_in_identity might read a stale version
                # of the UserData from the request_cache.  In order to make
                # sure we have the latest userData we will get the the userData
                # again.  
                val = db.get(val.key())

                val.gae_bingo_identity = id_to_put

                val.put()

                # Flush the transaction so the HR datastore doesn't suffer from
                # eventual consistency issues when next grabbing this UserData.
                db.get(val.key())

def set_identity_cookie_header():
    return cookies.set_cookie_value(IDENTITY_COOKIE_KEY,
            base64.urlsafe_b64encode(identity()), max_age=IDENTITY_COOKIE_AGE)

def delete_identity_cookie_header():
    return cookies.set_cookie_value(IDENTITY_COOKIE_KEY, "")

# I am well aware that this is a far-from-perfect, hacky method of quickly
# determining who's a bot or not. If necessary, in the future we could implement
# a javascript check like a/bingo and django-lean do -- but for now, I'm sticking
# w/ the simplest possible implementation for devs (don't need to add JS in any template code)
# that doesn't strongly bias the statistical outcome (undetected bots aren't a distaster,
# because they shouldn't favor one side over the other).
bot_regex = re.compile("(Baidu|Gigabot|Googlebot|libwww-perl|lwp-trivial|msnbot|SiteUptime|Slurp|WordPress|ZIBB|ZyBorg)", re.IGNORECASE)
def is_bot():
    return bool(bot_regex.search(os.environ.get("HTTP_USER_AGENT") or ""))

########NEW FILE########
__FILENAME__ = instance_cache
"""
Based on cachepy.py by Juan Pablo Guereca with additional modifications
for thread safety and simplified to reduce time spent in critical areas.

Module which implements a per GAE instance data cache, similar to what
you can achieve with APC in PHP instances.

Each GAE instance caches the global scope, keeping the state of every
variable on the global scope.

You can go farther and cache other things, creating a caching layer
for each GAE instance, and it's really fast because there is no
network transfer like in memcache. Moreover GAE doesn't charge for
using it and it can save you many memcache and db requests.

Not everything are upsides. You can not use it on every case because:

- There's no way to know if you have set or deleted a key in all the
  GAE instances that your app is using. Everything you do with Cachepy
  happens in the instance of the current request and you have N
  instances, be aware of that.

- The only way to be sure you have flushed all the GAE instances
  caches is doing a code upload, no code change required.

- The memory available depends on each GAE instance and your app. I've
  been able to set a 60 millions characters string which is like 57 MB
  at least. You can cache somethings but not everything.
"""

# TODO(chris): implement an LRU cache. currently we store all sorts of
# things in instance memory by default via layer_cache, and these
# things might never be reaped.

import time
import logging
import os

try:
    import threading
except ImportError:
    import dummy_threading as threading

_CACHE = {}
_CACHE_LOCK = threading.RLock()

""" Flag to deactivate it on local environment. """
ACTIVE = (not os.environ.get('SERVER_SOFTWARE').startswith('Devel') or
          os.environ.get('FAKE_PROD_APPSERVER'))

"""
None means forever.
Value in seconds.
"""
DEFAULT_CACHING_TIME = None


# TODO(csilvers): change the API to be consistent with the memcache API.


def get(key):
    """ Gets the data associated to the key or a None """
    if ACTIVE is False:
        return None

    with _CACHE_LOCK:
        entry = _CACHE.get(key, None)
        if entry is None:
            return None

        value, expiry = entry
        if expiry == None:
            return value

        current_timestamp = time.time()
        if current_timestamp < expiry:
            return value
        else:
            del _CACHE[key]
            return None


def get_all_with_prefix(prefix):
    """ Return a map of key->data for all keys starting with prefix """
    if ACTIVE is False:
        return {}

    retval = {}
    current_timestamp = time.time()
    with _CACHE_LOCK:
        for key in _CACHE:
            if key.startswith(prefix):
                value, expiry = _CACHE[key]
                if expiry is not None:
                    if current_timestamp >= expiry:
                        del _CACHE[key]
                        continue
                retval[key] = value
        return retval


def set(key, value, expiry=DEFAULT_CACHING_TIME):
    """
    Sets a key in the current instance
    key, value, expiry seconds till it expires
    """
    if ACTIVE is False:
        return None

    if expiry != None:
        expiry = time.time() + int(expiry)

    try:
        with _CACHE_LOCK:
            _CACHE[key] = (value, expiry)
    except MemoryError:
        # It doesn't seems to catch the exception, something in the
        # GAE's python runtime probably.
        logging.info("%s memory error setting key '%s'" % (__name__, key))


def increment(key, expiry=DEFAULT_CACHING_TIME):
    """
    Increments key (setting the result to 1 if key isn't present).
    Also resets the expiry for this key.
    """
    if ACTIVE is False:
        return None

    if expiry != None:
        expiry = time.time() + int(expiry)

    try:
        with _CACHE_LOCK:
            (old_value, _) = _CACHE.get(key, (0, None))
            _CACHE[key] = (old_value + 1, expiry)
    except TypeError:
        logging.error("Cannot increment instance-cache key '%s': value '%s' "
                      "is not an integer" % (key, old_value))
    except MemoryError:
        # It doesn't seems to catch the exception, something in the
        # GAE's python runtime probably.
        logging.info("%s memory error setting key '%s'" % (__name__, key))


def delete(key):
    """ Deletes the key stored in the cache of the current instance,
    not all the instances.  There's no reason to use it except for
    debugging when developing (or reclaiming space using a policy other
    than time), use expiry when setting a value instead.
    """
    with _CACHE_LOCK:
        _CACHE.pop(key, None)


def dump():
    """
    Returns the cache dictionary with all the data of the current
    instance, not all the instances.  There's no reason to use it
    except for debugging when developing.
    """
    return _CACHE


def flush():
    """
    Resets the cache of the current instance, not all the instances.
    There's no reason to use it except for debugging when developing.
    """
    global _CACHE
    with _CACHE_LOCK:
        _CACHE = {}

########NEW FILE########
__FILENAME__ = instance_cache_test
import instance_cache
from testutil import gae_model


class InstanceCacheTest(gae_model.GAEModelTestCase):
    def setUp(self):
        super(InstanceCacheTest, self).setUp()

    def test_no_expiry_should_last_forever(self):
        instance_cache.set('foo', 'bar', expiry=None)
        # A month passes - what incredible up time we have!
        month_in_secs = 60 * 60 * 24 * 31
        self.adjust_time(delta_in_seconds=month_in_secs)
        self.assertEquals('bar', instance_cache.get('foo'))

    def test_expiry_works_as_expected(self):
        instance_cache.set('foo', 'bar', expiry=60)
        self.assertEquals('bar', instance_cache.get('foo'))
        self.adjust_time(delta_in_seconds=61)
        self.assertEquals(None, instance_cache.get('foo'))


########NEW FILE########
__FILENAME__ = jsonify
# Based on http://appengine-cookbook.appspot.com/recipe/extended-jsonify-function-for-dbmodel,
# with modifications for flask and performance.

# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

from google.appengine.ext import db
from datetime import datetime
import re

SIMPLE_TYPES = (int, long, float, bool, basestring)


def dumps(obj, camel_cased=False):
    if isinstance(obj, SIMPLE_TYPES):
        return obj
    elif obj == None:
        return None
    elif isinstance(obj, list):
        items = []
        for item in obj:
            items.append(dumps(item, camel_cased))
        return items
    elif isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif isinstance(obj, dict):
        properties = {}
        for key in obj:
            value = dumps(obj[key], camel_cased)
            if camel_cased:
                properties[camel_casify(key)] = value
            else:
                properties[key] = value
        return properties

    properties = dict()
    if isinstance(obj, db.Model):
        properties['kind'] = obj.kind()

    serialize_blacklist = []
    if hasattr(obj, "_serialize_blacklist"):
        serialize_blacklist = obj._serialize_blacklist

    serialize_list = dir(obj)
    if hasattr(obj, "_serialize_whitelist"):
        serialize_list = obj._serialize_whitelist

    for property in serialize_list:
        if _is_visible_property(property, serialize_blacklist):
            try:
                value = obj.__getattribute__(property)
                if not _is_visible_property_value(value):
                    continue

                valueClass = str(value.__class__)
                if is_visible_class_name(valueClass):
                    value = dumps(value, camel_cased)
                    if camel_cased:
                        properties[camel_casify(property)] = value
                    else:
                        properties[property] = value
            except:
                continue

    if len(properties) == 0:
        return str(obj)
    else:
        return properties

UNDERSCORE_RE = re.compile("_([a-z])")


def camel_case_replacer(match):
    """ converts "_[a-z]" to remove the underscore and uppercase the letter """
    return match.group(0)[1:].upper()


def camel_casify(str):
    return re.sub(UNDERSCORE_RE, camel_case_replacer, str)


def _is_visible_property(property, serialize_blacklist):
    return (property[0] != '_' and
            not property.startswith("INDEX_") and
            not property in serialize_blacklist)


def _is_visible_property_value(value):
    # Right now only db.Blob objects are
    # blacklisted (since they may contain binary that doesn't JSONify well)
    if isinstance(value, db.Blob):
        return False
    return True


def is_visible_class_name(class_name):
    return not(
                ('function' in class_name) or 
                ('built' in class_name) or 
                ('method' in class_name) or
                ('db.Query' in class_name)
            )


class JSONModelEncoder(json.JSONEncoder):
    def default(self, o):
        """ Turns objects into serializable dicts for the default encoder """
        return dumps(o)


class JSONModelEncoderCamelCased(json.JSONEncoder):
    def encode(self, obj):
        # We override encode() instead of the usual default(), since we need
        # to handle built in types like lists and dicts ourselves as well.
        # Specifically, we need to re-construct the object with camelCasing
        # anyways, so do that before encoding.
        obj = dumps(obj, camel_cased=True)
        return super(self.__class__, self).encode(obj)


def jsonify(data, camel_cased=False):
    """jsonify data in a standard (human friendly) way. If a db.Model
    entity is passed in it will be encoded as a dict.

    If the current request being served is being served via Flask, and
    has a parameter "casing" with the value "camel", properties in the
    resulting output will be converted to use camelCase instead of the
    regular Pythonic underscore convention.
    """

    if camel_cased:
        encoder = JSONModelEncoderCamelCased
    else:
        encoder = JSONModelEncoder
    return json.dumps(data,
                      skipkeys=True,
                      sort_keys=False,
                      ensure_ascii=False,
                      indent=4,
                      cls=encoder)

########NEW FILE########
__FILENAME__ = main
from __future__ import absolute_import

from google.appengine.ext.webapp.util import run_wsgi_app
import webapp2
from webapp2_extras.routes import RedirectRoute

from gae_bingo import (cache, dashboard, middleware, plots, blotter,
                       api, redirect, persist)
from gae_bingo.config import config

application = webapp2.WSGIApplication([
    ("/gae_bingo/persist", persist.GuaranteePersistTask),
    ("/gae_bingo/log_snapshot", cache.LogSnapshotToDatastore),
    ("/gae_bingo/blotter/ab_test", blotter.AB_Test),
    ("/gae_bingo/blotter/bingo", blotter.Bingo),

    ("/gae_bingo/redirect", redirect.Redirect),

    ("/gae_bingo", dashboard.Dashboard),
    RedirectRoute('/gae_bingo/dashboard', redirect_to='/gae_bingo'),
    ("/gae_bingo/dashboard/archives", dashboard.Dashboard),
    ("/gae_bingo/dashboard/export", dashboard.Export),

    ("/gae_bingo/api/v1/experiments", api.Experiments),
    ("/gae_bingo/api/v1/experiments/summary", api.ExperimentSummary),
    ("/gae_bingo/api/v1/experiments/conversions", api.ExperimentConversions),
    ("/gae_bingo/api/v1/experiments/control", api.ControlExperiment),
    ("/gae_bingo/api/v1/experiments/notes", api.NoteExperiment),
    ("/gae_bingo/api/v1/alternatives", api.Alternatives),

])
application = middleware.GAEBingoWSGIMiddleware(application)
application = config.wrap_wsgi_app(application)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = middleware
import cache
import identity
import request_cache

class GAEBingoWSGIMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):

        try:
            # Make sure request-cached values are cleared at start of request
            request_cache.flush_request_cache()

            def gae_bingo_start_response(status, headers, exc_info = None):

                if identity.using_logged_in_bingo_identity():
                    if identity.get_identity_cookie_value():
                        # If using logged in identity, clear cookie b/c we don't need it
                        # and it can cause issues after logging out.
                        headers.append(("Set-Cookie",
                                        identity.delete_identity_cookie_header()))
                else:
                    # Not using logged-in identity. If current identity isn't
                    # already stored in cookie, do it now.
                    if identity.identity() != identity.get_identity_cookie_value():
                        headers.append(("Set-Cookie",
                                        identity.set_identity_cookie_header()))

                return start_response(status, headers, exc_info)

            result = self.app(environ, gae_bingo_start_response)
            for value in result:
                yield value

            # Persist any changed GAEBingo data to memcache
            cache.store_if_dirty()

            # If we got a new ID, we should put it to the datastore so it persists
            identity.put_id_if_necessary()

        finally:
            request_cache.flush_request_cache()

########NEW FILE########
__FILENAME__ = models
from collections import defaultdict
import datetime

from google.appengine.ext import db
from google.appengine.ext import ndb

import pickle_util
import synchronized_counter


# We are explicit here about which model properties are indexed and
# which aren't (even when we're just repeating the default behavior),
# to be maximally clear.  We keep indexed properties to a minimum to
# reduce put()-time.  (The cost is you can't pass an unindexed
# property to filter().)

# If you use a datastore model to uniquely identify each user,
# let it inherit from this class, like so...
#
#       class UserData(GAEBingoIdentityModel)
#
# ...this will let gae_bingo automatically take care of persisting ab_test
# identities from unregistered users to logged in users.
class GAEBingoIdentityModel(db.Model):
    gae_bingo_identity = db.StringProperty(indexed=False)

class ConversionTypes():
    # Binary conversions are counted at most once per user
    Binary = "binary"

    # Counting conversions increment each time
    Counting = "counting"

    @staticmethod
    def get_all_as_list():
        return [ConversionTypes.Binary, ConversionTypes.Counting]

    def __setattr__(self, attr, value):
        pass

class _GAEBingoExperiment(db.Model):
    # This is used for a db-query in fetch_for_experiment()
    name = db.StringProperty(indexed=True)

    # Not necessarily unique. Experiments "monkeys" and "monkeys (2)" both have
    # canonical_name "monkeys"
    # This isn't used for db-querying in code, but can be for one-offs.
    canonical_name = db.StringProperty(indexed=True)
    family_name = db.StringProperty(indexed=False)
    conversion_name = db.StringProperty(indexed=False)
    conversion_type = db.StringProperty(
        indexed=False,
        default=ConversionTypes.Binary,
        choices=set(ConversionTypes.get_all_as_list()))

    # Experiments can be live (running), stopped (not running, not archived),
    # or archived (not running, permanently archived).
    # Stopped experiments aren't collecting data, but they exist and can be
    # used to "short-circuit" an alternative by showing it to all users even
    # before the code is appropriately modified to do so.
    live = db.BooleanProperty(indexed=False, default=True)
    # This is used for a db-query in cache.py:load_from_datastore()
    archived = db.BooleanProperty(indexed=True, default=False)

    dt_started = db.DateTimeProperty(indexed=False, auto_now_add=True)
    short_circuit_pickled_content = db.BlobProperty(indexed=False)

    @property
    def stopped(self):
        return not (self.archived or self.live)

    @property
    def short_circuit_content(self):
        if self.short_circuit_pickled_content:
            return pickle_util.load(self.short_circuit_pickled_content)
        else:
            return None

    def set_short_circuit_content(self, value):
        self.short_circuit_pickled_content = pickle_util.dump(value)

    @property
    def pretty_name(self):
        return self.name.capitalize().replace("_", " ")

    @property
    def pretty_conversion_name(self):
        return self.conversion_name.capitalize().replace("_", " ")

    @property
    def pretty_canonical_name(self):
        return self.canonical_name.capitalize().replace("_", " ")

    @property
    def conversion_group(self):
        if "_" in self.conversion_name:
            group = "_".join(self.conversion_name.split("_")[:-1])
            return group.capitalize().replace("_", " ")
        else:
            return self.conversion_name

    @property
    def hashable_name(self):
        return self.family_name if self.family_name else self.canonical_name

    @property
    def age_desc(self):
        if self.archived:
            return "Ran %s UTC" % self.dt_started.strftime('%Y-%m-%d at %H:%M:%S')

        days_running = (datetime.datetime.now() - self.dt_started).days
        
        if days_running < 1:
            return "Less than a day old"
        else:
            return "%s day%s old" % (days_running, ("" if days_running == 1 else "s"))

    @property
    def y_axis_title(self):
        if self.conversion_type == ConversionTypes.Counting:
            "Average Conversions per Participant"
        else:
            "Conversions (%)"

    @property
    def participants_key(self):
        return "%s:participants" % self.name

    @property
    def conversions_key(self):
        return "%s:conversions" % self.name

    def reset_counters(self):
        """Reset the participants and conversions accumulating counters."""
        synchronized_counter.SynchronizedCounter.delete_multi(
                [self.participants_key, self.conversions_key])


class _GAEBingoAlternative(db.Model):
    number = db.IntegerProperty(indexed=False)
    experiment_name = db.StringProperty(indexed=False)
    pickled_content = db.BlobProperty(indexed=False)
    conversions = db.IntegerProperty(indexed=False, default=0)
    participants = db.IntegerProperty(indexed=False, default=0)
    live = db.BooleanProperty(indexed=False, default=True)
    # This is used for a db-query in cache.py:load_from_datastore()
    archived = db.BooleanProperty(indexed=True, default=False)
    weight = db.IntegerProperty(indexed=False, default=1)

    @staticmethod
    def key_for_experiment_name_and_number(experiment_name, number):
        return "_gae_alternative:%s:%s" % (experiment_name, number)

    @property
    def content(self):
        return pickle_util.load(self.pickled_content)

    @property
    def pretty_content(self):
        return str(self.content).capitalize()

    @property
    def conversion_rate(self):
        if self.participants > 0:
            return float(self.conversions) / float(self.participants)
        return 0

    @property
    def pretty_conversion_rate(self):
        return "%4.2f%%" % (self.conversion_rate * 100)

    @property
    def participants_key(self):
        return "%s:participants" % self.experiment_name

    @property
    def conversions_key(self):
        return "%s:conversions" % self.experiment_name

    @ndb.tasklet
    def increment_participants_async(self):
        """Increment a memcache.incr-backed counter to keep track of
        participants in a scalable fashion.

        It's possible that the cached _GAEBingoAlternative entities will fall a
        bit behind due to concurrency issues, but the memcache.incr'd version
        should stay up-to-date and be persisted.

        Returns:
            True if participants was successfully incremented, False otherwise.
        """
        incremented = (yield
                synchronized_counter.SynchronizedCounter.incr_async(
                    self.participants_key, self.number))
        raise ndb.Return(incremented)

    @ndb.tasklet
    def increment_conversions_async(self):
        """Increment a memcache.incr-backed counter to keep track of
        conversions in a scalable fashion.

        It's possible that the cached _GAEBingoAlternative entities will fall a
        bit behind due to concurrency issues, but the memcache.incr'd version
        should stay up-to-date and be persisted.

        Returns:
            True if conversions was successfully incremented, False otherwise.
        """
        incremented = (yield
            synchronized_counter.SynchronizedCounter.incr_async(
                self.conversions_key, self.number))
        raise ndb.Return(incremented)

    def latest_participants_count(self):
        running_count = synchronized_counter.SynchronizedCounter.get(
                self.participants_key, self.number)
        return self.participants + running_count

    def latest_conversions_count(self):
        running_count = synchronized_counter.SynchronizedCounter.get(
                self.conversions_key, self.number)
        return self.conversions + running_count


class _GAEBingoSnapshotLog(db.Model):
    """A snapshot of bingo metrics for a given experiment alternative.

    This is always created with the _GAEBingoExperiment as the entity parent.
    """
    alternative_number = db.IntegerProperty(indexed=False)
    conversions = db.IntegerProperty(indexed=False, default=0)
    participants = db.IntegerProperty(indexed=False, default=0)
    # This is used for a db-query in fetch_for_experiment().
    time_recorded = db.DateTimeProperty(indexed=True, auto_now_add=True)

    @staticmethod
    def fetch_for_experiment(name, limit=100):
        """Retrieves the most recent snapshots for a given experiment.

        Arguments:
            name -- the name of the experiment (not canonical name).
                e.g. "Homepage layout v2point3 (answer_added_binary)"
            limit -- number of snapshots across all the alternatives to fetch
                (note it could be that some alternatives have one more than
                others, depending on the distribution.)
        Returns:
            A dict of snapshots, indexed by alternative_number.
        """
        exp = _GAEBingoExperiment.all().filter("name =", name).get()
        if not exp:
            return {}

        results = (_GAEBingoSnapshotLog.all()
                       .ancestor(exp)
                       .order("-time_recorded")
                       .fetch(limit))
        groups = defaultdict(list)
        for s in results:
            groups[s.alternative_number].append(s)
        return groups


class _GAEBingoExperimentNotes(db.Model):
    """Notes and list of emotions associated w/ results of an experiment."""

    # arbitrary user-supplied notes
    notes = db.TextProperty(indexed=False)

    # list of choices from selection of emotions, such as "happy" and "surprised"
    pickled_emotions = db.BlobProperty(indexed=False)

    @staticmethod
    def key_for_experiment(experiment):
        """Return the key for this experiment's notes."""
        return "_gae_bingo_notes:%s" % experiment.name

    @staticmethod
    def get_for_experiment(experiment):
        """Return GAEBingoExperimentNotes, if it exists, for the experiment."""
        return _GAEBingoExperimentNotes.get_by_key_name(
                _GAEBingoExperimentNotes.key_for_experiment(experiment),
                parent=experiment)

    @staticmethod
    def save(experiment, notes, emotions):
        """Save notes and emo list, associating with specified experiment."""
        notes = _GAEBingoExperimentNotes(
            key_name = _GAEBingoExperimentNotes.key_for_experiment(experiment),
            parent = experiment,
            notes = notes,
            pickled_emotions = pickle_util.dump(emotions))
        notes.put()

    @property
    def emotions(self):
        """Return unpickled list of emotions tied to these notes."""
        if self.pickled_emotions:
            return pickle_util.load(self.pickled_emotions)
        else:
            return None


class _GAEBingoIdentityRecord(db.Model):
    identity = db.StringProperty(indexed=False)

    # Stores a pickled BingoIdentityCache object.
    pickled = db.BlobProperty(indexed=False)

    # A timestamp for keeping track when this record was last updated.
    # Used (well, potentially used) by analytics.git:src/fetch_entities.py.
    backup_timestamp = db.DateTimeProperty(indexed=True, auto_now=True)

    @staticmethod
    def key_for_identity(identity):
        return "_gae_bingo_identity_record:%s" % identity

    @staticmethod
    def load(identity):
        gae_bingo_identity_record = (
                _GAEBingoIdentityRecord.get_by_key_name(
                    _GAEBingoIdentityRecord.key_for_identity(identity)))
        if gae_bingo_identity_record:
            return pickle_util.load(gae_bingo_identity_record.pickled)

        return None

def create_experiment_and_alternatives(experiment_name, canonical_name, alternative_params = None, conversion_name = None, conversion_type = ConversionTypes.Binary, family_name = None):

    if not experiment_name:
        raise Exception("gae_bingo experiments must be named.")

    conversion_name = conversion_name or experiment_name

    if not alternative_params:
        # Default to simple True/False testing
        alternative_params = [True, False]

    # Generate a random key name for this experiment so it doesn't collide with
    # any past experiments of the same name. All other entities, such as
    # alternatives, snapshots, and notes, will then use this entity as their
    # parent.
    experiment = _GAEBingoExperiment(
                key_name = "_gae_experiment:%s" % experiment_name,
                name = experiment_name,
                canonical_name = canonical_name,
                family_name = family_name,
                conversion_name = conversion_name,
                conversion_type = conversion_type,
                live = True,
            )

    alternatives = []

    is_dict = type(alternative_params) == dict
    for i, content in enumerate(alternative_params):

        alternatives.append(
                _GAEBingoAlternative(
                        key_name = _GAEBingoAlternative.key_for_experiment_name_and_number(experiment_name, i),
                        parent = experiment,
                        experiment_name = experiment.name,
                        number = i,
                        pickled_content = pickle_util.dump(content),
                        live = True,
                        weight = alternative_params[content] if is_dict else 1,
                    )
                )

    return experiment, alternatives

########NEW FILE########
__FILENAME__ = persist
"""Persist tools are used to continually persist data from gae/bingo's caches.

The current persistence technique works by chaining together task queue tasks.
Each task loads all current memcached gae/bingo data and stores it in the
datastore. At the end of each persist task, a new task is queued up. In this
way, persistence should be happening 'round the clock.

In the event that the persist chain has broken down at some point due to a
problem we didn't foresee (gasp!), a one-per-minute cron job will be hitting
GuaranteePersistTask and attempting to re-insert any missing persist task.
"""
import datetime
import logging
import os
import time

from google.appengine.api import datastore_errors
from google.appengine.api import taskqueue
from google.appengine.ext import deferred
from google.appengine.ext import ndb
from google.appengine.ext.webapp import RequestHandler

import cache
from config import config
import instance_cache
import request_cache


class _GAEBingoPersistLockEntry(ndb.Model):
    """A db entry used for creating a lock. See PersistLock for details.

    TODO(benkomalo): this is used in place of a memcache based lock, since we
    were seeing fairly constant, spontaneous evictions of the memcache entry
    within a matter of seconds, making the lock unreliable. Using a db entity
    for locking is non-ideal, and can hopefully be changed later.
    """

    # Can be "None" to signify the lock is not taken. Otherwise, if non-empty,
    # this means the lock has been taken and will expire at the specified time.
    expiry = ndb.DateTimeProperty(indexed=False)


class PersistLock(object):
    """PersistLock makes sure we're only running one persist task at a time.

    It can also be acquired to temporarily prevent persist tasks from running.
    """

    KEY = "_gae_bingo_persist_lock"

    def __init__(self, key=KEY):
        self._entity = None
        self._key = key

    def take(self, lock_timeout=60):
        """Take the gae/bingo persist lock.

        This is only a quick, one-time attempt to take the lock. This doesn't
        spin waiting for the lock at all, because we often expect another
        persist to already be running, and that's ok.

        This lock will expire on its own after a timeout. We do this to avoid
        completely losing the lock if some bug causes the lock to not be
        released.

        Arguments:
            lock_timeout -- how long in seconds the lock should be valid for
                after being successful in taking it
        Returns:
            True if lock successfully taken, False otherwise.
        """
        def txn():
            entity = _GAEBingoPersistLockEntry.get_or_insert(
                    self._key,
                    expiry=None)

            if entity.expiry and entity.expiry > datetime.datetime.utcnow():
                return None
            entity.expiry = (datetime.datetime.utcnow() +
                             datetime.timedelta(seconds=lock_timeout))
            entity.put()
            return entity

        try:
            self._entity = ndb.transaction(txn, retries=0)
        except datastore_errors.TransactionFailedError, e:
            # If there was a transaction collision, it probably means someone
            # else acquired the lock. Just wipe out any old values and move on.
            self._entity = None
        return self._entity is not None

    def spin_and_take(self, attempt_timeout=60, lock_timeout=60):
        """Take the gae/bingo persist lock, hard spinning until success.

        This is essentially used for clients interested in altering bingo
        data without colliding with the persist tasks.

        Arguments:
            attempt_timeout -- how long in seconds to try to take the
                lock before giving up and bailing
            lock_timeout -- how long in seconds the lock should be valid for
                after being successful in taking it
        Returns:
            True if lock successfully taken, False otherwise.
        """

        # Just use wall clock time for the attempt_timeout
        start = time.time()

        attempts = 0
        while time.time() - start < attempt_timeout:
            attempts += 1
            if self.take(lock_timeout):
                logging.info("took PersistLock after %s attempts" % attempts)
                return True
        logging.error("Failed to take PersistLock after %s attempts" %
                      attempts)
        return False

    def is_active(self):
        return self._entity is not None

    def release(self):
        """Release the gae/bingo persist lock."""
        if self.is_active():
            self._entity.expiry = None
            self._entity.put()
            self._entity = None


def persist_task():
    """Persist all gae/bingo cache entities to the datastore.

    After persisting, this task should queue itself up for another run quickly
    thereafter.

    This function uses a lock to make sure that only one persist task
    is running at a time.
    """
    lock = PersistLock()

    # Take the lock (only one persist should be running at a time)
    if not lock.take():
        logging.info("Skipping gae/bingo persist, persist lock already owned.")
        return

    logging.info("Persisting gae/bingo state from memcache to datastore")

    try:
        # Make sure request and instance caches are flushed, because this task
        # doesn't go through the normal gae/bingo WSGI app which is wrapped in
        # middleware. Regardless, we want to flush instance cache so that we're
        # persisting the current shared memcache state of all exercises to the
        # datastore.
        request_cache.flush_request_cache()
        instance_cache.flush()

        cache.BingoCache.get().persist_to_datastore()
        cache.BingoIdentityCache.persist_buckets_to_datastore()
    finally:
        # Always release the persist lock
        lock.release()

    # In production, at the end of every persist task, queue up the next one.
    # An unbroken chain of persists should always be running.
    if not os.environ["SERVER_SOFTWARE"].startswith('Development'):
        queue_new_persist_task()


def queue_new_persist_task():
    """Queue up a new persist task on the task queue via deferred library.

    These tasks should fire off immediately. If they're being backed off by GAE
    due to errors, they shouldn't try less frequently than once every 60
    seconds."""
    try:
        deferred.defer(persist_task, _queue=config.QUEUE_NAME,
            _retry_options=taskqueue.TaskRetryOptions(max_backoff_seconds=60))
    except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstonedTaskError):
        logging.info("Task for gae/bingo persist already exists.")


class GuaranteePersistTask(RequestHandler):
    """Triggered by cron, this GET handler makes sure a persist task exists.

    This should be triggered once every minute. We expect the vast majority of
    this handler's attempts to queue up a new persist task to be unable to grab
    the PersistLock, which is expected.

    Since persist tasks always queue up another task at the end of their job,
    there should be an unbroken chain of tasks always running.
    GuaranteePersistTask is just an extra safety measure in case something has
    gone terribly wrong with task queues and the persist task queue chain was
    broken.
    """
    def get(self):
        queue_new_persist_task()

########NEW FILE########
__FILENAME__ = pickle_util
"""Utility functions for pickling and unpickling.

These provide a thin wrapper around pickle.dumps and loads, but
automatically pick a fast pickle implementation and an efficient
pickle version.

Most important, these utilities deal with class renaming.  Sometimes
database entities are pickled -- see exercise_models.UserExercise,
which pickles AccuracyModel.  If we renamed AccuracyModel -- even just
by moving it to another location -- then unpickling UserExercise would
break.  To fix it, we keep a map in this file of oldname->newname.
Then, whenever we unpickle an object and see oldname, we can
instantiate a newname instead.
"""

# The trick we use to do the classname mapping requires us to use
# cPickle in particular, not pickle.  That's ok.
import cPickle
import cStringIO
import sys

# Provide some of the symbols from pickle so we can be a drop-in replacement.
from pickle import PicklingError   # @UnusedImport


# To update this: if you rename a subclass of db.model, add a new entry:
#   (old_modules, old_classname) -> (new_modules, new_classname)
# If you later want to rename newname to newername, you should add
#   (new_modules, new_classname) -> (newer_modules, newer_classname)
# but also modify the existing oldname entry to be:
#   (old_modules, old_classname) -> (newer_modules, newer_classname)
_CLASS_RENAME_MAP = {
    ('accuracy_model.accuracy_model', 'AccuracyModel'):
    ('exercises.accuracy_model', 'AccuracyModel'),

    ('accuracy_model', 'AccuracyModel'):
    ('exercises.accuracy_model', 'AccuracyModel'),
}


def _renamed_class_loader(module_name, class_name):
    """Return a class object for class class_name, loaded from module_name.

    The trick here is we look in _CLASS_RENAME_MAP before doing
    the loading.  So even if the class has moved to a different module
    since when this pickled object was created, we can still load it.
    """
    (actual_module_name, actual_class_name) = _CLASS_RENAME_MAP.get(
        (module_name, class_name),   # key to the map
        (module_name, class_name))   # what to return if the key isn't found

    # This is taken from pickle.py:Unpickler.find_class()
    __import__(actual_module_name)   # import the module if necessary
    module = sys.modules[actual_module_name]
    return getattr(module, actual_class_name)


def dump(obj):
    """Return a pickled string of obj: equivalent to pickle.dumps(obj)."""
    return cPickle.dumps(obj, cPickle.HIGHEST_PROTOCOL)


def load(s):
    """Return an unpickled object from s: equivalent to pickle.loads(s)."""
    unpickler = cPickle.Unpickler(cStringIO.StringIO(s))
    # See http://docs.python.org/library/pickle.html#subclassing-unpicklers
    unpickler.find_global = _renamed_class_loader
    return unpickler.load()

########NEW FILE########
__FILENAME__ = plots
import datetime
import time

from .cache import BingoCache
from .models import _GAEBingoSnapshotLog

def get_experiment_timeline_data(experiment, alternatives):
    query = _GAEBingoSnapshotLog.all().ancestor(experiment)
    query.order('-time_recorded')
    experiment_snapshots = query.fetch(1000)

    experiment_data_map = {}
    experiment_data = []

    def get_alt_str(n):
        for alt in alternatives:
            if alt.number == n:
                return alt.pretty_content
        return "Alternative #" + str(n)

    for snapshot in experiment_snapshots:
        n = snapshot.alternative_number

        if n not in experiment_data_map:
            data = {
                "name": get_alt_str(n),
                "data": []
            }
            experiment_data.append(data)
            experiment_data_map[n] = data

        utc_time = time.mktime(snapshot.time_recorded.timetuple()) * 1000

        experiment_data_map[n]["data"].append([
            utc_time,
            snapshot.participants,
            snapshot.conversions
        ])

    # add an extra data point to each series that represents the latest counts
    # this relies on the alternatives parameter being prefilled by the caller
    if experiment.live:
        utcnow = time.mktime(datetime.datetime.utcnow().timetuple()) * 1000
        for series in experiment_data:
            alt = next(a for a in alternatives
                       if get_alt_str(a.number) == series["name"])
            series["data"].append([utcnow, alt.participants, alt.conversions])

    return experiment_data

########NEW FILE########
__FILENAME__ = redirect
import urlparse

from google.appengine.ext.webapp import RequestHandler

from config import config
import custom_exceptions
import os
from .gae_bingo import bingo, _iri_to_uri

class Redirect(RequestHandler):
    def get(self):
        """ Score conversions and redirect as specified by url params

        Expects a 'continue' url parameter for the destination,
        and a 'conversion_name' url parameter for each conversion to score.
        """
        cont = self.request.get('continue', default_value='/')

        # Check whether redirecting to an absolute or relative url
        netloc = urlparse.urlsplit(cont).netloc
        if (netloc and
                netloc != os.environ["HTTP_HOST"] and
                not config.is_safe_hostname(netloc)):
            # Disallow open redirects to other domains.
            raise custom_exceptions.InvalidRedirectURLError(
                    "Redirecting to an absolute url is not allowed.")

        conversion_names = self.request.get_all('conversion_name')

        if len(conversion_names):
            bingo(conversion_names)

        self.redirect(_iri_to_uri(cont))

########NEW FILE########
__FILENAME__ = request_cache
"""Routines for request-level caching.

The request-level cache is set up before and cleared after every
request by middleware.

Never assign to request_cache.cache when using webapp2_extras.local
for thread-safety. It is a thread-local proxy object that will no
longer be thread-safe if overwritten.

The cache interface is a dict:

   request_cache.cache['key'] = 'value'
   if 'key' in request_cache.cache:
      value = request_cache.cache['key']
"""

import logging

try:
    import webapp2_extras.local
    _local = webapp2_extras.local.Local()
    _local.cache = {}
    # cache is a LocalProxy. it forwards all operations (except
    # assignment) to the object that _local.cache is bound to.
    cache = _local('cache')
except ImportError:
    logging.warning("webapp2_extras.local is not available "
                    "so gae_bingo won't be thread-safe!")
    _local = None
    cache = {}


def flush_request_cache():
    """Release referenced data from the request cache."""
    if _local is not None:
        _local.__release_local__()
        _local.cache = {}
    else:
        cache = {}

########NEW FILE########
__FILENAME__ = stats
import logging

# This file in particular is almost a direct port from Patrick McKenzie's A/Bingo's abingo/lib/abingo/statistics.rb

HANDY_Z_SCORE_CHEATSHEET = [[0.10, 1.29], [0.05, 1.65], [0.01, 2.33], [0.001, 3.08]]

PERCENTAGES = {0.10: '90%', 0.05: '95%', 0.01: '99%', 0.001: '99.9%'}

DESCRIPTION_IN_WORDS = {
        0.10: 'fairly confident', 0.05: 'confident',
        0.01: 'very confident', 0.001: 'extremely confident'
        }

def zscore(alternatives):

    if len(alternatives) != 2:
        raise Exception("Sorry, can't currently automatically calculate statistics for A/B tests with > 2 alternatives. Need to brush up on some statistics via http://www.khanacademy.org/math/statistics before implementing.")

    if alternatives[0].participants == 0 or alternatives[1].participants == 0:
        raise Exception("Can't calculate the z score if either of the alternatives lacks participants.")

    cr1 = alternatives[0].conversion_rate
    cr2 = alternatives[1].conversion_rate

    n1 = alternatives[0].participants
    n2 = alternatives[1].participants

    numerator = cr1 - cr2
    frac1 = cr1 * (1 - cr1) / float(n1)
    frac2 = cr2 * (1 - cr2) / float(n2)

    if frac1 + frac2 == 0:
        return 0
    elif frac1 + frac2 < 0:
        raise Exception("At the moment we can't calculate the z score of experiments that allow multiple conversions per participant.")

    return numerator / float((frac1 + frac2) ** 0.5)

def p_value(alternatives):

    index = 0
    z = zscore(alternatives)
    z = abs(z)

    found_p = None
    while index < len(HANDY_Z_SCORE_CHEATSHEET):
        if z > HANDY_Z_SCORE_CHEATSHEET[index][1]:
            found_p = HANDY_Z_SCORE_CHEATSHEET[index][0]
        index += 1

    return found_p

def is_statistically_significant(p = 0.05):
    return p_value <= p

def describe_result_in_words(alternatives):

    try:
        z = zscore(alternatives)
    except Exception, e:
        return str(e)

    p = p_value(alternatives)

    words = ""

    if alternatives[0].participants < 10 or alternatives[1].participants < 10:
        words += "Take these results with a grain of salt since your samples are so small: "

    best_alternative = max(alternatives, key=lambda alternative: alternative.conversion_rate)
    worst_alternative = min(alternatives, key=lambda alternative: alternative.conversion_rate)

    words += """The best alternative you have is:[%(best_alternative_content)s], which had 
    %(best_alternative_conversions)s conversions from %(best_alternative_participants)s participants 
    (%(best_alternative_pretty_conversion_rate)s).  The other alternative was [%(worst_alternative_content)s], 
    which had %(worst_alternative_conversions)s conversions from %(worst_alternative_participants)s participants 
    (%(worst_alternative_pretty_conversion_rate)s).  """ % {
                "best_alternative_content": best_alternative.content,
                "best_alternative_conversions": best_alternative.conversions,
                "best_alternative_participants": best_alternative.participants,
                "best_alternative_pretty_conversion_rate": best_alternative.pretty_conversion_rate,
                "worst_alternative_content": worst_alternative.content,
                "worst_alternative_conversions": worst_alternative.conversions,
                "worst_alternative_participants": worst_alternative.participants,
                "worst_alternative_pretty_conversion_rate": worst_alternative.pretty_conversion_rate,
            }

    if p is None:
        words += "However, this difference is not statistically significant."
    else:
        words += """This difference is %(percentage_likelihood)s likely to be statistically significant, which means you can be 
        %(description)s that it is the result of your alternatives actually mattering, rather than 
        being due to random chance.  However, this statistical test can't measure how likely the currently 
        observed magnitude of the difference is to be accurate or not.  It only says "better," not "better 
        by so much.\"""" % {
                    "percentage_likelihood": PERCENTAGES[p],
                    "description": DESCRIPTION_IN_WORDS[p],
                }

    return words


########NEW FILE########
__FILENAME__ = synchronized_counter
"""Synchronized counters are memcache counters that get evicted synchronously.

In other words, you can use synchronized counters to track two different
incrementing numbers, A and B, that should be evicted from memcache
consistently w/r/t each other. This is especially useful when you need a fast
atomic incrementor (which memcache's incr() provides) while also maintaining
two or more numbers that are related to each other.

There are two nouns you should think of when reading through this file,
"combinations" and "counters"

    - "Combinations" are groups of up to 4 counters that stay in memcache
      together and are evicted at the same time.

    - "Counters" are simple incrementing counters.

You get the following benefits when using synchronized counters:

    - If one counter in a combination is present in memcache, all counters in
      that combination are present.
    
    - If one counter in a combination is evicted from memcache, all counters are
      evicted.

In order to achieve this, these counters suffer from some limitations:

    - Each combination can only have four individual counters.

    - Counters have a maximum value of 65,535. *Client code is responsible for
      calling pop_counters to get and reset the current counter state when
      appropriate, otherwise these counters will rollover over 65,535 and reset
      their entire combination of counters. See below.*

    - Counters can still be randomly evicted by memcache -- this does not make
      memcache more stable or persistent. This only guarantees that all
      counters in a single combination will be evicted at the same time.

Example usage:

    # Create and increment the 0th individual counter in a combination of
    # counters called "GorillaCombination"
    SynchronizedCounter.incr_async("GorillaCombination", 0)

    # Increment the 2nd individual counter as well. Now the 0th and 2nd
    # counters in "GorillaCombination" will remain in (or be evicted from)
    # memcache together.
    SynchronizedCounter.incr_async("GorillaCombination", 2)

    # Get the current value of the 2nd counter in "GorillaCombination" -- in
    # this case, it will return 1.
    current_count_2 = SynchronizedCounter.get("GorillaCombination", 2)

    # Get all current gorilla counts and pop them off the accumulating counters
    # This return value should be: {"GorillaCombination": [0, 0, 1, 0]}
    gorilla_counts = SynchronizedCounter.pop_counters(["GorillaCombination"])

    # ...and after the pop, the counters will be reset and this assert should
    # succeed.
    current_count_2 = SynchronizedCounter.get("GorillaCombination", 2)
    assertEqual(current_count_2, 0)
"""
import logging

from google.appengine.api import memcache
from google.appengine.ext import ndb


# total # of bits in a memcache incr() int
BITS_IN_MEMCACHE_INT = 64

# number of counters in each combination
COUNTERS_PER_COMBINATION = 4

# number of bits in each counter in the combination
BITS_PER_COUNTER = BITS_IN_MEMCACHE_INT / COUNTERS_PER_COMBINATION

# max value each counter can represent
MAX_COUNTER_VALUE = 2**BITS_PER_COUNTER - 1

# above this value, counters will start warning of rollover possibilities
WARNING_HIGH_COUNTER_VALUE = 2**(BITS_PER_COUNTER - 1)


class SynchronizedCounter(object):
    """Tool for managing combinations of synchronized memcache counters."""

    @staticmethod
    def get(key, number):
        """Return value of the n'th counter in key's counter combination.
        
        Args:
            key: name of the counter combination
            number: n'th counter value being queried
        """
        if not (0 <= number < COUNTERS_PER_COMBINATION):
            raise ValueError("Invalid counter number.")

        # Get the combined count for this counter combination
        combined_count = long(memcache.get(key) or 0)

        # Return the single counter value for the n'th counter
        return SynchronizedCounter._single_counter_value(combined_count, number)

    @staticmethod
    def _single_counter_value(combined_count, number):
        """Return the n'th counter value from the combination's total value.
        
        Args:
            combined_count: combined count value for the entire counter
                combination, usually taken directly from memcache
            number: n'th counter value being queried
        """
        if combined_count is None:
            return 0

        # Shift the possiblty-left-shifted bits over into the rightmost spot
        shifted_count = combined_count >> (number * BITS_PER_COUNTER)

        # And mask off all bits other than the n'th counter's bits
        mask = 2**BITS_PER_COUNTER - 1
        return shifted_count & mask

    @staticmethod
    @ndb.tasklet
    def incr_async(key, number, delta=1):
        """Increment the n'th counter in key's counter combination.
        
        Args:
            key: name of the counter combination
            number: n'th counter value being incremented
            delta: amount to increment by
        """
        if not (0 <= number < COUNTERS_PER_COMBINATION):
            raise ValueError("Invalid counter number.")

        if delta < 0:
            raise ValueError("Cannot decrement synchronized counters.")

        # We want to increment the counter, but we need to increment the
        # counter that's sitting in this combination's correct bit position. So
        # we shift our increment-by-1 to the left by the number of bits
        # necessary to get to the correct counter.
        delta_base = 1 << (number * BITS_PER_COUNTER)
        delta_shifted = delta_base * delta

        ctx = ndb.get_context()
        combined_count = yield ctx.memcache_incr(key, delta=delta_shifted,
                initial_value=0)

        if combined_count is None:
            # Memcache may be down and returning None for incr.
            raise ndb.Return(False)

        # If the value we get back from memcache's incr is less than the delta
        # we sent, then we've rolled over this counter's maximum value (2^16).
        # That's a problem, because it bleeds data from this counter into the
        # next one in its combination.
        #
        # As noted above, it is the client code's responsibility to call
        # pop_counters frequently enough to prevent this from happening.
        #
        # However, if this does happen, we wipe this entire corrupted counter
        # from memcache and act just as if the memcache key was randomly
        # evicted.
        count = SynchronizedCounter._single_counter_value(combined_count,
                number)
        if count < delta:
            # This is an error worth knowing about in our logs
            logging.error("SynchronizedCounter %s exceeded its maximum value" %
                    key)
            # Evict corrupted data from memcache
            SynchronizedCounter.delete_multi([key])
        elif count > WARNING_HIGH_COUNTER_VALUE:
            logging.warning("SynchronizedCounter %s approaching max value" %
                    key)

        raise ndb.Return(True)

    @staticmethod
    def pop_counters(keys):
        """Return all counters in provided combinations and reset their counts.

        This will return a dict mapping the provided key values to a list of
        each of their current counter values.
        Example return value: {
            "MonkeyCombination": [1, 5, 0, 12],
            "GorillaCombination": [0, 0, 0, 9],
        }

        This will also clear out the current counts for all combinations listed
        in keys, so after calling this the counts for each specified
        combination's counter should be 0.

        Note: while pop_counters tries to do the get and pop as atomically as
        possible, it is not truly atomic. This means there are rare edge cases
        during which problematic memcache evictions and incr()s can happen
        between the results being retrieved and the counters being popped. When
        this happens, we detect the situation and pretend like this combination
        of counters has simply been evicted from memcache (by deleting the
        combination of counters). This situation should hopefully be very rare.

        Args:
            keys: list of names of counter combinations
        """
        results = {k: [0] * COUNTERS_PER_COMBINATION for k in keys}

        # Grab all accumulating counters...
        combined_counters = memcache.get_multi(keys)

        # ...and immediately offset them by the inverse of their current counts
        # as quickly as possible.
        negative_offsets = {k: -1 * count
                for k, count in combined_counters.iteritems()}
        offset_results = memcache.offset_multi(negative_offsets)

        # Now that we've tried to pop the counter values from the accumulators,
        # make sure that none of the pops caused an overflow rollover due to
        # the race condition described in the above docstring.
        for key in offset_results:
            offset_counter = offset_results[key]
            for i in range(COUNTERS_PER_COMBINATION):
                count = SynchronizedCounter._single_counter_value(
                        offset_counter, i)
                if count > WARNING_HIGH_COUNTER_VALUE:
                    # We must've rolled a counter over backwards due to the
                    # memcache race condition described above. Warn and clear
                    # this counter.
                    #
                    # We don't expect this to happen, but if it does we should
                    # know about it without crashing on the user. See above
                    # explanation.
                    #
                    # TODO(kamens): find a nicer way to protect this scenario
                    logging.error("SynchronizedCounter %s rolled over on pop" %
                            key)
                    SynchronizedCounter.delete_multi([key])

        # Prepare popped results in form {
        #   "counter combination A": [<counter 1>, ..., <counter 4>],
        #   "counter combination B": [<counter 1>, ..., <counter 4>],
        # }
        for key in combined_counters:
            combined_counter = combined_counters[key]

            for i in range(COUNTERS_PER_COMBINATION):
                results[key][i] = SynchronizedCounter._single_counter_value(
                        combined_counter, i)

        return results

    @staticmethod
    def delete_multi(keys):
        """Delete all counters in provided keys."""
        memcache.delete_multi(keys)


########NEW FILE########
__FILENAME__ = main
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import gae_bingo.config
import gae_bingo.identity
import gae_bingo.middleware


class Homepage(webapp.RequestHandler):
    def get(self):
        pass


class Identity(webapp.RequestHandler):
    def get(self):
        self.response.out.write(gae_bingo.identity.identity())

application = webapp.WSGIApplication([
    ("/identity", Identity),
    ("/.*", Homepage),
])
application = gae_bingo.middleware.GAEBingoWSGIMiddleware(application)
application = gae_bingo.config.config.wrap_wsgi_app(application)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = pickle_util
# TODO(chris): break dependency on KA website code. This file is specific to
# the KA website and is required by bingo.

import cPickle as pickle

load = pickle.loads
dump = pickle.dumps

########NEW FILE########
__FILENAME__ = endtoend_main
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from .. import config, middleware

import run_step


class Homepage(webapp.RequestHandler):
    def get(self):
        pass


application = webapp.WSGIApplication([
    ("/gae_bingo/tests/run_step", run_step.RunStep),
    ("/.*", Homepage),
])
application = middleware.GAEBingoWSGIMiddleware(application)
application = config.config.wrap_wsgi_app(application)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = endtoend_test
import ast
import base64
import cookielib
import json
import os
import random
import unittest
import urllib2

import google.appengine.ext.deferred

from testutil import gae_model
from testutil import dev_appserver_utils
from testutil import random_util
from testutil import taskqueue_util
from testutil import testsize
from testutil import wsgi_test_utils

import endtoend_main
from .. import main as gae_bingo_main

_CURRENT_DIR = os.path.dirname(__file__)


class AppServerTests(unittest.TestCase):
    """The test case contains tests that require dev_appserver to run.

    TODO(chris): remove the need for the app server entirely. The
    dependencies for login tests in particular are hard to break.
    """

    def __init__(self, *args, **kwargs):
        super(AppServerTests, self).__init__(*args, **kwargs)
        self.last_opener = None

    def fetch(self, url, use_last_cookies=False):
        if not use_last_cookies or self.last_opener is None:
            cj = cookielib.CookieJar()
            self.last_opener = urllib2.build_opener(
                urllib2.HTTPCookieProcessor(cj))
        url = "%s%s" % (dev_appserver_utils.appserver_url, url)
        req = self.last_opener.open(url)
        try:
            return req.read()
        finally:
            req.close()

    @testsize.large()
    def setUp(self):
        super(AppServerTests, self).setUp()
        appdir = os.path.join(_CURRENT_DIR, 'app')
        tmpdir = dev_appserver_utils.create_sandbox(root=appdir)
        # Symlink gae_bingo into the test app's sandbox. We don't want
        # to keep a permanent symlink in the source tree because when
        # tools/runtests.py walks the tree to find tests, this would
        # create a cycle.
        os.symlink(os.path.join(_CURRENT_DIR, '..'),
                   os.path.join(tmpdir, 'gae_bingo'))
        dev_appserver_utils.start_dev_appserver_in_sandbox(tmpdir, root=appdir)

    def tearDown(self):
        super(AppServerTests, self).tearDown()
        # Let's emit the dev_appserver's logs in case those are helpful.
        # TODO(chris): only emit if there are >0 failures?
        print
        print '---------------- START DEV_APPSERVER LOGS ---------------------'
        print open(dev_appserver_utils.dev_appserver_logfile_name()).read()
        print '----------------- END DEV_APPSERVER LOGS ----------------------'
        dev_appserver_utils.stop_dev_appserver()

    def test_identity_with_login(self):
        # Ensure identity works correctly and consistently after login.
        last_id = None
        for _ in xrange(5):
            # Randomly generate an ID so we have a good chance of
            # having a new one.  If that assumption is wrong, the test
            # will fail -- clear the datastore to increase chances of
            # working.
            user = base64.urlsafe_b64encode(os.urandom(30)) + "%40example.com"
            self.fetch("/")  # Load / to get ID assigned
            first_id = self.fetch("/identity", use_last_cookies=True)
            self.assertNotEqual(first_id, last_id)
            self.fetch(
                "/_ah/login?email=" + user + "&action=Login&continue=%2Fpostlogin",
                use_last_cookies=True)
            # Now make sure the ID is consistent
            last_id = self.fetch("/identity", use_last_cookies=True)
            self.assertEqual(first_id, last_id)


class EndToEndTests(gae_model.GAEModelTestCase):
    def setUp(self):
        super(EndToEndTests, self).setUp(
            # TODO(chris): remove strong consistency. When I ported
            # the tests some required this to work.
            db_consistency_probability=1)
        self.runstep_client = wsgi_test_utils.TestApp(
            endtoend_main.application)
        self.bingo_client = wsgi_test_utils.TestApp(gae_bingo_main.application)
        random_util.stub_os_urandom(42)

    def tearDown(self):
        super(EndToEndTests, self).tearDown()
        random_util.unstub_os_urandom()

    def run_tasks(self):
        taskqueue_util.execute_until_empty(
            self.testbed,
            wsgi_test_utils.SetUpAppEngineEnvFromWsgiEnv(
                google.appengine.ext.deferred.application))

    def fetch_bingo_redirect(self, url, use_runstep_cookies=False):
        if use_runstep_cookies:
            self.bingo_client.cookies = self.runstep_client.cookies.copy()
        response = self.bingo_client.get(url, status=302)
        if use_runstep_cookies:
            self.runstep_client.cookies = self.bingo_client.cookies.copy()
        return response.headers['Location']

    def fetch_runstep_json(self, step="", data=None, headers=None,
                           bot=False, url=None, use_last_cookies=False):
        if not use_last_cookies:
            self.clear_runstep_cookies()
        if bot:
            if headers is None:
                headers = {}
            headers["User-agent"] = "monkeysmonkeys Googlebot monkeysmonkeys"
        if url is None:
            if data is None:
                data = {}
            data["step"] = step
            url = "/gae_bingo/tests/run_step"
        response = self.runstep_client.get(url, params=data, headers=headers,
                                           status=200)
        try:
            return json.loads(response.body)
        except ValueError:
            return None

    def clear_runstep_cookies(self):
        self.runstep_client.reset()

    def test_cookie_identity(self):
        # Identity should be carried over due to cookie
        ident1 = self.fetch_runstep_json("get_identity")
        ident2 = self.fetch_runstep_json("get_identity", use_last_cookies=True)
        self.assertEqual(ident1, ident2)

        # If identity is not in the cookie, a new one is generated
        ident1 = self.fetch_runstep_json("get_identity")
        ident2 = self.fetch_runstep_json("get_identity")
        self.assertNotEqual(ident1, ident2)

    def test_conversions(self):
        # We're going to try to add a conversion to the experiment
        self.assertIn(
            self.fetch_runstep_json("participate_in_hippos"),
            [True, False])
    
        self.assertTrue(self.fetch_runstep_json(
            "convert_in", {"conversion_name": "hippos_binary"},
            use_last_cookies=True))
    
        # Make sure participant counts are right
        self.assertEqual(1, self.fetch_runstep_json(
                                "count_participants_in",
                                {"experiment_name": "hippos (hippos_binary)"},
                                use_last_cookies=True))
        self.assertEqual(1, self.fetch_runstep_json(
                                "count_participants_in",
                                {"experiment_name": "hippos (hippos_counting)"},
                                use_last_cookies=True))
        # Make sure we have the right number of conversions
        dict_conversions_server = self.fetch_runstep_json(
                             "count_conversions_in",
                             {"experiment_name": "hippos (hippos_binary)"},
                             use_last_cookies=True)
        self.assertEqual(1, sum(dict_conversions_server.values()))
    
        dict_conversions_server = self.fetch_runstep_json(
                            "count_conversions_in",
                            {"experiment_name": "hippos (hippos_counting)"},
                            use_last_cookies=True)
        self.assertEqual(0, sum(dict_conversions_server.values()))
    
        self.assertIn(self.fetch_runstep_json("add_conversions", use_last_cookies=True), [True, False])
        self.assertEqual(3, self.fetch_runstep_json("count_experiments", use_last_cookies=True))
    
        # make sure that we have the /right/ experiments
        self.assertEqual(
            set(["hippos (hippos_binary)",
                 "hippos (hippos_counting)",
                 "hippos (rhinos_counting)"]),
            set(ast.literal_eval(self.fetch_runstep_json(
                                     "get_experiments",
                                     use_last_cookies=True)).keys()))
        
        self.assertTrue(self.fetch_runstep_json(
                            "convert_in",
                            {"conversion_name": "rhinos_counting"},
                            use_last_cookies=True))
    
        dict_conversions_server = self.fetch_runstep_json(
                            "count_conversions_in",
                            {"experiment_name": "hippos (hippos_binary)"})
        self.assertEqual(1, sum(dict_conversions_server.values()))
    
        dict_conversions_server = self.fetch_runstep_json(
                            "count_conversions_in",
                            {"experiment_name": "hippos (hippos_counting)"},
                            use_last_cookies=True)
        self.assertEqual(0, sum(dict_conversions_server.values()))
        
        dict_conversions_server = self.fetch_runstep_json(
                            "count_conversions_in",
                            {"experiment_name": "hippos (rhinos_counting)"},
                            use_last_cookies=True)
        
        self.assertEqual(1, sum(dict_conversions_server.values()))

    def test_conversions_with_user_switching(self):
        # Now try the same, but with switching users
        self.assertIn(self.fetch_runstep_json("participate_in_hippos"), [True, False])
        
        self.assertTrue(self.fetch_runstep_json(
                            "convert_in",
                            {"conversion_name":
                             "hippos_binary"}, use_last_cookies=True))
    
        self.assertIn(self.fetch_runstep_json("participate_in_hippos", use_last_cookies=False),
                      [True, False])
    
        self.assertIn(self.fetch_runstep_json("add_conversions", use_last_cookies=True),
                      [True, False])
    
        self.assertTrue(self.fetch_runstep_json(
                            "convert_in",
                            {"conversion_name":
                             "rhinos_counting"}, use_last_cookies=True))
        self.assertEqual(2, self.fetch_runstep_json(
                                "count_participants_in",
                                {"experiment_name": "hippos (hippos_binary)"}))
        self.assertEqual(1, self.fetch_runstep_json(
                                "count_participants_in",
                                {"experiment_name": "hippos (rhinos_counting)"}))
        dict_conversions_server = self.fetch_runstep_json(
                                     "count_conversions_in",
                                     {"experiment_name": "hippos (hippos_binary)"})
        self.assertEqual(1, sum(dict_conversions_server.values()))
        dict_conversions_server = self.fetch_runstep_json(
                                "count_conversions_in",
                                {"experiment_name": "hippos (rhinos_counting)"})
        self.assertEqual(1, sum(dict_conversions_server.values()))

    def test_conversions_with_redirects(self):
        # Test constructing a redirect URL that converts in monkey and chimps
        redirect_url_monkeys = self.fetch_runstep_json("create_monkeys_redirect_url")
        self.assertEqual(
            redirect_url_monkeys,
            "/gae_bingo/redirect?continue=/gae_bingo&conversion_name=monkeys")
    
        redirect_url_chimps = self.fetch_runstep_json("create_chimps_redirect_url")
        self.assertEqual(redirect_url_chimps,
                         ("/gae_bingo/redirect?continue=/gae_bingo&"
                          "conversion_name=chimps_conversion_1&"
                          "conversion_name=chimps_conversion_2"))
    
        # Test participating in monkeys and chimps once,
        # and use previously constructed redirect URLs to convert
        self.assertIn(self.fetch_runstep_json("participate_in_monkeys"), [True, False])
        self.fetch_bingo_redirect(redirect_url_monkeys, use_runstep_cookies=True)
        self.assertIn(self.fetch_runstep_json("participate_in_chimpanzees"), [True, False])
        self.fetch_bingo_redirect(redirect_url_chimps, use_runstep_cookies=True)
    
        # Make sure there's a single participant and conversion in monkeys
        self.assertEqual(1, self.fetch_runstep_json("count_participants_in",
                                          {"experiment_name": "monkeys"}))
        dict_conversions_server = self.fetch_runstep_json("count_conversions_in",
                                               {"experiment_name": "monkeys"})
        self.assertEqual(1, sum(dict_conversions_server.values()))
    
        # Make sure there's a single participant and two conversions in chimps
        self.assertEqual(1, self.fetch_runstep_json(
                                "count_participants_in",
                                {"experiment_name":
                                 "chimpanzees (chimps_conversion_1)"}))
        dict_conversions_server = self.fetch_runstep_json(
                                    "count_conversions_in",
                                    {"experiment_name":
                                        "chimpanzees (chimps_conversion_1)"})
        self.assertEqual(1, sum(dict_conversions_server.values()))
        dict_conversions_server = self.fetch_runstep_json(
                                    "count_conversions_in",
                                    {"experiment_name":
                                     "chimpanzees (chimps_conversion_2)"})
        self.assertEqual(1, sum(dict_conversions_server.values()))

    def test_too_many_alternatives(self):
        def participation_crash():
            self.fetch_runstep_json("participate_in_skunks")
        self.assertRaises(Exception, participation_crash)

    def test_simultaneous_experiment_creation(self):
        for _ in range(0, 3):
            # Start an experiment on a faked "new instance"
            self.assertIn(self.fetch_runstep_json(
                "participate_in_doppleganger_on_new_instance"),
                [True, False])

            # Persist from that instance
            self.assertTrue(self.fetch_runstep_json("persist"))

        # Make sure that only one experiment has been created
        self.assertEqual(1, self.fetch_runstep_json(
            "count_doppleganger_experiments"))

    # TODO(chris): divide this up into more targeted tests.
    # TODO(kamens): add unit tests for deleting experiments.
    @testsize.medium()  # lots going on here, takes a few seconds to run.
    def test_bots_conversions_weighting_and_lifecycle(self):
        # Refresh bot's identity record so it doesn't pollute tests
        self.assertTrue(self.fetch_runstep_json("refresh_identity_record", bot=True))
    
        # Participate in experiment A, check for correct alternative
        # valuesum(core_metrics.values(), [])s being returned,
        for _ in range(0, 20):
            self.assertIn(self.fetch_runstep_json("participate_in_monkeys"), [True, False])
    
        self.assertEqual(20, self.fetch_runstep_json("count_participants_in",
                                           {"experiment_name": "monkeys"}))
    
        # Identify as a bot a couple times (response should stay the same)
        bot_value = None
        for _ in range(0, 5):
            value = self.fetch_runstep_json("participate_in_monkeys", bot=True)
            self.assertIn(value, [True, False])
    
            if bot_value is None:
                bot_value = value
    
            self.assertEqual(value, bot_value)
    
        # Check total participants in A (1 extra for bots)
        self.assertEqual(21, self.fetch_runstep_json("count_participants_in",
                                           {"experiment_name": "monkeys"}))
    
        # Participate in experiment B (responses should be "a" "b" or "c")
        for _ in range(0, 15):
            self.assertIn(self.fetch_runstep_json("participate_in_gorillas"), ["a", "b", "c"])
    
        # Participate in experiment A,
        # using cookies half of the time to maintain identity
        for i in range(0, 20):
            self.assertIn(self.fetch_runstep_json("participate_in_monkeys",
                                        use_last_cookies=(i % 2 == 1)),
                          [True, False])
        # Check total participants in A
        # (should've only added 10 more in previous step)
        self.assertEqual(31, self.fetch_runstep_json("count_participants_in",
                                           {"experiment_name": "monkeys"}))
    
        # Participate in A once more with a lot of followup, 
        # persisting to datastore and flushing memcache between followups
        for i in range(0, 10):
            self.assertIn(self.fetch_runstep_json("participate_in_monkeys",
                                        use_last_cookies=(i not in [0, 5])),
                          [True, False])
    
            if i in [1, 6]:
    
                self.assertTrue(self.fetch_runstep_json("persist", use_last_cookies=True))
    
                # Wait for task queues to run
                self.run_tasks()
    
                self.assertTrue(self.fetch_runstep_json("flush_all_cache",
                                              use_last_cookies=True))
    
        # NOTE: It's possible for this to fail sometimes--maybe a race condition?
        # TODO(kamens,josh): figure out why this happens? (Or just wait to not use
        #                     AppEngine any more)
        # Check total participants in A
        # (should've only added 2 more in previous step)
        self.assertEqual(33, self.fetch_runstep_json("count_participants_in",
                                           {"experiment_name": "monkeys"}))
    
        # Participate and convert in experiment A,
        # using cookies to tie participation to conversions,
        # tracking conversions-per-alternative
        dict_conversions = {}
        for _ in range(0, 35):
            alternative_key = str(self.fetch_runstep_json("participate_in_monkeys"))
            self.assertTrue(self.fetch_runstep_json("convert_in",
                                          {"conversion_name": "monkeys"},
                                          use_last_cookies=True))
    
            if not alternative_key in dict_conversions:
                dict_conversions[alternative_key] = 0
            dict_conversions[alternative_key] += 1
    
        # Check total conversions-per-alternative in A
        self.assertEqual(2, len(dict_conversions))
        self.assertEqual(35, sum(dict_conversions.values()))
    
        dict_conversions_server = self.fetch_runstep_json("count_conversions_in",
                                               {"experiment_name": "monkeys"})
        self.assertEqual(len(dict_conversions), len(dict_conversions_server))
    
        for key in dict_conversions:
            self.assertEqual(dict_conversions[key], dict_conversions_server[key])

        # Participate in experiment B, using cookies to maintain identity
        # and making sure alternatives for B are stable per identity
        last_response = None
        for _ in range(0, 20):
            use_last_cookies = (last_response is not None and
                                 random.randint(0, 2) > 0)
    
            current_response = self.fetch_runstep_json("participate_in_gorillas",
                                             use_last_cookies=use_last_cookies)
    
            if not use_last_cookies:
                last_response = current_response
    
            self.assertIn(current_response, ["a", "b", "c"])
            self.assertEqual(last_response, current_response)
    
        # Participate in experiment C, which is a multi-conversion experiment,
        # and occasionally convert in *one* of the conversions
        expected_conversions = 0
        for _ in range(0, 20):
            self.assertIn(self.fetch_runstep_json("participate_in_chimpanzees"), [True, False])
    
            if random.randint(0, 2) > 0:
                self.assertTrue(
                    self.fetch_runstep_json("convert_in",
                                  {"conversion_name": "chimps_conversion_2"},
                                  use_last_cookies=True))
                expected_conversions += 1
    
        # This would be random if the RNG weren't seeded.
        self.assertEqual(13, expected_conversions)
    
        # Make sure conversions for the 2nd conversion type 
        # of this experiment are correct
        dict_conversions_server = self.fetch_runstep_json(
                                     "count_conversions_in",
                                     {"experiment_name":
                                         "chimpanzees (chimps_conversion_2)"})
        self.assertEqual(expected_conversions, sum(dict_conversions_server.values()))
    
        # Make sure conversions for the 1st conversion type 
        # of this experiment are empty
        dict_conversions_server = self.fetch_runstep_json(
                                    "count_conversions_in",
                                    {"experiment_name":
                                     "chimpanzees (chimps_conversion_1)"})
        self.assertEqual(0, sum(dict_conversions_server.values()))
    
        # Test that calling bingo multiple times for a single 
        # user creates only one conversion (for a BINARY conversion type)
        self.assertIn(self.fetch_runstep_json("participate_in_chimpanzees"), [True, False])
        self.assertTrue(self.fetch_runstep_json("convert_in",
                                      {"conversion_name": "chimps_conversion_1"},
                                      use_last_cookies=True))
    
        self.assertTrue(self.fetch_runstep_json(
            "convert_in",
            {"conversion_name": "chimps_conversion_1"},
            use_last_cookies=True))
    
        dict_conversions_server = self.fetch_runstep_json(
                                    "count_conversions_in",
                                    {"experiment_name":
                                        "chimpanzees (chimps_conversion_1)"})
        self.assertEqual(1, sum(dict_conversions_server.values()))
    
        # End experiment C, choosing a short-circuit alternative
        self.fetch_runstep_json("end_and_choose",
                     {"canonical_name": "chimpanzees", "alternative_number": 1})
    
        # Make sure short-circuited alternatives for 
        # C's experiments are set appropriately
        for _ in range(0, 5):
            self.assertFalse(self.fetch_runstep_json("participate_in_chimpanzees"))
    
        # Test an experiment with a Counting type conversion 
        # by converting multiple times for a single user
        self.assertIn(self.fetch_runstep_json("participate_in_hippos"), [True, False])
    
        # Persist to the datastore before Counting stress test
        self.assertTrue(self.fetch_runstep_json("persist", use_last_cookies=True))
    
        # Wait for task queues to run
        self.run_tasks()
    
        # Hit Counting conversions multiple times
        for i in range(0, 20):
    
            if i % 3 == 0:
                # Stress things out a bit by flushing the memcache .incr() 
                # counts of each hippo alternative
                self.assertTrue(self.fetch_runstep_json("persist", use_last_cookies=True))
                self.assertTrue(self.fetch_runstep_json("flush_hippo_counts_memcache",
                                              use_last_cookies=True))
            
            elif i % 5 == 0:
                # Stress things out even more flushing the core bingo memcache
                self.assertTrue(self.fetch_runstep_json("flush_bingo_cache",
                                              use_last_cookies=True))
    
            self.assertTrue(self.fetch_runstep_json(
                "convert_in",
                {"conversion_name": "hippos_binary"},
                use_last_cookies=True))
    
            self.assertTrue(self.fetch_runstep_json(
                "convert_in",
                {"conversion_name": "hippos_counting"},
                use_last_cookies=True))
    
        dict_conversions_server = self.fetch_runstep_json(
                                    "count_conversions_in",
                                    {"experiment_name": "hippos (hippos_binary)"})
        self.assertEqual(1, sum(dict_conversions_server.values()))
        dict_conversions_server = self.fetch_runstep_json(
                                    "count_conversions_in",
                                    {"experiment_name":
                                        "hippos (hippos_counting)"})
        self.assertEqual(20, sum(dict_conversions_server.values()))
    
        # Participate in experiment D (weight alternatives), 
        # keeping track of alternative returned count.
        dict_alternatives = {}
        for _ in range(0, 75):
            alternative = self.fetch_runstep_json("participate_in_crocodiles")
            self.assertIn(alternative, ["a", "b", "c"])
    
            if not alternative in dict_alternatives:
                dict_alternatives[alternative] = 0
            dict_alternatives[alternative] += 1
    
        # Make sure weighted alternatives work -> should be a < b < c < d < e,
        # and they should all exist. This would be random if the RNG weren't
        # seeded.
        self.assertEqual(5, dict_alternatives.get("a"))
        self.assertEqual(18, dict_alternatives.get("b"))
        self.assertEqual(52, dict_alternatives.get("c"))
    
        # Check experiments count
        self.assertEqual(7, self.fetch_runstep_json("count_experiments"))
    
        # Test persist and load from DS
        self.assertTrue(self.fetch_runstep_json("persist"))
        self.assertTrue(self.fetch_runstep_json("flush_all_cache"))

        # Wait for task queues to run
        self.run_tasks()

        # Check experiments and conversion counts 
        # remain after persist and memcache flush
        self.assertEqual(7, self.fetch_runstep_json("count_experiments"))
    
        dict_conversions_server = self.fetch_runstep_json(
                                    "count_conversions_in", 
                                    {"experiment_name":
                                        "chimpanzees (chimps_conversion_2)"})
        self.assertEqual(expected_conversions, sum(dict_conversions_server.values()))
    
        # Test archiving
        self.assertTrue(self.fetch_runstep_json("archive_monkeys"))

        # Wait for eventual consistency of archived experiment
        # TODO(chris): remove dependency on db_consistency=1
    
        # Test lack of presence in normal list of experiments after archive
        self.assertNotIn("monkeys", self.fetch_runstep_json("get_experiments"))
    
        # Test presence in list of archived experiments
        self.assertIn("monkeys", self.fetch_runstep_json("get_archived_experiments"))
    
        # Test participating in monkeys once again after archiving
        # and make sure there's only one participant
        self.assertIn(self.fetch_runstep_json("participate_in_monkeys"), [True, False])
        self.assertEqual(1, self.fetch_runstep_json("count_participants_in",
                                          {"experiment_name": "monkeys"}))

########NEW FILE########
__FILENAME__ = main
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from gae_bingo.tests import RunStep
from gae_bingo import middleware

application = webapp.WSGIApplication([
    ("/gae_bingo/tests/run_step", RunStep),
])
application = middleware.GAEBingoWSGIMiddleware(application)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = run_step
import copy
import os

# use json in Python 2.7, fallback to simplejson for Python 2.5
try:
    import json
except ImportError:
    import simplejson as json

from google.appengine.ext.webapp import RequestHandler
from google.appengine.api import memcache

from gae_bingo.api import ControlExperiment
from gae_bingo.cache import BingoCache, BingoIdentityCache
from gae_bingo.gae_bingo import ab_test, bingo, choose_alternative, create_redirect_url
from gae_bingo.gae_bingo import ExperimentController
import gae_bingo.identity
from gae_bingo.models import _GAEBingoExperiment, ConversionTypes
import gae_bingo.persist
import gae_bingo.instance_cache

# See gae_bingo/tests/run_tests.py for the full explanation/sequence of these tests
# TODO(kamens): this whole file and ad-hoc test process should be replaced w/
# our real unit testing or end-to-end testing framework.


class RunStep(RequestHandler):

    def get(self):

        if not os.environ["SERVER_SOFTWARE"].startswith('Development'):
            return

        step = self.request.get("step")
        v = None

        if step == "delete_all":
            v = self.delete_all_experiments()
        elif step == "get_identity":
            v = self.get_identity()
        elif step == "refresh_identity_record":
            v = self.refresh_identity_record()
        elif step == "participate_in_monkeys":
            v = self.participate_in_monkeys()
        elif step == "participate_in_gorillas":
            v = self.participate_in_gorillas()
        elif step == "participate_in_skunks":
            v = self.participate_in_skunks()
        elif step == "participate_in_chimpanzees":
            v = self.participate_in_chimpanzees()
        elif step == "participate_in_crocodiles":
            v = self.participate_in_crocodiles()
        elif step == "participate_in_hippos":
            v = self.participate_in_hippos()
        elif step == "participate_in_doppleganger_on_new_instance":
            v = self.participate_in_doppleganger_on_new_instance()
        elif step == "count_doppleganger_experiments":
            v = self.count_doppleganger_experiments()
        elif step == "add_conversions":
            v = self.add_conversions()
        elif step == "get_experiments":
            v = self.get_experiments()
        elif step == "get_archived_experiments":
            v = self.get_experiments(archives=True)
        elif step == "print_cache":
            v = self.print_cache()
        elif step == "convert_in":
            v = self.convert_in()
        elif step == "count_participants_in":
            v = self.count_participants_in()
        elif step == "count_conversions_in":
            v = self.count_conversions_in()
        elif step == "count_experiments":
            v = self.count_experiments()
        elif step == "end_and_choose":
            v = self.end_and_choose()
        elif step == "persist":
            v = self.persist()
        elif step == "flush_hippo_counts_memcache":
            v = self.flush_hippo_counts_memcache()
        elif step == "flush_bingo_cache":
            v = self.flush_bingo_cache()
        elif step == "flush_all_cache":
            v = self.flush_all_cache()
        elif step == "create_monkeys_redirect_url":
            v = self.create_monkeys_redirect_url()
        elif step == "create_chimps_redirect_url":
            v = self.create_chimps_redirect_url()
        elif step == "archive_monkeys":
            v = self.archive_monkeys()

        self.response.out.write(json.dumps(v))

    def delete_all_experiments(self):
        bingo_cache = BingoCache.get()
        for experiment_name in bingo_cache.experiments.keys():
            bingo_cache.delete_experiment_and_alternatives(
                    bingo_cache.get_experiment(experiment_name))

        bingo_cache_archives = BingoCache.load_from_datastore(archives=True)
        for experiment_name in bingo_cache_archives.experiments.keys():
            bingo_cache_archives.delete_experiment_and_alternatives(
                    bingo_cache_archives.get_experiment(experiment_name))

        return (len(bingo_cache.experiments) +
                len(bingo_cache_archives.experiments))

    def get_identity(self):
        return gae_bingo.identity.identity()

    def refresh_identity_record(self):
        BingoIdentityCache.get().load_from_datastore()
        return True

    def participate_in_monkeys(self):
        return ab_test("monkeys")

    def archive_monkeys(self):
        bingo_cache = BingoCache.get()
        bingo_cache.archive_experiment_and_alternatives(bingo_cache.get_experiment("monkeys"))
        return True

    def participate_in_doppleganger_on_new_instance(self):
        """Simulate participating in a new experiment on a "new" instance.
        
        This test works by loading memcache with a copy of all gae/bingo
        experiments before the doppleganger test exists.

        After the doppleganger test has been created once, all future calls to
        this function simulate being run on machines that haven't yet cleared
        their instance cache and loaded the newly created doppleganger yet. We
        do this by replacing the instance cache'd state of BingoCache with the
        deep copy that we made before doppleganger was created.

        A correctly functioning test will still only create one copy of the
        experiment even though multiple clients attempted to create a new
        experiment.
        """
        # First, make a deep copy of the current state of bingo's experiments
        bingo_clone = memcache.get("bingo_clone")

        if not bingo_clone:
            # Set the clone by copying the current bingo cache state
            memcache.set("bingo_clone", copy.deepcopy(BingoCache.get()))
        else:
            # Set the current bingo cache state to the cloned state
            gae_bingo.instance_cache.set(BingoCache.CACHE_KEY, bingo_clone)

        return ab_test("doppleganger")

    def count_doppleganger_experiments(self):
        experiments = _GAEBingoExperiment.all().run()
        return len([e for e in experiments if e.name == "doppleganger"])

    def participate_in_gorillas(self):
        return ab_test("gorillas", ["a", "b", "c"])

    def participate_in_chimpanzees(self):
        # Multiple conversions test
        return ab_test("chimpanzees", conversion_name=["chimps_conversion_1", "chimps_conversion_2"])

    def participate_in_skunks(self):
        # Too many alternatives
        return ab_test("skunks", ["a", "b", "c", "d", "e"])

    def participate_in_crocodiles(self):
        # Weighted test
        return ab_test("crocodiles", {"a": 100, "b": 200, "c": 400})

    def participate_in_hippos(self):
        # Multiple conversions test
        return ab_test("hippos",
                        conversion_name=["hippos_binary",
                                         "hippos_counting"],
                        conversion_type=[ConversionTypes.Binary,
                                         ConversionTypes.Counting])

    # Should be called after participate_in_hippos to test adding
    # conversions mid-experiment
    def add_conversions(self):
        return ab_test("hippos",
                       conversion_name=["hippos_binary",
                                        "hippos_counting",
                                        "rhinos_counting"],
                       conversion_type=[ConversionTypes.Binary,
                                        ConversionTypes.Counting,
                                        ConversionTypes.Counting])

    def get_experiments(self, archives=False):
        if archives:
            bingo_cache = BingoCache.load_from_datastore(archives=True)
        else:
            bingo_cache = BingoCache.get()

        return str(bingo_cache.experiments)

    def try_this_bad(self):
        cache = BingoCache.get()
        return len(cache.get_experiment_names_by_canonical_name("hippos"))

    def convert_in(self):
        bingo(self.request.get("conversion_name"))
        return True

    def create_monkeys_redirect_url(self):
        return create_redirect_url("/gae_bingo", "monkeys")

    def create_chimps_redirect_url(self):
        return create_redirect_url("/gae_bingo",
                                  ["chimps_conversion_1",
                                   "chimps_conversion_2"])

    def end_and_choose(self):
        with ExperimentController() as dummy:
            bingo_cache = BingoCache.get()
            choose_alternative(
                    self.request.get("canonical_name"),
                    int(self.request.get("alternative_number")))

    def count_participants_in(self):
        return sum(
                map(lambda alternative: alternative.latest_participants_count(),
                    BingoCache.get().get_alternatives(self.request.get("experiment_name"))
                    )
                )

    def count_conversions_in(self):
        dict_conversions = {}

        for alternative in BingoCache.get().get_alternatives(self.request.get("experiment_name")):
            dict_conversions[alternative.content] = alternative.latest_conversions_count()

        return dict_conversions

    def count_experiments(self):
        return len(BingoCache.get().experiments)

    def persist(self):
        gae_bingo.persist.persist_task()
        return True

    def flush_hippo_counts_memcache(self):
        experiments, alternative_lists = BingoCache.get().experiments_and_alternatives_from_canonical_name("hippos")

        for experiment in experiments:
            experiment.reset_counters()

        return True

    def flush_bingo_cache(self):
        memcache.delete(BingoCache.CACHE_KEY)
        gae_bingo.instance_cache.delete(BingoCache.CACHE_KEY)
        return True

    def flush_all_cache(self):
        memcache.flush_all()
        gae_bingo.instance_cache.flush()
        return True

########NEW FILE########
__FILENAME__ = run_tests
import ast
import base64
import cookielib
import json
import os
import random
import time
import urllib
import urllib2

# TODO: convert this unit test file to the correct unit
# test pattern used by the rest of our codebase
TEST_GAE_HOST = "http://localhost:8111"

last_opener = None

def test_response(step="", data={}, use_last_cookies=False, bot=False, url=None):
    global last_opener

    if not use_last_cookies or last_opener is None:
        cj = cookielib.CookieJar()
        last_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        if bot:
            last_opener.addheaders = [(
                                'User-agent',
                                'monkeysmonkeys Googlebot monkeysmonkeys')]

    if url is None:
        data["step"] = step
        url = "/gae_bingo/tests/run_step?%s" % urllib.urlencode(data)

    req = last_opener.open("%s%s" % (TEST_GAE_HOST, url))

    try:
        response = req.read()
    finally:
        req.close()

    try:
        return json.loads(response)
    except ValueError:
        return None

def run_tests():

    # Delete all experiments (response should be count of experiments left)
    assert(test_response("delete_all") == 0)

    # Ensure the identity works correctly and consistently after login.
    for i in xrange(5):
        # Randomly generate an ID so we have a good chance of having a new one.
        # If that assumption is wrong, the test will fail--clear
        # the datastore to increase chances of working.
        user = base64.urlsafe_b64encode(os.urandom(30)) + "%40example.com"
        test_response(url="/")  # Load / to get ID assigned
        firstID = test_response("get_identity", use_last_cookies=True)  # get ID
        url = "/_ah/login?email=" + user + "&action=Login&continue=%2Fpostlogin"
        test_response(use_last_cookies=True, url=url)
        # Now make sure the ID is consistent
        assert(firstID == test_response("get_identity", use_last_cookies=True))

    assert(test_response("delete_all") == 0)  # Clear out experiments this made

    # We're going to try to add a conversion to the experiment
    assert(test_response("participate_in_hippos") in [True, False])

    assert(test_response("convert_in",
                        {"conversion_name":
                         "hippos_binary"}, use_last_cookies=True))

    # Make sure participant counts are right
    assert(test_response("count_participants_in",
                        {"experiment_name": "hippos (hippos_binary)"},
                        use_last_cookies=True)
           == 1)
    assert(test_response("count_participants_in",
                        {"experiment_name": "hippos (hippos_counting)"},
                        use_last_cookies=True)
           == 1)
    # Make sure we have the right number of conversions
    dict_conversions_server = test_response(
                         "count_conversions_in",
                         {"experiment_name": "hippos (hippos_binary)"},
                         use_last_cookies=True)
    assert(sum(dict_conversions_server.values()) == 1)

    dict_conversions_server = test_response(
                        "count_conversions_in",
                        {"experiment_name": "hippos (hippos_counting)"},
                        use_last_cookies=True)
    assert(sum(dict_conversions_server.values()) == 0)

    assert(test_response("add_conversions", use_last_cookies=True)
            in [True, False])
    assert(test_response("count_experiments", use_last_cookies=True) == 3)

    # make sure that we have the /right/ experiments
    assert(set(ast.literal_eval(test_response("get_experiments",
                                use_last_cookies=True)).keys()) ==
               set(["hippos (hippos_binary)",
                    "hippos (hippos_counting)",
                    "hippos (rhinos_counting)"]))
    
    assert(test_response("convert_in",
                        {"conversion_name": "rhinos_counting"},
                        use_last_cookies=True))

    dict_conversions_server = test_response(
                        "count_conversions_in",
                        {"experiment_name": "hippos (hippos_binary)"})
    assert(sum(dict_conversions_server.values()) == 1)

    dict_conversions_server = test_response(
                        "count_conversions_in",
                        {"experiment_name": "hippos (hippos_counting)"},
                         use_last_cookies=True)
    assert(sum(dict_conversions_server.values()) == 0)
    
    dict_conversions_server = test_response(
                        "count_conversions_in",
                        {"experiment_name": "hippos (rhinos_counting)"},
                        use_last_cookies=True)
    
    assert(sum(dict_conversions_server.values()) == 1)

    # get rid of this test's data so it doesn't affect other tests
    assert(test_response("delete_all") == 0)

    # Now try the same, but with switching users
    assert(test_response("participate_in_hippos") in [True, False])
    
    assert(test_response("convert_in",
                        {"conversion_name":
                         "hippos_binary"}, use_last_cookies=True))

    assert(test_response("participate_in_hippos", use_last_cookies=False) 
            in [True, False])

    assert(test_response("add_conversions", use_last_cookies=True) in 
            [True, False])

    assert(test_response("convert_in",
                        {"conversion_name":
                         "rhinos_counting"}, use_last_cookies=True))
    assert(test_response("count_participants_in",
                        {"experiment_name": "hippos (hippos_binary)"}) == 2)
    assert(test_response("count_participants_in",
                        {"experiment_name": "hippos (rhinos_counting)"}) == 1)
    dict_conversions_server = test_response(
                                 "count_conversions_in",
                                 {"experiment_name": "hippos (hippos_binary)"})
    assert(sum(dict_conversions_server.values()) == 1)
    dict_conversions_server = test_response(
                            "count_conversions_in",
                            {"experiment_name": "hippos (rhinos_counting)"})
    assert(sum(dict_conversions_server.values()) == 1)
    
    assert(test_response("delete_all") == 0)

    # Test constructing a redirect URL that converts in monkey and chimps
    redirect_url_monkeys = test_response("create_monkeys_redirect_url")
    assert(redirect_url_monkeys ==
           "/gae_bingo/redirect?continue=/gae_bingo" +
           "&conversion_name=monkeys")

    redirect_url_chimps = test_response("create_chimps_redirect_url")
    assert(redirect_url_chimps ==
           "/gae_bingo/redirect?continue=/gae_bingo&" +
           "conversion_name=chimps_conversion_1&" + 
           "conversion_name=chimps_conversion_2")

    # Test participating in monkeys and chimps once,
    # and use previously constructed redirect URLs to convert
    assert(test_response("participate_in_monkeys") in [True, False])
    test_response(use_last_cookies=True, url=redirect_url_monkeys)
    assert(test_response("participate_in_chimpanzees") in [True, False])
    test_response(use_last_cookies=True, url=redirect_url_chimps)

    # Make sure there's a single participant and conversion in monkeys
    assert(test_response("count_participants_in",
                        {"experiment_name": "monkeys"})
           == 1)
    dict_conversions_server = test_response("count_conversions_in",
                                           {"experiment_name": "monkeys"})
    assert(sum(dict_conversions_server.values()) == 1)

    # Make sure there's a single participant and two conversions in chimps
    assert(test_response(
                "count_participants_in",
               {"experiment_name": "chimpanzees (chimps_conversion_1)"}) == 1)
    dict_conversions_server = test_response(
                                "count_conversions_in",
                                {"experiment_name":
                                    "chimpanzees (chimps_conversion_1)"})
    assert(sum(dict_conversions_server.values()) == 1)
    dict_conversions_server = test_response(
                                "count_conversions_in",
                                {"experiment_name":
                                 "chimpanzees (chimps_conversion_2)"})
    assert(sum(dict_conversions_server.values()) == 1)

    # Delete all experiments for next round of tests
    # (response should be count of experiments left)
    assert(test_response("delete_all") == 0)

    # Refresh bot's identity record so it doesn't pollute tests
    assert(test_response("refresh_identity_record", bot=True))

    # Participate in experiment A, check for correct alternative
    # valuesum(core_metrics.values(), [])s being returned,
    for i in range(0, 20):
        assert(test_response("participate_in_monkeys") in [True, False])

    assert(test_response("count_participants_in",
                        {"experiment_name": "monkeys"})
            == 20)

    # Identify as a bot a couple times (response should stay the same)
    bot_value = None
    for i in range(0, 5):
        value = test_response("participate_in_monkeys", bot=True)
        assert(value in [True, False])

        if bot_value is None:
            bot_value = value

        assert(value == bot_value)

    # Check total participants in A (1 extra for bots)
    assert(test_response("count_participants_in",
                        {"experiment_name": "monkeys"}) == 21)

    # Participate in experiment B (responses should be "a" "b" or "c")
    for i in range(0, 15):
        assert(test_response("participate_in_gorillas") in ["a", "b", "c"])

    # Participate in experiment A,
    # using cookies half of the time to maintain identity
    for i in range(0, 20):
        assert(test_response("participate_in_monkeys",
                             use_last_cookies=(i % 2 == 1)) 
               in [True, False])
    # Check total participants in A
    # (should've only added 10 more in previous step)
    assert(test_response("count_participants_in",
                        {"experiment_name": "monkeys"}) == 31)

    # Participate in A once more with a lot of followup, 
    # persisting to datastore and flushing memcache between followups
    for i in range(0, 10):
        assert(test_response("participate_in_monkeys",
                             use_last_cookies=(i not in [0, 5]))
               in [True, False])

        if i in [1, 6]:

            assert(test_response("persist", use_last_cookies=True))

            # Wait 10 seconds for task queues to run
            time.sleep(10)

            assert(test_response("flush_all_memcache",
                                 use_last_cookies=True))

    # NOTE: It's possible for this to fail sometimes--maybe a race condition?
    # TODO(kamens,josh): figure out why this happens? (Or just wait to not use
    #                     AppEngine any more)
    # Check total participants in A
    # (should've only added 2 more in previous step)
    assert(test_response("count_participants_in",
                         {"experiment_name": "monkeys"}) == 33)

    # Participate and convert in experiment A,
    # using cookies to tie participation to conversions,
    # tracking conversions-per-alternative
    dict_conversions = {}
    for i in range(0, 35):
        alternative_key = str(test_response("participate_in_monkeys"))
        assert(test_response("convert_in",
                            {"conversion_name": "monkeys"},
                             use_last_cookies=True))


        if not alternative_key in dict_conversions:
            dict_conversions[alternative_key] = 0
        dict_conversions[alternative_key] += 1

    # Check total conversions-per-alternative in A
    assert(len(dict_conversions) == 2)
    assert(35 == sum(dict_conversions.values()))

    dict_conversions_server = test_response("count_conversions_in",
                                           {"experiment_name": "monkeys"})
    assert(len(dict_conversions) == len(dict_conversions_server))

    for key in dict_conversions:
        assert(dict_conversions[key] == dict_conversions_server[key])

    # Participate in experiment B, using cookies to maintain identity
    # and making sure alternatives for B are stable per identity
    last_response = None
    for i in range(0, 20):
        use_last_cookies = (last_response is not None and
                             random.randint(0, 2) > 0)

        current_response = test_response("participate_in_gorillas",
                                         use_last_cookies=use_last_cookies)

        if not use_last_cookies:
            last_response = current_response

        assert(current_response in ["a", "b", "c"])
        assert(last_response == current_response)

    # Participate in experiment C, which is a multi-conversion experiment,
    # and occasionally convert in *one* of the conversions
    expected_conversions = 0
    for i in range(0, 20):
        assert(test_response("participate_in_chimpanzees") in [True, False])

        if random.randint(0, 2) > 0:
            assert(test_response("convert_in",
                                {"conversion_name": "chimps_conversion_2"},
                                use_last_cookies=True))
            expected_conversions += 1

    # It's statistically possible but incredibly unlikely 
    # for this to fail based on random.randint()'s behavior
    assert(expected_conversions > 0)

    # Make sure conversions for the 2nd conversion type 
    # of this experiment are correct
    dict_conversions_server = test_response(
                                 "count_conversions_in",
                                 {"experiment_name":
                                     "chimpanzees (chimps_conversion_2)"})
    assert(expected_conversions == sum(dict_conversions_server.values()))

    # Make sure conversions for the 1st conversion type 
    # of this experiment are empty
    dict_conversions_server = test_response(
                                "count_conversions_in",
                                {"experiment_name":
                                 "chimpanzees (chimps_conversion_1)"})
    assert(0 == sum(dict_conversions_server.values()))

    # Test that calling bingo multiple times for a single 
    # user creates only one conversion (for a BINARY conversion type)
    assert(test_response("participate_in_chimpanzees") in [True, False])
    assert(test_response("convert_in",
                        {"conversion_name": "chimps_conversion_1"},
                        use_last_cookies=True))

    assert(test_response("convert_in",
                        {"conversion_name": "chimps_conversion_1"},
                         use_last_cookies=True))

    dict_conversions_server = test_response(
                                "count_conversions_in",
                                {"experiment_name":
                                    "chimpanzees (chimps_conversion_1)"})
    assert(1 == sum(dict_conversions_server.values()))

    # End experiment C, choosing a short-circuit alternative
    test_response("end_and_choose",
                 {"canonical_name": "chimpanzees", "alternative_number": 1})

    # Make sure short-circuited alternatives for 
    # C's experiments are set appropriately
    for i in range(0, 5):
        assert(test_response("participate_in_chimpanzees") == False)

    # Test an experiment with a Counting type conversion 
    # by converting multiple times for a single user
    assert(test_response("participate_in_hippos") in [True, False])

    # Persist to the datastore before Counting stress test
    assert(test_response("persist", use_last_cookies=True))

    # Wait 20 seconds for task queues to run
    time.sleep(20)

    # Hit Counting conversions multiple times
    for i in range(0, 20):

        if i % 3 == 0:
            # Stress things out a bit by flushing the memcache .incr() 
            # counts of each hippo alternative
            assert(test_response("persist", use_last_cookies=True))
            assert(test_response("flush_hippo_counts_memcache", 
                                 use_last_cookies=True))
        
        elif i % 5 == 0:
            # Stress things out even more flushing the core bingo memcache
            assert(test_response("flush_bingo_memcache",
                                 use_last_cookies=True))


        assert(test_response("convert_in",
                            {"conversion_name": "hippos_binary"},
                            use_last_cookies=True))

        assert(test_response("convert_in",
                            {"conversion_name": "hippos_counting"},
                            use_last_cookies=True))


    dict_conversions_server = test_response(
                                "count_conversions_in",
                                {"experiment_name": "hippos (hippos_binary)"})
    assert(1 == sum(dict_conversions_server.values()))
    dict_conversions_server = test_response(
                                "count_conversions_in",
                                {"experiment_name":
                                    "hippos (hippos_counting)"})
    assert(20 == sum(dict_conversions_server.values()))

    # Participate in experiment D (weight alternatives), 
    # keeping track of alternative returned count.
    dict_alternatives = {}
    for i in range(0, 75):
        alternative = test_response("participate_in_crocodiles")
        assert(alternative in ["a", "b", "c"])

        if not alternative in dict_alternatives:
            dict_alternatives[alternative] = 0
        dict_alternatives[alternative] += 1

    # Make sure weighted alternatives work -> should be a < b < c < d < e, 
    # but they should all exist.
    #
    # Again, it is statistically possible for
    # the following asserts to occasionally fail during
    # these tests, but it should be exceedingly rare 
    # if weighted alternatives are working properly.
    for key in ["a", "b", "c"]:
        assert(dict_alternatives.get(key, 0) > 0)
    assert(dict_alternatives.get("a", 0) < dict_alternatives.get("b", 0))
    assert(dict_alternatives.get("b", 0) < dict_alternatives.get("c", 0))

    # Check experiments count
    assert(test_response("count_experiments") == 7)

    # Test persist and load from DS
    assert(test_response("persist"))
    assert(test_response("flush_all_memcache"))

    # Check experiments and conversion counts 
    # remain after persist and memcache flush
    assert(test_response("count_experiments") == 7)

    dict_conversions_server = test_response(
                                "count_conversions_in", 
                                {"experiment_name":
                                    "chimpanzees (chimps_conversion_2)"})
    assert(expected_conversions == sum(dict_conversions_server.values()))

    # Test archiving
    assert(test_response("archive_monkeys"))

    # Test lack of presence in normal list of experiments after archive
    assert("monkeys" not in test_response("get_experiments"))

    # Test presence in list of archived experiments
    assert("monkeys" in test_response("get_archived_experiments"))

    # Test participating in monkeys once again after archiving
    # and make sure there's only one participant
    assert(test_response("participate_in_monkeys") in [True, False])
    assert(test_response("count_participants_in",
                        {"experiment_name": "monkeys"})
           == 1)

    print "Tests successful."

if __name__ == "__main__":
    run_tests()



########NEW FILE########
__FILENAME__ = synchronized_counter_test
import mock

from google.appengine.api import memcache

from gae_bingo import synchronized_counter
from testutil import gae_model


class SynchronizedCounterTest(gae_model.GAEModelTestCase):
    """Test gae/bingo's synchronized memcache counter."""

    def sync_incr(self, key, number, delta=1):
        future = synchronized_counter.SynchronizedCounter.incr_async(key,
                number, delta=delta)
        self.assertTrue(future.get_result())

    def pop_counters(self, keys):
        results = synchronized_counter.SynchronizedCounter.pop_counters(keys)
        self.assertTrue(isinstance(results, dict))
        return results

    def assert_counter_value(self, key, number, expected):
        count = synchronized_counter.SynchronizedCounter.get(key, number)
        self.assertEqual(count, expected)

    def test_simple_incr(self):
        self.sync_incr("monkeys", 0)
        self.sync_incr("monkeys", 0)
        self.sync_incr("monkeys", 0)

        self.assert_counter_value("monkeys", 0, 3)

    def test_multiple_incrs(self):
        for _ in range(10):
            self.sync_incr("monkeys", 1)

        for _ in range(12):
            self.sync_incr("monkeys", 2)

        for _ in range(5):
            self.sync_incr("monkeys", 0)

        for _ in range(7):
            self.sync_incr("monkeys", 3)

        for i in range(20):
            self.sync_incr("gorillas", i % 2)

        self.assert_counter_value("monkeys", 0, 5)
        self.assert_counter_value("monkeys", 1, 10)
        self.assert_counter_value("monkeys", 2, 12)
        self.assert_counter_value("monkeys", 3, 7)

        self.assert_counter_value("gorillas", 0, 10)
        self.assert_counter_value("gorillas", 1, 10)

    def test_incr_multiple_deltas(self):
        self.sync_incr("monkeys", 0, delta=5)
        self.sync_incr("monkeys", 0)
        self.sync_incr("monkeys", 0, delta=12)

        self.assert_counter_value("monkeys", 0, 18)

    def test_rollover(self):
        max_value = synchronized_counter.MAX_COUNTER_VALUE

        # Setup a combination of counters with one of the individual counters
        # at max value
        self.sync_incr("walrus", 0)

        # Bring walrus[1] up to max value
        with mock.patch('logging.warning') as log_warning:
            self.sync_incr("walrus", 1, max_value-1)  # should trigger warning
            self.sync_incr("walrus", 1)  # should trigger another warning
            self.assertEquals(2, log_warning.call_count)  # expect 2 warnings

        self.sync_incr("walrus", 2)
        self.sync_incr("walrus", 3)

        self.assert_counter_value("walrus", 0, 1)
        self.assert_counter_value("walrus", 1, max_value)
        self.assert_counter_value("walrus", 2, 1)
        self.assert_counter_value("walrus", 3, 1)

        # Increment the non-max value counters, make sure everything still
        # looks good
        self.sync_incr("walrus", 0)
        self.sync_incr("walrus", 2)

        self.assert_counter_value("walrus", 0, 2)
        self.assert_counter_value("walrus", 1, max_value)
        self.assert_counter_value("walrus", 2, 2)

        # Increment the max value counter. ROLLOVER!
        with mock.patch('logging.error') as log_error:
            self.sync_incr("walrus", 1) 
            self.assertEquals(1, log_error.call_count)  # expecting 1 error log

        # Rollover should've completely erased all counters.
        self.assert_counter_value("walrus", 0, 0)
        self.assert_counter_value("walrus", 1, 0)
        self.assert_counter_value("walrus", 2, 0)
        self.assert_counter_value("walrus", 3, 0)

        # Increment another couple counters in a new, single combination
        self.sync_incr("giraffe", 0, delta=5)
        self.sync_incr("giraffe", 2, delta=2)

        self.assert_counter_value("giraffe", 0, 5)
        self.assert_counter_value("giraffe", 2, 2)

        # Cause another rollover, this time due to a large delta.
        with mock.patch('logging.error') as log_error:
            self.sync_incr("giraffe", 0, max_value)
            self.assertEquals(1, log_error.call_count)  # expecting 1 error log

        # Make sure rollover completely erased the counter
        self.assert_counter_value("giraffe", 0, 0)
        self.assert_counter_value("giraffe", 2, 0)

    def test_invalid_input(self):
        def negative_delta():
            self.sync_incr("chimps", 1, delta=-1)

        def invalid_counter_number():
            self.sync_incr("chimps",
                    synchronized_counter.COUNTERS_PER_COMBINATION + 1)

        def negative_counter_number():
            self.sync_incr("chimps", -1)

        self.assertRaises(ValueError, negative_delta)
        self.assertRaises(ValueError, invalid_counter_number)
        self.assertRaises(ValueError, negative_counter_number)

    def test_pop(self):
        self.sync_incr("monkeys", 0, delta=5)
        self.sync_incr("giraffes", 3, delta=5)
        self.sync_incr("giraffes", 2)
        self.sync_incr("giraffes", 1)
        self.sync_incr("giraffes", 1)

        results = self.pop_counters(["monkeys", "giraffes"])
        results_after_pop = self.pop_counters(["monkeys", "giraffes"])

        self.assertEqual(results["giraffes"], [0, 2, 1, 5])
        self.assertEqual(results["monkeys"], [5, 0, 0, 0])

        self.assertEqual(results_after_pop["giraffes"], [0, 0, 0, 0])
        self.assertEqual(results_after_pop["monkeys"], [0, 0, 0, 0])

    def test_bad_pop(self):
        """Test dangerous race condition situation during pop."""
        self.sync_incr("penguins", 2)
        self.sync_incr("giraffes", 2)

        # We want to simulate a memcache eviction followed by an incr() right
        # *before* offset_multi gets called. So we mock out offset_multi to do
        # exactly that, and we use "penguins" as the problematically evicted
        # memcache key.
        old_offset_multi = memcache.offset_multi
        def evict_and_incr_during_pop(d):
            synchronized_counter.SynchronizedCounter.delete_multi(["penguins"])
            self.sync_incr("penguins", 3)
            self.sync_incr("giraffes", 3)
            return old_offset_multi(d)

        self.mock_function('google.appengine.api.memcache.offset_multi',
                evict_and_incr_during_pop)

        # During this pop, we should've detected the dangerous eviction, wiped
        # out the value for "penguins", and logged an error.
        with mock.patch('logging.error') as log_error:
            results = self.pop_counters(["penguins", "giraffes"])
            self.assertEquals(1, log_error.call_count)  # expecting 1 error log

        # The original pop will still return correct values...
        self.assertEqual(results["penguins"], [0, 0, 1, 0])
        self.assertEqual(results["giraffes"], [0, 0, 1, 0])

        # ...but after the rolled over pop, even though penguin's 3rd counter
        # was incr()'d, the counter should've been erased due to rollover
        # during pop. So a subsequent get() should not find anything in the
        # counter.
        self.assert_counter_value("penguins", 3, 0)
        self.assert_counter_value("giraffes", 3, 1)

########NEW FILE########
