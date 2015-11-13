__FILENAME__ = boundaries
#!/usr/bin/env python

import xml.sax, os, errno, urllib, urllib2, sys, datetime, time, shutil
from xml.sax.handler import ContentHandler
import yaml
from lxml import etree
from tempfile import mkdtemp, NamedTemporaryFile
from StringIO import StringIO
from subprocess import Popen, PIPE

with open(os.path.join(
        os.path.dirname(__file__), '..', 'conf', 'general.yml')) as f:
    config = yaml.load(f)

# Suggested by http://stackoverflow.com/q/600268/223092
def mkdir_p(path):
    """Create a directory (and parents if necessary) like mkdir -p

    For example:

    >>> test_directory = mkdtemp()
    >>> new_directory = os.path.join(test_directory, "foo", "bar")
    >>> mkdir_p(new_directory)
    >>> os.path.exists(new_directory)
    True
    >>> os.path.isdir(new_directory)
    True

    There should be no error if the directory already exists:

    >>> mkdir_p(new_directory)

    But if there is another error, e.g. permissions prevent the
    directory from being created:

    >>> os.chmod(new_directory, 0)
    >>> new_subdirectory = os.path.join(new_directory, "baz")
    >>> mkdir_p(new_subdirectory) #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
      ...
    OSError: [Errno 13] Permission denied: '/tmp/tmp64Q8MJ/foo/bar/baz'

    Remove the temporary directory created for these doctests:
    >>> os.chmod(new_directory, 0755)
    >>> shutil.rmtree(test_directory)
    """

    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise

def get_query_relation_and_dependents(element_type, element_id):
    return """<osm-script timeout="3600">
  <union into="_">
    <id-query into="_" ref="%s" type="%s"/>
    <recurse from="_" into="_" type="down"/>
  </union>
  <print from="_" limit="" mode="body" order="id"/>
</osm-script>
""" % (element_id, element_type)

def get_query_relations_and_ways(required_tags):
    has_kv = "\n".join('      <has-kv k="%s" modv="" v="%s"/>' % (k,v)
                       for k, v in required_tags.items())
    return """<osm-script timeout="3600">
  <union into="_">
    <query into="_" type="relation">
%s
    </query>
    <query into="_" type="way">
%s
    </query>
  </union>
  <print from="_" limit="" mode="body" order="id"/>
</osm-script>""" % (has_kv, has_kv)

def get_from_overpass(query_xml, filename):
    if not os.path.exists(filename):
        if config.get('LOCAL_OVERPASS'):
            return get_osm3s(query_xml, filename)
        else:
            return get_remote(query_xml, filename)

def get_osm3s(query_xml, filename):
    with open(filename, 'w') as file_output:
        p = Popen(["osm3s_query",
                   "--concise",
                   "--db-dir=" + config['OVERPASS_DB_DIRECTORY']],
                  stdin=PIPE,
                  stdout=file_output)
        p.communicate(query_xml)
        if p.returncode != 0:
            raise Exception, "The osm3s_query failed"

def get_remote(query_xml, filename):
    url = config['OVERPASS_SERVER']
    values = {'data': query_xml}
    encoded_values = urllib.urlencode(values)
    request = urllib2.Request(url, encoded_values)
    response = urllib2.urlopen(request)
    with open(filename, "w") as fp:
        fp.write(response.read())

def get_cache_filename(element_type, element_id, cache_directory=None):
    if cache_directory is None:
        script_directory = os.path.dirname(os.path.abspath(__file__))
        cache_directory = os.path.join(script_directory,
                                       '..',
                                       'data',
                                       'new-cache')
    element_id = int(element_id, 10)
    subdirectory = "%03d" % (element_id % 1000,)
    full_subdirectory = os.path.join(cache_directory,
                                     element_type,
                                     subdirectory)
    mkdir_p(full_subdirectory)
    basename = "%s-%d.xml" % (element_type, element_id)
    return os.path.join(full_subdirectory, basename)

def get_name_from_tags(tags, element_type=None, element_id=None):
    """Given an OSMElement, return a readable name if possible

    If there's a name tag (typically the local spelling of the
    element), then use that:

    >>> tags = {'name': 'Deutschland',
    ...         'name:en': 'Federal Republic of Germany'}
    >>> get_name_from_tags(tags, 'relation', '51477')
    'Deutschland'

    Or fall back to the English name, if that's the only option:

    >>> tags = {'name:en': 'Freedonia', 'relation': '345678'}
    >>> get_name_from_tags(tags)
    'Freedonia'

    Otherwise, use the type and ID to form a readable name:

    >>> get_name_from_tags({}, 'node', '65432')
    'Unknown name for node with ID 65432'

    Or if we've no information at all, just return 'Unknown':

    >>> get_name_from_tags({})
    'Unknown'

    """

    if 'name' in tags:
        return tags['name']
    elif 'name:en' in tags:
        return tags['name:en']
    elif 'place_name' in tags:
        return tags['place_name']
    elif element_type and element_id:
        return "Unknown name for %s with ID %s" % (element_type, element_id)
    else:
        return "Unknown"

def get_non_contained_elements(elements):
    """Filter elements, keeping only those which are not a member of another

    As an example, you can do the following:

    >>> top = Relation("13")
    >>> sub = Relation("14")
    >>> top.children.append((sub, ''))
    >>> lone = Way("15")
    >>> get_non_contained_elements([top, sub, lone])
    [Relation(id="13", members=1), Way(id="15", nodes=0)]


    """
    contained_elements = set([])
    for e in elements:
        if e.element_type == "relation":
            for member, role in e:
                contained_elements.add(member)
    return [e for e in elements if e not in contained_elements]

class OSMElement(object):

    def __init__(self, element_id, element_content_missing=False, element_type=None):
        self.element_id = element_id
        self.element_type = element_type or "BUG"
        self.missing = element_content_missing

    def __lt__(self, other):
        return int(self.element_id, 10) < int(other.element_id, 10)

    def __eq__(self, other):
        """Define equality of OSMElements as same (OSM) type and ID

        For example, they should be equal even if one is of the base
        class and one the subclass:

        >>> missing = OSMElement('42', element_content_missing=True, element_type='node')
        >>> real = Node('42')
        >>> missing == real
        True

        But non-OSMElements aren't equal:

        >>> real == ('node', '42')
        False

        And elements of different type aren't equal:
        >>> real == Relation('42')
        False

        """
        if not isinstance(other, OSMElement):
            return False
        if self.element_type == other.element_type:
            return self.element_id == other.element_id
        return False

    def __ne__(self, other):
        """Inequality is just the negation of equality

        >>> Node('42') != Relation('42')
        True

        >>> Node('42') != Node('8')
        True

        """
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.element_id)

    def name_id_tuple(self):
        """Return the OSM type and ID as a tuple

        This is sometimes useful for a lower-memory representation of
        elements.  (Debatably - this should be considered for removal.)
        FIXME: also should rename this to type_id_tuple

        >>> n = Node('123456', latitude="52", longitude="0")
        >>> n.tags['name'] = 'Cambridge'
        >>> n.name_id_tuple()
        ('node', '123456')
        """

        return (self.element_type, self.element_id)

    def get_name(self):
        """Get a human-readable name for the element, if possible

        >>> germany = Relation("51477")
        >>> tags = {'name': 'Deutschland',
        ...         'name:en': 'Federal Republic of Germany'}
        >>> germany.tags.update(tags)
        >>> germany.get_name()
        'Deutschland'
        """
        return get_name_from_tags(self.tags, self.element_type, self.element_id)

    @property
    def element_content_missing(self):
        return self.missing

    @staticmethod
    def make_missing_element(element_type, element_id):
        """Create an element for which we only know the type and ID

        It is useful to be able to represent OSM elements that we've
        just seen mentioned as members of relations, but haven't
        actually parsed.  You can use this static method to create a
        node of such a type:

        >>> OSMElement.make_missing_element('node', '42')
        Node(id="42", missing)
        >>> OSMElement.make_missing_element('way', '7')
        Way(id="7", missing)
        >>> OSMElement.make_missing_element('relation', '13')
        Relation(id="13", missing)
        >>> OSMElement.make_missing_element('other', '2')
        Traceback (most recent call last):
          ...
        Exception: Unknown element name 'other'
        """

        if element_type == "node":
            return Node(element_id, element_content_missing=True)
        elif element_type == "way":
            return Way(element_id, element_content_missing=True)
        elif element_type == "relation":
            return Relation(element_id, element_content_missing=True)
        else:
            raise Exception, "Unknown element name '%s'" % (element_type,)

    def __repr__(self):
        """A returns simple repr-style representation of the OSMElement

        For example:

        >>> OSMElement('23', element_type='node')
        OSMElement(id="23", type="node")

        >>> OSMElement('25', element_content_missing=True, element_type='relation')
        OSMElement(id="25", type="relation", missing)
        """

        if self.element_content_missing:
            return 'OSMElement(id="%s", type="%s", missing)' % (self.element_id,
                                                                self.element_type)
        else:
            return 'OSMElement(id="%s", type="%s")' % (self.element_id,
                                                       self.element_type)

    def get_missing_elements(self, to_append_to=None):
        """Return a list of element type, id tuples of missing elements

        In the case of an element without children, this should either
        return an empty list or a list with this element in it,
        depending on whether it's marked as missing or not:

        >>> missing = OSMElement('42', element_content_missing=True, element_type="node")
        >>> missing.get_missing_elements()
        [('node', '42')]
        >>> present = OSMElement('42', element_type="node")
        >>> present.get_missing_elements()
        []

        If to_append_to is supplied, the missing elements should be
        appended to that array, and the same array returned:

        >>> l = []
        >>> result = missing.get_missing_elements(l)
        >>> l is result
        True
        >>> l
        [('node', '42')]
        """
        if to_append_to is None:
            to_append_to = []
        if self.element_content_missing:
            to_append_to.append(self.name_id_tuple())
        return to_append_to

    @staticmethod
    def xml_wrapping():
        """Get an XML element that OSM nodes/ways/relations can be added to

        The returned object is an etree.Element, which can be
        pretty-printed with etree.tostring:

        >>> print etree.tostring(OSMElement.xml_wrapping(), pretty_print=True),
        <osm version="0.6" generator="mySociety Boundary Extractor">
          <note>The data included in this document is from www.openstreetmap.org. It has there been collected by a large group of contributors. For individual attribution of each item please refer to http://www.openstreetmap.org/api/0.6/[node|way|relation]/#id/history</note>
        </osm>
        """

        osm = etree.Element("osm", attrib={"version": "0.6",
                                           "generator": "mySociety Boundary Extractor"})
        note = etree.SubElement(osm, "note")
        note.text = "The data included in this document is from www.openstreetmap.org. It has there been collected by a large group of contributors. For individual attribution of each item please refer to http://www.openstreetmap.org/api/0.6/[node|way|relation]/#id/history"
        return osm

    def xml_add_tags(self, xml_element):
        """Add the tags from this OSM element to an XML element

        >>> n = Node('42')
        >>> n.tags.update({'name': 'Venezia',
        ...                'name:en': 'Venice'})
        >>> xe = etree.Element('example')
        >>> n.xml_add_tags(xe)
        >>> print etree.tostring(xe, pretty_print=True),
        <example>
          <tag k="name" v="Venezia"/>
          <tag k="name:en" v="Venice"/>
        </example>
        """

        for k, v in sorted(self.tags.items()):
            etree.SubElement(xml_element, 'tag', attrib={'k': k, 'v': v})

class Node(OSMElement):

    """Represents an OSM node

    You can create a complete node as follows:

    >>> cambridge = Node("12345", latitude="52.205", longitude="0.119")
    >>> cambridge
    Node(id="12345", lat="52.205", lon="0.119")

    Each node has a tags attribute as well:
    >>> cambridge.tags['name:en'] = "Cambridge"

    The tags can be seen with the .pretty() representation:

    >>> print cambridge.pretty(4)
        node (12345) lat: 52.205, lon: 0.119
          name:en => Cambridge

    If you only know the ID of the node, but not its latitude or
    longitude yet, you can create it as a 'missing' node with a
    static method from OSMElement:

    >>> missing = OSMElement.make_missing_element("node", "321")
    >>> missing
    Node(id="321", missing)

    """

    def __init__(self, node_id, latitude=None, longitude=None, element_content_missing=False):
        super(Node, self).__init__(node_id, element_content_missing, 'node')
        self.lat = latitude
        self.lon = longitude
        self.tags = {}

    def pretty(self, indent=0):
        i = u" "*indent
        result = i + u"node (%s) lat: %s, lon: %s" % (self.element_id, self.lat, self.lon)
        for k, v in sorted(self.tags.items()):
            result += u"\n%s  %s => %s" % (i, k, v)
        return result

    def lon_lat_tuple(self):
        """Return the latitude and longitude as a tuple of two strings

        >>> n = Node("1234", latitude="52", longitude="0.5")
        >>> n.lon_lat_tuple()
        ('0.5', '52')
        """
        return (self.lon, self.lat)

    def __repr__(self):
        if self.element_content_missing:
            return 'Node(id="%s", missing)' % (self.element_id)
        else:
            return 'Node(id="%s", lat="%s", lon="%s")' % (self.element_id,
                                                          self.lat,
                                                          self.lon)

    def to_xml(self, parent_element=None, include_node_dependencies=False):
        """Generate an XML element representing this node

        If parent_element is supplied, it is added to that element and
        returned.  If no parent_element is supplied, an OSM XML root
        element is created, and the generated <node> element is added
        to that.

        >>> n = Node("1234", latitude="51.2", longitude="-0.2")
        >>> parent = etree.Element('example')
        >>> result = n.to_xml(parent_element=parent)
        >>> parent is result
        True
        >>> print etree.tostring(parent, pretty_print=True),
        <example>
          <node lat="51.2" lon="-0.2" id="1234"/>
        </example>
        >>> full_result = n.to_xml()
        >>> print etree.tostring(full_result, pretty_print=True),
        <osm version="0.6" generator="mySociety Boundary Extractor">
          <note>The data included in this document is from www.openstreetmap.org. It has there been collected by a large group of contributors. For individual attribution of each item please refer to http://www.openstreetmap.org/api/0.6/[node|way|relation]/#id/history</note>
          <node lat="51.2" lon="-0.2" id="1234"/>
        </osm>
        """

        if parent_element is None:
            parent_element = OSMElement.xml_wrapping()
        node = etree.SubElement(parent_element,
                                'node',
                                attrib={'id': self.element_id,
                                        'lat': self.lat,
                                        'lon': self.lon})
        self.xml_add_tags(node)
        return parent_element

class Way(OSMElement):

    """Represents an OSM way as returned via the Overpass API

    You can create a Way object as follows:

    >>> Way("314159265")
    Way(id="314159265", nodes=0)

    Or supply a list of nodes:

    >>> top_left = Node("12", latitude="52", longitude="1")
    >>> top_right = Node("13", latitude="52", longitude="2")
    >>> bottom_right = Node("14", latitude="51", longitude="2")
    >>> bottom_left = Node("15", latitude="51", longitude="1")

    >>> ns = [top_left,
    ...       top_right,
    ...       bottom_right,
    ...       bottom_left]
    >>> unclosed = Way("314159265", ns)
    >>> unclosed
    Way(id="314159265", nodes=4)

    You can iterate over the nodes:

    >>> for n in unclosed:
    ...     print n
    Node(id="12", lat="52", lon="1")
    Node(id="13", lat="52", lon="2")
    Node(id="14", lat="51", lon="2")
    Node(id="15", lat="51", lon="1")

    Or test if a node is closed or not:

    >>> unclosed.closed()
    False
    >>> nsc = ns + [top_left]
    >>> closed = Way("98765", nodes=nsc)
    >>> closed.closed()
    True

    """

    def __init__(self, way_id, nodes=None, element_content_missing=False):
        super(Way, self).__init__(way_id, element_content_missing, 'way')
        self.nodes = nodes or []
        self.tags = {}

    def __iter__(self):
        for n in self.nodes:
            yield n

    def __len__(self):
        """Allow len(way) to return the number of nodes

        For example:

        >>> w = Way("1", nodes=[Node("12", latitude="52", longitude="1"),
        ...                     Node("13", latitude="52", longitude="2"),
        ...                     Node("14", latitude="51", longitude="2")])
        >>> len(w)
        3
        """
        return len(self.nodes)

    def __getitem__(self, val):
        """Allow access to nodes with array notation

        For example:
        >>> w = Way('76543', nodes=[Node("12", latitude="52", longitude="1"),
        ...                         Node("13", latitude="52", longitude="2"),
        ...                         Node("14", latitude="51", longitude="2")])
        >>> w[2]
        Node(id="14", lat="51", lon="2")
        """
        return self.nodes.__getitem__(val)

    def pretty(self, indent=0):
        """Generate a fuller string representation of this way

        For example:

        >>> w = Way('76543', nodes=[Node("12", latitude="52", longitude="1"),
        ...                         Node("13", latitude="52", longitude="2"),
        ...                         Node("14", latitude="51", longitude="1"),
        ...                         Node("15", latitude="51", longitude="2")])
        >>> w.tags['random_key'] = 'some value or other'
        >>> w.tags['boundary'] = 'administrative'
        >>> print w.pretty(2)
          way (76543)
            boundary => administrative
            random_key => some value or other
            node (12) lat: 52, lon: 1
            node (13) lat: 52, lon: 2
            node (14) lat: 51, lon: 1
            node (15) lat: 51, lon: 2
        """

        i = u" "*indent
        result = i + u"way (%s)" % (self.element_id)
        for k, v in sorted(self.tags.items()):
            result += u"\n%s  %s => %s" % (i, k, v)
        for node in self.nodes:
            result += u"\n" + node.pretty(indent + 2)
        return result

    @property
    def first(self):
        return self.nodes[0]

    @property
    def last(self):
        return self.nodes[-1]

    def closed(self):
        return self.first == self.last

    def join(self, other):
        """Try to join another way to this one.

        This will succeed if they can be joined at either end, and
        otherwise returns None.

        As examples, consider joining two edges of a square in various
        ways:

             top_left -- top_right

                 |           |

          bottom_left -- bottom_right

        In the examples below, we try to join the top edge to the
        right in four distinct ways:

        >>> top_left = Node("12", latitude="52", longitude="1")
        >>> top_right = Node("13", latitude="52", longitude="2")
        >>> bottom_right = Node("14", latitude="51", longitude="2")
        >>> bottom_left = Node("15", latitude="51", longitude="1")

        >>> top_cw = Way("3456", nodes=[top_left, top_right])
        >>> right_cw = Way("1234", nodes=[top_right, bottom_right])
        >>> bottom_cw = Way("6789", nodes=[bottom_right, bottom_left])

        >>> joined = top_cw.join(right_cw)
        >>> print joined.pretty(2)
          way (None)
            node (12) lat: 52, lon: 1
            node (13) lat: 52, lon: 2
            node (14) lat: 51, lon: 2

        >>> top_ccw = Way("4567", nodes=[top_right, top_left])
        >>> joined = top_ccw.join(right_cw)
        >>> print joined.pretty(2)
          way (None)
            node (14) lat: 51, lon: 2
            node (13) lat: 52, lon: 2
            node (12) lat: 52, lon: 1

        >>> right_ccw = Way("2345", nodes=[bottom_right, top_right])
        >>> joined = top_ccw.join(right_ccw)
        >>> print joined.pretty(2)
          way (None)
            node (14) lat: 51, lon: 2
            node (13) lat: 52, lon: 2
            node (12) lat: 52, lon: 1

        >>> joined = top_cw.join(right_ccw)
        >>> print joined.pretty(2)
          way (None)
            node (12) lat: 52, lon: 1
            node (13) lat: 52, lon: 2
            node (14) lat: 51, lon: 2

        Closed ways cannot be joined, and throw exceptions as in these
        examples:

        >>> closed = Way("5678", nodes=[top_left,
        ...                             top_right,
        ...                             bottom_right,
        ...                             bottom_left,
        ...                             top_left])
        >>> joined = closed.join(top_cw)
        Traceback (most recent call last):
           ...
        Exception: Trying to join a closed way to another

        >>> closed = Way("5678", nodes=[top_left,
        ...                             top_right,
        ...                             bottom_right,
        ...                             bottom_left,
        ...                             top_left])
        >>> joined = top_cw.join(closed)
        Traceback (most recent call last):
           ...
        Exception: Trying to join a way to a closed way

        Finally, an exception is also thrown if there are no end
        points in common between the two ways:

        >>> top_cw.join(bottom_cw)
        Traceback (most recent call last):
           ...
        Exception: Trying to join two ways with no end point in common
        """

        if self.closed():
            raise Exception, "Trying to join a closed way to another"
        if other.closed():
            raise Exception, "Trying to join a way to a closed way"
        if self.first == other.first:
            new_nodes = list(reversed(other.nodes))[0:-1] + self.nodes
        elif self.first == other.last:
            new_nodes = other.nodes[0:-1] + self.nodes
        elif self.last == other.first:
            new_nodes = self.nodes[0:-1] + other.nodes
        elif self.last == other.last:
            new_nodes = self.nodes[0:-1] + list(reversed(other.nodes))
        else:
            raise Exception, "Trying to join two ways with no end point in common"
        return Way(None, new_nodes)

    def bounding_box_tuple(self):
        """Returns a tuple of floats representing a bounding box of this Way

        Each tuple is (min_lat, min_lon, max_lat, max_lon).  If the
        longitude of any node is less than -90 degrees, 360 is added
        to every node, to deal with ways that cross the -180 degree
        meridian.

        >>> w = Way('76543', nodes=[Node("12", latitude="52", longitude="1"),
        ...                         Node("13", latitude="52", longitude="2"),
        ...                         Node("14", latitude="51", longitude="1"),
        ...                         Node("15", latitude="51", longitude="2")])
        >>> w.bounding_box_tuple()
        (51.0, 1.0, 52.0, 2.0)

        As another example close to the -180 degree meridian, create a
        closed way somewhere in Alaska:


        >>> w = Way('76543', nodes=[Node("12", latitude="62", longitude="-149"),
        ...                         Node("13", latitude="62", longitude="-150"),
        ...                         Node("14", latitude="61", longitude="-149"),
        ...                         Node("15", latitude="61", longitude="-150")])
        >>> w.bounding_box_tuple()
        (61.0, 210.0, 62.0, 211.0)



        """

        longitudes = [float(n.lon) for n in self]
        latitudes = [float(n.lat) for n in self]

        if any(x for x in longitudes if x < -90):
            longitudes = [x + 360 for x in longitudes]

        min_lon = min(longitudes)
        max_lon = max(longitudes)

        min_lat = min(latitudes)
        max_lat = max(latitudes)

        return (min_lat, min_lon, max_lat, max_lon)

    def __repr__(self):
        """A returns simple repr-style representation of the Way

        >>> Way('81')
        Way(id="81", nodes=0)
        >>> OSMElement.make_missing_element('way', '49')
        Way(id="49", missing)
        """

        if self.element_content_missing:
            return 'Way(id="%s", missing)' % (self.element_id,)
        else:
            return 'Way(id="%s", nodes=%d)' % (self.element_id, len(self.nodes))

    def get_missing_elements(self, to_append_to=None):
        """Return a list of element type, id tuples of missing elements

        In the case of an element without children, this should either
        return an empty list or a list with this element in it,
        depending on whether it's marked as missing or not:

        >>> nodes = [OSMElement.make_missing_element('node', '43'),
        ...          Node('44'),
        ...          Node('45'),
        ...          OSMElement.make_missing_element('node', '46')]
        >>> w = Way("42", nodes=nodes)
        >>> w.get_missing_elements()
        [('node', '43'), ('node', '46')]

        >>> l = [('relation', '47')]
        >>> result = w.get_missing_elements(l)
        >>> l is result
        True
        >>> l
        [('relation', '47'), ('node', '43'), ('node', '46')]
        """

        to_append_to = OSMElement.get_missing_elements(self, to_append_to)
        for node in self:
            node.get_missing_elements(to_append_to)
        return to_append_to

    def to_xml(self, parent_element=None, include_node_dependencies=False):
        """Generate an XML element representing this way

        If parent_element is supplied, it is added to that element and
        returned.  If no parent_element is supplied, an OSM XML root
        element is created, and the generated <node> element is added
        to that.

        >>> w = Way('76543', nodes=[Node("12", latitude="52", longitude="1"),
        ...                         Node("13", latitude="52", longitude="2"),
        ...                         Node("14", latitude="51", longitude="1"),
        ...                         Node("15", latitude="51", longitude="2")])
        >>> w.tags.update({'boundary': 'administrative',
        ...                'admin_level': '2'})
        >>> xe = etree.Element('example')
        >>> result = w.to_xml(xe)
        >>> result is xe
        True
        >>> print etree.tostring(xe, pretty_print=True),
        <example>
          <way id="76543">
            <nd ref="12"/>
            <nd ref="13"/>
            <nd ref="14"/>
            <nd ref="15"/>
            <tag k="admin_level" v="2"/>
            <tag k="boundary" v="administrative"/>
          </way>
        </example>

        Sometimes we'd like to output the nodes that are in a way at the same time:

        >>> xe = etree.Element('example-with-nodes')
        >>> w.to_xml(xe, include_node_dependencies=True) #doctest: +ELLIPSIS
        <Element example-with-nodes at ...>
        >>> print etree.tostring(xe, pretty_print=True),
        <example-with-nodes>
          <node lat="52" lon="1" id="12"/>
          <node lat="52" lon="2" id="13"/>
          <node lat="51" lon="1" id="14"/>
          <node lat="51" lon="2" id="15"/>
          <way id="76543">
            <nd ref="12"/>
            <nd ref="13"/>
            <nd ref="14"/>
            <nd ref="15"/>
            <tag k="admin_level" v="2"/>
            <tag k="boundary" v="administrative"/>
          </way>
        </example-with-nodes>

        And the final option is to include the OSM XML boilerplate as well:

        >>> result = w.to_xml()
        >>> print etree.tostring(result, pretty_print=True),
        <osm version="0.6" generator="mySociety Boundary Extractor">
          <note>The data included in this document is from www.openstreetmap.org. It has there been collected by a large group of contributors. For individual attribution of each item please refer to http://www.openstreetmap.org/api/0.6/[node|way|relation]/#id/history</note>
          <way id="76543">
            <nd ref="12"/>
            <nd ref="13"/>
            <nd ref="14"/>
            <nd ref="15"/>
            <tag k="admin_level" v="2"/>
            <tag k="boundary" v="administrative"/>
          </way>
        </osm>
        """

        if parent_element is None:
            parent_element = OSMElement.xml_wrapping()
        if include_node_dependencies:
            for node in self:
                node.to_xml(parent_element, include_node_dependencies)
        way = etree.SubElement(parent_element,
                               'way',
                               attrib={'id': self.element_id})
        for node in self:
            etree.SubElement(way, 'nd', attrib={'ref': node.element_id})
        self.xml_add_tags(way)
        return parent_element

    def reconstruct_missing(self, parser, id_to_node):
        """Replace any missing nodes from the parser's cache or id_to_node

        id_to_node should be a dictionary that maps IDs of nodes (as
        strings) the complete Node object or None.  parser should have
        a method called get_known_or_fetch('node', element_id) which
        will return None or the complete Node object, if the parser
        can find it.

        If any nodes could not be found from parser or id_to_node,
        they are returned as a list.  Therefore, if the way could be
        completely reconstructed, [] will be returned.

        >>> w = Way('76543', nodes=[Node("12", latitude="52", longitude="1"),
        ...                         OSMElement.make_missing_element('node', '13'),
        ...                         OSMElement.make_missing_element('node', '14'),
        ...                         Node("15", latitude="51", longitude="2")])
        >>> class FakeParser:
        ...     def get_known_or_fetch(self, element_type, element_id):
        ...         if element_type != 'node':
        ...             return None
        ...         if element_id == "14":
        ...             return Node("14", latitude="52.4", longitude="2.1")
        ...         return None
        >>> node_cache = {"13": Node("13", latitude="51.2", longitude="1.3"),
        ...               "22": None}
        >>> w.reconstruct_missing(FakeParser(), node_cache)
        []

        >>> w = Way('76543', nodes=[Node("21", latitude="52", longitude="1"),
        ...                         OSMElement.make_missing_element('node', '22'),
        ...                         OSMElement.make_missing_element('node', '23'),
        ...                         Node("24", latitude="51", longitude="2")])
        >>> w.reconstruct_missing(FakeParser(), node_cache)
        [Node(id="22", missing), Node(id="23", missing)]
        """

        still_missing = []
        for i, node in enumerate(self.nodes):
            if not node.element_content_missing:
                continue
            node_id = node.element_id
            found_node = None
            if node_id in id_to_node:
                found_node = id_to_node[node_id]
            else:
                # Ask the parser to try to fetch it from its filesystem cache:
                found_node = parser.get_known_or_fetch('node', node_id)
            if (found_node is not None) and (not found_node.element_content_missing):
                self.nodes[i] = found_node
            else:
                still_missing.append(node)
        return still_missing

class Relation(OSMElement):

    """Represents an OSM relation as returned via the Overpass API"""

    def __init__(self, relation_id, element_content_missing=False):
        super(Relation, self).__init__(relation_id, element_content_missing, 'relation')
        # A relation has an ordered list of children, which we store
        # as a list of tuples.  The first element of each tuple is a
        # Node, Way or Relation, and the second is a "role" string.
        self.children = []
        self.tags = {}

    def __iter__(self):
        for c in self.children:
            yield c

    def __len__(self):
        return len(self.children)

    def __getitem__(self, val):
        return self.children.__getitem__(val)

    def add_member(self, new_member, role=''):
        self.children.append((new_member, role))

    def pretty(self, indent=0):
        """Generate a fuller string representation of this way

        For example:

        >>> r = Relation('98765')
        >>> r.add_member(Node('76542', latitude="51.0", longitude="0.3"))
        >>> r.add_member(Way('76543'))
        >>> r.add_member(Way('76544'), role='inner')
        >>> r.add_member(Way('76545'), role='inner')
        >>> r.add_member(Way('76546'))
        >>> r.tags['random_key'] = 'some value or other'
        >>> r.tags['boundary'] = 'administrative'
        >>> print r.pretty(2)
          relation (98765)
            boundary => administrative
            random_key => some value or other
            child node with role ''
              node (76542) lat: 51.0, lon: 0.3
            child way with role ''
              way (76543)
            child way with role 'inner'
              way (76544)
            child way with role 'inner'
              way (76545)
            child way with role ''
              way (76546)
        """

        i = u" "*indent
        result = i + u"relation (%s)" % (self.element_id)
        for k, v in sorted(self.tags.items()):
            result += u"\n%s  %s => %s" % (i, k, v)
        for child, role in self.children:
            result += u"\n%s  child %s" % (i, child.element_type)
            result += u" with role '%s'" % (role)
            result += u"\n" + child.pretty(indent + 4)
        return result

    def way_iterator(self, inner=False):
        """Iterate over the ways in this relation

        If inner is set, iterate only over ways with the roles 'inner'
        or 'enclave' - otherwise miss them out.

        For example:

        >>> subr1 = Relation('98764')
        >>> subr1.add_member(Way('54319'), role='inner')
        >>> subr1.add_member(Way('54320'))

        >>> subr2 = Relation('87654')
        >>> subr2.add_member(Way('54321'))
        >>> subr2.add_member(Way('54322'), role='inner')

        >>> r = Relation('98765')
        >>> r.add_member(Node('76542', latitude="51.0", longitude="0.3"))
        >>> r.add_member(Way('76543'))
        >>> r.add_member(subr1)
        >>> r.add_member(Way('76544'), role='inner')
        >>> r.add_member(Way('76545'), role='inner')
        >>> r.add_member(subr2, role='inner')
        >>> r.add_member(Way('76546'))

        >>> for w in r.way_iterator():
        ...     print w
        Way(id="76543", nodes=0)
        Way(id="54320", nodes=0)
        Way(id="76546", nodes=0)

        >>> for w in r.way_iterator(inner=True):
        ...     print w
        Way(id="76544", nodes=0)
        Way(id="76545", nodes=0)
        Way(id="54322", nodes=0)
        """

        for child, role in self.children:
            if inner:
                if role not in ('enclave', 'inner'):
                    continue
            else:
                if role and role != 'outer':
                    continue
            if child.element_type == 'way':
                yield child
            elif child.element_type == 'relation':
                for sub_way in child.way_iterator(inner):
                    yield sub_way

    def __repr__(self):
        """A returns simple repr-style representation of the OSMElement

        For example:

        >>> Relation('6')
        Relation(id="6", members=0)

        >>> OSMElement.make_missing_element('relation', '7')
        Relation(id="7", missing)
        """

        if self.element_content_missing:
            return 'Relation(id="%s", missing)' % (self.element_id,)
        else:
            return 'Relation(id="%s", members=%d)' % (self.element_id, len(self.children))

    def get_missing_elements(self, to_append_to=None):
        """Return a list of element type, id tuples of missing elements

        In the case of an element without children, this should either
        return an empty list or a list with this element in it,
        depending on whether it's marked as missing or not:

        >>> r1 = Relation('77')
        >>> r1.get_missing_elements()
        []
        >>> r2 = OSMElement.make_missing_element('relation', '78')
        >>> r2.get_missing_elements()
        [('relation', '78')]

        >>> subr1 = Relation('98764')
        >>> subr1.add_member(Way('54319'), role='inner')
        >>> subr1.add_member(OSMElement.make_missing_element('relation', '54320'))
        >>> subr1.add_member(OSMElement.make_missing_element('way', '54321'))

        >>> subr2 = Relation('87654')
        >>> subr2.add_member(Way('54322'))
        >>> subr2.add_member(Way('54323'), role='inner')

        >>> r = Relation('98765')
        >>> r.add_member(OSMElement.make_missing_element('node', '76542'))
        >>> r.add_member(Way('76543'))
        >>> r.add_member(subr1)
        >>> r.add_member(OSMElement.make_missing_element('way', '98764'))
        >>> r.add_member(Way('76545'), role='inner')
        >>> r.add_member(subr2, role='inner')
        >>> r.add_member(Way('76546'))

        >>> r.get_missing_elements()
        [('node', '76542'), ('relation', '54320'), ('way', '54321'), ('way', '98764')]
        """

        to_append_to = OSMElement.get_missing_elements(self, to_append_to)
        for member, role in self:
            if role not in OSMXMLParser.IGNORED_ROLES:
                member.get_missing_elements(to_append_to)
        return to_append_to

    def to_xml(self, parent_element=None, include_node_dependencies=False):
        """Generate an XML element representing this relation

        If parent_element is supplied, it is added to that element and
        returned.  If no parent_element is supplied, an OSM XML root
        element is created, and the generated <node> element is added
        to that.

        >>> subr1 = Relation('98764')
        >>> subr1.add_member(Way('54319'), role='inner')
        >>> subr1.add_member(OSMElement.make_missing_element('relation', '54320'))
        >>> subr1.add_member(OSMElement.make_missing_element('way', '54321'))

        >>> subr2 = Relation('87654')
        >>> subr2.add_member(Way('54322'))
        >>> subr2.add_member(Way('54323'), role='inner')

        >>> r = Relation('98765')
        >>> r.add_member(Node('76542', latitude='52', longitude='0.3'))
        >>> r.add_member(Way('76543'))
        >>> r.add_member(subr1)
        >>> r.add_member(OSMElement.make_missing_element('way', '98764'))
        >>> r.add_member(Way('76545'), role='inner')
        >>> r.add_member(subr2, role='inner')
        >>> r.add_member(Way('76546'))

        >>> r.tags.update({'boundary': 'administrative',
        ...                'admin_level': '2'})
        >>> xe = etree.Element('example')
        >>> result = r.to_xml(xe)
        >>> result is xe
        True
        >>> print etree.tostring(xe, pretty_print=True),
        <example>
          <relation id="98765">
            <member ref="76542" role="" type="node"/>
            <member ref="76543" role="" type="way"/>
            <member ref="98764" role="" type="relation"/>
            <member ref="98764" role="" type="way"/>
            <member ref="76545" role="inner" type="way"/>
            <member ref="87654" role="inner" type="relation"/>
            <member ref="76546" role="" type="way"/>
            <tag k="admin_level" v="2"/>
            <tag k="boundary" v="administrative"/>
          </relation>
        </example>

        Sometimes we'd like to output the nodes that are included at the same time:

        >>> xe = etree.Element('example-with-nodes')
        >>> r.to_xml(xe, include_node_dependencies=True) #doctest: +ELLIPSIS
        <Element example-with-nodes at ...>
        >>> print etree.tostring(xe, pretty_print=True),
        <example-with-nodes>
          <node lat="52" lon="0.3" id="76542"/>
          <relation id="98765">
            <member ref="76542" role="" type="node"/>
            <member ref="76543" role="" type="way"/>
            <member ref="98764" role="" type="relation"/>
            <member ref="98764" role="" type="way"/>
            <member ref="76545" role="inner" type="way"/>
            <member ref="87654" role="inner" type="relation"/>
            <member ref="76546" role="" type="way"/>
            <tag k="admin_level" v="2"/>
            <tag k="boundary" v="administrative"/>
          </relation>
        </example-with-nodes>


        And the final option is to include the OSM XML boilerplate as well:

        >>> result = r.to_xml()
        >>> print etree.tostring(result, pretty_print=True),
        <osm version="0.6" generator="mySociety Boundary Extractor">
          <note>The data included in this document is from www.openstreetmap.org. It has there been collected by a large group of contributors. For individual attribution of each item please refer to http://www.openstreetmap.org/api/0.6/[node|way|relation]/#id/history</note>
          <relation id="98765">
            <member ref="76542" role="" type="node"/>
            <member ref="76543" role="" type="way"/>
            <member ref="98764" role="" type="relation"/>
            <member ref="98764" role="" type="way"/>
            <member ref="76545" role="inner" type="way"/>
            <member ref="87654" role="inner" type="relation"/>
            <member ref="76546" role="" type="way"/>
            <tag k="admin_level" v="2"/>
            <tag k="boundary" v="administrative"/>
          </relation>
        </osm>

        An exception should be thrown if a missing node is included,
        and include_node_dependencies is true:

        >>> r = Relation('1234')
        >>> r.add_member(OSMElement.make_missing_element('node', '17'))
        >>> example = etree.Element('exception-example')
        >>> r.to_xml(example, include_node_dependencies=True)
        Traceback (most recent call last):
          ...
        Exception: Trying out output a missing node %s as XML
        """

        if parent_element is None:
            parent_element = OSMElement.xml_wrapping()
        relation = etree.Element('relation',
                                 attrib={'id': self.element_id})
        members_xml = []
        for member, role in self:
            if include_node_dependencies and member.element_type == "node":
                if member.element_content_missing:
                    raise Exception, "Trying out output a missing node %s as XML"
                member.to_xml(parent_element, include_node_dependencies)
            etree.SubElement(relation,
                             'member',
                             attrib={'type': member.element_type,
                                     'ref': member.element_id,
                                     'role': role})
        parent_element.append(relation)
        self.xml_add_tags(relation)
        return parent_element

    def reconstruct_missing(self, parser, id_to_node):
        """Replace any missing nodes from the parser's cache or id_to_node

        id_to_node should be a dictionary that maps IDs of nodes (as
        strings) the complete Node object or None.  parser should have
        a method called get_known_or_fetch('node', element_id) which
        will return None or the complete Node object, if the parser
        can find it.

        If any nodes could not be found from parser or id_to_node,
        they are returned as a list.  Therefore, if the way could be
        completely reconstructed, [] will be returned.

        >>> def make_incomplete_relation():
        ...     w = Way('76543', nodes=[Node("12", latitude="52", longitude="1"),
        ...                             OSMElement.make_missing_element('node', '13'),
        ...                             OSMElement.make_missing_element('node', '14'),
        ...                             Node("15", latitude="51", longitude="2")])
        ...     r = Relation('76544')
        ...     r.add_member(Node("16", latitude="50", longitude="0"))
        ...     r.add_member(w)
        ...     r.add_member(OSMElement.make_missing_element('relation', '76545'), role='defaults')
        ...     r.add_member(Way('17'))
        ...     r.add_member(OSMElement.make_missing_element('way', '18'))
        ...     r.add_member(OSMElement.make_missing_element('node', '19'))
        ...     r.add_member(OSMElement.make_missing_element('node', '20'))
        ...     return r
        >>> r = make_incomplete_relation()
        >>> class FakeParser:
        ...     def get_known_or_fetch(self, element_type, element_id):
        ...         if element_type != 'node':
        ...             return OSMElement.make_missing_element(element_type, element_id)
        ...         if element_id == "14":
        ...             return Node("14", latitude="52.4", longitude="2.1")
        ...         return OSMElement.make_missing_element(element_type, element_id)
        >>> node_cache = {"13": Node("13", latitude="51.2", longitude="1.3"),
        ...               "19": None,
        ...               "20": Node("20", latitude="51.3", longitude="1.1"),
        ...               "22": None}
        >>> r.reconstruct_missing(FakeParser(), node_cache)
        [Way(id="18", missing), Node(id="19", missing)]

        Supposing that both those caches are empty, all of the missing
        elements should be returned:

        >>> r = make_incomplete_relation()
        >>> class FakeEmptyParser:
        ...     def get_known_or_fetch(self, element_type, element_id):
        ...         return OSMElement.make_missing_element(element_type, element_id)
        >>> node_cache = {}
        >>> r.reconstruct_missing(FakeEmptyParser(), node_cache)
        [Node(id="13", missing), Node(id="14", missing), Way(id="18", missing), Node(id="19", missing), Node(id="20", missing)]
        """

        still_missing = []
        for i, t in enumerate(self.children):
            member, role = t
            if role in OSMXMLParser.IGNORED_ROLES:
                continue
            element_type = member.element_type
            element_id = member.element_id
            if member.element_content_missing:
                found_element = None
                if element_type == 'node':
                    if element_id in id_to_node:
                        found_element = id_to_node[element_id]
                if not found_element:
                    # Ask the parser to try to fetch it from its filesystem cache:
                    found_element = parser.get_known_or_fetch(element_type, element_id)
                if (found_element is not None) and (not found_element.element_content_missing):
                    self.children[i] = (found_element, role)
                else:
                    still_missing.append(member)
            else:
                # Even if the element isn't marked as missing, it may
                # contain nodes, ways or relations that *are* missing,
                # so we have to recurse:
                if element_type != 'node':
                    still_missing.extend(member.reconstruct_missing(parser, id_to_node))

        return still_missing

class UnexpectedElementException(Exception):
    def __init__(self, element_name, message):
        self.element_name = element_name
        self.message = message
    def __str__(self):
        return self.message

class OSMXMLParser(ContentHandler):

    """A SAX-based parser for data from OSM's Overpass API

    This has two main modes of operation.  The first builds a
    structure of Node, Way and Relation objects that represent the
    returned data, fetching missing elements as necessary, keeping
    these all in memory.  Typically one would then call
    get_known_or_fetch on this object to get back data for a
    particular element.

    The second allows you to supply a callback that will be called for
    each top-level element as it's parsed, which takes a minimal
    amount of memory.

    >>> valid_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <node id="291974462" lat="55.0548850" lon="-2.9544991"/>
    ...   <node id="312203528" lat="54.4600000" lon="-5.0596341"/>
    ...   <way id="28421671">
    ...     <nd ref="291974462"/>
    ...     <nd ref="312203528"/>
    ...   </way>
    ...   <relation id="3123205528">
    ...     <member type="way" ref="28421671" role="inner"/>
    ...      <tag k="name:en" v="Whatever"/>
    ...   </relation>
    ... </osm>'''
    >>> parser = parse_xml_string(valid_xml, fetch_missing=False)
    >>> len(parser)
    4
    >>> parser.empty()
    False

    If any unexpected elements occur, an exception is thrown:

    >>> parse_xml_string('''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <blah/>
    ... </osm>''', fetch_missing=False)
    Traceback (most recent call last):
      ...
    UnexpectedElementException: Should never get a <blah> at the top level

    Similarly for unexpected elements at lower level:

    >>> parse_xml_string('''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <node id="123" lat="52" lon="0">
    ...     <foo>
    ...   </node>
    ... </osm>''', fetch_missing=False)
    Traceback (most recent call last):
      ...
    UnexpectedElementException: Unhandled element <foo>

    Some elements can only be nested in others:

    >>> parse_xml_string('''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <node id="123" lat="52" lon="0">
    ...     <member type="way" ref="345" role=""/>
    ...   </node>
    ... </osm>''', fetch_missing=False)
    Traceback (most recent call last):
      ...
    UnexpectedElementException: Didn't expect to find <member> in a <node>, can only be in <relation>

    And some elements can't be at the top level:

    >>> parse_xml_string('''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <member type="way" ref="345" role=""/>
    ... </osm>''', fetch_missing=False)
    Traceback (most recent call last):
      ...
    UnexpectedElementException: Should never get a <member> at the top level

    Top-level elements should never be found at a sub-level:

    >>> parse_xml_string('''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <node id="123" lat="52" lon="0">
    ...     <node>
    ...   </node>
    ... </osm>''', fetch_missing=False)
    Traceback (most recent call last):
      ...
    UnexpectedElementException: Should never get a new <node> when still in a top-level element

    The types of members of relations must be known:

    >>> parse_xml_string('''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <relation id="3123205528">
    ...     <member type="foo" ref="28421671" role="inner"/>
    ...   </relation>
    ... </osm>''', fetch_missing=False)
    Traceback (most recent call last):
      ...
    Exception: Unknown member type 'foo' in <relation>

    Parsed elements are normally cached:

    >>> parser = parse_xml_string(valid_xml, fetch_missing=False)
    >>> len(parser.known_nodes)
    2
    >>> len(parser.known_ways)
    1
    >>> len(parser.known_relations)
    1

    But the cache can be cleared:

    >>> parser.clear_caches()
    >>> len(parser.known_nodes) + len(parser.known_ways) + len(parser.known_relations)
    0

    Or you can request no caching in the first place:

    parser = parse_xml_string(valid_xml, cache_in_memory=False, fetch_missing=False)
    >>> len(parser.known_nodes) + len(parser.known_ways) + len(parser.known_relations)
    0

    Now some examples of using a callback instead:

    >>> def test(element, parser):
    ...    print "got element:", element
    >>> parser = parse_xml_string(valid_xml, fetch_missing=False, callback=test)
    got element: Node(id="291974462", lat="55.0548850", lon="-2.9544991")
    got element: Node(id="312203528", lat="54.4600000", lon="-5.0596341")
    got element: Way(id="28421671", nodes=2)
    got element: Relation(id="3123205528", members=1)

    And then trying to access the top-level elements in any way should
    throw an exception:

    >>> len(parser)
    Traceback (most recent call last):
      ...
    Exception: When parsed with a callback, no top level elements are kept in memory
    >>> parser.empty()
    Traceback (most recent call last):
      ...
    Exception: When parsed with a callback, no top level elements are kept in memory
    >>> for e in parser:
    ...    print e
    Traceback (most recent call last):
      ...
    Exception: When parsed with a callback, no top level elements are kept in memory

    If the elements are in an unhelpful order, then parsing still
    succeeds:

    >>> reordered_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <relation id="3123205528">
    ...     <member type="way" ref="28421671" role="inner"/>
    ...      <tag k="name:en" v="Whatever"/>
    ...   </relation>
    ...   <way id="28421671">
    ...     <nd ref="291974462"/>
    ...     <nd ref="312203528"/>
    ...   </way>
    ...   <node id="291974462" lat="55.0548850" lon="-2.9544991"/>
    ...   <node id="312203528" lat="54.4600000" lon="-5.0596341"/>
    ... </osm>'''
    >>> tmp_cache = mkdtemp()
    >>> parser = parse_xml_string(reordered_xml,
    ...                           fetch_missing=False,
    ...                           cache_directory=tmp_cache)
    >>> for e in parser:
    ...     print e
    Relation(id="3123205528", members=1)
    Way(id="28421671", nodes=2)
    Node(id="291974462", lat="55.0548850", lon="-2.9544991")
    Node(id="312203528", lat="54.4600000", lon="-5.0596341")

    But some elements may be marked as missing:

    >>> r = parser[0]
    >>> r
    Relation(id="3123205528", members=1)
    >>> r[0]
    (Way(id="28421671", missing), u'inner')

    ... which can be fixed up with reconstruct_missing, which uses its
    in-memory cache:

    >>> still_missing = r.reconstruct_missing(parser, {})
    >>> still_missing
    []
    >>> parser[0][0]
    (Way(id="28421671", nodes=2), u'inner')

    If there are some missing elements which aren't in the XML at all,
    they can be fetched from the Overpass API if you have the
    fetch_missing option on (as it is by default):

    >>> tmp_cache = mkdtemp()
    >>> xml_requiring_fetch = '''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <relation id="1">
    ...     <member type="relation" ref="295353" role="example-subrelation"/>
    ...   </relation>
    ... </osm>'''
    >>> parser = parse_xml_string(xml_requiring_fetch,
    ...                           cache_directory=tmp_cache)
    >>> south_cambridgeshire_relation, fake_role = parser[0][0]
    >>> south_cambridgeshire_relation # doctest: +ELLIPSIS
    Relation(id="295353", members=...)
    >>> len(south_cambridgeshire_relation) > 0
    True

    Doing that again will be faster, since the results of the API will
    have been cached to disk, but still produce the same result:

    >>> parser = parse_xml_string(xml_requiring_fetch,
    ...                           cache_directory=tmp_cache)
    >>> south_cambridgeshire_relation, fake_role = parser[0][0]
    >>> south_cambridgeshire_relation # doctest: +ELLIPSIS
    Relation(id="295353", members=...)
    >>> len(south_cambridgeshire_relation) > 0
    True

    If some elements are totally non-existent, and we're not fetching:

    >>> xml_with_fictitious_refs = '''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <way id="28421671">
    ...     <nd ref="1000000000000"/>
    ...     <nd ref="1000000000001"/>
    ...   </way>
    ... </osm>'''
    >>> parser = parse_xml_string(xml_with_fictitious_refs,
    ...                           fetch_missing=False,
    ...                           cache_directory=tmp_cache)
    >>> for e in parser[0]:
    ...     print e
    Node(id="1000000000000", missing)
    Node(id="1000000000001", missing)

    If fetching isn't allowed, we get the same result the first time:

    >>> parser = parse_xml_string(xml_with_fictitious_refs,
    ...                           cache_directory=tmp_cache)
    >>> for e in parser[0]:
    ...     print e
    Node(id="1000000000000", missing)
    Node(id="1000000000001", missing)

    A second time, we find an empty file in the cache, which should
    give the same result.

    >>> parser = parse_xml_string(xml_with_fictitious_refs,
    ...                           cache_directory=tmp_cache) # doctest: +ELLIPSIS
    >>> for e in parser[0]:
    ...     print e
    Node(id="1000000000000", missing)
    Node(id="1000000000001", missing)

    Remove the temporary directory created for these doctests:
    >>> shutil.rmtree(tmp_cache)
    """

    VALID_TOP_LEVEL_ELEMENTS = set(('node', 'relation', 'way'))
    VALID_RELATION_MEMBERS = set(('node', 'relation', 'way'))
    IGNORED_TAGS = set(('osm', 'note', 'meta', 'bound'))
    IGNORED_ROLES = set(('subarea', 'defaults', 'apply_to'))

    def __init__(self, fetch_missing=True, callback=None, cache_in_memory=True, cache_directory=None):
        self.top_level_elements = []
        self.current_top_level_element = None
        # These dictionaries map ids to already discovered elements:
        self.known_nodes = {}
        self.known_ways = {}
        self.known_relations = {}
        self.fetch_missing = fetch_missing
        self.callback = callback
        self.cache_in_memory = cache_in_memory
        self.cache_directory = cache_directory

    def clear_caches(self):
        self.known_nodes.clear()
        self.known_ways.clear()
        self.known_relations.clear()

    # FIXME: make this a decorator
    def raise_if_callback(self):
        if self.callback:
            raise Exception, "When parsed with a callback, no top level elements are kept in memory"

    def __iter__(self):
        self.raise_if_callback()
        for e in self.top_level_elements:
            yield e

    def __len__(self):
        self.raise_if_callback()
        return len(self.top_level_elements)

    def empty(self):
        self.raise_if_callback()
        return 0 == len(self.top_level_elements)

    def __getitem__(self, val):
        return self.top_level_elements.__getitem__(val)

    def raise_if_sub_level(self, name):
        if self.current_top_level_element is not None:
            raise UnexpectedElementException(name, "Should never get a new <%s> when still in a top-level element" % (name,))

    def raise_if_top_level(self, name):
        if self.current_top_level_element is None:
            raise UnexpectedElementException(name, "Should never get a <%s> at the top level" % (name,))

    def raise_unless_expected_parent(self, name, expected_parent):
        if self.current_top_level_element.element_type != expected_parent:
            wrong_parent = self.current_top_level_element.element_type
            raise UnexpectedElementException(name, "Didn't expect to find <%s> in a <%s>, can only be in <%s>" % (name, wrong_parent, expected_parent))

    def get_known_or_fetch(self, element_type, element_id, verbose=False):
        """Return an OSM Node, Way or Relation, fetching it if necessary

        If the element couldn't be found any means, an element marked
        with element_content_missing is returned."""
        element_id = str(element_id)
        if self.cache_in_memory:
            d = {'node': self.known_nodes,
                 'way': self.known_ways,
                 'relation': self.known_relations}[element_type]
            if element_id in d:
                return d[element_id]
        result = None
        # See if it is in the on-disk cache:
        cache_filename = get_cache_filename(element_type, element_id, self.cache_directory)
        if os.path.exists(cache_filename):
            parser = parse_xml(cache_filename, fetch_missing=self.fetch_missing)
            for e in parser.top_level_elements:
                if e.name_id_tuple() == (element_type, element_id):
                    result = e
                    break
            if result is None:
                if len(parser) == 0:
                    # If it's an empty file, just return a missing element:
                    return OSMElement.make_missing_element(element_type, element_id)
                else:
                    # However, if there's the wrong data in the file,
                    # that's worth looking into:
                    raise Exception, "Failed to find expected element in: " + cache_filename
        if result is None:
            if self.fetch_missing:
                result = fetch_osm_element(element_type,
                                           element_id,
                                           self.fetch_missing,
                                           verbose,
                                           self.cache_directory)
                if not result:
                    return OSMElement.make_missing_element(element_type, element_id)
            else:
                return OSMElement.make_missing_element(element_type, element_id)
        if self.cache_in_memory:
            d[element_id] = result
        return result

    def startElement(self, name, attr):
        if name in OSMXMLParser.IGNORED_TAGS:
            return
        elif name in OSMXMLParser.VALID_TOP_LEVEL_ELEMENTS:
            self.raise_if_sub_level(name)
            element_id = attr['id']
            if name == "node":
                self.current_top_level_element = Node(element_id, attr['lat'], attr['lon'])
                if self.cache_in_memory:
                    self.known_nodes[element_id] = self.current_top_level_element
            elif name == "way":
                self.current_top_level_element = Way(element_id)
                if self.cache_in_memory:
                    self.known_ways[element_id] = self.current_top_level_element
            elif name == "relation":
                self.current_top_level_element = Relation(element_id)
                if self.cache_in_memory:
                    self.known_relations[element_id] = self.current_top_level_element
            else:
                # A programming error: something's been added to
                # VALID_TOP_LEVEL_ELEMENTS which isn't dealt with.
                assert "Unhandled top level element %s" % (name,) # pragma: no cover
        else:
            # These must be sub-elements:
            self.raise_if_top_level(name)
            if name == "tag":
                k, v = attr['k'], attr['v']
                self.current_top_level_element.tags[k] = v
            elif name == "member":
                self.raise_unless_expected_parent(name, 'relation')
                member_type = attr['type']
                if member_type not in OSMXMLParser.VALID_RELATION_MEMBERS:
                    raise Exception, "Unknown member type '%s' in <relation>" % (member_type,)
                if attr['role'] not in OSMXMLParser.IGNORED_ROLES:
                    member = self.get_known_or_fetch(member_type, attr['ref'])
                    self.current_top_level_element.children.append((member, attr['role']))
            elif name == "nd":
                self.raise_unless_expected_parent(name, 'way')
                node = self.get_known_or_fetch('node', attr['ref'])
                if node.element_content_missing:
                    if self.fetch_missing:
                         # print >> sys.stderr, "A node (%s) was referenced that couldn't be found" % (attr['ref'],)
                         pass
                    node = OSMElement.make_missing_element('node', attr['ref'])
                self.current_top_level_element.nodes.append(node)
            else:
                raise UnexpectedElementException(name, "Unhandled element <%s>" % (name,))

    def endElement(self, name):
        if name in OSMXMLParser.VALID_TOP_LEVEL_ELEMENTS:
            if self.callback:
                self.callback(self.current_top_level_element, self)
            else:
                self.top_level_elements.append(self.current_top_level_element)
            self.current_top_level_element = None

class MinimalOSMXMLParser(ContentHandler):

    """Only extract ID and tags from top-level elements"""

    def __init__(self, handle_element):
        self.handle_element = handle_element
        self.current_tags = None
        self.current_element_type = None
        self.current_element_id = None

    def startElement(self, name, attr):
        if name in OSMXMLParser.VALID_TOP_LEVEL_ELEMENTS:
            self.current_element_type = name
            self.current_element_id = attr['id']
            self.current_tags = {}
        elif name == "tag":
            self.current_tags[attr['k']] = attr['v']

    def endElement(self, name):
        if name in OSMXMLParser.VALID_TOP_LEVEL_ELEMENTS:
            self.handle_element(self.current_element_type,
                                self.current_element_id,
                                self.current_tags)
            self.current_element_type = None
            self.current_element_id = None
            self.current_tags = None

def get_total_seconds(td):
    """A replacement for timedelta.total_seconds(), that's only in Python >= 2.7"""
    return td.microseconds * 1e-6 + td.seconds + td.days * (24.0 * 60 * 60)

def fetch_cached(element_type, element_id, verbose=False, cache_directory=None):
    """Get an OSM element from the Overpass API, with caching on disk

    >>> tmp_cache = mkdtemp()
    >>> filename = fetch_cached('relation',
    ...                         '375982',
    ...                         cache_directory=tmp_cache)
    >>> filename # doctest: +ELLIPSIS
    '.../relation/982/relation-375982.xml'

    If you request an unknown element type, an exception is thrown:
    >>> filename = fetch_cached('nonsense',
    ...                         '1',
    ...                         cache_directory=tmp_cache)
    Traceback (most recent call last):
      ...
    Exception: Unknown element type 'nonsense'
    """

    global last_overpass_fetch
    arguments = (element_type, element_id)
    if element_type not in ('relation', 'way', 'node'):
        raise Exception, "Unknown element type '%s'" % (element_type,)
    filename = get_cache_filename(element_type, element_id, cache_directory)
    if not os.path.exists(filename):
        all_dependents_query = get_query_relation_and_dependents(element_type, element_id)
        get_from_overpass(all_dependents_query, filename)
    return filename

def parse_xml_minimal(filename, element_handler):
    """Parse some OSM XML just to get type, id and tags

    >>> def output(type, id, tags):
    ...     print "type:", type, "id:", id, "tags:", tags
    >>> example_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <node id="291974462" lat="55.0548850" lon="-2.9544991"/>
    ...   <node id="312203528" lat="54.4600000" lon="-5.0596341"/>
    ...   <way id="28421671">
    ...     <nd ref="291974462"/>
    ...     <nd ref="312203528"/>
    ...   </way>
    ...   <relation id="3123205528">
    ...     <member type="way" ref="28421671" role="inner"/>
    ...      <tag k="name:en" v="Whatever"/>
    ...   </relation>
    ... </osm>
    ... '''
    >>> with NamedTemporaryFile(delete=False) as ntf:
    ...     ntf.write(example_xml)
    >>> parse_xml_minimal(ntf.name, output)
    type: node id: 291974462 tags: {}
    type: node id: 312203528 tags: {}
    type: way id: 28421671 tags: {}
    type: relation id: 3123205528 tags: {u'name:en': u'Whatever'}
    """
    parser = MinimalOSMXMLParser(element_handler)
    with open(filename) as fp:
        xml.sax.parse(fp, parser)

def parse_xml(filename, fetch_missing=True):
    """Completely parse an OSM XML file

    >>> example_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    ... <osm version="0.6" generator="Overpass API">
    ...   <node id="291974462" lat="55.0548850" lon="-2.9544991"/>
    ...   <node id="312203528" lat="54.4600000" lon="-5.0596341"/>
    ...   <way id="28421671">
    ...     <nd ref="291974462"/>
    ...     <nd ref="312203528"/>
    ...   </way>
    ...   <relation id="3123205528">
    ...     <member type="way" ref="28421671" role="inner"/>
    ...      <tag k="name:en" v="Whatever"/>
    ...   </relation>
    ... </osm>
    ... '''
    >>> with NamedTemporaryFile(delete=False) as ntf:
    ...     ntf.write(example_xml)
    >>> parser = parse_xml(ntf.name, fetch_missing=False)
    >>> os.remove(ntf.name)
    >>> for top_level_element in parser:
    ...     print top_level_element
    Node(id="291974462", lat="55.0548850", lon="-2.9544991")
    Node(id="312203528", lat="54.4600000", lon="-5.0596341")
    Way(id="28421671", nodes=2)
    Relation(id="3123205528", members=1)
    """
    parser = OSMXMLParser(fetch_missing)
    with open(filename) as fp:
        xml.sax.parse(fp, parser)
    return parser

def parse_xml_string(s, *parser_args, **parser_kwargs):
    fp = StringIO(s)
    parser = OSMXMLParser(*parser_args, **parser_kwargs)
    xml.sax.parse(fp, parser)
    return parser

def fetch_osm_element(element_type, element_id, fetch_missing=True, verbose=False, cache_directory=None):
    """Fetch and parse a particular OSM element recursively

    More data is fetched from the API if required.  'element_type'
    should be one of 'relation', 'way' or 'node'.

    For example, you could request the relation representing Scotland
    with:

    >>> tmp_cache = mkdtemp()
    >>> fetch_osm_element("relation", "58446", cache_directory=tmp_cache)
    Relation(id="58446", members=71)

    Or do the same, more verbosely, with:

    >>> tmp_cache2 = mkdtemp()
    >>> fetch_osm_element("relation", "58446", verbose=True, cache_directory=tmp_cache2)
    fetch_osm_element(relation, 58446)
    Relation(id="58446", members=71)

    FIXME: fetching a non-existing element really should produce an
    exception, but at the moment just returns None

    >>> tmp_cache3 = mkdtemp()
    >>> fetch_osm_element('relation', '10000000000', cache_directory=tmp_cache3)

    Remove the temporary directories created for these doctests:
    >>> for d in (tmp_cache, tmp_cache2, tmp_cache3):
    ...     shutil.rmtree(d)
    """

    element_id = str(element_id)
    if verbose:
        print "fetch_osm_element(%s, %s)" % (element_type, element_id)
    # Make sure we have the XML file for that relation, node or way:
    filename = fetch_cached(element_type, element_id, verbose, cache_directory)
    try:
        parsed = parse_xml(filename, fetch_missing)
    except UnexpectedElementException, e:
        # If we failed to parse the file, move it out of the way (so
        # for transient errors we can just try again) and re-raise the
        # exception:
        new_filename = filename+".broken"
        os.rename(filename, new_filename)
        raise
    # Sometimes we seem to have an empty element returned, in which
    # case just return None:
    if not len(parsed):
        return None
    return parsed.get_known_or_fetch(element_type, element_id)

class EndpointToWayMap:

    """A class for mapping endpoints to the Way they're on

    This is useful for quickly checking finding which Ways (if any)
    you can join another Way to.  However, each endpoint can only map
    to one way.

    For example, create some nodes that are at the corners of a square

    >>> top_left = Node("12", latitude="52", longitude="1")
    >>> top_right = Node("13", latitude="52", longitude="2")
    >>> bottom_right = Node("14", latitude="51", longitude="2")
    >>> bottom_left = Node("15", latitude="51", longitude="1")

    ... and extra ones at the bottom left:

    >>> below_bottom_left = Node("16", latitude="50", longitude="1")
    >>> left_of_bottom_left = Node("17", latitude="51", longitude="0")

    And create a way which represents the left side (w), top and right
    sides (ne), bottom side (s) and edges coming down and left from
    the bottom left:

    >>> w = Way("1", nodes=[bottom_left, top_left])
    >>> ne = Way("2", nodes=[top_left, top_right, bottom_right])
    >>> s = Way("3", nodes=[bottom_right, bottom_left])
    >>> stalk_down = Way("4", nodes=[below_bottom_left, bottom_left])
    >>> stalk_left = Way("5", nodes=[left_of_bottom_left, bottom_left])

    Now add two to an EndpointToWayMap:

    >>> etwm = EndpointToWayMap()
    >>> etwm.add_way(ne)
    >>> etwm.add_way(stalk_down)

    Ways can them be retrieved by endpoints that overlap:

    >>> etwm.get_from_either_end(stalk_left)
    [Way(id="4", nodes=2)]
    >>> result = etwm.get_from_either_end(s)
    >>> set(result) == set([stalk_down, ne])
    True
    >>> etwm.number_of_endpoints()
    4

    You can output a readable version of the EndpointToWayMap:

    >>> print etwm.pretty(2)
      EndpointToWayMap:
        endpoint: node (12) lat: 52, lon: 1
          way.first: Node(id="12", lat="52", lon="1")
          way.last: Node(id="14", lat="51", lon="2")
        endpoint: node (14) lat: 51, lon: 2
          way.first: Node(id="12", lat="52", lon="1")
          way.last: Node(id="14", lat="51", lon="2")
        endpoint: node (15) lat: 51, lon: 1
          way.first: Node(id="16", lat="50", lon="1")
          way.last: Node(id="15", lat="51", lon="1")
        endpoint: node (16) lat: 50, lon: 1
          way.first: Node(id="16", lat="50", lon="1")
          way.last: Node(id="15", lat="51", lon="1")

    Ways can be removed from the map as well:

    >>> etwm.remove_way(ne)
    >>> etwm.remove_way(stalk_down)
    >>> etwm.get_from_either_end(w)
    []

    Adding a way that has endpoints that are already in the map is an
    error:

    >>> etwm.add_way(ne)
    >>> etwm.add_way(s)
    Traceback (most recent call last):
      ...
    Exception: Call to add_way would overwrite existing way(s)
    """

    def __init__(self):
        self.endpoints = {}

    def add_way(self, way):
        if self.get_from_either_end(way):
            raise Exception, "Call to add_way would overwrite existing way(s)"
        self.endpoints[way.first] = way
        self.endpoints[way.last] = way

    def remove_way(self, way):
        del self.endpoints[way.first]
        del self.endpoints[way.last]

    def get_from_either_end(self, way):
        return [ self.endpoints[e] for e in (way.first, way.last)
                 if e in self.endpoints ]

    def pretty(self, indent=0):
        i = " "*indent
        result = i + "EndpointToWayMap:"
        for k, v in sorted(self.endpoints.items()):
            result += "\n%s  endpoint: %s" % (i, k.pretty())
            result += "\n%s    way.first: %r" % (i, v.first)
            result += "\n%s    way.last: %r" % (i, v.last)
        return result

    def number_of_endpoints(self):
        return len(self.endpoints)

class UnclosedBoundariesException(Exception):
    def __init__(self, detailed_error=None):
        self.detailed_error = detailed_error

def join_way_soup(ways):
    """Join an iterable collection of ways into closed ways

    Two ways can be joined when the share a start or end node.  This
    function will try to join the given ways into a series of closed
    loops.  If there are any unclosed loops left at the end, they are
    reported to standard error and an exception is thrown.

    For example, if we create some points in a square:

    >>> top_left = Node("12", latitude="52", longitude="1")
    >>> top_right = Node("13", latitude="52", longitude="2")
    >>> bottom_right = Node("14", latitude="51", longitude="2")
    >>> bottom_left = Node("15", latitude="51", longitude="1")

    ... and extra ones at the bottom left:

    >>> below_bottom_left = Node("16", latitude="50", longitude="1")
    >>> left_of_bottom_left = Node("17", latitude="51", longitude="0")

    And create a way which represents the left side (w), top and right
    sides (ne), bottom side (s) and edges coming down and left from
    the bottom left:

    >>> w = Way("1", nodes=[bottom_left, top_left])
    >>> ne = Way("2", nodes=[top_left, top_right, bottom_right])
    >>> s = Way("3", nodes=[bottom_right, bottom_left])
    >>> stalk_down = Way("4", nodes=[below_bottom_left, bottom_left])
    >>> stalk_left = Way("5", nodes=[left_of_bottom_left, bottom_left])

    It shouldn't be possible to join stalk_left to ne:

    >>> join_way_soup([stalk_left, ne])
    Traceback (most recent call last):
    ...
    UnclosedBoundariesException

    And w and ne can be joined, but won't form a closed boundary (the
    bottom side of the square (s) is missing):

    >>> join_way_soup([w, ne])
    Traceback (most recent call last):
    ...
    UnclosedBoundariesException

    However, all of the sides of the square can be joined:

    >>> result = join_way_soup([w, ne, s])
    >>> result
    [Way(id="None", nodes=5)]

    If the way soup includes any missing ways, then just ignore them:
    >>> missing = OSMElement.make_missing_element('way', '7')
    >>> join_way_soup([w, ne, s, missing])
    [Way(id="None", nodes=5)]

    The nodes in the joined way should be the same as all the corners
    of the square (with one repeated once to join up again):

    >>> set(result[0].nodes) == set([top_left, top_right, bottom_left, bottom_right])
    True

    The ways supplied can from more than one closed polygon.  e.g.

    >>> other_top_left = Node("18", latitude="52", longitude="5")
    >>> other_top_right = Node("19", latitude="52", longitude="6")
    >>> other_bottom_right = Node("20", latitude="51", longitude="5")
    >>> other_bottom_left = Node("21", latitude="51", longitude="6")

    >>> other_nw = Way("6", nodes=[other_bottom_left, other_top_left, other_top_right])
    >>> other_se = Way("7", nodes=[other_top_right, other_bottom_right, other_bottom_left])

    >>> join_way_soup([s, w, ne, other_nw, other_se])
    [Way(id="None", nodes=5), Way(id="None", nodes=5)]

    But one closed polygon and an open one still fails:

    >>> join_way_soup([s, ne, other_nw, other_se])
    Traceback (most recent call last):
    ...
    UnclosedBoundariesException

    Another option is that one of the ways might already be closed,
    which is fine:

    >>> whole_square = Way("8", nodes=[top_left, top_right, bottom_right, bottom_left, top_left])
    >>> join_way_soup([whole_square, other_nw, other_se])
    [Way(id="8", nodes=5), Way(id="None", nodes=5)]
    """

    closed_ways = []
    endpoints_to_ways = EndpointToWayMap()
    for way in ways:
        if way.element_content_missing:
            continue
        if way.closed():
            closed_ways.append(way)
            continue
        # Are there any existing ways we can join this to?
        to_join_to = endpoints_to_ways.get_from_either_end(way)
        if to_join_to:
            joined = way
            for existing_way in to_join_to:
                joined = joined.join(existing_way)
                endpoints_to_ways.remove_way(existing_way)
                if joined.closed():
                    closed_ways.append(joined)
                    break
            if not joined.closed():
                endpoints_to_ways.add_way(joined)
        else:
            endpoints_to_ways.add_way(way)
    if endpoints_to_ways.number_of_endpoints():
        raise UnclosedBoundariesException, endpoints_to_ways.pretty()
    return closed_ways

if __name__ == "__main__":

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--test", dest="doctest",
                      default=False, action='store_true',
                      help="Run all doctests in this file")
    parser.add_option("--relation", dest="relation",
                      metavar="<RELATION_ID>",
                      help="Output KML for the OSM relation <RELATION_ID>")
    parser.add_option("--way", dest="way",
                      metavar="<WAY_ID>",
                      help="Output KML for the OSM way <WAY_ID>")

    (options, args) = parser.parse_args()

    if args:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    # These options are all mutually exclusive:
    exclusive_options = (options.doctest,
                         options.relation,
                         options.way)

    if sum(bool(x) for x in exclusive_options) != 1:
        print >> sys.stderr, "You must specify exactly one of --test, --relation or --way"
        sys.exit(1)

    if options.doctest:
        import doctest
        failure_count, test_count = doctest.testmod()
        sys.exit(0 if failure_count == 0 else 1)

    if options.relation:
        element_type = 'relation'
        element_id = options.relation
    elif options.way:
        element_type = 'way'
        element_id = options.way

    from generate_kml import *

    kml, bbox = get_kml_for_osm_element(element_type, element_id)

    if kml:
        print kml
        sys.exit(0)
    else:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = check-capitals-in-global
#!/usr/bin/env python

# This script checks whether a representative latitude / longitude in
# each capital city of the world is contained in a level 2 admin area
# in MapIt Global.  This is a simple sanity check for finding any
# unclosed country boundaries.
#
# There are two dependencies from PyPi needed for this script, which
# can be installed with:
#
#   pip install requests
#   pip install SPARQLWrapper

from collections import defaultdict
import json
import re
import requests
import time
import urllib
from SPARQLWrapper import SPARQLWrapper, JSON

def name_from_url(url):
    """Extract everything after the last slash in the URL"""

    url_as_str = url.encode('utf-8')
    unquoted = urllib.unquote(re.sub(r'^.*/', '', url_as_str))
    return unquoted.decode('utf-8')

def tuple_mean(index, tuples):
    """Return the mean along a given index in a sequence of tuples"""

    return sum(t[index] for t in tuples) / float(len(tuples))

# Get a list of coordinates for capital cities
# The filter for only selecting current countries (as opposed to
# historical ones) was from here:
#  http://answers.semanticweb.com/questions/2155/sparql-query-to-get-a-distinct-set-of-current-countries-from-dbpedia

sparql = SPARQLWrapper("http://dbpedia.org/sparql")
sparql.setQuery("""
    PREFIX o: <http://dbpedia.org/ontology/>
    PREFIX p: <http://dbpedia.org/property/>
    PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>

    SELECT ?lon ?lat ?country ?capital WHERE {
        ?country p:capital ?capital .
        ?country rdf:type o:Country .
        ?capital geo:lat ?lat .
        ?capital geo:long ?lon .
        OPTIONAL {?country p:yearEnd ?yearEnd}
        FILTER (!bound(?yearEnd))
    } ORDER BY ?country
""")
sparql.setReturnFormat(JSON)
results = sparql.query().convert()

coordinates_for_places = defaultdict(list)

for result in results["results"]["bindings"]:
    lat = float(result['lat']['value'])
    lon = float(result['lon']['value'])
    country = name_from_url(result['country']['value'])
    capital = name_from_url(result['capital']['value'])
    coordinates_for_places[(capital, country)].append((lon, lat))

sorted_mapping = sorted(coordinates_for_places.items(),
                        key=lambda t: (t[0][1], t[0][0]))

total_capitals = 0
capitals_with_no_country = 0

for place, coords in sorted_mapping:
    city, country = (name_from_url(x) for x in place)
    print u"{0} ({1})".format(city, country).encode('utf-8')
    mean_lon = tuple_mean(0, coords)
    mean_lat = tuple_mean(1, coords)
    mapit_url_format = "http://global.mapit.mysociety.org/point/4326/{0},{1}"
    mapit_url = mapit_url_format.format(mean_lon, mean_lat)
    print "  browse on MapIt Global:", mapit_url + ".html"
    r = requests.get(mapit_url, headers={'User-Agent': 'TestingCapitals/1.0'})
    mapit_result = json.loads(r.text)
    area_values = [a for k, a in mapit_result.items() if k != "debug_db_queries"]
    level_2_areas = [a for a in area_values if a['type'] == 'O02']
    if level_2_areas:
        print "  In these level 2 areas:"
        for a in level_2_areas:
            print "    ", a['name'].encode('utf-8')
    else:
        print "  ### No level 2 areas found!"
        capitals_with_no_country += 1
    total_capitals += 1
    # Sleep so we don't hit MapIt's rate limiting:
    time.sleep(1)

print "{0} capitals had no country in MapIt Global (out of {1})".format(
    capitals_with_no_country,
    total_capitals)

########NEW FILE########
__FILENAME__ = generate_kml
#!/usr/bin/python
# -*- coding: utf-8 -*-

from boundaries import *
from lxml import etree
from shapely.geometry import Polygon

def ways_overlap(a, b):
    """Determines if two Way objects represent overlapping polygons

    For example, if we have two overlapping ways:

    >>> w1 = Way('1', nodes=[Node('10', latitude=53, longitude=0),
    ...                      Node('11', latitude=53, longitude=4),
    ...                      Node('12', latitude=49, longitude=4),
    ...                      Node('13', latitude=49, longitude=0),
    ...                      Node('10', latitude=53, longitude=0)])

    >>> w2 = Way('2', nodes=[Node('14', latitude=51, longitude=2),
    ...                      Node('15', latitude=51, longitude=6),
    ...                      Node('16', latitude=47, longitude=6),
    ...                      Node('17', latitude=47, longitude=2),
    ...                      Node('14', latitude=51, longitude=2)])

    >>> ways_overlap(w1, w2)
    True

    Or a non-overlapping one:

    >>> w3 = Way('3', nodes=[Node('18', latitude=51, longitude=7),
    ...                      Node('19', latitude=51, longitude=11),
    ...                      Node('20', latitude=47, longitude=11),
    ...                      Node('21', latitude=47, longitude=7),
    ...                      Node('18', latitude=51, longitude=7)])
    >>> ways_overlap(w1, w3)
    False

    Passing in a Way with too few points is an error:

    >>> w_open = Way('4', nodes=[Node('18', latitude=51, longitude=7),
    ...                          Node('19', latitude=51, longitude=11)])
    >>> ways_overlap(w1, w_open)
    Traceback (most recent call last):
      ...
    ValueError: A LinearRing must have at least 3 coordinate tuples
    """

    tuples_a = [(float(n.lon), float(n.lat)) for n in a]
    tuples_b = [(float(n.lon), float(n.lat)) for n in b]
    polygon_a = Polygon(tuples_a)
    polygon_b = Polygon(tuples_b)
    return polygon_a.intersects(polygon_b)

def group_boundaries_into_polygons(outer_ways, inner_ways):

    """Group outer_ways and inner_ways into distinct polygons

    Given a list of ways that represent the outer and inner boundaries
    of possibly disconnected polygons, find how to group them into an
    outer way, and inner ways that represent holes in that outer
    boundary.

    For example:

    >>> big_square = Way('1', nodes=[Node('10', latitude=53, longitude=0),
    ...                              Node('11', latitude=53, longitude=4),
    ...                              Node('12', latitude=49, longitude=4),
    ...                              Node('13', latitude=49, longitude=0),
    ...                              Node('10', latitude=53, longitude=0)])
    >>>
    >>> hole_in_big_square = Way('2', nodes=[Node('14', latitude=52, longitude=1),
    ...                                      Node('15', latitude=52, longitude=3),
    ...                                      Node('16', latitude=50, longitude=3),
    ...                                      Node('17', latitude=50, longitude=1),
    ...                                      Node('14', latitude=52, longitude=1)])
    >>>
    >>> isolated_square = Way('3', nodes=[Node('18', latitude=52, longitude=-3),
    ...                                   Node('19', latitude=52, longitude=-2),
    ...                                   Node('20', latitude=51, longitude=-2),
    ...                                   Node('21', latitude=51, longitude=-3),
    ...                                   Node('18', latitude=52, longitude=-3)])
    >>> outers = [big_square, isolated_square]
    >>> inners = [hole_in_big_square]
    >>> grouped = group_boundaries_into_polygons(outers, inners)
    >>> for p in grouped:
    ...     print p
    {'outer': [Way(id="1", nodes=5)], 'inner': [Way(id="2", nodes=5)]}
    {'outer': [Way(id="3", nodes=5)], 'inner': []}

    Any Way object that has too few points is ignored:

    >>> too_small_a = Way('4', nodes=[Node('22', latitude=53, longitude=0),
    ...                               Node('23', latitude=53, longitude=2),
    ...                               Node('24', latitude=53, longitude=0)])
    >>> too_small_b = Way('5', nodes=[Node('25', latitude=53, longitude=0),
    ...                               Node('26', latitude=51, longitude=2)])
    >>> outers.append(too_small_a)
    >>> inners.insert(0, too_small_b)
    >>> grouped_with_invalid_ways = group_boundaries_into_polygons(outers, inners)
    >>> grouped == grouped_with_invalid_ways
    True

    """

    # For each outer boundary, find all the inner paths that overlap
    # with it, and remove them from the list of inner paths to consider:

    result = []
    inner_ways_left = inner_ways[:]

    for outer_way in outer_ways:
        if len(outer_way) <= 3:
            continue
        polygon = { 'outer': [outer_way],
                    'inner': [] }
        for i in range(len(inner_ways_left) - 1, -1, -1):
            inner_way = inner_ways_left[i]
            if len(inner_way) <= 3:
                del inner_ways_left[i]
                continue
            if ways_overlap(inner_way, outer_way):
                polygon['inner'].append(inner_way)
                del inner_ways_left[i]
        result.append(polygon)

    return result

def kml_string(folder_name,
               placemark_name,
               extended_data,
               outer_ways,
               inner_ways):

    """Generate the contents of a KML files from Way objects

    For example, supposing we have these Ways:

    >>> big_square = Way('1', nodes=[Node('10', latitude=53, longitude=0),
    ...                              Node('11', latitude=53, longitude=4),
    ...                              Node('12', latitude=49, longitude=4),
    ...                              Node('13', latitude=49, longitude=0),
    ...                              Node('10', latitude=53, longitude=0)])
    >>>
    >>> hole_in_big_square = Way('2', nodes=[Node('14', latitude=52, longitude=1),
    ...                                      Node('15', latitude=52, longitude=3),
    ...                                      Node('16', latitude=50, longitude=3),
    ...                                      Node('17', latitude=50, longitude=1),
    ...                                      Node('14', latitude=52, longitude=1)])
    >>>
    >>> isolated_square = Way('3', nodes=[Node('18', latitude=52, longitude=-3),
    ...                                   Node('19', latitude=52, longitude=-2),
    ...                                   Node('20', latitude=51, longitude=-2),
    ...                                   Node('21', latitude=51, longitude=-3),
    ...                                   Node('18', latitude=52, longitude=-3)])
    >>> print kml_string('Example Folder',
    ...                  'Example Placemark',
    ...                  {"some key": "some value",
    ...                   "foo": "bar"},
    ...                  [big_square, isolated_square],
    ...                  [hole_in_big_square]),
    <?xml version='1.0' encoding='utf-8'?>
    <kml xmlns="http://earth.google.com/kml/2.1">
      <Folder>
        <name>Example Folder</name>
        <Placemark>
          <name>Example Placemark</name>
          <ExtendedData>
            <Data name="foo">
              <value>bar</value>
            </Data>
            <Data name="some key">
              <value>some value</value>
            </Data>
          </ExtendedData>
          <MultiGeometry>
            <Polygon>
              <outerBoundaryIs>
                <LinearRing>
                  <coordinates>0,53,0  4,53,0  4,49,0  0,49,0  0,53,0 </coordinates>
                </LinearRing>
              </outerBoundaryIs>
              <innerBoundaryIs>
                <LinearRing>
                  <coordinates>1,52,0  3,52,0  3,50,0  1,50,0  1,52,0 </coordinates>
                </LinearRing>
              </innerBoundaryIs>
            </Polygon>
            <Polygon>
              <outerBoundaryIs>
                <LinearRing>
                  <coordinates>-3,52,0  -2,52,0  -2,51,0  -3,51,0  -3,52,0 </coordinates>
                </LinearRing>
              </outerBoundaryIs>
            </Polygon>
          </MultiGeometry>
        </Placemark>
      </Folder>
    </kml>
    """

    kml = etree.Element("kml",
                        nsmap={None: "http://earth.google.com/kml/2.1"})
    folder = etree.SubElement(kml,"Folder")
    name = etree.SubElement(folder,"name")
    name.text = folder_name

    placemark = etree.SubElement(folder,"Placemark")
    name = etree.SubElement(placemark,"name")
    name.text = placemark_name

    extended = etree.SubElement(placemark, "ExtendedData")
    for k, v in sorted(extended_data.items()):
        data = etree.SubElement(extended, "Data",
                                attrib={"name": k})
        value = etree.SubElement(data, "value")
        value.text = v

    multigeometry = etree.SubElement(placemark, "MultiGeometry")

    for p in group_boundaries_into_polygons(outer_ways, inner_ways):
        polygon = etree.SubElement(multigeometry, "Polygon")
        all_ways = [(w, False) for w in p['outer']]
        all_ways += [(w, True) for w in p['inner']]
        for way, inner in all_ways:
            boundary_type = "inner" if inner else "outer"
            boundary = etree.SubElement(polygon, boundary_type+"BoundaryIs")
            linear_ring = etree.SubElement(boundary, "LinearRing")
            coordinates = etree.SubElement(linear_ring, "coordinates")
            coordinates.text = " ".join("%s,%s,0 " % n.lon_lat_tuple() for n in way.nodes)

    return etree.tostring(kml,
                          pretty_print=True,
                          encoding="utf-8",
                          xml_declaration=True)


def get_kml_for_osm_element_no_fetch(element):
    """Return KML for a boundary represented by a supplied OSM element

    >>> big_square = Way('1', nodes=[Node('10', latitude=53, longitude=0),
    ...                              Node('11', latitude=53, longitude=4),
    ...                              Node('12', latitude=49, longitude=4),
    ...                              Node('13', latitude=49, longitude=0),
    ...                              Node('10', latitude=53, longitude=0)])
    >>> kml, bbox = get_kml_for_osm_element_no_fetch(big_square)
    >>> bbox
    [(49.0, 0.0, 53.0, 4.0)]
    >>> print kml, # +doctest: ELLIPSIS
    <?xml version='1.0' encoding='utf-8'?>
    <kml xmlns="http://earth.google.com/kml/2.1">
      <Folder>
        <name>Boundaries for Unknown name for way with ID 1 [way 1] from OpenStreetMap</name>
        <Placemark>
          <name>Unknown name for way with ID 1</name>
          <ExtendedData/>
          <MultiGeometry>
            <Polygon>
              <outerBoundaryIs>
                <LinearRing>
                  <coordinates>0,53,0  4,53,0  4,49,0  0,49,0  0,53,0 </coordinates>
                </LinearRing>
              </outerBoundaryIs>
            </Polygon>
          </MultiGeometry>
        </Placemark>
      </Folder>
    </kml>

    It is an error to pass in a Node instead of a Relation or a Way:

    >>> n = Node('1', latitude=51, longitude=0)
    >>> get_kml_for_osm_element_no_fetch(n)
    Traceback (most recent call last):
      ...
    Exception: Unsupported element type in get_kml_for_osm_element(node, 1)

    And it's an error to pass in an unclosed Way:

    >>> unclosed_way = Way('1', nodes=[Node('10', latitude=53, longitude=0),
    ...                              Node('11', latitude=53, longitude=4),
    ...                              Node('12', latitude=49, longitude=4)])
    >>> kml, bbox = get_kml_for_osm_element_no_fetch(unclosed_way)
    Traceback (most recent call last):
      ...
    UnclosedBoundariesException
    """

    element_type, element_id = element.name_id_tuple()

    name = element.get_name()
    folder_name = u"Boundaries for %s [%s %s] from OpenStreetMap" % (name, element_type, element_id)

    if element_type == 'way':
        if not element.closed():
            raise UnclosedBoundariesException, "get_kml_for_osm_element called with an unclosed way (%s)" % (element_id)
        return (kml_string(folder_name,
                           name,
                           element.tags,
                           [element],
                           []),
                [element.bounding_box_tuple()])

    elif element_type == 'relation':

        outer_ways = join_way_soup(element.way_iterator(False))
        inner_ways = join_way_soup(element.way_iterator(True))

        bounding_boxes = [w.bounding_box_tuple() for w in outer_ways]

        extended_data = element.tags.copy()
        extended_data['osm'] = element_id

        return (kml_string(folder_name,
                           name,
                           element.tags,
                           outer_ways,
                           inner_ways),
                bounding_boxes)

    else:
        raise Exception, "Unsupported element type in get_kml_for_osm_element(%s, %s)" % (element_type, element_id)

def get_kml_for_osm_element(element_type, element_id):

    """Fetch an OSM element (if necessary) and return KML

    For example, we could fetch the boundary of the South
    Cambridgeshire (which has a hole in it, which is Cambridge) with:

    >>> kml, bbox = get_kml_for_osm_element('relation', '295353')
    >>> print kml, #doctest: +ELLIPSIS
    <?xml version='1.0' encoding='utf-8'?>
    <kml xmlns="http://earth.google.com/kml/2.1">
      <Folder>
        <name>Boundaries for South Cambridgeshire [relation 295353] from OpenStreetMap</name>
        <Placemark>
          <name>South Cambridgeshire</name>
          <ExtendedData>
            <Data name="admin_level">
              <value>8</value>
            </Data>
            <Data name="boundary">
              <value>administrative</value>
            </Data>
            <Data name="name">
              <value>South Cambridgeshire</value>
            </Data>
            <Data name="ons_code">
              <value>12UG</value>
            </Data>
            <Data name="source:ons_code">
              <value>OS_OpenData_CodePoint Codelist.txt</value>
            </Data>
            <Data name="type">
              <value>boundary</value>
            </Data>
            <Data name="wikipedia">
              <value>en:South Cambridgeshire</value>
            </Data>
          </ExtendedData>
          <MultiGeometry>
            <Polygon>
              <outerBoundaryIs>
                <LinearRing>
                  <coordinates>...</coordinates>
                </LinearRing>
              </outerBoundaryIs>
              <innerBoundaryIs>
                <LinearRing>
                  <coordinates>...</coordinates>
                </LinearRing>
              </innerBoundaryIs>
            </Polygon>
          </MultiGeometry>
        </Placemark>
      </Folder>
    </kml>

    If a relation can't be found, (None, None) is returned:

    >>> get_kml_for_osm_element('relation', '100000000000')
    (None, None)
    """

    e = fetch_osm_element(element_type, element_id)
    if e is None:
        return (None, None)

    return get_kml_for_osm_element_no_fetch(e)


if __name__ == "__main__":

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("--test", dest="doctest",
                      default=False, action='store_true',
                      help="Run all doctests in this file")

    (options, args) = parser.parse_args()

    if args:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

    if options.doctest:
        import doctest
        failure_count, test_count = doctest.testmod()
        sys.exit(0 if failure_count == 0 else 1)
    else:
        parser.print_help(file=sys.stderr)
        sys.exit(1)

########NEW FILE########
__FILENAME__ = get-boundaries-by-admin-level
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This script fetches all administrative and political boundaries from
# OpenStreetMap and writes them out as KML.

import xml.sax, urllib, os, re, errno, sys
from xml.sax.handler import ContentHandler
import urllib, urllib2

from boundaries import *
from generate_kml import *

if len(sys.argv) > 2:
    print >> sys.stderr, "Usage: %s [FIRST-MAPIT_TYPE]" % (sys.argv[0],)
    sys.exit(1)

start_mapit_type = 'O02'
if len(sys.argv) == 2:
    start_mapit_type = sys.argv[1]

dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(dir, '..', 'data')

def replace_slashes(s):
    return re.sub(r'/', '_', s)

mapit_type_to_tags = {
    # Administrative boundaries, each with a numbered admin_level:
    # http://wiki.openstreetmap.org/wiki/Tag:boundary%3Dadministrative
    'O02': {'boundary': 'administrative', 'admin_level': '2'},
    'O03': {'boundary': 'administrative', 'admin_level': '3'},
    'O04': {'boundary': 'administrative', 'admin_level': '4'},
    'O05': {'boundary': 'administrative', 'admin_level': '5'},
    'O06': {'boundary': 'administrative', 'admin_level': '6'},
    'O07': {'boundary': 'administrative', 'admin_level': '7'},
    'O08': {'boundary': 'administrative', 'admin_level': '8'},
    'O09': {'boundary': 'administrative', 'admin_level': '9'},
    'O10': {'boundary': 'administrative', 'admin_level': '10'},
    'O11': {'boundary': 'administrative', 'admin_level': '11'},
    # Also do political boundaries:
    # http://wiki.openstreetmap.org/wiki/Tag:boundary%3Dpolitical
    'OLC': {'boundary': 'political', 'political_division': 'linguistic_community'},
    'OIC': {'boundary': 'political', 'political_division': 'insular_council'},
    'OEC': {'boundary': 'political', 'political_division': 'euro_const'},
    'OCA': {'boundary': 'political', 'political_division': 'canton'},
    'OCL': {'boundary': 'political', 'political_division': 'circonscription_législative'},
    'OPC': {'boundary': 'political', 'political_division': 'parl_const'},
    'OCD': {'boundary': 'political', 'political_division': 'county_division'},
    'OWA': {'boundary': 'political', 'political_division': 'ward'},
}

if start_mapit_type not in mapit_type_to_tags.keys():
    print >> sys.stderr, "The type %s isn't known" % (start_mapit_type,)
    print >> sys.stderr, "The known types are:"
    for mapit_type in sorted(mapit_type_to_tags.keys()):
        print >> sys.stderr, " ", mapit_type
    sys.exit(1)

reached_first_mapit_type = False

for mapit_type, required_tags in sorted(mapit_type_to_tags.items()):

    if not reached_first_mapit_type:
        if mapit_type == start_mapit_type:
            reached_first_mapit_type = True
        else:
            print "Haven't reached the first MapIt type, skipping", mapit_type
            continue

    print "Fetching data for MapIt type", mapit_type

    file_basename = mapit_type + ".xml"
    output_directory = os.path.join(data_dir, "cache-with-political")
    xml_filename = os.path.join(output_directory, file_basename)
    query = get_query_relations_and_ways(required_tags)
    get_osm3s(query, xml_filename)

    level_directory = os.path.join(output_directory, mapit_type)
    mkdir_p(level_directory)

    def handle_top_level_element(element_type, element_id, tags):

        for required_key, required_value in required_tags.items():

            if required_key not in tags:
                return
            if tags[required_key] != required_value:
                return

        name = get_name_from_tags(tags, element_type, element_id)

        print "Considering admin boundary:", name.encode('utf-8')

        try:

            basename = "%s-%s-%s" % (element_type,
                                     element_id,
                                     replace_slashes(name))

            filename = os.path.join(level_directory, u"%s.kml" % (basename,))

            if not os.path.exists(filename):

                kml, _ = get_kml_for_osm_element(element_type, element_id)
                if not kml:
                    print "      No data found for %s %s" % (element_type, element_id)
                    return

                print "      Writing KML to", filename.encode('utf-8')
                with open(filename, "w") as fp:
                    fp.write(kml)

        except UnclosedBoundariesException:
            print "      ... ignoring unclosed boundary"

    parse_xml_minimal(xml_filename, handle_top_level_element)

########NEW FILE########
__FILENAME__ = scrape_admin_boundaries_tables
#!/usr/bin/env python

import sys, re
from bs4 import BeautifulSoup
import urllib2

url = "http://wiki.openstreetmap.org/wiki/Tag:boundary%3Dadministrative"

f = urllib2.urlopen(url)
data = f.read()
f.close()

soup = BeautifulSoup(data, "lxml")

def strip_all_tags(element):
    for br in element.find_all('br'):
        br.replaceWith(u"\n")
    return "".join(element.findAll(text=True)).strip()

# Tidy up the country name column - I'm not sure there's an obviously
# smarter way of doing this for the moment:

def get_country_name(s):
    if re.search('(?s)new levels.*Germany', s):
        return 'Germany'
    result = re.sub(r' +[\(/].*', '', s)
    result = re.sub(r'(?ms)$.*', '', result)
    result = re.sub(r'\s+(see also|has it)', '', result)
    result = re.sub(r'(Poland|Portugal|France|Georgia|Germany).*', '\\1', result)
    result = re.sub(r'^(?u)Flag of Isle of Man\s+', '', result)
    return result

def make_missing_none(s):
    if re.search('(?uis)^\s*N/A\s*$', s):
        return None
    else:
        return s

country_to_admin_levels = {}

for table in soup.find_all('table', 'wikitable'):
    rows = table.findAll('tr', recursive=False)
    for row in rows:
        ths = row.findAll('th', recursive=False)
        if ths:
            headers = [th.string.strip() for th in ths]
            continue
        tds = row.findAll('td', recursive=False)
        if len(tds) <= 2:
            continue
        country_name = get_country_name(strip_all_tags(tds[0]))
        if len(tds) != len(headers):
            print >> sys.stderr, "Warning: Ignoring row of unexpected length", len(tds)
            continue
        levels = [None]
        levels += [make_missing_none(strip_all_tags(td))
                   for td in tds[1:]]
        if country_name in country_to_admin_levels:
            print >> sys.stderr, "Warning: Overwriting previous information for country '%s'" % (country_name,)
        country_to_admin_levels[country_name] = levels

for country_name, levels in sorted(country_to_admin_levels.items()):
    print "####", country_name.encode('utf-8')
    for i, s in enumerate(levels):
        print "---- level", i
        if s:
            print "  " + s.encode('utf-8')
        else:
            print "  [No information]"

########NEW FILE########
__FILENAME__ = subdivide-new-cache
#!/usr/bin/env python

import re
from boundaries import *

script_directory = os.path.dirname(os.path.abspath(__file__))

cache_directory = os.path.realpath(os.path.join(script_directory,
                                                '..',
                                                'data',
                                                'new-cache'))

for old_filename in os.listdir(cache_directory):
    print "filename is", old_filename
    m = re.search(r'^(way|node|relation)-(\d+)\.xml$', old_filename)
    if not m:
        print >> sys.stderr, "Ignoring file:", old_filename
        continue
    element_type, element_id = m.groups()
    full_new_filename = get_cache_filename(element_type, element_id)
    full_old_filename = os.path.join(cache_directory,
                                     old_filename)
    os.rename(full_old_filename, full_new_filename)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django.contrib.gis import admin
from mapit.models import Area, Code, Name, Generation, Geometry, Postcode, Type, NameType, CodeType, Country

class NameInline(admin.TabularInline):
    model = Name

class CodeInline(admin.TabularInline):
    model = Code

class AreaAdmin(admin.OSMGeoAdmin):
    list_filter = ('type', 'country')
    list_display = ('name', 'type', 'country', 'generation_low', 'generation_high', 'parent_area', 'geometries_link')
    search_fields = ('names__name',)
    raw_id_fields = ('parent_area',)
    inlines = [
        NameInline,
        CodeInline,
    ]

    def geometries_link(self, obj):
        return '<a href="../geometry/?area=%d">Shapes</a>' % obj.id
    geometries_link.allow_tags = True

class GeometryAdmin(admin.OSMGeoAdmin):
    raw_id_fields = ('area',)

class GenerationAdmin(admin.OSMGeoAdmin):
    list_display = ('id', 'active', 'created', 'description')

class PostcodeAdmin(admin.OSMGeoAdmin):
    search_fields = ['postcode']
    raw_id_fields = ('areas',)

class TypeAdmin(admin.OSMGeoAdmin):
    pass

class NameTypeAdmin(admin.OSMGeoAdmin):
    pass

class CodeTypeAdmin(admin.OSMGeoAdmin):
    pass

class CountryAdmin(admin.OSMGeoAdmin):
    pass

admin.site.register(Area, AreaAdmin)
admin.site.register(Geometry, GeometryAdmin)
admin.site.register(Generation, GenerationAdmin)
admin.site.register(Postcode, PostcodeAdmin)
admin.site.register(Type, TypeAdmin)
admin.site.register(CodeType, CodeTypeAdmin)
admin.site.register(NameType, NameTypeAdmin)
admin.site.register(Country, CountryAdmin)

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings

def country(request):
    return { 'country': settings.MAPIT_COUNTRY }

def analytics(request):
    return { 'GOOGLE_ANALYTICS': settings.GOOGLE_ANALYTICS }

########NEW FILE########
__FILENAME__ = 2009-10
# A control file for importing Boundary-Line.
# Not all areas have ONS codes, so we have to have something
# manual to e.g. tell us if some WMC have changed.
#
# Things without ONS codes: CED EUR GLA LAC SPC SPE WAC WAE WMC
# 
# For Oct 2009, it doesn't matter what this returns, as it's
# the first Open version and the database will/should be empty.
#
# This edition of Boundary-Line uses the old SNAC codes

def code_version():
    return 'ons'

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match"""
    return False


########NEW FILE########
__FILENAME__ = 2010-05
# A control file for importing Boundary-Line.
# Not all areas have ONS codes, so we have to have something
# manual to e.g. tell us if some WMC have changed.
#
# Things without ONS codes: CED EUR GLA LAC SPC SPE WAC WAE WMC
# 
# For May 2010, England and Wales WMC are all new. I think that's it!
#
# This edition of Boundary-Line uses the old SNAC codes

def code_version():
    return 'ons'

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match"""
    if type == 'WMC' and country in ('E', 'W'):
        return True
    return False


########NEW FILE########
__FILENAME__ = 2010-10
# A control file for importing Boundary-Line.
# Not all areas have ONS codes, so we have to have something
# manual to e.g. tell us if some WMC have changed.
#
# Things without ONS codes: CED EUR GLA LAC SPC SPE WAC WAE WMC
# 
# This edition of Boundary-Line uses the new SNAC codes

import re

def code_version():
    return 'gss'

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match"""

    return False

########NEW FILE########
__FILENAME__ = 2011-05
# A control file for importing Boundary-Line.
# CEDs don't have ONS codes, so we have to have something manual
# to e.g. tell us if some county council wards have changed.
# 
# This edition of Boundary-Line uses the new SNAC codes

from areas.models import Area, Generation

def code_version():
    return 'gss'

# Renames
# Eastleigh: Parish of Allbrook renamed Allbrook and North Boyatt 
# North Norfolk: Parish of Aldborough renamed  Aldborough & Thurgarton 
# Sevenoaks: Ash Ward renamed  Ash and New Ash Green 
# Harrogate: Parish of Markingfield renamed Markenfield
# Wiltshire: Parishes of Allcannings and Bower Chalke renamed All Cannings and Bowerchalke 

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match against ONS code,
       or an Area to be used as an override instead"""

    # There appears to be a regression, in that new areas introduced, I
    # believe, correctly by October 2010 Boundary-Line (due to WSI 2010/1481:
    # http://www.legislation.gov.uk/wsi/2010/1451/contents/made )
    # have disappeared from May 2011 and it has the previous areas.
    if type == 'UTE' and name in ('Sully ED', 'Dinas Powys ED', 'Plymouth ED', 'Llandough ED'):
        area_within = Area.objects.filter(type__code='UTA', polygons__polygon__contains=geometry.geos.point_on_surface)[0]
        if area_within.name == 'Vale of Glamorgan Council':
            current = Generation.objects.current()
            return Area.objects.get(names__name=name, names__type='O', parent_area=area_within,
                generation_low__lte=current, generation_high__gte=current)

    # The Scottish Parliament has had boundary changes. New Boundary-Line has
    # ONS codes for this too, hooray!

    # The following have had boundary changes for the 2011 elections, but all
    # have ONS codes and so can be ignored/ detected that way:
    #  
    # Redrawn boundaries
    # 2011/3   Cheshire East
    # 2011/4   Cheshire West and Chester
    # 2011/161 Bedford
    # 2011/162 Central Bedfordshire
    # 2011/163 Mansfield
    # 2011/164 Northampton
    # 2011/165 South Derbyshire
    # 2011/166 Sedgemoor
    # 2011/167 Stoke-on-Trent
    # 2011/168 West Somerset
    #  
    # Minor changes
    # 2008/176  Maidston
    # 2008/178  Uttlesford
    # 2008/748  2009/533 Stratford-on-Avon
    # 2009/532  Tewkesbury
    # 2009/538  North Norfolk
    # 2009/540  Pendle
    # 2009/542  Mid Devon
    # 2009/543  East Devon
    # 2009/2786 Kettering
    # 2010/684  Huntingdonshire
    # 2010/687  Wellingborough
    # 2010/2108 Tonbridge and Malling
    # 2010/2109 Kirklees
    # 2010/2788 Teignbridge
    # 2010/2943 North Somerset
    # 2011/404  New Forest
    # 2011/406  Rotherham

    # S2010/353 East Dunbarton/ Glasgow

    return False

########NEW FILE########
__FILENAME__ = 2011-10
# A control file for importing October 2011 Boundary-Line.
# 
# Notes for this edition:
# 
# * Two CEDs have had their names changed (no GSS codes so can't match up
# automatically) - Okhey Park ED to Oxhey Park ED, and Bested ED to Bersted ED.
# Here's the SQL used to fix this, using our own IDs (yours may differ):
#
# update areas_name set name='Oxhey Park ED' where area_id=15065 and type='O';
# update areas_area set name='Oxhey Park' where id=15065;
# update areas_name set name='Bersted ED' where area_id=53226 and type='O';
# update areas_area set name='Bersted' where id=53226;
#
# * Ordnance Survey changed the IDs of the wrong areas in two cases in the May
# 2011 Boundary-Line. E05004368 became E05008570, when it was E05004419 that
# should have become that. And E04008791 became E04012125 rather than
# E04008782. This edition corrects this, but the damage in mapit has already
# been done. Manually fixed before running import_boundary_line using the below
# SQL, again, using our hard-coded IDs.
#
# update areas_code set code='E05004368' where type='gss' and area_id=135066; -- Should have been all along
# delete from areas_code where code='E05004368' and type='gss' and area_id=4526; -- Can't have two areas with same GSS code
# update areas_code set code='E04008791' where type='gss' and area_id=135448;
# delete from areas_code where code='E04008791' and type='gss' and area_id=60017;
#
# This means the E04008782 and E05004419 areas contain new boundaries, rather
# than old, which were lost by the May 2011 import. This could be manually
# fixed if necessary by importing those two areas from the old Boundary-Line.

def code_version():
    return 'gss'

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match"""

    return False

########NEW FILE########
__FILENAME__ = 2012-05
# A control file for importing May 2012 Boundary-Line. This control file
# assumes previous Boundary-Lines have been imported, because it uses that
# information. If this is a first import, use the first-gss control file.

from areas.models import Area, Generation

def code_version():
    return 'gss'

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match against ONS code,
       or an Area to be used as an override instead"""

    # There is a problem, in that users of this service, including ourselves,
    # have assumed a mapit ID is an identifier for a concept, rather than a
    # particular boundary. Until now, this has not really been an issue, but
    # this edition of Boundary-Line changes the boundary of four councils,
    # assigning them new ONS IDs in the process. This would cause some amount
    # of pain for code that assumes e.g. ID 2579 is the concept of Glasgow City
    # Council, rather than the boundary of Glasgow City Council from
    # generations 1 to 16 (but then not 17).
    #
    # Therefore, for the time being, we have decided to match up the new
    # boundaries with the current mapit IDs for these four councils. The old
    # boundaries will be lost from mapit, but could be loaded in manually from
    # the last edition of Boundary-Line if we really wanted, assigned new IDs.
    #
    # In the future, perhaps the current IDs should host the concept, for
    # continuity, and the current and historical boundaries are then available
    # under it in some way. Tricky.
    #
    # NB: After import_boundary_line is run with this control file, the GSS
    # codes of these four councils will need updating to their new entries, as
    # it will have maintained the old codes.
    
    if ( type == 'UTA' and name in ('Glasgow City', 'East Dunbartonshire') ) \
    or ( type == 'DIS' and name in ('St. Albans District (B)', 'Welwyn Hatfield District (B)') ):
        current = Generation.objects.current()
        return Area.objects.get(names__name=name, names__type='O',
            generation_low__lte=current, generation_high__gte=current)

    # The following have had boundary changes for the 2012 elections, but all
    # have ONS codes and so can be ignored/ detected that way:
    #  
    # Glasgow/E Dunb.	2010/353
    # Huntingdonshire	2010/684
    # Epping Forest	2011/2764 (minor)
    # Swansea		2011/2932
    # Swindon		2012/2
    # Hartlepool	2012/3
    # Rugby		2012/4
    # Broxbourne	2012/159
    # Daventry		2012/160
    # Rushmoor		2012/161
    # Welwyn/St Albans	2012/667

    return False


########NEW FILE########
__FILENAME__ = 2012-10
# A control file for importing October 2012 Boundary-Line.
#
# Nothing special to do, hooray.

def code_version():
    return 'gss'

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match"""
    return False

########NEW FILE########
__FILENAME__ = 2013-05
# A control file for importing Boundary-Line.
# CEDs (county council electoral divisions) don't have ONS codes, so we have to
# have something manual as this is a year of county council boundary changes.
#
# The following counties have had full boundary changes (with Statutory
# Instrument number):
# - Buckinghamshire     2012/1396
# - Cumbria             2012/3113
# - Derbyshire          2012/2986
# - Gloucestershire     2012/877
# - Northamptonshire    2013/68
# - Oxfordshire         2012/1812
# - Somerset            2012/2984
# - Staffordshire       2012/875
# - Surrey              2012/1872
#
# The following have had minor changes:
# - Cambridgeshire      2012/51
# - Devon               2010/2788
# - Essex               2011/2764
# - Kent                2010/2108
# - Leicestershire      2012/2854
# - Norfolk             2012/3260 2013/220
# - North Yorkshire     2012/3150 2013/221

from mapit.models import Area

COUNTIES = [
    'Buckinghamshire', 'Cumbria', 'Derbyshire', 'Gloucestershire',
    'Northamptonshire', 'Oxfordshire', 'Somerset', 'Staffordshire', 'Surrey'
]
COUNTIES = [ "%s County Council" % c for c in COUNTIES ]

def code_version():
    return 'gss'

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match"""

    if type != 'CED': return False

    # Make sure CEDs are loaded *after* CTY
    area_within = Area.objects.filter(type__code='CTY', polygons__polygon__contains=geometry.geos.point_on_surface)[0]
    if area_within.name in COUNTIES:
        return True

    # The following have had boundary changes for the 2013 elections, but all
    # have ONS codes and so can be ignored/ detected that way:
    #
    # Anglesey          2012/2676 (W290)
    # Cornwall          2011/1
    # Durham            2012/1394
    # Northumberland    2011/2
    # Shropshire        2012/2935 (minor)

    return False

########NEW FILE########
__FILENAME__ = 2013-10
# A control file for importing October 2013 Boundary-Line.

# This control file assumes previous Boundary-Lines have been imported,
# because it uses that information. If this is a first import, use the
# first-gss control file.

from ..models import Area, Generation

def code_version():
    return 'gss'

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match against
    an ONS code, or an Area to be used as an override instead."""

    # See 2012-05.py for a better explanation of what we're doing here and why.

    # We're basically manually overriding the area that gets updated for some
    # of the areas in this edition of the boundary line, because we want their
    # Mapit ID numbers to stay the same, but they have new GSS codes, so they
    # would normally be created as new areas.

    # The following Welsh Assembly regions and constituencies changed as part
    # of SI 2011/2987, but we don't need to worry about them because we don't
    # store their IDs anywhere that'll break.
    # 'South Wales West Assembly ER',
    # 'South Wales East Assembly ER',
    # 'South Wales Central Assembly ER',
    # 'Mid and West Wales Assembly ER'
    # These Welsh constituencies also changed, but we don't need to worry
    # about them either:
    # 'Brecon and Radnorshire Assembly Const',
    # 'Vale of Glamorgan Assembly Const',
    # 'Pontypridd Assembly Const',
    # 'Cardiff North Assembly Const',
    # 'Merthyr Tydfil and Rhymney Assembly Const',
    # 'Ogmore Assembly Const',
    # 'Cardiff South and Penarth Assembly Const',

    # These districts changed as part of SI 2013/596, we need to keep their
    # IDs the same because FixMyStreet stores them in it's DB.
    overriden_dis_areas = (
        'East Hertfordshire District',
        'Stevenage District (B)'
    )
    # These wards which changed because of 2013/596, but we don't mind that:
    # Walkern Ward - DIW
    # Manor Ward - DIW

    # These Unitary Authorities which changed in 2013/595, we also need to
    # maintain old IDs for:
    # Northumberland
    # Gateshead District (B)

    # There were two ward which changed in 2013/595 too, but we don't care
    # about that.
    # South Tynedale ED - UTE
    # Chopwell & Rowlands Gill - MTW

    # The following Parish Council's changed, but because we don't rely on
    # their ID numbers, we don't care that they make new ones.
    # Walkern CP - CPC
    # Wootton CP - CPC
    # Hardingstone CP - CPC
    # Upton CP - CPC
    # Great Houghton CP - CPC
    # Hedley CP - CPC
    # Collingtree CP - CPC

    # These are new and they actually are new, but they have a GSS code, so
    # the import command will find them on it's own:
    # West Hunsbury CP - CPC
    # Hunsbury Meadows CP - CPC

    current = Generation.objects.current()

    if (type == 'UTA' and name == 'Northumberland') \
       or (type == 'MTD' and name == 'Gateshead District (B)') \
       or (type == 'DIS' and name in overriden_dis_areas):
        return Area.objects.get(names__name=name, names__type__code='O',
            generation_low__lte=current, generation_high__gte=current)

    # This is the default
    return False

########NEW FILE########
__FILENAME__ = first-gss
# A control file for importing Boundary-Line.
# Not all areas have ONS codes, so we have to have something
# manual to e.g. tell us if some WMC have changed.
#
# Things without new ONS codes: CED
# 
# This edition of Boundary-Line uses the new SNAC codes

def code_version():
    return 'gss'

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match"""
    return False


########NEW FILE########
__FILENAME__ = first-ons
# A control file for importing Boundary-Line.
# Not all areas have ONS codes, so we have to have something
# manual to e.g. tell us if some WMC have changed.
#
# Things without ONS codes: CED EUR GLA LAC SPC SPE WAC WAE WMC
# 
# For Oct 2009, it doesn't matter what this returns, as it's
# the first Open version and the database will/should be empty.
#
# This edition of Boundary-Line uses the old SNAC codes

def code_version():
    return 'ons'

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match"""
    return False


########NEW FILE########
__FILENAME__ = possible-future
# A control file for importing Boundary-Line.
# CEDs don't have ONS codes, so we have to have something manual
# to e.g. tell us if some county council wards have changed.
# 
# In the future, a county council (CTY) may have boundary changes to its
# electoral divisions (CED). It's the only one that's tricky, as the others
# will all change at once, but not all CEDs will be changing.
#
# In this example, Buckinghamshire County Council has had boundary changes.
#
# This edition of Boundary-Line uses the new SNAC codes

import re

def code_version():
    return 'gss'

def check(name, type, country, geometry):
    """Should return True if this area is NEW, False if we should match"""

    if type != 'CED': return False

    # Make sure CEDs are loaded *after* CTY
    area_within = Area.objects.filter(type__code='CTY', polygons__polygon__contains=geometry.geos.point_on_surface)[0]
    if re.search('Buckinghamshire(?i)', area_within.name):
        return True

    return False


########NEW FILE########
__FILENAME__ = gb
import re

from django.http import HttpResponse, HttpResponseRedirect

from mapit.shortcuts import get_object_or_404

def area_code_lookup(request, area_id, format):
    from mapit.models import Area, CodeType
    area_code = None
    if re.match('\d\d([A-Z]{2}|[A-Z]{4}|[A-Z]{2}\d\d\d|[A-Z]|[A-Z]\d\d)$', area_id):
        area_code = CodeType.objects.get(code='ons')
    elif re.match('[EW]0[12]\d{6}$', area_id): # LSOA/MSOA have ONS code type
        area_code = CodeType.objects.get(code='ons')
    elif re.match('[ENSW]\d{8}$', area_id):
        area_code = CodeType.objects.get(code='gss')
    if not area_code:
        return None

    args = { 'format': format, 'codes__type': area_code, 'codes__code': area_id }
    if re.match('[EW]01', area_id):
        args['type__code'] = 'OLF'
    elif re.match('[EW]02', area_id):
        args['type__code'] = 'OMF'

    area = get_object_or_404(Area, **args)
    path = '/area/%d%s' % (area.id, '.%s' % format if format else '')
    # If there was a query string, make sure it's passed on in the
    # redirect:
    if request.META['QUERY_STRING']:
        path += "?" + request.META['QUERY_STRING']
    return HttpResponseRedirect(path)

def canonical_postcode(pc):
    pc = re.sub('[^A-Z0-9]', '', pc.upper())
    return pc

def is_special_postcode(pc):
    if pc in (
        'ASCN1ZZ', # Ascension Island
        'BBND1ZZ', # BIOT
        'BIQQ1ZZ', # British Antarctic Territory
        'FIQQ1ZZ', # Falkland Islands
        'PCRN1ZZ', # Pitcairn Islands
        'SIQQ1ZZ', # South Georgia and the South Sandwich Islands
        'STHL1ZZ', # St Helena
        'TDCU1ZZ', # Tristan da Cunha
        'TKCA1ZZ', # Turks and Caicos Islands
        'GIR0AA', 'G1R0AA', # Girobank
        'SANTA1', # Santa Claus
    ):
        return True
    return False

def is_valid_postcode(pc):
    # Our test postcode
    if pc in ('ZZ99ZZ', 'ZZ99ZY'): return True

    if is_special_postcode(pc): return True

    # See http://www.govtalk.gov.uk/gdsc/html/noframes/PostCode-2-1-Release.htm
    inward = 'ABDEFGHJLNPQRSTUWXYZ'
    fst = 'ABCDEFGHIJKLMNOPRSTUWYZ'
    sec = 'ABCDEFGHJKLMNOPQRSTUVWXY'
    thd = 'ABCDEFGHJKSTUW'
    fth = 'ABEHMNPRVWXY'

    if re.match('[%s][1-9]\d[%s][%s]$' % (fst, inward, inward), pc) or \
        re.match('[%s][1-9]\d\d[%s][%s]$' % (fst, inward, inward), pc) or \
        re.match('[%s][%s]\d\d[%s][%s]$' % (fst, sec, inward, inward), pc) or \
        re.match('[%s][%s][1-9]\d\d[%s][%s]$' % (fst, sec, inward, inward), pc) or \
        re.match('[%s][1-9][%s]\d[%s][%s]$' % (fst, thd, inward, inward), pc) or \
        re.match('[%s][%s][1-9][%s]\d[%s][%s]$' % (fst, sec, fth, inward, inward), pc):
        return True

    return False

def is_valid_partial_postcode(pc):
    # Our test postcode
    if pc == 'ZZ9': return True
    
    # See http://www.govtalk.gov.uk/gdsc/html/noframes/PostCode-2-1-Release.htm
    fst = 'ABCDEFGHIJKLMNOPRSTUWYZ'
    sec = 'ABCDEFGHJKLMNOPQRSTUVWXY'
    thd = 'ABCDEFGHJKSTUW'
    fth = 'ABEHMNPRVWXY'
  
    if re.match('[%s][1-9]$' % (fst), pc) or \
        re.match('[%s][1-9]\d$' % (fst), pc) or \
        re.match('[%s][%s]\d$' % (fst, sec), pc) or \
        re.match('[%s][%s][1-9]\d$' % (fst, sec), pc) or \
        re.match('[%s][1-9][%s]$' % (fst, thd), pc) or \
        re.match('[%s][%s][1-9][%s]$' % (fst, sec, fth), pc):
        return True

    return False

def get_postcode_display(pc):
    return re.sub('(...)$', r' \1', pc).strip()

def augment_postcode(postcode, result):
    pc = postcode.postcode
    if is_special_postcode(pc): return
    if pc[0:2] == 'BT':
        loc = postcode.as_irish_grid()
        result['coordsyst'] = 'I'
    else:
        loc = postcode.location
        loc.transform(27700)
        result['coordsyst'] = 'G'
    result['easting'] = int(round(loc[0]))
    result['northing'] = int(round(loc[1]))

# Hacky function to restrict certain geographical links in the HTML pages to
# types to make them more likely to return results.
def restrict_geo_html(area):
    geotype = {}
    if area.type.code == 'EUR':
        geotype = { 'touches': ['EUR'], 'overlaps': ['UTA'], 'covers': ['UTA'], 'coverlaps': ['UTA'] }
    elif area.type.code in ('CTY', 'UTA'):
        geotype = { 'touches': ['CTY','DIS','MTD','LBO','COI','UTA'], 'overlaps': ['WMC'], 'covers': ['CED','DIW','MTW','LBW','UTE','UTW'], 'coverlaps': ['CED','DIW','MTW','LBW','UTE','UTW'] }
    elif area.type.code == 'COI':
        geotype = { 'covers': ['CPC'], 'coverlaps': ['CPC'] }
    elif area.type.code == 'LGD':
        geotype = { 'overlaps': ['LGE','LGW'], 'coverlaps': ['LGE','LGW'] }
    elif area.type.code == 'GLA':
        geotype = { 'touches': ['CTY','UTA'], 'overlaps': ['WMC'], 'covers': ['LBO'], 'coverlaps': ['WMC'] }
    elif area.type.code == 'SPE':
        geotype = { 'touches': ['SPE'], 'overlaps': ['UTA'], 'covers': ['UTA'], 'coverlaps': ['UTA'] }
    elif area.type.code == 'WAE':
        geotype = { 'touches': ['WAE'], 'overlaps': ['UTA'], 'covers': ['UTA'], 'coverlaps': ['UTA'] }
    for k, v in geotype.items():
        geotype[k] = [ '?type=%s' % ','.join(v), ' (%s)' % ', '.join(v) ]
    return geotype


########NEW FILE########
__FILENAME__ = no
import re

# SRID to also output area geometry information in
area_geometry_srid = 32633

# Norwegian postcodes are four digits. Some put "no-" in front, but
# this is ignored here.
def is_valid_postcode(pc):
    if re.match('\d{4}$', pc):
        return True
    return False

# Should match one, two and three digits.
def is_valid_partial_postcode(pc):
    if re.match('\d{1,3}$', pc):
        return True
    return False


########NEW FILE########
__FILENAME__ = osm
import re

def sorted_areas(areas):
    return sorted(list(areas), key=lambda a: (a.type.code, a.name))

########NEW FILE########
__FILENAME__ = djangopatch
from django.db.models.sql import RawQuery
from django.db.models.query import RawQuerySet

# This monkeypatches RawQuery/RawQuerySet so that validate_sql (which simply
# checks the query starts with SELECT) isn't called, as it isn't for our query
# and we know what we're doing. This restriction was removed in Django 1.3.

class NoValidateRawQuery(RawQuery):
    def __init__(self, sql, using, params=None):
        # XXX NOT REQUIRED self.validate_sql(sql)
        self.params = params or ()
        self.sql = sql
        self.using = using
        self.cursor = None

        # Mirror some properties of a normal query so that
        # the compiler can be used to process results.
        self.low_mark, self.high_mark = 0, None  # Used for offset/limit
        self.extra_select = {}
        self.aggregate_select = {}

class NoValidateRawQuerySet(RawQuerySet):
    def __init__(self, raw_query, model=None, query=None, params=None,
        translations=None, using=None):
        self.raw_query = raw_query
        self.model = model
        self._db = using
        self.query = query or NoValidateRawQuery(sql=raw_query, using=self.db, params=params)
        self.params = params or ()
        self.translations = translations or {}




########NEW FILE########
__FILENAME__ = loader
"""
Wrapper for loading templates from "templates" directories in INSTALLED_APPS
packages. Copy of built-in function, with additional path for MAPIT_COUNTRY,
as we want templates to override in order like TEMPLATE_DIRS but within an app.
"""

import os
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateDoesNotExist
from django.utils._os import safe_join
from django.utils.importlib import import_module

# At compile time, cache the directories to search.
fs_encoding = sys.getfilesystemencoding() or sys.getdefaultencoding()
app_template_dirs = []
for app in settings.INSTALLED_APPS:
    try:
        mod = import_module(app)
    except ImportError, e:
        raise ImproperlyConfigured, 'ImportError %s: %s' % (app, e.args[0])
    template_dir = os.path.join(os.path.dirname(mod.__file__), 'templates')
    if os.path.isdir(template_dir):
        if settings.MAPIT_COUNTRY:
            app_template_dirs.append(os.path.join(template_dir, settings.MAPIT_COUNTRY.lower()).decode(fs_encoding))
        app_template_dirs.append(template_dir.decode(fs_encoding))

# It won't change, so convert it to a tuple to save memory.
app_template_dirs = tuple(app_template_dirs)

def get_template_sources(template_name, template_dirs=None):
    """
    Returns the absolute paths to "template_name", when appended to each
    directory in "template_dirs". Any paths that don't lie inside one of the
    template dirs are excluded from the result set, for security reasons.
    """
    if not template_dirs:
        template_dirs = app_template_dirs
    for template_dir in template_dirs:
        try:
            yield safe_join(template_dir, template_name)
        except UnicodeDecodeError:
            # The template dir name was a bytestring that wasn't valid UTF-8.
            raise
        except ValueError:
            # The joined path was located outside of template_dir.
            pass

def load_template_source(template_name, template_dirs=None):
    for filepath in get_template_sources(template_name, template_dirs):
        try:
            return (open(filepath).read().decode(settings.FILE_CHARSET), filepath)
        except IOError:
            pass
    raise TemplateDoesNotExist, template_name
load_template_source.is_usable = True

########NEW FILE########
__FILENAME__ = mapit_delete_areas_from_new_generation
# This script deletes all the areas from the new generation (i.e. the
# most recent inactive one).

from optparse import make_option
from django.core.management.base import NoArgsCommand
from mapit.models import Generation, Area

class Command(NoArgsCommand):
    help = 'Remove all areas from the new (inactive) generation'
    args = '<GENERATION-ID>'
    option_list = NoArgsCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit',
                    help='Actually update the database'),)

    def handle(self, **options):
        new = Generation.objects.new()
        if not new:
            raise CommandError, "There's no new inactive generation to delete areas from"

        generations = list(Generation.objects.all().order_by('id'))
        if len(generations) <= 1:
            previous_generation = None
        else:
            previous_generation = generations[-2]

        for area in Area.objects.filter(generation_low__lte=new, generation_high__gte=new):

            print "Considering", area

            g_low = area.generation_low
            g_high = area.generation_high

            if g_low not in generations:
                raise Exception, "area.generation_low was " + g_low + ", which no longer exists!"
            if g_high not in generations:
                raise Exception, "area.generation_high was " + g_high + ", which no longer exists!"

            if area.generation_low == new and area.generation_high == new:
                print "  ... only exists in", new, "so will delete"
                if options['commit']:
                    area.delete()
                    print "  ... deleted."
                else:
                    print "  ... not deleting, since --commit wasn't specified"
            elif area.generation_low.id < new.id and area.generation_high == new:
                print "  ... still exists in an earlier generation, so lowering generation_high to", previous_generation
                area.generation_high = previous_generation
                if options['commit']:
                    area.save()
                    print "  ... lowered."
                else:
                    print "  ... not lowering, since --commit wasn't specified"

            elif area.generation_high.id > new.id:
                # This should never happen - it'd mean the
                # implementation of Generation.objects.new() has
                # changed or something else is badly wrong:
                message = "Somehow area.generation_high (" + \
                    str(area.generation_high) + \
                    ") is after Generation.objects.new() (" + \
                    str(new) + ")"
                raise Exception, message

########NEW FILE########
__FILENAME__ = mapit_generation_activate
# This script activates the currently inactive generation.

from optparse import make_option
from django.core.management.base import NoArgsCommand
from mapit.models import Generation

class Command(NoArgsCommand):
    help = 'Actives the inactive generation'
    option_list = NoArgsCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    def handle(self, **options):
        new = Generation.objects.new()
        if not new:
            raise Exception, "You do not have an inactive generation to activate"

        new.active = True
        if options['commit']:
            new.save()
            print "%s - activated" % new
        else:
            print "%s - not activated, dry run" % new

########NEW FILE########
__FILENAME__ = mapit_generation_create
# This script is used to create a new inactive generation for
# inputting new boundaries of some sort.

from optparse import make_option
from django.core.management.base import NoArgsCommand
from mapit.models import Generation

class Command(NoArgsCommand):
    help = 'Create a new generation'
    option_list = NoArgsCommand.option_list + (
        make_option('--desc', action='store', dest='desc', help='Description of this generation'),
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    def handle(self, **options):
        new_generation = Generation.objects.new()
        if new_generation:
            raise Exception, "You already have an inactive generation"

        if not options['desc']:
            raise Exception, "You must specify a generation description"

        g = Generation(description=options['desc'])
        print "Creating generation..."
        if options['commit']:
            g.save()
            print "...saved: %s" % g
        else:
            print "...not saving, dry run"

########NEW FILE########
__FILENAME__ = mapit_generation_deactivate
# This script deactivates a particular generation

from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from mapit.models import Generation

class Command(BaseCommand):
    help = 'Deactivate a generation'
    args = '<GENERATION-ID>'
    option_list = BaseCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit',
                    help='Actually update the database'),
        make_option('--force', action='store_true', dest='force',
                    help='Force deactivation, even if it would leave no active generations'))

    def handle(self, generation_id, **options):
        generation_to_deactivate = Generation.objects.get(id=int(generation_id, 10))
        if not generation_to_deactivate.active:
            raise CommandError, "The generation %s wasn't active" % (generation_id,)
        active_generations = Generation.objects.filter(active=True).count()
        if active_generations <= 1 and not options['force']:
            raise CommandError, "You're trying to deactivate the only active generation.  If this is what you intended, please re-run the command with --force"
        generation_to_deactivate.active = False
        if options['commit']:
            generation_to_deactivate.save()
            print "%s - deactivated" % generation_to_deactivate
        else:
            print "%s - not deactivated, dry run" % generation_to_deactivate

########NEW FILE########
__FILENAME__ = mapit_global_analyse_differences
#!/usr/bin/env python

import sys
import os
import csv

from django.core.management.base import LabelCommand

from mapit.models import *

class Command(LabelCommand):
    help = 'Analyse a CVS file generated by mapit_global_find_differences'
    args = '<CSV-FILE>'

    def handle_label(self, differences_results_csv_file, **options):

        osm_elements_seen_in_new_data = set([])

        with open(differences_results_csv_file) as fp:
            reader = csv.DictReader(fp)
            equals_but_not_equals_exact = 0
            equals_exact_but_not_equals = 0
            completely_new_boundaries = 0
            boundary_stayed_the_same = 0
            boundary_changed = 0
            empty_in_either = 0
            total = 0
            for row in reader:
                total += 1
                counted_somewhere = False
                if row['GEOSEquals'] == 'True' and row['GEOSEqualsExact'] == 'False':
                    equals_but_not_equals_exact += 1
                    counted_somewhere = True
                elif row['GEOSEqualsExact'] == 'True' and row['GEOSEquals'] == 'False':
                    equals_exact_but_not_equals += 1
                    counted_somewhere = True
                if row['ExistedPreviously'] == 'False':
                    # n.b. includes cases where the new area is empty or malformed
                    completely_new_boundaries += 1
                    counted_somewhere = True
                elif row['GEOSEquals'] == 'True':
                    boundary_stayed_the_same += 1
                    counted_somewhere = True
                elif row['GEOSEquals'] == 'False':
                    boundary_changed += 1
                    counted_somewhere = True
                elif row['PreviousEmpty'] == 'True' or row['NewEmpty'] == 'True':
                    empty_in_either += 1
                    counted_somewhere = True
                if not counted_somewhere:
                    print "not counted:", row
                osm_elements_seen_in_new_data.add((row['ElementType'],row['ElementID']))
            
        disappeared = 0
        
        for a in Area.objects.all().iterator():
            all_codes = a.codes.all()
            if len(all_codes) == 0:
                print "code missing for:", a
            elif len(all_codes) > 1:
                print "too many codes (%d) for: %s" % (len(all_codes), a)
            else:
                code = all_codes[0]
                element_type = 'relation' if code.type.code == 'osm_rel' else 'way'
                element_id = code.code
                t = (element_type, element_id)
                if t not in osm_elements_seen_in_new_data:
                    disappeared += 1
                    polygons = a.polygons.all()
                    if len(polygons) > 0:
                        if polygons[0].polygon.valid:
                            lon, lat = polygons[0].polygon.point_on_surface
                            point_url = "/point/4326/%s,%s.html" % (lon, lat)
                        else:
                            point_url = "[first polygon was invalid, skipping]"
                    else:
                        point_url = "[no polygons]"
                    print "disappeared: /code/%s/%s - a point inside is: %s" % (code.type.code, code.code, point_url)

        print "========================================================================"
        print "equals_but_not_equals_exact:", equals_but_not_equals_exact
        print "equals_exact_but_not_equals:", equals_exact_but_not_equals
        print "completely_new_boundaries:", completely_new_boundaries
        print "areas that disappeared:", disappeared
        print "boundary_stayed_the_same:", boundary_stayed_the_same
        print "boundary_changed:", boundary_changed
        print "empty_in_either:", empty_in_either
        print "out of a total:", total

########NEW FILE########
__FILENAME__ = mapit_global_find_differences
# import_global_osm.py:
#
# This script is used to import administrative boundaries from
# OpenStreetMap into MaPit.
#
# It takes KML data generated by get-boundaries-by-admin-level.py, so
# you need to have run that first.
#
# This script is heavily based on import_norway_osm.py by Matthew
# Somerville.
#
# Copyright (c) 2011, 2012 UK Citizens Online Democracy. All rights reserved.
# Email: mark@mysociety.org; WWW: http://www.mysociety.org

import os
import re
import xml.sax
from optparse import make_option
from django.core.management.base import LabelCommand
from django.contrib.gis.gdal import *
from mapit.models import Area, Generation, Country, Type, Code, CodeType, NameType
from mapit.management.command_utils import save_polygons, KML
from glob import glob
import urllib2
from BeautifulSoup import BeautifulSoup
from collections import namedtuple
import json
import csv

def empty_if_none(o):
    return '' if o is None else o

class Command(LabelCommand):
    help = 'Import OSM administrative boundary data'
    args = '<KML-DIRECTORY>'

    def handle_label(self, directory_name, **options):
        current_generation = Generation.objects.current()

        if not os.path.isdir(directory_name):
            raise Exception, "'%s' is not a directory" % (directory_name,)

        os.chdir(directory_name)
        skip_up_to = None
        # skip_up_to = 'relation-80370'

        skipping = bool(skip_up_to)

        osm_elements_seen_in_new_data = set([])

        with open("/home/mark/difference-results.csv", 'w') as fp:
            csv_writer = csv.writer(fp)
            csv_writer.writerow(["ElementType",
                                 "ElementID",
                                 "ExistedPreviously",
                                 "PreviousEmpty",
                                 "PreviousArea",
                                 "NewEmpty",
                                 "NewArea",
                                 "SymmetricDifferenceArea",
                                 "GEOSEquals",
                                 "GEOSEqualsExact"])

            for admin_directory in sorted(x for x in os.listdir('.') if os.path.isdir(x)):

                if not re.search('^[A-Z0-9]{3}$', admin_directory):
                    print "Skipping a directory that doesn't look like a MapIt type:", admin_directory

                if not os.path.exists(admin_directory):
                    continue

                files = sorted(os.listdir(admin_directory))
                total_files = len(files)

                for i, e in enumerate(files):

                    progress = "[%d%% complete] " % ((i * 100) / total_files,)

                    if skipping:
                        if skip_up_to in e:
                            skipping = False
                        else:
                            continue

                    if not e.endswith('.kml'):
                        continue

                    m = re.search(r'^(way|relation)-(\d+)-', e)
                    if not m:
                        raise Exception, u"Couldn't extract OSM element type and ID from: " + e

                    osm_type, osm_id = m.groups()

                    osm_elements_seen_in_new_data.add((osm_type, osm_id))

                    kml_filename = os.path.join(admin_directory, e)

                    # Need to parse the KML manually to get the ExtendedData
                    kml_data = KML()
                    print "parsing", kml_filename
                    xml.sax.parse(kml_filename, kml_data)

                    useful_names = [n for n in kml_data.data.keys() if not n.startswith('Boundaries for')]
                    if len(useful_names) == 0:
                        raise Exception, "No useful names found in KML data"
                    elif len(useful_names) > 1:
                        raise Exception, "Multiple useful names found in KML data"
                    name = useful_names[0]
                    print " ", name.encode('utf-8')

                    if osm_type == 'relation':
                        code_type_osm = CodeType.objects.get(code='osm_rel')
                    elif osm_type == 'way':
                        code_type_osm = CodeType.objects.get(code='osm_way')
                    else:
                        raise Exception, "Unknown OSM element type:", osm_type

                    ds = DataSource(kml_filename)
                    if len(ds) != 1:
                        raise Exception, "We only expect one layer in a DataSource"

                    layer = ds[0]
                    if len(layer) != 1:
                        raise Exception, "We only expect one feature in each layer"

                    feat = layer[0]

                    area_code = admin_directory

                    osm_codes = list(Code.objects.filter(type=code_type_osm, code=osm_id))
                    osm_codes.sort(key=lambda e: e.area.generation_high.created)

                    new_area = None
                    new_valid = None
                    new_empty = None

                    previous_area = None
                    previous_valid = None
                    previous_empty = None

                    symmetric_difference_area = None

                    g = feat.geom.transform(4326, clone=True)

                    new_some_nonempty = False
                    for polygon in g:
                        if polygon.point_count < 4:
                            new_empty = True
                        else:
                            new_some_nonempty = True
                    if not new_empty:
                        new_geos_geometry = g.geos.simplify(tolerance=0)
                        new_area = new_geos_geometry.area
                        new_empty = new_geos_geometry.empty

                    geos_equals = None
                    geos_equals_exact = None

                    most_recent_osm_code = None
                    if osm_codes:
                        most_recent_osm_code = osm_codes[-1]
                        previous_geos_geometry = most_recent_osm_code.area.polygons.collect()
                        previous_empty = previous_geos_geometry is None

                        if not previous_empty:
                            previous_geos_geometry = previous_geos_geometry.simplify(tolerance=0)
                            previous_area = previous_geos_geometry.area

                            if not new_empty:
                                symmetric_difference_area = previous_geos_geometry.sym_difference(new_geos_geometry).area
                                geos_equals = previous_geos_geometry.equals(new_geos_geometry)
                                geos_equals_exact = previous_geos_geometry.equals_exact(new_geos_geometry)

                    csv_writer.writerow([osm_type,
                                         osm_id,
                                         bool(osm_codes), # ExistedPreviously
                                         empty_if_none(previous_empty),
                                         empty_if_none(previous_area),
                                         empty_if_none(new_empty),
                                         empty_if_none(new_area),
                                         empty_if_none(symmetric_difference_area),
                                         empty_if_none(geos_equals),
                                         empty_if_none(geos_equals_exact)])

########NEW FILE########
__FILENAME__ = mapit_global_import
# import_global_osm.py:
#
# This script is used to import boundaries from OpenStreetMap into
# MaPit.
#
# It takes KML data generated either by
# get-boundaries-by-admin-level.py, so you need to have run that
# script first.
#
# This script was originally based on import_norway_osm.py by Matthew
# Somerville.
#
# Copyright (c) 2011, 2012 UK Citizens Online Democracy. All rights reserved.
# Email: mark@mysociety.org; WWW: http://www.mysociety.org

from collections import namedtuple
import csv
from glob import glob
import json
from optparse import make_option
import os
import re
import urllib2
import xml.sax

from django.core.management.base import LabelCommand
# Not using LayerMapping as want more control, but what it does is what this does
#from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.gdal import *
from django.contrib.gis.geos import MultiPolygon
import shapely

from mapit.models import Area, Generation, Country, Type, Code, CodeType, NameType
from mapit.management.command_utils import save_polygons, KML
from mapit.management.command_utils import fix_invalid_geos_polygon, fix_invalid_geos_multipolygon

def make_missing_none(s):
    """If s is empty (considering Unicode spaces) return None, else s"""
    if re.search('(?uis)^\s*$', s):
        return None
    else:
        return s

LanguageCodes = namedtuple('LanguageCodes',
                           ['three_letter',
                            'two_letter',
                            'english_name',
                            'french_name'])

def get_iso639_2_table():
    """Scrape and return the table of ISO639-2 and ISO639-1 language codes

    The OSM tags of the form "name:en", "name:fr", etc. refer to
    ISO639-1 two-letter codes, or ISO639-2 three-letter codes.  This
    function parses the Library of Congress table of these values, and
    returns them as a list of LanguageCodes"""

    result = []
    url = "http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt"
    for row in csv.reader(urllib2.urlopen(url), delimiter='|'):
        row = [ cell.decode('utf-8-sig') for cell in row ]
        bibliographic = [ row[0], row[2], row[3], row[4] ]
        result_row = LanguageCodes._make(make_missing_none(s) for s in bibliographic)
        result.append(result_row)
        if row[1]:
            terminologic = [ row[1], row[2], row[3], row[4] ]
            result_row = LanguageCodes._make(make_missing_none(s) for s in terminologic)
            result.append(result_row)
    return result

class Command(LabelCommand):
    help = 'Import OSM boundary data from KML files'
    args = '<KML-DIRECTORY>'
    option_list = LabelCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    def handle_label(self, directory_name, **options):
        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        if not new_generation:
            raise Exception, "No new generation to be used for import!"

        if not os.path.isdir(directory_name):
            raise Exception, "'%s' is not a directory" % (directory_name,)

        os.chdir(directory_name)

        mapit_type_glob = "[A-Z0-9][A-Z0-9][A-Z0-9]"

        if not glob(mapit_type_glob):
            raise Exception, "'%s' did not contain any directories that look like MapIt types (e.g. O11, OWA, etc.)" % (directory_name,)

        def verbose(s):
            if int(options['verbosity']) > 1:
                print s.encode('utf-8')

        verbose("Loading any admin boundaries from " + directory_name)

        verbose("Finding language codes...")

        language_code_to_name = {}
        code_keys = ('two_letter', 'three_letter')
        for row in get_iso639_2_table():
            english_name = getattr(row, 'english_name')
            for k in code_keys:
                code = getattr(row, k)
                if not code:
                    continue
                language_code_to_name[code] = english_name

        global_country = Country.objects.get(code='G')

        # print json.dumps(language_code_to_name, sort_keys=True, indent=4)

        skip_up_to = None
        # skip_up_to = 'relation-80370'

        skipping = bool(skip_up_to)

        for type_directory in sorted(glob(mapit_type_glob)):

            verbose("Loading type " + type_directory)

            if not os.path.exists(type_directory):
                verbose("Skipping the non-existent " + type_directory)
                continue

            verbose("Loading all KML in " + type_directory)

            files = sorted(os.listdir(type_directory))
            total_files = len(files)

            for i, e in enumerate(files):

                progress = "[%d%% complete] " % ((i * 100) / total_files,)

                if skipping:
                    if skip_up_to in e:
                        skipping = False
                    else:
                        continue

                if not e.endswith('.kml'):
                    verbose("Ignoring non-KML file: " + e)
                    continue

                m = re.search(r'^(way|relation)-(\d+)-', e)
                if not m:
                    raise Exception, u"Couldn't extract OSM element type and ID from: " + e

                osm_type, osm_id = m.groups()

                kml_filename = os.path.join(type_directory, e)

                verbose(progress + "Loading " + unicode(os.path.realpath(kml_filename), 'utf-8'))

                # Need to parse the KML manually to get the ExtendedData
                kml_data = KML()
                xml.sax.parse(kml_filename, kml_data)

                useful_names = [n for n in kml_data.data.keys() if not n.startswith('Boundaries for')]
                if len(useful_names) == 0:
                    raise Exception, "No useful names found in KML data"
                elif len(useful_names) > 1:
                    raise Exception, "Multiple useful names found in KML data"
                name = useful_names[0]
                print " ", name.encode('utf-8')

                if osm_type == 'relation':
                    code_type_osm = CodeType.objects.get(code='osm_rel')
                elif osm_type == 'way':
                    code_type_osm = CodeType.objects.get(code='osm_way')
                else:
                    raise Exception, "Unknown OSM element type:", osm_type

                ds = DataSource(kml_filename)
                layer = ds[0]
                if len(layer) != 1:
                    raise Exception, "We only expect one feature in each layer"

                feat = layer[1]

                g = feat.geom.transform(4326, clone=True)

                if g.geom_count == 0:
                    # Just ignore any KML files that have no polygons in them:
                    verbose('    Ignoring that file - it contained no polygons')
                    continue

                # Nowadays, in generating the data we should have
                # excluded any "polygons" with less than four points
                # (the final one being the same as the first), but
                # just in case:
                polygons_too_small = 0
                for polygon in g:
                    if polygon.num_points < 4:
                        polygons_too_small += 1
                if polygons_too_small:
                    message = "%d out of %d polygon(s) were too small" % (polygons_too_small, g.geom_count)
                    verbose('    Skipping, since ' + message)
                    continue

                g_geos = g.geos

                if not g_geos.valid:
                    verbose("    Invalid KML:" + unicode(kml_filename, 'utf-8'))
                    fixed_multipolygon = fix_invalid_geos_multipolygon(g_geos)
                    if len(fixed_multipolygon) == 0:
                        verbose("    Invalid polygons couldn't be fixed")
                        continue
                    g = fixed_multipolygon.ogr

                area_type = Type.objects.get(code=type_directory)

                try:
                    osm_code = Code.objects.get(type=code_type_osm,
                                                code=osm_id,
                                                area__generation_high__lte=current_generation,
                                                area__generation_high__gte=current_generation)
                except Code.DoesNotExist:
                    verbose('    No area existed in the current generation with that OSM element type and ID')
                    osm_code = None

                was_the_same_in_current = False

                if osm_code:
                    m = osm_code.area

                    # First, we need to check if the polygons are
                    # still the same as in the previous generation:
                    previous_geos_geometry = m.polygons.collect()
                    if previous_geos_geometry is None:
                        verbose('    In the current generation, that area was empty - skipping')
                    else:
                        # Simplify it to make sure the polygons are valid:
                        previous_geos_geometry = shapely.wkb.loads(str(previous_geos_geometry.simplify(tolerance=0).ewkb))
                        new_geos_geometry = shapely.wkb.loads(str(g.geos.simplify(tolerance=0).ewkb))
                        if previous_geos_geometry.almost_equals(new_geos_geometry, decimal=7):
                            was_the_same_in_current = True
                        else:
                            verbose('    In the current generation, the boundary was different')

                if was_the_same_in_current:
                    # Extend the high generation to the new one:
                    verbose('    The boundary was identical in the previous generation; raising generation_high')
                    m.generation_high = new_generation

                else:
                    # Otherwise, create a completely new area:
                    m = Area(
                        name = name,
                        type = area_type,
                        country = global_country,
                        parent_area = None,
                        generation_low = new_generation,
                        generation_high = new_generation,
                    )

                poly = [ g ]

                if options['commit']:
                    m.save()
                    verbose('    Area ID: ' + str(m.id))

                    if name not in kml_data.data:
                        print json.dumps(kml_data.data, sort_keys=True, indent=4)
                        raise Exception, u"Will fail to find '%s' in the dictionary" % (name,)

                    old_lang_codes = set(unicode(n.type.code) for n in m.names.all())

                    for k, translated_name in kml_data.data[name].items():
                        language_name = None
                        if k == 'name':
                            lang = 'default'
                            language_name = "OSM Default"
                        else:
                            name_match = re.search(r'^name:(.+)$', k)
                            if name_match:
                                lang = name_match.group(1)
                                if lang in language_code_to_name:
                                    language_name = language_code_to_name[lang]
                        if not language_name:
                            continue
                        old_lang_codes.discard(unicode(lang))

                        # Otherwise, make sure that a NameType for this language exists:
                        NameType.objects.update_or_create({'code': lang},
                                                          {'code': lang,
                                                           'description': language_name})
                        name_type = NameType.objects.get(code=lang)

                        m.names.update_or_create({ 'type': name_type }, { 'name': translated_name })

                    if old_lang_codes:
                        verbose('Removing deleted languages codes: ' + ' '.join(old_lang_codes))
                    m.names.filter(type__code__in=old_lang_codes).delete()
                    # If the boundary was the same, the old Code
                    # object will still be pointing to the same Area,
                    # which just had its generation_high incremented.
                    # In every other case, there's a new area object,
                    # so create a new Code and save it:
                    if not was_the_same_in_current:
                        new_code = Code(area=m, type=code_type_osm, code=osm_id)
                        new_code.save()
                    save_polygons({ 'dummy': (m, poly) })

########NEW FILE########
__FILENAME__ = mapit_import
# This script is used to import geometry information, from a shapefile, KML
# or GeoJSON file, into MapIt.
#
# Copyright (c) 2011 UK Citizens Online Democracy. All rights reserved.
# Email: matthew@mysociety.org; WWW: http://www.mysociety.org

import re
import sys
from optparse import make_option
from django.core.management.base import LabelCommand
# Not using LayerMapping as want more control, but what it does is what this does
#from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.gdal import *
from django.conf import settings
from mapit.models import Area, Generation, Type, NameType, Country, CodeType
from mapit.management.command_utils import save_polygons, fix_invalid_geos_geometry

class Command(LabelCommand):
    help = 'Import geometry data from .shp, .kml or .geojson files'
    args = '<SHP/KML/GeoJSON files>'
    option_list = LabelCommand.option_list + (
        make_option(
            '--commit',
            action='store_true',
            dest='commit',
            help='Actually update the database'
        ),
        make_option(
            '--generation_id',
            action="store",
            dest='generation_id',
            help='Which generation ID should be used',
        ),
        make_option(
            '--country_code',
            action="store",
            dest='country_code',
            help='Which country should be used',
        ),
        make_option(
            '--area_type_code',
            action="store",
            dest='area_type_code',
            help='Which area type should be used (specify using code)',
        ),
        make_option(
            '--name_type_code',
            action="store",
            dest='name_type_code',
            help='Which name type should be used (specify using code)',
        ),
        make_option(
            '--code_type',
            action="store",
            dest='code_type',
            help='Which code type should be used (specify using its code)',
        ),
        make_option(
            '--name_field',
            action="store",
            dest='name_field',
            help="The field name containing the area's name"
        ),
        make_option(
            '--override_name',
            action="store",
            dest='override_name',
            help="The name to use for the area"
        ),
        make_option(
            '--code_field',
            action="store",
            dest='code_field',
            help="The field name containing the area's ID code"
        ),
        make_option(
            '--override_code',
            action="store",
            dest='override_code',
            help="The ID code to use for the area"
        ),
        make_option(
            '--use_code_as_id',
            action="store_true",
            dest='use_code_as_id',
            help="Set to use the code from code_field as the MapIt ID"
        ),
        make_option(
            '--preserve',
            action="store_true",
            dest='preserve',
            help="Create a new area if the name's the same but polygons differ"
        ),
        make_option(
            '--new',
            action="store_true",
            dest='new',
            help="Don't look for existing areas at all, just import everything as new areas"
        ),
        make_option(
            '--encoding',
            action="store",
            dest='encoding',
            help="The encoding of names in this dataset"
        ),
        make_option(
            '--fix_invalid_polygons',
            action="store_true",
            dest='fix_invalid_polygons',
            help="Try to fix any invalid polygons and multipolygons found"
        ),
    )

    def handle_label(self, filename, **options):

        err = False
        for k in ['generation_id','area_type_code','name_type_code','country_code']:
            if options[k]: continue
            print "Missing argument '--%s'" % k
            err = True
        if err:
            sys.exit(1)

        generation_id = options['generation_id']
        area_type_code = options['area_type_code']
        name_type_code = options['name_type_code']
        country_code = options['country_code']
        override_name = options['override_name']
        name_field = options['name_field']
        if not (override_name or name_field):
            name_field = 'Name'
        override_code = options['override_code']
        code_field = options['code_field']
        code_type_code = options['code_type']
        encoding = options['encoding'] or 'utf-8'

        if len(area_type_code)>3:
            print "Area type code must be 3 letters or fewer, sorry"
            sys.exit(1)

        if name_field and override_name:
            print "You must not specify both --name_field and --override_name"
            sys.exit(1)
        if code_field and override_code:
            print "You must not specify both --code_field and --override_code"
            sys.exit(1)

        using_code = (code_field or override_code)
        if (using_code and not code_type_code) or (not using_code and code_type_code):
            print "If you want to save a code, specify --code_type and either --code_field or --override_code"
            sys.exit(1)
        try:
            area_type = Type.objects.get(code=area_type_code)
        except:
            type_desc = raw_input('Please give a description for area type code %s: ' % area_type_code)
            area_type = Type(code=area_type_code, description=type_desc)
            if options['commit']: area_type.save()

        try:
            name_type = NameType.objects.get(code=name_type_code)
        except:
            name_desc = raw_input('Please give a description for name type code %s: ' % name_type_code)
            name_type = NameType(code=name_type_code, description=name_desc)
            if options['commit']: name_type.save()

        try:
            country = Country.objects.get(code=country_code)
        except:
            country_name = raw_input('Please give the name for country code %s: ' % country_code)
            country = Country(code=country_code, name=country_name)
            if options['commit']: country.save()

        if code_type_code:
            try:
                code_type = CodeType.objects.get(code=code_type_code)
            except:
                code_desc = raw_input('Please give a description for code type %s: ' % code_type_code)
                code_type = CodeType(code=code_type_code, description=code_desc)
                if options['commit']: code_type.save()

        print "Importing from %s" % filename

        if not options['commit']:
            print '(will not save to db as --commit not specified)'

        current_generation = Generation.objects.current()
        new_generation     = Generation.objects.get( id=generation_id )

        def verbose(*args):
            if int(options['verbosity']) > 1:
                print " ".join(str(a) for a in args)

        ds = DataSource(filename)
        layer = ds[0]
        if (override_name or override_code) and len(layer) > 1:
            message = "Warning: you have specified an override %s and this file contains more than one feature; multiple areas with the same %s will be created"
            if override_name:
                print message % ('name', 'name')
            if override_code:
                print message % ('code', 'code')

        for feat in layer:

            if override_name:
                name = override_name
            else:
                try:
                    name = feat[name_field].value
                except:
                    choices = ', '.join(layer.fields)
                    print "Could not find name using name field '%s' - should it be something else? It will be one of these: %s. Specify which with --name_field" % (name_field, choices)
                    sys.exit(1)
                try:
                    if not isinstance(name, unicode):
                        name = name.decode(encoding)
                except:
                    print "Could not decode name using encoding '%s' - is it in another encoding? Specify one with --encoding" % encoding
                    sys.exit(1)

            name = re.sub('\s+', ' ', name)
            if not name:
                raise Exception( "Could not find a name to use for area" )

            code = None
            if override_code:
                code = override_code
            elif code_field:
                try:
                    code = feat[code_field].value
                except:
                    choices = ', '.join(layer.fields)
                    print "Could not find code using code field '%s' - should it be something else? It will be one of these: %s. Specify which with --code_field" % (code_field, choices)
                    sys.exit(1)

            print "  looking at '%s'%s" % ( name.encode('utf-8'), (' (%s)' % code) if code else '' )

            g = feat.geom.transform(settings.MAPIT_AREA_SRID, clone=True)

            try:
                if options['new']: # Always want a new area
                    raise Area.DoesNotExist
                if code:
                    matching_message = "code %s of code type %s" % (code, code_type)
                    areas = Area.objects.filter(codes__code=code, codes__type=code_type).order_by('-generation_high')
                else:
                    matching_message = "name %s of area type %s" % (name, area_type)
                    areas = Area.objects.filter(name=name, type=area_type).order_by('-generation_high')
                if len(areas) == 0:
                    verbose("    the area was not found - creating a new one")
                    raise Area.DoesNotExist
                m = areas[0]
                verbose("    found the area")
                if options['preserve']:
                    # Find whether we need to create a new Area:
                    previous_geos_geometry = m.polygons.collect()
                    if m.generation_high < current_generation.id:
                        # Then it was missing in current_generation:
                        verbose("    area existed previously, but was missing from", current_generation)
                        raise Area.DoesNotExist
                    elif previous_geos_geometry is None:
                        # It was empty in the previous generation:
                        verbose("    area was empty in", current_generation)
                        raise Area.DoesNotExist
                    else:
                        # Otherwise, create a new Area unless the
                        # polygons were the same in current_generation:
                        previous_geos_geometry = previous_geos_geometry.simplify(tolerance=0)
                        new_geos_geometry = g.geos.simplify(tolerance=0)
                        create_new_area = not previous_geos_geometry.equals(new_geos_geometry)
                        p = previous_geos_geometry.sym_difference(new_geos_geometry).area / previous_geos_geometry.area
                        verbose("    change in area is:", "%.03f%%" % (100 * p,))
                        if create_new_area:
                            verbose("    the area", m, "has changed, creating a new area due to --preserve")
                            raise Area.DoesNotExist
                        else:
                            verbose("    the area remained the same")
                else:
                    # If --preserve is not specified, the code or the name must be unique:
                    if len(areas) > 1:
                        raise Area.MultipleObjectsReturned, "There was more than one area with %s, and --preserve was not specified" % (matching_message,)

            except Area.DoesNotExist:
                m = Area(
                    name            = name,
                    type            = area_type,
                    country         = country,
                    # parent_area     = parent_area,
                    generation_low  = new_generation,
                    generation_high = new_generation,
                )
                if options['use_code_as_id'] and code:
                    m.id = int(code)

            # check that we are not about to skip a generation
            if m.generation_high and current_generation and m.generation_high.id < current_generation.id:
                raise Exception, "Area %s found, but not in current generation %s" % (m, current_generation)
            m.generation_high = new_generation

            if options['fix_invalid_polygons']:
                # Make a GEOS geometry only to check for validity:
                geos_g = g.geos
                if not geos_g.valid:
                    geos_g = fix_invalid_geos_geometry(geos_g)
                    if geos_g is None:
                        print "The geometry for area %s was invalid and couldn't be fixed" % name
                        g = None
                    else:
                        g = geos_g.ogr

            poly = [ g ] if g is not None else []

            if options['commit']:
                m.save()
                m.names.update_or_create({ 'type': name_type }, { 'name': name })
                if code:
                    m.codes.update_or_create({ 'type': code_type }, { 'code': code })
                save_polygons({ m.id : (m, poly) })


########NEW FILE########
__FILENAME__ = mapit_import_area_unions
# import_area_unions.py:
# This script is used to import regions (combinations of existing
# areas into a new area) into MaPit.
#
# Copyright (c) 2011 Petter Reinholdtsen.  Some rights reserved using
# the GPL.  Based on import_norway_osm.py by Matthew Somerville

import csv
import sys
import re
from optparse import make_option
from django.core.management.base import LabelCommand
from django.contrib.gis.gdal import *
from django.contrib.gis.geos import GEOSGeometry
from mapit.models import Area, Generation, Geometry, Country, Type
from mapit.management.command_utils import save_polygons

# CSV format is
# ID;code;name;area1,area2,...;email;categories

# Copied from
# http://www.mfasold.net/blog/2010/02/python-recipe-read-csvtsv-textfiles-and-ignore-comment-lines/
class CommentedFile:
    def __init__(self, f, commentstring="#"):
        self.f = f
        self.commentstring = commentstring
    def next(self):
        line = self.f.next()
        while line.startswith(self.commentstring):
            line = self.f.next()
        return line
    def __iter__(self):
        return self

class Command(LabelCommand):
    help = 'Import region data'
    args = '<CSV file listing name and which existing areas to combine into regions>'
    option_list = LabelCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    def handle_label(self, filename, **options):
        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        if not new_generation:
            print "Using current generation %d" % current_generation.id
            new_generation = current_generation
        else:
            print "Using new generation %d" % new_generation.id

        print "Loading file %s" % filename
        region_line = csv.reader(CommentedFile(open(filename, "rb")),
                                 delimiter=';')

        for regionid, area_type, regionname, area_names, email, categories in region_line:
            print "Building region '%s'" % regionname
            if (-2147483648 > int(regionid) or 2147483647 < int(regionid)):
                raise Exception, "Region ID %d is outside range of 32-bit integer" % regionid

            if area_names:
                # Look up areas using the names, find their geometry
                # and build a geometric union to set as the geometry
                # of the region.
                geometry = None
                for name in area_names.split(','):
                    name.strip()
                    name.lstrip()

                    try:
                        # Use this to allow '123 Name' in area definition
                        areaidnum = int(name.split()[0])
                        print "Looking up ID '%d'" % areaidnum
                        args = {
                            'id__exact': areaidnum,
                            'generation_low__lte': current_generation,
                            'generation_high__gte': new_generation,
                            }
                    except (ValueError, IndexError):
                        print "Looking up name '%s'" % name
                        args = {
                            'name__iexact': name,
                            'generation_low__lte': current_generation,
                            'generation_high__gte': new_generation,
                            }
                    area_id = Area.objects.filter(**args).only('id')
                    if 1 < len(area_id):
                        raise Exception, "More than one Area named %s, use area ID as well" % name
                    try:
                        print "ID:", area_id[0].id
                        args = {
                            'area__exact': area_id[0].id,
                            }
                        if geometry:
                            geometry = geometry | Geometry.objects.filter(**args)
                        else:
                            geometry = Geometry.objects.filter(**args)
                    except:
                        raise Exception, "Area or geometry with name %s was not found!" % name
                    unionoutline = geometry.unionagg()

                def update_or_create():
                    try:
                        m = Area.objects.get(id=int(regionid))
                        print "Updating area %s with id %d" % (regionname, int(regionid))
                    except Area.DoesNotExist:
                        print "Creating new area %s with id %d" % (regionname, int(regionid))
                        m = Area(
                            id = int(regionid),
                            name = regionname,
                            type = Type.objects.get(code=area_type),
                            country = Country.objects.get(code='O'),
                            generation_low = new_generation,
                            generation_high = new_generation,
                            )

                    if m.generation_high and current_generation \
                            and m.generation_high.id < current_generation.id:
                        raise Exception, "Area %s found, but not in current generation %s" % (m, current_generation)
                    m.generation_high = new_generation

                    poly = [ GEOSGeometry(unionoutline).ogr ]
                    if options['commit']:
                        m.save()
                        save_polygons({ regionid : (m, poly) })

                update_or_create()
            else:
                raise Exception, "No area names found for region with name %s!" % regionname

########NEW FILE########
__FILENAME__ = mapit_import_postal_codes
# This is a generic script for importing postal codes in some format from a CSV
# file. The CSV file should have the following columns:
#   Postal code, Latitude, Longitude
# By default in those positions, though you can specify other column numbers on
# the command line

import csv
from optparse import make_option
from django.contrib.gis.geos import Point
from django.core.management.base import LabelCommand
from django.conf import settings
from mapit.models import Postcode

class Command(LabelCommand):
    help = 'Import Postal codes from a CSV file or files'
    args = '<CSV files>'
    count = { 'total': 0, 'updated': 0, 'unchanged': 0, 'created': 0 }
    often = 1000

    option_defaults = {}
    option_list = LabelCommand.option_list + (
        make_option(
            '--code-field',
            action = 'store',
            dest = 'code-field',
            default = 1,
            help = 'The column of the CSV containing the postal code (default 1, first)'
        ),
        make_option(
            '--coord-field-lat',
            action = 'store',
            dest = 'coord-field-lat',
            default = 2,
            help = 'The column of the CSV containing the lat/y co-ordinate (default 2)'
        ),
        make_option(
            '--coord-field-lon',
            action = 'store',
            dest = 'coord-field-lon',
            default = None,
            help = 'The column of the CSV containing the lon/x co-ordinate (default --coord-field-lat + 1)'
        ),
        make_option(
            '--header-row',
            action = 'store_true',
            dest = 'header-row',
            default = False,
            help = 'Set if the CSV file has a header row'
        ),
        make_option(
            '--no-location',
            action = "store_false",
            dest = 'location',
            default = True,
            help = 'Set if the postal codes have no associated location (still useful for existence checks)'
        ),
        make_option(
            '--srid',
            action = "store",
            dest = 'srid',
            default = 4326,
            help = 'The SRID of the projection for the data given (default 4326 WGS-84)'
        ),
        make_option(
            '--strip',
            action = "store_true",
            dest = 'strip',
            default = False,
            help = 'Whether to strip all spaces from the postal code before import'
        ),
        make_option(
            '--tabs',
            action = "store_true",
            dest = 'tabs',
            default = False,
            help = 'If the CSV file actually uses tab as its separator'
        ),
    )

    def handle_label(self, file, **options):
        self.process(file, options)

    def process(self, file, options):
        options.update(self.option_defaults)
        if options['tabs']:
            reader = csv.reader(open(file), dialect='excel-tab')
        else:
            reader = csv.reader(open(file))
        if options['header-row']: next(reader)
        for row in reader:
            self.code = row[int(options['code-field'])-1].strip()
            if options['strip']:
                self.code = self.code.replace(' ', '')
            if not self.pre_row(row, options):
                continue
            pc = self.handle_row(row, options)
            self.post_row(pc)
        self.print_stats()

    def pre_row(self, row, options):
        return True

    def post_row(self, pc):
        return True

    def handle_row(self, row, options):
        if not options['location']:
            return self.do_postcode()

        if not options['coord-field-lon']:
            options['coord-field-lon'] = int(options['coord-field-lat']) + 1
        lat = float(row[int(options['coord-field-lat'])-1])
        lon = float(row[int(options['coord-field-lon'])-1])
        srid = int(options['srid'])
        location = Point(lon, lat, srid=srid)
        return self.do_postcode(location, srid)

    # Want to compare co-ordinates so can't use straightforward
    # update_or_create
    def do_postcode(self, location=None, srid=None):
        try:
            pc = Postcode.objects.get(postcode=self.code)
            if location:
                curr_location = ( pc.location[0], pc.location[1] )
                if settings.MAPIT_COUNTRY == 'GB':
                    if pc.postcode[0:2] == 'BT':
                        curr_location = pc.as_irish_grid()
                    else:
                        pc.location.transform(27700) # Postcode locations are stored as WGS84
                        curr_location = ( pc.location[0], pc.location[1] )
                    curr_location = map(round, curr_location)
                elif srid != 4326:
                    pc.location.transform(srid) # Postcode locations are stored as WGS84
                    curr_location = ( pc.location[0], pc.location[1] )
                if curr_location[0] != location[0] or curr_location[1] != location[1]:
                    pc.location = location
                    pc.save()
                    self.count['updated'] += 1
                else:
                    self.count['unchanged'] += 1
            else:
                self.count['unchanged'] += 1
        except Postcode.DoesNotExist:
            pc = Postcode.objects.create(postcode=self.code, location=location)
            self.count['created'] += 1
        self.count['total'] += 1
        if self.count['total'] % self.often == 0:
            self.print_stats()
        return pc

    def print_stats(self):
        print "Imported %d (%d new, %d changed, %d same)" % (
            self.count['total'], self.count['created'],
            self.count['updated'], self.count['unchanged']
        )


########NEW FILE########
__FILENAME__ = mapit_make_fusion_csv
# mapit_make_fusion_csv.py
#
# This script is used to generate a CSV file with a column containing
# KML polygons for visualization with Google Fusion Tables.
#
# Copyright (c) 2011, 2012 UK Citizens Online Democracy. All rights reserved.
# Email: mark@mysociety.org; WWW: http://www.mysociety.org

# FIXME: add these instructions to code.fixmystreet.com as well

# Examples:
#
# In MapIt Global, find all countries:
#
#    ./manage.py mapit_make_fusion_csv --type=O02 --tolerance=0.001 global-countries.csv
#
# In MapIt Global, find all admin_level=10 areas in France:
#
#    ./manage.py mapit_make_fusion_csv --types=O10 --coveredby=28 france-10.csv
#
# (That assumes that 28 is the ID of the area corresponding to
# http://www.openstreetmap.org/browse/relation/1403916 in your MapIt.
# FIXME: it might be nice to be able to specify a relation or way ID
# instead of a MapIt Area ID here.)
#
# To import such CSV files into Google Fusion Tables, and make them
# look good, do the following:
#
#  1. Go to http://www.google.com/drive/start/apps.html#fusiontables
#  and click "Create a new table"
#
#  2. Select the CSV file you generated, with the defaults ("comma" as
#  the separator and UTF-8 encoding).  Then click "Next".
#
#  3. In the next dialog, the default ("Column names are in row 1")
#  should be fine, so just click "Next"
#
#  4. Put the correct attribution in the "Attribute data to" and the
#  "Attribution page link" fields (e.g. "OpenStreetMap contributors
#  and MapIt Global" and "http://global.mapit.mysociety.org/").  Then
#  click "Finish".

#  5. Now click on the "Map of name" tab.  Select "location" from the
#  "Tools -> Select location" submenu.

# 6. Go to "Tools -> Change map style ...", select Polygons -> Fill
# color, the Column tab, and specify the "color" column for colours.
#
# 7. You might need to switch to the "Rows 1" and back to the "Map of
# name" tab for the areas to be visible.
#
# 8. Go to File -> Share and change "Private" to "Anyone with the link"

import sys
import csv
from optparse import make_option
from random import random, seed
import colorsys

from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import *
from mapit.models import Area, Generation, Country, Type, Code, CodeType, NameType, TransformError
from mapit.views.areas import area_polygon

def hsv_to_rgb(h, s, v):
    rgb = colorsys.hsv_to_rgb(h, s, v)
    return [int(x*255) for x in rgb]

def rgb_for_html(r, g, b):
    return "%02x%02x%02x" % (r, g, b)

# From: http://stackoverflow.com/questions/3844801/check-if-all-elements-in-a-list-are-identical
def all_equal(iterator):
    try:
        iterator = iter(iterator)
        first = next(iterator)
        return all(first == rest for rest in iterator)
    except StopIteration:
        return True

class Command(BaseCommand):
    help = 'Generate a CSV file for Google Fusion Tables from MapIt'
    option_list = BaseCommand.option_list + (
            make_option("--types", dest="types",
                        help="The comma-separated types of the areas to return",
                        metavar="TYPES"),
            make_option("--coveredby", dest="coveredby", type="int",
                        help="Only include areas covered by AREA-ID",
                        metavar="AREA-ID"),
            make_option("--generation", dest="generation",
                        help="Specify the generation number", metavar="AREA-ID"),
            make_option("--tolerance", dest="tolerance", type="float",
                        default=0.0001,
                        help="Specify the simplifiy tolerance (default: 0.0001)",
                        metavar="TOLERANCE"),
            )

    def handle(self, *args, **options):

        # To add a new query type, add it to this tuple, and option_list above:
        possible_query_types = ('coveredby',)

        if len(args) != 1:
            print >> sys.stderr, "You must supply a CSV file name for output"
            sys.exit(1)

        output_filename = args[0]

        if options['generation']:
            generation = Generation.objects.get(id=int(options['generation']))
        else:
            generation = Generation.objects.current()

        if not options['types']:
            print >> sys.stderr, "Currently you must choose at least one type"
            sys.exit(1)

        selected_query_types = [q for q in possible_query_types if options[q]]

        if not all_equal(options[q] for q in selected_query_types):
            print >> sys.stderr, "The ID used in %s must be the same" % (", ".join(selected_query_types),)
            sys.exit(1)

        if len(selected_query_types) > 0:
            area_id = options[selected_query_types[0]]
            areas = list(Area.objects.intersect(selected_query_types,
                                                Area.objects.get(id=area_id),
                                                options['types'].split(','),
                                                generation))

        else:
            areas = list(Area.objects.filter(type__code=options['types'],
                                             generation_low__lte=generation,
                                             generation_high__gte=generation))

        simplified_away = []
        empty_anyway = []

        with open(output_filename, "w") as fp:
            writer = csv.writer(fp)
            writer.writerow(["name", "color", "location"])
            for i, area in enumerate(areas):
                seed(area.name)
                hue = random()
                line_rgb = rgb_for_html(*hsv_to_rgb(hue, 0.5, 0.5))
                fill_rgb = rgb_for_html(*hsv_to_rgb(hue, 0.5, 0.95))
                print "Exporting:", area
                try:
                    kml, _ = area.export(4326,
                                         'kml',
                                         simplify_tolerance=options['tolerance'],
                                         kml_type="polygon")
                except TransformError, e:
                    simplified_away.append(area)
                    print "  (the area was simplified away to nothing)"
                    continue

                if kml is None:
                    empty_anyway.append(area)
                    print "  (the area was empty, skipping it)"
                    continue

                # The maximum cell size in Google Fusion tables is 1
                # million characters:
                #
                #   https://developers.google.com/fusiontables/docs/v1/using#geolimits
                #
                # (I'm assuming they really do mean characters, rather
                # than bytes after UTF-8 encoding.)

                if len(kml) > 1E6:
                  print >> sys.stderr, "A cell for Google Fusion tables must be less than 1 million characters"
                  print >> sys.stderr, "but %s was %d characters" % (area, len(kml))
                  print >> sys.stderr, "Try raising the simplify tolerance with --tolerance"
                  sys.exit(1)

                writer.writerow([area.name.encode('utf-8') + " [%d]" % (area.id,),
                                 "#" + fill_rgb,
                                 kml.encode('utf-8')])

        if empty_anyway:
            print "The following areas had no polygons in the first place:"
            for area in empty_anyway:
                print "  ", area

        if simplified_away:
            print "The following areas did have polygon data, but were simplified away to nothing:"
            for area in simplified_away:
                print "  ", area

########NEW FILE########
__FILENAME__ = mapit_NO_import_bolstad_postcodes
# This script is used to import Norwegian postcode information from
# http://www.erikbolstad.no/geo/noreg/postnummer/, released by the
# Erik Bolstad:
# http://www.erikbolstad.no/postnummer-koordinatar/txt/postnummer.csv
# You can just use the generic postal code importer for this file,
# using the arguments: --coord-field-lat 10 --header-row --tabs

from mapit.management.commands.mapit_import_postal_codes import Command

class Command(Command):
    help = 'Import Norwegian postcodes from the Erik Bolstad data set'
    args = '<CSV file>'
    option_defaults = { 'coord-field-lat': 10, 'header-row': True, 'tabs': True }


########NEW FILE########
__FILENAME__ = mapit_NO_import_n5000
# import_norway_n5000.py:
# This script was used to import information from the N5000 dataset available at
# http://www.statkart.no/?module=Articles;action=Article.publicShow;ID=15305
#
# This script can now be done using the generic import script, as follows:
# python manage.py loaddata norway # Optional, will load in types
# python manage.py mapit_import --generation_id <new-gen-id> \
#   --area_type_code NKO --name_type_code M --country_code O \
#   --name_field NAVN --encoding iso-8859-1 \
#   --code_field KOMM --code_type n5000 --use_code_as_id --commit \
#   N5000_AdministrativFlate.shp


########NEW FILE########
__FILENAME__ = mapit_NO_import_osm
# import_norway_osm.py:
# This script is used to import information from OpenStreetMap into MaPit.
# It takes KML data generated by bin/mapit_osm_to_kml, so you should run that first.
#
# Copyright (c) 2011 UK Citizens Online Democracy. All rights reserved.
# Email: matthew@mysociety.org; WWW: http://www.mysociety.org

import re
import xml.sax
from optparse import make_option
from django.core.management.base import LabelCommand
# Not using LayerMapping as want more control, but what it does is what this does
#from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.gdal import *
from mapit.models import Area, Generation, Country, Type, CodeType, NameType
from mapit.management.command_utils import save_polygons, KML

class Command(LabelCommand):
    help = 'Import OSM data'
    args = '<OSM KML files generated by mapit_osm_to_kml (make sure fylke KML file is first)>'
    option_list = LabelCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    def handle_label(self, filename, **options):
        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        if not new_generation:
            raise Exception, "No new generation to be used for import!"

        print filename

        # Need to parse the KML manually to get the ExtendedData
        kml_data = KML()
        xml.sax.parse(filename, kml_data)

        code_type_osm = CodeType.objects.get(code='osm')
        code_type_n5000 = CodeType.objects.get(code='n5000')

        ds = DataSource(filename)
        layer = ds[0]
        for feat in layer:
            name = feat['Name'].value
            if not isinstance(name, unicode):
                name = name.decode('utf-8')
            name = re.sub('\s+', ' ', name)
            print " ", name.encode('utf-8')

            code = int(kml_data.data[name]['ref'])
            if code == 301: # Oslo ref in OSM could be either 3 (fylke) or 301 (kommune). Make sure it's 3.
                code = 3
            if code < 100: # Not particularly nice, but fine
                area_code = 'NFY'
                parent_area = None
                code_str = '%02d' % code
            else:
                area_code = 'NKO'
                code_str = '%04d' % code
                parent_area = Area.objects.get(id=int(code_str[0:2]))

            def update_or_create():
                try:
                    m = Area.objects.get(id=code)
                except Area.DoesNotExist:
                    m = Area(
                        id = code,
                        name = name,
                        type = Type.objects.get(code=area_code),
                        country = Country.objects.get(code='O'),
                        parent_area = parent_area,
                        generation_low = new_generation,
                        generation_high = new_generation,
                    )

                if m.generation_high and current_generation and m.generation_high.id < current_generation.id:
                    raise Exception, "Area %s found, but not in current generation %s" % (m, current_generation)
                m.generation_high = new_generation

                g = feat.geom.transform(4326, clone=True)
                poly = [ g ]

                if options['commit']:
                    m.save()
                    for k, v in kml_data.data[name].items():
                        if k in ('name:smi', 'name:fi'):
                    	    lang = 'N' + k[5:]
                    	    m.names.update_or_create({ 'type': NameType.objects.get(code=lang) }, { 'name': v })
                    m.codes.update_or_create({ 'type': code_type_n5000 }, { 'code': code_str })
                    m.codes.update_or_create({ 'type': code_type_osm }, { 'code': int(kml_data.data[name]['osm']) })
                    save_polygons({ code : (m, poly) })

            update_or_create()
            # Special case Oslo so it's in twice, once as fylke, once as kommune
            if code == 3:
                code, area_code, parent_area, code_str = 301, 'NKO', Area.objects.get(id=3), '0301'
                update_or_create()


########NEW FILE########
__FILENAME__ = mapit_print_areas
# For each generation, show every area, grouped by type

from django.core.management.base import NoArgsCommand
from mapit.models import Area, Generation, Type, NameType, Country, CodeType

class Command(NoArgsCommand):
    help = 'Show all areas by generation and area type'
    def handle_noargs(self, **options):
        for g in Generation.objects.all().order_by('id'):
            print g
            for t in Type.objects.all().order_by('code'):
                qs = Area.objects.filter(type=t,
                                         generation_high__gte=g,
                                         generation_low__lte=g)
                print "  %s (number of areas: %d)" % (t, qs.count())
                for a in qs:
                    print "    ", a

########NEW FILE########
__FILENAME__ = mapit_UK_add_ons_to_gss
# This script is for a one off import of all the old ONS codes to a MapIt
# containing only the new ones from a modern Boundary-Line.

import csv
import os.path
from django.core.management.base import NoArgsCommand
from mapit.models import Area, CodeType
from psycopg2 import IntegrityError

def process(new_code, old_code):
    try:
        area = Area.objects.get(codes__code=new_code, codes__type__code='gss')
    except Area.DoesNotExist:
        # An area that existed at the time of the mapping, but no longer
        return

    # Check if already has the right code
    if 'ons' in area.all_codes and area.all_codes['ons'] == old_code:
        return

    try:
        area.codes.create(type=CodeType.objects.get(code='ons'), code=old_code)
    except IntegrityError:
        raise Exception, "Key already exists for %s, can't give it %s" % (area, old_code)

class Command(NoArgsCommand):
    help = 'Inserts the old ONS codes into mapit'

    def handle_noargs(self, **options):
        mapping = csv.reader(open(os.path.dirname(__file__) + '/../../../data/UK/BL-2010-10-code-change.csv'))
        mapping.next()
        for row in mapping:
            new_code, name, old_code = row[0], row[1], row[3]
            process(new_code, old_code)

        mapping = csv.reader(open(os.path.dirname(__file__) + '/../../../data/UK/BL-2010-10-missing-codes.csv'))
        mapping.next()
        for row in mapping:
            type, new_code, old_code, name = row
            process(new_code, old_code)


########NEW FILE########
__FILENAME__ = mapit_UK_find_parents
# This script is used after Boundary-Line has been imported to
# associate shapes with their parents. With the new coding
# system coming in, this could be done from a BIG lookup table; however,
# I reckon P-in-P tests might be quick enough...

from django.core.management.base import NoArgsCommand
from mapit.models import Area, Generation

class Command(NoArgsCommand):
    help = 'Find parents for shapes'

    def handle_noargs(self, **options):
        new_generation = Generation.objects.new()
        if not new_generation:
            raise Exception, "No new generation to be used for import!"

        parentmap = {
            # A District council ward's parent is a District council:
            'DIW': 'DIS',
            # A County council ward's parent is a County council:
            'CED': 'CTY',
            # A London borough ward's parent is a London borough:
            'LBW': 'LBO',
            # A London Assembly constituency's parent is the Greater London Authority:
            'LAC': 'GLA',
            # A Metropolitan district ward's parent is a Metropolitan district:
            'MTW': 'MTD',
            # A Unitary Authority ward (UTE)'s parent is a Unitary Authority:
            'UTE': 'UTA',
            # A Unitary Authority ward (UTW)'s parent is a Unitary Authority:
            'UTW': 'UTA',
            # A Scottish Parliament constituency's parent is a Scottish Parliament region:
            'SPC': 'SPE',
            # A Welsh Assembly constituency's parent is a Welsh Assembly region:
            'WAC': 'WAE',
            # A Civil Parish's parent is one of:
            #   District council
            #   Unitary Authority
            #   Metropolitan district
            #   London borough
            #   Scilly Isles
            'CPC': ('DIS', 'UTA', 'MTD', 'LBO', 'COI'),
            'CPW': 'CPC',
        }
        for area in Area.objects.filter(
            type__code__in=parentmap.keys(),
            generation_low__lte=new_generation, generation_high__gte=new_generation,
        ):
            parent = None
            for polygon in area.polygons.all():
                try:
                    args = {
                        'polygons__polygon__contains': polygon.polygon.point_on_surface,
                        'generation_low__lte': new_generation,
                        'generation_high__gte': new_generation,
                    }
                    if isinstance(parentmap[area.type.code], str):
                        args['type__code'] = parentmap[area.type.code]
                    else:
                        args['type__code__in'] = parentmap[area.type.code]
                    parent = Area.objects.get(**args)
                    break
                except Area.DoesNotExist:
                    continue
            if not parent:
                raise Exception, "Area %s does not have a parent?" % (self.pp_area(area))
            if area.parent_area != parent:
                print "Parent for %s was %s, is now %s" % (self.pp_area(area), self.pp_area(area.parent_area), self.pp_area(parent))
                area.parent_area = parent
                area.save()

    def pp_area(self, area):
        if not area: return "None"
        return "%s [%d] (%s)" % (area.name, area.id, area.type.code)

########NEW FILE########
__FILENAME__ = mapit_UK_fix_2011-10
# As per the comment in the 2011-10 control file, this script is to be run
# one-off after that import in order to get the two old boundaries back in that
# were removed due to a mistake in the 2011-05 Boundary-Line.

from optparse import make_option
from django.core.management.base import LabelCommand
from django.contrib.gis.gdal import *
from mapit.models import Area, CodeType
from utils import save_polygons

class Command(LabelCommand):
    help = 'Import OS Boundary-Line'
    args = '<October 2010 Boundary-Line parish and district ward SHP files>'
    option_list = LabelCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    def handle_label(self,  filename, **options):
        code_version = CodeType.objects.get(code='gss')
        for feat in DataSource(filename)[0]:
            name = unicode(feat['NAME'].value, 'iso-8859-1')
            ons_code = feat['CODE'].value
            if ons_code in ('E04008782', 'E05004419'):
                m = Area.objects.get(codes__type=code_version, codes__code=ons_code)
                if options['commit']:
                    print 'Updating %s' % name
                    save_polygons({ ons_code: (m, [ feat.geom ]) })


########NEW FILE########
__FILENAME__ = mapit_UK_fix_2012-05
# As per the comment in the 2012-05 control file, this script is to be run
# one-off after that import in order to get the four old boundaries back
# that were removed during that import.

import re
from optparse import make_option
from django.core.management.base import LabelCommand
from django.contrib.gis.gdal import *
from mapit.models import Area, CodeType, Type, Country, Generation, NameType
from utils import save_polygons

class Command(LabelCommand):
    help = 'Import OS Boundary-Line'
    args = '<October 2010 Boundary-Line unitary/district SHP file>'
    option_list = LabelCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    def handle_label(self,  filename, **options):
        code_version = CodeType.objects.get(code='gss')
        name_type = NameType.objects.get(code='O')
        for feat in DataSource(filename)[0]:
            name = unicode(feat['NAME'].value, 'iso-8859-1')
            name = re.sub('\s*\(DET( NO \d+|)\)\s*(?i)', '', name)
            name = re.sub('\s+', ' ', name)
            ons_code = feat['CODE'].value
            area_code = feat['AREA_CODE'].value
            country = ons_code[0]
            if ons_code in ('E07000100', 'E07000104', 'S12000009', 'S12000043'):
                assert Area.objects.filter(codes__type=code_version, codes__code=ons_code).count() == 0
                print ons_code, area_code, country, name

                m = Area(
                    type = Type.objects.get(code=area_code),
                    country = Country.objects.get(code=country),
                    generation_low = Generation.objects.get(id=1),
                    generation_high = Generation.objects.get(id=14),
                )
                if options['commit']:
                    m.save()
                    m.names.update_or_create({ 'type': name_type }, { 'name': name })
                    m.codes.update_or_create({ 'type': code_version }, { 'code': ons_code })
                    save_polygons({ ons_code: (m, [feat.geom]) })


########NEW FILE########
__FILENAME__ = mapit_UK_fix_2013-10
# As per the comment in the 2013-10 control file, this script is to be run
# one-off after that import in order to get the four old boundaries back
# that were removed during that import.

import re
from optparse import make_option
from django.core.management.base import LabelCommand
from django.contrib.gis.gdal import *
from mapit.models import Area, Code, CodeType, Type, Country, Generation, NameType
from ..command_utils import save_polygons

class Command(LabelCommand):
    help = 'Import OS Boundary-Line'
    args = '<May 2013 Boundary-Line unitary/district SHP file>'
    option_list = LabelCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    def handle_label(self,  filename, **options):
        code_version = CodeType.objects.get(code='gss')
        name_type = NameType.objects.get(code='O')

        # Update the new areas to have the right codes
        # Northumberland, Gateshead, Stevenage, East Hertfordshire (in that order)
        areas_to_update = {
            2248: 'E06000057',
            2523: 'E08000037',
            2347: 'E07000243',
            2342: 'E07000242',
        }

        for id, code in areas_to_update.iteritems():
            area = Area.objects.get(id=id)
            print "Updating: {0} to: {1}".format(area, code)
            area.generation_low = Generation.objects.new()
            if options['commit']:
                area.save()
            old_code = Code.objects.get(type__code='gss', area=area)
            old_code.code = code
            if options['commit']:
                old_code.save()

        # Add in new areas to represent the old boundaries too
        for feat in DataSource(filename)[0]:
            name = feat['NAME'].value
            if not isinstance(name, unicode):
                name = name.decode('iso-8859-1')
            name = re.sub('\s*\(DET( NO \d+|)\)\s*(?i)', '', name)
            name = re.sub('\s+', ' ', name)
            ons_code = feat['CODE'].value
            area_code = feat['AREA_CODE'].value
            country = ons_code[0]
            new_area = None
            # Gateshead, Stevenage, East Hertfordshire (in that order)
            if ons_code in ('E08000020', 'E07000101', 'E07000097'):
                new_area = self.make_new_area(name, ons_code, area_code, code_version, 1, 20, country)
            elif ons_code == 'E06000048':
                # Northumberland was only in the db from 11-20
                new_area = self.make_new_area(name, ons_code, area_code, code_version, 11, 20, country)
            if new_area and options['commit']:
                new_area.save()
                new_area.names.update_or_create({ 'type': name_type }, { 'name': name })
                new_area.codes.update_or_create({ 'type': code_version }, { 'code': ons_code })
                save_polygons({ ons_code: (new_area, [feat.geom]) })

    def make_new_area(self, name, ons_code, area_code, code_version, generation_low, generation_high, country):
        assert Area.objects.filter(codes__type=code_version, codes__code=ons_code).count() == 0
        print ons_code, area_code, country, name

        return Area(
            type = Type.objects.get(code=area_code),
            country = Country.objects.get(code=country),
            generation_low = Generation.objects.get(id=generation_low),
            generation_high = Generation.objects.get(id=generation_high),
        )

########NEW FILE########
__FILENAME__ = mapit_UK_import_2011_scotparl
# This script is used to import the 2011 Scottish Parliament from OS Boundary-Line.

import re
from optparse import make_option
from django.core.management.base import LabelCommand
from django.contrib.gis.gdal import *
from mapit.models import Area, Generation, Country, Type, CodeType, NameType
from mapit.management.command_utils import save_polygons

name_to_code = {
    'Aberdeen Central P Const': 'S16000074',
    'Aberdeen Donside P Const': 'S16000075',
    'Aberdeen South and North Kincardine P Const': 'S16000076',
    'Aberdeenshire East P Const': 'S16000077',
    'Aberdeenshire West P Const': 'S16000078',
    'Airdrie and Shotts P Const': 'S16000079',
    'Almond Valley P Const': 'S16000080',
    'Angus North and Mearns P Const': 'S16000081',
    'Angus South P Const': 'S16000082',
    'Argyll and Bute P Const': 'S16000083',
    'Ayr P Const': 'S16000084',
    'Banffshire and Buchan Coast P Const': 'S16000085',
    'Caithness, Sutherland and Ross P Const': 'S16000086',
    'Carrick, Cumnock and Doon Valley P Const': 'S16000087',
    'Clackmannanshire and Dunblane P Const': 'S16000088',
    'Clydebank and Milngavie P Const': 'S16000089',
    'Clydesdale P Const': 'S16000090',
    'Coatbridge and Chryston P Const': 'S16000091',
    'Cowdenbeath P Const': 'S16000092',
    'Cumbernauld and Kilsyth P Const': 'S16000093',
    'Cunninghame North P Const': 'S16000094',
    'Cunninghame South P Const': 'S16000095',
    'Dumbarton P Const': 'S16000096',
    'Dumfriesshire P Const': 'S16000097',
    'Dundee City East P Const': 'S16000098',
    'Dundee City West P Const': 'S16000099',
    'Dunfermline P Const': 'S16000100',
    'East Kilbride P Const': 'S16000101',
    'East Lothian P Const': 'S16000102',
    'Eastwood P Const': 'S16000103',
    'Edinburgh Central P Const': 'S16000104',
    'Edinburgh Eastern P Const': 'S16000105',
    'Edinburgh Northern and Leith P Const': 'S16000106',
    'Edinburgh Pentlands P Const': 'S16000107',
    'Edinburgh Southern P Const': 'S16000108',
    'Edinburgh Western P Const': 'S16000109',
    'Na h-Eileanan an Iar P Const': 'S16000110',
    'Ettrick, Roxburgh and Berwickshire P Const': 'S16000111',
    'Falkirk East P Const': 'S16000112',
    'Falkirk West P Const': 'S16000113',
    'Galloway and West Dumfries P Const': 'S16000114',
    'Glasgow Anniesland P Const': 'S16000115',
    'Glasgow Cathcart P Const': 'S16000116',
    'Glasgow Kelvin P Const': 'S16000117',
    'Glasgow Maryhill and Springburn P Const': 'S16000118',
    'Glasgow Pollok P Const': 'S16000119',
    'Glasgow Provan P Const': 'S16000120',
    'Glasgow Shettleston P Const': 'S16000121',
    'Glasgow Southside P Const': 'S16000122',
    'Greenock and Inverclyde P Const': 'S16000123',
    'Hamilton, Larkhall and Stonehouse P Const': 'S16000124',
    'Inverness and Nairn P Const': 'S16000125',
    'Kilmarnock and Irvine Valley P Const': 'S16000126',
    'Kirkcaldy P Const': 'S16000127',
    'Linlithgow P Const': 'S16000128',
    'Mid Fife and Glenrothes P Const': 'S16000129',
    'Midlothian North and Musselburgh P Const': 'S16000130',
    'Midlothian South, Tweeddale and Lauderdale P Const': 'S16000131',
    'Moray P Const': 'S16000132',
    'Motherwell and Wishaw P Const': 'S16000133',
    'North East Fife P Const': 'S16000134',
    'Orkney Islands P Const': 'S16000135',
    'Paisley P Const': 'S16000136',
    'Perthshire North P Const': 'S16000137',
    'Perthshire South and Kinrossshire P Const': 'S16000138',
    'Renfrewshire North and West P Const': 'S16000139',
    'Renfrewshire South P Const': 'S16000140',
    'Rutherglen P Const': 'S16000141',
    'Shetland Islands P Const': 'S16000142',
    'Skye, Lochaber and Badenoch P Const': 'S16000143',
    'Stirling P Const': 'S16000144',
    'Strathkelvin and Bearsden P Const': 'S16000145',
    'Uddingston and Bellshill P Const': 'S16000146',
    'Central Scotland PER': 'S17000009',
    'Glasgow PER': 'S17000010',
    'Highland and Islands PER': 'S17000011',
    'Lothian PER': 'S17000012',
    'Mid Scotland and Fife PER': 'S17000013',
    'North East Scotland PER': 'S17000014',
    'South Scotland PER': 'S17000015',
    'West of Scotland PER': 'S17000016',
}

class Command(LabelCommand):
    help = 'Import OS Boundary-Line Scottish Parliament 2011 in advance'
    args = '<Boundary-Line SHP files>'
    option_list = LabelCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    ons_code_to_shape = {}

    def handle_label(self,  filename, **options):
        print filename
        new_generation = Generation.objects.new()
        if not new_generation:
            raise Exception, "No new generation to be used for import!"

        name_type = NameType.objects.get(code='O')
        code_type = CodeType.objects.get(code='gss')

        ds = DataSource(filename)
        layer = ds[0]
        for feat in layer:
            name = unicode(feat['NAME'].value, 'iso-8859-1')
            print " ", name
            name = re.sub('\s*\(DET( NO \d+|)\)\s*(?i)', '', name)
            name = re.sub('\s+', ' ', name)

            if "P Const" in name: area_code = 'SPC'
            elif "PER" in name: area_code = 'SPE'
            else: raise Exception, "Unknown type of area %s" % name

            ons_code = name_to_code[name]

            if ons_code in self.ons_code_to_shape:
                m, poly = self.ons_code_to_shape[ons_code]
                if options['commit']:
                    m_name = m.names.get(type=name_type).name
                    if name != m_name:
                        raise Exception, "ONS code %s is used for %s and %s" % (ons_code, name, m_name)
                # Otherwise, combine the two shapes for one area
                print "    Adding subsequent shape to ONS code %s" % ons_code
                poly.append(feat.geom)
                continue

            try:
                m = Area.objects.get(codes__type=code_type, codes__code=ons_code)
            except Area.DoesNotExist:
                m = Area(
                    type = Type.objects.get(code=area_code),
                    country = Country.objects.get(name='Scotland'),
                    generation_low = new_generation,
                    generation_high = new_generation,
                )

            if options['commit']:
                m.save()

            poly = [ feat.geom ]

            if options['commit']:
                m.names.update_or_create({ 'type': name_type }, { 'name': name })
            if ons_code:
                self.ons_code_to_shape[ons_code] = (m, poly)
                if options['commit']:
                    m.codes.update_or_create({ 'type': code_type }, { 'code': ons_code })

        if options['commit']:
            save_polygons(self.ons_code_to_shape)


########NEW FILE########
__FILENAME__ = mapit_UK_import_boundary_line
# This script is used to import information from OS Boundary-Line,
# which contains digital boundaries for administrative areas within
# Great Britain. Northern Ireland is handled separately, during the
# postcode import phase.

import re
import sys
from optparse import make_option
from django.core.management.base import LabelCommand
# Not using LayerMapping as want more control, but what it does is what this does
#from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.gdal import *
from mapit.models import Area, Name, Generation, Country, Type, CodeType, NameType
from mapit.management.command_utils import save_polygons

class Command(LabelCommand):
    help = 'Import OS Boundary-Line'
    args = '<Boundary-Line SHP files (wards before Westminster)>'
    option_list = LabelCommand.option_list + (
        make_option('--control', action='store', dest='control', help='Refer to a Python module that can tell us what has changed'),
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    ons_code_to_shape = {}
    unit_id_to_shape = {}

    def handle_label(self,  filename, **options):
        if not options['control']:
            raise Exception, "You must specify a control file"
        __import__(options['control'])
        control = sys.modules[options['control']]

        code_version = CodeType.objects.get(code=control.code_version())
        name_type = NameType.objects.get(code='O')
        code_type_os = CodeType.objects.get(code='unit_id')

        print filename
        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        if not new_generation:
            raise Exception, "No new generation to be used for import!"

        ds = DataSource(filename)
        layer = ds[0]
        for feat in layer:
            name = feat['NAME'].value
            if not isinstance(name, unicode):
                name = name.decode('iso-8859-1')

            name = re.sub('\s*\(DET( NO \d+|)\)\s*(?i)', '', name)
            name = re.sub('\s+', ' ', name)

            ons_code = feat['CODE'].value if feat['CODE'].value not in ('999999', '999999999') else None
            unit_id = str(feat['UNIT_ID'].value)
            area_code = feat['AREA_CODE'].value
            patch = self.patch_boundary_line(ons_code, area_code)
            if patch == True: ons_code = None
            elif patch: ons_code = patch

            if area_code == 'NCP': continue # Ignore Non Parished Areas

            if ons_code in self.ons_code_to_shape:
                m, poly = self.ons_code_to_shape[ons_code]
                try:
                    m_name = m.names.get(type=name_type).name
                except Name.DoesNotExist:
                    m_name = m.name # If running without commit for dry run, so nothing being stored in db
                if name != m_name:
                    raise Exception, "ONS code %s is used for %s and %s" % (ons_code, name, m_name)
                # Otherwise, combine the two shapes for one area
                poly.append(feat.geom)
                continue

            if unit_id in self.unit_id_to_shape:
                m, poly = self.unit_id_to_shape[unit_id]
                try:
                    m_name = m.names.get(type=name_type).name
                except Name.DoesNotExist:
                    m_name = m.name # If running without commit for dry run, so nothing being stored in db
                if name != m_name:
                    raise Exception, "Unit ID code %s is used for %s and %s" % (unit_id, name, m_name)
                # Otherwise, combine the two shapes for one area
                poly.append(feat.geom)
                continue

            if code_version.code == 'gss' and ons_code:
                country = ons_code[0] # Hooray!
            elif area_code in ('CED', 'CTY', 'DIW', 'DIS', 'MTW', 'MTD', 'LBW', 'LBO', 'LAC', 'GLA'):
                country = 'E'
            elif code_version.code == 'gss':
                raise Exception, area_code
            elif (area_code == 'EUR' and 'Scotland' in name) or area_code in ('SPC', 'SPE') or (ons_code and ons_code[0:3] in ('00Q', '00R')):
                country = 'S'
            elif (area_code == 'EUR' and 'Wales' in name) or area_code in ('WAC', 'WAE') or (ons_code and ons_code[0:3] in ('00N', '00P')):
                country = 'W'
            elif area_code in ('EUR', 'UTA', 'UTE', 'UTW', 'CPC'):
                country = 'E'
            else: # WMC
                # Make sure WMC are loaded after all wards...
                area_within = Area.objects.filter(type__code__in=('UTW','UTE','MTW','COP','LBW','DIW'), polygons__polygon__contains=feat.geom.geos.point_on_surface)[0]
                country = area_within.country.code
            # Can't do the above ons_code checks with new GSS codes, will have to do more PinP checks
            # Do parents in separate P-in-P code after this is done.

            try:
                check = control.check(name, area_code, country, feat.geom)
                if check == True:
                    raise Area.DoesNotExist
                if isinstance(check, Area):
                    m = check
                    ons_code = m.codes.get(type=code_version).code
                elif ons_code:
                    m = Area.objects.get(codes__type=code_version, codes__code=ons_code)
                elif unit_id:
                    m = Area.objects.get(codes__type=code_type_os, codes__code=unit_id, generation_high=current_generation)
                    m_name = m.names.get(type=name_type).name
                    if name != m_name:
                        raise Exception, "Unit ID code %s is %s in DB but %s in SHP file" % (unit_id, m_name, name)
                else:
                    raise Exception, 'Area "%s" (%s) has neither ONS code nor unit ID' % (name, area_code)
                if int(options['verbosity']) > 1:
                    print "  Area matched, %s" % (m, )
            except Area.DoesNotExist:
                print "  New area: %s %s %s %s" % (area_code, ons_code, unit_id, name)
                m = Area(
                    name = name, # If committing, this will be overwritten by the m.names.update_or_create
                    type = Type.objects.get(code=area_code),
                    country = Country.objects.get(code=country),
                    generation_low = new_generation,
                    generation_high = new_generation,
                )

            if m.generation_high and current_generation and m.generation_high.id < current_generation.id:
                raise Exception, "Area %s found, but not in current generation %s" % (m, current_generation)
            m.generation_high = new_generation
            if options['commit']:
                m.save()

            poly = [ feat.geom ]

            if options['commit']:
                m.names.update_or_create({ 'type': name_type }, { 'name': name })
            if ons_code:
                self.ons_code_to_shape[ons_code] = (m, poly)
                if options['commit']:
                    m.codes.update_or_create({ 'type': code_version }, { 'code': ons_code })
            if unit_id:
                self.unit_id_to_shape[unit_id] = (m, poly)
                if options['commit']:
                    m.codes.update_or_create({ 'type': code_type_os }, { 'code': unit_id })

        if options['commit']:
            save_polygons(self.unit_id_to_shape)
            save_polygons(self.ons_code_to_shape)

    def patch_boundary_line(self, ons_code, area_code):
        """Fix mistakes in Boundary-Line"""
        if area_code == 'WMC' and ons_code == '42UH012':
            return True
        if area_code == 'UTA' and ons_code == 'S16000010':
            return 'S12000010'
        return False


########NEW FILE########
__FILENAME__ = mapit_UK_import_codepoint
# This script is used to import Great Britain postcode information from
# Code-Point Open, released by the Ordnance Survey. Compared to the
# scripts we had in 2003, and that the data is free, I'm in heaven.
# 
# The fields of a Code-Point Open CSV file before August 2011 are:
#   Postcode, Quality, 8 blanked out fields, Easting, Northing, Country,
#   NHS region, NHS health authority, County, District, Ward, blanked field
#
# The fields after August 2011, with blank fields removed and with new GSS
# codes, are: Postcode, Quality, Easting, Northing, Country, NHS region, NHS
# health authority, County, District, Ward

import csv
from mapit.management.commands.mapit_import_postal_codes import Command

class Command(Command):
    help = 'Import OS Code-Point Open postcodes'
    args = '<Code-Point CSV files>'
    often = 10000
    option_defaults = { 'strip': True, 'srid': 27700 }

    def pre_row(self, row, options):
        if row[1] == '90':
            return False # Bad postcode
        # A new Code-Point only has 10 columns
        if len(row) == 10:
            options['coord-field-lon'] = 3
            options['coord-field-lat'] = 4
        else:
            options['coord-field-lon'] = 11
            options['coord-field-lat'] = 12
        return True


########NEW FILE########
__FILENAME__ = mapit_UK_import_ni_output_areas
# This script is used to import information from the Northern Ireland
# Output Areas, available from http://www.nisra.gov.uk/geography/default.asp2.htm

import urllib
from optparse import make_option
from django.core.management.base import LabelCommand
# Not using LayerMapping as want more control, but what it does is what this does
#from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.gdal import *
from mapit.models import Area, Generation, Country, Type, CodeType, NameType
from mapit.management.command_utils import save_polygons

class Command(LabelCommand):
    help = 'Import NI Output Areas'
    args = '<NI Super Output Area shapefile> <NI Output Area shapefile>'
    option_list = LabelCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    ons_code_to_shape = {}
    councils = []

    def handle_label(self,  filename, **options):
        country = Country.objects.get(code='N')
        oa_type = Type.objects.get(code='OUA')
        soa_type = Type.objects.get(code='OLF')
        name_type = NameType.objects.get(code='S')
        code_type = CodeType.objects.get(code='ons')

        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        if not new_generation:
            raise Exception, "No new generation to be used for import!"

        # Compile an alphabetical list of NI councils and their wards, OA codes
        # are assigned alphabetically.
        if not self.councils:
            self.councils = Area.objects.filter(type=Type.objects.get(code='LGD')).order_by('name').values()
            for lgd in self.councils:
                lges = Area.objects.filter(parent_area=lgd['id'])
                areas = []
                for lge in lges:
                    lgws = Area.objects.filter(parent_area=lge).values()
                    areas += lgws
                lgd['wards'] = sorted(areas, key=lambda x: x['name'])

        ds = DataSource(filename)
        layer = ds[0]
        layer_name = str(layer)
        for feat in layer:
            if layer_name == 'soa':
                area_type = soa_type
                ons_code = feat['SOA_CODE'].value
                name = feat['SOA_LABEL'].value.replace('_', ' ')
            elif layer_name == 'OA_ni':
                area_type = oa_type
                ons_code = feat['OA_CODE'].value
                name = 'Output Area %s' % ons_code
            else:
                raise Exception, 'Bad data passed in'

            council = ord(ons_code[2:3]) - 65
            ward = int(ons_code[4:6]) - 1
            if ward == 98: # SOA covers two wards, set parent to council, best we can do
                parent = self.councils[council]['id']
            else:
                parent = self.councils[council]['wards'][ward]['id']

            try:
                m = Area.objects.get(codes__type=code_type, codes__code=ons_code)
                if int(options['verbosity']) > 1:
                    print "  Area matched, %s" % (m, )
            except Area.DoesNotExist:
                print "  New area: %s" % (ons_code)
                m = Area(
                    name = name, # If committing, this will be overwritten by the m.names.update_or_create
                    type = area_type,
                    country = country,
                    parent_area_id = parent,
                    generation_low = new_generation,
                    generation_high = new_generation,
                )

            if m.generation_high and current_generation and m.generation_high.id < current_generation.id:
                raise Exception, "Area %s found, but not in current generation %s" % (m, current_generation)
            m.generation_high = new_generation
            m.parent_area_id = parent
            if options['commit']:
                m.save()

            f = feat.geom
            f.srid = 29902
            poly = [ f ]

            if options['commit']:
                m.names.update_or_create({ 'type': name_type }, { 'name': name })
            if ons_code:
                self.ons_code_to_shape[ons_code] = (m, poly)
                if options['commit']:
                    m.codes.update_or_create({ 'type': code_type }, { 'code': ons_code })

        if options['commit']:
            save_polygons(self.ons_code_to_shape)


########NEW FILE########
__FILENAME__ = mapit_UK_import_nspd_crown_dependencies
# This script is used to import Crown Dependency postcode information from the
# National Statistics Postcode Database.
# http://www.ons.gov.uk/about-statistics/geography/products/geog-products-postcode/nspd/

import csv
from mapit.management.commands.mapit_import_postal_codes import Command

class Command(Command):
    help = 'Imports Crown Dependency postcodes from the NSPD'
    args = '<NSPD CSV file>'
    option_defaults = { 'strip': True, 'location': False }

    def pre_row(self, row, options):
        if row[4]: return False # Terminated postcode
        if self.code[0:2] not in ('GY', 'JE', 'IM'): return False # Only importing Crown dependencies from NSPD
        return True

########NEW FILE########
__FILENAME__ = mapit_UK_import_nspd_national_parks
# This script is used to import National Park postcode information from the
# National Statistics Postcode Database.
# http://www.ons.gov.uk/about-statistics/geography/products/geog-products-postcode/nspd/
# 
# Just as an example, haven't actually run this.
#
# The fields of NSPD Open CSV file are:
#   0: Postcode (7), 36: National Park

import csv
from django.core.management.base import LabelCommand
from mapit.models import Postcode, Area, Generation, Type

lookup = {
    '01': 'Dartmoor National Park',
    '02': 'Exmoor National Park',
    '03': 'Lake District National Park',
    '04': 'Northumberland National Park',
    '05': 'North York Moors National Park',
    '06': 'Peak District National Park',
    '07': 'The Broads Authority',
    '08': 'Yorkshire Dales National Park',
    '09': 'Brecon Beacons National Park',
    '10': 'Pembrokeshire Coast National Park',
    '11': 'Snowdonia National Park',
    '12': 'New Forest National Park',
    '14': 'The Cairngorms National Park',
    '15': 'The Loch Lomond and the Trossachs National Park',
    '16': 'South Downs National Park',
}

class Command(LabelCommand):
    help = 'Imports postcode->National Park from the NSPD, creates the areas if need be'
    args = '<NSPD CSV file>'

    def handle_label(self, file, **options):
        if not Generation.objects.new():
            raise Exception, "No new generation to be used for import!"

        count = 0
        for row in csv.reader(open(file)):
            if row[4]: continue # Terminated postcode
            if row[11] == '9': continue # PO Box etc.

            postcode = row[0].strip().replace(' ', '')
            if postcode[0:2] == 'BT':
                srid = 29902
            else:
                srid = 27700

            try:
                pc = Postcode.objects.get(postcode=postcode)
            except Postcode.DoesNotExist:
                continue # Ignore postcodes that aren't already in db

            national_park = row[36]
            name = lookup[national_park]
            national_park_area = Area.objects.get_or_create_with_name( type=Type.objects.get(code='NPK'), name_type='S', name=name )
            pc.areas.add(national_park_area)

            count += 1
            if count % 10000 == 0:
                print "Imported %d" % count

########NEW FILE########
__FILENAME__ = mapit_UK_import_nspd_ni
# This script is used to import Northern Ireland postcode information from the
# National Statistics Postcode Database.
# http://www.ons.gov.uk/about-statistics/geography/products/geog-products-postcode/nspd/
# 
# The fields of NSPD Open CSV file are:
#   Postcode (7), Postcode (8), Postcode (sp), Start date, End date, County,
#   council, ward, usertype, Easting, Northing, quality, SHA, IT cluster,
#   country, GOR, Stats region, Parliamentary constituency, Euro region,
#   TEC/LEC, Travel to Work area, Primary Care Org, NUTS, 1991 census ED,
#   1991 census ED, ED indicator, Pre-July 2006 SHA, LEA, Pre 2002 Health
#   Authority, 1991 ward code, 1991 ward code, 1998 ward code, 2005 stats ward,
#   OA code, OA indicator, CAS ward, National Park, SOA (Lower), Datazone, SOA
#   (Middle), Urban/rural, Urban/rural, Urban/rural, Intermediate, SOA (NI), OA
#   classification, Pre October 2006 PCO

import csv
import os.path
from django.db import transaction
from mapit.models import Area
from mapit.management.commands.mapit_import_postal_codes import Command

class Command(Command):
    help = 'Imports Northern Ireland postcodes from the NSPD, using existing areas only'
    args = '<NSPD CSV file>'
    option_defaults = { 'strip': True, 'srid': 29902, 'coord-field-lon': 10, 'coord-field-lat': 11 }

    @transaction.commit_manually
    def handle_label(self, file, **options):
        # First set up the areas needed (as we have to match to postcode manually)
        self.euro_area = Area.objects.get(country__code='N', type__code='EUR')

        # Read in new ONS code to names, look up existing wards and Parliamentary constituencies
        snac = csv.reader(open(os.path.dirname(__file__) + '/../../../data/UK/snac-2009-ni-cons2ward.csv'))
        snac.next()
        code_to_area = {}
        for parl_code, parl_name, ward_code, ward_name, district_code, district_name in snac:
            ward_code = ward_code.replace(' ', '')
            if ward_code not in code_to_area:
                ward_area = Area.objects.get(
                    country__code='N', type__code='LGW', codes__type__code='ons', codes__code=ward_code
                )
                code_to_area[ward_code] = ward_area

            if parl_code not in code_to_area and len(parl_code)==3: # Ignore Derryaghy line
                parl_area = Area.objects.get(
                    country__code='N', type__code='WMC', codes__type__code='ons', codes__code=parl_code,
                )
                gss_code = parl_area.all_codes['gss']
                # Store lookup for both old and new codes, so any version of NSPD will work
                code_to_area[parl_code] = parl_area
                code_to_area[gss_code] = parl_area
                nia_area = Area.objects.get(
                    country__code='N', type__code='NIE', names__type__code='S', names__name=parl_name,
                )
                code_to_area['NIE' + parl_code] = nia_area
                code_to_area['NIE' + gss_code] = nia_area
        self.code_to_area = code_to_area

        # Start the main import process
        self.process(file, options)

    def pre_row(self, row, options):
        if row[4]: return False # Terminated postcode
        if row[11] == '9': return False # PO Box etc.
        if self.code[0:2] != 'BT': return False # Only importing NI from NSPD

        # NSPD (now ONSPD) started using GSS codes for Parliament in February 2011
        # Detect this here; although they're still using old codes for council/wards
        gss = True if len(row[7]) == 6 else False

        # Create/update the areas
        if gss:
            ons_code = row[7].replace(' ', '')
            parl_code = row[17]
        else:
            ons_code = ''.join(row[5:8])
            parl_code = row[17].replace('N', '7')
        #output_area = row[33]
        #super_output_area = row[44]

        ward = self.code_to_area[ons_code]
        electoral_area = ward.parent_area
        self.areas = [
            ward,
            electoral_area,
            electoral_area.parent_area, # Council
            self.code_to_area['NIE' + parl_code], # Assembly
            self.code_to_area[parl_code], # Parliament
            self.euro_area,
        ]

        return True

    def post_row(self, pc):
        pc.areas.clear()
        pc.areas.add(*self.areas)
        transaction.commit()


########NEW FILE########
__FILENAME__ = mapit_UK_import_nspd_ni_areas
# This script is used to import Northern Ireland areas into MaPit
# 
# XXX This is incomplete, it needs to know which things have had boundary changes
# like import_boundary_line does. Hopefully just using new GSS codes by the time
# NI has any boundary changes.

import csv, re
import os.path
from django.contrib.gis.geos import Point
from django.core.management.base import NoArgsCommand
from mapit.models import Postcode, Area, Generation, Country, Type, CodeType, NameType

class Command(NoArgsCommand):
    help = 'Creates/updates Northern Ireland areas'

    def handle_noargs(self, **options):
        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        country = Country.objects.get(code='N')
        if not new_generation:
            raise Exception, "No new generation to be used for import!"

        code_type = CodeType.objects.get(code='gss')
        name_type = NameType.objects.get(code='S')

        euro_area, created = Area.objects.get_or_create(country=country, type=Type.objects.get(code='EUR'),
            generation_low__lte=current_generation, generation_high__gte=current_generation,
            defaults = { 'generation_low': new_generation, 'generation_high': new_generation }
        )
        euro_area.generation_high = new_generation
        euro_area.save()
        euro_area.names.get_or_create(type=name_type, name='Northern Ireland')

        # Read in ward name -> electoral area name/area
        ni_eas = csv.reader(open(os.path.dirname(__file__) + '/../../../data/UK/ni-electoral-areas.csv'))
        ni_eas.next()
        ward_to_electoral_area = {}
        e = {}
        for district, electoral_area, ward, dummy in ni_eas:
            if not district:
                district = last_district
            if not electoral_area:
                electoral_area = last_electoral_area
            last_district = district
            last_electoral_area = electoral_area
            if electoral_area not in e:
                ea = Area.objects.get_or_create_with_name(
                    country=country, type=Type.objects.get(code='LGE'), name_type='M', name=electoral_area,
                )
                e[electoral_area] = ea
            ward_to_electoral_area.setdefault(district, {})[ward] = e[electoral_area]

        # Read in new ONS code to names
        snac = csv.reader(open(os.path.dirname(__file__) + '/../../../data/UK/snac-2009-ni-cons2ward.csv'))
        snac.next()
        code_to_area = {}
        for parl_code, parl_name, ward_code, ward_name, district_code, district_name in snac:
            if district_name not in ward_to_electoral_area:
                raise Exception, "District %s is missing" % district_name
            if ward_name not in ward_to_electoral_area[district_name]:
                raise Exception, "Ward %s, district %s is missing" % (ward_name, district_name)

            ward_code = ward_code.replace(' ', '')

            if district_code not in code_to_area:
                district_area = Area.objects.get_or_create_with_code(
                    country=country, type=Type.objects.get(code='LGD'), code_type='ons', code=district_code,
                )
                district_area.names.get_or_create(type=name_type, name=district_name)
                code_to_area[district_code] = district_area

            if ward_code not in code_to_area:
                ward_area = Area.objects.get_or_create_with_code(
                    country=country, type=Type.objects.get(code='LGW'), code_type='ons', code=ward_code
                )
                ward_area.names.get_or_create(type=name_type, name=ward_name)
                ward_area.parent_area = ward_to_electoral_area[district_name][ward_name]
                ward_area.save()
                ward_area.parent_area.parent_area = code_to_area[district_code]
                ward_area.parent_area.save()
                code_to_area[ward_code] = ward_area

            if ward_code == '95S24': continue # Derryaghy

            if parl_code not in code_to_area:
                parl_area = Area.objects.get_or_create_with_code(
                    country=country, type=Type.objects.get(code='WMC'), code_type='ons', code=parl_code,
                )
                parl_area.names.get_or_create(type=name_type, name=parl_name)
                new_code = re.sub('^7', 'N060000', parl_code)
                parl_area.codes.get_or_create(type=code_type, code=new_code)
                code_to_area[parl_code] = parl_area
                
            if 'NIE' + parl_code not in code_to_area:
                nia_area = Area.objects.get_or_create_with_name(
                    country=country, type=Type.objects.get(code='NIE'), name_type='S', name=parl_name,
                )
                code_to_area['NIE' + parl_code] = nia_area


########NEW FILE########
__FILENAME__ = mapit_UK_import_police_force_areas
# This script is used to import police force area boundaries into MapIt. These
# boundaries are published as KML files at:
#
#     http://data.gov.uk/dataset/police-force-boundaries-england-and-wales
#
# The dataset also includes a very vague polygon for Northern Ireland with only
# 7 points - this will be imported, but you might want to delete it afterwards.
#
# Scotland is not covered by this dataset, but as of 1st April 2013 has one
# police force for the whole country, called Police Scotland.


import json
import os
import sys
import urllib2

from optparse import make_option

from django.core.management import call_command
from django.core.management.base import LabelCommand

from mapit.models import Type, NameType, Country, CodeType


DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')


class Command(LabelCommand):
    help = 'Import England, Wales and Northern Ireland police force area boundaries from .kml files'
    args = '<directory containing KML files from data.gov.uk>'
    option_list = LabelCommand.option_list + (
        make_option(
            '--commit',
            action='store_true',
            dest='commit',
            help='Actually update the database'
        ),
        make_option(
            '--generation_id',
            action="store",
            dest='generation_id',
            help='Which generation ID should be used',
        ),
        make_option(
            '--area_type_code',
            action="store",
            dest='area_type_code',
            help='Which area type should be used (specify using code)',
        ),
        make_option(
            '--name_type_code',
            action="store",
            dest='name_type_code',
            help='Which name type should be used (specify using code)',
        ),
        make_option(
            '--code_type',
            action="store",
            dest='code_type',
            help='Which code type should be used (specify using its code)',
        ),
        make_option(
            '--preserve',
            action="store_true",
            dest='preserve',
            help="Create a new area if the name's the same but polygons differ"
        ),
        make_option(
            '--new',
            action="store_true",
            dest='new',
            help="Don't look for existing areas at all, just import everything as new areas"
        ),
        make_option(
            '--fix_invalid_polygons',
            action="store_true",
            dest='fix_invalid_polygons',
            help="Try to fix any invalid polygons and multipolygons found"
        ),
    )

    def handle_label(self, directory, **options):

        err = False
        for k in ['generation_id', 'area_type_code', 'name_type_code', 'code_type']:
            if options[k]:
                continue
            print "Missing argument '--%s'" % k
            err = True
        if err:
            sys.exit(1)

        generation_id = options['generation_id']
        area_type_code = options['area_type_code']
        name_type_code = options['name_type_code']
        code_type_code = options['code_type']

        try:
            Country.objects.get(code='E')
            Country.objects.get(code='W')
            Country.objects.get(code='N')
        except Country.DoesNotExist:
            print "England, Wales and Northern Ireland don't exist yet; load the UK fixture first."
            sys.exit(1)
        welsh_forces = ('dyfed-powys', 'gwent', 'north-wales', 'south-wales')

        # The KML files don't contain the names of each force, but the filenames
        # are the force IDs used by the police API, so we can fetch the names
        # data and save the IDs as codes for future use:
        names_data_filename = os.path.join(DATA_DIRECTORY, "police_force_names.json")
        if not os.path.exists(names_data_filename):
            print "Can't find force names data at %s; trying to fetch it from the police API instead..." % names_data_filename
            url = "http://data.police.uk/api/forces"
            forces = urllib2.urlopen(url)
            with open(names_data_filename, 'w') as f:
                f.write(forces.read())
            print "...successfully fetched and saved the force names data."

        with open(names_data_filename) as names_file:
            names_data = json.load(names_file)

        # Map force codes to names for easy lookup:
        codes_to_names = dict((d['id'], d['name']) for d in names_data)

        # Ensure that these types exist already, because if --commit is not
        # specified then mapit_import will prompt for their descriptions
        # for each force:
        try:
            Type.objects.get(code=area_type_code)
            NameType.objects.get(code=name_type_code)
            CodeType.objects.get(code=code_type_code)
        except (Type.DoesNotExist, NameType.DoesNotExist, CodeType.DoesNotExist) as e:
            print e, "Create the area, name and code types first."
            sys.exit(1)

        print "Importing police force areas from %s" % directory

        # mapit_import command kwargs which are common to all forces:
        command_kwargs = {
            'generation_id': generation_id,
            'area_type_code': area_type_code,
            'name_type_code': name_type_code,
            'code_type': code_type_code,
            'name_field': None,
            'code_field': None,
            'use_code_as_id': False,
            'encoding': None,
        }
        for option in ('commit', 'preserve', 'new', 'fix_invalid_polygons'):
            command_kwargs[option] = options[option]

        for kml_file in os.listdir(directory):
            code, extension = os.path.splitext(kml_file)
            if extension.lower() != '.kml':
                continue
            file_path = os.path.join(directory, kml_file)

            country_code = 'E'
            if code in welsh_forces:
                country_code = 'W'
            elif code == 'northern-ireland':
                country_code = 'N'

            try:
                name = codes_to_names[code]
            except KeyError:
                print "Could not find a force name in API JSON data for %s" % code
                sys.exit(1)

            call_command(
                'mapit_import',
                file_path,
                override_name=name,
                override_code=code,
                country_code=country_code,
                **command_kwargs
            )

########NEW FILE########
__FILENAME__ = mapit_UK_import_soa
# This script is used to import boundary polygons and other information
# from the ONS's CD-ROM of Super Output Areas for England and Wales.  
# Information about the CD-ROM here: http://bit.ly/63bX97

# Run as: ./manage.py mapit_UK_import_soa shapefile.shp

from django.core.management.base import LabelCommand
from django.contrib.gis.gdal import *
from mapit.models import Area, Generation, Country, Type, NameType, CodeType

class Command(LabelCommand):
    help = 'Creates Super Output Area boundaries from ONS shapefiles'
    args = '<ONS SOA shapefile>'

    def handle_label(self, filename, **options):
        print filename
        generation = Generation.objects.current()

        short_filename = filename.split("/")[-1]
        filename_prefix = short_filename[:4]
        filename_suffix = short_filename.split(".")[0][-3:]

        # check shapefile type - we handle both LSOA and MSOA
        if filename_prefix=="LSOA":
            feat_name = 'LSOA04NM'
            feat_code = 'LSOA04CD'
            if filename_suffix=='BGC':
                area_type = 'OLG'
            else: 
                area_type = 'OLF'
        elif filename_prefix=="MSOA":
            feat_name = 'MSOA04NM'
            feat_code = 'MSOA04CD'
            if filename_suffix=='BGC':
                area_type = 'OMG'
            else: 
                area_type = 'OMF'
        else:
            raise Exception, "Sorry, this script only handles LSOA/MSOA shapefiles!"            
    
        ds = DataSource(filename)
        layer = ds[0]
        for feat in layer:
            # retrieve name and code, and set country
            name = feat[feat_name].value
            lsoa_code = feat[feat_code].value 
            country = lsoa_code[0]
            # skip if the SOA already exists in db (SOAs don't change)
            if Area.objects.filter(type__code=area_type, codes__code=lsoa_code).count():
                continue
            print "Adding %s (%s) %s" % (name, lsoa_code, feat.geom.geom_name)
            m = Area(
                type = Type.objects.get(code=area_type),
                country = Country.objects.get(code=country),
                generation_low = generation,
                generation_high = generation,
            )
            m.save()
            m.names.update_or_create({ 'type': NameType.objects.get(code='S') }, { 'name': name })
            m.codes.update_or_create({ 'type': CodeType.objects.get(code='ons') }, { 'code': lsoa_code })

            p = feat.geom
            if p.geom_name == 'POLYGON':
                shapes = [ p ]
            else:
                shapes = p
            for g in shapes:
                m.polygons.create(polygon=g.wkt)


########NEW FILE########
__FILENAME__ = mapit_UK_ni_consolidate_boundaries
# This script is used after importing NI output areas to create the higher
# level boundaries for the existing areas.

from optparse import make_option
from django.core.management.base import NoArgsCommand
from mapit.models import Area, Type, Geometry

class Command(NoArgsCommand):
    help = 'Puts the boundaries on the LGDs, LGWs and LGEs from the Output Areas'
    option_list = NoArgsCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    def handle_noargs(self, **options):
        area_type = Type.objects.get(code='OUA')
        done = []

        def save_polygons(area, **args):
            print 'Working on', area.type.code, area.name, '...',
            args['area__type'] = area_type
            geometry = Geometry.objects.filter(**args)
            p = geometry.unionagg()
            if options['commit']:
                area.polygons.all().delete()
                if p.geom_type == 'Polygon':
                    shapes = [ p ]
                else:
                    shapes = p
                for g in shapes:
                    area.polygons.create(polygon=g)
            done.append(area.id)
            print 'done'

        for ward in Area.objects.filter(type=Type.objects.get(code='LGW')):
            save_polygons(ward, area__parent_area=ward)

            lge = ward.parent_area
            if lge.id not in done:
                save_polygons(lge, area__parent_area__parent_area=lge)

            council = lge.parent_area
            if council.id not in done:
                save_polygons(council, area__parent_area__parent_area__parent_area=council)


########NEW FILE########
__FILENAME__ = mapit_UK_scilly
# This script is used to fix up the Isles of Scilly, as Boundary-Line only contains
# the Isles alone. We have to generate the COP parishes within it.

import csv
import re
from django.contrib.gis.geos import Point
from django.core.management.base import LabelCommand
from mapit.models import Postcode, Area, Generation, Country, Type, CodeType, NameType

class Command(LabelCommand):
    help = 'Sort out the Isles of Scilly'
    args = '<Code-Point Open TR file>'

    def handle_label(self, file, **options):
        # The Isles of Scilly have changed their code in B-L, but Code-Point still has the old code currently
        try:
            council = Area.objects.get(codes__type__code='gss', codes__code='E06000053')
        except:
            council = Area.objects.get(codes__type__code='ons', codes__code='00HF')
        if council.type != Type.objects.get(code='COI'):
            council.type = Type.objects.get(code='COI')
            council.save()
        
        wards = (
            ('00HFMA', 'E05008322', 'Bryher'),
            ('00HFMB', 'E05008323', 'St. Agnes'),
            ('00HFMC', 'E05008324', "St. Martin's"),
            ('00HFMD', 'E05008325', "St. Mary's"),
            ('00HFME', 'E05008326', 'Tresco'),
        )
        ward = {}
        for old_ward_code, new_ward_code, ward_name in wards:
            area = Area.objects.get_or_create_with_code(
                country=Country.objects.get(code='E'), type=Type.objects.get(code='COP'), code_type='gss', code=new_ward_code
            )
            area.names.get_or_create(type=NameType.objects.get(code='S'), name=ward_name)
            area.codes.get_or_create(type=CodeType.objects.get(code='ons'), code=old_ward_code)
            if area.parent_area != council:
                area.parent_area = council
                area.save()
            ward[old_ward_code] = area
            ward[new_ward_code] = area

        for row in csv.reader(open(file)):
            if row[1] == '90': continue
            postcode = row[0].strip().replace(' ', '')
            if len(row) == 10:
                ons_code = row[9]
                if not re.match('^E0500832[2-6]$', ons_code): continue
            else:
                ons_code = ''.join(row[15:18])
                if ons_code[0:4] != '00HF': continue
            pc = Postcode.objects.get(postcode=postcode)
            pc.areas.add(ward[ons_code])
            print ".",

########NEW FILE########
__FILENAME__ = mapit_UK_time_lookups
# A simple script for timing point-in-polygon lookups in an instance
# of MapIt UK.  The results for this tend to be quite variable - the
# suggestion in the timeit documentation is to take the minimum over
# a number of repetitions.

from random import randint, uniform, seed
from time import time
from timeit import timeit, Timer, repeat
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Min, Max
from mapit.models import *

minimum_postcode_id = Postcode.objects.aggregate(Min('id'))['id__min']
maximum_postcode_id = Postcode.objects.aggregate(Max('id'))['id__max']

def get_random_UK_location():
    """Return a random location generally on the UK mainland

    This doesn't need to be very good for our testing purposes, so we
    just pick a random postcode from the database, and add some error
    to the latitude and longitude for that postcode.  Sometimes this
    might give you a point which is actually out in the sea, but again
    this doesn't really matter for these purposes.  Obviously these
    locations aren't going to be uniform across the UK, since
    postcodes are more dense in towns."""

    location = None
    while not location:
        postcode_id = randint(minimum_postcode_id, maximum_postcode_id)
        try:
            location = Postcode.objects.get(id=postcode_id).location
        # It's always possible that the IDs aren't sequential:
        except Postcode.DoesNotExist:
            continue

    # This is (very) roughly a kilometer in degrees longitude or
    # latitude in the UK:
    max_error_to_add = 0.01
    new_lon = location.coords[0] + uniform(-max_error_to_add, max_error_to_add)
    new_lat = location.coords[1] + uniform(-max_error_to_add, max_error_to_add)
    location.coords = (new_lon, new_lat)
    return location

random_locations = None

class Command(BaseCommand):
    args = '<iterations>'
    help = 'Time many point-in-polygon lookups'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('There must be only one argument')

        try:
            iterations = int(args[0])
        except ValueError:
            raise CommandError('The iterations argument must be an integer')

        repeats = 5

        # So that the time to generate random locations isn't a factor
        # in the timing, generate all the locations ahead of time.
        # (In fact, this takes a vanishingly small amount of time
        # compared to the area lookups in the current version, but in
        # previous versions of this script generating random locations
        # was much slower.)

        to_generate = repeats * iterations
        print "Generating %d random locations in the UK ..." % (to_generate,)
        global random_locations
        random_locations = [get_random_UK_location() for _ in xrange(to_generate)]
        print "... done."

        # Now look up each of those locations, timing the process with
        # timeit.  Note that the list() is required to cause
        # evaluation of the GeoQuerySet.

        print "Testing point-in-polygon tests ..."
        result = repeat(stmt='list(Area.objects.by_location(random_locations.pop()))',
                        setup='''
from mapit.models import Area
from mapit.management.commands.mapit_UK_time_lookups import random_locations
''',
                        repeat=repeats,
                        number=iterations)
        print "... done."

        print result

########NEW FILE########
__FILENAME__ = mapit_UK_update_ons_ids
# This script is for a one off import of all the new GSS codes.

import csv
from django.core.management.base import NoArgsCommand
from mapit.models import Area, Generation, CodeType
from psycopg2 import IntegrityError

class Command(NoArgsCommand):
    help = 'Inserts all the new GSS codes into mapit'
    args = '<CSV file mapping old to new>'

    def handle_noargs(self, **options):
        current_generation = Generation.objects.current()

        # Read in ward name -> electoral area name/area
        mapping = csv.reader(open('../data/UK/BL-2010-10-code-change.csv'))
        mapping.next()
        for row in mapping:
            new_code, name, old_code = row[0], row[1], row[3]
            try:
                area = Area.objects.get(codes__code=old_code, codes__type__code='ons')
            except Area.MultipleObjectsReturned:
                if old_code == '11' or old_code == '12':
                    # Also the IDs of two EURs, but they're not in this lookup
                    area = Area.objects.get(type__code='CTY', codes__code=old_code, codes__type__code='ons')
                elif old_code == '09':
                    # Also the ID of a now non-existent county council
                    area = Area.objects.get(type__code='EUR', codes__code=old_code, codes__type__code='ons')
                else:
                    raise
            except Area.DoesNotExist:
                # Don't have old WMC codes in, go on name
                try:
                    area = Area.objects.get(type__code='WMC', name=name.decode('iso-8859-1'), generation_high=current_generation)
                except:
                    # New parishes in 2010-01
                    # 00NS007 Caldey Island and St. Margaret's Island
                    # 00PK027 Risca East
                    # 00PK028 Risca West
                    # 18UK064 Area not comprised in any Parish-Lundy Island
                    # 19UG029 Affpuddle and Turnerspuddle
                    continue

            # Check if already has the right code
            if 'gss' in area.all_codes and area.all_codes['gss'] == new_code:
                continue

            try:
                area.codes.create(type=CodeType.objects.get(code='gss'), code=new_code)
            except IntegrityError:
                raise Exception, "Key already exists for %s, can't give it %s" % (area, new_code)


########NEW FILE########
__FILENAME__ = mapit_UK_update_ons_ids2
# This script is for a one off import of all the new GSS codes.
# To include the ones not in the file from Ordnance Survey.

import csv
from django.core.management.base import NoArgsCommand
from mapit.models import Area, Generation, CodeType
from psycopg2 import IntegrityError

class Command(NoArgsCommand):
    help = 'Inserts all the new GSS codes into mapit'
    args = '<CSV file mapping old to new>'

    def handle_noargs(self, **options):
        current_generation = Generation.objects.current()

        # Read in ward name -> electoral area name/area
        mapping = csv.reader(open('../data/UK/BL-2010-10-missing-codes.csv'))
        mapping.next()
        for row in mapping:
            type, new_code, old_code, name = row
            try:
                area = Area.objects.get(type__code=type, codes__code=old_code, codes__type__code='ons')
            except Area.DoesNotExist:
                area = Area.objects.get(type__code=type, name=name.decode('iso-8859-1'), generation_high=current_generation)

            # Check if already has the right code
            if 'gss' in area.all_codes and area.all_codes['gss'] == new_code:
                continue

            try:
                area.codes.create(type=CodeType.objects.get(code='gss'), code=new_code)
            except IntegrityError:
                raise Exception, "Key already exists for %s, can't give it %s" % (area, new_code)


########NEW FILE########
__FILENAME__ = mapit_use_osm_place_name
# use_osm_place_name.py:
#
# Look through KML files for any that have 'Unknown name for ...' as
# their name - if they have a place_name tag in their extended data,
# update the corresponding Area in the database with that name.
#
# Copyright (c) 2011, 2012 UK Citizens Online Democracy. All rights reserved.
# Email: mark@mysociety.org; WWW: http://www.mysociety.org

import os
import re
from optparse import make_option
from django.core.management.base import LabelCommand
from mapit.models import Area, Code, CodeType
from glob import glob
import urllib2
from lxml import etree

class Command(LabelCommand):
    help = 'Find any "Unknown" names, and use place_name instead, if possible'
    args = '<KML-DIRECTORY>'
    option_list = LabelCommand.option_list + (
        make_option('--commit', action='store_true', dest='commit', help='Actually update the database'),
    )

    def handle_label(self, directory_name, **options):

        if not os.path.isdir(directory_name):
            raise Exception, "'%s' is not a directory" % (directory_name,)

        os.chdir(directory_name)

        if not glob("al[0-1][0-9]"):
            raise Exception, "'%s' did not contain any admin level directories (e.g. al02, al03, etc.)" % (directory_name,)

        def verbose(s):
            if int(options['verbosity']) > 1:
                print s.encode('utf-8')

        verbose("Loading any admin boundaries from " + directory_name)

        unknown_names_before = Area.objects.filter(name__startswith='Unknown name').count()

        for admin_level in range(2,12):

            verbose("Loading admin_level " + str(admin_level))

            admin_directory = "al%02d" % (admin_level)

            if not os.path.exists(admin_directory):
                verbose("Skipping the non-existent " + admin_directory)
                continue

            verbose("Loading all KML in " + admin_directory)

            files = sorted(os.listdir(admin_directory))
            total_files = len(files)

            for i, e in enumerate(files):

                progress = "[%d%% complete] " % ((i * 100) / total_files,)

                if not e.endswith('.kml'):
                    verbose("Ignoring non-KML file: " + e)
                    continue

                m = re.search(r'^(way|relation)-(\d+)-', e)
                if not m:
                    raise Exception, u"Couldn't extract OSM element type and ID from: " + e

                osm_type, osm_id = m.groups()

                kml_filename = os.path.join(admin_directory, e)

                if not re.search('Unknown name for', e):
                    continue

                verbose(progress + "Loading " + unicode(os.path.realpath(kml_filename), 'utf-8'))

                tree = etree.parse(kml_filename)
                place_name_values = tree.xpath('//kml:Placemark/kml:ExtendedData/kml:Data[@name="place_name"]/kml:value',
                                               namespaces={'kml': 'http://earth.google.com/kml/2.1'} )

                if len(place_name_values) > 0:

                    place_name = place_name_values[0].text

                    verbose(u"Found a better name: " + place_name)

                    # Then we can replace the name:

                    if osm_type == 'relation':
                        code_type_osm = CodeType.objects.get(code='osm_rel')
                    elif osm_type == 'way':
                        code_type_osm = CodeType.objects.get(code='osm_way')
                    else:
                        raise Exception, "Unknown OSM element type:", osm_type

                    try:
                        existing_area = Code.objects.get(type=code_type_osm, code=osm_id).area
                    except Code.DoesNotExist:
                        print "WARNING: failed to find Code with code_type %s and code %s" % (code_type_osm, osm_id)
                        continue

                    # Just check that the existing area really does
                    # still have an unknown name:

                    if not existing_area.name.startswith('Unknown name'):
                        print (u"The existing area already had a sensible name: " + existing_area.name).encode('utf-8')
                        raise Exception, "Not overwriting sensible name, exiting."

                    existing_area.name = place_name

                    if options['commit']:
                        existing_area.save()

        unknown_names_after = Area.objects.filter(name__startswith='Unknown name').count()

        print "unknown_names_before:", unknown_names_before
        print "unknown_names_after:", unknown_names_after

########NEW FILE########
__FILENAME__ = command_utils
# Shared functions for postcode and area importing.

import re
import sys
from xml.sax.handler import ContentHandler
import shapely.ops
import shapely.wkt
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon

class KML(ContentHandler):
    def __init__(self, *args, **kwargs):
        self.content = ''
        self.data = {}

    def characters(self, content):
        self.content += content

    @staticmethod
    def normalize_whitespace(s):
        return re.sub('(?us)\s+', ' ', s).strip()

    def endElement(self, name):
        if name == 'name':
            self.current = {}
            self.data[self.normalize_whitespace(self.content)] = self.current
        elif name == 'value':
            self.current[self.name] = self.content.strip()
            self.name = None
        self.content = ''

    def startElement(self, name, attr):
        if name == 'Data':
            self.name = self.normalize_whitespace(attr['name'])

def save_polygons(lookup):
    for shape in lookup.values():
        m, poly = shape
        if not poly:
            continue
        sys.stdout.write(".")
        sys.stdout.flush()
        #g = OGRGeometry(OGRGeomType('MultiPolygon'))
        m.polygons.all().delete()
        for p in poly:
            if p.geom_name == 'POLYGON':
                shapes = [ p ]
            else:
                shapes = p
            for g in shapes:
                # Ignore any shape with fewer than four points, to
                # avoid introducing invalid polygons into the
                # database.
                if g.point_count < 4:
                    continue
                # XXX Using g.wkt directly when importing Norway KML works fine
                # with Django 1.1, Postgres 8.3, PostGIS 1.3.3 but fails with
                # Django 1.2, Postgres 8.4, PostGIS 1.5.1, saying that the
                # dimensions constraint fails - because it is trying to import a
                # shape as 3D as the WKT contains an altitude at the end of
                # every co-ordinate. Removing the altitudes from the KML, and/or
                # using altitudeMode makes no difference to the WKT here, so the
                # only easy solution appears to be removing the altitude
                # directly from the WKT before using it.
                dimensions_re = r'([\d.-]+\s+[\d.-]+)(\s+[\d.-]+)(,|\))'
                must_be_two_d = re.sub(dimensions_re, r'\1\3', g.wkt)
                m.polygons.create(polygon=must_be_two_d)
        #m.polygon = g.wkt
        #m.save()
        poly[:] = [] # Clear the polygon's list, so that if it has both an ons_code and unit_id, it's not processed twice
    print ""


def fix_with_buffer(geos_polygon):
    return geos_polygon.buffer(0)

def fix_with_exterior_union_polygonize(geos_polygon):
    exterior_ring = geos_polygon.exterior_ring
    unioned = exterior_ring.union(exterior_ring)
    # We want to use GEOSPolygonize which isn't exposed via
    # django.contrib.gis.geos, but is available via shapely:
    shapely_unioned = shapely.wkt.loads(unioned.wkt)
    try:
        reconstructed_geos_polygons = [
            GEOSGeometry(sp.wkt, geos_polygon.srid) for sp in
            shapely.ops.polygonize(shapely_unioned)]
    except ValueError:
        reconstructed_geos_polygons = []
    return MultiPolygon(reconstructed_geos_polygons)

def fix_invalid_geos_polygon(geos_polygon, methods=('buffer', 'exterior')):
    """Try to make a valid version of an invalid GEOS polygon

    The test cases and techniques used here are from the helpful
    presentation here: http://s3.opengeo.org/postgis-power.pdf

      3  ------>------
         |           |
         |           |
      2  |     x     |
         |    / \    |
         ^   /   \   |
      1  |  x     x  |
         |   \   /   |
         |    \ /    |
      0  --<--| |---<--

         0  1  2  3  4

    This is the "banana polygon" example, if you imagine the points at
    (2, 0) drawn together to be the same point.

    >>> from django.contrib.gis.geos import Polygon
    >>> coords = [(0, 0), (0, 3), (4, 3), (4, 0),
    ...           (2, 0), (3, 1), (2, 2), (1, 1),
    ...           (2, 0), (0, 0)]
    >>> poly = Polygon(coords)
    >>> poly.valid
    False

    That one should be fixable just with the ST_Buffer(_, 0) technique:

    >>> fixed = fix_invalid_geos_polygon(poly, 'buffer')
    >>> fixed.valid
    True
    >>> len(fixed)
    2
    >>> import math
    >>> expected_length = 3 + 3 + 4 + 4 + 4 * math.sqrt(2)
    >>> abs(fixed.length - expected_length) < 0.000001
    True

    Others need the more complex technique mentioned in that PDF, such
    as this figure-of-eight polygon:

      2         -->--
               |     |
               |     |
      1   --<-----<--
         |     |
         |     |
      0   -->--

         0     1     2

    ... with coordinates as follows:

    >>> coords = [(0, 0), (1, 0), (1, 2), (2, 2),
    ...           (2, 1), (0, 1), (0, 0)]
    >>> poly = Polygon(coords)
    >>> poly.valid
    False

    The function should return a valid version with the right
    perimeter length:

    >>> fixed = fix_invalid_geos_polygon(poly, ('buffer', 'exterior'))
    >>> fixed.valid
    True
    >>> fixed.length
    8.0

    Also, check that this can fix a invalid polygon that's equivalent
    to four separate polygons:

      2  ---x---
         | / \ |
         |/   \|
      1  x     x
         |\   /|
         | \ / |
      0  ---x---

         0  1  2

    ... where the points start at the bottom 'x', go right around the
    outside square clockwise and then go around the inside square
    anti-clockwise, creating 4 filled triangles with a square hole in
    the middle:

    >>> coords = [(1, 0), (0, 0), (0, 2), (2, 2), (2, 0), (1, 0),
    ...           (2, 1), (1, 2), (0, 1), (1, 0)]
    >>> poly = Polygon(coords)
    >>> poly.valid
    False

    Try to fix it:

    >>> fixed = fix_invalid_geos_polygon(poly)
    >>> fixed.valid
    True
    >>> len(fixed)
    4
    >>> expected_length = 2 + 2 + 2 + 2 + 4 * math.sqrt(2)
    >>> abs(fixed.length - expected_length) < 0.000001
    True
    """

    cutoff = 0.01
    original_length = geos_polygon.length

    for method, fix_function in (
        ('buffer', fix_with_buffer),
        ('exterior', fix_with_exterior_union_polygonize)
        ):
        if method in methods:
            fixed = fix_function(geos_polygon)
            if not fixed:
                continue
            difference = abs(original_length - fixed.length)
            if (difference / float(original_length)) < cutoff:
                return fixed
    return None

def fix_invalid_geos_multipolygon(geos_multipolygon):
    """Try to fix an invalid GEOS MultiPolygon

    Two overlapping valid polyons should be unioned to one shape:

    3  ---------                3  ---------
       | A     |                   | C     |
    2  |   ----|----            2  |       -----
       |   |   |   |   --->        |           |
    1  ----|----   |            1  -----       |
           |     B |                   |       |
    0      ---------            0      ---------

       0   1   2   3               0   1   2   3

    >>> coords_a = [(0, 1), (0, 3), (2, 3), (2, 1), (0, 1)]
    >>> coords_b = [(1, 0), (1, 2), (3, 2), (3, 0), (1, 0)]
    >>> coords_c = [(0, 1), (0, 3), (2, 3), (2, 2), (3, 2),
    ...             (3, 0), (1, 0), (1, 1), (0, 1)]

    >>> mp = MultiPolygon(Polygon(coords_a), Polygon(coords_b))
    >>> mp.valid
    False

    >>> fixed_mp = fix_invalid_geos_multipolygon(mp)
    >>> fixed_mp.valid
    True
    >>> expected_polygon = Polygon(coords_c)
    >>> fixed_mp.equals(expected_polygon)
    True

    If there's one valid and one fixable invalid polygon in the
    multipolygon, it should return a multipolygon with the valid one
    and the fixed version:

      2         -->--
               | D   |
               |     |
      1   --<-----<--       -----
         |     |           | E   |
         |     |           |     |
      0   -->--             -----

         0     1     2     3     4

    >>> coords_d = [(0, 0), (1, 0), (1, 2), (2, 2),
    ...             (2, 1), (0, 1), (0, 0)]
    >>> coords_e = [(3, 0), (3, 1), (4, 1), (4, 0), (3, 0)]
    >>> mp = MultiPolygon(Polygon(coords_d), Polygon(coords_e))
    >>> mp.valid
    False

    >>> fixed_mp = fix_invalid_geos_multipolygon(mp)
    >>> fixed_mp.valid
    True

    The eventual result should be three squares:

    >>> fixed_mp.num_geom
    3
    >>> fixed_mp.area
    3.0
    >>> expected_polygon = MultiPolygon(Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]),
    ...                                 Polygon([(1, 1), (1, 2), (2, 2), (2, 1), (1, 1)]),
    ...                                 Polygon([(3, 0), (3, 1), (4, 1), (4, 0), (3, 0)]))
    >>> fixed_mp.equals(expected_polygon)
    True

    If all the polygons are invalid and unfixable, an empty
    MultiPolygon will be returned.  This example, where the loop
    around the inner diamond is traversed clockwise as well, seems to
    be unfixable, so it's a good example for this:

      2  ---x---
         | / \ |
         |/   \|
      1  x     x
         |\   /|
         | \ / |
      0  ---x---

         0  1  2

    Here the points start at the bottom 'x', go right around the
    outside square clockwise and then go around the inside square
    clockwise as well.

    >>> coords = [(1, 0), (0, 0), (0, 2), (2, 2), (2, 0), (1, 0),
    ...           (0, 1), (1, 2), (2, 1), (1, 0)]
    >>> poly = Polygon(coords)
    >>> poly.valid
    False
    >>> mp = MultiPolygon(poly)
    >>> fixed = fix_invalid_geos_multipolygon(mp)
    >>> len(fixed)
    0

    """

    polygons = list(geos_multipolygon)
    # If all of the polygons in the KML are individually
    # valid, then we just need to union them:
    individually_all_valid = all(p.valid for p in polygons)
    if individually_all_valid:
        for_union = geos_multipolygon
    # Otherwise, try to fix the individually broken
    # polygons, discard any unfixable ones, and union
    # the result:
    else:
        valid_polygons = []
        for p in polygons:
            if p.valid:
                valid_polygons.append(p)
            else:
                fixed = fix_invalid_geos_polygon(p)
                if fixed is not None:
                    if fixed.geom_type == 'MultiPolygon':
                        valid_polygons += list(fixed)
                    elif fixed.geom_type == 'Polygon':
                        valid_polygons.append(fixed)
                    else:
                        raise "Unknown fixed geometry type:", fixed.geom_type
        for_union = MultiPolygon(valid_polygons)
    if len(for_union) > 0:
        result = for_union.cascaded_union
        # If they have been unioned into a single Polygon, still return
        # a MultiPolygon, for consistency of return types:
        if result.geom_type == 'Polygon':
            result = MultiPolygon(result)
    else:
        result = for_union
    return result

if __name__ == "__main__":
    import doctest
    doctest.testmod()


def fix_invalid_geos_geometry(geos_geometry):
    """
    Try to fix a geometry if it is either a polygon or multipolygon.
    """
    if geos_geometry.geom_type == 'Polygon':
        return fix_invalid_geos_polygon(geos_geometry)
    elif geos_geometry.geom_type == 'MultiPolygon':
        return fix_invalid_geos_multipolygon(geos_geometry)
    else:
        raise Exception("Don't know how to fix an invalid %s" % geos_geometry.geom_type)

########NEW FILE########
__FILENAME__ = managers
from django.contrib.gis.db import models
from django.core.exceptions import ObjectDoesNotExist

# Given unique look-up attributes, and extra data attributes,
# either updates the entry referred to if it exists, or
# creates it if it doesn't.
# Returns string describing what has happened.
def update_or_create(self, filter_attrs, attrs):
    try:
        obj = self.get(**filter_attrs)
        changed = False
        for k, v in attrs.items():
            if obj.__dict__[k] != v:
                changed = True
                obj.__dict__[k] = v
        if changed:
            obj.save()
            return 'updated'
        return 'unchanged'
    except ObjectDoesNotExist:
        attrs.update(filter_attrs)
        self.create(**attrs)
        return 'created'

class GeoManager(models.GeoManager):
    def update_or_create(self, filter_attrs, attrs):
        return update_or_create(self, filter_attrs, attrs)

class Manager(models.Manager):
    def update_or_create(self, filter_attrs, attrs):
        return update_or_create(self, filter_attrs, attrs)


########NEW FILE########
__FILENAME__ = view_error
# Middleware to catch any sort of error from our views,
# and output it as either HTML or JSON appropriately

from django import http
from django.template import RequestContext
from django.template.loader import render_to_string
from mapit.shortcuts import output_json

class ViewException(Exception):
    pass

class ViewExceptionMiddleware(object):
    def process_exception(self, request, exception):
        if not isinstance(exception, ViewException):
            return None

        format, message, code = exception.args
        if format == 'html':
            types = {
                400: http.HttpResponseBadRequest,
                404: http.HttpResponseNotFound,
                500: http.HttpResponseServerError,
            }
            response_type = types.get(code, http.HttpResponse)
            return response_type(render_to_string(
                'mapit/%s.html' % code,
                { 'error': message, },
                context_instance=RequestContext(request)
            ))
        return output_json({ 'error': message }, code=code)


########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'Generation'
        db.create_table('mapit_generation', (
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('mapit', ['Generation'])

        # Adding model 'Country'
        db.create_table('mapit_country', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=1, unique=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, unique=True)),
        ))
        db.send_create_signal('mapit', ['Country'])

        # Adding model 'Type'
        db.create_table('mapit_type', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=3, unique=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
        ))
        db.send_create_signal('mapit', ['Type'])

        # Adding model 'Area'
        db.create_table('mapit_area', (
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('country', self.gf('django.db.models.fields.related.ForeignKey')(related_name='areas', blank=True, null=True, to=orm['mapit.Country'])),
            ('parent_area', self.gf('django.db.models.fields.related.ForeignKey')(related_name='children', blank=True, null=True, to=orm['mapit.Area'])),
            ('generation_high', self.gf('django.db.models.fields.related.ForeignKey')(related_name='final_areas', null=True, to=orm['mapit.Generation'])),
            ('generation_low', self.gf('django.db.models.fields.related.ForeignKey')(related_name='new_areas', null=True, to=orm['mapit.Generation'])),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='areas', to=orm['mapit.Type'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('mapit', ['Area'])

        # Adding model 'Geometry'
        db.create_table('mapit_geometry', (
            ('polygon', self.gf('django.contrib.gis.db.models.fields.PolygonField')(srid=settings.MAPIT_AREA_SRID)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('area', self.gf('django.db.models.fields.related.ForeignKey')(related_name='polygons', to=orm['mapit.Area'])),
        ))
        db.send_create_signal('mapit', ['Geometry'])

        # Adding model 'Name'
        db.create_table('mapit_name', (
            ('type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('area', self.gf('django.db.models.fields.related.ForeignKey')(related_name='names', to=orm['mapit.Area'])),
        ))
        db.send_create_signal('mapit', ['Name'])

        # Adding unique constraint on 'Name', fields ['area', 'type']
        db.create_unique('mapit_name', ['area_id', 'type'])

        # Adding model 'Code'
        db.create_table('mapit_code', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('area', self.gf('django.db.models.fields.related.ForeignKey')(related_name='codes', to=orm['mapit.Area'])),
        ))
        db.send_create_signal('mapit', ['Code'])

        # Adding unique constraint on 'Code', fields ['area', 'type']
        db.create_unique('mapit_code', ['area_id', 'type'])

        # Adding model 'Postcode'
        db.create_table('mapit_postcode', (
            ('location', self.gf('django.contrib.gis.db.models.fields.PointField')(null=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('postcode', self.gf('django.db.models.fields.CharField')(max_length=7, unique=True, db_index=True)),
        ))
        db.send_create_signal('mapit', ['Postcode'])

        # Adding M2M table for field areas on 'Postcode'
        db.create_table('mapit_postcode_areas', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('postcode', models.ForeignKey(orm['mapit.postcode'], null=False)),
            ('area', models.ForeignKey(orm['mapit.area'], null=False))
        ))
        db.create_unique('mapit_postcode_areas', ['postcode_id', 'area_id'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'Generation'
        db.delete_table('mapit_generation')

        # Deleting model 'Country'
        db.delete_table('mapit_country')

        # Deleting model 'Type'
        db.delete_table('mapit_type')

        # Deleting model 'Area'
        db.delete_table('mapit_area')

        # Deleting model 'Geometry'
        db.delete_table('mapit_geometry')

        # Removing unique constraint on 'Name', fields ['area', 'type']
        db.delete_unique('mapit_name', ['area_id', 'type'])

        # Deleting model 'Name'
        db.delete_table('mapit_name')

        # Removing unique constraint on 'Code', fields ['area', 'type']
        db.delete_unique('mapit_code', ['area_id', 'type'])

        # Deleting model 'Code'
        db.delete_table('mapit_code')

        # Deleting model 'Postcode'
        db.delete_table('mapit_postcode')

        # Removing M2M table for field areas on 'Postcode'
        db.delete_table('mapit_postcode_areas')
    
    
    models = {
        'mapit.area': {
            'Meta': {'object_name': 'Area'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'blank': 'True', 'null': 'True', 'to': "orm['mapit.Country']"}),
            'generation_high': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'final_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'generation_low': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'parent_area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'blank': 'True', 'null': 'True', 'to': "orm['mapit.Area']"}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'to': "orm['mapit.Type']"})
        },
        'mapit.code': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Code'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': "orm['mapit.Area']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        'mapit.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '1', 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True'})
        },
        'mapit.generation': {
            'Meta': {'object_name': 'Generation'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.geometry': {
            'Meta': {'object_name': 'Geometry'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polygons'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polygon': ('django.contrib.gis.db.models.fields.PolygonField', [], {'srid': str(settings.MAPIT_AREA_SRID)})
        },
        'mapit.name': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Name'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        'mapit.postcode': {
            'Meta': {'object_name': 'Postcode'},
            'areas': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'postcodes'", 'blank': 'True', 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True'}),
            'postcode': ('django.db.models.fields.CharField', [], {'max_length': '7', 'unique': 'True', 'db_index': 'True'})
        },
        'mapit.type': {
            'Meta': {'object_name': 'Type'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '3', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mapit']

########NEW FILE########
__FILENAME__ = 0002_add_nametype_codetype
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'NameType'
        db.create_table('mapit_nametype', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=10, unique=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
        ))
        db.send_create_signal('mapit', ['NameType'])

        # Adding model 'CodeType'
        db.create_table('mapit_codetype', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=10, unique=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
        ))
        db.send_create_signal('mapit', ['CodeType'])

        # Adding field 'Code.type_id'
        db.add_column('mapit_code', 'type_id', self.gf('django.db.models.fields.related.ForeignKey')(related_name='codes', null=True, to=orm['mapit.CodeType']), keep_default=False)

        # Adding field 'Name.type_id'
        db.add_column('mapit_name', 'type_id', self.gf('django.db.models.fields.related.ForeignKey')(related_name='names', null=True, to=orm['mapit.NameType']), keep_default=False)
    
    
    def backwards(self, orm):
        
        db.create_unique('mapit_code', ['type', 'area_id'])
        db.create_unique('mapit_name', ['type', 'area_id'])

        # Deleting model 'NameType'
        db.delete_table('mapit_nametype')

        # Deleting model 'CodeType'
        db.delete_table('mapit_codetype')

        # Deleting field 'Code.type_id'
        db.delete_column('mapit_code', 'type_id_id')

        # Deleting field 'Name.type_id'
        db.delete_column('mapit_name', 'type_id_id')
    
    
    models = {
        'mapit.area': {
            'Meta': {'object_name': 'Area'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'blank': 'True', 'null': 'True', 'to': "orm['mapit.Country']"}),
            'generation_high': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'final_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'generation_low': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'parent_area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'blank': 'True', 'null': 'True', 'to': "orm['mapit.Area']"}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'to': "orm['mapit.Type']"})
        },
        'mapit.code': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Code'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': "orm['mapit.Area']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'type_id': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'null': 'True', 'to': "orm['mapit.CodeType']"})
        },
        'mapit.codetype': {
            'Meta': {'object_name': 'CodeType'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '1', 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True'})
        },
        'mapit.generation': {
            'Meta': {'object_name': 'Generation'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.geometry': {
            'Meta': {'object_name': 'Geometry'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polygons'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polygon': ('django.contrib.gis.db.models.fields.PolygonField', [], {'srid': str(settings.MAPIT_AREA_SRID)})
        },
        'mapit.name': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Name'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'type_id': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'null': 'True', 'to': "orm['mapit.NameType']"})
        },
        'mapit.nametype': {
            'Meta': {'object_name': 'NameType'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.postcode': {
            'Meta': {'object_name': 'Postcode'},
            'areas': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'postcodes'", 'blank': 'True', 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True'}),
            'postcode': ('django.db.models.fields.CharField', [], {'max_length': '7', 'unique': 'True', 'db_index': 'True'})
        },
        'mapit.type': {
            'Meta': {'object_name': 'Type'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '3', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mapit']

########NEW FILE########
__FILENAME__ = 0003_convert_name_and_code_types
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.conf import settings

class Migration(DataMigration):
    
    def forwards(self, orm):
        for code in orm.Code.objects.all():
            code.type_id = orm.CodeType.objects.get(code=code.type)
            code.save()
        for name in orm.Name.objects.all():
            name.type_id = orm.NameType.objects.get(code=name.type)
            name.save()
    
    def backwards(self, orm):
        for code in orm.Code.objects.all():
            code.type = code.type_id.code
            code.save()
        for name in orm.Name.objects.all():
            name.type = name.type_id.code
            name.save()
    
    models = {
        'mapit.area': {
            'Meta': {'object_name': 'Area'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'blank': 'True', 'null': 'True', 'to': "orm['mapit.Country']"}),
            'generation_high': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'final_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'generation_low': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'parent_area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'blank': 'True', 'null': 'True', 'to': "orm['mapit.Area']"}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'to': "orm['mapit.Type']"})
        },
        'mapit.code': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Code'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': "orm['mapit.Area']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'type_id': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'null': 'True', 'to': "orm['mapit.CodeType']"})
        },
        'mapit.codetype': {
            'Meta': {'object_name': 'CodeType'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '1', 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True'})
        },
        'mapit.generation': {
            'Meta': {'object_name': 'Generation'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.geometry': {
            'Meta': {'object_name': 'Geometry'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polygons'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polygon': ('django.contrib.gis.db.models.fields.PolygonField', [], {'srid': str(settings.MAPIT_AREA_SRID)})
        },
        'mapit.name': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Name'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'type_id': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'null': 'True', 'to': "orm['mapit.NameType']"})
        },
        'mapit.nametype': {
            'Meta': {'object_name': 'NameType'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.postcode': {
            'Meta': {'object_name': 'Postcode'},
            'areas': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'postcodes'", 'blank': 'True', 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True'}),
            'postcode': ('django.db.models.fields.CharField', [], {'max_length': '7', 'unique': 'True', 'db_index': 'True'})
        },
        'mapit.type': {
            'Meta': {'object_name': 'Type'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '3', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mapit']

########NEW FILE########
__FILENAME__ = 0004_remove_old_type_columns
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        db.delete_unique('mapit_code', ['type', 'area_id'])
        db.delete_column('mapit_code', 'type')
        db.rename_column('mapit_code', 'type_id_id', 'type_id')
        db.alter_column('mapit_code', 'type_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mapit.CodeType']))
        db.create_unique('mapit_code', ['type_id', 'area_id'])

        db.delete_unique('mapit_name', ['type', 'area_id'])
        db.delete_column('mapit_name', 'type')
        db.rename_column('mapit_name', 'type_id_id', 'type_id')
        db.alter_column('mapit_name', 'type_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mapit.NameType']))
        db.create_unique('mapit_name', ['type_id', 'area_id'])
    
    
    def backwards(self, orm):
        db.delete_unique('mapit_code', ['type_id', 'area_id'])
        db.alter_column('mapit_code', 'type_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['mapit.CodeType']))
        db.rename_column('mapit_code', 'type_id', 'type_id_id')
        db.add_column('mapit_code', 'type', self.gf('django.db.models.fields.CharField')(default='', max_length=10), keep_default=False)
        db.create_unique('mapit_code', ['area_id', 'type'])

        db.delete_unique('mapit_name', ['type_id', 'area_id'])
        db.alter_column('mapit_name', 'type_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['mapit.NameType']))
        db.rename_column('mapit_name', 'type_id', 'type_id_id')
        db.add_column('mapit_name', 'type', self.gf('django.db.models.fields.CharField')(default='', max_length=10), keep_default=False)
        db.create_unique('mapit_name', ['area_id', 'type'])
    
    models = {
        'mapit.area': {
            'Meta': {'object_name': 'Area'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'blank': 'True', 'null': 'True', 'to': "orm['mapit.Country']"}),
            'generation_high': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'final_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'generation_low': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'parent_area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'blank': 'True', 'null': 'True', 'to': "orm['mapit.Area']"}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'to': "orm['mapit.Type']"})
        },
        'mapit.code': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Code'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': "orm['mapit.Area']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': "orm['mapit.CodeType']"})
        },
        'mapit.codetype': {
            'Meta': {'object_name': 'CodeType'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '1', 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True'})
        },
        'mapit.generation': {
            'Meta': {'object_name': 'Generation'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.geometry': {
            'Meta': {'object_name': 'Geometry'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polygons'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polygon': ('django.contrib.gis.db.models.fields.PolygonField', [], {'srid': str(settings.MAPIT_AREA_SRID)})
        },
        'mapit.name': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Name'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': "orm['mapit.NameType']"})
        },
        'mapit.nametype': {
            'Meta': {'object_name': 'NameType'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.postcode': {
            'Meta': {'object_name': 'Postcode'},
            'areas': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'postcodes'", 'blank': 'True', 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True'}),
            'postcode': ('django.db.models.fields.CharField', [], {'max_length': '7', 'unique': 'True', 'db_index': 'True'})
        },
        'mapit.type': {
            'Meta': {'object_name': 'Type'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '3', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['mapit']

########NEW FILE########
__FILENAME__ = 0005_auto__chg_field_name_name
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Name.name'
        db.alter_column('mapit_name', 'name', self.gf('django.db.models.fields.CharField')(max_length=2000))

    def backwards(self, orm):

        # Changing field 'Name.name'
        db.alter_column('mapit_name', 'name', self.gf('django.db.models.fields.CharField')(max_length=100))

    models = {
        'mapit.area': {
            'Meta': {'ordering': "('name', 'type')", 'object_name': 'Area'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'blank': 'True', 'null': 'True', 'to': "orm['mapit.Country']"}),
            'generation_high': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'final_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'generation_low': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'parent_area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'blank': 'True', 'null': 'True', 'to': "orm['mapit.Area']"}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'to': "orm['mapit.Type']"})
        },
        'mapit.code': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Code'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': "orm['mapit.Area']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': "orm['mapit.CodeType']"})
        },
        'mapit.codetype': {
            'Meta': {'object_name': 'CodeType'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '1', 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'unique': 'True'})
        },
        'mapit.generation': {
            'Meta': {'object_name': 'Generation'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.geometry': {
            'Meta': {'object_name': 'Geometry'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polygons'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polygon': ('django.contrib.gis.db.models.fields.PolygonField', [], {'srid': str(settings.MAPIT_AREA_SRID)})
        },
        'mapit.name': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Name'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': "orm['mapit.NameType']"})
        },
        'mapit.nametype': {
            'Meta': {'object_name': 'NameType'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.postcode': {
            'Meta': {'ordering': "('postcode',)", 'object_name': 'Postcode'},
            'areas': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'postcodes'", 'blank': 'True', 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True'}),
            'postcode': ('django.db.models.fields.CharField', [], {'max_length': '7', 'unique': 'True', 'db_index': 'True'})
        },
        'mapit.type': {
            'Meta': {'object_name': 'Type'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '3', 'unique': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['mapit']

########NEW FILE########
__FILENAME__ = 0006_code_code_increase_max_length
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Code.code'
        db.alter_column('mapit_code', 'code', self.gf('django.db.models.fields.CharField')(max_length=500))

    def backwards(self, orm):

        # Changing field 'Code.code'
        db.alter_column('mapit_code', 'code', self.gf('django.db.models.fields.CharField')(max_length=10))

    models = {
        'mapit.area': {
            'Meta': {'ordering': "('name', 'type')", 'object_name': 'Area'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'areas'", 'null': 'True', 'to': "orm['mapit.Country']"}),
            'generation_high': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'final_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'generation_low': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'parent_area': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['mapit.Area']"}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'to': "orm['mapit.Type']"})
        },
        'mapit.code': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Code'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': "orm['mapit.Area']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': "orm['mapit.CodeType']"})
        },
        'mapit.codetype': {
            'Meta': {'object_name': 'CodeType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '1'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'mapit.generation': {
            'Meta': {'object_name': 'Generation'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.geometry': {
            'Meta': {'object_name': 'Geometry'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polygons'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polygon': ('django.contrib.gis.db.models.fields.PolygonField', [], {'srid': str(settings.MAPIT_AREA_SRID)})
        },
        'mapit.name': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Name'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': "orm['mapit.NameType']"})
        },
        'mapit.nametype': {
            'Meta': {'object_name': 'NameType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.postcode': {
            'Meta': {'ordering': "('postcode',)", 'object_name': 'Postcode'},
            'areas': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'postcodes'", 'blank': 'True', 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True'}),
            'postcode': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '7', 'db_index': 'True'})
        },
        'mapit.type': {
            'Meta': {'object_name': 'Type'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['mapit']

########NEW FILE########
__FILENAME__ = 0007_auto__chg_field_country_code
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Country.code'
        db.alter_column(u'mapit_country', 'code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=3))

    def backwards(self, orm):

        # Changing field 'Country.code'
        db.alter_column(u'mapit_country', 'code', self.gf('django.db.models.fields.CharField')(max_length=1, unique=True))

    models = {
        u'mapit.area': {
            'Meta': {'ordering': "('name', 'type')", 'object_name': 'Area'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'areas'", 'null': 'True', 'to': u"orm['mapit.Country']"}),
            'generation_high': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'final_areas'", 'null': 'True', 'to': u"orm['mapit.Generation']"}),
            'generation_low': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_areas'", 'null': 'True', 'to': u"orm['mapit.Generation']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'parent_area': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': u"orm['mapit.Area']"}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'to': u"orm['mapit.Type']"})
        },
        u'mapit.code': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Code'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': u"orm['mapit.Area']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': u"orm['mapit.CodeType']"})
        },
        u'mapit.codetype': {
            'Meta': {'object_name': 'CodeType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'mapit.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'mapit.generation': {
            'Meta': {'object_name': 'Generation'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'mapit.geometry': {
            'Meta': {'object_name': 'Geometry'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polygons'", 'to': u"orm['mapit.Area']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polygon': ('django.contrib.gis.db.models.fields.PolygonField', [], {'srid': str(settings.MAPIT_AREA_SRID)})
        },
        u'mapit.name': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Name'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': u"orm['mapit.Area']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': u"orm['mapit.NameType']"})
        },
        u'mapit.nametype': {
            'Meta': {'object_name': 'NameType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'mapit.postcode': {
            'Meta': {'ordering': "('postcode',)", 'object_name': 'Postcode'},
            'areas': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'postcodes'", 'blank': 'True', 'to': u"orm['mapit.Area']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True'}),
            'postcode': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '7', 'db_index': 'True'})
        },
        u'mapit.type': {
            'Meta': {'object_name': 'Type'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['mapit']

########NEW FILE########
__FILENAME__ = 0008_auto__chg_field_area_name
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Area.name'
        db.alter_column(u'mapit_area', 'name', self.gf('django.db.models.fields.CharField')(max_length=2000))

    def backwards(self, orm):

        # Changing field 'Area.name'
        db.alter_column(u'mapit_area', 'name', self.gf('django.db.models.fields.CharField')(max_length=100))

    models = {
        u'mapit.area': {
            'Meta': {'ordering': "('name', 'type')", 'object_name': 'Area'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'areas'", 'null': 'True', 'to': u"orm['mapit.Country']"}),
            'generation_high': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'final_areas'", 'null': 'True', 'to': u"orm['mapit.Generation']"}),
            'generation_low': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_areas'", 'null': 'True', 'to': u"orm['mapit.Generation']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'blank': 'True'}),
            'parent_area': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': u"orm['mapit.Area']"}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'to': u"orm['mapit.Type']"})
        },
        u'mapit.code': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Code'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': u"orm['mapit.Area']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': u"orm['mapit.CodeType']"})
        },
        u'mapit.codetype': {
            'Meta': {'object_name': 'CodeType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'mapit.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'mapit.generation': {
            'Meta': {'object_name': 'Generation'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'mapit.geometry': {
            'Meta': {'object_name': 'Geometry'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polygons'", 'to': u"orm['mapit.Area']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polygon': ('django.contrib.gis.db.models.fields.PolygonField', [], {'srid': str(settings.MAPIT_AREA_SRID)})
        },
        u'mapit.name': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Name'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': u"orm['mapit.Area']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': u"orm['mapit.NameType']"})
        },
        u'mapit.nametype': {
            'Meta': {'object_name': 'NameType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'mapit.postcode': {
            'Meta': {'ordering': "('postcode',)", 'object_name': 'Postcode'},
            'areas': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'postcodes'", 'blank': 'True', 'to': u"orm['mapit.Area']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True'}),
            'postcode': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '7', 'db_index': 'True'})
        },
        u'mapit.type': {
            'Meta': {'object_name': 'Type'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['mapit']

########NEW FILE########
__FILENAME__ = 0009_auto__chg_field_type_code
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Type.code'
        db.alter_column(u'mapit_type', 'code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=500))

    def backwards(self, orm):

        # Changing field 'Type.code'
        db.alter_column(u'mapit_type', 'code', self.gf('django.db.models.fields.CharField')(max_length=3, unique=True))

    models = {
        u'mapit.area': {
            'Meta': {'ordering': "('name', 'type')", 'object_name': 'Area'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'areas'", 'null': 'True', 'to': u"orm['mapit.Country']"}),
            'generation_high': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'final_areas'", 'null': 'True', 'to': u"orm['mapit.Generation']"}),
            'generation_low': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_areas'", 'null': 'True', 'to': u"orm['mapit.Generation']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'blank': 'True'}),
            'parent_area': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': u"orm['mapit.Area']"}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'to': u"orm['mapit.Type']"})
        },
        u'mapit.code': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Code'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': u"orm['mapit.Area']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': u"orm['mapit.CodeType']"})
        },
        u'mapit.codetype': {
            'Meta': {'object_name': 'CodeType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'mapit.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'mapit.generation': {
            'Meta': {'object_name': 'Generation'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'mapit.geometry': {
            'Meta': {'object_name': 'Geometry'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polygons'", 'to': u"orm['mapit.Area']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polygon': ('django.contrib.gis.db.models.fields.PolygonField', [], {'srid': str(settings.MAPIT_AREA_SRID)})
        },
        u'mapit.name': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Name'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': u"orm['mapit.Area']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '2000'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': u"orm['mapit.NameType']"})
        },
        u'mapit.nametype': {
            'Meta': {'object_name': 'NameType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'mapit.postcode': {
            'Meta': {'ordering': "('postcode',)", 'object_name': 'Postcode'},
            'areas': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'postcodes'", 'blank': 'True', 'to': u"orm['mapit.Area']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True'}),
            'postcode': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '7', 'db_index': 'True'})
        },
        u'mapit.type': {
            'Meta': {'object_name': 'Type'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '500'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['mapit']

########NEW FILE########
__FILENAME__ = models
import re
import itertools

from django.contrib.gis.db import models
from django.contrib.gis.gdal import SRSException, OGRException
from django.conf import settings
from django.db import connection
from django.utils.html import escape

from mapit.managers import Manager, GeoManager
from mapit import countries
from mapit.djangopatch import NoValidateRawQuerySet

class GenerationManager(models.Manager):
    def current(self):
        """Return the most recent active generation.

        If there are no active generations, return 0."""

        latest_on = self.get_query_set().filter(active=True).order_by('-id')
        if latest_on: return latest_on[0]
        return 0

    def new(self):
        """If the most recent generation is inactive, return it.

        If there are no generations, or the most recent one is active,
        return None."""

        latest = self.get_query_set().order_by('-id')
        if not latest or latest[0].active:
            return None
        return latest[0]
        
class Generation(models.Model):

    # Generations are used so that, theoretically, old versions of the same
    # data can be stored and accessed when new versions (ie. boundary changes
    # of some sort) come along. The current generation is the most recent
    # active generation, and is the default for e.g. postcode and point
    # lookups (both can be overridden to a different generation with a query
    # parameter). Inactive generations are so that you can load in new data
    # without it being returned by normal lookups by everyone using mapit.
    # 
    # An Area in the database has a minimum and maximum generation that it is
    # valid for, so that you can see at which point an area was added and then
    # removed.
    # 
    # As an example, http://mapit.mysociety.org/postcode/EH11BB.html is the
    # current areas for that postcode, whilst
    # http://mapit.mysociety.org/postcode/EH11BB.html?generation=14 gives you
    # the areas before the last Scottish Parliament boundary changes, hence
    # giving you the different areas involved.
    # 
    # The concept works okay for boundary changes of things that have the
    # notion of being children - e.g. council wards, UK Parliament
    # constituencies, and so on - which are changed with a clean slate to a
    # new set (though note that if someone has some sort of alert on a ward
    # ID, that will stop at a point at which that ward ceases to exist, no
    # easy solution there). Where it falls down a bit is if the 'parent' has a
    # boundary change - users of mapit (including us) assume that e.g.
    # http://mapit.mysociety.org/area/2651.html is and always will be the City
    # of Edinburgh Council boundary. If the City of Edinburgh Council boundary
    # were to change, this should get a new ID starting at the new generation.
    # But that would break some things.
    # 
    # Another example, as I've just fixed #32, is
    # http://mapit.mysociety.org/area/2253/children.html?type=UTW vs
    # http://mapit.mysociety.org/area/2253/children.html?generation=14;type=UTW
    # - the wards of Bedford before and after a boundary change.

    active = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, help_text="Describe this generation, eg '2010 electoral boundaries'")

    objects = GenerationManager()

    def __unicode__(self):
        id = self.id or '?'
        return "Generation %s (%sactive)" % (id, "" if self.active else "in")

    def as_dict(self):
        return {
            'id': self.id,
            'active': self.active,
            'created': self.created,
            'description': self.description,
        }

class Country(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=100, unique=True)

    def __unicode__(self):
        return self.name
    
    class Meta:
        verbose_name_plural='countries'

class Type(models.Model):

    # An area type (the Type model) is the type of area. You can see examples
    # for a few countries in the mapit/fixtures directory. In the UK we have
    # county councils (CTY), district councils (DIS), constituencies of the UK
    # Parliament (WMC), Scottish Parliament regions (SPE), and so on. The fact
    # these examples are three letter codes is a hangover from the original
    # source data we used from Ordnance Survey.

    code = models.CharField(max_length=500, unique=True, help_text="A unique code, eg 'CTR', 'CON', etc")
    description = models.CharField(max_length=200, blank=True, help_text="The name of the type of area, eg 'Country', 'Constituency', etc")

    def __unicode__(self):
        return '%s (%s)' % (self.description, self.code)

class AreaManager(models.GeoManager):
    def get_query_set(self):
        return super(AreaManager, self).get_query_set().select_related('type', 'country')

    def by_location(self, location, generation=None):
        if generation is None: generation = Generation.objects.current()
        if not location: return []
        return Area.objects.filter(
            polygons__polygon__contains=location,
            generation_low__lte=generation, generation_high__gte=generation
        )

    def by_postcode(self, postcode, generation=None):
        if not generation: generation = Generation.objects.current()
        return list(itertools.chain(
            self.by_location(postcode.location, generation),
            postcode.areas.filter(
                generation_low__lte=generation, generation_high__gte=generation
            )
        ))

    # In order for this query to be performant, we have to do it ourselves.
    # We force the non-geographical part of the query to be done first, because
    # if a type is specified, that greatly speeds it up.
    def intersect(self, query_type, area, types, generation):
        if not isinstance(query_type, list): query_type = [ query_type ]

        params = [ area.id, area.id, generation.id, generation.id ]

        if types:
            params.append( tuple(types) )
            query_area_type = ' AND mapit_area.type_id IN (SELECT id FROM mapit_type WHERE code IN %s) '
        else:
            query_area_type = ''

        query_geo = ' OR '.join([ 'ST_%s(geometry.polygon, target.polygon)' % type for type in query_type ])

        query = '''
WITH
    target AS ( SELECT ST_collect(polygon) polygon FROM mapit_geometry WHERE area_id=%%s ),
    geometry AS (
        SELECT mapit_geometry.*
          FROM mapit_geometry, mapit_area, target
         WHERE mapit_geometry.area_id = mapit_area.id
               AND mapit_geometry.polygon && target.polygon
               AND mapit_area.id != %%s
               AND mapit_area.generation_low_id <= %%s
               AND mapit_area.generation_high_id >= %%s
               %s
    )
SELECT DISTINCT mapit_area.*
  FROM mapit_area, geometry, target
 WHERE geometry.area_id = mapit_area.id AND (%s)
''' % (query_area_type, query_geo)
        # Monkeypatched self.raw() here to prevent needless SQL validation (removed from Django 1.3)
        return NoValidateRawQuerySet(raw_query=query, model=self.model, params=params, using=self._db)

    def get_or_create_with_name(self, country=None, type=None, name_type='', name=''):
        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        area, created = Area.objects.get_or_create(country=country, type=type,
            generation_low__lte=current_generation, generation_high__gte=current_generation,
            names__type__code=name_type, names__name=name,
            defaults = { 'generation_low': new_generation, 'generation_high': new_generation }
        )
        if created:
            area.names.get_or_create(type=NameType.objects.get(code=name_type), name=name)
        else:
            area.generation_high = new_generation
            area.save()
        return area

    def get_or_create_with_code(self, country=None, type=None, code_type='', code=''):
        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        area, created = Area.objects.get_or_create(country=country, type=type,
            generation_low__lte=current_generation, generation_high__gte=current_generation,
            codes__type__code=code_type, codes__code=code,
            defaults = { 'generation_low': new_generation, 'generation_high': new_generation }
        )
        if created:
            area.codes.get_or_create(type=CodeType.objects.get(code=code_type), code=code)
        else:
            area.generation_high = new_generation
            area.save()
        return area

class TransformError(Exception):
    pass

class Area(models.Model):
    name = models.CharField(max_length=2000, editable=False, blank=True) # Automatically set from name children
    parent_area = models.ForeignKey('self', related_name='children', null=True, blank=True)
    type = models.ForeignKey(Type, related_name='areas')
    country = models.ForeignKey(Country, related_name='areas', null=True, blank=True)
    generation_low = models.ForeignKey(Generation, related_name='new_areas', null=True)
    generation_high = models.ForeignKey(Generation, related_name='final_areas', null=True)

    objects = AreaManager()

    class Meta:
        ordering = ('name', 'type')

    @property
    def all_codes(self):
        if not getattr(self, 'code_list', None):
            self.code_list = self.codes.select_related('type')
        codes = {}
        for code in self.code_list:
            codes[code.type.code] = code.code
        return codes

    def __unicode__(self):
        name = self.name or '(unknown)'
        return '%s %s' % (self.type.code, name)

    def as_dict(self, all_names=None):
        all_names = all_names or []
        return {
            'id': self.id,
            'name': self.name,
            'parent_area': self.parent_area_id,
            'type': self.type.code,
            'type_name': self.type.description,
            'country': self.country.code if self.country else '',
            'country_name': self.country.name if self.country else '-',
            'generation_low': self.generation_low_id,
            'generation_high': self.generation_high_id,
            'codes': self.all_codes,
            'all_names': dict(n.as_tuple() for n in all_names),
        }

    def css_indent_class(self):
        """Get a CSS class for use on <li> representations of this area

        Currently this is only used to indicate the indentation level
        that should be used on the code types O02, O03, O04 ... O011,
        which are only used by global MapIt.
        """
        m = re.search(r'^O([01][0-9])$', self.type.code)
        if m:
            level = int(m.group(1), 10)
            return "area_level_%d" % (level,)
        else:
            return ""

    def export(self,
               srid,
               export_format,
               simplify_tolerance=0,
               line_colour="70ff0000",
               fill_colour="3dff5500",
               kml_type="full"):
        """Generate a representation of the area in KML, GeoJSON or WKT

        This returns a tuple of (data, content_type), which are
        strings representing the data itself and its MIME type.  If
        there are no polygons associated with this area (None, None)
        is returned.  'export_format' may be one of 'kml', 'wkt,
        'json' and 'geojson', the last two being synonymous.  The
        'srid' parameter specifies the coordinate system that the
        polygons should be transformed into before being exported, if
        it is different from this MapIt.  simplify_tolerance, if
        non-zero, is passed to
        django.contrib.gis.geos.GEOSGeometry.simplify for simplifying
        the polygon boundary before export.  The line_colour and
        fill_colour parameters are only used if the export type is KML
        and kml_type is 'full'.  The 'kml_type' parameter may be
        either 'full' (in which case a complete, valid KML file is
        returned) or 'polygon' (in which case just the <Polygon>
        element is returned).

        If the simplify_tolerance provided is large enough that all
        the polygons completely disappear under simplification, or
        something else goes wrong with the spatial transform, then a
        TransformError exception is raised.
        """
        all_areas = self.polygons.all()
        if len(all_areas) > 1:
            all_areas = all_areas.collect()
        elif len(all_areas) == 1:
            all_areas = all_areas[0].polygon
        else:
            return (None, None)

        if srid != settings.MAPIT_AREA_SRID:
            try:
                all_areas.transform(srid)
            except (SRSException, OGRException) as e:
                raise TransformError, "Error with transform: %s" % e

        num_points_before_simplification = all_areas.num_points
        if simplify_tolerance:
            all_areas = all_areas.simplify(simplify_tolerance)
            if all_areas.num_points == 0 and num_points_before_simplification > 0:
                raise TransformError, "Simplifying %s with tolerance %f left no boundary at all" % (self, simplify_tolerance)

        if export_format=='kml':
            if kml_type == "polygon":
                out = all_areas.kml
            elif kml_type == "full":
                out = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
    <Document>
        <Style id="ourPolygonStyle">
            <LineStyle>
                <color>%s</color>
                <width>2</width>
            </LineStyle>
            <PolyStyle>
                <color>%s</color>
            </PolyStyle>
        </Style>
        <Placemark>
            <styleUrl>#ourPolygonStyle</styleUrl>
            <name>%s</name>
            %s
        </Placemark>
    </Document>
</kml>''' % (line_colour, fill_colour, escape(self.name), all_areas.kml)
            else:
                raise Exception, "Unknown kml_type: '%s'" % (kml_type,)
            content_type = 'application/vnd.google-earth.kml+xml'
        elif export_format in ('json', 'geojson'):
            out = all_areas.json
            content_type = 'application/json'
        elif export_format=='wkt':
            out = all_areas.wkt
            content_type = 'text/plain'
        return (out, content_type)

class Geometry(models.Model):
    area = models.ForeignKey(Area, related_name='polygons')
    polygon = models.PolygonField(srid=settings.MAPIT_AREA_SRID)
    objects = GeoManager()

    class Meta:
        verbose_name_plural = 'geometries'

    def __unicode__(self):
        return u'%s, polygon %d' % (self.area, self.id)

class NameType(models.Model):

    # Name types are for storing different types of names. This could have
    # different uses - in the UK it is used to store names from different
    # sources, and then one is picked for the canonical name on the Area model
    # itself; in global MaPit, the different language names are stored here
    # and displayed in the alternative names section.

    code = models.CharField(max_length=10, unique=True, help_text="A unique code to identify this type of name: eg 'english' or 'iso'")
    description = models.CharField(max_length=200, blank=True, help_text="The name of this type of name, eg 'English' or 'ISO Standard'")
    objects = Manager()

    def __unicode__(self):
        return '%s (%s)' % (self.description, self.code)

class Name(models.Model):
    area = models.ForeignKey(Area, related_name='names')
    type = models.ForeignKey(NameType, related_name='names')
    name = models.CharField(max_length=2000)
    objects = Manager()

    class Meta:
        unique_together = ('area', 'type')

    def __unicode__(self):
        return '%s (%s) [%s]' % (self.name, self.type.code, self.area.id)

    def make_friendly_name(self, name):
        n = re.sub('\s+', ' ', name.name.strip())
        n = n.replace('St. ', 'St ')
        if name.type.code == 'M': return n
        if name.type.code == 'S': return n
        # Type must be 'O' here
        n = re.sub(' Euro Region$', '', n) # EUR
        n = re.sub(' (Burgh|Co|Boro) Const$', '', n) # WMC
        n = re.sub(' P Const$', '', n) # SPC
        n = re.sub(' PER$', '', n) # SPE
        n = re.sub(' GL Assembly Const$', '', n) # LAC
        n = re.sub(' Assembly Const$', '', n) # WAC
        n = re.sub(' Assembly ER$', '', n) # WAE
        n = re.sub(' London Boro$', ' Borough', n) # LBO
        if self.area.country and self.area.country.name == 'Wales': n = re.sub('^.*? - ', '', n) # UTA
        n = re.sub('(?:The )?City of (.*?) (District )?\(B\)$', r'\1 City', n) # UTA
        n = re.sub(' District \(B\)$', ' Borough', n) # DIS
        n = re.sub(' \(B\)$', ' Borough', n) # DIS
        if self.area.type.code in ('CTY', 'DIS', 'LBO', 'UTA', 'MTD'): n += ' Council'
        n = re.sub(' (ED|CP)$', '', n) # CPC, CED, UTE
        n = re.sub(' Ward$', '', n) # DIW, LBW, MTW, UTW
        return n

    def save(self, *args, **kwargs):
        super(Name, self).save(*args, **kwargs)
        try:
            name = self.area.names.filter(type__code__in=('M', 'O', 'S')).order_by('type__code')[0]
            self.area.name = self.make_friendly_name(name)
            self.area.save()
        except:
            pass

    def as_tuple(self):
        return (self.type.code, [self.type.description,
                                 self.name])

class CodeType(models.Model):

    # Code types are so you can store different types of code for an area. In
    # the UK we have "ons" for old style Office of National Statistics codes,
    # "gss" for new style ONS codes, and unit_id for the Ordnance Survey ID.
    # This could be extended to a more generic data store of information on an
    # object, perhaps.

    code = models.CharField(max_length=10, unique=True, help_text="A unique code, eg 'ons' or 'unit_id'")
    description = models.CharField(max_length=200, blank=True, help_text="The name of the code, eg 'Office of National Statitics' or 'Ordnance Survey ID'")

    def __unicode__(self):
        return '%s (%s)' % (self.description, self.code)

class Code(models.Model):
    area = models.ForeignKey(Area, related_name='codes')
    type = models.ForeignKey(CodeType, related_name='codes')
    code = models.CharField(max_length=500)
    objects = Manager()

    class Meta:
        unique_together = ('area', 'type')

    def __unicode__(self):
        return '%s (%s) [%s]' % (self.code, self.type.code, self.area.id)

# Postcodes

class PostcodeManager(GeoManager):
    def get_query_set(self):
        return self.model.QuerySet(self.model)
    def __getattr__(self, attr, *args):
        return getattr(self.get_query_set(), attr, *args)

class Postcode(models.Model):
    postcode = models.CharField(max_length=7, db_index=True, unique=True)
    location = models.PointField(null=True)
    # Will hopefully use PostGIS point-in-polygon tests, but if we don't have the polygons...
    areas = models.ManyToManyField(Area, related_name='postcodes', blank=True)

    objects = PostcodeManager()

    class Meta:
        ordering = ('postcode',)

    class QuerySet(models.query.GeoQuerySet):
        # ST_CoveredBy on its own does not appear to use the index.
        # Plus this way we can keep the polygons in the database
        # without pulling out in a giant WKB string
        def filter_by_area(self, area):
            collect = 'ST_Transform((select ST_Collect(polygon) from mapit_geometry where area_id=%s group by area_id), 4326)'
            return self.extra(
                where = [
                    'location && %s' % collect,
                    'ST_CoveredBy(location, %s)' % collect
                ],
                params = [ area.id, area.id ]
            )

    def __unicode__(self):
        return self.get_postcode_display()

    # Prettify postcode for display, if we know how to
    def get_postcode_display(self):
        if hasattr(countries, 'get_postcode_display'):
            return countries.get_postcode_display(self.postcode)
        return self.postcode

    def as_dict(self):
        if not self.location:
            return {
                'postcode': self.get_postcode_display(),
            }
        loc = self.location
        result = {
            'postcode': self.get_postcode_display(),
            'wgs84_lon': loc[0],
            'wgs84_lat': loc[1]
        }
        if hasattr(countries, 'augment_postcode'):
            countries.augment_postcode(self, result)
        return result

    # Doing this via self.location.transform(29902) gives incorrect results.
    # The database has the right proj4 text, the proj file does not. I think.
    def as_irish_grid(self):
        cursor = connection.cursor()
        cursor.execute("SELECT ST_AsText(ST_Transform(ST_GeomFromText('POINT(%f %f)', 4326), 29902))" % (self.location[0], self.location[1]))
        row = cursor.fetchone()
        m = re.match('POINT\((.*?) (.*)\)', row[0])
        return map(float, m.groups())


########NEW FILE########
__FILENAME__ = ratelimitcache
from datetime import datetime, timedelta
import functools, hashlib

from django.http import HttpResponseForbidden
from django.core.cache import cache
from django.conf import settings

class ratelimit(object):
    "Instances of this class can be used as decorators"
    # This class is designed to be sub-classed
    minutes = 2 # The time period
    requests = 20 # Number of allowed requests in that time period
    # IP addresses or user agents that aren't rate limited
    excluded = settings.MAPIT_RATE_LIMIT
    
    prefix = 'rl-' # Prefix for memcache key
    
    def __init__(self, **options):
        for key, value in options.items():
            setattr(self, key, value)
    
    def __call__(self, fn):
        def wrapper(request, *args, **kwargs):
            return self.view_wrapper(request, fn, *args, **kwargs)
        functools.update_wrapper(wrapper, fn)
        return wrapper
    
    def view_wrapper(self, request, fn, *args, **kwargs):
        if not self.should_ratelimit(request):
            return fn(request, *args, **kwargs)
        
        if request.META.get('REMOTE_ADDR', '') in self.excluded or \
            ( '/' in request.META.get('HTTP_USER_AGENT', '') and request.META.get('HTTP_USER_AGENT', '') in self.excluded ):
            return fn(request, *args, **kwargs)

        # If we're using the DummyCache backend then no data will
        # actually be stored in the cache, and as a result cache.incr
        # for a key will fail even immediately after cache.add.
        cache_backend = settings.CACHES['default']['BACKEND']
        if cache_backend == 'django.core.cache.backends.dummy.DummyCache':
            return fn(request, *args, **kwargs)

        counts = self.get_counters(request).values()
        
        # Increment rate limiting counter
        self.cache_incr(self.current_key(request))
        
        # Have they failed?
        if sum(int(c) for c in counts) >= self.requests:
            return self.disallowed(request)
        
        return fn(request, *args, **kwargs)
    
    def cache_get_many(self, keys):
        return cache.get_many(keys)
    
    def cache_incr(self, key):
        try:
            cache.incr(key)
        except ValueError:
            cache.add(key, '0', self.expire_after())
            cache.incr(key)
    
    def should_ratelimit(self, request):
        return len(settings.MAPIT_RATE_LIMIT)
    
    def get_counters(self, request):
        return self.cache_get_many(self.keys_to_check(request))
    
    def keys_to_check(self, request):
        extra = self.key_extra(request)
        now = datetime.now()
        return [
            '%s%s-%s' % (
                self.prefix,
                extra,
                (now - timedelta(minutes = minute)).strftime('%Y%m%d%H%M')
            ) for minute in range(self.minutes + 1)
        ]
    
    def current_key(self, request):
        return '%s%s-%s' % (
            self.prefix,
            self.key_extra(request),
            datetime.now().strftime('%Y%m%d%H%M')
        )
    
    def key_extra(self, request):
        # By default, their IP address is used
        return request.META.get('REMOTE_ADDR', '')
    
    def disallowed(self, request):
        "Over-ride this method if you want to log incidents"
        return HttpResponseForbidden('Rate limit exceeded')
    
    def expire_after(self):
        "Used for setting the memcached cache expiry"
        return (self.minutes + 1) * 60

class ratelimit_post(ratelimit):
    "Rate limit POSTs - can be used to protect a login form"
    key_field = None # If provided, this POST var will affect the rate limit
    
    def should_ratelimit(self, request):
        return request.method == 'POST'
    
    def key_extra(self, request):
        # IP address and key_field (if it is set)
        extra = super(ratelimit_post, self).key_extra(request)
        if self.key_field:
            value = hashlib.sha1(request.POST.get(self.key_field, '')).hexdigest()
            extra += '-' + value
        return extra


########NEW FILE########
__FILENAME__ = shortcuts
import json
import re
import django
from django import http
from django.db import connection
from django.conf import settings
from django.shortcuts import get_object_or_404 as orig_get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext

from django.core.serializers.json import DjangoJSONEncoder
# Assuming at least python 2.6, in Django < 1.6, the above class is either a
# packaged simplejson subclass if simplejson is installed, or a core json
# subclass. In Django >= 1.6, it is always a core json subclass. The json.dump
# call in this file needs to be the same thing that the above class is.
if django.get_version() < '1.6':
    try:
        import simplejson
        if issubclass(DjangoJSONEncoder, simplejson.JSONEncoder):
            import simplejson as json
    except:
        pass

class GEOS_JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        try:
            return o.json # Will therefore support all the GEOS objects
        except:
            pass
        return super(GEOS_JSONEncoder, self).default(o)

def render(request, template_name, context=None):
    if context is None: context = {}
#    context['base'] = base or 'base.html'
#    context['connection'] = connection
    return render_to_response(
        template_name, context, context_instance = RequestContext(request)
    )

def sorted_areas(areas):
    # In here to prevent a circular dependency
    from mapit import countries
    if hasattr(countries, 'sorted_areas'):
        return countries.sorted_areas(areas)
    return list(areas)

def output_html(request, title, areas, **kwargs):
    kwargs['json_url'] = request.path.replace('.html', '')
    kwargs['title'] = title
    kwargs['areas'] = sorted_areas(areas)
    kwargs['indent_areas'] = kwargs.get('indent_areas', False)
    return render(request, 'mapit/data.html', kwargs)

def output_json(out, code=200):
    types = {
        400: http.HttpResponseBadRequest,
        404: http.HttpResponseNotFound,
        500: http.HttpResponseServerError,
    }
    response_type = types.get(code, http.HttpResponse)
    response = response_type(content_type='application/json; charset=utf-8')
    response['Access-Control-Allow-Origin'] = '*'
    response['Cache-Control'] = 'max-age=2419200' # 4 weeks
    if code != 200:
        out['code'] = code
    indent = None
    if settings.DEBUG:
        if isinstance(out, dict):
            out['debug_db_queries'] = connection.queries
        indent = 4
    json.dump(out, response, ensure_ascii=False, cls=GEOS_JSONEncoder, indent=indent)
    return response

def get_object_or_404(klass, format='json', *args, **kwargs):
    try:
        return orig_get_object_or_404(klass, *args, **kwargs)
    except http.Http404, e:
        from mapit.middleware import ViewException
        raise ViewException(format, str(e), 404)

def json_500(request):
    return output_json({ 'error': "Sorry, something's gone wrong." }, code=500)

def set_timeout(format):
    cursor = connection.cursor()
    timeout = 10000 if format == 'html' else 10000
    cursor.execute('set session statement_timeout=%d' % timeout)


########NEW FILE########
__FILENAME__ = tests
import json

from django.test import TestCase
from django.contrib.gis.geos import Polygon

from mapit.models import Type, Area, Geometry, Generation

class AreaViewsTest(TestCase):
    @classmethod
    def setUpClass(self):
        self.generation = Generation.objects.create(
            active=True,
            description="Test generation",
            )

        self.big_type = Type.objects.create(
            code="BIG",
            description="A large test area",
            )
        
        self.small_type = Type.objects.create(
            code="SML",
            description="A small test area",
            )

        self.big_area = Area.objects.create(
            name="Big Area",
            type=self.big_type,
            generation_low=self.generation,
            generation_high=self.generation,
            )

        self.big_shape = Geometry.objects.create(
            area=self.big_area,
            polygon=Polygon(((-5, 50), (-5, 55), (1, 55), (1, 50), (-5, 50))),
            )

        self.small_area_1 = Area.objects.create(
            name="Small Area 1",
            type=self.small_type,
            generation_low=self.generation,
            generation_high=self.generation,
            )

        self.small_area_2 = Area.objects.create(
            name="Small Area 2",
            type=self.small_type,
            generation_low=self.generation,
            generation_high=self.generation,
            )

        self.small_shape_1 = Geometry.objects.create(
            area=self.small_area_1,
            polygon=Polygon(((-4, 51), (-4, 52), (-3, 52), (-3, 51), (-4, 51))),
            )

        self.small_shape_2 = Geometry.objects.create(
            area=self.small_area_2,
            polygon=Polygon(((-3, 51), (-3, 52), (-2, 52), (-2, 51), (-3, 51))),
            )

    def test_areas_by_latlon(self):
        response = self.client.get('/point/latlon/51.5,-3.5.json')
        self.assertRedirects(response, '/point/4326/-3.5,51.5.json')

    def test_areas_by_point(self):
        # Different co-ords to evade any caching
        response = self.client.get('/point/4326/-3.4,51.5.json')

        content = json.loads(response.content)

        self.assertEqual(
            set((int(x) for x in content.keys())),
            set((x.id for x in (self.big_area, self.small_area_1)))
            )

    def test_front_page(self):
        response = self.client.get('/')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns

from mapit.shortcuts import render

handler500 = 'mapit.shortcuts.json_500'

format_end = '(?:\.(?P<format>html|json))?'

urlpatterns = patterns('',
    (r'^$', render, { 'template_name': 'mapit/index.html' }, 'mapit_index' ),
    (r'^licensing$', render, { 'template_name': 'mapit/licensing.html' } ),
    (r'^overview$', render, { 'template_name': 'mapit/overview.html' } ),

    (r'^generations$', 'mapit.views.areas.generations'),

    (r'^postcode/$', 'mapit.views.postcodes.form_submitted'),
    (r'^postcode/(?P<postcode>[A-Za-z0-9 +]+)%s$' % format_end, 'mapit.views.postcodes.postcode'),
    (r'^postcode/partial/(?P<postcode>[A-Za-z0-9 ]+)%s$' % format_end, 'mapit.views.postcodes.partial_postcode'),

    (r'^area/(?P<area_id>[0-9A-Z]+)%s$' % format_end, 'mapit.views.areas.area'),
    (r'^area/(?P<area_id>[0-9]+)/example_postcode%s$' % format_end, 'mapit.views.postcodes.example_postcode_for_area'),
    (r'^area/(?P<area_id>[0-9]+)/children%s$' % format_end, 'mapit.views.areas.area_children'),
    (r'^area/(?P<area_id>[0-9]+)/geometry$', 'mapit.views.areas.area_geometry'),
    (r'^area/(?P<area_id>[0-9]+)/touches%s$' % format_end, 'mapit.views.areas.area_touches'),
    (r'^area/(?P<area_id>[0-9]+)/overlaps%s$' % format_end, 'mapit.views.areas.area_overlaps'),
    (r'^area/(?P<area_id>[0-9]+)/covers%s$' % format_end, 'mapit.views.areas.area_covers'),
    (r'^area/(?P<area_id>[0-9]+)/covered%s$' % format_end, 'mapit.views.areas.area_covered'),
    (r'^area/(?P<area_id>[0-9]+)/coverlaps%s$' % format_end, 'mapit.views.areas.area_coverlaps'),
    (r'^area/(?P<area_id>[0-9]+)/intersects%s$' % format_end, 'mapit.views.areas.area_intersects'),
    (r'^area/(?P<area_id>[0-9A-Z]+)\.(?P<format>kml|geojson|wkt)$', 'mapit.views.areas.area_polygon'),
    (r'^area/(?P<srid>[0-9]+)/(?P<area_id>[0-9]+)\.(?P<format>kml|json|geojson|wkt)$', 'mapit.views.areas.area_polygon'),

    (r'^point/$', 'mapit.views.areas.point_form_submitted'),
    (r'^point/(?P<srid>[0-9]+)/(?P<x>[0-9.-]+),(?P<y>[0-9.-]+)(?:/(?P<bb>box))?%s$' % format_end, 'mapit.views.areas.areas_by_point'),
    (r'^point/latlon/(?P<lat>[0-9.-]+),(?P<lon>[0-9.-]+)(?:/(?P<bb>box))?%s$' % format_end, 'mapit.views.areas.areas_by_point_latlon'),
    (r'^point/osgb/(?P<e>[0-9.-]+),(?P<n>[0-9.-]+)(?:/(?P<bb>box))?%s$' % format_end, 'mapit.views.areas.areas_by_point_osgb'),

    (r'^nearest/(?P<srid>[0-9]+)/(?P<x>[0-9.-]+),(?P<y>[0-9.-]+)%s$' % format_end, 'mapit.views.postcodes.nearest'),

    (r'^areas/(?P<area_ids>[0-9,]*[0-9]+)%s$' % format_end, 'mapit.views.areas.areas'),
    (r'^areas/(?P<area_ids>[0-9,]*[0-9]+)/geometry$', 'mapit.views.areas.areas_geometry'),
    (r'^areas/(?P<type>[A-Z0-9,]*[A-Z0-9]+)%s$' % format_end, 'mapit.views.areas.areas_by_type'),
    (r'^areas/(?P<name>.+?)%s$' % format_end, 'mapit.views.areas.areas_by_name'),
    (r'^areas$', 'mapit.views.areas.deal_with_POST', { 'call': 'areas' }),
    (r'^code/(?P<code_type>[^/]+)/(?P<code_value>[^/]+?)%s$' % format_end, 'mapit.views.areas.area_from_code'),
)

########NEW FILE########
__FILENAME__ = utils
import re
from django.conf import settings

from mapit import countries

def is_valid_postcode(pc):
    pc = re.sub('\s+', '', pc.upper())

    if hasattr(countries, 'is_valid_postcode'):
        return countries.is_valid_postcode(pc)
    return False

def is_valid_partial_postcode(pc):
    pc = re.sub('\s+', '', pc.upper())

    if hasattr(countries, 'is_valid_partial_postcode'):
        return countries.is_valid_partial_postcode(pc)
    return False

########NEW FILE########
__FILENAME__ = areas
import re
import operator
from psycopg2.extensions import QueryCanceledError
from psycopg2 import InternalError
try:
    from django.db.utils import DatabaseError
except:
    from psycopg2 import DatabaseError
from osgeo import gdal

from django.contrib.gis.geos import Point
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import resolve, reverse
from django.db.models import Q
from django.conf import settings
from django.shortcuts import redirect

from mapit.models import Area, Generation, Geometry, Code, Name, TransformError
from mapit.shortcuts import output_json, output_html, render, get_object_or_404, set_timeout
from mapit.middleware import ViewException
from mapit.ratelimitcache import ratelimit
from mapit import countries

def generations(request):
    generations = Generation.objects.all()
    return output_json( dict( (g.id, g.as_dict() ) for g in generations ) )

@ratelimit(minutes=3, requests=100)
def area(request, area_id, format='json'):
    if hasattr(countries, 'area_code_lookup'):
        resp = countries.area_code_lookup(request, area_id, format)
        if resp: return resp


    if not re.match('\d+$', area_id):
        raise ViewException(format, 'Bad area ID specified', 400)


    area = get_object_or_404(Area, format=format, id=area_id)

    codes = []
    for code_type, code in sorted(area.all_codes.items()):
        code_link = None
        if code_type in ('osm', 'osm_rel'):
            code_link = 'http://www.openstreetmap.org/browse/relation/' + code
        elif code_type == 'osm_way':
            code_link = 'http://www.openstreetmap.org/browse/way/' + code
        codes.append((code_type, code, code_link))

    # Sort any alternative names by the description of the name (the
    # English name of the language for global MapIt) and exclude the
    # default OSM name, since if that exists, it'll already be
    # displayed as the page title.

    names = Name.objects.filter(area=area).select_related()
    alternative_names = sorted((n.type.description, n.name) for n in names
                               if n.type.code != "default")

    geotype = {}
    if hasattr(countries, 'restrict_geo_html'):
        geotype = countries.restrict_geo_html(area)

    if format == 'html':
        return render(request, 'mapit/area.html', {
            'area': area,
            'codes': codes,
            'alternative_names': alternative_names,
            'geotype': geotype,
        })
    return output_json( area.as_dict(names) )

@ratelimit(minutes=3, requests=100)
def area_polygon(request, srid='', area_id='', format='kml'):
    if not srid and hasattr(countries, 'area_code_lookup'):
        resp = countries.area_code_lookup(request, area_id, format)
        if resp: return resp

    if not re.match('\d+$', area_id):
        raise ViewException(format, 'Bad area ID specified', 400)

    if not srid:
        srid = 4326 if format in ('kml', 'json', 'geojson') else settings.MAPIT_AREA_SRID
    srid = int(srid)

    area = get_object_or_404(Area, id=area_id)

    try:
        simplify_tolerance = float(request.GET.get('simplify_tolerance', 0))
    except ValueError:
        raise ViewException(format, 'Badly specified tolerance', 400)

    try:
        output, content_type = area.export(srid, format, simplify_tolerance=simplify_tolerance)
        if output is None:
            return output_json({'error': 'No polygons found'}, code=404)
    except TransformError as e:
        return output_json({ 'error': e.args[0] }, code=400)

    response = HttpResponse(content_type='%s; charset=utf-8' % content_type)
    response['Access-Control-Allow-Origin'] = '*'
    response['Cache-Control'] = 'max-age=2419200' # 4 weeks
    response.write(output)
    return response
    
@ratelimit(minutes=3, requests=100)
def area_children(request, area_id, format='json'):
    area = get_object_or_404(Area, format=format, id=area_id)

    generation = request.REQUEST.get('generation', Generation.objects.current())
    if not generation: generation = Generation.objects.current()
    args = {
        'generation_low__lte': generation,
        'generation_high__gte': generation,
    }

    type = request.REQUEST.get('type', '')
    if ',' in type:
        args['type__code__in'] = type.split(',')
    elif type:
        args['type__code'] = type

    children = add_codes(area.children.filter(**args))

    if format == 'html': return output_html(request, 'Children of %s' % area.name, children)
    return output_json( dict( (child.id, child.as_dict() ) for child in children ) )

def area_intersect(query_type, title, request, area_id, format):
    area = get_object_or_404(Area, format=format, id=area_id)
    if not area.polygons.count():
        raise ViewException(format, 'No polygons found', 404)

    generation = Generation.objects.current()
    types = filter( None, request.REQUEST.get('type', '').split(',') )

    set_timeout(format)
    try:
        # Cast to list so that it's evaluated here, and add_codes doesn't get
        # confused with a RawQuerySet
        areas = list(Area.objects.intersect(query_type, area, types, generation))
        areas = add_codes(areas)
    except QueryCanceledError:
        raise ViewException(format, 'That query was taking too long to compute - try restricting to a specific type, if you weren\'t already doing so.', 500)
    except DatabaseError, e:
        # Django 1.2+ catches QueryCanceledError and throws its own DatabaseError instead
        if 'canceling statement due to statement timeout' not in e.args[0]: raise
        raise ViewException(format, 'That query was taking too long to compute - try restricting to a specific type, if you weren\'t already doing so.', 500)
    except InternalError:
        raise ViewException(format, 'There was an internal error performing that query.', 500)

    if format == 'html':
        return output_html(request,
            title % ('<a href="%sarea/%d.html">%s</a>' % (reverse('mapit_index'), area.id, area.name)),
            areas, norobots=True
        )
    return output_json( dict( (a.id, a.as_dict() ) for a in areas ) )

@ratelimit(minutes=3, requests=100)
def area_touches(request, area_id, format='json'):
    return area_intersect('touches', 'Areas touching %s', request, area_id, format)

@ratelimit(minutes=3, requests=100)
def area_overlaps(request, area_id, format='json'):
    return area_intersect('overlaps', 'Areas overlapping %s', request, area_id, format)

@ratelimit(minutes=3, requests=100)
def area_covers(request, area_id, format='json'):
    return area_intersect('coveredby', 'Areas covered by %s', request, area_id, format)

@ratelimit(minutes=3, requests=100)
def area_coverlaps(request, area_id, format='json'):
    return area_intersect(['overlaps', 'coveredby'], 'Areas covered by or overlapping %s', request, area_id, format)

@ratelimit(minutes=3, requests=100)
def area_covered(request, area_id, format='json'):
    return area_intersect('covers', 'Areas that cover %s', request, area_id, format)

@ratelimit(minutes=3, requests=100)
def area_intersects(request, area_id, format='json'):
    return area_intersect('intersects', 'Areas that intersect %s', request, area_id, format)

def add_codes(areas):
    codes = Code.objects.select_related('type').filter(area__in=areas)
    lookup = {}
    for code in codes:
        lookup.setdefault(code.area_id, []).append(code)
    for area in areas:
        if area.id in lookup:
            area.code_list = lookup[area.id]
    return areas

@ratelimit(minutes=3, requests=100)
def areas(request, area_ids, format='json'):
    area_ids = area_ids.split(',')
    areas = add_codes(Area.objects.filter(id__in=area_ids))
    if format == 'html': return output_html(request, 'Areas ID lookup', areas)
    return output_json( dict( ( area.id, area.as_dict() ) for area in areas ) )

@ratelimit(minutes=3, requests=100)
def areas_by_type(request, type, format='json'):
    generation = request.REQUEST.get('generation', Generation.objects.current())
    if not generation: generation = Generation.objects.current()

    try:
        min_generation = int(request.REQUEST['min_generation'])
    except:
        min_generation = generation

    args = {}
    if ',' in type:
        args['type__code__in'] = type.split(',')
    elif type:
        args['type__code'] = type

    if min_generation == -1:
        areas = add_codes(Area.objects.filter(**args))
    else:
        args['generation_low__lte'] = generation
        args['generation_high__gte'] = min_generation
        areas = add_codes(Area.objects.filter(**args))
    if format == 'html':
        return output_html(request, 'Areas in %s' % type, areas)
    return output_json( dict( (a.id, a.as_dict() ) for a in areas ) )

@ratelimit(minutes=3, requests=100)
def areas_by_name(request, name, format='json'):
    generation = request.REQUEST.get('generation', Generation.objects.current())
    if not generation: generation = Generation.objects.current()

    try:
        min_generation = int(request.REQUEST['min_generation'])
    except:
        min_generation = generation

    type = request.REQUEST.get('type', '')

    args = {
        'name__istartswith': name,
        'generation_low__lte': generation,
        'generation_high__gte': min_generation,
    }
    if ',' in type:
        args['type__code__in'] = type.split(',')
    elif type:
        args['type__code'] = type

    areas = add_codes(Area.objects.filter(**args))
    if format == 'html': return output_html(request, 'Areas starting with %s' % name, areas)
    out = dict( ( area.id, area.as_dict() ) for area in areas )
    return output_json(out)

@ratelimit(minutes=3, requests=100)
def area_geometry(request, area_id):
    area = _area_geometry(area_id)
    if isinstance(area, HttpResponse): return area
    return output_json(area)

def _area_geometry(area_id):
    area = get_object_or_404(Area, id=area_id)
    all_areas = area.polygons.all().collect()
    if not all_areas:
        return output_json({ 'error': 'No polygons found' }, code=404)
    out = {
        'parts': all_areas.num_geom,
    }
    if settings.MAPIT_AREA_SRID != 4326:
        out['srid_en'] = settings.MAPIT_AREA_SRID
        out['area'] = all_areas.area
        out['min_e'], out['min_n'], out['max_e'], out['max_n'] = all_areas.extent
        out['centre_e'], out['centre_n'] = all_areas.centroid
        all_areas.transform(4326)
        out['min_lon'], out['min_lat'], out['max_lon'], out['max_lat'] = all_areas.extent
        out['centre_lon'], out['centre_lat'] = all_areas.centroid
    else:
        out['min_lon'], out['min_lat'], out['max_lon'], out['max_lat'] = all_areas.extent
        out['centre_lon'], out['centre_lat'] = all_areas.centroid
        if hasattr(countries, 'area_geometry_srid'):
            srid = countries.area_geometry_srid
            all_areas.transform(srid)
            out['srid_en'] = srid
            out['area'] = all_areas.area
            out['min_e'], out['min_n'], out['max_e'], out['max_n'] = all_areas.extent
            out['centre_e'], out['centre_n'] = all_areas.centroid
    return out

@ratelimit(minutes=3, requests=100)
def areas_geometry(request, area_ids):
    area_ids = area_ids.split(',')
    out = {}
    for id in area_ids:
        area = _area_geometry(id)
        if isinstance(area, HttpResponse):
            area = {}
        out[id] = area
    return output_json(out)

@ratelimit(minutes=3, requests=100)
def area_from_code(request, code_type, code_value, format='json'):
    generation = request.REQUEST.get('generation',
                                     Generation.objects.current())
    if not generation:
        generation = Generation.objects.current()
    try:
        area = Area.objects.get(codes__type__code=code_type,
                                codes__code=code_value,
                                generation_low__lte=generation,
                                generation_high__gte=generation)
    except Area.DoesNotExist, e:
        message = 'No areas were found that matched code %s = %s.' % (code_type, code_value)
        raise ViewException(format, message, 404)
    except Area.MultipleObjectsReturned, e:
        message = 'There were multiple areas that matched code %s = %s.' % (code_type, code_value)
        raise ViewException(format, message, 500)
    return HttpResponseRedirect("/area/%d%s" % (area.id, '.%s' % format if format else ''))

@ratelimit(minutes=3, requests=100)
def areas_by_point(request, srid, x, y, bb=False, format='json'):
    type = request.REQUEST.get('type', '')
    generation = request.REQUEST.get('generation', Generation.objects.current())
    if not generation: generation = Generation.objects.current()

    location = Point(float(x), float(y), srid=int(srid))
    gdal.UseExceptions()
    try:
        location.transform(settings.MAPIT_AREA_SRID, clone=True)
    except:
        raise ViewException(format, 'Point outside the area geometry', 400)

    method = 'box' if bb and bb != 'polygon' else 'polygon'

    args = { 'generation_low__lte': generation, 'generation_high__gte': generation }

    if ',' in type:
        args['type__code__in'] = type.split(',')
    elif type:
        args['type__code'] = type

    if type and method == 'polygon':
        args = dict( ("area__%s" % k, v) for k, v in args.items() )
        # So this is odd. It doesn't matter if you specify types, PostGIS will
        # do the contains test on all the geometries matching the bounding-box
        # index, even if it could be much quicker to filter some out first
        # (ie. the EUR ones).
        args['polygon__bbcontains'] = location
        shapes = Geometry.objects.filter(**args).defer('polygon')
        areas = []
        for shape in shapes:
            try:
                areas.append( Area.objects.get(polygons__id=shape.id, polygons__polygon__contains=location) )
            except:
                pass
    else:
        if method == 'box':
            args['polygons__polygon__bbcontains'] = location
        else:
            geoms = list(Geometry.objects.filter(polygon__contains=location).defer('polygon'))
            args['polygons__in'] = geoms
        areas = Area.objects.filter(**args)

    areas = add_codes(areas)
    if format == 'html': return output_html(request, 'Areas covering the point (%s,%s)' % (x,y), areas, indent_areas=True)
    return output_json( dict( (area.id, area.as_dict() ) for area in areas ) )

@ratelimit(minutes=3, requests=100)
def areas_by_point_latlon(request, lat, lon, bb=False, format=''):
    return HttpResponseRedirect("/point/4326/%s,%s%s%s" % (lon, lat, "/box" if bb else '', '.%s' % format if format else ''))

@ratelimit(minutes=3, requests=100)
def areas_by_point_osgb(request, e, n, bb=False, format=''):
    return HttpResponseRedirect("/point/27700/%s,%s%s%s" % (e, n, "/box" if bb else '', '.%s' % format if format else ''))

def point_form_submitted(request):
    latlon = request.POST.get('pc', None)
    if not request.method == 'POST' or not latlon:
        return redirect('/')
    m = re.match('\s*([0-9.-]+)\s*,\s*([0-9.-]+)', latlon)
    if not m:
        return redirect('/')
    lat, lon = m.groups()
    return redirect('mapit.views.areas.areas_by_point',
        srid=4326, x=lon, y=lat, format='html'
    )

# ---

def deal_with_POST(request, call='areas'):
    url = request.POST.get('URL', '')
    if not url:
        return output_json({ 'error': 'No content specified' }, code=400)
    view, args, kwargs = resolve('/%s/%s' % (call, url))
    kwargs['request'] = request
    return view(*args, **kwargs)


########NEW FILE########
__FILENAME__ = postcodes
import re
import itertools
from psycopg2.extensions import QueryCanceledError
try:
    from django.db.utils import DatabaseError
except:
    from psycopg2 import DatabaseError

from django.template import loader
from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

from mapit.models import Postcode, Area, Generation
from mapit.utils import is_valid_postcode, is_valid_partial_postcode
from mapit.shortcuts import output_json, get_object_or_404, set_timeout, render
from mapit.middleware import ViewException
from mapit.ratelimitcache import ratelimit
from mapit.views.areas import add_codes
from mapit import countries

# Stupid fixed IDs from old MaPit
WMP_AREA_ID = 900000
EUP_AREA_ID = 900001
LAE_AREA_ID = 900002
SPA_AREA_ID = 900003
WAS_AREA_ID = 900004
NIA_AREA_ID = 900005
LAS_AREA_ID = 900006
HOL_AREA_ID = 900007
HOC_AREA_ID = 900008
enclosing_areas = {
    'LAC': [ LAE_AREA_ID, LAS_AREA_ID ],
    'SPC': [ SPA_AREA_ID ],
    'WAC': [ WAS_AREA_ID ],
    'NIE': [ NIA_AREA_ID ],
    'WMC': [ WMP_AREA_ID ],
    'EUR': [ EUP_AREA_ID ],
}

@ratelimit(minutes=3, requests=100)
def postcode(request, postcode, format=None):
    if hasattr(countries, 'canonical_postcode'):
        canon_postcode = countries.canonical_postcode(postcode)
        postcode = canon_postcode
        #if (postcode != canon_postcode and format is None) or format == 'json':
        #    return redirect('mapit.views.postcodes.postcode', postcode=canon_postcode)
    if format is None:
        format = 'json'
    if not is_valid_postcode(postcode):
        raise ViewException(format, "Postcode '%s' is not valid." % postcode, 400)
    postcode = get_object_or_404(Postcode, format=format, postcode=postcode)
    try:
        generation = int(request.REQUEST['generation'])
    except:
        generation = Generation.objects.current()
    if not hasattr(countries, 'is_special_postcode') or not countries.is_special_postcode(postcode.postcode):
        areas = add_codes(Area.objects.by_postcode(postcode, generation))
    else:
        areas = []

    # Shortcuts
    shortcuts = {}
    for area in areas:
        if area.type.code in ('COP','LBW','LGE','MTW','UTE','UTW'):
            shortcuts['ward'] = area.id
            shortcuts['council'] = area.parent_area_id
        elif area.type.code == 'CED':
            shortcuts.setdefault('ward', {})['county'] = area.id
            shortcuts.setdefault('council', {})['county'] = area.parent_area_id
        elif area.type.code == 'DIW':
            shortcuts.setdefault('ward', {})['district'] = area.id
            shortcuts.setdefault('council', {})['district'] = area.parent_area_id
        elif area.type.code in ('WMC'): # XXX Also maybe 'EUR', 'NIE', 'SPC', 'SPE', 'WAC', 'WAE', 'OLF', 'OLG', 'OMF', 'OMG'):
            shortcuts[area.type.code] = area.id

    # Add manual enclosing areas. 
    extra = []
    for area in areas:
        if area.type.code in enclosing_areas.keys():
            extra.extend(enclosing_areas[area.type.code])
    areas = itertools.chain(areas, Area.objects.filter(id__in=extra))
 
    if format == 'html':
        return render(request, 'mapit/postcode.html', {
            'postcode': postcode.as_dict(),
            'areas': areas,
            'json': '/postcode/',
        })

    out = postcode.as_dict()
    out['areas'] = dict( ( area.id, area.as_dict() ) for area in areas )
    if shortcuts: out['shortcuts'] = shortcuts
    return output_json(out)

@ratelimit(minutes=3, requests=100)
def partial_postcode(request, postcode, format='json'):
    postcode = re.sub('\s+', '', postcode.upper())
    if is_valid_postcode(postcode):
        postcode = re.sub('\d[A-Z]{2}$', '', postcode)
    if not is_valid_partial_postcode(postcode):
        raise ViewException(format, "Partial postcode '%s' is not valid." % postcode, 400)
    try:
        postcode = Postcode(
            postcode = postcode,
            location = Postcode.objects.filter(postcode__startswith=postcode).extra(
                where = [ 'length(postcode) = %d' % (len(postcode)+3) ]
            ).collect().centroid
        )
    except:
        raise ViewException(format, 'Postcode not found', 404)

    if format == 'html':
        return render(request, 'mapit/postcode.html', {
            'postcode': postcode.as_dict(),
            'json': '/postcode/partial/',
        })

    return output_json(postcode.as_dict())

@ratelimit(minutes=3, requests=100)
def example_postcode_for_area(request, area_id, format='json'):
    area = get_object_or_404(Area, format=format, id=area_id)
    try:
        pc = Postcode.objects.filter(areas=area).order_by()[0]
    except:
        set_timeout(format)
        try:
            pc = Postcode.objects.filter_by_area(area).order_by()[0]
        except QueryCanceledError:
            raise ViewException(format, 'That query was taking too long to compute.', 500)
        except DatabaseError, e:
            if 'canceling statement due to statement timeout' not in e.args[0]: raise
            raise ViewException(format, 'That query was taking too long to compute.', 500)
        except:
            pc = None
    if pc: pc = pc.get_postcode_display()
    if format == 'html':
        return render(request, 'mapit/example-postcode.html', { 'area': area, 'postcode': pc })
    return output_json(pc)

def form_submitted(request):
    pc = request.POST.get('pc', None)
    if not request.method == 'POST' or not pc:
        return redirect('/')
    return redirect('mapit.views.postcodes.postcode', postcode=pc, format='html')

@ratelimit(minutes=3, requests=100)
def nearest(request, srid, x, y, format='json'):
    location = Point(float(x), float(y), srid=int(srid))
    set_timeout(format)
    try:
        postcode = Postcode.objects.filter(location__distance_gte=( location, D(mi=0) )).distance(location).order_by('distance')[0]
    except QueryCanceledError:
        raise ViewException(format, 'That query was taking too long to compute.', 500)
    except DatabaseError, e:
        if 'canceling statement due to statement timeout' not in e.args[0]: raise
        raise ViewException(format, 'That query was taking too long to compute.', 500)
    except:
        raise ViewException(format, 'No postcode found near %s,%s (%s)' % (x, y, srid), 404)

    if format == 'html':
        return render( request, 'mapit/postcode.html', {
            'postcode': postcode.as_dict(),
            'json': '/postcode/',
        })

    pc = postcode.as_dict()
    pc['distance'] = round(postcode.distance.m)
    return output_json({
        'postcode': pc,
    })


########NEW FILE########
__FILENAME__ = settings
import os
import sys
import yaml
import django

# Path to here is something like
# /data/vhost/<vhost>/<repo>/<project_name>/settings.py
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(PROJECT_DIR, '..'))
PARENT_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, '..'))

# The mySociety deployment system works by having a conf directory at the root
# of the repo, containing a general.yml file of options. Use that file if
# present. Obviously you can just edit any part of this file, it is a normal
# Django settings.py file.
try:
    config = yaml.load( open(os.path.join(PROJECT_ROOT, 'conf', 'general.yml'), 'r') )
except:
    config = {}

# An EPSG code for what the areas are stored as, e.g. 27700 is OSGB, 4326 for
# WGS84. Optional, defaults to 4326.
MAPIT_AREA_SRID = int(config.get('AREA_SRID', 4326))

# Country is currently one of GB, NO, or KE. Optional; country specific things
# won't happen if not set.
MAPIT_COUNTRY = config.get('COUNTRY', '')

# A list of IP addresses or User Agents that should be excluded from rate
# limiting. Optional.
MAPIT_RATE_LIMIT = config.get('RATE_LIMIT', [])

# A GA code for analytics
GOOGLE_ANALYTICS = config.get('GOOGLE_ANALYTICS', '')

# Django settings for mapit project.

DEBUG = config.get('DEBUG', True)
TEMPLATE_DEBUG = DEBUG

# (Note that even if DEBUG is true, output_json still sets a
# Cache-Control header with max-age of 28 days.)
if DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
    CACHE_MIDDLEWARE_SECONDS = 0
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': '127.0.0.1:11211',
            'TIMEOUT': 86400,
        }
    }
    CACHE_MIDDLEWARE_SECONDS = 86400
    CACHE_MIDDLEWARE_KEY_PREFIX = config.get('MAPIT_DB_NAME')

if config.get('BUGS_EMAIL'):
    SERVER_EMAIL = config['BUGS_EMAIL']
    ADMINS = (
        ('mySociety bugs', config['BUGS_EMAIL']),
    )
    MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': config.get('MAPIT_DB_NAME', 'mapit'),
        'USER': config.get('MAPIT_DB_USER', 'mapit'),
        'PASSWORD': config.get('MAPIT_DB_PASS', ''),
        'HOST': config.get('MAPIT_DB_HOST', ''),
        'PORT': config.get('MAPIT_DB_PORT', ''),
    }
}

# Make this unique, and don't share it with anybody.
SECRET_KEY = config.get('DJANGO_SECRET_KEY', '')

ALLOWED_HOSTS = ['*']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
if MAPIT_COUNTRY == 'GB':
    TIME_ZONE = 'Europe/London'
    LANGUAGE_CODE = 'en-gb'
elif MAPIT_COUNTRY == 'NO':
    TIME_ZONE = 'Europe/Oslo'
    LANGUAGE_CODE = 'no'
else:
    TIME_ZONE = 'Europe/London'
    LANGUAGE_CODE = 'en'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.join( PARENT_DIR, 'collected_static' )

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    # Needs adapting to new class version
    #'django.template.loaders.app_directories.Loader',
    'mapit.loader.load_template_source',
)

# UpdateCacheMiddleware does ETag setting, and
# ConditionalGetMiddleware does ETag checking.
# So we don't want this flag, which runs very
# similar ETag code in CommonMiddleware.
USE_ETAGS = False

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'mapit.middleware.JSONPMiddleware',
    'mapit.middleware.ViewExceptionMiddleware',
)

ROOT_URLCONF = 'project.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'project.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'mapit.context_processors.country',
    'mapit.context_processors.analytics',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.gis',
    'django.contrib.staticfiles',

    'south',
    'mapit',
)


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include
from django.contrib import admin
admin.autodiscover()

handler500 = 'mapit.shortcuts.json_500'

urlpatterns = patterns('',
    (r'^', include('mapit.urls')),
    (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
#!/usr/bin/env python

import os, sys

file_dir = os.path.realpath(os.path.dirname(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(file_dir, '..')))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = wsgi_monitor
# From http://code.google.com/p/modwsgi/wiki/ReloadingSourceCode

import os
import sys
import time
import signal
import threading
import atexit
import Queue

_interval = 1.0
_times = {}
_files = []

_running = False
_queue = Queue.Queue()
_lock = threading.Lock()

def _restart(path):
    _queue.put(True)
    prefix = 'monitor (pid=%d):' % os.getpid()
    print >> sys.stderr, '%s Change detected to \'%s\'.' % (prefix, path)
    print >> sys.stderr, '%s Triggering process restart.' % prefix
    os.kill(os.getpid(), signal.SIGINT)

def _modified(path):
    try:
        # If path doesn't denote a file and were previously
        # tracking it, then it has been removed or the file type
        # has changed so force a restart. If not previously
        # tracking the file then we can ignore it as probably
        # pseudo reference such as when file extracted from a
        # collection of modules contained in a zip file.

        if not os.path.isfile(path):
            return path in _times

        # Check for when file last modified.

        mtime = os.stat(path).st_mtime
        if path not in _times:
            _times[path] = mtime

        # Force restart when modification time has changed, even
        # if time now older, as that could indicate older file
        # has been restored.

        if mtime != _times[path]:
            return True
    except:
        # If any exception occured, likely that file has been
        # been removed just before stat(), so force a restart.

        return True

    return False

def _monitor():
    while 1:
        # Check modification times on all files in sys.modules.

        for module in sys.modules.values():
            if not hasattr(module, '__file__'):
                continue
            path = getattr(module, '__file__')
            if not path:
                continue
            if os.path.splitext(path)[1] in ['.pyc', '.pyo', '.pyd']:
                path = path[:-1]
            if _modified(path):
                return _restart(path)

        # Check modification times on files which have
        # specifically been registered for monitoring.

        for path in _files:
            if _modified(path):
                return _restart(path)

        # Go to sleep for specified interval.

        try:
            return _queue.get(timeout=_interval)
        except:
            pass

_thread = threading.Thread(target=_monitor)
_thread.setDaemon(True)

def _exiting():
    try:
        _queue.put(True)
    except:
        pass
    _thread.join()

atexit.register(_exiting)

def track(path):
    if not path in _files:
        _files.append(path)

def start(interval=1.0):
    global _interval
    if interval < _interval:
        _interval = interval

    global _running
    _lock.acquire()
    if not _running:
        prefix = 'monitor (pid=%d):' % os.getpid()
        print >> sys.stderr, '%s Starting change monitor.' % prefix
        _running = True
        _thread.start()
    _lock.release()

########NEW FILE########
