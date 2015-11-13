__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# PyMongo documentation build configuration file
#
# This file is execfile()d with the current directory set to its containing dir.

import sys
import os
sys.path.append(os.path.abspath('..'))

import pycassa

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'pycassa'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = pycassa.__version__
# The full version, including alpha/beta/rc tags.
release = pycassa.__version__

# List of documents that shouldn't be included in the build.
unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# -- Options for extensions ----------------------------------------------------
autoclass_content = 'both'

# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

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
html_favicon = 'favicon.ico'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'pycassa' + release.replace('.', '_')


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'pycassa.tex', 'pycassa Documentation',
   'Jonathan Hseu', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = batch
"""
The batch interface allows insert, update, and remove operations to be performed
in batches. This allows a convenient mechanism for streaming updates or doing a
large number of operations while reducing number of RPC roundtrips.

Batch mutator objects are synchronized and can be safely passed around threads.

.. code-block:: python

    >>> b = cf.batch(queue_size=10)
    >>> b.insert('key1', {'col1':'value11', 'col2':'value21'})
    >>> b.insert('key2', {'col1':'value12', 'col2':'value22'}, ttl=15)
    >>> b.remove('key1', ['col2'])
    >>> b.remove('key2')
    >>> b.send()

One can use the `queue_size` argument to control how many mutations will be
queued before an automatic :meth:`send` is performed. This allows simple streaming
of updates. If set to ``None``, automatic checkpoints are disabled. Default is 100.

Supercolumns are supported:

.. code-block:: python

    >>> b = scf.batch()
    >>> b.insert('key1', {'supercol1': {'colA':'value1a', 'colB':'value1b'}
    ...                  {'supercol2': {'colA':'value2a', 'colB':'value2b'}})
    >>> b.remove('key1', ['colA'], 'supercol1')
    >>> b.send()

You may also create a :class:`.Mutator` directly, allowing operations
on multiple column families:

.. code-block:: python

    >>> b = Mutator(pool)
    >>> b.insert(cf, 'key1', {'col1':'value1', 'col2':'value2'})
    >>> b.insert(supercf, 'key1', {'subkey1': {'col1':'value1', 'col2':'value2'}})
    >>> b.send()

.. note:: This interface does not implement atomic operations across column
          families. All the limitations of the `batch_mutate` Thrift API call
          applies. Remember, a mutation in Cassandra is always atomic per key per
          column family only.

.. note:: If a single operation in a batch fails, the whole batch fails.

In addition mutators can be used as context managers, where an implicit
:meth:`send` will be called upon exit.

.. code-block:: python

    >>> with cf.batch() as b:
    ...     b.insert('key1', {'col1':'value11', 'col2':'value21'})
    ...     b.insert('key2', {'col1':'value12', 'col2':'value22'})

Calls to :meth:`insert` and :meth:`remove` can also be chained:

.. code-block:: python

    >>> cf.batch().remove('foo').remove('bar').send()

To use atomic batches (supported in Cassandra 1.2 and later), pass the atomic
option in when creating the batch:

.. code-block:: python

    >>> cf.batch(atomic=True)

or when sending it:

.. code-block:: python

    >>> b = cf.batch()
    >>> b.insert('key1', {'col1':'val2'})
    >>> b.insert('key2', {'col1':'val2'})
    >>> b.send(atomic=True)

"""

import threading
from pycassa.cassandra.ttypes import (ConsistencyLevel, Deletion, Mutation, SlicePredicate)

__all__ = ['Mutator', 'CfMutator']

class Mutator(object):
    """
    Batch update convenience mechanism.

    Queues insert/update/remove operations and executes them when the queue
    is full or `send` is called explicitly.
    """

    def __init__(self, pool, queue_size=100, write_consistency_level=None, allow_retries=True, atomic=False):
        """
        `pool` is the :class:`~pycassa.pool.ConnectionPool` that will be used
        for operations.

        After `queue_size` operations, :meth:`send()` will be executed
        automatically.  Use 0 to disable automatic sends.
        """
        self._buffer = []
        self._lock = threading.RLock()
        self.pool = pool
        self.limit = queue_size
        self.allow_retries = allow_retries
        self.atomic = atomic
        if write_consistency_level is None:
            self.write_consistency_level = ConsistencyLevel.ONE
        else:
            self.write_consistency_level = write_consistency_level

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.send()

    def _enqueue(self, key, column_family, mutations):
        self._lock.acquire()
        try:
            mutation = (key, column_family.column_family, mutations)
            self._buffer.append(mutation)
            if self.limit and len(self._buffer) >= self.limit:
                self.send()
        finally:
            self._lock.release()
        return self

    def send(self, write_consistency_level=None, atomic=None):
        """ Sends all operations currently in the batch and clears the batch. """
        if write_consistency_level is None:
            write_consistency_level = self.write_consistency_level
        if atomic is None:
            atomic = self.atomic
        mutations = {}
        conn = None
        self._lock.acquire()
        try:
            for key, column_family, cols in self._buffer:
                mutations.setdefault(key, {}).setdefault(column_family, []).extend(cols)
            if mutations:
                conn = self.pool.get()
                mutatefn = conn.atomic_batch_mutate if atomic else conn.batch_mutate
                mutatefn(mutations, write_consistency_level,
                         allow_retries=self.allow_retries)
            self._buffer = []
        finally:
            if conn:
                conn.return_to_pool()
            self._lock.release()

    def insert(self, column_family, key, columns, timestamp=None, ttl=None):
        """
        Adds a single row insert to the batch.

        `column_family` is the :class:`~pycassa.columnfamily.ColumnFamily`
        that the insert will be executed on.

        If this is used on a counter column family, integers may be used for
        column values, and they will be taken as counter adjustments.

        """
        if columns:
            if timestamp is None:
                timestamp = column_family.timestamp()
            packed_key = column_family._pack_key(key)
            mut_list = column_family._make_mutation_list(columns, timestamp, ttl)
            self._enqueue(packed_key, column_family, mut_list)
        return self

    def remove(self, column_family, key, columns=None, super_column=None, timestamp=None):
        """
        Adds a single row remove to the batch.

        `column_family` is the :class:`~pycassa.columnfamily.ColumnFamily`
        that the remove will be executed on.

        """
        if timestamp is None:
            timestamp = column_family.timestamp()
        deletion = Deletion(timestamp=timestamp)
        _pack_name = column_family._pack_name
        if super_column is not None:
            deletion.super_column = _pack_name(super_column, True)
        if columns is not None:
            is_super = column_family.super and super_column is None
            packed_cols = [_pack_name(col, is_super) for col in columns]
            deletion.predicate = SlicePredicate(column_names=packed_cols)
        mutation = Mutation(deletion=deletion)
        packed_key = column_family._pack_key(key)
        self._enqueue(packed_key, column_family, (mutation,))
        return self


class CfMutator(Mutator):
    """
    A :class:`~pycassa.batch.Mutator` that deals only with one column family.
    """

    def __init__(self, column_family, queue_size=100, write_consistency_level=None,
                 allow_retries=True, atomic=False):
        """
        `column_family` is the :class:`~pycassa.columnfamily.ColumnFamily`
        that all operations will be executed on.
        """
        wcl = write_consistency_level or column_family.write_consistency_level
        Mutator.__init__(self, column_family.pool, queue_size, wcl, allow_retries, atomic)
        self._column_family = column_family

    def insert(self, key, cols, timestamp=None, ttl=None):
        """ Adds a single row insert to the batch. """
        return Mutator.insert(self, self._column_family, key, cols, timestamp, ttl)

    def remove(self, key, columns=None, super_column=None, timestamp=None):
        """ Adds a single row remove to the batch. """
        return Mutator.remove(self, self._column_family, key,
                              columns, super_column, timestamp)

########NEW FILE########
__FILENAME__ = Cassandra
#
# Autogenerated by Thrift Compiler (0.9.0)
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#
#  options string: py:new_style
#

from thrift.Thrift import TType, TMessageType, TException, TApplicationException
from ttypes import *
from thrift.Thrift import TProcessor
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TProtocol
try:
  from thrift.protocol import fastbinary
except:
  fastbinary = None


class Iface(object):
  def login(self, auth_request):
    """
    Parameters:
     - auth_request
    """
    pass

  def set_keyspace(self, keyspace):
    """
    Parameters:
     - keyspace
    """
    pass

  def get(self, key, column_path, consistency_level):
    """
    Get the Column or SuperColumn at the given column_path. If no value is present, NotFoundException is thrown. (This is
    the only method that can throw an exception under non-failure conditions.)

    Parameters:
     - key
     - column_path
     - consistency_level
    """
    pass

  def get_slice(self, key, column_parent, predicate, consistency_level):
    """
    Get the group of columns contained by column_parent (either a ColumnFamily name or a ColumnFamily/SuperColumn name
    pair) specified by the given SlicePredicate. If no matching values are found, an empty list is returned.

    Parameters:
     - key
     - column_parent
     - predicate
     - consistency_level
    """
    pass

  def get_count(self, key, column_parent, predicate, consistency_level):
    """
    returns the number of columns matching <code>predicate</code> for a particular <code>key</code>,
    <code>ColumnFamily</code> and optionally <code>SuperColumn</code>.

    Parameters:
     - key
     - column_parent
     - predicate
     - consistency_level
    """
    pass

  def multiget_slice(self, keys, column_parent, predicate, consistency_level):
    """
    Performs a get_slice for column_parent and predicate for the given keys in parallel.

    Parameters:
     - keys
     - column_parent
     - predicate
     - consistency_level
    """
    pass

  def multiget_count(self, keys, column_parent, predicate, consistency_level):
    """
    Perform a get_count in parallel on the given list<binary> keys. The return value maps keys to the count found.

    Parameters:
     - keys
     - column_parent
     - predicate
     - consistency_level
    """
    pass

  def get_range_slices(self, column_parent, predicate, range, consistency_level):
    """
    returns a subset of columns for a contiguous range of keys.

    Parameters:
     - column_parent
     - predicate
     - range
     - consistency_level
    """
    pass

  def get_paged_slice(self, column_family, range, start_column, consistency_level):
    """
    returns a range of columns, wrapping to the next rows if necessary to collect max_results.

    Parameters:
     - column_family
     - range
     - start_column
     - consistency_level
    """
    pass

  def get_indexed_slices(self, column_parent, index_clause, column_predicate, consistency_level):
    """
    Returns the subset of columns specified in SlicePredicate for the rows matching the IndexClause
    @deprecated use get_range_slices instead with range.row_filter specified

    Parameters:
     - column_parent
     - index_clause
     - column_predicate
     - consistency_level
    """
    pass

  def insert(self, key, column_parent, column, consistency_level):
    """
    Insert a Column at the given column_parent.column_family and optional column_parent.super_column.

    Parameters:
     - key
     - column_parent
     - column
     - consistency_level
    """
    pass

  def add(self, key, column_parent, column, consistency_level):
    """
    Increment or decrement a counter.

    Parameters:
     - key
     - column_parent
     - column
     - consistency_level
    """
    pass

  def remove(self, key, column_path, timestamp, consistency_level):
    """
    Remove data from the row specified by key at the granularity specified by column_path, and the given timestamp. Note
    that all the values in column_path besides column_path.column_family are truly optional: you can remove the entire
    row by just specifying the ColumnFamily, or you can remove a SuperColumn or a single Column by specifying those levels too.

    Parameters:
     - key
     - column_path
     - timestamp
     - consistency_level
    """
    pass

  def remove_counter(self, key, path, consistency_level):
    """
    Remove a counter at the specified location.
    Note that counters have limited support for deletes: if you remove a counter, you must wait to issue any following update
    until the delete has reached all the nodes and all of them have been fully compacted.

    Parameters:
     - key
     - path
     - consistency_level
    """
    pass

  def batch_mutate(self, mutation_map, consistency_level):
    """
      Mutate many columns or super columns for many row keys. See also: Mutation.

      mutation_map maps key to column family to a list of Mutation objects to take place at that scope.
    *

    Parameters:
     - mutation_map
     - consistency_level
    """
    pass

  def atomic_batch_mutate(self, mutation_map, consistency_level):
    """
      Atomically mutate many columns or super columns for many row keys. See also: Mutation.

      mutation_map maps key to column family to a list of Mutation objects to take place at that scope.
    *

    Parameters:
     - mutation_map
     - consistency_level
    """
    pass

  def truncate(self, cfname):
    """
    Truncate will mark and entire column family as deleted.
    From the user's perspective a successful call to truncate will result complete data deletion from cfname.
    Internally, however, disk space will not be immediatily released, as with all deletes in cassandra, this one
    only marks the data as deleted.
    The operation succeeds only if all hosts in the cluster at available and will throw an UnavailableException if
    some hosts are down.

    Parameters:
     - cfname
    """
    pass

  def describe_schema_versions(self, ):
    """
    for each schema version present in the cluster, returns a list of nodes at that version.
    hosts that do not respond will be under the key DatabaseDescriptor.INITIAL_VERSION.
    the cluster is all on the same version if the size of the map is 1.
    """
    pass

  def describe_keyspaces(self, ):
    """
    list the defined keyspaces in this cluster
    """
    pass

  def describe_cluster_name(self, ):
    """
    get the cluster name
    """
    pass

  def describe_version(self, ):
    """
    get the thrift api version
    """
    pass

  def describe_ring(self, keyspace):
    """
    get the token ring: a map of ranges to host addresses,
    represented as a set of TokenRange instead of a map from range
    to list of endpoints, because you can't use Thrift structs as
    map keys:
    https://issues.apache.org/jira/browse/THRIFT-162

    for the same reason, we can't return a set here, even though
    order is neither important nor predictable.

    Parameters:
     - keyspace
    """
    pass

  def describe_token_map(self, ):
    """
    get the mapping between token->node ip
    without taking replication into consideration
    https://issues.apache.org/jira/browse/CASSANDRA-4092
    """
    pass

  def describe_partitioner(self, ):
    """
    returns the partitioner used by this cluster
    """
    pass

  def describe_snitch(self, ):
    """
    returns the snitch used by this cluster
    """
    pass

  def describe_keyspace(self, keyspace):
    """
    describe specified keyspace

    Parameters:
     - keyspace
    """
    pass

  def describe_splits(self, cfName, start_token, end_token, keys_per_split):
    """
    experimental API for hadoop/parallel query support.
    may change violently and without warning.

    returns list of token strings such that first subrange is (list[0], list[1]],
    next is (list[1], list[2]], etc.

    Parameters:
     - cfName
     - start_token
     - end_token
     - keys_per_split
    """
    pass

  def trace_next_query(self, ):
    """
    Enables tracing for the next query in this connection and returns the UUID for that trace session
    The next query will be traced idependently of trace probability and the returned UUID can be used to query the trace keyspace
    """
    pass

  def describe_splits_ex(self, cfName, start_token, end_token, keys_per_split):
    """
    Parameters:
     - cfName
     - start_token
     - end_token
     - keys_per_split
    """
    pass

  def system_add_column_family(self, cf_def):
    """
    adds a column family. returns the new schema id.

    Parameters:
     - cf_def
    """
    pass

  def system_drop_column_family(self, column_family):
    """
    drops a column family. returns the new schema id.

    Parameters:
     - column_family
    """
    pass

  def system_add_keyspace(self, ks_def):
    """
    adds a keyspace and any column families that are part of it. returns the new schema id.

    Parameters:
     - ks_def
    """
    pass

  def system_drop_keyspace(self, keyspace):
    """
    drops a keyspace and any column families that are part of it. returns the new schema id.

    Parameters:
     - keyspace
    """
    pass

  def system_update_keyspace(self, ks_def):
    """
    updates properties of a keyspace. returns the new schema id.

    Parameters:
     - ks_def
    """
    pass

  def system_update_column_family(self, cf_def):
    """
    updates properties of a column family. returns the new schema id.

    Parameters:
     - cf_def
    """
    pass

  def execute_cql_query(self, query, compression):
    """
    Executes a CQL (Cassandra Query Language) statement and returns a
    CqlResult containing the results.

    Parameters:
     - query
     - compression
    """
    pass

  def execute_cql3_query(self, query, compression, consistency):
    """
    Parameters:
     - query
     - compression
     - consistency
    """
    pass

  def prepare_cql_query(self, query, compression):
    """
    Prepare a CQL (Cassandra Query Language) statement by compiling and returning
    - the type of CQL statement
    - an id token of the compiled CQL stored on the server side.
    - a count of the discovered bound markers in the statement

    Parameters:
     - query
     - compression
    """
    pass

  def prepare_cql3_query(self, query, compression):
    """
    Parameters:
     - query
     - compression
    """
    pass

  def execute_prepared_cql_query(self, itemId, values):
    """
    Executes a prepared CQL (Cassandra Query Language) statement by passing an id token and  a list of variables
    to bind and returns a CqlResult containing the results.

    Parameters:
     - itemId
     - values
    """
    pass

  def execute_prepared_cql3_query(self, itemId, values, consistency):
    """
    Parameters:
     - itemId
     - values
     - consistency
    """
    pass

  def set_cql_version(self, version):
    """
    @deprecated This is now a no-op. Please use the CQL3 specific methods instead.

    Parameters:
     - version
    """
    pass


class Client(Iface):
  def __init__(self, iprot, oprot=None):
    self._iprot = self._oprot = iprot
    if oprot is not None:
      self._oprot = oprot
    self._seqid = 0

  def login(self, auth_request):
    """
    Parameters:
     - auth_request
    """
    self.send_login(auth_request)
    self.recv_login()

  def send_login(self, auth_request):
    self._oprot.writeMessageBegin('login', TMessageType.CALL, self._seqid)
    args = login_args()
    args.auth_request = auth_request
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_login(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = login_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.authnx is not None:
      raise result.authnx
    if result.authzx is not None:
      raise result.authzx
    return

  def set_keyspace(self, keyspace):
    """
    Parameters:
     - keyspace
    """
    self.send_set_keyspace(keyspace)
    self.recv_set_keyspace()

  def send_set_keyspace(self, keyspace):
    self._oprot.writeMessageBegin('set_keyspace', TMessageType.CALL, self._seqid)
    args = set_keyspace_args()
    args.keyspace = keyspace
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_set_keyspace(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = set_keyspace_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.ire is not None:
      raise result.ire
    return

  def get(self, key, column_path, consistency_level):
    """
    Get the Column or SuperColumn at the given column_path. If no value is present, NotFoundException is thrown. (This is
    the only method that can throw an exception under non-failure conditions.)

    Parameters:
     - key
     - column_path
     - consistency_level
    """
    self.send_get(key, column_path, consistency_level)
    return self.recv_get()

  def send_get(self, key, column_path, consistency_level):
    self._oprot.writeMessageBegin('get', TMessageType.CALL, self._seqid)
    args = get_args()
    args.key = key
    args.column_path = column_path
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_get(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = get_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.nfe is not None:
      raise result.nfe
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    raise TApplicationException(TApplicationException.MISSING_RESULT, "get failed: unknown result");

  def get_slice(self, key, column_parent, predicate, consistency_level):
    """
    Get the group of columns contained by column_parent (either a ColumnFamily name or a ColumnFamily/SuperColumn name
    pair) specified by the given SlicePredicate. If no matching values are found, an empty list is returned.

    Parameters:
     - key
     - column_parent
     - predicate
     - consistency_level
    """
    self.send_get_slice(key, column_parent, predicate, consistency_level)
    return self.recv_get_slice()

  def send_get_slice(self, key, column_parent, predicate, consistency_level):
    self._oprot.writeMessageBegin('get_slice', TMessageType.CALL, self._seqid)
    args = get_slice_args()
    args.key = key
    args.column_parent = column_parent
    args.predicate = predicate
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_get_slice(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = get_slice_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    raise TApplicationException(TApplicationException.MISSING_RESULT, "get_slice failed: unknown result");

  def get_count(self, key, column_parent, predicate, consistency_level):
    """
    returns the number of columns matching <code>predicate</code> for a particular <code>key</code>,
    <code>ColumnFamily</code> and optionally <code>SuperColumn</code>.

    Parameters:
     - key
     - column_parent
     - predicate
     - consistency_level
    """
    self.send_get_count(key, column_parent, predicate, consistency_level)
    return self.recv_get_count()

  def send_get_count(self, key, column_parent, predicate, consistency_level):
    self._oprot.writeMessageBegin('get_count', TMessageType.CALL, self._seqid)
    args = get_count_args()
    args.key = key
    args.column_parent = column_parent
    args.predicate = predicate
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_get_count(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = get_count_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    raise TApplicationException(TApplicationException.MISSING_RESULT, "get_count failed: unknown result");

  def multiget_slice(self, keys, column_parent, predicate, consistency_level):
    """
    Performs a get_slice for column_parent and predicate for the given keys in parallel.

    Parameters:
     - keys
     - column_parent
     - predicate
     - consistency_level
    """
    self.send_multiget_slice(keys, column_parent, predicate, consistency_level)
    return self.recv_multiget_slice()

  def send_multiget_slice(self, keys, column_parent, predicate, consistency_level):
    self._oprot.writeMessageBegin('multiget_slice', TMessageType.CALL, self._seqid)
    args = multiget_slice_args()
    args.keys = keys
    args.column_parent = column_parent
    args.predicate = predicate
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_multiget_slice(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = multiget_slice_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    raise TApplicationException(TApplicationException.MISSING_RESULT, "multiget_slice failed: unknown result");

  def multiget_count(self, keys, column_parent, predicate, consistency_level):
    """
    Perform a get_count in parallel on the given list<binary> keys. The return value maps keys to the count found.

    Parameters:
     - keys
     - column_parent
     - predicate
     - consistency_level
    """
    self.send_multiget_count(keys, column_parent, predicate, consistency_level)
    return self.recv_multiget_count()

  def send_multiget_count(self, keys, column_parent, predicate, consistency_level):
    self._oprot.writeMessageBegin('multiget_count', TMessageType.CALL, self._seqid)
    args = multiget_count_args()
    args.keys = keys
    args.column_parent = column_parent
    args.predicate = predicate
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_multiget_count(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = multiget_count_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    raise TApplicationException(TApplicationException.MISSING_RESULT, "multiget_count failed: unknown result");

  def get_range_slices(self, column_parent, predicate, range, consistency_level):
    """
    returns a subset of columns for a contiguous range of keys.

    Parameters:
     - column_parent
     - predicate
     - range
     - consistency_level
    """
    self.send_get_range_slices(column_parent, predicate, range, consistency_level)
    return self.recv_get_range_slices()

  def send_get_range_slices(self, column_parent, predicate, range, consistency_level):
    self._oprot.writeMessageBegin('get_range_slices', TMessageType.CALL, self._seqid)
    args = get_range_slices_args()
    args.column_parent = column_parent
    args.predicate = predicate
    args.range = range
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_get_range_slices(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = get_range_slices_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    raise TApplicationException(TApplicationException.MISSING_RESULT, "get_range_slices failed: unknown result");

  def get_paged_slice(self, column_family, range, start_column, consistency_level):
    """
    returns a range of columns, wrapping to the next rows if necessary to collect max_results.

    Parameters:
     - column_family
     - range
     - start_column
     - consistency_level
    """
    self.send_get_paged_slice(column_family, range, start_column, consistency_level)
    return self.recv_get_paged_slice()

  def send_get_paged_slice(self, column_family, range, start_column, consistency_level):
    self._oprot.writeMessageBegin('get_paged_slice', TMessageType.CALL, self._seqid)
    args = get_paged_slice_args()
    args.column_family = column_family
    args.range = range
    args.start_column = start_column
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_get_paged_slice(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = get_paged_slice_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    raise TApplicationException(TApplicationException.MISSING_RESULT, "get_paged_slice failed: unknown result");

  def get_indexed_slices(self, column_parent, index_clause, column_predicate, consistency_level):
    """
    Returns the subset of columns specified in SlicePredicate for the rows matching the IndexClause
    @deprecated use get_range_slices instead with range.row_filter specified

    Parameters:
     - column_parent
     - index_clause
     - column_predicate
     - consistency_level
    """
    self.send_get_indexed_slices(column_parent, index_clause, column_predicate, consistency_level)
    return self.recv_get_indexed_slices()

  def send_get_indexed_slices(self, column_parent, index_clause, column_predicate, consistency_level):
    self._oprot.writeMessageBegin('get_indexed_slices', TMessageType.CALL, self._seqid)
    args = get_indexed_slices_args()
    args.column_parent = column_parent
    args.index_clause = index_clause
    args.column_predicate = column_predicate
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_get_indexed_slices(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = get_indexed_slices_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    raise TApplicationException(TApplicationException.MISSING_RESULT, "get_indexed_slices failed: unknown result");

  def insert(self, key, column_parent, column, consistency_level):
    """
    Insert a Column at the given column_parent.column_family and optional column_parent.super_column.

    Parameters:
     - key
     - column_parent
     - column
     - consistency_level
    """
    self.send_insert(key, column_parent, column, consistency_level)
    self.recv_insert()

  def send_insert(self, key, column_parent, column, consistency_level):
    self._oprot.writeMessageBegin('insert', TMessageType.CALL, self._seqid)
    args = insert_args()
    args.key = key
    args.column_parent = column_parent
    args.column = column
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_insert(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = insert_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    return

  def add(self, key, column_parent, column, consistency_level):
    """
    Increment or decrement a counter.

    Parameters:
     - key
     - column_parent
     - column
     - consistency_level
    """
    self.send_add(key, column_parent, column, consistency_level)
    self.recv_add()

  def send_add(self, key, column_parent, column, consistency_level):
    self._oprot.writeMessageBegin('add', TMessageType.CALL, self._seqid)
    args = add_args()
    args.key = key
    args.column_parent = column_parent
    args.column = column
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_add(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = add_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    return

  def remove(self, key, column_path, timestamp, consistency_level):
    """
    Remove data from the row specified by key at the granularity specified by column_path, and the given timestamp. Note
    that all the values in column_path besides column_path.column_family are truly optional: you can remove the entire
    row by just specifying the ColumnFamily, or you can remove a SuperColumn or a single Column by specifying those levels too.

    Parameters:
     - key
     - column_path
     - timestamp
     - consistency_level
    """
    self.send_remove(key, column_path, timestamp, consistency_level)
    self.recv_remove()

  def send_remove(self, key, column_path, timestamp, consistency_level):
    self._oprot.writeMessageBegin('remove', TMessageType.CALL, self._seqid)
    args = remove_args()
    args.key = key
    args.column_path = column_path
    args.timestamp = timestamp
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_remove(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = remove_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    return

  def remove_counter(self, key, path, consistency_level):
    """
    Remove a counter at the specified location.
    Note that counters have limited support for deletes: if you remove a counter, you must wait to issue any following update
    until the delete has reached all the nodes and all of them have been fully compacted.

    Parameters:
     - key
     - path
     - consistency_level
    """
    self.send_remove_counter(key, path, consistency_level)
    self.recv_remove_counter()

  def send_remove_counter(self, key, path, consistency_level):
    self._oprot.writeMessageBegin('remove_counter', TMessageType.CALL, self._seqid)
    args = remove_counter_args()
    args.key = key
    args.path = path
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_remove_counter(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = remove_counter_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    return

  def batch_mutate(self, mutation_map, consistency_level):
    """
      Mutate many columns or super columns for many row keys. See also: Mutation.

      mutation_map maps key to column family to a list of Mutation objects to take place at that scope.
    *

    Parameters:
     - mutation_map
     - consistency_level
    """
    self.send_batch_mutate(mutation_map, consistency_level)
    self.recv_batch_mutate()

  def send_batch_mutate(self, mutation_map, consistency_level):
    self._oprot.writeMessageBegin('batch_mutate', TMessageType.CALL, self._seqid)
    args = batch_mutate_args()
    args.mutation_map = mutation_map
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_batch_mutate(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = batch_mutate_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    return

  def atomic_batch_mutate(self, mutation_map, consistency_level):
    """
      Atomically mutate many columns or super columns for many row keys. See also: Mutation.

      mutation_map maps key to column family to a list of Mutation objects to take place at that scope.
    *

    Parameters:
     - mutation_map
     - consistency_level
    """
    self.send_atomic_batch_mutate(mutation_map, consistency_level)
    self.recv_atomic_batch_mutate()

  def send_atomic_batch_mutate(self, mutation_map, consistency_level):
    self._oprot.writeMessageBegin('atomic_batch_mutate', TMessageType.CALL, self._seqid)
    args = atomic_batch_mutate_args()
    args.mutation_map = mutation_map
    args.consistency_level = consistency_level
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_atomic_batch_mutate(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = atomic_batch_mutate_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    return

  def truncate(self, cfname):
    """
    Truncate will mark and entire column family as deleted.
    From the user's perspective a successful call to truncate will result complete data deletion from cfname.
    Internally, however, disk space will not be immediatily released, as with all deletes in cassandra, this one
    only marks the data as deleted.
    The operation succeeds only if all hosts in the cluster at available and will throw an UnavailableException if
    some hosts are down.

    Parameters:
     - cfname
    """
    self.send_truncate(cfname)
    self.recv_truncate()

  def send_truncate(self, cfname):
    self._oprot.writeMessageBegin('truncate', TMessageType.CALL, self._seqid)
    args = truncate_args()
    args.cfname = cfname
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_truncate(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = truncate_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    return

  def describe_schema_versions(self, ):
    """
    for each schema version present in the cluster, returns a list of nodes at that version.
    hosts that do not respond will be under the key DatabaseDescriptor.INITIAL_VERSION.
    the cluster is all on the same version if the size of the map is 1.
    """
    self.send_describe_schema_versions()
    return self.recv_describe_schema_versions()

  def send_describe_schema_versions(self, ):
    self._oprot.writeMessageBegin('describe_schema_versions', TMessageType.CALL, self._seqid)
    args = describe_schema_versions_args()
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_describe_schema_versions(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = describe_schema_versions_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    raise TApplicationException(TApplicationException.MISSING_RESULT, "describe_schema_versions failed: unknown result");

  def describe_keyspaces(self, ):
    """
    list the defined keyspaces in this cluster
    """
    self.send_describe_keyspaces()
    return self.recv_describe_keyspaces()

  def send_describe_keyspaces(self, ):
    self._oprot.writeMessageBegin('describe_keyspaces', TMessageType.CALL, self._seqid)
    args = describe_keyspaces_args()
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_describe_keyspaces(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = describe_keyspaces_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    raise TApplicationException(TApplicationException.MISSING_RESULT, "describe_keyspaces failed: unknown result");

  def describe_cluster_name(self, ):
    """
    get the cluster name
    """
    self.send_describe_cluster_name()
    return self.recv_describe_cluster_name()

  def send_describe_cluster_name(self, ):
    self._oprot.writeMessageBegin('describe_cluster_name', TMessageType.CALL, self._seqid)
    args = describe_cluster_name_args()
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_describe_cluster_name(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = describe_cluster_name_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    raise TApplicationException(TApplicationException.MISSING_RESULT, "describe_cluster_name failed: unknown result");

  def describe_version(self, ):
    """
    get the thrift api version
    """
    self.send_describe_version()
    return self.recv_describe_version()

  def send_describe_version(self, ):
    self._oprot.writeMessageBegin('describe_version', TMessageType.CALL, self._seqid)
    args = describe_version_args()
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_describe_version(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = describe_version_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    raise TApplicationException(TApplicationException.MISSING_RESULT, "describe_version failed: unknown result");

  def describe_ring(self, keyspace):
    """
    get the token ring: a map of ranges to host addresses,
    represented as a set of TokenRange instead of a map from range
    to list of endpoints, because you can't use Thrift structs as
    map keys:
    https://issues.apache.org/jira/browse/THRIFT-162

    for the same reason, we can't return a set here, even though
    order is neither important nor predictable.

    Parameters:
     - keyspace
    """
    self.send_describe_ring(keyspace)
    return self.recv_describe_ring()

  def send_describe_ring(self, keyspace):
    self._oprot.writeMessageBegin('describe_ring', TMessageType.CALL, self._seqid)
    args = describe_ring_args()
    args.keyspace = keyspace
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_describe_ring(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = describe_ring_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    raise TApplicationException(TApplicationException.MISSING_RESULT, "describe_ring failed: unknown result");

  def describe_token_map(self, ):
    """
    get the mapping between token->node ip
    without taking replication into consideration
    https://issues.apache.org/jira/browse/CASSANDRA-4092
    """
    self.send_describe_token_map()
    return self.recv_describe_token_map()

  def send_describe_token_map(self, ):
    self._oprot.writeMessageBegin('describe_token_map', TMessageType.CALL, self._seqid)
    args = describe_token_map_args()
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_describe_token_map(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = describe_token_map_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    raise TApplicationException(TApplicationException.MISSING_RESULT, "describe_token_map failed: unknown result");

  def describe_partitioner(self, ):
    """
    returns the partitioner used by this cluster
    """
    self.send_describe_partitioner()
    return self.recv_describe_partitioner()

  def send_describe_partitioner(self, ):
    self._oprot.writeMessageBegin('describe_partitioner', TMessageType.CALL, self._seqid)
    args = describe_partitioner_args()
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_describe_partitioner(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = describe_partitioner_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    raise TApplicationException(TApplicationException.MISSING_RESULT, "describe_partitioner failed: unknown result");

  def describe_snitch(self, ):
    """
    returns the snitch used by this cluster
    """
    self.send_describe_snitch()
    return self.recv_describe_snitch()

  def send_describe_snitch(self, ):
    self._oprot.writeMessageBegin('describe_snitch', TMessageType.CALL, self._seqid)
    args = describe_snitch_args()
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_describe_snitch(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = describe_snitch_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    raise TApplicationException(TApplicationException.MISSING_RESULT, "describe_snitch failed: unknown result");

  def describe_keyspace(self, keyspace):
    """
    describe specified keyspace

    Parameters:
     - keyspace
    """
    self.send_describe_keyspace(keyspace)
    return self.recv_describe_keyspace()

  def send_describe_keyspace(self, keyspace):
    self._oprot.writeMessageBegin('describe_keyspace', TMessageType.CALL, self._seqid)
    args = describe_keyspace_args()
    args.keyspace = keyspace
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_describe_keyspace(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = describe_keyspace_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.nfe is not None:
      raise result.nfe
    if result.ire is not None:
      raise result.ire
    raise TApplicationException(TApplicationException.MISSING_RESULT, "describe_keyspace failed: unknown result");

  def describe_splits(self, cfName, start_token, end_token, keys_per_split):
    """
    experimental API for hadoop/parallel query support.
    may change violently and without warning.

    returns list of token strings such that first subrange is (list[0], list[1]],
    next is (list[1], list[2]], etc.

    Parameters:
     - cfName
     - start_token
     - end_token
     - keys_per_split
    """
    self.send_describe_splits(cfName, start_token, end_token, keys_per_split)
    return self.recv_describe_splits()

  def send_describe_splits(self, cfName, start_token, end_token, keys_per_split):
    self._oprot.writeMessageBegin('describe_splits', TMessageType.CALL, self._seqid)
    args = describe_splits_args()
    args.cfName = cfName
    args.start_token = start_token
    args.end_token = end_token
    args.keys_per_split = keys_per_split
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_describe_splits(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = describe_splits_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    raise TApplicationException(TApplicationException.MISSING_RESULT, "describe_splits failed: unknown result");

  def trace_next_query(self, ):
    """
    Enables tracing for the next query in this connection and returns the UUID for that trace session
    The next query will be traced idependently of trace probability and the returned UUID can be used to query the trace keyspace
    """
    self.send_trace_next_query()
    return self.recv_trace_next_query()

  def send_trace_next_query(self, ):
    self._oprot.writeMessageBegin('trace_next_query', TMessageType.CALL, self._seqid)
    args = trace_next_query_args()
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_trace_next_query(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = trace_next_query_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    raise TApplicationException(TApplicationException.MISSING_RESULT, "trace_next_query failed: unknown result");

  def describe_splits_ex(self, cfName, start_token, end_token, keys_per_split):
    """
    Parameters:
     - cfName
     - start_token
     - end_token
     - keys_per_split
    """
    self.send_describe_splits_ex(cfName, start_token, end_token, keys_per_split)
    return self.recv_describe_splits_ex()

  def send_describe_splits_ex(self, cfName, start_token, end_token, keys_per_split):
    self._oprot.writeMessageBegin('describe_splits_ex', TMessageType.CALL, self._seqid)
    args = describe_splits_ex_args()
    args.cfName = cfName
    args.start_token = start_token
    args.end_token = end_token
    args.keys_per_split = keys_per_split
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_describe_splits_ex(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = describe_splits_ex_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    raise TApplicationException(TApplicationException.MISSING_RESULT, "describe_splits_ex failed: unknown result");

  def system_add_column_family(self, cf_def):
    """
    adds a column family. returns the new schema id.

    Parameters:
     - cf_def
    """
    self.send_system_add_column_family(cf_def)
    return self.recv_system_add_column_family()

  def send_system_add_column_family(self, cf_def):
    self._oprot.writeMessageBegin('system_add_column_family', TMessageType.CALL, self._seqid)
    args = system_add_column_family_args()
    args.cf_def = cf_def
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_system_add_column_family(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = system_add_column_family_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.sde is not None:
      raise result.sde
    raise TApplicationException(TApplicationException.MISSING_RESULT, "system_add_column_family failed: unknown result");

  def system_drop_column_family(self, column_family):
    """
    drops a column family. returns the new schema id.

    Parameters:
     - column_family
    """
    self.send_system_drop_column_family(column_family)
    return self.recv_system_drop_column_family()

  def send_system_drop_column_family(self, column_family):
    self._oprot.writeMessageBegin('system_drop_column_family', TMessageType.CALL, self._seqid)
    args = system_drop_column_family_args()
    args.column_family = column_family
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_system_drop_column_family(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = system_drop_column_family_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.sde is not None:
      raise result.sde
    raise TApplicationException(TApplicationException.MISSING_RESULT, "system_drop_column_family failed: unknown result");

  def system_add_keyspace(self, ks_def):
    """
    adds a keyspace and any column families that are part of it. returns the new schema id.

    Parameters:
     - ks_def
    """
    self.send_system_add_keyspace(ks_def)
    return self.recv_system_add_keyspace()

  def send_system_add_keyspace(self, ks_def):
    self._oprot.writeMessageBegin('system_add_keyspace', TMessageType.CALL, self._seqid)
    args = system_add_keyspace_args()
    args.ks_def = ks_def
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_system_add_keyspace(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = system_add_keyspace_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.sde is not None:
      raise result.sde
    raise TApplicationException(TApplicationException.MISSING_RESULT, "system_add_keyspace failed: unknown result");

  def system_drop_keyspace(self, keyspace):
    """
    drops a keyspace and any column families that are part of it. returns the new schema id.

    Parameters:
     - keyspace
    """
    self.send_system_drop_keyspace(keyspace)
    return self.recv_system_drop_keyspace()

  def send_system_drop_keyspace(self, keyspace):
    self._oprot.writeMessageBegin('system_drop_keyspace', TMessageType.CALL, self._seqid)
    args = system_drop_keyspace_args()
    args.keyspace = keyspace
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_system_drop_keyspace(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = system_drop_keyspace_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.sde is not None:
      raise result.sde
    raise TApplicationException(TApplicationException.MISSING_RESULT, "system_drop_keyspace failed: unknown result");

  def system_update_keyspace(self, ks_def):
    """
    updates properties of a keyspace. returns the new schema id.

    Parameters:
     - ks_def
    """
    self.send_system_update_keyspace(ks_def)
    return self.recv_system_update_keyspace()

  def send_system_update_keyspace(self, ks_def):
    self._oprot.writeMessageBegin('system_update_keyspace', TMessageType.CALL, self._seqid)
    args = system_update_keyspace_args()
    args.ks_def = ks_def
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_system_update_keyspace(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = system_update_keyspace_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.sde is not None:
      raise result.sde
    raise TApplicationException(TApplicationException.MISSING_RESULT, "system_update_keyspace failed: unknown result");

  def system_update_column_family(self, cf_def):
    """
    updates properties of a column family. returns the new schema id.

    Parameters:
     - cf_def
    """
    self.send_system_update_column_family(cf_def)
    return self.recv_system_update_column_family()

  def send_system_update_column_family(self, cf_def):
    self._oprot.writeMessageBegin('system_update_column_family', TMessageType.CALL, self._seqid)
    args = system_update_column_family_args()
    args.cf_def = cf_def
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_system_update_column_family(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = system_update_column_family_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.sde is not None:
      raise result.sde
    raise TApplicationException(TApplicationException.MISSING_RESULT, "system_update_column_family failed: unknown result");

  def execute_cql_query(self, query, compression):
    """
    Executes a CQL (Cassandra Query Language) statement and returns a
    CqlResult containing the results.

    Parameters:
     - query
     - compression
    """
    self.send_execute_cql_query(query, compression)
    return self.recv_execute_cql_query()

  def send_execute_cql_query(self, query, compression):
    self._oprot.writeMessageBegin('execute_cql_query', TMessageType.CALL, self._seqid)
    args = execute_cql_query_args()
    args.query = query
    args.compression = compression
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_execute_cql_query(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = execute_cql_query_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    if result.sde is not None:
      raise result.sde
    raise TApplicationException(TApplicationException.MISSING_RESULT, "execute_cql_query failed: unknown result");

  def execute_cql3_query(self, query, compression, consistency):
    """
    Parameters:
     - query
     - compression
     - consistency
    """
    self.send_execute_cql3_query(query, compression, consistency)
    return self.recv_execute_cql3_query()

  def send_execute_cql3_query(self, query, compression, consistency):
    self._oprot.writeMessageBegin('execute_cql3_query', TMessageType.CALL, self._seqid)
    args = execute_cql3_query_args()
    args.query = query
    args.compression = compression
    args.consistency = consistency
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_execute_cql3_query(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = execute_cql3_query_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    if result.sde is not None:
      raise result.sde
    raise TApplicationException(TApplicationException.MISSING_RESULT, "execute_cql3_query failed: unknown result");

  def prepare_cql_query(self, query, compression):
    """
    Prepare a CQL (Cassandra Query Language) statement by compiling and returning
    - the type of CQL statement
    - an id token of the compiled CQL stored on the server side.
    - a count of the discovered bound markers in the statement

    Parameters:
     - query
     - compression
    """
    self.send_prepare_cql_query(query, compression)
    return self.recv_prepare_cql_query()

  def send_prepare_cql_query(self, query, compression):
    self._oprot.writeMessageBegin('prepare_cql_query', TMessageType.CALL, self._seqid)
    args = prepare_cql_query_args()
    args.query = query
    args.compression = compression
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_prepare_cql_query(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = prepare_cql_query_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    raise TApplicationException(TApplicationException.MISSING_RESULT, "prepare_cql_query failed: unknown result");

  def prepare_cql3_query(self, query, compression):
    """
    Parameters:
     - query
     - compression
    """
    self.send_prepare_cql3_query(query, compression)
    return self.recv_prepare_cql3_query()

  def send_prepare_cql3_query(self, query, compression):
    self._oprot.writeMessageBegin('prepare_cql3_query', TMessageType.CALL, self._seqid)
    args = prepare_cql3_query_args()
    args.query = query
    args.compression = compression
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_prepare_cql3_query(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = prepare_cql3_query_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    raise TApplicationException(TApplicationException.MISSING_RESULT, "prepare_cql3_query failed: unknown result");

  def execute_prepared_cql_query(self, itemId, values):
    """
    Executes a prepared CQL (Cassandra Query Language) statement by passing an id token and  a list of variables
    to bind and returns a CqlResult containing the results.

    Parameters:
     - itemId
     - values
    """
    self.send_execute_prepared_cql_query(itemId, values)
    return self.recv_execute_prepared_cql_query()

  def send_execute_prepared_cql_query(self, itemId, values):
    self._oprot.writeMessageBegin('execute_prepared_cql_query', TMessageType.CALL, self._seqid)
    args = execute_prepared_cql_query_args()
    args.itemId = itemId
    args.values = values
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_execute_prepared_cql_query(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = execute_prepared_cql_query_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    if result.sde is not None:
      raise result.sde
    raise TApplicationException(TApplicationException.MISSING_RESULT, "execute_prepared_cql_query failed: unknown result");

  def execute_prepared_cql3_query(self, itemId, values, consistency):
    """
    Parameters:
     - itemId
     - values
     - consistency
    """
    self.send_execute_prepared_cql3_query(itemId, values, consistency)
    return self.recv_execute_prepared_cql3_query()

  def send_execute_prepared_cql3_query(self, itemId, values, consistency):
    self._oprot.writeMessageBegin('execute_prepared_cql3_query', TMessageType.CALL, self._seqid)
    args = execute_prepared_cql3_query_args()
    args.itemId = itemId
    args.values = values
    args.consistency = consistency
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_execute_prepared_cql3_query(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = execute_prepared_cql3_query_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.success is not None:
      return result.success
    if result.ire is not None:
      raise result.ire
    if result.ue is not None:
      raise result.ue
    if result.te is not None:
      raise result.te
    if result.sde is not None:
      raise result.sde
    raise TApplicationException(TApplicationException.MISSING_RESULT, "execute_prepared_cql3_query failed: unknown result");

  def set_cql_version(self, version):
    """
    @deprecated This is now a no-op. Please use the CQL3 specific methods instead.

    Parameters:
     - version
    """
    self.send_set_cql_version(version)
    self.recv_set_cql_version()

  def send_set_cql_version(self, version):
    self._oprot.writeMessageBegin('set_cql_version', TMessageType.CALL, self._seqid)
    args = set_cql_version_args()
    args.version = version
    args.write(self._oprot)
    self._oprot.writeMessageEnd()
    self._oprot.trans.flush()

  def recv_set_cql_version(self, ):
    (fname, mtype, rseqid) = self._iprot.readMessageBegin()
    if mtype == TMessageType.EXCEPTION:
      x = TApplicationException()
      x.read(self._iprot)
      self._iprot.readMessageEnd()
      raise x
    result = set_cql_version_result()
    result.read(self._iprot)
    self._iprot.readMessageEnd()
    if result.ire is not None:
      raise result.ire
    return


class Processor(Iface, TProcessor):
  def __init__(self, handler):
    self._handler = handler
    self._processMap = {}
    self._processMap["login"] = Processor.process_login
    self._processMap["set_keyspace"] = Processor.process_set_keyspace
    self._processMap["get"] = Processor.process_get
    self._processMap["get_slice"] = Processor.process_get_slice
    self._processMap["get_count"] = Processor.process_get_count
    self._processMap["multiget_slice"] = Processor.process_multiget_slice
    self._processMap["multiget_count"] = Processor.process_multiget_count
    self._processMap["get_range_slices"] = Processor.process_get_range_slices
    self._processMap["get_paged_slice"] = Processor.process_get_paged_slice
    self._processMap["get_indexed_slices"] = Processor.process_get_indexed_slices
    self._processMap["insert"] = Processor.process_insert
    self._processMap["add"] = Processor.process_add
    self._processMap["remove"] = Processor.process_remove
    self._processMap["remove_counter"] = Processor.process_remove_counter
    self._processMap["batch_mutate"] = Processor.process_batch_mutate
    self._processMap["atomic_batch_mutate"] = Processor.process_atomic_batch_mutate
    self._processMap["truncate"] = Processor.process_truncate
    self._processMap["describe_schema_versions"] = Processor.process_describe_schema_versions
    self._processMap["describe_keyspaces"] = Processor.process_describe_keyspaces
    self._processMap["describe_cluster_name"] = Processor.process_describe_cluster_name
    self._processMap["describe_version"] = Processor.process_describe_version
    self._processMap["describe_ring"] = Processor.process_describe_ring
    self._processMap["describe_token_map"] = Processor.process_describe_token_map
    self._processMap["describe_partitioner"] = Processor.process_describe_partitioner
    self._processMap["describe_snitch"] = Processor.process_describe_snitch
    self._processMap["describe_keyspace"] = Processor.process_describe_keyspace
    self._processMap["describe_splits"] = Processor.process_describe_splits
    self._processMap["trace_next_query"] = Processor.process_trace_next_query
    self._processMap["describe_splits_ex"] = Processor.process_describe_splits_ex
    self._processMap["system_add_column_family"] = Processor.process_system_add_column_family
    self._processMap["system_drop_column_family"] = Processor.process_system_drop_column_family
    self._processMap["system_add_keyspace"] = Processor.process_system_add_keyspace
    self._processMap["system_drop_keyspace"] = Processor.process_system_drop_keyspace
    self._processMap["system_update_keyspace"] = Processor.process_system_update_keyspace
    self._processMap["system_update_column_family"] = Processor.process_system_update_column_family
    self._processMap["execute_cql_query"] = Processor.process_execute_cql_query
    self._processMap["execute_cql3_query"] = Processor.process_execute_cql3_query
    self._processMap["prepare_cql_query"] = Processor.process_prepare_cql_query
    self._processMap["prepare_cql3_query"] = Processor.process_prepare_cql3_query
    self._processMap["execute_prepared_cql_query"] = Processor.process_execute_prepared_cql_query
    self._processMap["execute_prepared_cql3_query"] = Processor.process_execute_prepared_cql3_query
    self._processMap["set_cql_version"] = Processor.process_set_cql_version

  def process(self, iprot, oprot):
    (name, type, seqid) = iprot.readMessageBegin()
    if name not in self._processMap:
      iprot.skip(TType.STRUCT)
      iprot.readMessageEnd()
      x = TApplicationException(TApplicationException.UNKNOWN_METHOD, 'Unknown function %s' % (name))
      oprot.writeMessageBegin(name, TMessageType.EXCEPTION, seqid)
      x.write(oprot)
      oprot.writeMessageEnd()
      oprot.trans.flush()
      return
    else:
      self._processMap[name](self, seqid, iprot, oprot)
    return True

  def process_login(self, seqid, iprot, oprot):
    args = login_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = login_result()
    try:
      self._handler.login(args.auth_request)
    except AuthenticationException as authnx:
      result.authnx = authnx
    except AuthorizationException as authzx:
      result.authzx = authzx
    oprot.writeMessageBegin("login", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_set_keyspace(self, seqid, iprot, oprot):
    args = set_keyspace_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = set_keyspace_result()
    try:
      self._handler.set_keyspace(args.keyspace)
    except InvalidRequestException as ire:
      result.ire = ire
    oprot.writeMessageBegin("set_keyspace", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_get(self, seqid, iprot, oprot):
    args = get_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = get_result()
    try:
      result.success = self._handler.get(args.key, args.column_path, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except NotFoundException as nfe:
      result.nfe = nfe
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("get", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_get_slice(self, seqid, iprot, oprot):
    args = get_slice_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = get_slice_result()
    try:
      result.success = self._handler.get_slice(args.key, args.column_parent, args.predicate, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("get_slice", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_get_count(self, seqid, iprot, oprot):
    args = get_count_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = get_count_result()
    try:
      result.success = self._handler.get_count(args.key, args.column_parent, args.predicate, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("get_count", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_multiget_slice(self, seqid, iprot, oprot):
    args = multiget_slice_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = multiget_slice_result()
    try:
      result.success = self._handler.multiget_slice(args.keys, args.column_parent, args.predicate, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("multiget_slice", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_multiget_count(self, seqid, iprot, oprot):
    args = multiget_count_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = multiget_count_result()
    try:
      result.success = self._handler.multiget_count(args.keys, args.column_parent, args.predicate, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("multiget_count", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_get_range_slices(self, seqid, iprot, oprot):
    args = get_range_slices_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = get_range_slices_result()
    try:
      result.success = self._handler.get_range_slices(args.column_parent, args.predicate, args.range, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("get_range_slices", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_get_paged_slice(self, seqid, iprot, oprot):
    args = get_paged_slice_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = get_paged_slice_result()
    try:
      result.success = self._handler.get_paged_slice(args.column_family, args.range, args.start_column, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("get_paged_slice", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_get_indexed_slices(self, seqid, iprot, oprot):
    args = get_indexed_slices_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = get_indexed_slices_result()
    try:
      result.success = self._handler.get_indexed_slices(args.column_parent, args.index_clause, args.column_predicate, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("get_indexed_slices", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_insert(self, seqid, iprot, oprot):
    args = insert_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = insert_result()
    try:
      self._handler.insert(args.key, args.column_parent, args.column, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("insert", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_add(self, seqid, iprot, oprot):
    args = add_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = add_result()
    try:
      self._handler.add(args.key, args.column_parent, args.column, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("add", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_remove(self, seqid, iprot, oprot):
    args = remove_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = remove_result()
    try:
      self._handler.remove(args.key, args.column_path, args.timestamp, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("remove", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_remove_counter(self, seqid, iprot, oprot):
    args = remove_counter_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = remove_counter_result()
    try:
      self._handler.remove_counter(args.key, args.path, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("remove_counter", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_batch_mutate(self, seqid, iprot, oprot):
    args = batch_mutate_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = batch_mutate_result()
    try:
      self._handler.batch_mutate(args.mutation_map, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("batch_mutate", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_atomic_batch_mutate(self, seqid, iprot, oprot):
    args = atomic_batch_mutate_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = atomic_batch_mutate_result()
    try:
      self._handler.atomic_batch_mutate(args.mutation_map, args.consistency_level)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("atomic_batch_mutate", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_truncate(self, seqid, iprot, oprot):
    args = truncate_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = truncate_result()
    try:
      self._handler.truncate(args.cfname)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    oprot.writeMessageBegin("truncate", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_describe_schema_versions(self, seqid, iprot, oprot):
    args = describe_schema_versions_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = describe_schema_versions_result()
    try:
      result.success = self._handler.describe_schema_versions()
    except InvalidRequestException as ire:
      result.ire = ire
    oprot.writeMessageBegin("describe_schema_versions", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_describe_keyspaces(self, seqid, iprot, oprot):
    args = describe_keyspaces_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = describe_keyspaces_result()
    try:
      result.success = self._handler.describe_keyspaces()
    except InvalidRequestException as ire:
      result.ire = ire
    oprot.writeMessageBegin("describe_keyspaces", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_describe_cluster_name(self, seqid, iprot, oprot):
    args = describe_cluster_name_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = describe_cluster_name_result()
    result.success = self._handler.describe_cluster_name()
    oprot.writeMessageBegin("describe_cluster_name", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_describe_version(self, seqid, iprot, oprot):
    args = describe_version_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = describe_version_result()
    result.success = self._handler.describe_version()
    oprot.writeMessageBegin("describe_version", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_describe_ring(self, seqid, iprot, oprot):
    args = describe_ring_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = describe_ring_result()
    try:
      result.success = self._handler.describe_ring(args.keyspace)
    except InvalidRequestException as ire:
      result.ire = ire
    oprot.writeMessageBegin("describe_ring", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_describe_token_map(self, seqid, iprot, oprot):
    args = describe_token_map_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = describe_token_map_result()
    try:
      result.success = self._handler.describe_token_map()
    except InvalidRequestException as ire:
      result.ire = ire
    oprot.writeMessageBegin("describe_token_map", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_describe_partitioner(self, seqid, iprot, oprot):
    args = describe_partitioner_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = describe_partitioner_result()
    result.success = self._handler.describe_partitioner()
    oprot.writeMessageBegin("describe_partitioner", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_describe_snitch(self, seqid, iprot, oprot):
    args = describe_snitch_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = describe_snitch_result()
    result.success = self._handler.describe_snitch()
    oprot.writeMessageBegin("describe_snitch", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_describe_keyspace(self, seqid, iprot, oprot):
    args = describe_keyspace_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = describe_keyspace_result()
    try:
      result.success = self._handler.describe_keyspace(args.keyspace)
    except NotFoundException as nfe:
      result.nfe = nfe
    except InvalidRequestException as ire:
      result.ire = ire
    oprot.writeMessageBegin("describe_keyspace", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_describe_splits(self, seqid, iprot, oprot):
    args = describe_splits_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = describe_splits_result()
    try:
      result.success = self._handler.describe_splits(args.cfName, args.start_token, args.end_token, args.keys_per_split)
    except InvalidRequestException as ire:
      result.ire = ire
    oprot.writeMessageBegin("describe_splits", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_trace_next_query(self, seqid, iprot, oprot):
    args = trace_next_query_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = trace_next_query_result()
    result.success = self._handler.trace_next_query()
    oprot.writeMessageBegin("trace_next_query", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_describe_splits_ex(self, seqid, iprot, oprot):
    args = describe_splits_ex_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = describe_splits_ex_result()
    try:
      result.success = self._handler.describe_splits_ex(args.cfName, args.start_token, args.end_token, args.keys_per_split)
    except InvalidRequestException as ire:
      result.ire = ire
    oprot.writeMessageBegin("describe_splits_ex", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_system_add_column_family(self, seqid, iprot, oprot):
    args = system_add_column_family_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = system_add_column_family_result()
    try:
      result.success = self._handler.system_add_column_family(args.cf_def)
    except InvalidRequestException as ire:
      result.ire = ire
    except SchemaDisagreementException as sde:
      result.sde = sde
    oprot.writeMessageBegin("system_add_column_family", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_system_drop_column_family(self, seqid, iprot, oprot):
    args = system_drop_column_family_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = system_drop_column_family_result()
    try:
      result.success = self._handler.system_drop_column_family(args.column_family)
    except InvalidRequestException as ire:
      result.ire = ire
    except SchemaDisagreementException as sde:
      result.sde = sde
    oprot.writeMessageBegin("system_drop_column_family", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_system_add_keyspace(self, seqid, iprot, oprot):
    args = system_add_keyspace_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = system_add_keyspace_result()
    try:
      result.success = self._handler.system_add_keyspace(args.ks_def)
    except InvalidRequestException as ire:
      result.ire = ire
    except SchemaDisagreementException as sde:
      result.sde = sde
    oprot.writeMessageBegin("system_add_keyspace", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_system_drop_keyspace(self, seqid, iprot, oprot):
    args = system_drop_keyspace_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = system_drop_keyspace_result()
    try:
      result.success = self._handler.system_drop_keyspace(args.keyspace)
    except InvalidRequestException as ire:
      result.ire = ire
    except SchemaDisagreementException as sde:
      result.sde = sde
    oprot.writeMessageBegin("system_drop_keyspace", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_system_update_keyspace(self, seqid, iprot, oprot):
    args = system_update_keyspace_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = system_update_keyspace_result()
    try:
      result.success = self._handler.system_update_keyspace(args.ks_def)
    except InvalidRequestException as ire:
      result.ire = ire
    except SchemaDisagreementException as sde:
      result.sde = sde
    oprot.writeMessageBegin("system_update_keyspace", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_system_update_column_family(self, seqid, iprot, oprot):
    args = system_update_column_family_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = system_update_column_family_result()
    try:
      result.success = self._handler.system_update_column_family(args.cf_def)
    except InvalidRequestException as ire:
      result.ire = ire
    except SchemaDisagreementException as sde:
      result.sde = sde
    oprot.writeMessageBegin("system_update_column_family", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_execute_cql_query(self, seqid, iprot, oprot):
    args = execute_cql_query_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = execute_cql_query_result()
    try:
      result.success = self._handler.execute_cql_query(args.query, args.compression)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    except SchemaDisagreementException as sde:
      result.sde = sde
    oprot.writeMessageBegin("execute_cql_query", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_execute_cql3_query(self, seqid, iprot, oprot):
    args = execute_cql3_query_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = execute_cql3_query_result()
    try:
      result.success = self._handler.execute_cql3_query(args.query, args.compression, args.consistency)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    except SchemaDisagreementException as sde:
      result.sde = sde
    oprot.writeMessageBegin("execute_cql3_query", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_prepare_cql_query(self, seqid, iprot, oprot):
    args = prepare_cql_query_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = prepare_cql_query_result()
    try:
      result.success = self._handler.prepare_cql_query(args.query, args.compression)
    except InvalidRequestException as ire:
      result.ire = ire
    oprot.writeMessageBegin("prepare_cql_query", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_prepare_cql3_query(self, seqid, iprot, oprot):
    args = prepare_cql3_query_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = prepare_cql3_query_result()
    try:
      result.success = self._handler.prepare_cql3_query(args.query, args.compression)
    except InvalidRequestException as ire:
      result.ire = ire
    oprot.writeMessageBegin("prepare_cql3_query", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_execute_prepared_cql_query(self, seqid, iprot, oprot):
    args = execute_prepared_cql_query_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = execute_prepared_cql_query_result()
    try:
      result.success = self._handler.execute_prepared_cql_query(args.itemId, args.values)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    except SchemaDisagreementException as sde:
      result.sde = sde
    oprot.writeMessageBegin("execute_prepared_cql_query", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_execute_prepared_cql3_query(self, seqid, iprot, oprot):
    args = execute_prepared_cql3_query_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = execute_prepared_cql3_query_result()
    try:
      result.success = self._handler.execute_prepared_cql3_query(args.itemId, args.values, args.consistency)
    except InvalidRequestException as ire:
      result.ire = ire
    except UnavailableException as ue:
      result.ue = ue
    except TimedOutException as te:
      result.te = te
    except SchemaDisagreementException as sde:
      result.sde = sde
    oprot.writeMessageBegin("execute_prepared_cql3_query", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()

  def process_set_cql_version(self, seqid, iprot, oprot):
    args = set_cql_version_args()
    args.read(iprot)
    iprot.readMessageEnd()
    result = set_cql_version_result()
    try:
      self._handler.set_cql_version(args.version)
    except InvalidRequestException as ire:
      result.ire = ire
    oprot.writeMessageBegin("set_cql_version", TMessageType.REPLY, seqid)
    result.write(oprot)
    oprot.writeMessageEnd()
    oprot.trans.flush()


# HELPER FUNCTIONS AND STRUCTURES

class login_args(object):
  """
  Attributes:
   - auth_request
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'auth_request', (AuthenticationRequest, AuthenticationRequest.thrift_spec), None, ), # 1
  )

  def __init__(self, auth_request=None,):
    self.auth_request = auth_request

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.auth_request = AuthenticationRequest()
          self.auth_request.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('login_args')
    if self.auth_request is not None:
      oprot.writeFieldBegin('auth_request', TType.STRUCT, 1)
      self.auth_request.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.auth_request is None:
      raise TProtocol.TProtocolException(message='Required field auth_request is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class login_result(object):
  """
  Attributes:
   - authnx
   - authzx
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'authnx', (AuthenticationException, AuthenticationException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'authzx', (AuthorizationException, AuthorizationException.thrift_spec), None, ), # 2
  )

  def __init__(self, authnx=None, authzx=None,):
    self.authnx = authnx
    self.authzx = authzx

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.authnx = AuthenticationException()
          self.authnx.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.authzx = AuthorizationException()
          self.authzx.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('login_result')
    if self.authnx is not None:
      oprot.writeFieldBegin('authnx', TType.STRUCT, 1)
      self.authnx.write(oprot)
      oprot.writeFieldEnd()
    if self.authzx is not None:
      oprot.writeFieldBegin('authzx', TType.STRUCT, 2)
      self.authzx.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class set_keyspace_args(object):
  """
  Attributes:
   - keyspace
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'keyspace', None, None, ), # 1
  )

  def __init__(self, keyspace=None,):
    self.keyspace = keyspace

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.keyspace = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('set_keyspace_args')
    if self.keyspace is not None:
      oprot.writeFieldBegin('keyspace', TType.STRING, 1)
      oprot.writeString(self.keyspace)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.keyspace is None:
      raise TProtocol.TProtocolException(message='Required field keyspace is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class set_keyspace_result(object):
  """
  Attributes:
   - ire
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
  )

  def __init__(self, ire=None,):
    self.ire = ire

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('set_keyspace_result')
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_args(object):
  """
  Attributes:
   - key
   - column_path
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'key', None, None, ), # 1
    (2, TType.STRUCT, 'column_path', (ColumnPath, ColumnPath.thrift_spec), None, ), # 2
    (3, TType.I32, 'consistency_level', None,     1, ), # 3
  )

  def __init__(self, key=None, column_path=None, consistency_level=thrift_spec[3][4],):
    self.key = key
    self.column_path = column_path
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.column_path = ColumnPath()
          self.column_path.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_args')
    if self.key is not None:
      oprot.writeFieldBegin('key', TType.STRING, 1)
      oprot.writeString(self.key)
      oprot.writeFieldEnd()
    if self.column_path is not None:
      oprot.writeFieldBegin('column_path', TType.STRUCT, 2)
      self.column_path.write(oprot)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 3)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.key is None:
      raise TProtocol.TProtocolException(message='Required field key is unset!')
    if self.column_path is None:
      raise TProtocol.TProtocolException(message='Required field column_path is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_result(object):
  """
  Attributes:
   - success
   - ire
   - nfe
   - ue
   - te
  """

  thrift_spec = (
    (0, TType.STRUCT, 'success', (ColumnOrSuperColumn, ColumnOrSuperColumn.thrift_spec), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'nfe', (NotFoundException, NotFoundException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 3
    (4, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 4
  )

  def __init__(self, success=None, ire=None, nfe=None, ue=None, te=None,):
    self.success = success
    self.ire = ire
    self.nfe = nfe
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRUCT:
          self.success = ColumnOrSuperColumn()
          self.success.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.nfe = NotFoundException()
          self.nfe.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRUCT, 0)
      self.success.write(oprot)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.nfe is not None:
      oprot.writeFieldBegin('nfe', TType.STRUCT, 2)
      self.nfe.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 3)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 4)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_slice_args(object):
  """
  Attributes:
   - key
   - column_parent
   - predicate
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'key', None, None, ), # 1
    (2, TType.STRUCT, 'column_parent', (ColumnParent, ColumnParent.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'predicate', (SlicePredicate, SlicePredicate.thrift_spec), None, ), # 3
    (4, TType.I32, 'consistency_level', None,     1, ), # 4
  )

  def __init__(self, key=None, column_parent=None, predicate=None, consistency_level=thrift_spec[4][4],):
    self.key = key
    self.column_parent = column_parent
    self.predicate = predicate
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.column_parent = ColumnParent()
          self.column_parent.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.predicate = SlicePredicate()
          self.predicate.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_slice_args')
    if self.key is not None:
      oprot.writeFieldBegin('key', TType.STRING, 1)
      oprot.writeString(self.key)
      oprot.writeFieldEnd()
    if self.column_parent is not None:
      oprot.writeFieldBegin('column_parent', TType.STRUCT, 2)
      self.column_parent.write(oprot)
      oprot.writeFieldEnd()
    if self.predicate is not None:
      oprot.writeFieldBegin('predicate', TType.STRUCT, 3)
      self.predicate.write(oprot)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 4)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.key is None:
      raise TProtocol.TProtocolException(message='Required field key is unset!')
    if self.column_parent is None:
      raise TProtocol.TProtocolException(message='Required field column_parent is unset!')
    if self.predicate is None:
      raise TProtocol.TProtocolException(message='Required field predicate is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_slice_result(object):
  """
  Attributes:
   - success
   - ire
   - ue
   - te
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(ColumnOrSuperColumn, ColumnOrSuperColumn.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, success=None, ire=None, ue=None, te=None,):
    self.success = success
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype171, _size168) = iprot.readListBegin()
          for _i172 in xrange(_size168):
            _elem173 = ColumnOrSuperColumn()
            _elem173.read(iprot)
            self.success.append(_elem173)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_slice_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter174 in self.success:
        iter174.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_count_args(object):
  """
  Attributes:
   - key
   - column_parent
   - predicate
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'key', None, None, ), # 1
    (2, TType.STRUCT, 'column_parent', (ColumnParent, ColumnParent.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'predicate', (SlicePredicate, SlicePredicate.thrift_spec), None, ), # 3
    (4, TType.I32, 'consistency_level', None,     1, ), # 4
  )

  def __init__(self, key=None, column_parent=None, predicate=None, consistency_level=thrift_spec[4][4],):
    self.key = key
    self.column_parent = column_parent
    self.predicate = predicate
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.column_parent = ColumnParent()
          self.column_parent.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.predicate = SlicePredicate()
          self.predicate.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_count_args')
    if self.key is not None:
      oprot.writeFieldBegin('key', TType.STRING, 1)
      oprot.writeString(self.key)
      oprot.writeFieldEnd()
    if self.column_parent is not None:
      oprot.writeFieldBegin('column_parent', TType.STRUCT, 2)
      self.column_parent.write(oprot)
      oprot.writeFieldEnd()
    if self.predicate is not None:
      oprot.writeFieldBegin('predicate', TType.STRUCT, 3)
      self.predicate.write(oprot)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 4)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.key is None:
      raise TProtocol.TProtocolException(message='Required field key is unset!')
    if self.column_parent is None:
      raise TProtocol.TProtocolException(message='Required field column_parent is unset!')
    if self.predicate is None:
      raise TProtocol.TProtocolException(message='Required field predicate is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_count_result(object):
  """
  Attributes:
   - success
   - ire
   - ue
   - te
  """

  thrift_spec = (
    (0, TType.I32, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, success=None, ire=None, ue=None, te=None,):
    self.success = success
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.I32:
          self.success = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_count_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.I32, 0)
      oprot.writeI32(self.success)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class multiget_slice_args(object):
  """
  Attributes:
   - keys
   - column_parent
   - predicate
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.LIST, 'keys', (TType.STRING,None), None, ), # 1
    (2, TType.STRUCT, 'column_parent', (ColumnParent, ColumnParent.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'predicate', (SlicePredicate, SlicePredicate.thrift_spec), None, ), # 3
    (4, TType.I32, 'consistency_level', None,     1, ), # 4
  )

  def __init__(self, keys=None, column_parent=None, predicate=None, consistency_level=thrift_spec[4][4],):
    self.keys = keys
    self.column_parent = column_parent
    self.predicate = predicate
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.LIST:
          self.keys = []
          (_etype178, _size175) = iprot.readListBegin()
          for _i179 in xrange(_size175):
            _elem180 = iprot.readString();
            self.keys.append(_elem180)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.column_parent = ColumnParent()
          self.column_parent.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.predicate = SlicePredicate()
          self.predicate.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('multiget_slice_args')
    if self.keys is not None:
      oprot.writeFieldBegin('keys', TType.LIST, 1)
      oprot.writeListBegin(TType.STRING, len(self.keys))
      for iter181 in self.keys:
        oprot.writeString(iter181)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.column_parent is not None:
      oprot.writeFieldBegin('column_parent', TType.STRUCT, 2)
      self.column_parent.write(oprot)
      oprot.writeFieldEnd()
    if self.predicate is not None:
      oprot.writeFieldBegin('predicate', TType.STRUCT, 3)
      self.predicate.write(oprot)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 4)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.keys is None:
      raise TProtocol.TProtocolException(message='Required field keys is unset!')
    if self.column_parent is None:
      raise TProtocol.TProtocolException(message='Required field column_parent is unset!')
    if self.predicate is None:
      raise TProtocol.TProtocolException(message='Required field predicate is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class multiget_slice_result(object):
  """
  Attributes:
   - success
   - ire
   - ue
   - te
  """

  thrift_spec = (
    (0, TType.MAP, 'success', (TType.STRING,None,TType.LIST,(TType.STRUCT,(ColumnOrSuperColumn, ColumnOrSuperColumn.thrift_spec))), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, success=None, ire=None, ue=None, te=None,):
    self.success = success
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.MAP:
          self.success = {}
          (_ktype183, _vtype184, _size182 ) = iprot.readMapBegin() 
          for _i186 in xrange(_size182):
            _key187 = iprot.readString();
            _val188 = []
            (_etype192, _size189) = iprot.readListBegin()
            for _i193 in xrange(_size189):
              _elem194 = ColumnOrSuperColumn()
              _elem194.read(iprot)
              _val188.append(_elem194)
            iprot.readListEnd()
            self.success[_key187] = _val188
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('multiget_slice_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.MAP, 0)
      oprot.writeMapBegin(TType.STRING, TType.LIST, len(self.success))
      for kiter195,viter196 in self.success.items():
        oprot.writeString(kiter195)
        oprot.writeListBegin(TType.STRUCT, len(viter196))
        for iter197 in viter196:
          iter197.write(oprot)
        oprot.writeListEnd()
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class multiget_count_args(object):
  """
  Attributes:
   - keys
   - column_parent
   - predicate
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.LIST, 'keys', (TType.STRING,None), None, ), # 1
    (2, TType.STRUCT, 'column_parent', (ColumnParent, ColumnParent.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'predicate', (SlicePredicate, SlicePredicate.thrift_spec), None, ), # 3
    (4, TType.I32, 'consistency_level', None,     1, ), # 4
  )

  def __init__(self, keys=None, column_parent=None, predicate=None, consistency_level=thrift_spec[4][4],):
    self.keys = keys
    self.column_parent = column_parent
    self.predicate = predicate
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.LIST:
          self.keys = []
          (_etype201, _size198) = iprot.readListBegin()
          for _i202 in xrange(_size198):
            _elem203 = iprot.readString();
            self.keys.append(_elem203)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.column_parent = ColumnParent()
          self.column_parent.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.predicate = SlicePredicate()
          self.predicate.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('multiget_count_args')
    if self.keys is not None:
      oprot.writeFieldBegin('keys', TType.LIST, 1)
      oprot.writeListBegin(TType.STRING, len(self.keys))
      for iter204 in self.keys:
        oprot.writeString(iter204)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.column_parent is not None:
      oprot.writeFieldBegin('column_parent', TType.STRUCT, 2)
      self.column_parent.write(oprot)
      oprot.writeFieldEnd()
    if self.predicate is not None:
      oprot.writeFieldBegin('predicate', TType.STRUCT, 3)
      self.predicate.write(oprot)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 4)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.keys is None:
      raise TProtocol.TProtocolException(message='Required field keys is unset!')
    if self.column_parent is None:
      raise TProtocol.TProtocolException(message='Required field column_parent is unset!')
    if self.predicate is None:
      raise TProtocol.TProtocolException(message='Required field predicate is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class multiget_count_result(object):
  """
  Attributes:
   - success
   - ire
   - ue
   - te
  """

  thrift_spec = (
    (0, TType.MAP, 'success', (TType.STRING,None,TType.I32,None), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, success=None, ire=None, ue=None, te=None,):
    self.success = success
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.MAP:
          self.success = {}
          (_ktype206, _vtype207, _size205 ) = iprot.readMapBegin() 
          for _i209 in xrange(_size205):
            _key210 = iprot.readString();
            _val211 = iprot.readI32();
            self.success[_key210] = _val211
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('multiget_count_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.MAP, 0)
      oprot.writeMapBegin(TType.STRING, TType.I32, len(self.success))
      for kiter212,viter213 in self.success.items():
        oprot.writeString(kiter212)
        oprot.writeI32(viter213)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_range_slices_args(object):
  """
  Attributes:
   - column_parent
   - predicate
   - range
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'column_parent', (ColumnParent, ColumnParent.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'predicate', (SlicePredicate, SlicePredicate.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'range', (KeyRange, KeyRange.thrift_spec), None, ), # 3
    (4, TType.I32, 'consistency_level', None,     1, ), # 4
  )

  def __init__(self, column_parent=None, predicate=None, range=None, consistency_level=thrift_spec[4][4],):
    self.column_parent = column_parent
    self.predicate = predicate
    self.range = range
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.column_parent = ColumnParent()
          self.column_parent.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.predicate = SlicePredicate()
          self.predicate.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.range = KeyRange()
          self.range.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_range_slices_args')
    if self.column_parent is not None:
      oprot.writeFieldBegin('column_parent', TType.STRUCT, 1)
      self.column_parent.write(oprot)
      oprot.writeFieldEnd()
    if self.predicate is not None:
      oprot.writeFieldBegin('predicate', TType.STRUCT, 2)
      self.predicate.write(oprot)
      oprot.writeFieldEnd()
    if self.range is not None:
      oprot.writeFieldBegin('range', TType.STRUCT, 3)
      self.range.write(oprot)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 4)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.column_parent is None:
      raise TProtocol.TProtocolException(message='Required field column_parent is unset!')
    if self.predicate is None:
      raise TProtocol.TProtocolException(message='Required field predicate is unset!')
    if self.range is None:
      raise TProtocol.TProtocolException(message='Required field range is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_range_slices_result(object):
  """
  Attributes:
   - success
   - ire
   - ue
   - te
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(KeySlice, KeySlice.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, success=None, ire=None, ue=None, te=None,):
    self.success = success
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype217, _size214) = iprot.readListBegin()
          for _i218 in xrange(_size214):
            _elem219 = KeySlice()
            _elem219.read(iprot)
            self.success.append(_elem219)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_range_slices_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter220 in self.success:
        iter220.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_paged_slice_args(object):
  """
  Attributes:
   - column_family
   - range
   - start_column
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'column_family', None, None, ), # 1
    (2, TType.STRUCT, 'range', (KeyRange, KeyRange.thrift_spec), None, ), # 2
    (3, TType.STRING, 'start_column', None, None, ), # 3
    (4, TType.I32, 'consistency_level', None,     1, ), # 4
  )

  def __init__(self, column_family=None, range=None, start_column=None, consistency_level=thrift_spec[4][4],):
    self.column_family = column_family
    self.range = range
    self.start_column = start_column
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.column_family = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.range = KeyRange()
          self.range.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.start_column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_paged_slice_args')
    if self.column_family is not None:
      oprot.writeFieldBegin('column_family', TType.STRING, 1)
      oprot.writeString(self.column_family)
      oprot.writeFieldEnd()
    if self.range is not None:
      oprot.writeFieldBegin('range', TType.STRUCT, 2)
      self.range.write(oprot)
      oprot.writeFieldEnd()
    if self.start_column is not None:
      oprot.writeFieldBegin('start_column', TType.STRING, 3)
      oprot.writeString(self.start_column)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 4)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.column_family is None:
      raise TProtocol.TProtocolException(message='Required field column_family is unset!')
    if self.range is None:
      raise TProtocol.TProtocolException(message='Required field range is unset!')
    if self.start_column is None:
      raise TProtocol.TProtocolException(message='Required field start_column is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_paged_slice_result(object):
  """
  Attributes:
   - success
   - ire
   - ue
   - te
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(KeySlice, KeySlice.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, success=None, ire=None, ue=None, te=None,):
    self.success = success
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype224, _size221) = iprot.readListBegin()
          for _i225 in xrange(_size221):
            _elem226 = KeySlice()
            _elem226.read(iprot)
            self.success.append(_elem226)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_paged_slice_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter227 in self.success:
        iter227.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_indexed_slices_args(object):
  """
  Attributes:
   - column_parent
   - index_clause
   - column_predicate
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'column_parent', (ColumnParent, ColumnParent.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'index_clause', (IndexClause, IndexClause.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'column_predicate', (SlicePredicate, SlicePredicate.thrift_spec), None, ), # 3
    (4, TType.I32, 'consistency_level', None,     1, ), # 4
  )

  def __init__(self, column_parent=None, index_clause=None, column_predicate=None, consistency_level=thrift_spec[4][4],):
    self.column_parent = column_parent
    self.index_clause = index_clause
    self.column_predicate = column_predicate
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.column_parent = ColumnParent()
          self.column_parent.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.index_clause = IndexClause()
          self.index_clause.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.column_predicate = SlicePredicate()
          self.column_predicate.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_indexed_slices_args')
    if self.column_parent is not None:
      oprot.writeFieldBegin('column_parent', TType.STRUCT, 1)
      self.column_parent.write(oprot)
      oprot.writeFieldEnd()
    if self.index_clause is not None:
      oprot.writeFieldBegin('index_clause', TType.STRUCT, 2)
      self.index_clause.write(oprot)
      oprot.writeFieldEnd()
    if self.column_predicate is not None:
      oprot.writeFieldBegin('column_predicate', TType.STRUCT, 3)
      self.column_predicate.write(oprot)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 4)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.column_parent is None:
      raise TProtocol.TProtocolException(message='Required field column_parent is unset!')
    if self.index_clause is None:
      raise TProtocol.TProtocolException(message='Required field index_clause is unset!')
    if self.column_predicate is None:
      raise TProtocol.TProtocolException(message='Required field column_predicate is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class get_indexed_slices_result(object):
  """
  Attributes:
   - success
   - ire
   - ue
   - te
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(KeySlice, KeySlice.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, success=None, ire=None, ue=None, te=None,):
    self.success = success
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype231, _size228) = iprot.readListBegin()
          for _i232 in xrange(_size228):
            _elem233 = KeySlice()
            _elem233.read(iprot)
            self.success.append(_elem233)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('get_indexed_slices_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter234 in self.success:
        iter234.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class insert_args(object):
  """
  Attributes:
   - key
   - column_parent
   - column
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'key', None, None, ), # 1
    (2, TType.STRUCT, 'column_parent', (ColumnParent, ColumnParent.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'column', (Column, Column.thrift_spec), None, ), # 3
    (4, TType.I32, 'consistency_level', None,     1, ), # 4
  )

  def __init__(self, key=None, column_parent=None, column=None, consistency_level=thrift_spec[4][4],):
    self.key = key
    self.column_parent = column_parent
    self.column = column
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.column_parent = ColumnParent()
          self.column_parent.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.column = Column()
          self.column.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('insert_args')
    if self.key is not None:
      oprot.writeFieldBegin('key', TType.STRING, 1)
      oprot.writeString(self.key)
      oprot.writeFieldEnd()
    if self.column_parent is not None:
      oprot.writeFieldBegin('column_parent', TType.STRUCT, 2)
      self.column_parent.write(oprot)
      oprot.writeFieldEnd()
    if self.column is not None:
      oprot.writeFieldBegin('column', TType.STRUCT, 3)
      self.column.write(oprot)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 4)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.key is None:
      raise TProtocol.TProtocolException(message='Required field key is unset!')
    if self.column_parent is None:
      raise TProtocol.TProtocolException(message='Required field column_parent is unset!')
    if self.column is None:
      raise TProtocol.TProtocolException(message='Required field column is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class insert_result(object):
  """
  Attributes:
   - ire
   - ue
   - te
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, ire=None, ue=None, te=None,):
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('insert_result')
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class add_args(object):
  """
  Attributes:
   - key
   - column_parent
   - column
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'key', None, None, ), # 1
    (2, TType.STRUCT, 'column_parent', (ColumnParent, ColumnParent.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'column', (CounterColumn, CounterColumn.thrift_spec), None, ), # 3
    (4, TType.I32, 'consistency_level', None,     1, ), # 4
  )

  def __init__(self, key=None, column_parent=None, column=None, consistency_level=thrift_spec[4][4],):
    self.key = key
    self.column_parent = column_parent
    self.column = column
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.column_parent = ColumnParent()
          self.column_parent.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.column = CounterColumn()
          self.column.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('add_args')
    if self.key is not None:
      oprot.writeFieldBegin('key', TType.STRING, 1)
      oprot.writeString(self.key)
      oprot.writeFieldEnd()
    if self.column_parent is not None:
      oprot.writeFieldBegin('column_parent', TType.STRUCT, 2)
      self.column_parent.write(oprot)
      oprot.writeFieldEnd()
    if self.column is not None:
      oprot.writeFieldBegin('column', TType.STRUCT, 3)
      self.column.write(oprot)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 4)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.key is None:
      raise TProtocol.TProtocolException(message='Required field key is unset!')
    if self.column_parent is None:
      raise TProtocol.TProtocolException(message='Required field column_parent is unset!')
    if self.column is None:
      raise TProtocol.TProtocolException(message='Required field column is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class add_result(object):
  """
  Attributes:
   - ire
   - ue
   - te
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, ire=None, ue=None, te=None,):
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('add_result')
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class remove_args(object):
  """
  Attributes:
   - key
   - column_path
   - timestamp
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'key', None, None, ), # 1
    (2, TType.STRUCT, 'column_path', (ColumnPath, ColumnPath.thrift_spec), None, ), # 2
    (3, TType.I64, 'timestamp', None, None, ), # 3
    (4, TType.I32, 'consistency_level', None,     1, ), # 4
  )

  def __init__(self, key=None, column_path=None, timestamp=None, consistency_level=thrift_spec[4][4],):
    self.key = key
    self.column_path = column_path
    self.timestamp = timestamp
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.column_path = ColumnPath()
          self.column_path.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('remove_args')
    if self.key is not None:
      oprot.writeFieldBegin('key', TType.STRING, 1)
      oprot.writeString(self.key)
      oprot.writeFieldEnd()
    if self.column_path is not None:
      oprot.writeFieldBegin('column_path', TType.STRUCT, 2)
      self.column_path.write(oprot)
      oprot.writeFieldEnd()
    if self.timestamp is not None:
      oprot.writeFieldBegin('timestamp', TType.I64, 3)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 4)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.key is None:
      raise TProtocol.TProtocolException(message='Required field key is unset!')
    if self.column_path is None:
      raise TProtocol.TProtocolException(message='Required field column_path is unset!')
    if self.timestamp is None:
      raise TProtocol.TProtocolException(message='Required field timestamp is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class remove_result(object):
  """
  Attributes:
   - ire
   - ue
   - te
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, ire=None, ue=None, te=None,):
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('remove_result')
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class remove_counter_args(object):
  """
  Attributes:
   - key
   - path
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'key', None, None, ), # 1
    (2, TType.STRUCT, 'path', (ColumnPath, ColumnPath.thrift_spec), None, ), # 2
    (3, TType.I32, 'consistency_level', None,     1, ), # 3
  )

  def __init__(self, key=None, path=None, consistency_level=thrift_spec[3][4],):
    self.key = key
    self.path = path
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.path = ColumnPath()
          self.path.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('remove_counter_args')
    if self.key is not None:
      oprot.writeFieldBegin('key', TType.STRING, 1)
      oprot.writeString(self.key)
      oprot.writeFieldEnd()
    if self.path is not None:
      oprot.writeFieldBegin('path', TType.STRUCT, 2)
      self.path.write(oprot)
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 3)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.key is None:
      raise TProtocol.TProtocolException(message='Required field key is unset!')
    if self.path is None:
      raise TProtocol.TProtocolException(message='Required field path is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class remove_counter_result(object):
  """
  Attributes:
   - ire
   - ue
   - te
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, ire=None, ue=None, te=None,):
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('remove_counter_result')
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class batch_mutate_args(object):
  """
  Attributes:
   - mutation_map
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.MAP, 'mutation_map', (TType.STRING,None,TType.MAP,(TType.STRING,None,TType.LIST,(TType.STRUCT,(Mutation, Mutation.thrift_spec)))), None, ), # 1
    (2, TType.I32, 'consistency_level', None,     1, ), # 2
  )

  def __init__(self, mutation_map=None, consistency_level=thrift_spec[2][4],):
    self.mutation_map = mutation_map
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.MAP:
          self.mutation_map = {}
          (_ktype236, _vtype237, _size235 ) = iprot.readMapBegin() 
          for _i239 in xrange(_size235):
            _key240 = iprot.readString();
            _val241 = {}
            (_ktype243, _vtype244, _size242 ) = iprot.readMapBegin() 
            for _i246 in xrange(_size242):
              _key247 = iprot.readString();
              _val248 = []
              (_etype252, _size249) = iprot.readListBegin()
              for _i253 in xrange(_size249):
                _elem254 = Mutation()
                _elem254.read(iprot)
                _val248.append(_elem254)
              iprot.readListEnd()
              _val241[_key247] = _val248
            iprot.readMapEnd()
            self.mutation_map[_key240] = _val241
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('batch_mutate_args')
    if self.mutation_map is not None:
      oprot.writeFieldBegin('mutation_map', TType.MAP, 1)
      oprot.writeMapBegin(TType.STRING, TType.MAP, len(self.mutation_map))
      for kiter255,viter256 in self.mutation_map.items():
        oprot.writeString(kiter255)
        oprot.writeMapBegin(TType.STRING, TType.LIST, len(viter256))
        for kiter257,viter258 in viter256.items():
          oprot.writeString(kiter257)
          oprot.writeListBegin(TType.STRUCT, len(viter258))
          for iter259 in viter258:
            iter259.write(oprot)
          oprot.writeListEnd()
        oprot.writeMapEnd()
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 2)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.mutation_map is None:
      raise TProtocol.TProtocolException(message='Required field mutation_map is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class batch_mutate_result(object):
  """
  Attributes:
   - ire
   - ue
   - te
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, ire=None, ue=None, te=None,):
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('batch_mutate_result')
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class atomic_batch_mutate_args(object):
  """
  Attributes:
   - mutation_map
   - consistency_level
  """

  thrift_spec = (
    None, # 0
    (1, TType.MAP, 'mutation_map', (TType.STRING,None,TType.MAP,(TType.STRING,None,TType.LIST,(TType.STRUCT,(Mutation, Mutation.thrift_spec)))), None, ), # 1
    (2, TType.I32, 'consistency_level', None,     1, ), # 2
  )

  def __init__(self, mutation_map=None, consistency_level=thrift_spec[2][4],):
    self.mutation_map = mutation_map
    self.consistency_level = consistency_level

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.MAP:
          self.mutation_map = {}
          (_ktype261, _vtype262, _size260 ) = iprot.readMapBegin() 
          for _i264 in xrange(_size260):
            _key265 = iprot.readString();
            _val266 = {}
            (_ktype268, _vtype269, _size267 ) = iprot.readMapBegin() 
            for _i271 in xrange(_size267):
              _key272 = iprot.readString();
              _val273 = []
              (_etype277, _size274) = iprot.readListBegin()
              for _i278 in xrange(_size274):
                _elem279 = Mutation()
                _elem279.read(iprot)
                _val273.append(_elem279)
              iprot.readListEnd()
              _val266[_key272] = _val273
            iprot.readMapEnd()
            self.mutation_map[_key265] = _val266
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.consistency_level = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('atomic_batch_mutate_args')
    if self.mutation_map is not None:
      oprot.writeFieldBegin('mutation_map', TType.MAP, 1)
      oprot.writeMapBegin(TType.STRING, TType.MAP, len(self.mutation_map))
      for kiter280,viter281 in self.mutation_map.items():
        oprot.writeString(kiter280)
        oprot.writeMapBegin(TType.STRING, TType.LIST, len(viter281))
        for kiter282,viter283 in viter281.items():
          oprot.writeString(kiter282)
          oprot.writeListBegin(TType.STRUCT, len(viter283))
          for iter284 in viter283:
            iter284.write(oprot)
          oprot.writeListEnd()
        oprot.writeMapEnd()
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.consistency_level is not None:
      oprot.writeFieldBegin('consistency_level', TType.I32, 2)
      oprot.writeI32(self.consistency_level)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.mutation_map is None:
      raise TProtocol.TProtocolException(message='Required field mutation_map is unset!')
    if self.consistency_level is None:
      raise TProtocol.TProtocolException(message='Required field consistency_level is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class atomic_batch_mutate_result(object):
  """
  Attributes:
   - ire
   - ue
   - te
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, ire=None, ue=None, te=None,):
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('atomic_batch_mutate_result')
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class truncate_args(object):
  """
  Attributes:
   - cfname
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'cfname', None, None, ), # 1
  )

  def __init__(self, cfname=None,):
    self.cfname = cfname

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.cfname = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('truncate_args')
    if self.cfname is not None:
      oprot.writeFieldBegin('cfname', TType.STRING, 1)
      oprot.writeString(self.cfname)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.cfname is None:
      raise TProtocol.TProtocolException(message='Required field cfname is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class truncate_result(object):
  """
  Attributes:
   - ire
   - ue
   - te
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
  )

  def __init__(self, ire=None, ue=None, te=None,):
    self.ire = ire
    self.ue = ue
    self.te = te

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('truncate_result')
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_schema_versions_args(object):

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_schema_versions_args')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_schema_versions_result(object):
  """
  Attributes:
   - success
   - ire
  """

  thrift_spec = (
    (0, TType.MAP, 'success', (TType.STRING,None,TType.LIST,(TType.STRING,None)), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, ire=None,):
    self.success = success
    self.ire = ire

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.MAP:
          self.success = {}
          (_ktype286, _vtype287, _size285 ) = iprot.readMapBegin() 
          for _i289 in xrange(_size285):
            _key290 = iprot.readString();
            _val291 = []
            (_etype295, _size292) = iprot.readListBegin()
            for _i296 in xrange(_size292):
              _elem297 = iprot.readString();
              _val291.append(_elem297)
            iprot.readListEnd()
            self.success[_key290] = _val291
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_schema_versions_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.MAP, 0)
      oprot.writeMapBegin(TType.STRING, TType.LIST, len(self.success))
      for kiter298,viter299 in self.success.items():
        oprot.writeString(kiter298)
        oprot.writeListBegin(TType.STRING, len(viter299))
        for iter300 in viter299:
          oprot.writeString(iter300)
        oprot.writeListEnd()
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_keyspaces_args(object):

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_keyspaces_args')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_keyspaces_result(object):
  """
  Attributes:
   - success
   - ire
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(KsDef, KsDef.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, ire=None,):
    self.success = success
    self.ire = ire

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype304, _size301) = iprot.readListBegin()
          for _i305 in xrange(_size301):
            _elem306 = KsDef()
            _elem306.read(iprot)
            self.success.append(_elem306)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_keyspaces_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter307 in self.success:
        iter307.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_cluster_name_args(object):

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_cluster_name_args')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_cluster_name_result(object):
  """
  Attributes:
   - success
  """

  thrift_spec = (
    (0, TType.STRING, 'success', None, None, ), # 0
  )

  def __init__(self, success=None,):
    self.success = success

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRING:
          self.success = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_cluster_name_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRING, 0)
      oprot.writeString(self.success)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_version_args(object):

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_version_args')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_version_result(object):
  """
  Attributes:
   - success
  """

  thrift_spec = (
    (0, TType.STRING, 'success', None, None, ), # 0
  )

  def __init__(self, success=None,):
    self.success = success

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRING:
          self.success = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_version_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRING, 0)
      oprot.writeString(self.success)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_ring_args(object):
  """
  Attributes:
   - keyspace
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'keyspace', None, None, ), # 1
  )

  def __init__(self, keyspace=None,):
    self.keyspace = keyspace

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.keyspace = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_ring_args')
    if self.keyspace is not None:
      oprot.writeFieldBegin('keyspace', TType.STRING, 1)
      oprot.writeString(self.keyspace)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.keyspace is None:
      raise TProtocol.TProtocolException(message='Required field keyspace is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_ring_result(object):
  """
  Attributes:
   - success
   - ire
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(TokenRange, TokenRange.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, ire=None,):
    self.success = success
    self.ire = ire

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype311, _size308) = iprot.readListBegin()
          for _i312 in xrange(_size308):
            _elem313 = TokenRange()
            _elem313.read(iprot)
            self.success.append(_elem313)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_ring_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter314 in self.success:
        iter314.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_token_map_args(object):

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_token_map_args')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_token_map_result(object):
  """
  Attributes:
   - success
   - ire
  """

  thrift_spec = (
    (0, TType.MAP, 'success', (TType.STRING,None,TType.STRING,None), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, ire=None,):
    self.success = success
    self.ire = ire

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.MAP:
          self.success = {}
          (_ktype316, _vtype317, _size315 ) = iprot.readMapBegin() 
          for _i319 in xrange(_size315):
            _key320 = iprot.readString();
            _val321 = iprot.readString();
            self.success[_key320] = _val321
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_token_map_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.MAP, 0)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.success))
      for kiter322,viter323 in self.success.items():
        oprot.writeString(kiter322)
        oprot.writeString(viter323)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_partitioner_args(object):

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_partitioner_args')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_partitioner_result(object):
  """
  Attributes:
   - success
  """

  thrift_spec = (
    (0, TType.STRING, 'success', None, None, ), # 0
  )

  def __init__(self, success=None,):
    self.success = success

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRING:
          self.success = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_partitioner_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRING, 0)
      oprot.writeString(self.success)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_snitch_args(object):

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_snitch_args')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_snitch_result(object):
  """
  Attributes:
   - success
  """

  thrift_spec = (
    (0, TType.STRING, 'success', None, None, ), # 0
  )

  def __init__(self, success=None,):
    self.success = success

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRING:
          self.success = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_snitch_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRING, 0)
      oprot.writeString(self.success)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_keyspace_args(object):
  """
  Attributes:
   - keyspace
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'keyspace', None, None, ), # 1
  )

  def __init__(self, keyspace=None,):
    self.keyspace = keyspace

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.keyspace = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_keyspace_args')
    if self.keyspace is not None:
      oprot.writeFieldBegin('keyspace', TType.STRING, 1)
      oprot.writeString(self.keyspace)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.keyspace is None:
      raise TProtocol.TProtocolException(message='Required field keyspace is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_keyspace_result(object):
  """
  Attributes:
   - success
   - nfe
   - ire
  """

  thrift_spec = (
    (0, TType.STRUCT, 'success', (KsDef, KsDef.thrift_spec), None, ), # 0
    (1, TType.STRUCT, 'nfe', (NotFoundException, NotFoundException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, nfe=None, ire=None,):
    self.success = success
    self.nfe = nfe
    self.ire = ire

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRUCT:
          self.success = KsDef()
          self.success.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.nfe = NotFoundException()
          self.nfe.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_keyspace_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRUCT, 0)
      self.success.write(oprot)
      oprot.writeFieldEnd()
    if self.nfe is not None:
      oprot.writeFieldBegin('nfe', TType.STRUCT, 1)
      self.nfe.write(oprot)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 2)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_splits_args(object):
  """
  Attributes:
   - cfName
   - start_token
   - end_token
   - keys_per_split
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'cfName', None, None, ), # 1
    (2, TType.STRING, 'start_token', None, None, ), # 2
    (3, TType.STRING, 'end_token', None, None, ), # 3
    (4, TType.I32, 'keys_per_split', None, None, ), # 4
  )

  def __init__(self, cfName=None, start_token=None, end_token=None, keys_per_split=None,):
    self.cfName = cfName
    self.start_token = start_token
    self.end_token = end_token
    self.keys_per_split = keys_per_split

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.cfName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.start_token = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.end_token = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.keys_per_split = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_splits_args')
    if self.cfName is not None:
      oprot.writeFieldBegin('cfName', TType.STRING, 1)
      oprot.writeString(self.cfName)
      oprot.writeFieldEnd()
    if self.start_token is not None:
      oprot.writeFieldBegin('start_token', TType.STRING, 2)
      oprot.writeString(self.start_token)
      oprot.writeFieldEnd()
    if self.end_token is not None:
      oprot.writeFieldBegin('end_token', TType.STRING, 3)
      oprot.writeString(self.end_token)
      oprot.writeFieldEnd()
    if self.keys_per_split is not None:
      oprot.writeFieldBegin('keys_per_split', TType.I32, 4)
      oprot.writeI32(self.keys_per_split)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.cfName is None:
      raise TProtocol.TProtocolException(message='Required field cfName is unset!')
    if self.start_token is None:
      raise TProtocol.TProtocolException(message='Required field start_token is unset!')
    if self.end_token is None:
      raise TProtocol.TProtocolException(message='Required field end_token is unset!')
    if self.keys_per_split is None:
      raise TProtocol.TProtocolException(message='Required field keys_per_split is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_splits_result(object):
  """
  Attributes:
   - success
   - ire
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRING,None), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, ire=None,):
    self.success = success
    self.ire = ire

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype327, _size324) = iprot.readListBegin()
          for _i328 in xrange(_size324):
            _elem329 = iprot.readString();
            self.success.append(_elem329)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_splits_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRING, len(self.success))
      for iter330 in self.success:
        oprot.writeString(iter330)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class trace_next_query_args(object):

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('trace_next_query_args')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class trace_next_query_result(object):
  """
  Attributes:
   - success
  """

  thrift_spec = (
    (0, TType.STRING, 'success', None, None, ), # 0
  )

  def __init__(self, success=None,):
    self.success = success

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRING:
          self.success = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('trace_next_query_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRING, 0)
      oprot.writeString(self.success)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_splits_ex_args(object):
  """
  Attributes:
   - cfName
   - start_token
   - end_token
   - keys_per_split
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'cfName', None, None, ), # 1
    (2, TType.STRING, 'start_token', None, None, ), # 2
    (3, TType.STRING, 'end_token', None, None, ), # 3
    (4, TType.I32, 'keys_per_split', None, None, ), # 4
  )

  def __init__(self, cfName=None, start_token=None, end_token=None, keys_per_split=None,):
    self.cfName = cfName
    self.start_token = start_token
    self.end_token = end_token
    self.keys_per_split = keys_per_split

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.cfName = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.start_token = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.end_token = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.keys_per_split = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_splits_ex_args')
    if self.cfName is not None:
      oprot.writeFieldBegin('cfName', TType.STRING, 1)
      oprot.writeString(self.cfName)
      oprot.writeFieldEnd()
    if self.start_token is not None:
      oprot.writeFieldBegin('start_token', TType.STRING, 2)
      oprot.writeString(self.start_token)
      oprot.writeFieldEnd()
    if self.end_token is not None:
      oprot.writeFieldBegin('end_token', TType.STRING, 3)
      oprot.writeString(self.end_token)
      oprot.writeFieldEnd()
    if self.keys_per_split is not None:
      oprot.writeFieldBegin('keys_per_split', TType.I32, 4)
      oprot.writeI32(self.keys_per_split)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.cfName is None:
      raise TProtocol.TProtocolException(message='Required field cfName is unset!')
    if self.start_token is None:
      raise TProtocol.TProtocolException(message='Required field start_token is unset!')
    if self.end_token is None:
      raise TProtocol.TProtocolException(message='Required field end_token is unset!')
    if self.keys_per_split is None:
      raise TProtocol.TProtocolException(message='Required field keys_per_split is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class describe_splits_ex_result(object):
  """
  Attributes:
   - success
   - ire
  """

  thrift_spec = (
    (0, TType.LIST, 'success', (TType.STRUCT,(CfSplit, CfSplit.thrift_spec)), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, ire=None,):
    self.success = success
    self.ire = ire

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.LIST:
          self.success = []
          (_etype334, _size331) = iprot.readListBegin()
          for _i335 in xrange(_size331):
            _elem336 = CfSplit()
            _elem336.read(iprot)
            self.success.append(_elem336)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('describe_splits_ex_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.LIST, 0)
      oprot.writeListBegin(TType.STRUCT, len(self.success))
      for iter337 in self.success:
        iter337.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_add_column_family_args(object):
  """
  Attributes:
   - cf_def
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'cf_def', (CfDef, CfDef.thrift_spec), None, ), # 1
  )

  def __init__(self, cf_def=None,):
    self.cf_def = cf_def

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.cf_def = CfDef()
          self.cf_def.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_add_column_family_args')
    if self.cf_def is not None:
      oprot.writeFieldBegin('cf_def', TType.STRUCT, 1)
      self.cf_def.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.cf_def is None:
      raise TProtocol.TProtocolException(message='Required field cf_def is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_add_column_family_result(object):
  """
  Attributes:
   - success
   - ire
   - sde
  """

  thrift_spec = (
    (0, TType.STRING, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'sde', (SchemaDisagreementException, SchemaDisagreementException.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, ire=None, sde=None,):
    self.success = success
    self.ire = ire
    self.sde = sde

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRING:
          self.success = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.sde = SchemaDisagreementException()
          self.sde.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_add_column_family_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRING, 0)
      oprot.writeString(self.success)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.sde is not None:
      oprot.writeFieldBegin('sde', TType.STRUCT, 2)
      self.sde.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_drop_column_family_args(object):
  """
  Attributes:
   - column_family
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'column_family', None, None, ), # 1
  )

  def __init__(self, column_family=None,):
    self.column_family = column_family

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.column_family = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_drop_column_family_args')
    if self.column_family is not None:
      oprot.writeFieldBegin('column_family', TType.STRING, 1)
      oprot.writeString(self.column_family)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.column_family is None:
      raise TProtocol.TProtocolException(message='Required field column_family is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_drop_column_family_result(object):
  """
  Attributes:
   - success
   - ire
   - sde
  """

  thrift_spec = (
    (0, TType.STRING, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'sde', (SchemaDisagreementException, SchemaDisagreementException.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, ire=None, sde=None,):
    self.success = success
    self.ire = ire
    self.sde = sde

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRING:
          self.success = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.sde = SchemaDisagreementException()
          self.sde.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_drop_column_family_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRING, 0)
      oprot.writeString(self.success)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.sde is not None:
      oprot.writeFieldBegin('sde', TType.STRUCT, 2)
      self.sde.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_add_keyspace_args(object):
  """
  Attributes:
   - ks_def
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'ks_def', (KsDef, KsDef.thrift_spec), None, ), # 1
  )

  def __init__(self, ks_def=None,):
    self.ks_def = ks_def

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.ks_def = KsDef()
          self.ks_def.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_add_keyspace_args')
    if self.ks_def is not None:
      oprot.writeFieldBegin('ks_def', TType.STRUCT, 1)
      self.ks_def.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.ks_def is None:
      raise TProtocol.TProtocolException(message='Required field ks_def is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_add_keyspace_result(object):
  """
  Attributes:
   - success
   - ire
   - sde
  """

  thrift_spec = (
    (0, TType.STRING, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'sde', (SchemaDisagreementException, SchemaDisagreementException.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, ire=None, sde=None,):
    self.success = success
    self.ire = ire
    self.sde = sde

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRING:
          self.success = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.sde = SchemaDisagreementException()
          self.sde.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_add_keyspace_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRING, 0)
      oprot.writeString(self.success)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.sde is not None:
      oprot.writeFieldBegin('sde', TType.STRUCT, 2)
      self.sde.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_drop_keyspace_args(object):
  """
  Attributes:
   - keyspace
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'keyspace', None, None, ), # 1
  )

  def __init__(self, keyspace=None,):
    self.keyspace = keyspace

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.keyspace = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_drop_keyspace_args')
    if self.keyspace is not None:
      oprot.writeFieldBegin('keyspace', TType.STRING, 1)
      oprot.writeString(self.keyspace)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.keyspace is None:
      raise TProtocol.TProtocolException(message='Required field keyspace is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_drop_keyspace_result(object):
  """
  Attributes:
   - success
   - ire
   - sde
  """

  thrift_spec = (
    (0, TType.STRING, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'sde', (SchemaDisagreementException, SchemaDisagreementException.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, ire=None, sde=None,):
    self.success = success
    self.ire = ire
    self.sde = sde

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRING:
          self.success = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.sde = SchemaDisagreementException()
          self.sde.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_drop_keyspace_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRING, 0)
      oprot.writeString(self.success)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.sde is not None:
      oprot.writeFieldBegin('sde', TType.STRUCT, 2)
      self.sde.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_update_keyspace_args(object):
  """
  Attributes:
   - ks_def
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'ks_def', (KsDef, KsDef.thrift_spec), None, ), # 1
  )

  def __init__(self, ks_def=None,):
    self.ks_def = ks_def

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.ks_def = KsDef()
          self.ks_def.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_update_keyspace_args')
    if self.ks_def is not None:
      oprot.writeFieldBegin('ks_def', TType.STRUCT, 1)
      self.ks_def.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.ks_def is None:
      raise TProtocol.TProtocolException(message='Required field ks_def is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_update_keyspace_result(object):
  """
  Attributes:
   - success
   - ire
   - sde
  """

  thrift_spec = (
    (0, TType.STRING, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'sde', (SchemaDisagreementException, SchemaDisagreementException.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, ire=None, sde=None,):
    self.success = success
    self.ire = ire
    self.sde = sde

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRING:
          self.success = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.sde = SchemaDisagreementException()
          self.sde.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_update_keyspace_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRING, 0)
      oprot.writeString(self.success)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.sde is not None:
      oprot.writeFieldBegin('sde', TType.STRUCT, 2)
      self.sde.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_update_column_family_args(object):
  """
  Attributes:
   - cf_def
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'cf_def', (CfDef, CfDef.thrift_spec), None, ), # 1
  )

  def __init__(self, cf_def=None,):
    self.cf_def = cf_def

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.cf_def = CfDef()
          self.cf_def.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_update_column_family_args')
    if self.cf_def is not None:
      oprot.writeFieldBegin('cf_def', TType.STRUCT, 1)
      self.cf_def.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.cf_def is None:
      raise TProtocol.TProtocolException(message='Required field cf_def is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class system_update_column_family_result(object):
  """
  Attributes:
   - success
   - ire
   - sde
  """

  thrift_spec = (
    (0, TType.STRING, 'success', None, None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'sde', (SchemaDisagreementException, SchemaDisagreementException.thrift_spec), None, ), # 2
  )

  def __init__(self, success=None, ire=None, sde=None,):
    self.success = success
    self.ire = ire
    self.sde = sde

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRING:
          self.success = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.sde = SchemaDisagreementException()
          self.sde.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('system_update_column_family_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRING, 0)
      oprot.writeString(self.success)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.sde is not None:
      oprot.writeFieldBegin('sde', TType.STRUCT, 2)
      self.sde.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class execute_cql_query_args(object):
  """
  Attributes:
   - query
   - compression
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'query', None, None, ), # 1
    (2, TType.I32, 'compression', None, None, ), # 2
  )

  def __init__(self, query=None, compression=None,):
    self.query = query
    self.compression = compression

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.query = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.compression = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('execute_cql_query_args')
    if self.query is not None:
      oprot.writeFieldBegin('query', TType.STRING, 1)
      oprot.writeString(self.query)
      oprot.writeFieldEnd()
    if self.compression is not None:
      oprot.writeFieldBegin('compression', TType.I32, 2)
      oprot.writeI32(self.compression)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.query is None:
      raise TProtocol.TProtocolException(message='Required field query is unset!')
    if self.compression is None:
      raise TProtocol.TProtocolException(message='Required field compression is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class execute_cql_query_result(object):
  """
  Attributes:
   - success
   - ire
   - ue
   - te
   - sde
  """

  thrift_spec = (
    (0, TType.STRUCT, 'success', (CqlResult, CqlResult.thrift_spec), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
    (4, TType.STRUCT, 'sde', (SchemaDisagreementException, SchemaDisagreementException.thrift_spec), None, ), # 4
  )

  def __init__(self, success=None, ire=None, ue=None, te=None, sde=None,):
    self.success = success
    self.ire = ire
    self.ue = ue
    self.te = te
    self.sde = sde

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRUCT:
          self.success = CqlResult()
          self.success.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRUCT:
          self.sde = SchemaDisagreementException()
          self.sde.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('execute_cql_query_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRUCT, 0)
      self.success.write(oprot)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    if self.sde is not None:
      oprot.writeFieldBegin('sde', TType.STRUCT, 4)
      self.sde.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class execute_cql3_query_args(object):
  """
  Attributes:
   - query
   - compression
   - consistency
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'query', None, None, ), # 1
    (2, TType.I32, 'compression', None, None, ), # 2
    (3, TType.I32, 'consistency', None, None, ), # 3
  )

  def __init__(self, query=None, compression=None, consistency=None,):
    self.query = query
    self.compression = compression
    self.consistency = consistency

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.query = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.compression = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I32:
          self.consistency = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('execute_cql3_query_args')
    if self.query is not None:
      oprot.writeFieldBegin('query', TType.STRING, 1)
      oprot.writeString(self.query)
      oprot.writeFieldEnd()
    if self.compression is not None:
      oprot.writeFieldBegin('compression', TType.I32, 2)
      oprot.writeI32(self.compression)
      oprot.writeFieldEnd()
    if self.consistency is not None:
      oprot.writeFieldBegin('consistency', TType.I32, 3)
      oprot.writeI32(self.consistency)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.query is None:
      raise TProtocol.TProtocolException(message='Required field query is unset!')
    if self.compression is None:
      raise TProtocol.TProtocolException(message='Required field compression is unset!')
    if self.consistency is None:
      raise TProtocol.TProtocolException(message='Required field consistency is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class execute_cql3_query_result(object):
  """
  Attributes:
   - success
   - ire
   - ue
   - te
   - sde
  """

  thrift_spec = (
    (0, TType.STRUCT, 'success', (CqlResult, CqlResult.thrift_spec), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
    (4, TType.STRUCT, 'sde', (SchemaDisagreementException, SchemaDisagreementException.thrift_spec), None, ), # 4
  )

  def __init__(self, success=None, ire=None, ue=None, te=None, sde=None,):
    self.success = success
    self.ire = ire
    self.ue = ue
    self.te = te
    self.sde = sde

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRUCT:
          self.success = CqlResult()
          self.success.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRUCT:
          self.sde = SchemaDisagreementException()
          self.sde.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('execute_cql3_query_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRUCT, 0)
      self.success.write(oprot)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    if self.sde is not None:
      oprot.writeFieldBegin('sde', TType.STRUCT, 4)
      self.sde.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class prepare_cql_query_args(object):
  """
  Attributes:
   - query
   - compression
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'query', None, None, ), # 1
    (2, TType.I32, 'compression', None, None, ), # 2
  )

  def __init__(self, query=None, compression=None,):
    self.query = query
    self.compression = compression

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.query = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.compression = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('prepare_cql_query_args')
    if self.query is not None:
      oprot.writeFieldBegin('query', TType.STRING, 1)
      oprot.writeString(self.query)
      oprot.writeFieldEnd()
    if self.compression is not None:
      oprot.writeFieldBegin('compression', TType.I32, 2)
      oprot.writeI32(self.compression)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.query is None:
      raise TProtocol.TProtocolException(message='Required field query is unset!')
    if self.compression is None:
      raise TProtocol.TProtocolException(message='Required field compression is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class prepare_cql_query_result(object):
  """
  Attributes:
   - success
   - ire
  """

  thrift_spec = (
    (0, TType.STRUCT, 'success', (CqlPreparedResult, CqlPreparedResult.thrift_spec), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, ire=None,):
    self.success = success
    self.ire = ire

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRUCT:
          self.success = CqlPreparedResult()
          self.success.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('prepare_cql_query_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRUCT, 0)
      self.success.write(oprot)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class prepare_cql3_query_args(object):
  """
  Attributes:
   - query
   - compression
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'query', None, None, ), # 1
    (2, TType.I32, 'compression', None, None, ), # 2
  )

  def __init__(self, query=None, compression=None,):
    self.query = query
    self.compression = compression

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.query = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.compression = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('prepare_cql3_query_args')
    if self.query is not None:
      oprot.writeFieldBegin('query', TType.STRING, 1)
      oprot.writeString(self.query)
      oprot.writeFieldEnd()
    if self.compression is not None:
      oprot.writeFieldBegin('compression', TType.I32, 2)
      oprot.writeI32(self.compression)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.query is None:
      raise TProtocol.TProtocolException(message='Required field query is unset!')
    if self.compression is None:
      raise TProtocol.TProtocolException(message='Required field compression is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class prepare_cql3_query_result(object):
  """
  Attributes:
   - success
   - ire
  """

  thrift_spec = (
    (0, TType.STRUCT, 'success', (CqlPreparedResult, CqlPreparedResult.thrift_spec), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
  )

  def __init__(self, success=None, ire=None,):
    self.success = success
    self.ire = ire

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRUCT:
          self.success = CqlPreparedResult()
          self.success.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('prepare_cql3_query_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRUCT, 0)
      self.success.write(oprot)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class execute_prepared_cql_query_args(object):
  """
  Attributes:
   - itemId
   - values
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'itemId', None, None, ), # 1
    (2, TType.LIST, 'values', (TType.STRING,None), None, ), # 2
  )

  def __init__(self, itemId=None, values=None,):
    self.itemId = itemId
    self.values = values

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.itemId = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.values = []
          (_etype341, _size338) = iprot.readListBegin()
          for _i342 in xrange(_size338):
            _elem343 = iprot.readString();
            self.values.append(_elem343)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('execute_prepared_cql_query_args')
    if self.itemId is not None:
      oprot.writeFieldBegin('itemId', TType.I32, 1)
      oprot.writeI32(self.itemId)
      oprot.writeFieldEnd()
    if self.values is not None:
      oprot.writeFieldBegin('values', TType.LIST, 2)
      oprot.writeListBegin(TType.STRING, len(self.values))
      for iter344 in self.values:
        oprot.writeString(iter344)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.itemId is None:
      raise TProtocol.TProtocolException(message='Required field itemId is unset!')
    if self.values is None:
      raise TProtocol.TProtocolException(message='Required field values is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class execute_prepared_cql_query_result(object):
  """
  Attributes:
   - success
   - ire
   - ue
   - te
   - sde
  """

  thrift_spec = (
    (0, TType.STRUCT, 'success', (CqlResult, CqlResult.thrift_spec), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
    (4, TType.STRUCT, 'sde', (SchemaDisagreementException, SchemaDisagreementException.thrift_spec), None, ), # 4
  )

  def __init__(self, success=None, ire=None, ue=None, te=None, sde=None,):
    self.success = success
    self.ire = ire
    self.ue = ue
    self.te = te
    self.sde = sde

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRUCT:
          self.success = CqlResult()
          self.success.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRUCT:
          self.sde = SchemaDisagreementException()
          self.sde.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('execute_prepared_cql_query_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRUCT, 0)
      self.success.write(oprot)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    if self.sde is not None:
      oprot.writeFieldBegin('sde', TType.STRUCT, 4)
      self.sde.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class execute_prepared_cql3_query_args(object):
  """
  Attributes:
   - itemId
   - values
   - consistency
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'itemId', None, None, ), # 1
    (2, TType.LIST, 'values', (TType.STRING,None), None, ), # 2
    (3, TType.I32, 'consistency', None, None, ), # 3
  )

  def __init__(self, itemId=None, values=None, consistency=None,):
    self.itemId = itemId
    self.values = values
    self.consistency = consistency

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.itemId = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.values = []
          (_etype348, _size345) = iprot.readListBegin()
          for _i349 in xrange(_size345):
            _elem350 = iprot.readString();
            self.values.append(_elem350)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I32:
          self.consistency = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('execute_prepared_cql3_query_args')
    if self.itemId is not None:
      oprot.writeFieldBegin('itemId', TType.I32, 1)
      oprot.writeI32(self.itemId)
      oprot.writeFieldEnd()
    if self.values is not None:
      oprot.writeFieldBegin('values', TType.LIST, 2)
      oprot.writeListBegin(TType.STRING, len(self.values))
      for iter351 in self.values:
        oprot.writeString(iter351)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.consistency is not None:
      oprot.writeFieldBegin('consistency', TType.I32, 3)
      oprot.writeI32(self.consistency)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.itemId is None:
      raise TProtocol.TProtocolException(message='Required field itemId is unset!')
    if self.values is None:
      raise TProtocol.TProtocolException(message='Required field values is unset!')
    if self.consistency is None:
      raise TProtocol.TProtocolException(message='Required field consistency is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class execute_prepared_cql3_query_result(object):
  """
  Attributes:
   - success
   - ire
   - ue
   - te
   - sde
  """

  thrift_spec = (
    (0, TType.STRUCT, 'success', (CqlResult, CqlResult.thrift_spec), None, ), # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'ue', (UnavailableException, UnavailableException.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'te', (TimedOutException, TimedOutException.thrift_spec), None, ), # 3
    (4, TType.STRUCT, 'sde', (SchemaDisagreementException, SchemaDisagreementException.thrift_spec), None, ), # 4
  )

  def __init__(self, success=None, ire=None, ue=None, te=None, sde=None,):
    self.success = success
    self.ire = ire
    self.ue = ue
    self.te = te
    self.sde = sde

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 0:
        if ftype == TType.STRUCT:
          self.success = CqlResult()
          self.success.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.ue = UnavailableException()
          self.ue.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.te = TimedOutException()
          self.te.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRUCT:
          self.sde = SchemaDisagreementException()
          self.sde.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('execute_prepared_cql3_query_result')
    if self.success is not None:
      oprot.writeFieldBegin('success', TType.STRUCT, 0)
      self.success.write(oprot)
      oprot.writeFieldEnd()
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    if self.ue is not None:
      oprot.writeFieldBegin('ue', TType.STRUCT, 2)
      self.ue.write(oprot)
      oprot.writeFieldEnd()
    if self.te is not None:
      oprot.writeFieldBegin('te', TType.STRUCT, 3)
      self.te.write(oprot)
      oprot.writeFieldEnd()
    if self.sde is not None:
      oprot.writeFieldBegin('sde', TType.STRUCT, 4)
      self.sde.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class set_cql_version_args(object):
  """
  Attributes:
   - version
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'version', None, None, ), # 1
  )

  def __init__(self, version=None,):
    self.version = version

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.version = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('set_cql_version_args')
    if self.version is not None:
      oprot.writeFieldBegin('version', TType.STRING, 1)
      oprot.writeString(self.version)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.version is None:
      raise TProtocol.TProtocolException(message='Required field version is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class set_cql_version_result(object):
  """
  Attributes:
   - ire
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'ire', (InvalidRequestException, InvalidRequestException.thrift_spec), None, ), # 1
  )

  def __init__(self, ire=None,):
    self.ire = ire

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.ire = InvalidRequestException()
          self.ire.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('set_cql_version_result')
    if self.ire is not None:
      oprot.writeFieldBegin('ire', TType.STRUCT, 1)
      self.ire.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

########NEW FILE########
__FILENAME__ = constants
#
# Autogenerated by Thrift Compiler (0.9.0)
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#
#  options string: py:new_style
#

from thrift.Thrift import TType, TMessageType, TException, TApplicationException
from ttypes import *

VERSION = "19.36.1"

########NEW FILE########
__FILENAME__ = ttypes
#
# Autogenerated by Thrift Compiler (0.9.0)
#
# DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
#
#  options string: py:new_style
#

from thrift.Thrift import TType, TMessageType, TException, TApplicationException

from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol, TProtocol
try:
  from thrift.protocol import fastbinary
except:
  fastbinary = None


class ConsistencyLevel(object):
  """
  The ConsistencyLevel is an enum that controls both read and write
  behavior based on the ReplicationFactor of the keyspace.  The
  different consistency levels have different meanings, depending on
  if you're doing a write or read operation.

  If W + R > ReplicationFactor, where W is the number of nodes to
  block for on write, and R the number to block for on reads, you
  will have strongly consistent behavior; that is, readers will
  always see the most recent write. Of these, the most interesting is
  to do QUORUM reads and writes, which gives you consistency while
  still allowing availability in the face of node failures up to half
  of <ReplicationFactor>. Of course if latency is more important than
  consistency then you can use lower values for either or both.

  Some ConsistencyLevels (ONE, TWO, THREE) refer to a specific number
  of replicas rather than a logical concept that adjusts
  automatically with the replication factor.  Of these, only ONE is
  commonly used; TWO and (even more rarely) THREE are only useful
  when you care more about guaranteeing a certain level of
  durability, than consistency.

  Write consistency levels make the following guarantees before reporting success to the client:
    ANY          Ensure that the write has been written once somewhere, including possibly being hinted in a non-target node.
    ONE          Ensure that the write has been written to at least 1 node's commit log and memory table
    TWO          Ensure that the write has been written to at least 2 node's commit log and memory table
    THREE        Ensure that the write has been written to at least 3 node's commit log and memory table
    QUORUM       Ensure that the write has been written to <ReplicationFactor> / 2 + 1 nodes
    LOCAL_ONE    Ensure that the write has been written to 1 node within the local datacenter (requires NetworkTopologyStrategy)
    LOCAL_QUORUM Ensure that the write has been written to <ReplicationFactor> / 2 + 1 nodes, within the local datacenter (requires NetworkTopologyStrategy)
    EACH_QUORUM  Ensure that the write has been written to <ReplicationFactor> / 2 + 1 nodes in each datacenter (requires NetworkTopologyStrategy)
    ALL          Ensure that the write is written to <code>&lt;ReplicationFactor&gt;</code> nodes before responding to the client.

  Read consistency levels make the following guarantees before returning successful results to the client:
    ANY          Not supported. You probably want ONE instead.
    ONE          Returns the record obtained from a single replica.
    TWO          Returns the record with the most recent timestamp once two replicas have replied.
    THREE        Returns the record with the most recent timestamp once three replicas have replied.
    QUORUM       Returns the record with the most recent timestamp once a majority of replicas have replied.
    LOCAL_ONE    Returns the record with the most recent timestamp once a single replica within the local datacenter have replied.
    LOCAL_QUORUM Returns the record with the most recent timestamp once a majority of replicas within the local datacenter have replied.
    EACH_QUORUM  Returns the record with the most recent timestamp once a majority of replicas within each datacenter have replied.
    ALL          Returns the record with the most recent timestamp once all replicas have replied (implies no replica may be down)..
  """
  ONE = 1
  QUORUM = 2
  LOCAL_QUORUM = 3
  EACH_QUORUM = 4
  ALL = 5
  ANY = 6
  TWO = 7
  THREE = 8
  LOCAL_ONE = 11

  _VALUES_TO_NAMES = {
    1: "ONE",
    2: "QUORUM",
    3: "LOCAL_QUORUM",
    4: "EACH_QUORUM",
    5: "ALL",
    6: "ANY",
    7: "TWO",
    8: "THREE",
    11: "LOCAL_ONE",
  }

  _NAMES_TO_VALUES = {
    "ONE": 1,
    "QUORUM": 2,
    "LOCAL_QUORUM": 3,
    "EACH_QUORUM": 4,
    "ALL": 5,
    "ANY": 6,
    "TWO": 7,
    "THREE": 8,
    "LOCAL_ONE": 11,
  }

class IndexOperator(object):
  EQ = 0
  GTE = 1
  GT = 2
  LTE = 3
  LT = 4

  _VALUES_TO_NAMES = {
    0: "EQ",
    1: "GTE",
    2: "GT",
    3: "LTE",
    4: "LT",
  }

  _NAMES_TO_VALUES = {
    "EQ": 0,
    "GTE": 1,
    "GT": 2,
    "LTE": 3,
    "LT": 4,
  }

class IndexType(object):
  KEYS = 0
  CUSTOM = 1
  COMPOSITES = 2

  _VALUES_TO_NAMES = {
    0: "KEYS",
    1: "CUSTOM",
    2: "COMPOSITES",
  }

  _NAMES_TO_VALUES = {
    "KEYS": 0,
    "CUSTOM": 1,
    "COMPOSITES": 2,
  }

class Compression(object):
  """
  CQL query compression
  """
  GZIP = 1
  NONE = 2

  _VALUES_TO_NAMES = {
    1: "GZIP",
    2: "NONE",
  }

  _NAMES_TO_VALUES = {
    "GZIP": 1,
    "NONE": 2,
  }

class CqlResultType(object):
  ROWS = 1
  VOID = 2
  INT = 3

  _VALUES_TO_NAMES = {
    1: "ROWS",
    2: "VOID",
    3: "INT",
  }

  _NAMES_TO_VALUES = {
    "ROWS": 1,
    "VOID": 2,
    "INT": 3,
  }


class Column(object):
  """
  Basic unit of data within a ColumnFamily.
  @param name, the name by which this column is set and retrieved.  Maximum 64KB long.
  @param value. The data associated with the name.  Maximum 2GB long, but in practice you should limit it to small numbers of MB (since Thrift must read the full value into memory to operate on it).
  @param timestamp. The timestamp is used for conflict detection/resolution when two columns with same name need to be compared.
  @param ttl. An optional, positive delay (in seconds) after which the column will be automatically deleted.

  Attributes:
   - name
   - value
   - timestamp
   - ttl
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'name', None, None, ), # 1
    (2, TType.STRING, 'value', None, None, ), # 2
    (3, TType.I64, 'timestamp', None, None, ), # 3
    (4, TType.I32, 'ttl', None, None, ), # 4
  )

  def __init__(self, name=None, value=None, timestamp=None, ttl=None,):
    self.name = name
    self.value = value
    self.timestamp = timestamp
    self.ttl = ttl

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.value = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.ttl = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('Column')
    if self.name is not None:
      oprot.writeFieldBegin('name', TType.STRING, 1)
      oprot.writeString(self.name)
      oprot.writeFieldEnd()
    if self.value is not None:
      oprot.writeFieldBegin('value', TType.STRING, 2)
      oprot.writeString(self.value)
      oprot.writeFieldEnd()
    if self.timestamp is not None:
      oprot.writeFieldBegin('timestamp', TType.I64, 3)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    if self.ttl is not None:
      oprot.writeFieldBegin('ttl', TType.I32, 4)
      oprot.writeI32(self.ttl)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.name is None:
      raise TProtocol.TProtocolException(message='Required field name is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class SuperColumn(object):
  """
  A named list of columns.
  @param name. see Column.name.
  @param columns. A collection of standard Columns.  The columns within a super column are defined in an adhoc manner.
                  Columns within a super column do not have to have matching structures (similarly named child columns).

  Attributes:
   - name
   - columns
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'name', None, None, ), # 1
    (2, TType.LIST, 'columns', (TType.STRUCT,(Column, Column.thrift_spec)), None, ), # 2
  )

  def __init__(self, name=None, columns=None,):
    self.name = name
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.columns = []
          (_etype3, _size0) = iprot.readListBegin()
          for _i4 in xrange(_size0):
            _elem5 = Column()
            _elem5.read(iprot)
            self.columns.append(_elem5)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('SuperColumn')
    if self.name is not None:
      oprot.writeFieldBegin('name', TType.STRING, 1)
      oprot.writeString(self.name)
      oprot.writeFieldEnd()
    if self.columns is not None:
      oprot.writeFieldBegin('columns', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.columns))
      for iter6 in self.columns:
        iter6.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.name is None:
      raise TProtocol.TProtocolException(message='Required field name is unset!')
    if self.columns is None:
      raise TProtocol.TProtocolException(message='Required field columns is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class CounterColumn(object):
  """
  Attributes:
   - name
   - value
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'name', None, None, ), # 1
    (2, TType.I64, 'value', None, None, ), # 2
  )

  def __init__(self, name=None, value=None,):
    self.name = name
    self.value = value

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I64:
          self.value = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('CounterColumn')
    if self.name is not None:
      oprot.writeFieldBegin('name', TType.STRING, 1)
      oprot.writeString(self.name)
      oprot.writeFieldEnd()
    if self.value is not None:
      oprot.writeFieldBegin('value', TType.I64, 2)
      oprot.writeI64(self.value)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.name is None:
      raise TProtocol.TProtocolException(message='Required field name is unset!')
    if self.value is None:
      raise TProtocol.TProtocolException(message='Required field value is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class CounterSuperColumn(object):
  """
  Attributes:
   - name
   - columns
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'name', None, None, ), # 1
    (2, TType.LIST, 'columns', (TType.STRUCT,(CounterColumn, CounterColumn.thrift_spec)), None, ), # 2
  )

  def __init__(self, name=None, columns=None,):
    self.name = name
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.columns = []
          (_etype10, _size7) = iprot.readListBegin()
          for _i11 in xrange(_size7):
            _elem12 = CounterColumn()
            _elem12.read(iprot)
            self.columns.append(_elem12)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('CounterSuperColumn')
    if self.name is not None:
      oprot.writeFieldBegin('name', TType.STRING, 1)
      oprot.writeString(self.name)
      oprot.writeFieldEnd()
    if self.columns is not None:
      oprot.writeFieldBegin('columns', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.columns))
      for iter13 in self.columns:
        iter13.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.name is None:
      raise TProtocol.TProtocolException(message='Required field name is unset!')
    if self.columns is None:
      raise TProtocol.TProtocolException(message='Required field columns is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class ColumnOrSuperColumn(object):
  """
  Methods for fetching rows/records from Cassandra will return either a single instance of ColumnOrSuperColumn or a list
  of ColumnOrSuperColumns (get_slice()). If you're looking up a SuperColumn (or list of SuperColumns) then the resulting
  instances of ColumnOrSuperColumn will have the requested SuperColumn in the attribute super_column. For queries resulting
  in Columns, those values will be in the attribute column. This change was made between 0.3 and 0.4 to standardize on
  single query methods that may return either a SuperColumn or Column.

  If the query was on a counter column family, you will either get a counter_column (instead of a column) or a
  counter_super_column (instead of a super_column)

  @param column. The Column returned by get() or get_slice().
  @param super_column. The SuperColumn returned by get() or get_slice().
  @param counter_column. The Counterolumn returned by get() or get_slice().
  @param counter_super_column. The CounterSuperColumn returned by get() or get_slice().

  Attributes:
   - column
   - super_column
   - counter_column
   - counter_super_column
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'column', (Column, Column.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'super_column', (SuperColumn, SuperColumn.thrift_spec), None, ), # 2
    (3, TType.STRUCT, 'counter_column', (CounterColumn, CounterColumn.thrift_spec), None, ), # 3
    (4, TType.STRUCT, 'counter_super_column', (CounterSuperColumn, CounterSuperColumn.thrift_spec), None, ), # 4
  )

  def __init__(self, column=None, super_column=None, counter_column=None, counter_super_column=None,):
    self.column = column
    self.super_column = super_column
    self.counter_column = counter_column
    self.counter_super_column = counter_super_column

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.column = Column()
          self.column.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.super_column = SuperColumn()
          self.super_column.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.counter_column = CounterColumn()
          self.counter_column.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRUCT:
          self.counter_super_column = CounterSuperColumn()
          self.counter_super_column.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('ColumnOrSuperColumn')
    if self.column is not None:
      oprot.writeFieldBegin('column', TType.STRUCT, 1)
      self.column.write(oprot)
      oprot.writeFieldEnd()
    if self.super_column is not None:
      oprot.writeFieldBegin('super_column', TType.STRUCT, 2)
      self.super_column.write(oprot)
      oprot.writeFieldEnd()
    if self.counter_column is not None:
      oprot.writeFieldBegin('counter_column', TType.STRUCT, 3)
      self.counter_column.write(oprot)
      oprot.writeFieldEnd()
    if self.counter_super_column is not None:
      oprot.writeFieldBegin('counter_super_column', TType.STRUCT, 4)
      self.counter_super_column.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class NotFoundException(TException):
  """
  A specific column was requested that does not exist.
  """

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('NotFoundException')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class InvalidRequestException(TException):
  """
  Invalid request could mean keyspace or column family does not exist, required parameters are missing, or a parameter is malformed.
  why contains an associated error message.

  Attributes:
   - why
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'why', None, None, ), # 1
  )

  def __init__(self, why=None,):
    self.why = why

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.why = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('InvalidRequestException')
    if self.why is not None:
      oprot.writeFieldBegin('why', TType.STRING, 1)
      oprot.writeString(self.why)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.why is None:
      raise TProtocol.TProtocolException(message='Required field why is unset!')
    return


  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class UnavailableException(TException):
  """
  Not all the replicas required could be created and/or read.
  """

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('UnavailableException')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class TimedOutException(TException):
  """
  RPC timeout was exceeded.  either a node failed mid-operation, or load was too high, or the requested op was too large.

  Attributes:
   - acknowledged_by: if a write operation was acknowledged by some replicas but not by enough to
  satisfy the required ConsistencyLevel, the number of successful
  replies will be given here. In case of atomic_batch_mutate method this field
  will be set to -1 if the batch was written to the batchlog and to 0 if it wasn't.
   - acknowledged_by_batchlog: in case of atomic_batch_mutate method this field tells if the batch was written to the batchlog.
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'acknowledged_by', None, None, ), # 1
    (2, TType.BOOL, 'acknowledged_by_batchlog', None, None, ), # 2
  )

  def __init__(self, acknowledged_by=None, acknowledged_by_batchlog=None,):
    self.acknowledged_by = acknowledged_by
    self.acknowledged_by_batchlog = acknowledged_by_batchlog

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.acknowledged_by = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.BOOL:
          self.acknowledged_by_batchlog = iprot.readBool();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('TimedOutException')
    if self.acknowledged_by is not None:
      oprot.writeFieldBegin('acknowledged_by', TType.I32, 1)
      oprot.writeI32(self.acknowledged_by)
      oprot.writeFieldEnd()
    if self.acknowledged_by_batchlog is not None:
      oprot.writeFieldBegin('acknowledged_by_batchlog', TType.BOOL, 2)
      oprot.writeBool(self.acknowledged_by_batchlog)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class AuthenticationException(TException):
  """
  invalid authentication request (invalid keyspace, user does not exist, or credentials invalid)

  Attributes:
   - why
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'why', None, None, ), # 1
  )

  def __init__(self, why=None,):
    self.why = why

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.why = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('AuthenticationException')
    if self.why is not None:
      oprot.writeFieldBegin('why', TType.STRING, 1)
      oprot.writeString(self.why)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.why is None:
      raise TProtocol.TProtocolException(message='Required field why is unset!')
    return


  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class AuthorizationException(TException):
  """
  invalid authorization request (user does not have access to keyspace)

  Attributes:
   - why
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'why', None, None, ), # 1
  )

  def __init__(self, why=None,):
    self.why = why

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.why = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('AuthorizationException')
    if self.why is not None:
      oprot.writeFieldBegin('why', TType.STRING, 1)
      oprot.writeString(self.why)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.why is None:
      raise TProtocol.TProtocolException(message='Required field why is unset!')
    return


  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class SchemaDisagreementException(TException):
  """
  NOTE: This up outdated exception left for backward compatibility reasons,
  no actual schema agreement validation is done starting from Cassandra 1.2

  schemas are not in agreement across all nodes
  """

  thrift_spec = (
  )

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('SchemaDisagreementException')
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __str__(self):
    return repr(self)

  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class ColumnParent(object):
  """
  ColumnParent is used when selecting groups of columns from the same ColumnFamily. In directory structure terms, imagine
  ColumnParent as ColumnPath + '/../'.

  See also <a href="cassandra.html#Struct_ColumnPath">ColumnPath</a>

  Attributes:
   - column_family
   - super_column
  """

  thrift_spec = (
    None, # 0
    None, # 1
    None, # 2
    (3, TType.STRING, 'column_family', None, None, ), # 3
    (4, TType.STRING, 'super_column', None, None, ), # 4
  )

  def __init__(self, column_family=None, super_column=None,):
    self.column_family = column_family
    self.super_column = super_column

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 3:
        if ftype == TType.STRING:
          self.column_family = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRING:
          self.super_column = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('ColumnParent')
    if self.column_family is not None:
      oprot.writeFieldBegin('column_family', TType.STRING, 3)
      oprot.writeString(self.column_family)
      oprot.writeFieldEnd()
    if self.super_column is not None:
      oprot.writeFieldBegin('super_column', TType.STRING, 4)
      oprot.writeString(self.super_column)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.column_family is None:
      raise TProtocol.TProtocolException(message='Required field column_family is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class ColumnPath(object):
  """
  The ColumnPath is the path to a single column in Cassandra. It might make sense to think of ColumnPath and
  ColumnParent in terms of a directory structure.

  ColumnPath is used to looking up a single column.

  @param column_family. The name of the CF of the column being looked up.
  @param super_column. The super column name.
  @param column. The column name.

  Attributes:
   - column_family
   - super_column
   - column
  """

  thrift_spec = (
    None, # 0
    None, # 1
    None, # 2
    (3, TType.STRING, 'column_family', None, None, ), # 3
    (4, TType.STRING, 'super_column', None, None, ), # 4
    (5, TType.STRING, 'column', None, None, ), # 5
  )

  def __init__(self, column_family=None, super_column=None, column=None,):
    self.column_family = column_family
    self.super_column = super_column
    self.column = column

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 3:
        if ftype == TType.STRING:
          self.column_family = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRING:
          self.super_column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.STRING:
          self.column = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('ColumnPath')
    if self.column_family is not None:
      oprot.writeFieldBegin('column_family', TType.STRING, 3)
      oprot.writeString(self.column_family)
      oprot.writeFieldEnd()
    if self.super_column is not None:
      oprot.writeFieldBegin('super_column', TType.STRING, 4)
      oprot.writeString(self.super_column)
      oprot.writeFieldEnd()
    if self.column is not None:
      oprot.writeFieldBegin('column', TType.STRING, 5)
      oprot.writeString(self.column)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.column_family is None:
      raise TProtocol.TProtocolException(message='Required field column_family is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class SliceRange(object):
  """
  A slice range is a structure that stores basic range, ordering and limit information for a query that will return
  multiple columns. It could be thought of as Cassandra's version of LIMIT and ORDER BY

  @param start. The column name to start the slice with. This attribute is not required, though there is no default value,
                and can be safely set to '', i.e., an empty byte array, to start with the first column name. Otherwise, it
                must a valid value under the rules of the Comparator defined for the given ColumnFamily.
  @param finish. The column name to stop the slice at. This attribute is not required, though there is no default value,
                 and can be safely set to an empty byte array to not stop until 'count' results are seen. Otherwise, it
                 must also be a valid value to the ColumnFamily Comparator.
  @param reversed. Whether the results should be ordered in reversed order. Similar to ORDER BY blah DESC in SQL.
  @param count. How many columns to return. Similar to LIMIT in SQL. May be arbitrarily large, but Thrift will
                materialize the whole result into memory before returning it to the client, so be aware that you may
                be better served by iterating through slices by passing the last value of one call in as the 'start'
                of the next instead of increasing 'count' arbitrarily large.

  Attributes:
   - start
   - finish
   - reversed
   - count
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'start', None, None, ), # 1
    (2, TType.STRING, 'finish', None, None, ), # 2
    (3, TType.BOOL, 'reversed', None, False, ), # 3
    (4, TType.I32, 'count', None, 100, ), # 4
  )

  def __init__(self, start=None, finish=None, reversed=thrift_spec[3][4], count=thrift_spec[4][4],):
    self.start = start
    self.finish = finish
    self.reversed = reversed
    self.count = count

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.start = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.finish = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.BOOL:
          self.reversed = iprot.readBool();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.count = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('SliceRange')
    if self.start is not None:
      oprot.writeFieldBegin('start', TType.STRING, 1)
      oprot.writeString(self.start)
      oprot.writeFieldEnd()
    if self.finish is not None:
      oprot.writeFieldBegin('finish', TType.STRING, 2)
      oprot.writeString(self.finish)
      oprot.writeFieldEnd()
    if self.reversed is not None:
      oprot.writeFieldBegin('reversed', TType.BOOL, 3)
      oprot.writeBool(self.reversed)
      oprot.writeFieldEnd()
    if self.count is not None:
      oprot.writeFieldBegin('count', TType.I32, 4)
      oprot.writeI32(self.count)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.start is None:
      raise TProtocol.TProtocolException(message='Required field start is unset!')
    if self.finish is None:
      raise TProtocol.TProtocolException(message='Required field finish is unset!')
    if self.reversed is None:
      raise TProtocol.TProtocolException(message='Required field reversed is unset!')
    if self.count is None:
      raise TProtocol.TProtocolException(message='Required field count is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class SlicePredicate(object):
  """
  A SlicePredicate is similar to a mathematic predicate (see http://en.wikipedia.org/wiki/Predicate_(mathematical_logic)),
  which is described as "a property that the elements of a set have in common."

  SlicePredicate's in Cassandra are described with either a list of column_names or a SliceRange.  If column_names is
  specified, slice_range is ignored.

  @param column_name. A list of column names to retrieve. This can be used similar to Memcached's "multi-get" feature
                      to fetch N known column names. For instance, if you know you wish to fetch columns 'Joe', 'Jack',
                      and 'Jim' you can pass those column names as a list to fetch all three at once.
  @param slice_range. A SliceRange describing how to range, order, and/or limit the slice.

  Attributes:
   - column_names
   - slice_range
  """

  thrift_spec = (
    None, # 0
    (1, TType.LIST, 'column_names', (TType.STRING,None), None, ), # 1
    (2, TType.STRUCT, 'slice_range', (SliceRange, SliceRange.thrift_spec), None, ), # 2
  )

  def __init__(self, column_names=None, slice_range=None,):
    self.column_names = column_names
    self.slice_range = slice_range

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.LIST:
          self.column_names = []
          (_etype17, _size14) = iprot.readListBegin()
          for _i18 in xrange(_size14):
            _elem19 = iprot.readString();
            self.column_names.append(_elem19)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.slice_range = SliceRange()
          self.slice_range.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('SlicePredicate')
    if self.column_names is not None:
      oprot.writeFieldBegin('column_names', TType.LIST, 1)
      oprot.writeListBegin(TType.STRING, len(self.column_names))
      for iter20 in self.column_names:
        oprot.writeString(iter20)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.slice_range is not None:
      oprot.writeFieldBegin('slice_range', TType.STRUCT, 2)
      self.slice_range.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class IndexExpression(object):
  """
  Attributes:
   - column_name
   - op
   - value
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'column_name', None, None, ), # 1
    (2, TType.I32, 'op', None, None, ), # 2
    (3, TType.STRING, 'value', None, None, ), # 3
  )

  def __init__(self, column_name=None, op=None, value=None,):
    self.column_name = column_name
    self.op = op
    self.value = value

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.column_name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.op = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.value = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('IndexExpression')
    if self.column_name is not None:
      oprot.writeFieldBegin('column_name', TType.STRING, 1)
      oprot.writeString(self.column_name)
      oprot.writeFieldEnd()
    if self.op is not None:
      oprot.writeFieldBegin('op', TType.I32, 2)
      oprot.writeI32(self.op)
      oprot.writeFieldEnd()
    if self.value is not None:
      oprot.writeFieldBegin('value', TType.STRING, 3)
      oprot.writeString(self.value)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.column_name is None:
      raise TProtocol.TProtocolException(message='Required field column_name is unset!')
    if self.op is None:
      raise TProtocol.TProtocolException(message='Required field op is unset!')
    if self.value is None:
      raise TProtocol.TProtocolException(message='Required field value is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class IndexClause(object):
  """
  @deprecated use a KeyRange with row_filter in get_range_slices instead

  Attributes:
   - expressions
   - start_key
   - count
  """

  thrift_spec = (
    None, # 0
    (1, TType.LIST, 'expressions', (TType.STRUCT,(IndexExpression, IndexExpression.thrift_spec)), None, ), # 1
    (2, TType.STRING, 'start_key', None, None, ), # 2
    (3, TType.I32, 'count', None, 100, ), # 3
  )

  def __init__(self, expressions=None, start_key=None, count=thrift_spec[3][4],):
    self.expressions = expressions
    self.start_key = start_key
    self.count = count

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.LIST:
          self.expressions = []
          (_etype24, _size21) = iprot.readListBegin()
          for _i25 in xrange(_size21):
            _elem26 = IndexExpression()
            _elem26.read(iprot)
            self.expressions.append(_elem26)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.start_key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I32:
          self.count = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('IndexClause')
    if self.expressions is not None:
      oprot.writeFieldBegin('expressions', TType.LIST, 1)
      oprot.writeListBegin(TType.STRUCT, len(self.expressions))
      for iter27 in self.expressions:
        iter27.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.start_key is not None:
      oprot.writeFieldBegin('start_key', TType.STRING, 2)
      oprot.writeString(self.start_key)
      oprot.writeFieldEnd()
    if self.count is not None:
      oprot.writeFieldBegin('count', TType.I32, 3)
      oprot.writeI32(self.count)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.expressions is None:
      raise TProtocol.TProtocolException(message='Required field expressions is unset!')
    if self.start_key is None:
      raise TProtocol.TProtocolException(message='Required field start_key is unset!')
    if self.count is None:
      raise TProtocol.TProtocolException(message='Required field count is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class KeyRange(object):
  """
  The semantics of start keys and tokens are slightly different.
  Keys are start-inclusive; tokens are start-exclusive.  Token
  ranges may also wrap -- that is, the end token may be less
  than the start one.  Thus, a range from keyX to keyX is a
  one-element range, but a range from tokenY to tokenY is the
  full ring.

  Attributes:
   - start_key
   - end_key
   - start_token
   - end_token
   - row_filter
   - count
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'start_key', None, None, ), # 1
    (2, TType.STRING, 'end_key', None, None, ), # 2
    (3, TType.STRING, 'start_token', None, None, ), # 3
    (4, TType.STRING, 'end_token', None, None, ), # 4
    (5, TType.I32, 'count', None, 100, ), # 5
    (6, TType.LIST, 'row_filter', (TType.STRUCT,(IndexExpression, IndexExpression.thrift_spec)), None, ), # 6
  )

  def __init__(self, start_key=None, end_key=None, start_token=None, end_token=None, row_filter=None, count=thrift_spec[5][4],):
    self.start_key = start_key
    self.end_key = end_key
    self.start_token = start_token
    self.end_token = end_token
    self.row_filter = row_filter
    self.count = count

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.start_key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.end_key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.start_token = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRING:
          self.end_token = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 6:
        if ftype == TType.LIST:
          self.row_filter = []
          (_etype31, _size28) = iprot.readListBegin()
          for _i32 in xrange(_size28):
            _elem33 = IndexExpression()
            _elem33.read(iprot)
            self.row_filter.append(_elem33)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.I32:
          self.count = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('KeyRange')
    if self.start_key is not None:
      oprot.writeFieldBegin('start_key', TType.STRING, 1)
      oprot.writeString(self.start_key)
      oprot.writeFieldEnd()
    if self.end_key is not None:
      oprot.writeFieldBegin('end_key', TType.STRING, 2)
      oprot.writeString(self.end_key)
      oprot.writeFieldEnd()
    if self.start_token is not None:
      oprot.writeFieldBegin('start_token', TType.STRING, 3)
      oprot.writeString(self.start_token)
      oprot.writeFieldEnd()
    if self.end_token is not None:
      oprot.writeFieldBegin('end_token', TType.STRING, 4)
      oprot.writeString(self.end_token)
      oprot.writeFieldEnd()
    if self.count is not None:
      oprot.writeFieldBegin('count', TType.I32, 5)
      oprot.writeI32(self.count)
      oprot.writeFieldEnd()
    if self.row_filter is not None:
      oprot.writeFieldBegin('row_filter', TType.LIST, 6)
      oprot.writeListBegin(TType.STRUCT, len(self.row_filter))
      for iter34 in self.row_filter:
        iter34.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.count is None:
      raise TProtocol.TProtocolException(message='Required field count is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class KeySlice(object):
  """
  A KeySlice is key followed by the data it maps to. A collection of KeySlice is returned by the get_range_slice operation.

  @param key. a row key
  @param columns. List of data represented by the key. Typically, the list is pared down to only the columns specified by
                  a SlicePredicate.

  Attributes:
   - key
   - columns
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'key', None, None, ), # 1
    (2, TType.LIST, 'columns', (TType.STRUCT,(ColumnOrSuperColumn, ColumnOrSuperColumn.thrift_spec)), None, ), # 2
  )

  def __init__(self, key=None, columns=None,):
    self.key = key
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.columns = []
          (_etype38, _size35) = iprot.readListBegin()
          for _i39 in xrange(_size35):
            _elem40 = ColumnOrSuperColumn()
            _elem40.read(iprot)
            self.columns.append(_elem40)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('KeySlice')
    if self.key is not None:
      oprot.writeFieldBegin('key', TType.STRING, 1)
      oprot.writeString(self.key)
      oprot.writeFieldEnd()
    if self.columns is not None:
      oprot.writeFieldBegin('columns', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.columns))
      for iter41 in self.columns:
        iter41.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.key is None:
      raise TProtocol.TProtocolException(message='Required field key is unset!')
    if self.columns is None:
      raise TProtocol.TProtocolException(message='Required field columns is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class KeyCount(object):
  """
  Attributes:
   - key
   - count
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'key', None, None, ), # 1
    (2, TType.I32, 'count', None, None, ), # 2
  )

  def __init__(self, key=None, count=None,):
    self.key = key
    self.count = count

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.count = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('KeyCount')
    if self.key is not None:
      oprot.writeFieldBegin('key', TType.STRING, 1)
      oprot.writeString(self.key)
      oprot.writeFieldEnd()
    if self.count is not None:
      oprot.writeFieldBegin('count', TType.I32, 2)
      oprot.writeI32(self.count)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.key is None:
      raise TProtocol.TProtocolException(message='Required field key is unset!')
    if self.count is None:
      raise TProtocol.TProtocolException(message='Required field count is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class Deletion(object):
  """
  Note that the timestamp is only optional in case of counter deletion.

  Attributes:
   - timestamp
   - super_column
   - predicate
  """

  thrift_spec = (
    None, # 0
    (1, TType.I64, 'timestamp', None, None, ), # 1
    (2, TType.STRING, 'super_column', None, None, ), # 2
    (3, TType.STRUCT, 'predicate', (SlicePredicate, SlicePredicate.thrift_spec), None, ), # 3
  )

  def __init__(self, timestamp=None, super_column=None, predicate=None,):
    self.timestamp = timestamp
    self.super_column = super_column
    self.predicate = predicate

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I64:
          self.timestamp = iprot.readI64();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.super_column = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRUCT:
          self.predicate = SlicePredicate()
          self.predicate.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('Deletion')
    if self.timestamp is not None:
      oprot.writeFieldBegin('timestamp', TType.I64, 1)
      oprot.writeI64(self.timestamp)
      oprot.writeFieldEnd()
    if self.super_column is not None:
      oprot.writeFieldBegin('super_column', TType.STRING, 2)
      oprot.writeString(self.super_column)
      oprot.writeFieldEnd()
    if self.predicate is not None:
      oprot.writeFieldBegin('predicate', TType.STRUCT, 3)
      self.predicate.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class Mutation(object):
  """
  A Mutation is either an insert (represented by filling column_or_supercolumn) or a deletion (represented by filling the deletion attribute).
  @param column_or_supercolumn. An insert to a column or supercolumn (possibly counter column or supercolumn)
  @param deletion. A deletion of a column or supercolumn

  Attributes:
   - column_or_supercolumn
   - deletion
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRUCT, 'column_or_supercolumn', (ColumnOrSuperColumn, ColumnOrSuperColumn.thrift_spec), None, ), # 1
    (2, TType.STRUCT, 'deletion', (Deletion, Deletion.thrift_spec), None, ), # 2
  )

  def __init__(self, column_or_supercolumn=None, deletion=None,):
    self.column_or_supercolumn = column_or_supercolumn
    self.deletion = deletion

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRUCT:
          self.column_or_supercolumn = ColumnOrSuperColumn()
          self.column_or_supercolumn.read(iprot)
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRUCT:
          self.deletion = Deletion()
          self.deletion.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('Mutation')
    if self.column_or_supercolumn is not None:
      oprot.writeFieldBegin('column_or_supercolumn', TType.STRUCT, 1)
      self.column_or_supercolumn.write(oprot)
      oprot.writeFieldEnd()
    if self.deletion is not None:
      oprot.writeFieldBegin('deletion', TType.STRUCT, 2)
      self.deletion.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class EndpointDetails(object):
  """
  Attributes:
   - host
   - datacenter
   - rack
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'host', None, None, ), # 1
    (2, TType.STRING, 'datacenter', None, None, ), # 2
    (3, TType.STRING, 'rack', None, None, ), # 3
  )

  def __init__(self, host=None, datacenter=None, rack=None,):
    self.host = host
    self.datacenter = datacenter
    self.rack = rack

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.host = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.datacenter = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.rack = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('EndpointDetails')
    if self.host is not None:
      oprot.writeFieldBegin('host', TType.STRING, 1)
      oprot.writeString(self.host)
      oprot.writeFieldEnd()
    if self.datacenter is not None:
      oprot.writeFieldBegin('datacenter', TType.STRING, 2)
      oprot.writeString(self.datacenter)
      oprot.writeFieldEnd()
    if self.rack is not None:
      oprot.writeFieldBegin('rack', TType.STRING, 3)
      oprot.writeString(self.rack)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class TokenRange(object):
  """
  A TokenRange describes part of the Cassandra ring, it is a mapping from a range to
  endpoints responsible for that range.
  @param start_token The first token in the range
  @param end_token The last token in the range
  @param endpoints The endpoints responsible for the range (listed by their configured listen_address)
  @param rpc_endpoints The endpoints responsible for the range (listed by their configured rpc_address)

  Attributes:
   - start_token
   - end_token
   - endpoints
   - rpc_endpoints
   - endpoint_details
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'start_token', None, None, ), # 1
    (2, TType.STRING, 'end_token', None, None, ), # 2
    (3, TType.LIST, 'endpoints', (TType.STRING,None), None, ), # 3
    (4, TType.LIST, 'rpc_endpoints', (TType.STRING,None), None, ), # 4
    (5, TType.LIST, 'endpoint_details', (TType.STRUCT,(EndpointDetails, EndpointDetails.thrift_spec)), None, ), # 5
  )

  def __init__(self, start_token=None, end_token=None, endpoints=None, rpc_endpoints=None, endpoint_details=None,):
    self.start_token = start_token
    self.end_token = end_token
    self.endpoints = endpoints
    self.rpc_endpoints = rpc_endpoints
    self.endpoint_details = endpoint_details

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.start_token = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.end_token = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.endpoints = []
          (_etype45, _size42) = iprot.readListBegin()
          for _i46 in xrange(_size42):
            _elem47 = iprot.readString();
            self.endpoints.append(_elem47)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.LIST:
          self.rpc_endpoints = []
          (_etype51, _size48) = iprot.readListBegin()
          for _i52 in xrange(_size48):
            _elem53 = iprot.readString();
            self.rpc_endpoints.append(_elem53)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.LIST:
          self.endpoint_details = []
          (_etype57, _size54) = iprot.readListBegin()
          for _i58 in xrange(_size54):
            _elem59 = EndpointDetails()
            _elem59.read(iprot)
            self.endpoint_details.append(_elem59)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('TokenRange')
    if self.start_token is not None:
      oprot.writeFieldBegin('start_token', TType.STRING, 1)
      oprot.writeString(self.start_token)
      oprot.writeFieldEnd()
    if self.end_token is not None:
      oprot.writeFieldBegin('end_token', TType.STRING, 2)
      oprot.writeString(self.end_token)
      oprot.writeFieldEnd()
    if self.endpoints is not None:
      oprot.writeFieldBegin('endpoints', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.endpoints))
      for iter60 in self.endpoints:
        oprot.writeString(iter60)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.rpc_endpoints is not None:
      oprot.writeFieldBegin('rpc_endpoints', TType.LIST, 4)
      oprot.writeListBegin(TType.STRING, len(self.rpc_endpoints))
      for iter61 in self.rpc_endpoints:
        oprot.writeString(iter61)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.endpoint_details is not None:
      oprot.writeFieldBegin('endpoint_details', TType.LIST, 5)
      oprot.writeListBegin(TType.STRUCT, len(self.endpoint_details))
      for iter62 in self.endpoint_details:
        iter62.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.start_token is None:
      raise TProtocol.TProtocolException(message='Required field start_token is unset!')
    if self.end_token is None:
      raise TProtocol.TProtocolException(message='Required field end_token is unset!')
    if self.endpoints is None:
      raise TProtocol.TProtocolException(message='Required field endpoints is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class AuthenticationRequest(object):
  """
  Authentication requests can contain any data, dependent on the IAuthenticator used

  Attributes:
   - credentials
  """

  thrift_spec = (
    None, # 0
    (1, TType.MAP, 'credentials', (TType.STRING,None,TType.STRING,None), None, ), # 1
  )

  def __init__(self, credentials=None,):
    self.credentials = credentials

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.MAP:
          self.credentials = {}
          (_ktype64, _vtype65, _size63 ) = iprot.readMapBegin() 
          for _i67 in xrange(_size63):
            _key68 = iprot.readString();
            _val69 = iprot.readString();
            self.credentials[_key68] = _val69
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('AuthenticationRequest')
    if self.credentials is not None:
      oprot.writeFieldBegin('credentials', TType.MAP, 1)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.credentials))
      for kiter70,viter71 in self.credentials.items():
        oprot.writeString(kiter70)
        oprot.writeString(viter71)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.credentials is None:
      raise TProtocol.TProtocolException(message='Required field credentials is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class ColumnDef(object):
  """
  Attributes:
   - name
   - validation_class
   - index_type
   - index_name
   - index_options
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'name', None, None, ), # 1
    (2, TType.STRING, 'validation_class', None, None, ), # 2
    (3, TType.I32, 'index_type', None, None, ), # 3
    (4, TType.STRING, 'index_name', None, None, ), # 4
    (5, TType.MAP, 'index_options', (TType.STRING,None,TType.STRING,None), None, ), # 5
  )

  def __init__(self, name=None, validation_class=None, index_type=None, index_name=None, index_options=None,):
    self.name = name
    self.validation_class = validation_class
    self.index_type = index_type
    self.index_name = index_name
    self.index_options = index_options

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.validation_class = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I32:
          self.index_type = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRING:
          self.index_name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.MAP:
          self.index_options = {}
          (_ktype73, _vtype74, _size72 ) = iprot.readMapBegin() 
          for _i76 in xrange(_size72):
            _key77 = iprot.readString();
            _val78 = iprot.readString();
            self.index_options[_key77] = _val78
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('ColumnDef')
    if self.name is not None:
      oprot.writeFieldBegin('name', TType.STRING, 1)
      oprot.writeString(self.name)
      oprot.writeFieldEnd()
    if self.validation_class is not None:
      oprot.writeFieldBegin('validation_class', TType.STRING, 2)
      oprot.writeString(self.validation_class)
      oprot.writeFieldEnd()
    if self.index_type is not None:
      oprot.writeFieldBegin('index_type', TType.I32, 3)
      oprot.writeI32(self.index_type)
      oprot.writeFieldEnd()
    if self.index_name is not None:
      oprot.writeFieldBegin('index_name', TType.STRING, 4)
      oprot.writeString(self.index_name)
      oprot.writeFieldEnd()
    if self.index_options is not None:
      oprot.writeFieldBegin('index_options', TType.MAP, 5)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.index_options))
      for kiter79,viter80 in self.index_options.items():
        oprot.writeString(kiter79)
        oprot.writeString(viter80)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.name is None:
      raise TProtocol.TProtocolException(message='Required field name is unset!')
    if self.validation_class is None:
      raise TProtocol.TProtocolException(message='Required field validation_class is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class CfDef(object):
  """
  Attributes:
   - keyspace
   - name
   - column_type
   - comparator_type
   - subcomparator_type
   - comment
   - read_repair_chance
   - column_metadata
   - gc_grace_seconds
   - default_validation_class
   - id
   - min_compaction_threshold
   - max_compaction_threshold
   - replicate_on_write
   - key_validation_class
   - key_alias
   - compaction_strategy
   - compaction_strategy_options
   - compression_options
   - bloom_filter_fp_chance
   - caching
   - dclocal_read_repair_chance
   - populate_io_cache_on_flush
   - row_cache_size: @deprecated
   - key_cache_size: @deprecated
   - row_cache_save_period_in_seconds: @deprecated
   - key_cache_save_period_in_seconds: @deprecated
   - memtable_flush_after_mins: @deprecated
   - memtable_throughput_in_mb: @deprecated
   - memtable_operations_in_millions: @deprecated
   - merge_shards_chance: @deprecated
   - row_cache_provider: @deprecated
   - row_cache_keys_to_save: @deprecated
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'keyspace', None, None, ), # 1
    (2, TType.STRING, 'name', None, None, ), # 2
    (3, TType.STRING, 'column_type', None, "Standard", ), # 3
    None, # 4
    (5, TType.STRING, 'comparator_type', None, "BytesType", ), # 5
    (6, TType.STRING, 'subcomparator_type', None, None, ), # 6
    None, # 7
    (8, TType.STRING, 'comment', None, None, ), # 8
    (9, TType.DOUBLE, 'row_cache_size', None, None, ), # 9
    None, # 10
    (11, TType.DOUBLE, 'key_cache_size', None, None, ), # 11
    (12, TType.DOUBLE, 'read_repair_chance', None, None, ), # 12
    (13, TType.LIST, 'column_metadata', (TType.STRUCT,(ColumnDef, ColumnDef.thrift_spec)), None, ), # 13
    (14, TType.I32, 'gc_grace_seconds', None, None, ), # 14
    (15, TType.STRING, 'default_validation_class', None, None, ), # 15
    (16, TType.I32, 'id', None, None, ), # 16
    (17, TType.I32, 'min_compaction_threshold', None, None, ), # 17
    (18, TType.I32, 'max_compaction_threshold', None, None, ), # 18
    (19, TType.I32, 'row_cache_save_period_in_seconds', None, None, ), # 19
    (20, TType.I32, 'key_cache_save_period_in_seconds', None, None, ), # 20
    (21, TType.I32, 'memtable_flush_after_mins', None, None, ), # 21
    (22, TType.I32, 'memtable_throughput_in_mb', None, None, ), # 22
    (23, TType.DOUBLE, 'memtable_operations_in_millions', None, None, ), # 23
    (24, TType.BOOL, 'replicate_on_write', None, None, ), # 24
    (25, TType.DOUBLE, 'merge_shards_chance', None, None, ), # 25
    (26, TType.STRING, 'key_validation_class', None, None, ), # 26
    (27, TType.STRING, 'row_cache_provider', None, None, ), # 27
    (28, TType.STRING, 'key_alias', None, None, ), # 28
    (29, TType.STRING, 'compaction_strategy', None, None, ), # 29
    (30, TType.MAP, 'compaction_strategy_options', (TType.STRING,None,TType.STRING,None), None, ), # 30
    (31, TType.I32, 'row_cache_keys_to_save', None, None, ), # 31
    (32, TType.MAP, 'compression_options', (TType.STRING,None,TType.STRING,None), None, ), # 32
    (33, TType.DOUBLE, 'bloom_filter_fp_chance', None, None, ), # 33
    (34, TType.STRING, 'caching', None, "keys_only", ), # 34
    None, # 35
    None, # 36
    (37, TType.DOUBLE, 'dclocal_read_repair_chance', None, 0, ), # 37
    (38, TType.BOOL, 'populate_io_cache_on_flush', None, None, ), # 38
  )

  def __init__(self, keyspace=None, name=None, column_type=thrift_spec[3][4], comparator_type=thrift_spec[5][4], subcomparator_type=None, comment=None, read_repair_chance=None, column_metadata=None, gc_grace_seconds=None, default_validation_class=None, id=None, min_compaction_threshold=None, max_compaction_threshold=None, replicate_on_write=None, key_validation_class=None, key_alias=None, compaction_strategy=None, compaction_strategy_options=None, compression_options=None, bloom_filter_fp_chance=None, caching=thrift_spec[34][4], dclocal_read_repair_chance=thrift_spec[37][4], populate_io_cache_on_flush=None, row_cache_size=None, key_cache_size=None, row_cache_save_period_in_seconds=None, key_cache_save_period_in_seconds=None, memtable_flush_after_mins=None, memtable_throughput_in_mb=None, memtable_operations_in_millions=None, merge_shards_chance=None, row_cache_provider=None, row_cache_keys_to_save=None,):
    self.keyspace = keyspace
    self.name = name
    self.column_type = column_type
    self.comparator_type = comparator_type
    self.subcomparator_type = subcomparator_type
    self.comment = comment
    self.read_repair_chance = read_repair_chance
    self.column_metadata = column_metadata
    self.gc_grace_seconds = gc_grace_seconds
    self.default_validation_class = default_validation_class
    self.id = id
    self.min_compaction_threshold = min_compaction_threshold
    self.max_compaction_threshold = max_compaction_threshold
    self.replicate_on_write = replicate_on_write
    self.key_validation_class = key_validation_class
    self.key_alias = key_alias
    self.compaction_strategy = compaction_strategy
    self.compaction_strategy_options = compaction_strategy_options
    self.compression_options = compression_options
    self.bloom_filter_fp_chance = bloom_filter_fp_chance
    self.caching = caching
    self.dclocal_read_repair_chance = dclocal_read_repair_chance
    self.populate_io_cache_on_flush = populate_io_cache_on_flush
    self.row_cache_size = row_cache_size
    self.key_cache_size = key_cache_size
    self.row_cache_save_period_in_seconds = row_cache_save_period_in_seconds
    self.key_cache_save_period_in_seconds = key_cache_save_period_in_seconds
    self.memtable_flush_after_mins = memtable_flush_after_mins
    self.memtable_throughput_in_mb = memtable_throughput_in_mb
    self.memtable_operations_in_millions = memtable_operations_in_millions
    self.merge_shards_chance = merge_shards_chance
    self.row_cache_provider = row_cache_provider
    self.row_cache_keys_to_save = row_cache_keys_to_save

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.keyspace = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.column_type = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.STRING:
          self.comparator_type = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 6:
        if ftype == TType.STRING:
          self.subcomparator_type = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 8:
        if ftype == TType.STRING:
          self.comment = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 12:
        if ftype == TType.DOUBLE:
          self.read_repair_chance = iprot.readDouble();
        else:
          iprot.skip(ftype)
      elif fid == 13:
        if ftype == TType.LIST:
          self.column_metadata = []
          (_etype84, _size81) = iprot.readListBegin()
          for _i85 in xrange(_size81):
            _elem86 = ColumnDef()
            _elem86.read(iprot)
            self.column_metadata.append(_elem86)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 14:
        if ftype == TType.I32:
          self.gc_grace_seconds = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 15:
        if ftype == TType.STRING:
          self.default_validation_class = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 16:
        if ftype == TType.I32:
          self.id = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 17:
        if ftype == TType.I32:
          self.min_compaction_threshold = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 18:
        if ftype == TType.I32:
          self.max_compaction_threshold = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 24:
        if ftype == TType.BOOL:
          self.replicate_on_write = iprot.readBool();
        else:
          iprot.skip(ftype)
      elif fid == 26:
        if ftype == TType.STRING:
          self.key_validation_class = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 28:
        if ftype == TType.STRING:
          self.key_alias = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 29:
        if ftype == TType.STRING:
          self.compaction_strategy = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 30:
        if ftype == TType.MAP:
          self.compaction_strategy_options = {}
          (_ktype88, _vtype89, _size87 ) = iprot.readMapBegin() 
          for _i91 in xrange(_size87):
            _key92 = iprot.readString();
            _val93 = iprot.readString();
            self.compaction_strategy_options[_key92] = _val93
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 32:
        if ftype == TType.MAP:
          self.compression_options = {}
          (_ktype95, _vtype96, _size94 ) = iprot.readMapBegin() 
          for _i98 in xrange(_size94):
            _key99 = iprot.readString();
            _val100 = iprot.readString();
            self.compression_options[_key99] = _val100
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 33:
        if ftype == TType.DOUBLE:
          self.bloom_filter_fp_chance = iprot.readDouble();
        else:
          iprot.skip(ftype)
      elif fid == 34:
        if ftype == TType.STRING:
          self.caching = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 37:
        if ftype == TType.DOUBLE:
          self.dclocal_read_repair_chance = iprot.readDouble();
        else:
          iprot.skip(ftype)
      elif fid == 38:
        if ftype == TType.BOOL:
          self.populate_io_cache_on_flush = iprot.readBool();
        else:
          iprot.skip(ftype)
      elif fid == 9:
        if ftype == TType.DOUBLE:
          self.row_cache_size = iprot.readDouble();
        else:
          iprot.skip(ftype)
      elif fid == 11:
        if ftype == TType.DOUBLE:
          self.key_cache_size = iprot.readDouble();
        else:
          iprot.skip(ftype)
      elif fid == 19:
        if ftype == TType.I32:
          self.row_cache_save_period_in_seconds = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 20:
        if ftype == TType.I32:
          self.key_cache_save_period_in_seconds = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 21:
        if ftype == TType.I32:
          self.memtable_flush_after_mins = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 22:
        if ftype == TType.I32:
          self.memtable_throughput_in_mb = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 23:
        if ftype == TType.DOUBLE:
          self.memtable_operations_in_millions = iprot.readDouble();
        else:
          iprot.skip(ftype)
      elif fid == 25:
        if ftype == TType.DOUBLE:
          self.merge_shards_chance = iprot.readDouble();
        else:
          iprot.skip(ftype)
      elif fid == 27:
        if ftype == TType.STRING:
          self.row_cache_provider = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 31:
        if ftype == TType.I32:
          self.row_cache_keys_to_save = iprot.readI32();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('CfDef')
    if self.keyspace is not None:
      oprot.writeFieldBegin('keyspace', TType.STRING, 1)
      oprot.writeString(self.keyspace)
      oprot.writeFieldEnd()
    if self.name is not None:
      oprot.writeFieldBegin('name', TType.STRING, 2)
      oprot.writeString(self.name)
      oprot.writeFieldEnd()
    if self.column_type is not None:
      oprot.writeFieldBegin('column_type', TType.STRING, 3)
      oprot.writeString(self.column_type)
      oprot.writeFieldEnd()
    if self.comparator_type is not None:
      oprot.writeFieldBegin('comparator_type', TType.STRING, 5)
      oprot.writeString(self.comparator_type)
      oprot.writeFieldEnd()
    if self.subcomparator_type is not None:
      oprot.writeFieldBegin('subcomparator_type', TType.STRING, 6)
      oprot.writeString(self.subcomparator_type)
      oprot.writeFieldEnd()
    if self.comment is not None:
      oprot.writeFieldBegin('comment', TType.STRING, 8)
      oprot.writeString(self.comment)
      oprot.writeFieldEnd()
    if self.row_cache_size is not None:
      oprot.writeFieldBegin('row_cache_size', TType.DOUBLE, 9)
      oprot.writeDouble(self.row_cache_size)
      oprot.writeFieldEnd()
    if self.key_cache_size is not None:
      oprot.writeFieldBegin('key_cache_size', TType.DOUBLE, 11)
      oprot.writeDouble(self.key_cache_size)
      oprot.writeFieldEnd()
    if self.read_repair_chance is not None:
      oprot.writeFieldBegin('read_repair_chance', TType.DOUBLE, 12)
      oprot.writeDouble(self.read_repair_chance)
      oprot.writeFieldEnd()
    if self.column_metadata is not None:
      oprot.writeFieldBegin('column_metadata', TType.LIST, 13)
      oprot.writeListBegin(TType.STRUCT, len(self.column_metadata))
      for iter101 in self.column_metadata:
        iter101.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.gc_grace_seconds is not None:
      oprot.writeFieldBegin('gc_grace_seconds', TType.I32, 14)
      oprot.writeI32(self.gc_grace_seconds)
      oprot.writeFieldEnd()
    if self.default_validation_class is not None:
      oprot.writeFieldBegin('default_validation_class', TType.STRING, 15)
      oprot.writeString(self.default_validation_class)
      oprot.writeFieldEnd()
    if self.id is not None:
      oprot.writeFieldBegin('id', TType.I32, 16)
      oprot.writeI32(self.id)
      oprot.writeFieldEnd()
    if self.min_compaction_threshold is not None:
      oprot.writeFieldBegin('min_compaction_threshold', TType.I32, 17)
      oprot.writeI32(self.min_compaction_threshold)
      oprot.writeFieldEnd()
    if self.max_compaction_threshold is not None:
      oprot.writeFieldBegin('max_compaction_threshold', TType.I32, 18)
      oprot.writeI32(self.max_compaction_threshold)
      oprot.writeFieldEnd()
    if self.row_cache_save_period_in_seconds is not None:
      oprot.writeFieldBegin('row_cache_save_period_in_seconds', TType.I32, 19)
      oprot.writeI32(self.row_cache_save_period_in_seconds)
      oprot.writeFieldEnd()
    if self.key_cache_save_period_in_seconds is not None:
      oprot.writeFieldBegin('key_cache_save_period_in_seconds', TType.I32, 20)
      oprot.writeI32(self.key_cache_save_period_in_seconds)
      oprot.writeFieldEnd()
    if self.memtable_flush_after_mins is not None:
      oprot.writeFieldBegin('memtable_flush_after_mins', TType.I32, 21)
      oprot.writeI32(self.memtable_flush_after_mins)
      oprot.writeFieldEnd()
    if self.memtable_throughput_in_mb is not None:
      oprot.writeFieldBegin('memtable_throughput_in_mb', TType.I32, 22)
      oprot.writeI32(self.memtable_throughput_in_mb)
      oprot.writeFieldEnd()
    if self.memtable_operations_in_millions is not None:
      oprot.writeFieldBegin('memtable_operations_in_millions', TType.DOUBLE, 23)
      oprot.writeDouble(self.memtable_operations_in_millions)
      oprot.writeFieldEnd()
    if self.replicate_on_write is not None:
      oprot.writeFieldBegin('replicate_on_write', TType.BOOL, 24)
      oprot.writeBool(self.replicate_on_write)
      oprot.writeFieldEnd()
    if self.merge_shards_chance is not None:
      oprot.writeFieldBegin('merge_shards_chance', TType.DOUBLE, 25)
      oprot.writeDouble(self.merge_shards_chance)
      oprot.writeFieldEnd()
    if self.key_validation_class is not None:
      oprot.writeFieldBegin('key_validation_class', TType.STRING, 26)
      oprot.writeString(self.key_validation_class)
      oprot.writeFieldEnd()
    if self.row_cache_provider is not None:
      oprot.writeFieldBegin('row_cache_provider', TType.STRING, 27)
      oprot.writeString(self.row_cache_provider)
      oprot.writeFieldEnd()
    if self.key_alias is not None:
      oprot.writeFieldBegin('key_alias', TType.STRING, 28)
      oprot.writeString(self.key_alias)
      oprot.writeFieldEnd()
    if self.compaction_strategy is not None:
      oprot.writeFieldBegin('compaction_strategy', TType.STRING, 29)
      oprot.writeString(self.compaction_strategy)
      oprot.writeFieldEnd()
    if self.compaction_strategy_options is not None:
      oprot.writeFieldBegin('compaction_strategy_options', TType.MAP, 30)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.compaction_strategy_options))
      for kiter102,viter103 in self.compaction_strategy_options.items():
        oprot.writeString(kiter102)
        oprot.writeString(viter103)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.row_cache_keys_to_save is not None:
      oprot.writeFieldBegin('row_cache_keys_to_save', TType.I32, 31)
      oprot.writeI32(self.row_cache_keys_to_save)
      oprot.writeFieldEnd()
    if self.compression_options is not None:
      oprot.writeFieldBegin('compression_options', TType.MAP, 32)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.compression_options))
      for kiter104,viter105 in self.compression_options.items():
        oprot.writeString(kiter104)
        oprot.writeString(viter105)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.bloom_filter_fp_chance is not None:
      oprot.writeFieldBegin('bloom_filter_fp_chance', TType.DOUBLE, 33)
      oprot.writeDouble(self.bloom_filter_fp_chance)
      oprot.writeFieldEnd()
    if self.caching is not None:
      oprot.writeFieldBegin('caching', TType.STRING, 34)
      oprot.writeString(self.caching)
      oprot.writeFieldEnd()
    if self.dclocal_read_repair_chance is not None:
      oprot.writeFieldBegin('dclocal_read_repair_chance', TType.DOUBLE, 37)
      oprot.writeDouble(self.dclocal_read_repair_chance)
      oprot.writeFieldEnd()
    if self.populate_io_cache_on_flush is not None:
      oprot.writeFieldBegin('populate_io_cache_on_flush', TType.BOOL, 38)
      oprot.writeBool(self.populate_io_cache_on_flush)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.keyspace is None:
      raise TProtocol.TProtocolException(message='Required field keyspace is unset!')
    if self.name is None:
      raise TProtocol.TProtocolException(message='Required field name is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class KsDef(object):
  """
  Attributes:
   - name
   - strategy_class
   - strategy_options
   - replication_factor: @deprecated ignored
   - cf_defs
   - durable_writes
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'name', None, None, ), # 1
    (2, TType.STRING, 'strategy_class', None, None, ), # 2
    (3, TType.MAP, 'strategy_options', (TType.STRING,None,TType.STRING,None), None, ), # 3
    (4, TType.I32, 'replication_factor', None, None, ), # 4
    (5, TType.LIST, 'cf_defs', (TType.STRUCT,(CfDef, CfDef.thrift_spec)), None, ), # 5
    (6, TType.BOOL, 'durable_writes', None, True, ), # 6
  )

  def __init__(self, name=None, strategy_class=None, strategy_options=None, replication_factor=None, cf_defs=None, durable_writes=thrift_spec[6][4],):
    self.name = name
    self.strategy_class = strategy_class
    self.strategy_options = strategy_options
    self.replication_factor = replication_factor
    self.cf_defs = cf_defs
    self.durable_writes = durable_writes

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.name = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.strategy_class = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.MAP:
          self.strategy_options = {}
          (_ktype107, _vtype108, _size106 ) = iprot.readMapBegin() 
          for _i110 in xrange(_size106):
            _key111 = iprot.readString();
            _val112 = iprot.readString();
            self.strategy_options[_key111] = _val112
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.I32:
          self.replication_factor = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 5:
        if ftype == TType.LIST:
          self.cf_defs = []
          (_etype116, _size113) = iprot.readListBegin()
          for _i117 in xrange(_size113):
            _elem118 = CfDef()
            _elem118.read(iprot)
            self.cf_defs.append(_elem118)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 6:
        if ftype == TType.BOOL:
          self.durable_writes = iprot.readBool();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('KsDef')
    if self.name is not None:
      oprot.writeFieldBegin('name', TType.STRING, 1)
      oprot.writeString(self.name)
      oprot.writeFieldEnd()
    if self.strategy_class is not None:
      oprot.writeFieldBegin('strategy_class', TType.STRING, 2)
      oprot.writeString(self.strategy_class)
      oprot.writeFieldEnd()
    if self.strategy_options is not None:
      oprot.writeFieldBegin('strategy_options', TType.MAP, 3)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.strategy_options))
      for kiter119,viter120 in self.strategy_options.items():
        oprot.writeString(kiter119)
        oprot.writeString(viter120)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.replication_factor is not None:
      oprot.writeFieldBegin('replication_factor', TType.I32, 4)
      oprot.writeI32(self.replication_factor)
      oprot.writeFieldEnd()
    if self.cf_defs is not None:
      oprot.writeFieldBegin('cf_defs', TType.LIST, 5)
      oprot.writeListBegin(TType.STRUCT, len(self.cf_defs))
      for iter121 in self.cf_defs:
        iter121.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.durable_writes is not None:
      oprot.writeFieldBegin('durable_writes', TType.BOOL, 6)
      oprot.writeBool(self.durable_writes)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.name is None:
      raise TProtocol.TProtocolException(message='Required field name is unset!')
    if self.strategy_class is None:
      raise TProtocol.TProtocolException(message='Required field strategy_class is unset!')
    if self.cf_defs is None:
      raise TProtocol.TProtocolException(message='Required field cf_defs is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class CqlRow(object):
  """
  Row returned from a CQL query

  Attributes:
   - key
   - columns
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'key', None, None, ), # 1
    (2, TType.LIST, 'columns', (TType.STRUCT,(Column, Column.thrift_spec)), None, ), # 2
  )

  def __init__(self, key=None, columns=None,):
    self.key = key
    self.columns = columns

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.key = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.columns = []
          (_etype125, _size122) = iprot.readListBegin()
          for _i126 in xrange(_size122):
            _elem127 = Column()
            _elem127.read(iprot)
            self.columns.append(_elem127)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('CqlRow')
    if self.key is not None:
      oprot.writeFieldBegin('key', TType.STRING, 1)
      oprot.writeString(self.key)
      oprot.writeFieldEnd()
    if self.columns is not None:
      oprot.writeFieldBegin('columns', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.columns))
      for iter128 in self.columns:
        iter128.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.key is None:
      raise TProtocol.TProtocolException(message='Required field key is unset!')
    if self.columns is None:
      raise TProtocol.TProtocolException(message='Required field columns is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class CqlMetadata(object):
  """
  Attributes:
   - name_types
   - value_types
   - default_name_type
   - default_value_type
  """

  thrift_spec = (
    None, # 0
    (1, TType.MAP, 'name_types', (TType.STRING,None,TType.STRING,None), None, ), # 1
    (2, TType.MAP, 'value_types', (TType.STRING,None,TType.STRING,None), None, ), # 2
    (3, TType.STRING, 'default_name_type', None, None, ), # 3
    (4, TType.STRING, 'default_value_type', None, None, ), # 4
  )

  def __init__(self, name_types=None, value_types=None, default_name_type=None, default_value_type=None,):
    self.name_types = name_types
    self.value_types = value_types
    self.default_name_type = default_name_type
    self.default_value_type = default_value_type

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.MAP:
          self.name_types = {}
          (_ktype130, _vtype131, _size129 ) = iprot.readMapBegin() 
          for _i133 in xrange(_size129):
            _key134 = iprot.readString();
            _val135 = iprot.readString();
            self.name_types[_key134] = _val135
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.MAP:
          self.value_types = {}
          (_ktype137, _vtype138, _size136 ) = iprot.readMapBegin() 
          for _i140 in xrange(_size136):
            _key141 = iprot.readString();
            _val142 = iprot.readString();
            self.value_types[_key141] = _val142
          iprot.readMapEnd()
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.STRING:
          self.default_name_type = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRING:
          self.default_value_type = iprot.readString();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('CqlMetadata')
    if self.name_types is not None:
      oprot.writeFieldBegin('name_types', TType.MAP, 1)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.name_types))
      for kiter143,viter144 in self.name_types.items():
        oprot.writeString(kiter143)
        oprot.writeString(viter144)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.value_types is not None:
      oprot.writeFieldBegin('value_types', TType.MAP, 2)
      oprot.writeMapBegin(TType.STRING, TType.STRING, len(self.value_types))
      for kiter145,viter146 in self.value_types.items():
        oprot.writeString(kiter145)
        oprot.writeString(viter146)
      oprot.writeMapEnd()
      oprot.writeFieldEnd()
    if self.default_name_type is not None:
      oprot.writeFieldBegin('default_name_type', TType.STRING, 3)
      oprot.writeString(self.default_name_type)
      oprot.writeFieldEnd()
    if self.default_value_type is not None:
      oprot.writeFieldBegin('default_value_type', TType.STRING, 4)
      oprot.writeString(self.default_value_type)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.name_types is None:
      raise TProtocol.TProtocolException(message='Required field name_types is unset!')
    if self.value_types is None:
      raise TProtocol.TProtocolException(message='Required field value_types is unset!')
    if self.default_name_type is None:
      raise TProtocol.TProtocolException(message='Required field default_name_type is unset!')
    if self.default_value_type is None:
      raise TProtocol.TProtocolException(message='Required field default_value_type is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class CqlResult(object):
  """
  Attributes:
   - type
   - rows
   - num
   - schema
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'type', None, None, ), # 1
    (2, TType.LIST, 'rows', (TType.STRUCT,(CqlRow, CqlRow.thrift_spec)), None, ), # 2
    (3, TType.I32, 'num', None, None, ), # 3
    (4, TType.STRUCT, 'schema', (CqlMetadata, CqlMetadata.thrift_spec), None, ), # 4
  )

  def __init__(self, type=None, rows=None, num=None, schema=None,):
    self.type = type
    self.rows = rows
    self.num = num
    self.schema = schema

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.type = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.LIST:
          self.rows = []
          (_etype150, _size147) = iprot.readListBegin()
          for _i151 in xrange(_size147):
            _elem152 = CqlRow()
            _elem152.read(iprot)
            self.rows.append(_elem152)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I32:
          self.num = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.STRUCT:
          self.schema = CqlMetadata()
          self.schema.read(iprot)
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('CqlResult')
    if self.type is not None:
      oprot.writeFieldBegin('type', TType.I32, 1)
      oprot.writeI32(self.type)
      oprot.writeFieldEnd()
    if self.rows is not None:
      oprot.writeFieldBegin('rows', TType.LIST, 2)
      oprot.writeListBegin(TType.STRUCT, len(self.rows))
      for iter153 in self.rows:
        iter153.write(oprot)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.num is not None:
      oprot.writeFieldBegin('num', TType.I32, 3)
      oprot.writeI32(self.num)
      oprot.writeFieldEnd()
    if self.schema is not None:
      oprot.writeFieldBegin('schema', TType.STRUCT, 4)
      self.schema.write(oprot)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.type is None:
      raise TProtocol.TProtocolException(message='Required field type is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class CqlPreparedResult(object):
  """
  Attributes:
   - itemId
   - count
   - variable_types
   - variable_names
  """

  thrift_spec = (
    None, # 0
    (1, TType.I32, 'itemId', None, None, ), # 1
    (2, TType.I32, 'count', None, None, ), # 2
    (3, TType.LIST, 'variable_types', (TType.STRING,None), None, ), # 3
    (4, TType.LIST, 'variable_names', (TType.STRING,None), None, ), # 4
  )

  def __init__(self, itemId=None, count=None, variable_types=None, variable_names=None,):
    self.itemId = itemId
    self.count = count
    self.variable_types = variable_types
    self.variable_names = variable_names

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.I32:
          self.itemId = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.I32:
          self.count = iprot.readI32();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.LIST:
          self.variable_types = []
          (_etype157, _size154) = iprot.readListBegin()
          for _i158 in xrange(_size154):
            _elem159 = iprot.readString();
            self.variable_types.append(_elem159)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      elif fid == 4:
        if ftype == TType.LIST:
          self.variable_names = []
          (_etype163, _size160) = iprot.readListBegin()
          for _i164 in xrange(_size160):
            _elem165 = iprot.readString();
            self.variable_names.append(_elem165)
          iprot.readListEnd()
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('CqlPreparedResult')
    if self.itemId is not None:
      oprot.writeFieldBegin('itemId', TType.I32, 1)
      oprot.writeI32(self.itemId)
      oprot.writeFieldEnd()
    if self.count is not None:
      oprot.writeFieldBegin('count', TType.I32, 2)
      oprot.writeI32(self.count)
      oprot.writeFieldEnd()
    if self.variable_types is not None:
      oprot.writeFieldBegin('variable_types', TType.LIST, 3)
      oprot.writeListBegin(TType.STRING, len(self.variable_types))
      for iter166 in self.variable_types:
        oprot.writeString(iter166)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    if self.variable_names is not None:
      oprot.writeFieldBegin('variable_names', TType.LIST, 4)
      oprot.writeListBegin(TType.STRING, len(self.variable_names))
      for iter167 in self.variable_names:
        oprot.writeString(iter167)
      oprot.writeListEnd()
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.itemId is None:
      raise TProtocol.TProtocolException(message='Required field itemId is unset!')
    if self.count is None:
      raise TProtocol.TProtocolException(message='Required field count is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

class CfSplit(object):
  """
  Represents input splits used by hadoop ColumnFamilyRecordReaders

  Attributes:
   - start_token
   - end_token
   - row_count
  """

  thrift_spec = (
    None, # 0
    (1, TType.STRING, 'start_token', None, None, ), # 1
    (2, TType.STRING, 'end_token', None, None, ), # 2
    (3, TType.I64, 'row_count', None, None, ), # 3
  )

  def __init__(self, start_token=None, end_token=None, row_count=None,):
    self.start_token = start_token
    self.end_token = end_token
    self.row_count = row_count

  def read(self, iprot):
    if iprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and isinstance(iprot.trans, TTransport.CReadableTransport) and self.thrift_spec is not None and fastbinary is not None:
      fastbinary.decode_binary(self, iprot.trans, (self.__class__, self.thrift_spec))
      return
    iprot.readStructBegin()
    while True:
      (fname, ftype, fid) = iprot.readFieldBegin()
      if ftype == TType.STOP:
        break
      if fid == 1:
        if ftype == TType.STRING:
          self.start_token = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 2:
        if ftype == TType.STRING:
          self.end_token = iprot.readString();
        else:
          iprot.skip(ftype)
      elif fid == 3:
        if ftype == TType.I64:
          self.row_count = iprot.readI64();
        else:
          iprot.skip(ftype)
      else:
        iprot.skip(ftype)
      iprot.readFieldEnd()
    iprot.readStructEnd()

  def write(self, oprot):
    if oprot.__class__ == TBinaryProtocol.TBinaryProtocolAccelerated and self.thrift_spec is not None and fastbinary is not None:
      oprot.trans.write(fastbinary.encode_binary(self, (self.__class__, self.thrift_spec)))
      return
    oprot.writeStructBegin('CfSplit')
    if self.start_token is not None:
      oprot.writeFieldBegin('start_token', TType.STRING, 1)
      oprot.writeString(self.start_token)
      oprot.writeFieldEnd()
    if self.end_token is not None:
      oprot.writeFieldBegin('end_token', TType.STRING, 2)
      oprot.writeString(self.end_token)
      oprot.writeFieldEnd()
    if self.row_count is not None:
      oprot.writeFieldBegin('row_count', TType.I64, 3)
      oprot.writeI64(self.row_count)
      oprot.writeFieldEnd()
    oprot.writeFieldStop()
    oprot.writeStructEnd()

  def validate(self):
    if self.start_token is None:
      raise TProtocol.TProtocolException(message='Required field start_token is unset!')
    if self.end_token is None:
      raise TProtocol.TProtocolException(message='Required field end_token is unset!')
    if self.row_count is None:
      raise TProtocol.TProtocolException(message='Required field row_count is unset!')
    return


  def __repr__(self):
    L = ['%s=%r' % (key, value)
      for key, value in self.__dict__.iteritems()]
    return '%s(%s)' % (self.__class__.__name__, ', '.join(L))

  def __eq__(self, other):
    return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

  def __ne__(self, other):
    return not (self == other)

########NEW FILE########
__FILENAME__ = columnfamily
"""
Provides an abstraction of Cassandra's data model to allow for easy
manipulation of data inside Cassandra.

.. seealso:: :mod:`pycassa.columnfamilymap`
"""

import time
import struct
from UserDict import DictMixin

from pycassa.cassandra.ttypes import Column, ColumnOrSuperColumn,\
    ColumnParent, ColumnPath, ConsistencyLevel, NotFoundException,\
    SlicePredicate, SliceRange, SuperColumn, KeyRange,\
    IndexExpression, IndexClause, CounterColumn, Mutation
import pycassa.marshal as marshal
import pycassa.types as types
from pycassa.batch import CfMutator
try:
    from collections import OrderedDict
except ImportError:
    from pycassa.util import OrderedDict # NOQA

__all__ = ['gm_timestamp', 'ColumnFamily', 'PooledColumnFamily']

class ColumnValidatorDict(DictMixin):

    def __init__(self, other_dict={}, name_packer=None, name_unpacker=None):
        self.name_packer = name_packer or (lambda x: x)
        self.name_unpacker = name_unpacker or (lambda x: x)

        self.type_map = {}
        self.packers = {}
        self.unpackers = {}
        for item, value in other_dict.items():
            packed_item = self.name_packer(item)
            self[packed_item] = value

    def __getitem__(self, item):
        packed_item = self.name_packer(item)
        return self.type_map[packed_item]

    def __setitem__(self, item, value):
        packed_item = self.name_packer(item)
        if isinstance(value, types.CassandraType):
            self.type_map[packed_item] = value
            self.packers[packed_item] = value.pack
            self.unpackers[packed_item] = value.unpack
        else:
            self.type_map[packed_item] = marshal.extract_type_name(value)
            self.packers[packed_item] = marshal.packer_for(value)
            self.unpackers[packed_item] = marshal.unpacker_for(value)

    def __delitem__(self, item):
        packed_item = self.name_packer(item)
        del self.type_map[packed_item]
        del self.packers[packed_item]
        del self.unpackers[packed_item]

    def keys(self):
        return map(self.name_unpacker, self.type_map.keys())

def gm_timestamp():
    """ Returns the number of microseconds since the Unix Epoch. """
    return int(time.time() * 1e6)

class ColumnFamily(object):
    """
    An abstraction of a Cassandra column family or super column family.
    Operations on this, such as :meth:`get` or :meth:`insert` will get data from or
    insert data into the corresponding Cassandra column family.
    """

    buffer_size = 1024
    """ When calling :meth:`get_range()` or :meth:`get_indexed_slices()`,
    the intermediate results need to be buffered if we are fetching many
    rows, otherwise performance may suffer and the Cassandra server may
    overallocate memory and fail. This is the size of that buffer in number
    of rows. The default is 1024. """

    column_buffer_size = 1024
    """ The number of columns fetched at once for :meth:`xget()` """

    read_consistency_level = ConsistencyLevel.ONE
    """ The default consistency level for every read operation, such as
    :meth:`get` or :meth:`get_range`. This may be overridden per-operation. This should be
    an instance of :class:`~pycassa.cassandra.ttypes.ConsistencyLevel`.
    The default level is ``ONE``. """

    write_consistency_level = ConsistencyLevel.ONE
    """ The default consistency level for every write operation, such as
    :meth:`insert` or :meth:`remove`. This may be overridden per-operation. This should be
    an instance of :class:`.~pycassa.cassandra.ttypes.ConsistencyLevel`.
    The default level is ``ONE``. """

    timestamp = gm_timestamp
    """ Each :meth:`insert()` or :meth:`remove` sends a timestamp with every
    column. This attribute is a function that is used to get
    this timestamp when needed.  The default function is :meth:`gm_timestamp()`."""

    dict_class = OrderedDict
    """ Results are returned as dictionaries. By default, python 2.7's
    :class:`collections.OrderedDict` is used if available, otherwise
    :class:`~pycassa.util.OrderedDict` is used so that order is maintained.
    A different class, such as :class:`dict`, may be instead by used setting
    this. """

    autopack_names = True
    """ Controls whether column names are automatically converted to or from
    their natural type to the binary string format that Cassandra uses.
    The data type used is controlled by :attr:`column_name_class` for
    column names and :attr:`super_column_name_class` for super column names.
    By default, this is :const:`True`. """

    autopack_values = True
    """ Whether column values are automatically converted to or from
    their natural type to the binary string format that Cassandra uses.
    The data type used is controlled by :attr:`default_validation_class`
    and :attr:`column_validators`.
    By default, this is :const:`True`. """

    autopack_keys = True
    """ Whether row keys are automatically converted to or from
    their natural type to the binary string format that Cassandra uses.
    The data type used is controlled by :attr:`key_validation_class`.
    By default, this is :const:`True`.
    """

    retry_counter_mutations = False
    """ Whether to retry failed counter mutations. Counter mutations are
    not idempotent so retrying could result in double counting.
    By default, this is :const:`False`.

    .. versionadded:: 1.5.0

    """

    def _set_column_name_class(self, t):
        if isinstance(t, types.CassandraType):
            self._column_name_class = t
            self._name_packer = t.pack
            self._name_unpacker = t.unpack
        else:
            self._column_name_class = marshal.extract_type_name(t)
            self._name_packer = marshal.packer_for(t)
            self._name_unpacker = marshal.unpacker_for(t)

    def _get_column_name_class(self):
        return self._column_name_class

    column_name_class = property(_get_column_name_class, _set_column_name_class)
    """ The data type of column names, which pycassa will use
    to determine how to pack and unpack them.

    This is set automatically by inspecting the column family's
    ``comparator_type``, but it may also be set manually if you want
    autopacking behavior without setting a ``comparator_type``. Options
    include an instance of any class in :mod:`pycassa.types`, such as ``LongType()``.
    """

    def _set_super_column_name_class(self, t):
        if isinstance(t, types.CassandraType):
            self._super_column_name_class = t
            self._super_name_packer = t.pack
            self._super_name_unpacker = t.unpack
        else:
            self._super_column_name_class = marshal.extract_type_name(t)
            self._super_name_packer = marshal.packer_for(t)
            self._super_name_unpacker = marshal.unpacker_for(t)

    def _get_super_column_name_class(self):
        return self._super_column_name_class

    super_column_name_class = property(_get_super_column_name_class,
                                       _set_super_column_name_class)
    """ Like :attr:`column_name_class`, but for
    super column names. """

    def _set_default_validation_class(self, t):
        if isinstance(t, types.CassandraType):
            self._default_validation_class = t
            self._default_value_packer = t.pack
            self._default_value_unpacker = t.unpack
            self._have_counters = isinstance(t, types.CounterColumnType)
        else:
            self._default_validation_class = marshal.extract_type_name(t)
            self._default_value_packer = marshal.packer_for(t)
            self._default_value_unpacker = marshal.unpacker_for(t)
            self._have_counters = self._default_validation_class == "CounterColumnType"

        if not self.super:
            if self._have_counters:
                def _make_counter_cosc(name, value, timestamp, ttl):
                    return ColumnOrSuperColumn(counter_column=CounterColumn(name, value))
                self._make_cosc = _make_counter_cosc
            else:
                def _make_normal_cosc(name, value, timestamp, ttl):
                    return ColumnOrSuperColumn(Column(name, value, timestamp, ttl))
                self._make_cosc = _make_normal_cosc
        else:
            if self._have_counters:
                def _make_column(name, value, timestamp, ttl):
                    return CounterColumn(name, value)
                self._make_column = _make_column

                def _make_counter_super_cosc(scol_name, subcols):
                    return ColumnOrSuperColumn(counter_super_column=(SuperColumn(scol_name, subcols)))
                self._make_cosc = _make_counter_super_cosc
            else:
                self._make_column = Column

                def _make_super_cosc(scol_name, subcols):
                    return ColumnOrSuperColumn(super_column=(SuperColumn(scol_name, subcols)))
                self._make_cosc = _make_super_cosc

    def _get_default_validation_class(self):
        return self._default_validation_class

    default_validation_class = property(_get_default_validation_class,
                                        _set_default_validation_class)
    """ The default data type of column values, which pycassa
    will use to determine how to pack and unpack them.

    This is set automatically by inspecting the column family's
    ``default_validation_class``, but it may also be set manually if you want
    autopacking behavior without setting a ``default_validation_class``. Options
    include an instance of any class in :mod:`pycassa.types`, such as ``LongType()``.
    """

    @property
    def _allow_retries(self):
        return not self._have_counters or self.retry_counter_mutations

    def _set_column_validators(self, other_dict):
        self._column_validators = ColumnValidatorDict(other_dict, self._pack_name, self._unpack_name)

    def _get_column_validators(self):
        return self._column_validators

    column_validators = property(_get_column_validators, _set_column_validators)
    """ Like :attr:`default_validation_class`, but is a
    :class:`dict` mapping individual columns to types. """

    def _set_key_validation_class(self, t):
        if isinstance(t, types.CassandraType):
            self._key_validation_class = t
            self._key_packer = t.pack
            self._key_unpacker = t.unpack
        else:
            self._key_validation_class = marshal.extract_type_name(t)
            self._key_packer = marshal.packer_for(t)
            self._key_unpacker = marshal.unpacker_for(t)

    def _get_key_validation_class(self):
        return self._key_validation_class

    key_validation_class = property(_get_key_validation_class,
                                    _set_key_validation_class)
    """ The data type of row keys, which pycassa will use
    to determine how to pack and unpack them.

    This is set automatically by inspecting the column family's
    ``key_validation_class`` (which only exists in Cassandra 0.8 or greater),
    but may be set manually if you want the autopacking behavior without
    setting a ``key_validation_class`` or if you are using Cassandra 0.7.
    Options include an instance of any class in :mod:`pycassa.types`,
    such as ``LongType()``.
    """

    def __init__(self, pool, column_family, **kwargs):
        """
        `pool` is a :class:`~pycassa.pool.ConnectionPool` that the column
        family will use for all operations. A connection is drawn from the
        pool before each operations and is returned afterwards.

        `column_family` should be the name of the column family that you
        want to use in Cassandra. Note that the keyspace to be used is
        determined by the pool.
        """

        self.pool = pool
        self.column_family = column_family
        self.timestamp = gm_timestamp
        self.load_schema()

        recognized_kwargs = ("buffer_size", "read_consistency_level",
                             "write_consistency_level", "timestamp",
                             "dict_class", "buffer_size", "autopack_names",
                             "autopack_values", "autopack_keys",
                             "retry_counter_mutations")
        for k, v in kwargs.iteritems():
            if k in recognized_kwargs:
                setattr(self, k, v)
            else:
                raise TypeError(
                        "ColumnFamily.__init__() got an unexpected keyword "
                        "argument '%s'" % (k,))

    def load_schema(self):
        """
        Loads the schema definition for this column family from
        Cassandra and updates comparator and validation classes if
        neccessary.
        """
        ksdef = self.pool.execute('get_keyspace_description',
                                  use_dict_for_col_metadata=True)
        try:
            self._cfdef = ksdef[self.column_family]
        except KeyError:
            nfe = NotFoundException()
            nfe.why = 'Column family %s not found.' % self.column_family
            raise nfe

        self.super = self._cfdef.column_type == 'Super'
        self._load_comparator_classes()
        self._load_validation_classes()
        self._load_key_class()

    def _load_comparator_classes(self):
        if not self.super:
            self.column_name_class = self._cfdef.comparator_type
            self.super_column_name_class = None
        else:
            self.column_name_class = self._cfdef.subcomparator_type
            self.super_column_name_class = self._cfdef.comparator_type

    def _load_validation_classes(self):
        self.default_validation_class = self._cfdef.default_validation_class
        self.column_validators = {}
        for name, coldef in self._cfdef.column_metadata.items():
            unpacked_name = self._unpack_name(name)
            self.column_validators[unpacked_name] = coldef.validation_class

    def _load_key_class(self):
        if hasattr(self._cfdef, "key_validation_class"):
            self.key_validation_class = self._cfdef.key_validation_class
        else:
            self.key_validation_class = 'BytesType'

    def _col_to_dict(self, column, include_timestamp, include_ttl):
        value = self._unpack_value(column.value, column.name)
        if include_timestamp and include_ttl:
            return (value, column.timestamp, column.ttl)
        elif include_timestamp:
            return (value, column.timestamp)
        elif include_ttl:
            return (value, column.ttl)
        else:
            return value

    def _scol_to_dict(self, super_column, include_timestamp, include_ttl):
        ret = self.dict_class()
        for column in super_column.columns:
            ret[self._unpack_name(column.name)] = self._col_to_dict(column, include_timestamp, include_ttl)
        return ret

    def _scounter_to_dict(self, counter_super_column):
        ret = self.dict_class()
        for counter in counter_super_column.columns:
            ret[self._unpack_name(counter.name)] = counter.value
        return ret

    def _cosc_to_dict(self, list_col_or_super, include_timestamp, include_ttl):
        ret = self.dict_class()
        for cosc in list_col_or_super:
            if cosc.column:
                col = cosc.column
                ret[self._unpack_name(col.name)] = self._col_to_dict(col, include_timestamp, include_ttl)
            elif cosc.counter_column:
                counter = cosc.counter_column
                ret[self._unpack_name(counter.name)] = counter.value
            elif cosc.super_column:
                scol = cosc.super_column
                ret[self._unpack_name(scol.name, True)] = self._scol_to_dict(scol, include_timestamp, include_ttl)
            else:
                scounter = cosc.counter_super_column
                ret[self._unpack_name(scounter.name, True)] = self._scounter_to_dict(scounter)
        return ret

    def _column_path(self, super_column=None, column=None):
        return ColumnPath(self.column_family,
                          self._pack_name(super_column, is_supercol_name=True),
                          self._pack_name(column, False))

    def _column_parent(self, super_column=None):
        return ColumnParent(column_family=self.column_family,
                            super_column=self._pack_name(super_column, is_supercol_name=True))

    def _slice_predicate(self, columns, column_start, column_finish,
                         column_reversed, column_count, super_column=None, pack=True):
        is_supercol_name = self.super and super_column is None
        if columns is not None:
            packed_cols = []
            for col in columns:
                packed_cols.append(self._pack_name(col, is_supercol_name=is_supercol_name))
            return SlicePredicate(column_names=packed_cols)
        else:
            if column_start != '' and pack:
                column_start = self._pack_name(column_start,
                                               is_supercol_name=is_supercol_name,
                                               slice_start=(not column_reversed))
            if column_finish != '' and pack:
                column_finish = self._pack_name(column_finish,
                                                is_supercol_name=is_supercol_name,
                                                slice_start=column_reversed)

            sr = SliceRange(start=column_start, finish=column_finish,
                            reversed=column_reversed, count=column_count)
            return SlicePredicate(slice_range=sr)

    def _pack_name(self, value, is_supercol_name=False, slice_start=None):
        if value is None:
            return

        if not self.autopack_names:
            if not isinstance(value, basestring):
                raise TypeError("A str or unicode column name was expected, " +
                                "but %s was received instead (%s)"
                                % (value.__class__.__name__, str(value)))
            return value

        try:
            if is_supercol_name:
                return self._super_name_packer(value, slice_start)
            else:
                return self._name_packer(value, slice_start)
        except struct.error:
            if is_supercol_name:
                d_type = self.super_column_name_class
            else:
                d_type = self.column_name_class

            raise TypeError("%s is not a compatible type for %s" %
                            (value.__class__.__name__, d_type))

    def _unpack_name(self, b, is_supercol_name=False):
        if not self.autopack_names:
            return b

        try:
            if is_supercol_name:
                return self._super_name_unpacker(b)
            else:
                return self._name_unpacker(b)
        except struct.error:
            if is_supercol_name:
                d_type = self.super_column_name_class
            else:
                d_type = self.column_name_class
            raise TypeError("%s cannot be converted to a type matching %s" %
                            (b, d_type))

    def _pack_value(self, value, col_name):
        if value is None:
            return

        if not self.autopack_values:
            if not isinstance(value, basestring):
                raise TypeError("A str or unicode column value was expected for " +
                                "column '%s', but %s was received instead (%s)"
                                % (str(col_name), value.__class__.__name__, str(value)))
            return value

        packed_col_name = self._pack_name(col_name, False)
        packer = self._column_validators.packers.get(packed_col_name, self._default_value_packer)
        try:
            return packer(value)
        except struct.error:
            d_type = self.column_validators.get(col_name, self._default_validation_class)
            raise TypeError("%s is not a compatible type for %s" %
                            (value.__class__.__name__, d_type))

    def _unpack_value(self, value, col_name):
        if not self.autopack_values:
            return value
        unpacker = self._column_validators.unpackers.get(col_name, self._default_value_unpacker)
        try:
            return unpacker(value)
        except struct.error:
            d_type = self.column_validators.get(col_name, self.default_validation_class)
            raise TypeError("%s cannot be converted to a type matching %s" %
                            (value, d_type))

    def _pack_key(self, key):
        if not self.autopack_keys or key == '':
            return key
        try:
            return self._key_packer(key)
        except struct.error:
            d_type = self.key_validation_class
            raise TypeError("%s is not a compatible type for %s" %
                            (key.__class__.__name__, d_type))

    def _unpack_key(self, b):
        if not self.autopack_keys:
            return b
        try:
            return self._key_unpacker(b)
        except struct.error:
            d_type = self.key_validation_class
            raise TypeError("%s cannot be converted to a type matching %s" %
                            (b, d_type))

    def _make_mutation_list(self, columns, timestamp, ttl):
        _pack_name = self._pack_name
        _pack_value = self._pack_value
        if not self.super:
            return map(lambda (c, v): Mutation(self._make_cosc(_pack_name(c), _pack_value(v, c), timestamp, ttl)),
                       columns.iteritems())
        else:
            mut_list = []
            for super_col, subcs in columns.items():
                subcols = map(lambda (c, v): self._make_column(_pack_name(c), _pack_value(v, c), timestamp, ttl),
                              subcs.iteritems())
                mut_list.append(Mutation(self._make_cosc(_pack_name(super_col, True), subcols)))
            return mut_list

    def xget(self, key, column_start="", column_finish="", column_reversed=False,
             column_count=None, include_timestamp=False, read_consistency_level=None,
             buffer_size=None, include_ttl=False):
        """
        Like :meth:`get()`, but creates a generator that pages over the columns
        automatically.

        The number of columns fetched at once can be controlled with the
        `buffer_size` parameter. The default is :attr:`column_buffer_size`.

        The generator returns `(name, value)` tuples.
        """

        packed_key = self._pack_key(key)
        cp = self._column_parent(None)
        rcl = read_consistency_level or self.read_consistency_level

        if buffer_size is None:
            buffer_size = self.column_buffer_size

        count = i = 0
        last_name = finish = ""
        if column_start != "":
            last_name = self._pack_name(column_start,
                    is_supercol_name=self.super,
                    slice_start=(not column_reversed))
        if column_finish != "":
            finish = self._pack_name(column_finish,
                    is_supercol_name=self.super,
                    slice_start=column_reversed)

        while True:
            if column_count is not None:
                if i == 0 and column_count <= buffer_size:
                    buffer_size = column_count
                else:
                    buffer_size = min(column_count - count + 1, buffer_size)

            sp = self._slice_predicate(None, last_name, finish,
                                       column_reversed, buffer_size, None, pack=False)
            list_cosc = self.pool.execute('get_slice', packed_key, cp, sp, rcl)

            if not list_cosc:
                return

            for j, cosc in enumerate(list_cosc):
                if j == 0 and i != 0:
                    continue

                if self.super:
                    if self._have_counters:
                        scol = cosc.counter_super_column
                    else:
                        scol = cosc.super_column
                    yield (self._unpack_name(scol.name, True), self._scol_to_dict(scol, include_timestamp, include_ttl))
                else:
                    if self._have_counters:
                        col = cosc.counter_column
                    else:
                        col = cosc.column
                    yield (self._unpack_name(col.name, False), self._col_to_dict(col, include_timestamp, include_ttl))

                count += 1
                if column_count is not None and count >= column_count:
                    return

            if len(list_cosc) != buffer_size:
                return

            if self.super:
                if self._have_counters:
                    last_name = list_cosc[-1].counter_super_column.name
                else:
                    last_name = list_cosc[-1].super_column.name
            else:
                if self._have_counters:
                    last_name = list_cosc[-1].counter_column.name
                else:
                    last_name = list_cosc[-1].column.name
            i += 1

    def get(self, key, columns=None, column_start="", column_finish="",
            column_reversed=False, column_count=100, include_timestamp=False,
            super_column=None, read_consistency_level=None, include_ttl=False):
        """
        Fetches all or part of the row with key `key`.

        The columns fetched may be limited to a specified list of column names
        using `columns`.

        Alternatively, you may fetch a slice of columns or super columns from a row
        using `column_start`, `column_finish`, and `column_count`.
        Setting these will cause columns or super columns to be fetched starting with
        `column_start`, continuing until `column_count` columns or super columns have
        been fetched or `column_finish` is reached.  If `column_start` is left as the
        empty string, the slice will begin with the start of the row; leaving
        `column_finish` blank will cause the slice to extend to the end of the row.
        Note that `column_count` defaults to 100, so rows over this size will not be
        completely fetched by default.

        If `column_reversed` is ``True``, columns are fetched in reverse sorted order,
        beginning with `column_start`.  In this case, if `column_start` is the empty
        string, the slice will begin with the end of the row.

        You may fetch all or part of only a single super column by setting `super_column`.
        If this is set, `column_start`, `column_finish`, `column_count`, and `column_reversed`
        will apply to the subcolumns of `super_column`.

        To include every column's timestamp in the result set, set `include_timestamp` to
        ``True``.  Results will include a ``(value, timestamp)`` tuple for each column.

        To include every column's ttl in the result set, set `include_ttl` to
        ``True``.  Results will include a ``(value, ttl)`` tuple for each column.

        If this is a standard column family, the return type is of the form
        ``{column_name: column_value}``.  If this is a super column family and `super_column`
        is not specified, the results are of the form
        ``{super_column_name: {column_name, column_value}}``.  If `super_column` is set,
        the super column name will be excluded and the results are of the form
        ``{column_name: column_value}``.

        """

        packed_key = self._pack_key(key)
        single_column = columns is not None and len(columns) == 1
        if (not self.super and single_column) or \
           (self.super and super_column is not None and single_column):
            column = None
            if self.super and super_column is None:
                super_column = columns[0]
            else:
                column = columns[0]
            cp = self._column_path(super_column, column)
            col_or_super = self.pool.execute('get', packed_key, cp,
                    read_consistency_level or self.read_consistency_level)
            return self._cosc_to_dict([col_or_super], include_timestamp, include_ttl)
        else:
            cp = self._column_parent(super_column)
            sp = self._slice_predicate(columns, column_start, column_finish,
                                       column_reversed, column_count, super_column)

            list_col_or_super = self.pool.execute('get_slice', packed_key, cp, sp,
                read_consistency_level or self.read_consistency_level)

            if len(list_col_or_super) == 0:
                raise NotFoundException()
            return self._cosc_to_dict(list_col_or_super, include_timestamp, include_ttl)

    def get_indexed_slices(self, index_clause, columns=None, column_start="", column_finish="",
                           column_reversed=False, column_count=100, include_timestamp=False,
                           read_consistency_level=None, buffer_size=None, include_ttl=False):
        """
        Similar to :meth:`get_range()`, but an :class:`~pycassa.cassandra.ttypes.IndexClause`
        is used instead of a key range.

        `index_clause` limits the keys that are returned based on expressions
        that compare the value of a column to a given value.  At least one of the
        expressions in the :class:`.IndexClause` must be on an indexed column.

        Note that Cassandra does not support secondary indexes or get_indexed_slices()
        for super column families.

            .. seealso:: :meth:`~pycassa.index.create_index_clause()` and
                         :meth:`~pycassa.index.create_index_expression()`

        """

        assert not self.super, "get_indexed_slices() is not " \
                "supported by super column families"

        cl = read_consistency_level or self.read_consistency_level
        cp = self._column_parent()
        sp = self._slice_predicate(columns, column_start, column_finish,
                                   column_reversed, column_count)

        new_exprs = []
        # Pack the values in the index clause expressions
        for expr in index_clause.expressions:
            value = self._pack_value(expr.value, expr.column_name)
            name = self._pack_name(expr.column_name)
            new_exprs.append(IndexExpression(name, expr.op, value))

        packed_start_key = self._pack_key(index_clause.start_key)
        clause = IndexClause(new_exprs, packed_start_key, index_clause.count)

        # Figure out how we will chunk the request
        if buffer_size is None:
            buffer_size = self.buffer_size
        row_count = clause.count

        count = 0
        i = 0
        last_key = clause.start_key
        while True:
            if row_count is not None:
                if i == 0 and row_count <= buffer_size:
                    # We don't need to chunk, grab exactly the number of rows
                    buffer_size = row_count
                else:
                    buffer_size = min(row_count - count + 1, buffer_size)
            clause.count = buffer_size
            clause.start_key = last_key
            key_slices = self.pool.execute('get_indexed_slices', cp, clause, sp, cl)

            if key_slices is None:
                return
            for j, key_slice in enumerate(key_slices):
                # Ignore the first element after the first iteration
                # because it will be a duplicate.
                if j == 0 and i != 0:
                    continue
                unpacked_key = self._unpack_key(key_slice.key)
                yield (unpacked_key,
                       self._cosc_to_dict(key_slice.columns, include_timestamp, include_ttl))

                count += 1
                if row_count is not None and count >= row_count:
                    return

            if len(key_slices) != buffer_size:
                return
            last_key = key_slices[-1].key
            i += 1

    def multiget(self, keys, columns=None, column_start="", column_finish="",
                 column_reversed=False, column_count=100, include_timestamp=False,
                 super_column=None, read_consistency_level=None, buffer_size=None, include_ttl=False):
        """
        Fetch multiple rows from a Cassandra server.

        `keys` should be a list of keys to fetch.

        `buffer_size` is the number of rows from the total list to fetch at a time.
        If left as ``None``, the ColumnFamily's :attr:`buffer_size` will be used.

        All other parameters are the same as :meth:`get()`, except that a list of keys may
        be passed in.

        Results will be returned in the form: ``{key: {column_name: column_value}}``. If
        an OrderedDict is used, the rows will have the same order as `keys`.

        """

        packed_keys = map(self._pack_key, keys)
        cp = self._column_parent(super_column)
        sp = self._slice_predicate(columns, column_start, column_finish,
                                   column_reversed, column_count, super_column)
        consistency = read_consistency_level or self.read_consistency_level

        buffer_size = buffer_size or self.buffer_size
        offset = 0
        keymap = {}
        while offset < len(packed_keys):
            new_keymap = self.pool.execute('multiget_slice',
                packed_keys[offset:offset + buffer_size], cp, sp, consistency)
            keymap.update(new_keymap)
            offset += buffer_size

        ret = self.dict_class()

        # Keep the order of keys
        for key in keys:
            ret[key] = None

        empty_keys = []
        for packed_key, columns in keymap.iteritems():
            unpacked_key = self._unpack_key(packed_key)
            if len(columns) > 0:
                ret[unpacked_key] = self._cosc_to_dict(columns, include_timestamp, include_ttl)
            else:
                empty_keys.append(unpacked_key)

        for key in empty_keys:
            try:
                del ret[key]
            except KeyError:
                pass

        return ret

    MAX_COUNT = 2 ** 31 - 1

    def get_count(self, key, super_column=None, read_consistency_level=None,
                  columns=None, column_start="", column_finish="",
                  column_reversed=False, max_count=None):
        """
        Count the number of columns in the row with key `key`.

        You may limit the columns or super columns counted to those in `columns`.
        Additionally, you may limit the columns or super columns counted to
        only those between `column_start` and `column_finish`.

        You may also count only the number of subcolumns in a single super column
        using `super_column`.  If this is set, `columns`, `column_start`, and
        `column_finish` only apply to the subcolumns of `super_column`.

        To put an upper bound on the number of columns that are counted,
        set `max_count`.

        """
        if max_count is None:
            max_count = self.MAX_COUNT

        packed_key = self._pack_key(key)
        cp = self._column_parent(super_column)
        sp = self._slice_predicate(columns, column_start, column_finish,
                                   column_reversed, max_count, super_column)

        return self.pool.execute('get_count', packed_key, cp, sp,
                read_consistency_level or self.read_consistency_level)

    def multiget_count(self, keys, super_column=None,
                       read_consistency_level=None,
                       columns=None, column_start="",
                       column_finish="", buffer_size=None,
                       column_reversed=False, max_count=None):
        """
        Perform a column count in parallel on a set of rows.

        The parameters are the same as for :meth:`multiget()`, except that a list
        of keys may be used. A dictionary of the form ``{key: int}`` is
        returned.

        `buffer_size` is the number of rows from the total list to count at a time.
        If left as ``None``, the ColumnFamily's :attr:`buffer_size` will be used.

        To put an upper bound on the number of columns that are counted,
        set `max_count`.

        """
        if max_count is None:
            max_count = self.MAX_COUNT

        packed_keys = map(self._pack_key, keys)
        cp = self._column_parent(super_column)
        sp = self._slice_predicate(columns, column_start, column_finish,
                                   column_reversed, max_count, super_column)
        consistency = read_consistency_level or self.read_consistency_level

        buffer_size = buffer_size or self.buffer_size
        offset = 0
        keymap = {}
        while offset < len(packed_keys):
            new_keymap = self.pool.execute('multiget_count',
                packed_keys[offset:offset + buffer_size], cp, sp, consistency)
            keymap.update(new_keymap)
            offset += buffer_size

        ret = self.dict_class()

        # Keep the order of keys
        for key in keys:
            ret[key] = None

        for packed_key, count in keymap.iteritems():
            ret[self._unpack_key(packed_key)] = count

        return ret

    def get_range(self, start="", finish="", columns=None, column_start="",
                  column_finish="", column_reversed=False, column_count=100,
                  row_count=None, include_timestamp=False,
                  super_column=None, read_consistency_level=None,
                  buffer_size=None, filter_empty=True, include_ttl=False,
                  start_token=None, finish_token=None):
        """
        Get an iterator over rows in a specified key range.

        The key range begins with `start` and ends with `finish`. If left
        as empty strings, these extend to the beginning and end, respectively.
        Note that if RandomPartitioner is used, rows are stored in the
        order of the MD5 hash of their keys, so getting a lexicographical range
        of keys is not feasible.

        In place of `start` and `finish`, you may use `start_token` and
        `finish_token` or a combination of `start` and `finish_token`.  In this
        case, you are specifying a token range to fetch instead of a key
        range.  This can be useful for fetching all data owned
        by a node or for parallelizing a full data set scan. Otherwise,
        you should typically just use `start` and `finish`.  When using
        RandomPartitioner or Murmur3Partitioner, `start_token`
        and `finish_token` should be string versions of the numeric tokens;
        for ByteOrderedPartitioner, they should be hex-encoded string versions
        of the token.

        The `row_count` parameter limits the total number of rows that may be
        returned. If left as ``None``, the number of rows that may be returned
        is unlimted (this is the default).

        When calling `get_range()`, the intermediate results need to be
        buffered if we are fetching many rows, otherwise the Cassandra
        server will overallocate memory and fail. `buffer_size` is the
        size of that buffer in number of rows. If left as ``None``, the
        ColumnFamily's :attr:`buffer_size` attribute will be used.

        When `filter_empty` is left as ``True``, empty rows (including
        `range ghosts <http://wiki.apache.org/cassandra/FAQ#range_ghosts>`_)
        will be skipped and will not count towards `row_count`.

        All other parameters are the same as those of :meth:`get()`.

        A generator over ``(key, {column_name: column_value})`` is returned.
        To convert this to a list, use ``list()`` on the result.

        """

        cl = read_consistency_level or self.read_consistency_level
        cp = self._column_parent(super_column)
        sp = self._slice_predicate(columns, column_start, column_finish,
                                   column_reversed, column_count, super_column)

        kr_args = {}
        count = 0
        i = 0

        if start_token is not None and (start not in ("", None) or finish not in ("", None)):
            raise ValueError(
                "ColumnFamily.get_range() received incompatible arguments: "
                "'start_token' may not be used with 'start' or 'finish'")

        if finish_token is not None and finish not in ("", None):
            raise ValueError(
                "ColumnFamily.get_range() received incompatible arguments: "
                "'finish_token' may not be used with 'finish'")

        if start_token is not None:
            kr_args['start_token'] = start_token
            kr_args['end_token'] = "" if finish_token is None else finish_token
        elif finish_token is not None:
            kr_args['start_key'] = self._pack_key(start)
            kr_args['end_token'] = finish_token
        else:
            kr_args['start_key'] = self._pack_key(start)
            kr_args['end_key'] = self._pack_key(finish)

        if buffer_size is None:
            buffer_size = self.buffer_size
        while True:
            if row_count is not None:
                if i == 0 and row_count <= buffer_size:
                    # We don't need to chunk, grab exactly the number of rows
                    buffer_size = row_count
                else:
                    buffer_size = min(row_count - count + 1, buffer_size)
            kr_args['count'] = buffer_size
            key_range = KeyRange(**kr_args)
            key_slices = self.pool.execute('get_range_slices', cp, sp, key_range, cl)
            # This may happen if nothing was ever inserted
            if key_slices is None:
                return
            for j, key_slice in enumerate(key_slices):
                # Ignore the first element after the first iteration
                # because it will be a duplicate.
                if j == 0 and i != 0:
                    continue
                if filter_empty and not key_slice.columns:
                    continue
                yield (self._unpack_key(key_slice.key),
                       self._cosc_to_dict(key_slice.columns, include_timestamp, include_ttl))
                count += 1
                if row_count is not None and count >= row_count:
                    return

            if len(key_slices) != buffer_size:
                return
            if 'start_token' in kr_args:
                del kr_args['start_token']
            kr_args['start_key'] = key_slices[-1].key
            i += 1

    def insert(self, key, columns, timestamp=None, ttl=None,
               write_consistency_level=None):
        """
        Insert or update columns in the row with key `key`.

        `columns` should be a dictionary of columns or super columns to insert
        or update.  If this is a standard column family, `columns` should
        look like ``{column_name: column_value}``.  If this is a super
        column family, `columns` should look like
        ``{super_column_name: {sub_column_name: value}}``.  If this is a
        counter column family, you may use integers as values and those will
        be used as counter adjustments.

        A timestamp may be supplied for all inserted columns with `timestamp`.

        `ttl` sets the "time to live" in number of seconds for the inserted
        columns. After this many seconds, Cassandra will mark the columns as
        deleted.

        The timestamp Cassandra reports as being used for insert is returned.

        """
        if timestamp is None:
            timestamp = self.timestamp()

        packed_key = self._pack_key(key)
        mut_list = self._make_mutation_list(columns, timestamp, ttl)
        mutations = {packed_key: {self.column_family: mut_list}}
        self.pool.execute('batch_mutate', mutations,
                write_consistency_level or self.write_consistency_level,
                allow_retries=self._allow_retries)

        return timestamp

    def batch_insert(self, rows, timestamp=None, ttl=None, write_consistency_level=None):
        """
        Like :meth:`insert()`, but multiple rows may be inserted at once.

        The `rows` parameter should be of the form ``{key: {column_name: column_value}}``
        if this is a standard column family or
        ``{key: {super_column_name: {column_name: column_value}}}`` if this is a super
        column family.

        """

        if timestamp == None:
            timestamp = self.timestamp()

        cf = self.column_family
        mutations = {}
        for key, columns in rows.iteritems():
            packed_key = self._pack_key(key)
            mut_list = self._make_mutation_list(columns, timestamp, ttl)
            mutations[packed_key] = {cf: mut_list}

        if mutations:
            self.pool.execute('batch_mutate', mutations,
                    write_consistency_level or self.write_consistency_level,
                    allow_retries=self._allow_retries)

        return timestamp

    def add(self, key, column, value=1, super_column=None, write_consistency_level=None):
        """
        Increment or decrement a counter.

        `value` should be an integer, either positive or negative, to be added
        to a counter column. By default, `value` is 1.

        .. versionadded:: 1.1.0
            Available in Cassandra 0.8.0 and later.

        """
        packed_key = self._pack_key(key)
        cp = self._column_parent(super_column)
        column = self._pack_name(column)
        self.pool.execute('add', packed_key, cp, CounterColumn(column, value),
                          write_consistency_level or self.write_consistency_level,
                          allow_retries=self._allow_retries)

    def remove(self, key, columns=None, super_column=None,
               write_consistency_level=None, timestamp=None, counter=None):
        """
        Remove a specified row or a set of columns within the row with key `key`.

        A set of columns or super columns to delete may be specified using
        `columns`.

        A single super column may be deleted by setting `super_column`. If
        `super_column` is specified, `columns` will apply to the subcolumns
        of `super_column`.

        If `columns` and `super_column` are both ``None``, the entire row is
        removed.

        The timestamp used for the mutation is returned.
        """

        if timestamp is None:
            timestamp = self.timestamp()
        batch = self.batch(write_consistency_level=write_consistency_level)
        batch.remove(key, columns, super_column, timestamp)
        batch.send()
        return timestamp

    def remove_counter(self, key, column, super_column=None, write_consistency_level=None):
        """
        Remove a counter at the specified location.

        Note that counters have limited support for deletes: if you remove a
        counter, you must wait to issue any following update until the delete
        has reached all the nodes and all of them have been fully compacted.

        .. versionadded:: 1.1.0
            Available in Cassandra 0.8.0 and later.

        """
        packed_key = self._pack_key(key)
        cp = self._column_path(super_column, column)
        self.pool.execute('remove_counter', packed_key, cp,
                          write_consistency_level or self.write_consistency_level)

    def batch(self, queue_size=100, write_consistency_level=None, atomic=None):
        """
        Create batch mutator for doing multiple insert, update, and remove
        operations using as few roundtrips as possible.

        The `queue_size` parameter sets the max number of mutations per request.

        A :class:`~pycassa.batch.CfMutator` is returned.

        """

        return CfMutator(self, queue_size,
                         write_consistency_level or self.write_consistency_level,
                         allow_retries=self._allow_retries,
                         atomic=atomic)

    def truncate(self):
        """
        Marks the entire ColumnFamily as deleted.

        From the user's perspective, a successful call to ``truncate`` will
        result complete data deletion from this column family. Internally,
        however, disk space will not be immediatily released, as with all
        deletes in Cassandra, this one only marks the data as deleted.

        The operation succeeds only if all hosts in the cluster at available
        and will throw an :exc:`.UnavailableException` if some hosts are
        down.

        """
        self.pool.execute('truncate', self.column_family)

PooledColumnFamily = ColumnFamily

########NEW FILE########
__FILENAME__ = columnfamilymap
"""
Provides a way to map an existing class of objects to a column family.

This can help to cut down boilerplate code related to converting
objects to a row format and back again.  ColumnFamilyMap is primarily
useful when you have one "object" per row.

.. seealso:: :mod:`pycassa.types` for selecting data types for object
             attributes and infomation about creating custom data
             types.

"""

from pycassa.types import CassandraType
from pycassa.columnfamily import ColumnFamily
import pycassa.util as util
import inspect

__all__ = ['ColumnFamilyMap']

def create_instance(cls, **kwargs):
    instance = cls()
    map(lambda (k,v): setattr(instance, k, v), kwargs.iteritems())
    return instance

class ColumnFamilyMap(ColumnFamily):
    """
    Maps an existing class to a column family.  Class fields become columns,
    and instances of that class can be represented as rows in standard column
    families or super columns in super column families.
    """

    def __init__(self, cls, pool, column_family, raw_columns=False, **kwargs):
        """
        Instances of `cls` are returned from :meth:`get()`, :meth:`multiget()`,
        :meth:`get_range()` and :meth:`get_indexed_slices()`.

        `pool` is a :class:`~pycassa.pool.ConnectionPool` that will be used
        in the same way a :class:`~.ColumnFamily` uses one.

        `column_family` is the name of a column family to tie to `cls`.

        If `raw_columns` is ``True``, all columns will be fetched into the
        `raw_columns` field in requests.
        """
        ColumnFamily.__init__(self, pool, column_family, **kwargs)

        self.cls = cls
        self.autopack_names = False

        self.raw_columns = raw_columns
        self.dict_class = util.OrderedDict
        self.defaults = {}
        self.fields = []
        for name, val_type in inspect.getmembers(self.cls):
            if name != 'key' and isinstance(val_type, CassandraType):
                self.fields.append(name)
                self.column_validators[name] = val_type
                self.defaults[name] = val_type.default

        if hasattr(self.cls, 'key') and isinstance(self.cls.key, CassandraType):
            self.key_validation_class = self.cls.key

    def combine_columns(self, columns):
        combined_columns = columns

        if self.raw_columns:
            combined_columns['raw_columns'] = columns

        for column, default in self.defaults.items():
            combined_columns.setdefault(column, default)

        return combined_columns

    def get(self, key, *args, **kwargs):
        """
        Creates one or more instances of `cls` from the row with key `key`.

        The fields that are retreived may be specified using `columns`, which
        should be a list of column names.

        If the column family is a super column family, a list of `cls`
        instances will be returned, one for each super column.  If
        the `super_column` parameter is not supplied, then `columns`
        specifies which super columns will be used to create instances
        of `cls`.  If the `super_column` parameter *is* supplied, only
        one instance of `cls` will be returned; if `columns` is specified
        in this case, only those attributes listed in `columns` will be fetched.

        All other parameters behave the same as in :meth:`.ColumnFamily.get()`.

        """
        if 'columns' not in kwargs and not self.super and not self.raw_columns:
            kwargs['columns'] = self.fields

        columns = ColumnFamily.get(self, key, *args, **kwargs)

        if self.super:
            if 'super_column' not in kwargs:
                vals = self.dict_class()
                for super_column, subcols in columns.iteritems():
                    combined = self.combine_columns(subcols)
                    vals[super_column] = create_instance(self.cls, key=key,
                            super_column=super_column, **combined)
                return vals

            combined = self.combine_columns(columns)
            return create_instance(self.cls, key=key,
                                   super_column=kwargs['super_column'],
                                   **combined)

        combined = self.combine_columns(columns)
        return create_instance(self.cls, key=key, **combined)

    def multiget(self, *args, **kwargs):
        """
        Like :meth:`get()`, but a list of keys may be specified.

        The result of multiget will be a dictionary where the keys
        are the keys from the `keys` argument, minus any missing rows.
        The value for each key in the dictionary will be the same as
        if :meth:`get()` were called on that individual key.

        """
        if 'columns' not in kwargs and not self.super and not self.raw_columns:
            kwargs['columns'] = self.fields

        kcmap = ColumnFamily.multiget(self, *args, **kwargs)
        ret = self.dict_class()
        for key, columns in kcmap.iteritems():
            if self.super:
                if 'super_column' not in kwargs:
                    vals = self.dict_class()
                    for super_column, subcols in columns.iteritems():
                        combined = self.combine_columns(subcols)
                        vals[super_column] = create_instance(self.cls, key=key, super_column=super_column, **combined)
                    ret[key] = vals
                else:
                    combined = self.combine_columns(columns)
                    ret[key] = create_instance(self.cls, key=key, super_column=kwargs['super_column'], **combined)
            else:
                combined = self.combine_columns(columns)
                ret[key] = create_instance(self.cls, key=key, **combined)
        return ret

    def get_range(self, *args, **kwargs):
        """
        Get an iterator over instances in a specified key range.

        Like :meth:`multiget()`, whether a single instance or multiple
        instances are returned per-row when the column family is a super
        column family depends on what parameters are passed.

        For an explanation of how :meth:`get_range` works and a description
        of the parameters, see :meth:`.ColumnFamily.get_range()`.

        Example usage with a standard column family:

        .. code-block:: python

            >>> pool = pycassa.ConnectionPool('Keyspace1')
            >>> usercf =  pycassa.ColumnFamily(pool, 'Users')
            >>> cfmap = pycassa.ColumnFamilyMap(MyClass, usercf)
            >>> users = cfmap.get_range(row_count=2, columns=['name', 'age'])
            >>> for key, user in users:
            ...     print user.name, user.age
            Miles Davis 84
            Winston Smith 42

        """
        if 'columns' not in kwargs and not self.super and not self.raw_columns:
            kwargs['columns'] = self.fields

        for key, columns in ColumnFamily.get_range(self, *args, **kwargs):
            if self.super:
                if 'super_column' not in kwargs:
                    vals = self.dict_class()
                    for super_column, subcols in columns.iteritems():
                        combined = self.combine_columns(subcols)
                        vals[super_column] = create_instance(self.cls, key=key, super_column=super_column, **combined)
                    yield vals
                else:
                    combined = self.combine_columns(columns)
                    yield create_instance(self.cls, key=key, super_column=kwargs['super_column'], **combined)
            else:
                combined = self.combine_columns(columns)
                yield create_instance(self.cls, key=key, **combined)

    def get_indexed_slices(self, *args, **kwargs):
        """
        Fetches a list of instances that satisfy an index clause. Similar
        to :meth:`get_range()`, but uses an index clause instead of a key range.

        See :meth:`.ColumnFamily.get_indexed_slices()` for
        an explanation of the parameters.

        """

        assert not self.super, "get_indexed_slices() is not " \
                "supported by super column families"

        if 'columns' not in kwargs and not self.raw_columns:
            kwargs['columns'] = self.fields

        for key, columns in ColumnFamily.get_indexed_slices(self, *args, **kwargs):
            combined = self.combine_columns(columns)
            yield create_instance(self.cls, key=key, **combined)

    def _get_instance_as_dict(self, instance, columns=None):
        fields = columns or self.fields
        instance_dict = {}
        for field in fields:
            val = getattr(instance, field, None)
            if val is not None and not isinstance(val, CassandraType):
                instance_dict[field] = val
        if self.super:
            instance_dict = {instance.super_column: instance_dict}
        return instance_dict

    def insert(self, instance, columns=None, timestamp=None, ttl=None,
               write_consistency_level=None):
        """
        Insert or update stored instances.

        `instance` should be an instance of `cls` to store.

        The `columns` parameter allows to you specify which attributes of
        `instance` should be inserted or updated. If left as ``None``, all
        attributes will be inserted.
        """

        if columns is None:
            fields = self.fields
        else:
            fields = columns

        insert_dict = self._get_instance_as_dict(instance, columns=fields)
        return ColumnFamily.insert(self, instance.key, insert_dict,
                                   timestamp=timestamp, ttl=ttl,
                                   write_consistency_level=write_consistency_level)

    def batch_insert(self, instances, timestamp=None, ttl=None,
            write_consistency_level=None):
        """
        Insert or update stored instances.

        `instances` should be a list containing instances of `cls` to store.
        """
        insert_dict = dict(
            [(instance.key, self._get_instance_as_dict(instance))
                for instance in instances]
        )
        return ColumnFamily.batch_insert(self, insert_dict,
                timestamp=timestamp, ttl=ttl,
                write_consistency_level=write_consistency_level)

    def remove(self, instance, columns=None, write_consistency_level=None):
        """
        Removes a stored instance.

        The `columns` parameter is a list of columns that should be removed.
        If this is left as the default value of ``None``, the entire stored
        instance will be removed.

        """
        if self.super:
            return ColumnFamily.remove(self, instance.key,
                                       super_column=instance.super_column,
                                       columns=columns,
                                       write_consistency_level=write_consistency_level)
        else:
            return ColumnFamily.remove(self, instance.key, columns,
                                       write_consistency_level=write_consistency_level)

########NEW FILE########
__FILENAME__ = connection
import struct
from cStringIO import StringIO

from thrift.transport import TTransport, TSocket, TSSLSocket
from thrift.transport.TTransport import (TTransportBase, CReadableTransport,
        TTransportException)
from thrift.protocol import TBinaryProtocol

from pycassa.cassandra import Cassandra
from pycassa.cassandra.ttypes import AuthenticationRequest

DEFAULT_SERVER = 'localhost:9160'
DEFAULT_PORT = 9160


def default_socket_factory(host, port):
    """
    Returns a normal :class:`TSocket` instance.
    """
    return TSocket.TSocket(host, port)


def default_transport_factory(tsocket, host, port):
    """
    Returns a normal :class:`TFramedTransport` instance wrapping `tsocket`.
    """
    return TTransport.TFramedTransport(tsocket)


class Connection(Cassandra.Client):
    """Encapsulation of a client session."""

    def __init__(self, keyspace, server, framed_transport=True, timeout=None,
                 credentials=None,
                 socket_factory=default_socket_factory,
                 transport_factory=default_transport_factory):
        self.keyspace = None
        self.server = server
        server = server.split(':')
        if len(server) <= 1:
            port = 9160
        else:
            port = server[1]
        host = server[0]
        socket = socket_factory(host, int(port))
        if timeout is not None:
            socket.setTimeout(timeout * 1000.0)
        self.transport = transport_factory(socket, host, port)
        protocol = TBinaryProtocol.TBinaryProtocolAccelerated(self.transport)
        Cassandra.Client.__init__(self, protocol)
        self.transport.open()

        if credentials is not None:
            request = AuthenticationRequest(credentials=credentials)
            self.login(request)

        self.set_keyspace(keyspace)

    def set_keyspace(self, keyspace):
        if keyspace != self.keyspace:
            Cassandra.Client.set_keyspace(self, keyspace)
            self.keyspace = keyspace

    def close(self):
        self.transport.close()


def make_ssl_socket_factory(ca_certs, validate=True):
    """
    A convenience function for creating an SSL socket factory.

    `ca_certs` should contain the path to the certificate file,
    `validate` determines whether or not SSL certificate validation will be performed.
    """

    def ssl_socket_factory(host, port):
        """
        Returns a :class:`TSSLSocket` instance.
        """
        return TSSLSocket.TSSLSocket(host, port, ca_certs=ca_certs, validate=validate)

    return ssl_socket_factory


class TSaslClientTransport(TTransportBase, CReadableTransport):

    START = 1
    OK = 2
    BAD = 3
    ERROR = 4
    COMPLETE = 5

    def __init__(self, transport, host, service,
            mechanism='GSSAPI', **sasl_kwargs):

        from puresasl.client import SASLClient

        self.transport = transport
        self.sasl = SASLClient(host, service, mechanism, **sasl_kwargs)

        self.__wbuf = StringIO()
        self.__rbuf = StringIO()

    def open(self):
        if not self.transport.isOpen():
            self.transport.open()

        self.send_sasl_msg(self.START, self.sasl.mechanism)
        self.send_sasl_msg(self.OK, self.sasl.process())

        while True:
            status, challenge = self.recv_sasl_msg()
            if status == self.OK:
                self.send_sasl_msg(self.OK, self.sasl.process(challenge))
            elif status == self.COMPLETE:
                if not self.sasl.complete:
                    raise TTransportException("The server erroneously indicated "
                            "that SASL negotiation was complete")
                else:
                    break
            else:
                raise TTransportException("Bad SASL negotiation status: %d (%s)"
                        % (status, challenge))

    def send_sasl_msg(self, status, body):
        header = struct.pack(">BI", status, len(body))
        self.transport.write(header + body)
        self.transport.flush()

    def recv_sasl_msg(self):
        header = self.transport.readAll(5)
        status, length = struct.unpack(">BI", header)
        if length > 0:
            payload = self.transport.readAll(length)
        else:
            payload = ""
        return status, payload

    def write(self, data):
        self.__wbuf.write(data)

    def flush(self):
        data = self.__wbuf.getvalue()
        encoded = self.sasl.wrap(data)
        # Note stolen from TFramedTransport:
        # N.B.: Doing this string concatenation is WAY cheaper than making
        # two separate calls to the underlying socket object. Socket writes in
        # Python turn out to be REALLY expensive, but it seems to do a pretty
        # good job of managing string buffer operations without excessive copies
        self.transport.write(''.join((struct.pack("!i", len(encoded)), encoded)))
        self.transport.flush()
        self.__wbuf = StringIO()

    def read(self, sz):
        ret = self.__rbuf.read(sz)
        if len(ret) != 0:
            return ret

        self._read_frame()
        return self.__rbuf.read(sz)

    def _read_frame(self):
        header = self.transport.readAll(4)
        length, = struct.unpack('!i', header)
        encoded = self.transport.readAll(length)
        self.__rbuf = StringIO(self.sasl.unwrap(encoded))

    def close(self):
        self.sasl.dispose()
        self.transport.close()

    # Implement the CReadableTransport interface.
    # Stolen shamelessly from TFramedTransport
    @property
    def cstringio_buf(self):
        return self.__rbuf

    def cstringio_refill(self, prefix, reqlen):
        # self.__rbuf will already be empty here because fastbinary doesn't
        # ask for a refill until the previous buffer is empty.  Therefore,
        # we can start reading new frames immediately.
        while len(prefix) < reqlen:
            self._read_frame()
            prefix += self.__rbuf.getvalue()
        self.__rbuf = StringIO(prefix)
        return self.__rbuf


def make_sasl_transport_factory(credential_factory):
    """
    A convenience function for creating a SASL transport factory.

    `credential_factory` should be a function taking two args: `host` and
    `port`.  It should return a ``dict`` of kwargs that will be passed
    to :func:`puresasl.client.SASLClient.__init__()`.

    Example usage::

        >>> def make_credentials(host, port):
        ...    return {'host': host,
        ...            'service': 'cassandra',
        ...            'principal': 'user/role@FOO.EXAMPLE.COM',
        ...            'mechanism': 'GSSAPI'}
        >>>
        >>> factory = make_sasl_transport_factory(make_credentials)
        >>> pool = ConnectionPool(..., transport_factory=factory)

    """

    def sasl_transport_factory(tsocket, host, port):
        sasl_kwargs = credential_factory(host, port)
        sasl_transport = TSaslClientTransport(tsocket, **sasl_kwargs)
        return TTransport.TFramedTransport(sasl_transport)

    return sasl_transport_factory

########NEW FILE########
__FILENAME__ = stubs
"""A functional set of stubs to be used for unit testing.

Projects that use pycassa and need to run an automated unit test suite on a
system like Jenkins can use these stubs to emulate interactions with Cassandra
without spinning up a cluster locally.

"""

import operator
from uuid import UUID

from collections import MutableMapping
from pycassa import NotFoundException
from pycassa.util import OrderedDict
from pycassa.columnfamily import gm_timestamp
from pycassa.index import EQ, GT, GTE, LT, LTE


__all__ = ['ConnectionPoolStub', 'ColumnFamilyStub', 'SystemManagerStub']


class DictWithTime(MutableMapping):
    def __init__(self, *args, **kwargs):
        self.__timestamp = kwargs.pop('timestamp', None)
        self.store = dict()
        self.update(dict(*args, **kwargs))

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value, timestamp=None):
        if timestamp is None:
            timestamp = self.__timestamp or gm_timestamp()

        self.store[key] = (value, timestamp)

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

operator_dict = {
    EQ: operator.eq,
    GT: operator.gt,
    GTE: operator.ge,
    LT: operator.lt,
    LTE: operator.le,
}


class ConnectionPoolStub(object):
    """Connection pool stub.

    Notes created column families in :attr:`self.column_families`.

    """
    def __init__(self, *args, **kwargs):
        self.column_families = {}

    def _register_mock_cf(self, name, cf):
        if name:
            self.column_families[name] = cf

    def dispose(self, *args, **kwargs):
        pass


class SystemManagerStub(object):
    """Functional System Manager stub object.

    Records when column families, columns, and indexes have been created. To
    see what has been recorded, look at :attr:`self.column_families`.

    """

    def __init__(self, *args, **kwargs):
        self.column_families = {}

    def create_column_family(self, keyspace, table_name, *args, **kwargs):
        """Create a column family and record its existence."""

        self.column_families[table_name] = {
            'keyspace': keyspace,
            'columns': {},
            'indexes': {},
        }

    def alter_column(self, keyspace, table_name, column_name, column_type):
        """Alter a column, recording its name and type."""

        self.column_families[table_name]['columns'][column_name] = column_type

    def create_index(self, keyspace, table_name, column_name, column_type):
        """Create an index, recording its name and type."""

        self.column_families[table_name]['indexes'][column_name] = column_type

    def _schema(self):
        ret = ','.join(self.column_families.keys())
        for k in self.column_families:
            for v in ('columns', 'indexes'):
                ret += ','.join(self.column_families[k][v])

        return hash(ret)

    def describe_schema_versions(self):
        """Describes the schema based on a hash of the stub system state."""

        return {self._schema(): ['1.1.1.1']}


class ColumnFamilyStub(object):
    """Functional ColumnFamily stub object.

    Acts very similar to a remote column family, supporting a basic version of
    the API. When instantiated, it registers itself with the supplied (stub)
    connection pool.

    """

    def __init__(self, pool=None, column_family=None, rows=None, **kwargs):
        rows = rows or OrderedDict()
        for r in rows.itervalues():
            if not isinstance(r, DictWithTime):
                r = DictWithTime(r)
        self.rows = rows

        if pool is not None:
            pool._register_mock_cf(column_family, self)

    def __len__(self):
        return len(self.rows)

    def __contains__(self, obj):
        return self.rows.__contains__(obj)

    def get(self, key, columns=None, column_start=None, column_finish=None,
            column_reversed=False, column_count=100, include_timestamp=False, **kwargs):
        """Get a value from the column family stub."""

        my_columns = self.rows.get(key)
        if include_timestamp:
            get_value = lambda x: x
        else:
            get_value = lambda x: x[0]
        if not my_columns:
            raise NotFoundException()

        items = my_columns.items()
        if isinstance(items[0], UUID) and items[0].version == 1:
            items.sort(key=lambda uuid: uuid.time)
        elif isinstance(items[0], tuple) and any(isinstance(x, UUID) for x in items[0]):
            are_components_uuids = [isinstance(x, UUID) and x.version == 1 for x in items[0]]

            def sortuuid(tup):
                return [x.time if is_uuid else x for x, is_uuid in zip(tup, are_components_uuids)]
            items.sort(key=sortuuid)
        else:
            items.sort()

        if column_reversed:
            items.reverse()

        sliced_items = [(k, get_value(v)) for (k, v) in items
                        if self._is_column_in_range(k, columns,
                                                    column_start, column_finish, column_reversed)][:column_count]

        return OrderedDict(sliced_items)

    def _is_column_in_range(self, k, columns, column_start, column_finish, column_reversed):
        lower_bound = column_start if not column_reversed else column_finish
        upper_bound = column_finish if not column_reversed else column_start

        if columns:
            return k in columns
        return (not lower_bound or k >= lower_bound) and (not upper_bound or k <= upper_bound)

    def multiget(self, keys, columns=None, column_start=None, column_finish=None,
                 column_reversed=False, column_count=100, include_timestamp=False, **kwargs):
        """Get multiple key values from the column family stub."""

        return OrderedDict(
            (key, self.get(
                key,
                columns=columns,
                column_start=column_start,
                column_finish=column_finish,
                column_reversed=column_reversed,
                column_count=column_count,
                include_timestamp=include_timestamp,
            )) for key in keys if key in self.rows)

    def batch(self, **kwargs):
        """Returns itself."""
        return self

    def send(self):
        pass

    def insert(self, key, columns, timestamp=None, **kwargs):
        """Insert data to the column family stub."""

        if key not in self.rows:
            self.rows[key] = DictWithTime([], timestamp=timestamp)

        for column in columns:
            self.rows[key].__setitem__(column, columns[column], timestamp)

        return self.rows[key][columns.keys()[0]][1]

    def get_indexed_slices(self, index_clause, **kwargs):
        """Grabs rows that match a pycassa index clause.

        See :meth:`pycassa.index.create_index_clause()` for creating such an
        index clause."""

        keys = []
        for key, row in self.rows.iteritems():
            for expr in index_clause.expressions:
                if (
                    expr.column_name in row and
                    operator_dict[expr.op](row[expr.column_name][0], expr.value)
                ):
                    keys.append(key)

        data = self.multiget(keys, **kwargs).items()
        return data

    def remove(self, key, columns=None):
        """Remove a key from the column family stub."""
        if key not in self.rows:
            raise NotFoundException()
        if columns is None:
            del self.rows[key]
        else:
            for c in columns:
                if c in self.rows[key]:
                    del self.rows[key][c]
            if not self.rows[key]:
                del self.rows[key]
        return gm_timestamp()

    def get_range(self, include_timestamp=False, columns=None, **kwargs):
        """Currently just gets all values from the column family."""

        return [(key, self.get(key, columns, include_timestamp))
                for key in self.rows]

    def truncate(self):
        """Clears all data from the column family stub."""

        self.rows.clear()

########NEW FILE########
__FILENAME__ = index
"""
Tools for using Cassandra's secondary indexes.

Example Usage:

.. code-block:: python

    >>> from pycassa.columnfamily import ColumnFamily
    >>> from pycassa.pool import ConnectionPool
    >>> from pycassa.index import *
    >>>
    >>> pool = ConnectionPool('Keyspace1')
    >>> users = ColumnFamily(pool, 'Users')
    >>> state_expr = create_index_expression('state', 'Utah')
    >>> bday_expr = create_index_expression('birthdate', 1970, GT)
    >>> clause = create_index_clause([state_expr, bday_expr], count=20)
    >>> for key, user in users.get_indexed_slices(clause):
    ...     print user['name'] + ",", user['state'], user['birthdate']
    John Smith, Utah 1971
    Mike Scott, Utah 1980
    Jeff Bird, Utah 1973

This gives you all of the rows (up to 20) which have a 'birthdate' value
above 1970 and a state value of 'Utah'.

.. seealso:: :class:`~pycassa.system_manager.SystemManager` methods
             :meth:`~pycassa.system_manager.SystemManager.create_index()`
             and :meth:`~pycassa.system_manager.SystemManager.drop_index()`

"""

from pycassa.cassandra.ttypes import IndexClause, IndexExpression,\
                                     IndexOperator

__all__ = ['create_index_clause', 'create_index_expression', 'EQ', 'GT', 'GTE',
           'LT', 'LTE']

EQ = IndexOperator.EQ
""" Equality (==) operator for index expressions """

GT = IndexOperator.GT
""" Greater-than (>) operator for index expressions """

GTE = IndexOperator.GTE
""" Greater-than-or-equal (>=) operator for index expressions """

LT = IndexOperator.LT
""" Less-than (<) operator for index expressions """

LTE = IndexOperator.LTE
""" Less-than-or-equal (<=) operator for index expressions """

def create_index_clause(expr_list, start_key='', count=100):
    """
    Constructs an :class:`~pycassa.cassandra.ttypes.IndexClause` for use with 
    :meth:`~pycassa.columnfamily.get_indexed_slices()`

    `expr_list` should be a list of
    :class:`~pycassa.cassandra.ttypes.IndexExpression` objects that
    must be matched for a row to be returned.  At least one of these expressions
    must be on an indexed column.

    Cassandra will only return matching rows with keys after `start_key`.  If this
    is the empty string, all rows will be considered.  Keep in mind that this
    is not as meaningful unless an OrderPreservingPartitioner is used.

    The number of rows to return is limited by `count`, which defaults to 100.

    """
    return IndexClause(expressions=expr_list, start_key=start_key,
                       count=count)

def create_index_expression(column_name, value, op=EQ):
    """
    Constructs an :class:`~pycassa.cassandra.ttypes.IndexExpression` to use
    in an :class:`~pycassa.cassandra.ttypes.IndexClause`

    The expression will be applied to the column with name `column_name`. A match
    will only occur if the operator specified with `op` returns ``True`` when used
    on the actual column value and the `value` parameter.

    The default operator is :const:`~EQ`, which tests for equality.

    """
    return IndexExpression(column_name=column_name, op=op, value=value)

########NEW FILE########
__FILENAME__ = pool_logger
import pycassa_logger
import logging

class PoolLogger(object):

    def __init__(self):
        self.root_logger = pycassa_logger.PycassaLogger()
        self.logger = self.root_logger.add_child_logger('pool', self.name_changed)

    def name_changed(self, new_logger):
        self.logger = new_logger

    def connection_created(self, dic):
        level = pycassa_logger.levels[dic.get('level', 'info')]
        conn = dic.get('connection')
        if level <= logging.INFO:
            self.logger.log(level,
                    "Connection %s (%s) opened for pool %s",
                    id(conn), conn.server, dic.get('pool_id'))
        else:
            self.logger.log(level,
                    "Error opening connection (%s) for pool %s: %s",
                    conn.server, dic.get('pool_id'), dic.get('error'))

    def connection_checked_out(self, dic):
        level = pycassa_logger.levels[dic.get('level', 'info')]
        conn = dic.get('connection')
        self.logger.log(level,
                "Connection %s (%s) was checked out from pool %s",
                id(conn), conn.server, dic.get('pool_id'))

    def connection_checked_in(self, dic):
        level = pycassa_logger.levels[dic.get('level', 'info')]
        conn = dic.get('connection')
        self.logger.log(level,
                "Connection %s (%s) was checked in to pool %s",
                id(conn), conn.server, dic.get('pool_id'))

    def connection_disposed(self, dic):
        level = pycassa_logger.levels[dic.get('level', 'info')]
        conn = dic.get('connection')
        if level <= logging.INFO:
            self.logger.log(level,
                    "Connection %s (%s) was closed; pool %s, reason: %s",
                    id(conn), conn.server, dic.get('pool_id'),
                    dic.get('message'))
        else:
            error = dic.get('error')
            self.logger.log(level,
                    "Error closing connection %s (%s) in pool %s, "
                    "reason: %s, error: %s %s",
                    id(conn), conn.server, dic.get('pool_id'),
                    dic.get('message'), error.__class__, error)

    def connection_recycled(self, dic):
        level = pycassa_logger.levels[dic.get('level', 'info')]
        old_conn = dic.get('old_conn')
        new_conn = dic.get('new_conn')
        self.logger.log(level,
                "Connection %s (%s) is being recycled in pool %s "
                "after %d operations; it is replaced by connection %s (%s)",
                id(old_conn), old_conn.server, dic.get('pool_id'),
                old_conn.operation_count, id(new_conn), new_conn.server)

    def connection_failed(self, dic):
        level = pycassa_logger.levels[dic.get('level', 'info')]
        conn = dic.get('connection')
        self.logger.log(level,
                "Connection %s (%s) in pool %s failed: %s",
                id(conn), dic.get('server'),
                dic.get('pool_id'), str(dic.get('error')))

    def obtained_server_list(self, dic):
        level = pycassa_logger.levels[dic.get('level', 'info')]
        self.logger.log(level,
                "Server list obtained for pool %s: [%s]",
                 dic.get('pool_id'), ", ".join(dic.get('server_list')))

    def pool_disposed(self, dic):
        level = pycassa_logger.levels[dic.get('level', 'info')]
        self.logger.log(level,
                "Pool %s was disposed", dic.get('pool_id'))

    def pool_at_max(self, dic):
        level = pycassa_logger.levels[dic.get('level', 'info')]
        self.logger.log(level,
                "Pool %s had a checkout request but was already "
                "at its max size (%s)",
                dic.get('pool_id'), dic.get('pool_max'))

########NEW FILE########
__FILENAME__ = pool_stats_logger
import pycassa_logger
import logging
import threading
import functools

def sync(lock_name):
    def wrapper(f):
        @functools.wraps(f)
        def wrapped(self, *args, **kwargs):
            lock = getattr(self, lock_name)
            try:
                lock.acquire()
                return f(self, *args, **kwargs)
            finally:
                lock.release()

        return wrapped

    return wrapper


class StatsLogger(object):
    """
    Basic stats logger that increment counts. You can plot these as `COUNTER` or
    `DERIVED` (RRD) or apply derivative (graphite) except for ``opened``, which tracks
    the currently opened connections.

    Usage::

        >>> pool = ConnectionPool(...)
        >>> stats_logger = StatsLogger()
        >>> pool.add_listener(stats_logger)
        >>>
        >>> # use the pool for a while...
        >>> import pprint
        >>> pprint.pprint(stats_logger.stats)
        {'at_max': 0,
         'checked_in': 401,
         'checked_out': 403,
         'created': {'failure': 0, 'success': 0},
         'disposed': {'failure': 0, 'success': 0},
         'failed': 1,
         'list': 0,
         'opened': {'current': 2, 'max': 2},
         'recycled': 0}


    Get your stats as ``stats_logger.stats`` and push them to your metrics
    system.
    """

    def __init__(self):
        #some callbacks are already locked by pool_lock, it's just simpler to have a global here for all operations
        self.lock = threading.Lock()
        self.reset()

    @sync('lock')
    def reset(self):
        """ Reset all counters to 0 """
        self._stats = {
            'created': {
                'success': 0,
                'failure': 0,
                },
            'checked_out': 0,
            'checked_in': 0,
            'opened': {
                'current': 0,
                'max': 0
            },
            'disposed': {
                'success': 0,
                'failure': 0
            },
            'recycled': 0,
            'failed': 0,
            'list': 0,
            'at_max': 0
        }


    def name_changed(self, new_logger):
        self.logger = new_logger

    @sync('lock')
    def connection_created(self, dic):
        level = pycassa_logger.levels[dic.get('level', 'info')]
        if level <= logging.INFO:
            self._stats['created']['success'] += 1
        else:
            self._stats['created']['failure'] += 1

    @sync('lock')
    def connection_checked_out(self, dic):
        self._stats['checked_out'] += 1
        self._update_opened(1)

    @sync('lock')
    def connection_checked_in(self, dic):
        self._stats['checked_in'] += 1
        self._update_opened(-1)

    def _update_opened(self, value):
        self._stats['opened']['current'] += value
        if self._stats['opened']['current'] > self._stats['opened']['max']:
            self._stats['opened']['max'] = self._stats['opened']['current']

    @sync('lock')
    def connection_disposed(self, dic):
        level = pycassa_logger.levels[dic.get('level', 'info')]
        if level <= logging.INFO:
            self._stats['disposed']['success'] += 1
        else:
            self._stats['disposed']['failure'] += 1

    @sync('lock')
    def connection_recycled(self, dic):
        self._stats['recycled'] += 1

    @sync('lock')
    def connection_failed(self, dic):
        self._stats['failed'] += 1

    @sync('lock')
    def obtained_server_list(self, dic):
        self._stats['list'] += 1

    @sync('lock')
    def pool_disposed(self, dic):
        pass

    @sync('lock')
    def pool_at_max(self, dic):
        self._stats['at_max'] += 1

    @property
    def stats(self):
        return self._stats

########NEW FILE########
__FILENAME__ = pycassa_logger
""" Logging facilities for pycassa. """

import logging

__all__ = ['PycassaLogger']

levels = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warn': logging.WARN,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

_DEFAULT_LOGGER_NAME = 'pycassa'
_DEFAULT_LEVEL = 'info'

class PycassaLogger:
    """
    The root logger for pycassa.

    This uses a singleton-like pattern,
    so creating a new instance will always give you the
    same result. This means that you can adjust all of
    pycassa's logging by calling methods on any instance.

    pycassa does *not* automatically add a handler to the
    logger, so logs will not be captured by default. You
    *must* add a :class:`logging.Handler()` object to
    the root handler for logs to be captured.  See the
    example usage below.

    By default, the root logger name is 'pycassa' and the
    logging level is 'info'.

    The available levels are:

    * debug
    * info
    * warn
    * error
    * critical

    Example Usage::

        >>> import logging
        >>> log = pycassa.PycassaLogger()
        >>> log.set_logger_name('pycassa_library')
        >>> log.set_logger_level('debug')
        >>> log.get_logger().addHandler(logging.StreamHandler())

    """

    __shared_state = {}

    def __init__(self):
        self.__dict__ = self.__shared_state
        if not hasattr(self, '_has_been_initialized'):
            self._has_been_initialized = True
            self._root_logger = None
            self._logger_name = None
            self._level = None
            self._child_loggers = []
            self.set_logger_name(_DEFAULT_LOGGER_NAME)
            self.set_logger_level(_DEFAULT_LEVEL)

    def get_logger(self):
        """ Returns the underlying :class:`logging.Logger` instance. """
        return self._root_logger

    def set_logger_level(self, level):
        """ Sets the logging level for all pycassa logging. """
        self._level = level
        self._root_logger.setLevel(levels[level])

    def get_logger_level(self):
        """ Gets the logging level for all pycassa logging. """
        return self._level

    def set_logger_name(self, logger_name):
        """ Sets the root logger name for pycassa and all of its children loggers. """
        self._logger_name = logger_name
        self._root_logger = logging.getLogger(logger_name)
        h = NullHandler()
        self._root_logger.addHandler(h)
        for child_logger in self._child_loggers:
            # make the callback
            child_logger[2](logging.getLogger('%s.%s' % (logger_name, child_logger[1])))
        if self._level is not None:
            self.set_logger_level(self._level)

    def get_logger_name(self):
        """ Gets the root logger name for pycassa. """
        return self._logger_name

    def add_child_logger(self, child_logger_name, name_change_callback):
        """
        Adds a child logger to pycassa that will be
        updated when the logger name changes.

        """
        new_logger = logging.getLogger('%s.%s' % (self._logger_name, child_logger_name))
        self._child_loggers.append((new_logger, child_logger_name, name_change_callback))
        return new_logger

class NullHandler(logging.Handler):
    """ For python pre 2.7 compatibility. """
    def emit(self, record):
        pass

# Initialize our "singleton"
PycassaLogger()

########NEW FILE########
__FILENAME__ = marshal
"""
Tools for marshalling and unmarshalling data stored
in Cassandra.
"""

import uuid
import struct
import calendar
from datetime import datetime
from decimal import Decimal

import pycassa.util as util

_number_types = frozenset((int, long, float))


def make_packer(fmt_string):
    return struct.Struct(fmt_string)

_bool_packer = make_packer('>B')
_float_packer = make_packer('>f')
_double_packer = make_packer('>d')
_long_packer = make_packer('>q')
_int_packer = make_packer('>i')
_short_packer = make_packer('>H')

_BASIC_TYPES = ('BytesType', 'LongType', 'IntegerType', 'UTF8Type',
                'AsciiType', 'LexicalUUIDType', 'TimeUUIDType',
                'CounterColumnType', 'FloatType', 'DoubleType',
                'DateType', 'BooleanType', 'UUIDType', 'Int32Type',
                'DecimalType', 'TimestampType')

def extract_type_name(typestr):
    if typestr is None:
        return 'BytesType'

    if "DynamicCompositeType" in typestr:
        return _get_composite_name(typestr)

    if "CompositeType" in typestr:
        return _get_composite_name(typestr)

    if "ReversedType" in typestr:
        return _get_inner_type(typestr)

    index = typestr.rfind('.')
    if index != -1:
        typestr = typestr[index + 1:]
    if typestr not in _BASIC_TYPES:
        typestr = 'BytesType'
    return typestr

def _get_inner_type(typestr):
    """ Given a str like 'org.apache...ReversedType(LongType)',
    return just 'LongType' """
    first_paren = typestr.find('(')
    return typestr[first_paren + 1:-1]

def _get_inner_types(typestr):
    """ Given a str like 'org.apache...CompositeType(LongType, DoubleType)',
    return a tuple of the inner types, like ('LongType', 'DoubleType') """
    internal_str = _get_inner_type(typestr)
    return map(str.strip, internal_str.split(','))

def _get_composite_name(typestr):
    types = map(extract_type_name, _get_inner_types(typestr))
    return "CompositeType(" + ", ".join(types) + ")"

def _to_timestamp(v):
    # Expects Value to be either date or datetime
    try:
        converted = calendar.timegm(v.utctimetuple())
        converted = converted * 1e3 + getattr(v, 'microsecond', 0) / 1e3
    except AttributeError:
        # Ints and floats are valid timestamps too
        if type(v) not in _number_types:
            raise TypeError('DateType arguments must be a datetime or timestamp')

        converted = v * 1e3
    return long(converted)

def get_composite_packer(typestr=None, composite_type=None):
    assert (typestr or composite_type), "Must provide typestr or " + \
            "CompositeType instance"
    if typestr:
        packers = map(packer_for, _get_inner_types(typestr))
    elif composite_type:
        packers = [c.pack for c in composite_type.components]

    len_packer = _short_packer.pack

    def pack_composite(items, slice_start=None):
        last_index = len(items) - 1
        s = ''
        for i, (item, packer) in enumerate(zip(items, packers)):
            eoc = '\x00'
            if isinstance(item, tuple):
                item, inclusive = item
                if inclusive:
                    if slice_start:
                        eoc = '\xff'
                    elif slice_start is False:
                        eoc = '\x01'
                else:
                    if slice_start:
                        eoc = '\x01'
                    elif slice_start is False:
                        eoc = '\xff'
            elif i == last_index:
                if slice_start:
                    eoc = '\xff'
                elif slice_start is False:
                    eoc = '\x01'

            packed = packer(item)
            s += ''.join((len_packer(len(packed)), packed, eoc))
        return s

    return pack_composite

def get_composite_unpacker(typestr=None, composite_type=None):
    assert (typestr or composite_type), "Must provide typestr or " + \
            "CompositeType instance"
    if typestr:
        unpackers = map(unpacker_for, _get_inner_types(typestr))
    elif composite_type:
        unpackers = [c.unpack for c in composite_type.components]

    len_unpacker = lambda v: _short_packer.unpack(v)[0]

    def unpack_composite(bytestr):
        # The composite format for each component is:
        #   <len>   <value>   <eoc>
        # 2 bytes | ? bytes | 1 byte
        components = []
        i = iter(unpackers)
        while bytestr:
            unpacker = i.next()
            length = len_unpacker(bytestr[:2])
            components.append(unpacker(bytestr[2:2 + length]))
            bytestr = bytestr[3 + length:]
        return tuple(components)

    return unpack_composite

def get_dynamic_composite_packer(typestr):
    cassandra_types = {}
    for inner_type in _get_inner_types(typestr):
        alias, cassandra_type = inner_type.split('=>')
        cassandra_types[alias] = cassandra_type

    len_packer = _short_packer.pack

    def pack_dynamic_composite(items, slice_start=None):
        last_index = len(items) - 1
        s = ''
        i = 0
        for (alias, item) in items:
            eoc = '\x00'
            if isinstance(alias, tuple):
                inclusive = item
                alias, item = alias
                if inclusive:
                    if slice_start:
                        eoc = '\xff'
                    elif slice_start is False:
                        eoc = '\x01'
                else:
                    if slice_start:
                        eoc = '\x01'
                    elif slice_start is False:
                        eoc = '\xff'
            elif i == last_index:
                if slice_start:
                    eoc = '\xff'
                elif slice_start is False:
                    eoc = '\x01'
            if isinstance(alias, str) and len(alias) == 1:
                header = '\x80' + alias
                packer = packer_for(cassandra_types[alias])
            else:
                cassandra_type = str(alias).split('(')[0]
                header = len_packer(len(cassandra_type)) + cassandra_type
                packer = packer_for(cassandra_type)
            i += 1

            packed = packer(item)
            s += ''.join((header, len_packer(len(packed)), packed, eoc))
        return s

    return pack_dynamic_composite

def get_dynamic_composite_unpacker(typestr):
    cassandra_types = {}
    for inner_type in _get_inner_types(typestr):
        alias, cassandra_type = inner_type.split('=>')
        cassandra_types[alias] = cassandra_type

    len_unpacker = lambda v: _short_packer.unpack(v)[0]

    def unpack_dynamic_composite(bytestr):
        # The composite format for each component is:
        # <header>     <len>      <value>     <eoc>
        # ? bytes  |  2 bytes  |  ? bytes  |  1 byte
        types = []
        components = []
        while bytestr:
            header = len_unpacker(bytestr[:2])
            if header & 0x8000:
                alias = bytestr[1]
                types.append(alias)
                unpacker = unpacker_for(cassandra_types[alias])
                bytestr = bytestr[2:]
            else:
                cassandra_type = bytestr[2:2 + header]
                types.append(cassandra_type)
                unpacker = unpacker_for(cassandra_type)
                bytestr = bytestr[2 + header:]
            length = len_unpacker(bytestr[:2])
            components.append(unpacker(bytestr[2:2 + length]))
            bytestr = bytestr[3 + length:]
        return tuple(zip(types, components))

    return unpack_dynamic_composite

def packer_for(typestr):
    if typestr is None:
        return lambda v: v

    if "DynamicCompositeType" in typestr:
        return get_dynamic_composite_packer(typestr)

    if "CompositeType" in typestr:
        return get_composite_packer(typestr)

    if "ReversedType" in typestr:
        return packer_for(_get_inner_type(typestr))

    data_type = extract_type_name(typestr)

    if data_type in ('DateType', 'TimestampType'):
        def pack_date(v, _=None):
            return _long_packer.pack(_to_timestamp(v))
        return pack_date

    elif data_type == 'BooleanType':
        def pack_bool(v, _=None):
            return _bool_packer.pack(bool(v))
        return pack_bool

    elif data_type == 'DoubleType':
        def pack_double(v, _=None):
            return _double_packer.pack(v)
        return pack_double

    elif data_type == 'FloatType':
        def pack_float(v, _=None):
            return _float_packer.pack(v)
        return pack_float

    elif data_type == 'DecimalType':
        def pack_decimal(dec, _=None):
            sign, digits, exponent = dec.as_tuple()
            unscaled = int(''.join(map(str, digits)))
            if sign:
                unscaled *= -1
            scale = _int_packer.pack(-exponent)
            unscaled = encode_int(unscaled)
            return scale + unscaled
        return pack_decimal

    elif data_type == 'LongType':
        def pack_long(v, _=None):
            return _long_packer.pack(v)
        return pack_long

    elif data_type == 'Int32Type':
        def pack_int32(v, _=None):
            return _int_packer.pack(v)
        return pack_int32

    elif data_type == 'IntegerType':
        return encode_int

    elif data_type == 'UTF8Type':
        def pack_utf8(v, _=None):
            try:
                return v.encode('utf-8')
            except UnicodeDecodeError:
                # v is already utf-8 encoded
                return v
        return pack_utf8

    elif 'UUIDType' in data_type:
        def pack_uuid(value, slice_start=None):
            if slice_start is None:
                value = util.convert_time_to_uuid(value,
                        randomize=True)
            else:
                value = util.convert_time_to_uuid(value,
                        lowest_val=slice_start,
                        randomize=False)

            if not hasattr(value, 'bytes'):
                raise TypeError("%s is not valid for UUIDType" % value)
            return value.bytes
        return pack_uuid

    elif data_type == "CounterColumnType":
        def noop(value, slice_start=None):
            return value
        return noop

    else: # data_type == 'BytesType' or something unknown
        def pack_bytes(v, _=None):
            if not isinstance(v, basestring):
                raise TypeError("A str or unicode value was expected, " +
                                "but %s was received instead (%s)"
                                % (v.__class__.__name__, str(v)))
            return v
        return pack_bytes

def unpacker_for(typestr):
    if typestr is None:
        return lambda v: v

    if "DynamicCompositeType" in typestr:
        return get_dynamic_composite_unpacker(typestr)

    if "CompositeType" in typestr:
        return get_composite_unpacker(typestr)

    if "ReversedType" in typestr:
        return unpacker_for(_get_inner_type(typestr))

    data_type = extract_type_name(typestr)

    if data_type == 'BytesType':
        return lambda v: v

    elif data_type in ('DateType', 'TimestampType'):
        return lambda v: datetime.utcfromtimestamp(
                _long_packer.unpack(v)[0] / 1e3)

    elif data_type == 'BooleanType':
        return lambda v: bool(_bool_packer.unpack(v)[0])

    elif data_type == 'DoubleType':
        return lambda v: _double_packer.unpack(v)[0]

    elif data_type == 'FloatType':
        return lambda v: _float_packer.unpack(v)[0]

    elif data_type == 'DecimalType':
        def unpack_decimal(v):
            scale = _int_packer.unpack(v[:4])[0]
            unscaled = decode_int(v[4:])
            return Decimal('%de%d' % (unscaled, -scale))
        return unpack_decimal

    elif data_type == 'LongType':
        return lambda v: _long_packer.unpack(v)[0]

    elif data_type == 'Int32Type':
        return lambda v: _int_packer.unpack(v)[0]

    elif data_type == 'IntegerType':
        return decode_int

    elif data_type == 'UTF8Type':
        return lambda v: v.decode('utf-8')

    elif 'UUIDType' in data_type:
        return lambda v: uuid.UUID(bytes=v)

    else:
        return lambda v: v

def encode_int(x, *args):
    if x >= 0:
        out = []
        while x >= 256:
            out.append(struct.pack('B', 0xff & x))
            x >>= 8
        out.append(struct.pack('B', 0xff & x))
        if x > 127:
            out.append('\x00')
    else:
        x = -1 - x
        out = []
        while x >= 256:
            out.append(struct.pack('B', 0xff & ~x))
            x >>= 8
        if x <= 127:
            out.append(struct.pack('B', 0xff & ~x))
        else:
            out.append(struct.pack('>H', 0xffff & ~x))

    return ''.join(reversed(out))

def decode_int(term, *args):
    if term != "":
        val = int(term.encode('hex'), 16)
        if (ord(term[0]) & 128) != 0:
            val = val - (1 << (len(term) * 8))
        return val

########NEW FILE########
__FILENAME__ = pool
""" Connection pooling for Cassandra connections. """

from __future__ import with_statement

import time
import threading
import random
import socket
import sys

if 'gevent.monkey' in sys.modules:
    from gevent import queue as Queue
else:
    import Queue  # noqa

from thrift import Thrift
from thrift.transport.TTransport import TTransportException
from connection import (Connection, default_socket_factory,
        default_transport_factory)
from logging.pool_logger import PoolLogger
from util import as_interface
from cassandra.ttypes import TimedOutException, UnavailableException

_BASE_BACKOFF = 0.01

__all__ = ['QueuePool', 'ConnectionPool', 'PoolListener',
           'ConnectionWrapper', 'AllServersUnavailable',
           'MaximumRetryException', 'NoConnectionAvailable',
           'InvalidRequestError']

class ConnectionWrapper(Connection):
    """
    Creates a wrapper for a :class:`~.pycassa.connection.Connection`
    object, adding pooling related functionality while still allowing
    access to the thrift API calls.

    These should not be created directly, only obtained through
    Pool's :meth:`~.ConnectionPool.get()` method.
    """

    # These mark the state of the connection so that we can
    # check to see that they are not returned, checked out,
    # or disposed twice (or from the wrong state).
    _IN_QUEUE = 0
    _CHECKED_OUT = 1
    _DISPOSED = 2

    def __init__(self, pool, max_retries, *args, **kwargs):
        self._pool = pool
        self._retry_count = 0
        self.max_retries = max_retries
        self.info = {}
        self.starttime = time.time()
        self.operation_count = 0
        self._state = ConnectionWrapper._CHECKED_OUT
        Connection.__init__(self, *args, **kwargs)
        self._pool._notify_on_connect(self)

        # For testing purposes only
        self._should_fail = False
        self._original_meth = self.send_batch_mutate

    def return_to_pool(self):
        """
        Returns this to the pool.

        This has the same effect as calling :meth:`ConnectionPool.put()`
        on the wrapper.

        """
        self._pool.put(self)

    def _checkin(self):
        if self._state == ConnectionWrapper._IN_QUEUE:
            raise InvalidRequestError("A connection has been returned to "
                    "the connection pool twice.")
        elif self._state == ConnectionWrapper._DISPOSED:
            raise InvalidRequestError("A disposed connection has been returned "
                    "to the connection pool.")
        self._state = ConnectionWrapper._IN_QUEUE

    def _checkout(self):
        if self._state != ConnectionWrapper._IN_QUEUE:
            raise InvalidRequestError("A connection has been checked "
                    "out twice.")
        self._state = ConnectionWrapper._CHECKED_OUT

    def _is_in_queue_or_disposed(self):
        ret = self._state == ConnectionWrapper._IN_QUEUE or \
              self._state == ConnectionWrapper._DISPOSED
        return ret

    def _dispose_wrapper(self, reason=None):
        if self._state == ConnectionWrapper._DISPOSED:
            raise InvalidRequestError("A connection has been disposed twice.")
        self._state = ConnectionWrapper._DISPOSED

        self.close()
        self._pool._notify_on_dispose(self, msg=reason)

    def _replace(self, new_conn_wrapper):
        """
        Get another wrapper from the pool and replace our own contents
        with its contents.

        """
        self.server = new_conn_wrapper.server
        self.transport = new_conn_wrapper.transport
        self._iprot = new_conn_wrapper._iprot
        self._oprot = new_conn_wrapper._oprot
        self.info = new_conn_wrapper.info
        self.starttime = new_conn_wrapper.starttime
        self.operation_count = new_conn_wrapper.operation_count
        self._state = ConnectionWrapper._CHECKED_OUT
        self._should_fail = new_conn_wrapper._should_fail

    @classmethod
    def _retry(cls, f):
        def new_f(self, *args, **kwargs):
            self.operation_count += 1
            self.info['request'] = {'method': f.__name__, 'args': args, 'kwargs': kwargs}
            try:
                allow_retries = kwargs.pop('allow_retries', True)
                if kwargs.pop('reset', False):
                    self._pool._replace_wrapper() # puts a new wrapper in the queue
                    self._replace(self._pool.get()) # swaps out transport
                result = f(self, *args, **kwargs)
                self._retry_count = 0 # reset the count after a success
                return result
            except Thrift.TApplicationException:
                self.close()
                self._pool._decrement_overflow()
                self._pool._clear_current()
                raise
            except (TimedOutException, UnavailableException,
                    TTransportException,
                    socket.error, IOError, EOFError), exc:
                self._pool._notify_on_failure(exc, server=self.server, connection=self)

                self.close()
                self._pool._decrement_overflow()
                self._pool._clear_current()

                self._retry_count += 1
                if (not allow_retries or
                    (self.max_retries != -1 and self._retry_count > self.max_retries)):
                    raise MaximumRetryException('Retried %d times. Last failure was %s: %s' %
                                                (self._retry_count, exc.__class__.__name__, exc))
                # Exponential backoff
                time.sleep(_BASE_BACKOFF * (2 ** self._retry_count))

                kwargs['reset'] = True
                return new_f(self, *args, **kwargs)

        new_f.__name__ = f.__name__
        return new_f

    def _fail_once(self, *args, **kwargs):
        if self._should_fail:
            self._should_fail = False
            raise TimedOutException
        else:
            return self._original_meth(*args, **kwargs)

    def get_keyspace_description(self, keyspace=None, use_dict_for_col_metadata=False):
        """
        Describes the given keyspace.

        If `use_dict_for_col_metadata` is ``True``, the column metadata will be stored
        as a dictionary instead of a list

        A dictionary of the form ``{column_family_name: CfDef}`` is returned.

        """
        if keyspace is None:
            keyspace = self.keyspace

        ks_def = self.describe_keyspace(keyspace)
        cf_defs = dict()
        for cf_def in ks_def.cf_defs:
            cf_defs[cf_def.name] = cf_def
            if use_dict_for_col_metadata:
                old_metadata = cf_def.column_metadata
                new_metadata = dict()
                for datum in old_metadata:
                    new_metadata[datum.name] = datum
                cf_def.column_metadata = new_metadata
        return cf_defs

    def __str__(self):
        return "<ConnectionWrapper %s@%s>" % (self.keyspace, self.server)

retryable = ('get', 'get_slice', 'multiget_slice', 'get_count', 'multiget_count',
             'get_range_slices', 'get_indexed_slices', 'batch_mutate', 'add',
             'insert', 'remove', 'remove_counter', 'truncate', 'describe_keyspace',
             'atomic_batch_mutate')
for fname in retryable:
    new_f = ConnectionWrapper._retry(getattr(Connection, fname))
    setattr(ConnectionWrapper, fname, new_f)

class ConnectionPool(object):
    """A pool that maintains a queue of open connections."""

    _max_overflow = 0

    def _get_max_overflow(self):
        return self._max_overflow

    def _set_max_overflow(self, max_overflow):
        with self._pool_lock:
            self._max_overflow = max_overflow
            self._overflow_enabled = max_overflow > 0 or max_overflow == -1
            if max_overflow == -1:
                self._max_conns = (2 ** 31) - 1
            else:
                self._max_conns = self._pool_size + max_overflow

    max_overflow = property(_get_max_overflow, _set_max_overflow)
    """ Whether or not a new connection may be opened when the
    pool is empty is controlled by `max_overflow`.  This specifies how many
    additional connections may be opened after the pool has reached `pool_size`;
    keep in mind that these extra connections will be discarded upon checkin
    until the pool is below `pool_size`.  This may be set to -1 to indicate no
    overflow limit. The default value is 0, which does not allow for overflow. """

    pool_timeout = 30
    """ If ``pool_size + max_overflow`` connections have already been checked
    out, an attempt to retrieve a new connection from the pool will wait
    up to `pool_timeout` seconds for a connection to be returned to the
    pool before giving up. Note that this setting is only meaningful when you
    are accessing the pool concurrently, such as with multiple threads.
    This may be set to 0 to fail immediately or -1 to wait forever.
    The default value is 30. """

    recycle = 10000
    """ After performing `recycle` number of operations, connections will
    be replaced when checked back in to the pool.  This may be set to
    -1 to disable connection recycling. The default value is 10,000. """

    max_retries = 5
    """ When an operation on a connection fails due to an :exc:`~.TimedOutException`
    or :exc:`~.UnavailableException`, which tend to indicate single or
    multiple node failure, the operation will be retried on different nodes
    up to `max_retries` times before an :exc:`~.MaximumRetryException` is raised.
    Setting this to 0 disables retries and setting to -1 allows unlimited retries.
    The default value is 5. """

    logging_name = None
    """ By default, each pool identifies itself in the logs using ``id(self)``.
    If multiple pools are in use for different purposes, setting `logging_name` will
    help individual pools to be identified in the logs. """

    socket_factory = default_socket_factory
    """ A function that creates the socket for each connection in the pool.
    This function should take two arguments: `host`, the host the connection is
    being made to, and `port`, the destination port.

    By default, this is function is :func:`~connection.default_socket_factory`.
    """

    transport_factory = default_transport_factory
    """ A function that creates the transport for each connection in the pool.
    This function should take three arguments: `tsocket`, a TSocket object for the
    transport, `host`, the host the connection is being made to, and `port`,
    the destination port.

    By default, this is function is :func:`~connection.default_transport_factory`.
    """

    def __init__(self, keyspace,
                 server_list=['localhost:9160'],
                 credentials=None,
                 timeout=0.5,
                 use_threadlocal=True,
                 pool_size=5,
                 prefill=True,
                 socket_factory=default_socket_factory,
                 transport_factory=default_transport_factory,
                 **kwargs):
        """
        All connections in the pool will be opened to `keyspace`.

        `server_list` is a sequence of servers in the form ``"host:port"`` that
        the pool will connect to. The port defaults to 9160 if excluded.
        The list will be randomly shuffled before being drawn from sequentially.
        `server_list` may also be a function that returns the sequence of servers.

        If authentication or authorization is required, `credentials` must
        be supplied.  This should be a dictionary containing 'username' and
        'password' keys with appropriate string values.

        `timeout` specifies in seconds how long individual connections will
        block before timing out. If set to ``None``, connections will never
        timeout.

        If `use_threadlocal` is set to ``True``, repeated calls to
        :meth:`get()` within the same application thread will
        return the same :class:`ConnectionWrapper` object if one is
        already checked out from the pool.  Be careful when setting `use_threadlocal`
        to ``False`` in a multithreaded application, especially with retries enabled.
        Synchronization may be required to prevent the connection from changing while
        another thread is using it.

        The pool will keep up `pool_size` open connections in the pool
        at any time.  When a connection is returned to the pool, the
        connection will be discarded is the pool already contains `pool_size`
        connections.  The total number of simultaneous connections the pool will
        allow is ``pool_size + max_overflow``,
        and the number of "sleeping" connections the pool will allow is ``pool_size``.

        A good choice for `pool_size` is a multiple of the number of servers
        passed to the Pool constructor.  If a size less than this is chosen,
        the last ``(len(server_list) - pool_size)`` servers may not be used until
        either overflow occurs, a connection is recycled, or a connection
        fails. Similarly, if a multiple of ``len(server_list)`` is not chosen,
        those same servers would have a decreased load. By default, overflow
        is disabled.

        If `prefill` is set to ``True``, `pool_size` connections will be opened
        when the pool is created.

        Example Usage:

        .. code-block:: python

            >>> pool = pycassa.ConnectionPool(keyspace='Keyspace1', server_list=['10.0.0.4:9160', '10.0.0.5:9160'], prefill=False)
            >>> cf = pycassa.ColumnFamily(pool, 'Standard1')
            >>> cf.insert('key', {'col': 'val'})
            1287785685530679

        """

        self._pool_threadlocal = use_threadlocal
        self.keyspace = keyspace
        self.credentials = credentials
        self.timeout = timeout
        self.socket_factory = socket_factory
        self.transport_factory = transport_factory
        if use_threadlocal:
            self._tlocal = threading.local()

        self._pool_size = pool_size
        self._q = Queue.Queue(pool_size)
        self._pool_lock = threading.Lock()
        self._current_conns = 0

        # Listener groups
        self.listeners = []
        self._on_connect = []
        self._on_checkout = []
        self._on_checkin = []
        self._on_dispose = []
        self._on_recycle = []
        self._on_failure = []
        self._on_server_list = []
        self._on_pool_dispose = []
        self._on_pool_max = []

        self.add_listener(PoolLogger())

        if "listeners" in kwargs:
            listeners = kwargs["listeners"]
            for l in listeners:
                self.add_listener(l)

        self.logging_name = kwargs.get("logging_name", None)
        if not self.logging_name:
            self.logging_name = id(self)

        if "max_overflow" not in kwargs:
            self._set_max_overflow(0)

        recognized_kwargs = ["pool_timeout", "recycle", "max_retries", "max_overflow"]
        for kw in recognized_kwargs:
            if kw in kwargs:
                setattr(self, kw, kwargs[kw])

        self.set_server_list(server_list)

        self._prefill = prefill
        if self._prefill:
            self.fill()

    def set_server_list(self, server_list):
        """
        Sets the server list that the pool will make connections to.

        `server_list` should be sequence of servers in the form ``"host:port"`` that
        the pool will connect to.  The list will be randomly permuted before
        being used. `server_list` may also be a function that returns the
        sequence of servers.
        """
        if callable(server_list):
            self.server_list = list(server_list())
        else:
            self.server_list = list(server_list)

        random.shuffle(self.server_list)
        self._list_position = 0
        self._notify_on_server_list(self.server_list)

    def _get_next_server(self):
        """
        Gets the next 'localhost:port' combination from the list of
        servers and increments the position. This is not thread-safe,
        but client-side load-balancing isn't so important that this is
        a problem.
        """
        if self._list_position >= len(self.server_list):
            self._list_position = 0
        server = self.server_list[self._list_position]
        self._list_position += 1
        return server

    def _create_connection(self):
        """Creates a ConnectionWrapper, which opens a
        pycassa.connection.Connection."""
        if not self.server_list:
            raise AllServersUnavailable('Cannot connect to any servers as server list is empty!')
        failure_count = 0
        while failure_count < 2 * len(self.server_list):
            try:
                server = self._get_next_server()
                wrapper = self._get_new_wrapper(server)
                return wrapper
            except (TTransportException, socket.error, IOError, EOFError), exc:
                self._notify_on_failure(exc, server)
                failure_count += 1
        raise AllServersUnavailable('An attempt was made to connect to each of the servers ' +
                                    'twice, but none of the attempts succeeded. The last failure was %s: %s' %
                                    (exc.__class__.__name__, exc))

    def fill(self):
        """
        Adds connections to the pool until at least ``pool_size`` connections
        exist, whether they are currently checked out from the pool or not.

        .. versionadded:: 1.2.0
        """
        with self._pool_lock:
            while self._current_conns < self._pool_size:
                conn = self._create_connection()
                conn._checkin()
                self._q.put(conn, False)
                self._current_conns += 1

    def _get_new_wrapper(self, server):
        return ConnectionWrapper(self, self.max_retries,
                                 self.keyspace, server,
                                 timeout=self.timeout,
                                 credentials=self.credentials,
                                 socket_factory=self.socket_factory,
                                 transport_factory=self.transport_factory)

    def _replace_wrapper(self):
        """Try to replace the connection."""
        if not self._q.full():
            conn = self._create_connection()
            conn._checkin()

            try:
                self._q.put(conn, False)
            except Queue.Full:
                conn._dispose_wrapper(reason="pool is already full")
            else:
                with self._pool_lock:
                    self._current_conns += 1

    def _clear_current(self):
        """ If using threadlocal, clear our threadlocal current conn. """
        if self._pool_threadlocal:
            self._tlocal.current = None

    def put(self, conn):
        """ Returns a connection to the pool. """
        if not conn.transport.isOpen():
            return

        if self._pool_threadlocal:
            if hasattr(self._tlocal, 'current') and self._tlocal.current:
                conn = self._tlocal.current
                self._tlocal.current = None
            else:
                conn = None
        if conn:
            conn._retry_count = 0
            if conn._is_in_queue_or_disposed():
                raise InvalidRequestError("Connection was already checked in or disposed")

            if self.recycle > -1 and conn.operation_count > self.recycle:
                new_conn = self._create_connection()
                self._notify_on_recycle(conn, new_conn)
                conn._dispose_wrapper(reason="recyling connection")
                conn = new_conn
            conn._checkin()
            self._notify_on_checkin(conn)

            try:
                self._q.put_nowait(conn)
            except Queue.Full:
                conn._dispose_wrapper(reason="pool is already full")
                self._decrement_overflow()
    return_conn = put

    def _decrement_overflow(self):
        with self._pool_lock:
            self._current_conns -= 1

    def _new_if_required(self, max_conns, check_empty_queue=False):
        """ Creates new connection if there is room """
        with self._pool_lock:
            if (not check_empty_queue or self._q.empty()) and self._current_conns < max_conns:
                new_conn = True
                self._current_conns += 1
            else:
                new_conn = False

        if new_conn:
            try:
                return self._create_connection()
            except:
                with self._pool_lock:
                    self._current_conns -= 1
                raise
        return None

    def get(self):
        """ Gets a connection from the pool. """
        conn = None
        if self._pool_threadlocal:
            try:
                if self._tlocal.current:
                    conn = self._tlocal.current
                if conn:
                    return conn
            except AttributeError:
                pass

        conn = self._new_if_required(self._pool_size)
        if not conn:
            # if queue is empty and max_overflow is not reached, create new conn
            conn = self._new_if_required(self._max_conns, check_empty_queue=True)

        if not conn:
            # We will have to fetch from the queue, and maybe block
            timeout = self.pool_timeout
            if timeout == -1:
                timeout = None

            try:
                conn = self._q.get(timeout=timeout)
            except Queue.Empty:
                self._notify_on_pool_max(pool_max=self._max_conns)
                size_msg = "size %d" % (self._pool_size, )
                if self._overflow_enabled:
                    size_msg += "overflow %d" % (self._max_overflow)
                message = "ConnectionPool limit of %s reached, unable to obtain connection after %d seconds" \
                          % (size_msg, self.pool_timeout)
                raise NoConnectionAvailable(message)
            else:
                conn._checkout()

        if self._pool_threadlocal:
            self._tlocal.current = conn
        self._notify_on_checkout(conn)
        return conn

    def execute(self, f, *args, **kwargs):
        """
        Get a connection from the pool, execute
        `f` on it with `*args` and `**kwargs`, return the
        connection to the pool, and return the result of `f`.
        """
        conn = None
        try:
            conn = self.get()
            return getattr(conn, f)(*args, **kwargs)
        finally:
            if conn:
                conn.return_to_pool()

    def dispose(self):
        """ Closes all checked in connections in the pool. """
        while True:
            try:
                conn = self._q.get(False)
                conn._dispose_wrapper(
                        reason="Pool %s is being disposed" % id(self))
                self._decrement_overflow()
            except Queue.Empty:
                break

        self._notify_on_pool_dispose()

    def size(self):
        """ Returns the capacity of the pool. """
        return self._pool_size

    def checkedin(self):
        """ Returns the number of connections currently in the pool. """
        return self._q.qsize()

    def overflow(self):
        """ Returns the number of overflow connections that are currently open. """
        return max(self._current_conns - self._pool_size, 0)

    def checkedout(self):
        """ Returns the number of connections currently checked out from the pool. """
        return self._current_conns - self.checkedin()

    def add_listener(self, listener):
        """
        Add a :class:`PoolListener`-like object to this pool.

        `listener` may be an object that implements some or all of
        :class:`PoolListener`, or a dictionary of callables containing implementations
        of some or all of the named methods in :class:`PoolListener`.

        """

        listener = as_interface(listener,
            methods=('connection_created', 'connection_checked_out',
                     'connection_checked_in', 'connection_disposed',
                     'connection_recycled', 'connection_failed',
                     'obtained_server_list', 'pool_disposed',
                     'pool_at_max'))

        self.listeners.append(listener)
        if hasattr(listener, 'connection_created'):
            self._on_connect.append(listener)
        if hasattr(listener, 'connection_checked_out'):
            self._on_checkout.append(listener)
        if hasattr(listener, 'connection_checked_in'):
            self._on_checkin.append(listener)
        if hasattr(listener, 'connection_disposed'):
            self._on_dispose.append(listener)
        if hasattr(listener, 'connection_recycled'):
            self._on_recycle.append(listener)
        if hasattr(listener, 'connection_failed'):
            self._on_failure.append(listener)
        if hasattr(listener, 'obtained_server_list'):
            self._on_server_list.append(listener)
        if hasattr(listener, 'pool_disposed'):
            self._on_pool_dispose.append(listener)
        if hasattr(listener, 'pool_at_max'):
            self._on_pool_max.append(listener)

    def _notify_on_pool_dispose(self):
        if self._on_pool_dispose:
            dic = {'pool_id': self.logging_name,
                   'level': 'info'}
            for l in self._on_pool_dispose:
                l.pool_disposed(dic)

    def _notify_on_pool_max(self, pool_max):
        if self._on_pool_max:
            dic = {'pool_id': self.logging_name,
                   'level': 'info',
                   'pool_max': pool_max}
            for l in self._on_pool_max:
                l.pool_at_max(dic)

    def _notify_on_dispose(self, conn_record, msg=""):
        if self._on_dispose:
            dic = {'pool_id': self.logging_name,
                   'level': 'debug',
                   'connection': conn_record}
            if msg:
                dic['message'] = msg
            for l in self._on_dispose:
                l.connection_disposed(dic)

    def _notify_on_server_list(self, server_list):
        dic = {'pool_id': self.logging_name,
               'level': 'debug',
               'server_list': server_list}
        if self._on_server_list:
            for l in self._on_server_list:
                l.obtained_server_list(dic)

    def _notify_on_recycle(self, old_conn, new_conn):
        if self._on_recycle:
            dic = {'pool_id': self.logging_name,
                   'level': 'debug',
                   'old_conn': old_conn,
                   'new_conn': new_conn}
        for l in self._on_recycle:
            l.connection_recycled(dic)

    def _notify_on_connect(self, conn_record, msg="", error=None):
        if self._on_connect:
            dic = {'pool_id': self.logging_name,
                   'level': 'debug',
                   'connection': conn_record}
            if msg:
                dic['message'] = msg
            if error:
                dic['error'] = error
                dic['level'] = 'warn'
            for l in self._on_connect:
                l.connection_created(dic)

    def _notify_on_checkin(self, conn_record):
        if self._on_checkin:
            dic = {'pool_id': self.logging_name,
                   'level': 'debug',
                   'connection': conn_record}
            for l in self._on_checkin:
                l.connection_checked_in(dic)

    def _notify_on_checkout(self, conn_record):
        if self._on_checkout:
            dic = {'pool_id': self.logging_name,
                   'level': 'debug',
                   'connection': conn_record}
            for l in self._on_checkout:
                l.connection_checked_out(dic)

    def _notify_on_failure(self, error, server, connection=None):
        if self._on_failure:
            dic = {'pool_id': self.logging_name,
                   'level': 'info',
                   'error': error,
                   'server': server,
                   'connection': connection}
            for l in self._on_failure:
                l.connection_failed(dic)

QueuePool = ConnectionPool

class PoolListener(object):
    """Hooks into the lifecycle of connections in a :class:`ConnectionPool`.

    Usage::

        class MyListener(PoolListener):
            def connection_created(self, dic):
                '''perform connect operations'''
            # etc.

        # create a new pool with a listener
        p = ConnectionPool(..., listeners=[MyListener()])

        # or add a listener after the fact
        p.add_listener(MyListener())

    Listeners receive a dictionary that contains event information and
    is indexed by a string describing that piece of info.  For example,
    all event dictionaries include 'level', so dic['level'] will return
    the prescribed logging level.

    There is no need to subclass :class:`PoolListener` to handle events.
    Any class that implements one or more of these methods can be used
    as a pool listener.  The :class:`ConnectionPool` will inspect the methods
    provided by a listener object and add the listener to one or more
    internal event queues based on its capabilities.  In terms of
    efficiency and function call overhead, you're much better off only
    providing implementations for the hooks you'll be using.

    Each of the :class:`PoolListener` methods wil be called with a
    :class:`dict` as the single parameter. This :class:`dict` may
    contain the following fields:

        * `connection`: The :class:`ConnectionWrapper` object that persistently
          manages the connection

        * `message`: The reason this event happened

        * `error`: The :class:`Exception` that caused this event

        * `pool_id`: The id of the :class:`ConnectionPool` that this event came from

        * `level`: The prescribed logging level for this event.  Can be 'debug', 'info',
          'warn', 'error', or 'critical'

    Entries in the :class:`dict` that are specific to only one event type are
    detailed with each method.


    """

    def connection_created(self, dic):
        """Called once for each new Cassandra connection.

        Fields: `pool_id`, `level`, and `connection`.
        """

    def connection_checked_out(self, dic):
        """Called when a connection is retrieved from the Pool.

        Fields: `pool_id`, `level`, and `connection`.
        """

    def connection_checked_in(self, dic):
        """Called when a connection returns to the pool.

        Fields: `pool_id`, `level`, and `connection`.
        """

    def connection_disposed(self, dic):
        """Called when a connection is closed.

        ``dic['message']``: A reason for closing the connection, if any.

        Fields: `pool_id`, `level`, `connection`, and `message`.
        """

    def connection_recycled(self, dic):
        """Called when a connection is recycled.

        ``dic['old_conn']``: The :class:`ConnectionWrapper` that is being recycled

        ``dic['new_conn']``: The :class:`ConnectionWrapper` that is replacing it

        Fields: `pool_id`, `level`, `old_conn`, and `new_conn`.
        """

    def connection_failed(self, dic):
        """Called when a connection to a single server fails.

        ``dic['server']``: The server the connection was made to.

        Fields: `pool_id`, `level`, `error`, `server`, and `connection`.
        """
    def server_list_obtained(self, dic):
        """Called when the pool finalizes its server list.

        ``dic['server_list']``: The randomly permuted list of servers that the
        pool will choose from.

        Fields: `pool_id`, `level`, and `server_list`.
        """

    def pool_disposed(self, dic):
        """Called when a pool is disposed.

        Fields: `pool_id`, and `level`.
        """

    def pool_at_max(self, dic):
        """
        Called when an attempt is made to get a new connection from the
        pool, but the pool is already at its max size.

        ``dic['pool_max']``: The max number of connections the pool will
        keep open at one time.

        Fields: `pool_id`, `pool_max`, and `level`.
        """


class AllServersUnavailable(Exception):
    """Raised when none of the servers given to a pool can be connected to."""

class NoConnectionAvailable(Exception):
    """Raised when there are no connections left in a pool."""

class MaximumRetryException(Exception):
    """
    Raised when a :class:`ConnectionWrapper` has retried the maximum
    allowed times before being returned to the pool; note that all of
    the retries do not have to be on the same operation.
    """

class InvalidRequestError(Exception):
    """
    Pycassa was asked to do something it can't do.

    This error generally corresponds to runtime state errors.
    """

########NEW FILE########
__FILENAME__ = system_manager
import time

from pycassa.connection import (Connection, default_socket_factory,
        default_transport_factory)
from pycassa.cassandra.ttypes import IndexType, KsDef, CfDef, ColumnDef,\
                                     SchemaDisagreementException
import pycassa.marshal as marshal
import pycassa.types as types

_DEFAULT_TIMEOUT = 30
_SAMPLE_PERIOD = 0.25

SIMPLE_STRATEGY = 'SimpleStrategy'
""" Replication strategy that simply chooses consecutive nodes in the ring for replicas """

NETWORK_TOPOLOGY_STRATEGY = 'NetworkTopologyStrategy'
""" Replication strategy that puts a number of replicas in each datacenter """

OLD_NETWORK_TOPOLOGY_STRATEGY = 'OldNetworkTopologyStrategy'
"""
Original replication strategy for putting a number of replicas in each datacenter.
This was originally called 'RackAwareStrategy'.
"""

KEYS_INDEX = IndexType.KEYS
""" A secondary index type where each indexed value receives its own row """

BYTES_TYPE = types.BytesType()
LONG_TYPE = types.LongType()
INT_TYPE = types.IntegerType()
ASCII_TYPE = types.AsciiType()
UTF8_TYPE = types.UTF8Type()
TIME_UUID_TYPE = types.TimeUUIDType()
LEXICAL_UUID_TYPE = types.LexicalUUIDType()
COUNTER_COLUMN_TYPE = types.CounterColumnType()
DOUBLE_TYPE = types.DoubleType()
FLOAT_TYPE = types.FloatType()
DECIMAL_TYPE = types.DecimalType()
BOOLEAN_TYPE = types.BooleanType()
DATE_TYPE = types.DateType()

class SystemManager(object):
    """
    Lets you examine and modify schema definitions as well as get basic
    information about the cluster.

    This class is mainly designed to be used manually in a python shell,
    not as part of a program, although it can be used that way.

    All operations which modify a keyspace or column family definition
    will block until the cluster reports that all nodes have accepted
    the modification.

    Example Usage:

    .. code-block:: python

        >>> from pycassa.system_manager import *
        >>> sys = SystemManager('192.168.10.2:9160')
        >>> sys.create_keyspace('TestKeyspace', SIMPLE_STRATEGY, {'replication_factor': '1'})
        >>> sys.create_column_family('TestKeyspace', 'TestCF', super=False,
        ...                          comparator_type=LONG_TYPE)
        >>> sys.alter_column_family('TestKeyspace', 'TestCF', key_cache_size=42, gc_grace_seconds=1000)
        >>> sys.drop_keyspace('TestKeyspace')
        >>> sys.close()

    """

    def __init__(self, server='localhost:9160', credentials=None, framed_transport=True,
                 timeout=_DEFAULT_TIMEOUT, socket_factory=default_socket_factory,
                 transport_factory=default_transport_factory):
        self._conn = Connection(None, server, framed_transport, timeout,
                credentials, socket_factory, transport_factory)

    def close(self):
        """ Closes the underlying connection """
        self._conn.close()

    def get_keyspace_column_families(self, keyspace, use_dict_for_col_metadata=False):
        """
        Returns a raw description of the keyspace, which is more useful for use
        in programs than :meth:`describe_keyspace()`.

        If `use_dict_for_col_metadata` is ``True``, the CfDef's column_metadata will
        be stored as a dictionary where the keys are column names instead of a list.

        Returns a dictionary of the form ``{column_family_name: CfDef}``

        """
        if keyspace is None:
            keyspace = self._keyspace

        ks_def = self._conn.describe_keyspace(keyspace)
        cf_defs = dict()
        for cf_def in ks_def.cf_defs:
            cf_defs[cf_def.name] = cf_def
            if use_dict_for_col_metadata:
                old_metadata = cf_def.column_metadata
                new_metadata = dict()
                for datum in old_metadata:
                    new_metadata[datum.name] = datum
                cf_def.column_metadata = new_metadata
        return cf_defs

    def get_keyspace_properties(self, keyspace):
        """
        Gets a keyspace's properties.

        Returns a :class:`dict` with 'strategy_class' and
        'strategy_options' as keys.
        """
        if keyspace is None:
            keyspace = self._keyspace

        ks_def = self._conn.describe_keyspace(keyspace)
        return {'replication_strategy': ks_def.strategy_class,
                'strategy_options': ks_def.strategy_options}

    def list_keyspaces(self):
        """ Returns a list of all keyspace names. """
        return [ks.name for ks in self._conn.describe_keyspaces()]

    def describe_ring(self, keyspace):
        """ Describes the Cassandra cluster """
        return self._conn.describe_ring(keyspace)

    def describe_token_map(self):
        """ List tokens and their node assignments. """
        return self._conn.describe_token_map()

    def describe_cluster_name(self):
        """ Gives the cluster name """
        return self._conn.describe_cluster_name()

    def describe_version(self):
        """ Gives the server's API version """
        return self._conn.describe_version()

    def describe_schema_versions(self):
        """ Lists what schema version each node has """
        return self._conn.describe_schema_versions()

    def describe_partitioner(self):
        """ Gives the partitioner that the cluster is using """
        part = self._conn.describe_partitioner()
        return part[part.rfind('.') + 1:]

    def describe_snitch(self):
        """ Gives the snitch that the cluster is using """
        snitch = self._conn.describe_snitch()
        return snitch[snitch.rfind('.') + 1:]

    def _system_add_keyspace(self, ksdef):
        return self._schema_update(self._conn.system_add_keyspace, ksdef)

    def _system_update_keyspace(self, ksdef):
        return self._schema_update(self._conn.system_update_keyspace, ksdef)

    def create_keyspace(self, name,
                        replication_strategy=SIMPLE_STRATEGY,
                        strategy_options=None, durable_writes=True, **ks_kwargs):

        """
        Creates a new keyspace.  Column families may be added to this keyspace
        after it is created using :meth:`create_column_family()`.

        `replication_strategy` determines how replicas are chosen for this keyspace.
        The strategies that Cassandra provides by default
        are available as :const:`SIMPLE_STRATEGY`, :const:`NETWORK_TOPOLOGY_STRATEGY`,
        and :const:`OLD_NETWORK_TOPOLOGY_STRATEGY`.

        `strategy_options` is a dictionary of strategy options. For
        NetworkTopologyStrategy, the dictionary should look like
        ``{'Datacenter1': '2', 'Datacenter2': '1'}``. This maps each
        datacenter (as defined in a Cassandra property file) to a replica count.
        For SimpleStrategy, you can specify the replication factor as follows:
        ``{'replication_factor': '1'}``.

        Example Usage:

        .. code-block:: python

            >>> from pycassa.system_manager import *
            >>> sys = SystemManager('192.168.10.2:9160')
            >>> # Create a SimpleStrategy keyspace
            >>> sys.create_keyspace('SimpleKS', SIMPLE_STRATEGY, {'replication_factor': '1'})
            >>> # Create a NetworkTopologyStrategy keyspace
            >>> sys.create_keyspace('NTS_KS', NETWORK_TOPOLOGY_STRATEGY, {'DC1': '2', 'DC2': '1'})
            >>> sys.close()

        """

        if replication_strategy.find('.') == -1:
            strategy_class = 'org.apache.cassandra.locator.%s' % replication_strategy
        else:
            strategy_class = replication_strategy

        ksdef = KsDef(name, strategy_class=strategy_class,
                      strategy_options=strategy_options,
                      cf_defs=[],
                      durable_writes=durable_writes)

        for k, v in ks_kwargs.iteritems():
            setattr(ksdef, k, v)

        self._system_add_keyspace(ksdef)

    def alter_keyspace(self, keyspace, replication_strategy=None,
                       strategy_options=None, durable_writes=None, **ks_kwargs):

        """
        Alters an existing keyspace.

        .. warning:: Don't use this unless you know what you are doing.

        Parameters are the same as for :meth:`create_keyspace()`.

        """

        old_ksdef = self._conn.describe_keyspace(keyspace)
        old_durable = getattr(old_ksdef, 'durable_writes', True)
        ksdef = KsDef(name=old_ksdef.name,
                      strategy_class=old_ksdef.strategy_class,
                      strategy_options=old_ksdef.strategy_options,
                      cf_defs=[],
                      durable_writes=old_durable)

        if replication_strategy is not None:
            if replication_strategy.find('.') == -1:
                ksdef.strategy_class = 'org.apache.cassandra.locator.%s' % replication_strategy
            else:
                ksdef.strategy_class = replication_strategy
        if strategy_options is not None:
            ksdef.strategy_options = strategy_options
        if durable_writes is not None:
            ksdef.durable_writes = durable_writes

        for k, v in ks_kwargs.iteritems():
            setattr(ksdef, k, v)

        self._system_update_keyspace(ksdef)

    def drop_keyspace(self, keyspace):
        """
        Drops a keyspace from the cluster.

        """
        self._schema_update(self._conn.system_drop_keyspace, keyspace)

    def _system_add_column_family(self, cfdef):
        self._conn.set_keyspace(cfdef.keyspace)
        return self._schema_update(self._conn.system_add_column_family, cfdef)

    def create_column_family(self, keyspace, name, column_validation_classes=None, **cf_kwargs):

        """
        Creates a new column family in a given keyspace.  If a value is not
        supplied for any of optional parameters, Cassandra will use a reasonable
        default value.

        `keyspace` should be the name of the keyspace the column family will
        be created in. `name` gives the name of the column family.
        """

        self._conn.set_keyspace(keyspace)
        cfdef = CfDef()
        cfdef.keyspace = keyspace
        cfdef.name = name

        if cf_kwargs.pop('super', False):
            cf_kwargs.setdefault('column_type', 'Super')

        for k, v in cf_kwargs.iteritems():
            v = self._convert_class_attrs(k, v)
            setattr(cfdef, k, v)

        if column_validation_classes:
            for (colname, value_type) in column_validation_classes.items():
                cfdef = self._alter_column_cfdef(cfdef, colname, value_type)

        self._system_add_column_family(cfdef)

    def _system_update_column_family(self, cfdef):
        return self._schema_update(self._conn.system_update_column_family, cfdef)

    def alter_column_family(self, keyspace, column_family, column_validation_classes=None, **cf_kwargs):
        """
        Alters an existing column family.

        Parameter meanings are the same as for :meth:`create_column_family`.
        """

        self._conn.set_keyspace(keyspace)
        cfdef = self.get_keyspace_column_families(keyspace)[column_family]

        for k, v in cf_kwargs.iteritems():
            v = self._convert_class_attrs(k, v)
            setattr(cfdef, k, v)

        if column_validation_classes:
            for (colname, value_type) in column_validation_classes.items():
                cfdef = self._alter_column_cfdef(cfdef, colname, value_type)

        self._system_update_column_family(cfdef)

    def drop_column_family(self, keyspace, column_family):
        """
        Drops a column family from the keyspace.

        """
        self._conn.set_keyspace(keyspace)
        self._schema_update(self._conn.system_drop_column_family, column_family)

    def _convert_class_attrs(self, attr, value):
        if attr in ('comparator_type', 'subcomparator_type',
                    'key_validation_class', 'default_validation_class'):
            return self._qualify_type_class(value)
        else:
            return value

    def _qualify_type_class(self, classname):
        if classname:
            if isinstance(classname, types.CassandraType):
                s = str(classname)
            elif isinstance(classname, basestring):
                s = classname
            else:
                raise TypeError(
                        "Column family validators and comparators " \
                        "must be specified as instances of " \
                        "pycassa.types.CassandraType subclasses or strings.")

            if s.find('.') == -1:
                return 'org.apache.cassandra.db.marshal.%s' % s
            else:
                return s
        else:
            return None

    def _alter_column_cfdef(self, cfdef, column, value_type):
        if cfdef.column_type == 'Super':
            packer = marshal.packer_for(cfdef.subcomparator_type)
        else:
            packer = marshal.packer_for(cfdef.comparator_type)

        packed_column = packer(column)

        value_type = self._qualify_type_class(value_type)
        cfdef.column_metadata = cfdef.column_metadata or []
        matched = False
        for c in cfdef.column_metadata:
            if c.name == packed_column:
                c.validation_class = value_type
                matched = True
                break
        if not matched:
            cfdef.column_metadata.append(ColumnDef(packed_column, value_type, None, None))

        return cfdef

    def alter_column(self, keyspace, column_family, column, value_type):
        """
        Sets a data type for the value of a specific column.

        `value_type` is a string that determines what type the column value will be.
        By default, :const:`LONG_TYPE`, :const:`INT_TYPE`,
        :const:`ASCII_TYPE`, :const:`UTF8_TYPE`, :const:`TIME_UUID_TYPE`,
        :const:`LEXICAL_UUID_TYPE` and :const:`BYTES_TYPE` are provided.  Custom
        types may be used as well by providing the class name; if the custom
        comparator class is not in ``org.apache.cassandra.db.marshal``, the fully
        qualified class name must be given.

        For super column families, this sets the subcolumn value type for
        any subcolumn named `column`, regardless of the super column name.

        """

        self._conn.set_keyspace(keyspace)
        cfdef = self.get_keyspace_column_families(keyspace)[column_family]
        self._system_update_column_family(self._alter_column_cfdef(cfdef, column, value_type))

    def create_index(self, keyspace, column_family, column, value_type,
                     index_type=KEYS_INDEX, index_name=None):
        """
        Creates an index on a column.

        This allows efficient for index usage via
        :meth:`~pycassa.columnfamily.ColumnFamily.get_indexed_slices()`

        `column` specifies what column to index, and `value_type` is a string
        that describes that column's value's data type; see
        :meth:`alter_column()` for a full description of `value_type`.

        `index_type` determines how the index will be stored internally. Currently,
        :const:`KEYS_INDEX` is the only option.  `index_name` is an optional name
        for the index.

        Example Usage:

        .. code-block:: python

            >>> from pycassa.system_manager import *
            >>> sys = SystemManager('192.168.2.10:9160')
            >>> sys.create_index('Keyspace1', 'Standard1', 'birthdate', LONG_TYPE, index_name='bday_index')
            >>> sys.close

        """

        self._conn.set_keyspace(keyspace)
        cfdef = self.get_keyspace_column_families(keyspace)[column_family]

        packer = marshal.packer_for(cfdef.comparator_type)
        packed_column = packer(column)

        value_type = self._qualify_type_class(value_type)
        coldef = ColumnDef(packed_column, value_type, index_type, index_name)

        for c in cfdef.column_metadata:
            if c.name == packed_column:
                cfdef.column_metadata.remove(c)
                break
        cfdef.column_metadata.append(coldef)
        self._system_update_column_family(cfdef)

    def drop_index(self, keyspace, column_family, column):
        """
        Drops an index on a column.

        """
        self._conn.set_keyspace(keyspace)
        cfdef = self.get_keyspace_column_families(keyspace)[column_family]

        matched = False
        for c in cfdef.column_metadata:
            if c.name == column:
                c.index_type = None
                c.index_name = None
                matched = True
                break

        if matched:
            self._system_update_column_family(cfdef)

    def _wait_for_agreement(self):
        while True:
            versions = self._conn.describe_schema_versions()

            # ignore unreachable nodes
            live_versions = [key for key in versions.keys() if key != 'UNREACHABLE']

            if len(live_versions) == 1:
                break
            else:
                time.sleep(_SAMPLE_PERIOD)

    def _schema_update(self, schema_func, *args):
        """
        Call schema updates functions and properly
        waits for agreement if needed.
        """
        while True:
            try:
                schema_version = schema_func(*args)
            except SchemaDisagreementException:
                self._wait_for_agreement()
            else:
                break
        return schema_version

########NEW FILE########
__FILENAME__ = types
"""
Data type definitions that are used when converting data to and from
the binary format that the data will be stored in.

In addition to the default classes included here, you may also define
custom types by creating a new class that extends :class:`~.CassandraType`.
For example, IntString, which stores an arbitrary integer as a string, may
be defined as follows:

.. code-block:: python

    >>> class IntString(pycassa.types.CassandraType):
    ...
    ...    @staticmethod
    ...    def pack(intval):
    ...        return str(intval)
    ...
    ...    @staticmethod
    ...    def unpack(strval):
    ...        return int(strval)

"""

import calendar
from datetime import datetime

import pycassa.marshal as marshal

__all__ = ('CassandraType', 'BytesType', 'LongType', 'IntegerType',
           'AsciiType', 'UTF8Type', 'TimeUUIDType', 'LexicalUUIDType',
           'CounterColumnType', 'DoubleType', 'FloatType', 'DecimalType',
           'BooleanType', 'DateType', 'OldPycassaDateType',
           'IntermediateDateType', 'CompositeType',
           'UUIDType', 'DynamicCompositeType', 'TimestampType')

class CassandraType(object):
    """
    A data type that Cassandra is aware of and knows
    how to validate and sort. All of the other classes in this
    module are subclasses of this class.

    If `reversed` is true and this is used as a column comparator,
    the columns will be sorted in reverse order.


    The `default` parameter only applies to use of this
    with ColumnFamilyMap, where `default` is used if a row
    does not contain a column corresponding to this item.
    """

    def __init__(self, reversed=False, default=None):
        self.reversed = reversed
        self.default = default
        if not hasattr(self.__class__, 'pack'):
            self.pack = marshal.packer_for(self.__class__.__name__)
        if not hasattr(self.__class__, 'unpack'):
            self.unpack = marshal.unpacker_for(self.__class__.__name__)

    def __str__(self):
        return self.__class__.__name__ + "(reversed=" + str(self.reversed).lower() + ")"

class BytesType(CassandraType):
    """ Stores data as a byte array """
    pass

class LongType(CassandraType):
    """ Stores data as an 8 byte integer """
    pass

class IntegerType(CassandraType):
    """
    Stores data as a variable-length integer. This
    is a more compact format for storing small integers
    than :class:`~.LongType`, and the limits
    on the size of the integer are much higher.

    .. versionchanged:: 1.2.0
        Prior to 1.2.0, this was always stored as a 4 byte
        integer.

    """
    pass

class Int32Type(CassandraType):
    """ Stores data as a 4 byte integer """
    pass

class AsciiType(CassandraType):
    """ Stores data as ASCII text """
    pass

class UTF8Type(CassandraType):
    """ Stores data as UTF8 encoded text """
    pass

class UUIDType(CassandraType):
    """ Stores data as a type 1 or type 4 UUID """
    pass

class TimeUUIDType(CassandraType):
    """ Stores data as a version 1 UUID """
    pass

class LexicalUUIDType(CassandraType):
    """ Stores data as a non-version 1 UUID """
    pass

class CounterColumnType(CassandraType):
    """ A 64bit counter column """
    pass

class DoubleType(CassandraType):
    """ Stores data as an 8 byte double """
    pass

class FloatType(CassandraType):
    """ Stores data as a 4 byte float """
    pass

class DecimalType(CassandraType):
    """
    Stores an unlimited precision decimal number.  `decimal.Decimal`
    objects are used by pycassa to represent these objects.
    """
    pass

class BooleanType(CassandraType):
    """ Stores data as a 1 byte boolean """
    pass

class DateType(CassandraType):
    """
    An 8 byte timestamp. This will be returned
    as a :class:`datetime.datetime` instance by pycassa. Either
    :class:`datetime` instances or timestamps will be accepted.

    .. versionchanged:: 1.7.0
        Prior to 1.7.0, datetime objects were expected to be in
        local time. In 1.7.0 and beyond, naive datetimes are
        assumed to be in UTC and tz-aware objects will be
        automatically converted to UTC for storage in Cassandra.
    """
    pass

TimestampType = DateType


def _to_timestamp(v, use_micros=False):
    # Expects Value to be either date or datetime
    if use_micros:
        scale = 1e6
        micro_scale = 1.0
    else:
        scale = 1e3
        micro_scale = 1e3

    try:
        converted = calendar.timegm(v.utctimetuple())
        converted = (converted * scale) + \
                    (getattr(v, 'microsecond', 0) / micro_scale)
    except AttributeError:
        # Ints and floats are valid timestamps too
        if type(v) not in marshal._number_types:
            raise TypeError('DateType arguments must be a datetime or timestamp')

        converted = v * scale
    return long(converted)

class OldPycassaDateType(CassandraType):
    """
    This class can only read and write the DateType format
    used by pycassa versions 1.2.0 to 1.5.0.

    This formats store the number of microseconds since the
    unix epoch, rather than the number of milliseconds, which
    is what cassandra-cli and other clients supporting DateType
    use.

    .. versionchanged:: 1.7.0
        Prior to 1.7.0, datetime objects were expected to be in
        local time. In 1.7.0 and beyond, naive datetimes are
        assumed to be in UTC and tz-aware objects will be
        automatically converted to UTC for storage in Cassandra.
    """

    @staticmethod
    def pack(v, *args, **kwargs):
        ts = _to_timestamp(v, use_micros=True)
        return marshal._long_packer.pack(ts)

    @staticmethod
    def unpack(v):
        ts = marshal._long_packer.unpack(v)[0] / 1e6
        return datetime.utcfromtimestamp(ts)

class IntermediateDateType(CassandraType):
    """
    This class is capable of reading either the DateType
    format by pycassa versions 1.2.0 to 1.5.0 or the correct
    format used in pycassa 1.5.1+.  It will only write the
    new, correct format.

    This type is a good choice when you are using DateType
    as the validator for non-indexed column values and you are
    in the process of converting from thee old format to
    the new format.

    It almost certainly *should not be used* for row keys,
    column names (if you care about the sorting), or column
    values that have a secondary index on them.

    .. versionchanged:: 1.7.0
        Prior to 1.7.0, datetime objects were expected to be in
        local time. In 1.7.0 and beyond, naive datetimes are
        assumed to be in UTC and tz-aware objects will be
        automatically converted to UTC for storage in Cassandra.
    """

    @staticmethod
    def pack(v, *args, **kwargs):
        ts = _to_timestamp(v, use_micros=False)
        return marshal._long_packer.pack(ts)

    @staticmethod
    def unpack(v):
        raw_ts = marshal._long_packer.unpack(v)[0] / 1e3

        try:
            return datetime.utcfromtimestamp(raw_ts)
        except ValueError:
            # convert from bad microsecond format to millis
            corrected_ts = raw_ts / 1e3
            return datetime.utcfromtimestamp(corrected_ts)

class CompositeType(CassandraType):
    """
    A type composed of one or more components, each of
    which have their own type.  When sorted, items are
    primarily sorted by their first component, secondarily
    by their second component, and so on.

    Each of `*components` should be an instance of
    a subclass of :class:`CassandraType`.

    .. seealso:: :ref:`composite-types`

    """

    def __init__(self, *components):
        self.components = components

    def __str__(self):
        return "CompositeType(" + ", ".join(map(str, self.components)) + ")"

    @property
    def pack(self):
        return marshal.get_composite_packer(composite_type=self)

    @property
    def unpack(self):
        return marshal.get_composite_unpacker(composite_type=self)

class DynamicCompositeType(CassandraType):
    """
    A type composed of one or more components, each of
    which have their own type.  When sorted, items are
    primarily sorted by their first component, secondarily
    by their second component, and so on.

    Unlike CompositeType, DynamicCompositeType columns
    need not all be of the same structure. Each column
    can be composed of different component types.

    Components are specified using a 2-tuple made up of
    a comparator type and value. Aliases for comparator
    types can optionally be specified with a dictionary 
    during instantiation.

    """

    def __init__(self, *aliases):
        self.aliases = {}
        for alias in aliases:
            if isinstance(alias, dict):
                self.aliases.update(alias)

    def __str__(self):
        aliases = []
        for k, v in self.aliases.iteritems():
            aliases.append(k + '=>' + str(v))
        return "DynamicCompositeType(" + ", ".join(aliases) + ")"


########NEW FILE########
__FILENAME__ = util
"""
A combination of utilities used internally by pycassa and utilities
available for use by others working with pycassa.

"""

import random
import uuid
import calendar

__all__ = ['convert_time_to_uuid', 'convert_uuid_to_time', 'OrderedDict']

_number_types = frozenset((int, long, float))

LOWEST_TIME_UUID = uuid.UUID('00000000-0000-1000-8080-808080808080')
""" The lowest possible TimeUUID, as sorted by Cassandra. """

HIGHEST_TIME_UUID = uuid.UUID('ffffffff-ffff-1fff-bf7f-7f7f7f7f7f7f')
""" The highest possible TimeUUID, as sorted by Cassandra. """

def convert_time_to_uuid(time_arg, lowest_val=True, randomize=False):
    """
    Converts a datetime or timestamp to a type 1 :class:`uuid.UUID`.

    This is to assist with getting a time slice of columns or creating
    columns when column names are ``TimeUUIDType``. Note that this is done
    automatically in most cases if name packing and value packing are
    enabled.

    Also, be careful not to rely on this when specifying a discrete
    set of columns to fetch, as the non-timestamp portions of the
    UUID will be generated randomly. This problem does not matter
    with slice arguments, however, as the non-timestamp portions
    can be set to their lowest or highest possible values.

    :param datetime:
      The time to use for the timestamp portion of the UUID.
      Expected inputs to this would either be a :class:`datetime`
      object or a timestamp with the same precision produced by
      :meth:`time.time()`. That is, sub-second precision should
      be below the decimal place.
    :type datetime: :class:`datetime` or timestamp

    :param lowest_val:
      Whether the UUID produced should be the lowest possible value
      UUID with the same timestamp as datetime or the highest possible
      value.
    :type lowest_val: bool

    :param randomize:
      Whether the clock and node bits of the UUID should be randomly
      generated.  The `lowest_val` argument will be ignored if this
      is true.
    :type randomize: bool

    :rtype: :class:`uuid.UUID`

    .. versionchanged:: 1.7.0
        Prior to 1.7.0, datetime objects were expected to be in
        local time. In 1.7.0 and beyond, naive datetimes are
        assumed to be in UTC and tz-aware objects will be
        automatically converted to UTC.

    """
    if isinstance(time_arg, uuid.UUID):
        return time_arg

    if hasattr(time_arg, 'utctimetuple'):
        seconds = int(calendar.timegm(time_arg.utctimetuple()))
        microseconds = (seconds * 1e6) + time_arg.time().microsecond
    elif type(time_arg) in _number_types:
        microseconds = int(time_arg * 1e6)
    else:
        raise ValueError('Argument for a v1 UUID column name or value was ' +
                'neither a UUID, a datetime, or a number')

    # 0x01b21dd213814000 is the number of 100-ns intervals between the
    # UUID epoch 1582-10-15 00:00:00 and the Unix epoch 1970-01-01 00:00:00.
    timestamp = int(microseconds * 10) + 0x01b21dd213814000L

    time_low = timestamp & 0xffffffffL
    time_mid = (timestamp >> 32L) & 0xffffL
    time_hi_version = (timestamp >> 48L) & 0x0fffL

    if randomize:
        rand_bits = random.getrandbits(8 + 8 + 48)
        clock_seq_low = rand_bits & 0xffL  # 8 bits, no offset
        # keep the first two bits as 10 for the uuid variant
        clock_seq_hi_variant = 0b10000000 | (0b00111111 & ((rand_bits & 0xff00L) >> 8))  # 8 bits, 8 offset
        node = (rand_bits & 0xffffffffffff0000L) >> 16  # 48 bits, 16 offset
    else:
        # In the event of a timestamp tie, Cassandra compares the two
        # byte arrays directly. This is a *signed* comparison of each byte
        # in the two arrays.  So, we have to make each byte -128 or +127 for
        # this to work correctly.
        #
        # For the clock_seq_hi_variant, we don't get to pick the two most
        # significant bits (they're always 10), so we are dealing with a
        # positive byte range for this particular byte.
        if lowest_val:
            # Make the lowest value UUID with the same timestamp
            clock_seq_low = 0x80L
            clock_seq_hi_variant = 0 & 0x80L # The two most significant bits
                                             # will be 10 for the variant
            node = 0x808080808080L # 48 bits
        else:
            # Make the highest value UUID with the same timestamp

            # uuid timestamps have 100ns precision, while the timestamp
            # we have only has microsecond precision; to create the highest
            # uuid for the same microsecond, add 900ns
            timestamp = int(timestamp + 9)

            clock_seq_low = 0x7fL
            clock_seq_hi_variant = 0xbfL # The two most significant bits will
                                         # 10 for the variant
            node = 0x7f7f7f7f7f7fL # 48 bits
    return uuid.UUID(fields=(time_low, time_mid, time_hi_version,
                        clock_seq_hi_variant, clock_seq_low, node), version=1)

def convert_uuid_to_time(uuid_arg):
    """
    Converts a version 1 :class:`uuid.UUID` to a timestamp with the same precision
    as :meth:`time.time()` returns.  This is useful for examining the
    results of queries returning a v1 :class:`~uuid.UUID`.

    :param uuid_arg: a version 1 :class:`~uuid.UUID`

    :rtype: timestamp

    """
    ts = uuid_arg.get_time()
    return (ts - 0x01b21dd213814000L)/1e7

# Copyright (C) 2005, 2006, 2007, 2008, 2009, 2010 Michael Bayer mike_mp@zzzcomputing.com
#
# The 'as_interface' method is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import operator

def as_interface(obj, cls=None, methods=None, required=None):
    """Ensure basic interface compliance for an instance or dict of callables.

    Checks that ``obj`` implements public methods of ``cls`` or has members
    listed in ``methods``.  If ``required`` is not supplied, implementing at
    least one interface method is sufficient.  Methods present on ``obj`` that
    are not in the interface are ignored.

    If ``obj`` is a dict and ``dict`` does not meet the interface
    requirements, the keys of the dictionary are inspected. Keys present in
    ``obj`` that are not in the interface will raise TypeErrors.

    Raises TypeError if ``obj`` does not meet the interface criteria.

    In all passing cases, an object with callable members is returned.  In the
    simple case, ``obj`` is returned as-is; if dict processing kicks in then
    an anonymous class is returned.

    obj
      A type, instance, or dictionary of callables.
    cls
      Optional, a type.  All public methods of cls are considered the
      interface.  An ``obj`` instance of cls will always pass, ignoring
      ``required``..
    methods
      Optional, a sequence of method names to consider as the interface.
    required
      Optional, a sequence of mandatory implementations. If omitted, an
      ``obj`` that provides at least one interface method is considered
      sufficient.  As a convenience, required may be a type, in which case
      all public methods of the type are required.

    """
    if not cls and not methods:
        raise TypeError('a class or collection of method names are required')

    if isinstance(cls, type) and isinstance(obj, cls):
        return obj

    interface = set(methods or [m for m in dir(cls) if not m.startswith('_')])
    implemented = set(dir(obj))

    complies = operator.ge
    if isinstance(required, type):
        required = interface
    elif not required:
        required = set()
        complies = operator.gt
    else:
        required = set(required)

    if complies(implemented.intersection(interface), required):
        return obj

    # No dict duck typing here.
    if not type(obj) is dict:
        qualifier = complies is operator.gt and 'any of' or 'all of'
        raise TypeError("%r does not implement %s: %s" % (
            obj, qualifier, ', '.join(interface)))

    class AnonymousInterface(object):
        """A callable-holding shell."""

    if cls:
        AnonymousInterface.__name__ = 'Anonymous' + cls.__name__
    found = set()

    for method, impl in dictlike_iteritems(obj):
        if method not in interface:
            raise TypeError("%r: unknown in this interface" % method)
        if not callable(impl):
            raise TypeError("%r=%r is not callable" % (method, impl))
        setattr(AnonymousInterface, method, staticmethod(impl))
        found.add(method)

    if complies(found, required):
        return AnonymousInterface

    raise TypeError("dictionary does not contain required keys %s" %
                    ', '.join(required - found))


# Copyright (c) 2009 Raymond Hettinger
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
#     The above copyright notice and this permission notice shall be
#     included in all copies or substantial portions of the Software.
#
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#     OTHER DEALINGS IN THE SOFTWARE.

from UserDict import DictMixin

class OrderedDict(dict, DictMixin):
    """ A dictionary which maintains the insertion order of keys. """

    def __init__(self, *args, **kwds):
        """ A dictionary which maintains the insertion order of keys. """

        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        if last:
            key = reversed(self).next()
        else:
            key = iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            if len(self) != len(other):
                return False
            for p, q in  zip(self.items(), other.items()):
                if p != q:
                    return False
            return True
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

########NEW FILE########
__FILENAME__ = stubs
import unittest
import time

from nose.tools import assert_raises, assert_equal, assert_true

from pycassa import index, ColumnFamily, ConnectionPool,\
                    NotFoundException
from pycassa.contrib.stubs import ColumnFamilyStub, ConnectionPoolStub
from pycassa.util import convert_time_to_uuid

pool = cf = indexed_cf = None
pool_stub = cf_stub = indexed_cf_stub = None


def setup_module():
    global pool, cf, indexed_cf, pool_stub, indexed_cf_stub, cf_stub
    credentials = {'username': 'jsmith', 'password': 'havebadpass'}
    pool = ConnectionPool(keyspace='PycassaTestKeyspace',
            credentials=credentials, timeout=1.0)
    cf = ColumnFamily(pool, 'Standard1', dict_class=TestDict)
    indexed_cf = ColumnFamily(pool, 'Indexed1')

    pool_stub = ConnectionPoolStub(keyspace='PycassaTestKeyspace',
            credentials=credentials, timeout=1.0)
    cf_stub = ColumnFamilyStub(pool_stub, 'Standard1', dict_class=TestDict)
    indexed_cf_stub = ColumnFamilyStub(pool_stub, 'Indexed1')


def teardown_module():
    cf.truncate()
    cf_stub.truncate()
    indexed_cf.truncate()
    indexed_cf_stub.truncate()
    pool.dispose()


class TestDict(dict):
    pass


class TestColumnFamilyStub(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        for test_cf in (cf, cf_stub):
            for key, columns in test_cf.get_range():
                test_cf.remove(key)

    def test_empty(self):
        key = 'TestColumnFamily.test_empty'

        for test_cf in (cf, cf_stub):
            assert_raises(NotFoundException, test_cf.get, key)
            assert_equal(len(test_cf.multiget([key])), 0)
            for key, columns in test_cf.get_range():
                assert_equal(len(columns), 0)

    def test_insert_get(self):
        key = 'TestColumnFamily.test_insert_get'
        columns = {'1': 'val1', '2': 'val2'}
        for test_cf in (cf, cf_stub):
            assert_raises(NotFoundException, test_cf.get, key)
            ts = test_cf.insert(key, columns)
            assert_true(isinstance(ts, (int, long)))
            assert_equal(test_cf.get(key), columns)

    def test_insert_get_column_start_and_finish_reversed(self):
        key = 'TestColumnFamily.test_insert_get_reversed'
        columns = {'1': 'val1', '2': 'val2'}
        for test_cf in (cf, cf_stub):
            assert_raises(NotFoundException, test_cf.get, key)
            ts = test_cf.insert(key, columns)
            assert_true(isinstance(ts, (int, long)))
            test_cf.get(key, column_reversed=True)

    def test_insert_get_column_start_and_finish(self):
        key = 'TestColumnFamily.test_insert_get_column_start_and_finish'
        columns = {'a': 'val1', 'b': 'val2', 'c': 'val3', 'd': 'val4'}
        for test_cf in (cf, cf_stub):
            assert_raises(NotFoundException, test_cf.get, key)
            ts = test_cf.insert(key, columns)
            assert_true(isinstance(ts, (int, long)))
            assert_equal(test_cf.get(key, column_start='b', column_finish='c'), {'b': 'val2', 'c': 'val3'})

    def test_insert_get_column_start_and_reversed(self):
        key = 'TestColumnFamily.test_insert_get_column_start_and_finish_reversed'
        columns = {'a': 'val1', 'b': 'val2', 'c': 'val3', 'd': 'val4'}
        for test_cf in (cf, cf_stub):
            assert_raises(NotFoundException, test_cf.get, key)
            ts = test_cf.insert(key, columns)
            assert_true(isinstance(ts, (int, long)))
            assert_equal(test_cf.get(key, column_start='b', column_reversed=True), {'b': 'val2', 'a': 'val1'})

    def test_insert_get_column_count(self):
        key = 'TestColumnFamily.test_insert_get_column_count'
        columns = {'a': 'val1', 'b': 'val2', 'c': 'val3', 'd': 'val4'}
        for test_cf in (cf, cf_stub):
            assert_raises(NotFoundException, test_cf.get, key)
            ts = test_cf.insert(key, columns)
            assert_true(isinstance(ts, (int, long)))
            assert_equal(test_cf.get(key, column_count=3), {'a': 'val1', 'b': 'val2', 'c': 'val3'})

    def test_insert_get_default_column_count(self):
        keys = [str(i) for i in range(1000)]
        keys.sort()
        keys_and_values = [(key, key) for key in keys]
        key = 'TestColumnFamily.test_insert_get_default_column_count'

        for test_cf in (cf, cf_stub):
            assert_raises(NotFoundException, test_cf.get, key)
            test_cf.insert(key, dict(key_value for key_value in keys_and_values))
            assert_equal(test_cf.get(key), dict([key_value for key_value in keys_and_values][:100]))

    def test_insert_multiget(self):
        key1 = 'TestColumnFamily.test_insert_multiget1'
        columns1 = {'1': 'val1', '2': 'val2'}
        key2 = 'test_insert_multiget1'
        columns2 = {'3': 'val1', '4': 'val2'}
        missing_key = 'key3'

        for test_cf in (cf, cf_stub):
            test_cf.insert(key1, columns1)
            test_cf.insert(key2, columns2)
            rows = test_cf.multiget([key1, key2, missing_key])
            assert_equal(len(rows), 2)
            assert_equal(rows[key1], columns1)
            assert_equal(rows[key2], columns2)
            assert_true(missing_key not in rows)

    def test_insert_multiget_column_start_and_finish(self):
        key1 = 'TestColumnFamily.test_insert_multiget_column_start_and_finish1'
        columns1 = {'1': 'val1', '2': 'val2'}
        key2 = 'TestColumnFamily.test_insert_multiget_column_start_and_finish2'
        columns2 = {'3': 'val1', '4': 'val2'}
        missing_key = 'key3'

        for test_cf in (cf, cf_stub):
            test_cf.insert(key1, columns1)
            test_cf.insert(key2, columns2)
            rows = test_cf.multiget([key1, key2, missing_key], column_start='2', column_finish='3')
            assert_equal(len(rows), 2)
            assert_equal(rows[key1], {'2': 'val2'})
            assert_equal(rows[key2], {'3': 'val1'})
            assert_true(missing_key not in rows)

    def test_insert_multiget_column_finish_and_reversed(self):
        key1 = 'TestColumnFamily.test_insert_multiget_column_finish_and_reversed1'
        columns1 = {'1': 'val1', '3': 'val2'}
        key2 = 'TestColumnFamily.test_insert_multiget_column_finish_and_reversed2'
        columns2 = {'5': 'val1', '7': 'val2'}
        missing_key = 'key3'

        for test_cf in (cf, cf_stub):
            test_cf.insert(key1, columns1)
            test_cf.insert(key2, columns2)
            rows = test_cf.multiget([key1, key2, missing_key], column_finish='3', column_reversed=True)
            assert_equal(len(rows), 2)
            assert_equal(rows[key1], {'3': 'val2'})
            assert_equal(rows[key2], {'5': 'val1', '7': 'val2'})
            assert_true(missing_key not in rows)

    def test_insert_multiget_column_start_column_count(self):
        key1 = 'TestColumnFamily.test_insert_multiget_column_start_column_count'
        columns1 = {'1': 'val1', '2': 'val2'}
        key2 = 'test_insert_multiget1'
        columns2 = {'3': 'val1', '4': 'val2'}
        missing_key = 'key3'

        for test_cf in (cf, cf_stub):
            test_cf.insert(key1, columns1)
            test_cf.insert(key2, columns2)
            rows = test_cf.multiget([key1, key2, missing_key], column_count=1, column_start='2')
            assert_equal(len(rows), 2)
            assert_equal(rows[key1], {'2': 'val2'})
            assert_equal(rows[key2], {'3': 'val1'})
            assert_true(missing_key not in rows)

    def test_insert_multiget_default_column_count(self):
        keys = [str(i) for i in range(1000)]
        keys.sort()
        keys_and_values = [(key, key) for key in keys]
        key = 'TestColumnFamily.test_insert_multiget_default_column_count'

        for test_cf in (cf, cf_stub):
            test_cf.insert(key, dict(key_value for key_value in keys_and_values))
            rows = test_cf.multiget([key])
            assert_equal(len(rows), 1)
            assert_equal(rows[key], dict([key_value for key_value in keys_and_values][:100]))

    def insert_insert_get_indexed_slices(self):
        columns = {'birthdate': 1L}

        keys = set()
        for i in range(1, 4):
            indexed_cf.insert('key%d' % i, columns)
            indexed_cf_stub.insert('key%d' % i, columns)
            keys.add('key%d' % i)

        expr = index.create_index_expression(column_name='birthdate', value=1L)
        clause = index.create_index_clause([expr])

        for test_indexed_cf in (indexed_cf, indexed_cf_stub):
            count = 0
            for key, cols in test_indexed_cf.get_indexed_slices(clause):
                assert_equal(cols, columns)
                assert key in keys
                count += 1
            assert_equal(count, 3)

    def test_remove(self):
        key = 'TestColumnFamily.test_remove'
        for test_cf in (cf, cf_stub):
            columns = {'1': 'val1', '2': 'val2'}
            test_cf.insert(key, columns)

            # An empty list for columns shouldn't delete anything
            test_cf.remove(key, columns=[])
            assert_equal(test_cf.get(key), columns)

            test_cf.remove(key, columns=['2'])
            del columns['2']
            assert_equal(test_cf.get(key), {'1': 'val1'})

            test_cf.remove(key)
            assert_raises(NotFoundException, test_cf.get, key)

    def test_insert_get_tuuids(self):
        key = 'TestColumnFamily.test_insert_get'
        columns = ((convert_time_to_uuid(time.time() - 1000, randomize=True), 'val1'),
                   (convert_time_to_uuid(time.time(), randomize=True), 'val2'))
        for test_cf in (cf, cf_stub):
            assert_raises(NotFoundException, test_cf.get, key)
            ts = test_cf.insert(key, dict(columns))
            assert_true(isinstance(ts, (int, long)))
            assert_equal(test_cf.get(key).keys(), [x[0] for x in columns])

########NEW FILE########
__FILENAME__ = test_autopacking
from pycassa import NotFoundException
from pycassa.pool import ConnectionPool
from pycassa.columnfamily import ColumnFamily
from pycassa.util import OrderedDict, convert_uuid_to_time
from pycassa.system_manager import SystemManager
from pycassa.types import (LongType, IntegerType, TimeUUIDType, LexicalUUIDType,
                           AsciiType, UTF8Type, BytesType, CompositeType,
                           OldPycassaDateType, IntermediateDateType, DateType,
                           BooleanType, CassandraType, DecimalType,
                           FloatType, Int32Type, UUIDType, DoubleType, DynamicCompositeType)
from pycassa.index import create_index_expression, create_index_clause
import pycassa.marshal as marshal

from nose import SkipTest
from nose.tools import (assert_raises, assert_equal, assert_almost_equal,
                        assert_true)

from datetime import date, datetime
from uuid import uuid1
from decimal import Decimal
import uuid
import unittest
import time
from collections import namedtuple

TIME1 = uuid.UUID(hex='ddc6118e-a003-11df-8abf-00234d21610a')
TIME2 = uuid.UUID(hex='40ad6d4c-a004-11df-8abf-00234d21610a')
TIME3 = uuid.UUID(hex='dc3d5234-a00b-11df-8abf-00234d21610a')

VALS = ['val1', 'val2', 'val3']
KEYS = ['key1', 'key2', 'key3']

pool = None
TEST_KS = 'PycassaTestKeyspace'

def setup_module():
    global pool
    credentials = {'username': 'jsmith', 'password': 'havebadpass'}
    pool = ConnectionPool(TEST_KS, pool_size=10, credentials=credentials, timeout=1.0)

def teardown_module():
    pool.dispose()

class TestCFs(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'StdLong', comparator_type=LongType())
        sys.create_column_family(TEST_KS, 'StdInteger', comparator_type=IntegerType())
        sys.create_column_family(TEST_KS, 'StdBigInteger', comparator_type=IntegerType())
        sys.create_column_family(TEST_KS, 'StdDecimal', comparator_type=DecimalType())
        sys.create_column_family(TEST_KS, 'StdTimeUUID', comparator_type=TimeUUIDType())
        sys.create_column_family(TEST_KS, 'StdLexicalUUID', comparator_type=LexicalUUIDType())
        sys.create_column_family(TEST_KS, 'StdAscii', comparator_type=AsciiType())
        sys.create_column_family(TEST_KS, 'StdUTF8', comparator_type=UTF8Type())
        sys.create_column_family(TEST_KS, 'StdBytes', comparator_type=BytesType())
        sys.create_column_family(TEST_KS, 'StdComposite',
                                 comparator_type=CompositeType(LongType(), BytesType()))
        sys.create_column_family(TEST_KS, 'StdDynamicComposite',
                                 comparator_type=DynamicCompositeType({'a': AsciiType(),
                                 'b': BytesType(), 'c': DecimalType(), 'd': DateType(),
                                 'f': FloatType(), 'i': IntegerType(), 'l': LongType(),
                                 'n': Int32Type(), 's': UTF8Type(), 't': TimeUUIDType(),
                                 'u': UUIDType(), 'w': DoubleType(), 'x': LexicalUUIDType(),
                                 'y': BooleanType()}))
        sys.close()

        cls.cf_long = ColumnFamily(pool, 'StdLong')
        cls.cf_int = ColumnFamily(pool, 'StdInteger')
        cls.cf_big_int = ColumnFamily(pool, 'StdBigInteger')
        cls.cf_decimal = ColumnFamily(pool, 'StdDecimal')
        cls.cf_time = ColumnFamily(pool, 'StdTimeUUID')
        cls.cf_lex = ColumnFamily(pool, 'StdLexicalUUID')
        cls.cf_ascii = ColumnFamily(pool, 'StdAscii')
        cls.cf_utf8 = ColumnFamily(pool, 'StdUTF8')
        cls.cf_bytes = ColumnFamily(pool, 'StdBytes')
        cls.cf_composite = ColumnFamily(pool, 'StdComposite')
        cls.cf_dynamic_composite = ColumnFamily(pool, 'StdDynamicComposite')

        cls.cfs = [cls.cf_long, cls.cf_int, cls.cf_time, cls.cf_lex,
                   cls.cf_ascii, cls.cf_utf8, cls.cf_bytes, cls.cf_composite, 
                   cls.cf_dynamic_composite]

    def tearDown(self):
        for cf in TestCFs.cfs:
            for key, cols in cf.get_range():
                cf.remove(key)

    def make_group(self, cf, cols):
        diction = OrderedDict([(cols[0], VALS[0]),
                               (cols[1], VALS[1]),
                               (cols[2], VALS[2])])
        return {'cf': cf, 'cols': cols, 'dict': diction}

    def test_standard_column_family(self):

        # For each data type, create a group that includes its column family,
        # a set of column names, and a dictionary that maps from the column
        # names to values.
        type_groups = []

        long_cols = [1111111111111111L,
                     2222222222222222L,
                     3333333333333333L]
        type_groups.append(self.make_group(TestCFs.cf_long, long_cols))

        int_cols = [1, 2, 3]
        type_groups.append(self.make_group(TestCFs.cf_int, int_cols))

        big_int_cols = [1 + int(time.time() * 10 ** 6),
                        2 + int(time.time() * 10 ** 6),
                        3 + int(time.time() * 10 ** 6)]
        type_groups.append(self.make_group(TestCFs.cf_big_int, big_int_cols))

        decimal_cols = [Decimal('1.123456789123456789'),
                        Decimal('2.123456789123456789'),
                        Decimal('3.123456789123456789')]
        type_groups.append(self.make_group(TestCFs.cf_decimal, decimal_cols))

        time_cols = [TIME1, TIME2, TIME3]
        type_groups.append(self.make_group(TestCFs.cf_time, time_cols))

        lex_cols = [uuid.UUID(bytes='aaa aaa aaa aaaa'),
                    uuid.UUID(bytes='bbb bbb bbb bbbb'),
                    uuid.UUID(bytes='ccc ccc ccc cccc')]
        type_groups.append(self.make_group(TestCFs.cf_lex, lex_cols))

        ascii_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_group(TestCFs.cf_ascii, ascii_cols))

        utf8_cols = [u'a\u0020', u'b\u0020', u'c\u0020']
        type_groups.append(self.make_group(TestCFs.cf_utf8, utf8_cols))

        bytes_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_group(TestCFs.cf_bytes, bytes_cols))

        composite_cols = [(1, 'foo'), (2, 'bar'), (3, 'baz')]
        type_groups.append(self.make_group(TestCFs.cf_composite, composite_cols))

        dynamic_composite_cols = [(('LongType', 1), ('BytesType', 'foo')), 
                                  (('LongType', 2), ('BytesType', 'bar')), 
                                  (('LongType', 3), ('BytesType', 'baz'))]
        type_groups.append(self.make_group(TestCFs.cf_dynamic_composite, dynamic_composite_cols))

        dynamic_composite_alias_cols = [(('l', 1), ('b', 'foo')), 
                                        (('l', 2), ('b', 'bar')), 
                                        (('l', 3), ('b', 'baz'))]
        type_groups.append(self.make_group(TestCFs.cf_dynamic_composite, dynamic_composite_alias_cols))

        # Begin the actual inserting and getting	
        for group in type_groups:
            cf = group.get('cf')
            gdict = group.get('dict')
            gcols = group.get('cols')

            cf.insert(KEYS[0], gdict)
            assert_equal(cf.get(KEYS[0]), gdict)

            # Check each column individually
            for i in range(3):
                assert_equal(cf.get(KEYS[0], columns=[gcols[i]]),
                             {gcols[i]: VALS[i]})

            # Check that if we list all columns, we get the full dict
            assert_equal(cf.get(KEYS[0], columns=gcols[:]), gdict)
            # The same thing with a start and end instead
            assert_equal(cf.get(KEYS[0], column_start=gcols[0], column_finish=gcols[2]),
                         gdict)
            # A start and end that are the same
            assert_equal(cf.get(KEYS[0], column_start=gcols[0], column_finish=gcols[0]),
                         {gcols[0]: VALS[0]})

            assert_equal(cf.get_count(KEYS[0]), 3)

            # Test xget paging
            assert_equal(list(cf.xget(KEYS[0], buffer_size=2)), gdict.items())
            assert_equal(list(cf.xget(KEYS[0], column_reversed=True, buffer_size=2)),
                         list(reversed(gdict.items())))
            assert_equal(list(cf.xget(KEYS[0], column_start=gcols[0], buffer_size=2)),
                         gdict.items())
            assert_equal(list(cf.xget(KEYS[0], column_finish=gcols[2], buffer_size=2)),
                         gdict.items())
            assert_equal(list(cf.xget(KEYS[0], column_start=gcols[2], column_finish=gcols[0],
                                      column_reversed=True, buffer_size=2)),
                         list(reversed(gdict.items())))
            assert_equal(list(cf.xget(KEYS[0], column_start=gcols[1], column_finish=gcols[1],
                                      column_reversed=True, buffer_size=2)),
                         [(gcols[1], VALS[1])])

            # Test removing rows
            cf.remove(KEYS[0], columns=gcols[:1])
            assert_equal(cf.get_count(KEYS[0]), 2)

            cf.remove(KEYS[0], columns=gcols[1:])
            assert_equal(cf.get_count(KEYS[0]), 0)

            # Insert more than one row now
            cf.insert(KEYS[0], gdict)
            cf.insert(KEYS[1], gdict)
            cf.insert(KEYS[2], gdict)

            ### multiget() tests ###

            res = cf.multiget(KEYS[:])
            for i in range(3):
                assert_equal(res.get(KEYS[i]), gdict)

            res = cf.multiget(KEYS[2:])
            assert_equal(res.get(KEYS[2]), gdict)

            # Check each column individually
            for i in range(3):
                res = cf.multiget(KEYS[:], columns=[gcols[i]])
                for j in range(3):
                    assert_equal(res.get(KEYS[j]), {gcols[i]: VALS[i]})

            # Check that if we list all columns, we get the full dict
            res = cf.multiget(KEYS[:], columns=gcols[:])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), gdict)

            # The same thing with a start and end instead
            res = cf.multiget(KEYS[:], column_start=gcols[0], column_finish=gcols[2])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), gdict)

            # A start and end that are the same
            res = cf.multiget(KEYS[:], column_start=gcols[0], column_finish=gcols[0])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), {gcols[0]: VALS[0]})

            ### get_range() tests ###

            res = cf.get_range(start=KEYS[0])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], column_start=gcols[0], column_finish=gcols[2])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], columns=gcols[:])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)


class TestSuperCFs(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'SuperLong', super=True, comparator_type=LongType())
        sys.create_column_family(TEST_KS, 'SuperInt', super=True, comparator_type=IntegerType())
        sys.create_column_family(TEST_KS, 'SuperBigInt', super=True, comparator_type=IntegerType())
        sys.create_column_family(TEST_KS, 'SuperTime', super=True, comparator_type=TimeUUIDType())
        sys.create_column_family(TEST_KS, 'SuperLex', super=True, comparator_type=LexicalUUIDType())
        sys.create_column_family(TEST_KS, 'SuperAscii', super=True, comparator_type=AsciiType())
        sys.create_column_family(TEST_KS, 'SuperUTF8', super=True, comparator_type=UTF8Type())
        sys.create_column_family(TEST_KS, 'SuperBytes', super=True, comparator_type=BytesType())
        sys.close()

        cls.cf_suplong = ColumnFamily(pool, 'SuperLong')
        cls.cf_supint = ColumnFamily(pool, 'SuperInt')
        cls.cf_supbigint = ColumnFamily(pool, 'SuperBigInt')
        cls.cf_suptime = ColumnFamily(pool, 'SuperTime')
        cls.cf_suplex = ColumnFamily(pool, 'SuperLex')
        cls.cf_supascii = ColumnFamily(pool, 'SuperAscii')
        cls.cf_suputf8 = ColumnFamily(pool, 'SuperUTF8')
        cls.cf_supbytes = ColumnFamily(pool, 'SuperBytes')

        cls.cfs = [cls.cf_suplong, cls.cf_supint, cls.cf_suptime,
                   cls.cf_suplex, cls.cf_supascii, cls.cf_suputf8,
                   cls.cf_supbytes]

    def tearDown(self):
        for cf in TestSuperCFs.cfs:
            for key, cols in cf.get_range():
                cf.remove(key)

    def make_super_group(self, cf, cols):
        diction = OrderedDict([(cols[0], {'bytes': VALS[0]}),
                               (cols[1], {'bytes': VALS[1]}),
                               (cols[2], {'bytes': VALS[2]})])
        return {'cf': cf, 'cols': cols, 'dict': diction}

    def test_super_column_families(self):

        # For each data type, create a group that includes its column family,
        # a set of column names, and a dictionary that maps from the column
        # names to values.
        type_groups = []

        long_cols = [1111111111111111L,
                     2222222222222222L,
                     3333333333333333L]
        type_groups.append(self.make_super_group(TestSuperCFs.cf_suplong, long_cols))

        int_cols = [1, 2, 3]
        type_groups.append(self.make_super_group(TestSuperCFs.cf_supint, int_cols))

        big_int_cols = [1 + int(time.time() * 10 ** 6),
                        2 + int(time.time() * 10 ** 6),
                        3 + int(time.time() * 10 ** 6)]
        type_groups.append(self.make_super_group(TestSuperCFs.cf_supbigint, big_int_cols))

        time_cols = [TIME1, TIME2, TIME3]
        type_groups.append(self.make_super_group(TestSuperCFs.cf_suptime, time_cols))

        lex_cols = [uuid.UUID(bytes='aaa aaa aaa aaaa'),
                    uuid.UUID(bytes='bbb bbb bbb bbbb'),
                    uuid.UUID(bytes='ccc ccc ccc cccc')]
        type_groups.append(self.make_super_group(TestSuperCFs.cf_suplex, lex_cols))

        ascii_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_super_group(TestSuperCFs.cf_supascii, ascii_cols))

        utf8_cols = [u'a\u0020', u'b\u0020', u'c\u0020']
        type_groups.append(self.make_super_group(TestSuperCFs.cf_suputf8, utf8_cols))

        bytes_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_super_group(TestSuperCFs.cf_supbytes, bytes_cols))

        # Begin the actual inserting and getting
        for group in type_groups:
            cf = group.get('cf')
            gdict = group.get('dict')
            gcols = group.get('cols')

            cf.insert(KEYS[0], gdict)
            assert_equal(cf.get(KEYS[0]), gdict)

            # Check each supercolumn individually
            for i in range(3):
                res = cf.get(KEYS[0], columns=[gcols[i]])
                assert_equal(res, {gcols[i]: {'bytes': VALS[i]}})

            # Check that if we list all columns, we get the full dict
            assert_equal(cf.get(KEYS[0], columns=gcols[:]), gdict)
            # The same thing with a start and end instead
            assert_equal(cf.get(KEYS[0], column_start=gcols[0], column_finish=gcols[2]), gdict)
            # A start and end that are the same
            assert_equal(cf.get(KEYS[0], column_start=gcols[0], column_finish=gcols[0]),
                         {gcols[0]: {'bytes': VALS[0]}})

            # test xget paging
            assert_equal(list(cf.xget(KEYS[0], buffer_size=2)), gdict.items())

            assert_equal(cf.get_count(KEYS[0]), 3)

            # Test removing rows
            cf.remove(KEYS[0], columns=gcols[:1])
            assert_equal(cf.get_count(KEYS[0]), 2)

            cf.remove(KEYS[0], columns=gcols[1:])
            assert_equal(cf.get_count(KEYS[0]), 0)

            # Insert more than one row now
            cf.insert(KEYS[0], gdict)
            cf.insert(KEYS[1], gdict)
            cf.insert(KEYS[2], gdict)

            ### multiget() tests ###

            res = cf.multiget(KEYS[:])
            for i in range(3):
                assert_equal(res.get(KEYS[i]), gdict)

            res = cf.multiget(KEYS[2:])
            assert_equal(res.get(KEYS[2]), gdict)

            # Check each column individually
            for i in range(3):
                res = cf.multiget(KEYS[:], columns=[gcols[i]])
                for j in range(3):
                    assert_equal(res.get(KEYS[j]), {gcols[i]: {'bytes': VALS[i]}})

            # Check that if we list all columns, we get the full dict
            res = cf.multiget(KEYS[:], columns=gcols[:])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), gdict)

            # The same thing with a start and end instead
            res = cf.multiget(KEYS[:], column_start=gcols[0], column_finish=gcols[2])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), gdict)

            # A start and end that are the same
            res = cf.multiget(KEYS[:], column_start=gcols[0], column_finish=gcols[0])
            for j in range(3):
                assert_equal(res.get(KEYS[j]), {gcols[0]: {'bytes': VALS[0]}})

            ### get_range() tests ###

            res = cf.get_range(start=KEYS[0])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], column_start=gcols[0], column_finish=gcols[2])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], columns=gcols[:])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)


class TestSuperSubCFs(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'SuperLongSubLong', super=True,
                                 comparator_type=LongType(), subcomparator_type=LongType())
        sys.create_column_family(TEST_KS, 'SuperLongSubInt', super=True,
                                 comparator_type=LongType(), subcomparator_type=IntegerType())
        sys.create_column_family(TEST_KS, 'SuperLongSubBigInt', super=True,
                                 comparator_type=LongType(), subcomparator_type=IntegerType())
        sys.create_column_family(TEST_KS, 'SuperLongSubTime', super=True,
                                 comparator_type=LongType(), subcomparator_type=TimeUUIDType())
        sys.create_column_family(TEST_KS, 'SuperLongSubLex', super=True,
                                 comparator_type=LongType(), subcomparator_type=LexicalUUIDType())
        sys.create_column_family(TEST_KS, 'SuperLongSubAscii', super=True,
                                 comparator_type=LongType(), subcomparator_type=AsciiType())
        sys.create_column_family(TEST_KS, 'SuperLongSubUTF8', super=True,
                                 comparator_type=LongType(), subcomparator_type=UTF8Type())
        sys.create_column_family(TEST_KS, 'SuperLongSubBytes', super=True,
                                 comparator_type=LongType(), subcomparator_type=BytesType())
        sys.close()

        cls.cf_suplong_sublong = ColumnFamily(pool, 'SuperLongSubLong')
        cls.cf_suplong_subint = ColumnFamily(pool, 'SuperLongSubInt')
        cls.cf_suplong_subbigint = ColumnFamily(pool, 'SuperLongSubBigInt')
        cls.cf_suplong_subtime = ColumnFamily(pool, 'SuperLongSubTime')
        cls.cf_suplong_sublex = ColumnFamily(pool, 'SuperLongSubLex')
        cls.cf_suplong_subascii = ColumnFamily(pool, 'SuperLongSubAscii')
        cls.cf_suplong_subutf8 = ColumnFamily(pool, 'SuperLongSubUTF8')
        cls.cf_suplong_subbytes = ColumnFamily(pool, 'SuperLongSubBytes')

        cls.cfs = [cls.cf_suplong_subint, cls.cf_suplong_subint,
                   cls.cf_suplong_subtime, cls.cf_suplong_sublex,
                   cls.cf_suplong_subascii, cls.cf_suplong_subutf8,
                   cls.cf_suplong_subbytes]

    def tearDown(self):
        for cf in TestSuperSubCFs.cfs:
            for key, cols in cf.get_range():
                cf.remove(key)

    def make_sub_group(self, cf, cols):
        diction = {123L: {cols[0]: VALS[0],
                          cols[1]: VALS[1],
                          cols[2]: VALS[2]}}
        return {'cf': cf, 'cols': cols, 'dict': diction}

    def test_super_column_family_subs(self):

        # For each data type, create a group that includes its column family,
        # a set of column names, and a dictionary that maps from the column
        # names to values.
        type_groups = []

        long_cols = [1111111111111111L,
                     2222222222222222L,
                     3333333333333333L]
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_sublong, long_cols))

        int_cols = [1, 2, 3]
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_subint, int_cols))

        big_int_cols = [1 + int(time.time() * 10 ** 6),
                        2 + int(time.time() * 10 ** 6),
                        3 + int(time.time() * 10 ** 6)]
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_subbigint, big_int_cols))

        time_cols = [TIME1, TIME2, TIME3]
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_subtime, time_cols))

        lex_cols = [uuid.UUID(bytes='aaa aaa aaa aaaa'),
                    uuid.UUID(bytes='bbb bbb bbb bbbb'),
                    uuid.UUID(bytes='ccc ccc ccc cccc')]
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_sublex, lex_cols))

        ascii_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_subascii, ascii_cols))

        utf8_cols = [u'a\u0020', u'b\u0020', u'c\u0020']
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_subutf8, utf8_cols))

        bytes_cols = ['aaaa', 'bbbb', 'cccc']
        type_groups.append(self.make_sub_group(TestSuperSubCFs.cf_suplong_subbytes, bytes_cols))

        # Begin the actual inserting and getting
        for group in type_groups:
            cf = group.get('cf')
            gdict = group.get('dict')

            cf.insert(KEYS[0], gdict)

            assert_equal(cf.get(KEYS[0]), gdict)
            assert_equal(cf.get(KEYS[0], columns=[123L]), gdict)

            # A start and end that are the same
            assert_equal(cf.get(KEYS[0], column_start=123L, column_finish=123L), gdict)

            res = cf.get(KEYS[0], super_column=123L, column_start=group.get('cols')[0])
            assert_equal(res, gdict.get(123L))

            res = cf.get(KEYS[0], super_column=123L, column_finish=group.get('cols')[-1])
            assert_equal(res, gdict.get(123L))

            assert_equal(cf.get_count(KEYS[0]), 1)

            # Test removing rows
            cf.remove(KEYS[0], super_column=123L)
            assert_equal(cf.get_count(KEYS[0]), 0)

            # Insert more than one row now
            cf.insert(KEYS[0], gdict)
            cf.insert(KEYS[1], gdict)
            cf.insert(KEYS[2], gdict)

            ### multiget() tests ###

            res = cf.multiget(KEYS[:])
            for i in range(3):
                assert_equal(res.get(KEYS[i]), gdict)

            res = cf.multiget(KEYS[2:])
            assert_equal(res.get(KEYS[2]), gdict)

            res = cf.multiget(KEYS[:], columns=[123L])
            for i in range(3):
                assert_equal(res.get(KEYS[i]), gdict)

            res = cf.multiget(KEYS[:], super_column=123L)
            for i in range(3):
                assert_equal(res.get(KEYS[i]), gdict.get(123L))

            res = cf.multiget(KEYS[:], super_column=123L, column_start=group.get('cols')[0])
            for i in range(3):
                assert_equal(res.get(KEYS[i]), gdict.get(123L))

            res = cf.multiget(KEYS[:], column_start=123L, column_finish=123L)
            for j in range(3):
                assert_equal(res.get(KEYS[j]), gdict)

            ### get_range() tests ###

            res = cf.get_range(start=KEYS[0])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], column_start=123L, column_finish=123L)
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], columns=[123L])
            for sub_res in res:
                assert_equal(sub_res[1], gdict)

            res = cf.get_range(start=KEYS[0], super_column=123L)
            for sub_res in res:
                assert_equal(sub_res[1], gdict.get(123L))

            res = cf.get_range(start=KEYS[0], super_column=123L, column_start=group.get('cols')[0])
            for sub_res in res:
                assert_equal(sub_res[1], gdict.get(123L))

            res = cf.get_range(start=KEYS[0], super_column=123L, column_finish=group.get('cols')[-1])
            for sub_res in res:
                assert_equal(sub_res[1], gdict.get(123L))

class TestValidators(unittest.TestCase):

    def test_validation_with_packed_names(self):
        """
        Make sure that validated columns are packed correctly when the
        column names themselves must be packed
        """
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'Validators2',
                comparator_type=LongType(), default_validation_class=LongType())
        sys.alter_column(TEST_KS, 'Validators2', 1, TimeUUIDType())
        sys.close()

        my_uuid = uuid.uuid1()
        cf = ColumnFamily(pool, 'Validators2')

        cf.insert('key', {0: 0})
        assert_equal(cf.get('key'), {0: 0})

        cf.insert('key', {1: my_uuid})
        assert_equal(cf.get('key'), {0: 0, 1: my_uuid})

        cf.insert('key', {0: 0, 1: my_uuid})
        assert_equal(cf.get('key'), {0: 0, 1: my_uuid})

    def test_validated_columns(self):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'Validators',)
        sys.alter_column(TEST_KS, 'Validators', 'long', LongType())
        sys.alter_column(TEST_KS, 'Validators', 'int', IntegerType())
        sys.alter_column(TEST_KS, 'Validators', 'time', TimeUUIDType())
        sys.alter_column(TEST_KS, 'Validators', 'lex', LexicalUUIDType())
        sys.alter_column(TEST_KS, 'Validators', 'ascii', AsciiType())
        sys.alter_column(TEST_KS, 'Validators', 'utf8', UTF8Type())
        sys.alter_column(TEST_KS, 'Validators', 'bytes', BytesType())
        sys.close()

        cf = ColumnFamily(pool, 'Validators')
        key = 'key1'

        col = {'long': 1L}
        cf.insert(key, col)
        assert_equal(cf.get(key)['long'], 1L)

        col = {'int': 1}
        cf.insert(key, col)
        assert_equal(cf.get(key)['int'], 1)

        col = {'time': TIME1}
        cf.insert(key, col)
        assert_equal(cf.get(key)['time'], TIME1)

        col = {'lex': uuid.UUID(bytes='aaa aaa aaa aaaa')}
        cf.insert(key, col)
        assert_equal(cf.get(key)['lex'], uuid.UUID(bytes='aaa aaa aaa aaaa'))

        col = {'ascii': 'aaa'}
        cf.insert(key, col)
        assert_equal(cf.get(key)['ascii'], 'aaa')

        col = {'utf8': u'a\u0020'}
        cf.insert(key, col)
        assert_equal(cf.get(key)['utf8'], u'a\u0020')

        col = {'bytes': 'aaa'}
        cf.insert(key, col)
        assert_equal(cf.get(key)['bytes'], 'aaa')

        cf.remove(key)


class TestDefaultValidators(unittest.TestCase):

    def test_default_validated_columns(self):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'DefaultValidator', default_validation_class=LongType())
        sys.alter_column(TEST_KS, 'DefaultValidator', 'subcol', TimeUUIDType())
        sys.close()

        cf = ColumnFamily(pool, 'DefaultValidator')
        key = 'key1'

        col_cf = {'aaaaaa': 1L}
        col_cm = {'subcol': TIME1}
        col_ncf = {'aaaaaa': TIME1}

        # Both of these inserts work, as cf allows
        #  longs and cm for 'subcol' allows TIMEUUIDs.
        cf.insert(key, col_cf)
        cf.insert(key, col_cm)
        assert_equal(cf.get(key), {'aaaaaa': 1L, 'subcol': TIME1})

        # Insert multiple columns at once
        col_cf.update(col_cm)
        cf.insert(key, col_cf)
        assert_equal(cf.get(key), {'aaaaaa': 1L, 'subcol': TIME1})

        assert_raises(TypeError, cf.insert, key, col_ncf)

        cf.remove(key)

class TestKeyValidators(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()

        sys.create_column_family(TEST_KS, 'KeyLong', key_validation_class=LongType())
        sys.create_column_family(TEST_KS, 'KeyInteger', key_validation_class=IntegerType())
        sys.create_column_family(TEST_KS, 'KeyTimeUUID', key_validation_class=TimeUUIDType())
        sys.create_column_family(TEST_KS, 'KeyLexicalUUID', key_validation_class=LexicalUUIDType())
        sys.create_column_family(TEST_KS, 'KeyAscii', key_validation_class=AsciiType())
        sys.create_column_family(TEST_KS, 'KeyUTF8', key_validation_class=UTF8Type())
        sys.create_column_family(TEST_KS, 'KeyBytes', key_validation_class=BytesType())
        sys.close()

        cls.cf_long = ColumnFamily(pool, 'KeyLong')
        cls.cf_int = ColumnFamily(pool, 'KeyInteger')
        cls.cf_time = ColumnFamily(pool, 'KeyTimeUUID')
        cls.cf_lex = ColumnFamily(pool, 'KeyLexicalUUID')
        cls.cf_ascii = ColumnFamily(pool, 'KeyAscii')
        cls.cf_utf8 = ColumnFamily(pool, 'KeyUTF8')
        cls.cf_bytes = ColumnFamily(pool, 'KeyBytes')

        cls.cfs = [cls.cf_long, cls.cf_int, cls.cf_time, cls.cf_lex,
                    cls.cf_ascii, cls.cf_utf8, cls.cf_bytes]

    def tearDown(self):
        for cf in TestKeyValidators.cfs:
            for key, cols in cf.get_range():
                cf.remove(key)

    def setUp(self):
        self.type_groups = []

        long_keys = [1111111111111111L,
                     2222222222222222L,
                     3333333333333333L]
        self.type_groups.append((TestKeyValidators.cf_long, long_keys))

        int_keys = [1, 2, 3]
        self.type_groups.append((TestKeyValidators.cf_int, int_keys))

        time_keys = [TIME1, TIME2, TIME3]
        self.type_groups.append((TestKeyValidators.cf_time, time_keys))

        lex_keys = [uuid.UUID(bytes='aaa aaa aaa aaaa'),
                    uuid.UUID(bytes='bbb bbb bbb bbbb'),
                    uuid.UUID(bytes='ccc ccc ccc cccc')]
        self.type_groups.append((TestKeyValidators.cf_lex, lex_keys))

        ascii_keys = ['aaaa', 'bbbb', 'cccc']
        self.type_groups.append((TestKeyValidators.cf_ascii, ascii_keys))

        utf8_keys = [u'a\u0020', u'b\u0020', u'c\u0020']
        self.type_groups.append((TestKeyValidators.cf_utf8, utf8_keys))

        bytes_keys = ['aaaa', 'bbbb', 'cccc']
        self.type_groups.append((TestKeyValidators.cf_bytes, bytes_keys))

    def test_inserts(self):
        for cf, keys in self.type_groups:
            for key in keys:
                cf.insert(key, {str(key): 'val'})
                results = cf.get(key)
                assert_equal(results, {str(key): 'val'})

                col1 = str(key) + "1"
                col2 = str(key) + "2"
                cols = {col1: "val1", col2: "val2"}
                cf.insert(key, cols)
                results = cf.get(key)
                cols.update({str(key): 'val'})
                assert_equal(results, cols)

    def test_batch_insert(self):
        for cf, keys in self.type_groups:
            rows = dict([(key, {str(key): 'val'}) for key in keys])
            cf.batch_insert(rows)
            for key in keys:
                results = cf.get(key)
                assert_equal(results, {str(key): 'val'})

    def test_multiget(self):
        for cf, keys in self.type_groups:
            for key in keys:
                cf.insert(key, {str(key): 'val'})
            results = cf.multiget(keys)
            for key in keys:
                assert_true(key in results)
                assert_equal(results[key], {str(key): 'val'})

    def test_get_count(self):
        for cf, keys in self.type_groups:
            for key in keys:
                cf.insert(key, {str(key): 'val'})
                results = cf.get_count(key)
                assert_equal(results, 1)

    def test_multiget_count(self):
        for cf, keys in self.type_groups:
            for key in keys:
                cf.insert(key, {str(key): 'val'})
            results = cf.multiget_count(keys)
            for key in keys:
                assert_true(key in results, "%s should be in %r" % (key, results))
                assert_equal(results[key], 1)

    def test_get_range(self):
        for cf, keys in self.type_groups:
            for key in keys:
                cf.insert(key, {str(key): 'val'})

            rows = list(cf.get_range())
            assert_equal(len(rows), len(keys))
            for k, c in rows:
                assert_true(k in keys)
                assert_equal(c, {str(k): 'val'})

    def test_get_indexed_slices(self):
        sys = SystemManager()
        for cf, keys in self.type_groups:
            sys.create_index(TEST_KS, cf.column_family, 'birthdate', LongType())
            cf = ColumnFamily(pool, cf.column_family)
            for key in keys:
                cf.insert(key, {'birthdate': 1})
            expr = create_index_expression('birthdate', 1)
            clause = create_index_clause([expr])
            rows = list(cf.get_indexed_slices(clause))
            assert_equal(len(rows), len(keys))
            for k, c in rows:
                assert_true(k in keys)
                assert_equal(c, {'birthdate': 1})

    def test_remove(self):
        for cf, keys in self.type_groups:
            for key in keys:
                cf.insert(key, {str(key): 'val'})
                assert_equal(cf.get(key), {str(key): 'val'})
                cf.remove(key)
                assert_raises(NotFoundException, cf.get, key)

    def test_add_remove_counter(self):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'KeyLongCounter', key_validation_class=LongType(),
                                 default_validation_class='CounterColumnType')
        sys.close()
        cf_long = ColumnFamily(pool, 'KeyLongCounter')

        key = 1111111111111111L

        cf_long.add(key, 'col')
        assert_equal(cf_long.get(key), {'col': 1})
        cf_long.remove_counter(key, 'col')
        time.sleep(0.1)
        assert_raises(NotFoundException, cf_long.get, key)

class TestComposites(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'StaticComposite',
                                 comparator_type=CompositeType(LongType(),
                                                               IntegerType(),
                                                               TimeUUIDType(reversed=True),
                                                               LexicalUUIDType(reversed=False),
                                                               AsciiType(),
                                                               UTF8Type(),
                                                               BytesType()))

    @classmethod
    def teardown_class(cls):
        sys = SystemManager()
        sys.drop_column_family(TEST_KS, 'StaticComposite')

    def test_static_composite_basic(self):
        cf = ColumnFamily(pool, 'StaticComposite')
        colname = (127312831239123123, 1, uuid.uuid1(), uuid.uuid4(), 'foo', u'ba\u0254r', 'baz')
        cf.insert('key', {colname: 'val'})
        assert_equal(cf.get('key'), {colname: 'val'})

    def test_static_composite_slicing(self):
        cf = ColumnFamily(pool, 'StaticComposite')
        u1 = uuid.uuid1()
        u4 = uuid.uuid4()
        col0 = (0, 1, u1, u4, '', '', '')
        col1 = (1, 1, u1, u4, '', '', '')
        col2 = (1, 2, u1, u4, '', '', '')
        col3 = (1, 3, u1, u4, '', '', '')
        col4 = (2, 1, u1, u4, '', '', '')
        cf.insert('key2', {col0: '', col1: '', col2: '', col3: '', col4: ''})

        result = cf.get('key2', column_start=((1, True),), column_finish=((1, True),))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=(1,), column_finish=((2, False), ))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=((1, True),), column_finish=((2, False), ))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=(1, ), column_finish=((2, False), ))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=((0, False), ), column_finish=((2, False), ))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=(1, 1), column_finish=(1, 3))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=(1, 1), column_finish=(1, (3, True)))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=(1, (1, True)), column_finish=((2, False), ))
        assert_equal(result, {col1: '', col2: '', col3: ''})

    def test_static_composite_get_partial_composite(self):
        cf = ColumnFamily(pool, 'StaticComposite')
        cf.insert('key3', {(123123, 1): 'val'})
        assert_equal(cf.get('key3'), {(123123, 1): 'val'})

    def test_uuid_composites(self):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'UUIDComposite',
                comparator_type=CompositeType(IntegerType(reversed=True), TimeUUIDType()),
                key_validation_class=TimeUUIDType(),
                default_validation_class=UTF8Type())

        key, u1, u2 = uuid.uuid1(), uuid.uuid1(), uuid.uuid1()
        cf = ColumnFamily(pool, 'UUIDComposite')
        cf.insert(key, {(123123, u1): 'foo'})
        cf.insert(key, {(123123, u1): 'foo', (-1, u2): 'bar', (-123123123, u1): 'baz'})
        assert_equal(cf.get(key), {(123123, u1): 'foo', (-1, u2): 'bar', (-123123123, u1): 'baz'})

    def test_single_component_composite(self):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'SingleComposite',
                comparator_type=CompositeType(IntegerType()))

        cf = ColumnFamily(pool, 'SingleComposite')
        cf.insert('key', {(123456,): 'val'})
        assert_equal(cf.get('key'), {(123456,): 'val'})

class TestDynamicComposites(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'StaticDynamicComposite',
                                 comparator_type=DynamicCompositeType({'l': LongType(),
                                                                       'i': IntegerType(),
                                                                       'T': TimeUUIDType(reversed=True),
                                                                       'x': LexicalUUIDType(reversed=False),
                                                                       'a': AsciiType(),
                                                                       's': UTF8Type(),
                                                                       'b': BytesType()}))

    @classmethod
    def teardown_class(cls):
        sys = SystemManager()
        sys.drop_column_family(TEST_KS, 'StaticDynamicComposite')

    def setUp(self):
        global a, b, i, I, x, l, t, T, s

        component = namedtuple('DynamicComponent', ['type','value'])
        ascii_alias = component('a', None)
        bytes_alias = component('b', None)
        integer_alias = component('i', None)
        integer_rev_alias = component('I', None)
        lexicaluuid_alias = component('x', None)
        long_alias = component('l', None)
        timeuuid_alias = component('t', None)
        timeuuid_rev_alias = component('T', None)
        utf8_alias = component('s', None)

        _r = lambda t, v: t._replace(value=v) 
        a = lambda v: _r(ascii_alias, v)
        b = lambda v: _r(bytes_alias, v)
        i = lambda v: _r(integer_alias, v)
        I = lambda v: _r(integer_rev_alias, v)
        x = lambda v: _r(lexicaluuid_alias, v)
        l = lambda v: _r(long_alias, v)
        t = lambda v: _r(timeuuid_alias, v)
        T = lambda v: _r(timeuuid_rev_alias, v)
        s = lambda v: _r(utf8_alias, v)

    def test_static_composite_basic(self):
        cf = ColumnFamily(pool, 'StaticDynamicComposite')
        colname = (l(127312831239123123), i(1), T(uuid.uuid1()), x(uuid.uuid4()), a('foo'), s(u'ba\u0254r'), b('baz'))
        cf.insert('key', {colname: 'val'})
        assert_equal(cf.get('key'), {colname: 'val'})

    def test_static_composite_slicing(self):
        cf = ColumnFamily(pool, 'StaticDynamicComposite')
        u1 = uuid.uuid1()
        u4 = uuid.uuid4()
        col0 = (l(0), i(1), T(u1), x(u4), a(''), s(''), b(''))
        col1 = (l(1), i(1), T(u1), x(u4), a(''), s(''), b(''))
        col2 = (l(1), i(2), T(u1), x(u4), a(''), s(''), b(''))
        col3 = (l(1), i(3), T(u1), x(u4), a(''), s(''), b(''))
        col4 = (l(2), i(1), T(u1), x(u4), a(''), s(''), b(''))
        cf.insert('key2', {col0: '', col1: '', col2: '', col3: '', col4: ''})

        result = cf.get('key2', column_start=((l(1), True),), column_finish=((l(1), True),))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=(l(1),), column_finish=((l(2), False), ))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=((l(1), True),), column_finish=((l(2), False), ))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=(l(1), ), column_finish=((l(2), False), ))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=((l(0), False), ), column_finish=((l(2), False), ))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=(l(1), i(1)), column_finish=(l(1), i(3)))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=(l(1), i(1)), column_finish=(l(1), (i(3), True)))
        assert_equal(result, {col1: '', col2: '', col3: ''})

        result = cf.get('key2', column_start=(l(1), (i(1), True)), column_finish=((l(2), False), ))
        assert_equal(result, {col1: '', col2: '', col3: ''})

    def test_static_composite_get_partial_composite(self):
        cf = ColumnFamily(pool, 'StaticDynamicComposite')
        cf.insert('key3', {(l(123123), i(1)): 'val'})
        assert_equal(cf.get('key3'), {(l(123123), i(1)): 'val'})

    def test_uuid_composites(self):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'UUIDDynamicComposite',
                comparator_type=DynamicCompositeType({'I': IntegerType(reversed=True), 't': TimeUUIDType()}),
                key_validation_class=TimeUUIDType(),
                default_validation_class=UTF8Type())

        key, u1, u2 = uuid.uuid1(), uuid.uuid1(), uuid.uuid1()
        cf = ColumnFamily(pool, 'UUIDDynamicComposite')
        cf.insert(key, {(I(123123), t(u1)): 'foo'})
        cf.insert(key, {(I(123123), t(u1)): 'foo', (I(-1), t(u2)): 'bar', (I(-123123123), t(u1)): 'baz'})
        assert_equal(cf.get(key), {(I(123123), t(u1)): 'foo', (I(-1), t(u2)): 'bar', (I(-123123123), t(u1)): 'baz'})

    def test_single_component_composite(self):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'SingleDynamicComposite',
                comparator_type=DynamicCompositeType({'i': IntegerType()}))

        cf = ColumnFamily(pool, 'SingleDynamicComposite')
        cf.insert('key', {(i(123456),): 'val'})
        assert_equal(cf.get('key'), {(i(123456),): 'val'})

class TestBigInt(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'StdInteger', comparator_type=IntegerType())

    @classmethod
    def teardown_class(cls):
        sys = SystemManager()
        sys.drop_column_family(TEST_KS, 'StdInteger')

    def setUp(self):
        self.key = 'TestBigInt'
        self.cf = ColumnFamily(pool, 'StdInteger')

    def tearDown(self):
        self.cf.remove(self.key)

    def test_negative_integers(self):
        self.cf.insert(self.key, {-1: '-1'})
        self.cf.insert(self.key, {-12342390: '-12342390'})
        self.cf.insert(self.key, {-255: '-255'})
        self.cf.insert(self.key, {-256: '-256'})
        self.cf.insert(self.key, {-257: '-257'})
        for key, cols in self.cf.get_range():
            self.assertEquals(str(cols.keys()[0]), cols.values()[0])

class TestTimeUUIDs(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'TestTimeUUIDs', comparator_type=TimeUUIDType())
        sys.close()
        cls.cf_time = ColumnFamily(pool, 'TestTimeUUIDs')

    def test_datetime_to_uuid(self):
        cf_time = TestTimeUUIDs.cf_time
        key = 'key1'
        timeline = []

        timeline.append(datetime.utcnow())
        time1 = uuid1()
        col1 = {time1: '0'}
        cf_time.insert(key, col1)
        time.sleep(1)

        timeline.append(datetime.utcnow())
        time2 = uuid1()
        col2 = {time2: '1'}
        cf_time.insert(key, col2)
        time.sleep(1)

        timeline.append(datetime.utcnow())

        cols = {time1: '0', time2: '1'}

        assert_equal(cf_time.get(key, column_start=timeline[0])                            , cols)
        assert_equal(cf_time.get(key,                           column_finish=timeline[2]) , cols)
        assert_equal(cf_time.get(key, column_start=timeline[0], column_finish=timeline[2]) , cols)
        assert_equal(cf_time.get(key, column_start=timeline[0], column_finish=timeline[2]) , cols)
        assert_equal(cf_time.get(key, column_start=timeline[0], column_finish=timeline[1]) , col1)
        assert_equal(cf_time.get(key, column_start=timeline[1], column_finish=timeline[2]) , col2)
        cf_time.remove(key)

    def test_time_to_uuid(self):
        cf_time = TestTimeUUIDs.cf_time
        key = 'key1'
        timeline = []

        timeline.append(time.time())
        time1 = uuid1()
        col1 = {time1: '0'}
        cf_time.insert(key, col1)
        time.sleep(0.1)

        timeline.append(time.time())
        time2 = uuid1()
        col2 = {time2: '1'}
        cf_time.insert(key, col2)
        time.sleep(0.1)

        timeline.append(time.time())

        cols = {time1:'0', time2: '1'}

        assert_equal(cf_time.get(key, column_start=timeline[0])                            , cols)
        assert_equal(cf_time.get(key,                           column_finish=timeline[2]) , cols)
        assert_equal(cf_time.get(key, column_start=timeline[0], column_finish=timeline[2]) , cols)
        assert_equal(cf_time.get(key, column_start=timeline[0], column_finish=timeline[2]) , cols)
        assert_equal(cf_time.get(key, column_start=timeline[0], column_finish=timeline[1]) , col1)
        assert_equal(cf_time.get(key, column_start=timeline[1], column_finish=timeline[2]) , col2)
        cf_time.remove(key)

    def test_auto_time_to_uuid1(self):
        cf_time = TestTimeUUIDs.cf_time
        key = 'key1'
        t = time.time()
        col = {t: 'foo'}
        cf_time.insert(key, col)
        uuid_res = cf_time.get(key).keys()[0]
        timestamp = convert_uuid_to_time(uuid_res)
        assert_almost_equal(timestamp, t, places=3)
        cf_time.remove(key)

class TestTypeErrors(unittest.TestCase):

    def test_packing_enabled(self):
        self.cf = ColumnFamily(pool, 'Standard1')
        self.cf.insert('key', {'col': 'val'})
        assert_raises(TypeError, self.cf.insert, args=('key', {123: 'val'}))
        assert_raises(TypeError, self.cf.insert, args=('key', {'col': 123}))
        assert_raises(TypeError, self.cf.insert, args=('key', {123: 123}))
        self.cf.remove('key')

    def test_packing_disabled(self):
        self.cf = ColumnFamily(pool, 'Standard1', autopack_names=False, autopack_values=False)
        self.cf.insert('key', {'col': 'val'})
        assert_raises(TypeError, self.cf.insert, args=('key', {123: 'val'}))
        assert_raises(TypeError, self.cf.insert, args=('key', {'col': 123}))
        assert_raises(TypeError, self.cf.insert, args=('key', {123: 123}))
        self.cf.remove('key')

class TestDateTypes(unittest.TestCase):

    def _compare_dates(self, d1, d2):
        self.assertEquals(d1.timetuple(), d2.timetuple())
        self.assertEquals(int(d1.microsecond/1e3), int(d2.microsecond/1e3))

    def test_compatibility(self):
        self.cf = ColumnFamily(pool, 'Standard1')
        self.cf.column_validators['date'] = OldPycassaDateType()

        d = datetime.utcnow()
        self.cf.insert('key1', {'date': d})
        self._compare_dates(self.cf.get('key1')['date'], d)

        self.cf.column_validators['date'] = IntermediateDateType()
        self._compare_dates(self.cf.get('key1')['date'], d)
        self.cf.insert('key1', {'date': d})
        self._compare_dates(self.cf.get('key1')['date'], d)

        self.cf.column_validators['date'] = DateType()
        self._compare_dates(self.cf.get('key1')['date'], d)
        self.cf.insert('key1', {'date': d})
        self._compare_dates(self.cf.get('key1')['date'], d)
        self.cf.remove('key1')

class TestPackerOverride(unittest.TestCase):

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(TEST_KS, 'CompositeOverrideCF',
                comparator_type=CompositeType(AsciiType(), AsciiType()),
                default_validation_class=AsciiType())

    @classmethod
    def teardown_class(cls):
        sys = SystemManager()
        sys.drop_column_family(TEST_KS, 'CompositeOverrideCF')

    def test_column_validator(self):
        cf = ColumnFamily(pool, 'CompositeOverrideCF')
        cf.column_validators[('a', 'b')] = BooleanType()
        cf.insert('key', {('a', 'a'): 'foo', ('a', 'b'): True})
        assert_equal(cf.get('key'), {('a', 'a'): 'foo', ('a', 'b'): True})

        assert_equal(cf.column_validators[('a', 'b')].__class__, BooleanType)

        keys = cf.column_validators.keys()
        assert_equal(keys, [('a', 'b')])

        del cf.column_validators[('a', 'b')]
        assert_raises(KeyError, cf.column_validators.__getitem__, ('a', 'b'))

class TestCustomTypes(unittest.TestCase):

    class IntString(CassandraType):

        @staticmethod
        def pack(intval):
            return str(intval)

        @staticmethod
        def unpack(strval):
            return int(strval)

    class IntString2(CassandraType):

        def __init__(self, *args, **kwargs):
            self.pack = lambda val: str(val)
            self.unpack = lambda val: int(val)

    def test_staticmethod_funcs(self):
        self.cf = ColumnFamily(pool, 'Standard1')
        self.cf.key_validation_class = TestCustomTypes.IntString()
        self.cf.insert(1234, {'col': 'val'})
        assert_equal(self.cf.get(1234), {'col': 'val'})

    def test_constructor_lambdas(self):
        self.cf = ColumnFamily(pool, 'Standard1')
        self.cf.key_validation_class = TestCustomTypes.IntString2()
        self.cf.insert(1234, {'col': 'val'})
        assert_equal(self.cf.get(1234), {'col': 'val'})

class TestCustomComposite(unittest.TestCase):
    """
    Test CompositeTypes with custom inner types.
    """

    # Some contrived scenarios
    class IntDateType(CassandraType):
        """
        Represent a date as an integer. E.g.: March 05, 2012 = 20120305
        """
        @staticmethod
        def pack(v, *args, **kwargs):
            assert type(v) in (datetime, date), "Invalid arg"
            str_date = v.strftime("%Y%m%d")
            return marshal.encode_int(int(str_date))

        @staticmethod
        def unpack(v, *args, **kwargs):
            int_date = marshal.decode_int(v)
            return date(*time.strptime(str(int_date), "%Y%m%d")[0:3])

    class IntString(CassandraType):

        @staticmethod
        def pack(intval):
            return str(intval)

        @staticmethod
        def unpack(strval):
            return int(strval)

    class IntString2(CassandraType):

        def __init__(self, *args, **kwargs):
            self.pack = lambda val: str(val)
            self.unpack = lambda val: int(val)

    @classmethod
    def setup_class(cls):
        sys = SystemManager()
        sys.create_column_family(
            TEST_KS,
            'CustomComposite1',
            comparator_type=CompositeType(
                IntegerType(),
                UTF8Type()))

    @classmethod
    def teardown_class(cls):
        sys = SystemManager()
        sys.drop_column_family(TEST_KS, 'CustomComposite1')

    def test_static_composite_basic(self):
        cf = ColumnFamily(pool, 'CustomComposite1')
        colname = (20120305, '12345')
        cf.insert('key', {colname: 'val1'})
        assert_equal(cf.get('key'), {colname: 'val1'})

    def test_insert_with_custom_composite(self):
        cf_std = ColumnFamily(pool, 'CustomComposite1')
        cf_cust = ColumnFamily(pool, 'CustomComposite1')
        cf_cust.column_name_class = CompositeType(
                TestCustomComposite.IntDateType(),
                TestCustomComposite.IntString())

        std_col = (20120311, '321')
        cust_col = (date(2012, 3, 11), 321)
        cf_cust.insert('cust_insert_key_1', {cust_col: 'cust_insert_val_1'})
        assert_equal(cf_std.get('cust_insert_key_1'),
                {std_col: 'cust_insert_val_1'})

    def test_retrieve_with_custom_composite(self):
        cf_std = ColumnFamily(pool, 'CustomComposite1')
        cf_cust = ColumnFamily(pool, 'CustomComposite1')
        cf_cust.column_name_class = CompositeType(
                TestCustomComposite.IntDateType(),
                TestCustomComposite.IntString())

        std_col = (20120312, '321')
        cust_col = (date(2012, 3, 12), 321)
        cf_std.insert('cust_insert_key_2', {std_col: 'cust_insert_val_2'})
        assert_equal(cf_cust.get('cust_insert_key_2'),
                {cust_col: 'cust_insert_val_2'})

    def test_composite_slicing(self):
        cf_std = ColumnFamily(pool, 'CustomComposite1')
        cf_cust = ColumnFamily(pool, 'CustomComposite1')
        cf_cust.column_name_class = CompositeType(
                TestCustomComposite.IntDateType(),
                TestCustomComposite.IntString2())

        col0 = (20120101, '123')
        col1 = (20120102, '123')
        col2 = (20120102, '456')
        col3 = (20120102, '789')
        col4 = (20120103, '123')

        dt0 = date(2012, 1, 1)
        dt1 = date(2012, 1, 2)
        dt2 = date(2012, 1, 3)

        col1_cust = (dt1, 123)
        col2_cust = (dt1, 456)
        col3_cust = (dt1, 789)

        cf_std.insert('key2', {col0: '', col1: '', col2: '', col3: '', col4: ''})

        def check(column_start, column_finish, col_reversed=False):
            result = cf_cust.get('key2', column_start=column_start,
                    column_finish=column_finish, column_reversed=col_reversed)

            assert_equal(result, {col1_cust: '', col2_cust: '', col3_cust: ''})

        # Defaults should be inclusive on both ends
        check((dt1,), (dt1,))
        check((dt1,), (dt1,), True)

        check(((dt1, True),), ((dt1, True),))
        check((dt1,), ((dt2, False),))
        check(((dt1, True),), ((dt2, False),))
        check(((dt0, False),), ((dt2, False),))

        check((dt1, 123), (dt1, 789))
        check((dt1, 123), (dt1, (789, True)))
        check((dt1, (123, True)), ((dt2, False),))

        # Test inclusive ends for reversed
        check(((dt1, True),), ((dt1, True),), True)
        check( (dt1,),        ((dt1, True),), True)
        check(((dt1, True),),  (dt1,),        True)

        # Test exclusive ends for reversed
        check(((dt2, False),), ((dt0, False),), True)
        check(((dt2, False),),  (dt1,),         True)
        check((dt1,),          ((dt0, False),), True)


########NEW FILE########
__FILENAME__ = test_batch_mutation
from __future__ import with_statement

import sys
import unittest

from nose import SkipTest
from nose.tools import assert_raises, assert_equal
from pycassa import ConnectionPool, ColumnFamily, NotFoundException
import pycassa.batch as batch_mod
from pycassa.system_manager import SystemManager

ROWS = {'1': {'a': '123', 'b': '123'},
        '2': {'a': '234', 'b': '234'},
        '3': {'a': '345', 'b': '345'}}

pool = cf = scf = counter_cf = super_counter_cf = sysman = None

def setup_module():
    global pool, cf, scf, counter_cf, super_counter_cf, sysman
    credentials = {'username': 'jsmith', 'password': 'havebadpass'}
    pool = ConnectionPool(keyspace='PycassaTestKeyspace', credentials=credentials)
    cf = ColumnFamily(pool, 'Standard1')
    scf = ColumnFamily(pool, 'Super1')
    sysman = SystemManager()
    counter_cf = ColumnFamily(pool, 'Counter1')
    super_counter_cf = ColumnFamily(pool, 'SuperCounter1')

def teardown_module():
    pool.dispose()

class TestMutator(unittest.TestCase):

    def tearDown(self):
        for key, cols in cf.get_range():
            cf.remove(key)
        for key, cols, in scf.get_range():
            scf.remove(key)

    def test_insert(self):
        batch = cf.batch()
        for key, cols in ROWS.iteritems():
            batch.insert(key, cols)
        batch.send()
        for key, cols in ROWS.items():
            assert cf.get(key) == cols

    def test_insert_supercolumns(self):
        batch = scf.batch()
        batch.insert('one', ROWS)
        batch.insert('two', ROWS)
        batch.insert('three', ROWS)
        batch.send()
        assert scf.get('one') == ROWS
        assert scf.get('two') == ROWS
        assert scf.get('three') == ROWS

    def test_insert_counters(self):
        batch = counter_cf.batch()
        batch.insert('one', {'col': 1})
        batch.insert('two', {'col': 2})
        batch.insert('three', {'col': 3})
        batch.send()
        assert_equal(counter_cf.get('one'), {'col': 1})
        assert_equal(counter_cf.get('two'), {'col': 2})
        assert_equal(counter_cf.get('three'), {'col': 3})

        batch = super_counter_cf.batch()
        batch.insert('one', {'scol': {'col1': 1, 'col2': 2}})
        batch.insert('two', {'scol': {'col1': 3, 'col2': 4}})
        batch.send()
        assert_equal(super_counter_cf.get('one'), {'scol': {'col1': 1, 'col2': 2}})
        assert_equal(super_counter_cf.get('two'), {'scol': {'col1': 3, 'col2': 4}})

    def test_queue_size(self):
        batch = cf.batch(queue_size=2)
        batch.insert('1', ROWS['1'])
        batch.insert('2', ROWS['2'])
        batch.insert('3', ROWS['3'])
        assert cf.get('1') == ROWS['1']
        assert_raises(NotFoundException, cf.get, '3')
        batch.send()
        for key, cols in ROWS.items():
            assert cf.get(key) == cols

    def test_remove_key(self):
        batch = cf.batch()
        batch.insert('1', ROWS['1'])
        batch.remove('1')
        batch.send()
        assert_raises(NotFoundException, cf.get, '1')

    def test_remove_columns(self):
        batch = cf.batch()
        batch.insert('1', {'a': '123', 'b': '123'})
        batch.remove('1', ['a'])
        batch.send()
        assert cf.get('1') == {'b': '123'}

    def test_remove_supercolumns(self):
        batch = scf.batch()
        batch.insert('one', ROWS)
        batch.insert('two', ROWS)
        batch.insert('three', ROWS)
        batch.remove('two', ['b'], '2')
        batch.send()
        assert scf.get('one') == ROWS
        assert scf.get('two')['2'] == {'a': '234'}
        assert scf.get('three') == ROWS

    def test_chained(self):
        batch = cf.batch()
        batch.insert('1', ROWS['1']).insert('2', ROWS['2']).insert('3', ROWS['3']).send()
        assert cf.get('1') == ROWS['1']
        assert cf.get('2') == ROWS['2']
        assert cf.get('3') == ROWS['3']

    def test_contextmgr(self):
        if sys.version_info < (2, 5):
            raise SkipTest("No context managers in Python < 2.5")
        exec """with cf.batch(queue_size=2) as b:
    b.insert('1', ROWS['1'])
    b.insert('2', ROWS['2'])
    b.insert('3', ROWS['3'])
assert cf.get('3') == ROWS['3']"""

    def test_multi_column_family(self):
        batch = batch_mod.Mutator(pool)
        cf2 = cf
        batch.insert(cf, '1', ROWS['1'])
        batch.insert(cf, '2', ROWS['2'])
        batch.remove(cf2, '1', ROWS['1'])
        batch.send()
        assert cf.get('2') == ROWS['2']
        assert_raises(NotFoundException, cf.get, '1')

    def test_atomic_insert_at_mutator_creation(self):
        batch = cf.batch(atomic=True)
        for key, cols in ROWS.iteritems():
            batch.insert(key, cols)
        batch.send()
        for key, cols in ROWS.items():
            assert cf.get(key) == cols

    def test_atomic_insert_at_send(self):
        batch = cf.batch(atomic=True)
        for key, cols in ROWS.iteritems():
            batch.insert(key, cols)
        batch.send(atomic=True)
        for key, cols in ROWS.items():
            assert cf.get(key) == cols

########NEW FILE########
__FILENAME__ = test_columnfamily
import unittest

from nose.tools import assert_raises, assert_equal, assert_true

from pycassa import index, ColumnFamily, ConnectionPool,\
                    NotFoundException, SystemManager
from pycassa.util import OrderedDict

from tests.util import requireOPP

pool = cf = scf = indexed_cf = counter_cf = counter_scf = sys_man = None

def setup_module():
    global pool, cf, scf, indexed_cf, counter_cf, counter_scf, sys_man
    credentials = {'username': 'jsmith', 'password': 'havebadpass'}
    pool = ConnectionPool(keyspace='PycassaTestKeyspace',
            credentials=credentials, timeout=1.0)
    cf = ColumnFamily(pool, 'Standard1', dict_class=TestDict)
    scf = ColumnFamily(pool, 'Super1', dict_class=dict)
    indexed_cf = ColumnFamily(pool, 'Indexed1')
    sys_man = SystemManager()
    counter_cf = ColumnFamily(pool, 'Counter1')
    counter_scf = ColumnFamily(pool, 'SuperCounter1')

def teardown_module():
    cf.truncate()
    indexed_cf.truncate()
    counter_cf.truncate()
    counter_scf.truncate()
    pool.dispose()


class TestDict(dict):
    pass


class TestColumnFamily(unittest.TestCase):

    def setUp(self):
        self.sys_man = sys_man

    def tearDown(self):
        for key, columns in cf.get_range():
            cf.remove(key)
        for key, columns in indexed_cf.get_range():
            cf.remove(key)

    def test_bad_kwarg(self):
        assert_raises(TypeError,
                ColumnFamily.__init__, pool, 'test', bar='foo')

    def test_empty(self):
        key = 'TestColumnFamily.test_empty'
        assert_raises(NotFoundException, cf.get, key)
        assert_equal(len(cf.multiget([key])), 0)
        for key, columns in cf.get_range():
            assert_equal(len(columns), 0)

    def test_insert_get(self):
        key = 'TestColumnFamily.test_insert_get'
        columns = {'1': 'val1', '2': 'val2'}
        assert_raises(NotFoundException, cf.get, key)
        ts = cf.insert(key, columns)
        assert_true(isinstance(ts, (int, long)))
        assert_equal(cf.get(key), columns)

    def test_insert_multiget(self):
        key1 = 'TestColumnFamily.test_insert_multiget1'
        columns1 = {'1': 'val1', '2': 'val2'}
        key2 = 'test_insert_multiget1'
        columns2 = {'3': 'val1', '4': 'val2'}
        missing_key = 'key3'

        cf.insert(key1, columns1)
        cf.insert(key2, columns2)
        rows = cf.multiget([key1, key2, missing_key])
        assert_equal(len(rows), 2)
        assert_equal(rows[key1], columns1)
        assert_equal(rows[key2], columns2)
        assert_true(missing_key not in rows)

    def test_multiget_multiple_bad_key(self):
        key = 'efefefef'
        cf.multiget([key, key, key])

    def test_insert_get_count(self):
        key = 'TestColumnFamily.test_insert_get_count'
        columns = {'1': 'val1', '2': 'val2'}
        cf.insert(key, columns)
        assert_equal(cf.get_count(key), 2)

        assert_equal(cf.get_count(key, column_start='1'), 2)
        assert_equal(cf.get_count(key, column_finish='2'), 2)
        assert_equal(cf.get_count(key, column_start='1', column_finish='2'), 2)
        assert_equal(cf.get_count(key, column_start='1', column_finish='1'), 1)
        assert_equal(cf.get_count(key, columns=['1', '2']), 2)
        assert_equal(cf.get_count(key, columns=['1']), 1)
        assert_equal(cf.get_count(key, max_count=1), 1)
        assert_equal(cf.get_count(key, max_count=1, column_reversed=True), 1)
        assert_equal(cf.get_count(key, column_reversed=True), 2)
        assert_equal(cf.get_count(key, column_start='1', column_reversed=True), 1)

    def test_insert_multiget_count(self):
        keys = ['TestColumnFamily.test_insert_multiget_count1',
                'TestColumnFamily.test_insert_multiget_count2',
                'TestColumnFamily.test_insert_multiget_count3']
        for key in keys:
            cf.insert(key, {'1': 'val1', '2': 'val2'})

        result = cf.multiget_count(keys)
        assert_equal([result[k] for k in keys], [2 for key in keys])

        result = cf.multiget_count(keys, column_start='1')
        assert_equal([result[k] for k in keys], [2 for key in keys])

        result = cf.multiget_count(keys, column_finish='2')
        assert_equal([result[k] for k in keys], [2 for key in keys])

        result = cf.multiget_count(keys, column_start='1', column_finish='2')
        assert_equal([result[k] for k in keys], [2 for key in keys])

        result = cf.multiget_count(keys, column_start='1', column_finish='1')
        assert_equal([result[k] for k in keys], [1 for key in keys])

        result = cf.multiget_count(keys, columns=['1', '2'])
        assert_equal([result[k] for k in keys], [2 for key in keys])

        result = cf.multiget_count(keys, columns=['1'])
        assert_equal([result[k] for k in keys], [1 for key in keys])

        result = cf.multiget_count(keys, max_count=1)
        assert_equal([result[k] for k in keys], [1 for key in keys])

        result = cf.multiget_count(keys, column_start='1', column_reversed=True)
        assert_equal([result[k] for k in keys], [1 for key in keys])

    @requireOPP
    def test_insert_get_range(self):
        keys = ['TestColumnFamily.test_insert_get_range%s' % i for i in xrange(5)]
        columns = {'1': 'val1', '2': 'val2'}
        for key in keys:
            cf.insert(key, columns)

        rows = list(cf.get_range(start=keys[0], finish=keys[-1]))
        assert_equal(len(rows), len(keys))
        for i, (k, c) in enumerate(rows):
            assert_equal(k, keys[i])
            assert_equal(c, columns)

    @requireOPP
    def test_get_range_batching(self):
        cf.truncate()

        keys = []
        columns = {'c': 'v'}
        for i in range(100, 201):
            keys.append('key%d' % i)
            cf.insert('key%d' % i, columns)

        for i in range(201, 301):
            cf.insert('key%d' % i, columns)

        count = 0
        for k, v in cf.get_range(row_count=100, buffer_size=10):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 100)

        count = 0
        for k, v in cf.get_range(row_count=100, buffer_size=1000):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 100)

        count = 0
        for k, v in cf.get_range(row_count=100, buffer_size=150):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 100)

        count = 0
        for k, v in cf.get_range(row_count=100, buffer_size=7):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 100)

        count = 0
        for k, v in cf.get_range(row_count=100, buffer_size=2):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 100)

        # Put the remaining keys in our list
        for i in range(201, 301):
            keys.append('key%d' % i)

        count = 0
        for k, v in cf.get_range(row_count=10000, buffer_size=2):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 201)

        count = 0
        for k, v in cf.get_range(row_count=10000, buffer_size=7):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 201)

        count = 0
        for k, v in cf.get_range(row_count=10000, buffer_size=200):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 201)

        count = 0
        for k, v in cf.get_range(row_count=10000, buffer_size=10000):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 201)

        # Don't give a row count
        count = 0
        for k, v in cf.get_range(buffer_size=2):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 201)

        count = 0
        for k, v in cf.get_range(buffer_size=77):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 201)

        count = 0
        for k, v in cf.get_range(buffer_size=200):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 201)

        count = 0
        for k, v in cf.get_range(buffer_size=10000):
            assert_true(k in keys, 'key "%s" should be in keys' % k)
            count += 1
        assert_equal(count, 201)

        cf.truncate()

    @requireOPP
    def test_get_range_tokens(self):
        cf.truncate()
        columns = {'c': 'v'}
        for i in range(100, 201):
            cf.insert('key%d' % i, columns)

        results = list(cf.get_range(start_token="key100".encode('hex'), finish_token="key200".encode('hex')))
        assert_equal(100, len(results))

        results = list(cf.get_range(start_token="key100".encode('hex'), finish_token="key200".encode('hex'), buffer_size=10))
        assert_equal(100, len(results))

        results = list(cf.get_range(start_token="key100".encode('hex'), buffer_size=10))
        assert_equal(100, len(results))

        results = list(cf.get_range(finish_token="key201".encode('hex'), buffer_size=10))
        assert_equal(101, len(results))

    def insert_insert_get_indexed_slices(self):
        indexed_cf = ColumnFamily(pool, 'Indexed1')

        columns = {'birthdate': 1L}

        keys = []
        for i in range(1, 4):
            indexed_cf.insert('key%d' % i, columns)
            keys.append('key%d')

        expr = index.create_index_expression(column_name='birthdate', value=1L)
        clause = index.create_index_clause([expr])

        count = 0
        for key, cols in indexed_cf.get_indexed_slices(clause):
            assert_equal(cols, columns)
            assert key in keys
            count += 1
        assert_equal(count, 3)

    def test_get_indexed_slices_batching(self):
        indexed_cf = ColumnFamily(pool, 'Indexed1')

        columns = {'birthdate': 1L}

        for i in range(200):
            indexed_cf.insert('key%d' % i, columns)

        expr = index.create_index_expression(column_name='birthdate', value=1L)
        clause = index.create_index_clause([expr], count=10)

        result = list(indexed_cf.get_indexed_slices(clause, buffer_size=2))
        assert_equal(len(result), 10)
        result = list(indexed_cf.get_indexed_slices(clause, buffer_size=10))
        assert_equal(len(result), 10)
        result = list(indexed_cf.get_indexed_slices(clause, buffer_size=77))
        assert_equal(len(result), 10)
        result = list(indexed_cf.get_indexed_slices(clause, buffer_size=200))
        assert_equal(len(result), 10)
        result = list(indexed_cf.get_indexed_slices(clause, buffer_size=1000))
        assert_equal(len(result), 10)

        clause = index.create_index_clause([expr], count=250)

        result = list(indexed_cf.get_indexed_slices(clause, buffer_size=2))
        assert_equal(len(result), 200)
        result = list(indexed_cf.get_indexed_slices(clause, buffer_size=10))
        assert_equal(len(result), 200)
        result = list(indexed_cf.get_indexed_slices(clause, buffer_size=77))
        assert_equal(len(result), 200)
        result = list(indexed_cf.get_indexed_slices(clause, buffer_size=200))
        assert_equal(len(result), 200)
        result = list(indexed_cf.get_indexed_slices(clause, buffer_size=1000))
        assert_equal(len(result), 200)

    def test_multiget_batching(self):
        key_prefix = "TestColumnFamily.test_multiget_batching"
        keys = []
        expected = OrderedDict()
        for i in range(10):
            key = key_prefix + str(i)
            keys.append(key)
            expected[key] = {'col': 'val'}
            cf.insert(key, {'col': 'val'})

        assert_equal(cf.multiget(keys, buffer_size=1), expected)
        assert_equal(cf.multiget(keys, buffer_size=2), expected)
        assert_equal(cf.multiget(keys, buffer_size=3), expected)
        assert_equal(cf.multiget(keys, buffer_size=9), expected)
        assert_equal(cf.multiget(keys, buffer_size=10), expected)
        assert_equal(cf.multiget(keys, buffer_size=11), expected)
        assert_equal(cf.multiget(keys, buffer_size=100), expected)

    def test_add(self):
        counter_cf.add('key', 'col')
        result = counter_cf.get('key')
        assert_equal(result['col'], 1)

        counter_cf.add('key', 'col')
        result = counter_cf.get('key')
        assert_equal(result['col'], 2)

        counter_cf.add('key', 'col2')
        result = counter_cf.get('key')
        assert_equal(result, {'col': 2, 'col2': 1})

    def test_insert_counters(self):
        counter_cf.insert('counter_key', {'col1': 1})
        result = counter_cf.get('counter_key')
        assert_equal(result['col1'], 1)

        counter_cf.insert('counter_key', {'col1': 1, 'col2': 1})
        result = counter_cf.get('counter_key')
        assert_equal(result, {'col1': 2, 'col2': 1})

    def test_remove(self):
        key = 'TestColumnFamily.test_remove'
        columns = {'1': 'val1', '2': 'val2'}
        cf.insert(key, columns)

        # An empty list for columns shouldn't delete anything
        cf.remove(key, columns=[])
        assert_equal(cf.get(key), columns)

        cf.remove(key, columns=['2'])
        del columns['2']
        assert_equal(cf.get(key), {'1': 'val1'})

        cf.remove(key)
        assert_raises(NotFoundException, cf.get, key)

    def test_remove_counter(self):
        key = 'test_remove_counter'
        counter_cf.add(key, 'col')
        result = counter_cf.get(key)
        assert_equal(result['col'], 1)

        counter_cf.remove_counter(key, 'col')
        assert_raises(NotFoundException, cf.get, key)

    def test_dict_class(self):
        key = 'TestColumnFamily.test_dict_class'
        cf.insert(key, {'1': 'val1'})
        assert isinstance(cf.get(key), TestDict)

    def test_xget(self):
        key = "test_xget_batching"
        cf.insert(key, dict((str(i), str(i)) for i in range(100, 300)))

        combos = [(100, 10),
                  (100, 1000),
                  (100, 199),
                  (100, 200),
                  (100, 201),
                  (100, 7),
                  (100, 2)]

        for count, bufsz in combos:
            res = list(cf.xget(key, column_count=count, buffer_size=bufsz))
            assert_equal(len(res), count)
            assert_equal(res, [(str(i), str(i)) for i in range(100, 200)])

        combos = [(10000, 2),
                  (10000, 7),
                  (10000, 199),
                  (10000, 200),
                  (10000, 201),
                  (10000, 10000)]

        for count, bufsz in combos:
            res = list(cf.xget(key, column_count=count, buffer_size=bufsz))
            assert_equal(len(res), 200)
            assert_equal(res, [(str(i), str(i)) for i in range(100, 300)])

        for bufsz in [2, 77, 199, 200, 201, 10000]:
            res = list(cf.xget(key, column_count=None, buffer_size=bufsz))
            assert_equal(len(res), 200)
            assert_equal(res, [(str(i), str(i)) for i in range(100, 300)])

    def test_xget_counter(self):
        key = 'test_xget_counter'
        counter_cf.insert(key, {'col1': 1})
        res = list(counter_cf.xget(key))
        assert_equal(res, [('col1', 1)])

        counter_cf.insert(key, {'col1': 1, 'col2': 1})
        res = list(counter_cf.xget(key))
        assert_equal(res, [('col1', 2), ('col2', 1)])

class TestSuperColumnFamily(unittest.TestCase):

    def tearDown(self):
        for key, columns in scf.get_range():
            scf.remove(key)

    def test_empty(self):
        key = 'TestSuperColumnFamily.test_empty'
        assert_raises(NotFoundException, cf.get, key)
        assert_equal(len(cf.multiget([key])), 0)
        for key, columns in cf.get_range():
            assert_equal(len(columns), 0)

    def test_get_whole_row(self):
        key = 'TestSuperColumnFamily.test_get_whole_row'
        columns = {'1': {'sub1': 'val1', 'sub2': 'val2'}, '2': {'sub3': 'val3', 'sub4': 'val4'}}
        scf.insert(key, columns)
        assert_equal(scf.get(key), columns)

    def test_get_super_column(self):
        key = 'TestSuperColumnFamily.test_get_super_column'
        subcolumns = {'sub1': 'val1', 'sub2': 'val2', 'sub3': 'val3'}
        columns = {'1': subcolumns}
        scf.insert(key, columns)
        assert_equal(scf.get(key), columns)
        assert_equal(scf.get(key, super_column='1'), subcolumns)
        assert_equal(scf.get(key, super_column='1', columns=['sub1']),     {'sub1': 'val1'})
        assert_equal(scf.get(key, super_column='1', column_start='sub3'),  {'sub3': 'val3'})
        assert_equal(scf.get(key, super_column='1', column_finish='sub1'), {'sub1': 'val1'})
        assert_equal(scf.get(key, super_column='1', column_count=1),       {'sub1': 'val1'})
        assert_equal(scf.get(key, super_column='1', column_count=1, column_reversed=True), {'sub3': 'val3'})

    def test_get_super_columns(self):
        key = 'TestSuperColumnFamily.test_get_super_columns'
        super1 = {'sub1': 'val1', 'sub2': 'val2'}
        super2 = {'sub3': 'val3', 'sub4': 'val4'}
        super3 = {'sub5': 'val5', 'sub6': 'val6'}
        columns = {'1': super1, '2': super2, '3': super3}
        scf.insert(key, columns)
        assert_equal(scf.get(key), columns)
        assert_equal(scf.get(key, columns=['1']),     {'1': super1})
        assert_equal(scf.get(key, column_start='3'),  {'3': super3})
        assert_equal(scf.get(key, column_finish='1'), {'1': super1})
        assert_equal(scf.get(key, column_count=1),    {'1': super1})
        assert_equal(scf.get(key, column_count=1, column_reversed=True), {'3': super3})

    def test_multiget_supercolumn(self):
        key1 = 'TestSuerColumnFamily.test_multiget_supercolumn1'
        key2 = 'TestSuerColumnFamily.test_multiget_supercolumn2'
        keys = [key1, key2]
        subcolumns = {'sub1': 'val1', 'sub2': 'val2', 'sub3': 'val3'}
        columns = {'1': subcolumns}
        scf.insert(key1, columns)
        scf.insert(key2, columns)

        assert_equal(scf.multiget(keys),
                     {key1: columns, key2: columns})

        assert_equal(scf.multiget(keys, super_column='1'),
                     {key1: subcolumns, key2: subcolumns})

        assert_equal(scf.multiget(keys, super_column='1', columns=['sub1']),
                     {key1: {'sub1': 'val1'}, key2: {'sub1': 'val1'}})

        assert_equal(scf.multiget(keys, super_column='1', column_start='sub3'),
                     {key1: {'sub3': 'val3'}, key2: {'sub3': 'val3'}})

        assert_equal(scf.multiget(keys, super_column='1', column_finish='sub1'),
                     {key1: {'sub1': 'val1'}, key2: {'sub1': 'val1'}})

        assert_equal(scf.multiget(keys, super_column='1', column_count=1),
                     {key1: {'sub1': 'val1'}, key2: {'sub1': 'val1'}})

        assert_equal(scf.multiget(keys, super_column='1', column_count=1, column_reversed=True),
                     {key1: {'sub3': 'val3'}, key2: {'sub3': 'val3'}})

    def test_multiget_supercolumns(self):
        key1 = 'TestSuerColumnFamily.test_multiget_supercolumns1'
        key2 = 'TestSuerColumnFamily.test_multiget_supercolumns2'
        keys = [key1, key2]
        super1 = {'sub1': 'val1', 'sub2': 'val2'}
        super2 = {'sub3': 'val3', 'sub4': 'val4'}
        super3 = {'sub5': 'val5', 'sub6': 'val6'}
        columns = {'1': super1, '2': super2, '3': super3}
        scf.insert(key1, columns)
        scf.insert(key2, columns)
        assert_equal(scf.multiget(keys), {key1: columns, key2: columns})
        assert_equal(scf.multiget(keys, columns=['1']),     {key1: {'1': super1}, key2: {'1': super1}})
        assert_equal(scf.multiget(keys, column_start='3'),  {key1: {'3': super3}, key2: {'3': super3}})
        assert_equal(scf.multiget(keys, column_finish='1'), {key1: {'1': super1}, key2: {'1': super1}})
        assert_equal(scf.multiget(keys, column_count=1),    {key1: {'1': super1}, key2: {'1': super1}})
        assert_equal(scf.multiget(keys, column_count=1, column_reversed=True), {key1: {'3': super3}, key2: {'3': super3}})

    def test_get_range_super_column(self):
        key = 'TestSuperColumnFamily.test_get_range_super_column'
        subcolumns = {'sub1': 'val1', 'sub2': 'val2', 'sub3': 'val3'}
        columns = {'1': subcolumns}
        scf.insert(key, columns)
        assert_equal(list(scf.get_range(start=key, finish=key, super_column='1')),
                     [(key, subcolumns)])
        assert_equal(list(scf.get_range(start=key, finish=key, super_column='1', columns=['sub1'])),
                     [(key, {'sub1': 'val1'})])
        assert_equal(list(scf.get_range(start=key, finish=key, super_column='1', column_start='sub3')),
                     [(key, {'sub3': 'val3'})])
        assert_equal(list(scf.get_range(start=key, finish=key, super_column='1', column_finish='sub1')),
                     [(key, {'sub1': 'val1'})])
        assert_equal(list(scf.get_range(start=key, finish=key, super_column='1', column_count=1)),
                     [(key, {'sub1': 'val1'})])
        assert_equal(list(scf.get_range(start=key, finish=key, super_column='1', column_count=1, column_reversed=True)),
                     [(key, {'sub3': 'val3'})])

    def test_get_range_super_columns(self):
        key = 'TestSuperColumnFamily.test_get_range_super_columns'
        super1 = {'sub1': 'val1', 'sub2': 'val2'}
        super2 = {'sub3': 'val3', 'sub4': 'val4'}
        super3 = {'sub5': 'val5', 'sub6': 'val6'}
        columns = {'1': super1, '2': super2, '3': super3}
        scf.insert(key, columns)
        assert_equal(list(scf.get_range(start=key, finish=key, columns=['1'])),
                     [(key, {'1': super1})])
        assert_equal(list(scf.get_range(start=key, finish=key, column_start='3')),
                     [(key, {'3': super3})])
        assert_equal(list(scf.get_range(start=key, finish=key, column_finish='1')),
                     [(key, {'1': super1})])
        assert_equal(list(scf.get_range(start=key, finish=key, column_count=1)),
                     [(key, {'1': super1})])
        assert_equal(list(scf.get_range(start=key, finish=key, column_count=1, column_reversed=True)),
                     [(key, {'3': super3})])

    def test_get_count_super_column(self):
        key = 'TestSuperColumnFamily.test_get_count_super_column'
        subcolumns = {'sub1': 'val1', 'sub2': 'val2', 'sub3': 'val3'}
        columns = {'1': subcolumns}
        scf.insert(key, columns)
        assert_equal(scf.get_count(key, super_column='1'),                       3)
        assert_equal(scf.get_count(key, super_column='1', columns=['sub1']),     1)
        assert_equal(scf.get_count(key, super_column='1', column_start='sub3'),  1)
        assert_equal(scf.get_count(key, super_column='1', column_finish='sub1'), 1)

    def test_get_count_super_columns(self):
        key = 'TestSuperColumnFamily.test_get_count_super_columns'
        columns = {'1': {'sub1': 'val1'}, '2': {'sub2': 'val2'}, '3': {'sub3': 'val3'}}
        scf.insert(key, columns)
        assert_equal(scf.get_count(key),                    3)
        assert_equal(scf.get_count(key, columns=['1']),     1)
        assert_equal(scf.get_count(key, column_start='3'),  1)
        assert_equal(scf.get_count(key, column_finish='1'), 1)

    def test_multiget_count_super_column(self):
        key1 = 'TestSuperColumnFamily.test_multiget_count_super_column1'
        key2 = 'TestSuperColumnFamily.test_multiget_count_super_column2'
        keys = [key1, key2]
        subcolumns = {'sub1': 'val1', 'sub2': 'val2', 'sub3': 'val3'}
        columns = {'1': subcolumns}
        scf.insert(key1, columns)
        scf.insert(key2, columns)
        assert_equal(scf.multiget_count(keys, super_column='1'),                       {key1: 3, key2: 3})
        assert_equal(scf.multiget_count(keys, super_column='1', columns=['sub1']),     {key1: 1, key2: 1})
        assert_equal(scf.multiget_count(keys, super_column='1', column_start='sub3'),  {key1: 1, key2: 1})
        assert_equal(scf.multiget_count(keys, super_column='1', column_finish='sub1'), {key1: 1, key2: 1})

    def test_multiget_count_super_columns(self):
        key1 = 'TestSuperColumnFamily.test_multiget_count_super_columns1'
        key2 = 'TestSuperColumnFamily.test_multiget_count_super_columns2'
        keys = [key1, key2]
        columns = {'1': {'sub1': 'val1'}, '2': {'sub2': 'val2'}, '3': {'sub3': 'val3'}}
        scf.insert(key1, columns)
        scf.insert(key2, columns)
        assert_equal(scf.multiget_count(keys),                    {key1: 3, key2: 3})
        assert_equal(scf.multiget_count(keys, columns=['1']),     {key1: 1, key2: 1})
        assert_equal(scf.multiget_count(keys, column_start='3'),  {key1: 1, key2: 1})
        assert_equal(scf.multiget_count(keys, column_finish='1'), {key1: 1, key2: 1})

    def test_batch_insert(self):
        key1 = 'TestSuperColumnFamily.test_batch_insert1'
        key2 = 'TestSuperColumnFamily.test_batch_insert2'
        columns = {'1': {'sub1': 'val1'}, '2': {'sub2': 'val2', 'sub3': 'val3'}}
        scf.batch_insert({key1: columns, key2: columns})
        assert_equal(scf.get(key1), columns)
        assert_equal(scf.get(key2), columns)

    def test_add(self):
        counter_scf.add('key', 'col', super_column='scol')
        result = counter_scf.get('key', super_column='scol')
        assert_equal(result['col'], 1)

        counter_scf.add('key', 'col', super_column='scol')
        result = counter_scf.get('key', super_column='scol')
        assert_equal(result['col'], 2)

        counter_scf.add('key', 'col2', super_column='scol')
        result = counter_scf.get('key', super_column='scol')
        assert_equal(result, {'col': 2, 'col2': 1})

    def test_remove(self):
        key = 'TestSuperColumnFamily.test_remove'
        columns = {'1': {'sub1': 'val1'}, '2': {'sub2': 'val2', 'sub3': 'val3'}, '3': {'sub4': 'val4'}}
        scf.insert(key, columns)
        assert_equal(scf.get_count(key), 3)
        scf.remove(key, super_column='1')
        assert_equal(scf.get_count(key), 2)
        scf.remove(key, columns=['3'])
        assert_equal(scf.get_count(key), 1)

        assert_equal(scf.get_count(key, super_column='2'), 2)
        scf.remove(key, super_column='2', columns=['sub2'])
        assert_equal(scf.get_count(key, super_column='2'), 1)

    def test_remove_counter(self):
        key = 'test_remove_counter'
        counter_scf.add(key, 'col', super_column='scol')
        result = counter_scf.get(key, super_column='scol')
        assert_equal(result['col'], 1)

        counter_scf.remove_counter(key, 'col', super_column='scol')
        assert_raises(NotFoundException, scf.get, key)

    def test_xget_counter(self):
        key = 'test_xget_counter'
        counter_scf.insert(key, {'scol': {'col1': 1}})
        res = list(counter_scf.xget(key))
        assert_equal(res, [('scol', {'col1': 1})])

        counter_scf.insert(key, {'scol': {'col1': 1, 'col2': 1}})
        res = list(counter_scf.xget(key))
        assert_equal(res, [('scol', {'col1': 2, 'col2': 1})])

########NEW FILE########
__FILENAME__ = test_columnfamilymap
from datetime import datetime
import unittest
import uuid

from nose.tools import assert_raises, assert_equal, assert_true
from nose.plugins.skip import SkipTest

import pycassa.types as types
from pycassa import index, ColumnFamily, ConnectionPool, \
    ColumnFamilyMap, NotFoundException, SystemManager

from tests.util import requireOPP

CF = 'Standard1'
SCF = 'Super1'
INDEXED_CF = 'Indexed1'
pool = None
sys_man = None

def setup_module():
    global pool, sys_man
    credentials = {'username': 'jsmith', 'password': 'havebadpass'}
    pool = ConnectionPool(keyspace='PycassaTestKeyspace',
            credentials=credentials, timeout=1.0)
    sys_man = SystemManager()

def teardown_module():
    pool.dispose()


class TestUTF8(object):
    key = types.LexicalUUIDType()
    strcol = types.AsciiType(default='default')
    intcol = types.LongType(default=0)
    floatcol = types.FloatType(default=0.0)
    datetimecol = types.DateType()

    def __str__(self):
        return str(map(str, [self.strcol, self.intcol, self.floatcol, self.datetimecol]))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return self.__dict__ != other.__dict__


class TestIndex(object):
    birthdate = types.LongType(default=0)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return self.__dict__ != other.__dict__


class TestEmpty(object):
    pass


class TestColumnFamilyMap(unittest.TestCase):

    def setUp(self):
        self.sys_man = sys_man
        self.map = ColumnFamilyMap(TestUTF8, pool, CF)
        self.indexed_map = ColumnFamilyMap(TestIndex, pool, INDEXED_CF)
        self.empty_map = ColumnFamilyMap(TestEmpty, pool, CF, raw_columns=True)

    def tearDown(self):
        for instance in self.map.get_range():
            self.map.remove(instance)
        for instance in self.indexed_map.get_range():
            self.indexed_map.remove(instance)

    def instance(self):
        instance = TestUTF8()
        instance.key = uuid.uuid4()
        instance.strcol = '1'
        instance.intcol = 2
        instance.floatcol = 3.5
        instance.datetimecol = datetime.now().replace(microsecond=0)

        return instance

    def test_empty(self):
        key = uuid.uuid4()
        assert_raises(NotFoundException, self.map.get, key)
        assert_equal(len(self.map.multiget([key])), 0)

    def test_insert_get(self):
        instance = self.instance()
        assert_raises(NotFoundException, self.map.get, instance.key)
        ts = self.map.insert(instance)
        assert_true(isinstance(ts, (int, long)))
        assert_equal(self.map.get(instance.key), instance)

    def test_insert_get_omitting_columns(self):
        """
        When omitting columns, pycassa should not try to insert the CassandraType
        instance on a ColumnFamilyMap object
        """
        instance2 = TestUTF8()
        instance2.key = uuid.uuid4()
        instance2.strcol = 'lol'
        instance2.intcol = 2
        assert_raises(NotFoundException, self.map.get, instance2.key)
        self.map.insert(instance2)
        ret_inst = self.map.get(instance2.key)
        assert_equal(ret_inst.key, instance2.key)
        assert_equal(ret_inst.strcol, instance2.strcol)
        assert_equal(ret_inst.intcol, instance2.intcol)

        ## these lines are commented out because, though they should work, wont
        ## because CassandraTypes are not descriptors when used on a ColumnFamilyMap
        ## instance, they are merely class attributes that are overwritten at runtime

        # assert_equal(ret_inst.floatcol, instance2.floatcol)
        # assert_equal(ret_inst.datetimecol, instance2.datetimecol)
        # assert_equal(self.map.get(instance2.key), instance2)

    def test_insert_get_indexed_slices(self):
        instance1 = TestIndex()
        instance1.key = 'key1'
        instance1.birthdate = 1L
        self.indexed_map.insert(instance1)

        instance2 = TestIndex()
        instance2.key = 'key2'
        instance2.birthdate = 1L
        self.indexed_map.insert(instance2)

        instance3 = TestIndex()
        instance3.key = 'key3'
        instance3.birthdate = 2L
        self.indexed_map.insert(instance3)

        expr = index.create_index_expression(column_name='birthdate', value=2L)
        clause = index.create_index_clause([expr])

        result = self.indexed_map.get_indexed_slices(index_clause=clause)
        count = 0
        for instance in result:
            assert_equal(instance, instance3)
            count += 1
        assert_equal(count, 1)

    def test_insert_multiget(self):
        instance1 = self.instance()
        instance2 = self.instance()
        missing_key = uuid.uuid4()

        self.map.insert(instance1)
        self.map.insert(instance2)
        rows = self.map.multiget([instance1.key, instance2.key, missing_key])
        assert_equal(len(rows), 2)
        assert_equal(rows[instance1.key], instance1)
        assert_equal(rows[instance2.key], instance2)
        assert_true(missing_key not in rows)

    @requireOPP
    def test_insert_get_range(self):
        instances = [self.instance() for i in range(5)]
        instances = sorted(instances, key=lambda instance: instance.key)
        for instance in instances:
            self.map.insert(instance)

        rows = list(self.map.get_range(start=instances[0].key, finish=instances[-1].key))
        assert_equal(len(rows), len(instances))
        assert_equal(rows, instances)

    def test_remove(self):
        instance = self.instance()

        self.map.insert(instance)
        self.map.remove(instance)
        assert_raises(NotFoundException, self.map.get, instance.key)

    def test_does_not_insert_extra_column(self):
        instance = self.instance()
        instance.othercol = 'Test'

        self.map.insert(instance)

        get_instance = self.map.get(instance.key)
        assert_equal(get_instance.strcol, instance.strcol)
        assert_equal(get_instance.intcol, instance.intcol)
        assert_equal(get_instance.floatcol, instance.floatcol)
        assert_equal(get_instance.datetimecol, instance.datetimecol)
        assert_raises(AttributeError, getattr, get_instance, 'othercol')

    def test_has_defaults(self):
        key = uuid.uuid4()
        ColumnFamily.insert(self.map, key, {'strcol': '1'})
        instance = self.map.get(key)

        assert_equal(instance.intcol, TestUTF8.intcol.default)
        assert_equal(instance.floatcol, TestUTF8.floatcol.default)
        assert_equal(instance.datetimecol, TestUTF8.datetimecol.default)

    def test_batch_insert(self):
        instances = []
        for i in range(3):
            instance = TestUTF8()
            instance.key = uuid.uuid4()
            instance.strcol = 'instance%s' % (i + 1)
            instances.append(instance)

        for i in instances:
            assert_raises(NotFoundException, self.map.get, i.key)

        self.map.batch_insert(instances)

        for i in instances:
            get_instance = self.map.get(i.key)
            assert_equal(get_instance.key, i.key)
            assert_equal(get_instance.strcol, i.strcol)

class TestSuperColumnFamilyMap(unittest.TestCase):

    def setUp(self):
        self.map = ColumnFamilyMap(TestUTF8, pool, SCF)

    def tearDown(self):
        for scols in self.map.get_range():
            for instance in scols.values():
                self.map.remove(instance)

    def instance(self, super_column):
        instance = TestUTF8()
        instance.key = uuid.uuid4()
        instance.super_column = super_column
        instance.strcol = '1'
        instance.intcol = 2
        instance.floatcol = 3.5
        instance.datetimecol = datetime.now().replace(microsecond=0)

        return instance

    def test_super(self):
        instance = self.instance('super1')
        assert_raises(NotFoundException, self.map.get, instance.key)
        self.map.insert(instance)
        res = self.map.get(instance.key)[instance.super_column]
        assert_equal(res, instance)
        assert_equal(self.map.multiget([instance.key])[instance.key][instance.super_column], instance)
        assert_equal(list(self.map.get_range(start=instance.key, finish=instance.key)), [{instance.super_column: instance}])

    def test_super_remove(self):
        instance1 = self.instance('super1')
        assert_raises(NotFoundException, self.map.get, instance1.key)
        self.map.insert(instance1)

        instance2 = self.instance('super2')
        self.map.insert(instance2)

        self.map.remove(instance2)
        assert_equal(len(self.map.get(instance1.key)), 1)
        assert_equal(self.map.get(instance1.key)[instance1.super_column], instance1)

    def test_batch_insert_super(self):
        instances = []
        for i in range(3):
            instance = self.instance('super_batch%s' % (i + 1))
            instances.append(instance)

        for i in instances:
            assert_raises(NotFoundException, self.map.get, i.key)

        self.map.batch_insert(instances)

        for i in instances:
            result = self.map.get(i.key)
            get_instance = result[i.super_column]
            assert_equal(len(result), 1)
            assert_equal(get_instance.key, i.key)
            assert_equal(get_instance.super_column, i.super_column)
            assert_equal(get_instance.strcol, i.strcol)

########NEW FILE########
__FILENAME__ = test_connection_pooling
import threading
import unittest
import time

from nose.tools import assert_raises, assert_equal, assert_true
from pycassa import ColumnFamily, ConnectionPool, InvalidRequestError,\
                    NoConnectionAvailable, MaximumRetryException, AllServersUnavailable
from pycassa.logging.pool_stats_logger import StatsLogger
from pycassa.cassandra.ttypes import ColumnPath
from pycassa.cassandra.ttypes import InvalidRequestException
from pycassa.cassandra.ttypes import NotFoundException


_credentials = {'username': 'jsmith', 'password': 'havebadpass'}

def _get_list():
    return ['foo:bar']

class PoolingCase(unittest.TestCase):

    def tearDown(self):
        pool = ConnectionPool('PycassaTestKeyspace')
        cf = ColumnFamily(pool, 'Standard1')
        for key, cols in cf.get_range():
            cf.remove(key)

    def test_basic_pools(self):
        pool = ConnectionPool('PycassaTestKeyspace', credentials=_credentials)
        cf = ColumnFamily(pool, 'Standard1')
        cf.insert('key1', {'col': 'val'})
        pool.dispose()

    def test_empty_list(self):
        assert_raises(AllServersUnavailable, ConnectionPool, 'PycassaTestKeyspace', server_list=[])

    def test_server_list_func(self):
        stats_logger = StatsLoggerWithListStorage()
        pool = ConnectionPool('PycassaTestKeyspace', server_list=_get_list,
                         listeners=[stats_logger], prefill=False)
        assert_equal(stats_logger.serv_list, ['foo:bar'])
        assert_equal(stats_logger.stats['list'], 1)
        pool.dispose()

    def test_queue_pool(self):
        stats_logger = StatsLoggerWithListStorage()
        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=10000,
                         prefill=True, pool_timeout=0.1, timeout=1,
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         listeners=[stats_logger], use_threadlocal=False)
        conns = []
        for i in range(10):
            conns.append(pool.get())

        assert_equal(stats_logger.stats['created']['success'], 10)
        assert_equal(stats_logger.stats['checked_out'], 10)

        # Pool is maxed out now
        assert_raises(NoConnectionAvailable, pool.get)
        assert_equal(stats_logger.stats['created']['success'], 10)
        assert_equal(stats_logger.stats['at_max'], 1)

        for i in range(0, 5):
            pool.return_conn(conns[i])
        assert_equal(stats_logger.stats['disposed']['success'], 0)
        assert_equal(stats_logger.stats['checked_in'], 5)

        for i in range(5, 10):
            pool.return_conn(conns[i])
        assert_equal(stats_logger.stats['disposed']['success'], 5)
        assert_equal(stats_logger.stats['checked_in'], 10)

        conns = []

        # These connections should come from the pool
        for i in range(5):
            conns.append(pool.get())
        assert_equal(stats_logger.stats['created']['success'], 10)
        assert_equal(stats_logger.stats['checked_out'], 15)

        # But these will need to be made
        for i in range(5):
            conns.append(pool.get())
        assert_equal(stats_logger.stats['created']['success'], 15)
        assert_equal(stats_logger.stats['checked_out'], 20)

        assert_equal(stats_logger.stats['disposed']['success'], 5)
        for i in range(10):
            conns[i].return_to_pool()
        assert_equal(stats_logger.stats['checked_in'], 20)
        assert_equal(stats_logger.stats['disposed']['success'], 10)

        assert_raises(InvalidRequestError, conns[0].return_to_pool)
        assert_equal(stats_logger.stats['checked_in'], 20)
        assert_equal(stats_logger.stats['disposed']['success'], 10)

        print "in test:", id(conns[-1])
        conns[-1].return_to_pool()
        assert_equal(stats_logger.stats['checked_in'], 20)
        assert_equal(stats_logger.stats['disposed']['success'], 10)

        pool.dispose()

    def test_queue_pool_threadlocal(self):
        stats_logger = StatsLoggerWithListStorage()
        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=10000,
                         prefill=True, pool_timeout=0.01, timeout=1,
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         listeners=[stats_logger], use_threadlocal=True)
        conns = []

        assert_equal(stats_logger.stats['created']['success'], 5)
        # These connections should all be the same
        for i in range(10):
            conns.append(pool.get())
        assert_equal(stats_logger.stats['created']['success'], 5)
        assert_equal(stats_logger.stats['checked_out'], 1)

        for i in range(0, 5):
            pool.return_conn(conns[i])
        assert_equal(stats_logger.stats['checked_in'], 1)
        for i in range(5, 10):
            pool.return_conn(conns[i])
        assert_equal(stats_logger.stats['checked_in'], 1)

        conns = []

        assert_equal(stats_logger.stats['created']['success'], 5)
        # A single connection should come from the pool
        for i in range(5):
            conns.append(pool.get())
        assert_equal(stats_logger.stats['created']['success'], 5)
        assert_equal(stats_logger.stats['checked_out'], 2)

        for conn in conns:
            pool.return_conn(conn)

        conns = []
        threads = []
        stats_logger.reset()

        def checkout_return():
            conn = pool.get()
            time.sleep(1)
            pool.return_conn(conn)

        for i in range(5):
            threads.append(threading.Thread(target=checkout_return))
            threads[-1].start()
        for thread in threads:
            thread.join()

        assert_equal(stats_logger.stats['created']['success'], 0) # Still 5 connections in pool
        assert_equal(stats_logger.stats['checked_out'], 5)
        assert_equal(stats_logger.stats['checked_in'], 5)

        # These should come from the pool
        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=checkout_return))
            threads[-1].start()
        for thread in threads:
            thread.join()
        assert_equal(stats_logger.stats['created']['success'], 0)
        assert_equal(stats_logger.stats['checked_out'], 10)
        assert_equal(stats_logger.stats['checked_in'], 10)

        pool.dispose()

    def test_queue_pool_no_prefill(self):
        stats_logger = StatsLoggerWithListStorage()
        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=10000,
                         prefill=False, pool_timeout=0.1, timeout=1,
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         listeners=[stats_logger], use_threadlocal=False)
        conns = []
        for i in range(10):
            conns.append(pool.get())
            assert_equal(stats_logger.stats['created']['success'], i + 1)
            assert_equal(stats_logger.stats['checked_out'], i + 1)

        # Pool is maxed out now
        assert_raises(NoConnectionAvailable, pool.get)
        assert_equal(stats_logger.stats['created']['success'], 10)
        assert_equal(stats_logger.stats['at_max'], 1)

        for i in range(0, 5):
            pool.return_conn(conns[i])
            assert_equal(stats_logger.stats['checked_in'], i + 1)
            assert_equal(stats_logger.stats['disposed']['success'], 0)

        for i in range(5, 10):
            pool.return_conn(conns[i])
            assert_equal(stats_logger.stats['checked_in'], i + 1)
            assert_equal(stats_logger.stats['disposed']['success'], (i - 5) + 1)

        conns = []

        # These connections should come from the pool
        for i in range(5):
            conns.append(pool.get())
            assert_equal(stats_logger.stats['created']['success'], 10)
            assert_equal(stats_logger.stats['checked_out'], (i + 10) + 1)

        # But these will need to be made
        for i in range(5):
            conns.append(pool.get())
            assert_equal(stats_logger.stats['created']['success'], (i + 10) + 1)
            assert_equal(stats_logger.stats['checked_out'], (i + 15) + 1)

        assert_equal(stats_logger.stats['disposed']['success'], 5)
        for i in range(10):
            conns[i].return_to_pool()
            assert_equal(stats_logger.stats['checked_in'], (i + 10) + 1)
        assert_equal(stats_logger.stats['disposed']['success'], 10)

        # Make sure a double return doesn't change our counts
        assert_raises(InvalidRequestError, conns[0].return_to_pool)
        assert_equal(stats_logger.stats['checked_in'], 20)
        assert_equal(stats_logger.stats['disposed']['success'], 10)

        conns[-1].return_to_pool()
        assert_equal(stats_logger.stats['checked_in'], 20)
        assert_equal(stats_logger.stats['disposed']['success'], 10)

        pool.dispose()

    def test_queue_pool_recycle(self):
        stats_logger = StatsLoggerWithListStorage()
        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=1,
                         prefill=True, pool_timeout=0.5, timeout=1,
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         listeners=[stats_logger], use_threadlocal=False)

        cf = ColumnFamily(pool, 'Standard1')
        columns = {'col1': 'val', 'col2': 'val'}
        for i in range(10):
            cf.insert('key', columns)

        assert_equal(stats_logger.stats['recycled'], 5)

        pool.dispose()
        stats_logger.reset()

        # Try with threadlocal=True
        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=1,
                         prefill=False, pool_timeout=0.5, timeout=1,
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         listeners=[stats_logger], use_threadlocal=True)

        cf = ColumnFamily(pool, 'Standard1')
        for i in range(10):
            cf.insert('key', columns)

        pool.dispose()
        assert_equal(stats_logger.stats['recycled'], 5)

    def test_pool_connection_failure(self):
        stats_logger = StatsLoggerWithListStorage()

        def get_extra():
            """Make failure count adjustments based on whether or not
            the permuted list starts with a good host:port"""
            if stats_logger.serv_list[0] == 'localhost:9160':
                return 0
            else:
                return 1

        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=10000, prefill=True,
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         pool_timeout=0.01, timeout=0.05,
                         listeners=[stats_logger], use_threadlocal=False,
                         server_list=['localhost:9160', 'foobar:1'])

        assert_equal(stats_logger.stats['failed'], 4 + get_extra())

        for i in range(0, 7):
            pool.get()

        assert_equal(stats_logger.stats['failed'], 6 + get_extra())

        pool.dispose()
        stats_logger.reset()

        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=10000, prefill=True,
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         pool_timeout=0.01, timeout=0.05,
                         listeners=[stats_logger], use_threadlocal=True,
                         server_list=['localhost:9160', 'foobar:1'])

        assert_equal(stats_logger.stats['failed'], 4 + get_extra())

        threads = []
        for i in range(0, 7):
            threads.append(threading.Thread(target=pool.get))
            threads[-1].start()
        for thread in threads:
            thread.join()

        assert_equal(stats_logger.stats['failed'], 6 + get_extra())

        pool.dispose()

    def test_queue_failover(self):
        for prefill in (True, False):
            stats_logger = StatsLoggerWithListStorage()
            pool = ConnectionPool(pool_size=1, max_overflow=0, recycle=10000,
                             prefill=prefill, timeout=1,
                             keyspace='PycassaTestKeyspace', credentials=_credentials,
                             listeners=[stats_logger], use_threadlocal=False,
                             server_list=['localhost:9160', 'localhost:9160'])

            cf = ColumnFamily(pool, 'Standard1')

            for i in range(1, 5):
                conn = pool.get()
                setattr(conn, 'send_batch_mutate', conn._fail_once)
                conn._should_fail = True
                conn.return_to_pool()

                # The first insert attempt should fail, but failover should occur
                # and the insert should succeed
                cf.insert('key', {'col': 'val%d' % i, 'col2': 'val'})
                assert_equal(stats_logger.stats['failed'], i)
                assert_equal(cf.get('key'), {'col': 'val%d' % i, 'col2': 'val'})

            pool.dispose()

    def test_queue_threadlocal_failover(self):
        stats_logger = StatsLoggerWithListStorage()
        pool = ConnectionPool(pool_size=1, max_overflow=0, recycle=10000,
                         prefill=True, timeout=0.05,
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         listeners=[stats_logger], use_threadlocal=True,
                         server_list=['localhost:9160', 'localhost:9160'])

        cf = ColumnFamily(pool, 'Standard1')

        for i in range(1, 5):
            conn = pool.get()
            setattr(conn, 'send_batch_mutate', conn._fail_once)
            conn._should_fail = True
            conn.return_to_pool()

            # The first insert attempt should fail, but failover should occur
            # and the insert should succeed
            cf.insert('key', {'col': 'val%d' % i, 'col2': 'val'})
            assert_equal(stats_logger.stats['failed'], i)
            assert_equal(cf.get('key'), {'col': 'val%d' % i, 'col2': 'val'})

        pool.dispose()
        stats_logger.reset()

        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=10000,
                         prefill=True, timeout=0.05,
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         listeners=[stats_logger], use_threadlocal=True,
                         server_list=['localhost:9160', 'localhost:9160'])

        cf = ColumnFamily(pool, 'Standard1')

        for i in range(5):
            conn = pool.get()
            setattr(conn, 'send_batch_mutate', conn._fail_once)
            conn._should_fail = True
            conn.return_to_pool()

        threads = []
        args = ('key', {'col': 'val', 'col2': 'val'})
        for i in range(5):
            threads.append(threading.Thread(target=cf.insert, args=args))
            threads[-1].start()
        for thread in threads:
            thread.join()

        assert_equal(stats_logger.stats['failed'], 5)

        pool.dispose()

    def test_queue_retry_limit(self):
        for prefill in (True, False):
            stats_logger = StatsLoggerWithListStorage()
            pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=10000,
                             prefill=prefill, max_retries=3, # allow 3 retries
                             keyspace='PycassaTestKeyspace', credentials=_credentials,
                             listeners=[stats_logger], use_threadlocal=False,
                             server_list=['localhost:9160', 'localhost:9160'])

            # Corrupt all of the connections
            for i in range(5):
                conn = pool.get()
                setattr(conn, 'send_batch_mutate', conn._fail_once)
                conn._should_fail = True
                conn.return_to_pool()

            cf = ColumnFamily(pool, 'Standard1')
            assert_raises(MaximumRetryException, cf.insert, 'key', {'col': 'val', 'col2': 'val'})
            assert_equal(stats_logger.stats['failed'], 4) # On the 4th failure, didn't retry

            pool.dispose()

    def test_queue_failure_on_retry(self):
        stats_logger = StatsLoggerWithListStorage()
        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=10000,
                         prefill=True, max_retries=3, # allow 3 retries
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         listeners=[stats_logger], use_threadlocal=False,
                         server_list=['localhost:9160', 'localhost:9160'])

        def raiser():
            raise IOError
        # Replace wrapper will open a connection to get the version, so if it
        # fails we need to retry as with any other connection failure
        pool._replace_wrapper = raiser

        # Corrupt all of the connections
        for i in range(5):
            conn = pool.get()
            setattr(conn, 'send_batch_mutate', conn._fail_once)
            conn._should_fail = True
            conn.return_to_pool()

        cf = ColumnFamily(pool, 'Standard1')
        assert_raises(MaximumRetryException, cf.insert, 'key', {'col': 'val', 'col2': 'val'})
        assert_equal(stats_logger.stats['failed'], 4) # On the 4th failure, didn't retry

        pool.dispose()

    def test_queue_threadlocal_retry_limit(self):
        stats_logger = StatsLoggerWithListStorage()
        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=10000,
                         prefill=True, max_retries=3, # allow 3 retries
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         listeners=[stats_logger], use_threadlocal=True,
                         server_list=['localhost:9160', 'localhost:9160'])

        # Corrupt all of the connections
        for i in range(5):
            conn = pool.get()
            setattr(conn, 'send_batch_mutate', conn._fail_once)
            conn._should_fail = True
            conn.return_to_pool()

        cf = ColumnFamily(pool, 'Standard1')
        assert_raises(MaximumRetryException, cf.insert, 'key', {'col': 'val', 'col2': 'val'})
        assert_equal(stats_logger.stats['failed'], 4) # On the 4th failure, didn't retry

        pool.dispose()

    def test_queue_failure_with_no_retries(self):
        stats_logger = StatsLoggerWithListStorage()
        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=10000,
                         prefill=True, max_retries=3, # allow 3 retries
                         keyspace='PycassaTestKeyspace', credentials=_credentials,
                         listeners=[stats_logger], use_threadlocal=False,
                         server_list=['localhost:9160', 'localhost:9160'])

        # Corrupt all of the connections
        for i in range(5):
            conn = pool.get()
            setattr(conn, 'send_batch_mutate', conn._fail_once)
            conn._should_fail = True
            conn.return_to_pool()

        cf = ColumnFamily(pool, 'Counter1')
        assert_raises(MaximumRetryException, cf.insert, 'key', {'col': 2, 'col2': 2})
        assert_equal(stats_logger.stats['failed'], 1)  # didn't retry at all

        pool.dispose()

    def test_failure_connection_info(self):
        stats_logger = StatsLoggerRequestInfo()
        pool = ConnectionPool(pool_size=1, max_overflow=0, recycle=10000,
                              prefill=True, max_retries=0,
                              keyspace='PycassaTestKeyspace', credentials=_credentials,
                              listeners=[stats_logger], use_threadlocal=True,
                              server_list=['localhost:9160'])
        cf = ColumnFamily(pool, 'Counter1')

        # Corrupt the connection
        conn = pool.get()
        setattr(conn, 'send_get', conn._fail_once)
        conn._should_fail = True
        conn.return_to_pool()

        assert_raises(MaximumRetryException, cf.get, 'greunt', columns=['col'])
        assert_true('request' in stats_logger.failure_dict['connection'].info)
        request = stats_logger.failure_dict['connection'].info['request']
        assert_equal(request['method'], 'get')
        assert_equal(request['args'], ('greunt', ColumnPath('Counter1', None, 'col'), 1))
        assert_equal(request['kwargs'], {})

    def test_pool_invalid_request(self):
        stats_logger = StatsLoggerWithListStorage()
        pool = ConnectionPool(pool_size=1, max_overflow=0, recycle=10000,
                         prefill=True, max_retries=3,
                         keyspace='PycassaTestKeyspace',
                         credentials=_credentials,
                         listeners=[stats_logger], use_threadlocal=False,
                         server_list=['localhost:9160'])
        cf = ColumnFamily(pool, 'Standard1')
        # Make sure the pool doesn't hide and retries invalid requests
        assert_raises(InvalidRequestException, cf.add, 'key', 'col')
        assert_raises(NotFoundException, cf.get, 'none')
        pool.dispose()


class StatsLoggerWithListStorage(StatsLogger):

    def obtained_server_list(self, dic):
        StatsLogger.obtained_server_list(self, dic)
        self.serv_list = dic.get('server_list')


class StatsLoggerRequestInfo(StatsLogger):

    def connection_failed(self, dic):
        StatsLogger.connection_failed(self, dic)
        self.failure_dict = dic

########NEW FILE########
__FILENAME__ = test_pool_logger
from unittest import TestCase
from nose.tools import assert_equal, assert_raises

from pycassa.logging.pool_stats_logger import StatsLogger
from pycassa.pool import ConnectionPool, NoConnectionAvailable, InvalidRequestError

__author__ = 'gilles'

_credentials = {'username': 'jsmith', 'password': 'havebadpass'}

class TestStatsLogger(TestCase):
    def __init__(self, methodName='runTest'):
        super(TestStatsLogger, self).__init__(methodName)

    def setUp(self):
        super(TestStatsLogger, self).setUp()
        self.logger = StatsLogger()

    def test_empty(self):
        assert_equal(self.logger.stats, self.logger._stats)

    def test_connection_created(self):
        self.logger.connection_created({'level': 'info'})
        self.logger.connection_created({'level': 'error'})

        stats = self.logger.stats
        assert_equal(stats['created']['success'], 1)
        assert_equal(stats['created']['failure'], 1)

    def test_connection_checked(self):
        self.logger.connection_checked_out({})
        self.logger.connection_checked_out({})
        self.logger.connection_checked_in({})
        stats = self.logger.stats
        assert_equal(stats['checked_out'], 2)
        assert_equal(stats['checked_in'], 1)
        assert_equal(stats['opened'], {'current': 1, 'max': 2})

    def test_connection_disposed(self):
        self.logger.connection_disposed({'level': 'info'})
        self.logger.connection_disposed({'level': 'error'})

        stats = self.logger.stats
        assert_equal(stats['disposed']['success'], 1)
        assert_equal(stats['disposed']['failure'], 1)

    def test_connection_recycled(self):
        self.logger.connection_recycled({})
        stats = self.logger.stats
        assert_equal(stats['recycled'], 1)

    def test_connection_failed(self):
        self.logger.connection_failed({})
        stats = self.logger.stats
        assert_equal(stats['failed'], 1)

    def test_obtained_server_list(self):
        self.logger.obtained_server_list({})
        stats = self.logger.stats
        assert_equal(stats['list'], 1)

    def test_pool_at_max(self):
        self.logger.pool_at_max({})
        stats = self.logger.stats
        assert_equal(stats['at_max'], 1)


class TestInPool(TestCase):
    def __init__(self, methodName='runTest'):
        super(TestInPool, self).__init__(methodName)

    def test_pool(self):
        listener = StatsLogger()
        pool = ConnectionPool(pool_size=5, max_overflow=5, recycle=10000,
                              prefill=True, pool_timeout=0.1, timeout=1,
                              keyspace='PycassaTestKeyspace', credentials=_credentials,
                              listeners=[listener], use_threadlocal=False)
        conns = []
        for i in range(10):
            conns.append(pool.get())
        assert_equal(listener.stats['created']['success'], 10)
        assert_equal(listener.stats['created']['failure'], 0)
        assert_equal(listener.stats['checked_out'], 10)
        assert_equal(listener.stats['opened'], {'current': 10, 'max': 10})

        # Pool is maxed out now
        assert_raises(NoConnectionAvailable, pool.get)
        assert_equal(listener.stats['created']['success'], 10)
        assert_equal(listener.stats['checked_out'], 10)
        assert_equal(listener.stats['opened'], {'current': 10, 'max': 10})
        assert_equal(listener.stats['at_max'], 1)

        for i in range(0, 5):
            pool.return_conn(conns[i])
        assert_equal(listener.stats['disposed']['success'], 0)
        assert_equal(listener.stats['checked_in'], 5)
        assert_equal(listener.stats['opened'], {'current': 5, 'max': 10})

        for i in range(5, 10):
            pool.return_conn(conns[i])
        assert_equal(listener.stats['disposed']['success'], 5)
        assert_equal(listener.stats['checked_in'], 10)

        conns = []

        # These connections should come from the pool
        for i in range(5):
            conns.append(pool.get())
        assert_equal(listener.stats['created']['success'], 10)
        assert_equal(listener.stats['checked_out'], 15)

        # But these will need to be made
        for i in range(5):
            conns.append(pool.get())
        assert_equal(listener.stats['created']['success'], 15)
        assert_equal(listener.stats['checked_out'], 20)

        assert_equal(listener.stats['disposed']['success'], 5)
        for i in range(10):
            conns[i].return_to_pool()
        assert_equal(listener.stats['checked_in'], 20)
        assert_equal(listener.stats['disposed']['success'], 10)

        assert_raises(InvalidRequestError, conns[0].return_to_pool)
        assert_equal(listener.stats['checked_in'], 20)
        assert_equal(listener.stats['disposed']['success'], 10)

        print "in test:", id(conns[-1])
        conns[-1].return_to_pool()
        assert_equal(listener.stats['checked_in'], 20)
        assert_equal(listener.stats['disposed']['success'], 10)

        pool.dispose()

########NEW FILE########
__FILENAME__ = test_system_manager
import unittest

from nose import SkipTest
from nose.tools import assert_equal, assert_raises

from pycassa.pool import ConnectionPool
from pycassa.columnfamily import ColumnFamily
from pycassa.system_manager import (SIMPLE_STRATEGY, LONG_TYPE, SystemManager,
        UTF8_TYPE, TIME_UUID_TYPE, ASCII_TYPE, INT_TYPE)

from pycassa.cassandra.ttypes import InvalidRequestException
from pycassa.types import LongType

TEST_KS = 'PycassaTestKeyspace'
sys = None

def setup_module():
    global sys
    sys = SystemManager()

def teardown_module():
    sys.close()

class SystemManagerTest(unittest.TestCase):

    def test_system_calls(self):
        # keyspace modifications
        try:
            sys.drop_keyspace('TestKeyspace')
        except InvalidRequestException:
            pass
        sys.create_keyspace('TestKeyspace', SIMPLE_STRATEGY, {'replication_factor': '3'})
        sys.alter_keyspace('TestKeyspace', strategy_options={'replication_factor': '1'})

        sys.create_column_family('TestKeyspace', 'TestCF')
        sys.alter_column_family('TestKeyspace', 'TestCF', comment='testing')
        sys.create_index('TestKeyspace', 'TestCF', 'column', LONG_TYPE)
        sys.drop_column_family('TestKeyspace', 'TestCF')

        sys.describe_ring('TestKeyspace')
        sys.describe_cluster_name()
        sys.describe_version()
        sys.describe_schema_versions()
        sys.list_keyspaces()

        sys.drop_keyspace('TestKeyspace')

    def test_bad_comparator(self):
        sys.create_keyspace('TestKeyspace', SIMPLE_STRATEGY, {'replication_factor': '3'})
        for comparator in [LongType, 123]:
            assert_raises(TypeError, sys.create_column_family,
                    'TestKeyspace', 'TestBadCF', comparator_type=comparator)
        sys.drop_keyspace('TestKeyspace')

    def test_alter_column_non_bytes_type(self):
        sys.create_column_family(TEST_KS, 'LongCF', comparator_type=LONG_TYPE)
        sys.create_index(TEST_KS, 'LongCF', 3, LONG_TYPE)
        pool = ConnectionPool(TEST_KS)
        cf = ColumnFamily(pool, 'LongCF')
        cf.insert('key', {3: 3})
        assert_equal(cf.get('key')[3], 3)

        sys.alter_column(TEST_KS, 'LongCF', 2, LONG_TYPE)
        cf = ColumnFamily(pool, 'LongCF')
        cf.insert('key', {2: 2})
        assert_equal(cf.get('key')[2], 2)

    def test_alter_column_family_default_validation_class(self):
        sys.create_column_family(TEST_KS, 'AlteredCF', default_validation_class=LONG_TYPE)
        pool = ConnectionPool(TEST_KS)
        cf = ColumnFamily(pool, 'AlteredCF')
        assert_equal(cf.default_validation_class, "LongType")

        sys.alter_column_family(TEST_KS, 'AlteredCF', default_validation_class=UTF8_TYPE)
        cf = ColumnFamily(pool, 'AlteredCF')
        assert_equal(cf.default_validation_class, "UTF8Type")

    def test_alter_column_super_cf(self):
        sys.create_column_family(TEST_KS, 'SuperCF', super=True,
                comparator_type=TIME_UUID_TYPE, subcomparator_type=UTF8_TYPE)
        sys.alter_column(TEST_KS, 'SuperCF', 'foobar_col', UTF8_TYPE)

    def test_column_validators(self):
        validators = {'name': UTF8_TYPE, 'age': LONG_TYPE}
        sys.create_column_family(TEST_KS, 'ValidatedCF',
                column_validation_classes=validators)
        pool = ConnectionPool(TEST_KS)
        cf = ColumnFamily(pool, 'ValidatedCF')
        cf.insert('key', {'name': 'John', 'age': 40})
        self.assertEquals(cf.get('key'), {'name': 'John', 'age': 40})

        validators = {'name': ASCII_TYPE, 'age': INT_TYPE}
        sys.alter_column_family(TEST_KS, 'ValidatedCF',
                column_validation_classes=validators)
        cf.load_schema()
        self.assertEquals(cf.get('key'), {'name': 'John', 'age': 40})

    def test_caching_pre_11(self):
        version = tuple(
            [int(v) for v in sys._conn.describe_version().split('.')])
        if version >= (19, 30, 0):
            raise SkipTest('CF specific caching no longer supported.')
        sys.create_column_family(TEST_KS, 'CachedCF10',
            row_cache_size=100, key_cache_size=100,
            row_cache_save_period_in_seconds=3,
            key_cache_save_period_in_seconds=3)
        pool = ConnectionPool(TEST_KS)
        cf = ColumnFamily(pool, 'CachedCF10')
        assert_equal(cf._cfdef.row_cache_size, 100)
        assert_equal(cf._cfdef.key_cache_size, 100)
        assert_equal(cf._cfdef.row_cache_save_period_in_seconds, 3)
        assert_equal(cf._cfdef.key_cache_save_period_in_seconds, 3)
        sys.alter_column_family(TEST_KS, 'CachedCF10',
            row_cache_size=200, key_cache_size=200,
            row_cache_save_period_in_seconds=4,
            key_cache_save_period_in_seconds=4)
        cf1 = ColumnFamily(pool, 'CachedCF10')
        assert_equal(cf1._cfdef.row_cache_size, 200)
        assert_equal(cf1._cfdef.key_cache_size, 200)
        assert_equal(cf1._cfdef.row_cache_save_period_in_seconds, 4)
        assert_equal(cf1._cfdef.key_cache_save_period_in_seconds, 4)

    def test_caching_post_11(self):
        version = tuple(
            [int(v) for v in sys._conn.describe_version().split('.')])
        if version < (19, 30, 0):
            raise SkipTest('CF caching policy not yet supported.')
        sys.create_column_family(TEST_KS, 'CachedCF11')
        pool = ConnectionPool(TEST_KS)
        cf = ColumnFamily(pool, 'CachedCF11')
        assert_equal(cf._cfdef.caching, 'KEYS_ONLY')
        sys.alter_column_family(TEST_KS, 'CachedCF11', caching='all')
        cf = ColumnFamily(pool, 'CachedCF11')
        assert_equal(cf._cfdef.caching, 'ALL')
        sys.alter_column_family(TEST_KS, 'CachedCF11', caching='rows_only')
        cf = ColumnFamily(pool, 'CachedCF11')
        assert_equal(cf._cfdef.caching, 'ROWS_ONLY')
        sys.alter_column_family(TEST_KS, 'CachedCF11', caching='none')
        cf = ColumnFamily(pool, 'CachedCF11')
        assert_equal(cf._cfdef.caching, 'NONE')

########NEW FILE########
__FILENAME__ = util
from functools import wraps

from nose.plugins.skip import SkipTest

def requireOPP(f):
    """ Decorator to require an order-preserving partitioner """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        partitioner = self.sys_man.describe_partitioner()
        if partitioner in ('RandomPartitioner', 'Murmur3Partitioner'):
            raise SkipTest('Must use order preserving partitioner for this test')
        return f(self, *args, **kwargs)

    return wrapper

########NEW FILE########
