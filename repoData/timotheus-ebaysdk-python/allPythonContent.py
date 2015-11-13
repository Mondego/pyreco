__FILENAME__ = config
# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import yaml

from ebaysdk import log

class Config(object):
    """Config Class for all APIs connections

    >>> c = Config(domain='api.ebay.com')
    >>> print(c.file())
    ebay.yaml
    >>> c.set('fname', 'tim')
    >>> c.get('fname')
    'tim'
    >>> c.get('missingkey', 'defaultvalue')
    'defaultvalue'
    >>> c.set('number', 22)
    >>> c.get('number')
    22
    """

    def __init__(self, domain, connection_kwargs=dict(), config_file='ebay.yaml'):
        self.config_file=config_file
        self.domain=domain
        self.values=dict()
        self.config_file_used=[]
        self.connection_kwargs=connection_kwargs

        # populate defaults        
        self._populate_yaml_defaults()

    def _populate_yaml_defaults(self):
        "Returns a dictionary of YAML defaults."

        # check for absolute path
        if self.config_file and os.path.exists(self.config_file):
            self.config_file_used=self.config_file
            fhandle = open(self.config_file, "r")
            dataobj = yaml.load(fhandle.read())

            for k, val in dataobj.get(self.domain, {}).items():
                self.set(k, val)

            return self

        # check other directories
        dirs = ['.', os.path.expanduser('~'), '/etc']
        for mydir in dirs:
            myfile = "%s/%s" % (mydir, self.config_file)

            if os.path.exists(myfile):
                self.config_file_used=myfile

                fhandle = open(myfile, "r")
                dataobj = yaml.load(fhandle.read())

                for k, val in dataobj.get(self.domain, {}).items():
                    self.set(k, val)

                return self

    def file(self):
        return self.config_file_used

    def get(self, cKey, defaultValue=None):
        #log.debug('get: %s=%s' % (cKey, self.values.get(cKey, defaultValue)))
        return self.values.get(cKey, defaultValue)

    def set(self, cKey, defaultValue, force=False):
        
        if force:
            #log.debug('set (force): %s=%s' % (cKey, defaultValue))
            self.values.update({cKey: defaultValue})
                    
        elif cKey in self.connection_kwargs and self.connection_kwargs[cKey] is not None:
            #log.debug('set: %s=%s' % (cKey, self.connection_kwargs[cKey]))
            self.values.update({cKey: self.connection_kwargs[cKey]})

        # otherwise, use yaml default and then fall back to
        # the default set in the __init__()
        else:
            if not cKey in self.values:
                #log.debug('set: %s=%s' % (cKey, defaultValue))
                self.values.update({cKey: defaultValue})
            else:
                pass

########NEW FILE########
__FILENAME__ = connection
# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

from ebaysdk import log

import re
import json
import time
import uuid

from requests import Request, Session
from requests.adapters import HTTPAdapter

from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError

from ebaysdk import set_stream_logger, UserAgent
from ebaysdk.utils import getNodeText as getNodeTextUtils
from ebaysdk.utils import dict2xml, xml2dict, getValue
from ebaysdk.exception import ConnectionError, ConnectionResponseError

HTTP_SSL = {
    False: 'http',
    True: 'https',
}

class BaseConnection(object):
    """Base Connection Class.

    Doctests:
    >>> d = { 'list': ['a', 'b', 'c']}
    >>> print(dict2xml(d, listnames={'': 'list'}))
    <list>a</list><list>b</list><list>c</list>
    >>> d2 = {'node': {'@attrs': {'a': 'b'}, '#text': 'foo'}}
    >>> print(dict2xml(d2))
    <node a="b">foo</node>
    """

    def __init__(self, debug=False, method='GET',
                 proxy_host=None, timeout=20, proxy_port=80,
                 parallel=None, **kwargs):

        if debug:
            set_stream_logger()

        self.response = None
        self.request = None
        self.verb = None
        self.debug = debug
        self.method = method
        self.timeout = timeout
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

        self.proxies = dict()
        if self.proxy_host:
            proxy = 'http://%s:%s' % (self.proxy_host, self.proxy_port)
            self.proxies = {
                'http': proxy,
                'https': proxy
            }

        self.session = Session()
        self.session.mount('http://', HTTPAdapter(max_retries=3))
        self.session.mount('https://', HTTPAdapter(max_retries=3))

        self.parallel = parallel

        self._reset()

    def debug_callback(self, debug_type, debug_message):
        log.debug('type: ' + str(debug_type) + ' message' + str(debug_message))

    def v(self, *args, **kwargs):
        return getValue(self.response_dict(), *args, **kwargs)
        
    def getNodeText(self, nodelist):
        return getNodeTextUtils(nodelist)

    def _reset(self):
        self.response = None
        self.request = None
        self.verb = None
        self._request_id = None
        self._time = time.time()
        self._response_content = None
        self._response_dom = None
        self._response_obj = None
        self._response_soup = None
        self._response_dict = None
        self._response_error = None
        self._resp_body_errors = []
        self._resp_body_warnings = []
        self._resp_codes = []

    def do(self, verb, call_data=dict()):
        return self.execute(verb, call_data)

    def execute(self, verb, data=None):
        "Executes the HTTP request."
        log.debug('execute: verb=%s data=%s' % (verb, data))

        self._reset()
        self.build_request(verb, data)
        self.execute_request()        

        if self.response:
            self.process_response()
            self.error_check()

        log.debug('total time=%s' % (time.time() - self._time))
        
        return self

    def build_request(self, verb, data):
 
        self.verb = verb
        self._request_id = uuid.uuid4()

        url = "%s://%s%s" % (
            HTTP_SSL[self.config.get('https', False)],
            self.config.get('domain'),
            self.config.get('uri')
        )

        headers = self.build_request_headers(verb)
        headers.update({'User-Agent': UserAgent, 
                        'X-EBAY-SDK-REQUEST-ID': str(self._request_id)})

        request = Request(self.method, 
            url,
            data=self.build_request_data(verb, data),
            headers=headers,
        )

        self.request = request.prepare()

    def execute_request(self):

        log.debug("REQUEST (%s): %s %s" \
            % (self._request_id, self.request.method, self.request.url))
        log.debug('headers=%s' % self.request.headers)
        log.debug('body=%s' % self.request.body)

        if self.parallel:
            self.parallel._add_request(self)
            return None

        self.response = self.session.send(self.request,
            verify=False,
            proxies=self.proxies,
            timeout=self.timeout,
            allow_redirects=True
        )

        log.debug('RESPONSE (%s):' % self._request_id)
        log.debug('elapsed time=%s' % self.response.elapsed)
        log.debug('status code=%s' % self.response.status_code)
        log.debug('headers=%s' % self.response.headers)
        log.debug('content=%s' % self.response.text)      
    
    def process_response(self):
        """Post processing of the response"""
        
        if self.response.status_code != 200:
            self._response_error = self.response.reason

        # remove xml namespace
        regex = re.compile('xmlns="[^"]+"')
        self._response_content = regex.sub('', self.response.content)

    def error_check(self):
        estr = self.error()

        if estr and self.config.get('errors', True):
            log.error(estr)
            raise ConnectionError(estr)

    def response_codes(self):
        return self._resp_codes

    def response_status(self):
        "Retuns the HTTP response status string."

        return self.response.reason

    def response_code(self):
        "Returns the HTTP response status code."

        return self.response.status_code

    def response_content(self):
        return self._response_content

    def response_soup(self):
        "Returns a BeautifulSoup object of the response."
        try:
            from bs4 import BeautifulStoneSoup
        except ImportError:
            from BeautifulSoup import BeautifulStoneSoup
            log.warn('DeprecationWarning: BeautifulSoup 3 or earlier is deprecated; install bs4 instead\n')

        if not self._response_soup:
            self._response_soup = BeautifulStoneSoup(
                self._response_content.decode('utf-8')
            )

        return self._response_soup

    def response_obj(self):
        return self.response_dict()

    def response_dom(self):
        "Returns the response DOM (xml.dom.minidom)."

        if not self._response_dom:
            dom = None
            content = None

            try:
                if self._response_content:
                    content = self._response_content
                else:
                    content = "<%sResponse></%sResponse>" % (self.verb, self.verb)

                dom = parseString(content)
                self._response_dom = dom.getElementsByTagName(
                    self.verb + 'Response')[0]

            except ExpatError as e:
                raise ConnectionResponseError("Invalid Verb: %s (%s)" % (self.verb, e))
            except IndexError:
                self._response_dom = dom

        return self._response_dom

    def response_dict(self):
        "Returns the response dictionary."

        if not self._response_dict and self._response_content:
            mydict = xml2dict().fromstring(self._response_content)
            self._response_dict = mydict.get(self.verb + 'Response', mydict)

        return self._response_dict

    def response_json(self):
        "Returns the response JSON."

        return json.dumps(self.response_dict())

    def _get_resp_body_errors(self):
        """Parses the response content to pull errors.

        Child classes should override this method based on what the errors in the
        XML response body look like. They can choose to look at the 'ack',
        'Errors', 'errorMessage' or whatever other fields the service returns.
        the implementation below is the original code that was part of error()
        """

        if self._resp_body_errors and len(self._resp_body_errors) > 0:
            return self._resp_body_errors

        errors = []

        if self.verb is None:
            return errors

        dom = self.response_dom()
        if dom is None:
            return errors

        return []

    def error(self):
        "Builds and returns the api error message."

        error_array = []
        if self._response_error:
            error_array.append(self._response_error)

        error_array.extend(self._get_resp_body_errors())

        if len(error_array) > 0:
            error_string = "%s: %s" % (self.verb, ", ".join(error_array))

            return error_string

        return None

########NEW FILE########
__FILENAME__ = exception
# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

class ConnectionError(Exception):
    pass

class ConnectionResponseError(Exception):
    pass

########NEW FILE########
__FILENAME__ = parallel
# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import grequests
from ebaysdk.exception import ConnectionError

class Parallel(object):
    """
    >>> from ebaysdk.finding import Connection as finding
    >>> from ebaysdk.shopping import Connection as shopping
    >>> from ebaysdk.http import Connection as html
    >>> import os
    >>> p = Parallel()
    >>> r1 = html(parallel=p)
    >>> retval = r1.execute('http://shop.ebay.com/i.html?rt=nc&_nkw=mytouch+slide&_dmpt=PDA_Accessories&_rss=1')
    >>> r2 = finding(parallel=p, config_file=os.environ.get('EBAY_YAML'))
    >>> retval = r2.execute('findItemsAdvanced', {'keywords': 'shoes'})
    >>> r3 = shopping(parallel=p, config_file=os.environ.get('EBAY_YAML'))
    >>> retval = r3.execute('FindItemsAdvanced', {'CharityID': 3897})
    >>> p.wait()
    >>> print(p.error())
    None
    >>> print(r1.response_obj().rss.channel.ttl)
    60
    >>> print(r2.response_dict().ack)
    Success
    >>> print(r3.response_obj().Ack)
    Success
    """

    def __init__(self):
        self._grequests = []
        self._requests = []
        self._errors = []

    def _add_request(self, request):
        self._requests.append(request)

    def wait(self, timeout=20):
        "wait for all of the api requests to complete"

        self._errors = []
        self._grequests = []

        try:
            for r in self._requests:
                req = grequests.request(r.request.method,
                                        r.request.url,
                                        data=r.request.body,
                                        headers=r.request.headers,
                                        verify=False,
                                        proxies=r.proxies,
                                        timeout=r.timeout,
                                        allow_redirects=True)

                self._grequests.append(req)

            gresponses = grequests.map(self._grequests)

            for idx, r in enumerate(self._requests):
                r.response = gresponses[idx]
                r.process_response()
                r.error_check()

                if r.error():
                    self._errors.append(r.error())

        except ConnectionError as e:
            self._errors.append("%s" % e)

        self._requests = []

    def error(self):
        "builds and returns the api error message"

        if len(self._errors) > 0:
            return "parallel error:\n%s\n" % ("\n".join(self._errors))

        return None

########NEW FILE########
__FILENAME__ = finditem
# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os

from ebaysdk.soa import Connection as BaseConnection
from ebaysdk.utils import to_xml, getNodeText

class Connection(BaseConnection):
    """
    Not to be confused with Finding service

    Implements FindItemServiceNextGen

    https://wiki.vip.corp.ebay.com/display/apdoc/FindItemServiceNextGen

    This class is a bit hackish, it subclasses SOAService, but removes
    SOAP support. FindItemServiceNextGen works fine with standard XML
    and lets avoid all of the ugliness associated with SOAP.

    >>> from ebaysdk.shopping import Connection as Shopping 
    >>> s = Shopping(config_file=os.environ.get('EBAY_YAML'))
    >>> retval = s.execute('FindPopularItems', {'QueryKeywords': 'Python'})
    >>> nodes = s.response_dom().getElementsByTagName('ItemID')
    >>> itemIds = [getNodeText(n) for n in nodes]
    >>> len(itemIds) > 0
    True
    >>> f = Connection(debug=False, config_file=os.environ.get('EBAY_YAML'))
    >>> records = f.find_items_by_ids(itemIds)
    >>> len(records) > 0
    True
    """

    def __init__(self, site_id='EBAY-US', debug=False, consumer_id=None, 
                 **kwargs):

        super(Connection, self).__init__(consumer_id=consumer_id,
                                         domain='apifindingcore.vip.ebay.com',
                                         app_config=None,
                                         site_id=site_id,
                                         debug=debug, **kwargs)
        
        self.config.set('domain', 'apifindingcore.vip.ebay.com')
        self.config.set('service', 'FindItemServiceNextGen', force=True)
        self.config.set('https', False)
        self.config.set('uri', "/services/search/FindItemServiceNextGen/v1", force=True)
        self.config.set('consumer_id', consumer_id)

        self.read_set = None

    def build_request_headers(self, verb):
        return {
            "X-EBAY-SOA-SERVICE-NAME": self.config.get('service', ''),
            "X-EBAY-SOA-SERVICE-VERSION": self.config.get('version', ''),
            "X-EBAY-SOA-GLOBAL-ID": self.config.get('siteid', ''),
            "X-EBAY-SOA-OPERATION-NAME": verb,
            "X-EBAY-SOA-CONSUMER-ID": self.config.get('consumer_id', ''),
            "Content-Type": "text/xml"
        }

    def findItemsByIds(self, ebay_item_ids,
         read_set=['ITEM_ID', 'TITLE', 'SELLER_NAME', 'ALL_CATS', 'ITEM_CONDITION_NEW']):

        self.read_set = read_set
        read_set_node = []

        for rtype in self.read_set:
            read_set_node.append({
                'member': {
                    'namespace': 'ItemDictionary',
                    'name': rtype
                }
            })
            
        args = {'id': ebay_item_ids, 'readSet': read_set_node}            
        self.execute('findItemsByIds', args)
        return self.mappedResponse()

    def mappedResponse(self):
        records = []

        for r in self.response_dict().get('record', []):
            mydict = dict()
            i = 0
            for values_dict in r.value:                
                for key, value in values_dict.iteritems():
                    value_data = None
                    if type(value) == list:
                        value_data = [x['value'] for x in value]
                    else:
                        value_data = value['value']

                    mydict.update({self.read_set[i]: value_data})

                    i = i+1

            records.append(mydict)

        return records                    

    def find_items_by_ids(self, *args, **kwargs):
        return self.findItemsByIds(*args, **kwargs)

    def build_request_data(self, verb, data):        
        xml = "<?xml version='1.0' encoding='utf-8'?>"
        xml += "<" + verb + "Request"
        xml += ' xmlns="http://www.ebay.com/marketplace/search/v1/services"'
        xml += '>'
        xml += to_xml(data) or ''
        xml += "</" + verb + "Request>"

        return xml


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

try:
    import xml.etree.ElementTree as ET
except:
    import cElementTree as ET # for 2.4

import re
import sys
from io import BytesIO

def to_xml(data):
    "Converts a list or dictionary to XML and returns it."

    xml = ''

    if type(data) == dict:
        xml = dict2xml(data)
    elif type(data) == list:
        xml = list2xml(data)
    else:
        xml = data

    return xml

def getValue(response_dict, *args, **kwargs):
    args_a = [w for w in args]
    first = args_a[0]
    args_a.remove(first)

    h = kwargs.get('mydict', {})
    if h:
        h = h.get(first, {})
    else:
        h = response_dict.get(first, {})

    if len(args) == 1:
        try:
            return h.get('value', None)
        except:
            return h

    last = args_a.pop()

    for a in args_a:
        h = h.get(a, {})

    h = h.get(last, {})

    try:
        return h.get('value', None)
    except:
        return h

def getNodeText(node):
    "Returns the node's text string."

    rc = []

    if hasattr(node, 'childNodes'):
        for cn in node.childNodes:
            if cn.nodeType == cn.TEXT_NODE:
                rc.append(cn.data)
            elif cn.nodeType == cn.CDATA_SECTION_NODE:
                rc.append(cn.data)

    return ''.join(rc)

class object_dict(dict):
    """object view of dict, you can
    >>> a = object_dict()
    >>> a.fish = 'fish'
    >>> a['fish']
    'fish'
    >>> a['water'] = 'water'
    >>> a.water
    'water'
    >>> a.test = {'value': 1}
    >>> a.test2 = object_dict({'name': 'test2', 'value': 2})
    >>> a.test, a.test2.name, a.test2.value
    (1, 'test2', 2)
    """
    def __init__(self, initd=None):
        if initd is None:
            initd = {}
        dict.__init__(self, initd)

    def __getattr__(self, item):
        try:
            d = self.__getitem__(item)
        except KeyError:
            return None

        if isinstance(d, dict) and 'value' in d and len(d) == 1:
            return d['value']
        else:
            return d

        # if value is the only key in object, you can omit it

    def __setattr__(self, item, value):
        self.__setitem__(item, value)

    def getvalue(self, item, value=None):
        return self.get(item, {}).get('value', value)

    def __getstate__(self):
        return list(self.items())

    def __setstate__(self, items):
        self.update(items)

class xml2dict(object):

    def __init__(self):
        pass

    def _parse_node(self, node):
        node_tree = object_dict()
        # Save attrs and text, hope there will not be a child with same name
        if node.text:
            node_tree.value = node.text
        for (k,v) in list(node.attrib.items()):
            k,v = self._namespace_split(k, object_dict({'value':v}))
            node_tree[k] = v
        #Save childrens
        for child in list(node):
            tag, tree = self._namespace_split(child.tag, self._parse_node(child))
            if  tag not in node_tree: # the first time, so store it in dict
                node_tree[tag] = tree
                continue
            old = node_tree[tag]
            if not isinstance(old, list):
                node_tree.pop(tag)
                node_tree[tag] = [old] # multi times, so change old dict to a list
            node_tree[tag].append(tree) # add the new one

        return node_tree

    def _namespace_split(self, tag, value):
        """
           Split the tag  '{http://cs.sfsu.edu/csc867/myscheduler}patients'
             ns = http://cs.sfsu.edu/csc867/myscheduler
             name = patients
        """
        result = re.compile("\{(.*)\}(.*)").search(tag)
        if result:
            value.namespace, tag = result.groups()

        return (tag,value)

    def parse(self, file):
        """parse a xml file to a dict"""
        f = open(file, 'r')
        return self.fromstring(f.read())

    def fromstring(self, s):
        """parse a string"""
        t = ET.fromstring(s)
        root_tag, root_tree = self._namespace_split(t.tag, self._parse_node(t))
        return object_dict({root_tag: root_tree})


# Basic conversation goal here is converting a dict to an object allowing
# more comfortable access. `Struct()` and `make_struct()` are used to archive
# this goal.
# See http://stackoverflow.com/questions/1305532/convert-python-dict-to-object for the inital Idea
#
# The reasoning for this is the observation that we ferry arround hundreds of dicts via JSON
# and accessing them as `obj['key']` is tiresome after some time. `obj.key` is much nicer.
class Struct(object):
    """Emulate a cross over between a dict() and an object()."""
    def __init__(self, entries, default=None, nodefault=False):
        # ensure all keys are strings and nothing else
        entries = dict([(str(x), y) for x, y in list(entries.items())])
        self.__dict__.update(entries)
        self.__default = default
        self.__nodefault = nodefault

    def __getattr__(self, name):
        """Emulate Object access.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.a
        'b'
        >>> obj.foobar
        'c'

        `hasattr` results in strange behaviour if you give a default value. This might change in the future.
        >>> hasattr(obj, 'a')
        True
        >>> hasattr(obj, 'foobar')
        True
        """
        if name.startswith('_'):
            # copy expects __deepcopy__, __getnewargs__ to raise AttributeError
            # see http://groups.google.com/group/comp.lang.python/browse_thread/thread/6ac8a11de4e2526f/
            # e76b9fbb1b2ee171?#e76b9fbb1b2ee171
            raise AttributeError("'<Struct>' object has no attribute '%s'" % name)
        if self.__nodefault:
            raise AttributeError("'<Struct>' object has no attribute '%s'" % name)
        return self.__default

    def __getitem__(self, key):
        """Emulate dict like access.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj['a']
        'b'

        While the standard dict access via [key] uses the default given when creating the struct,
        access via get(), results in None for keys not set. This might be considered a bug and
        should change in the future.
        >>> obj['foobar']
        'c'
        >>> obj.get('foobar')
        'c'
        """
        # warnings.warn("dict_accss[foo] on a Struct, use object_access.foo instead",
        #                DeprecationWarning, stacklevel=2)
        if self.__nodefault:
            return self.__dict__[key]
        return self.__dict__.get(key, self.__default)

    def get(self, key, default=None):
        """Emulate dictionary access.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.get('a')
        'b'
        >>> obj.get('foobar')
        'c'
        """
        if key in self.__dict__:
            return self.__dict__[key]
        if not self.__nodefault:
            return self.__default
        return default

    def __contains__(self, item):
        """Emulate dict 'in' functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> 'a' in obj
        True
        >>> 'foobar' in obj
        False
        """
        return item in self.__dict__

    def __bool__(self):
        """Returns whether the instance evaluates to False"""
        return bool(list(self.items()))

    def has_key(self, item):
        """Emulate dict.has_key() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.has_key('a')
        True
        >>> obj.has_key('foobar')
        False
        """
        return item in self

    def items(self):
        """Emulate dict.items() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.items()
        [('a', 'b')]
        """
        return [(k, v) for (k, v) in list(self.__dict__.items()) if not k.startswith('_Struct__')]

    def keys(self):
        """Emulate dict.keys() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.keys()
        ['a']
        """
        return [k for (k, _v) in list(self.__dict__.items()) if not k.startswith('_Struct__')]

    def values(self):
        """Emulate dict.values() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.values()
        ['b']
        """
        return [v for (k, v) in list(self.__dict__.items()) if not k.startswith('_Struct__')]

    def __repr__(self):
        return "<Struct: %r>" % dict(list(self.items()))

    def as_dict(self):
        """Return a dict representing the content of this struct."""
        return self.__dict__


def make_struct(obj, default=None, nodefault=False):
    """Converts a dict to an object, leaves objects untouched.

    Someting like obj.vars() = dict() - Read Only!

    >>> obj = make_struct(dict(foo='bar'))
    >>> obj.foo
    'bar'

    `make_struct` leaves objects alone.
    >>> class MyObj(object): pass
    >>> data = MyObj()
    >>> data.foo = 'bar'
    >>> obj = make_struct(data)
    >>> obj.foo
    'bar'

    `make_struct` also is idempotent
    >>> obj = make_struct(make_struct(dict(foo='bar')))
    >>> obj.foo
    'bar'

    `make_struct` recursively handles dicts and lists of dicts
    >>> obj = make_struct(dict(foo=dict(bar='baz')))
    >>> obj.foo.bar
    'baz'

    >>> obj = make_struct([dict(foo='baz')])
    >>> obj
    [<Struct: {'foo': 'baz'}>]
    >>> obj[0].foo
    'baz'

    >>> obj = make_struct(dict(foo=dict(bar=dict(baz='end'))))
    >>> obj.foo.bar.baz
    'end'

    >>> obj = make_struct(dict(foo=[dict(bar='baz')]))
    >>> obj.foo[0].bar
    'baz'
    >>> obj.items()
    [('foo', [<Struct: {'bar': 'baz'}>])]
    """
    if type(obj) == type(Struct):
        return obj
    if type(obj) == dict:
        struc = Struct(obj, default, nodefault)
        # handle recursive sub-dicts
        for key, val in list(obj.items()):
            setattr(struc, key, make_struct(val, default, nodefault))
        return struc
    elif type(obj) == list:
        return [make_struct(v, default, nodefault) for v in obj]
    else:
        return obj


# Code is based on http://code.activestate.com/recipes/573463/
def _convert_dict_to_xml_recurse(parent, dictitem, listnames):
    """Helper Function for XML conversion."""
    # we can't convert bare lists
    assert not isinstance(dictitem, list)

    if isinstance(dictitem, dict):
        # special case of attrs and text
        if '@attrs' in dictitem.keys():
            attrs = dictitem.pop('@attrs')
            for key, value in attrs.iteritems():
                parent.set(key, value) # TODO: will fail if attrs is not a dict
        if '#text' in dictitem.keys():
            text = dictitem.pop('#text')
            if sys.version_info[0] < 3:
                parent.text = unicode(text)
            else:
                parent.text = str(text)
        for (tag, child) in sorted(dictitem.items()):
            if isinstance(child, list):
                # iterate through the array and convert
                listparent = ET.Element(tag if tag in listnames.keys() else '')
                parent.append(listparent)
                for listchild in child:
                    item = ET.SubElement(listparent, listnames.get(tag, tag))
                    _convert_dict_to_xml_recurse(item, listchild, listnames)
            else:
                elem = ET.Element(tag)
                parent.append(elem)
                _convert_dict_to_xml_recurse(elem, child, listnames)
    elif not dictitem is None:
        if sys.version_info[0] < 3:
            parent.text = unicode(dictitem)
        else:
            parent.text = str(dictitem)


def dict2et(xmldict, roottag='data', listnames=None):
    """Converts a dict to an ElementTree.

    Converts a dictionary to an XML ElementTree Element::

    >>> data = {"nr": "xq12", "positionen": [{"m": 12}, {"m": 2}]}
    >>> root = dict2et(data)
    >>> ET.tostring(root, encoding="utf-8").replace('<>', '').replace('</>','')
    '<data><nr>xq12</nr><positionen><m>12</m></positionen><positionen><m>2</m></positionen></data>'

    Per default ecerything ins put in an enclosing '<data>' element. Also per default lists are converted
    to collecitons of `<item>` elements. But by provding a mapping between list names and element names,
    you van generate different elements::

    >>> data = {"positionen": [{"m": 12}, {"m": 2}]}
    >>> root = dict2et(data, roottag='xml')
    >>> ET.tostring(root, encoding="utf-8").replace('<>', '').replace('</>','')
    '<xml><positionen><m>12</m></positionen><positionen><m>2</m></positionen></xml>'

    >>> root = dict2et(data, roottag='xml', listnames={'positionen': 'position'})
    >>> ET.tostring(root, encoding="utf-8").replace('<>', '').replace('</>','')
    '<xml><positionen><position><m>12</m></position><position><m>2</m></position></positionen></xml>'

    >>> data = {"kommiauftragsnr":2103839, "anliefertermin":"2009-11-25", "prioritaet": 7,
    ... "ort": u"Hücksenwagen",
    ... "positionen": [{"menge": 12, "artnr": "14640/XL", "posnr": 1},],
    ... "versandeinweisungen": [{"guid": "2103839-XalE", "bezeichner": "avisierung48h",
    ...                          "anweisung": "48h vor Anlieferung unter 0900-LOGISTIK avisieren"},
    ... ]}

    >>> print ET.tostring(dict2et(data, 'kommiauftrag',
    ... listnames={'positionen': 'position', 'versandeinweisungen': 'versandeinweisung'}),
    ... encoding="utf-8").replace('<>', '').replace('</>','')
    ...  # doctest: +SKIP
    '''<kommiauftrag>
    <anliefertermin>2009-11-25</anliefertermin>
    <positionen>
        <position>
            <posnr>1</posnr>
            <menge>12</menge>
            <artnr>14640/XL</artnr>
        </position>
    </positionen>
    <ort>H&#xC3;&#xBC;cksenwagen</ort>
    <versandeinweisungen>
        <versandeinweisung>
            <bezeichner>avisierung48h</bezeichner>
            <anweisung>48h vor Anlieferung unter 0900-LOGISTIK avisieren</anweisung>
            <guid>2103839-XalE</guid>
        </versandeinweisung>
    </versandeinweisungen>
    <prioritaet>7</prioritaet>
    <kommiauftragsnr>2103839</kommiauftragsnr>
    </kommiauftrag>'''
    """

    if not listnames:
        listnames = {}
    root = ET.Element(roottag)
    _convert_dict_to_xml_recurse(root, xmldict, listnames)
    return root


def list2et(xmllist, root, elementname):
    """Converts a list to an ElementTree.

        See also dict2et()
    """

    basexml = dict2et({root: xmllist}, 'xml', listnames={root: elementname})
    return basexml.find(root)


def dict2xml(datadict, roottag='', listnames=None, pretty=False):
    """
    Converts a dictionary to an UTF-8 encoded XML string.
    See also dict2et()
    """
    if isinstance(datadict, dict) and len(datadict):
        root = dict2et(datadict, roottag, listnames)
        xml = to_string(root, pretty=pretty)
        xml = xml.replace('<>', '').replace('</>', '')
        return xml
    else:
        return ''


def list2xml(datalist, roottag, elementname, pretty=False):
    """Converts a list to an UTF-8 encoded XML string.

    See also dict2et()
    """
    root = list2et(datalist, roottag, elementname)
    return to_string(root, pretty=pretty)


def to_string(root, pretty=False):
    """Converts an ElementTree to a string"""

    if pretty:
        indent(root)

    tree = ET.ElementTree(root)
    fileobj = BytesIO()

    # asdf fileobj.write('<?xml version="1.0" encoding="%s"?>' % encoding)

    if pretty:
        fileobj.write('\n')

    tree.write(fileobj, 'utf-8')
    return fileobj.getvalue()


# From http://effbot.org/zone/element-lib.htm
# prettyprint: Prints a tree with each node indented according to its depth. This is
# done by first indenting the tree (see below), and then serializing it as usual.
# indent: Adds whitespace to the tree, so that saving it as usual results in a prettyprinted tree.
# in-place prettyprint formatter

def indent(elem, level=0):
    """XML prettyprint: Prints a tree with each node indented according to its depth."""
    i = "\n" + level * " "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + " "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent(child, level + 1)
        if child:
            if not child.tail or not child.tail.strip():
                child.tail = i
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def test():
    """Simple selftest."""

    data = {"guid": "3104247-7",
            "menge": 7,
            "artnr": "14695",
            "batchnr": "3104247"}
    xmlstr = dict2xml(data, roottag='warenzugang')
    assert xmlstr == ('<warenzugang><artnr>14695</artnr>'
                      '<batchnr>3104247</batchnr><guid>3104247-7</guid><menge>7</menge></warenzugang>')

    data = {"kommiauftragsnr": 2103839,
     "anliefertermin": "2009-11-25",
     "fixtermin": True,
     "prioritaet": 7,
     "info_kunde": "Besuch H. Gerlach",
     "auftragsnr": 1025575,
     "kundenname": "Ute Zweihaus 400424990",
     "kundennr": "21548",
     "name1": "Uwe Zweihaus",
     "name2": "400424990",
     "name3": "",
     "strasse": "Bahnhofstr. 2",
     "land": "DE",
     "plz": "42499",
     "ort": "Hücksenwagen",
     "positionen": [{"menge": 12,
                     "artnr": "14640/XL",
                     "posnr": 1},
                    {"menge": 4,
                     "artnr": "14640/03",
                     "posnr": 2},
                    {"menge": 2,
                     "artnr": "10105",
                     "posnr": 3}],
     "versandeinweisungen": [{"guid": "2103839-XalE",
                              "bezeichner": "avisierung48h",
                              "anweisung": "48h vor Anlieferung unter 0900-LOGISTIK avisieren"},
                             {"guid": "2103839-GuTi",
                              "bezeichner": "abpackern140",
                              "anweisung": "Paletten höchstens auf 140 cm Packen"}]
    }

    xmlstr = dict2xml(data, roottag='kommiauftrag')

    data = {"kommiauftragsnr": 2103839,
     "positionen": [{"menge": 4,
                     "artnr": "14640/XL",
                     "posnr": 1,
                     "nve": "23455326543222553"},
                    {"menge": 8,
                     "artnr": "14640/XL",
                     "posnr": 1,
                     "nve": "43255634634653546"},
                    {"menge": 4,
                     "artnr": "14640/03",
                     "posnr": 2,
                     "nve": "43255634634653546"},
                    {"menge": 2,
                     "artnr": "10105",
                     "posnr": 3,
                     "nve": "23455326543222553"}],
     "nves": [{"nve": "23455326543222553",
               "gewicht": 28256,
               "art": "paket"},
              {"nve": "43255634634653546",
               "gewicht": 28256,
                "art": "paket"}]}

    xmlstr = dict2xml(data, roottag='rueckmeldung')

if __name__ == '__main__':
    import doctest
    import sys
    failure_count, test_count = doctest.testmod()
    d = make_struct({
        'item1': 'string',
        'item2': ['dies', 'ist', 'eine', 'liste'],
        'item3': dict(dies=1, ist=2, ein=3, dict=4),
        'item4': 10,
        'item5': [dict(dict=1, in_einer=2, liste=3)]})
    test()
    sys.exit(failure_count)


########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import json

def dump(api, full=False):

    print("\n")

    if api.warnings():
        print("Warnings" + api.warnings())

    if api.response_content():
        print("Call Success: %s in length" % len(api.response_content()))

    print("Response code: %s" % api.response_code())
    print("Response DOM: %s" % api.response_dom())

    if full:
        print(api.response_content())
        print((json.dumps(api.response_dict(), indent=2)))
    else:
        dictstr = "%s" % api.response_dict()
        print("Response dictionary: %s..." % dictstr[:150])

########NEW FILE########
__FILENAME__ = finding
# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys
from optparse import OptionParser

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump

import ebaysdk
from ebaysdk.finding import Connection as finding
from ebaysdk.exception import ConnectionError

def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")

    (opts, args) = parser.parse_args()
    return opts, args


def run(opts):

    try:
        api = finding(siteid='EBAY-NLBE', debug=opts.debug, appid=opts.appid,
                      config_file=opts.yaml, warnings=True)

        api.execute('findItemsAdvanced', {
            'keywords': u'niño',
            'itemFilter': [
                {'name': 'Condition',
                 'value': 'Used'},
                {'name': 'LocatedIn',
                 'value': 'GB'},
            ],
            'affiliate': {'trackingId': 1},
            'sortOrder': 'CountryDescending',
        })

        dump(api)

    except ConnectionError as e:
        print(e)



def run2(opts):
    try:
        api = finding(debug=opts.debug, appid=opts.appid, config_file=opts.yaml)
        api.execute('findItemsByProduct', '<productId type="ReferenceID">53039031</productId>')
    
        dump(api)

    except ConnectionError as e:
        print(e)


if __name__ == "__main__":
    print("Finding samples for SDK version %s" % ebaysdk.get_version())
    (opts, args) = init_options()
    run(opts)
    run2(opts)

########NEW FILE########
__FILENAME__ = finditem
# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys
from optparse import OptionParser

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump

import ebaysdk
from ebaysdk.soa.finditem import Connection as FindItem
from ebaysdk.shopping import Connection as Shopping
from ebaysdk.utils import getNodeText
from ebaysdk.exception import ConnectionError

def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")
    parser.add_option("-c", "--consumer_id",
                      dest="consumer_id", default=None,
                      help="Specifies the eBay consumer_id id to use.")

    (opts, args) = parser.parse_args()
    return opts, args

def run(opts):

    try:

        shopping = Shopping(debug=opts.debug, appid=opts.appid, 
            config_file=opts.yaml, warnings=False)

        shopping.execute('FindPopularItems', {'QueryKeywords': 'Python'})
        nodes = shopping.response_dom().getElementsByTagName('ItemID')
        itemIds = [getNodeText(n) for n in nodes]

        api = FindItem(debug=opts.debug, consumer_id=opts.consumer_id, config_file=opts.yaml)
        
        records = api.find_items_by_ids(itemIds)

        for r in records:
            print("ID(%s) TITLE(%s)" % (r['ITEM_ID'], r['TITLE'][:35]))

        dump(api)

    except ConnectionError as e:
        print e


if __name__ == "__main__":
    print("FindItem samples for SDK version %s" % ebaysdk.get_version())
    (opts, args) = init_options()
    run(opts)

########NEW FILE########
__FILENAME__ = merchandising
# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys
from optparse import OptionParser

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump

import ebaysdk
from ebaysdk.merchandising import Connection as merchandising
from ebaysdk.exception import ConnectionError

def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")

    (opts, args) = parser.parse_args()
    return opts, args

def run(opts):
    try:
        api = merchandising(debug=opts.debug, appid=opts.appid,
                            config_file=opts.yaml, warnings=True)

        api.execute('getMostWatchedItems', {'maxResults': 3})

        dump(api)
    except ConnectionError as e:
        print e


if __name__ == "__main__":
    (opts, args) = init_options()
    run(opts)

########NEW FILE########
__FILENAME__ = parallel
# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys
from optparse import OptionParser

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump
from ebaysdk.finding import Connection as finding
from ebaysdk.http import Connection as html
from ebaysdk.parallel import Parallel
from ebaysdk.exception import ConnectionError

def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")

    (opts, args) = parser.parse_args()
    return opts, args


def run(opts):

    try:
        p = Parallel()
        apis = []

        api1 = finding(parallel=p, debug=opts.debug, appid=opts.appid, config_file=opts.yaml)
        api1.execute('findItemsAdvanced', {'keywords': 'python'})
        apis.append(api1)

        api4 = html(parallel=p)
        api4.execute('http://www.ebay.com/sch/i.html?_nkw=Shirt&_rss=1')
        apis.append(api4)

        api2 = finding(parallel=p, debug=opts.debug, appid=opts.appid, config_file=opts.yaml)
        api2.execute('findItemsAdvanced', {'keywords': 'perl'})
        apis.append(api2)

        api3 = finding(parallel=p, debug=opts.debug, appid=opts.appid, config_file=opts.yaml)
        api3.execute('findItemsAdvanced', {'keywords': 'php'})
        apis.append(api3)

        p.wait()

        if p.error():
            print p.error()

        for api in apis:
            dump(api)

    except ConnectionError as e:
        print e

if __name__ == "__main__":
    (opts, args) = init_options()
    run(opts)

########NEW FILE########
__FILENAME__ = shopping
# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys
from optparse import OptionParser

try:
    input = raw_input
except NameError:
    pass

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump

import ebaysdk
from ebaysdk.exception import ConnectionError
from ebaysdk.shopping import Connection as Shopping


def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")

    (opts, args) = parser.parse_args()
    return opts, args

def run(opts):
    api = Shopping(debug=opts.debug, appid=opts.appid, config_file=opts.yaml,
                   warnings=True)

    print("Shopping samples for SDK version %s" % ebaysdk.get_version())

    try:
        api.execute('FindPopularItems', {'QueryKeywords': 'Python'})

        if api.response_content():
            print("Call Success: %s in length" % len(api.response_content()))

        print("Response code: %s" % api.response_code())
        print("Response DOM: %s" % api.response_dom())

        dictstr = "%s" % api.response_dict()
        print("Response dictionary: %s..." % dictstr[:50])

        print("Matching Titles:")
        for item in api.response_dict().ItemArray.Item:
            print(item.Title)

    except ConnectionError as e:
        print e 


def popularSearches(opts):

    api = Shopping(debug=opts.debug, appid=opts.appid, config_file=opts.yaml,
                   warnings=True)


    choice = True

    while choice:

        choice = input('Search: ')

        if choice == 'quit':
            break

        mySearch = {
            # "CategoryID": " string ",
            # "IncludeChildCategories": " boolean ",
            "MaxKeywords": 10,
            "QueryKeywords": choice,
        }

        try:
            api.execute('FindPopularSearches', mySearch)

            #dump(api, full=True)

            print("Related: %s" % api.response_dict().PopularSearchResult.RelatedSearches)

            for term in api.response_dict().PopularSearchResult.AlternativeSearches.split(';')[:3]:
                api.execute('FindPopularItems', {'QueryKeywords': term, 'MaxEntries': 3})

                print("Term: %s" % term)

                try:
                    for item in api.response_dict().ItemArray.Item:
                        print(item.Title)
                except AttributeError:
                    pass

                # dump(api)

            print("\n")
        except ConnectionError as e:
            print e

def categoryInfo(opts):

    try:
        api = Shopping(debug=opts.debug, appid=opts.appid, config_file=opts.yaml,
                       warnings=True)

        api.execute('GetCategoryInfo', {"CategoryID": 3410})
        dump(api, full=False)
    
    except ConnectionError as e:
        print e

def with_affiliate_info(opts):
    try:
        api = Shopping(debug=opts.debug, appid=opts.appid,
                       config_file=opts.yaml, warnings=True,
                       trackingid=1234, trackingpartnercode=9)

        mySearch = {    
            "MaxKeywords": 10,
            "QueryKeywords": 'shirt',
        }

        api.execute('FindPopularSearches', mySearch)
        dump(api, full=True)

    except ConnectionError as e:
        print e

def using_attributes(opts):

    try:
        api = Shopping(debug=opts.debug, appid=opts.appid,
                       config_file=opts.yaml, warnings=True)

        api.execute('FindProducts', {
            "ProductID": {'@attrs': {'type': 'ISBN'}, 
                          '#text': '0596154488'}})

        dump(api, full=False)

    except ConnectionError as e:
        print e

if __name__ == "__main__":
    (opts, args) = init_options()
    run(opts)
    popularSearches(opts)
    categoryInfo(opts)
    with_affiliate_info(opts)
    using_attributes(opts)

########NEW FILE########
__FILENAME__ = trading
# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys
import datetime
from optparse import OptionParser

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump

import ebaysdk
from ebaysdk.utils import getNodeText
from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading


def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")
    parser.add_option("-y", "--yaml",
                      dest="yaml", default='ebay.yaml',
                      help="Specifies the name of the YAML defaults file. [default: %default]")
    parser.add_option("-a", "--appid",
                      dest="appid", default=None,
                      help="Specifies the eBay application id to use.")
    parser.add_option("-p", "--devid",
                      dest="devid", default=None,
                      help="Specifies the eBay developer id to use.")
    parser.add_option("-c", "--certid",
                      dest="certid", default=None,
                      help="Specifies the eBay cert id to use.")

    (opts, args) = parser.parse_args()
    return opts, args

def run(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid)

        api.execute('GetCharities', {'CharityID': 3897})
        dump(api)
        print(api.response_dict().Charity.Name)

    except ConnectionError as e:
        print e

def feedback(opts):
    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=False)

        api.execute('GetFeedback', {'UserID': 'tim0th3us'})
        dump(api)

        if int(api.response_dict().FeedbackScore) > 50:
            print("Doing good!")
        else:
            print("Sell more, buy more..")
    
    except ConnectionError as e:
        print e


def getTokenStatus(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=False)

        api.execute('GetTokenStatus')
        dump(api)

    except ConnectionError as e:
        print e

def verifyAddItem(opts):
    """http://www.utilities-online.info/xmltojson/#.UXli2it4avc
    """

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=False)

        myitem = {
            "Item": {
                "Title": "Harry Potter and the Philosopher's Stone",
                "Description": "This is the first book in the Harry Potter series. In excellent condition!",
                "PrimaryCategory": {"CategoryID": "377"},
                "StartPrice": "1.0",
                "CategoryMappingAllowed": "true",
                "Country": "US",
                "ConditionID": "3000",
                "Currency": "USD",
                "DispatchTimeMax": "3",
                "ListingDuration": "Days_7",
                "ListingType": "Chinese",
                "PaymentMethods": "PayPal",
                "PayPalEmailAddress": "tkeefdddder@gmail.com",
                "PictureDetails": {"PictureURL": "http://i1.sandbox.ebayimg.com/03/i/00/30/07/20_1.JPG?set_id=8800005007"},
                "PostalCode": "95125",
                "Quantity": "1",
                "ReturnPolicy": {
                    "ReturnsAcceptedOption": "ReturnsAccepted",
                    "RefundOption": "MoneyBack",
                    "ReturnsWithinOption": "Days_30",
                    "Description": "If you are not satisfied, return the book for refund.",
                    "ShippingCostPaidByOption": "Buyer"
                },
                "ShippingDetails": {
                    "ShippingType": "Flat",
                    "ShippingServiceOptions": {
                        "ShippingServicePriority": "1",
                        "ShippingService": "USPSMedia",
                        "ShippingServiceCost": "2.50"
                    }
                },
                "Site": "US"
            }
        }

        api.execute('VerifyAddItem', myitem)
        dump(api)

    except ConnectionError as e:
        print e

def verifyAddItemErrorCodes(opts):
    """http://www.utilities-online.info/xmltojson/#.UXli2it4avc
    """

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=False)

        myitem = {
            "Item": {
                "Title": "Harry Potter and the Philosopher's Stone",
                "Description": "This is the first book in the Harry Potter series. In excellent condition!",
                "PrimaryCategory": {"CategoryID": "377aaaaaa"},
                "StartPrice": "1.0",
                "CategoryMappingAllowed": "true",
                "Country": "US",
                "ConditionID": "3000",
                "Currency": "USD",
                "DispatchTimeMax": "3",
                "ListingDuration": "Days_7",
                "ListingType": "Chinese",
                "PaymentMethods": "PayPal",
                "PayPalEmailAddress": "tkeefdddder@gmail.com",
                "PictureDetails": {"PictureURL": "http://i1.sandbox.ebayimg.com/03/i/00/30/07/20_1.JPG?set_id=8800005007"},
                "PostalCode": "95125",
                "Quantity": "1",
                "ReturnPolicy": {
                    "ReturnsAcceptedOption": "ReturnsAccepted",
                    "RefundOption": "MoneyBack",
                    "ReturnsWithinOption": "Days_30",
                    "Description": "If you are not satisfied, return the book for refund.",
                    "ShippingCostPaidByOption": "Buyer"
                },
                "ShippingDetails": {
                    "ShippingType": "Flat",
                    "ShippingServiceOptions": {
                        "ShippingServicePriority": "1",
                        "ShippingService": "USPSMedia",
                        "ShippingServiceCost": "2.50"
                    }
                },
                "Site": "US"
            }
        }

        api.execute('VerifyAddItem', myitem)
    
    except ConnectionError as e:
        # traverse the DOM to look for error codes
        for node in api.response_dom().getElementsByTagName('ErrorCode'):
            print("error code: %s" % getNodeText(node))

        # check for invalid data - error code 37
        if 37 in api.response_codes():
            print("Invalid data in request")

        print e

def uploadPicture(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True)

        pictureData = {
            "WarningLevel": "High",
            "ExternalPictureURL": "http://developer.ebay.com/DevZone/XML/docs/images/hp_book_image.jpg",
            "PictureName": "WorldLeaders"
        }

        api.execute('UploadSiteHostedPictures', pictureData)
        dump(api)

    except ConnectionError as e:
        print e

def memberMessages(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True)

        now = datetime.datetime.now()

        memberData = {
            "WarningLevel": "High",
            "MailMessageType": "All",
            # "MessageStatus": "Unanswered",
            "StartCreationTime": now - datetime.timedelta(days=60),
            "EndCreationTime": now,
            "Pagination": {
                "EntriesPerPage": "5",
                "PageNumber": "1"
            }
        }

        api.execute('GetMemberMessages', memberData)

        dump(api)

        if api.response_dict().MemberMessage:
            messages = api.response_dict().MemberMessage.MemberMessageExchange

            if type(messages) != list:
                    messages = [ messages ]

            for m in messages:
                print("%s: %s" % (m.CreationDate, m.Question.Subject[:50]))

    except ConnectionError as e:
        print e

def getUser(opts):
    try:

        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True, timeout=20, siteid=101)

        api.execute('GetUser', {'UserID': 'biddergoat'})
        dump(api, full=False)
    
    except ConnectionError as e:
        print e

def getOrders(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True, timeout=20)

        api.execute('GetOrders', {'NumberOfDays': 30})
        dump(api, full=False)

    except ConnectionError as e:
        print e

def categories(opts):

    try:
        api = Trading(debug=opts.debug, config_file=opts.yaml, appid=opts.appid,
                      certid=opts.certid, devid=opts.devid, warnings=True, timeout=20, siteid=101)

        callData = {
            'DetailLevel': 'ReturnAll',
            'CategorySiteID': 101,
            'LevelLimit': 4,
        }

        api.execute('GetCategories', callData)
        dump(api, full=False)

    except ConnectionError as e:
        print e

'''
api = trading(domain='api.sandbox.ebay.com')
api.execute('GetCategories', {
    'DetailLevel': 'ReturnAll',
    'CategorySiteID': 101,
    'LevelLimit': 4,
})
'''

if __name__ == "__main__":
    (opts, args) = init_options()

    print("Trading API Samples for version %s" % ebaysdk.get_version())

    run(opts)
    feedback(opts)
    verifyAddItem(opts)
    getTokenStatus(opts)
    verifyAddItemErrorCodes(opts)
    uploadPicture(opts)
    memberMessages(opts)
    categories(opts)
    getUser(opts)
    getOrders(opts)

########NEW FILE########
__FILENAME__ = t_http
# -*- coding: utf-8 -*-
'''
© 2012-2013 eBay Software Foundation
Authored by: Tim Keefer
Licensed under CDDL 1.0
'''

import os
import sys

from optparse import OptionParser

sys.path.insert(0, '%s/../' % os.path.dirname(__file__))

from common import dump

import ebaysdk
from ebaysdk.http import Connection as HTTP
from ebaysdk.exception import ConnectionError

def init_options():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="Enabled debugging [default: %default]")

    (opts, args) = parser.parse_args()
    return opts, args

def run(opts):

    try:
        api = HTTP(debug=opts.debug, method='GET')

        api.execute('http://feeds.wired.com/wired/index')

        dump(api)

    except ConnectionError as e:
        print e

if __name__ == "__main__":
    print("HTTP samples for SDK version %s" % ebaysdk.get_version())
    (opts, args) = init_options()
    run(opts)

########NEW FILE########
