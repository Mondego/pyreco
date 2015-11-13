__FILENAME__ = cardinality
from .relationship_manager import RelationshipManager, ZeroOrMore # noqa


class ZeroOrOne(RelationshipManager):
    description = "zero or one relationship"

    def single(self):
        nodes = super(ZeroOrOne, self).all()
        if len(nodes) == 1:
            return nodes[0]
        if len(nodes) > 1:
            raise CardinalityViolation(self, len(nodes))

    def all(self):
        node = self.single()
        return [node] if node else []

    def connect(self, obj, properties=None):
        if len(self):
            raise AttemptedCardinalityViolation(
                    "Node already has {0} can't connect more".format(self))
        else:
            return super(ZeroOrOne, self).connect(obj, properties)


class OneOrMore(RelationshipManager):
    description = "one or more relationships"

    def single(self):
        nodes = super(OneOrMore, self).all()
        if nodes:
            return nodes[0]
        raise CardinalityViolation(self, 'none')

    def all(self):
        nodes = super(OneOrMore, self).all()
        if nodes:
            return nodes
        raise CardinalityViolation(self, 'none')

    def disconnect(self, obj):
        if super(OneOrMore, self).__len__() < 2:
            raise AttemptedCardinalityViolation("One or more expected")
        return super(OneOrMore, self).disconnect(obj)


class One(RelationshipManager):
    description = "one relationship"

    def single(self):
        nodes = super(One, self).all()
        if nodes:
            if len(nodes) == 1:
                return nodes[0]
            else:
                raise CardinalityViolation(self, len(nodes))
        else:
            raise CardinalityViolation(self, 'none')

    def all(self):
        return [self.single()]

    def disconnect(self, obj):
        raise AttemptedCardinalityViolation("Cardinality one, cannot disconnect use reconnect")

    def connect(self, obj, properties=None):
        if self.origin.__node__ is None:
            raise Exception("Node has not been saved cannot connect!")
        if len(self):
            raise AttemptedCardinalityViolation("Node already has one relationship")
        else:
            return super(One, self).connect(obj, properties)


class AttemptedCardinalityViolation(Exception):
    pass


class CardinalityViolation(Exception):
    def __init__(self, rel_manager, actual):
        self.rel_manager = str(rel_manager)
        self.actual = str(actual)

    def __str__(self):
        return "CardinalityViolation: Expected {0} got {1}".format(self.rel_manager, self.actual)

########NEW FILE########
__FILENAME__ = hierarchical
from ..core import StructuredNode


class Hierarchical(object):
    """ The Hierarchical mixin provides parent-child context for
        StructuredNodes. On construction of a new object, the `__parent__`
        argument should contain another `StructuredNode` and is used to
        build a relationship `(P)-[R:T]->(C)` with the following parameters:

        - `P` - parent node
        - `C` - child node (this StructuredNode instance)
        - `R` - the parent->child relationship with `__child__` set to `True`
        - `T` - the relationship type determined by the class of this node

        This mixin can therefore be used as follows::

            class Country(Hierarchical, StructuredNode):
                code = StringProperty(unique_index=True)
                name = StringProperty()

            class Nationality(Hierarchical, StructuredNode):
                code = StringProperty(unique_index=True)
                name = StringProperty()

            cy = Country(code="CY", name="Cyprus").save()
            greek_cypriot = Nationality(__parent__=cy, code="CY-GR", name="Greek Cypriot").save()

        The code above will create relationships thus:

            (CY {"code":"CY","name":"Cyprus"})
            (CY_GR {"code":"CY-GR","name":"Greek Cypriot"})
            (CY)-[:NATIONALITY {"__child__":True}]->(CY_GR)

        Note also that the `Hierarchical` constructor registers a
        post_create_hook with the instance which allows this relationship
        to be created.

        :ivar __parent__: parent object according to defined hierarchy
    """

    def __init__(self, *args, **kwargs):
        try:
            super(Hierarchical, self).__init__(*args, **kwargs)
        except TypeError:
            super(Hierarchical, self).__init__()
        self.__parent__ = None
        for key, value in kwargs.items():
            if key == "__parent__":
                self.__parent__ = value

    def post_create(self):
        """ Called by StructuredNode class on creation of new instance. Will
            build relationship from parent to child (this) node.
        """
        if self.__parent__ and isinstance(self, StructuredNode):
            self.client.create(
                (self.__parent__.__node__, self.relationship_type(), self.__node__, {"__child__": True})
            )

    def parent(self):
        return self.__parent__

    def children(self, cls):
        if isinstance(self, StructuredNode):
            child_nodes = [
                rel.end_node
                for rel in self.__node__.match_outgoing(cls.relationship_type())
                if rel["__child__"]
            ]
            return [cls.inflate(node) for node in child_nodes]
        else:
            return []

########NEW FILE########
__FILENAME__ = localisation
from .. import RelationshipTo, StructuredNode, StringProperty
from ..core import NodeIndexManager


class Locale(StructuredNode):
    code = StringProperty(unique_index=True)
    name = StringProperty()

    def __repr__(self):
        return self.code

    def __str__(self):
        return self.code

    @classmethod
    def get(cls, code):
        return Locale.index.get(code=code)


class LocalisedIndexManager(NodeIndexManager):
    """ Only return results in current locale """
    def __init__(self, locale_code, *args, **kwargs):
        super(LocalisedIndexManager, self).__init__(*args, **kwargs)
        self.locale_code = locale_code

    def _execute(self, query):
        locale = Locale.get(self.locale_code)
        cquery = """
            START lang = node({self}),
            lnode = node:%s({query})
            MATCH (lnode)-[:LANGUAGE]->(lang)
            RETURN lnode
            """ % (self.name)  # set index name
        result, meta = locale.cypher(cquery, {'query': query})
        return [row[0] for row in result] if result else []


class Localised(object):
    locales = RelationshipTo("Locale", "LANGUAGE")

    def __init__(self, *args, **kwargs):
        try:
            super(Localised, self).__init__(*args, **kwargs)
        except TypeError:
            super(Localised, self).__init__()

    def add_locale(self, lang):
        if not isinstance(lang, StructuredNode):
            lang = Locale.get(lang)
        self.locales.connect(lang)

    def remove_locale(self, lang):
        self.locales.disconnect(Locale.get(lang))

    def has_locale(self, lang):
        return self.locales.is_connected(Locale.get(lang))

    @classmethod
    def locale_index(cls, code):
        return LocalisedIndexManager(code, cls, cls.__name__)

########NEW FILE########
__FILENAME__ = semi_structured
from ..core import StructuredNode
from ..properties import Property, AliasProperty


class InflateConflict(Exception):
    def __init__(self, cls, key, value, nid):
        self.cls_name = cls.__name__
        self.property_name = key
        self.value = value
        self.nid = nid

    def __str__(self):
        return """Found conflict with node {0}, has property '{1}' with value '{2}'
            although class {3} already has a property '{1}'""".format(
            self.nid, self.property_name, self.value, self.cls_name)


class DeflateConflict(InflateConflict):
    def __init__(self, cls, key, value, nid):
        self.cls_name = cls.__name__
        self.property_name = key
        self.value = value
        self.nid = nid if nid else '(unsaved)'

    def __str__(self):
        return """Found trying to set property '{1}' with value '{2}' on node {0}
            although class {3} already has a property '{1}'""".format(
            self.nid, self.property_name, self.value, self.cls_name)


class SemiStructuredNode(StructuredNode):
    """
    A base class allowing properties to be stored on a node that aren't specified in it's definition.
    Conflicting properties are avoided through the DeflateConflict exception::

        class Person(SemiStructuredNode):
            name = StringProperty()
            age = IntegerProperty()

            def hello(self):
                print("Hi my names " + self.name)

        tim = Person(name='Tim', age=8, weight=11).save()
        tim.hello = "Hi"
        tim.save() # DeflateConflict
    """
    __abstract_node__ = True

    def __init__(self, *args, **kwargs):
        super(SemiStructuredNode, self).__init__(*args, **kwargs)

    @classmethod
    def inflate(cls, node):
        props = {}
        for key, prop in cls._class_properties().items():
            if (issubclass(prop.__class__, Property)
                    and not isinstance(prop, AliasProperty)):
                if key in node.__metadata__['data']:
                    props[key] = prop.inflate(node.__metadata__['data'][key], node)
                elif prop.has_default:
                    props[key] = prop.default_value()
                else:
                    props[key] = None
        # handle properties not defined on the class
        for free_key in [key for key in node.__metadata__['data'] if key not in props]:
            if hasattr(cls, free_key):
                raise InflateConflict(cls, free_key, node.__metadata__['data'][free_key], node._id)
            props[free_key] = node.__metadata__['data'][free_key]

        snode = cls(**props)
        snode.__node__ = node
        return snode

    @classmethod
    def deflate(cls, node_props, obj=None):
        deflated = super(SemiStructuredNode, cls).deflate(node_props, obj)
        for key in [k for k in node_props if k not in deflated]:
            if hasattr(cls, key):
                raise DeflateConflict(cls, key, deflated[key], obj._id)
        node_props.update(deflated)
        return node_props

########NEW FILE########
__FILENAME__ = core
from py2neo import neo4j
from py2neo.packages.httpstream import SocketError
from py2neo.exceptions import ClientError
from .exception import DoesNotExist, CypherException
from .util import camel_to_upper, CustomBatch, _legacy_conflict_check
from .properties import Property, PropertyManager, AliasProperty
from .relationship_manager import RelationshipManager, OUTGOING
from .traversal import TraversalSet, Query
from .signals import hooks
from .index import NodeIndexManager
import os
import time
import sys
import logging
logger = logging.getLogger(__name__)

if sys.version_info >= (3, 0):
    from urllib.parse import urlparse
else:
    from urlparse import urlparse  # noqa


DATABASE_URL = os.environ.get('NEO4J_REST_URL', 'http://localhost:7474/db/data/')


def connection():
    if hasattr(connection, 'db'):
        return connection.db

    url = DATABASE_URL
    u = urlparse(url)
    if u.netloc.find('@') > -1:
        credentials, host = u.netloc.split('@')
        user, password, = credentials.split(':')
        neo4j.authenticate(host, user, password)
        url = ''.join([u.scheme, '://', host, u.path, u.query])

    try:
        connection.db = neo4j.GraphDatabaseService(url)
    except SocketError as e:
        raise SocketError("Error connecting to {0} - {1}".format(url, e))

    if connection.db.neo4j_version >= (2, 0):
        raise Exception("Support for neo4j 2.0 is in progress but not supported by this release.")
    if connection.db.neo4j_version < (1, 8):
        raise Exception("Versions of neo4j prior to 1.8 are unsupported.")

    return connection.db


def cypher_query(query, params=None):
    if isinstance(query, Query):
        query = query.__str__()

    try:
        cq = neo4j.CypherQuery(connection(), '')
        start = time.clock()
        r = neo4j.CypherResults(cq._cypher._post({'query': query, 'params': params or {}}))
        end = time.clock()
        results = [list(rr.values) for rr in r.data], list(r.columns)
    except ClientError as e:
        raise CypherException(query, params, e.args[0], e.exception, e.stack_trace)

    if os.environ.get('NEOMODEL_CYPHER_DEBUG', False):
        logger.debug("query: " + query + "\nparams: " + repr(params) + "\ntook: %.2gs\n" % (end - start))

    return results


class CypherMixin(object):
    @property
    def client(self):
        return connection()

    def cypher(self, query, params=None):
        self._pre_action_check('cypher')
        assert self.__node__ is not None
        params = params or {}
        params.update({'self': self.__node__._id})
        return cypher_query(query, params)


class StructuredNodeMeta(type):
    def __new__(mcs, name, bases, dct):
        dct.update({'DoesNotExist': type('DoesNotExist', (DoesNotExist,), dct)})
        inst = super(StructuredNodeMeta, mcs).__new__(mcs, name, bases, dct)

        if hasattr(inst, '__abstract_node__'):
            delattr(inst, '__abstract_node__')
        else:
            for key, value in dct.items():
                if issubclass(value.__class__, Property):
                    value.name = key
                    value.owner = inst
                    # support for 'magic' properties
                    if hasattr(value, 'setup') and hasattr(value.setup, '__call__'):
                        value.setup()
            if '__index__' in dct or hasattr(inst, '__index__'):
                name = dct['__index__'] if '__index__' in dct else getattr(inst, '__index__')
            inst.index = NodeIndexManager(inst, name)
        return inst


StructuredNodeBase = StructuredNodeMeta('StructuredNodeBase', (PropertyManager,), {})


class StructuredNode(StructuredNodeBase, CypherMixin):
    """ Base class for nodes requiring declaration of formal structure.

        :ivar __node__: neo4j.Node instance bound to database for this instance
    """

    __abstract_node__ = True

    def __init__(self, *args, **kwargs):
        self.__node__ = None
        super(StructuredNode, self).__init__(*args, **kwargs)

    @classmethod
    def category(cls):
        return category_factory(cls)

    def __eq__(self, other):
        if not isinstance(other, (StructuredNode,)):
            raise TypeError("Cannot compare neomodel node with a {}".format(other.__class__.__name__))
        return self.__node__ == other.__node__

    def __ne__(self, other):
        if not isinstance(other, (StructuredNode,)):
            raise TypeError("Cannot compare neomodel node with a {}".format(other.__class__.__name__))
        return self.__node__ != other.__node__

    @hooks
    def save(self):
        # create or update instance node
        if self.__node__ is not None:
            batch = CustomBatch(connection(), self.index.name, self.__node__._id)
            batch.remove_from_index(neo4j.Node, index=self.index.__index__, entity=self.__node__)
            props = self.deflate(self.__properties__, self.__node__._id)
            batch.set_properties(self.__node__, props)
            self._update_indexes(self.__node__, props, batch)
            batch.submit()
        elif hasattr(self, '_is_deleted') and self._is_deleted:
            raise ValueError("{}.save() attempted on deleted node".format(self.__class__.__name__))
        else:
            self.__node__ = self.create(self.__properties__)[0].__node__
            if hasattr(self, 'post_create'):
                self.post_create()
        return self

    def _pre_action_check(self, action):
        if hasattr(self, '_is_deleted') and self._is_deleted:
            raise ValueError("{}.{}() attempted on deleted node".format(self.__class__.__name__, action))
        if self.__node__ is None:
            raise ValueError("{}.{}() attempted on unsaved node".format(self.__class__.__name__, action))

    @hooks
    def delete(self):
        self._pre_action_check('delete')
        self.index.__index__.remove(entity=self.__node__)  # not sure if this is necessary
        self.cypher("START self=node({self}) MATCH (self)-[r]-() DELETE r, self")
        self.__node__ = None
        self._is_deleted = True
        return True

    def traverse(self, rel_manager, *args):
        self._pre_action_check('traverse')
        return TraversalSet(self).traverse(rel_manager, *args)

    def refresh(self):
        self._pre_action_check('refresh')
        """Reload this object from its node in the database"""
        if self.__node__ is not None:
            msg = 'Node %s does not exist in the database anymore'
            try:
                props = self.inflate(
                    self.client.node(self.__node__._id)).__properties__
                for key, val in props.items():
                    setattr(self, key, val)
            # in case py2neo raises error when actually getting the node
            except ClientError as e:
                if 'not found' in e.args[0].lower():
                    raise self.DoesNotExist(msg % self.__node__._id)
                else:
                    raise e

    @classmethod
    def create(cls, *props):
        category = cls.category()
        batch = CustomBatch(connection(), cls.index.name)
        deflated = [cls.deflate(p) for p in list(props)]
        # build batch
        for p in deflated:
            batch.create(neo4j.Node.abstract(**p))

        for i in range(0, len(deflated)):
            batch.create(neo4j.Relationship.abstract(category.__node__,
                    cls.relationship_type(), i, __instance__=True))
            cls._update_indexes(i, deflated[i], batch)
        results = batch.submit()
        return [cls.inflate(node) for node in results[:len(props)]]

    @classmethod
    def inflate(cls, node):
        props = {}
        for key, prop in cls._class_properties().items():
            if (issubclass(prop.__class__, Property)
                    and not isinstance(prop, AliasProperty)):
                if key in node.__metadata__['data']:
                    props[key] = prop.inflate(node.__metadata__['data'][key], node)
                elif prop.has_default:
                    props[key] = prop.default_value()
                else:
                    props[key] = None

        snode = cls(**props)
        snode.__node__ = node
        return snode

    @classmethod
    def relationship_type(cls):
        return camel_to_upper(cls.__name__)

    @classmethod
    def _update_indexes(cls, node, props, batch):
        # check for conflicts prior to execution
        if batch._graph_db.neo4j_version < (1, 9):
            _legacy_conflict_check(cls, node, props)

        for key, value in props.items():
            if key in cls._class_properties():
                node_property = cls.get_property(key)
                if node_property.unique_index:
                    try:
                        batch.add_to_index_or_fail(neo4j.Node, cls.index.__index__, key, value, node)
                    except NotImplementedError:
                        batch.get_or_add_to_index(neo4j.Node, cls.index.__index__, key, value, node)
                elif node_property.index:
                    batch.add_to_index(neo4j.Node, cls.index.__index__, key, value, node)
        return batch


class CategoryNode(CypherMixin):
    def __init__(self, name):
        self.name = name

    def traverse(self, rel):
        return TraversalSet(self).traverse(rel)

    def _pre_action_check(self, action):
        pass


class InstanceManager(RelationshipManager):
    """Manage 'instance' rel of category nodes"""
    def connect(self, node):
        raise Exception("connect not available from category node")

    def disconnect(self, node):
        raise Exception("disconnect not available from category node")


def category_factory(instance_cls):
    """ Retrieve category node by name """
    name = instance_cls.__name__
    category_index = connection().get_or_create_index(neo4j.Node, 'Category')
    category = CategoryNode(name)
    category.__node__ = category_index.get_or_create('category', name, {'category': name})
    rel_type = camel_to_upper(instance_cls.__name__)
    category.instance = InstanceManager({
        'direction': OUTGOING,
        'relation_type': rel_type,
        'target_map': {rel_type: instance_cls},
    }, category)
    category.instance.name = 'instance'
    return category

########NEW FILE########
__FILENAME__ = exception
class UniqueProperty(ValueError):
    def __init__(self, key, value, index, node='(unsaved)'):
        self.property_name = key
        self.value = value
        self.index_name = index
        self.node = node

    def __str__(self):
        msg = "Value '{0}' of property {1} of node {2} in index {3} is not unique"
        return msg.format(self.value, self.property_name, self.node, self.index_name)


class DataInconsistencyError(ValueError):
    def __init__(self, key, value, index, node='(unsaved)'):
        self.property_name = key
        self.value = value
        self.index_name = index
        self.node = node

    def __str__(self):
        return """DATA INCONSISTENCY ERROR - PLEASE READ.

        Setting value '{0}' for unique property '{1}' in index '{2}' for node {3} failed!

        Neo4j servers before version 1.9.M03 do not support unique index
        enforcement via ?unique=create_or_fail:
        http://docs.neo4j.org/chunked/1.9.M03/rest-api-unique-indexes.html
        Due to this, neomodel checks indexes for uniqueness conflicts prior to
        executing a batch which then updates the node's properties and the index.

        Here lies a race condition that your code has hit, the index value has
        probably been taken in between checking for conflicts and executing the batch,
        the properties in neo4j for node {3} don't match those in the index '{2}'.

        You must resolve this manually. To find the node currently indexed under the given
        key, value pair run the following cypher query:

        START a=node:{2}({1}="{0}") RETURN a;
        """.format(self.value, self.property_name, self.index_name, str(self.node))


class DoesNotExist(Exception):
    pass


class RequiredProperty(Exception):
    def __init__(self, key, cls):
        self.property_name = key
        self.node_class = cls

    def __str__(self):
        return "property '{0}' on objects of class {1}".format(
            self.property_name, self.node_class.__name__)


class CypherException(Exception):
    def __init__(self, query, params, message, jexception, trace):
        self.message = message
        self.java_exception = jexception
        self.java_trace = trace
        self.query = query
        self.query_parameters = params

    def __str__(self):
        trace = "\n    ".join(self.java_trace)
        return "\n{0}: {1}\nQuery: {2}\nParams: {3}\nTrace: {4}\n".format(
            self.java_exception, self.message, self.query, repr(self.query_parameters), trace)


def _obj_to_str(obj):
    if obj is None:
        return "object"
    if obj.__class__.__name__ == 'Node':
        return "node ({0})".format(obj._id)
    else:
        return "relationship ({0})".format(obj._id)


class InflateError(ValueError):
    def __init__(self, key, cls, msg, obj=None):
        self.property_name = key
        self.node_class = cls
        self.msg = msg
        self.obj = _obj_to_str(obj)

    def __str__(self):
        return "Attempting to inflate property '{0}' on {1} of class '{2}': {3}".format(
            self.property_name, self.obj, self.node_class.__name__, self.msg)


class DeflateError(ValueError):
    def __init__(self, key, cls, msg, obj):
        self.property_name = key
        self.node_class = cls
        self.msg = msg
        self.obj = _obj_to_str(obj)

    def __str__(self):
        return "Attempting to deflate property '{0}' on {1} of class '{2}': {3}".format(
            self.property_name, self.obj, self.node_class.__name__, self.msg)


class NoSuchProperty(Exception):
    def __init__(self, key, cls):
        self.property_name = key
        self.node_class = cls

    def __str__(self):
        return "No property '{0}' on object of class '{1}'".format(
            self.property_name, self.node_class.__name__)


class PropertyNotIndexed(Exception):
    pass


class NotConnected(Exception):
    def __init__(self, action, node1, node2):
        self.action = action
        self.node1 = node1
        self.node2 = node2

    def __str__(self):
        msg = "Error preforming '{0}' - ".format(self.action)
        msg += "Node {0} of type '{1}' is not connected to {2} of type '{3}'".format(
            self.node1.__node__._id, self.node1.__class__.__name__,
            self.node2.__node__._id, self.node2.__class__.__name__)
        return msg

########NEW FILE########
__FILENAME__ = index
from lucenequerybuilder import Q
from .exception import PropertyNotIndexed
from .properties import AliasProperty
import functools
from py2neo import neo4j


class NodeIndexManager(object):
    def __init__(self, node_class, index_name):
        self.node_class = node_class
        self.name = index_name

    def _check_params(self, params):
        """checked args are indexed and convert aliases"""
        for key in params.keys():
            prop = self.node_class.get_property(key)
            if not prop.is_indexed:
                raise PropertyNotIndexed(key)
            if isinstance(prop, AliasProperty):
                real_key = prop.aliased_to()
                if real_key in params:
                    msg = "Can't alias {0} to {1} in {2}, key {0} exists."
                    raise Exception(msg.format(key, real_key, repr(params)))
                params[real_key] = params[key]
                del params[key]

    def _execute(self, query):
        return self.__index__.query(query)

    def search(self, query=None, **kwargs):
        """Search nodes using an via index"""
        if not query:
            if not kwargs:
                msg = "No arguments provided.\nUsage: {0}.index.search(key=val)"
                msg += " or (lucene query): {0}.index.search('key:val').\n"
                msg += "To retrieve all nodes use the category node: {0}.category().instance.all()"
                raise ValueError(msg.format(self.node_class.__name__))
            self._check_params(kwargs)
            query = functools.reduce(lambda x, y: x & y, [Q(k, v) for k, v in kwargs.items()])

        return [self.node_class.inflate(n) for n in self._execute(str(query))]

    def get(self, query=None, **kwargs):
        """Load single node from index lookup"""
        if not query and not kwargs:
            msg = "No arguments provided.\nUsage: {0}.index.get(key=val)"
            msg += " or (lucene query): {0}.index.get('key:val')."
            raise ValueError(msg.format(self.node_class.__name__))

        nodes = self.search(query=query, **kwargs)
        if len(nodes) == 1:
            return nodes[0]
        elif len(nodes) > 1:
            raise Exception("Multiple nodes returned from query, expected one")
        else:
            raise self.node_class.DoesNotExist("Can't find node in index matching query")

    @property
    def __index__(self):
        from .core import connection
        return connection().get_or_create_index(neo4j.Node, self.name)

########NEW FILE########
__FILENAME__ = properties
from .exception import InflateError, DeflateError, RequiredProperty, NoSuchProperty
from datetime import datetime, date
from .relationship_manager import RelationshipDefinition, RelationshipManager
import os
import types
import pytz
import json
import sys
import functools
import logging
logger = logging.getLogger(__name__)

if sys.version_info >= (3, 0):
    unicode = lambda x: str(x)


class PropertyManager(object):
    """Common stuff for handling properties in nodes and relationships"""
    def __init__(self, *args, **kwargs):
        for key, val in self._class_properties().items():
            if val.__class__ is RelationshipDefinition:
                self.__dict__[key] = val.build_manager(self, key)
            # handle default values
            elif isinstance(val, (Property,)) and not isinstance(val, (AliasProperty,)):
                if not key in kwargs or kwargs[key] is None:
                    if val.has_default:
                        kwargs[key] = val.default_value()
        for key, value in kwargs.items():
            if not(key.startswith("__") and key.endswith("__")):
                setattr(self, key, value)

    @property
    def __properties__(self):
        node_props = {}
        for key, value in self.__dict__.items():
            if not (key.startswith('_') or value is None
                    or isinstance(value,
                        (types.MethodType, RelationshipManager, AliasProperty,))):
                node_props[key] = value
        return node_props

    @classmethod
    def deflate(cls, obj_props, obj=None):
        """ deflate dict ready to be stored """
        deflated = {}
        for key, prop in cls._class_properties().items():
            if (not isinstance(prop, AliasProperty)
                    and issubclass(prop.__class__, Property)):
                if key in obj_props and obj_props[key] is not None:
                    deflated[key] = prop.deflate(obj_props[key], obj)
                elif prop.has_default:
                    deflated[key] = prop.deflate(prop.default_value(), obj)
                elif prop.required:
                    raise RequiredProperty(key, cls)
        return deflated

    @classmethod
    def get_property(cls, name):
        try:
            neo_property = getattr(cls, name)
        except AttributeError:
            raise NoSuchProperty(name, cls)
        if not issubclass(neo_property.__class__, Property)\
                or not issubclass(neo_property.__class__, AliasProperty):
            NoSuchProperty(name, cls)
        return neo_property

    @classmethod
    def _class_properties(cls):
        # get all dict values for inherited classes
        # reverse is done to keep inheritance order
        props = {}
        for scls in reversed(cls.mro()):
            for key, value in scls.__dict__.items():
                props[key] = value
        return props


def validator(fn):
    fn_name = fn.func_name if hasattr(fn, 'func_name') else fn.__name__
    if fn_name == 'inflate':
        exc_class = InflateError
    elif fn_name == 'deflate':
        exc_class = DeflateError
    else:
        raise Exception("Unknown Property method " + fn_name)

    @functools.wraps(fn)
    def validator(self, value, obj=None):
        try:
            return fn(self, value)
        except Exception as e:
            raise exc_class(self.name, self.owner, str(e), obj)
    return validator


class Property(object):
    def __init__(self, unique_index=False, index=False, required=False, default=None):
        if default and required:
            raise Exception("required and default are mutually exclusive")

        if unique_index and index:
            raise Exception("unique_index and index are mutually exclusive")

        self.required = required
        self.unique_index = unique_index
        self.index = index
        self.default = default
        self.has_default = True if self.default is not None else False

    def default_value(self):
        if self.has_default:
            if hasattr(self.default, '__call__'):
                return self.default()
            else:
                return self.default
        else:
            raise Exception("No default value specified")

    @property
    def is_indexed(self):
        return self.unique_index or self.index


class StringProperty(Property):
    @validator
    def inflate(self, value):
        return unicode(value)

    @validator
    def deflate(self, value):
        return unicode(value)

    def default_value(self):
        return unicode(super(StringProperty, self).default_value())


class IntegerProperty(Property):
    @validator
    def inflate(self, value):
        return int(value)

    @validator
    def deflate(self, value):
        return int(value)

    def default_value(self):
        return int(super(IntegerProperty, self).default_value())


class FloatProperty(Property):
    @validator
    def inflate(self, value):
        return float(value)

    @validator
    def deflate(self, value):
        return float(value)

    def default_value(self):
        return float(super(FloatProperty, self).default_value())


class BooleanProperty(Property):
    @validator
    def inflate(self, value):
        return bool(value)

    @validator
    def deflate(self, value):
        return bool(value)

    def default_value(self):
        return bool(super(BooleanProperty, self).default_value())


class DateProperty(Property):
    @validator
    def inflate(self, value):
        return datetime.strptime(unicode(value), "%Y-%m-%d").date()

    @validator
    def deflate(self, value):
        if not isinstance(value, date):
            msg = 'datetime.date object expected, got {0}'.format(repr(value))
            raise ValueError(msg)
        return value.isoformat()


class DateTimeProperty(Property):
    @validator
    def inflate(self, value):
        try:
            epoch = float(value)
        except ValueError:
            raise ValueError('float or integer expected, got {0} cant inflate to datetime'.format(value))
        return datetime.utcfromtimestamp(epoch).replace(tzinfo=pytz.utc)

    @validator
    def deflate(self, value):
        #: Fixed timestamp strftime following suggestion from
        # http://stackoverflow.com/questions/11743019/convert-python-datetime-to-epoch-with-strftime
        if not isinstance(value, datetime):
            raise ValueError('datetime object expected, got {0}'.format(value))
        if value.tzinfo:
            value = value.astimezone(pytz.utc)
            epoch_date = datetime(1970,1,1,tzinfo=pytz.utc)
        elif os.environ.get('NEOMODEL_FORCE_TIMEZONE', False):
            raise ValueError("Error deflating {} no timezone provided".format(value))
        else:
            logger.warning("No timezone sepecified on datetime object.. will be inflated to UTC")
            epoch_date = datetime(1970,1,1)
        return float((value - epoch_date).total_seconds())


class JSONProperty(Property):
    @validator
    def inflate(self, value):
        return json.loads(value)

    @validator
    def deflate(self, value):
        return json.dumps(value)


class AliasProperty(property, Property):
    def __init__(self, to=None):
        self.target = to
        self.required = False
        self.has_default = False

    def aliased_to(self):
        return self.target

    def __get__(self, obj, cls):
        return getattr(obj, self.aliased_to()) if obj else self

    def __set__(self, obj, value):
        setattr(obj, self.aliased_to(), value)

    @property
    def index(self):
        return getattr(self.owner, self.aliased_to()).index

    @property
    def unique_index(self):
        return getattr(self.owner, self.aliased_to()).unique_index

########NEW FILE########
__FILENAME__ = relationship
from .properties import Property, PropertyManager, AliasProperty


class RelationshipMeta(type):
    def __new__(mcs, name, bases, dct):
        inst = super(RelationshipMeta, mcs).__new__(mcs, name, bases, dct)
        for key, value in dct.items():
            if issubclass(value.__class__, Property):
                value.name = key
                value.owner = inst
                if value.is_indexed:
                    raise NotImplemented("Indexed relationship properties not supported yet")

                # support for 'magic' properties
                if hasattr(value, 'setup') and hasattr(value.setup, '__call__'):
                    value.setup()
        return inst


StructuredRelBase = RelationshipMeta('RelationshipBase', (PropertyManager,), {})


class StructuredRel(StructuredRelBase):
    def __init__(self, *args, **kwargs):
        super(StructuredRel, self).__init__(*args, **kwargs)

    def save(self):
        props = self.deflate(self.__properties__, self.__relationship__)
        self.__relationship__.set_properties(props)
        return self

    def delete(self):
        raise Exception("Can not delete relationships please use 'disconnect'")

    def start_node(self):
        return self._start_node_class.inflate(self.__relationship__.start_node)

    def end_node(self):
        return self._end_node_class.inflate(self.__relationship__.end_node)

    @classmethod
    def inflate(cls, rel):
        props = {}
        for key, prop in cls._class_properties().items():
            if (issubclass(prop.__class__, Property)
                    and not isinstance(prop, AliasProperty)):
                if key in rel.__metadata__['data']:
                    props[key] = prop.inflate(rel.__metadata__['data'][key], obj=rel)
                elif prop.has_default:
                    props[key] = prop.default_value()
                else:
                    props[key] = None
        srel = cls(**props)
        srel.__relationship__ = rel
        return srel

########NEW FILE########
__FILENAME__ = relationship_manager
import sys
import functools
from importlib import import_module
from .exception import DoesNotExist, NotConnected
from .util import camel_to_upper

OUTGOING, INCOMING, EITHER = 1, -1, 0


# check origin node is saved and not deleted
def check_origin(fn):
    fn_name = fn.func_name if hasattr(fn, 'func_name') else fn.__name__

    @functools.wraps(fn)
    def checker(self, *args, **kwargs):
        self.origin._pre_action_check(self.name + '.' + fn_name)
        return fn(self, *args, **kwargs)
    return checker


def rel_helper(**rel):
    if rel['direction'] == OUTGOING:
        stmt = '-[{0}:{1}]->'
    elif rel['direction'] == INCOMING:
        stmt = '<-[{0}:{1}]-'
    else:
        stmt = '-[{0}:{1}]-'
    ident = rel['ident'] if 'ident' in rel else ''
    stmt = stmt.format(ident, rel['relation_type'])
    return "  ({0}){1}({2})".format(rel['lhs'], stmt, rel['rhs'])


class RelationshipManager(object):
    def __init__(self, definition, origin):
        self.direction = definition['direction']
        self.relation_type = definition['relation_type']
        self.target_map = definition['target_map']
        self.definition = definition
        self.origin = origin

    def __str__(self):
        direction = 'either'
        if self.direction == OUTGOING:
            direction = 'a outgoing'
        elif self.direction == INCOMING:
            direction = 'a incoming'

        return "{0} in {1} direction of type {2} on node ({3}) of class '{4}'".format(
            self.description, direction,
            self.relation_type, self.origin.__node__._id, self.origin.__class__.__name__)

    @check_origin
    def __bool__(self):
        return len(self) > 0

    @check_origin
    def __nonzero__(self):
        return len(self) > 0

    @check_origin
    def __len__(self):
        return len(self.origin.traverse(self.name))

    @property
    def client(self):
        return self.origin.client

    @check_origin
    def count(self):
        return self.__len__()

    @check_origin
    def all(self):
        return self.origin.traverse(self.name).run()

    @check_origin
    def get(self, **kwargs):
        result = self.search(**kwargs)
        if len(result) == 1:
            return result[0]
        if kwargs:
            msg = ", ".join(["{}: {}".format(str(k), str(v)) for k, v in kwargs.items()])
        else:
            msg = ""
        if len(result) > 1:
            raise Exception("Multiple items returned, use search?{}".format(msg))
        if not result:
            raise DoesNotExist("No items exist for the specified arguments.{}".format(msg))

    @check_origin
    def search(self, **kwargs):
        t = self.origin.traverse(self.name)
        for field, value in kwargs.items():
            t.where(field, '=', value)
        return t.run()

    @check_origin
    def is_connected(self, obj):
        self._check_node(obj)

        rel = rel_helper(lhs='a', rhs='b', ident='r', **self.definition)
        q = "START a=node({self}), b=node({them}) MATCH" + rel + "RETURN count(r)"
        return bool(self.origin.cypher(q, {'them': obj.__node__._id})[0][0][0])

    def _check_node(self, obj):
        """check for valid target node i.e correct class and is saved"""
        for rel_type, cls in self.target_map.items():
            if obj.__class__ is cls:
                if obj.__node__ is None:
                    raise Exception("Can't preform operation on unsaved node " + repr(obj))
                return

        allowed_cls = ", ".join([(tcls if isinstance(tcls, str) else tcls.__name__)
                                 for tcls, _ in self.target_map.items()])
        raise Exception("Expected node objects of class "
                + allowed_cls + " got " + repr(obj)
                + " see relationship definition in " + self.origin.__class__.__name__)

    @check_origin
    def connect(self, obj, properties=None):
        self._check_node(obj)

        new_rel = rel_helper(lhs='us', rhs='them', ident='r', **self.definition)
        q = "START them=node({them}), us=node({self}) CREATE UNIQUE " + new_rel
        params = {'them': obj.__node__._id}

        # set propeties via rel model
        if self.definition['model']:
            rel_model = self.definition['model']
            rel_instance = rel_model(**properties) if properties else rel_model()

            if self.definition['direction'] == INCOMING:
                rel_instance._start_node_class = obj.__class__
                rel_instance._end_node_class = self.origin.__class__
            else:
                rel_instance._start_node_class = self.origin.__class__
                rel_instance._end_node_class = obj.__class__

            for p, v in rel_model.deflate(rel_instance.__properties__).items():
                params['place_holder_' + p] = v
                q += " SET r." + p + " = {place_holder_" + p + "}"
            rel_instance.__relationship__ = self.origin.cypher(q + " RETURN r", params)[0][0][0]
            return rel_instance

        # OR.. set properties schemaless
        if properties:
            for p, v in properties.items():
                params['place_holder_' + p] = v
                q += " SET r." + p + " = {place_holder_" + p + "}"
        self.origin.cypher(q, params)

    @check_origin
    def relationship(self, obj):
        """relationship: target_node"""
        self._check_node(obj)
        if not 'model' in self.definition:
            raise NotImplemented("'relationship' method only available on relationships"
                    + " that have a model defined")

        rel_model = self.definition['model']

        new_rel = rel_helper(lhs='us', rhs='them', ident='r', **self.definition)
        q = "START them=node({them}), us=node({self}) MATCH " + new_rel + " RETURN r"
        rel = self.origin.cypher(q, {'them': obj.__node__._id})[0][0][0]
        if not rel:
            return
        rel_instance = rel_model.inflate(rel)

        if self.definition['direction'] == INCOMING:
            rel_instance._start_node_class = obj.__class__
            rel_instance._end_node_class = self.origin.__class__
        else:
            rel_instance._start_node_class = self.origin.__class__
            rel_instance._end_node_class = obj.__class__
        return rel_instance

    @check_origin
    def reconnect(self, old_obj, new_obj):
        """reconnect: old_node, new_node"""
        self._check_node(old_obj)
        self._check_node(new_obj)
        if old_obj.__node__._id == new_obj.__node__._id:
            return
        old_rel = rel_helper(lhs='us', rhs='old', ident='r', **self.definition)

        # get list of properties on the existing rel
        result, meta = self.origin.cypher("START us=node({self}), old=node({old}) MATCH " + old_rel + " RETURN r",
            {'old': old_obj.__node__._id})
        if result:
            existing_properties = result[0][0].__metadata__['data'].keys()
        else:
            raise NotConnected('reconnect', self.origin, old_obj)

        # remove old relationship and create new one
        new_rel = rel_helper(lhs='us', rhs='new', ident='r2', **self.definition)
        q = "START us=node({self}), old=node({old}), new=node({new}) MATCH " + old_rel
        q += " CREATE UNIQUE " + new_rel

        # copy over properties if we have
        for p in existing_properties:
            q += " SET r2.{} = r.{}".format(p, p)
        q += " WITH r DELETE r"

        self.origin.cypher(q, {'old': old_obj.__node__._id, 'new': new_obj.__node__._id})

    @check_origin
    def disconnect(self, obj):
        rel = rel_helper(lhs='a', rhs='b', ident='r', **self.definition)
        q = "START a=node({self}), b=node({them}) MATCH " + rel + " DELETE r"
        self.origin.cypher(q, {'them': obj.__node__._id})

    @check_origin
    def single(self):
        nodes = self.origin.traverse(self.name).limit(1).run()
        return nodes[0] if nodes else None


class RelationshipDefinition(object):
    def __init__(self, relation_type, cls_name, direction, manager=RelationshipManager, model=None):
        self.module_name = sys._getframe(4).f_globals['__name__']
        self.module_file = sys._getframe(4).f_globals['__file__']
        self.node_class = cls_name
        self.manager = manager
        self.definition = {}
        self.definition['relation_type'] = relation_type
        self.definition['direction'] = direction
        self.definition['model'] = model

    def _lookup(self, name):
        if name.find('.') == -1:
            module = self.module_name
        else:
            module, _, name = name.rpartition('.')

        if not module in sys.modules:
            # yet another hack to get around python semantics
            # __name__ is the namespace of the parent module for __init__.py files,
            # and the namespace of the current module for other .py files,
            # therefore there's a need to define the namespace differently for
            # these two cases in order for . in relative imports to work correctly
            # (i.e. to mean the same thing for both cases).
            # For example in the comments below, namespace == myapp, always
            if '__init__.py' in self.module_file:
                # e.g. myapp/__init__.py -[__name__]-> myapp
                namespace = self.module_name
            else:
                # e.g. myapp/models.py -[__name__]-> myapp.models
                namespace = self.module_name.rpartition('.')[0]

            # load a module from a namespace (e.g. models from myapp)
            if module:
                module = import_module(module, namespace).__name__
            # load the namespace itself (e.g. myapp)
            # (otherwise it would look like import . from myapp)
            else:
                module = import_module(namespace).__name__
        return getattr(sys.modules[module], name)

    def build_manager(self, origin, name):
        # get classes for target
        if isinstance(self.node_class, list):
            node_classes = [self._lookup(cls) if isinstance(cls, (str,)) else cls
                        for cls in self.node_class]
        else:
            node_classes = [self._lookup(self.node_class)
                if isinstance(self.node_class, (str,)) else self.node_class]

        # build target map
        self.definition['target_map'] = dict(zip([camel_to_upper(c.__name__)
                for c in node_classes], node_classes))
        rel = self.manager(self.definition, origin)
        rel.name = name
        return rel


class ZeroOrMore(RelationshipManager):
    description = "zero or more relationships"


def _relate(cls_name, direction, rel_type, cardinality=None, model=None):
    if not isinstance(cls_name, (str, list, object)):
        raise Exception('Expected class name or list of class names, got ' + repr(cls_name))
    from .relationship import StructuredRel
    if model and not issubclass(model, (StructuredRel,)):
        raise Exception('model of class {} must be a StructuredRel'.format(model.__class__.__name__))
    return RelationshipDefinition(rel_type, cls_name, direction, cardinality, model)


def RelationshipTo(cls_name, rel_type, cardinality=ZeroOrMore, model=None):
    return _relate(cls_name, OUTGOING, rel_type, cardinality, model)


def RelationshipFrom(cls_name, rel_type, cardinality=ZeroOrMore, model=None):
    return _relate(cls_name, INCOMING, rel_type, cardinality, model)


def Relationship(cls_name, rel_type, cardinality=ZeroOrMore, model=None):
    return _relate(cls_name, EITHER, rel_type, cardinality, model)

########NEW FILE########
__FILENAME__ = signals
import os
signals = None
try:
    if not 'DJANGO_SETTINGS_MODULE' in os.environ:
        from django.conf import settings
        settings.configure()
    from django.db.models import signals
    SIGNAL_SUPPORT = True
except ImportError:
    SIGNAL_SUPPORT = False


def exec_hook(hook_name, self, *args, **kwargs):
    if hasattr(self, hook_name):
        getattr(self, hook_name)(*args, **kwargs)
    if signals and hasattr(signals, hook_name):
        sig = getattr(signals, hook_name)
        sig.send(sender=self.__class__, instance=self)


def hooks(fn):
    def hooked(self, *args, **kwargs):
        fn_name = fn.func_name if hasattr(fn, 'func_name') else fn.__name__
        exec_hook('pre_' + fn_name, self, *args, **kwargs)
        val = fn(self, *args, **kwargs)
        exec_hook('post_' + fn_name, self, *args, **kwargs)
        return val
    return hooked

########NEW FILE########
__FILENAME__ = traversal
from .relationship_manager import RelationshipDefinition, rel_helper, INCOMING
from copy import deepcopy
import re


def _deflate_node_value(target_map, prop, value):
    prop = prop.replace('!', '').replace('?', '')
    property_classes = set()
    # find properties on target classes
    for node_cls in target_map.values():
        if hasattr(node_cls, prop):
            property_classes.add(getattr(node_cls, prop).__class__)

    # attempt to deflate
    if len(property_classes) == 1:
        return property_classes.pop()().deflate(value)
    elif len(property_classes) > 1:
        classes = ' or '.join([cls.__name__ for cls in property_classes])
        node_classes = ' or '.join([cls.__name__ for cls in target_map.values()])
        raise ValueError("Unsure how to deflate '" + value + "' conflicting definitions "
                + " for target node classes " + node_classes + ", property could be any of: "
                + classes + " in where()")
    else:
        node_classes = ', '.join([cls.__name__ for cls in target_map.values()])
        raise ValueError("No property '{}' on {} can't deflate '{}' for where()".format(
            prop, node_classes, value))


def last_x_in_ast(ast, x):
    assert isinstance(ast, (list,))
    for node in reversed(ast):
        if x in node:
            return node
    raise IndexError("Could not find {0} in {1}".format(x, ast))


def unique_placeholder(placeholder, query_params):
        i = 0
        new_placeholder = "{}_{}".format(placeholder, i)
        while new_placeholder in query_params:
            i += 1
            new_placeholder = "{}_{}".format(placeholder, i)
        return new_placeholder


class AstBuilder(object):
    """Construct AST for traversal"""
    def __init__(self, start_node):
        self.start_node = start_node
        self.ident_count = 0
        self.query_params = {}
        self.ast = [{'start': '{self}',
            'class': self.start_node.__class__, 'name': 'origin'}]
        self.origin_is_category = start_node.__class__.__name__ == 'CategoryNode'

    def _traverse(self, rel_manager, where_stmts=None):
        if len(self.ast) > 1:
            t = self._find_map(self.ast[-2]['target_map'], rel_manager)
        else:
            if not hasattr(self.start_node, rel_manager):
                    raise AttributeError("{} class has no relationship definition '{}' to traverse.".format(
                        self.start_node.__class__.__name__, rel_manager))
            t = getattr(self.start_node, rel_manager).definition
            t['name'] = rel_manager

        if where_stmts and not 'model' in t:
                raise Exception("Conditions " + repr(where_stmts) + " to traverse "
                        + rel_manager + " not allowed as no model specified on " + rel_manager)
        match, where = self._build_match_ast(t, where_stmts)
        self._add_match(match)
        if where:
            self._add_where(where)
        return self

    def _add_match(self, match):
        if len(self.ast) > 1:
            node = last_x_in_ast(self.ast, 'match')
            for rel in match['match']:
                node['match'].append(rel)
            # replace name and target map
            node['name'] = match['name']
            node['target_map'] = match['target_map']
        else:
            self.ast.append(match)

    def _add_where(self, where):
        if len(self.ast) > 2:
            node = last_x_in_ast(self.ast, 'where')
            for stmt in where:
                node['where'].append(stmt)
        else:
            self.ast.append({'where': where})

    def _create_ident(self):
        # ident generator
        self.ident_count += 1
        return 'r' + str(self.ident_count)

    def _build_match_ast(self, target, where_stmts):
        rel_to_traverse = {
            'lhs': last_x_in_ast(self.ast, 'name')['name'],
            'direction': target['direction'],
            'relation_type': target['relation_type'],
            'ident': self._create_ident(),
            'rhs': target['name'],
        }

        match = {
            'match': [rel_to_traverse],
            'name': target['name'],
            'target_map': target['target_map']
        }

        where_clause = []
        if where_stmts:
            where_clause = self._where_rel(where_stmts, rel_to_traverse['ident'], target['model'])

        # if we aren't category node or already traversed one rel
        if not self.origin_is_category or len(self.ast) > 1:
            category_rel_ident = self._create_ident()
            match['match'].append({
                'lhs': target['name'],
                'direction': INCOMING,
                'ident': category_rel_ident,
                'relation_type': "|".join([rel for rel in target['target_map']]),
                'rhs': ''
            })
            # Add where
            where_clause.append(category_rel_ident + '.__instance__! = true')

        return match, where_clause

    def _find_map(self, target_map, rel_manager):
        targets = []
        # find matching rel definitions
        for rel, cls in target_map.items():
            if hasattr(cls, rel_manager):
                manager = getattr(cls, rel_manager)
                if isinstance(manager, (RelationshipDefinition)):
                    p = manager.definition
                    p['name'] = rel_manager
                    # add to possible targets
                    targets.append(p)

        if not targets:
            t_list = ', '.join([t_cls.__name__ for t_cls, _ in target_map.items()])
            raise AttributeError("No such rel manager {0} on {1}".format(
                rel_manager, t_list))

        # return as list if more than one
        return targets if len(targets) > 1 else targets[0]

    def _where_node(self, ident_prop, op, value):
        if re.search(r'[^\w\?\!\.]', ident_prop):
            raise Exception("Invalid characters in ident allowed: [. \w ! ?]")
        target = last_x_in_ast(self.ast, 'name')
        if not '.' in ident_prop:
            prop = ident_prop
            ident_prop = target['name'] + '.' + ident_prop
        else:
            prop = ident_prop.split('.')[1]
        value = _deflate_node_value(target['target_map'], prop, value)
        return self._where_expr(ident_prop, op, value)

    def _where_rel(self, statements, rel_ident, model):
        stmts = []
        for statement in statements:
            rel_prop = statement[0].replace('!', '').replace('?', '')
            prop = getattr(model, rel_prop)
            if not prop:
                raise AttributeError("RelationshipManager '{}' on {} doesn't have a property '{}' defined".format(
                    rel_ident, self.start_node.__class__.__name__, rel_prop))
            val = prop.__class__().deflate(statement[2])
            stmts.append(self._where_expr(rel_ident + "." + statement[0], statement[1], val))
        return stmts

    def _where_expr(self, ident_prop, op, value):
        if not op in ['>', '<', '=', '<>', '=~']:
            raise Exception("Operator not supported: " + op)
        placeholder = re.sub('[!?]', '', ident_prop.replace('.', '_'))
        placeholder = unique_placeholder(placeholder, self.query_params)
        self.query_params[placeholder] = value
        return " ".join([ident_prop, op, '{' + placeholder + '}'])

    def _add_return(self, ast):
        node = last_x_in_ast(ast, 'name')
        idents = [node['name']]
        if self.ident_count > 0:
            idents.append('r{0}'.format(self.ident_count))
        ast.append({'return': idents})
        if hasattr(self, '_skip'):
            ast.append({'skip': int(self._skip)})
        if hasattr(self, '_limit'):
            ast.append({'limit': int(self._limit)})

    def _add_return_rels(self, ast):
        node = last_x_in_ast(ast, 'name')
        idents = [node['match'][0]['ident']]
        ast.append({'return': idents})
        if hasattr(self, '_skip'):
            ast.append({'skip': int(self._skip)})
        if hasattr(self, '_limit'):
            ast.append({'limit': int(self._limit)})

    def _set_order(self, ident_prop, desc=False):
        if not '.' in ident_prop:
            ident_prop = last_x_in_ast(self.ast, 'name')['name'] + '.' + ident_prop
        rel_manager, prop = ident_prop.split('.')

        # just in case input isn't safe
        assert not (re.search(r'[^\w]', rel_manager) and re.search(r'[^\w]', prop))

        name = last_x_in_ast(self.ast, 'name')['name']
        if name != rel_manager:
            raise ValueError("Last traversal was {0} not {1}".format(name, rel_manager))
        # set order
        if not hasattr(self, 'order_part'):
            self.order_part = {'order': ident_prop, 'desc': desc}
        else:
            raise NotImplemented("Order already set")

    def _add_return_count(self, ast):
        if hasattr(self, '_skip') or hasattr(self, '_limit'):
            raise NotImplemented("Can't use skip or limit with count")
        node = last_x_in_ast(ast, 'name')
        ident = ['count(' + node['name'] + ')']
        node = last_x_in_ast(ast, 'name')
        ast.append({'return': ident})

    def execute(self, ast):
        if hasattr(self, 'order_part'):
            # find suitable place to insert order node
            for i, entry in enumerate(reversed(ast)):
                if not ('limit' in entry or 'skip' in entry):
                    ast.insert(len(ast) - i, self.order_part)
                    break
        results, meta = self.start_node.cypher(Query(ast), self.query_params)
        self.last_ast = ast
        return results

    def execute_and_inflate_nodes(self, ast):
        target_map = last_x_in_ast(ast, 'target_map')['target_map']
        results = self.execute(ast)
        nodes = [row[0] for row in results]
        classes = [target_map[row[1].type] for row in results]
        return [cls.inflate(node) for node, cls in zip(nodes, classes)]


class TraversalSet(AstBuilder):
    """API level methods"""
    def __init__(self, start_node):
        super(TraversalSet, self).__init__(start_node)

    def traverse(self, rel, *where_stmts):
        if self.start_node.__node__ is None:
            raise Exception("Cannot traverse unsaved node")
        self._traverse(rel, where_stmts)
        return self

    def order_by(self, prop):
        self._set_order(prop, desc=False)
        return self

    def order_by_desc(self, prop):
        self._set_order(prop, desc=True)
        return self

    def where(self, ident, op, value):
        expr = self._where_node(ident, op, value)
        self._add_where([expr])
        return self

    def skip(self, count):
        if int(count) < 0:
            raise ValueError("Negative skip value not supported")
        self._skip = int(count)
        return self

    def limit(self, count):
        if int(count) < 0:
            raise ValueError("Negative limit value not supported")
        self._limit = int(count)
        return self

    def run(self):
        ast = deepcopy(self.ast)
        self._add_return(ast)
        return self.execute_and_inflate_nodes(ast)

    def __iter__(self):
        return iter(self.run())

    def __len__(self):
        ast = deepcopy(self.ast)
        self._add_return_count(ast)
        return self.execute(ast)[0][0]

    def __bool__(self):
        return bool(len(self))

    def __nonzero__(self):
        return bool(len(self))


class Query(object):
    def __init__(self, ast):
        self.ast = ast

    def _create_ident(self):
        self.ident_count += 1
        return 'r' + str(self.ident_count)

    def _build(self):
        self.position = 0
        self.ident_count = 0
        self.query = ''
        for entry in self.ast:
            self.query += self._render(entry) + "\n"
            self.position += 1
        return self.query

    def _render(self, entry):
        if 'start' in entry:
            return self._render_start(entry)
        elif 'match' in entry:
            return self._render_match(entry)
        elif 'where' in entry:
            return self._render_where(entry)
        elif 'return' in entry:
            return self._render_return(entry)
        elif 'skip' in entry:
            return self._render_skip(entry)
        elif 'limit' in entry:
            return self._render_limit(entry)
        elif 'order' in entry:
            return self._render_order(entry)

    def _render_start(self, entry):
        return "START origin=node(%s)" % entry['start']

    def _render_return(self, entry):
        return "RETURN " + ', '.join(entry['return'])

    def _render_match(self, entry):
        # add match clause if at start
        stmt = "MATCH\n" if 'start' in self.ast[self.position - 1] else ''
        stmt += ",\n".join([rel_helper(**rel) for rel in entry['match']])
        return stmt

    def _render_where(self, entry):
        expr = ' AND '.join(entry['where'])
        return "WHERE " + expr

    def _render_skip(self, entry):
        return "SKIP {0}".format(entry['skip'])

    def _render_limit(self, entry):
        return "LIMIT {0}".format(entry['limit'])

    def _render_order(self, entry):
        sort = ' DESC' if entry['desc'] else ''
        return "ORDER BY {0}{1}".format(entry['order'], sort)

    def __str__(self):
        return self._build()

########NEW FILE########
__FILENAME__ = util
import re
from py2neo import neo4j
from .exception import UniqueProperty, DataInconsistencyError

camel_to_upper = lambda x: "_".join(word.upper() for word in re.split(r"([A-Z][0-9a-z]*)", x)[1::2])
upper_to_camel = lambda x: "".join(word.title() for word in x.split("_"))

# the default value "true;format=pretty" causes the server to loose individual status codes in batch responses
neo4j._headers[None] = [("X-Stream", "true")]


class CustomBatch(neo4j.WriteBatch):
    def __init__(self, graph, index_name, node='(unsaved)'):
        super(CustomBatch, self).__init__(graph)
        self.index_name = index_name
        self.node = node

    def submit(self):
        responses = self._execute()
        batch_responses = [neo4j.BatchResponse(r) for r in responses.json]
        if self._graph_db.neo4j_version < (1, 9):
            self._legacy_check_for_conflicts(responses, batch_responses, self._requests)
        else:
            self._check_for_conflicts(responses, batch_responses, self._requests)

        try:
            return [r.hydrated for r in batch_responses]
        finally:
            responses.close()

    def _check_for_conflicts(self, responses, batch_responses, requests):
        for i, r in enumerate(batch_responses):
            if r.status_code == 409:
                responses.close()
                raise UniqueProperty(
                        requests[i].body['key'], requests[i].body['key'],
                        self.index_name, self.node)

    def _legacy_check_for_conflicts(self, responses, batch_responses, requests):
        for i, r in enumerate(batch_responses):
            if r.status_code == 200:
                responses.close()
                raise DataInconsistencyError(
                        requests[i].body['key'], requests[i].body['key'],
                        self.index_name, self.node)


def _legacy_conflict_check(cls, node, props):
    """
    prior to the introduction of create_or_fail in 1.9 we check to see if the key
    exists in the index before executing the batch.
    """
    for key, value in props.items():
        if key in cls._class_properties() and cls.get_property(key).unique_index:
            results = cls.index.__index__.get(key, value)
            if len(results):
                if isinstance(node, (int,)):  # node ref
                    raise UniqueProperty(key, value, cls.index.name)
                elif hasattr(node, '_id') and results[0]._id != node._id:
                    raise UniqueProperty(key, value, cls.index.name, node)

########NEW FILE########
__FILENAME__ = test_alias
from neomodel import StructuredNode, StringProperty, AliasProperty


class MagicProperty(AliasProperty):
    def setup(self):
        self.owner.setup_hook_called = True


class AliasTestNode(StructuredNode):
    name = StringProperty(unique_index=True)
    full_name = AliasProperty(to='name')
    long_name = MagicProperty(to='name')


def test_property_setup_hook():
    assert AliasTestNode.setup_hook_called
    tim = AliasTestNode(long_name='tim').save()
    assert tim.name == 'tim'


def test_alias():
    jim = AliasTestNode(full_name='Jim').save()
    assert jim.name == 'Jim'
    assert jim.full_name == 'Jim'
    assert 'full_name' not in AliasTestNode.deflate(jim.__properties__)
    jim = AliasTestNode.index.get(full_name='Jim')
    assert jim
    assert jim.name == 'Jim'
    assert jim.full_name == 'Jim'
    assert 'full_name' not in AliasTestNode.deflate(jim.__properties__)

########NEW FILE########
__FILENAME__ = test_batch
from neomodel import (StructuredNode, StringProperty, IntegerProperty)
from neomodel.exception import UniqueProperty, DeflateError


class Customer(StructuredNode):
    email = StringProperty(unique_index=True, required=True)
    age = IntegerProperty(index=True)


def test_batch_create():
    users = Customer.create(
            {'email': 'jim1@aol.com', 'age': 11},
            {'email': 'jim2@aol.com', 'age': 7},
            {'email': 'jim3@aol.com', 'age': 9},
            {'email': 'jim4@aol.com', 'age': 7},
            {'email': 'jim5@aol.com', 'age': 99},
            )
    assert len(users) == 5
    assert users[0].age == 11
    assert users[1].age == 7
    assert users[1].email == 'jim2@aol.com'
    assert Customer.index.get(email='jim1@aol.com')


def test_batch_validation():
    # test validation in batch create
    try:
        Customer.create(
            {'email': 'jim1@aol.com', 'age': 'x'},
        )
    except DeflateError:
        assert True
    else:
        assert False


def test_batch_index_violation():
    for u in Customer.category().instance.all():
        u.delete()

    users = Customer.create(
        {'email': 'jim6@aol.com', 'age': 3},
    )
    assert users
    try:
        Customer.create(
            {'email': 'jim6@aol.com', 'age': 3},
            {'email': 'jim7@aol.com', 'age': 5},
        )
    except UniqueProperty:
        assert True
    else:
        assert False

    # not in index
    assert not Customer.index.search(email='jim7@aol.com')
    # not found via category
    assert not Customer.category().instance.search(email='jim7@aol.com')

########NEW FILE########
__FILENAME__ = test_cardinality
from neomodel import (StructuredNode, StringProperty, IntegerProperty,
        RelationshipTo, AttemptedCardinalityViolation, CardinalityViolation,
         OneOrMore, ZeroOrMore, ZeroOrOne, One)


class HairDryer(StructuredNode):
    version = IntegerProperty()


class ScrewDriver(StructuredNode):
    version = IntegerProperty()


class Car(StructuredNode):
    version = IntegerProperty()


class Monkey(StructuredNode):
    name = StringProperty()
    dryers = RelationshipTo('HairDryer', 'OWNS_DRYER', cardinality=ZeroOrMore)
    driver = RelationshipTo('ScrewDriver', 'HAS_SCREWDRIVER', cardinality=ZeroOrOne)
    car = RelationshipTo('Car', 'HAS_CAR', cardinality=OneOrMore)
    toothbrush = RelationshipTo('ToothBrush', 'HAS_TOOTHBRUSH', cardinality=One)


class ToothBrush(StructuredNode):
    name = StringProperty()


def test_cardinality_zero_or_more():
    m = Monkey(name='tim').save()
    assert m.dryers.all() == []
    assert m.dryers.single() == None
    h = HairDryer(version=1).save()

    m.dryers.connect(h)
    assert len(m.dryers.all()) == 1
    assert m.dryers.single().version == 1

    m.dryers.disconnect(h)
    assert m.dryers.all() == []
    assert m.dryers.single() == None


def test_cardinality_zero_or_one():
    m = Monkey(name='bob').save()
    assert m.driver.all() == []
    assert m.driver.single() == None
    h = ScrewDriver(version=1).save()

    m.driver.connect(h)
    assert len(m.driver.all()) == 1
    assert m.driver.single().version == 1

    j = ScrewDriver(version=2).save()
    try:
        m.driver.connect(j)
    except AttemptedCardinalityViolation:
        assert True
    else:
        assert False

    m.driver.reconnect(h, j)
    assert m.driver.single().version == 2


def test_cardinality_one_or_more():
    m = Monkey(name='jerry').save()

    try:
        m.car.all()
    except CardinalityViolation:
        assert True
    else:
        assert False

    try:
        m.car.single()
    except CardinalityViolation:
        assert True
    else:
        assert False

    c = Car(version=2).save()
    m.car.connect(c)
    assert m.car.single().version == 2

    try:
        m.car.disconnect(c)
    except AttemptedCardinalityViolation:
        assert True
    else:
        assert False


def test_cardinality_one():
    m = Monkey(name='jerry').save()

    try:
        m.toothbrush.all()
    except CardinalityViolation:
        assert True
    else:
        assert False

    try:
        m.toothbrush.single()
    except CardinalityViolation:
        assert True
    else:
        assert False

    b = ToothBrush(name='Jim').save()
    m.toothbrush.connect(b)
    assert m.toothbrush.single().name == 'Jim'

    x = ToothBrush(name='Jim').save
    try:
        m.toothbrush.connect(x)
    except AttemptedCardinalityViolation:
        assert True
    else:
        assert False

    try:
        m.toothbrush.disconnect(b)
    except AttemptedCardinalityViolation:
        assert True
    else:
        assert False

########NEW FILE########
__FILENAME__ = test_category
from neomodel import StructuredNode, StringProperty


class Giraffe(StructuredNode):
    name = StringProperty()


class Foobar(StructuredNode):
    name = StringProperty()


def test_category_node():
    Giraffe(name='Tim').save()
    Giraffe(name='Tim1').save()
    Giraffe(name='Tim2').save()
    z = Giraffe(name='Tim3').save()

    assert len(Giraffe.category().instance.all()) == 4

    # can't connect on category node
    try:
        Giraffe.category().instance.connect(z)
    except Exception:
        assert True
    else:
        assert False

    # can't disconnect on category node
    try:
        Giraffe.category().instance.disconnect(z)
    except Exception:
        assert True
    else:
        assert False

    results = Giraffe.category().instance.search(name='Tim')
    assert len(results) == 1
    assert results[0].name == 'Tim'


# doesn't bork if no category node
def test_no_category_node():
    assert len(Foobar.category().instance.all()) == 0

########NEW FILE########
__FILENAME__ = test_cypher
from neomodel import StructuredNode, StringProperty, CypherException


class User2(StructuredNode):
    email = StringProperty()


def test_cypher():
    """
    py2neo's cypher result format changed in 1.6 this tests its return value
    is backward compatible with earlier versions of neomodel
    """

    jim = User2(email='jim1@test.com').save()
    data, meta = jim.cypher("START a=node({self}) RETURN a.email")
    assert data[0][0] == 'jim1@test.com'
    assert 'a.email' in meta

    data, meta = jim.cypher("START a=node({self}) MATCH (a)<-[:USER2]-(b) RETURN a, b, 3")
    assert 'a' in meta and 'b' in meta


def test_cypher_syntax_error():
    jim = User2(email='jim1@test.com').save()
    try:
        jim.cypher("START a=node({self}) RETURN xx")
    except CypherException as e:
        assert hasattr(e, 'message')
        assert hasattr(e, 'query')
        assert hasattr(e, 'query_parameters')
        assert hasattr(e, 'java_trace')
        assert hasattr(e, 'java_exception')
    else:
        assert False

########NEW FILE########
__FILENAME__ = test_hierarchical
from neomodel.contrib import Hierarchical
from neomodel import StructuredNode, StringProperty


class CountryNode(Hierarchical, StructuredNode):
    code = StringProperty(unique_index=True)


class Nationality(Hierarchical, StructuredNode):
    code = StringProperty(unique_index=True)


def test_hierarchies():
    gb = CountryNode(code="GB").save()
    cy = CountryNode(code="CY").save()

    british = Nationality(__parent__=gb, code="GB-GB").save()
    greek_cypriot = Nationality(__parent__=cy, code="CY-GR").save()
    turkish_cypriot = Nationality(__parent__=cy, code="CY-TR").save()

    assert british.parent() == gb
    assert greek_cypriot.parent() == cy
    assert turkish_cypriot.parent() == cy
    assert greek_cypriot in cy.children(Nationality)

########NEW FILE########
__FILENAME__ = test_hooks
from neomodel import (StructuredNode, StringProperty)


class PreSaveCalled(Exception):
    pass


class PreSaveHook(StructuredNode):
    name = StringProperty()

    def pre_save(self):
        raise PreSaveCalled


def test_pre_save():
    try:
        PreSaveHook(name='x').save()
    except PreSaveCalled:
        assert True
    else:
        assert False


class PostSaveCalled(Exception):
    pass


class PostSaveHook(StructuredNode):
    name = StringProperty()

    def post_save(self):
        raise PostSaveCalled


def test_post_save():
    try:
        PostSaveHook(name='x').save()
    except PostSaveCalled:
        assert True
    else:
        assert False


class PreDeleteCalled(Exception):
    pass


class PreDeleteHook(StructuredNode):
    name = StringProperty()

    def pre_delete(self):
        raise PreDeleteCalled


def test_pre_delete():
    try:
        PreDeleteHook(name='x').save().delete()
    except PreDeleteCalled:
        assert True
    else:
        assert False


class PostDeleteCalled(Exception):
    pass


class PostDeleteHook(StructuredNode):
    name = StringProperty()

    def post_delete(self):
        raise PostDeleteCalled


def test_post_delete():
    try:
        PostDeleteHook(name='x').save().delete()
    except PostDeleteCalled:
        assert True
    else:
        assert False

########NEW FILE########
__FILENAME__ = test_indexing
from neomodel import StructuredNode, StringProperty, IntegerProperty, UniqueProperty
from lucenequerybuilder import Q


class Human(StructuredNode):
    name = StringProperty(unique_index=True)
    age = IntegerProperty(index=True)


def test_unique_error():
    Human(name="j1m", age=13).save()
    try:
        Human(name="j1m", age=14).save()
    except UniqueProperty as e:
        assert True
        assert str(e).find('j1m')
        assert str(e).find('name')
        assert str(e).find('FooBarr')
    else:
        assert False


def test_optional_properties_dont_get_indexed():
    Human(name=None, age=99).save()
    h = Human.index.get(age=99)
    assert h
    assert h.name is None

    Human(age=98).save()
    h = Human.index.get(age=98)
    assert h
    assert h.name is None


def test_lucene_query():
    Human(name='sarah', age=3).save()
    Human(name='jim', age=4).save()
    Human(name='bob', age=5).save()
    Human(name='tim', age=2).save()

    names = [p.name for p in Human.index.search(Q('age', inrange=[3, 5]))]
    assert 'sarah' in names
    assert 'jim' in names
    assert 'bob' in names


def test_escaped_chars():
    Human(name='sarah:test', age=3).save()
    r = Human.index.search(name='sarah:test')
    assert r
    assert r[0].name == 'sarah:test'


def test_no_args():
    try:
        Human.index.search()
    except ValueError:
        assert True
    else:
        assert False

    try:
        Human.index.search()
    except ValueError:
        assert True
    else:
        assert False


def test_does_not_exist():
    try:
        Human.index.get(name='XXXX')
    except Human.DoesNotExist:
        assert True
    else:
        assert False


def test_index_inherited_props():

    class Mixin(object):
        extra = StringProperty(unique_index=True)

    class MixedHuman(Human, Mixin):
        pass

    jim = MixedHuman(age=23, name='jimmy', extra='extra').save()

    assert MixedHuman.index.name == 'MixedHuman'
    node = MixedHuman.index.get(extra='extra')
    assert node.name == jim.name


def test_custom_index_name():
    class Giraffe(StructuredNode):
        __index__ = 'GiraffeIndex'
        name = StringProperty(unique_index=True)

    jim = Giraffe(name='timothy').save()
    assert Giraffe.index.name == 'GiraffeIndex'
    node = Giraffe.index.get(name='timothy')
    assert node.name == jim.name

    class SpecialGiraffe(Giraffe):
        power = StringProperty()

    # custom indexes shall be inherited
    assert SpecialGiraffe.index.name == 'GiraffeIndex'

########NEW FILE########
__FILENAME__ = test_issue_79
from neomodel import StructuredNode, StringProperty, RelationshipTo, RelationshipFrom


class Cell(StructuredNode):
    next_cell = RelationshipTo('Cell', 'NEXT_CELL') # This can point to multiple
    prev_cell = RelationshipFrom('Cell', 'NEXT_CELL')
    members = RelationshipFrom('CellMember', 'CONTAINED_BY')


class CellMember(StructuredNode):
    containing_cell = RelationshipTo('Cell', 'CONTAINED_BY')
    member_items = RelationshipFrom('MemberItem', 'OWNED_BY')
    member_name = StringProperty(required=True, index=True)


class MemberItem(StructuredNode):
    owning_member = RelationshipTo('CellMember', 'OWNED_BY')
    item_name = StringProperty(required=True, index=True)


def _setup_cell_data():
    cell1 = Cell().save()
    cell2 = Cell().save()
    cell1.next_cell.connect(cell2)
    cell2.next_cell.connect(cell1)

    for name in ['a1', 'a2', 'a3']:
        cell_member = CellMember(member_name=name).save()
        cell2.members.connect(cell_member)
        for item in ['_i1', '_i2', '_i3']:
            mi = MemberItem(item_name=name + item).save()
            cell_member.member_items.connect(mi)

    return cell1


def test_traverse_missing_relation():
    test_cell = _setup_cell_data()
    try:
        test_cell.traverse('next').traverse('members').traverse('member_items').run()
    except AttributeError as e:
        assert "no relationship definition" in str(e)
    else:
        assert False


def test_correct_traversal():
    test_cell = _setup_cell_data()
    results = test_cell.traverse('next_cell').traverse('members').traverse('member_items').run()
    assert len(results) == 9
    for item in results:
        assert isinstance(item, (MemberItem,))

########NEW FILE########
__FILENAME__ = test_issue_87
import neomodel
import py2neo
from neomodel import StructuredNode, StructuredRel, Relationship
from neomodel import StringProperty, DateTimeProperty, IntegerProperty
from datetime import datetime, timedelta
    
twelve_days = timedelta(days=12)
eleven_days = timedelta(days=11)
ten_days    = timedelta(days=10)
nine_days   = timedelta(days=9)
now         = datetime.now()

class FriendRelationship(StructuredRel):
    since = DateTimeProperty(default=datetime.now)
        
class Person(StructuredNode):
    name    = StringProperty()
    age     = IntegerProperty()
    friends = Relationship('Person','friend_of', model=FriendRelationship)
    

def setup_friends(person0, person1, since=None):
    rel = person0.friends.connect(person1)
    if (since):
        rel.since = since
        rel.save()
    return rel.since

def clear_db():
    db = py2neo.neo4j.GraphDatabaseService()
    db.clear()

def test_traversal_single_param():
    clear_db()
    jean  = Person(name="Jean", age=25).save()
    johan = Person(name="Johan", age=19).save()
    chris = Person(name="Chris", age=21).save()
    frank = Person(name="Frank", age=29).save()
    

    setup_friends(jean, johan, now - eleven_days)
    setup_friends(jean, chris, now - nine_days)
    setup_friends(chris, johan, now)
    setup_friends(chris, frank, now - nine_days)
     
    assert len(jean.traverse('friends', ('since','>', now - twelve_days)).run())   ==  2
    assert len(jean.traverse('friends', ('since','>', now - ten_days)).run())      ==  1
    assert len(jean.traverse('friends', ('since','>', now - nine_days)).run())     ==  0

def test_traversal_relationship_filter():
    clear_db()
    jean  = Person(name="Jean", age=25).save()
    johan = Person(name="Johan", age=19).save()
    chris = Person(name="Chris", age=21).save()
    frank = Person(name="Frank", age=29).save()
    
    setup_friends(jean, johan, now - eleven_days)
    setup_friends(jean, chris, now - nine_days)
    setup_friends(chris, johan, now)
    setup_friends(chris, frank, now - nine_days)
    
    assert len(jean.traverse('friends', ('since','>', now - twelve_days), ('since','<', now - ten_days)).run()) ==  1

def test_traversal_node_double_where():
    clear_db()
    jean  = Person(name="Jean", age=25).save()
    johan = Person(name="Johan", age=19).save()
    chris = Person(name="Chris", age=21).save()
    frank = Person(name="Frank", age=29).save()
    
    setup_friends(jean, johan, now - eleven_days)
    setup_friends(jean, chris, now - nine_days)
    setup_friends(chris, johan, now)
    setup_friends(chris, frank, now - nine_days)
    assert len(chris.traverse('friends').where('age','>', 18).where('age','<', 30).run()) ==  3
    assert len(chris.traverse('friends').where('age','>', 18).where('age','<', 29).run()) ==  2

########NEW FILE########
__FILENAME__ = test_localisation
from neomodel import StructuredNode, StringProperty
from neomodel.contrib import Localised, Locale


class Student(Localised, StructuredNode):
    name = StringProperty(unique_index=True)


def setup():
    for l in ['fr', 'ar', 'pl', 'es']:
        Locale(code=l).save()


def test_localised():
    bob = Student(name="Bob").save()
    bob.add_locale(Locale.get("fr"))
    bob.add_locale("ar")
    bob.add_locale(Locale.get("ar"))
    bob.add_locale(Locale.get("pl"))

    assert bob.has_locale("fr")
    assert not bob.has_locale("es")

    bob.remove_locale("fr")
    assert not bob.has_locale("fr")

    assert len(bob.locales) == 2
    assert Locale.get("pl") in bob.locales.all()
    assert Locale.get("ar") in bob.locales.all()


def test_localised_index():
    fred = Student(name="Fred").save()
    jim = Student(name="Jim").save()
    katie = Student(name="Katie").save()

    fred.add_locale(Locale.get('fr'))
    jim.add_locale(Locale.get('fr'))
    katie.add_locale(Locale.get('ar'))

    assert Student.locale_index('fr').get(name='Fred')
    assert len(Student.locale_index('fr').search('name:*')) == 2

    try:
        Student.locale_index('fr').get(name='Katie')
    except Student.DoesNotExist:
        assert True
    else:
        assert False

########NEW FILE########
__FILENAME__ = test_models
from neomodel import (StructuredNode, StringProperty, IntegerProperty)
from neomodel.exception import RequiredProperty, UniqueProperty


class User(StructuredNode):
    email = StringProperty(unique_index=True, required=True)
    age = IntegerProperty(index=True)

    @property
    def email_alias(self):
        return self.email

    @email_alias.setter
    def email_alias(self, value):
        self.email = value


def test_required():
    try:
        User(age=3).save()
    except RequiredProperty:
        assert True
    else:
        assert False


def test_get():
    u = User(email='robin@test.com', age=3)
    assert u.save()
    rob = User.index.get(email='robin@test.com')
    assert rob.email == 'robin@test.com'
    assert rob.age == 3


def test_search():
    assert User(email='robin1@test.com', age=3).save()
    assert User(email='robin2@test.com', age=3).save()
    users = User.index.search(age=3)
    assert len(users)


def test_save_to_model():
    u = User(email='jim@test.com', age=3)
    assert u.save()
    assert u.__node__ is not None
    assert u.email == 'jim@test.com'
    assert u.age == 3


def test_unique():
    User(email='jim1@test.com', age=3).save()
    try:
        User(email='jim1@test.com', age=3).save()
    except Exception as e:
        assert e.__class__.__name__ == 'UniqueProperty'
    else:
        assert False


def test_update_unique():
    u = User(email='jimxx@test.com', age=3).save()
    try:
        u.save() # this shouldn't fail
    except UniqueProperty:
        assert False
    else:
        assert True


def test_update():
    user = User(email='jim2@test.com', age=3).save()
    assert user
    user.email = 'jim2000@test.com'
    user.save()
    jim = User.index.get(email='jim2000@test.com')
    assert jim
    assert jim.email == 'jim2000@test.com'


def test_save_through_magic_property():
    user = User(email_alias='blah@test.com', age=8).save()
    assert user.email_alias == 'blah@test.com'
    user = User.index.get(email='blah@test.com')
    assert user.email == 'blah@test.com'
    assert user.email_alias == 'blah@test.com'

    user1 = User(email='blah1@test.com', age=8).save()
    assert user1.email_alias == 'blah1@test.com'
    user1.email_alias = 'blah2@test.com'
    assert user1.save()
    user2 = User.index.get(email='blah2@test.com')
    assert user2


class Customer2(StructuredNode):
    email = StringProperty(unique_index=True, required=True)
    age = IntegerProperty(index=True)


def test_not_updated_on_unique_error():
    Customer2(email='jim@bob.com', age=7).save()
    test = Customer2(email='jim1@bob.com', age=2).save()
    test.email = 'jim@bob.com'
    try:
        test.save()
    except UniqueProperty:
        pass
    customers = Customer2.category().instance.all()
    assert customers[0].email != customers[1].email
    assert Customer2.index.get(email='jim@bob.com').age == 7
    assert Customer2.index.get(email='jim1@bob.com').age == 2


def test_refresh():
    c = Customer2(email='my@email.com', age=16).save()
    c.my_custom_prop = 'value'
    copy = Customer2.index.get(email='my@email.com')
    copy.age = 20
    copy.save()

    assert c.age == 16

    c.refresh()
    assert c.age == 20
    assert c.my_custom_prop == 'value'

########NEW FILE########
__FILENAME__ = test_multi_class_relation
from neomodel import StructuredNode, StringProperty, RelationshipTo


class Humanbeing(StructuredNode):
    name = StringProperty(unique_index=True)
    has_a = RelationshipTo(['Location', 'Nationality'], 'HAS_A')


class Location(StructuredNode):
    name = StringProperty(unique_index=True)


class Nationality(StructuredNode):
    name = StringProperty(unique_index=True)


def test_multi_class_rels():
    ne = Humanbeing(name='new news').save()
    lo = Location(name='Belgium').save()
    na = Nationality(name='British').save()

    ne.has_a.connect(lo)
    ne.has_a.connect(na)

    results = ne.has_a.all()
    assert len(results) == 2
    assert isinstance(results[0], Location)
    assert results[0].name == 'Belgium'
    assert isinstance(results[1], Nationality)
    assert results[1].name == 'British'


def test_multi_class_search():
    foo = Humanbeing(name='foo').save()
    lo = Location(name='Birmingham').save()
    na = Nationality(name='Croatian').save()
    na2 = Nationality(name='French').save()

    foo.has_a.connect(lo)
    foo.has_a.connect(na)
    foo.has_a.connect(na2)

    results = foo.has_a.search(name='French')
    assert isinstance(results[0], Nationality)
    results = foo.has_a.search(name='Birmingham')
    assert isinstance(results[0], Location)

########NEW FILE########
__FILENAME__ = test_properties
from neomodel.properties import (IntegerProperty, DateTimeProperty,
    DateProperty, StringProperty, JSONProperty)
from neomodel.exception import InflateError, DeflateError
from neomodel import StructuredNode
from pytz import timezone
from datetime import datetime, date


class FooBar(object):
    pass


def test_deflate_inflate():
    prop = IntegerProperty(required=True)
    prop.name = 'age'
    prop.owner = FooBar

    try:
        prop.inflate("six")
    except InflateError as e:
        assert True
        assert str(e).index('inflate property')
    else:
        assert False

    try:
        prop.deflate("six")
    except DeflateError as e:
        assert True
        assert str(e).index('deflate property')
    else:
        assert False


def test_datetimes_timezones():
    prop = DateTimeProperty()
    prop.name = 'foo'
    prop.owner = FooBar
    t = datetime.utcnow()
    gr = timezone('Europe/Athens')
    gb = timezone('Europe/London')
    dt1 = gr.localize(t)
    dt2 = gb.localize(t)
    time1 = prop.inflate(prop.deflate(dt1))
    time2 = prop.inflate(prop.deflate(dt2))
    assert time1.utctimetuple() == dt1.utctimetuple()
    assert time1.utctimetuple() < time2.utctimetuple()
    assert time1.tzname() == 'UTC'


def test_date():
    prop = DateProperty()
    prop.name = 'foo'
    prop.owner = FooBar
    somedate = date(2012, 12, 15)
    assert prop.deflate(somedate) == '2012-12-15'
    assert prop.inflate('2012-12-15') == somedate


def test_datetime_exceptions():
    prop = DateTimeProperty()
    prop.name = 'created'
    prop.owner = FooBar
    faulty = 'dgdsg'

    try:
        prop.inflate(faulty)
    except InflateError as e:
        assert True
        assert str(e).index('inflate property')
    else:
        assert False

    try:
        prop.deflate(faulty)
    except DeflateError as e:
        assert True
        assert str(e).index('deflate property')
    else:
        assert False


def test_date_exceptions():
    prop = DateProperty()
    prop.name = 'date'
    prop.owner = FooBar
    faulty = '2012-14-13'

    try:
        prop.inflate(faulty)
    except InflateError as e:
        assert True
        assert str(e).index('inflate property')
    else:
        assert False

    try:
        prop.deflate(faulty)
    except DeflateError as e:
        assert True
        assert str(e).index('deflate property')
    else:
        assert False


def test_json():
    prop = JSONProperty()
    prop.name = 'json'
    prop.owner = FooBar

    value = {'test': [1, 2, 3]}

    assert prop.deflate(value) == '{"test": [1, 2, 3]}'
    assert prop.inflate('{"test": [1, 2, 3]}') == value


def test_default_value():
    class DefaultTestValue(StructuredNode):
        name_xx = StringProperty(default='jim', index=True)

    a = DefaultTestValue()
    assert a.name_xx == 'jim'
    a.save()
    return
    b = DefaultTestValue.index.get(name='jim')
    assert b.name == 'jim'

    c = DefaultTestValue(name=None)
    assert c.name == 'jim'


def test_default_value_callable():
    def uid_generator():
        return 'xx'

    class DefaultTestValueTwo(StructuredNode):
        uid = StringProperty(default=uid_generator, index=True)

    a = DefaultTestValueTwo().save()
    assert a.uid == 'xx'


def test_default_valude_callable_type():
    # check our object gets converted to str without serializing and reload
    def factory():
        class Foo(object):
            def __str__(self):
                return "123"
        return Foo()

    class DefaultTestValueThree(StructuredNode):
        uid = StringProperty(default=factory, index=True)

    x = DefaultTestValueThree()
    assert x.uid == '123'
    x.save()
    assert x.uid == '123'
    x.refresh()
    assert x.uid == '123'

########NEW FILE########
__FILENAME__ = test_relationships
from neomodel import (StructuredNode, RelationshipTo, RelationshipFrom,
        Relationship, StringProperty, IntegerProperty, One)


class Person(StructuredNode):
    name = StringProperty(unique_index=True)
    age = IntegerProperty(index=True)
    is_from = RelationshipTo('Country', 'IS_FROM')
    knows = Relationship('Person', 'KNOWS')

    @property
    def special_name(self):
        return self.name

    def special_power(self):
        return "I have no powers"


class Country(StructuredNode):
    code = StringProperty(unique_index=True)
    inhabitant = RelationshipFrom(Person, 'IS_FROM')
    president = RelationshipTo(Person, 'PRESIDENT', cardinality=One)


class SuperHero(Person):
    power = StringProperty(index=True)

    def special_power(self):
        return "I have powers"


def test_actions_on_deleted_node():
    u = Person(name='Jim2', age=3).save()
    u.delete()
    try:
        u.is_from.connect(None)
    except ValueError:
        assert True
    else:
        assert False

    try:
        u.is_from.get()
    except ValueError:
        assert True
    else:
        assert False

    try:
        u.save()
    except ValueError:
        assert True
    else:
        assert False


def test_bidirectional_relationships():
    u = Person(name='Jim', age=3).save()
    assert u

    de = Country(code='DE').save()
    assert de

    assert len(u.is_from) == 0
    assert not u.is_from

    assert u.is_from.__class__.__name__ == 'ZeroOrMore'
    u.is_from.connect(de)

    assert len(u.is_from) == 1
    assert u.is_from

    assert u.is_from.is_connected(de)

    b = u.is_from.all()[0]
    assert b.__class__.__name__ == 'Country'
    assert b.code == 'DE'

    s = b.inhabitant.all()[0]
    assert s.name == 'Jim'

    u.is_from.disconnect(b)
    assert not u.is_from.is_connected(b)


def test_either_direction_connect():
    rey = Person(name='Rey', age=3).save()
    sakis = Person(name='Sakis', age=3).save()

    rey.knows.connect(sakis)
    assert rey.knows.is_connected(sakis)
    assert sakis.knows.is_connected(rey)
    sakis.knows.connect(rey)

    result, meta = sakis.cypher("""START us=node({self}), them=node({them})
            MATCH (us)-[r:KNOWS]-(them) RETURN COUNT(r)""",
            {'them': rey.__node__._id})
    assert int(result[0][0]) == 1


def test_search():
    fred = Person(name='Fred', age=13).save()
    zz = Country(code='ZZ').save()
    zx = Country(code='ZX').save()
    zt = Country(code='ZY').save()
    fred.is_from.connect(zz)
    fred.is_from.connect(zx)
    fred.is_from.connect(zt)
    result = fred.is_from.search(code='ZX')
    assert result[0].code == 'ZX'


def test_custom_methods():
    u = Person(name='Joe90', age=13).save()
    assert u.special_power() == "I have no powers"
    u = SuperHero(name='Joe91', age=13, power='xxx').save()
    assert u.special_power() == "I have powers"
    assert u.special_name == 'Joe91'


def test_valid_reconnection():
    p = Person(name='ElPresidente', age=93).save()
    assert p

    pp = Person(name='TheAdversary', age=33).save()
    assert pp

    c = Country(code='CU').save()
    assert c

    c.president.connect(p)
    assert c.president.is_connected(p)

    # the coup d'etat
    c.president.reconnect(p, pp)
    assert c.president.is_connected(pp)

    # reelection time
    c.president.reconnect(pp, pp)
    assert c.president.is_connected(pp)


def test_props_relationship():
    u = Person(name='Mar', age=20).save()
    assert u

    c = Country(code='AT').save()
    assert c

    c2 = Country(code='LA').save()
    assert c2

    c.inhabitant.connect(u, properties={'city': 'Thessaloniki'})
    assert c.inhabitant.is_connected(u)

    # Check if properties were inserted
    result, meta = u.cypher('START root=node:Person(name={name})' +
        ' MATCH root-[r:IS_FROM]->() RETURN r.city', {'name': u.name})
    assert result and result[0][0] == 'Thessaloniki'

    u.is_from.reconnect(c, c2)
    assert u.is_from.is_connected(c2)

    # Check if properties are transferred correctly
    result, meta = u.cypher('START root=node:Person(name={name})' +
        ' MATCH root-[r:IS_FROM]->() RETURN r.city', {'name': u.name})
    assert result and result[0][0] == 'Thessaloniki'

########NEW FILE########
__FILENAME__ = test_relationship_models
from neomodel import (StructuredNode, StructuredRel, Relationship, RelationshipTo,
        StringProperty, DateTimeProperty, DeflateError)
from datetime import datetime
import pytz


class FriendRel(StructuredRel):
    since = DateTimeProperty(default=lambda: datetime.now(pytz.utc))


class HatesRel(FriendRel):
    reason = StringProperty()


class Badger(StructuredNode):
    name = StringProperty(unique_index=True)
    friend = Relationship('Badger', 'FRIEND', model=FriendRel)
    hates = RelationshipTo('Stoat', 'HATES', model=HatesRel)


class Stoat(StructuredNode):
    name = StringProperty(unique_index=True)
    hates = RelationshipTo('Badger', 'HATES', model=HatesRel)


def test_either_connect_with_rel_model():
    paul = Badger(name="Paul").save()
    tom = Badger(name="Tom").save()

    # creating rels
    new_rel = tom.friend.disconnect(paul)
    new_rel = tom.friend.connect(paul)
    assert isinstance(new_rel, FriendRel)
    assert isinstance(new_rel.since, datetime)

    # updating properties
    new_rel.since = datetime.now(pytz.utc)
    assert isinstance(new_rel.save(), FriendRel)

    # start and end nodes are the opposite of what you'd expect when using either..
    # I've tried everything possible to correct this to no avail
    paul = new_rel.start_node()
    tom = new_rel.end_node()
    assert paul.name == 'Paul'
    assert tom.name == 'Tom'


def test_direction_connect_with_rel_model():
    paul = Badger(name="Paul the badger").save()
    ian = Stoat(name="Ian the stoat").save()

    rel = ian.hates.connect(paul, {'reason': "thinks paul should bath more often"})
    assert isinstance(rel.since, datetime)
    assert isinstance(rel, FriendRel)
    assert rel.reason.startswith("thinks")
    rel.reason = 'he smells'
    rel.save()

    ian = rel.start_node()
    assert isinstance(ian, Stoat)
    paul = rel.end_node()
    assert isinstance(paul, Badger)

    assert ian.name.startswith("Ian")
    assert paul.name.startswith("Paul")

    rel = ian.hates.relationship(paul)
    assert isinstance(rel, HatesRel)
    assert isinstance(rel.since, datetime)
    rel.save()

    # test deflate checking
    rel.since = "2:30pm"
    try:
        rel.save()
    except DeflateError:
        assert True
    else:
        assert False

    # check deflate check via connect
    try:
        paul.hates.connect(ian, {'reason': "thinks paul should bath more often", 'since': '2:30pm'})
    except DeflateError:
        assert True
    else:
        assert False


def test_traversal_where_clause():
    phill = Badger(name="Phill the badger").save()
    tim = Badger(name="Tim the badger").save()
    bob = Badger(name="Bob the badger").save()
    rel = tim.friend.connect(bob)
    now = datetime.now(pytz.utc)
    assert rel.since < now
    rel2 = tim.friend.connect(phill)
    assert rel2.since > now
    friends = tim.traverse('friend', ('since', '>', now)).run()
    assert len(friends) == 1

########NEW FILE########
__FILENAME__ = test_relative_relationships
from neomodel import StructuredNode, RelationshipTo, StringProperty
from .test_relationships import Country


class Cat(StructuredNode):
    name = StringProperty()
    # Relationship is defined using a relative class path
    is_from = RelationshipTo('.test_relationships.Country', 'IS_FROM')


def test_relative_relationship():
    a = Cat(name='snufkin').save()
    assert a

    c = Country(code='MG').save()
    assert c

    # connecting an instance of the class defined above
    # the next statement will fail if there's a type mismatch
    a.is_from.connect(c)
    assert a.is_from.is_connected(c)

########NEW FILE########
__FILENAME__ = test_semi_structured
from neomodel import (StringProperty, IntegerProperty)
from neomodel.contrib import SemiStructuredNode


class UserProf(SemiStructuredNode):
    email = StringProperty(unique_index=True, required=True)
    age = IntegerProperty(index=True)


def test_save_to_model_with_extras():
    u = UserProf(email='jim@test.com', age=3, bar=99)
    u.foo = True
    assert u.save()
    u = UserProf.index.get(age=3)
    assert u.foo is True
    assert u.bar == 99

########NEW FILE########
__FILENAME__ = test_signals
from nose.plugins.skip import SkipTest
from neomodel import StructuredNode, StringProperty, SIGNAL_SUPPORT


if not SIGNAL_SUPPORT:
    raise SkipTest("Couldn't import django signals skipping")
else:
    from django.db.models import signals


SENT_SIGNAL = {}
HOOK_CALLED = {}


class TestSignals(StructuredNode):
    name = StringProperty()

    def pre_save(self):
        HOOK_CALLED['pre_save'] = True


def pre_save(sender, instance, signal):
    SENT_SIGNAL['pre_save'] = True
signals.pre_save.connect(pre_save, sender=TestSignals)


def post_save(sender, instance, signal):
    SENT_SIGNAL['post_save'] = True
signals.post_save.connect(post_save, sender=TestSignals)


def pre_delete(sender, instance, signal):
    SENT_SIGNAL['pre_delete'] = True
signals.pre_delete.connect(pre_delete, sender=TestSignals)


def post_delete(sender, instance, signal):
    SENT_SIGNAL['post_delete'] = True
signals.post_delete.connect(post_delete, sender=TestSignals)


def test_signals():
    test = TestSignals(name=1).save()
    assert 'post_save' in SENT_SIGNAL
    assert 'pre_save' in SENT_SIGNAL
    assert 'pre_save' in HOOK_CALLED

    test.delete()
    assert 'post_delete' in SENT_SIGNAL
    assert 'pre_delete' in SENT_SIGNAL

########NEW FILE########
__FILENAME__ = test_traversal
from neomodel.traversal import TraversalSet
from neomodel import (StructuredNode, RelationshipTo, StringProperty)


class Shopper(StructuredNode):
    name = StringProperty(unique_index=True)
    friend = RelationshipTo('Shopper', 'FRIEND')
    basket = RelationshipTo('Basket', 'BASKET')


class ShoppingItem(StructuredNode):
    name = StringProperty()


class Basket(StructuredNode):
    item = RelationshipTo([ShoppingItem], 'ITEM')


def setup_shopper(name, friend):
    jim = Shopper(name=name).save()
    bob = Shopper(name=friend).save()
    b = Basket().save()
    si1 = ShoppingItem(name='Tooth brush').save()
    si2 = ShoppingItem(name='Screwdriver').save()
    b.item.connect(si1)
    b.item.connect(si2)
    jim.friend.connect(bob)
    bob.basket.connect(b)
    return jim


def test_one_level_traversal():
    jim = setup_shopper('Jim', 'Bob')
    t = TraversalSet(jim)
    for friend in t.traverse('friend'):
        assert isinstance(friend, Shopper)
    assert t.last_ast[-1]['return'][0] == 'friend'
    assert t.last_ast[-3]['name'] == 'friend'


def test_multilevel_traversal():
    bill = setup_shopper('bill', 'ted')
    result = bill.traverse('friend').traverse('basket').traverse('item')
    for i in result:
        assert i.__class__ is ShoppingItem
    assert 'Screwdriver' in [i.name for i in result]


def test_none_existant_relmanager():
    t = Shopper(name='Test').save()
    try:
        t.traverse('friend').traverse('foo')
    except AttributeError:
        assert True
    else:
        assert False


def test_iteration():
    jim = setup_shopper('Jill', 'Barbra')
    jim.friend.connect(Shopper(name='timothy').save())
    i = 0
    for item in jim.traverse('friend'):
        i += 1
        assert isinstance(item, (Shopper,))
    assert i


def test_len_and_bool():
    jim = setup_shopper('Jill1', 'Barbra2')
    assert len(jim.traverse('friend'))


def test_slice_and_index():
    jim = setup_shopper('Jill2', 'Barbra3')
    jim.friend.connect(Shopper(name='Fred').save())
    jim.friend.connect(Shopper(name='Terry').save())
    for i in jim.traverse('friend').limit(3):
        assert isinstance(i, Shopper)
    assert isinstance(jim.traverse('friend').run()[1], Shopper)


def test_order_by_skip_limit():
    zara = Shopper(name='Zara').save()
    zara.friend.connect(Shopper(name='Alan').save())
    zara.friend.connect(Shopper(name='Wendy').save())
    friends = zara.traverse('friend').order_by('friend.name').limit(2).run()
    assert friends[0].name == 'Alan'
    assert friends[1].name == 'Wendy'
    friends = zara.traverse('friend').order_by_desc('name').skip(1).limit(1).run()
    assert friends[0].name == 'Alan'
    friends = zara.traverse('friend').order_by_desc('name').skip(1).limit(1).run()
    assert friends[0].name == 'Alan'


def test_where_clause():
    terrance = setup_shopper('Terrance', 'Teriesa')
    results = terrance.traverse('friend').where('name', '=', 'Teriesa').limit(1).run()
    assert results[0].name == 'Teriesa'

    # clause with property that doesn't exist
    try:
        terrance.traverse('friend').where('age?', '>', 7).run()
    except ValueError:
        assert True
    else:
        assert False

########NEW FILE########
