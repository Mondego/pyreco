__FILENAME__ = api
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
"""
This file serves the ConceptNet 5 JSON API, by connecting to a Solr
index of all of ConceptNet 5.

It was written in Fall 2011 by Julian Chaidez and Rob Speer, and
updated in March 2014 to account for Python 3 and the code refactor.

It should probably be revised more, but there's a good chance that
we will be replacing the Solr index with something else.
"""

# Python 2/3 compatibility
import sys
if sys.version_info.major < 3:
    from urllib import urlencode
    from urllib2 import urlopen
else:
    from urllib.parse import urlencode
    from urllib.request import urlopen

import flask
import re
import json
import os
from werkzeug.contrib.cache import SimpleCache
app = flask.Flask(__name__)

if not app.debug:
    import logging
    file_handler = logging.FileHandler('logs/flask_errors.log')
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

ASSOC_DIR = os.environ.get('CONCEPTNET_ASSOC_DATA') or '../data/assoc/space'
commonsense_assoc = None
def load_assoc():
    """
    Load the association matrix. Requires the open source Python package
    'assoc_space'.
    """
    from assoc_space import AssocSpace
    global commonsense_assoc
    if commonsense_assoc: return commonsense_assoc
    commonsense_assoc = AssocSpace.load_dir(ASSOC_DIR)
    return commonsense_assoc

if len(sys.argv) == 1:
    root_url = 'http://conceptnet5.media.mit.edu/data/5.2'
else:
    root_url = sys.argv[1]

cache_dict = {
    'limit_timeout': 60,
    'limit_amount': 1000
}

request_cache = SimpleCache(threshold=0, default_timeout=cache_dict['limit_timeout'])

def add_slash(uri):
    """
    Ensures that a slash is present in all situations where slashes are
    absolutely necessary for an address.
    """
    if uri[0] == '/':
        return uri
    else:
        return '/' + uri

def request_limit(ip_address, amount=1):
    """
    This function checks the query ip address and ensures that the requests
    from that address have not passed the query limit.
    """
    if request_cache.get(ip_address) > cache_dict['limit_amount']:
        return True, flask.Response(
          response=flask.json.dumps({'error': 'rate limit exceeded'}),
          status=429, mimetype='json')
    else:
        request_cache.inc(ip_address, amount)
        return False, None

@app.route('/<path:query>')
def query_node(query):
    req_args = flask.request.args
    path = '/'+query.strip('/')
    key = None
    if path.startswith('/c/') or path.startswith('/r/'):
        key = 'nodes'
    elif path.startswith('/a/'):
        key = 'uri'
    elif path.startswith('/d/'):
        key = 'dataset'
    elif path.startswith('/l/'):
        key = 'license'
    elif path.startswith('/s/'):
        key = 'sources'
    if key is None:
        flask.abort(404)
    query_args = {key: path}

    # Take some parameters that will be passed on to /search
    query_args['offset'] = req_args.get('offset', '0')
    query_args['limit'] = req_args.get('limit', '50')
    query_args['filter'] = req_args.get('filter', '')
    return search(query_args)

# This is one reason I want to get away from Solr.
LUCENE_SPECIAL_RE = re.compile(r'([-+!(){}\[\]^"~*?:\\])')

def lucene_escape(text):
    text = LUCENE_SPECIAL_RE.sub(r'\\\1', text)
    if ' ' in text:
        return '"%s"' % text
    else:
        return text

PATH_FIELDS = ['id', 'uri', 'rel', 'start', 'end', 'dataset', 'license', 'nodes', 'context', 'sources']
TEXT_FIELDS = ['surfaceText', 'text', 'startLemmas', 'endLemmas', 'relLemmas']
STRING_FIELDS = ['features']

@app.route('/search')
def search(query_args=None):
    limited, limit_response = request_limit(flask.request.remote_addr, 1)
    if limited:
        return limit_response
    if query_args is None:
        query_args = flask.request.args
    query_params = []
    filter_params = []
    sharded = True
    if query_args.get('filter') in ('core', 'core-assertions'):
        # core-assertions is equivalent to core, now that assertions are the
        # only edge-like structures the API returns.
        filter_params.append('license:/l/CC/By')
    for key in PATH_FIELDS:
        if key in query_args:
            val = lucene_escape(query_args.get(key)).rstrip('/')
            query_params.append("%s:%s" % (key, val))
            filter_params.append("%s:%s*" % (key, val))
    for key in TEXT_FIELDS + STRING_FIELDS:
        if key in query_args:
            val = lucene_escape(query_args.get(key)).rstrip('/')
            query_params.append("%s:%s" % (key, val))
    if 'minWeight' in query_args:
        try:
            weight = float(query_args.get('minWeight'))
        except ValueError:
            flask.abort(400)
        filter_params.append("weight:[%s TO *]" % weight)

    params = {}
    params['q'] = u' AND '.join(query_params).encode('utf-8')
    params['fq'] = u' AND '.join(filter_params).encode('utf-8')
    params['start'] = query_args.get('offset', '0')
    params['rows'] = query_args.get('limit', '50')
    params['fl'] = '*,score'
    params['wt'] = 'json'
    params['indent'] = 'on'
    if sharded:
        params['shards'] = 'burgundy.media.mit.edu:8983/solr,claret.media.mit.edu:8983/solr'
    if params['q'] == '':
        return see_documentation()
    return get_query_result(params)

SOLR_BASE = 'http://salmon.media.mit.edu:8983/solr/select?'

def get_link(params):
    return SOLR_BASE + urlencode(params)

def get_query_result(params):
    link = get_link(params)
    fp = urlopen(link)
    obj = json.load(fp)
    #obj['response']['params'] = params
    obj['response']['edges'] = obj['response']['docs']
    del obj['response']['docs']
    del obj['response']['start']
    return flask.jsonify(obj['response'])

@app.route('/')
def see_documentation():
    """
    This function redirects to the api documentation
    """
    return flask.redirect('https://github.com/commonsense/conceptnet5/wiki/API')

@app.errorhandler(404)
def not_found(error):
    return flask.jsonify({
       'error': 'invalid request',
       'details': str(error)
    })

@app.route('/assoc/list/<lang>/<termlist>')
def list_assoc(lang, termlist):
    limited, limit_response = request_limit(flask.request.remote_addr, 10)
    if limited:
        return limit_response
    load_assoc()
    if commonsense_assoc is None:
        flask.abort(404)
    if isinstance(termlist, bytes):
        termlist = termlist.decode('utf-8')

    terms = []
    try:
        term_pieces = termlist.split(',')
        for piece in term_pieces:
            piece = piece.strip()
            if '@' in piece:
                term, weight = piece.split('@')
                weight = float(weight)
            else:
                term = piece
                weight = 1.
            terms.append(('/c/%s/%s' % (lang, term), weight))
    except ValueError:
        flask.abort(400)
    return assoc_for_termlist(terms, commonsense_assoc)

def assoc_for_termlist(terms, assoc):
    limit = flask.request.args.get('limit', '20')
    limit = int(limit)
    if limit > 1000: limit=20

    filter = flask.request.args.get('filter')
    def passes_filter(uri):
        return filter is None or uri.startswith(filter)

    vec = assoc.vector_from_terms(terms)
    similar = assoc.terms_similar_to_vector(vec)
    similar = [item for item in similar if item[1] > 0 and
               passes_filter(item[0])][:limit]

    return flask.jsonify({'terms': terms, 'similar': similar})

@app.route('/assoc/<path:uri>')
def concept_assoc(uri):
    limited, limit_response = request_limit(flask.request.remote_addr, 10)
    if limited:
        return limit_response
    load_assoc()
    uri = '/' + uri.rstrip('/')
    if commonsense_assoc is None:
        flask.abort(404)

    return assoc_for_termlist([(uri, 1.0)], commonsense_assoc)

if __name__ == '__main__':
    app.debug = True
    app.run('127.0.0.1', debug=True, port=8084)

########NEW FILE########
__FILENAME__ = combine_assertions
from __future__ import unicode_literals, print_function
import codecs
from conceptnet5.edges import make_edge
from conceptnet5.uri import disjunction_uri, parse_compound_uri
from conceptnet5.formats.json_stream import JSONStreamWriter
import os
import math

N = 100
CURRENT_DIR = os.getcwd()


def weight_scale(weight):
    """
    Put the weight of an assertion on a log_2 scale.
    """
    return math.log(max(1, weight + 1), 2)


def extract_contributors(source):
    """
    Extract the set of human contributors from a 'source' URI. This is used
    in making sure we haven't duplicated the same person's contribution of
    the same assertion.
    
    This has to happen during the combining step, not when extracting the
    ConceptNet edges in the first place, because the duplicate contributions
    may appear in different files.

    >>> extract_contributors('/s/contributor/omcs/dev')
    {'/s/contributor/omcs/dev'}
    >>> extract_contributors('/and/[/s/contributor/omcs/dev/,/s/activity/omcs1/]')
    {'/s/contributor/omcs/dev'}
    >>> extract_contributors('/s/robot/johnny5')
    set()
    """
    if source.startswith('/s/contributor/'):
        return {source}
    elif source.startswith('/and/'):
        head, items = parse_compound_uri(source)
        return set(item for item in items if item.startswith('/s/contributor/'))
    else:
        return set()


def combine_assertions(csv_filename, output_file, license):
    """
    Take in a tab-separated, sorted "CSV" file, named `csv_filename`, of
    distinct edges which should be grouped together into assertions. Output a
    JSON stream of assertions to `output_file`.

    The combined assertions will all have the dataset of the first edge that
    produces them, and the license of the strongest license being combined
    (which should be passed in as `license`).

    This process requires its input to be a sorted CSV so that all edges for
    the same assertion will appear consecutively.
    """
    # The current_... variables accumulate information about the current
    # assertion. When the URI changes, we can output this assertion.
    current_uri = None
    current_data = {}
    current_contributors = set()
    current_surface = None
    current_dataset = None
    current_weight = 0.
    current_sources = []

    out = JSONStreamWriter(output_file)
    for line in codecs.open(csv_filename, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line:
            continue
        # Interpret the columns of the file.
        parts = line.split('\t')
        (uri, rel, start, end, context, weight, source_uri, id, this_dataset,
         surface) = parts[:10]
        surface = surface.strip()
        weight = float(weight)

        # If the uri is 'uri', this was a header line, which isn't supposed
        # to be there.
        assert uri != 'uri'

        # If the uri is the same as current_uri, accumulate more information.
        if uri == current_uri:
            current_weight += weight
            if source_uri not in current_sources:
                contributors = extract_contributors(source_uri)
                if not contributors & current_contributors:
                    current_sources.append(source_uri)
                    current_contributors |= contributors
            # We use the first surface form we see as the surface form for
            # the whole assertion.
            if (current_surface is None) and surface:
                current_surface = surface


        # Otherwise, it's a new assertion.
        else:
            if current_uri is not None:
                output_assertion(out,
                    dataset=current_dataset, license=license,
                    sources=current_sources,
                    surfaceText=current_surface,
                    weight=weight_scale(current_weight),
                    uri=current_uri,
                    **current_data
                )
            current_uri = uri
            current_data = {
                'rel': rel,
                'start': start,
                'end': end
            }
            current_weight = weight
            current_sources = [source_uri]
            current_contributors = extract_contributors(source_uri)
            current_surface = surface or None
            current_dataset = this_dataset

    if current_uri is not None:
        output_assertion(out,
            rel=rel, start=start, end=end,
            dataset=current_dataset, license=license,
            sources=current_sources,
            surfaceText=current_surface,
            weight=weight_scale(current_weight),
            uri=current_uri
        )


def output_assertion(out, **kwargs):
    """
    Output an assertion to the given output stream. All keyword arguments
    become arguments to `make_edge`. (An assertion is a kind of edge.)
    """
    # Remove the URI, because make_edge computes it for us.
    uri = kwargs.pop('uri')

    # Combine the sources into one AND-OR tree.
    sources = set(kwargs.pop('sources'))
    source_tree = disjunction_uri(*sources)

    # Build the assertion object.
    assertion = make_edge(sources=source_tree, **kwargs)

    # Make sure the computed URI is the same as the one we had.
    assert assertion['uri'] == uri, (assertion['uri'], uri)

    # Output the result in a JSON stream.
    out.write(assertion)


class AssertionCombiner(object):
    """
    A class that wraps the combine_assertions function, so it can be tested in
    the same way as the readers, despite its extra parameters.
    """
    def __init__(self, license):
        self.license = license

    def handle_file(self, input_filename, output_file):
        combine_assertions(input_filename, output_file, self.license)


if __name__ == '__main__':
    # This is the main command-line entry point, used in steps of building
    # ConceptNet that need to combine edges into assertions. See data/Makefile
    # for more context.
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='csv file of input')
    parser.add_argument('output', help='jsons file to output to')
    parser.add_argument('-l', '--license',
        help='URI of the license to use, such as /l/CC/By-SA'
    )
    args = parser.parse_args()
    combiner = AssertionCombiner(args.license)
    combiner.handle_file(args.input, args.output)


########NEW FILE########
__FILENAME__ = distribute_edges
from __future__ import unicode_literals
import sys
import argparse
import codecs

# Get the version of sys.stdin that contains bytes, not Unicode.
if sys.version_info.major >= 3:
    STDIN = sys.stdin.buffer
else:
    STDIN = sys.stdin


class EdgeDistributor(object):
    """
    Takes in lines of a tab-separated "CSV" file, and distributes them
    between `n` output files.

    The file to write to is determined by a hash of the first item in
    the line, so all rows with the same first item will end up in the same
    file, useful if you are about to sort and group by that item.

    In ConceptNet terms, the input file is a listing of edges, and the
    first item in the line is their assertion URI. We can then sort the
    result, and pass it to `conceptnet5.builders.combine_assertions` to
    group edges with the same assertion URI into single assertions.
    """
    def __init__(self, output_dir, n):
        """
        Take in parameters and open the appropriate output files.
        """
        self.n = n
        self.files = [
            codecs.open(output_dir + '/edges_%02d.csv' % i, 'w', encoding='utf-8')
            for i in range(n)
        ]

    def handle_line(self, line):
        """
        Read a line, and split based on the hash of its first item.
        """
        key = line.split('\t', 1)[0]
        bucket = hash(key) % self.n
        self.files[bucket].write(line)

    def close(self):
        """
        Close all the output files when finished.
        """
        for file in self.files:
            file.close()


def run_args():
    """
    Handle command-line arguments, and run the EdgeDistributor on lines read
    from standard input.
    
    Unlike other builder commands, this uses standard input instead of
    taking a filename, because we often simply want to run the output of
    another step through it as a pipe.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', default='./split', help='the directory in which to write output files')
    parser.add_argument('-n', type=int, default=20, help='the number of separate files to write')
    args = parser.parse_args()

    sorter = EdgeDistributor(args.o, args.n)
    for line in STDIN:
        sorter.handle_line(line.decode('utf-8'))

    sorter.close()


if __name__ == '__main__':
    run_args()


########NEW FILE########
__FILENAME__ = json_to_assoc
from __future__ import unicode_literals, print_function
from conceptnet5.uri import join_uri, split_uri
from conceptnet5.formats.json_stream import read_json_stream
import codecs
import json
import sys


def reduce_concept(concept):
    """
    Remove the part of speech and disambiguation (if present) from a concept,
    leaving a potentially ambiguous concept that can be matched against surface
    text.

    Additionally, remove the region tag from Chinese assertions, so they are
    considered simply as assertions about Chinese regardless of whether it is
    Traditional or Simplified Chinese. In the cases where they overlap, this
    helps to make the information more complete.

    >>> reduce_concept('/c/en/cat/n/feline')
    '/c/en/cat'
    >>> reduce_concept('/c/zh_TW/良好')
    '/c/zh/良好'
    """
    parts = split_uri(concept)
    # Unify simplified and traditional Chinese in associations.
    if parts[1] == 'zh_CN' or parts[1] == 'zh_TW':
        parts[1] = 'zh'
    return join_uri(*parts[:3])


def convert_to_assoc(input_filename, output_filename):
    """
    Convert a JSON stream to a tab-separated "CSV" of concept-to-concept associations.

    The relation is mostly ignored, except:

    - Negative relations create associations between concepts suffixed with '/neg'
    - An assertion that means "People want X" in English or Chinese is converted to
      an assertion between X and "good", and also X and the negation of "bad"
    - Combining both of these, an assertion that "People don't want X" moves the
      negation so that X is associated with "not good" and "bad".

    The result can be used to predict word associations using ConceptNet by using
    dimensionality reduction, as in the `assoc_space` package.
    
    The relation is mostly ignored because we have not yet found a good way to
    take the relation into account in dimensionality reduction.
    """
    out_stream = codecs.open(output_filename, 'w', encoding='utf-8')
    
    for info in read_json_stream(input_filename):
        startc = reduce_concept(info['start'])
        endc = reduce_concept(info['end'])
        rel = info['rel']
        weight = info['weight']

        if 'dbpedia' in info['sources'] and '/or/' not in info['sources']:
            # DBPedia associations are still too numerous and too weird to
            # associate.
            continue

        pairs = []
        if startc == '/c/en/person':
            if rel == '/r/Desires':
                pairs = [('/c/en/good', endc), ('/c/en/bad/neg', endc)]
            elif rel == '/r/NotDesires':
                pairs = [('/c/en/bad', endc), ('/c/en/good/neg', endc)]
            else:
                pairs = [(startc, endc)]
        elif startc == '/c/zh/人':
            if rel == '/r/Desires':
                pairs = [('/c/zh/良好', endc), ('/c/zh/不良/neg', endc)]
            elif rel == '/r/NotDesires':
                pairs = [('/c/zh/良好/neg', endc), ('/c/zh/不良', endc)]
            else:
                pairs = [(startc, endc)]
        else:
            negated = (rel.startswith('/r/Not') or rel.startswith('/r/Antonym'))
            if not negated:
                pairs = [(startc, endc)]
            else:
                pairs = [(startc, endc + '/neg'), (startc + '/neg', endc)]

        for (start, end) in pairs:
            line = "%(start)s\t%(end)s\t%(weight)s" % {
                'start': start,
                'end': end,
                'weight': weight,
            }
            print(line, file=out_stream)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='JSON-stream file of input')
    parser.add_argument('output', help='CSV file to output to')
    args = parser.parse_args()
    convert_to_assoc(args.input, args.output)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = json_to_csv
from __future__ import unicode_literals, print_function
from conceptnet5.formats.json_stream import read_json_stream
import codecs


def convert_to_tab_separated(input_filename, output_filename):
    out_stream = codecs.open(output_filename, 'w', encoding='utf-8')
    for info in read_json_stream(input_filename):
        if info['surfaceText'] is None:
            info['surfaceText'] = ''
        info['weight'] = str(info['weight'])
        columns = [
            'uri', 'rel', 'start', 'end', 'context', 'weight', 'source_uri',
            'id', 'dataset', 'surfaceText'
        ]
        column_values = [info.get(col) for col in columns]
        line = '\t'.join(column_values)
        print(line, file=out_stream)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='JSON-stream file of input')
    parser.add_argument('output', help='CSV file to output to')
    args = parser.parse_args()
    convert_to_tab_separated(args.input, args.output)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = json_to_solr
from __future__ import unicode_literals, print_function
from conceptnet5.formats.json_stream import read_json_stream
from conceptnet5.nodes import uri_to_lemmas
import codecs
import json

def convert_to_solr(input_filename, output_filename):
    """
    Convert a JSON stream to a different JSON file that can be loaded into
    Solr.

    A JSON stream differs from standard JSON in that it contains several
    objects separated by line breaks.

    A Solr input file differs from standard JSON in a different way: it is
    represented as a single object with many fields. The values of these
    fields are the various different objects, but the key of each field
    must be "add".

    Having many values with the same key is incompatible with Python
    dictionaries, but is technically allowed by the JSON grammar. To create the
    output JSON file in Python, we have to write its components incrementally.
    """
    out = codecs.open(output_filename, 'w', encoding='utf-8')

    print("{", file=out)
    for info in read_json_stream(input_filename):
        boost = info['weight']

        # Handle searchable lemmas
        info['relLemmas'] = ''
        info['startLemmas'] = ' '.join(uri_to_lemmas(info['start']))
        info['endLemmas'] = ' '.join(uri_to_lemmas(info['end']))

        if boost > 0:
            if 'surfaceText' in info and info['surfaceText'] is None:
                del info['surfaceText']

            solr_struct = {'doc': info, 'boost': boost}
            solr_fragment = '\t"add": %s,' % json.dumps(solr_struct)
            print(solr_fragment, file=out)
    print('\t"commit": {}', file=out)
    print('}', file=out)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='JSON-stream file of input')
    parser.add_argument('output', help='Solr-style JSON file to output to')
    args = parser.parse_args()
    convert_to_solr(args.input, args.output)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = edges
from __future__ import unicode_literals
from hashlib import sha1
from conceptnet5.uri import (conjunction_uri, assertion_uri, Licenses,
                             parse_possible_compound_uri)
from pprint import pprint

def make_edge(rel, start, end, dataset, license, sources,
              context='/ctx/all', surfaceText=None, weight=1.0):
    """
    Take in the information representing an edge (a justified assertion),
    and output that edge in dictionary form.

        >>> e = make_edge(rel='/r/HasProperty',
        ...               start='/c/en/fire',
        ...               end='/c/en/hot',
        ...               dataset='/d/conceptnet/4/en',
        ...               license=Licenses.cc_attribution,
        ...               sources='/and/[/.../]',
        ...               surfaceText='[[Fire]] is [[hot]]',
        ...               weight=1.0)
        >>> pprint(e)
        {'context': '/ctx/all',
         'dataset': '/d/conceptnet/4/en',
         'end': '/c/en/hot',
         'features': ['/c/en/fire /r/HasProperty -',
                      '/c/en/fire - /c/en/hot',
                      '- /r/HasProperty /c/en/hot'],
         'id': '/e/ee13e234ee835eabfcf7c906b358cc2229366b42',
         'license': '/l/CC/By',
         'rel': '/r/HasProperty',
         'source_uri': '/and/[/.../]',
         'sources': ['/...'],
         'start': '/c/en/fire',
         'surfaceText': '[[Fire]] is [[hot]]',
         'uri': '/a/[/r/HasProperty/,/c/en/fire/,/c/en/hot/]',
         'weight': 1.0}
    """
    features = [
        "%s %s -" % (start, rel),
        "%s - %s" % (start, end),
        "- %s %s" % (rel, end)
    ]
    uri = assertion_uri(rel, start, end)
    if isinstance(sources, list):
        source_tree = conjunction_uri(*sources)
        source_list = sources
    else:
        source_tree = sources
        source_list = parse_possible_compound_uri('or', sources)
    
    separate_source_lists = [
        parse_possible_compound_uri('and', source)
        for source in source_list
    ]
    flat_sources = [inner for outer in separate_source_lists
                          for inner in outer]
    flat_sources = sorted(set(flat_sources))

    # Generate a unique ID for the edge. This is the only opaque ID
    # that appears in ConceptNet objects. You can use it as a
    # pseudo-random sort order over edges.
    edge_unique_data = [uri, context, source_tree]
    edge_unique = ' '.join(edge_unique_data).encode('utf-8')
    id = '/e/'+sha1(edge_unique).hexdigest()
    obj = {
        'id': id,
        'uri': uri,
        'rel': rel,
        'start': start,
        'end': end,
        'context': context,
        'dataset': dataset,
        'sources': flat_sources,
        'source_uri': source_tree,
        'features': features,
        'license': license,
        'weight': weight,
        'surfaceText': surfaceText
    }
    return obj

########NEW FILE########
__FILENAME__ = json_stream
from __future__ import print_function, unicode_literals
import json
import sys
import codecs

# Python 2/3 compatibility
if sys.version_info.major >= 3:
    string_type = str
    from io import StringIO
else:
    string_type = basestring
    from StringIO import StringIO


class JSONStreamWriter(object):
    """
    Write a stream of data in "JSON stream" format. This format contains a
    number of JSON objects, separated by line breaks. Line breaks are not
    allowed within a JSON object, which is stricter than the JSON standard.

    The suggested extension for this format is '.jsons'.

    The stream can be specified with a filename, or it can be an existing
    stream such as `sys.stdout`. As a special case, it will not close
    `sys.stdout` even if it's asked to, because that is usually undesired
    and causes things to crash.
    """
    def __init__(self, filename_or_stream):
        if hasattr(filename_or_stream, 'write'):
            self.stream = filename_or_stream
        else:
            self.stream = codecs.open(filename_or_stream, 'w', encoding='utf-8')

    def write(self, obj):
        if isinstance(obj, string_type):
            raise ValueError(
                "%r is already a string. It shouldn't be written to a JSON stream."
                % obj
            )

        line = json.dumps(obj, ensure_ascii=False)
        print(line, file=self.stream)

    def close(self):
        if self.stream is not sys.stdout:
            self.stream.close()


def read_json_stream(filename_or_stream):
    """
    Read a stream of data in "JSON stream" format. Returns a generator of the
    decoded objects.
    """
    if hasattr(filename_or_stream, 'read'):
        stream = filename_or_stream
    else:
        stream = codecs.open(filename_or_stream, encoding='utf-8')
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


########NEW FILE########
__FILENAME__ = semantic_web
# coding: utf-8
from __future__ import print_function, unicode_literals
from conceptnet5.uri import ROOT_URL
import sys
import urllib
import codecs

SEE_ALSO = 'http://www.w3.org/2000/01/rdf-schema#seeAlso'


if sys.version_info.major >= 3:
    unquote = urllib.parse.unquote_to_bytes
    quote = urllib.parse.quote
    urlsplit = urllib.parse.urlsplit
    string_type = str
else:
    import urlparse
    urlsplit = urlparse.urlsplit
    unquote = urllib.unquote
    quote = urllib.quote
    string_type = basestring


def decode_url(url):
    """
    Take in a URL that is percent-encoded for use in a format such as HTML or
    N-triples, and convert it to a Unicode URL.

    If the URL is contained in angle brackets because it comes from an
    N-triples file, strip those.

    >>> decode_url('<http://dbpedia.org/resource/N%C3%BAria_Espert>')
    'http://dbpedia.org/resource/Núria_Espert'
    """
    url_bytes = url.strip('<>').encode('utf-8')
    return unquote(url_bytes).decode('utf-8', 'replace')


def safe_quote(uri):
    """
    Represent a URL in a form that no system should find objectionable.

    Encode non-ASCII characters as UTF-8 and then quote them. Consider
    the special URL characters :, #, and / to be "safe" to represent
    as themselves, because we want them to have their URL meaning.

    This can be used on both DBPedia URLs and ConceptNet URIs.

    >>> safe_quote('http://dbpedia.org/resource/Núria_Espert')
    'http://dbpedia.org/resource/N%C3%BAria_Espert'
    >>> safe_quote('/c/en/Núria_Espert')
    '/c/en/N%C3%BAria_Espert'
    """
    return quote(uri.encode('utf-8'), safe=':#/')


def encode_url(url):
    """
    Reverses the operation of `decode_url` by using percent-encoding and
    surrounding the URL in angle brackets.

    >>> encode_url('http://dbpedia.org/resource/Núria_Espert')
    '<http://dbpedia.org/resource/N%C3%BAria_Espert>'
    """
    return '<%s>' % safe_quote(url)


def resource_name(url):
    """
    Get a concise name for a Semantic Web resource, given its URL.

    This is either the "fragment" identifier, or the path after '/resource/',
    or the item after the final slash.

    There's a special case for '/resource/' because resource names are Wikipedia
    article names, which are allowed to contain additional slashes.

    On a Semantic Web URL, this has the effect of getting an object's effective
    "name" while ignoring the namespace and details of where it is stored.

    >>> resource_name('<http://dbpedia.org/resource/N%C3%BAria_Espert>')
    'Núria_Espert'
    """
    parsed = urlsplit(decode_url(url))
    if parsed.fragment:
        return parsed.fragment
    else:
        path = parsed.path.strip('/')
        if '/resource/' in path:
            return path.split('/resource/')[-1]
        else:
            return path.split('/')[-1]


def full_conceptnet_url(uri):
    """
    Translate a ConceptNet URI into a fully-specified URL.

    >>> full_conceptnet_url('/c/en/dog')
    'http://conceptnet5.media.mit.edu/data/5.2/c/en/dog'
    """
    assert uri.startswith('/')
    return ROOT_URL + safe_quote(uri)


class NTriplesWriter(object):
    """
    Write to a file in N-Triples format.

    N-Triples is a very simple format for expressing RDF relations. It is
    a sequence of lines of the form

    <node1> <relation> <node2> .

    The angle brackets are literally present in the lines, and the things
    they contain are URLs.

    The suggested extension for this format is '.nt'.
    """
    def __init__(self, filename_or_stream):
        if hasattr(filename_or_stream, 'write'):
            self.stream = filename_or_stream
        else:
            self.stream = codecs.open(filename_or_stream, 'w', encoding='ascii')
        self.seen = set()

    def write(self, triple):
        """
        Write a triple of (node1, rel, node2) to a file, if it's not already
        there.
        """
        if triple not in self.seen:
            self.seen.add(triple)
            line_pieces = [encode_url(item) for item in triple] + ['.']
            line = ' '.join(line_pieces)
            print(line, file=self.stream)

    def write_link(self, node1, node2):
        """
        Write a line expressing that node1 is linked to node2, using the RDF
        "seeAlso" property.
        """
        self.write((node1, SEE_ALSO, node2))

    def close(self):
        if self.stream is not sys.stdout:
            self.stream.close()


class NTriplesReader(object):
    """
    A class for reading multiple files in N-Triples format, keeping track of
    prefixes that they define and expanding them when they appear.
    """
    def __init__(self):
        self.prefixes = {}

    def parse_file(self, filename):
        for line in codecs.open(filename, encoding='utf-8'):
            line = line.strip()
            if line:
                result = self.parse_line(line)
                if result is not None:
                    yield result

    def parse_line(self, line):
        subj, rel, objdot = line.split(' ', 2)
        obj, dot = objdot.rsplit(' ', 1)
        assert dot == '.'
        if subj == '@prefix':
            # Handle prefix definitions, which are lines that look like:
            # @prefix wn30: <http://purl.org/vocabularies/princeton/wn30/> .
            prefix = rel
            prefixname = prefix.rstrip(':')
            self.prefixes[prefixname] = decode_url(obj)
            return None
        else:
            # We assume that `subj` and `rel` are URLs, or can be treated as URLs.
            # `obj` might be a literal text, however, so we need to actually look
            # at what it's tagged with.
            subj_url = self.resolve_node(subj)[1]
            rel_url = self.resolve_node(rel)[1]
            obj_tag, obj_url = self.resolve_node(obj)
            return subj_url, rel_url, obj_url, obj_tag

    def resolve_node(self, node_text):
        """
        Given a Semantic Web node expressed in the N-Triples syntax, expand
        it to either its full, decoded URL or its natural language text
        (whichever is appropriate).

        Returns (lang, text), where `lang` is a language code or the string 'URL'.
        If `lang` is 'URL', the `text` is the expanded, decoded URL.

        >>> reader = NTriplesReader()
        >>> reader.parse_line('@prefix wn30: <http://purl.org/vocabularies/princeton/wn30/> .')
        >>> reader.resolve_node('wn30:synset-Roman_alphabet-noun-1')
        ('URL', 'http://purl.org/vocabularies/princeton/wn30/synset-Roman_alphabet-noun-1')
        >>> reader.resolve_node('<http://purl.org/vocabularies/princeton/wn30/>')
        ('URL', 'http://purl.org/vocabularies/princeton/wn30/')
        >>> reader.resolve_node('"Abelian group"@en-us')
        ('en', 'Abelian group')
        """
        if node_text.startswith('<') and node_text.endswith('>'):
            # This is a literal URL, so decode_url will handle it directly.
            return 'URL', decode_url(node_text)
        elif node_text.startswith('"'):
            if '"^^' in node_text:
                quoted_string, type_tag = node_text.rsplit('^^', 1)
                type_tag = resource_name(decode_url(type_tag))
                assert quoted_string.startswith('"') and quoted_string.endswith('"')
                return type_tag, quoted_string[1:-1]
            elif '@' in node_text:
                quoted_string, lang_code = node_text.rsplit('@', 1)
                assert quoted_string.startswith('"') and quoted_string.endswith('"')
                lang = lang_code.split('-')[0]
                return lang, quoted_string[1:-1]
            else:
                raise ValueError("Can't understand value: %s" % node_text)
        elif ':' in node_text:
            prefix, resource = node_text.split(':', 1)
            if prefix not in self.prefixes:
                raise KeyError("Unknown prefix: %r" % prefix)
            url_base = self.prefixes[prefix]
            return 'URL', decode_url(url_base + resource)
        else:
            return (None, node_text)

########NEW FILE########
__FILENAME__ = nodes
from __future__ import unicode_literals
"""
This module constructs URIs for nodes (concepts) in various languages. This
puts the tools in conceptnet5.uri together with stemmers that reduce words
to a root form.

Currently, the only stemmer we use is Morphy, the built-in stemmer in WordNet,
which we apply to English concept names. Other languages are left alone.

The advantage of using Morphy is that its intended output is WordNet 3 lemmas,
a well-established set of strings. Other stemmers present a moving target that
is harder to define.
"""

from metanl.nltk_morphy import normalize as normalize_english
from conceptnet5.uri import normalize_text, concept_uri, split_uri, BAD_NAMES_FOR_THINGS


def normalized_concept_name(lang, text):
    """
    Make a normalized form of the given text in the given language. If the
    language is English, reduce words to their root form using metanl's
    implementation of Morphy. Otherwise, simply apply the function called
    `conceptnet5.uri.normalize_text`.

    >>> normalized_concept_name('en', 'this is a test')
    'this_be_test'
    >>> normalized_concept_name('es', 'ESTO ES UNA PRUEBA')
    'esto_es_una_prueba'
    """
    if lang == 'en':
        stem = normalize_english(text) or text
        return normalize_text(stem)
    else:
        return normalize_text(text)


def normalized_concept_uri(lang, text, *more):
    """
    Make the appropriate URI for a concept in a particular language, including
    stemming the text if necessary, normalizing it, and joining it into a
    concept URI.

    Items in 'more' will not be stemmed, but will go through the other
    normalization steps.

    >>> normalized_concept_uri('en', 'this is a test')
    '/c/en/this_be_test'
    >>> normalized_concept_uri('en', 'this is a test', 'n', 'example phrase')
    '/c/en/this_be_test/n/example_phrase'
    """
    norm_text = normalized_concept_name(lang, text)
    more_text = [normalize_text(item) for item in more]
    return concept_uri(lang, norm_text, *more_text)


def uri_to_lemmas(uri):
    """
    Given a normalized concept URI, extract the list of words (in their root
    form) that it contains in its text.

    >>> # This is the lemmatized concept meaning 'United States'
    >>> uri_to_lemmas('/c/en/unite_state')
    ['unite', 'state']
    >>> uri_to_lemmas('/c/en/township/n/united_states')
    ['township', 'unite', 'state']
    """
    uri_pieces = split_uri(uri)
    lemmas = uri_pieces[2].split('_')
    if len(uri_pieces) >= 5:
        lang = uri_pieces[1]
        text = uri_pieces[4].replace('_', ' ')
        if text not in BAD_NAMES_FOR_THINGS:
            disambig = normalized_concept_name(lang, text)
            lemmas.extend(disambig.split('_'))
    return lemmas


########NEW FILE########
__FILENAME__ = conceptnet4
from __future__ import unicode_literals
"""
This script reads the ConceptNet 4 data out of the flat files in raw_data,
and builds ConceptNet 5 edges from the data.
"""

from conceptnet5.formats.json_stream import JSONStreamWriter, read_json_stream
from conceptnet5.nodes import normalized_concept_uri
from conceptnet5.edges import make_edge
from conceptnet5.uri import join_uri, Licenses, normalize_text, BAD_NAMES_FOR_THINGS

# bedume is a prolific OMCS contributor who seemed to go off the rails at some
# point, adding lots of highly correlated nonsense assertions. We need to
# filter them out without losing his informative statements.

BEDUME_FLAGGED_CONCEPTS = [
  'cute', 'lose', 'sew', 'brat', 'work', 'sex', 'shop', 'drive to work',
  'type', 'in jail', 'jog in park', 'wash his car', 'poor', 'pull weed',
  'dance', 'sleep', 'pout', 'rake leave', 'wash her car', 'chop wood',
  'write book', 'shout', 'take out garbage', 'it', 'cry', 'run', 'cook',
  'late', 'happy', 'eat', 'afraid', 'vote', 'thief', 'shovel snow',
  'drink', 'drunk', 'watch tv', 'nut', 'early', 'well', 'ill', 'jog',
  'dead', 'naked', 'play card', 'sick', 'paint', 'read', 'hunter',
  'play monopoly', 'build new house', 'ride horse', 'play in football game',
  'make love', 'knit', 'go to take vacation', 'fish', 'go to dentist',
  'go to store', 'go to airport', 'go to go to store', 'kid', 'computer',
  'stew', 'take walk', 'tire', 'new computer', 'horn', 'serve mealfish',
  'potatoe shed', 'hunt', 'crazy', 'buy new car', 'laugh', 'intoxicated',
  'intoxicate', 'eat hamburger', 'wok'
]
BEDUME_FLAGGED_PLACES = [
  'alaska', 'kansa', 'utah', 'austria', 'delaware', 'pennsylvania', 'italy',
  'cuba', 'norway', 'idaho', 'france', 'utha', 'mexico', 'connecticut',
  'massachusetts', 'montana', 'wyoming', 'every state', 'new york', 'maine',
  'suface of moon', 'germany', 'nebraska', 'finland', 'louisiana', 'belgium',
  'morrocco', 'ireland', 'ceylon', 'california', 'oregon', 'florida',
  'uraguay', 'egypt', 'maryland', 'washington', 'morocco', 'south dakota',
  'tuscon', 'panama', 'alberta', 'arizona', 'texas', 'new jersey', 'colorado',
  'jamaica', 'vermont', 'nevada', 'delawere', 'hawaii', 'minnesota', 'tuscony',
  'costa rica', 'south dakato', 'south dakota', 'china', 'argentina',
  'venazuela', 'honduras', 'opera', 'wisconsin', 'great britain',
]
AROUND_PREPOSITIONS = [
  'in', 'on', 'at', 'under', 'near'
]


def can_skip(parts_dict):
    """
    Skip the kinds of data that we don't want to import from ConceptNet 4's
    database dump.

    The activity called 'testing' was actually collecting preliminary data for
    a dataset about subjective medical experiences. This data looks really out
    of place now.
    """
    lang = parts_dict['lang']
    if lang.startswith('zh'):
        # Chinese assertions from GlobalMind are not reliable enough. We'll get
        # Chinese from the `ptt_petgame` module instead.
        return True
    if lang == 'ja' and parts_dict["activity"] != 'nadya.jp':
        # Use Japanese data collected from nadya.jp, but not earlier attempts.
        return True
    if parts_dict["goodness"] < 1:
        return True
    if 'spatial concept' in parts_dict["startText"]:
        return True
    if not parts_dict["startText"] or not parts_dict["endText"]:
        return True
    if 'rubycommons' in parts_dict["activity"]:
        return True
    if 'Verbosity' in parts_dict["activity"]:
        return True
    if 'testing' in parts_dict["activity"]:
        return True
    if (
        parts_dict["startText"].strip() in BAD_NAMES_FOR_THINGS or
        parts_dict["endText"].strip() in BAD_NAMES_FOR_THINGS
    ):
        return True
    return False


def build_frame_text(parts_dict):
    """
    Make a ConceptNet 5 surfaceText out of the ConceptNet 4 assertion's
    frame and surface texts.
    """
    frame_text = parts_dict["frame_text"]
    # Mark frames where {2} precedes {1} with an asterisk.
    if frame_text.find('{1}') > frame_text.find('{2}'):
        frame_text = '*' + frame_text
    polarity = parts_dict["polarity"]

    # If this is a negative frame, then it should either have the negative
    # phrasing baked in, or (in English) the symbol {%} where we can insert
    # the word "not".
    if polarity > 0:
        frame_text = frame_text.replace('{%}', '')
    else:
        frame_text = frame_text.replace('{%}', 'not ')
    frame_text = frame_text.replace('{1}', '[[%s]]' % parts_dict["startText"]).replace('{2}', '[[%s]]' % parts_dict["endText"])
    return frame_text


def build_relation(parts_dict):
    """
    Update relation names to ConceptNet 5's names. Mostly we preserve the same
    names, but any instance of "ConceptuallyRelatedTo" becomes "RelatedTo".
    Statements with negative polarity get new negative relations.
    """
    relname = parts_dict["relname"]
    polarity = polarity = parts_dict["polarity"]
    if relname == 'ConceptuallyRelatedTo':
        relname = 'RelatedTo'

    if polarity > 0:
        relation = join_uri('/r', relname)
    else:
        relation = join_uri('/r', 'Not' + relname)

    return relation


def build_start(parts_dict):
    lang = parts_dict['lang']
    startText = parts_dict["startText"]
    start = normalized_concept_uri(lang, startText)
    return start


def build_end(parts_dict):
    lang = parts_dict['lang']
    endText = parts_dict["endText"]
    end = normalized_concept_uri(lang, endText)
    return end


def build_data_set(parts_dict):
    lang = parts_dict['lang']
    dataset = join_uri('/d/conceptnet/4', lang)
    return dataset


def build_sources(parts_dict, preposition_fix=False):
    """
    Create the 'source' information for an assertion.

    The output is a list of (conjunction, weight) tuples, where 'conjunction'
    is a list of sources that combined to produce this assertion. Later,
    inside the 'make_edge' function, these will be combined into an '/and'
    node.
    """
    activity = parts_dict["activity"]

    creator_node = join_uri('/s/contributor/omcs', parts_dict["creator"])
    activity_node = join_uri('/s/activity/omcs', normalize_text(activity))
    if preposition_fix:
        conjunction = [creator_node, activity_node, '/s/rule/preposition_fix']
    else:
        conjunction = [creator_node, activity_node]
    weighted_sources = [(conjunction, 1)]

    for vote in parts_dict["votes"]:
        username = vote[0]
        vote_int = vote[1]
        conjunction = [
            join_uri('/s/contributor/omcs', username),
            '/s/activity/omcs/vote'
        ]
        weighted_sources.append((conjunction, vote_int))
    return weighted_sources


def by_bedume_and_bad(source_list,start,end):
    if 'bedume' in ' '.join(source_list):
        for flagged in BEDUME_FLAGGED_CONCEPTS + BEDUME_FLAGGED_PLACES:
            check = '/'+flagged.replace(' ', '_')
            if start.endswith(check) or end.endswith(check):
                return True
    return False


class CN4Builder(object):
    def __init__(self):
        self.seen_sources = set()

    def handle_assertion(self, parts_dict):
        """
        Process one assertion from ConceptNet 4, which appears in the input
        file as a dictionary.

        Use the 'raw' text -- the text that's not yet reduced to a normalized
        form -- so we can run ConceptNet 5's normalization on it instead.

        Each assertion becomes a number of ConceptNet 5 edges, which will
        probably be grouped together into an assertion again.
        """
        if can_skip(parts_dict):
            return

        # fix the result of some process that broke prepositions ages ago
        preposition_fix = False
        if '} around {' in parts_dict['frame_text']:
            for prep in AROUND_PREPOSITIONS:
                if parts_dict['endText'].startswith(prep + ' '):
                    parts_dict['endText'] = \
                        parts_dict['endText'][len(prep) + 1:]
                    replacement = '} %s {' % prep
                    parts_dict['frame_text'] = \
                        parts_dict['frame_text'].replace(
                            '} around {',
                            replacement
                        )
                    preposition_fix = True
                    break

        if can_skip(parts_dict):
            return
        
        # build the assertion
        frame_text = build_frame_text(parts_dict)
        relation = build_relation(parts_dict)
        start = build_start(parts_dict)
        end = build_end(parts_dict)
        dataset = build_data_set(parts_dict)
        weighted_sources = build_sources(parts_dict, preposition_fix)

        for source_list, weight in weighted_sources:
            if 'commons2_reject' in ' '.join(source_list):
                return

        for source_list, weight in weighted_sources:
            if not by_bedume_and_bad(source_list, start, end):
                yield make_edge(
                    rel=relation, start=start, end=end,
                    dataset=dataset, license=Licenses.cc_attribution,
                    sources=source_list, surfaceText=frame_text,
                    weight=weight
                )


    def transform_file(self, input_filename, output_file):
        out = JSONStreamWriter(output_file)
        for obj in read_json_stream(input_filename):
            for new_obj in self.handle_assertion(obj):
                out.write(new_obj)


def handle_file(input_filename, output_file):
    builder = CN4Builder()
    builder.transform_file(input_filename, output_file)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='JSON-stream file of input')
    parser.add_argument('output', help='JSON-stream file to output to')
    args = parser.parse_args()
    handle_file(args.input, args.output)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = dbpedia
from __future__ import unicode_literals, print_function
"""
Get data from DBPedia.
"""

__author__ = 'Justin Venezuela (jven@mit.edu), Rob Speer (rspeer@mit.edu)'

from metanl.token_utils import un_camel_case
from conceptnet5.uri import Licenses
from conceptnet5.nodes import normalized_concept_uri
from conceptnet5.edges import make_edge
from conceptnet5.formats.json_stream import JSONStreamWriter
from conceptnet5.formats.semantic_web import NTriplesWriter, NTriplesReader, full_conceptnet_url, resource_name
import urllib
import sys
import re


# Python 2/3 compatibility
if sys.version_info.major >= 3:
    quote = urllib.parse.quote
    urlsplit = urllib.parse.urlsplit
else:
    import urlparse
    urlsplit = urlparse.urlsplit
    quote = urllib.quote


# We're going to be building a mapping from Semantic Web URIs to ConceptNet
# URIs. This set keeps track of the ones we already used, so we don't have to
# output them again.
def parse_topic_name(text):
    """
    Get a canonical representation of a Wikipedia topic, which may include
    a disambiguation string in parentheses.

    Returns a list of URI pieces, which could be simply [name], or
    [name, pos], or [name, pos, disambiguation].
    """
    # Convert space-substitutes to spaces, and eliminate redundant spaces
    text = text.replace('_', ' ')
    while '  ' in text:
        text = text.replace('  ', ' ')
    # Find titles of the form "Topic (disambiguation)"
    match = re.match(r'([^(]+) \((.+)\)', text)
    if not match:
        return [text]
    else:
        # Assume all topics are nouns
        return [match.group(1), 'n', match.group(2).strip(' ')]


def translate_dbpedia_url(url, lang='en'):
    """
    Convert an object that's defined by a DBPedia URL to a ConceptNet
    URI. We do this by finding the part of the URL that names the object,
    and using that as surface text for ConceptNet.

    This is, in some ways, abusing a naming convention in the Semantic Web.
    The URL of an object doesn't have to mean anything at all. The
    human-readable name is supposed to be a string, specified by the "name"
    relation.

    The problem here is that the "name" relation is not unique in either
    direction. A URL can have many names, and the same name can refer to
    many URLs, and some of these names are the result of parsing glitches.
    The URL itself is a stable thing that we can build a ConceptNet URI from,
    on the other hand.
    """
    # Some Semantic Web URLs are camel-cased. ConceptNet URIs use underscores
    # between words.
    pieces = parse_topic_name(resource_name(url))
    pieces[0] = un_camel_case(pieces[0])
    return normalized_concept_uri(lang, *pieces)


def map_dbpedia_relation(url):
    """
    Recognize three relations that we can extract from DBPedia, and convert
    them to ConceptNet relations.

    >>> map_dbpedia_relation('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')
    '/r/IsA'
    >>> map_dbpedia_relation('http://dbpedia.org/ontology/location')
    '/r/AtLocation'
    """
    name = resource_name(url)
    if name == 'type':
        return '/r/IsA'
    elif name.startswith('isPartOf'):
        return '/r/PartOf'
    elif name.startswith('location'):
        return '/r/AtLocation'
    else:
        return None


def handle_file(filename, output_file, sw_map_file):
    reader = NTriplesReader()
    out = JSONStreamWriter(output_file)
    map_out = NTriplesWriter(sw_map_file)
    for line in open(filename, 'rb'):
        handle_triple(line.decode('utf-8').strip(), reader, out, map_out)


def handle_triple(line, reader, out, map_out):
    subj, pred, obj, tag = reader.parse_line(line)
    if tag != 'URL':
        return

    # Ignore types of edges that we don't care about:
    #   - Homepage links
    #   - GIS features
    #   - Assertions that something "is a thing"
    #   - Anonymous nodes identified with double-underscores, such as the node
    #     "Alfred_Nobel__1", which means "Alfred Nobel's occupation, whatever
    #     it is"
    #   - Nodes that are articles named "List of X" on Wikipedia
    if ('foaf/0.1/homepage' in pred or '_Feature' in obj or '#Thing' in obj or
        '__' in subj or '__' in obj or 'List_of' in subj or 'List_of' in obj):
        return

    # We don't try to parse URIs from outside of dbpedia.org's namespace.
    if 'dbpedia.org' not in obj:
        return

    subj_concept = translate_dbpedia_url(subj, 'en')
    obj_concept = translate_dbpedia_url(obj, 'en')

    # DBPedia categorizes a lot of things as 'works', which causes unnecessary
    # ambiguity. Disregard these edges; there will almost always be a more
    # specific edge calling it a 'creative work' anyway.
    if obj_concept == '/c/en/work':
        return

    rel = map_dbpedia_relation(pred)
    if rel is None:
        return

    # We've successfully converted this Semantic Web triple to ConceptNet URIs.
    # Now write the results to the 'sw_map' file so others can follow this
    # mapping.
    mapped_pairs = [
        (pred, rel),
        (subj, subj_concept),
        (obj, obj_concept)
    ]
    for sw_url, conceptnet_uri in mapped_pairs:
        conceptnet_url = full_conceptnet_url(conceptnet_uri)
        map_out.write_link(conceptnet_url, sw_url)

    edge = make_edge(rel, subj_concept, obj_concept,
                     dataset='/d/dbpedia/en',
                     license=Licenses.cc_sharealike,
                     sources=['/s/dbpedia/3.7'],
                     weight=0.5)

    out.write(edge)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='JSON-stream file of input')
    parser.add_argument('output', help='JSON-stream file to output to')
    parser.add_argument('sw_map', help='A .nt file of Semantic Web equivalences')
    args = parser.parse_args()
    handle_file(args.input, args.output, args.sw_map)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = extract_wiktionary
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# A work in progress on a better first step for reading Wiktionary.
# Right now it puts its results into a bunch of files under "./en.wiktionary.org".
#
# TODO: when extracting links, try to determine what language they're in. It's
# annoying because it differs by section, and even by template:
#   {{sl-adv|head=[[na]] [[primer]]}}\n\n# [[for example]]

from xml.sax import ContentHandler, make_parser
from xml.sax.handler import feature_namespaces
import re
import os
import unicodedata
import json
from ftfy import ftfy
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SECTION_HEADER_RES = {}
for level in range(2, 8):
    equals = '=' * level
    regex = re.compile(
        r'''
        ^{equals}            # N equals signs, after start or newline
        \s*                  # There might be whitespace around the section title
        ([^=]+?)             # The section title, with no more = signs
        \s*
        {equals}\s           # End with N more equals signs and whitespace
        '''.format(equals=equals),
        # This is a verbose regex (ignore spaces and comments); this is a
        # multiline regex (the ^ should match any line start as well as the
        # start of the string)
        re.VERBOSE | re.MULTILINE
    )
    SECTION_HEADER_RES[level] = regex

# Match wikilinks. Deliberately fail to match links with colons in them,
# because those tend to be internal bookkeeping, or inter-wiki links of the
# non-translation kind.
#
# The match result contains two-item tuples, of which the first item is the
# link target.
WIKILINK_RE = re.compile(
    r'''
    \[\[                  # Wiki links begin with two left brackets.
    (                     # Match the link target:
        [^\[\]\|\{\}:]    #   The target doesn't contain other link syntax.
                          #   (We also don't like links with colons.)
    +?)                   # Match this part as tightly as possible.
    (                     # There might be a separate text to display:
        \|                #   It's separated by a vertical bar.
        [^\[\]]+          #   After that, there are non-bracket characters.
    )?                    # But this part is optional.
    \]\]                  # Finally, end with two right brackets.
    ''', re.VERBOSE
)
TRANSLATION_RE = re.compile(
    r'''
    \{\{                  # Translation templates start with two left braces.
    t.?.?                 # The template name is 1-3 chars starting with 't'.
    \|                    # A vertical bar terminates the template name.
    ([a-z]+)              # The first parameter is the language code. Match it.
    \|
    (.+?)                 # The second parameter is the target word. Match it.
    (?:                   # Throw away the following match:
        \|                #   There might be more parameters. It might be the
    |   \}\}              #   end of the template. We don't actually care. So
    )                     #   match a vertical bar or two right braces.
    ''', re.VERBOSE
)

TRANS_DIVIDER_RE = re.compile(
    r'''
    \{\{ 
    (check)?trans-       # Template names start with 'trans-' or 'checktrans-'.
    (top|bottom)         # We care when they're 'top' or 'bottom'.
    (
      \|(.*?)            # The template might take an optional parameter.
    )?
    \}\}                 # End with two right braces.
    ''', re.VERBOSE
)

SENSE_RE = re.compile(r'\{\{sense\|(.*?)\}\}')

def safe_path_component(text):
    return text.replace('/', '_').replace(' ', '_').replace(':',
        '_').replace('!', '_')

def fix_heading(heading):
    return ftfy(heading).strip('[]')

def safe_path(origtitle):
    title = safe_path_component(ftfy(origtitle))
    
    if len(title) == 0:
        title = origtitle = u'_'

    if title.startswith(u'-') or title.startswith(u'.'):
        title = u'_' + title
    try:
        charname = safe_path_component(unicodedata.name(origtitle[0]))
    except ValueError:
        charname = u'UNKNOWN'
    category = charname.split('_')[0]

    # some ridiculous stuff to give every article a unique name that can be
    # stored on multiple file systems and tab-completed
    if len(origtitle) == 1:
        pieces = [u'single_character', category, charname + '.json']
    else:
        try:
            charname2 = safe_path_component(unicodedata.name(origtitle[1]))
        except ValueError:
            charname2 = u'UNKNOWN'
        text_to_encode = unicodedata.normalize("NFKD", safe_path_component(title[:64]))
        finalpart = text_to_encode.encode('punycode').rstrip('-')
        pieces = [charname, charname2, finalpart + '.json']
    path = u'/'.join(pieces)
    return path
    

class ExtractPages(ContentHandler):
    def __init__(self, callback):
        self.in_article = False
        self.in_title = False
        self.cur_title = ''
        self.callback = callback

    def startElement(self, name, attrs):
        if name == 'text':
            self.in_article = True
            self.cur_text = []
        elif name == 'title':
            self.in_title = True
            self.cur_title = ''

    def endElement(self, name):
        if name == 'text':
            self.in_article = False
        elif name == 'title':
            self.in_title = False
        elif name == 'page':
            self.callback(self.cur_title, ''.join(self.cur_text))
    
    def characters(self, text):
        if self.in_title:
            self.cur_title += text
        elif self.in_article:
            self.cur_text.append(text)
            if len(self.cur_text) > 100000:
                # bail out
                self.in_article = False

def handle_page(title, text, site='en.wiktionary.org'):
    if ':' not in title:
        found = SECTION_HEADER_RES[2].split(text)
        headings = found[1::2]
        texts = found[2::2]
        for heading, text in zip(headings, texts):
            heading = fix_heading(heading)
            handle_language_section(site, title, heading, text)

def handle_language_section(site, title, heading, text):
    path = u'/'.join([site, safe_path_component(heading), safe_path(title)]).encode('utf-8')
    try:
        os.makedirs(os.path.dirname(path))
    except OSError:
        pass
    sec_data = handle_section(text, heading, level=2)
    data = {
        'site': site,
        'language': sec_data['heading'],
        'title': title,
        'sections': sec_data['sections']
    }
    jsondata = json.dumps(data, ensure_ascii=False, indent=2)
    out = open(path, 'w')
    out.write(jsondata.encode('utf-8'))
    out.close()
    

def handle_section(text, heading, level):
    section_finder = SECTION_HEADER_RES[level + 1]
    found = section_finder.split(text)
    headings = found[1::2]
    texts = found[2::2]
    data = {
        'heading': heading,
        'text': found[0].strip(),
        'sections': [handle_section(text2, heading2, level + 1)
                     for (text2, heading2) in zip(texts, headings)]
    }
    if heading == 'Translations':
        data['translations'] = extract_translations(found[0])
    else:
        data['links'] = parse_links(found[0])
        #data['sense'] = find_sense(found[0])
    return data


def parse_links(text):
    return [found[0] for found in WIKILINK_RE.findall(text)]


def extract_translations(text):
    translations = []
    pos = 0
    disambig = None
    in_trans_block = False
    while True:
        # Find whether the next relevant template tag is an individual
        # translation, or a divider between translation sections
        translation_match = TRANSLATION_RE.search(text, pos)
        divider_match = TRANS_DIVIDER_RE.search(text, pos)
        use_translation_match = None
        use_divider_match = None
        if translation_match is not None:
            if divider_match is not None:
                if translation_match.start() < divider_match.start():
                    use_translation_match = translation_match
                else:
                    use_divider_match = divider_match
            else:
                use_translation_match = translation_match
        else:
            use_divider_match = divider_match

        if use_divider_match is not None:
            match = use_divider_match
            pos = match.end()
            tagtype = match.group(2)
            if tagtype == 'top':
                if in_trans_block:
                    logger.warn(
                        u'starting a new trans block on top of an old one: '
                        u'\n%s' % text
                    )
                in_trans_block = True
                disambig = match.group(4)
            elif tagtype == 'bottom':
                in_trans_block = False
                disambig = None

        elif use_translation_match is not None:
            match = use_translation_match
            pos = match.end()
            translations.append({
                'langcode': match.group(1),
                'word': match.group(2),
                'disambig': disambig
            })
        else:
            return translations


def parse_wiktionary_file(filename):
    # Create a parser
    parser = make_parser()

    # Tell the parser we are not interested in XML namespaces
    parser.setFeature(feature_namespaces, 0)

    # Create the handler
    dh = ExtractPages(handle_page)

    # Tell the parser to use our handler
    parser.setContentHandler(dh)

    # Parse the input
    parser.parse(open(filename))

if __name__ == '__main__':
    parse_wiktionary_file('../../data/raw/wiktionary/enwiktionary.xml')

########NEW FILE########
__FILENAME__ = globalmind
from __future__ import unicode_literals
from conceptnet5.uri import Licenses
from conceptnet5.nodes import normalized_concept_uri
from conceptnet5.edges import make_edge
from conceptnet5.formats.json_stream import JSONStreamWriter

import yaml
import sys


# The language codes used by GlobalMind were idiosyncratic, and need to be
# converted to ISO-like codes by this dictionary instead of by the
# language_codes module. For example, 'cht' doesn't really mean Traditional
# Chinese, it means Cholón.
LANG_CODES = {
    'eng': 'en',
    'cht': 'zh_TW',
    'chs': 'zh_CN',
    'jpn': 'ja',
    'kor': 'ko',
    'spa': 'es',
}

LANG_NAMES = {
    'eng': 'English',
    'en': 'English',
    'cht': 'Traditional Chinese',
    'zh_TW': 'Traditional Chinese',
    'chs': 'Simplified Chinese',
    'zh_CN': 'Simplified Chinese',
    'jpn': 'Japanese',
    'ja': 'Japanese',
    'kor': 'Korean',
    'ko': 'Korean',
    'spa': 'Spanish',
    'es': 'Spanish'
}

RELATION_MAP = {
    'ThematicKLine': 'RelatedTo',
    'EffectOf': 'Causes',
    'MotivationOf': 'MotivatedByGoal',
    'DesirousEffectOf': 'CausesDesire',
    'OnEvent': 'HasSubevent',
    'NotDesireOf': 'NotDesires',
    'FirstSubeventOf': 'HasFirstSubevent',
    'LastSubeventOf': 'HasLastSubevent',
    'SubeventOf': 'HasSubevent',
    'PrerequisiteEventOf': 'HasPrerequisite',
    'PropertyOf': 'HasProperty',
    'LocationOf': 'AtLocation',
}


def get_lang(assertion):
    return assertion['start'].split('/')[2]


def build_from_dir(dirname, output_file):
    """
    Read a GlobalMind database exported in YAML files, translate
    it into ConceptNet 5 edges, and write those edges to disk using
    a JSONStreamWriter.
    """
    out = JSONStreamWriter(output_file)
    userdata = yaml.load_all(open(dirname + '/GMUser.yaml'))
    users = {}

    for userinfo in userdata:
        users[userinfo['pk']] = userinfo

    frame_data = yaml.load_all(open(dirname + '/GMFrame.yaml'))
    frames = {}
    for frame in frame_data:
        frames[frame['pk']] = frame['fields']

    assertiondata = yaml.load_all(open(dirname + '/GMAssertion.yaml'))
    assertions = {}
    for assertion in assertiondata:
        obj = assertion['fields']
        frame = frames[obj['frame']]
        frametext = frame['text']
        userinfo = users[obj['author']]
        username = userinfo['fields']['username']

        # GlobalMind provides information about what country the user is from, which
        # we can preserve in the contributor URI.
        #
        # If I got to re-choose these URIs, I would distinguish usernames with
        # a country code from those without a country code by something more
        # than the number of slashes, and I would write the country code in
        # capital letters.
        userlocale = userinfo['fields']['ccode'].lower()
        if userlocale:
            user_source = "/s/contributor/globalmind/%s/%s" % (userlocale, username)
        else:
            user_source = "/s/contributor/globalmind/%s" % username

        sources = [
            user_source,
            "/s/activity/globalmind/assert"
        ]

        lang = LANG_CODES[obj['lcode']]
        start = normalized_concept_uri(lang, obj['node1'])
        end = normalized_concept_uri(lang, obj['node2'])
        rel = '/r/' + RELATION_MAP.get(frame['relation'], frame['relation'])

        # fix messy english "around in"
        if ' around ' in frametext:
            if obj['node2'].startswith('in '):
                frametext = frametext.replace(' around ', ' in ')
                obj['node2'] = obj['node2'][3:]
            else:
                frametext = frametext.replace(' around ', ' near ')
                rel = '/r/LocatedNear'

        # fix more awkward English. I wonder how bad the other languages are.
        frametext = frametext.replace('hits your head', 'comes to mind')
        frametext = frametext.replace(': [node1], [node2]', ' [node1] and [node2]')

        node1 = u'[[' + obj['node1'] + u']]'
        node2 = u'[[' + obj['node2'] + u']]'
        surfaceText = frametext.replace('//', '').replace('[node1]', node1).replace('[node2]', node2)
        edge = make_edge(rel, start, end,
                         dataset='/d/globalmind',
                         license='/l/CC/By',
                         sources=sources,
                         surfaceText=surfaceText,
                         weight=1)
        out.write(edge)
        assertions[assertion['pk']] = edge

    translationdata = yaml.load_all(open(dirname + '/GMTranslation.yaml'))
    for translation in translationdata:
        obj = translation['fields']
        assertion1 = assertions[obj['assertion1']]
        assertion2 = assertions[obj['assertion2']]
        start = assertion1['uri']
        end = assertion2['uri']
        rel = '/r/TranslationOf'
        text1 = assertion1['surfaceText'].replace('[[', '').replace(']]', '')
        text2 = assertion2['surfaceText'].replace('[[', '').replace(']]', '')
        lang1 = LANG_NAMES[get_lang(assertion1)]
        lang2 = LANG_NAMES[get_lang(assertion2)]
        surfaceText = u"[[%s]] in %s means [[%s]] in %s." % (text1, lang1, text2, lang2)
        userinfo = users[obj['author']]
        username = userinfo['fields']['username']

        userlocale = userinfo['fields']['ccode'].lower()
        if userlocale:
            user_source = "/s/contributor/globalmind/%s/%s" % (userlocale, username)
        else:
            user_source = "/s/contributor/globalmind/%s" % username

        sources = [
            user_source,
            "/s/activity/globalmind/translate"
        ]
        edge = make_edge(rel, start, end,
                         dataset='/d/globalmind',
                         license=Licenses.cc_attribution,
                         sources=sources,
                         surfaceText=surfaceText,
                         weight=1)
        out.write(edge)


# Entry point for testing
handle_file = build_from_dir


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_dir', help="Directory containing WordNet files")
    parser.add_argument('output', help='JSON-stream file to output to')
    args = parser.parse_args()
    build_from_dir(args.input_dir, args.output)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = jmdict
from __future__ import unicode_literals, print_function
import xmltodict
import re
import codecs
from conceptnet5.util.language_codes import CODE_TO_ENGLISH_NAME, ENGLISH_NAME_TO_CODE
from conceptnet5.formats.json_stream import JSONStreamWriter
from conceptnet5.uri import Licenses, BAD_NAMES_FOR_THINGS
from conceptnet5.nodes import normalized_concept_uri
from conceptnet5.edges import make_edge


# Now that Unicode literals are on, get the type of a Unicode string,
# regardless of whether this is Python 2 or 3.
STRING_TYPE = type("")

# I took the time to record these, but in the end I don't think I plan
# to use them. Japanese parts of speech don't fit neatly enough into
# ConceptNet's neat n/v/a/r types.
#
# The idea was to record the parts of speech by the first 10 characters
# of their category in JMdict (because they're automatically decoded
# from their more helpful entity form).
NOUN_TYPES = [
    "nouns whic",
    "noun (comm",
    "adverbial ",
    "noun, used",
    "noun (temp",
    "noun or pa",
]
ADJ_TYPES = [
    "adjective ",
    "adjectival",
    "pre-noun a",
]
ADV_TYPES = [
    "adverb (fu",
    "adverb tak",
]
VERB_TYPES = [
    "Ichidan ve",
    "Nidan verb",
    "Yodan verb",
    "Godan verb",
    "intransiti",
    "Kuru verb ",
    "irregular ",
    "su verb - ",
    "suru verb ",
]


def convert_lang_code(code):
    """
    Map a language code to the canonical one that ConceptNet 5 uses,
    which is either the alpha2 code, or the "terminology" alpha3 code if no
    alpha2 code exists

    JMdict uses the "bibliographic" alpha3 code, which is often equal to
    neither of these, but we can map it to a canonical one by running it back
    and forth through our language name dictionaries.
    """
    return ENGLISH_NAME_TO_CODE[CODE_TO_ENGLISH_NAME[code]]


def get_list(node, tag):
    """
    Get sub-nodes of this node by their tag, and make sure to return a list.

    The problem here is that xmltodict returns a nested dictionary structure,
    whose substructures have different *types* if there's repeated nodes
    with the same tag. So a list of one thing ends up being a totally different
    thing than a list of two things.

    So, here, we look up a sub-node by its tag, and return a list regardless of
    whether it matched 0, 1, or more things.
    """
    subnode = node.get(tag, [])
    if isinstance(subnode, list):
        return subnode
    else:
        return [subnode]


GLOSS_RE = re.compile(r'''
    # Separate out text in parentheses or brackets.
    ^
    (\(.*?\)|\[.*?\] )?   # possibly a bracketed expression before the gloss
    (.*?)                 # the gloss itself
    ( \(.*?\)|\[.*?\])?   # possibly a bracketed expression after the gloss
    $
''', re.VERBOSE)
def parse_gloss(text):
    matched = GLOSS_RE.match(text)
    if matched:
        return matched.group(2).strip()
    else:
        return None


def handle_file(filename, output_file):
    """
    JMdict is a Japanese translation dictionary, targeting multiple languages,
    released under a Creative Commons Attribution-ShareAlike license. That's
    awesome.

    It's released as a kind of annoying XML structure, using fancy XML features
    like entities, so in order to read it we need a full-blown XML parser. Python's
    built-in XML parsers are horrifying, so here we use the 'xmltodict' module, which
    is also horrifying but gets the job done.

    The majorly weird thing about xmltodict that we have to work around is that
    it gives results of different *types* when you get 0, 1, or many child nodes.
    This is what get_list is for.
    """
    # Read the XML file as UTF-8, and parse it into a dictionary.
    file = codecs.open(filename, encoding='utf-8')
    out = JSONStreamWriter(output_file)
    data = file.read()
    file.close()
    xml = xmltodict.parse(data)
    
    # The dictionary contains a list of <entry> tags.
    root_node = xml['JMdict']
    for entry in get_list(root_node, 'entry'):
        # From JMdict's documentation: "The kanji element, or in its absence,
        # the reading element, is the defining component of each entry."
        #
        # Quick summary of what's going on here: most Japanese words can be
        # written using kanji or kana.
        #
        # Kana are phonetic characters. Every word can be written in kana, in
        # one of two alphabets (hiragana or katakana). Words that are homonyms
        # have the same kana, unless they're written in different alphabets.
        #
        # Kanji are Chinese-based characters that are related to the meaning of
        # the word. They're compact and good at disambiguating homonyms, so
        # kanji are usually used as the canonical representation of a word.
        # However, some words have no kanji.
        #
        # The kana version of a word written in kanji is called its 'reading'.
        # Words that are pronounced differently in different contexts have
        # multiple readings.
        #
        # Okay, done with the intro to Japanese orthography. In JMdict, if
        # a word can be written in kanji, it has a <k_ele> element, containing
        # a <keb> element that contains the text. Every word also has an
        # <r_ele> element, containing one or more <reb> elements that are phonetic
        # readings of the word.
        #
        # We get the "defining text" of a word by taking its <keb> if it exists,
        # or all of its <reb>s if not. There's no way to tell which <reb> is the
        # most "defining" in the case where there's no <keb>.
        headwords = [word['keb'] for word in get_list(entry, 'k_ele')]
        if not headwords:
            headwords = [word['reb'] for word in get_list(entry, 'r_ele')]

        # An entry might have different word senses that are translated
        # differently to other languages. Ideally, we'd remember that they're
        # different senses. However, we have no way to refer to the different
        # senses. So for now, we disregard word senses. One day we might have
        # a better overall plan for word senses in ConceptNet.
        for sense in get_list(entry, 'sense'):
            # Glosses are translations of the word to different languages.
            # If the word is a loan-word, the foreign word it was derived from
            # will be marked with the <lsource> tag instead of <gloss>.
            #
            # Get all the glosses, including the lsource if it's there.
            glosses = get_list(sense, 'gloss') + get_list(sense, 'lsource')
            for gloss in glosses:
                text = lang = None
                if '#text' in gloss:
                    # A gloss node might be marked with a 'lang' attribute. If so,
                    # xmltodict represents it as a dictionary with '#text' and
                    # '@xml:lang' elements.
                    text = parse_gloss(gloss['#text'])
                    lang = convert_lang_code(gloss['@xml:lang'])
                elif isinstance(gloss, STRING_TYPE):
                    # If there's no 'lang' attribute, the gloss is in English,
                    # and xmltodict gives it to us as a plain Unicode string.
                    lang = 'en'
                    text = parse_gloss(gloss)

                # If we parsed the node at all and the text looks good, then we can
                # add edges to ConceptNet.
                #
                # We don't want to deal with texts with periods (these might be
                # dictionary-style abbreviations, which are sort of unhelpful when
                # we can't expand them), and we also don't want to deal with texts
                # that are more than five words long.
                if (
                    text is not None and '.' not in text and text.count(' ') <= 4
                    and text not in BAD_NAMES_FOR_THINGS
                ):
                    for head in headwords:
                        ja_concept = normalized_concept_uri('ja', head)
                        other_concept = normalized_concept_uri(lang, text)
                        output_edge(out, ja_concept, other_concept)


def output_edge(out, subj_concept, obj_concept):
    """
    Write an edge to `out`, an instance of JSONFileWriter.
    """
    rel = '/r/TranslationOf'
    edge = make_edge(rel, subj_concept, obj_concept,
                     dataset='/d/jmdict',
                     license=Licenses.cc_sharealike,
                     sources=['/s/jmdict/1.07'],
                     weight=0.5)
    out.write(edge)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='XML copy of JMDict to read')
    parser.add_argument('output', help='JSON-stream file to output to')
    args = parser.parse_args()
    handle_file(args.input, args.output)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = ptt_petgame
from __future__ import unicode_literals
import codecs
import json
from conceptnet5.formats.json_stream import JSONStreamWriter
from conceptnet5.nodes import normalized_concept_uri
from conceptnet5.edges import make_edge
from conceptnet5.util import get_data_filename


FRAME_DATA = json.load(
    codecs.open(get_data_filename('zh_frames.json'), encoding='utf-8')
)


def handle_raw_assertion(line):
    parts = line.split(', ')
    user, frame_id, concept1, concept2 = parts
    fdata = FRAME_DATA[frame_id]
    ftext = fdata['text']
    rel = fdata['relation']

    surfaceText = ftext.replace('{1}', '[[' + concept1 + ']]').replace('{2}', '[[' + concept2 + ']]')
    start = normalized_concept_uri('zh_TW', concept1)
    end = normalized_concept_uri('zh_TW', concept2)
    sources = ['/s/activity/ptt/petgame', '/s/contributor/petgame/' + user]
    yield make_edge(rel, start, end, dataset='/d/conceptnet/4/zh',
                    license='/l/CC/By', sources=sources,
                    surfaceText=surfaceText, weight=1)

def handle_file(input_filename, output_file):
    out = JSONStreamWriter(output_file)
    for line in codecs.open(input_filename, encoding='utf-8'):
        line = line.strip()
        if line:
            for new_obj in handle_raw_assertion(line):
                out.write(new_obj)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='JSON-stream file of input')
    parser.add_argument('output', help='JSON-stream file to output to')
    args = parser.parse_args()
    handle_file(args.input, args.output)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = verbosity
from __future__ import print_function, unicode_literals, division
from conceptnet5.uri import Licenses
from conceptnet5.nodes import normalized_concept_uri
from conceptnet5.edges import make_edge
from conceptnet5.formats.json_stream import JSONStreamWriter
from conceptnet5.util.sounds_like import sounds_like_score
from collections import defaultdict
import re
import sys

# If any word in a clue matches one of these words, it is probably a bad
# common-sense assertion.
# 
# Many of these represent violations of the use-mention distinction, such as
# "dog has three letters" instead of "dog has four legs". Others involve
# pronouns that refer to a previous clue or previous guess.
#
# I have no idea why the word 'mince' shows up in so many bad assertions, but
# it does.
BAD_CLUE_REGEX = re.compile(
    r'(^letter|^rhyme|^blank$|^words?$|^syllable$|^spell|^tense$|^prefix'
    r'|^suffix|^guess|^starts?$|^ends?$|^singular$|^plural|^noun|^verb'
    r'|^opposite|^homonym$|^synonym$|^antonym$|^close$|^only$|^just$|'
    r'^different|^this$|^that$|^these$|^those$|^mince$|^said$|^same$|'
    r'^delete|^remove|^add$|^plus$|^more$|^less$|^clue$)'
)

# These are words we won't pull out of phrases in order to make individual
# assertions. The list is much more extensive than the three and a half
# stopwords that ConceptNet uses for English in general.
STOPWORDS = {
    'a', 'an', 'the', 'to', 'of', 'for', 'in', 'on', 'at', 'by', 'with', 'and',
    'or', 'far', 'near', 'away', 'from', 'thing', 'something', 'things', 'be',
    'is', 'are', 'was', 'were', 'as', 'so', 'get', 'me', 'you', 'it', 'he',
    'she', 'him', 'her', 'this', 'that', 'they', 'them', 'some', 'many', 'no',
    'one', 'all', 'either', 'both', 'er'
}

def handle_file(infile, outfile):
    count = 0
    outcomes = defaultdict(int)

    sources = ['/s/site/verbosity']

    writer = JSONStreamWriter(outfile)

    for line in open(infile):
        parts = line.strip().split('\t')
        if not parts:
            outcomes['blank'] += 1
            continue

        # The first 5 columns of the Verbosity output file are:
        #
        #   left: the word being clued
        #   relation: the relation between the word and the clue that the
        #             clue-giver chose, in a form such as "it is part of"
        #   right: the one or two words used as the clue
        #   freq: the number of different times this clue was given
        #   orderscore: the average position in the list of clues
        #
        # 'orderscore' is a number from 0 to 999, representing the average
        # quantile of its position in the list of clues. (It's like a
        # percentile, except there are 1000 of them, not 100.)
        #
        # A clue that's always given first has an orderscore of 0. A clue
        # that always appears halfway through the list has an orderscore of
        # 500.
        #
        # This may seem like a strange thing to measure, and I didn't come up
        # with it, but it actually turns out to be somewhat informative.
        # A clue with an orderscore of 0 is probably a good common-sense
        # relation, representing the first thing that comes to mind. A clue
        # with a high order score may be a move of desperation after several
        # other clues have failed. It causes the guesser to get the answer
        # soon afterward, but perhaps because it's a "cheating" move. So,
        # low orderscores represent better common sense relations.
        left, relation, right, freq, orderscore = parts[:5]
        freq = int(freq)
        orderscore = int(orderscore)

        # Test each word 
        flagged = False
        for rword in right.split():
            if BAD_CLUE_REGEX.match(rword):
                flagged = True
                break

        if flagged:
            outcomes['flag word'] += 1
            continue
        if len(right) < 3:
            outcomes['clue too short'] += 1
            continue
        if len(right.split()[-1]) == 1:
            outcomes['letter'] += 1
            continue

        # The Verbosity interface and gameplay did not particularly encourage
        # players to choose an appropriate relation. In practice, players seem
        # to have used them all interchangeably, except for the negative
        # relation "it is the opposite of", expressing /r/Antonym.
        #
        # Another way that players expressed negative relations was to use
        # 'not' as the first word of their clue; we make that into an instance
        # of /r/Antonym as well.
        #
        # In other cases, the relation is a positive relation, so we replace it
        # with the most general positive relation, /r/RelatedTo.
        rel = '/r/RelatedTo'
        reltext = 'is related to'
        if right.startswith('not '):
            rel = '/r/Antonym'
            right = right[4:]
            reltext = 'is not'
        if relation == 'it is the opposite of':
            rel = '/r/Antonym'
            reltext = 'is the opposite of'

        # The "sounds-like score" determines whether this clue seems to be a
        # pun or rhyme, rather than an actual common-sense relationship. If
        # the sounds-like score is over 0.35, skip the assertion.
        sls = sounds_like_score(left, right)
        if sls > 0.35:
            outcomes['text similarity'] += 1
            continue
        
        # Calculate a score for the assertion:
        #
        #   - The number of times it's been used as a clue
        #   - ...with a linear penalty for a high sounds-like score
        #   - ...and a linear penalty for high orderscores
        #
        # The penalties are multiplicative factors from 0 to 1, which decrease
        # linearly as the relevant penalties increase. If a clue is given N
        # times, with a sounds-like score of 0 and an orderscore of 0, it will
        # get an overall score of 2N - 1. This is a formula we should probably
        # revisit.
        #
        # The weight is the score divided by 100. All divisions are floating
        # point, as defined by the __future__ import at the top of this module.
        score = (freq * 2 - 1) * (1 - sls) * (1 - orderscore / 1000)
        if score <= 0.5:
            outcomes['low score'] += 1
            continue

        weight = score / 100

        # If the clue on the right is a two-word phrase, we make additional
        # connections to both words individually. We label them with the
        # rule-based source '/s/rule/split_words' to track that this happened.
        rightwords = [right]
        if ' ' in right:
            morewords = [word for word in right.split(' ') if word not in STOPWORDS]
            rightwords.extend(morewords)

        for i, rightword in enumerate(rightwords):
            edge_sources = list(sources)
            if i > 0:
                edge_sources.append('/s/rule/split_words')
            
            # Build the natural-language-ish surface text for this clue
            text = '[[%s]] %s [[%s]]' % (left, reltext, rightword)
            
            count += 1
            outcomes['success'] += 1
            
            leftc = normalized_concept_uri('en', left)
            rightc = normalized_concept_uri('en', rightword)
            edge = make_edge(rel, leftc, rightc, dataset='/d/verbosity',
                             license=Licenses.cc_attribution,
                             sources=sources, surfaceText=text,
                             weight=weight)
            writer.write(edge)

    # Count the various outcomes. This can be used as a sanity-check. It
    # also was used for a graph in a ConceptNet 5 paper.
    print("Verbosity outcomes: %s" % outcomes)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='JSON-stream file of input')
    parser.add_argument('output', help='JSON-stream file to output to')
    args = parser.parse_args()
    handle_file(args.input, args.output)

########NEW FILE########
__FILENAME__ = wiktionary_en
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""
This Wiktionary reader should be refactored, but it does the job for now.
"""

from xml.sax import ContentHandler, make_parser
from xml.sax.handler import feature_namespaces
from conceptnet5.uri import Licenses, BAD_NAMES_FOR_THINGS
from conceptnet5.nodes import normalized_concept_uri
from conceptnet5.edges import make_edge
from conceptnet5.formats.json_stream import JSONStreamWriter
from conceptnet5.util.language_codes import CODE_TO_ENGLISH_NAME
import unicodedata
import re


def ascii_enough(text):
    """
    Test whether text is entirely in the ASCII set. We use this as a very rough
    way to figure out definitions that are supposed to be in English but
    aren't.
    """
    # cheap assumption: if it's ASCII, and it's meant to be in English, it's
    # probably actually in English.
    return text.encode('ascii', 'replace') == text.encode('ascii', 'ignore')


def term_is_bad(term):
    return (term in BAD_NAMES_FOR_THINGS or 'Wik' in term or ':' in term)


PARTS_OF_SPEECH = {
    'Noun': 'n',
    'Verb': 'v',
    'Adjective': 'a',
    'Adverb': 'r',
    'Preposition': 'p',
    'Pronoun': 'n',
    'Determiner': 'd',
    'Article': 'd',
    'Interjection': 'i',
    'Conjunction': 'c',
}
LANGUAGE_HEADER = re.compile(r'==\s*(.+)\s*==')
TRANS_TOP = re.compile(r"\{\{trans-top\|(.+)\}\}")
TRANS_TAG = re.compile(r"\{\{t.?\|([^|}]+)\|([^|}]+)")
CHINESE_TAG = re.compile(r"\{\{cmn-(noun|verb)+\|(s|t|st|ts)\|")
WIKILINK = re.compile(r"\[\[([^|\]#]+)")

LANGUAGES = {
    'English': 'en',

    'Afrikaans': 'af',
    'Arabic': 'ar',
    'Armenian': 'hy',
    'Basque': 'eu',
    'Belarusian': 'be',
    'Bengali': 'bn',
    'Bosnian': 'bs',
    'Bulgarian': 'bg',
    'Burmese': 'my',
    'Chinese': 'zh',
    'Crimean Tatar': 'crh',
    'Croatian': 'hr',
    'Czech': 'cs',
    'Danish': 'da',
    'Dutch': 'nl',
    'Esperanto': 'eo',
    'Estonian': 'et',
    'Finnish': 'fi',
    'French': 'fr',
    'Galician': 'gl',
    'German': 'de',
    'Greek': 'el',
    'Hebrew': 'he',
    'Hindi': 'hi',
    'Hungarian': 'hu',
    'Icelandic': 'is',
    'Ido': 'io',
    'Indonesian': 'id',
    'Irish': 'ga',
    'Italian': 'it',
    'Japanese': 'ja',
    'Kannada': 'kn',
    'Kazakh': 'kk',
    'Khmer': 'km',
    'Korean': 'ko',
    'Kyrgyz': 'ky',
    'Lao': 'lo',
    'Latin': 'la',
    'Lithuanian': 'lt',
    'Lojban': 'jbo',
    'Macedonian': 'mk',
    'Min Nan': 'nan',
    'Malagasy': 'mg',
    'Mandarin': 'zh',
    'Norwegian': 'no',
    'Pashto': 'ps',
    'Persian': 'fa',
    'Polish': 'pl',
    'Portuguese': 'pt',
    'Romanian': 'ro',
    'Russian': 'ru',
    'Sanskrit': 'sa',
    'Sinhalese': 'si',
    'Scots': 'sco',
    'Scottish Gaelic': 'gd',
    'Serbian': 'sr',
    'Slovak': 'sk',
    'Slovene': 'sl',
    'Slovenian': 'sl',
    'Spanish': 'es',
    'Swahili': 'sw',
    'Swedish': 'sv',
    'Tajik': 'tg',
    'Tamil': 'ta',
    'Thai': 'th',
    'Turkish': 'tr',
    'Turkmen': 'tk',
    'Ukrainian': 'uk',
    'Urdu': 'ur',
    'Uzbek': 'uz',
    'Vietnamese': 'vi',
    '英語': 'en',
    '日本語': 'ja'
}

SOURCE = '/s/web/en.wiktionary.org'
INTERLINGUAL = '/s/rule/wiktionary_interlingual_definitions'
MONOLINGUAL = '/s/rule/wiktionary_monolingual_definitions'
TRANSLATE = '/s/rule/wiktionary_translation_tables'
DEFINE = '/s/rule/wiktionary_define_senses'

class FindTranslations(ContentHandler):
    def __init__(self, output_file='wiktionary.json'):
        self.lang = None
        self.langcode = None
        self.inArticle = False
        self.inTitle = False
        self.curSense = None
        self.curTitle = ''
        self.curText = ''
        self.locales = []
        self.curRelation = None
        self.writer = JSONStreamWriter(output_file)

    def startElement(self, name, attrs):
        if name == 'page':
            self.inArticle = True
            self.curText = []
        elif name == 'title':
            self.inTitle = True
            self.curTitle = ''

    def endElement(self, name):
        if name == 'page':
            self.inArticle = False
            self.handleArticle(self.curTitle, ''.join(self.curText))
        elif name == 'title':
            self.inTitle = False

    def characters(self, text):
        if self.inTitle:
            self.curTitle += text
        elif self.inArticle:
            self.curText.append(text)
            if len(self.curText) > 10000:
                # bail out
                self.inArticle = False

    def handleArticle(self, title, text):
        lines = text.split('\n')
        self.pos = None
        for line in lines:
            self.handleLine(title, line.strip())

    def handleLine(self, title, line):
        language_match = LANGUAGE_HEADER.match(line)
        trans_top_match = TRANS_TOP.match(line)
        trans_tag_match = TRANS_TAG.search(line)
        chinese_match = CHINESE_TAG.search(line)
        if line.startswith('===') and line.endswith('==='):
            pos = line.strip('= ')
            if pos == 'Synonyms':
                self.curRelation = 'Synonym'
            elif pos == 'Antonym':
                self.curRelation = 'Antonym'
            elif pos == 'Related terms':
                self.curRelation = 'RelatedTo'
            elif pos == 'Derived terms':
                if not line.startswith('===='):
                    # this is at the same level as the part of speech;
                    # now we don't know what POS these apply to
                    self.pos = None
                self.curRelation = 'DerivedFrom'
            else:
                self.curRelation = None
                if pos in PARTS_OF_SPEECH:
                    self.pos = PARTS_OF_SPEECH[pos]
        elif language_match:
            self.lang = language_match.group(1)
            self.langcode = LANGUAGES.get(self.lang)
        elif chinese_match:
            scripttag = chinese_match.group(2)
            self.locales = []
            if 's' in scripttag:
                self.locales.append('_CN')
            if 't' in scripttag:
                self.locales.append('_TW')
        elif line[0:1] == '#' and self.lang != 'English' and self.lang is not None:
            defn = line[1:].strip()
            if defn[0:1] not in ':*#':
                for defn2 in filter_line(defn):
                    if not ascii_enough(defn2): continue
                    if 'Index:' in title: continue
                    if self.langcode == 'zh':
                        for locale in self.locales:
                            self.output_translation(title, defn2, locale)
                    elif self.langcode:
                        self.output_translation(title, defn2)
        elif line[0:4] == '----':
            self.pos = None
            self.lang = None
            self.langcode = None
            self.curRelation = None
        elif trans_top_match:
            pos = self.pos or 'n'
            sense = trans_top_match.group(1).split(';')[0].strip('.')
            if 'translations' in sense.lower():
                self.curSense = None
            else:
                self.curSense = (pos, sense)
        elif trans_tag_match:
            lang = trans_tag_match.group(1)
            translation = trans_tag_match.group(2)
            if self.curSense is not None and self.lang == 'English':
                # handle Chinese separately
                if lang not in ('cmn', 'yue', 'zh-yue', 'zh'):
                    self.output_sense_translation(lang, translation, title,
                                                  self.curSense)
        elif '{{trans-bottom}}' in line:
            self.curSense = None
        elif line.startswith('* ') and self.curRelation and self.langcode:
            relatedmatch = WIKILINK.search(line)
            if relatedmatch:
                related = relatedmatch.group(1)
                self.output_monolingual(self.langcode, self.curRelation,
                                        related, title)

    def output_monolingual(self, lang, relation, term1, term2):
        if term_is_bad(term1) or term_is_bad(term2):
            return
        source = normalized_concept_uri(lang, term1)
        if self.pos:
            target = normalized_concept_uri(lang, term2, self.pos)
        else:
            target = normalized_concept_uri(lang, term2)
        surfaceText = "[[%s]] %s [[%s]]" % (term1, relation, term2)

        edge = make_edge('/r/'+relation, source, target, '/d/wiktionary/%s/%s' % (lang, lang),
                         license=Licenses.cc_sharealike,
                         sources=[SOURCE, MONOLINGUAL],
                         weight=1.0,
                         surfaceText=surfaceText)
        self.writer.write(edge)

    def output_sense_translation(self, lang, foreign, english, sense):
        pos, disambiguation = sense
        if 'Wik' in foreign or 'Wik' in english or term_is_bad(foreign) or term_is_bad(english):
            return
        # Quick fix that drops definitions written in Lojban syntax
        if lang == 'jbo' and re.search(r'x[1-5]', english):
            return
        if lang == 'zh-cn':
            lang = 'zh_CN'
        elif lang == 'zh-tw':
            lang = 'zh_TW'
        source = normalized_concept_uri(
          lang, unicodedata.normalize('NFKC', foreign)
        )
        target = normalized_concept_uri(
          'en', english, pos, disambiguation
        )
        relation = '/r/TranslationOf'
        try:
            surfaceRel = "is %s for" % (CODE_TO_ENGLISH_NAME[lang.split('_')[0]])
        except KeyError:
            surfaceRel = "is [language %s] for" % lang
        surfaceText = "[[%s]] %s [[%s (%s)]]" % (foreign, surfaceRel, english, disambiguation.split('/')[-1].replace('_', ' '))
        edge = make_edge(relation, source, target, '/d/wiktionary/en/%s' % lang,
                         license=Licenses.cc_sharealike,
                         sources=[SOURCE, TRANSLATE],
                         weight=1.0,
                         surfaceText=surfaceText)
        self.writer.write(edge)

    def output_translation(self, foreign, english, locale=''):
        if term_is_bad(foreign) or term_is_bad(english):
            return
        # Quick fix that drops definitions written in Lojban syntax
        if self.langcode == 'jbo' and re.search(r'x[1-5]', english):
            return
        source = normalized_concept_uri(
            self.langcode + locale,
            foreign
        )
        target = normalized_concept_uri(
          'en', english
        )
        relation = '/r/TranslationOf'
        try:
            surfaceRel = "is %s for" % (CODE_TO_ENGLISH_NAME[self.langcode.split('_')[0]])
        except KeyError:
            surfaceRel = "is [language %s] for" % self.langcode
        surfaceText = "[[%s]] %s [[%s]]" % (foreign, surfaceRel, english)
        edge = make_edge(relation, source, target, '/d/wiktionary/en/%s' % self.langcode,
                         license=Licenses.cc_sharealike,
                         sources=[SOURCE, INTERLINGUAL],
                         weight=1.0,
                         surfaceText=surfaceText)
        self.writer.write(edge)

def filter_line(line):
    line = re.sub(r"\{\{.*?\}\}", "", line)
    line = re.sub(r"<.*?>", "", line)
    line = re.sub(r"\[\[([^|]*\|)?(.*?)\]\]", r"\2", line)
    line = re.sub(r"''+", "", line)
    line = re.sub(r"\(.*?\(.*?\).*?\)", "", line)
    line = re.sub(r"\(.*?\)", "", line)
    if re.search(r"\.\s+[A-Z]", line): return
    parts = re.split(r"[,;:/]", line)
    for part in parts:
        if not re.search(r"(singular|plural|participle|preterite|present|-$)", part):
            remain = part.strip().strip('.').strip()
            if remain: yield remain


def handle_file(input_file, output_file):
    # Create a parser
    parser = make_parser()

    # Tell the parser we are not interested in XML namespaces
    parser.setFeature(feature_namespaces, 0)

    # Create the handler
    dh = FindTranslations(output_file=output_file)

    # Tell the parser to use our handler
    parser.setContentHandler(dh)

    # Parse the input
    if hasattr(input_file, 'read'):
        input_stream = input_file
    else:
        input_stream = open(input_file)
    parser.parse(input_stream)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='XML file of input')
    parser.add_argument('output', help='JSON-stream file to output to')
    args = parser.parse_args()
    handle_file(args.input, args.output)

########NEW FILE########
__FILENAME__ = wordnet
from __future__ import unicode_literals
from collections import defaultdict
from conceptnet5.uri import join_uri
from conceptnet5.nodes import normalized_concept_uri
from conceptnet5.edges import make_edge
from conceptnet5.formats.json_stream import JSONStreamWriter
from conceptnet5.formats.semantic_web import NTriplesReader, NTriplesWriter, resource_name, full_conceptnet_url
import re
import os


SOURCE = '/s/wordnet/3.0'

PARTS_OF_SPEECH = {
    'noun': 'n',
    'verb': 'v',
    'adjective': 'a',
    'adjectivesatellite': 'a',
    'adverb': 'r',
}

REL_MAPPING = {
    'attribute': 'Attribute',
    'causes': 'Causes',
    'classifiedByRegion': 'HasContext',
    'classifiedByUsage': 'HasContext',
    'classifiedByTopic': 'HasContext',
    'entails': 'Entails',
    'hyponymOf': 'IsA',
    'instanceOf': 'InstanceOf',
    'memberMeronymOf': 'MemberOf',
    'partMeronymOf': 'PartOf',
    'sameVerbGroupAs': 'SimilarTo',
    'similarTo': 'SimilarTo',
    'substanceMeronymOf': '~MadeOf',
    'antonymOf': 'Antonym',
    'derivationallyRelated': '~DerivedFrom',
    'pertainsTo': 'PertainsTo',
    'seeAlso': 'RelatedTo',
}


def run_wordnet(input_dir, output_file, sw_map_file):
    out = JSONStreamWriter(output_file)
    map_out = NTriplesWriter(sw_map_file)
    reader = NTriplesReader()

    synset_senses = defaultdict(list)
    sense_synsets = {}

    labels = {}
    glossary = {}
    concept_map = {}
    sense_to_synset = {}

    # Parse lines such as:
    #   wn30:synset-Aeolian-noun-2 rdfs:label "Aeolian"@en-us .
    for subj, rel, obj, objtag in reader.parse_file(os.path.join(input_dir, 'wordnet-synset.ttl')):
        if resource_name(rel) == 'label':
            # Everything in WordNet is in English
            assert objtag == 'en'
            labels[subj] = obj

    for subj, rel, obj, objtag in reader.parse_file(os.path.join(input_dir, 'wordnet-glossary.ttl')):
        if resource_name(rel) == 'gloss':
            assert objtag == 'en'

            # Take the definition up to the first semicolon
            text = obj.split(';')[0]

            # Remove introductory phrases with a colon
            text = text.split(': ', 1)[-1]

            # Remove parenthesized expressions
            while True:
                newtext = re.sub(r'\(.+?\) ?', '', text).strip()
                if newtext == text or newtext == '':
                    break
                else:
                    text = newtext

            glossary[subj] = text.replace('/', '_')

    # Get the list of word senses in each synset, and make a bidirectional mapping.
    #
    # Example line:
    #   wn30:synset-Aeolian-noun-2 wn20schema:containsWordSense wn30:wordsense-Aeolian-noun-2 .
    for subj, rel, obj, objtag in reader.parse_file(os.path.join(input_dir, 'full/wordnet-wordsense-synset-relations.ttl')):
        if resource_name(rel) == 'containsWordSense':
            synset_senses[subj].append(obj)
            sense_synsets[obj] = subj

    # Assign every synset to a disambiguated concept.
    for synset in synset_senses:
        synset_name = labels[synset]
        synset_pos = synset.split('-')[-2]
        pos = PARTS_OF_SPEECH[synset_pos]
        disambig = glossary[synset]

        concept = normalized_concept_uri('en', synset_name, pos, disambig)
        concept_map[synset] = concept

    # Map senses to their synsets.
    for sense, synset in sense_synsets.items():
        sense_to_synset[sense] = synset

    for filename in (
        'wordnet-attribute.ttl', 'wordnet-causes.ttl',
        'wordnet-classifiedby.ttl', 'wordnet-entailment.ttl',
        'wordnet-hyponym.ttl', 'wordnet-instances.ttl',
        'wordnet-membermeronym.ttl', 'wordnet-partmeronym.ttl',
        'wordnet-sameverbgroupas.ttl', 'wordnet-similarity.ttl',
        'wordnet-substancemeronym.ttl', 'full/wordnet-antonym.ttl',
        'full/wordnet-derivationallyrelated.ttl',
        'full/wordnet-participleof.ttl',
        'full/wordnet-pertainsto.ttl',
        'full/wordnet-seealso.ttl'
    ):
        filepath = os.path.join(input_dir, filename)
        if os.path.exists(filepath):
            for web_subj, web_rel, web_obj, objtag in reader.parse_file(filepath):
                # If this relation involves word senses, map them to their synsets
                # first.
                if web_subj in sense_to_synset:
                    web_subj = sense_to_synset[web_subj]
                if web_obj in sense_to_synset:
                    web_obj = sense_to_synset[web_obj]
                subj = concept_map[web_subj]
                obj = concept_map[web_obj]
                pred_label = resource_name(web_rel)
                if pred_label in REL_MAPPING:
                    mapped_rel = REL_MAPPING[pred_label]

                    # Handle WordNet relations that are the reverse of ConceptNet
                    # relations. Change the word 'meronym' to 'holonym' if
                    # necessary.
                    if mapped_rel.startswith('~'):
                        subj, obj = obj, subj
                        web_subj, web_obj = web_obj, web_subj
                        web_rel = web_rel.replace('meronym', 'holonym')
                        mapped_rel = mapped_rel[1:]
                    rel = join_uri('r', mapped_rel)
                else:
                    rel = join_uri('r', 'wordnet', pred_label)

                map_out.write_link(web_rel, full_conceptnet_url(rel))
                map_out.write_link(web_subj, full_conceptnet_url(subj))
                map_out.write_link(web_obj, full_conceptnet_url(obj))
                edge = make_edge(
                    rel, subj, obj, dataset='/d/wordnet/3.0',
                    license='/l/CC/By', sources=SOURCE, weight=2.0
                )
                out.write(edge)


# Entry point for testing
handle_file = run_wordnet


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_dir', help="Directory containing WordNet files")
    parser.add_argument('output', help='JSON-stream file to output to')
    parser.add_argument('sw_map', help='A .nt file of Semantic Web equivalences')
    args = parser.parse_args()
    run_wordnet(args.input_dir, args.output, args.sw_map)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = uri
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
"""
URIs are Unicode strings that represent the canonical name for any object in
ConceptNet. These can be used with the ConceptNet Web API, or referred to in a
Semantic Web application, by attaching the prefix:

    http://conceptnet5.media.mit.edu/data/VERSION

For example, the English concept "book" has the URI '/c/en/book'. This concept
can be referred to, or retrieved, using this complete URI (in version 5.2):

    http://conceptnet5.media.mit.edu/data/5.2/c/en/book
"""

import sys
from ftfy import fix_text


if sys.version_info.major >= 3:
    unicode = str


# All URIs are conceptually appended to this URL, when we need to interoperate
# with Semantic Web-style resources.
ROOT_URL = 'http://conceptnet5.media.mit.edu/data/5.2'

# If we end up trying to fit a piece of text that looks like these into a URI,
# it will mess up our patterns of URIs.
BAD_NAMES_FOR_THINGS = {'', ',', '[', ']', '/'}

def normalize_text(text):
    """
    When a piece of a URI is an arbitrary string, we standardize it in the
    following ways:

    - Ensure it is in Unicode, and standardize its Unicode representation
      with the `ftfy.fix_text` function.
    - Erase case distinctions by converting cased characters to lowercase.
    - Strip common punctuation, unless that would make the string empty.
    - Replace spaces with underscores.

    The result will be a Unicode string that can be used within a URI.

        >>> normalize_text(' cat')
        'cat'

        >>> normalize_text('Italian supercat')
        'italian_supercat'

        >>> normalize_text('Test?!')
        'test'

        >>> normalize_text('TEST.')
        'test'

        >>> normalize_text('test/test')
        'test_test'
        
        >>> normalize_text('   u\N{COMBINING DIAERESIS}ber\\n')
        'über'
    """
    if not isinstance(text, unicode):
        raise ValueError("All texts must be Unicode, not bytes.")

    # Replace slashes with spaces, which will become underscores later.
    # Slashes should separate pieces of a URI, and shouldn't appear within
    # a piece.
    text = fix_text(text, normalization='NFC').strip()
    text = text.replace('/', ' ')
    assert (text not in BAD_NAMES_FOR_THINGS), text
    text = text.strip('.,?!"') or text
    text = text.lower().replace(' ', '_')
    return text


def join_uri(*pieces):
    """
    `join_uri` builds a URI from constituent pieces that should be joined
    with slashes (/).

    Leading and trailing on the pieces are acceptable, but will be ignored.
    The resulting URI will always begin with a slash and have its pieces
    separated by a single slash.

    The pieces do not have `normalize_text` applied to them; to make sure your
    URIs are in normal form, run `normalize_text` on each piece that represents
    arbitrary text.

    >>> join_uri('/c', 'en', 'cat')
    '/c/en/cat'

    >>> join_uri('c', 'en', ' spaces ')
    '/c/en/ spaces '

    >>> join_uri('/r/', 'AtLocation/')
    '/r/AtLocation'

    >>> join_uri('/test')
    '/test'

    >>> join_uri('test')
    '/test'
    
    >>> join_uri('/test', '/more/')
    '/test/more'
    """
    joined = '/' + ('/'.join([piece.strip('/') for piece in pieces]))
    return joined


def concept_uri(lang, text, pos=None, disambiguation=None):
    """
    `concept_uri` builds a representation of a concept, which is a word or
    phrase of a particular language, which can participate in relations with
    other concepts, and may be linked to concepts in other languages.
    
    Every concept has an ISO language code and a text. It may also have a part
    of speech (pos), which is typically a single letter. If it does, it may
    have a disambiguation, a string that distinguishes it from other concepts
    with the same text.

    `text` and `disambiguation` should be strings that have already been run
    through `normalize_text`. See `normalized_concept_uri` in nodes.py for
    a more generally applicable function that also deals with special
    per-language handling.

    >>> concept_uri('en', 'cat')
    '/c/en/cat'
    >>> concept_uri('en', 'cat', 'n')
    '/c/en/cat/n'
    >>> concept_uri('en', 'cat', 'n', 'feline')
    '/c/en/cat/n/feline'
    >>> concept_uri('en', 'this is wrong')
    Traceback (most recent call last):
        ...
    AssertionError: 'this is wrong' is not in normalized form
    """
    assert text == normalize_text(text), "%r is not in normalized form" % text
    if pos is None:
        if disambiguation is not None:
            raise ValueError("Disambiguated concepts must have a part of speech")
        return join_uri('/c', lang, text)
    else:
        if disambiguation is None:
            return join_uri('/c', lang, text, pos)
        else:
            assert disambiguation == normalize_text(disambiguation),\
                "%r is not in normalized form" % disambiguation
            return join_uri('/c', lang, text, pos, disambiguation)


def compound_uri(op, args):
    """
    Some URIs represent a compound structure or operator built out of a number
    of arguments. Some examples are the '/and' and '/or' operators, which
    represent a conjunction or disjunction over two or more URIs, which may
    themselves be compound URIs; or the assertion structure, '/a', which takes
    a relation and two URIs as its arguments.

    This function takes the main 'operator', with the slash included, and an
    arbitrary number of arguments, and produces the URI that represents the
    entire compound structure.

    These structures contain square brackets as segments, which look like
    `/[/` and `/]/`, so that compound URIs can contain other compound URIs
    without ambiguity.

    >>> compound_uri('/nothing', [])
    '/nothing/[/]'
    >>> compound_uri('/a', ['/r/CapableOf', '/c/en/cat', '/c/en/sleep'])
    '/a/[/r/CapableOf/,/c/en/cat/,/c/en/sleep/]'
    """
    items = [op]
    first_item = True
    items.append('[')
    for arg in args:
        if first_item:
            first_item = False
        else:
            items.append(',')
        items.append(arg)
    items.append(']')
    return join_uri(*items)


def split_uri(uri):
    """
    Get the slash-delimited pieces of a URI.
        
    >>> split_uri('/c/en/cat/n/feline')
    ['c', 'en', 'cat', 'n', 'feline']
    >>> split_uri('/')
    []
    """
    uri2 = uri.lstrip('/')
    if not uri2:
        return []
    return uri2.split('/')


def parse_compound_uri(uri):
    """
    Given a compound URI, extract its operator and its list of arguments.

    >>> parse_compound_uri('/nothing/[/]')
    ('/nothing', [])
    >>> parse_compound_uri('/a/[/r/CapableOf/,/c/en/cat/,/c/en/sleep/]')
    ('/a', ['/r/CapableOf', '/c/en/cat', '/c/en/sleep'])
    >>> parse_compound_uri('/or/[/and/[/s/one/,/s/two/]/,/and/[/s/three/,/s/four/]/]')
    ('/or', ['/and/[/s/one/,/s/two/]', '/and/[/s/three/,/s/four/]'])
    """
    pieces = split_uri(uri)
    if pieces[-1] != ']':
        raise ValueError("Compound URIs must end with /]")
    if '[' not in pieces:
        raise ValueError("Compound URIs must contain /[/ at the beginning of "
                         "the argument list")
    list_start = pieces.index('[')
    op = join_uri(*pieces[:list_start])

    chunks = []
    current = []
    depth = 0

    # Split on commas, but not if they're within additional pairs of brackets.
    for piece in pieces[(list_start + 1):-1]:
        if piece == ',' and depth == 0:
            chunks.append('/' + ('/'.join(current)).strip('/'))
            current = []
        else:
            current.append(piece)
            if piece == '[':
                depth += 1
            elif piece == ']':
                depth -= 1

    assert depth == 0, "Unmatched brackets in %r" % uri
    if current:
        chunks.append('/' + ('/'.join(current)).strip('/'))
    return op, chunks


def parse_possible_compound_uri(op, uri):
    """
    The AND and OR conjunctions can be expressed as compound URIs, but if they
    contain only one thing, they are returned as just that single URI, not a
    compound.

    This function returns the list of things in the compound URI if its operator
    matches `op`, or a list containing the URI itself if not.

    >>> parse_possible_compound_uri(
    ...    'or', '/or/[/and/[/s/one/,/s/two/]/,/and/[/s/three/,/s/four/]/]'
    ... )
    ['/and/[/s/one/,/s/two/]', '/and/[/s/three/,/s/four/]']
    >>> parse_possible_compound_uri('or', '/s/contributor/omcs/dev')
    ['/s/contributor/omcs/dev']
    """
    if uri.startswith('/' + op + '/'):
        return parse_compound_uri(uri)[1]
    else:
        return [uri]


def conjunction_uri(*sources):
    """
    Make a URI representing a conjunction of sources that work together to provide
    an assertion. The sources will be sorted in lexicographic order.

    >>> conjunction_uri('/s/contributor/omcs/dev')
    '/s/contributor/omcs/dev'
    
    >>> conjunction_uri('/s/rule/some_kind_of_parser', '/s/contributor/omcs/dev')
    '/and/[/s/contributor/omcs/dev/,/s/rule/some_kind_of_parser/]'
    """
    if len(sources) == 0:
        # Logically, a conjunction with 0 inputs represents 'True', a
        # proposition that cannot be denied. This could be useful as a
        # justification for, say, mathematical axioms, but when it comes to
        # ConceptNet, that kind of thing makes us uncomfortable and shouldn't
        # appear in the data.
        raise ValueError("Conjunctions of 0 things are not allowed")
    elif len(sources) == 1:
        return sources[0]
    else:
        return compound_uri('/and', sorted(set(sources)))


def disjunction_uri(*sources):
    """
    Make a URI representing a choice of sources that provide the same assertion. The
    sources will be sorted in lexicographic order.

    >>> disjunction_uri('/s/contributor/omcs/dev')
    '/s/contributor/omcs/dev'

    >>> disjunction_uri('/s/contributor/omcs/rspeer', '/s/contributor/omcs/dev')
    '/or/[/s/contributor/omcs/dev/,/s/contributor/omcs/rspeer/]'
    """
    if len(sources) == 0:
        # If something has a disjunction of 0 sources, we have no reason to
        # believe it, and therefore it shouldn't be here.
        raise ValueError("Disjunctions of 0 things are not allowed")
    elif len(sources) == 1:
        return sources[0]
    else:
        return compound_uri('/or', sorted(set(sources)))


def assertion_uri(rel, *args):
    """
    Make a URI for an assertion.

    There will usually be two items in *args, the 'start' and 'end' of the
    assertion. However, this can support relations with different number
    of arguments.

    >>> assertion_uri('/r/CapableOf', '/c/en/cat', '/c/en/sleep')
    '/a/[/r/CapableOf/,/c/en/cat/,/c/en/sleep/]'
    """
    assert rel.startswith('/r')
    return compound_uri('/a', (rel,) + args)


def and_or_tree(list_of_lists):
    """
    An and-or tree represents a disjunction of conjunctions. In ConceptNet terms,
    it represents all the reasons we might believe a particular assertion.

    >>> and_or_tree([['/s/one', '/s/two'], ['/s/three', '/s/four']])
    '/or/[/and/[/s/four/,/s/three/]/,/and/[/s/one/,/s/two/]/]'
    """
    conjunctions = [conjunction_uri(*sublist) for sublist in list_of_lists]
    return disjunction_uri(*conjunctions)


class Licenses(object):
    cc_attribution = '/l/CC/By'
    cc_sharealike = '/l/CC/By-SA'

########NEW FILE########
__FILENAME__ = language_codes
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
"""
In building ConceptNet, we often need to be able to map from language
names to language codes, or vice versa.

So far, this is only supported for English names of languages, although
we will need translations of these names to say, parse entries from the
Japanese-language Wiktionary.

>>> CODE_TO_ENGLISH_NAME['fr']
'French'
>>> CODE_TO_ENGLISH_NAME['fra']
'French'
>>> ENGLISH_NAME_TO_CODE['French']
'fr'
"""

from conceptnet5.util import get_data_filename
import codecs
import re

ISO_DATA_FILENAME = get_data_filename('iso639.txt')

CODE_TO_ENGLISH_NAME = {}
ENGLISH_NAME_TO_CODE = {}

# The SUPPORTED_LANGUAGE_CODES are the ones that should appear in the
# browsable Web interface.
#
# This might be too many.
SUPPORTED_LANGUAGE_CODES = [
    'aa', 'ab', 'ae', 'af', 'ak', 'am', 'an', 'ar', 'as', 'ase', 'av', 'ay',
    'az', 'ba', 'be', 'bg', 'bh', 'bi', 'bm', 'bn', 'bo', 'br', 'bs', 'ca',
    'ce', 'ch', 'co', 'cr', 'crh', 'cs', 'cu', 'cv', 'cy', 'da', 'de', 'dv',
    'dz', 'ee', 'el', 'en', 'eo', 'es', 'et', 'eu', 'fa', 'ff', 'fi', 'fj',
    'fo', 'fr', 'fy', 'ga', 'gd', 'gl', 'gn', 'gu', 'gv', 'ha', 'he', 'hi',
    'ho', 'hr', 'ht', 'hu', 'hy', 'hz', 'ia', 'id', 'ie', 'ig', 'ii', 'ik',
    'io', 'is', 'it', 'iu', 'ja', 'jv', 'ka', 'kg', 'ki', 'kj', 'kk', 'kl',
    'km', 'kn', 'ko', 'kr', 'ks', 'ku', 'kv', 'kw', 'ky', 'la', 'lb', 'lg',
    'li', 'ln', 'lo', 'lt', 'lu', 'lv', 'mg', 'mh', 'mi', 'mk', 'ml', 'mn',
    'mr', 'ms', 'mt', 'my', 'na', 'nan', 'nb', 'nd', 'ne', 'ng', 'nl', 'nn',
    'no', 'nr', 'nv', 'ny', 'oc', 'oj', 'om', 'or', 'os', 'pa', 'pi', 'pl',
    'ps', 'pt', 'qu', 'rm', 'rn', 'ro', 'ru', 'rw', 'sa', 'sc', 'sco', 'sd',
    'se', 'sg', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'ss', 'st',
    'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tn', 'to',
    'tr', 'ts', 'tt', 'tw', 'ty', 'ug', 'uk', 'ur', 'uz', 've', 'vi', 'vo',
    'wa', 'wo', 'xh', 'yi', 'yo', 'za', 'zh', 'zu'
]

def _setup():
    """
    Read the tab-separated text file of language names, and create the
    forward and backward mappings between language codes and language names.
    """
    first_line = True
    for line in codecs.open(ISO_DATA_FILENAME, encoding='utf-8'):
        if first_line:
            first_line = False
            continue
        alpha3, morecodes, alpha2, language_name = line.rstrip('\n').split('\t')
        codes = []
        if alpha2:
            # Not every language has an alpha2 code, but it should be first in
            # the list if it does.
            codes.append(alpha2)
        # Every language has an ISO 639-3 alpha3 code.
        codes.append(alpha3)

        # The second column contains ISO 639-2 alpha3 codes. Some
        # languages have two different codes, a "terminology" and a
        # "bibliographic" code, apparently by historical accident.
        # If this is the case, the entry will look like:
        #
        #    xxx / yyy*
        multi_code_match = re.match(r'(...) / (...)\*', morecodes)
        if multi_code_match:
            assert multi_code_match.group(1) == alpha3
            codes.append(multi_code_match.group(2))

        for code in codes:
            CODE_TO_ENGLISH_NAME[code] = language_name
        ENGLISH_NAME_TO_CODE[language_name] = codes[0]

_setup()
if __name__ == '__main__':
    for code in SUPPORTED_LANGUAGE_CODES:
        print("%-4s %s" % (code, CODE_TO_ENGLISH_NAME[code]))


########NEW FILE########
__FILENAME__ = sounds_like
from __future__ import with_statement, print_function, unicode_literals, division
from conceptnet5.util import get_data_filename


PHONETIC_DICT = {}
def _setup():
    """
    Read the dictionary file, creating a mapping from words to their
    phonetics.

    When multiple pronunciations are given, keep the last one.
    """
    with open(get_data_filename('cmudict.0.7a')) as rhymelist:
        for line in rhymelist:
            if line.startswith(';;;'): continue
            word, phon = line.strip().split('  ')
            phon = phon.split(' ')
            PHONETIC_DICT[word] = phon
_setup()


def get_phonetic(text):
    """
    Given a string which could contain multiple words, get the sequence of
    phonemes are the pronunciation of the sequence of words.

    When a pronunciation is not known, use the letters to stand for
    themselves.

    >>> get_phonetic('thing')
    ['TH', 'IH1', 'NG']
    >>> get_phonetic('thingummy')
    ['T', 'H', 'I', 'N', 'G', 'U', 'M', 'M', 'Y']
    >>> get_phonetic('concept net')
    ['K', 'AA1', 'N', 'S', 'EH0', 'P', 'T', 'N', 'EH1', 'T']
    """
    parts = []
    for word in text.split():
        parts.extend(PHONETIC_DICT.get(word.upper(), list(word.upper())))
    return parts


def edit_distance(list1, list2):
    """
    Find the minimum number of insertions, deletions, or replacements required
    to turn list1 into list2, using the typical dynamic programming algorithm.

    >>> edit_distance('test', 'test')
    0
    >>> edit_distance([], [])
    0
    >>> edit_distance('test', 'toast')
    2
    >>> edit_distance(['T', 'EH1', 'S', 'T'], ['T', 'OH1', 'S', 'T'])
    1
    >>> edit_distance('xxxx', 'yyyyyyyy')
    8
    """
    m = len(list1)
    n = len(list2)
    data = [[0 for col in range(n+1)] for row in range(m+1)]
    for col in range(n+1):
        data[0][col] = col
    for row in range(m+1):
        data[row][0] = row
    for a in range(1, m+1):
        for b in range(1, n+1):
            if list1[a-1] == list2[b-1]:
                data[a][b] = data[a-1][b-1]
            else:
                data[a][b] = 1 + min(data[a-1][b], data[a][b-1], data[a-1][b-1])
    return data[m][n]


def longest_match(list1, list2):
    """
    Find the length of the longest substring match between list1 and list2.

    >>> longest_match([], [])
    0
    >>> longest_match('test', 'test')
    4
    >>> longest_match('test', 'toast')
    2
    >>> longest_match('supercalifragilisticexpialidocious', 'mystical californication')
    5
    """
    m = len(list1)
    n = len(list2)
    data = [[0 for col in range(n+1)] for row in range(m+1)]
    for a in range(1, m+1):
        for b in range(1, n+1):
            if list1[a-1] == list2[b-1]:
                data[a][b] = 1 + data[a-1][b-1]
            else:
                data[a][b] = 0
    maxes = [max(row) for row in data]
    return max(maxes)


def prefix_match(list1, list2):
    """
    Find the length of the longest common prefix of list1 and list2.

    >>> prefix_match([], [])
    0
    >>> prefix_match('test', 'test')
    4
    >>> prefix_match('test', 'toast')
    1
    >>> prefix_match('test', 'best')
    0
    >>> prefix_match([1, 2, 3, 4], [1, 2, 4, 8])
    2
    """
    for i in range(min(len(list1), len(list2)), 0, -1):
        if list1[:i] == list2[:i]:
            return i
    return 0


def suffix_match(list1, list2):
    """
    Find the length of the longest common suffix of list1 and list2.
    >>> suffix_match([], [])
    0
    >>> suffix_match('test', 'test')
    4
    >>> suffix_match('test', 'toast')
    2
    >>> suffix_match('test', 'best')
    3
    >>> suffix_match([1, 2, 3, 4], [1, 2, 4, 8])
    0
    """
    for i in range(min(len(list1), len(list2)), 0, -1):
        if list1[-i:] == list2[-i:]:
            return i
    return 0


def scaled_edit_distance_match(list1, list2):
    """
    The inverse edit distance between two lists, as a proportion of their
    minimum length. Think of this as the proportion of the characters
    that don't change when turning list1 into list2.

    >>> scaled_edit_distance_match('test', 'toast')
    0.5
    """
    return 1 - edit_distance(list1, list2) / min(len(list1), len(list2))


def scaled_suffix_match(list1, list2):
    """
    The length of the longest common suffix between two lists, as a
    proportion of their minimum length.

    >>> scaled_suffix_match('test', 'toast')
    0.5
    """
    return suffix_match(list1, list2) / min(len(list1), len(list2))


def scaled_prefix_match(list1, list2):
    """
    The length of the longest common prefix between two lists, as a
    proportion of their minimum length.
    
    >>> scaled_prefix_match('test', 'toast')
    0.25
    """
    return float(prefix_match(list1, list2)) / min(len(list1), len(list2))


def scaled_longest_match(list1, list2):
    """
    The length of the longest substring match between two lists, as a
    proportion of their minimum length.

    >>> scaled_longest_match('test', 'toast')
    0.5
    """
    return longest_match(list1, list2) / min(len(list1), len(list2))


def combined_score(list1, list2):
    """
    A combined measure of the similarity between two lists.

    This measure is the average of the four similarity measures above.
    """
    return (scaled_edit_distance_match(list1, list2)
            + scaled_suffix_match(list1, list2)
            + scaled_prefix_match(list1, list2)
            + scaled_longest_match(list1, list2)) / 4


def _sounds_like_score(text1, text2):
    """
    A measure of the similarity between two texts, via either their
    spelling or their phonetics. The higher this is, the more likely
    it is that one is a 'pun' on the other.
    """
    result = max(combined_score(text1.replace(' ', ''), text2.replace(' ', '')),
                 combined_score(get_phonetic(text1), get_phonetic(text2)))
    return result


def sounds_like_score(target, clue):
    """
    A measure of the similarity between a target word and a 'clue' for that word.
    If the clue as a whole "sounds like" the target word, or each word within it
    does, it is likely that the clue is a pun-based clue, not a meaning-based
    clue.

    >>> sounds_like_score('heat', 'feat meat')
    0.5625
    >>> sounds_like_score('fish', 'chips')
    0.08333333333333333
    """
    subscores = []
    for word in clue.split():
        subscores.append(_sounds_like_score(target, word))
    scores = [_sounds_like_score(target, clue),
              sum(subscores) / len(subscores)]
    return max(scores)


def test(cutoff=0.35):
    """
    Test our heuristics by checking some known positive and negative cases.
    """
    # Positive tests: these should all be greater than the cutoff
    assert sounds_like_score('ham', 'spam') > cutoff
    assert sounds_like_score('research', 're search') > cutoff
    assert sounds_like_score('feet', 'eat') > cutoff
    assert sounds_like_score('mother', 'other') > cutoff
    assert sounds_like_score('fish', 'swish') > cutoff 
    assert sounds_like_score('heat', 'feat meat') > cutoff 
    assert sounds_like_score('love', 'above') > cutoff 
    assert sounds_like_score('love', 'of') > cutoff 

    # Negative tests: these are not sufficiently similar, and should be
    # less than the cutoff
    assert sounds_like_score('spam', 'eggs') < cutoff
    assert sounds_like_score('cow', 'logical') < cutoff
    assert sounds_like_score('sister', 'brother') < cutoff
    assert sounds_like_score('a', 'b') < cutoff 
    assert sounds_like_score('fish', 'chips') < cutoff 
    assert sounds_like_score('behind', 'not') < cutoff 
    assert sounds_like_score('name', 'nomenclature') < cutoff 
    assert sounds_like_score('clothing', 'covering') < cutoff 
    assert sounds_like_score('love', 'of another') < cutoff


if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = utils
from __future__ import unicode_literals
"""
Utility functions for web interface.
"""

__author__ = 'Justin Venezuela (jven@mit.edu)'

from conceptnet5.util.language_codes import SUPPORTED_LANGUAGE_CODES, CODE_TO_ENGLISH_NAME


def data_url(uri):
    return '/web/' + uri.strip('/')


def uri2name(arg):
    if arg.startswith('/c/'):
        if len(arg.split('/')) <= 3:
            return arg.split('/')[-1]
        result = arg.split('/')[3].replace('_', ' ')
    else:
        result = arg.split('/')[-1].replace('_', ' ')
    if result.startswith('be ') or result.startswith('to '):
        result = result[3:]
    return result


def get_sorted_languages():
    return [
        (lang, CODE_TO_ENGLISH_NAME[lang])
        for lang in SUPPORTED_LANGUAGE_CODES
    ]

########NEW FILE########
__FILENAME__ = web_interface
"""
Web interface for ConceptNet5.

Minimally updated in March 2014 to maintain compatibility, but it needs to be
revised.
"""

__author__ = 'Justin Venezuela (jven@mit.edu)'

# Python 2/3 compatibility
import sys
if sys.version_info.major < 3:
    from urllib import urlencode, quote
    from urllib2 import urlopen
else:
    from urllib.parse import urlencode, quote
    from urllib.request import urlopen

import os
import json
import re
from flask import Flask
from flask import redirect
from flask import render_template
from flask import request
from flask import send_from_directory
from conceptnet5.nodes import normalized_concept_uri
from conceptnet5.web_interface.utils import uri2name, get_sorted_languages

LANGUAGES = get_sorted_languages()

########################
# Set this flag to True when developing, False otherwise! -JVen
#
DEVELOPMENT = False
#
########################

app = Flask(__name__)

if DEVELOPMENT:
  site = 'http://new-caledonia.media.mit.edu:8080'
  web_root = ''
else:
  site = 'http://conceptnet5.media.mit.edu'
  web_root = '/web'

json_root = 'http://conceptnet5.media.mit.edu/data/5.2/'

import logging
file_handler = logging.FileHandler('logs/web_errors.log')
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)

def get_json_from_uri(uri, params):
    url = uri.lstrip(u'/')
    url_bytes = url.encode('utf-8')
    url_quoted = quote(url_bytes)
    params_quoted = urlencode(params)
    if params_quoted:
        params_quoted = '?'+params_quoted
    full_url = json_root + url_quoted + params_quoted
    return json.load(urlopen(full_url))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'img'), 'favicon.ico',
        mimetype='image/vnd.microsoft.icon')

@app.route('/')
def home():
    return render_template('home.html', languages=LANGUAGES)
    
@app.route('/concept/<path:uri>')
def concept_redirect(uri):
    return redirect(site + web_root + '/c/'+uri)

@app.route('/relation/<path:uri>')
def rel_redirect(uri):
    return redirect(site + web_root + '/r/'+uri)

@app.route('/search', methods=['POST'])
def search():
    keyword = request.form.get('keyword')
    lang = request.form.get('language')
    return redirect(site + web_root + normalized_concept_uri(lang, keyword))

@app.route('/<path:uri>', methods=['GET'])
def edges_for_uri(uri):
    """
    This function replaces most functions in the old Web interface, as every
    query to the API now returns a list of edges.
    """
    uri = u'/'+uri.rstrip(u'/')
    response = get_json_from_uri(uri, {'limit': 100})
    edges = response.get('edges', [])
    seen_edges = {}
    out_edges = []
    caption = uri
    for edge in edges:
        switched = False
        if edge['uri'] not in seen_edges:
            url1 = web_root+edge['start']
            url2 = web_root+edge['end']
            edge['startName'] = uri2name(edge['start'])
            edge['relName'] = uri2name(edge['rel'])
            edge['endName'] = uri2name(edge['end'])
            text = edge.get('surfaceText') or ''
            if caption == uri and edge['start'] == uri:
                caption = edge['startName']
            if caption == uri and edge['end'] == uri:
                caption = edge['endName']

            ## possible guess:
            #  "[[%s]] %s [[%s]]" %\
            #  (uri2name(edge['start']), uri2name(edge['rel']),
            #   uri2name(edge['end']))

            linked1 = re.sub(r'\[\[([^\]]+)\]\]',
                r'<a href="%s">\1</a>' % url1, text, count=1)
            linked2 = re.sub(r'\[\[([^\]]+)\]\]',
                r'<a href="%s">\1</a>' % url2, linked1, count=1)
            edge['linked'] = linked2
            out_edges.append(edge)
            seen_edges[edge['uri']] = edge
        else:
            oldedge = seen_edges[edge['uri']]
            oldedge['score'] += edge['score']
            if not oldedge.get('linked'):
                text = edge.get('surfaceText') or ''
                url1 = web_root+edge['start']
                url2 = web_root+edge['end']
                linked1 = re.sub(r'\[\[([^\]]+)\]\]',
                    r'<a href="%s">\1</a>' % url1, text, count=1)
                linked2 = re.sub(r'\[\[([^\]]+)\]\]',
                    r'<a href="%s">\1</a>' % url2, linked1, count=1)
                oldedge['linked'] = linked2

    if not edges:
        return render_template('not_found.html', uri=uri, languages=LANGUAGES)
    else:
        return render_template('edges.html', uri=uri, caption=caption,
        edges=out_edges, root=web_root, languages=LANGUAGES)

@app.errorhandler(404)
def handler404(error):
    return render_template('404.html', languages=LANGUAGES)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)

########NEW FILE########
__FILENAME__ = wsgi_api
from conceptnet5.api import app as application

########NEW FILE########
__FILENAME__ = wsgi_web
from conceptnet5.web_interface.web_interface import app as application

########NEW FILE########
__FILENAME__ = add_weights
import json
import codecs
from collections import defaultdict

responses = json.load(open('responses/all_responses.json'))
edge_ids = set()
edge_values = defaultdict(float)

for response_group in responses:
    for id in response_group['values']:
        edge_ids.add('/e/'+id)

count = 0
for line in codecs.open('../import/data/flat/ALL.csv'):
    uri, rel, start, end, context, weight, sources, id, rest = line.split('\t', 8)
    if weight == 'weight': continue
    weight = float(weight)
    count += 1
    if count % 10000 == 0:
        print count
    if id in edge_ids:
        if weight < 0:
            print id, weight
        edge_values[id] = float(weight)

for response_group in responses:
    for id, response in response_group['values'].items():
        response['weight'] = edge_values['/e/'+id]

out = open('responses/with_weights.json', 'w')
json.dump(responses, out, indent=2)

########NEW FILE########
__FILENAME__ = evaluate
from flask import Flask, redirect, render_template, request, send_from_directory
import random
import os
import time
import json
import codecs

app = Flask(__name__)
@app.route('/')
def randomize():
    prefix = "%04x" % random.randrange(0, 16**4)
    
    return redirect('/evaluate/%s' % prefix)

def readable(uri):
    parts = uri.split('/')
    disambig = None
    if len(parts) > 5:
        disambig = uri.split('/')[5].replace('_', ' ')
    if uri.startswith('/r/'):
        concept = uri.split('/')[2].replace('_', ' ')
        if concept == 'InstanceOf':
            concept = 'is a'
    else:
        concept = uri.split('/')[3].replace('_', ' ')
    if disambig:
        return u'%s (<i>%s</i>)' % (concept, disambig)
    else:
        return concept

@app.route('/respond', methods=['POST'])
def respond():
    data = {}
    for key in request.form:
        type, id = key.split('-')
        if not data.has_key(id):
            data[id] = {}
        data[id][type] = request.form[key]

    results = {
        'headers': dict(request.headers),
        'values': data
    }
    out = open('responses/%d' % time.time(), 'w')
    json.dump(results, out, indent=2)
    return render_template('thanks.html')


@app.route('/evaluate/<prefix>')
def evaluate(prefix):
    assert len(prefix) == 4 and all([letter in '0123456789abcdef' for letter in prefix])
    # crappy way to get data! go!
    prefix3 = prefix[:3]
    if not os.access('data/%s.csv' % prefix3, os.F_OK):
        os.system("grep /e/%s ../import/data/flat/all.csv > data/%s.csv" % (prefix3, prefix3))
    skipped = False
    statements = []
    random.seed(int(prefix, 16))
    for line in codecs.open('data/%s.csv' % prefix3, encoding='utf-8'):
        if not skipped:
            skipped = True
        else:
            uri, rel, start, end, context, weight, sources, id, dataset, text = line.strip('\n').split('\t')
            if 'dbpedia' in dataset and random.random() > .25:
                continue
            elif 'wiktionary' in dataset and random.random() > .5:
                continue
            if ':' in start or ':' in end or 'Wiktionary' in line or 'Category' in line:
                continue
            if not '/c/en' in line:
                continue
            if text is None or text == 'None':
                subj = readable(start)
                obj = readable(end)
                rel = readable(rel)
                text = "[[%s]] %s [[%s]]" % (subj, rel, obj)

            text = text.replace('[[', '<b>').replace(']]', '</b>')
            if weight < 0:
                uri += '/'
            statements.append(dict(
                id=id[3:],
                uri=uri,
                dataset=dataset,
                text=text,
                weight=weight
            ))

    neg_statements = [s for s in statements if s['weight'] < 0]
    pos_statements = [s for s in statements if s['weight'] > 0]
    num_to_sample = min(len(pos_statements), max(1, 25 - len(neg_statements)))
    shown_statements = neg_statements + random.sample(pos_statements, num_to_sample)
    random.shuffle(shown_statements)

    return render_template('evaluate.html', statements=shown_statements)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)

########NEW FILE########
__FILENAME__ = tally
import json
import codecs
from collections import defaultdict

responses = json.load(open('responses/with_weights.json'))
by_dataset = defaultdict(lambda: defaultdict(float))

for response_group in responses:
    for response in response_group['values'].values():
        if response.has_key('rating'):
            dataset = response['dataset']
            rating = response['rating']
            weight = response['weight']
            if weight < 0:
                dataset = 'negated'
            if 'globalmind' in dataset and 'Translation' in response['uri']:
                dataset = '/d/globalmind/tr'
            if dataset.startswith('/d/conceptnet/4') and dataset != '/d/conceptnet/4/en':
                dataset = '/d/conceptnet/4/other'
            if dataset.startswith('/d/wiktionary') and dataset != '/d/wiktionary/en/en':
                dataset = '/d/wiktionary/other'
            by_dataset[dataset][rating] += 1

out = open('responses/by_dataset.json', 'w')
json.dump(by_dataset, out, default=dict, indent=2)

########NEW FILE########
__FILENAME__ = test_readers
from conceptnet5.util import get_data_filename
from conceptnet5.readers import (
    conceptnet4, dbpedia, jmdict, ptt_petgame, verbosity, wiktionary_en, wordnet
)
from conceptnet5.builders.combine_assertions import AssertionCombiner
import codecs
import os
import sys
import json
from nose.tools import eq_

if sys.version_info.major < 3:
    from StringIO import StringIO
else:
    from io import StringIO


TESTDATA_DIR = get_data_filename("testdata")
def data_path(filename):
    return os.path.join(TESTDATA_DIR, filename)


# This is a multi-test: it generates a sequence of tests, consisting of the
# function to run and the arguments to give it. nosetests knows how to run
# tests with this structure.
def test_reader_modules():
    combiner = AssertionCombiner('/l/CC/By-SA')
    io_mappings = [
        (conceptnet4, 'input/conceptnet4.jsons', ['output/conceptnet4.jsons']),
        (dbpedia, 'input/dbpedia.nt', ['output/dbpedia.jsons', 'output/dbpedia_map.nt']),
        (jmdict, 'input/jmdict.xml', ['output/jmdict.jsons']),
        (ptt_petgame, 'input/ptt_petgame.csv', ['output/ptt_petgame.jsons']),
        (verbosity, 'input/verbosity.txt', ['output/verbosity.jsons']),
        (wiktionary_en, 'input/wiktionary.xml', ['output/wiktionary.jsons']),
        (wordnet, 'input/wordnet', ['output/wordnet.jsons', 'output/wordnet_map.nt']),
        (combiner, 'input/combiner.csv', ['output/combiner.jsons'])
    ]
    for (reader_module, input, outputs) in io_mappings:
        yield compare_input_and_output, reader_module, input, outputs


def compare_input_and_output(reader_module, input, outputs):
    handle_file = getattr(reader_module, 'handle_file')
    input_filename = data_path(input)
    output_filenames = [data_path(output) for output in outputs]
    output_streams = [StringIO() for _ in output_filenames]
    
    # Every reader module has a 'handle_file' function, with one input and
    # up to two outputs.
    #
    # We run these functions on the appropriate input files, with output
    # "files" that are actually StringIO instances. We then compare the
    # StringIO contents to the desired output, found in the reference output
    # files with the given filenames.
    handle_file(input_filename, *output_streams)
    for (reference_output_filename, output_stream) in zip(output_filenames, output_streams):
        reference_output_file = codecs.open(reference_output_filename, encoding='utf-8')
        reference_lines = reference_output_file.readlines()
        actual_lines = output_stream.getvalue().split('\n')
        for line1, line2 in zip(reference_lines, actual_lines):
            if reference_output_filename.endswith('.jsons'):
                eq_(json.loads(line1), json.loads(line2))
            else:
                eq_(line1.rstrip('\n'), line2)

########NEW FILE########
__FILENAME__ = test_sounds_like
def test_sounds_like():
    from conceptnet5.util import sounds_like
    sounds_like.test()

########NEW FILE########
