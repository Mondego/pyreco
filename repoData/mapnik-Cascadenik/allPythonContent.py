__FILENAME__ = compile
import os, sys
import math
import urllib
import urllib2
import tempfile
import StringIO
import operator
import base64
import posixpath
import os.path as systempath
import zipfile
import shutil

from hashlib import md5
from datetime import datetime
from time import strftime, localtime
from re import sub, compile, MULTILINE
from urlparse import urlparse, urljoin
from operator import lt, le, eq, ge, gt

# os.path.relpath was added in Python 2.6
def _relpath(path, start=posixpath.curdir):
    """Return a relative version of a path"""
    if not path:
        raise ValueError("no path specified")
    start_list = posixpath.abspath(start).split(posixpath.sep)
    path_list = posixpath.abspath(path).split(posixpath.sep)
    i = len(posixpath.commonprefix([start_list, path_list]))
    rel_list = [posixpath.pardir] * (len(start_list)-i) + path_list[i:]
    if not rel_list:
        return posixpath.curdir
    return posixpath.join(*rel_list)

# timeout parameter to HTTPConnection was added in Python 2.6
if sys.hexversion >= 0x020600F0:
    from httplib import HTTPConnection, HTTPSConnection

else:
    posixpath.relpath = _relpath
    
    from httplib import HTTPConnection as _HTTPConnection
    from httplib import HTTPSConnection as _HTTPSConnection
    import socket
    
    def HTTPConnection(host, port=None, strict=None, timeout=None):
        if timeout:
            socket.setdefaulttimeout(timeout)
        return _HTTPConnection(host, port=port, strict=strict)

    def HTTPSConnection(host, port=None, strict=None, timeout=None):
        if timeout:
            socket.setdefaulttimeout(timeout)
        return _HTTPSConnection(host, port=port, strict=strict)


# cascadenik
from . import safe64, style, output, sources
from . import MAPNIK_VERSION, MAPNIK_VERSION_STR
from .nonposix import un_posix, to_posix
from .parse import stylesheet_declarations
from .style import uri

try:
    from PIL import Image
except ImportError:
    try:
        import Image
    except ImportError:
        Image = False

if not Image:
    warn = 'Warning: PIL (Python Imaging Library) is required for proper handling of image symbolizers when using JPEG format images or not running Mapnik >=0.7.0\n'
    sys.stderr.write(warn)

DEFAULT_ENCODING = 'utf-8'

try:
    import xml.etree.ElementTree as ElementTree
    from xml.etree.ElementTree import Element
except ImportError:
    try:
        import lxml.etree as ElementTree
        from lxml.etree import Element
    except ImportError:
        import elementtree.ElementTree as ElementTree
        from elementtree.ElementTree import Element

opsort = {lt: 1, le: 2, eq: 3, ge: 4, gt: 5}
opstr = {lt: '<', le: '<=', eq: '==', ge: '>=', gt: '>'}

VERBOSE = False

def msg(msg):
    if VERBOSE:
        sys.stderr.write('Cascadenik debug: %s\n' % msg)

counter = 0

def next_counter():
    global counter
    counter += 1
    return counter

def url2fs(url):
    """ encode a URL to be safe as a filename """
    uri, extension = posixpath.splitext(url)
    return safe64.dir(uri) + extension

def fs2url(url):
    """ decode a filename to the URL it is derived from """
    return safe64.decode(url)

def indent(elem, level=0):
    """ http://infix.se/2007/02/06/gentlemen-indent-your-xml
    """
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level+1)
            if not e.tail or not e.tail.strip():
                e.tail = i + "  "
        if not e.tail or not e.tail.strip():
            e.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

class Directories:
    """ Holder for full paths to output and cache dirs.
    """
    def __init__(self, output, cache, source):
        self.output = posixpath.realpath(to_posix(output))
        self.cache = posixpath.realpath(to_posix(cache))

        scheme, n, path, p, q, f = urlparse(to_posix(source))
        
        if scheme in ('http','https'):
            self.source = source
        elif scheme in ('file', ''):
            # os.path (systempath) usage here is intentional...
            self.source = 'file://' + to_posix(systempath.realpath(path))
        assert self.source, "self.source does not exist: source was: %s" % source

    def output_path(self, path_name):
        """ Modify a path so it fits expectations.
        
            Avoid returning relative paths that start with '../' and possibly
            return relative paths when output and cache directories match.
        """        
        # make sure it is a valid posix format
        path = to_posix(path_name)
        
        assert (path == path_name), "path_name passed to output_path must be in posix format"
        
        if posixpath.isabs(path):
            if self.output == self.cache:
                # worth seeing if an absolute path can be avoided
                path = posixpath.relpath(path, self.output)

            else:
                return posixpath.realpath(path)
    
        if path.startswith('../'):
            joined = posixpath.join(self.output, path)
            return posixpath.realpath(joined)
    
        return path

class Range:
    """ Represents a range for use in min/max scale denominator.
    
        Ranges can have a left side, a right side, neither, or both,
        with sides specified as inclusive or exclusive.
    """
    def __init__(self, leftop=None, leftedge=None, rightop=None, rightedge=None):
        assert leftop in (lt, le, eq, ge, gt, None)
        assert rightop in (lt, le, eq, ge, gt, None)

        self.leftop = leftop
        self.rightop = rightop
        self.leftedge = leftedge
        self.rightedge = rightedge

    def midpoint(self):
        """ Return a point guranteed to fall within this range, hopefully near the middle.
        """
        minpoint = self.leftedge

        if self.leftop is gt:
            minpoint += 1
    
        maxpoint = self.rightedge

        if self.rightop is lt:
            maxpoint -= 1

        if minpoint is None:
            return maxpoint
            
        elif maxpoint is None:
            return minpoint
            
        else:
            return (minpoint + maxpoint) / 2

    def isOpen(self):
        """ Return true if this range has any room in it.
        """
        if self.leftedge and self.rightedge and self.leftedge > self.rightedge:
            return False
    
        if self.leftedge == self.rightedge:
            if self.leftop is gt or self.rightop is lt:
                return False

        return True
    
    def toFilter(self, property):
        """ Convert this range to a Filter with a tests having a given property.
        """
        if self.leftedge == self.rightedge and self.leftop is ge and self.rightop is le:
            # equivalent to ==
            return Filter(style.SelectorAttributeTest(property, '=', self.leftedge))
    
        try:
            return Filter(style.SelectorAttributeTest(property, opstr[self.leftop], self.leftedge),
                          style.SelectorAttributeTest(property, opstr[self.rightop], self.rightedge))
        except KeyError:
            try:
                return Filter(style.SelectorAttributeTest(property, opstr[self.rightop], self.rightedge))
            except KeyError:
                try:
                    return Filter(style.SelectorAttributeTest(property, opstr[self.leftop], self.leftedge))
                except KeyError:
                    return Filter()
    
    def __repr__(self):
        """
        """
        if self.leftedge == self.rightedge and self.leftop is ge and self.rightop is le:
            # equivalent to ==
            return '(=%s)' % self.leftedge
    
        try:
            return '(%s%s ... %s%s)' % (self.leftedge, opstr[self.leftop], opstr[self.rightop], self.rightedge)
        except KeyError:
            try:
                return '(... %s%s)' % (opstr[self.rightop], self.rightedge)
            except KeyError:
                try:
                    return '(%s%s ...)' % (self.leftedge, opstr[self.leftop])
                except KeyError:
                    return '(...)'

class Filter:
    """ Represents a filter of some sort for use in stylesheet rules.
    
        Composed of a list of tests.
    """
    def __init__(self, *tests):
        self.tests = list(tests)

    def isOpen(self):
        """ Return true if this filter is not trivially false, i.e. self-contradictory.
        """
        equals = {}
        nequals = {}
        
        for test in self.tests:
            if test.op == '=':
                if equals.has_key(test.property) and test.value != equals[test.property]:
                    # we've already stated that this arg must equal something else
                    return False
                    
                if nequals.has_key(test.property) and test.value in nequals[test.property]:
                    # we've already stated that this arg must not equal its current value
                    return False
                    
                equals[test.property] = test.value
        
            if test.op == '!=':
                if equals.has_key(test.property) and test.value == equals[test.property]:
                    # we've already stated that this arg must equal its current value
                    return False
                    
                if not nequals.has_key(test.property):
                    nequals[test.property] = set()

                nequals[test.property].add(test.value)
        
        return True

    def clone(self):
        """
        """
        return Filter(*self.tests[:])
    
    def minusExtras(self):
        """ Return a new Filter that's equal to this one,
            without extra terms that don't add meaning.
        """
        assert self.isOpen()
        
        trimmed = self.clone()
        
        equals = {}
        
        for test in trimmed.tests:
            if test.op == '=':
                equals[test.property] = test.value

        extras = []

        for (i, test) in enumerate(trimmed.tests):
            if test.op == '!=' and equals.has_key(test.property) and equals[test.property] != test.value:
                extras.append(i)

        while extras:
            trimmed.tests.pop(extras.pop())

        return trimmed
    
    def __repr__(self):
        """
        """
        return ''.join(map(repr, sorted(self.tests)))
    
    def __cmp__(self, other):
        """
        """
        # get the scale tests to the front of the line, followed by regular alphabetical
        key_func = lambda t: (not t.isMapScaled(), t.property, t.op, t.value)

        # extract tests into cleanly-sortable tuples
        self_tuples = [(t.property, t.op, t.value) for t in sorted(self.tests, key=key_func)]
        other_tuples = [(t.property, t.op, t.value) for t in sorted(other.tests, key=key_func)]
        
        return cmp(self_tuples, other_tuples)

def test_ranges(tests):
    """ Given a list of tests, return a list of Ranges that fully describes
        all possible unique ranged slices within those tests.
        
        This function was hard to write, it should be hard to read.
        
        TODO: make this work for <= following by >= in breaks
    """
    if len(tests) == 0:
        return [Range()]
    
    assert 1 == len(set(test.property for test in tests)), 'All tests must share the same property'
    assert True in [test.isRanged() for test in tests], 'At least one test must be ranged'
    assert False not in [test.isNumeric() for test in tests], 'All tests must be numeric'
    
    repeated_breaks = []
    
    # start by getting all the range edges from the selectors into a list of break points
    for test in tests:
        repeated_breaks.append(test.rangeOpEdge())

    # from here on out, *order will matter*
    # it's expected that the breaks will be sorted from minimum to maximum,
    # with greater/lesser/equal operators accounted for.
    repeated_breaks.sort(key=lambda (o, e): (e, opsort[o]))
    
    breaks = []

    # next remove repetitions from the list
    for (i, (op, edge)) in enumerate(repeated_breaks):
        if i > 0:
            if op is repeated_breaks[i - 1][0] and edge == repeated_breaks[i - 1][1]:
                continue

        breaks.append(repeated_breaks[i])

    ranges = []
    
    # now turn those breakpoints into a list of ranges
    for (i, (op, edge)) in enumerate(breaks):
        if i == 0:
            # get a right-boundary for the first range
            if op in (lt, le):
                ranges.append(Range(None, None, op, edge))
            elif op is ge:
                ranges.append(Range(None, None, lt, edge))
            elif op is gt:
                ranges.append(Range(None, None, le, edge))
            elif op is eq:
                # edge case
                ranges.append(Range(None, None, lt, edge))
                ranges.append(Range(ge, edge, le, edge))

        elif i > 0:
            # get a left-boundary based on the previous right-boundary
            if ranges[-1].rightop is lt:
                ranges.append(Range(ge, ranges[-1].rightedge))
            else:
                ranges.append(Range(gt, ranges[-1].rightedge))

            # get a right-boundary for the current range
            if op in (lt, le):
                ranges[-1].rightop, ranges[-1].rightedge = op, edge
            elif op in (eq, ge):
                ranges[-1].rightop, ranges[-1].rightedge = lt, edge
            elif op is gt:
                ranges[-1].rightop, ranges[-1].rightedge = le, edge

            # equals is a special case, sometimes
            # an extra element may need to sneak in.
            if op is eq:
                if ranges[-1].leftedge == edge:
                    # the previous range also covered just this one slice.
                    ranges.pop()
            
                # equals is expressed as greater-than-equals and less-than-equals.
                ranges.append(Range(ge, edge, le, edge))
            
        if i == len(breaks) - 1:
            # get a left-boundary for the final range
            if op in (lt, ge):
                ranges.append(Range(ge, edge))
            else:
                ranges.append(Range(gt, edge))

    ranges = [range for range in ranges if range.isOpen()]
    
    # print breaks
    # print ranges
    
    if ranges:
        return ranges

    else:
        # if all else fails, return a Range that covers everything
        return [Range()]

def test_combinations(tests, filter=None):
    """ Given a list of simple =/!= tests, return a list of possible combinations.
    
        The filter argument is used to call test_combinations() recursively;
        this cuts down on the potential tests^2 number of combinations by
        identifying closed filters early and culling them from consideration.
    """
    # is the first one simple? it should be
    if len(tests) >= 1:
        assert tests[0].isSimple(), 'All tests must be simple, i.e. = or !='
    
    # does it share a property with the next one? it should
    if len(tests) >= 2:
        assert tests[0].property == tests[1].property, 'All tests must share the same property'

    # -------- remaining tests will be checked in subsequent calls --------
    
    # bail early
    if len(tests) == 0:
        return []

    # base case where no filter has been passed
    if filter is None:
        filter = Filter()

    # knock one off the front
    first_test, remaining_tests = tests[0], tests[1:]
    # one filter with the front test on it
    this_filter = filter.clone()
    this_filter.tests.append(first_test)
    
    # another filter with the inverse of the front test on it
    that_filter = filter.clone()
    that_filter.tests.append(first_test.inverse())
    
    # return value
    test_sets = []
    
    for new_filter in (this_filter, that_filter):
        if new_filter.isOpen():
            if len(remaining_tests) > 0:
                # keep diving deeper
                test_sets += test_combinations(remaining_tests, new_filter)
            
            else:
                # only append once the list has been exhausted
                new_set = []
                
                for test in new_filter.minusExtras().tests:
                    if test not in new_set:
                        new_set.append(test)
    
                test_sets.append(new_set)

    return test_sets

def xindexes(slots):
    """ Generate list of possible indexes into a list of slots.
    
        Best way to think of this is as a number where each digit might have a different radix.
        E.g.: (10, 10, 10) would return 10 x 10 x 10 = 1000 responses from (0, 0, 0) to (9, 9, 9),
        (2, 2, 2, 2) would return 2 x 2 x 2 x 2 = 16 responses from (0, 0, 0, 0) to (1, 1, 1, 1).
    """
    # the first response...
    slot = [0] * len(slots)
    
    for i in range(reduce(operator.mul, slots)):
        yield slot
        
        carry = 1
        
        # iterate from the least to the most significant digit
        for j in range(len(slots), 0, -1):
            k = j - 1
            
            slot[k] += carry
            
            if slot[k] >= slots[k]:
                carry = 1 + slot[k] - slots[k]
                slot[k] = 0
            else:
                carry = 0

def selectors_tests(selectors, property=None):
    """ Given a list of selectors, return a list of unique tests.
    
        Optionally limit to those with a given property.
    """
    tests = {}
    
    for selector in selectors:
        for test in selector.allTests():
            if property is None or test.property == property:
                tests[unicode(test)] = test

    return tests.values()

def tests_filter_combinations(tests):
    """ Return a complete list of filter combinations for given list of tests
    """
    if len(tests) == 0:
        return [Filter()]
    
    # unique properties
    properties = sorted(list(set([test.property for test in tests])))

    property_tests = {}
    
    # divide up the tests by their first argument, e.g. "landuse" vs. "tourism",
    # into lists of all possible legal combinations of those tests.
    for property in properties:
        
        # limit tests to those with the current property
        current_tests = [test for test in tests if test.property == property]
        
        has_ranged_tests = True in [test.isRanged() for test in current_tests]
        has_nonnumeric_tests = False in [test.isNumeric() for test in current_tests]
        
        if has_ranged_tests and has_nonnumeric_tests:
            raise Exception('Mixed ranged/non-numeric tests in %s' % str(current_tests))

        elif has_ranged_tests:
            property_tests[property] = [range.toFilter(property).tests for range in test_ranges(current_tests)]

        else:
            property_tests[property] = test_combinations(current_tests)
            
    # get a list of the number of combinations for each group of tests from above.
    property_counts = [len(property_tests[property]) for property in properties]
    
    filters = []
        
    # now iterate over each combination - for large numbers of tests, this can get big really, really fast
    for property_indexes in xindexes(property_counts):
        # list of lists of tests
        testslist = [property_tests[properties[i]][j] for (i, j) in enumerate(property_indexes)]
        
        # corresponding filter
        filter = Filter(*reduce(operator.add, testslist))
        
        filters.append(filter)

    if len(filters):
        return sorted(filters)

    # if no filters have been defined, return a blank one that matches anything
    return [Filter()]

def is_merc_projection(srs):
    """ Return true if the map projection matches that used by VEarth, Google, OSM, etc.
    
        Is currently necessary for zoom-level shorthand for scale-denominator.
    """
    if srs.lower() == '+init=epsg:900913':
        return True

    # observed
    srs = dict([p.split('=') for p in srs.split() if '=' in p])
    
    # expected
    # note, common optional modifiers like +no_defs, +over, and +wkt
    # are not pairs and should not prevent matching
    gym = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null'
    gym = dict([p.split('=') for p in gym.split() if '=' in p])
        
    for p in gym:
        if srs.get(p, None) != gym.get(p, None):
            return False

    return True

def extract_declarations(map_el, dirs, scale=1, user_styles=[]):
    """ Given a Map element and directories object, remove and return a complete
        list of style declarations from any Stylesheet elements found within.
    """
    styles = []
    
    #
    # First, look at all the stylesheets defined in the map itself.
    #
    for stylesheet in map_el.findall('Stylesheet'):
        map_el.remove(stylesheet)

        content, mss_href = fetch_embedded_or_remote_src(stylesheet, dirs)
        
        if content:
            styles.append((content, mss_href))
    
    #
    # Second, look through the user-supplied styles for override rules.
    #
    for stylesheet in user_styles:
        mss_href = urljoin(dirs.source.rstrip('/')+'/', stylesheet)
        content = urllib.urlopen(mss_href).read().decode(DEFAULT_ENCODING)

        styles.append((content, mss_href))
    
    declarations = []
    
    for (content, mss_href) in styles:
        is_merc = is_merc_projection(map_el.get('srs',''))
        
        for declaration in stylesheet_declarations(content, is_merc, scale):
            #
            # Change the value of each URI relative to the location
            # of the containing stylesheet. We generally just have
            # the one instance of "dirs" around for a full parse cycle,
            # so it's necessary to perform this normalization here
            # instead of later, while mss_href is still available.
            #
            uri_value = declaration.value.value
            
            if uri_value.__class__ is uri:
                uri_value.address = urljoin(mss_href, uri_value.address)

            declarations.append(declaration)

    return declarations

def fetch_embedded_or_remote_src(elem, dirs):
    """
    """
    if 'src' in elem.attrib:
        scheme, host, remote_path, p, q, f = urlparse(dirs.source)
        src_href = urljoin(dirs.source.rstrip('/')+'/', elem.attrib['src'])
        return urllib.urlopen(src_href).read().decode(DEFAULT_ENCODING), src_href

    elif elem.text:
        return elem.text, dirs.source.rstrip('/')+'/'
    
    return None, None

def expand_source_declarations(map_el, dirs, local_conf):
    """ This provides mechanism for externalizing and sharing data sources.  The datasource configs are
    python files, and layers reference sections within that config:
    
    <DataSourcesConfig src="datasources.cfg" />
    <Layer class="road major" source_name="planet_osm_major_roads" />
    <Layer class="road minor" source_name="planet_osm_minor_roads" />
    
    See example_dscfg.mml and example.cfg at the root of the cascadenik directory for an example.
    """

    
    
    ds = sources.DataSources(dirs.source, local_conf)

    # build up the configuration
    for spec in map_el.findall('DataSourcesConfig'):
        map_el.remove(spec)
        src_text, local_base = fetch_embedded_or_remote_src(spec, dirs)
        if not src_text:
            continue

        ds.add_config(src_text, local_base)    
    
    # now transform the xml

    # add in base datasources
    for base_name in ds.templates:
        b = Element("Datasource", name=base_name)
        for pname, pvalue in ds.sources[base_name]['parameters'].items():
            p = Element("Parameter", name=pname)
            p.text = str(pvalue)
            b.append(p)
        map_el.insert(0, b)
    
    # expand layer data sources
    for layer in map_el.findall('Layer'):
        if 'source_name' not in layer.attrib:
            continue
        
        if layer.attrib['source_name'] not in ds.sources:
            raise Exception("Datasource '%s' referenced, but not defined in layer:\n%s" % (layer.attrib['source_name'], ElementTree.tostring(layer)))
                
        # create the nested datasource object 
        b = Element("Datasource")
        dsrc = ds.sources[layer.attrib['source_name']]

        if 'template' in dsrc:
            b.attrib['base'] = dsrc['template']
        
        # set the SRS if present
        if 'layer_srs' in dsrc:
            layer.attrib['srs'] = dsrc['layer_srs']
        
        for pname, pvalue in dsrc['parameters'].items():
            p = Element("Parameter", name=pname)
            p.text = pvalue
            b.append(p)
        
        layer.append(b)
        del layer.attrib['source_name']
        
def test2str(test):
    """ Return a mapnik-happy Filter expression atom for a single test
    """
    if type(test.value) in (int, float):
        value = str(test.value)
    elif type(test.value) in (str, unicode):
        value = "'%s'" % test.value
    else:
        raise Exception("test2str doesn't know what to do with a %s" % type(test.value))
    
    if test.op == '!=':
        return "not [%s] = %s" % (test.property, value)
    elif test.op in ('<', '<=', '=', '>=', '>'):
        return "[%s] %s %s" % (test.property, test.op, value)
    else:
        raise Exception('"%s" is not a valid filter operation' % test.op)

def make_rule(filter, *symbolizers):
    """ Given a Filter and some symbolizers, return a Rule prepopulated
        with applicable min/max scale denominator and filter.
    """
    scale_tests = [test for test in filter.tests if test.isMapScaled()]
    other_tests = [test for test in filter.tests if not test.isMapScaled()]
    
    # these will be replaced with values as necessary
    minscale, maxscale, filter = None, None, None
    
    for scale_test in scale_tests:

        if scale_test.op in ('>', '>='):
            if scale_test.op == '>=':
                value = scale_test.value
            elif scale_test.op == '>':
                value = scale_test.value + 1

            minscale = output.MinScaleDenominator(value)

        if scale_test.op in ('<', '<='):
            if scale_test.op == '<=':
                value = scale_test.value
            elif scale_test.op == '<':
                value = scale_test.value - 1

            maxscale = output.MaxScaleDenominator(value)
    
    filter_text = ' and '.join(test2str(test) for test in other_tests)
    
    if filter_text:
        filter = output.Filter(filter_text)

    rule = output.Rule(minscale, maxscale, filter, [s for s in symbolizers if s])
    
    return rule

def is_applicable_selector(selector, filter):
    """ Given a Selector and Filter, return True if the Selector is
        compatible with the given Filter, and False if they contradict.
    """
    for test in selector.allTests():
        if not test.isCompatible(filter.tests):
            return False
    
    return True

def get_map_attributes(declarations):
    """
    """
    property_map = {'map-bgcolor': 'background'}    
    
    return dict([(property_map[dec.property.name], dec.value.value)
                 for dec in declarations
                 if dec.property.name in property_map])

def filtered_property_declarations(declarations, property_names):
    """
    """
    property_names += ['display']

    # just the ones we care about here
    declarations = [dec for dec in declarations if dec.property.name in property_names]
    selectors = [dec.selector for dec in declarations]

    # a place to put rules
    rules = []
    
    for filter in tests_filter_combinations(selectors_tests(selectors)):
        rule = {}
        
        # collect all the applicable declarations into a list of parameters and values
        for dec in declarations:
            if is_applicable_selector(dec.selector, filter):
                rule[dec.property.name] = dec.value
                
                # Presence of display: none means don't add this rule at all.
                if (dec.property.name, dec.value.value) == ('display', 'none'):
                    rule = {}
                    break

        # Presence of display here probably just means display: map,
        # which is boring and can be discarded.
        if rule and 'display' in rule:
            del rule['display']
        
        # If the rule is empty by this point, skip it.
        if not rule:
            continue

        rules.append((filter, rule))
    
    return rules

def get_polygon_rules(declarations):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a PolygonSymbolizer, add it to Map
        and refer to it in Layer.
    """
    property_map = {'polygon-fill': 'fill', 'polygon-opacity': 'fill-opacity',
                    'polygon-gamma': 'gamma',
                    'polygon-meta-output': 'meta-output', 'polygon-meta-writer': 'meta-writer'}

    property_names = property_map.keys()
    
    # a place to put rules
    rules = []
    
    for (filter, values) in filtered_property_declarations(declarations, property_names):
        color = values.has_key('polygon-fill') and values['polygon-fill'].value
        opacity = values.has_key('polygon-opacity') and values['polygon-opacity'].value or None
        gamma = values.has_key('polygon-gamma') and values['polygon-gamma'].value or None
        symbolizer = color and output.PolygonSymbolizer(color, opacity, gamma)
        
        if symbolizer:
            rules.append(make_rule(filter, symbolizer))
    
    return rules

def get_raster_rules(declarations):
    """ Given a Map element, a Layer element, and a list of declarations,
        create a new Style element with a RasterSymbolizer, add it to Map
        and refer to it in Layer.
        
        The RasterSymbolizer will always created, even if there are
        no applicable declarations.
    """
    property_map = {'raster-opacity': 'opacity',
                    'raster-mode': 'mode',
                    'raster-scaling': 'scaling'
                    }

    property_names = property_map.keys()

    # a place to put rules
    rules = []

    for (filter, values) in filtered_property_declarations(declarations, property_names):
        sym_params = {}
        for prop,attr in property_map.items():
            sym_params[attr] = values.has_key(prop) and values[prop].value or None
        
        symbolizer = output.RasterSymbolizer(**sym_params)

        rules.append(make_rule(filter, symbolizer))

    if not rules:
        # No raster-* rules were created, but we're here so we must need a symbolizer.
        rules.append(make_rule(Filter(), output.RasterSymbolizer()))
    
    return rules

def get_line_rules(declarations):
    """ Given a list of declarations, return a list of output.Rule objects.
        
        This function is wise to line-<foo>, inline-<foo>, and outline-<foo> properties,
        and will generate multiple LineSymbolizers if necessary.
    """
    property_map = {'line-color': 'stroke', 'line-width': 'stroke-width',
                    'line-opacity': 'stroke-opacity', 'line-join': 'stroke-linejoin',
                    'line-cap': 'stroke-linecap', 'line-dasharray': 'stroke-dasharray',
                    'line-meta-output': 'meta-output', 'line-meta-writer': 'meta-writer'}


    property_names = property_map.keys()
    
    # prepend parameter names with 'in' and 'out'
    for i in range(len(property_names)):
        property_names.append('in' + property_names[i])
        property_names.append('out' + property_names[i])

    # a place to put rules
    rules = []
    
    for (filter, values) in filtered_property_declarations(declarations, property_names):
    
        width = values.has_key('line-width') and values['line-width'].value
        color = values.has_key('line-color') and values['line-color'].value

        opacity = values.has_key('line-opacity') and values['line-opacity'].value or None
        join = values.has_key('line-join') and values['line-join'].value or None
        cap = values.has_key('line-cap') and values['line-cap'].value or None
        dashes = values.has_key('line-dasharray') and values['line-dasharray'].value or None

        line_symbolizer = color and width and output.LineSymbolizer(color, width, opacity, join, cap, dashes) or False

        width = values.has_key('inline-width') and values['inline-width'].value
        color = values.has_key('inline-color') and values['inline-color'].value

        opacity = values.has_key('inline-opacity') and values['inline-opacity'].value or None
        join = values.has_key('inline-join') and values['inline-join'].value or None
        cap = values.has_key('inline-cap') and values['inline-cap'].value or None
        dashes = values.has_key('inline-dasharray') and values['inline-dasharray'].value or None

        inline_symbolizer = color and width and output.LineSymbolizer(color, width, opacity, join, cap, dashes) or False

        # outline requires regular line to have a meaningful width
        width = values.has_key('outline-width') and values.has_key('line-width') \
            and values['line-width'].value + values['outline-width'].value * 2
        color = values.has_key('outline-color') and values['outline-color'].value

        opacity = values.has_key('outline-opacity') and values['outline-opacity'].value or None
        join = values.has_key('outline-join') and values['outline-join'].value or None
        cap = values.has_key('outline-cap') and values['outline-cap'].value or None
        dashes = values.has_key('outline-dasharray') and values['outline-dasharray'].value or None

        outline_symbolizer = color and width and output.LineSymbolizer(color, width, opacity, join, cap, dashes) or False
        
        if outline_symbolizer or line_symbolizer or inline_symbolizer:
            rules.append(make_rule(filter, outline_symbolizer, line_symbolizer, inline_symbolizer))

    return rules

def get_text_rule_groups(declarations):
    """ Given a list of declarations, return a list of output.Rule objects.
    """
    property_map = {'text-anchor-dx': 'anchor_dx', # does nothing
                    'text-anchor-dy': 'anchor_dy', # does nothing
                    'text-align': 'horizontal_alignment',
                    'text-allow-overlap': 'allow_overlap',
                    'text-avoid-edges': 'avoid_edges',
                    'text-character-spacing': 'character_spacing',
                    'text-dx': 'dx',
                    'text-dy': 'dy',
                    'text-face-name': 'face_name',
                    'text-fill': 'fill',
                    'text-fontset': 'fontset',
                    'text-halo-fill': 'halo_fill',
                    'text-halo-radius': 'halo_radius',
                    'text-justify-align': 'justify_alignment',
                    'text-label-position-tolerance': 'label_position_tolerance',
                    'text-line-spacing': 'line_spacing',
                    'text-max-char-angle-delta': 'max_char_angle_delta',
                    'text-min-distance': 'minimum_distance',
                    'text-placement': 'label_placement',
                    'text-ratio': 'text_ratio',
                    'text-size': 'size', 
                    'text-spacing': 'spacing',
                    'text-transform': 'text_convert',
                    'text-vertical-align': 'vertical_alignment',
                    'text-wrap-width': 'wrap_width',
                    'text-meta-output': 'meta-output',
                    'text-meta-writer': 'meta-writer'
                    }

    property_names = property_map.keys()
    
    # pull out all the names
    text_names = [dec.selector.elements[1].names[0]
                  for dec in declarations
                  if len(dec.selector.elements) is 2 and len(dec.selector.elements[1].names) is 1]
    
    # a place to put groups
    groups = []
    
    # a separate style element for each text name
    for text_name in set(text_names):
    
        # just the ones we care about here.
        # the complicated conditional means: get all declarations that
        # apply to this text_name specifically, or text in general.
        name_declarations = [dec for dec in declarations
                             if dec.property.name in property_map
                                and (len(dec.selector.elements) == 1
                                     or (len(dec.selector.elements) == 2
                                         and dec.selector.elements[1].names[0] in (text_name, '*')))]
        
        # a place to put rules
        rules = []
        
        for (filter, values) in filtered_property_declarations(name_declarations, property_names):
            
            face_name = values.has_key('text-face-name') and values['text-face-name'].value or None
            fontset = values.has_key('text-fontset') and values['text-fontset'].value or None
            size = values.has_key('text-size') and values['text-size'].value
            color = values.has_key('text-fill') and values['text-fill'].value
            
            ratio = values.has_key('text-ratio') and values['text-ratio'].value or None
            wrap_width = values.has_key('text-wrap-width') and values['text-wrap-width'].value or None
            label_spacing = values.has_key('text-spacing') and values['text-spacing'].value or None
            label_position_tolerance = values.has_key('text-label-position-tolerance') and values['text-label-position-tolerance'].value or None
            max_char_angle_delta = values.has_key('text-max-char-angle-delta') and values['text-max-char-angle-delta'].value or None
            halo_color = values.has_key('text-halo-fill') and values['text-halo-fill'].value or None
            halo_radius = values.has_key('text-halo-radius') and values['text-halo-radius'].value or None
            dx = values.has_key('text-dx') and values['text-dx'].value or None
            dy = values.has_key('text-dy') and values['text-dy'].value or None
            avoid_edges = values.has_key('text-avoid-edges') and values['text-avoid-edges'].value or None
            minimum_distance = values.has_key('text-min-distance') and values['text-min-distance'].value or None
            allow_overlap = values.has_key('text-allow-overlap') and values['text-allow-overlap'].value or None
            label_placement = values.has_key('text-placement') and values['text-placement'].value or None
            text_transform = values.has_key('text-transform') and values['text-transform'].value or None
            anchor_dx = values.has_key('text-anchor-dx') and values['text-anchor-dx'].value or None
            anchor_dy = values.has_key('text-anchor-dy') and values['text-anchor-dy'].value or None
            horizontal_alignment = values.has_key('text-horizontal-align') and values['text-horizontal-align'].value or None
            vertical_alignment = values.has_key('text-vertical-align') and values['text-vertical-align'].value or None
            justify_alignment = values.has_key('text-justify-align') and values['text-justify-align'].value or None
            line_spacing = values.has_key('text-line-spacing') and values['text-line-spacing'].value or None
            character_spacing = values.has_key('text-character-spacing') and values['text-character-spacing'].value or None
            
            if (face_name or fontset) and size and color:
                symbolizer = output.TextSymbolizer(text_name, face_name, size, color, \
                                              wrap_width, label_spacing, label_position_tolerance, \
                                              max_char_angle_delta, halo_color, halo_radius, dx, dy, \
                                              avoid_edges, minimum_distance, allow_overlap, label_placement, \
                                              line_spacing, character_spacing, text_transform, fontset,
                                              anchor_dx, anchor_dy,horizontal_alignment, \
                                              vertical_alignment, justify_alignment)
            
                rules.append(make_rule(filter, symbolizer))
        
        groups.append((text_name, rules))
    
    return dict(groups)

def locally_cache_remote_file(href, dir):
    """ Locally cache a remote resource using a predictable file name
        and awareness of modification date. Assume that files are "normal"
        which is to say they have filenames with extensions.
    """
    scheme, host, remote_path, params, query, fragment = urlparse(href)
    
    assert scheme in ('http','https'), 'Scheme must be either http or https, not "%s" (for %s)' % (scheme,href)

    head, ext = posixpath.splitext(posixpath.basename(remote_path))
    head = sub(r'[^\w\-_]', '', head)
    hash = md5(href).hexdigest()[:8]
    
    local_path = '%(dir)s/%(host)s-%(hash)s-%(head)s%(ext)s' % locals()

    headers = {}
    if posixpath.exists(local_path):
        msg('Found local file: %s' % local_path )
        t = localtime(os.stat(local_path).st_mtime)
        headers['If-Modified-Since'] = strftime('%a, %d %b %Y %H:%M:%S %Z', t)
    
    if scheme == 'https':
        conn = HTTPSConnection(host, timeout=5)
    else:
        conn = HTTPConnection(host, timeout=5)

    if query:
        remote_path += '?%s' % query

    conn.request('GET', remote_path, headers=headers)
    resp = conn.getresponse()
        
    if resp.status in range(200, 210):
        # hurrah, it worked
        f = open(un_posix(local_path), 'wb')
        msg('Reading from remote: %s' % remote_path)
        f.write(resp.read())
        f.close()

    elif resp.status in (301, 302, 303) and resp.getheader('location', False):
        # follow a redirect, totally untested.
        redirected_href = urljoin(href, resp.getheader('location'))
        redirected_path = locally_cache_remote_file(redirected_href, dir)
        os.rename(redirected_path, local_path)
    
    elif resp.status == 304:
        # hurrah, it's cached
        msg('Reading directly from local cache')
        pass

    else:
        raise Exception("Failed to get remote resource %s: %s" % (href, resp.status))
    
    return local_path

def post_process_symbolizer_image_file(file_href, dirs):
    """ Given an image file href and a set of directories, modify the image file
        name so it's correct with respect to the output and cache directories.
    """
    # support latest mapnik features of auto-detection
    # of image sizes and jpeg reading support...
    # http://trac.mapnik.org/ticket/508

    mapnik_auto_image_support = (MAPNIK_VERSION >= 701)
    mapnik_requires_absolute_paths = (MAPNIK_VERSION < 601)
    file_href = urljoin(dirs.source.rstrip('/')+'/', file_href)
    scheme, n, path, p, q, f = urlparse(file_href)
    if scheme in ('http','https'):
        scheme, path = '', locally_cache_remote_file(file_href, dirs.cache)
    
    if scheme not in ('file', '') or not systempath.exists(un_posix(path)):
        raise Exception("Image file needs to be a working, fetchable resource, not %s" % file_href)
        
    if not mapnik_auto_image_support and not Image:
        raise SystemExit('PIL (Python Imaging Library) is required for handling image data unless you are using PNG inputs and running Mapnik >=0.7.0')

    img = Image.open(un_posix(path))
    
    if mapnik_requires_absolute_paths:
        path = posixpath.realpath(path)
    
    else:
        path = dirs.output_path(path)

    msg('reading symbol: %s' % path)

    image_name, ext = posixpath.splitext(path)
    
    if ext in ('.png', '.tif', '.tiff'):
        output_ext = ext
    else:
        output_ext = '.png'
    
    # new local file name
    dest_file = un_posix('%s%s' % (image_name, output_ext))
    
    if not posixpath.exists(dest_file):
        img.save(dest_file,'PNG')

    msg('Destination file: %s' % dest_file)

    return dest_file, output_ext[1:], img.size[0], img.size[1]

def get_shield_rule_groups(declarations, dirs):
    """ Given a list of declarations, return a list of output.Rule objects.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'shield-face-name': 'face_name',
                    'shield-fontset': 'fontset',
                    'shield-size': 'size', 
                    'shield-fill': 'fill', 'shield-character-spacing': 'character_spacing',
                    'shield-line-spacing': 'line_spacing',
                    'shield-spacing': 'spacing', 'shield-min-distance': 'minimum_distance',
                    'shield-file': 'file', 'shield-width': 'width', 'shield-height': 'height',
                    'shield-meta-output': 'meta-output', 'shield-meta-writer': 'meta-writer',
                    'shield-text-dx': 'dx', 'shield-text-dy': 'dy'}

    property_names = property_map.keys()
    
    # pull out all the names
    text_names = [dec.selector.elements[1].names[0]
                  for dec in declarations
                  if len(dec.selector.elements) is 2 and len(dec.selector.elements[1].names) is 1]
    
    # a place to put groups
    groups = []
    
    # a separate style element for each text name
    for text_name in set(text_names):
    
        # just the ones we care about here.
        # the complicated conditional means: get all declarations that
        # apply to this text_name specifically, or text in general.
        name_declarations = [dec for dec in declarations
                             if dec.property.name in property_map
                                and (len(dec.selector.elements) == 1
                                     or (len(dec.selector.elements) == 2
                                         and dec.selector.elements[1].names[0] in (text_name, '*')))]
        
        # a place to put rules
        rules = []
        
        for (filter, values) in filtered_property_declarations(name_declarations, property_names):
        
            face_name = values.has_key('shield-face-name') and values['shield-face-name'].value or None
            fontset = values.has_key('shield-fontset') and values['shield-fontset'].value or None
            size = values.has_key('shield-size') and values['shield-size'].value or None
            
            file, filetype, width, height \
                = values.has_key('shield-file') \
                and post_process_symbolizer_image_file(str(values['shield-file'].value), dirs) \
                or (None, None, None, None)
            
            width = values.has_key('shield-width') and values['shield-width'].value or width
            height = values.has_key('shield-height') and values['shield-height'].value or height
            
            color = values.has_key('shield-fill') and values['shield-fill'].value or None
            minimum_distance = values.has_key('shield-min-distance') and values['shield-min-distance'].value or None
            
            character_spacing = values.has_key('shield-character-spacing') and values['shield-character-spacing'].value or None
            line_spacing = values.has_key('shield-line-spacing') and values['shield-line-spacing'].value or None
            label_spacing = values.has_key('shield-spacing') and values['shield-spacing'].value or None
            
            text_dx = values.has_key('shield-text-dx') and values['shield-text-dx'].value or 0
            text_dy = values.has_key('shield-text-dy') and values['shield-text-dy'].value or 0
            
            if file and (face_name or fontset):
                symbolizer = output.ShieldSymbolizer(text_name, face_name, size, file, filetype, 
                                            width, height, color, minimum_distance, character_spacing,
                                            line_spacing, label_spacing, text_dx=text_dx, text_dy=text_dy,
                                            fontset=fontset)
            
                rules.append(make_rule(filter, symbolizer))
        
        groups.append((text_name, rules))
    
    return dict(groups)

def get_point_rules(declarations, dirs):
    """ Given a list of declarations, return a list of output.Rule objects.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'point-file': 'file', 'point-width': 'width',
                    'point-height': 'height', 'point-type': 'type',
                    'point-allow-overlap': 'allow_overlap',
                    'point-meta-output': 'meta-output', 'point-meta-writer': 'meta-writer'}
    
    property_names = property_map.keys()
    
    # a place to put rules
    rules = []
    
    for (filter, values) in filtered_property_declarations(declarations, property_names):
        point_file, point_type, point_width, point_height \
            = values.has_key('point-file') \
            and post_process_symbolizer_image_file(str(values['point-file'].value), dirs) \
            or (None, None, None, None)
        
        point_width = values.has_key('point-width') and values['point-width'].value or point_width
        point_height = values.has_key('point-height') and values['point-height'].value or point_height
        point_allow_overlap = values.has_key('point-allow-overlap') and values['point-allow-overlap'].value or None
        
        symbolizer = point_file and output.PointSymbolizer(point_file, point_type, point_width, point_height, point_allow_overlap)

        if symbolizer:
            rules.append(make_rule(filter, symbolizer))
    
    return rules

def get_polygon_pattern_rules(declarations, dirs):
    """ Given a list of declarations, return a list of output.Rule objects.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'polygon-pattern-file': 'file', 'polygon-pattern-width': 'width',
                    'polygon-pattern-height': 'height', 'polygon-pattern-type': 'type',
                    'polygon-meta-output': 'meta-output', 'polygon-meta-writer': 'meta-writer'}

    
    property_names = property_map.keys()
    
    # a place to put rules
    rules = []
    
    for (filter, values) in filtered_property_declarations(declarations, property_names):
    
        poly_pattern_file, poly_pattern_type, poly_pattern_width, poly_pattern_height \
            = values.has_key('polygon-pattern-file') \
            and post_process_symbolizer_image_file(str(values['polygon-pattern-file'].value), dirs) \
            or (None, None, None, None)
        
        poly_pattern_width = values.has_key('polygon-pattern-width') and values['polygon-pattern-width'].value or poly_pattern_width
        poly_pattern_height = values.has_key('polygon-pattern-height') and values['polygon-pattern-height'].value or poly_pattern_height
        symbolizer = poly_pattern_file and output.PolygonPatternSymbolizer(poly_pattern_file, poly_pattern_type, poly_pattern_width, poly_pattern_height)
        
        if symbolizer:
            rules.append(make_rule(filter, symbolizer))
    
    return rules

def get_line_pattern_rules(declarations, dirs):
    """ Given a list of declarations, return a list of output.Rule objects.
        
        Optionally provide an output directory for local copies of image files.
    """
    property_map = {'line-pattern-file': 'file', 'line-pattern-width': 'width',
                    'line-pattern-height': 'height', 'line-pattern-type': 'type',
                    'line-pattern-meta-output': 'meta-output', 'line-pattern-meta-writer': 'meta-writer'}

    
    property_names = property_map.keys()
    
    # a place to put rules
    rules = []
    
    for (filter, values) in filtered_property_declarations(declarations, property_names):
    
        line_pattern_file, line_pattern_type, line_pattern_width, line_pattern_height \
            = values.has_key('line-pattern-file') \
            and post_process_symbolizer_image_file(str(values['line-pattern-file'].value), dirs) \
            or (None, None, None, None)
        
        line_pattern_width = values.has_key('line-pattern-width') and values['line-pattern-width'].value or line_pattern_width
        line_pattern_height = values.has_key('line-pattern-height') and values['line-pattern-height'].value or line_pattern_height
        symbolizer = line_pattern_file and output.LinePatternSymbolizer(line_pattern_file, line_pattern_type, line_pattern_width, line_pattern_height)
        
        if symbolizer:
            rules.append(make_rule(filter, symbolizer))
    
    return rules

def get_applicable_declarations(element, declarations):
    """ Given an XML element and a list of declarations, return the ones
        that match as a list of (property, value, selector) tuples.
    """
    element_tag = element.tag
    element_id = element.get('id', None)
    element_classes = element.get('class', '').split()

    return [dec for dec in declarations
            if dec.selector.matches(element_tag, element_id, element_classes)]

def unzip_shapefile_into(zip_path, dir, host=None):
    """
    """
    hash = md5(zip_path).hexdigest()[:8]
    zip_file = zipfile.ZipFile(un_posix(zip_path))
    zip_ctime = os.stat(un_posix(zip_path)).st_ctime
    
    infos = zip_file.infolist()
    extensions = [posixpath.splitext(info.filename)[1] for info in infos]
    
    host_prefix = host and ('%(host)s-' % locals()) or ''
    shape_parts = ('.shp', True), ('.shx', True), ('.dbf', True), ('.prj', False), ('.index', False)
    
    for (expected, required) in shape_parts:
        if required and expected not in extensions:
            raise Exception('Zip file %(zip_path)s missing extension "%(expected)s"' % locals())

        for info in infos:
            head, ext = posixpath.splitext(posixpath.basename(info.filename))
            head = sub(r'[^\w\-_]', '', head)

            if ext == expected:
                file_data = zip_file.read(info.filename)
                file_name = '%(dir)s/%(host_prefix)s%(hash)s-%(head)s%(ext)s' % locals()
                
                if not systempath.exists(un_posix(file_name)) or os.stat(un_posix(file_name)).st_ctime < zip_ctime:
                    file_ = open(un_posix(file_name), 'wb')
                    file_.write(file_data)
                    file_.close()
                
                if ext == '.shp':
                    local = file_name[:-4]
                
                break

    return local

def localize_shapefile(shp_href, dirs):
    """ Given a shapefile href and a set of directories, modify the shapefile
        name so it's correct with respect to the output and cache directories.
    """
    # support latest mapnik features of auto-detection
    # of image sizes and jpeg reading support...
    # http://trac.mapnik.org/ticket/508

    mapnik_requires_absolute_paths = (MAPNIK_VERSION < 601)

    shp_href = urljoin(dirs.source.rstrip('/')+'/', shp_href)
    scheme, host, path, p, q, f = urlparse(shp_href)
    
    if scheme in ('http','https'):
        msg('%s | %s' % (shp_href, dirs.cache))
        scheme, path = '', locally_cache_remote_file(shp_href, dirs.cache)
    else:
        host = None
    
    # collect drive for windows
    to_posix(systempath.realpath(path))

    if scheme not in ('file', ''):
        raise Exception("Shapefile needs to be local, not %s" % shp_href)
        
    if mapnik_requires_absolute_paths:
        path = posixpath.realpath(path)
        original = path

    path = dirs.output_path(path)
    
    if path.endswith('.zip'):
        # unzip_shapefile_into needs a path it can find
        path = posixpath.join(dirs.output, path)
        path = unzip_shapefile_into(path, dirs.cache, host)

    return dirs.output_path(path)

def localize_file_datasource(file_href, dirs):
    """ Handle localizing file-based datasources other than shapefiles.
    
        This will only work for single-file based types.
    """
    # support latest mapnik features of auto-detection
    # of image sizes and jpeg reading support...
    # http://trac.mapnik.org/ticket/508

    mapnik_requires_absolute_paths = (MAPNIK_VERSION < 601)

    file_href = urljoin(dirs.source.rstrip('/')+'/', file_href)
    scheme, n, path, p, q, f = urlparse(file_href)
    
    if scheme in ('http','https'):
        scheme, path = '', locally_cache_remote_file(file_href, dirs.cache)

    if scheme not in ('file', ''):
        raise Exception("Datasource file needs to be a working, fetchable resource, not %s" % file_href)

    if mapnik_requires_absolute_paths:
        return posixpath.realpath(path)
    
    else:
        return dirs.output_path(path)
    
def compile(src, dirs, verbose=False, srs=None, datasources_cfg=None, user_styles=[], scale=1):
    """ Compile a Cascadenik MML file, returning a cascadenik.output.Map object.
    
        Parameters:
        
          src:
            Path to .mml file, or raw .mml file content.
          
          dirs:
            Object with directory names in 'cache', 'output', and 'source' attributes.
            dirs.source is expected to be fully-qualified, e.g. "http://example.com"
            or "file:///home/example".
        
        Keyword Parameters:
        
          verbose:
            If True, debugging information will be printed to stderr.
        
          srs:
            Target spatial reference system for the compiled stylesheet.
            If provided, overrides default map srs in the .mml file.
        
          datasources_cfg:
            If a file or URL, uses the config to override datasources or parameters
            (i.e. postgis_dbname) defined in the map's canonical <DataSourcesConfig>
            entities.  This is most useful in development, whereby one redefines
            individual datasources, connection parameters, and/or local paths.
        
          user_styles:
            A optional list of files or URLs, that override styles defined in
            the map source. These are evaluated in order, with declarations from
            later styles overriding those from earlier styles.
        
          scale:
            Scale value for output map, 2 doubles the size for high-res displays.
    """
    global VERBOSE

    if verbose:
        VERBOSE = True
        sys.stderr.write('\n')
    
    msg('Targeting mapnik version: %s | %s' % (MAPNIK_VERSION, MAPNIK_VERSION_STR))
        
    if posixpath.exists(src):
        doc = ElementTree.parse(src)
        map_el = doc.getroot()
    else:
        try:
            # guessing src is a literal XML string?
            map_el = ElementTree.fromstring(src)
    
        except:
            if not (src[:7] in ('http://', 'https:/', 'file://')):
                src = "file://" + src
            try:
                doc = ElementTree.parse(urllib.urlopen(src))
            except IOError, e:
                raise IOError('%s: %s' % (e,src))
            map_el = doc.getroot()

    expand_source_declarations(map_el, dirs, datasources_cfg)
    declarations = extract_declarations(map_el, dirs, scale, user_styles)
    
    # a list of layers and a sequential ID generator
    layers, ids = [], (i for i in xrange(1, 999999))


    # Handle base datasources
    # http://trac.mapnik.org/changeset/574
    datasource_templates = {}
    for base_el in map_el:
        if base_el.tag != 'Datasource':
            continue
        datasource_templates[base_el.get('name')] = dict(((p.get('name'),p.text) for p in base_el.findall('Parameter')))
    
    for layer_el in map_el.findall('Layer'):
    
        # nevermind with this one
        if layer_el.get('status', None) in ('off', '0', 0):
            continue

        # build up a map of Parameters for this Layer
        datasource_params = dict((p.get('name'),p.text) for p in layer_el.find('Datasource').findall('Parameter'))

        base = layer_el.find('Datasource').get('base')
        if base:
            datasource_params.update(datasource_templates[base])

        if datasource_params.get('table'):
            # remove line breaks from possible SQL, using a possibly-unsafe regexp
            # that simply blows away anything that looks like it might be a SQL comment.
            # http://trac.mapnik.org/ticket/173
            if not MAPNIK_VERSION >= 601:
                sql = datasource_params.get('table')
                sql = compile(r'--.*$', MULTILINE).sub('', sql)
                sql = sql.replace('\r', ' ').replace('\n', ' ')
                datasource_params['table'] = sql

        elif datasource_params.get('file') is not None:
            # make sure we localize any remote files
            file_param = datasource_params.get('file')

            if datasource_params.get('type') == 'shape':
                # handle a local shapefile or fetch a remote, zipped shapefile
                msg('Handling shapefile datasource...')
                file_param = localize_shapefile(file_param, dirs)

                # TODO - support datasource reprojection to make map srs
                # TODO - support automatically indexing shapefiles

            else: # ogr,raster, gdal, sqlite
                # attempt to generically handle other file based datasources
                msg('Handling generic datasource...')
                file_param = localize_file_datasource(file_param, dirs)

            msg("Localized path = %s" % un_posix(file_param))
            datasource_params['file'] = un_posix(file_param)

            # TODO - consider custom support for other mapnik datasources:
            # sqlite, oracle, osm, kismet, gdal, raster, rasterlite

        layer_declarations = get_applicable_declarations(layer_el, declarations)
        
        # a list of styles
        styles = []
        
        if datasource_params.get('type', None) == 'gdal':
            styles.append(output.Style('raster style %d' % ids.next(),
                                       get_raster_rules(layer_declarations)))
    
        else:
            styles.append(output.Style('polygon style %d' % ids.next(),
                                       get_polygon_rules(layer_declarations)))
    
            styles.append(output.Style('polygon pattern style %d' % ids.next(),
                                       get_polygon_pattern_rules(layer_declarations, dirs)))
    
            styles.append(output.Style('line style %d' % ids.next(),
                                       get_line_rules(layer_declarations)))
    
            styles.append(output.Style('line pattern style %d' % ids.next(),
                                       get_line_pattern_rules(layer_declarations, dirs)))
    
            for (shield_name, shield_rules) in get_shield_rule_groups(layer_declarations, dirs).items():
                styles.append(output.Style('shield style %d (%s)' % (ids.next(), shield_name), shield_rules))
    
            for (text_name, text_rules) in get_text_rule_groups(layer_declarations).items():
                styles.append(output.Style('text style %d (%s)' % (ids.next(), text_name), text_rules))
    
            styles.append(output.Style('point style %d' % ids.next(),
                                       get_point_rules(layer_declarations, dirs)))
                                   
        styles = [s for s in styles if s.rules]
        
        if styles:
            datasource = output.Datasource(**datasource_params)
            
            layer = output.Layer('layer %d' % ids.next(),
                                 datasource, styles,
                                 layer_el.get('srs', None),
                                 layer_el.get('min_zoom', None) and int(layer_el.get('min_zoom')) or None,
                                 layer_el.get('max_zoom', None) and int(layer_el.get('max_zoom')) or None)
    
            layers.append(layer)
    
    map_attrs = get_map_attributes(get_applicable_declarations(map_el, declarations))
    
    # if a target srs is profiled, override whatever is in mml
    if srs is not None:
        map_el.set('srs', srs)
    
    return output.Map(map_el.attrib.get('srs', None), layers, **map_attrs)

########NEW FILE########
__FILENAME__ = nonposix
import os
import os.path as systempath
import posixpath
from hashlib import md5

drives = {}

# sketchy windows only mucking to handle translating between
# native cascadenik storage of posix paths and the filesystem.
# to_posix() and un_posix() are called in cascadenik/compile.py
# but only impact non-posix systems (windows)

def get_posix_root(valid_posix_path):
    if posixpath.isdir(valid_posix_path) and not valid_posix_path.endswith(posixpath.sep):
        valid_posix_path += posixpath.sep
    else:
        valid_posix_path = posixpath.dirname(valid_posix_path)
    return valid_posix_path.split(posixpath.sep)[1] or valid_posix_path

def add_drive(drive,valid_posix_path):
    root = get_posix_root(valid_posix_path)
    if not drives.get(root):
        drives[root] = drive
        #print 'pushing drive: %s | %s | %s' % (drive,root, valid_posix_path)

def get_drive(valid_posix_path):
    return drives.get(get_posix_root(valid_posix_path))

# not currently used
def add_drive_by_hash(drive,valid_posix_path):
    # cache the drive so we can try to recreate later
    global drives
    hash = md5(valid_posix_path).hexdigest()[:8]
    drives[hash] = drive
    #print 'pushing drive: %s | %s | %s' % (drive,valid_posix_path,hash)

# not currently used
def get_drive_by_hash(valid_posix_path):
    # todo - make this smarter
    hash = md5(valid_posix_path).hexdigest()[:8]
    drive = drives.get(hash)
    if not drive:
        hash = md5(posixpath.dirname(valid_posix_path)).hexdigest()[:8]
        drive = drives.get(hash)

def to_posix(path_name):
    
    if os.name == "posix":
        return path_name
    
    else:
        drive, path = systempath.splitdrive(path_name)
        valid_posix_path = path.replace(os.sep,posixpath.sep)
        if drive:
            #add_drive_by_hash(drive,valid_posix_path)
            add_drive(drive,valid_posix_path)
        return valid_posix_path

def un_posix(valid_posix_path,drive=None):
    
    if os.name == "posix":
        return valid_posix_path
    
    else:
        global drives
        if not posixpath.isabs(valid_posix_path):
            return valid_posix_path# what to do? for now assert
        assert posixpath.isabs(valid_posix_path), "un_posix() needs an absolute posix style path, not %s" % valid_posix_path
        #drive = get_drive_by_hash(valid_posix_path)
        drive = get_drive(valid_posix_path)
        
        assert drive, "We cannot make this path (%s) local to the platform without knowing the drive" % valid_posix_path
        path = systempath.join(drive,systempath.normpath(valid_posix_path))
        return path
########NEW FILE########
__FILENAME__ = output
import sys
from re import sub
from itertools import count
from os import getcwd, chdir

from . import style, mapnik, MAPNIK_VERSION

def safe_str(s):
    return None if not s else unicode(s).encode('utf-8')

def fontset_name(face_names):
    return '-'.join([sub(r'\W', '_', name) for name in face_names])

class OutputException(Exception):
    """ Exception raised when an output error is encountered.
    """
    pass

class Map:
    def __init__(self, srs=None, layers=None, background=None):
        assert srs is None or isinstance(srs, basestring)
        assert layers is None or type(layers) in (list, tuple)
        assert background is None or background.__class__ is style.color or background == 'transparent'
        
        self.srs = safe_str(srs)
        self.layers = layers or []
        self.background = background

    def __repr__(self):
        return 'Map(%s %s)' % (self.background, repr(self.layers))

    def to_mapnik(self, mmap, dirs=None):
        """
        """
        prev_cwd = getcwd()
        
        if dirs:
            chdir(dirs.output)
        
        try:
            mmap.srs = self.srs or mmap.srs
            if self.background:
                mmap.background = mapnik.Color(str(self.background))
            
            ids = count(1)
            fontsets = dict()
            
            for layer in self.layers:
                for style in layer.styles:
    
                    sty = mapnik.Style()
                    
                    if MAPNIK_VERSION >= 200000:
                        sty.filter_mode = mapnik.filter_mode.FIRST
                    
                    for rule in style.rules:
                        rul = mapnik.Rule('rule %d' % ids.next())
                        rul.filter = rule.filter and mapnik.Filter(rule.filter.text) or rul.filter
                        rul.min_scale = rule.minscale and rule.minscale.value or rul.min_scale
                        rul.max_scale = rule.maxscale and rule.maxscale.value or rul.max_scale
                        
                        for symbolizer in rule.symbolizers:
                            if not hasattr(symbolizer, 'to_mapnik'):
                                continue
    
                            if hasattr(symbolizer, 'get_fontset_name'):
                                fontset_name = symbolizer.get_fontset_name()
                            
                                if fontset_name and fontset_name not in fontsets:
                                    fontset = FontSet(symbolizer.face_name.values).to_mapnik()
                                    mmap.append_fontset(fontset_name, fontset)
                                    fontsets[fontset_name] = mmap.find_fontset(fontset_name)

                                sym = symbolizer.to_mapnik(fontsets)
                            
                            else:
                                sym = symbolizer.to_mapnik()
                            
                            rul.symbols.append(sym)
                        sty.rules.append(rul)
                    mmap.append_style(style.name, sty)
    
                lay = mapnik.Layer(layer.name)
                lay.srs = layer.srs or lay.srs
                if layer.datasource:
                    lay.datasource = layer.datasource.to_mapnik()
                lay.minzoom = layer.minzoom or lay.minzoom
                lay.maxzoom = layer.maxzoom or lay.maxzoom
                
                for style in layer.styles:
                    lay.styles.append(style.name)
    
                mmap.layers.append(lay)
        
        except:
            # pass it along, but first chdir back to the previous directory
            # in the finally clause below, to put things back the way they were.
            raise
        
        finally:
            chdir(prev_cwd)

class Style:
    def __init__(self, name, rules):
        assert name is None or type(name) is str
        assert rules is None or type(rules) in (list, tuple)
        
        self.name = name
        self.rules = rules or []

    def __repr__(self):
        return 'Style(%s: %s)' % (self.name, repr(self.rules))

class Rule:
    def __init__(self, minscale, maxscale, filter, symbolizers):
        assert minscale is None or minscale.__class__ is MinScaleDenominator
        assert maxscale is None or maxscale.__class__ is MaxScaleDenominator
        assert filter is None or filter.__class__ is Filter

        self.minscale = minscale
        self.maxscale = maxscale
        self.filter = filter
        self.symbolizers = symbolizers

    def __repr__(self):
        return 'Rule(%s:%s, %s, %s)' % (repr(self.minscale), repr(self.maxscale), repr(self.filter), repr(self.symbolizers))

class Layer:
    def __init__(self, name, datasource, styles=None, srs=None, minzoom=None, maxzoom=None):
        assert isinstance(name, basestring)
        assert styles is None or type(styles) in (list, tuple)
        assert srs is None or isinstance(srs, basestring)
        assert minzoom is None or type(minzoom) in (int, float)
        assert maxzoom is None or type(maxzoom) in (int, float)
        
        self.name = safe_str(name)
        self.datasource = datasource
        self.styles = styles or []
        self.srs = safe_str(srs)
        self.minzoom = minzoom
        self.maxzoom = maxzoom

    def __repr__(self):
        return 'Layer(%s: %s)' % (self.name, repr(self.styles))

class Datasource:
    def __init__(self, **parameters):
        self.parameters = {}
        for param, value in parameters.items():
            if isinstance(value, basestring):
                value = safe_str(value)
            self.parameters[param] = value

    def to_mapnik(self):
        return mapnik.Datasource(**self.parameters)

class MinScaleDenominator:
    def __init__(self, value):
        assert type(value) is int
        self.value = value

    def __repr__(self):
        return str(self.value)

class MaxScaleDenominator:
    def __init__(self, value):
        assert type(value) is int
        self.value = value

    def __repr__(self):
        return str(self.value)

class Filter:
    def __init__(self, text):
        self.text = text.encode('utf8')
    
    def __repr__(self):
        return str(self.text)

class PolygonSymbolizer:
    def __init__(self, color, opacity=None, gamma=None):
        assert color.__class__ is style.color
        assert opacity is None or type(opacity) in (int, float)
        assert gamma is None or type(gamma) in (int, float)

        self.color = color
        self.opacity = opacity or 1.0
        self.gamma = gamma

    def __repr__(self):
        return 'Polygon(%s, %s, %s)' % (self.color, self.opacity, self.gamma)

    def to_mapnik(self):
        sym = mapnik.PolygonSymbolizer(mapnik.Color(str(self.color)))
        sym.fill_opacity = self.opacity
        sym.gamma = self.gamma or sym.gamma
        
        return sym

class RasterSymbolizer:
    def __init__(self, mode=None, opacity=None, scaling=None):
        assert opacity is None or type(opacity) in (int, float)
        assert mode is None or isinstance(mode, basestring)
        assert scaling is None or isinstance(scaling, basestring)

        self.mode = safe_str(mode)
        self.opacity = opacity or 1.0
        self.scaling = safe_str(scaling)

    def __repr__(self):
        return 'Raster(%s, %s, %s)' % (self.mode, self.opacity, self.scaling)

    def to_mapnik(self):
        sym = mapnik.RasterSymbolizer()
        sym.opacity = self.opacity
        sym.mode = self.mode or sym.mode
        sym.scaling = self.scaling or sym.scaling

        return sym

class LineSymbolizer:
    def __init__(self, color, width, opacity=None, join=None, cap=None, dashes=None):
        assert color.__class__ is style.color
        assert type(width) in (int, float)
        assert opacity is None or type(opacity) in (int, float)
        assert join is None or isinstance(join, basestring)
        assert cap is None or isinstance(cap, basestring)
        assert dashes is None or dashes.__class__ is style.numbers

        self.color = color
        self.width = width
        self.opacity = opacity
        self.join = safe_str(join)
        self.cap = safe_str(cap)
        self.dashes = dashes

    def __repr__(self):
        return 'Line(%s, %s)' % (self.color, self.width)

    def to_mapnik(self):
        line_caps = {'butt': mapnik.line_cap.BUTT_CAP,
                     'round': mapnik.line_cap.ROUND_CAP,
                     'square': mapnik.line_cap.SQUARE_CAP}

        line_joins = {'miter': mapnik.line_join.MITER_JOIN,
                      'round': mapnik.line_join.ROUND_JOIN,
                      'bevel': mapnik.line_join.BEVEL_JOIN}
    
        stroke = mapnik.Stroke(mapnik.Color(str(self.color)), self.width)
        stroke.opacity = self.opacity or stroke.opacity
        stroke.line_cap = self.cap and line_caps[self.cap] or stroke.line_cap
        stroke.line_join = self.join and line_joins[self.join] or stroke.line_join

        if self.dashes:
            lengths_gaps = list(self.dashes.values)
            while lengths_gaps:
                (length, gap), lengths_gaps = lengths_gaps[:2], lengths_gaps[2:]
                stroke.add_dash(length, gap)

        sym = mapnik.LineSymbolizer(stroke)
        
        return sym

class FontSet:
    def __init__(self, face_names):
        self.faces = tuple(face_names)
    
    def to_mapnik(self):
        if MAPNIK_VERSION >= 200101:
            fontset = mapnik.FontSet(fontset_name(self.faces))
        else:
            fontset = mapnik.FontSet()
        
        for face in self.faces:
            fontset.add_face_name(face)
        
        return fontset

class TextSymbolizer:
    def __init__(self, name, face_name, size, color, wrap_width=None, \
        label_spacing=None, label_position_tolerance=None, max_char_angle_delta=None, \
        halo_color=None, halo_radius=None, dx=None, dy=None, avoid_edges=None, \
        minimum_distance=None, allow_overlap=None, label_placement=None, \
        character_spacing=None, line_spacing=None, text_transform=None, fontset=None, \
        anchor_dx=None, anchor_dy=None,horizontal_alignment=None,vertical_alignment=None,
        justify_alignment=None):

        assert isinstance(name, basestring)
        assert face_name is None or face_name.__class__ is style.strings
        assert fontset is None or isinstance(fontset, basestring)
        assert type(size) is int
        assert color.__class__ is style.color
        assert wrap_width is None or type(wrap_width) is int
        assert label_spacing is None or type(label_spacing) is int
        assert label_position_tolerance is None or type(label_position_tolerance) is int
        assert max_char_angle_delta is None or type(max_char_angle_delta) is int
        assert halo_color is None or halo_color.__class__ is style.color
        assert halo_radius is None or type(halo_radius) is int
        assert dx is None or type(dx) is int
        assert dy is None or type(dy) is int
        assert character_spacing is None or type(character_spacing) is int
        assert line_spacing is None or type(line_spacing) is int
        assert avoid_edges is None or avoid_edges.__class__ is style.boolean
        assert minimum_distance is None or type(minimum_distance) is int
        assert allow_overlap is None or allow_overlap.__class__ is style.boolean
        assert label_placement is None or isinstance(label_placement, basestring)
        assert text_transform is None or isinstance(text_transform, basestring)

        assert face_name or fontset, "Must specify either face_name or fontset"

        self.name = safe_str(name)
        self.face_name = face_name
        self.fontset = safe_str(fontset)
        self.size = size
        self.color = color

        self.wrap_width = wrap_width
        self.label_spacing = label_spacing
        self.label_position_tolerance = label_position_tolerance
        self.max_char_angle_delta = max_char_angle_delta
        self.halo_color = halo_color
        self.halo_radius = halo_radius
        self.dx = dx
        self.dy = dy
        self.character_spacing = character_spacing
        self.line_spacing = line_spacing
        self.allow_overlap = allow_overlap
        self.avoid_edges = avoid_edges
        self.minimum_distance = minimum_distance
        self.label_placement = label_placement
        self.text_transform = text_transform
        self.vertical_alignment = vertical_alignment
        self.justify_alignment = justify_alignment
        self.horizontal_alignment = horizontal_alignment
        self.anchor_dx = anchor_dx
        self.anchor_dy = anchor_dy

    def __repr__(self):
        return 'Text(%s, %s)' % (' '.join(self.face_name.values), self.size)

    def get_fontset_name(self):
        if len(self.face_name.values) > 1 and MAPNIK_VERSION < 200100:
            # Mapnik only supports multiple font face names as of version 2.1
            return None

        if len(self.face_name.values) == 1:
            return None
        
        return fontset_name(self.face_name.values)
    
    def to_mapnik(self, fontsets=None):
        if MAPNIK_VERSION >= 200100:
            convert_enums = {'uppercase': mapnik.text_transform.UPPERCASE,
                             'lowercase': mapnik.text_transform.LOWERCASE}

            if self.get_fontset_name() is not None:
                sym = mapnik.TextSymbolizer(mapnik.Expression('[%s]' % self.name),
                                            '', self.size,
                                            mapnik.Color(str(self.color)))

                sym.format.fontset = fontsets[self.get_fontset_name()]

            else:
                sym = mapnik.TextSymbolizer(mapnik.Expression('[%s]' % self.name),
                                            self.face_name.values[0], self.size,
                                            mapnik.Color(str(self.color)))

        elif MAPNIK_VERSION >= 200000:
            convert_enums = {'uppercase': mapnik.text_transform.UPPERCASE,
                             'lowercase': mapnik.text_transform.LOWERCASE}

            sym = mapnik.TextSymbolizer(mapnik.Expression('[%s]' % self.name),
                                        self.face_name.values[0], self.size,
                                        mapnik.Color(str(self.color)))
        else:
            # note: these match css in Mapnik2
            convert_enums = {'uppercase': mapnik.text_convert.TOUPPER,
                             'lowercase': mapnik.text_convert.TOLOWER}

            sym = mapnik.TextSymbolizer(self.name, self.face_name.values[0], self.size,
                                        mapnik.Color(str(self.color)))

        if MAPNIK_VERSION >= 200100:
            sym.properties.wrap_width = self.wrap_width or sym.properties.wrap_width
            sym.properties.label_spacing = self.label_spacing or sym.properties.label_spacing
            sym.properties.label_position_tolerance = self.label_position_tolerance or sym.properties.label_position_tolerance
            sym.properties.maximum_angle_char_delta = self.max_char_angle_delta or sym.properties.maximum_angle_char_delta

            sym.format.halo_fill = mapnik.Color(str(self.halo_color)) if self.halo_color else sym.format.halo_fill
            sym.format.halo_radius = self.halo_radius or sym.format.halo_radius
            sym.format.character_spacing = self.character_spacing or sym.format.character_spacing
            sym.format.line_spacing = self.line_spacing or sym.format.line_spacing

            sym.properties.avoid_edges = self.avoid_edges.value if self.avoid_edges else sym.properties.avoid_edges
            sym.properties.minimum_distance = self.minimum_distance or sym.properties.minimum_distance
            sym.properties.allow_overlap = self.allow_overlap.value if self.allow_overlap else sym.properties.allow_overlap

            if self.label_placement:
                sym.properties.label_placement \
                    = mapnik.label_placement.names.get(self.label_placement, mapnik.label_placement.POINT_PLACEMENT)
    
            if self.vertical_alignment:
                # match the logic in load_map.cpp for conditionally applying vertical_alignment default
                if self.dx > 0.0:
                    default_vertical_alignment = mapnik.vertical_alignment.BOTTOM
                elif self.dy < 0.0:
                    default_vertical_alignment = mapnik.vertical_alignment.TOP
                else:
                    default_vertical_alignment = mapnik.vertical_alignment.MIDDLE
                
                sym.properties.vertical_alignment \
                    = mapnik.vertical_alignment.names.get(self.vertical_alignment, default_vertical_alignment)
    
            if self.justify_alignment:
                sym.properties.justify_alignment \
                    = mapnik.justify_alignment.names.get(self.justify_alignment, mapnik.justify_alignment.MIDDLE)
    
        else:
            sym.wrap_width = self.wrap_width or sym.wrap_width
            sym.label_spacing = self.label_spacing or sym.label_spacing
            sym.label_position_tolerance = self.label_position_tolerance or sym.label_position_tolerance
            sym.max_char_angle_delta = self.max_char_angle_delta or sym.max_char_angle_delta

            sym.halo_fill = mapnik.Color(str(self.halo_color)) if self.halo_color else sym.halo_fill
            sym.halo_radius = self.halo_radius or sym.halo_radius
            sym.character_spacing = self.character_spacing or sym.character_spacing
            sym.line_spacing = self.line_spacing or sym.line_spacing

            sym.avoid_edges = self.avoid_edges.value if self.avoid_edges else sym.avoid_edges
            sym.minimum_distance = self.minimum_distance or sym.minimum_distance
            sym.allow_overlap = self.allow_overlap.value if self.allow_overlap else sym.allow_overlap
        
            if self.label_placement:
                sym.label_placement \
                    = mapnik.label_placement.names.get(self.label_placement, mapnik.label_placement.POINT_PLACEMENT)
    
            if self.vertical_alignment:
                # match the logic in load_map.cpp for conditionally applying vertical_alignment default
                if self.dx > 0.0:
                    default_vertical_alignment = mapnik.vertical_alignment.BOTTOM
                elif self.dy < 0.0:
                    default_vertical_alignment = mapnik.vertical_alignment.TOP
                else:
                    default_vertical_alignment = mapnik.vertical_alignment.MIDDLE
                
                sym.vertical_alignment \
                    = mapnik.vertical_alignment.names.get(self.vertical_alignment, default_vertical_alignment)
    
            if self.justify_alignment:
                sym.justify_alignment \
                    = mapnik.justify_alignment.names.get(self.justify_alignment, mapnik.justify_alignment.MIDDLE)
    
        if self.text_transform and MAPNIK_VERSION >= 200000:
            sym.text_convert = convert_enums.get(self.text_transform, mapnik.text_transform.NONE)
        elif self.text_transform:
            # note-renamed in Mapnik2 to 'text_transform'
            sym.text_convert = convert_enums.get(self.text_transform, mapnik.text_convert.NONE)

        if self.fontset:
        #    sym.fontset = str(self.fontset)
             # not viable via python
            sys.stderr.write('\nCascadenik debug: Warning, FontSets will be ignored as they are not yet supported in Mapnik via Python...\n')
        
        if MAPNIK_VERSION >= 200100:
            sym.properties.displacement = (self.dx or 0.0, self.dy or 0.0)
        elif MAPNIK_VERSION >= 200000:
            sym.displacement = (self.dx or 0.0, self.dy or 0.0)
        else:
            sym.displacement(self.dx or 0.0, self.dy or 0.0)
        
        if MAPNIK_VERSION >= 200100:
            sym.clip = False

        return sym

class ShieldSymbolizer:
    def __init__(self, name, face_name=None, size=None, file=None, filetype=None, \
        width=None, height=None, color=None, minimum_distance=None, character_spacing=None, \
        line_spacing=None, label_spacing=None, fontset=None, text_dx=0, text_dy=0):
        
        assert (face_name or fontset) and file
        
        assert isinstance(name, basestring)
        assert face_name is None or face_name.__class__ is style.strings
        assert fontset is None or isinstance(fontset, basestring)
        assert size is None or type(size) is int
        assert width is None or type(width) is int
        assert height is None or type(height) is int

        assert color is None or color.__class__ is style.color
        assert character_spacing is None or type(character_spacing) is int
        assert line_spacing is None or type(line_spacing) is int
        assert label_spacing is None or type(label_spacing) is int
        assert minimum_distance is None or type(minimum_distance) is int

        assert text_dx is None or type(text_dx) is int
        assert text_dy is None or type(text_dy) is int

        self.name = safe_str(name)
        self.face_name = face_name
        self.fontset = safe_str(fontset)
        self.size = size or 10
        self.file = safe_str(file)
        self.type = safe_str(filetype)
        self.width = width
        self.height = height

        self.color = color
        self.character_spacing = character_spacing
        self.line_spacing = line_spacing
        self.label_spacing = label_spacing
        self.minimum_distance = minimum_distance
        self.text_dx = text_dx
        self.text_dy = text_dy

    def __repr__(self):
        return 'Shield(%s, %s, %s, %s)' % (self.name, ' '.join(self.face_name.values), self.size, self.file)

    def get_fontset_name(self):
        if len(self.face_name.values) > 1 and MAPNIK_VERSION < 200100:
            raise OutputException("Mapnik only supports multiple font face names as of version 2.1")

        if len(self.face_name.values) == 1:
            return None
        
        return fontset_name(self.face_name.values)
    
    def to_mapnik(self, fontsets=None):
        if MAPNIK_VERSION >= 200100:
            if self.get_fontset_name() is not None:
                sym = mapnik.ShieldSymbolizer(
                        mapnik.Expression('[%s]' % self.name), '', self.size or 10, 
                        mapnik.Color(str(self.color)) if self.color else mapnik.Color('black'), 
                        mapnik.PathExpression(self.file))

                sym.fontset = fontsets[self.get_fontset_name()]

            else:
                sym = mapnik.ShieldSymbolizer(
                        mapnik.Expression('[%s]' % self.name), self.face_name.values[0], self.size or 10, 
                        mapnik.Color(str(self.color)) if self.color else mapnik.Color('black'), 
                        mapnik.PathExpression(self.file))

        elif MAPNIK_VERSION >= 200000:
            sym = mapnik.ShieldSymbolizer(
                    mapnik.Expression('[%s]' % self.name), self.face_name.values[0], self.size or 10, 
                    mapnik.Color(str(self.color)) if self.color else mapnik.Color('black'), 
                    mapnik.PathExpression(self.file))
        else:
            sym = mapnik.ShieldSymbolizer(
                    self.name, self.face_name.values[0], self.size or 10, 
                    mapnik.Color(str(self.color)) if self.color else mapnik.Color('black'), 
                    self.file, self.type, self.width, self.height)

        sym.character_spacing = self.character_spacing or sym.character_spacing
        sym.line_spacing = self.line_spacing or sym.line_spacing
        sym.label_placement = self.label_spacing and mapnik.label_placement.LINE_PLACEMENT or sym.label_placement
        sym.label_spacing = self.label_spacing or sym.label_spacing
        sym.minimum_distance = self.minimum_distance or sym.minimum_distance

        if self.fontset:
            sym.fontset = self.fontset.value
        
        if MAPNIK_VERSION >= 200000:
            sym.displacement = (self.text_dx or 0, self.text_dy or 0)
        else:
            sym.displacement(self.text_dx or 0, self.text_dy or 0)
        
        if MAPNIK_VERSION >= 200100:
            sym.clip = False

        return sym

class BasePointSymbolizer(object):
    def __init__(self, file, filetype, width, height):
        assert isinstance(file, basestring)
        assert isinstance(filetype, basestring)
        assert type(width) is int
        assert type(height) is int

        self.file = safe_str(file)
        self.type = safe_str(filetype)
        self.width = width
        self.height = height

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.file)

    def to_mapnik(self):
        sym_class = getattr(mapnik, self.__class__.__name__)
        
        if MAPNIK_VERSION >= 200000:
            sym = sym_class(mapnik.PathExpression(self.file))
        else:
            sym = sym_class(self.file, self.type, self.width, self.height)
        
        return sym

class PointSymbolizer(BasePointSymbolizer):
    def __init__(self, file, filetype, width, height, allow_overlap=None):
        super(PointSymbolizer, self).__init__(file, filetype, width, height)

        assert allow_overlap is None or allow_overlap.__class__ is style.boolean

        self.allow_overlap = allow_overlap

    def to_mapnik(self):
        sym = super(PointSymbolizer, self).to_mapnik()
        
        sym.allow_overlap = self.allow_overlap.value if self.allow_overlap else sym.allow_overlap
        
        return sym
        

class PolygonPatternSymbolizer(BasePointSymbolizer):
    pass

class LinePatternSymbolizer(BasePointSymbolizer):
    pass

########NEW FILE########
__FILENAME__ = parse
import re
import operator
from copy import deepcopy
from itertools import chain, product
from binascii import unhexlify as unhex
from cssutils.tokenize2 import Tokenizer as cssTokenizer

from .style import properties, numbers, strings, boolean, uri, color, color_transparent
from .style import Selector, SelectorElement, ConcatenatedElement, SelectorAttributeTest
from .style import Declaration, Property, Value

class ParseException(Exception):
    """ Exception raised when a parsing error is encountered.
    
        Includes the line and column from the origin style text.
    """
    def __init__(self, msg, line, col):
        Exception.__init__(self, '%(msg)s (line %(line)d, column %(col)d)' % locals())

class BlockTerminatedValue (Exception):
    """ Exception generated when a value ends at a block instead of a semicolon.
    
        Caught and handled in parse_block(), not really an error.
    """
    def __init__(self, tokens, important, line, col):
        self.tokens = tokens
        self.important = important
        self.line = line
        self.col = col

def stylesheet_declarations(string, is_merc=False, scale=1):
    """ Parse a string representing a stylesheet into a list of declarations.
    
        Required boolean is_merc indicates whether the projection should
        be interpreted as spherical mercator, so we know what to do with
        zoom/scale-denominator in parse_rule().
    """
    # everything is display: map by default
    display_map = Declaration(Selector(SelectorElement(['*'], [])),
                              Property('display'), Value('map', False),
                              (False, (0, 0, 0), (0, 0)))
    
    declarations = [display_map]

    tokens = cssTokenizer().tokenize(string)
    variables = {}
    
    while True:
        try:
            for declaration in parse_rule(tokens, variables, [], [], is_merc):
                if scale != 1:
                    declaration.scaleBy(scale)
            
                declarations.append(declaration)
        except StopIteration:
            break
    
    # sort by a css-like method
    return sorted(declarations, key=operator.attrgetter('sort_key'))

def parse_attribute(tokens, is_merc):
    """ Parse a token stream from inside an attribute selector.
    
        Enter this function after a left-bracket is found:
        http://www.w3.org/TR/CSS2/selector.html#attribute-selectors
    """
    #
    # Local helper functions
    #

    def next_scalar(tokens, op):
        """ Look for a scalar value just after an attribute selector operator.
        """
        while True:
            tname, tvalue, line, col = tokens.next()
            if tname == 'NUMBER':
                try:
                    value = int(tvalue)
                except ValueError:
                    value = float(tvalue)
                return value
            elif (tname, tvalue) == ('CHAR', '-'):
                tname, tvalue, line, col = tokens.next()
                if tname == 'NUMBER':
                    try:
                        value = int(tvalue)
                    except ValueError:
                        value = float(tvalue)
                    return -value
                else:
                    raise ParseException('Unexpected non-number after a minus sign', line, col)
            elif tname in ('STRING', 'IDENT'):
                if op in ('<', '<=', '=>', '>'):
                    raise ParseException('Selector attribute must use a number for comparison tests', line, col)
                if tname == 'STRING':
                    return tvalue[1:-1]
                else:
                    return tvalue
            elif tname != 'S':
                raise ParseException('Unexpected non-scalar token in attribute', line, col)
    
    def finish_attribute(tokens):
        """ Look for the end of an attribute selector operator.
        """
        while True:
            tname, tvalue, line, col = tokens.next()
            if (tname, tvalue) == ('CHAR', ']'):
                return
            elif tname != 'S':
                raise ParseException('Found something other than a closing right-bracket at the end of attribute', line, col)
    
    #
    # The work.
    #
    
    while True:
        tname, tvalue, line, col = tokens.next()
        
        if tname == 'IDENT':
            property = tvalue
            
            while True:
                tname, tvalue, line, col = tokens.next()
                
                if (tname, tvalue) in [('CHAR', '<'), ('CHAR', '>')]:
                    _tname, _tvalue, line, col = tokens.next()
        
                    if (_tname, _tvalue) == ('CHAR', '='):
                        #
                        # Operator is one of '<=', '>='
                        #
                        op = tvalue + _tvalue
                        value = next_scalar(tokens, op)
                        finish_attribute(tokens)
                        return SelectorAttributeTest(property, op, value)
                    
                    else:
                        #
                        # Operator is one of '<', '>' and we popped a token too early
                        #
                        op = tvalue
                        value = next_scalar(chain([(_tname, _tvalue, line, col)], tokens), op)
                        finish_attribute(tokens)
                        return SelectorAttributeTest(property, op, value)
                
                elif (tname, tvalue) == ('CHAR', '!'):
                    _tname, _tvalue, line, col = tokens.next()
        
                    if (_tname, _tvalue) == ('CHAR', '='):
                        #
                        # Operator is '!='
                        #
                        op = tvalue + _tvalue
                        value = next_scalar(tokens, op)
                        finish_attribute(tokens)
                        return SelectorAttributeTest(property, op, value)
                    
                    else:
                        raise ParseException('Malformed operator in attribute selector', line, col)
                
                elif (tname, tvalue) == ('CHAR', '='):
                    #
                    # Operator is '='
                    #
                    op = tvalue
                    value = next_scalar(tokens, op)
                    finish_attribute(tokens)
                    return SelectorAttributeTest(property, op, value)
                
                elif tname != 'S':
                    raise ParseException('Missing operator in attribute selector', line, col)
        
        elif tname != 'S':
            raise ParseException('Unexpected token in attribute selector', line, col)

    raise ParseException('Malformed attribute selector', line, col)

def postprocess_value(property, tokens, important, line, col):
    """ Convert a list of property value tokens into a single Value instance.
    
        Values can be numbers, strings, colors, uris, or booleans:
        http://www.w3.org/TR/CSS2/syndata.html#values
    """
    #
    # Helper function.
    #
    
    def combine_negative_numbers(tokens, line, col):
        """ Find negative numbers in a list of tokens, return a new list.
        
            Negative numbers come as two tokens, a minus sign and a number.
        """
        tokens, original_tokens = [], iter(tokens)
        
        while True:
            try:
                tname, tvalue = original_tokens.next()[:2]
                
                if (tname, tvalue) == ('CHAR', '-'):
                    tname, tvalue = original_tokens.next()[:2]
    
                    if tname == 'NUMBER':
                        # minus sign with a number is a negative number
                        tokens.append(('NUMBER', '-'+tvalue))
                    else:
                        raise ParseException('Unexpected non-number after a minus sign', line, col)
    
                else:
                    tokens.append((tname, tvalue))
    
            except StopIteration:
                break
        
        return tokens
    
    #
    # The work.
    #
    
    tokens = combine_negative_numbers(tokens, line, col)
    
    if properties[property.name] in (int, float, str, color, uri, boolean) or type(properties[property.name]) is tuple:
        if len(tokens) != 1:
            raise ParseException('Single value only for property "%(property)s"' % locals(), line, col)

    if properties[property.name] is int:
        if tokens[0][0] != 'NUMBER':
            raise ParseException('Number value only for property "%(property)s"' % locals(), line, col)

        value = int(tokens[0][1])

    elif properties[property.name] is float:
        if tokens[0][0] != 'NUMBER':
            raise ParseException('Number value only for property "%(property)s"' % locals(), line, col)

        value = float(tokens[0][1])

    elif properties[property.name] is str:
        if tokens[0][0] != 'STRING':
            raise ParseException('String value only for property "%(property)s"' % locals(), line, col)

        value = str(tokens[0][1][1:-1])

    elif properties[property.name] is color_transparent:
        if tokens[0][0] != 'HASH' and (tokens[0][0] != 'IDENT' or tokens[0][1] != 'transparent'):
            raise ParseException('Hash or transparent value only for property "%(property)s"' % locals(), line, col)

        if tokens[0][0] == 'HASH':
            if not re.match(r'^#([0-9a-f]{3}){1,2}$', tokens[0][1], re.I):
                raise ParseException('Unrecognized color value for property "%(property)s"' % locals(), line, col)
    
            hex = tokens[0][1][1:]
            
            if len(hex) == 3:
                hex = hex[0]+hex[0] + hex[1]+hex[1] + hex[2]+hex[2]
            
            rgb = (ord(unhex(h)) for h in (hex[0:2], hex[2:4], hex[4:6]))
            
            value = color(*rgb)

        else:
            value = 'transparent'

    elif properties[property.name] is color:
        if tokens[0][0] != 'HASH':
            raise ParseException('Hash value only for property "%(property)s"' % locals(), line, col)

        if not re.match(r'^#([0-9a-f]{3}){1,2}$', tokens[0][1], re.I):
            raise ParseException('Unrecognized color value for property "%(property)s"' % locals(), line, col)

        hex = tokens[0][1][1:]
        
        if len(hex) == 3:
            hex = hex[0]+hex[0] + hex[1]+hex[1] + hex[2]+hex[2]
        
        rgb = (ord(unhex(h)) for h in (hex[0:2], hex[2:4], hex[4:6]))
        
        value = color(*rgb)

    elif properties[property.name] is uri:
        if tokens[0][0] != 'URI':
            raise ParseException('URI value only for property "%(property)s"' % locals(), line, col)

        raw = str(tokens[0][1])

        if raw.startswith('url("') and raw.endswith('")'):
            raw = raw[5:-2]
            
        elif raw.startswith("url('") and raw.endswith("')"):
            raw = raw[5:-2]
            
        elif raw.startswith('url(') and raw.endswith(')'):
            raw = raw[4:-1]

        value = uri(raw)
            
    elif properties[property.name] is boolean:
        if tokens[0][0] != 'IDENT' or tokens[0][1] not in ('true', 'false'):
            raise ParseException('true/false value only for property "%(property)s"' % locals(), line, col)

        value = boolean(tokens[0][1] == 'true')
            
    elif type(properties[property.name]) is tuple:
        if tokens[0][0] != 'IDENT':
            raise ParseException('Identifier value only for property "%(property)s"' % locals(), line, col)

        if tokens[0][1] not in properties[property.name]:
            raise ParseException('Unrecognized value for property "%(property)s"' % locals(), line, col)

        value = str(tokens[0][1])
            
    elif properties[property.name] is numbers:
        values = []
        
        # strip spaces from the list
        relevant_tokens = [token for token in tokens if token[0] != 'S']
        
        for (i, token) in enumerate(relevant_tokens):
            if (i % 2) == 0 and token[0] == 'NUMBER':
                try:
                    value = int(token[1])
                except ValueError:
                    value = float(token[1])

                values.append(value)

            elif (i % 2) == 1 and token[0] == 'CHAR':
                # fine, it's a comma
                continue

            else:
                raise ParseException('Value for property "%(property)s" should be a comma-delimited list of numbers' % locals(), line, col)

        value = numbers(*values)

    elif properties[property.name] is strings:
        values = []
    
        # strip spaces from the list
        relevant_tokens = [token for token in tokens if token[0] != 'S']
        
        for (i, token) in enumerate(relevant_tokens):
            if (i % 2) == 0 and token[0] == 'STRING':
                values.append(str(token[1][1:-1]))
            
            elif (i % 2) == 1 and token == ('CHAR', ','):
                # fine, it's a comma
                continue
            
            else:
                raise ParseException('Value for property "%(property)s" should be a comma-delimited list of strings' % locals(), line, col)
    
        value = strings(*values)

    return Value(value, important)

def parse_block(tokens, variables, selectors, is_merc):
    """ Parse a token stream into an array of declaration tuples.
    
        In addition to tokens, requires a dictionary of declared variables,
        a list of selectors that will apply to the declarations parsed in
        this block, and a boolean flag for mercator projection, both needed
        by possible recursive calls back to parse_rule().
    
        Return an array of (property, value, (line, col), importance).
    
        Enter this function after a left-brace is found:
        http://www.w3.org/TR/CSS2/syndata.html#block
    """
    #
    # Local helper functions
    #

    def parse_value(tokens, variables):
        """ Look for value tokens after a property name, possibly !important.
        """
        value = []
        while True:
            tname, tvalue, line, col = tokens.next()
            if (tname, tvalue) == ('CHAR', '!'):
                while True:
                    tname, tvalue, line, col = tokens.next()
                    if (tname, tvalue) == ('IDENT', 'important'):
                        while True:
                            tname, tvalue, line, col = tokens.next()
                            if (tname, tvalue) == ('CHAR', ';'):
                                #
                                # end of a high-importance value
                                #
                                return value, True
                            elif (tname, tvalue) == ('CHAR', '}'):
                                #
                                # end of a block means end of a value
                                #
                                raise BlockTerminatedValue(value, True, line, col)
                            elif (tname, tvalue) == ('S', '\n'):
                                raise ParseException('Unexpected end of line', line, col)
                            elif tname not in ('S', 'COMMENT'):
                                raise ParseException('Unexpected values after !important declaration', line, col)
                        break
                    else:
                        raise ParseException('Malformed declaration after "!"', line, col)
                break
            elif (tname, tvalue) == ('CHAR', ';'):
                #
                # end of a low-importance value
                #
                return value, False
            elif (tname, tvalue) == ('CHAR', '}'):
                #
                # end of a block means end of a value
                #
                raise BlockTerminatedValue(value, False, line, col)
            elif tname == 'ATKEYWORD':
                #
                # Possible variable use:
                # http://lesscss.org/#-variables
                #
                tokens = chain(iter(variables[tvalue]), tokens)
            elif (tname, tvalue) == ('S', '\n'):
                raise ParseException('Unexpected end of line', line, col)
            elif tname not in ('S', 'COMMENT'):
                #
                # Legitimate-looking value token.
                #
                value.append((tname, tvalue))
        raise ParseException('Malformed property value', line, col)
    
    #
    # The work.
    #
    
    ruleset = []
    property_values = []
    
    while True:
        tname, tvalue, line, col = tokens.next()
        
        if tname == 'IDENT':
            _tname, _tvalue, _line, _col = tokens.next()
            
            if (_tname, _tvalue) == ('CHAR', ':'):
                #
                # Retrieve and process a value after a property name.
                # http://www.w3.org/TR/CSS2/syndata.html#declaration
                #
                if tvalue not in properties:
                    raise ParseException('Unsupported property name, %s' % tvalue, line, col)

                try:
                    property = Property(tvalue)
                    vtokens, importance = parse_value(tokens, variables)
                except BlockTerminatedValue, e:
                    vtokens, importance = e.tokens, e.important
                    tokens = chain([('CHAR', '}', e.line, e.col)], tokens)

                value = postprocess_value(property, vtokens, importance, line, col)
                property_values.append((property, value, (line, col), importance))
                
            else:
                #
                # We may have just found the start of a nested block.
                # http://lesscss.org/#-nested-rules
                #
                tokens_ = chain([(tname, tvalue, line, col), (_tname, _tvalue, _line, _col)], tokens)
                ruleset += parse_rule(tokens_, variables, [], selectors, is_merc)
        
        elif (tname, tvalue) == ('CHAR', '}'):
            #
            # Closing out a block
            #
            for (selector, property_value) in product(selectors, property_values):

                property, value, (line, col), importance = property_value
                sort_key = value.importance(), selector.specificity(), (line, col)

                ruleset.append(Declaration(selector, property, value, sort_key))
                
            return ruleset
        
        elif tname in ('HASH', ) or (tname, tvalue) in [('CHAR', '.'), ('CHAR', '*'), ('CHAR', '['), ('CHAR', '&')]:
            #
            # One of a bunch of valid ways to start a nested rule.
            #
            # Most will end up rejected by Cascadenik as parsing errors,
            # except for identifiers for text rules and the start of
            # nested blocks with a "&" combinator:
            # http://lesscss.org/#-nested-rules
            #
            tokens_ = chain([(tname, tvalue, line, col)], tokens)
            ruleset += parse_rule(tokens_, variables, [], selectors, is_merc)
        
        elif tname not in ('S', 'COMMENT'):
            raise ParseException('Malformed style rule', line, col)

    raise ParseException('Malformed block', line, col)

def parse_rule(tokens, variables, neighbors, parents, is_merc):
    """ Parse a rule set, return a list of declarations.
        
        Requires a dictionary of declared variables. Selectors in the neighbors
        list are simply grouped, and are generated from comma-delimited lists
        of selectors in the stylesheet. Selectors in the parents list should
        be combined with those found by this functions, and are generated
        from nested, Less-style rulesets.
        
        A rule set is a combination of selectors and declarations:
        http://www.w3.org/TR/CSS2/syndata.html#rule-sets
        
        Nesting is described in the Less CSS spec:
        http://lesscss.org/#-nested-rules
    
        To handle groups of selectors, use recursion:
        http://www.w3.org/TR/CSS2/selector.html#grouping
    """
    #
    # Local helper function
    #

    def validate_selector_elements(elements, line, col):
        if len(elements) > 2:
            raise ParseException('Only two-element selectors are supported for Mapnik styles', line, col)
    
        if len(elements) == 0:
            raise ParseException('At least one element must be present in selectors for Mapnik styles', line, col)
    
        if elements[0].names[0] not in ('Map', 'Layer') and elements[0].names[0][0] not in ('.', '#', '*'):
            raise ParseException('All non-ID, non-class first elements must be "Layer" Mapnik styles', line, col)
        
        if set([name[:1] for name in elements[0].names[1:]]) - set('#.'):
            raise ParseException('All names after the first must be IDs or classes', line, col)
        
        if len(elements) == 2 and elements[1].countTests():
            raise ParseException('Only the first element in a selector may have attributes in Mapnik styles', line, col)
    
        if len(elements) == 2 and elements[1].countIDs():
            raise ParseException('Only the first element in a selector may have an ID in Mapnik styles', line, col)
    
        if len(elements) == 2 and elements[1].countClasses():
            raise ParseException('Only the first element in a selector may have a class in Mapnik styles', line, col)
    
    def parse_variable_definition(tokens):
        """ Look for variable value tokens after an @keyword, return an array.
        """
        while True:
            tname, tvalue, line, col = tokens.next()
            
            if (tname, tvalue) == ('CHAR', ':'):
                vtokens = []
            
                while True:
                    tname, tvalue, line, col = tokens.next()
            
                    if (tname, tvalue) in (('CHAR', ';'), ('S', '\n')):
                        return vtokens
                    
                    elif tname not in ('S', 'COMMENT'):
                        vtokens.append((tname, tvalue, line, col))

            elif tname not in ('S', 'COMMENT'):
                raise ParseException('Unexpected token in variable definition: "%s"' % tvalue, line, col)
            
    #
    # The work.
    #
    
    ElementClass = SelectorElement
    element = None
    elements = []
    
    while True:
        tname, tvalue, line, col = tokens.next()
        
        if tname == 'ATKEYWORD':
            #
            # Likely variable definition:
            # http://lesscss.org/#-variables
            #
            variables[tvalue] = parse_variable_definition(tokens)
        
        elif (tname, tvalue) == ('CHAR', '&'):
            #
            # Start of a nested block with a "&" combinator
            # http://lesscss.org/#-nested-rules
            #
            ElementClass = ConcatenatedElement
        
        elif tname == 'S':
            #
            # Definitely no longer in a "&" combinator.
            #
            ElementClass = SelectorElement
        
        elif tname == 'IDENT':
            #
            # Identifier always starts a new element.
            #
            element = ElementClass()
            elements.append(element)
            element.addName(tvalue)
            
        elif tname == 'HASH':
            #
            # Hash is an ID selector:
            # http://www.w3.org/TR/CSS2/selector.html#id-selectors
            #
            if not element:
                element = ElementClass()
                elements.append(element)
        
            element.addName(tvalue)
        
        elif (tname, tvalue) == ('CHAR', '.'):
            while True:
                tname, tvalue, line, col = tokens.next()
                
                if tname == 'IDENT':
                    #
                    # Identifier after a period is a class selector:
                    # http://www.w3.org/TR/CSS2/selector.html#class-html
                    #
                    if not element:
                        element = ElementClass()
                        elements.append(element)
                
                    element.addName('.'+tvalue)
                    break
                
                else:
                    raise ParseException('Malformed class selector', line, col)
        
        elif (tname, tvalue) == ('CHAR', '*'):
            #
            # Asterisk character is a universal selector:
            # http://www.w3.org/TR/CSS2/selector.html#universal-selector
            #
            if not element:
                element = ElementClass()
                elements.append(element)
        
            element.addName(tvalue)

        elif (tname, tvalue) == ('CHAR', '['):
            #
            # Left-bracket is the start of an attribute selector:
            # http://www.w3.org/TR/CSS2/selector.html#attribute-selectors
            #
            if not element:
                element = ElementClass()
                elements.append(element)
        
            test = parse_attribute(tokens, is_merc)
            element.addTest(test)
        
        elif (tname, tvalue) == ('CHAR', ','):
            #
            # Comma delineates one of a group of selectors:
            # http://www.w3.org/TR/CSS2/selector.html#grouping
            #
            # Recurse here.
            #
            neighbors.append(Selector(*elements))
            
            return parse_rule(tokens, variables, neighbors, parents, is_merc)
        
        elif (tname, tvalue) == ('CHAR', '{'):
            #
            # Left-brace is the start of a block:
            # http://www.w3.org/TR/CSS2/syndata.html#block
            #
            # Return a full block here.
            #
            class DummySelector:
                def __init__(self, *elements):
                    self.elements = elements[:]
            
            neighbors.append(DummySelector(*elements))
            
            selectors = []

            #
            # Combine lists of parents and neighbors into a single list of
            # selectors, for passing off to parse_block(). There might not
            # be any parents, but there will definitely be neighbors.
            #
            for parent in (parents or [DummySelector()]):
                for neighbor in neighbors:
                    if len(neighbor.elements) == 0:
                        raise ParseException('At least one element must be present in selectors for Mapnik styles', line, col)
                    
                    elements = chain(parent.elements + neighbor.elements)
                    selector = Selector(deepcopy(elements.next()))
                    
                    for element in elements:
                        if element.__class__ is ConcatenatedElement:
                            for name in element.names: selector.elements[-1].addName(deepcopy(name))
                            for test in element.tests: selector.elements[-1].addTest(deepcopy(test))
                        else:
                            selector.addElement(deepcopy(element))
                    
                    # selector should be fully valid at this point.
                    validate_selector_elements(selector.elements, line, col)
                    selector.convertZoomTests(is_merc)
                    selectors.append(selector)
            
            return parse_block(tokens, variables, selectors, is_merc)
        
        elif tname not in ('S', 'COMMENT'):
            raise ParseException('Unexpected token in selector: "%s"' % tvalue, line, col)

########NEW FILE########
__FILENAME__ = safe64
import base64, os

"""
simulate an unlimited-length kv store using normal directories
"""

def key(base):
    """ get a list of all *leaf* directories as strings """
    for root, dirs, files in os.walk(base, topdown=False):
        for file in files:
            yield os.path.join(root, file)
            # if root != base and root != dir:
            #     yield os.path.join(root, dir)

def chunk(url):
    """ create filesystem-safe places for url-keyed data to be stored """
    chunks = lambda l, n: [l[x: x+n] for x in xrange(0, len(l), n)]
    url_64 = base64.urlsafe_b64encode(url)
    return chunks(url_64, 255)

def dir(url):
    """ use safe64 to create a proper directory """
    return "/".join(chunk(url))

def decode(url):
    """ use safe64 to create a proper directory """
    return base64.urlsafe_b64decode(url.replace('/', ''))

########NEW FILE########
__FILENAME__ = sources
import ConfigParser
import StringIO
import urlparse
import urllib

from . import mapnik

class DataSources(object):
    def __init__(self, base, local_cfg):
        self.templates = set([])
        self.sources = {}
        self.defaults = {}
        self.local_cfg_data = None
        self.local_cfg_url = None
        self.finalized = False
        
        # avoid circular import
        import compile
        self.msg = compile.msg     
        
        # if a local_cfg is provided, we want to get the defaults first, before reading any other
        # configuration.
        if local_cfg:
            self.local_cfg_url = urlparse.urljoin(base, local_cfg)
            self.msg("Using local datasource config: %s" % self.local_cfg_url)
            self.set_local_cfg_data(urllib.urlopen(self.local_cfg_url).read().decode(compile.DEFAULT_ENCODING))
            
    def set_local_cfg_data(self, data):
        self.local_cfg_data = data
        locals = OverrideConfigParser({})
        locals.loads(data)
        self.defaults = locals.defaults()

    def finalize(self):
        if self.local_cfg_data:
            self.msg("Loading local config data: %s" % self.local_cfg_url)
            self.add_config(self.local_cfg_data, self.local_cfg_url)
        self.finalized = True

    def get(self, name):
        if not self.finalized:
            self.finalize()
        return self.sources.get(name)

    def add_config(self, textdata, filename):
        parser = OverrideConfigParser(self.defaults)
        parser.loads(textdata)

        for sect in parser.sections():
            options = {}
            name = sect
            dtype = parser.get(sect,"type") if parser.has_option(sect, "type") else None
            template = parser.get(sect,"template") if parser.has_option(sect, "template") else None
            layer_srs = parser.get(sect,"layer_srs") if parser.has_option(sect, "layer_srs") else None

            # this layer declares a template template
            if template:
                self.templates.add(template)
                # the template may have been declared already, or we haven't processed it yet.
                if template in self.sources:
                    dtype = self.sources[template]['parameters'].get('type', dtype)
                    layer_srs = self.sources[template].get('layer_srs', layer_srs)
                else:
                    # TODO catch section missing errors
                    dtype = parser.get(template, 'type')
                    layer_srs = parser.get(template, 'layer_srs') if parser.has_option(template, 'layer_srs') else layer_srs

            # handle the most common projections
            if layer_srs and layer_srs.lower().startswith("epsg:"):
                if self.PROJ4_PROJECTIONS.get(layer_srs.lower()):
                    layer_srs = self.PROJ4_PROJECTIONS.get(layer_srs.lower())
                else:
                    layer_srs = '+init=%s' % layer_srs

            # try to init the projection
            if layer_srs:
                try:
                    mapnik.Projection(str(layer_srs))
                except Exception, e:
                    raise Exception("Section [%s] declares an invalid layer_srs (%s) in %s.\n\t%s" % (sect, layer_srs, filename, e))
                    
            if dtype:
                options['type'] = dtype
            else:
                raise Exception("Section [%s] missing 'type' information in %s." % (sect, filename))
            
            # now populate the options for this type of source, looping over all the valid params
            for option, option_type in self.XML_OPTIONS[dtype].items():
                opt_value = None
                try:
                    if option_type == int:
                        opt_value = parser.getint(sect,option)
                    elif option_type == float:
                        opt_value = parser.getfloat(sect,option)
                    elif option_type == bool:
                        opt_value = parser.getboolean(sect,option)
                    else:
                        opt_value = parser.get(sect,option)
                except ConfigParser.NoOptionError:
                    pass
                except ValueError, e:
                    raise ValueError("Section [%s], field '%s' in file %s contains an invalid value: %s" % (sect, option, filename, e))

                if opt_value is not None:
                    options[option] = opt_value

            # build an object mirroring the XML Datasource object
            conf = dict(parameters=options)
            if template:
                conf['template'] = template
            if layer_srs:
                conf['layer_srs'] = layer_srs
            self.sources[name] = conf
                

    PROJ4_PROJECTIONS = {"epsg:4326" : "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs",
                         "epsg:900913" : "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs"
                         }

    XML_OPTIONS = {"shape" : dict(file=str,encoding=str,base=str),
                   "postgis" : dict(cursor_size=int,
                                    dbname=str,
                                    geometry_field=str,
                                    estimate_extent=bool,
                                    host=str,
                                    initial_size=int,
                                    max_size=int,
                                    multiple_geometries=bool,
                                    password=str,
                                    persist_connection=bool,
                                    port=int,
                                    row_limit=int,
                                    table=str,
                                    srid=int,
                                    user=str),
                   "ogr" : dict(layer=str, file=str),
                   "osm" : dict(file=str, parser=str, url=str, bbox=str),
                   "gdal": dict(file=str, base=str),
                   "occi": dict(user=str, password=str, host=str, table=str,
                                initial_size=int,
                                max_size=int,
                                estimate_extent=bool,
                                encoding=str,
                                geometry_field=str,
                                use_spatial_index=bool,
                                multiple_geometries=bool),
                   "sqlite":dict(file=str,
                                 table=str,
                                 base=str,
                                 encoding=str,
                                 metadata=str,
                                 geometry_field=str,
                                 key_field=str,
                                 row_offset=int,
                                 row_limit=int,
                                 wkb_format=str,
                                 multiple_geometries=bool,
                                 use_spatial_index=bool),
                   "kismet":dict(host=str,
                                 port=int,
                                 encoding=str),
                   "raster":dict(file=str,
                                 lox=float,
                                 loy=float,
                                 hix=float,
                                 hiy=float,
                                 base=str),
                   }

    # add in global options
    for v in XML_OPTIONS.values():
        v.update(dict(type=str, estimate_extent=bool, extent=str))

class OverrideConfigParser(ConfigParser.SafeConfigParser):
    def __init__(self, overrides):
        ConfigParser.SafeConfigParser.__init__(self, overrides)
        self.overrides = overrides

    def loads(self, textdata):
        data = StringIO.StringIO(textdata)
        data.seek(0)
        self.readfp(data)

    def get(self, section, option):
        return ConfigParser.SafeConfigParser.get(self, section, option, vars=self.overrides)
    

########NEW FILE########
__FILENAME__ = style
from math import log
from copy import deepcopy
import operator

class color:
    def __init__(self, r, g, b):
        self.channels = r, g, b

    def __repr__(self):
        return '#%02x%02x%02x' % self.channels

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        return self.channels == other.channels

class color_transparent(color):
    pass

class uri:
    def __init__(self, address):
        self.address = address

    def __repr__(self):
        return str(self.address) #'url("%(address)s")' % self.__dict__

    def __str__(self):
        return repr(self)

class boolean:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        if self.value:
            return 'true'
        else:
            return 'false'

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        return hasattr(other, 'value') and bool(self.value) == bool(other.value)

class numbers:
    def __init__(self, *values):
        self.values = values

    def __repr__(self):
        return ','.join(map(str, self.values))

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        return self.values == other.values

class strings:
    def __init__(self, *values):
        self.values = values

    def __repr__(self):
        return ','.join(map(str, self.values))

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        return self.values == other.values

# recognized properties

properties = {
    # 
    'display': ('map', 'none'),

    #--------------- map

    # 
    'map-bgcolor': color_transparent,

    #--------------- polygon symbolizer

    # polygon fill color
    'polygon-fill': color,

    # gamma value affecting level of antialiases of polygon edges
    # 0.0 - 1.0 (default 1.0 - fully antialiased) 
    'polygon-gamma': float,

    # 0.0 - 1.0 (default 1.0)
    'polygon-opacity': float,

    # metawriter support
    'polygon-meta-output': str,

    'polygon-meta-writer': str,

    #--------------- line symbolizer

    # CSS colour (default "black")
    'line-color': color,

    # 0.0 - n (default 1.0)
    'line-width': float,

    # 0.0 - 1.0 (default 1.0)
    'line-opacity': float,

    # miter, round, bevel (default miter)
    'line-join': ('miter', 'round', 'bevel'),

    # round, butt, square (default butt)
    'line-cap': ('butt', 'round', 'square'),

    # d0,d1, ... (default none)
    'line-dasharray': numbers, # Number(s)

    # metawriter support
    'line-meta-output': str,

    'line-meta-writer': str,

    #--------------- line symbolizer for outlines

    # CSS colour (default "black")
    'outline-color': color,

    # 0.0 - n (default 1.0)
    'outline-width': float,

    # 0.0 - 1.0 (default 1.0)
    'outline-opacity': float,

    # miter, round, bevel (default miter)
    'outline-join': ('miter', 'round', 'bevel'),

    # round, butt, square (default butt)
    'outline-cap': ('butt', 'round', 'square'),

    # d0,d1, ... (default none)
    'outline-dasharray': numbers, # Number(s)

    # metawriter support
    'outline-meta-output': str,

    'outline-meta-writer': str,

    #--------------- line symbolizer for inlines

    # CSS colour (default "black")
    'inline-color': color,

    # 0.0 - n (default 1.0)
    'inline-width': float,

    # 0.0 - 1.0 (default 1.0)
    'inline-opacity': float,

    # miter, round, bevel (default miter)
    'inline-join': ('miter', 'round', 'bevel'),

    # round, butt, square (default butt)
    'inline-cap': ('butt', 'round', 'square'),

    # d0,d1, ... (default none)
    'inline-dasharray': numbers, # Number(s)

    # metawriter support
    'inline-meta-output': str,

    'inline-meta-writer': str,

    #--------------- text symbolizer

    'text-anchor-dx':int,
    'text-anchor-dy':int,
    'text-align': ('left','middle','right',),
    'text-vertical-align': ('top','middle','bottom',),
    'text-justify-align': ('left','middle','right',),
    'text-transform': ('uppercase','lowercase',),

    # Font name
    'text-face-name': strings,

    # Font size
    'text-size': int,

    # ?
    'text-ratio': None, # ?

    # length before wrapping long names
    'text-wrap-width': int,

    # space between repeated labels
    'text-spacing': int,

    # Horizontal spacing between characters (in pixels).
    'text-character-spacing': int,

    # Vertical spacing between lines of multiline labels (in pixels)
    'text-line-spacing': int,

    # allow labels to be moved from their point by some distance
    'text-label-position-tolerance': int,

    # Maximum angle (in degrees) between two consecutive characters in a label allowed (to stop placing labels around sharp corners)
    'text-max-char-angle-delta': int,

    # Color of the fill ie #FFFFFF
    'text-fill': color,

    # Color of the halo
    'text-halo-fill': color,

    # Radius of the halo in whole pixels, fractional pixels are not accepted
    'text-halo-radius': int,

    # displace label by fixed amount on either axis.
    'text-dx': int,
    'text-dy': int,

    # Boolean to avoid labeling near intersection edges.
    'text-avoid-edges': boolean,

    # Minimum distance between repeated labels such as street names or shield symbols
    'text-min-distance': int,

    # Allow labels to overlap other labels
    'text-allow-overlap': boolean,

    # "line" to label along lines instead of by point
    'text-placement': ('point', 'line'),

    # metawriter support
    'text-meta-output': str,

    'text-meta-writer': str,

    #--------------- point symbolizer

    # path to image file
    'point-file': uri, # none

    # px (default 4), generally omit this and let PIL handle it
    'point-width': int,
    'point-height': int,

    # image type: png or tiff, omitted thanks to PIL
    'point-type': None,

    # true/false
    'point-allow-overlap': boolean,

    # metawriter support
    'point-meta-output': str,

    'point-meta-writer': str,

    #--------------- raster symbolizer

    # raster transparency
    # 0.0 - 1.0 (default 1.0)
    'raster-opacity': float,
    
    # Compositing/Merging effects with image below raster level
    # default normal
    'raster-mode': ('normal','grain_merge', 'grain_merge2',
                    'multiply', 'multiply2', 'divide', 'divide2',
                    'screen', 'hard_light'),
    
    # resampling method
    'raster-scaling': ('fast', 'bilinear', 'bilinear8',),
        
    #--------------- polygon pattern symbolizer

    # path to image file (default none)
    'polygon-pattern-file': uri,

    # px (default 4), generally omit this and let PIL handle it
    'polygon-pattern-width': int,
    'polygon-pattern-height': int,

    # image type: png or tiff, omitted thanks to PIL
    'polygon-pattern-type': None,

    # metawriter support
    'polygon-pattern-meta-output': str,

    'polygon-pattern-meta-writer': str,

    #--------------- line pattern symbolizer

    # path to image file (default none)
    'line-pattern-file': uri,

    # px (default 4), generally omit this and let PIL handle it
    'line-pattern-width': int,
    'line-pattern-height': int,

    # image type: png or tiff, omitted thanks to PIL
    'line-pattern-type': None,

    # metawriter support
    'line-pattern-meta-output': str,

    'line-pattern-meta-writer': str,

    #--------------- shield symbolizer

    # 
    'shield-name': None, # (use selector for this)

    # 
    'shield-face-name': strings,

    # 
    'shield-size': int,

    # 
    'shield-fill': color,

    # Minimum distance between repeated labels such as street names or shield symbols
    'shield-min-distance': int,

    # Spacing between repeated labels such as street names or shield symbols
    'shield-spacing': int,

    # Horizontal spacing between characters (in pixels).
    'shield-character-spacing': int,
    
    # Vertical spacing between lines of multiline shields (in pixels)
    'shield-line-spacing': int,

    # Text offset in pixels from image center
    'shield-text-dx': int,
    'shield-text-dy': int,

    # path to image file (default none)
    'shield-file': uri,

    # px (default 4), generally omit this and let PIL handle it
    'shield-width': int,
    'shield-height': int,

    # image type: png or tiff, omitted thanks to PIL
    'shield-type': None,

    # metawriter support
    'shield-meta-output': str,

    'shield-meta-writer': str,
}

class Declaration:
    """ Bundle with a selector, single property and value.
    """
    def __init__(self, selector, property, value, sort_key):
        self.selector = selector
        self.property = property
        self.value = value
        self.sort_key = sort_key

    def __repr__(self):
        return u'%(selector)s { %(property)s: %(value)s }' % self.__dict__
    
    def scaleBy(self, scale):
        self.selector = self.selector.scaledBy(scale)
        
        if not self.property.name.endswith('-opacity'):
            self.value = self.value.scaledBy(scale)

class Selector:
    """ Represents a complete selector with elements and attribute checks.
    """
    def __init__(self, *elements):
        self.elements = elements[:]

    def addElement(self, element):
        self.elements = tuple(list(self.elements) + [element])
    
    def convertZoomTests(self, is_merc):
        """ Modify the tests on this selector to use mapnik-friendly
            scale-denominator instead of shorthand zoom.
        """
        #
        # Midpoint values for spherical mercator scale denominators at a range
        # of zoom levels, based on 96dpi values from Microsoft documentation.
        # http://msdn.microsoft.com/en-us/library/bb259689.aspx
        #
        zooms = {
             0: (418365887, 836731773),
             1: (209182943, 418365886),
             2: (104591472, 209182943),
             3: (52295736, 104591472),
             4: (26147868, 52295736),
             5: (13073934, 26147868),
             6: (6536967, 13073934),
             7: (3268484, 6536967),
             8: (1634242, 3268484),
             9: (817121, 1634242),
            10: (408561, 817121),
            11: (204280, 408561),
            12: (102140, 204280),
            13: (51070, 102140),
            14: (25535, 51070),
            15: (12768, 25535),
            16: (6384, 12768),
            17: (3192, 6384),
            18: (1596, 3192),
            19: (798, 1596),
            20: (399, 798),
            21: (200, 399),
            22: (100, 200),
           }
        
        for test in self.elements[0].tests:
            if test.property == 'zoom':
                if not is_merc:
                    # TODO - should we warn instead that values may not be appropriate?
                    raise NotImplementedError('Map srs is not web mercator, so zoom level shorthand cannot be propertly converted to Min/Max scaledenominators')

                test.property = 'scale-denominator'

                if test.op == '=':
                    # zoom level equality implies two tests, so we add one and modify one
                    self.elements[0].addTest(SelectorAttributeTest('scale-denominator', '<', max(zooms[test.value])))
                    test.op, test.value = '>=', min(zooms[test.value])

                elif test.op == '<':
                    test.op, test.value = '>=', max(zooms[test.value])
                elif test.op == '<=':
                    test.op, test.value = '>=', min(zooms[test.value])
                elif test.op == '>=':
                    test.op, test.value = '<', max(zooms[test.value])
                elif test.op == '>':
                    test.op, test.value = '<', min(zooms[test.value])


    def specificity(self):
        """ Loosely based on http://www.w3.org/TR/REC-CSS2/cascade.html#specificity
        """
        ids = sum(a.countIDs() for a in self.elements)
        non_ids = sum((a.countNames() - a.countIDs()) for a in self.elements)
        tests = sum(len(a.tests) for a in self.elements)
        
        return (ids, non_ids, tests)

    def matches(self, tag, id, classes):
        """ Given an id and a list of classes, return True if this selector would match.
        """
        element = self.elements[0]
        unmatched_ids = [name[1:] for name in element.names if name.startswith('#')]
        unmatched_classes = [name[1:] for name in element.names if name.startswith('.')]
        unmatched_tags = [name for name in element.names if name is not '*' and not name.startswith('#') and not name.startswith('.')]
        
        if tag and tag in unmatched_tags:
            unmatched_tags.remove(tag)

        if id and id in unmatched_ids:
            unmatched_ids.remove(id)

        for class_ in classes:
            if class_ in unmatched_classes:
                unmatched_classes.remove(class_)
        
        if unmatched_tags or unmatched_ids or unmatched_classes:
            return False

        else:
            return True
    
    def isRanged(self):
        """
        """
        return bool(self.rangeTests())
    
    def rangeTests(self):
        """
        """
        return [test for test in self.allTests() if test.isRanged()]
    
    def isMapScaled(self):
        """
        """
        return bool(self.mapScaleTests())
    
    def mapScaleTests(self):
        """
        """
        return [test for test in self.allTests() if test.isMapScaled()]
    
    def allTests(self):
        """
        """
        tests = []
        
        for test in self.elements[0].tests:
            tests.append(test)

        return tests
    
    def inRange(self, value):
        """
        """
        for test in self.rangeTests():
            if not test.inRange(value):
                return False

        return True

    def scaledBy(self, scale):
        """ Return a new Selector with scale denominators scaled by a number.
        """
        scaled = deepcopy(self)
    
        for test in scaled.elements[0].tests:
            if type(test.value) in (int, float):
                if test.property == 'scale-denominator':
                    test.value /= scale
                elif test.property == 'zoom':
                    test.value += log(scale)/log(2)
        
        return scaled
    
    def __repr__(self):
        return u' '.join(repr(a) for a in self.elements)

class SelectorElement:
    """ One element in selector, with names and tests.
    """
    def __init__(self, names=None, tests=None):
        if names:
            self.names = names
        else:
            self.names = []

        if tests:
            self.tests = tests
        else:
            self.tests = []

    def addName(self, name):
        self.names.append(str(name))
    
    def addTest(self, test):
        self.tests.append(test)

    def countTests(self):
        return len(self.tests)
    
    def countIDs(self):
        return len([n for n in self.names if n.startswith('#')])
    
    def countNames(self):
        return len(self.names)
    
    def countClasses(self):
        return len([n for n in self.names if n.startswith('.')])
    
    def __repr__(self):
        return u''.join(self.names) + u''.join(repr(t) for t in self.tests)

class ConcatenatedElement (SelectorElement):
    """
    """
    def __repr__(self):
        return '&' + SelectorElement.__repr__(self)

class SelectorAttributeTest:
    """ Attribute test for a Selector, i.e. the part that looks like "[foo=bar]"
    """
    def __init__(self, property, op, value):
        assert op in ('<', '<=', '=', '!=', '>=', '>')
        self.op = op
        self.property = str(property)
        self.value = value

    def __repr__(self):
        return u'[%(property)s%(op)s%(value)s]' % self.__dict__

    def __cmp__(self, other):
        """
        """
        return cmp(unicode(self), unicode(other))

    def isSimple(self):
        """
        """
        return self.op in ('=', '!=') and not self.isRanged()
    
    def inverse(self):
        """
        
            TODO: define this for non-simple tests.
        """
        assert self.isSimple(), 'inverse() is only defined for simple tests'
        
        if self.op == '=':
            return SelectorAttributeTest(self.property, '!=', self.value)
        
        elif self.op == '!=':
            return SelectorAttributeTest(self.property, '=', self.value)
    
    def isNumeric(self):
        """
        """
        return type(self.value) in (int, float)
    
    def isRanged(self):
        """
        """
        return self.op in ('<', '<=', '>=', '>')
    
    def isMapScaled(self):
        """
        """
        return self.property == 'scale-denominator'
    
    def inRange(self, scale_denominator):
        """
        """
        if not self.isRanged():
            # always in range
            return True

        elif self.op == '>' and scale_denominator > self.value:
            return True

        elif self.op == '>=' and scale_denominator >= self.value:
            return True

        elif self.op == '=' and scale_denominator == self.value:
            return True

        elif self.op == '<=' and scale_denominator <= self.value:
            return True

        elif self.op == '<' and scale_denominator < self.value:
            return True

        return False

    def isCompatible(self, tests):
        """ Given a collection of tests, return false if this test contradicts any of them.
        """
        # print '?', self, tests
        
        for test in tests:
            if self.property == test.property:
                if self.op == '=':
                    if test.op == '=' and self.value != test.value:
                        return False
    
                    if test.op == '!=' and self.value == test.value:
                        return False
    
                    if test.op == '<' and self.value >= test.value:
                        return False
                
                    if test.op == '>' and self.value <= test.value:
                        return False
                
                    if test.op == '<=' and self.value > test.value:
                        return False
                
                    if test.op == '>=' and self.value < test.value:
                        return False
            
                if self.op == '!=':
                    if test.op == '=' and self.value == test.value:
                        return False
    
                    if test.op == '!=':
                        pass
    
                    if test.op == '<':
                        pass
                
                    if test.op == '>':
                        pass
                
                    if test.op == '<=' and self.value == test.value:
                        return False
                
                    if test.op == '>=' and self.value == test.value:
                        return False
            
                if self.op == '<':
                    if test.op == '=' and self.value <= test.value:
                        return False
    
                    if test.op == '!=':
                        return False
    
                    if test.op == '<':
                        pass
                
                    if test.op == '>' and self.value <= test.value:
                        return False
                
                    if test.op == '<=':
                        pass
                
                    if test.op == '>=' and self.value <= test.value:
                        return False
            
                if self.op == '>':
                    if test.op == '=' and self.value >= test.value:
                        return False
    
                    if test.op == '!=':
                        return False
    
                    if test.op == '<' and self.value >= test.value:
                        return False
                
                    if test.op == '>':
                        pass
                
                    if test.op == '<=' and self.value >= test.value:
                        return False
                
                    if test.op == '>=':
                        pass
            
                if self.op == '<=':
                    if test.op == '=' and self.value < test.value:
                        return False
    
                    if test.op == '!=' and self.value == test.value:
                        return False
    
                    if test.op == '<':
                        pass
                
                    if test.op == '>' and self.value <= test.value:
                        return False
                
                    if test.op == '<=':
                        pass
                
                    if test.op == '>=' and self.value < test.value:
                        return False
            
                if self.op == '>=':
                    if test.op == '=' and self.value > test.value:
                        return False
    
                    if test.op == '!=' and self.value == test.value:
                        return False
    
                    if test.op == '<' and self.value >= test.value:
                        return False
                
                    if test.op == '>':
                        pass
                
                    if test.op == '<=' and self.value > test.value:
                        return False
                
                    if test.op == '>=':
                        pass

        return True
    
    def rangeOpEdge(self):
        ops = {'<': operator.lt, '<=': operator.le, '=': operator.eq, '>=': operator.ge, '>': operator.gt}
        return ops[self.op], self.value

        return None

class Property:
    """ A style property.
    """
    def __init__(self, name):
        assert name in properties
    
        self.name = name

    def group(self):
        return self.name.split('-')[0]
    
    def __repr__(self):
        return self.name

    def __str__(self):
        return repr(self)

class Value:
    """ A style value.
    """
    def __init__(self, value, important):
        self.value = value
        self.important = important

    def importance(self):
        return int(self.important)
    
    def scaledBy(self, scale):
        """ Return a new Value scaled by a given number for ints and floats.
        """
        scaled = deepcopy(self)
    
        if type(scaled.value) in (int, float):
            scaled.value *= scale
        elif isinstance(scaled.value, numbers):
            scaled.value.values = tuple(v * scale for v in scaled.value.values)

        return scaled
    
    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return str(self.value)

########NEW FILE########
__FILENAME__ = tests
""" Tests for Cascadenik.

Run as a module, like this:
    python -m cascadenik.tests
"""
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import urllib
import urlparse
import os.path
import unittest
import tempfile
import xml.etree.ElementTree

from .style import color, numbers, strings, boolean
from .style import Property, Selector, SelectorElement, SelectorAttributeTest
from .parse import ParseException, postprocess_value, stylesheet_declarations
from .compile import tests_filter_combinations, Filter, selectors_tests
from .compile import filtered_property_declarations, is_applicable_selector
from .compile import get_polygon_rules, get_line_rules, get_text_rule_groups, get_shield_rule_groups
from .compile import get_point_rules, get_polygon_pattern_rules, get_line_pattern_rules
from .compile import test2str, compile
from .compile import Directories
from .sources import DataSources
from . import mapnik, MAPNIK_VERSION
from . import output
    
class ParseTests(unittest.TestCase):
    
    def testBadSelector1(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Too Many Things { }')

    def testBadSelector2(self):
        self.assertRaises(ParseException, stylesheet_declarations, '{ }')

    def testBadSelector3(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Illegal { }')

    def testBadSelector4(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer foo[this=that] { }')

    def testBadSelector5(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[this>that] foo { }')

    def testBadSelector6(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer foo#bar { }')

    def testBadSelector7(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer foo.bar { }')

    def testBadSelectorTest1(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[foo>] { }')

    def testBadSelectorTest2(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[foo><bar] { }')

    def testBadSelectorTest3(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[foo<<bar] { }')

    def testBadSelectorTest4(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[<bar] { }')

    def testBadSelectorTest5(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer[<<bar] { }')

    def testBadProperty1(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { unknown-property: none; }')

    def testBadProperty2(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { extra thing: none; }')

    def testBadProperty3(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { "not an ident": none; }')

    def testBadNesting1(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { .weird { line-width: 1; } }')

    def testBadNesting2(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { #weird { line-width: 1; } }')

    def testBadNesting3(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { [foo=bar] { line-width: 1; } }')

    def testBadNesting4(self):
        self.assertRaises(ParseException, stylesheet_declarations, 'Layer { &More { line-width: 1; } }')

    def testRulesets1(self):
        self.assertEqual(1, len(stylesheet_declarations('/* empty stylesheet */')))

    def testDeclarations2(self):
        self.assertEqual(2, len(stylesheet_declarations('Layer { line-width: 1; }')))

    def testDeclarations3(self):
        self.assertEqual(3, len(stylesheet_declarations('Layer { line-width: 1; } Layer { line-width: 1; }')))

    def testDeclarations4(self):
        self.assertEqual(4, len(stylesheet_declarations('Layer { line-width: 1; } /* something */ Layer { line-width: 1; } /* extra */ Layer { line-width: 1; }')))

    def testDeclarations5(self):
        self.assertEqual(2, len(stylesheet_declarations('Map { line-width: 1; }')))

class SelectorTests(unittest.TestCase):
    
    def testSpecificity1(self):
        self.assertEqual((0, 1, 0), Selector(SelectorElement(['Layer'])).specificity())
    
    def testSpecificity2(self):
        self.assertEqual((0, 2, 0), Selector(SelectorElement(['Layer']), SelectorElement(['name'])).specificity())
    
    def testSpecificity3(self):
        self.assertEqual((0, 2, 0), Selector(SelectorElement(['Layer', '.class'])).specificity())
    
    def testSpecificity4(self):
        self.assertEqual((0, 3, 0), Selector(SelectorElement(['Layer', '.class']), SelectorElement(['name'])).specificity())
    
    def testSpecificity5(self):
        self.assertEqual((1, 2, 0), Selector(SelectorElement(['Layer', '#id']), SelectorElement(['name'])).specificity())
    
    def testSpecificity6(self):
        self.assertEqual((1, 0, 0), Selector(SelectorElement(['#id'])).specificity())
    
    def testSpecificity7(self):
        self.assertEqual((1, 0, 1), Selector(SelectorElement(['#id'], [SelectorAttributeTest('a', '>', 'b')])).specificity())
    
    def testSpecificity8(self):
        self.assertEqual((1, 0, 2), Selector(SelectorElement(['#id'], [SelectorAttributeTest('a', '>', 'b'), SelectorAttributeTest('a', '<', 'b')])).specificity())

    def testSpecificity9(self):
        self.assertEqual((1, 0, 2), Selector(SelectorElement(['#id'], [SelectorAttributeTest('a', '>', 100), SelectorAttributeTest('a', '<', 'b')])).specificity())

    def testMatch1(self):
        assert Selector(SelectorElement(['Layer'])).matches('Layer', 'foo', [])

    def testMatch2(self):
        assert Selector(SelectorElement(['#foo'])).matches('Layer', 'foo', [])

    def testMatch3(self):
        assert not Selector(SelectorElement(['#foo'])).matches('Layer', 'bar', [])

    def testMatch4(self):
        assert Selector(SelectorElement(['.bar'])).matches('Layer', None, ['bar'])

    def testMatch5(self):
        assert Selector(SelectorElement(['.bar'])).matches('Layer', None, ['bar', 'baz'])

    def testMatch6(self):
        assert Selector(SelectorElement(['.bar', '.baz'])).matches('Layer', None, ['bar', 'baz'])

    def testMatch7(self):
        assert not Selector(SelectorElement(['.bar', '.baz'])).matches('Layer', None, ['bar'])

    def testMatch8(self):
        assert not Selector(SelectorElement(['Layer'])).matches('Map', None, [])

    def testMatch9(self):
        assert not Selector(SelectorElement(['Map'])).matches('Layer', None, [])

    def testMatch10(self):
        assert Selector(SelectorElement(['*'])).matches('Layer', None, [])

    def testMatch11(self):
        assert Selector(SelectorElement(['*'])).matches('Map', None, [])

    def testRange1(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>', 100)]))
        assert selector.isRanged()
        assert not selector.inRange(99)
        assert not selector.inRange(100)
        assert selector.inRange(1000)

    def testRange2(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>=', 100)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert not selector.inRange(99)
        assert selector.inRange(100)
        assert selector.inRange(1000)

    def testRange3(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '<', 100)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert selector.inRange(99)
        assert not selector.inRange(100)
        assert not selector.inRange(1000)

    def testRange4(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '<=', 100)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert selector.inRange(99)
        assert selector.inRange(100)
        assert not selector.inRange(1000)

    def testRange5(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('nonsense', '<=', 100)]))
        assert selector.isRanged()
        assert not selector.isMapScaled()
        assert selector.inRange(99)
        assert selector.inRange(100)
        assert not selector.inRange(1000)

    def testRange6(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>=', 100), SelectorAttributeTest('scale-denominator', '<', 1000)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert not selector.inRange(99)
        assert selector.inRange(100)
        assert not selector.inRange(1000)

    def testRange7(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '>', 100), SelectorAttributeTest('scale-denominator', '<=', 1000)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert not selector.inRange(99)
        assert not selector.inRange(100)
        assert selector.inRange(1000)

    def testRange8(self):
        selector = Selector(SelectorElement(['*'], [SelectorAttributeTest('scale-denominator', '<=', 100), SelectorAttributeTest('scale-denominator', '>=', 1000)]))
        assert selector.isRanged()
        assert selector.isMapScaled()
        assert not selector.inRange(99)
        assert not selector.inRange(100)
        assert not selector.inRange(1000)

class ValueTests(unittest.TestCase):

    def testBadValue1(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-opacity'), [], False, 0, 0)

    def testBadValue2(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-opacity'), [('IDENT', 'too'), ('IDENT', 'many')], False, 0, 0)

    def testBadValue3(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-opacity'), [('IDENT', 'non-number')], False, 0, 0)

    def testBadValue3b(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-gamma'), [('IDENT', 'non-number')], False, 0, 0)

    def testBadValue4(self):
        self.assertRaises(ParseException, postprocess_value, Property('text-face-name'), [('IDENT', 'non-string')], False, 0, 0)

    def testBadValue5(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-fill'), [('IDENT', 'non-hash')], False, 0, 0)

    def testBadValue6(self):
        self.assertRaises(ParseException, postprocess_value, Property('polygon-fill'), [('HASH', '#badcolor')], False, 0, 0)

    def testBadValue7(self):
        self.assertRaises(ParseException, postprocess_value, Property('point-file'), [('IDENT', 'non-URI')], False, 0, 0)

    def testBadValue8(self):
        self.assertRaises(ParseException, postprocess_value, Property('text-avoid-edges'), [('IDENT', 'bad-boolean')], False, 0, 0)

    def testBadValue9(self):
        self.assertRaises(ParseException, postprocess_value, Property('line-join'), [('STRING', 'not an IDENT')], False, 0, 0)

    def testBadValue10(self):
        self.assertRaises(ParseException, postprocess_value, Property('line-join'), [('IDENT', 'not-in-tuple')], False, 0, 0)

    def testBadValue11(self):
        self.assertRaises(ParseException, postprocess_value, Property('line-dasharray'), [('NUMBER', '1'), ('CHAR', ','), ('CHAR', ','), ('NUMBER', '3')], False, 0, 0)

    def testValue1(self):
        self.assertEqual(1.0, postprocess_value(Property('polygon-opacity'), [('NUMBER', '1.0')], False, 0, 0).value)

    def testValue1b(self):
        self.assertEqual(1.0, postprocess_value(Property('polygon-gamma'), [('NUMBER', '1.0')], False, 0, 0).value)

    def testValue2(self):
        self.assertEqual(10, postprocess_value(Property('line-width'), [('NUMBER', '10')], False, 0, 0).value)

    def testValue2b(self):
        self.assertEqual(-10, postprocess_value(Property('text-dx'), [('CHAR', '-'), ('NUMBER', '10')], False, 0, 0).value)

    def testValue3(self):
        self.assertEqual('DejaVu', str(postprocess_value(Property('text-face-name'), [('STRING', '"DejaVu"')], False, 0, 0)))

    def testValue4(self):
        self.assertEqual('#ff9900', str(postprocess_value(Property('map-bgcolor'), [('HASH', '#ff9900')], False, 0, 0)))

    def testValue5(self):
        self.assertEqual('#ff9900', str(postprocess_value(Property('map-bgcolor'), [('HASH', '#f90')], False, 0, 0)))

    def testValue6(self):
        self.assertEqual('http://example.com', str(postprocess_value(Property('point-file'), [('URI', 'url("http://example.com")')], False, 0, 0)))

    def testValue7(self):
        self.assertEqual('true', str(postprocess_value(Property('text-avoid-edges'), [('IDENT', 'true')], False, 0, 0)))

    def testValue8(self):
        self.assertEqual('false', str(postprocess_value(Property('text-avoid-edges'), [('IDENT', 'false')], False, 0, 0)))

    def testValue9(self):
        self.assertEqual('bevel', str(postprocess_value(Property('line-join'), [('IDENT', 'bevel')], False, 0, 0)))

    def testValue10(self):
        self.assertEqual('1,2,3', str(postprocess_value(Property('line-dasharray'), [('NUMBER', '1'), ('CHAR', ','), ('NUMBER', '2'), ('CHAR', ','), ('NUMBER', '3')], False, 0, 0)))

    def testValue11(self):
        self.assertEqual('1,2.0,3', str(postprocess_value(Property('line-dasharray'), [('NUMBER', '1'), ('CHAR', ','), ('S', ' '), ('NUMBER', '2.0'), ('CHAR', ','), ('NUMBER', '3')], False, 0, 0)))

    def testValue12(self):
        self.assertEqual(12, postprocess_value(Property('text-character-spacing'), [('NUMBER', '12')], False, 0, 0).value)

    def testValue13(self):
        self.assertEqual(14, postprocess_value(Property('shield-character-spacing'), [('NUMBER', '14')], False, 0, 0).value)

    def testValue14(self):
        self.assertEqual(12, postprocess_value(Property('text-line-spacing'), [('NUMBER', '12')], False, 0, 0).value)

    def testValue15(self):
        self.assertEqual(14, postprocess_value(Property('shield-line-spacing'), [('NUMBER', '14')], False, 0, 0).value)
    
class CascadeTests(unittest.TestCase):

    def testCascade1(self):
        s = """
            Layer
            {
                text-dx: -10;
                text-dy: -10;
            }
        """
        declarations = stylesheet_declarations(s)
        
        # ditch the boring display: map declaration
        declarations.pop(0)
        
        self.assertEqual(2, len(declarations))
        self.assertEqual(1, len(declarations[0].selector.elements))
        self.assertEqual('text-dx', declarations[0].property.name)
        self.assertEqual('text-dy', declarations[1].property.name)
        self.assertEqual(-10, declarations[1].value.value)

    def testCascade2(self):
        s = """
            * { text-fill: #ff9900 !important; }

            Layer#foo.foo[baz>10] bar,
            *
            {
                polygon-fill: #f90;
                text-face-name: /* boo yah */ "Helvetica Bold";
                text-size: 10;
                polygon-pattern-file: url('http://example.com');
                line-cap: square;
                text-allow-overlap: false;
                text-dx: -10;
                polygon-gamma: /* value between 0 and 1 */ .65;
                text-character-spacing: 4;
            }
        """
        declarations = stylesheet_declarations(s)
        
        # ditch the boring display: map declaration
        declarations.pop(0)
        
        # first declaration is the unimportant polygon-fill: #f90
        self.assertEqual(1, len(declarations[0].selector.elements))

        # last declaration is the !important one, text-fill: #ff9900
        self.assertEqual(1, len(declarations[-1].selector.elements))

        # second-last declaration is the highly-specific one, text-character-spacing
        self.assertEqual(2, len(declarations[-2].selector.elements))
        
        self.assertEqual(19, len(declarations))

        self.assertEqual('*', str(declarations[0].selector))
        self.assertEqual('polygon-fill', declarations[0].property.name)
        self.assertEqual('#ff9900', str(declarations[0].value))

        self.assertEqual('*', str(declarations[1].selector))
        self.assertEqual('text-face-name', declarations[1].property.name)
        self.assertEqual('Helvetica Bold', str(declarations[1].value))

        self.assertEqual('*', str(declarations[2].selector))
        self.assertEqual('text-size', declarations[2].property.name)
        self.assertEqual('10', str(declarations[2].value))

        self.assertEqual('*', str(declarations[3].selector))
        self.assertEqual('polygon-pattern-file', declarations[3].property.name)
        self.assertEqual('http://example.com', str(declarations[3].value))

        self.assertEqual('*', str(declarations[4].selector))
        self.assertEqual('line-cap', declarations[4].property.name)
        self.assertEqual('square', str(declarations[4].value))

        self.assertEqual('*', str(declarations[5].selector))
        self.assertEqual('text-allow-overlap', declarations[5].property.name)
        self.assertEqual('false', str(declarations[5].value))

        self.assertEqual('*', str(declarations[6].selector))
        self.assertEqual('text-dx', declarations[6].property.name)
        self.assertEqual('-10', str(declarations[6].value))

        self.assertEqual('*', str(declarations[7].selector))
        self.assertEqual('polygon-gamma', declarations[7].property.name)
        self.assertEqual('0.65', str(declarations[7].value))
        
        self.assertEqual('*', str(declarations[8].selector))
        self.assertEqual('text-character-spacing', declarations[8].property.name)
        self.assertEqual('4', str(declarations[8].value))
        
        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[9].selector))
        self.assertEqual('polygon-fill', declarations[9].property.name)
        self.assertEqual('#ff9900', str(declarations[9].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[10].selector))
        self.assertEqual('text-face-name', declarations[10].property.name)
        self.assertEqual('Helvetica Bold', str(declarations[10].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[11].selector))
        self.assertEqual('text-size', declarations[11].property.name)
        self.assertEqual('10', str(declarations[11].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[12].selector))
        self.assertEqual('polygon-pattern-file', declarations[12].property.name)
        self.assertEqual('http://example.com', str(declarations[12].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[13].selector))
        self.assertEqual('line-cap', declarations[13].property.name)
        self.assertEqual('square', str(declarations[13].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[14].selector))
        self.assertEqual('text-allow-overlap', declarations[14].property.name)
        self.assertEqual('false', str(declarations[14].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[15].selector))
        self.assertEqual('text-dx', declarations[15].property.name)
        self.assertEqual('-10', str(declarations[15].value))

        self.assertEqual('Layer#foo.foo[baz>10] bar', str(declarations[16].selector))
        self.assertEqual('polygon-gamma', declarations[16].property.name)
        self.assertEqual('0.65', str(declarations[16].value))

        self.assertEqual('*', str(declarations[18].selector))
        self.assertEqual('text-fill', declarations[18].property.name)
        self.assertEqual('#ff9900', str(declarations[18].value))

class SelectorParseTests(unittest.TestCase):

    def testFilters1(self):
        s = """
            Layer[landuse=military] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters2(self):
        s = """
            Layer[landuse='military'] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters3(self):
        s = """
            Layer[landuse="military"] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters4(self):
        s = """
            Layer[foo=1] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = 1", test2str(filters[1].tests[0]))

    def testFilters5(self):
        s = """
            Layer[foo=1.1] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = 1.1", test2str(filters[1].tests[0]))

    def testFilters6(self):
        s = """
            Layer[foo="1.1"] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = '1.1'", test2str(filters[1].tests[0]))

    def testFilters7(self):
        s = """
            Layer[landuse= "military"] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[landuse] = 'military'", test2str(filters[1].tests[0]))

    def testFilters8(self):
        s = """
            Layer[foo =1] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = 1", test2str(filters[1].tests[0]))

    def testFilters9(self):
        s = """
            Layer[foo = "1.1"] { polygon-fill: #000; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual("[foo] = '1.1'", test2str(filters[1].tests[0]))

    def testFilters10(self):
        # Unicode is fine in filter values
        # Not so much in properties
        s = u'''
        Layer[name="Grüner Strich"] { polygon-fill: #000; }
        '''
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(u"[name] = 'Grüner Strich'", test2str(filters[1].tests[0]))
        self.assert_(isinstance(filters[1].tests[0].value, unicode))
        self.assert_(isinstance(filters[1].tests[0].property, str))

    def testUnicode1(self):
        # Unicode is bad in property values
        s = u'''
        Layer CODE {
            text-face-name: "DejaVu Sans Book";
            text-size: 12; 
            text-fill: #005;
            text-placement: line;
        }
        '''
        declarations = stylesheet_declarations(s, is_merc=True)
        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(str, type(text_rule_groups.keys()[0]))
        self.assert_(isinstance(text_rule_groups['CODE'][0].symbolizers[0].face_name, strings))
        self.assertEqual(str, type(text_rule_groups['CODE'][0].symbolizers[0].label_placement))

class FilterCombinationTests(unittest.TestCase):

    def testFilters1(self):
        s = """
            Layer[landuse=military]     { polygon-fill: #000; }
            Layer[landuse=civilian]     { polygon-fill: #001; }
            Layer[landuse=agriculture]  { polygon-fill: #010; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 4)
        self.assertEqual(str(sorted(filters)), '[[landuse!=agriculture][landuse!=civilian][landuse!=military], [landuse=agriculture], [landuse=civilian], [landuse=military]]')

    def testFilters2(self):
        s = """
            Layer[landuse=military]     { polygon-fill: #000; }
            Layer[landuse=civilian]     { polygon-fill: #001; }
            Layer[landuse=agriculture]  { polygon-fill: #010; }
            Layer[horse=yes]    { polygon-fill: #011; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 8)
        self.assertEqual(str(sorted(filters)), '[[horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military], [horse!=yes][landuse=agriculture], [horse!=yes][landuse=civilian], [horse!=yes][landuse=military], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military], [horse=yes][landuse=agriculture], [horse=yes][landuse=civilian], [horse=yes][landuse=military]]')

    def testFilters3(self):
        s = """
            Layer[landuse=military]     { polygon-fill: #000; }
            Layer[landuse=civilian]     { polygon-fill: #001; }
            Layer[landuse=agriculture]  { polygon-fill: #010; }
            Layer[horse=yes]    { polygon-fill: #011; }
            Layer[horse=no]     { polygon-fill: #100; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 12)
        self.assertEqual(str(sorted(filters)), '[[horse!=no][horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military], [horse!=no][horse!=yes][landuse=agriculture], [horse!=no][horse!=yes][landuse=civilian], [horse!=no][horse!=yes][landuse=military], [horse=no][landuse!=agriculture][landuse!=civilian][landuse!=military], [horse=no][landuse=agriculture], [horse=no][landuse=civilian], [horse=no][landuse=military], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military], [horse=yes][landuse=agriculture], [horse=yes][landuse=civilian], [horse=yes][landuse=military]]')

    def testFilters4(self):
        s = """
            Layer[landuse=military]     { polygon-fill: #000; }
            Layer[landuse=civilian]     { polygon-fill: #001; }
            Layer[landuse=agriculture]  { polygon-fill: #010; }
            Layer[horse=yes]    { polygon-fill: #011; }
            Layer[leisure=park] { polygon-fill: #100; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 16)
        self.assertEqual(str(sorted(filters)), '[[horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure!=park], [horse!=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure=park], [horse!=yes][landuse=agriculture][leisure!=park], [horse!=yes][landuse=agriculture][leisure=park], [horse!=yes][landuse=civilian][leisure!=park], [horse!=yes][landuse=civilian][leisure=park], [horse!=yes][landuse=military][leisure!=park], [horse!=yes][landuse=military][leisure=park], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure!=park], [horse=yes][landuse!=agriculture][landuse!=civilian][landuse!=military][leisure=park], [horse=yes][landuse=agriculture][leisure!=park], [horse=yes][landuse=agriculture][leisure=park], [horse=yes][landuse=civilian][leisure!=park], [horse=yes][landuse=civilian][leisure=park], [horse=yes][landuse=military][leisure!=park], [horse=yes][landuse=military][leisure=park]]')

class NestedRuleTests(unittest.TestCase):

    def testCompile1(self):
        s = """
            Layer
            {
                &.red { polygon-fill: #f00 }
                &.blue { polygon-fill: #00f }
            }
        """
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 3)
        
        self.assertEqual(len(declarations[1].selector.elements), 1)
        self.assertEqual(len(declarations[2].selector.elements), 1)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], 'Layer')
        self.assertEqual(declarations[1].selector.elements[0].names[1], '.red')
        self.assertEqual((declarations[1].property.name, str(declarations[1].value.value)), ('polygon-fill', '#ff0000'))
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], 'Layer')
        self.assertEqual(declarations[2].selector.elements[0].names[1], '.blue')
        self.assertEqual((declarations[2].property.name, str(declarations[2].value.value)), ('polygon-fill', '#0000ff'))

    def testCompile2(self):
        s = """
            .north, .south
            {
                &.east, &.west
                {
                    polygon-fill: #f90
                }
            }
        """
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 5)
        
        self.assertEqual(len(declarations[1].selector.elements), 1)
        self.assertEqual(len(declarations[2].selector.elements), 1)
        self.assertEqual(len(declarations[3].selector.elements), 1)
        self.assertEqual(len(declarations[4].selector.elements), 1)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '.north')
        self.assertEqual(declarations[1].selector.elements[0].names[1], '.east')
        self.assertEqual((declarations[1].property.name, str(declarations[1].value.value)), ('polygon-fill', '#ff9900'))
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], '.north')
        self.assertEqual(declarations[2].selector.elements[0].names[1], '.west')
        self.assertEqual((declarations[2].property.name, str(declarations[2].value.value)), ('polygon-fill', '#ff9900'))
        
        self.assertEqual(declarations[3].selector.elements[0].names[0], '.south')
        self.assertEqual(declarations[3].selector.elements[0].names[1], '.east')
        self.assertEqual((declarations[3].property.name, str(declarations[3].value.value)), ('polygon-fill', '#ff9900'))
        
        self.assertEqual(declarations[4].selector.elements[0].names[0], '.south')
        self.assertEqual(declarations[4].selector.elements[0].names[1], '.west')
        self.assertEqual((declarations[4].property.name, str(declarations[4].value.value)), ('polygon-fill', '#ff9900'))

    def testCompile3(self):
        s = """
            .roads
            {
                line-color: #f90;
            
                &[kind=highway] { line-width: 3 }
                &[kind=major] { line-width: 2 }
                &[kind=minor] { line-width: 1 }
            }
        """
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 5)
        
        self.assertEqual(len(declarations[1].selector.elements), 1)
        self.assertEqual(len(declarations[2].selector.elements), 1)
        self.assertEqual(len(declarations[3].selector.elements), 1)
        self.assertEqual(len(declarations[4].selector.elements), 1)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '.roads')
        self.assertEqual((declarations[1].property.name, str(declarations[1].value.value)), ('line-color', '#ff9900'))
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[2].selector.elements[0].tests[0]), '[kind=highway]')
        self.assertEqual((declarations[2].property.name, declarations[2].value.value), ('line-width', 3))
        
        self.assertEqual(declarations[3].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[3].selector.elements[0].tests[0]), '[kind=major]')
        self.assertEqual((declarations[3].property.name, declarations[3].value.value), ('line-width', 2))
        
        self.assertEqual(declarations[4].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[4].selector.elements[0].tests[0]), '[kind=minor]')
        self.assertEqual((declarations[4].property.name, declarations[4].value.value), ('line-width', 1))

    def testCompile4(self):
        s = """
            .roads
            {
                text-fill: #f90;
            
                &[kind=highway] name { text-size: 24 }
                &[kind=major] name { text-size: 18 }
                &[kind=minor] name { text-size: 12 }
            }
        """
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 5)
        
        self.assertEqual(len(declarations[1].selector.elements), 1)
        self.assertEqual(len(declarations[2].selector.elements), 2)
        self.assertEqual(len(declarations[3].selector.elements), 2)
        self.assertEqual(len(declarations[4].selector.elements), 2)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '.roads')
        self.assertEqual((declarations[1].property.name, str(declarations[1].value.value)), ('text-fill', '#ff9900'))
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[2].selector.elements[0].tests[0]), '[kind=highway]')
        self.assertEqual(declarations[2].selector.elements[1].names[0], 'name')
        self.assertEqual((declarations[2].property.name, declarations[2].value.value), ('text-size', 24))
        
        self.assertEqual(declarations[3].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[3].selector.elements[0].tests[0]), '[kind=major]')
        self.assertEqual(declarations[3].selector.elements[1].names[0], 'name')
        self.assertEqual((declarations[3].property.name, declarations[3].value.value), ('text-size', 18))
        
        self.assertEqual(declarations[4].selector.elements[0].names[0], '.roads')
        self.assertEqual(str(declarations[4].selector.elements[0].tests[0]), '[kind=minor]')
        self.assertEqual(declarations[4].selector.elements[1].names[0], 'name')
        self.assertEqual((declarations[4].property.name, declarations[4].value.value), ('text-size', 12))

    def testCompile5(self):
        s = """
            #roads
            {
                &[level=1]
                {
                    &[level=2]
                    {
                        &[level=3]
                        {
                            &.deep[level=4]
                            {
                                name
                                {
                                    text-size: 12;
                                }
                            }
                        }
                    }
                }
            }
        """
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 2)
        
        self.assertEqual(len(declarations[1].selector.elements), 2)
        self.assertEqual(len(declarations[1].selector.elements[0].names), 2)
        self.assertEqual(len(declarations[1].selector.elements[0].tests), 4)
        self.assertEqual(len(declarations[1].selector.elements[1].names), 1)
        self.assertEqual(len(declarations[1].selector.elements[1].tests), 0)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '#roads')
        self.assertEqual(declarations[1].selector.elements[0].names[1], '.deep')
        self.assertEqual(str(declarations[1].selector.elements[0].tests[0]), '[level=1]')
        self.assertEqual(str(declarations[1].selector.elements[0].tests[1]), '[level=2]')
        self.assertEqual(str(declarations[1].selector.elements[0].tests[2]), '[level=3]')
        self.assertEqual(str(declarations[1].selector.elements[0].tests[3]), '[level=4]')
        
        self.assertEqual(declarations[1].selector.elements[1].names[0], 'name')
        
        self.assertEqual((declarations[1].property.name, declarations[1].value.value), ('text-size', 12))

    def testCompile6(self):
        s = """
            #low[zoom<5],
            #high[zoom>=5]
            {
                polygon-fill: #fff;
            
                &[zoom=0] { polygon-fill: #000; }
                &[zoom=3] { polygon-fill: #333; }
                &[zoom=6] { polygon-fill: #666; }
                &[zoom=9] { polygon-fill: #999; }
            }
        """
        
        declarations = stylesheet_declarations(s, is_merc=True)
        
        self.assertEqual(len(declarations), 11)
        
        for index in (1, 3, 5, 7, 9):
            self.assertEqual(str(declarations[index].selector.elements[0])[:33], '#low[scale-denominator>=26147868]')
        
        for index in (2, 4, 6, 8, 10):
            self.assertEqual(str(declarations[index].selector.elements[0])[:33], '#high[scale-denominator<26147868]')
        
        for index in (1, 2):
            self.assertEqual(str(declarations[index].value.value), '#ffffff')
        
        for index in (3, 4):
            self.assertEqual(str(declarations[index].selector.elements[0])[33:], '[scale-denominator>=418365887][scale-denominator<836731773]')
            self.assertEqual(str(declarations[index].value.value), '#000000')
        
        for index in (5, 6):
            self.assertEqual(str(declarations[index].selector.elements[0])[33:], '[scale-denominator>=52295736][scale-denominator<104591472]')
            self.assertEqual(str(declarations[index].value.value), '#333333')
        
        for index in (7, 8):
            self.assertEqual(str(declarations[index].selector.elements[0])[33:], '[scale-denominator>=6536967][scale-denominator<13073934]')
            self.assertEqual(str(declarations[index].value.value), '#666666')
        
        for index in (9, 10):
            self.assertEqual(str(declarations[index].selector.elements[0])[33:], '[scale-denominator>=817121][scale-denominator<1634242]')
            self.assertEqual(str(declarations[index].value.value), '#999999')

class AtVariableTests(unittest.TestCase):

    def testCompile1(self):
        s = """
            @orange: #f90;
            @blue : #00c;
            
            .orange { polygon-fill: @orange }
            .blue { polygon-fill: @blue }
        """
        
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 3)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '.orange')
        self.assertEqual(str(declarations[1].value.value), '#ff9900')
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], '.blue')
        self.assertEqual(str(declarations[2].value.value), '#0000cc')

    def testCompile2(self):
        s = """
            @blue: #00c;
            .dk-blue { polygon-fill: @blue }
        
            @blue: #06f;
            .lt-blue { polygon-fill: @blue }
        """
        
        declarations = stylesheet_declarations(s)
        
        self.assertEqual(len(declarations), 3)
        
        self.assertEqual(declarations[1].selector.elements[0].names[0], '.dk-blue')
        self.assertEqual(str(declarations[1].value.value), '#0000cc')
        
        self.assertEqual(declarations[2].selector.elements[0].names[0], '.lt-blue')
        self.assertEqual(str(declarations[2].value.value), '#0066ff')

class SimpleRangeTests(unittest.TestCase):

    def testRanges1(self):
        s = """
            Layer[foo<1000] { polygon-fill: #000; }
            Layer[foo>1000] { polygon-fill: #001; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 3)
        self.assertEqual(str(sorted(filters)), '[[foo<1000], [foo=1000], [foo>1000]]')

    def testRanges2(self):
        s = """
            Layer[foo>1] { polygon-fill: #000; }
            Layer[foo<2] { polygon-fill: #001; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 3)
        self.assertEqual(str(sorted(filters)), '[[foo<2][foo>1], [foo<=1], [foo>=2]]')

    def testRanges3(self):
        s = """
            Layer[foo>1] { polygon-fill: #000; }
            Layer[foo<2] { polygon-fill: #001; }
            Layer[bar>4] { polygon-fill: #010; }
            Layer[bar<8] { polygon-fill: #011; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 9)
        self.assertEqual(str(sorted(filters)), '[[bar<8][bar>4][foo<2][foo>1], [bar<8][bar>4][foo<=1], [bar<8][bar>4][foo>=2], [bar<=4][foo<2][foo>1], [bar<=4][foo<=1], [bar<=4][foo>=2], [bar>=8][foo<2][foo>1], [bar>=8][foo<=1], [bar>=8][foo>=2]]')

    def testRanges4(self):
        s = """
            Layer[foo>1] { polygon-fill: #000; }
            Layer[foo<2] { polygon-fill: #001; }
            Layer[bar=this] { polygon-fill: #010; }
            Layer[bar=that] { polygon-fill: #011; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 9)
        self.assertEqual(str(sorted(filters)), '[[bar!=that][bar!=this][foo<2][foo>1], [bar!=that][bar!=this][foo<=1], [bar!=that][bar!=this][foo>=2], [bar=that][foo<2][foo>1], [bar=that][foo<=1], [bar=that][foo>=2], [bar=this][foo<2][foo>1], [bar=this][foo<=1], [bar=this][foo>=2]]')

    def testRanges5(self):
        s = """
            Layer[foo>1] { polygon-fill: #000; }
            Layer[foo<2] { polygon-fill: #001; }
            Layer[bar=this] { polygon-fill: #010; }
            Layer[bar=that] { polygon-fill: #011; }
            Layer[bar=blah] { polygon-fill: #100; }
        """
        selectors = [dec.selector for dec in stylesheet_declarations(s)]
        filters = tests_filter_combinations(selectors_tests(selectors))
        
        self.assertEqual(len(filters), 12)
        self.assertEqual(str(sorted(filters)), '[[bar!=blah][bar!=that][bar!=this][foo<2][foo>1], [bar!=blah][bar!=that][bar!=this][foo<=1], [bar!=blah][bar!=that][bar!=this][foo>=2], [bar=blah][foo<2][foo>1], [bar=blah][foo<=1], [bar=blah][foo>=2], [bar=that][foo<2][foo>1], [bar=that][foo<=1], [bar=that][foo>=2], [bar=this][foo<2][foo>1], [bar=this][foo<=1], [bar=this][foo>=2]]')

class CompatibilityTests(unittest.TestCase):

    def testCompatibility1(self):
        a = SelectorAttributeTest('foo', '=', 1)
        b = SelectorAttributeTest('foo', '=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility2(self):
        a = SelectorAttributeTest('foo', '=', 1)
        b = SelectorAttributeTest('bar', '=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility3(self):
        a = SelectorAttributeTest('foo', '=', 1)
        b = SelectorAttributeTest('foo', '!=', 1)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility4(self):
        a = SelectorAttributeTest('foo', '!=', 1)
        b = SelectorAttributeTest('bar', '=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility5(self):
        a = SelectorAttributeTest('foo', '!=', 1)
        b = SelectorAttributeTest('foo', '!=', 2)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility6(self):
        a = SelectorAttributeTest('foo', '!=', 1)
        b = SelectorAttributeTest('foo', '!=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility7(self):
        a = SelectorAttributeTest('foo', '=', 1)
        b = SelectorAttributeTest('foo', '<', 1)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility8(self):
        a = SelectorAttributeTest('foo', '>=', 1)
        b = SelectorAttributeTest('foo', '=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility9(self):
        a = SelectorAttributeTest('foo', '=', 1)
        b = SelectorAttributeTest('foo', '<=', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility10(self):
        a = SelectorAttributeTest('foo', '>', 1)
        b = SelectorAttributeTest('foo', '=', 1)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility11(self):
        a = SelectorAttributeTest('foo', '>', 2)
        b = SelectorAttributeTest('foo', '<=', 1)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility12(self):
        a = SelectorAttributeTest('foo', '<=', 1)
        b = SelectorAttributeTest('foo', '>', 2)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility13(self):
        a = SelectorAttributeTest('foo', '<', 1)
        b = SelectorAttributeTest('foo', '>', 1)
        assert not a.isCompatible([b])
        assert not b.isCompatible([a])

    def testCompatibility14(self):
        a = SelectorAttributeTest('foo', '<', 2)
        b = SelectorAttributeTest('foo', '>', 1)
        assert a.isCompatible([b])
        assert b.isCompatible([a])

    def testCompatibility15(self):
        # Layer[scale-denominator>1000][bar>1]
        s = Selector(SelectorElement(['Layer'], [SelectorAttributeTest('scale-denominator', '>', 1000), SelectorAttributeTest('bar', '<', 3)]))
        
        # [bar>=3][baz=quux][foo>1][scale-denominator>1000]
        f = Filter(SelectorAttributeTest('scale-denominator', '>', 1000), SelectorAttributeTest('bar', '>=', 3), SelectorAttributeTest('foo', '>', 1), SelectorAttributeTest('baz', '=', 'quux'))
        
        assert not is_applicable_selector(s, f)

    def testCompatibility16(self):
        # Layer[scale-denominator<1000][foo=1]
        s = Selector(SelectorElement(['Layer'], [SelectorAttributeTest('scale-denominator', '<', 1000), SelectorAttributeTest('foo', '=', 1)]))
        
        # [baz!=quux][foo=1][scale-denominator>1000]
        f = Filter(SelectorAttributeTest('baz', '!=', 'quux'), SelectorAttributeTest('foo', '=', 1), SelectorAttributeTest('scale-denominator', '>', 1000))
        
        assert not is_applicable_selector(s, f)

class StyleRuleTests(unittest.TestCase):

    def setUp(self):
        # a directory for all the temp files to be created below
        self.tmpdir = tempfile.mkdtemp(prefix='cascadenik-tests-')
        self.dirs = Directories(self.tmpdir, self.tmpdir, self.tmpdir)

    def tearDown(self):
        # destroy the above-created directory
        shutil.rmtree(self.tmpdir)

    def testStyleRules01(self):
        s = """
            Layer[zoom<=10][use=park] { polygon-fill: #0f0; }
            Layer[zoom<=10][use=cemetery] { polygon-fill: #999; }
            Layer[zoom>10][use=park] { polygon-fill: #6f6; }
            Layer[zoom>10][use=cemetery] { polygon-fill: #ccc; }
        """

        declarations = stylesheet_declarations(s, is_merc=True)
        rules = get_polygon_rules(declarations)
        
        self.assertEqual(408560, rules[0].maxscale.value)
        self.assertEqual(color(0xCC, 0xCC, 0xCC), rules[0].symbolizers[0].color)
        self.assertEqual("[use] = 'cemetery'", rules[0].filter.text)
        
        self.assertEqual(408560, rules[1].maxscale.value)
        self.assertEqual(color(0x66, 0xFF, 0x66), rules[1].symbolizers[0].color)
        self.assertEqual("[use] = 'park'", rules[1].filter.text)
    
        self.assertEqual(408561, rules[2].minscale.value)
        self.assertEqual(color(0x99, 0x99, 0x99), rules[2].symbolizers[0].color)
        self.assertEqual("[use] = 'cemetery'", rules[2].filter.text)
        
        self.assertEqual(408561, rules[3].minscale.value)
        self.assertEqual(color(0x00, 0xFF, 0x00), rules[3].symbolizers[0].color)
        self.assertEqual("[use] = 'park'", rules[3].filter.text)

    def testStyleRules02(self):
        s = """
            Layer[zoom<=10][foo<1] { polygon-fill: #000; }
            Layer[zoom<=10][foo>1] { polygon-fill: #00f; }
            Layer[zoom>10][foo<1] { polygon-fill: #0f0; }
            Layer[zoom>10][foo>1] { polygon-fill: #f00; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        rules = get_polygon_rules(declarations)
        
        self.assertEqual(408560, rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0x00), rules[0].symbolizers[0].color)
        self.assertEqual('[foo] < 1', rules[0].filter.text)
        
        self.assertEqual(408560, rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0x00), rules[1].symbolizers[0].color)
        self.assertEqual('[foo] > 1', rules[1].filter.text)
    
        self.assertEqual(408561, rules[2].minscale.value)
        self.assertEqual(color(0x00, 0x00, 0x00), rules[2].symbolizers[0].color)
        self.assertEqual('[foo] < 1', rules[2].filter.text)
        
        self.assertEqual(408561, rules[3].minscale.value)
        self.assertEqual(color(0x00, 0x00, 0xFF), rules[3].symbolizers[0].color)
        self.assertEqual('[foo] > 1', rules[3].filter.text)

    def testStyleRules03(self):
        s = """
            Layer[zoom<=10][foo<1] { polygon-fill: #000; }
            Layer[zoom<=10][foo>1] { polygon-fill: #00f; }
            Layer[zoom>10][foo<1] { polygon-fill: #0f0; }
            Layer[zoom>10][foo>1] { polygon-fill: #f00; }
    
            Layer[zoom<=10] { line-width: 1; }
            Layer[zoom>10] { line-width: 2; }
            Layer[foo<1] { line-color: #0ff; }
            Layer[foo=1] { line-color: #f0f; }
            Layer[foo>1] { line-color: #ff0; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)

        poly_rules = get_polygon_rules(declarations)
        
        self.assertEqual(408560, poly_rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0x00), poly_rules[0].symbolizers[0].color)
        self.assertEqual('[foo] < 1', poly_rules[0].filter.text)
        
        self.assertEqual(408560, poly_rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0x00), poly_rules[1].symbolizers[0].color)
        self.assertEqual('[foo] > 1', poly_rules[1].filter.text)
    
        self.assertEqual(408561, poly_rules[2].minscale.value)
        self.assertEqual(color(0x00, 0x00, 0x00), poly_rules[2].symbolizers[0].color)
        self.assertEqual('[foo] < 1', poly_rules[2].filter.text)
        
        self.assertEqual(408561, poly_rules[3].minscale.value)
        self.assertEqual(color(0x00, 0x00, 0xFF), poly_rules[3].symbolizers[0].color)
        self.assertEqual('[foo] > 1', poly_rules[3].filter.text)
        
        line_rules = get_line_rules(declarations)

        self.assertEqual(408560, line_rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[0].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[0].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[0].filter.text)
        
        self.assertEqual(408560, line_rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[1].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[1].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[1].filter.text)
    
        self.assertEqual(408560, line_rules[2].maxscale.value)
        self.assertEqual(color(0xFF, 0xFF, 0x00), line_rules[2].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[2].symbolizers[0].width)
        self.assertEqual('[foo] > 1', line_rules[2].filter.text)
    
        self.assertEqual(408561, line_rules[3].minscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[3].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[3].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[3].filter.text)
        
        self.assertEqual(408561, line_rules[4].minscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[4].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[4].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[4].filter.text)
        
        self.assertEqual(408561, line_rules[5].minscale.value)
        self.assertEqual(color(0xFF, 0xFF, 0x00), line_rules[5].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[5].symbolizers[0].width)
        self.assertEqual('[foo] > 1', line_rules[5].filter.text)

    def testStyleRules04(self):
        s = """
            Layer[zoom<=10] { line-width: 1; }
            Layer[zoom>10] { line-width: 2; }
            Layer[foo<1] { line-color: #0ff; }
            Layer[foo=1] { line-color: #f0f; }
            Layer[foo>1] { line-color: #ff0; }
            
            Layer label { text-face-name: 'Helvetica'; text-size: 12; text-fill: #000; }
            Layer[foo<1] label { text-face-name: 'Arial'; }
            Layer[zoom<=10] label { text-size: 10; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        line_rules = get_line_rules(declarations)

        self.assertEqual(408560, line_rules[0].maxscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[0].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[0].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[0].filter.text)
        
        self.assertEqual(408560, line_rules[1].maxscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[1].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[1].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[1].filter.text)
    
        self.assertEqual(408560, line_rules[2].maxscale.value)
        self.assertEqual(color(0xFF, 0xFF, 0x00), line_rules[2].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[2].symbolizers[0].width)
        self.assertEqual('[foo] > 1', line_rules[2].filter.text)
    
        self.assertEqual(408561, line_rules[3].minscale.value)
        self.assertEqual(color(0x00, 0xFF, 0xFF), line_rules[3].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[3].symbolizers[0].width)
        self.assertEqual('[foo] < 1', line_rules[3].filter.text)
        
        self.assertEqual(408561, line_rules[4].minscale.value)
        self.assertEqual(color(0xFF, 0x00, 0xFF), line_rules[4].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[4].symbolizers[0].width)
        self.assertEqual('[foo] = 1', line_rules[4].filter.text)
        
        self.assertEqual(408561, line_rules[5].minscale.value)
        self.assertEqual(color(0xFF, 0xFF, 0x00), line_rules[5].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[5].symbolizers[0].width)
        self.assertEqual('[foo] > 1', line_rules[5].filter.text)
        
        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(408560, text_rule_groups['label'][0].maxscale.value)
        self.assertEqual(strings('Arial'), text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][0].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][0].filter.text)
        
        self.assertEqual(408560, text_rule_groups['label'][1].maxscale.value)
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][1].symbolizers[0].size)
        self.assertEqual('[foo] >= 1', text_rule_groups['label'][1].filter.text)
    
        self.assertEqual(408561, text_rule_groups['label'][2].minscale.value)
        self.assertEqual(strings('Arial'), text_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(10, text_rule_groups['label'][2].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][2].filter.text)
        
        self.assertEqual(408561, text_rule_groups['label'][3].minscale.value)
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][3].symbolizers[0].face_name)
        self.assertEqual(10, text_rule_groups['label'][3].symbolizers[0].size)
        self.assertEqual('[foo] >= 1', text_rule_groups['label'][3].filter.text)

    def testStyleRules05(self):
        s = """
            Layer label { text-face-name: 'Helvetica'; text-size: 12; text-fill: #000; }
            Layer[foo<1] label { text-face-name: 'Arial'; }
            Layer[zoom<=10] label { text-size: 10; }
            
            Layer label { shield-face-name: 'Helvetica'; shield-size: 12; shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
            Layer[foo>1] label { shield-size: 10; }
            Layer[bar=baz] label { shield-size: 14; }
            Layer[bar=quux] label { shield-size: 16; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(408560, text_rule_groups['label'][0].maxscale.value)
        self.assertEqual(strings('Arial'), text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][0].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][0].filter.text)
        
        self.assertEqual(408560, text_rule_groups['label'][1].maxscale.value)
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][1].symbolizers[0].size)
        self.assertEqual('[foo] >= 1', text_rule_groups['label'][1].filter.text)
    
        self.assertEqual(408561, text_rule_groups['label'][2].minscale.value)
        self.assertEqual(strings('Arial'), text_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(10, text_rule_groups['label'][2].symbolizers[0].size)
        self.assertEqual('[foo] < 1', text_rule_groups['label'][2].filter.text)
        
        self.assertEqual(408561, text_rule_groups['label'][3].minscale.value)
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][3].symbolizers[0].face_name)
        self.assertEqual(10, text_rule_groups['label'][3].symbolizers[0].size)
        self.assertEqual('[foo] >= 1', text_rule_groups['label'][3].filter.text)
        
        shield_rule_groups = get_shield_rule_groups(declarations, self.dirs)
        
        assert shield_rule_groups['label'][0].minscale is None
        assert shield_rule_groups['label'][0].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, shield_rule_groups['label'][0].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][0].filter.text)
        
        assert shield_rule_groups['label'][1].minscale is None
        assert shield_rule_groups['label'][1].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(10, shield_rule_groups['label'][1].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] > 1", shield_rule_groups['label'][1].filter.text)
        
        assert shield_rule_groups['label'][2].minscale is None
        assert shield_rule_groups['label'][2].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][2].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] <= 1", shield_rule_groups['label'][2].filter.text)
        
        assert shield_rule_groups['label'][3].minscale is None
        assert shield_rule_groups['label'][3].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][3].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][3].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] > 1", shield_rule_groups['label'][3].filter.text)
        
        assert shield_rule_groups['label'][4].minscale is None
        assert shield_rule_groups['label'][4].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][4].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][4].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].height)
        self.assertEqual("[bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][4].filter.text)
        
        assert shield_rule_groups['label'][5].minscale is None
        assert shield_rule_groups['label'][5].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][5].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][5].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][5].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][5].symbolizers[0].height)
        self.assertEqual("[bar] = 'quux' and [foo] > 1", shield_rule_groups['label'][5].filter.text)

    def testStyleRules06(self):
        s = """
            Layer label { shield-face-name: 'Helvetica'; shield-size: 12; shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
            Layer[foo>1] label { shield-size: 10; }
            Layer[bar=baz] label { shield-size: 14; }
            Layer[bar=quux] label { shield-size: 16; }
    
            Layer { point-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        shield_rule_groups = get_shield_rule_groups(declarations, self.dirs)
        
        assert shield_rule_groups['label'][0].minscale is None
        assert shield_rule_groups['label'][0].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, shield_rule_groups['label'][0].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][0].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][0].filter.text)
        
        assert shield_rule_groups['label'][1].minscale is None
        assert shield_rule_groups['label'][1].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][1].symbolizers[0].face_name)
        self.assertEqual(10, shield_rule_groups['label'][1].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][1].symbolizers[0].height)
        self.assertEqual("not [bar] = 'baz' and not [bar] = 'quux' and [foo] > 1", shield_rule_groups['label'][1].filter.text)
        
        assert shield_rule_groups['label'][2].minscale is None
        assert shield_rule_groups['label'][2].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][2].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][2].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][2].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] <= 1", shield_rule_groups['label'][2].filter.text)
        
        assert shield_rule_groups['label'][3].minscale is None
        assert shield_rule_groups['label'][3].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][3].symbolizers[0].face_name)
        self.assertEqual(14, shield_rule_groups['label'][3].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][3].symbolizers[0].height)
        self.assertEqual("[bar] = 'baz' and [foo] > 1", shield_rule_groups['label'][3].filter.text)
        
        assert shield_rule_groups['label'][4].minscale is None
        assert shield_rule_groups['label'][4].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][4].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][4].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][4].symbolizers[0].height)
        self.assertEqual("[bar] = 'quux' and [foo] <= 1", shield_rule_groups['label'][4].filter.text)
        
        assert shield_rule_groups['label'][5].minscale is None
        assert shield_rule_groups['label'][5].maxscale is None
        self.assertEqual(strings('Helvetica'), shield_rule_groups['label'][5].symbolizers[0].face_name)
        self.assertEqual(16, shield_rule_groups['label'][5].symbolizers[0].size)
        if MAPNIK_VERSION < 701:
            self.assertEqual(8, shield_rule_groups['label'][5].symbolizers[0].width)
            self.assertEqual(8, shield_rule_groups['label'][5].symbolizers[0].height)
        self.assertEqual("[bar] = 'quux' and [foo] > 1", shield_rule_groups['label'][5].filter.text)

        point_rules = get_point_rules(declarations, self.dirs)
        
        assert point_rules[0].filter is None
        assert point_rules[0].minscale is None
        assert point_rules[0].maxscale is None
        if MAPNIK_VERSION < 701:
            self.assertEqual('png', point_rules[0].symbolizers[0].type)
            self.assertEqual(8, point_rules[0].symbolizers[0].width)
            self.assertEqual(8, point_rules[0].symbolizers[0].height)

    def testStyleRules07(self):
        s = """
            Layer { point-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
            Layer { polygon-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
            Layer { line-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)

        point_rules = get_point_rules(declarations, self.dirs)
        
        assert point_rules[0].filter is None
        assert point_rules[0].minscale is None
        assert point_rules[0].maxscale is None
        if MAPNIK_VERSION < 701:
            self.assertEqual('png', point_rules[0].symbolizers[0].type)
            self.assertEqual(8, point_rules[0].symbolizers[0].width)
            self.assertEqual(8, point_rules[0].symbolizers[0].height)

        polygon_pattern_rules = get_polygon_pattern_rules(declarations, self.dirs)
        
        assert polygon_pattern_rules[0].filter is None
        assert polygon_pattern_rules[0].minscale is None
        assert polygon_pattern_rules[0].maxscale is None
        if MAPNIK_VERSION < 701:
            self.assertEqual('png', polygon_pattern_rules[0].symbolizers[0].type)
            self.assertEqual(8, polygon_pattern_rules[0].symbolizers[0].width)
            self.assertEqual(8, polygon_pattern_rules[0].symbolizers[0].height)

        line_pattern_rules = get_line_pattern_rules(declarations, self.dirs)
        
        assert line_pattern_rules[0].filter is None
        assert line_pattern_rules[0].minscale is None
        assert line_pattern_rules[0].maxscale is None
        if MAPNIK_VERSION < 701:
            self.assertEqual('png', line_pattern_rules[0].symbolizers[0].type)
            self.assertEqual(8, line_pattern_rules[0].symbolizers[0].width)
            self.assertEqual(8, line_pattern_rules[0].symbolizers[0].height)

    def testStyleRules08(self):
        s = """
            Layer { line-width: 3; line-color: #fff; }
            Layer[foo=1] { outline-width: 1; outline-color: #000; }
            Layer[bar=1] { inline-width: 1; inline-color: #999; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        line_rules = get_line_rules(declarations)
        
        self.assertEqual(4, len(line_rules))
        
    
        assert line_rules[0].minscale is None
        assert line_rules[0].maxscale is None
        self.assertEqual("not [bar] = 1 and not [foo] = 1", line_rules[0].filter.text)
        self.assertEqual(1, len(line_rules[0].symbolizers))
        
        line_symbolizer = line_rules[0].symbolizers[0]
        self.assertEqual(color(0xFF, 0xFF, 0xFF), line_symbolizer.color)
        self.assertEqual(3.0, line_symbolizer.width)
        
    
        assert line_rules[1].minscale is None
        assert line_rules[1].maxscale is None
        self.assertEqual("not [bar] = 1 and [foo] = 1", line_rules[1].filter.text)
        self.assertEqual(2, len(line_rules[1].symbolizers))
        
        outline_symbolizer = line_rules[1].symbolizers[0]
        self.assertEqual(color(0x00, 0x00, 0x00), outline_symbolizer.color)
        self.assertEqual(5.0, outline_symbolizer.width)
        
        line_symbolizer = line_rules[1].symbolizers[1]
        self.assertEqual(color(0xff, 0xff, 0xff), line_symbolizer.color)
        self.assertEqual(3.0, line_symbolizer.width)
    
    
        assert line_rules[2].minscale is None
        assert line_rules[2].maxscale is None
        self.assertEqual("[bar] = 1 and not [foo] = 1", line_rules[2].filter.text)
        self.assertEqual(2, len(line_rules[2].symbolizers))
        
        line_symbolizer = line_rules[2].symbolizers[0]
        self.assertEqual(color(0xff, 0xff, 0xff), line_symbolizer.color)
        self.assertEqual(3.0, line_symbolizer.width)
        
        inline_symbolizer = line_rules[2].symbolizers[1]
        self.assertEqual(color(0x99, 0x99, 0x99), inline_symbolizer.color)
        self.assertEqual(1.0, inline_symbolizer.width)
        
    
        assert line_rules[3].minscale is None
        assert line_rules[3].maxscale is None
        self.assertEqual("[bar] = 1 and [foo] = 1", line_rules[3].filter.text)
        self.assertEqual(3, len(line_rules[3].symbolizers))
        
        outline_symbolizer = line_rules[3].symbolizers[0]
        self.assertEqual(color(0x00, 0x00, 0x00), outline_symbolizer.color)
        self.assertEqual(5.0, outline_symbolizer.width)
        
        line_symbolizer = line_rules[3].symbolizers[1]
        self.assertEqual(color(0xff, 0xff, 0xff), line_symbolizer.color)
        self.assertEqual(3.0, line_symbolizer.width)
        
        inline_symbolizer = line_rules[3].symbolizers[2]
        self.assertEqual(color(0x99, 0x99, 0x99), inline_symbolizer.color)
        self.assertEqual(1.0, inline_symbolizer.width)

    def testStyleRules09(self):
        s = """
            Layer { line-color: #000; }
            
            Layer[ELEVATION=0] { line-width: 1; }
            Layer[ELEVATION=50] { line-width: 2; }
            Layer[ELEVATION>900] { line-width: 3; line-color: #fff; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        line_rules = get_line_rules(declarations)
        
        self.assertEqual('[ELEVATION] = 0', line_rules[0].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x00), line_rules[0].symbolizers[0].color)
        self.assertEqual(1.0, line_rules[0].symbolizers[0].width)
    
        self.assertEqual('[ELEVATION] = 50', line_rules[1].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x00), line_rules[1].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[1].symbolizers[0].width)
    
        self.assertEqual('[ELEVATION] > 900', line_rules[2].filter.text)
        self.assertEqual(color(0xFF, 0xFF, 0xFF), line_rules[2].symbolizers[0].color)
        self.assertEqual(3.0, line_rules[2].symbolizers[0].width)

    def testStyleRules10(self):
        s = """
            Layer[landuse!=desert] { polygon-fill: #006; }
            Layer[landuse=field] { polygon-fill: #001; }
            Layer[landuse=meadow] { polygon-fill: #002; }
            Layer[landuse=forest] { polygon-fill: #003; }
            Layer[landuse=woods] { polygon-fill: #004; }
            Layer { polygon-fill: #000; }
        """
    
        declarations = stylesheet_declarations(s, is_merc=True)
        
        polygon_rules = get_polygon_rules(declarations)
        
        self.assertEqual("not [landuse] = 'field' and not [landuse] = 'woods' and not [landuse] = 'desert' and not [landuse] = 'forest' and not [landuse] = 'meadow'", polygon_rules[0].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x66), polygon_rules[0].symbolizers[0].color)
        
        self.assertEqual("[landuse] = 'desert'", polygon_rules[1].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x00), polygon_rules[1].symbolizers[0].color)
        
        self.assertEqual("[landuse] = 'field'", polygon_rules[2].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x11), polygon_rules[2].symbolizers[0].color)
        
        self.assertEqual("[landuse] = 'forest'", polygon_rules[3].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x33), polygon_rules[3].symbolizers[0].color)
        
        self.assertEqual("[landuse] = 'meadow'", polygon_rules[4].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x22), polygon_rules[4].symbolizers[0].color)
        
        self.assertEqual("[landuse] = 'woods'", polygon_rules[5].filter.text)
        self.assertEqual(color(0x00, 0x00, 0x44), polygon_rules[5].symbolizers[0].color)

    def testStyleRules11(self):
        """ Spaces and negative numbers in attribute selectors need to be acceptable
        """
        s = """
            Layer[PERSONS < -2000000] { polygon-fill: #6CAE4C; }
            Layer[PERSONS >= -2000000][PERSONS < 4000000] { polygon-fill: #3B7AB3; }
            Layer[PERSONS > 4000000] { polygon-fill: #88000F; }
        """
    
        declarations = stylesheet_declarations(s, False)
        polygon_rules = get_polygon_rules(declarations)
        
        self.assertEqual("[PERSONS] < -2000000", polygon_rules[0].filter.text)
        self.assertEqual(color(0x6c, 0xae, 0x4c), polygon_rules[0].symbolizers[0].color)
        
        self.assertEqual("[PERSONS] >= -2000000 and [PERSONS] < 4000000", polygon_rules[1].filter.text)
        self.assertEqual(color(0x3b, 0x7a, 0xb3), polygon_rules[1].symbolizers[0].color)
        
        self.assertEqual("[PERSONS] > 4000000", polygon_rules[2].filter.text)
        self.assertEqual(color(0x88, 0x00, 0x0f), polygon_rules[2].symbolizers[0].color)

    def testStyleRules11b(self):
        s = """
            Layer
            {
                polygon-fill: #000;
                polygon-opacity: .5;

                line-color: #000;
                line-width: 2;
                line-opacity: .5;
                line-join: miter;
                line-cap: butt;
                line-dasharray: 1,2,3;
            }
        """

        declarations = stylesheet_declarations(s, is_merc=True)

        polygon_rules = get_polygon_rules(declarations)
        
        self.assertEqual(color(0x00, 0x00, 0x00), polygon_rules[0].symbolizers[0].color)
        self.assertEqual(0.5, polygon_rules[0].symbolizers[0].opacity)

        line_rules = get_line_rules(declarations)
        
        self.assertEqual(color(0x00, 0x00, 0x00), line_rules[0].symbolizers[0].color)
        self.assertEqual(2.0, line_rules[0].symbolizers[0].width)
        self.assertEqual(0.5, line_rules[0].symbolizers[0].opacity)
        self.assertEqual('miter', line_rules[0].symbolizers[0].join)
        self.assertEqual('butt', line_rules[0].symbolizers[0].cap)
        self.assertEqual(numbers(1, 2, 3), line_rules[0].symbolizers[0].dashes)

    def testStyleRules12(self):
        s = """
            Layer label
            {
                text-face-name: 'Helvetica';
                text-size: 12;
                
                text-fill: #f00;
                text-wrap-width: 100;
                text-spacing: 50;
                text-label-position-tolerance: 25;
                text-max-char-angle-delta: 10;
                text-halo-fill: #ff0;
                text-halo-radius: 2;
                text-dx: 10;
                text-dy: 15;
                text-avoid-edges: true;
                text-min-distance: 5;
                text-allow-overlap: false;
                text-placement: point;
            }
        """

        declarations = stylesheet_declarations(s, is_merc=True)

        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(strings('Helvetica'), text_rule_groups['label'][0].symbolizers[0].face_name)
        self.assertEqual(12, text_rule_groups['label'][0].symbolizers[0].size)

        self.assertEqual(color(0xFF, 0x00, 0x00), text_rule_groups['label'][0].symbolizers[0].color)
        self.assertEqual(100, text_rule_groups['label'][0].symbolizers[0].wrap_width)
        self.assertEqual(50, text_rule_groups['label'][0].symbolizers[0].label_spacing)
        self.assertEqual(25, text_rule_groups['label'][0].symbolizers[0].label_position_tolerance)
        self.assertEqual(10, text_rule_groups['label'][0].symbolizers[0].max_char_angle_delta)
        self.assertEqual(color(0xFF, 0xFF, 0x00), text_rule_groups['label'][0].symbolizers[0].halo_color)
        self.assertEqual(2, text_rule_groups['label'][0].symbolizers[0].halo_radius)
        self.assertEqual(10, text_rule_groups['label'][0].symbolizers[0].dx)
        self.assertEqual(15, text_rule_groups['label'][0].symbolizers[0].dy)
        self.assertEqual(boolean(1), text_rule_groups['label'][0].symbolizers[0].avoid_edges)
        self.assertEqual(5, text_rule_groups['label'][0].symbolizers[0].minimum_distance)
        self.assertEqual(boolean(0), text_rule_groups['label'][0].symbolizers[0].allow_overlap)
        self.assertEqual('point', text_rule_groups['label'][0].symbolizers[0].label_placement)

    def testStyleRules12a(self):
        s = """
            Layer label1
            {
                text-face-name: 'Bananas';
                text-size: 12;
                text-fill: #f00;
            }
            Layer label2
            {
                text-face-name: "Monkeys";
                text-size: 12;
                text-fill: #f00;
            }
        """

        declarations = stylesheet_declarations(s, is_merc=True)

        text_rule_groups = get_text_rule_groups(declarations)
        
        self.assertEqual(strings('Bananas'), text_rule_groups['label1'][0].symbolizers[0].face_name)
        self.assertEqual(strings('Monkeys'), text_rule_groups['label2'][0].symbolizers[0].face_name)

    def testStyleRules13(self):
        s = """
            Layer
            {
                point-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                point-width: 16;
                point-height: 16;
                point-allow-overlap: true;

                polygon-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                polygon-pattern-width: 16;
                polygon-pattern-height: 16;

                line-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                line-pattern-width: 16;
                line-pattern-height: 16;
            }
        """

        declarations = stylesheet_declarations(s, is_merc=True)

        point_rules = get_point_rules(declarations, self.dirs)
        
        self.assertEqual(16, point_rules[0].symbolizers[0].width)
        self.assertEqual(16, point_rules[0].symbolizers[0].height)
        self.assertEqual(boolean(True), point_rules[0].symbolizers[0].allow_overlap)

        polygon_pattern_rules = get_polygon_pattern_rules(declarations, self.dirs)
        
        self.assertEqual(16, polygon_pattern_rules[0].symbolizers[0].width)
        self.assertEqual(16, polygon_pattern_rules[0].symbolizers[0].height)

        line_pattern_rules = get_line_pattern_rules(declarations, self.dirs)
        
        self.assertEqual(16, line_pattern_rules[0].symbolizers[0].width)
        self.assertEqual(16, line_pattern_rules[0].symbolizers[0].height)

    def testStyleRules14(self):
        s = """
            Layer just_image
            {
                shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                shield-width: 16;
                shield-height: 16;
                
                shield-min-distance: 5;
            }

            Layer both
            {
                shield-face-name: 'Interstate';
                shield-size: 12;
                
                shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                shield-width: 16;
                shield-height: 16;
                
                shield-fill: #f00;
                shield-min-distance: 5;
            }
        """

        declarations = stylesheet_declarations(s, is_merc=True)

        shield_rule_groups = get_shield_rule_groups(declarations, self.dirs)
        
        # Also Mapnik's python bindings should be able to allow a ShieldSymbolizer without text
        # put this is not properly exposed in the latest release (0.7.1)
        # So, disabling this test until we actually add support in Mapnik 0.7.x
        # http://trac.mapnik.org/ticket/652
        #self.assertEqual(16, shield_rule_groups['just_image'][0].symbolizers[0].width)
        #self.assertEqual(16, shield_rule_groups['just_image'][0].symbolizers[0].height)
        #self.assertEqual(5, shield_rule_groups['just_image'][0].symbolizers[0].minimum_distance)
        
        self.assertEqual(strings('Interstate'), shield_rule_groups['both'][0].symbolizers[0].face_name)
        self.assertEqual(12, shield_rule_groups['both'][0].symbolizers[0].size)
        self.assertEqual(color(0xFF, 0x00, 0x00), shield_rule_groups['both'][0].symbolizers[0].color)
        self.assertEqual(16, shield_rule_groups['both'][0].symbolizers[0].width)
        self.assertEqual(16, shield_rule_groups['both'][0].symbolizers[0].height)
        self.assertEqual(5, shield_rule_groups['both'][0].symbolizers[0].minimum_distance)

class DataSourcesTests(unittest.TestCase):

    def gen_section(self, name, **kwargs):
        return """[%s]\n%s\n""" % (name, "\n".join(("%s=%s" % kwarg for kwarg in kwargs.items())))

    def testSimple1(self):
        cdata = """
[simple]
type=shape
file=foo.shp
garbage=junk
"""
        dss = DataSources(None, None)
        dss.add_config(cdata, __file__)
        self.assertTrue(dss.sources['simple'] != None)

        ds = dss.sources['simple']
        self.assertTrue(ds['parameters'] != None)
        p = ds['parameters']
        self.assertEqual(p['type'],'shape')
        self.assertEqual(p['file'],'foo.shp')
        self.assertTrue(p.get('garbage') == None)

        self.assertRaises(Exception, dss.add_config, (self.gen_section("foo", encoding="bar"), __file__))
    
    def testChain1(self):
        dss = DataSources(None, None)
        dss.add_config(self.gen_section("t1", type="shape", file="foo"), __file__)
        dss.add_config(self.gen_section("t2", type="shape", file="foo"), __file__)
        self.assertTrue(dss.get('t1') != None)
        self.assertTrue(dss.get('t2') != None)

    def testDefaults1(self):
        dss = DataSources(None, None)
        sect = self.gen_section("DEFAULT", var="cows") + "\n" + self.gen_section("t1", type="shape", file="%(var)s") 
        #dss.add_config(self.gen_section("DEFAULT", var="cows"), __file__)
        #dss.add_config(self.gen_section("t1", type="shape", file="%(var)s"), __file__)
        dss.add_config(sect, __file__)

        self.assertEqual(dss.get('t1')['parameters']['file'], "cows")

    def testLocalDefaultsFromString(self):
        dss = DataSources(None, None)
        dss.set_local_cfg_data(self.gen_section("DEFAULT", var="cows2"))
        sect = self.gen_section("DEFAULT", var="cows") + "\n" + self.gen_section("t1", type="shape", file="%(var)s") 
        dss.add_config(sect, __file__)
        dss.finalize()
        self.assertEqual(dss.get('t1')['parameters']['file'], "cows2")

    def testLocalDefaultsFromFile(self):
        handle, cfgpath = tempfile.mkstemp()
        os.close(handle)

        try:
            open(cfgpath, 'w').write(self.gen_section("DEFAULT", var="cows2"))
            self.assertTrue(os.path.exists(cfgpath))
            dss = DataSources(__file__, cfgpath)
            sect = self.gen_section("DEFAULT", var="cows") + "\n" + self.gen_section("t1", type="shape", file="%(var)s") 
            dss.add_config(sect, __file__)
            self.assertEqual(dss.get('t1')['parameters']['file'], "cows2")
        finally:
            os.unlink(cfgpath)

    def testBase1(self):
        dss = DataSources(None, None)
        dss.add_config(self.gen_section("base", type="shape", encoding="latin1"), __file__)
        dss.add_config(self.gen_section("t2", template="base", file="foo"), __file__)
        self.assertTrue("base" in dss.templates)
        self.assertEqual(dss.get('t2')['template'], 'base')
        self.assertEqual(dss.get('t2')['parameters']['file'], 'foo')

    def testSRS(self):
        dss = DataSources(None, None)
        dss.add_config(self.gen_section("s", type="shape", layer_srs="epsg:4326"), __file__)
        dss.add_config(self.gen_section("g", type="shape", layer_srs="epsg:900913"), __file__)
        self.assertEqual(dss.get("s")['layer_srs'], dss.PROJ4_PROJECTIONS['epsg:4326'])
        self.assertEqual(dss.get("g")['layer_srs'], dss.PROJ4_PROJECTIONS['epsg:900913'])
        self.assertRaises(Exception, dss.add_config, (self.gen_section("s", type="shape", layer_srs="epsg:43223432423"), __file__))

    def testDataTypes(self):
        dss = DataSources(None, None)
        dss.add_config(self.gen_section("s",
                                        type="postgis",
                                        cursor_size="5",
                                        estimate_extent="yes"), __file__)
        self.assertEqual(dss.get("s")['parameters']['cursor_size'], 5)
        self.assertEqual(dss.get("s")['parameters']['estimate_extent'], True)

        self.assertRaises(Exception,
                          dss.add_config,
                          (self.gen_section("f",
                                            type="postgis",
                                            cursor_size="5.xx",
                                            estimate_extent="yes"), __file__))


class CompileXMLTests(unittest.TestCase):

    def setUp(self):
        # a directory for all the temp files to be created below
        self.tmpdir = tempfile.mkdtemp(prefix='cascadenik-tests-')
        self.data = tempfile.mkdtemp(prefix='cascadenik-data-')
        self.dirs = Directories(self.tmpdir, self.tmpdir, os.getcwd())
        
        for name in ('test.dbf', 'test.prj', 'test.qpj', 'test.shp', 'test.shx'):
            href = 'http://cascadenik-sampledata.s3.amazonaws.com/data/' + name
            path = os.path.join(self.data, name)
            
            file = open(path, 'w')
            file.write(urllib.urlopen(href).read())
            file.close()
        
    def tearDown(self):
        # destroy the above-created directory
        shutil.rmtree(self.tmpdir)
        shutil.rmtree(self.data)

    def testCompile1(self):
        """
        """
        s = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { map-bgcolor: #fff; }
                    
                    Layer
                    {
                        polygon-fill: #999;
                        line-color: #fff;
                        line-width: 1;
                        outline-color: #000;
                        outline-width: 1;
                    }
                    
                    Layer name
                    {
                        text-face-name: 'Comic Sans';
                        text-size: 14;
                        text-fill: #f90;
                    }
                </Stylesheet>
                <Datasource name="template">
                    <Parameter name="type">shape</Parameter>
                    <Parameter name="encoding">latin1</Parameter>
                    <Parameter name="base">data</Parameter>
                </Datasource>
                <Layer srs="+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource base="template">
                        <Parameter name="file">test.shp</Parameter>
                    </Datasource>
                </Layer>
                <Layer srs="+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource base="template">
                        <Parameter name="file">test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        self.doCompile1(s)

        # run the same test with a datasourcesconfig
        dscfg = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { map-bgcolor: #fff; }
                    
                    Layer
                    {
                        polygon-fill: #999;
                        line-color: #fff;
                        line-width: 1;
                        outline-color: #000;
                        outline-width: 1;
                    }
                    
                    Layer name
                    {
                        text-face-name: 'Comic Sans';
                        text-size: 14;
                        text-fill: #f90;
                    }
                </Stylesheet>
                <DataSourcesConfig>
[DEFAULT]
default_layer_srs = epsg:4326
other_srs = epsg:4326

[template1]
type=shape
layer_srs=%(default_layer_srs)s
encoding=latin1
base=data

[test_shp]
file=test.shp
template=template1

[test_shp_2]
type=shape
encoding=latin1
base=data
layer_srs=%(other_srs)s
                </DataSourcesConfig>
                <Layer source_name="test_shp" />
                <Layer source_name="test_shp_2" />
            </Map>
        """
        map = self.doCompile1(dscfg)        
        self.assertEqual(map.layers[1].srs, '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
        
        handle, cfgpath = tempfile.mkstemp()
        os.close(handle)

        try:
            open(cfgpath, 'w').write("[DEFAULT]\nother_srs=epsg:900913")
            map = self.doCompile1(dscfg, datasources_cfg=cfgpath)
            self.assertEqual(map.layers[1].srs, '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs')
        finally:
            os.unlink(cfgpath)
        
    def doCompile1(self, s, **kwargs):
        map = compile(s, self.dirs, **kwargs)
        
        self.assertEqual(2, len(map.layers))
        self.assertEqual(3, len(map.layers[0].styles))

        self.assertEqual(1, len(map.layers[0].styles[0].rules))
        self.assertEqual(1, len(map.layers[0].styles[0].rules[0].symbolizers))

        self.assertEqual(color(0x99, 0x99, 0x99), map.layers[0].styles[0].rules[0].symbolizers[0].color)
        self.assertEqual(1.0, map.layers[0].styles[0].rules[0].symbolizers[0].opacity)

        self.assertEqual(1, len(map.layers[0].styles[1].rules))
        self.assertEqual(2, len(map.layers[0].styles[1].rules[0].symbolizers))

        self.assertEqual(color(0x00, 0x00, 0x00), map.layers[0].styles[1].rules[0].symbolizers[0].color)
        self.assertEqual(color(0xFF, 0xFF, 0xFF), map.layers[0].styles[1].rules[0].symbolizers[1].color)
        self.assertEqual(3.0, map.layers[0].styles[1].rules[0].symbolizers[0].width)
        self.assertEqual(1.0, map.layers[0].styles[1].rules[0].symbolizers[1].width)

        self.assertEqual(1, len(map.layers[0].styles[2].rules))
        self.assertEqual(1, len(map.layers[0].styles[2].rules[0].symbolizers))

        self.assertEqual(strings('Comic Sans'), map.layers[0].styles[2].rules[0].symbolizers[0].face_name)
        self.assertEqual(14, map.layers[0].styles[2].rules[0].symbolizers[0].size)

        self.assertEqual(map.layers[0].srs, '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
        self.assertEqual(os.path.basename(map.layers[0].datasource.parameters['file']), 'test.shp')
        self.assertEqual(map.layers[0].datasource.parameters['encoding'], 'latin1')
        self.assertEqual(map.layers[0].datasource.parameters['type'], 'shape')
        return map

    def testCompile2(self):
        """
        """
        s = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { map-bgcolor: #fff; }
                    
                    Layer
                    {
                        polygon-fill: #999;
                        polygon-opacity: 0.5;
                        line-color: #fff;
                        line-width: 2;
                        outline-color: #000;
                        outline-width: 1;
                    }
                    
                    Layer name
                    {
                        text-face-name: 'Comic Sans';
                        text-size: 14;
                        text-fill: #f90;
                    }
                </Stylesheet>
                <Datasource name="template">
                     <Parameter name="type">shape</Parameter>
                     <Parameter name="encoding">latin1</Parameter>
                </Datasource>

                <Layer>
                    <Datasource base="template">
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">%(data)s/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % self.__dict__

        map = compile(s, self.dirs)
        
        mmap = mapnik.Map(640, 480)
        map.to_mapnik(mmap)
        
        (handle, path) = tempfile.mkstemp(suffix='.xml', prefix='cascadenik-mapnik-')
        os.close(handle)
        
        mapnik.save_map(mmap, path)
        doc = xml.etree.ElementTree.parse(path)
        map_el = doc.getroot()
        
        #print open(path, 'r').read()
        os.unlink(path)

        self.assertEqual(3, len(map_el.findall('Style')))
        self.assertEqual(1, len(map_el.findall('Layer')))
        self.assertEqual(3, len(map_el.find('Layer').findall('StyleName')))
        
        for stylename_el in map_el.find('Layer').findall('StyleName'):
            self.assertTrue(stylename_el.text in [style_el.get('name') for style_el in map_el.findall('Style')])

        for style_el in map_el.findall('Style'):
            if style_el.get('name').startswith('polygon style '):
                self.assertEqual(1, len(style_el.find('Rule').findall('PolygonSymbolizer')))

            if style_el.get('name').startswith('line style '):
                self.assertEqual(2, len(style_el.find('Rule').findall('LineSymbolizer')))

            if style_el.get('name').startswith('text style '):
                self.assertEqual(1, len(style_el.find('Rule').findall('TextSymbolizer')))

        self.assertEqual(len(map_el.find("Layer").findall('Datasource')), 1)
        params = dict(((p.get('name'), p.text) for p in map_el.find('Layer').find('Datasource').findall('Parameter')))
        self.assertEqual(params['type'], 'shape')
        self.assertTrue(params['file'].endswith('%s/test.shp' % self.data))
        self.assertEqual(params['encoding'], 'latin1')

    def testCompile3(self):
        """
        """
        map = output.Map(layers=[
            output.Layer('this',
            output.Datasource(type="shape",file="%s/test.shp" % self.data), [
                output.Style('a style', [
                    output.Rule(
                        output.MinScaleDenominator(1),
                        output.MaxScaleDenominator(100),
                        output.Filter("[this] = 'that'"),
                        [
                            output.PolygonSymbolizer(color(0xCC, 0xCC, 0xCC))
                        ])
                    ])
                ]),
            output.Layer('that',
            output.Datasource(type="shape",file="%s/test.shp" % self.data), [
                output.Style('another style', [
                    output.Rule(
                        output.MinScaleDenominator(101),
                        output.MaxScaleDenominator(200),
                        output.Filter("[this] = 2"),
                        [
                            output.PolygonSymbolizer(color(0x33, 0x33, 0x33)),
                            output.LineSymbolizer(color(0x66, 0x66, 0x66), 2)
                        ])
                    ])
                ])
            ])
        
        mmap = mapnik.Map(640, 480)
        map.to_mapnik(mmap)
        
        (handle, path) = tempfile.mkstemp(suffix='.xml', prefix='cascadenik-mapnik-')
        os.close(handle)
        
        mapnik.save_map(mmap, path)
        doc = xml.etree.ElementTree.parse(path)
        map_el = doc.getroot()
        
        # print open(path, 'r').read()
        os.unlink(path)
        
        self.assertEqual(2, len(map_el.findall('Style')))
        self.assertEqual(2, len(map_el.findall('Layer')))
        
        for layer_el in map_el.findall('Layer'):
            self.assertEqual(1, len(layer_el.findall('StyleName')))
            self.assertTrue(layer_el.find('StyleName').text in [style_el.get('name') for style_el in map_el.findall('Style')])

        for style_el in map_el.findall('Style'):
            if style_el.get('name') == 'a style':
                self.assertEqual("([this]='that')", style_el.find('Rule').find('Filter').text)
                self.assertEqual('1', style_el.find('Rule').find('MinScaleDenominator').text)
                self.assertEqual('100', style_el.find('Rule').find('MaxScaleDenominator').text)
                self.assertEqual(1, len(style_el.find('Rule').findall('PolygonSymbolizer')))

            if style_el.get('name') == 'another style':
                self.assertEqual('([this]=2)', style_el.find('Rule').find('Filter').text)
                self.assertEqual('101', style_el.find('Rule').find('MinScaleDenominator').text)
                self.assertEqual('200', style_el.find('Rule').find('MaxScaleDenominator').text)
                self.assertEqual(1, len(style_el.find('Rule').findall('PolygonSymbolizer')))
                self.assertEqual(1, len(style_el.find('Rule').findall('LineSymbolizer')))

    def testCompile4(self):
        s = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { 
                        map-bgcolor: #fff; 
                    }
                    
                    Layer {
                        point-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                        point-allow-overlap: true;
                    }
                    
                    Layer {
                        line-color: #0f0;
                        line-width: 3;
                        line-dasharray: 8,100,4,50;
                    }

                    Layer { 
                        polygon-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); 
                    }
                    Layer { 
                        line-pattern-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png'); 
                    }
                    
                    Layer name {
                        text-face-name: "DejaVu Sans Book";
                        text-size: 10;
                        text-fill: #005;
                        text-halo-radius: 1;
                        text-halo-fill: #f00;
                        text-placement: line;
                        text-allow-overlap: true;
                        text-avoid-edges: true;
                    }
                    
                    Layer name2 {
                        shield-face-name: 'Helvetica';
                        shield-size: 12;
                        
                        shield-file: url('http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png');
                        shield-width: 16;
                        shield-height: 16;
                        
                        shield-fill: #f00;
                        shield-min-distance: 5;
                        shield-spacing: 7;
                        shield-line-spacing: 3;
                        shield-character-spacing: 18;
                    }
                </Stylesheet>
                <Datasource name="template">
                     <Parameter name="type">shape</Parameter>
                     <Parameter name="encoding">latin1</Parameter>
                </Datasource>

                <Layer>
                    <Datasource base="template">
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">%(data)s/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % self.__dict__

        mmap = mapnik.Map(640, 480)
        ms = compile(s, self.dirs)
        ms.to_mapnik(mmap, self.dirs)
        mapnik.save_map(mmap, os.path.join(self.tmpdir, 'out.mml'))

    def testCompile5(self):
        s = u"""<?xml version="1.0" encoding="UTF-8" ?>
            <Map>
                <Stylesheet>
                    Layer[name="Grüner Strich"] { polygon-fill: #000; }
                </Stylesheet>
                <Layer>
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">%(data)s/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """.encode('utf-8') % self.__dict__

        mmap = mapnik.Map(640, 480)
        ms = compile(s, self.dirs)
        ms.to_mapnik(mmap, self.dirs)
        mapnik.save_map(mmap, os.path.join(self.tmpdir, 'out.mml'))


    def testCompile6(self):
        s = u"""
            Layer NAME
            {
                text-anchor-dx: 10;
                text-anchor-dy: 10;
                text-allow-overlap: true;
                text-avoid-edges: true;
                text-align: middle;
                text-character-spacing: 10;
                text-dx: 10;
                text-dy: 15;
                text-face-name: 'Helvetica';
                text-fill: #f00;
                text-halo-fill: #ff0;
                text-halo-radius: 2;
                text-label-position-tolerance: 25;
                text-line-spacing:10;
                
                text-anchor-dx: 10;
                text-anchor-dy: 10;
                text-align: left;
                text-vertical-align: bottom;
                text-justify-align: left;
                text-transform: uppercase;
                text-size: 12;
                text-spacing: 50;
                text-wrap-width: 100;
                text-transform: uppercase;
                text-max-char-angle-delta: 10;
                text-min-distance: 5;
                text-placement: line;
                text-vertical-align: top;
            }
        """
        declarations = stylesheet_declarations(s, is_merc=True)
        text_rule_groups = get_text_rule_groups(declarations)
        sym = text_rule_groups['NAME'][0].symbolizers[0].to_mapnik()
        
        if MAPNIK_VERSION >= 200000:
            self.assertEqual((10, 15), sym.properties.displacement if (MAPNIK_VERSION >= 200100) else sym.displacement)
        else:
            self.assertEqual([10, 15], sym.get_displacement())
        
        # todo - anchor (does not do anything yet in mapnik, but likely will)
        # and is not set in xml, but accepted in python
        #self.assertEqual([0,5], sym.get_anchor())
        self.assertEqual(True, sym.properties.allow_overlap if (MAPNIK_VERSION >= 200100) else sym.allow_overlap)
        self.assertEqual(True, sym.properties.avoid_edges if (MAPNIK_VERSION >= 200100) else sym.avoid_edges)
        self.assertEqual(10, sym.format.character_spacing if (MAPNIK_VERSION >= 200100) else sym.character_spacing)
        self.assertEqual('Helvetica', sym.format.face_name if (MAPNIK_VERSION >= 200100) else sym.face_name)
        self.assertEqual(mapnik.Color("#f00"), sym.format.fill if (MAPNIK_VERSION >= 200100) else sym.fill)
        
        self.assertEqual(mapnik.justify_alignment.LEFT, sym.properties.justify_alignment if (MAPNIK_VERSION >= 200100) else sym.justify_alignment)
        self.assertEqual(mapnik.Color("#ff0"), sym.format.halo_fill if (MAPNIK_VERSION >= 200100) else sym.halo_fill)
        self.assertEqual(2, sym.format.halo_radius if (MAPNIK_VERSION >= 200100) else sym.halo_radius)
        
        if MAPNIK_VERSION >= 200100:
            # TextSymbolizer got a "clip" attribute and we want it to be false.
            self.assertFalse(sym.clip)
        
        if MAPNIK_VERSION >= 200100:
            # TextSymbolizer lost its "name" attribute in Mapnik 2.1.
            pass
        elif MAPNIK_VERSION >= 200001:
            self.assertEqual('[NAME]', str(sym.name))
        else:
            self.assertEqual('NAME', sym.name)
        
        self.assertEqual(12, sym.format.text_size if (MAPNIK_VERSION >= 200100) else sym.text_size)
        self.assertEqual(100, sym.properties.wrap_width if (MAPNIK_VERSION >= 200100) else sym.wrap_width)
        self.assertEqual(50, sym.properties.label_spacing if (MAPNIK_VERSION >= 200100) else sym.label_spacing)
        self.assertEqual(25, sym.properties.label_position_tolerance if (MAPNIK_VERSION >= 200100) else sym.label_position_tolerance)
        
        if MAPNIK_VERSION >= 200100:
            # Seriously?
            self.assertEqual(10, sym.properties.maximum_angle_char_delta if (MAPNIK_VERSION >= 200100) else sym.maximum_angle_char_delta)
        else:
            self.assertEqual(10, sym.max_char_angle_delta)
        
        self.assertEqual(10, sym.format.line_spacing if (MAPNIK_VERSION >= 200100) else sym.line_spacing)
        self.assertEqual(5, sym.properties.minimum_distance if (MAPNIK_VERSION >= 200100) else sym.minimum_distance)
        self.assertEqual(mapnik.label_placement.LINE_PLACEMENT, sym.properties.label_placement if (MAPNIK_VERSION >= 200100) else sym.label_placement)
    
    def testCompile7(self):
        s = """
            #roads
            {
                line-color: #f90;
                line-width: 1 !important;
            }
            
            #roads[tiny=yes]
            {
                display: none;
            }
        """
        declarations = stylesheet_declarations(s, is_merc=True)
        line_rules = get_line_rules(declarations)
        
        self.assertEqual(1, len(line_rules))
        self.assertEqual(line_rules[0].filter.text, "not [tiny] = 'yes'")

    def testCompile8(self):
        s = """
            #roads[zoom=12]
            {
                line-color: #f90;
                line-width: 1;
            }

            #roads[zoom=12] name
            {
                text-fill: #f90;
                text-face-name: "Courier New";
                text-size: 12;
            }
        """
        declarations = stylesheet_declarations(s, is_merc=True, scale=2)

        line_rules = get_line_rules(declarations)
        line_rule = line_rules[0]
        
        self.assertEqual(1, len(line_rules))
        self.assertEqual(51070, line_rule.minscale.value)
        self.assertEqual(102139, line_rule.maxscale.value)
        self.assertEqual(2, line_rule.symbolizers[0].width)

        text_rules = get_text_rule_groups(declarations).get('name', [])
        text_rule = text_rules[0]
        
        self.assertEqual(1, len(text_rules))
        self.assertEqual(51070, text_rule.minscale.value)
        self.assertEqual(102139, text_rule.maxscale.value)
        self.assertEqual(24, text_rule.symbolizers[0].size)

    def testCompile9(self):
        s = u"""
            Layer NAME
            {
                text-face-name: 'Helvetica', 'DejaVu Sans Book';
                text-fill: #f00;
                text-size: 12;
            }
        """
        if MAPNIK_VERSION < 200100:
            # Mapnik only supports multiple font face names as of version 2.1
            return
        
        declarations = stylesheet_declarations(s, is_merc=True)
        text_rule_groups = get_text_rule_groups(declarations)
        
        symbolizer = text_rule_groups['NAME'][0].symbolizers[0]
        fontsets = {symbolizer.get_fontset_name(): output.FontSet(symbolizer.face_name.values).to_mapnik()}
        sym = text_rule_groups['NAME'][0].symbolizers[0].to_mapnik(fontsets)
        
        self.assertEqual(mapnik.Color("#f00"), sym.format.fill if (MAPNIK_VERSION >= 200100) else sym.fill)
        self.assertEqual(12, sym.format.text_size if (MAPNIK_VERSION >= 200100) else sym.text_size)

        # TODO: test for output of FontSet in text symbolizer when Mapnik
        # adds support. See also https://github.com/mapnik/mapnik/issues/1483

    def testCompile10(self):
        """
        """
        s = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { map-bgcolor: #fff; }
                    
                    Layer name
                    {
                        text-face-name: 'Comic Sans', 'Papyrus';
                        text-size: 14;
                        text-fill: #f90;
                    }
                </Stylesheet>
                <Datasource name="template">
                     <Parameter name="type">shape</Parameter>
                     <Parameter name="encoding">latin1</Parameter>
                </Datasource>
                <Layer>
                    <Datasource base="template">
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">%(data)s/test.shp</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % self.__dict__

        map = compile(s, self.dirs)
        mmap = mapnik.Map(640, 480)
        
        map.to_mapnik(mmap)
        
        (handle, path) = tempfile.mkstemp(suffix='.xml', prefix='cascadenik-mapnik-')
        os.close(handle)
        
        mapnik.save_map(mmap, path)
        doc = xml.etree.ElementTree.parse(path)
        map_el = doc.getroot()
        
        self.assertEqual(len(map_el.find("Layer").findall('Datasource')), 1)
        params = dict(((p.get('name'), p.text) for p in map_el.find('Layer').find('Datasource').findall('Parameter')))
        self.assertEqual(params['type'], 'shape')
        self.assertTrue(params['file'].endswith('%s/test.shp' % self.data))
        self.assertEqual(params['encoding'], 'latin1')
        
        textsym_el = map_el.find('Style').find('Rule').find('TextSymbolizer')

        if MAPNIK_VERSION >= 200100:
            self.assertEqual('false', textsym_el.get('clip'))
        
        if MAPNIK_VERSION < 200100:
            # Mapnik only supports multiple font face names as of version 2.1,
            # so check for single face name here and skip remaining tests.

            if MAPNIK_VERSION >= 200000:
                # It changed as of 2.0.
                self.assertEqual('Comic Sans', textsym_el.get('face-name'))
            else:
                self.assertEqual('Comic Sans', textsym_el.get('face_name'))

            return
        
        fontset_el = map_el.find('FontSet')

        self.assertEqual('Comic Sans', fontset_el.findall('Font')[0].get('face-name'))
        self.assertEqual('Papyrus', fontset_el.findall('Font')[1].get('face-name'))
        
        if MAPNIK_VERSION >= 200101:
            # Ensure that the fontset-name made it out,
            # see also https://github.com/mapnik/mapnik/issues/1483
            self.assertEqual(fontset_el.get('name'), textsym_el.get('fontset-name'))

    def testCompile11(self):
        """
        """
        s = """<?xml version="1.0"?>
            <Map>
                <Stylesheet>
                    Map { map-bgcolor: #fff; }
                </Stylesheet>
            </Map>
        """
        map = compile(s, self.dirs, user_styles=['http://cascadenik-sampledata.s3.amazonaws.com/black-bgcolor.css'])
        
        self.assertEqual(str(map.background), '#000000')

class RelativePathTests(unittest.TestCase):

    def setUp(self):
        # directories for all the temp files to be created below
        self.tmpdir1 = os.path.realpath(tempfile.mkdtemp(prefix='cascadenik-tests1-'))
        self.tmpdir2 = os.path.realpath(tempfile.mkdtemp(prefix='cascadenik-tests2-'))

        basepath = os.path.dirname(__file__)
        
        paths = ('paths-test2.mml',
                 'paths-test2.mss',
                 'mission-points/mission-points.dbf',
                 'mission-points/mission-points.prj',
                 'mission-points/mission-points.shp',
                 'mission-points/mission-points.shx',
                 'mission-points.zip',
                 'purple-point.png')

        for path in paths:
            href = urlparse.urljoin('http://cascadenik-sampledata.s3.amazonaws.com', path)
            path = os.path.join(self.tmpdir1, os.path.basename(path))
            file = open(path, 'w')
            file.write(urllib.urlopen(href).read())
            file.close()

    def tearDown(self):
        # destroy the above-created directories
        shutil.rmtree(self.tmpdir1)
        shutil.rmtree(self.tmpdir2)

    def testLocalizedPaths(self):
        
        dirs = Directories(self.tmpdir1, self.tmpdir1, self.tmpdir1)

        mml_path = dirs.output + '/style.mml'
        mml_file = open(mml_path, 'w')
        
        print >> mml_file, """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">http://cascadenik-sampledata.s3.amazonaws.com/mission-points.zip</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        
        mml_file.close()
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert not os.path.isabs(img_path)
        assert os.path.exists(os.path.join(dirs.output, img_path))
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert not os.path.isabs(shp_path)
        assert os.path.exists(os.path.join(dirs.output, shp_path))

    def testSplitPaths(self):
        
        dirs = Directories(self.tmpdir1, self.tmpdir2, self.tmpdir1)

        mml_path = dirs.output + '/style.mml'
        mml_file = open(mml_path, 'w')
        
        print >> mml_file, """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("http://cascadenik-sampledata.s3.amazonaws.com/purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">http://cascadenik-sampledata.s3.amazonaws.com/mission-points.zip</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        
        mml_file.close()
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.cache)
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(dirs.cache)
        assert os.path.exists(shp_path)

    def testRelativePaths(self):
    
        dirs = Directories(self.tmpdir1, self.tmpdir1, self.tmpdir1)
        
        mml_path = dirs.output + '/style.mml'
        mml_file = open(mml_path, 'w')
        
        print >> mml_file, """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        
        mml_file.close()
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert not os.path.isabs(img_path)
        assert os.path.exists(os.path.join(dirs.output, img_path))
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert not os.path.isabs(shp_path), shp_path
        assert os.path.exists(os.path.join(dirs.output, shp_path))

    def testDistantPaths(self):
    
        dirs = Directories(self.tmpdir2, self.tmpdir2, self.tmpdir1)
        
        mml_path = dirs.output + '/style.mml'
        mml_file = open(mml_path, 'w')
        
        print >> mml_file, """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """
        
        mml_file.close()
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.source[7:]), str((img_path, dirs.source[7:]))
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(dirs.source[7:]), str((shp_path, dirs.source[7:]))
        assert os.path.exists(shp_path)

    def testAbsolutePaths(self):
    
        dirs = Directories(self.tmpdir2, self.tmpdir2, self.tmpdir1)
        
        mml_path = dirs.output + '/style.mml'
        mml_file = open(mml_path, 'w')
        
        print >> mml_file, """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("%s/purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">%s/mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % (self.tmpdir1, self.tmpdir1)
        
        mml_file.close()
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.source[7:])
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(dirs.source[7:])
        assert os.path.exists(shp_path)

    def testRemotePaths(self):
        """ MML and MSS files are remote, cache and output to a local directory.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir2, 'http://cascadenik-sampledata.s3.amazonaws.com')
        
        mml_href = 'http://cascadenik-sampledata.s3.amazonaws.com/paths-test.mml'
        
        map = compile(mml_href, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert not os.path.isabs(img_path)
        assert os.path.exists(os.path.join(dirs.output, img_path))
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert not os.path.isabs(shp_path)
        assert os.path.exists(os.path.join(dirs.output, shp_path))

    def testRemoteLinkedSheetPaths(self):
        """ MML and MSS files are remote, cache to one local directory and output to a second.
        """
        dirs = Directories(self.tmpdir1, self.tmpdir2, 'http://cascadenik-sampledata.s3.amazonaws.com')
        
        mml_href = 'http://cascadenik-sampledata.s3.amazonaws.com/paths-test2.mml'
        
        map = compile(mml_href, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.cache), str((img_path, dirs.cache))
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(dirs.cache), str((shp_path, dirs.cache))
        assert os.path.exists(shp_path)

    def testLocalLinkedSheetPaths(self):
        """ MML and MSS files are in one directory, cache and output to a second.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir2, self.tmpdir1)
        
        mml_path = os.path.join(self.tmpdir1, 'paths-test2.mml')
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.source[7:]), str((img_path, dirs.source[7:]))
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert not os.path.isabs(shp_path)
        assert os.path.exists(os.path.join(dirs.output, shp_path))

    def testSplitLinkedSheetPaths(self):
        """ MML and MSS files are in one directory, cache in that same directory, and output to a second.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir1, self.tmpdir1)
        
        mml_path = os.path.join(self.tmpdir1, 'paths-test2.mml')
        
        map = compile(mml_path, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(dirs.source[7:]), str((img_path, dirs.source[7:]))
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(dirs.cache), str((shp_path, dirs.cache))
        assert os.path.exists(shp_path)

    def testReflexivePaths(self):
        """ MML file is at a remote location, but it references a local resource by file://.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir2, 'http://cascadenik-sampledata.s3.amazonaws.com')
        
        mml_data = """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet>
                    Layer
                    {
                        point-file: url("file://%s/purple-point.png");
                    }
                </Stylesheet>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">file://%s/mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % (self.tmpdir1, self.tmpdir1)
        
        map = compile(mml_data, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (img_path, self.tmpdir1)
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (shp_path, self.tmpdir1)
        assert os.path.exists(shp_path)
    
    def testDotDotStylePaths(self):
        """ MML file is in a subdirectory, MSS is outside that subdirectory with relative resources.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir2, self.tmpdir1 + '/sub')
        
        mml_data = """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet src="../paths-test2.mss"/>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">file://%s/mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % self.tmpdir1
        
        map = compile(mml_data, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (img_path, self.tmpdir1)
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (shp_path, self.tmpdir1)
        assert os.path.exists(shp_path)
    
    def testSubdirStylePaths(self):
        """ MML file is in a directory, MSS is in a subdirectory with relative resources.
        """
        dirs = Directories(self.tmpdir2, self.tmpdir2, self.tmpdir1 + '/..')
        
        mml_data = """<?xml version="1.0" encoding="utf-8"?>
            <Map srs="+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null">
                <Stylesheet src="%s/paths-test2.mss"/>
                <Layer srs="+proj=latlong +ellps=WGS84 +datum=WGS84 +no_defs">
                    <Datasource>
                        <Parameter name="type">shape</Parameter>
                        <Parameter name="file">file://%s/mission-points</Parameter>
                    </Datasource>
                </Layer>
            </Map>
        """ % (os.path.basename(self.tmpdir1), self.tmpdir1)
        
        map = compile(mml_data, dirs)
        
        img_path = map.layers[0].styles[0].rules[0].symbolizers[0].file
        assert img_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (img_path, self.tmpdir1)
        assert os.path.exists(img_path)
        
        shp_path = map.layers[0].datasource.parameters['file'] + '.shp'
        assert shp_path.startswith(self.tmpdir1), 'Assert that "%s" starts with "%s"' % (shp_path, self.tmpdir1)
        assert os.path.exists(shp_path)
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = cascadenik-compile
#!/usr/bin/env python

import os
import sys
import shutil
import optparse
import tempfile
from os.path import realpath, dirname

import cascadenik
from cascadenik import mapnik

try:
    import xml.etree.ElementTree as ElementTree
    from xml.etree.ElementTree import Element
except ImportError:
    try:
        import lxml.etree as ElementTree
        from lxml.etree import Element
    except ImportError:
        import elementtree.ElementTree as ElementTree
        from elementtree.ElementTree import Element

def main(src_file, dest_file, **kwargs):
    """ Given an input layers file and a directory, print the compiled
        XML file to stdout and save any encountered external image files
        to the named directory.
    """
    mmap = mapnik.Map(1, 1)
    # allow [zoom] filters to work
    mmap.srs = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null'
    load_kwargs = dict([(k, v) for (k, v) in kwargs.items() if k in ('cache_dir', 'scale', 'verbose', 'datasources_cfg', 'user_styles')])
    cascadenik.load_map(mmap, src_file, dirname(realpath(dest_file)), **load_kwargs)
    
    (handle, tmp_file) = tempfile.mkstemp(suffix='.xml', prefix='cascadenik-mapnik-')
    os.close(handle)
    mapnik.save_map(mmap, tmp_file)
    
    if kwargs.get('pretty'):
        doc = ElementTree.fromstring(open(tmp_file, 'rb').read())
        cascadenik._compile.indent(doc)
        f = open(tmp_file, 'wb')
        ElementTree.ElementTree(doc).write(f)
        f.close()
        
    # manually unlinking seems to be required on windows
    if os.path.exists(dest_file):
        os.unlink(dest_file)

    os.chmod(tmp_file, 0666^os.umask(0))
    shutil.move(tmp_file, dest_file)
    return 0

parser = optparse.OptionParser(usage="""%prog [options] <mml> <xml>""", version='%prog ' + cascadenik.__version__)

parser.set_defaults(cache_dir=None, pretty=True, verbose=False, scale=1, user_styles=[], datasources_cfg=None)

# the actual default for cache_dir is handled in load_map(),
# to ensure that the mkdir behavior is correct.
parser.add_option('-c', '--cache-dir', dest='cache_dir',
                  help='Cache file-based resources (symbols, shapefiles, etc) to this directory. (default: %s)' % cascadenik.CACHE_DIR)

parser.add_option('-d' , '--datasources-config', dest='datasources_cfg',
                  help='Use the specified .cfg file to provide local overrides to datasources and variables.',
                  type="string")

parser.add_option('--srs', dest='srs',
                  help='Target srs for the compiled stylesheet. If provided, overrides default map srs in the mml. (default: None)')

parser.add_option('--2x', dest='scale', action='store_const', const=2,
                  help='Optionally scale all values (lengths and scale denominators) in output xml by two, suitable for display on high-resolution (e.g. iPhone) screens.')

parser.add_option('--style', dest='user_styles', action='append',
                  help='Look for additional styles in the named file, which will override anything provided in the MML. Any number of these can be provided.')

parser.add_option('-p', '--pretty', dest='pretty',
                  help='Pretty print the xml output. (default: True)',
                  action='store_true')

parser.add_option('-v' , '--verbose', dest='verbose',
                  help='Make a bunch of noise. (default: False)',
                  action='store_true')

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    
    if not len(args) == 2:
        parser.error('Please specify .mml and .xml files')

    layersfile, outputfile = args[0:2]
    
    print >> sys.stderr, 'output file:', outputfile, dirname(realpath(outputfile))

    if not layersfile.endswith('.mml'):
        parser.error('Input must be an .mml file')

    if not outputfile.endswith('.xml'):
        parser.error('Output must be an .xml file')

    sys.exit(main(layersfile, outputfile, **options.__dict__))

########NEW FILE########
__FILENAME__ = cascadenik-extract-dscfg
#!/usr/bin/env python

import os, sys
import math
import pprint
import urllib
import urlparse
import tempfile
import StringIO
import os.path
import zipfile
import itertools
import re
import ConfigParser
import codecs
import optparse

# Solves nasty problems:
# http://bytes.com/topic/python/answers/40109-missing-sys-setappdefaultencoding
reload(sys)
sys.setdefaultencoding('utf-8')

try:
    import lxml.etree as ElementTree
    from lxml.etree import Element, tostring
except ImportError:
    try:
        import xml.etree.ElementTree as ElementTree
        from xml.etree.ElementTree import Element, tostring
    except ImportError:
        import elementtree.ElementTree as ElementTree
        from elementtree.ElementTree import Element, tostring


standard_projections = {
    'srs900913' : '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs',
    'srsMerc' :  '+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs',
    'srs4326' : '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
}

        
def add_source(sources, ds_name, params):
    if ds_name not in sources:
        sources[ds_name] = params
        return ds_name
    op = sources[ds_name]
    c = 0
    while True:
        for k,v in op.items():
            # dicts are unequal
            if k not in params or op[k] != params[k]:
                c += 1
                nds_name = "%s_%d" % (ds_name, c)
                if nds_name in sources:
                    op = sources[nds_name] 
                    break
                sources[nds_name] = params
                return nds_name
            else: # equal, return!
                return ds_name


#
class MyConfigParser(ConfigParser.RawConfigParser):
    def write(self, fp):
        """Write an .ini-format representation of the configuration state."""
        if self._defaults:
            fp.write("[%s]\n" % ConfigParser.DEFAULTSECT)
            for (key, value) in sorted(self._defaults.items(), key=lambda x: x[0]):
                fp.write("%s = %s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in sorted(self._sections):
            fp.write("[%s]\n" % section)
            for (key, value) in sorted(self._sections[section].items(), key=lambda x: x[0]):
                if key != "__name__":
                    fp.write("%s = %s\n" %
                             (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")


def convert(src, outmml, outconfig, opts):
    if os.path.exists(src): # local file
        # using 'file:' enables support on win32
        # for opening local files with urllib.urlopen
        # Note: this must only be used with abs paths to local files
        # otherwise urllib will think they are absolute, 
        # therefore in the future it will likely be
        # wiser to just open local files with open()
        if os.path.isabs(src) and sys.platform == "win32":
            src = 'file:%s' % src

    
    doc = ElementTree.parse(urllib.urlopen(src))
    map = doc.getroot()
    
    defaults = standard_projections
    sources = {}
    
    all_srs = dict([(v,k) for k,v in standard_projections.items()])
    
    name_filter = re.compile("\W")
    
    for layer in map.findall("Layer"):
        if not opts.extract_all and layer.attrib.get('status',"on").lower() == "off":
            map.remove(layer)
            continue
        srs = layer.attrib['srs']
        srs_name = all_srs.get(srs)
        if not srs_name:
            srs_name = "srs%d"%len(all_srs)
            defaults[srs_name] = srs
            all_srs[srs] = srs_name

        id = layer.attrib.get('id')
        classes = layer.attrib.get('class') 
        keys = []
        if id:
            keys.append("%s_" % id)
        if classes:
            keys.extend(classes.split(" "))
        ds_name = name_filter.sub("_", " ".join(keys))
        
        
        params = {}
        for param in layer.find("Datasource").findall("Parameter"):
            params[param.attrib['name']] = param.text
        
        params.update(layer.find("Datasource").attrib)
        params['layer_srs'] = "%%(%s)s" % srs_name
        
        ds_name = add_source(sources, ds_name, params)
        
        layer.attrib['source_name'] = ds_name
        del layer.attrib['srs']
        layer.remove(layer.find("Datasource"))

    # now generate unique bases
    g_params = {}
    
    for name, params in sources.items():
        gp = {}
        name_base = None
        if params.get('type') == 'postgis':
            param_set = ("port","host","user","layer_srs","password","type","dbname","estimate_extent","extent")
            name_base = "postgis_conn_%d"
#        elif params.get('type') == 'shape':
#            param_set = ("type","file","source_srs")
#            name_base = "shapefile_%d"
        else:
            continue

        for p in param_set:
            if p in params:
                gp[p] = params[p]
                del params[p]
                
        gp_name,gp_data = g_params.get(repr(gp),(None,None))        
        if not gp_name:
            gp_name = name_base % len(g_params)
            g_params[repr(gp)] = gp_name,gp
        
        params['template'] = gp_name
        
    config = MyConfigParser(defaults)     
    
    for name,params in itertools.chain(g_params.values(), sources.items()):
        config.add_section(name)
        for pn,pv in params.items():
            if pn == 'table': pv = pv.strip()
            config.set(name,pn,pv)
    with codecs.open(outconfig,"w","utf-8") as oc:
        config.write(oc)
    
    map.insert(0,Element("DataSourcesConfig", src=outconfig))
    doc.write(outmml, encoding="utf8")

    


        
if __name__ == "__main__":
    parser = optparse.OptionParser(usage= "usage: %s [options] <source.mml> <output.mml> <output.cfg>" % sys.argv[0])

    parser.add_option('-a', '--all', dest='extract_all', default=False, action="store_true",
                      help='Include disabled layers')

    (options, args) = parser.parse_args()
    if len(args) != 3:
        parser.error("Please specify <source.mml> <output.mml> <output.cfg>")
    
    inmml, outmml, outcfg = args
    convert(inmml, outmml, outcfg, options)

        

########NEW FILE########
__FILENAME__ = cascadenik-style
#!/usr/bin/env python

import sys
import os.path
import optparse
import cascadenik

# monkey with sys.path due to some weirdness inside cssutils
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from cssutils.tokenize2 import Tokenizer as cssTokenizer

def main(filename):
    """ Given an input file containing nothing but styles, print out an
        unrolled list of declarations in cascade order.
    """
    input = open(filename, 'r').read()
    declarations = cascadenik.stylesheet_declarations(input, is_merc=True)
    
    for dec in declarations:
        print dec.selector,
        print '{',
        print dec.property.name+':',
        
        if cascadenik.style.properties[dec.property.name] in (cascadenik.style.color, cascadenik.style.boolean, cascadenik.style.numbers):
            print str(dec.value.value)+';',
        
        elif cascadenik.style.properties[dec.property.name] is cascadenik.style.uri:
            print 'url("'+str(dec.value.value)+'");',
        
        elif cascadenik.style.properties[dec.property.name] is str:
            print '"'+str(dec.value.value)+'";',
        
        elif cascadenik.style.properties[dec.property.name] in (int, float) or type(cascadenik.style.properties[dec.property.name]) is tuple:
            print str(dec.value.value)+';',
        
        print '}'
    
    return 0

parser = optparse.OptionParser(usage="""cascadenik-style.py <style file>""")

if __name__ == '__main__':
    (options, args) = parser.parse_args()
    if not args:
        parser.error('Please specify a .mss file')
    stylefile = args[0]
    if not stylefile.endswith('.mss'):
        parser.error('Only accepts an .mss file')
    sys.exit(main(stylefile))

########NEW FILE########
