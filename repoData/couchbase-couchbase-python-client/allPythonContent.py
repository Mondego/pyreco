__FILENAME__ = admin
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
The contents of this module do not have a stable API and are subject to
change
"""
from collections import deque

import couchbase.connection
import couchbase._libcouchbase as LCB
import couchbase.exceptions as E
from couchbase.user_constants import FMT_JSON


METHMAP = {
    'GET': LCB.LCB_HTTP_METHOD_GET,
    'PUT': LCB.LCB_HTTP_METHOD_PUT,
    'POST': LCB.LCB_HTTP_METHOD_POST,
    'DELETE': LCB.LCB_HTTP_METHOD_DELETE
}


class Admin(LCB.Connection):
    """An administrative connection to a Couchbase cluster.

    With this object, you can do things which affect the cluster, such as
    modifying buckets, allocating nodes, or retrieving information about
    the cluster.

    This object should **not** be used to perform Key/Value operations. The
    :class:`couchbase.connection.Connection` is used for that.
    """
    def __init__(self, username, password, host='localhost', port=8091,
                 **kwargs):

        """Connect to a cluster

        :param string username: The administrative username for the cluster,
          this is typically ``Administrator``
        :param string password: The administrative password for the cluster,
          this is the password you entered when Couchbase was installed
        :param string host: The hostname or IP of one of the nodes which is
          currently a member of the cluster (or a newly allocated node, if
          you wish to operate on that)
        :param int port: The management port for the node

        :raise:
            :exc:`couchbase.exceptions.AuthError` if incorrect credentials
            were supplied

            :exc:`couchbase.exceptions.ConnectError` if there was a problem
            establishing a connection to the provided host

        :return: an instance of :class:`Admin`
        """
        kwargs = {
            'username': username,
            'password': password,
            'host': "{0}:{1}".format(host, port),
            '_conntype': LCB.LCB_TYPE_CLUSTER,
            '_errors': deque()
        }

        super(Admin, self).__init__(**kwargs)
        self._connect()

    def http_request(self,
                     path,
                     method='GET',
                     content=None,
                     content_type="application/json",
                     response_format=FMT_JSON):
        """
        Perform an administrative HTTP request. This request is sent out to
        the administrative API interface (i.e. the "Management/REST API")
        of the cluster.

        See <LINK?> for a list of available comments.

        Note that this is a fairly low level function. This class will with
        time contain more and more wrapper methods for common tasks such
        as bucket creation or node allocation, and this method should
        mostly be used if a wrapper is not available.

        :param string path: The path portion (not including the host) of the
          rest call to perform. This should also include any encoded arguments.

        :param string method: This is the HTTP method to perform. Currently
          supported values are `GET`, `POST`, `PUT`, and `DELETE`

        :param bytes content: Content to be passed along in the request body.
          This is only applicable on `PUT` and `POST` methods.

        :param string content_type: Value for the HTTP ``Content-Type`` header.
          Currently this is ``application-json``, and should probably not be
          set to something else.

        :param int response_format:
          Hint about how to format the response. This goes into the
          :attr:`~couchbase.result.HttpResult.value` field of the
          :class:`~couchbase.result.HttpResult` object. The default is
          :const:`~couchbase.connection.FMT_JSON`.

          Note that if the conversion fails, the content will be returned as
          ``bytes``

        :raise:

          :exc:`couchbase.exceptions.ArgumentError` if the method supplied was
            incorrect

          :exc:`couchbase.exceptions.ConnectError` if there was a problem
            establishing a connection.

          :exc:`couchbase.exceptions.HTTPError` if the server responded with a
            negative reply

        :return: a :class:`~couchbase.result.HttpResult` object.
        """
        imeth = None
        if not method in METHMAP:
            raise E.ArgumentError.pyexc("Unknown HTTP Method", method)

        imeth = METHMAP[method]
        return self._http_request(type=LCB.LCB_HTTP_TYPE_MANAGEMENT,
                                  path=path,
                                  method=imeth,
                                  content_type=content_type,
                                  post_data=content,
                                  response_format=response_format)

########NEW FILE########
__FILENAME__ = connection
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
This file contains the stub Async implementation.
This module is prefixed by an underscore and thus is not public API,
meaning the interface may change. Its presence is here primarily to
expose potential integrators to the mechanisms by which the library
may be extended to support other async frameworks
"""

import couchbase._bootstrap
from couchbase._libcouchbase import (
    AsyncResult,
    PYCBC_CONN_F_ASYNC,
    PYCBC_CONN_F_ASYNC_DTOR)

from couchbase.result import AsyncResult
from couchbase.async.view import AsyncViewBase
from couchbase.connection import Connection
from couchbase.exceptions import ArgumentError

class Async(Connection):
    def __init__(self, iops=None, **kwargs):
        """
        Create a new Async connection. An async connection is an object
        which functions like a normal synchronous connection, except that it
        returns future objects (i.e. :class:`~couchbase.result.AsyncResult`
        objects) instead of :class:`~couchbase.result.Result`.
        These objects are actually :class:`~couchbase.result.MultiResult`
        objects which are empty upon retun. As operations complete, this
        object becomes populated with the relevant data.

        Note that the AsyncResult object must currently have valid
        :attr:`~couchbase.result.AsyncResult.callback` and
        :attr:`~couchbase.result.AsyncResult.errback` fields initialized
        *after* they are returned from
        the API methods. If this is not the case then an exception will be
        raised when the callbacks are about to arrive. This behavior is the
        primary reason why this interface isn't public, too :)

        :param iops: An :class:`~couchbase.iops.base.IOPS`-interface
          conforming object. This object must not be used between two
          instances, and is owned by the connection object.

        :param kwargs: Additional arguments to pass to
          the :class:`~couchbase.connection.Connection` constructor
        """
        if not iops:
            raise ValueError("Must have IOPS")

        kwargs.setdefault('_flags', 0)

        # Must have an IOPS implementation
        kwargs['_iops'] = iops

        # Flags should be async
        kwargs['_flags'] |= PYCBC_CONN_F_ASYNC|PYCBC_CONN_F_ASYNC_DTOR

        # Don't lock/unlock GIL as the enter/leave points are not coordinated
        # kwargs['unlock_gil'] = False
        # This is always set to false in connection.c

        super(Async, self).__init__(**kwargs)

    def query(self, *args, **kwargs):
        """
        Reimplemented from base class. This method does not add additional
        functionality of the base class`
        :meth:`~couchbase.connection.Connection.query` method (all the
        functionality is encapsulated in the view class anyway). However it
        does require one additional keyword argument

        :param class itercls: A class used for instantiating the view
          object. This should be a subclass of
          :class:`~couchbase.async.view.AsyncViewBase`.
        """
        if not issubclass(kwargs.get('itercls', None), AsyncViewBase):
            raise ArgumentError.pyexc("itercls must be defined "
                                      "and must be derived from AsyncViewBase")

        return super(Async, self).query(*args, **kwargs)

    def endure(self, key, *args, **kwargs):
        res = super(Async, self).endure_multi([key], *args, **kwargs)
        res._set_single()
        return res

########NEW FILE########
__FILENAME__ = events
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This file contains various utility classes for scheduling
and destroying events
"""

class EventQueue(object):
    def __init__(self):
        self.called = False
        self.waiters = []

    def fire_async(self, event):
        """
        Fire this event 'immediately', but in the next event iteration
        """

    def maybe_raise(self, *args, **kwargs):
        """
        Given the arguments from '__call__', see if we should raise an error
        """

    def call_single_success(self, event, *args, **kwargs):
        """
        Call a single event with success
        """

    def call_single_failure(self, event, *args, **kwargs):
        """
        Call a single event with a failure. This will be from within
        the 'except' block and thus will have sys.exc_info() available
        """

    def schedule(self, event):
        if self.called:
            self.fire_async(event)
            return

        self.waiters.append(event)

    def __hash__(self):
        return hash(self.name)

    def __len__(self):
        return len(self.waiters)

    def __iter__(self):
        return iter(self.waiters)

    def invoke_waiters(self, *args, **kwargs):
        self.called = True
        try:
            self.maybe_raise(*args, **kwargs)
            for event in self.waiters:
                try:
                    self.call_single_success(event, *args, **kwargs)
                except:
                    pass
        except:
            for event in self.waiters:
                try:
                    self.call_single_failure(event, event, *args, **kwargs)
                except Exception as e:
                    pass

        self.waiters = None

    def __call__(self, *args, **kwargs):
        self.invoke_waiters(*args, **kwargs)

########NEW FILE########
__FILENAME__ = view
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
This file contains the view implementation for Async
"""
from couchbase.views.iterator import View
from couchbase.exceptions import CouchbaseError, ArgumentError

class AsyncViewBase(View):
    def __init__(self, *args, **kwargs):
        """
        Initialize a new AsyncViewBase object. This is intended to be
        subclassed in order to implement the require methods to be
        invoked on error, data, and row events.

        Usage of this class is not as a standalone, but rather as
        an ``itercls`` parameter to the
        :meth:`~couchbase.connection.Connection.query` method of the
        connection object.
        """
        kwargs['streaming'] = True
        super(AsyncViewBase, self).__init__(*args, **kwargs)
        if self.include_docs:
            self.raise_include_docs()

    def raise_include_docs(self):
        """
        Raise an error on include docs
        """
        raise ArgumentError.pyexc(
            "Include docs not supported with async views. If you "
            "must gather docs, you should do so manually")



    def __iter__(self):
        """
        Unlike our base class, iterating does not make sense here
        """
        raise NotImplementedError("Iteration not supported on async view")

    def on_error(self, ex):
        """
        Called when there is a failure with the response data

        :param Exception ex: The exception caught.

        This must be implemented in a subclass
        """
        raise NotImplementedError("Must be implemented in subclass")

    def on_rows(self, rowiter):
        """
        Called when there are more processed views.

        :param iterable rowiter: An iterable which will yield results
          as defined by the :class:`RowProcessor` implementation

        This method must be implemented in a subclass
        """
        raise NotImplementedError("Must be implemented in subclass")

    def on_done(self):
        """
        Called when this request has completed. Once this method is called,
        no other methods will be invoked on this object.

        This method must be implemented in a subclass
        """
        raise NotImplementedError("Must be implemented in subclass")

    def _callback(self, htres, rows):
        """
        This is invoked as the row callback.
        If 'rows' is true, then we are a row callback, otherwise
        the request has ended and it's time to collect the other data
        """
        try:
            self._process_payload(rows)
            if self._rp_iter:
                self.on_rows(self._rp_iter)

            if self.raw.done:
                self.raw._maybe_raise()
                self.on_done()

        except CouchbaseError as e:
            self.on_error(e)

        finally:
            self._rp_iter = None

    def start(self):
        """
        Initiate the callbacks for this query. These callbacks will be invoked
        until the request has completed and the :meth:`on_done`
        method is called.
        """
        self._setup_streaming_request()
        self._do_iter = True
        self.raw._callback = self._callback
        return self

########NEW FILE########
__FILENAME__ = connection
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import json
import time
from collections import deque


import couchbase._bootstrap
import couchbase._libcouchbase as _LCB
from couchbase._libcouchbase import Connection as _Base
from couchbase.iops.select import SelectIOPS

from couchbase.exceptions import *
from couchbase.user_constants import *
from couchbase.result import *

import couchbase.exceptions as exceptions
from couchbase.views.params import make_dvpath, make_options_string
from couchbase.views.iterator import View
from couchbase._pyport import basestring

class Pipeline(object):
    def __init__(self, parent):
        """

        .. versionadded:: 1.2.0

        Creates a new pipeline context. See :meth:`~Connection.pipeline`
        for more details
        """
        self._parent = parent
        self._results = None

    def __enter__(self):
        self._parent._pipeline_begin()

    def __exit__(self, *args):
        self._results = self._parent._pipeline_end()
        return False

    @property
    def results(self):
        """
        Contains a list of results for each pipelined operation executed within
        the context. The list remains until this context is reused.

        The elements in the list are either :class:`~couchbase.result.Result`
        objects (for single operations) or
        :class:`~couchbase.result.MultiResult` objects (for multi operations)
        """
        return self._results


class DurabilityContext(object):

    def __init__(self, parent, persist_to=-1, replicate_to=-1, timeout=0.0):
        self._parent = parent
        self._new = {
            '_dur_persist_to': persist_to,
            '_dur_replicate_to': replicate_to,
            '_dur_timeout': int(timeout * 1000000)
        }

        self._old = {}

    def __enter__(self):
        for k, v in self._new.items():
            self._old[k] = getattr(self._parent, k)
            setattr(self._parent, k, v)

    def __exit__(self, *args):
        for k, v in self._old.items():
            setattr(self._parent, k, v)

        return False

class Connection(_Base):

    def _gen_host_string(self, host, port):
        if not isinstance(host, (tuple, list)):
            return "{0}:{1}".format(host, port)

        hosts_tmp = []
        for curhost in host:
            cur_hname = None
            cur_hport = None
            if isinstance(curhost, (list, tuple)):
                cur_hname, cur_hport = curhost
            else:
                cur_hname = curhost
                cur_hport = port

            hosts_tmp.append("{0}:{1}".format(cur_hname, cur_hport))

        return ";".join(hosts_tmp)

    def __init__(self, **kwargs):
        """Connection to a bucket.

        Normally it's initialized through :meth:`couchbase.Couchbase.connect`

        See :meth:`couchbase.Couchbase.connect` for constructor options
        """
        bucket = kwargs.get('bucket', None)
        host = kwargs.get('host', 'localhost')
        username = kwargs.get('username', None)
        password = kwargs.get('password', None)

        # We don't pass this to the actual constructor
        port = kwargs.pop('port', 8091)
        _no_connect_exceptions = kwargs.pop('_no_connect_exceptions', False)
        _gevent_support = kwargs.pop('experimental_gevent_support', False)
        _cntlopts = kwargs.pop('_cntl', {})

        if not bucket:
            raise exceptions.ArgumentError("A bucket name must be given")

        kwargs['host'] = self._gen_host_string(host, port)
        kwargs['bucket'] = bucket

        if password and not username:
            kwargs['username'] = bucket

        # Internal parameters
        kwargs['_errors'] = deque(maxlen=1000)

        tc = kwargs.get('transcoder')
        if isinstance(tc, type):
            kwargs['transcoder'] = tc()

        if _gevent_support:
            kwargs['_iops'] = SelectIOPS()

        super(Connection, self).__init__(**kwargs)
        for ctl, val in _cntlopts.items():
            self._cntl(ctl, val)

        try:
            self._do_ctor_connect()
        except exceptions.CouchbaseError as e:
            if not _no_connect_exceptions:
                raise

    def _do_ctor_connect(self):
        """
        This should be overidden by subclasses which want to use a different
        sort of connection behavior
        """
        self._connect()

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def __delitem__(self, key):
        return self.delete(key)

    def errors(self, clear_existing=True):
        """
        Get miscellaneous error information.

        This function returns error information relating to the client
        instance. This will contain error information not related to
        any specific operation and may also provide insight as to what
        caused a specific operation to fail.

        :param boolean clear_existing: If set to true, the errors will be
          cleared once they are returned. The client will keep a history of
          the last 1000 errors which were received.

        :return: a tuple of ((errnum, errdesc), ...) (which may be empty)
        """

        ret = tuple(self._errors)

        if clear_existing:
            self._errors.clear()
        return ret

    def pipeline(self):
        """

        Returns a new :class:`Pipeline` context manager. When the context
        manager is active, operations performed will return ``None``, and
        will be sent on the network when the context leaves (in its
        ``__exit__`` method). To get the results of the pipelined operations,
        inspect the :attr:`Pipeline.results` property.

        Operational errors (i.e. negative replies from the server, or network
        errors) are delivered when the pipeline exits, but argument errors
        are thrown immediately.

        :return: a :class:`Pipeline` object

        :raise: :exc:`couchbase.exceptions.PipelineError` if a pipeline
          is already in progress

        :raise: Other operation-specific errors.

        Scheduling multiple operations, without checking results::

          with cb.pipeline():
            cb.set("key1", "value1")
            cb.incr("counter")
            cb.add_multi({
              "new_key1" : "new_value_1",
              "new_key2" : "new_value_2"
            })

        Retrieve the results for several operations::

          pipeline = cb.pipeline()
          with pipeline:
            cb.set("foo", "bar")
            cb.replace("something", "value")

          for result in pipeline.results:
            print("Pipeline result: CAS {0}".format(result.cas))

        .. note::

          When in pipeline mode, you cannot execute view queries.
          Additionally, pipeline mode is not supported on async handles

        .. warning::

          Pipeline mode should not be used if you are using the same
          object concurrently from multiple threads. This only refers
          to the internal lock within the object itself. It is safe
          to use if you employ your own locking mechanism (for example
          a connection pool)

        .. versionadded:: 1.2.0

        """
        return Pipeline(self)

    # We have these wrappers so that IDEs can do param tooltips and the like.
    # we might move this directly into C some day

    def set(self, key, value, cas=0, ttl=0, format=None,
            persist_to=0, replicate_to=0):
        """Unconditionally store the object in Couchbase.

        :param key: The key to set the value with. By default, the key must be
          either a :class:`bytes` or :class:`str` object encodable as UTF-8.
          If a custom `transcoder` class is used
          (see :meth:`couchbase.Couchbase.connect`), then
          the key object is passed directly to the transcoder, which may
          serialize it how it wishes.
        :type key: string or bytes

        :param value: The value to set for the key. The type for `value`
          follows the same rules as for `key`

        :param int cas: The _CAS_ value to use. If supplied, the value will
          only be stored if it already exists with the supplied CAS

        :param int ttl: If specified, the key will expire after this many
          seconds

        :param int format: If specified, indicates the `format` to use when
          encoding the value. If none is specified, it will use the
          `default_format`
          For more info see
          :attr:`~couchbase.connection.Connection.default_format`

        :param int persist_to: Perform durability checking on this many

          .. versionadded:: 1.1.0

          nodes for persistence to disk.
          See :meth:`endure` for more information

        :param int replicate_to: Perform durability checking on this many

          .. versionadded:: 1.1.0

          replicas for presence in memory. See :meth:`endure` for more
          information.

        :raise: :exc:`couchbase.exceptions.ArgumentError` if an
          argument is supplied that is not applicable in this context.
          For example setting the CAS as a string.
        :raise: :exc:`couchbase.exceptions.ConnectError` if the
          connection closed
        :raise: :exc:`couchbase.exceptions.KeyExistsError` if the key
          already exists on the server with a different CAS value.
        :raise: :exc:`couchbase.exceptions.ValueFormatError` if the
          value cannot be serialized with chosen encoder, e.g. if you
          try to store a dictionaty in plain mode.

        :return: :class:`~couchbase.result.Result`

        Simple set::

            cb.set('key', 'value')

        Force JSON document format for value::

            cb.set('foo', {'bar': 'baz'}, format=couchbase.FMT_JSON)

        Perform optimistic locking by specifying last known CAS version::

            cb.set('foo', 'bar', cas=8835713818674332672)

        Several sets at the same time (mutli-set)::

            cb.set_multi({'foo': 'bar', 'baz': 'value'})

        .. seealso:: :meth:`set_multi`

        """
        return _Base.set(self, key, value, cas, ttl, format,
                         persist_to, replicate_to)

    def add(self, key, value, ttl=0, format=None, persist_to=0, replicate_to=0):
        """
        Store an object in Couchbase unless it already exists.

        Follows the same conventions as
        :meth:`~couchbase.connection.Connection.set` but the value is
        stored only if it does not exist already. Conversely, the value
        is not stored if the key already exists.

        Notably missing from this method is the `cas` parameter, this is
        because `add` will only succeed if a key does not already exist
        on the server (and thus can have no CAS)

        :raise: :exc:`couchbase.exceptions.KeyExistsError` if the key
          already exists

        .. seealso:: :meth:`set`, :meth:`add_multi`

        """
        return _Base.add(self, key, value, ttl=ttl, format=format,
                         persist_to=persist_to, replicate_to=replicate_to)

    def replace(self, key, value, cas=0, ttl=0, format=None,
                persist_to=0, replicate_to=0):
        """
        Store an object in Couchbase only if it already exists.

        Follows the same conventions as
        :meth:`~couchbase.connection.Connection.set`, but the value is
        stored only if a previous value already exists.

        :raise: :exc:`couchbase.exceptions.NotFoundError` if the key
          does not exist

        .. seealso:: :meth:`set`, :meth:`replace_multi`

        """
        return _Base.replace(self, key, value, ttl=ttl, cas=cas, format=format,
                             persist_to=persist_to, replicate_to=replicate_to)

    def append(self, key, value, cas=0, ttl=0, format=None,
               persist_to=0, replicate_to=0):
        """
        Append a string to an existing value in Couchbase.

        This follows the same conventions as
        :meth:`~couchbase.connection.Connection.set`.

        The `format` argument must be one of :const:`~couchbase.FMT_UTF8` or
        :const:`~couchbase.FMT_BYTES`. If not specified, it will be
        :const:`~couchbase.FMT_UTF8`
        (overriding the :attr:`default_format` attribute).
        This is because JSON or Pickle formats will be nonsensical when
        random data is appended to them. If you wish to modify a JSON or
        Pickle encoded object, you will need to retrieve it (via :meth:`get`),
        modify it, and then store it again (using :meth:`set`).

        Additionally, you must ensure the value (and flags) for the current
        value is compatible with the data to be appended. For an example,
        you may append a :const:`~couchbase.FMT_BYTES` value to an existing
        :const:`~couchbase.FMT_JSON` value, but an error will be thrown when
        retrieving the value using
        :meth:`get` (you may still use the :attr:`data_passthrough` to
        overcome this).

        :raise: :exc:`couchbase.exceptions.NotStoredError` if the key does
          not exist

        .. seealso::
            :meth:`set`, :meth:`append_multi`

        """
        return _Base.append(self, key, value, ttl=ttl, cas=cas, format=format,
                            persist_to=persist_to, replicate_to=replicate_to)

    def prepend(self, key, value, cas=0, ttl=0, format=None,
                persist_to=0, replicate_to=0):
        """
        Prepend a string to an existing value in Couchbase.

        .. seealso::
            :meth:`append`, :meth:`prepend_multi`

        """
        return _Base.prepend(self, key, value, ttl=ttl, cas=cas, format=format,
                             persist_to=persist_to, replicate_to=replicate_to)

    def get(self, key, ttl=0, quiet=None, replica=False, no_format=False):
        """Obtain an object stored in Couchbase by given key.

        :param string key: The key to fetch. The type of key is the same
          as mentioned in :meth:`set`

        :param int ttl:
          If specified, indicates that the key's expiration time should be
          *modified* when retrieving the value.

        :param boolean quiet: causes `get` to return None instead of
          raising an exception when the key is not found. It defaults
          to the value set by
          :attr:`~couchbase.connection.Connection.quiet` on the instance.
          In `quiet` mode, the error may still be obtained by inspecting
          the :attr:`~couchbase.result.Result.rc` attribute of the
          :class:`couchbase.result.Result` object, or
          checking :attr:`couchbase.result.Result.success`.

          Note that the default value is `None`, which means to use
          the :attr:`quiet`. If it is a boolean (i.e. `True` or `False) it will
          override the :class:`Connection`-level :attr:`quiet` attribute.

        :param bool replica: Whether to fetch this key from a replica
          rather than querying the master server. This is primarily useful
          when operations with the master fail (possibly due to a configuration
          change). It should normally be used in an exception handler like so

          Using the ``replica`` option::

            try:
                res = c.get("key", quiet=True) # suppress not-found errors
            catch CouchbaseError:
                res = c.get("key", replica=True, quiet=True)


        :param bool no_format:

          .. versionadded:: 1.1.0

          If set to ``True``, then the value will always be
          delivered in the :class:`~couchbase.result.Result` object as being of
          :data:`~couchbase.FMT_BYTES`. This is a item-local equivalent of using
          the :attr:`data_passthrough` option


        :raise: :exc:`couchbase.exceptions.NotFoundError` if the key
          is missing in the bucket
        :raise: :exc:`couchbase.exceptions.ConnectError` if the
          connection closed
        :raise: :exc:`couchbase.exceptions.ValueFormatError` if the
          value cannot be deserialized with chosen decoder, e.g. if you
          try to retreive an object stored with an unrecognized format
        :return: A :class:`~couchbase.result.Result` object

        Simple get::

            value = cb.get('key').value

        Get multiple values::

            cb.get_multi(['foo', 'bar'])
            # { 'foo' : <Result(...)>, 'bar' : <Result(...)> }

        Inspect the flags::

            rv = cb.get("key")
            value, flags, cas = rv.value, rv.flags, rv.cas

        Update the expiration time::

            rv = cb.get("key", ttl=10)
            # Expires in ten seconds


        .. seealso::
            :meth:`get_multi`

        """

        return _Base.get(self, key, ttl, quiet, replica, no_format)

    def touch(self, key, ttl=0):
        """Update a key's expiration time

        :param string key: The key whose expiration time should be modified
        :param int ttl: The new expiration time. If the expiration time is
          ``0`` then the key never expires (and any existing expiration is
          removed)

        :return: :class:`couchbase.result.OperationResult`

        Update the expiration time of a key ::

            cb.set("key", ttl=100)
            # expires in 100 seconds
            cb.touch("key", ttl=0)
            # key should never expire now

        :raise: The same things that :meth:`get` does

        .. seealso::
            :meth:`get` - which can be used to get *and* update the expiration,
            :meth:`touch_multi`
        """
        return _Base.touch(self, key, ttl=ttl)

    def lock(self, key, ttl=0):
        """Lock and retrieve a key-value entry in Couchbase.

        :param key: A string which is the key to lock.
        :param int: a TTL for which the lock should be valid. If set to
          `0` it will use the default lock timeout on the server.
          While the lock is active, attempts to access the key (via
          other :meth:`lock`, :meth:`set` or other mutation calls) will
          fail with an :exc:`couchbase.exceptions.TemporaryFailError`


        This function otherwise functions similarly to :meth:`get`;
        specifically, it will return the value upon success.
        Note the :attr:`~couchbase.result.Result.cas` value from the
        :class:`couchbase.result.Result`
        object. This will be needed to :meth:`unlock` the key.

        Note the lock will also be implicitly released if modified by one
        of the :meth:`set` family of functions when the valid CAS is
        supplied

        :raise: :exc:`couchbase.exceptions.TemporaryFailError` if the key
          was already locked.

        :raise: See :meth:`get` for possible exceptions


        Lock a key ::

            rv = cb.lock("locked_key", ttl=100)
            # This key is now locked for the next 100 seconds.
            # attempts to access this key will fail until the lock
            # is released.

            # do important stuff...

            cb.unlock("locked_key", rv.cas)

        Lock a key, implicitly unlocking with :meth:`set` with CAS ::

            rv = self.cb.lock("locked_key", ttl=100)
            new_value = rv.value.upper()
            cb.set("locked_key", new_value, rv.cas)


        Poll and Lock ::

            rv = None
            begin_time = time.time()
            while time.time() - begin_time < 15:
                try:
                    rv = cb.lock("key")
                except TemporaryFailError:
                    print("Key is currently locked.. waiting")
                    time.sleep(0)

            if not rv:
                raise Exception("Waited too long..")

            # Do stuff..

            cb.unlock("key", rv.cas)

        .. seealso::
            :meth:`get`, :meth:`lock_multi`, :meth:`unlock`

        """
        return _Base.lock(self, key, ttl=ttl)

    def unlock(self, key, cas):
        """Unlock a Locked Key in Couchbase.

        :param key: The key to unlock
        :param cas: The cas returned from
          :meth:`lock`'s :class:`couchbase.result.Result` object.


        Unlock a previously-locked key in Couchbase. A key is
        locked by a call to :meth:`lock`.


        See :meth:`lock` for an example.

        :raise: :exc:`couchbase.exceptions.KeyExistsError` if the CAS
          supplied does not match the CAS on the server (possibly because
          it was unlocked by previous call).

        .. seealso::

        :meth:`lock`
        :meth:`unlock_multi`

        """
        return _Base.unlock(self, key, cas=cas)

    def delete(self, key, cas=0, quiet=None, persist_to=0, replicate_to=0):
        """Remove the key-value entry for a given key in Couchbase.

        :param key: A string which is the key to delete. The format and type
          of the key follows the same conventions as in :meth:`set`

        :type key: string, dict, or tuple/list
        :param int cas: The CAS to use for the removal operation.
          If specified, the key will only be deleted from the server if
          it has the same CAS as specified. This is useful to delete a
          key only if its value has not been changed from the version
          currently visible to the client.
          If the CAS on the server does not match the one specified,
          an exception is thrown.
        :param boolean quiet:
          Follows the same semantics as `quiet` in :meth:`get`

        :param int persist_to: If set, wait for the item to be deleted from
          the storage of at least these many nodes

          .. versionadded:: 1.2.0

        :param int replicate_to: If set, wait for the item to be deleted from
          the cache of at least these many nodes (excluding the master)

          .. versionadded:: 1.2.0

        :raise: :exc:`couchbase.exceptions.NotFoundError` if the key
          does not exist on the bucket
        :raise: :exc:`couchbase.exceptions.KeyExistsError` if a CAS
          was specified, but the CAS on the server had changed
        :raise: :exc:`couchbase.exceptions.ConnectError` if the
          connection was closed

        :return: A :class:`~couchbase.result.Result` object.


        Simple delete::

            ok = cb.delete("key").success

        Don't complain if key does not exist::

            ok = cb.delete("key", quiet=True)

        Only delete if CAS matches our version::

            rv = cb.get("key")
            cb.delete("key", cas=rv.cas)

        Remove multiple keys::

            oks = cb.delete_multi(["key1", "key2", "key3"])

        Remove multiple keys with CAS::

            oks = cb.delete({
                "key1" : cas1,
                "key2" : cas2,
                "key3" : cas3
            })


        .. seealso:: :meth:`delete_multi`, :meth:`endure` for more information
          on the ``persist_to`` and ``replicate_to`` options.

        """
        return _Base.delete(self, key, cas, quiet, persist_to=persist_to,
                            replicate_to=replicate_to)

    def incr(self, key, amount=1, initial=None, ttl=0):
        """
        Increment the numeric value of a key.

        :param string key: A key whose counter value is to be incremented

        :param int amount: an amount by which the key should be
          incremented

        :param initial: The initial value for the key, if it does not
          exist. If the key does not exist, this value is used, and
          `amount` is ignored. If this parameter is `None` then no
          initial value is used
        :type initial: int or `None`

        :param int ttl: The lifetime for the key, after which it will
          expire

        :raise: :exc:`couchbase.exceptions.NotFoundError` if the key
          does not exist on the bucket (and `initial` was `None`)

        :raise: :exc:`couchbase.exceptions.DeltaBadvalError` if the key
          exists, but the existing value is not numeric

        :return:
          A :class:`couchbase.result.Result` object. The current value
          of the counter may be obtained by inspecting the return value's
          `value` attribute.

        Simple increment::

            rv = cb.incr("key")
            rv.value
            # 42

        Increment by 10::

            ok = cb.incr("key", amount=10)

        Increment by 20, set initial value to 5 if it does not exist::

            ok = cb.incr("key", amount=20, initial=5)

        Increment three keys::

            kv = cb.incr_multi(["foo", "bar", "baz"])
            for key, result in kv.items():
                print "Key %s has value %d now" % (key, result.value)

        .. seealso:: :meth:`decr`, :meth:`incr_multi`

        """
        return _Base.incr(self, key, amount, initial, ttl)

    def decr(self, key, amount=1, initial=None, ttl=0):
        """
        Like :meth:`incr`, but decreases, rather than increaes the
        counter value

        .. seealso:: :meth:`incr`, :meth:`decr_multi`

        """
        return _Base.decr(self, key, amount, initial, ttl)

    def stats(self, keys=None):
        """Request server statistics
        Fetches stats from each node in the cluster. Without a key
        specified the server will respond with a default set of
        statistical information. It returns the a `dict` with stats keys
        and node-value pairs as a value.

        :param stats: One or several stats to query
        :type stats: string or list of string

        :raise: :exc:`couchbase.exceptions.ConnectError` if the
          connection closed

        :return: `dict` where keys are stat keys and values are
          host-value pairs

        Find out how many items are in the bucket::

            total = 0
            for key, value in cb.stats()['total_items'].items():
                total += value

        Get memory stats (works on couchbase buckets)::

            cb.stats('memory')
            # {'mem_used': {...}, ...}
        """
        if keys and not isinstance(keys, (tuple, list)):
            keys = (keys,)
        return self._stats(keys)

    def observe(self, key, master_only=False):
        """
        Return storage information for a key.
        The ``observe`` function maps to the low-level ``OBSERVE``
        command.

        It returns a :class:`couchbase.result.ValueResult`
        object with the ``value`` field
        set to a list of :class:`~couchbase.result.ObserveInfo`
        objects. Each element in the list
        responds to the storage status for the key on the given node. The
        length of the list (and thus the number of
        :class:`~couchbase.result.ObserveInfo` objects)
        are equal to the number of online replicas plus the master for the
        given key.

        :param string key: The key to inspect
        :param bool master_only: Whether to only retrieve information from
          the master node. Note this requires libcouchbase 2.3.0 or greater

        .. seealso:: :ref:`observe_info`

        """
        return _Base.observe(self, key, master_only)

    def endure(self, key, persist_to=-1, replicate_to=-1,
               cas=0,
               check_removed=False,
               timeout=5.0,
               interval=0.010):
        """
        Wait until a key has been distributed to one or more nodes

        .. versionadded:: 1.1.0

        By default, when items are stored to Couchbase, the operation is
        considered successful if the vBucket master (i.e. the "primary" node)
        for the key has successfuly stored the item in its memory.

        In most situations, this is sufficient to assume that the item has
        successfuly been stored. However the possibility remains that the
        "master" server will go offline as soon as it sends back the successful
        response and the data is lost.

        The ``endure`` function allows you to provide stricter criteria for
        success. The criteria may be expressed in terms of number of nodes
        for which the item must exist in that node's RAM and/or on that node's
        disk. Ensuring that an item exists in more than one place is a safer
        way to guarantee against possible data loss.

        We call these requirements `Durability Constraints`, and thus the
        method is called `endure`.

        :param string key: The key to endure.
        :param int persist_to: The minimum number of nodes which must contain
            this item on their disk before this function returns. Ensure that
            you do not specify too many nodes; otherwise this function will
            fail. Use the :attr:`server_nodes` to determine how many nodes
            exist in the cluster.

            The maximum number of nodes an item can reside on is currently
            fixed to 4 (i.e. the "master" node, and up to three "replica"
            nodes). This limitation is current as of Couchbase Server version
            2.1.0.

            If this parameter is set to a negative value, the maximum number
            of possible nodes the key can reside on will be used.

        :param int replicate_to: The minimum number of replicas which must
            contain this item in their memory for this method to succeed.
            As with ``persist_to``, you may specify a negative value in which
            case the requirement will be set to the maximum number possible.

        :param float timeout: A timeout value in seconds before this function
            fails with an exception. Typically it should take no longer than
            several milliseconds on a functioning cluster for durability
            requirements to be satisfied (unless something has gone wrong).

        :param float interval: The polling interval in secods
            to use for checking the
            key status on the respective nodes. Internally, ``endure`` is
            implemented by polling each server individually to see if the
            key exists on that server's disk and memory. Once the status
            request is sent to all servers, the client will check if their
            replies are satisfactory; if they are then this function succeeds,
            otherwise the client will wait a short amount of time and try
            again. This parameter sets this "wait time".

        :param bool check_removed: This flag inverts the check. Instead of
            checking that a given key *exists* on the nodes, this changes
            the behavior to check that the key is *removed* from the nodes.

        :param long cas: The CAS value to check against. It is possible for
            an item to exist on a node but have a CAS value from a prior
            operation. Passing the CAS ensures that only replies from servers
            with a CAS matching this parameter are accepted

        :return: A :class:`~couchbase.result.OperationResult`

        :raise: :exc:`~couchbase.exceptions.CouchbaseError`.
            see :meth:`set` and :meth:`get` for possible errors

        .. seealso:: :meth:`set`, :meth:`endure_multi`
        """
        # We really just wrap 'endure_multi'
        kv = { key : cas }
        rvs = self.endure_multi(keys=kv,
                                persist_to=persist_to,
                                replicate_to=replicate_to,
                                check_removed=check_removed,
                                timeout=timeout,
                                interval=interval)
        return rvs[key]

    def durability(self, persist_to=-1, replicate_to=-1, timeout=0.0):
        """
        Returns a context manager which will apply the given
        persistence/replication settings to all mutation operations when
        active

        :param int persist_to:
        :param int replicate_to:

        See :meth:`endure` for the meaning of these two values

        Thus, something like::

          with cb.durability(persist_to=3):
            cb.set("foo", "foo_value")
            cb.set("bar", "bar_value")
            cb.set("baz", "baz_value")

        is equivalent to::

            cb.set("foo", "foo_value", persist_to=3)
            cb.set("bar", "bar_value", persist_to=3)
            cb.set("baz", "baz_value", persist_to=3)


        .. versionadded:: 1.2.0

        .. seealso:: :meth:`endure`
        """
        return DurabilityContext(self, persist_to, replicate_to, timeout)

    def set_multi(self, keys, ttl=0, format=None, persist_to=0, replicate_to=0):
        """Set multiple keys

        This follows the same semantics as
        :meth:`~couchbase.connection.Connection.set`

        :param dict keys: A dictionary of keys to set. The keys are the keys
          as they should be on the server, and the values are the values for
          the keys to be stored.


          From version 1.1.0, `keys` may also be a
          :class:`~couchbase.items.ItemCollection`. If using a dictionary
          variant for item collections, an additional `ignore_cas` parameter
          may be supplied with a boolean value. If not specified, the operation
          will fail if the CAS value on the server does not match the one
          specified in the `Item`'s `cas` field.

        :param int ttl: If specified, sets the expiration value for all
          keys

        :param int format:
          If specified, this is the conversion format which will be used for
          _all_ the keys.

        :param int persist_to: Durability constraint for persistence.
          Note that it is more efficient to use :meth:`endure_multi`
          on the returned :class:`~couchbase.result.MultiResult` than
          using these parameters for a high volume of keys. Using these
          parameters however does save on latency as the constraint checking
          for each item is performed as soon as it is successfully stored.

        :param int replicate_to: Durability constraints for replication.
          See notes on the `persist_to` parameter for usage.

        :return: A :class:`~couchbase.result.MultiResult` object, which
          is a `dict` subclass.

        The multi methods are more than just a convenience, they also save on
        network performance by batch-scheduling operations, reducing latencies.
        This is especially noticeable on smaller value sizes.

        .. seealso:: :meth:`set`

        """
        return _Base.set_multi(self, keys, ttl=ttl, format=format,
                               persist_to=persist_to, replicate_to=replicate_to)

    def add_multi(self, keys, ttl=0, format=None, persist_to=0, replicate_to=0):
        """Add multiple keys.
        Multi variant of :meth:`~couchbase.connection.Connection.add`

        .. seealso:: :meth:`add`, :meth:`set_multi`, :meth:`set`

        """
        return _Base.add_multi(self, keys, ttl=ttl, format=format,
                               persist_to=persist_to, replicate_to=replicate_to)

    def replace_multi(self, keys, ttl=0, format=None,
                      persist_to=0, replicate_to=0):
        """Replace multiple keys.
        Multi variant of :meth:`replace`

        .. seealso:: :meth:`replace`, :meth:`set_multi`, :meth:`set`

        """
        return _Base.replace_multi(self, keys, ttl=ttl, format=format,
                                   persist_to=persist_to,
                                   replicate_to=replicate_to)

    def append_multi(self, keys, ttl=0, format=None,
                     persist_to=0, replicate_to=0):
        """Append to multiple keys.
        Multi variant of :meth:`append`.


        .. warning::

            If using the `Item` interface, use the :meth:`append_items`
            and :meth:`prepend_items` instead, as those will automatically
            update the :attr:`couchbase.items.Item.value` property upon
            successful completion.

        .. seealso:: :meth:`append`, :meth:`set_multi`, :meth:`set`

        """
        return _Base.append_multi(self, keys, ttl=ttl, format=format,
                                  persist_to=persist_to,
                                  replicate_to=replicate_to)

    def prepend_multi(self, keys, ttl=0, format=None,
                      persist_to=0, replicate_to=0):
        """Prepend to multiple keys.
        Multi variant of :meth:`prepend`

        .. seealso:: :meth:`prepend`, :meth:`set_multi`, :meth:`set`

        """
        return _Base.prepend_multi(self, keys, ttl=ttl, format=format,
                                   persist_to=persist_to,
                                   replicate_to=replicate_to)

    def get_multi(self, keys, ttl=0, quiet=None, replica=False, no_format=False):
        """Get multiple keys
        Multi variant of :meth:`get`

        :param keys: keys the keys to fetch
        :type keys: :ref:`iterable<argtypes>`

        :param int ttl: Set the expiration for all keys when retrieving

        :param boolean replica:
          Whether the results should be obtained from a replica instead of the
          master. See :meth:`get` for more information about this parameter.

        :return: A :class:`~couchbase.result.MultiResult` object.
          This object is a subclass of dict and contains the keys (passed as)
          `keys` as the dictionary keys, and
          :class:`~couchbase.result.Result` objects as values

        """
        return _Base.get_multi(self, keys, ttl=ttl, quiet=quiet, replica=replica, no_format=no_format)

    def touch_multi(self, keys, ttl=0):
        """Touch multiple keys

        Multi variant of :meth:`touch`

        :param keys: the keys to touch
        :type keys: :ref:`iterable<argtypes>`

        ``keys`` can also be a dictionary with values being integers, in
        whic case the value for each key will be used as the TTL instead
        of the global one (i.e. the one passed to this function)

        :param int ttl: The new expiration time

        :return: A :class:`~couchbase.result.MultiResult` object


        Update three keys to expire in 10 seconds ::

            cb.touch_multi(("key1", "key2", "key3"), ttl=10)

        Update three keys with different expiration times ::

            cb.touch_multi({"foo" : 1, "bar" : 5, "baz" : 10})

        .. seealso:: :meth:`touch`
        """
        return _Base.touch_multi(self, keys, ttl=ttl)

    def lock_multi(self, keys, ttl=0):
        """Lock multiple keys

        Multi variant of :meth:`lock`

        :param keys: the keys to lock
        :type keys: :ref:`iterable<argtypes>`
        :param int ttl: The lock timeout for all keys

        :return: a :class:`~couchbase.result.MultiResult` object

        .. seealso:: :meth:`lock`

        """
        return _Base.lock_multi(self, keys, ttl=ttl)

    def unlock_multi(self, keys):
        """Unlock multiple keys

        Multi variant of :meth:`unlock`

        :param dict keys: the keys to unlock

        :return: a :class:`~couchbase.result.MultiResult` object

        The value of the ``keys`` argument should be either the CAS, or a
        previously returned :class:`Result` object from a :meth:`lock` call.
        Effectively, this means you may pass a
        :class:`~couchbase.result.MultiResult` as the ``keys`` argument.

        Thus, you can do something like ::

            keys = (....)
            rvs = cb.lock_multi(keys, ttl=5)
            # do something with rvs
            cb.unlock_multi(rvs)


        .. seealso:: :meth:`unlock`
        """
        return _Base.unlock_multi(self, keys)

    def observe_multi(self, keys, master_only=False):
        """
        Multi-variant of :meth:`observe`
        """
        return _Base.observe_multi(self, keys, master_only)

    def endure_multi(self, keys, persist_to=-1, replicate_to=-1,
                     timeout=5.0,
                     interval=0.010,
                     check_removed=False):
        """
        .. versionadded:: 1.1.0

        Check durability requirements for multiple keys

        :param keys: The keys to check

        The type of keys may be one of the following:

            * Sequence of keys
            * A :class:`~couchbase.result.MultiResult` object
            * A ``dict`` with CAS values as the dictionary value
            * A sequence of :class:`~couchbase.result.Result` objects

        :return: A :class:`~couchbase.result.MultiResult` object of
            :class:`~couchbase.result.OperationResult` items.

        .. seealso:: :meth:`endure`
        """
        return _Base.endure_multi(self, keys, persist_to, replicate_to,
                                  timeout=timeout,
                                  interval=interval,
                                  check_removed=check_removed)


    def rget(self, key, replica_index=None, quiet=None):
        """
        Get a key from a replica

        :param string key: The key to fetch

        :param int replica_index: The replica index to fetch.
          If this is ``None`` then this method will return once any replica
          responds. Use :attr:`configured_replica_count` to figure out the
          upper bound for this parameter.

          The value for this parameter must be a number between 0 and the
          value of :attr:`configured_replica_count`-1.

        :param boolean quiet: Whether to suppress errors when the key is not
          found

        This function (if `replica_index` is not supplied) functions like
        the :meth:`get` method that has been passed the `replica` parameter::

            c.get(key, replica=True)

        .. seealso::
            :meth:`get` :meth:`rget_multi`
        """
        if replica_index is not None:
            return _Base._rgetix(self, key, replica=replica_index, quiet=quiet)
        else:
            return _Base._rget(self, key, quiet=quiet)

    def rget_multi(self, keys, replica_index=None, quite=None):
        if replica_index is not None:
            return _Base._rgetix_multi(self, keys, replica=replica_index, quiet=quiet)
        else:
            return _Base._rget_multi(self, keys, quiet=quiet)


    def _view(self, ddoc, view,
              use_devmode=False,
              params=None,
              unrecognized_ok=False,
              passthrough=False):
        """
        .. warning:: This method's API is not stable

        Execute a view (MapReduce) query

        :param string ddoc: Name of the design document
        :param string view: Name of the view function to execute
        :param params: Extra options to pass to the view engine
        :type params: string or dict

        :return: a :class:`~couchbase.result.HttpResult` object.
        """

        if params:
            if not isinstance(params, str):
                params = make_options_string(
                    params,
                    unrecognized_ok=unrecognized_ok,
                    passthrough=passthrough)
        else:
            params = ""

        ddoc = self._mk_devmode(ddoc, use_devmode)
        url = make_dvpath(ddoc, view) + params

        ret = self._http_request(type=_LCB.LCB_HTTP_TYPE_VIEW,
                                 path=url,
                                 method=_LCB.LCB_HTTP_METHOD_GET,
                                 response_format=FMT_JSON)
        return ret

    def _doc_rev(self, res):
        """
        Returns the rev id from the header
        """
        jstr = res.headers['X-Couchbase-Meta']
        jobj = json.loads(jstr)
        return jobj['rev']

    def _design_poll(self, name, mode, oldres, timeout=5):
        """
        Poll for an 'async' action to be complete.
        :param string name: The name of the design document
        :param string mode: One of ``add`` or ``del`` to indicate whether
            we should check for addition or deletion of the document
        :param oldres: The old result from the document's previous state, if
            any
        :param float timeout: How long to poll for. If this is 0 then this
            function returns immediately
        :type oldres: :class:`~couchbase.result.HttpResult`
        """

        if not timeout:
            return True

        if timeout < 0:
            raise ArgumentError.pyexc("Interval must not be negative")

        t_end = time.time() + timeout
        old_rev = None

        if oldres:
            old_rev = self._doc_rev(oldres)

        while time.time() < t_end:
            try:
                cur_resp = self.design_get(name, use_devmode=False)
                if old_rev and self._doc_rev(cur_resp) == old_rev:
                    continue

                # Try to execute a view..
                vname = list(cur_resp.value['views'].keys())[0]
                try:
                    self._view(name, vname, use_devmode=False,
                               params={'limit': 1, 'stale': 'ok'})
                    # We're able to query it? whoopie!
                    return True

                except CouchbaseError:
                    continue

            except CouchbaseError as e:
                if mode == 'del':
                    # Deleted, whopee!
                    return True
                cur_resp = e.objextra

        raise exceptions.TimeoutError.pyexc(
            "Wait time for design action completion exceeded")

    def _mk_devmode(self, n, use_devmode):
        if n.startswith("dev_") or not use_devmode:
            return n
        return "dev_" + n

    def design_create(self, name, ddoc, use_devmode=True, syncwait=0):
        """
        Store a design document

        :param string name: The name of the design
        :param ddoc: The actual contents of the design document

        :type ddoc: string or dict
            If ``ddoc`` is a string, it is passed, as-is, to the server.
            Otherwise it is serialized as JSON, and its ``_id`` field is set to
            ``_design/{name}``.

        :param bool use_devmode:
            Whether a *development* mode view should be used. Development-mode
            views are less resource demanding with the caveat that by default
            they only operate on a subset of the data. Normally a view will
            initially be created in 'development mode', and then published
            using :meth:`design_publish`

        :param float syncwait:
            How long to poll for the action to complete. Server side design
            operations are scheduled and thus this function may return before
            the operation is actually completed. Specifying the timeout here
            ensures the client polls during this interval to ensure the
            operation has completed.

        :raise: :exc:`couchbase.exceptions.TimeoutError` if ``syncwait`` was
            specified and the operation could not be verified within the
            interval specified.

        :return: An :class:`~couchbase.result.HttpResult` object.

        .. seealso:: :meth:`design_get`, :meth:`design_delete`,
            :meth:`design_publish`

        """
        name = self._mk_devmode(name, use_devmode)

        fqname = "_design/{0}".format(name)
        if isinstance(ddoc, dict):
            ddoc = ddoc.copy()
            ddoc['_id'] = fqname
            ddoc = json.dumps(ddoc)
        else:
            if use_devmode:
                raise ArgumentError.pyexc("devmode can only be used "
                                          "with dict type design docs")

        existing = None
        if syncwait:
            try:
                existing = self.design_get(name, use_devmode=False)
            except CouchbaseError:
                pass

        ret = self._http_request(type=_LCB.LCB_HTTP_TYPE_VIEW,
                                 path=fqname,
                                 method=_LCB.LCB_HTTP_METHOD_PUT,
                                 post_data=ddoc,
                                 content_type="application/json",
                                 fetch_headers=True)

        self._design_poll(name, 'add', existing, syncwait)
        return ret

    def design_get(self, name, use_devmode=True):
        """
        Retrieve a design document

        :param string name: The name of the design document
        :param bool use_devmode: Whether this design document is still in
            "development" mode

        :return: A :class:`~couchbase.result.HttpResult` containing
            a dict representing the format of the design document

        :raise: :exc:`couchbase.exceptions.HTTPError` if the design does not
            exist.

        .. seealso:: :meth:`design_create`

        """
        name = self._mk_devmode(name, use_devmode)

        existing = self._http_request(type=_LCB.LCB_HTTP_TYPE_VIEW,
                                      path="_design/" + name,
                                      method=_LCB.LCB_HTTP_METHOD_GET,
                                      content_type="application/json",
                                      fetch_headers=True)
        return existing

    def design_publish(self, name, syncwait=0):
        """
        Convert a development mode view into a production mode views.
        Production mode views, as opposed to development views, operate on the
        entire cluster data (rather than a restricted subset thereof).

        :param string name: The name of the view to convert.

        Once the view has been converted, ensure that all functions (such as
        :meth:`design_get`) have the ``use_devmode`` parameter disabled,
        otherwise an error will be raised when those functions are used.

        Note that the ``use_devmode`` option is missing. This is intentional
        as the design document must currently be a development view.

        :return: An :class:`~couchbase.result.HttpResult` object.

        :raise: :exc:`couchbase.exceptions.HTTPError` if the design does not
            exist

        .. seealso:: :meth:`design_create`, :meth:`design_delete`,
            :meth:`design_get`
        """
        existing = self.design_get(name, use_devmode=True)
        rv = self.design_create(name, existing.value, use_devmode=False,
                                syncwait=syncwait)
        self.design_delete(name, use_devmode=True,
                           syncwait=syncwait)
        return rv

    def design_delete(self, name, use_devmode=True, syncwait=0):
        """
        Delete a design document

        :param string name: The name of the design document to delete
        :param bool use_devmode: Whether the design to delete is a development
            mode design doc.

        :param float syncwait: Timeout for operation verification. See
            :meth:`design_create` for more information on this parameter.

        :return: An :class:`HttpResult` object.

        :raise: :exc:`couchbase.exceptions.HTTPError` if the design does not
            exist
        :raise: :exc:`couchbase.exceptions.TimeoutError` if ``syncwait`` was
            specified and the operation could not be verified within the
            specified interval.

        .. seealso:: :meth:`design_create`, :meth:`design_get`

        """
        name = self._mk_devmode(name, use_devmode)
        existing = None
        if syncwait:
            try:
                existing = self.design_get(name, use_devmode=False)
            except CouchbaseError:
                pass

        ret = self._http_request(type=_LCB.LCB_HTTP_TYPE_VIEW,
                                 path="_design/" + name,
                                 method=_LCB.LCB_HTTP_METHOD_DELETE,
                                 fetch_headers=True)

        self._design_poll(name, 'del', existing, syncwait)
        return ret

    def query(self, design, view, use_devmode=False, itercls=View, **kwargs):
        """
        Query a pre-defined MapReduce view, passing parameters.

        This method executes a view on the cluster. It accepts various
        parameters for the view and returns an iterable object (specifically,
        a :class:`~couchbase.views.iterator.View`).

        :param string design: The design document
        :param string view: The view function contained within the design
            document
        :param boolean use_devmode: Whether the view name should be transformed
            into a development-mode view. See documentation on
            :meth:`design_create` for more explanation.

        :param kwargs: Extra arguments passedd to the
            :class:`~couchbase.views.iterator.View` object constructor.

        :param itercls: Subclass of 'view' to use.

        .. seealso::

            * :class:`~couchbase.views.iterator.View`

                which contains more extensive documentation and examples

            * :class:`~couchbase.views.params.Query`

                which contains documentation on the available query options

        """
        design = self._mk_devmode(design, use_devmode)
        return itercls(self, design, view, **kwargs)

    def __repr__(self):
        return ("<{modname}.{cls} bucket={bucket}, "
                "nodes={nodes} at 0x{oid:x}>"
                ).format(modname=__name__,
                         cls=self.__class__.__name__,
                         nodes=self.server_nodes,
                         bucket=self.bucket,
                         oid=id(self))


    # "items" interface
    def append_items(self, items, **kwargs):
        """
        Method to append data to multiple :class:`~couchbase.items.Item` objects.

        This method differs from the normal :meth:`append_multi` in that each
        `Item`'s `value` field is updated with the appended data upon successful
        completion of the operation.

        :param items: The item dictionary. The value for each key should contain
          a ``fragment`` field containing the object to append to the value on
          the server.

        :type items: :class:`~couchbase.items.ItemOptionDict`.

        The rest of the options are passed verbatim to :meth:`append_multi`

        .. seealso:: :meth:`append_multi`, :meth:`append`
        """
        rv = self.append_multi(items, **kwargs)
        # Assume this is an 'ItemOptionDict'
        for k, v in items.dict.items():
            if k.success:
                k.value += v["fragment"]

        return rv

    def prepend_items(self, items, **kwargs):
        """
        Method to prepend data to multiple :class:`~couchbase.items.Item` objects.

        See :meth:`append_items` for more information

        .. seealso:: :meth:`append_items`
        """
        rv = self.prepend_multi(items, **kwargs)
        for k, v in items.dict.items():
            if k.success:
                k.value = v["fragment"] + k.value

        return rv

    @property
    def closed(self):
        """
        Returns True if the object has been closed with :meth:`_close`
        """
        return self._privflags & _LCB.PYCBC_CONN_F_CLOSED


    """
    Lists the names of all the memcached operations. This is useful
    for classes which want to wrap all the methods
    """
    _MEMCACHED_OPERATIONS = ('set', 'get', 'add', 'append', 'prepend',
                             'replace', 'delete', 'incr', 'decr', 'touch',
                             'lock', 'unlock', 'arithmetic', 'endure',
                             'observe', 'rget', 'stats')

    _MEMCACHED_NOMULTI = ('stats')

    @classmethod
    def _gen_memd_wrappers(cls, factory):
        """
        Generates wrappers for all the memcached operations.
        :param factory: A function to be called to return the wrapped method.
          It will be called with two arguments; the first is the unbound
          method being wrapped, and the second is the name of such a method.

          The factory shall return a new unbound method

        :return: A dictionary of names mapping the API calls to the wrapped
        functions
        """
        d = {}
        for n in cls._MEMCACHED_OPERATIONS:
            for variant in (n, n + "_multi"):
                try:
                    d[variant] = factory(getattr(cls, variant), variant)
                except AttributeError:
                    if n in cls._MEMCACHED_NOMULTI:
                        continue
                    raise
        return d


    def _cntl(self, *args):
        """
        Interface to 'lcb_cntl'.

        This method accepts an opcode and an
        optional value. Constants are intentionally not defined for
        the various opcodes to allow saner error handling when an
        unknown opcode is not used.

        .. warning::

          If you pass the wrong parameters to this API call, your
          application may crash. For this reason, this is not a
          public API call. Nevertheless it may be used sparingly as
          a workaround for settings which may have not yet been exposed
          directly via a supported API

        :param int op: Type of cntl to access. These are defined in
          libcouchbase's ``cntl.h`` header file

        :param value: An optional value to supply for the operation.
           If a value is not passed then the operation will return
           the current value of the cntl without doing anything else.
           otherwise, it will interpret the cntl in a manner that
           makes sense. If the value is a float, it will be treated
           as a timeout value and will be multiplied by 1000000 to yield
           the microsecond equivalent for the library. If the value
           is a boolean, it is treated as a C ``int``

        :return: current value of the setting
           (if no 'value' argument is provided), or the previous value of the
           setting (if a value was provided).

        """
        return _Base._cntl(self, *args)

########NEW FILE########
__FILENAME__ = exceptions
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import couchbase._libcouchbase as C

class CouchbaseError(Exception):
    """Base exception for Couchbase errors

    This is the base class for all exceptions thrown by Couchbase

    **Exception Attributes**

      .. py:attribute:: rc

      The return code which caused the error

        A :class:`~couchbase.result.MultiResult` object, if this
        exception was thrown as part of a multi-operation. This contains
        all the operations (including ones which may not have failed)

      .. py:attribute:: inner_cause

        If this exception was triggered by another exception, it is
        present here.

      .. py:attribute:: key

        If applicable, this is the key which failed.

      .. py:attribute:: csrc_info

        A tuple of (`file`, `line`) pointing to a location in the C
        source code where the exception was thrown (if applicable)

      .. py:attribute:: categories

        An integer representing a set of bits representing various error
        categories for the specific error as returned by libcouchbase.

      .. py:attribute:: is_data

        True if this error is a negative reply from the server
        (see :exc:`CouchbaseDataError`)

      .. py:attribute:: is_transient

        True if this error was likely caused by a transient condition
        (see :exc:`CouchbaseTransientError`)

      .. py:attribute:: is_fatal

        True if this error indicates a likely fatal condition for the client.
        See :exc:`CouchbaseFatalError`

      .. py:attribute:: is_network

        True if errors were received during TCP transport.
        See :exc:`CouchbaseNetworkError`


    """

    @classmethod
    def rc_to_exctype(cls, rc):
        """
        Map an error code to an exception

        :param int rc: The error code received for an operation

        :return: a subclass of :class:`CouchbaseError`
        """
        try:
            return _LCB_ERRNO_MAP[rc]
        except KeyError:
            newcls = _mk_lcberr(rc)
            _LCB_ERRNO_MAP[rc] = newcls
            return newcls

    @classmethod
    def _can_derive(cls, rc):
        """
        Determines if the given error code is logically derived from this class
        :param int rc: the error code to check
        :return: a boolean indicating if the code is derived from this exception
        """
        return issubclass(cls.rc_to_exctype(rc), cls)

    def __init__(self, params=None):
        if isinstance(params, str):
            params = {'message': params}
        elif isinstance(params, CouchbaseError):
            self.__dict__.update(params.__dict__)
            return

        self.rc = params.get('rc', 0)
        self.all_results = params.get('all_results', {})
        self.result = params.get('result', None)
        self.inner_cause = params.get('inner_cause', None)
        self.csrc_info = params.get('csrc_info', ())
        self.key = params.get('key', None)
        self.objextra = params.get('objextra', None)
        self.message = params.get('message', None)

    @classmethod
    def pyexc(cls, message=None, obj=None, inner=None):
        return cls({'message': message,
                    'objextra': obj,
                    'inner_cause': inner})

    @property
    def categories(self):
        """
        Gets the exception categories (as a set of bits)
        """
        return C._get_errtype(self.rc)

    @property
    def is_transient(self):
        return self.categories & C.LCB_ERRTYPE_TRANSIENT

    @property
    def is_fatal(self):
        return self.categories & C.LCB_ERRTYPE_FATAL

    @property
    def is_network(self):
        return self.categories & C.LCB_ERRTYPE_NETWORK

    @property
    def is_data(self):
        return self.categories & C.LCB_ERRTYPE_DATAOP

    def __str__(self):
        details = []

        if self.key:
            details.append("Key={0}".format(repr(self.key)))

        if self.rc:
            details.append("RC=0x{0:X}[{1}]".format(
                self.rc, C._strerror(self.rc)))
        if self.message:
            details.append(self.message)
        if self.all_results:
            details.append("Results={0}".format(len(self.all_results)))

        if self.inner_cause:
            details.append("inner_cause={0}".format(self.inner_cause))

        if self.csrc_info:
            details.append("C Source=({0},{1})".format(*self.csrc_info))

        if self.objextra:
            details.append("OBJ={0}".format(repr(self.objextra)))

        s = "<{0}>".format(", ".join(details))
        return s


class InternalSDKError(CouchbaseError):
    """
    This means the SDK has done something wrong. Get support.
    (this doesn't mean *you* didn't do anything wrong, it does mean you should
    not be seeing this message)
    """

class CouchbaseInternalError(InternalSDKError):
    pass

class CouchbaseNetworkError(CouchbaseError):
    """
    Base class for network-related errors. These indicate issues in the low
    level connectivity
    """

class CouchbaseInputError(CouchbaseError):
    """
    Base class for errors possibly caused by malformed input
    """

class CouchbaseTransientError(CouchbaseError):
    """
    Base class for errors which are likely to go away with time
    """

class CouchbaseFatalError(CouchbaseError):
    """
    Base class for errors which are likely fatal and require reinitialization
    of the instance
    """

class CouchbaseDataError(CouchbaseError):
    """
    Base class for negative replies received from the server. These errors
    indicate that the server could not satisfy the request because of certain
    data constraints (such as an item not being present, or a CAS mismatch)
    """


class ArgumentError(CouchbaseError):
    """Invalid argument

    A given argument is invalid or must be set
    """


class ValueFormatError(CouchbaseError):
    """Failed to decode or encode value"""


# The following exceptions are derived from libcouchbase
class AuthError(CouchbaseError):
    """Authentication failed

    You provided an invalid username/password combination.
    """


class DeltaBadvalError(CouchbaseError):
    """The given value is not a number

    The server detected that operation cannot be executed with
    requested arguments. For example, when incrementing not a number.
    """


class TooBigError(CouchbaseError):
    """Object too big

    The server reported that this object is too big
    """


class BusyError(CouchbaseError):
    """The cluster is too busy

    The server is too busy to handle your request right now.
    please back off and try again at a later time.
    """


class InternalError(CouchbaseError):
    """Internal Error

    Internal error inside the library. You would have
    to destroy the instance and create a new one to recover.
    """


class InvalidError(CouchbaseError):
    """Invalid arguments specified"""


class NoMemoryError(CouchbaseError):
    """The server ran out of memory"""


class RangeError(CouchbaseError):
    """An invalid range specified"""


class LibcouchbaseError(CouchbaseError):
    """A generic error"""


class TemporaryFailError(CouchbaseError):
    """Temporary failure (on server)

    The server tried to perform the requested operation, but failed
    due to a temporary constraint. Retrying the operation may work.

    This error may also be delivered if the key being accessed was
    locked.

    .. seealso::

        :meth:`couchbase.connection.Connection.lock`
        :meth:`couchbase.connection.Connection.unlock`
    """


class KeyExistsError(CouchbaseError):
    """The key already exists (with another CAS value)

    This exception may be thrown during an ``add()`` operation
    (if the key already exists), or when a CAS is supplied
    and the server-side CAS differs.
    """


class NotFoundError(CouchbaseError):
    """The key does not exist"""


class DlopenFailedError(CouchbaseError):
    """Failed to open shared object"""


class DlsymFailedError(CouchbaseError):
    """Failed to locate the requested symbol in the shared object"""


class NetworkError(CouchbaseNetworkError):
    """Network error

    A network related problem occured (name lookup,
    read/write/connect etc)
    """


class NotMyVbucketError(CouchbaseError):
    """The vbucket is not located on this server

    The server who received the request is not responsible for the
    object anymore. (This happens during changes in the cluster
    topology)
    """


class NotStoredError(CouchbaseError):
    """The object was not stored on the server"""


class NotSupportedError(CouchbaseError):
    """Not supported

    The server doesn't support the requested command. This error
    differs from :exc:`couchbase.exceptions.UnknownCommandError` by
    that the server knows about the command, but for some reason
    decided to not support it.
    """


class UnknownCommandError(CouchbaseError):
    """The server doesn't know what that command is"""


class UnknownHostError(CouchbaseNetworkError):
    """The server failed to resolve the requested hostname"""


class ProtocolError(CouchbaseNetworkError):
    """Protocol error

    There is something wrong with the datastream received from
    the server
    """


class TimeoutError(CouchbaseError):
    """The operation timed out"""


class ConnectError(CouchbaseNetworkError):
    """Failed to connect to the requested server"""


class BucketNotFoundError(CouchbaseError):
    """The requested bucket does not exist"""


class ClientNoMemoryError(CouchbaseError):
    """The client ran out of memory"""


class ClientTemporaryFailError(CouchbaseError):
    """Temporary failure (on client)

    The client encountered a temporary error (retry might resolve
    the problem)
    """


class BadHandleError(CouchbaseError):
    """Invalid handle type

    The requested operation isn't allowed for given type.
    """


class HTTPError(CouchbaseError):
    """HTTP error"""


class ObjectThreadError(CouchbaseError):
    """Thrown when access from multiple threads is detected"""


class ViewEngineError(CouchbaseError):
    """Thrown for inline errors during view queries"""

class ObjectDestroyedError(CouchbaseError):
    """Object has been destroyed. Pending events are invalidated"""


class PipelineError(CouchbaseError):
    """Illegal operation within pipeline state"""

_LCB_ERRCAT_MAP = {
    C.LCB_ERRTYPE_NETWORK:      CouchbaseNetworkError,
    C.LCB_ERRTYPE_INPUT:        CouchbaseInputError,
    C.LCB_ERRTYPE_TRANSIENT:    CouchbaseTransientError,
    C.LCB_ERRTYPE_FATAL:        CouchbaseFatalError,
    C.LCB_ERRTYPE_DATAOP:       CouchbaseDataError,
    C.LCB_ERRTYPE_INTERNAL:     CouchbaseInternalError
}

_LCB_ERRNO_MAP = {
    C.LCB_AUTH_ERROR:       AuthError,
    C.LCB_DELTA_BADVAL:     DeltaBadvalError,
    C.LCB_E2BIG:            TooBigError,
    C.LCB_EBUSY:            BusyError,
    C.LCB_ENOMEM:           NoMemoryError,
    C.LCB_ETMPFAIL:         TemporaryFailError,
    C.LCB_KEY_EEXISTS:      KeyExistsError,
    C.LCB_KEY_ENOENT:       NotFoundError,
    C.LCB_DLOPEN_FAILED:    DlopenFailedError,
    C.LCB_DLSYM_FAILED:     DlsymFailedError,
    C.LCB_NETWORK_ERROR:    NetworkError,
    C.LCB_NOT_MY_VBUCKET:   NotMyVbucketError,
    C.LCB_NOT_STORED:       NotStoredError,
    C.LCB_NOT_SUPPORTED:    NotSupportedError,
    C.LCB_UNKNOWN_HOST:     UnknownHostError,
    C.LCB_PROTOCOL_ERROR:   ProtocolError,
    C.LCB_ETIMEDOUT:        TimeoutError,
    C.LCB_CONNECT_ERROR:    ConnectError,
    C.LCB_BUCKET_ENOENT:    BucketNotFoundError,
    C.LCB_EBADHANDLE:       BadHandleError,
    C.LCB_INVALID_HOST_FORMAT: InvalidError,
    C.LCB_INVALID_CHAR:     InvalidError,
    C.LCB_DURABILITY_ETOOMANY: ArgumentError,
    C.LCB_DUPLICATE_COMMANDS: ArgumentError,
    C.LCB_CLIENT_ETMPFAIL:  ClientTemporaryFailError
}

def _mk_lcberr(rc, name=None, default=CouchbaseError, docstr="", extrabase=[]):
    """
    Create a new error class derived from the appropriate exceptions.
    :param int rc: libcouchbase error code to map
    :param str name: The name of the new exception
    :param class default: Default exception to return if no categories are found
    :return: a new exception derived from the appropriate categories, or the
             value supplied for `default`
    """
    categories = C._get_errtype(rc)
    if not categories:
        return default

    bases = extrabase[::]

    for cat, base in _LCB_ERRCAT_MAP.items():
        if cat & categories:
            bases.append(base)

    if name is None:
        name = "LCB_0x{0:0X}".format(rc)

    d = { '__doc__' : docstr }

    if not bases:
        bases = [CouchbaseError]

    return type(name, tuple(bases), d)

# Reinitialize the exception classes again.
for rc, oldcls in _LCB_ERRNO_MAP.items():
    # Determine the new reparented error category for this
    newname = "_{0}_0x{1:0X} (generated, catch {0})".format(oldcls.__name__, rc)
    newcls = _mk_lcberr(rc, name=newname, default=None, docstr=oldcls.__doc__,
                        extrabase=[oldcls])
    if not newcls:
        # No categories for this type, fall back to existing one
        continue

    _LCB_ERRNO_MAP[rc] = newcls

_EXCTYPE_MAP = {
    C.PYCBC_EXC_ARGUMENTS:  ArgumentError,
    C.PYCBC_EXC_ENCODING:   ValueFormatError,
    C.PYCBC_EXC_INTERNAL:   InternalSDKError,
    C.PYCBC_EXC_HTTP:       HTTPError,
    C.PYCBC_EXC_THREADING:  ObjectThreadError,
    C.PYCBC_EXC_DESTROYED:  ObjectDestroyedError,
    C.PYCBC_EXC_PIPELINE:   PipelineError
}

########NEW FILE########
__FILENAME__ = experimental
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

_USE_EXPERIMENTAL_APIS = False
def enable():
    """
    Enable usage of experimental APIs bundled with Couchbase.
    """
    global _USE_EXPERIMENTAL_APIS
    _USE_EXPERIMENTAL_APIS = True

def enabled_or_raise():
    if _USE_EXPERIMENTAL_APIS:
        return

    raise ImportError(
            "Your application has requested use of an unstable couchbase "
            "client API. Use "
            "couchbase.experimental.enable() to enable experimental APIs. "
            "Experimental APIs are subject to interface, behavior, and "
            "stability changes. Use at your own risk")

########NEW FILE########
__FILENAME__ = base
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
This file is here for example purposes only. It demonstrates the basic
IOPS API.

This is not yet considered stable interface, although this is currently
the only means by which an external event loop can be integrated with
Couchbase through Python
"""

from couchbase._libcouchbase import (
    PYCBC_EVACTION_WATCH,
    PYCBC_EVACTION_UNWATCH,
    PYCBC_EVACTION_CLEANUP,
    LCB_READ_EVENT,
    LCB_WRITE_EVENT,
    LCB_RW_EVENT,
    IOEvent,
    TimerEvent,
    Event
)

class IOPS(object):
    def __init__(self):
        """
        The IOPS class is intended as an efficient and multiplexing
        manager of one or more :class:`Event` objects.

        As this represents an interface with methods only,
        there is no required behavior in the constructor of this object
        """

    def update_event(self, event, action, flags):
        """
        This method shall perform an action modifying an event.

        :param event: An :class:`IOEvent` object which shall have its
          watcher settings modified. The ``IOEvent`` object is an object
          which provides a ``fileno()`` method.

        :param int action: one of:

          * ``PYCBC_EVACTION_WATCH``: Watch this file for events
          * ``PYCBC_EVACTION_UNWATCH``: Remove this file from all watches
          * ``PYCBC_EVACTION_CLEANUP``: Destroy any references to this object

        :param int flags: Event details, this indicates which events this
          file should be watched for. This is only applicable if ``action``
          was ``PYCBC_EVACTION_WATCH``. It can a bitmask of the following:

          * ``LCB_READ_EVENT``: Watch this file until it becomes readable
          * ``LCB_WRITE_EVENT``: Watch this file until it becomes writeable

        If the action is to watch the event for readability or writeability,
        the ``IOPS`` implementation shall schedule the underlying event system
        to call one of the ``ready_r``, ``ready_w`` or ``ready_rw`` methods
        (for readbility, writeability or both readability and writability
        respectively) at such a time when the underlying reactor/event loop
        implementation has signalled it being so.

        Event watchers are non-repeatable. This means that once the event
        has been delivered, the ``IOEvent`` object shall be removed from a
        watching state. The extension shall call this method again for each
        time an event is requested.

        This method must be implemented
        """

    def update_timer(self, timer, action, usecs):
        """
        This method shall schedule or unschedule a timer.

        :param timer: A :class:`TimerEvent` object.
        :param action: See :meth:`update_event` for meaning
        :param usecs: A relative offset in microseconds when this timer
          shall be fired.

        This method follows the same semantics as :meth:`update_event`,
        except that there is no file.

        When the underlying event system shall invoke the timer, the
        ``TimerEvent`` ``ready`` method shall be called with ``0`` as its
        argument.

        Like ``IOEvents``, ``TimerEvents`` are non-repeatable.

        This method must be implemented
        """

    def io_event_factory(self):
        """
        Returns a new instance of :class:`IOEvent`.

        This method is optional, and is useful in case an implementation
        wishes to utilize its own subclass of ``IOEvent``.

        As with most Python subclasses, the user should ensure that the
        base implementation's ``__init__`` is called.
        """

    def timer_event_factory(self):
        """
        Returns a new instance of :class:`TimerEvent`. Like the
        :meth:`io_event_factory`, this is optional
        """

    def start_watching(self):
        """
        Called by the extension when all scheduled IO events have been
        submitted. Depending on the I/O model, this method can either
        drive the event loop until :meth:`stop_watching` is called, or
        do nothing.

        This method must be implemented
        """

    def stop_watching(self):
        """
        Called by the extension when it no longer needs to wait for events.
        Its function is to undo anything which was done in the
        :meth:`start_watching` method

        This method must be implemented
        """

########NEW FILE########
__FILENAME__ = select
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import absolute_import

import select
import time

import couchbase._libcouchbase as LCB
from couchbase._libcouchbase import (
    Event, TimerEvent, IOEvent,
    LCB_READ_EVENT, LCB_WRITE_EVENT, LCB_RW_EVENT,
    PYCBC_EVSTATE_ACTIVE,
    PYCBC_EVACTION_WATCH,
    PYCBC_EVACTION_UNWATCH
)

class SelectTimer(TimerEvent):
    def __init__(self):
        super(SelectTimer, self).__init__()
        self.pydata = 0

    @property
    def exptime(self):
        return self.pydata

    @exptime.setter
    def exptime(self, val):
        self.pydata = val

    def activate(self, usecs):
        self.exptime = time.time() + usecs / 1000000

    def deactivate(self):
        pass

    @property
    def active(self):
        return self.state == PYCBC_EVSTATE_ACTIVE

    # Rich comparison operators implemented - __cmp__ not used in Py3
    def __lt__(self, other): return self.exptime < other.exptime
    def __le__(self, other): return self.exptime <= other.exptime
    def __gt__(self, other): return self.exptime > other.exptime
    def __ge__(self, other): return self.exptime >= other.exptime
    def __ne__(self, other): return self.exptime != other.exptime
    def __eq__(self, other): return self.exptime == other.exptime


class SelectIOPS(object):
    def __init__(self):
        self._do_watch = False
        self._ioevents = set()
        self._timers = []

        # Active readers and writers
        self._evwr = set()
        self._evrd = set()



    def _unregister_timer(self, timer):
        timer.deactivate()
        if timer in self._timers:
            self._timers.remove(timer)

    def _unregister_event(self, event):
        try:
            self._evrd.remove(event)
        except KeyError:
            pass
        try:
            self._evwr.remove(event)
        except KeyError:
            pass
        try:
            self._ioevents.remove(event)
        except KeyError:
            pass

    def update_timer(self, timer, action, usecs):
        if action == PYCBC_EVACTION_UNWATCH:
            self._unregister_timer(timer)
            return

        if timer.active:
            self._unregister_timer(timer)
        timer.activate(usecs)
        self._timers.append(timer)

    def update_event(self, event, action, flags, fd=None):
        if action == PYCBC_EVACTION_UNWATCH:
            self._unregister_event(event)
            return

        elif action == PYCBC_EVACTION_WATCH:
            if flags & LCB_READ_EVENT:
                self._evrd.add(event)
            else:
                try:
                    self._evrd.remove(event)
                except KeyError:
                    pass

            if flags & LCB_WRITE_EVENT:
                self._evwr.add(event)
            else:
                try:
                    self._evwr.remove(event)
                except KeyError:
                    pass

    def _poll(self):
        rin = self._evrd
        win = self._evwr
        ein = list(rin) + list(win)

        self._timers.sort()
        mintime = self._timers[0].exptime - time.time()
        if mintime < 0:
            mintime = 0

        if not (rin or win or ein):
            time.sleep(mintime)
            rout = tuple()
            wout = tuple()
            eout = tuple()
        else:
            rout, wout, eout = select.select(rin, win, ein, mintime)

        now = time.time()

        ready_events = {}
        for ev in rout:
            ready_events[ev] = LCB_READ_EVENT

        for ev in wout:
            if ev in ready_events:
                ready_events[ev] |= LCB_WRITE_EVENT
            else:
                ready_events[ev] = LCB_WRITE_EVENT

        for ev in eout:
            ready_events[ev] = LCB_RW_EVENT

        for ev, flags in ready_events.items():
            if ev.state == PYCBC_EVSTATE_ACTIVE:
                ev.ready(flags)

        for timer in self._timers[:]:
            if not timer.active:
                continue

            if timer.exptime > now:
                continue

            timer.ready(0)

    def start_watching(self):
        if self._do_watch:
            return

        self._do_watch = True
        while self._do_watch:
            self._poll()

    def stop_watching(self):
        self._do_watch = False

    def timer_event_factory(self):
        return SelectTimer()

########NEW FILE########
__FILENAME__ = items
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# This module contains various collections to be used with items. These provide
# various means by which multiple operations can have their options customized

# Each of these collections yields an iterator consisting of a 3-tuple:
# (item, {options})
# The CAS, Format, and Value are all expected to be inside the Item itself;


from couchbase._libcouchbase import Item as _Item

class Item(_Item):
    def __init__(self, key=None, value=None):
        """
        Construct a new `Item` object.

        :param string key: The key to initialize this item with
        :param object value: The value to initialize this item with

        The `Item` class is a sublcass of a
        :class:`~couchbase.result.ValueResult`.
        Its members are all writeable and accessible from this object.

        .. warning::

            As the item build-in properties (such as ``key``, ``value``,
            ``cas``, etc.)
            are implemented directly in C and are not exposed in the item's
            ``__dict__`` field, you cannot override these fields in a subclass
            to be a ``property`` or some other custom data descriptor.

            To confuse matters even more, if you do implement these properties
            as descriptors, they will be visible from your own code, but *not*
            from the implementation code. You have been warned.

            In short, don't override these properties.

            Here's an example of what you should *not* do::

                class MyItem(Item):
                    # ...
                    @property
                    def key(self):
                        return self._key

                    @key.setter
                    def key(self, newkey):
                        self._key = key

        To use this class with the :class:`couchbase.connection.Connection`
        API methods, you must take care to:

        1. Use only the ``*_multi`` methods
        2. Pass one of the :class:`ItemCollection` objects to these methods.
           This will let the API know to enable special handling for
           the :class:`Item` API.

        """

        super(Item, self).__init__()
        self.key = key
        self.value = value

    def as_itcoll(self, **kwargs):
        """
        Convenience method to return an instance of a :class:`ItemCollection`
        containing only this item. This would then be used like so::

            cb.set_multi(itm.as_itcoll())

        Or use it with options::

            cb.set_multi(itm.as_itcoll(ignore_cas=True))

        :param kwargs: Extra operation-specific options.

        :return: An :class:`ItemCollection` instance
        """
        if not kwargs:
            return ItemSequence([self])
        else:
            return ItemOptionDict({self: kwargs})

class ItemCollection(object):
    """
    The base class for a collection of Items.
    """
    def __len__(self):
        raise NotImplementedError()

    def __iter__(self):
        """
        This iterator is mainly intended for the internal API use; it
        yields a tuple of (item, options).
        In the case of a :class:`ItemSequence` which does not store
        options, the second element is always `None`
        """

    def dict_items(self):
        """
        Iterator which returns a tuple of ``(item, options)``
        for each item in this collection.
        """
        return iter(self)

class ItemOptionDict(ItemCollection):
    def __init__(self, d=None):
        """
        A simple mapping of :class:`Item` objects to optional dictionaries
        of values.

        The keys and values for the options dictionary depends on the command
        being used. See the appropriate command for more options

        :param dict d: A dictionary of item -> option, or None.
        """
        if d is None:
            d = {}
        self._d = d

    @property
    def dict(self):
        """
        Return the actual dict object
        """
        return self._d

    def add(self, itm, **options):
        """
        Convenience method to add an item together with a series of options.

        :param itm: The item to add
        :param options: keyword arguments which will be placed in the item's
            option entry.

        If the item already exists, it (and its options) will be overidden. Use
        :attr:`dict` instead to update options

        """
        if not options:
            options = None
        self._d[itm] = options

    def __iter__(self):
        for p in self._d.items():
            yield p

    def __len__(self):
        return len(self._d)

class ItemSequence(ItemCollection):
    def __init__(self, obj):
        """
        Create a new :class:`ItemSequence` object

        :param seq: A sequence containing the items
        :type seq: An iterable or a single item
        """
        self._seq = [ obj ] if isinstance(obj, Item) else obj

    @property
    def sequence(self):
        """
        The actual sequence object passed in
        """
        return self._seq

    def __len__(self):
        return len(self._seq)

    def __iter__(self):
        for e in self._seq:
            yield (e, None)

########NEW FILE########
__FILENAME__ = mockserver
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from subprocess import Popen, PIPE
from couchbase._pyport import urlopen, ulp, basestring
import socket
import json
import os.path

class BucketSpec(object):
    def __init__(self, name='default', bucket_type='couchbase', password=''):
        self.name = name
        self.bucket_type = bucket_type
        self.password = password

    def __str__(self):
        return ':'.join([self.name, self.password, self.bucket_type])

class MockControlClient(object):
    def __init__(self, mockport=18091, host='127.0.0.1'):
        self.urlbase = "http://{0}:{1}/mock/".format(host, mockport)

    def _get_common(self, command, params):
        qparams = {}
        for k, v in params.items():
            qparams[k] = json.dumps(v)
        qparams = ulp.urlencode(qparams)
        url = self.urlbase + "{0}?{1}".format(command, qparams)
        data = urlopen(url).read()
        if not isinstance(data, basestring):
            data = str(data, "utf-8")
        ret = json.loads(data)
        return ret

    def _params_common(self, key,
                       bucket=None,
                       on_master=False,
                       replica_count=None,
                       replicas=None,
                       cas=None,
                       value=None):
        r = {
            'Key' : key,
            'OnMaster' : on_master
        }
        if bucket:
            r['Bucket'] = bucket
        if replica_count is not None:
            r['OnReplicas'] = replica_count
        else:
            r['OnReplicas'] = replicas
        if cas is not None:
            r['CAS'] = cas

        if value is not None:
            r['Value'] = value

        return r

    def _do_request(self, cmd, *args, **kwargs):
        params = self._params_common(*args, **kwargs)
        return self._get_common(cmd, params)

    def keyinfo(self, *args, **kwargs):
        return self._do_request("keyinfo", *args, **kwargs)

    def persist(self, *args, **kwargs):
        return self._do_request("persist", *args, **kwargs)

    def endure(self, *args, **kwargs):
        return self._do_request("endure", *args, **kwargs)

    def cache(self, *args, **kwargs):
        return self._do_request("cache", *args, **kwargs)

    def uncache(self, *args, **kwargs):
        return self._do_request("uncache", *args, **kwargs)

    def unpersist(self, *args, **kwargs):
        return self._do_request("unpersist", *args, **kwargs)

    def purge(self, *args, **kwargs):
        return self._do_request("purge", *args, **kwargs)


class CouchbaseMock(object):
    def _setup_listener(self):
        sock = socket.socket()
        sock.bind( ('', 0) )
        sock.listen(5)

        addr, port = sock.getsockname()
        self.listen = sock
        self.port = port

    def _invoke(self):
        self._setup_listener()
        args = [
            "java", "-client", "-jar", self.runpath,
            "--port", "0",
            "--harakiri-monitor", "127.0.0.1:" + str(self.port),
            "--nodes", str(self.nodes)
        ]

        if self.vbuckets is not None:
            args += ["--vbuckets", str(self.vbuckets)]

        if self.replicas is not None:
            args += ["--replicas", str(self.replicas)]

        bspec = ",".join([str(x) for x in self.buckets])
        args += ["--buckets", bspec]

        self.po = Popen(args)
        self.harakiri_sock, addr = self.listen.accept()
        self.ctlfp = self.harakiri_sock.makefile()

        sbuf = ""
        while True:
            c = self.ctlfp.read(1)
            if c == '\0':
                break
            sbuf += c
        self.rest_port = int(sbuf)

    def __init__(self, buckets, runpath,
                 url=None,
                 replicas=None,
                 vbuckets=None,
                 nodes=4):
        """
        Creates a new instance of the mock server. You must actually call
        'start()' for it to be invoked.
        :param list buckets: A list of BucketSpec items
        :param string runpath: a string pointing to the location of the mock
        :param string url: The URL to use to download the mock. This is only
          used if runpath does not exist
        :param int replicas: How many replicas should each bucket have
        :param int vbuckets: How many vbuckets should each bucket have
        :param int nodes: How many total nodes in the cluster

        Note that you must have ``java`` in your `PATH`
        """


        self.runpath = runpath
        self.buckets = buckets
        self.nodes = nodes
        self.vbuckets = vbuckets
        self.replicas = replicas

        if not os.path.exists(runpath):
            if not url:
                raise Exception(runpath + " Does not exist and no URL specified")
            fp = open(runpath, "wb")
            ulp = urlopen(url)
            jarblob = ulp.read()
            fp.write(jarblob)
            fp.close()

    def start(self):
        self._invoke()

    def stop(self):
        self.po.kill()

########NEW FILE########
__FILENAME__ = result
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from platform import python_implementation

import couchbase._bootstrap
from couchbase._libcouchbase import (
    Result,
    ValueResult,
    OperationResult,
    HttpResult,
    MultiResult,
    ObserveInfo,
    AsyncResult)

if python_implementation() == 'PyPy':
    from couchbase._bootstrap import PyPyMultiResultWrap as MultiResult

########NEW FILE########
__FILENAME__ = base
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import os
import sys
import types
import platform

try:
    from unittest.case import SkipTest
except ImportError:
    from nose.exc import SkipTest

try:
    from configparser import ConfigParser
except ImportError:
    # Python <3.0 fallback
    from ConfigParser import SafeConfigParser as ConfigParser

from testresources import ResourcedTestCase, TestResourceManager

from couchbase.exceptions import CouchbaseError
from couchbase.admin import Admin
from couchbase.mockserver import CouchbaseMock, BucketSpec, MockControlClient
from couchbase.result import (
    MultiResult, ValueResult, OperationResult, ObserveInfo, Result)
from couchbase._pyport import basestring

CONFIG_FILE = 'tests.ini' # in cwd

class ClusterInformation(object):
    def __init__(self):
        self.host = "localhost"
        self.port = 8091
        self.admin_username = "Administrator"
        self.admin_password = "password"
        self.bucket_prefix = "default"
        self.bucket_password = ""
        self.extra_buckets = False

    def make_connargs(self, **overrides):
        ret = {
            'host': self.host,
            'port': self.port,
            'password': self.bucket_password,
            'bucket': self.bucket_prefix
        }
        ret.update(overrides)
        return ret

    def get_sasl_params(self):
        if not self.bucket_password:
            return None
        ret = self.make_connargs()
        if self.extra_buckets:
            ret['bucket'] += "_sasl"
        return ret

    def make_connection(self, conncls, **kwargs):
        return conncls(**self.make_connargs(**kwargs))

    def make_admin_connection(self):
        return Admin(self.admin_username, self.admin_password,
                     self.host, self.port)


class ConnectionConfiguration(object):
    def __init__(self, filename=CONFIG_FILE):
        self._fname = filename
        self.load()

    def load(self):
        config = ConfigParser()
        config.read(self._fname)

        info = ClusterInformation()
        info.host = config.get('realserver', 'host')
        info.port = config.getint('realserver', 'port')
        info.admin_username = config.get('realserver', 'admin_username')
        info.admin_password = config.get('realserver', 'admin_password')
        info.bucket_prefix = config.get('realserver', 'bucket_prefix')
        info.bucket_password = config.get('realserver', 'bucket_password')
        info.extra_buckets = config.getboolean('realserver','extra_buckets')

        if config.getboolean('realserver', 'enabled'):
            self.realserver_info = info
        else:
            self.realserver_info = None

        if (config.has_option("mock", "enabled") and
                              config.getboolean('mock', 'enabled')):

            self.mock_enabled = True
            self.mockpath = config.get("mock", "path")
            if config.has_option("mock", "url"):
                self.mockurl = config.get("mock", "url")
            else:
                self.mockurl = None
        else:
            self.mock_enabled = False


class MockResourceManager(TestResourceManager):
    def __init__(self, config):
        super(MockResourceManager, self).__init__()
        self._config = config
        self._info = None

    def _reset(self, *args, **kw):
        pass

    def make(self, *args, **kw):
        if not self._config.mock_enabled:
            return None

        if self._info:
            return self._info

        bspec_dfl = BucketSpec('default', 'couchbase')
        bspec_sasl = BucketSpec('default_sasl', 'couchbase', 'secret')
        mock = CouchbaseMock([bspec_dfl, bspec_sasl],
                             self._config.mockpath,
                             self._config.mockurl,
                             replicas=2,
                             nodes=4)
        mock.start()

        info = ClusterInformation()
        info.bucket_prefix = "default"
        info.bucket_password = "secret"
        info.port = mock.rest_port
        info.host = "127.0.0.1"
        info.admin_username = "Administrator"
        info.admin_password = "password"
        info.extra_buckets = True
        info.mock = mock
        self._info = info
        return info

    def isDirty(self):
        return False


class RealServerResourceManager(TestResourceManager):
    def __init__(self, config):
        super(RealServerResourceManager, self).__init__()
        self._config = config

    def make(self, *args, **kw):
        return self._config.realserver_info

    def isDirty(self):
        return False


class ApiImplementationMixin(object):
    """
    This represents the interface which should be installed by an implementation
    of the API during load-time
    """
    @property
    def factory(self):
        """
        Return the main Connection class used for this implementation
        """
        raise NotImplementedError()

    @property
    def viewfactory(self):
        """
        Return the view subclass used for this implementation
        """
        raise NotImplementedError()

    @property
    def should_check_refcount(self):
        """
        Return whether the instance's reference cound should be checked at
        destruction time
        """
        raise NotImplementedError()

    cls_MultiResult = MultiResult
    cls_ValueResult = ValueResult
    cls_OperationResult = OperationResult
    cls_ObserveInfo = ObserveInfo
    cls_Result = Result

GLOBAL_CONFIG = ConnectionConfiguration()


class CouchbaseTestCase(ResourcedTestCase):
    resources = [
        ('_mock_info', MockResourceManager(GLOBAL_CONFIG)),
        ('_realserver_info', RealServerResourceManager(GLOBAL_CONFIG))
    ]

    config = GLOBAL_CONFIG

    @property
    def cluster_info(self):
        for v in [self._realserver_info, self._mock_info]:
            if v:
                return v
        raise Exception("Neither mock nor realserver available")

    @property
    def realserver_info(self):
        if not self._realserver_info:
            raise SkipTest("Real server required")
        return self._realserver_info

    @property
    def mock(self):
        try:
            return self._mock_info.mock
        except AttributeError:
            return None

    @property
    def mock_info(self):
        if not self._mock_info:
            raise SkipTest("Mock server required")
        return self._mock_info


    def setUp(self):
        super(CouchbaseTestCase, self).setUp()

        if not hasattr(self, 'assertIsInstance'):
            def tmp(self, a, *bases):
                self.assertTrue(isinstance(a, bases))
            self.assertIsInstance = types.MethodType(tmp, self)
        if not hasattr(self, 'assertIsNone'):
            def tmp(self, a):
                self.assertTrue(a is None)
            self.assertIsNone = types.MethodType(tmp, self)

        self._key_counter = 0

    def get_sasl_cinfo(self):
        for info in [self._realserver_info, self._mock_info]:
            if info and info.bucket_password:
                return info


    def get_sasl_params(self):
        einfo = self.get_sasl_cinfo()
        if not einfo:
            return None
        return einfo.get_sasl_params()

    def skipUnlessSasl(self):
        sasl_params = self.get_sasl_params()
        if not sasl_params:
            raise SkipTest("No SASL buckets configured")

    def skipLcbMin(self, vstr):
        """
        Test requires a libcouchbase version of at least vstr.
        This may be a hex number (e.g. 0x020007) or a string (e.g. "2.0.7")
        """

        if isinstance(vstr, basestring):
            components = vstr.split('.')
            hexstr = "0x"
            for comp in components:
                if len(comp) > 2:
                    raise ValueError("Version component cannot be larger than 99")
                hexstr += "{0:02}".format(int(comp))

            vernum = int(hexstr, 16)
        else:
            vernum = vstr
            components = []
            # Get the display
            for x in range(0, 3):
                comp = (vernum & 0xff << (x*8)) >> x*8
                comp = "{0:x}".format(comp)
                components = [comp] + components
            vstr = ".".join(components)

        rtstr, rtnum = self.factory.lcb_version()
        if rtnum < vernum:
            raise SkipTest(("Test requires {0} to run (have {1})")
                            .format(vstr, rtstr))

    def skipIfMock(self):
        pass

    def skipUnlessMock(self):
        pass

    def skipIfPyPy(self):
        import platform
        if platform.python_implementation() == 'PyPy':
            raise SkipTest("PyPy not supported here..")


    def make_connargs(self, **overrides):
        return self.cluster_info.make_connargs(**overrides)

    def make_connection(self, **kwargs):
        return self.cluster_info.make_connection(self.factory, **kwargs)

    def make_admin_connection(self):
        return self.realserver_info.make_admin_connection()

    def gen_key(self, prefix=None):
        if not prefix:
            prefix = "python-couchbase-key_"

        ret = "{0}{1}".format(prefix, self._key_counter)
        self._key_counter += 1
        return ret

    def gen_key_list(self, amount=5, prefix=None):
        ret = [ self.gen_key(prefix) for x in range(amount) ]
        return ret

    def gen_kv_dict(self, amount=5, prefix=None):
        ret = {}
        keys = self.gen_key_list(amount=amount, prefix=prefix)
        for k in keys:
            ret[k] = "Value_For_" + k
        return ret


class ConnectionTestCase(CouchbaseTestCase):
    def checkCbRefcount(self):
        if not self.should_check_refcount:
            return

        import gc
        if platform.python_implementation() == 'PyPy':
            return

        gc.collect()
        for x in range(10):
            oldrc = sys.getrefcount(self.cb)
            if oldrc > 2:
                gc.collect()
            else:
                break

        self.assertEqual(oldrc, 2)

    def setUp(self):
        super(ConnectionTestCase, self).setUp()
        self.cb = self.make_connection()

    def tearDown(self):
        super(ConnectionTestCase, self).tearDown()
        try:
            self.checkCbRefcount()
        finally:
            del self.cb


class RealServerTestCase(ConnectionTestCase):
    def setUp(self):
        super(RealServerTestCase, self).setUp()

        if not self._realserver_info:
            raise SkipTest("Need real server")

    @property
    def cluster_info(self):
        return self.realserver_info


# Class which sets up all the necessary Mock stuff
class MockTestCase(ConnectionTestCase):
    def setUp(self):
        super(MockTestCase, self).setUp()
        self.skipUnlessMock()
        self.mockclient = MockControlClient(self.mock.rest_port)

    def make_connection(self, **kwargs):
        return self.mock_info.make_connection(self.factory, **kwargs)

    @property
    def cluster_info(self):
        return self.mock_info

class DDocTestCase(RealServerTestCase):
    pass


class ViewTestCase(RealServerTestCase):
    pass

########NEW FILE########
__FILENAME__ = admin_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import sys
import platform

from couchbase.admin import Admin
from couchbase.result import HttpResult
from couchbase.exceptions import (
    BadHandleError, ArgumentError, AuthError, ConnectError, CouchbaseError,
    HTTPError)
from couchbase.tests.base import CouchbaseTestCase

class AdminSimpleTest(CouchbaseTestCase):
    def setUp(self):
        super(AdminSimpleTest, self).setUp()
        self.skipIfMock()
        self.admin = self.make_admin_connection()

    def tearDown(self):
        super(AdminSimpleTest, self).tearDown()
        if platform.python_implementation() != 'PyPy':
            rc = sys.getrefcount(self.admin)
            self.assertEqual(rc, 2)

        del self.admin

    def test_http_request(self):
        htres = self.admin.http_request('pools/')
        self.assertIsInstance(htres, HttpResult)
        self.assertIsInstance(htres.value, dict)
        self.assertEqual(htres.http_status, 200)
        self.assertEqual(htres.url, 'pools/')
        self.assertTrue(htres.success)

    def test_bad_request(self):
        self.assertRaises(HTTPError,
                          self.admin.http_request,
                          '/badpath')

        excraised = 0
        try:
            self.admin.http_request("/badpath")
        except HTTPError as e:
            excraised = 1
            self.assertIsInstance(e.objextra, HttpResult)

        self.assertTrue(excraised)

    def test_bad_args(self):
        self.assertRaises(ArgumentError,
                          self.admin.http_request,
                          None)

        self.assertRaises(ArgumentError,
                          self.admin.http_request,
                          '/',
                          method='blahblah')

    def test_bad_auth(self):
        self.assertRaises(AuthError, Admin,
                          'baduser', 'badpass', host=self.cluster_info.host)

    def test_bad_host(self):
        self.assertRaises(ConnectError, Admin,
                          'user', 'pass', host='127.0.0.1', port=1)

    def test_bad_handle(self):
        self.assertRaises(BadHandleError, self.admin.set, "foo", "bar")
        self.assertRaises(BadHandleError, self.admin.get, "foo")
        self.assertRaises(BadHandleError, self.admin.append, "foo", "bar")
        self.assertRaises(BadHandleError, self.admin.delete, "foo")
        self.assertRaises(BadHandleError, self.admin.unlock, "foo", 1)
        str(None)

########NEW FILE########
__FILENAME__ = append_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase import FMT_JSON, FMT_PICKLE, FMT_BYTES, FMT_UTF8

from couchbase.exceptions import (KeyExistsError, ValueFormatError,
                                  ArgumentError, NotFoundError,
                                  NotStoredError)

from couchbase.tests.base import ConnectionTestCase


class ConnectionAppendTest(ConnectionTestCase):

    def test_append_prepend(self):
        key = self.gen_key("appendprepend")
        vbase = "middle"
        self.cb.set(key, vbase, format=FMT_UTF8)
        self.cb.prepend(key, "begin ")
        self.cb.append(key, " end")
        self.assertEquals(self.cb.get(key).value,
                          "begin middle end")


    def test_append_binary(self):
        kname = self.gen_key("binary_append")
        initial = b'\x10'
        self.cb.set(kname, initial, format=FMT_BYTES)
        self.cb.append(kname, b'\x20', format=FMT_BYTES)
        self.cb.prepend(kname, b'\x00', format=FMT_BYTES)

        res = self.cb.get(kname)
        self.assertEqual(res.value, b'\x00\x10\x20')

    def test_append_nostr(self):
        key = self.gen_key("append_nostr")
        self.cb.set(key, "value")
        rv = self.cb.append(key, "a_string")
        self.assertTrue(rv.cas)

        self.assertRaises(ValueFormatError,
                          self.cb.append, "key", { "some" : "object" })

    def test_append_enoent(self):
        key = self.gen_key("append_enoent")
        self.cb.delete(key, quiet=True)
        self.assertRaises(NotStoredError,
                          self.cb.append, key, "value")

    def test_append_multi(self):
        kv = self.gen_kv_dict(amount=4, prefix="append_multi")

        self.cb.set_multi(kv, format=FMT_UTF8)
        self.cb.append_multi(kv)
        self.cb.prepend_multi(kv)

        rvs = self.cb.get_multi(list(kv.keys()))
        self.assertTrue(rvs.all_ok)
        self.assertEqual(len(rvs), 4)

        for k, v in rvs.items():
            basekey = kv[k]
            self.assertEqual(v.value, basekey * 3)

########NEW FILE########
__FILENAME__ = arithmetic_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.exceptions import (NotFoundError, DeltaBadvalError)
from couchbase.tests.base import ConnectionTestCase


class ConnectionArithmeticTest(ConnectionTestCase):

    def test_trivial_incrdecr(self):
        key = self.gen_key("trivial_incrdecr")
        self.cb.delete(key, quiet=True)
        rv_arith = self.cb.incr(key, initial=1)
        rv_get = self.cb.get(key)

        self.assertEqual(rv_arith.value, 1)
        self.assertEqual(int(rv_get.value), 1)

        rv = self.cb.incr(key)
        self.assertEquals(rv.value, 2)

        rv = self.cb.decr(key)
        self.assertEquals(rv.value, 1)
        self.assertEquals(int(self.cb.get(key).value), 1)

        rv = self.cb.decr(key)
        self.assertEquals(rv.value, 0)
        self.assertEquals(int(self.cb.get(key).value), 0)

    def test_incr_notfound(self):
        key = self.gen_key("incr_notfound")
        self.cb.delete(key, quiet=True)
        self.assertRaises(NotFoundError,
                          self.cb.incr, key)

    def test_incr_badval(self):
        key = self.gen_key("incr_badval")
        self.cb.set(key, "THIS IS SPARTA")
        self.assertRaises(DeltaBadvalError,
                          self.cb.incr, key)

    def test_incr_multi(self):
        keys = self.gen_key_list(amount=5, prefix="incr_multi")

        def _multi_lim_assert(expected):
            for k, v in self.cb.get_multi(keys).items():
                self.assertTrue(k in keys)
                self.assertEqual(v.value, expected)

        self.cb.delete_multi(keys, quiet=True)
        self.cb.incr_multi(keys, initial=5)
        _multi_lim_assert(5)

        self.cb.incr_multi(keys)
        _multi_lim_assert(6)

        self.cb.decr_multi(keys)
        _multi_lim_assert(5)

        self.cb.incr_multi(keys, amount=10)
        _multi_lim_assert(15)

        self.cb.decr_multi(keys, amount=6)
        _multi_lim_assert(9)

        self.cb.delete(keys[0])

        self.assertRaises(NotFoundError,
                          self.cb.incr_multi, keys)

    def test_incr_extended(self):
        key = self.gen_key("incr_extended")
        self.cb.delete(key, quiet=True)
        rv = self.cb.incr(key, initial=10)
        self.assertEquals(rv.value, 10)
        srv = self.cb.set(key, "42", cas=rv.cas)
        self.assertTrue(srv.success)

        # test with multiple values?
        klist = self.gen_key_list(amount=5, prefix="incr_extended_list")
        self.cb.delete_multi(klist, quiet=True)
        rvs = self.cb.incr_multi(klist, initial=40)
        [ self.assertEquals(x.value, 40) for x in rvs.values() ]
        self.assertEquals(sorted(list(rvs.keys())), sorted(klist))


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = badargs_t
from time import sleep

from couchbase import FMT_JSON, FMT_PICKLE, FMT_UTF8, FMT_BYTES
from couchbase.exceptions import (KeyExistsError, ValueFormatError,
                                  ArgumentError, NotFoundError,
                                  NotStoredError)
from couchbase.tests.base import ConnectionTestCase

#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

class ConnectionBadArgsTest(ConnectionTestCase):

    def test_bad_single(self):

        for k in (
            (),
            ("key",),
            {"key":"value"},
            [],
            set(),
            {}.keys(),
            {}.values(),
            ["key"],
            None,
            True,
            False,
            0,
            object()):

            print("Testing with key (%r)" % (k,))

            self.assertRaises(ValueFormatError, self.cb.get, k)
            self.assertRaises(ValueFormatError, self.cb.incr, k)
            self.assertRaises(ValueFormatError, self.cb.delete, k)
            self.assertRaises(ValueFormatError, self.cb.set, k, "value")
            self.assertRaises(ValueFormatError, self.cb.set, "key", k,
                              format=FMT_UTF8)
            self.assertRaises(ValueFormatError, self.cb.set, "key", k,
                              format=FMT_BYTES)
            self.assertRaises(ValueFormatError, self.cb.append, "key", k)

    def test_bad_multi(self):
        for k in (
            "key",
            None,
            [],
            {},
            set(),
            {}.keys(),
            {}.values(),
            0,
            object()):
            print("Testing with keys (%r)" % (k,))

            self.assertRaises(ArgumentError, self.cb.get_multi, k)
            self.assertRaises(ArgumentError, self.cb.set_multi, k)
            self.assertRaises(ArgumentError, self.cb.incr_multi, k)
            self.assertRaises(ArgumentError, self.cb.delete_multi, k)

    def test_bad_timeout(self):
        def _set_timeout(x):
            self.cb.timeout = x

        self.assertRaises(ValueError, _set_timeout, 0)
        self.assertRaises(ValueError, _set_timeout, -1)
        self.assertRaises(TypeError, _set_timeout, None)
        self.assertRaises(TypeError, _set_timeout, "a string")

        self.cb.timeout = 0.1
        self.cb.timeout = 1
        self.cb.timeout = 2.5

    def test_bad_quiet(self):
        def _set_quiet(x):
            self.cb.quiet = x

        self.assertRaises(Exception, _set_quiet, "asfasf")
        self.assertRaises(Exception, _set_quiet, None)
        _set_quiet(True)
        _set_quiet(False)

    def test_badargs_get(self):
        self.assertRaises(ArgumentError, self.cb.get_multi,
                          {"key" : "string"})
        self.assertRaises(ArgumentError, self.cb.get_multi,
                          { "key" : object()} )
        self.assertRaises(ArgumentError, self.cb.get, "string", ttl="string")
        self.assertRaises(ArgumentError, self.cb.lock, "string", ttl="string")
        self.assertRaises(ArgumentError, self.cb.get, "string", ttl=object())

    def test_bad_default_format(self):
        def _set_fmt(x):
            self.cb.default_format = x
            self.assertEqual(self.cb.default_format, x)

        _set_fmt(FMT_JSON)
        _set_fmt(FMT_BYTES)
        _set_fmt(FMT_UTF8)
        _set_fmt(FMT_PICKLE)

        self.assertRaises(ArgumentError, _set_fmt, "a format")
        self.assertRaises(ArgumentError, _set_fmt, None)
        self.assertRaises(ArgumentError, _set_fmt, False)
        self.assertRaises(ArgumentError, _set_fmt, True)
        self.assertRaises(ArgumentError, _set_fmt, object())

        # TODO: Stricter format handling

        #self.assertRaises(ArgumentError, self.cb.set,
        #                  "foo", "bar", format=-1)

    def test_negative_ttl(self):
        for bad_ttl in (-1,
                        "ttl",
                        object(),
                        [1],
                        {'foo':'bar'},
                        2**100):

            print(bad_ttl)
            self.assertRaises(ArgumentError, self.cb.get, "key", ttl=bad_ttl)
            self.assertRaises(ArgumentError, self.cb.set, "key", "value",
                              ttl=bad_ttl)
            self.assertRaises(ArgumentError, self.cb.touch, "key", ttl=bad_ttl)
            self.assertRaises(ArgumentError, self.cb.incr, "key", ttl=bad_ttl)
            self.assertRaises(ArgumentError, self.cb.lock, "key", ttl=bad_ttl)

            self.assertRaises(ArgumentError, self.cb.get_multi,
                              ["key"], ttl=bad_ttl)
            self.assertRaises(ArgumentError, self.cb.get_multi,
                              { "key" : { 'ttl' : bad_ttl } })
            self.assertRaises(ArgumentError, self.cb.get_multi,
                              { "key" : bad_ttl } )
            self.assertRaises(ArgumentError, self.cb.incr_multi,
                              "key", ttl=bad_ttl)
            self.assertRaises(ArgumentError, self.cb.lock_multi,
                              "key", ttl=bad_ttl)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = connection_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import tempfile
import os

from nose.plugins.attrib import attr

from couchbase.exceptions import (AuthError, ArgumentError,
                                  BucketNotFoundError, ConnectError,
                                  CouchbaseNetworkError,
                                  NotFoundError, InvalidError,
                                  TimeoutError)
from couchbase.tests.base import CouchbaseTestCase, SkipTest


class ConnectionTest(CouchbaseTestCase):
    def test_connection_host_port(self):
        cb = self.factory(host=self.cluster_info.host,
                          port=self.cluster_info.port,
                          password=self.cluster_info.bucket_password,
                          bucket=self.cluster_info.bucket_prefix)
        # Connection didn't throw an error
        self.assertIsInstance(cb, self.factory)

    @attr('slow')
    def test_server_not_found(self):
        connargs = self.make_connargs()
        connargs['host'] = 'example.com'
        self.assertRaises((CouchbaseNetworkError, TimeoutError),
                          self.factory, **connargs)

        connargs['host'] = self.cluster_info.host
        connargs['port'] = 34567
        self.assertRaises(CouchbaseNetworkError, self.factory, **connargs)

    def test_bucket(self):
        cb = self.factory(**self.make_connargs())
        self.assertIsInstance(cb, self.factory)

    def test_sasl_bucket(self):
        self.skipUnlessSasl()
        cb = self.factory(**self.get_sasl_cinfo().make_connargs())
        self.assertIsInstance(cb, self.factory)

    def test_bucket_not_found(self):
        connargs = self.make_connargs(bucket='this_bucket_does_not_exist')
        self.assertRaises(BucketNotFoundError, self.factory, **connargs)

    def test_bucket_wrong_credentials(self):
        sasl_info = self.get_sasl_cinfo()
        if sasl_info is self.mock_info:
            raise SkipTest("Mock not supported")

        self.assertRaises(AuthError, self.factory,
                          **self.make_connargs(password='bad_pass'))

        self.assertRaises(AuthError, self.factory,
                          **self.make_connargs(password='wrong_password'))

    def test_sasl_bucket_wrong_credentials(self):
        self.skipUnlessSasl()
        sasl_info = self.get_sasl_cinfo()
        sasl_bucket = sasl_info.get_sasl_params()['bucket']
        self.assertRaises(AuthError, self.factory,
                          **sasl_info.make_connargs(password='wrong_password',
                                               bucket=sasl_bucket))

    def test_quiet(self):
        connparams = self.make_connargs()
        cb = self.factory(**connparams)
        self.assertRaises(NotFoundError, cb.get, 'missing_key')

        cb = self.factory(quiet=True, **connparams)
        cb.delete('missing_key', quiet=True)
        val1 = cb.get('missing_key')
        self.assertFalse(val1.success)

        cb = self.factory(quiet=False, **connparams)
        self.assertRaises(NotFoundError, cb.get, 'missing_key')


    def test_conncache(self):
        cachefile = None
        # On Windows, the NamedTemporaryFile is deleted right when it's
        # created. So we need to ensure it's not deleted, and delete it
        # ourselves when it's closed
        try:
            cachefile = tempfile.NamedTemporaryFile(delete=False)
            cb = self.factory(conncache=cachefile.name, **self.make_connargs())
            self.assertTrue(cb.set("foo", "bar").success)

            cb2 = self.factory(config_cache=cachefile.name, **self.make_connargs())

            self.assertTrue(cb2.set("foo", "bar").success)
            self.assertEquals("bar", cb.get("foo").value)

            sb = os.stat(cachefile.name)

            # For some reason this fails on Windows?
            self.assertTrue(sb.st_size > 0)
        finally:
            # On windows, we can't delete if the file is still being used
            cachefile.close()
            os.unlink(cachefile.name)

        # TODO, see what happens when bad path is used
        # apparently libcouchbase does not report this failure.

    def test_connection_errors(self):
        cb = self.factory(password='bad',
                          bucket='meh',
                          host='localhost',
                          port=1,
                          _no_connect_exceptions=True)
        errors = cb.errors()
        self.assertTrue(len(errors))
        self.assertEqual(len(errors[0]), 2)

        cb = self.factory(**self.make_connargs())
        self.assertFalse(len(cb.errors()))

    def test_invalid_hostname(self):
        self.assertRaises(InvalidError,
                          self.factory,
                          bucket='default', host='12345:qwer###')

    def test_multi_hosts(self):
        kwargs = {
            'password' : self.cluster_info.bucket_password,
            'bucket' : self.cluster_info.bucket_prefix
        }

        if not self.mock:
            cb = self.factory(host=[self.cluster_info.host], **kwargs)
            self.assertTrue(cb.set("foo", "bar").success)

        hostspec = [(self.cluster_info.host, self.cluster_info.port)]
        cb = self.factory(host=hostspec, **kwargs)
        self.assertTrue(cb.set("foo", "bar").success)

        hostlist = [
            ('localhost', 1),
            (self.cluster_info.host,
             self.cluster_info.port)
        ]
        cb = self.factory(host=hostlist, **kwargs)
        self.assertTrue(cb.set("foo", "bar").success)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = couchbase_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase import Couchbase
from couchbase.connection import Connection
from couchbase.tests.base import CouchbaseTestCase


BUCKET_NAME = 'test_bucket_for_pythonsdk'


class CouchbaseTest(CouchbaseTestCase):
    def test_is_instance_of_connection(self):
        self.assertIsInstance(
            Couchbase.connect(host=self.cluster_info.host,
                              port=self.cluster_info.port,
                              password=self.cluster_info.bucket_password,
                              bucket=self.cluster_info.bucket_prefix),
            Connection)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = delete_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.exceptions import (KeyExistsError, NotFoundError)
from couchbase.tests.base import ConnectionTestCase

class ConnectionDeleteTest(ConnectionTestCase):

    def test_trivial_delete(self):
        # Try to delete a key that exists. Ensure that the operation
        # succeeds

        key = self.gen_key("trivial_delete")
        rv = self.cb.set(key, 'value')
        self.assertTrue(rv.success)
        self.assertTrue(rv.cas > 0)
        rv = self.cb.delete(key)
        self.assertTrue(rv.success)

    def test_delete_notfound(self):
        # Delete a key that does not exist.
        # With 'quiet' ensure that it returns false. Without 'quiet', ensure that
        # it raises a NotFoundError

        self.cb.delete("foo", quiet = True)
        rv = self.cb.delete("foo", quiet = True)
        self.assertFalse(rv.success)
        self.assertRaises(NotFoundError, self.cb.delete, 'foo')

    def test_delete_cas(self):
        # Delete with a CAS value. Ensure that it returns OK

        key = self.gen_key("delete_cas")
        rv1 = self.cb.set(key, 'bar')
        self.assertTrue(rv1.cas > 0)
        rv2 = self.cb.delete(key, cas = rv1.cas)
        self.assertTrue(rv2.success)

    def test_delete_badcas(self):
        # Simple delete with a bad CAS

        key = self.gen_key("delete_badcas")
        self.cb.set(key, 'bar')
        self.assertRaises(KeyExistsError,
                self.cb.delete, key, cas = 0xdeadbeef)

    def test_delete_multi(self):
        # Delete passing a list of keys

        kvlist = self.gen_kv_dict(amount=5, prefix='delete_multi')

        rvs = self.cb.set_multi(kvlist)
        self.assertTrue(len(rvs) == len(kvlist))
        rm_rvs = self.cb.delete_multi(list(rvs.keys()))
        self.assertTrue(len(rm_rvs) == len(kvlist))
        self.assertTrue(rm_rvs.all_ok)

        for k, v in rm_rvs.items():
            self.assertTrue(k in kvlist)
            self.assertTrue(v.success)

    def test_delete_dict(self):
        # Delete passing a dict of key:cas pairs

        kvlist = self.gen_kv_dict(amount=5, prefix='delete_dict')

        rvs = self.cb.set_multi(kvlist)
        self.assertTrue(rvs.all_ok)

        # We should just be able to pass it to 'delete'
        rm_rvs = self.cb.delete_multi(rvs)
        self.assertTrue(rm_rvs.all_ok)
        for k, v in rm_rvs.items():
            self.assertTrue(v.success)

    def test_delete_mixed(self):
        # Delete with mixed success-error keys.
        # Test with mixed found/not-found
        # Test with mixed cas-valid/cas-invalid

        self.cb.delete("foo", quiet = True)

        self.cb.set("bar", "a_value")
        # foo does not exit,

        rvs = self.cb.delete_multi(('foo', 'bar'), quiet = True)
        self.assertFalse(rvs.all_ok)
        self.assertTrue(rvs['bar'].success)
        self.assertFalse(rvs['foo'].success)

        # Now see what happens if we delete those with a bad CAS
        kvs = self.gen_kv_dict(amount=3, prefix="delete_mixed_badcas")
        keys = list(kvs.keys())
        cas_rvs = self.cb.set_multi(kvs)

        # Ensure set had no errors
        set_errors = []
        for k, v in cas_rvs.items():
            if not v.success:
                set_errors.append([k, v])
        self.assertTrue(len(set_errors) == 0)

        # Set one to have a bad CAS
        cas_rvs[keys[0]] = 0xdeadbeef
        self.assertRaises(KeyExistsError,
                          self.cb.delete_multi, cas_rvs)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = design_t
0#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import time

from nose.plugins.attrib import attr

from couchbase.tests.base import DDocTestCase
from couchbase.exceptions import HTTPError, CouchbaseError

DNAME = "tmp"
VNAME = "a_view"

DESIGN_JSON = {
    'language' : 'javascript',
    'views' : {
        VNAME : {
            'map' : "function(doc) { emit(null,null); }"
        }
    }
}

@attr('slow')
class DesignDocManagementTest(DDocTestCase):
    def setUp(self):
        super(DesignDocManagementTest, self).setUp()
        self.skipIfMock()

        try:
            self.cb.design_delete(DNAME, use_devmode=False, syncwait=5)
        except HTTPError:
            pass

        try:
            self.cb.design_delete(DNAME, use_devmode=True, syncwait=5)
        except HTTPError:
            pass

    def test_design_management(self):
        rv = self.cb.design_create(DNAME,
                                   DESIGN_JSON,
                                   use_devmode=True,
                                   syncwait=5)
        self.assertTrue(rv.success)
        rv = self.cb._view(DNAME, VNAME, use_devmode=True,
                           params = { 'limit':10 })
        print(rv)
        self.assertTrue(rv.success)

        rv = self.cb.design_publish(DNAME, syncwait=5)
        self.assertTrue(rv.success)

        rv = self.cb._view(DNAME, VNAME, use_devmode=False,
                           params = { 'limit':10 })
        self.assertTrue(rv.success)

        self.assertRaises(HTTPError,
                          self.cb._view,
                          DNAME, VNAME,
                          use_devmode=True)

        rv = self.cb.design_delete(DNAME, use_devmode=False, syncwait=5)
        self.assertTrue(rv.success)

        self.assertRaises(HTTPError,
                          self.cb._view,
                          DNAME, VNAME,
                          use_devmode=False)

    def test_design_headers(self):
        rv = self.cb.design_create(DNAME, DESIGN_JSON, use_devmode=True,
                                   syncwait=5)

        rv = self.cb.design_get(DNAME, use_devmode=True)
        self.assertTrue(rv.headers)
        print(rv.headers)
        self.assertTrue('X-Couchbase-Meta' in rv.headers)

########NEW FILE########
__FILENAME__ = dupkeys_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import warnings

from couchbase.tests.base import ConnectionTestCase
from couchbase.exceptions import NotFoundError, TemporaryFailError
import couchbase._libcouchbase as LCB

class DupKeyTestCase(ConnectionTestCase):
    def setUp(self):
        super(DupKeyTestCase, self).setUp()

    def _assertWarned(self, wlog):
        mcount = 0
        while wlog:
            w = wlog.pop()
            self.assertEqual(w.category, RuntimeWarning)
            print(w.message)
            mcount += 1

        self.assertTrue(mcount)
        warnings.resetwarnings()

    def test_duplicate_keys(self):
        with warnings.catch_warnings(record=True) as wlog:
            self.cb._privflags |= LCB.PYCBC_CONN_F_WARNEXPLICIT
            warnings.resetwarnings()

            meths = (self.cb.get_multi,
                     self.cb.delete_multi,
                     self.cb.incr_multi,
                     self.cb.decr_multi)

            for m in meths:
                print(m.__name__)
                try:
                    m(("foo", "foo"))
                except NotFoundError:
                    pass
                self._assertWarned(wlog)


            try:
                self.cb.lock_multi(("foo", "foo"), ttl=5)
            except NotFoundError:
                pass
            self._assertWarned(wlog)

            ktmp = self.gen_key("duplicate_keys")
            rv = self.cb.set(ktmp, "value")

            try:
                self.cb.unlock_multi((rv, rv))
            except (NotFoundError, TemporaryFailError):
                pass
            self._assertWarned(wlog)

########NEW FILE########
__FILENAME__ = empty_key_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.exceptions import ArgumentError
from couchbase.tests.base import ConnectionTestCase

class EmptyKeyTest(ConnectionTestCase):

    def test_empty_key(self):
        fnargs = (
            (self.cb.set, ["", "value"]),
            (self.cb.get, [""]),
            (self.cb.lock, ["", {'ttl': 5}]),
            (self.cb.incr, [""]),
            (self.cb.unlock, ["", 1234]),
            (self.cb.delete, [""]),
            (self.cb.observe, [""]),
            (self.cb.set_multi, [{"": "value"}]),
            (self.cb.incr_multi, [("", "")]),
            (self.cb.delete_multi, [("", "")]),
            (self.cb.unlock_multi, [{"": 1234}]),
            (self.cb.observe_multi, [("")])
        )

        for fn, args in fnargs:
            self.assertRaises(ArgumentError, fn, *args)

########NEW FILE########
__FILENAME__ = encodings_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase import FMT_BYTES, FMT_JSON, FMT_PICKLE, FMT_UTF8
from couchbase.connection import Connection
from couchbase.exceptions import ValueFormatError, CouchbaseError
from couchbase.tests.base import ConnectionTestCase, SkipTest

BLOB_ORIG =  b'\xff\xfe\xe9\x05\xdc\x05\xd5\x05\xdd\x05'

class ConnectionEncodingTest(ConnectionTestCase):

    def test_default_format(self):
        self.assertEqual(self.cb.default_format, FMT_JSON)

    def test_unicode(self):
        txt = BLOB_ORIG.decode('utf-16')
        for f in (FMT_BYTES, FMT_PICKLE):
            cas = self.cb.set(txt, txt.encode('utf-16'), format=f).cas
            server_val = self.cb.get(txt).value
            self.assertEquals(server_val, BLOB_ORIG)

    def test_json_unicode(self):
        self.assertEqual(self.cb.default_format, FMT_JSON)
        uc = BLOB_ORIG.decode('utf-16')
        rv = self.cb.set(uc, uc)
        self.assertTrue(rv.success)
        rv = self.cb.get(uc)
        self.assertEqual(rv.value, uc)
        self.assertEqual(rv.key, uc)

    def test_json_compact(self):
        # This ensures our JSON encoder doesn't store huge blobs of data in the
        # server. This was added as a result of PYCBC-108
        self.assertEqual(self.cb.default_format, FMT_JSON)
        uc = BLOB_ORIG.decode('utf-16')
        key = self.gen_key('json_compact')
        self.cb.set(key, uc, format=FMT_JSON)
        self.cb.data_passthrough = 1
        rv = self.cb.get(key)

        expected = '"'.encode('utf-8') + uc.encode('utf-8') + '"'.encode('utf-8')
        self.assertEqual(expected, rv.value)

        self.cb.data_passthrough = 0

    def test_blob(self):
        blob = b'\x00\x01\x00\xfe\xff\x01\x42'
        for f in (FMT_BYTES, FMT_PICKLE):
            cas = self.cb.set("key", blob, format=f).cas
            self.assertTrue(cas)
            rv = self.cb.get("key").value
            self.assertEquals(rv, blob)

    def test_bytearray(self):
        ba = bytearray(b"Hello World")
        self.cb.set("key", ba, format=FMT_BYTES)
        rv = self.cb.get("key")
        self.assertEqual(ba, rv.value)

    def test_passthrough(self):
        self.cb.data_passthrough = True
        self.cb.set("malformed", "some json")
        self.cb.append("malformed", "blobs")
        rv = self.cb.get("malformed")

        self.assertTrue(rv.success)
        self.assertEqual(rv.flags, FMT_JSON)
        self.assertEqual(rv.value, b'"some json"blobs')

        self.cb.data_passthrough = False
        self.assertRaises(ValueFormatError, self.cb.get, "malformed")

    def test_zerolength(self):
        rv = self.cb.set("key", b"", format=FMT_BYTES)
        self.assertTrue(rv.success)
        rv = self.cb.get("key")
        self.assertEqual(rv.value, b"")

        self.assertRaises(CouchbaseError, self.cb.set, "", "value")

    def test_blob_keys_py2(self):
        if bytes == str:
            rv = self.cb.set(b"\0", "value")
            rv = self.cb.get(b"\0")
        else:
            self.assertRaises(ValueFormatError, self.cb.set, b"\0", "value")

########NEW FILE########
__FILENAME__ = endure_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.exceptions import NotFoundError, ArgumentError, TimeoutError
from couchbase.tests.base import MockTestCase

class ConnectionEndureTest(MockTestCase):
    #XXX: Require LCB 2.1.0

    def test_excessive(self):
        self.assertRaises(ArgumentError,
                          self.cb.set,
                          "foo", "bar",
                          persist_to=99, replicate_to=99)

    def test_embedded_endure_set(self):
        key = self.gen_key("embedded_endure")
        with self.cb.durability(persist_to=-1, replicate_to=-1, timeout=0.1):
            def cb1(res):
                self.mockclient.endure(key,
                                       replica_count=self.mock.replicas,
                                       value=90,
                                       cas=res.cas)

            self.cb._dur_testhook = cb1
            rv = self.cb.set(key, "blah blah")
            self.assertTrue(rv.success)


            def cb2(res):
                self.mockclient.unpersist(key, on_master=True,
                                          replica_count=self.mock.replicas)

            self.cb._dur_testhook = cb2
            self.assertRaises(TimeoutError, self.cb.set, key, "value")

    def test_embedded_endure_delete(self):
        key = self.gen_key("embedded_endure_delete")
        cas = 12345

        # Store it first
        self.mockclient.endure(key, replica_count=self.mock.replicas,
                               on_master=True,
                               value=666666, cas=cas)

        with self.cb.durability(persist_to=-1, replicate_to=-1, timeout=0.1):
            def cb1(res):
                self.mockclient.purge(key, on_master=True,
                                      replica_count=self.mock.replicas)

            res = self.cb.get(key)

            self.cb._dur_testhook = cb1
            rv_rm = self.cb.delete(key)
            self.assertTrue(rv_rm.success)



            self.mockclient.endure(key, on_master=True,
                                   replica_count=self.mock.replicas,
                                   cas=cas, value="blah")

            self.cb._dur_testhook =  None
            self.assertRaises(TimeoutError, self.cb.delete, key)


    def test_single_poll(self):
        key = self.gen_key("endure_single_poll")
        self.mockclient.endure(key,
                               on_master=True,
                               replica_count=self.mock.replicas,
                               value=90,
                               cas=1234)

        rv = self.cb.endure(key,
                            persist_to=-1, replicate_to=-1)
        self.assertTrue(rv.success)

        # This will fail..
        self.mockclient.unpersist(key,
                                  on_master=True,
                                  replica_count=self.mock.replicas)

        obsres = self.cb.observe(key)
        self.assertRaises(TimeoutError,
                          self.cb.endure,
                          key, persist_to=1, replicate_to=0,
                          timeout=0.1)

        self.mockclient.persist(key, on_master=True, replica_count=0)
        rv = self.cb.endure(key, persist_to=1, replicate_to=0)
        self.assertTrue(rv.success)

        self.assertRaises(TimeoutError,
                          self.cb.endure,
                          key, persist_to=2,
                          replicate_to=0,
                          timeout=0.1)

        rv = self.cb.endure(key, persist_to=0,
                            replicate_to=self.mock.replicas)
        self.assertTrue(rv.success)

########NEW FILE########
__FILENAME__ = excextra_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import couchbase.exceptions as E
from couchbase.tests.base import ConnectionTestCase

# These tests try to see if the 'result' and 'all_results' appear properly
# also verify that other documented exception fields are present

class ConnectionExcExtraTest(ConnectionTestCase):

    def test_simple_excextra(self):
        exc = None
        key = self.gen_key("simple_excextra")
        self.cb.delete(key, quiet=True)

        try:
            self.cb.get(key, quiet=False)
        except E.CouchbaseError as e:
            exc = e

        self.assertTrue(exc)
        self.assertIsInstance(exc, E.CouchbaseError)
        self.assertTrue(exc.message)
        self.assertIsInstance(exc, E.NotFoundError)
        self.assertEqual(exc.key, key)
        self.assertIsInstance(exc.all_results, self.cls_MultiResult)
        self.assertTrue(key in exc.all_results)
        self.assertIsInstance(exc.all_results[key], self.cls_ValueResult)
        self.assertEqual(exc.all_results[key].rc, exc.rc)

        str(exc)
        repr(exc)
        del exc

    def test_multi_exc(self):
        kv_missing = self.gen_kv_dict(prefix="multi_exc_missing")
        kv_existing = self.gen_kv_dict(prefix="multi_exc_existing")
        self.cb.set_multi(kv_existing)
        exc = None
        try:
            self.cb.get_multi(list(kv_missing.keys()) + list(kv_existing.keys()),
                        quiet=False)
        except E.CouchbaseError as e:
            exc = e

        self.assertTrue(exc)
        self.assertIsInstance(exc, E.NotFoundError)
        self.assertEqual(len(exc.all_results),
                         len(kv_missing) + len(kv_existing))

        all_results = exc.all_results
        for k, v in kv_missing.items():
            self.assertTrue(k in all_results)
            self.assertFalse(all_results[k].success)

        for k, v in kv_existing.items():
            self.assertTrue(k in all_results)
            self.assertTrue(all_results[k].success)
            self.assertTrue(all_results[k].value)
            self.assertEqual(v, all_results[k].value)

        str(exc)
        repr(exc)
        del exc

########NEW FILE########
__FILENAME__ = format_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json
import pickle

from couchbase.tests.base import ConnectionTestCase, SkipTest
from couchbase.exceptions import ValueFormatError, ArgumentError
from couchbase import FMT_AUTO, FMT_JSON, FMT_BYTES, FMT_UTF8, FMT_PICKLE

class ConnectionFormatTest(ConnectionTestCase):

    def test_set_autoformat(self):
        key = self.gen_key("set_autoformat")
        jvals = (None, True, False, {}, [], tuple() )
        bvals = (b"\x01", bytearray([1,2,3]))
        uvals = (b"\x42".decode('utf-8'), b'\xea\x80\x80'.decode("utf-8"))
        pvals = (set([]), object())

        for jv in jvals:
            self.cb.set(key, jv, format=FMT_AUTO)
            rv = self.cb.get(key, no_format=True)
            self.assertEqual(rv.flags, FMT_JSON)
            # We need 'decode' because Python3's byte type
            self.assertEqual(rv.value.decode("utf-8"), json.dumps(jv))

        for bv in bvals:
            self.cb.set(key, bv, format=FMT_AUTO)
            rv = self.cb.get(key, no_format=True)
            self.assertEqual(rv.flags, FMT_BYTES)
            self.assertEqual(rv.value, bv)

        for uv in uvals:
            self.cb.set(key, uv, format=FMT_AUTO)
            rv = self.cb.get(key, no_format=True)
            self.assertEqual(rv.flags, FMT_UTF8)
            self.assertEqual(rv.value, uv.encode("utf-8"))

        for pv in pvals:
            self.cb.set(key, pv, format=FMT_AUTO)
            rv = self.cb.get(key, no_format=True)
            self.assertEqual(rv.flags, FMT_PICKLE)
            self.assertEqual(rv.value, pickle.dumps(pv))

    def test_set_format(self):
        key = self.gen_key('set_format')
        rv1 = self.cb.set(key, {'some': 'value1'}, format=FMT_JSON)
        self.assertTrue(rv1.cas > 0)

        self.assertRaises(ValueFormatError, self.cb.set,
                          key, object(), format=FMT_JSON)

        rv3 = self.cb.set(key, {'some': 'value3'},
                           format=FMT_PICKLE)
        self.assertTrue(rv3.cas > 0)
        rv4 = self.cb.set(key, object(), format=FMT_PICKLE)
        self.assertTrue(rv4.cas > 0)

        self.assertRaises(ValueFormatError, self.cb.set,
                          key, {'some': 'value5'},
                          format=FMT_BYTES)
        self.assertRaises(ValueFormatError, self.cb.set,
                          key, { 'some' : 'value5.1'},
                          format=FMT_UTF8)

        rv6 = self.cb.set(key, b'some value6', format=FMT_BYTES)
        self.assertTrue(rv6.cas > 0)

        rv7 = self.cb.set(key, b"\x42".decode('utf-8'),
                          format=FMT_UTF8)
        self.assertTrue(rv7.success)


    def test_get_noformat(self):
        k = self.gen_key("get_noformat")
        self.cb.set(k, {"foo":"bar"}, format=FMT_JSON)
        rv = self.cb.get(k, no_format=True)
        self.assertEqual(rv.value, b'{"foo":"bar"}')

        kl = self.gen_key_list(prefix="get_noformat")
        kv = {}
        for k in kl:
            kv[k] = {"foo" : "bar"}

        self.cb.set_multi(kv)
        rvs = self.cb.get_multi(kv.keys(), no_format=True)
        for k, v in rvs.items():
            self.assertEqual(v.value, b'{"foo":"bar"}')


    def test_get_format(self):

        raise(SkipTest("get-with-format not implemented"))

        self.cb.set('key_format1', {'some': 'value1'}, format=FMT_JSON)
        val1 = self.cb.get('key_format1')
        self.assertEqual(val1, {'some': 'value1'})

        self.cb.set('key_format2', {'some': 'value2'}, format=FMT_PICKLE)
        val2 = self.cb.get('key_format2')
        self.assertEqual(val2, {'some': 'value2'})

        self.cb.set('key_format3', b'some value3', format=FMT_BYTES)
        val3 = self.cb.get('key_format3')
        self.assertEqual(val3, b'some value3')


        self.cb.set('key_format4', {'some': 'value4'}, format=FMT_JSON)
        val4 = self.cb.get('key_format4', format=FMT_BYTES)
        self.assertEqual(val4, b'{"some": "value4"}')

        self.cb.set('key_format5', {'some': 'value5'}, format=FMT_PICKLE)
        val5 = self.cb.get('key_format5', format=FMT_BYTES)
        self.assertEqual(pickle.loads(val5), {'some': 'value5'})


        self.cb.set('key_format6', {'some': 'value6'}, format=FMT_JSON)
        self.assertRaises(ValueFormatError, self.cb.get, 'key_format6',
                          format=FMT_PICKLE)

        self.cb.set('key_format7', {'some': 'value7'}, format=FMT_PICKLE)
        self.assertRaises(ValueFormatError, self.cb.get, 'key_format7',
                          format=FMT_JSON)

########NEW FILE########
__FILENAME__ = get_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import pickle
from time import sleep

from nose.plugins.attrib import attr

from couchbase import FMT_JSON, FMT_PICKLE, FMT_UTF8, FMT_BYTES

from couchbase.exceptions import (
    CouchbaseError, ValueFormatError, NotFoundError)
from couchbase.result import MultiResult, Result
from couchbase.tests.base import ConnectionTestCase, SkipTest

class ConnectionGetTest(ConnectionTestCase):

    def test_trivial_get(self):
        key = self.gen_key('trivial_get')
        self.cb.set(key, 'value1')
        rv = self.cb.get(key)
        self.assertEqual(rv.value, 'value1')

        rvs = self.cb.get_multi([key])
        self.assertIsInstance(rvs, self.cls_MultiResult)
        self.assertEqual(len(rvs), 1)
        self.assertEqual(rvs[key].value, 'value1')


    def test_get_missing_key(self):
        rv = self.cb.get('key_missing_1', quiet=True)
        self.assertIsNone(rv.value)
        self.assertFalse(rv.success)

        # Get with quiet=False
        self.assertRaises(NotFoundError, self.cb.get, 'key_missing_1',
                          quiet=False)

    def test_multi_get(self):
        kv = self.gen_kv_dict(amount=3, prefix='get_multi')
        rvs = self.cb.set_multi(kv)
        self.assertTrue(rvs.all_ok)

        k_subset = list(kv.keys())[:2]

        rvs1 = self.cb.get_multi(k_subset)
        self.assertEqual(len(rvs1), 2)
        self.assertEqual(rvs1[k_subset[0]].value, kv[k_subset[0]])
        self.assertEqual(rvs1[k_subset[1]].value, kv[k_subset[1]])

        rv2 = self.cb.get_multi(kv.keys())
        self.assertEqual(rv2.keys(), kv.keys())


    def test_multi_mixed(self):
        kv_missing = self.gen_kv_dict(amount=3, prefix='multi_missing_mixed')
        kv_existing = self.gen_kv_dict(amount=3, prefix='multi_existing_mixed')

        self.cb.delete_multi(list(kv_missing.keys()) + list(kv_existing.keys()),
                             quiet=True)

        self.cb.set_multi(kv_existing)

        rvs = self.cb.get_multi(
            list(kv_existing.keys()) + list(kv_missing.keys()),
            quiet=True)


        self.assertFalse(rvs.all_ok)

        for k, v in kv_missing.items():
            self.assertTrue(k in rvs)
            self.assertFalse(rvs[k].success)
            self.assertTrue(rvs[k].value is None)
            self.assertTrue(NotFoundError._can_derive(rvs[k].rc))

        for k, v in kv_existing.items():
            self.assertTrue(k in rvs)
            self.assertTrue(rvs[k].success)
            self.assertEqual(rvs[k].value, kv_existing[k])
            self.assertEqual(rvs[k].rc, 0)

        # Try this again, but without quiet
        cb_exc = None
        try:
            self.cb.get_multi(list(kv_existing.keys()) + list(kv_missing.keys()))
        except NotFoundError as e:
            cb_exc = e

        self.assertTrue(cb_exc)
        all_res = cb_exc.all_results
        self.assertTrue(all_res)
        self.assertFalse(all_res.all_ok)

        for k, v in kv_existing.items():
            self.assertTrue(k in all_res)
            self.assertTrue(all_res[k].success)
            self.assertEqual(all_res[k].value, v)
            self.assertEqual(all_res[k].rc, 0)

        for k, v in kv_missing.items():
            self.assertTrue(k in all_res)
            self.assertFalse(all_res[k].success)
            self.assertTrue(all_res[k].value is None)

        del cb_exc


    def test_extended_get(self):
        key = self.gen_key(prefix='key_extended')
        orig_cas1 = self.cb.set(key, 'value1').cas
        rv = self.cb.get(key)
        val1, flags1, cas1 = rv.value, rv.flags, rv.cas
        self.assertEqual(val1, 'value1')
        self.assertEqual(flags1, 0x0)
        self.assertEqual(cas1, orig_cas1)

        # Test named tuples
        result1 = self.cb.get(key)
        self.assertEqual(result1.value, 'value1')
        self.assertEqual(result1.flags, 0x0)
        self.assertEqual(result1.cas, orig_cas1)

        # Single get as array
        result2 = self.cb.get_multi([key])
        self.assertIsInstance(result2, self.cls_MultiResult)
        self.assertTrue(key in result2)
        self.assertEqual(result2[key].value, 'value1')
        self.assertEqual(result2[key].flags, 0x0)
        self.assertEqual(result2[key].cas, orig_cas1)

        key2 = self.gen_key('key_extended_2')
        cas2 = self.cb.set(key2, 'value2').cas

        key3 = self.gen_key('key_extended_3')
        cas3 = self.cb.set(key3, 'value3').cas
        results = self.cb.get_multi([key2, key3])

        self.assertEqual(results[key3].value, 'value3')
        self.assertEqual(results[key3].flags, 0x0)
        self.assertEqual(results[key3].cas, cas3)

        rv = self.cb.get('missing_key', quiet=True)
        val4, flags4, cas4 = rv.value, rv.flags, rv.cas
        self.assertEqual(val4, None)
        self.assertEqual(flags1, 0x0)
        self.assertEqual(cas4, 0)

    @attr('slow')
    def test_get_ttl(self):
        key = self.gen_key('get_ttl')
        self.cb.delete(key, quiet=True)
        self.cb.set(key, "a_value")
        rv = self.cb.get(key, ttl=1)
        self.assertEqual(rv.value, "a_value")
        sleep(2)
        rv = self.cb.get(key, quiet=True)
        self.assertFalse(rv.success)
        self.assertTrue(NotFoundError._can_derive(rv.rc))

    @attr('slow')
    def test_get_multi_ttl(self):
        kvs = self.gen_kv_dict(amount=2, prefix='get_multi_ttl')

        self.cb.set_multi(kvs)
        rvs = self.cb.get_multi(list(kvs.keys()), ttl=1)
        for k, v in rvs.items():
            self.assertEqual(v.value, kvs[k])

        sleep(2)
        rvs = self.cb.get_multi(list(kvs.keys()), quiet=True)
        for k, v in rvs.items():
            self.assertFalse(v.success)
            self.assertTrue(k in kvs)
            self.assertTrue(NotFoundError._can_derive(v.rc))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = iops_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.tests.base import CouchbaseTestCase

# For now, this just checks that basic set/get doesn't explode
# We'll definitely want to add more here before we consider it stable

class ConnectionIopsTest(CouchbaseTestCase):
    def setUp(self):
        super(ConnectionIopsTest, self).setUp()
        self.skipIfPyPy()

    def _iops_connection(self, **kwargs):
        ret = self.make_connection(
            experimental_gevent_support=True,
            **kwargs
        )
        return ret

    def test_creation(self):
        self._iops_connection()
        self.assertTrue(True)

    def test_simple_ops(self):
        cb = self._iops_connection()
        key = self.gen_key("iops-simple")
        value = "some_value"
        cb.set(key, value)
        rv = cb.get(key)
        self.assertTrue(rv.success)
        self.assertEqual(rv.value, value)

########NEW FILE########
__FILENAME__ = itemsyntax_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from time import sleep

from couchbase.exceptions import (ValueFormatError,
                                  ArgumentError, NotFoundError)
from couchbase.tests.base import ConnectionTestCase


class ConnectionItemSyntaxTest(ConnectionTestCase):

    def test_simple_accessors(self):
        cb = self.cb
        cb.quiet = True
        k = self.gen_key('__getitem__')

        del cb[k]
        cb[k] = "bar"
        self.assertEqual(cb[k].value, 'bar')

        del cb['blah']


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = itertypes_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.tests.base import ConnectionTestCase
from couchbase.exceptions import ArgumentError, ValueFormatError
from couchbase.user_constants import FMT_UTF8

class ConnectionItertypeTest(ConnectionTestCase):

    def test_itertypes(self):
        kvs = self.gen_kv_dict(amount=10, prefix='itertypes')
        intlist = set(self.gen_key_list(amount=3, prefix='setobject'))

        self.cb.delete_multi(kvs.keys(), quiet=True)
        self.cb.set_multi(kvs)
        self.cb.get_multi(kvs.keys())
        self.cb.get_multi(kvs.values(), quiet=True)

        self.cb.incr_multi(intlist, initial=10)
        self.cb.decr_multi(intlist)
        self.cb.get_multi(intlist)

    def test_bad_elements(self):
        badlist = ("key1", None, "key2")
        for fn in (self.cb.incr_multi,
                   self.cb.delete_multi,
                   self.cb.get_multi):
            self.assertRaises(
                (ArgumentError, ValueFormatError),
                fn, badlist)

        self.assertRaises(
            (ArgumentError, ValueFormatError),
            self.cb.set_multi,
            { None: "value" })

        self.assertRaises(ValueFormatError,
                          self.cb.set_multi,
                          { "Value" : None},
                          format=FMT_UTF8)

    def test_iterclass(self):
        class IterTemp(object):
            def __init__(self, gen_ints = False, badlen=False):
                self.current = 0
                self.max = 5
                self.gen_ints = gen_ints
                self.badlen = badlen

            def __iter__(self):
                while self.current < self.max:
                    ret = self.current
                    if not self.gen_ints:
                        ret = "Key_" + str(ret)
                    self.current += 1
                    yield ret

            def __len__(self):
                if self.badlen:
                    return 100
                return self.max

        self.cb.delete_multi(IterTemp(gen_ints=False), quiet=True)
        self.cb.incr_multi(IterTemp(gen_ints = False), initial=10)
        self.cb.decr_multi(IterTemp(gen_ints = False), initial=10)
        self.cb.get_multi(IterTemp(gen_ints=False))
        self.cb.delete_multi(IterTemp(gen_ints = False))

        # Try with a mismatched len-iter
        self.assertRaises(ArgumentError,
                          self.cb.get_multi,
                          IterTemp(gen_ints=False, badlen=True))

########NEW FILE########
__FILENAME__ = itmops_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.tests.base import ConnectionTestCase
from couchbase.items import Item, ItemSequence, ItemOptionDict
from couchbase.exceptions import (
    NotFoundError, ValueFormatError, ArgumentError, KeyExistsError)
from couchbase.user_constants import FMT_BYTES, FMT_UTF8

class ConnectionItemTest(ConnectionTestCase):
    """
    This class tests the new 'Item' API
    """

    def setUp(self):
        super(ConnectionItemTest, self).setUp()
        self.skipIfPyPy()

    def test_construction(self):
        # Test whether we can construct a simple Item
        it = Item("some_key", "some_value")
        it.cas = 123456
        it.flags = 1000

        self.assertEqual(it.key, "some_key")
        self.assertEqual(it.value, "some_value")
        self.assertEqual(it.cas, 123456)
        self.assertEqual(it.flags, 1000)
        hash(it)

    def test_simple_get(self):
        k = self.gen_key("itm_simple_get")
        it = Item(k, "simple_value")

        rvs = self.cb.set_multi(ItemSequence([it]))
        self.assertTrue(rvs.all_ok)

        it_out = rvs[it.key]
        self.assertEqual(it_out, it)

        it = Item()
        it.key = k
        itcoll = ItemSequence([it])

        rvs = self.cb.get_multi(ItemSequence([it]))
        self.assertTrue(rvs.all_ok)
        it_out = rvs[it.key]
        self.assertEqual(it_out, it)
        self.assertEqual(it_out.value, "simple_value")

        # Now, set it again
        self.cb.replace_multi(itcoll)

        # Now, delete it
        self.cb.delete_multi(itcoll)

        self.assertRaises(NotFoundError,
                          self.cb.get_multi, itcoll)

    def test_item_format(self):
        # Tests whether things like 'CAS' and 'format' are honored
        k = self.gen_key("itm_format_options")
        it = Item(k, {})
        itcoll = ItemOptionDict()
        itcoll.dict[it] = { "format" : FMT_BYTES }
        self.assertRaises(ValueFormatError, self.cb.set_multi, itcoll)

    def test_items_append(self):
        k = self.gen_key("itm_append")
        it = Item(k, "MIDDLE")
        itcoll = ItemOptionDict()
        itcoll.add(it)

        self.cb.set_multi(itcoll, format=FMT_UTF8)

        itcoll.add(it, fragment="_END")
        self.cb.append_items(itcoll, format=FMT_UTF8)
        self.assertEqual(it.value, "MIDDLE_END")

        itcoll.add(it, fragment="BEGIN_")
        self.cb.prepend_items(itcoll, format=FMT_UTF8)
        self.assertEqual(it.value, "BEGIN_MIDDLE_END")

        rv = self.cb.get(it.key)
        self.assertEqual(rv.value, "BEGIN_MIDDLE_END")

        # Try without a 'fragment' specifier
        self.assertRaises(ArgumentError,
                          self.cb.append_items, ItemSequence([it]))
        itcoll.add(it)
        self.assertRaises(ArgumentError,
                          self.cb.append_items, itcoll)

    def test_items_ignorecas(self):
        k = self.gen_key("itm_ignorecas")
        it = Item(k, "a value")
        itcoll = ItemOptionDict()
        itcoll.add(it)
        self.cb.set_multi(itcoll)
        self.assertTrue(it.cas)

        # Set it again
        rv = self.cb.set(it.key, it.value)
        self.assertTrue(rv.cas)
        self.assertFalse(rv.cas == it.cas)

        # Should raise an error without ignore_cas
        self.assertRaises(KeyExistsError, self.cb.set_multi, itcoll)
        self.assertTrue(it.cas)

        itcoll.add(it, ignore_cas=True)
        self.cb.set_multi(itcoll)
        rv = self.cb.get(it.key)
        self.assertEqual(rv.cas, it.cas)

    def test_subclass_descriptors(self):
        class MyItem(Item):
            def __init__(self):
                pass
            @property
            def value(self):
                return "This should not be present!!!"
            @value.setter
            def value(self, other):
                return

        k = self.gen_key("itm_desc")
        it = MyItem()
        it.key = k
        it.value = "hi!"
        self.assertRaises(ArgumentError,
                          self.cb.set_multi,
                          ItemSequence([it]))

    def test_apiwrap(self):
        it = Item(self.gen_key("item_apiwrap"))
        self.cb.set_multi(it.as_itcoll())
        self.assertTrue(it.cas)

        # Set with 'ignorecas'
        it.cas = 1234
        self.cb.set_multi(it.as_itcoll(ignore_cas=True))

        self.cb.set_multi(ItemSequence(it))

########NEW FILE########
__FILENAME__ = lockmode_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from threading import Thread, Lock
import time


from couchbase.exceptions import CouchbaseError, ObjectThreadError
from couchbase.tests.base import CouchbaseTestCase
from couchbase import LOCKMODE_WAIT, LOCKMODE_EXC, LOCKMODE_NONE

class LockmodeTest(CouchbaseTestCase):
    def test_lockmode_defaults(self):
        # default is LOCKMODE_EXC
        key = self.gen_key("lockmode_defaults")
        cb = self.make_connection()
        self.assertEqual(cb.lockmode, LOCKMODE_EXC)
        cb._thr_lockop(0)
        cb._thr_lockop(1)
        cb.set(key, "value")

        cb = self.make_connection(lockmode=LOCKMODE_NONE)
        self.assertEqual(cb.lockmode, LOCKMODE_NONE)

        self.assertRaises(ObjectThreadError,
                          cb._thr_lockop, 1)
        self.assertRaises(ObjectThreadError,
                          cb._thr_lockop, 0)
        cb.set(key, "value")

        cb = self.make_connection(lockmode=LOCKMODE_WAIT)
        self.assertEqual(cb.lockmode, LOCKMODE_WAIT)
        cb._thr_lockop(0)
        cb._thr_lockop(1)
        cb.set(key, "value")

        cb = self.make_connection(lockmode=LOCKMODE_WAIT, unlock_gil=False)
        self.assertEqual(cb.lockmode, LOCKMODE_NONE)
        cb.set(key, "value")

    def test_lockmode_exc(self):
        key = self.gen_key("lockmode_exc")

        cb = self.make_connection()
        cb._thr_lockop(0)
        self.assertRaises(ObjectThreadError,
                          cb.set,
                          key, "bar")
        cb._thr_lockop(1)

        # Ensure the old value is not buffered
        cb.set(key, "baz")
        self.assertEqual(cb.get(key).value, "baz")

    def test_lockmode_wait(self):
        key = self.gen_key("lockmode_wait")
        cb = self.make_connection(lockmode=LOCKMODE_WAIT, unlock_gil=True)

        d = {
            'ended' : 0
        }

        def runfunc():
            cb.set(key, "value")
            d['ended'] = time.time()

        cb._thr_lockop(0)
        t = Thread(target=runfunc)
        t.start()

        time.sleep(0.5)
        time_unlocked = time.time()
        cb._thr_lockop(1)

        t.join()
        self.assertTrue(d['ended'] >= time_unlocked)

########NEW FILE########
__FILENAME__ = lock_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from time import sleep

from nose.plugins.attrib import attr

from couchbase.exceptions import (
    CouchbaseError, TemporaryFailError, KeyExistsError, ArgumentError)

from couchbase.tests.base import ConnectionTestCase


class ConnectionLockTest(ConnectionTestCase):

    def test_simple_lock(self):
        k = self.gen_key('lock')
        v = "locked_value"
        self.cb.set(k, v)
        rv = self.cb.lock(k, ttl=5)

        self.assertTrue(rv.success)
        self.assertEqual(rv.value, v)
        self.assertRaises(KeyExistsError, self.cb.set, k, v)

        self.assertRaises(TemporaryFailError, self.cb.lock, k, ttl=5)

        # Test set-while-locked
        self.assertRaises(KeyExistsError, self.cb.set, k, v)

        self.assertRaises(TemporaryFailError, self.cb.unlock, k, cas=0xdeadbeef)

        rv = self.cb.unlock(k, rv.cas)
        self.assertTrue(rv.success)

        # Unlocked with key already unlocked
        self.assertRaises(TemporaryFailError,
                          self.cb.unlock,
                          k,
                          1234)

        rv = self.cb.set(k, v)
        self.assertTrue(rv.success)

    @attr('slow')
    def test_timed_lock(self):
        k = self.gen_key('lock')
        v = "locked_value"
        self.cb.set(k, v)
        rv = self.cb.lock(k, ttl=1)
        sleep(2)
        self.cb.set(k, v)

    def test_multi_lock(self):
        kvs = self.gen_kv_dict(prefix='lock_multi')

        self.cb.set_multi(kvs)
        rvs = self.cb.lock_multi(kvs.keys(), ttl=5)
        self.assertTrue(rvs.all_ok)
        self.assertEqual(len(rvs), len(kvs))
        for k, v in rvs.items():
            self.assertEqual(v.value, kvs[k])

        rvs = self.cb.unlock_multi(rvs)

    def test_unlock_multi(self):
        key = self.gen_key(prefix='unlock_multi')
        val = "lock_value"
        self.cb.set(key, val)

        rv = self.cb.lock(key, ttl=5)
        rvs = self.cb.unlock_multi({key:rv.cas})
        self.assertTrue(rvs.all_ok)
        self.assertTrue(rvs[key].success)

        rv = self.cb.lock(key, ttl=5)
        self.assertTrue(rv.success)
        rvs = self.cb.unlock_multi({key:rv})
        self.assertTrue(rvs.all_ok)
        self.assertTrue(rvs[key].success)

    def test_missing_expiry(self):
        self.assertRaises(ArgumentError,
                          self.cb.lock, "foo")
        self.assertRaises(ArgumentError, self.cb.lock_multi,
                          ("foo", "bar"))

    def test_missing_cas(self):
        self.assertRaises(ArgumentError,
                          self.cb.unlock_multi,
                          ("foo", "bar"))
        self.assertRaises(ArgumentError,
                          self.cb.unlock_multi,
                          {"foo":0, "bar":0})

    def test_resobjs(self):
        keys = self.gen_kv_dict(prefix="Lock_test_resobjs")
        self.cb.set_multi(keys)
        rvs = self.cb.lock_multi(keys.keys(), ttl=5)
        self.cb.unlock_multi(rvs)

        kv_single = list(keys.keys())[0]

        rv = self.cb.lock(kv_single, ttl=5)
        self.assertTrue(rv.cas)

        self.cb.unlock_multi([rv])

########NEW FILE########
__FILENAME__ = misc_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.tests.base import ConnectionTestCase
from couchbase.user_constants import FMT_JSON, FMT_AUTO, FMT_JSON, FMT_PICKLE
from couchbase.exceptions import ClientTemporaryFailError
from couchbase import Couchbase
from couchbase.exceptions import CouchbaseError

class ConnectionMiscTest(ConnectionTestCase):

    def test_server_nodes(self):
        nodes = self.cb.server_nodes
        self.assertIsInstance(nodes, (list, tuple))
        self.assertTrue(len(nodes) > 0)
        for n in nodes:
            self.assertIsInstance(n, str)

        def _set_nodes():
            self.cb.server_nodes = 'sdf'
        self.assertRaises((AttributeError, TypeError), _set_nodes)

    def test_lcb_version(self):
        verstr, vernum = self.factory.lcb_version()
        self.assertIsInstance(verstr, str)
        self.assertIsInstance(vernum, int)

    def test_bucket(self):
        bucket_str = self.cb.bucket
        self.assertEqual(bucket_str, self.make_connargs()['bucket'])

    def test_conn_repr(self):
        repr(self.cb)


    def test_connection_defaults(self):
        # This will only work on the basic Connection class
        from couchbase.connection import Connection
        ctor_params = self.make_connargs()
        # XXX: Change these if any of the defaults change
        defaults = {
            'timeout' : 2.5,
            'quiet' : False,
            'default_format' : FMT_JSON,
            'unlock_gil' : True,
            'transcoder' : None
        }

        cb_ctor = Connection(**ctor_params)
        cb_connect = Couchbase.connect(**ctor_params)

        for option, value in defaults.items():
            actual = getattr(cb_ctor, option)
            self.assertEqual(actual, value)

            actual = getattr(cb_connect, option)
            self.assertEqual(actual, value)

    def test_closed(self):
        cb = self.cb
        self.assertFalse(cb.closed)
        cb._close()
        self.assertTrue(cb.closed)
        self.assertRaises(ClientTemporaryFailError, self.cb.get, "foo")


    def test_fmt_args(self):
        # Regression
        cb = self.make_connection(default_format=123)
        self.assertEqual(cb.default_format, 123)

        key = self.gen_key("fmt_auto_ctor")
        cb = self.make_connection(default_format = FMT_AUTO)
        cb.set("foo", set([]))
        rv = cb.get("foo")
        self.assertEqual(rv.flags, FMT_PICKLE)


    def test_cntl(self):
        cb = self.make_connection()
        # Get the timeout
        rv = cb._cntl(0x01)
        self.assertEqual(75000000, rv)

        cb._cntl(0x01, rv)
        # Doesn't crash? good enough

        # Try with something invalid
        self.assertRaises(CouchbaseError, cb._cntl, 0xf000)
        self.assertRaises(CouchbaseError, cb._cntl, 0x01, "string")

    def test_vbmap(self):
        # We don't know what the vbucket map is supposed to be, so just
        # check it doesn't fail
        cb = self.make_connection()
        vb, ix = cb._vbmap("hello")
        int(vb)
        int(ix)

########NEW FILE########
__FILENAME__ = observe_t
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.tests.base import ConnectionTestCase, MockTestCase
from couchbase.result import ObserveInfo
from couchbase.user_constants import OBS_MASK, OBS_FOUND, OBS_PERSISTED

class ConnectionObserveTest(ConnectionTestCase):

    def test_single_observe(self):
        key = self.gen_key("test_single_observe")
        self.cb.set(key, "value")
        rv = self.cb.observe(key)
        grv = self.cb.get(key)
        print(rv)

        self.assertTrue(rv.success)
        self.assertIsInstance(rv.value, list)
        self.assertTrue(rv.value)

        found_master = False


        for oi in rv.value:
            self.assertIsInstance(oi, self.cls_ObserveInfo)
            oi.cas
            oi.from_master
            self.assertEqual(oi.flags, oi.flags & OBS_MASK)

            if oi.from_master:
                found_master = True
                self.assertTrue(oi.flags & (OBS_FOUND) == OBS_FOUND)
                self.assertEqual(oi.cas, grv.cas)

        self.assertTrue(found_master)
        repr(oi)
        str(oi)

    def test_multi_observe(self):
        kexist = self.gen_key("test_multi_observe-exist")
        kmissing = self.gen_key("test_multi_observe-missing")
        self.cb.set(kexist, "value")
        self.cb.delete(kmissing, quiet=True)
        grv = self.cb.get(kexist)

        mres = self.cb.observe_multi((kexist, kmissing))
        self.assertTrue(mres.all_ok)
        self.assertEqual(len(mres), 2)

        v_exist = mres[kexist]
        v_missing = mres[kmissing]

        for v in (v_exist.value, v_missing.value):
            self.assertIsInstance(v, list)
            self.assertTrue(len(v))
            found_master = False

            for oi in v:
                self.assertIsInstance(oi, self.cls_ObserveInfo)
                oi.flags
                oi.cas
                if oi.from_master:
                    found_master = True


class ConnectionObserveMasterTest(MockTestCase):
    def test_master_observe(self):
        self.skipLcbMin("2.3.0")
        key = self.gen_key("test_master_observe")
        rv = self.cb.set(key, "value")
        obs_all = self.cb.observe(key)
        self.assertTrue(len(obs_all.value) > 1)
        obs_master = self.cb.observe(key, master_only=True)
        self.assertEqual(len(obs_master.value), 1)
        obs_val = obs_master.value[0]
        self.assertTrue(obs_val.from_master)
        self.assertEqual(obs_val.cas, rv.cas)

########NEW FILE########
__FILENAME__ = pipeline_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.exceptions import PipelineError, NotFoundError, ArgumentError
from couchbase.tests.base import ConnectionTestCase
from couchbase import FMT_UTF8

class ConnectionPipelineTest(ConnectionTestCase):

    def test_simple_pipeline(self):
        k = self.gen_key("pipeline_test")
        with self.cb.pipeline():
            self.cb.delete(k, quiet=True)
            self.cb.add(k, "MIDDLE", format=FMT_UTF8)
            self.cb.prepend(k, "BEGIN_")
            self.cb.append(k, "_END")

        # No errors
        rv = self.cb.get(k)
        self.assertEqual(rv.value, "BEGIN_MIDDLE_END")

    def test_empty_pipeline(self):
        k = self.gen_key("empty_pipeline")

        with self.cb.pipeline():
            pass

        self.cb.set(k, "a value")
        rv = self.cb.get(k)
        self.assertEqual(rv.value, "a value")

    def test_pipeline_results(self):
        k = self.gen_key("pipeline_results")
        pipeline = self.cb.pipeline()
        with pipeline:
            self.cb.delete(k, quiet=True)
            self.cb.set(k, "blah")
            self.cb.get(k)
            self.cb.delete(k)

        results = pipeline.results
        self.assertEqual(len(results), 4)

        self.assertTrue(results[1].success)
        self.assertEqual(results[1].key, k)

        self.assertTrue(results[2].success)
        self.assertEqual(results[2].key, k)
        self.assertEqual(results[2].value, "blah")

        self.assertTrue(results[3].success)

    def test_pipeline_operrors(self):
        k = self.gen_key("pipeline_errors")
        v = "hahahaha"
        self.cb.delete(k, quiet=True)

        def run_pipeline():
            with self.cb.pipeline():
                self.cb.get(k, quiet=False)
                self.cb.set(k, v)
        self.assertRaises(NotFoundError, run_pipeline)

        rv = self.cb.set("foo", "bar")
        self.assertTrue(rv.success)

    def test_pipeline_state_errors(self):
        def fun():
            with self.cb.pipeline():
                with self.cb.pipeline():
                    pass

        self.assertRaises(PipelineError, fun)

        def fun():
            with self.cb.pipeline():
                list(self.cb.query("design", "view"))

        self.assertRaises(PipelineError, fun)

    def test_pipeline_argerrors(self):
        k = self.gen_key("pipeline_argerrors")
        self.cb.delete(k, quiet=True)

        pipeline = self.cb.pipeline()

        def fun():
            with pipeline:
                self.cb.set(k, "foo")
                self.cb.get("foo", "bar")
                self.cb.get(k)

        self.assertRaises(ArgumentError, fun)
        self.assertEqual(len(pipeline.results), 1)
        self.assertEqual(self.cb.get(k).value, "foo")

    def test_multi_pipeline(self):
        kvs = self.gen_kv_dict(prefix="multi_pipeline")

        pipeline = self.cb.pipeline()
        with pipeline:
            self.cb.set_multi(kvs)
            self.cb.get_multi(kvs.keys())

        self.assertEqual(len(pipeline.results), 2)
        for mres in pipeline.results:
            for k in kvs:
                self.assertTrue(k in mres)
                self.assertTrue(mres[k].success)


        for k, v in pipeline.results[1].items():
            self.assertEqual(v.value, kvs[k])

########NEW FILE########
__FILENAME__ = querystrings_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# These tests are largely ported from php-ext-couchbase
import json

from couchbase.views.params import (make_options_string,
                                    Query,
                                    ulp,
                                    UNSPEC,
                                    _HANDLER_MAP)

from couchbase.exceptions import ArgumentError
from couchbase.tests.base import CouchbaseTestCase

class QueryStringTest(CouchbaseTestCase):
    def setUp(self):
        super(QueryStringTest, self).setUp()

    def _assert_vopteq(self, expected, key, value):
        s = make_options_string({key:value})
        self.assertEqual(s, expected)

    def _assert_vopteq_multi(self, d, key, value):
        q = Query(**{key:value})
        enc = q.encoded
        res = {}
        for kvp in enc.split("&"):
            k, v = kvp.split("=")
            res[k] = v

        d = d.copy()
        for k in d:
            d[k] = ulp.quote(d[k])

        self.assertEqual(res, d)

    def test_stale_params(self):
        self._assert_vopteq('stale=ok', 'stale', True)
        self._assert_vopteq('stale=false', 'stale', False)
        self._assert_vopteq('stale=update_after', "stale", "update_after")
        self._assert_vopteq('stale=ok', 'stale', 1)
        self._assert_vopteq('stale=false', 'stale', 0)
        self._assert_vopteq('stale=false', 'stale', "false")


    def test_bad_stale(self):
        self.assertRaises(ArgumentError,
                          self._assert_vopteq,
                          'stale=blahblah', 'stale', 'blahblha')
        self.assertRaises(ArgumentError,
                          self._assert_vopteq,
                          'stale=None', 'stale', None)


    def test_unrecognized_params(self):
        self.assertRaises(ArgumentError,
                          self._assert_vopteq,
                          'frobble=gobble', 'frobble', 'gobble')

    def test_misc_booleans(self):
        bparams = ('descending',
                   'reduce',
                   'inclusive_end',
                   'full_set',
                   'group')

        for p in bparams:
            # with string "false"
            self._assert_vopteq(p+"=false",
                                p,
                                "false")

            # with string "true"
            self._assert_vopteq(p+"=true",
                                p,
                                "true")

            self.assertRaises(ArgumentError,
                              self._assert_vopteq,
                              p+'=gobble', p, 'gobble')

            self.assertRaises(ArgumentError,
                              self._assert_vopteq,
                              p+'=None', p, None)

    def test_misc_numeric(self):
        nparams = (
            'connection_timeout',
            'group_level',
            'skip')

        for p in nparams:
            self._assert_vopteq(p+'=42',
                                p,
                                42)

            self._assert_vopteq(p+'=42',
                                p,
                                "42")

            self.assertRaises(ArgumentError,
                              self._assert_vopteq,
                              p+'=true', p, True)

            self.assertRaises(ArgumentError,
                              self._assert_vopteq,
                              p+'=blah', p, 'blah')

            self._assert_vopteq(p+'=0', p, 0)
            self._assert_vopteq(p+'=0', p, "0")
            self._assert_vopteq(p+'=-1', p, -1)

    def test_encode_string_to_json(self):
        jparams = (
            'endkey',
            'key',
            'startkey')

        values = (
            'dummy',
            42,
            None,
            True,
            False,
            { "chicken" : "broth" },
            ["noodle", "soup"],
            ["lone element"],
            ("empty tuple",)
        )

        for p in jparams:
            for v in values:
                expected = p + '=' + ulp.quote(json.dumps(v))
                print("Expected", expected)
                self._assert_vopteq(expected, p, v)

            self.assertRaises(ArgumentError,
                              self._assert_vopteq,
                              "blah", p, object())


    def test_encode_to_jarray(self):
        jparams = ('keys',) #add more here
        values = (
            ['foo', 'bar'],
            ['foo'])

        badvalues = (True,
                     False,
                     {"foo":"bar"},
                     1,
                     "string")

        for p in jparams:
            for v in values:

                print(v)
                expected = p + '=' + ulp.quote(json.dumps(v))
                self._assert_vopteq(expected, p, v)

            for v in badvalues:
                self.assertRaises(ArgumentError,
                                  self._assert_vopteq,
                                  "blah", p, v)


    def test_passthrough(self):
        values = (
            "blah",
            -1,
            "-invalid/uri&char")

        for p in _HANDLER_MAP.keys():
            for v in values:
                expected = "{0}={1}".format(p, v)
                got = make_options_string({p:v}, passthrough=True)
                self.assertEqual(expected, got)


        # Ensure we still can't use unrecognized params
        self.assertRaises(ArgumentError,
                          make_options_string,
                          {'foo':'bar'},
                          passthrough=True)


        # ensure we still can't use "stupid" params
        badvals = (object(), None, True, False)
        for bv in badvals:
            self.assertRaises(ArgumentError,
                              make_options_string,
                              {'stale':bv},
                              passthrough=True)


    def test_unrecognized(self):
        keys = ("new_param", "another_param")
        values = ("blah", -1, "-invalid-uri-char^&")
        for p in keys:
            for v in values:
                got = make_options_string({p:v},
                    unrecognized_ok=True)
                expected = "{0}={1}".format(p, v)
                self.assertEqual(expected, got)


        badvals = (object(), True, False, None)
        for bv in badvals:
            self.assertRaises(ArgumentError,
                              make_options_string,
                              {'foo':bv},
                              unrecognized_ok=True)

    def test_string_params(self):
        # This test is mainly to see that 'stupid' things don't make
        # their way through as strings, like booleans and None
        sparams = ('endkey_docid',
                   'startkey_docid')

        goodvals = ("string", -1, "OHAI!", '&&escape_me_nao&&')
        badvals = (True, False, None, object(), [])

        for p in sparams:
            for v in goodvals:
                expected = "{0}={1}".format(p, ulp.quote(str(v)))
                self._assert_vopteq(expected, p, v)

            for v in badvals:
                self.assertRaises(ArgumentError,
                                  make_options_string,
                                  {p:v})


    def test_ranges(self):
        expected = "startkey={0}".format(ulp.quote(json.dumps("foo")))
        self._assert_vopteq(expected, "mapkey_range", ["foo"])
        self._assert_vopteq_multi(
            {'startkey' : json.dumps("foo"),
             'endkey' : json.dumps("bar") },
            "mapkey_range",
            ["foo", "bar"])


        expected = "startkey_docid=bar"
        self._assert_vopteq(expected, "dockey_range", ["bar"])
        self._assert_vopteq_multi(
            {'startkey_docid' : "range_begin",
             'endkey_docid' : "range_end"},
            "dockey_range",
            ["range_begin", "range_end"])

        for p in ('mapkey_range', 'dockey_range'):
            self._assert_vopteq('', p, [])
            self._assert_vopteq('', p, UNSPEC)
            self._assert_vopteq('', p, [UNSPEC,UNSPEC])
            self._assert_vopteq('', p, [UNSPEC])

            self.assertRaises(ArgumentError,
                  self._assert_vopteq,
                  "blah", p, [object()])

            self.assertRaises(ArgumentError,
                              self._assert_vopteq,
                              "blah", p, None)

########NEW FILE########
__FILENAME__ = results_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.tests.base import ConnectionTestCase

INT_TYPES = None
try:
    INT_TYPES = (long, int)
except:
    INT_TYPES = (int,)

class ConnectionResultsTest(ConnectionTestCase):

    def __test_oprsesult(self, rv, check_exact=True, exprc=0):
        # Ensure they can be stringified
        self.assertIsInstance(rv, self.cls_OperationResult)
        self.assertIsInstance(rv, self.cls_Result)

        if check_exact:
            self.assertEqual(rv.__class__, self.cls_OperationResult)

        self.assertIsInstance(rv.cas, INT_TYPES)
        self.assertIsInstance(rv.rc, INT_TYPES)

        self.assertEqual(rv.rc, exprc)
        if exprc == 0:
            self.assertTrue(rv.success)

        self.assertIsInstance(rv.errstr, str)

        self.assertIsInstance(repr(rv), str)
        self.assertIsInstance(str(rv), str)

    def __test_valresult(self, rv, value):
        self.assertEqual(rv.__class__, self.cls_ValueResult)
        self.__test_oprsesult(rv, check_exact=False)

        self.assertEqual(rv.value, value)
        self.assertIsInstance(rv.flags, INT_TYPES)

    def test_results(self):
        # Test OperationResult/ValueResult fields
        key = self.gen_key("opresult")
        rv = self.cb.set(key, "value")
        self.__test_oprsesult(rv)

        rv = self.cb.delete(key)
        self.__test_oprsesult(rv)

        rv = self.cb.set(key, "value")
        self.__test_oprsesult(rv)

        rv = self.cb.lock(key, ttl=10)
        self.__test_valresult(rv, "value")
        rv = self.cb.unlock(key, rv.cas)
        self.__test_oprsesult(rv)
        rv = self.cb.get(key)
        self.__test_valresult(rv, "value")
        rv = self.cb.delete(key)
        self.__test_oprsesult(rv)

        rv = self.cb.incr(key, initial=10)
        self.__test_valresult(rv, 10)
        rv = self.cb.get(key)
        self.__test_valresult(rv, 10)

        rv = self.cb.touch(key)
        self.__test_oprsesult(rv)

    def test_multi_results(self):
        kvs = self.gen_kv_dict(prefix="multi_results")
        rvs = self.cb.set_multi(kvs)
        self.assertIsInstance(rvs, self.cls_MultiResult)
        [ self.__test_oprsesult(x) for x in rvs.values() ]
        repr(rvs)
        str(rvs)

        rvs = self.cb.get_multi(kvs.keys())
        self.assertIsInstance(rvs, self.cls_MultiResult)
        self.assertTrue(rvs.all_ok)

        [ self.__test_valresult(v, kvs[k]) for k, v in rvs.items()]

        rvs = self.cb.delete_multi(kvs.keys())
        [ self.__test_oprsesult(x) for x in rvs.values() ]

########NEW FILE########
__FILENAME__ = rget_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.exceptions import NotFoundError, ArgumentError

from couchbase.tests.base import MockTestCase
from couchbase.mockserver import MockControlClient

class ConnectionReplicaGetTest(MockTestCase):
    def setUp(self):
        super(ConnectionReplicaGetTest, self).setUp()
        self.skipUnlessMock()
        self.skipLcbMin("2.0.7")
        self.mockclient = MockControlClient(self.mock.rest_port)

    def test_get_kw(self):
        key = self.gen_key("get_kw")
        # Set on all replicas
        self.mockclient.cache(key,
                              on_master=False,
                              replica_count=self.mock.replicas,
                              value=99,
                              cas=1234)

        self.assertRaises(NotFoundError,
                          self.cb.get, key)

        rv = self.cb.get(key, replica=True)
        self.assertTrue(rv.success)
        self.assertEqual(rv.value, 99)

    def _check_single_replica(self, ix):
        key = self.gen_key("get_kw_ix")

        # Ensure the key is removed...
        self.mockclient.purge(key,
                              on_master=True,
                              replica_count=self.mock.replicas)

        # Getting it should raise an error
        self.assertRaises(NotFoundError, self.cb.get, key)

        # So should getting it from any replica
        self.assertRaises(NotFoundError, self.cb.rget, key)

        # And so should getting it from a specific index
        for jx in range(self.mock.replicas):
            self.assertRaises(NotFoundError, self.cb.rget, key,
                              replica_index=jx)

        # Store the key on the desired replica
        self.mockclient.cache(key,
                              on_master=False,
                              replicas=[ix],
                              value=ix,
                              cas=12345)

        # Getting it from a replica should ultimately succeed
        self.cb.get(key, replica=True)
        rv = self.cb.rget(key)
        self.assertTrue(rv.success)
        self.assertEqual(rv.value, ix)

        # Getting it from our specified replica should succeed
        rv = self.cb.rget(key, replica_index=ix)
        self.assertTrue(rv.success)
        self.assertEqual(rv.value, ix)

        # Getting it from any other replica should fail
        for jx in range(self.mock.replicas):
            if jx == ix:
                continue

            self.assertRaises(NotFoundError,
                              self.cb.rget,
                              key,
                              replica_index=jx)


    def test_get_ix(self):
        key = self.gen_key("get_kw_ix")
        for ix in range(self.mock.replicas):
            self._check_single_replica(ix)

########NEW FILE########
__FILENAME__ = set_converters_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json
import pickle

from couchbase.tests.base import ConnectionTestCase
import couchbase
import couchbase._libcouchbase as LCB

class ConverertSetTest(ConnectionTestCase):
    def _swap_converters(self, swapfunc, kbase, new_enc, new_dec):
        kencode = kbase + "_encode"
        kdecode = kbase + "_decode"

        old_enc = LCB._get_helper(kencode)
        old_dec = LCB._get_helper(kdecode)

        old = swapfunc(new_enc, new_dec)
        self.assertEqual(old[0], old_enc)
        self.assertEqual(old[1], old_dec)
        return old

    def test_json_conversions(self):
        d = {
            'encode' : 0,
            'decode' : 0
        }

        def _encode(val):
            d['encode'] += 1
            return json.dumps(val)

        def _decode(val):
            d['decode'] += 1
            return json.loads(val)

        old = self._swap_converters(couchbase.set_json_converters,
                                    "json",
                                    _encode,
                                    _decode)

        key = self.gen_key("test_json_conversion")

        self.cb.set(key, ["value"], format=couchbase.FMT_JSON)
        rv = self.cb.get(key)
        self.assertEqual(rv.value, ["value"])
        self.assertEqual(1, d['encode'])
        self.assertEqual(1, d['decode'])

        self._swap_converters(couchbase.set_json_converters,
                              "json",
                              old[0],
                              old[1])

    def test_pickle_conversions(self):
        d = {
            'encode' : 0,
            'decode' : 0
        }

        def _encode(val):
            d['encode'] += 1
            return pickle.dumps(val)

        def _decode(val):
            d['decode'] += 1
            return pickle.loads(val)

        key = self.gen_key("test_pickle_conversions")
        old = self._swap_converters(couchbase.set_pickle_converters,
                                    "pickle",
                                    _encode,
                                    _decode)
        fn = set([1,2,3])
        self.cb.set(key, fn, format=couchbase.FMT_PICKLE)
        rv = self.cb.get(key)
        self.assertEqual(rv.value, fn)
        self.assertEqual(1, d['encode'])
        self.assertEqual(1, d['decode'])

        self._swap_converters(couchbase.set_pickle_converters,
                              "pickle",
                              old[0],
                              old[1])

########NEW FILE########
__FILENAME__ = set_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from time import sleep

from nose.plugins.attrib import attr

from couchbase import FMT_JSON, FMT_PICKLE, FMT_BYTES, FMT_UTF8
from couchbase.exceptions import (KeyExistsError, ValueFormatError,
                                  ArgumentError, NotFoundError,
                                  NotStoredError)
from couchbase.tests.base import ConnectionTestCase


class ConnectionSetTest(ConnectionTestCase):

    def test_trivial_set(self):
        rv = self.cb.set(self.gen_key(), 'value1')
        self.assertTrue(rv)
        self.assertTrue(rv.cas > 0)
        rv = self.cb.set(self.gen_key(), 'value2')
        self.assertTrue(rv.cas > 0)

    def test_set_with_cas(self):
        key = self.gen_key('cas')
        rv1 = self.cb.set(key, 'value1')
        self.assertTrue(rv1.cas > 0)

        self.assertRaises(KeyExistsError, self.cb.set,
                          key, 'value2', cas=rv1.cas+1)

        rv2 = self.cb.set(key, 'value3', cas=rv1.cas)
        self.assertTrue(rv2.cas > 0)
        self.assertNotEqual(rv1.cas, rv2.cas)

        rv3 = self.cb.set(key, 'value4')
        self.assertTrue(rv3.cas > 0)
        self.assertNotEqual(rv3.cas, rv2.cas)
        self.assertNotEqual(rv3.cas, rv1.cas)

    @attr('slow')
    def test_set_with_ttl(self):
        key = self.gen_key('ttl')
        self.cb.set(key, 'value_ttl', ttl=2)
        rv = self.cb.get(key)
        self.assertEqual(rv.value, 'value_ttl')
        # Make sure the key expires
        sleep(3)
        self.assertRaises(NotFoundError, self.cb.get, key)

    def test_set_objects(self):
        key = self.gen_key('set_objects')
        for v in (None, False, True):
            for fmt in (FMT_JSON, FMT_PICKLE):
                rv = self.cb.set(key, v, format=fmt)
                self.assertTrue(rv.success)
                rv = self.cb.get(key)
                self.assertTrue(rv.success)
                self.assertEqual(rv.value, v)

    def test_multi_set(self):
        kv = self.gen_kv_dict(prefix='set_multi')
        rvs = self.cb.set_multi(kv)
        self.assertTrue(rvs.all_ok)
        for k, v in rvs.items():
            self.assertTrue(v.success)
            self.assertTrue(v.cas > 0)

        for k, v in rvs.items():
            self.assertTrue(k in rvs)
            self.assertTrue(rvs[k].success)

        self.assertRaises((ArgumentError,TypeError), self.cb.set_multi, kv,
                          cas = 123)

    def test_add(self):
        key = self.gen_key('add')
        self.cb.delete(key, quiet=True)
        rv = self.cb.add(key, "value")
        self.assertTrue(rv.cas)

        self.assertRaises(KeyExistsError,
                          self.cb.add, key, "value")

    def test_replace(self):
        key = self.gen_key('replace')
        rv = self.cb.set(key, "value")
        self.assertTrue(rv.success)

        rv = self.cb.replace(key, "value")
        self.assertTrue(rv.cas)

        rv = self.cb.replace(key, "value", cas=rv.cas)
        self.assertTrue(rv.cas)

        self.assertRaises(KeyExistsError,
                          self.cb.replace, key, "value", cas=0xdeadbeef)

        self.cb.delete(key, quiet=True)
        self.assertRaises(NotFoundError,
                          self.cb.replace, key, "value")


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = stats_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.tests.base import ConnectionTestCase, RealServerTestCase


# For Python 2/3 compatibility
try:
    basestring
except NameError:
    basestring = str


class ConnectionStatsTest(ConnectionTestCase):

    def test_trivial_stats_without_argument(self):
        stats = self.cb.stats()
        self.assertIsInstance(stats, dict)
        self.assertTrue('curr_connections' in stats)
        val = list(stats['curr_connections'].values())[0]
        self.assertIsInstance(val, (float,int))
        key, info = list(stats.items())[0]
        self.assertIsInstance(key, basestring)
        self.assertIsInstance(info, dict)


class ConnectionStatsDetailTest(RealServerTestCase):
    def test_stats_with_argument(self):
        stats = self.cb.stats('memory')
        self.assertIsInstance(stats, dict)
        self.assertTrue('mem_used' in stats)
        self.assertFalse('ep_tap_count' in stats)
        key, info = list(stats.items())[0]
        self.assertIsInstance(key, basestring)
        self.assertIsInstance(info, dict)

    def test_stats_with_argument_list(self):
        stats = self.cb.stats(['memory', 'tap'])
        self.assertIsInstance(stats, dict)
        self.assertTrue('mem_used' in stats)
        self.assertTrue('ep_tap_count' in stats)
        key, info = list(stats.items())[0]
        self.assertIsInstance(key, basestring)
        self.assertIsInstance(info, dict)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = touch_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import time

from nose.plugins.attrib import attr

from couchbase.tests.base import ConnectionTestCase
import couchbase.exceptions as E


@attr('slow')
class ConnectionTouchTest(ConnectionTestCase):
    def setUp(self):
        super(ConnectionTouchTest, self).setUp()
        self.cb = self.make_connection()

    def test_trivial_touch(self):
        key = self.gen_key("trivial_touch")
        self.cb.set(key, "value", ttl=1)
        rv = self.cb.touch(key, ttl=0)
        self.assertTrue(rv.success)
        time.sleep(2)
        rv = self.cb.get(key)
        self.assertTrue(rv.success)
        self.assertEqual(rv.value, "value")

        self.cb.touch(key, ttl=1)
        time.sleep(2)
        rv = self.cb.get(key, quiet=True)
        self.assertFalse(rv.success)
        self.assertTrue(E.NotFoundError._can_derive(rv.rc))

    def test_trivial_multi_touch(self):
        kv = self.gen_kv_dict(prefix="trivial_multi_touch")
        self.cb.set_multi(kv, ttl=1)
        time.sleep(2)
        rvs = self.cb.get_multi(kv.keys(), quiet=True)
        self.assertFalse(rvs.all_ok)

        self.cb.set_multi(kv, ttl=1)
        self.cb.touch_multi(kv.keys(), ttl=0)
        rvs = self.cb.get_multi(kv.keys())
        self.assertTrue(rvs.all_ok)

        self.cb.touch_multi(kv.keys(), ttl=1)
        time.sleep(2)
        rvs = self.cb.get_multi(kv.keys(), quiet=True)
        self.assertFalse(rvs.all_ok)

    def test_dict_touch_multi(self):
        k_missing = self.gen_key("dict_touch_multi_missing")
        k_existing = self.gen_key("dict_touch_multi_existing")

        self.cb.set_multi(
            {k_missing : "missing_val", k_existing : "existing_val"})

        self.cb.touch_multi({k_missing : 1, k_existing : 3})
        time.sleep(2)
        rvs = self.cb.get_multi([k_missing, k_existing], quiet=True)
        self.assertTrue(rvs[k_existing].success)
        self.assertFalse(rvs[k_missing].success)
        time.sleep(2)
        rv = self.cb.get(k_existing, quiet=True)
        self.assertFalse(rv.success)

########NEW FILE########
__FILENAME__ = transcoder_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from couchbase.tests.base import ConnectionTestCase
from couchbase.transcoder import TranscoderPP
from couchbase import Couchbase, FMT_UTF8
from couchbase.connection import Connection
import couchbase.exceptions as E

# This won't test every single permutation of the transcoder, but will check
# mainly to see if error messages are appropriate and how the application handles
# a misbehaving transcoder. The Transcoder API is fairly simple.. so

def gen_func(fname):
    def fn(self, *args):
        if fname in self._op_next:
            val = self._op_next[fname]
            if hasattr(val, '__call__'):
                return val()
            return self._op_next[fname]

        return getattr(self._tc, fname)(*args)
    return fn

class MangledTranscoder(object):
    """
    This is a custom transcoder class where we can optionally set a 'next_value'
    field for a specific operation. If this field is empty, then the default
    method is used
    """
    def __init__(self):
        self._tc = TranscoderPP()
        self._op_next = {}

    def set_all(self, val):
        for n in ('encode_key', 'encode_value', 'decode_key', 'decode_value'):
            self._op_next[n] = val

    def set_next(self, ftype, val):
        self._op_next[ftype] = val

    decode_key = gen_func('decode_key')
    encode_key = gen_func('encode_key')
    decode_value = gen_func('decode_value')
    encode_value = gen_func('encode_value')

class ConnectionTranscoderTest(ConnectionTestCase):

    def test_simple_transcoder(self):
        tc = TranscoderPP()
        self.cb.transcoder = tc

        key = self.gen_key("simple_transcoder")
        obj_values = ({}, [], -1, None, False, True)
        for curval in obj_values:
            self.cb.set(key, curval)
            ret = self.cb.get(key)
            self.assertEqual(ret.value, curval)


    # Try to test some bad transcoders:

    def test_empty_transcoder(self):
        for v in (None, False, 0):
            self.cb.transcoder = v
            self.cb.set("foo", "bar")

    def test_bad_transcoder(self):
        self.cb.transcoder = None

        key = self.gen_key("bad_transcoder")
        self.cb.set(key, "value")

        self.cb.transcoder = object()
        self.assertRaises(E.ValueFormatError, self.cb.set, key, "bar")
        self.assertRaises(E.ValueFormatError, self.cb.get, key)


        mangled = MangledTranscoder()
        # Ensure we actually work
        self.cb.transcoder = mangled
        self.cb.set(key, "value")
        self.cb.get(key)


        for badret in (None, (), [], ""):
            mangled.set_all(badret)
            self.assertRaises(E.ValueFormatError, self.cb.set, key, "value")
            self.assertRaises(E.ValueFormatError, self.cb.get, key)

        mangled._op_next.clear()
        # Try with only bad keys:
        mangled._op_next['encode_key'] = None
        self.assertRaises(E.ValueFormatError, self.cb.set, key, "value")


    def test_transcoder_bad_encvals(self):
        mangled = MangledTranscoder()
        self.cb.transcoder = mangled

        key = self.gen_key("transcoder_bad_encvals")

        # Various tests for 'bad_value':
        encrets = (

            # None
            None,

            # Valid string, but not inside tuple
            b"string",

            # Tuple, but invalid contents
            (None, None),

            # Tuple, valid string, but invalid size (no length)
            (b"valid string"),

            # Tuple, valid flags but invalid string
            (None, 0xf00),

            # Valid tuple, but flags are too big
            (b"string", 2**40),

            # Tuple, but bad leading string
            ([], 42)
        )

        for encret in encrets:
            print(encret)
            mangled._op_next['encode_value'] = encret
            self.assertRaises(E.ValueFormatError, self.cb.set, key, "value")

    def test_transcoder_kdec_err(self):
        key = self.gen_key("transcoder_kenc_err")
        mangled = MangledTranscoder()
        self.cb.transcoder = mangled
        key = self.gen_key('kdec_err')
        self.cb.set(key, 'blah', format=FMT_UTF8)
        def exthrow():
            raise UnicodeDecodeError()

        mangled.set_next('decode_value', exthrow)
        self.assertRaises(E.ValueFormatError, self.cb.get, key)



    def test_transcoder_anyobject(self):
        # This tests the versatility of the transcoder object
        key = self.gen_key("transcoder_anyobject")
        mangled = MangledTranscoder()
        self.cb.transcoder = mangled

        mangled._op_next['encode_key'] = key.encode("utf-8")
        mangled._op_next['encode_value'] = (b"simple_value", 10)

        objs = (object(), None, MangledTranscoder(), True, False)
        for o in objs:
            mangled._op_next['decode_key'] = o
            mangled._op_next['decode_value'] = o
            self.cb.set(o, o, format=o)
            rv = self.cb.get(o)
            self.assertEqual(rv.value, o)


    def test_transcoder_unhashable_keys(self):
        key = self.gen_key("transcoder_unhashable_keys")
        mangled = MangledTranscoder()
        mangled._op_next['encode_key'] = key.encode("utf-8")
        mangled._op_next['encode_value'] = (b"simple_value", 10)
        self.cb.transcoder = mangled

        # As MultiResult objects must be able to store its keys in a dictionary
        # we cannot allow unhashable types. These are such examples
        unhashable = ({}, [], set())
        for o in unhashable:
            mangled._op_next['decode_key'] = o
            mangled._op_next['decode_value'] = o
            self.assertRaises(E.ValueFormatError, self.cb.set, o, o)
            self.assertRaises(E.ValueFormatError, self.cb.get, o, quiet=True)

    def test_transcoder_class(self):
        # Test whether we can pass a class for a transcoder
        key = self.gen_key("transcoder_class")
        c = Connection(**self.make_connargs(transcoder=TranscoderPP))
        c.set(key, "value")

        c = Couchbase.connect(**self.make_connargs(transcoder=TranscoderPP))
        c.set(key, "value")

########NEW FILE########
__FILENAME__ = view_iterator_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase.tests.base import ViewTestCase, SkipTest
from couchbase.views.iterator import (
    View, ViewRow, RowProcessor, AlreadyQueriedError, MAX_URI_LENGTH)

from couchbase.views.params import Query, UNSPEC
from couchbase.exceptions import CouchbaseError
from couchbase.result import Result
from couchbase.exceptions import ArgumentError, CouchbaseError, HTTPError
from couchbase._pyport import xrange


# We'll be using the beer-sample database as it has a sufficiently large
# dataset with well-defined return values

class Brewery(object):
    __ALL_BREWERIES = {}
    __BY_ID = {}

    def __init__(self, id, doc):
        self._id = id
        self.name = doc['name']
        self.city = doc['city']
        self.code = doc['code']
        self.country = doc['country']
        self.phone = doc['phone']
        self.website = doc['website']
        self.type = doc['type']
        self.updated = doc['updated']
        self.description = doc['description']
        self.address = doc['address']

        self.__ALL_BREWERIES[self.name] = self
        self.__BY_ID[self._id] = self

    @classmethod
    def get_brewery(cls, name):
        return cls.__ALL_BREWERIES.get(name)

    @classmethod
    def by_id(cls, name):
        return cls.__BY_ID.get(name)

class Beer(object):
    __ALL_BEERS = {}
    __BY_ID = {}

    @classmethod
    def get_beer(cls, name):
        return cls.__ALL_BEERS.get(name)

    @classmethod
    def by_id(cls, name):
        return cls.__BY_ID.get(name)

    def __init__(self, id, doc):
        self._id = id
        self.name = doc['name']
        self.brewery = Brewery.by_id(doc['brewery_id'])
        self.abv = doc['abv']
        self.updated = doc['updated']
        self.description = doc['description']
        self.category = doc['category']
        self.style = doc['style']

        self.__ALL_BEERS[self.name] = self
        self.__BY_ID[self._id] = self


class BreweryBeerRowProcessor(object):
    """
    This specialized processor will attempt to fetch the name of the beers
    and breweries which it gets, trying to ensure maximum efficiency.

    This only returns beers, skipping over any breweries.
    """
    def __init__(self):
        # Iterates over names of beers. We get them via 'get_beer'.
        self._riter = None


    def handle_rows(self, rows, connection, include_docs):
        """
        This shows an example of an efficient 'include_docs' algorithm
        which fetches the beers and relevant breweries in a single sweep,
        skipping over those that are already cached locally.
        """

        breweries_to_fetch = set()
        beers_to_fetch = set()

        # The order of the keys returned in the result set.
        retkeys = []

        for r in rows:
            if len(r['key']) == 1:
                # It's a brewery
                continue

            brewery_id, beer_id = r['key']
            retkeys.append(beer_id)

            if not Brewery.by_id(brewery_id):
                breweries_to_fetch.add(brewery_id)


            if not Beer.by_id(beer_id):
                beers_to_fetch.add(beer_id)

        self._riter = iter(retkeys)


        if beers_to_fetch or breweries_to_fetch:
            if not include_docs:
                raise ValueError(
                    "Don't have all documents, but include_docs was set to False")

            keys_to_fetch = list(breweries_to_fetch) + list(beers_to_fetch)
            docs = connection.get_multi(keys_to_fetch)

            for brewery in breweries_to_fetch:
                b = Brewery(brewery, docs[brewery].value)

            for beer in beers_to_fetch:
                b = Beer(beer, docs[beer].value)

        return iter(self)

    def __iter__(self):
        if not self._riter:
            return

        for b in self._riter:
            beer = Beer.by_id(b)
            assert beer, "Eh?"

            yield beer

        self._riter = None


class ViewIteratorTest(ViewTestCase):
    def setUp(self):
        super(ViewIteratorTest, self).setUp()
        self.skipIfMock()

    def make_connection(self):
        try:
            return super(ViewIteratorTest,
                         self).make_connection(bucket='beer-sample')
        except CouchbaseError:
            raise SkipTest("Need 'beer-sample' bucket for this")

    def test_simple_query(self):
        ret = self.cb.query("beer", "brewery_beers", limit=3)
        self.assertIsInstance(ret, View)
        self.assertIsInstance(ret.row_processor, RowProcessor)

        count = 0
        rows = list(ret)
        self.assertEqual(len(rows), 3)
        for r in rows:
            self.assertIsInstance(r, ViewRow)

    def test_include_docs(self):
        ret = self.cb.query("beer", "brewery_beers", limit=10,
                            include_docs=True)
        rows = list(ret)
        self.assertEqual(len(rows), 10)
        for r in rows:
            self.assertIsInstance(r.doc, self.cls_Result)
            doc = r.doc
            mc_doc = self.cb.get(r.docid, quiet=True)
            self.assertEqual(doc.cas, mc_doc.cas)
            self.assertEqual(doc.value, mc_doc.value)
            self.assertTrue(doc.success)

        # Try with reduce
        self.assertRaises(ArgumentError,
                          self.cb.query,
                          "beer", "by_location",
                          reduce=True,
                          include_docs=True)

    def test_bad_view(self):
        ret = self.cb.query("beer", "bad_view")
        self.assertIsInstance(ret, View)
        self.assertRaises(HTTPError,
                          tuple, ret)

    def test_streaming(self):
        ret = self.cb.query("beer", "brewery_beers", streaming=True, limit=100)
        rows = list(ret)
        self.assertEqual(len(rows), 100)

        # Get all the views
        ret = self.cb.query("beer", "brewery_beers", streaming=True)
        rows = list(ret)
        self.assertTrue(len(rows))
        self.assertEqual(len(rows), ret.indexed_rows)

        self.assertTrue(ret.raw.value)
        self.assertIsInstance(ret.raw.value, dict)
        self.assertTrue('total_rows' in ret.raw.value)

    def test_streaming_dtor(self):
        # Ensure that the internal lcb_http_request_t is destroyed if the
        # Python object is destroyed before the results are done.

        ret = self.cb.query("beer", "brewery_beers", streaming=True)
        v = iter(ret)
        try:
            v.next()
        except AttributeError:
            v.__next__()

        del ret

    def test_mixed_query(self):
        self.assertRaises(ArgumentError,
                          self.cb.query,
                          "d", "v",
                          query=Query(),
                          limit=10)

        self.cb.query("d","v", query=Query(limit=5).update(skip=15))

    def test_range_query(self):
        q = Query()

        q.mapkey_range = [
            ["abbaye_de_maredsous"],
            ["abbaye_de_maredsous", Query.STRING_RANGE_END]
        ]

        q.inclusive_end = True

        ret = self.cb.query("beer", "brewery_beers", query=q)
        rows = list(ret)
        self.assertEqual(len(rows), 4)

        q.mapkey_range = [ ["u"], ["v"] ]
        ret = self.cb.query("beer", "brewery_beers", query=q)
        self.assertEqual(len(list(ret)), 88)

        q.mapkey_range = [ ["u"], ["uppper"+Query.STRING_RANGE_END]]
        ret = self.cb.query("beer", "brewery_beers", query=q)
        rows = list(ret)
        self.assertEqual(len(rows), 56)

    def test_key_query(self):
        q = Query()
        q.mapkey_single = ["abbaye_de_maredsous"]
        ret = self.cb.query("beer", "brewery_beers", query=q)
        rows = list(ret)
        self.assertEqual(len(rows), 1)

        q.mapkey_single = UNSPEC
        q.mapkey_multi = [["abbaye_de_maredsous"],
                          ["abbaye_de_maredsous", "abbaye_de_maredsous-8"]]
        ret = self.cb.query("beer", "brewery_beers", query=q)
        rows = list(ret)
        self.assertEqual(len(rows), 2)

    def test_row_processor(self):
        rp = BreweryBeerRowProcessor()
        q = Query(limit=20)

        ret = self.cb.query("beer", "brewery_beers",
                            query=q,
                            row_processor=rp,
                            include_docs=True)

        beers = list(ret)
        for b in beers:
            self.assertIsInstance(b, Beer)
            self.assertIsInstance(b.brewery, Brewery)

        ret = self.cb.query("beer", "brewery_beers",
                            query=q,
                            row_processor=rp,
                            include_docs=False)

        list(ret)

        ret = self.cb.query("beer", "brewery_beers",
                            row_processor=rp,
                            include_docs=False,
                            limit=40)

        self.assertRaises(ValueError, list, ret)

    def test_already_queried(self):
        ret = self.cb.query("beer", "brewery_beers", limit=5)
        list(ret)
        self.assertRaises(AlreadyQueriedError, list, ret)

    def test_no_rows(self):
        ret = self.cb.query("beer", "brewery_beers", limit=0)
        for row in ret:
            raise Exception("...")


    def test_long_uri(self):
        qobj = Query()
        qobj.mapkey_multi = [ str(x) for x in xrange(MAX_URI_LENGTH) ]
        ret = self.cb.query("beer", "brewery_beers", query=qobj)
        # No assertions, just make sure it didn't break
        for row in ret:
            raise Exception("...")

        # Apparently only the "keys" parameter is supposed to be in POST.
        # Let's fetch 100 items now
        keys = [r.key for r in self.cb.query("beer", "brewery_beers", limit=100)]
        self.assertEqual(100, len(keys))

        kslice = keys[90:]
        self.assertEqual(10, len(kslice))
        rows = [x for x in self.cb.query("beer", "brewery_beers", mapkey_multi=kslice, limit=5)]
        self.assertEqual(5, len(rows))
        for row in rows:
            self.assertTrue(row.key in kslice)


    def _verify_data(self, ret):
        list(ret)
        data = ret.raw.value
        self.assertTrue('rows' in data)
        self.assertTrue('total_rows' in data)
        self.assertTrue('debug_info' in data)


    def test_http_data(self):
        q = Query(limit=30, debug=True)
        self._verify_data(self.cb.query("beer", "brewery_beers", streaming=False,
                                        query=q))

    def test_http_data_streaming(self):
        q = Query(limit=30, debug=True)
        self._verify_data(self.cb.query("beer", "brewery_beers", streaming=True,
                                        query=q))

    def test_pycbc_206(self):
        # Set up the view..
        design = self.cb.design_get('beer', use_devmode=False).value
        if not 'with_value' in design['views']:

            design['views']['with_value'] = {
                'map': 'function(doc,meta) { emit(meta.id,doc.name); }'
            }

            ret = self.cb.design_create('beer', design, use_devmode=0)
            self.assertTrue(ret.success)

        # Streaming with values
        view = self.cb.query("beer", "with_value", streaming=True)
        rows = list(view)
        self.assertTrue(len(rows))

########NEW FILE########
__FILENAME__ = view_t
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import json

from couchbase.tests.base import ViewTestCase
from couchbase.user_constants import FMT_JSON
from couchbase.exceptions import HTTPError

DESIGN_JSON = {
    'language' : 'javascript',
    'views' : {
        'recent_posts' : {
            'map' :
            """
            function(doc) {
                if (doc.date && doc.title) {
                    emit(doc.date, doc.title);
                }
            }
            """.replace("\n", '')
        }
    }
}

DOCS_JSON = {
    "bought-a-cat" : {
        "title" : "Bought a Cat",
        "body" : "I went to the pet store earlier and brought home a "
                "little kitty",
        "date" : "2009/01/30 18:04:11"
    },
    "biking" : {
        "title" : "Biking",
        "body" : "My biggest hobby is mountainbiking. The other day..",
        "date" : "2009/01/30 18:04:11"
    },
    "hello-world" : {
        "title" : "Hello World",
        "body" : "Well hello and welcome to my new blog",
        "date" : "2009/01/15 15:52:20"
    }
}

class ConnectionViewTest(ViewTestCase):
    def setUp(self):
        super(ConnectionViewTest, self).setUp()
        self.skipIfMock()

        ret = self.cb.design_create('blog', DESIGN_JSON, use_devmode=False)
        self.assertTrue(ret.success)
        self.assertTrue(self.cb.set_multi(DOCS_JSON, format=FMT_JSON).all_ok)

    def test_simple_view(self):
        ret = self.cb._view("blog", "recent_posts",
                            params={ 'stale' : 'false' })
        self.assertTrue(ret.success)
        rows = ret.value
        self.assertIsInstance(rows, dict)
        print(rows)
        self.assertTrue(rows['total_rows']  >= 3)
        self.assertTrue(len(rows['rows']) == rows['total_rows'])

    def test_with_params(self):
        ret = self.cb._view("blog", "recent_posts",
                            params={'limit':1})
        self.assertTrue(ret.success)
        rows = ret.value['rows']
        self.assertEqual(len(rows), 1)

    def test_with_strparam(self):
        ret = self.cb._view("blog", "recent_posts", params='limit=2')
        self.assertTrue(ret.success)
        self.assertEqual(len(ret.value['rows']), 2)

    def test_with_jparams(self):
        jkey_pure = '2009/01/15 15:52:20'

        ret = self.cb._view("blog", "recent_posts",
                            params={
                                'startkey' : jkey_pure,
                                'endkey' : jkey_pure,
                                'inclusive_end' : 'true'
                            })
        print(ret)
        self.assertTrue(ret.success)
        rows = ret.value['rows']
        self.assertTrue(len(rows) == 1)
        single_row = rows[0]
        self.assertEqual(single_row['id'], 'hello-world')
        self.assertEqual(single_row['key'], jkey_pure)


        jkey_pure = []
        for v in DOCS_JSON.values():
            curdate = v['date']
            jkey_pure.append(curdate)

        ret = self.cb._view("blog", "recent_posts",
                            params={
                                'keys' : jkey_pure
                            })
        self.assertTrue(ret.success)
        self.assertTrue(len(ret.value['rows']), 3)
        for row in ret.value['rows']:
            self.assertTrue(row['id'] in DOCS_JSON)
            self.assertTrue(row['key'] in jkey_pure)

    def test_missing_view(self):
        self.assertRaises(HTTPError,
                          self.cb._view,
                          "nonexist", "designdoc")

########NEW FILE########
__FILENAME__ = importer
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""
File which contains all the test cases.
This should be loaded after all the pre-test configuration has
been done.
"""
from __future__ import print_function
import os
import os.path

imps = []
testmods = []
testclasses = []

for name in os.listdir(os.path.join(os.path.dirname(__file__), 'cases')):
    if name.startswith('__init__'):
        continue

    name, ext = os.path.splitext(name)
    if ext.lower() != '.py':
        continue

    imps.append(name)

def _get_packages():
    """
    Returns a dictionary of { name: module_object } for all cases
    """
    ret = {}
    for modname in imps:
        print(repr(modname))

        module = __import__('couchbase.tests.cases.'+modname,
                            fromlist=('couchbase', 'tests', 'cases'))
        ret[modname] = module
    return ret

def _get_classes(modules):
    """
    Returns an extracted dictionary of { name: test_class } as combined
    from all the modules provided
    """
    ret = {}

    for module in modules:
        for attrname in dir(module):
            attrobj = getattr(module, attrname)

            if not isinstance(attrobj, type):
                continue

            from couchbase.tests.base import CouchbaseTestCase
            if not issubclass(attrobj, CouchbaseTestCase):
                continue

            ret[attrname] = attrobj

    return ret


def get_configured_classes(implconfig, implstr=None, skiplist=None):
    """
    returns a tuple of (module_dict, testcase_dict)
    :param implstr: A unique string to be appended to each test case
    :param implconfig: An ApiConfigurationMixin to use as the mixin for
    the test class.
    """
    d_mods = _get_packages()
    d_cases = _get_classes(d_mods.values())
    ret = {}

    if not implstr:
        implstr = "_" + implconfig.factory.__name__

    if not skiplist:
        skiplist = []

    for name, case in d_cases.items():
        if name in skiplist:
            continue

        cls = type(name+implstr, (case, implconfig), {})
        ret[name+implstr] = cls

    return ret

if __name__ == "__main__":
    mods, classes = get_all()
    for cls in classes.values():
        print(cls.__name__)

########NEW FILE########
__FILENAME__ = test_sync
from couchbase.connection import Connection
from couchbase.views.iterator import View
from couchbase.tests.base import ApiImplementationMixin
from couchbase.tests.importer import get_configured_classes

class SyncImplMixin(ApiImplementationMixin):
    factory = Connection
    viewfactory = View
    should_check_refcount = True

configured_cases = get_configured_classes(SyncImplMixin)
globals().update(configured_cases)

########NEW FILE########
__FILENAME__ = transcoder
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import warnings
import json
import pickle

from couchbase import (FMT_JSON, FMT_AUTO,
                       FMT_BYTES, FMT_UTF8, FMT_PICKLE, FMT_MASK)
from couchbase.exceptions import ValueFormatError
from couchbase._libcouchbase import Transcoder
from couchbase._pyport import unicode


class TranscoderPP(object):
    """
    This is a pure-python Transcoder class. It is here only to show a reference
    implementation. It is recommended that you subclass from
    the :class:`Transcoder` object instead if all the methods are not
    implemented.
    """

    def encode_key(self, key):
        ret = (self.encode_value(key, FMT_UTF8))[0]
        return ret

    def decode_key(self, key):
        return self.decode_value(key, FMT_UTF8)

    def encode_value(self, value, format):
        if format == FMT_AUTO:
            if isinstance(value, unicode):
                format = FMT_UTF8
            elif isinstance(value, (bytes, bytearray)):
                format = FMT_BYTES
            elif isinstance(value, (list, tuple, dict, bool)) or value is None:
                format = FMT_JSON
            else:
                format = FMT_PICKLE

        fbase = format & FMT_MASK

        if fbase not in (FMT_PICKLE, FMT_JSON, FMT_BYTES, FMT_UTF8):
            raise ValueError("Unrecognized format")

        if fbase == FMT_BYTES:
            if isinstance(value, bytes):
                pass

            elif isinstance(value, bytearray):
                value = bytes(value)

            else:
                raise TypeError("Expected bytes")

            return (value, format)

        elif fbase == FMT_UTF8:
            return (value.encode('utf-8'), format)

        elif fbase == FMT_PICKLE:
            return (pickle.dumps(value), FMT_PICKLE)

        elif fbase == FMT_JSON:
            return (json.dumps(value, ensure_ascii=False
                               ).encode('utf-8'), FMT_JSON)

        else:
            raise ValueError("Unrecognized format '%r'" % (format,))

    def decode_value(self, value, flags):
        is_recognized_format = True
        fbase = flags & FMT_MASK

        if fbase not in (FMT_JSON, FMT_UTF8, FMT_BYTES, FMT_PICKLE):
            fbase = FMT_BYTES
            is_recognized_format = False

        if fbase == FMT_BYTES:
            if not is_recognized_format:
                warnings.warn("Received unrecognized flags %d" % (flags,))
            return value

        elif fbase == FMT_UTF8:
            return value.decode("utf-8")

        elif fbase == FMT_JSON:
            return json.loads(value.decode("utf-8"))

        elif fbase == FMT_PICKLE:
            return pickle.loads(value)

########NEW FILE########
__FILENAME__ = user_constants
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Constants defined in _libcouchbase module for use by users
"""
import couchbase._bootstrap
from couchbase._libcouchbase import (
    FMT_JSON,
    FMT_BYTES,
    FMT_UTF8,
    FMT_PICKLE,
    FMT_AUTO,
    FMT_MASK,

    OBS_PERSISTED,
    OBS_FOUND,
    OBS_NOTFOUND,
    OBS_LOGICALLY_DELETED,

    OBS_MASK,

    LOCKMODE_WAIT,
    LOCKMODE_EXC,
    LOCKMODE_NONE
)

########NEW FILE########
__FILENAME__ = iterator
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from collections import namedtuple
from copy import deepcopy
import json
from warnings import warn

from couchbase.exceptions import ArgumentError, CouchbaseError, ViewEngineError
from couchbase.views.params import Query, UNSPEC, make_dvpath
from couchbase._pyport import ulp, xrange
from couchbase.user_constants import FMT_JSON
import couchbase._libcouchbase as C

MAX_URI_LENGTH = 2048 # Let's be safe

class AlreadyQueriedError(CouchbaseError):
    """Thrown when iterating over a View which was already iterated over"""


ViewRow = namedtuple('ViewRow', ['key', 'value', 'docid', 'doc'])
"""
Default class for a single row.
"""


class RowProcessor(object):
    """
    This class contains the handling and conversion functions between
    multiple rows and the means by which they are returned from the
    view iterator.

    This class should be overidden if you are:

    * Using a custom row class
        This saves on processing time and memory by converting from the raw
        results rather than having to unpack from the default class. This
        class returns a :class:`ViewRow` object by default. (This can also
        be overridden using the :attr:`rowclass` attribute)

    * Fetching multiple documents for each row
        You can use the :meth:`~couchbase.connection.Connection.get_multi`
        method to efficiently fetch multiple docs beforehand for the entire
        page.

    .. attribute:: rowclass

        Class or function to call for each result (row) received. This
        is called as ``rowclass(key, value, docid, doc)``

        * ``key`` is the key as returned by the first argument to the
            view function's ``emit``.
        * ``value`` is the value returned as the second argument to the
            view function's ``emit``, or the value of the ``reduce``
            function
        * ``docid`` is the ID of the document itself (as stored by one
            of the :meth:`~couchbase.connection.Connection.set` family of
            methods).
            If ``reduce`` was set to true for the view, this will always
            be None.
        * ``doc`` is the document itself - Only valid if ``include_docs``
            is set to true - in which case a
            :class:`~couchbase.connection.Result` object is passed.
            If ``reduce`` was set to true for the view, this will always
            be None
            Otherwise, ``None`` is passed instead.

        By default, the :class:`ViewRow` is used.
    """
    def __init__(self, rowclass=ViewRow):
        self._riter = None
        self._docs = None
        self.rowclass = rowclass

    def handle_rows(self, rows, connection, include_docs):
        """
        Preprocesses a page of rows.

        :param list rows: A list of rows. Each row is a JSON object containing
            the decoded JSON of the view as returned from the server
        :param connection: The connection object (pass to the :class:`View`
            constructor)
        :param include_docs: Whether to include documents in the return value.
            This is ``True`` or ``False`` depending on what was passed to the
            :class:`View` constructor

        :return: an iterable. When the iterable is exhausted, this method will
            be called again with a new 'page'.
        """
        self._riter = iter(rows)

        if not include_docs:
            return iter(self)

        keys = tuple(x['id'] for x in rows)
        self._docs = connection.get_multi(keys, quiet=True)
        return iter(self)

    def __iter__(self):
        if not self._riter:
            return

        for ret in self._riter:
            doc = None
            if self._docs is not None:
                # We still want to go through this if we have an empty dict
                try:
                    doc = self._docs[ret['id']]
                except KeyError:
                    warn("Error encountered when executing view. "
                         "Inspect 'errors' for more information")

            yield self.rowclass(ret['key'],
                                ret['value'],
                                # Use get, because reduce values don't have
                                # IDs
                                ret.get('id'),
                                doc)

        self._docs = None
        self._riter = None


class View(object):
    def __init__(self,
                 parent,
                 design,
                 view,
                 row_processor=None,
                 streaming=0,
                 include_docs=False,
                 query=None,
                 **params):
        """
        Construct a iterable which can be used to iterate over view query
        results.

        :param parent: The parent Connection object
        :type parent: :class:`~couchbase.connection.Connection`
        :param string design: The design document
        :param string view: The name of the view within the design document
        :param callable row_processor: See :attr:`row_processor` for more
            details.

        :param boolean include_docs: If set, the document itself will be
            retrieved for each row in the result. The default algorithm
            uses :meth:`~couchbase.connection.Connection.get_multi` for each
            page (i.e. every :attr:`streaming` results).

            The :attr:`~couchbase.views.params.Query.reduce`
            family of attributes must not be active, as results fro
            ``reduce`` views do not have corresponding
            doc IDs (as these are aggregation functions).

        :param bool streaming:
            Whether a streaming chunked request should be used. This is
            helpful for handling the view results in small chunks rather
            than loading the entire resultset into memory at once. By default,
            a single request is made and the response is decoded at once. With
            streaming enabled, rows are decoded incrementally.

        :param query: If set, is a :class:`~couchbase.views.params.Query`
            object. It is illegal to use this in conjunction with
            additional ``params``

        :param params: Extra view options. This may be used to pass view
            arguments (as defined in :class:`~couchbase.views.params.Query`)
            without explicitly constructing a
            :class:`~couchbase.views.params.Query` object.
            It is illegal to use this together with the ``query`` argument.
            If you wish to 'inline' additional arguments to the provided
            ``query`` object, use the
            query's :meth:`~couchbase.views.params.Query.update` method
            instead.

        This object is an iterator - it does not send out the request until
        the first item from the iterator is request. See :meth:`__iter__` for
        more details on what this object returns.


        Simple view query, with no extra options::

            # c is the Connection object.

            for result in View(c, "beer", "brewery_beers"):
                print("emitted key: {0}, doc_id: {1}"
                        .format(result.key, result.docid))


        Execute a view with extra query options::

            # Implicitly creates a Query object

            view = View(c, "beer", "by_location",
                        limit=4,
                        reduce=True,
                        group_level=2)

        Pass a Query object::

            q = Query(
                stale=False,
                inclusive_end=True,
                mapkey_range=[
                    ["21st_ammendment_brewery_cafe"],
                    ["21st_ammendment_brewery_cafe", Query.STRING_RANGE_END]
                ]
            )

            view = View(c, "beer", "brewery_beer", query=q)

        Add extra parameters to query object for single call::

            view = View(c, "beer", "brewery_beer",
                        query=q.update(debug=True, copy=True))


        Include documents with query::

            view = View(c, "beer", "brewery_beer",
                        query=q, include_docs=True)

            for result in view:
                print("Emitted key: {0}, Document: {1}".format(
                    result.key, result.doc.value))
        """

        self._parent = parent
        self.design = design
        self.view = view
        self.errors = []
        self.raw = None
        self.rows_returned = 0

        self.include_docs = include_docs
        self.indexed_rows = 0

        if not row_processor:
            row_processor = RowProcessor()
        self.row_processor = row_processor
        self._rp_iter = None

        if query and params:
            raise ArgumentError.pyexc(
                "Extra parameters are mutually exclusive with the "
                "'query' argument. Use query.update() to add extra arguments")

        if query:
            self._query = deepcopy(query)
        else:
            self._query = Query.from_any(params)

        if include_docs:
            if (self._query.reduce or
                    self._query.group or
                    self._query.group_level):

                raise ArgumentError.pyexc("include_docs is only applicable "
                                          "for map-only views, but 'reduce', "
                                          "'group', or 'group_level' "
                                          "was specified",
                                          self._query)

        # The original 'limit' parameter, passed to the query.
        self._streaming = streaming
        self._do_iter = True

    @property
    def streaming(self):
        """
        Read-Only. Returns whether streaming is enabled for this view.
        """
        return self._streaming

    @property
    def query(self):
        """
        Returns the :class:`~couchbase.views.params.Query` object associated
        with this execution instance.

        Note that is normally a modified version
        of the passed object (in the constructor's ``query`` params). It should
        not be directly modified.
        """
        return self._query

    def _handle_errors(self, errors):
        if not errors:
            return

        self.errors += [ errors ]

        if self._query.on_error != 'continue':
            raise ViewEngineError.pyexc("Error while executing view.",
                                        self.errors)
        else:
            warn("Error encountered when executing view. Inspect 'errors' "
                 "for more information")

    def _handle_meta(self, value):
        if not isinstance(value, dict):
            return

        self.indexed_rows = value.get('total_rows', 0)
        self._handle_errors(value.get('errors'))

    def _process_page(self, rows):
        if not rows:
            return

        self.rows_returned += len(rows)

        self._rp_iter = self.row_processor.handle_rows(rows,
                                                       self._parent,
                                                       self.include_docs)

        # Raise exceptions early on
        self._rp_iter = iter(self._rp_iter)

    def _handle_single_view(self):
        self.raw = self._create_raw()
        self._process_page(self.raw.value['rows'])
        self._handle_meta(self.raw.value)

    def _create_raw(self, **kwargs):
        """
        Return common parameters for _libcouchbase._http_request
        """
        d = {
            'type': C.LCB_HTTP_TYPE_VIEW,
            'fetch_headers': True,
            'quiet': False,
            'response_format': FMT_JSON
        }

        # Figure out the path
        qstr = self._query.encoded
        uri = make_dvpath(self.design, self.view)

        if len(uri) + len(qstr) > MAX_URI_LENGTH:
            (uriparams, post_data) = self._query._long_query_encoded

            d['method'] = C.LCB_HTTP_METHOD_POST
            d['post_data'] = post_data
            d['path'] = uri + uriparams
            d['content_type'] = "application/json"

        else:
            d['method'] = C.LCB_HTTP_METHOD_GET
            d['path'] = "{0}{1}".format(uri, qstr)


        d.update(**kwargs)
        return self._parent._http_request(**d)

    def _setup_streaming_request(self):
        """
        Sets up the streaming request. This contains a streaming
        :class:`couchbase.results.HttpResult` object
        """
        self.raw = self._create_raw(chunked=True)

    def _process_payload(self, rows):
        if rows:
            rows = tuple(json.loads(r) for r in rows)
            self._process_page(rows)

        if self.raw.done:
            self._handle_meta(self.raw.value)
            self._do_iter = False

        # No rows and nothing to iterate over?
        elif not self._rp_iter:
            self._rp_iter = iter([])

    def _get_page(self):
        if not self._streaming:
            self._handle_single_view()
            self._do_iter = False
            return

        if not self.raw:
            self._setup_streaming_request()

        # Fetch the rows:
        rows = self.raw._fetch()
        self._process_payload(rows)

    def __iter__(self):
        """
        Returns a row for each query.
        The type of the row depends on the :attr:`row_processor` being used.

        :raise: :exc:`~couchbase.exceptions.ViewEngineError`

            If an error was encountered while processing the view, and the
            :attr:`~couchbase.views.params.Query.on_error`
            attribute was not set to `continue`.

            If `continue` was specified, a warning message is printed to the
            screen (via ``warnings.warn`` and operation continues). To inspect
            the error, examine :attr:`errors`

        :raise: :exc:`AlreadyQueriedError`

            If this object was already iterated
            over and the last result was already returned.
        """
        if not self._do_iter:
            raise AlreadyQueriedError.pyexc(
                "This object has already been executed. Create a new one to "
                "query again")

        while self._do_iter:
            self._get_page()
            if not self._rp_iter:
                break

            for r in self._rp_iter:
                yield r

            self._rp_iter = None

    def __repr__(self):
        details = []
        details.append("Design={0}".format(self.design))
        details.append("View={0}".format(self.view))
        details.append("Query={0}".format(self._query))
        details.append("Rows Fetched={0}".format(self.rows_returned))
        return '{cls}<{details}>'.format(cls=self.__class__.__name__,
                                         details=', '.join(details))

########NEW FILE########
__FILENAME__ = params
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# This module is largely used by other modules, though it just contains
# simple string utilities :)

import json
from copy import deepcopy

from couchbase._pyport import long, xrange, ulp, basestring, parse_qs
from couchbase.exceptions import ArgumentError

# Some constants
STALE_UPDATE_BEFORE = "false"
STALE_UPDATE_AFTER = "update_after"
STALE_OK = "ok"
ONERROR_CONTINUE = "continue"
ONERROR_STOP = "stop"


class _Unspec(object):
    def __nonzero__(self):
        return False

    # Py3
    __bool__ = __nonzero__

    def __str__(self):
        return ""

    def __repr__(self):
        return "<Placeholder>"

UNSPEC = _Unspec()


def _bool_param_handler(input):
    if isinstance(input, bool):
        if input:
            return "true"
        else:
            return "false"

    if isinstance(input, basestring):
        if input not in ("true", "false"):
            raise ArgumentError.pyexc("String for boolean must be "
                                      "'true' or 'false'", input)
        return input

    try:
        input + 0
        if input:
            return "true"
        else:
            return "false"

    except TypeError:
        raise ArgumentError.pyexc("Boolean value must be boolean, "
                                  "numeric, or a string of 'true' "
                                  "or 'false'", input)


def _num_param_handler(input):
    # Don't allow booleans:
    if isinstance(input, bool):
        raise ArgumentError.pyexc("Cannot use booleans as numeric values",
                                  input)
    try:
        return str(int(input))
    except Exception as e:
        raise ArgumentError.pyexc("Expected a numeric argument", input, e)


def _string_param_common(input, do_quote=False):
    # TODO, if we pass this to urlencode, do we ever need to quote?
    # For the moment, i'm always forcing non-quote behavior
    do_quote = False

    s = None
    if isinstance(input, basestring):
        s = input

    elif isinstance(input, bool):
        raise ArgumentError.pyexc("Can't use boolean as string", input)

    elif isinstance(input, (int, long, float)):
        # Basic numeric types:
        s = str(input)

    else:
        raise ArgumentError.pyexc("Expected simple numeric type or string ",
                                  input)
    if do_quote:
        s = ulp.quote(s)

    return s


def _string_param_handler(input):
    return _string_param_common(input, do_quote=True)


def _generic_param_handler(input):
    return _string_param_handler(input, do_quote=False)


def _stale_param_handler(input):
    if input in (STALE_UPDATE_AFTER, STALE_OK, STALE_UPDATE_BEFORE):
        return input

    ret = _bool_param_handler(input)
    if ret == "true":
        ret = STALE_OK
    return ret


def _onerror_param_handler(input):
    if input not in (ONERROR_CONTINUE, ONERROR_STOP):
        raise ArgumentError.pyexc(
            "on_error must be 'continue' or 'stop'", input)

    return input


def _jval_param_handler(input):
    try:
        ret = json.dumps(input)
        return _string_param_handler(ret)
    except Exception as e:
        raise ArgumentError.pyexc("Couldn't convert value to JSON", input, e)


def _jarry_param_handler(input):
    ret = _jval_param_handler(input)
    if not ret.startswith('['):
        raise ArgumentError.pyexc(
            "Value must be converted to JSON array", input)

    return ret


# Some more constants. Yippie!
class Params(object):
    # Random, unspecified value.

    DESCENDING              = "descending"
    STARTKEY                = "startkey"
    STARTKEY_DOCID          = "startkey_docid"
    ENDKEY                  = "endkey"
    ENDKEY_DOCID            = "endkey_docid"
    KEY                     = "key"
    KEYS                    = "keys"
    INCLUSIVE_END           = "inclusive_end"

    GROUP                   = "group"
    GROUP_LEVEL             = "group_level"
    REDUCE                  = "reduce"

    SKIP                    = "skip"
    LIMIT                   = "limit"

    ON_ERROR                = "on_error"
    STALE                   = "stale"
    DEBUG                   = "debug"
    CONNECTION_TIMEOUT      = "connection_timeout"
    FULL_SET                = "full_set"

    MAPKEY_SINGLE           = "mapkey_single"
    MAPKEY_MULTI            = "mapkey_multi"
    MAPKEY_RANGE            = "mapkey_range"
    DOCKEY_RANGE            = "dockey_range"

_HANDLER_MAP = {
    Params.DESCENDING        : _bool_param_handler,

    Params.STARTKEY          : _jval_param_handler,
    Params.STARTKEY_DOCID    : _string_param_handler,
    Params.ENDKEY            : _jval_param_handler,
    Params.ENDKEY_DOCID      : _string_param_handler,

    Params.FULL_SET          : _bool_param_handler,

    Params.GROUP             : _bool_param_handler,
    Params.GROUP_LEVEL       : _num_param_handler,
    Params.INCLUSIVE_END     : _bool_param_handler,
    Params.KEY               : _jval_param_handler,
    Params.KEYS              : _jarry_param_handler,
    Params.ON_ERROR          : _onerror_param_handler,
    Params.REDUCE            : _bool_param_handler,
    Params.STALE             : _stale_param_handler,
    Params.SKIP              : _num_param_handler,
    Params.LIMIT             : _num_param_handler,
    Params.DEBUG             : _bool_param_handler,
    Params.CONNECTION_TIMEOUT: _num_param_handler
}


def _gendoc(param):
    for k, v in Params.__dict__.items():
        if param == v:
            return "\n:data:`Params.{0}`".format(k)


class Query(object):
    def _set_common(self, param, value, set_user=True):
        # Invalidate encoded string
        self._encoded = None

        if value is UNSPEC:
            self._real_options.pop(param, None)
            if set_user:
                self._user_options.pop(param, None)
            return

        handler = _HANDLER_MAP.get(param)
        if not handler:
            if not self.unrecognized_ok:
                raise ArgumentError.pyexc(
                    "Unrecognized parameter. To use unrecognized parameters, "
                    "set 'unrecognized_ok' to True")

        if not handler:
            self._extra_options[param] = _string_param_handler(value)
            return

        if self.passthrough:
            handler = _string_param_handler

        self._real_options[param] = handler(value)
        if set_user:
            self._user_options[param] = value

    def _get_common(self, param):
        if param in self._user_options:
            return self._user_options[param]
        return self._real_options.get(param, UNSPEC)

    def _set_range_common(self, k_sugar, k_start, k_end, value):
        """
        Checks to see if the client-side convenience key is present, and if so
        converts the sugar convenience key into its real server-side
        equivalents.

        :param string k_sugar: The client-side convenience key
        :param string k_start: The server-side key specifying the beginning of
            the range
        :param string k_end: The server-side key specifying the end of the
            range
        """

        if not isinstance(value, (list, tuple, _Unspec)):
            raise ArgumentError.pyexc(
                "Range specification for {0} must be a list, tuple or UNSPEC"
                .format(k_sugar))

        if self._user_options.get(k_start, UNSPEC) is not UNSPEC or (
                self._user_options.get(k_end, UNSPEC) is not UNSPEC):

            raise ArgumentError.pyexc(
                "Cannot specify {0} with either {1} or {2}"
                .format(k_sugar, k_start, k_end))

        if not value:
            self._set_common(k_start, UNSPEC, set_user=False)
            self._set_common(k_end, UNSPEC, set_user=False)
            self._user_options[k_sugar] = UNSPEC
            return

        if len(value) not in (1, 2):
            raise ArgumentError.pyexc("Range specification "
                                      "must have one or two elements",
                                      value)

        value = value[::]
        if len(value) == 1:
            value.append(UNSPEC)

        for p, ix in ((k_start, 0), (k_end, 1)):
            self._set_common(p, value[ix], set_user=False)

        self._user_options[k_sugar] = value

    def __rangeprop(k_sugar, k_start, k_end):
        def getter(self):
            return self._user_options.get(k_sugar, UNSPEC)

        def setter(self, value):
            self._set_range_common(k_sugar, k_start, k_end, value)

        return property(getter, setter, fdel=None, doc=_gendoc(k_sugar))

    def __genprop(p):
        def getter(self):
            return self._get_common(p)

        def setter(self, value):
            self._set_common(p, value)

        return property(getter, setter, fdel=None, doc=_gendoc(p))


    descending          = __genprop(Params.DESCENDING)

    # Use the range parameters. They're easier
    startkey            = __genprop(Params.STARTKEY)
    endkey              = __genprop(Params.ENDKEY)
    startkey_docid      = __genprop(Params.STARTKEY_DOCID)
    endkey_docid        = __genprop(Params.ENDKEY_DOCID)

    keys                = __genprop(Params.KEYS)
    key                 = __genprop(Params.KEY)
    inclusive_end       = __genprop(Params.INCLUSIVE_END)
    skip                = __genprop(Params.SKIP)
    limit               = __genprop(Params.LIMIT)
    on_error            = __genprop(Params.ON_ERROR)
    stale               = __genprop(Params.STALE)
    debug               = __genprop(Params.DEBUG)
    connection_timeout  = __genprop(Params.CONNECTION_TIMEOUT)
    full_set            = __genprop(Params.FULL_SET)

    reduce              = __genprop(Params.REDUCE)
    group               = __genprop(Params.GROUP)
    group_level         = __genprop(Params.GROUP_LEVEL)

    # Aliases:
    mapkey_single       = __genprop(Params.KEY)
    mapkey_multi        = __genprop(Params.KEYS)

    mapkey_range        = __rangeprop(Params.MAPKEY_RANGE,
                                      Params.STARTKEY, Params.ENDKEY)

    dockey_range        = __rangeprop(Params.DOCKEY_RANGE,
                                      Params.STARTKEY_DOCID,
                                      Params.ENDKEY_DOCID)


    STRING_RANGE_END = json.loads('"\u0FFF"')
    """
    Highest acceptable unicode value
    """

    def __init__(self, passthrough=False, unrecognized_ok=False, **params):
        """
        Create a new Query object.

        A Query object is used as a container for the various view options.
        It can be used as a standalone object to encode queries but is typically
        passed as the ``query`` value to :class:`~couchbase.views.iterator.View`.

        :param boolean passthrough:
            Whether *passthrough* mode is enabled

        :param boolean unrecognized_ok:
            Whether unrecognized options are acceptable. See
            :ref:`passthrough_values`.

        :param params:
            Key-value pairs for view options. See :ref:`view_options` for
            a list of acceptable options and their values.


        :raise: :exc:`couchbase.exceptions.ArgumentError` if a view option
            or a combination of view options were deemed invalid.

        """
        self.passthrough = passthrough
        self.unrecognized_ok = unrecognized_ok
        self._real_options = {}
        self._user_options = {}
        self._extra_options = {}

        self._encoded = None

        # String literal to pass along with the query
        self._base_str = ""
        self.update(**params)

    def update(self, copy=False, **params):
        """
        Chained assignment operator.

        This may be used to quickly assign extra parameters to the
        :class:`Query` object.

        Example::

            q = Query(reduce=True, full_sec=True)

            # Someplace later

            v = View(design, view, query=q.update(mapkey_range=["foo"]))

        Its primary use is to easily modify the query object (in-place).

        :param boolean copy:
            If set to true, the original object is copied before new attributes
            are added to it
        :param params: Extra arguments. These must be valid query options.

        :return: A :class:`Query` object. If ``copy`` was set to true, this
            will be a new instance, otherwise it is the same instance on which
            this method was called

        """
        if copy:
            self = deepcopy(self)

        for k, v in params.items():
            if not hasattr(self, k):
                if not self.unrecognized_ok:
                    raise ArgumentError.pyexc("Unknown option", k)
                self._set_common(k, v)

            else:
                setattr(self, k, v)

        return self

    @classmethod
    def from_any(cls, params):
        """
        Creates a new Query object from input.

        :param params: Parameter to convert to query
        :type params: dict, string, or :class:`Query`

        If ``params`` is a :class:`Query` object already, a deep copy is made
        and a new :class:`Query` object is returned.

        If ``params`` is a string, then a :class:`Query` object is contructed
        from it. The string itself is not parsed, but rather prepended to
        any additional parameters (defined via the object's methods)
        with an additional ``&`` characted.

        If ``params`` is a dictionary, it is passed to the :class:`Query`
        constructor.

        :return: a new :class:`Query` object
        :raise: :exc:`ArgumentError` if the input is none of the acceptable
            types mentioned above. Also raises any exceptions possibly thrown
            by the constructor.

        """
        if isinstance(params, cls):
            return deepcopy(params)

        elif isinstance(params, dict):
            return cls(**params)

        elif isinstance(params, basestring):
            ret = cls()
            ret._base_str = params
            return ret

        else:
            raise ArgumentError.pyexc("Params must be Query, dict, or string")

    def _encode(self, omit_keys=False):
        res_d = []

        for k, v in self._real_options.items():
            if v is UNSPEC:
                continue

            if omit_keys and k == "keys":
                continue

            if not self.passthrough:
                k = ulp.quote(k)
                v = ulp.quote(v)

            res_d.append("{0}={1}".format(k, v))

        for k, v in self._extra_options.items():
            res_d.append("{0}={1}".format(k, v))

        return '&'.join(res_d)

    @property
    def encoded(self):
        """
        Returns an encoded form of the query
        """
        if not self._encoded:
            self._encoded = self._encode()

        if self._base_str:
            return '&'.join((self._base_str, self._encoded))

        else:
            return self._encoded

    @property
    def _long_query_encoded(self):
        """
        Returns the (uri_part, post_data_part) for a long query.
        """
        uristr = self._encode(omit_keys=True)
        kstr = "{}"

        klist = self._real_options.get('keys', UNSPEC)
        if klist != UNSPEC:
            kstr = '{{"keys":{0}}}'.format(klist)

        return (uristr, kstr)

    @property
    def has_blob(self):
        """
        Whether this query object is 'dirty'.

        A 'dirty' object is one which
        contains parameters unrecognized by the internal handling methods.
        A dirty query may be constructed by using the ``passthrough``
        or ``unrecognized_ok`` options, or by passing a string to
        :meth:`from_any`
        """
        return self._base_str or self.unrecognized_ok or self.passthrough

    def __repr__(self):
        return "Query:'{0}'".format(self.encoded)


def make_options_string(input, unrecognized_ok=False, passthrough=False):
    if not isinstance(input, Query):
        input = Query(passthrough=passthrough,
                      unrecognized_ok=unrecognized_ok,
                      **input)
    return input.encoded


def make_dvpath(doc, view):
    return "_design/{0}/_view/{1}?".format(doc, view)

########NEW FILE########
__FILENAME__ = _bootstrap
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
This module contains the core functionality of '_libcouchbase'. In short,
this contains the convergence between the C module and code written in Python.

While the _libcouchbase module should never be used directly, in the off chance
that this does happen, ensure this module is loaded as well before anything is
done, otherwise Bad Things May Happen.

Additionally, this
module contains python functions used exclusively from C. They are here
because it was quicker to write them in Python than it was in C. Do not touch
this file at all. You have been warned
"""
import json
import pickle

import couchbase.exceptions as E
import couchbase._libcouchbase as C
from couchbase.items import ItemCollection, ItemOptionDict, ItemSequence


def _result__repr__(self):
    """
    This is used as the `__repr__` function for the :class:`Result`
    """

    details = []
    flags = self.__class__._fldprops

    rcstr = "RC=0x{0:X}".format(self.rc)
    if self.rc != 0:
        rcstr += "[{0}]".format(self.errstr)

    details.append(rcstr)

    if flags & C.PYCBC_RESFLD_KEY and hasattr(self, 'key'):
        details.append("Key={0}".format(repr(self.key)))

    if flags & C.PYCBC_RESFLD_VALUE and hasattr(self, 'value'):
        details.append("Value={0}".format(repr(self.value)))

    if flags & C.PYCBC_RESFLD_CAS and hasattr(self, 'cas'):
        details.append("CAS=0x{cas:x}".format(cas=self.cas))

    if flags & C.PYCBC_RESFLD_CAS and hasattr(self, 'flags'):
        details.append("Flags=0x{flags:x}".format(flags=self.flags))

    if flags & C.PYCBC_RESFLD_HTCODE and hasattr(self, "http_status"):
        details.append("HTTP={0}".format(self.http_status))

    if flags & C.PYCBC_RESFLD_URL and hasattr(self, "url"):
        details.append("URL={0}".format(self.url))

    ret = "{0}<{1}>".format(self.__class__.__name__, ', '.join(details))
    return ret


def _observeinfo__repr__(self):
    constants = ('OBS_PERSISTED',
                 'OBS_FOUND',
                 'OBS_NOTFOUND',
                 'OBS_LOGICALLY_DELETED')


    flag_str = ''
    for c in constants:
        if self.flags == getattr(C, c):
            flag_str = c
            break

    fmstr = ("{cls}<Status=[{status_s} (0x{flags:X})], "
             "Master={is_master}, "
             "CAS=0x{cas:X}>")
    ret = fmstr.format(cls=self.__class__.__name__,
                       status_s=flag_str,
                       flags=self.flags,
                       is_master=bool(self.from_master),
                       cas=self.cas)
    return ret

def _json_encode_wrapper(*args):
    return json.dumps(*args, ensure_ascii=False, separators=(',', ':'))


class FMT_AUTO_object_not_a_number(object):
    pass

# TODO: Make this more readable and have PEP8 ignore it.
_FMT_AUTO = FMT_AUTO_object_not_a_number()


class PyPyMultiResultWrap(dict):
    def __init__(self, mres, d):
        super(PyPyMultiResultWrap, self).__init__()
        self.update(d)
        object.__setattr__(self, '_mres', mres)

    def __getattr__(self, name):
        return getattr(self._mres, name)

    def __setattr__(self, name, value):
        setattr(self._mres, name, value)


C._init_helpers(result_reprfunc=_result__repr__,
                fmt_utf8_flags=C.FMT_UTF8,
                fmt_bytes_flags=C.FMT_BYTES,
                fmt_json_flags=C.FMT_JSON,
                fmt_pickle_flags=C.FMT_PICKLE,
                pickle_encode=pickle.dumps,
                pickle_decode=pickle.loads,
                json_encode=_json_encode_wrapper,
                json_decode=json.loads,
                lcb_errno_map=E._LCB_ERRNO_MAP,
                misc_errno_map=E._EXCTYPE_MAP,
                default_exception=E.CouchbaseError,
                obsinfo_reprfunc=_observeinfo__repr__,
                itmcoll_base_type=ItemCollection,
                itmopts_dict_type=ItemOptionDict,
                itmopts_seq_type=ItemSequence,
                fmt_auto=_FMT_AUTO,
                pypy_mres_factory=PyPyMultiResultWrap)

C.FMT_AUTO = _FMT_AUTO

########NEW FILE########
__FILENAME__ = _pyport
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# This module contains various mappings for modules which have had
# their names changed across Python major versions

try:
    import urllib.parse as ulp
    from urllib.request import urlopen
    from urllib.parse import parse_qs
except ImportError:
    import urllib as ulp
    from urllib2 import urlopen
    from urlparse import parse_qs

try:
    long = long
except NameError:
    long = int

try:
    xrange = xrange
except NameError:
    xrange = range

try:
    basestring = basestring
except NameError:
    basestring = str

try:
    unicode = unicode
except NameError:
    unicode = str

########NEW FILE########
__FILENAME__ = couchbase_version
#!/usr/bin/env python

import subprocess
import datetime
import sys
import os.path
import warnings

class CantInvokeGit(Exception): pass
class VersionNotFound(Exception): pass

verfile = os.path.join(
    os.path.dirname(__file__),
    os.path.join("couchbase", "_version.py"))

def get_version():
    """
    Returns the version from the generated version file without actually
    loading it (and thus trying to load the extension module).
    """
    if not os.path.exists(verfile):
        raise VersionNotFound(verfile + " does not exist")
    fp = open(verfile, "r")
    vline = None
    for x in fp.readlines():
        x = x.rstrip()
        if not x:
            continue
        if not x.startswith("__version__"):
            continue

        vline = x.split('=')[1]
        break
    if not vline:
        raise VersionNotFound("version file present but has no contents")

    return vline.strip().rstrip().replace("'", '')

def gen_version():
    """
    Generate a version based on git tag info. This will write the
    couchbase/_version.py file. If not inside a git tree it will raise a
    CantInvokeGit exception - which is normal (and squashed by setup.py) if
    we are running from a tarball
    """
    if not os.path.exists(os.path.join(os.path.dirname(__file__), ".git")):
        raise CantInvokeGit("Not a git build")

    try:
        po = subprocess.Popen(("git", "describe", "--tags", "--long", "--always"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
    except OSError as e:
        raise CantInvokeGit(e)

    stdout, stderr = po.communicate()
    if po.returncode != 0:
        raise CantInvokeGit("Couldn't invoke git describe", stderr)

    try:
        # Python 3
        stdout = str(stdout.rstrip(), 'utf-8')
    except TypeError:
        stdout = str(stdout.rstrip())

    info = stdout.split('-')
    sha1 = info[-1]
    try:
        ncommits = int(info[-2])
        basevers = '-'.join(info[:-2])
        # Make the version string itself
        if not ncommits:
            vstr = basevers
        else:
            vstr = stdout

    except IndexError:
        warnings.warn("Malformed tag '{0}'".format(stdout))
        vstr = "0.0.0-UNKNOWN-" + stdout

    fp = open(verfile, "w")
    fp.write('''
# This file automatically generated by
#   {path}
# at
#   {now}
__version__ = '{vstr}'
'''.format(path=__file__,
           now=datetime.datetime.now().isoformat(' '),
           vstr=vstr))

    fp.close()

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "show":
        print(get_version())
    elif cmd == "make":
        gen_version()
        print(get_version())
    else:
        raise Exception("Command must be 'show' or 'make'")

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Couchbase Python Client Library documentation build configuration file, created by
# sphinx-quickstart on Fri Apr  5 17:46:04 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os
import sys

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../..'))
#sys.path.insert(0, os.path.abspath('../../couchbase'))
#sys.path.insert(0, os.path.abspath(os.path.join(os.pardir, os.pardir, 'couchbase')))
import couchbase_version

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'numpydoc', 'sphinx.ext.autosummary']
#extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode', 'numpydoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Couchbase Python Client Library'
copyright = '2013, Couchbase, Inc.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.
release = couchbase_version.get_version()

# The short X.Y version.
version = release.split('.')[:2]

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
html_theme = 'default'

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
html_static_path = ['_static']

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
htmlhelp_basename = 'CouchbasePythonClientLibrarydoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    ('index', 'CouchbasePythonClientLibrary.tex', 'Couchbase Python Client Library Documentation',
     'Couchbase, Inc.', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'couchbasepythonclientlibrary', 'Couchbase Python Client Library Documentation',
     ['Couchbase, Inc.'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'CouchbasePythonClientLibrary', 'Couchbase Python Client Library Documentation',
     'Couchbase, Inc.', 'CouchbasePythonClientLibrary', 'A python client library to store, retrieve and query data from a Couchbase cluster.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

autoclass_content = 'both'

########NEW FILE########
__FILENAME__ = basic
#!/usr/bin/env python
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from couchbase import Couchbase, FMT_PICKLE
from couchbase.exceptions import KeyExistsError


# Connect to the default bucket on local host
cb = Couchbase.connect(host='127.0.0.1', bucket='default')

# If you want to store the Python objects pickled and not as JSON
#cb.default_format = FMT_PICKLE

# Store a document
rv = cb.set('first', {'hello': 'world'})
cas = rv.cas
print(rv)

# Get the document
item = cb.get('first')
print(item)

# Overwrite the existing document only if the CAS value matched
try:
    # An exception will be raised if the CAS doesn't match
    wrong_cas = cas + 123
    cb.set('first', {'hello': 'world', 'additional': True}, cas=wrong_cas)
except KeyExistsError:
    # Get the correct current CAS value
    rv = cb.get('first')
    item, flags, correct_cas = rv.value, rv.flags, rv.cas
    # Set it again, this time with the correct CAS value
    rv = cb.set('first',
                {'hello': 'world', 'additional': True},
                cas=correct_cas)
    print(rv)

# Delete the document only if the CAS value matches (it would also
# work without a cas value)
cb.delete('first', cas=rv.cas)

# Make sure the document really got deleted
assert cb.get('first', quiet=True).success is False

########NEW FILE########
__FILENAME__ = bench
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

#!/usr/bin/env python
import argparse
from threading import Thread
from time import sleep, time
from couchbase.connection import Connection, FMT_BYTES
from couchbase.transcoder import Transcoder

ap = argparse.ArgumentParser()

ap.add_argument('-t', '--threads', default=4, type=int,
                help="Number of threads to spawn. 0 means no threads "
                "but workload will still run in the main thread")

ap.add_argument('-d', '--delay', default=0, type=float,
                help="Number of seconds to wait between each op. "
                "may be a fraction")

ap.add_argument('-b', '--bucket', default='default', type=str)
ap.add_argument('-p', '--password', default=None, type=str)
ap.add_argument('-H', '--hostname', default='localhost', type=str)
ap.add_argument('-D', '--duration', default=10, type=int,
                help="Duration of run (in seconds)")
ap.add_argument('-T', '--transcoder', default=False,
                action='store_true',
                help="Use the Transcoder object rather than built-in "
                "conversion routines")

ap.add_argument('--ksize', default=12, type=int,
                help="Key size to use")

ap.add_argument('--vsize', default=128, type=int,
                help="Value size to use")
ap.add_argument('--iops', default=False, action='store_true',
                help="Use Pure-Python IOPS plugin")

ap.add_argument('--batch', '-N', default=1, type=int,
                help="Number of commands to schedule per iteration")

options = ap.parse_args()
DO_UNLOCK_GIL = options.threads > 0
TC = Transcoder()


class Worker(Thread):
    def __init__(self):
        self.delay = options.delay
        self.key = 'K' * options.ksize
        self.value = b'V' * options.vsize
        self.kv = {}
        for x in range(options.batch):
            self.kv[self.key + str(x)] = self.value
        self.wait_time = 0
        self.opcount = 0
        connopts = { "bucket" : "default",
                     "host" : options.hostname,
                     "unlock_gil": DO_UNLOCK_GIL }
        if options.iops:
            connopts["experimental_gevent_support"] = True

        self.cb = Connection(**connopts)

        if options.transcoder:
            self.cb.transcoder = TC
        self.end_time = time() + options.duration
        super(Worker, self).__init__()

    def run(self, *args, **kwargs):
        cb = self.cb

        while time() < self.end_time:
            begin_time = time()
            rv = cb.set_multi(self.kv, format=FMT_BYTES)
            assert rv.all_ok, "Operation failed: "
            self.wait_time += time() - begin_time

            if self.delay:
                sleep(self.delay)

            self.opcount += options.batch


global_begin = None
worker_threads = []
if not options.threads:
    # No threding requested:
    w = Worker()
    worker_threads.append(w)
    global_begin = time()
    w.run()
else:
    for x in range(options.threads):
        worker_threads.append(Worker())

    global_begin = time()
    for t in worker_threads:
        t.start()

    for t in worker_threads:
        t.join()

global_duration = time() - global_begin
total_ops = sum([w.opcount for w in worker_threads])
total_time = 0
for t in worker_threads:
    total_time += t.wait_time

print("Total run took an absolute time of %0.2f seconds" % (global_duration,))
print("Did a total of %d operations" % (total_ops,))
print("Total wait time of %0.2f seconds" % (total_time,))
print("[WAIT] %0.2f ops/second" % (float(total_ops)/float(total_time),))
print("[ABS] %0.2f ops/second" % (float(total_ops)/float(global_duration),))

########NEW FILE########
__FILENAME__ = connection-pool
#!/usr/bin/env python
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This file shows how to make a simple connection pool using Couchbase.
"""
from couchbase.connection import Connection
from Queue import Queue, Empty
from threading import Lock, Thread
from time import time
from argparse import ArgumentParser


class ClientUnavailableError(Exception):
    pass


class ConnectionWrapper(Connection):
    """
    This is a simple subclass which adds usage statistics to inspect later on
    """
    def __init__(self, **kwargs):
        super(ConnectionWrapper, self).__init__(**kwargs)
        self.use_count = 0
        self.use_time = 0
        self.last_use_time = 0

    def start_using(self):
        self.last_use_time = time()

    def stop_using(self):
        self.use_time += time() - self.last_use_time
        self.use_count += 1


class Pool(object):
    def __init__(self, initial=4, max_clients=10, **connargs):
        """
        Create a new pool
        :param int initial: The initial number of client objects to create
        :param int max_clients: The maximum amount of clients to create. These
          clients will only be created on demand and will potentially be
          destroyed once they have been returned via a call to
          :meth:`release_client`
        :param connargs: Extra arguments to pass to the Connection object's
        constructor
        """
        self._q = Queue()
        self._l = []
        self._connargs = connargs
        self._cur_clients = 0
        self._max_clients = max_clients
        self._lock = Lock()

        for x in range(initial):
            self._q.put(self._make_client())
            self._cur_clients += 1

    def _make_client(self):
        ret = ConnectionWrapper(**self._connargs)
        self._l.append(ret)
        return ret

    def get_client(self, initial_timeout=0.05, next_timeout=200):
        """
        Wait until a client instance is available
        :param float initial_timeout:
          how long to wait initially for an existing client to complete
        :param float next_timeout:
          if the pool could not obtain a client during the initial timeout,
          and we have allocated the maximum available number of clients, wait
          this long until we can retrieve another one

        :return: A connection object
        """
        try:
            return self._q.get(True, initial_timeout)
        except Empty:
            try:
                self._lock.acquire()
                if self._cur_clients == self._max_clients:
                    raise ClientUnavailableError("Too many clients in use")
                cb = self._make_client()
                self._cur_clients += 1
                cb.start_using()
                return cb
            except ClientUnavailableError as ex:
                try:
                    return self._q.get(True, next_timeout)
                except Empty:
                    raise ex
            finally:
                self._lock.release()

    def release_client(self, cb):
        """
        Return a Connection object to the pool
        :param Connection cb: the client to release
        """
        cb.stop_using()
        self._q.put(cb, True)


class CbThread(Thread):
    def __init__(self, pool, opcount=10, remaining=10000):
        super(CbThread, self).__init__()
        self.pool = pool
        self.remaining = remaining
        self.opcount = opcount

    def run(self):
        while self.remaining:
            cb = self.pool.get_client()
            kv = dict(
                ("Key_{0}".format(x), str(x)) for x in range(self.opcount)
            )
            cb.set_multi(kv)
            self.pool.release_client(cb)
            self.remaining -= 1


def main():

    ap = ArgumentParser()
    ap.add_argument('-H', '--host', help="Host to connect to",
                    default="localhost")
    ap.add_argument('-b', '--bucket', help="Bucket to connect to",
                    default="default")
    ap.add_argument("-O", "--opcount", help="How many operations to perform "
                    "at once", type=int,
                    default=10)
    ap.add_argument('--pool-min',
                    help="Minimum pool size", default=4, type=int)
    ap.add_argument('--pool-max',
                    help="Maximum pool size", default=10, type=int)
    ap.add_argument('-t', '--threads', type=int, default=10,
                    help="Number of threads to launch")

    options = ap.parse_args()

    pool = Pool(initial=options.pool_min,
                max_clients=options.pool_max,
                bucket=options.bucket,
                host=options.host)

    thrs = [
        CbThread(pool, opcount=options.opcount) for _ in range(options.threads)
    ]

    map(lambda thr: thr.start(), thrs)
    map(lambda thr: thr.join(), thrs)

    for c in pool._l:
        print "Have client {0}".format(c)
        print "\tTime In Use: {0}, use count: {1}".format(c.use_time,
                                                          c.use_count)


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = gbench
#!/usr/bin/env python
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import argparse
from time import sleep, time

import gevent

from couchbase.connection import FMT_BYTES
from gcouchbase.connection import GConnection as Connection

ap = argparse.ArgumentParser()

ap.add_argument('-t', '--threads', default=4, type=int,
                help="Number of threads to spawn. 0 means no threads "
                "but workload will still run in the main thread")

ap.add_argument('-d', '--delay', default=0, type=float,
                help="Number of seconds to wait between each op. "
                "may be a fraction")

ap.add_argument('-b', '--bucket', default='default', type=str)
ap.add_argument('-p', '--password', default=None, type=str)
ap.add_argument('-H', '--hostname', default='localhost', type=str)
ap.add_argument('-D', '--duration', default=10, type=int,
                help="Duration of run (in seconds)")

ap.add_argument('--ksize', default=12, type=int,
                help="Key size to use")

ap.add_argument('--vsize', default=128, type=int,
                help="Value size to use")
ap.add_argument('--iops', default=None, type=str,
                help="Use Pure-Python IOPS plugin")
ap.add_argument('-g', '--global-instance',
                help="Use global instance", default=False,
                action='store_true')
ap.add_argument('--batch', '-N', type=int, help="Batch size", default=1)

options = ap.parse_args()

GLOBAL_INSTANCE = None
CONN_OPTIONS = {
    "bucket": options.bucket,
    "host": options.hostname
}

GLOBAL_INSTANCE = Connection(**CONN_OPTIONS)

def make_instance():
    if options.global_instance:
        return GLOBAL_INSTANCE
    else:
        return Connection(**CONN_OPTIONS)

class Worker(object):
    def __init__(self):
        self.delay = options.delay
        self.key = 'K' * options.ksize
        self.value = b'V' * options.vsize
        self.kv = {}
        for x in range(options.batch):
            self.kv[self.key + str(x)] = self.value

        self.wait_time = 0
        self.opcount = 0

    def run(self, *args, **kwargs):
        self.end_time = time() + options.duration
        cb = make_instance()

        while time() < self.end_time:
            begin_time = time()
            rv = cb.set_multi(self.kv, format=FMT_BYTES)
            assert rv.all_ok, "Operation failed: "
            self.wait_time += time() - begin_time
            self.opcount += options.batch

global_begin = None
gthreads = []
worker_threads = []
for x in range(options.threads):
    w = Worker()
    worker_threads.append(w)
    t = gevent.spawn(w.run)
    gthreads.append(t)

global_begin = time()
for t in gthreads:
    t.join()

global_duration = time() - global_begin
total_ops = sum([w.opcount for w in worker_threads])
total_time = 0
for t in worker_threads:
    total_time += t.wait_time

print("Total run took an absolute time of %0.2f seconds" % (global_duration,))
print("Did a total of %d operations" % (total_ops,))
print("Total wait time of %0.2f seconds" % (total_time,))
print("[WAIT] %0.2f ops/second" % (float(total_ops)/float(total_time),))
print("[ABS] %0.2f ops/second" % (float(total_ops)/float(global_duration),))

########NEW FILE########
__FILENAME__ = iops_demo
#!/usr/bin/env python
import gevent
import gevent.monkey; gevent.monkey.patch_all()
import sys

from couchbase import Couchbase

def test(x):
    c = Couchbase.connect(bucket='default', experimental_gevent_support=True)
    c.set("tmp-" + str(x), 1)
    sys.stdout.write(str(x) + " ")
    sys.stdout.flush()

print("Gevent starting..")
gevent.joinall([gevent.spawn(test, x) for x in xrange(100)])
print("")

########NEW FILE########
__FILENAME__ = item
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from couchbase.items import Item, ItemSequence
from couchbase import Couchbase
from pprint import pprint
from random import randint

class Player(Item):
    def __init__(self, name, create_structure=False):
        super(Player, self).__init__(name)
        if create_structure:
            self.value = {
                'email': None,
                'score': 0,
                'games': []
            }

    @classmethod
    def create(cls, name, email, cb):
        """
        Create the basic structure of a player
        """
        it = cls(name, create_structure=True)
        it.value['email'] = email

        # In an actual application you'd probably want to use 'add',
        # but since this app might be run multiple times, you don't
        # want to get KeyExistsError
        cb.set_multi(ItemSequence([it]))
        return it

    @classmethod
    def load(cls, name, cb):
        it = Player(name)
        cb.get_multi(ItemSequence([it]))
        return it

    def save(self, cb):
        cb.replace_multi(ItemSequence([self]))

    @property
    def name(self):
        return self.key

    @property
    def score(self):
        return self.value['score']

    @score.setter
    def score(self, value):
        self.value['score'] = value

    @property
    def games(self):
        return self.value['games']

    @property
    def email(self):
        return self.value['email']
    @email.setter
    def email(self, value):
        self.value['email'] = value

cb = Couchbase.connect(bucket='default')
single_player = Player.create("bob", "bob@bobnob.com", cb)
single_player.score += 100
single_player.save(cb)

# Let's try multiple players
players = ItemSequence([Player(x, create_structure=True)
           for x in ("joe", "jim", "bill", "larry")])

# Save them all
cb.set_multi(players)

# Give them all some points
for p, options in players:
    p.score += randint(20, 2000)
    # also set the email?
    if not p.email:
        p.email = "{0}@{0}.notspecified.com".format(p.name)

cb.replace_multi(players)
all_players = ItemSequence([x[0] for x in players] + [single_player])

INDENT = " " * 3
for player in all_players.sequence:
    print "Name:", player.name
    print INDENT , player

    lines = []
    lines.append("email: {0}".format(player.email))
    lines.append("score: {0}".format(player.score))

    for line in lines:
        print INDENT, line

cb.delete_multi(all_players)
cb.endure_multi(all_players, check_removed=True, replicate_to=0,
                persist_to=1)

########NEW FILE########
__FILENAME__ = reversed_keys
#!/usr/bin/env python

from couchbase.transcoder import Transcoder
from couchbase.connection import Connection


class ReverseTranscoder(Transcoder):
    def encode_key(self, key):
        return super(ReverseTranscoder, self).encode_key(key[::-1])

    def decode_key(self, key):
        key = super(ReverseTranscoder, self).decode_key(key)
        return key[::-1]


c_reversed = Connection(bucket='default', transcoder=ReverseTranscoder())
c_plain = Connection(bucket='default')

c_plain.delete_multi(('ABC', 'CBA', 'XYZ', 'ZYX'), quiet=True)

c_reversed.set("ABC", "This is a reversed key")

rv = c_plain.get("CBA")
print("Got value for reversed key '{0}'".format(rv.value))

rv = c_reversed.get("ABC")
print("Got value for reversed key '{0}' again".format(rv.value))

c_plain.set("ZYX", "This is really ZYX")

rv = c_reversed.get("XYZ")
print("Got value for '{0}': '{1}'".format(rv.key, rv.value))

########NEW FILE########
__FILENAME__ = search_keywords
#!/usr/bin/env python

#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# This file demonstrates some of the functionalities available with
# view queries. This creates a bunch of key-value pairs where the value is
# a number. It also creates a view to index the key-value pairs by the
# number itself, and finally queries the view to return the ten items with
# the highest values.

from argparse import ArgumentParser
import random
import pprint

from couchbase.connection import Connection

ap = ArgumentParser()

ap.add_argument('-D', '--create-design', default=False,
                action='store_true',
                help='whether to create the design')

ap.add_argument('-n', '--number-of-terms', default=10,
                type=int, help="How many terms to generate")

options = ap.parse_args()

c = Connection(bucket='default')

DESIGN = {
    '_id': '_design/search_keywords',
    'language': 'javascript',
    'views': {
        'top_keywords': {
            'map':
            """
            function(doc) {
                if (typeof doc === 'number') {
                    emit(doc, null);
                }
            }
            """
        }
    }
}

if options.create_design:
    c.design_create('search_keywords',
                    DESIGN,
                    use_devmode=False,
                    syncwait=5)

NOUNS = ['cow', 'cat', 'dog', 'computer', 'WMD']
ADJECTIVES = ['happy', 'sad', 'thoughtful', 'extroverted']

kv = {}

for x in range(options.number_of_terms):
    n = random.choice(NOUNS)
    a = random.choice(ADJECTIVES)
    kv[" ".join([a, n])] = random.randint(1, 100000)

c.set_multi(kv)

vret = c.query('search_keywords',
               'top_keywords',
               limit=10,
               descending=True)

for row in vret:
    pprint.pprint(row, indent=4)

# Sample output:
#[   {   u'id': u'WMD sad', u'key': 92772, u'value': None},
#    {   u'id': u'WMD thoughtful', u'key': 76222, u'value': None},
#    {   u'id': u'cow happy', u'key': 71984, u'value': None},
#    {   u'id': u'computer sad', u'key': 68849, u'value': None},
#    {   u'id': u'cat thoughtful', u'key': 68417, u'value': None},
#    {   u'id': u'computer thoughtful', u'key': 67518, u'value': None},
#    {   u'id': u'dog thoughtful', u'key': 67350, u'value': None},
#    {   u'id': u'computer extroverted', u'key': 63279, u'value': None},
#    {   u'id': u'cow thoughtful', u'key': 60962, u'value': None},
#    {   u'id': u'cow sad', u'key': 49510, u'value': None}]

########NEW FILE########
__FILENAME__ = twist-sample
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, Deferred

from txcouchbase.connection import Connection

class MyClient(object):
    def __init__(self):
        self.cb = Connection(bucket='default')
        self.do_set()

    def on_op_error(self, msg):
        print "Got operation error!" + str(msg)

    def do_set(self):
        self.cb.set("foo", "bar").addCallback(self.on_set)

    def on_set(self, res):
        print res
        self.cb.get("foo").addCallback(self.on_get)

    def on_get(self, res):
        print res

@inlineCallbacks
def run_sync_example():
    cb = Connection(bucket='default')
    rv_set = yield cb.set("foo", "bar")
    print rv_set
    rv_get = yield cb.get("foo")
    print rv_get

cb = MyClient()
run_sync_example()
reactor.run()

########NEW FILE########
__FILENAME__ = txbasic
from twisted.internet import reactor

from txcouchbase.connection import Connection as TxCouchbase

cb = TxCouchbase(bucket='default')
def on_set(ret):
    print("Set key. Result", ret)

def on_get(ret):
    print("Got key. Result", ret)
    reactor.stop()

cb.set("key", "value").addCallback(on_set)
cb.get("key").addCallback(on_get)
reactor.run()

########NEW FILE########
__FILENAME__ = txbench
#!/usr/bin/env python
#
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import argparse
from time import time

from twisted.internet import reactor

from txcouchbase.connection import Connection, TxAsyncConnection
from couchbase.connection import FMT_BYTES
from couchbase.transcoder import Transcoder

ap = argparse.ArgumentParser()

ap.add_argument('-t', '--threads', default=4, type=int,
                help="Number of threads to spawn. 0 means no threads "
                "but workload will still run in the main thread")

ap.add_argument('-d', '--delay', default=0, type=float,
                help="Number of seconds to wait between each op. "
                "may be a fraction")

ap.add_argument('-C', '--clients', default=1, type=int,
                help="Number of clients (nthreads are per-client)")

ap.add_argument('--deferreds', action='store_true', default=False,
                help="Whether to use Deferreds (or normal callbacks)")

ap.add_argument('-b', '--bucket', default='default', type=str)
ap.add_argument('-p', '--password', default=None, type=str)
ap.add_argument('-H', '--hostname', default='localhost', type=str)
ap.add_argument('-D', '--duration', default=10, type=int,
                help="Duration of run (in seconds)")

ap.add_argument('-T', '--transcoder', default=False,
                action='store_true',
                help="Use the Transcoder object rather than built-in "
                "conversion routines")

ap.add_argument('--ksize', default=12, type=int,
                help="Key size to use")

ap.add_argument('--vsize', default=128, type=int,
                help="Value size to use")

ap.add_argument('--batch', '-N', type=int, default=1, help="Batch size to use")

options = ap.parse_args()

class Runner(object):
    def __init__(self, cb):
        self.cb = cb
        self.delay = options.delay
        self.key = 'K' * options.ksize
        self.value = b'V' * options.vsize
        self.kv = {}
        for x in range(options.batch):
            self.kv[self.key + str(x)] = self.value
        self.wait_time = 0
        self.opcount = 0
        self.end_time = time() + options.duration
        self._do_stop = False
        self.start()

    def _schedule_raw(self, *args):
        opres = self.cb.set(self.key, self.value, format=FMT_BYTES)
        opres.callback = self._schedule_raw
        self.opcount += 1

    def _schedule_deferred(self, *args):
        rv = self.cb.setMulti(self.kv, format=FMT_BYTES)
        rv.addCallback(self._schedule_deferred)
        self.opcount += options.batch

    def start(self):
        if options.deferreds:
            self._schedule_deferred()
        else:
            self.cb._async_raw = True
            self._schedule_raw()

    def stop(self):
        self._do_stop = True

global_begin = time()
runners = []
clients = []
kwargs = {
    'bucket': options.bucket,
    'host': options.hostname,
    'password': options.password,
    'unlock_gil': False
}
if options.transcoder:
    kwargs['transcoder'] = Transcoder()

for _ in range(options.clients):
    if options.deferreds:
        cb = Connection(**kwargs)
    else:
        cb = TxAsyncConnection(**kwargs)

    clients.append(cb)
    d = cb.connect()

    def _on_connected(unused, client):
        for _ in range(options.threads):
            r = Runner(client)
            runners.append(r)
    d.addCallback(_on_connected, cb)

def stop_all():
    [r.stop() for r in runners]
    reactor.stop()

reactor.callLater(options.duration, stop_all)
reactor.run()


global_duration = time() - global_begin
total_ops = sum([r.opcount for r in runners])
total_time = 0
for r in runners:
    total_time += r.wait_time

print("Total run took an absolute time of %0.2f seconds" % (global_duration,))
print("Did a total of %d operations" % (total_ops,))
print("[ABS] %0.2f ops/second" % (float(total_ops)/float(global_duration),))

########NEW FILE########
__FILENAME__ = txview
from twisted.internet import reactor

from txcouchbase.connection import Connection

def on_view_rows(res):
    for row in res:
        print "Got row", row.key

cb = Connection(bucket='beer-sample')
d = cb.queryAll("beer", "brewery_beers", limit=20)
d.addCallback(on_view_rows)
reactor.run()

########NEW FILE########
__FILENAME__ = connection
from collections import deque

from gevent.event import AsyncResult, Event
from gevent.hub import get_hub, getcurrent, Waiter

from couchbase.async.connection import Async
from couchbase.async.view import AsyncViewBase
from couchbase.views.iterator import AlreadyQueriedError
try:
    from gcouchbase.iops_gevent0x import IOPS
except ImportError:
    from gcouchbase.iops_gevent10 import IOPS

class GView(AsyncViewBase):
    def __init__(self, *args, **kwargs):
        """
        Subclass of :class:`~couchbase.async.view.AsyncViewBase`
        This doesn't expose an API different from the normal synchronous
        view API. It's just implemented differently
        """
        super(GView, self).__init__(*args, **kwargs)

        # We use __double_underscore to mangle names. This is because
        # the views class has quite a bit of data attached to it.
        self.__waiter = Waiter()
        self.__iterbufs = deque()
        self.__done_called = False

    def raise_include_docs(self):
        # We allow include_docs in the RowProcessor
        pass

    def _callback(self, *args):
        # Here we need to make sure the callback is invoked
        # from within the context of the calling greenlet. Since
        # we're invoked from the hub, we will need to issue more
        # blocking calls and thus ensure we're not doing the processing
        # from here.
        self.__waiter.switch(args)

    def on_rows(self, rows):
        self.__iterbufs.appendleft(rows)

    def on_error(self, ex):
        raise ex

    def on_done(self):
        self.__done_called = True

    def __wait_rows(self):
        """
        Called when we need more data..
        """
        args = self.__waiter.get()
        super(GView, self)._callback(*args)

    def __iter__(self):
        if not self._do_iter:
            raise AlreadyQueriedError.pyexc("Already queried")

        while self._do_iter and not self.__done_called:
            self.__wait_rows()
            while len(self.__iterbufs):
                ri = self.__iterbufs.pop()
                for r in ri:
                    yield r

        self._do_iter = False

class GConnection(Async):
    def __init__(self, *args, **kwargs):
        """
        This class is a 'GEvent'-optimized subclass of libcouchbase
        which utilizes the underlying IOPS structures and the gevent
        event primitives to efficiently utilize couroutine switching.
        """
        super(GConnection, self).__init__(IOPS(), *args, **kwargs)

    def _do_ctor_connect(self):
        if self.connected:
            return

        self._connect()
        self._evconn = AsyncResult()
        self._conncb = self._on_connected
        self._evconn.get()
        self._evconn = None

    def _on_connected(self, err):
        if err:
            self._evconn.set_exception(err)
        else:
            self._evconn.set(None)

    def _waitwrap(self, cbasync):
        cur_thread = getcurrent()
        cbasync.callback = cur_thread.switch
        cbasync.errback = lambda r, x, y, z: cur_thread.throw(x, y, z)

        return get_hub().switch()

    def _meth_factory(meth, name):
        def ret(self, *args, **kwargs):
            return self._waitwrap(meth(self, *args, **kwargs))
        return ret

    def _http_request(self, **kwargs):
        res = super(GConnection, self)._http_request(**kwargs)
        if kwargs.get('chunked', False):
            return res #views

        e = Event()
        res._callback = lambda x, y: e.set()

        e.wait()

        res._maybe_raise()
        return res

    def query(self, *args, **kwargs):
        kwargs['itercls'] = GView
        ret = super(GConnection, self).query(*args, **kwargs)
        ret.start()
        return ret

    locals().update(Async._gen_memd_wrappers(_meth_factory))

########NEW FILE########
__FILENAME__ = iops_gevent0x
from gevent.core import event as LibeventEvent
from gevent.core import timer as LibeventTimer
from gevent.core import EV_READ, EV_WRITE

from couchbase.iops.base import (
    IOEvent, TimerEvent,
    LCB_READ_EVENT, LCB_WRITE_EVENT, LCB_RW_EVENT,
    PYCBC_EVACTION_WATCH, PYCBC_EVACTION_UNWATCH
)

EVENTMAP = {
    LCB_READ_EVENT: EV_READ,
    LCB_WRITE_EVENT: EV_WRITE,
    LCB_RW_EVENT: EV_READ|EV_WRITE
}

REVERSERMAP = {
    EV_READ: LCB_READ_EVENT,
    EV_WRITE: LCB_WRITE_EVENT,
    EV_READ|EV_WRITE: LCB_RW_EVENT
}

class GeventIOEvent(IOEvent):
    def __init__(self):
        super(GeventIOEvent, self).__init__()
        self.ev = None
        self._last_events = -1

    def _ready_pre(self, unused, flags):
        self.update(self.flags)
        lcbflags = REVERSERMAP[flags]
        self.ready(lcbflags)

    def update(self, flags):
        if not self.ev:
            self.ev = LibeventEvent(flags, self.fd, self._ready_pre)

        if self._last_events != self.ev.events:
            self.ev.cancel()
            # DANGER: this relies on the implementation details of the
            # cython-level class.
            LibeventEvent.__init__(self.ev, flags, self.fd, self._ready_pre)

        self.ev.add()

    def cancel(self):
        if not self.ev:
            return
        self.ev.cancel()

class GeventTimer(TimerEvent):
    def __init__(self):
        super(GeventTimer, self).__init__()
        self._tmev = LibeventTimer(0, lambda: self.ready(0))
        self._tmev.cancel()

    def reset(self, usecs):
        self._tmev.add(usecs / 1000000)

    def cancel(self):
        self._tmev.cancel()

class IOPS(object):
    def update_event(self, event, action, flags):
        if action == PYCBC_EVACTION_WATCH:
            event.update(EVENTMAP[flags])

        elif action == PYCBC_EVACTION_UNWATCH:
            event.cancel()

    def update_timer(self, event, action, usecs):
        if action == PYCBC_EVACTION_WATCH:
            event.reset(usecs)
        else:
            event.cancel()

    def start_watching(self):
        pass

    def stop_watching(self):
        pass

    def io_event_factory(self):
        return GeventIOEvent()

    def timer_event_factory(self):
        return GeventTimer()

########NEW FILE########
__FILENAME__ = iops_gevent10
from gevent.hub import get_hub
from gevent.core import timer as _PyxTimer
from time import time

from couchbase.iops.base import (
    IOEvent, TimerEvent,
    LCB_READ_EVENT, LCB_WRITE_EVENT, LCB_RW_EVENT,
    PYCBC_EVACTION_WATCH, PYCBC_EVACTION_UNWATCH
)

from couchbase.iops.base import (
    IOEvent, TimerEvent,
    LCB_READ_EVENT, LCB_WRITE_EVENT, LCB_RW_EVENT,
    PYCBC_EVACTION_WATCH, PYCBC_EVACTION_UNWATCH
)

EVENTMAP = {
    LCB_READ_EVENT: 1,
    LCB_WRITE_EVENT: 2,
    LCB_RW_EVENT: 3
}

REVERSERMAP = {
    1: LCB_READ_EVENT,
    2: LCB_WRITE_EVENT,
    3: LCB_RW_EVENT
}

class GEventIOEvent(IOEvent):
    def __init__(self):
        self.ev = get_hub().loop.io(0,0)

    def ready_proxy(self, event):
        self.ready(REVERSERMAP[event])

    def watch(self, events):
        self.ev.stop()
        self.ev.fd = self.fd
        self.ev.events = events

        self.ev.start(self.ready_proxy, pass_events=True)

class GEventTimer(TimerEvent):
    def __init__(self):
        self.ev = get_hub().loop.timer(0)

    def ready_proxy(self, *args):
        self.ready(0)

    def schedule(self, usecs):
        seconds = usecs / 1000000
        # This isn't the "clean" way, but it's much quicker.. and
        # since we're already using undocumented APIs, why not..
        _PyxTimer.__init__(self.ev, get_hub().loop, seconds)
        self.ev.start(self.ready_proxy, 0)


class IOPS(object):
    def update_event(self, event, action, flags):
        if action == PYCBC_EVACTION_UNWATCH:
            event.ev.stop()
            return

        elif action == PYCBC_EVACTION_WATCH:
            ev_event = EVENTMAP[flags]
            event.watch(ev_event)

    def update_timer(self, event, action, usecs):
        if action == PYCBC_EVACTION_UNWATCH:
            event.ev.stop()
            return

        elif action == PYCBC_EVACTION_WATCH:
            event.schedule(usecs)

    def start_watching(self):
        pass

    def stop_watching(self):
        pass

    def io_event_factory(self):
        return GEventIOEvent()

    def timer_event_factory(self):
        return GEventTimer()

########NEW FILE########
__FILENAME__ = test_api
from couchbase.tests.base import ApiImplementationMixin, SkipTest
try:
    import gevent
except ImportError as e:
    raise SkipTest(e)

from gcouchbase.connection import GConnection, GView
from couchbase.tests.importer import get_configured_classes

class GEventImplMixin(ApiImplementationMixin):
    factory = GConnection
    viewfactor = GView
    should_check_refcount = False


skiplist = ('ConnectionIopsTest', 'LockmodeTest', 'ConnectionPipelineTest')

configured_classes = get_configured_classes(GEventImplMixin,
                                            skiplist=skiplist)
globals().update(configured_classes)

########NEW FILE########
__FILENAME__ = connection
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
This file contains the twisted-specific bits for the Couchbase client.
"""

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from couchbase.async.connection import Async
from couchbase.async.view import AsyncViewBase
from couchbase.async.events import EventQueue
from couchbase.exceptions import CouchbaseError
from txcouchbase.iops import v0Iops

class BatchedView(AsyncViewBase):
    def __init__(self, *args, **kwargs):
        """
        Iterator/Container object for a single-call view result.

        This functions as an iterator over all results of the query, once the
        query has been completed.

        Additional metadata may be obtained by examining the object. See
        :class:`~couchbase.views.iterator.Views` for more details.

        You will normally not need to construct this object manually.
        """
        super(BatchedView, self).__init__(*args, **kwargs)
        self._d = Deferred()
        self.__rows = None # likely a superlcass might have this?

    def _getDeferred(self):
        return self._d

    def start(self):
        super(BatchedView, self).start()
        self.raw.rows_per_call = -1
        return self

    def on_rows(self, rowiter):
        """
        Reimplemented from :meth:`~AsyncViewBase.on_rows`
        """
        self.__rows = rowiter
        self._d.callback(self)
        self._d = None

    def on_error(self, ex):
        """
        Reimplemented from :meth:`~AsyncViewBase.on_error`
        """
        if self._d:
            self._d.errback()
            self._d = None

    def on_done(self):
        """
        Reimplemented from :meth:`~AsyncViewBase.on_done`
        """
        if self._d:
            self._d.callback(self)
            self._d = None

    def __iter__(self):
        """
        Iterate over the rows in this resultset
        """
        return self.__rows


class TxEventQueue(EventQueue):
    """
    Subclass of EventQueue. This implements the relevant firing methods,
    treating an 'Event' as a 'Deferred'
    """
    def fire_async(self, event):
        reactor.callLater(0, event.callback, None)

    def call_single_success(self, event, *args, **kwargs):
        event.callback(None)

    def call_single_failure(self, event, *args, **kwargs):
        event.errback(None)

class ConnectionEventQueue(TxEventQueue):
    """
    For events fired upon connect
    """
    def maybe_raise(self, err, *args, **kwargs):
        if not err:
            return
        raise err

class TxAsyncConnection(Async):
    def __init__(self, **kwargs):
        """
        Connection subclass for Twisted. This inherits from the 'Async' class,
        but also adds some twisted-specific logic for hooking on a connection.
        """

        iops = v0Iops(reactor)
        super(TxAsyncConnection, self).__init__(iops=iops, **kwargs)

        self._evq = {
            'connect': ConnectionEventQueue(),
            '_dtor': TxEventQueue()
        }

        self._conncb = self._evq['connect']
        self._dtorcb = self._evq['_dtor']

    def registerDeferred(self, event, d):
        """
        Register a defer to be fired at the firing of a specific event.

        :param string event: Currently supported values are `connect`. Another
          value may be `_dtor` which will register an event to fire when this
          object has been completely destroyed.

        :param event: The defered to fire when the event succeeds or failes
        :type event: :class:`Deferred`

        If this event has already fired, the deferred will be triggered
        asynchronously.

        Example::

          def on_connect(*args):
              print("I'm connected")
          def on_connect_err(*args):
              print("Connection failed")

          d = Deferred()
          cb.registerDeferred('connect', d)
          d.addCallback(on_connect)
          d.addErrback(on_connect_err)

        :raise: :exc:`ValueError` if the event name is unrecognized
        """
        try:
            self._evq[event].schedule(d)
        except KeyError:
            raise ValueError("No such event type", event)

    def connect(self):
        """
        Short-hand for the following idiom::

            d = Deferred()
            cb.registerDeferred('connect', d)
            return d

        :return: A :class:`Deferred`
        """
        d = Deferred()
        self.registerDeferred('connect', d)
        return d

    def defer(self, opres):
        """
        Converts a raw :class:`couchbase.results.AsyncResult` object
        into a :class:`Deferred`.

        This is shorthand for the following "non-idiom"::

          d = Deferred()
          opres = cb.set("foo", "bar")
          opres.callback = d.callback

          def d_err(res, ex_type, ex_val, ex_tb):
              d.errback(opres, ex_type, ex_val, ex_tb)

          opres.errback = d_err
          return d

        :param opres: The operation to wrap
        :type opres: :class:`couchbase.results.AsyncResult`

        :return: a :class:`Deferred` object.

        Example::

          opres = cb.set("foo", "bar")
          d = cb.defer(opres)
          def on_ok(res):
              print("Result OK. Cas: {0}".format(res.cas))
          d.addCallback(opres)


        """
        d = Deferred()
        opres.callback = d.callback

        def _on_err(mres, ex_type, ex_val, ex_tb):
            try:
                raise ex_type(ex_val)
            except CouchbaseError:
                d.errback()
        opres.errback = _on_err
        return d

    def queryEx(self, viewcls, *args, **kwargs):
        """
        Query a view, with the ``viewcls`` instance receiving events
        of the query as they arrive.

        :param type viewcls: A class (derived from :class:`AsyncViewBase`)
          to instantiate

        Other arguments are passed to the standard `query` method.

        This functions exactly like the :meth:`~couchbase.async.Connection.query`
        method, except it automatically schedules operations if the connection
        has not yet been negotiated.
        """

        kwargs['itercls'] = viewcls
        o = super(TxAsyncConnection, self).query(*args, **kwargs)
        if not self.connected:
            self.connect().addCallback(lambda x: o.start())
        else:
            o.start()

        return o

    def queryAll(self, *args, **kwargs):
        """
        Returns a :class:`Deferred` object which will have its callback invoked
        with a :class:`BatchedView` when the results are complete.

        Parameters follow conventions of
        :meth:`~couchbase.connection.Connection.query`.

        Example::

          d = cb.queryAll("beer", "brewery_beers")
          def on_all_rows(rows):
              for row in rows:
                 print("Got row {0}".format(row))

          d.addCallback(on_all_rows)

        """

        if not self.connected:
            cb = lambda x: self.queryAll(*args, **kwargs)
            return self.connect().addCallback(cb)

        kwargs['itercls'] = BatchedView
        o = super(TxAsyncConnection, self).query(*args, **kwargs)
        o.start()
        return o._getDeferred()


class Connection(TxAsyncConnection):
    def __init__(self, *args, **kwargs):
        """
        This class inherits from :class:`TxAsyncConnection`.
        In addition to the connection methods, this class' data access methods
        return :class:`Deferreds` instead of :class:`AsyncResult` objects.

        Operations such as :meth:`get` or :meth:`set` will invoke the
        :attr:`Deferred.callback` with the result object when the result is
        complete, or they will invoke the :attr:`Deferred.errback` with an
        exception (or :class:`Failure`) in case of an error. The rules of the
        :attr:`~couchbase.connection.Connection.quiet` attribute for raising
        exceptions apply to the invocation of the ``errback``. This means that
        in the case where the synchronous client would raise an exception,
        the Deferred API will have its ``errback`` invoked. Otherwise, the
        result's :attr:`~couchbase.result.Result.success` field should be
        inspected.


        Likewise multi operations will be invoked with a
        :class:`~couchbase.result.MultiResult` compatible object.

        Some examples:

        Using single items::

          d_set = cb.set("foo", "bar")
          d_get = cb.get("foo")

          def on_err_common(*args):
              print("Got an error: {0}".format(args)),
          def on_set_ok(res):
              print("Successfuly set key with CAS {0}".format(res.cas))
          def on_get_ok(res):
              print("Successfuly got key with value {0}".format(res.value))

          d_set.addCallback(on_set_ok).addErrback(on_err_common)
          d_get.addCallback(on_get_ok).addErrback(on_get_common)

          # Note that it is safe to do this as operations performed on the
          # same key are *always* performed in the order they were scheduled.

        Using multiple items::

          d_get = cb.get_multi(("Foo", "bar", "baz))
          def on_mres(mres):
              for k, v in mres.items():
                  print("Got result for key {0}: {1}".format(k, v.value))
          d.addCallback(mres)

        """
        super(Connection, self).__init__(*args, **kwargs)

    def _connectSchedule(self, f, meth, *args, **kwargs):
        qop = Deferred()
        qop.addCallback(lambda x: f(meth, *args, **kwargs))
        self._evq['connect'].schedule(qop)
        return qop

    def _wrap(self, meth, *args, **kwargs):
        """
        Calls a given method with the appropriate arguments, or defers such
        a call until the instance has been connected
        """
        if not self.connected:
            return self._connectSchedule(self._wrap, meth, *args, **kwargs)

        opres = meth(self, *args, **kwargs)
        return self.defer(opres)


    ### Generate the methods
    def _meth_factory(meth, name):
        def ret(self, *args, **kwargs):
            return self._wrap(meth, *args, **kwargs)
        return ret

    locals().update(TxAsyncConnection._gen_memd_wrappers(_meth_factory))
    for x in TxAsyncConnection._MEMCACHED_OPERATIONS:
        if locals().get(x+'_multi', None):
            locals().update({x+"Multi": locals()[x+"_multi"]})

########NEW FILE########
__FILENAME__ = iops
from twisted.internet import error as TxErrors

import couchbase._libcouchbase as LCB
from couchbase._libcouchbase import (
    Event, TimerEvent, IOEvent,
    LCB_READ_EVENT, LCB_WRITE_EVENT, LCB_RW_EVENT,
    PYCBC_EVSTATE_ACTIVE,
    PYCBC_EVACTION_WATCH,
    PYCBC_EVACTION_UNWATCH,
    PYCBC_EVACTION_CLEANUP
)

class TxIOEvent(IOEvent):
    """
    IOEvent is a class implemented in C. It exposes
    a 'fileno()' method, so we don't have to.
    """
    __slots__ = []

    def __init__(self):
        super(TxIOEvent, self).__init__()

    def doRead(self):
        self.ready_r()

    def doWrite(self):
        self.ready_w()

    def connectionLost(self, reason):
        if self.state == PYCBC_EVSTATE_ACTIVE:
            self.ready_w()

    def logPrefix(self):
        return "Couchbase IOEvent"


class TxTimer(TimerEvent):
    __slots__ = ['_txev', 'lcb_active']

    def __init__(self):
        self.lcb_active = False
        self._txev = None


    def _timer_wrap(self):
        if not self.lcb_active:
            return

        self.ready(0)
        self.lcb_active = False


    def schedule(self, usecs, reactor):
        nsecs = usecs / 1000000
        if not self._txev or not self._txev.active():
            self._txev = reactor.callLater(nsecs, self._timer_wrap)
        else:
            self._txev.reset(nsecs)

        self.lcb_active = True

    def cancel(self):
        self.lcb_active = False

    def cleanup(self):
        if not self._txev:
            return

        try:
            self._txev.cancel()
        except (TxErrors.AlreadyCalled, TxErrors.AlreadyCancelled):
            pass

        self._txev = None


class v0Iops(object):
    """
    IOPS Implementation to be used with Twisted's "FD" based reactors
    """

    __slots__ = [ 'reactor', 'is_sync', '_stop' ]

    def __init__(self, reactor, is_sync=False):
        self.reactor = reactor
        self.is_sync = is_sync
        self._stop = False

    def update_event(self, event, action, flags):
        """
        Called by libcouchbase to add/remove event watchers
        """
        if action == PYCBC_EVACTION_UNWATCH:
            if event.flags & LCB_READ_EVENT:
                self.reactor.removeReader(event)
            if event.flags & LCB_WRITE_EVENT:
                self.reactor.removeWriter(event)

        elif action == PYCBC_EVACTION_WATCH:
            if flags & LCB_READ_EVENT:
                self.reactor.addReader(event)
            if flags & LCB_WRITE_EVENT:
                self.reactor.addWriter(event)

            if flags & LCB_READ_EVENT == 0:
                self.reactor.removeReader(event)
            if flags & LCB_WRITE_EVENT == 0:
                self.reactor.removeWriter(event)

    def update_timer(self, timer, action, usecs):
        """
        Called by libcouchbase to add/remove timers
        """
        if action == PYCBC_EVACTION_WATCH:
            timer.schedule(usecs, self.reactor)

        elif action == PYCBC_EVACTION_UNWATCH:
            timer.cancel()

        elif action == PYCBC_EVACTION_CLEANUP:
            timer.cleanup()

    def io_event_factory(self):
        return TxIOEvent()

    def timer_event_factory(self):
        return TxTimer()

    def start_watching(self):
        """
        Start/Stop operations. This is a no-op in twisted because
        it's a continuously running async loop
        """
        if not self.is_sync:
            return

        self._stop = False
        while not self._stop:
            self.reactor.doIteration(0)

    def stop_watching(self):
        self._stop = True

########NEW FILE########
__FILENAME__ = base
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from twisted.internet import defer
from twisted.trial.unittest import TestCase

from txcouchbase.connection import Connection
from couchbase.tests.base import ConnectionTestCase

def gen_base(basecls):
    class _TxTestCase(basecls, TestCase):
        def register_cleanup(self, obj):
            d = defer.Deferred()
            obj.registerDeferred('_dtor', d)
            self.addCleanup(lambda x: d, None)

        def make_connection(self, **kwargs):
            ret = super(_TxTestCase, self).make_connection(**kwargs)
            self.register_cleanup(ret)
            return ret

        def checkCbRefcount(self):
            pass

        @property
        def factory(self):
            return Connection

        def setUp(self):
            super(_TxTestCase, self).setUp()
            self.register_cleanup(self.cb)
            self.cb = None

        def tearDown(self):
            super(_TxTestCase, self).tearDown()

    return _TxTestCase

########NEW FILE########
__FILENAME__ = test_ops
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from couchbase.tests.base import ConnectionTestCase

from txcouchbase.tests.base import gen_base
from couchbase.exceptions import NotFoundError
from couchbase.result import (
    Result, OperationResult, ValueResult, MultiResult)


class OperationTestCase(gen_base(ConnectionTestCase)):
    def testSimpleSet(self):
        cb = self.make_connection()
        key = self.gen_key("test_simple_set")
        d = cb.set(key, "simple_Value")
        def t(ret):
            self.assertIsInstance(ret, OperationResult)
            self.assertEqual(ret.key, key)
            del ret

        d.addCallback(t)
        del cb
        return d

    def testSimpleGet(self):
        cb = self.make_connection()
        key = self.gen_key("test_simple_get")
        value = "simple_value"

        cb.set(key, value)
        d_get = cb.get(key)
        def t(ret):
            self.assertIsInstance(ret, ValueResult)
            self.assertEqual(ret.key, key)
            self.assertEqual(ret.value, value)

        d_get.addCallback(t)
        return d_get

    def testMultiSet(self):
        cb = self.make_connection()
        kvs = self.gen_kv_dict(prefix="test_multi_set")
        d_set = cb.setMulti(kvs)

        def t(ret):
            self.assertEqual(len(ret), len(kvs))
            self.assertEqual(ret.keys(), kvs.keys())
            self.assertTrue(ret.all_ok)
            for k in kvs:
                self.assertEqual(ret[k].key, k)
                self.assertTrue(ret[k].success)

            del ret

        d_set.addCallback(t)
        return d_set

    def testSingleError(self):
        cb = self.make_connection()
        key = self.gen_key("test_single_error")

        d_del = cb.delete(key, quiet=True)

        d = cb.get(key, quiet=False)
        def t(err):
            self.assertIsInstance(err.value, NotFoundError)
            return True

        d.addCallback(lambda x: self.assertTrue(False))
        d.addErrback(t)
        return d

    def testMultiErrors(self):
        cb = self.make_connection()
        kv = self.gen_kv_dict(prefix = "test_multi_errors")
        cb.setMulti(kv)

        rmkey = kv.keys()[0]
        cb.delete(rmkey)

        d = cb.getMulti(kv.keys())

        def t(err):
            self.assertIsInstance(err.value, NotFoundError)
            all_results = err.value.all_results
            for k, v in kv.items():
                self.assertTrue(k in all_results)
                res = all_results[k]
                self.assertEqual(res.key, k)
                if k != rmkey:
                    self.assertTrue(res.success)
                    self.assertEqual(res.value, v)

            res_fail = err.value.result
            self.assertFalse(res_fail.success)
            self.assertTrue(NotFoundError._can_derive(res_fail.rc))

        d.addErrback(t)
        return d

########NEW FILE########
__FILENAME__ = test_txconn
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from twisted.internet import reactor, defer
from couchbase.exceptions import (
    BucketNotFoundError,
    ObjectDestroyedError)

from couchbase.tests.base import ConnectionTestCase
from txcouchbase.tests.base import gen_base

class BasicConnectionTest(gen_base(ConnectionTestCase)):
    def testConnectionSuccess(self):
        cb = self.make_connection()
        d = cb.connect()
        d.addCallback(lambda x: self.assertTrue(cb.connected))
        return d

    def testConnectionFailure(self):
        cb = self.make_connection(bucket='blahblah')
        d = cb.connect()
        d.addCallback(lambda x: x, cb)
        return self.assertFailure(d, BucketNotFoundError)

    def testBadEvent(self):
        cb = self.make_connection()
        self.assertRaises(ValueError, cb.registerDeferred,
                          'blah',
                          defer.Deferred())

        d = defer.Deferred()
        cb.registerDeferred('connect', d)
        d.addBoth(lambda x: None)
        return d

    def testMultiHost(self):
        info = self.cluster_info
        hostlist = [(info.host, 10), info.host]

        cb = self.make_connection(host=hostlist)
        d = cb.connect()
        d.addCallback(lambda x: self.assertTrue(cb.connected))
        return d

    def testConnectionDestroyed(self):
        cb = self.make_connection()
        d = cb.connect()
        self.assertFailure(d, ObjectDestroyedError)
        return d

########NEW FILE########
__FILENAME__ = test_views
# Copyright 2013, Couchbase, Inc.
# All Rights Reserved
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from twisted.internet import defer

from txcouchbase.connection import BatchedView
from couchbase.exceptions import HTTPError, ArgumentError
from couchbase.async.view import AsyncViewBase

from couchbase.tests.base import ViewTestCase
from txcouchbase.tests.base import gen_base

class RowsHandler(AsyncViewBase):
    def __init__(self, *args, **kwargs):
        super(RowsHandler, self).__init__(*args, **kwargs)
        self._rows_received = 0
        self._done_called = False
        self._call_count = 0
        self._cached_ex = None

    def on_rows(self, rows):
        l = list(rows)
        self._rows_received += len(l)
        self._call_count += 1

    def on_done(self):
        self._done_called = True
        self._d.callback(None)

    def on_error(self, ex):
        self._cached_ex = ex
        self._d.errback(ex)


class TxViewsTests(gen_base(ViewTestCase)):
    def make_connection(self, **kwargs):
        return super(TxViewsTests, self).make_connection(bucket='beer-sample')

    def testEmptyView(self):
        cb = self.make_connection()
        return cb.queryAll('beer', 'brewery_beers', limit=0)

    def testLimitView(self):
        cb = self.make_connection()
        d = cb.queryAll('beer', 'brewery_beers', limit=10)

        def _verify(o):
            self.assertIsInstance(o, BatchedView)
            rows = list(o)
            self.assertEqual(len(rows), 10)

        return d.addCallback(_verify)

    def testBadView(self):
        cb = self.make_connection()
        d = cb.queryAll('blah', 'blah_blah')
        self.assertFailure(d, HTTPError)
        return d


    # What happens with 'includeDocs'? this should be interesting
    def testIncludeDocs(self):
        cb = self.make_connection()
        d = cb.queryAll('beer', 'brewery_beers', limit=20, include_docs=True)
        self.assertFailure(d, ArgumentError)



    def testIncrementalRows(self):
        d = defer.Deferred()
        cb = self.make_connection()
        o = cb.queryEx(RowsHandler, 'beer', 'brewery_beers')
        self.assertIsInstance(o, RowsHandler)

        def verify(unused):
            self.assertTrue(o.indexed_rows > 7000)
            self.assertEqual(o._rows_received, o.indexed_rows)

            ## Commented because we can't really verify this now,
            ## can we?
            #self.assertTrue(o._call_count > 1)

        d.addCallback(verify)
        o._d = d
        return d

########NEW FILE########
