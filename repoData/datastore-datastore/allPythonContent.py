__FILENAME__ = basic

from key import Key
from query import Cursor

class Datastore(object):
  '''A Datastore represents storage for any key-value pair.

  Datastores are general enough to be backed by all kinds of different storage:
  in-memory caches, databases, a remote datastore, flat files on disk, etc.

  The general idea is to wrap a more complicated storage facility in a simple,
  uniform interface, keeping the freedom of using the right tools for the job.
  In particular, a Datastore can aggregate other datastores in interesting ways,
  like sharded (to distribute load) or tiered access (caches before databases).

  While Datastores should be written general enough to accept all sorts of
  values, some implementations will undoubtedly have to be specific (e.g. SQL
  databases where fields should be decomposed into columns), particularly to
  support queries efficiently.

  '''

  # Main API. Datastore mplementations MUST implement these methods.

  def get(self, key):
    '''Return the object named by key or None if it does not exist.

    None takes the role of default value, so no KeyError exception is raised.

    Args:
      key: Key naming the object to retrieve

    Returns:
      object or None
    '''
    raise NotImplementedError

  def put(self, key, value):
    '''Stores the object `value` named by `key`.

    How to serialize and store objects is up to the underlying datastore.
    It is recommended to use simple objects (strings, numbers, lists, dicts).

    Args:
      key: Key naming `value`
      value: the object to store.
    '''
    raise NotImplementedError

  def delete(self, key):
    '''Removes the object named by `key`.

    Args:
      key: Key naming the object to remove.
    '''
    raise NotImplementedError

  def query(self, query):
    '''Returns an iterable of objects matching criteria expressed in `query`

    Implementations of query will be the largest differentiating factor
    amongst datastores. All datastores **must** implement query, even using
    query's worst case scenario, see :ref:class:`Query` for details.

    Args:
      query: Query object describing the objects to return.

    Raturns:
      iterable cursor with all objects matching criteria
    '''
    raise NotImplementedError

  # Secondary API. Datastores MAY provide optimized implementations.

  def contains(self, key):
    '''Returns whether the object named by `key` exists.

    The default implementation pays the cost of a get. Some datastore
    implementations may optimize this.

    Args:
      key: Key naming the object to check.

    Returns:
      boalean whether the object exists
    '''
    return self.get(key) is not None




class NullDatastore(Datastore):
  '''Stores nothing, but conforms to the API. Useful to test with.'''

  def get(self, key):
    '''Return the object named by key or None if it does not exist (None).'''
    return None

  def put(self, key, value):
    '''Store the object `value` named by `key` (does nothing).'''
    pass

  def delete(self, key):
    '''Remove the object named by `key` (does nothing).'''
    pass

  def query(self, query):
    '''Returns an iterable of objects matching criteria in `query` (empty).'''
    return query([])





class DictDatastore(Datastore):
  '''Simple straw-man in-memory datastore backed by nested dicts.'''

  def __init__(self):
    self._items = dict()

  def _collection(self, key):
    '''Returns the namespace collection for `key`.'''
    collection = str(key.path)
    if not collection in self._items:
      self._items[collection] = dict()
    return self._items[collection]

  def get(self, key):
    '''Return the object named by `key` or None.

    Retrieves the object from the collection corresponding to ``key.path``.

    Args:
      key: Key naming the object to retrieve.

    Returns:
      object or None
    '''
    try:
      return self._collection(key)[key]
    except KeyError, e:
      return None

  def put(self, key, value):
    '''Stores the object `value` named by `key`.

    Stores the object in the collection corresponding to ``key.path``.

    Args:
      key: Key naming `value`
      value: the object to store.
    '''
    if value is None:
      self.delete(key)
    else:
      self._collection(key)[key] = value

  def delete(self, key):
    '''Removes the object named by `key`.

    Removes the object from the collection corresponding to ``key.path``.

    Args:
      key: Key naming the object to remove.
    '''
    try:
      del self._collection(key)[key]

      if len(self._collection(key)) == 0:
        del self._items[str(key.path)]
    except KeyError, e:
      pass

  def contains(self, key):
    '''Returns whether the object named by `key` exists.

    Checks for the object in the collection corresponding to ``key.path``.

    Args:
      key: Key naming the object to check.

    Returns:
      boalean whether the object exists
    '''

    return key in self._collection(key)

  def query(self, query):
    '''Returns an iterable of objects matching criteria expressed in `query`

    Naively applies the query operations on the objects within the namespaced
    collection corresponding to ``query.key.path``.

    Args:
      query: Query object describing the objects to return.

    Raturns:
      iterable cursor with all objects matching criteria
    '''

    # entire dataset already in memory, so ok to apply query naively
    if str(query.key) in self._items:
      return query(self._items[str(query.key)].values())
    else:
      return query([])

  def __len__(self):
    return sum(map(len, self._items.values()))




class InterfaceMappingDatastore(Datastore):
  '''Represents simple wrapper datastore around an object that, though not a
  Datastore, implements data storage through a similar interface. For example,
  memcached and redis both implement a `get`, `set`, `delete` interface.
  '''

  def __init__(self, service, get='get', put='put', delete='delete', key=str):
    '''Initialize the datastore with given `service`.

    Args:
      service: A service that provides data storage through a similar interface
          to Datastore. Using the service should only require a simple mapping
          of methods, such as {put : set}.

      get:    The attribute name of the `service` method implementing get
      put:    The attribute name of the `service` method implementing put
      delete: The attribute name of the `service` method implementing delete

      key: A function converting a Datastore key (of type Key) into a `service`
          key. The conversion will often be as simple as `str`.
    '''
    self._service = service
    self._service_key = key

    self._service_ops = {}
    self._service_ops['get'] = getattr(service, get)
    self._service_ops['put'] = getattr(service, put)
    self._service_ops['delete'] = getattr(service, delete)
    # AttributeError will be raised if service does not implement the interface


  def get(self, key):
    '''Return the object in `service` named by `key` or None.

    Args:
      key: Key naming the object to retrieve.

    Returns:
      object or None
    '''
    key = self._service_key(key)
    return self._service_ops['get'](key)

  def put(self, key, value):
    '''Stores the object `value` named by `key` in `service`.

    Args:
      key: Key naming `value`.
      value: the object to store.
    '''
    key = self._service_key(key)
    self._service_ops['put'](key, value)

  def delete(self, key):
    '''Removes the object named by `key` in `service`.

    Args:
      key: Key naming the object to remove.
    '''
    key = self._service_key(key)
    self._service_ops['delete'](key)






class ShimDatastore(Datastore):
  '''Represents a non-concrete datastore that adds functionality between the
  client and a lower level datastore. Shim datastores do not actually store
  data themselves; instead, they delegate storage to an underlying child
  datastore. The default implementation just passes all calls to the child.
  '''

  def __init__(self, datastore):
    '''Initializes this ShimDatastore with child `datastore`.'''

    if not isinstance(datastore, Datastore):
      errstr = 'datastore must be of type %s. Got %s.'
      raise TypeError(errstr % (Datastore, datastore))

    self.child_datastore = datastore

  # default implementation just passes all calls to child
  def get(self, key):
    '''Return the object named by key or None if it does not exist.

    Default shim implementation simply returns ``child_datastore.get(key)``
    Override to provide different functionality, for example::

        def get(self, key):
          value = self.child_datastore.get(key)
          return json.loads(value)

    Args:
      key: Key naming the object to retrieve

    Returns:
      object or None
    '''
    return self.child_datastore.get(key)

  def put(self, key, value):
    '''Stores the object `value` named by `key`.

    Default shim implementation simply calls ``child_datastore.put(key, value)``
    Override to provide different functionality, for example::

        def put(self, key, value):
          value = json.dumps(value)
          self.child_datastore.put(key, value)

    Args:
      key: Key naming `value`.
      value: the object to store.
    '''
    self.child_datastore.put(key, value)

  def delete(self, key):
    '''Removes the object named by `key`.

    Default shim implementation simply calls ``child_datastore.delete(key)``
    Override to provide different functionality.

    Args:
      key: Key naming the object to remove.
    '''
    self.child_datastore.delete(key)

  def query(self, query):
    '''Returns an iterable of objects matching criteria expressed in `query`.

    Default shim implementation simply returns ``child_datastore.query(query)``
    Override to provide different functionality, for example::

        def query(self, query):
          cursor = self.child_datastore.query(query)
          cursor._iterable = deserialized(cursor._iterable)
          return cursor

    Args:
      query: Query object describing the objects to return.

    Raturns:
      iterable cursor with all objects matching criteria
    '''
    return self.child_datastore.query(query)




class CacheShimDatastore(ShimDatastore):
  '''Wraps a datastore with a caching shim optimizes some calls.'''

  def __init__(self, *args, **kwargs):

    self.cache_datastore = kwargs.pop('cache')

    if not isinstance(self.cache_datastore, Datastore):
      errstr = 'datastore must be of type %s. Got %s.'
      raise TypeError(errstr % (Datastore, self.cache_datastore))

    super(CacheShimDatastore, self).__init__(*args, **kwargs)

  def get(self, key):
    '''Return the object named by key or None if it does not exist.
       CacheShimDatastore first checks its ``cache_datastore``.
    '''
    value = self.cache_datastore.get(key)
    return value if value is not None else self.child_datastore.get(key)

  def put(self, key, value):
    '''Stores the object `value` named by `key`self.
       Writes to both ``cache_datastore`` and ``child_datastore``.
    '''
    self.cache_datastore.put(key, value)
    self.child_datastore.put(key, value)

  def delete(self, key):
    '''Removes the object named by `key`.
       Writes to both ``cache_datastore`` and ``child_datastore``.
    '''
    self.cache_datastore.delete(key)
    self.child_datastore.delete(key)

  def contains(self, key):
    '''Returns whether the object named by `key` exists.
       First checks ``cache_datastore``.
    '''
    return self.cache_datastore.contains(key) \
        or self.child_datastore.contains(key)



class LoggingDatastore(ShimDatastore):
  '''Wraps a datastore with a logging shim.'''

  def __init__(self, child_datastore, logger=None):

    if not logger:
      import logging
      logger = logging

    self.logger = logger

    super(LoggingDatastore, self).__init__(child_datastore)

  def get(self, key):
    '''Return the object named by key or None if it does not exist.
       LoggingDatastore logs the access.
    '''
    self.logger.info('%s: get %s' % (self, key))
    value = super(LoggingDatastore, self).get(key)
    self.logger.debug('%s: %s' % (self, value))
    return value

  def put(self, key, value):
    '''Stores the object `value` named by `key`self.
       LoggingDatastore logs the access.
    '''
    self.logger.info('%s: put %s' % (self, key))
    self.logger.debug('%s: %s' % (self, value))
    super(LoggingDatastore, self).put(key, value)

  def delete(self, key):
    '''Removes the object named by `key`.
       LoggingDatastore logs the access.
    '''
    self.logger.info('%s: delete %s' % (self, key))
    super(LoggingDatastore, self).delete(key)

  def contains(self, key):
    '''Returns whether the object named by `key` exists.
       LoggingDatastore logs the access.
    '''
    self.logger.info('%s: contains %s' % (self, key))
    return super(LoggingDatastore, self).contains(key)

  def query(self, query):
    '''Returns an iterable of objects matching criteria expressed in `query`.
       LoggingDatastore logs the access.
    '''
    self.logger.info('%s: query %s' % (self, query))
    return super(LoggingDatastore, self).query(query)




class KeyTransformDatastore(ShimDatastore):
  '''Represents a simple ShimDatastore that applies a transform on all incoming
     keys. For example:

       >>> import datastore.core
       >>> def transform(key):
       ...   return key.reverse
       ...
       >>> ds = datastore.DictDatastore()
       >>> kt = datastore.KeyTransformDatastore(ds, keytransform=transform)
       None
       >>> ds.put(datastore.Key('/a/b/c'), 'abc')
       >>> ds.get(datastore.Key('/a/b/c'))
       'abc'
       >>> kt.get(datastore.Key('/a/b/c'))
       None
       >>> kt.get(datastore.Key('/c/b/a'))
       'abc'
       >>> ds.get(datastore.Key('/c/b/a'))
       None

  '''

  def __init__(self, *args, **kwargs):
    '''Initializes KeyTransformDatastore with `keytransform` function.'''
    self.keytransform = kwargs.pop('keytransform', None)
    super(KeyTransformDatastore, self).__init__(*args, **kwargs)

  def get(self, key):
    '''Return the object named by keytransform(key).'''
    return self.child_datastore.get(self._transform(key))

  def put(self, key, value):
    '''Stores the object names by keytransform(key).'''
    return self.child_datastore.put(self._transform(key), value)

  def delete(self, key):
    '''Removes the object named by keytransform(key).'''
    return self.child_datastore.delete(self._transform(key))

  def contains(self, key):
    '''Returns whether the object named by key is in this datastore.'''
    return self.child_datastore.contains(self._transform(key))

  def query(self, query):
    '''Returns a sequence of objects matching criteria expressed in `query`'''
    query = query.copy()
    query.key = self._transform(query.key)
    return self.child_datastore.query(query)

  def _transform(self, key):
    '''Returns a `key` transformed by `self.keytransform`.'''
    return self.keytransform(key) if self.keytransform else key



class LowercaseKeyDatastore(KeyTransformDatastore):
  '''Represents a simple ShimDatastore that lowercases all incoming keys.
     For example:

      >>> import datastore.core
      >>> ds = datastore.DictDatastore()
      >>> ds.put(datastore.Key('hello'), 'world')
      >>> ds.put(datastore.Key('HELLO'), 'WORLD')
      >>> ds.get(datastore.Key('hello'))
      'world'
      >>> ds.get(datastore.Key('HELLO'))
      'WORLD'
      >>> ds.get(datastore.Key('HeLlO'))
      None
      >>> lds = datastore.LowercaseKeyDatastore(ds)
      >>> lds.get(datastore.Key('HeLlO'))
      'world'
      >>> lds.get(datastore.Key('HeLlO'))
      'world'
      >>> lds.get(datastore.Key('HeLlO'))
      'world'

  '''

  def __init__(self, *args, **kwargs):
    '''Initializes KeyTransformDatastore with keytransform function.'''
    super(LowercaseKeyDatastore, self).__init__(*args, **kwargs)
    self.keytransform = self.lowercaseKey

  @classmethod
  def lowercaseKey(cls, key):
    '''Returns a lowercased `key`.'''
    return Key(str(key).lower())



class NamespaceDatastore(KeyTransformDatastore):
  '''Represents a simple ShimDatastore that namespaces all incoming keys.
     For example:

      >>> import datastore.core
      >>>
      >>> ds = datastore.DictDatastore()
      >>> ds.put(datastore.Key('/a/b'), 'ab')
      >>> ds.put(datastore.Key('/c/d'), 'cd')
      >>> ds.put(datastore.Key('/a/b/c/d'), 'abcd')
      >>>
      >>> nd = datastore.NamespaceDatastore('/a/b', ds)
      >>> nd.get(datastore.Key('/a/b'))
      None
      >>> nd.get(datastore.Key('/c/d'))
      'abcd'
      >>> nd.get(datastore.Key('/a/b/c/d'))
      None
      >>> nd.put(datastore.Key('/c/d'), 'cd')
      >>> ds.get(datastore.Key('/a/b/c/d'))
      'cd'

  '''

  def __init__(self, namespace, *args, **kwargs):
    '''Initializes NamespaceDatastore with `key` namespace.'''
    super(NamespaceDatastore, self).__init__(*args, **kwargs)
    self.keytransform = self.namespaceKey
    self.namespace = Key(namespace)

  def namespaceKey(self, key):
    '''Returns a namespaced `key`: namespace.child(key).'''
    return self.namespace.child(key)





class NestedPathDatastore(KeyTransformDatastore):
  '''Represents a simple ShimDatastore that shards/namespaces incoming keys.

    Incoming keys are sharded into nested namespaces. The idea is to use the key
    name to separate into nested namespaces. This is akin to the directory
    structure that ``git`` uses for objects. For example:

    >>> import datastore.core
    >>>
    >>> ds = datastore.DictDatastore()
    >>> np = datastore.NestedPathDatastore(ds, depth=3, length=2)
    >>>
    >>> np.put(datastore.Key('/abcdefghijk'), 1)
    >>> np.get(datastore.Key('/abcdefghijk'))
    1
    >>> ds.get(datastore.Key('/abcdefghijk'))
    None
    >>> ds.get(datastore.Key('/ab/cd/ef/abcdefghijk'))
    1
    >>> np.put(datastore.Key('abc'), 2)
    >>> np.get(datastore.Key('abc'))
    2
    >>> ds.get(datastore.Key('/ab/ca/bc/abc'))
    2

  '''

  _default_depth = 3
  _default_length = 2
  _default_keyfn = lambda key: key.name
  _default_keyfn = staticmethod(_default_keyfn)

  def __init__(self, *args, **kwargs):
    '''Initializes KeyTransformDatastore with keytransform function.

    kwargs:
      depth: the nesting level depth (e.g. 3 => /1/2/3/123) default: 3
      length: the nesting level length (e.g. 2 => /12/123456) default: 2
    '''

    # assign the nesting variables
    self.nest_depth = kwargs.pop('depth', self._default_depth)
    self.nest_length = kwargs.pop('length', self._default_length)
    self.nest_keyfn = kwargs.pop('keyfn', self._default_keyfn)

    super(NestedPathDatastore, self).__init__(*args, **kwargs)
    self.keytransform = self.nestKey

  def query(self, query):
    # Requires supporting * operator on queries.
    raise NotImplementedError

  def nestKey(self, key):
    '''Returns a nested `key`.'''

    nest = self.nest_keyfn(key)

    # if depth * length > len(key.name), we need to pad.
    mult = 1 + int(self.nest_depth * self.nest_length / len(nest))
    nest = nest * mult

    pref = Key(self.nestedPath(nest, self.nest_depth, self.nest_length))
    return pref.child(key)

  @staticmethod
  def nestedPath(path, depth, length):
    '''returns a nested version of `basename`, using the starting characters.
      For example:

        >>> NestedPathDatastore.nested_path('abcdefghijk', 3, 2)
        'ab/cd/ef'
        >>> NestedPathDatastore.nested_path('abcdefghijk', 4, 2)
        'ab/cd/ef/gh'
        >>> NestedPathDatastore.nested_path('abcdefghijk', 3, 4)
        'abcd/efgh/ijk'
        >>> NestedPathDatastore.nested_path('abcdefghijk', 1, 4)
        'abcd'
        >>> NestedPathDatastore.nested_path('abcdefghijk', 3, 10)
        'abcdefghij/k'
    '''
    components = [path[n:n+length] for n in xrange(0, len(path), length)]
    components = components[:depth]
    return '/'.join(components)




class SymlinkDatastore(ShimDatastore):
  '''Datastore that creates filesystem-like symbolic link keys.

  A symbolic link key is a way of naming the same value with multiple keys.

  For example:

      >>> import datastore.core
      >>>
      >>> dds = datastore.DictDatastore()
      >>> sds = datastore.SymlinkDatastore(dds)
      >>>
      >>> a = datastore.Key('/A')
      >>> b = datastore.Key('/B')
      >>>
      >>> sds.put(a, 1)
      >>> sds.get(a)
      1
      >>> sds.link(a, b)
      >>> sds.get(b)
      1
      >>> sds.put(b, 2)
      >>> sds.get(b)
      2
      >>> sds.get(a)
      2
      >>> sds.delete(a)
      >>> sds.get(a)
      None
      >>> sds.get(b)
      None
      >>> sds.put(a, 3)
      >>> sds.get(a)
      3
      >>> sds.get(b)
      3
      >>> sds.delete(b)
      >>> sds.get(b)
      None
      >>> sds.get(a)
      3

  '''
  sentinel = 'datastore_link'

  def _link_value_for_key(self, source_key):
    '''Returns the link value for given `key`.'''
    return str(source_key.child(self.sentinel))


  def _link_for_value(self, value):
    '''Returns the linked key if `value` is a link, or None.'''
    try:
      key = Key(value)
      if key.name == self.sentinel:
        return key.parent
    except:
      pass
    return None


  def _follow_link(self, value):
    '''Returns given `value` or, if it is a symlink, the `value` it names.'''
    seen_keys = set()
    while True:
      link_key = self._link_for_value(value)
      if not link_key:
        return value

      assert link_key not in seen_keys, 'circular symlink reference'
      seen_keys.add(link_key)
      value = super(SymlinkDatastore, self).get(link_key)

  def _follow_link_gen(self, iterable):
    '''A generator that follows links in values encountered.'''
    for item in iterable:
      yield self._follow_link(item)


  def link(self, source_key, target_key):
    '''Creates a symbolic link key pointing from `target_key` to `source_key`'''
    link_value = self._link_value_for_key(source_key)

    # put straight into the child, to avoid following previous links.
    self.child_datastore.put(target_key, link_value)

    # exercise the link. ensure there are no cycles.
    self.get(target_key)


  def get(self, key):
    '''Return the object named by `key. Follows links.'''
    value = super(SymlinkDatastore, self).get(key)
    return self._follow_link(value)

  def put(self, key, value):
    '''Stores the object named by `key`. Follows links.'''
    # if value is a link, don't follow links
    if self._link_for_value(value):
      super(SymlinkDatastore, self).put(key, value)
      return

    # if `key` points to a symlink, need to follow it.
    current_value = super(SymlinkDatastore, self).get(key)
    link_key = self._link_for_value(current_value)
    if link_key:
      self.put(link_key, value) # self.put: could be another link.
    else:
      super(SymlinkDatastore, self).put(key, value)

  def query(self, query):
    '''Returns objects matching criteria expressed in `query`. Follows links.'''
    results = super(SymlinkDatastore, self).query(query)
    return self._follow_link_gen(results)




class DirectoryDatastore(ShimDatastore):
  '''Datastore that allows manual tracking of directory entries.

  For example:
    >>> ds = DirectoryDatastore(ds)
    >>>
    >>> # initialize directory at /foo
    >>> ds.directory(Key('/foo'))
    >>>
    >>> # adding directory entries
    >>> ds.directoryAdd(Key('/foo'), Key('/foo/bar'))
    >>> ds.directoryAdd(Key('/foo'), Key('/foo/baz'))
    >>>
    >>> # value is a generator returning all the keys in this dir
    >>> for key in ds.directoryRead(Key('/foo')):
    ...   print key
    Key('/foo/bar')
    Key('/foo/baz')
    >>>
    >>> # querying for a collection works
    >>> for item in ds.query(Query(Key('/foo'))):
    ...  print item
    'bar'
    'baz'

  '''

  def directory(self, dir_key):
    '''Initializes directory at dir_key.'''
    dir_items = self.get(dir_key)
    if not isinstance(dir_items, list):
      self.put(dir_key, [])


  def directoryRead(self, dir_key):
    '''Returns a generator that iterates over all keys in the directory
    referenced by `dir_key`

    Returns None if the directory `dir_key` does not exist
    '''

    return self.directory_entries_generator(dir_key)


  def directoryAdd(self, dir_key, key):
    '''Adds directory entry `key` to directory at `dir_key`.

    If the directory `dir_key` does not exist, it is created.
    '''
    key = str(key)

    dir_items = self.get(dir_key) or []
    if key not in dir_items:
      dir_items.append(key)
      self.put(dir_key, dir_items)


  def directoryRemove(self, dir_key, key):
    '''Removes directory entry `key` from directory at `dir_key`.

    If either the directory `dir_key` or the directory entry `key` don't exist,
    this method is a no-op.
    '''
    key = str(key)

    dir_items = self.get(dir_key) or []
    if key in dir_items:
      dir_items = [k for k in dir_items if k != key]
      self.put(dir_key, dir_items)


  def directory_entries_generator(self, dir_key):
    dir_items = self.get(dir_key) or []
    for item in dir_items:
      yield Key(item)



class DirectoryTreeDatastore(ShimDatastore):
  '''Datastore that tracks directory entries, like in a filesystem.
  All key changes cause changes in a collection-like directory.

  For example:

      >>> import datastore.core
      >>>
      >>> dds = datastore.DictDatastore()
      >>> rds = datastore.DirectoryTreeDatastore(dds)
      >>>
      >>> a = datastore.Key('/A')
      >>> b = datastore.Key('/A/B')
      >>> c = datastore.Key('/A/C')
      >>>
      >>> rds.get(a)
      []
      >>> rds.put(b, 1)
      >>> rds.get(b)
      1
      >>> rds.get(a)
      ['/A/B']
      >>> rds.put(c, 1)
      >>> rds.get(c)
      1
      >>> rds.get(a)
      ['/A/B', '/A/C']
      >>> rds.delete(b)
      >>> rds.get(a)
      ['/A/C']
      >>> rds.delete(c)
      >>> rds.get(a)
      []

  '''

  def put(self, key, value):
    '''Stores the object `value` named by `key`self.
       DirectoryTreeDatastore stores a directory entry.
    '''
    super(DirectoryTreeDatastore, self).put(key, value)

    str_key = str(key)

    # ignore root
    if str_key == '/':
      return

    # retrieve directory, to add entry
    dir_key = key.parent.instance('directory')
    directory = self.directory(dir_key)

    # ensure key is in directory
    if str_key not in directory:
      directory.append(str_key)
      super(DirectoryTreeDatastore, self).put(dir_key, directory)


  def delete(self, key):
    '''Removes the object named by `key`.
       DirectoryTreeDatastore removes the directory entry.
    '''
    super(DirectoryTreeDatastore, self).delete(key)

    str_key = str(key)

    # ignore root
    if str_key == '/':
      return

    # retrieve directory, to remove entry
    dir_key = key.parent.instance('directory')
    directory = self.directory(dir_key)

    # ensure key is not in directory
    if directory and str_key in directory:
      directory.remove(str_key)
      if len(directory) > 0:
        super(DirectoryTreeDatastore, self).put(dir_key, directory)
      else:
        super(DirectoryTreeDatastore, self).delete(dir_key)


  def query(self, query):
    '''Returns objects matching criteria expressed in `query`.
    DirectoryTreeDatastore uses directory entries.
    '''
    return query(self.directory_values_generator(query.key))



  def directory(self, key):
    '''Retrieves directory entries for given key.'''
    if key.name != 'directory':
      key = key.instance('directory')
    return self.get(key) or []


  def directory_values_generator(self, key):
    '''Retrieve directory values for given key.'''
    directory = self.directory(key)
    for key in directory:
      yield self.get(Key(key))




class DatastoreCollection(ShimDatastore):
  '''Represents a collection of datastores.'''

  def __init__(self, stores=[]):
    '''Initialize the datastore with any provided datastores.'''
    if not isinstance(stores, list):
      stores = list(stores)

    for store in stores:
      if not isinstance(store, Datastore):
        raise TypeError("all stores must be of type %s" % Datastore)

    self._stores = stores

  def datastore(self, index):
    '''Returns the datastore at `index`.'''
    return self._stores[index]

  def appendDatastore(self, store):
    '''Appends datastore `store` to this collection.'''
    if not isinstance(store, Datastore):
      raise TypeError("stores must be of type %s" % Datastore)

    self._stores.append(store)

  def removeDatastore(self, store):
    '''Removes datastore `store` from this collection.'''
    self._stores.remove(store)

  def insertDatastore(self, index, store):
    '''Inserts datastore `store` into this collection at `index`.'''
    if not isinstance(store, Datastore):
      raise TypeError("stores must be of type %s" % Datastore)

    self._stores.insert(index, store)





class TieredDatastore(DatastoreCollection):
  '''Represents a hierarchical collection of datastores.

  Each datastore is queried in order. This is helpful to organize access
  order in terms of speed (i.e. read caches first).

  Datastores should be arranged in order of completeness, with the most complete
  datastore last, as it will handle query calls.

  Semantics:
    * get      : returns first found value
    * put      : writes through to all
    * delete   : deletes through to all
    * contains : returns first found value
    * query    : queries bottom (most complete) datastore

  '''

  def get(self, key):
    '''Return the object named by key. Checks each datastore in order.'''
    value = None
    for store in self._stores:
      value = store.get(key)
      if value is not None:
        break

    # add model to lower stores only
    if value is not None:
      for store2 in self._stores:
        if store == store2:
          break
        store2.put(key, value)

    return value

  def put(self, key, value):
    '''Stores the object in all underlying datastores.'''
    for store in self._stores:
      store.put(key, value)

  def delete(self, key):
    '''Removes the object from all underlying datastores.'''
    for store in self._stores:
      store.delete(key)

  def query(self, query):
    '''Returns a sequence of objects matching criteria expressed in `query`.
    The last datastore will handle all query calls, as it has a (if not
    the only) complete record of all objects.
    '''
    # queries hit the last (most complete) datastore
    return self._stores[-1].query(query)

  def contains(self, key):
    '''Returns whether the object is in this datastore.'''
    for store in self._stores:
      if store.contains(key):
        return True
    return False





class ShardedDatastore(DatastoreCollection):
  '''Represents a collection of datastore shards.

  A datastore is selected based on a sharding function.
  Sharding functions should take a Key and return an integer.

  WARNING: adding or removing datastores while mid-use may severely affect
           consistency. Also ensure the order is correct upon initialization.
           While this is not as important for caches, it is crucial for
           persistent datastores.

  '''

  def __init__(self, stores=[], shardingfn=hash):
    '''Initialize the datastore with any provided datastore.'''
    if not callable(shardingfn):
      raise TypeError('shardingfn (type %s) is not callable' % type(shardingfn))

    super(ShardedDatastore, self).__init__(stores)
    self._shardingfn = shardingfn


  def shard(self, key):
    '''Returns the shard index to handle `key`, according to sharding fn.'''
    return self._shardingfn(key) % len(self._stores)

  def shardDatastore(self, key):
    '''Returns the shard to handle `key`.'''
    return self.datastore(self.shard(key))


  def get(self, key):
    '''Return the object named by key from the corresponding datastore.'''
    return self.shardDatastore(key).get(key)

  def put(self, key, value):
    '''Stores the object to the corresponding datastore.'''
    self.shardDatastore(key).put(key, value)

  def delete(self, key):
    '''Removes the object from the corresponding datastore.'''
    self.shardDatastore(key).delete(key)

  def contains(self, key):
    '''Returns whether the object is in this datastore.'''
    return self.shardDatastore(key).contains(key)

  def query(self, query):
    '''Returns a sequence of objects matching criteria expressed in `query`'''
    cursor = Cursor(query, self.shard_query_generator(query))
    cursor.apply_order()  # ordering sharded queries is expensive (no generator)
    return cursor

  def shard_query_generator(self, query):
    '''A generator that queries each shard in sequence.'''
    shard_query = query.copy()

    for shard in self._stores:
      # yield all items matching within this shard
      cursor = shard.query(shard_query)
      for item in cursor:
        yield item

      # update query with results of first query
      shard_query.offset = max(shard_query.offset - cursor.skipped, 0)
      if shard_query.limit:
        shard_query.limit = max(shard_query.limit - cursor.returned, 0)

        if shard_query.limit <= 0:
          break  # we're already done!


'''

Hello Tiered Access

    >>> import pymongo
    >>> import datastore.core
    >>>
    >>> from datastore.impl.mongo import MongoDatastore
    >>> from datastore.impl.lrucache import LRUCache
    >>> from datastore.impl.filesystem import FileSystemDatastore
    >>>
    >>> conn = pymongo.Connection()
    >>> mongo = MongoDatastore(conn.test_db)
    >>>
    >>> cache = LRUCache(1000)
    >>> fs = FileSystemDatastore('/tmp/.test_db')
    >>>
    >>> ds = datastore.TieredDatastore([cache, mongo, fs])
    >>>
    >>> hello = datastore.Key('hello')
    >>> ds.put(hello, 'world')
    >>> ds.contains(hello)
    True
    >>> ds.get(hello)
    'world'
    >>> ds.delete(hello)
    >>> ds.get(hello)
    None

Hello Sharding

    >>> import datastore.core
    >>>
    >>> shards = [datastore.DictDatastore() for i in range(0, 10)]
    >>>
    >>> ds = datastore.ShardedDatastore(shards)
    >>>
    >>> hello = datastore.Key('hello')
    >>> ds.put(hello, 'world')
    >>> ds.contains(hello)
    True
    >>> ds.get(hello)
    'world'
    >>> ds.delete(hello)
    >>> ds.get(hello)
    None

'''

########NEW FILE########
__FILENAME__ = key


import uuid
from .util import fasthash

class Namespace(str):
  '''
  A Key Namespace is a string identifier.

  A namespace can optionally include a field (delimited by ':')

  Example namespaces::

      Namespace('Bruces')
      Namespace('Song:PhilosopherSong')

  '''
  namespace_delimiter = ':'

  def __repr__(self):
    return "Namespace('%s')" % self

  @property
  def field(self):
    '''returns the `field` part of this namespace, if any.'''
    if ':' in self:
      return self.split(self.namespace_delimiter)[0]
    return ''

  @property
  def value(self):
    '''returns the `value` part of this namespace.'''
    return self.split(self.namespace_delimiter)[-1]



class Key(object):
  '''
  A Key represents the unique identifier of an object.

  Our Key scheme is inspired by file systems and the Google App Engine key
  model.

  Keys are meant to be unique across a system. Keys are hierarchical,
  incorporating more and more specific namespaces. Thus keys can be deemed
  'children' or 'ancestors' of other keys::

      Key('/Comedy')
      Key('/Comedy/MontyPython')

  Also, every namespace can be parametrized to embed relevant object
  information. For example, the Key `name` (most specific namespace) could
  include the object type::

      Key('/Comedy/MontyPython/Actor:JohnCleese')
      Key('/Comedy/MontyPython/Sketch:CheeseShop')
      Key('/Comedy/MontyPython/Sketch:CheeseShop/Character:Mousebender')

  '''

  __slots__ = ('_string', '_list')

  def __init__(self, key):
    if isinstance(key, list):
      key = '/'.join(key)

    self._string = self.removeDuplicateSlashes(str(key))
    self._list = None


  def __str__(self):
    '''Returns the string representation of this Key.'''
    return self._string

  def __repr__(self):
    '''Returns the repr of this Key.'''
    return "Key('%s')" % self._string


  @property
  def list(self):
    '''Returns the `list` representation of this Key.

    Note that this method assumes the key is immutable.
    '''
    if not self._list:
      self._list = map(Namespace, self._string.split('/'))
    return self._list

  @property
  def reverse(self):
    '''Returns the reverse of this Key.

        >>> Key('/Comedy/MontyPython/Actor:JohnCleese').reverse
        Key('/Actor:JohnCleese/MontyPython/Comedy')

    '''
    return Key(self.list[::-1])

  @property
  def namespaces(self):
    '''Returns the list of namespaces of this Key.'''
    return self.list

  @property
  def name(self):
    '''Returns the name of this Key, the value of the last namespace.'''
    return Namespace(self.list[-1]).value

  @property
  def type(self):
    '''Returns the type of this Key, the field of the last namespace.'''
    return Namespace(self.list[-1]).field

  def instance(self, other):
    '''Returns an instance Key, by appending a name to the namespace.'''
    assert '/' not in str(other)
    return Key(str(self) + ':' + str(other))

  @property
  def path(self):
    '''Returns the path of this Key, the parent and the type.'''
    return Key(str(self.parent) + '/' + self.type)

  @property
  def parent(self):
    '''Returns the parent Key (all namespaces except the last).

        >>> Key('/Comedy/MontyPython/Actor:JohnCleese').parent
        Key('/Comedy/MontyPython')

    '''
    if '/' in self._string:
      return Key(self.list[:-1])
    raise ValueError('%s is base key (it has no parent)' % repr(self))

  def child(self, other):
    '''Returns the child Key by appending namespace `other`.

        >>> Key('/Comedy/MontyPython').child('Actor:JohnCleese')
        Key('/Comedy/MontyPython/Actor:JohnCleese')

    '''
    return Key('%s/%s' % (self._string, str(other)))


  def isAncestorOf(self, other):
    '''Returns whether this Key is an ancestor of `other`.

        >>> john = Key('/Comedy/MontyPython/Actor:JohnCleese')
        >>> Key('/Comedy').isAncestorOf(john)
        True

    '''
    if isinstance(other, Key):
      return other._string.startswith(self._string + '/')
    raise TypeError('%s is not of type %s' % (other, Key))

  def isDescendantOf(self, other):
    '''Returns whether this Key is a descendant of `other`.

        >>> Key('/Comedy/MontyPython').isDescendantOf(Key('/Comedy'))
        True

    '''
    if isinstance(other, Key):
      return other.isAncestorOf(self)
    raise TypeError('%s is not of type %s' % (other, Key))


  def isTopLevel(self):
    '''Returns whether this Key is top-level (one namespace).'''
    return len(self.list) == 1


  def __hash__(self):
    '''Returns the hash of this Key.

    Note that for the purposes of this Key (that is, to use it and its hash
    values as unique identifiers across systems and platforms), the hash(.)
    builtin is not adequate (as it is not guaranteed to return the same hash
    value for two different interpreter runs, let alone different machines).

    For our purposes, then, we are using a perhaps more expensive hash function
    that guarantees equal hash values given the same input.
    '''
    return fasthash.hash(self)


  def __iter__(self):
    return iter(self._string)

  def __len__(self):
    return len(self._string)

  def __cmp__(self, other):
    if isinstance(other, Key):
      return cmp(self._string, other._string)
    raise TypeError('other is not of type %s' % Key)

  def __eq__(self, other):
    if isinstance(other, Key):
      return self._string == other._string
    return False

  def __ne__(self, other):
    return not self.__eq__(other)


  @classmethod
  def randomKey(cls):
    '''Returns a random Key'''
    return Key(uuid.uuid4().hex)

  @classmethod
  def removeDuplicateSlashes(cls, path):
    '''Returns the path string `path` without duplicate slashes.'''
    return '/' + '/'.join(filter(lambda p: p != '', path.split('/')))



########NEW FILE########
__FILENAME__ = query

from key import Key


def _object_getattr(obj, field):
  '''Attribute getter for the objects to operate on.

  This function can be overridden in classes or instances of Query, Filter, and
  Order. Thus, a custom function to extract values to attributes can be
  specified, and the system can remain agnostic to the client's data model,
  without loosing query power.

  For example, the default implementation works with attributes and items::

    def _object_getattr(obj, field):
      # check whether this key is an attribute
      if hasattr(obj, field):
        value = getattr(obj, field)

      # if not, perhaps it is an item (raw dicts, etc)
      elif field in obj:
        value = obj[field]

      # return whatever we've got.
      return value

  Or consider a more complex, application-specific structure::

    def _object_getattr(version, field):

      if field in ['key', 'committed', 'created', 'hash']:
        return getattr(version, field)

      else:
        return version.attributes[field]['value']


  '''

  # TODO: consider changing this to raise an exception if no value is found.
  value = None

  # check whether this key is an attribute
  if hasattr(obj, field):
    value = getattr(obj, field)

  # if not, perhaps it is an item (raw dicts, etc)
  elif field in obj:
    value = obj[field]

  # return whatever we've got.
  return value




def limit_gen(limit, iterable):
  '''A generator that applies a count `limit`.'''
  limit = int(limit)
  assert limit >= 0, 'negative limit'

  for item in iterable:
    if limit <= 0:
      break
    yield item
    limit -= 1


def offset_gen(offset, iterable, skip_signal=None):
  '''A generator that applies an `offset`, skipping `offset` elements from
  `iterable`. If skip_signal is a callable, it will be called with every
  skipped element.
  '''
  offset = int(offset)
  assert offset >= 0, 'negative offset'

  for item in iterable:
    if offset > 0:
      offset -= 1
      if callable(skip_signal):
        skip_signal(item)
    else:
      yield item


def chain_gen(iterables):
  '''A generator that chains `iterables`.'''
  for iterable in iterables:
    for item in iterable:
      yield item




class Filter(object):
  '''Represents a Filter for a specific field and its value.

  Filters are used on queries to narrow down the set of matching objects.

  Args:
    field: the attribute name (string) on which to apply the filter.

    op: the conditional operator to apply (one of
        ['<', '<=', '=', '!=', '>=', '>']).

    value: the attribute value to compare against.

  Examples::

    Filter('name', '=', 'John Cleese')
    Filter('age', '>=', 18)

  '''

  conditional_operators = ['<', '<=', '=', '!=', '>=', '>']
  '''Conditional operators that Filters support.'''

  _conditional_cmp = {
    "<"  : lambda a, b: a < b,
    "<=" : lambda a, b: a <= b,
    "="  : lambda a, b: a == b,
    "!=" : lambda a, b: a != b,
    ">=" : lambda a, b: a >= b,
    ">"  : lambda a, b: a > b
  }


  object_getattr = staticmethod(_object_getattr)
  '''Object attribute getter. Can be overridden to match client data model.
  See :py:meth:`datastore.query._object_getattr`.
  '''

  def __init__(self, field, op, value):
    if op not in self.conditional_operators:
      raise ValueError('"%s" is not a valid filter Conditional Operator' % op)

    self.field = field
    self.op = op
    self.value = value

  def __call__(self, obj):
    '''Returns whether this object passes this filter.
    This method aggressively tries to find the appropriate value.
    '''
    value = self.object_getattr(obj, self.field)

    # TODO: which way should the direction go here? it may make more sense to
    #       convert the passed-in value instead. Or try both? Or not at all?
    if not isinstance(value, self.value.__class__) and not self.value is None and not value is None:
      value = self.value.__class__(value)

    return self.valuePasses(value)

  def valuePasses(self, value):
    '''Returns whether this value passes this filter'''
    return self._conditional_cmp[self.op](value, self.value)


  def __str__(self):
    return '%s %s %s' % (self.field, self.op, self.value)

  def __repr__(self):
    return "Filter('%s', '%s', %s)" % (self.field, self.op, repr(self.value))


  def __eq__(self, o):
    return self.field == o.field and self.op == o.op and self.value == o.value

  def __ne__(self, other):
    return not self.__eq__(other)

  def __hash__(self):
    return hash(repr(self))

  def generator(self, iterable):
    '''Generator function that iteratively filters given `items`.'''
    for item in iterable:
      if self(item):
        yield item

  @classmethod
  def filter(cls, filters, iterable):
    '''Returns the elements in `iterable` that pass given `filters`'''
    if isinstance(filters, Filter):
      filters = [filters]

    for filter in filters:
      iterable = filter.generator(iterable)

    return iterable





class Order(object):
  '''Represents an Order upon a specific field, and a direction.
  Orders are used on queries to define how they operate on objects

  Args:
    order: an order in string form. This follows the format: [+-]name
           where + is ascending, - is descending, and name is the name
           of the field to order by.
           Note: if no ordering operator is specified, + is default.

  Examples::

    Order('+name')   #  ascending order by name
    Order('-age')    # descending order by age
    Order('score')   #  ascending order by score

  '''

  order_operators = ['-', '+']
  '''Ordering operators: + is ascending, - is descending.'''

  object_getattr = staticmethod(_object_getattr)
  '''Object attribute getter. Can be overridden to match client data model.
  See :py:meth:`datastore.query._object_getattr`.
  '''

  def __init__(self, order):
    self.op = '+'

    try:
      if order[0] in self.order_operators:
        self.op = order[0]
        order = order[1:]
    except IndexError:
      raise ValueError('Order input be at least two characters long.')

    self.field = order

    if self.op not in self.order_operators:
      raise ValueError('"%s" is not a valid Order Operator.' % op)


  def __str__(self):
    return '%s%s' % (self.op, self.field)

  def __repr__(self):
    return "Order('%s%s')" % (self.op, self.field)


  def __eq__(self, other):
    return self.field == other.field and self.op == other.op

  def __ne__(self, other):
    return not self.__eq__(other)

  def __hash__(self):
    return hash(repr(self))


  def isAscending(self):
    return self.op == '+'

  def isDescending(self):
    return not self.isAscending()


  def keyfn(self, obj):
    '''A key function to be used in pythonic sort operations.'''
    return self.object_getattr(obj, self.field)

  @classmethod
  def multipleOrderComparison(cls, orders):
    '''Returns a function that will compare two items according to `orders`'''
    comparers = [ (o.keyfn, 1 if o.isAscending() else -1) for o in orders]

    def cmpfn(a, b):
      for keyfn, ascOrDesc in comparers:
        comparison = cmp(keyfn(a), keyfn(b)) * ascOrDesc
        if comparison is not 0:
          return comparison
      return 0

    return cmpfn

  @classmethod
  def sorted(cls, items, orders):
    '''Returns the elements in `items` sorted according to `orders`'''
    return sorted(items, cmp=cls.multipleOrderComparison(orders))




class Query(object):
  '''A Query describes a set of objects.

  Queries are used to retrieve objects and instances matching a set of criteria
  from Datastores. Query objects themselves are simply descriptions,
  the actual Query implementations are left up to the Datastores.
  '''

  '''Object attribute getter. Can be overridden to match client data model.'''
  object_getattr = staticmethod(_object_getattr)

  def __init__(self, key=Key('/'), limit=None, offset=0, offset_key=None, object_getattr=None):
    ''' Initialize a query.

    Parameters
      key: a key representing the level of this query. For example, a Query with
           Key('/MontyPython/Actor:') would query objects in that key path, eg:
             Key('/MontyPython/Actor:JohnCleese')
             Key('/MontyPython/Actor:EricIdle')
             Key('/MontyPython/Actor:GrahamChapman')

            It is up to datastores how to implement this namespacing. E.g.,
            some datastores may store values in different tables or collections.

      limit: an integer representing the maximum number of results to return.

      offset: an integer representing a number of results to skip.

      object_getattr: a function to extract attribute values from an object. It
           is used to satisfy query filters and orders. Defining this function
           allows the client to control the data model of the stored values.
           The default function attempts to access values as attributes
           (__getattr__) or items (__getitem__).
    '''
    if not isinstance(key, Key):
      raise TypeError('key must be of type %s' % Key)

    self.key = key

    self.limit = int(limit) if limit is not None else None
    self.offset = int(offset)
    self.offset_key = offset_key

    self.filters = []
    self.orders = []

    if object_getattr:
      self.object_getattr = object_getattr

  def __str__(self):
    '''Returns a string describing this query.'''
    return repr(self)

  def __repr__(self):
    '''Returns the representation of this query. Enables eval(repr(.)).'''
    return 'Query.from_dict(%s)' % self.dict()

  def __call__(self, iterable):
    '''Naively apply this query on an iterable of objects.
    Applying a query applies filters, sorts by appropriate orders, and returns
    a limited set.

    WARNING: When orders are applied, this function operates on the entire set
             of entities directly, not just iterators/generators. That means
             the entire result set will be in memory. Datastores with large
             objects and large query results should translate the Query and
             perform their own optimizations.
    '''

    cursor = Cursor(self, iterable)
    cursor.apply_filter()
    cursor.apply_order()
    cursor.apply_offset()
    cursor.apply_limit()
    return cursor


  def order(self, order):
    '''Adds an Order to this query.

    Args:
      see :py:class:`Order <datastore.query.Order>` constructor

    Returns self for JS-like method chaining::

      query.order('+age').order('-home')

    '''
    order = order if isinstance(order, Order) else Order(order)

    # ensure order gets attr values the same way the rest of the query does.
    order.object_getattr = self.object_getattr
    self.orders.append(order)
    return self # for chaining


  def filter(self, *args):
    '''Adds a Filter to this query.

    Args:
      see :py:class:`Filter <datastore.query.Filter>` constructor

    Returns self for JS-like method chaining::

      query.filter('age', '>', 18).filter('sex', '=', 'Female')

    '''
    if len(args) == 1 and isinstance(args[0], Filter):
      filter = args[0]
    else:
      filter = Filter(*args)

    # ensure filter gets attr values the same way the rest of the query does.
    filter.object_getattr = self.object_getattr
    self.filters.append(filter)
    return self # for chaining


  def __cmp__(self, other):
    return cmp(self.dict(), other.dict())

  def __hash__(self):
    return hash(repr(self))

  def copy(self):
    '''Returns a copy of this query.'''
    if self.object_getattr is Query.object_getattr:
      other = Query(self.key)
    else:
      other = Query(self.key, object_getattr=self.object_getattr)
    other.limit = self.limit
    other.offset = self.offset
    other.offset_key = self.offset_key
    other.filters = self.filters
    other.orders = self.orders
    return other

  def dict(self):
    '''Returns a dictionary representing this query.'''
    d = dict()
    d['key'] = str(self.key)

    if self.limit is not None:
      d['limit'] = self.limit
    if self.offset > 0:
      d['offset'] = self.offset
    if self.offset_key:
      d['offset_key'] = str(self.offset_key)
    if len(self.filters) > 0:
      d['filter'] = [[f.field, f.op, f.value] for f in self.filters]
    if len(self.orders) > 0:
      d['order'] = [str(o) for o in self.orders]

    return d

  @classmethod
  def from_dict(cls, dictionary):
    '''Constructs a query from a dictionary.'''
    query = cls(Key(dictionary['key']))

    for key, value in dictionary.items():

      if key == 'order':
        for order in value:
          query.order(order)

      elif key == 'filter':
        for filter in value:
          if not isinstance(filter, Filter):
            filter = Filter(*filter)
          query.filter(filter)

      elif key in ['limit', 'offset', 'offset_key']:
        setattr(query, key, value)
    return query



def is_iterable(obj):
  return hasattr(obj, '__iter__') or hasattr(obj, '__getitem__')


class Cursor(object):
  '''Represents a query result generator.'''

  __slots__ = ('query', '_iterable', '_iterator', 'skipped', 'returned', )

  def __init__(self, query, iterable):
    if not isinstance(query, Query):
      raise ValueError('Cursor received invalid query: %s' % query)

    if not is_iterable(iterable):
      raise ValueError('Cursor received invalid iterable: %s' % iterable)

    self.query = query
    self._iterable = iterable
    self._iterator = None
    self.returned = 0
    self.skipped = 0


  def __iter__(self):
    '''The cursor itself is the iterator. Note that it cannot be used twice,
    and once iteration starts, the cursor cannot be modified.
    '''
    if self._iterator:
      raise RuntimeError('Attempt to iterate over Cursor twice.')

    self._iterator = iter(self._iterable)
    return self

  def next(self):
    '''Iterator next. Build up count of returned elements during iteration.'''

    # if iteration has not begun, begin it.
    if not self._iterator:
      self.__iter__()

    next = self._iterator.next()
    if next is not StopIteration:
      self._returned_inc(next)
    return next


  def _skipped_inc(self, item):
    '''A function to increment the skipped count.'''
    self.skipped += 1

  def _returned_inc(self, item):
    '''A function to increment the returned count.'''
    self.returned += 1


  def _ensure_modification_is_safe(self):
    '''Assertions to ensure modification of this Cursor is safe.'''
    assert self.query, 'Cursor must have a Query.'
    assert is_iterable(self._iterable), 'Cursor must have a resultset iterable.'
    assert not self._iterator, 'Cursor must not be modified after iteration.'


  def apply_filter(self):
    '''Naively apply query filters.'''
    self._ensure_modification_is_safe()

    if len(self.query.filters) > 0:
      self._iterable = Filter.filter(self.query.filters, self._iterable)

  def apply_order(self):
    '''Naively apply query orders.'''
    self._ensure_modification_is_safe()

    if len(self.query.orders) > 0:
      self._iterable = Order.sorted(self._iterable, self.query.orders)
      # not a generator :(

  def apply_offset(self):
    '''Naively apply query offset.'''
    self._ensure_modification_is_safe()

    if self.query.offset != 0:
      self._iterable = \
        offset_gen(self.query.offset, self._iterable, self._skipped_inc)
        # _skipped_inc helps keep count of skipped elements

  def apply_limit(self):
    '''Naively apply query limit.'''
    self._ensure_modification_is_safe()

    if self.query.limit is not None:
      self._iterable = limit_gen(self.query.limit, self._iterable)


########NEW FILE########
__FILENAME__ = serialize


import json
from basic import Datastore, ShimDatastore

default_serializer = json



class Serializer(object):
  '''Serializing protocol. Serialized data must be a string.'''
  @classmethod
  def loads(cls, value):
    '''returns deserialized `value`.'''
    raise NotImplementedError

  @classmethod
  def dumps(cls, value):
    '''returns serialized `value`.'''
    raise NotImplementedError

  @staticmethod
  def implements_serializer_interface(cls):
    return hasattr(cls, 'loads') and callable(cls.loads) \
       and hasattr(cls, 'dumps') and callable(cls.dumps)



class NonSerializer(Serializer):
  '''Implements serializing protocol but does not serialize at all.
  If only storing strings (or already-serialized values).
  '''
  @classmethod
  def loads(cls, value):
    '''returns `value`.'''
    return value

  @classmethod
  def dumps(cls, value):
    '''returns `value`.'''
    return value



class prettyjson(Serializer):
  '''json wrapper serializer that pretty-prints.
  Useful for human readable values and versioning.
  '''

  @classmethod
  def loads(cls, value):
    '''returns json deserialized `value`.'''
    return json.loads(value)

  @classmethod
  def dumps(cls, value):
    '''returns json serialized `value` (pretty-printed).'''
    return json.dumps(value, sort_keys=True, indent=1)


class Stack(Serializer, list):
  '''represents a stack of serializers, applying each serializer in sequence.'''

  def loads(self, value):
    '''Returns deserialized `value`.'''
    for serializer in reversed(self):
      value = serializer.loads(value)
    return value

  def dumps(self, value):
    '''returns serialized `value`.'''
    for serializer in self:
      value = serializer.dumps(value)
    return value



class map_serializer(Serializer):
  '''map serializer that ensures the serialized value is a mapping type.'''

  sentinel = '@wrapped'

  @classmethod
  def loads(cls, value):
    '''Returns mapping type deserialized `value`.'''
    if len(value) == 1 and cls.sentinel in value:
      value = value[cls.sentinel]
    return value

  @classmethod
  def dumps(cls, value):
    '''returns mapping typed serialized `value`.'''
    if not hasattr(value, '__getitem__') or not hasattr(value, 'iteritems'):
      value = {cls.sentinel: value}
    return value




def deserialized_gen(serializer, iterable):
  '''Generator that yields deserialized objects from `iterable`.'''
  for item in iterable:
    yield serializer.loads(item)

def serialized_gen(serializer, iterable):
  '''Generator that yields serialized objects from `iterable`.'''
  for item in iterable:
    yield serializer.dumps(item)



def monkey_patch_bson(bson=None):
  '''Patch bson in pymongo to use loads and dumps interface.'''
  if not bson:
    import bson

  if not hasattr(bson, 'loads'):
    bson.loads = lambda bsondoc: bson.BSON(bsondoc).decode()

  if not hasattr(bson, 'dumps'):
    bson.dumps = lambda document: bson.BSON.encode(document)



class SerializerShimDatastore(ShimDatastore):
  '''Represents a Datastore that serializes and deserializes values.

  As data is ``put``, the serializer shim serializes it and ``put``s it into
  the underlying ``child_datastore``. Correspondingly, on the way out (through
  ``get`` or ``query``) the data is retrieved from the ``child_datastore`` and
  deserialized.

  Args:
    datastore: a child datastore for the ShimDatastore superclass.

    serializer: a serializer object (responds to loads and dumps).
  '''

  # value serializer
  # override this with their own custom serializer on a class-wide or per-
  # instance basis. If you plan to store mostly strings, use NonSerializer.
  serializer = default_serializer

  def __init__(self, datastore, serializer=None):
    '''Initializes internals and tests the serializer.

    Args:
      datastore: a child datastore for the ShimDatastore superclass.

      serializer: a serializer object (responds to loads and dumps).
    '''
    super(SerializerShimDatastore, self).__init__(datastore)

    if serializer:
      self.serializer = serializer

    # ensure serializer works
    test = { 'value': repr(self) }
    errstr = 'Serializer error: serialized value does not match original'
    assert self.serializer.loads(self.serializer.dumps(test)) == test, errstr


  def serializedValue(self, value):
    '''Returns serialized `value` or None.'''
    return self.serializer.dumps(value) if value is not None else None

  def deserializedValue(self, value):
    '''Returns deserialized `value` or None.'''
    return self.serializer.loads(value) if value is not None else None


  def get(self, key):
    '''Return the object named by key or None if it does not exist.
    Retrieves the value from the ``child_datastore``, and de-serializes
    it on the way out.

    Args:
      key: Key naming the object to retrieve

    Returns:
      object or None
    '''

    ''''''
    value = self.child_datastore.get(key)
    return self.deserializedValue(value)

  def put(self, key, value):
    '''Stores the object `value` named by `key`.
    Serializes values on the way in, and stores the serialized data into the
    ``child_datastore``.

    Args:
      key: Key naming `value`
      value: the object to store.
    '''

    value = self.serializedValue(value)
    self.child_datastore.put(key, value)

  def query(self, query):
    '''Returns an iterable of objects matching criteria expressed in `query`
    De-serializes values on the way out, using a :ref:`deserialized_gen` to
    avoid incurring the cost of de-serializing all data at once, or ever, if
    iteration over results does not finish (subject to order generator
    constraint).

    Args:
      query: Query object describing the objects to return.

    Raturns:
      iterable cursor with all objects matching criteria
    '''

    # run the query on the child datastore
    cursor = self.child_datastore.query(query)

    # chain the deserializing generator to the cursor's result set iterable
    cursor._iterable = deserialized_gen(self.serializer, cursor._iterable)

    return cursor



def shim(datastore, serializer=None):
  '''Return a SerializerShimDatastore wrapping `datastore`.

  Can be used as a syntacticly-nicer eay to wrap a datastore with a
  serializer::

      my_store = datastore.serialize.shim(my_store, json)

  '''
  return SerializerShimDatastore(datastore, serializer=serializer)

'''
Hello World:

    >>> import datastore.core
    >>> import json
    >>>
    >>> ds_child = datastore.DictDatastore()
    >>> ds = datastore.serialize.shim(ds_child, json)
    >>>
    >>> hello = datastore.Key('hello')
    >>> ds.put(hello, 'world')
    >>> ds.contains(hello)
    True
    >>> ds.get(hello)
    'world'
    >>> ds.delete(hello)
    >>> ds.get(hello)
    None

'''

########NEW FILE########
__FILENAME__ = test_basic

import unittest
import logging

from ..basic import DictDatastore
from ..key import Key
from ..query import Query


class TestDatastore(unittest.TestCase):
  pkey = Key('/dfadasfdsafdas/')
  stores = []
  numelems = []

  def check_length(self,len):
    try:
      for sn in self.stores:
        self.assertEqual(len(sn), len)
    except TypeError, e:
      pass

  def subtest_remove_nonexistent(self):
    self.assertTrue(len(self.stores) > 0)
    self.check_length(0)

    # ensure removing non-existent keys is ok.
    for value in range(0, self.numelems):
      key = self.pkey.child(value)
      for sn in self.stores:
        self.assertFalse(sn.contains(key))
        sn.delete(key)
        self.assertFalse(sn.contains(key))

    self.check_length(0)

  def subtest_insert_elems(self):
    # insert numelems elems
    for value in range(0, self.numelems):
      key = self.pkey.child(value)
      for sn in self.stores:
        self.assertFalse(sn.contains(key))
        sn.put(key, value)
        self.assertTrue(sn.contains(key))
        self.assertEqual(sn.get(key), value)

    # reassure they're all there.
    self.check_length(self.numelems)

    for value in range(0, self.numelems):
      key = self.pkey.child(value)
      for sn in self.stores:
        self.assertTrue(sn.contains(key))
        self.assertEqual(sn.get(key), value)

    self.check_length(self.numelems)

  def check_query(self, query, total, slice):
    allitems = list(range(0, total))
    resultset = None

    for sn in self.stores:
      try:
        contents = list(sn.query(Query(self.pkey)))
        expected = contents[slice]
        resultset = sn.query(query)
        result = list(resultset)

        # make sure everything is there.
        self.assertTrue(len(contents) == len(allitems),\
          '%s == %s' %  (str(contents), str(allitems)))
        self.assertTrue(all([val in contents for val in allitems]))

        self.assertTrue(len(result) == len(expected),\
          '%s == %s' %  (str(result), str(expected)))
        self.assertTrue(all([val in result for val in expected]))

        #TODO: should order be preserved?
        #self.assertEqual(result, expected)

      except NotImplementedError:
        print 'WARNING: %s does not implement query.' % sn

    return resultset

  def subtest_queries(self):
    for value in range(0, self.numelems):
      key = self.pkey.child(value)
      for sn in self.stores:
        sn.put(key, value)

    k = self.pkey
    n = int(self.numelems)

    self.check_query(Query(k), n, slice(0, n))
    self.check_query(Query(k, limit=n), n, slice(0, n))
    self.check_query(Query(k, limit=n/2), n, slice(0, n/2))
    self.check_query(Query(k, offset=n/2), n, slice(n/2, n))
    self.check_query(Query(k, offset=n/3, limit=n/3), n, slice(n/3, 2*(n/3)))
    del k
    del n


  def subtest_update(self):
    # change numelems elems
    for value in range(0, self.numelems):
      key = self.pkey.child(value)
      for sn in self.stores:
        self.assertTrue(sn.contains(key))
        sn.put(key, value + 1)
        self.assertTrue(sn.contains(key))
        self.assertNotEqual(value, sn.get(key))
        self.assertEqual(value + 1, sn.get(key))

    self.check_length(self.numelems)

  def subtest_remove(self):
    # remove numelems elems
    for value in range(0, self.numelems):
      key = self.pkey.child(value)
      for sn in self.stores:
        self.assertTrue(sn.contains(key))
        sn.delete(key)
        self.assertFalse(sn.contains(key))

    self.check_length(0)


  def subtest_simple(self, stores, numelems=1000):
    self.stores = stores
    self.numelems = numelems

    self.subtest_remove_nonexistent()
    self.subtest_insert_elems()
    self.subtest_queries()
    self.subtest_update()
    self.subtest_remove()


class TestNullDatastore(unittest.TestCase):

  def test_null(self):
    from ..basic import NullDatastore

    s = NullDatastore()

    for c in range(1, 20):
      c = str(c)
      k = Key(c)
      self.assertFalse(s.contains(k))
      self.assertEqual(s.get(k), None)
      s.put(k, c)
      self.assertFalse(s.contains(k))
      self.assertEqual(s.get(k), None)

    for item in s.query(Query(Key('/'))):
      raise Exception('Should not have found anything.')


class TestDictionaryDatastore(TestDatastore):

  def test_dictionary(self):

    s1 = DictDatastore()
    s2 = DictDatastore()
    s3 = DictDatastore()
    stores = [s1, s2, s3]

    self.subtest_simple(stores)



class TestCacheShimDatastore(TestDatastore):

  def test_simple(self):
    from ..basic import CacheShimDatastore
    from ..basic import NullDatastore

    class NullMinusQueryDatastore(NullDatastore):
      def query(self, query):
        raise NotImplementedError

    # make sure the cache is used
    s1 = CacheShimDatastore(NullMinusQueryDatastore(), cache=DictDatastore())

    # make sure the cache is not relief upon
    s2 = CacheShimDatastore(DictDatastore(), cache=NullDatastore())

    # make sure the cache works in tandem
    s3 = CacheShimDatastore(DictDatastore(), cache=DictDatastore())

    self.subtest_simple([s1, s2, s3])


class TestLoggingDatastore(TestDatastore):

  def test_simple(self):
    from ..basic import LoggingDatastore

    class NullLogger(logging.getLoggerClass()):
      def debug(self, *args, **kwargs): pass
      def info(self, *args, **kwargs): pass
      def warning(self, *args, **kwargs): pass
      def error(self, *args, **kwargs): pass
      def critical(self, *args, **kwargs): pass

    s1 = LoggingDatastore(DictDatastore(), logger=NullLogger('null'))
    s2 = LoggingDatastore(DictDatastore())
    self.subtest_simple([s1, s2])




class TestKeyTransformDatastore(TestDatastore):

  def test_simple(self):
    from ..basic import KeyTransformDatastore

    s1 = KeyTransformDatastore(DictDatastore())
    s2 = KeyTransformDatastore(DictDatastore())
    s3 = KeyTransformDatastore(DictDatastore())
    stores = [s1, s2, s3]

    self.subtest_simple(stores)

  def test_reverse_transform(self):
    from ..basic import KeyTransformDatastore

    def transform(key):
      return key.reverse

    ds = DictDatastore()
    kt = KeyTransformDatastore(ds, keytransform=transform)

    k1 = Key('/a/b/c')
    k2 = Key('/c/b/a')
    self.assertFalse(ds.contains(k1))
    self.assertFalse(ds.contains(k2))
    self.assertFalse(kt.contains(k1))
    self.assertFalse(kt.contains(k2))

    ds.put(k1, 'abc')
    self.assertEqual(ds.get(k1), 'abc')
    self.assertFalse(ds.contains(k2))
    self.assertFalse(kt.contains(k1))
    self.assertEqual(kt.get(k2), 'abc')

    kt.put(k1, 'abc')
    self.assertEqual(ds.get(k1), 'abc')
    self.assertEqual(ds.get(k2), 'abc')
    self.assertEqual(kt.get(k1), 'abc')
    self.assertEqual(kt.get(k2), 'abc')

    ds.delete(k1)
    self.assertFalse(ds.contains(k1))
    self.assertEqual(ds.get(k2), 'abc')
    self.assertEqual(kt.get(k1), 'abc')
    self.assertFalse(kt.contains(k2))

    kt.delete(k1)
    self.assertFalse(ds.contains(k1))
    self.assertFalse(ds.contains(k2))
    self.assertFalse(kt.contains(k1))
    self.assertFalse(kt.contains(k2))

  def test_lowercase_transform(self):
    from ..basic import KeyTransformDatastore

    def transform(key):
      return Key(str(key).lower())

    ds = DictDatastore()
    lds = KeyTransformDatastore(ds, keytransform=transform)

    k1 = Key('hello')
    k2 = Key('HELLO')
    k3 = Key('HeLlo')

    ds.put(k1, 'world')
    ds.put(k2, 'WORLD')

    self.assertEqual(ds.get(k1), 'world')
    self.assertEqual(ds.get(k2), 'WORLD')
    self.assertFalse(ds.contains(k3))

    self.assertEqual(lds.get(k1), 'world')
    self.assertEqual(lds.get(k2), 'world')
    self.assertEqual(lds.get(k3), 'world')

    def test(key, val):
      lds.put(key, val)
      self.assertEqual(lds.get(k1), val)
      self.assertEqual(lds.get(k2), val)
      self.assertEqual(lds.get(k3), val)

    test(k1, 'a')
    test(k2, 'b')
    test(k3, 'c')



class TestLowercaseKeyDatastore(TestDatastore):

  def test_simple(self):
    from ..basic import LowercaseKeyDatastore

    s1 = LowercaseKeyDatastore(DictDatastore())
    s2 = LowercaseKeyDatastore(DictDatastore())
    s3 = LowercaseKeyDatastore(DictDatastore())
    stores = [s1, s2, s3]

    self.subtest_simple(stores)


  def test_lowercase(self):
    from ..basic import LowercaseKeyDatastore

    ds = DictDatastore()
    lds = LowercaseKeyDatastore(ds)

    k1 = Key('hello')
    k2 = Key('HELLO')
    k3 = Key('HeLlo')

    ds.put(k1, 'world')
    ds.put(k2, 'WORLD')

    self.assertEqual(ds.get(k1), 'world')
    self.assertEqual(ds.get(k2), 'WORLD')
    self.assertFalse(ds.contains(k3))

    self.assertEqual(lds.get(k1), 'world')
    self.assertEqual(lds.get(k2), 'world')
    self.assertEqual(lds.get(k3), 'world')

    def test(key, val):
      lds.put(key, val)
      self.assertEqual(lds.get(k1), val)
      self.assertEqual(lds.get(k2), val)
      self.assertEqual(lds.get(k3), val)

    test(k1, 'a')
    test(k2, 'b')
    test(k3, 'c')


class TestNamespaceDatastore(TestDatastore):

  def test_simple(self):
    from ..basic import NamespaceDatastore

    s1 = NamespaceDatastore(Key('a'), DictDatastore())
    s2 = NamespaceDatastore(Key('b'), DictDatastore())
    s3 = NamespaceDatastore(Key('c'), DictDatastore())
    stores = [s1, s2, s3]

    self.subtest_simple(stores)


  def test_namespace(self):
    from ..basic import NamespaceDatastore

    k1 = Key('/c/d')
    k2 = Key('/a/b')
    k3 = Key('/a/b/c/d')

    ds = DictDatastore()
    nd = NamespaceDatastore(k2, ds)

    ds.put(k1, 'cd')
    ds.put(k3, 'abcd')

    self.assertEqual(ds.get(k1), 'cd')
    self.assertFalse(ds.contains(k2))
    self.assertEqual(ds.get(k3), 'abcd')

    self.assertEqual(nd.get(k1), 'abcd')
    self.assertFalse(nd.contains(k2))
    self.assertFalse(nd.contains(k3))

    def test(key, val):
      nd.put(key, val)
      self.assertEqual(nd.get(key), val)
      self.assertFalse(ds.contains(key))
      self.assertFalse(nd.contains(k2.child(key)))
      self.assertEqual(ds.get(k2.child(key)), val)

    for i in range(0, 10):
      test(Key(str(i)), 'val%d' % i)



class TestNestedPathDatastore(TestDatastore):

  def test_simple(self):
    from ..basic import NestedPathDatastore

    s1 = NestedPathDatastore(DictDatastore())
    s2 = NestedPathDatastore(DictDatastore(), depth=2)
    s3 = NestedPathDatastore(DictDatastore(), length=2)
    s4 = NestedPathDatastore(DictDatastore(), length=1, depth=2)
    stores = [s1, s2, s3, s4]

    self.subtest_simple(stores)


  def test_nested_path(self):
    from ..basic import NestedPathDatastore

    nested_path = NestedPathDatastore.nestedPath

    def test(depth, length, expected):
      nested = nested_path('abcdefghijk', depth, length)
      self.assertEqual(nested, expected)

    test(3, 2, 'ab/cd/ef')
    test(4, 2, 'ab/cd/ef/gh')
    test(3, 4, 'abcd/efgh/ijk')
    test(1, 4, 'abcd')
    test(3, 10, 'abcdefghij/k')

  def subtest_nested_path_ds(self, **kwargs):
    from ..basic import NestedPathDatastore

    k1 = kwargs.pop('k1')
    k2 = kwargs.pop('k2')
    k3 = kwargs.pop('k3')
    k4 = kwargs.pop('k4')

    ds = DictDatastore()
    np = NestedPathDatastore(ds, **kwargs)

    self.assertFalse(ds.contains(k1))
    self.assertFalse(ds.contains(k2))
    self.assertFalse(ds.contains(k3))
    self.assertFalse(ds.contains(k4))

    self.assertFalse(np.contains(k1))
    self.assertFalse(np.contains(k2))
    self.assertFalse(np.contains(k3))
    self.assertFalse(np.contains(k4))

    np.put(k1, k1)
    np.put(k2, k2)

    self.assertFalse(ds.contains(k1))
    self.assertFalse(ds.contains(k2))
    self.assertTrue(ds.contains(k3))
    self.assertTrue(ds.contains(k4))

    self.assertTrue(np.contains(k1))
    self.assertTrue(np.contains(k2))
    self.assertFalse(np.contains(k3))
    self.assertFalse(np.contains(k4))

    self.assertEqual(np.get(k1), k1)
    self.assertEqual(np.get(k2), k2)
    self.assertEqual(ds.get(k3), k1)
    self.assertEqual(ds.get(k4), k2)

    np.delete(k1)
    np.delete(k2)

    self.assertFalse(ds.contains(k1))
    self.assertFalse(ds.contains(k2))
    self.assertFalse(ds.contains(k3))
    self.assertFalse(ds.contains(k4))

    self.assertFalse(np.contains(k1))
    self.assertFalse(np.contains(k2))
    self.assertFalse(np.contains(k3))
    self.assertFalse(np.contains(k4))

    ds.put(k3, k1)
    ds.put(k4, k2)

    self.assertFalse(ds.contains(k1))
    self.assertFalse(ds.contains(k2))
    self.assertTrue(ds.contains(k3))
    self.assertTrue(ds.contains(k4))

    self.assertTrue(np.contains(k1))
    self.assertTrue(np.contains(k2))
    self.assertFalse(np.contains(k3))
    self.assertFalse(np.contains(k4))

    self.assertEqual(np.get(k1), k1)
    self.assertEqual(np.get(k2), k2)
    self.assertEqual(ds.get(k3), k1)
    self.assertEqual(ds.get(k4), k2)

    ds.delete(k3)
    ds.delete(k4)

    self.assertFalse(ds.contains(k1))
    self.assertFalse(ds.contains(k2))
    self.assertFalse(ds.contains(k3))
    self.assertFalse(ds.contains(k4))

    self.assertFalse(np.contains(k1))
    self.assertFalse(np.contains(k2))
    self.assertFalse(np.contains(k3))
    self.assertFalse(np.contains(k4))


  def test_3_2(self):

    opts = {}
    opts['k1'] = Key('/abcdefghijk')
    opts['k2'] = Key('/abcdefghijki')
    opts['k3'] = Key('/ab/cd/ef/abcdefghijk')
    opts['k4'] = Key('/ab/cd/ef/abcdefghijki')
    opts['depth'] = 3
    opts['length'] = 2

    self.subtest_nested_path_ds(**opts)

  def test_5_3(self):

    opts = {}
    opts['k1'] = Key('/abcdefghijk')
    opts['k2'] = Key('/abcdefghijki')
    opts['k3'] = Key('/abc/def/ghi/jka/bcd/abcdefghijk')
    opts['k4'] = Key('/abc/def/ghi/jki/abc/abcdefghijki')
    opts['depth'] = 5
    opts['length'] = 3

    self.subtest_nested_path_ds(**opts)

  def test_keyfn(self):

    opts = {}
    opts['k1'] = Key('/abcdefghijk')
    opts['k2'] = Key('/abcdefghijki')
    opts['k3'] = Key('/kj/ih/gf/abcdefghijk')
    opts['k4'] = Key('/ik/ji/hg/abcdefghijki')
    opts['depth'] = 3
    opts['length'] = 2
    opts['keyfn'] = lambda key: key.name[::-1]

    self.subtest_nested_path_ds(**opts)



class TestSymlinkDatastore(TestDatastore):

  def test_simple(self):
    from ..basic import SymlinkDatastore

    s1 = SymlinkDatastore(DictDatastore())
    s2 = SymlinkDatastore(DictDatastore())
    s3 = SymlinkDatastore(DictDatastore())
    s4 = SymlinkDatastore(DictDatastore())
    stores = [s1, s2, s3, s4]

    self.subtest_simple(stores)


  def test_symlink_basic(self):
    from ..basic import SymlinkDatastore

    dds = DictDatastore()
    sds = SymlinkDatastore(dds)

    a = Key('/A')
    b = Key('/B')

    sds.put(a, 1)
    self.assertEqual(sds.get(a), 1)
    self.assertEqual(sds.get(b), None)
    self.assertNotEqual(sds.get(b), sds.get(a))

    sds.link(a, b)
    self.assertEqual(sds.get(a), 1)
    self.assertEqual(sds.get(b), 1)
    self.assertEqual(sds.get(a), sds.get(b))

    sds.put(b, 2)
    self.assertEqual(sds.get(a), 2)
    self.assertEqual(sds.get(b), 2)
    self.assertEqual(sds.get(a), sds.get(b))

    sds.delete(a)
    self.assertEqual(sds.get(a), None)
    self.assertEqual(sds.get(b), None)
    self.assertEqual(sds.get(b), sds.get(a))

    sds.put(a, 3)
    self.assertEqual(sds.get(a), 3)
    self.assertEqual(sds.get(b), 3)
    self.assertEqual(sds.get(b), sds.get(a))

    sds.delete(b)
    self.assertEqual(sds.get(a), 3)
    self.assertEqual(sds.get(b), None)
    self.assertNotEqual(sds.get(b), sds.get(a))

  def test_symlink_internals(self):
    from ..basic import SymlinkDatastore

    dds = DictDatastore()
    sds = SymlinkDatastore(dds)

    a = Key('/A')
    b = Key('/B')
    c = Key('/C')
    d = Key('/D')

    lva = sds._link_value_for_key(a)
    lvb = sds._link_value_for_key(b)
    lvc = sds._link_value_for_key(c)
    lvd = sds._link_value_for_key(d)

    # helper to check queries
    sds_query = lambda: list(sds.query(Query(Key('/'))))
    dds_query = lambda: list(dds.query(Query(Key('/'))))

    # ensure _link_value_for_key and _link_for_value work
    self.assertEqual(lva, str(a.child(sds.sentinel)))
    self.assertEqual(a, sds._link_for_value(lva))

    # adding a value should work like usual
    sds.put(a, 1)
    self.assertEqual(sds.get(a), 1)
    self.assertEqual(sds.get(b), None)
    self.assertNotEqual(sds.get(b), sds.get(a))

    self.assertEqual(dds.get(a), 1)
    self.assertEqual(dds.get(b), None)

    self.assertEqual(sds_query(), [1])
    self.assertEqual(dds_query(), [1])

    # _follow_link(sds._link_value_for_key(a)) should == get(a)
    self.assertEqual(sds._follow_link(lva), 1)
    self.assertEqual(list(sds._follow_link_gen([lva])), [1])

    # linking keys should work
    sds.link(a, b)
    self.assertEqual(sds.get(a), 1)
    self.assertEqual(sds.get(b), 1)
    self.assertEqual(sds.get(a), sds.get(b))

    self.assertEqual(dds.get(a), 1)
    self.assertEqual(dds.get(b), lva)

    self.assertEqual(sds_query(), [1, 1])
    self.assertEqual(dds_query(), [lva, 1])

    # changing link should affect source
    sds.put(b, 2)
    self.assertEqual(sds.get(a), 2)
    self.assertEqual(sds.get(b), 2)
    self.assertEqual(sds.get(a), sds.get(b))

    self.assertEqual(dds.get(a), 2)
    self.assertEqual(dds.get(b), lva)

    self.assertEqual(sds_query(), [2, 2])
    self.assertEqual(dds_query(), [lva, 2])

    # deleting source should affect link
    sds.delete(a)
    self.assertEqual(sds.get(a), None)
    self.assertEqual(sds.get(b), None)
    self.assertEqual(sds.get(b), sds.get(a))

    self.assertEqual(dds.get(a), None)
    self.assertEqual(dds.get(b), lva)

    self.assertEqual(sds_query(), [None])
    self.assertEqual(dds_query(), [lva])

    # putting back source should yield working link
    sds.put(a, 3)
    self.assertEqual(sds.get(a), 3)
    self.assertEqual(sds.get(b), 3)
    self.assertEqual(sds.get(b), sds.get(a))

    self.assertEqual(dds.get(a), 3)
    self.assertEqual(dds.get(b), lva)

    self.assertEqual(sds_query(), [3, 3])
    self.assertEqual(dds_query(), [lva, 3])


    # deleting link should not affect source
    sds.delete(b)
    self.assertEqual(sds.get(a), 3)
    self.assertEqual(sds.get(b), None)
    self.assertNotEqual(sds.get(b), sds.get(a))

    self.assertEqual(dds.get(a), 3)
    self.assertEqual(dds.get(b), None)

    self.assertEqual(sds_query(), [3])
    self.assertEqual(dds_query(), [3])

    # linking should bring back to normal
    sds.link(a, b)
    self.assertEqual(sds.get(a), 3)
    self.assertEqual(sds.get(b), 3)
    self.assertEqual(sds.get(b), sds.get(a))

    self.assertEqual(dds.get(a), 3)
    self.assertEqual(dds.get(b), lva)

    self.assertEqual(sds_query(), [3, 3])
    self.assertEqual(dds_query(), [lva, 3])

    # Adding another link should not affect things.
    sds.link(a, c)
    self.assertEqual(sds.get(a), 3)
    self.assertEqual(sds.get(b), 3)
    self.assertEqual(sds.get(c), 3)
    self.assertEqual(sds.get(a), sds.get(b))
    self.assertEqual(sds.get(a), sds.get(c))

    self.assertEqual(dds.get(a), 3)
    self.assertEqual(dds.get(b), lva)
    self.assertEqual(dds.get(c), lva)

    self.assertEqual(sds_query(), [3, 3, 3])
    self.assertEqual(dds_query(), [lva, lva, 3])

    # linking should be transitive
    sds.link(b, c)
    sds.link(c, d)
    self.assertEqual(sds.get(a), 3)
    self.assertEqual(sds.get(b), 3)
    self.assertEqual(sds.get(c), 3)
    self.assertEqual(sds.get(d), 3)
    self.assertEqual(sds.get(a), sds.get(b))
    self.assertEqual(sds.get(a), sds.get(c))
    self.assertEqual(sds.get(a), sds.get(d))

    self.assertEqual(dds.get(a), 3)
    self.assertEqual(dds.get(b), lva)
    self.assertEqual(dds.get(c), lvb)
    self.assertEqual(dds.get(d), lvc)

    self.assertEqual(sds_query(), [3, 3, 3, 3])
    self.assertEqual(set(dds_query()), set([3, lva, lvb, lvc]))

    self.assertRaises(AssertionError, sds.link, d, a)


  def test_symlink_recursive(self):
    from ..basic import SymlinkDatastore

    dds = DictDatastore()
    sds1 = SymlinkDatastore(dds)
    sds2 = SymlinkDatastore(sds1)

    a = Key('/A')
    b = Key('/B')

    sds2.put(a, 1)
    self.assertEqual(sds2.get(a), 1)
    self.assertEqual(sds2.get(b), None)
    self.assertNotEqual(sds2.get(b), sds2.get(a))

    sds2.link(a, b)
    self.assertEqual(sds2.get(a), 1)
    self.assertEqual(sds2.get(b), 1)
    self.assertEqual(sds2.get(a), sds2.get(b))
    self.assertEqual(sds1.get(a), sds1.get(b))

    sds2.link(a, b)
    self.assertEqual(sds2.get(a), 1)
    self.assertEqual(sds2.get(b), 1)
    self.assertEqual(sds2.get(a), sds2.get(b))
    self.assertEqual(sds1.get(a), sds1.get(b))

    sds2.link(a, b)
    self.assertEqual(sds2.get(a), 1)
    self.assertEqual(sds2.get(b), 1)
    self.assertEqual(sds2.get(a), sds2.get(b))
    self.assertEqual(sds1.get(a), sds1.get(b))

    sds2.put(b, 2)
    self.assertEqual(sds2.get(a), 2)
    self.assertEqual(sds2.get(b), 2)
    self.assertEqual(sds2.get(a), sds2.get(b))
    self.assertEqual(sds1.get(a), sds1.get(b))

    sds2.delete(a)
    self.assertEqual(sds2.get(a), None)
    self.assertEqual(sds2.get(b), None)
    self.assertEqual(sds2.get(b), sds2.get(a))

    sds2.put(a, 3)
    self.assertEqual(sds2.get(a), 3)
    self.assertEqual(sds2.get(b), 3)
    self.assertEqual(sds2.get(b), sds2.get(a))

    sds2.delete(b)
    self.assertEqual(sds2.get(a), 3)
    self.assertEqual(sds2.get(b), None)
    self.assertNotEqual(sds2.get(b), sds2.get(a))



class TestDirectoryDatastore(TestDatastore):

  def test_simple(self):
    from ..basic import DirectoryDatastore

    s1 = DirectoryDatastore(DictDatastore())
    s2 = DirectoryDatastore(DictDatastore())
    self.subtest_simple([s1, s2])


  def test_directory_init(self):
    from ..basic import DirectoryDatastore

    ds = DirectoryDatastore(DictDatastore())

    # initialize directory at /foo
    dir_key = Key('/foo')
    ds.directory(dir_key)
    self.assertEqual(ds.get(dir_key), [])

    # can add to dir
    bar_key = Key('/foo/bar')
    ds.directoryAdd(dir_key, bar_key)
    self.assertEqual(ds.get(dir_key), [str(bar_key)])

    # re-init does not wipe out directory at /foo
    dir_key = Key('/foo')
    ds.directory(dir_key)
    self.assertEqual(ds.get(dir_key), [str(bar_key)])


  def test_directory_simple(self):
    from ..basic import DirectoryDatastore

    ds = DirectoryDatastore(DictDatastore())

    # initialize directory at /foo
    dir_key = Key('/foo')
    ds.directory(dir_key)

    # adding directory entries
    bar_key = Key('/foo/bar')
    baz_key = Key('/foo/baz')
    ds.directoryAdd(dir_key, bar_key)
    ds.directoryAdd(dir_key, baz_key)
    keys = list(ds.directoryRead(dir_key))
    self.assertEqual(keys, [bar_key, baz_key])

    # removing directory entries
    ds.directoryRemove(dir_key, bar_key)
    keys = list(ds.directoryRead(dir_key))
    self.assertEqual(keys, [baz_key])

    ds.directoryRemove(dir_key, baz_key)
    keys = list(ds.directoryRead(dir_key))
    self.assertEqual(keys, [])

    # generator
    with self.assertRaises(StopIteration):
      gen = ds.directoryRead(dir_key)
      gen.next()


  def test_directory_double_add(self):
    from ..basic import DirectoryDatastore

    ds = DirectoryDatastore(DictDatastore())

    # initialize directory at /foo
    dir_key = Key('/foo')
    ds.directory(dir_key)

    # adding directory entries
    bar_key = Key('/foo/bar')
    baz_key = Key('/foo/baz')
    ds.directoryAdd(dir_key, bar_key)
    ds.directoryAdd(dir_key, baz_key)
    ds.directoryAdd(dir_key, bar_key)
    ds.directoryAdd(dir_key, baz_key)
    ds.directoryAdd(dir_key, baz_key)
    ds.directoryAdd(dir_key, bar_key)

    keys = list(ds.directoryRead(dir_key))
    self.assertEqual(keys, [bar_key, baz_key])


  def test_directory_remove(self):
    from ..basic import DirectoryDatastore

    ds = DirectoryDatastore(DictDatastore())

    # initialize directory at /foo
    dir_key = Key('/foo')
    ds.directory(dir_key)

    # adding directory entries
    bar_key = Key('/foo/bar')
    baz_key = Key('/foo/baz')
    ds.directoryAdd(dir_key, bar_key)
    ds.directoryAdd(dir_key, baz_key)
    keys = list(ds.directoryRead(dir_key))
    self.assertEqual(keys, [bar_key, baz_key])

    # removing directory entries
    ds.directoryRemove(dir_key, bar_key)
    ds.directoryRemove(dir_key, bar_key)
    ds.directoryRemove(dir_key, bar_key)
    keys = list(ds.directoryRead(dir_key))
    self.assertEqual(keys, [baz_key])




class TestDirectoryTreeDatastore(TestDatastore):

  def test_simple(self):
    from ..basic import DirectoryTreeDatastore

    s1 = DirectoryTreeDatastore(DictDatastore())
    s2 = DirectoryTreeDatastore(DictDatastore())
    self.subtest_simple([s1, s2])



class TestDatastoreCollection(TestDatastore):

  def test_tiered(self):
    from ..basic import TieredDatastore

    s1 = DictDatastore()
    s2 = DictDatastore()
    s3 = DictDatastore()
    ts = TieredDatastore([s1, s2, s3])

    k1 = Key('1')
    k2 = Key('2')
    k3 = Key('3')

    s1.put(k1, '1')
    s2.put(k2, '2')
    s3.put(k3, '3')

    self.assertTrue(s1.contains(k1))
    self.assertFalse(s2.contains(k1))
    self.assertFalse(s3.contains(k1))
    self.assertTrue(ts.contains(k1))

    self.assertEqual(ts.get(k1), '1')
    self.assertEqual(s1.get(k1), '1')
    self.assertFalse(s2.contains(k1))
    self.assertFalse(s3.contains(k1))

    self.assertFalse(s1.contains(k2))
    self.assertTrue(s2.contains(k2))
    self.assertFalse(s3.contains(k2))
    self.assertTrue(ts.contains(k2))

    self.assertEqual(s2.get(k2), '2')
    self.assertFalse(s1.contains(k2))
    self.assertFalse(s3.contains(k2))

    self.assertEqual(ts.get(k2), '2')
    self.assertEqual(s1.get(k2), '2')
    self.assertEqual(s2.get(k2), '2')
    self.assertFalse(s3.contains(k2))

    self.assertFalse(s1.contains(k3))
    self.assertFalse(s2.contains(k3))
    self.assertTrue(s3.contains(k3))
    self.assertTrue(ts.contains(k3))

    self.assertEqual(s3.get(k3), '3')
    self.assertFalse(s1.contains(k3))
    self.assertFalse(s2.contains(k3))

    self.assertEqual(ts.get(k3), '3')
    self.assertEqual(s1.get(k3), '3')
    self.assertEqual(s2.get(k3), '3')
    self.assertEqual(s3.get(k3), '3')

    ts.delete(k1)
    ts.delete(k2)
    ts.delete(k3)

    self.assertFalse(ts.contains(k1))
    self.assertFalse(ts.contains(k2))
    self.assertFalse(ts.contains(k3))

    self.subtest_simple([ts])

  def test_sharded(self, numelems=1000):
    from ..basic import ShardedDatastore

    s1 = DictDatastore()
    s2 = DictDatastore()
    s3 = DictDatastore()
    s4 = DictDatastore()
    s5 = DictDatastore()
    stores = [s1, s2, s3, s4, s5]
    hash = lambda key: int(key.name) * len(stores) / numelems
    sharded = ShardedDatastore(stores, shardingfn=hash)
    sumlens = lambda stores: sum(map(lambda s: len(s), stores))

    def checkFor(key, value, sharded, shard=None):
      correct_shard = sharded._stores[hash(key) % len(sharded._stores)]

      for s in sharded._stores:
        if shard and s == shard:
          self.assertTrue(s.contains(key))
          self.assertEqual(s.get(key), value)
        else:
          self.assertFalse(s.contains(key))

      if correct_shard == shard:
        self.assertTrue(sharded.contains(key))
        self.assertEqual(sharded.get(key), value)
      else:
        self.assertFalse(sharded.contains(key))

    self.assertEqual(sumlens(stores), 0)
    # test all correct.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      shard = stores[hash(key) % len(stores)]
      checkFor(key, value, sharded)
      shard.put(key, value)
      checkFor(key, value, sharded, shard)
    self.assertEqual(sumlens(stores), numelems)

    # ensure its in the same spots.
    for i in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      shard = stores[hash(key) % len(stores)]
      checkFor(key, value, sharded, shard)
      shard.put(key, value)
      checkFor(key, value, sharded, shard)
    self.assertEqual(sumlens(stores), numelems)

    # ensure its in the same spots.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      shard = stores[hash(key) % len(stores)]
      checkFor(key, value, sharded, shard)
      sharded.put(key, value)
      checkFor(key, value, sharded, shard)
    self.assertEqual(sumlens(stores), numelems)

    # ensure its in the same spots.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      shard = stores[hash(key) % len(stores)]
      checkFor(key, value, sharded, shard)
      if value % 2 == 0:
        shard.delete(key)
      else:
        sharded.delete(key)
      checkFor(key, value, sharded)
    self.assertEqual(sumlens(stores), 0)

    # try out adding it to the wrong shards.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      incorrect_shard = stores[(hash(key) + 1) % len(stores)]
      checkFor(key, value, sharded)
      incorrect_shard.put(key, value)
      checkFor(key, value, sharded, incorrect_shard)
    self.assertEqual(sumlens(stores), numelems)

    # ensure its in the same spots.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      incorrect_shard = stores[(hash(key) + 1) % len(stores)]
      checkFor(key, value, sharded, incorrect_shard)
      incorrect_shard.put(key, value)
      checkFor(key, value, sharded, incorrect_shard)
    self.assertEqual(sumlens(stores), numelems)

    # this wont do anything
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      incorrect_shard = stores[(hash(key) + 1) % len(stores)]
      checkFor(key, value, sharded, incorrect_shard)
      sharded.delete(key)
      checkFor(key, value, sharded, incorrect_shard)
    self.assertEqual(sumlens(stores), numelems)

    # this will place it correctly.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      incorrect_shard = stores[(hash(key) + 1) % len(stores)]
      correct_shard = stores[(hash(key)) % len(stores)]
      checkFor(key, value, sharded, incorrect_shard)
      sharded.put(key, value)
      incorrect_shard.delete(key)
      checkFor(key, value, sharded, correct_shard)
    self.assertEqual(sumlens(stores), numelems)

    # this will place it correctly.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      correct_shard = stores[(hash(key)) % len(stores)]
      checkFor(key, value, sharded, correct_shard)
      sharded.delete(key)
      checkFor(key, value, sharded)
    self.assertEqual(sumlens(stores), 0)

    self.subtest_simple([sharded])


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = test_key

import unittest
import random

from ..key import Key
from ..key import Namespace


def randomString():
  string = ''
  length = random.randint(0, 50)
  for i in range(0, length):
    string += chr(random.randint(ord('0'), ord('Z')))
  return string


class KeyTests(unittest.TestCase):

  def __subtest_basic(self, string):
    fixedString = Key.removeDuplicateSlashes(string)
    lastNamespace = fixedString.rsplit('/')[-1].split(':')
    ktype = lastNamespace[0] if len(lastNamespace) > 1 else ''
    name = lastNamespace[-1]
    path = fixedString.rsplit('/', 1)[0] + '/' + ktype
    instance = fixedString + ':' + 'c'

    self.assertEqual(Key(string)._string, fixedString)
    self.assertEqual(Key(string), Key(string))
    self.assertEqual(str(Key(string)), fixedString)
    self.assertEqual(repr(Key(string)), "Key('%s')" % fixedString)
    self.assertEqual(Key(string).name, name)
    self.assertEqual(Key(string).type, ktype)
    self.assertEqual(Key(string).instance('c'), Key(instance))
    self.assertEqual(Key(string).path, Key(path))
    self.assertEqual(Key(string), eval(repr(Key(string))))

    self.assertTrue(Key(string).child('a') > Key(string))
    self.assertTrue(Key(string).child('a') < Key(string).child('b'))
    self.assertTrue(Key(string) == Key(string))

    self.assertRaises(TypeError, cmp, Key(string), string)

    split = fixedString.split('/')
    if len(split) > 1:
      self.assertEqual(Key('/'.join(split[:-1])), Key(string).parent)
    else:
      self.assertRaises(ValueError, lambda: Key(string).parent)

    namespace = split[-1].split(':')
    if len(namespace) > 1:
      self.assertEqual(namespace[0], Key(string).type)
    else:
      self.assertEqual('', Key(string).type)


  def test_basic(self):
    self.__subtest_basic('')
    self.__subtest_basic('abcde')
    self.__subtest_basic('disahfidsalfhduisaufidsail')
    self.__subtest_basic('/fdisahfodisa/fdsa/fdsafdsafdsafdsa/fdsafdsa/')
    self.__subtest_basic(u'4215432143214321432143214321')
    self.__subtest_basic('/fdisaha////fdsa////fdsafdsafdsafdsa/fdsafdsa/')
    self.__subtest_basic('abcde:fdsfd')
    self.__subtest_basic('disahfidsalfhduisaufidsail:fdsa')
    self.__subtest_basic('/fdisahfodisa/fdsa/fdsafdsafdsafdsa/fdsafdsa/:')
    self.__subtest_basic(u'4215432143214321432143214321:')
    self.__subtest_basic('/fdisaha////fdsa////fdsafdsafdsafdsa/fdsafdsa/f:fdaf')


  def test_ancestry(self):
    k1 = Key('/A/B/C')
    k2 = Key('/A/B/C/D')

    self.assertEqual(k1._string, '/A/B/C')
    self.assertEqual(k2._string, '/A/B/C/D')
    self.assertTrue(k1.isAncestorOf(k2))
    self.assertTrue(k2.isDescendantOf(k1))
    self.assertTrue(Key('/A').isAncestorOf(k2))
    self.assertTrue(Key('/A').isAncestorOf(k1))
    self.assertFalse(Key('/A').isDescendantOf(k2))
    self.assertFalse(Key('/A').isDescendantOf(k1))
    self.assertTrue(k2.isDescendantOf(Key('/A')))
    self.assertTrue(k1.isDescendantOf(Key('/A')))
    self.assertFalse(k2.isAncestorOf(Key('/A')))
    self.assertFalse(k1.isAncestorOf(Key('/A')))
    self.assertFalse(k2.isAncestorOf(k2))
    self.assertFalse(k1.isAncestorOf(k1))
    self.assertEqual(k1.child('D'), k2)
    self.assertEqual(k1, k2.parent)
    self.assertEqual(k1.path, k2.parent.path)

  def test_type(self):
    k1 = Key('/A/B/C:c')
    k2 = Key('/A/B/C:c/D:d')

    self.assertRaises(TypeError, k1.isAncestorOf, str(k2))
    self.assertTrue(k1.isAncestorOf(k2))
    self.assertTrue(k2.isDescendantOf(k1))
    self.assertEqual(k1.type, 'C')
    self.assertEqual(k2.type, 'D')
    self.assertEqual(k1.type, k2.parent.type)

  def test_hashing(self):

    def randomKey():
      return Key('/herp/' + randomString() + '/derp')

    keys = {}

    for i in range(0, 200):
      key = randomKey()
      while key in keys.values():
        key = randomKey()

      hstr = str(hash(key))
      self.assertFalse(hstr in keys)
      keys[hstr] = key

    for key in keys.values():
      hstr = str(hash(key))
      self.assertTrue(hstr in keys)
      self.assertEqual(key, keys[hstr])

  def test_random(self):
    keys = set()
    for i in range(0, 1000):
      random = Key.randomKey()
      self.assertFalse(random in keys)
      keys.add(random)
    self.assertEqual(len(keys), 1000)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = test_query
import time
import datetime
import unittest
import hashlib
import nanotime

from ..key import Key
from ..query import Filter, Order, Query, Cursor



def version_objects():
  sr1 = {}
  sr1['key'] = '/ABCD'
  sr1['hash'] = hashlib.sha1('herp').hexdigest()
  sr1['parent'] = '0000000000000000000000000000000000000000'
  sr1['created'] = nanotime.now().nanoseconds()
  sr1['committed'] = nanotime.now().nanoseconds()
  sr1['attributes'] = {'str' : {'value' : 'herp'} }
  sr1['type'] = 'Hurr'

  sr2 = {}
  sr2['key'] = '/ABCD'
  sr2['hash'] = hashlib.sha1('derp').hexdigest()
  sr2['parent'] = hashlib.sha1('herp').hexdigest()
  sr2['created'] = nanotime.now().nanoseconds()
  sr2['committed'] = nanotime.now().nanoseconds()
  sr2['attributes'] = {'str' : {'value' : 'derp'} }
  sr2['type'] = 'Hurr'

  sr3 = {}
  sr3['key'] = '/ABCD'
  sr3['hash'] = hashlib.sha1('lerp').hexdigest()
  sr3['parent'] = hashlib.sha1('derp').hexdigest()
  sr3['created'] = nanotime.now().nanoseconds()
  sr3['committed'] = nanotime.now().nanoseconds()
  sr3['attributes'] = {'str' : {'value' : 'lerp'} }
  sr3['type'] = 'Hurr'

  return sr1, sr2, sr3


class TestFilter(unittest.TestCase):

  def assertFilter(self, filter, objects, match):
    result = [o for o in Filter.filter(filter, objects)]
    self.assertEqual(result, match)

  def test_basic(self):

    v1, v2, v3 = version_objects()
    vs = [v1, v2, v3]

    t1 = v1['committed']
    t2 = v2['committed']
    t3 = v3['committed']

    fkgtA = Filter('key', '>', '/A')

    self.assertTrue(fkgtA(v1))
    self.assertTrue(fkgtA(v2))
    self.assertTrue(fkgtA(v3))

    self.assertTrue(fkgtA.valuePasses('/BCDEG'))
    self.assertTrue(fkgtA.valuePasses('/ZCDEFDSA/fdsafdsa/fdsafdsaf'))
    self.assertFalse(fkgtA.valuePasses('/6353456346543'))
    self.assertFalse(fkgtA.valuePasses('.'))
    self.assertTrue(fkgtA.valuePasses('afsdafdsa'))

    self.assertFilter(fkgtA, vs, vs)

    fkltA = Filter('key', '<', '/A')

    self.assertFalse(fkltA(v1))
    self.assertFalse(fkltA(v2))
    self.assertFalse(fkltA(v3))

    self.assertFalse(fkltA.valuePasses('/BCDEG'))
    self.assertFalse(fkltA.valuePasses('/ZCDEFDSA/fdsafdsa/fdsafdsaf'))
    self.assertTrue(fkltA.valuePasses('/6353456346543'))
    self.assertTrue(fkltA.valuePasses('.'))
    self.assertFalse(fkltA.valuePasses('A'))
    self.assertFalse(fkltA.valuePasses('afsdafdsa'))

    self.assertFilter(fkltA, vs, [])

    fkeqA = Filter('key', '=', '/ABCD')

    self.assertTrue(fkeqA(v1))
    self.assertTrue(fkeqA(v2))
    self.assertTrue(fkeqA(v3))

    self.assertFalse(fkeqA.valuePasses('/BCDEG'))
    self.assertFalse(fkeqA.valuePasses('/ZCDEFDSA/fdsafdsa/fdsafdsaf'))
    self.assertFalse(fkeqA.valuePasses('/6353456346543'))
    self.assertFalse(fkeqA.valuePasses('A'))
    self.assertFalse(fkeqA.valuePasses('.'))
    self.assertFalse(fkeqA.valuePasses('afsdafdsa'))
    self.assertTrue(fkeqA.valuePasses('/ABCD'))

    self.assertFilter(fkeqA, vs, vs)
    self.assertFilter([fkeqA, fkltA], vs, [])
    self.assertFilter([fkeqA, fkeqA], vs, vs)

    fkgtB = Filter('key', '>', '/B')

    self.assertFalse(fkgtB(v1))
    self.assertFalse(fkgtB(v2))
    self.assertFalse(fkgtB(v3))

    self.assertFalse(fkgtB.valuePasses('/A'))
    self.assertTrue(fkgtB.valuePasses('/BCDEG'))
    self.assertTrue(fkgtB.valuePasses('/ZCDEFDSA/fdsafdsa/fdsafdsaf'))
    self.assertFalse(fkgtB.valuePasses('/6353456346543'))
    self.assertFalse(fkgtB.valuePasses('.'))
    self.assertTrue(fkgtB.valuePasses('A'))
    self.assertTrue(fkgtB.valuePasses('afsdafdsa'))

    self.assertFilter(fkgtB, vs, [])
    self.assertFilter([fkgtB, fkgtA], vs, [])
    self.assertFilter([fkgtB, fkgtB], vs, [])

    fkltB = Filter('key', '<', '/B')

    self.assertTrue(fkltB(v1))
    self.assertTrue(fkltB(v2))
    self.assertTrue(fkltB(v3))

    self.assertTrue(fkltB.valuePasses('/A'))
    self.assertFalse(fkltB.valuePasses('/BCDEG'))
    self.assertFalse(fkltB.valuePasses('/ZCDEFDSA/fdsafdsa/fdsafdsaf'))
    self.assertTrue(fkltB.valuePasses('/6353456346543'))
    self.assertTrue(fkltB.valuePasses('.'))
    self.assertFalse(fkltB.valuePasses('A'))
    self.assertFalse(fkltB.valuePasses('afsdafdsa'))

    self.assertFilter(fkltB, vs, vs)

    fkgtAB = Filter('key', '>', '/AB')

    self.assertTrue(fkgtAB(v1))
    self.assertTrue(fkgtAB(v2))
    self.assertTrue(fkgtAB(v3))

    self.assertFalse(fkgtAB.valuePasses('/A'))
    self.assertTrue(fkgtAB.valuePasses('/BCDEG'))
    self.assertTrue(fkgtAB.valuePasses('/ZCDEFDSA/fdsafdsa/fdsafdsaf'))
    self.assertFalse(fkgtAB.valuePasses('/6353456346543'))
    self.assertFalse(fkgtAB.valuePasses('.'))
    self.assertTrue(fkgtAB.valuePasses('A'))
    self.assertTrue(fkgtAB.valuePasses('afsdafdsa'))

    self.assertFilter(fkgtAB, vs, vs)
    self.assertFilter([fkgtAB, fkltB], vs, vs)
    self.assertFilter([fkltB, fkgtAB], vs, vs)

    fgtet1 = Filter('committed', '>=', t1)
    fgtet2 = Filter('committed', '>=', t2)
    fgtet3 = Filter('committed', '>=', t3)

    self.assertTrue(fgtet1(v1))
    self.assertTrue(fgtet1(v2))
    self.assertTrue(fgtet1(v3))

    self.assertFalse(fgtet2(v1))
    self.assertTrue(fgtet2(v2))
    self.assertTrue(fgtet2(v3))

    self.assertFalse(fgtet3(v1))
    self.assertFalse(fgtet3(v2))
    self.assertTrue(fgtet3(v3))

    self.assertFilter(fgtet1, vs, vs)
    self.assertFilter(fgtet2, vs, [v2, v3])
    self.assertFilter(fgtet3, vs, [v3])

    fltet1 = Filter('committed', '<=', t1)
    fltet2 = Filter('committed', '<=', t2)
    fltet3 = Filter('committed', '<=', t3)

    self.assertTrue(fltet1(v1))
    self.assertFalse(fltet1(v2))
    self.assertFalse(fltet1(v3))

    self.assertTrue(fltet2(v1))
    self.assertTrue(fltet2(v2))
    self.assertFalse(fltet2(v3))

    self.assertTrue(fltet3(v1))
    self.assertTrue(fltet3(v2))
    self.assertTrue(fltet3(v3))

    self.assertFilter(fltet1, vs, [v1])
    self.assertFilter(fltet2, vs, [v1, v2])
    self.assertFilter(fltet3, vs, vs)

    self.assertFilter([fgtet2, fltet2], vs, [v2])
    self.assertFilter([fgtet1, fltet3], vs, vs)
    self.assertFilter([fgtet3, fltet1], vs, [])

    feqt1 = Filter('committed', '=', t1)
    feqt2 = Filter('committed', '=', t2)
    feqt3 = Filter('committed', '=', t3)

    self.assertTrue(feqt1(v1))
    self.assertFalse(feqt1(v2))
    self.assertFalse(feqt1(v3))

    self.assertFalse(feqt2(v1))
    self.assertTrue(feqt2(v2))
    self.assertFalse(feqt2(v3))

    self.assertFalse(feqt3(v1))
    self.assertFalse(feqt3(v2))
    self.assertTrue(feqt3(v3))

    self.assertFilter(feqt1, vs, [v1])
    self.assertFilter(feqt2, vs, [v2])
    self.assertFilter(feqt3, vs, [v3])

  def test_none(self):
    # test query against None
    feqnone = Filter('val', '=', None)
    vs = [{'val': None}, {'val': 'something'}]
    self.assertFilter(feqnone, vs, vs[0:1])

    feqzero = Filter('val', '=', 0)
    vs = [{'val': 0}, {'val': None}]
    self.assertFilter(feqzero, vs, vs[0:1])

  def test_object(self):
    t1 = nanotime.now()
    t2 = nanotime.now()

    f1 = Filter('key', '>', '/A')
    f2 = Filter('key', '<', '/A')
    f3 = Filter('committed', '=', t1)
    f4 = Filter('committed', '>=', t2)

    self.assertEqual(f1, eval(repr(f1)))
    self.assertEqual(f2, eval(repr(f2)))
    self.assertEqual(f3, eval(repr(f3)))
    self.assertEqual(f4, eval(repr(f4)))

    self.assertEqual(str(f1), 'key > /A')
    self.assertEqual(str(f2), 'key < /A')
    self.assertEqual(str(f3), 'committed = %s' % t1)
    self.assertEqual(str(f4), 'committed >= %s' % t2)

    self.assertEqual(f1, Filter('key', '>', '/A'))
    self.assertEqual(f2, Filter('key', '<', '/A'))
    self.assertEqual(f3, Filter('committed', '=', t1))
    self.assertEqual(f4, Filter('committed', '>=', t2))

    self.assertNotEqual(f2, Filter('key', '>', '/A'))
    self.assertNotEqual(f1, Filter('key', '<', '/A'))
    self.assertNotEqual(f4, Filter('committed', '=', t1))
    self.assertNotEqual(f3, Filter('committed', '>=', t2))

    self.assertEqual(hash(f1), hash(Filter('key', '>', '/A')))
    self.assertEqual(hash(f2), hash(Filter('key', '<', '/A')))
    self.assertEqual(hash(f3), hash(Filter('committed', '=', t1)))
    self.assertEqual(hash(f4), hash(Filter('committed', '>=', t2)))

    self.assertNotEqual(hash(f2), hash(Filter('key', '>', '/A')))
    self.assertNotEqual(hash(f1), hash(Filter('key', '<', '/A')))
    self.assertNotEqual(hash(f4), hash(Filter('committed', '=', t1)))
    self.assertNotEqual(hash(f3), hash(Filter('committed', '>=', t2)))



class TestOrder(unittest.TestCase):

  def test_basic(self):
    o1 = Order('key')
    o2 = Order('+committed')
    o3 = Order('-created')

    v1, v2, v3 = version_objects()

    # test  isAscending
    self.assertTrue(o1.isAscending())
    self.assertTrue(o2.isAscending())
    self.assertFalse(o3.isAscending())

    # test keyfn
    self.assertEqual(o1.keyfn(v1), (v1['key']))
    self.assertEqual(o1.keyfn(v2), (v2['key']))
    self.assertEqual(o1.keyfn(v3), (v3['key']))
    self.assertEqual(o1.keyfn(v1), (v2['key']))
    self.assertEqual(o1.keyfn(v1), (v3['key']))

    self.assertEqual(o2.keyfn(v1),    (v1['committed']))
    self.assertEqual(o2.keyfn(v2),    (v2['committed']))
    self.assertEqual(o2.keyfn(v3),    (v3['committed']))
    self.assertNotEqual(o2.keyfn(v1), (v2['committed']))
    self.assertNotEqual(o2.keyfn(v1), (v3['committed']))

    self.assertEqual(o3.keyfn(v1),    (v1['created']))
    self.assertEqual(o3.keyfn(v2),    (v2['created']))
    self.assertEqual(o3.keyfn(v3),    (v3['created']))
    self.assertNotEqual(o3.keyfn(v1), (v2['created']))
    self.assertNotEqual(o3.keyfn(v1), (v3['created']))

    # test sorted
    self.assertEqual(Order.sorted([v3, v2, v1], [o1]), [v3, v2, v1])
    self.assertEqual(Order.sorted([v3, v2, v1], [o1, o2]), [v1, v2, v3])
    self.assertEqual(Order.sorted([v1, v3, v2], [o1, o3]), [v3, v2, v1])
    self.assertEqual(Order.sorted([v3, v2, v1], [o1, o2, o3]), [v1, v2, v3])
    self.assertEqual(Order.sorted([v1, v3, v2], [o1, o3, o2]), [v3, v2, v1])

    self.assertEqual(Order.sorted([v3, v2, v1], [o2]), [v1, v2, v3])
    self.assertEqual(Order.sorted([v3, v2, v1], [o2, o1]), [v1, v2, v3])
    self.assertEqual(Order.sorted([v3, v2, v1], [o2, o3]), [v1, v2, v3])
    self.assertEqual(Order.sorted([v3, v2, v1], [o2, o1, o3]), [v1, v2, v3])
    self.assertEqual(Order.sorted([v3, v2, v1], [o2, o3, o1]), [v1, v2, v3])

    self.assertEqual(Order.sorted([v1, v2, v3], [o3]), [v3, v2, v1])
    self.assertEqual(Order.sorted([v1, v2, v3], [o3, o2]), [v3, v2, v1])
    self.assertEqual(Order.sorted([v1, v2, v3], [o3, o1]), [v3, v2, v1])
    self.assertEqual(Order.sorted([v1, v2, v3], [o3, o2, o1]), [v3, v2, v1])
    self.assertEqual(Order.sorted([v1, v2, v3], [o3, o1, o2]), [v3, v2, v1])


  def test_object(self):
    self.assertEqual(Order('key'), eval(repr(Order('key'))))
    self.assertEqual(Order('+committed'), eval(repr(Order('+committed'))))
    self.assertEqual(Order('-created'), eval(repr(Order('-created'))))

    self.assertEqual(str(Order('key')), '+key')
    self.assertEqual(str(Order('+committed')), '+committed')
    self.assertEqual(str(Order('-created')), '-created')

    self.assertEqual(Order('key'), Order('+key'))
    self.assertEqual(Order('-key'), Order('-key'))
    self.assertEqual(Order('+committed'), Order('+committed'))

    self.assertNotEqual(Order('key'), Order('-key'))
    self.assertNotEqual(Order('+key'), Order('-key'))
    self.assertNotEqual(Order('+committed'), Order('+key'))

    self.assertEqual(hash(Order('+key')), hash(Order('+key')))
    self.assertEqual(hash(Order('-key')), hash(Order('-key')))
    self.assertNotEqual(hash(Order('+key')), hash(Order('-key')))
    self.assertEqual(hash(Order('+committed')), hash(Order('+committed')))
    self.assertNotEqual(hash(Order('+committed')), hash(Order('+key')))


class TestQuery(unittest.TestCase):

  def test_basic(self):

    now = nanotime.now().nanoseconds()

    q1 = Query(Key('/'), limit=100)
    q2 = Query(Key('/'), offset=200)
    q3 = Query(Key('/'), object_getattr=getattr)

    q1.offset = 300
    q3.limit = 1

    q1.filter('key', '>', '/ABC')
    q1.filter('created', '>', now)

    q2.order('key')
    q2.order('-created')

    q1d = {'key': '/', 'limit':100, 'offset':300, \
      'filter': [['key', '>', '/ABC'], ['created', '>', now]] }

    q2d = {'key': '/', 'offset':200, 'order': ['+key', '-created'] }

    q3d = {'key': '/', 'limit':1}

    self.assertEqual(q1.dict(), q1d)
    self.assertEqual(q2.dict(), q2d)
    self.assertEqual(q3.dict(), q3d)

    self.assertEqual(q1, Query.from_dict(q1d))
    self.assertEqual(q2, Query.from_dict(q2d))
    self.assertEqual(q3, Query.from_dict(q3d))

    self.assertEqual(q1, eval(repr(q1)))
    self.assertEqual(q2, eval(repr(q2)))
    self.assertEqual(q3, eval(repr(q3)))

    self.assertEqual(q1, q1.copy())
    self.assertEqual(q2, q2.copy())
    self.assertEqual(q3, q3.copy())


  def test_cursor(self):

    k = Key('/')

    self.assertRaises(ValueError, Cursor, None, None)
    self.assertRaises(ValueError, Cursor, Query(Key('/')), None)
    self.assertRaises(ValueError, Cursor, None, [1])
    c = Cursor(Query(k), [1, 2, 3, 4, 5]) # should not raise

    self.assertEqual(c.skipped, 0)
    self.assertEqual(c.returned, 0)
    self.assertEqual(c._iterable, [1, 2, 3, 4, 5])

    c.skipped = 1
    c.returned = 2
    self.assertEqual(c.skipped, 1)
    self.assertEqual(c.returned, 2)

    c._skipped_inc(None)
    c._skipped_inc(None)
    self.assertEqual(c.skipped, 3)

    c._returned_inc(None)
    c._returned_inc(None)
    c._returned_inc(None)
    self.assertEqual(c.returned, 5)

    self.subtest_cursor(Query(k), [5, 4, 3, 2, 1], [5, 4, 3, 2, 1])
    self.subtest_cursor(Query(k, limit=3), [5, 4, 3, 2, 1], [5, 4, 3])
    self.subtest_cursor(Query(k, limit=0), [5, 4, 3, 2, 1], [])
    self.subtest_cursor(Query(k, offset=2), [5, 4, 3, 2, 1], [3, 2, 1])
    self.subtest_cursor(Query(k, offset=5), [5, 4, 3, 2, 1], [])
    self.subtest_cursor(Query(k, limit=2, offset=2), [5, 4, 3, 2, 1], [3, 2])

    v1, v2, v3 = version_objects()
    vs = [v1, v2, v3]

    t1 = v1['committed']
    t2 = v2['committed']
    t3 = v3['committed']

    self.subtest_cursor(Query(k), vs, vs)
    self.subtest_cursor(Query(k, limit=2), vs, [v1, v2])
    self.subtest_cursor(Query(k, offset=1), vs, [v2, v3])
    self.subtest_cursor(Query(k, offset=1, limit=1), vs, [v2])

    self.subtest_cursor(Query(k).filter('committed', '>=', t2), vs, [v2, v3])
    self.subtest_cursor(Query(k).filter('committed', '<=', t1), vs, [v1])

    self.subtest_cursor(Query(k).order('+committed'), vs, [v1, v2, v3])
    self.subtest_cursor(Query(k).order('-created'), vs, [v3, v2, v1])


  def subtest_cursor(self, query, iterable, expected_results):

    self.assertRaises(ValueError, Cursor, None, None)
    self.assertRaises(ValueError, Cursor, query, None)
    self.assertRaises(ValueError, Cursor, None, iterable)
    cursor = Cursor(query, iterable)
    self.assertEqual(cursor.skipped, 0)
    self.assertEqual(cursor.returned, 0)

    cursor._ensure_modification_is_safe()
    cursor.apply_filter()
    cursor.apply_order()
    cursor.apply_offset()
    cursor.apply_limit()

    cursor_results = []
    for i in cursor:
      self.assertRaises(AssertionError, cursor._ensure_modification_is_safe)
      self.assertRaises(AssertionError, cursor.apply_filter)
      self.assertRaises(AssertionError, cursor.apply_order)
      self.assertRaises(AssertionError, cursor.apply_offset)
      self.assertRaises(AssertionError, cursor.apply_limit)
      cursor_results.append(i)

    # ensure iteration happens only once.
    self.assertRaises(RuntimeError, iter, cursor)

    self.assertEqual(cursor_results, expected_results)
    self.assertEqual(cursor.returned, len(expected_results))
    self.assertEqual(cursor.skipped, query.offset)
    if query.limit:
      self.assertTrue(cursor.returned <= query.limit)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = test_serialize

import unittest

from ..key import Key
from ..basic import DictDatastore
from ..serialize import *
from test_basic import TestDatastore

import pickle
import bson

monkey_patch_bson(bson)



class TestSerialize(TestDatastore):


  def test_basic(self):

    value = 'test_value_%s' % self
    values_raw = [{'value': i} for i in xrange(0, 1000)]
    values_json = map(json.dumps, values_raw)

    # test protocol
    self.assertRaises(NotImplementedError, Serializer.loads, value)
    self.assertRaises(NotImplementedError, Serializer.dumps, value)

    # test non serializer
    self.assertEqual(NonSerializer.loads(value), value)
    self.assertEqual(NonSerializer.dumps(value), value)
    self.assertTrue(NonSerializer.loads(value) is value)
    self.assertTrue(NonSerializer.dumps(value) is value)

    # test generators
    values_serialized = list(serialized_gen(json, values_raw))
    values_deserialized = list(deserialized_gen(json, values_serialized))
    self.assertEqual(values_serialized, values_json)
    self.assertEqual(values_deserialized, values_raw)

    # test stack
    stack = Stack([json, map_serializer, bson])
    values_serialized = map(stack.dumps, values_raw)
    values_deserialized = map(stack.loads, values_serialized)
    self.assertEqual(values_deserialized, values_raw)


  def subtest_serializer_shim(self, serializer, numelems=100):

    child = DictDatastore()
    shim = SerializerShimDatastore(child, serializer=serializer)

    values_raw = [{'value': i} for i in xrange(0, numelems)]

    values_serial = [serializer.dumps(v) for v in values_raw]
    values_deserial = [serializer.loads(v) for v in values_serial]
    self.assertEqual(values_deserial, values_raw)

    for value in values_raw:
      key = Key(value['value'])
      value_serialized = serializer.dumps(value)

      # should not be there yet
      self.assertFalse(shim.contains(key))
      self.assertEqual(shim.get(key), None)

      # put (should be there)
      shim.put(key, value)
      self.assertTrue(shim.contains(key))
      self.assertEqual(shim.get(key), value)

      # make sure underlying DictDatastore is storing the serialized value.
      self.assertEqual(shim.child_datastore.get(key), value_serialized)

      # delete (should not be there)
      shim.delete(key)
      self.assertFalse(shim.contains(key))
      self.assertEqual(shim.get(key), None)

      # make sure manipulating underlying DictDatastore works equally well.
      shim.child_datastore.put(key, value_serialized)
      self.assertTrue(shim.contains(key))
      self.assertEqual(shim.get(key), value)

      shim.child_datastore.delete(key)
      self.assertFalse(shim.contains(key))
      self.assertEqual(shim.get(key), None)

    if serializer is not bson: # bson can't handle non mapping types
      self.subtest_simple([shim], numelems)


  def test_serializer_shim(self):

    self.subtest_serializer_shim(json)
    self.subtest_serializer_shim(prettyjson)
    self.subtest_serializer_shim(pickle)
    self.subtest_serializer_shim(map_serializer)
    self.subtest_serializer_shim(bson)
    self.subtest_serializer_shim(default_serializer) # module default

    self.subtest_serializer_shim(Stack([map_serializer]))
    self.subtest_serializer_shim(Stack([map_serializer, bson]))
    self.subtest_serializer_shim(Stack([json, map_serializer, bson]))
    self.subtest_serializer_shim(Stack([json, map_serializer, bson, pickle]))


  def test_has_interface_check(self):
    self.assertTrue(hasattr(Serializer, 'implements_serializer_interface'))


  def test_interface_check_returns_true_for_valid_serializers(self):
    class S(object):
      def loads(self, foo): return foo
      def dumps(self, foo): return foo

    self.assertTrue(Serializer.implements_serializer_interface(S))
    self.assertTrue(Serializer.implements_serializer_interface(json))
    self.assertTrue(Serializer.implements_serializer_interface(pickle))
    self.assertTrue(Serializer.implements_serializer_interface(Serializer))


  def test_interface_check_returns_false_for_invalid_serializers(self):
    class S1(object):
      pass

    class S2(object):
      def loads(self, foo):
        return foo

    class S3(object):
      def dumps(self, foo):
        return foo

    class S4(object):
      def dumps(self, foo):
        return foo

    class S5(object):
      loads = 'loads'
      dumps = 'dumps'

    self.assertFalse(Serializer.implements_serializer_interface(S1))
    self.assertFalse(Serializer.implements_serializer_interface(S2))
    self.assertFalse(Serializer.implements_serializer_interface(S3))
    self.assertFalse(Serializer.implements_serializer_interface(S4))
    self.assertFalse(Serializer.implements_serializer_interface(S5))


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = fasthash

import hashlib

def hash(tohash):
  '''fast, deterministic hash function'''
  return int(hashlib.sha1(str(tohash)).hexdigest(), 16)

########NEW FILE########
__FILENAME__ = test

import os
import shutil
import unittest

from datastore import serialize
from datastore.core.test.test_basic import TestDatastore

from . import FileSystemDatastore


class TestFileSystemDatastore(TestDatastore):

  tmp = os.path.normpath('/tmp/datastore.test.fs')

  def setUp(self):
    if os.path.exists(self.tmp):
      shutil.rmtree(self.tmp)

  def tearDown(self):
    shutil.rmtree(self.tmp)

  def test_datastore(self):
    dirs = map(str, range(0, 4))
    dirs = map(lambda d: os.path.join(self.tmp, d), dirs)
    fses = map(FileSystemDatastore, dirs)
    dses = map(serialize.shim, fses)
    self.subtest_simple(dses, numelems=500)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# datastore documentation build configuration file, created by
# sphinx-quickstart on Thu Dec 22 01:26:05 2011.
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

sys.path.insert(0, os.path.abspath('../'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.intersphinx', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'datastore'
copyright = u'2011, Juan Batiz-Benet'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3'
# The full version, including alpha/beta/rc tags.
release = '0.3.0'

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
exclude_patterns = ['.build']

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
html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

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
html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

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
htmlhelp_basename = 'datastoredoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'datastore.tex', u'datastore Documentation',
   u'Juan Batiz-Benet', 'manual'),
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
    ('index', 'datastore', u'datastore Documentation',
     [u'Juan Batiz-Benet'], 1)
]


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

# -- Import Mocking for rtfd.org -----------------------------------------------

# some modules have large dependencies or even c/c++ dependencies.
# for autodoc to compile correctly in rtfd.org and other environments without
# the presence of these dependencies, we must mock their imports.

import sys

class Mock(object):
  def __init__(self, *args, **kwargs):
    pass

  def __getattr__(self, name):
    return Mock()

# name all modules to mock
MOCK_MODULES = [
  'bson',
  'pymongo',
  'pylibmc',
  'redis',
  'pylru',
  'dulwich'
]

for mod_name in MOCK_MODULES:
  sys.modules[mod_name] = Mock()

########NEW FILE########
