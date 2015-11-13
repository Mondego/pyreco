__FILENAME__ = endpoints_proto_datastore_test_runner
# Copyright 2013 Google Inc. All Rights Reserved.

"""Run all unittests.

Idea borrowed from ndb project:
code.google.com/p/appengine-ndb-experiment/source/browse/ndb/ndb_test.py
"""


import os
import subprocess
import sys
import unittest

import test_utils


MODULES_TO_TEST = ['utils']
NO_DEVAPPSERVER_TEMPLATE = ('Either dev appserver file path %r does not exist '
                            'or dev_appserver.py is not on your PATH.')


def fix_up_path():
  """Changes import path to make all dependencies import correctly.

  Performs the following:
  - Removes the 'google' module from sys.modules, if it exists, since
    this could cause the google.appengine... imports to fail.
  - Follow the symlink that puts dev_appserver.py on the user's path
    to find the App Engine SDK and add the SDK root to the path.
  - Import dev_appserver from the SDK and fix up the path for imports using
    dev_appserver.fix_sys_path.
  - Add the current git project root to the import path.
  """
  # May have namespace conflicts with google.appengine.api...
  # such as google.net.proto
  sys.modules.pop('google', None)

  # Find where dev_appserver.py is installed locally. If dev_appserver.py
  # is not on the path, then 'which' will return None.
  dev_appserver_on_path = test_utils.which('dev_appserver.py')
  if dev_appserver_on_path is None or not os.path.exists(dev_appserver_on_path):
    print >>sys.stderr, NO_DEVAPPSERVER_TEMPLATE % (dev_appserver_on_path,)
    raise SystemExit(1)

  real_path = os.path.realpath(dev_appserver_on_path)
  sys.path.insert(0, os.path.dirname(real_path))
  import dev_appserver
  # Use fix_sys_path to make all App Engine imports work
  dev_appserver.fix_sys_path()

  project_root = subprocess.check_output(
      ['git', 'rev-parse', '--show-toplevel']).strip()
  sys.path.insert(0, project_root)


def load_tests(import_location):
  """Loads all tests for modules and adds them to a single test suite.

  Args:
    import_location: String; used to determine how the endpoints_proto_datastore
        package is imported.

  Returns:
    Instance of unittest.TestSuite containing all tests from the modules in
        this library.
  """
  test_modules = ['%s_test' % name for name in MODULES_TO_TEST]
  endpoints_proto_datastore = __import__(import_location,
                                         fromlist=test_modules, level=1)

  loader = unittest.TestLoader()
  suite = unittest.TestSuite()

  for module in [getattr(endpoints_proto_datastore, name)
                 for name in test_modules]:
    for name in set(dir(module)):
      try:
        if issubclass(getattr(module, name), unittest.TestCase):
          test_case = getattr(module, name)
          tests = loader.loadTestsFromTestCase(test_case)
          suite.addTests(tests)
      except TypeError:
        pass

  return suite


def main():
  """Fixes up the import path and runs all tests.

  Also makes sure it can import the endpoints_proto_datastore package and passes
  the import location along to load_tests().
  """
  fix_up_path()
  # As the number of environments goes up (such as Google's production
  # environment), this will expand to include those.
  import endpoints_proto_datastore
  import_location = 'endpoints_proto_datastore'

  v = 1
  for arg in sys.argv[1:]:
    if arg.startswith('-v'):
      v += arg.count('v')
    elif arg == '-q':
      v = 0
  result = unittest.TextTestRunner(verbosity=v).run(load_tests(import_location))
  sys.exit(not result.wasSuccessful())


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = model
# Copyright 2012 Google Inc. All Rights Reserved.

"""EndpointsModel definition and accompanying definitions.

This model can be used to replace an existing NDB model and allow simple
conversion of model classes into ProtoRPC message classes. These classes can be
used to simplify endpoints API methods so that only entities need be used rather
than converting between ProtoRPC messages and entities and then back again.
"""

import functools
import itertools
try:
  import json
except ImportError:
  import simplejson as json
import pickle
import re

import endpoints

from . import properties
from . import utils as ndb_utils
from .. import utils

from protorpc import messages
from protorpc import message_types

from google.appengine.api import datastore_types
from google.appengine.datastore import datastore_query
from google.appengine.ext import ndb


__all__ = ['EndpointsModel']


QUERY_LIMIT_DEFAULT = 10
QUERY_LIMIT_MAX = 100
QUERY_MAX_EXCEEDED_TEMPLATE = '%s results requested. Exceeds limit of %s.'
PROPERTY_COLLISION_TEMPLATE = ('Name conflict: %s set as an NDB property and '
                               'an Endpoints alias property.')
BAD_FIELDS_SCHEMA_TEMPLATE = (
    'Model %s has bad message fields schema type: %s. Only a '
    'list, tuple, dictionary or MessageFieldsSchema are allowed.')
NO_MSG_FIELD_TEMPLATE = ('Tried to use a ProtoRPC message field: %s. Only '
                         'simple fields can be used when allow message fields '
                         'is turned off.')
REQUEST_MESSAGE = 'request_message'
RESPONSE_MESSAGE = 'response_message'
HTTP_METHOD = 'http_method'
PATH = 'path'
QUERY_HTTP_METHOD = 'GET'
# This global will be updated after EndpointsModel is defined and is used by
# the metaclass EndpointsMetaModel
BASE_MODEL_CLASS = None

EndpointsAliasProperty = properties.EndpointsAliasProperty
MessageFieldsSchema = utils.MessageFieldsSchema


def _VerifyProperty(modelclass, attr_name):
  """Return a property if set on a model class, otherwise raises an exception.

  Args:
    modelclass: A subclass of EndpointsModel which has a
        _GetEndpointsProperty method.
    attr_name: String; the name of the property.

  Returns:
    The property set at the attribute name.

  Raises:
    AttributeError: if the property is not set on the class.
  """
  prop = modelclass._GetEndpointsProperty(attr_name)
  if prop is None:
    error_msg = ('The attribute %s is not an accepted field. Accepted fields '
                 'are limited to NDB properties and Endpoints alias '
                 'properties.' % (attr_name,))
    raise AttributeError(error_msg)

  return prop


def ToValue(prop, value):
  """Serializes a value from a property to a ProtoRPC message type.

  Args:
    prop: The NDB or alias property to be converted.
    value: The value to be serialized.

  Returns:
    The serialized version of the value to be set on a ProtoRPC message.
  """
  if value is None:
    return value
  elif isinstance(value, EndpointsModel):
    return value.ToMessage()
  elif hasattr(prop, 'ToValue') and callable(prop.ToValue):
    return prop.ToValue(value)
  elif isinstance(prop, ndb.JsonProperty):
    return json.dumps(value)
  elif isinstance(prop, ndb.PickleProperty):
    return pickle.dumps(value)
  elif isinstance(prop, ndb.UserProperty):
    return utils.UserMessageFromUser(value)
  elif isinstance(prop, ndb.GeoPtProperty):
    return utils.GeoPtMessage(lat=value.lat, lon=value.lon)
  elif isinstance(prop, ndb.KeyProperty):
    return value.urlsafe()
  elif isinstance(prop, ndb.BlobKeyProperty):
    return str(value)
  elif isinstance(prop, (ndb.TimeProperty,
                         ndb.DateProperty,
                         ndb.DateTimeProperty)):
    return utils.DatetimeValueToString(value)
  else:
    return value


def FromValue(prop, value):
  """Deserializes a value from a ProtoRPC message type to a property value.

  Args:
    prop: The NDB or alias property to be set.
    value: The value to be deserialized.

  Returns:
    The deserialized version of the ProtoRPC value to be set on a property.

  Raises:
    TypeError: if a StructuredProperty has a model class that is not an
        EndpointsModel.
  """
  if value is None:
    return value

  if isinstance(prop, (ndb.StructuredProperty, ndb.LocalStructuredProperty)):
    modelclass = prop._modelclass
    if not utils.IsSubclass(modelclass, EndpointsModel):
      error_msg = ('Structured properties should refer to models which '
                   'inherit from EndpointsModel. Received an instance '
                   'of %s.' % (modelclass.__class__.__name__,))
      raise TypeError(error_msg)
    return modelclass.FromMessage(value)

  if hasattr(prop, 'FromValue') and callable(prop.FromValue):
    return prop.FromValue(value)
  elif isinstance(prop, ndb.JsonProperty):
    return json.loads(value)
  elif isinstance(prop, ndb.PickleProperty):
    return pickle.loads(value)
  elif isinstance(prop, ndb.UserProperty):
    return utils.UserMessageToUser(value)
  elif isinstance(prop, ndb.GeoPtProperty):
    return datastore_types.GeoPt(lat=value.lat, lon=value.lon)
  elif isinstance(prop, ndb.KeyProperty):
    return ndb.Key(urlsafe=value)
  elif isinstance(prop, ndb.BlobKeyProperty):
    return datastore_types.BlobKey(value)
  elif isinstance(prop, (ndb.TimeProperty,
                         ndb.DateProperty,
                         ndb.DateTimeProperty)):
    return utils.DatetimeValueFromString(value)
  else:
    return value


class _EndpointsQueryInfo(object):
  """A custom container for query information.

  This will be set on an EndpointsModel (or subclass) instance, and can be used
  in conjunction with alias properties to store query information, simple
  filters, ordering and ancestor.

  Uses an entity to construct simple filters, to validate ordering, to validate
  ancestor and finally to construct a query from these filters, ordering and/or
  ancestor.

  Attributes:
    _entity: An instance of EndpointsModel or a subclass. The values from this
        will be used to create filters for a query.
    _filters: A set of simple equality filters (ndb.FilterNode). Utilizes the
        fact that FilterNodes are hashable and respect equality.
    _ancestor: An ndb Key to be used as an ancestor for a query.
    _cursor: A datastore_query.Cursor, to be used for resuming a query.
    _limit: A positive integer, to be used in a fetch.
    _order: String; comma separated list of property names or property names
        preceded by a minus sign. Used to define an order of query results.
    _order_attrs: The attributes (or negation of attributes) parsed from
        _order. If these can't be parsed from the attributes in _entity, will
        throw an exception.
    _query_final: A final query created using the orders (_order_attrs), filters
        (_filters) and class definition (_entity) in the query info. If this is
        not null, setting attributes on the query info object will fail.
  """

  def __init__(self, entity):
    """Sets all internal variables to the default values and verifies entity.

    Args:
      entity: An instance of EndpointsModel or a subclass.

    Raises:
      TypeError: if entity is not an instance of EndpointsModel or a subclass.
    """
    if not isinstance(entity, EndpointsModel):
      raise TypeError('Query info can only be used with an instance of an '
                      'EndpointsModel subclass. Received: instance of %s.' %
                      (entity.__class__.__name__,))
    self._entity = entity

    self._filters = set()
    self._ancestor = None
    self._cursor = None
    self._limit = None
    self._order = None
    self._order_attrs = ()

    self._query_final = None

  def _PopulateFilters(self):
    """Populates filters in query info by using values set on the entity."""
    entity = self._entity
    for prop in entity._properties.itervalues():
      # The name of the attr on the model/object, may differ from the name
      # of the NDB property in the datastore
      attr_name = prop._code_name
      current_value = getattr(entity, attr_name)

      if prop._repeated:
        if current_value != []:
          raise ValueError('No queries on repeated values are allowed.')
        continue

      # Only filter for non-null values
      if current_value is not None:
        self._AddFilter(prop == current_value)

  def SetQuery(self):
    """Sets the final query on the query info object.

    Uses the filters and orders in the query info to refine the query. If the
    final query is already set, does nothing.
    """
    if self._query_final is not None:
      return

    self._PopulateFilters()

    # _entity.query calls the classmethod for the entity
    if self.ancestor is not None:
      query = self._entity.query(ancestor=self.ancestor)
    else:
      query = self._entity.query()

    for simple_filter in self._filters:
      query = query.filter(simple_filter)
    for order_attr in self._order_attrs:
      query = query.order(order_attr)

    self._query_final = query

  def _AddFilter(self, candidate_filter):
    """Checks a filter and sets it in the filter set.

    Args:
      candidate_filter: An NDB filter which may be added to the query info.

    Raises:
      AttributeError: if query on the object is already final.
      TypeError: if the filter is not a simple filter (FilterNode).
      ValueError: if the operator symbol in the filter is not equality.
    """
    if self._query_final is not None:
      raise AttributeError('Can\'t add more filters. Query info is final.')

    if not isinstance(candidate_filter, ndb.FilterNode):
      raise TypeError('Only simple filters can be used. Received: %s.' %
                      (candidate_filter,))
    opsymbol = candidate_filter._FilterNode__opsymbol
    if opsymbol != '=':
      raise ValueError('Only equality filters allowed. Received: %s.' %
                       (opsymbol,))

    self._filters.add(candidate_filter)

  @property
  def query(self):
    """Public getter for the final query on query info."""
    return self._query_final

  def _GetAncestor(self):
    """Getter to be used for public ancestor property on query info."""
    return self._ancestor

  def _SetAncestor(self, value):
    """Setter to be used for public ancestor property on query info.

    Args:
      value: A potential value for an ancestor.

    Raises:
      AttributeError: if query on the object is already final.
      AttributeError: if the ancestor has already been set.
      TypeError: if the value to be set is not an instance of ndb.Key.
    """
    if self._query_final is not None:
      raise AttributeError('Can\'t set ancestor. Query info is final.')

    if self._ancestor is not None:
      raise AttributeError('Ancestor can\'t be set twice.')
    if not isinstance(value, ndb.Key):
      raise TypeError('Ancestor must be an instance of ndb.Key.')
    self._ancestor = value

  ancestor = property(fget=_GetAncestor, fset=_SetAncestor)

  def _GetCursor(self):
    """Getter to be used for public cursor property on query info."""
    return self._cursor

  def _SetCursor(self, value):
    """Setter to be used for public cursor property on query info.

    Args:
      value: A potential value for a cursor.

    Raises:
      AttributeError: if query on the object is already final.
      AttributeError: if the cursor has already been set.
      TypeError: if the value to be set is not an instance of
          datastore_query.Cursor.
    """
    if self._query_final is not None:
      raise AttributeError('Can\'t set cursor. Query info is final.')

    if self._cursor is not None:
      raise AttributeError('Cursor can\'t be set twice.')
    if not isinstance(value, datastore_query.Cursor):
      raise TypeError('Cursor must be an instance of datastore_query.Cursor.')
    self._cursor = value

  cursor = property(fget=_GetCursor, fset=_SetCursor)

  def _GetLimit(self):
    """Getter to be used for public limit property on query info."""
    return self._limit

  def _SetLimit(self, value):
    """Setter to be used for public limit property on query info.

    Args:
      value: A potential value for a limit.

    Raises:
      AttributeError: if query on the object is already final.
      AttributeError: if the limit has already been set.
      TypeError: if the value to be set is not a positive integer.
    """
    if self._query_final is not None:
      raise AttributeError('Can\'t set limit. Query info is final.')

    if self._limit is not None:
      raise AttributeError('Limit can\'t be set twice.')
    if not isinstance(value, (int, long)) or value < 1:
      raise TypeError('Limit must be a positive integer.')
    self._limit = value

  limit = property(fget=_GetLimit, fset=_SetLimit)

  def _GetOrder(self):
    """Getter to be used for public order property on query info."""
    return self._order

  def _SetOrderAttrs(self):
    """Helper method to set _order_attrs using the value of _order.

    If _order is not set, simply returns, else splits _order by commas and then
    looks up each value (or its negation) in the _properties of the entity on
    the query info object.

    We look up directly in _properties rather than using the attribute names
    on the object since only NDB property names will be used for field names.

    Raises:
      AttributeError: if one of the attributes in the order is not a property
          on the entity.
    """
    if self._order is None:
      return

    unclean_attr_names = self._order.strip().split(',')
    result = []
    for attr_name in unclean_attr_names:
      ascending = True
      if attr_name.startswith('-'):
        ascending = False
        attr_name = attr_name[1:]

      attr = self._entity._properties.get(attr_name)
      if attr is None:
        raise AttributeError('Order attribute %s not defined.' % (attr_name,))

      if ascending:
        result.append(+attr)
      else:
        result.append(-attr)

    self._order_attrs = tuple(result)

  def _SetOrder(self, value):
    """Setter to be used for public order property on query info.

    Sets the value of _order and attempts to set _order_attrs as well
    by valling _SetOrderAttrs, which uses the value of _order.

    If the passed in value is None, but the query is not final and the
    order has not already been set, the method will return without any
    errors or data changed.

    Args:
      value: A potential value for an order.

    Raises:
      AttributeError: if query on the object is already final.
      AttributeError: if the order has already been set.
      TypeError: if the order to be set is not a string.
    """
    if self._query_final is not None:
      raise AttributeError('Can\'t set order. Query info is final.')

    if self._order is not None:
      raise AttributeError('Order can\'t be set twice.')

    if value is None:
      return
    elif not isinstance(value, basestring):
      raise TypeError('Order must be a string.')

    self._order = value
    self._SetOrderAttrs()

  order = property(fget=_GetOrder, fset=_SetOrder)


class EndpointsMetaModel(ndb.MetaModel):
  """Metaclass for EndpointsModel.

  This exists to create new instances of the mutable class attributes for
  subclasses and to verify ProtoRPC specific properties.
  """

  def __init__(cls, name, bases, classdict):
    """Verifies additional ProtoRPC properties on an NDB model."""
    super(EndpointsMetaModel, cls).__init__(name, bases, classdict)

    # Reset the `_message_fields_schema` to `None` unless it was explicitly
    # mentioned in the class definition. It's possible for this value to be
    # set if a superclass had this value set by `_VerifyMessageFieldsSchema`
    # then this subclass would keep that value, even if that was not the
    # intended behavior.
    if '_message_fields_schema' not in classdict:
      cls._message_fields_schema = None

    cls._alias_properties = {}
    cls._proto_models = {}
    cls._proto_collections = {}
    cls._resource_containers = {}
    cls._property_to_proto = ndb_utils.NDB_PROPERTY_TO_PROTO.copy()

    cls._FixUpAliasProperties()

    cls._VerifyMessageFieldsSchema()
    cls._VerifyProtoMapping()

  def _FixUpAliasProperties(cls):
    """Updates the alias properties map and verifies each alias property.

    Raises:
      AttributeError: if an alias property is defined beginning with
          an underscore.
      AttributeError: if an alias property is defined that conflicts with
          an NDB property.
    """
    for attr_name in dir(cls):
      prop = getattr(cls, attr_name, None)
      if isinstance(prop, EndpointsAliasProperty):
        if attr_name.startswith('_'):
          raise AttributeError('EndpointsAliasProperty %s cannot begin with an '
                               'underscore character.' % (attr_name,))
        if attr_name in cls._properties:
          raise AttributeError(PROPERTY_COLLISION_TEMPLATE % (attr_name,))
        prop._FixUp(attr_name)
        cls._alias_properties[prop._name] = prop

  def _VerifyMessageFieldsSchema(cls):
    """Verifies that the preset message fields correspond to actual properties.

    If no message fields schema was set on the class, sets the schema using the
    default fields determing by the NDB properties and alias properties defined.

    In either case, converts the passed in fields to an instance of
       MessageFieldsSchema and sets that as the value of _message_fields_schema
       on the class.

    Raises:
      TypeError: if a message fields schema was set on the class that is not a
          list, tuple, dictionary, or MessageFieldsSchema instance.
    """
    message_fields_schema = getattr(cls, '_message_fields_schema', None)
    # Also need to check we aren't re-using from EndpointsModel
    base_schema = getattr(BASE_MODEL_CLASS, '_message_fields_schema', None)
    if message_fields_schema is None or message_fields_schema == base_schema:
      message_fields_schema = cls._DefaultFields()
    elif not isinstance(message_fields_schema,
                        (list, tuple, dict, MessageFieldsSchema)):
      raise TypeError(BAD_FIELDS_SCHEMA_TEMPLATE %
                      (cls.__name__, message_fields_schema.__class__.__name__))
    else:
      for attr in message_fields_schema:
        _VerifyProperty(cls, attr)

    cls._message_fields_schema = MessageFieldsSchema(message_fields_schema,
                                                     name=cls.__name__)

  def _VerifyProtoMapping(cls):
    """Verifies that each property on the class has an associated proto mapping.

    First checks if there is a _custom_property_to_proto dictionary present and
    then overrides the class to proto mapping found in _property_to_proto.

    Then, for each property (NDB or alias), tries to add a mapping first by
    checking for a message field attribute, and then by trying to infer based
    on property subclass.

    Raises:
      TypeError: if a key from _custom_property_to_proto is not a valid NBD
          property. (We don't allow EndpointsAliasProperty here because it
          is not meant to be subclassed and defines a message_field).
      TypeError: if after checking _custom_property_to_proto, message_field and
          inference from a superclass, no appropriate mapping is found in
          _property_to_proto.
    """
    custom_property_to_proto = getattr(cls, '_custom_property_to_proto', None)
    if isinstance(custom_property_to_proto, dict):
      for key, value in custom_property_to_proto.iteritems():
        if not utils.IsSubclass(key, ndb.Property):
          raise TypeError('Invalid property class: %s.' % (key,))
        cls._property_to_proto[key] = value

    for prop in cls._EndpointsPropertyItervalues():
      property_class = prop.__class__
      cls._TryAddMessageField(property_class)
      cls._TryInferSuperclass(property_class)

      if property_class not in cls._property_to_proto:
        raise TypeError('No converter present for property %s' %
                        (property_class.__name__,))

  # TODO(dhermes): Consider renaming this optional property attr from
  #                "message_field" to something more generic. It can either be
  #                a field or it can be a method with the signature
  #                (property instance, integer index)
  def _TryAddMessageField(cls, property_class):
    """Tries to add a proto mapping for a property class using a message field.

    If the property class is already in the proto mapping, does nothing.

    Args:
      property_class: The class of a property from a model.
    """
    if property_class in cls._property_to_proto:
      return

    message_field = getattr(property_class, 'message_field', None)
    if message_field is not None:
      cls._property_to_proto[property_class] = message_field

  def _TryInferSuperclass(cls, property_class):
    """Tries to add a proto mapping for a property class by using a base class.

    If the property class is already in the proto mapping, does nothing.
    Descends up the class hierarchy until an ancestor class has more than one
    base class or until ndb.Property is reached. If any class up the hierarchy
    is already in the proto mapping, the method/field for the superclass is also
    set for the propert class in question.

    Args:
      property_class: The class of a property from a model.
    """
    if (property_class in cls._property_to_proto or
        utils.IsSubclass(property_class, EndpointsAliasProperty)):
      return

    bases = property_class.__bases__
    while len(bases) == 1 and bases[0] != ndb.Property:
      base = bases[0]
      if base in cls._property_to_proto:
        cls._property_to_proto[property_class] = cls._property_to_proto[base]
        return
      else:
        bases = base.__bases__


class EndpointsModel(ndb.Model):
  """Subclass of NDB model that enables translation to ProtoRPC message classes.

  Also uses a subclass of ndb.MetaModel as the metaclass, to allow for custom
  behavior (particularly property verification) on class creation. Two types of
  properties are allowed, the standard NDB property, which ends up in a
  _properties dictionary and {EndpointsAliasProperty}s, which end up in an
  _alias_properties dictionary. They can be accessed simultaneously through
  _GetEndpointsProperty.

  As with NDB, you cannot use the same property object to describe multiple
  properties -- you must create separate property objects for each property.

  In addition to _alias_properties, there are several other class variables that
  can be used to augment the default NDB model behavior:
      _property_to_proto: This is a mapping from properties to ProtoRPC message
          fields or methods which can take a property and an index and convert
          them to a message field. It starts out as a copy of the global
          NDB_PROPERTY_TO_PROTO from ndb_utils and can be augmented by your
          class and/or property definitions
      _custom_property_to_proto: if set as a dictionary, allows default mappings
          from NDB properties to ProtoRPC fields in _property_to_proto to be
          overridden.

  The metaclass ensures each property (alias properties included) can be
  converted to a ProtoRPC message field before the class can be created. Due to
  this, a ProtoRPC message class can be created using any subset of the model
  properties in any order, or a collection containing multiple messages of the
  same class. Once created, these ProtoRPC message classes are cached in the
  class variables _proto_models and _proto_collections.

  Endpoints models also have two class methods which can be used as decorators
  for Cloud Endpoints API methods: method and query_method. These methods use
  the endpoints.api decorator but tailor the behavior to the specific model
  class.

  Where a method decorated with the endpoints.api expects a ProtoRPC
  message class for the response and request type, a method decorated with the
  "method" decorator provided by a model class expects an instance of that class
  both as input and output. In order to deserialize the ProtoRPC input to an
  entity and serialize the entity returned by the decorated method back to
  ProtoRPC, request and response fields can be specified which the Endpoints
  model class can use to create (and cache) corresponding ProtoRPC message
  classes.

  Similarly, a method decorated with the query_method decorator expects a query
  for the EndpointsModel subclass both as input and output. Instead of
  specifying request/response fields for entities, a query and collection fields
  list can be used.

  When no fields are provided, the default fields from the class are used. This
  can be overridden by setting the class variable _message_fields_schema to a
  dictionary, list, tuple or MessageFieldsSchema of your choice. If none is
  provided, the default will include all NDB properties and all Endpoints Alias
  properties.
  """

  __metaclass__ = EndpointsMetaModel

  # Custom properties that can be specified to override this value when
  # the class is defined. The value for `custom_property_to_proto`
  # will persist through subclasses while that for `_message_fields_schema`
  # will only work on the class where it is explicitly mentioned in
  # the definition.
  _custom_property_to_proto = None
  _message_fields_schema = None

  # A new instance of each of these will be created by the metaclass
  # every time a subclass is declared
  _alias_properties = None
  _proto_models = None
  _proto_collections = None
  _resource_containers = None
  _property_to_proto = None

  def __init__(self, *args, **kwargs):
    """Initializes NDB model and adds a query info object.

    Attributes:
      _endpoints_query_info: An _EndpointsQueryInfo instance, directly tied to
          the current instance that can be used to form queries using properties
          provided by the instance and can be augmented by alias properties to
          allow custom queries.
    """
    super(EndpointsModel, self).__init__(*args, **kwargs)
    self._endpoints_query_info = _EndpointsQueryInfo(self)
    self._from_datastore = False

  @property
  def from_datastore(self):
    """Property accessor that represents if the entity is from the datastore."""
    return self._from_datastore

  @classmethod
  def _DefaultFields(cls):
    """The default fields for the class.

    Uses all NDB properties and alias properties which are different from the
    alias properties defined on the parent class EndpointsModel.
    """
    fields = cls._properties.keys()
    # Only include Alias properties not defined on the base class
    for prop_name, prop in cls._alias_properties.iteritems():
      base_alias_props = getattr(BASE_MODEL_CLASS, '_alias_properties', {})
      base_prop = base_alias_props.get(prop_name)
      if base_prop != prop:
        fields.append(prop_name)
    return fields

  def _CopyFromEntity(self, entity):
    """Copies properties from another entity to the current one.

    Only sets properties on the current entity that are not already set.

    Args:
      entity: A model instance to be copied from.

    Raises:
      TypeError: if the entity passed in is not the exact same type as the
          current entity.
    """
    if entity.__class__ != self.__class__:
      raise TypeError('Can only copy from entities of the exact type %s. '
                      'Received an instance of %s.' %
                      (self.__class__.__name__, entity.__class__.__name__))

    for prop in entity._EndpointsPropertyItervalues():
      # The name of the attr on the model/object, may differ
      # from the name of the property
      attr_name = prop._code_name

      value = getattr(entity, attr_name)
      if value is not None:
        # Only overwrite null values
        if isinstance(prop, EndpointsAliasProperty):
          value_set = getattr(self, attr_name) is not None
        else:
          value_set = prop._name in self._values
        if not value_set:
          setattr(self, attr_name, value)

  def UpdateFromKey(self, key):
    """Attempts to get current entity for key and update the unset properties.

    Only does anything if there is a corresponding entity in the datastore.
    Calls _CopyFromEntity to merge the current entity with the one that was
    retrieved. If one was retrieved, sets _from_datastore to True to signal that
    an entity was retrieved.

    Args:
      key: An NDB key used to retrieve an entity.
    """
    self._key = key
    entity = self._key.get()
    if entity is not None:
      self._CopyFromEntity(entity)
      self._from_datastore = True

  def IdSet(self, value):
    """Setter to be used for default id EndpointsAliasProperty.

    Sets the key on the current entity using the value passed in as the ID.
    Using this key, attempts to retrieve the entity from the datastore and
    update the unset properties of the current entity with those from the
    retrieved entity.

    Args:
      value: An integer ID value for a simple key.

    Raises:
      TypeError: if the value to be set is not an integer. (Though if outside of
          a given range, the get call will also throw an exception.)
    """
    if not isinstance(value, (int, long)):
      raise TypeError('ID must be an integer.')
    self.UpdateFromKey(ndb.Key(self.__class__, value))

  @EndpointsAliasProperty(setter=IdSet, property_type=messages.IntegerField)
  def id(self):
    """Getter to be used for default id EndpointsAliasProperty.

    Specifies that the ProtoRPC property_type is IntegerField, though simple
    string IDs or more complex IDs that use ancestors could also be used.

    Returns:
      The integer ID of the entity key, if the key is not null and the integer
          ID is not null, else returns None.
    """
    if self._key is not None:
      return self._key.integer_id()

  def EntityKeySet(self, value):
    """Setter to be used for default entityKey EndpointsAliasProperty.

    Sets the key on the current entity using the urlsafe entity key string.
    Using the key set on the entity, attempts to retrieve the entity from the
    datastore and update the unset properties of the current entity with those
    from the retrieved entity.

    Args:
      value: String; A urlsafe entity key for an object.

    Raises:
      TypeError: if the value to be set is not a string. (Though if the string
          is not valid base64 or not properly encoded, the key creation will
          also throw an exception.)
    """
    if not isinstance(value, basestring):
      raise TypeError('entityKey must be a string.')
    self.UpdateFromKey(ndb.Key(urlsafe=value))

  @EndpointsAliasProperty(setter=EntityKeySet)
  def entityKey(self):
    """Getter to be used for default entityKey EndpointsAliasProperty.

    Uses the default ProtoRPC property_type StringField.

    Returns:
      The urlsafe string produced by the entity key, if the key is not null,
          else returns None.
    """
    if self._key is not None:
      return self._key.urlsafe()

  def LimitSet(self, value):
    """Setter to be used for default limit EndpointsAliasProperty.

    Simply sets the limit on the entity's query info object, and the query
    info object handles validation.

    Args:
      value: The limit value to be set.
    """
    self._endpoints_query_info.limit = value

  @EndpointsAliasProperty(setter=LimitSet, property_type=messages.IntegerField)
  def limit(self):
    """Getter to be used for default limit EndpointsAliasProperty.

    Uses the ProtoRPC property_type IntegerField since a limit.

    Returns:
      The integer (or null) limit from the query info on the entity.
    """
    return self._endpoints_query_info.limit

  def OrderSet(self, value):
    """Setter to be used for default order EndpointsAliasProperty.

    Simply sets the order on the entity's query info object, and the query
    info object handles validation.

    Args:
      value: The order value to be set.
    """
    self._endpoints_query_info.order = value

  @EndpointsAliasProperty(setter=OrderSet)
  def order(self):
    """Getter to be used for default order EndpointsAliasProperty.

    Uses the default ProtoRPC property_type StringField.

    Returns:
      The string (or null) order from the query info on the entity.
    """
    return self._endpoints_query_info.order

  def PageTokenSet(self, value):
    """Setter to be used for default pageToken EndpointsAliasProperty.

    Tries to use Cursor.from_websafe_string to convert the value to a cursor
    and then sets the cursor on the entity's query info object, and the query
    info object handles validation.

    Args:
      value: The websafe string version of a cursor.
    """
    cursor = datastore_query.Cursor.from_websafe_string(value)
    self._endpoints_query_info.cursor = cursor

  @EndpointsAliasProperty(setter=PageTokenSet)
  def pageToken(self):
    """Getter to be used for default pageToken EndpointsAliasProperty.

    Uses the default ProtoRPC property_type StringField.

    Returns:
      The websafe string from the cursor on the entity's query info object, or
          None if the cursor is null.
    """
    cursor = self._endpoints_query_info.cursor
    if cursor is not None:
      return cursor.to_websafe_string()

  @classmethod
  def _GetEndpointsProperty(cls, attr_name):
    """Return a property if set on a model class.

    Attempts to retrieve both the NDB and alias version of the property, makes
    sure at most one is not null and then returns that one.

    Args:
      attr_name: String; the name of the property.

    Returns:
      The property set at the attribute name.

    Raises:
      AttributeError: if the property is both an NDB and alias property.
    """
    property_value = cls._properties.get(attr_name)
    alias_value = cls._alias_properties.get(attr_name)
    if property_value is not None and alias_value is not None:
      raise AttributeError(PROPERTY_COLLISION_TEMPLATE % (attr_name,))

    return property_value or alias_value

  @classmethod
  def _EndpointsPropertyItervalues(cls):
    """Iterator containing both NDB and alias property instances for class."""
    property_values = cls._properties.itervalues()
    alias_values = cls._alias_properties.itervalues()
    return itertools.chain(property_values, alias_values)

  @classmethod
  def _MessageFields(cls, message_fields_schema, allow_message_fields=True):
    """Creates ProtoRPC fields from a MessageFieldsSchema.

    Verifies that each property is valid (may cause exception) and then uses the
    proto mapping to create the corresponding ProtoRPC field.

    Args:
      message_fields_schema: MessageFieldsSchema object to create fields from.
      allow_message_fields: An optional boolean; defaults to True. If True, does
          nothing. If False, stops ProtoRPC message classes that have one or
          more ProtoRPC {MessageField}s from being created.

    Returns:
      Dictionary of ProtoRPC fields.

    Raises:
      AttributeError: if a verified property has no proto mapping registered.
          This is a serious error and should not occur due to what happens in
          the metaclass.
      TypeError: if a value from the proto mapping is not a ProtoRPC field or a
          callable method (which takes a property and an index).
      TypeError: if a proto mapping results in a ProtoRPC MessageField while
          message fields are explicitly disallowed by having
          allow_message_fields set to False.
    """
    message_fields = {}
    for index, name in enumerate(message_fields_schema):
      field_index = index + 1
      prop = _VerifyProperty(cls, name)
      to_proto = cls._property_to_proto.get(prop.__class__)

      if to_proto is None:
        raise AttributeError('%s does not have a proto mapping for %s.' %
                             (cls.__name__, prop.__class__.__name__))

      if utils.IsSimpleField(to_proto):
        proto_attr = ndb_utils.MessageFromSimpleField(to_proto, prop,
                                                      field_index)
      elif callable(to_proto):
        proto_attr = to_proto(prop, field_index)
      else:
        raise TypeError('Proto mapping for %s was invalid. Received %s, which '
                        'was neither a ProtoRPC field, nor a callable object.' %
                        (name, to_proto))

      if not allow_message_fields:
        if isinstance(proto_attr, messages.MessageField):
          error_msg = NO_MSG_FIELD_TEMPLATE % (proto_attr.__class__.__name__,)
          raise TypeError(error_msg)

      message_fields[name] = proto_attr

    return message_fields

  @classmethod
  def ProtoModel(cls, fields=None, allow_message_fields=True):
    """Creates a ProtoRPC message class using a subset of the class properties.

    Creates a MessageFieldsSchema from the passed in fields (may cause exception
    if not valid). If this MessageFieldsSchema is already in the cache of
    models, returns the cached value.

    If not creates ProtoRPC fields from the MessageFieldsSchema (may cause
    exception). Using the created fields and the name from the MessageFieldsSchema,
    creates a new ProtoRPC message class by calling the type() constructor.

    Before returning it, it caches the newly created ProtoRPC message class.

    Args:
      fields: Optional fields, defaults to None. If None, the default from
          the class is used. If specified, will be converted to a
          MessageFieldsSchema object (and verified as such).
      allow_message_fields: An optional boolean; defaults to True. If True, does
          nothing. If False, stops ProtoRPC message classes that have one or
          more ProtoRPC {MessageField}s from being created.

    Returns:
      The cached or created ProtoRPC message class specified by the fields.

    Raises:
      TypeError: if a proto mapping results in a ProtoRPC MessageField while
          message fields are explicitly disallowed by having
          allow_message_fields set to False.
    """
    if fields is None:
      fields = cls._message_fields_schema
    # If fields is None, either the module user manaully removed the default
    # value or some bug has occurred in the library
    message_fields_schema = MessageFieldsSchema(fields,
                                                basename=cls.__name__ + 'Proto')

    if message_fields_schema in cls._proto_models:
      cached_model = cls._proto_models[message_fields_schema]
      if not allow_message_fields:
        for field in cached_model.all_fields():
          if isinstance(field, messages.MessageField):
            error_msg = NO_MSG_FIELD_TEMPLATE % (field.__class__.__name__,)
            raise TypeError(error_msg)
      return cached_model

    message_fields = cls._MessageFields(message_fields_schema,
                                        allow_message_fields=allow_message_fields)

    # TODO(dhermes): This behavior should be regulated more directly.
    #                This is to make sure the schema name in the discovery
    #                document is message_fields_schema.name rather than
    #                EndpointsProtoDatastoreNdbModel{message_fields_schema.name}
    message_fields['__module__'] = ''
    message_class = type(message_fields_schema.name,
                         (messages.Message,),
                         message_fields)

    cls._proto_models[message_fields_schema] = message_class
    return message_class

  @classmethod
  def ResourceContainer(cls, message=message_types.VoidMessage, fields=None):
    """Creates a ResourceContainer using a subset of the class properties.

    Creates a MessageFieldsSchema from the passed in fields (may cause exception
    if not valid). If this MessageFieldsSchema in combination with the message
    is already in the cache, returns the cached value.

    If not creates ProtoRPC fields from the MessageFieldsSchema (may cause
    exception) and creates a endpoints.ResourceContainer using the created
    ProtoRPC fields and the provided reques body message.

    Before returning it, it caches the newly created ResourceContainer.

    Args:
      message: ProtoRPC message class to be used as request body.
      fields: Optional fields, defaults to None. If None, the default from
          the class is used. If specified, will be converted to a
          MessageFieldsSchema object (and verified as such).

    Returns:
      The cached or created ResourceContainer specified by the fields and message.

    """

    if fields is None:
      fields = cls._message_fields_schema

    message_fields_schema = MessageFieldsSchema(fields,
                                                basename=cls.__name__ + 'Proto')

    container_key = (message.__name__, message_fields_schema)
    if container_key in cls._resource_containers:
      return cls._resource_containers[container_key]

    message_fields = cls._MessageFields(message_fields_schema,
                                        allow_message_fields=False)

    resource_container = endpoints.ResourceContainer(message, **message_fields)

    cls._resource_containers[container_key] = resource_container
    return resource_container

  @classmethod
  def ProtoCollection(cls, collection_fields=None):
    """Creates a ProtoRPC message class using a subset of the class properties.

    In contrast to ProtoModel, this creates a collection with only two fields:
    items and nextPageToken. The field nextPageToken is used for paging through
    result sets, while the field items is a repeated ProtoRPC MessageField used
    to hold the query results. The fields passed in are used to specify the
    ProtoRPC message class set on the MessageField.

    As with ProtoModel, creates a MessageFieldsSchema from the passed in fields,
    checks if this MessageFieldsSchema is already in the cache of collections,
    and returns the cached value if it exists.

    If not, will call ProtoModel with the collection_fields passed in to set
    the ProtoRPC message class on the items MessageField.

    Before returning it, it caches the newly created ProtoRPC message class in a
    cache of collections.

    Args:
      collection_fields: Optional fields, defaults to None. If None, the
          default from the class is used. If specified, will be converted to a
          MessageFieldsSchema object (and verified as such).

    Returns:
      The cached or created ProtoRPC (collection) message class specified by
          the fields.
    """
    if collection_fields is None:
      collection_fields = cls._message_fields_schema
    message_fields_schema = MessageFieldsSchema(collection_fields,
                                                basename=cls.__name__ + 'Proto')

    if message_fields_schema in cls._proto_collections:
      return cls._proto_collections[message_fields_schema]

    proto_model = cls.ProtoModel(fields=message_fields_schema)

    message_fields = {
        'items': messages.MessageField(proto_model, 1, repeated=True),
        'nextPageToken': messages.StringField(2),
        # TODO(dhermes): This behavior should be regulated more directly.
        #                This is to make sure the schema name in the discovery
        #                document is message_fields_schema.collection_name
        '__module__': '',
    }
    collection_class = type(message_fields_schema.collection_name,
                            (messages.Message,),
                            message_fields)
    cls._proto_collections[message_fields_schema] = collection_class
    return collection_class

  def ToMessage(self, fields=None):
    """Converts an entity to an ProtoRPC message.

    Uses the fields list passed in to create a ProtoRPC message class and then
    converts the relevant fields from the entity using ToValue.

    Args:
      fields: Optional fields, defaults to None. Passed to ProtoModel to
          create a ProtoRPC message class for the message.

    Returns:
      The ProtoRPC message created using the values from the entity and the
          fields provided for the message class.

    Raises:
      TypeError: if a repeated field has a value which is not a tuple or list.
    """
    proto_model = self.ProtoModel(fields=fields)

    proto_args = {}
    for field in proto_model.all_fields():
      name = field.name
      value_property = _VerifyProperty(self.__class__, name)

      # Since we are using getattr rather than checking self._values, this will
      # also work for properties which have a default set
      value = getattr(self, value_property._code_name)
      if value is None:
        continue

      if field.repeated:
        if not isinstance(value, (list, tuple)):
          error_msg = ('Property %s is a repeated field and its value should '
                       'be a list or tuple. Received: %s' % (name, value))
          raise TypeError(error_msg)

        to_add = [ToValue(value_property, element) for element in value]
      else:
        to_add = ToValue(value_property, value)
      proto_args[name] = to_add

    return proto_model(**proto_args)

  @classmethod
  def FromMessage(cls, message):
    """Converts a ProtoRPC message to an entity of the model class.

    Makes sure the message being converted is an instance of a ProtoRPC message
    class we have already encountered and then converts the relevant field
    values to the entity values using FromValue.

    When collecting the values from the message for conversion to an entity, NDB
    and alias properties are treated differently. The NDB properties can just be
    passed in to the class constructor as kwargs, but the alias properties must
    be set after the fact, and may even throw exceptions if the message has
    fields corresponding to alias properties which don't define a setter.

    Args:
      message: A ProtoRPC message.

    Returns:
      The entity of the current class that was created using the
          message field values.

    Raises:
      TypeError: if a message class is encountered that has not been stored in
          the _proto_models cache on the class. This is a precaution against
          unkown ProtoRPC message classes.
      TypeError: if a repeated field has a value which is not a tuple or list.
    """
    message_class = message.__class__

    # The CombinedContainer is a result of ResourceContainers.
    # Might need some better handling...
    if (message_class not in cls._proto_models.values() and
        message_class.__name__ != "CombinedContainer"):
      error_msg = ('The message is an instance of %s, which is a class this '
                   'EndpointsModel does not know how to process.' %
                   (message_class.__name__))
      raise TypeError(error_msg)

    entity_kwargs = {}
    alias_args = []

    for field in sorted(message_class.all_fields(),
                        key=lambda field: field.number):
      name = field.name
      value = getattr(message, name, None)
      if value is None:
        continue

      value_property = _VerifyProperty(cls, name)

      if field.repeated:
        if not isinstance(value, (list, tuple)):
          error_msg = ('Repeated attribute should be a list or tuple. '
                       'Received a %s.' % (value.__class__.__name__,))
          raise TypeError(error_msg)
        to_add = [FromValue(value_property, element) for element in value]
      else:
        to_add = FromValue(value_property, value)

      local_name = value_property._code_name
      if isinstance(value_property, EndpointsAliasProperty):
        alias_args.append((local_name, to_add))
      else:
        entity_kwargs[local_name] = to_add

    # Will not throw exception if a required property is not included. This
    # sort of exception is only thrown when attempting to put the entity.
    entity = cls(**entity_kwargs)

    # Set alias properties, will fail on an alias property if that
    # property was not defined with a setter
    for name, value in alias_args:
      setattr(entity, name, value)

    return entity

  @classmethod
  def ToMessageCollection(cls, items, collection_fields=None,
                          next_cursor=None):
    """Converts a list of entities and cursor to ProtoRPC (collection) message.

    Uses the fields list to create a ProtoRPC (collection) message class and
    then converts each item into a ProtoRPC message to be set as a list of
    items.

    If the cursor is not null, we convert it to a websafe string and set the
    nextPageToken field on the result message.

    Args:
      items: A list of entities of this model.
      collection_fields: Optional fields, defaults to None. Passed to
          ProtoCollection to create a ProtoRPC message class for for the
          collection of messages.
      next_cursor: An optional query cursor, defaults to None.

    Returns:
      The ProtoRPC message created using the entities and cursor provided,
          making sure that the entity message class matches collection_fields.
    """
    proto_model = cls.ProtoCollection(collection_fields=collection_fields)

    items_as_message = [item.ToMessage(fields=collection_fields)
                        for item in items]
    result = proto_model(items=items_as_message)

    if next_cursor is not None:
      result.nextPageToken = next_cursor.to_websafe_string()

    return result

  @classmethod
  @utils.positional(1)
  def method(cls,
             request_fields=None,
             response_fields=None,
             user_required=False,
             **kwargs):
    """Creates an API method decorator using provided metadata.

    Augments the endpoints.method decorator-producing function by allowing
    API methods to receive and return a class instance rather than having to
    worry with ProtoRPC messages (and message class definition). By specifying
    a list of ProtoRPC fields rather than defining the class, response and
    request classes can be defined on the fly.

    If there is any collision between request/response field lists and potential
    custom request/response message definitions that can be passed to the
    endpoints.method decorator, this call will fail.

    All other arguments will be passed directly to the endpoints.method
    decorator-producing function. If request/response field lists are used to
    define custom classes, the newly defined classes will also be passed to
    endpoints.method as the keyword arguments request_message/response_message.

    If a custom request message class is passed in, the resulting decorator will
    not attempt to convert the ProtoRPC message it receives into an
    EndpointsModel entity before passing it to the decorated method. Similarly,
    if a custom response message class is passed in, no attempt will be made to
    convert the object (returned by the decorated method) in the opposite
    direction.

    NOTE: Using utils.positional(1), we ensure the class instance will be the
    only positional argument hence won't have leaking/collision between the
    endpoints.method decorator function that we mean to pass metadata to.

    Args:
      request_fields: An (optional) list, tuple, dictionary or
          MessageFieldsSchema that defines a field ordering in a ProtoRPC
          message class. Defaults to None.
      response_fields: An (optional) list, tuple, dictionary or
          MessageFieldsSchema that defines a field ordering in a ProtoRPC
          message class. Defaults to None.
      user_required: Boolean; indicates whether or not a user is required on any
          incoming request.

    Returns:
      A decorator that takes the metadata passed in and augments an API method.

    Raises:
      TypeError: if there is a collision (either request or response) of
          field list and custom message definition.
    """
    request_message = kwargs.get(REQUEST_MESSAGE)
    if request_fields is not None and request_message is not None:
      raise TypeError('Received both a request message class and a field list '
                      'for creating a request message class.')
    if request_message is None:
      path = kwargs.get(PATH)
      query_fields = []
      if path is not None:
        query_fields = re.findall("{(.*?)}", path)
      if len(query_fields) > 0:
        kwargs[REQUEST_MESSAGE] = cls.ResourceContainer(
            message=cls.ProtoModel(fields=request_fields), fields=query_fields)
      else:
        kwargs[REQUEST_MESSAGE] = cls.ProtoModel(fields=request_fields)

    response_message = kwargs.get(RESPONSE_MESSAGE)
    if response_fields is not None and response_message is not None:
      raise TypeError('Received both a response message class and a field list '
                      'for creating a response message class.')
    if response_message is None:
      kwargs[RESPONSE_MESSAGE] = cls.ProtoModel(fields=response_fields)

    apiserving_method_decorator = endpoints.method(**kwargs)

    def RequestToEntityDecorator(api_method):
      """A decorator that uses the metadata passed to the enclosing method.

      Args:
        api_method: A method to be decorated. Expected signature is two
            positional arguments, an instance object of an API service and a
            variable containing a deserialized API request object, most likely
            as a ProtoRPC message or as an instance of the current
            EndpointsModel class.

      Returns:
        A decorated method that uses the metadata of the enclosing method to
            verify the service instance, convert the arguments to ones that can
            be consumed by the decorated method and serialize the method output
            back to a ProtoRPC message.
      """

      @functools.wraps(api_method)
      def EntityToRequestMethod(service_instance, request):
        """Stub method to be decorated.

        After creation, will be passed to the standard endpoints.method
        decorator to preserve the necessary method attributes needed for
        endpoints API methods.

        Args:
          service_instance: A ProtoRPC remove service instance.
          request: A ProtoRPC message.

        Returns:
          A ProtoRPC message, potentially serialized after being returned from a
              method which returns a class instance.

        Raises:
          endpoints.UnauthorizedException: if the user required boolean from
             the metadata is True and if there is no current endpoints user.
        """
        if user_required and endpoints.get_current_user() is None:
          raise endpoints.UnauthorizedException('Invalid token.')

        if request_message is None:
          # If we are using a fields list, we can convert the message to an
          # instance of the current class
          request = cls.FromMessage(request)

        # If developers are using request_fields to create a request message
        # class for them, their method should expect to receive an instance of
        # the current EndpointsModel class, and if it fails for some reason
        # their API users will receive a 503 from an uncaught exception.
        response = api_method(service_instance, request)

        if response_message is None:
          # If developers using a custom request message class with
          # response_fields to create a response message class for them, it is
          # up to them to return an instance of the current EndpointsModel
          # class. If not, their API users will receive a 503 from an uncaught
          # exception.
          response = response.ToMessage(fields=response_fields)

        return response

      return apiserving_method_decorator(EntityToRequestMethod)

    return RequestToEntityDecorator

  @classmethod
  @utils.positional(1)
  def query_method(cls,
                   query_fields=(),
                   collection_fields=None,
                   limit_default=QUERY_LIMIT_DEFAULT,
                   limit_max=QUERY_LIMIT_MAX,
                   user_required=False,
                   use_projection=False,
                   **kwargs):
    """Creates an API query method decorator using provided metadata.

    This will produce a decorator which is solely intended to decorate functions
    which receive queries and expect them to be decorated. Augments the
    endpoints.method decorator-producing function by allowing API methods to
    receive and return a query object.

    Query data will be stored in an entity using the same (de)serialization
    methods used by the classmethod "method". Once there, the query info
    object on the entity will allow conversion into a query and the decorator
    will execute this query.

    Rather than request/response fields (as in "method"), we require that
    callers specify query fields -- which will produce the entity before it
    is converted to a query -- and collection fields -- which will be passed
    to ProtoCollection to create a container class for items returned by the
    query.

    In contrast to "method", no custom request/response message classes can be
    passed in, the queries and collection responses can only be specified by the
    query/collection fields. THIS IS SUBJECT TO CHANGE.

    All other arguments will be passed directly to the endpoints.method
    decorator-producing function. The custom classes defined by the
    query/collection fields will also be passed to endpoints.method as the
    keyword arguments request_message/response_message.

    Custom {EndpointsAliasProperty}s have been defined that allow for
    customizing queries:
      limit: allows a limit to be passed in and augment the query info on the
          deserialized entity.
      order: allows an order to be passed in and augment the query info on the
          deserialized entity.
      pageToken: allows a websafe string value to be converted to a cursor and
          set on the query info of the deserialized entity.

    NOTE: Using utils.positional(1), we ensure the class instance will be the
    only positional argument hence won't have leaking/collision between the
    endpoints.method decorator function that we mean to pass metadata to.

    Args:
      query_fields: An (optional) list, tuple, dictionary or MessageFieldsSchema
          that define a field ordering in a ProtoRPC message class. Defaults to
          an empty tuple, which results in a simple datastore query of the kind.
      collection_fields: An (optional) list, tuple, dictionary or
          MessageFieldsSchema that define a field ordering in a ProtoRPC
          message class. Defaults to None.
      limit_default: An (optional) default value for the amount of items to
          fetch in a query. Defaults to the global QUERY_LIMIT_DEFAULT.
      limit_max: An (optional) max value for the amount of items to
          fetch in a query. Defaults to the global QUERY_LIMIT_MAX.
      user_required: Boolean; indicates whether or not a user is required on any
          incoming request. Defaults to False.
      use_projection: Boolean; indicates whether or the query should retrieve
          entire entities or just a projection using the collection fields.
          Defaults to False. If used, all properties in a projection must be
          indexed, so this should be used with care. However, when used
          correctly, this will speed up queries, reduce payload size and even
          reduce cost at times.

    Returns:
      A decorator that takes the metadata passed in and augments an API query
          method. The decorator will perform the fetching, the decorated method
          simply need return the augmented query object.

    Raises:
      TypeError: if there is a custom request or response message class was
          passed in.
      TypeError: if a http_method other than 'GET' is passed in.
    """
    if REQUEST_MESSAGE in kwargs:
      raise TypeError('Received a request message class on a method intended '
                      'for queries. This is explicitly not allowed. Only '
                      'query_fields can be specified.')

    kwargs[REQUEST_MESSAGE] = cls.ResourceContainer(fields=query_fields)

    if RESPONSE_MESSAGE in kwargs:
      raise TypeError('Received a response message class on a method intended '
                      'for queries. This is explicitly not allowed. Only '
                      'collection_fields can be specified.')
    kwargs[RESPONSE_MESSAGE] = cls.ProtoCollection(
        collection_fields=collection_fields)

    # Only allow GET for queries
    if HTTP_METHOD in kwargs:
      if kwargs[HTTP_METHOD] != QUERY_HTTP_METHOD:
        raise TypeError('Query requests must use the HTTP GET methods. '
                        'Received %s.' % (kwargs[HTTP_METHOD],))
    kwargs[HTTP_METHOD] = QUERY_HTTP_METHOD

    apiserving_method_decorator = endpoints.method(**kwargs)

    def RequestToQueryDecorator(api_method):
      """A decorator that uses the metadata passed to the enclosing method.

      Args:
        api_method: A method to be decorated. Expected signature is two
            positional arguments, an instance object of an API service and a
            variable containing a deserialized API request object, required here
            to be an NDB query object with kind set to the current
            EndpointsModel class.

      Returns:
        A decorated method that uses the metadata of the enclosing method to
            verify the service instance, convert the arguments to ones that can
            be consumed by the decorated method and serialize the method output
            back to a ProtoRPC (collection) message.
      """

      @functools.wraps(api_method)
      def QueryFromRequestMethod(service_instance, request):
        """Stub method to be decorated.

        After creation, will be passed to the standard endpoints.method
        decorator to preserve the necessary method attributes needed for
        endpoints API methods.

        Args:
          service_instance: A ProtoRPC remove service instance.
          request: A ProtoRPC message.

        Returns:
          A ProtoRPC (collection) message, serialized after being returned from
              an NDB query and containing the cursor if there are more results
              and a cursor was returned.

        Raises:
          endpoints.UnauthorizedException: if the user required boolean from
             the metadata is True and if there is no current endpoints user.
          endpoints.ForbiddenException: if the limit passed in through the
             request exceeds the maximum allowed.
        """
        if user_required and endpoints.get_current_user() is None:
          raise endpoints.UnauthorizedException('Invalid token.')

        request_entity = cls.FromMessage(request)
        query_info = request_entity._endpoints_query_info
        query_info.SetQuery()

        # Allow the caller to update the query
        query = api_method(service_instance, query_info.query)

        # Use limit on query info or default if none was set
        request_limit = query_info.limit or limit_default
        if request_limit > limit_max:
          raise endpoints.ForbiddenException(
              QUERY_MAX_EXCEEDED_TEMPLATE % (request_limit, limit_max))

        query_options = {'start_cursor': query_info.cursor}
        if use_projection:
          projection = [value for value in collection_fields
                        if value in cls._properties]
          query_options['projection'] = projection
        items, next_cursor, more_results = query.fetch_page(
            request_limit, **query_options)

        # Don't pass a cursor if there are no more results
        if not more_results:
          next_cursor = None

        return cls.ToMessageCollection(items,
                                       collection_fields=collection_fields,
                                       next_cursor=next_cursor)

      return apiserving_method_decorator(QueryFromRequestMethod)

    return RequestToQueryDecorator
# Update base class global so EndpointsMetaModel can check subclasses against it
BASE_MODEL_CLASS = EndpointsModel

########NEW FILE########
__FILENAME__ = properties
# Copyright 2012 Google Inc. All Rights Reserved.

"""Custom properties for hybrid NDB/ProtoRPC models.

Custom properties are defined to allow custom interactions with complex
types and custom serialization of these values into ProtoRPC fields.

Defined here:
  EndpointsAliasProperty:
    A local only property used for including custom properties in messages
    without having to persist these properties in the datastore and for creating
    custom setters based on values parsed from requests.
  EndpointsUserProperty:
    For getting the user the same way an endpoints method does.
  EndpointsDateTimeProperty,EndpointsDateProperty,EndpointsTimeProperty:
    For custom serialization of date and/or time stamps.
  EndpointsVariantIntegerProperty,EndpointsVariantFloatProperty:
    For allowing ProtoRPC type variants for fields which allow it, e.g. a 32-bit
    integer instead of the default 64-bit.
  EndpointsComputedProperty:
    a subclass of ndb.ComputedProperty; this property class is needed since one
    cannot readily determine the type desired of the output.
"""

import datetime
import warnings
warnings.simplefilter('default')  # To allow DeprecationWarning

from . import utils as ndb_utils
from .. import utils

import endpoints

from protorpc import messages
from google.appengine.ext import ndb


__all__ = [
    'EndpointsAliasProperty', 'EndpointsUserProperty',
    'EndpointsDateTimeProperty', 'EndpointsDateProperty',
    'EndpointsTimeProperty', 'EndpointsVariantIntegerProperty',
    'EndpointsVariantFloatProperty', 'EndpointsComputedProperty',
]


DEFAULT_PROPERTY_TYPE = messages.StringField
DATETIME_STRING_FORMAT = utils.DATETIME_STRING_FORMAT
DATE_STRING_FORMAT = utils.DATE_STRING_FORMAT
TIME_STRING_FORMAT = utils.TIME_STRING_FORMAT


def ComputedPropertyToProto(prop, index):
  """Converts a computed property to the corresponding message field.

  Args:
    prop: The NDB property to be converted.
    index: The index of the property within the message.

  Returns:
    A ProtoRPC field. If the property_type of prop is a field, then a field of
        that type will be returned. If the property_type of prop is an enum
        class, then an enum field using that enum class is returned. If the
        property_type of prop is a message class, then a message field using
        that message class is returned.

  Raises:
    TypeError: if the property_type manages to pass CheckValidPropertyType
        without an exception but does not match any of the parent types
        messages.Field, messages.Enum or messages.Message. NOTE: This should
        not occur, given the behavior of CheckValidPropertyType.
  """
  kwargs = ndb_utils.GetKeywordArgs(prop)
  property_type = prop.property_type

  utils.CheckValidPropertyType(property_type)

  if utils.IsSubclass(property_type, messages.Field):
    return property_type(index, **kwargs)
  elif utils.IsSubclass(property_type, messages.Enum):
    return messages.EnumField(property_type, index, **kwargs)
  elif utils.IsSubclass(property_type, messages.Message):
    # No default for {MessageField}s
    kwargs.pop('default', None)
    return messages.MessageField(property_type, index, **kwargs)
  else:
    # Should never occur due to utils.CheckValidPropertyType.
    raise TypeError('Unexpected property type: %s.' % (property_type,))


class EndpointsAliasProperty(property):
  """A custom property that also considers the type of the response.

  Allows Python properties to be used in an EndpointsModel by also
  specifying a property type. These properties can be derived from the rest
  of the model and included in a ProtoRPC message definition, but will not need
  to be persisted in the datastore.

  This class can be used directly to define properties or as a decorator.

  Attributes:
    message_field: a value used to register the property in the property class
        to proto dictionary for any model class with this property. The method
        ComputedPropertyToProto is used here.
  """
  message_field = ComputedPropertyToProto

  @utils.positional(2)
  def __init__(self, func=None, setter=None, fdel=None, doc=None,
               repeated=False, required=False, default=None, name=None,
               variant=None, property_type=DEFAULT_PROPERTY_TYPE):
    """Constructor for property.

    Attributes:
      __saved_property_args: A dictionary that can be stored on the instance if
          used as a decorator rather than directly as a property.
      __initialized: A boolean corresponding to whether or not the instance has
          completed initialization or needs to continue when called as a
          decorator.
      _required: A boolean attribute for ProtoRPC conversion, denoting whether
          this property is required in a message class.
      _repeated: A boolean attribute for ProtoRPC conversion, denoting whether
          this property is repeated in a message class.
      _name: The true name of the property.
      _code_name: The attribute name of the property on the model that
          instantiated it.
      _variant: An optional variant that can be used for ProtoRPC conversion,
          since some ProtoRPC fields allow variants. Will not always be set on
          alias properties.
      property_type: A ProtoRPC field, message class or enum class that
          describes the output of the alias property.

    Args:
      func: The method that outputs the value of the property. If None,
          we use this as a signal the instance is being used as a decorator.
      setter: The (optional) method that will allow the property to be set.
          Passed to the property constructor as fset. Defaults to None.
      fdel: The (optional) method that will be called when the property is
          deleted. Passed to the property constructor as fdel. Defaults to None.
      doc: The (optional) docstring for the property. Defaults to None.
      repeated: Optional boolean, defaults to False. Indicates whether or not
          the ProtoRPC field is repeated.
      required: Optional boolean, defaults to False. Indicates whether or not
          the ProtoRPC field should be required.
      default: Optional default value for the property. Only set on the property
          instance if not None. Will be validated when a corresponding message
          field is created.
      name: A custom name that can be used to describe the property.
      variant: A variant of that can be used to augment the ProtoRPC field. Will
          be validated when a corresponding message field is created.
      property_type: A ProtoRPC field, message class or enum class that
          describes the output of the alias property.
    """
    self._required = required
    self._repeated = repeated
    self._name = name
    self._code_name = None

    if default is not None:
      self._default = default

    if variant is not None:
      self._variant = variant

    utils.CheckValidPropertyType(property_type)
    self.property_type = property_type

    property_args = {'fset': setter, 'fdel': fdel, 'doc': doc}
    if func is None:
      self.__initialized = False
      self.__saved_property_args = property_args
    else:
      self.__initialized = True
      super(EndpointsAliasProperty, self).__init__(func, **property_args)

  def __call__(self, func):
    """Callable method to be used when instance is used as a decorator.

    If called as a decorator, passes the saved keyword arguments and the func
    to the constructor to complete initialization.

    Args:
      func: The method that outputs the value of the property.

    Returns:
      The property instance.

    Raises:
      TypeError: if the instance has already been initialized, either directly
          as a property or as a decorator elsewhere.
    """
    if self.__initialized:
      raise TypeError('EndpointsAliasProperty is not callable.')

    super(EndpointsAliasProperty, self).__init__(func,
                                                 **self.__saved_property_args)
    del self.__saved_property_args

    # Return the property created
    return self

  def _FixUp(self, code_name):
    """Internal helper called to tell the property its name.

    Intended to allow a similar name interface as provided by NDB properties.
    Used during class creation in EndpointsMetaModel.

    Args:
      code_name: The attribute name of the property as set on a class.
    """
    self._code_name = code_name
    if self._name is None:
      self._name = self._code_name


class EndpointsUserProperty(ndb.UserProperty):
  """A custom user property for interacting with user ID tokens.

  Uses the tools provided in the endpoints module to detect the current user.
  In addition, has an optional parameter raise_unauthorized which will return
  a 401 to the endpoints API request if a user can't be detected.
  """

  def __init__(self, *args, **kwargs):
    """Constructor for User property.

    NOTE: Have to pop custom arguments from the keyword argument dictionary
    to avoid corrupting argument order when sent to the superclass.

    Attributes:
      _raise_unauthorized: An optional boolean, defaulting to False. If True,
         the property will return a 401 to the API request if a user can't
         be deteced.
    """
    self._raise_unauthorized = kwargs.pop('raise_unauthorized', False)
    super(EndpointsUserProperty, self).__init__(*args, **kwargs)

  def _set_value(self, entity, value):
    """Internal helper to set value on model entity.

    If the value to be set is null, will try to retrieve the current user and
    will return a 401 if a user can't be found and raise_unauthorized is True.

    Args:
      entity: An instance of some NDB model.
      value: The value of this property to be set on the instance.
    """
    if value is None:
      value = endpoints.get_current_user()
      if self._raise_unauthorized and value is None:
        raise endpoints.UnauthorizedException('Invalid token.')
    super(EndpointsUserProperty, self)._set_value(entity, value)

  def _fix_up(self, cls, code_name):
    """Internal helper called to register the property with the model class.

    Overrides the _set_attributes method on the model class to interject this
    attribute in to the keywords passed to it. Since the method _set_attributes
    is called by the model class constructor to set values, this -- in congress
    with the custom defined _set_value -- will make sure this property always
    gets set when an instance is created, even if not passed in.

    Args:
      cls: The model class that owns the property.
      code_name: The name of the attribute on the model class corresponding
          to the property.
    """
    original_set_attributes = cls._set_attributes

    def CustomSetAttributes(setattr_self, kwds):
      """Custom _set_attributes which makes sure this property is always set."""
      if self._code_name not in kwds:
        kwds[self._code_name] = None
      original_set_attributes(setattr_self, kwds)

    cls._set_attributes = CustomSetAttributes
    super(EndpointsUserProperty, self)._fix_up(cls, code_name)


class EndpointsDateTimeProperty(ndb.DateTimeProperty):
  """A custom datetime property.

  Allows custom serialization of a datetime.datetime stamp when used to create
  a message field.
  """

  def __init__(self, *args, **kwargs):
    """Constructor for datetime property.

    NOTE: Have to pop custom arguments from the keyword argument dictionary
    to avoid corrupting argument order when sent to the superclass.

    Attributes:
      _string_format: An optional string, defaulting to DATETIME_STRING_FORMAT.
         This is used to serialize using strftime and deserialize using strptime
         when the datetime stamp is turned into a message.
    """
    self._string_format = kwargs.pop('string_format', DATETIME_STRING_FORMAT)
    super(EndpointsDateTimeProperty, self).__init__(*args, **kwargs)

  def ToValue(self, value):
    """A custom method to override the typical ProtoRPC message serialization.

    Uses the string_format set on the property to serialize the datetime stamp.

    Args:
      value: A datetime stamp, the value of the property.

    Returns:
      The serialized string value of the datetime stamp.
    """
    return value.strftime(self._string_format)

  def FromValue(self, value):
    """A custom method to override the typical ProtoRPC message deserialization.

    Uses the string_format set on the property to deserialize the datetime
    stamp.

    Args:
      value: A serialized datetime stamp as a string.

    Returns:
      The deserialized datetime.datetime stamp.
    """
    return datetime.datetime.strptime(value, self._string_format)


class EndpointsDateProperty(ndb.DateProperty):
  """A custom date property.

  Allows custom serialization of a datetime.date stamp when used to create a
  message field.
  """

  def __init__(self, *args, **kwargs):
    """Constructor for date property.

    NOTE: Have to pop custom arguments from the keyword argument dictionary
    to avoid corrupting argument order when sent to the superclass.

    Attributes:
      _string_format: An optional string, defaulting to DATE_STRING_FORMAT. This
         is used to serialize using strftime and deserialize using strptime when
         the date stamp is turned into a message.
    """
    self._string_format = kwargs.pop('string_format', DATE_STRING_FORMAT)
    super(EndpointsDateProperty, self).__init__(*args, **kwargs)

  def ToValue(self, value):
    """A custom method to override the typical ProtoRPC message serialization.

    Uses the string_format set on the property to serialize the date stamp.

    Args:
      value: A date stamp, the value of the property.

    Returns:
      The serialized string value of the date stamp.
    """
    return value.strftime(self._string_format)

  def FromValue(self, value):
    """A custom method to override the typical ProtoRPC message deserialization.

    Uses the string_format set on the property to deserialize the date stamp.

    Args:
      value: A serialized date stamp as a string.

    Returns:
      The deserialized datetime.date stamp.
    """
    return datetime.datetime.strptime(value, self._string_format).date()


class EndpointsTimeProperty(ndb.TimeProperty):
  """A custom time property.

  Allows custom serialization of a datetime.time stamp when used to create a
  message field.
  """

  def __init__(self, *args, **kwargs):
    """Constructor for time property.

    NOTE: Have to pop custom arguments from the keyword argument dictionary
    to avoid corrupting argument order when sent to the superclass.

    Attributes:
      string_format: An optional string, defaulting to TIME_STRING_FORMAT. This
         is used to serialize using strftime and deserialize using strptime when
         the time stamp is turned into a message.
    """
    self._string_format = kwargs.pop('string_format', TIME_STRING_FORMAT)
    super(EndpointsTimeProperty, self).__init__(*args, **kwargs)

  def ToValue(self, value):
    """A custom method to override the typical ProtoRPC message serialization.

    Uses the string_format set on the property to serialize the date stamp.

    Args:
      value: A date stamp, the value of the property.

    Returns:
      The serialized string value of the time stamp.
    """
    return value.strftime(self._string_format)

  def FromValue(self, value):
    """A custom method to override the typical ProtoRPC message deserialization.

    Uses the string_format set on the property to deserialize the time stamp.

    Args:
      value: A serialized time stamp as a string.

    Returns:
      The deserialized datetime.time stamp.
    """
    return datetime.datetime.strptime(value, self._string_format).time()


class EndpointsVariantIntegerProperty(ndb.IntegerProperty):
  """A custom integer property.

  Allows custom serialization of a integers by allowing variant types when used
  to create a message field.
  """

  def __init__(self, *args, **kwargs):
    """Constructor for integer property.

    NOTE: Have to pop custom arguments from the keyword argument dictionary
    to avoid corrupting argument order when sent to the superclass.

    Attributes:
      variant: A variant of integer types, defaulting to the default variant for
          a ProtoRPC IntegerField.
    """
    # The value of variant will be verified when the message field is created
    self._variant = kwargs.pop('variant', messages.IntegerField.DEFAULT_VARIANT)
    super(EndpointsVariantIntegerProperty, self).__init__(*args, **kwargs)


class EndpointsVariantFloatProperty(ndb.FloatProperty):
  """A custom float property.

  Allows custom serialization of a float by allowing variant types when used
  to create a message field.
  """

  def __init__(self, *args, **kwargs):
    """Constructor for float property.

    NOTE: Have to pop custom arguments from the keyword argument dictionary
    to avoid corrupting argument order when sent to the superclass.

    Attributes:
      variant: A variant of float types, defaulting to the default variant for
          a ProtoRPC FloatField.
    """
    # The value of variant be verified when the message field is created
    self._variant = kwargs.pop('variant', messages.FloatField.DEFAULT_VARIANT)
    super(EndpointsVariantFloatProperty, self).__init__(*args, **kwargs)


class EndpointsComputedProperty(ndb.ComputedProperty):
  """A custom computed property that also considers the type of the response.

  Allows NDB computed properties to be used in an EndpointsModel by also
  specifying a property type.

  This class can be used directly to define properties or as a decorator.

  Attributes:
    message_field: a value used to register the property in the property class
        to proto dictionary for any model class with this property. The method
        ComputedPropertyToProto is used here.
  """
  message_field = ComputedPropertyToProto

  @utils.positional(2)
  def __init__(self, func=None, **kwargs):
    """Constructor for computed property.

    NOTE: Have to pop custom arguments from the keyword argument dictionary
    to avoid corrupting argument order when sent to the superclass.

    Attributes:
      _variant: A variant of that can be used to augment the ProtoRPC field.
      property_type: A ProtoRPC field, message class or enum class that
          describes the output of the alias property.
      __saved_kwargs: A dictionary that can be stored on the instance if used
          as a decorator rather than directly as a property.
      __initialized: A boolean corresponding to whether or not the instance has
          completed initialization or needs to continue when called as a
          decorator.

    Args:
      func: The method that outputs the value of the computed property. If None,
          we use this as a signal the instance is being used as a decorator.
    """
    variant = kwargs.pop('variant', None)
    # The value of variant will be verified when the message field is created
    if variant is not None:
      self._variant = variant

    property_type = kwargs.pop('property_type', DEFAULT_PROPERTY_TYPE)
    utils.CheckValidPropertyType(property_type)
    self.property_type = property_type

    if func is None:
      self.__initialized = False
      self.__saved_kwargs = kwargs
    else:
      self.__initialized = True
      super(EndpointsComputedProperty, self).__init__(func, **kwargs)

  def __call__(self, func):
    """Callable method to be used when instance is used as a decorator.

    If called as a decorator, passes the saved keyword arguments and the func
    to the constructor to complete initialization.

    Args:
      func: The method that outputs the value of the computed property.

    Returns:
      The property instance.

    Raises:
      TypeError: if the instance has already been initialized, either directly
          as a property or as a decorator elsewhere.
    """
    if self.__initialized:
      raise TypeError('EndpointsComputedProperty is not callable.')

    super(EndpointsComputedProperty, self).__init__(func, **self.__saved_kwargs)
    del self.__saved_kwargs

    # Return the property created
    return self

  def _set_value(self, unused_entity, unused_value):
    """Internal helper to set a value in an entity for a ComputedProperty.

    Typically, on a computed property, an ndb.model.ComputedPropertyError
    exception is raised when we try to set the property.

    In endpoints, since we will be deserializing messages to entities, we want
    to be able to call entity.some_computed_property_name = some_value without
    halting code, hence this will simply do nothing.
    """
    warnings.warn('Cannot assign to a ComputedProperty.', DeprecationWarning)

########NEW FILE########
__FILENAME__ = utils
# Copyright 2012 Google Inc. All Rights Reserved.

"""Utility module for converting NDB properties to ProtoRPC messages/fields.

In the dictionary NDB_PROPERTY_TO_PROTO, each property defined by NDB is
registered. The registry values can either be a ProtoRPC field for simple
types/properties or a custom method for converting a property into a
ProtoRPC field.

Some properties have no corresponding implementation. These fields are
registered with a method that will raise a NotImplementedError. As of right now,
these are:
  Property -- this is the base property class and shouldn't be used
  GenericProperty -- this does not play nicely with strongly typed messages
  ModelKey -- this is only intended for the key of the instance, and doesn't
              make sense to send in messages
  ComputedProperty -- a variant of this class is needed to determine the type
                      desired of the output. Such a variant is provided in
                      properties
"""

from .. import utils

from protorpc import messages

from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop


__all__ = []


GeoPtMessage = utils.GeoPtMessage
RaiseNotImplementedMethod = utils.RaiseNotImplementedMethod
UserMessage = utils.UserMessage

MODEL_KEY_EXPLANATION = (
    'A model key property can\'t be used to define an EndpointsModel. These '
    'are intended to be used as the lone key of an entity and all ModelKey '
    'properties on an entity will have the same value.')
COMPUTED_PROPERTY_EXPLANATION = (
    'A computed property can\'t be used to define an EndpointsModel. The type '
    'of the message field must be explicitly named; this can be done by using '
    'the property EndpointsComputedProperty.')

NDB_PROPERTY_TO_PROTO = {
    ndb.BlobKeyProperty: messages.StringField,
    ndb.BlobProperty: messages.BytesField,  # No concept of compressed here
    ndb.BooleanProperty: messages.BooleanField,
    ndb.ComputedProperty: RaiseNotImplementedMethod(
        ndb.ComputedProperty,
        explanation=COMPUTED_PROPERTY_EXPLANATION),
    ndb.DateProperty: messages.StringField,
    ndb.DateTimeProperty: messages.StringField,
    ndb.FloatProperty: messages.FloatField,
    ndb.GenericProperty: RaiseNotImplementedMethod(ndb.GenericProperty),
    ndb.IntegerProperty: messages.IntegerField,
    ndb.JsonProperty: messages.BytesField,
    ndb.KeyProperty: messages.StringField,
    ndb.ModelKey: RaiseNotImplementedMethod(
        ndb.ModelKey,
        explanation=MODEL_KEY_EXPLANATION),
    ndb.PickleProperty: messages.BytesField,
    ndb.Property: RaiseNotImplementedMethod(ndb.Property),
    ndb.StringProperty: messages.StringField,
    ndb.TextProperty: messages.StringField,  # No concept of compressed here
    ndb.TimeProperty: messages.StringField,
}


def GetKeywordArgs(prop, include_default=True):
  """Captures attributes from an NDB property to be passed to a ProtoRPC field.

  Args:
    prop: The NDB property which will have its attributes captured.
    include_default: An optional boolean indicating whether or not the default
        value of the property should be included. Defaults to True, and is
        intended to be turned off for special ProtoRPC fields which don't take
        a default.

  Returns:
    A dictionary of attributes, intended to be passed to the constructor of a
        ProtoRPC field as keyword arguments.
  """
  kwargs = {
      'required': prop._required,
      'repeated': prop._repeated,
  }
  if include_default and hasattr(prop, '_default'):
    kwargs['default'] = prop._default
  if hasattr(prop, '_variant'):
    kwargs['variant'] = prop._variant
  return kwargs


def MessageFromSimpleField(field, prop, index):
  """Converts a property to the corresponding field of specified type.

  Assumes index is the only positional argument needed to create an instance
  of {field}, hence only simple fields will work and an EnumField or
  MessageField will fail.

  Args:
    field: A ProtoRPC field type.
    prop: The NDB property to be converted.
    index: The index of the property within the message.

  Returns:
    An instance of field with attributes corresponding to those in prop and
        index corresponding to that which was passed in.
  """
  return field(index, **GetKeywordArgs(prop))


def StructuredPropertyToProto(prop, index):
  """Converts a structured property to the corresponding message field.

  Args:
    prop: The NDB property to be converted.
    index: The index of the property within the message.

  Returns:
    A message field with attributes corresponding to those in prop, index
        corresponding to that which was passed in and with underlying message
        class equal to the message class produced by the model class, which
        should be a subclass of EndpointsModel.

  Raises:
    TypeError if the model class of the property does not have a callable
        ProtoModel method. This is because we expected a subclass of
        EndpointsModel set on the structured property.
  """
  modelclass = prop._modelclass
  try:
    property_proto_method = modelclass.ProtoModel
    property_proto = property_proto_method()
  except (AttributeError, TypeError):
    error_msg = ('Structured properties must receive a model class with a '
                 'callable ProtoModel attribute. The class %s has no such '
                 'attribute.' % (modelclass.__name__,))
    raise TypeError(error_msg)

  # No default for {MessageField}s
  kwargs = GetKeywordArgs(prop, include_default=False)
  return messages.MessageField(property_proto, index, **kwargs)
NDB_PROPERTY_TO_PROTO[ndb.StructuredProperty] = StructuredPropertyToProto
# Ignore fact that LocalStructuredProperty is just a blob in the datastore
NDB_PROPERTY_TO_PROTO[ndb.LocalStructuredProperty] = StructuredPropertyToProto


def EnumPropertyToProto(prop, index):
  """Converts an enum property from a model to a message field.

  Args:
    prop: The NDB enum property to be converted.
    index: The index of the property within the message.

  Returns:
    An enum field with attributes corresponding to those in prop, index
        corresponding to that which was passed in and with underlying enum type
        equal to the enum type set in the enum property.
  """
  enum = prop._enum_type
  kwargs = GetKeywordArgs(prop)
  return messages.EnumField(enum, index, **kwargs)
NDB_PROPERTY_TO_PROTO[msgprop.EnumProperty] = EnumPropertyToProto


def MessagePropertyToProto(prop, index):
  """Converts a message property from a model to a message field.

  Args:
    prop: The NDB message property to be converted.
    index: The index of the property within the message.

  Returns:
    A message field with attributes corresponding to those in prop, index
        corresponding to that which was passed in and with underlying message
        class equal to the message type set in the message property.
  """
  message_type = prop._message_type
  # No default for {MessageField}s
  kwargs = GetKeywordArgs(prop, include_default=False)
  return messages.MessageField(message_type, index, **kwargs)
NDB_PROPERTY_TO_PROTO[msgprop.MessageProperty] = MessagePropertyToProto


def GeoPtPropertyToProto(prop, index):
  """Converts a model property to a Geo Point message field.

  Args:
    prop: The NDB property to be converted.
    index: The index of the property within the message.

  Returns:
    A message field with attributes corresponding to those in prop, index
        corresponding to that which was passed in and with underlying message
        class equal to GeoPtMessage.
  """
  # No default for {MessageField}s
  kwargs = GetKeywordArgs(prop, include_default=False)
  return messages.MessageField(GeoPtMessage, index, **kwargs)
NDB_PROPERTY_TO_PROTO[ndb.GeoPtProperty] = GeoPtPropertyToProto


def UserPropertyToProto(prop, index):
  """Converts a model property to a user message field.

  Args:
    prop: The NDB property to be converted.
    index: The index of the property within the message.

  Returns:
    A message field with attributes corresponding to those in prop, index
        corresponding to that which was passed in and with underlying message
        class equal to UserMessage.
  """
  # No default for {MessageField}s
  kwargs = GetKeywordArgs(prop, include_default=False)
  return messages.MessageField(UserMessage, index, **kwargs)
NDB_PROPERTY_TO_PROTO[ndb.UserProperty] = UserPropertyToProto

########NEW FILE########
__FILENAME__ = test_utils
# Copyright 2013 Google Inc. All Rights Reserved.

"""Utility module for tests.

NOTE: The which method below is borrowed from a project with a different
LICENSE. See README.md for this project for more details.
"""


import os


PATH_ENV_VAR = 'PATH'
# Used by Windows to add potential extensions to scripts on path
PATH_EXTENSIONS_ENV_VAR = 'PATHEXT'


def which(name, flags=os.X_OK):
    """Search PATH for executable files with the given name.

    On newer versions of MS-Windows, the PATHEXT environment variable will be
    set to the list of file extensions for files considered executable. This
    will normally include things like ".EXE". This fuction will also find files
    with the given name ending with any of these extensions.

    On MS-Windows the only flag that has any meaning is os.F_OK. Any other
    flags will be ignored.

    NOTE: Adapted from the Twisted project:
    ('https://twistedmatrix.com/trac/browser/tags/releases/twisted-8.2.0/'
     'twisted/python/procutils.py')

    Args:
      name: String; the name for which to search.
      flags: Integer; arguments to os.access.

    Returns:
      String containing the full path of the named file combined with one
        of the directory choices on PATH (optionally with an extension added).
        If the script is not on the path, None is returned.
    """
    result = []

    path_extension = os.getenv(PATH_EXTENSIONS_ENV_VAR, '')
    valid_extensions = [extension
                        for extension in path_extension.split(os.pathsep)
                        if extension]

    path = os.getenv(PATH_ENV_VAR)
    if path is None:
        return

    for directory_on_path in path.split(os.pathsep):
        potential_match = os.path.join(directory_on_path, name)

        # Unix
        if os.access(potential_match, flags):
            return potential_match

        # Windows helper
        for extension in valid_extensions:
            potential_match_with_ext = potential_match + extension
            if os.access(potential_match_with_ext, flags):
                return potential_match_with_ext

    return result

########NEW FILE########
__FILENAME__ = utils
# Copyright 2012 Google Inc. All Rights Reserved.

"""Utility module for converting properties to ProtoRPC messages/fields.

The methods here are not specific to NDB or DB (the datastore APIs) and can
be used by utility methods in the datastore API specific code.
"""

__all__ = ['GeoPtMessage', 'MessageFieldsSchema', 'UserMessage',
           'method', 'positional', 'query_method']


import datetime

from protorpc import messages
from protorpc import util as protorpc_util

from google.appengine.api import users


ALLOWED_DECORATOR_NAME = frozenset(['method', 'query_method'])
DATETIME_STRING_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
DATE_STRING_FORMAT = '%Y-%m-%d'
TIME_STRING_FORMAT = '%H:%M:%S.%f'

positional = protorpc_util.positional


def IsSubclass(candidate, parent_class):
  """Calls issubclass without raising an exception.

  Args:
    candidate: A candidate to check if a subclass.
    parent_class: A class or tuple of classes representing a potential parent.

  Returns:
    A boolean indicating whether or not candidate is a subclass of parent_class.
  """
  try:
    return issubclass(candidate, parent_class)
  except TypeError:
    return False


def IsSimpleField(property_type):
  """Checks if a property type is a "simple" ProtoRPC field.

  We consider "simple" ProtoRPC fields to be ones which are not message/enum
  fields, since those depend on extra data when defined.

  Args:
    property_type: A ProtoRPC field.

  Returns:
    A boolean indicating whether or not the passed in property type is a
        simple field.
  """
  if IsSubclass(property_type, messages.Field):
    return property_type not in (messages.EnumField, messages.MessageField)

  return False


def CheckValidPropertyType(property_type, raise_invalid=True):
  """Checks if a property type is a valid class.

  Here "valid" means the property type is either a simple field, a ProtoRPC
  enum class which can be used to define an EnumField or a ProtoRPC message
  class that can be used to define a MessageField.

  Args:
    property_type: A ProtoRPC field, message class or enum class that
        describes the output of the alias property.
    raise_invalid: Boolean indicating whether or not an exception should be
        raised if the given property is not valid. Defaults to True.

  Returns:
    A boolean indicating whether or not the passed in property type is valid.
        NOTE: Only returns if raise_invalid is False.

  Raises:
    TypeError: If raise_invalid is True and the passed in property is not valid.
  """
  is_valid = IsSimpleField(property_type)
  if not is_valid:
    is_valid = IsSubclass(property_type, (messages.Enum, messages.Message))

  if not is_valid and raise_invalid:
    error_msg = ('Property field must be either a subclass of a simple '
                 'ProtoRPC field, a ProtoRPC enum class or a ProtoRPC message '
                 'class. Received %r.' % (property_type,))
    raise TypeError(error_msg)

  return is_valid


def _DictToTuple(to_sort):
  """Converts a dictionary into a tuple of keys sorted by values.

  Args:
    to_sort: A dictionary like object that has a callable items method.

  Returns:
    A tuple containing the dictionary keys, sorted by value.
  """
  items = to_sort.items()
  items.sort(key=lambda pair: pair[1])
  return tuple(pair[0] for pair in items)


class MessageFieldsSchema(object):
  """A custom dictionary which is hashable.

  Intended to be used so either dictionaries or lists can be used to define
  field index orderings of a ProtoRPC message classes. Since hashable, we can
  cache these ProtoRPC message class definitions using the fields schema
  as a key.

  These objects can be used as if they were dictionaries in many contexts and
  can be compared for equality by hash.
  """

  def __init__(self, fields, name=None, collection_name=None, basename=''):
    """Save list/tuple or convert dictionary a list based on value ordering.

    Attributes:
      name: A name for the fields schema.
      collection_name: A name for collections using the fields schema.
      _data: The underlying dictionary holding the data for the instance.

    Args:
      fields: A dictionary or ordered iterable which defines an index ordering
          for fields in a ProtoRPC message class
      name: A name for the fields schema, defaults to None. If None, uses the
          names in the fields in the order they appear. If the fields schema
          passed in is an instance of MessageFieldsSchema, this is ignored.
      collection_name: A name for collections containing the fields schema,
          defaults to None. If None, uses the name and appends the string
          'Collection'.
      basename: A basename for the default fields schema name, defaults to the
          empty string. If the fields passed in is an instance of
          MessageFieldsSchema, this is ignored.

    Raises:
      TypeError: if the fields passed in are not a dictionary, tuple, list or
          existing MessageFieldsSchema instance.
    """
    if isinstance(fields, MessageFieldsSchema):
      self._data = fields._data
      name = fields.name
      collection_name = fields.collection_name
    elif isinstance(fields, dict):
      self._data = _DictToTuple(fields)
    elif isinstance(fields, (list, tuple)):
      self._data = tuple(fields)
    else:
      error_msg = ('Can\'t create MessageFieldsSchema from object of type %s. '
                   'Must be a dictionary or iterable.' % (fields.__class__,))
      raise TypeError(error_msg)

    self.name = name or self._DefaultName(basename=basename)
    self.collection_name = collection_name or (self.name + 'Collection')

  def _DefaultName(self, basename=''):
    """The default name of the fields schema.

    Can potentially use a basename at the front, but otherwise uses the instance
    fields and joins all the values together using an underscore.

    Args:
      basename: An optional string, defaults to the empty string. If not empty,
          is used at the front of the default name.

    Returns:
      A string containing the default name of the fields schema.
    """
    name_parts = []
    if basename:
      name_parts.append(basename)
    name_parts.extend(self._data)
    return '_'.join(name_parts)

  def __ne__(self, other):
    """Not equals comparison that uses the definition of equality."""
    return not self.__eq__(other)

  def __eq__(self, other):
    """Comparison for equality that uses the hash of the object."""
    if not isinstance(other, self.__class__):
      return False
    return self.__hash__() == other.__hash__()

  def __hash__(self):
    """Unique and idempotent hash.

    Uses a the property list (_data) which is uniquely defined by its elements
    and their sort order, the name of the fields schema and the collection name
    of the fields schema.

    Returns:
      Integer hash value.
    """
    return hash((self._data, self.name, self.collection_name))

  def __iter__(self):
    """Iterator for loop expressions."""
    return iter(self._data)


class GeoPtMessage(messages.Message):
  """ProtoRPC container for GeoPt instances.

  Attributes:
    lat: Float; The latitude of the point.
    lon: Float; The longitude of the point.
  """
  # TODO(dhermes): This behavior should be regulated more directly.
  #                This is to make sure the schema name in the discovery
  #                document is GeoPtMessage rather than
  #                EndpointsProtoDatastoreGeoPtMessage.
  __module__ = ''

  lat = messages.FloatField(1, required=True)
  lon = messages.FloatField(2, required=True)


class UserMessage(messages.Message):
  """ProtoRPC container for users.User objects.

  Attributes:
    email: String; The email of the user.
    auth_domain: String; The auth domain of the user.
    user_id: String; The user ID.
    federated_identity: String; The federated identity of the user.
  """
  # TODO(dhermes): This behavior should be regulated more directly.
  #                This is to make sure the schema name in the discovery
  #                document is UserMessage rather than
  #                EndpointsProtoDatastoreUserMessage.
  __module__ = ''

  email = messages.StringField(1, required=True)
  auth_domain = messages.StringField(2, required=True)
  user_id = messages.StringField(3)
  federated_identity = messages.StringField(4)


def UserMessageFromUser(user):
  """Converts a native users.User object to a UserMessage.

  Args:
    user: An instance of users.User.

  Returns:
    A UserMessage with attributes set from the user.
  """
  return UserMessage(email=user.email(),
                     auth_domain=user.auth_domain(),
                     user_id=user.user_id(),
                     federated_identity=user.federated_identity())


def UserMessageToUser(message):
  """Converts a UserMessage to a native users.User object.

  Args:
    message: The message to be converted.

  Returns:
    An instance of users.User with attributes set from the message.
  """
  return users.User(email=message.email,
                    _auth_domain=message.auth_domain,
                    _user_id=message.user_id,
                    federated_identity=message.federated_identity)


def DatetimeValueToString(value):
  """Converts a datetime value to a string.

  Args:
    value: The value to be converted to a string.

  Returns:
    A string containing the serialized value of the datetime stamp.

  Raises:
    TypeError: if the value is not an instance of one of the three
        datetime types.
  """
  if isinstance(value, datetime.time):
    return value.strftime(TIME_STRING_FORMAT)
  # Order is important, datetime.datetime is a subclass of datetime.date
  elif isinstance(value, datetime.datetime):
    return value.strftime(DATETIME_STRING_FORMAT)
  elif isinstance(value, datetime.date):
    return value.strftime(DATE_STRING_FORMAT)
  else:
    raise TypeError('Could not serialize timestamp: %s.' % (value,))


def DatetimeValueFromString(value):
  """Converts a serialized datetime string to the native type.

  Args:
    value: The string value to be deserialized.

  Returns:
    A datetime.datetime/date/time object that was deserialized from the string.

  Raises:
    TypeError: if the value can not be deserialized to one of the three
        datetime types.
  """
  try:
    return datetime.datetime.strptime(value, TIME_STRING_FORMAT).time()
  except ValueError:
    pass

  try:
    return datetime.datetime.strptime(value, DATE_STRING_FORMAT).date()
  except ValueError:
    pass

  try:
    return datetime.datetime.strptime(value, DATETIME_STRING_FORMAT)
  except ValueError:
    pass

  raise TypeError('Could not deserialize timestamp: %s.' % (value,))


def RaiseNotImplementedMethod(property_class, explanation=None):
  """Wrapper method that returns a method which always fails.

  Args:
    property_class: A property class
    explanation: An optional argument explaining why the given property
        has not been implemented

  Returns:
    A method which will always raise NotImplementedError. If explanation is
        included, it will be raised as part of the exception, otherwise, a
        simple explanation will be provided that uses the name of the property
        class.
  """
  if explanation is None:
    explanation = ('The property %s can\'t be used to define an '
                   'EndpointsModel.' % (property_class.__name__,))

  def RaiseNotImplemented(unused_prop, unused_index):
    """Dummy method that will always raise NotImplementedError.

    Raises:
      NotImplementedError: always
    """
    raise NotImplementedError(explanation)
  return RaiseNotImplemented


def _GetEndpointsMethodDecorator(decorator_name, modelclass, **kwargs):
  """Decorate a ProtoRPC method for use by the endpoints model passed in.

  Requires exactly two positional arguments and passes the rest of the keyword
  arguments to the classmethod method at the decorator name on the given class.

  Args:
    decorator_name: The name of the attribute on the model containing the
       function which will produce the decorator.
    modelclass: An Endpoints model class.

  Returns:
    A decorator that will use the endpoint metadata to decorate an endpoints
        method.
  """
  if decorator_name not in ALLOWED_DECORATOR_NAME:
    raise TypeError('Decorator %s not allowed.' % (decorator_name,))

  # Import here to avoid circular imports
  from .ndb import model
  if IsSubclass(modelclass, model.EndpointsModel):
    return getattr(modelclass, decorator_name)(**kwargs)

  raise TypeError('Model class %s not a valid Endpoints model.' % (modelclass,))


@positional(1)
def method(modelclass, **kwargs):
  """Decorate a ProtoRPC method for use by the endpoints model passed in.

  Requires exactly one positional argument and passes the rest of the keyword
  arguments to the classmethod "method" on the given class.

  Args:
    modelclass: An Endpoints model class that can create a method.

  Returns:
    A decorator that will use the endpoint metadata to decorate an endpoints
        method.
  """
  return _GetEndpointsMethodDecorator('method', modelclass, **kwargs)


@positional(1)
def query_method(modelclass, **kwargs):
  """Decorate a ProtoRPC method intended for queries

  For use by the endpoints model passed in. Requires exactly one positional
  argument and passes the rest of the keyword arguments to the classmethod
  "query_method" on the given class.

  Args:
    modelclass: An Endpoints model class that can create a query method.

  Returns:
    A decorator that will use the endpoint metadata to decorate an endpoints
        query method.
  """
  return _GetEndpointsMethodDecorator('query_method', modelclass, **kwargs)

########NEW FILE########
__FILENAME__ = utils_test
# Copyright 2013 Google Inc. All Rights Reserved.

"""Tests for utils.py."""


import unittest

from protorpc import messages

from . import utils


class UtilsTests(unittest.TestCase):
  """Comprehensive test for the endpoints_proto_datastore.utils module."""

  def testIsSubclass(self):
    """Tests the utils.IsSubclass method."""
    self.assertTrue(utils.IsSubclass(int, int))

    self.assertTrue(utils.IsSubclass(bool, int))
    self.assertTrue(utils.IsSubclass(str, (str, basestring)))
    self.assertFalse(utils.IsSubclass(int, bool))

    # Make sure this does not fail
    self.assertFalse(utils.IsSubclass(int, None))

  def testDictToTuple(self):
    """Tests the utils._DictToTuple method."""
    # pylint:disable-msg=W0212
    self.assertRaises(AttributeError, utils._DictToTuple, None)

    class Simple(object):
      items = None  # Not callable
    self.assertRaises(TypeError, utils._DictToTuple, Simple)

    single_value_dictionary = {1: 2}
    self.assertEqual((1,), utils._DictToTuple(single_value_dictionary))

    multiple_value_dictionary = {-5: 3, 1: 1, 3: 2}
    self.assertEqual((1, 3, -5), utils._DictToTuple(multiple_value_dictionary))
    # pylint:enable-msg=W0212

  def testGeoPtMessage(self):
    """Tests the utils.GeoPtMessage protorpc message class."""
    geo_pt_message = utils.GeoPtMessage(lat=1.0)
    self.assertEqual(geo_pt_message.lat, 1.0)
    self.assertEqual(geo_pt_message.lon, None)
    self.assertFalse(geo_pt_message.is_initialized())

    geo_pt_message.lon = 2.0
    self.assertEqual(geo_pt_message.lon, 2.0)
    self.assertTrue(geo_pt_message.is_initialized())

    self.assertRaises(messages.ValidationError,
                      utils.GeoPtMessage, lat='1', lon=2)

    self.assertRaises(TypeError, utils.GeoPtMessage, 1.0, 2.0)

    self.assertRaises(AttributeError, utils.GeoPtMessage,
                      lat=1.0, lon=2.0, other=3.0)

    geo_pt_message = utils.GeoPtMessage(lat=1.0, lon=2.0)
    self.assertTrue(geo_pt_message.is_initialized())


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = main
import endpoints

from google.appengine.ext import ndb
from protorpc import remote

from endpoints_proto_datastore.ndb import EndpointsModel


# Transitioning an existing model is as easy as replacing ndb.Model with
# EndpointsModel. Since EndpointsModel inherits from ndb.Model, you will have
# the same behavior and more functionality.
class MyModel(EndpointsModel):
  # By default, the ProtoRPC message schema corresponding to this model will
  # have three string fields: attr1, attr2 and created
  # in an arbitrary order (the ordering of properties in a dictionary is not
  # guaranteed).
  attr1 = ndb.StringProperty()
  attr2 = ndb.StringProperty()
  created = ndb.DateTimeProperty(auto_now_add=True)


# Use of this decorator is the same for APIs created with or without
# endpoints-proto-datastore.
@endpoints.api(name='myapi', version='v1', description='My Little API')
class MyApi(remote.Service):

  # Instead of the endpoints.method decorator, we can use MyModel.method to
  # define a new endpoints method. Instead of having to convert a
  # ProtoRPC request message into an entity of our model and back again, we
  # start out with a MyModel entity and simply have to return one.
  # Since no overrides for the schema are specified in this decorator, the
  # request and response ProtoRPC message definition will have the three string
  # fields attr1, attr2 and created.
  @MyModel.method(path='mymodel', http_method='POST', name='mymodel.insert')
  def MyModelInsert(self, my_model):
    # Though we don't actively change the model passed in, two things happen:
    # - The entity gets an ID and is persisted
    # - Since created is auto_now_add, the entity gets a new value for created
    my_model.put()
    return my_model

  # As MyModel.method replaces a ProtoRPC request message to an entity of our
  # model, MyModel.query_method replaces it with a query object for our model.
  # By default, this query will take no arguments (the ProtoRPC request message
  # is empty) and will return a response with two fields: items and
  # nextPageToken. "nextPageToken" is simply a string field for paging through
  # result sets. "items" is what is called a "MessageField", meaning its value
  # is a ProtoRPC message itself; it is also a repeated field, meaning we have
  # an array of values rather than a single value. The nested ProtoRPC message
  # in the definition of "items" uses the same schema in MyModel.method, so each
  # value in the "items" array will have the fields attr1, attr2 and created.
  # As with MyModel.method, overrides can be specified for both the schema of
  # the request that defines the query and the schema of the messages contained
  # in the "items" list. We'll see how to use these in further examples.
  @MyModel.query_method(path='mymodels', name='mymodel.list')
  def MyModelList(self, query):
    # We have no filters that we need to apply, so we just return the query
    # object as is. As we'll see in further examples, we can augment the query
    # using environment variables and other parts of the request state.
    return query


# Use of endpoints.api_server is the same for APIs created with or without
# endpoints-proto-datastore.
application = endpoints.api_server([MyApi], restricted=False)

########NEW FILE########
__FILENAME__ = main
# If you have not yet seen the source in basic/main.py, please take a look.

import endpoints

from google.appengine.ext import ndb
from protorpc import remote

from endpoints_proto_datastore.ndb import EndpointsModel


# In this model definition, we have added an extra field "owner" to the model
# defined in basic/main.py. Since using auth, we will save the current user and
# query by the current user, so saving a user property on each entity will allow
# us to do this.
class MyModel(EndpointsModel):
  # By default, the ProtoRPC message schema corresponding to this model will
  # have four fields: attr1, attr2, created and owner
  # in an arbitrary order (the ordering of properties in a dictionary is not
  # guaranteed).
  attr1 = ndb.StringProperty()
  attr2 = ndb.StringProperty()
  created = ndb.DateTimeProperty(auto_now_add=True)
  # The three properties above are represented by string fields, but the
  # UserProperty below is represented in the ProtoRPC message schema as a
  # message field -- a field whose value is itself a message. To hold a user
  # property, a custom ProtoRPC message class is defined in
  # endpoints_proto_datastore.utils and is used to convert to and from the NDB
  # property and the corresponding ProtoRPC field.
  owner = ndb.UserProperty()


# Since we are using auth, we want to test with the Google APIs Explorer:
# https://developers.google.com/apis-explorer/
# By default, if allowed_client_ids is not specified, this is enabled by
# default. If you specify allowed_client_ids, you'll need to include
# endpoints.API_EXPLORER_CLIENT_ID in this list. This is necessary for auth
# tokens obtained by the API Explorer (on behalf of users) to be considered
# valid by our API.
@endpoints.api(name='myapi', version='v1', description='My Little API')
class MyApi(remote.Service):

  # To specify that this method requires authentication, we can simply set the
  # keyword argument user_required to True in the MyModel.method decorator. The
  # remaining arguments to the decorator are the same as in basic/main.py. Once
  # user_required is set, the method will first determine if a user has been
  # detected from the token sent with the request (if any was sent it all) and
  # will return an HTTP 401 Unauthorized if no valid user is detected. In the
  # case of a 401, the method will not be executed. Conversely, if method
  # execution occurs, user_required=True will guarantee that the current user is
  # valid.
  @MyModel.method(user_required=True,
                  path='mymodel', http_method='POST', name='mymodel.insert')
  def MyModelInsert(self, my_model):
    # Since user_required is True, we know endpoints.get_current_user will
    # return a valid user.
    my_model.owner = endpoints.get_current_user()
    # Also note, since we don't override the default ProtoRPC message schema,
    # API users can send an owner object in the request, but we overwrite the
    # model property with the current user before the entity is inserted into
    # the datastore and this put operation will only occur if a valid token
    # identifying the user was sent in the Authorization header.
    my_model.put()
    return my_model

  # As above with MyModelInsert, we add user_required=True to the arguments
  # passed to the MyModel.query_method decorator in basic/main.py. Therefore,
  # only queries can be made by a valid user.
  @MyModel.query_method(user_required=True,
                        path='mymodels', name='mymodel.list')
  def MyModelList(self, query):
    # We only allow users to query the MyModel entities that they have created,
    # so query using owner equal to the current user. Since user_required is
    # set, we know get_current_user will return a valid user.
    return query.filter(MyModel.owner == endpoints.get_current_user())


application = endpoints.api_server([MyApi], restricted=False)

########NEW FILE########
__FILENAME__ = main
# If you have not yet seen the source in simple_get/main.py, please take a look.

# In this sample, we override two of the helper properties provided by
# EndpointsModel: id and order. The purpose of this sample is to understand
# how these properties -- called alias properties -- are used. For more
# reference on EndpointsAliasProperty, see matching_queries_to_indexes/main.py
# and keys_with_ancestors/main.py.

import endpoints

from google.appengine.ext import ndb
from protorpc import remote

# See matching_queries_to_indexes/main.py for reference on this import.
from endpoints_proto_datastore.ndb import EndpointsAliasProperty
from endpoints_proto_datastore.ndb import EndpointsModel


# The helper property "order" provided by EndpointsModel has no default value,
# but we can provide it with this one, which will result in ordering a query
# first by attr1 and then attr2 in descending order. To ensure queries using
# this order do not fail, we specify the equivalent index in index.yaml.
DEFAULT_ORDER = 'attr1,-attr2'


class MyModel(EndpointsModel):
  # As in simple_get/main.py, by setting _message_fields_schema, we can set a
  # custom ProtoRPC message schema. We set the schema to the alias property
  # "id" -- which we override here -- and the three properties corresponding to
  # the NDB properties and exclude the fifth property, which is the alias
  # property "order".

  # The property "order" is excluded since we defined our own schema but would
  # have been included otherwise. We have observed that the helper property
  # "order" from EndpointsModel is not included in the ProtoRPC message schema
  # when _message_fields_schema is not present, but this case does not
  # contradict that fact. When "order" (or any of the other four helper
  # properties) is overridden, it is treated like any other NDB or alias
  # property and is included in the schema.
  _message_fields_schema = ('id', 'attr1', 'attr2', 'created')

  attr1 = ndb.StringProperty()
  attr2 = ndb.StringProperty()
  created = ndb.DateTimeProperty(auto_now_add=True)

  # This is a setter which will be used by the helper property "id", which we
  # are overriding here. The setter used for that helper property is also named
  # IdSet. This method will be called when id is set from a ProtoRPC query
  # request.
  def IdSet(self, value):
    # By default, the property "id" assumes the "id" will be an integer in a
    # simple key -- e.g. ndb.Key(MyModel, 10) -- which is the default behavior
    # if no key is set. Instead, we wish to use a string value as the "id" here,
    # so first check if the value being set is a string.
    if not isinstance(value, basestring):
      raise TypeError('ID must be a string.')
    # We call UpdateFromKey, which each of EndpointsModel.IdSet and
    # EndpointsModel.EntityKeySet use, to update the current entity using a
    # datastore key. This method sets the key on the current entity, attempts to
    # retrieve a corresponding entity from the datastore and then patch in any
    # missing values if an entity is found in the datastore.
    self.UpdateFromKey(ndb.Key(MyModel, value))

  # This EndpointsAliasProperty is our own helper property and overrides the
  # original "id". We specify the setter as the function IdSet which we just
  # defined. We also set required=True in the EndpointsAliasProperty decorator
  # to signal that an "id" must always have a value if it is included in a
  # ProtoRPC message schema.

  # Since no property_type is specified, the default value of
  # messages.StringField is used.

  # See matching_queries_to_indexes/main.py for more information on
  # EndpointsAliasProperty.
  @EndpointsAliasProperty(setter=IdSet, required=True)
  def id(self):
    # First check if the entity has a key.
    if self.key is not None:
      # If the entity has a key, return only the string_id. The method id()
      # would return any value, string, integer or otherwise, but we have a
      # specific type we wish to use for the entity "id" and that is string.
      return self.key.string_id()

  # This EndpointsAliasProperty only seeks to override the default value used by
  # the helper property "order". Both the original getter and setter are used;
  # the first by setter=EndpointsModel.OrderSet and the second by using super
  # to call the original getter. The argument default=DEFAULT_ORDER is used to
  # augment the EndpointsAliasProperty decorator by specifying a default value.
  # This value is used by the corresponding ProtoRPC field to set a value if
  # none is set by the request. Therefore, if a query has no order, rather than
  # a basic query, the order of DEFAULT_ORDER will be used.

  # Since no property_type is specified, the default value of
  # messages.StringField is used.
  @EndpointsAliasProperty(setter=EndpointsModel.OrderSet, default=DEFAULT_ORDER)
  def order(self):
    # Use getter from parent class.
    return super(MyModel, self).order


@endpoints.api(name='myapi', version='v1', description='My Little API')
class MyApi(remote.Service):

  # Since "id" is required, we require that the request contain an "id" to be
  # set on the entity. Rather than being specified in the POST body, we ask that
  # the "id" be sent in the request by setting path='mymodel/{id}'. To insert
  # a new value with id equal to cheese we would submit a request to
  #   .../mymodel/cheese
  # where ... is the full path to the API.
  @MyModel.method(path='mymodel/{id}', http_method='POST',
                  name='mymodel.insert')
  def MyModelInsert(self, my_model):
    # If the API user is trying to insert an entity which already exists in the
    # datastore (as evidenced by from_datastore being True) then we return an
    # HTTP 400 Bad request saying the entity already exists. We only want users
    # to be able to insert new entities, not to overwrite existing ones.

    # See simple_get/main.py for more about from_datastore.
    if my_model.from_datastore:
      # We can use the entity name by retrieving the string_id, since we know
      # our overridden definition of "id" ensures the string_id is set.
      name = my_model.key.string_id()
      # We raise an exception which results in an HTTP 400.
      raise endpoints.BadRequestException(
          'MyModel of name %s already exists.' % (name,))
    # If the entity does not already exist, insert it into the datastore. Since
    # the key is set when UpdateFromKey is called within IdSet, the "id" of the
    # inserted entity will be the value passed in from the request.
    my_model.put()
    return my_model

  # To use the helper property "order" that we defined, we specify query_fields
  # equal to ('order',) in the MyModel.query_method decorator. This will result
  # in a single string field in the ProtoRPC message schema. If no "order" is
  # specified in the query, the default value from the "order" property we
  # defined will be used instead.
  @MyModel.query_method(query_fields=('order',),
                        path='mymodels', name='mymodel.list')
  def MyModelList(self, query):
    return query


application = endpoints.api_server([MyApi], restricted=False)

########NEW FILE########
__FILENAME__ = main
# If you have not yet seen the source in basic/main.py, please take a look.

# In this sample we override the ProtoRPC message schema of MyModel in both the
# request and response of MyModelInsert and in the response of MyModelList.

# This is used to randomly set the value of attr2 based on attr1.
import random

import endpoints

from google.appengine.ext import ndb
from protorpc import remote

from endpoints_proto_datastore.ndb import EndpointsModel


# These are used as extra phrases to randomly add to the value of attr1 when
# setting attr2.
PHRASES = ['I', 'AM', 'RANDOM', 'AND', 'ARBITRARY']


class MyModel(EndpointsModel):
  attr1 = ndb.StringProperty()
  attr2 = ndb.StringProperty()
  created = ndb.DateTimeProperty(auto_now_add=True)


@endpoints.api(name='myapi', version='v1', description='My Little API')
class MyApi(remote.Service):

  # In addition to the arguments used in the MyModel.method decorator in
  # basic/main.py, we also use request_fields and response_fields to override
  # the schema of the ProtoRPC request message and response message,
  # respectively.

  # Since request_fields is ('attr1',), instead of the three string fields
  # attr1, attr2 and created, the request message schema will contain a single
  # string field corresponding to the NDB property attr1. Similarly, since
  # response_fields is ('created',), the response message schema will contain a
  # single string field corresponding to the NDB property created.
  @MyModel.method(request_fields=('attr1',),
                  response_fields=('created',),
                  path='mymodel',
                  http_method='POST',
                  name='mymodel.insert')
  def MyModelInsert(self, my_model):
    # We use a random value from PHRASES to set attr2 in terms of attr1. Since
    # the request message can only contain a value for attr1, we need to also
    # provide a value for attr2.
    my_model.attr2 = '%s-%s' % (my_model.attr1, random.choice(PHRASES))
    # As in basic/main.py, since created is auto_now_add, the entity gets a new
    # value for created and an ID after being persisted.
    my_model.put()
    return my_model

  # As above, in addition to the arguments used in the MyModel.query_method
  # decorator in basic/main.py, we also use collection_fields to override
  # the schema of the ProtoRPC messages that are listed in the "items" fields
  # of the query response. As in basic/main.py, there are no query arguments.
  # Since collection_fields is ('attr2', 'created'), each value in the "items"
  # list will contain the two string fields corresponding to the NDB properties
  # attr2 and created.
  @MyModel.query_method(collection_fields=('attr2', 'created'),
                        path='mymodels', name='mymodel.list')
  def MyModelList(self, query):
    # As in basic/main.py, no filters are applied.
    return query


application = endpoints.api_server([MyApi], restricted=False)

########NEW FILE########
__FILENAME__ = main
# If you have not yet seen the source in matching_queries_to_indexes/main.py and
# custom_alias_properties/main.py, please take a look.

# In this sample we define an EndpointsAliasProperty which does not override
# one of the helper properties provided by EndpointsModel; this is a first as
# all the other samples have simply tweaked existing alias properties. We use
# this property in conjuction with another alias property to define entity keys
# which have an ancestor -- for example ndb.Key(MyParent, ..., MyModel, ...) --
# which is slightly more complex than the keys we have seen so far.

# We define an extra model MyParent to hold all the data for the ancestors being
# used (though this is not strictly necessary, an ancestor key does not need to
# exist in the datastore to be used). In addition, since we will be requiring
# that a MyParent entity exists to be used as an ancestor, we provide a method
# MyParentInsert to allow API users to create or update parent objects.

import endpoints

from google.appengine.ext import ndb
from protorpc import remote

# See matching_queries_to_indexes/main.py for reference on this import.
from endpoints_proto_datastore.ndb import EndpointsAliasProperty
from endpoints_proto_datastore.ndb import EndpointsModel


class MyParent(EndpointsModel):
  # As in simple_get/main.py, by setting _message_fields_schema, we can set a
  # custom ProtoRPC message schema. We set the schema to the alias property
  # "name" and ignore the NDB property updated.
  _message_fields_schema = ('name',)

  updated = ndb.DateTimeProperty(auto_now=True)

  # This is a setter which will be used by the alias property "name".
  def NameSet(self, value):
    # The property "name" is a string field, so we expect a value passed in from
    # a ProtoRPC message to be a string. Since (as seen below), "name" is
    # required, we also need not worry about the case that the value is None.
    if not isinstance(value, basestring):
      raise TypeError('Name must be a string.')
    # We update the key using the name.
    self.UpdateFromKey(ndb.Key(MyParent, value))

  # This EndpointsAliasProperty is used for the property "name". It is required,
  # meaning that a value must always be set if the corresponding field is
  # contained in a ProtoRPC message schema.

  # Since no property_type is specified, the default value of
  # messages.StringField is used.

  # See matching_queries_to_indexes/main.py for more information on
  # EndpointsAliasProperty.
  @EndpointsAliasProperty(setter=NameSet, required=True)
  def name(self):
    # First check if the entity has a key.
    if self.key is not None:
      # If the entity has a key, return only the string_id since the property is
      # a string field.
      return self.key.string_id()


class MyModel(EndpointsModel):
  # These values are placeholders to be used when a key is created; the _parent
  # will be used as the ancestor and the _id as the ID. For example:
  #  ndb.Key(MyParent, _parent, MyModel, _id)
  # Since these values will be set by alias properties which are not set
  # simultaneously, we need to hold them around until both are present before we
  # can create a key from them.
  _parent = None
  _id = None

  attr1 = ndb.StringProperty()
  attr2 = ndb.StringProperty()
  created = ndb.DateTimeProperty(auto_now_add=True)

  # This is a helper method that will set the key on the entity only if both the
  # parent and ID are present. It will be used by property setters that provide
  # values for _parent and _id.
  def SetKey(self):
    # Can only set the key if both the parent and the child ID are set.
    if self._parent is not None and self._id is not None:
      key = ndb.Key(MyParent, self._parent, MyModel, self._id)
      # Will set the key and attempt to update the entity if it exists.
      self.UpdateFromKey(key)

  # This is a helper method that will set the _parent and _id values using the
  # entity key, if it exists. It will be used by property getters that retrieve
  # the current values of _parent and _id.
  def SetParts(self):
    # If there is no key, nothing can be set.
    if self.key is not None:
      # If there are not two tuples in the key pairs, a ValueError will occur.
      parent_pair, id_pair = self.key.pairs()
      # Each pair in key pairs will be a tuple (model kind, value) where model
      # kind is a string representing the name of the model and value is the
      # actual string or integer ID that was set.
      self._parent = parent_pair[1]
      self._id = id_pair[1]

  # This is a setter which will be used by the alias property "parent". This
  # method will be called when parent is set from a ProtoRPC request.
  def ParentSet(self, value):
    # The property "parent" is a string field, so we expect a value passed in
    # from a ProtoRPC message to be a string. Since (as seen below), "parent" is
    # required, we also need not worry about the case that the value is None.
    if not isinstance(value, basestring):
      raise TypeError('Parent name must be a string.')

    self._parent = value
    # After setting the value, we must make sure the parent exists before it can
    # be used as an ancestor.
    if ndb.Key(MyParent, value).get() is None:
      # If the MyParent key does not correspond to an entity in the datastore,
      # we return an HTTP 404 Not Found.
      raise endpoints.NotFoundException('Parent %s does not exist.' % value)
    # The helper method SetKey is called to set the entity key if the _id has
    # also been set already.
    self.SetKey()

    # If the "parent" property is used in a query method, we want the ancestor
    # of the query to be the parent key.
    self._endpoints_query_info.ancestor = ndb.Key(MyParent, value)

  # This EndpointsAliasProperty is used to get and set a parent for our entity
  # key. It is required, meaning that a value must always be set if the
  # corresponding field is contained in a ProtoRPC message schema.

  # Since no property_type is specified, the default value of
  # messages.StringField is used.

  # See matching_queries_to_indexes/main.py for more information on
  # EndpointsAliasProperty.
  @EndpointsAliasProperty(setter=ParentSet, required=True)
  def parent(self):
    # If _parent has not already been set on the entity, try to set it.
    if self._parent is None:
      # Using the helper method SetParts, _parent will be set if a valid key has
      # been set on the entity.
      self.SetParts()
    return self._parent

  # This is a setter which will be used by the alias property "id". This
  # method will be called when id is set from a ProtoRPC request. This replaces
  # the helper property "id" provided by EndpointsModel, but does not use any of
  # the functionality from that method.
  def IdSet(self, value):
    # The property "id" is a string field, so we expect a value passed in from a
    # ProtoRPC message to be a string. Since (as seen below), "id" is required,
    # we also need not worry about the case that the value is None.
    if not isinstance(value, basestring):
      raise TypeError('ID must be a string.')

    self._id = value
    # The helper method SetKey is called to set the entity key if the _parent
    # has also been set already.
    self.SetKey()

  # This EndpointsAliasProperty is used to get and set an id value for our
  # entity key. It is required, meaning that a value must always be set if the
  # corresponding field is contained in a ProtoRPC message schema.

  # Since no property_type is specified, the default value of
  # messages.StringField is used.

  # See matching_queries_to_indexes/main.py for more information on
  # EndpointsAliasProperty.
  @EndpointsAliasProperty(setter=IdSet, required=True)
  def id(self):
    # If _id has not already been set on the entity, try to set it.
    if self._id is None:
      # Using the helper method SetParts, _id will be set if a valid key has
      # been set on the entity.
      self.SetParts()
    return self._id


@endpoints.api(name='myapi', version='v1', description='My Little API')
class MyApi(remote.Service):

  # This method is not defined in any of the previous examples; it allows a
  # parent entity to be inserted so that it can be used as an ancestor. Since
  # the ProtoRPC message schema for MyParent is a single field "name", this will
  # be all that is contained in the request and the response.
  @MyParent.method(path='myparent', http_method='POST',
                   name='myparent.insert')
  def MyParentInsert(self, my_parent):
    # Though we don't actively change the model passed in, the value of updated
    # is set to the current time. No check is performed to see if the MyParent
    # entity already exists, since the values other than the name (set in the
    # key) are not relevant.
    my_parent.put()
    return my_parent

  # Since we require MyModel instances also have a MyParent ancestor, we include
  # "parent" in the request path by setting path='mymodel/{parent}'. Since "id"
  # is also required, an "id" must be included in the request body or it will be
  # rejected by ProtoRPC before this method is called.
  @MyModel.method(path='mymodel/{parent}', http_method='POST',
                  name='mymodel.insert')
  def MyModelInsert(self, my_model):
    # If the entity already exists (as evidenced by from_datastore equal to
    # True), an HTTP 400 Bad Request is returned. Since both "parent" and "id"
    # are required fields, both _parent and _id will be set on the entity and
    # MyModel.SetKey must have been called.

    # Checking in this fashion is not truly safe against duplicates. To do this,
    # a datastore transaction would be necessary.
    if my_model.from_datastore:
      raise endpoints.BadRequestException(
          'MyModel %s with parent %s already exists.' %
          (my_model.id, my_model.parent))
    my_model.put()
    return my_model

  # To make sure queries have a specified ancestor, we use the alias property
  # "parent" which we defined on MyModel and specify query_fields equal to
  # ('parent',). To specify the parent in the query, it is included in the path
  # as it was in MyModelInsert. So no query parameters will be required, simply
  # a request to
  #   .../mymodels/someparent
  # where ... is the full path to the API.
  @MyModel.query_method(query_fields=('parent',),
                        path='mymodels/{parent}', name='mymodel.list')
  def MyModelList(self, query):
    return query


application = endpoints.api_server([MyApi], restricted=False)

########NEW FILE########
__FILENAME__ = main
# If you have not yet seen the source in basic_with_auth/main.py and
# paging/main.py, please take a look.

# In this sample we use a custom Enum for the "order" property in queries
# to strictly control the indexes used and make sure we have corresponding
# indexes created in index.yaml.

import endpoints

from google.appengine.ext import ndb
# This import allows us to define our own Enum using the ProtoRPC messages
# library. This is not usually needed, since EndpointsModel handles message
# definition, but in this case it is.
from protorpc import messages
from protorpc import remote

# We import EndpointsAliasProperty so that we can define our own helper property
# similar to the properties "id", "entityKey", "limit", "order" and "pageToken"
# provided by EndpointsModel.
from endpoints_proto_datastore.ndb import EndpointsAliasProperty
from endpoints_proto_datastore.ndb import EndpointsModel


# This is an Enum used to strictly define which order values are allowed.
# In this case, we are only allowing two query orders and have an enum value
# corresponding to each.
class Order(messages.Enum):
  MYFIRST = 1
  MYSECOND = 2


class MyModel(EndpointsModel):
  # As in simple_get/main.py, by setting _message_fields_schema, we can set a
  # custom ProtoRPC message schema. We set the schema to the four properties
  # corresponding to the NDB properties and exclude the fifth property, which is
  # the alias property "order". Though the helper property "order" from
  # EndpointsModel is not included in the message schema, since we define our
  # own "order", this would be included if we did not define our own schema.
  _message_fields_schema = ('attr1', 'attr2', 'owner', 'created')

  # The properties attr1 and attr2 are required here so that all entities will
  # have values for performing queries.
  attr1 = ndb.StringProperty(required=True)
  attr2 = ndb.StringProperty(required=True)
  created = ndb.DateTimeProperty(auto_now_add=True)
  # As in basic_with_auth/main.py, an owner property is used and each entity
  # created will have the current user saved as the owner. As with attr1 and
  # attr2 above, we are also requiring the owner field so we can use it for
  # queries too.
  owner = ndb.UserProperty(required=True)

  # This is a setter which will be used by the helper property "order", which we
  # are overriding here. The setter used for that helper property is also named
  # OrderSet. This method will be called when order is set from a ProtoRPC
  # query request.
  def OrderSet(self, value):
    # Since we wish to control which queries are made, we only accept values
    # from our custom Enum type Order.
    if not isinstance(value, Order):
      raise TypeError('Expected an enum, received: %s.' % (value,))

    # For MYFIRST, we order by attr1.
    if value == Order.MYFIRST:
      # Use the method OrderSet from the parent class to set the string value
      # based on the enum.
      super(MyModel, self).OrderSet('attr1')
    # For MYSECOND, we order by attr2, but in descending order.
    elif value == Order.MYSECOND:
      # Use the method OrderSet from the parent class to set the string value
      # based on the enum.
      super(MyModel, self).OrderSet('-attr2')
    # For either case, the order used here will be combined with an equality
    # filter based on the current user, and we have the corresponding indexes
    # specified in index.yaml so no index errors are experienced by our users.

    # If the value is not a valid Enum value, raise a TypeError. This should
    # never occur since value is known to be an instance of Order.
    else:
      raise TypeError('Unexpected value of Order: %s.' % (value,))

  # This EndpointsAliasProperty is our own helper property and overrides the
  # original "order". We specify the setter as the function OrderSet which we
  # just defined. The property_type is the class Order and the default value of
  # the alias property is MYFIRST.

  # Endpoints alias properties must have a corresponding property type, which
  # can be either a ProtoRPC field or a ProtoRPC message class or enum class.
  # Here, by providing a property type of Order, we aid in the creation of a
  # field corresponding to this property in a ProtoRPC message schema.

  # The EndpointsAliasProperty can be used as a decorator as is done here, or
  # can be used in the same way NDB properties are, e.g.
  #   attr1 = ndb.StringProperty()
  # and the similar
  #   order = EndpointsAliasProperty(OrderGet, setter=OrderSet, ...)
  # where OrderGet would be the function defined here.
  @EndpointsAliasProperty(setter=OrderSet, property_type=Order,
                          default=Order.MYFIRST)
  def order(self):
    # We only need to limit the values to Order enums, so we can use the getter
    # from the helper property with no changes.
    return super(MyModel, self).order



# Since we are using auth, we want to test with the Google APIs Explorer:
# https://developers.google.com/apis-explorer/
# By default, if allowed_client_ids is not specified, this is enabled by
# default. If you specify allowed_client_ids, you'll need to include
# endpoints.API_EXPLORER_CLIENT_ID in this list. This is necessary for auth
# tokens obtained by the API Explorer (on behalf of users) to be considered
# valid by our API.
@endpoints.api(name='myapi', version='v1', description='My Little API')
class MyApi(remote.Service):

  # We use specify that request_fields is ('attr1', 'attr2') because the
  # created value is set when the entity is put to the datastore and the owner
  # is set from the current user. As in basic_with_auth, since user_required is
  # set to True, the current user will always be valid.

  # Since no response_fields are set, the four fields from
  # _message_fields_schema will be sent in the response.
  @MyModel.method(request_fields=('attr1', 'attr2'),
                  user_required=True,
                  path='mymodel', http_method='POST', name='mymodel.insert')
  def MyModelInsert(self, my_model):
    my_model.owner = endpoints.get_current_user()
    my_model.put()
    return my_model

  # As in paging/main.py, we use the fields limit, order and pageToken for
  # paging, but here "order" is the Enum-based property we defined above. As
  # mentioned in the definition of OrderSet, these order values are coupled with
  # the filter for current user.

  # Since no collection_fields are set, each value in "items" in the response
  # will use the four fields from _message_fields_schema.
  @MyModel.query_method(query_fields=('limit', 'order', 'pageToken'),
                        user_required=True,
                        path='mymodels', name='mymodel.list')
  def MyModelList(self, query):
    # Current user is valid since user_required is set to True.
    return query.filter(MyModel.owner == endpoints.get_current_user())


application = endpoints.api_server([MyApi], restricted=False)

########NEW FILE########
__FILENAME__ = main
# If you have not yet seen the source in basic/main.py, please take a look.

# In this sample we modify the query parameters in the MyModelList method to
# allow paging through results.

import endpoints

from google.appengine.ext import ndb
from protorpc import remote

from endpoints_proto_datastore.ndb import EndpointsModel


class MyModel(EndpointsModel):
  attr1 = ndb.StringProperty()
  attr2 = ndb.StringProperty()
  created = ndb.DateTimeProperty(auto_now_add=True)


@endpoints.api(name='myapi', version='v1', description='My Little API')
class MyApi(remote.Service):

  @MyModel.method(path='mymodel', http_method='POST', name='mymodel.insert')
  def MyModelInsert(self, my_model):
    my_model.put()
    return my_model

  # To add paging functionality, we set the keyword argument query_fields in the
  # MyModel.query_method decorator. By specifying the fields "limit", "order"
  # and "pageToken" as the query fields, we can accept values specializing the
  # query before retrieving results from the datastore. Though "limit", "order"
  # and "pageToken" are not defined as properties on MyModel, they are included
  # as helper properties by the base class EndpointsModel.

  # The three helper properties we use here perform the following

  # - limit: Allows a limit to be set for the number of results retrieved by a
  #          query.

  # - order: This allows the result set to be ordered by properties. For
  #          example, if the value of order is "attr1", results of the query
  #          will be in ascending order, ordered by "attr1". Similarly, if the
  #          value of order is "-attr2", the results of the query will be in
  #          descending order, ordered by "attr2".

  #          Even more complex orders can be created, such as "attr1,-attr2",
  #          which will first order by attr1 and then within each value order by
  #          attr2. However, such queries are not possible in the datastore if
  #          no index has been built. See custom_alias_properties/main.py and
  #          matching_queries_to_indexes/main.py for examples of how to deal
  #          with complex queries.

  # - pageToken: This is used for paging within a result set. For example, if a
  #              limit of 10 is set, but there are 12 results, then the ProtoRPC
  #              response will have "items" with 10 values and a nextPageToken
  #              which contains a string cursor for the query. By using this
  #              value as pageToken in a subsequent query, the remaining 2
  #              results can be retrieved and the ProtoRPC response will not
  #              contain a nextPageToken since there are no more results.

  # For a bit more on the other helper properties provided by EndpointsModel,
  # see simple_get/main.py. To see how to define your own helper properties, see
  # custom_alias_properties/main.py, matching_queries_to_indexes/main.py and
  # keys_with_ancestors/main.py.

  # To see how query fields can be used to perform simple equality filters, see
  # property_filters/main.py.
  @MyModel.query_method(query_fields=('limit', 'order', 'pageToken'),
                        path='mymodels', name='mymodel.list')
  def MyModelList(self, query):
    return query


application = endpoints.api_server([MyApi], restricted=False)

########NEW FILE########
__FILENAME__ = main
# If you have not yet seen the source in paging/main.py, please take a look.

# In this sample we modify the query parameters in the MyModelList method to
# allow querying with simple equality filters.

import endpoints

from google.appengine.ext import ndb
from protorpc import remote

from endpoints_proto_datastore.ndb import EndpointsModel


class MyModel(EndpointsModel):
  attr1 = ndb.StringProperty()
  attr2 = ndb.StringProperty()
  created = ndb.DateTimeProperty(auto_now_add=True)


@endpoints.api(name='myapi', version='v1', description='My Little API')
class MyApi(remote.Service):

  @MyModel.method(path='mymodel', http_method='POST', name='mymodel.insert')
  def MyModelInsert(self, my_model):
    my_model.put()
    return my_model

  # To add simple filters, we set the keyword argument query_fields in the
  # MyModel.query_method decorator. By specifying the fields "attr1" and "attr2"
  # as the query fields, we can filter for entities based on the values of the
  # NDB properties attr1 and/or attr2.

  # For example, a request /mymodels?attr1=cheese will return all entities with
  # attr1 equal to "cheese". The query parameters attr1 and attr2 can be used
  # individually, at the same time, or not at all.

  # An NDB property can only be used in query_fields to construct an equality
  # filter. For NDB properties which correspond to ProtoRPC message fields, such
  # as UserProperty or GeoPtProperty (see basic_with_auth/main.py), the values
  # of the property cannot be represented simply via /path?key=value. As a
  # result, such NDB properties are explicitly not allowed in query_fields and
  # if this is attempted a TypeError will be raised.
  @MyModel.query_method(query_fields=('attr1', 'attr2'),
                        path='mymodels', name='mymodel.list')
  def MyModelList(self, query):
    return query


application = endpoints.api_server([MyApi], restricted=False)

########NEW FILE########
__FILENAME__ = main
# If you have not yet seen the source in basic/main.py, please take a look.

# In this sample we add an additional method MyModelGet which allows a specific
# entity to be retrieved.

import endpoints

from google.appengine.ext import ndb
from protorpc import remote

from endpoints_proto_datastore.ndb import EndpointsModel


# In this model definition, we have included _message_fields_schema to define
# a custom ProtoRPC message schema for this model. To see a similar but
# different way to use custom fields, check out the samples in
# custom_api_response_messages/main.py and paging/main.py.
class MyModel(EndpointsModel):
  # This results in a ProtoRPC message definition with four fields, in the exact
  # order specified here: id, attr1, attr2, and created.
  # The fields corresponding to properties (attr1, attr2 and created) are string
  # fields as in basic/main.py. The field "id" will be an integer field
  # representing the ID of the entity in the datastore. For example if
  # my_entity.key is equal to ndb.Key(MyModel, 1), the id is the integer 1.

  # The property "id" is one of five helper properties provided by default to
  # help you perform common operations like this (retrieving by ID). In addition
  # there is an "entityKey" property which provides a base64 encoded version of
  # a datastore key and can be used in a similar fashion as "id", and three
  # properties used for queries -- limit, order, pageToken -- which are
  # described in more detail in paging/main.py.
  _message_fields_schema = ('id', 'attr1', 'attr2', 'created')

  attr1 = ndb.StringProperty()
  attr2 = ndb.StringProperty()
  created = ndb.DateTimeProperty(auto_now_add=True)


@endpoints.api(name='myapi', version='v1', description='My Little API')
class MyApi(remote.Service):

  @MyModel.method(path='mymodel', http_method='POST', name='mymodel.insert')
  def MyModelInsert(self, my_model):
    # Here, since the schema includes an ID, it is possible that the entity
    # my_model has an ID, hence we could be specifying a new ID in the datastore
    # or overwriting an existing entity. If no ID is included in the ProtoRPC
    # request, then no key will be set in the model and the ID will be set after
    # the put completes, as in basic/main.py.

    # In either case, the datastore ID from the entity will be returned in the
    # ProtoRPC response message.
    my_model.put()
    return my_model

  # This method is not defined in any of the previous examples: it allows an
  # entity to be retrieved from it's ID. As in
  # custom_api_response_messages/main.py, we override the schema of the ProtoRPC
  # request message to limit to a single field: "id". Since "id" is one of
  # the helper methods provided by EndpointsModel, we may use it as one of our
  # request_fields. In general, other than these five, only properties you
  # define are allowed.
  @MyModel.method(request_fields=('id',),
                  path='mymodel/{id}', http_method='GET', name='mymodel.get')
  def MyModelGet(self, my_model):
    # Since the field "id" is included, when it is set from the ProtoRPC
    # message, the decorator attempts to retrieve the entity by its ID. If the
    # entity was retrieved, the boolean from_datastore on the entity will be
    # True, otherwise it will be False. In this case, if the entity we attempted
    # to retrieve was not found, we return an HTTP 404 Not Found.

    # For more details on the behavior of setting "id", see the sample
    # custom_alias_properties/main.py.
    if not my_model.from_datastore:
      raise endpoints.NotFoundException('MyModel not found.')
    return my_model

  # This is identical to the example in basic/main.py, however since the
  # ProtoRPC schema for the model now includes "id", all the values in "items"
  # will also contain an "id".
  @MyModel.query_method(path='mymodels', name='mymodel.list')
  def MyModelList(self, query):
    return query


application = endpoints.api_server([MyApi], restricted=False)

########NEW FILE########
__FILENAME__ = models
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random
import re

from google.appengine.ext import ndb
from protorpc import messages

from endpoints_proto_datastore.ndb import EndpointsAliasProperty
from endpoints_proto_datastore.ndb import EndpointsModel
from endpoints_proto_datastore.ndb import EndpointsUserProperty


class Board(EndpointsModel):
  state = ndb.StringProperty(required=True)

  def MoveOpponent(self):
    free_indices = [match.start() for match in re.finditer('-', self.state)]
    random_index = random.choice(free_indices)
    result = list(self.state)  # Need a mutable object
    result[random_index] = 'O'
    self.state = ''.join(result)


class Order(messages.Enum):
  WHEN = 1
  TEXT = 2


class Score(EndpointsModel):
  _message_fields_schema = ('id', 'outcome', 'played', 'player')

  outcome = ndb.StringProperty(required=True)
  played = ndb.DateTimeProperty(auto_now_add=True)
  player = EndpointsUserProperty(required=True, raise_unauthorized=True)

  def OrderSet(self, value):
    if not isinstance(value, Order):
      raise TypeError('Expected an enum, received: %s.' % (value,))

    if value == Order.WHEN:
      super(Score, self).OrderSet('-played')
    elif value == Order.TEXT:
      super(Score, self).OrderSet('outcome')
    else:
      raise TypeError('Unexpected value of Order: %s.' % (value,))

  @EndpointsAliasProperty(setter=OrderSet, property_type=Order,
                          default=Order.WHEN)
  def order(self):
    return super(Score, self).order

########NEW FILE########
__FILENAME__ = services
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import endpoints

import tictactoe_api


application = endpoints.api_server([tictactoe_api.TicTacToeApi],
                                   restricted=False)

########NEW FILE########
__FILENAME__ = tictactoe_api
# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from protorpc import remote

import endpoints

from models import Board
from models import Score


@endpoints.api(name='tictactoe', version='v1',
               description='Tic Tac Toe API',
               allowed_client_ids=['YOUR-CLIENT-ID',
                                   endpoints.API_EXPLORER_CLIENT_ID])
class TicTacToeApi(remote.Service):

  @Board.method(path='board', http_method='POST',
                name='board.getmove')
  def BoardGetMove(self, board):
    if not (len(board.state) == 9 and set(board.state) <= set('OX-')):
      raise endpoints.BadRequestException('Invalid board.')
    board.MoveOpponent()
    return board

  @Score.method(request_fields=('id',),
                path='scores/{id}', http_method='GET',
                name='scores.get')
  def ScoresGet(self, score):
    if not score.from_datastore:
      raise endpoints.NotFoundException('Score not found.')

    if score.player != endpoints.get_current_user():
      raise endpoints.ForbiddenException(
          'You do not have access to this score.')

    return score

  @Score.method(request_fields=('outcome',),
                path='scores', http_method='POST',
                name='scores.insert')
  def ScoresInsert(self, score):
    score.put()  # score.player already set since EndpointsUserProperty
    return score

  @Score.query_method(query_fields=('limit', 'order', 'pageToken'),
                      user_required=True,
                      path='scores', name='scores.list')
  def ScoresList(self, query):
    return query.filter(Score.player == endpoints.get_current_user())

########NEW FILE########
