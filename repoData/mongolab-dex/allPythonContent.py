__FILENAME__ = analyzer
__author__ = 'eric'

from utils import pretty_json, validate_yaml
import sys
import pymongo
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

################################################################################
# Constants
#    query operator groupings and flag values
################################################################################

RANGE_QUERY_OPERATORS = ['$ne', '$gt', '$lt',
                         '$gte', '$lte', '$in',
                         '$nin', '$all', '$not']

#The following field is provided for reference and possible future use:
UNSUPPORTED_QUERY_OPERATORS = ['$mod', '$exists', '$size',
                               '$type', '$elemMatch', '$where', '$near',
                               '$within']

SUPPORTED_COMMANDS = ['count', 'findAndModify']

COMPOSITE_QUERY_OPERATORS = ['$or', '$nor', '$and']
RANGE_TYPE = 'RANGE'
EQUIV_TYPE = 'EQUIV'
UNSUPPORTED_TYPE = 'UNSUPPORTED'
SORT_TYPE = 'SORT'
BACKGROUND_FLAG = 'true'


################################################################################
# QueryAnalyzer
#   Maintains an internal cache of indexes to analyze queries against. Connects
#   to databases to populate cache.
################################################################################
class QueryAnalyzer:
    def __init__(self, check_indexes):
        self._internal_map = {}
        self._check_indexes = check_indexes
        self._index_cache_connection = None

    ############################################################################
    def generate_query_report(self, db_uri, parsed_query, db_name, collection_name):
        """Generates a comprehensive report on the raw query"""
        index_analysis = None
        recommendation = None
        namespace = parsed_query['ns']
        indexStatus = "unknown"

        index_cache_entry = self._ensure_index_cache(db_uri,
                                                     db_name,
                                                     collection_name)


        query_analysis = self._generate_query_analysis(parsed_query,
                                                       db_name,
                                                       collection_name)
        if ((query_analysis['analyzedFields'] != []) and
             query_analysis['supported']):
            index_analysis = self._generate_index_analysis(query_analysis,
                                                           index_cache_entry['indexes'])
            indexStatus = index_analysis['indexStatus']
            if index_analysis['indexStatus'] != 'full':
                recommendation = self._generate_recommendation(query_analysis,
                                                               db_name,
                                                               collection_name)
                # a temporary fix to suppress faulty parsing of $regexes.
                # if the recommendation cannot be re-parsed into yaml, we assume
                # it is invalid.
                if not validate_yaml(recommendation['index']):
                    recommendation = None
                    query_analysis['supported'] = False


        # QUERY REPORT
        return OrderedDict({
            'queryMask': parsed_query['queryMask'],
            'indexStatus': indexStatus,
            'parsed': parsed_query,
            'namespace': namespace,
            'queryAnalysis': query_analysis,
            'indexAnalysis': index_analysis,
            'recommendation': recommendation
        })

    ############################################################################
    def _ensure_index_cache(self, db_uri, db_name, collection_name):
        """Adds a collections index entries to the cache if not present"""
        if not self._check_indexes or db_uri is None:
            return {'indexes': None}
        if db_name not in self.get_cache():
            self._internal_map[db_name] = {}
        if collection_name not in self._internal_map[db_name]:
            indexes = []
            try:
                if self._index_cache_connection is None:
                    self._index_cache_connection = pymongo.MongoClient(db_uri,
                                                                       document_class=OrderedDict,
                                                                       read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED)

                db = self._index_cache_connection[db_name]
                indexes = db[collection_name].index_information()
            except:
                warning = 'Warning: unable to connect to ' + db_uri + "\n"
            else:
                internal_map_entry = {'indexes': indexes}
                self.get_cache()[db_name][collection_name] = internal_map_entry
        return self.get_cache()[db_name][collection_name]

    ############################################################################
    def _generate_query_analysis(self, parsed_query, db_name, collection_name):
        """Translates a raw query object into a Dex query analysis"""

        analyzed_fields = []
        field_count = 0
        supported = True
        sort_fields = []
        query_mask = None

        if 'command' in parsed_query and parsed_query['command'] not in SUPPORTED_COMMANDS:
            supported = False
        else:
            #if 'orderby' in parsed_query:
            sort_component = parsed_query['orderby'] if 'orderby' in parsed_query else []
            sort_seq = 0
            for key in sort_component:
                sort_field = {'fieldName': key,
                              'fieldType': SORT_TYPE,
                              'seq': sort_seq}
                sort_fields.append(key)
                analyzed_fields.append(sort_field)
                field_count += 1
                sort_seq += 1

            query_component = parsed_query['query'] if 'query' in parsed_query else {}
            for key in query_component:
                if key not in sort_fields:
                    field_type = UNSUPPORTED_TYPE
                    if ((key not in UNSUPPORTED_QUERY_OPERATORS) and
                            (key not in COMPOSITE_QUERY_OPERATORS)):
                        try:
                            if query_component[key] == {}:
                                raise
                            nested_field_list = query_component[key].keys()
                        except:
                            field_type = EQUIV_TYPE
                        else:
                            for nested_field in nested_field_list:
                                if ((nested_field in RANGE_QUERY_OPERATORS) and
                                    (nested_field not in UNSUPPORTED_QUERY_OPERATORS)):
                                    field_type = RANGE_TYPE
                                else:
                                    supported = False
                                    field_type = UNSUPPORTED_TYPE
                                    break

                    if field_type is UNSUPPORTED_TYPE:
                        supported = False

                    analyzed_field = {'fieldName': key,
                                      'fieldType': field_type}
                    analyzed_fields.append(analyzed_field)
                    field_count += 1

        query_mask = parsed_query['queryMask']

        # QUERY ANALYSIS
        return OrderedDict({
            'analyzedFields': analyzed_fields,
            'fieldCount': field_count,
            'supported': supported,
            'queryMask': query_mask
        })

    ############################################################################
    def _generate_index_analysis(self, query_analysis, indexes):
        """Compares a query signature to the index cache to identify complete
            and partial indexes available to the query"""
        needs_recommendation = True
        full_indexes = []
        partial_indexes = []
        coverage = "unknown"

        if indexes is not None:
            for index_key in indexes.keys():
                index = indexes[index_key]
                index_report = self._generate_index_report(index,
                                                           query_analysis)
                if index_report['supported'] is True:
                    if index_report['coverage'] == 'full':
                        full_indexes.append(index_report)
                        if index_report['idealOrder']:
                            needs_recommendation = False
                    elif index_report['coverage'] == 'partial':
                        partial_indexes.append(index_report)

        if len(full_indexes) > 0:
            coverage = "full"
        elif (len(partial_indexes)) > 0:
            coverage = "partial"
        elif query_analysis['supported']:
            coverage = "none"

        # INDEX ANALYSIS
        return OrderedDict([('indexStatus', coverage),
                            ('fullIndexes', full_indexes),
                            ('partialIndexes', partial_indexes)])

    ############################################################################
    def _generate_index_report(self, index, query_analysis):
        """Analyzes an existing index against the results of query analysis"""

        all_fields = []
        equiv_fields = []
        sort_fields = []
        range_fields = []

        for query_field in query_analysis['analyzedFields']:
            all_fields.append(query_field['fieldName'])
            if query_field['fieldType'] is EQUIV_TYPE:
                equiv_fields.append(query_field['fieldName'])
            elif query_field['fieldType'] is SORT_TYPE:
                sort_fields.append(query_field['fieldName'])
            elif query_field['fieldType'] is RANGE_TYPE:
                range_fields.append(query_field['fieldName'])

        max_equiv_seq = len(equiv_fields)
        max_sort_seq = max_equiv_seq + len(sort_fields)
        max_range_seq = max_sort_seq + len(range_fields)

        coverage = 'none'
        query_fields_covered = 0
        query_field_count = query_analysis['fieldCount']
        supported = True
        ideal_order = True
        for index_field in index['key']:
            field_name = index_field[0]

            if index_field[1] == '2d':
                supported = False
                break

            if field_name not in all_fields:
                break

            if query_fields_covered == 0:
                coverage = 'partial'

            if query_fields_covered < max_equiv_seq:
                if field_name not in equiv_fields:
                    ideal_order = False
            elif query_fields_covered < max_sort_seq:
                if field_name not in sort_fields:
                    ideal_order = False
            elif query_fields_covered < max_range_seq:
                if field_name not in range_fields:
                    ideal_order = False
            query_fields_covered += 1
        if query_fields_covered == query_field_count:
            coverage = 'full'

        # INDEX REPORT
        return OrderedDict({
            'coverage': coverage,
            'idealOrder': ideal_order,
            'queryFieldsCovered': query_fields_covered,
            'index': index,
            'supported': supported
        })

    ############################################################################
    def _generate_recommendation(self,
                                 query_analysis,
                                 db_name,
                                 collection_name):
        """Generates an ideal query recommendation"""
        index_rec = '{'
        for query_field in query_analysis['analyzedFields']:
            if query_field['fieldType'] is EQUIV_TYPE:
                if len(index_rec) is not 1:
                    index_rec += ', '
                index_rec += '"' + query_field['fieldName'] + '": 1'
        for query_field in query_analysis['analyzedFields']:
            if query_field['fieldType'] is SORT_TYPE:
                if len(index_rec) is not 1:
                    index_rec += ', '
                index_rec += '"' + query_field['fieldName'] + '": 1'
        for query_field in query_analysis['analyzedFields']:
            if query_field['fieldType'] is RANGE_TYPE:
                if len(index_rec) is not 1:
                    index_rec += ', '
                index_rec += '"' + query_field['fieldName'] + '": 1'
        index_rec += '}'

        # RECOMMENDATION
        return OrderedDict([('index',index_rec),
                            ('shellCommand', self.generate_shell_command(collection_name, index_rec))])

    ############################################################################
    def generate_shell_command(self, collection_name, index_rec):
        command_string = 'db["' + collection_name + '"].ensureIndex('
        command_string += index_rec + ', '
        command_string += '{"background": ' + BACKGROUND_FLAG + '})'
        return command_string

    ############################################################################
    def get_cache(self):
        return self._internal_map

    ############################################################################
    def clear_cache(self):
        self._internal_map = {}

################################################################################
# ReportAggregation
#   Stores a merged set of query reports with running statistics
################################################################################
class ReportAggregation:
    def __init__(self):
        self._reports = []

    ############################################################################
    def add_query_occurrence(self, report):
        """Adds a report to the report aggregation"""

        initial_millis = int(report['parsed']['stats']['millis'])
        mask = report['queryMask']

        existing_report = self._get_existing_report(mask, report)

        if existing_report is not None:
            self._merge_report(existing_report, report)
        else:
            time = None
            if 'ts' in report['parsed']:
                time = report['parsed']['ts']
            self._reports.append(OrderedDict([
                ('namespace', report['namespace']),
                ('lastSeenDate', time),
                ('queryMask', mask),
                ('supported', report['queryAnalysis']['supported']),
                ('indexStatus', report['indexStatus']),
                ('recommendation', report['recommendation']),
                ('stats', OrderedDict([('count', 1),
                                       ('totalTimeMillis', initial_millis),
                                       ('avgTimeMillis', initial_millis)]))]))

    ############################################################################
    def get_reports(self):
        """Returns a minimized version of the aggregation"""
        return sorted(self._reports,
                      key=lambda x: x['stats']['totalTimeMillis'],
                      reverse=True)

    ############################################################################
    def _get_existing_report(self, mask, report):
        """Returns the aggregated report that matches report"""
        for existing_report in self._reports:
            if existing_report['namespace'] == report['namespace']:
                if mask == existing_report['queryMask']:
                    return existing_report
        return None

    ############################################################################
    def _merge_report(self, target, new):
        """Merges a new report into the target report"""
        time = None
        if 'ts' in new['parsed']:
            time = new['parsed']['ts']

        if (target.get('lastSeenDate', None) and
                time and
                    target['lastSeenDate'] < time):
            target['lastSeenDate'] = time

        query_millis = int(new['parsed']['stats']['millis'])
        target['stats']['totalTimeMillis'] += query_millis
        target['stats']['count'] += 1
        target['stats']['avgTimeMillis'] = target['stats']['totalTimeMillis'] / target['stats']['count']

########NEW FILE########
__FILENAME__ = dex
################################################################################
#
# Copyright (c) 2012 ObjectLabs Corporation
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
################################################################################

import pymongo
import sys
import time
from utils import pretty_json
from analyzer import QueryAnalyzer, ReportAggregation
from parsers import LogParser, ProfileParser, get_line_time
from datetime import datetime
from datetime import timedelta
import traceback
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

################################################################################
# Configuration
################################################################################

IGNORE_DBS = ['local', 'admin', 'config']
IGNORE_COLLECTIONS = [u'system.namespaces',
                      u'system.profile',
                      u'system.users',
                      u'system.indexes']
WATCH_INTERVAL_SECONDS = 3.0
WATCH_DISPLAY_REFRESH_SECONDS = 30.0
DEFAULT_PROFILE_LEVEL = pymongo.SLOW_ONLY


################################################################################
# Dex
#   Uses a QueryAnalyzer (with included LogParser) to analyze a MongoDB
#   query or logfile
################################################################################
class Dex:

    ############################################################################
    def __init__(self, db_uri, verbose, namespaces_list, slowms, check_indexes, timeout):
        self._check_indexes = check_indexes
        self._query_analyzer = QueryAnalyzer(check_indexes)
        self._db_uri = db_uri
        self._slowms = slowms
        self._verbose = verbose
        self._requested_namespaces = self._validate_namespaces(namespaces_list)
        self._recommendation_cache = []
        self._report = ReportAggregation()
        self._start_time = None
        self._timeout_time = None
        self._timeout = timeout
        self._run_stats = self._get_initial_run_stats()
        self._first_line = True

    ############################################################################
    def generate_query_report(self, db_uri, query, db_name, collection_name):
        """Analyzes a single query"""
        return self._query_analyzer.generate_query_report(db_uri,
                                                          query,
                                                          db_name,
                                                          collection_name)

    ############################################################################
    def _process_query(self, input, parser):
        self._run_stats['linesRead'] += 1

        line_time = get_line_time(input)

        if line_time is not None:
            if ((self._run_stats['timeRange']['start'] is None) or
                (self._run_stats['timeRange']['start'] > line_time)):
                self._run_stats['timeRange']['start'] = line_time
            if ((self._run_stats['timeRange']['end'] is None) or
                (self._run_stats['timeRange']['end'] < line_time)):
                self._run_stats['timeRange']['end'] = line_time

        parsed = parser.parse(input)

        if parsed is not None:
            if parsed['supported']:
                self._run_stats['linesAnalyzed'] += 1
                namespace_tuple = self._tuplefy_namespace(parsed['ns'])
                # If the query is for a requested namespace ....
                if self._namespace_requested(parsed['ns']):
                    db_name = namespace_tuple[0]
                    collection_name = namespace_tuple[1]
                    query_report = None
                    if parsed['stats']['millis'] >= self._slowms:
                        try:
                            query_report = self.generate_query_report(self._db_uri,
                                                                      parsed,
                                                                      db_name,
                                                                      collection_name)
                        except Exception as e:
                            #print traceback.print_exc()
                            return 1
                    if query_report is not None:
                        if query_report['recommendation'] is not None:
                            self._run_stats['linesWithRecommendations'] += 1
                        self._report.add_query_occurrence(query_report)
            else:
                self._run_stats['unparsableLineInfo']['unparsableLines'] += 1
                self._run_stats['unparsableLineInfo']['unparsableLinesWithTime'] += 1
                self._run_stats['unparsableLineInfo']['unparsedTimeMillis'] += int(parsed['stats']['millis'])
                self._run_stats['unparsableLineInfo']['unparsedAvgTimeMillis'] = self._run_stats['unparsableLineInfo']['unparsedTimeMillis'] / self._run_stats['unparsableLineInfo']['unparsableLinesWithTime']
        else:
            self._run_stats['unparsableLineInfo']['unparsableLines'] += 1
            self._run_stats['unparsableLineInfo']['unparsableLinesWithoutTime'] += 1

    ############################################################################
    def analyze_profile(self):
        """Analyzes queries from a given log file"""
        profile_parser = ProfileParser()
        databases = self._get_requested_databases()
        connection = pymongo.MongoClient(self._db_uri,
                                         document_class=OrderedDict,
                                         read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED)

        if databases == []:
            try:
                databases = connection.database_names()
            except:
                message = "Error: Could not list databases on server. Please " \
                          +         "check the auth components of your URI or provide " \
                          +         "a namespace filter with -n.\n"
                sys.stderr.write(message)
                databases = []

            for ignore_db in IGNORE_DBS:
                if ignore_db in databases:
                    databases.remove(ignore_db)

        for database in databases:

            db = connection[database]

            profile_entries = db['system.profile'].find()

            for profile_entry in profile_entries:
                self._process_query(profile_entry,
                                    profile_parser)

        self._output_aggregated_report(sys.stdout)

        return 0

    ############################################################################
    def watch_profile(self):
        """Analyzes queries from a given log file"""
        profile_parser = ProfileParser()
        databases = self._get_requested_databases()
        connection = pymongo.MongoClient(self._db_uri,
                                         document_class=OrderedDict,
                                         read_preference=pymongo.ReadPreference.PRIMARY_PREFERRED)
        enabled_profile = False

        if databases == []:
            try:
                databases = connection.database_names()
            except:
                message = "Error: Could not list databases on server. Please " \
                          +         "check the auth components of your URI.\n"
                sys.stderr.write(message)
                databases = []

            for ignore_db in IGNORE_DBS:
                if ignore_db in databases:
                    databases.remove(ignore_db)

        if len(databases) != 1:
            message = "Error: Please use namespaces (-n) to specify a single " \
                      +         "database for profile watching.\n"
            sys.stderr.write(message)
            return 1

        database = databases[0]
        db = connection[database]

        initial_profile_level = db.profiling_level()

        if initial_profile_level is pymongo.OFF:
            message = "Profile level currently 0. Dex is setting profile " \
                      +         "level 1. To run --watch at profile level 2, " \
                      +         "enable profile level 2 before running Dex.\n"
            sys.stderr.write(message)
            db.set_profiling_level(DEFAULT_PROFILE_LEVEL)

        output_time = time.time() + WATCH_DISPLAY_REFRESH_SECONDS
        try:
            for profile_entry in self._tail_profile(db, WATCH_INTERVAL_SECONDS):
                self._process_query(profile_entry,
                                    profile_parser)
                if time.time() >= output_time:
                    self._output_aggregated_report(sys.stderr)
                    output_time = time.time() + WATCH_DISPLAY_REFRESH_SECONDS
        except KeyboardInterrupt:
            sys.stderr.write("Interrupt received\n")
        finally:
            self._output_aggregated_report(sys.stdout)
            if initial_profile_level is pymongo.OFF:
                message = "Dex is resetting profile level to initial value " \
                          +         "of 0. You may wish to drop the system.profile " \
                          +         "collection.\n"
                sys.stderr.write(message)
                db.set_profiling_level(initial_profile_level)

        return 0

    ############################################################################
    def analyze_logfile(self, logfile_path):
        self._run_stats['logSource'] = logfile_path
        """Analyzes queries from a given log file"""
        with open(logfile_path) as obj:
            self.analyze_logfile_object(obj)

        self._output_aggregated_report(sys.stdout)

        return 0

    ############################################################################
    def analyze_logfile_object(self, file_object):
        """Analyzes queries from a given log file"""
        log_parser = LogParser()

        if self._start_time is None:
            self._start_time = datetime.now()
            if self._timeout != 0:
                self._end_time = self._start_time + timedelta(minutes=self._timeout)
            else:
                self._end_time = None

        # For each line in the logfile ...
        for line in file_object:
            if self._end_time is not None and datetime.now() > self._end_time:
                self._run_stats['timedOut'] = True
                self._run_stats['timeoutInMinutes'] = self._timeout
                break
            self._process_query(line, log_parser)

        return 0

    ############################################################################
    def watch_logfile(self, logfile_path):
        """Analyzes queries from the tail of a given log file"""
        self._run_stats['logSource'] = logfile_path
        log_parser = LogParser()

        # For each new line in the logfile ...
        output_time = time.time() + WATCH_DISPLAY_REFRESH_SECONDS
        try:
            firstLine = True
            for line in self._tail_file(open(logfile_path),
                                        WATCH_INTERVAL_SECONDS):
                if firstLine:
                    self._run_stats['timeRange']['start'] = get_line_time(line)
                self._process_query(line, log_parser)
                self._run_stats['timeRange']['end'] = get_line_time(line)
                if time.time() >= output_time:
                    self._output_aggregated_report(sys.stderr)
                    output_time = time.time() + WATCH_DISPLAY_REFRESH_SECONDS
        except KeyboardInterrupt:
            sys.stderr.write("Interrupt received\n")
        finally:
            self._output_aggregated_report(sys.stdout)

        return 0

    ############################################################################
    def _get_initial_run_stats(self):
        """Singlesource for initializing an output dict"""
        return OrderedDict([('linesWithRecommendations', 0),
                            ('linesAnalyzed', 0),
                            ('linesRead', 0),
                            ('dexTime', datetime.utcnow()),
                            ('logSource', None),
                            ('timeRange', OrderedDict([('start', None),
                                                       ('end', None)])),
                            ('unparsableLineInfo', OrderedDict([('unparsableLines', 0),
                                                                ('unparsableLinesWithoutTime', 0),
                                                                ('unparsableLinesWithTime', 0),
                                                                ('unparsedTimeMillis', 0),
                                                                ('unparsedAvgTimeMillis', 0)]))])

    ############################################################################
    def _make_aggregated_report(self):
        output = OrderedDict([('runStats', self._run_stats),
                              ('results', self._report.get_reports())])
        return output

    ############################################################################
    def _output_aggregated_report(self, out):
        out.write(pretty_json(self._make_aggregated_report()).replace('"', "'").replace("\\'", '"') + "\n")

    ############################################################################
    def _tail_file(self, file, interval):
        """Tails a file"""
        file.seek(0,2)
        while True:
            where = file.tell()
            line = file.readline()
            if not line:
                time.sleep(interval)
                file.seek(where)
            else:
                yield line

    ############################################################################
    def _tail_profile(self, db, interval):
        """Tails the system.profile collection"""
        latest_doc = None
        while latest_doc is None:
            time.sleep(interval)
            latest_doc = db['system.profile'].find_one()

        current_time = latest_doc['ts']

        while True:
            time.sleep(interval)
            cursor = db['system.profile'].find({'ts': {'$gte': current_time}}).sort('ts', pymongo.ASCENDING)
            for doc in cursor:
                current_time = doc['ts']
                yield doc


    ############################################################################
    def _tuplefy_namespace(self, namespace):
        """Converts a mongodb namespace to a db, collection tuple"""
        namespace_split = namespace.split('.', 1)
        if len(namespace_split) is 1:
            # we treat a single element as a collection name.
            # this also properly tuplefies '*'
            namespace_tuple = ('*', namespace_split[0])
        elif len(namespace_split) is 2:
            namespace_tuple = (namespace_split[0],namespace_split[1])
        else:
            return None
        return namespace_tuple

    ############################################################################
    # Need to add rejection of true regex attempts.
    def _validate_namespaces(self, input_namespaces):
        """Converts a list of db namespaces to a list of namespace tuples,
            supporting basic commandline wildcards"""
        output_namespaces = []
        if input_namespaces == []:
            return output_namespaces
        elif '*' in input_namespaces:
            if len(input_namespaces) > 1:
                warning = 'Warning: Multiple namespaces are '
                warning += 'ignored when one namespace is "*"\n'
                sys.stderr.write(warning)
            return output_namespaces
        else:
            for namespace in input_namespaces:
                if not isinstance(namespace, unicode):
                    namespace = unicode(namespace)
                namespace_tuple = self._tuplefy_namespace(namespace)
                if namespace_tuple is None:
                    warning = 'Warning: Invalid namespace ' + namespace
                    warning += ' will be ignored\n'
                    sys.stderr.write(warning)
                else:
                    if namespace_tuple not in output_namespaces:
                        output_namespaces.append(namespace_tuple)
                    else:
                        warning = 'Warning: Duplicate namespace ' + namespace
                        warning += ' will be ignored\n'
                        sys.stderr.write(warning)
        return output_namespaces

    ############################################################################
    def _namespace_requested(self, namespace):
        """Checks whether the requested_namespaces contain the provided
            namespace"""
        if namespace is None:
            return False
        namespace_tuple = self._tuplefy_namespace(namespace)
        if namespace_tuple[0] in IGNORE_DBS:
            return False
        elif namespace_tuple[1] in IGNORE_COLLECTIONS:
            return False
        else:
            return self._tuple_requested(namespace_tuple)

    ############################################################################
    def _tuple_requested(self, namespace_tuple):
        """Helper for _namespace_requested. Supports limited wildcards"""
        if not isinstance(namespace_tuple[0], unicode):
            encoded_db = unicode(namespace_tuple[0])
        else:
            encoded_db = namespace_tuple[0]
        if not isinstance(namespace_tuple[1], unicode):
            encoded_coll = unicode(namespace_tuple[1])
        else:
            encoded_coll = namespace_tuple[1]

        if namespace_tuple is None:
            return False
        elif len(self._requested_namespaces) is 0:
            return True
        for requested_namespace in self._requested_namespaces:
            if  ((((requested_namespace[0]) == u'*') or
                 (encoded_db == requested_namespace[0])) and
                (((requested_namespace[1]) == u'*') or
                 (encoded_coll == requested_namespace[1]))):
                return True
        return False

    ############################################################################
    def _get_requested_databases(self):
        """Returns a list of databases requested, not including ignored dbs"""
        requested_databases = []
        if ((self._requested_namespaces is not None) and
                (self._requested_namespaces != [])):
            for requested_namespace in self._requested_namespaces:
                if requested_namespace[0] is '*':
                    return []
                elif requested_namespace[0] not in IGNORE_DBS:
                    requested_databases.append(requested_namespace[0])
        return requested_databases

########NEW FILE########
__FILENAME__ = parsers
__author__ = 'eric'

import re
from utils import pretty_json, small_json, yamlfy
from time import strptime, mktime
from datetime import datetime
import traceback

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict


################################################################################
# Query masking and scrubbing functions
################################################################################

def scrub(e):
    if isinstance(e, dict):
        return scrub_doc(e)
    elif isinstance(e, list):
        return scrub_list(e)
    else:
        return None


def scrub_doc(d):
    for k in d:
        if k in ['$in', '$nin', '$all']:
            d[k] = ["<val>"]
        else:
            d[k] = scrub(d[k])
        if d[k] is None:
            d[k] = "<val>"
    return d


def scrub_list(a):
    v = []
    for e in a:
        e = scrub(e)
        if e is not None:
            v.append(scrub(e))
    return sorted(v)


ts_rx = re.compile('^(?P<ts>[a-zA-Z]{3} [a-zA-Z]{3} {1,2}\d+ \d{2}:\d{2}:\d{2}).*')
def get_line_time(line):
    ts = None
    match = ts_rx.match(line)
    if match:
        year = datetime.utcnow().year
        timestamp = mktime(strptime(match.group('ts') + ' ' + str(year), '%a %b %d %H:%M:%S %Y'))
        ts = datetime.fromtimestamp(timestamp)
    return ts


################################################################################
# Parser
#   Provides a parse function that passes input to a round of handlers.
################################################################################
class Parser(object):
    def __init__(self, handlers):
        self._line_handlers = handlers

    def parse(self, input):
        """Passes input to each QueryLineHandler in use"""
        query = None
        for handler in self._line_handlers:
            try:
                query = handler.handle(input)
            except Exception as e:
                query = None
            finally:
                if query is not None:
                    return query
        return None


################################################################################
# ProfileParser
#   Extracts queries from profile entries using a single ProfileEntryHandler
################################################################################
class ProfileParser(Parser):
    def __init__(self):
        """Declares the QueryLineHandlers to use"""
        super(ProfileParser, self).__init__([self.ProfileEntryHandler()])

    def get_line_time(self, input):
        return input['ts'] if 'ts' in input else None

    ############################################################################
    # Base ProfileEntryHandler class
    #   Knows how to yamlfy a logline query
    ############################################################################
    class ProfileEntryHandler:
        ########################################################################
        def handle(self, input):
            result = OrderedDict()
            query = None
            orderby = None

            if (input is not None) and (input.has_key('op')):
                if input['op'] == 'query':
                    if input['query'].has_key('$query'):
                        query = input['query']['$query']
                        if input['query'].has_key('$orderby'):
                            orderby = input['query']['$orderby']
                    else:
                        query = input['query']
                    result['ns'] = input['ns']
                elif input['op'] == 'update':
                    query = input['query']
                    if input.has_key('updateobj'):
                        if input['updateobj'].has_key('orderby'):
                            orderby = input['updateobj']['orderby']
                    result['ns'] = input['ns']
                elif ((input['op'] == 'command') and
                          ((input['command'].has_key('count')) or
                               (input['command'].has_key('findAndModify')))):
                    query = input['command']['query']
                    db = input['ns'][0:input['ns'].rfind('.')]
                    result['ns'] = db + "." + input['command']['count']
                else:
                    return None

                toMask = OrderedDict()

                if orderby is not None:
                    result['orderby'] = orderby
                    toMask['$orderby'] = orderby
                result['query'] = scrub(query)
                toMask['$query'] = query

                result['queryMask'] = small_json(toMask)
                result['stats'] = {'millis': input['millis']}
                return result
            else:
                return None


################################################################################
# LogParser
#   Extracts queries from log lines using a list of QueryLineHandlers
################################################################################
class LogParser(Parser):
    def __init__(self):
        """Declares the QueryLineHandlers to use"""
        super(LogParser, self).__init__([CmdQueryHandler(),
                                         UpdateQueryHandler(),
                                         StandardQueryHandler(),
                                         TimeLineHandler()])


############################################################################
# Base QueryLineHandler class
#   Knows how to yamlfy a logline query
############################################################################
class QueryLineHandler:
    ########################################################################
    def parse_query(self, extracted_query):
        return yamlfy(extracted_query)

    def handle(self, line):

        result = self.do_handle(line)
        if result is not None:
            result['ts'] = get_line_time(line)
            return result

    def do_handle(self, line):
        return None

    def parse_line_stats(self, stat_string):
        line_stats = {}
        split = stat_string.split(" ")

        for stat in split:
            if stat is not "" and stat is not None and stat != "locks(micros)":
                stat_split = stat.split(":")
                if (stat_split is not None) and (stat_split is not "") and (len(stat_split) is 2):
                    try:
                        line_stats[stat_split[0]] = int(stat_split[1])
                    except:
                        pass

        return line_stats

    def standardize_query(self, query_yaml):
        if len(query_yaml.keys()) == 1:
            if '$query' in query_yaml:
                return scrub(query_yaml)
            if 'query' in query_yaml:
                return OrderedDict([('$query', scrub(query_yaml['query']))])

        if len(query_yaml.keys()) == 2:
            query = None
            orderby = None

            if 'query' in query_yaml:
                query = query_yaml['query']
            elif '$query' in query_yaml:
                query = query_yaml['$query']

            if 'orderby' in query_yaml:
                orderby = query_yaml['orderby']
            elif '$orderby' in query_yaml:
                orderby = query_yaml['$orderby']

            if query is not None and orderby is not None:
                return OrderedDict([('$query', scrub(query)),
                                    ('$orderby', orderby)])

        return OrderedDict([('$query', scrub(query_yaml))])



############################################################################
# StandardQueryHandler
#   QueryLineHandler implementation for general queries (incl. getmore)
############################################################################
class StandardQueryHandler(QueryLineHandler):
    ########################################################################
    def __init__(self):
        self.name = 'Standard Query Log Line Handler'
        self._regex = '.*\[(?P<connection>\S*)\] '
        self._regex += '(?P<operation>\S+) (?P<ns>\S+\.\S+) query: '
        self._regex += '(?P<query>\{.*\}) (?P<stats>(\S+ )*)'
        self._regex += '(?P<query_time>\d+)ms'
        self._rx = re.compile(self._regex)

    ########################################################################
    def do_handle(self, input):
        match = self._rx.match(input)
        if match is not None:
            parsed = self.parse_query(match.group('query'))
            if parsed is not None:
                result = OrderedDict()
                scrubbed = self.standardize_query(parsed)
                result['query'] = scrubbed['$query']
                if '$orderby' in scrubbed:
                    result['orderby'] = scrubbed['$orderby']
                result['queryMask'] = small_json(scrubbed)
                result['ns'] = match.group('ns')
                result['stats'] = self.parse_line_stats(match.group('stats'))
                result['stats']['millis'] = match.group('query_time')
                result['supported'] = True
                return result
        return None


############################################################################
# CmdQueryHandler
#   QueryLineHandler implementation for $cmd queries (count, findandmodify)
############################################################################
class CmdQueryHandler(QueryLineHandler):
    ########################################################################
    def __init__(self):
        self.name = 'CMD Log Line Handler'
        self._regex = '.*\[conn(?P<connection_id>\d+)\] '
        self._regex += 'command (?P<db>\S+)\.\$cmd command: '
        self._regex += '(?P<query>\{.*\}) (?P<stats>(\S+ )*)'
        self._regex += '(?P<query_time>\d+)ms'
        self._rx = re.compile(self._regex)

    ########################################################################
    def do_handle(self, input):
        match = self._rx.match(input)
        if match is not None:
            parsed = self.parse_query(match.group('query'))
            if parsed is not None:
                result = OrderedDict()
                result['stats'] = self.parse_line_stats(match.group('stats'))
                result['stats']['millis'] = match.group('query_time')

                command = parsed.keys()[0]

                toMask = OrderedDict()

                result['command'] = command
                result['supported'] = True
                if command.lower() == 'count':
                    result['ns'] = match.group('db') + '.'
                    result['ns'] += parsed[command]
                    query = self.standardize_query(parsed['query'])
                    result['query'] = query['$query']
                    toMask = query
                elif command.lower() == 'findandmodify':
                    if 'sort' in parsed:
                        result['orderby'] = parsed['sort']
                        toMask['$orderby'] = parsed['sort']
                    result['ns'] = match.group('db') + '.'
                    result['ns'] += parsed[command]
                    query = self.standardize_query(parsed['query'])
                    result['query'] = query['$query']
                    if 'sort' in parsed:
                        result['orderby'] = parsed['sort']
                        toMask['$orderby'] = parsed['sort']
                    toMask['$query'] = query
                elif command.lower() == 'geonear':
                    result['ns'] = match.group('db') + '.'
                    result['ns'] += parsed[command]
                    query = self.standardize_query(parsed['search'])
                    result['query'] = query
                    toMask = query
                else:
                    result['supported'] = False
                    result['ns'] = match.group('db') + '.$cmd'

                result['command'] = command
                toMask['$cmd'] = command
                result['queryMask'] = small_json(toMask)

                return result
        return None


############################################################################
# UpdateQueryHandler
#   QueryLineHandler implementation for update queries
############################################################################
class UpdateQueryHandler(QueryLineHandler):
    ########################################################################
    def __init__(self):
        self.name = 'Update Log Line Handler'
        self._regex = '.*\[conn(?P<connection_id>\d+)\] '
        self._regex += 'update (?P<ns>\S+\.\S+) query: '
        self._regex += '(?P<query>\{.*\}) update: (?P<update>\{.*\}) '
        self._regex += '(?P<stats>(\S+ )*)(?P<query_time>\d+)ms'
        self._rx = re.compile(self._regex)

    ########################################################################
    def do_handle(self, input):

        match = self._rx.match(input)
        if match is not None:
            parsed = self.parse_query(match.group('query'))
            if parsed is not None:
                result = OrderedDict()
                scrubbed = self.standardize_query(parsed)
                result['query'] = scrubbed['$query']
                if '$orderby' in scrubbed:
                    result['orderby'] = scrubbed['$orderby']
                result['queryMask'] = small_json(scrubbed)
                result['ns'] = match.group('ns')
                result['stats'] = self.parse_line_stats(match.group('stats'))
                result['stats']['millis'] = match.group('query_time')
                result['supported'] = True
                return result
        return None

############################################################################
# Empty TimeLineHandler class
#   Last Resort for unparsed lines
############################################################################
class TimeLineHandler(QueryLineHandler):
    ########################################################################
    def __init__(self):
        self.name = 'Standard Query Log Line Handler'
        self._regex = '.*(?P<query_time>\d+)ms'
        self._rx = re.compile(self._regex)

    ########################################################################
    def do_handle(self, input):
        match = self._rx.match(input)
        if match is not None:
            return {'ns': "?",
                    'stats': {"millis": match.group('query_time')},
                    'supported': False,
                    'queryMask': None
            }
        return None





########NEW FILE########
__FILENAME__ = test
################################################################################
#
# Copyright (c) 2012 ObjectLabs Corporation
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
################################################################################

import unittest
from test_dex import test_dex

all_suites = [ unittest.TestLoader().loadTestsFromTestCase(test_dex) ]

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(all_suites))

########NEW FILE########
__FILENAME__ = test_dex
################################################################################
#
# Copyright (c) 2012 ObjectLabs Corporation
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
################################################################################

import unittest
import pymongo
import yaml
import sys
from dex import dex
from dex.parsers import Parser, QueryLineHandler, small_json, scrub
from dex.utils import pretty_json
import os
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

TEST_URI = "mongodb://localhost:27017"
TEST_DBNAME = "dex_test"
TEST_COLLECTION = "test_collection"
TEST_LOGFILE = os.path.dirname(__file__) + "/whitebox.log"


class test_dex(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        try:
            cls._connection = pymongo.Connection()
            cls._connection.drop_database(TEST_DBNAME)
            db = cls._connection[TEST_DBNAME]
            collection = db[TEST_COLLECTION]
            cls.parser = TestParser()
                
            collection.create_index("simpleIndexedField")
            collection.create_index([("complexIndexedFieldOne",
                                      pymongo.DESCENDING),
                                     ("complexIndexedFieldTwo",
                                      pymongo.DESCENDING)])
            collection.create_index([("complexIndexedFieldTen",
                                      pymongo.DESCENDING),
                                     ("complexIndexedFieldNine",
                                      pymongo.DESCENDING)])
            collection.create_index([("complexIndexedFieldOne",
                                      pymongo.DESCENDING),
                                     ("complexIndexedFieldTwo",
                                      pymongo.DESCENDING),
                                     ("complexIndexedFieldThree",
                                      pymongo.DESCENDING)])
            collection.create_index([("geoIndexedFieldOne",
                                      pymongo.GEO2D)])
        except:
            raise unittest.SkipTest('You must have a database at ' + TEST_URI + ' to run this test case. Do not run this mongod in --auth mode.')
        else:
            
            pass
    
    @classmethod
    def tearDownClass(cls):
        cls._connection.drop_database(TEST_DBNAME)
        pass
   
    def test_analyze_query(self):
        test_dex = dex.Dex(TEST_URI, False, [], 0, True, 0)
        
        test_query = "{ simpleUnindexedField: null }"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation']['index'], '{"simpleUnindexedField": 1}')
                
        test_query = "{ simpleIndexedField: null }"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation'], None, pretty_json(result))
                
        test_query = "{ simpleUnindexedField: {$lt: 4}}"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation']['index'], '{"simpleUnindexedField": 1}')
                
        test_query = "{ simpleIndexedField:  { $lt: 4 }}"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation'], None)
                
        test_query = "{ $query: {}, $orderby: { simpleUnindexedField }}"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation']['index'], '{"simpleUnindexedField": 1}')
                
        test_query = "{ $query: {}, $orderby: { simpleIndexedField: 1 }}"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation'], None)
                
        test_query = "{complexUnindexedFieldOne: null, complexUnindexedFieldTwo: null }"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation']['index'], '{"complexUnindexedFieldOne": 1, "complexUnindexedFieldTwo": 1}')
        
        test_query = "{ complexIndexedFieldOne: null, complexIndexedFieldTwo: null }"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation'], None)
        self.assertEqual(result['indexAnalysis']['fullIndexes'][0]['index']['key'], [('complexIndexedFieldOne', -1), ('complexIndexedFieldTwo', -1), ('complexIndexedFieldThree', -1)])
                
        test_query = "{ complexUnindexedFieldOne: null, complexUnindexedFieldTwo: { $lt: 4 }}"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation']['index'], '{"complexUnindexedFieldOne": 1, "complexUnindexedFieldTwo": 1}')
        
        test_query = "{ complexIndexedFieldOne: null, complexIndexedFieldTwo: { $lt: 4 }  }"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation'], None, pretty_json(result))
                
        test_query = "{ complexIndexedFieldNine: null, complexIndexedFieldTen: { $lt: 4 }  }"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation']['index'], '{"complexIndexedFieldNine": 1, "complexIndexedFieldTen": 1}')
        
        test_query = "{ $query: {complexUnindexedFieldOne: null}, $orderby: { complexUnindexedFieldTwo: 1 } }"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation']['index'], '{"complexUnindexedFieldOne": 1, "complexUnindexedFieldTwo": 1}')
                
        test_query = "{ $query: {complexIndexedFieldOne: null}, $orderby: { complexIndexedFieldTwo: 1 } }"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation'], None)
        
        test_query = "{ $query: {complexIndexedFieldTen: {$lt: 4}}, $orderby: { complexIndexedFieldNine: 1 } }"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation']['index'], '{"complexIndexedFieldNine": 1, "complexIndexedFieldTen": 1}')
                
        test_query = "{ $query: {complexIndexedFieldThree: null, complexIndexedFieldTwo: {$lt: 4}}, $orderby: { complexIndexedFieldOne: 1 }}"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation']['index'], '{"complexIndexedFieldThree": 1, "complexIndexedFieldOne": 1, "complexIndexedFieldTwo": 1}')
        
        test_query = "{ $query: {complexIndexedFieldOne: null, complexIndexedFieldThree: {$lt: 4}}, $orderby: { complexIndexedFieldTwo: 1 } }"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation'], None)
                
        test_query = "{ $query: { $or: [ { orFieldOne: { $lt: 4 } }, {orFieldTwo: { $gt: 5 } }], complexUnindexedFieldOne: 'A'}, $orderby: { _id: 1 }}"
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation'], None)
        
        test_query = "{ geoIndexedFieldOne: { $near: [50, 50] } } "
        result = test_dex.generate_query_report(TEST_URI,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)        
        self.assertEqual(result['recommendation'], None)
                
    def test_generate_query_analysis(self):
        analyzer = dex.Dex(TEST_URI, False, [], 0, True, 0)._query_analyzer

        analysis = analyzer._generate_query_analysis(self.parser.parse('{ a: null }'), 'db', 'collection')
        self.assertEqual(analysis['fieldCount'], 1)
        self.assertTrue(analysis['supported'])
        self.assertEqual(analysis['analyzedFields'][0]['fieldName'], 'a')
        self.assertEqual(analysis['analyzedFields'][0]['fieldType'], 'EQUIV')
        analysis = analyzer._generate_query_analysis(self.parser.parse('{ a: null , b: { $lt: 4 }}'), 'db', 'collection')
        self.assertEqual(analysis['fieldCount'], 2)
        self.assertTrue(analysis['supported'])
        self.assertEqual(analysis['analyzedFields'][0]['fieldName'], 'a')
        self.assertEqual(analysis['analyzedFields'][0]['fieldType'], 'EQUIV')
        self.assertEqual(analysis['analyzedFields'][1]['fieldName'], 'b')
        self.assertEqual(analysis['analyzedFields'][1]['fieldType'], 'RANGE')
        analysis = analyzer._generate_query_analysis(self.parser.parse('{$query: { a: null , b: { $lt: 4 }}, $orderby: {c: 1}}'), 'db', 'collection')
        self.assertEqual(analysis['fieldCount'], 3)
        self.assertTrue(analysis['supported'])
        self.assertEqual(analysis['analyzedFields'][0]['fieldName'], 'c')
        self.assertEqual(analysis['analyzedFields'][0]['fieldType'], 'SORT')
        self.assertEqual(analysis['analyzedFields'][1]['fieldName'], 'a')
        self.assertEqual(analysis['analyzedFields'][1]['fieldType'], 'EQUIV')
        self.assertEqual(analysis['analyzedFields'][2]['fieldName'], 'b')
        self.assertEqual(analysis['analyzedFields'][2]['fieldType'], 'RANGE')
        analysis = analyzer._generate_query_analysis(self.parser.parse('{$query: { a: null , b: { $lt: 4 }, d: {$near: [50, 50]}}, $orderby: {c: 1}}'), 'db', 'collection')
        self.assertEqual(analysis['fieldCount'], 4)
        self.assertFalse(analysis['supported'])
        self.assertEqual(analysis['analyzedFields'][0]['fieldName'], 'c')
        self.assertEqual(analysis['analyzedFields'][0]['fieldType'], 'SORT')
        self.assertEqual(analysis['analyzedFields'][1]['fieldName'], 'a')
        self.assertEqual(analysis['analyzedFields'][1]['fieldType'], 'EQUIV')
        self.assertEqual(analysis['analyzedFields'][2]['fieldName'], 'b')
        self.assertEqual(analysis['analyzedFields'][2]['fieldType'], 'RANGE')
        self.assertEqual(analysis['analyzedFields'][3]['fieldName'], 'd')
        self.assertEqual(analysis['analyzedFields'][3]['fieldType'], 'UNSUPPORTED')
                
    def test_generate_index_report(self):
        analyzer = dex.Dex(TEST_URI, False, [], 0, True, 0)._query_analyzer

        index = {"key": [ ("complexIndexedFieldOne", -1), ("complexIndexedFieldTwo", -1)],
                 "v": 1}
        analysis = {'supported': True,
                    'analyzedFields': [{'fieldName': 'simpleUnindexedField', 'fieldType': 'EQUIV'}],
                    'fieldCount': 1}
        report = analyzer._generate_index_report(index, analysis)
        self.assertEqual(report['queryFieldsCovered'], 0)
        self.assertEqual(report['index'], index)
        self.assertEqual(report['coverage'], 'none')

        index = {"key": [ ("complexIndexedFieldOne", -1), ("complexIndexedFieldTwo", -1)],
                 "v": 1}
        analysis = {'supported': True,
                    'analyzedFields': [{'fieldName': 'complexIndexedFieldTwo', 'fieldType': 'EQUIV'}],
                    'fieldCount': 1}
        report = analyzer._generate_index_report(index, analysis)
        self.assertEqual(report['queryFieldsCovered'], 0)
        self.assertEqual(report['index'], index)
        self.assertEqual(report['coverage'], 'none')
        
        index = {"key": [ ("complexIndexedFieldOne", -1), ("complexIndexedFieldTwo", -1)],
                 "v": 1}
        analysis = {'supported': True,
                    'analyzedFields': [{'fieldName': 'complexIndexedFieldOne', 'fieldType': 'EQUIV'}],
                    'fieldCount': 1}
        report = analyzer._generate_index_report(index, analysis)
        self.assertEqual(report['queryFieldsCovered'], 1)
        self.assertEqual(report['index'], index)
        self.assertEqual(report['coverage'], 'full')

        index = {"key": [ ("complexIndexedFieldOne", -1), ("complexIndexedFieldTwo", -1)],
                 "v": 1}
        analysis = {'supported': True,
                    'analyzedFields': [{'fieldName': 'complexIndexedFieldTwo', 'fieldType': 'EQUIV'},
                                       {'fieldName': 'complexIndexedFieldOne', 'fieldType': 'RANGE'}],
                    'fieldCount': 2}
        report = analyzer._generate_index_report(index, analysis)
        self.assertEqual(report['queryFieldsCovered'], 2)
        self.assertEqual(report['index'], index)
        self.assertEqual(report['coverage'], 'full')
        self.assertFalse(report['idealOrder'])

        index = {"key": [ ("complexIndexedFieldOne", -1), ("complexIndexedFieldTwo", -1)],
                 "v": 1}
        analysis = {'supported': True,
                    'analyzedFields': [{'fieldName': 'complexIndexedFieldTwo', 'fieldType': 'RANGE'},
                                       {'fieldName': 'complexIndexedFieldOne', 'fieldType': 'EQUIV'}],
                    'fieldCount': 2}
        report = analyzer._generate_index_report(index, analysis)
        self.assertEqual(report['queryFieldsCovered'], 2)
        self.assertEqual(report['index'], index)
        self.assertEqual(report['coverage'], 'full')
        self.assertTrue(report['idealOrder'])

        index = {"key": [ ("complexIndexedFieldOne", -1), ("complexIndexedFieldTwo", -1)],
                 "v": 1}
        analysis = {'supported': True,
                    'analyzedFields': [{'fieldName': 'complexIndexedFieldTwo', 'fieldType': 'RANGE'},
                                       {'fieldName': 'complexIndexedFieldOne', 'fieldType': 'SORT'}],
                    'fieldCount': 2}
        report = analyzer._generate_index_report(index, analysis)
        self.assertEqual(report['queryFieldsCovered'], 2)
        self.assertEqual(report['index'], index)
        self.assertEqual(report['coverage'], 'full')
        self.assertTrue(report['idealOrder'])

    def test_sort_ordering(self):
        test_dex = dex.Dex(TEST_URI, True, [], 0, True, 0)
        report = test_dex._report._reports
        test_query = "{ $query: {}, $orderby: { simpleUnindexedField: null, simpleUnindexedFieldTwo: null  }}"
        result = test_dex.generate_query_report(None,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)
        self.assertEqual(result['recommendation']['index'],
                         '{"simpleUnindexedField": 1, "simpleUnindexedFieldTwo": 1}')

        test_query = "{ $query: {}, $orderby: { simpleUnindexedFieldTwo: null, simpleUnindexedFieldOne: null  }}"
        result = test_dex.generate_query_report(None,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)
        self.assertEqual(result['recommendation']['index'],
                         '{"simpleUnindexedFieldTwo": 1, "simpleUnindexedFieldOne": 1}')

    def test_report_aggregation(self):
        test_dex = dex.Dex(TEST_URI, True, [], 0, True, 0)
        report = test_dex._report._reports

        test_query = "{ simpleUnindexedField: null }"
        result = test_dex.generate_query_report(None,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)
        test_dex._report.add_query_occurrence(result)
        self.assertEqual(len(report), 1)
        self.assertEqual(report[0]['stats']['count'], 1)

        test_query = "{ $query: {}, $orderby: { simpleUnindexedField: null }}"
        result = test_dex.generate_query_report(None,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)
        test_dex._report.add_query_occurrence(result)

        self.assertEqual(len(report), 2)

        test_query = "{ anotherUnindexedField: null }"
        result = test_dex.generate_query_report(None,
                                        self.parser.parse(test_query),
                                        TEST_DBNAME,
                                        TEST_COLLECTION)
        #adding twice for a double query
        test_dex._report.add_query_occurrence(result)
        test_dex._report.add_query_occurrence(result)

        self.assertEqual(len(report), 3)

    if __name__ == '__main__':
        unittest.main()


class TestParser(Parser):
    def __init__(self):
        """Declares the QueryLineHandlers to use"""
        super(TestParser, self).__init__([self.TestHandler()])

    ############################################################################
    # Base QueryLineHandler class
    #   Knows how to yamlfy a logline query
    ############################################################################
    class TestHandler(QueryLineHandler):
        ########################################################################
        def handle(self, input):
            parsed = self.parse_query(input)
            result = OrderedDict()
            if parsed is not None:
                scrubbed = scrub(parsed)
                result['query'] = scrubbed['$query']
                if '$orderby' in scrubbed:
                    result['orderby'] = scrubbed['$orderby']
                result['ns'] = TEST_DBNAME + "." + TEST_COLLECTION
                result['stats'] = {}
                result['stats']['millis'] = 500
                result['queryMask'] = small_json(scrubbed)
                return result
########NEW FILE########
__FILENAME__ = utils
__author__ = 'eric'

import json
from bson import json_util
import yaml
import yaml.constructor
from datetime import datetime, date

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict


################################################################################
# Utilities
################################################################################
def pretty_json(obj):
    return json.dumps(obj, indent=4, default=_custom_json_hook)


def _custom_json_hook(obj):
    if type(obj) in [datetime, date]:
        return {"$date": obj.strftime("%Y-%m-%dT%H:%M:%S.000Z")}
    else:
        return json_util.default(obj)


def validate_yaml(string):
    try:
        yamlfy(string)
    except:
        return False
    else:
        return True


def small_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(',',':'))


def yamlfy(string):
    return yaml.load(string, OrderedDictYAMLLoader)


# From https://gist.github.com/844388
class OrderedDictYAMLLoader(yaml.Loader):
    """
    A YAML loader that loads mappings into ordered dictionaries.
    """

    def __init__(self, *args, **kwargs):
        yaml.Loader.__init__(self, *args, **kwargs)

        self.add_constructor(u'tag:yaml.org,2002:map', type(self).construct_yaml_map)
        self.add_constructor(u'tag:yaml.org,2002:omap', type(self).construct_yaml_map)

    def construct_yaml_map(self, node):
        data = OrderedDict()
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            self.flatten_mapping(node)
        else:
            raise yaml.constructor.ConstructorError(None, None,
                                                    'expected a mapping node, but found %s' % node.id, node.start_mark)

        mapping = OrderedDict()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError, exc:
                raise yaml.constructor.ConstructorError('while constructing a mapping',
                                                        node.start_mark, 'found unacceptable key (%s)' % exc, key_node.start_mark)
            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping

########NEW FILE########
