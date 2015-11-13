__FILENAME__ = esclient
from __future__ import print_function
import requests
try:
    from urllib import urlencode, quote_plus
except ImportError:
    from urllib.parse import urlencode, quote_plus

from pprint import pprint

try:
    import simplejson as json   # try the faster simplejson on old versions
except:
    import json
import logging
log = logging.getLogger(__name__)

__author__ = 'Erik-Jan van Baaren'
__all__ = ['ESClient']
__version__ = (0, 5, 8)


def get_version():
        return "%s.%s.%s" % __version__


def _utf8_encode(component):
    return component.encode("utf-8")


class ESClientException(Exception):
    pass


class ESClient:
    """ESClient is a Python library that wraps around the ElasticSearch
    REST API.

    ESClient methods will always return a hierachy of Python objects and not
    the pure JSON as returned by ElasticSearch.

    Take a look at the unit tests to see usage examples for all available API
    methods that this library implements.
    Any API calls that are not (yet) implemented by ESClient can still be used
    by using the send_request() method to directly do an HTTP request to the
    ElasticSearch API.

    """

    def __init__(self, es_url='http://localhost:9200', request_timeout=10):
        self.es_url = es_url
        self.request_timeout = request_timeout
        self.bulk_data = ''

        if self.es_url.endswith('/'):
            self.es_url = self.es_url[:-1]

        # For those that forget the http part, lets just add it
        if not self.es_url.startswith('http://'):
            self.es_url = "http://" + self.es_url
    #
    # Internal helper methods
    #

    def _make_path(self, path_components):
        """Create path from components. Empty components will be
        ignored.

        """
        path_components = map(_utf8_encode, filter(None, path_components))
        path_components = map(quote_plus, path_components)
        path = '/'.join(path_components)
        if not path.startswith('/'):
            path = '/' + path
        return path

    def _parse_json_response(self, response):
        """Convert JSON response from ElasticSearch to a hierarchy of Python
        objects and return that hierarchy.

        Throws an exception when parsing fails.

        """
        try:
            return json.loads(response)
        except:
            raise ESClientException("Unable to parse JSON response from "
                                    "ElasticSearch")

    def check_result(self, results, key, value):
        """Check if key is an element of list, and check if that element
        is equal (==) to value.

        Returns True if the key exists and is equal to given value, false
        otherwise.
        """
        if key in results:
            log.debug("Key %s found in response %s" % (key, results))
            return results[key] == value
        else:
            log.debug("Key %s not found in response %s" % (key, results))
            return False

    def send_request(self, method, path, body=None, query_string_args={},encode_json=True):
        """Make a raw HTTP request to ElasticSearch.

        You may use this method to manually do whatever is not (yet) supported
        by ESClient. This method does not return anything, but sets the class
        variable called last_response, which is the response object returned
        by the requests library.

        Arguments:
        method -- HTTP method, e.g. 'GET', 'PUT', 'DELETE', etc.
        path -- URL path
        body -- the body, as a hierachy of Python objects that is parseable
                to JSON with json.dumps()
        query_string_args -- the query string arguments, which are the
        key=value pairs after the question mark in any URL.

        """
        if query_string_args:
            path = "?".join([path, urlencode(query_string_args)])

        kwargs = { 'timeout': self.request_timeout }
        url = self.es_url + path

        if body:
            if encode_json:
                kwargs['data'] = json.dumps(body)
            else:
                kwargs['data'] = body

        if not hasattr(requests, method.lower()):
            raise ESClientException("No such HTTP Method '%s'!" %
                                    method.upper())

        self.last_response = requests.request(method.lower(), url, **kwargs)
        log.debug(self.last_response)

    def _search_operation(self, request_type, query_body=None,
                    operation_type="_search", query_string_args=None,
                    indexes=["_all"], doctypes=[]):
        """Perform a search operation. This method can be used for search and
        counting by using the operation types:
            _search, _count

        Note that you can also count with more options by using ElasticSearch's
        search_type=count, which is not yet implemented in ESClient

        Searching in ElasticSearch can be done in two ways:
        1) with a query string, by providing query_args
        2) using a full query body (JSON) by providing the query_body

        """

        indexes = ','.join(indexes)
        doctypes = ','.join(doctypes)
        path = self._make_path([indexes, doctypes, operation_type])

        self.send_request(request_type, path, body=query_body,
                            query_string_args=query_string_args)

        try:
            return self._parse_json_response(self.last_response.text)
        except:
            raise ESClientException("Was unable to parse the ElasticSearch "
            "response as JSON: \n%s", self.last_response.text)

    #
    # The API methods
    #

    def index(self, index, doctype, body, docid=None, op_type=None, parent=None, routing=None):
        """Index the supplied document.

        Options:
        index -- the index name (e.g. twitter)
        doctype -- the document types (e.g. tweet)
        body -- the body of this document
        docid -- optional document id, ElasticSearch will generate one for you if not provided
        op_type -- optional: "create" or None:
            "create": create document only if it does not exists already
            None: create document or update an existing document
        parent -- the optional parent id of this documents
        routing -- the optional routing of this document
        Returns True on success (document added/updated or already exists
        while using op_type="create") or False in all other instances.

        """
        args = dict()
        if op_type:
            args["op_type"] = op_type

        if parent:
            args["parent"] = parent

        if routing:
            args["routing"] = routing

        path = self._make_path([index, doctype, str(docid)])
        self.send_request('POST', path, body=body, query_string_args=args)
        rescode = self.last_response.status_code
        if 200 <= rescode < 300:
            return True
        elif rescode == 409 and op_type == "create":
            # If document already exists, ES returns 409
            return True
        else:
            return False

    def search(self, query_body=None, query_string_args=None,
                indexes=["_all"], doctypes=[]):
        """Perform a search operation.

        Searching in ElasticSearch can be done in two ways:
        1) with a query string, by providing query_args
        2) using a full query body (JSON) by providing
        the query_body.
        You can choose one, but not both at the same time.

        """
        if query_body and query_string_args:
            raise ESClientException("Both query_body and query_string_args" +
            "provided, please use only on at a time")
        return self._search_operation('GET', query_body=query_body,
                query_string_args=query_string_args, indexes=indexes,
                doctypes=doctypes)

    def scan(self, query_body=None, query_string_args=None,
              indexes=["_all"], doctypes=[], scroll="10m", size=50):
        """Perform a scan search.

        The scan search type allows to efficiently scroll a large result
        set. This method returns a scroll_id, which can be used to get
        more results with the scroll(id=scroll_id) method.

        """
        if not query_string_args:
            query_string_args = {}

        query_string_args["search_type"] = "scan"
        query_string_args["scroll"] = scroll
        query_string_args["size"] = size

        result = self._search_operation('GET', query_body=query_body,
                query_string_args=query_string_args, indexes=indexes,
                doctypes=doctypes)

        return result["_scroll_id"]

    def scroll(self, scroll_id, scroll_time="10m"):
        """Get the next batch of results from a scan search.

        ElasticSearch will return a new scroll_id to you after every
        call to scoll.
        A scroll has ended when you get no more resulst from ElasticSeach.

        Options:
        scroll_id -- the scroll id as returned by the scan method

        """
        query_string_args = {}
        query_string_args["scroll"] = scroll_time
        body = scroll_id

        self.send_request('GET', '/_search/scroll', body=body,
                query_string_args=query_string_args, encode_json=False)

        return json.loads(self.last_response.text)

    def delete_by_query(self, query_body=None, query_string_args=None,
                indexes=["_all"], doctypes=[]):
        """Delete based on a search operation.

        Searching in ElasticSearch can be done in two ways:
        1) with a query string, by providing query_args
        2) using a full query body (JSON) by providing
        the query_body.
        You can choose one, but not both at the same time.

        """
        return self._search_operation('DELETE', query_body=query_body,
                query_string_args=query_string_args, indexes=indexes,
                doctypes=doctypes, operation_type='_query')

    def count(self, query_body=None, query_string_args=None,
                indexes=["_all"], doctypes=[]):
        """Count based on a search operation. The query is optional, and when
        not provided, it will use match_all to count all the docs.

        Searching in ElasticSearch can be done in two ways:
        1) with a query string, by providing query_args
        2) using a full query body (JSON) by providing
        the query_body.
        You can choose one, but not both at the same time.

        """
        return self._search_operation('GET', query_body=query_body,
                query_string_args=query_string_args, indexes=indexes,
                doctypes=doctypes, operation_type='_count')

    def get(self, index, doctype, docid, fields=None):
        """Get document from the index.

        You need to supply an index, doctype and id. Optionally, you can
        list the fields that you want to retrieve, e.g.:
        fields=['name','address']

        """
        args = dict()
        if fields:
            fields = ",".join(fields)
            args['fields'] = fields

        path = self._make_path([index, doctype, str(docid)])
        self.send_request('GET', path, query_string_args=args)
        return self._parse_json_response(self.last_response.text)

    def mget(self, index, doctype, ids, fields=None):
        """Perform a multi get.

        Although ElasticSearch supports it, this method does not allow you to
        specify the index and/or fields per id. So you can only specify the
        index and fields once and this will be applied to all document id's
        you want to fetch.

        Arguments:
            index -- the index name
            doctype -- the document type
            ids -- a list of ids to fetch
            fields -- option list of fields to return

        """
        path = self._make_path([index, doctype, '_mget'])
        docs = []
        for id in ids:
            doc = {'_id': id}
            if fields:
                doc['fields'] = fields
            docs.append(doc)
        body = {'docs': docs}
        self.send_request('GET', path, body=body)
        return self._parse_json_response(self.last_response.text)

    def delete(self, index, doctype, docid):
        """Delete document from index.

        Returns true if the document was found and false otherwise.

        """
        path = self._make_path([index, doctype, str(docid)])
        self.send_request('DELETE', path)
        resp = json.loads(self.last_response.text)
        return self.check_result(resp, 'found', True)

    """
    Bulk API
    """
    def _bulk_make_param(self, index, doctype, docid, op_type):
        """Return the bulk format data."""
        return json.dumps({op_type: {'_index': index, '_type': doctype, '_id': docid}}) + '\n'

    def bulk_index(self, index, doctype, body, docid, op_type='index'):
        """Bulk index the supplied document. You can call this method repeatedly
        to add actions to the bulk request and finally call bulk_push() to fire the
        complete bulk request."""
        data = self._bulk_make_param(index, doctype, docid, op_type) + json.dumps(body) + '\n'
        self.bulk_data += data

    def bulk_delete(self, index, doctype, docid):
        """Bulk delete document from index. You can call this method repeatedly
        to add actions to the bulk request and finally call bulk_push() to fire the
        complete bulk request."""
        data = self._bulk_make_param(index, doctype, docid, 'delete')
        self.bulk_data += data

    def bulk_push(self):
        """Make a raw HTTP bulk request to ElasticSearch. All actions added with
        bulk_index() and bulk_delete() will be send to ElasticSearch.
        Returns true if the index was deleted and false otherwise.

        """
        path = self._make_path(['_bulk'])
        self.send_request('POST', path, body=self.bulk_data, encode_json=False)
        self.bulk_data = ''
        rescode = self.last_response.status_code
        if 200 <= rescode < 300:
            return True
        else:
            return False

    """
    Indices API
    """
    def create_index(self, index, body=None):
        """Create an index.

        You have to supply the optional settings and mapping yourself.

        """
        path = self._make_path([index])
        self.send_request('PUT', path, body=body)
        resp = json.loads(self.last_response.text)
        return self.check_result(resp, 'acknowledged', True)

    def delete_index(self, index):
        """Delete an entire index.

        Returns true if the index was deleted and false otherwise.

        """
        path = self._make_path([index])
        self.send_request('DELETE', path)
        resp = json.loads(self.last_response.text)
        return self.check_result(resp, 'acknowledged', True)

    def index_exists(self, index):
        """Check if index exists.

        Returns true if the index exists, false otherwise.

        """
        path = self._make_path([index])
        self.send_request('HEAD', path)
        if self.last_response.status_code == 200:
            return True
        else:
            return False

    def refresh(self, index):
        """Refresh index.

        Returns True on success, false otherwise.

        """
        path = self._make_path([index, '_refresh'])
        self.send_request('POST', path)
        return True

    def create_alias(self, alias, indexes):
        """Create an alias for one or more indexes.

        Arguments:
        alias -- the alias name
        indexes -- a list of indexes that this alias spans over

        """
        query = {}
        query['actions'] = []
        for index in indexes:
            query['actions'].append({"add": {"index": index, "alias": alias}})

        path = self._make_path(['_aliases'])
        self.send_request('POST', path, body=query)
        resp = json.loads(self.last_response.text)
        return self.check_result(resp, 'ok', True)

    def delete_alias(self, alias, indexes):
        """delete an alias.

        Arguments:
        alias -- the alias name to delete
        indexes -- a list of indexes from which to delete the alias

        """
        query = {}
        query['actions'] = []
        for index in indexes:
            query['actions'].append({"delete": {"index": index, "alias": alias}})

        path = self._make_path(['_aliases'])
        self.send_request('POST', path, body=query)
        resp = json.loads(self.last_response.text)
        return self.check_result(resp, 'ok', True)


    def open_index(self, index):
        """Open a closed index.

        Opening a closed index will make that index go through the normal
        recover process.

        Returns True on success, False of failure.

        """
        path = self._make_path([index, '_open'])
        self.send_request('POST', path)
        resp = json.loads(self.last_response.text)
        return self.check_result(resp, 'acknowledged', True)

    def close_index(self, index):
        """Close an index. A closed index has almost no overhead on the
        cluster except for maintaining its metadata. A closed index is
        blocked for reading and writing.

        Returns True on success, False of failure.
        """
        path = self._make_path([index, '_close'])
        self.send_request('POST', path)
        resp = json.loads(self.last_response.text)
        return self.check_result(resp, 'acknowledged', True)

    def status(self, indexes=['_all']):
        """Retrieve the status of one or more indices.

        Returns the JSON response converted to a hierachy of Python objects.

        """
        path = self._make_path([','.join(indexes), '_status'])
        self.send_request('GET', path)
        return self._parse_json_response(self.last_response.text)

    def flush(self, indexes=['_all'], refresh=False):
        """Flush one or more indexes.

        Flush frees memory from the index by flushing data to the index
        storage and clearing the internal transaction log. There is
        usually no need to use this function manually though.

        """
        path = self._make_path([','.join(indexes), '_flush'])
        args = {}
        if refresh:
            args['refresh'] = "true"
        self.send_request('POST', path, query_string_args=args)
        return True

    def get_mapping(self, indexes=['_all'], doctypes=[]):
        """Get mapping(s).

        You can get mappings for multiple indexes and/or multiple
        types.

        Arguments:
        indexes -- optional list of indexes
        types -- optional list of types

        """

        # TODO: find out if you can get a mapping for multiple indexes
        # and multiple types at the same time
        path = self._make_path([','.join(indexes), ','.join(doctypes),
                                '_mapping'])
        self.send_request('GET', path)
        return self._parse_json_response(self.last_response.text)

    def put_mapping(self, mapping, doctype, indexes=['_all']):
        """Register a mapping definition for a specific type. You can
        register a mapping for one index, multiple indexes or even
        all indexes (the default).

        Arguments:
        indexes -- optional list of indexes (defaults to _all)
        type -- the type you want this mapping to apply to
        mapping -- a hierachy of Python object that can be converted to
        a JSON document

        """
        path = self._make_path([','.join(indexes), doctype, '_mapping'])
        self.send_request('PUT', path=path, body=mapping)
        return self._parse_json_response(self.last_response.text)

    #Cluster related API

    def get_health(self, indexes=[]):
        path = self._make_path(['_cluster', 'health', ','.join(indexes)])
        self.send_request('GET', path=path)
        resp = json.loads(self.last_response.text)
        return resp["status"]


if __name__ == '__main__':
    print("This is a library, it is not intended to be started by itself.")

########NEW FILE########
__FILENAME__ = test_esclient
import esclient
import unittest

class TestESClient(unittest.TestCase):
    """Test all API methods implemented in esclient library"""

    @classmethod
    def setUpClass(self):
        """Create an ESClient"""
        self.es = esclient.ESClient()

        """Delete the test schema, if any. This will prevent any errors
        due to the schema already existing """
        print("Deleting test indexes, if any")
        self.es.delete_index("contacts_esclient_test")
        self.es.delete_index("contacts_esclient_test2")

    def setUp(self):
        """ Create a test schema once """
        body = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }
        self.assertTrue(self.es.create_index('contacts_esclient_test', body))
        self.assertFalse(self.es.create_index('contacts_esclient_test', body))

        self.assertTrue(self.es.create_index('contacts_esclient_test2', body))
        self.assertFalse(self.es.create_index('contacts_esclient_test2', body))


        """ Index some test data """
        data = {"name": "Joe Tester","age": 21, "sex": "male"}
        self.assertTrue(self.es.index("contacts_esclient_test", "person", body=data,
                                        docid=1))
        data = {"name": "Joe Schmoe","age": 17, "sex": "male"}
        self.assertTrue(self.es.index("contacts_esclient_test", "person", body=data,
                                        docid=2))

        self.assertTrue(self.es.refresh('contacts_esclient_test'))

    def tearDown(self):
        """docstring for tearDownClass"""

        """Delete the test schemas"""
        self.assertTrue(self.es.delete_index("contacts_esclient_test"))
        self.assertTrue(self.es.delete_index("contacts_esclient_test2"))

    def test_open_close_index(self):
        """docstring for test_open_index"""
        self.assertTrue(self.es.close_index('contacts_esclient_test'))
        self.assertTrue(self.es.open_index('contacts_esclient_test'))

    def test_index_api(self):
        data = {"name": "Jane Tester","age": 23, "sex": "female"}
        self.assertTrue(self.es.index("contacts_esclient_test", "person", body=data,
                        docid=3))
        """
        Again, now with op_type='create', meaning: only index when
        the document id does not exist yet
        """
        self.assertTrue(self.es.index("contacts_esclient_test", "person", body=data,
                        docid="3", op_type="create"))

        """ Ensure that the document has really been indexed """
        result = self.es.get('contacts_esclient_test', 'person', 3)
        try:
            found = result['exists']
        except KeyError:
            found = result['found']
        self.assertTrue(found)

    def test_get_api(self):
        result = self.es.get('contacts_esclient_test', 'person', 1)
        try:
            found = result['exists']
        except KeyError:
            found = result['found']
        self.assertTrue(found)

    def test_mget_api(self):
        """docstring for test_mget_api"""
        result = self.es.mget('contacts_esclient_test', 'person',
                              ids=[1,2], fields=['name','age'])

        for doc in result['docs']:
            self.assertTrue(doc['_id'] == '1' or  doc['_id'] == '2')

    def test_search_queryargs_api(self):
        """docstring for test_search_api"""
        query_string_args = {
                "q": "name:Joe",
                "sort":"age",
                "timeout":10,
                "fields": "id,name,age"
                }
        result = self.es.search(query_string_args=query_string_args,
                                indexes=['contacts_esclient_test'])
        self.assertEqual(result['hits']['total'], 2)

    def test_search_body_api(self):
        """docstring for test_search_body_api"""
        query_body = {
            "query": {
               "term": {"name": "joe"}
            }
        }
        result = self.es.search(query_body=query_body,
                                indexes=['contacts_esclient_test'])
        self.assertEqual(result['hits']['total'], 2)

    def test_scan_scroll_api(self):
        query_body= {
            "query": {
                "match_all": {}
            }
        }
        scroll_id = self.es.scan(query_body=query_body, indexes=['contacts_esclient_test'], size=1)

        total_docs = 0
        while True:
            count = 0
            res = self.es.scroll(scroll_id)
            for hit in res['hits']['hits']:
                total_docs += 1
                count += 1
            if count == 0:
                break

        self.assertEqual(total_docs, 2)

    @unittest.skip("demonstrating skipping")
    def test_deletebyquery_querystring_api(self):
        """Delete documents with a query using querystring option"""
        query_string_args = {
                "q": "name:Joe",
                "sort":"age",
                "timeout":10,
                "fields": "id,name,age"
                }
        result = self.es.delete_by_query(query_string_args=query_string_args,
                                         indexes=['contacts_esclient_test'])
        self.assertTrue(result['ok'])
        self.assertTrue(self.es.refresh('contacts_esclient_test'))
        result = self.es.get('contacts_esclient_test', 'person', 1)
        self.assertFalse(result['found'])
        result = self.es.get('contacts_esclient_test', 'person', 1)
        self.assertFalse(result['found'])

    @unittest.skip("demonstrating skipping")
    def test_deletebyquery_body_api(self):
        """Delete documents with a query in a HTTP body"""
        query_body = { "term": {"name": "joe"}}
        result = self.es.delete_by_query(query_body=query_body,
                                indexes=['contacts_esclient_test'],
                                doctypes=['person'])
        self.assertTrue(result['ok'])
        self.assertTrue(self.es.refresh('contacts_esclient_test'))
        result = self.es.get('contacts_esclient_test', 'person', 1)
        self.assertFalse(result['found'])
        result = self.es.get('contacts_esclient_test', 'person', 1)
        self.assertFalse(result['found'])

    def test_count_api(self):
        """docstring for count_api"""
        result = self.es.count(indexes=['contacts_esclient_test'])
        """ We can be sure there are at least two docs indexed """
        self.assertTrue(result['count'] > 1)

    def test_delete_api(self):
        """Delete a document"""
        result = self.es.delete('contacts_esclient_test', 'person', 1)
        result = self.es.get('contacts_esclient_test', 'person', 1)
        try:
            found = result['exists']
        except KeyError:
            found = result['found']

        self.assertFalse(found)

    def test_create_delete_alias_api(self):
        self.es.create_alias('contacts_alias', ['contacts_esclient_test',
                                                'contacts_esclient_test2'])
        self.es.delete_alias('contacts_alias', ['contacts_esclient_test',
                                                'contacts_esclient_test2'])
    @unittest.skip("needs fixing")
    def test_status(self):
        """docstring for test_status"""
        result = self.es.status(indexes=['contacts_esclient_test'])
        self.assertTrue(result['ok'])

    def test_flush(self):
        """docstring for test_flush"""
        self.assertTrue(self.es.flush(['contacts_esclient_test'], refresh=True))

    def test_get_mapping(self):
        """docstring for test_get_mapping"""
        m = self.es.get_mapping(indexes=['contacts_esclient_test'])
        self.assertIn("contacts_esclient_test", m)

    @unittest.skip("needs to be fixed")
    def test_put_mapping(self):
        """docstring for test_put_mapping"""
        mapping = {'persons': {'properties':{'name': {'type': 'string'}}}}
        result = self.es.put_mapping(doctype='person', mapping=mapping, indexes=['contacts_esclient_test', 'contacts_esclient_test2'])
        self.assertTrue(result['ok'])

    def test_index_exists(self):
        result = self.es.index_exists("contacts_esclient_test")
        self.assertTrue(result)

    def test_bulk(self):
        self.es.bulk_index('contacts_esclient_test', 'bulk', {'test':'test'}, 1)
        self.es.bulk_index('contacts_esclient_test', 'bulk', {'test':'test'}, 2)
        self.assertTrue(self.es.bulk_push())
        result = self.es.get('contacts_esclient_test', 'bulk', 2)
        try:
            found = result['exists']
        except KeyError:
            found = result['found']
        self.es.bulk_index('contacts_esclient_test', 'bulk', {'test':'test'}, 3)
        self.es.bulk_delete('contacts_esclient_test', 'bulk', 2)
        self.assertTrue(self.es.bulk_push())

        result = self.es.get('contacts_esclient_test', 'bulk', 2)
        try:
            found = result['exists']
        except KeyError:
            found = result['found']

        result = self.es.get('contacts_esclient_test', 'bulk', 3)
        try:
            found = result['exists']
        except KeyError:
            found = result['found']

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
