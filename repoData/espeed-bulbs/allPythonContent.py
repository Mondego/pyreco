__FILENAME__ = client
# -*- coding: utf-8 -*-
#
# Copyright 2011 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""

Bulbs supports pluggable backends. These are the abstract base classes that 
provides the server-client interface. Implement these to create a new client. 

"""
import inspect

from bulbs.config import Config, DEBUG
from bulbs.registry import Registry
from bulbs.utils import get_logger

from .typesystem import TypeSystem

SERVER_URI = "http://localhost"

log = get_logger(__name__)

# TODO: Consider making these real Python Abstract Base Classes (import abc)            

class Request(object):

    def __init__(self, config, content_type):
        """
        Initializes a client object.

        :param root_uri: the base URL of Rexster.

        """
        self.config = config
        self.content_type = content_type
        self._initialize()

    def _initialize(self):
        pass

class Result(object):
    """
    Abstract base class for a single result, not a list of results.  

    :param result: The raw result.
    :type result: dict

    :param config: The graph Config object.
    :type config: Config 

    :ivar raw: The raw result.
    :ivar data: The data in the result.

    """

    def __init__(self, result, config):
        self.config = config

        # The raw result.
        self.raw = result
        
        # The data in the result.
        self.data = None

    def get_id(self):
        """
        Returns the element ID.

        :rtype: int

        """
        raise NotImplementedError
    
    def get_type(self):
        """
        Returns the element's base type, either "vertex" or "edge".

        :rtype: str

        """
        raise NotImplementedError

    def get_data(self):
        """
        Returns the element's property data.

        :rtype: dict

        """
        raise NotImplementedError

    def get_uri(self):
        """
        Returns the element URI.

        :rtype: str

        """
        raise NotImplementedError

    def get_outV(self):
        """
        Returns the ID of the edge's outgoing vertex (start node).

        :rtype: int

        """
        raise NotImplementedError

    def get_inV(self):
        """
        Returns the ID of the edge's incoming vertex (end node).

        :rtype: int

        """
        raise NotImplementedError

    def get_label(self):
        """
        Returns the edge label (relationship type).

        :rtype: str

        """
        raise NotImplementedError

    def get_index_name(self):
        """
        Returns the index name.

        :rtype: str

        """
        raise NotImplementedError
   
    def get_index_class(self):
        """
        Returns the index class, either "vertex" or "edge".

        :rtype: str

        """
        raise NotImplementedError

    def get(self, attribute):
        """
        Returns the value of a client-specific attribute.

        :param attribute: Name of the attribute:
        :type attribute: str

        :rtype: str

        """
        return self.raw[attribute]


class Response(object):
    """
    Abstract base class for the response returned by the request.
    
    :param response: The raw response.
    :type response: Depends on Client.

    :param config: Config object.
    :type config: bulbs.config.Config

    :ivar config: Config object.
    :ivar headers: Response headers.
    :ivar content: A dict containing the response content.
    :ivar results: A generator of Neo4jResult objects, a single Neo4jResult object, 
        or None, depending on the number of results returned.
    :ivar total_size: The number of results returned.
    :ivar raw: Raw HTTP response. Only set when log_level is DEBUG.

    """
    result_class = Result

    def __init__(self,  response, config):
        self.config = config
        self.handle_response(response)
        self.headers = self.get_headers(response)
        self.content = self.get_content(response)
        self.results, self.total_size = self.get_results()
        self.raw = self._maybe_get_raw(response, config)

    def _maybe_get_raw(self,response, config):
        """Returns the raw response if in DEBUG mode."""
        # don't store raw response in production else you'll bloat the obj
        if config.log_level == DEBUG:
            return response

    def handle_response(self, response):
        """
        Check the server response and raise exception if needed.
        
        :param response: Raw server response.
        :type response: Depends on Client.

        :rtype: None

        """
        raise NotImplementedError

    def get_headers(self, response):
        """
        Returns a dict containing the headers from the response.

        :param response: Raw server response.
        :type response: tuple
        
        :rtype: httplib2.Response

        """
        raise NotImplementedError

    def get_content(self, response):
        """
        Returns a dict containing the content from the response.
        
        :param response: Raw server response.
        :type response: tuple
        
        :rtype: dict or None

        """
        raise NotImplementedError

    def get_results(self):
        """
        Returns the results contained in the response.

        :return:  A tuple containing two items: 1. Either a generator of Neo4jResult objects, 
                  a single Neo4jResult object, or None, depending on the number of results 
                  returned; 2. An int representing the number results returned.
        :rtype: tuple

        """
        raise NotImplementedError

    def get(self, attribute):
        """Return a client-specific attribute."""
        return self.content[attribute]

    def one(self):
        """
        Returns one result or raises an error if there is more than one result.

        :rtype: Result

        """
        # If you're using this utility, that means the results attribute in the 
        # Response object should always contain a single result object,
        # not multiple items. But gremlin returns all results as a list
        # even if the list contains only one element. And the Response class
        # converts all lists to a generator of Result objects. Thus in that case,
        # we need to grab the single Result object out of the list/generator.
        if self.total_size > 1:
            log.error('resp.results contains more than one item.')
            raise ValueError
        if inspect.isgenerator(self.results):
            result = next(self.results)
        else:
            result = self.results
        return result
        

class Client(object):
    """
    Abstract base class for the low-level server client.

    :param config: Optional Config object. Defaults to default Config.
    :type config: bulbs.config.Config

    :cvar default_uri: Default URI for the database.
    :cvar request_class: Request class for the Client.

    :ivar config: Config object.
    :ivar registry: Registry object.
    :ivar type_system: TypeSystem object.
    :ivar request: Request object.

    Example:

    >>> from bulbs.neo4jserver import Neo4jClient
    >>> client = Neo4jClient()
    >>> script = client.scripts.get("get_vertices")
    >>> response = client.gremlin(script, params=None)
    >>> result = response.results.next()


    """
    default_uri = SERVER_URI
    request_class = Request


    def __init__(self, config=None):
        self.config = config or Config(self.default_uri)
        self.registry = Registry(self.config)
        self.type_system = TypeSystem()
        self.request = self.request_class(self.config, self.type_system.content_type)

    # Vertex Proxy

    def create_vertex(self, data):
        """
        Creates a vertex and returns the Response.

        :param data: Property data.
        :type data: dict

        :rtype: Response

        """
        raise NotImplementedError
    
    def get_vertex(self, _id):
        """
        Gets the vertex with the _id and returns the Response.

        :param data: Vertex ID.
        :type data: int

        :rtype: Response

        """
        raise NotImplementedError 

    def get_all_vertices(self):
        """
        Returns a Response containing all the vertices in the Graph.

        :rtype: Response

        """
        raise NotImplementedError 

    def update_vertex(self, _id, data):
        """
        Updates the vertex with the _id and returns the Response.

        :param _id: Vertex ID.
        :type _id: dict

        :param data: Property data.
        :type data: dict

        :rtype: Response

        """
        raise NotImplementedError 

    def delete_vertex(self, _id):
        """
        Deletes a vertex with the _id and returns the Response.

        :param _id: Vertex ID.
        :type _id: dict

        :rtype: Response

        """
        raise NotImplementedError 

    # Edge Proxy

    def create_edge(self, outV, label, inV, data=None):
        """
        Creates a edge and returns the Response.
        
        :param outV: Outgoing vertex ID.
        :type outV: int

        :param label: Edge label.
        :type label: str

        :param inV: Incoming vertex ID.
        :type inV: int

        :param data: Property data.
        :type data: dict or None

        :rtype: Response

        """
        raise NotImplementedError 

    def get_edge(self, _id):
        """
        Gets the edge with the _id and returns the Response.

        :param data: Edge ID.
        :type data: int

        :rtype: Response

        """
        raise NotImplementedError 

    def get_all_edges(self):
        """
        Returns a Response containing all the edges in the Graph.

        :rtype: Response

        """
        raise NotImplementedError 

    def update_edge(self, _id, data):
        """
        Updates the edge with the _id and returns the Response.

        :param _id: Edge ID.
        :type _id: dict

        :param data: Property data.
        :type data: dict

        :rtype: Response

        """
        raise NotImplementedError 

    def delete_edge(self, _id):
        """
        Deletes a edge with the _id and returns the Response.

        :param _id: Edge ID.
        :type _id: dict

        :rtype: Response

        """
        raise NotImplementedError 

    # Vertex Container

    def outE(self, _id, label=None):
        """
        Returns the outgoing edges of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Response
        
        """
        raise NotImplementedError 

    def inE(self, _id, label=None):
        """
        Returns the incoming edges of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Response

        """
        raise NotImplementedError 

    def bothE(self, _id, label=None):
        """
        Returns the incoming and outgoing edges of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Response
        
        """
        raise NotImplementedError 

    def outV(self, _id, label=None):
        """
        Returns the out-adjacent vertices of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Response

        """
        raise NotImplementedError 

    def inV(self, _id, label=None):
        """
        Returns the in-adjacent vertices of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Response

        """
        raise NotImplementedError 

    def bothV(self, _id, label=None):
        """
        Returns the incoming- and outgoing-adjacent vertices of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Response

        """
        raise NotImplementedError 

    # Index Proxy - Vertex

    def create_vertex_index(self, params):
        """
        Creates a vertex index with the specified params.

        :param index_name: Name of the index to create.
        :type index_name: str

        :rtype: Response

        """
        raise NotImplementedError 

    def get_vertex_index(self, index_name):
        """
        Returns the vertex index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: Response

        """
        raise NotImplementedError 
        
    def delete_vertex_index(self, index_name): 
        """
        Deletes the vertex index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: Response

        """
        raise NotImplementedError 

    # Index Proxy - Edge

    def create_edge_index(self, index_name):
        """
        Creates a edge index with the specified params.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: Response

        """
        raise NotImplementedError 

    def get_edge_index(self, index_name):
        """
        Returns the edge index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: Response

        """
        raise NotImplementedError 
        
    def delete_edge_index(self, index_name): 
        """
        Deletes the edge index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: Response

        """
        raise NotImplementedError 
    
    # Index Container - Vertex

    def put_vertex(self, index_name, key, value, _id):
        """
        Adds a vertex to the index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :param _id: Vertex ID
        :type _id: int
        
        :rtype: Response

        """
        raise NotImplementedError 

    def lookup_vertex(self, index_name, key, value):
        """
        Returns the vertices indexed with the key and value.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :rtype: Response

        """
        raise NotImplementedError 

    def remove_vertex(self, index_name, _id, key=None, value=None):
        """
        Removes a vertex from the index and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Optional. Name of the key.
        :type key: str

        :param value: Optional. Value of the key.
        :type value: str        

        :rtype: Response

        """
        raise NotImplementedError 

    # Index Container - Edge

    def put_edge(self, index_name, key, value, _id):
        """
        Adds an edge to the index and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :param _id: Edge ID
        :type _id: int
        
        :rtype: Response

        """
        raise NotImplementedError 

    def lookup_edge(self, index_name, key, value):
        """
        Looks up an edge in the index and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :rtype: Response

        """
        raise NotImplementedError 

    def remove_edge(self, index_name, _id, key=None, value=None):
        """
        Removes an edge from the index and returns the Response.
        
        :param index_name: Name of the index.
        :type index_name: str

        :param _id: Edge ID
        :type _id: int

        :param key: Optional. Name of the key.
        :type key: str

        :param value: Optional. Value of the key.
        :type value: str        

        :rtype: Response

        """
        raise NotImplementedError 

    # Model Proxy - Vertex

    def create_indexed_vertex(self, data, index_name, keys=None):
        """
        Creates a vertex, indexes it, and returns the Response.

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index.
        :type keys: list

        :rtype: Response

        """
        raise NotImplementedError 

    def update_indexed_vertex(self, _id, data, index_name, keys=None):
        """
        Updates an indexed vertex and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index.
        :type keys: list

        :rtype: Response

        """
        raise NotImplementedError 

    # Model Proxy - Edge

    def create_indexed_edge(self, data, index_name, keys=None):
        """
        Creates a edge, indexes it, and returns the Response.

        :param outV: Outgoing vertex ID.
        :type outV: int

        :param label: Edge label.
        :type label: str

        :param inV: Incoming vertex ID.
        :type inV: int

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index. Defaults to None (indexes all properties).
        :type keys: list

        :rtype: Response

        """
        raise NotImplementedError 

    def update_indexed_edge(self, _id, data, index_name, keys=None):
        """
        Updates an indexed edge and returns the Response.

        :param _id: Edge ID.
        :type _id: int

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index. Defaults to None (indexes all properties).
        :type keys: list

        :rtype: Response

        """
        raise NotImplementedError 
    
        

########NEW FILE########
__FILENAME__ = graph
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
from bulbs.config import Config
from bulbs.factory import Factory
from bulbs.element import Vertex, Edge
from bulbs.model import Relationship
from bulbs.utils import initialize_elements

from bulbs.base.client import Client
from bulbs.base.index import Index


# A framework is an understanding of how things could fit together.
# When designing these things, it's important to remember that your 
# understanding is incomplete.

# Bulbs is written as a series of layers, designed from the bottom up.

class Graph(object):
    """
    Abstract base class for the server-specific Graph implementations. 

    :param config: Optional Config object. Defaults to the default config.
    :type config: Config
        
    :cvar client_class: Client class.
    :cvar default_index: Default index class.

    :ivar client: Client object.
    :ivar config: Config object.
    :ivar vertices: VertexProxy object.
    :ivar edges: EdgeProxy object.

    Example:

    >>> from bulbs.neo4jserver import Graph
    >>> g = Graph()
    >>> james = g.vertices.create(name="James")
    >>> julie = g.vertices.create(name="Julie")
    >>> g.edges.create(james, "knows", julie)

    """    
    # The Client class to use for this Graph.
    client_class = Client

    # The default Index class.
    default_index = Index

    def __init__(self, config=None):
        self.client = self.client_class(config)
        self.config = self.client.config

        self.factory = Factory(self.client)

        self.vertices = self.build_proxy(Vertex)
        self.edges = self.build_proxy(Edge)

    @property
    def V(self):
        """
        Returns a list of all the vertices in the graph.

        :rtype: list or None

        """
        resp = self.client.get_all_vertices()
        if resp.total_size > 0:
            vertices = initialize_elements(self.client, resp)
            return list(vertices)
   
    @property
    def E(self):
        """
        Returns a list of all the edges in the graph.

        :rtype: list or None

        """
        resp = self.client.get_all_edges()
        if resp.total_size > 0:
            edges = initialize_elements(self.client, resp)
            return list(edges)
        
    def add_proxy(self, proxy_name, element_class, index_class=None):
        """
        Adds an element proxy to the Graph object for the element class.

        :param proxy_name: Attribute name to use for the proxy.
        :type proxy_name: str

        :param element_class: Element class managed by this proxy.
        :type element_class: Element

        :param index_class: Index class for Element's primary index. 
            Defaults to default_index.
        :type index_class: Index

        :rtype: None

        """
        proxy = self.build_proxy(element_class, index_class)
        self.client.registry.add_proxy(proxy_name, proxy)
        setattr(self, proxy_name, proxy)
    
    def build_proxy(self, element_class, index_class=None):
        """
        Returns an element proxy built to specifications.

        :param element_class: Element class managed by this proxy.
        :type element_class: Element

        :param index_class: Optional Index class for Element's primary index. 
            Defaults to default_index.
        :type index_class: Index

        :rtype: Element proxy

        """
        if not index_class:
            index_class = self.default_index
        return self.factory.build_element_proxy(element_class, index_class)

    def load_graphml(self, uri):
        """
        Loads a GraphML file into the database and returns the response.

        :param uri: URI of the GraphML file.
        :type uri: str

        :rtype: Response

        """
        raise NotImplementedError
        
    def get_graphml(self):
        """
        Returns a GraphML file representing the entire database.

        :rtype: Response

        """
        raise NotImplementedError

    def warm_cache(self):
        """
        Warms the server cache by loading elements into memory.

        :rtype: Response

        """
        raise NotImplementedError

    def clear(self):
        """Deletes all the elements in the graph.

        :rtype: Response

        .. admonition:: WARNING 

           This will delete all your data!

        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = index
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""

Bulbs supports pluggable backends. These are the abstract base classes that 
provides the index interface for a client. Implement these to create an index.

"""
from bulbs.utils import initialize_element, initialize_elements, get_one_result


# Index Proxies

class VertexIndexProxy(object):
    """
    Abstract base class the vertex index proxy.

    :ivar index_class: Index class.
    :ivar client: Client object.

    """
    def __init__(self, index_class, client):        
        # The index class for this proxy, e.g. ExactIndex.
        self.index_class = index_class

        # The Client object for the database.
        self.client = client
    
    def create(self, index_name):
        """
        Creates an Vertex index and returns it.

        :param index_name: Index name.
        :type index_name: str

        :rtype: Index
        
        """
        raise NotImplementedError

    def get(self, index_name):
        """
        Returns the Index object with the specified name or None if not found.
        
        :param index_name: Index name.
        :type index_name: str

        :rtype: Index
        
        """
        raise NotImplementedError

    def get_or_create(self, index_name):
        """
        Get a Vertex Index or create it if it doesn't exist.

        :param index_name: Index name.
        :type index_name: str

        :rtype: Index

        """ 
        raise NotImplementedError

    def delete(self, index_name):
        """ 
        Deletes an index and returns the Response.

        :param index_name: Index name.
        :type index_name: str

        :rtype: Response

        """
        raise NotImplementedError


class EdgeIndexProxy(object):
    """
    Abstract base class the edge index proxy.

    :ivar index_class: Index class.
    :ivar client: Client object.

    """
    def __init__(self, index_class, client):        
        # The index class for this proxy, e.g. ExactIndex.
        self.index_class = index_class

        # The Client object for the database.
        self.client = client
    
    def create(self, index_name):
        """
        Creates an Edge index and returns it.

        :param index_name: Index name.
        :type index_name: str

        :rtype: Index
        
        """
        raise NotImplementedError

    def get(self, index_name):
        """
        Returns the Index object with the specified name or None if not found.
        
        :param index_name: Index name.
        :type index_name: str

        :rtype: Index
        
        """
        raise NotImplementedError

    def get_or_create(self, index_name):
        """
        Get an Edge Index or create it if it doesn't exist.

        :param index_name: Index name.
        :type index_name: str

        :rtype: Index

        """ 
        raise NotImplementedError

    def delete(self, index_name):
        """ 
        Deletes an index and returns the Response.

        :param index_name: Index name.
        :type index_name: str

        :rtype: Response

        """
        raise NotImplementedError


# Index Containers

class Index(object):
    """
    Abstract base class for the default index.

    :ivar client: Client object 
    :ivar result: Result object.

    """

    def __init__(self, client, result):

        # The Client object for the database.
        self.client = client

        # The index attributes returned by the proxy request.
        self.result = result

    @classmethod 
    def get_proxy_class(cls, base_type=None):
        """
        Returns the IndexProxy class.

        :param base_type: Index base type, either vertex or edge.
        :type base_type: str

        :rtype: class

        """
        class_map = dict(vertex=VertexIndexProxy, edge=EdgeIndexProxy)
        return class_map[base_type]

    @property
    def index_name(self):
        """
        Returns the index name.

        :rtype: str

        """
        return self.result.get_index_name()

    @property
    def index_class(self):
        """
        Returns the index class.

        :rtype: class

        """
        return self.result.get_index_class()

    def put(self, _id, key=None, value=None, **pair):
        """
        Put an element into the index at key/value and return the Response.

        :param _id: The element ID.
        :type _id: int or str

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: name/value pair

        :rtype: Response
            
        """
        raise NotImplementedError

    def update(self, _id, key=None, value=None, **pair):
        """
        Update the element ID for the key and value.
        
        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: Response

        """
        raise NotImplementedError

    def lookup(self, key=None, value=None, **pair):
        """
        Return all the elements in the index where key equals value.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: Element generator

        """
        raise NotImplementedError

    def put_unique(self, _id, key=None, value=None, **pair):
        """
        Put an element into the index at key/value and overwrite it if an 
        element already exists; thus, when you do a lookup on that key/value pair,
        there will be a max of 1 element returned.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: Resposne

        """
        raise NotImplementedError

    def get_unique(self, key=None, value=None, **pair):
        """
        Returns a max of 1 elements in the index matching the key/value pair.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: Element or None

        """
        raise NotImplementedError

    def remove(self, _id, key=None, value=None, **pair):
        """
        Remove the element from the index located by key/value.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: Response

        """
        raise NotImplementedError

    def count(self, key=None, value=None, **pair):
        """
        Return the number of items in the index for the key and value.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: name/value pair

        :rtype: int

        """
        raise NotImplementedError
        
    def _get_key_value(self, key, value, pair):
        """
        Returns the key and value, regardless of how it was entered.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: tuple

        """
        if pair:
            key, value = pair.popitem()
        return key, value

    def _get_method(self, **method_map):
        """
        Returns the right method, depending on the index class type.

        :param method_map: Dict mapping the index class type to its method name. 
        :type method_map: dict

        :rtype: Callable

        """
        method_name = method_map[self.index_class]
        method = getattr(self.client, method_name)
        return method

########NEW FILE########
__FILENAME__ = typesystem
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Bulbs supports plugabble type systems.

"""

class TypeSystem(object):
    """
    Abstract base class for plugabble database type systems.

    :cvar content_type: The backend client's content type.
    :cvar database: Converter object. Converts Python values to database values.
    :cvar python: Converter object. Converts database values to Python values.

    """
    content_type = None
    database = None
    python = None


class Converter(object):
    """Abstract base class of conversion methods called by DataType classes."""

    def to_string(self, value):
        raise NotImplementedError

    def to_integer(self, value):
        raise NotImplementedError
    
    def to_long(self, value):
        raise NotImplementedError

    def to_float(self, value):
        raise NotImplementedError

    def to_bool(self, value):
        raise NotImplementedError

    def to_list(self, value):
        raise NotImplementedError

    def to_dictionary(self, value):
        raise NotImplementedError

    def to_null(self, value):
        raise NotImplementedError

    def to_document(self, value):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
import os
from .utils import bulbs_logger, get_logger, urlparse
from logging import StreamHandler, DEBUG, INFO, WARNING, ERROR, CRITICAL

log = get_logger(__name__)


class Config(object):
    """
    Configuration options for Bulbs.

    :param root_uri: Root URI of the database.
    :type root_uri: str

    :param username: Optional username. Defaults to None.
    :type username: str

    :param password: Optional password. Defaults to None.
    :type password: str

    :ivar root_uri: Root URI of the server.
    :ivar username: Optional username. Defaults to None.
    :ivar password: Optional password. Defaults to None.
    :ivar log_level: Python log level. Defaults to ERROR.
    :ivar log_handler: Python log handler. Defaults to StreamHandler.
    :ivar id_var: Name of the element ID variable. Defaults to "eid".
    :ivar type_var: Name of the type variable. Defaults to "element_type".
    :ivar label_var: Name of the label variable. Defaults to "label".
    :ivar type_system: Name of the type system. Defaults to "json".
    :ivar vertex_index: Name of the vertex index. Defaults to "vertex". 
    :ivar edge_index: Name of the edge index. Defaults to "edge". 
    :ivar autoindex: Enable auto indexing. Defaults to True.
    :ivar server_scripts: Scripts are defined server side. Defaults to False.
    :ivar timeout: Optional timeout in seconds. Defaults to None

    Example:

    >>> from bulbs.config import Config, DEBUG
    >>> from bulbs.neo4jserver import Graph, NEO4J_URI
    >>> config = Config(NEO4J_URI, username="james", password="secret")
    >>> config.set_logger(DEBUG)
    >>> g = Graph(config)

    """

    def __init__(self, root_uri, username=None, password=None, timeout=None):
        self.root_uri = root_uri
        self.username = username
        self.password = password
        self.log_level = ERROR
        self.log_handler = StreamHandler
        self.id_var = "eid"
        self.type_var = "element_type"
        self.label_var = "label"
        self.type_system = "json" 
        self.vertex_index = "vertex"
        self.edge_index = "edge"
        self.autoindex = True         # Titan Client sets autoindex to false
        self.server_scripts = False
        self.timeout = timeout
        
        # Set the default log level and log handler
        self.set_logger(self.log_level, self.log_handler)

        # Sanity checks...
        assert self.root_uri is not None

    # TODO: fix duplicate log issue from setting logger multiple times
    def set_logger(self, log_level, log_handler=None):
        """
        Sets or updates the log level and log handler.

        :param log_level: Python log level.
        :type log_level: int

        :param log_handler: Python log handler. Defaults to log_handler.
        :type log_handler: logging.Handler

        :rtype: None

        """
        #log = get_logger(__name__)
        bulbs_logger.setLevel(log_level)
        self.log_level = log_level 
        
        if log_handler is not None:
            # Don't add log handler twice to prevent duplicate output
            self._maybe_add_log_handler(log_handler)

    def _maybe_add_log_handler(self, log_handler):
        """
        Adds log handler if an instance of it hasn't already been added.

        :param log_handler: Python log handler.
        :type log_handler: logging.Handler
        
        :rtype: None

        """
        for handler in bulbs_logger.handlers:
            if isinstance(handler, log_handler):
                return
        # log handler hasn't been added yet so add it
        bulbs_logger.addHandler(log_handler())

    def set_neo4j_heroku(self, log_level=ERROR, log_handler=None):
        """
        Sets credentials if using the Neo4j Heroku Add On.

        :param log_level: Python log level. Defaults to ERROR.
        :type log_level: int

        :param log_handler: Python log handler. Defaults to log_handler.
        :type log_handler: logging.Handler

        :rtype: None

        """
        url = os.environ.get('NEO4J_REST_URL', None)
        log.debug("NEORJ_REST_URL: %s", url)

        if url is not None:
            parsed =  urlparse(url)
            pieces = (parsed.scheme, parsed.hostname, parsed.port, parsed.path)
            self.root_uri = "%s://%s:%s%s" % pieces
            self.username = parsed.username
            self.password = parsed.password
            self.set_logger(log_level, log_handler)
            log.debug("ROOT_URI: %s", self.root_uri)
            log.debug("USERNAME: %s", self.username)
            log.debug("PASSWORD: %s", self.password)

########NEW FILE########
__FILENAME__ = element
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Vertex and Edge container classes and associated proxy classes.

"""
from .utils import u  # Python 3 unicode
from .utils import initialize_element, initialize_elements, coerce_id, get_logger

log = get_logger(__name__)


class Element(object):
    """An abstract base class for Vertex and Edge containers."""

    def __init__(self, client):

        # NOTE: moved all private prop defs here so they are declared and
        # pre-defined in _properties so that setattr works in model NORMAL mode

        # Client object
        self._client = client

        # Property data
        self._data = {}

        # Result object.
        self._result = None

        # Vertex Proxy Object
        self._vertices = None

        # Edge Proxy Object
        self._edges = None

        # Initialized Flag
        # Initialize all non-database properties here because when _initialized
        # is set to True, __setattr__ will assume all non-defined properties 
        # are database properties and will set them in self._data.
        self._initialized = True

    def _initialize(self, result):
        """
        Initialize the element with the result that was returned by the DB.

        :param result: The Result object returned by the the Client request.
        :type result: Result

        :rtype: None

        """
        self._result = result

        # TODO: Do we really need to make a copy?
        self._data = result.get_data().copy() 

        # Sets the element ID to the var defined in Config. Defaults to eid.
        self._set_pretty_id(self._client)

        # These vertex and edge proxies are primarily used for gets; 
        # all mutable methods that use these are overloaded in Model.
        self._vertices = VertexProxy(Vertex,self._client)
        self._edges = EdgeProxy(Edge,self._client)

       
    @classmethod
    def get_base_type(cls):
        """
        Returns this element class's base type.
        
        :rtype: str
        
        """
        raise NotImplementedError 

    @classmethod
    def get_element_key(cls, config):
        """
        Returns the element key.

        :param config: Config object.
        :type config: bulbs.config.Config

        :rtype: str

        """
        raise NotImplementedError 

    @classmethod
    def get_index_name(cls, config):
        """
        Returns the index name. 

        :param config: Config object.
        :type config: bulbs.config.Config

        :rtype: str

        """
        raise NotImplementedError 

    @classmethod
    def get_proxy_class(cls):
        """
        Returns the proxy class. 

        :param config: Config object.
        :type config: bulbs.config.Config

        :rtype: class

        """
        raise NotImplementedError 

    @property
    def _id(self):
        """
        Returns the element ID. 

        :rtype: int or str

        .. note:: This is the element's "primary key"; however, some DBs (such 
                  as neo4j) reuse IDs if they are deleted so be careful with 
                  how you use them. 
      
                  If you want to guarantee they are unique across the DB's 
                  lifetime either don't physically delete elements and just set
                  a deleted flag, or use some other mechanism  for the primary 
                  key, such as an external sequence or a hash.

        """
        return self._result.get_id()

    @property 
    def _type(self):
        """
        Returns the result's base type, either vertex or edge.

        :rtype: str

        """
        return self._result.get_type()

    def _set_pretty_id(self, client):
        """
        Sets the ID var defined in Config as a Python property. Defaults to eid.
        
        :param client: Client object.
        :type client: Client

        :rtype: None

        .. note:: The user-configured element_type and label vars are not set 
                  as Python properties because they are class vars so you set 
                  those when you define the Models.

        """
        pretty_var = client.config.id_var
        fget = lambda self: self._result.get_id()
        setattr(Element, pretty_var, property(fget))                    

    def __setattr__(self, key, value):
        """
        Overloaded to set the object attributes or the property data.

        If you explicitly set/change the values of an element's properties,
        make sure you call save() to updated the values in the DB.

        :param key: Database property key.
        :type key: str

        :param value: Database property value.
        :type value: str, int, long, float, list, dict

        :rtype: None

        """
        # caching __dict__ to avoid the dots and boost performance
        dict_ = self.__dict__ 

        # dict_.get() is faster than getattr()
        _initialized = dict_.get("_initialized", False)

        if key in dict_ or _initialized is False or key in self.__class__.__dict__:
            # set the attribute normally
            object.__setattr__(self, key, value)
        else:
            # set the attribute as a data property
            self._data[key] = value

    def __getattr__(self, name):
        """
        Returns the value of the database property for the given name.

        :param name: The name of the data property.
        :type name: str

        :raises: AttributeError

        :rtype: str, int, long, float, list, dict, or None 
        
        """
        try:
            return self._data[name]
        except:
            raise AttributeError(name)

    def __len__(self):
        """
        Returns the number of items stored in the DB results

        :rtype: int

        """
        return len(self._data)

    def __contains__(self, key):
        """
        Returns True if the key in the database property data.
        
        :param key: Property key. 
        :type key: str

        :rtype: bool

        """
        return key in self._data

    def __eq__(self, element):
        """
        Returns True if the elements are equal

        :param element: Element object.
        :type element: Element

        :rtype bool

        """
        return (isinstance(element, Element) and
                element.__class__  == self.__class__ and
                element._id == self._id and
                element._data == self._data)

    def __ne__(self, element):
        """
        Returns True if the elements are not equal.

        :param element: Element object.
        :type element: Element

        :rtype bool

        """
        return not self.__eq__(element)

    def __repr__(self):
        """
        Returns the string representation of the attribute.

        :rtype: unicode

        """
        return self.__unicode__()
    
    def __str__(self):
        """
        Returns the string representation of the attribute.

        :rtype: unicode

        """
        return self.__unicode__()
    
    def __unicode__(self):
        """
        Returns the unicode representation of the attribute.

        :rtype: unicode

        """
        class_name = self.__class__.__name__
        element_uri = self._result.get_uri()
        representation = "<%s: %s>" % (class_name, element_uri)
        return u(representation)    # Python 3

    def __setstate__(self, state):
        config = state['_config']
        client_class = state['_client_class']
        client = client_class(config)
        state['_client'] = client
        state['_vertices'] = VertexProxy(Vertex, client)
        state['_edges'] = EdgeProxy(Edge, client)
        del state['_client_class']
        del state['_config']
        self.__dict__ = state

    def __getstate__(self):
        state = self.__dict__.copy() 
        state['_config'] = self._client.config
        state['_client_class'] = self._client.__class__
        del state['_client']
        del state['_vertices']
        del state['_edges']
        return state
        
    def get(self, name, default_value=None):
        """
        Returns the value of a Python attribute or the default value.

        :param name: Python attribute name.
        :type name: str

        :param default_value: Default value. Defaults to None.
        :type default_value: object

        :rtype: object or None

        """
        # TODO: Why do we need this?
        return getattr(self, name, default_value)


    def data(self):
        """
        Returns the element's property data.

        :rtype: dict

        """
        return self._data

    def map(self):
        """
        Deprecated. Returns the element's property data.

        :rtype: dict

        """
        log.debug("This is deprecated; use data() instead.")
        return self.data()



#
# Vertices
#

class Vertex(Element):
    """
    A container for a Vertex returned by a client proxy.

    :param client: The Client object for the database.
    :type client: Client

    :ivar eid: Element ID. This varname is configurable in Config.
    :ivar _client: Client object.
    :ivar _data: Property data dict returned in Result.
    :ivar _vertices: Vertex proxy object.
    :ivar _edges: Edge proxy object.
    :ivar _initialized: Boolean set to True upon initialization.

    Example::
        
    >>> from bulbs.neo4jserver import Graph
    >>> g = Graph()                   # Create a Neo4j Graph object
    >>> james = g.vertices.get(3)     # Get a vertex from the database
    >>> james.age = 34                # Set a database property
    >>> james.save()                  # Save the vertex in the database
    >>> james.data()                   # Get the database property map
    >>> friends = james.outV("knows") # Return Vertex generator of friends

    """  
    @classmethod
    def get_base_type(cls):
        """
        Returns this element class's base type, which is "vertex". 
        
        :rtype: str
        
        .. admonition:: WARNING 

           Don't override this.

        """
        # Don't override this
        return "vertex"

    @classmethod
    def get_element_key(cls, config):
        """
        Returns the element key. Defaults to "vertex". Override this in Model.

        :param config: Config object.
        :type config: Config

        :rtype: str

        """
        return "vertex"

    @classmethod 
    def get_index_name(cls, config):
        """
        Returns the index name. Defaults to the value of Config.vertex_index. 

        :param config: Config object.
        :type config: Config

        :rtype: str

        """
        return config.vertex_index

    @classmethod 
    def get_proxy_class(cls):
        """
        Returns the proxy class. Defaults to VertexProxy.

        :rtype: class

        """
        return VertexProxy

    def outE(self, label=None, start=None, limit=None):
        """
        Returns the outgoing edges.

        :param label: Optional edge label.
        :type label: str or None

        :rtype: Edge generator

        """
        resp = self._client.outE(self._id, label, start, limit)
        return initialize_elements(self._client,resp)

    def inE(self, label=None, start=None, limit=None):
        """
        Returns the incoming edges.

        :param label: Optional edge label.
        :type label: str or None

        :rtype: Edge generator

        """
        resp = self._client.inE(self._id, label, start, limit)
        return initialize_elements(self._client,resp)

    def bothE(self, label=None, start=None, limit=None):
        """
        Returns the incoming and outgoing edges.

        :param label: Optional edge label.
        :type label: str or None

        :rtype: Edge generator

        """
        resp = self._client.bothE(self._id, label, start, limit)
        return initialize_elements(self._client,resp)

    def outV(self, label=None, start=None, limit=None):
        """
        Returns the out-adjacent vertices.

        :param label: Optional edge label.
        :type label: str or None

        :rtype: Vertex generator

        """
        resp = self._client.outV(self._id, label, start, limit)
        return initialize_elements(self._client,resp)

    def inV(self, label=None, start=None, limit=None):
        """
        Returns the in-adjacent vertices.

        :param label: Optional edge label.
        :type label: str or None

        :rtype: Vertex generator

        """
        resp = self._client.inV(self._id, label, start, limit)
        return initialize_elements(self._client,resp)
        
    def bothV(self, label=None, start=None, limit=None):
        """
        Returns all incoming- and outgoing-adjacent vertices.

        :param label: Optional edge label.
        :type label: str or None

        :rtype: Vertex generator

        """
        resp = self._client.bothV(self._id, label, start, limit)
        return initialize_elements(self._client,resp)

    def save(self):
        """
        Saves the vertex in the database.

        :rtype: Response

        """
        return self._vertices.update(self._id, self._data)
            

class VertexProxy(object):
    """ 
    A proxy for interacting with vertices on the graph database. 

    :param element_class: The element class managed by this proxy instance.
    :type element_class: Vertex class

    :param client: The Client object for the database.
    :type client: Client

    :ivar element_class: Element class.
    :ivar client: Client object.
    :ivar index: The primary index object or None.

    .. note:: The Graph object contains a VertexProxy instance named "vertices".

    Example::
        
    >>> from bulbs.neo4jserver import Graph
    >>> g = Graph()                                  # Create Neo4j Graph
    >>> james = g.vertices.create(name="James")      # Create vertex in DB
    >>> g.vertices.update(james.eid, name="James T") # Update properties
    >>> james = g.vertices.get(james.eid)            # Get vertex (again)
    >>> g.vertices.delete(james.eid)                 # Delete vertex

    """
    def __init__(self,element_class, client):
        assert issubclass(element_class, Vertex)

        self.element_class = element_class
        self.client = client
        self.index = None

        # Add element class to Registry so we can initialize query results.
        self.client.registry.add_class(element_class)

    def create(self, _data=None, _keys=None, **kwds):
        """
        Adds a vertex to the database and returns it.

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: Vertex

        """
        data = build_data(_data, kwds)
        resp = self.client.create_vertex(data, keys=_keys)
        return initialize_element(self.client, resp.results)

    def get(self, _id):
        """
        Returns the vertex for the given ID.

        :param _id: The vertex ID.
        :type _id: int or str

        :rtype: Vertex or None

        """
        try:
            resp = self.client.get_vertex(_id)
            return initialize_element(self.client, resp.results)
        except LookupError:
            return None
        
    def get_or_create(self, key, value, _data=None, _keys=None, **kwds):
        """
        Lookup a vertex in the index and create it if it doesn't exsit.

        :param key: Index key.
        :type key: str

        :param value: Index value.
        :type value: str, int, long

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: Vertex

        """
        # TODO: Make this an atomic Gremlin method
        # TODO: This will only index for non-models if autoindex is True.
        # Relationship Models are set to index by default, but 
        # EdgeProxy doesn't have this method anyway.
        vertex = self.index.get_unique(key, value)
        if vertex is None:
            vertex = self.create(_data, keys=_keys, **kwds)
        return vertex

    def get_all(self):
        """
        Returns all the vertices in the graph.
        
        :rtype: Vertex generator
 
        """
        resp = self.client.get_all_vertices()
        return initialize_elements(self.client, resp)

    def update(self,_id, _data=None, _keys=None, **kwds):
        """
        Updates an element in the graph DB and returns it.

        :param _id: The vertex ID.
        :type _id: int or str

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: Response

        """ 
        # NOTE: this no longer returns an initialized element because not all 
        # Clients return element data, e.g. Neo4jServer retuns nothing.
        data = build_data(_data, kwds)
        self.client.update_vertex(_id, _data, keys=_keys)

    def remove_properties(self, _id):
        """
        Removes all properties from a vertex and returns the response.

        :param _id: The vertex ID.
        :type _id: int or str

        :rtype: Response

        """ 
        return self.client.remove_vertex_properties(_id)
                    
    def delete(self, _id):
        """
        Deletes a vertex from the graph database and returns the response.

        :param _id: The vertex ID.
        :type _id: int or str

        :rtype: Response
        
        """
        return self.client.delete_vertex(_id)


#
# Edges
#

class Edge(Element):
    """
    A container for an Edge returned by a client proxy.

    :param client: The Client object for the database.
    :type client: Client

    :ivar eid: Element ID. This varname is configurable in Config.
    :ivar _client: Client object.
    :ivar _data: Property data dict returned in Result.
    :ivar _vertices: Vertex proxy object.
    :ivar _edges: Edge proxy object.
    :ivar _initialized: Boolean set to True upon initialization.

    Example:
        
    >>> from bulbs.neo4jserver import Graph
    >>> g = Graph()                   # Create a Neo4j Graph
    >>> edge = g.edges.get(8)         # Get an edge from DB

    >>> label = edge.label()          # Return edge label
    >>> outV = edge.outV()            # Return outgoing vertex
    >>> inV = edge.inV()              # Return incoming vertex

    >>> edge._outV                    # Return the outgoing vertex ID
    >>> edge._inV                     # Return the incoming vertex ID

    >>> edge.weight = 0.5             # Set a property
    >>> edge.save()                   # Save properties in DB
    >>> data = edge.data()            # Return property data

    """
    @classmethod
    def get_base_type(cls):
        """
        Returns this element class's base type, which is "edge".
        
        :rtype: str
        
        .. admonition:: WARNING 

           Don't override this.

        """
        #: Don't override this
        return "edge"

    @classmethod
    def get_element_key(cls, config):
        """
        Returns the element key. Defaults to "edge". Override this in Model.

        :rtype: str

        """
        return "edge"

    @classmethod 
    def get_index_name(cls, config):
        """
        Returns the index name. Defaults to the value of Config.edge_index. 

        :rtype: str

        """
        return config.edge_index

    @classmethod 
    def get_proxy_class(cls):
        """
        Returns the proxy class. Defaults to EdgeProxy.

        :rtype: class

        """
        return EdgeProxy

    @property
    def _outV(self):
        """
        Returns the edge's outgoing (start) vertex ID.

        :rtype: int

        """
        return self._result.get_outV()
        
    @property
    def _inV(self):
        """
        Returns the edge's incoming (end) vertex ID.

        :rtype: int

        """
        return self._result.get_inV()
        
    @property
    def _label(self):
        """
        Returns the edge's label.

        :rtype: str

        """
        return self._result.get_label()
        
    def outV(self):
        """
        Returns the outgoing (start) Vertex of the edge.

        :rtype: Vertex

        """
        return self._vertices.get(self._outV)
    
    def inV(self):
        """
        Returns the incoming (end) Vertex of the edge.

        :rtype: Vertex

        """
        return self._vertices.get(self._inV)

    def label(self):
        """
        Returns the edge's label.

        :rtype: str

        """
        return self._result.get_label()

    def save(self):
        """
        Saves the edge in the database.

        :rtype: Response

        """
        return self._edges.update(self._id, self._data)

    
class EdgeProxy(object):
    """ 
    A proxy for interacting with edges on the graph database. 

    :param element_class: The element class managed by this proxy instance.
    :type element_class: Edge class

    :param client: The Client object for the database.
    :type client: Client

    :ivar element_class: Element class
    :ivar client: Client object.
    :ivar index: The primary index object or None.

    .. note:: The Graph object contains an EdgeProxy instance named "edges".

    Example::
        
    >>> from bulbs.neo4jserver import Graph
    >>> g = Graph()                                   # Create Neo4j Graph
    >>> james = g.vertices.create(name="James")       # Create vertex
    >>> julie = g.vertices.create(name="Julie")       # Create vertex
    >>> knows = g.edges.create(james, "knows", julie) # Create edge
    >>> knows = g.edges.get(knows.eid)                # Get edge (again)
    >>> g.edges.update(knows.eid, weight=0.5)         # Update properties
    >>> g.edges.delete(knows.eid)                     # Delete edge

    """
    def __init__(self, element_class, client):
        assert issubclass(element_class, Edge)

        self.element_class = element_class
        self.client = client
        self.index = None

        # Add element class to Registry so we can initialize query results.
        self.client.registry.add_class(element_class)

    def create(self, outV, label, inV, _data=None, _keys=None, **kwds):
        """
        Creates an edge in the database and returns it.
        
        :param outV: The outgoing vertex. 
        :type outV: Vertex or int
                      
        :param label: The edge's label.
        :type label: str

        :param inV: The incoming vertex. 
        :type inV: Vertex or int

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: Edge

        """ 
        assert label is not None
        data = build_data(_data, kwds)
        outV, inV = coerce_vertices(outV, inV)
        resp = self.client.create_edge(outV, label, inV, data, keys=_keys)
        return initialize_element(self.client, resp.results)

    def get(self,_id):
        """
        Retrieves an edge from the database and returns it.

        :param _id: The edge ID.
        :type _id: int or str

        :rtype: Edge or None

        """
        try:
            resp = self.client.get_edge(_id)
            return initialize_element(self.client, resp.results)
        except LookupError:
            return None

    def get_all(self):
        """
        Returns all the edges in the graph.
        
        :rtype: Edge generator
 
        """
        resp = self.client.get_all_edges()
        return initialize_elements(self.client, resp)


    def update(self,_id, _data=None, _keys=None, **kwds):
        """ 
        Updates an edge in the database and returns it. 
        
        :param _id: The edge ID.
        :type _id: int or str

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: Response

        """
        # NOTE: this no longer returns an initialized element because 
        # not all Clients return element data, e.g. Neo4jServer retuns nothing.
        data = build_data(_data, kwds)
        return self.client.update_edge(_id, data, keys=_keys)
                    
    def remove_properties(self, _id):
        """
        Removes all properties from a element and returns the response.
        
        :param _id: The edge ID.
        :type _id: int or str

        :rtype: Response
        
        """
        return self.client.remove_edge_properties(_id)

    def delete(self, _id):
        """
        Deletes a vertex from a graph database and returns the response.
        
        :param _id: The edge ID.
        :type _id: int or str

        :rtype: Response

        """
        return self.client.delete_edge(_id)


#
# Element Utils
#

def build_data(_data, kwds):
    """
    Returns property data dict, regardless of how it was entered.

    :param _data: Optional property data dict.
    :type _data: dict

    :param kwds: Optional property data keyword pairs. 
    :type kwds: dict

    :rtype: dict

    """
    # Doing this rather than defaulting the _data arg to a mutable value
    data = {} if _data is None else _data
    data.update(kwds)
    return data

def coerce_vertices(outV, inV):
    """
    Coerces the outgoing and incoming vertices to integers or strings.

    :param outV: The outgoing vertex. 
    :type outV: Vertex or int
                      
    :param inV: The incoming vertex. 
    :type inV: Vertex or int

    :rtype: tuple

    """
    outV = coerce_vertex(outV)
    inV = coerce_vertex(inV)
    return outV, inV
  
def coerce_vertex(vertex):
    """
    Coerces an object into a vertex ID and returns it.
    
    :param vertex: The object we want to coerce into a vertex ID.
    :type vertex: Vertex object or vertex ID.

    :rtype: int or str

    """
    if isinstance(vertex, Vertex):
        vertex_id = vertex._id
    else:
        # the vertex ID may have been passed in as a string
        # using corece_id to support OrientDB and linked-data URI (non-integer) IDs
        vertex_id = coerce_id(vertex)
    return vertex_id




########NEW FILE########
__FILENAME__ = factory
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Build instances used to interact with the backend clients.

"""

class Factory(object):

    def __init__(self, client):
        self.client = client

    def build_element_proxy(self, element_class, index_class, index_name=None):
        proxy_class = element_class.get_proxy_class()
        element_proxy = proxy_class(element_class, self.client)
        primary_index = self.get_index(element_class,index_class,index_name)
        element_proxy.index = primary_index
        return element_proxy

    def get_index(self, element_class, index_class, index_name=None):
        if index_name is None:
            index_name = element_class.get_index_name(self.client.config)
        index_proxy = self.build_index_proxy(element_class, index_class)
        index = index_proxy.get_or_create(index_name)
        return index

    def build_index_proxy(self, element_class, index_class):
        base_type = element_class.get_base_type()
        proxy_class = index_class.get_proxy_class(base_type)
        index_proxy = proxy_class(index_class, self.client)
        return index_proxy

    


########NEW FILE########
__FILENAME__ = gremlin
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
An interface for executing Gremlin scripts on the client.

"""
from .utils import initialize_elements, get_one_result


class Gremlin(object):
    """
    An interface for executing Gremlin scripts on the client.
    
    :param client: The Client object for the database.
    :type client: Client

    """

    def __init__(self, client):
        self.client = client

    def command(self, script, params=None):
        """
        Returns the raw Result object from an arbitrary Gremlin command.

        :param script: Gremlin script to execute on the client.
        :type script: str
 
        :param params: Optional paramaters to bind to the Gremlin script. 
        :type params: dict or None

        :rtype: Result

        .. note:: Use this when you are executing a command that returns
                  a single result that does not need to be initialized. 

        """
        resp = self.client.gremlin(script,params)
        if resp.total_size > 0:
            result = get_one_result(resp)
            return result.raw

    def query(self, script, params=None):
        """
        Returns initialized Element objects from an arbitrary Gremlin query.

        :param script: Gremlin script to execute on the client.
        :type script: str
 
        :param params: Optional paramaters to bind to the Gremlin script. 
        :type params: dict or None

        :rtype: Generator of objects: Vertex, Edge, Node, or Relationship

        .. note:: Use this when you are returning elements that need to 
                  be initialized.

        """
        resp = self.client.gremlin(script, params)
        return initialize_elements(self.client, resp)
 
    def execute(self, script, params=None):
        """
        Returns the raw Response object from an arbitrary Gremlin script.

        :param script: Gremlin script to execute on the client.
        :type script: str
 
        :param params: Optional paramaters to bind to the Gremlin script. 
        :type params: dict or None

        :rtype: Response

        .. note:: Use this when you are returning element IDs and the actual
                  elements are cached in Redis or Membase. Or, when you're 
                  returning primitives or Table data.

        """
        return self.client.gremlin(script, params)
        

########NEW FILE########
__FILENAME__ = groovy
import os
import io
import re
import string
import sre_parse
import sre_compile
from collections import OrderedDict, namedtuple
from sre_constants import BRANCH, SUBPATTERN
import hashlib
from . import utils

# GroovyScripts is the only public class

#
# The scanner code came from the TED project.
#

# TODO: Simplify this. You don't need group pattern detection.



Method = namedtuple('Method', ['definition', 'signature', 'body', 'sha1'])

class LastUpdatedOrderedDict(OrderedDict):
    """Store items in the order the keys were last added."""

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)


class GroovyScripts(object):
    """
    Store and manage an index of Gremlin-Groovy scripts.

    :parm config: Config object.
    :type config: bulbs.Config

    :param file_path: Path to the base Groovy scripts file.
    :type file_path: str

    :ivar config: Config object.

    :ivar source_files: List containing the absolute paths to the script files,
                        in the order they were added.
    :ivar methods: LastUpdatedOrderedDict mapping Groovy method names to the 
                   Python Method object, which is a namedtuple containing the 
                   Groovy script's definition, signature, body, and sha1.

    .. note:: Use the update() method to add subsequent script files. 
              Order matters. Groovy methods are overridden if subsequently added
              files contain the same method name as a previously added file.

    """
    #: Relative path to the default script file
    default_file = "gremlin.groovy"

    def __init__(self, config, file_path=None):
        self.config = config

        self.source_file_map = OrderedDict()   # source_file_map[file_path] = namespace

        # may have model-specific namespaces
        # methods format: methods[method_name] = method_object
        self.namespace_map = OrderedDict()     # namespace_map[namespace] = methods

        if file_path is None:
            file_path = self._get_default_file()
        # default_namespace is derifed from the default_file so
        # default_namespace will be "gremlin" assuming you don't change default_file
        # or override default_file by passing in an explicit file_path
        self.default_namespace = self._get_filename(file_path) 
        self.update(file_path, self.default_namespace)


    def get(self, method_name, namespace=None):
        """
        Returns the Groovy script with the method name.
        
        :param method_name: Method name of a Groovy script.
        :type method_name: str

        :rtype: str

        """
        # Example: my_method                # uses default_namespace
        #          my_method, my_namespace  # pass in namespace as an arg
        #          my_namespace:my_method   # pass in  namespace via a method_name prefix
        method = self.get_method(method_name, namespace)
        script = method.signature if self.config.server_scripts is True else method.body 
        #script = self._build_script(method_definition, method_signature)
        return script

    def get_methods(self, namespace):
        return self.namespace_map[namespace]

    def get_method(self, method_name, namespace=None):
        """
        Returns a Python namedtuple for the Groovy script with the method name.
        
        :param method_name: Name of a Groovy method.
        :type method_name: str

        :rtype: bulbs.groovy.Method

        """
        namespace, method_name = self._get_namespace_and_method_name(method_name, namespace)
        methods = self.get_methods(namespace)
        return methods[method_name]
 
    def update(self, file_path, namespace=None):
        """
        Updates the script index with the Groovy methods in the script file.

        :rtype: None

        """
        file_path = os.path.abspath(file_path)
        methods = self._get_methods(file_path)
        if namespace is None:
            namespace = self._get_filename(file_path)
        self._maybe_create_namespace(namespace)
        self.source_file_map[file_path] = namespace
        self.namespace_map[namespace].update(methods)

    def refresh(self):
        """
        Refreshes the script index by re-reading the Groovy source files.

        :rtype: None

        """
        for file_path in self.source_file_map:
            namespace = self.source_file_map[file_path]
            methods = self._get_methods(file_path)
            self.namespace_map[namespace].update(methods)

    def _maybe_create_namespace(self, namespace):
        if namespace not in self.namespace_map:
            methods = LastUpdatedOrderedDict()
            self.namespace_map[namespace] = methods

    def _get_filename(self, file_path):
        base_name = os.path.basename(file_path)
        file_name, file_ext = os.path.splitext(base_name)
        return file_name

    def _get_namespace_and_method_name(self, method_name, namespace=None):
        if namespace is None:
            namespace = self.default_namespace
        parts = method_name.split(":") 
        if len(parts) == 2:
            # a namespace explicitly set in method_name takes precedent
            namespace = parts[0]
            method_name = parts[1]
        return namespace, method_name

    def _get_methods(self,file_path):
        return Parser(file_path).get_methods()

    def _get_default_file(self):
        file_path = utils.get_file_path(__file__, self.default_file)
        return file_path

    def _build_script(definition, signature): 
        # This method isn't be used right now...
        # This method is not current (rework it to suit needs).
        script = """
        try {
          current_sha1 = methods[name]
        } catch(e) {
          current_sha1 = null
          methods = [:]
          methods[name] = sha1
        }
        if (current_sha1 == sha1) 
          %s

        try { 
          return %s
        } catch(e) {

          return %s 
        }""" % (signature, definition, signature)
        return script



class Scanner:
    def __init__(self, lexicon, flags=0):
        self.lexicon = lexicon
        self.group_pattern = self._get_group_pattern(flags)
        
    def _get_group_pattern(self,flags):
        # combine phrases into a compound pattern
        patterns = []
        sub_pattern = sre_parse.Pattern()
        sub_pattern.flags = flags
        for phrase, action in self.lexicon:
            patterns.append(sre_parse.SubPattern(sub_pattern, [
                (SUBPATTERN, (len(patterns) + 1, sre_parse.parse(phrase, flags))),
                ]))
        sub_pattern.groups = len(patterns) + 1
        group_pattern = sre_parse.SubPattern(sub_pattern, [(BRANCH, (None, patterns))])
        return sre_compile.compile(group_pattern)

    def get_multiline(self,f,m):
        content = []
        next_line = ''
        while not re.search("^}",next_line):
            content.append(next_line)
            try:
                next_line = next(f)    
            except StopIteration:
                # This will happen at end of file
                next_line = None
                break
        content = "".join(content)       
        return content, next_line

    def get_item(self,f,line):
        # IMPORTANT: Each item needs to be added sequentially 
        # to make sure the record data is grouped properly
        # so make sure you add content by calling callback()
        # before doing any recursive calls
        match = self.group_pattern.scanner(line).match() 
        if not match:
            return
        callback = self.lexicon[match.lastindex-1][1]
        if "def" in match.group():
            # this is a multi-line get
            first_line = match.group()
            body, current_line = self.get_multiline(f,match)
            sections = [first_line, body, current_line]
            content = "\n".join(sections).strip()
            callback(self,content)
            if current_line:
                self.get_item(f,current_line)
        else:
            callback(self,match.group(1))

    def scan(self,file_path):
        fin = io.open(file_path, 'r', encoding='utf-8')    
        for line in fin:
            self.get_item(fin,line)

    
class Parser(object):

    def __init__(self, groovy_file):
        self.methods = OrderedDict()
        # handler format: (pattern, callback)
        handlers = [ ("^def( .*)", self.add_method), ]
        Scanner(handlers).scan(groovy_file)

    def get_methods(self):
        return self.methods

    # Scanner Callback
    def add_method(self,scanner,token):
        method_definition = token
        method_signature = self._get_method_signature(method_definition)
        method_name = self._get_method_name(method_signature)
        method_body = self._get_method_body(method_definition)
        # NOTE: Not using sha1, signature, or the full method right now
        # because of the way the GSE works. It's easier to handle version
        # control by just using the method_body, which the GSE compiles,
        # creates a class out of, and stores in a classMap for reuse.
        # You can't do imports inside Groovy methods so just using the func body 
        sha1 = self._get_sha1(method_definition)
        #self.methods[method_name] = (method_signature, method_definition, sha1)
        method = Method(method_definition, method_signature, method_body, sha1)
        self.methods[method_name] = method

    def _get_method_signature(self,method_definition):
        pattern = '^def(.*){'
        return re.search(pattern,method_definition).group(1).strip()
            
    def _get_method_name(self,method_signature):
        pattern = '^(.*)\('
        return re.search(pattern,method_signature).group(1).strip()

    def _get_method_body(self,method_definition):
        # remove the first and last lines, and return just the method body
        lines = method_definition.split('\n')
        body_lines = lines[+1:-1]
        method_body = "\n".join(body_lines).strip()
        return method_body

    def _get_sha1(self,method_definition):
        # this is used to detect version changes
        method_definition_bytes = method_definition.encode('utf-8')
        sha1 = hashlib.sha1()
        sha1.update(method_definition_bytes)
        return sha1.hexdigest()




#print Parser("gremlin.groovy").get_methods()

########NEW FILE########
__FILENAME__ = json
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
The JSON Type System.

"""
# Python 3
import six
import sys
if sys.version > '3':
    long = int
    unicode = str

from bulbs.base import TypeSystem, Converter
from .utils import to_timestamp, to_datetime, to_datestamp, to_date, json


class DatabaseConverter(Converter):
    """
    Converts Python values to database values.

    .. note:: Python to JSON conversion is usually just a simple pass through.

    """
    def to_string(self, value):
        """
        Converts a Python byte string to a unicode string.
        
        :param value: Property value. 
        :type value: str or None

        :rtype: unicode or None

        :raises: ValueError

        """
        # NOTE: Using unicode instead of str
        if value is not None:
            return unicode(value)

    def to_integer(self, value):
        """
        Passes through a Python integer.

        :param value: Property value. 
        :type value: int or None

        :rtype: int or None

        """
        return value
    
    def to_long(self, value):
        """
        Passes through a Python long.

        :param value: Property value. 
        :type value: long or None

        :rtype: long or None

        """
        return value

    def to_bool(self, value):
        """
        Passes through a Python bool.

        :param value: Property value.
        :type value: bool or None

        :rtype: bool or None

        """
        return value

    def to_float(self, value):
        """
        Passes through a Python float.

        :param value: Property value. 
        :type value: float or None

        :rtype: float or None

        """
        return value

    def to_list(self, value):
        """
        Passes through a Python list.

        :param value: Property value. 
        :type value: list or None

        :rtype: list or None

        """
        return value

    def to_dictionary(self, value):
        """
        Passes through a Python dictionary.

        :param value: Property value. 
        :type value: dict or None

        :rtype: dict or None

        """
        return value

    def to_datetime(self, value):
        """
        Converts a Python datetime object to a timestamp integer.

        :param value: Property value. 
        :type value: datetime or None

        :rtype: int or None

        """
        if value is not None:
            return to_timestamp(value)

    def to_date(self, value):
        """
        Converts a Python date object to a timestamp integer.

        :param value: Property value. 
        :type value: date or None

        :rtype: int or None

        """
        if value is not None:
            return to_datestamp(value)

    def to_null(self, value):
        """
        Passes through a Python None.

        :param value: Property value. 
        :type value: None

        :rtype: None

        """
        return value

    def to_document(self, value):
        """
        Converts a Python object to a json string

        :param value: Property value.
        :type value: dict or list or None

        :rtype: unicode or None
        """
        if value is not None:
            return unicode(json.dumps(value))


class PythonConverter(Converter):
    """Converts database values to Python values."""

    # TODO: Why are we checking if value is not None?
    # This is supposed to be handled elsewhere.
    # Conversion exceptions are now handled in Property.convert_to_python() 
    
    def to_string(self, value):
        """
        Converts a JSON string to a Python unicode string.
        
        :param value: Property value. 
        :type value: str or None

        :rtype: unicode or None

        :raises: ValueError

        """
        if value is not None:
            return unicode(value)

    def to_integer(self, value):
        """
        Converts a JSON number to a Python integer.

        :param value: Property value. 
        :type value: int or None

        :rtype: int or None

        :raises: ValueError

        """
        if value is not None:
            return int(value)

    def to_long(self, value):
        """
        Converts a JSON number to a Python long.

        :param value: Property value. 
        :type value: long or None

        :rtype: long or None

        :raises: ValueError

        """
        if value is not None:
            return long(value)

    def to_float(self, value):
        """
        Converts a JSON number to a Python float.

        :param value: Property value. 
        :type value: float or None

        :rtype: float or None

        :raises: ValueError

        """
        if value is not None:
            return float(value)              

    def to_bool(self, value):
        """
        Converts a JSON boolean value to a Python bool.

        :param value: Property value.
        :type value: bool or None

        :rtype: bool or None

        :raises: ValueError

        """
        if value is not None:
            return bool(value)

    def to_list(self, value):
        """
        Converts a JSON list to a Python list.

        :param value: Property value. 
        :type value: list or None

        :rtype: list or None

        :raises: ValueError

        """
        if value is not None:
            return list(value)

    def to_dictionary(self, value):
        """
        Converts a JSON map to a Python dictionary.         

        :param value: Property value. 
        :type value: dict or unicode or None

        :rtype: dict or None

        :raises: ValueError

        """
        if value is None:
            return None

        if isinstance(value, unicode):
            return json.loads(value)

        return dict(value)

    def to_datetime(self, value):
        """
        Converts a JSON integer timestamp to a Python datetime object.

        :param value: Property value. 
        :type value: int or None

        :rtype: datetime or None

        :raises: ValueError

        """
        if value is not None:
            return to_datetime(value)
            
    def to_date(self, value):
        """
        Converts a JSON integer timestamp to a Python date object.

        :param value: Property value. 
        :type value: int or None

        :rtype: date or None

        :raises: ValueError

        """
        if value is not None:
            return to_date(value)

    def to_null(self, value):
        """
        Converts a JSON null to a Python None.

        :param value: Property value. 
        :type value: None

        :rtype: None

        :raises: ValueError

        """
        if value is not None:
            raise ValueError

        return None


class JSONTypeSystem(TypeSystem):
    """
    Converts database properties to and from their JSON representations.

    :cvar content_type: The backend client's content type.
    :cvar database: Converter object. Converts Python values to database values.
    :cvar python: Converter object. Converts database values to Python values.

    """
    content_type = "application/json"

    database = DatabaseConverter()
    python = PythonConverter()
    












########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
# 
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Base classes for modeling domain objects that wrap vertices and edges.

"""
import six  # Python 3
import inspect
import types
from collections import Callable

from bulbs.property import Property
from bulbs.element import Element, Vertex, VertexProxy, Edge, EdgeProxy, \
    coerce_vertices, build_data
from bulbs.utils import initialize_element, get_logger


# Model Modes
NORMAL = 1
STRICT = 2

log = get_logger(__name__)


class ModelMeta(type):
    """Metaclass used to set database Property definitions on Models."""

    def __init__(cls, name, base, namespace):
        """Store Property instance definitions on the class as a dictionary.""" 

        # Get inherited Properties
        cls._properties = cls._get_initial_properties()
        
        # Add new Properties
        cls._register_properties(namespace)

    def _get_initial_properties(cls):
        """
        Get Properties defined in the parent and inherit them.

        :rtype: dict

        """
        try: 
            parent_properties = getattr(cls, '_properties')
            properties = parent_properties.copy() 
        except:
            # Set it to an empty dict if the Model doesn't have a parent Model. 
            properties = {}
        return properties
            
    def _register_properties(cls, namespace):
        """
        Loop through the class namespace looking for Property instances.

        :param namespace: Class namespace
        :type namespace: dict

        :rtype: None

        """

        # e.g. age = Integer()
        for key in namespace: # Python 3
            value = namespace[key]

            assert key not in cls._properties, \
                "Can't redefine Property '%s'" % key

            if isinstance(value, Property):
                property_instance = value  # for clarity
                cls._properties[key] = property_instance
                cls._set_property_name(key,property_instance)
                cls._initialize_property(key,property_instance)
                # not doing this b/c some Properties are calculated at savetime
                #delattr(cls, key) 
                            
    def _set_property_name(cls, key, property_instance):
        """
        Set Property name to attribute key unless explicitly set via kwd param.

        :param key: Class attribute key
        :type key: str

        :param property_instance: Property instance
        :type property_instance bulbs.property.Property

        :rtype None

        """
        if property_instance.name is None:
            property_instance.name = key

    def _initialize_property(cls, key, property_instance):
        """
        Set the Model class attribute based on the Property definition.

        :param key: Class attribute key
        :type key: str

        :param property_instance: Property instance
        :type property_instance bulbs.property.Property

        """
        if property_instance.fget:
            # TODO: make this configurable
            # this is a calculated property (should it persist?)
            # wrapped fset and fdel in str() to make the default None not 
            # error on getattr
            fget = getattr(cls, property_instance.fget)
            # TODO: implement fset and fdel (maybe)
            #fset = getattr(cls, str(property_instance.fset), None)
            #fdel = getattr(cls, str(property_instance.fdel), None)
            fset = None
            fdel = None
            property_value = property(fget, fset, fdel)
        else:
            property_value = None
        setattr(cls, key, property_value)


class Model(six.with_metaclass(ModelMeta, object)):  # Python 3
    """Abstract base class for Node and Relationship container classes."""
    

    #: The mode for saving attributes to the database. 
    #: If set to STRICT, only defined Properties are saved.
    #: If set to NORMAL, all attributes are saved. 
    #: Defaults to NORMAL. 
    __mode__ = NORMAL
    
    #: A dict containing the database Property instances.
    _properties = None
    

    def __setattr__(self, key, value):
        """
        Set model attributes, possibly coercing database Properties to the 
        defined types.

        :param key: Attribute key
        :type key: str

        :param value: Attribute value
        :type value: object
        
        :rtype: None

        """
        if key in self._properties:
            self._set_database_property(key, value)
        else:
            # If _mode = STRICT, set an instance var, which isn't saved to DB.
            # If _mode = NORMAL, store in self._data, which is saved to DB
            self._set_normal_attribute(key, value)

    def _set_database_property(self, key, value):
        """
        Set Property attributes after coercing them into the defined types.

        :param key: Attribute key
        :type key: str

        :param value: Attribute value
        :type value: object
        
        :rtype: None

        """
        # we want Model Properties to be set be set as actual attributes
        # because they can be real Python propertes or calculated values,
        # which are calcualted/set upon each save().
        # Don't set calculated (fget) properties; they're calculated at save.
        if not self._is_calculated_property(key):
            value = self._coerce_property_value(key, value)
            object.__setattr__(self, key, value)

    def _set_normal_attribute(self, key, value):
        """
        Set normal/non-database Property attributes, depending on the __mode__.

        :param key: Attribute key
        :type key: str

        :param value: Attribute value
        :type value: object
        
        :rtype: None

        """
        if self.__mode__ == STRICT:
            # Set as a Python attribute, which won't be saved to the database.
            object.__setattr__(self, key, value)
        else:
            # Store the attribute in self._data, which are saved to database.
            Element.__setattr__(self, key, value)        

    def _is_calculated_property(self, key):
        """
        Returns True if the Property is a cacluated property, i.e. has fget set.

        :param key: Attribute key
        :type key: str

        :rtype: bool

        """
        # TODO: fget works, but fset, fdel have not been tested
        property_instance = self._properties[key]
        return (property_instance.fget is not None)

    def _coerce_property_value(self, key, value):
        """
        Coerce database Property value into its defined type.

        :param key: Attribute key
        :type key: str

        :param value: Attribute value
        :type value: object
        
        :rtype: object

        """
        if value is not None:
            property_instance = self._properties[key]
            value = property_instance.coerce(key, value)
        return value

    def _set_property_defaults(self):
        """
        Set the default values for all the database Properties.

        :rtype: None

        """
        for key in self._properties:
            default_value = self._get_property_default(key)     
            setattr(self, key, default_value)
            
    def _get_property_default(self, key):
        """
        Coerce database Property value into its defined type.

        :param key: Attribute key
        :type key: str

        :rtype: object

        """
        # TODO: make this work for model methods?
        # The value entered could be a scalar or a function name
        # Should we defer the call until all properties are set, 
        # or only for calculated properties?
        property_instance = self._properties[key]
        default_value = property_instance.default
        if isinstance(default_value, Callable):
            default_value = default_value()
        return default_value

    def _set_keyword_attributes(self, _data, kwds):
        """
        Sets Python attributes using the _data and keywords passed in by user.

        :param _data: Data that was passed in via a dict.
        :type _data: dict

        :param kwds: Data that was passed in via name/value pairs.
        :type kwds: dict

        :rtype: None

        """
        # NOTE: keys may have been passed in that are not defined as Properties
        data = build_data(_data, kwds)
        for key in data:    # Python 3
            value = data[key]  
            # Notice that __setattr__ is overloaded
            setattr(self, key, value)

    def _set_property_data(self):
        """
        Sets Property data after it is retrieved from the DB.

        :rtype: None

        .. note:: Sets the value to None if it's an invalid type.

        """
        type_system = self._client.type_system
        for key in self._properties:   # Python 3
            
            # Don't set calculted property values, i.e. those with fset defined.
            if self._is_calculated_property(key): continue

            property_instance = self._properties[key]
            #name = property_instance.name
            value = self._data.get(key, None)
            value = property_instance.convert_to_python(type_system, key, value)

            # TODO: Maybe need to wrap this in try/catch too.
            # Notice that __setattr__ is overloaded. No need to coerce it twice.
            object.__setattr__(self, key, value)
            
    def _get_property_data(self):
        """
        Returns validated Property data, ready to be saved in the DB.

        :rtype: dict

        """
        # If __mode__ is STRICT, data set to empty; otherwise set to self._data
        data = self._get_initial_data()

        type_var = self._client.config.type_var
        type_system = self._client.type_system

        if hasattr(self, type_var):
            # Add element_type to the database properties to be saved;
            # but don't worry about "label", it's always saved on the edge.
            data[type_var] = object.__getattribute__(self, type_var)

        # Convert database Property values to their database types.
        for key in self._properties:  # Python 3
            property_instance = self._properties[key]
            value = self._get_property_value(key)
            property_instance.validate(key, value)
            #name = property_instance.name
            db_value = property_instance.convert_to_db(type_system, key, value)
            data[key] = db_value

        return data

    def _get_initial_data(self):
        """
        Returns empty dict if __mode__ is set to STRICT, otherwise self._data.
        
        :rtype: dict

        """
        data = {} if self.__mode__ == STRICT else self._data.copy()
        return data

    def _get_property_value(self, key):
        """
        Returns the value of a Property, calculated via a function if needed.

        :param key: Attribute key
        :type key: str

        :rtype: object

        """
        # Notice that __getattr__ is overloaded in Element.
        value = object.__getattribute__(self, key)
        if isinstance(value, Callable):
            return value()
        return value

    def get_bundle(self, _data=None, **kwds):
        """
        Returns a tuple contaning the property data, index name, and index keys.

        :param _data: Data that was passed in via a dict.
        :type _data: dict

        :param kwds: Data that was passed in via name/value pairs.
        :type kwds: dict

        :rtype: tuple

        """
        self._set_property_defaults()   
        self._set_keyword_attributes(_data, kwds)
        data = self._get_property_data()
        index_name = self.get_index_name(self._client.config)
        keys = self.get_index_keys()
        return data, index_name, keys

    def get_index_keys(self):
        """
        Returns Property keys to index in DB. Defaults to None (index all keys).

        :rtype: list or None

        """
        # TODO: Derive this from Property definitions.
        return None

    def get_property_keys(self):
        """
        Returns a list of all the Property keys.

        :rtype: list

        """
        return self._properties.keys()

    def data(self):
        """
        Returns a the element's property data.

        :rtype: dict

        """
        data = dict()
        if self.__mode__ == NORMAL:
            data = self._data

        for key in self._properties: 
            # TODO: make this work for calculated values.
            # Calculated props shouldn't be stored, but components should be.
            data[key] = object.__getattribute__(self, key)
        return data

    def map(self):
        """
        Deprecated. Returns the element's property data.

        :rtype: dict

        """
        log.debug("This is deprecated; use data() instead.")
        return self.data()

    def __check__(self,data):
        """
        Override this method in the child class to throw an exception if the data dictionary is invalid
        
        :param data: Collection of parameters to be set for this Model
        :type data: dict

        """
        pass

class Node(Model, Vertex):
    """ 
    Abstract base class used for creating a Vertex Model.
 
    It's used to create classes that model domain objects, and it's not meant 
    to be used directly. To use it, create a subclass specific to the type of 
    data you are storing. 

    Example model declaration::

        # people.py

        from bulbs.model import Node
        from bulbs.property import String, Integer

        class Person(Node):
            element_type = "person"
            
            name = String(nullable=False)
            age = Integer()

    Example usage::

        >>> from people import Person
        >>> from bulbs.neo4jserver import Graph
        >>> g = Graph()

        # Add a "people" proxy to the Graph object for the Person model:
        >>> g.add_proxy("people", Person)

        # Use it to create a Person node, which also saves it in the database:
        >>> james = g.people.create(name="James")
        >>> james.eid
        3
        >>> james.name
        'James'

        # Get the node (again) from the database by its element ID:
        >>> james = g.people.get(james.eid)

        # Update the node and save it in the database:
        >>> james.age = 34
        >>> james.save()

        # Lookup people using the Person model's primary index:
        >>> nodes = g.people.index.lookup(name="James")
        
    """
    #: The mode for saving attributes to the database. 
    #: If set to STRICT, only defined Properties are saved.
    #: If set to NORMAL, all attributes are saved. 
    #: Defaults to NORMAL. 
    __mode__ = NORMAL
    
    #: A dict containing the database Property instances.
    _properties = None

    element_type = None

    @classmethod
    def get_element_type(cls, config):
        """
        Returns the element type.

        :param config: Config object.
        :type config: bulbs.config.Config

        :rtype: str

        """
        element_type = getattr(cls, config.type_var)
        return element_type

    @classmethod
    def get_element_key(cls, config):
        """
        Returns the element key.

        :param config: Config object.
        :type config: bulbs.config.Config

        :rtype: str

        """
        return cls.get_element_type(config)

    @classmethod 
    def get_index_name(cls, config):
        """
        Returns the index name. 

        :param config: Config object.
        :type config: bulbs.config.Config

        :rtype: str

        """
        return cls.get_element_type(config)

    @classmethod 
    def get_proxy_class(cls):
        """
        Returns the proxy class. 

        :param config: Config object.
        :type config: bulbs.config.Config

        :rtype: class

        """
        return NodeProxy


    def save(self):
        """
        Saves/updates the element's data in the database.

        :rtype: None

        """
        data = self._get_property_data()
        self.__check__(data)
        index_name = self.get_index_name(self._client.config)
        keys = self.get_index_keys()
        self._client.update_indexed_vertex(self._id, data, index_name, keys)
        
    #
    # Override the _create and _update methods to cusomize behavior.
    #
    
    def _create(self, _data, kwds):  
        """
        Creates a vertex in the database; called by the NodeProxy create() method.

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: None
        
        """
        # bundle is an OrderedDict containing data, index_name, and keys
        data, index_name, keys = self.get_bundle(_data, **kwds)
        self.__check__(data)
        resp = self._client.create_indexed_vertex(data, index_name, keys)
        result = resp.one()
        self._initialize(result)
        
    def _update(self, _id, _data, kwds):
        """
        Updates a vertex in the database; called by NodeProxy update() method.
        
        :param _id: Element ID.
        :param _id: int or str

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: None
        
        """
        data, index_name, keys = self.get_bundle(_data, **kwds)
        self.__check__(data)
        resp = self._client.update_indexed_vertex(_id, data, index_name, keys)
        result = resp.one()
        self._initialize(result)
        
    def _initialize(self, result):
        """
        Initializes the element. Initialize all non-DB attributes here.

        :param result: Result object.
        :type result: Result

        :rtype: None

        ..note:: Called by _create, _update, and utils.initialize_element. 

        """
        Vertex._initialize(self,result)
        self._initialized = False
        self._set_property_data()
        self._initialized = True


class Relationship(Model, Edge):
    """ 
    Abstract base class used for creating a Relationship Model.
 
    It's used to create classes that model domain objects, and it's not meant 
    to be used directly. To use it, create a subclass specific to the type of 
    data you are storing. 

    Example usage for an edge between a blog entry node and its creating user::

        # people.py

        from bulbs.model import Relationship
        from bulbs.properties import DateTime
        from bulbs.utils import current_timestamp

        class Knows(Relationship):

            label = "knows"

            created = DateTime(default=current_timestamp, nullable=False)


    Example usage::

          >>> from people import Person, Knows
          >>> from bulbs.neo4jserver import Graph
          >>> g = Graph()

          # Add proxy interfaces to the Graph object for each custom Model
          >>> g.add_proxy("people", Person)
          >>> g.add_proxy("knows", Knows)

          # Create two Person nodes, which are automatically saved in the DB
          >>> james = g.people.create(name="James")
          >>> julie = g.people.create(name="Julie")

          # Create a "knows" relationship between James and Julie:
          >>> knows = g.knows.create(james,julie)
          >>> knows.timestamp

          # Get the people James knows (the outgoing vertices labeled "knows")
          >>> friends = james.outV('knows')

    """
    label = None

    @classmethod
    def get_label(cls, config):
        """
        Returns the edge's label.

        :param config: Config object.
        :type config: bulbs.config.Config

        :rtype: str

        """
        label = getattr(cls, config.label_var)
        return label

    @classmethod
    def get_element_key(cls, config):
        """
        Returns the element key.

        :param config: Config object.
        :type config: bulbs.config.Config

        :rtype: str

        """
        return cls.get_label(config)

    @classmethod 
    def get_index_name(cls, config):
        """
        Returns the index name. 

        :param config: Config object.
        :type config: bulbs.config.Config

        :rtype: str

        """
        return cls.get_label(config)

    @classmethod 
    def get_proxy_class(cls):
        """
        Returns the proxy class. 

        :param config: Config object.
        :type config: bulbs.config.Config

        :rtype: class

        """
        return RelationshipProxy


    def save(self):
        """
        Saves/updates the element's data in the database.

        :rtype: None

        """
        data = self._get_property_data()
        self.__check__(data)

        index_name = self.get_index_name(self._client.config)
        keys = self.get_index_keys()
        self._client.update_indexed_edge(self._id, data, index_name, keys)

    #
    # Override the _create and _update methods to customize behavior.
    #

    def _create(self, outV, inV, _data, kwds):
        """
        Creates an edge in the DB; called by RelatinshipProxy create() method.

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: None
        
        """
        label = self.get_label(self._client.config)
        outV, inV = coerce_vertices(outV, inV)
        data, index_name, keys = self.get_bundle(_data, **kwds)
        self.__check__(data)
        resp = self._client.create_indexed_edge(outV, label, inV, data, index_name, keys)
        result = resp.one()
        self._initialize(result)
        
    def _update(self, _id, _data, kwds):
        """
        Updates an edge in DB; called by RelationshipProxy update() method.
        
        :param _id: Element ID.
        :param _id: int or str

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: None
        
        """
        data, index_name, keys = self.get_bundle(_data, **kwds)
        self.__check__(data)
        resp = self._client.update_indexed_edge(_id, data, index_name, keys)
        result = resp.one()
        self._initialize(result)

    def _initialize(self,result):
        """
        Initializes the element. Initialize all non-DB attributes here.

        :param result: Result object.
        :type result: Result

        :rtype: None

        ..note:: Called by _create, _update, and utils.initialize_element. 

        """
        Edge._initialize(self,result)
        self._initialized = False
        self._set_property_data()
        self._initialized = True


class NodeProxy(VertexProxy):

    def create(self, _data=None, **kwds):
        """
        Adds a vertex to the database and returns it.

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: Node

        """
        node = self.element_class(self.client)
        node._create(_data, kwds)
        return node
        
    def update(self, _id, _data=None, **kwds):
        """
        Updates an element in the graph DB and returns it.

        :param _id: The vertex ID.
        :type _id: int or str

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: Node

        """ 
        node = self.element_class(self.client)
        node._update(_id, _data, kwds)
        return node

    def get_all(self):
        """
        Returns all the elements for the model type.
        
        :rtype: Node generator
 
        """

        config = self.client.config
        type_var = config.type_var
        element_type = self.element_class.get_element_type(config)
        return self.index.lookup(type_var,element_type)

    def get_property_keys(self):
        """
        Returns a list of all the Property keys.

        :rtype: list

        """
        return self.element_class._properties.keys()

class RelationshipProxy(EdgeProxy):

    def create(self, outV, inV, _data=None, **kwds):
        """
        Creates an edge in the database and returns it.
        
        :param outV: The outgoing vertex. 
        :type outV: Vertex or int
              
        :param inV: The incoming vertex. 
        :type inV: Vertex or int

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: Relationship

        """ 
        relationship = self.element_class(self.client)
        relationship._create(outV, inV, _data, kwds)
        return relationship

    def update(self, _id, _data=None, **kwds):
        """ 
        Updates an edge in the database and returns it. 
        
        :param _id: The edge ID.
        :type _id: int or str

        :param _data: Optional property data dict.
        :type _data: dict

        :param kwds: Optional property data keyword pairs. 
        :type kwds: dict

        :rtype: Relationship

        """
        relationship = self.element_class(self.client)
        relationship._update(_id, _data, kwds)
        return relationship

    def get_all(self):
        """
        Returns all the relationships for the label.

        :rtype: Relationship generator
 
        """
        # TODO: find a blueprints method that returns all edges for a given 
        # label because you many not want to index edges
        config = self.client.config
        label_var = config.label_var
        label = self.element_class.get_label(config)
        return self.index.lookup(label_var,label)


    def get_property_keys(self):
        """
        Returns a list of all the Property keys.

        :rtype: list

        """
        return self.element_class._properties.keys()
        

########NEW FILE########
__FILENAME__ = batch
from .client import Neo4jRequest, Neo4jClient

#
# Batch isn't fully baked yet
#

class Neo4jBatchRequest(Neo4jRequest):
    """Makes HTTP requests to Neo4j Server and returns a Neo4jResponse.""" 
    
    def _initialize(self):
        self.messages = []
        self.message_id = 0

    def request(self, method, path, params):
        """
        Adds request to the messages list and returns a placeholder.

        :param method: HTTP method: GET, PUT, POST, or DELETE.
        :type method: str

        :param path: Path to the server resource, relative to the root URI.
        :type path: str

        :param params: Optional URI parameters for the resource.
        :type params: dict

        :rtype: str

        """
                
        return self.add_message(method, path, params)

        # return self 
        # would allow you to do self.request.post(path, params).send()
        # that won't work unless you always want to go throught the batch interface


    def add_message(self, method, path, params):
        message_id = self.next_id()
        message = dict(method=method, to=path, body=params, id=message_id)
        self.messages.append(message)
        return self.placeholder(message_id)

    def next_id(self):
        self.message_id = self.message_id + 1
        return self.message_id

    def placeholder(self, message_id):
        return "{%d}" % message_id

    def send(self):
        """
        Convenience method that sends request messages to the client.

        :param message: Tuple containing: (HTTP method, path, params)
        :type path: tuple

        :param params: Optional URI params for the resource.
        :type params: dict

        :rtype: Response

        """
        path = "batch"
        params = self.messages
        return Neo4jRequest.post(self, path, params)

    def get_messages(self):
        return self.messages

    def clear(self):
        self._initialize()


class Neo4jBatchClient(Neo4jClient):

    request_class = Neo4jBatchRequest

    # Batch isn't fully baked yet

    # Batch try (old -- from Neo4jClient)...
    #def create_indexed_vertex(self,data,index_name,keys=None):
    #    """Creates a vertex, indexes it, and returns the Response."""
    #    batch = Neo4jBatch(self.client)
    #    placeholder = batch.add(self.message.create_vertex(data))
    #    for key in keys:
    #        value = data.get(key)
    #        if value is None: continue
    #        batch.add(self.message.put_vertex(index_name,key,value,placeholder))
    #    resp = batch.send()
    #    #for result in resp.results:


    def send(self):
        return self.request.send()

    def get_messages(self):
        return self.request.get_messages()

    def clear(self):
        self.request.clear()



########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Bulbs supports pluggable backends. This is the Neo4j Server client.

"""
import re

from bulbs.config import Config, DEBUG, ERROR
from bulbs.registry import Registry
from bulbs.utils import get_logger

# specific to this client
from bulbs.json import JSONTypeSystem
from bulbs.base import Client, Response, Result
from bulbs.rest import Request, RESPONSE_HANDLERS, server_error
from bulbs.utils import json, build_path, get_file_path, urlsplit
from bulbs.groovy import GroovyScripts

# TODO: Clean up and generalize Yaml
from .cypher import Cypher, Yaml


# The default URI
NEO4J_URI = "http://localhost:7474/db/data/"

# The logger defined in Config
log = get_logger(__name__)

# Neo4j Server resource paths
# TODO: local path vars would be faster
vertex_path = "node"
edge_path = "relationship"
index_path = "index"
gremlin_path = "ext/GremlinPlugin/graphdb/execute_script"
cypher_path = "cypher"


class Neo4jResult(Result):
    """
    Container class for a single result, not a list of results.

    :param result: The raw result.
    :type result: dict

    :param config: The graph Config object.
    :type config: Config 

    :ivar raw: The raw result.
    :ivar data: The data in the result.

    """
    def __init__(self, result, config):
        self.config = config

        # The raw result.
        self.raw = result

        # The data in the result.
        self.data = self._get_data(result)

        self.type_map = dict(node="vertex",relationship="edge")

    def get_id(self):
        """
        Returns the element ID.

        :rtype: int

        """
        uri = self.raw.get('self')
        return self._parse_id(uri)
       
    def get_type(self):
        """
        Returns the element's base type, either "vertex" or "edge".

        :rtype: str

        """
        uri = self.get_uri()
        neo4j_type = self._parse_type(uri)
        return self.type_map[neo4j_type]
        
    def get_data(self):
        """
        Returns the element's property map.

        :rtype: dict

        """
        return self.data

    def get_uri(self):
        """
        Returns the element URI.

        :rtype: str

        """
        return self.raw.get('self')
                 
    def get_outV(self):
        """
        Returns the ID of the edge's outgoing vertex (start node).

        :rtype: int

        """
        uri = self.raw.get('start')
        return self._parse_id(uri)
        
    def get_inV(self):
        """
        Returns the ID of the edge's incoming vertex (end node).

        :rtype: int

        """
        uri = self.raw.get('end')
        return self._parse_id(uri)

    def get_label(self):
        """
        Returns the edge label (relationship type).

        :rtype: str

        """
        return self.raw.get('type')

    def get_index_name(self):
        """
        Returns the index name.

        :rtype: str

        """
        return self.raw.get('name')
   
    def get_index_class(self):
        """
        Returns the index class, either "vertex" or "edge".

        :rtype: str

        """
        uri = self.raw.get('template') 
        neo4j_type = self._parse_index_type(uri)
        return self.type_map[neo4j_type]

    def get(self, attribute):
        """
        Returns the value of a client-specific attribute.
        
        :param attribute: Name of the attribute. 
        :type attribute: str

        :rtype: str

        """
        return self.raw[attribute]

    def _get_data(self, result):
        if type(result) is dict:
            return result.get('data') 

    def _parse_id(self, uri):
        """Parses the ID out of a URI."""
        if uri:
            _id = int(uri.rpartition('/')[-1])
            return _id

    def _parse_type(self, uri):
        """Parses the type ouf of a normal URI."""
        if uri:
            root_uri = uri.rpartition('/')[0]
            neo4j_type = root_uri.rpartition('/')[-1]
            return neo4j_type
    
    def _parse_index_type(self, uri):
        """Parses the type out of an index URI."""
        if uri:
            path = urlsplit(uri).path
            segments = path.split("/")
            neo4j_type = segments[-4]
            return neo4j_type


class Neo4jResponse(Response):
    """
    Container class for the server response.

    :param response: httplib2 response: (headers, content).
    :type response: tuple

    :param config: Config object.
    :type config: bulbs.config.Config

    :ivar config: Config object.
    :ivar headers: httplib2 response headers, see:
        http://httplib2.googlecode.com/hg/doc/html/libhttplib2.html
    :ivar content: A dict containing the HTTP response content.
    :ivar results: A generator of Neo4jResult objects, a single Neo4jResult object, 
        or None, depending on the number of results returned.
    :ivar total_size: The number of results returned.
    :ivar raw: Raw HTTP response. Only set when log_level is DEBUG.

    """
    result_class = Neo4jResult

    def __init__(self, response, config):
        self.config = config
        self.handle_response(response)
        self.headers = self.get_headers(response)
        self.content = self.get_content(response)
        self.results, self.total_size = self.get_results()
        self.raw = self._maybe_get_raw(response, config)

    def _maybe_get_raw(self,response, config):
        """Returns the raw response if in DEBUG mode."""
        # don't store raw response in production else you'll bloat the obj
        if config.log_level == DEBUG:
            return response

    def handle_response(self, response):
        """
        Check the server response and raise exception if needed.
        
        :param response: httplib2 response: (headers, content).
        :type response: tuple

        :rtype: None

        """
        headers, content = response

        # Temporary hack to catch Gremlin Plugin exceptions that return 200 status
        # See https://github.com/neo4j/community/issues/343
        # Example: '"java.lang.IllegalArgumentException: Unknown property type on..."'
        if re.search(b"^\"java.(.*).Exception:", content):
            # raise error...
            server_error(response)
        
        response_handler = RESPONSE_HANDLERS.get(headers.status)
        response_handler(response)

    def get_headers(self, response):
        """
        Returns a dict containing the headers from the response.

        :param response: httplib2 response: (headers, content).
        :type response: tuple
        
        :rtype: httplib2.Response

        """
        # response is a tuple containing (headers, content)
        # headers is an httplib2 Response object, content is a string
        # see http://httplib2.googlecode.com/hg/doc/html/libhttplib2.html
        headers, content = response
        return headers

    def get_content(self, response):
        """
        Returns a dict containing the content from the response.
        
        :param response: httplib2 response: (headers, content).
        :type response: tuple
        
        :rtype: dict or None

        """
        # content is a JSON string
        headers, content = response

        # Neo4jServer returns empty content on update
        if content:
            content = json.loads(content.decode('utf-8'))
            return content

    def get_results(self):
        """
        Returns the results contained in the response.

        :return:  A tuple containing two items: 1. Either a generator of Neo4jResult objects, 
                  a single Neo4jResult object, or None, depending on the number of results 
                  returned; 2. An int representing the number results returned.
        :rtype: tuple

        """
        if type(self.content) == list:
            results = (self.result_class(result, self.config) for result in self.content)
            total_size = len(self.content)
        elif self.content and self.content != "null":
            # Checking for self.content.get('data') won't work b/c the data value
            # isn't returned for edges with no properties;
            # and self.content != "null": Yep, the null thing is sort of a hack. 
            # Neo4j returns "null" if Gremlin scripts don't return anything.
            results = self.result_class(self.content, self.config)
            total_size = 1
        else:
            results = None
            total_size = 0
        return results, total_size

    def _set_index_name(self, index_name):
        """Sets the index name to the raw result."""
        # this is pretty much a hack becuase neo4j doesn't include the index name in response
        self.results.raw['name'] = index_name
        

class Neo4jRequest(Request):
    """Makes HTTP requests to Neo4j Server and returns a Neo4jResponse.""" 
    
    response_class = Neo4jResponse


class Neo4jClient(Client):
    """
    Low-level client that sends a request to Neo4j Server and returns a response.

    :param config: Optional Config object. Defaults to default Config.
    :type config: bulbs.config.Config

    :ivar config: Config object.
    :ivar registry: Registry object.
    :ivar scripts: GroovyScripts object.  
    :ivar type_system: JSONTypeSystem object.
    :ivar request: Neo4jRequest object.

    Example:

    >>> from bulbs.neo4jserver import Neo4jClient
    >>> client = Neo4jClient()
    >>> response = client.get_all_vertices()
    >>> result = response.results.next()

    """ 
    #: Default URI for the database.
    default_uri = NEO4J_URI

    #: Request class for the Client.
    request_class = Neo4jRequest


    def __init__(self, config=None):
        self.config = config or Config(self.default_uri)
        self.registry = Registry(self.config)
        self.type_system = JSONTypeSystem()
        self.request = self.request_class(self.config, self.type_system.content_type)

        # Neo4j supports Gremlin so include the Gremlin-Groovy script library
        self.scripts = GroovyScripts(self.config)
        
        # Also include the Neo4j Server-specific Gremlin-Groovy scripts
        scripts_file = get_file_path(__file__, "gremlin.groovy")
        self.scripts.update(scripts_file)

        # Add it to the registry. This allows you to have more than one scripts namespace.
        self.registry.add_scripts("gremlin", self.scripts)
        

    # Gremlin

    def gremlin(self, script, params=None): 
        """
        Executes a Gremlin script and returns the Response.

        :param script: Gremlin script to execute.
        :type script: str

        :param params: Param bindings for the script.
        :type params: dict

        :rtype: Neo4jResponse

        """
        path = gremlin_path
        params = dict(script=script, params=params)
        return self.request.post(path, params)

    # Cypher

    def cypher(self, query, params=None):
        """
        Executes a Cypher query and returns the Response.

        :param query: Cypher query to execute.
        :type query: str

        :param params: Param bindings for the query.
        :type params: dict

        :rtype: Neo4jResponse

        """
        path = cypher_path
        params = dict(query=query,params=params)
        resp = self.request.post(path, params)

        # Cypher data hack
        resp.total_size = len(resp.results.data)
        resp.results = (Neo4jResult(result[0], self.config) for result in resp.results.data)
        return resp

    # Vertex Proxy

    def create_vertex(self, data, keys=None):
        """
        Creates a vertex and returns the Response.

        :param data: Property data.
        :type data: dict

        :rtype: Neo4jResponse

        """
        if keys or self.config.autoindex is True:
            index_name = self.config.vertex_index
            return self.create_indexed_vertex(data, index_name, keys=keys)
        path = vertex_path
        params = self._remove_null_values(data)
        return self.request.post(path, params)

    def get_vertex(self, _id):
        """
        Gets the vertex with the _id and returns the Response.

        :param data: Vertex ID.
        :type data: int

        :rtype: Neo4jResponse

        """
        path = build_path(vertex_path, _id)
        params = None
        return self.request.get(path, params)
        
    def get_all_vertices(self):
        """
        Returns a Response containing all the vertices in the Graph.

        :rtype: Neo4jResponse

        """
        script = self.scripts.get("get_vertices")
        params = None
        return self.gremlin(script, params)

    def update_vertex(self, _id, data, keys=None):
        """
        Updates the vertex with the _id and returns the Response.

        :param _id: Vertex ID.
        :type _id: dict

        :param data: Property data.
        :type data: dict

        :rtype: Neo4jResponse

        """
        if keys or self.config.autoindex is True:
            index_name = self.config.vertex_index
            return self.update_indexed_vertex(_id,data,index_name,keys=keys)
        path = self._build_vertex_path(_id,"properties")
        params = self._remove_null_values(data)
        return self.request.put(path, params)

    def delete_vertex(self, _id):
        """
        Deletes a vertex with the _id and returns the Response.

        :param _id: Vertex ID.
        :type _id: dict

        :rtype: Neo4jResponse

        """
        script = self.scripts.get("delete_vertex")
        params = dict(_id=_id)
        return self.gremlin(script,params)
        
    # Edge Proxy

    def create_edge(self, outV, label, inV, data=None, keys=None): 
        """
        Creates a edge and returns the Response.
        
        :param outV: Outgoing vertex ID.
        :type outV: int

        :param label: Edge label.
        :type label: str

        :param inV: Incoming vertex ID.
        :type inV: int

        :param data: Property data.
        :type data: dict or None

        :rtype: Neo4jResponse

        """
        if keys or self.config.autoindex is True:
            index_name = self.config.edge_index
            return self.create_indexed_edge(outV,label,inV,data,index_name,keys=keys)
        data = self._remove_null_values(data)
        inV_uri = self._build_vertex_uri(inV)
        path = build_path(vertex_path, outV, "relationships")
        params = {'to':inV_uri, 'type':label, 'data':data}
        return self.request.post(path, params)

    def get_edge(self, _id):
        """
        Gets the edge with the _id and returns the Response.

        :param data: Edge ID.
        :type data: int

        :rtype: Neo4jResponse

        """
        path = build_path(edge_path,_id)
        params = None
        return self.request.get(path, params)
        
    def get_all_edges(self):
        """
        Returns a Response containing all the edges in the Graph.

        :rtype: Neo4jResponse

        """
        script = self.scripts.get("get_edges")
        params = None
        return self.gremlin(script, params)

    def update_edge(self, _id, data, keys=None):
        """
        Updates the edge with the _id and returns the Response.

        :param _id: Edge ID.
        :type _id: dict

        :param data: Property data.
        :type data: dict

        :rtype: Neo4jResponse

        """
        if keys or self.config.autoindex is True:
            index_name = self.config.edge_index
            return self.update_indexed_edge(_id,data,index_name,keys=keys)
        path = build_path(edge_path,_id,"properties")
        params = self._remove_null_values(data)
        return self.request.put(path, params)

    def delete_edge(self, _id):
        """
        Deletes a edge with the _id and returns the Response.

        :param _id: Edge ID.
        :type _id: dict

        :rtype: Neo4jResponse

        """
        path = build_path(edge_path,_id)
        params = None
        return self.request.delete(path, params)

    # Vertex Container

    def outE(self, _id, label=None, start=None, limit=None):
        """
        Returns the outgoing edges of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Neo4jResponse
        
        """
        script = self.scripts.get('outE')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)

    def inE(self, _id, label=None, start=None, limit=None):
        """
        Returns the incoming edges of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Neo4jResponse

        """
        script = self.scripts.get('inE')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)

    def bothE(self, _id, label=None, start=None, limit=None):
        """
        Returns the incoming and outgoing edges of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Neo4jResponse
        
        """
        script = self.scripts.get('bothE')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)

    def outV(self, _id, label=None, start=None, limit=None):
        """
        Returns the out-adjacent vertices of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Neo4jResponse

        """
        script = self.scripts.get('outV')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)
        
    def inV(self, _id, label=None, start=None, limit=None):
        """
        Returns the in-adjacent vertices of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Neo4jResponse

        """
        script = self.scripts.get('inV')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)
        
    def bothV(self, _id, label=None, start=None, limit=None):
        """
        Returns the incoming- and outgoing-adjacent vertices of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: Neo4jResponse

        """
        script = self.scripts.get('bothV')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)

    #: Index Proxy - Vertex

    def create_vertex_index(self, index_name, *args, **kwds):
        """
        Creates a vertex index with the specified params.

        :param index_name: Name of the index to create.
        :type index_name: str

        :rtype: Neo4jResponse

        """
        default_config = {'type': "exact", 'provider': "lucene"}
        index_config = kwds.pop("index_config", default_config) 
        path = build_path(index_path, vertex_path)
        params = dict(name=index_name, config=index_config)
        resp = self.request.post(path, params)
        resp._set_index_name(index_name)        
        return resp

    def get_vertex_indices(self):
        """
        Returns all the vertex indices.

        :rtype: Neo4jResponse

        """
        path = build_path(index_path,vertex_path)
        params = None
        return self.request.get(path, params)

    def get_vertex_index(self, index_name):
        """
        Returns the vertex index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: Neo4jResponse

        """
        resp = self.get_vertex_indices()
        resp.results = self._get_index_results(index_name,resp)
        if resp.results:
            resp._set_index_name(index_name)
        return resp

    def get_or_create_vertex_index(self, index_name, *args, **kwds):
        """
        Get a Vertex Index or create it if it doesn't exist.

        :param index_name: Index name.
        :type index_name: str

        :param index_config: Index configuration.
        :type index_config: dict

        :rtype: bulbs.neo4jserver.index.Index

        """ 
        # Neo4j's create index endpoint returns the index if it already exists
        return self.create_vertex_index(index_name, *args, **kwds)

    def delete_vertex_index(self, index_name): 
        """
        Deletes the vertex index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: Neo4jResponse

        """
        path = build_path(index_path, vertex_path, index_name)
        params = None
        return self.request.delete(path, params)

    # Index Proxy - Edge

    def create_edge_index(self, index_name, *args, **kwds):
        """
        Creates a edge index with the specified params.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: Neo4jResponse

        """
        default_config = {'type': "exact", 'provider': "lucene"}
        index_config = kwds.pop("index_config", default_config) 
        path = build_path(index_path, edge_path)
        params = dict(name=index_name, config=index_config)
        resp = self.request.post(path, params)
        resp._set_index_name(index_name)
        return resp

    def get_edge_indices(self):
        """
        Returns a dict of all the vertex indices.

        :rtype: Neo4jResponse

        """
        path = build_path(index_path,edge_path)
        params = None
        return self.request.get(path, params)

    def get_edge_index(self, index_name):
        """
        Returns the edge index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: Neo4jResponse

        """
        resp = self.get_edge_indices()
        resp.results = self._get_index_results(index_name, resp)
        if resp.results:
            resp._set_index_name(index_name)
        return resp

    def get_or_create_edge_index(self, index_name, *args, **kwds):
        """
        Get a Edge Index or create it if it doesn't exist.

        :param index_name: Index name.
        :type index_name: str

        :param index_config: Index configuration.
        :type index_config: dict

        :rtype: bulbs.neo4jserver.index.Index

        """ 
        # Neo4j's create index endpoint returns the index if it already exists
        return self.create_edge_index(index_name, *args, **kwds)

    def delete_edge_index(self, index_name):
        """
        Deletes the edge index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: Neo4jResponse

        """
        path = build_path(index_path, edge_path, index_name)
        params = None
        return self.request.delete(path, params)

    # Index Container - Vertex

    def put_vertex(self, index_name, key, value, _id):
        """
        Adds a vertex to the index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :param _id: Vertex ID
        :type _id: int
        
        :rtype: Neo4jResponse

        """
        uri = "%s/%s/%d" % (self.config.root_uri, vertex_path, _id)
        path = build_path(index_path, vertex_path, index_name)
        params = dict(key=key, value=value, uri=uri)
        return self.request.post(path, params)

    def lookup_vertex(self, index_name, key, value):
        """
        Returns the vertices indexed with the key and value.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :rtype: Neo4jResponse

        """
        # converting all values to strings because that's how they're stored
        path = build_path(index_path, vertex_path, index_name, key, value)
        params = None
        return self.request.get(path, params)

    def create_unique_vertex(self, index_name, key, value, data=None):
        """
        Create unique (based on the key / value pair) vertex with the properties
        described by data.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :param data: Properties of the new element.
        :type data: dict

        :rtype: Neo4jResponse

        """
        data = {} if data is None else data
        data = self._remove_null_values(data)
        path = (build_path(index_path, vertex_path, index_name) +
                '?uniqueness=get_or_create')
        params = {'key': key, 'value': value, 'properties': data}
        return self.request.post(path, params)
        
    def query_vertex(self, index_name, query):
        """
        Queries the index and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param query: Lucene query string
        :type query: str

        :rtype: Neo4jResponse

        """
        path = build_path(index_path, vertex_path, index_name)
        params = dict(query=query)
        return self.request.get(path, params)

    def remove_vertex(self, index_name, _id, key=None, value=None):
        """
        Removes a vertex from the index and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Optional. Name of the key.
        :type key: str

        :param value: Optional. Value of the key.
        :type value: str        

        :rtype: Neo4jResponse

        """
        path = build_path(index_path, vertex_path, index_name ,key, value, _id)
        params = None
        return self.request.delete(path, params)
        
    # Index Container - Edge

    def put_edge(self, index_name, key, value, _id):
        """
        Adds an edge to the index and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :param _id: Edge ID
        :type _id: int
        
        :rtype: Neo4jResponse

        """
        uri = "%s/%s/%d" % (self.config.root_uri,edge_path,_id)
        path = build_path(index_path, edge_path, index_name)
        params = dict(key=key,value=value,uri=uri)
        return self.request.post(path, params)

    def lookup_edge(self, index_name, key, value):
        """
        Looks up an edge in the index and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :rtype: Neo4jResponse

        """
        # converting all values to strings because that's how they're stored
        path = build_path(index_path, edge_path, index_name, key, value)
        params = None
        return self.request.get(path, params)

    def query_edge(self, index_name, query):
        """
        Queries the index and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param query: Lucene query string
        :type query: str

        :rtype: Neo4jResponse

        """
        path = build_path(index_path, edge_path, index_name)
        params = dict(query=query)
        return self.request.get(path, params)

    def remove_edge(self, index_name, _id, key=None, value=None):
        """
        Removes an edge from the index and returns the Response.
        
        :param index_name: Name of the index.
        :type index_name: str

        :param _id: Edge ID
        :type _id: int

        :param key: Optional. Name of the key.
        :type key: str

        :param value: Optional. Value of the key.
        :type value: str        

        :rtype: Neo4jResponse

        """
        path = build_path(index_path, edge_path, index_name, key, value, _id)
        params = None
        return self.request.delete(path, params)

    # Model Proxy - Vertex

    def create_indexed_vertex(self, data, index_name, keys=None):
        """
        Creates a vertex, indexes it, and returns the Response.

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index.
        :type keys: list

        :rtype: Neo4jResponse

        """
        data = self._remove_null_values(data)
        params = dict(data=data,index_name=index_name,keys=keys)
        script = self.scripts.get("create_indexed_vertex")
        return self.gremlin(script,params)
    
    def update_indexed_vertex(self, _id, data, index_name, keys=None):
        """
        Updates an indexed vertex and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index.
        :type keys: list

        :rtype: Neo4jResponse

        """
        data = self._remove_null_values(data)
        params = dict(_id=_id,data=data,index_name=index_name,keys=keys)
        script = self.scripts.get("update_indexed_vertex")
        return self.gremlin(script,params)

    # Model Proxy - Edge

    def create_indexed_edge(self, outV, label, inV, data, index_name, keys=None):
        """
        Creates a edge, indexes it, and returns the Response.

        :param outV: Outgoing vertex ID.
        :type outV: int

        :param label: Edge label.
        :type label: str

        :param inV: Incoming vertex ID.
        :type inV: int

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index. Defaults to None (indexes all properties).
        :type keys: list

        :rtype: Neo4jResponse

        """
        data = self._remove_null_values(data)
        edge_params = dict(outV=outV,label=label,inV=inV,label_var=self.config.label_var)
        params = dict(data=data,index_name=index_name,keys=keys)
        params.update(edge_params)
        script = self.scripts.get("create_indexed_edge")
        return self.gremlin(script,params)


    def update_indexed_edge(self, _id, data, index_name, keys=None):
        """
        Updates an indexed edge and returns the Response.

        :param _id: Edge ID.
        :type _id: int

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index. Defaults to None (indexes all properties).
        :type keys: list

        :rtype: Neo4jResponse

        """
        data = self._remove_null_values(data)
        params = dict(_id=_id,data=data,index_name=index_name,keys=keys)
        script = self.scripts.get("update_indexed_edge")
        return self.gremlin(script,params)


    # Metadata

    def set_metadata(self, key, value):
        """
        Sets the metadata key to the supplied value.

        :param key: Metadata key
        :type key: str

        :param value: Metadata value.
        :type value: str, int, or list

        :rtype: Neo4jResponse
        
        """
        script = self.scripts.get("set_metadata")
        params = dict(key=key, value=value)
        return self.gremlin(script, params)

    def get_metadata(self, key, default_value=None):
        """
        Returns the value of metadata for the key.

        :param key: Metadata key
        :type key: str

        :param default_value: Default value to return if the key is not found.
        :type default_value: str, int, or list

        :rtype: Neo4jResponse
        
        """
        script = self.scripts.get("get_metadata")
        params = dict(key=key, default_value=default_value)
        return self.gremlin(script, params)

    def remove_metadata(self, key):
        """
        Removes the metadata key and value.

        :param key: Metadata key
        :type key: str

        :rtype: Neo4jResponse
        
        """
        script = self.scripts.get("remove_metadata")
        params = dict(key=key)
        return self.gremlin(script, params)


    # Private 

    def _remove_null_values(self,data):
        """Removes null property values because they aren't valid in Neo4j."""
        # Neo4j Server uses PUTs to overwrite all properties so no need
        # to worry about deleting props that are being set to null.
        data = data or {}
        clean_data = [(k, data[k]) for k in data if data[k] is not None] # Python 3
        return dict(clean_data)

    def _get_index_results(self, index_name, resp):
        """
        Returns the index from a dict of indicies.

        """
        if resp.content and index_name in resp.content:
            result = resp.content[index_name]
            return Neo4jResult(result, self.config)


    # Batch related
    def _placeholder(self,_id):
        pattern = "^{.*}$"
        match = re.search(pattern,str(_id))
        if match:
            placeholder = match.group()
            return placeholder

    def _build_vertex_path(self,_id,*args):
        # if the _id is a placeholder, return the placeholder;
        # othewise, return a normal vertex path
        placeholder = self._placeholder(_id) 
        if placeholder:
            segments = [placeholder]
        else:
            segments = [vertex_path,_id]
        segments = segments + list(args)
        return build_path(*segments)
        
    def _build_vertex_uri(self,_id,*args):
        placeholder = self._placeholder(_id) 
        if placeholder:
            return placeholder
        root_uri = self.config.root_uri.rstrip("/")
        segments = [vertex_path, _id] + list(args)
        path = build_path(*segments)
        uri = "%s/%s" % (root_uri, path)
        return uri

    def _build_edge_path(self,_id):
        # if the _id is a placeholder, return the placeholder;
        # othewise, return a normal edge path
        return self._placeholder(_id) or build_path(edge_path,_id)

    def _build_edge_uri(self,_id):
        pass


########NEW FILE########
__FILENAME__ = cypher
# -*- coding: utf-8 -*-
#
# Copyright 2011 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#

import os
import io
import re
import yaml 
from string import Template

from bulbs.utils import initialize_elements

class Cypher(object):

    def __init__(self, client):
        self.client = client

    def query(self, query, params=None):
        # Like a normal Gremlin query (returns elements)
        resp = self.client.cypher(query, params)
        return initialize_elements(self.client, resp)

    def table(self, query, params=None):
        resp = self.client.cypher(query,params)
        columns = resp.content['columns']
        data = resp.content['data']
        return columns, data

    def execute(self, query, params=None):
        return self.client.cypher(query, params)
        

class ScriptError(Exception):
    pass


class Yaml(object):
    """Load Gremlin scripts from a YAML source file."""

    def __init__(self,file_name=None):
        self.file_name = self._get_file_name(file_name)
        self.templates = self._get_templates(self.file_name)

    def get(self,name,params={}):
        """Return a Gremlin script, generated from the params."""
        template = self.templates.get(name)
        #params = self._quote_params(params)
        return template.substitute(params)
        
    def refresh(self):
        """Refresh the stored templates from the YAML source."""
        self.templates = self._get_templates()

    def override(self,file_name):
        new_templates = self._get_templates(file_name)
        self.templates.update(new_templates)

    def _get_file_name(self,file_name):
        if file_name is None:
            dir_name = os.path.dirname(__file__)
            file_name = utils.get_file_path(dir_name,"gremlin.yaml")
        return file_name

    def _get_templates(self,file_name):
        templates = dict()
        with io.open (file_name, encoding='utf-8') as f:
            yaml_map = yaml.load(f)    
            for name in yaml_map: # Python 3
                template = yaml_map[name]
                #template = ';'.join(lines.split('\n'))
                method_signature = self._get_method_signature(template)
                templates[name] = Template(template)
        return templates

    def _get_method_signature(self,template):
        lines = template.split('\n')
        first_line = lines[0]
        pattern = 'def(.*){'
        try:
            method_signature = re.search(pattern,first_line).group(1).strip()
            return method_signature
        except AttributeError:
            raise ScriptError("Each Gremln script in the YAML file must be defined as a Groovy method.")

    def _quote_params(self,params):
        for key in params:   # Python 3
            value = params[key]
            params[key] = self._quote(value)
        return params

    def _quote(self, value):
        if type(value) == str:
            value = "'%s'" % value
        elif value is None:
            value = ""
        return value

########NEW FILE########
__FILENAME__ = graph
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Interface for interacting with a graph database through Neo4j Server.

"""
from bulbs.config import Config
from bulbs.gremlin import Gremlin
from bulbs.element import Vertex, Edge
from bulbs.model import Node, Relationship
from bulbs.base.graph import Graph as BaseGraph

# Neo4j-specific imports
from .client import Neo4jClient
from .index import ExactIndex
from .cypher import Cypher

class Graph(BaseGraph):
    """
    The primary interface to Neo4j Server.

    Instantiates the database :class:`~bulbs.neo4jserver.client.Client` object using 
    the specified Config and sets up proxy objects to the database.

    :param config: Optional. Defaults to the default config.
    :type config: bulbs.config.Config

    :cvar client_class: Neo4jClient class.
    :cvar default_index: Default index class.

    :ivar client: Neo4jClient object.
    :ivar vertices: VertexProxy object.
    :ivar edges: EdgeProxy object.
    :ivar config: Config object.
    :ivar gremlin: Gremlin object.
    :ivar scripts: GroovyScripts object.
    
    Example:

    >>> from bulbs.neo4jserver import Graph
    >>> g = Graph()
    >>> james = g.vertices.create(name="James")
    >>> julie = g.vertices.create(name="Julie")
    >>> g.edges.create(james, "knows", julie)

    """
    client_class = Neo4jClient
    default_index = ExactIndex

    def __init__(self, config=None):
        # What happens if these REST init calls error on Heroku?    
        super(Graph, self).__init__(config)

        # Neo4j Server supports Gremlin
        self.gremlin = Gremlin(self.client)
        self.scripts = self.client.scripts    # for convienience 

        # Cypher; TODO: Cypher Queries library object
        self.cypher = Cypher(self.client)

    def set_metadata(self, key, value):
        """
        Sets the metadata key to the supplied value.

        :param key: Metadata key
        :type key: str

        :param value: Metadata value.
        :type value: str, int, or list

        :rtype: Neo4jResponse
        
        """
        return self.client.set_metadata(key, value).one()

    def get_metadata(self, key, default_value=None):
        """
        Returns the value of metadata for the key.

        :param key: Metadata key
        :type key: str

        :param default_value: Default value to return if the key is not found.
        :type default_value: str, int, or list

        :rtype: Neo4jResult
        
        """
        return self.client.get_metadata(key, default_value).one()

    def remove_metadata(self, key):
        """
        Removes the metadata key and value.

        :param key: Metadata key
        :type key: str

        :rtype: Neo4jResponse
        
        """
        return self.client.remove_metadata(key)
        
    def load_graphml(self, uri):
        """
        Loads a GraphML file into the database and returns the response.

        :param uri: URI of the GraphML file to load.
        :type uri: str

        :rtype: Neo4jResult

        """
        script = self.client.scripts.get('load_graphml')
        params = dict(uri=uri)
        return self.gremlin.command(script, params)
        
    def get_graphml(self):
        """
        Returns a GraphML file representing the entire database.

        :rtype: Neo4jResult

        """
        script = self.client.scripts.get('save_graphml')
        return self.gremlin.command(script, params=None)
        
    def warm_cache(self):
        """
        Warms the server cache by loading elements into memory.

        :rtype: Neo4jResult

        """
        script = self.scripts.get('warm_cache')
        return self.gremlin.command(script, params=None)

    def clear(self):
        """
        Deletes all the elements in the graph.

        :rtype: Neo4jResult

        .. admonition:: WARNING 

           This will delete all your data!

        """
        script = self.client.scripts.get('clear')
        return self.gremlin.command(script, params=None)
        

########NEW FILE########
__FILENAME__ = index
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
An interface for interacting with indices on Neo4j Server.

"""
from bulbs.utils import initialize_element, initialize_elements, get_one_result


class IndexProxy(object):
    """Abstract base class the index proxies."""

    def __init__(self, index_class, client):        
        # The index class for this proxy, e.g. ExactIndex.
        self.index_class = index_class

        # The Client object for the database.
        self.client = client
    
    def _build_index_config(self, index_class):
        assert self.index_class.blueprints_type is not "AUTOMATIC"
        index_config = {'type':self.index_class.index_type,
                        'provider':self.index_class.index_provider}
        return index_config
    

class VertexIndexProxy(IndexProxy):
    """
    Manage vertex indices on Neo4j Server.

    :param index_class: The index class for this proxy, e.g. ExactIndex.
    :type index_class: Index

    :param client: The Client object for the database.
    :type client: bulbs.neo4jserver.client.Neo4jClient

    :ivar index_class: Index class.
    :ivar client: Neo4jClient object.

    """
    def create(self, index_name):
        """
        Creates an Vertex index and returns it.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.neo4jserver.index.Index
        
        """
        config = self._build_index_config(self.index_class)
        resp = self.client.create_vertex_index(index_name,index_config=config)
        index = self.index_class(self.client, resp.results)
        self.client.registry.add_index(index_name,index)
        return index

    def get(self, index_name):
        """
        Returns the Index object with the specified name or None if not found.
        
        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.neo4jserver.index.Index
        
        """
        resp = self.client.get_vertex_index(index_name)
        if resp.results:
            index = self.index_class(self.client, resp.results)
            self.client.registry.add_index(index_name,index)
            return index

    def get_or_create(self, index_name):
        """
        Get a Vertex Index or create it if it doesn't exist.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.neo4jserver.index.Index

        """ 
        config = self._build_index_config(self.index_class)
        resp = self.client.get_or_create_vertex_index(index_name,index_config=config)
        index = self.index_class(self.client, resp.results)
        self.client.registry.add_index(index_name,index)
        return index

    def delete(self, index_name):
        """ 
        Deletes an index and returns the Response.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.neo4jserver.client.Neo4jResponse

        """
        return self.client.delete_vertex_index(index_name)


class EdgeIndexProxy(IndexProxy):
    """
    Manage edge indices on Neo4j Server.

    :param index_class: The index class for this proxy, e.g. ExactIndex.
    :type index_class: Index

    :param client: The Client object for the database.
    :type client: bulbs.neo4jserver.client.Neo4jClient

    :ivar index_class: Index class.
    :ivar client: Neo4jClient object.

    """
    def create(self, index_name):
        """
        Creates an Edge index and returns it.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.neo4jserver.index.Index
        
        """
        config = self._build_index_config(self.index_class)
        resp = self.client.create_edge_index(index_name,index_config=config)
        index = self.index_class(self.client,resp.results)
        self.client.registry.add_index(index_name,index)
        return index

    def get(self, index_name):
        """
        Returns the Index object with the specified name or None if not found.
        
        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.neo4jserver.index.Index
        
        """
        resp = self.client.get_edge_index(index_name)
        if resp.results:
            index = self.index_class(self.client,resp.results)
            self.client.registry.add_index(index_name,index)
            return index

    def get_or_create(self, index_name):
        """
        Get an Edge Index or create it if it doesn't exist.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.neo4jserver.index.Index

        """ 
        config = self._build_index_config(self.index_class)
        resp = self.client.get_or_create_edge_index(index_name, index_config=config)
        index = self.index_class(self.client, resp.results)
        self.client.registry.add_index(index_name,index)
        return index

    def delete(self, index_name):
        """ 
        Deletes an index and returns the Response.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.neo4jserver.client.Neo4jResponse

        """
        return self.client.delete_edge_index(index_name)

#
# Index Containers (Exact, Fulltext, Automatic, Unique)
#

class Index(object):
    """Abstract base class for Neo4j's Lucene index."""

    index_type = None
    index_provider = None
    blueprints_type = None

    def __init__(self, client, result):
        self.client = client
        self.result = result

    @classmethod 
    def get_proxy_class(cls, base_type):
        """
        Returns the IndexProxy class.

        :param base_type: Index base type, either vertex or edge.
        :type base_type: str

        :rtype: class

        """
        class_map = dict(vertex=VertexIndexProxy, edge=EdgeIndexProxy)
        return class_map[base_type]

    @property
    def index_name(self):
        """
        Returns the index name.

        :rtype: str

        """
        return self.result.get_index_name()

    @property
    def index_class(self):
        """
        Returns the index class, either vertex or edge.

        :rtype: class

        """
        return self.result.get_index_class()

    def put(self, _id, key=None, value=None, **pair):
        """
        Put an element into the index at key/value and return the Response.

        :param _id: The element ID.
        :type _id: int or str

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: name/value pair

        :rtype: bulbs.neo4jserver.client.Neo4jResponse
            
        """
        key, value = self._get_key_value(key,value,pair)
        put = self._get_method(vertex="put_vertex", edge="put_edge")
        return put(self.index_name,key,value,_id)

    def update(self, _id, key=None, value=None, **pair):
        """
        Update the element ID for the key and value.
        
        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: bulbs.neo4jserver.client.Neo4jResponse

        """
        # TODO: This should be a Gremlin method
        key, value = self._get_key_value(key,value,pair)
        for result in self.get(key,value):
            self.remove(self.index_name, result._id, key, value)
        return self.put(_id,key,value)

    def lookup(self, key=None, value=None, **pair):
        """
        Return all the elements in the index where key equals value.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: Element generator

        """
        key, value = self._get_key_value(key,value,pair)
        lookup = self._get_method(vertex="lookup_vertex", edge="lookup_edge")
        resp = lookup(self.index_name,key,value)
        return initialize_elements(self.client, resp)

    #put_unique = update
    def put_unique(self, _id, key=None, value=None, **pair):
        """
        Put an element into the index at key/value and overwrite it if an 
        element already exists; thus, when you do a lookup on that key/value pair,
        there will be a max of 1 element returned.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: bulbs.neo4jserver.client.Neo4jResponse

        """
        return self.update(_id, key, value, **pair)

    # TODO: maybe a putIfAbsent method too

    def get_unique(self, key=None, value=None, **pair):
        """
        Returns a max of 1 elements in the index matching the key/value pair.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: Element or None

        """
        key, value = self._get_key_value(key,value,pair)
        lookup = self._get_method(vertex="lookup_vertex", edge="lookup_edge")
        resp = lookup(self.index_name,key,value)
        if resp.total_size > 0:
            result = get_one_result(resp)
            return initialize_element(self.client,result)

    def create_unique_vertex(self, key=None, value=None, data=None, **pair):
        """
        Returns a tuple containing two values. The first is the element if it
        was created / found. The second is a boolean value the tells whether
        the element was created (True) or not (False).

        :param key: The index key.
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: tuple

        """
        key, value = self._get_key_value(key,value,pair)
        data = {} if data is None else data
        create = self._get_method(vertex="create_unique_vertex")
        resp = create(self.index_name, key, value, data)
        if resp.total_size > 0:
            result = get_one_result(resp)
            was_created = resp.headers['status'] == '201'
            return initialize_element(self.client, result), was_created
        else:
            return None, False

    def remove(self, _id, key=None, value=None, **pair):
        """
        Remove the element from the index located by key/value.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: bulbs.neo4jserver.client.Neo4jResponse

        """
        key, value = self._get_key_value(key, value, pair)
        remove = self._get_method(vertex="remove_vertex", edge="remove_edge")
        return remove(self.index_name,_id,key,value)

    def count(self, key=None, value=None, **pair):
        """
        Return the number of items in the index for the key and value.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: name/value pair

        :rtype: int

        """
        key, value = self._get_key_value(key,value,pair)
        script = self.client.scripts.get('index_count')
        params = dict(index_name=self.index_name,key=key,value=value)
        resp = self.client.gremlin(script,params)
        total_size = int(resp.content)
        return total_size

    def _get_key_value(self, key, value, pair):
        """
        Returns the key and value, regardless of how it was entered.

        :param key: The index key. 
        :type key: str

        :param value: The key's value.
        :type value: str or int

        :param pair: Optional key/value pair. Example: name="James"
        :type pair: key/value pair

        :rtype: tuple

        """
        if pair:
            key, value = pair.popitem()
        return key, value

    def _get_method(self, **method_map):
        """
        Returns the right method, depending on the index class type.

        :param method_map: Dict mapping the index class type to its method name. 
        :type method_map: dict

        :rtype: Callable

        """
        method_name = method_map[self.index_class]
        method = getattr(self.client, method_name)
        return method


class ExactIndex(Index):
    """
    Neo4j's Lucence exact index.

    :cvar index_type: Index type.
    :cvar index_provider: Index provider.
    :cvar blueprints_type: Blueprints type.

    :ivar client: Neo4jClient object 
    :ivar result: Neo4jResult object.

    """
    index_type = "exact"
    index_provider = "lucene"
    blueprints_type = "MANUAL"

    def query(self, key, query_string):
        """
        Return all the elements in the index matching the query.

        :param key: The index key. 
        :type key: str

        :param query_string: The query string. Example: "Jam*".
        :type value: str or int

        :rtype: Element generator

        """
        # TODO: Maybe update this to use the REST endpoint.
        script = self.client.scripts.get('query_exact_index')
        params = dict(index_name=self.index_name, key=key, query_string=query_string)
        resp = self.client.gremlin(script, params)
        return initialize_elements(self.client, resp)       

# TODO: add fulltext index tests
class FulltextIndex(Index):
    """
    Neo4j's Lucence fulltext index.

    :cvar index_type: Index type.
    :cvar index_provider: Index provider.
    :cvar blueprints_type: Blueprints type.

    :ivar client: Neo4jClient object 
    :ivar result: Neo4jResult object.
    
    """
    index_type = "fulltext"
    index_provider = "lucene"
    blueprints_type = "MANUAL"

    def query(self, query_string):
        """
        Return elements mathing the query.

        See http://lucene.apache.org/core/3_6_0/queryparsersyntax.html

        :param query_string: The query formatted in the Lucene query language. 
        :type query_string: str

        :rtype: Element generator

        """
        query = self._get_method(vertex="query_vertex", edge="query_edge")
        resp = query(self.index_name, query_string)
        return initialize_elements(self.client,resp)



# Uncdocumented -- experimental
class AutomaticIndex(ExactIndex):

    index_type = "exact"
    index_provider = "lucene"
    blueprints_type = "AUTOMATIC"

    # This works just like an ExactIndex except that the put, update, remove methods
    # are not implemented because those are done automatically.

    def put(self,_id, key=None, value=None, **pair):
        raise NotImplementedError

    def update(self, _id, key=None, value=None, **pair):
        raise NotImplementedError

    def remove(self, _id, key=None, value=None, **pair):
        raise NotImplementedError


# Uncdocumented -- experimental -- use put_unique and get_unique for now
class UniqueIndex(ExactIndex):
    pass


########NEW FILE########
__FILENAME__ = bulbs_tests
import unittest
from bulbs.config import Config
from bulbs.tests import BulbsTestCase, bulbs_test_suite
from bulbs.neo4jserver import Graph, Neo4jClient, NEO4J_URI, \
   VertexIndexProxy, EdgeIndexProxy, ExactIndex
from bulbs.tests import GremlinTestCase

config = Config(NEO4J_URI)
BulbsTestCase.client = Neo4jClient(config)
BulbsTestCase.vertex_index_proxy = VertexIndexProxy
BulbsTestCase.edge_index_proxy = EdgeIndexProxy
BulbsTestCase.index_class = ExactIndex
BulbsTestCase.graph = Graph(config)

def test_suite():
    suite = bulbs_test_suite()
    #suite.addTest(unittest.makeSuite(RestTestCase))
    suite.addTest(unittest.makeSuite(GremlinTestCase))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')


########NEW FILE########
__FILENAME__ = client_tests
from uuid import uuid1
import unittest
from bulbs.config import Config
from bulbs.utils import json
from bulbs.neo4jserver import Neo4jClient, NEO4J_URI
from bulbs.tests.client_tests import ClientTestCase
from bulbs.tests.client_index_tests import ClientIndexTestCase

from bulbs.factory import Factory
from bulbs.element import Vertex, Edge
from bulbs.neo4jserver.index import ExactIndex

import time


class Neo4jClientTestCase(ClientTestCase):

    def setUp(self):
        config = Config(NEO4J_URI)
        self.client = Neo4jClient(config)


# Separated client index tests for Titan
class Neo4jClientIndexTestCase(ClientIndexTestCase):

    def setUp(self):
        config = Config(NEO4J_URI)
        self.client = Neo4jClient(config)

    def test_create_unique_vertex(self):
        idx_name = 'test_idx'
        self._delete_vertex_index(idx_name)
        self.client.create_vertex_index(idx_name)

        k, v = 'key', uuid1().get_hex()
        args = (k, v, {k: v})
        resp = self.client.create_unique_vertex(idx_name, *args)
        assert resp.headers['status'] == '201'
        assert resp.results.data.get(k) == v

        resp = self.client.create_unique_vertex(idx_name, *args)
        assert resp.headers['status'] == '200'
        assert resp.results.data.get(k) == v


# why is this here? - JT 10/22/2012
class Neo4jIndexTestCase(unittest.TestCase):
    
    def setUp(self):
        config = Config(NEO4J_URI)
        self.client = Neo4jClient(config)
        self.factory = Factory(self.client)

    def test_gremlin(self):
        # limiting return count so we don't exceed heap size
        resp = self.client.gremlin("g.V[0..9]")
        assert resp.total_size > 5

    def test_query_exact_vertex_index(self):
        index = self.factory.get_index(Vertex, ExactIndex)
        vertices = index.query("name", "Jam*")
        assert len(list(vertices)) > 1

    def test_query_exact_edge_index(self):
        index = self.factory.get_index(Edge, ExactIndex)
        edges = index.query("timestamp", "1*")
        assert len(list(edges)) > 1

    def test_create_unique_vertex(self):
        index = self.factory.get_index(Vertex, ExactIndex)
        k, v = 'key', uuid1().get_hex()
        args = (k, v, {k: v})

        vertex, created = index.create_unique_vertex(*args)
        assert isinstance(vertex, Vertex)
        assert created is True

        vertex, created = index.create_unique_vertex(*args)
        assert isinstance(vertex, Vertex)
        assert created is False


class CypherTestCase(unittest.TestCase):
    
    def setUp(self):
        config = Config(NEO4J_URI)
        self.client = Neo4jClient(config)

    #def test_warm_cache(self):
    #    resp = self.client.warm_cache()
    #    print resp.raw

    def test_cypher(self):
        query = """START x  = node({_id}) MATCH x -[r]-> n RETURN type(r), n.name?, n.age?"""
        params = dict(_id=1261)
        resp = self.client.cypher(query,params)
        #print resp.raw

def neo4j_client_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Neo4jClientTestCase))
    suite.addTest(unittest.makeSuite(Neo4jClientIndexTestCase))
    suite.addTest(unittest.makeSuite(Neo4jIndexTestCase))
    #suite.addTest(unittest.makeSuite(GremlinTestCase))
    #suite.addTest(unittest.makeSuite(CypherTestCase))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='neo4j_client_suite')


########NEW FILE########
__FILENAME__ = property
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Interface for interacting with a graph database through Rexster.

"""
# Python 3
import six
import sys
if sys.version > '3':
    long = int
    unicode = str

import datetime
import dateutil.parser
from numbers import Number

from . import utils
from .utils import get_logger, to_datetime, to_date

log = get_logger(__name__)


class Property(object):
    """
    Abstract base class for database property types used in Models.

    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str

    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexeded: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed. 

    """
    def __init__(self, fget=None, name=None, default=None, \
                     nullable=True, unique=False, indexed=False):
        self.fget = fget
        self.name = name
        self.default = default
        self.nullable = nullable

        # These aren't implemented yet.         
        # TODO: unique creates an index
        self.indexed = indexed
        self.unique = unique
        #self.constraint = constraint


    def validate(self, key, value):
        """
        Validates the Property value before saving it to the database.
        
        :param key: Property key.
        :type key: str

        :param value: Property value.
        :type value: object

        :rtype: None

        """
        # Do null checks first so you can ignore None values in check_datatype()
        self._check_null(key, value)
        self._check_datatype(key, value)

    def _check_null(self,key,value):
        # TODO: should this be checking that the value is True to catch empties?
        if self.nullable is False and value is None:
            log.error("Null Property Error: '%s' cannot be set to '%s'", 
                      key, value)
            raise ValueError

    def _check_datatype(self, key, value):
        if value is not None and isinstance(value, self.python_type) is False:
            log.error("Type Error: '%s' is set to %s with type %s, but must be a %s.", 
                      key, value, type(value), self.python_type)
            raise TypeError

    def convert_to_db(self, type_system, key, value):
        """
        Converts a Property value from its Python type to its database representation.

        :param type_system: TypeSystem object.
        :type type_system: TypeSystem

        :param key: Property key.
        :type key: str

        :param value: Property value.
        :type value: object

        :rtype: object

        """
        value = self.to_db(type_system,value)
        return value

    def convert_to_python(self, type_system, key, value):
        """
        Converts a Property value from its database representation to its Python type.

        :param type_system: TypeSystem object.
        :type type_system: TypeSystem

        :param key: Property key.
        :type key: str

        :param value: Property value.
        :type value: object

        :rtype: object

        """
        try:
            value = self.to_python(type_system, value)
        except Exception as e:
            log.exception("Property Type Mismatch: '%s' with value '%s': %s", 
                          key, value, e)
            value = None
        return value

    def coerce(self, key, value):
        """
        Coerces a Property value to its Python type.
        
        :param key: Property key.
        :type key: str
        
        :param value: Property value.
        :type value: object

        :rtype: object        

        """
        initial_datatype = type(value)
        try:
            value = self._coerce(value)
            return value
        except ValueError:
            log.exception("'%s' is not a valid value for %s, must be  %s.", 
                          value, key, self.python_type)
            raise
        except AttributeError:
            log.exception("Can't set attribute '%s' to value '%s with type %s'", 
                          key, value, initial_datatype)
            raise

    def _coerce(self, value):
        # overload coerce for special types like DateTime
        return self.python_type(value)

class String(Property): 
    """
    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str
    
    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexed: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed. 

    """
    #: Python type
    python_type = unicode

    def to_db(self,type_system,value):
        return type_system.database.to_string(value)

    def to_python(self,type_system,value):
        return type_system.python.to_string(value)

    def _coerce(self, value):
        return utils.u(value)

class Integer(Property):    
    """
    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str

    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexed: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed. 

    """
    #: Python type
    python_type = int

    def to_db(self,type_system,value):
        return type_system.database.to_integer(value)
    
    def to_python(self,type_system,value):
        return type_system.python.to_integer(value)

class Long(Property):
    """
    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str

    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexed: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed. 

    """
    #: Python type
    python_type = long

    def to_db(self,type_system,value):
        return type_system.database.to_long(value)

    def to_python(self,type_system,value):
        return type_system.python.to_long(value)

class Float(Property):
    """
    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str

    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexed: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed. 

    """
    #: Python type
    python_type = float

    def to_db(self,type_system,value):
        return type_system.database.to_float(value)
    
    def to_python(self,type_system,value):
        return type_system.python.to_float(value)              

class Bool(Property):
    """
    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str

    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, bool, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexed: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed.

    """
    #: Python type
    python_type = bool

    def to_db(self,type_system,value):
        return type_system.database.to_bool(value)

    def to_python(self,type_system,value):
        return type_system.python.to_bool(value)

class Null(Property):
    """
    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str
    
    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexed: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed. 

    """
    #: Python type
    python_type = None

    def to_db(self,type_system,value):
        return type_system.database.to_null(value)

    def to_python(self,type_system,value):
        return type_system.python.to_null(value)

class List(Property):
    """
    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str
    
    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexed: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed. 

    """
    #: Python type
    python_type = list

    def to_db(self,type_system,value):
        return type_system.database.to_list(value)

    def to_python(self,type_system,value):
        return type_system.python.to_list(value)

class Dictionary(Property):
    """
    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str
    
    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexed: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed. 

    """
    #: Python type
    python_type = dict

    def to_db(self,type_system,value):
        return type_system.database.to_dictionary(value)

    def to_python(self,type_system,value):
        return type_system.python.to_dictionary(value)


class Document(Property):
    """
    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str
    
    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexed: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed. 

    """
    #: Python type
    python_type = dict

    def to_db(self,type_system,value):
        return type_system.database.to_document(value)

    def to_python(self,type_system,value):
        return type_system.python.to_dictionary(value)


class DateTime(Property):
    """
    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str

    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexed: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed. 

    """
    #: Python type
    python_type = datetime.datetime

    def to_db(self, type_system, value):
        return type_system.database.to_datetime(value)

    def to_python(self, type_system, value):
        return type_system.python.to_datetime(value)

    def is_valid(self, key, value):
        # how do you assert it's UTC?
        #Don't use assert except for sanity check during development 
        # (it gets turned to a no-op when you run with python -o), and 
        # don't raise the wrong kind of exception (such as, an AssertionError 
        # when a TypeError is clearly what you mean here).
        #return type(value) is datetime.datetime
        return isinstance(value, datetime.datetime)

    def _coerce(self, value):
        # Coerce user input to the Python type
        # Overloaded from Property since this is a special case
        # http://labix.org/python-dateutil#head-a23e8ae0a661d77b89dfb3476f85b26f0b30349c
        # return dateutils.parse(value)
        # Not using parse -- let the client code do that. Expect a UTC dateime object here.
        # How you going to handle asserts? It's easy with ints.
        
        if isinstance(value, Number):
            # catches unix timestamps
            dt = to_datetime(value)
        elif isinstance(value, datetime.datetime):  
            # value passed in was already in proper form
            dt = value
        else:
            # Python 3 unicode/str catchall
            dt = dateutil.parser.parse(value)

        #if dt.tzinfo is None:
        #    tz = pytz.timezone('UTC')
        #    dt.replace(tzinfo = tz)

        return dt


class Date(Property):
    """
    :param fget: Method name that returns a calculated value. Defaults to None.
    :type fget: str

    :param name: Database property name. Defaults to the Property key.
    :type name: str

    :param default: Default property value. Defaults to None.
    :type default: str, int, long, float, list, dict, or Callable

    :param nullable: If True, the Property can be null. Defaults to True.
    :type nullable: bool

    :param indexed: If True, index the Property in the DB. Defaults to False.
    :type indexed: bool

    :ivar fget: Name of the method that gets the calculated Property value.
    :ivar name: Database property name. Defaults to the Property key.
    :ivar default: Default property value. Defaults to None.
    :ivar nullable: If True, the Property can be null. Defaults to True.
    :ivar indexed: If True, index the Property in the DB. Defaults to False.

    .. note:: If no Properties have index=True, all Properties are indexed. 

    """
    #: Python type
    python_type = datetime.date

    def to_db(self, type_system, value):
        return type_system.database.to_date(value)

    def to_python(self, type_system, value):
        return type_system.python.to_date(value)

    def is_valid(self, key, value):
        # how do you assert it's UTC?
        #Don't use assert except for sanity check during development 
        # (it gets turned to a no-op when you run with python -o), and 
        # don't raise the wrong kind of exception (such as, an AssertionError 
        # when a TypeError is clearly what you mean here).
        return isinstance(value, datetime.date)

    def _coerce(self, value):
        # Coerce user input to the Python type
        # Overloaded from Property since this is a special case
        # http://labix.org/python-dateutil#head-a23e8ae0a661d77b89dfb3476f85b26f0b30349c
        # return dateutils.parse(value)
        # Not using parse -- let the client code do that. Expect a UTC dateime object here.
        # How you going to handle asserts? It's easy with ints.
        
        if isinstance(value, Number):
            # catches unix timestamps
            d = to_date(value)
        elif isinstance(value, datetime.date):  
            # value passed in was already in proper form
            d = value
        else:
            # Python 3 unicode/str catchall
            d = dateutil.parser.parse(value).date()

        return d
    

########NEW FILE########
__FILENAME__ = registry
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
from collections import OrderedDict
from bulbs.element import Vertex, Edge


class Registry(object):
    """
    Store runtime configuration settings.

    :param config: Config object.
    :type config: bulbs.config.Config

    """
    
    def __init__(self, config):
        self.config = config
        self.class_map = dict(vertex=Vertex,edge=Edge)
        self.proxy_map = dict()
        self.index_map = dict()
        self.scripts_map = OrderedDict()

    # Classes

    def add_class(self, element_class):
        """
        Adds an element class to the registry.

        :param element_class: Element class.
        :type element_class: class

        :rtype: None

        """
        # Vertex and Edge are always set by default
        if element_class not in (Vertex, Edge): 
            # TODO: may get into an issue with name clashes
            # a vertex has the same element_type as an edge's label;
            # for now "don't do that".
            element_key = element_class.get_element_key(self.config)
            self.class_map[element_key] = element_class

    def get_class(self, element_key):
        """
        Returns the element class given the element key.

        :param element_key: Element key, value of element_type or label.
        :type element_key: str

        :rtype: class

        """
        return self.class_map.get(element_key)

    # Proxies

    def add_proxy(self, name, proxy):
        """
        Adds a proxy object to the registry.

        :param name: Proxy name.
        :type name: str

        :param proxy: Proxy object.
        :type proxy: object

        :rtype: None

        """
        self.proxy_map[name] = proxy

    def get_proxy(self, name):
        """
        Returns proxy objects given the name.

        :param name: Proxy name.
        :type name: str

        :rtype: class

        """
        return self.proxy_map[name]

    # Indices

    def add_index(self, index_name, index):
        """
        Adds an index object to the registry.

        :param name: Index name.
        :type name: str

        :param name: index
        :type name: Index

        :rtype: None

        """
        self.index_map[index_name] = index
        
    def get_index(self, index_name):
        """
        Returns the Index object for the given index name.

        :param index_name: Index name.
        :type index_name: str

        :rtype: Index

        """
        return self.index_map[index_name]
 
    # Scripts

    def add_scripts(self, name, scripts):
        """
        Adds a scripts object to the registry.

        :param name: Scripts object name.
        :type name: str

        :param name: Scripts object.
        :type name: Scripts

        :rtype: None

        """
        self.scripts_map[name] = scripts

    def get_scripts(self, key):
        """
        Returns a scripts object for the given name.

        :param name: Scripts object name.
        :type name: str

        :rtype: Scripts

        """
        return self.scripts_map[key]


########NEW FILE########
__FILENAME__ = rest
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Low-level module for connecting to the Rexster REST server and
returning a Response object.

"""
import httplib2

import bulbs
from bulbs.base import Response
from .utils import json, get_logger, quote, urlencode, encode_dict


log = get_logger(__name__)

GET = "GET"
PUT = "PUT"
POST = "POST"
DELETE = "DELETE"

# HTTP Response Handlers
def ok(http_resp):
    return

def created(http_resp):
    return
    
def no_content(http_resp):
    return

def bad_request(http_resp):
    raise ValueError(http_resp)

def not_found(http_resp):
    raise LookupError(http_resp)
    #return None

def method_not_allowed(http_resp):
    # TODO: is there a better error for this than SystemError?
    raise SystemError(http_resp)

def conflict(http_resp):
    raise SystemError(http_resp)

def server_error(http_resp):
    raise SystemError(http_resp)

RESPONSE_HANDLERS = {200:ok,
                     201:created,
                     204:no_content,
                     400:bad_request,
                     404:not_found,
                     405:method_not_allowed,
                     409:conflict,
                     500:server_error}

# good posture good brain

class Request(object):
    """Used for connecting to the a REST server over HTTP."""

    response_class = Response

    def __init__(self, config, content_type):
        """
        Initializes a client object.

        :param root_uri: the base URL of Rexster.

        """
        self.config = config
        self.content_type = content_type
        self.user_agent = "bulbs/%s" % (bulbs.__version__)
        if config.timeout is not None:
            self.http = httplib2.Http(timeout=int(config.timeout))
        else:
            self.http = httplib2.Http()    
        self._add_credentials(config.username, config.password)
        self._initialize()

    def _initialize(self):
        pass
    
    def get(self, path, params=None):
        """
        Convenience method that sends GET requests to the client.

        :param path: Path to the server resource, relative to the root URI.
        :type path: str

        :param params: Optional URI params for the resource.
        :type params: dict

        :rtype: Response

        """ 
        return self.request(GET, path, params)

    def put(self, path, params=None):
        """
        Convenience method that sends PUT requests to the client.

        :param path: Path to the server resource, relative to the root URI.
        :type path: str

        :param params: Optional URI params for the resource.
        :type params: dict

        :rtype: Response

        """
        return self.request(PUT, path, params)

    def post(self, path, params=None):
        """
        Convenience method that sends POST requests to the client.

        :param path: Path to the server resource, relative to the root URI.
        :type path: str

        :param params: Optional URI params for the resource.
        :type params: dict

        :rtype: Response

        """
        return self.request(POST, path, params)

    def delete(self, path, params=None):
        """
        Convenience method that sends DELETE requests to the client.

        :param path: Path to the server resource, relative to the root URI.
        :type path: str

        :param params: Optional URI params for the resource.
        :type params: dict

        :rtype: Response

        """
        return self.request(DELETE, path, params)
    
    def send(self, message):
        """
        Convenience method that sends request messages to the client.

        :param message: Tuple containing: (HTTP method, path, params)
        :type path: tuple

        :param params: Optional URI params for the resource.
        :type params: dict

        :rtype: Response

        """
        method, path, params = message
        return self.request(method, path, params)

    def request(self, method, path, params):
        """
        Sends a request to the client.

        :param method: HTTP method: GET, PUT, POST, or DELETE.
        :type method: str

        :param path: Path to the server resource, relative to the root URI.
        :type path: str

        :param params: Optional URI parameters for the resource.
        :type params: dict

        :rtype: Response

        """
        uri, method, body, headers = self._build_request_args(path, method, params)

        self._display_debug(uri, method, body)

        http_resp = self.http.request(uri, method, body, headers)

        return self.response_class(http_resp, self.config)


    def _display_debug(self, uri, method, body):
        log.debug("%s url:  %s  ", method, uri)
        log.debug("%s body: %s ", method, body)
                    
    def _build_request_args(self, path, method, params):
        headers = {'Accept': 'application/json',
                   'User-Agent': self.user_agent}
        body = None

        uri = "%s/%s" % (self.config.root_uri.rstrip("/"), path.lstrip("/"))

        if params and method is GET:
            params = encode_dict(params)
            uri = "%s?%s" % (uri, urlencode(params))
            content_type = "%s ; charset=utf-8" % self.content_type
            get_headers = {'Content-Type': content_type}
            headers.update(get_headers)
        
        if params and (method in [PUT, POST, DELETE]):
            #params = encode_dict(params)
            body = json.dumps(params)
            post_headers = {'Content-Type': self.content_type}
            headers.update(post_headers)
        
        return uri, method, body, headers 

    def _add_credentials(self, username, password):
        if username and password:
            self.http.add_credentials(username, password)

    # how to reuse the http object?
    def __getstate__(self):
        state = self.__data__.copy()
        del state['http']
        return state

    def __setstate__(self, state):
        state['http'] = httplib2.Http()
        self.__data__ = state


########NEW FILE########
__FILENAME__ = batch

# NOTE: This isn't fully baked. Will probably redo this and 
# create a BatchClient like in neo4jserver/batch.py

class RexsterTransaction(object):

    def __init__(self):
        self.actions = []

    def create_edge(self,outV,label,inV,data={}):
        edge_data = dict(_outV=outV,_label=label,_inV=inV)
        data.update(edge_data)
        action = build_action("create","edge",data)
        self.actions.append(action)

    def build_action(self,_action,_type,data={}):
        action = {'_action':_action,'_type':_type}
        for key in data:  # Python 3
            value = data[key]
            action.update({key:value})
        return action              
          

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Bulbs supports pluggable clients. This is the Rexster client.

"""
from bulbs.config import Config, DEBUG
from bulbs.registry import Registry
from bulbs.utils import get_logger

# specific to this client
from bulbs.json import JSONTypeSystem
from bulbs.base import Client, Response, Result 
from bulbs.rest import Request, RESPONSE_HANDLERS
from bulbs.groovy import GroovyScripts

from bulbs.utils import json, build_path, get_file_path, urlsplit, coerce_id


# The default URIs
REXSTER_URI = "http://localhost:8182/graphs/emptygraph"  # emptygraph has mock-tx enabled 
SAIL_URI = "http://localhost:8182/graphs/sailgraph"

# The logger defined in Config
log = get_logger(__name__)

# Rexster resource paths
# TODO: local path vars would be faster
vertex_path = "vertices"
edge_path = "edges"
index_path = "indices"
gremlin_path = "tp/gremlin"
transaction_path = "tp/batch/tx"
multi_get_path = "tp/batch"


class RexsterResult(Result):
    """
    Container class for a single result, not a list of results.

    :param result: The raw result.
    :type result: dict

    :param config: The client Config object.
    :type config: Config 

    :ivar raw: The raw result.
    :ivar data: The data in the result.

    """
    def __init__(self, result, config):
        self.config = config

        # The raw result.
        self.raw = result

        # The data in the result.
        self.data = result

    def get_id(self):
        """
        Returns the element ID.

        :rtype: int or str

        """
        _id = self.data['_id']

        # OrientDB uses string IDs
        return coerce_id(_id)
               
    def get_type(self):
        """
        Returns the element's base type, either "vertex" or "edge".

        :rtype: str

        """
        return self.data['_type']
        
    def get_data(self):
        """
        Returns the element's property data.

        :rtype: dict

        """
        property_data = dict()
        private_keys = ['_id','_type','_outV','_inV','_label']
        for key in self.data: # Python 3
            value = self.data[key]
            if key not in private_keys:
                property_data.update({key:value})
        return property_data

    def get_uri(self):
        """
        Returns the element URI.

        :rtype: str

        """
        path_map = dict(vertex="vertices",edge="edges")
        _id = self.get_id()
        _type = self.get_type()
        element_path = path_map[_type]
        root_uri = self.config.root_uri
        uri = "%s/%s/%s" % (root_uri,element_path,_id)
        return uri
                 
    def get_outV(self):
        """
        Returns the ID of the edge's outgoing vertex (start node).

        :rtype: int

        """
        _outV = self.data.get('_outV')
        return coerce_id(_outV)
        
    def get_inV(self):
        """
        Returns the ID of the edge's incoming vertex (end node).

        :rtype: int

        """
        _inV = self.data.get('_inV')
        return coerce_id(_inV)

    def get_label(self):
        """
        Returns the edge label (relationship type).

        :rtype: str

        """
        return self.data.get('_label')

    def get_index_name(self):
        """
        Returns the index name.

        :rtype: str

        """
        return self.data['name']

    def get_index_class(self):
        """
        Returns the index class, either "vertex" or "edge".

        :rtype: str

        """
        return self.data['class']

    def get(self,attribute):
        """
        Returns the value of a client-specific attribute.
        
        :param attribute: Name of the attribute. 
        :type attribute: str

        :rtype: str

        """
        return self.data[attribute]


class RexsterResponse(Response):
    """
    Container class for the server response.

    :param response: httplib2 response: (headers, content).
    :type response: tuple

    :param config: Config object.
    :type config: bulbs.config.Config

    :ivar config: Config object.
    :ivar headers: httplib2 response headers, see:
        http://httplib2.googlecode.com/hg/doc/html/libhttplib2.html
    :ivar content: A dict containing the HTTP response content.
    :ivar results: A generator of RexsterResult objects, a single RexsterResult object, 
        or None, depending on the number of results returned.
    :ivar total_size: The number of results returned.
    :ivar raw: Raw HTTP response. Only set when log_level is DEBUG.

    """
    result_class = RexsterResult

    def __init__(self, response, config):
        self.config = config
        self.handle_response(response)
        self.headers = self.get_headers(response)
        self.content = self.get_content(response)
        self.results, self.total_size = self.get_results()
        self.raw = self._maybe_get_raw(response, config)

    def _maybe_get_raw(self,response, config):
        """Returns the raw response if in DEBUG mode."""
        # don't store raw response in production else you'll bloat the obj
        if config.log_level == DEBUG:
            return response

    def handle_response(self,http_resp):
        """
        Check the server response and raise exception if needed.
        
        :param response: httplib2 response: (headers, content).
        :type response: tuple

        :rtype: None

        """
        headers, content = http_resp
        response_handler = RESPONSE_HANDLERS.get(headers.status)
        response_handler(http_resp)

    def get_headers(self,response):
        """
        Returns a dict containing the headers from the response.

        :param response: httplib2 response: (headers, content).
        :type response: tuple
        
        :rtype: httplib2.Response

        """
        headers, content = response
        return headers

    def get_content(self,response):
        """
        Returns a dict containing the content from the response.
        
        :param response: httplib2 response: (headers, content).
        :type response: tuple
        
        :rtype: dict or None

        """
        # response is a tuple containing (headers, content)
        # headers is an httplib2 Response object, content is a string
        # see http://httplib2.googlecode.com/hg/doc/html/libhttplib2.html
        headers, content = response

        if content:
            content = json.loads(content.decode('utf-8'))
            return content

    def get_results(self):
        """
        Returns the results contained in the response.

        :return:  A tuple containing two items: 1. Either a generator of RexsterResult objects, 
                  a single RexsterResult object, or None, depending on the number of results 
                  returned; 2. An int representing the number results returned.
        :rtype: tuple

        """
        if type(self.content.get('results')) == list:
            results = (self.result_class(result, self.config) for result in self.content['results'])
            total_size = len(self.content['results'])
        elif self.content.get('results'):
            results = self.result_class(self.content['results'], self.config)
            total_size = 1
        else:
            results = None
            total_size = 0
        return results, total_size


class RexsterRequest(Request):
    """Makes HTTP requests to Rexster and returns a RexsterResponse.""" 
    
    response_class = RexsterResponse


class RexsterClient(Client):
    """
    Low-level client that sends a request to Rexster and returns a response.

    :param config: Optional Config object. Defaults to default Config.
    :type config: bulbs.config.Config

    :cvar default_uri: Default URI for the database.
    :cvar request_class: Request class for the Client.

    :ivar config: Config object.
    :ivar registry: Registry object.
    :ivar scripts: GroovyScripts object.  
    :ivar type_system: JSONTypeSystem object.
    :ivar request: RexsterRequest object.

    Example:

    >>> from bulbs.rexster import RexsterClient
    >>> client = RexsterClient()
    >>> script = client.scripts.get("get_vertices")
    >>> response = client.gremlin(script, params=None)
    >>> result = response.results.next()

    """ 
    #: Default URI for the database.
    default_uri = REXSTER_URI
    request_class = RexsterRequest


    def __init__(self, config=None, db_name=None):
        # This makes is easy to test different DBs 
        uri = self._get_uri(db_name) or self.default_uri

        self.config = config or Config(uri)
        self.registry = Registry(self.config)
        self.type_system = JSONTypeSystem()
        self.request = self.request_class(self.config, self.type_system.content_type)

        # Rexster supports Gremlin so include the Gremlin-Groovy script library
        self.scripts = GroovyScripts(self.config) 

        # Also include the Rexster-specific Gremlin-Groovy scripts
        scripts_file = get_file_path(__file__, "gremlin.groovy")
        self.scripts.update(scripts_file)

        # Add it to the registry. This allows you to have more than one scripts namespace.
        self.registry.add_scripts("gremlin", self.scripts)

    def _get_uri(self, db_name):
        if db_name is not None:
            uri = "http://localhost:8182/graphs/%s" % db_name
            return uri

    # Gremlin

    def gremlin(self, script, params=None, load=None): 
        """
        Executes a Gremlin script and returns the Response.

        :param script: Gremlin script to execute.
        :type script: str

        :param params: Param bindings for the script.
        :type params: dict

        :rtype: RexsterResponse

        """
        params = dict(script=script, params=params)
        if self.config.server_scripts is True:
            params["load"] = load or [self.scripts.default_namespace]
        return self.request.post(gremlin_path, params)


    # Vertex Proxy

    def create_vertex(self, data, keys=None):
        """
        Creates a vertex and returns the Response.

        :param data: Property data.
        :type data: dict

        :rtype: RexsterResponse

        """
        if keys or self.config.autoindex is True:
            index_name = self.config.vertex_index
            return self.create_indexed_vertex(data, index_name, keys=keys)
        data = self._remove_null_values(data)
        return self.request.post(vertex_path, data)

    def get_vertex(self, _id):
        """
        Gets the vertex with the _id and returns the Response.

        :param data: Vertex ID.
        :type data: int

        :rtype: RexsterResponse

        """
        path = build_path(vertex_path,_id)
        return self.request.get(path,params=None)

    def get_all_vertices(self):
        """
        Returns a Response containing all the vertices in the Graph.

        :rtype: RexsterResponse

        """
        script = self.scripts.get("get_vertices")
        params = None
        return self.gremlin(script, params)

    def update_vertex(self, _id, data, keys=None):
        """
        Updates the vertex with the _id and returns the Response.

        :param _id: Vertex ID.
        :type _id: dict

        :param data: Property data.
        :type data: dict

        :rtype: RexsterResponse

        """
        data = self._remove_null_values(data)
        path = build_path(vertex_path,_id)
        return self.request.put(path,data)
        
    def delete_vertex(self, _id):
        """
        Deletes a vertex with the _id and returns the Response.

        :param _id: Vertex ID.
        :type _id: dict

        :rtype: RexsterResponse

        """
        path = build_path(vertex_path,_id)
        return self.request.delete(path,params=None)

    # Edge Proxy

    def create_edge(self, outV, label, inV, data={}, keys=None): 
        """
        Creates a edge and returns the Response.
        
        :param outV: Outgoing vertex ID.
        :type outV: int

        :param label: Edge label.
        :type label: str

        :param inV: Incoming vertex ID.
        :type inV: int

        :param data: Property data.
        :type data: dict or None

        :rtype: RexsterResponse

        """
        if keys or self.config.autoindex is True:
            index_name = self.config.edge_index
            return self.create_indexed_edge(outV,label,inV,data,index_name,keys=keys)
        data = self._remove_null_values(data)
        edge_data = dict(_outV=outV,_label=label,_inV=inV)
        data.update(edge_data)
        return self.request.post(edge_path, data)

    def get_edge(self, _id):
        """
        Gets the edge with the _id and returns the Response.

        :param data: Edge ID.
        :type data: int

        :rtype: RexsterResponse

        """
        path = build_path(edge_path, _id)
        return self.request.get(path, params=None)

    def get_all_edges(self):
        """
        Returns a Response containing all the edges in the Graph.

        :rtype: RexsterResponse

        """
        script = self.scripts.get("get_edges")
        params = None
        return self.gremlin(script, params)

    def update_edge(self,_id, data, keys=None):
        """
        Updates the edge with the _id and returns the Response.

        :param _id: Edge ID.
        :type _id: dict

        :param data: Property data.
        :type data: dict

        :rtype: RexsterResponse

        """
        data = self._remove_null_values(data)
        path = build_path(edge_path, _id)
        return self.request.put(path, data)

    def delete_edge(self,_id):
        """
        Deletes a edge with the _id and returns the Response.

        :param _id: Edge ID.
        :type _id: dict

        :rtype: RexsterResponse

        """
        path = build_path(edge_path, _id)
        return self.request.delete(path, params=None)

    # Vertex Container

    def outE(self,_id, label=None, start=None, limit=None):
        """
        Returns the outgoing edges of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: RexsterResponse
        
        """
        script = self.scripts.get('outE')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)

    def inE(self,_id, label=None, start=None, limit=None):
        """
        Returns the incoming edges of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: RexsterResponse

        """
        script = self.scripts.get('inE')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)

    def bothE(self,_id, label=None, start=None, limit=None):
        """
        Returns the incoming and outgoing edges of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: RexsterResponse
        
        """
        script = self.scripts.get('bothE')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)

    def outV(self,_id, label=None, start=None, limit=None):
        """
        Returns the out-adjacent vertices of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: RexsterResponse

        """
        script = self.scripts.get('outV')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)
        
    def inV(self,_id, label=None, start=None, limit=None):
        """
        Returns the in-adjacent vertices of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: RexsterResponse

        """
        script = self.scripts.get('inV')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)
        
    def bothV(self,_id, label=None, start=None, limit=None):
        """
        Returns the incoming- and outgoing-adjacent vertices of the vertex.

        :param _id: Vertex ID.
        :type _id: dict

        :param label: Optional edge label. Defaults to None.
        :type label: str

        :rtype: RexsterResponse

        """
        script = self.scripts.get('bothV')
        params = dict(_id=_id,label=label,start=start,limit=limit)
        return self.gremlin(script,params)

    # Index Proxy - General

    def get_all_indices(self):
        """Returns a list of all the element indices."""
        return self.request.get(index_path,params=None)

    def get_index(self, name):
        path = build_path(index_path,name)
        return self.request.get(path,params=None)

    def delete_index(self, name): 
        """Deletes the index with the index_name."""
        path = build_path(index_path,name)
        return self.request.delete(path,params=None)
            
    # Index Proxy - Vertex

    def create_vertex_index(self, index_name, *args, **kwds):
        """
        Creates a vertex index with the specified params.

        :param index_name: Name of the index to create.
        :type index_name: str

        :rtype: RexsterResponse

        """
        path = build_path(index_path,index_name)
        index_type = kwds.get('index_type','manual')
        index_keys = kwds.get('index_keys',None)                              
        params = {'class':'vertex','type':index_type}
        if index_keys: 
            params.update({'keys':index_keys})
        return self.request.post(path,params)

    def get_vertex_index(self, index_name):
        """
        Returns the vertex index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: RexsterResponse

        """
        return self.get_index(index_name)

    def get_or_create_vertex_index(self, index_name, index_params=None):
        script = self.scripts.get('get_or_create_vertex_index')
        params = dict(index_name=index_name, index_params=index_params)
        resp = self.gremlin(script, params)
        #assert "MANUAL" in resp.content['results'][0]
        result = {'name': index_name, 'type': 'manual', 'class': 'vertex'}
        resp.results = RexsterResult(result, self.config)
        return resp

    def delete_vertex_index(self, name): 
        """
        Deletes the vertex index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: RexsterResponse

        """
        return self.delete_index(name)

    # Index Proxy - Edge

    def create_edge_index(self, name, *args, **kwds):
        """
        Creates a edge index with the specified params.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: RexsterResponse

        """
        path = build_path(index_path,name)
        index_type = kwds.get('index_type','manual')
        index_keys = kwds.get('index_keys',None)                              
        params = {'class':'edge','type':index_type}
        if index_keys: 
            params.update({'keys':index_keys})
        return self.request.post(path,params)
        
    def get_edge_index(self, name):
        """
        Returns the edge index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: RexsterResponse

        """
        return self.get_index(name)
        
    def get_or_create_edge_index(self, index_name, index_params=None):
        script = self.scripts.get('get_or_create_edge_index')
        params = dict(index_name=index_name, index_params=index_params)
        resp = self.gremlin(script, params)
        #assert "MANUAL" in resp.content['results'][0]
        result = {'name': index_name, 'type': 'manual', 'class': 'edge'}
        resp.results = RexsterResult(result, self.config)
        return resp

    def delete_edge_index(self, name):
        """
        Deletes the edge index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: RexsterResponse

        """
        self.delete_index(name)

    #def create_automatic_vertex_index(self,index_name,element_class,keys=None):
    #    keys = json.dumps(keys) if keys else "null"
    #    params = dict(index_name=index_name,element_class=element_class,keys=keys)
    #    script = self.scripts.get('create_automatic_vertex_index',params)
    #    return self.gremlin(script)
        
    #def create_indexed_vertex_automatic(self,data,index_name):
    #    data = json.dumps(data)
    #    params = dict(data=data,index_name=index_name)
    #    script = self.scripts.get('create_automatic_indexed_vertex',params)
    #    return self.gremlin(script)

    # Index Container - General

    def index_count(self, index_name, key, value):
        path = build_path(index_path,index_name,"count")
        params = dict(key=key,value=value)
        return self.request.get(path,params)

    def index_keys(self, index_name):
        path = build_path(index_path,index_name,"keys")
        return self.request.get(path,params=None)

    # Index Container - Vertex

    def put_vertex(self, index_name, key, value, _id):
        """
        Adds a vertex to the index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :param _id: Vertex ID
        :type _id: int
        
        :rtype: RexsterResponse

        """
        # Rexster's API only supports string lookups so convert value to a string 
        path = build_path(index_path,index_name)
        params = {'key':key,'value':str(value),'class':'vertex','id':_id}
        return self.request.put(path,params)

    def lookup_vertex(self, index_index_name, key, value):
        """
        Returns the vertices indexed with the key and value.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :rtype: RexsterResponse

        """
        path = build_path(index_path,index_index_name)
        params = dict(key=key,value=value)
        return self.request.get(path,params)

    def query_vertex(self, index_name, params):
        """Queries for an edge in the index and returns the Response."""
        path = build_path(index_path,index_name)
        return self.request.get(path,params)

    def remove_vertex(self,index_name,_id,key=None,value=None):
        """
        Removes a vertex from the index and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Optional. Name of the key.
        :type key: str

        :param value: Optional. Value of the key.
        :type value: str        

        :rtype: RexsterResponse

        """
        # Can Rexster have None for key and value?
        path = build_path(index_path,index_name)
        params = {'key':key,'value':value,'class':'vertex','id':_id}
        return self.request.delete(path,params)

    # Index Container - Edge

    def put_edge(self, index_name, key, value, _id):
        """
        Adds an edge to the index and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :param _id: Edge ID
        :type _id: int
        
        :rtype: RexsterResponse

        """
        # Rexster's API only supports string lookups so convert value to a string 
        path = build_path(index_path,index_name)
        params = {'key':key,'value':str(value),'class':'edge','id':_id}
        return self.request.put(path,params)

    def lookup_edge(self, index_index_name, key, value):
        """
        Looks up an edge in the index and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :rtype: RexsterResponse

        """
        path = build_path(index_path,index_index_name)
        params = dict(key=key,value=value)
        return self.request.get(path,params)

    def query_edge(self, index_name, params):
        """Queries for an edge in the index and returns the Response."""
        path = build_path(index_path,index_name)
        return self.request.get(path,params)

    def remove_edge(self, index_name, _id, key=None, value=None):
        """
        Removes an edge from the index and returns the Response.
        
        :param index_name: Name of the index.
        :type index_name: str

        :param _id: Edge ID
        :type _id: int

        :param key: Optional. Name of the key.
        :type key: str

        :param value: Optional. Value of the key.
        :type value: str        

        :rtype: RexsterResponse

        """
        # Can Rexster have None for key and value?
        path = build_path(index_path,index_name)
        params = {'key':key,'value':value,'class':'edge','id':_id}
        return self.request.delete(path,params)
    
    # Model Proxy - Vertex

    def create_indexed_vertex(self, data, index_name, keys=None):
        """
        Creates a vertex, indexes it, and returns the Response.

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index.
        :type keys: list

        :rtype: RexsterResponse

        """
        data = self._remove_null_values(data)
        params = dict(data=data,index_name=index_name,keys=keys)
        script = self.scripts.get("create_indexed_vertex")
        resp = self.gremlin(script,params)
        resp.results = resp.one()
        return resp
    
    def update_indexed_vertex(self, _id, data, index_name, keys=None):
        """
        Updates an indexed vertex and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index.
        :type keys: list

        :rtype: RexsterResponse

        """
        data = self._remove_null_values(data)
        params = dict(_id=_id,data=data,index_name=index_name,keys=keys)
        script = self.scripts.get("update_indexed_vertex")
        return self.gremlin(script,params)

    # Model Proxy - Edge

    def create_indexed_edge(self, outV, label, inV, data, index_name, keys=None):
        """
        Creates a edge, indexes it, and returns the Response.

        :param outV: Outgoing vertex ID.
        :type outV: int

        :param label: Edge label.
        :type label: str

        :param inV: Incoming vertex ID.
        :type inV: int

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index. Defaults to None (indexes all properties).
        :type keys: list

        :rtype: RexsterResponse

        """
        data = self._remove_null_values(data)
        edge_params = dict(outV=outV,label=label,inV=inV,label_var=self.config.label_var)
        params = dict(data=data,index_name=index_name,keys=keys)
        params.update(edge_params)
        script = self.scripts.get("create_indexed_edge")
        resp = self.gremlin(script,params)
        resp.results = resp.one()
        return resp
        
    def update_indexed_edge(self, _id, data, index_name, keys=None):
        """
        Updates an indexed edge and returns the Response.

        :param _id: Edge ID.
        :type _id: int

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index. Defaults to None (indexes all properties).
        :type keys: list

        :rtype: RexsterResponse

        """
        data = self._remove_null_values(data)
        params = dict(_id=_id,data=data,index_name=index_name,keys=keys)
        script = self.scripts.get("update_indexed_edge")
        return self.gremlin(script,params)

    # Utils

    def warm_cache(self):
        """Warms the server cache by loading elements into memory."""
        script = self.scripts.get('warm_cache')
        return self.gremlin(script,params=None)

    # Rexster Specific Stuff

    def rebuild_vertex_index(self, index_name):
        params = dict(index_name=index_name)
        script = self.scripts.get('rebuild_vertex_index',params)
        return self.gremlin(script)

    def rebuild_edge_index(self, index_name):
        params = dict(index_name=index_name)
        script = self.scripts.get('rebuild_edge_index',params)
        return self.gremlin(script)


    # TODO: manual/custom index API

    def multi_get_vertices(self, id_list):
        path = build_path(multi_get_path,"vertices")
        idList = self._build_url_list(id_list)
        params = dict(idList=idList)
        return self.request.get(path,params)

    def multi_get_edges(self, id_list):
        path = build_path(multi_get_path,"edges")
        idList = self._build_url_list(id_list)
        params = dict(idList=idList)
        return self.request.get(path,params)

    def _build_url_list(self, items):
        items = [str(item) for item in items]
        url_list = "[%s]" % ",".join(items)
        return url_list

    def execute_transaction(self, transaction):
        params = dict(tx=transaction.actions)
        return self.request.post(self.transction_path,params)

    def _remove_null_values(self, data):
        """Removes null property values because they aren't valid in Neo4j."""
        # using PUTs to overwrite all properties so no need
        # to worry about deleting props that are being set to null.
        clean_data = [(k, data[k]) for k in data if data[k] is not None]  # Python 3
        return dict(clean_data)


########NEW FILE########
__FILENAME__ = graph
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Interface for interacting with a graph database through Rexster.

"""
import os
import io
from bulbs.config import Config
from bulbs.gremlin import Gremlin
from bulbs.element import Vertex, Edge
from bulbs.model import Node, Relationship
from bulbs.base.graph import Graph as BaseGraph

# Rexster-specific imports
from .client import RexsterClient, SAIL_URI
from .index import ManualIndex


class Graph(BaseGraph):
    """
    The primary interface to Rexster.

    Instantiates the database :class:`~bulbs.rexster.client.Client` object using 
    the specified Config and sets up proxy objects to the database.

    :param config: Optional. Defaults to the default config.
    :type config: bulbs.config.Config

    :cvar client_class: RexsterClient class.
    :cvar default_index: Default index class.

    :ivar client: RexsterClient object.
    :ivar vertices: VertexProxy object.
    :ivar edges: EdgeProxy object.
    :ivar config: Config object.
    :ivar gremlin: Gremlin object.
    :ivar scripts: GroovyScripts object.
    
    Example:

    >>> from bulbs.rexster import Graph
    >>> g = Graph()
    >>> james = g.vertices.create(name="James")
    >>> julie = g.vertices.create(name="Julie")
    >>> g.edges.create(james, "knows", julie)

    """
    client_class = RexsterClient
    default_index = ManualIndex
    
    def __init__(self, config=None):
        super(Graph, self).__init__(config)

        # Rexster supports Gremlin
        self.gremlin = Gremlin(self.client)
        self.scripts = self.client.scripts    # for convienience 

    def make_script_files(self, out_dir=None):
        """
        Generates a server-side scripts file.

        """
        out_dir = out_dir or os.getcwd()
        for namespace in self.scripts.namespace_map:
            # building script content from stored methods 
            # instead of sourcing files directly to filter out overridden methods
            methods = self.scripts.namespace_map[namespace]
            scripts_file = os.path.join(out_dir, "%s.groovy" % namespace)
            method_defs = []
            for method_name in methods:
                method = methods[method_name]
                method_defs.append(method.definition)
            content = "\n\n".join(method_defs)
            with io.open(scripts_file, "w", encoding='utf-8') as fout:
                fout.write(content + "\n")

    def load_graphml(self,uri):
        """
        Loads a GraphML file into the database and returns the response.

        :param uri: URI of the GraphML file to load.
        :type uri: str

        :rtype: RexsterResult

        """
        script = self.client.scripts.get('load_graphml')
        params = dict(uri=uri)
        return self.gremlin.command(script, params)
        
    def get_graphml(self):
        """
        Returns a GraphML file representing the entire database.

        :rtype: RexsterResult

        """
        script = self.client.scripts.get('save_graphml')
        return self.gremlin.command(script, params=None)
        
    def warm_cache(self):
        """
        Warms the server cache by loading elements into memory.

        :rtype: RexsterResult

        """
        script = self.scripts.get('warm_cache')
        return self.gremlin.command(script, params=None)

    def clear(self):
        """
        Deletes all the elements in the graph.

        :rtype: RexsterResult

        .. admonition:: WARNING 

           This will delete all your data!

        """
        script = self.client.scripts.get('clear')
        return self.gremlin.command(script,params=None)


#
# SailGraph is Undocumented/Experimental - Not Current
#

# TODO: Create a SailClient or sail Client methods.

class SailGraph(object):
    """ An interface to for SailGraph. """

    def __init__(self,root_uri=SAIL_URI):
        self.config = Config(root_uri)
        self.client = RexsterClient(self.config)

        # No indices on sail graphs
        self.gremlin = Gremlin(self.client)        

        self.vertices = VertexProxy(Vertex,self.client)
        self.edges = EdgeProxy(Edge,self.client)

    def add_prefix(self,prefix,namespace):
        params = dict(prefix=prefix,namespace=namespace)
        resp = self.client.post(self._base_target(),params)
        return resp

    def get_all_prefixes(self):
        resp = self.client.get(self._base_target(),params=None)
        return resp.results

    def get_prefix(self,prefix):
        target = "%s/%s" % (self._base_target(), prefix)
        resp = self.client.get(target,params=None)
        return resp.results
        
    def remove_prefix(self,prefix):
        target = "%s/%s" % (self._base_target(), prefix)
        resp = self.client.delete(target,params=None)
        return resp

    def load_rdf(self,url):
        """
        Loads an RDF file into the database, and returns the Rexster 
        response object.

        :param url: The URL of the RDF file to load.

        """
        script = "g.loadRDF('%s', 'n-triples')" % url
        params = dict(script=script)
        resp = self.client.get(self.base_target,params)
        return resp

    def _base_target(self):
        "Returns the base target URL path for vertices on Rexster."""
        base_target = "%s/%s" % (self.client.db_name,"prefixes")
        return base_target

########NEW FILE########
__FILENAME__ = index
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
An interface for interacting with indices on Rexster.

"""
from bulbs.utils import initialize_element, initialize_elements, get_one_result


class IndexProxy(object):
    """Abstract base class the index proxies."""

    def __init__(self, index_class, client):        
        # The index class for this proxy, e.g. ManualIndex.
        self.index_class = index_class

        # The Client object for the database.
        self.client = client
    

class VertexIndexProxy(IndexProxy):
    """
    Manage vertex indices on Rexster.

    :param index_class: The index class for this proxy, e.g. ManualIndex.
    :type index_class: Index

    :param client: The Client object for the database.
    :type client: bulbs.rexster.client.RexsterClient

    :ivar index_class: Index class.
    :ivar client: RexsterClient object.

    """
                        
    def create(self, index_name):
        """
        Creates an Vertex index and returns it.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.index.Index
        
        """
        resp = self.client.create_vertex_index(index_name)
        index = self.index_class(self.client,resp.results)
        self.client.registry.add_index(index_name, index)
        return index

    def get(self, index_name):
        """
        Returns the Index object with the specified name or None if not found.
        
        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.index.Index
        
        """
        resp = self.client.get_vertex_index(index_name)
        if resp.results:
            index = self.index_class(self.client,resp.results)
            self.client.registry.add_index(index_name, index)
            return index

    def get_or_create(self, index_name, index_params=None):
        """
        Get a Vertex Index or create it if it doesn't exist.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.index.Index

        """ 
        resp = self.client.get_or_create_vertex_index(index_name, index_params)
        index = self.index_class(self.client,resp.results)
        self.client.registry.add_index(index_name, index)
        return index

    def delete(self, index_name):
        """ 
        Deletes an index and returns the Response.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.client.RexsterResponse

        """
        try:
            return self.client.delete_vertex_index(index_name)
        except LookupError:
            return None


class EdgeIndexProxy(IndexProxy):
    """
    Manage edge indices on Rexster.

    :param index_class: The index class for this proxy, e.g. ManualIndex.
    :type index_class: Index

    :param client: The Client object for the database.
    :type client: bulbs.rexster.client.RexsterClient

    :ivar index_class: Index class.
    :ivar client: RexsterClient object.

    """

    def create(self,index_name,*args,**kwds):
        """ 
        Adds an index to the database and returns it. 

        index_keys must be a string in this format: '[k1,k2]'
        Don't pass actual list b/c keys get double quoted.

        :param index_name: The name of the index to create.

        :param index_class: The class of the elements stored in the index. 
                            Either vertex or edge.
        
        """
        resp = self.client.create_edge_index(index_name,*args,**kwds)
        index = self.index_class(self.client,resp.results)
        self.client.registry.add_index(index_name,index)
        return index

    def get(self,index_name):
        """
        Returns the Index object with the specified name or None if not found.
        
        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.index.Index
        
        """
        resp = self.client.get_edge_index(index_name)
        if resp.results:
            index = self.index_class(self.client,resp.results)
            self.client.registry.add_index(index_name,index)
            return index

    def get_or_create(self, index_name, index_params=None):
        """
        Get an Edge Index or create it if it doesn't exist.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.index.Index

        """ 
        resp = self.client.get_or_create_edge_index(index_name, index_params)
        index = self.index_class(self.client,resp.results)
        self.client.registry.add_index(index_name, index)
        return index

    def delete(self,index_name):
        """ 
        Deletes an index and returns the Response.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.client.RexsterResponse

        """
        try:
            return self.client.delete_edge_index(index_name)
        except LookupError:
            return None


#
# Index Containers (Manual, Automatic)
#

class Index(object):
    """Abstract base class for an index."""

    def __init__(self, client, result):
        self.client = client
        self.result = result

    @classmethod 
    def get_proxy_class(cls, base_type):
        """
        Returns the IndexProxy class.

        :param base_type: Index base type, either vertex or edge.
        :type base_type: str

        :rtype: class

        """
        class_map = dict(vertex=VertexIndexProxy, edge=EdgeIndexProxy)
        return class_map[base_type]

    @property
    def index_name(self):
        """
        Returns the index name.

        :rtype: str

        """
        return self.result.data['name']

    @property
    def index_class(self):
        """
        Returns the index class, either vertex or edge.

        :rtype: class

        """
        return self.result.data['class']

    @property
    def index_type(self):
        """
        Returns the index type, which will either be automatic or manual.

        :rtype: str

        """
        return self.result.data['type']

    def count(self,key=None,value=None,**pair):
        """
        Return a count of all elements with 'key' equal to 'value' in the index.

        :param key: The index key. This is optional because you can instead 
                    supply a key/value pair such as name="James". 

        :param value: The index key's value. This is optional because you can 
                      instead supply a key/value pair such as name="James". 

        :param pair: Optional keyword param. Instead of supplying key=name 
                     and value = 'James', you can supply a key/value pair in
                     the form of name='James'.
        """
        key, value = self._get_key_value(key,value,pair)
        resp = self.client.index_count(self.index_name,key,value)
        return resp.content['totalSize']


    def _get_key_value(self, key, value, pair):
        """Return the key and value, regardless of how it was entered."""
        if pair:
            key, value = pair.popitem()
        return key, value

    def _get_method(self, **method_map):
        method_name = method_map[self.index_class]
        method = getattr(self.client, method_name)
        return method

    def lookup(self, key=None, value=None, **pair):
        """
        Return a generator containing all the elements with key property equal 
        to value in the index.

        :param key: The index key. This is optional because you can instead 
                    supply a key/value pair such as name="James". 

        :param value: The index key's value. This is optional because you can 
                      instead supply a key/value pair such as name="James". 

        :param raw: Optional keyword param. If set to True, it won't try to 
                    initialize the results. Defaults to False. 

        :param pair: Optional keyword param. Instead of supplying key=name 
                     and value = 'James', you can supply a key/value pair in
                     the form of name='James'.
        """
        key, value = self._get_key_value(key, value, pair)
        resp = self.client.lookup_vertex(self.index_name,key,value)
        return initialize_elements(self.client,resp)


class ManualIndex(Index):
    """
    Creates, retrieves, and deletes indices provided by the graph database.

    Use this class to get, put, and update items in an index.
    

    :param client: The Client object for the database.

    :param result: The result list returned by Rexster.

    :param classes: Zero or more subclasses of Element to use when 
                    initializing the the elements returned by the query. 
                    For example, if Person is a subclass of Node (which 
                    is defined in model.py and is a subclass of Vertex), 
                    and the query returns person elements, pass in the 
                    Person class and the method will use the element_type
                    defined in the class to initialize the returned items
                    to a Person object.

    Example that creates an index for Web page URL stubs, 
    adds an page element to it, and then retrieves it from the index::

        >>> graph = Graph()
        >>> graph.indices.create("page","vertex","automatic","[stub]")
        >>> index = graph.indices.get("page")
        >>> index.put("stub",stub,page._id)
        >>> page = index.get("stub",stub)

    """

    
    def put(self,_id,key=None,value=None,**pair):
        """
        Put an element into the index at key/value and return Rexster's 
        response.

        :param _id: The element ID.

        :param key: The index key. This is optional because you can instead 
                    supply a key/value pair such as name="James". 

        :param value: The index key's value. This is optional because you can 
                      instead supply a key/value pair such as name="James". 

        :param pair: Optional keyword param. Instead of supplying key=name 
                     and value = 'James', you can supply a key/value pair in
                     the form of name='James'.

        """
        # NOTE: if you ever change the _id arg to element, change remove() too
        key, value = self._get_key_value(key,value,pair)
        put = self._get_method(vertex="put_vertex", edge="put_edge")
        resp = put(self.index_name,key,value,_id)
        return resp

    def update(self,_id,key=None,value=None,**pair):
        """
        Update the element ID for the key and value and return Rexsters' 
        response.

        :param _id: The element ID.

        :param key: The index key. This is optional because you can instead 
                    supply a key/value pair such as name="James". 

        :param value: The index key's value. This is optional because you can 
                      instead supply a key/value pair such as name="James". 

        :param pair: Optional keyword param. Instead of supplying key=name 
                     and value = 'James', you can supply a key/value pair in
                     the form of name='James'.
        """
        key, value = self._get_key_value(key,value,pair)
        for result in self.get(key,value):
            self.remove(self.index_name, result._id, key, value)
        return self.put(_id,key,value)


    def put_unique(self,_id,key=None,value=None,**pair):
        """
        Put an element into the index at key/value and overwrite it if an 
        element already exists at that key and value; thus, there will be a max
        of 1 element returned for that key/value pair. Return Rexster's 
        response.

        :param _id: The element ID.

        :param key: The index key. This is optional because you can instead 
                    supply a key/value pair such as name="James". 

        :param value: The index key's value. This is optional because you can 
                      instead supply a key/value pair such as name="James". 

        :param pair: Optional keyword param. Instead of supplying key=name 
                     and value = 'James', you can supply a key/value pair in 
                     the form of name='James'.

        """
        return self.update(_id, key, value, **pair)


    def get_unique(self,key=None,value=None,**pair):
        """
        Returns a max of 1 elements matching the key/value pair in the index.

        :param key: The index key. This is optional because you can instead 
                    supply a key/value pair such as name="James". 

        :param value: The index key's value. This is optional because you can 
                      instead supply a key/value pair such as name="James". 

        :param pair: Optional keyword param. Instead of supplying key=name 
                     and value = 'James', you can supply a key/value pair in
                     the form of name='James'.
        """
        key, value = self._get_key_value(key,value,pair)
        resp = self.client.lookup_vertex(self.index_name,key,value)
        if resp.total_size > 0:
            result = get_one_result(resp)
            return initialize_element(self.client, result)

    def remove(self,_id,key=None,value=None,**pair):
        """
        Remove the element from the index located by key/value.

        :param _id: The element ID.

        :param key: The index key. This is optional because you can instead 
                    supply a key/value pair such as name="James". 

        :param value: The index key's value. This is optional because you can 
                      instead supply a key/value pair such as name="James". 

        :param pair: Optional keyword param. Instead of supplying key=name 
                     and value = 'James', you can supply a key/value pair in
                     the form of name='James'.
        """
        key, value = self._get_key_value(key, value, pair)
        remove = self._get_method(vertex="remove_vertex", edge="remove_edge")
        return remove(self.index_name,_id,key,value)


class AutomaticIndex(Index):

    def keys(self):
        """Return the index's keys."""
        resp = self.client.index_keys(self.index_name)
        return list(resp.results)
    
    def rebuild(self):
        # need class_map b/c the Blueprints need capitalized class names, 
        # but Rexster returns lower-case class names for index_class
        method_map = dict(vertex=self.client.rebuild_vertex_index,
                          edge=self.client.rebuild_edge_index)
        rebuild_method = method_map.get(self.index_class)
        resp = rebuild_method(self.index_name)
        return list(resp.results)

 

########NEW FILE########
__FILENAME__ = bulbs_tests
import sys
import unittest
import argparse
from bulbs.config import Config, DEBUG
from bulbs.tests import BulbsTestCase, bulbs_test_suite
from bulbs.rexster import Graph, RexsterClient, REXSTER_URI, \
    VertexIndexProxy, EdgeIndexProxy, ManualIndex
from bulbs.tests import GremlinTestCase

# Setting a module var looks to be the easiest way to do this
db_name = "emptygraph"  # emptygraph has mock transactions enabled by default

def test_suite():
    # pass in a db_name to test a specific database
    client = RexsterClient(db_name=db_name)
    BulbsTestCase.client = client
    BulbsTestCase.vertex_index_proxy = VertexIndexProxy
    BulbsTestCase.edge_index_proxy = EdgeIndexProxy
    BulbsTestCase.index_class = ManualIndex
    BulbsTestCase.graph = Graph(client.config)

    suite = bulbs_test_suite()
    #suite.addTest(unittest.makeSuite(RestTestCase))
    suite.addTest(unittest.makeSuite(GremlinTestCase))
    return suite

if __name__ == '__main__':

    # TODO: Bubble up the command line option to python setup.py test.
    # http://eli.thegreenplace.net/2011/08/02/python-unit-testing-parametrized-test-cases/
    # http://www.doughellmann.com/PyMOTW/argparse/

    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default="emptygraph")
    args = parser.parse_args()
    
    db_name = args.db

    # Now set the sys.argv to the unittest_args (leaving sys.argv[0] alone)
    sys.argv[1:] = []

    unittest.main(defaultTest='test_suite')

########NEW FILE########
__FILENAME__ = client_tests
import sys
import argparse

import unittest
from bulbs.config import Config
from bulbs.tests.client_tests import ClientTestCase
from bulbs.tests.client_index_tests import ClientIndexTestCase
from bulbs.rexster.client import RexsterClient, REXSTER_URI, DEBUG

import time

# Default database. You can override this with the command line:
# $ python client_tests.py --db mydb
db_name = "emptygraph"  #  emtpygraph has mock transactions enabled

#client = RexsterClient(db_name=db_name)
#client.config.set_logger(DEBUG)

class RexsterClientTestCase(ClientTestCase):

    def setUp(self):
        self.client = RexsterClient(db_name=db_name)

# Separated client index tests for Titan
class RexsterClientIndexTestCase(ClientIndexTestCase):

    def setUp(self):
        self.client = RexsterClient(db_name=db_name)
 
# automatic tests not currenly implemented... - JT
class RexsterAutomaticIndexTestCase(unittest.TestCase):

    def setUp(self):
        self.client = RexsterClient(db_name=db_name)

    def test_create_automatic_vertex_index(self):
        index_name = "test_automatic_idxV"
        element_class = "TestVertex"
        self._delete_vertex_index(index_name)
        resp = self.client.create_automatic_vertex_index(index_name,element_class)
        

    def test_create_automatic_indexed_vertex(self):
        index_name = "test_automatic_idxV"
        timestamp = int(time.time())
        timestamp = 12345
        data = dict(name="James",age=34,timestamp=timestamp)
        resp = self.client.create_indexed_vertex_automatic(data,index_name)
        resp = self.client.lookup_vertex(index_name,"timestamp",timestamp)

def rexster_client_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RexsterClientTestCase))
    suite.addTest(unittest.makeSuite(RexsterClientIndexTestCase))
    return suite

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=None)
    args = parser.parse_args()
    
    db_name = args.db

    # Now set the sys.argv to the unittest_args (leaving sys.argv[0] alone)
    sys.argv[1:] = []
    
    unittest.main(defaultTest='rexster_client_suite')

########NEW FILE########
__FILENAME__ = index_tests
# -*- coding: utf-8 -*-
#
# Copyright 2011 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
import unittest

from bulbs.tests.testcase import BulbsTestCase
from bulbs.element import Vertex, VertexProxy, Edge, EdgeProxy
from bulbs.config import Config
    
from bulbs.rexster import RexsterClient, REXSTER_URI
from bulbs.rexster.index import VertexIndexProxy, EdgeIndexProxy, ManualIndex

config = Config(REXSTER_URI)
BulbsTestCase.client = RexsterClient(config)
BulbsTestCase.index_class = ManualIndex

# is this being used anywhere? -- JT 10/22/2012

class IndexTestCase(BulbsTestCase):
    
    def setUp(self):
        self.indicesV = VertexIndexProxy(self.index_class,self.client)
        self.indicesE = EdgeIndexProxy(self.index_class,self.client)

        self.indicesV.delete("test_idxV")
        self.indicesE.delete("test_idxE")

        self.vertices = VertexProxy(Vertex,self.client)
        self.vertices.index = self.indicesV.get_or_create("test_idxV")

        self.edges = EdgeProxy(Edge,self.client)
        self.edges.index = self.indicesE.get_or_create("test_idxE")

    def test_index(self):
        index_name = "test_idxV"
        # need to fix this to accept actual data types in POST
        #ikeys = '[name,location]'
        #self.indices.delete(index_name)
        #i1 = self.indices.create(index_name,Vertex)
        #assert i1.index_name == index_name
        #assert i1.index_type == "automatic"

        james = self.vertices.create({'name':'James'})
        self.vertices.index.put(james._id,'name','James')
        self.vertices.index.put(james._id,'location','Dallas')
        results = self.vertices.index.lookup('name','James')
        results = list(results)
        #print "RESULTS", results
        assert len(results) == 1
        assert results[0].name == "James"
        total_size = self.vertices.index.count('name','James')
        assert total_size == 1
        # NOTE: only automatic indices have user provided keys
        #keys = self.vertices.index..keys()
        #assert 'name' in keys
        #assert 'location' in keys
        i2 = self.indicesV.get(index_name)
        #print "INDEX_NAME", index_name, self.vertices.index..index_name, i2.index_name
        assert self.vertices.index.index_name == i2.index_name
        
        # remove vertex is bugged
        #self.vertices.index..remove(james._id,'name','James')
        #james = self.vertices.index..get_unique('name','James')
        #assert james is None
  
        # only can rebuild automatic indices
        #i3 = self.indices.get("vertices",Vertex)
        #results = i3.rebuild()
        #assert type(results) == list

        self.indicesV.delete(index_name)

        
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(IndexTestCase))

    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')


########NEW FILE########
__FILENAME__ = bulbs_tests
import unittest

from .rest_tests import RestTestCase
from .element_tests import VertexTestCase, VertexProxyTestCase, EdgeProxyTestCase
from .graph_tests import GraphTestCase
from .index_tests import IndexTestCase
from .model_tests import NodeTestCase, RelationshipTestCase
from .gremlin_tests import GremlinTestCase
from .testcase import BulbsTestCase



def bulbs_test_suite():

    suite = unittest.TestSuite()
    #suite.addTest(unittest.makeSuite(RestTestCase))
    suite.addTest(unittest.makeSuite(VertexTestCase))
    suite.addTest(unittest.makeSuite(VertexProxyTestCase))
    suite.addTest(unittest.makeSuite(EdgeProxyTestCase))
    # TODO: Add automatic/key-index tests
    #try:
        # Temporary hack...
        # The IndexTestCase currently only tests manual indices
        # but Titan only uses an automatic KeyIndex, and 
        # its index_type is hardcoded to "automatic"
        # index_type is a property that requires results being set so
        # it will barf if it's not hardcoded like Titan
        # so if it barfs, we know it's a manual index and thus
        # we want to run the test
     #   BulbsTestCase.index_class(None, None).index_type
      #  print "NOT RUNNING INDEX TESTS..."
        # don't run the test for Titan
    #except:
    suite.addTest(unittest.makeSuite(IndexTestCase))
    suite.addTest(unittest.makeSuite(NodeTestCase))
    suite.addTest(unittest.makeSuite(RelationshipTestCase))
    suite.addTest(unittest.makeSuite(GraphTestCase))
    #suite.addTest(unittest.makeSuite(GremlinTestCase))


    return suite

########NEW FILE########
__FILENAME__ = client_index_tests
import unittest
import random

from bulbs.config import Config, DEBUG, ERROR
from bulbs.registry import Registry
from bulbs.base import TypeSystem

class ClientIndexTestCase(unittest.TestCase):
    
    def setUp(self):
        self.client = None
        raise NotImplementedError

    # Some server implementations (Rexster) return a 404 if index doesn't exist
    def _delete_vertex_index(self,index_name):
        try:
            self.client.delete_vertex_index(index_name)
        except LookupError:
            pass

    def _delete_edge_index(self,index_name):
        try:
            self.client.delete_edge_index(index_name)
        except LookupError:
            pass

    # Index Controller Tests

    def test_create_vertex_index(self):
        index_name = "test_idxV"
        self._delete_vertex_index(index_name)
        resp = self.client.create_vertex_index(index_name)

        assert resp.results.get_index_class() == "vertex"        
        assert resp.results.get_index_name() == index_name
                
    def test_get_vertex_index(self):
        index_name = "test_idxV"
        resp = self.client.get_vertex_index(index_name)

        assert resp.results.get_index_class() == "vertex"        
        assert resp.results.get_index_name() == index_name


    # Index Container Tests

    def test_indexed_vertex_CRUD(self):

        index_name = "test_idxV"
        self._delete_vertex_index(index_name)
        self.client.create_vertex_index(index_name)

        # Create and Index Vertex
        name1 = "James %s" % random.random()
        age1 = 34
        data1 = dict(name=name1, age=age1)
        keys1 = ['name']
        self.client.create_indexed_vertex(data1, index_name, keys1)
        
        # Lookup Vertex
        resp1 = self.client.lookup_vertex(index_name, "name", name1)
        results1 = next(resp1.results)

        assert results1.get_type() == "vertex"
        assert results1.get_data() == data1  
        assert results1.data.get('name') == name1
        assert results1.data.get('age') == age1

        # Update and Index Vertex (update doesn't return data)
        _id = results1.get_id()
        name2 = "James Thornton %s" % random.random()
        age2 = 35
        data2 = dict(name=name2, age=age2)
        keys2 = None
        self.client.update_indexed_vertex(_id, data2, index_name, keys2)

        # Lookup Vertex
        resp2 = self.client.lookup_vertex(index_name, "name", name2)
        result2 = next(resp2.results)

        assert result2.get_type() == "vertex"
        assert result2.get_data() == data2
        assert result2.data.get('name') == name2
        assert result2.data.get('age') == age2

        # Remove a vertex from the index
        self.client.remove_vertex(index_name, _id, "name", name2)
        resp3 = self.client.lookup_vertex(index_name, "name", name2)
        assert resp3.total_size == 0
        
    def test_indexed_edge_CRUD(self):
        index_name = "test_idxE"
        self._delete_edge_index(index_name)
        self.client.create_edge_index(index_name)

        respV1 = self.client.create_vertex({'name':'James','age':34})
        respV2 = self.client.create_vertex({'name':'Julie','age':28})
        V1_id = respV1.results.get_id()
        V2_id = respV2.results.get_id()

        # Create and Index Edge
        city1 = "Dallas"
        data1 = dict(city=city1)
        keys1 = ['city']
        resp = self.client.create_indexed_edge(V1_id, "knows", V2_id, data1, index_name, keys1)
        
        # Lookup Edge
        resp1 = self.client.lookup_edge(index_name, "city", city1)
        results1 = next(resp1.results)

        assert results1.get_type() == "edge"
        assert results1.get_data() == data1  
        assert results1.data.get('city') == city1

        # Update and Index Edge (update doesn't return data)
        _id = results1.get_id()
        city2 = "Austin"
        data2 = dict(city=city2)
        keys2 = ['city']
        self.client.update_indexed_edge(_id, data2, index_name, keys2)

        # Lookup Edge
        resp2 = self.client.lookup_edge(index_name, "city", city2)
        result2 = next(resp2.results)

        assert result2.get_type() == "edge"
        assert result2.get_data() == data2
        assert result2.data.get('city') == city2

        # Remove and edge from the index
        self.client.remove_edge(index_name, _id, "city", city2)
        
        resp3 = self.client.lookup_edge(index_name, "city", city2)
        assert resp3.total_size == 0
        



########NEW FILE########
__FILENAME__ = client_tests
import unittest
import random

from bulbs.config import Config, DEBUG, ERROR
from bulbs.registry import Registry
from bulbs.base import TypeSystem

class ClientTestCase(unittest.TestCase):
    
    def setUp(self):
        self.client = None
        raise NotImplementedError

    def test_init(self):
        
        assert self.client.default_uri is not None
        assert isinstance(self.client.config, Config) 
        assert isinstance(self.client.registry, Registry)
        assert isinstance(self.client.type_system, TypeSystem)

    # Vertex Proxy

    def test_create_vertex(self):
        name, age = "James", 34
        data = dict(name=name, age=age)
        resp = self.client.create_vertex(data)
        assert resp.results.get_type() == "vertex"
        assert resp.results.get_data() == data  
        assert resp.results.data.get('name') == name
        assert resp.results.data.get('age') == age
  
    def test_get_vertex(self):
        name, age = "James", 34
        data = dict(name=name,age=age)
        resp1 = self.client.create_vertex(data)
        resp2 = self.client.get_vertex(resp1.results.get_id())
        assert resp1.results.data == resp2.results.data

    def test_get_all_vertices(self):
        resp = self.client.get_all_vertices()
        assert resp.total_size > 1

    def test_update_vertex(self):
        name1, age1 = "James", 34
        data1 = dict(name=name1, age=age1)
        resp1 = self.client.create_vertex(data1)        

        name2, age2 = "Julie", 28
        data2 = dict(name=name2,age=age2)
        resp2 = self.client.update_vertex(resp1.results.get_id(), data2)

        resp3 = self.client.get_vertex(resp1.results.get_id())

        assert resp3.results.get_type() == "vertex"
        assert resp3.results.data.get('name') == name2
        assert resp3.results.data.get('age') == age2

    def test_delete_vertex(self):
        name, age = "James", 34
        data = dict(name=name,age=age)
        resp1 = self.client.create_vertex(data)        

        deleted = False
        resp2 = self.client.delete_vertex(resp1.results.get_id())
        try:
            resp3 = self.client.get_vertex(resp1.results.get_id())
        except LookupError:
            deleted = True
        assert deleted is True

    # Edges
    def test_create_edge(self):
        resp1 = self.client.create_vertex({'name':'James','age':34})
        resp2 = self.client.create_vertex({'name':'Julie','age':28})

        outV = resp1.results.get_id()
        inV = resp2.results.get_id()
        label = "knows"
        data = dict(timestamp=123456789)
        resp3 = self.client.create_edge(outV, label, inV, data)

        assert resp3.results.get_type() == "edge"
        assert resp3.results.get_label() == label
        assert resp3.results.get_outV() == outV
        assert resp3.results.get_inV() == inV
        assert resp3.results.get_data() == data

    def test_get_edge(self):
        resp1 = self.client.create_vertex({'name':'James','age':34})
        resp2 = self.client.create_vertex({'name':'Julie','age':28})

        outV = resp1.results.get_id()
        inV = resp2.results.get_id()
        label = "knows"

        resp3 = self.client.create_edge(outV,label,inV)
        resp4 = self.client.get_edge(resp3.results.get_id())

        assert resp3.results.get_id() == resp4.results.get_id()
        assert resp3.results.get_type() == resp4.results.get_type()
        assert resp3.results.get_data() == resp4.results.get_data()

    def test_get_all_edges(self):
        resp1 = self.client.create_vertex({'name':'James','age':34})
        resp2 = self.client.create_vertex({'name':'Julie','age':28})

        outV = resp1.results.get_id()
        inV = resp2.results.get_id()
        label = "knows"
        data = dict(timestamp=123456789)
        resp3 = self.client.create_edge(outV, label, inV, data)
        resp4 = self.client.create_edge(inV, label, outV, data)

        resp = self.client.get_all_edges()
        assert resp.total_size > 1

    def test_update_edge(self):
        resp1 = self.client.create_vertex({'name':'James','age':34})
        resp2 = self.client.create_vertex({'name':'Julie','age':28})

        outV = resp1.results.get_id()
        inV = resp2.results.get_id()
        label = "knows"
        resp3 = self.client.create_edge(outV,label,inV)

        data = dict(timestamp=12345678)
        resp4 = self.client.update_edge(resp3.results.get_id(),data)

        assert resp4.results.get_data() == data

    def test_delete_edge(self):
        resp1 = self.client.create_vertex({'name':'James','age':34})
        resp2 = self.client.create_vertex({'name':'Julie','age':28})
        outV = resp1.results.get_id()
        inV = resp2.results.get_id()
        label = "knows"
        resp3 = self.client.create_edge(outV,label,inV)

        deleted = False
        resp4 = self.client.delete_edge(resp3.results.get_id())
        try:
            resp4 = self.client.get_edge(resp3.results.get_id())
        except LookupError:
            deleted = True
        assert deleted is True


    def test_vertex_container(self):
        resp1 = self.client.create_vertex({'name':'James','age':34})
        resp2 = self.client.create_vertex({'name':'Julie','age':28})

        outV = vertex_id1 =resp1.results.get_id()
        inV = vertex_id2 = resp2.results.get_id()
        label = "knows"

        resp3 = self.client.create_edge(outV, label, inV)
        edge_id = resp3.results.get_id()

        # Get the outgoing edge of vertex1
        outE = self.client.outE(vertex_id1).one()
        assert outE.get_id() == edge_id

        # Get the incoming edge of vertex2
        inE = self.client.inE(vertex_id2).one()
        assert inE.get_id() == edge_id

        # Get the incoming and outgoing edges of vertex1
        bothE = self.client.outE(vertex_id1).one()
        assert bothE.get_id() == edge_id
        
        # Get the outgoing edge of vertex1
        outV = self.client.outV(vertex_id1).one()
        assert outV.get_id() == vertex_id2

        # Get the incoming edge of vertex2
        inV = self.client.inV(vertex_id2).one()
        assert inV.get_id() == vertex_id1

        # Get the incoming and outgoing edges of vertex1
        bothV = self.client.outV(vertex_id1).one()
        assert bothV.get_id() == vertex_id2


#
# NOTE: client index tests moved to client_index_tests.py
#       because Titan does indexing differently - JT 10/22/2012
#    



########NEW FILE########
__FILENAME__ = element_tests
# -*- coding: utf-8 -*-
#
# Copyright 2011 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
import time
import unittest

from bulbs import config
from bulbs.element import Vertex, VertexProxy, EdgeProxy, Edge

from .testcase import BulbsTestCase

class VertexProxyTestCase(BulbsTestCase):

    def setUp(self):
        self.vertices = VertexProxy(Vertex,self.client)

    def test_create(self):
        james = self.vertices.create({'name':'James'})
        assert isinstance(james,Vertex)
        #assert type(james._id) == int
        assert james._type == "vertex"
        assert james.name == "James"

    def test_update_and_get(self):
        james1 = self.vertices.create({'name':'James'})
        self.vertices.update(james1._id, {'name':'James','age':34})
        james2 = self.vertices.get(james1._id)
        assert james2._id == james1._id
        assert james2.name == "James"
        assert james2.age == 34


    #def test_get_all(self):
     #   vertices = self.vertices.get_all()
    #    vertices = list(vertices)
    #    assert len(vertices) > 0

    #def test_remove_property(self):
    #    query_time = self.vertices.remove(self.james._id,'age')
    #    assert type(query_time) == float
    #    assert self.james.age is None

    def test_delete_vertex(self):
        james = self.vertices.create({'name':'James'})
        resp = self.vertices.delete(james._id)
        j2 = self.vertices.get(james._id)
        assert j2 == None

    def test_ascii_encoding(self):
        # http://stackoverflow.com/questions/19824952/unicodeencodeerror-bulbs-and-neo4j-create-model
        data = {u'name': u'Aname M\xf6ller'}
        v1a = self.vertices.create(data)
        v1b = self.vertices.get(v1a._id)
        assert v1b.name == data['name']



class VertexTestCase(BulbsTestCase):
    
    def setUp(self):
        self.vertices = VertexProxy(Vertex,self.client)
        self.edges = EdgeProxy(Edge,self.client)
        self.james = self.vertices.create({'name':'James'})
        self.julie = self.vertices.create({'name':'Julie'})
        self.edges.create(self.james,"test",self.julie)
        self.edges.create(self.julie,"test",self.james)
        
    def test_init(self):
        #assert type(self.james._id) == int
        assert isinstance(self.james,Vertex)

        assert self.james._type == "vertex"
        assert self.james.name == "James"

        assert self.julie._type == "vertex"
        assert self.julie.name == "Julie"

    def test_get_out_edges(self):
        edges = self.james.outE()
        edges = list(edges)
        assert len(edges) == 1

    def test_get_in_edges(self):
        edges = self.james.inE()
        edges = list(edges)
        assert len(edges) == 1

    def test_get_both_edges(self):
        edges = self.james.bothE()
        edges = list(edges)
        assert len(edges) == 2

    def test_get_both_labeled_edges(self):
        edges = self.james.bothE("test")
        edges = list(edges)
        assert len(edges) == 2

class EdgeProxyTestCase(BulbsTestCase):

    def setUp(self):
        self.vertices = VertexProxy(Vertex,self.client)
        self.edges = EdgeProxy(Edge,self.client)
        self.james = self.vertices.create({'name':'James'})
        self.julie = self.vertices.create({'name':'Julie'})
        
    def test_create(self):
        data = dict(timestamp=int(time.time()))
        edge = self.edges.create(self.james, "test", self.julie, data)
        assert edge._outV == self.james._id
        assert edge._label == "test"
        assert edge._inV == self.julie._id
        
    def test_update_and_get(self):
        now = int(time.time())
        e1 = self.edges.create(self.james,"test",self.julie, {'timestamp': now})
        assert e1.timestamp == now
        later = int(time.time())
        self.edges.update(e1._id, {'timestamp': later})
        e2 = self.edges.get(e1._id)
        assert e1._id == e2._id
        assert e1._inV == e2._inV
        assert e1._label == e2._label
        assert e1._outV == e2._outV
        assert e2.timestamp == later


    #def test_get_all(self):
    #    edges = self.edges.get_all()
    #    edges = list(edges)
    #    assert type(edges) == list

    #def test_remove_property(self):
    #    e1 = self.edges.create(self.james,"test",self.julie,{'time':'today'})
    #    query_time = self.edges.remove(e1._id,{'time'})
    #    assert type(query_time) == float
    #    assert e1.time is None

    def test_delete_edge(self):
        e1 = self.edges.create(self.james,"test",self.julie)
        resp = self.edges.delete(e1._id)
        e2 = self.edges.get(e1._id)
        assert e2 == None
        
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(VertexProxyTestCase))
    suite.addTest(unittest.makeSuite(VertexTestCase))
    suite.addTest(unittest.makeSuite(EdgeProxyTestCase))
    # NOTE: there are no tests for the Edge because it doesn't have methods.

    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')


########NEW FILE########
__FILENAME__ = graph_tests
import unittest

from bulbs.config import Config
from bulbs.property import String
from bulbs.element import VertexProxy, EdgeProxy
from bulbs.model import Node, NodeProxy, Relationship, RelationshipProxy
from bulbs.base.client import Client

from .testcase import BulbsTestCase


# Test Models

class User(Node):

    element_type = "user"

    name = String(nullable=False)
    username = String(nullable=False)
  
class Group(Node):

    element_type = "group"

    name = String(nullable=False)

class Member(Relationship):

    label = "member"
    


class GraphTestCase(BulbsTestCase):

    def test_init(self):
        assert isinstance(self.graph.config, Config)
        assert isinstance(self.graph.client, Client)
        assert isinstance(self.graph.vertices, VertexProxy)
        assert isinstance(self.graph.edges, EdgeProxy)

    def test_add_proxy(self):
        self.graph.add_proxy("users", User)
        self.graph.add_proxy("groups", Group)
        self.graph.add_proxy("members", Member)

        assert isinstance(self.graph.users, NodeProxy)
        assert isinstance(self.graph.groups, NodeProxy)
        assert isinstance(self.graph.members, RelationshipProxy)
        
        
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(GraphTestCase))

    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')


########NEW FILE########
__FILENAME__ = gremlin_tests
import unittest
from .testcase import BulbsTestCase

class GremlinTestCase(BulbsTestCase):

    def setUp(self):
        #    self.client = RexsterClient()
        #    self.vertex_type = "vertex"
        #    self.edge_type = "edge"
        #raise NotImplemented
        pass

    def test_gremlin(self):
        # limiting return count so we don't exceed heap size
        resp = self.client.gremlin("g.V[0..9]")
        assert resp.total_size > 5

########NEW FILE########
__FILENAME__ = index_tests
# -*- coding: utf-8 -*-
#
# Copyright 2011 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
import unittest
import random

import bulbs.utils
from bulbs.config import Config, DEBUG, ERROR
from bulbs.element import Vertex, VertexProxy, Edge, EdgeProxy       
from .testcase import BulbsTestCase


class IndexTestCase(BulbsTestCase):
    
    def setUp(self):
        self.indicesV = self.vertex_index_proxy(self.index_class,self.client)
        self.indicesE = self.edge_index_proxy(self.index_class,self.client)

        self.indicesV.delete("test_idxV")
        self.indicesE.delete("test_idxE")
        
        self.vertices = VertexProxy(Vertex,self.client)
        self.vertices.index = self.indicesV.get_or_create("test_idxV")

        self.edges = EdgeProxy(Edge,self.client)
        self.edges.index = self.indicesE.get_or_create("test_idxE")
               
    def test_index(self):
        index_name = "test_idxV"
        # need to fix this to accept actual data types in POST
        ikeys = '[name,location]'
        james = self.vertices.create({'name':'James'})
        self.vertices.index.put(james._id,'name','James')
        self.vertices.index.put(james._id,'location','Dallas')
        results = self.vertices.index.lookup('name','James')
        results = list(results)
        assert len(results) == 1
        assert results[0].name == "James"
        
        total_size = self.vertices.index.count('name','James')
        assert total_size == 1
        i2 = self.indicesV.get(index_name)
        assert self.vertices.index.index_name == i2.index_name
        
        self.vertices.index.remove(james._id,'name','James')
        james = self.vertices.index.get_unique('name','James')
        assert james is None
  
        self.indicesV.delete(index_name)

    def test_ascii_encoding_index_lookup(self):
        # Fixed for Neo4j Server. Still having issues with Rexster...
        # https://github.com/espeed/bulbs/issues/117
        # using default index name because that's what create_indexed_vertex() uses
        name = u'Aname M\xf6ller' + bulbs.utils.to_string(random.random())
        index_name = Vertex.get_index_name(self.vertices.client.config)
        self.vertices.client.config.set_logger(ERROR)
        self.vertices.index = self.indicesV.get_or_create(index_name)
        v1a = self.vertices.create(name=name)
        v1b = self.vertices.index.lookup(u"name", name)
        assert next(v1b).name == name

    def test_ascii_encoding_index_lookup2(self):
        # http://stackoverflow.com/questions/23057915/rexster-bulbs-unicode-node-property-node-created-but-not-found
        # using default index name because that's what create_indexed_vertex() uses
        name = u'Université de Montréal' + bulbs.utils.to_string(random.random())
        index_name = Vertex.get_index_name(self.vertices.client.config)
        self.vertices.client.config.set_logger(ERROR)
        self.vertices.index = self.indicesV.get_or_create(index_name)
        v1a = self.vertices.create(name=name)
        v1b = self.vertices.index.lookup(u"name", name)
        assert next(v1b).name == name





########NEW FILE########
__FILENAME__ = model_tests
import unittest
from .testcase import BulbsTestCase
from bulbs.model import Node, NodeProxy, Relationship, RelationshipProxy
from bulbs.property import Integer, String, DateTime, Bool
from bulbs.utils import current_datetime

class Knows(Relationship):

    label = "knows"
    timestamp = DateTime(default=current_datetime)

# Lightbulb Person model doesn't have age so it breaks get_all() when in use
class Person(Node):

    element_type = "person"
    
    name = String(nullable=False)
    age  = Integer()
    is_adult = Bool()



class NodeTestCase(BulbsTestCase):

    def setUp(self):
        indices = self.vertex_index_proxy(self.index_class,self.client)
        self.people = NodeProxy(Person,self.client)
        self.people.index = indices.get_or_create("person")
        self.james = self.people.create(name="James", age=34, is_adult=True)

    def test_properties(self):
        #assert type(self.james.eid) == int
        assert self.james.element_type == "person"
        assert self.james.name == "James"
        assert self.james.age == 34
        assert self.james.is_adult is True

    def test_get(self):
        person = self.people.get(self.james.eid)
        assert person == self.james
        
    def test_get_all(self):
        people = self.people.get_all()
        assert len(list(people)) > 1
        
    def test_index_name(self):
        index_name = self.people.index.index_name
        assert index_name == "person"

    # Will this work for autmatic indices?
    #def test_index_put_and_get(self): 
        # must test put/get together b/c self.james gets reset every time
     #   self.people.index.put(self.james.eid,age=self.james.age)
     #   james = self.people.index.get_unique("age",'34')
     #   assert self.james == james
        #Person.remove(self.james.eid,dict(age="34"))


class RelationshipTestCase(BulbsTestCase):

    def setUp(self):
        indicesV = self.vertex_index_proxy(self.index_class,self.client)
        indicesE = self.edge_index_proxy(self.index_class,self.client)

        self.people = NodeProxy(Person,self.client)
        self.people.index = indicesV.get_or_create("people")

        self.knows = RelationshipProxy(Knows,self.client)
        self.knows.index = indicesE.get_or_create("knows")

        self.james = self.people.create(name="James", age=34)
        self.julie = self.people.create(name="Julie", age=28)
        
    def test_properties(self):
        self.relationship = self.knows.create(self.james,self.julie)
        assert self.relationship._label == "knows"
        assert self.relationship.outV()._id == self.james.eid
        assert self.relationship.inV()._id == self.julie.eid

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(NodeTestCase))
    suite.addTest(unittest.makeSuite(RelationshipTestCase))

    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')


########NEW FILE########
__FILENAME__ = rest_tests
import unittest
from bulbs.config import Config
#from bulbs.rest import Request

from bulbs.utils import build_path
from bulbs.rexster.client import RexsterRequest

class RestTestCase(unittest.TestCase):
    
    def setUp(self):
        #self.client = Client(config.DATABASE_URL)
        config = Config(root_uri=None)
        self.request = RexsterRequest(config)

    def test_init(self):
        config = Config('http://localhost:8182/not-graphs/gratefulgraph')
        assert config.root_uri == 'http://localhost:8182/not-graphs/gratefulgraph'

    def test_post(self):
        name_in = "james"
        email_in = "james@jamesthornton.com"

        path = build_path("vertices")
        params = dict(name=name_in, email=email_in)
        resp = self.request.post(path,params)
                
        assert resp.results._type == 'vertex'
        assert name_in == resp.results.get('name') 
        assert email_in == resp.results.get('email')

        # use the results of this function for get and delete tests 
        return resp
        
    def test_get(self):
        resp1 = self.test_post()
        oid1 = resp1.results.get('_id')
        element_type1 = resp1.results.get('_type')
        name1 = resp1.results.get('name')
        email1 = resp1.results.get('email')

        path = build_path("vertices",oid1)
        params = dict(name=name1, email=email1)
        resp2 = self.request.get(path,params)

        assert oid1 == resp2.results.get('_id')
        assert element_type1 == resp2.results.get('_type')
        assert name1 == resp2.results.get('name')
        assert email1 == resp2.results.get('email')

    def test_delete(self):

        resp1 = self.test_post()
        oid1 = resp1.results.get('_id')
        name1 = resp1.results.get('name')
        email1 = resp1.results.get('email')

        # make sure it's there
        #assert type(oid1) == int

        # delete it
        path = build_path("vertices",oid1)
        params = dict(name=name1, email=email1)
        resp2 = self.request.delete(path,params)

        # verify it's gone
        #assert "SNAPSHOT" in resp2.rexster_version
        #assert type(resp2.get('query_time')) == float
        assert resp2.results == None


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RestTestCase))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')


########NEW FILE########
__FILENAME__ = testcase
import unittest

class BulbsTestCase(unittest.TestCase):

    client = None
    index_class = None
    

########NEW FILE########
__FILENAME__ = batch

# NOTE: This isn't fully baked. Will probably redo this and 
# create a BatchClient like in neo4jserver/batch.py

class RexsterTransaction(object):

    def __init__(self):
        self.actions = []

    def create_edge(self,outV,label,inV,data={}):
        edge_data = dict(_outV=outV,_label=label,_inV=inV)
        data.update(edge_data)
        action = build_action("create","edge",data)
        self.actions.append(action)

    def build_action(self,_action,_type,data={}):
        action = {'_action':_action,'_type':_type}
        for key in data:  # Python 3
            value = data[key]
            action.update({key:value})
        return action              
          

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Bulbs supports pluggable clients. This is the Rexster client.

"""
from bulbs.config import Config, DEBUG
from bulbs.registry import Registry
from bulbs.utils import get_logger

# specific to this client
from bulbs.json import JSONTypeSystem
from bulbs.base import Client, Response, Result 
from bulbs.rest import Request, RESPONSE_HANDLERS
from bulbs.groovy import GroovyScripts

from bulbs.utils import json, build_path, get_file_path, urlsplit, coerce_id


##### Titan

from bulbs.rexster.client import RexsterClient, \
    RexsterResponse, RexsterResult

# The default URIs
TITAN_URI = "http://localhost:8182/graphs/graph"

# The logger defined in Config
log = get_logger(__name__)

# Rexster resource paths
# TODO: local path vars would be faster
vertex_path = "vertices"
edge_path = "edges"
index_path = "indices"
gremlin_path = "tp/gremlin"
transaction_path = "tp/batch/tx"
multi_get_path = "tp/batch"
key_index_path = "keyindices"

class TitanResult(RexsterResult):
    """
    Container class for a single result, not a list of results.

    :param result: The raw result.
    :type result: dict

    :param config: The client Config object.
    :type config: Config 

    :ivar raw: The raw result.
    :ivar data: The data in the result.

    """
    pass


class TitanResponse(RexsterResponse):
    """
    Container class for the server response.

    :param response: httplib2 response: (headers, content).
    :type response: tuple

    :param config: Config object.
    :type config: bulbs.config.Config

    :ivar config: Config object.
    :ivar headers: httplib2 response headers, see:
        http://httplib2.googlecode.com/hg/doc/html/libhttplib2.html
    :ivar content: A dict containing the HTTP response content.
    :ivar results: A generator of RexsterResult objects, a single RexsterResult object, 
        or None, depending on the number of results returned.
    :ivar total_size: The number of results returned.
    :ivar raw: Raw HTTP response. Only set when log_level is DEBUG.

    """
    result_class = TitanResult



class TitanRequest(Request):
    """Makes HTTP requests to Rexster and returns a RexsterResponse.""" 
    
    response_class = TitanResponse


data_type = dict(string="String", 
                 integer="Integer", 
                 geoshape="Geoshape",)


class TitanClient(RexsterClient):
    """
    Low-level client that sends a request to Titan and returns a response.

    :param config: Optional Config object. Defaults to default Config.
    :type config: bulbs.config.Config

    :cvar default_uri: Default URI for the database.
    :cvar request_class: Request class for the Client.

    :ivar config: Config object.
    :ivar registry: Registry object.
    :ivar scripts: GroovyScripts object.  
    :ivar type_system: JSONTypeSystem object.
    :ivar request: TitanRequest object.

    Example:

    >>> from bulbs.titan import TitanClient
    >>> client = TitanClient()
    >>> script = client.scripts.get("get_vertices")
    >>> response = client.gremlin(script, params=None)
    >>> result = response.results.next()

    """ 
    #: Default URI for the database.
    default_uri = TITAN_URI
    request_class = TitanRequest



    def __init__(self, config=None, db_name=None):
        super(TitanClient, self).__init__(config, db_name)

        # override so Rexster create_vertex() method doesn't try to index
        self.config.autoindex = False 


    # GET 

    # these could replace the Rexster Gremlin version of these methods
    def outV(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "out")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)
    
    def inV(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "in")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)

    def bothV(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "both")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)

    def outV_count(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "outCount")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)

    def inV_count(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "inCount")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)

    def bothV_count(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "bothCount")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)

    def outV_ids(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "outIds")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)

    def inV_ids(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "inIds")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)

    def bothV_ids(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "bothIds")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)

    def outE(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "outE")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)
    
    def inE(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "inE")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)

    def bothE(self, _id, label=None, start=None, limit=None, properties=None):
        path = build_path(vertex_path, _id, "bothE")
        params = build_params(_label=label, _limit=limit, _properties=properties)
        return self.request.get(path, params)

    # Key Indices

    # Titan-Specific Index Methods

    # https://github.com/thinkaurelius/titan/wiki/Indexing-Backend-Overview                       
    # https://github.com/thinkaurelius/titan/wiki/Type-Definition-Overview

    def create_edge_label(self, label):
        # TODO: custom gremlin method
        pass

    def create_vertex_property_key():
        # TODO: custom gremlin method
        pass

    def create_edge_property_key():
        # TODO: custom gremlin method
        pass
    
    def create_vertex_key_index(self, key):
        path = build_path(key_index_path, "vertex", key)
        params = None
        return self.request.post(path, params)

    def create_edge_key_index(self, key):
        path = build_path(key_index_path, "edge", key)
        params = None
        return self.request.post(path, params)

    def get_vertex_keys(self):
        path = build_path(key_index_path, "vertex")
        params = None
        return self.request.get(path, params)

    def get_edge_keys(self):
        path = build_path(key_index_path, "edge")
        params = None
        return self.request.get(path, params)

    def get_all_keys(self):
        path = key_index_path
        params = None
        return self.request.get(path, params)


    # Index Proxy - General

    def get_all_indices(self):
        """Returns a list of all the element indices."""
        raise NotImplementedError

    def get_index(self, name):
        raise NotImplementedError

    def delete_index(self, name): 
        raise NotImplementedError
    
    # Index Proxy - Vertex

    def create_vertex_index(self, index_name, *args, **kwds):
        """
        Creates a vertex index with the specified params.

        :param index_name: Name of the index to create.
        :type index_name: str

        :rtype: TitanResponse

        """
        raise NotImplementedError

    def get_vertex_index(self, index_name):
        """
        Returns the vertex index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: TitanResponse

        """
        raise NotImplementedError

    def get_or_create_vertex_index(self, index_name, index_params=None):
        raise NotImplementedError
        
    def delete_vertex_index(self, name): 
        """
        Deletes the vertex index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: TitanResponse

        """
        raise NotImplementedError

    # Index Proxy - Edge
    # Titan does NOT support edge indices

    def create_edge_index(self, name, *args, **kwds):
        raise NotImplementedError
        
    def get_edge_index(self, name):
        """
        Returns the edge index with the index_name.

        :param index_name: Name of the index.
        :type index_name: str

        :rtype: TitanResponse

        """
        raise NotImplementedError
        
    def get_or_create_edge_index(self, index_name, index_params=None):
        raise NotImplementedError

    def delete_edge_index(self, name):
        raise NotImplementedError

    # Index Container - Vertex

    def put_vertex(self, index_name, key, value, _id):
        # Titan only supports automatic indices
        raise NotImplementedError

    def lookup_vertex(self, index_name, key, value):
        """
        Returns the vertices indexed with the key and value.

        :param index_name: Name of the index.
        :type index_name: str

        :param key: Name of the key.
        :type key: str

        :param value: Value of the key.
        :type value: str

        :rtype: TitanResponse

        """
        # NOTE: this is different than Rexster's version
        # it uses vertex_path instead of index_path, and 
        # index_name is N/A
        # Keeping method interface the same for practical reasons so
        # index_name will be ignored, any value will work.
        path = build_path(vertex_path)
        params = dict(key=key,value=value)
        return self.request.get(path,params)

    def query_vertex(self, index_name, params):
        """Queries for an vertex in the index and returns the Response."""
        path = build_path(index_path,index_name)
        return self.request.get(path,params)

    def remove_vertex(self,index_name,_id,key=None,value=None):
        # Titan only supports automatic indices
        raise NotImplementedError

    # Index Container - Edge 
    # Titan does NOT support edge indices

    def put_edge(self, index_name, key, value, _id):
        raise NotImplementedError

    def lookup_edge(self, index_name, key, value):
        """
        Looks up an edge in the index and returns the Response.
        """
        # NOTE: this is different than Rexster's version
        # it uses edge_path instead of index_path, and 
        # index_name is N/A
        # Keeping method interface the same for practical reasons so
        # index_name will be ignored, any value will work.
        #path = build_path(edge_path)
        #params = dict(key=key,value=value)
        #return self.request.get(path,params)
        raise NotImplementedError

    def query_edge(self, index_name, params):
        """Queries for an edge in the index and returns the Response."""
        raise NotImplementedError

    def remove_edge(self, index_name, _id, key=None, value=None):
        raise NotImplementedError
    
    # Model Proxy - Vertex

    def create_indexed_vertex(self, data, index_name, keys=None):
        """
        Creates a vertex, indexes it, and returns the Response.

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index.
        :type keys: list

        :rtype: TitanResponse

        """
        return self.create_vertex(data)
    
    def update_indexed_vertex(self, _id, data, index_name, keys=None):
        """
        Updates an indexed vertex and returns the Response.

        :param index_name: Name of the index.
        :type index_name: str

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index.
        :type keys: list

        :rtype: TitanResponse

        """
        return self.update_vertex(_id, data)

    # Model Proxy - Edge

    def create_indexed_edge(self, outV, label, inV, data, index_name, keys=None):
        """
        Creates a edge, indexes it, and returns the Response.

        :param outV: Outgoing vertex ID.
        :type outV: int

        :param label: Edge label.
        :type label: str

        :param inV: Incoming vertex ID.
        :type inV: int

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index. Defaults to None (indexes all properties).
        :type keys: list

        :rtype: TitanResponse

        """
        return self.create_edge(outV, label, inV, data)
        
    def update_indexed_edge(self, _id, data, index_name, keys=None):
        """
        Updates an indexed edge and returns the Response.

        :param _id: Edge ID.
        :type _id: int

        :param data: Property data.
        :type data: dict

        :param index_name: Name of the index.
        :type index_name: str

        :param keys: Property keys to index. Defaults to None (indexes all properties).
        :type keys: list

        :rtype: TitanResponse

        """
        return self.update_edge(_id, data)



# Utils

def build_params(**kwds):
    # Rexster isn't liking None param values
    params = dict()
    for key in kwds:
        value = kwds[key]
        if value is not None:
            params[key] = value
    return params

########NEW FILE########
__FILENAME__ = graph
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
Interface for interacting with a graph database through Rexster.

"""
from bulbs.config import Config
from bulbs.gremlin import Gremlin
from bulbs.element import Vertex, Edge
from bulbs.model import Node, Relationship
from bulbs.base.graph import Graph as BaseGraph

# Rexster-specific imports
from .client import TitanClient
from .index import KeyIndex


class Graph(BaseGraph):
    """
    The primary interface to Rexster.

    Instantiates the database :class:`~bulbs.rexster.client.Client` object using 
    the specified Config and sets up proxy objects to the database.

    :param config: Optional. Defaults to the default config.
    :type config: bulbs.config.Config

    :cvar client_class: RexsterClient class.
    :cvar default_index: Default index class.

    :ivar client: RexsterClient object.
    :ivar vertices: VertexProxy object.
    :ivar edges: EdgeProxy object.
    :ivar config: Config object.
    :ivar gremlin: Gremlin object.
    :ivar scripts: GroovyScripts object.
    
    Example:

    >>> from bulbs.rexster import Graph
    >>> g = Graph()
    >>> james = g.vertices.create(name="James")
    >>> julie = g.vertices.create(name="Julie")
    >>> g.edges.create(james, "knows", julie)

    """
    client_class = TitanClient
    default_index = KeyIndex
    
    def __init__(self, config=None):
        super(Graph, self).__init__(config)

        # Rexster supports Gremlin
        self.gremlin = Gremlin(self.client)
        self.scripts = self.client.scripts    # for convienience 


    def load_graphml(self,uri):
        """
        Loads a GraphML file into the database and returns the response.

        :param uri: URI of the GraphML file to load.
        :type uri: str

        :rtype: RexsterResult

        """
        script = self.client.scripts.get('load_graphml')
        params = dict(uri=uri)
        return self.gremlin.command(script, params)
        
    def get_graphml(self):
        """
        Returns a GraphML file representing the entire database.

        :rtype: RexsterResult

        """
        script = self.client.scripts.get('save_graphml')
        return self.gremlin.command(script, params=None)
        
    def warm_cache(self):
        """
        Warms the server cache by loading elements into memory.

        :rtype: RexsterResult

        """
        script = self.scripts.get('warm_cache')
        return self.gremlin.command(script, params=None)

    def clear(self):
        """
        Deletes all the elements in the graph.

        :rtype: RexsterResult

        .. admonition:: WARNING 

           This will delete all your data!

        """
        script = self.client.scripts.get('clear')
        return self.gremlin.command(script,params=None)



########NEW FILE########
__FILENAME__ = index
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
"""
An interface for interacting with indices on Rexster.

"""
from bulbs.utils import initialize_element, initialize_elements, get_one_result


class IndexProxy(object):
    """Abstract base class the index proxies."""

    def __init__(self, index_class, client):        
        # The index class for this proxy, e.g. ManualIndex.
        self.index_class = index_class

        # The Client object for the database.
        self.client = client
    

class VertexIndexProxy(IndexProxy):
    """
    Manage vertex indices on Rexster.

    :param index_class: The index class for this proxy, e.g. ManualIndex.
    :type index_class: Index

    :param client: The Client object for the database.
    :type client: bulbs.rexster.client.RexsterClient

    :ivar index_class: Index class.
    :ivar client: RexsterClient object.

    """
                        
    def create(self, index_name):
        """
        Creates an Vertex index and returns it.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.index.Index
        
        """
        raise NotImplementedError

    def get(self, index_name="vertex"):
        """
        Returns the Index object with the specified name or None if not found.
        
        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.index.Index
        
        """
        index = self.index_class(self.client, None)
        index.base_type = "vertex"
        index._index_name = index_name
        self.client.registry.add_index(index_name, index)
        return index

    def get_or_create(self, index_name="vertex", index_params=None):
        """
        Get a Vertex Index or create it if it doesn't exist.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.index.Index

        """ 
        return self.get(index_name)

    def delete(self, index_name):
        """ 
        Deletes an index and returns the Response.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.client.RexsterResponse

        """
        raise NotImplementedError


class EdgeIndexProxy(IndexProxy):
    """
    Manage edge indices on Rexster.

    :param index_class: The index class for this proxy, e.g. ManualIndex.
    :type index_class: Index

    :param client: The Client object for the database.
    :type client: bulbs.rexster.client.RexsterClient

    :ivar index_class: Index class.
    :ivar client: RexsterClient object.

    """

    def create(self,index_name,*args,**kwds):
        """ 
        Adds an index to the database and returns it. 

        index_keys must be a string in this format: '[k1,k2]'
        Don't pass actual list b/c keys get double quoted.

        :param index_name: The name of the index to create.

        :param index_class: The class of the elements stored in the index. 
                            Either vertex or edge.
        
        """
        raise NotImplementedError

    def get(self, index_name="edge"):
        """
        Returns the Index object with the specified name or None if not found.
        
        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.index.Index
        
        """
        index = self.index_class(self.client, None)
        index.base_type = "edge"
        index._index_name = index_name
        self.client.registry.add_index(index_name, index)
        return index


    def get_or_create(self, index_name="edge", index_params=None):
        """
        Get an Edge Index or create it if it doesn't exist.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.index.Index

        """ 
        return self.get(index_name)

    def delete(self,index_name):
        """ 
        Deletes an index and returns the Response.

        :param index_name: Index name.
        :type index_name: str

        :rtype: bulbs.rexster.client.RexsterResponse

        """
        raise NotImplementedError

#
# Index Containers (Titan only supports KeyIndex so far)
#

class Index(object):
    """Abstract base class for an index."""

    def __init__(self, client, result):
        self.client = client
        self.result = result
        self.base_type = None # set by Factory.get_index
        self._index_name = None # ditto 
        # the index_name is actually ignored with Titan, 
        # but setting it like normal to make tests pass

    @classmethod 
    def get_proxy_class(cls, base_type):
        """
        Returns the IndexProxy class.

        :param base_type: Index base type, either vertex or edge.
        :type base_type: str

        :rtype: class

        """
        class_map = dict(vertex=VertexIndexProxy, edge=EdgeIndexProxy)
        return class_map[base_type]

    @property
    def index_name(self):
        """
        Returns the index name.

        :rtype: str

        """
        # faking the index name as "vertex"
        return self._index_name

    @property
    def index_class(self):
        """
        Returns the index class, either vertex or edge.

        :rtype: class

        """
        return self.base_type
    
    @property
    def index_type(self):
        """
        Returns the index type, which will either be automatic or manual.

        :rtype: str

        """
        return "automatic"

    def count(self,key=None,value=None,**pair):
        """
        Return a count of all elements with 'key' equal to 'value' in the index.

        :param key: The index key. This is optional because you can instead 
                    supply a key/value pair such as name="James". 

        :param value: The index key's value. This is optional because you can 
                      instead supply a key/value pair such as name="James". 

        :param pair: Optional keyword param. Instead of supplying key=name 
                     and value = 'James', you can supply a key/value pair in
                     the form of name='James'.
        """
        raise NotImplementedError


    def _get_key_value(self, key, value, pair):
        """Return the key and value, regardless of how it was entered."""
        if pair:
            key, value = pair.popitem()
        return key, value

    def _get_method(self, **method_map):
        method_name = method_map[self.index_class]
        method = getattr(self.client, method_name)
        return method

    def lookup(self, key=None, value=None, **pair):
        """
        Return a generator containing all the elements with key property equal 
        to value in the index.

        :param key: The index key. This is optional because you can instead 
                    supply a key/value pair such as name="James". 

        :param value: The index key's value. This is optional because you can 
                      instead supply a key/value pair such as name="James". 

        :param raw: Optional keyword param. If set to True, it won't try to 
                    initialize the results. Defaults to False. 

        :param pair: Optional keyword param. Instead of supplying key=name 
                     and value = 'James', you can supply a key/value pair in
                     the form of name='James'.
        """
        key, value = self._get_key_value(key, value, pair)
        resp = self.client.lookup_vertex(self.index_name,key,value)
        return initialize_elements(self.client,resp)


    def get_unique(self,key=None,value=None,**pair):
        """
        Returns a max of 1 elements matching the key/value pair in the index.

        :param key: The index key. This is optional because you can instead 
                    supply a key/value pair such as name="James". 

        :param value: The index key's value. This is optional because you can 
                      instead supply a key/value pair such as name="James". 

        :param pair: Optional keyword param. Instead of supplying key=name 
                     and value = 'James', you can supply a key/value pair in
                     the form of name='James'.
        """
        key, value = self._get_key_value(key,value,pair)
        resp = self.client.lookup_vertex(self.index_name,key,value)
        if resp.total_size > 0:
            result = get_one_result(resp)
            return initialize_element(self.client, result)

class KeyIndex(Index):

    def keys(self):
        """Return the index's keys."""
        # Titan does not support edge indices.
        resp = self.client.get_vertex_keys()
        return [result.raw for result in resp.results]

    def create_key(self, key):
        # TODO: You can't create a key if prop already exists - workaround?
        if self.base_type is "edge":
            return self.create_edge_key(key)
        return self.create_vertex_key(key)
                        
    def create_vertex_key(self, key):
        return self.client.create_vertex_key_index(key)        

    def create_edge_key(self, key):
        return self.client.create_vertex_key_index(key)

    def rebuild(self):
        raise NotImplementedError # (for now)
        # need class_map b/c the Blueprints need capitalized class names, 
        # but Rexster returns lower-case class names for index_class
        method_map = dict(vertex=self.client.rebuild_vertex_index,
                          edge=self.client.rebuild_edge_index)
        rebuild_method = method_map.get(self.index_class)
        resp = rebuild_method(self.index_name)
        return list(resp.results)
        

 

########NEW FILE########
__FILENAME__ = bulbs_tests
import sys
import unittest
import argparse
from bulbs.config import Config, DEBUG
from bulbs.tests import BulbsTestCase, bulbs_test_suite
from bulbs.titan import Graph, TitanClient, TITAN_URI, \
    VertexIndexProxy, EdgeIndexProxy, KeyIndex
from bulbs.tests import GremlinTestCase

# Setting a module var looks to be the easiest way to do this
db_name = "graph"

def test_suite():
    # pass in a db_name to test a specific database
    client = TitanClient(db_name=db_name)
    BulbsTestCase.client = client
    BulbsTestCase.vertex_index_proxy = VertexIndexProxy
    BulbsTestCase.edge_index_proxy = EdgeIndexProxy
    BulbsTestCase.index_class = KeyIndex
    BulbsTestCase.graph = Graph(client.config)

    suite = bulbs_test_suite()
    #suite.addTest(unittest.makeSuite(RestTestCase))
    suite.addTest(unittest.makeSuite(GremlinTestCase))
    return suite

if __name__ == '__main__':

    # TODO: Bubble up the command line option to python setup.py test.
    # http://eli.thegreenplace.net/2011/08/02/python-unit-testing-parametrized-test-cases/
    # http://www.doughellmann.com/PyMOTW/argparse/

    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default="graph")
    args = parser.parse_args()
    
    db_name = args.db

    # Now set the sys.argv to the unittest_args (leaving sys.argv[0] alone)
    sys.argv[1:] = []

    unittest.main(defaultTest='test_suite')

########NEW FILE########
__FILENAME__ = client_tests
import sys
import argparse

import unittest
from bulbs.config import Config
from bulbs.tests.client_tests import ClientTestCase
from bulbs.tests.client_index_tests import ClientIndexTestCase
from bulbs.titan.client import TitanClient, TITAN_URI, DEBUG

import time

# Default database. You can override this with the command line:
# $ python client_tests.py --db mydb
db_name = "graph"

#client = TitanClient(db_name=db_name)
#client.config.set_logger(DEBUG)

class TitanClientTestCase(ClientTestCase):

    def setUp(self):
        self.client = TitanClient(db_name=db_name)

# Separated client index tests for Titan
class TitanClientIndexTestCase(ClientIndexTestCase):

    def setUp(self):
        self.client = TitanClient(db_name=db_name)
        
    def test_create_vertex_index(self):
        pass

    def test_get_vertex_index(self):
        pass

    def test_indexed_vertex_CRUD(self):
        pass

    def test_indexed_edge_CRUD(self):
        pass


def titan_client_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TitanClientTestCase))
    suite.addTest(unittest.makeSuite(TitanClientIndexTestCase))
    return suite

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=None)
    args = parser.parse_args()
    
    db_name = args.db

    # Now set the sys.argv to the unittest_args (leaving sys.argv[0] alone)
    sys.argv[1:] = []
    
    unittest.main(defaultTest='titan_client_suite')

########NEW FILE########
__FILENAME__ = index_tests
# -*- coding: utf-8 -*-
#
# Copyright 2011 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
import unittest

from bulbs.tests.testcase import BulbsTestCase
from bulbs.element import Vertex, VertexProxy, Edge, EdgeProxy
from bulbs.config import Config
    
from bulbs.rexster import RexsterClient, REXSTER_URI
from bulbs.rexster.index import VertexIndexProxy, EdgeIndexProxy, ManualIndex

config = Config(REXSTER_URI)
BulbsTestCase.client = RexsterClient(config)
BulbsTestCase.index_class = ManualIndex

 
class IndexTestCase(BulbsTestCase):
    
    def setUp(self):
        self.indicesV = VertexIndexProxy(self.index_class,self.client)
        self.indicesE = EdgeIndexProxy(self.index_class,self.client)

        self.indicesV.delete("test_idxV")
        self.indicesE.delete("test_idxE")

        self.vertices = VertexProxy(Vertex,self.client)
        self.vertices.index = self.indicesV.get_or_create("test_idxV")

        self.edges = EdgeProxy(Edge,self.client)
        self.edges.index = self.indicesE.get_or_create("test_idxE")

    def test_index(self):
        index_name = "test_idxV"
        # need to fix this to accept actual data types in POST
        #ikeys = '[name,location]'
        #self.indices.delete(index_name)
        #i1 = self.indices.create(index_name,Vertex)
        #assert i1.index_name == index_name
        #assert i1.index_type == "automatic"

        james = self.vertices.create({'name':'James'})
        self.vertices.index.put(james._id,'name','James')
        self.vertices.index.put(james._id,'location','Dallas')
        results = self.vertices.index.lookup('name','James')
        results = list(results)
        #print "RESULTS", results
        assert len(results) == 1
        assert results[0].name == "James"
        total_size = self.vertices.index.count('name','James')
        assert total_size == 1
        # NOTE: only automatic indices have user provided keys
        #keys = self.vertices.index..keys()
        #assert 'name' in keys
        #assert 'location' in keys
        i2 = self.indicesV.get(index_name)
        #print "INDEX_NAME", index_name, self.vertices.index..index_name, i2.index_name
        assert self.vertices.index.index_name == i2.index_name
        
        # remove vertex is bugged
        #self.vertices.index..remove(james._id,'name','James')
        #james = self.vertices.index..get_unique('name','James')
        #assert james is None
  
        # only can rebuild automatic indices
        #i3 = self.indices.get("vertices",Vertex)
        #results = i3.rebuild()
        #assert type(results) == list

        self.indicesV.delete(index_name)

        
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(IndexTestCase))

    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')


########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
#
# Copyright 2012 James Thornton (http://jamesthornton.com)
# BSD License (see LICENSE for details)
#
import os
import sys
import inspect
import logging
import numbers
import codecs

import six  # Python 3
import time
import datetime
import calendar
import omnijson as json # supports Python 2.5-3.2


#
# Python 3 
#

if sys.version < '3':
#    import ujson as json
    from urllib import quote, quote_plus, urlencode
    from urlparse import urlsplit, urlparse

    # def u(x):
    #     if isinstance(x, str):
    #         return x.decode('utf-8')
    #     return x.encode('utf-8').decode('utf-8')
                        
else:
    # ujson is faster but hasn't been ported to Python 3 yet
#    import json
    from urllib.parse import quote, quote_plus, urlencode, urlparse
    from urllib.parse import urlsplit

    long = int
    unicode = str

    # def u(x):
    #     return x.encode('utf-8').decode('utf-8')
         
         

# NOTE: now using the same unicode func for both Python 2 and Python 3
# http://stackoverflow.com/questions/6625782/unicode-literals-that-work-in-python-3-and-2
# Unicode - see Armin's http://lucumr.pocoo.org/2013/7/2/the-updated-guide-to-unicode/
def u(x):
    byte_string, length = codecs.unicode_escape_encode(x)
    unicode_string, length = codecs.unicode_escape_decode(byte_string)
    return unicode_string



#
# Logging
#

bulbs_logger = logging.getLogger('bulbs')

def get_logger(name, level=None):
    #logger = logging.getLogger(name)
    logger = bulbs_logger.getChild(name)
    if level:
        logger.setLevel(level)
    return logger

log = get_logger(__name__)

#
# Element Utils
#


def initialize_elements(client,response):
    # return None if there were no results; otherwise,
    # return a generator of initialized elements.
    if response.total_size > 0:
        # yield doesn't work for conditionals
        return (initialize_element(client, result) for result in response.results)

def initialize_element(client,result):
    # result should be a single Result object, not a list or generator
    element_class = get_element_class(client,result)
    element = element_class(client)
    element._initialize(result)
    return element

def get_element_class(client,result):
    element_key = get_element_key(client,result)
    element_class = client.registry.get_class(element_key)
    if element_class is None:
        # if element_class is not in registry, return the generic Vertex/Edge class
        base_type = result.get_type()
        element_class = client.registry.get_class(base_type)
    return element_class

def get_element_key(client,result):
    var_map = dict(vertex=client.config.type_var,
                   edge=client.config.label_var)
    base_type = result.get_type()
    if base_type == "vertex":
        key_var = var_map[base_type]
        # if key_var not found, just return the generic type for the Vertex
        element_key = result.data.get(key_var, base_type)
    elif base_type == "edge":
        label = result.get_label()
        element_key = label if label in client.registry.class_map else base_type
    else:
        raise TypeError
    return element_key

# Deprecated in favor of resp.one()
def get_one_result(resp):
    # If you're using this utility, that means the results attribute in the 
    # Response object should always contain a single result object,
    # not multiple items. But gremlin returns all results as a list
    # even if the list contains only one element. And the Response class
    # converts all lists to a generator of Result objects. Thus in that case,
    # we need to grab the single Result object out of the list/generator.
    if resp.total_size > 1:
        log.error('resp.results contains more than one item.')
        raise ValueError
    if inspect.isgenerator(resp.results):
        result = next(resp.results)
    else:
        result = resp.results
    return result
    

def get_key_value(key, value, pair):
    """Return the key and value, regardless of how it was entered."""
    if pair:
        key, value = pair.popitem()
    return key, value


#
# Client Utils
#


def build_path(*args):
    # don't include segment if it's None
    # quote_plus doesn't work for neo4j index lookups;
    # for example, this won't work: index/node/test_idxV/name/James+Thornton
    segments = [quote(to_bytes(segment), safe='') for segment in args if segment is not None]
    path = "/".join(segments)
    return path

def to_bytes(value):
    # urllib does not handle Unicode at all. 
    # URLs don't contain non-ASCII characters, by definition. 
    # When you're dealing with urllib you should use only byte strings. 
    # http://stackoverflow.com/a/5605354/161085
    string_value = to_string(value)             # may have been numeric
    unicode_value = u(string_value)             # ensure unicode
    byte_string = unicode_value.encode('utf8')  # encode as utf8 bytestring
    return byte_string

def to_string(value):
    # maybe convert a number to a string
    return value if not isinstance(value, numbers.Number) else str(value)
   
def encode_value(value):
    return value.encode('utf-8') if isinstance(value, str) else value

def is_string(value):
    return isinstance(value, six.string_types)

def encode_dict(d):
    for key in d:
        val = d.pop(key)
        #key = encode_value(key)
        #d[key] = encode_value(val)
        key = to_bytes(key) if is_string(key) else key
        d[key] = to_bytes(val) if is_string(val) else val
    return d
        


#
# Time Utils
#

def current_timestamp():
    # Return the unix UTC time 
    # TODO: should we cast this to an int for consistency?
    return int(time.time())

def current_datetime():
    # Returns a UTC datetime object
    # return datetime.datetime.utcnow()
    now =  current_timestamp()
    #return datetime.datetime.utcfromtimestamp(now).replace(tzinfo=pytz.utc)
    return datetime.datetime.utcfromtimestamp(now)

def current_date():
    #Return  a date object
    return to_date(current_timestamp())
    
def to_timestamp(datetime):
    # Converts a datetime object to unix UTC time
    return calendar.timegm(datetime.utctimetuple()) 

def to_datestamp(date):
    # Converts a date object to unix UTC time
    return calendar.timegm(date.timetuple()) 

def to_datetime(timestamp):
    # Converts unix UTC time into a UTC datetime object
    #return datetime.datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)
    return datetime.datetime.utcfromtimestamp(timestamp)

def to_date(timestamp):
    # Converts unix UTC time into a date object
    return datetime.date.fromtimestamp(timestamp)
    
# Exaplanations on dealing with time...

    # http://unix4lyfe.org/time/
    # http://lucumr.pocoo.org/2011/7/15/eppur-si-muove/
    # http://nvie.com/posts/introducing-times/
    # http://news.ycombinator.com/item?id=3545935
    # http://labix.org/python-dateutil
    # http://docs.python.org/library/time.html#module-time
    # http://code.davidjanes.com/blog/2008/12/22/working-with-dates-times-and-timezones-in-python/

    # for historical dates, see:
    # http://www.egenix.com/products/python/mxBase/mxDateTime/

    # Always store UTC

    # One way (I think dateutils requires this)
    # t = time.time()  # unix utc timestamp
    # dt = datetime.datetime.utcfromtimestamp(t) 
    # ut = calendar.timegm(dt.utctimetuple()) 

    # Simpler way?
    # t = time.time()  # unix utc timestamp
    # dt = time.gmtime(t)
    # t = calendar.timegm(dt)

    # Both ways lose subsecond precision going from datetime object to unixtime    
    # t = time.mktime(dt)  # back to unix timestamp # don't use this, this is the inverse of localtime()



#
# Generic utils
#

def extract(desired_keys, bigdict):
    subset = dict([(i, bigdict[i]) for i in desired_keys if i in bigdict])
    return subset

def get_file_path(current_filename, target_filename):
    """
    Returns the full file path for the target file.
    
    """
    current_dir = os.path.dirname(current_filename)
    file_path = os.path.normpath(os.path.join(current_dir, target_filename))
    return file_path

def coerce_id(_id):
    """
    Tries to coerce a vertex ID into an integer and returns it.

    :param v: The vertex ID we want to coerce into an integer.
    :type v: int or str

    :rtype: int or str

    """
    try:
        return int(_id)
    except:
        # some DBs, such as OrientDB, use string IDs
        return _id





########NEW FILE########
__FILENAME__ = yaml
import os
import io
import yaml 
from string import Template
from .utils import get_file_path

# You only need this for Gremlin scripts if the server doesn't implement param 
# bindings; otherwise, use groovy.py with gremlin.groovy -- it's several 
# hunderd times faster. Cypher is handled differently on the server side so 
# there there is no performance issue.

class Yaml(object):
    """Load Gremlin or Cypher YAML templates from a .yaml source file."""

    def __init__(self,file_name=None):
        self.file_name = self._get_file_name(file_name)
        self.templates = self._get_templates(self.file_name)

    def get(self,name,params={}):
        """Return a Gremlin script or Cypher query, generated from the params."""
        template = self.templates.get(name)
        #params = self._quote_params(params)
        return template.substitute(params)

    def update(self,file_name):
        new_templates = self._get_templates(file_name)
        self.templates.update(new_templates)
        
    def refresh(self):
        """Refresh the stored templates from the YAML source."""
        self.templates = self._get_templates()

    def _get_file_name(self,file_name):
        if file_name is None:
            dir_name = os.path.dirname(__file__)
            file_name = get_file_path(dir_name,"gremlin.yaml")
        return file_name

    def _get_templates(self,file_name):
        templates = dict()
        with io.open(file_name, encoding='utf-8') as f:
            yaml_map = yaml.load(f)    
            for name in yaml_map: # Python 3
                template = yaml_map[name] 
                templates[name] = Template(template)
        return templates

    #def _quote_params(self,params):
    #    quoted_tuple = map(self._quote,params.items())
    #    params = dict(quoted_tuple)
    #    return params

    #def _quote(self,pair):
    #    key, value = pair
    #    if type(value) == str:
    #        value = "'%s'" % value
    #    elif value is None:
    #        value = ""
    #    return key, value

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Bulbflow documentation build configuration file, created by
# sphinx-quickstart on Thu Jul  7 02:02:14 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "_ext")))
sys.path.append(os.path.abspath('_ext'))


# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.viewcode','bulbsdoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Bulbflow'
copyright = u'2011, James Thornton'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'bulbflow'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_theme']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Bulbflowdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Bulbflow.tex', u'Bulbflow Documentation',
   u'James Thornton', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bulbflow', u'Bulbflow Documentation',
     [u'James Thornton'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

autodoc_member_order = 'bysource'

########NEW FILE########
__FILENAME__ = download
>>> from bulbs import graph
>>> g = graph.Graph()


########NEW FILE########
__FILENAME__ = gremlin-traversal

def hackers(start_node):
    script = "g.v(%s).outE('knows').inV.loop(2).outE('coded_by').inV" % (start_node) 
    return Gremlin().query(script)

# Usage:
for hacker_node in hackers(traversal_start_node):
    # do stuff with hacker_node

########NEW FILE########
__FILENAME__ = idea
from bulbs.model import Node
from bulbs.property import String
        
class Idea(Node):

    element_type = "idea"

    text = String(nullable=False)
    stub = String("make_stub")

    def make_stub(self):
        return utils.create_stub(self.text)
           
    def after_created(self):
        Relationship.create(self,"created_by",current_user)


########NEW FILE########
__FILENAME__ = minimal
from 

########NEW FILE########
__FILENAME__ = neo4j-traversal
class Hackers(neo4j.Traversal):
    types = [
        neo4j.Outgoing.knows,
        neo4j.Outgoing.coded_by,
        ]
    order = neo4j.DEPTH_FIRST
    stop = neo4j.STOP_AT_END_OF_GRAPH

    def isReturnable(self, position):
        return (not position.is_start
                and position.last_relationship.type == 'coded_by')

# Usage:
for hacker_node in Hackers(traversal_start_node):
    # do stuff with hacker_node

########NEW FILE########
__FILENAME__ = person
from bulbs.graph import Graph
from bulbs.element import  Vertex
from bulbs.datatype import Property, Integer, String
        
class Person(Vertex):

    element_type = "person"

    name = Property(String, nullable=False)
    age  = Property(Integer)

    def __init__(self,element=None,eid=None,**kwds):
        self.initialize(element,eid,kwds)

james = Person(name="James", age=34)
julie = Person(name="Julie", age=28)

Graph().edges.create(james,"knows",julie)



########NEW FILE########
__FILENAME__ = bulbflow
# Import Docutils document tree nodes module.
#from docutils import nodes
# Import Directive base class.
from sphinx.util.compat import Directive
#from docutils.parsers.rst import Directive

def setup(app):
    app.add_directive("social", Social)

class Social(Directive):

    def run(self):
        filename = "%s/social.html"
        full_path = os.path.join(os.path.dirname(__file__), "../templates", filename)
        html = open(full_path, 'r').read()
        return "HELLO"


########NEW FILE########
__FILENAME__ = bulbsdoc
# Import Docutils document tree nodes module.
#from docutils import nodes
# Import Directive base class.
#from sphinx.util.compat import Directive
from docutils import nodes

from docutils.parsers.rst import Directive
import os

def setup(app):
    app.add_directive("snippet", Snippet)

#class social(nodes.General, nodes.Element):
#    pass

TEMPLATES = "/home/james/projects/bulbflow.com/www/root/templates"

class Snippet(Directive):

    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = False

    #def run(self):
    #    name = self.arguments[0]
    #    filename = "%s.html" % name
    #    full_path = os.path.join(os.path.dirname(__file__), "../../../templates", filename)
    #    snippet = open(full_path, 'r').read()
    #    return [nodes.raw(text=snippet, format='html')]

    def _social(self):
        name = self.arguments[0]
        filename = "%s.html" % name
        full_path = os.path.join(os.path.dirname(__file__), TEMPLATES, filename)
        snippet = open(full_path, 'r').read()
        return [nodes.raw(text=snippet, format='html')]

    def _comments(self):
        name = self.arguments[0]
        path = self.arguments[1]
        filename = "%s.html" % name
        full_path = os.path.join(os.path.dirname(__file__), TEMPLATES, filename)
        snippet = open(full_path, 'r').read()
        snippet = snippet.format(path=path)
        return [nodes.raw(text=snippet, format='html')]

    def run(self):
        snippet_map = dict(social=self._social,
                           comments=self._comments)
        name = str(self.arguments[0])
        snippet_func = snippet_map[name]
        return snippet_func()

########NEW FILE########
__FILENAME__ = something
# Import Docutils document tree nodes module.
#from docutils import nodes
# Import Directive base class.
#from sphinx.util.compat import Directive
from docutils import nodes

from docutils.parsers.rst import Directive
import os

def setup(app):
    app.add_directive("snippet", Snippet)

#class social(nodes.General, nodes.Element):
#    pass

class Snippet(Directive):

    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = False

    def _social(self):
        name = self.arguments[0]
        filename = "%s.html" % name
        full_path = os.path.join(os.path.dirname(__file__), "../../../templates", filename)
        snippet = open(full_path, 'r').read()
        return [nodes.raw(text=snippet, format='html')]

    def _comments(self):
        pass

    def run(self):
        snippet_map = dict(social=_social,comments=_comments)
        name = self.arguments[0]
        snippet_func = snippet_map[name]
        return snippet_func()

########NEW FILE########
__FILENAME__ = make-release
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    make-release
    ~~~~~~~~~~~~

    Helper script that performs a release.  Does pretty much everything
    automatically for us.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import sys
import os
import re
from datetime import datetime, date
from subprocess import Popen, PIPE


def parse_changelog():
    with open('CHANGES') as f:
        lineiter = iter(f)
        for line in lineiter:
            match = re.search('^Version\s+(.*)', line.strip())
            if match is None:
                continue
            length = len(match.group(1))
            version = match.group(1).strip()
            if lineiter.next().count('-') != len(match.group(0)):
                continue
            while 1:
                change_info = lineiter.next().strip()
                if change_info:
                    break
            match = re.search(r'released on (\w+\s+\d+\s+\d+)'
                              r'(?:, codename (.*))?(?i)', change_info)

            if match is None:
                continue
            datestr, codename = match.groups()
            return version, parse_date(datestr), codename


def bump_version(version):
    try:
        parts = map(int, version.split('.'))
    except ValueError:
        fail('Current version is not numeric')
    parts[-1] += 1
    return '.'.join(map(str, parts))


def parse_date(string):
    #string = string.replace('th ', ' ').replace('nd ', ' ') \
    #               .replace('rd ', ' ').replace('st ', ' ')
    return datetime.strptime(string, '%B %d %Y')


def set_filename_version(filename, version_number, pattern):
    changed = []
    def inject_version(match):
        before, old, after = match.groups()
        changed.append(True)
        return before + version_number + after
    with open(filename) as f:
        contents = re.sub(r"^(\s*%s\s*=\s*')(.+?)(')(?sm)" % pattern,
                          inject_version, f.read())

    if not changed:
        fail('Could not find %s in %s', pattern, filename)

    with open(filename, 'w') as f:
        f.write(contents)

def set_init_version(version):
    info('Setting __init__.py version to %s', version)
    set_filename_version('bulbs/__init__.py', version, '__version__')


def set_setup_version(version):
    info('Setting setup.py version to %s', version)
    set_filename_version('setup.py', version, 'version')


def build_and_upload():
    Popen([sys.executable, 'setup.py', 'release', 'sdist', 'upload']).wait()


def fail(message, *args):
    print >> sys.stderr, 'Error:', message % args
    sys.exit(1)


def info(message, *args):
    print >> sys.stderr, message % args


def get_git_tags():
    return set(Popen(['git', 'tag'], stdout=PIPE).communicate()[0].splitlines())


def git_is_clean():
    return Popen(['git', 'diff', '--quiet']).wait() == 0


def make_git_commit(message, *args):
    message = message % args
    Popen(['git', 'commit', '-am', message]).wait()


def make_git_tag(tag):
    info('Tagging "%s"', tag)
    Popen(['git', 'tag', tag]).wait()


def main():
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))

    rv = parse_changelog()
    if rv is None:
        fail('Could not parse changelog')

    version, release_date, codename = rv
    #dev_version = bump_version(version) + '-dev'
    dev_version = bump_version(version)


    info('Releasing %s (codename %s, release date %s)',
         version, codename, release_date.strftime('%d/%m/%Y'))
    tags = get_git_tags()

    if version in tags:
        fail('Version "%s" is already tagged', version)
    if release_date.date() != date.today():
        print release_date.date()
        fail('Release date is not today (%s != %s)')

    if not git_is_clean():
        fail('You have uncommitted changes in git')

    set_init_version(version)
    set_setup_version(version)
    make_git_commit('Bump version number to %s', version)
    make_git_tag(version)
    build_and_upload()
    set_init_version(dev_version)
    set_setup_version(dev_version)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = bulbs_tests
import unittest

from bulbs.rexster.tests.bulbs_tests import test_suite as rexster_bulbs_suite
from bulbs.rexster.tests.client_tests import rexster_client_suite

from bulbs.neo4jserver.tests.bulbs_tests import test_suite as neo4j_bulbs_suite
from bulbs.neo4jserver.tests.client_tests import neo4j_client_suite

from bulbs.titan.tests.bulbs_tests import test_suite as titan_bulbs_suite
from bulbs.titan.tests.client_tests import titan_client_suite


def suite():
    # This requires Neo4j Server and Rexster are running.
    
    suite = unittest.TestSuite()

    suite.addTest(rexster_client_suite())
    suite.addTest(rexster_bulbs_suite())

    suite.addTest(neo4j_client_suite()) 
    suite.addTest(neo4j_bulbs_suite())

    suite.addTest(titan_client_suite()) 
    suite.addTest(titan_bulbs_suite())
 
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

    




########NEW FILE########
