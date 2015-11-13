__FILENAME__ = datastream
"""
These classes used during communication with the servers.
"""

import eeml
import httplib
import re
from lxml import etree

URLPATTERN = re.compile("/v[12]/feeds/\d+\.xml")

class CosmError(Exception):
    """
    Exception type of COSM communication
    """
    pass

class Cosm(object):
    """
    A class for manually updating a Cosm data stream.
    """

    host = 'api.cosm.com'

    def __init__(self, url, key, env=None, loc=None, dat=list(),
                 use_https=True, timeout=10):
        """
        :param url: the api url either '/v2/feeds/1275.xml' or 1275
        :type url: `str`
        :param key: your personal api key
        :type key: `str`
        """
        if not env:
            env = eeml.Environment()
        if str(url) == url:
            if(URLPATTERN.match(url)):
                self._url = url
            else:
                raise ValueError("The url argument has to be in the form "
                                 "'/v2/feeds/1275.xml' or 1275")
        else:
            try:
                if int(url) == url:
                    self._url = '/v2/feeds/' + str(url) + '.xml'
                else:
                    raise TypeError('')
            except TypeError:
                raise TypeError("The url argument has to be in the form "
                                "'/v2/feeds/1275.xml' or 1275")
        self._key = key
        self._use_https = use_https
        self._eeml = eeml.create_eeml(env, loc, dat)
        self._http_timeout = timeout

    def update(self, data):
        """
        Update a data stream.

        :param data: the data to be updated
        :type data: `Data`, `list`
        """
        self._eeml.updateData(data)

    def put(self):
        """
        Put the information to the website.

        :raise CosmError: if there was problem with the communication
        """
        if self._use_https:
            conn = httplib.HTTPSConnection(self.host,
                                           timeout=self._http_timeout)
        else:
            conn = httplib.HTTPConnection(self.host,
                                          timeout=self._http_timeout)

        conn.request('PUT', self._url, self.geteeml(False),
                     {'X-ApiKey': self._key})
        conn.sock.settimeout(5.0)
        resp = conn.getresponse()
        if resp.status != 200:
            try:
                errors = etree.fromstring(resp.read())
                msg = "%s: %s" % (errors[0].text, errors[1].text)
            except:
                msg = resp.reason
            raise CosmError(msg)
        resp.read()
        conn.close()

    def geteeml(self, pretty_print=True):
        """
        Return the EEML document as a string
        """
        return etree.tostring(self._eeml.toeeml(), encoding='UTF-8',
                              pretty_print=pretty_print)

class Pachube(Cosm):
    """
    For backward compatibility
    """
    pass

########NEW FILE########
__FILENAME__ = invalidator
"""
Don't validate any input
"""


class Invalidator(object):
    """
    Doesn't do much
    """

    def environment(self, env):
        pass

    def location(self, loc):
        pass

    def data(self, data):
        pass

    def datapoints(self, datapoints):
        pass

Validator = Invalidator

########NEW FILE########
__FILENAME__ = namespace
"""
XML namespace definitions
"""

EEML_SCHEMA_VERSION = '0.5.1'
EEML_NAMESPACE = 'http://www.eeml.org/xsd/{}'.format(EEML_SCHEMA_VERSION)
XSI_NAMESPACE = 'http://www.w3.org/2001/XMLSchema-instance'
SCHEMA_LOCATION = ('{{{}}}schemaLocation'.format(XSI_NAMESPACE),
                   EEML_NAMESPACE +
                   ' http://www.eeml.org/xsd/{0}/{0}.xsd'
                   .format(EEML_SCHEMA_VERSION))
NSMAP = {None: EEML_NAMESPACE,
         'xsi': XSI_NAMESPACE}


########NEW FILE########
__FILENAME__ = unit
"""
This package stores all the available implementations of Unit
"""

from eeml.util import _elem, _addA

class Unit(object):
    """
    This class represents a unit element in the EEML document.
    """

    __valid_types = ['basicSI', 'derivedSI', 'conversionBasedUnits',
                     'derivedUnits', 'contextDependentUnits']

    def __init__(self, name, type_=None, symbol=None):
        """
        :raise Exception: is sg is wrong

        :param name: the name of this unit (eg. meter, Celsius)
        :type name: `str`
        :param type_: the type of this unit (``basicSI``, ``derivedSI``, ``conversionBasedUnits``, ``derivedUnits``, ``contextDependentUnits``)
        :type type: `str`
        :param symbol: the symbol of this unit (eg. m, C)
        :type symbol: `str`
        """

        self._name = name
        if type_ is not None and not type_ in self.__valid_types:
            raise ValueError("type must be {}, got '{}'".format(
                    ", ".join(['%s'%s for s in self.__valid_types]), type_))
        self._type = type_
        self._symbol = symbol

    def toeeml(self):
        """
        Convert this object into a DOM element.

        :return: the unit element
        :rtype: `Element`
        """

        unit = _elem('unit')

        _addA(unit, self._type, 'type')
        _addA(unit, self._symbol, 'symbol')

        unit.text = self._name

        return unit


class Celsius(Unit):
    """
    Degree Celsius unit class.
    """

    def __init__(self):
        """
        Initialize the `Unit` parameters with Celsius.
        """
        Unit.__init__(self, 'Celsius', 'derivedSI', u'\xb0C')

class Degree(Unit):
    """
    Degree of arc unit class.
    """

    def __init__(self):
        """
        Initialize the `Unit` parameters with Degree.
        """
        Unit.__init__(self, 'Degree', 'basicSI', u'\xb0')


class Fahrenheit(Unit):
    """
    Degree Fahrenheit unit class.
    """

    def __init__(self):
        """
        Initialize the `Unit` parameters with Fahrenheit.
        """
        Unit.__init__(self, 'Fahrenheit', 'derivedSI', u'\xb0F')


class hPa(Unit):
    """
    hPa unit class.
    """

    def __init__(self):
        """
        Initialize the `Unit` parameters with hPa.
        """
        Unit.__init__(self, 'hPa', 'derivedSI', 'hPa')


class Knots(Unit):
    """
    Knots class.
    """

    def __init__(self):
        """
        Initialize the `Unit` parameters with Knots.
        """
        Unit.__init__(self, 'Knots', 'conversionBasedUnits', u'kts')


class RH(Unit):
    """
    Relative Humidity unit class.
    """

    def __init__(self):
        """
        Initialize the `Unit` parameters with Relative Humidity.
        """
        Unit.__init__(self, 'Relative Humidity', 'derivedUnits', '%RH')


class Watt(Unit):
    """
    Watt unit class.
    """

    def __init__(self):
        """
        Initialize the `Unit` parameters with Watt.
        """
        Unit.__init__(self, 'Watt', 'derivedSI', 'W')


########NEW FILE########
__FILENAME__ = util
"""
Some utility functions, not for public use
"""

try:
    from lxml import etree
except ImportError: # If lxml is not there try python standard lib
    from xml.etree import ElementTree as etree

from eeml.namespace import EEML_NAMESPACE, NSMAP

def _elem(name):
    """
    Create an element in the EEML namespace
    """
    return etree.Element("{{{}}}{}".format(EEML_NAMESPACE, name), nsmap=NSMAP)


def _addE(env, attr, name, call=lambda x: x):
    """
    Helper method to add child if not None
    """
    if attr is not None:
        tmp = _elem(name)
        tmp.text = call(attr)
        env.append(tmp)


def _addA(env, attr, name, call=lambda x: x):
    """
    Helper method to add attribute if not None
    """
    if attr is not None:
        env.attrib[name] = call(attr)


def _assertPosInt(val, name, required=False):
    """
    Check if val is positive integer. If val is None ValueError is raised
    if required is True
    """
    if isinstance(val, (int, long)):
        if val < 0:
            raise ValueError("Positive integer is required as {}, got {}"
                             .format(name, val))
    elif val is not None:
        raise ValueError("Integer value is required as {}, got {}"
                         .format(name, type(val)))
    elif required:
        raise ValueError("{} is required, got {}".format(name, val))

########NEW FILE########
__FILENAME__ = validator
"""
Here are the validators
"""

from datetime import datetime

from eeml.unit import Unit
from eeml.util import _assertPosInt

import logging

class Version051(object):
    """
    Validate constructors by version 0.5.1 specification
    """

    def environment(self, env):
        status = env._status
        id_ = env._id
        private = env._private
        
        if status is not None and status not in ['frozen', 'live']:
            raise ValueError("status must be either 'frozen' or 'live', "
                             "got {}".format(status))
        _assertPosInt(id_, 'id', False)
        if private is not None and not isinstance(private, bool):
            raise ValueError("private is expected to be bool, got {}"
                             .format(type(private)))

    def location(self, loc):
        exposure = loc._exposure
        domain = loc._domain
        disposition = loc._disposition
        # TODO validate lat and lon

        if exposure is not None and exposure not in ['indoor', 'outdoor']:
            raise ValueError("exposure must be 'indoor' or 'outdoor', got '{}'"
                             .format(exposure))

        if domain not in ['physical', 'virtual']:
            raise ValueError("domain is required, must be 'physical' or 'virtual', got '{}'"
                             .format(domain))

        if disposition is not None and disposition not in ['fixed', 'mobile']:
            raise ValueError("disposition must be 'fixed' or 'mobile', got '{}'"
                             .format(disposition))

    def data(self, data):
        unit = data._unit
        at = data._at
        id_ = data._id

        _assertPosInt(id_, 'id', True)
        if unit is not None and not isinstance(unit, Unit):
            raise ValueError("unit must be an instance of Unit, got {}"
                             .format(type(unit)))
        if at is not None and not isinstance(at, datetime):
            raise ValueError("at must be an instance of datetime.datetime, "
                             "got {}".format(type(at)))

    def datapoints(self, datapoints):
        id_ = datapoints._id

        _assertPosInt(id_, 'id', True)

Validator = Version051

########NEW FILE########
__FILENAME__ = exception_example
import eeml
import eeml.datastream
import eeml.unit
import serial
from eeml.datastream import CosmError

# parameters
API_KEY = 'YOUR PERSONAL API KEY'
FEED = 'YOUR PERSONAL FEED ID'
API_URL = '/v2/feeds/{feednum}.xml' .format(feednum = FEED)

serial = serial.Serial('/dev/ttyUSB0', 9600)
readings = serial.readline().strip().split(' ') # the readings are separated by spaces

# open up your cosm feed
pac = eeml.datastream.Cosm(API_URL, API_KEY)

# prepare the emml payload
pac.update([eeml.Data(0, readings[0], unit=eeml.unit.Celsius()), eeml.Data(1, readings[1], unit=eeml.unit.RH())])

# attempt to send the data to Cosm.  Attempt to handle exceptions, such that the script continues running.
# You could optionally place some retry logic around the pac.put() command.
try:
	pac.put()
except CosmError, e:
	print('ERROR: pac.put(): {}'.format(e))
except StandardError:
	print('ERROR: StandardError')
except:
	print('ERROR: Unexpected error: %s' % sys.exc_info()[0])

########NEW FILE########
__FILENAME__ = read_serial
import eeml
import eeml.datastream
import eeml.unit
import serial

# parameters
API_KEY = 'YOUR PERSONAL API KEY'
API_URL = 'YOUR PERSONAL API URL, LIKE /api/1275.xml'

serial = serial.Serial('/dev/ttyUSB0', 9600)
readings = serial.readline().strip().split(' ') # the readings are separated by spaces
pac = eeml.datastream.Cosm(API_URL, API_KEY)
pac.update([eeml.Data(0, readings[0], unit=eeml.unit.Celsius()), eeml.Data(1, readings[1], unit=eeml.unit.RH())])
print(pac.geteeml())
pac.put()


########NEW FILE########
__FILENAME__ = simple_example
import eeml
import eeml.datastream
import eeml.unit
import serial
import datetime

# parameters
API_KEY = 'YOUR_API_KEY'
# API_URL = '/v2/feeds/42166.xml'
API_URL = 42166

readings = [3, 4]
pac = eeml.datastream.Cosm(API_URL, API_KEY)
at = datetime.datetime(2012, 9, 12, 11, 0, 0)

pac.update([
        eeml.Data(0, readings[0], tags=('Temperature',), unit=eeml.unit.Celsius(), at=at), 
        eeml.Data(1, readings[1], tags=('Humidity',), unit=eeml.unit.RH())])
pac.put()
print(pac.geteeml())

########NEW FILE########
__FILENAME__ = test_eeml
from datetime import datetime
import pytz

from lxml import etree

from formencode.doctest_xml_compare import xml_compare

from nose.tools import assert_true

from eeml import Location, EEML, Environment, Data, DataPoints, create_eeml
from eeml.datastream import Cosm, Pachube
from eeml.unit import Celsius, Unit, RH

from unittest import TestCase

class TestEEML(TestCase):

    def test_good_location(self):
        loc = Location('physical', 'My Room', 32.4, 22.7, 0.2, 'indoor', 'fixed')

        assert_true(xml_compare(etree.fromstring(
            """
            <location xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.eeml.org/xsd/0.5.1" disposition="fixed" domain="physical" exposure="indoor">
            <name>My Room</name>
            <lat>32.4</lat>
            <lon>22.7</lon>
            <ele>0.2</ele>
            </location>
            """), loc.toeeml(), reporter=self.fail))


    def test_good_unit(self):
        unit = Unit("Celzius", 'basicSI', "C")

        assert_true(xml_compare(etree.fromstring(
            """
            <unit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.eeml.org/xsd/0.5.1" type="basicSI" symbol="C">Celzius</unit>
            """), unit.toeeml(), reporter=self.fail))


    def test_good_data(self):
        u = Unit('Celsius', 'derivedSI', 'C')
        test_data = Data(
            id_=0,
            value=10.0, 
            tags=['length', 'foo'], 
            minValue=0, 
            maxValue=100, 
            unit=u)

        assert_true(xml_compare(etree.fromstring(
            """
            <data xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.eeml.org/xsd/0.5.1" id="0">
            <tag>length</tag>
            <tag>foo</tag>
            <current_value maxValue="100" minValue="0">10.0</current_value>
            <unit symbol="C" type="derivedSI">Celsius</unit>
            </data>
            """), test_data.toeeml(), reporter=self.fail))


    def test_good_datapoints(self):
        env = Environment('A Room Somewhere',
                          'http://www.cosm.com/feeds/1.xml',
                          'frozen',
                          'This is a room somewhere',
                          'http://www.roomsomewhere/icon.png',
                          'http://www.roomsomewhere/',
                          'myemail@roomsomewhere',
                          updated=datetime(2007, 5, 4, 18, 13, 51, 0, pytz.utc),
                          creator='http://www.somewhere',
                          id_=1)

        datapoints = DataPoints(1, [(0,), (1,), (2, datetime(2007, 5, 4, 18, 13, 51, 0, pytz.utc))])

        result = create_eeml(env, None, datapoints).toeeml()

        assert_true(xml_compare(etree.fromstring(
            """
<eeml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.eeml.org/xsd/0.5.1" xsi:schemaLocation="http://www.eeml.org/xsd/0.5.1 http://www.eeml.org/xsd/0.5.1/0.5.1.xsd" version="0.5.1">
  <environment updated="2007-05-04T18:13:51+00:00" creator="http://www.somewhere" id="1">
    <title>A Room Somewhere</title>
    <feed>http://www.cosm.com/feeds/1.xml</feed>
    <status>frozen</status>
    <description>This is a room somewhere</description>
    <icon>http://www.roomsomewhere/icon.png</icon>
    <website>http://www.roomsomewhere/</website>
    <email>myemail@roomsomewhere</email>
    <data id="1">
      <datapoints xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.eeml.org/xsd/0.5.1">
        <value>0</value>
        <value>1</value>
        <value at="2007-05-04T18:13:51+00:00">2</value>
      </datapoints>
    </data>
  </environment>
</eeml>
"""), result, reporter=self.fail))


    def test_good_environment(self):
        env = Environment('A Room Somewhere',
            'http://www.cosm.com/feeds/1.xml',
            'frozen',
            'This is a room somewhere',
            'http://www.roomsomewhere/icon.png',
            'http://www.roomsomewhere/',
            'myemail@roomsomewhere',
            updated='2007-05-04T18:13:51.0Z',
            creator='http://www.somewhere',
            id_=1)

        assert_true(xml_compare(etree.fromstring(
            """
            <environment xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.eeml.org/xsd/0.5.1" creator="http://www.somewhere" id="1" updated="2007-05-04T18:13:51.0Z">
                <title>A Room Somewhere</title>
                <feed>http://www.cosm.com/feeds/1.xml</feed>
                <status>frozen</status>
                <description>This is a room somewhere</description>
                <icon>http://www.roomsomewhere/icon.png</icon>
                <website>http://www.roomsomewhere/</website>
                <email>myemail@roomsomewhere</email>
            </environment>"""), env.toeeml(), reporter=self.fail))

    def test_good_create_doc(self):
        env = Environment('A Room Somewhere',
            'http://www.cosm.com/feeds/1.xml',
            'frozen',
            'This is a room somewhere',
            'http://www.roomsomewhere/icon.png',
            'http://www.roomsomewhere/',
            'myemail@roomsomewhere',
            updated='2007-05-04T18:13:51.0Z',
            creator='http://www.somewhere',
            id_=1)
        loc = Location('physical', 'My Room', 32.4, 22.7, 0.2, 'indoor', 'fixed')
        u = Unit('Celsius', 'derivedSI', 'C')
        dat = []
        dat.append(Data(0, 36.2, minValue=23.8, maxValue=48.0, unit = u, tags=['temperature']))
        u = Unit('blushesPerHour', 'contextDependentUnits')
        dat.append(Data(1, 84.2, minValue=0, maxValue=100, unit = u, tags=['blush', 'redness', 'embarrasement']))
        u = Unit('meter', 'basicSI', 'm')
        dat.append(Data(2, 12.3, minValue=0, unit = u, tags=['length', 'distance', 'extension']))


        intermed = etree.tostring(
            create_eeml(env, loc, dat).toeeml()) # Broken down to help with error-checking
        final = etree.fromstring(intermed)


        assert_true(xml_compare(etree.fromstring(
            """
            <eeml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.eeml.org/xsd/0.5.1" xsi:schemaLocation="http://www.eeml.org/xsd/0.5.1 http://www.eeml.org/xsd/0.5.1/0.5.1.xsd" version="0.5.1">
                <environment creator="http://www.somewhere" id="1" updated="2007-05-04T18:13:51.0Z">
                    <title>A Room Somewhere</title>
                    <feed>http://www.cosm.com/feeds/1.xml</feed>                    
                    <status>frozen</status>
                    <description>This is a room somewhere</description>
                    <icon>http://www.roomsomewhere/icon.png</icon>
                    <website>http://www.roomsomewhere/</website>
                    <email>myemail@roomsomewhere</email>
                    <location disposition="fixed" domain="physical" exposure="indoor">
                        <name>My Room</name>
                        <lat>32.4</lat>
                        <lon>22.7</lon>
                        <ele>0.2</ele>
                    </location>
                    <data id="0">
                        <tag>temperature</tag>
                        <current_value maxValue="48.0" minValue="23.8">36.2</current_value>
                        <unit symbol="C" type="derivedSI">Celsius</unit>
                    </data>
                    <data id="1">
                        <tag>blush</tag>
                        <tag>redness</tag>
                        <tag>embarrasement</tag>
                        <current_value maxValue="100" minValue="0">84.2</current_value>
                        <unit type="contextDependentUnits">blushesPerHour</unit>
                    </data>
                    <data id="2">
                        <tag>length</tag>
                        <tag>distance</tag>
                        <tag>extension</tag>
                        <current_value minValue="0">12.3</current_value>
                        <unit symbol="m" type="basicSI">meter</unit>
                    </data>
                </environment>
            </eeml>
            """), final, reporter=self.fail))

    def test_status(self):
        Environment(status='frozen')
        Environment(status='live')
        with self.assertRaises(ValueError):
            Environment(status='foobar')

    def test_env_location(self):
        env = Environment()
        env.setLocation(Location('virtual'))
        with self.assertRaises(ValueError):
            env.setLocation('foobar')

    def test_env_id(self):
        Environment(id_=1)
        Environment(id_=None)
        with self.assertRaises(ValueError):
            Environment(id_='foobar')
        with self.assertRaises(ValueError):
            Environment(id_=4.22)

    def test_env_private(self):
        env = Environment(private=False)
        assert_true(xml_compare(etree.fromstring("""
<environment xmlns="http://www.eeml.org/xsd/0.5.1">
  <private>false</private>
</environment>"""), env.toeeml(), reporter=self.fail))

        env = Environment(private=True)
        assert_true(xml_compare(etree.fromstring("""
<environment xmlns="http://www.eeml.org/xsd/0.5.1">
  <private>true</private>
</environment>"""), env.toeeml(), reporter=self.fail))

        with self.assertRaises(ValueError):
            Environment(private='foobar')

    def test_eeml_ctor(self):
        EEML(Environment())
        with self.assertRaises(ValueError):
            EEML('foobar')

    def test_exposure(self):
        Location('virtual', exposure='indoor')
        Location('physical', exposure='outdoor')
        with self.assertRaises(ValueError):
            Location('virtual', exposure='foobar')

    def test_domain(self):
        Location(domain='physical')
        Location(domain='virtual')
        Location('physical')
        Location('virtual')
        with self.assertRaises(ValueError):
            Location(domain='foobar')
        with self.assertRaises(ValueError):
            Location('foobar')

    def test_disposition(self):
        Location('virtual', disposition='fixed')
        Location('virtual', disposition='mobile')
        with self.assertRaises(ValueError):
            Location('virtual', disposition='foobar')

    def test_unit(self):
        Data(1, 2, unit=None)
        Data(1, 2, unit=Celsius())
        with self.assertRaises(ValueError):
            Data(1, 2, unit='foobar')

    def test_at(self):
        Data(1, 2, at=datetime.now())
        with self.assertRaises(ValueError):
            Data(1, 2, at='foobar')

    def test_data_id(self):
        Data(1, 2)
        with self.assertRaises(ValueError):
            Data('foobar', 4)
        with self.assertRaises(ValueError):
            Data(4.44, 4)

    def test_unit_types(self):
        for i in ['basicSI', 'derivedSI', 'conversionBasedUnits',
                  'derivedUnits', 'contextDependentUnits']:
            Unit('foobar', i)
        with self.assertRaises(ValueError):
            Unit('foobar', 'barbar')

    def test_pachube(self):
        Pachube('/v2/feeds/1234.xml', 'ASDF')
        Pachube(1234, 'ASDF')
        with self.assertRaises(ValueError):
            Pachube('12.xml', 'ASDF')

    def test_cosm(self):
        Cosm('/v2/feeds/1234.xml', 'ASDF')
        Cosm(1234, 'ASDF')
        with self.assertRaises(ValueError):
            Cosm('api.cosm.com/v2/feeds/', 'ASDF')
        
    def test_multiple_datapoints(self):
        env = Environment()
        env.updateData(DataPoints(1, [(4,)]))
        env.updateData(DataPoints(4, [(5,)]))
        env.updateData(DataPoints(1, [(6,), (7,)]))

        assert_true(xml_compare(etree.fromstring("""
<environment xmlns="http://www.eeml.org/xsd/0.5.1">
  <data id="1">
    <datapoints>
      <value>6</value>
      <value>7</value>
    </datapoints>
  </data>
  <data id="4">
    <datapoints>
      <value>5</value>
    </datapoints>
  </data>
</environment>"""), env.toeeml(), reporter=self.fail))

    def test_multiple_update(self):
        pac = Cosm(1, 'ASDF')
        pac.update([
                Data(1, 10),
                Data(2, 22, unit=RH()),
                Data(3, 44),
                Data(5, 65)])

        pac.update([
                Data(2, 476),
                Data(5, -1)])

        assert_true(xml_compare(etree.fromstring("""
            <eeml xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.eeml.org/xsd/0.5.1" xsi:schemaLocation="http://www.eeml.org/xsd/0.5.1 http://www.eeml.org/xsd/0.5.1/0.5.1.xsd" version="0.5.1">
              <environment>
                <data id="1">
                  <current_value>10</current_value>
                </data>
                <data id="2">
                  <current_value>476</current_value>
                </data>
                <data id="3">
                  <current_value>44</current_value>
                </data>
                <data id="5">
                  <current_value>-1</current_value>
                </data>
              </environment>
            </eeml>"""),
                                etree.fromstring(pac.geteeml()), reporter=self.fail))

    def test_invalidator(self):
        import eeml.validator
        oldvalidator = eeml.validator
        from eeml.invalidator import Invalidator
        eeml.validator = Invalidator()
        env = Environment(status='foobar')
        eeml.validator = oldvalidator

########NEW FILE########
