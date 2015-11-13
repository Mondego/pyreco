__FILENAME__ = api
import datetime
import backend.util
from urlparse import urlparse
try:
    import json
except ImportError:
    import simplejson as json

class BaseQuery(object):
    """
    Very basic common shared functionality.
    """

    all_key_pattern = None

    def __init__(self, redis_conn, mission_name, filters=None):
        self.redis_conn = redis_conn
        self.mission_name = mission_name
        if filters is None:
            self.filters = {}
        else:
            self.filters = filters
        self.all_key = self.all_key_pattern % {"mission_name": mission_name} 

    def _extend_query(self, key, value):
        new_filters = dict(self.filters.items())
        new_filters[key] = value
        return self.__class__(self.redis_conn, self.mission_name, new_filters)

    def __iter__(self):
        return iter( self.items() )
    

class LogLine(object):
    """
    Basic object that represents a log line; pass in the timestamp
    and transcript name and it will extract the right bits of data and
    make them accessible via attributes.
    """
    
    def __init__(self, redis_conn, transcript_name, timestamp):
        self.redis_conn = redis_conn
        self.transcript_name = transcript_name
        self.mission_name = transcript_name.split(u"/")[0]
        self.timestamp = timestamp
        self.id = u"%s:%i" % (self.transcript_name, self.timestamp)
        self._load()

    @classmethod
    def by_log_line_id(cls, redis_conn, log_line_id):
        transcript, timestamp = log_line_id.split(u":", 1)
        timestamp = int(timestamp)
        return cls(redis_conn, transcript, timestamp)

    def _load(self):
        data = self.redis_conn.hgetall(u"log_line:%s:info" % self.id)
        if not data:
            raise ValueError("No such LogLine: %s at %s [%s]" % (self.transcript_name, backend.util.seconds_to_timestamp(self.timestamp), self.timestamp))
        # Load onto our attributes
        self.page = int(data['page'])
        self.transcript_page = data.get('transcript_page')
        self.note = data.get('note', None)

        self.lines = []
        for line in self.redis_conn.lrange(u"log_line:%s:lines" % self.id, 0, -1):
            line = line.decode('utf-8')
            speaker_identifier, text = [x.strip() for x in line.split(u":", 1)]
            speaker = Character(self.redis_conn, self.mission_name, speaker_identifier)
            self.lines += [[speaker, text]]

        self.next_log_line_id = data.get('next', None)
        self.previous_log_line_id = data.get('previous', None)
        self.act_number = int(data['act'])
        self.key_scene_number = data.get('key_scene', None)
        self.utc_time = datetime.datetime.utcfromtimestamp(int(data['utc_time']))
        self.lang = data.get('lang', None)

    def __repr__(self):
        return "<LogLine %s:%i, page %s (%s lines)>" % (self.transcript_name, self.timestamp, self.page, len(self.lines))

    def next(self):
        if self.next_log_line_id:
            return LogLine.by_log_line_id(self.redis_conn, self.next_log_line_id)
        else:
            return None

    def previous(self):
        if self.previous_log_line_id:
            return LogLine.by_log_line_id(self.redis_conn, self.previous_log_line_id)
        else:
            return None

    def next_timestamp(self):
        next_log_line = self.next()
        if next_log_line is None:
            return None
        else:
            return next_log_line.timestamp

    def previous_timestamp(self):
        previous_log_line = self.previous()
        if previous_log_line is None:
            return None
        else:
            return previous_log_line.timestamp

    def following_silence(self):
        try:
            return self.next_timestamp() - self.timestamp
        except TypeError:
            return None

    def act(self):
        return Act(self.redis_conn, self.mission_name, self.act_number)

    def key_scene(self):
        if self.key_scene_number:
            return KeyScene(self.redis_conn, self.mission_name, int(self.key_scene_number))
        else:
            return None

    def has_key_scene(self):
        return self.key_scene_number is not None

    def first_in_act(self):
        return LogLine.Query(self.redis_conn, self.mission_name).transcript(self.transcript_name).first_after(self.act().start).timestamp == self.timestamp

    def first_in_key_scene(self):
        if self.key_scene():
            return LogLine.Query(self.redis_conn, self.mission_name).transcript(self.transcript_name).first_after(self.key_scene().start).timestamp == self.timestamp
        else:
            return False

    def images(self):
        "Returns any images associated with this LogLine."
        image_ids = self.redis_conn.lrange(u"log_line:%s:images" % self.id, 0, -1)
        images = [self.redis_conn.hgetall(u"image:%s" % id) for id in image_ids]
        return images

    def labels(self):
        "Returns the labels for this LogLine."
        return map(lambda x: x.decode('utf-8'), self.redis_conn.smembers(u"log_line:%s:labels" % self.id))

    class Query(BaseQuery):
        """
        Allows you to query for LogLines.
        """

        all_key_pattern = u"log_lines:%(mission_name)s"

        def transcript(self, transcript_name):
            "Returns a new Query filtered by transcript"
            return self._extend_query("transcript", transcript_name)
        
        def range(self, start_time, end_time):
            "Returns a new Query whose results are between two times"
            return self._extend_query("range", (start_time, end_time))
        
        def page(self, page_number):
            "Returns a new Query whose results are all the log lines on a given page"
            return self._extend_query("page", page_number)

        def first_after(self, timestamp):
            "Returns the closest log line after the timestamp."
            if "transcript" in self.filters:
                key = u"transcript:%s" % self.filters['transcript']
            else:
                key = self.all_key
            # Do a search.
            period = 1
            results = []
            while not results:
                results = self.redis_conn.zrangebyscore(key, timestamp, timestamp+period)
                period *= 2
                # This test is here to ensure they don't happen on every single request.
                if period == 8:
                    # Use zrange to get the highest scoring element and take its score
                    top_score = self.redis_conn.zrange(key, -1, -1, withscores=True)[0][1]
                    if timestamp > top_score:
                        raise ValueError("No matching LogLines after timestamp %s." % timestamp)
            # Return the first result
            return self._key_to_instance(results[0])

        def first_before(self, timestamp):
            if "transcript" in self.filters:
                key = u"transcript:%s" % self.filters['transcript']
            else:
                key = self.all_key
            # Do a search.
            period = 1
            results = []
            while not results:
                results = self.redis_conn.zrangebyscore(key, timestamp-period, timestamp)
                period *= 2
                # This test is here to ensure they don't happen on every single request.
                if period == 8:
                    # Use zrange to get the highest scoring element and take its score
                    bottom_score = self.redis_conn.zrange(key, 0, 0, withscores=True)[0][1]
                    if timestamp < bottom_score:
                        raise ValueError("No matching LogLines before timestamp %s." % timestamp)
            # Return the first result
            return self._key_to_instance(results[-1])

        def first(self):
            "Returns the first log line if you've filtered by page."
            if set(self.filters.keys()) == set(["transcript", "page"]):
                try:
                    key = self.redis_conn.lrange(u"page:%s:%i" % (self.filters['transcript'], self.filters['page']), 0, 0)[0]
                except IndexError:
                    raise ValueError("There are no log lines for this page.")
                return self._key_to_instance(key)
            else:
                raise ValueError("You can only use first() if you've used page() and transcript() only.")
        
        def speakers(self, speakers):
            "Returns a new Query whose results are any of the specified speakers"
            return self._extend_query("speakers", speakers)
        
        def labels(self, labels):
            "Returns a new Query whose results are any of the specified labels"
            return self._extend_query("labels", labels)
        
        def items(self):
            "Executes the query and returns the items."
            # Make sure it's a valid combination 
            filter_names = set(self.filters.keys())
            if filter_names == set():
                keys = map(lambda x: x.decode('utf-8'), self.redis_conn.zrange(self.all_key, 0, -1))
            elif filter_names == set(["transcript"]):
                keys = map(lambda x: x.decode('utf-8'), self.redis_conn.zrange(u"transcript:%s" % self.filters['transcript'], 0, -1))
            elif filter_names == set(["transcript", "range"]):
                keys = map(lambda x: x.decode('utf-8'), self.redis_conn.zrangebyscore(
                    u"transcript:%s" % self.filters['transcript'],
                    self.filters['range'][0],
                    self.filters['range'][1],
                ))
            elif filter_names == set(["range"]):
                keys = map(lambda x: x.decode('utf-8'), self.redis_conn.zrangebyscore(
                    self.all_key,
                    self.filters['range'][0],
                    self.filters['range'][1],
                ))
            elif filter_names == set(['page', 'transcript']):
                keys = map(lambda x: x.decode('utf-8'), 
                    self.redis_conn.lrange(u"page:%s:%i" % (self.filters['transcript'], self.filters['page']), 0, -1)
                )
            else:
                raise ValueError("Invalid combination of filters: %s" % ", ".join(filter_names))
            # Iterate over the keys and return LogLine objects
            for key in keys:
                yield self._key_to_instance(key)

        def count(self):
            "Return the number of matching objects (efficiently)"
            filter_names = set(self.filters.keys())
            if filter_names == set(["transcript", "range"]):
                return self.redis_conn.zcount(
                    u"transcript:%s" % self.filters['transcript'],
                    self.filters['range'][0],
                    self.filters['range'][1],
                )
            else:
                raise ValueError("Cannot count over this combination of filters.")
        
        def _key_to_instance(self, key):
            transcript_name, timestamp = key.split(u":", 1)
            return LogLine(self.redis_conn, transcript_name, int(timestamp))
    

class NarrativeElement(object):
    """
    Super-class for Acts and KeyScenes
    """

    def __init__(self, redis_conn, mission_name, number):
        self.redis_conn = redis_conn
        self.mission_name = mission_name
        self.number = number
        self.one_based_number = number + 1
        self.id = u"%s:%i" % (self.mission_name, self.number)
        self._load()

    def __eq__(self, other):
        return self.id == other.id

    def _load(self):
        data = self.redis_conn.hgetall("%s:%s" % (self.noun, self.id))
        # Load onto our attributes
        self.start = int(data['start'])
        self.end = int(data['end'])
        self.title = data['title']
        self.data = data

    def __repr__(self):
        return "<%s %s:%i [%s to %s]>" % (self.noun, self.mission_name, self.number, self.start, self.end)

    def log_lines(self):
        return LogLine.Query(self.redis_conn, self.mission_name).range(self.start, self.end)

    def includes(self, timestamp):
        return self.start <= timestamp < self.end

    class Query(BaseQuery):
        def act_number(self, act_number):
            return self._extend_query('act_number', act_number)

        def items(self):
            "Executes the query and returns the items."
            # Make sure it's a valid combination 
            filter_names = set(self.filters.keys())
            if filter_names == set():
                keys = map(lambda x: x.decode('utf-8'), self.redis_conn.lrange(self.all_key, 0, -1))
            elif filter_names == set(['act_number']):
                redis_key = u'act:%s:%s:key_scenes' % (self.mission_name, self.filters['act_number'])
                keys = map(lambda x: x.decode('utf-8'), self.redis_conn.lrange(redis_key, 0, -1))
            else:
                raise ValueError("Invalid combination of filters: %s" % ", ".join(filter_names))
            # Iterate over the keys and return LogLine objects
            for key in keys:
                yield self._key_to_instance(key)

        def _key_to_instance(self, key):
            mission_name, number = key.split(u":", 1)
            return self.result_class(self.redis_conn, mission_name, int(number))


class Act(NarrativeElement):
    """
    Represents an Act in the mission.
    """

    noun = u'act'

    def _load(self):
        super(Act, self)._load()
        self.description = self.data['description']
        self.banner = self.data.get("banner", None)
        self.banner_class = self.data.get("banner_class", None)
        self.banner_colour = self.data.get("banner_colour", None)
        self.orbital = self.data.get("orbital", None)
        self.illustration = self.data.get("illustration", None)
        self.homepage = self.data.get("homepage", None)

        stats_data = self.redis_conn.hgetall(u"%s:%s:stats" % (self.noun, self.id))
        if stats_data:
            self.has_stats = True
            self.stats_image_map = stats_data['image_map']
            self.stats_image_map_id = stats_data['image_map_id']
        else:
            self.has_stats = False
    
    def key_scenes(self):
        return list( KeyScene.Query(self.redis_conn, self.mission_name).act_number(self.number).items() )
    
    class Query(NarrativeElement.Query):
        all_key_pattern = u"acts:%(mission_name)s"

        def _key_to_instance(self, key):
            mission_name, number = key.split(u":", 1)
            return Act(self.redis_conn, mission_name, int(number))


class KeyScene(NarrativeElement):
    """
    Represents an Key Scene in the mission.
    """

    noun = 'key_scene'

    class Query(NarrativeElement.Query):
        all_key_pattern = u"key_scenes:%(mission_name)s"

        def _key_to_instance(self, key):
            mission_name, number = key.split(u":", 1)
            return KeyScene(self.redis_conn, mission_name, int(number))


class Character(object):
    """
    Represents a character in the mission
    """

    def __init__(self, redis_conn, mission_name, identifier):
        self.redis_conn = redis_conn
        self.mission_name = mission_name
        self.identifier = identifier
        self.id = u"%s:%s" % (self.mission_name, identifier)
        self._load()

    def _load(self):
        key = u"characters:%s" % self.id
        data = self.redis_conn.hgetall( key )
        bio = data.get('bio', None)
        if bio is not None:
            bio = bio.decode('utf-8')
        
        self.identifier_lang      = data.get('identifier_lang', None)
        self.name                 = data.get('name', self.identifier.encode('utf-8')).decode('utf-8')
        self.name_lang            = data.get('name_lang', None)
        self.short_name           = data.get('short_name', self.identifier.encode('utf-8')).decode('utf-8')
        self.short_name_lang      = data.get('short_name_lang', None)
        self.role                 = data.get('role', 'other')
        self.mission_position     = data.get('mission_position', '')
        self.avatar               = data.get('avatar', 'blank_avatar_48.png')
        self.bio                  = bio
        self.url                  = data.get('url', None)
        self.photo                = data.get('photo', None)
        self.photo_width          = data.get('photo_width', None)
        self.photo_height         = data.get('photo_height', None)
        self.quotable_log_line_id = data.get('quotable_log_line_id', None)
        self.precomputed_slug     = data.get('slug', None)
        
        stat_pairs = self.redis_conn.lrange( u"%s:stats" % key, 0, -1 )
        self.stats = [ stat.split(u':', 1) for stat in stat_pairs ]

    @property
    def slug(self):
        if self.precomputed_slug is not None:
            return self.precomputed_slug
        from django.template.defaultfilters import slugify
        return slugify(self.short_name)

    @property
    def urlsite(self):
        if self.url is not None:
            return urlparse(self.url).netloc
        return None

    def quotable_log_line(self):
        if not self.quotable_log_line_id:
            return None
        transcript_name, timestamp = self.quotable_log_line_id.split(u":", 1)
        
        parts = map(int, timestamp.split(u":"))
        timestamp = (parts[0] * 86400) + (parts[1] * 3600) + (parts[2] * 60) + parts[3]
        return LogLine(
            self.redis_conn,
            '%s/%s' % (self.mission_name, transcript_name), 
            int(timestamp)
        )

    def current_shift(self, timestamp):
        shifts_key = u'characters:%s:shifts' % self.id
        shifts = self.redis_conn.zrangebyscore(shifts_key, -86400, timestamp)
        if shifts:
            shift_start, character_identifier = shifts[-1].decode('utf-8').split(u':')
            return Character(self.redis_conn, self.mission_name, character_identifier)
        else:
            return self

    def __repr__(self):
        return '<Character: %s>' % self.identifier

    class Query(BaseQuery):

        all_key_pattern = u"characters:%(mission_name)s"
        role_key_pattern = u"characters:%(mission_name)s:%(role)s"

        def role(self, role):
            return self._extend_query("role", role)

        def items(self):
            "Executes the query and returns the items."
            
            filter_names = set(self.filters.keys())
            if filter_names == set():
                keys = map(lambda x: x.decode('utf-8'), self.redis_conn.lrange(self.all_key, 0, -1))
            elif filter_names == set(['role']):
                role_key = self.role_key_pattern % {'mission_name':self.mission_name, 'role':self.filters['role']}
                keys = map(lambda x: x.decode('utf-8'), self.redis_conn.lrange(role_key, 0, -1))
            else:
                raise ValueError("Invalid combination of filters: %s" % ", ".join(filter_names))
            
            for key in keys:
                yield self._key_to_instance(key)

        def _key_to_instance(self, key):
            return Character(self.redis_conn, self.mission_name, key)

class Glossary(object):
    """
    Represents a technical term with an associated explanation.
    """
    
    def __init__(self, redis_conn, mission_name, identifier):
        self.redis_conn   = redis_conn
        self.mission_name = mission_name
        self.identifier   = identifier
        self.id           = u"%s:%s" % (self.mission_name, identifier.lower())
        self._load()

    def _load(self):
        key = u"glossary:%s" % self.id
        data = self.redis_conn.hgetall( key )
        if not data:
            raise ValueError("No such glossary item: %s (%s)" % (self.id, key))
        self.description               = data['description'].decode('utf-8')
        self.description_lang          = data.get('description_lang', None)
        self.extended_description      = data.get('extended_description', None)
        self.extended_description_lang = data.get('extended_description_lang', None)
        self.abbr                      = data['abbr']
        self.abbr_lang                 = data.get('abbr_lang', None)
        self.key                       = self.id
        self.type                      = data.get('type', 'jargon')
        self.times_mentioned           = data['times_mentioned']
        self.precomputed_slug          = data.get('slug', None)

    @property
    def slug(self):
        if self.precomputed_slug is not None:
            return self.precomputed_slug
        from django.template.defaultfilters import slugify
        return slugify(self.abbr)

    def links(self):
        # Fetch all the IDs
        link_ids = self.redis_conn.lrange(u"glossary:%s:links" % self.id, 0, -1)
        for link_id in link_ids:
            yield self.redis_conn.hgetall(u"glossary-link:%s" % link_id)

    class Query(BaseQuery):
        all_key_pattern  = u"glossary:%(mission_name)s"
        role_key_pattern = u"glossary:%(mission_name)s:%(abbr)s"

        def items(self):
            "Executes the query and returns the items."
            
            filter_names = set(self.filters.keys())
            if filter_names == set():
                keys = map(lambda x: x.decode('utf-8'), self.redis_conn.lrange(self.all_key, 0, -1))
            else:
                raise ValueError("Invalid combination of filters: %s" % ", ".join(filter_names))
            
            for key in keys:
                yield self._key_to_instance(key)

        def _key_to_instance(self, key):
            return Glossary(self.redis_conn, self.mission_name, key)


class Mission(object):

    def __init__(self, redis_conn, name):
        self.redis_conn = redis_conn
        self.name = name
        self._load()

    def _load(self):
        data = self.redis_conn.hgetall(u"mission:%s" % self.name)
        self.copy = dict([
            (k, json.loads(v)) for k, v in
            self.redis_conn.hgetall(u"mission:%s:copy" % self.name).items()
        ])
        self.title = self.copy['title']
        self.upper_title = self.copy['upper_title']
        self.lower_title = self.copy['lower_title']
        self.summary = self.copy.get('summary', '')
        self.description = self.copy.get('description', self.summary)
        self.featured = (data['featured'].lower() == 'true')
        self.main_transcript = data['main_transcript']
        try:
            self.main_transcript_subname = data['main_transcript'].split(u"/", 1)[1]
        except IndexError:
            self.main_transcript_subname = ""
        self.media_transcript = data['media_transcript']
        self.incomplete = (data['incomplete'].lower() == "true")
        self.subdomain = data.get('subdomain', None)
        self.utc_launch_time = data['utc_launch_time']
        self.type_search = self.copy.get('type_search', 'reentry')
        self.transcripts = self.redis_conn.smembers("mission:%s:transcripts" % self.name)
        # HACK?: Hash of page counts
        self.transcript_pages = self.redis_conn.hgetall("pages:%s" % self.name)

    @property
    def year(self):
        dt = datetime.datetime.fromtimestamp(float(self.utc_launch_time))
        return dt.year

    class Query(BaseQuery):

        def __init__(self, redis_conn, filters=None):
            self.redis_conn = redis_conn
            if filters is None:
                self.filters = {}
            else:
                self.filters = filters

        def items(self):
            "Executes the query and returns the items."
            
            filter_names = set(self.filters.keys())
            if filter_names == set():
                keys = [
                    x.decode('utf-8').split(u":")[1]
                    for x in self.redis_conn.keys(u"mission:*")
                    if len(x.split(u":")) == 2
                ]
            else:
                raise ValueError("Invalid combination of filters: %s" % ", ".join(filter_names))

            missions = []
            for key in keys:
                missions.append(self._key_to_instance(key))
            missions.sort(
                key = lambda m: int(m.utc_launch_time),
            )
            return missions

        def _key_to_instance(self, key):
            return Mission(self.redis_conn, key)


########NEW FILE########
__FILENAME__ = indexer
from __future__ import with_statement
import os
import sys
import re
import redis
import xappy
import time
try:
    import json
except ImportError:
    import simplejson as json
from django.utils.html import strip_tags

from backend.parser import TranscriptParser, MetaParser
from backend.api import Act, KeyScene, Character, Glossary, LogLine
from backend.util import seconds_to_timestamp

search_db = xappy.IndexerConnection(
    os.path.join(os.path.dirname(__file__), '..', 'xappydb'),
)

def mission_time_to_timestamp(mission_time):
    """Takes a mission time string (XX:XX:XX:XX) and converts it to a number of seconds"""
    d,h,m,s = map(int, mission_time.split(':'))
    timestamp = d*86400 + h*3600 + m*60 + s
    
    if mission_time[0] == "-":
        return timestamp * -1
    else:
        return timestamp

class TranscriptIndexer(object):
    """
    Parses a file and indexes it.
    """

    LINES_PER_PAGE = 50

    def __init__(self, redis_conn, mission_name, transcript_name, parser):
        self.redis_conn = redis_conn
        self.mission_name = mission_name
        self.transcript_name = transcript_name
        self.parser = parser

        search_db.add_field_action(
            "mission",
            xappy.FieldActions.INDEX_EXACT,
            # search_by_default=False,
            # allow_field_specific=False,
        )
        search_db.add_field_action(
            "transcript",
            xappy.FieldActions.INDEX_EXACT,
        )
        # don't think we need STORE_CONTENT actions any more
        search_db.add_field_action(
            "speaker",
            xappy.FieldActions.STORE_CONTENT,
        )
        # Can't use facetting unless Xapian supports it
        # can't be bothered to check this (xappy._checkxapian.missing_features['facets']==1)
        #
        # search_db.add_field_action(
        #     "speaker",
        #     xappy.FieldActions.FACET,
        #     type='string',
        # )
        search_db.add_field_action(
            "speaker",
            xappy.FieldActions.INDEX_FREETEXT,
            weight=1,
            language='en',
            search_by_default=True,
            allow_field_specific=True,
        )
        search_db.add_field_action(
            "text",
            xappy.FieldActions.STORE_CONTENT,
        )
        search_db.add_field_action(
            "text",
            xappy.FieldActions.INDEX_FREETEXT,
            weight=1,
            language='en',
            search_by_default=True,
            allow_field_specific=False,
            spell=True,
        )
        search_db.add_field_action(
            "weight",
            xappy.FieldActions.SORTABLE,
            type='float',
        )
        search_db.add_field_action(
            "speaker_identifier",
            xappy.FieldActions.STORE_CONTENT,
        )
        # Add names as synonyms for speaker identifiers
        characters = Character.Query(self.redis_conn, self.mission_name).items()
        self.characters = {}
        for character in characters:
            self.characters[character.identifier] = character
        #     for name in [character.name, character.short_name]:
        #         for bit in name.split():
        #             search_db.add_synonym(bit, character.identifier)
        #             search_db.add_synonym(bit, character.identifier, field='speaker')
        # Add to the mission's list of transcripts
        self.redis_conn.sadd(
            "mission:%s:transcripts" % self.mission_name,
            self.transcript_name,
        )

    def add_to_search_index(self, mission, id, chunk, weight, timestamp):
        """
        Take some text and a set of speakers (also text) and add a document
        to the search index, with the id stuffed in the document data.
        """
        lines = chunk['lines']
        doc = xappy.UnprocessedDocument()
        doc.fields.append(xappy.Field("mission", mission))
        doc.fields.append(xappy.Field("weight", weight))
        doc.fields.append(xappy.Field("transcript", self.transcript_name))
        for line in lines:
            text = re.sub(
                r"\[\w+:([^]]+)\|([^]]+)\]",
                lambda m: m.group(2),
                line['text'],
            )
            text = re.sub(
                r"\[\w+:([^]]+)\]",
                lambda m: m.group(1),
                text,
            )
            # also strip tags from text, because they're lame lame lame
            text = strip_tags(text)
            doc.fields.append(xappy.Field("text", text))
            # grab the character to get some more text to index under speaker
            ch = self.characters.get(line['speaker'], None)
            if ch:
                ch2 = ch.current_shift(timestamp)
                doc.fields.append(xappy.Field("speaker_identifier", ch2.identifier))
                doc.fields.append(xappy.Field("speaker", ch2.short_name))
                doc.fields.append(xappy.Field("speaker", ch.short_name))
            else:
                doc.fields.append(xappy.Field("speaker_identifier", line['speaker']))
                doc.fields.append(xappy.Field("speaker", line['speaker']))
        doc.id = id
        try:
            search_db.replace(search_db.process(doc))
        except xappy.errors.IndexerError:
            print "umm, error"
            print id, lines
            raise

    def index(self):
        current_labels = {}
        current_transcript_page = None
        current_page = 1
        current_page_lines = 0
        current_lang = None
        last_act = None
        previous_log_line_id = None
        previous_timestamp = None
        launch_time = int(self.redis_conn.hget("mission:%s" % self.mission_name, "utc_launch_time"))
        acts = list(Act.Query(self.redis_conn, self.mission_name))
        key_scenes = list(KeyScene.Query(self.redis_conn, self.mission_name))
        glossary_items = dict([
            (item.identifier.lower(), item) for item in
            Glossary.Query(self.redis_conn, self.mission_name)
        ])
        for chunk in self.parser.get_chunks():
            timestamp = chunk['timestamp']
            log_line_id = "%s:%i" % (self.transcript_name, timestamp)
            if timestamp <= previous_timestamp:
                raise Exception, "%s should be after %s" % (seconds_to_timestamp(timestamp), seconds_to_timestamp(previous_timestamp))
            # See if there's transcript page info, and update it if so
            if chunk['meta'].get('_page', 0):
                current_transcript_page = int(chunk["meta"]['_page'])
            if chunk['meta'].get('_lang', None):
                current_lang = chunk['meta']['_lang']
            if current_transcript_page:
                self.redis_conn.set("log_line:%s:page" % log_line_id, current_transcript_page)
            # Look up the act
            for act in acts:
                if act.includes(timestamp):
                    break
            else:
                print "Error: No act for timestamp %s" % seconds_to_timestamp(timestamp)
                continue
            # If we've filled up the current page, go to a new one
            if current_page_lines >= self.LINES_PER_PAGE or (last_act is not None and last_act != act):
                current_page += 1
                current_page_lines = 0
            last_act = act
            # First, create a record with some useful information
            info_key = "log_line:%s:info" % log_line_id
            info_record = {
                "offset": chunk['offset'],
                "page": current_page,
                "act": act.number,
                "utc_time": launch_time + timestamp,
            }
            if current_transcript_page:
                info_record["transcript_page"] = current_transcript_page
            if current_lang:
                info_record["lang"] = current_lang
            # And an editorial note if present
            if '_note' in chunk['meta']:
                info_record["note"] = chunk['meta']['_note']

            self.redis_conn.hmset(
                info_key,
                info_record,
            )
            # Look up the key scene
            for key_scene in key_scenes:
                if key_scene.includes(timestamp):
                    self.redis_conn.hset(info_key, 'key_scene', key_scene.number)
                    break
            # Create the doubly-linked list structure
            if previous_log_line_id:
                self.redis_conn.hset(
                    info_key,
                    "previous",
                    previous_log_line_id,
                )
                self.redis_conn.hset(
                    "log_line:%s:info" % previous_log_line_id,
                    "next",
                    log_line_id,
                )
            previous_log_line_id = log_line_id
            previous_timestamp = timestamp
            # Also store the text
            text = u""
            for line in chunk['lines']:
                self.redis_conn.rpush(
                    "log_line:%s:lines" % log_line_id,
                    u"%(speaker)s: %(text)s" % line,
                )
                text += "%s %s" % (line['speaker'], line['text'])
            # Store any images
            for i, image in enumerate(chunk['meta'].get("_images", [])):
                # Make the image id
                image_id = "%s:%s" % (log_line_id, i)
                # Push it onto the images list
                self.redis_conn.rpush(
                    "log_line:%s:images" % log_line_id,
                    image_id,
                )
                # Store the image data
                self.redis_conn.hmset(
                    "image:%s" % image_id,
                    image,
                )
            # Add that logline ID for the people involved
            speakers = set([ line['speaker'] for line in chunk['lines'] ])
            for speaker in speakers:
                self.redis_conn.sadd("speaker:%s" % speaker, log_line_id)
            # Add it to the index for this page
            self.redis_conn.rpush("page:%s:%i" % (self.transcript_name, current_page), log_line_id)
            # Add it into the transcript and everything sets
            self.redis_conn.zadd("log_lines:%s" % self.mission_name, log_line_id, chunk['timestamp'])
            self.redis_conn.zadd("transcript:%s" % self.transcript_name, log_line_id, chunk['timestamp'])
            # Read the new labels into current_labels
            has_labels = False
            if '_labels' in chunk['meta']:
                for label, endpoint in chunk['meta']['_labels'].items():
                    if endpoint is not None and label not in current_labels:
                        current_labels[label] = endpoint
                    elif label in current_labels:
                        current_labels[label] = max(
                            current_labels[label],
                            endpoint
                        )
                    elif endpoint is None:
                        self.redis_conn.sadd("label:%s" % label, log_line_id)
                        has_labels = True
            # Expire any old labels
            for label, endpoint in current_labels.items():
                if endpoint < chunk['timestamp']:
                    del current_labels[label]
            # Apply any surviving labels
            for label in current_labels:
                self.redis_conn.sadd("label:%s" % label, log_line_id)
                has_labels = True
            # And add this logline to search index
            if has_labels:
                print "weight = 3 for %s" % log_line_id
                weight = 3.0 # magic!
            else:
                weight = 1.0
            self.add_to_search_index(
                mission=self.mission_name,
                id=log_line_id,
                chunk = chunk,
                weight=weight,
                timestamp=timestamp,
            )
            # For any mentioned glossary terms, add to them.
            for word in text.split():
                word = word.strip(",;-:'\"").lower()
                if word in glossary_items:
                    glossary_item = glossary_items[word]
                    self.redis_conn.hincrby(
                        "glossary:%s" % glossary_item.id,
                        "times_mentioned",
                        1,
                    )
            # Increment the number of log lines we've done
            current_page_lines += len(chunk['lines'])
        pages_set = self.redis_conn.hexists(
            "pages:%s" % self.mission_name,
            self.transcript_name
        )
        if not pages_set and current_transcript_page:
            print "%s original pages: %d" % (
                self.transcript_name, current_transcript_page
            )
            self.redis_conn.hset(
                "pages:%s" % self.mission_name, 
                self.transcript_name,
                current_transcript_page
            )

class MetaIndexer(object):
    """
    Takes a mission folder and reads and indexes its meta information.
    """

    def __init__(self, redis_conn, mission_name, parser):
        self.redis_conn = redis_conn
        self.parser = parser
        self.mission_name = mission_name

    def index(self):
        meta = self.parser.get_meta()

        # Store mission info
        for subdomain in meta['subdomains']:
            if meta.get('subdomain', None) is None:
                meta['subdomain'] = subdomain
            self.redis_conn.set("subdomain:%s" % subdomain, meta['name'])
        del meta['subdomains']
        utc_launch_time = meta['utc_launch_time']
        if isinstance(utc_launch_time, basestring):
            # parse as something more helpful than a number
            # time.mktime operates in the local timezone, so force that to UTC first
            os.environ['TZ'] = 'UTC'
            time.tzset()
            utc_launch_time = int(time.mktime(time.strptime(utc_launch_time, "%Y-%m-%dT%H:%M:%S")))
            print "Converted launch time to UTC timestamp:", utc_launch_time
        self.redis_conn.hmset(
            "mission:%s" % self.mission_name,
            {
                "utc_launch_time": utc_launch_time,
                "featured": meta.get('featured', False),
                "incomplete": meta.get('incomplete', True),
                "main_transcript": meta.get('main_transcript', "%s/TEC" % self.mission_name),
                "media_transcript": meta.get('media_transcript', None),
                "subdomain": meta.get('subdomain', None),
            }
        )
        
        # TODO: Default to highest _page from transcript if we don't have this
        transcript_pages = meta.get( 'transcript_pages' )
        if transcript_pages:
            print "Setting original pagecounts from _meta"
            self.redis_conn.hmset(
                "pages:%s" % self.mission_name,
                transcript_pages
            )
        
        
        copy = meta.get("copy", {})
        for key, value in copy.items():
            copy[key] = json.dumps(value)
        if copy.get('based_on_header', None) is None:
            copy['based_on_header'] = json.dumps('Based on the original transcript')
        self.redis_conn.hmset(
            "mission:%s:copy" % self.mission_name,
            copy,
        )
        for homepage_quote in meta.get('homepage_quotes', []):
            self.redis_conn.sadd(
                "mission:%s:homepage_quotes" % self.mission_name,
                homepage_quote,
            )

        self.index_narrative_elements(meta)
        self.index_glossary(meta)
        self.index_characters(meta)
        self.index_special_searches(meta)
        self.index_errors(meta)

    def index_narrative_elements(self, meta):
        "Stores acts and key scenes in redis"
        for noun in ('act', 'key_scene'):
            # Sort by element['range'][0] before adding to redis
            narrative_elements = meta.get('%ss' % noun, [])
            narrative_elements_sorted = sorted(
                narrative_elements,
                key=lambda element: element['range'][0]
            )
            
            for i, data in enumerate( narrative_elements_sorted ):
                key = "%s:%s:%i" % (noun, self.mission_name, i)
                self.redis_conn.rpush(
                    "%ss:%s" % (noun, self.mission_name),
                    "%s:%i" % (self.mission_name, i),
                )

                data['start'], data['end'] = map(mission_time_to_timestamp, data['range'])
                del data['range']

                self.redis_conn.hmset(key, data)
        # if no acts at all, make one that includes everything from before Vostok 1 until after now
        # do this before we link key scenes, so we can have them without having to specify acts
        if len(list(Act.Query(self.redis_conn, self.mission_name)))==0:
            key = "act:%s:0" % (self.mission_name,)
            title = meta.get('copy', {}).get('title', None)
            if title is None:
                title = meta.get('name', u'The Mission')
            else:
                title = json.loads(title)
            data = {
                'title': title,
                'description': '',
                'start': -300000000, # Vostok 1 launch was -275248380
                'end': int(time.time()) + 86400*365 # so we can have acts ending up to a year in the future
            }
            self.redis_conn.rpush(
                "acts:%s" % (self.mission_name,),
                "%s:0" % (self.mission_name,),
            )
            self.redis_conn.hmset(key, data)
        # Link key scenes and acts
        for act in Act.Query(self.redis_conn, self.mission_name):
            for key_scene in KeyScene.Query(self.redis_conn, self.mission_name):
                if act.includes(key_scene.start):
                    self.redis_conn.rpush(
                        'act:%s:%s:key_scenes' % (self.mission_name, act.number),
                        '%s:%s' % (self.mission_name, key_scene.number),
                    )

    def index_characters(self, meta):
        "Stores character information in redis"
        for identifier in meta.get("character_ordering", []):
            self.redis_conn.rpush(
                "character-ordering:%s" % self.mission_name,
                identifier,
            )
        for identifier, data in meta.get('characters', {}).items():
            mission_key   = "characters:%s" % self.mission_name
            character_key = "%s:%s" % (mission_key, identifier)
            
            self.redis_conn.rpush(mission_key, identifier)
            self.redis_conn.rpush(
                '%s:%s' % (mission_key, data['role']),
                identifier
            )
            
            # Push stats as a list so it's in-order later
            if 'stats' in data:
                for stat in data['stats']:
                    self.redis_conn.rpush(
                        '%s:stats' % character_key, 
                        "%s:%s" % (stat['value'], stat['text'])
                    )
                del data['stats']
            
            # Store the shifts
            if 'shifts' in data:
                for shift_information in data['shifts']:
                    character_identifier = shift_information[0]
                    shift_start = shift_information[1]
                    
                    shift_start = mission_time_to_timestamp(shift_start)
                    shifts_key = '%s:shifts' % character_key
                    self.redis_conn.zadd(
                        shifts_key,
                        '%s:%s' % (shift_start, character_identifier),
                        shift_start
                    )
                del data['shifts']
            
            self.redis_conn.hmset(character_key, data)

    def index_glossary(self, meta):
        """
        Stores glossary information in redis.
        Terms from the mission's shared glossary file(s) will be overridden by terms
        from the mission's own _meta file.
        """
        
        glossary_terms = {}
        
        # Load any shared glossary files and add their contents
        # to glossary_terms
        shared_glossary_files       = meta.get('shared_glossaries', [])
        shared_glossary_files_path  = os.path.join(os.path.dirname( __file__ ), '..', 'missions', 'shared', 'glossary')
        
        for filename in shared_glossary_files:
            with open(os.path.join(shared_glossary_files_path, filename)) as fh:
                glossary_terms.update(json.load(fh))
        
        # Add the mission specific glossary terms
        glossary_terms.update(meta.get('glossary', {}))
        
        # Add all the glossary terms to redis
        for identifier, data in glossary_terms.items():
            term_key = "%s:%s" % (self.mission_name, identifier.lower())
            
            # Add the ID to the list for this mission
            self.redis_conn.rpush("glossary:%s" % self.mission_name, identifier)

            # Extract the links from the data
            links = data.get('links', [])
            if "links" in data:
                del data['links']
            
            data['abbr'] = identifier
            data['times_mentioned'] = 0
            
            if data.has_key('summary') and data.has_key('description'):
                data['extended_description'] = data['description']
                data['description'] = data['summary']
                del data['summary']
            else:
                data['description'] = data.get('summary') or data.get('description', u"")
            if data.has_key('description_lang'):
                data['extended_description_lang'] = data['description_lang']
                del data['description_lang']
            if data.has_key('summary_lang'):
                data['description_lang'] = data['summary_lang']
                del data['summary_lang']
            
            # Store the main data in a hash
            self.redis_conn.hmset("glossary:%s" % term_key, data)

            # Store the links in a list
            for i, link in enumerate(links):
                link_id = "%s:%i" % (term_key, i)
                self.redis_conn.rpush("glossary:%s:links" % term_key, link_id)
                self.redis_conn.hmset(
                    "glossary-link:%s" % link_id,
                    link,
                )

    def index_special_searches(self, meta):
        "Indexes things that in no way sound like 'feaster legs'."
        for search, value in meta.get('special_searches', {}).items():
            self.redis_conn.set("special_search:%s:%s" % (self.mission_name, search), value)

    def index_errors(self, meta):
        "Indexes error page info"
        for key, info in meta.get('error_pages', {}).items():
            self.redis_conn.hmset(
                "error_page:%s:%s" % (self.mission_name, key),
                info,
            )


class MissionIndexer(object):
    """
    Takes a mission folder and indexes everything inside it.
    """

    def __init__(self, redis_conn, mission_name, folder_path):
        self.redis_conn = redis_conn
        self.folder_path = folder_path
        self.mission_name = mission_name

    def index(self):
        self.index_meta()
        self.index_transcripts()

    def index_transcripts(self):
        for filename in os.listdir(self.folder_path):
            if "." not in filename and filename[0] != "_" and filename[-1] != "~":
                print "Indexing %s..." % filename
                path = os.path.join(self.folder_path, filename)
                parser = TranscriptParser(path)
                indexer = TranscriptIndexer(self.redis_conn, self.mission_name, "%s/%s" % (self.mission_name, filename), parser)
                indexer.index()

    def index_meta(self):
        print "Indexing _meta..."
        path = os.path.join(self.folder_path, "_meta")
        parser = MetaParser(path)
        indexer = MetaIndexer(self.redis_conn, self.mission_name, parser)
        indexer.index()


if __name__ == "__main__":
    redis_conn = redis.Redis()
    transcript_dir = os.path.join(os.path.dirname( __file__ ), '..', "missions")
    if len(sys.argv)>1:
        dirs = sys.argv[1:]
        flip_db = False
    else:
        dirs = os.listdir(transcript_dir)
        flip_db = True
    # Find out what the current database number is
    if not redis_conn.exists("live_database"):
        redis_conn.set("live_database", 0)
    current_db = int(redis_conn.get("live_database") or 0)
    
    if flip_db:
        # Work out the new database
        new_db = 0 if current_db else 1
        print "Indexing into database %s" % new_db
        # Flush the new one
        redis_conn.select(new_db)
        redis_conn.flushdb()
        # Restore the live database key
        redis_conn.select(0)
        redis_conn.set("live_database", current_db)
        redis_conn.select(new_db)
    else:
        new_db = current_db
        print "Reindexing into database %s" % new_db
        print "Note that this is not perfect! Do not use in production."
        redis_conn.set("hold", "1")

    for filename in dirs:
        path = os.path.join(transcript_dir, filename)
        if filename[0] not in "_." and os.path.isdir(path) and os.path.exists(os.path.join(path, "transcripts", "_meta")):
            print "Mission: %s" % filename
            if not flip_db:
                # try to flush this mission
                for k in redis_conn.keys("*:%s:*" % filename):
                    redis_conn.delete(k.decode('utf-8'))
                for k in redis_conn.keys("*:%s/*" % filename):
                    redis_conn.delete(k.decode('utf-8'))
                for k in redis_conn.keys("%s:*" % filename):
                    redis_conn.delete(k.decode('utf-8'))
                for k in redis_conn.keys("*:%s" % filename):
                    redis_conn.delete(k.decode('utf-8'))
                for k in redis_conn.keys("speaker:*"):
                    for v in redis_conn.smembers(k.decode('utf-8')):
                        if v.startswith("%s/" % filename):
                            redis_conn.srem(k, v)
                for k in redis_conn.keys("subdomain:*"):
                    if redis_conn.get(k) == filename:
                        redis_conn.delete(k)
            idx = MissionIndexer(redis_conn, filename, os.path.join(path, "transcripts")) 
            idx.index()
    search_db.flush()
    if flip_db:
        # Switch the database over
        redis_conn.select(0)
        redis_conn.set("live_database", new_db)
    else:
        redis_conn.delete("hold")

########NEW FILE########
__FILENAME__ = parser
from __future__ import with_statement
import string
try:
    import json
except ImportError:
    import simplejson as json
from backend.util import timestamp_to_seconds, seconds_to_timestamp

class TranscriptParser(object):
    """
    Runs through a transcript file working out and storing the
    byte offsets.
    """

    def __init__(self, path):
        self.path = path

    def get_lines(self, offset):
        with open(self.path) as fh:
            fh.seek(offset)
            for line in fh:
                yield line

    def get_chunks(self, offset=0):
        """
        Reads the log lines from the file in order and yields them.
        """
        current_chunk = None
        reuse_line = None
        lines = iter(self.get_lines(offset))
        while lines or reuse_line:
            # If there's a line to reuse, use that, else read a new
            # line from the file.
            if reuse_line:
                line = reuse_line
                reuse_line = None
            else:
                try:
                    line = lines.next()
                except StopIteration:
                    break
                offset += len(line)
                line = line.decode("utf8")
            # If it's a comment or empty line, ignore it.
            if not line.strip() or line.strip()[0] == "#":
                continue
            # If it's a timestamp header, make a new chunk object.
            elif line[0] == "[":
                # Read the timestamp
                try:
                    timestamp = int(line[1:].split("]")[0])
                except ValueError:
                    try:
                        timestamp = timestamp_to_seconds(line[1:].split("]")[0])
                    except ValueError:
                        print "Error: invalid timestamp %s" % (line[1:], )
                        raise
                if current_chunk:
                    yield current_chunk
                # Start a new log line item
                current_chunk = {
                    "timestamp": timestamp,
                    "lines": [],
                    "meta": {},
                    "offset": offset - len(line),
                }
            # If it's metadata, read the entire thing.
            elif line[0] == "_":
                # Meta item
                name, blob = line.split(":", 1)
                while True:
                    try:
                        line = lines.next()
                    except StopIteration:
                        break
                    offset += len(line)
                    line = line.decode("utf8")
                    if not line.strip() or line.strip()[0] == "#":
                        continue
                    if line[0] in string.whitespace:
                        blob += line
                    else:
                        reuse_line = line
                        break
                # Parse the blob
                blob = blob.strip()
                if blob:
                    try:
                        data = json.loads(blob)
                    except ValueError:
                        try:
                            data = json.loads('"%s"' % blob.replace('"', r'\"'))
                        except ValueError:
                            print "Error: Invalid json at timestamp %s, key %s" % \
                                            (seconds_to_timestamp(timestamp), name)
                            continue
                    current_chunk['meta'][name.strip()] = data
            # If it's a continuation, append to the current line
            elif line[0] in string.whitespace:
                # Continuation line
                if not current_chunk:
                    print "Error: Continuation line before first timestamp header. Line: %s" % \
                                                                        (line)
                elif not current_chunk['lines']:
                    print "Error: Continuation line before first speaker name."
                else:
                    current_chunk['lines'][-1]['text'] += " " + line.strip()
            # If it's a new line, start a new line. Shock.
            else:
                # New line of speech
                try:
                    speaker, text = line.split(":", 1)
                except ValueError:
                    print "Error: First speaker line not in Name: Text format: %s." % (line,)
                else:
                    line = {
                        "speaker": speaker.strip(),
                        "text": text.strip(),
                    }
                    current_chunk['lines'].append(line)
        # Finally, if there's one last chunk, yield it.
        if current_chunk:
            yield current_chunk

class MetaParser(TranscriptParser):
    
    def get_meta(self):
        try:
            with open(self.path) as fh:
                return json.load(fh)
        except ValueError, e:
            raise ValueError("JSON decode error in file %s: %s" % (self.path, e))
        return json.load(fh)

########NEW FILE########
__FILENAME__ = reformat
"""
When run as a module, reads the file provided on the command line
and outputs on stdout a slightly nicer file format.
"""

import sys
from backend.parser import TranscriptParser
from backend.util import seconds_to_timestamp

def reformat(filename):
    parser = TranscriptParser(filename)
    for chunk in parser.get_chunks():
        timestamp = seconds_to_timestamp(chunk['timestamp'])
        for line in chunk['lines']:
            print "%s\t%s:\t %s" % (
                timestamp,
                line['speaker'],
                line['text'],
            )

if __name__ == "__main__":
    try:
        reformat(sys.argv[1])
    except IndexError:
        print "Please pass a file to reformat"


########NEW FILE########
__FILENAME__ = stats_porn
import subprocess
import redis
import os

from backend.api import Mission, Act, KeyScene, LogLine
from backend.util import seconds_to_timestamp

class StatsPornGenerator(object):
    
    graph_background_file = 'backend/stats_porn_assets/chart_background.png'
    key_scene_marker_files = 'backend/stats_porn_assets/key_scene_%d.png'
    max_bar_height = 40
    graph_background_width = 896
    graph_bar_colour = '#00a9d2'
    
    image_output_path = 'missions/%s/images/stats/'
    
    def __init__(self, redis_conn):
        self.redis_conn = redis_conn

    def build_all_missions(self):
        for mission in list(Mission.Query(self.redis_conn)):
            self.build_mission(mission)

    def build_mission(self, mission):
        print "Building data visualisations for %s..." % mission.name
        for act in list(Act.Query(self.redis_conn, mission.name)):
            print ' ... %s' % act.title

            # Split the act into sections, one for each bar on the graph
            act_duration = act.end - act.start
            section_duration = act_duration // 92
            
            # Count the number of log lines in each segment
            # and find the maximum number of log lines in a segment
            t = act.start            
            segment_line_counts = []
            max_line_count = 0
            real_output_path = self.image_output_path % mission.name
            while t < act.end:
                # Load log lines for this segment
                query = LogLine.Query(self.redis_conn, mission.name).transcript(mission.main_transcript).range(t, t+section_duration)
                line_count = len(list(query))
                # Store segment stats
                max_line_count = max(line_count, max_line_count)
                segment_line_counts.append((t, t+section_duration, line_count))
                t += section_duration

            # Make sure we have an output directoy and work out where to write the image
            try:
                os.makedirs(real_output_path)
            except OSError:
                pass
            graph_file = 'graph_%s_%s.png' % (mission.name, act.number)
            output_path = '%s/%s' % (real_output_path, graph_file)

            # Add initial draw command
            draw_commands = [
                'convert', self.graph_background_file,
                '-fill', self.graph_bar_colour,
            ]

            # Add initial image map tags
            image_map_id = '%s_%s_frequency_graph' % (mission.name, act.number)
            image_map = ['<map id="%s" name="%s">' % (image_map_id, image_map_id)]

            # Iterate over the segments and add them to the draw commands and image map
            for i, line in enumerate(segment_line_counts):
                start, end, count = line
                height = int(round(count / float(max(max_line_count, 1)) * self.max_bar_height))

                bar_width = 6
                bar_spacing = 4

                top_left_x     = i * (bar_width + bar_spacing) + 2
                top_left_y     = self.max_bar_height - height + 14
                bottom_right_x = top_left_x + bar_width
                bottom_right_y = self.max_bar_height + 14

                draw_commands.append('-draw')
                draw_commands.append('rectangle %s,%s,%s,%s' % (top_left_x, top_left_y, bottom_right_x, bottom_right_y))

                if height > 0:
                    image_map.append('<area shape="rect" coords="%(coords)s" href="%(url)s" alt="%(alt)s">' % {
                        "url":    '/%s/%s/#show-selection' % (seconds_to_timestamp(start), seconds_to_timestamp(end)),
                        "alt":    '%d lines between %s and %s' % (count, seconds_to_timestamp(start), seconds_to_timestamp(end)),
                        "coords": '%s,%s,%s,%s' % (top_left_x, top_left_y, bottom_right_x, bottom_right_y),
                    })

            # Output the basic graph image
            draw_commands.append(output_path)
            subprocess.call(draw_commands)

            # Iterate over the key scenes adding them to the graph and image map
            for i, key_scene in enumerate(act.key_scenes()):
                print '     - %s' % key_scene.title

                top_left_x =     int((self.graph_background_width / float(act_duration)) * (key_scene.start - act.start)) + 2
                top_left_y =     self.max_bar_height + 5 + 14
                bottom_right_x = top_left_x + 20
                bottom_right_y = top_left_y + 20
                marker_image =   self.key_scene_marker_files % (i+1)
                
                subprocess.call([
                    'composite',
                    '-geometry', '+%s+%s' % (top_left_x, top_left_y),
                    marker_image,
                    output_path,
                    output_path,
                ])

                image_map.append('<area shape="rect" coords="%(coords)s" href="%(url)s" alt="%(alt)s">' % {
                    "url":      '/%s/%s/#show-selection' % (seconds_to_timestamp(key_scene.start), seconds_to_timestamp(key_scene.end)),
                    "alt":      key_scene.title.decode('utf-8'),
                    "coords":   '%s,%s,%s,%s' % (top_left_x, top_left_y, bottom_right_x, bottom_right_y),
                })

            # Finalise the image map
            image_map.append('</map>')

            self.redis_conn.hmset(
                'act:%s:%s:stats' % (mission.name, act.number),
                {
                    "image_map":    "\n".join(image_map),
                    "image_map_id": image_map_id,
                }
            )


if __name__ == "__main__":
    redis_conn = redis.Redis()
    current_db = int(redis_conn.get("live_database") or 0)
    print "Building visualisations from database %d" % current_db
    redis_conn.select(current_db)

    generator = StatsPornGenerator(redis_conn)
    generator.build_all_missions()

########NEW FILE########
__FILENAME__ = util
import math

def seconds_to_timestamp(seconds):
    abss = abs(seconds)
    return "%s%02i:%02i:%02i:%02i" % (
        "-" if seconds<0 else "",
        abss // 86400,
        abss % 86400 // 3600,
        abss % 3600 // 60,
        abss % 60,
    )

def floor_and_int(s):
    return int(math.floor(float(s)))

def timestamp_to_seconds(timestamp):
    if timestamp[0]=='-':
        timestamp = timestamp[1:]
        mult = -1
    else:
        mult = 1
    parts = map(floor_and_int, timestamp.split(":", 3))
    return mult * ((parts[0] * 86400) + (parts[1] * 3600) + (parts[2] * 60) + parts[3])


########NEW FILE########
__FILENAME__ = client
import datetime
import errno
import socket
import threading
import time
import warnings
from itertools import chain, imap
from redis.exceptions import ConnectionError, ResponseError, InvalidResponse, WatchError
from redis.exceptions import RedisError, AuthenticationError


class ConnectionPool(threading.local):
    "Manages a list of connections on the local thread"
    def __init__(self):
        self.connections = {}

    def make_connection_key(self, host, port, db):
        "Create a unique key for the specified host, port and db"
        return '%s:%s:%s' % (host, port, db)

    def get_connection(self, host, port, db, password, socket_timeout):
        "Return a specific connection for the specified host, port and db"
        key = self.make_connection_key(host, port, db)
        if key not in self.connections:
            self.connections[key] = Connection(
                host, port, db, password, socket_timeout)
        return self.connections[key]

    def get_all_connections(self):
        "Return a list of all connection objects the manager knows about"
        return self.connections.values()


class Connection(object):
    "Manages TCP communication to and from a Redis server"
    def __init__(self, host='localhost', port=6379, db=0, password=None,
                 socket_timeout=None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.socket_timeout = socket_timeout
        self._sock = None
        self._fp = None

    def connect(self, redis_instance):
        "Connects to the Redis server if not already connected"
        if self._sock:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
        except socket.error, e:
            # args for socket.error can either be (errno, "message")
            # or just "message"
            if len(e.args) == 1:
                error_message = "Error connecting to %s:%s. %s." % \
                    (self.host, self.port, e.args[0])
            else:
                error_message = "Error %s connecting %s:%s. %s." % \
                    (e.args[0], self.host, self.port, e.args[1])
            raise ConnectionError(error_message)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(self.socket_timeout)
        self._sock = sock
        self._fp = sock.makefile('r')
        redis_instance._setup_connection()

    def disconnect(self):
        "Disconnects from the Redis server"
        if self._sock is None:
            return
        try:
            self._sock.close()
        except socket.error:
            pass
        self._sock = None
        self._fp = None

    def send(self, command, redis_instance):
        "Send ``command`` to the Redis server. Return the result."
        self.connect(redis_instance)
        try:
            self._sock.sendall(command)
        except socket.error, e:
            if e.args[0] == errno.EPIPE:
                self.disconnect()
            raise ConnectionError("Error %s while writing to socket. %s." % \
                e.args)

    def read(self, length=None):
        """
        Read a line from the socket is length is None,
        otherwise read ``length`` bytes
        """
        try:
            if length is not None:
                return self._fp.read(length)
            return self._fp.readline()
        except socket.error, e:
            self.disconnect()
            if e.args and e.args[0] == errno.EAGAIN:
                raise ConnectionError("Error while reading from socket: %s" % \
                    e.args[1])
        return ''

def list_or_args(command, keys, args):
    # returns a single list combining keys and args
    # if keys is not a list or args has items, issue a
    # deprecation warning
    oldapi = bool(args)
    try:
        i = iter(keys)
        # a string can be iterated, but indicates
        # keys wasn't passed as a list
        if isinstance(keys, basestring):
            oldapi = True
    except TypeError:
        oldapi = True
        keys = [keys]
    if oldapi:
        warnings.warn(DeprecationWarning(
            "Passing *args to Redis.%s has been deprecated. "
            "Pass an iterable to ``keys`` instead" % command
        ))
        keys.extend(args)
    return keys

def timestamp_to_datetime(response):
    "Converts a unix timestamp to a Python datetime object"
    if not response:
        return None
    try:
        response = int(response)
    except ValueError:
        return None
    return datetime.datetime.fromtimestamp(response)

def string_keys_to_dict(key_string, callback):
    return dict([(key, callback) for key in key_string.split()])

def dict_merge(*dicts):
    merged = {}
    [merged.update(d) for d in dicts]
    return merged

def parse_info(response):
    "Parse the result of Redis's INFO command into a Python dict"
    info = {}
    def get_value(value):
        if ',' not in value:
            return value
        sub_dict = {}
        for item in value.split(','):
            k, v = item.split('=')
            try:
                sub_dict[k] = int(v)
            except ValueError:
                sub_dict[k] = v
        return sub_dict
    for line in response.splitlines():
        key, value = line.split(':')
        try:
            info[key] = int(value)
        except ValueError:
            info[key] = get_value(value)
    return info

def pairs_to_dict(response):
    "Create a dict given a list of key/value pairs"
    return dict(zip(response[::2], response[1::2]))

def zset_score_pairs(response, **options):
    """
    If ``withscores`` is specified in the options, return the response as
    a list of (value, score) pairs
    """
    if not response or not options['withscores']:
        return response
    return zip(response[::2], map(float, response[1::2]))

def int_or_none(response):
    if response is None:
        return None
    return int(response)

def float_or_none(response):
    if response is None:
        return None
    return float(response)


class Redis(threading.local):
    """
    Implementation of the Redis protocol.

    This abstract class provides a Python interface to all Redis commands
    and an implementation of the Redis protocol.

    Connection and Pipeline derive from this, implementing how
    the commands are sent and received to the Redis server
    """
    RESPONSE_CALLBACKS = dict_merge(
        string_keys_to_dict(
            'AUTH DEL EXISTS EXPIRE EXPIREAT HDEL HEXISTS HMSET MOVE MSETNX '
            'RENAMENX SADD SISMEMBER SMOVE SETEX SETNX SREM ZADD ZREM',
            bool
            ),
        string_keys_to_dict(
            'DECRBY HLEN INCRBY LLEN SCARD SDIFFSTORE SINTERSTORE '
            'SUNIONSTORE ZCARD ZREMRANGEBYRANK ZREMRANGEBYSCORE ZREVRANK',
            int
            ),
        string_keys_to_dict(
            # these return OK, or int if redis-server is >=1.3.4
            'LPUSH RPUSH',
            lambda r: isinstance(r, int) and r or r == 'OK'
            ),
        string_keys_to_dict('ZSCORE ZINCRBY', float_or_none),
        string_keys_to_dict(
            'FLUSHALL FLUSHDB LSET LTRIM MSET RENAME '
            'SAVE SELECT SET SHUTDOWN WATCH UNWATCH',
            lambda r: r == 'OK'
            ),
        string_keys_to_dict('BLPOP BRPOP', lambda r: r and tuple(r) or None),
        string_keys_to_dict('SDIFF SINTER SMEMBERS SUNION',
            lambda r: r and set(r) or set()
            ),
        string_keys_to_dict('ZRANGE ZRANGEBYSCORE ZREVRANGE', zset_score_pairs),
        {
            'BGREWRITEAOF': lambda r: \
                r == 'Background rewriting of AOF file started',
            'BGSAVE': lambda r: r == 'Background saving started',
            'HGETALL': lambda r: r and pairs_to_dict(r) or {},
            'INFO': parse_info,
            'LASTSAVE': timestamp_to_datetime,
            'PING': lambda r: r == 'PONG',
            'RANDOMKEY': lambda r: r and r or None,
            'TTL': lambda r: r != -1 and r or None,
            'ZRANK': int_or_none,
        }
        )

    # commands that should NOT pull data off the network buffer when executed
    SUBSCRIPTION_COMMANDS = set([
        'SUBSCRIBE', 'UNSUBSCRIBE', 'PSUBSCRIBE', 'PUNSUBSCRIBE'
        ])

    def __init__(self, host='localhost', port=6379,
                 db=0, password=None, socket_timeout=None,
                 connection_pool=None,
                 charset='utf-8', errors='strict'):
        self.encoding = charset
        self.errors = errors
        self.connection = None
        self.subscribed = False
        self.connection_pool = connection_pool and connection_pool or ConnectionPool()
        self.select(db, host, port, password, socket_timeout)

    #### Legacty accessors of connection information ####
    def _get_host(self):
        return self.connection.host
    host = property(_get_host)

    def _get_port(self):
        return self.connection.port
    port = property(_get_port)

    def _get_db(self):
        return self.connection.db
    db = property(_get_db)

    def pipeline(self, transaction=True):
        """
        Return a new pipeline object that can queue multiple commands for
        later execution. ``transaction`` indicates whether all commands
        should be executed atomically. Apart from multiple atomic operations,
        pipelines are useful for batch loading of data as they reduce the
        number of back and forth network operations between client and server.
        """
        return Pipeline(
            self.connection,
            transaction,
            self.encoding,
            self.errors
            )

    def lock(self, name, timeout=None, sleep=0.1):
        """
        Return a new Lock object using key ``name`` that mimics
        the behavior of threading.Lock.

        If specified, ``timeout`` indicates a maximum life for the lock.
        By default, it will remain locked until release() is called.

        ``sleep`` indicates the amount of time to sleep per loop iteration
        when the lock is in blocking mode and another client is currently
        holding the lock.
        """
        return Lock(self, name, timeout=timeout, sleep=sleep)

    #### COMMAND EXECUTION AND PROTOCOL PARSING ####
    def _execute_command(self, command_name, command, **options):
        subscription_command = command_name in self.SUBSCRIPTION_COMMANDS
        if self.subscribed and not subscription_command:
            raise RedisError("Cannot issue commands other than SUBSCRIBE and "
                "UNSUBSCRIBE while channels are open")
        try:
            self.connection.send(command, self)
            if subscription_command:
                return None
            return self.parse_response(command_name, **options)
        except ConnectionError:
            self.connection.disconnect()
            self.connection.send(command, self)
            if subscription_command:
                return None
            return self.parse_response(command_name, **options)

    def execute_command(self, *args, **options):
        "Sends the command to the redis server and returns it's response"
        cmds = ['$%s\r\n%s\r\n' % (len(enc_value), enc_value)
                for enc_value in imap(self.encode, args)]
        return self._execute_command(
            args[0],
            '*%s\r\n%s' % (len(cmds), ''.join(cmds)),
            **options
            )

    def _parse_response(self, command_name, catch_errors):
        conn = self.connection
        response = conn.read()[:-2] # strip last two characters (\r\n)
        if not response:
            self.connection.disconnect()
            raise ConnectionError("Socket closed on remote end")

        # server returned a null value
        if response in ('$-1', '*-1'):
            return None
        byte, response = response[0], response[1:]

        # server returned an error
        if byte == '-':
            if response.startswith('ERR '):
                response = response[4:]
            raise ResponseError(response)
        # single value
        elif byte == '+':
            return response
        # int value
        elif byte == ':':
            return int(response)
        # bulk response
        elif byte == '$':
            length = int(response)
            if length == -1:
                return None
            response = length and conn.read(length) or ''
            conn.read(2) # read the \r\n delimiter
            return response
        # multi-bulk response
        elif byte == '*':
            length = int(response)
            if length == -1:
                return None
            if not catch_errors:
                return [self._parse_response(command_name, catch_errors)
                    for i in range(length)]
            else:
                # for pipelines, we need to read everything,
                # including response errors. otherwise we'd
                # completely mess up the receive buffer
                data = []
                for i in range(length):
                    try:
                        data.append(
                            self._parse_response(command_name, catch_errors)
                            )
                    except Exception, e:
                        data.append(e)
                return data

        raise InvalidResponse("Unknown response type for: %s" % command_name)

    def parse_response(self, command_name, catch_errors=False, **options):
        "Parses a response from the Redis server"
        response = self._parse_response(command_name, catch_errors)
        if command_name in self.RESPONSE_CALLBACKS:
            return self.RESPONSE_CALLBACKS[command_name](response, **options)
        return response

    def encode(self, value):
        "Encode ``value`` using the instance's charset"
        if isinstance(value, str):
            return value
        if isinstance(value, unicode):
            return value.encode(self.encoding, self.errors)
        # not a string or unicode, attempt to convert to a string
        return str(value)

    #### CONNECTION HANDLING ####
    def get_connection(self, host, port, db, password, socket_timeout):
        "Returns a connection object"
        conn = self.connection_pool.get_connection(
            host, port, db, password, socket_timeout)
        # if for whatever reason the connection gets a bad password, make
        # sure a subsequent attempt with the right password makes its way
        # to the connection
        conn.password = password
        return conn

    def _setup_connection(self):
        """
        After successfully opening a socket to the Redis server, the
        connection object calls this method to authenticate and select
        the appropriate database.
        """
        if self.connection.password:
            if not self.execute_command('AUTH', self.connection.password):
                raise AuthenticationError("Invalid Password")
        self.execute_command('SELECT', self.connection.db)

    def select(self, db, host=None, port=None, password=None,
            socket_timeout=None):
        """
        Switch to a different Redis connection.

        If the host and port aren't provided and there's an existing
        connection, use the existing connection's host and port instead.

        Note this method actually replaces the underlying connection object
        prior to issuing the SELECT command.  This makes sure we protect
        the thread-safe connections
        """
        if host is None:
            if self.connection is None:
                raise RedisError("A valid hostname or IP address "
                    "must be specified")
            host = self.connection.host
        if port is None:
            if self.connection is None:
                raise RedisError("A valid port must be specified")
            port = self.connection.port

        self.connection = self.get_connection(
            host, port, db, password, socket_timeout)

    def shutdown(self):
        "Shutdown the server"
        if self.subscribed:
            raise RedisError("Can't call 'shutdown' from a pipeline'")
        try:
            self.execute_command('SHUTDOWN')
        except ConnectionError:
            # a ConnectionError here is expected
            return
        raise RedisError("SHUTDOWN seems to have failed.")


    #### SERVER INFORMATION ####
    def bgrewriteaof(self):
        "Tell the Redis server to rewrite the AOF file from data in memory."
        return self.execute_command('BGREWRITEAOF')

    def bgsave(self):
        """
        Tell the Redis server to save its data to disk.  Unlike save(),
        this method is asynchronous and returns immediately.
        """
        return self.execute_command('BGSAVE')

    def dbsize(self):
        "Returns the number of keys in the current database"
        return self.execute_command('DBSIZE')

    def delete(self, *names):
        "Delete one or more keys specified by ``names``"
        return self.execute_command('DEL', *names)
    __delitem__ = delete

    def flush(self, all_dbs=False):
        warnings.warn(DeprecationWarning(
            "'flush' has been deprecated. "
            "Use Redis.flushdb() or Redis.flushall() instead"))
        if all_dbs:
            return self.flushall()
        return self.flushdb()

    def flushall(self):
        "Delete all keys in all databases on the current host"
        return self.execute_command('FLUSHALL')

    def flushdb(self):
        "Delete all keys in the current database"
        return self.execute_command('FLUSHDB')

    def info(self):
        "Returns a dictionary containing information about the Redis server"
        return self.execute_command('INFO')

    def lastsave(self):
        """
        Return a Python datetime object representing the last time the
        Redis database was saved to disk
        """
        return self.execute_command('LASTSAVE')

    def ping(self):
        "Ping the Redis server"
        return self.execute_command('PING')

    def save(self):
        """
        Tell the Redis server to save its data to disk,
        blocking until the save is complete
        """
        return self.execute_command('SAVE')

    #### BASIC KEY COMMANDS ####
    def append(self, key, value):
        """
        Appends the string ``value`` to the value at ``key``. If ``key``
        doesn't already exist, create it with a value of ``value``.
        Returns the new length of the value at ``key``.
        """
        return self.execute_command('APPEND', key, value)

    def decr(self, name, amount=1):
        """
        Decrements the value of ``key`` by ``amount``.  If no key exists,
        the value will be initialized as 0 - ``amount``
        """
        return self.execute_command('DECRBY', name, amount)

    def exists(self, name):
        "Returns a boolean indicating whether key ``name`` exists"
        return self.execute_command('EXISTS', name)
    __contains__ = exists

    def expire(self, name, time):
        "Set an expire flag on key ``name`` for ``time`` seconds"
        return self.execute_command('EXPIRE', name, time)

    def expireat(self, name, when):
        """
        Set an expire flag on key ``name``. ``when`` can be represented
        as an integer indicating unix time or a Python datetime object.
        """
        if isinstance(when, datetime.datetime):
            when = int(time.mktime(when.timetuple()))
        return self.execute_command('EXPIREAT', name, when)

    def get(self, name):
        """
        Return the value at key ``name``, or None of the key doesn't exist
        """
        return self.execute_command('GET', name)
    __getitem__ = get

    def getset(self, name, value):
        """
        Set the value at key ``name`` to ``value`` if key doesn't exist
        Return the value at key ``name`` atomically
        """
        return self.execute_command('GETSET', name, value)

    def incr(self, name, amount=1):
        """
        Increments the value of ``key`` by ``amount``.  If no key exists,
        the value will be initialized as ``amount``
        """
        return self.execute_command('INCRBY', name, amount)

    def keys(self, pattern='*'):
        "Returns a list of keys matching ``pattern``"
        return self.execute_command('KEYS', pattern)

    def mget(self, keys, *args):
        """
        Returns a list of values ordered identically to ``keys``

        * Passing *args to this method has been deprecated *
        """
        keys = list_or_args('mget', keys, args)
        return self.execute_command('MGET', *keys)

    def mset(self, mapping):
        "Sets each key in the ``mapping`` dict to its corresponding value"
        items = []
        for pair in mapping.iteritems():
            items.extend(pair)
        return self.execute_command('MSET', *items)

    def msetnx(self, mapping):
        """
        Sets each key in the ``mapping`` dict to its corresponding value if
        none of the keys are already set
        """
        items = []
        for pair in mapping.iteritems():
            items.extend(pair)
        return self.execute_command('MSETNX', *items)

    def move(self, name, db):
        "Moves the key ``name`` to a different Redis database ``db``"
        return self.execute_command('MOVE', name, db)

    def randomkey(self):
        "Returns the name of a random key"
        return self.execute_command('RANDOMKEY')

    def rename(self, src, dst, **kwargs):
        """
        Rename key ``src`` to ``dst``

        * The following flags have been deprecated *
        If ``preserve`` is True, rename the key only if the destination name
            doesn't already exist
        """
        if kwargs:
            if 'preserve' in kwargs:
                warnings.warn(DeprecationWarning(
                    "preserve option to 'rename' is deprecated, "
                    "use Redis.renamenx instead"))
                if kwargs['preserve']:
                    return self.renamenx(src, dst)
        return self.execute_command('RENAME', src, dst)

    def renamenx(self, src, dst):
        "Rename key ``src`` to ``dst`` if ``dst`` doesn't already exist"
        return self.execute_command('RENAMENX', src, dst)


    def set(self, name, value, **kwargs):
        """
        Set the value at key ``name`` to ``value``

        * The following flags have been deprecated *
        If ``preserve`` is True, set the value only if key doesn't already
        exist
        If ``getset`` is True, set the value only if key doesn't already exist
        and return the resulting value of key
        """
        if kwargs:
            if 'getset' in kwargs:
                warnings.warn(DeprecationWarning(
                    "getset option to 'set' is deprecated, "
                    "use Redis.getset() instead"))
                if kwargs['getset']:
                    return self.getset(name, value)
            if 'preserve' in kwargs:
                warnings.warn(DeprecationWarning(
                    "preserve option to 'set' is deprecated, "
                    "use Redis.setnx() instead"))
                if kwargs['preserve']:
                    return self.setnx(name, value)
        return self.execute_command('SET', name, value)
    __setitem__ = set

    def setex(self, name, value, time):
        """
        Set the value of key ``name`` to ``value``
        that expires in ``time`` seconds
        """
        return self.execute_command('SETEX', name, time, value)

    def setnx(self, name, value):
        "Set the value of key ``name`` to ``value`` if key doesn't exist"
        return self.execute_command('SETNX', name, value)

    def substr(self, name, start, end=-1):
        """
        Return a substring of the string at key ``name``. ``start`` and ``end``
        are 0-based integers specifying the portion of the string to return.
        """
        return self.execute_command('SUBSTR', name, start, end)

    def ttl(self, name):
        "Returns the number of seconds until the key ``name`` will expire"
        return self.execute_command('TTL', name)

    def type(self, name):
        "Returns the type of key ``name``"
        return self.execute_command('TYPE', name)

    def watch(self, name):
        """
        Watches the value at key ``name``, or None of the key doesn't exist
        """
        if self.subscribed:
            raise RedisError("Can't call 'watch' from a pipeline'")

        return self.execute_command('WATCH', name)

    def unwatch(self):
        """
        Unwatches the value at key ``name``, or None of the key doesn't exist
        """
        if self.subscribed:
            raise RedisError("Can't call 'unwatch' from a pipeline'")

        return self.execute_command('UNWATCH')

    #### LIST COMMANDS ####
    def blpop(self, keys, timeout=0):
        """
        LPOP a value off of the first non-empty list
        named in the ``keys`` list.

        If none of the lists in ``keys`` has a value to LPOP, then block
        for ``timeout`` seconds, or until a value gets pushed on to one
        of the lists.

        If timeout is 0, then block indefinitely.
        """
        if isinstance(keys, basestring):
            keys = [keys]
        else:
            keys = list(keys)
        keys.append(timeout)
        return self.execute_command('BLPOP', *keys)

    def brpop(self, keys, timeout=0):
        """
        RPOP a value off of the first non-empty list
        named in the ``keys`` list.

        If none of the lists in ``keys`` has a value to LPOP, then block
        for ``timeout`` seconds, or until a value gets pushed on to one
        of the lists.

        If timeout is 0, then block indefinitely.
        """
        if isinstance(keys, basestring):
            keys = [keys]
        else:
            keys = list(keys)
        keys.append(timeout)
        return self.execute_command('BRPOP', *keys)

    def lindex(self, name, index):
        """
        Return the item from list ``name`` at position ``index``

        Negative indexes are supported and will return an item at the
        end of the list
        """
        return self.execute_command('LINDEX', name, index)

    def llen(self, name):
        "Return the length of the list ``name``"
        return self.execute_command('LLEN', name)

    def lpop(self, name):
        "Remove and return the first item of the list ``name``"
        return self.execute_command('LPOP', name)

    def lpush(self, name, value):
        "Push ``value`` onto the head of the list ``name``"
        return self.execute_command('LPUSH', name, value)

    def lrange(self, name, start, end):
        """
        Return a slice of the list ``name`` between
        position ``start`` and ``end``

        ``start`` and ``end`` can be negative numbers just like
        Python slicing notation
        """
        return self.execute_command('LRANGE', name, start, end)

    def lrem(self, name, value, num=0):
        """
        Remove the first ``num`` occurrences of ``value`` from list ``name``

        If ``num`` is 0, then all occurrences will be removed
        """
        return self.execute_command('LREM', name, num, value)

    def lset(self, name, index, value):
        "Set ``position`` of list ``name`` to ``value``"
        return self.execute_command('LSET', name, index, value)

    def ltrim(self, name, start, end):
        """
        Trim the list ``name``, removing all values not within the slice
        between ``start`` and ``end``

        ``start`` and ``end`` can be negative numbers just like
        Python slicing notation
        """
        return self.execute_command('LTRIM', name, start, end)

    def pop(self, name, tail=False):
        """
        Pop and return the first or last element of list ``name``

        * This method has been deprecated,
          use Redis.lpop or Redis.rpop instead *
        """
        warnings.warn(DeprecationWarning(
            "Redis.pop has been deprecated, "
            "use Redis.lpop or Redis.rpop instead"))
        if tail:
            return self.rpop(name)
        return self.lpop(name)

    def push(self, name, value, head=False):
        """
        Push ``value`` onto list ``name``.

        * This method has been deprecated,
          use Redis.lpush or Redis.rpush instead *
        """
        warnings.warn(DeprecationWarning(
            "Redis.push has been deprecated, "
            "use Redis.lpush or Redis.rpush instead"))
        if head:
            return self.lpush(name, value)
        return self.rpush(name, value)

    def rpop(self, name):
        "Remove and return the last item of the list ``name``"
        return self.execute_command('RPOP', name)

    def rpoplpush(self, src, dst):
        """
        RPOP a value off of the ``src`` list and atomically LPUSH it
        on to the ``dst`` list.  Returns the value.
        """
        return self.execute_command('RPOPLPUSH', src, dst)

    def rpush(self, name, value):
        "Push ``value`` onto the tail of the list ``name``"
        return self.execute_command('RPUSH', name, value)

    def sort(self, name, start=None, num=None, by=None, get=None,
             desc=False, alpha=False, store=None):
        """
        Sort and return the list, set or sorted set at ``name``.

        ``start`` and ``num`` allow for paging through the sorted data

        ``by`` allows using an external key to weight and sort the items.
            Use an "*" to indicate where in the key the item value is located

        ``get`` allows for returning items from external keys rather than the
            sorted data itself.  Use an "*" to indicate where int he key
            the item value is located

        ``desc`` allows for reversing the sort

        ``alpha`` allows for sorting lexicographically rather than numerically

        ``store`` allows for storing the result of the sort into
            the key ``store``
        """
        if (start is not None and num is None) or \
                (num is not None and start is None):
            raise RedisError("``start`` and ``num`` must both be specified")

        pieces = [name]
        if by is not None:
            pieces.append('BY')
            pieces.append(by)
        if start is not None and num is not None:
            pieces.append('LIMIT')
            pieces.append(start)
            pieces.append(num)
        if get is not None:
            pieces.append('GET')
            pieces.append(get)
        if desc:
            pieces.append('DESC')
        if alpha:
            pieces.append('ALPHA')
        if store is not None:
            pieces.append('STORE')
            pieces.append(store)
        return self.execute_command('SORT', *pieces)


    #### SET COMMANDS ####
    def sadd(self, name, value):
        "Add ``value`` to set ``name``"
        return self.execute_command('SADD', name, value)

    def scard(self, name):
        "Return the number of elements in set ``name``"
        return self.execute_command('SCARD', name)

    def sdiff(self, keys, *args):
        "Return the difference of sets specified by ``keys``"
        keys = list_or_args('sdiff', keys, args)
        return self.execute_command('SDIFF', *keys)

    def sdiffstore(self, dest, keys, *args):
        """
        Store the difference of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        keys = list_or_args('sdiffstore', keys, args)
        return self.execute_command('SDIFFSTORE', dest, *keys)

    def sinter(self, keys, *args):
        "Return the intersection of sets specified by ``keys``"
        keys = list_or_args('sinter', keys, args)
        return self.execute_command('SINTER', *keys)

    def sinterstore(self, dest, keys, *args):
        """
        Store the intersection of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        keys = list_or_args('sinterstore', keys, args)
        return self.execute_command('SINTERSTORE', dest, *keys)

    def sismember(self, name, value):
        "Return a boolean indicating if ``value`` is a member of set ``name``"
        return self.execute_command('SISMEMBER', name, value)

    def smembers(self, name):
        "Return all members of the set ``name``"
        return self.execute_command('SMEMBERS', name)

    def smove(self, src, dst, value):
        "Move ``value`` from set ``src`` to set ``dst`` atomically"
        return self.execute_command('SMOVE', src, dst, value)

    def spop(self, name):
        "Remove and return a random member of set ``name``"
        return self.execute_command('SPOP', name)

    def srandmember(self, name):
        "Return a random member of set ``name``"
        return self.execute_command('SRANDMEMBER', name)

    def srem(self, name, value):
        "Remove ``value`` from set ``name``"
        return self.execute_command('SREM', name, value)

    def sunion(self, keys, *args):
        "Return the union of sets specifiued by ``keys``"
        keys = list_or_args('sunion', keys, args)
        return self.execute_command('SUNION', *keys)

    def sunionstore(self, dest, keys, *args):
        """
        Store the union of sets specified by ``keys`` into a new
        set named ``dest``.  Returns the number of keys in the new set.
        """
        keys = list_or_args('sunionstore', keys, args)
        return self.execute_command('SUNIONSTORE', dest, *keys)


    #### SORTED SET COMMANDS ####
    def zadd(self, name, value, score):
        "Add member ``value`` with score ``score`` to sorted set ``name``"
        return self.execute_command('ZADD', name, score, value)

    def zcard(self, name):
        "Return the number of elements in the sorted set ``name``"
        return self.execute_command('ZCARD', name)

    def zcount(self, name, min, max):
        return self.execute_command('ZCOUNT', name, min, max)

    def zincr(self, key, member, value=1):
        "This has been deprecated, use zincrby instead"
        warnings.warn(DeprecationWarning(
            "Redis.zincr has been deprecated, use Redis.zincrby instead"
            ))
        return self.zincrby(key, member, value)

    def zincrby(self, name, value, amount=1):
        "Increment the score of ``value`` in sorted set ``name`` by ``amount``"
        return self.execute_command('ZINCRBY', name, amount, value)

    def zinter(self, dest, keys, aggregate=None):
        warnings.warn(DeprecationWarning(
            "Redis.zinter has been deprecated, use Redis.zinterstore instead"
            ))
        return self.zinterstore(dest, keys, aggregate)

    def zinterstore(self, dest, keys, aggregate=None):
        """
        Intersect multiple sorted sets specified by ``keys`` into
        a new sorted set, ``dest``. Scores in the destination will be
        aggregated based on the ``aggregate``, or SUM if none is provided.
        """
        return self._zaggregate('ZINTERSTORE', dest, keys, aggregate)

    def zrange(self, name, start, end, desc=False, withscores=False):
        """
        Return a range of values from sorted set ``name`` between
        ``start`` and ``end`` sorted in ascending order.

        ``start`` and ``end`` can be negative, indicating the end of the range.

        ``desc`` indicates to sort in descending order.

        ``withscores`` indicates to return the scores along with the values.
            The return type is a list of (value, score) pairs
        """
        if desc:
            return self.zrevrange(name, start, end, withscores)
        pieces = ['ZRANGE', name, start, end]
        if withscores:
            pieces.append('withscores')
        return self.execute_command(*pieces, **{'withscores': withscores})

    def zrangebyscore(self, name, min, max,
            start=None, num=None, withscores=False):
        """
        Return a range of values from the sorted set ``name`` with scores
        between ``min`` and ``max``.

        If ``start`` and ``num`` are specified, then return a slice of the range.

        ``withscores`` indicates to return the scores along with the values.
            The return type is a list of (value, score) pairs
        """
        if (start is not None and num is None) or \
                (num is not None and start is None):
            raise RedisError("``start`` and ``num`` must both be specified")
        pieces = ['ZRANGEBYSCORE', name, min, max]
        if start is not None and num is not None:
            pieces.extend(['LIMIT', start, num])
        if withscores:
            pieces.append('withscores')
        return self.execute_command(*pieces, **{'withscores': withscores})

    def zrank(self, name, value):
        """
        Returns a 0-based value indicating the rank of ``value`` in sorted set
        ``name``
        """
        return self.execute_command('ZRANK', name, value)

    def zrem(self, name, value):
        "Remove member ``value`` from sorted set ``name``"
        return self.execute_command('ZREM', name, value)

    def zremrangebyrank(self, name, min, max):
        """
        Remove all elements in the sorted set ``name`` with ranks between
        ``min`` and ``max``. Values are 0-based, ordered from smallest score
        to largest. Values can be negative indicating the highest scores.
        Returns the number of elements removed
        """
        return self.execute_command('ZREMRANGEBYRANK', name, min, max)

    def zremrangebyscore(self, name, min, max):
        """
        Remove all elements in the sorted set ``name`` with scores
        between ``min`` and ``max``. Returns the number of elements removed.
        """
        return self.execute_command('ZREMRANGEBYSCORE', name, min, max)

    def zrevrange(self, name, start, num, withscores=False):
        """
        Return a range of values from sorted set ``name`` between
        ``start`` and ``num`` sorted in descending order.

        ``start`` and ``num`` can be negative, indicating the end of the range.

        ``withscores`` indicates to return the scores along with the values
            as a dictionary of value => score
        """
        pieces = ['ZREVRANGE', name, start, num]
        if withscores:
            pieces.append('withscores')
        return self.execute_command(*pieces, **{'withscores': withscores})

    def zrevrank(self, name, value):
        """
        Returns a 0-based value indicating the descending rank of
        ``value`` in sorted set ``name``
        """
        return self.execute_command('ZREVRANK', name, value)

    def zscore(self, name, value):
        "Return the score of element ``value`` in sorted set ``name``"
        return self.execute_command('ZSCORE', name, value)

    def zunion(self, dest, keys, aggregate=None):
        warnings.warn(DeprecationWarning(
            "Redis.zunion has been deprecated, use Redis.zunionstore instead"
            ))
        return self.zunionstore(dest, keys, aggregate)

    def zunionstore(self, dest, keys, aggregate=None):
        """
        Union multiple sorted sets specified by ``keys`` into
        a new sorted set, ``dest``. Scores in the destination will be
        aggregated based on the ``aggregate``, or SUM if none is provided.
        """
        return self._zaggregate('ZUNIONSTORE', dest, keys, aggregate)

    def _zaggregate(self, command, dest, keys, aggregate=None):
        pieces = [command, dest, len(keys)]
        if isinstance(keys, dict):
            items = keys.items()
            keys = [i[0] for i in items]
            weights = [i[1] for i in items]
        else:
            weights = None
        pieces.extend(keys)
        if weights:
            pieces.append('WEIGHTS')
            pieces.extend(weights)
        if aggregate:
            pieces.append('AGGREGATE')
            pieces.append(aggregate)
        return self.execute_command(*pieces)

    #### HASH COMMANDS ####
    def hdel(self, name, key):
        "Delete ``key`` from hash ``name``"
        return self.execute_command('HDEL', name, key)

    def hexists(self, name, key):
        "Returns a boolean indicating if ``key`` exists within hash ``name``"
        return self.execute_command('HEXISTS', name, key)

    def hget(self, name, key):
        "Return the value of ``key`` within the hash ``name``"
        return self.execute_command('HGET', name, key)

    def hgetall(self, name):
        "Return a Python dict of the hash's name/value pairs"
        return self.execute_command('HGETALL', name)

    def hincrby(self, name, key, amount=1):
        "Increment the value of ``key`` in hash ``name`` by ``amount``"
        return self.execute_command('HINCRBY', name, key, amount)

    def hkeys(self, name):
        "Return the list of keys within hash ``name``"
        return self.execute_command('HKEYS', name)

    def hlen(self, name):
        "Return the number of elements in hash ``name``"
        return self.execute_command('HLEN', name)

    def hset(self, name, key, value):
        """
        Set ``key`` to ``value`` within hash ``name``
        Returns 1 if HSET created a new field, otherwise 0
        """
        return self.execute_command('HSET', name, key, value)

    def hsetnx(self, name, key, value):
        """
        Set ``key`` to ``value`` within hash ``name`` if ``key`` does not
        exist.  Returns 1 if HSETNX created a field, otherwise 0.
        """
        return self.execute_command("HSETNX", name, key, value)

    def hmset(self, name, mapping):
        """
        Sets each key in the ``mapping`` dict to its corresponding value
        in the hash ``name``
        """
        items = []
        for pair in mapping.iteritems():
            items.extend(pair)
        return self.execute_command('HMSET', name, *items)

    def hmget(self, name, keys):
        "Returns a list of values ordered identically to ``keys``"
        return self.execute_command('HMGET', name, *keys)

    def hvals(self, name):
        "Return the list of values within hash ``name``"
        return self.execute_command('HVALS', name)


    # channels
    def psubscribe(self, patterns):
        "Subscribe to all channels matching any pattern in ``patterns``"
        if isinstance(patterns, basestring):
            patterns = [patterns]
        response = self.execute_command('PSUBSCRIBE', *patterns)
        # this is *after* the SUBSCRIBE in order to allow for lazy and broken
        # connections that need to issue AUTH and SELECT commands
        self.subscribed = True
        return response

    def punsubscribe(self, patterns=[]):
        """
        Unsubscribe from any channel matching any pattern in ``patterns``.
        If empty, unsubscribe from all channels.
        """
        if isinstance(patterns, basestring):
            patterns = [patterns]
        return self.execute_command('PUNSUBSCRIBE', *patterns)

    def subscribe(self, channels):
        "Subscribe to ``channels``, waiting for messages to be published"
        if isinstance(channels, basestring):
            channels = [channels]
        response = self.execute_command('SUBSCRIBE', *channels)
        # this is *after* the SUBSCRIBE in order to allow for lazy and broken
        # connections that need to issue AUTH and SELECT commands
        self.subscribed = True
        return response

    def unsubscribe(self, channels=[]):
        """
        Unsubscribe from ``channels``. If empty, unsubscribe
        from all channels
        """
        if isinstance(channels, basestring):
            channels = [channels]
        return self.execute_command('UNSUBSCRIBE', *channels)

    def publish(self, channel, message):
        """
        Publish ``message`` on ``channel``.
        Returns the number of subscribers the message was delivered to.
        """
        return self.execute_command('PUBLISH', channel, message)

    def listen(self):
        "Listen for messages on channels this client has been subscribed to"
        while self.subscribed:
            r = self.parse_response('LISTEN')
            if r[0] == 'pmessage':
                msg = {
                'type': r[0],
                'pattern': r[1],
                'channel': r[2],
                'data': r[3]
                }
            else:
                msg = {
                'type': r[0],
                'pattern': None,
                'channel': r[1],
                'data': r[2]
                }
            if r[0] == 'unsubscribe' and r[2] == 0:
                self.subscribed = False
            yield msg


class Pipeline(Redis):
    """
    Pipelines provide a way to transmit multiple commands to the Redis server
    in one transmission.  This is convenient for batch processing, such as
    saving all the values in a list to Redis.

    All commands executed within a pipeline are wrapped with MULTI and EXEC
    calls. This guarantees all commands executed in the pipeline will be
    executed atomically.

    Any command raising an exception does *not* halt the execution of
    subsequent commands in the pipeline. Instead, the exception is caught
    and its instance is placed into the response list returned by execute().
    Code iterating over the response list should be able to deal with an
    instance of an exception as a potential value. In general, these will be
    ResponseError exceptions, such as those raised when issuing a command
    on a key of a different datatype.
    """
    def __init__(self, connection, transaction, charset, errors):
        self.connection = connection
        self.transaction = transaction
        self.encoding = charset
        self.errors = errors
        self.subscribed = False # NOTE not in use, but necessary
        self.reset()

    def reset(self):
        self.command_stack = []

    def _execute_command(self, command_name, command, **options):
        """
        Stage a command to be executed when execute() is next called

        Returns the current Pipeline object back so commands can be
        chained together, such as:

        pipe = pipe.set('foo', 'bar').incr('baz').decr('bang')

        At some other point, you can then run: pipe.execute(),
        which will execute all commands queued in the pipe.
        """
        # if the command_name is 'AUTH' or 'SELECT', then this command
        # must have originated after a socket connection and a call to
        # _setup_connection(). run these commands immediately without
        # buffering them.
        if command_name in ('AUTH', 'SELECT'):
            return super(Pipeline, self)._execute_command(
                command_name, command, **options)
        else:
            self.command_stack.append((command_name, command, options))
        return self

    def _execute_transaction(self, commands):
        # wrap the commands in MULTI ... EXEC statements to indicate an
        # atomic operation
        all_cmds = ''.join([c for _1, c, _2 in chain(
            (('', 'MULTI\r\n', ''),),
            commands,
            (('', 'EXEC\r\n', ''),)
            )])
        self.connection.send(all_cmds, self)
        # parse off the response for MULTI and all commands prior to EXEC
        for i in range(len(commands)+1):
            _ = self.parse_response('_')
        # parse the EXEC. we want errors returned as items in the response
        response = self.parse_response('_', catch_errors=True)

        if response is None:
            raise WatchError("Watched variable changed.")

        if len(response) != len(commands):
            raise ResponseError("Wrong number of response items from "
                "pipeline execution")
        # Run any callbacks for the commands run in the pipeline
        data = []
        for r, cmd in zip(response, commands):
            if not isinstance(r, Exception):
                if cmd[0] in self.RESPONSE_CALLBACKS:
                    r = self.RESPONSE_CALLBACKS[cmd[0]](r, **cmd[2])
            data.append(r)
        return data

    def _execute_pipeline(self, commands):
        # build up all commands into a single request to increase network perf
        all_cmds = ''.join([c for _1, c, _2 in commands])
        self.connection.send(all_cmds, self)
        data = []
        for command_name, _, options in commands:
            data.append(
                self.parse_response(command_name, catch_errors=True, **options)
                )
        return data

    def execute(self):
        "Execute all the commands in the current pipeline"
        stack = self.command_stack
        self.reset()
        if self.transaction:
            execute = self._execute_transaction
        else:
            execute = self._execute_pipeline
        try:
            return execute(stack)
        except ConnectionError:
            self.connection.disconnect()
            return execute(stack)

    def select(self, *args, **kwargs):
        raise RedisError("Cannot select a different database from a pipeline")


class Lock(object):
    """
    A shared, distributed Lock. Using Redis for locking allows the Lock
    to be shared across processes and/or machines.

    It's left to the user to resolve deadlock issues and make sure
    multiple clients play nicely together.
    """

    LOCK_FOREVER = 2**31+1 # 1 past max unix time

    def __init__(self, redis, name, timeout=None, sleep=0.1):
        """
        Create a new Lock instnace named ``name`` using the Redis client
        supplied by ``redis``.

        ``timeout`` indicates a maximum life for the lock.
        By default, it will remain locked until release() is called.

        ``sleep`` indicates the amount of time to sleep per loop iteration
        when the lock is in blocking mode and another client is currently
        holding the lock.

        Note: If using ``timeout``, you should make sure all the hosts
        that are running clients are within the same timezone and are using
        a network time service like ntp.
        """
        self.redis = redis
        self.name = name
        self.acquired_until = None
        self.timeout = timeout
        self.sleep = sleep

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def acquire(self, blocking=True):
        """
        Use Redis to hold a shared, distributed lock named ``name``.
        Returns True once the lock is acquired.

        If ``blocking`` is False, always return immediately. If the lock
        was acquired, return True, otherwise return False.
        """
        sleep = self.sleep
        timeout = self.timeout
        while 1:
            unixtime = int(time.time())
            if timeout:
                timeout_at = unixtime + timeout
            else:
                timeout_at = Lock.LOCK_FOREVER
            if self.redis.setnx(self.name, timeout_at):
                self.acquired_until = timeout_at
                return True
            # We want blocking, but didn't acquire the lock
            # check to see if the current lock is expired
            existing = long(self.redis.get(self.name) or 1)
            if existing < unixtime:
                # the previous lock is expired, attempt to overwrite it
                existing = long(self.redis.getset(self.name, timeout_at) or 1)
                if existing < unixtime:
                    # we successfully acquired the lock
                    self.acquired_until = timeout_at
                    return True
            if not blocking:
                return False
            time.sleep(sleep)

    def release(self):
        "Releases the already acquired lock"
        if self.acquired_until is None:
            raise ValueError("Cannot release an unlocked lock")
        existing = long(self.redis.get(self.name) or 1)
        # if the lock time is in the future, delete the lock
        if existing >= self.acquired_until:
            self.redis.delete(self.name)
        self.acquired_until = None

########NEW FILE########
__FILENAME__ = exceptions
"Core exceptions raised by the Redis client"

class RedisError(Exception):
    pass

class AuthenticationError(RedisError):
    pass

class ConnectionError(RedisError):
    pass

class ResponseError(RedisError):
    pass

class InvalidResponse(RedisError):
    pass

class InvalidData(RedisError):
    pass

class WatchError(RedisError):
    pass

########NEW FILE########
__FILENAME__ = connection_pool
import redis
import threading
import time
import unittest

class ConnectionPoolTestCase(unittest.TestCase):
    def test_multiple_connections(self):
        # 2 clients to the same host/port/db/pool should use the same connection
        pool = redis.ConnectionPool()
        r1 = redis.Redis(host='localhost', port=6379, db=9, connection_pool=pool)
        r2 = redis.Redis(host='localhost', port=6379, db=9, connection_pool=pool)
        self.assertEquals(r1.connection, r2.connection)

        # if one of them switches, they should have
        # separate conncetion objects
        r2.select(db=10, host='localhost', port=6379)
        self.assertNotEqual(r1.connection, r2.connection)

        conns = [r1.connection, r2.connection]
        conns.sort()

        # but returning to the original state shares the object again
        r2.select(db=9, host='localhost', port=6379)
        self.assertEquals(r1.connection, r2.connection)

        # the connection manager should still have just 2 connections
        mgr_conns = pool.get_all_connections()
        mgr_conns.sort()
        self.assertEquals(conns, mgr_conns)

    def test_threaded_workers(self):
        r = redis.Redis(host='localhost', port=6379, db=9)
        r.set('a', 'foo')
        r.set('b', 'bar')

        def _info_worker():
            for i in range(50):
                _ = r.info()
                time.sleep(0.01)

        def _keys_worker():
            for i in range(50):
                _ = r.keys()
                time.sleep(0.01)

        t1 = threading.Thread(target=_info_worker)
        t2 = threading.Thread(target=_keys_worker)
        t1.start()
        t2.start()

        for i in [t1, t2]:
            i.join()


########NEW FILE########
__FILENAME__ = lock
from __future__ import with_statement
import redis
import time
import unittest
from redis.client import Lock

class LockTestCase(unittest.TestCase):
    def setUp(self):
        self.client = redis.Redis(host='localhost', port=6379, db=9)
        self.client.flushdb()

    def tearDown(self):
        self.client.flushdb()

    def test_lock(self):
        lock = self.client.lock('foo')
        self.assert_(lock.acquire())
        self.assertEquals(self.client['foo'], str(Lock.LOCK_FOREVER))
        lock.release()
        self.assertEquals(self.client['foo'], None)

    def test_competing_locks(self):
        lock1 = self.client.lock('foo')
        lock2 = self.client.lock('foo')
        self.assert_(lock1.acquire())
        self.assertFalse(lock2.acquire(blocking=False))
        lock1.release()
        self.assert_(lock2.acquire())
        self.assertFalse(lock1.acquire(blocking=False))
        lock2.release()

    def test_timeouts(self):
        lock1 = self.client.lock('foo', timeout=1)
        lock2 = self.client.lock('foo')
        self.assert_(lock1.acquire())
        self.assertEquals(lock1.acquired_until, long(time.time()) + 1)
        self.assertEquals(lock1.acquired_until, long(self.client['foo']))
        self.assertFalse(lock2.acquire(blocking=False))
        time.sleep(2) # need to wait up to 2 seconds for lock to timeout
        self.assert_(lock2.acquire(blocking=False))
        lock2.release()

    def test_non_blocking(self):
        lock1 = self.client.lock('foo')
        self.assert_(lock1.acquire(blocking=False))
        self.assert_(lock1.acquired_until)
        lock1.release()
        self.assert_(lock1.acquired_until is None)

    def test_context_manager(self):
        with self.client.lock('foo'):
            self.assertEquals(self.client['foo'], str(Lock.LOCK_FOREVER))
        self.assertEquals(self.client['foo'], None)

########NEW FILE########
__FILENAME__ = pipeline
import redis
import unittest

class PipelineTestCase(unittest.TestCase):
    def setUp(self):
        self.client = redis.Redis(host='localhost', port=6379, db=9)
        self.client.flushdb()

    def tearDown(self):
        self.client.flushdb()

    def test_pipeline(self):
        pipe = self.client.pipeline()
        pipe.set('a', 'a1').get('a').zadd('z', 'z1', 1).zadd('z', 'z2', 4)
        pipe.zincrby('z', 'z1').zrange('z', 0, 5, withscores=True)
        self.assertEquals(pipe.execute(),
            [
                True,
                'a1',
                True,
                True,
                2.0,
                [('z1', 2.0), ('z2', 4)],
            ]
            )

    def test_invalid_command_in_pipeline(self):
        # all commands but the invalid one should be excuted correctly
        self.client['c'] = 'a'
        pipe = self.client.pipeline()
        pipe.set('a', 1).set('b', 2).lpush('c', 3).set('d', 4)
        result = pipe.execute()

        self.assertEquals(result[0], True)
        self.assertEquals(self.client['a'], '1')
        self.assertEquals(result[1], True)
        self.assertEquals(self.client['b'], '2')
        # we can't lpush to a key that's a string value, so this should
        # be a ResponseError exception
        self.assert_(isinstance(result[2], redis.ResponseError))
        self.assertEquals(self.client['c'], 'a')
        self.assertEquals(result[3], True)
        self.assertEquals(self.client['d'], '4')

        # make sure the pipe was restored to a working state
        self.assertEquals(pipe.set('z', 'zzz').execute(), [True])
        self.assertEquals(self.client['z'], 'zzz')

    def test_pipeline_cannot_select(self):
        pipe = self.client.pipeline()
        self.assertRaises(redis.RedisError,
            pipe.select, 'localhost', 6379, db=9)

    def test_pipeline_no_transaction(self):
        pipe = self.client.pipeline(transaction=False)
        pipe.set('a', 'a1').set('b', 'b1').set('c', 'c1')
        self.assertEquals(pipe.execute(), [True, True, True])
        self.assertEquals(self.client['a'], 'a1')
        self.assertEquals(self.client['b'], 'b1')
        self.assertEquals(self.client['c'], 'c1')


########NEW FILE########
__FILENAME__ = server_commands
import redis
import unittest
import datetime
import threading
import time
from distutils.version import StrictVersion

class ServerCommandsTestCase(unittest.TestCase):

    def get_client(self):
        return redis.Redis(host='localhost', port=6379, db=9)

    def setUp(self):
        self.client = self.get_client()
        self.client.flushdb()

    def tearDown(self):
        self.client.flushdb()
        for c in self.client.connection_pool.get_all_connections():
            c.disconnect()

    # GENERAL SERVER COMMANDS
    def test_dbsize(self):
        self.client['a'] = 'foo'
        self.client['b'] = 'bar'
        self.assertEquals(self.client.dbsize(), 2)

    def test_get_and_set(self):
        # get and set can't be tested independently of each other
        self.assertEquals(self.client.get('a'), None)
        byte_string = 'value'
        integer = 5
        unicode_string = unichr(3456) + u'abcd' + unichr(3421)
        self.assert_(self.client.set('byte_string', byte_string))
        self.assert_(self.client.set('integer', 5))
        self.assert_(self.client.set('unicode_string', unicode_string))
        self.assertEquals(self.client.get('byte_string'), byte_string)
        self.assertEquals(self.client.get('integer'), str(integer))
        self.assertEquals(self.client.get('unicode_string').decode('utf-8'), unicode_string)

    def test_getitem_and_setitem(self):
        self.client['a'] = 'bar'
        self.assertEquals(self.client['a'], 'bar')

    def test_delete(self):
        self.assertEquals(self.client.delete('a'), False)
        self.client['a'] = 'foo'
        self.assertEquals(self.client.delete('a'), True)

    def test_delitem(self):
        self.client['a'] = 'foo'
        del self.client['a']
        self.assertEquals(self.client['a'], None)

    def test_info(self):
        self.client['a'] = 'foo'
        self.client['b'] = 'bar'
        info = self.client.info()
        self.assert_(isinstance(info, dict))
        self.assertEquals(info['db9']['keys'], 2)

    def test_lastsave(self):
        self.assert_(isinstance(self.client.lastsave(), datetime.datetime))

    def test_ping(self):
        self.assertEquals(self.client.ping(), True)


    # KEYS
    def test_append(self):
        # invalid key type
        self.client.rpush('a', 'a1')
        self.assertRaises(redis.ResponseError, self.client.append, 'a', 'a1')
        del self.client['a']
        # real logic
        self.assertEquals(self.client.append('a', 'a1'), 2)
        self.assertEquals(self.client['a'], 'a1')
        self.assert_(self.client.append('a', 'a2'), 4)
        self.assertEquals(self.client['a'], 'a1a2')

    def test_decr(self):
        self.assertEquals(self.client.decr('a'), -1)
        self.assertEquals(self.client['a'], '-1')
        self.assertEquals(self.client.decr('a'), -2)
        self.assertEquals(self.client['a'], '-2')
        self.assertEquals(self.client.decr('a', amount=5), -7)
        self.assertEquals(self.client['a'], '-7')

    def test_exists(self):
        self.assertEquals(self.client.exists('a'), False)
        self.client['a'] = 'foo'
        self.assertEquals(self.client.exists('a'), True)

    def test_expire_and_ttl(self):
        self.assertEquals(self.client.expire('a', 10), False)
        self.client['a'] = 'foo'
        self.assertEquals(self.client.expire('a', 10), True)
        self.assertEquals(self.client.ttl('a'), 10)

    def test_expireat(self):
        expire_at = datetime.datetime.now() + datetime.timedelta(minutes=1)
        self.assertEquals(self.client.expireat('a', expire_at), False)
        self.client['a'] = 'foo'
        # expire at in unix time
        expire_at_seconds = int(time.mktime(expire_at.timetuple()))
        self.assertEquals(self.client.expireat('a', expire_at_seconds), True)
        self.assertEquals(self.client.ttl('a'), 60)
        # expire at given a datetime object
        self.client['b'] = 'bar'
        self.assertEquals(self.client.expireat('b', expire_at), True)
        self.assertEquals(self.client.ttl('b'), 60)

    def test_getset(self):
        self.assertEquals(self.client.getset('a', 'foo'), None)
        self.assertEquals(self.client.getset('a', 'bar'), 'foo')

    def test_incr(self):
        self.assertEquals(self.client.incr('a'), 1)
        self.assertEquals(self.client['a'], '1')
        self.assertEquals(self.client.incr('a'), 2)
        self.assertEquals(self.client['a'], '2')
        self.assertEquals(self.client.incr('a', amount=5), 7)
        self.assertEquals(self.client['a'], '7')

    def test_keys(self):
        self.assertEquals(self.client.keys(), [])
        keys = set(['test_a', 'test_b', 'testc'])
        for key in keys:
            self.client[key] = 1
        self.assertEquals(set(self.client.keys(pattern='test_*')),
            keys - set(['testc']))
        self.assertEquals(set(self.client.keys(pattern='test*')), keys)

    def test_mget(self):
        self.assertEquals(self.client.mget(['a', 'b']), [None, None])
        self.client['a'] = '1'
        self.client['b'] = '2'
        self.client['c'] = '3'
        self.assertEquals(self.client.mget(['a', 'other', 'b', 'c']),
            ['1', None, '2', '3'])

    def test_mset(self):
        d = {'a': '1', 'b': '2', 'c': '3'}
        self.assert_(self.client.mset(d))
        for k,v in d.iteritems():
            self.assertEquals(self.client[k], v)

    def test_msetnx(self):
        d = {'a': '1', 'b': '2', 'c': '3'}
        self.assert_(self.client.msetnx(d))
        d2 = {'a': 'x', 'd': '4'}
        self.assert_(not self.client.msetnx(d2))
        for k,v in d.iteritems():
            self.assertEquals(self.client[k], v)
        self.assertEquals(self.client['d'], None)

    def test_randomkey(self):
        self.assertEquals(self.client.randomkey(), None)
        self.client['a'] = '1'
        self.client['b'] = '2'
        self.client['c'] = '3'
        self.assert_(self.client.randomkey() in ('a', 'b', 'c'))

    def test_rename(self):
        self.client['a'] = '1'
        self.assert_(self.client.rename('a', 'b'))
        self.assertEquals(self.client['a'], None)
        self.assertEquals(self.client['b'], '1')

    def test_renamenx(self):
        self.client['a'] = '1'
        self.client['b'] = '2'
        self.assert_(not self.client.renamenx('a', 'b'))
        self.assertEquals(self.client['a'], '1')
        self.assertEquals(self.client['b'], '2')

    def test_setex(self):
        self.assertEquals(self.client.setex('a', '1', 60), True)
        self.assertEquals(self.client['a'], '1')
        self.assertEquals(self.client.ttl('a'), 60  )

    def test_setnx(self):
        self.assert_(self.client.setnx('a', '1'))
        self.assertEquals(self.client['a'], '1')
        self.assert_(not self.client.setnx('a', '2'))
        self.assertEquals(self.client['a'], '1')

    def test_substr(self):
        # invalid key type
        self.client.rpush('a', 'a1')
        self.assertRaises(redis.ResponseError, self.client.substr, 'a', 0)
        del self.client['a']
        # real logic
        self.client['a'] = 'abcdefghi'
        self.assertEquals(self.client.substr('a', 0), 'abcdefghi')
        self.assertEquals(self.client.substr('a', 2), 'cdefghi')
        self.assertEquals(self.client.substr('a', 3, 5), 'def')
        self.assertEquals(self.client.substr('a', 3, -2), 'defgh')
        self.client['a'] = 123456 # does substr work with ints?
        self.assertEquals(self.client.substr('a', 2, -2), '345')

    def test_type(self):
        self.assertEquals(self.client.type('a'), 'none')
        self.client['a'] = '1'
        self.assertEquals(self.client.type('a'), 'string')
        del self.client['a']
        self.client.lpush('a', '1')
        self.assertEquals(self.client.type('a'), 'list')
        del self.client['a']
        self.client.sadd('a', '1')
        self.assertEquals(self.client.type('a'), 'set')
        del self.client['a']
        self.client.zadd('a', '1', 1)
        self.assertEquals(self.client.type('a'), 'zset')

    def test_watch(self):
        self.client.set("a", 1)

        self.client.watch("a")
        pipeline = self.client.pipeline()
        pipeline.set("a", 2)
        self.assertEquals(pipeline.execute(), [True])

        self.client.set("b", 1)
        self.client.watch("b")
        self.get_client().set("b", 2)
        pipeline = self.client.pipeline()
        pipeline.set("b", 3)

        self.assertRaises(redis.exceptions.WatchError, pipeline.execute)

    def test_unwatch(self):
        self.assertEquals(self.client.unwatch(), True)

    # LISTS
    def make_list(self, name, l):
        for i in l:
            self.client.rpush(name, i)

    def test_blpop(self):
        self.make_list('a', 'ab')
        self.make_list('b', 'cd')
        self.assertEquals(self.client.blpop(['b', 'a'], timeout=1), ('b', 'c'))
        self.assertEquals(self.client.blpop(['b', 'a'], timeout=1), ('b', 'd'))
        self.assertEquals(self.client.blpop(['b', 'a'], timeout=1), ('a', 'a'))
        self.assertEquals(self.client.blpop(['b', 'a'], timeout=1), ('a', 'b'))
        self.assertEquals(self.client.blpop(['b', 'a'], timeout=1), None)
        self.make_list('c', 'a')
        self.assertEquals(self.client.blpop('c', timeout=1), ('c', 'a'))

    def test_brpop(self):
        self.make_list('a', 'ab')
        self.make_list('b', 'cd')
        self.assertEquals(self.client.brpop(['b', 'a'], timeout=1), ('b', 'd'))
        self.assertEquals(self.client.brpop(['b', 'a'], timeout=1), ('b', 'c'))
        self.assertEquals(self.client.brpop(['b', 'a'], timeout=1), ('a', 'b'))
        self.assertEquals(self.client.brpop(['b', 'a'], timeout=1), ('a', 'a'))
        self.assertEquals(self.client.brpop(['b', 'a'], timeout=1), None)
        self.make_list('c', 'a')
        self.assertEquals(self.client.brpop('c', timeout=1), ('c', 'a'))

    def test_lindex(self):
        # no key
        self.assertEquals(self.client.lindex('a', '0'), None)
        # key is not a list
        self.client['a'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.lindex, 'a', '0')
        del self.client['a']
        # real logic
        self.make_list('a', 'abc')
        self.assertEquals(self.client.lindex('a', '0'), 'a')
        self.assertEquals(self.client.lindex('a', '1'), 'b')
        self.assertEquals(self.client.lindex('a', '2'), 'c')

    def test_llen(self):
        # no key
        self.assertEquals(self.client.llen('a'), 0)
        # key is not a list
        self.client['a'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.llen, 'a')
        del self.client['a']
        # real logic
        self.make_list('a', 'abc')
        self.assertEquals(self.client.llen('a'), 3)

    def test_lpop(self):
        # no key
        self.assertEquals(self.client.lpop('a'), None)
        # key is not a list
        self.client['a'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.lpop, 'a')
        del self.client['a']
        # real logic
        self.make_list('a', 'abc')
        self.assertEquals(self.client.lpop('a'), 'a')
        self.assertEquals(self.client.lpop('a'), 'b')
        self.assertEquals(self.client.lpop('a'), 'c')
        self.assertEquals(self.client.lpop('a'), None)

    def test_lpush(self):
        # key is not a list
        self.client['a'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.lpush, 'a', 'a')
        del self.client['a']
        # real logic
        version = self.client.info()['redis_version']
        if StrictVersion(version) >= StrictVersion('1.3.4'):
            self.assertEqual(1, self.client.lpush('a', 'b'))
            self.assertEqual(2, self.client.lpush('a', 'a'))
        else:
            self.assert_(self.client.lpush('a', 'b'))
            self.assert_(self.client.lpush('a', 'a'))
        self.assertEquals(self.client.lindex('a', 0), 'a')
        self.assertEquals(self.client.lindex('a', 1), 'b')

    def test_lrange(self):
        # no key
        self.assertEquals(self.client.lrange('a', 0, 1), [])
        # key is not a list
        self.client['a'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.lrange, 'a', 0, 1)
        del self.client['a']
        # real logic
        self.make_list('a', 'abcde')
        self.assertEquals(self.client.lrange('a', 0, 2), ['a', 'b', 'c'])
        self.assertEquals(self.client.lrange('a', 2, 10), ['c', 'd', 'e'])

    def test_lrem(self):
        # no key
        self.assertEquals(self.client.lrem('a', 'foo'), 0)
        # key is not a list
        self.client['a'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.lrem, 'a', 'b')
        del self.client['a']
        # real logic
        self.make_list('a', 'aaaa')
        self.assertEquals(self.client.lrem('a', 'a', 1), 1)
        self.assertEquals(self.client.lrange('a', 0, 3), ['a', 'a', 'a'])
        self.assertEquals(self.client.lrem('a', 'a'), 3)
        # remove all the elements in the list means the key is deleted
        self.assertEquals(self.client.lrange('a', 0, 1), [])

    def test_lset(self):
        # no key
        self.assertRaises(redis.ResponseError, self.client.lset, 'a', 1, 'b')
        # key is not a list
        self.client['a'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.lset, 'a', 1, 'b')
        del self.client['a']
        # real logic
        self.make_list('a', 'abc')
        self.assertEquals(self.client.lrange('a', 0, 2), ['a', 'b', 'c'])
        self.assert_(self.client.lset('a', 1, 'd'))
        self.assertEquals(self.client.lrange('a', 0, 2), ['a', 'd', 'c'])

    def test_ltrim(self):
        # no key -- TODO: Not sure why this is actually true.
        self.assert_(self.client.ltrim('a', 0, 2))
        # key is not a list
        self.client['a'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.ltrim, 'a', 0, 2)
        del self.client['a']
        # real logic
        self.make_list('a', 'abc')
        self.assert_(self.client.ltrim('a', 0, 1))
        self.assertEquals(self.client.lrange('a', 0, 5), ['a', 'b'])

    def test_lpop(self):
        # no key
        self.assertEquals(self.client.lpop('a'), None)
        # key is not a list
        self.client['a'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.lpop, 'a')
        del self.client['a']
        # real logic
        self.make_list('a', 'abc')
        self.assertEquals(self.client.lpop('a'), 'a')
        self.assertEquals(self.client.lpop('a'), 'b')
        self.assertEquals(self.client.lpop('a'), 'c')
        self.assertEquals(self.client.lpop('a'), None)

    def test_rpop(self):
        # no key
        self.assertEquals(self.client.rpop('a'), None)
        # key is not a list
        self.client['a'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.rpop, 'a')
        del self.client['a']
        # real logic
        self.make_list('a', 'abc')
        self.assertEquals(self.client.rpop('a'), 'c')
        self.assertEquals(self.client.rpop('a'), 'b')
        self.assertEquals(self.client.rpop('a'), 'a')
        self.assertEquals(self.client.rpop('a'), None)

    def test_rpoplpush(self):
        # no src key
        self.make_list('b', ['b1'])
        self.assertEquals(self.client.rpoplpush('a', 'b'), None)
        # no dest key
        self.assertEquals(self.client.rpoplpush('b', 'a'), 'b1')
        self.assertEquals(self.client.lindex('a', 0), 'b1')
        del self.client['a']
        del self.client['b']
        # src key is not a list
        self.client['a'] = 'a1'
        self.assertRaises(redis.ResponseError, self.client.rpoplpush, 'a', 'b')
        del self.client['a']
        # dest key is not a list
        self.make_list('a', ['a1'])
        self.client['b'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.rpoplpush, 'a', 'b')
        del self.client['a']
        del self.client['b']
        # real logic
        self.make_list('a', ['a1', 'a2', 'a3'])
        self.make_list('b', ['b1', 'b2', 'b3'])
        self.assertEquals(self.client.rpoplpush('a', 'b'), 'a3')
        self.assertEquals(self.client.lrange('a', 0, 2), ['a1', 'a2'])
        self.assertEquals(self.client.lrange('b', 0, 4),
            ['a3', 'b1', 'b2', 'b3'])

    def test_rpush(self):
        # key is not a list
        self.client['a'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.rpush, 'a', 'a')
        del self.client['a']
        # real logic
        version = self.client.info()['redis_version']
        if StrictVersion(version) >= StrictVersion('1.3.4'):
            self.assertEqual(1, self.client.rpush('a', 'a'))
            self.assertEqual(2, self.client.rpush('a', 'b'))
        else:
            self.assert_(self.client.rpush('a', 'a'))
            self.assert_(self.client.rpush('a', 'b'))
        self.assertEquals(self.client.lindex('a', 0), 'a')
        self.assertEquals(self.client.lindex('a', 1), 'b')

    # Set commands
    def make_set(self, name, l):
        for i in l:
            self.client.sadd(name, i)

    def test_sadd(self):
        # key is not a set
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.sadd, 'a', 'a1')
        del self.client['a']
        # real logic
        members = set(['a1', 'a2', 'a3'])
        self.make_set('a', members)
        self.assertEquals(self.client.smembers('a'), members)

    def test_scard(self):
        # key is not a set
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.scard, 'a')
        del self.client['a']
        # real logic
        self.make_set('a', 'abc')
        self.assertEquals(self.client.scard('a'), 3)

    def test_sdiff(self):
        # some key is not a set
        self.make_set('a', ['a1', 'a2', 'a3'])
        self.client['b'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.sdiff, ['a', 'b'])
        del self.client['b']
        # real logic
        self.make_set('b', ['b1', 'a2', 'b3'])
        self.assertEquals(self.client.sdiff(['a', 'b']), set(['a1', 'a3']))

    def test_sdiffstore(self):
        # some key is not a set
        self.make_set('a', ['a1', 'a2', 'a3'])
        self.client['b'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.sdiffstore,
            'c', ['a', 'b'])
        del self.client['b']
        self.make_set('b', ['b1', 'a2', 'b3'])
        # dest key always gets overwritten, even if it's not a set, so don't
        # test for that
        # real logic
        self.assertEquals(self.client.sdiffstore('c', ['a', 'b']), 2)
        self.assertEquals(self.client.smembers('c'), set(['a1', 'a3']))

    def test_sinter(self):
        # some key is not a set
        self.make_set('a', ['a1', 'a2', 'a3'])
        self.client['b'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.sinter, ['a', 'b'])
        del self.client['b']
        # real logic
        self.make_set('b', ['a1', 'b2', 'a3'])
        self.assertEquals(self.client.sinter(['a', 'b']), set(['a1', 'a3']))

    def test_sinterstore(self):
        # some key is not a set
        self.make_set('a', ['a1', 'a2', 'a3'])
        self.client['b'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.sinterstore,
            'c', ['a', 'b'])
        del self.client['b']
        self.make_set('b', ['a1', 'b2', 'a3'])
        # dest key always gets overwritten, even if it's not a set, so don't
        # test for that
        # real logic
        self.assertEquals(self.client.sinterstore('c', ['a', 'b']), 2)
        self.assertEquals(self.client.smembers('c'), set(['a1', 'a3']))

    def test_sismember(self):
        # key is not a set
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.sismember, 'a', 'a')
        del self.client['a']
        # real logic
        self.make_set('a', 'abc')
        self.assertEquals(self.client.sismember('a', 'a'), True)
        self.assertEquals(self.client.sismember('a', 'b'), True)
        self.assertEquals(self.client.sismember('a', 'c'), True)
        self.assertEquals(self.client.sismember('a', 'd'), False)

    def test_smembers(self):
        # key is not a set
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.smembers, 'a')
        del self.client['a']
        # set doesn't exist
        self.assertEquals(self.client.smembers('a'), set())
        # real logic
        self.make_set('a', 'abc')
        self.assertEquals(self.client.smembers('a'), set(['a', 'b', 'c']))

    def test_smove(self):
        # src key is not set
        self.make_set('b', ['b1', 'b2'])
        self.assertEquals(self.client.smove('a', 'b', 'a1'), 0)
        # src key is not a set
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.smove,
            'a', 'b', 'a1')
        del self.client['a']
        self.make_set('a', ['a1', 'a2'])
        # dest key is not a set
        del self.client['b']
        self.client['b'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.smove,
            'a', 'b', 'a1')
        del self.client['b']
        self.make_set('b', ['b1', 'b2'])
        # real logic
        self.assert_(self.client.smove('a', 'b', 'a1'))
        self.assertEquals(self.client.smembers('a'), set(['a2']))
        self.assertEquals(self.client.smembers('b'), set(['b1', 'b2', 'a1']))

    def test_spop(self):
        # key is not set
        self.assertEquals(self.client.spop('a'), None)
        # key is not a set
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.spop, 'a')
        del self.client['a']
        # real logic
        self.make_set('a', 'abc')
        value = self.client.spop('a')
        self.assert_(value in 'abc')
        self.assertEquals(self.client.smembers('a'), set('abc') - set(value))

    def test_srandmember(self):
        # key is not set
        self.assertEquals(self.client.srandmember('a'), None)
        # key is not a set
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.srandmember, 'a')
        del self.client['a']
        # real logic
        self.make_set('a', 'abc')
        self.assert_(self.client.srandmember('a') in 'abc')

    def test_srem(self):
        # key is not set
        self.assertEquals(self.client.srem('a', 'a'), False)
        # key is not a set
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.srem, 'a', 'a')
        del self.client['a']
        # real logic
        self.make_set('a', 'abc')
        self.assertEquals(self.client.srem('a', 'd'), False)
        self.assertEquals(self.client.srem('a', 'b'), True)
        self.assertEquals(self.client.smembers('a'), set('ac'))

    def test_sunion(self):
        # some key is not a set
        self.make_set('a', ['a1', 'a2', 'a3'])
        self.client['b'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.sunion, ['a', 'b'])
        del self.client['b']
        # real logic
        self.make_set('b', ['a1', 'b2', 'a3'])
        self.assertEquals(self.client.sunion(['a', 'b']),
            set(['a1', 'a2', 'a3', 'b2']))

    def test_sunionstore(self):
        # some key is not a set
        self.make_set('a', ['a1', 'a2', 'a3'])
        self.client['b'] = 'b'
        self.assertRaises(redis.ResponseError, self.client.sunionstore,
            'c', ['a', 'b'])
        del self.client['b']
        self.make_set('b', ['a1', 'b2', 'a3'])
        # dest key always gets overwritten, even if it's not a set, so don't
        # test for that
        # real logic
        self.assertEquals(self.client.sunionstore('c', ['a', 'b']), 4)
        self.assertEquals(self.client.smembers('c'),
            set(['a1', 'a2', 'a3', 'b2']))

    # SORTED SETS
    def make_zset(self, name, d):
        for k,v in d.items():
            self.client.zadd(name, k, v)

    def test_zadd(self):
        self.make_zset('a', {'a1': 1, 'a2': 2, 'a3': 3})
        self.assertEquals(self.client.zrange('a', 0, 3), ['a1', 'a2', 'a3'])

    def test_zcard(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zcard, 'a')
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 1, 'a2': 2, 'a3': 3})
        self.assertEquals(self.client.zcard('a'), 3)

    def test_zcount(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zcount, 'a', 0, 0)
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 1, 'a2': 2, 'a3': 3})
        self.assertEquals(self.client.zcount('a', '-inf', '+inf'), 3)
        self.assertEquals(self.client.zcount('a', 1, 2), 2)
        self.assertEquals(self.client.zcount('a', 10, 20), 0)

    def test_zincrby(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zincrby, 'a', 'a1')
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 1, 'a2': 2, 'a3': 3})
        self.assertEquals(self.client.zincrby('a', 'a2'), 3.0)
        self.assertEquals(self.client.zincrby('a', 'a3', amount=5), 8.0)
        self.assertEquals(self.client.zscore('a', 'a2'), 3.0)
        self.assertEquals(self.client.zscore('a', 'a3'), 8.0)

    def test_zinterstore(self):
        self.make_zset('a', {'a1': 1, 'a2': 1, 'a3': 1})
        self.make_zset('b', {'a1': 2, 'a3': 2, 'a4': 2})
        self.make_zset('c', {'a1': 6, 'a3': 5, 'a4': 4})

        # sum, no weight
        self.assert_(self.client.zinterstore('z', ['a', 'b', 'c']))
        self.assertEquals(
            self.client.zrange('z', 0, -1, withscores=True),
            [('a3', 8), ('a1', 9)]
            )

        # max, no weight
        self.assert_(
            self.client.zinterstore('z', ['a', 'b', 'c'], aggregate='MAX')
            )
        self.assertEquals(
            self.client.zrange('z', 0, -1, withscores=True),
            [('a3', 5), ('a1', 6)]
            )

        # with weight
        self.assert_(self.client.zinterstore('z', {'a': 1, 'b': 2, 'c': 3}))
        self.assertEquals(
            self.client.zrange('z', 0, -1, withscores=True),
            [('a3', 20), ('a1', 23)]
            )


    def test_zrange(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zrange, 'a', 0, 1)
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 1, 'a2': 2, 'a3': 3})
        self.assertEquals(self.client.zrange('a', 0, 1), ['a1', 'a2'])
        self.assertEquals(self.client.zrange('a', 1, 2), ['a2', 'a3'])
        self.assertEquals(self.client.zrange('a', 0, 1, withscores=True),
            [('a1', 1.0), ('a2', 2.0)])
        self.assertEquals(self.client.zrange('a', 1, 2, withscores=True),
            [('a2', 2.0), ('a3', 3.0)])
        # a non existant key should return empty list
        self.assertEquals(self.client.zrange('b', 0, 1, withscores=True), [])


    def test_zrangebyscore(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zrangebyscore,
            'a', 0, 1)
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 1, 'a2': 2, 'a3': 3, 'a4': 4, 'a5': 5})
        self.assertEquals(self.client.zrangebyscore('a', 2, 4),
            ['a2', 'a3', 'a4'])
        self.assertEquals(self.client.zrangebyscore('a', 2, 4, start=1, num=2),
            ['a3', 'a4'])
        self.assertEquals(self.client.zrangebyscore('a', 2, 4, withscores=True),
            [('a2', 2.0), ('a3', 3.0), ('a4', 4.0)])
        # a non existant key should return empty list
        self.assertEquals(self.client.zrangebyscore('b', 0, 1, withscores=True), [])

    def test_zrank(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zrank, 'a', 'a4')
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 1, 'a2': 2, 'a3': 3, 'a4': 4, 'a5': 5})
        self.assertEquals(self.client.zrank('a', 'a1'), 0)
        self.assertEquals(self.client.zrank('a', 'a2'), 1)
        self.assertEquals(self.client.zrank('a', 'a3'), 2)
        self.assertEquals(self.client.zrank('a', 'a4'), 3)
        self.assertEquals(self.client.zrank('a', 'a5'), 4)
        # non-existent value in zset
        self.assertEquals(self.client.zrank('a', 'a6'), None)

    def test_zrem(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zrem, 'a', 'a1')
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 1, 'a2': 2, 'a3': 3})
        self.assertEquals(self.client.zrem('a', 'a2'), True)
        self.assertEquals(self.client.zrange('a', 0, 5), ['a1', 'a3'])
        self.assertEquals(self.client.zrem('a', 'b'), False)
        self.assertEquals(self.client.zrange('a', 0, 5), ['a1', 'a3'])

    def test_zremrangebyrank(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zremrangebyscore,
            'a', 0, 1)
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 1, 'a2': 2, 'a3': 3, 'a4': 4, 'a5': 5})
        self.assertEquals(self.client.zremrangebyrank('a', 1, 3), 3)
        self.assertEquals(self.client.zrange('a', 0, 5), ['a1', 'a5'])

    def test_zremrangebyscore(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zremrangebyscore,
            'a', 0, 1)
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 1, 'a2': 2, 'a3': 3, 'a4': 4, 'a5': 5})
        self.assertEquals(self.client.zremrangebyscore('a', 2, 4), 3)
        self.assertEquals(self.client.zrange('a', 0, 5), ['a1', 'a5'])
        self.assertEquals(self.client.zremrangebyscore('a', 2, 4), 0)
        self.assertEquals(self.client.zrange('a', 0, 5), ['a1', 'a5'])

    def test_zrevrange(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zrevrange,
            'a', 0, 1)
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 1, 'a2': 2, 'a3': 3})
        self.assertEquals(self.client.zrevrange('a', 0, 1), ['a3', 'a2'])
        self.assertEquals(self.client.zrevrange('a', 1, 2), ['a2', 'a1'])
        self.assertEquals(self.client.zrevrange('a', 0, 1, withscores=True),
            [('a3', 3.0), ('a2', 2.0)])
        self.assertEquals(self.client.zrevrange('a', 1, 2, withscores=True),
            [('a2', 2.0), ('a1', 1.0)])
        # a non existant key should return empty list
        self.assertEquals(self.client.zrange('b', 0, 1, withscores=True), [])

    def test_zrevrank(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zrevrank, 'a', 'a4')
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 5, 'a2': 4, 'a3': 3, 'a4': 2, 'a5': 1})
        self.assertEquals(self.client.zrevrank('a', 'a1'), 0)
        self.assertEquals(self.client.zrevrank('a', 'a2'), 1)
        self.assertEquals(self.client.zrevrank('a', 'a3'), 2)
        self.assertEquals(self.client.zrevrank('a', 'a4'), 3)
        self.assertEquals(self.client.zrevrank('a', 'a5'), 4)

    def test_zscore(self):
        # key is not a zset
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.zscore, 'a', 'a1')
        del self.client['a']
        # real logic
        self.make_zset('a', {'a1': 0, 'a2': 1, 'a3': 2})
        self.assertEquals(self.client.zscore('a', 'a1'), 0.0)
        self.assertEquals(self.client.zscore('a', 'a2'), 1.0)
        # test a non-existant member
        self.assertEquals(self.client.zscore('a', 'a4'), None)

    def test_zunionstore(self):
        self.make_zset('a', {'a1': 1, 'a2': 1, 'a3': 1})
        self.make_zset('b', {'a1': 2, 'a3': 2, 'a4': 2})
        self.make_zset('c', {'a1': 6, 'a4': 5, 'a5': 4})

        # sum, no weight
        self.assert_(self.client.zunionstore('z', ['a', 'b', 'c']))
        self.assertEquals(
            self.client.zrange('z', 0, -1, withscores=True),
            [('a2', 1), ('a3', 3), ('a5', 4), ('a4', 7), ('a1', 9)]
            )

        # max, no weight
        self.assert_(
            self.client.zunionstore('z', ['a', 'b', 'c'], aggregate='MAX')
            )
        self.assertEquals(
            self.client.zrange('z', 0, -1, withscores=True),
            [('a2', 1), ('a3', 2), ('a5', 4), ('a4', 5), ('a1', 6)]
            )

        # with weight
        self.assert_(self.client.zunionstore('z', {'a': 1, 'b': 2, 'c': 3}))
        self.assertEquals(
            self.client.zrange('z', 0, -1, withscores=True),
            [('a2', 1), ('a3', 5), ('a5', 12), ('a4', 19), ('a1', 23)]
            )


    # HASHES
    def make_hash(self, key, d):
        for k,v in d.iteritems():
            self.client.hset(key, k, v)

    def test_hget_and_hset(self):
        # key is not a hash
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.hget, 'a', 'a1')
        del self.client['a']
        # no key
        self.assertEquals(self.client.hget('a', 'a1'), None)
        # real logic
        self.make_hash('a', {'a1': 1, 'a2': 2, 'a3': 3})
        self.assertEquals(self.client.hget('a', 'a1'), '1')
        self.assertEquals(self.client.hget('a', 'a2'), '2')
        self.assertEquals(self.client.hget('a', 'a3'), '3')
        self.assertEquals(self.client.hset('a', 'a2', 5), 0)
        self.assertEquals(self.client.hget('a', 'a2'), '5')
        self.assertEquals(self.client.hset('a', 'a4', 4), 1)
        self.assertEquals(self.client.hget('a', 'a4'), '4')
        # key inside of hash that doesn't exist returns null value
        self.assertEquals(self.client.hget('a', 'b'), None)

    def test_hsetnx(self):
        # Initially set the hash field
        self.client.hsetnx('a', 'a1', 1)
        self.assertEqual(self.client.hget('a', 'a1'), '1')
        # Try and set the existing hash field to a different value
        self.client.hsetnx('a', 'a1', 2)
        self.assertEqual(self.client.hget('a', 'a1'), '1')

    def test_hmset(self):
        d = {'a': '1', 'b': '2', 'c': '3'}
        self.assert_(self.client.hmset('foo', d))
        self.assertEqual(self.client.hgetall('foo'), d)
        self.assertRaises(redis.ResponseError, self.client.hmset, 'foo', {})

    def test_hmget(self):
        d = {'a': 1, 'b': 2, 'c': 3}
        self.assert_(self.client.hmset('foo', d))
        self.assertEqual(self.client.hmget('foo', ['a', 'b', 'c']), ['1', '2', '3'])
        self.assertEqual(self.client.hmget('foo', ['a', 'c']), ['1', '3'])

    def test_hmget_empty(self):
        self.assertEqual(self.client.hmget('foo', ['a', 'b']), [None, None])

    def test_hmget_no_keys(self):
        self.assertRaises(redis.ResponseError, self.client.hmget, 'foo', [])

    def test_hdel(self):
        # key is not a hash
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.hdel, 'a', 'a1')
        del self.client['a']
        # no key
        self.assertEquals(self.client.hdel('a', 'a1'), False)
        # real logic
        self.make_hash('a', {'a1': 1, 'a2': 2, 'a3': 3})
        self.assertEquals(self.client.hget('a', 'a2'), '2')
        self.assert_(self.client.hdel('a', 'a2'))
        self.assertEquals(self.client.hget('a', 'a2'), None)

    def test_hexists(self):
        # key is not a hash
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.hexists, 'a', 'a1')
        del self.client['a']
        # no key
        self.assertEquals(self.client.hexists('a', 'a1'), False)
        # real logic
        self.make_hash('a', {'a1': 1, 'a2': 2, 'a3': 3})
        self.assertEquals(self.client.hexists('a', 'a1'), True)
        self.assertEquals(self.client.hexists('a', 'a4'), False)
        self.client.hdel('a', 'a1')
        self.assertEquals(self.client.hexists('a', 'a1'), False)

    def test_hgetall(self):
        # key is not a hash
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.hgetall, 'a')
        del self.client['a']
        # no key
        self.assertEquals(self.client.hgetall('a'), {})
        # real logic
        h = {'a1': '1', 'a2': '2', 'a3': '3'}
        self.make_hash('a', h)
        remote_hash = self.client.hgetall('a')
        self.assertEquals(h, remote_hash)

    def test_hincrby(self):
        # key is not a hash
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.hincrby, 'a', 'a1')
        del self.client['a']
        # no key should create the hash and incr the key's value to 1
        self.assertEquals(self.client.hincrby('a', 'a1'), 1)
        # real logic
        self.assertEquals(self.client.hincrby('a', 'a1'), 2)
        self.assertEquals(self.client.hincrby('a', 'a1', amount=2), 4)
        # negative values decrement
        self.assertEquals(self.client.hincrby('a', 'a1', amount=-3), 1)
        # hash that exists, but key that doesn't
        self.assertEquals(self.client.hincrby('a', 'a2', amount=3), 3)
        # finally a key that's not an int
        self.client.hset('a', 'a3', 'foo')
        self.assertRaises(redis.ResponseError, self.client.hincrby, 'a', 'a3')


    def test_hkeys(self):
        # key is not a hash
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.hkeys, 'a')
        del self.client['a']
        # no key
        self.assertEquals(self.client.hkeys('a'), [])
        # real logic
        h = {'a1': '1', 'a2': '2', 'a3': '3'}
        self.make_hash('a', h)
        keys = h.keys()
        keys.sort()
        remote_keys = self.client.hkeys('a')
        remote_keys.sort()
        self.assertEquals(keys, remote_keys)

    def test_hlen(self):
        # key is not a hash
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.hlen, 'a')
        del self.client['a']
        # no key
        self.assertEquals(self.client.hlen('a'), 0)
        # real logic
        self.make_hash('a', {'a1': 1, 'a2': 2, 'a3': 3})
        self.assertEquals(self.client.hlen('a'), 3)
        self.client.hdel('a', 'a3')
        self.assertEquals(self.client.hlen('a'), 2)

    def test_hvals(self):
        # key is not a hash
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.hvals, 'a')
        del self.client['a']
        # no key
        self.assertEquals(self.client.hvals('a'), [])
        # real logic
        h = {'a1': '1', 'a2': '2', 'a3': '3'}
        self.make_hash('a', h)
        vals = h.values()
        vals.sort()
        remote_vals = self.client.hvals('a')
        remote_vals.sort()
        self.assertEquals(vals, remote_vals)

    # SORT
    def test_sort_bad_key(self):
        # key is not set
        self.assertEquals(self.client.sort('a'), [])
        # key is a string value
        self.client['a'] = 'a'
        self.assertRaises(redis.ResponseError, self.client.sort, 'a')
        del self.client['a']

    def test_sort_basic(self):
        self.make_list('a', '3214')
        self.assertEquals(self.client.sort('a'), ['1', '2', '3', '4'])

    def test_sort_limited(self):
        self.make_list('a', '3214')
        self.assertEquals(self.client.sort('a', start=1, num=2), ['2', '3'])

    def test_sort_by(self):
        self.client['score:1'] = 8
        self.client['score:2'] = 3
        self.client['score:3'] = 5
        self.make_list('a_values', '123')
        self.assertEquals(self.client.sort('a_values', by='score:*'),
            ['2', '3', '1'])

    def test_sort_get(self):
        self.client['user:1'] = 'u1'
        self.client['user:2'] = 'u2'
        self.client['user:3'] = 'u3'
        self.make_list('a', '231')
        self.assertEquals(self.client.sort('a', get='user:*'),
            ['u1', 'u2', 'u3'])

    def test_sort_desc(self):
        self.make_list('a', '231')
        self.assertEquals(self.client.sort('a', desc=True), ['3', '2', '1'])

    def test_sort_alpha(self):
        self.make_list('a', 'ecbda')
        self.assertEquals(self.client.sort('a', alpha=True),
            ['a', 'b', 'c', 'd', 'e'])

    def test_sort_store(self):
        self.make_list('a', '231')
        self.assertEquals(self.client.sort('a', store='sorted_values'), 3)
        self.assertEquals(self.client.lrange('sorted_values', 0, 5),
            ['1', '2', '3'])

    def test_sort_all_options(self):
        self.client['user:1:username'] = 'zeus'
        self.client['user:2:username'] = 'titan'
        self.client['user:3:username'] = 'hermes'
        self.client['user:4:username'] = 'hercules'
        self.client['user:5:username'] = 'apollo'
        self.client['user:6:username'] = 'athena'
        self.client['user:7:username'] = 'hades'
        self.client['user:8:username'] = 'dionysus'

        self.client['user:1:favorite_drink'] = 'yuengling'
        self.client['user:2:favorite_drink'] = 'rum'
        self.client['user:3:favorite_drink'] = 'vodka'
        self.client['user:4:favorite_drink'] = 'milk'
        self.client['user:5:favorite_drink'] = 'pinot noir'
        self.client['user:6:favorite_drink'] = 'water'
        self.client['user:7:favorite_drink'] = 'gin'
        self.client['user:8:favorite_drink'] = 'apple juice'

        self.make_list('gods', '12345678')
        num = self.client.sort('gods', start=2, num=4, by='user:*:username',
            get='user:*:favorite_drink', desc=True, alpha=True, store='sorted')
        self.assertEquals(num, 4)
        self.assertEquals(self.client.lrange('sorted', 0, 10),
            ['vodka', 'milk', 'gin', 'apple juice'])

    # PUBSUB
    def test_pubsub(self):
        # create a new client to not polute the existing one
        r = self.get_client()
        channels = ('a1', 'a2', 'a3')
        for c in channels:
            r.subscribe(c)
        # state variable should be flipped
        self.assertEquals(r.subscribed, True)

        channels_to_publish_to = channels + ('a4',)
        messages_per_channel = 4
        def publish():
            for i in range(messages_per_channel):
                for c in channels_to_publish_to:
                    self.client.publish(c, 'a message')
                    time.sleep(0.01)
            for c in channels_to_publish_to:
                self.client.publish(c, 'unsubscribe')
                time.sleep(0.01)

        messages = []
        # should receive a message for each subscribe/unsubscribe command
        # plus a message for each iteration of the loop * num channels
        # we hide the data messages that tell the client to unsubscribe
        num_messages_to_expect = len(channels)*2 + \
            (messages_per_channel*len(channels))
        t = threading.Thread(target=publish)
        t.start()
        for msg in r.listen():
            if msg['data'] == 'unsubscribe':
                r.unsubscribe(msg['channel'])
            else:
                messages.append(msg)

        self.assertEquals(r.subscribed, False)
        self.assertEquals(len(messages), num_messages_to_expect)
        sent_types, sent_channels = {}, {}
        for msg in messages:
            msg_type = msg['type']
            channel = msg['channel']
            sent_types.setdefault(msg_type, 0)
            sent_types[msg_type] += 1
            if msg_type == 'message':
                sent_channels.setdefault(channel, 0)
                sent_channels[channel] += 1
        for channel in channels:
            self.assert_(channel in sent_channels)
            self.assertEquals(sent_channels[channel], messages_per_channel)
        self.assertEquals(sent_types['subscribe'], len(channels))
        self.assertEquals(sent_types['unsubscribe'], len(channels))
        self.assertEquals(sent_types['message'],
            len(channels) * messages_per_channel)

    ## BINARY SAFE
    # TODO add more tests
    def test_binary_get_set(self):
        self.assertTrue(self.client.set(' foo bar ', '123'))
        self.assertEqual(self.client.get(' foo bar '), '123')

        self.assertTrue(self.client.set(' foo\r\nbar\r\n ', '456'))
        self.assertEqual(self.client.get(' foo\r\nbar\r\n '), '456')

        self.assertTrue(self.client.set(' \r\n\t\x07\x13 ', '789'))
        self.assertEqual(self.client.get(' \r\n\t\x07\x13 '), '789')

        self.assertEqual(sorted(self.client.keys('*')), [' \r\n\t\x07\x13 ', ' foo\r\nbar\r\n ', ' foo bar '])

        self.assertTrue(self.client.delete(' foo bar '))
        self.assertTrue(self.client.delete(' foo\r\nbar\r\n '))
        self.assertTrue(self.client.delete(' \r\n\t\x07\x13 '))

    def test_binary_lists(self):
        mapping = {'foo bar': '123',
                   'foo\r\nbar\r\n': '456',
                   'foo\tbar\x07': '789',
                   }
        # fill in lists
        for key, value in mapping.iteritems():
            for c in value:
                self.assertTrue(self.client.rpush(key, c))

        # check that KEYS returns all the keys as they are
        self.assertEqual(sorted(self.client.keys('*')), sorted(mapping.keys()))

        # check that it is possible to get list content by key name
        for key in mapping.keys():
            self.assertEqual(self.client.lrange(key, 0, -1), list(mapping[key]))

########NEW FILE########
__FILENAME__ = datastructures
#!/usr/bin/env python
#
# Copyright (C) 2007 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""datastructures.py: Datastructures for search engine core.

"""
__docformat__ = "restructuredtext en"

import errors
from replaylog import log
import xapian
import cPickle

class Field(object):
    # Use __slots__ because we're going to have very many Field objects in
    # typical usage.
    __slots__ = 'name', 'value'

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return 'Field(%r, %r)' % (self.name, self.value)

class UnprocessedDocument(object):
    """A unprocessed document to be passed to the indexer.

    This represents an item to be processed and stored in the search engine.
    Each document will be processed by the indexer to generate a
    ProcessedDocument, which can then be stored in the search engine index.

    Note that some information in an UnprocessedDocument will not be
    represented in the ProcessedDocument: therefore, it is not possible to
    retrieve an UnprocessedDocument from the search engine index.

    An unprocessed document is a simple container with two attributes:

     - `fields` is a list of Field objects, or an iterator returning Field
       objects.
     - `id` is a string holding a unique identifier for the document (or
       None to get the database to allocate a unique identifier automatically
       when the document is added).

    """

    __slots__ = 'id', 'fields',
    def __init__(self, id=None, fields=None):
        self.id = id
        if fields is None:
            self.fields = []
        else:
            self.fields = fields

    def __repr__(self):
        return 'UnprocessedDocument(%r, %r)' % (self.id, self.fields)

class ProcessedDocument(object):
    """A processed document, as stored in the index.

    This represents an item which is ready to be stored in the search engine,
    or which has been returned by the search engine.

    """

    __slots__ = '_doc', '_fieldmappings', '_data',
    def __init__(self, fieldmappings, xapdoc=None):
        """Create a ProcessedDocument.

        `fieldmappings` is the configuration from a database connection used lookup
        the configuration to use to store each field.
    
        If supplied, `xapdoc` is a Xapian document to store in the processed
        document.  Otherwise, a new Xapian document is created.

        """
        if xapdoc is None:
            self._doc = log(xapian.Document)
        else:
            self._doc = xapdoc
        self._fieldmappings = fieldmappings
        self._data = None

    def add_term(self, field, term, wdfinc=1, positions=None):
        """Add a term to the document.

        Terms are the main unit of information used for performing searches.

        - `field` is the field to add the term to.
        - `term` is the term to add.
        - `wdfinc` is the value to increase the within-document-frequency
          measure for the term by.
        - `positions` is the positional information to add for the term.
          This may be None to indicate that there is no positional information,
          or may be an integer to specify one position, or may be a sequence of
          integers to specify several positions.  (Note that the wdf is not
          increased automatically for each position: if you add a term at 7
          positions, and the wdfinc value is 2, the total wdf for the term will
          only be increased by 2, not by 14.)

        """
        prefix = self._fieldmappings.get_prefix(field)
        if len(term) > 0:
            # We use the following check, rather than "isupper()" to ensure
            # that we match the check performed by the queryparser, regardless
            # of our locale.
            if ord(term[0]) >= ord('A') and ord(term[0]) <= ord('Z'):
                prefix = prefix + ':'

        # Note - xapian currently restricts term lengths to about 248
        # characters - except that zero bytes are encoded in two bytes, so
        # in practice a term of length 125 characters could be too long.
        # Xapian will give an error when commit() is called after such
        # documents have been added to the database.
        # As a simple workaround, we give an error here for terms over 220
        # characters, which will catch most occurrences of the error early.
        #
        # In future, it might be good to change to a hashing scheme in this
        # situation (or for terms over, say, 64 characters), where the
        # characters after position 64 are hashed (we obviously need to do this
        # hashing at search time, too).
        if len(prefix + term) > 220:
            raise errors.IndexerError("Field %r is too long: maximum length "
                                       "220 - was %d (%r)" %
                                       (field, len(prefix + term),
                                        prefix + term))

        if positions is None:
            self._doc.add_term(prefix + term, wdfinc)
        elif isinstance(positions, int):
            self._doc.add_posting(prefix + term, positions, wdfinc)
        else:
            self._doc.add_term(prefix + term, wdfinc)
            for pos in positions:
                self._doc.add_posting(prefix + term, pos, 0)

    def add_value(self, field, value, purpose=''):
        """Add a value to the document.

        Values are additional units of information used when performing
        searches.  Note that values are _not_ intended to be used to store
        information for display in the search results - use the document data
        for that.  The intention is that as little information as possible is
        stored in values, so that they can be accessed as quickly as possible
        during the search operation.
        
        Unlike terms, each document may have at most one value in each field
        (whereas there may be an arbitrary number of terms in a given field).
        If an attempt to add multiple values to a single field is made, only
        the last value added will be stored.

        """
        slot = self._fieldmappings.get_slot(field, purpose)
        self._doc.add_value(slot, value)

    def get_value(self, field, purpose=''):
        """Get a value from the document.

        """
        slot = self._fieldmappings.get_slot(field, purpose)
        return self._doc.get_value(slot)

    def prepare(self):
        """Prepare the document for adding to a xapian database.

        This updates the internal xapian document with any changes which have
        been made, and then returns it.

        """
        if self._data is not None:
            self._doc.set_data(cPickle.dumps(self._data, 2))
            self._data = None
        return self._doc

    def _get_data(self):
        if self._data is None:
            rawdata = self._doc.get_data()
            if rawdata == '':
                self._data = {}
            else:
                self._data = cPickle.loads(rawdata)
        return self._data
    def _set_data(self, data):
        if not isinstance(data, dict):
            raise TypeError("Cannot set data to any type other than a dict")
        self._data = data
    data = property(_get_data, _set_data, doc=
    """The data stored in this processed document.

    This data is a dictionary of entries, where the key is a fieldname, and the
    value is a list of strings.

    """)

    def _get_id(self):
        tl = self._doc.termlist()
        try:
            term = tl.skip_to('Q').term
            if len(term) == 0 or term[0] != 'Q':
                return None
        except StopIteration:
            return None
        return term[1:]
    def _set_id(self, id):
        tl = self._doc.termlist()
        try:
            term = tl.skip_to('Q').term
        except StopIteration:
            term = ''
        if len(term) != 0 and term[0] == 'Q':
            self._doc.remove_term(term)
        if id is not None:
            self._doc.add_term('Q' + id, 0)
    id = property(_get_id, _set_id, doc=
    """The unique ID for this document.

    """)

    def __repr__(self):
        return '<ProcessedDocument(%r)>' % (self.id)

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod (sys.modules[__name__])

########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/env python
#
# Copyright (C) 2007 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""errors.py: Exceptions for the search engine core.

"""
__docformat__ = "restructuredtext en"

class SearchEngineError(Exception):
    r"""Base class for exceptions thrown by the search engine.

    Any errors generated by xappy itself, or by xapian, will be instances of
    this class or its subclasses.

    """

class IndexerError(SearchEngineError):
    r"""Class used to report errors relating to the indexing API.

    """

class SearchError(SearchEngineError):
    r"""Class used to report errors relating to the search API.

    """


class XapianError(SearchEngineError):
    r"""Base class for exceptions thrown by the xapian.

    Any errors generated by xapian will be instances of this class or its
    subclasses.

    """

def _rebase_xapian_exceptions():
    """Add new base classes for all the xapian exceptions.

    """
    import xapian
    for name in (
                 'AssertionError',
                 'DatabaseCorruptError',
                 'DatabaseCreateError',
                 'DatabaseError',
                 'DatabaseLockError',
                 'DatabaseModifiedError',
                 'DatabaseOpeningError',
                 'DatabaseVersionError',
                 'DocNotFoundError',
                 # We skip 'Error' because it inherits directly from exception
                 # and this causes problems with method resolution order.
                 # However, we probably don't need it anyway, because it's
                 # just a base class, and shouldn't ever actually be raised.
                 # Users can catch xappy.XapianError instead.
                 'FeatureUnavailableError',
                 'InternalError',
                 'InvalidArgumentError',
                 'InvalidOperationError',
                 'LogicError',
                 'NetworkError',
                 'NetworkTimeoutError',
                 'QueryParserError',
                 'RangeError',
                 'RuntimeError',
                 'UnimplementedError',
                 ):
        xapian_exception = getattr(xapian, name, None)
        if xapian_exception is not None:
            xapian_exception.__bases__ += (XapianError, )
            globals()['Xapian' + name] = xapian_exception

_rebase_xapian_exceptions()

########NEW FILE########
__FILENAME__ = fieldactions
#!/usr/bin/env python
#
# Copyright (C) 2007 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""fieldactions.py: Definitions and implementations of field actions.

"""
__docformat__ = "restructuredtext en"

import _checkxapian
import errors
import marshall
from replaylog import log
import xapian
import parsedate

def _act_store_content(fieldname, doc, value, context):
    """Perform the STORE_CONTENT action.
    
    """
    try:
        fielddata = doc.data[fieldname]
    except KeyError:
        fielddata = []
        doc.data[fieldname] = fielddata
    fielddata.append(value)

def _act_index_exact(fieldname, doc, value, context):
    """Perform the INDEX_EXACT action.
    
    """
    doc.add_term(fieldname, value, 0)

def _act_tag(fieldname, doc, value, context):
    """Perform the TAG action.
    
    """
    doc.add_term(fieldname, value.lower(), 0)

def _act_facet(fieldname, doc, value, context, type=None):
    """Perform the FACET action.
    
    """
    if type is None or type == 'string':
        value = value.lower()
        doc.add_term(fieldname, value, 0)
        serialiser = log(xapian.StringListSerialiser,
                          doc.get_value(fieldname, 'facet'))
        serialiser.append(value)
        doc.add_value(fieldname, serialiser.get(), 'facet')
    else:
        marshaller = SortableMarshaller()
        fn = marshaller.get_marshall_function(fieldname, type)
        doc.add_value(fieldname, fn(fieldname, value), 'facet')

def _act_index_freetext(fieldname, doc, value, context, weight=1, 
                        language=None, stop=None, spell=False,
                        nopos=False,
                        allow_field_specific=True,
                        search_by_default=True):
    """Perform the INDEX_FREETEXT action.
    
    """
    termgen = log(xapian.TermGenerator)
    if language is not None:
        termgen.set_stemmer(log(xapian.Stem, language))
        
    if stop is not None:
        stopper = log(xapian.SimpleStopper)
        for term in stop:
            stopper.add (term)
        termgen.set_stopper (stopper)

    if spell:
        termgen.set_database(context.index)
        termgen.set_flags(termgen.FLAG_SPELLING)
    
    termgen.set_document(doc._doc)

    if search_by_default:
        termgen.set_termpos(context.current_position)
        # Store a copy of the field without a prefix, for non-field-specific
        # searches.
        if nopos:
            termgen.index_text_without_positions(value, weight, '')
        else:
            termgen.index_text(value, weight, '')

    if allow_field_specific:
        # Store a second copy of the term with a prefix, for field-specific
        # searches.
        prefix = doc._fieldmappings.get_prefix(fieldname)
        if len(prefix) != 0:
            termgen.set_termpos(context.current_position)
            if nopos:
                termgen.index_text_without_positions(value, weight, prefix)
            else:
                termgen.index_text(value, weight, prefix)

    # Add a gap between each field instance, so that phrase searches don't
    # match across instances.
    termgen.increase_termpos(10)
    context.current_position = termgen.get_termpos()

class SortableMarshaller(object):
    """Implementation of marshalling for sortable values.

    """
    def __init__(self, indexing=True):
        if indexing:
            self._err = errors.IndexerError
        else:
            self._err = errors.SearchError

    def marshall_string(self, fieldname, value):
        """Marshall a value for sorting in lexicograpical order.

        This returns the input as the output, since strings already sort in
        lexicographical order.

        """
        return value

    def marshall_float(self, fieldname, value):
        """Marshall a value for sorting as a floating point value.

        """
        # convert the value to a float
        try:
            value = float(value)
        except ValueError:
            raise self._err("Value supplied to field %r must be a "
                            "valid floating point number: was %r" %
                            (fieldname, value))
        return marshall.float_to_string(value)

    def marshall_date(self, fieldname, value):
        """Marshall a value for sorting as a date.

        """
        try:
            value = parsedate.date_from_string(value)
        except ValueError, e:
            raise self._err("Value supplied to field %r must be a "
                            "valid date: was %r: error is '%s'" %
                            (fieldname, value, str(e)))
        return marshall.date_to_string(value)

    def get_marshall_function(self, fieldname, sorttype):
        """Get a function used to marshall values of a given sorttype.

        """
        try:
            return {
                None: self.marshall_string,
                'string': self.marshall_string,
                'float': self.marshall_float,
                'date': self.marshall_date,
            }[sorttype]
        except KeyError:
            raise self._err("Unknown sort type %r for field %r" %
                            (sorttype, fieldname))


def _act_sort_and_collapse(fieldname, doc, value, context, type=None):
    """Perform the SORTABLE action.

    """
    marshaller = SortableMarshaller()
    fn = marshaller.get_marshall_function(fieldname, type)
    value = fn(fieldname, value)
    doc.add_value(fieldname, value, 'collsort')

class ActionContext(object):
    """The context in which an action is performed.

    This is just used to pass term generators, word positions, and the like
    around.

    """
    def __init__(self, index):
        self.current_language = None
        self.current_position = 0
        self.index = index

class FieldActions(object):
    """An object describing the actions to be performed on a field.

    The supported actions are:
    
    - `STORE_CONTENT`: store the unprocessed content of the field in the search
      engine database.  All fields which need to be displayed or used when
      displaying the search results need to be given this action.

    - `INDEX_EXACT`: index the exact content of the field as a single search
      term.  Fields whose contents need to be searchable as an "exact match"
      need to be given this action.

    - `INDEX_FREETEXT`: index the content of this field as text.  The content
      will be split into terms, allowing free text searching of the field.  Four
      optional parameters may be supplied:

      - 'weight' is a multiplier to apply to the importance of the field.  This
        must be an integer, and the default value is 1.
      - 'language' is the language to use when processing the field.  This can
        be expressed as an ISO 2-letter language code.  The supported languages
        are those supported by the xapian core in use.
      - 'stop' is an iterable of stopwords to filter out of the generated
        terms.  Note that due to Xapian design, only non-positional terms are
        affected, so this is of limited use.
      - 'spell' is a boolean flag - if true, the contents of the field will be
        used for spelling correction.
      - 'nopos' is a boolean flag - if true, positional information is not
        stored.
      - 'allow_field_specific' is a boolean flag - if False, prevents terms with the field
        prefix being generated.  This means that searches specific to this
        field will not work, and thus should only be used when only non-field
        specific searches are desired.  Defaults to True.
      - 'search_by_default' is a boolean flag - if False, the field will not be
        searched by non-field specific searches.  If True, or omitted, the
        field will be included in searches for non field-specific searches.

    - `SORTABLE`: index the content of the field such that it can be used to
      sort result sets.  It also allows result sets to be restricted to those
      documents with a field values in a given range.  One optional parameter
      may be supplied:

      - 'type' is a value indicating how to sort the field.  It has several
        possible values:

        - 'string' - sort in lexicographic (ie, alphabetical) order.
          This is the default, used if no type is set.
        - 'float' - treat the values as (decimal representations of) floating
          point numbers, and sort in numerical order.  The values in the field
          must be valid floating point numbers (according to Python's float()
          function).
        - 'date' - sort in date order.  The values must be valid dates (either
          Python datetime.date objects, or ISO 8601 format (ie, YYYYMMDD or
          YYYY-MM-DD).

    - `COLLAPSE`: index the content of the field such that it can be used to
      "collapse" result sets, such that only the highest result with each value
      of the field will be returned.

    - `TAG`: the field contains tags; these are strings, which will be matched
      in a case insensitive way, but otherwise must be exact matches.  Tag
      fields can be searched for by making an explict query (ie, using
      query_field(), but not with query_parse()).  A list of the most frequent
      tags in a result set can also be accessed easily.

    - `FACET`: the field represents a classification facet; these are strings
      which will be matched exactly, but a list of all the facets present in
      the result set can also be accessed easily - in addition, a suitable
      subset of the facets, and a selection of the facet values, present in the
      result set can be calculated.  One optional parameter may be supplied:

      - 'type' is a value indicating the type of facet contained in the field:

        - 'string' - the facet values are exact binary strings.
        - 'float' - the facet values are floating point numbers.

    """

    # See the class docstring for the meanings of the following constants.
    STORE_CONTENT = 1
    INDEX_EXACT = 2
    INDEX_FREETEXT = 3
    SORTABLE = 4 
    COLLAPSE = 5
    TAG = 6
    FACET = 7

    # Sorting and collapsing store the data in a value, but the format depends
    # on the sort type.  Easiest way to implement is to treat them as the same
    # action.
    SORT_AND_COLLAPSE = -1

    _unsupported_actions = []

    if 'tags' in _checkxapian.missing_features:
        _unsupported_actions.append(TAG)
    if 'facets' in _checkxapian.missing_features:
        _unsupported_actions.append(FACET)

    def __init__(self, fieldname):
        # Dictionary of actions, keyed by type.
        self._actions = {}
        self._fieldname = fieldname

    def add(self, field_mappings, action, **kwargs):
        """Add an action to perform on a field.

        """
        if action in self._unsupported_actions:
            raise errors.IndexerError("Action unsupported with this release of xapian")

        if action not in (FieldActions.STORE_CONTENT,
                          FieldActions.INDEX_EXACT,
                          FieldActions.INDEX_FREETEXT,
                          FieldActions.SORTABLE,
                          FieldActions.COLLAPSE,
                          FieldActions.TAG,
                          FieldActions.FACET,
                         ):
            raise errors.IndexerError("Unknown field action: %r" % action)

        info = self._action_info[action]

        # Check parameter names
        for key in kwargs.keys():
            if key not in info[1]:
                raise errors.IndexerError("Unknown parameter name for action %r: %r" % (info[0], key))

        # Fields cannot be indexed both with "EXACT" and "FREETEXT": whilst we
        # could implement this, the query parser wouldn't know what to do with
        # searches.
        if action == FieldActions.INDEX_EXACT:
            if FieldActions.INDEX_FREETEXT in self._actions:
                raise errors.IndexerError("Field %r is already marked for indexing "
                                   "as free text: cannot mark for indexing "
                                   "as exact text as well" % self._fieldname)
        if action == FieldActions.INDEX_FREETEXT:
            if FieldActions.INDEX_EXACT in self._actions:
                raise errors.IndexerError("Field %r is already marked for indexing "
                                   "as exact text: cannot mark for indexing "
                                   "as free text as well" % self._fieldname)

        # Fields cannot be indexed as more than one type for "SORTABLE": to
        # implement this, we'd need to use a different prefix for each sortable
        # type, but even then the search end wouldn't know what to sort on when
        # searching.  Also, if they're indexed as "COLLAPSE", the value must be
        # stored in the right format for the type "SORTABLE".
        if action == FieldActions.SORTABLE or action == FieldActions.COLLAPSE:
            if action == FieldActions.COLLAPSE:
                sorttype = None
            else:
                try:
                    sorttype = kwargs['type']
                except KeyError:
                    sorttype = 'string'
            kwargs['type'] = sorttype
            action = FieldActions.SORT_AND_COLLAPSE

            try:
                oldsortactions = self._actions[FieldActions.SORT_AND_COLLAPSE]
            except KeyError:
                oldsortactions = ()

            if len(oldsortactions) > 0:
                for oldsortaction in oldsortactions:
                    oldsorttype = oldsortaction['type']

                if sorttype == oldsorttype or oldsorttype is None:
                    # Use new type
                    self._actions[action] = []
                elif sorttype is None:
                    # Use old type
                    return
                else:
                    raise errors.IndexerError("Field %r is already marked for "
                                               "sorting, with a different "
                                               "sort type" % self._fieldname)

        if 'prefix' in info[3]:
            field_mappings.add_prefix(self._fieldname)
        if 'slot' in info[3]:
            purposes = info[3]['slot']
            if isinstance(purposes, basestring):
                field_mappings.add_slot(self._fieldname, purposes)
            else:
                slotnum = None
                for purpose in purposes:
                    slotnum = field_mappings.get_slot(self._fieldname, purpose)
                    if slotnum is not None:
                        break
                for purpose in purposes:
                    field_mappings.add_slot(self._fieldname, purpose, slotnum=slotnum)

        # Make an entry for the action
        if action not in self._actions:
            self._actions[action] = []

        # Check for repetitions of actions
        for old_action in self._actions[action]:
            if old_action == kwargs:
                return

        # Append the action to the list of actions
        self._actions[action].append(kwargs)

    def perform(self, doc, value, context):
        """Perform the actions on the field.

        - `doc` is a ProcessedDocument to store the result of the actions in.
        - `value` is a string holding the value of the field.
        - `context` is an ActionContext object used to keep state in.

        """
        for type, actionlist in self._actions.iteritems():
            info = self._action_info[type]            
            for kwargs in actionlist:
                info[2](self._fieldname, doc, value, context, **kwargs)

    _action_info = {
        STORE_CONTENT: ('STORE_CONTENT', (), _act_store_content, {}, ),
        INDEX_EXACT: ('INDEX_EXACT', (), _act_index_exact, {'prefix': True}, ),
        INDEX_FREETEXT: ('INDEX_FREETEXT', ('weight', 'language', 'stop', 'spell', 'nopos', 'allow_field_specific', 'search_by_default', ), 
            _act_index_freetext, {'prefix': True, }, ),
        SORTABLE: ('SORTABLE', ('type', ), None, {'slot': 'collsort',}, ),
        COLLAPSE: ('COLLAPSE', (), None, {'slot': 'collsort',}, ),
        TAG: ('TAG', (), _act_tag, {'prefix': True,}, ),
        FACET: ('FACET', ('type', ), _act_facet, {'prefix': True, 'slot': 'facet',}, ),

        SORT_AND_COLLAPSE: ('SORT_AND_COLLAPSE', ('type', ), _act_sort_and_collapse, {'slot': 'collsort',}, ),
    }

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod (sys.modules[__name__])

########NEW FILE########
__FILENAME__ = fieldmappings
#!/usr/bin/env python
#
# Copyright (C) 2007 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""fieldmappings.py: Mappings from field names to term prefixes, etc.

"""
__docformat__ = "restructuredtext en"

import cPickle as _cPickle

class FieldMappings(object):
    """Mappings from field names to term prefixes, slot values, etc.

    The following mappings are maintained:

    - a mapping from field name to the string prefix to insert at the start of
      terms.
    - a mapping from field name to the slot numbers to store the field contents
      in.

    """
    __slots__ = '_prefixes', '_prefixcount', '_slots', '_slotcount', 

    def __init__(self, serialised=None):
        """Create a new field mapping object, or unserialise a saved one.

        """
        if serialised is not None:
            (self._prefixes, self._prefixcount,
             self._slots, self._slotcount) = _cPickle.loads(serialised)
        else:
            self._prefixes = {}
            self._prefixcount = 0
            self._slots = {}
            self._slotcount = 0

    def _genPrefix(self):
        """Generate a previously unused prefix.

        Prefixes are uppercase letters, and start with 'X' (this is a Xapian
        convention, for compatibility with other Xapian tools: other starting
        letters are reserved for special meanings):

        >>> maps = FieldMappings()
        >>> maps._genPrefix()
        'XA'
        >>> maps._genPrefix()
        'XB'
        >>> [maps._genPrefix() for i in xrange(60)]
        ['XC', 'XD', 'XE', 'XF', 'XG', 'XH', 'XI', 'XJ', 'XK', 'XL', 'XM', 'XN', 'XO', 'XP', 'XQ', 'XR', 'XS', 'XT', 'XU', 'XV', 'XW', 'XX', 'XY', 'XZ', 'XAA', 'XBA', 'XCA', 'XDA', 'XEA', 'XFA', 'XGA', 'XHA', 'XIA', 'XJA', 'XKA', 'XLA', 'XMA', 'XNA', 'XOA', 'XPA', 'XQA', 'XRA', 'XSA', 'XTA', 'XUA', 'XVA', 'XWA', 'XXA', 'XYA', 'XZA', 'XAB', 'XBB', 'XCB', 'XDB', 'XEB', 'XFB', 'XGB', 'XHB', 'XIB', 'XJB']
        >>> maps = FieldMappings()
        >>> [maps._genPrefix() for i in xrange(27*26 + 5)][-10:]
        ['XVZ', 'XWZ', 'XXZ', 'XYZ', 'XZZ', 'XAAA', 'XBAA', 'XCAA', 'XDAA', 'XEAA']
        """
        res = []
        self._prefixcount += 1
        num = self._prefixcount
        while num != 0:
            ch = (num - 1) % 26
            res.append(chr(ch + ord('A')))
            num -= ch
            num = num // 26
        return 'X' + ''.join(res)

    def get_fieldname_from_prefix(self, prefix):
        """Get a fieldname from a prefix.

        If the prefix is not found, return None.

        """
        for key, val in self._prefixes.iteritems():
            if val == prefix:
                return key
        return None

    def get_prefix(self, fieldname):
        """Get the prefix used for a given field name.

        """
        return self._prefixes[fieldname]

    def get_slot(self, fieldname, purpose):
        """Get the slot number used for a given field name and purpose.

        """
        return self._slots[(fieldname, purpose)]

    def add_prefix(self, fieldname):
        """Allocate a prefix for the given field.

        If a prefix is already allocated for this field, this has no effect.

        """
        if fieldname in self._prefixes:
            return
        self._prefixes[fieldname] = self._genPrefix()

    def add_slot(self, fieldname, purpose, slotnum=None):
        """Allocate a slot number for the given field and purpose.

        If a slot number is already allocated for this field and purpose, this
        has no effect.

        Returns the slot number allocated for the field and purpose (whether
        newly allocated, or previously allocated).

        If `slotnum` is supplied, the number contained in it is used to
        allocate the new slot, instead of allocating a new number.  No checks
        will be made to ensure that the slot number doesn't collide with
        existing (or later allocated) numbers: the main purpose of this
        parameter is to share allocations - ie, to collide deliberately.

        """
        try:
            return self._slots[(fieldname, purpose)]
        except KeyError:
            pass

        if slotnum is None:
            self._slots[(fieldname, purpose)] = self._slotcount
            self._slotcount += 1
            return self._slotcount - 1
        else:
            self._slots[(fieldname, purpose)] = slotnum
            return slotnum

    def serialise(self):
        """Serialise the field mappings to a string.

        This can be unserialised by passing the result of this method to the
        constructor of a new FieldMappings object.

        """
        return _cPickle.dumps((self._prefixes,
                               self._prefixcount,
                               self._slots,
                               self._slotcount,
                              ), 2)

########NEW FILE########
__FILENAME__ = highlight
#!/usr/bin/env python
#
# Copyright (C) 2007 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""highlight.py: Highlight and summarise text.

"""
__docformat__ = "restructuredtext en"

import re
import xapian

class Highlighter(object):
    """Class for highlighting text and creating contextual summaries.

    >>> hl = Highlighter("en")
    >>> hl.makeSample('Hello world.', ['world'])
    'Hello world.'
    >>> hl.highlight('Hello world', ['world'], ('<', '>'))
    'Hello <world>'

    """

    # split string into words, spaces, punctuation and markup tags
    _split_re = re.compile(r'<\w+[^>]*>|</\w+>|[\w\'&]+|\s+|[^\w\'\s<>/]+')
    
    # which means:
    # < wordchars non-wordchars >
    #   OR
    # </ wordchars >
    #   OR
    # wordchars and apostrophes and ampersands
    #   OR
    # whitespace
    #   OR
    # other things

    def __init__(self, language_code='en', stemmer=None):
        """Create a new highlighter for the specified language.

        """
        if stemmer is not None:
            self.stem = stemmer
        else:
            self.stem = xapian.Stem(language_code)

    def _split_text(self, text, strip_tags=False):
        """Split some text into words and non-words.

        - `text` is the text to process.  It may be a unicode object or a utf-8
          encoded simple string.
        - `strip_tags` is a flag - False to keep tags, True to strip all tags
          from the output.

        Returns a list of utf-8 encoded simple strings.

        """
        if isinstance(text, unicode):
            text = text.encode('utf-8')

        words = self._split_re.findall(text)
        if strip_tags:
            return [w for w in words if w[0] != '<']
        else:
            return words

    def _strip_prefix(self, term):
        """Strip the prefix off a term.

        Prefixes are any initial capital letters, with the exception that R always
        ends a prefix, even if followed by capital letters.

        >>> hl = Highlighter("en")
        >>> print hl._strip_prefix('hello')
        hello
        >>> print hl._strip_prefix('Rhello')
        hello
        >>> print hl._strip_prefix('XARHello')
        Hello
        >>> print hl._strip_prefix('XAhello')
        hello
        >>> print hl._strip_prefix('XAh')
        h
        >>> print hl._strip_prefix('XA')
        <BLANKLINE>
        >>> print hl._strip_prefix('900')
        900
        >>> print hl._strip_prefix('XA900')
        900

        """
        for p in xrange(len(term)):
            if not term[p].isupper():
                return term[p:]
            elif term[p] == 'R':
                return term[p+1:]
        return ''

    def _query_to_stemmed_words(self, query):
        """Convert a query to a list of stemmed words.

        - `query` is the query to parse: it may be xapian.Query object, or a
          sequence of terms.

        """
        if isinstance(query, xapian.Query):
            return [self._strip_prefix(t) for t in query]
        else:
            return [self.stem(q.lower()) for q in query]


    def makeSample(self, text, query, maxlen=600, hl=None, ellipsis='..', strict_length=False):
        """Make a contextual summary from the supplied text.

        This basically works by splitting the text into phrases, counting the query
        terms in each, and keeping those with the most.

        Any markup tags in the text will be stripped.

        `text` is the source text to summarise.
        `query` is either a Xapian query object or a list of (unstemmed) term strings.
        `maxlen` is the maximum length of the generated summary.
        `hl` is a pair of strings to insert around highlighted terms, e.g. ('<b>', '</b>')
        `ellipsis` is the separating ellipsis to use
        `strict_length` stops the sample from truncating the last interesting phrase found, at the cost of not using all its allotted characters

        """

        # coerce maxlen into an int, otherwise truncation doesn't happen
        maxlen = int(maxlen)

        words = self._split_text(text, True)
        terms = self._query_to_stemmed_words(query)
        
        # build blocks delimited by puncuation, and count matching words in each block
        # blocks[n] is a block [firstword, endword, charcount, termcount, selected]
        blocks = []
        start = end = count = blockchars = 0

        while end < len(words):
            blockchars += len(words[end])
            if words[end].isalnum():
                if self.stem(words[end].lower()) in terms:
                    count += 1
                end += 1
            elif words[end] in ',.;:?!\n':
                end += 1
                blocks.append([start, end, blockchars, count, False])
                start = end
                blockchars = 0
                count = 0
            else:
                end += 1
        if start != end:
            blocks.append([start, end, blockchars, count, False])
        if len(blocks) == 0:
            return ''

        # select high-scoring blocks first, down to zero-scoring
        chars = 0
        for count in xrange(3, -1, -1):
            for b in blocks:
                if b[3] >= count:
                    if not strict_length or chars == 0 or chars + b[2] < maxlen:
                        b[4] = True
                    chars += b[2]
                    if chars >= maxlen: break
            if chars >= maxlen: break

        # assemble summary
        words2 = []
        lastblock = -1
        for i, b in enumerate(blocks):
            if b[4]:
                if i != lastblock + 1:
                    words2.append(ellipsis)
                words2.extend(words[b[0]:b[1]])
                lastblock = i

        if not blocks[-1][4]:
            words2.append(ellipsis)

        # trim down to maxlen
        l = 0
        for i in xrange (len (words2)):
            if words2[i] != ellipsis:
                l += len (words2[i])
            if l >= maxlen:
                words2[i:] = [ellipsis]
                break

        if hl is None:
            return ''.join(words2)
        else:
            return self._hl(words2, terms, hl)

    def highlight(self, text, query, hl, strip_tags=False):
        """Add highlights (string prefix/postfix) to a string.

        `text` is the source to highlight.
        `query` is either a Xapian query object or a list of (unstemmed) term strings.
        `hl` is a pair of highlight strings, e.g. ('<i>', '</i>')
        `strip_tags` strips HTML markout iff True

        >>> hl = Highlighter()
        >>> qp = xapian.QueryParser()
        >>> q = qp.parse_query('cat dog')
        >>> tags = ('[[', ']]')
        >>> hl.highlight('The cat went Dogging; but was <i>dog tired</i>.', q, tags)
        'The [[cat]] went [[Dogging]]; but was <i>[[dog]] tired</i>.'
        >>> q = qp.parse_query('cat went')
        >>> tags = ('[[', ']]')
        >>> hl.highlight('The cat went Dogging; but was <i>dog tired</i>.', q, tags)
        'The [[cat went]] Dogging; but was <i>dog tired</i>.'

        """
        words = self._split_text(text, strip_tags)
        terms = self._query_to_stemmed_words(query)
        return self._hl(words, terms, hl)

    def _hl(self, words, terms, hl):
        """Add highlights to a list of words.
        
        `words` is the list of words and non-words to be highlighted..
        `terms` is the list of stemmed words to look for.

        """
        out = []
        interim = []
        
        def flush_interim():
            # interim should be wrapped in hl[0], hl[1] except
            # that pure whitespace at the end of interim should
            # be flushed to out *after* the hl[1]
            space = []
            highlighted = interim[:]
            while highlighted[-1].isspace():
                space = [ highlighted[-1] ] + space
                highlighted = highlighted[:-1]
            highlighted[0] = hl[0] + highlighted[0]
            highlighted[-1] = highlighted[-1] + hl[1]
            out.extend(highlighted)
            out.extend(space)
            return []
        
        for i, w in enumerate(words):
            if w.isspace():
                if len(interim)>0:
                    interim.append(w)
                else:
                    out.append(w)
            else:
                # HACK - more forgiving about stemmed terms 
                wl = w.lower()
                if wl in terms or self.stem(wl) in terms:
                    interim.append(w)
                else:
                    if len(interim) > 0:
                        interim = flush_interim()
                    out.append(w)
        if len(interim) > 0:
            interim = flush_interim()

        return ''.join(out)


__test__ = {
    'no_punc': r'''

    Test the highlighter's behaviour when there is no punctuation in the sample
    text (regression test - used to return no output):
    >>> hl = Highlighter("en")
    >>> hl.makeSample('Hello world', ['world'])
    'Hello world'

    ''',

    'stem_levels': r'''

    Test highlighting of words, and how it works with stemming:
    >>> hl = Highlighter("en")

    # "word" and "wording" stem to "word", so the following 4 calls all return
    # the same thing
    >>> hl.makeSample('Hello. word. wording. wordinging.', ['word'], hl='<>')
    'Hello. <word>. <wording>. wordinging.'
    >>> hl.highlight('Hello. word. wording. wordinging.', ['word'], '<>')
    'Hello. <word>. <wording>. wordinging.'
    >>> hl.makeSample('Hello. word. wording. wordinging.', ['wording'], hl='<>')
    'Hello. <word>. <wording>. wordinging.'
    >>> hl.highlight('Hello. word. wording. wordinging.', ['wording'], '<>')
    'Hello. <word>. <wording>. wordinging.'

    # "wordinging" stems to "wording", so only the last two words are
    # highlighted for this one.
    >>> hl.makeSample('Hello. word. wording. wordinging.', ['wordinging'], hl='<>')
    'Hello. word. <wording>. <wordinging>.'
    >>> hl.highlight('Hello. word. wording. wordinging.', ['wordinging'], '<>')
    'Hello. word. <wording>. <wordinging>.'
    ''',

    'supplied_stemmer': r'''

    Test behaviour if we pass in our own stemmer:
    >>> stem = xapian.Stem('en')
    >>> hl = Highlighter(stemmer=stem)
    >>> hl.highlight('Hello. word. wording. wordinging.', ['word'], '<>')
    'Hello. <word>. <wording>. wordinging.'

    ''',

    'unicode': r'''

    Test behaviour if we pass in unicode input:
    >>> hl = Highlighter('en')
    >>> hl.highlight(u'Hello\xf3. word. wording. wordinging.', ['word'], '<>')
    'Hello\xc3\xb3. <word>. <wording>. wordinging.'

    ''',

    'no_sample': r'''

    Test behaviour if we pass in unicode input:
    >>> hl = Highlighter('en')
    >>> hl.makeSample(u'', ['word'])
    ''

    ''',

    'short_samples': r'''

    >>> hl = Highlighter('en')
    >>> hl.makeSample("A boring start.  Hello world indeed.  A boring end.", ['hello'], 20, ('<', '>'))
    '..  <Hello> world ..'
    >>> hl.makeSample("A boring start.  Hello world indeed.  A boring end.", ['hello'], 40, ('<', '>'))
    'A boring start.  <Hello> world indeed...'
    >>> hl.makeSample("A boring start.  Hello world indeed.  A boring end.", ['boring'], 40, ('<', '>'))
    'A <boring> start...  A <boring> end.'

    ''',

    'apostrophes': r'''

    >>> hl = Highlighter('en')
    >>> hl.makeSample("A boring start.  Hello world's indeed.  A boring end.", ['world'], 40, ('<', '>'))
    "A boring start.  Hello <world's> indeed..."

    ''',

}

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod (sys.modules[__name__])

########NEW FILE########
__FILENAME__ = indexerconnection
#!/usr/bin/env python
#
# Copyright (C) 2007 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""indexerconnection.py: A connection to the search engine for indexing.

"""
__docformat__ = "restructuredtext en"

import _checkxapian
import cPickle
import xapian

from datastructures import *
import errors
from fieldactions import *
import fieldmappings
import memutils
from replaylog import log

class IndexerConnection(object):
    """A connection to the search engine for indexing.

    """

    def __init__(self, indexpath):
        """Create a new connection to the index.

        There may only be one indexer connection for a particular database open
        at a given time.  Therefore, if a connection to the database is already
        open, this will raise a xapian.DatabaseLockError.

        If the database doesn't already exist, it will be created.

        """
        self._index = log(xapian.WritableDatabase, indexpath, xapian.DB_CREATE_OR_OPEN)
        self._indexpath = indexpath

        # Read existing actions.
        self._field_actions = {}
        self._field_mappings = fieldmappings.FieldMappings()
        self._facet_hierarchy = {}
        self._facet_query_table = {}
        self._next_docid = 0
        self._config_modified = False
        self._load_config()

        # Set management of the memory used.
        # This can be removed once Xapian implements this itself.
        self._mem_buffered = 0
        self.set_max_mem_use()

    def set_max_mem_use(self, max_mem=None, max_mem_proportion=None):
        """Set the maximum memory to use.

        This call allows the amount of memory to use to buffer changes to be
        set.  This will affect the speed of indexing, but should not result in
        other changes to the indexing.

        Note: this is an approximate measure - the actual amount of memory used
        max exceed the specified amount.  Also, note that future versions of
        xapian are likely to implement this differently, so this setting may be
        entirely ignored.

        The absolute amount of memory to use (in bytes) may be set by setting
        max_mem.  Alternatively, the proportion of the available memory may be
        set by setting max_mem_proportion (this should be a value between 0 and
        1).

        Setting too low a value will result in excessive flushing, and very
        slow indexing.  Setting too high a value will result in excessive
        buffering, leading to swapping, and very slow indexing.

        A reasonable default for max_mem_proportion for a system which is
        dedicated to indexing is probably 0.5: if other tasks are also being
        performed on the system, the value should be lowered.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if max_mem is not None and max_mem_proportion is not None:
            raise errors.IndexerError("Only one of max_mem and "
                                       "max_mem_proportion may be specified")

        if max_mem is None and max_mem_proportion is None:
            self._max_mem = None

        if max_mem_proportion is not None:
            physmem = memutils.get_physical_memory()
            if physmem is not None:
                max_mem = int(physmem * max_mem_proportion)

        self._max_mem = max_mem

    def _store_config(self):
        """Store the configuration for the database.

        Currently, this stores the configuration in a file in the database
        directory, so changes to it are not protected by transactions.  When
        support is available in xapian for storing metadata associated with
        databases. this will be used instead of a file.

        """
        assert self._index is not None

        config_str = cPickle.dumps((
                                     self._field_actions,
                                     self._field_mappings.serialise(),
                                     self._facet_hierarchy,
                                     self._facet_query_table,
                                     self._next_docid,
                                    ), 2)
        log(self._index.set_metadata, '_xappy_config', config_str)

        self._config_modified = False

    def _load_config(self):
        """Load the configuration for the database.

        """
        assert self._index is not None

        config_str = log(self._index.get_metadata, '_xappy_config')
        if len(config_str) == 0:
            return

        try:
            (self._field_actions, mappings, self._facet_hierarchy, self._facet_query_table, self._next_docid) = cPickle.loads(config_str)
        except ValueError:
            # Backwards compatibility - configuration used to lack _facet_hierarchy and _facet_query_table
            (self._field_actions, mappings, self._next_docid) = cPickle.loads(config_str)
            self._facet_hierarchy = {}
            self._facet_query_table = {}
        self._field_mappings = fieldmappings.FieldMappings(mappings)

        self._config_modified = False

    def _allocate_id(self):
        """Allocate a new ID.

        """
        while True:
            idstr = "%x" % self._next_docid
            self._next_docid += 1
            if not self._index.term_exists('Q' + idstr):
                break
        self._config_modified = True
        return idstr

    def add_field_action(self, fieldname, fieldtype, **kwargs):
        """Add an action to be performed on a field.

        Note that this change to the configuration will not be preserved on
        disk until the next call to flush().

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if fieldname in self._field_actions:
            actions = self._field_actions[fieldname]
        else:
            actions = FieldActions(fieldname)
            self._field_actions[fieldname] = actions
        actions.add(self._field_mappings, fieldtype, **kwargs)
        self._config_modified = True

    def clear_field_actions(self, fieldname):
        """Clear all actions for the specified field.

        This does not report an error if there are already no actions for the
        specified field.

        Note that this change to the configuration will not be preserved on
        disk until the next call to flush().

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if fieldname in self._field_actions:
            del self._field_actions[fieldname]
            self._config_modified = True

    def get_fields_with_actions(self):
        """Get a list of field names which have actions defined.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        return self._field_actions.keys()

    def process(self, document):
        """Process an UnprocessedDocument with the settings in this database.

        The resulting ProcessedDocument is returned.

        Note that this processing will be automatically performed if an
        UnprocessedDocument is supplied to the add() or replace() methods of
        IndexerConnection.  This method is exposed to allow the processing to
        be performed separately, which may be desirable if you wish to manually
        modify the processed document before adding it to the database, or if
        you want to split processing of documents from adding documents to the
        database for performance reasons.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        result = ProcessedDocument(self._field_mappings)
        result.id = document.id
        context = ActionContext(self._index)

        for field in document.fields:
            try:
                actions = self._field_actions[field.name]
            except KeyError:
                # If no actions are defined, just ignore the field.
                continue
            actions.perform(result, field.value, context)

        return result

    def _get_bytes_used_by_doc_terms(self, xapdoc):
        """Get an estimate of the bytes used by the terms in a document.

        (This is a very rough estimate.)

        """
        count = 0
        for item in xapdoc.termlist():
            # The term may also be stored in the spelling correction table, so
            # double the amount used.
            count += len(item.term) * 2

            # Add a few more bytes for holding the wdf, and other bits and
            # pieces.
            count += 8

        # Empirical observations indicate that about 5 times as much memory as
        # the above calculation predicts is used for buffering in practice.
        return count * 5

    def add(self, document):
        """Add a new document to the search engine index.

        If the document has a id set, and the id already exists in
        the database, an exception will be raised.  Use the replace() method
        instead if you wish to overwrite documents.

        Returns the id of the newly added document (making up a new
        unique ID if no id was set).

        The supplied document may be an instance of UnprocessedDocument, or an
        instance of ProcessedDocument.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if not hasattr(document, '_doc'):
            # It's not a processed document.
            document = self.process(document)

        # Ensure that we have a id
        orig_id = document.id
        if orig_id is None:
            id = self._allocate_id()
            document.id = id
        else:
            id = orig_id
            if self._index.term_exists('Q' + id):
                raise errors.IndexerError("Document ID of document supplied to add() is not unique.")
            
        # Add the document.
        xapdoc = document.prepare()
        self._index.add_document(xapdoc)

        if self._max_mem is not None:
            self._mem_buffered += self._get_bytes_used_by_doc_terms(xapdoc)
            if self._mem_buffered > self._max_mem:
                self.flush()

        if id is not orig_id:
            document.id = orig_id
        return id

    def replace(self, document):
        """Replace a document in the search engine index.

        If the document does not have a id set, an exception will be
        raised.

        If the document has a id set, and the id does not already
        exist in the database, this method will have the same effect as add().

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if not hasattr(document, '_doc'):
            # It's not a processed document.
            document = self.process(document)

        # Ensure that we have a id
        id = document.id
        if id is None:
            raise errors.IndexerError("No document ID set for document supplied to replace().")

        xapdoc = document.prepare()
        self._index.replace_document('Q' + id, xapdoc)

        if self._max_mem is not None:
            self._mem_buffered += self._get_bytes_used_by_doc_terms(xapdoc)
            if self._mem_buffered > self._max_mem:
                self.flush()

    def _make_synonym_key(self, original, field):
        """Make a synonym key (ie, the term or group of terms to store in
        xapian).

        """
        if field is not None:
            prefix = self._field_mappings.get_prefix(field)
        else:
            prefix = ''
        original = original.lower()
        # Add the prefix to the start of each word.
        return ' '.join((prefix + word for word in original.split(' ')))

    def add_synonym(self, original, synonym, field=None,
                    original_field=None, synonym_field=None):
        """Add a synonym to the index.

         - `original` is the word or words which will be synonym expanded in
           searches (if multiple words are specified, each word should be
           separated by a single space).
         - `synonym` is a synonym for `original`.
         - `field` is the field which the synonym is specific to.  If no field
           is specified, the synonym will be used for searches which are not
           specific to any particular field.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if original_field is None:
            original_field = field
        if synonym_field is None:
            synonym_field = field
        key = self._make_synonym_key(original, original_field)
        # FIXME - this only works for exact fields which have no upper case
        # characters, or single words
        value = self._make_synonym_key(synonym, synonym_field)
        self._index.add_synonym(key, value)

    def remove_synonym(self, original, synonym, field=None):
        """Remove a synonym from the index.

         - `original` is the word or words which will be synonym expanded in
           searches (if multiple words are specified, each word should be
           separated by a single space).
         - `synonym` is a synonym for `original`.
         - `field` is the field which this synonym is specific to.  If no field
           is specified, the synonym will be used for searches which are not
           specific to any particular field.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        key = self._make_synonym_key(original, field)
        self._index.remove_synonym(key, synonym.lower())

    def clear_synonyms(self, original, field=None):
        """Remove all synonyms for a word (or phrase).

         - `field` is the field which this synonym is specific to.  If no field
           is specified, the synonym will be used for searches which are not
           specific to any particular field.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        key = self._make_synonym_key(original, field)
        self._index.clear_synonyms(key)

    def _assert_facet(self, facet):
        """Raise an error if facet is not a declared facet field.

        """
        for action in self._field_actions[facet]._actions:
            if action == FieldActions.FACET:
                return
        raise errors.IndexerError("Field %r is not indexed as a facet" % facet)

    def add_subfacet(self, subfacet, facet):
        """Add a subfacet-facet relationship to the facet hierarchy.
        
        Any existing relationship for that subfacet is replaced.

        Raises a KeyError if either facet or subfacet is not a field,
        and an IndexerError if either facet or subfacet is not a facet field.
        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        self._assert_facet(facet)
        self._assert_facet(subfacet)
        self._facet_hierarchy[subfacet] = facet
        self._config_modified = True

    def remove_subfacet(self, subfacet):
        """Remove any existing facet hierarchy relationship for a subfacet.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if subfacet in self._facet_hierarchy:
            del self._facet_hierarchy[subfacet]
            self._config_modified = True

    def get_subfacets(self, facet):
        """Get a list of subfacets of a facet.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        return [k for k, v in self._facet_hierarchy.iteritems() if v == facet] 

    FacetQueryType_Preferred = 1;
    FacetQueryType_Never = 2;
    def set_facet_for_query_type(self, query_type, facet, association):
        """Set the association between a query type and a facet.

        The value of `association` must be one of
        IndexerConnection.FacetQueryType_Preferred,
        IndexerConnection.FacetQueryType_Never or None. A value of None removes
        any previously set association.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if query_type is None:
            raise errors.IndexerError("Cannot set query type information for None")
        self._assert_facet(facet)
        if query_type not in self._facet_query_table:
            self._facet_query_table[query_type] = {}
        if association is None:
            if facet in self._facet_query_table[query_type]:
                del self._facet_query_table[query_type][facet]
        else:
            self._facet_query_table[query_type][facet] = association;
        if self._facet_query_table[query_type] == {}:
            del self._facet_query_table[query_type]
        self._config_modified = True

    def get_facets_for_query_type(self, query_type, association):
        """Get the set of facets associated with a query type.

        Only those facets associated with the query type in the specified
        manner are returned; `association` must be one of
        IndexerConnection.FacetQueryType_Preferred or
        IndexerConnection.FacetQueryType_Never.

        If the query type has no facets associated with it, None is returned.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if query_type not in self._facet_query_table:
            return None
        facet_dict = self._facet_query_table[query_type]
        return set([facet for facet, assoc in facet_dict.iteritems() if assoc == association])

    def set_metadata(self, key, value):
        """Set an item of metadata stored in the connection.

        The value supplied will be returned by subsequent calls to
        get_metadata() which use the same key.

        Keys with a leading underscore are reserved for internal use - you
        should not use such keys unless you really know what you are doing.

        This will store the value supplied in the database.  It will not be
        visible to readers (ie, search connections) until after the next flush.

        The key is limited to about 200 characters (the same length as a term
        is limited to).  The value can be several megabytes in size.

        To remove an item of metadata, simply call this with a `value`
        parameter containing an empty string.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if not hasattr(self._index, 'set_metadata'):
            raise errors.IndexerError("Version of xapian in use does not support metadata")
        log(self._index.set_metadata, key, value)

    def get_metadata(self, key):
        """Get an item of metadata stored in the connection.

        This returns a value stored by a previous call to set_metadata.

        If the value is not found, this will return the empty string.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if not hasattr(self._index, 'get_metadata'):
            raise errors.IndexerError("Version of xapian in use does not support metadata")
        return log(self._index.get_metadata, key)

    def delete(self, id):
        """Delete a document from the search engine index.

        If the id does not already exist in the database, this method
        will have no effect (and will not report an error).

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        self._index.delete_document('Q' + id)

    def flush(self):
        """Apply recent changes to the database.

        If an exception occurs, any changes since the last call to flush() may
        be lost.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if self._config_modified:
            self._store_config()
        self._index.flush()
        self._mem_buffered = 0

    def close(self):
        """Close the connection to the database.

        It is important to call this method before allowing the class to be
        garbage collected, because it will ensure that any un-flushed changes
        will be flushed.  It also ensures that the connection is cleaned up
        promptly.

        No other methods may be called on the connection after this has been
        called.  (It is permissible to call close() multiple times, but
        only the first call will have any effect.)

        If an exception occurs, the database will be closed, but changes since
        the last call to flush may be lost.

        """
        if self._index is None:
            return
        try:
            self.flush()
        finally:
            # There is currently no "close()" method for xapian databases, so
            # we have to rely on the garbage collector.  Since we never copy
            # the _index property out of this class, there should be no cycles,
            # so the standard python implementation should garbage collect
            # _index straight away.  A close() method is planned to be added to
            # xapian at some point - when it is, we should call it here to make
            # the code more robust.
            self._index = None
            self._indexpath = None
            self._field_actions = None
            self._config_modified = False

    def get_doccount(self):
        """Count the number of documents in the database.

        This count will include documents which have been added or removed but
        not yet flushed().

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        return self._index.get_doccount()

    def iterids(self):
        """Get an iterator which returns all the ids in the database.

        The unqiue_ids are currently returned in binary lexicographical sort
        order, but this should not be relied on.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        return PrefixedTermIter('Q', self._index.allterms())

    def get_document(self, id):
        """Get the document with the specified unique ID.

        Raises a KeyError if there is no such document.  Otherwise, it returns
        a ProcessedDocument.

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        postlist = self._index.postlist('Q' + id)
        try:
            plitem = postlist.next()
        except StopIteration:
            # Unique ID not found
            raise KeyError('Unique ID %r not found' % id)
        try:
            postlist.next()
            raise errors.IndexerError("Multiple documents " #pragma: no cover
                                       "found with same unique ID")
        except StopIteration:
            # Only one instance of the unique ID found, as it should be.
            pass

        result = ProcessedDocument(self._field_mappings)
        result.id = id
        result._doc = self._index.get_document(plitem.docid)
        return result

    def iter_synonyms(self, prefix=""):
        """Get an iterator over the synonyms.

         - `prefix`: if specified, only synonym keys with this prefix will be
           returned.

        The iterator returns 2-tuples, in which the first item is the key (ie,
        a 2-tuple holding the term or terms which will be synonym expanded,
        followed by the fieldname specified (or None if no fieldname)), and the
        second item is a tuple of strings holding the synonyms for the first
        item.

        These return values are suitable for the dict() builtin, so you can
        write things like:

         >>> conn = IndexerConnection('foo')
         >>> conn.add_synonym('foo', 'bar')
         >>> conn.add_synonym('foo bar', 'baz')
         >>> conn.add_synonym('foo bar', 'foo baz')
         >>> dict(conn.iter_synonyms())
         {('foo', None): ('bar',), ('foo bar', None): ('baz', 'foo baz')}

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        return SynonymIter(self._index, self._field_mappings, prefix)

    def iter_subfacets(self):
        """Get an iterator over the facet hierarchy.

        The iterator returns 2-tuples, in which the first item is the
        subfacet and the second item is its parent facet.

        The return values are suitable for the dict() builtin, for example:

         >>> conn = IndexerConnection('db')
         >>> conn.add_field_action('foo', FieldActions.FACET)
         >>> conn.add_field_action('bar', FieldActions.FACET)
         >>> conn.add_field_action('baz', FieldActions.FACET)
         >>> conn.add_subfacet('foo', 'bar')
         >>> conn.add_subfacet('baz', 'bar')
         >>> dict(conn.iter_subfacets())
         {'foo': 'bar', 'baz': 'bar'}

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if 'facets' in _checkxapian.missing_features:
            raise errors.IndexerError("Facets unsupported with this release of xapian")
        return self._facet_hierarchy.iteritems()

    def iter_facet_query_types(self, association):
        """Get an iterator over query types and their associated facets.

        Only facets associated with the query types in the specified manner
        are returned; `association` must be one of IndexerConnection.FacetQueryType_Preferred
        or IndexerConnection.FacetQueryType_Never.

        The iterator returns 2-tuples, in which the first item is the query
        type and the second item is the associated set of facets.

        The return values are suitable for the dict() builtin, for example:

         >>> conn = IndexerConnection('db')
         >>> conn.add_field_action('foo', FieldActions.FACET)
         >>> conn.add_field_action('bar', FieldActions.FACET)
         >>> conn.add_field_action('baz', FieldActions.FACET)
         >>> conn.set_facet_for_query_type('type1', 'foo', conn.FacetQueryType_Preferred)
         >>> conn.set_facet_for_query_type('type1', 'bar', conn.FacetQueryType_Never)
         >>> conn.set_facet_for_query_type('type1', 'baz', conn.FacetQueryType_Never)
         >>> conn.set_facet_for_query_type('type2', 'bar', conn.FacetQueryType_Preferred)
         >>> dict(conn.iter_facet_query_types(conn.FacetQueryType_Preferred))
         {'type1': set(['foo']), 'type2': set(['bar'])}
         >>> dict(conn.iter_facet_query_types(conn.FacetQueryType_Never))
         {'type1': set(['bar', 'baz'])}

        """
        if self._index is None:
            raise errors.IndexerError("IndexerConnection has been closed")
        if 'facets' in _checkxapian.missing_features:
            raise errors.IndexerError("Facets unsupported with this release of xapian")
        return FacetQueryTypeIter(self._facet_query_table, association)

class PrefixedTermIter(object):
    """Iterate through all the terms with a given prefix.

    """
    def __init__(self, prefix, termiter):
        """Initialise the prefixed term iterator.

        - `prefix` is the prefix to return terms for.
        - `termiter` is a xapian TermIterator, which should be at its start.

        """

        # The algorithm used in next() currently only works for single
        # character prefixes, so assert that the prefix is single character.
        # To deal with multicharacter prefixes, we need to check for terms
        # which have a starting prefix equal to that given, but then have a
        # following uppercase alphabetic character, indicating that the actual
        # prefix is longer than the target prefix.  We then need to skip over
        # these.  Not too hard to implement, but we don't need it yet.
        assert(len(prefix) == 1)

        self._started = False
        self._prefix = prefix
        self._prefixlen = len(prefix)
        self._termiter = termiter

    def __iter__(self):
        return self

    def next(self):
        """Get the next term with the specified prefix.

        """
        if not self._started:
            term = self._termiter.skip_to(self._prefix).term
            self._started = True
        else:
            term = self._termiter.next().term
        if len(term) < self._prefixlen or term[:self._prefixlen] != self._prefix:
            raise StopIteration
        return term[self._prefixlen:]


class SynonymIter(object):
    """Iterate through a list of synonyms.

    """
    def __init__(self, index, field_mappings, prefix):
        """Initialise the synonym iterator.

         - `index` is the index to get the synonyms from.
         - `field_mappings` is the FieldMappings object for the iterator.
         - `prefix` is the prefix to restrict the returned synonyms to.

        """
        self._index = index
        self._field_mappings = field_mappings
        self._syniter = self._index.synonym_keys(prefix)

    def __iter__(self):
        return self

    def next(self):
        """Get the next synonym.

        """
        synkey = self._syniter.next()
        pos = 0
        for char in synkey:
            if char.isupper(): pos += 1
            else: break
        if pos == 0:
            fieldname = None
            terms = synkey
        else:
            prefix = synkey[:pos]
            fieldname = self._field_mappings.get_fieldname_from_prefix(prefix)
            terms = ' '.join((term[pos:] for term in synkey.split(' ')))
        synval = tuple(self._index.synonyms(synkey))
        return ((terms, fieldname), synval)

class FacetQueryTypeIter(object):
    """Iterate through all the query types and their associated facets.

    """
    def __init__(self, facet_query_table, association):
        """Initialise the query type facet iterator.

        Only facets associated with each query type in the specified
        manner are returned (`association` must be one of
        IndexerConnection.FacetQueryType_Preferred or
        IndexerConnection.FacetQueryType_Never).

        """
        self._table_iter = facet_query_table.iteritems()
        self._association = association

    def __iter__(self):
        return self

    def next(self):
        """Get the next (query type, facet set) 2-tuple.

        """
        query_type, facet_dict = self._table_iter.next()
        facet_list = [facet for facet, association in facet_dict.iteritems() if association == self._association]
        if len(facet_list) == 0:
            return self.next()
        return (query_type, set(facet_list))

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod (sys.modules[__name__])

########NEW FILE########
__FILENAME__ = marshall
#!/usr/bin/env python
#
# Copyright (C) 2007 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""marshall.py: Marshal values into strings

"""
__docformat__ = "restructuredtext en"

import math
import xapian
from replaylog import log as _log

def float_to_string(value):
    """Marshall a floating point number to a string which sorts in the
    appropriate manner.

    """
    return _log(xapian.sortable_serialise, value)

def date_to_string(date):
    """Marshall a date to a string which sorts in the appropriate manner.

    """
    return '%04d%02d%02d' % (date.year, date.month, date.day)

########NEW FILE########
__FILENAME__ = memutils
#!/usr/bin/env python
#
# Copyright (C) 2007 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""memutils.py: Memory handling utilities.

"""
__docformat__ = "restructuredtext en"

import os

def _get_physical_mem_sysconf():
    """Try getting a value for the physical memory using os.sysconf().

    Returns None if no value can be obtained - otherwise, returns a value in
    bytes.

    """
    if getattr(os, 'sysconf', None) is None:
        return None

    try:
        pagesize = os.sysconf('SC_PAGESIZE')
    except ValueError:
        try:
            pagesize = os.sysconf('SC_PAGE_SIZE')
        except ValueError:
            return None

    try:
        pagecount = os.sysconf('SC_PHYS_PAGES')
    except ValueError:
        return None

    return pagesize * pagecount

def _get_physical_mem_win32():
    """Try getting a value for the physical memory using GlobalMemoryStatus.

    This is a windows specific method.  Returns None if no value can be
    obtained (eg, not running on windows) - otherwise, returns a value in
    bytes.

    """
    try:
        import ctypes
        import ctypes.wintypes as wintypes
    except ValueError:
        return None
    
    class MEMORYSTATUS(wintypes.Structure):
        _fields_ = [
            ('dwLength', wintypes.DWORD),
            ('dwMemoryLoad', wintypes.DWORD),
            ('dwTotalPhys', wintypes.DWORD),
            ('dwAvailPhys', wintypes.DWORD),
            ('dwTotalPageFile', wintypes.DWORD),
            ('dwAvailPageFile', wintypes.DWORD),
            ('dwTotalVirtual', wintypes.DWORD),
            ('dwAvailVirtual', wintypes.DWORD),
        ]

    m = MEMORYSTATUS()
    wintypes.windll.kernel32.GlobalMemoryStatus(wintypes.byref(m))
    return m.dwTotalPhys

def get_physical_memory():
    """Get the amount of physical memory in the system, in bytes.

    If this can't be obtained, returns None.

    """
    result = _get_physical_mem_sysconf()
    if result is not None:
        return result
    return _get_physical_mem_win32()

########NEW FILE########
__FILENAME__ = parsedate
#!/usr/bin/env python
#
# Copyright (C) 2007 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""parsedate.py: Parse date strings.

"""
__docformat__ = "restructuredtext en"

import datetime
import re

yyyymmdd_re = re.compile(r'(?P<year>[0-9]{4})(?P<month>[0-9]{2})(?P<day>[0-9]{2})$')
yyyy_mm_dd_re = re.compile(r'(?P<year>[0-9]{4})([-/.])(?P<month>[0-9]{2})\2(?P<day>[0-9]{2})$')

def date_from_string(value):
    """Parse a string into a date.

    If the value supplied is already a date-like object (ie, has 'year',
    'month' and 'day' attributes), it is returned without processing.

    Supported date formats are:

     - YYYYMMDD
     - YYYY-MM-DD 
     - YYYY/MM/DD 
     - YYYY.MM.DD 

    """
    if (hasattr(value, 'year')
        and hasattr(value, 'month')
        and hasattr(value, 'day')):
        return value

    mg = yyyymmdd_re.match(value)
    if mg is None:
        mg = yyyy_mm_dd_re.match(value)

    if mg is not None:
        year, month, day = (int(i) for i in mg.group('year', 'month', 'day'))
        return datetime.date(year, month, day)

    raise ValueError('Unrecognised date format')

########NEW FILE########
__FILENAME__ = replaylog
#!/usr/bin/env python
#
# Copyright (C) 2007 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""replaylog.py: Log all xapian calls to a file, so that they can be replayed.

"""
__docformat__ = "restructuredtext en"

import datetime
import sys
import thread
import threading
import time
import traceback
import types
import weakref
import xapian

from pprint import pprint

# The logger in use.
_replay_log = None

# True if a replay log has ever been in use since import time.
_had_replay_log = False

class NotifyingDeleteObject(object):
    """An wrapping for an object which calls a callback when its deleted.

    Note that the callback will be called from a __del__ method, so shouldn't
    raise any exceptions, and probably shouldn't make new references to the
    object supplied to it.

    """
    def __init__(self, obj, callback):
        self.obj = obj
        self.callback = callback

    def __del__(self):
        self.callback(self.obj)

class ReplayLog(object):
    """Log of xapian calls, to be replayed.

    """

    def __init__(self, logpath):
        """Create a new replay log.

        """
        # Mutex used to protect all access to _fd
        self._fd_mutex = threading.Lock()
        self._fd = file(logpath, 'wb')

        # Mutex used to protect all access to members other than _fd
        self._mutex = threading.Lock()
        self._next_call = 1

        self._next_thread = 0
        self._thread_ids = {}

        self._objs = weakref.WeakKeyDictionary()
        self._next_num = 1

        self._xapian_classes = {}
        self._xapian_functions = {}
        self._xapian_methods = {}
        for name in dir(xapian):
            item = getattr(xapian, name)
            has_members = False
            for membername in dir(item):
                member = getattr(item, membername)
                if isinstance(member, types.MethodType):
                    self._xapian_methods[member.im_func] = (name, membername)
                    has_members = True
            if has_members:
                self._xapian_classes[item] = name
            if isinstance(item, types.BuiltinFunctionType):
                self._xapian_functions[item] = name

    def _get_obj_num(self, obj, maybe_new):
        """Get the number associated with an object.

        If maybe_new is False, a value of 0 will be supplied if the object
        hasn't already been seen.  Otherwise, a new (and previously unused)
        value will be allocated to the object.

        The mutex should be held when this is called.

        """
        try:
            num = self._objs[obj]
            return num.obj
        except KeyError:
            pass

        if not maybe_new:
            return 0

        self._objs[obj] = NotifyingDeleteObject(self._next_num, self._obj_gone)
        self._next_num += 1
        return self._next_num - 1

    def _is_xap_obj(self, obj):
        """Return True iff an object is an instance of a xapian object.

        (Also returns true if the object is an instance of a subclass of a
        xapian object.)

        The mutex should be held when this is called.

        """
        # Check for xapian classes.
        classname = self._xapian_classes.get(type(obj), None)
        if classname is not None:
            return True
        # Check for subclasses of xapian classes.
        for classobj, classname in self._xapian_classes.iteritems():
            if isinstance(obj, classobj):
                return True
        # Not a xapian class or subclass.
        return False

    def _get_xap_name(self, obj, maybe_new=False):
        """Get the name of a xapian class or method.

        The mutex should be held when this is called.

        """
        # Check if it's a xapian class, or subclass.
        if isinstance(obj, types.TypeType):
            classname = self._xapian_classes.get(obj, None)
            if classname is not None:
                return classname

            for classobj, classname in self._xapian_classes.iteritems():
                if issubclass(obj, classobj):
                    return "subclassof_%s" % (classname, )

            return None

        # Check if it's a xapian function.
        if isinstance(obj, types.BuiltinFunctionType):
            funcname = self._xapian_functions.get(obj, None)
            if funcname is not None:
                return funcname

        # Check if it's a proxied object.
        if isinstance(obj, LoggedProxy):
            classname = self._xapian_classes.get(obj.__class__, None)
            if classname is not None:
                objnum = self._get_obj_num(obj, maybe_new=maybe_new)
                return "%s#%d" % (classname, objnum)

        # Check if it's a proxied method.
        if isinstance(obj, LoggedProxyMethod):
            classname, methodname = self._xapian_methods[obj.real.im_func]
            objnum = self._get_obj_num(obj.proxyobj, maybe_new=maybe_new)
            return "%s#%d.%s" % (classname, objnum, methodname)

        # Check if it's a subclass of a xapian class.  Note: this will only
        # pick up subclasses, because the original classes are filtered out
        # higher up.
        for classobj, classname in self._xapian_classes.iteritems():
            if isinstance(obj, classobj):
                objnum = self._get_obj_num(obj, maybe_new=maybe_new)
                return "subclassof_%s#%d" % (classname, objnum)

        return None

    def _log(self, msg):
        self._fd_mutex.acquire()
        try:
#            msg = '%s,%s' % (
#                datetime.datetime.fromtimestamp(time.time()).isoformat(),
#                msg,
#            )
            self._fd.write(msg)
            self._fd.flush()
        finally:
            self._fd_mutex.release()

    def _repr_arg(self, arg):
        """Return a representation of an argument.

        The mutex should be held when this is called.

        """

        xapargname = self._get_xap_name(arg)
        if xapargname is not None:
            return xapargname

        if isinstance(arg, basestring):
            if isinstance(arg, unicode):
                arg = arg.encode('utf-8')
            return 'str(%d,%s)' % (len(arg), arg)

        if isinstance(arg, long):
            try:
                arg = int(arg)
            except OverFlowError:
                pass

        if isinstance(arg, long):
            return 'long(%d)' % arg

        if isinstance(arg, int):
            return 'int(%d)' % arg

        if isinstance(arg, float):
            return 'float(%f)' % arg

        if arg is None:
            return 'None'

        if hasattr(arg, '__iter__'):
            seq = []
            for item in arg:
                seq.append(self._repr_arg(item))
            return 'list(%s)' % ','.join(seq)

        return 'UNKNOWN:' + str(arg)

    def _repr_args(self, args):
        """Return a representation of a list of arguments.

        The mutex should be held when this is called.

        """
        logargs = []
        for arg in args:
            logargs.append(self._repr_arg(arg))
        return ','.join(logargs)

    def _get_call_id(self):
        """Get an ID string for a call.

        The mutex should be held when this is called.

        """
        call_num = self._next_call
        self._next_call += 1

        thread_id = thread.get_ident()
        try:
            thread_num = self._thread_ids[thread_id]
        except KeyError:
            thread_num = self._next_thread
            self._thread_ids[thread_id] = thread_num
            self._next_thread += 1

        if thread_num is 0:
            return "%s" % call_num
        return "%dT%d" % (call_num, thread_num)

    def log_call(self, call, *args):
        """Add a log message about a call.

        Returns a number for the call, so it can be tied to a particular
        result.

        """
        self._mutex.acquire()
        try:
            logargs = self._repr_args(args)
            xapobjname = self._get_xap_name(call)
            call_id = self._get_call_id()
        finally:
            self._mutex.release()

        if xapobjname is not None:
            self._log("CALL%s:%s(%s)\n" % (call_id, xapobjname, logargs))
        else:
            self._log("CALL%s:UNKNOWN:%r(%s)\n" % (call_id, call, logargs))
        return call_id

    def log_except(self, (etype, value, tb), call_id):
        """Log an exception which has occurred.

        """
        # No access to an members, so no need to acquire mutex.
        exc = traceback.format_exception_only(etype, value)
        self._log("EXCEPT%s:%s\n" % (call_id, ''.join(exc).strip()))

    def log_retval(self, ret, call_id):
        """Log a return value.

        """
        if ret is None:
            self._log("RET%s:None\n" % call_id)
            return

        self._mutex.acquire()
        try:
            # If it's a xapian object, return a proxy for it.
            if self._is_xap_obj(ret):
                ret = LoggedProxy(ret)
                xapobjname = self._get_xap_name(ret, maybe_new=True)
            msg = "RET%s:%s\n" % (call_id, self._repr_arg(ret))
        finally:
            self._mutex.release()

        # Not a xapian object - just return it.
        self._log(msg)
        return ret

    def _obj_gone(self, num):
        """Log that an object has been deleted.

        """
        self._log('DEL:#%d\n' % num)

class LoggedProxy(object):
    """A proxy for a xapian object, which logs all calls made on the object.

    """
    def __init__(self, obj):
        self.__obj = obj

    def __getattribute__(self, name):
        obj = object.__getattribute__(self, '_LoggedProxy__obj')
        if name == '__obj':
            return obj
        real = getattr(obj, name)
        if not isinstance(real, types.MethodType):
            return real
        return LoggedProxyMethod(real, self)

    def __iter__(self):
        obj = object.__getattribute__(self, '_LoggedProxy__obj')
        return obj.__iter__()

    def __len__(self):
        obj = object.__getattribute__(self, '_LoggedProxy__obj')
        return obj.__len__()

    def __repr__(self):
        obj = object.__getattribute__(self, '_LoggedProxy__obj')
        return '<LoggedProxy of %s >' % obj.__repr__()

    def __str__(self):
        obj = object.__getattribute__(self, '_LoggedProxy__obj')
        return obj.__str__()

class LoggedProxyMethod(object):
    """A proxy for a xapian method, which logs all calls made on the method.

    """
    def __init__(self, real, proxyobj):
        """Make a proxy for the method.

        """
        self.real = real
        self.proxyobj = proxyobj

    def __call__(self, *args):
        """Call the proxied method, logging the call.

        """
        return log(self, *args)

def set_replay_path(logpath):
    """Set the path for the replay log.

    """
    global _replay_log
    global _had_replay_log
    if logpath is None:
        _replay_log = None
    else:
        _had_replay_log = True
        _replay_log = ReplayLog(logpath)

def _unproxy_call_and_args(call, args):
    """Convert a call and list of arguments to unproxied form.

    """
    if isinstance(call, LoggedProxyMethod):
        realcall = call.real
    else:
        realcall = call

    realargs = []
    for arg in args:
        if isinstance(arg, LoggedProxy):
            arg = arg.__obj
        realargs.append(arg)

    return realcall, realargs

def log(call, *args):
    """Make a call to xapian, and log it.

    """
    # If we've never had a replay log in force, no need to unproxy objects.
    global _had_replay_log
    if not _had_replay_log:
        return call(*args)

    # Get unproxied versions of the call and arguments.
    realcall, realargs = _unproxy_call_and_args(call, args)

    # If we have no replay log currently, just do the call.
    global _replay_log
    replay_log = _replay_log
    if replay_log is None:
        return realcall(*realargs)

    # We have a replay log: do a logged version of the call.
    call_id = replay_log.log_call(call, *args)
    try:
        ret = realcall(*realargs)
    except:
        replay_log.log_except(sys.exc_info(), call_id)
        raise
    return replay_log.log_retval(ret, call_id)

#set_replay_path('replay.log')

########NEW FILE########
__FILENAME__ = schema
#!/usr/bin/env python
#
# Copyright (C) 2008 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""schema.py: xdefinitions and implementations of field actions.

"""
__docformat__ = "restructuredtext en"

import errors as _errors
from replaylog import log as _log
import parsedate as _parsedate

class Schema(object):
    def __init__(self):
        pass

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod (sys.modules[__name__])

########NEW FILE########
__FILENAME__ = searchconnection
#!/usr/bin/env python
#
# Copyright (C) 2007 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""searchconnection.py: A connection to the search engine for searching.

"""
__docformat__ = "restructuredtext en"

import _checkxapian
import os as _os
import cPickle as _cPickle
import math

import xapian as _xapian
from datastructures import *
from fieldactions import *
import fieldmappings as _fieldmappings
import highlight as _highlight 
import errors as _errors
import indexerconnection as _indexerconnection
import re as _re
from replaylog import log as _log

class SearchResult(ProcessedDocument):
    """A result from a search.

    As well as being a ProcessedDocument representing the document in the
    database, the result has several members which may be used to get
    information about how well the document matches the search:

     - `rank`: The rank of the document in the search results, starting at 0
       (ie, 0 is the "top" result, 1 is the second result, etc).

     - `weight`: A floating point number indicating the weight of the result
       document.  The value is only meaningful relative to other results for a
       given search - a different search, or the same search with a different
       database, may give an entirely different scale to the weights.  This
       should not usually be displayed to users, but may be useful if trying to
       perform advanced reweighting operations on search results.

     - `percent`: A percentage value for the weight of a document.  This is
       just a rescaled form of the `weight` member.  It doesn't represent any
       kind of probability value; the only real meaning of the numbers is that,
       within a single set of results, a document with a higher percentage
       corresponds to a better match.  Because the percentage doesn't really
       represent a probability, or a confidence value, it is probably unhelpful
       to display it to most users, since they tend to place an over emphasis
       on its meaning.  However, it is included because it may be useful
       occasionally.

    """
    def __init__(self, msetitem, results):
        ProcessedDocument.__init__(self, results._fieldmappings, msetitem.document)
        self.rank = msetitem.rank
        self.weight = msetitem.weight
        self.percent = msetitem.percent
        self._results = results

    def _get_language(self, field):
        """Get the language that should be used for a given field.

        Raises a KeyError if the field is not known.

        """
        actions = self._results._conn._field_actions[field]._actions
        for action, kwargslist in actions.iteritems():
            if action == FieldActions.INDEX_FREETEXT:
                for kwargs in kwargslist:
                    try:
                        return kwargs['language']
                    except KeyError:
                        pass
        return 'none'

    def summarise(self, field, maxlen=600, hl=('<b>', '</b>'), ellipsis=None, strict_length=None, query=None):
        """Return a summarised version of the field specified.

        This will return a summary of the contents of the field stored in the
        search result, with words which match the query highlighted.

        The maximum length of the summary (in characters) may be set using the
        maxlen parameter.

        The return value will be a string holding the summary, with
        highlighting applied.  If there are multiple instances of the field in
        the document, the instances will be joined with a newline character.
        
        To turn off highlighting, set hl to None.  Each highlight will consist
        of the first entry in the `hl` list being placed before the word, and
        the second entry in the `hl` list being placed after the word.

        Any XML or HTML style markup tags in the field will be stripped before
        the summarisation algorithm is applied.

        If `query` is supplied, it should contain a Query object, as returned
        from SearchConnection.query_parse() or related methods, which will be
        used as the basis of the summarisation and highlighting rather than the
        query which was used for the search.
        
        `ellipsis` and `strict_length` are passed through to `Highlighter.makeSample`
        if given

        Raises KeyError if the field is not known.

        """
        highlighter = _highlight.Highlighter(language_code=self._get_language(field))
        field = self.data[field]
        results = []
        text = '\n'.join(field)
        if query is None:
            query = self._results._query
        kwargs = {}
        if ellipsis is not None:
            kwargs['ellipsis'] = ellipsis
        if strict_length is not None:
            kwargs['strict_length'] = strict_length
        return highlighter.makeSample(text, query, maxlen, hl, **kwargs)

    def highlight(self, field, hl=('<b>', '</b>'), strip_tags=False, query=None):
        """Return a highlighted version of the field specified.

        This will return all the contents of the field stored in the search
        result, with words which match the query highlighted.

        The return value will be a list of strings (corresponding to the list
        of strings which is the raw field data).

        Each highlight will consist of the first entry in the `hl` list being
        placed before the word, and the second entry in the `hl` list being
        placed after the word.

        If `strip_tags` is True, any XML or HTML style markup tags in the field
        will be stripped before highlighting is applied.

        If `query` is supplied, it should contain a Query object, as returned
        from SearchConnection.query_parse() or related methods, which will be
        used as the basis of the summarisation and highlighting rather than the
        query which was used for the search.

        Raises KeyError if the field is not known.

        """
        highlighter = _highlight.Highlighter(language_code=self._get_language(field))
        field = self.data[field]
        results = []
        if query is None:
            query = self._results._query
        for text in field:
            results.append(highlighter.highlight(text, query, hl, strip_tags))
        return results

    def __repr__(self):
        return ('<SearchResult(rank=%d, id=%r, data=%r)>' %
                (self.rank, self.id, self.data))


class SearchResultIter(object):
    """An iterator over a set of results from a search.

    """
    def __init__(self, results, order):
        self._results = results
        self._order = order
        if self._order is None:
            self._iter = iter(results._mset)
        else:
            self._iter = iter(self._order)

    def next(self):
        if self._order is None:
            msetitem = self._iter.next()
        else:
            index = self._iter.next()
            msetitem = self._results._mset.get_hit(index)
        return SearchResult(msetitem, self._results)


def _get_significant_digits(value, lower, upper):
    """Get the significant digits of value which are constrained by the
    (inclusive) lower and upper bounds.

    If there are no significant digits which are definitely within the
    bounds, exactly one significant digit will be returned in the result.

    >>> _get_significant_digits(15,15,15)
    15
    >>> _get_significant_digits(15,15,17)
    20
    >>> _get_significant_digits(4777,208,6000)
    5000
    >>> _get_significant_digits(4777,4755,4790)
    4800
    >>> _get_significant_digits(4707,4695,4710)
    4700
    >>> _get_significant_digits(4719,4717,4727)
    4720
    >>> _get_significant_digits(0,0,0)
    0
    >>> _get_significant_digits(9,9,10)
    9
    >>> _get_significant_digits(9,9,100)
    9

    """
    assert(lower <= value)
    assert(value <= upper)
    diff = upper - lower

    # Get the first power of 10 greater than the difference.
    # This corresponds to the magnitude of the smallest significant digit.
    if diff == 0:
        pos_pow_10 = 1
    else:
        pos_pow_10 = int(10 ** math.ceil(math.log10(diff)))

    # Special case for situation where we don't have any significant digits:
    # get the magnitude of the most significant digit in value.
    if pos_pow_10 > value:
        if value == 0:
            pos_pow_10 = 1
        else:
            pos_pow_10 = int(10 ** math.floor(math.log10(value)))

    # Return the value, rounded to the nearest multiple of pos_pow_10
    return ((value + pos_pow_10 // 2) // pos_pow_10) * pos_pow_10

class SearchResults(object):
    """A set of results of a search.

    """
    def __init__(self, conn, enq, query, mset, fieldmappings, tagspy,
                 tagfields, facetspy, facetfields, facethierarchy,
                 facetassocs):
        self._conn = conn
        self._enq = enq
        self._query = query
        self._mset = mset
        self._mset_order = None
        self._fieldmappings = fieldmappings
        self._tagspy = tagspy
        if tagfields is None:
            self._tagfields = None
        else:
            self._tagfields = set(tagfields)
        self._facetspy = facetspy
        self._facetfields = facetfields
        self._facethierarchy = facethierarchy
        self._facetassocs = facetassocs
        self._numeric_ranges_built = {}

    def _cluster(self, num_clusters, maxdocs, fields=None):
        """Cluster results based on similarity.

        Note: this method is experimental, and will probably disappear or
        change in the future.

        The number of clusters is specified by num_clusters: unless there are
        too few results, there will be exaclty this number of clusters in the
        result.

        """
        clusterer = _xapian.ClusterSingleLink()
        xapclusters = _xapian.ClusterAssignments()
        docsim = _xapian.DocSimCosine()
        source = _xapian.MSetDocumentSource(self._mset, maxdocs)

        if fields is None:
            clusterer.cluster(self._conn._index, xapclusters, docsim, source, num_clusters)
        else:
            decider = self._make_expand_decider(fields)
            clusterer.cluster(self._conn._index, xapclusters, docsim, source, decider, num_clusters)

        newid = 0
        idmap = {}
        clusters = {}
        for item in self._mset:
            docid = item.docid
            clusterid = xapclusters.cluster(docid)
            if clusterid not in idmap:
                idmap[clusterid] = newid
                newid += 1
            clusterid = idmap[clusterid]
            if clusterid not in clusters:
                clusters[clusterid] = []
            clusters[clusterid].append(item.rank)
        return clusters

    def _reorder_by_clusters(self, clusters):
        """Reorder the mset based on some clusters.

        """
        if self.startrank != 0:
            raise _errors.SearchError("startrank must be zero to reorder by clusters")
        reordered = False
        tophits = []
        nottophits = []

        clusterstarts = dict(((c[0], None) for c in clusters.itervalues()))
        for i in xrange(self.endrank):
            if i in clusterstarts:
                tophits.append(i)
            else:
                nottophits.append(i)
        self._mset_order = tophits
        self._mset_order.extend(nottophits)

    def _make_expand_decider(self, fields):
        """Make an expand decider which accepts only terms in the specified
        field.

        """
        prefixes = {}
        if isinstance(fields, basestring):
            fields = [fields]
        for field in fields:
            try:
                actions = self._conn._field_actions[field]._actions
            except KeyError:
                continue
            for action, kwargslist in actions.iteritems():
                if action == FieldActions.INDEX_FREETEXT:
                    prefix = self._conn._field_mappings.get_prefix(field)
                    prefixes[prefix] = None
                    prefixes['Z' + prefix] = None
                if action in (FieldActions.INDEX_EXACT,
                              FieldActions.TAG,
                              FieldActions.FACET,):
                    prefix = self._conn._field_mappings.get_prefix(field)
                    prefixes[prefix] = None
        prefix_re = _re.compile('|'.join([_re.escape(x) + '[^A-Z]' for x in prefixes.keys()]))
        class decider(_xapian.ExpandDecider):
            def __call__(self, term):
                return prefix_re.match(term) is not None
        return decider()

    def _reorder_by_similarity(self, count, maxcount, max_similarity,
                               fields=None):
        """Reorder results based on similarity.

        The top `count` documents will be chosen such that they are relatively
        dissimilar.  `maxcount` documents will be considered for moving around,
        and `max_similarity` is a value between 0 and 1 indicating the maximum
        similarity to the previous document before a document is moved down the
        result set.

        Note: this method is experimental, and will probably disappear or
        change in the future.

        """
        if self.startrank != 0:
            raise _errors.SearchError("startrank must be zero to reorder by similiarity")
        ds = _xapian.DocSimCosine()
        ds.set_termfreqsource(_xapian.DatabaseTermFreqSource(self._conn._index))

        if fields is not None:
            ds.set_expand_decider(self._make_expand_decider(fields))

        tophits = []
        nottophits = []
        full = False
        reordered = False

        sim_count = 0
        new_order = []
        end = min(self.endrank, maxcount)
        for i in xrange(end):
            if full:
                new_order.append(i)
                continue
            hit = self._mset.get_hit(i)
            if len(tophits) == 0:
                tophits.append(hit)
                continue

            # Compare each incoming hit to tophits
            maxsim = 0.0
            for tophit in tophits[-1:]:
                sim_count += 1
                sim = ds.similarity(hit.document, tophit.document)
                if sim > maxsim:
                    maxsim = sim

            # If it's not similar to an existing hit, add to tophits.
            if maxsim < max_similarity:
                tophits.append(hit)
            else:
                nottophits.append(hit)
                reordered = True

            # If we're full of hits, append to the end.
            if len(tophits) >= count:
                for hit in tophits:
                    new_order.append(hit.rank)
                for hit in nottophits:
                    new_order.append(hit.rank)
                full = True
        if not full:
            for hit in tophits:
                new_order.append(hit.rank)
            for hit in nottophits:
                new_order.append(hit.rank)
        if end != self.endrank:
            new_order.extend(range(end, self.endrank))
        assert len(new_order) == self.endrank
        if reordered:
            self._mset_order = new_order
        else:
            assert new_order == range(self.endrank)

    def __repr__(self):
        return ("<SearchResults(startrank=%d, "
                "endrank=%d, "
                "more_matches=%s, "
                "matches_lower_bound=%d, "
                "matches_upper_bound=%d, "
                "matches_estimated=%d, "
                "estimate_is_exact=%s)>" %
                (
                 self.startrank,
                 self.endrank,
                 self.more_matches,
                 self.matches_lower_bound,
                 self.matches_upper_bound,
                 self.matches_estimated,
                 self.estimate_is_exact,
                ))

    def _get_more_matches(self):
        # This check relies on us having asked for at least one more result
        # than retrieved to be checked.
        return (self.matches_lower_bound > self.endrank)
    more_matches = property(_get_more_matches, doc=
    """Check whether there are further matches after those in this result set.

    """)

    def _get_startrank(self):
        return self._mset.get_firstitem()
    startrank = property(_get_startrank, doc=
    """Get the rank of the first item in the search results.

    This corresponds to the "startrank" parameter passed to the search() method.

    """)

    def _get_endrank(self):
        return self._mset.get_firstitem() + len(self._mset)
    endrank = property(_get_endrank, doc=
    """Get the rank of the item after the end of the search results.

    If there are sufficient results in the index, this corresponds to the
    "endrank" parameter passed to the search() method.

    """)

    def _get_lower_bound(self):
        return self._mset.get_matches_lower_bound()
    matches_lower_bound = property(_get_lower_bound, doc=
    """Get a lower bound on the total number of matching documents.

    """)

    def _get_upper_bound(self):
        return self._mset.get_matches_upper_bound()
    matches_upper_bound = property(_get_upper_bound, doc=
    """Get an upper bound on the total number of matching documents.

    """)

    def _get_human_readable_estimate(self):
        lower = self._mset.get_matches_lower_bound()
        upper = self._mset.get_matches_upper_bound()
        est = self._mset.get_matches_estimated()
        return _get_significant_digits(est, lower, upper)
    matches_human_readable_estimate = property(_get_human_readable_estimate,
                                               doc=
    """Get a human readable estimate of the number of matching documents.

    This consists of the value returned by the "matches_estimated" property,
    rounded to an appropriate number of significant digits (as determined by
    the values of the "matches_lower_bound" and "matches_upper_bound"
    properties).

    """)

    def _get_estimated(self):
        return self._mset.get_matches_estimated()
    matches_estimated = property(_get_estimated, doc=
    """Get an estimate for the total number of matching documents.

    """)

    def _estimate_is_exact(self):
        return self._mset.get_matches_lower_bound() == \
               self._mset.get_matches_upper_bound()
    estimate_is_exact = property(_estimate_is_exact, doc=
    """Check whether the estimated number of matching documents is exact.

    If this returns true, the estimate given by the `matches_estimated`
    property is guaranteed to be correct.

    If this returns false, it is possible that the actual number of matching
    documents is different from the number given by the `matches_estimated`
    property.

    """)

    def get_hit(self, index):
        """Get the hit with a given index.

        """
        if self._mset_order is None:
            msetitem = self._mset.get_hit(index)
        else:
            msetitem = self._mset.get_hit(self._mset_order[index])
        return SearchResult(msetitem, self)
    __getitem__ = get_hit

    def __iter__(self):
        """Get an iterator over the hits in the search result.

        The iterator returns the results in increasing order of rank.

        """
        return SearchResultIter(self, self._mset_order)

    def __len__(self):
        """Get the number of hits in the search result.

        Note that this is not (usually) the number of matching documents for
        the search.  If startrank is non-zero, it's not even the rank of the
        last document in the search result.  It's simply the number of hits
        stored in the search result.

        It is, however, the number of items returned by the iterator produced
        by calling iter() on this SearchResults object.

        """
        return len(self._mset)

    def get_top_tags(self, field, maxtags):
        """Get the most frequent tags in a given field.

         - `field` - the field to get tags for.  This must have been specified
           in the "gettags" argument of the search() call.
         - `maxtags` - the maximum number of tags to return.

        Returns a sequence of 2-item tuples, in which the first item in the
        tuple is the tag, and the second is the frequency of the tag in the
        matches seen (as an integer).

        """
        if 'tags' in _checkxapian.missing_features:
            raise errors.SearchError("Tags unsupported with this release of xapian")
        if self._tagspy is None or field not in self._tagfields:
            raise _errors.SearchError("Field %r was not specified for getting tags" % field)
        prefix = self._conn._field_mappings.get_prefix(field)
        return self._tagspy.get_top_terms(prefix, maxtags)

    def get_suggested_facets(self, maxfacets=5, desired_num_of_categories=7,
                             required_facets=None):
        """Get a suggested set of facets, to present to the user.

        This returns a list, in descending order of the usefulness of the
        facet, in which each item is a tuple holding:

         - fieldname of facet.
         - sequence of 2-tuples holding the suggested values or ranges for that
           field:

           For facets of type 'string', the first item in the 2-tuple will
           simply be the string supplied when the facet value was added to its
           document.  For facets of type 'float', it will be a 2-tuple, holding
           floats giving the start and end of the suggested value range.

           The second item in the 2-tuple will be the frequency of the facet
           value or range in the result set.

        If required_facets is not None, it must be a field name, or a sequence
        of field names.  Any field names mentioned in required_facets will be
        returned if there are any facet values at all in the search results for
        that field.  The facet will only be omitted if there are no facet
        values at all for the field.

        The value of maxfacets will be respected as far as possible; the
        exception is that if there are too many fields listed in
        required_facets with at least one value in the search results, extra
        facets will be returned (ie, obeying the required_facets parameter is
        considered more important than the maxfacets parameter).

        If facet_hierarchy was indicated when search() was called, and the
        query included facets, then only subfacets of those query facets and
        top-level facets will be included in the returned list. Furthermore
        top-level facets will only be returned if there are remaining places
        in the list after it has been filled with subfacets. Note that
        required_facets is still respected regardless of the facet hierarchy.

        If a query type was specified when search() was called, and the query
        included facets, then facets with an association of Never to the
        query type are never returned, even if mentioned in required_facets.
        Facets with an association of Preferred are listed before others in
        the returned list.

        """
        if 'facets' in _checkxapian.missing_features:
            raise errors.SearchError("Facets unsupported with this release of xapian")
        if self._facetspy is None:
            raise _errors.SearchError("Facet selection wasn't enabled when the search was run")
        if isinstance(required_facets, basestring):
            required_facets = [required_facets]
        scores = []
        facettypes = {}
        for field, slot, kwargslist in self._facetfields:
            type = None
            for kwargs in kwargslist:
                type = kwargs.get('type', None)
                if type is not None: break
            if type is None: type = 'string'

            if type == 'float':
                if field not in self._numeric_ranges_built:
                    self._facetspy.build_numeric_ranges(slot, desired_num_of_categories)
                    self._numeric_ranges_built[field] = None
            facettypes[field] = type
            score = self._facetspy.score_categorisation(slot, desired_num_of_categories)
            scores.append((score, field, slot))

        # Sort on whether facet is top-level ahead of score (use subfacets first),
        # and on whether facet is preferred for the query type ahead of anything else
        if self._facethierarchy:
            # Note, tuple[-2] is the value of 'field' in a scores tuple
            scores = [(tuple[-2] not in self._facethierarchy,) + tuple for tuple in scores]
        if self._facetassocs:
            preferred = _indexerconnection.IndexerConnection.FacetQueryType_Preferred
            scores = [(self._facetassocs.get(tuple[-2]) != preferred,) + tuple for tuple in scores]
        scores.sort()
        if self._facethierarchy:
            index = 1
        else:
            index = 0
        if self._facetassocs:
            index += 1
        if index > 0:
            scores = [tuple[index:] for tuple in scores]

        results = []
        required_results = []
        for score, field, slot in scores:
            # Check if the facet is required
            required = False
            if required_facets is not None:
                required = field in required_facets

            # If we've got enough facets, and the field isn't required, skip it
            if not required and len(results) + len(required_results) >= maxfacets:
                continue

            # Get the values
            values = self._facetspy.get_values_as_dict(slot)
            if field in self._numeric_ranges_built:
                if '' in values:
                    del values['']

            # Required facets must occur at least once, other facets must occur
            # at least twice.
            if required:
                if len(values) < 1:
                    continue
            else:
                if len(values) <= 1:
                    continue

            newvalues = []
            if facettypes[field] == 'float':
                # Convert numbers to python numbers, and number ranges to a
                # python tuple of two numbers.
                for value, frequency in values.iteritems():
                    if len(value) <= 9:
                        value1 = _log(_xapian.sortable_unserialise, value)
                        value2 = value1
                    else:
                        value1 = _log(_xapian.sortable_unserialise, value[:9])
                        value2 = _log(_xapian.sortable_unserialise, value[9:])
                    newvalues.append(((value1, value2), frequency))
            else:
                for value, frequency in values.iteritems():
                    newvalues.append((value, frequency))

            newvalues.sort()
            if required:
                required_results.append((score, field, newvalues))
            else:
                results.append((score, field, newvalues))

        # Throw away any excess results if we have more required_results to
        # insert.
        maxfacets = maxfacets - len(required_results)
        if maxfacets <= 0:
            results = required_results
        else:
            results = results[:maxfacets]
            results.extend(required_results)
            results.sort()

        # Throw away the scores because they're not meaningful outside this
        # algorithm.
        results = [(field, newvalues) for (score, field, newvalues) in results]
        return results


class SearchConnection(object):
    """A connection to the search engine for searching.

    The connection will access a view of the database.

    """
    _qp_flags_base = _xapian.QueryParser.FLAG_LOVEHATE
    _qp_flags_phrase = _xapian.QueryParser.FLAG_PHRASE
    _qp_flags_synonym = (_xapian.QueryParser.FLAG_AUTO_SYNONYMS |
                         _xapian.QueryParser.FLAG_AUTO_MULTIWORD_SYNONYMS)
    _qp_flags_bool = _xapian.QueryParser.FLAG_BOOLEAN

    _index = None

    def __init__(self, indexpath):
        """Create a new connection to the index for searching.

        There may only an arbitrary number of search connections for a
        particular database open at a given time (regardless of whether there
        is a connection for indexing open as well).

        If the database doesn't exist, an exception will be raised.

        """
        self._index = _log(_xapian.Database, indexpath)
        self._indexpath = indexpath
        self._weight = _xapian.BM25Weight()

        # Read the actions.
        self._load_config()

        self._close_handlers = []

    def __del__(self):
        self.close()

    def set_weighting_scheme(self, weight):
        """
        Set the connection's default weighting scheme, which is used on
        every search.

        Should be a subclass of xapian.Weight.
        """
        self._weight = weight

    def append_close_handler(self, handler, userdata=None):
        """Append a callback to the list of close handlers.

        These will be called when the SearchConnection is closed.  This happens
        when the close() method is called, or when the SearchConnection object
        is deleted.  The callback will be passed two arguments: the path to the
        SearchConnection object, and the userdata supplied to this method.

        The handlers will be called in the order in which they were added.

        The handlers will be called after the connection has been closed, so
        cannot prevent it closing: their return value will be ignored.  In
        addition, they should not raise any exceptions.

        """
        self._close_handlers.append((handler, userdata))

    def _get_sort_type(self, field):
        """Get the sort type that should be used for a given field.

        """
        try:
            actions = self._field_actions[field]._actions
        except KeyError:
            actions = {}
        for action, kwargslist in actions.iteritems():
            if action == FieldActions.SORT_AND_COLLAPSE:
                for kwargs in kwargslist:
                    return kwargs['type']

    def _load_config(self):
        """Load the configuration for the database.

        """
        # Note: this code is basically duplicated in the IndexerConnection
        # class.  Move it to a shared location.
        assert self._index is not None

        config_str = _log(self._index.get_metadata, '_xappy_config')
        if len(config_str) == 0:
            self._field_actions = {}
            self._field_mappings = _fieldmappings.FieldMappings()
            self._facet_hierarchy = {}
            self._facet_query_table = {}
            return

        try:
            (self._field_actions, mappings, self._facet_hierarchy, self._facet_query_table, self._next_docid) = _cPickle.loads(config_str)
        except ValueError:
            # Backwards compatibility - configuration used to lack _facet_hierarchy and _facet_query_table
            (self._field_actions, mappings, self._next_docid) = _cPickle.loads(config_str)
            self._facet_hierarchy = {}
            self._facet_query_table = {}
        self._field_mappings = _fieldmappings.FieldMappings(mappings)

    def reopen(self):
        """Reopen the connection.

        This updates the revision of the index which the connection references
        to the latest flushed revision.

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        self._index.reopen()
        # Re-read the actions.
        self._load_config()
        
    def close(self):
        """Close the connection to the database.

        It is important to call this method before allowing the class to be
        garbage collected to ensure that the connection is cleaned up promptly.

        No other methods may be called on the connection after this has been
        called.  (It is permissible to call close() multiple times, but
        only the first call will have any effect.)

        If an exception occurs, the database will be closed, but changes since
        the last call to flush may be lost.

        """
        if self._index is None:
            return

        # Remember the index path
        indexpath = self._indexpath

        # There is currently no "close()" method for xapian databases, so
        # we have to rely on the garbage collector.  Since we never copy
        # the _index property out of this class, there should be no cycles,
        # so the standard python implementation should garbage collect
        # _index straight away.  A close() method is planned to be added to
        # xapian at some point - when it is, we should call it here to make
        # the code more robust.
        self._index = None
        self._indexpath = None
        self._field_actions = None
        self._field_mappings = None

        # Call the close handlers.
        for handler, userdata in self._close_handlers:
            try:
                handler(indexpath, userdata)
            except Exception, e:
                import sys, traceback
                print >>sys.stderr, "WARNING: unhandled exception in handler called by SearchConnection.close(): %s" % traceback.format_exception_only(type(e), e)

    def get_doccount(self):
        """Count the number of documents in the database.

        This count will include documents which have been added or removed but
        not yet flushed().

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        return self._index.get_doccount()

    OP_AND = _xapian.Query.OP_AND
    OP_OR = _xapian.Query.OP_OR
    def query_composite(self, operator, queries):
        """Build a composite query from a list of queries.

        The queries are combined with the supplied operator, which is either
        SearchConnection.OP_AND or SearchConnection.OP_OR.

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        return _log(_xapian.Query, operator, list(queries))

    def query_multweight(self, query, multiplier):
        """Build a query which modifies the weights of a subquery.

        This produces a query which returns the same documents as the subquery,
        and in the same order, but with the weights assigned to each document
        multiplied by the value of "multiplier".  "multiplier" may be any floating
        point value, but negative values will be clipped to 0, since Xapian
        doesn't support negative weights.

        This can be useful when producing queries to be combined with
        query_composite, because it allows the relative importance of parts of
        the query to be adjusted.

        """
        return _log(_xapian.Query, _xapian.Query.OP_SCALE_WEIGHT, query, multiplier)

    def query_filter(self, query, filter, exclude=False):
        """Filter a query with another query.

        If exclude is False (or not specified), documents will only match the
        resulting query if they match the both the first and second query: the
        results of the first query are "filtered" to only include those which
        also match the second query.

        If exclude is True, documents will only match the resulting query if
        they match the first query, but not the second query: the results of
        the first query are "filtered" to only include those which do not match
        the second query.
        
        Documents will always be weighted according to only the first query.

        - `query`: The query to filter.
        - `filter`: The filter to apply to the query.
        - `exclude`: If True, the sense of the filter is reversed - only
          documents which do not match the second query will be returned. 

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        if not isinstance(filter, _xapian.Query):
            raise _errors.SearchError("Filter must be a Xapian Query object")
        if exclude:
            return _log(_xapian.Query, _xapian.Query.OP_AND_NOT, query, filter)
        else:
            return _log(_xapian.Query, _xapian.Query.OP_FILTER, query, filter)

    def query_adjust(self, primary, secondary):
        """Adjust the weights of one query with a secondary query.

        Documents will be returned from the resulting query if and only if they
        match the primary query (specified by the "primary" parameter).
        However, the weights (and hence, the relevance rankings) of the
        documents will be adjusted by adding weights from the secondary query
        (specified by the "secondary" parameter).

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        return _log(_xapian.Query, _xapian.Query.OP_AND_MAYBE, primary, secondary)

    def query_range(self, field, begin, end):
        """Create a query for a range search.
        
        This creates a query which matches only those documents which have a
        field value in the specified range.

        Begin and end must be appropriate values for the field, according to
        the 'type' parameter supplied to the SORTABLE action for the field.

        The begin and end values are both inclusive - any documents with a
        value equal to begin or end will be returned (unless end is less than
        begin, in which case no documents will be returned).

        Begin or end may be set to None in order to create an open-ended
        range.  (They may also both be set to None, which will generate a query
        which matches all documents containing any value for the field.)

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")

        if begin is None and end is None:
            # Return a "match everything" query
            return _log(_xapian.Query, '')

        try:
            slot = self._field_mappings.get_slot(field, 'collsort')
        except KeyError:
            # Return a "match nothing" query
            return _log(_xapian.Query)

        sorttype = self._get_sort_type(field)
        marshaller = SortableMarshaller(False)
        fn = marshaller.get_marshall_function(field, sorttype)

        if begin is not None:
            begin = fn(field, begin)
        if end is not None:
            end = fn(field, end)

        if begin is None:
            return _log(_xapian.Query, _xapian.Query.OP_VALUE_LE, slot, end)

        if end is None:
            return _log(_xapian.Query, _xapian.Query.OP_VALUE_GE, slot, begin)

        return _log(_xapian.Query, _xapian.Query.OP_VALUE_RANGE, slot, begin, end)

    def query_facet(self, field, val):
        """Create a query for a facet value.
        
        This creates a query which matches only those documents which have a
        facet value in the specified range.

        For a numeric range facet, val should be a tuple holding the start and
        end of the range, or a comma separated string holding two floating
        point values.  For other facets, val should be the value to look
        for.

        The start and end values are both inclusive - any documents with a
        value equal to start or end will be returned (unless end is less than
        start, in which case no documents will be returned).

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        if 'facets' in _checkxapian.missing_features:
            raise errors.SearchError("Facets unsupported with this release of xapian")

        try:
            actions = self._field_actions[field]._actions
        except KeyError:
            actions = {}
        facettype = None
        for action, kwargslist in actions.iteritems():
            if action == FieldActions.FACET:
                for kwargs in kwargslist:
                    facettype = kwargs.get('type', None)
                    if facettype is not None:
                        break
            if facettype is not None:
                break

        if facettype == 'float':
            if isinstance(val, basestring):
                val = [float(v) for v in val.split(',', 2)]
            assert(len(val) == 2)
            try:
                slot = self._field_mappings.get_slot(field, 'facet')
            except KeyError:
                return _log(_xapian.Query)
            # FIXME - check that sorttype == self._get_sort_type(field)
            sorttype = 'float'
            marshaller = SortableMarshaller(False)
            fn = marshaller.get_marshall_function(field, sorttype)
            begin = fn(field, val[0])
            end = fn(field, val[1])
            return _log(_xapian.Query, _xapian.Query.OP_VALUE_RANGE, slot, begin, end)
        else:
            assert(facettype == 'string' or facettype is None)
            prefix = self._field_mappings.get_prefix(field)
            return _log(_xapian.Query, prefix + val.lower())


    def _prepare_queryparser(self, allow, deny, default_op, default_allow,
                             default_deny):
        """Prepare (and return) a query parser using the specified fields and
        operator.

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")

        if isinstance(allow, basestring):
            allow = (allow, )
        if isinstance(deny, basestring):
            deny = (deny, )
        if allow is not None and len(allow) == 0:
            allow = None
        if deny is not None and len(deny) == 0:
            deny = None
        if allow is not None and deny is not None:
            raise _errors.SearchError("Cannot specify both `allow` and `deny` "
                                      "(got %r and %r)" % (allow, deny))

        if isinstance(default_allow, basestring):
            default_allow = (default_allow, )
        if isinstance(default_deny, basestring):
            default_deny = (default_deny, )
        if default_allow is not None and len(default_allow) == 0:
            default_allow = None
        if default_deny is not None and len(default_deny) == 0:
            default_deny = None
        if default_allow is not None and default_deny is not None:
            raise _errors.SearchError("Cannot specify both `default_allow` and `default_deny` "
                                      "(got %r and %r)" % (default_allow, default_deny))

        qp = _log(_xapian.QueryParser)
        qp.set_database(self._index)
        qp.set_default_op(default_op)

        if allow is None:
            allow = [key for key in self._field_actions]
        if deny is not None:
            allow = [key for key in allow if key not in deny]

        for field in allow:
            try:
                actions = self._field_actions[field]._actions
            except KeyError:
                actions = {}
            for action, kwargslist in actions.iteritems():
                if action == FieldActions.INDEX_EXACT:
                    # FIXME - need patched version of xapian to add exact prefixes
                    #qp.add_exact_prefix(field, self._field_mappings.get_prefix(field))
                    qp.add_prefix(field, self._field_mappings.get_prefix(field))
                if action == FieldActions.INDEX_FREETEXT:
                    allow_field_specific = True
                    for kwargs in kwargslist:
                        allow_field_specific = allow_field_specific or kwargs.get('allow_field_specific', True)
                    if not allow_field_specific:
                        continue
                    qp.add_prefix(field, self._field_mappings.get_prefix(field))
                    for kwargs in kwargslist:
                        try:
                            lang = kwargs['language']
                            my_stemmer = _log(_xapian.Stem, lang)
                            qp.my_stemmer = my_stemmer
                            qp.set_stemmer(my_stemmer)
                            qp.set_stemming_strategy(qp.STEM_SOME)
                        except KeyError:
                            pass

        if default_allow is not None or default_deny is not None:
            if default_allow is None:
                default_allow = [key for key in self._field_actions]
            if default_deny is not None:
                default_allow = [key for key in default_allow if key not in default_deny]
            for field in default_allow:
                try:
                    actions = self._field_actions[field]._actions
                except KeyError:
                    actions = {}
                for action, kwargslist in actions.iteritems():
                    if action == FieldActions.INDEX_FREETEXT:
                        qp.add_prefix('', self._field_mappings.get_prefix(field))
                        # FIXME - set stemming options for the default prefix

        return qp

    def _query_parse_with_prefix(self, qp, string, flags, prefix):
        """Parse a query, with an optional prefix.

        """
        if prefix is None:
            return qp.parse_query(string, flags)
        else:
            return qp.parse_query(string, flags, prefix)

    def _query_parse_with_fallback(self, qp, string, prefix=None):
        """Parse a query with various flags.
        
        If the initial boolean pass fails, fall back to not using boolean
        operators.

        """
        try:
            q1 = self._query_parse_with_prefix(qp, string,
                                               self._qp_flags_base |
                                               self._qp_flags_phrase |
                                               self._qp_flags_synonym |
                                               self._qp_flags_bool,
                                               prefix)
        except _xapian.QueryParserError, e:
            # If we got a parse error, retry without boolean operators (since
            # these are the usual cause of the parse error).
            q1 = self._query_parse_with_prefix(qp, string,
                                               self._qp_flags_base |
                                               self._qp_flags_phrase |
                                               self._qp_flags_synonym,
                                               prefix)

        qp.set_stemming_strategy(qp.STEM_NONE)
        try:
            q2 = self._query_parse_with_prefix(qp, string,
                                               self._qp_flags_base |
                                               self._qp_flags_bool,
                                               prefix)
        except _xapian.QueryParserError, e:
            # If we got a parse error, retry without boolean operators (since
            # these are the usual cause of the parse error).
            q2 = self._query_parse_with_prefix(qp, string,
                                               self._qp_flags_base,
                                               prefix)

        return _log(_xapian.Query, _xapian.Query.OP_AND_MAYBE, q1, q2)

    def query_parse(self, string, allow=None, deny=None, default_op=OP_AND,
                    default_allow=None, default_deny=None):
        """Parse a query string.

        This is intended for parsing queries entered by a user.  If you wish to
        combine structured queries, it is generally better to use the other
        query building methods, such as `query_composite` (though you may wish
        to create parts of the query to combine with such methods with this
        method).

        The string passed to this method can have various operators in it.  In
        particular, it may contain field specifiers (ie, field names, followed
        by a colon, followed by some text to search for in that field).  For
        example, if "author" is a field in the database, the search string
        could contain "author:richard", and this would be interpreted as
        "search for richard in the author field".  By default, any fields in
        the database which are indexed with INDEX_EXACT or INDEX_FREETEXT will
        be available for field specific searching in this way - however, this
        can be modified using the "allow" or "deny" parameters, and also by the
        allow_field_specific tag on INDEX_FREETEXT fields.

        Any text which isn't prefixed by a field specifier is used to search
        the "default set" of fields.  By default, this is the full set of
        fields in the database which are indexed with INDEX_FREETEXT and for
        which the search_by_default flag set (ie, if the text is found in any
        of those fields, the query will match).  However, this may be modified
        with the "default_allow" and "default_deny" parameters.  (Note that
        fields which are indexed with INDEX_EXACT aren't allowed to be used in
        the default list of fields.)

        - `string`: The string to parse.
        - `allow`: A list of fields to allow in the query.
        - `deny`: A list of fields not to allow in the query.
        - `default_op`: The default operator to combine query terms with.
        - `default_allow`: A list of fields to search for by default.
        - `default_deny`: A list of fields not to search for by default.

        Only one of `allow` and `deny` may be specified.

        Only one of `default_allow` and `default_deny` may be specified.

        If any of the entries in `allow` are not present in the configuration
        for the database, or are not specified for indexing (either as
        INDEX_EXACT or INDEX_FREETEXT), they will be ignored.  If any of the
        entries in `deny` are not present in the configuration for the
        database, they will be ignored.

        Returns a Query object, which may be passed to the search() method, or
        combined with other queries.

        """
        qp = self._prepare_queryparser(allow, deny, default_op, default_allow,
                                       default_deny)
        return self._query_parse_with_fallback(qp, string)

    def query_field(self, field, value, default_op=OP_AND):
        """A query for a single field.

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        try:
            actions = self._field_actions[field]._actions
        except KeyError:
            actions = {}

        # need to check on field type, and stem / split as appropriate
        for action, kwargslist in actions.iteritems():
            if action in (FieldActions.INDEX_EXACT,
                          FieldActions.TAG,
                          FieldActions.FACET,):
                prefix = self._field_mappings.get_prefix(field)
                if len(value) > 0:
                    chval = ord(value[0])
                    if chval >= ord('A') and chval <= ord('Z'):
                        prefix = prefix + ':'
                return _log(_xapian.Query, prefix + value)
            if action == FieldActions.INDEX_FREETEXT:
                qp = _log(_xapian.QueryParser)
                qp.set_default_op(default_op)
                prefix = self._field_mappings.get_prefix(field)
                for kwargs in kwargslist:
                    try:
                        lang = kwargs['language']
                        qp.set_stemmer(_log(_xapian.Stem, lang))
                        qp.set_stemming_strategy(qp.STEM_SOME)
                    except KeyError:
                        pass
                return self._query_parse_with_fallback(qp, value, prefix)

        return _log(_xapian.Query)

    def query_similar(self, ids, allow=None, deny=None, simterms=10, weight=None):
        """Get a query which returns documents which are similar to others.

        The list of document IDs to base the similarity search on is given in
        `ids`.  This should be an iterable, holding a list of strings.  If
        any of the supplied IDs cannot be found in the database, they will be
        ignored.  (If no IDs can be found in the database, the resulting query
        will not match any documents.)

        By default, all fields which have been indexed for freetext searching
        will be used for the similarity calculation.  The list of fields used
        for this can be customised using the `allow` and `deny` parameters
        (only one of which may be specified):

        - `allow`: A list of fields to base the similarity calculation on.
        - `deny`: A list of fields not to base the similarity calculation on.
        - `simterms`: Number of terms to use for the similarity calculation.

        For convenience, any of `ids`, `allow`, or `deny` may be strings, which
        will be treated the same as a list of length 1.

        Regardless of the setting of `allow` and `deny`, only fields which have
        been indexed for freetext searching will be used for the similarity
        measure - all other fields will always be ignored for this purpose.

        The `weight` parameter overrides the connection's default weighting.
        """
        eterms, prefixes = self._get_eterms(ids, allow, deny, simterms, weight)

        # Use the "elite set" operator, which chooses the terms with the
        # highest query weight to use.
        q = _log(_xapian.Query, _xapian.Query.OP_ELITE_SET, eterms, simterms)
        return q

    def significant_terms(self, ids, maxterms=10, allow=None, deny=None, weight=None):
        """Get a set of "significant" terms for a document, or documents.

        This has a similar interface to query_similar(): it takes a list of
        ids, and an optional specification of a set of fields to consider.
        Instead of returning a query, it returns a list of terms from the
        document (or documents), which appear "significant".  Roughly,
        in this situation significant means that the terms occur more
        frequently in the specified document than in the rest of the corpus.

        The list is in decreasing order of "significance".

        By default, all terms related to fields which have been indexed for
        freetext searching will be considered for the list of significant
        terms.  The list of fields used for this can be customised using the
        `allow` and `deny` parameters (only one of which may be specified):

        - `allow`: A list of fields to consider.
        - `deny`: A list of fields not to consider.

        For convenience, any of `ids`, `allow`, or `deny` may be strings, which
        will be treated the same as a list of length 1.

        Regardless of the setting of `allow` and `deny`, only fields which have
        been indexed for freetext searching will be considered - all other
        fields will always be ignored for this purpose.

        The maximum number of terms to return may be specified by the maxterms
        parameter.

        The `weight` parameter overrides the connection's default weighting.
        """
        eterms, prefixes = self._get_eterms(ids, allow, deny, maxterms, weight)
        terms = []
        for term in eterms:
            pos = 0
            for char in term:
                if not char.isupper():
                    break
                pos += 1
            field = prefixes[term[:pos]]
            value = term[pos:]
            terms.append((field, value))
        return terms

    def _get_eterms(self, ids, allow, deny, simterms, weight=None):
        """Get a set of terms for an expand

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        if allow is not None and deny is not None:
            raise _errors.SearchError("Cannot specify both `allow` and `deny`")

        if isinstance(ids, basestring):
            ids = (ids, )
        if isinstance(allow, basestring):
            allow = (allow, )
        if isinstance(deny, basestring):
            deny = (deny, )

        # Set "allow" to contain a list of all the fields to use.
        if allow is None:
            allow = [key for key in self._field_actions]
        if deny is not None:
            allow = [key for key in allow if key not in deny]

        # Set "prefixes" to contain a list of all the prefixes to use.
        prefixes = {}
        for field in allow:
            try:
                actions = self._field_actions[field]._actions
            except KeyError:
                actions = {}
            for action, kwargslist in actions.iteritems():
                if action == FieldActions.INDEX_FREETEXT:
                    prefixes[self._field_mappings.get_prefix(field)] = field

        # Repeat the expand until we don't get a DatabaseModifiedError
        while True:
            try:
                eterms = self._perform_expand(ids, prefixes, simterms, weight)
                break;
            except _xapian.DatabaseModifiedError, e:
                self.reopen()
        return eterms, prefixes

    class ExpandDecider(_xapian.ExpandDecider):
        def __init__(self, prefixes):
            _xapian.ExpandDecider.__init__(self)
            self._prefixes = prefixes

        def __call__(self, term):
            pos = 0
            for char in term:
                if not char.isupper():
                    break
                pos += 1
            if term[:pos] in self._prefixes:
                return True
            return False

    def _perform_expand(self, ids, prefixes, simterms, weight=None):
        """Perform an expand operation to get the terms for a similarity
        search, given a set of ids (and a set of prefixes to restrict the
        similarity operation to).
        """
        # Set idquery to be a query which returns the documents listed in
        # "ids".
        idquery = _log(_xapian.Query, _xapian.Query.OP_OR, ['Q' + id for id in ids])

        enq = _log(_xapian.Enquire, self._index)
        if weight is not None:
            enq.set_weighting_scheme(weight)
        else:
            enq.set_weighting_scheme(self._weight)
        enq.set_query(idquery)
        rset = _log(_xapian.RSet)
        for id in ids:
            pl = self._index.postlist('Q' + id)
            try:
                xapid = pl.next()
                rset.add_document(xapid.docid)
            except StopIteration:
                pass

        expanddecider = _log(self.ExpandDecider, prefixes)
        eset = enq.get_eset(simterms, rset, 0, 1.0, expanddecider)
        return [term.term for term in eset]

    def query_all(self):
        """A query which matches all the documents in the database.

        """
        return _log(_xapian.Query, '')

    def query_none(self):
        """A query which matches no documents in the database.

        This may be useful as a placeholder in various situations.

        """
        return _log(_xapian.Query)

    def spell_correct(self, querystr, allow=None, deny=None, default_op=OP_AND,
                      default_allow=None, default_deny=None):
        """Correct a query spelling.

        This returns a version of the query string with any misspelt words
        corrected.

        - `allow`: A list of fields to allow in the query.
        - `deny`: A list of fields not to allow in the query.
        - `default_op`: The default operator to combine query terms with.
        - `default_allow`: A list of fields to search for by default.
        - `default_deny`: A list of fields not to search for by default.

        Only one of `allow` and `deny` may be specified.

        Only one of `default_allow` and `default_deny` may be specified.

        If any of the entries in `allow` are not present in the configuration
        for the database, or are not specified for indexing (either as
        INDEX_EXACT or INDEX_FREETEXT), they will be ignored.  If any of the
        entries in `deny` are not present in the configuration for the
        database, they will be ignored.

        Note that it is possible that the resulting spell-corrected query will
        still match no documents - the user should usually check that some
        documents are matched by the corrected query before suggesting it to
        users.

        """
        qp = self._prepare_queryparser(allow, deny, default_op, default_allow,
                                       default_deny)
        try:
            qp.parse_query(querystr,
                           self._qp_flags_base |
                           self._qp_flags_phrase |
                           self._qp_flags_synonym |
                           self._qp_flags_bool |
                           qp.FLAG_SPELLING_CORRECTION)
        except _xapian.QueryParserError:
            qp.parse_query(querystr,
                           self._qp_flags_base |
                           self._qp_flags_phrase |
                           self._qp_flags_synonym |
                           qp.FLAG_SPELLING_CORRECTION)
        corrected = qp.get_corrected_query_string()
        if len(corrected) == 0:
            if isinstance(querystr, unicode):
                # Encode as UTF-8 for consistency - this happens automatically
                # to values passed to Xapian.
                return querystr.encode('utf-8')
            return querystr
        return corrected

    def can_collapse_on(self, field):
        """Check if this database supports collapsing on a specified field.

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        try:
            self._field_mappings.get_slot(field, 'collsort')
        except KeyError:
            return False
        return True

    def can_sort_on(self, field):
        """Check if this database supports sorting on a specified field.

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        try:
            self._field_mappings.get_slot(field, 'collsort')
        except KeyError:
            return False
        return True
        
    def _get_prefix_from_term(self, term):
        """Get the prefix of a term.
   
        Prefixes are any initial capital letters, with the exception that R always
        ends a prefix, even if followed by capital letters.
        
        """
        for p in xrange(len(term)):
            if term[p].islower():
                return term[:p]
            elif term[p] == 'R':
                return term[:p+1]
        return term

    def _facet_query_never(self, facet, query_type):
        """Check if a facet must never be returned by a particular query type.

        Returns True if the facet must never be returned.

        Returns False if the facet may be returned - either becuase there is no
        entry for the query type, or because the entry is not
        FacetQueryType_Never.

        """
        if query_type is None:
            return False
        if query_type not in self._facet_query_table:
            return False
        if facet not in self._facet_query_table[query_type]:
            return False
        return self._facet_query_table[query_type][facet] == _indexerconnection.IndexerConnection.FacetQueryType_Never

    def search(self, query, startrank, endrank,
               checkatleast=0, sortby=None, collapse=None,
               gettags=None,
               getfacets=None, allowfacets=None, denyfacets=None, usesubfacets=None,
               percentcutoff=None, weightcutoff=None,
               query_type=None, weight=None):
        """Perform a search, for documents matching a query.

        - `query` is the query to perform.
        - `startrank` is the rank of the start of the range of matching
          documents to return (ie, the result with this rank will be returned).
          ranks start at 0, which represents the "best" matching document.
        - `endrank` is the rank at the end of the range of matching documents
          to return.  This is exclusive, so the result with this rank will not
          be returned.
        - `checkatleast` is the minimum number of results to check for: the
          estimate of the total number of matches will always be exact if
          the number of matches is less than `checkatleast`.  A value of ``-1``
          can be specified for the checkatleast parameter - this has the
          special meaning of "check all matches", and is equivalent to passing
          the result of get_doccount().
        - `sortby` is the name of a field to sort by.  It may be preceded by a
          '+' or a '-' to indicate ascending or descending order
          (respectively).  If the first character is neither '+' or '-', the
          sort will be in ascending order.
        - `collapse` is the name of a field to collapse the result documents
          on.  If this is specified, there will be at most one result in the
          result set for each value of the field.
        - `gettags` is the name of a field to count tag occurrences in, or a
          list of fields to do so.
        - `getfacets` is a boolean - if True, the matching documents will be
          examined to build up a list of the facet values contained in them.
        - `allowfacets` is a list of the fieldnames of facets to consider.
        - `denyfacets` is a list of fieldnames of facets which will not be
          considered.
        - `usesubfacets` is a boolean - if True, only top-level facets and
          subfacets of facets appearing in the query are considered (taking
          precedence over `allowfacets` and `denyfacets`).
        - `percentcutoff` is the minimum percentage a result must have to be
          returned.
        - `weightcutoff` is the minimum weight a result must have to be
          returned.
        - `query_type` is a value indicating the type of query being
          performed. If not None, the value is used to influence which facets
          are be returned by the get_suggested_facets() function. If the
          value of `getfacets` is False, it has no effect.
        - `weight` overrides the connection's xapian.Weight

        If neither 'allowfacets' or 'denyfacets' is specified, all fields
        holding facets will be considered (but see 'usesubfacets').

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        if 'facets' in _checkxapian.missing_features:
            if getfacets is not None or \
               allowfacets is not None or \
               denyfacets is not None or \
               usesubfacets is not None or \
               query_type is not None:
                raise errors.SearchError("Facets unsupported with this release of xapian")
        if 'tags' in _checkxapian.missing_features:
            if gettags is not None:
                raise errors.SearchError("Tags unsupported with this release of xapian")
        if checkatleast == -1:
            checkatleast = self._index.get_doccount()

        enq = _log(_xapian.Enquire, self._index)
        if weight is not None:
            enq.set_weighting_scheme(weight)
        else:
            enq.set_weighting_scheme(self._weight)
        enq.set_query(query)

        if sortby is not None:
            asc = True
            if sortby[0] == '-':
                asc = False
                sortby = sortby[1:]
            elif sortby[0] == '+':
                sortby = sortby[1:]

            try:
                slotnum = self._field_mappings.get_slot(sortby, 'collsort')
            except KeyError:
                raise _errors.SearchError("Field %r was not indexed for sorting" % sortby)

            # Note: we invert the "asc" parameter, because xapian treats
            # "ascending" as meaning "higher values are better"; in other
            # words, it considers "ascending" to mean return results in
            # descending order.
            enq.set_sort_by_value_then_relevance(slotnum, not asc)

        if collapse is not None:
            try:
                slotnum = self._field_mappings.get_slot(collapse, 'collsort')
            except KeyError:
                raise _errors.SearchError("Field %r was not indexed for collapsing" % collapse)
            enq.set_collapse_key(slotnum)

        maxitems = max(endrank - startrank, 0)
        # Always check for at least one more result, so we can report whether
        # there are more matches.
        checkatleast = max(checkatleast, endrank + 1)

        # Build the matchspy.
        matchspies = []

        # First, add a matchspy for any gettags fields
        if isinstance(gettags, basestring):
            if len(gettags) != 0:
                gettags = [gettags]
        tagspy = None
        if gettags is not None and len(gettags) != 0:
            tagspy = _log(_xapian.TermCountMatchSpy)
            for field in gettags:
                try:
                    prefix = self._field_mappings.get_prefix(field)
                    tagspy.add_prefix(prefix)
                except KeyError:
                    raise _errors.SearchError("Field %r was not indexed for tagging" % field)
            matchspies.append(tagspy)


        # add a matchspy for facet selection here.
        facetspy = None
        facetfields = []
        if getfacets:
            if allowfacets is not None and denyfacets is not None:
                raise _errors.SearchError("Cannot specify both `allowfacets` and `denyfacets`")
            if allowfacets is None:
                allowfacets = [key for key in self._field_actions]
            if denyfacets is not None:
                allowfacets = [key for key in allowfacets if key not in denyfacets]

            # include None in queryfacets so a top-level facet will
            # satisfy self._facet_hierarchy.get(field) in queryfacets
            # (i.e. always include top-level facets)
            queryfacets = set([None])
            if usesubfacets:
                # add facets used in the query to queryfacets
                termsiter = query.get_terms_begin()
                termsend = query.get_terms_end()
                while termsiter != termsend:
                    prefix = self._get_prefix_from_term(termsiter.get_term())
                    field = self._field_mappings.get_fieldname_from_prefix(prefix)
                    if field and FieldActions.FACET in self._field_actions[field]._actions:
                        queryfacets.add(field)
                    termsiter.next()

            for field in allowfacets:
                try:
                    actions = self._field_actions[field]._actions
                except KeyError:
                    actions = {}
                for action, kwargslist in actions.iteritems():
                    if action == FieldActions.FACET:
                        # filter out non-top-level facets that aren't subfacets
                        # of a facet in the query
                        if usesubfacets and self._facet_hierarchy.get(field) not in queryfacets:
                            continue
                        # filter out facets that should never be returned for the query type
                        if self._facet_query_never(field, query_type):
                            continue
                        slot = self._field_mappings.get_slot(field, 'facet')
                        if facetspy is None:
                            facetspy = _log(_xapian.CategorySelectMatchSpy)
                        facettype = None
                        for kwargs in kwargslist:
                            facettype = kwargs.get('type', None)
                            if facettype is not None:
                                break
                        if facettype is None or facettype == 'string':
                            facetspy.add_slot(slot, True)
                        else:
                            facetspy.add_slot(slot)
                        facetfields.append((field, slot, kwargslist))

            if facetspy is None:
                # Set facetspy to False, to distinguish from no facet
                # calculation being performed.  (This will prevent an
                # error being thrown when the list of suggested facets is
                # requested - instead, an empty list will be returned.)
                facetspy = False
            else:
                matchspies.append(facetspy)


        # Finally, build a single matchspy to pass to get_mset().
        if len(matchspies) == 0:
            matchspy = None
        elif len(matchspies) == 1:
            matchspy = matchspies[0]
        else:
            matchspy = _log(_xapian.MultipleMatchDecider)
            for spy in matchspies:
                matchspy.append(spy)

        enq.set_docid_order(enq.DONT_CARE)

        # Set percentage and weight cutoffs
        if percentcutoff is not None or weightcutoff is not None:
            if percentcutoff is None:
                percentcutoff = 0
            if weightcutoff is None:
                weightcutoff = 0
            enq.set_cutoff(percentcutoff, weightcutoff)

        # Repeat the search until we don't get a DatabaseModifiedError
        while True:
            try:
                if matchspy is None:
                    mset = enq.get_mset(startrank, maxitems, checkatleast)
                else:
                    mset = enq.get_mset(startrank, maxitems, checkatleast,
                                        None, None, matchspy)
                break
            except _xapian.DatabaseModifiedError, e:
                self.reopen()
        facet_hierarchy = None
        if usesubfacets:
            facet_hierarchy = self._facet_hierarchy
            
        return SearchResults(self, enq, query, mset, self._field_mappings,
                             tagspy, gettags, facetspy, facetfields,
                             facet_hierarchy,
                             self._facet_query_table.get(query_type))

    def iterids(self):
        """Get an iterator which returns all the ids in the database.

        The unqiue_ids are currently returned in binary lexicographical sort
        order, but this should not be relied on.

        Note that the iterator returned by this method may raise a
        xapian.DatabaseModifiedError exception if modifications are committed
        to the database while the iteration is in progress.  If this happens,
        the search connection must be reopened (by calling reopen) and the
        iteration restarted.

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        return _indexerconnection.PrefixedTermIter('Q', self._index.allterms())

    def get_document(self, id):
        """Get the document with the specified unique ID.

        Raises a KeyError if there is no such document.  Otherwise, it returns
        a ProcessedDocument.

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        while True:
            try:
                postlist = self._index.postlist('Q' + id)
                try:
                    plitem = postlist.next()
                except StopIteration:
                    # Unique ID not found
                    raise KeyError('Unique ID %r not found' % id)
                try:
                    postlist.next()
                    raise _errors.IndexerError("Multiple documents " #pragma: no cover
                                               "found with same unique ID")
                except StopIteration:
                    # Only one instance of the unique ID found, as it should be.
                    pass

                result = ProcessedDocument(self._field_mappings)
                result.id = id
                result._doc = self._index.get_document(plitem.docid)
                return result
            except _xapian.DatabaseModifiedError, e:
                self.reopen()

    def iter_synonyms(self, prefix=""):
        """Get an iterator over the synonyms.

         - `prefix`: if specified, only synonym keys with this prefix will be
           returned.

        The iterator returns 2-tuples, in which the first item is the key (ie,
        a 2-tuple holding the term or terms which will be synonym expanded,
        followed by the fieldname specified (or None if no fieldname)), and the
        second item is a tuple of strings holding the synonyms for the first
        item.

        These return values are suitable for the dict() builtin, so you can
        write things like:

         >>> conn = _indexerconnection.IndexerConnection('foo')
         >>> conn.add_synonym('foo', 'bar')
         >>> conn.add_synonym('foo bar', 'baz')
         >>> conn.add_synonym('foo bar', 'foo baz')
         >>> conn.flush()
         >>> conn = SearchConnection('foo')
         >>> dict(conn.iter_synonyms())
         {('foo', None): ('bar',), ('foo bar', None): ('baz', 'foo baz')}

        """
        if self._index is None:
            raise _errors.SearchError("SearchConnection has been closed")
        return _indexerconnection.SynonymIter(self._index, self._field_mappings, prefix)

    def get_metadata(self, key):
        """Get an item of metadata stored in the connection.

        This returns a value stored by a previous call to
        IndexerConnection.set_metadata.

        If the value is not found, this will return the empty string.

        """
        if self._index is None:
            raise _errors.IndexerError("SearchConnection has been closed")
        if not hasattr(self._index, 'get_metadata'):
            raise _errors.IndexerError("Version of xapian in use does not support metadata")
        return _log(self._index.get_metadata, key)

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod (sys.modules[__name__])

########NEW FILE########
__FILENAME__ = _checkxapian
# Copyright (C) 2008 Lemur Consulting Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
r"""_checkxapian.py: Check the version of xapian used.

Raises an ImportError on import if the version used is too old to be used at
all.

"""
__docformat__ = "restructuredtext en"

# The minimum version of xapian required to work at all.
min_xapian_version = (1, 0, 6)

# Dictionary of features we can't support do to them being missing from the
# available version of xapian.
missing_features = {}

import xapian

versions = xapian.major_version(), xapian.minor_version(), xapian.revision()


if versions < min_xapian_version:
    raise ImportError("""
        Xapian Python bindings installed, but need at least version %d.%d.%d - got %s
        """.strip() % tuple(list(min_xapian_version) + [xapian.version_string()]))

if not hasattr(xapian, 'TermCountMatchSpy'):
    missing_features['tags'] = 1
if not hasattr(xapian, 'CategorySelectMatchSpy'):
    missing_features['facets'] = 1

########NEW FILE########
__FILENAME__ = fabfile
"""
Remote server layout:

PATH/releases -- unpacked versions (versioned by datetime of fabric invocation)
  also current & previous doing the obvious thing (as symlinks)
  within each, ENV a virtualenv just for that version
PATH/archives -- tgz archives of versions

Use the setup action to build the bits you need.
"""

from fabric.api import *
from fabric.contrib.files import exists
import tempfile
import os

env.branch = "master"

# App choices

def artemis():
    env.django_project_name = 'artemis'
    env.staging_hosts = ['core.fort'] # old, aww
    env.live_hosts = ['spacelog.org']
    env.user = 'spacelog'
    env.path = '/home/spacelog'

# only one app
artemis()

# Environment choices

def staging():
    env.hosts = env.staging_hosts
    env.environment = 'staging'

def live():
    env.hosts = env.live_hosts
    env.environment = 'live'

# tasks

def dirty_deploy():
    """
    Do a dirty deploy. For some reason, fab doesn't want to let me pass True through
    to the dirty parameter of deploy().
    """
    deploy(True)

def deploy(dirty=False):
    """
    Deploy the latest version of the site to the servers, install any
    required third party modules and then restart the webserver
    """
    require('hosts')
    require('path')

    ponder_release()

    export_and_upload_tar_from_git()
    if dirty:
        copy_previous_virtualenv()
    else:
        make_release_virtualenv()
    prepare_release(dirty)
    switch_to(env.release)
    restart_webserver()

def setup():
    """
    Set up the initial structure for the given user.
    """
    require('hosts')
    require('path')
    
    run("mkdir releases")
    run("mkdir archives")

def switch_to(version):
    """Switch the current (ie live) version"""
    require('hosts')
    require('path')
    
    if exists('%s/releases/previous' % env.path):
        run('rm %s/releases/previous' % env.path)
    if exists('%s/releases/current' % env.path):
        run('mv %s/releases/current %s/releases/previous' % (env.path, env.path))
    run('cd %s; ln -s %s releases/current' % (env.path, version))
    
    env.release = version # in case anything else wants to use it after us

def switch_to_version(version):
    "Specify a specific version to be made live"
    switch_to(version)
    restart_webserver()
    
# Helpers. These are called by other functions rather than directly

def ponder_release():
    import time
    env.release = time.strftime('%Y-%m-%dT%H.%M.%S')

def export_and_upload_tar_from_git():
    "Create an archive from the git local repo."
    require('release', provided_by=[deploy])
    export_tgz_from_git()
    upload_tar()

def export_tgz_from_git():
    "Create an archive from the git local repo."
    local("git archive --format=tar --prefix=%(release)s/ %(branch)s | gzip -c > %(release)s.tar.gz" % {
        'release': env.release,
        'branch': env.branch,
        }
    )

def upload_tar():
    require('release', provided_by=[deploy])
    require('path', provided_by=[deploy])

    put('%s.tar.gz' % env.release, '%s/archives/' % env.path)
    run('cd %s/releases && gzip -dc ../archives/%s.tar.gz | tar xf -' % (env.path, env.release))
    local('rm %s.tar.gz' % env.release)

def copy_previous_virtualenv():
    "Copy a previous virtualenv, for when making a new one is too much of a PITA"
    require('release', provided_by=[deploy])
    run(
        "cp -a %(path)s/releases/current/ENV %(path)s/releases/%(release)s/ENV" % {
            'path': env.path,
            'release': env.release,
        }
    )

def make_release_virtualenv():
    "Make a virtualenv and install the required packages into it"
    require('release', provided_by=[deploy])
    new_release_virtualenv()
    update_release_virtualenv()
    
def new_release_virtualenv():
    "Create a new virtualenv, install pip, and upgrade setuptools"
    require('release', provided_by=[deploy])
    run(
        "cd %(path)s/releases/%(release)s; "
        "virtualenv ENV; "
        "ENV/bin/easy_install pip; "
        "ENV/bin/easy_install -U setuptools" % {
            'path': env.path,
            'release': env.release
        }
    )
    
def update_release_virtualenv():
    "Install the required packages from the requirements file using pip"
    require('release', provided_by=[deploy])
    run(
        "cd %(path)s/releases/%(release)s; "
        "ENV/bin/pip --default-timeout=600 install -r requirements.txt" % {
            'path': env.path,
            'release': env.release
        }
    )

def prepare_release(dirty=False):
    "Do any release-local build actions."
    require('release', provided_by=[deploy])
    if dirty:
        # basically, don't reindex, but copy the xappydb from the
        # currently-running deploy (in ../current)
        run(
            "make -C %(path)s/releases/%(release)s/ dirty" % {
                'environment': env.environment,
                'path': env.path,
                'project': env.django_project_name,
                'release': env.release
            }
        )
    else:
        run(
            "make -C %(path)s/releases/%(release)s/" % {
                'environment': env.environment,
                'path': env.path,
                'project': env.django_project_name,
                'release': env.release
            }
        )
    make_local_settings()

def make_local_settings():
    """
    make local_settings.py for both global & website that change
    the deployed URLs for static files (both global and mission-specific)
    to use env.release in their paths.
    
    then put it up to the release on live
    """
    require('release', provided_by=[deploy])

    (fd, fname) = tempfile.mkstemp()
    os.write(fd, """
# Override the default CDN URLs to use this release's timestamp
# (website)
STATIC_URL = 'http://cdn.spacelog.org/%(release)s/assets/website/'
MISSIONS_STATIC_URL = 'http://cdn.spacelog.org/%(release)s/assets/website/missions/'
""" % {
        'release': env.release,
    }
    )
    os.close(fd)
    put(
        fname,
        '%(path)s/releases/%(release)s/website/local_settings.py' % {
            'path': env.path,
            'release': env.release,
        }
    )
    os.unlink(fname)

    (fd, fname) = tempfile.mkstemp()
    os.write(fd, """
# Override the default CDN URLs to use this release's timestamp
# (global)
STATIC_URL = 'http://cdn.spacelog.org/%(release)s/assets/global/'
MISSIONS_STATIC_URL = 'http://cdn.spacelog.org/%(release)s/assets/website/missions/'
""" % {
        'release': env.release,
    }
    )
    os.close(fd)
    put(
        fname,
        '%(path)s/releases/%(release)s/global/local_settings.py' % {
            'path': env.path,
            'release': env.release,
        }
    )
    os.unlink(fname)

def restart_webserver():
    "Restart the web server"
    run("userv root apache2-reload")

########NEW FILE########
__FILENAME__ = context
from django.conf import settings

def static(request):
    return {
        "STATIC_URL": settings.STATIC_URL,
        "FIXED_STATIC_URL": settings.FIXED_STATIC_URL,
        "MISSIONS_STATIC_URL": settings.MISSIONS_STATIC_URL,
    }

########NEW FILE########
__FILENAME__ = middleware
import redis
from django.shortcuts import render_to_response
from django.template import RequestContext

class HoldingMiddleware(object):
    """
    Shows a holding page if we're in the middle of an upgrade.
    """
    def process_request(self, request):
        request.redis_conn = redis.Redis()
        # Get the current database
        request.redis_conn.select(int(request.redis_conn.get("live_database") or 0))
        if request.redis_conn.get("hold"):
            if request.path.startswith("/assets"):
                request.holding = True
            else:
                response = render_to_response(
                    "holding.html",
                    {},
                    RequestContext(request),
                )
                response.status_code = 503
                return response
        else:
            request.holding = False


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = missions
from django.template import Library
from django.conf import settings

register = Library()

@register.filter
def featured(missions, featured=True):
    if featured != True:
        featured = (featured.lower() == 'true')
    return [ mission for mission in missions if mission.featured == featured ]

@register.filter
def mission_url(mission):
    if isinstance(mission, basestring):
        return u"http://%s.%s/" % (mission, settings.PROJECT_DOMAIN)
    else:
        if mission.subdomain is not None:
            return u"http://%s.%s/" % (mission.subdomain, settings.PROJECT_DOMAIN)
        else:
            return u"http://%s.%s/" % (mission.name, settings.PROJECT_DOMAIN)

########NEW FILE########
__FILENAME__ = views
# -*- encoding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.cache import cache_control
from urllib import quote
import random
from backend.api import Mission

AFFILIATE_CODES = {'us': 'spacelog-20', 'uk': 'spacelog-21'}

READING_LISTS = [
    ("By astronauts and cosmonauts",
        [
            ("Deke!",           "Deke Slayton with Michael Cassutt",    "031285918X"),
            ("We Seven",        "The Mercury Astronauts",               "1439181039"),
            ("We Have Capture", "Tom Stafford with Michael Cassutt",    "1588341011"),
            ("Two Sides of the Moon", "David Scott and Alexei Leonov",  "0312308663"),
        ]),
    ("By other principals",
        [
            ("Flight",          "Chris Kraft",                          "B000EXYZR2"),
            ("Project Mars: A Technical Tale", "Wernher von Braun",     "0973820330"),
        ]),
    ("Other books",
        [
            ("Full Moon",       "Michael Light",                        "0375406344"),
        ])
]

class Thing:
    def __init__(self, quote, snippet, url, source, date):
        self.quote = quote
        self.snippet = snippet
        self.url = url
        self.source = source
        self.date = date

NICE_THINGS = [
    Thing(
        "What could possibly be cooler…gorgeous, elegant and easy-to-use",
        "What could possibly be cooler?",
        "http://techland.time.com/2011/05/11/site-built-in-a-fort-lets-you-scan-pivotal-space-tales/",
        "time.com",
        "11 May, 2011",
    ),
    Thing(
        "Seriously cool.",
        "Seriously cool",
        "http://techcrunch.com/2011/05/07/did-devfort-just-hand-over-astronaut-listening-data-to-the-www/",
        "TechCrunch",
        "7 May, 2011",
    ),
    Thing(
        "A must-visit site for space enthusiasts.", 
        "Must-visit for space enthusiasts", 
        "http://www.komando.com/coolsites/index.aspx?id=10587", "Kim Komando Cool Site of the Day",  "11 Apr, 2011",
    ),
  
    Thing(
        "Spacelog is awesome.", 
        "Spacelog is awesome", 
        "http://www.rockpapershotgun.com/2010/12/05/the-sunday-papers-148/", "Rock, Paper, Shotgun", "5 Dec, 2010",
    ),

    Thing(
        "This is the kind of historical documentation and access that reminds us of why the internet is so, insanely awesome.", 
        "Reminds us the internet is so, insanely awesome",
        "http://www.engadget.com/2010/12/02/spacelog-provides-fascinating-searchable-text-transcripts-for-na/", "Engadget", "2 Dec, 2010",
    ),

    Thing(
        "&hellip;highly addictive&hellip;", 
        "&hellip;highly addictive&hellip;", 
        "http://www.huffingtonpost.com/2010/12/02/spacelogorg-nasa-mission-transcripts_n_790735.html", "The Huffington Post", "2 Dec, 2010",
    ),

    Thing(
        "[Spacelog] is the best thing ever on the internet!", 
        "[Spacelog] is the best thing ever on the internet!", 
        "http://twitter.com/moleitau/status/9930034542288896", "Matt Jones", "1 Dec, 2010",
    ),

    Thing(
        "Wonderful stuff.", 
        "Wonderful stuff", 
        "http://kottke.org/10/12/spacelog", "Jason Kottke", "1 Dec, 2010",
    ),

    Thing(
        "I absolutely love this. Spacelog.org is taking the radio transcripts from NASA missions, pairing them with great graphic design, and making the whole thing searchable and linkable. The result: A delightfully immersive perspective on history.", 
        "A delightfully immersive perspective on history",
        "http://www.boingboing.net/2010/12/01/an-interactive-histo.html", "Boing Boing", "1 Dec, 2010",
    ),

    Thing(
        "If this isn’t making content meaningful, accessible (in a traditional sense), and enjoyable to consume, I don’t know what is.",
        "Meaningful, accessible and enjoyable",
        "http://cameronmoll.tumblr.com/post/2060251631/spacelog", "Cameron Moll", "1 Dec, 2010",
    ),
]

def homepage(request):
    missions = [
        mission for mission in list(Mission.Query(request.redis_conn))
        if not mission.incomplete
    ]
    missions_coming_soon = [
        mission for mission in list(Mission.Query(request.redis_conn))
        if mission.incomplete and mission.featured
    ]
    return render_to_response(
        'homepage/homepage.html',
        {
            'missions': missions,
            'missions_coming_soon': missions_coming_soon,
            'quote': random.choice(NICE_THINGS),
        },
        context_instance = RequestContext(request),
    )

def _get_amazon_url(country_code, asin):
    if country_code.lower() == 'uk':
        domain = 'co.uk'
        code = AFFILIATE_CODES['uk']
    else:
        domain = 'com'
        code = AFFILIATE_CODES['us']
    url = "http://www.amazon.%s/dp/%s" % (domain, asin)
    link_string = "http://www.amazon.%s/gp/redirect.html?ie=UTF8&location=%s&tag=%s" % \
            (domain, quote(url, safe=''), code)
    return link_string

def _get_image_url(asin):
    return "http://images.amazon.com/images/P/%(asin)s.01.THUMBZZZ.jpg" % {
        'asin': asin,
    }

def _get_reading_list(country_code):
    reading_list = []
    for category, books in READING_LISTS:
        books_new = []
        for title, author, asin in books:
            books_new.append((title, author, _get_amazon_url(country_code, asin), _get_image_url(asin)))
        reading_list.append((category, books_new))
    return reading_list

@cache_control(no_cache=True)
def about(request):
    return render_to_response(
            'pages/about.html',
            {'READING_LISTS': _get_reading_list(request.META.get('GEOIP_COUNTRY_CODE', '--')), 'page': 'about'},
            context_instance = RequestContext(request),
            )

@cache_control(no_cache=True)
def press(request):
    return render_to_response(
            'pages/press.html',
            {
                'page': 'press',
                'NICE_THINGS': NICE_THINGS,
            },
            context_instance = RequestContext(request),
            )

@cache_control(no_cache=True)
def get_involved(request):
    return render_to_response(
            'pages/get-involved.html',
            {'page': 'get-involved'},
            context_instance = RequestContext(request),
            )

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = xappy
from django.template import Library
from django.utils.safestring import mark_safe

register = Library()

@register.filter
def summarise(result, field):
    return mark_safe(result.summarise(field, maxlen=100, ellipsis='&hellip;', hl=('<em>', '</em>')))

########NEW FILE########
__FILENAME__ = views
import os
import urllib
from django.views.generic import TemplateView
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.safestring import mark_safe
import xappy
import xapian
import redis
from backend.api import LogLine, Character

PAGESIZE = 20

class SearchView(TemplateView):

    template_name = 'search/results.html'

    def get_context_data(self):
        # Get the query text
        q = self.request.GET.get('q', '')
        # Get the offset value
        try:
            offset = int(
                self.request.GET.get('offset', '0')
            )
            if offset < 0:
                offset = 0
        except ValueError:
            offset = 0

        # Is it a special search?
        redis_conn = self.request.redis_conn
        special_value = redis_conn.get("special_search:%s" % q)
        if special_value:
            self.template_name = "search/special.html"
            return {
                "q": q,
                "text": special_value,
            }

        # Get the results from Xapian
        db = xappy.SearchConnection(
            os.path.join(
                settings.SITE_ROOT,
                '..',
                "xappydb",
            ),
        )
        query = db.query_parse(
            q,
            default_op=db.OP_OR,
            deny = [ "mission" ],
        )
        # query=db.query_filter(
        #     query,
        #     db.query_field("mission", self.request.mission.name),
        # )
        results = db.search(
            query=query,
            startrank=offset,
            endrank=offset+PAGESIZE,
            checkatleast=offset+PAGESIZE+1,
        )
        # Go through the results, building a list of LogLine objects
        log_lines = []
        for result in results:
            transcript_name, timestamp = result.id.split(":", 1)
            log_line = LogLine(redis_conn, transcript_name, int(timestamp))
            log_line.speaker = Character(redis_conn, transcript_name.split('/')[0], result.data['speaker'][0])
            log_line.title = mark_safe(result.summarise("text", maxlen=50, ellipsis='&hellip;', strict_length=True, hl=None))
            log_line.summary = mark_safe(result.summarise("text", maxlen=600, ellipsis='&hellip;', hl=('<mark>', '</mark>')))
            log_lines.append(log_line)

        def page_url(offset):
            return reverse("search") + '?' + urllib.urlencode({
                'q': q,
                'offset': offset,
            })

        if offset==0:
            previous_page = False
        else:
            previous_page = page_url(offset - PAGESIZE)

        if offset+PAGESIZE > results.matches_estimated:
            next_page = False
        else:
            next_page = page_url(offset + PAGESIZE)

        thispage = offset / PAGESIZE
        maxpage = results.matches_estimated / PAGESIZE
        
        pages_to_show = set([0]) | set([thispage-1, thispage, thispage+1]) | set([maxpage])
        if 0 == thispage:
            pages_to_show.remove(thispage-1)
        if maxpage == thispage:
            pages_to_show.remove(thispage+1)
        pages = []
        
        class Page(object):
            def __init__(self, number, url, selected=False):
                self.number = number
                self.url = url
                self.selected = selected
        
        pages_in_order = list(pages_to_show)
        pages_in_order.sort()
        for page in pages_in_order:
            if len(pages)>0 and page != pages[-1].number:
                pages.append('...')
            pages.append(Page(page+1, page_url(page*PAGESIZE), page==thispage))
        
        return {
            'log_lines': log_lines,
            'result': results,
            'q': q,
            'previous_page': previous_page,
            'next_page': next_page,
            'pages': pages,
            'debug': {
                'query': query,
            },
        }

########NEW FILE########
__FILENAME__ = settings
from configs.settings import *

DEBUG = True
TEMPLATE_DEBUG = DEBUG
PROJECT_DOMAIN = "dev.spacelog.org:8000"

try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = settings
from configs.settings import *
# The following MUST be an absolute URL in live deploys (it's given out
# to other systems). Also, it doesn't get overridden in local_settings.py
# unlike the others.
FIXED_STATIC_URL = 'http://cdn.spacelog.org/assets/global/'

STATIC_URL = 'http://cdn.spacelog.org/assets/global/'
# I believe the next line to be true, although /assets/global/missions/ works too;
# this feels more correct.
MISSIONS_STATIC_URL = 'http://cdn.spacelog.org/assets/website/missions/'

# allow local overrides, probably built during deploy
try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = settings
# Django settings for website project.

import os
import django
import sys

# calculated paths for django and the site
# used as starting points for various other paths
DJANGO_ROOT = os.path.dirname(os.path.realpath(django.__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

sys.path.append(os.path.join(SITE_ROOT, 'apps'))

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

STATIC_ROOT = os.path.join(SITE_ROOT, 'static')
STATIC_URL  = '/assets/'
# FIXED_STATIC_URL doesn't change with varying deploys, so can be used for
# things that need long-term URLs, like image references in the Open Graph.
FIXED_STATIC_URL  = '/assets/'
MISSIONS_STATIC_ROOT = os.path.join(SITE_ROOT, '..', 'missions')
MISSIONS_STATIC_URL = '/assets/missions/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'hqp*)4r*a99h4@=7@5bpdn+ik8+x9c&=zk4o-=w1ap6n!9_@z1'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'homepage.middleware.HoldingMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "homepage.context.static",
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(SITE_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'homepage',
    'search',
    'website.apps.transcripts'
)

PROJECT_DOMAIN = "spacelog.org"

########NEW FILE########
__FILENAME__ = settings
from configs.settings import *
PROJECT_DOMAIN = "artemis.fort"

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import os
import sys

# where are we? eh?
project_path = os.path.realpath(os.path.dirname(__file__))

# we add them first in case we want to override anything already on the system
sys.path.insert(0, project_path)
sys.path.insert(0, os.path.join(project_path, '../'))

import ext

from django.core.management import execute_manager
args = sys.argv
# Let's figure out our environment
if os.environ.has_key('DJANGOENV'):
    environment = os.environ['DJANGOENV']
elif len(sys.argv) > 1:
    # this doesn't currently work
    environment = sys.argv[1]
    if os.path.isdir(os.path.join(project_path, 'configs', environment)):
        sys.argv = [sys.argv[0]] + sys.argv[2:]
    else:
        environment = None
else:
    environment = None
try:
    module = "configs.%s.settings" % environment
    __import__(module)
    settings = sys.modules[module]
    # worked, so add it into the path so we can import other things out of it
    sys.path.insert(0, os.path.join(project_path, 'configs', environment))
except ImportError:
    environment = None

# We haven't found anything helpful yet, so use development.
if environment == None:
    try:
        import configs.development.settings
        settings = configs.development.settings
        environment = 'development'
        sys.path.insert(0, os.path.join(project_path, 'configs', environment))
    except ImportError:
        sys.stderr.write("Error: Can't find the file 'settings.py'; looked in %s and development.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % (environment,))
        sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
#from search.views import SearchView

urlpatterns = patterns('',
    url(r'^$', 'homepage.views.homepage', name="homepage"),
    url(r'^about/$', 'homepage.views.about', name="about"),
    url(r'^press/$', 'homepage.views.press', name="press"),
    url(r'^get-involved/$', 'homepage.views.get_involved', name="get_involved"),
    # url(r'^search/$', SearchView.as_view(), name="search"),
)

if settings.DEBUG: # pragma: no cover
    urlpatterns += patterns('',
        (r'^' + settings.MISSIONS_STATIC_URL[1:] + '(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MISSIONS_STATIC_ROOT
        }),
        (r'^' + settings.STATIC_URL[1:] + '(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.STATIC_ROOT
        }),
        # (r'^' + settings.MEDIA_URL[1:] + '(?P<path>.*)$', 'django.views.static.serve', {
        #     'document_root': settings.MEDIA_ROOT
        # }),
    )


########NEW FILE########
__FILENAME__ = MCShred
#!/usr/bin/python

import sys
import re
from optparse import OptionParser

#MAX_FILE_NUMBER = 20
TIMESTAMP_PARTS = 4
SECONDS_OFFSET = 0

pageNumber = 1

errors = []
       
def get_file_name_for(num):
    return str(num).zfill(3) + ".txt"

def shred_to_lines(lines):
    global pageNumber
    logLines = []
    tapeNumber = None
        
    for number, line in enumerate(lines):
        line = line.decode('utf-8')
        try:
            if line.strip().startswith(u"Page"):
                pageNumber = int(line.strip().lstrip(u"Page ").strip())
            elif line.strip().startswith(u"Tape "):
                tapeNumber = line.lstrip(u"Tape ").strip()
            else:
                logLines.append(LogLine(pageNumber, tapeNumber, number, line))
        except:
            print "Failed on line %i: %s" % (number+1, line)
            raise

    return logLines

def get_all_raw_lines(path):
    translated_lines = []
    try:
        file = open(path, "r")
        file_lines = file.readlines()
        shredded_lines = shred_to_lines(file_lines)
        translated_lines.extend(shredded_lines)
    except IOError:
        errors.append("Could not find the file: " + path)
        
    return translated_lines    

def sterilize_token(token):
    bs0 = BadNumberSub(0, ["o","Q","O"])
    bs1 = BadNumberSub(1, ["i","J", "I","!","L","l"])
    bs4 = BadNumberSub(4, ["h"])
    bs8 = BadNumberSub(8, ["B"])
    
    tempToken = token
    
    for badSub in [ bs0, bs1, bs4, bs8 ]:
        for sub in badSub.badSubList:
            tempToken = tempToken.replace(sub, str(badSub.number))
    
    return tempToken

def get_seconds_from_mission_start(line):
    return translate_timestamp_to_seconds_from_mission_start(line.raw)

def translate_timestamp_to_seconds_from_mission_start(timestamp):
    values =  re.split("[ \t\:]+", timestamp);
    i = 0
    days = 0
    if TIMESTAMP_PARTS > 3:
        days = int(sterilize_token(values[i]))
        i += 1
    hours = int(sterilize_token(values[i]))
    i += 1
    minutes = int(sterilize_token(values[i]))
    i += 1
    seconds = int(sterilize_token(values[i]))
    
    return (seconds + (minutes * 60) + (hours * 60 * 60) + (days * 24 * 60 * 60)) - SECONDS_OFFSET

def set_timestamp_speaker_and_text(line):
    
    values =  re.split("[ \t\:]+", line.raw);
   
    line.set_seconds_from_mission_start(get_seconds_from_mission_start(line))
    
    if len(values) > TIMESTAMP_PARTS:
        line.set_speaker(values[TIMESTAMP_PARTS])
    else:
        line.set_speaker(u"_note")
        
    if len(values) > (TIMESTAMP_PARTS + 1):
        line.set_text(" ".join(values[TIMESTAMP_PARTS + 1:]))
    else:
        line.set_text(u"")

def line_is_a_new_entry(line):
    
    dateTokens = re.split('[ \t\:]+', line.raw)

    if len(dateTokens) < TIMESTAMP_PARTS:
        return False
    
    dateTokens = dateTokens[0:TIMESTAMP_PARTS]
    
    for token in dateTokens:
        try:
            int(token)
        except:
            return False

    if int(dateTokens[0]) > 20 or int(dateTokens[1]) > 23\
            or int(dateTokens[2]) > 59 or int(dateTokens[3]) > 59:
        return False

    return True

def is_a_non_log_line(line):
    if len(line.raw) == 0:
        return True

    return line.raw[0] == '\t' \
                or len(line.raw) != len(line.raw.lstrip()) \
                or not line.raw \
                or "(Music" in line.raw

def translate_lines(translated_lines, verbose=False):
    translatedLines = []
    currentLine = None

    for number, line in enumerate(translated_lines):
        if line_is_a_new_entry(line):
            if currentLine != None:
                translatedLines.append(currentLine)
            if verbose:
                print line.raw
            set_timestamp_speaker_and_text(line)
            currentLine = line
        elif currentLine != None:
            if line.raw.strip():
                if is_a_non_log_line(line):
                    currentLine.append_non_log_line(line.raw.strip())
                else:
                    currentLine.append_text(line.raw)
        else:
            errors.append("Line %i has no nominal timestamp: %s" % (number+1, line.raw))
    
    translatedLines.append(currentLine)
    
    return translatedLines          

def validate_line(line):
    try:
        line.seconds_from_mission_start
        line.page
        line.tape
        line.speaker
        line.text
    except:
        errors.append("Invalid line found at %s" % get_timestamp_as_mission_time(line))
        return False
    
    return True    


last_tape = None
last_page = None

def get_formatted_record_for(line):
    "Returns a correctly-formatted line."
    # These really shouldn't be globals, but I'm not ready to refactor
    # this all into a big class and use instance variables.
    global last_page, last_tape
    if validate_line(line):
        lines = []
        lines.append(u"\n[%s]\n" % get_timestamp_as_mission_time(line))
#        lines.append(u"\n[%d]\n" % line.seconds_from_mission_start)
        if line.page != last_page:
            lines.append(u"_page : %d\n" % line.page)
            last_page = line.page
        if line.tape != last_tape:
            lines.append(u"_tape : %s\n" % line.tape)
            last_tape = line.tape
        if len(line.non_log_lines) > 0:
            lines.append(u"_extra : %s\n" % "/n".join(line.non_log_lines))
        lines.append(u"%s: %s" % (line.speaker, line.text,))
        return lines
    else:
        return []
    


def check_lines_are_in_sequence(lines):
    currentTime = -20000000
    for line in lines:
        if line.seconds_from_mission_start < currentTime:
            errors.append("Line out of Sync error at %s" % get_timestamp_as_mission_time(line))
        currentTime = line.seconds_from_mission_start

def report_errors_and_exit():
    if len(errors) > 0:
        print "Shred returned errors, please check the following:"
        for error in errors:
            print error
        sys.exit(1)
    
    print "No errors found"    
    sys.exit(0)

def output_lines_to_file(lines, output_file_name_and_path):
    outputFile = open(output_file_name_and_path, "w")
    for i, line in enumerate(lines):
        try:
            outputFile.writelines(
                map(
                    lambda x: x.encode('utf8'),
                    get_formatted_record_for(line),
                )
            )
        except:
            print >>sys.stderr, "Failure in line %i (raw line %i)" % (i, line.line)
            raise
    outputFile.close()

def amalgamate_lines_by_timestamp(lines):
    amalgamated_lines = []
    last_line = lines[0]
    for line in lines[1:]:
        if last_line.seconds_from_mission_start == line.seconds_from_mission_start:
            last_line.append_second_line_content(line)
        else:
            amalgamated_lines.append(last_line)
            last_line = line
    amalgamated_lines.append(last_line)

    return amalgamated_lines

def get_timestamp_as_mission_time(line):
    sec = line.seconds_from_mission_start
    days = sec // 86400
    hours = (sec // 3600) % 24
    minutes = (sec // 60) % 60
    seconds = sec % 60
    
    return "%02d:%02d:%02d:%02d" % (days, hours, minutes, seconds)

class LogLine:
    def __init__(self, pageNumber, tapeNumber, lineNumber, rawLine):
        self.raw = rawLine
        self.page = pageNumber
        self.tape = tapeNumber
        self.line = lineNumber
        self.speaker = ""
        self.non_log_lines = []

    def get_raw_line(self):
        return self.raw
    
    def set_text(self, text):
        self.text = text
    
    def append_text(self, text):
        self.text = self.text + (" " * 5) + text
        
    def append_second_line_content(self, line):
        self.text = self.text + "\n%s: %s" % (line.speaker, line.text)
        
    def set_seconds_from_mission_start(self, seconds_from_mission_start):
        self.seconds_from_mission_start = seconds_from_mission_start
    
    def set_speaker(self, speaker):
        self.speaker = speaker
        
    def append_non_log_line(self, line):
        self.non_log_lines.append(line)

class BadNumberSub:
    def __init__(self, number, badSubList):
        self.number = number
        self.badSubList = badSubList

if __name__ == "__main__":
    usage = "usage: %prog [options] input_file output_file\n" + "eg: %prog missions/a18/TEC.txt missions/a18/transcripts/TEC"
    
    parser = OptionParser(usage=usage)
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False, help="print out parsed lines")
    (options, args) = parser.parse_args()
    
    if len(args)!=2:
        parser.print_help()
        sys.exit(0)
    
    file_path = args[0]
    output_file = args[1]
    allRawLines = get_all_raw_lines(file_path)
    print "Read in %d raw lines (%d non-blank)." % (len(allRawLines), len(filter(lambda x: x.raw.strip(), allRawLines)))
    translated_lines = translate_lines(allRawLines, options.verbose)
    print "Translated to %d lines." % len(translated_lines)
    check_lines_are_in_sequence(translated_lines)
    
    amalgamated_lines = amalgamate_lines_by_timestamp(translated_lines)
    
    output_lines_to_file(amalgamated_lines, output_file)
        
    report_errors_and_exit()

########NEW FILE########
__FILENAME__ = MCShredTest
#!/usr/bin/python
import unittest
import MCShred


class Test(unittest.TestCase):

    def setUp(self):
        pass


    def tearDown(self):
        pass
    
    def test_sterilize_token(self):
        assert int(MCShred.sterilize_token("00")) == 0
        assert int(MCShred.sterilize_token("01")) == 1
        assert int(MCShred.sterilize_token("l0")) == 10
        assert int(MCShred.sterilize_token("BB")) == 88
        assert int(MCShred.sterilize_token("Bh")) == 84
        assert int(MCShred.sterilize_token("lo")) == 10
        assert int(MCShred.sterilize_token("OQo")) == 0
        assert int(MCShred.sterilize_token("iJI!Ll")) == 111111
        assert int(MCShred.sterilize_token("B")) == 8
        assert int(MCShred.sterilize_token("h")) == 4
        
        assert int(MCShred.sterilize_token(u"00")) == 0
        assert int(MCShred.sterilize_token(u"01")) == 1
        assert int(MCShred.sterilize_token(u"l0")) == 10
        assert int(MCShred.sterilize_token(u"BB")) == 88
        assert int(MCShred.sterilize_token(u"Bh")) == 84
        assert int(MCShred.sterilize_token(u"lo")) == 10
        assert int(MCShred.sterilize_token(u"OQo")) == 0
        assert int(MCShred.sterilize_token(u"iJI!Ll")) == 111111
        assert int(MCShred.sterilize_token(u"B")) == 8
        assert int(MCShred.sterilize_token(u"h")) == 4
    
    def test_log_line(self):
        logLine = MCShred.LogLine(5, u"5/1", u"00 01 03 59 CC This is the rest of the line")
        
        assert logLine.page == 5
        assert logLine.tape == u"5/1"
        assert logLine.raw == u"00 01 03 59 CC This is the rest of the line"
        
    def test_get_seconds_from_mission_start(self):
        logLine = MCShred.LogLine(5, u"5/1", u"01 02 03 59 CC This is the rest of the line")
        expectedTime = (59 + (3 * 60) + (2 * 60 * 60) + (1 * 24 * 60 * 60))
        
        
#        print('expected time %d' % expectedTime)
#        print('got time of %d' % MCShred.get_seconds_from_mission_start(logLine))
        assert MCShred.get_seconds_from_mission_start(logLine) == expectedTime
        
    def test_get_seconds_from_mission_start_will_work_with_full_colon_seperated_timestamps(self):
        logLine = MCShred.LogLine(5, u"5/1", u"01:02:03:59 CC This is the rest of the line")
        expectedTime = (59 + (3 * 60) + (2 * 60 * 60) + (1 * 24 * 60 * 60))
        
        
#        print('expected time %d' % expectedTime)
#        print('got time of %d' % MCShred.get_seconds_from_mission_start(logLine))
        assert MCShred.get_seconds_from_mission_start(logLine) == expectedTime
        
    def test_set_timestamp_speaker_and_text(self):
        logLine = MCShred.LogLine(5, u"5/1", u"01 02 03 59 CC This is the rest of the line")
        
        MCShred.set_timestamp_speaker_and_text(logLine)
        
        expectedTime = (59 + (3 * 60) + (2 * 60 * 60) + (1 * 24 * 60 * 60))
        
#        print(expectedTime)
#        print(logLine.seconds_from_mission_start)
        
        assert logLine.seconds_from_mission_start == expectedTime
        assert logLine.speaker == u"CC"
        assert logLine.text == "This is the rest of the line"
        
    def test_line_is_a_new_entry(self):
        logLine1 = MCShred.LogLine(5, u"5/1", u"01 02 03 59 CC This is the rest of the line")
        logLine2 = MCShred.LogLine(5, u"5/1", u"except for this thing because it's actually")
        logLine3 = MCShred.LogLine(5, u"5/1", u"a three line comment")
        
        assert MCShred.line_is_a_new_entry(logLine1) == True
        assert MCShred.line_is_a_new_entry(logLine2) == False
        assert MCShred.line_is_a_new_entry(logLine3) == False
        
    def test_shred_to_lines(self):
        logLine0 = u"Tape 3/2"
        logLine1 = u"01 02 03 59 CC This is the rest of the line"
        logLine2 = u"except for this thing because it's actually"
        logLine3 = u"a three line comment"
        
        logLines = (logLine0, logLine1, logLine2, logLine3,)
        
        shreddedLines = MCShred.shred_to_lines(logLines)
        
        assert len(shreddedLines) == 3
        assert shreddedLines[0].page == 1
        assert shreddedLines[1].page == 1
        assert shreddedLines[2].page == 1
        assert shreddedLines[0].tape == u"3/2"
        assert shreddedLines[1].tape == u"3/2"
        assert shreddedLines[2].tape == u"3/2"
        assert shreddedLines[0].raw == logLine1
        assert shreddedLines[1].raw == logLine2
        assert shreddedLines[2].raw == logLine3
        
    def test_translate_lines(self):
        logLine0 = u"Tape 3/2"
        logLine1 = u"01 02 03 59 CC This is the rest of the line"
        logLine2 = u"except for this thing because it's actually"
        logLine3 = u"a three line comment"
        
        logLines = (logLine0, logLine1, logLine2, logLine3,)
        
        shreddedLines = MCShred.shred_to_lines(logLines)
        
        translatedLines = MCShred.translate_lines(shreddedLines)
        
        print(translatedLines[0].text)
        
        assert len(translatedLines) == 1
        assert translatedLines[0].page == 1
        assert translatedLines[0].tape == u"3/2"
        assert translatedLines[0].speaker == u"CC"
        assert translatedLines[0].text == u"This is the rest of the line" + "     " + logLine2 + "     " + logLine3

    def test_get_filename_for(self):
        assert MCShred.get_file_name_for(0) == u"000.txt"
        assert MCShred.get_file_name_for(1) == u"001.txt"
        assert MCShred.get_file_name_for(12) == u"012.txt"
        assert MCShred.get_file_name_for(304) == u"304.txt"
        assert MCShred.get_file_name_for(200) == u"200.txt"
        assert MCShred.get_file_name_for(003) == u"003.txt"
        
    def test_is_a_non_log_line(self):
        logLine0 = make_log_line(u"Tape 3/2")
        logLine1 = make_log_line(u"01 02 03 59 CC This is the rest of the line")
        logLine2 = make_log_line(u"  except for this thing because it's actually")
        logLine3 = make_log_line(u"    ( other weird text Thing )")
        logLine4 = make_log_line(u"")
        assert MCShred.is_a_non_log_line(logLine0) == False
        assert MCShred.is_a_non_log_line(logLine1) == False
        assert MCShred.is_a_non_log_line(logLine2) == True
        assert MCShred.is_a_non_log_line(logLine3) == True
        assert MCShred.is_a_non_log_line(logLine4) == True
        
    def test_if_no_speaker_indicated_it_is_considered_a_note(self):
        logLine = MCShred.LogLine(5, u"5/1", u"01 02 03 59")
        
        MCShred.set_timestamp_speaker_and_text(logLine)
        
        expectedTime = (59 + (3 * 60) + (2 * 60 * 60) + (1 * 24 * 60 * 60))
        
#        print(expectedTime)
#        print(logLine.seconds_from_mission_start)
        
        assert logLine.seconds_from_mission_start == expectedTime
        assert logLine.speaker == u"_note"
        assert logLine.text == ""
        

def make_log_line(content):
    return MCShred.LogLine(0, 0, content)        
            
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()

########NEW FILE########
__FILENAME__ = offset_trancript_pages
#!/usr/bin/env python

import os, sys

if len(sys.argv) < 3:
    print >>sys.stderr, "Usage: python offset_transcript_pages.py [transcript file] [offset]"
    print >>sys.stderr
    print >>sys.stderr, "Mass-modifies transcript page numbers by a specified offset."
    sys.exit(1)

transcript_file = sys.argv[1]
offset          = int( sys.argv[2] )

os.rename( transcript_file, transcript_file+"~" )
source      = open( transcript_file+"~", "r" )
destination = open( transcript_file, "w" )

for line in source:
    fixed_line = line
    if line.startswith( '_page' ):
        page = int( line.strip( '_page: ' ) )
        page += offset
        fixed_line = "_page : %d\n" % page
    
    destination.write( fixed_line )

source.close()
destination.close()
########NEW FILE########
__FILENAME__ = pdf_to_images
#!/usr/bin/env python
import os
import subprocess
import sys
import tempfile

ORIGINALS_WIDTH = 770
ABOUT_PAGE      = 1
ABOUT_WIDTH     = 270

requires = {
    'ImageMagick': 'convert',
    'OptiPNG'    : 'optipng',
}

unmet_requirements = []
for name, command in requires.iteritems():
    tf = tempfile.TemporaryFile()
    try:
        subprocess.call( command, stdin=None, stdout=tf, stderr=tf )
    except OSError:
        unmet_requirements += [ '%s (%s)' % ( name, command ) ]

if unmet_requirements:
    print >>sys.stderr, 'Unmet requirements: %s' % ', '.join( unmet_requirements )
    sys.exit(1)

if len(sys.argv) < 2:
    print >>sys.stderr, "Usage: python pdf_to_images.py [pdf file]"
    print >>sys.stderr
    print >>sys.stderr, "Converts a PDF into a directory full of PNGs. Requires ImageMagick and optipng."
    sys.exit(1)

pdf_file = sys.argv[1]
output_dir = '%s_images' % pdf_file
os.mkdir(output_dir)

page = 1

def generate_image( image_name, page, resize_dimensions=None ):
    png_file = os.path.join(output_dir, '%s.png' % image_name)
    
    # Convert and resize in two passes to get the smallest filesize
    print "Converting page %s to %s..." % ( page, png_file )
    exit_code = subprocess.call([
        'convert', 
        '-density', '300', 
        u'%s[%s]' % (pdf_file, page-1), # zero indexed pages
        png_file,
    ])
    
    if not exit_code:
        print "Resizing %s..." % png_file
        # HACK: Assumes that the input image is black and white,
        #       and 16 colors will suffice for antialiasing
        exit_code = subprocess.call([
            'convert', 
            '-colorspace', 'Gray',
            '-resize', resize_dimensions,
            '-colors', '16',
            png_file,
            png_file,
        ])
        
    if not exit_code:
        # This usually takes many times longer than the extract
        print "Optimising %s..." % png_file
        optimise_exit_code = subprocess.call([
            'optipng',
            '-q',
            '-o7',
            png_file,
        ])
        if optimise_exit_code != 0:
            print >>sys.stderr, "optipng failed"
            sys.exit(1)
    
    return exit_code


while True:
    if page == ABOUT_PAGE:
        exit_code = generate_image( 'about', page, '%i' % ABOUT_WIDTH )
        if exit_code != 0:
            break
    
    exit_code = generate_image( '%i' % page, page, '%i' % ORIGINALS_WIDTH )
    if exit_code != 0:
        break
    
    page += 1



########NEW FILE########
__FILENAME__ = resize
from PIL import Image
import os

crop_width = 600
crop_height = 100

sizes = [
    (0.5, 220),
    (1, 380),
    (999, 540),
]

for filename in os.listdir("."):
    if filename.endswith(".jpg") and not filename.endswith("-thumb.jpg"):
        basename = filename[:-4]
        thumbname = "%s-thumb.jpg" % basename
        if os.path.exists(thumbname):
            pass
            #continue
        print "Converting %s" % filename
        # Step one: big version
        source = Image.open(filename)
        thumbnail = source.copy()
        thumbnail.thumbnail((1024, 1024))
        thumbnail.save(filename)
        # Step two: in page version
        slice = source.copy()
        w, h = slice.size
        ratio = w / float(h)
        for max_ratio, width in sizes:
            if ratio <= max_ratio:
                break
        else:
            width = sizes[-1][1]
        slice.thumbnail((width, 10000))
        slice.save(thumbname)


########NEW FILE########
__FILENAME__ = s3-upload
#!/usr/bin/env python
# You'll need to set the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
# environment variables to make this work.
# (or ask Russ)

import boto
from boto.s3.key import Key
import os
import sys

BUCKET = 'spacelog'
TTL = 86400*7

if len(sys.argv) != 3:
    print "Usage s3-upload.py <directory> <upload path>"
    sys.exit(1)

conn = boto.connect_s3()
bucket = conn.get_bucket(BUCKET)

remote_files = set([key.name.split('/')[-1] for key in bucket.list(sys.argv[2])])

files = os.listdir(sys.argv[1])

for file in files:
    if file not in remote_files:
        print "Uploading", file
        k = Key(bucket, '%s/%s' % (sys.argv[2], file))
        k.set_contents_from_filename("%s/%s" % (sys.argv[1], file),
                headers={'Cache-Control': 'max-age=%s' % TTL})
        k.set_acl('public-read')

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = template
from django.template import Template
from django.template.loader_tags import BlockNode
from django.utils import simplejson

class JsonTemplate(Template):
    def _render(self, context):
        output = {}
        for n in self.nodelist.get_nodes_by_type(BlockNode):
            output[n.name] = n.render(context)
        return simplejson.dumps(output)




########NEW FILE########
__FILENAME__ = nbspify
from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()

@stringfilter
@register.filter
def nbspify(value):
    return mark_safe('&nbsp;'.join(conditional_escape(s) for s in value.split(' ')))


########NEW FILE########
__FILENAME__ = test_template
from django import template
import simplejson
import unittest
from website.apps.common.template import JsonTemplate

class TestJsonTemplate(unittest.TestCase):
    def test_blocks(self):
        output = JsonTemplate("""
{% extends "blah blah" %}
{% block title %}Title!{% endblock%}
{% block content %}Blah blah content{% endblock %}
""").render(template.Context())

        self.assertEqual(
            simplejson.loads(output),
            {
                'title': 'Title!',
                'content': 'Blah blah content',
            }
        )



########NEW FILE########
__FILENAME__ = views
from django.template import loader, TemplateDoesNotExist
from django.utils import simplejson
from django.views.generic import TemplateView
from website.apps.common.template import JsonTemplate


class JsonTemplateView(TemplateView):
    """
    A template view that outputs templates as JSON for ajax requests.
    """
    def load_template(self, names):
        if 'json' not in self.request.GET:
            return super(JsonTemplateView, self).load_template(names)
        
        for name in names:
            try:
                template, origin = loader.find_template(name)
            except TemplateDoesNotExist:
                continue
            if not hasattr(template, 'render'):
                return JsonTemplate(template, origin, name)
            else:
                # do some monkey business if the template has already been
                # compiled
                new_template = JsonTemplate('', origin, name)
                new_template.nodelist = template.nodelist
                return new_template
        raise TemplateDoesNotExist(', '.join(names))

    def get_response(self, content, **httpresponse_kwargs):
        if 'json' in self.request.GET and 'mimetype' not in httpresponse_kwargs:
            httpresponse_kwargs['mimetype'] = 'application/json'
        return super(JsonTemplateView, self).get_response(content, **httpresponse_kwargs)
            


class JsonMixin(object):
    def render_to_response(self, context=None):
        return self.get_response(simplejson.dumps(context), mimetype='application/json')


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext
from backend.api import Glossary


def glossary(request):
    terms = sorted(
        list(
            Glossary.Query(request.redis_conn, request.mission.name).items()
        ),
        key=lambda term: term.abbr,
    )
    
    return render_to_response(
        'glossary/glossary.html',
        {
            'terms': terms,
        },
        context_instance = RequestContext(request),
    )

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = views
from django.template.loader import render_to_string
from django.template import RequestContext
from django.views.generic import TemplateView
from backend.util import timestamp_to_seconds
from backend.api import LogLine, Act
from website.apps.common.views import JsonMixin

class HomepageView(TemplateView):
    template_name = 'homepage/homepage.html'
    def get_quote(self):
        quote_timestamp = self.request.redis_conn.srandmember(
            "mission:%s:homepage_quotes" % self.request.mission.name,
        )
        if quote_timestamp:
            if '/' in quote_timestamp:
                transcript, timestamp = quote_timestamp.rsplit('/', 1)
                transcript = "%s/%s" % (self.request.mission.name, transcript)
            else:
                transcript = self.request.mission.main_transcript
                timestamp = quote_timestamp
            return LogLine(
                self.request.redis_conn,
                transcript,
                int(timestamp_to_seconds(timestamp)),
            )

    def get_context_data(self):
        acts = [
            (x+1, act)
            for x, act in
            enumerate(Act.Query(self.request.redis_conn, self.request.mission.name))
        ]
        return {
            "acts": acts,
            "quote": self.get_quote(),
        }

class HomepageQuoteView(JsonMixin, HomepageView):
    def get_context_data(self):
        return {
            'quote': render_to_string(
                'homepage/_quote.html',
                { 'quote': self.get_quote() },
                RequestContext(self.request),
            )
        }

        
class AboutView(TemplateView):
    template_name = 'homepage/about.html'

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = views
from django.http import Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from backend.api import Character

def people(request, role=None):
    
    character_query = Character.Query(request.redis_conn, request.mission.name)
    character_ordering = list(request.redis_conn.lrange("character-ordering:%s" % request.mission.name, 0, -1))
    sort_characters = lambda l: sorted(
        list(l),
        key=lambda x: character_ordering.index(x.identifier) if x.identifier in character_ordering else 100
    )

    if role:
        people = [
            {
                'name': role,
                'members': sort_characters(character_query.role(role)),
            }
        ]
        more_people = False
    else:
        all_people = sort_characters(character_query)
        astronauts = list(character_query.role('astronaut'))
        ops = sort_characters(character_query.role('mission-ops-title'))
        people = [
            {
                'name': 'Flight Crew',
                'members': astronauts,
                'view': 'full'
            },
            {
                'name': 'Mission Control',
                'members': ops,
                'view': 'simple'
            }
        ]
        more_people = len(list(character_query.role('mission-ops')))
    
    # 404 if we have no content
    if 1 == len(people) and 0 == len(people[0]['members']):
        raise Http404( "No people were found" )
    return render_to_response(
        'people/people.html',
        {
            'role':   role,
            'people': people,
            'more_people': more_people,
        },
        context_instance = RequestContext(request),
    )

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = xappy
from django.template import Library
from django.utils.safestring import mark_safe

register = Library()

@register.filter
def summarise(result, field):
    return mark_safe(result.summarise(field, maxlen=100, ellipsis='&hellip;', hl=('<em>', '</em>')))

########NEW FILE########
__FILENAME__ = views
import os
import urllib
from django.views.generic import TemplateView
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.safestring import mark_safe
import xappy
import xapian
import redis
from backend.api import LogLine, Character
from backend.util import timestamp_to_seconds

PAGESIZE = 20

class SearchView(TemplateView):

    template_name = 'search/results.html'

    def get_context_data(self):
        # Get the query text
        q = self.request.GET.get('q', '')
        # Get the offset value
        try:
            offset = int(
                self.request.GET.get('offset', '0')
            )
            if offset < 0:
                offset = 0
        except ValueError:
            offset = 0

        # Is it a special search?
        special_value = self.request.redis_conn.get("special_search:%s:%s" % (
            self.request.mission.name,
            q,
        ))
        if special_value:
            self.template_name = "search/special.html"
            return {
                "q": q,
                "text": special_value,
            }

        # Get the results from Xapian
        db = xappy.SearchConnection(
            os.path.join(
                settings.SITE_ROOT,
                '..',
                "xappydb",
            ),
        )
        db.set_weighting_scheme(
            xapian.BM25Weight(
                1, # k1
                0, # k2
                1, # k4
                0.5, # b
                2, # min_normlen
            )
        )
        query = db.query_parse(
            q,
            default_op=db.OP_OR,
            deny = [ "mission" ],
        )
        query=db.query_filter(
            query,
            db.query_composite(db.OP_AND, [
                db.query_field("mission", self.request.mission.name),
                db.query_field("transcript", self.request.mission.main_transcript),
            ])
        )
        results = db.search(
            query=query,
            startrank=offset,
            endrank=offset+PAGESIZE,
            checkatleast=-1, # everything (entire xapian db fits in memory, so this should be fine)
            sortby="-weight",
        )
        # Go through the results, building a list of LogLine objects
        redis_conn = self.request.redis_conn
        log_lines = []
        for result in results:
            transcript_name, timestamp = result.id.split(":", 1)
            log_line = LogLine(redis_conn, transcript_name, int(timestamp))
            log_line.speaker = Character(redis_conn, transcript_name.split('/')[0], result.data['speaker_identifier'][0])
            log_line.title = mark_safe(result.summarise("text", maxlen=50, ellipsis='&hellip;', strict_length=True, hl=None))
            log_line.summary = mark_safe(result.summarise("text", maxlen=600, ellipsis='&hellip;', hl=('<mark>', '</mark>')))
            log_lines.append(log_line)

        def page_url(offset):
            return reverse("search") + '?' + urllib.urlencode({
                'q': q.encode('utf-8'),
                'offset': offset,
            })

        if offset==0:
            previous_page = False
        else:
            previous_page = page_url(offset - PAGESIZE)

        if offset+PAGESIZE > results.matches_estimated:
            next_page = False
        else:
            next_page = page_url(offset + PAGESIZE)

        thispage = offset / PAGESIZE
        maxpage = results.matches_estimated / PAGESIZE
        
        pages_to_show = set([0]) | set([thispage-1, thispage, thispage+1]) | set([maxpage])
        if 0 == thispage:
            pages_to_show.remove(thispage-1)
        if maxpage == thispage:
            pages_to_show.remove(thispage+1)
        pages = []
        
        class Page(object):
            def __init__(self, number, url, selected=False):
                self.number = number
                self.url = url
                self.selected = selected
        
        pages_in_order = list(pages_to_show)
        pages_in_order.sort()
        for page in pages_in_order:
            if len(pages)>0 and page != pages[-1].number:
                pages.append('...')
            pages.append(Page(page+1, page_url(page*PAGESIZE), page==thispage))
        
        error_info = self.request.redis_conn.hgetall(
            "error_page:%s:%s" % (
                self.request.mission.name,
                'no_search_results',
            ),
        )
        if not error_info:
            error_info = {}
        if error_info.has_key('classic_moment_quote'):
            error_quote = LogLine(
                self.request.redis_conn,
                self.request.mission.main_transcript,
                timestamp_to_seconds(error_info['classic_moment_quote'])
            )
        else:
            error_quote = None
        
        return {
            'log_lines': log_lines,
            'result': results,
            'q': q,
            'previous_page': previous_page,
            'next_page': next_page,
            'pages': pages,
            'debug': {
                'query': query,
            },
            'error': {
                'info': error_info,
                'quote': error_quote,
            }
        }

########NEW FILE########
__FILENAME__ = context
from django.conf import settings

def mission(request):
    return {
        "mission": getattr(request, 'mission', None),
        "PROJECT_HOME": settings.PROJECT_HOME,
        "MISSION_URL": "http://%s%s" % (
            request.META['HTTP_HOST'],
            # "apollo13.spacelog.org",
            '/',
        ),
    }

def static(request):
    return {
        "STATIC_URL": settings.STATIC_URL,
        "FIXED_MISSIONS_STATIC_URL": settings.FIXED_MISSIONS_STATIC_URL,
        "MISSIONS_STATIC_URL": settings.MISSIONS_STATIC_URL,
        "MISSIONS_IMAGE_URL": settings.MISSIONS_IMAGE_URL,
    }

########NEW FILE########
__FILENAME__ = middleware
import redis
from django.shortcuts import render_to_response
from django.template import RequestContext
from backend.api import Mission
from transcripts.templatetags.missiontime import component_suppression

class MissionMiddleware(object):
    """
    Adds a mission and redis object into every request.
    """
    def process_request(self, request):
        request.redis_conn = redis.Redis()
        # Get the current database
        request.redis_conn.select(int(request.redis_conn.get("live_database") or 0))
        # Get the mission subdomain
        subdomain = request.META['HTTP_HOST'].split(".")[0]
        if not request.holding:
            mission_name = request.redis_conn.get("subdomain:%s" % subdomain) or "a13"
            request.mission = Mission(request.redis_conn, mission_name)
            if request.mission.copy.get('component_suppression', None):
                component_suppression.leading = request.mission.copy['component_suppression'].get('leading', None)                
                component_suppression.trailing = request.mission.copy['component_suppression'].get('trailing', None)
            else:
                component_suppression.leading = None
                component_suppression.trailing = None

class HoldingMiddleware(object):
    """
    Shows a holding page if we're in the middle of an upgrade.
    """
    def process_request(self, request):
        redis_conn = redis.Redis()
        # Get the current database
        redis_conn.select(int(redis_conn.get("live_database") or 0))
        if redis_conn.get("hold"):
            if request.path.startswith("/assets"):
                request.holding = True
            else:
                response = render_to_response(
                    "holding.html",
                    {},
                    RequestContext(request),
                )
                response.status_code = 503
                return response
        else:
            request.holding = False


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = characters
from django.template import Library
from django.core.urlresolvers import reverse
from django.conf import settings

register = Library()

@register.simple_tag
def avatar_and_name(speaker, mission_name, timestamp=None):

    if timestamp is not None:
        current_speaker = speaker.current_shift(timestamp)
    else:
        current_speaker = speaker
    
    short_name_lang = ''
    if current_speaker.short_name_lang:
        short_name_lang = " lang='%s'"  % current_speaker.short_name_lang 
    
    detail = """
      <img src='%(MISSIONS_STATIC_URL)s%(mission_name)s/images/avatars/%(avatar)s' alt='' width='48' height='48'>
      <span%(short_name_lang)s>%(short_name)s</span>
    """ % {
        "avatar": current_speaker.avatar,
        "short_name": current_speaker.short_name,
        "short_name_lang": short_name_lang,
        "mission_name": mission_name,
        "MISSIONS_STATIC_URL": settings.MISSIONS_STATIC_URL,
    }

    url = None
    if current_speaker.role == 'mission-ops':
        url = '%s#%s' % (reverse("people", kwargs={"role": current_speaker.role}), current_speaker.slug)
    elif current_speaker.role == 'astronaut' or current_speaker.role == 'mission-ops-title':
        url = '%s#%s' % (reverse("people"), current_speaker.slug)

    if url:
        return "<a href='%s'>%s</a>" % (url, detail)
    else:
        return detail

@register.simple_tag
def avatar(speaker, mission_name, timestamp=None):

    if timestamp is not None:
        current_speaker = speaker.current_shift(timestamp)
    else:
        current_speaker = speaker

    short_name_lang = ''
    if current_speaker.short_name_lang:
        short_name_lang = " lang='%s'"  % current_speaker.short_name_lang 
    detail = """
      <img src='%(MISSIONS_STATIC_URL)s%(mission_name)s/images/avatars/%(avatar)s' alt='' width='48' height='48' %(short_name_lang)salt='%(short_name)s'>
    """ % {
        "avatar": current_speaker.avatar,
        "short_name": current_speaker.short_name,
        "short_name_lang": short_name_lang,
        "mission_name": mission_name,
        "MISSIONS_STATIC_URL": settings.MISSIONS_STATIC_URL,
    }

    url = None
    if current_speaker.role == 'mission-ops':
        url = '%s#%s' % (reverse("people", kwargs={"role": current_speaker.role}), current_speaker.slug)
    elif current_speaker.role == 'astronaut' or current_speaker.role == 'mission-ops-title':
        url = '%s#%s' % (reverse("people"), current_speaker.slug)

    if url:
        return "<a href='%s'>%s</a>" % (url, detail)
    else:
        return detail

########NEW FILE########
__FILENAME__ = linkify
import re
from django.template import Library
from django.template.defaultfilters import slugify
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from backend.api import Glossary
from backend.util import timestamp_to_seconds
from transcripts.templatetags.missiontime import timestamp_to_url

from templatetag_sugar.register import tag
from templatetag_sugar.parser import Variable, Optional

register = Library()

@tag(register, [Variable(), Variable()])
def original_link(context, transcript, page):
    url_args = {
        'page': page,
    }
    if transcript != context['request'].mission.main_transcript:
        # Split transcript name from [mission]/[transcript]
        url_args["transcript"] = transcript.split('/')[1]
    
    return reverse("original", kwargs=url_args)


def glossary_link(match, request):
    # Try to look up the definition
    gitem = None
    if request:
        try:
            gitem = Glossary(request.redis_conn, request.mission.name, match.group(1))
        except ValueError:
            title = ""
            more_information = True
        else:
            title = gitem.description
            more_information = bool(gitem.extended_description)
            tag = 'abbr' if gitem.type == 'abbreviation' else 'i'
    else:
        title = ""
        more_information = True

    try:
        # full syntax [glossary:term|display]
        display = match.group(2)
    except IndexError:
        # abbreviated syntax [glossary:term]
        display = match.group(1)

    if title:
        display = u"<%(tag)s class='jargon' title='%(title)s'>%(text)s</%(tag)s>" % {
            "tag":   tag,
            "title": title,
            "text":  display,
        }

    if more_information:
        if gitem is not None:
            return u"<a href='%s#%s'>%s</a>" % (
                reverse("glossary"),
                gitem.slug,
                display,
            )
        else:
            return u"<a href='%s#%s'>%s</a>" % (
                reverse("glossary"),
                slugify(match.group(1)),
                display,
            )
    else:
        return display

def time_link(match):
    try:
        # full syntax [time:time|display]
        return "<a href='%s'>%s</a>" % (
            timestamp_to_url({}, match.group(1), anchor="closest"),
            match.group(2)
        )
    except:
        # abbreviated syntax [time:time]
        return "<a href='%s'>%s</a>" % (
            timestamp_to_url({}, match.group(1), anchor="closest"),
            match.group(1)
        )

@register.filter
def linkify(text, request=None):
    # Typographize double quotes
    text = re.sub(r'"([^"]+)"', r'&ldquo;\1&rdquo;', text)
    text = text.replace('...', '&hellip;')
    
    link_types = {
        'time': time_link,
        'glossary': lambda m: glossary_link(m, request),
    }
    
    for link_type, link_maker in link_types.items():
        # first, the "full" version
        text = re.sub(
            r"\[%s:([^]]+)\|([^]]+)\]" % link_type,
            link_maker,
            text,
        )
        # Then the abbreviated syntax
        text = re.sub(
            r"\[%s:([^]]+)\]" % link_type,
            link_maker,
            text,
        )

    # Dashing through the text, with a one-space open sleigh
    text = text.replace("- -", "&mdash;").replace(" - ", "&mdash;").replace("--", "&mdash;")
    return mark_safe(text)

########NEW FILE########
__FILENAME__ = missiontime
from django.template import Library
from django.core.urlresolvers import reverse
from backend.util import timestamp_to_seconds

from templatetag_sugar.register import tag
from templatetag_sugar.parser import Variable, Optional


import threading

register = Library()

component_suppression = threading.local()
component_suppression.leading = None
component_suppression.trailing = None # must be negative to trim!

def timestamp_components(seconds, enable_suppression=False):
    # FIXME: this is almost identical to backend.util.seconds_to_timestamp, so
    # refactor
    "Takes a timestamp in seconds and returns a tuple of days, hours, minutes and seconds"
    # FIXME: really nasty thread-local to suppress different ends
    days = seconds // 86400
    hours = seconds % 86400 // 3600
    minutes = seconds % 3600 // 60
    seconds = seconds % 60
    if enable_suppression:
        return (days, hours, minutes, seconds)[component_suppression.leading:component_suppression.trailing]
    else:
        return (days, hours, minutes, seconds)

def mission_time(seconds, separator=':', enable_suppression=False):
    """
    Takes a timestamp and a separator and returns a mission time string
    e.g. Passing in 63 seconds and ':' would return '00:00:01:03'.
    """
    if isinstance(seconds, basestring) and separator in seconds:
        return seconds
    mission_time = separator.join([ '%02d' % x for x in timestamp_components(abs(seconds), enable_suppression) ])
    if seconds < 0:
        mission_time = '-%s' % mission_time
    return mission_time

@register.filter
def mission_time_format(seconds):
    return mission_time(seconds, ' ', True)

@tag(register, [Variable(), Optional([Variable()])])
def timestamp_to_url(context, seconds, anchor=None):
    transcript = None
    if 'transcript_name' in context:
        transcript = context['transcript_name']
    return timestamp_to_url_in_transcript(context, seconds, transcript, anchor)

@tag(register, [Variable(), Variable(), Optional([Variable()])])
def timestamp_to_url_in_transcript(context, seconds, transcript, anchor=None):
    url_args = {
        "start": mission_time(seconds)
    }
    if transcript and transcript != context['request'].mission.main_transcript:
        # Split transcript name from [mission]/[transcript]
        url_args["transcript"] = transcript.split('/')[1]
    
    # Render the URL
    url = reverse("view_page", kwargs=url_args)
    if anchor:
        url = '%s#log-line-%s' % (url, anchor)
    return url
    

@tag(register, [Variable(), Optional([Variable()])])
def selection_url(context, start_seconds, end_seconds=None):
    transcript = None
    if 'transcript_name' in context:
        transcript = context['transcript_name']
    return selection_url_in_transcript(context, start_seconds, transcript, end_seconds)

@tag(register, [Variable(), Variable(), Optional([Variable()])])
def selection_url_in_transcript(context, start_seconds, transcript, end_seconds=None):
    url_args = {
        "start": mission_time(start_seconds)
    }
    if end_seconds:
        url_args["end"] = mission_time(end_seconds)
    
    if transcript and transcript != context['request'].mission.main_transcript:
        # Split transcript name from [mission]/[transcript]
        url_args["transcript"] = transcript.split('/')[1]
    
    # Render the URL
    url = reverse("view_range", kwargs=url_args)
    if isinstance(start_seconds, basestring):
        start_seconds = timestamp_to_seconds(start_seconds)
    return '%s#log-line-%i' % ( url, start_seconds )

########NEW FILE########
__FILENAME__ = pauses
from django.template import Library

register = Library()

@register.simple_tag
def pause_class(seconds):
    if 120 <= seconds < 300:
        return 'pause short'
    elif 300 <= seconds < 1800:
        return 'pause medium'
    elif 1800 <= seconds < 3600:
        return 'pause long'
    else:
        return ''

@register.simple_tag
def pause_length(seconds):
    hours = seconds // 3600
    minutes = seconds % 3600 // 60
    seconds = seconds % 60
    
    return '%d:%02d:%02d' % (hours, minutes, seconds)

########NEW FILE########
__FILENAME__ = views
from __future__ import division
import os.path
from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.views.generic import TemplateView
from django.views.decorators.http import condition
from django.core.urlresolvers import reverse
from website.apps.common.views import JsonTemplateView
from backend.api import LogLine, Act
from backend.util import timestamp_to_seconds
from transcripts.templatetags.linkify import linkify
from transcripts.templatetags.missiontime import timestamp_to_url, selection_url

class TranscriptView(JsonTemplateView):
    """
    Base view for all views which deal with transcripts.
    Provides some nice common functionality.
    """

    def parse_mission_time(self, mission_time):
        "Parses a mission timestamp from a URL and converts it to a number of seconds"
        # d, h, m, s = [ int(x) for x in mission_time.split(':') ]
        # print mission_time
        # return s + m*60 + h*3600 + d*86400
        return timestamp_to_seconds( mission_time )

    def log_line_query(self):
        return LogLine.Query(self.request.redis_conn, self.request.mission.name)

    def act_query(self):
        return Act.Query(self.request.redis_conn, self.request.mission.name)

    def get_transcript_name(self):
      if self.kwargs.get("transcript", None):
          return self.request.mission.name + "/" + self.kwargs["transcript"]
      return self.request.mission.main_transcript

    def main_transcript_query(self):
        return self.log_line_query().transcript(self.get_transcript_name())

    def media_transcript_query(self):
        return self.log_line_query().transcript(self.request.mission.media_transcript)

    def log_lines(self, start_page, end_page):
        "Returns the log lines and the previous/next timestamps, with images mixed in."
        if end_page > (start_page + 5):
            end_page = start_page + 5
        # Collect the log lines
        log_lines = []
        done_closest = False
        for page in range(start_page, end_page+1):
            log_lines += list(self.main_transcript_query().page(page))
        for log_line in log_lines:
            log_line.images = list(log_line.images())
            log_line.lines = [
                (s, linkify(t, self.request))
                for s, t in log_line.lines
            ]
            # If this is the first after the start time, add an anchor later
            if log_line.timestamp > timestamp_to_seconds(self.kwargs.get('start', "00:00:00:00")) and not done_closest:
                log_line.closest = True
                done_closest = True
        # Find all media that falls inside this same range, and add it onto the preceding line.
        for image_line in self.media_transcript_query().range(log_lines[0].timestamp, log_lines[-1].timestamp):
            # Find the line just before the images
            last_line = None
            for log_line in log_lines:
                if log_line.timestamp > image_line.timestamp:
                    break
                last_line = log_line
            # Add the images to it
            last_line.images += image_line.images()
        # Find the previous log line from this, and then the beginning of its page
        try:
            previous_timestamp = self.main_transcript_query().page(start_page - 1).first().timestamp
        except ValueError:
            previous_timestamp = None
        # Find the next log line and its timestamp
        next_timestamp = log_lines[-1].next_timestamp()
        # Return
        return log_lines, previous_timestamp, next_timestamp, 0, None

    def page_number(self, timestamp):
        "Finds the page number for a given timestamp"
        acts = list(self.act_query().items())
        if timestamp is None:
            timestamp = acts[0].start
        else:
            timestamp = self.parse_mission_time(timestamp)
        try:
            closest_log_line = self.main_transcript_query().first_after(timestamp)
        except ValueError:
            raise Http404("No log entries match that timestamp.")
        return closest_log_line.page

    def other_transcripts(self, start, end):
        """
        Return the list of transcripts and if they have any messages between the times specified.
        """
        for transcript in self.request.mission.transcripts:
            yield transcript, self.log_line_query().transcript(transcript).range(start, end).count()


class PageView(TranscriptView):
    """
    Shows a single page of transcript, based on a passed-in timestamp.
    """

    template_name = 'transcripts/page.html'
    
    def render_to_response(self, context):
        # Ensure that the request is always redirected to:
        # - The first page (timestampless)
        # - The timestamp for the start of an act
        # - The timestamp for the start of an in-act page
        # If the timestamp is already one of these, render as normal
        
        requested_start       = None
        if context['start']:
            requested_start   = timestamp_to_seconds( context['start'] )
        current_act           = context['current_act']
        first_log_line        = context['log_lines'][0]
        prior_log_line        = first_log_line.previous()
        
        # NOTE: is_act_first_page will be false for first act:
        #       that's handled by is_first_page
        is_first_page         = not prior_log_line
        is_act_first_page     = False
        if prior_log_line:
            is_act_first_page = prior_log_line.timestamp < current_act.start \
                             <= first_log_line.timestamp
        
        page_start_url = None
        # If we're on the first page, but have a timestamp,
        # redirect to the bare page URL
        if requested_start and is_first_page:
            if context['transcript_name'] != context['mission_main_transcript']:
                # Split transcript name from [mission]/[transcript]
                transcript = context['transcript_name'].split('/')[1]
                page_start_url = reverse("view_page", kwargs={"transcript": transcript})
            else:
                page_start_url = reverse("view_page")
        # If we're on the first page of an act,
        # but not on the act-start timestamp, redirect to that
        elif is_act_first_page \
        and requested_start != current_act.start:
            page_start_url = timestamp_to_url( context, current_act.start )
        # If we're on any other page and the timestamp doesn't match
        # the timestamp of the first item, redirect to that item's timestamp
        elif requested_start and not is_act_first_page \
        and requested_start != first_log_line.timestamp:
            page_start_url = timestamp_to_url(
                context,
                first_log_line.timestamp
            )
        
        # Redirect to the URL we found
        if page_start_url:
            if self.request.GET:
                page_start_url += '?%s' % self.request.GET.urlencode()
            return HttpResponseRedirect( page_start_url )
        
        return super( PageView, self ).render_to_response( context )
    
    def get_context_data(self, start=None, end=None, transcript=None):

        if end is None:
            end = start

        # Get the content
        log_lines, previous_timestamp, next_timestamp, max_highlight_index, first_highlighted_line = self.log_lines(
            self.page_number(start),
            self.page_number(end),
        )
        
        act          = log_lines[0].act()
        act_id       = log_lines[0].act().number
        acts         = list(self.act_query().items())
        previous_act = None
        next_act     = None
        
        if act_id > 0:
            previous_act = acts[act_id-1]
        if act_id < len(acts) - 1:
            next_act = acts[act_id+1]
        
        for log_line in log_lines:
            if log_line.transcript_page:
                original_transcript_page = log_line.transcript_page
                break
        else:
            original_transcript_page = None
        
        if start:
            permalink_fragment = '#log-line-%s' % timestamp_to_seconds(start)
        else:
            permalink_fragment = '#log-line-%s' % log_lines[0].timestamp
        
        return {
            # HACK: Force request into context. Not sure why it's not here.
            'request': self.request,
            'mission_name': self.request.mission.name,
            'mission_main_transcript': self.request.mission.main_transcript,
            'transcript_name': self.get_transcript_name(),
            'transcript_short_name': self.get_transcript_name().split('/')[1],
            'start' : start,
            'log_lines': log_lines,
            'next_timestamp': next_timestamp,
            'previous_timestamp': previous_timestamp,
            'acts': acts,
            'act': act_id+1,
            'current_act': act,
            'previous_act': previous_act,
            'next_act': next_act,
            'max_highlight_index': max_highlight_index,
            'first_highlighted_line': first_highlighted_line,
            'original_transcript_page': original_transcript_page,
            'permalink': 'http://%s%s%s' % (
                self.request.META['HTTP_HOST'],
                self.request.path,
                permalink_fragment,
            ),
            'other_transcripts': self.other_transcripts(
                log_lines[0].timestamp,
                log_lines[-1].timestamp,
            ),
        }


class RangeView(PageView):
    """
    Shows records between two timestamps (may also include just
    showing a single record).
    """
    
    def render_to_response(self, context):
        # Identify whether our start and end timestamps match real timestamps
        # If not, redirect from the invalid-timestamped URL to the
        # URL with timestamps matching loglines
        start = context['selection_start_timestamp']
        end = context['selection_end_timestamp']
        if start == end:
            end = None
        
        start_line = context['first_highlighted_line']
        
        # Find the last log_line in the current selection if we have a range
        end_line = start_line
        if end:
            for log_line in context['log_lines']:
                if end_line.timestamp <= log_line.timestamp <= end:
                    end_line = log_line
                elif end <= log_line.timestamp:
                    break
        
        # Get the URL we should redirect to (if any)
        page_start_url = None
        if (not end and start != start_line.timestamp) \
        or (end and start != end and start_line.timestamp == end_line.timestamp):
            # We have an individual start time only
            # -or-
            # We have start and end times that resolve to the same log_line
            page_start_url = selection_url( context, start_line.timestamp )
        elif (start != start_line.timestamp) \
          or (end and end != end_line.timestamp):
            # We have an invalid start/end time in a range
            # Doesn't matter if start is valid or not: this will handle both
            page_start_url = selection_url(
                context,
                start_line.timestamp,
                end_line.timestamp
            )
        
        # Redirect to the URL we found
        if page_start_url:
            return HttpResponseRedirect( page_start_url )
            
        return super( PageView, self ).render_to_response( context )
    
    def log_lines(self, start_page, end_page):
        log_lines, previous_link, next_link, highlight_index, discard = super(RangeView, self).log_lines(start_page, end_page)
        start = self.parse_mission_time(self.kwargs['start'])
        # If there's no end, make it the first item after the given start.
        if "end" in self.kwargs:
            end = self.parse_mission_time(self.kwargs['end'])
        else:
            end = self.main_transcript_query().first_after(start).timestamp

        highlight_index = 0
        first_highlighted_line = None
        for log_line in log_lines:
            if start <= log_line.timestamp <= end:
                log_line.highlighted = True
                if highlight_index == 0:
                    first_highlighted_line = log_line
                highlight_index += 1
                log_line.highlight_index = highlight_index

        for log_line1, log_line2 in zip(log_lines, log_lines[1:]):
            if getattr(log_line2, 'highlight_index', None) == 1:
                log_line1.pre_highlight = True
                break

        return log_lines, previous_link, next_link, highlight_index, first_highlighted_line

    def get_context_data(self, start=None, end=None, transcript=None):
        data = super(RangeView, self).get_context_data(start, end, transcript)
        data.update({
            "selection_start_timestamp": self.parse_mission_time(start),
            "selection_end_timestamp": self.parse_mission_time(start if end is None else end),
        })
        return data


class PhasesView(TranscriptView):
    """
    Shows the list of all phases (acts).
    """
    
    template_name = 'transcripts/phases.html'
    
    def get_context_data(self, phase_number='1'):
        try:
            selected_act = Act(self.request.redis_conn, self.request.mission.name, int(phase_number) - 1)
        except KeyError:
            raise Http404('Phase %s not found' % phase_number)

        return {
            'acts': list(self.act_query()),
            'act': selected_act,
        }

class ErrorView(TemplateView):

    template_name = "error.html"
    error_code = 404

    default_titles = {
        404: "Page Not Found",
        500: "Server Error",
    }

    def render_to_response(self, context):
        """
        Returns a response with a template rendered with the given context.
        """
        return self.get_response(self.render_template(context), status=self.error_code)

    def get_context_data(self):
        error_info = self.request.redis_conn.hgetall(
            "error_page:%s:%i" % (
                self.request.mission.name,
                self.error_code,
            ),
        )
        if not error_info:
            error_info = {}
        return {
            "title": error_info.get('title', self.default_titles[self.error_code]),
            "heading": error_info.get('heading', self.default_titles[self.error_code]),
            "heading_quote": error_info.get('heading_quote', None),
            "subheading": error_info.get('subheading', ""),
            "text": error_info.get('text', ''),
            "classic_moment": error_info.get('classic_moment', None),
            "classic_moment_quote": error_info.get('classic_moment_quote', None),
        }

class OriginalView(TemplateView):

    template_name = "transcripts/original.html"
    
    def get_transcript_name(self):
      if self.kwargs.get("transcript", None):
          return self.request.mission.name + "/" + self.kwargs["transcript"]
      return self.request.mission.main_transcript
    
    def get_context_data(self, page, transcript=None):
        page = int(page)
        transcript_name = self.get_transcript_name();
        max_transcript_pages = int(self.request.mission.transcript_pages[transcript_name])
        
        if not 1 <= page <= max_transcript_pages:
            raise Http404("No original page with that page number.")
        
        return {
            'transcript_name': transcript_name,
            'transcript_short_name': transcript_name.split('/')[1],
            "page": page,
            "next_page": page + 1 if page < max_transcript_pages else None,
            "previous_page": page - 1 if page > 1 else None,
        }

class ProgressiveFileWrapper(object):
    def __init__(self, filelike, blksize, interval):
        self.filelike = filelike
        self.blksize = blksize
        self.lastsend = None
        if hasattr(filelike,'close'):
            self.close = filelike.close

    def _wait(self):
        if self.lastsend is None:
            return
        diff = time() - self.lastsend + interval
        if diff < 0:
            return
        sleep(diff)

    def __getitem__(self,key):
        self._wait()
        data = self.filelike.read(self.blksize)
        if data:
            return data
        raise IndexError

    def __iter__(self):
        return self

    def next(self):
        self._wait()
        data = self.filelike.read(self.blksize)
        if data:
            return data
        raise StopIteration

@condition(etag_func=None)
def stream(request, start):
    bitrate = 48000
    offset = 555
    file_path = os.path.join(settings.SITE_ROOT, '../missions/mr3/audio/ATG.mp3')
    start = timestamp_to_seconds(start)
    offset = int((start + offset) * bitrate / 8)
    file_size = os.path.getsize(file_path)
    if offset > file_size or offset < 0:
        raise Http404
    fh = open(file_path, 'r')
    fh.seek(offset)
    response = HttpResponse(ProgressiveFileWrapper(fh, int(bitrate / 8), 1))
    response['Content-Type'] = 'audio/mpeg'
    return response

########NEW FILE########
__FILENAME__ = settings
from configs.settings import *

DEBUG = True
TEMPLATE_DEBUG = DEBUG
PROJECT_HOME = "http://dev.spacelog.org:8001/"

INSTALLED_APPS += ('django_concurrent_test_server',)

try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = settings
from configs.settings import *
# The following MUST be an absolute URL in live deploys (it's given out
# to other systems). Also, it doesn't get overridden in local_settings.py
# unlike the others.
FIXED_MISSIONS_STATIC_URL = 'http://cdn.spacelog.org/assets/website/missions/'

STATIC_URL = 'http://cdn.spacelog.org/assets/website/'
MISSIONS_STATIC_URL = 'http://cdn.spacelog.org/assets/website/missions/'
MISSIONS_IMAGE_URL = 'http://media.spacelog.org/'

# allow local overrides, probably built during deploy
try:
    from local_settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = settings
# Django settings for website project.

import os
import django
import sys

# calculated paths for django and the site
# used as starting points for various other paths
DJANGO_ROOT = os.path.dirname(os.path.realpath(django.__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

sys.path.append(os.path.join(SITE_ROOT, 'apps'))

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

STATIC_ROOT = os.path.join(SITE_ROOT, 'static')
STATIC_URL = '/assets/'
# in dev, these come from the same place; in live, they'll be in different
# places on the CDN
MISSIONS_STATIC_ROOT = os.path.join(SITE_ROOT, '..', 'missions')
MISSIONS_STATIC_URL = '/assets/missions/'
# FIXED_MISSIONS_STATIC_URL doesn't change with varying deploys, so can be used for
# things that need long-term URLs, like image references in the Open Graph.
FIXED_MISSIONS_STATIC_URL = '/assets/missions/'
MISSIONS_IMAGE_ROOT = os.path.join(SITE_ROOT, '..', 'missions')
# Set this to '/assets/missions/' if you want to test local mission images
MISSIONS_IMAGE_URL = 'http://media.spacelog.org/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'hqp*)4r*a99h4@=7@5bpdn+ik8+x9c&=zk4o-=w1ap6n!9_@z1'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'transcripts.middleware.HoldingMiddleware',
    'transcripts.middleware.MissionMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    "transcripts.context.mission",
    "transcripts.context.static",
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(SITE_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.humanize',
    'common',
    'search',
    'transcripts',
)

PROJECT_HOME = "http://spacelog.org/"

########NEW FILE########
__FILENAME__ = settings
from configs.settings import *
PROJECT_HOME = "http://artemis.fort/"

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import os
import sys

# where are we? eh?
project_path = os.path.realpath(os.path.dirname(__file__))

# we add them first in case we want to override anything already on the system
sys.path.insert(0, project_path)
sys.path.insert(0, os.path.join(project_path, '../'))

import ext

from django.core.management import execute_manager
args = sys.argv
# Let's figure out our environment
if os.environ.has_key('DJANGOENV'):
    environment = os.environ['DJANGOENV']
elif len(sys.argv) > 1:
    # this doesn't currently work
    environment = sys.argv[1]
    if os.path.isdir(os.path.join(project_path, 'configs', environment)):
        sys.argv = [sys.argv[0]] + sys.argv[2:]
    else:
        environment = None
else:
    environment = None
try:
    module = "configs.%s.settings" % environment
    __import__(module)
    settings = sys.modules[module]
    # worked, so add it into the path so we can import other things out of it
    sys.path.insert(0, os.path.join(project_path, 'configs', environment))
except ImportError:
    environment = None

# We haven't found anything helpful yet, so use development.
if environment == None:
    try:
        import configs.development.settings
        settings = configs.development.settings
        environment = 'development'
        sys.path.insert(0, os.path.join(project_path, 'configs', environment))
    except ImportError:
        sys.stderr.write("Error: Can't find the file 'settings.py'; looked in %s and development.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % (environment,))
        sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from transcripts.views import PageView, PhasesView, RangeView, ErrorView, OriginalView
from homepage.views import HomepageView, HomepageQuoteView
from search.views import SearchView
from homepage.views import HomepageView, AboutView

tspatt = r'-?\d+:\d+:\d+:\d+'

urlpatterns = patterns('',
    url(r'^$', HomepageView.as_view(), name="homepage"),
    url(r'^homepage-quote/$', HomepageQuoteView.as_view()),
    url(r'^about/$', AboutView.as_view(), name="about"),
    url(r'^page/(?:(?P<transcript>[-_\w]+)/)?$', PageView.as_view(), name="view_page"),
    url(r'^page/(?P<start>' + tspatt + ')/(?:(?P<transcript>[-_\w]+)/)?$', PageView.as_view(), name="view_page"),
    url(r'^(?P<start>' + tspatt + ')/(?:(?P<transcript>[-_\w]+)/)?$', RangeView.as_view(), name="view_range"),
    url(r'^stream/(?P<start>' + tspatt + ')/?$', 'transcripts.views.stream', name="stream"),
    url(r'^(?P<start>' + tspatt + ')/(?P<end>' + tspatt + ')/(?:(?P<transcript>[-_\w]+)/)?$', RangeView.as_view(), name="view_range"),
    url(r'^phases/$', PhasesView.as_view(), name="phases"),
    url(r'^phases/(?P<phase_number>\d+)/$', PhasesView.as_view(), name="phases"),
    url(r'^search/$', SearchView.as_view(), name="search"),
    url(r'^people/$', 'people.views.people', name="people"),
    url(r'^people/(?P<role>[-_\w]+)/$', 'people.views.people', name="people"),
    url(r'^glossary/$', 'glossary.views.glossary', name="glossary"),   
    url(r'^original/(?:(?P<transcript>[-_\w]+)/)?(?P<page>-?\d+)/$', OriginalView.as_view(), name="original"),
)

if settings.DEBUG: # pragma: no cover
    urlpatterns += patterns('',
        (r'^' + settings.MISSIONS_STATIC_URL[1:] + '(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MISSIONS_STATIC_ROOT
        }),
        (r'^' + settings.MISSIONS_IMAGE_URL[1:] + '(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MISSIONS_IMAGE_ROOT
        }),
        (r'^' + settings.STATIC_URL[1:] + '(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.STATIC_ROOT
        }),
        # (r'^' + settings.MEDIA_URL[1:] + '(?P<path>.*)$', 'django.views.static.serve', {
        #     'document_root': settings.MEDIA_ROOT
        # }),
        (r'^404/$', ErrorView.as_view()),
        (r'^500/$', ErrorView.as_view(error_code=500)),
    )

handler404 = ErrorView.as_view()
handler500 = ErrorView.as_view(error_code=500)


########NEW FILE########
