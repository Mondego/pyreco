__FILENAME__ = build
import os
import pickle
import sqlite3

import jellyfish

PWD = os.path.abspath(os.path.dirname(__file__))


def dict_factory(cursor, row):
    return dict((col[0], row[idx]) for idx, col in enumerate(cursor.description))


def pickle_data():

    dbpath = os.path.abspath(os.path.join(PWD, 'data.db'))

    conn = sqlite3.connect(dbpath)
    conn.row_factory = dict_factory

    c = conn.cursor()
    c.execute("""SELECT * FROM states ORDER BY name""")

    states = []

    for row in c:
        row['name_metaphone'] = jellyfish.metaphone(row['name'])
        row['is_territory'] = row['is_territory'] == 1
        row['is_obsolete'] = row['is_obsolete'] == 1
        row['time_zones'] = row['time_zones'].split(',')
        states.append(row)

    pkl_path = os.path.abspath(os.path.join(PWD, 'us', 'states.pkl'))

    with open(pkl_path, 'wb') as pkl_file:
        pickle.dump(states, pkl_file)


def build():
    pickle_data()


if __name__ == '__main__':
    build()

########NEW FILE########
__FILENAME__ = tests
import unittest
import requests

import us


class AttributeTestCase(unittest.TestCase):

    def test_attribute(self):

        for state in us.STATES_AND_TERRITORIES:
            self.assertEqual(state, getattr(us.states, state.abbr))


class MarylandLookupTestCase(unittest.TestCase):

    def test_fips(self):
        self.assertEqual(us.states.lookup('24'), us.states.MD)
        self.assertNotEqual(us.states.lookup('51'), us.states.MD)

    def test_abbr(self):
        self.assertEqual(us.states.lookup('MD'), us.states.MD)
        self.assertEqual(us.states.lookup('md'), us.states.MD)
        self.assertNotEqual(us.states.lookup('VA'), us.states.MD)
        self.assertNotEqual(us.states.lookup('va'), us.states.MD)

    def test_name(self):
        self.assertEqual(us.states.lookup('Maryland'), us.states.MD)
        self.assertEqual(us.states.lookup('maryland'), us.states.MD)
        self.assertEqual(us.states.lookup('Maryland', field='name'), us.states.MD)
        self.assertEqual(us.states.lookup('maryland', field='name'), None)
        self.assertEqual(us.states.lookup('murryland'), us.states.MD)
        self.assertNotEqual(us.states.lookup('Virginia'), us.states.MD)


class MappingTestCase(unittest.TestCase):

    def test_mapping(self):

        states = us.STATES[:5]

        self.assertEqual(
            us.states.mapping('abbr', 'fips', states=states),
            dict((s.abbr, s.fips) for s in states))


class KnownBugsTestCase(unittest.TestCase):

    def test_kentucky_uppercase(self):
        self.assertEqual(us.states.lookup('kentucky'), us.states.KY)
        self.assertEqual(us.states.lookup('KENTUCKY'), us.states.KY)


class ShapefileTestCase(unittest.TestCase):

    def test_head(self):

        for state in us.STATES_AND_TERRITORIES:

            for region, url in state.shapefile_urls().items():
                resp = requests.head(url)
                self.assertEqual(resp.status_code, 200)


class CountsTestCase(unittest.TestCase):

    def test_obsolete(self):
        self.assertEqual(len(us.OBSOLETE), 3)

    def test_states(self):
        self.assertEqual(len(us.STATES), 51)

    def test_territories(self):
        self.assertEqual(len(us.TERRITORIES), 5)



if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = states
import sys
import us


def main():

    import argparse

    parser = argparse.ArgumentParser(description='Lookup state information')
    parser.add_argument('query', metavar='QUERY', nargs=1,
                   help='name, abbreviation, or FIPS code')

    args = parser.parse_args()

    state = us.states.lookup(args.query[0])

    if not state:
        sys.stdout.write("Sorry, couldn't find a matching state.\n")

    else:

        data = state.__dict__.copy()

        region = 'territory' if data.pop('is_territory') else 'state'

        sys.stdout.write("\n")
        sys.stdout.write("*** The great %s of %s (%s) ***\n\n" % (region, data.pop('name'), data.pop('abbr')))

        sys.stdout.write("  FIPS code: %s\n" % data.pop('fips'))

        sys.stdout.write("\n")
        sys.stdout.write("  other attributes:\n")

        for key in sorted(data.keys()):

            val = data[key]

            if isinstance(val, (list, tuple)):
                val = ", ".join(val)

            sys.stdout.write("    %s: %s\n" % (key, val))

        sys.stdout.write("\n")
        sys.stdout.write("  shapefiles:\n")
        for region, url in state.shapefile_urls().items():
            sys.stdout.write("    %s: %s\n" % (region, url))

        sys.stdout.write("\n")


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = states
import pickle
import re

FIPS_RE = re.compile(r'^\d{2}$')
ABBR_RE = re.compile(r'^[a-zA-Z]{2}$')

STATES = []
TERRITORIES = []
OBSOLETE = []
STATES_AND_TERRITORIES = []

_lookup_cache = {}


class State(object):

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            self.__dict__[k] = v

    def __repr__(self):
        return "<State:%s>" % self.name

    def __str__(self):
        return self.name

    def shapefile_urls(self, region=None):

        if not self.fips:
            return {}

        base_url = "http://www2.census.gov/geo/tiger/TIGER2010"
        urls = {
            'tract': base_url + '/TRACT/2010/tl_2010_%s_tract10.zip' % self.fips,
            'cd': base_url + '/CD/111/tl_2010_%s_cd111.zip' % self.fips,
            'county': base_url + '/COUNTY/2010/tl_2010_%s_county10.zip' % self.fips,
            'state': base_url + '/STATE/2010/tl_2010_%s_state10.zip' % self.fips,
            'zcta': base_url + '/ZCTA5/2010/tl_2010_%s_zcta510.zip' % self.fips,
            'block': base_url + '/TABBLOCK/2010/tl_2010_%s_tabblock10.zip' % self.fips,
            'blockgroup': base_url + '/BG/2010/tl_2010_%s_bg10.zip' % self.fips
        }

        if region and region in urls:
            return urls[region]

        return urls


def load_states():
    """ Load state data from pickle file distributed with this package.

        Creates lists of states, territories, and combined states and
        territories. Also adds state abbreviation attribute access
        to the package: us.states.MD
    """

    from pkg_resources import resource_stream

    # load state data from pickle file
    with resource_stream(__name__, 'states.pkl') as pklfile:
        for s in pickle.load(pklfile):

            state = State(**s)  # create state object

            # create separate lists for obsolete, states, and territories
            if state.is_obsolete:
                OBSOLETE.append(state)
            elif state.is_territory:
                TERRITORIES.append(state)
            else:
                STATES.append(state)

            # also create list of all states and territories
            STATES_AND_TERRITORIES.append(state)

            # provide package-level abbreviation access: us.states.MD
            globals()[state.abbr] = state


def lookup(val, field=None, use_cache=True):
    """ Semi-fuzzy state lookup. This method will make a best effort
        attempt at finding the state based on the lookup value provided.

          * two digits will search for FIPS code
          * two letters will search for state abbreviation
          * anything else will try to match the metaphone of state names

        Metaphone is used to allow for incorrect, but phonetically accurate,
        spelling of state names.

        Exact matches can be done on any attribute on State objects by passing
        the `field` argument. This skips the fuzzy-ish matching and does an
        exact, case-sensitive comparison against the specified field.

        This method caches non-None results, but can the cache can be bypassed
        with the `use_cache=False` argument.
    """

    import jellyfish

    if field is None:
        if FIPS_RE.match(val):
            field = 'fips'
        elif ABBR_RE.match(val):
            val = val.upper()
            field = 'abbr'
        else:
            val = jellyfish.metaphone(val)
            field = 'name_metaphone'

    # see if result is in cache
    cache_key = "%s:%s" % (field, val)
    if use_cache and cache_key in _lookup_cache:
        return _lookup_cache[cache_key]

    for state in STATES_AND_TERRITORIES:
        if val == getattr(state, field):
            _lookup_cache[cache_key] = state
            return state


def mapping(from_field, to_field, states=None):
    if states is None:
        states = STATES_AND_TERRITORIES
    return dict((getattr(s, from_field), getattr(s, to_field)) for s in states)


load_states()

########NEW FILE########
__FILENAME__ = unitedstatesofamerica
name = 'United States of America'
abbr = 'US'

########NEW FILE########
