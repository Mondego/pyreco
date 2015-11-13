__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

try:
    import pkg_resources
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if is_jython:
    import subprocess
    
    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd', 
           quote(tmpeggs), 'zc.buildout'], 
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse('setuptools')).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout',
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse('setuptools')).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout')
import zc.buildout.buildout
zc.buildout.buildout.main(sys.argv[1:] + ['bootstrap'])
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = account
from googleanalytics.exception import GoogleAnalyticsClientError
from googleanalytics.data import DataSet

import urllib

filter_operators = ['==', '!=', '>', '<', '>=', '<=', '=~', '!~', '=@', '!@']

class Account:
    def __init__(self, connection=None, title=None, id=None,
        account_id=None, account_name=None, profile_id=None,
        currency=None, time_zone=None, web_property_id=None,
        table_id=None, updated=None):
        self.connection = connection
        self.title = title
        self.id = id
        self.account_id = account_id
        self.account_name = account_name
        self.profile_id = profile_id
        self.currency = currency
        self.time_zone = time_zone
        self.updated = updated
        self.web_property_id = web_property_id
        self.table_id = table_id

    def __repr__(self):
        return '<Account: %s>' % self.title

    def get_data(self, start_date, end_date, metrics, dimensions=[], sort=[], filters=[], start_index=0, max_results=0):
        """
        Pulls data in from an account and returns a processed data structure for
        easy post processing. This method requires the following inputs:
        
        ** Required Arguments **
        
        ``start_date``
          A ``datetime`` object for the lower bound of your query
          
        ``end_date``
          A ``datetime`` object for the upper bound of your query
    
        ``metrics``
          A list of metrics, for example: ['pageviews', 'uniquePageviews']
        
          See: http://code.google.com/apis/analytics/docs/gdata/gdataReferenceDimensionsMetrics.html
          See: http://code.google.com/apis/analytics/docs/gdata/gdataReference.html#dimensionsAndMetrics
    
        ** Optional Arguments **
        
        ``dimensions``
          A list of dimensions, for example: ['country','browser']
        
          See: http://code.google.com/apis/analytics/docs/gdata/gdataReferenceDimensionsMetrics.html
          See: http://code.google.com/apis/analytics/docs/gdata/gdataReference.html#dimensionsAndMetrics
    
        ``sort``
          A list of dimensions or metrics to sort the output by, should probably
          be one of the items you specified in ``dimensions`` or ``metrics``.
          For example: ['browser', 'pageviews']
        
          See: http://code.google.com/apis/analytics/docs/gdata/gdataReference.html#sorting
          
        ``filters``
          A list of filters.  A filter expression has three parts:
          
            name - The name of the dimension or metric to filter on. 
                    For example: ga:pageviews will filter on the pageviews metric.
            operator - Defines the type of filter match to use. Operators are 
                        specific to either dimensions or metrics.
            expression - States the values included or excluded from the results.
                          Expressions use regular expression syntax.
    
          Learn more about valid operators and expressions here:
          http://code.google.com/apis/analytics/docs/gdata/gdataReference.html#filtering
          
          The ``filters`` input accepts this data as a list of lists like so. Please
          note that order matters, especially when using boolean operators (see
          below). 
          
            [
              ['browser', '=~', 'Firefox', 'AND'], # Regular expression match on 'Firefox'
              ['browser', '=~', 'Internet (Explorer|Exploder)', 'OR'],
              ['city', '=@', 'York', 'OR'], # All cities with York as a substring
              ['state', '!=', 'California', 'AND'], # Everything but California
              ['timeOnPage', '<', '10'], # Reject results where timeonpage < 10sec
            ]
            
          Filters can be combined with AND boolean logic as well as with OR 
          boolean logic. When using both operators, the OR operator has higher 
          precendence. When you are using more than one filter, please specify
          a fourth item in your list 'AND' or 'OR' to explicitly spell out the
          filters' relationships:
          
          For example, this filter selects data from the United States from the
          browser Firefox.
          
          [
            ['country', '==', 'United States', 'OR'],
            ['browser', '=@', 'FireFox'],
          ]
          
          This filter selects data from either the United States or Canada.
          
          [
            ['country', '==', 'United States', 'AND'],
            ['country', '==', 'Canada'],
          ]
          
          The first filter limits results to cities starting with 'L' and ending 
          with 'S'. The second limits results to browsers starting with 'Fire' 
          and the cities starting with 'L':
          
          [
            ['city', '=~', '^L.*S$']
          ]
          
          [
            ['city', '=~', '^L', 'AND'],
            ['browser', '=~', '^Fire']
          ]
    
        ``start_index``
          The first row to return, starts at 1. This is useful for paging in combination with
          max_results, and also to get results past row 1000 (Google Data does not return
          more than 1000 results at once)
          
        ``max_results``
          Number of results to return.
          
        """
        path = '/analytics/feeds/data'

        if start_date > end_date:
            raise GoogleAnalyticsClientError('Date orders are reversed')

        data = {
            'ids': self.table_id,
            'start-date': start_date.strftime('%Y-%m-%d'),
            'end-date': end_date.strftime('%Y-%m-%d'),
        }

        if start_index > 0:
            data['start-index'] = str(start_index)

        if max_results > 0:
            data['max-results'] = str(max_results)

        if dimensions:
            data['dimensions'] = ",".join(['ga:' + d for d in dimensions])

        data['metrics'] = ",".join(['ga:' + m for m in metrics])

        if sort:
            _sort = []
            for s in sort:
                pre = 'ga:'
                if s[0] == '-':
                    pre = '-ga:'
                    s = s[1:]
                _sort.append(pre + s)
            data['sort'] = ",".join(_sort)

        if filters:
            filter_string = self.process_filters(filters)
            data['filters'] = filter_string

        data = urllib.urlencode(data)
        response = self.connection.make_request('GET', path=path, data=data)
        raw_xml = response.read()
        processed_data = DataSet(raw_xml)
        return processed_data

    def process_filters(self, filters):
        processed_filters = []
        multiple_filters = False
        if len(filters) > 1:
            multiple_filters = True
        for filt in filters:
            if len(filt) < 3:
                continue
            if len(filt) == 3:
                name, operator, expression = filt
                if multiple_filters:
                    comb = 'AND'
                else:
                    comb = ''
            elif len(filt) == 4:
                name, operator, expression, comb = filt
                if comb != 'AND' and comb != 'OR':
                    comb == 'AND'

            # Reject any filters with invalid operators
            if operator not in filter_operators:
                continue

            name = 'ga:' + name

            # Mapping to GA's boolean operators
            if comb == 'AND': comb = ';'
            if comb == 'OR': comb = ','

            # These three characters are special and must be escaped
            if '\\' in expression:
                expression = expression.replace('\\', '\\\\')
            if ',' in expression:
                expression = expression.replace(',', '\,')
            if ';' in expression:
                expression = expression.replace(';', '\;')

            processed_filters.append("".join([name, operator, expression, comb]))
        filter_string = "".join(processed_filters)

        # Strip any trailing boolean symbols
        if filter_string:
            if filter_string[-1] == ';' or filter_string[-1] == ',':
                filter_string = filter_string[:-1]
        return filter_string

########NEW FILE########
__FILENAME__ = config
import ConfigParser
import os.path

def get_configuration():
    home_directory = os.path.expanduser('~')
    config_file = os.path.join(home_directory, '.pythongoogleanalytics')
    if not os.path.exists(config_file):
        return None
    config = ConfigParser.RawConfigParser()
    config.read(config_file)
    return config


def get_google_credentials():
    config = get_configuration()
    if not config:
        return None, None
    google_account_email = config.get('Credentials', 'google_account_email')
    google_account_password = config.get('Credentials', 'google_account_password')
    return google_account_email, google_account_password


def get_valid_profiles():
    config = get_configuration()
    if not config:
        return None
    profile_ids = config.get('Accounts', 'test_profile_ids').split(' ')
    return profile_ids

########NEW FILE########
__FILENAME__ = connection
from googleanalytics.exception import GoogleAnalyticsClientError
from googleanalytics import config
from googleanalytics.account import Account
from xml.etree import ElementTree

import re
import urllib
import urllib2

DEBUG = False
PRETTYPRINT = True
TIMEOUT = 10

class GAConnection:
    default_host = 'https://www.google.com'
    user_agent = 'python-gapi-1.0'
    auth_token = None

    def __init__(self, google_email=None, google_password=None):
        authtoken_pat = re.compile(r"Auth=(.*)")
        path = '/accounts/ClientLogin'

        if google_email == None or google_password == None:
            google_email, google_password = config.get_google_credentials()

        data = "accountType=GOOGLE&Email=%s&Passwd=%s&service=analytics&source=%s"
        data = data % (google_email, google_password, self.user_agent)
        if DEBUG:
            print "Authenticating with %s / %s" % (google_email, google_password)
        response = self.make_request('POST', path=path, data=data)
        auth_token = authtoken_pat.search(response.read())
        self.auth_token = auth_token.groups(0)[0]

    def get_accounts(self, start_index=1, max_results=None):
        path = '/analytics/feeds/accounts/default'
        data = {'start-index': start_index, }
        if max_results:
            data['max-results'] = max_results
        data = urllib.urlencode(data)
        response = self.make_request('GET', path, data=data)
        raw_xml = response.read()
        xml_tree = ElementTree.fromstring(raw_xml)
        account_list = []
        accounts = xml_tree.getiterator('{http://www.w3.org/2005/Atom}entry')
        for account in accounts:
            account_data = {
                'title': account.find('{http://www.w3.org/2005/Atom}title').text,
                'id': account.find('{http://www.w3.org/2005/Atom}id').text,
                'updated': account.find('{http://www.w3.org/2005/Atom}updated').text,
                'table_id': account.find('{http://schemas.google.com/analytics/2009}tableId').text,
            }
            for f in account.getiterator('{http://schemas.google.com/analytics/2009}property'):
                account_data[f.attrib['name']] = f.attrib['value']
            a = Account(
                connection=self,
                title=account_data['title'],
                id=account_data['id'],
                updated=account_data['updated'],
                table_id=account_data['table_id'],
                account_id=account_data['ga:accountId'],
                account_name=account_data['ga:accountName'],
                currency=account_data['ga:currency'],
                time_zone=account_data['ga:timezone'],
                profile_id=account_data['ga:profileId'],
                web_property_id=account_data['ga:webPropertyId'],
            )
            account_list.append(a)
        return account_list

    def get_account(self, profile_id):
        for account in self.get_accounts():
            if account.profile_id == profile_id:
                return account

    def make_request(self, method, path, headers=None, data=''):
        if headers == None:
            headers = {
                'User-Agent': self.user_agent,
                'Authorization': 'GoogleLogin auth=%s' % self.auth_token
            }
        else:
            headers = headers.copy()

        if DEBUG:
            print "** Headers: %s" % (headers,)

        if method == 'GET':
            path = '%s?%s' % (path, data)

        if DEBUG:
            print "** Method: %s" % (method,)
            print "** Path: %s" % (path,)
            print "** Data: %s" % (data,)
            print "** URL: %s" % (self.default_host + path)

        if PRETTYPRINT:
            # Doesn't seem to work yet...
            data += "&prettyprint=true"

        if method == 'POST':
            request = urllib2.Request(self.default_host + path, data, headers)
        elif method == 'GET':
            request = urllib2.Request(self.default_host + path, headers=headers)

        try:
            response = urllib2.urlopen(request, timeout=TIMEOUT)
        except urllib2.HTTPError, e:
            raise GoogleAnalyticsClientError(e)
        return response

########NEW FILE########
__FILENAME__ = data
import datetime
import time
from xml.etree import ElementTree

data_converters = {
   'integer': int,
}

class DataSet(list):
    """docstring for DataSet"""

    def __init__(self, raw_xml):
        list.__init__(self)
        self.raw_xml = raw_xml
        xml_tree = ElementTree.fromstring(self.raw_xml)
        self.id = xml_tree.find('{http://www.w3.org/2005/Atom}id').text
        self.title = xml_tree.find('{http://www.w3.org/2005/Atom}title').text
        self.totalResults = int(xml_tree.find('{http://a9.com/-/spec/opensearch/1.1/}totalResults').text)
        self.startIndex = int(xml_tree.find('{http://a9.com/-/spec/opensearch/1.1/}startIndex').text)
        self.itemsPerPage = int(xml_tree.find('{http://a9.com/-/spec/opensearch/1.1/}itemsPerPage').text)

        endDate = xml_tree.find('{http://schemas.google.com/analytics/2009}endDate').text
        self.endDate = datetime.date.fromtimestamp(time.mktime(time.strptime(endDate, '%Y-%m-%d')))
        startDate = xml_tree.find('{http://schemas.google.com/analytics/2009}startDate').text
        self.startDate = datetime.date.fromtimestamp(time.mktime(time.strptime(startDate, '%Y-%m-%d')))

        aggregates = xml_tree.find('{http://schemas.google.com/analytics/2009}aggregates')
        aggregate_metrics = aggregates.findall('{http://schemas.google.com/analytics/2009}metric')
        self.aggregates = []
        for m in aggregate_metrics:
            metric = Metric(**m.attrib)
            setattr(self, metric.name, metric)
            self.aggregates.append(metric)

        dataSource = xml_tree.find('{http://schemas.google.com/analytics/2009}dataSource')
        self.tableId = dataSource.find('{http://schemas.google.com/analytics/2009}tableId').text
        self.tableName = dataSource.find('{http://schemas.google.com/analytics/2009}tableName').text
        properties = dataSource.findall('{http://schemas.google.com/analytics/2009}property')
        for property in properties:
            setattr(self, property.attrib['name'].replace('ga:', ''), property.attrib['value'])

        entries = xml_tree.getiterator('{http://www.w3.org/2005/Atom}entry')
        for entry in entries:
            dp = DataPoint(entry)
            self.append(dp)

    @property
    def list(self):
        return [[[d.value for d in dp.dimensions], [m.value for m in dp.metrics]] for dp in self]

    @property
    def tuple(self):
        return tuple(map(tuple, self.list))


class DataPoint(object):
    """DataPoint takes an `entry` from the xml response and creates `Dimension` and `Metric`
    objects in the order they are returned. It has the the dimensions and metrics available 
    directly as object attributes as well as stored in the `metrics` and `dimensions` array attributes.
    """
    def __init__(self, entry):
        self.title = entry.find('{http://www.w3.org/2005/Atom}title').text
        metrics = entry.findall('{http://schemas.google.com/analytics/2009}metric')
        self.metrics = []
        for m in metrics:
            metric = Metric(**m.attrib)
            setattr(self, metric.name, metric.value)
            self.metrics.append(metric)

        dimensions = entry.findall('{http://schemas.google.com/analytics/2009}dimension')
        self.dimensions = []
        for d in dimensions:
            dimension = Dimension(**d.attrib)
            setattr(self, dimension.name, dimension.value)
            self.dimensions.append(dimension)


class Dimension(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, unicode(v.replace('ga:', '')))


class Metric(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, unicode(v.replace('ga:', '')))
        if self.type in data_converters:
            self.value = data_converters[self.type](self.value)


########NEW FILE########
__FILENAME__ = exception
class GoogleAnalyticsClientError(Exception):
    """
    General Google Analytics error (error accessing GA)
    """

    def __init__(self, reason):
        self.reason = reason

    def __repr__(self):
        return 'GAError: %s' % self.reason

    def __str__(self):
        return 'GAError: %s' % self.reason

########NEW FILE########
__FILENAME__ = tests
import datetime
import unittest

import googleanalytics
from googleanalytics.exception import GoogleAnalyticsClientError
from googleanalytics import config

class GoogleAnalyticsTest(unittest.TestCase):
    def setUp(self):
        self.connection = googleanalytics.Connection()
        self.valid_profile_ids = config.get_valid_profiles()
        self.end_date = datetime.date.today()
        self.start_date = self.end_date - datetime.timedelta(30)

    def test_goodconnection(self):
        assert self.connection.auth_token is not None

    def test_badconnection(self):
        Connection = googleanalytics.Connection
        try:
            connection = Connection('clintecker@gmail.com', 'fakefake')
        except GoogleAnalyticsClientError, e:
            assert str(e.reason) == "HTTP Error 403: Forbidden"

    def test_accountlist(self):
        for c in range(1, len(self.valid_profile_ids)):
            accounts = self.connection.get_accounts(max_results=c)
            assert len(accounts) == c

    def test_bad_date_order(self):
        start_date = datetime.date(2009, 02, 21)
        end_date = datetime.date(2009, 02, 20)
        account = self.connection.get_account(self.valid_profile_ids[0])
        try:
            data = account.get_data(start_date=start_date, end_date=end_date, metrics=['pageviews'])
        except GoogleAnalyticsClientError, e:
            assert str(e.reason) == "Date orders are reversed"

    def test_dimensions_basic_get_data(self):
        for profile_id in self.valid_profile_ids:
            account = self.connection.get_account(profile_id)
            data = account.get_data(self.start_date, self.end_date, metrics=['pageviews'], dimensions=['browser'])
            assert len(data) > 0
            data = account.get_data(self.start_date, self.end_date, metrics=['pageviews'], dimensions=['pagePath'])
            assert len(data) > 0

    def test_dimensions_basic_get_data_output(self):
        for profile_id in self.valid_profile_ids:
            account = self.connection.get_account(profile_id)
            data = account.get_data(self.start_date, self.end_date, metrics=['pageviews'], dimensions=['browser'], sort=['-pageviews'])
            assert len(data) > 0
            assert isinstance(data.list, list)
            assert isinstance(data.list[0], list)
            assert isinstance(data.tuple, tuple)
            assert isinstance(data.tuple[0], tuple)

    def test_basic_filter(self):
        filters = [
            ['country', '==', 'United States'],
        ]
        account = googleanalytics.account.Account()
        filter_string = account.process_filters(filters)
        assert filter_string == 'ga:country==United States'

    def test_filter_escaping(self):
        filters = [
            ['country', '==', 'United,States'],
        ]
        account = googleanalytics.account.Account()
        filter_string = account.process_filters(filters)
        assert filter_string == 'ga:country==United\,States'

        filters = [
            ['country', '==', 'United\States'],
        ]
        filter_string = account.process_filters(filters)
        assert filter_string == 'ga:country==United\\\\States'

        filters = [
            ['country', '==', 'Uni,tedSt,ates'],
        ]
        filter_string = account.process_filters(filters)
        assert filter_string == 'ga:country==Uni\,tedSt\,ates'

        filters = [
            ['country', '==', 'Uni,tedSt;at,es'],
        ]
        filter_string = account.process_filters(filters)
        assert filter_string == 'ga:country==Uni\,tedSt\;at\,es'

    def test_bad_operator_rejection(self):
        filters = [
            ['country', '@@', 'United,States'],
        ]
        account = googleanalytics.account.Account()
        filter_string = account.process_filters(filters)
        assert filter_string == ''

    def test_multiple_filters(self):
        filters = [
            ['country', '==', 'United States', 'AND'],
            ['country', '==', 'Canada']
        ]
        account = googleanalytics.account.Account()
        filter_string = account.process_filters(filters)
        assert filter_string == 'ga:country==United States;ga:country==Canada'

        filters = [
            ['city', '=~', '^L', 'AND'],
            ['browser', '=~', '^Fire']
        ]
        filter_string = account.process_filters(filters)
        assert filter_string == 'ga:city=~^L;ga:browser=~^Fire'

        filters = [
            ['browser', '=~', '^Fire', 'OR'],
            ['browser', '=~', '^Internet', 'OR'],
            ['browser', '=~', '^Saf'],
        ]
        filter_string = account.process_filters(filters)
        assert filter_string == 'ga:browser=~^Fire,ga:browser=~^Internet,ga:browser=~^Saf'

    def test_multiple_filters_mix_ops(self):
        filters = [
            ['browser', '=~', 'Firefox', 'AND'],
            ['browser', '=~', 'Internet (Explorer|Exploder)', 'OR'],
            ['city', '=@', 'York', 'OR'],
            ['state', '!=', 'California', 'AND'],
            ['timeOnPage', '<', '10'],
        ]
        account = googleanalytics.account.Account()
        filter_string = account.process_filters(filters)
        assert filter_string == 'ga:browser=~Firefox;ga:browser=~Internet (Explorer|Exploder),ga:city=@York,ga:state!=California;ga:timeOnPage<10'

    def test_paging(self):
        for profile_id in self.valid_profile_ids:
            account = self.connection.get_account(profile_id)
            data = account.get_data(self.start_date, self.end_date, metrics=['pageviews'], dimensions=['pageTitle', 'pagePath'], sort=['-pageviews'])
            max_results = len(data) / 2
            if not max_results:
                print("profileId: %s does not have enough results for `test_paging`" % profile_id)
            data1 = account.get_data(self.start_date, self.end_date, metrics=['pageviews'], dimensions=['pageTitle', 'pagePath'], sort=['-pageviews'], max_results=max_results)
            assert len(data1) == max_results
            data2 = account.get_data(self.start_date, self.end_date, metrics=['pageviews'], dimensions=['pageTitle', 'pagePath'], sort=['-pageviews'], max_results=max_results, start_index=max_results)
            assert len(data2) == max_results
            for value in data1.tuple:
                assert value not in data2

    def test_multiple_dimensions(self):
        for profile_id in self.valid_profile_ids:
            account = self.connection.get_account(profile_id)
            data = account.get_data(self.start_date, self.end_date, metrics=['pageviews', 'timeOnPage', 'entrances'], dimensions=['pageTitle', 'pagePath'], max_results=10)
            for t in data.tuple:
                assert len(t) == 2
                assert len(t[0]) == 2
                assert len(t[1]) == 3

    def test_data_attributes(self):
        for profile_id in self.valid_profile_ids:
            account = self.connection.get_account(profile_id)
            metrics = ['pageviews', 'timeOnPage', 'entrances']
            dimensions = ['pageTitle', 'pagePath']
            data = account.get_data(self.start_date, self.end_date, metrics=metrics, dimensions=dimensions, max_results=10)
            assert data.startDate == self.start_date
            assert data.endDate == self.end_date
            assert len(data.aggregates) == len(metrics)
            for dp in data:
                assert len(dp.metrics) == len(metrics)
                for metric in metrics:
                    assert hasattr(dp, metric)
                assert len(dp.dimensions) == len(dimensions)
                for dimension in dimensions:
                    assert hasattr(dp, dimension)


def test_suite():
    return unittest.makeSuite(GoogleAnalyticsTest)

########NEW FILE########
