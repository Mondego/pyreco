__FILENAME__ = cache
from boto3.core.exceptions import NotCached


class ServiceCache(object):
    """
    A centralized registry of classes that have already been built.

    Present to both prevent too much factory churn as well as to give the
    resource layer something to refer to in relations.

    Usage::

        >>> sc = ServiceCache()
        >>> len(sc)
        0
        >>> sc.set_connection('s3', S3Connection)
        >>> sc.set_resource('s3', 'Bucket', Bucket)
        >>> sc.set_collection('s3', 'BucketCollection', BucketCollection)
        # We only count services.
        >>> len(sc)
        1
        >>> 's3' in sc
        True
        # Later...
        >>> conn_class = sc.get_connection('s3')
        >>> res_class = sc.get_resource('s3', 'Bucket')
        >>> sc.del_resource('s3', 'Bucket')

    """
    # TODO: We may want to add LRU/expiration behavior in the future, to
    #       prevent the cache from taking up too much space.
    #       Unlikely, but potential.
    def __init__(self):
        self.services = {}

    def __str__(self):
        return 'ServiceCache: {0}'.format(
            ', '.join(sorted(self.services.keys()))
        )

    def __len__(self):
        return len(self.services)

    def __contains__(self, service_name):
        return service_name in self.services

    def get_connection(self, service_name):
        """
        Retrieves a connection class from the cache, if available.

        :param service_name: The service a given ``Connection`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :returns: A <boto3.core.connection.Connection> subclass
        """
        service = self.services.get(service_name, {})
        connection_class = service.get('connection', None)

        if not connection_class:
            msg = "Connection for '{0}' is not present in the cache."
            raise NotCached(msg.format(
                service_name
            ))

        return connection_class

    def set_connection(self, service_name, to_cache):
        """
        Sets a connection class within the cache.

        :param service_name: The service a given ``Connection`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param to_cache: The class to be cached for the service.
        :type to_cache: class
        """
        self.services.setdefault(service_name, {})
        self.services[service_name]['connection'] = to_cache

    def del_connection(self, service_name):
        """
        Deletes a connection for a given service.

        Fails silently if no connection is found in the cache.

        :param service_name: The service a given ``Connection`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string
        """
        # Unlike ``get_connection``, this should be fire & forget.
        # We don't really care, as long as it's not in the cache any longer.
        try:
            del self.services[service_name]['connection']
        except KeyError:
            pass

    def build_classpath(self, klass=None):
        if not klass:
            classpath = 'default'
        else:
            classpath = "{0}.{1}".format(
                klass.__module__,
                klass.__name__
            )

        return classpath

    def get_resource(self, service_name, resource_name, base_class=None):
        """
        Retrieves a resource class from the cache, if available.

        :param service_name: The service a given ``Resource`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param resource_name: The name of the ``Resource``. Ex.
            ``Queue``, ``Notification``, ``Table``, etc.
        :type resource_name: string

        :param base_class: (Optional) The base class of the object. Prevents
            "magically" loading the wrong class (one with a different base).
            Default is ``default``.
        :type base_class: class

        :returns: A <boto3.core.resources.Resource> subclass
        """
        classpath = self.build_classpath(base_class)
        service = self.services.get(service_name, {})
        resources = service.get('resources', {})
        resource_options = resources.get(resource_name, {})
        resource_class = resource_options.get(classpath, None)

        if not resource_class:
            msg = "Resource '{0}' for {1} is not present in the cache."
            raise NotCached(msg.format(
                resource_name,
                service_name
            ))

        return resource_class

    def set_resource(self, service_name, resource_name, to_cache):
        """
        Sets the resource class within the cache.

        :param service_name: The service a given ``Resource`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param resource_name: The name of the ``Resource``. Ex.
            ``Queue``, ``Notification``, ``Table``, etc.
        :type resource_name: string

        :param to_cache: The class to be cached for the service.
        :type to_cache: class
        """
        self.services.setdefault(service_name, {})
        self.services[service_name].setdefault('resources', {})
        self.services[service_name]['resources'].setdefault(resource_name, {})
        options = self.services[service_name]['resources'][resource_name]
        classpath = self.build_classpath(to_cache.__bases__[0])

        if classpath == 'boto3.core.resources.Resource':
            classpath = 'default'

        options[classpath] = to_cache

    def del_resource(self, service_name, resource_name, base_class=None):
        """
        Deletes a resource class for a given service.

        Fails silently if no connection is found in the cache.

        :param service_name: The service a given ``Resource`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param base_class: (Optional) The base class of the object. Prevents
            "magically" loading the wrong class (one with a different base).
            Default is ``default``.
        :type base_class: class
        """
         # Unlike ``get_resource``, this should be fire & forget.
        # We don't really care, as long as it's not in the cache any longer.
        try:
            classpath = self.build_classpath(base_class)
            opts = self.services[service_name]['resources'][resource_name]
            del opts[classpath]
        except KeyError:
            pass

    def get_collection(self, service_name, collection_name, base_class=None):
        """
        Retrieves a collection class from the cache, if available.

        :param service_name: The service a given ``Collection`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param collection_name: The name of the ``Collection``. Ex.
            ``QueueCollection``, ``NotificationCollection``,
            ``TableCollection``, etc.
        :type collection_name: string

        :param base_class: (Optional) The base class of the object. Prevents
            "magically" loading the wrong class (one with a different base).
            Default is ``default``.
        :type base_class: class

        :returns: A <boto3.core.collections.Collection> subclass
        """
        classpath = self.build_classpath(base_class)
        service = self.services.get(service_name, {})
        collections = service.get('collections', {})
        collection_options = collections.get(collection_name, {})
        collection_class = collection_options.get(classpath, None)

        if not collection_class:
            msg = "Collection '{0}' for {1} is not present in the cache."
            raise NotCached(msg.format(
                collection_name,
                service_name
            ))

        return collection_class

    def set_collection(self, service_name, collection_name, to_cache):
        """
        Sets a collection class within the cache.

        :param service_name: The service a given ``Collection`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param collection_name: The name of the ``Collection``. Ex.
            ``QueueCollection``, ``NotificationCollection``,
            ``TableCollection``, etc.
        :type collection_name: string

        :param to_cache: The class to be cached for the service.
        :type to_cache: class
        """
        self.services.setdefault(service_name, {})
        self.services[service_name].setdefault('collections', {})
        self.services[service_name]['collections'].setdefault(collection_name, {})
        options = self.services[service_name]['collections'][collection_name]
        classpath = self.build_classpath(to_cache.__bases__[0])

        if classpath == 'boto3.core.collections.Collection':
            classpath = 'default'

        options[classpath] = to_cache

    def del_collection(self, service_name, collection_name, base_class=None):
        """
        Deletes a collection for a given service.

        Fails silently if no collection is found in the cache.

        :param service_name: The service a given ``Collection`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param collection_name: The name of the ``Collection``. Ex.
            ``QueueCollection``, ``NotificationCollection``,
            ``TableCollection``, etc.
        :type collection_name: string

        :param base_class: (Optional) The base class of the object. Prevents
            "magically" loading the wrong class (one with a different base).
            Default is ``default``.
        :type base_class: class
        """
         # Unlike ``get_collection``, this should be fire & forget.
        # We don't really care, as long as it's not in the cache any longer.
        try:
            classpath = self.build_classpath(base_class)
            opts = self.services[service_name]['collections'][collection_name]
            del opts[classpath]
        except KeyError:
            pass

########NEW FILE########
__FILENAME__ = collections
from boto3.core.constants import DEFAULT_DOCSTRING
from boto3.core.exceptions import NoSuchMethod
from boto3.core.loader import ResourceJSONLoader
from boto3.utils.mangle import to_snake_case
from boto3.utils import six


class CollectionDetails(object):
    """
    A class that encapsulates the metadata about a given ``Collection``.

    Usually hangs off a ``Collection`` as ``Collection._details``.
    """
    service_name = ''
    collection_name = ''
    session = None

    def __init__(self, session, service_name, collection_name, loader=None):
        """
        Creates a ``CollectionDetails`` instance.

        :param session: The configured ``Session`` object to refer to.
        :type session: <class boto3.core.session.Session> instance

        :param service_name: The service a given ``Collection`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param collection_name: The name of the ``Collection``. Ex.
            ``Queue``, ``Notification``, ``Table``, etc.
        :type collection_name: string

        :param loader: (Optional) An instance of a ``ResourceJSONLoader`` class.
            This can be swapped with a different instance or with a completely
            different class with the same interface.
        :type loader: <class boto3.core.loader.ResourceJSONLoader> instance
        """
        super(CollectionDetails, self).__init__()
        self.session = session
        self.service_name = service_name
        self.collection_name = collection_name
        self.loader = loader
        self._api_version = None
        self._loaded_data = None

    def __str__(self):
        return u'<{0}: {1} - {2}>'.format(
            self.__class__.__name__,
            self.service_name,
            self.collection_name,
            self.api_version
        )

    # Kinda ugly (method within a class definition, but not static/classmethod)
    # but depends on internal state. Grump.
    def requires_loaded(func):
        """
        A decorator to ensure the resource data is loaded.
        """
        def _wrapper(self, *args, **kwargs):
            # If we don't have data, go load it.
            if self._loaded_data is None:
                self._loaded_data = self.loader.load(self.service_name)

            return func(self, *args, **kwargs)

        return _wrapper

    @property
    @requires_loaded
    def service_data(self):
        """
        Returns all introspected service data. This will include things like
        other resources/collections that are part of the service. Typically,
        using ``.collection_data`` is much more useful/relevant.

        If the data has been previously accessed, a memoized version of the
        data is returned.

        :returns: A dict of introspected service data
        :rtype: dict
        """
        return self._loaded_data

    @property
    @requires_loaded
    def collection_data(self):
        """
        Returns all introspected collection data.

        If the data has been previously accessed, a memoized version of the
        data is returned.

        :returns: A dict of introspected collection data
        :rtype: dict
        """
        return self._loaded_data['collections'][self.collection_name]

    @property
    @requires_loaded
    def api_version(self):
        """
        Returns the API version introspected from the collection data.
        This is useful in preventing mismatching API versions between the
        client code & service.

        If the data has been previously accessed, a memoized version of the
        API version is returned.

        :returns: The service's version
        :rtype: string
        """
        self._api_version = self._loaded_data.get('api_version', '')
        return self._api_version

    @property
    @requires_loaded
    def resource(self):
        """
        Returns the ``Resource`` to which this collection should be mapped.

        If the data has been previously accessed, a memoized version of the
        resource name is returned.

        :returns: The resource name
        :rtype: string
        """
        return self.collection_data.get('resource', None)

    @property
    @requires_loaded
    def identifiers(self):
        """
        Returns the identifiers.

        If the data has been previously accessed, a memoized version of the
        variable name is returned.

        :returns: The identifiers
        :rtype: list
        """
        # Unlike, ``ResourceDetails``, ``identifiers`` is **optionally**
        # present on ``Collections``.
        return self.collection_data.get('identifiers', [])

    @requires_loaded
    def result_key_for(self, op_name):
        """
        Checks for the presence of a ``result_key``, which defines what data
        should make up an instance.

        Returns ``None`` if there is no ``result_key``.

        :param op_name: The operation name to look for the ``result_key`` in.
        :type op_name: string

        :returns: The expected key to look for data within
        :rtype: string or None
        """
        ops = self.collection_data.get('operations', {})
        op = ops.get(op_name, {})
        key = op.get('result_key', None)
        return key


class Collection(six.Iterator):
    """
    A common base class for all the ``Collection`` objects.
    """
    _res_class = None

    def __init__(self, connection=None, **kwargs):
        """
        Creates a new ``Collection`` instance.

        :param connection: (Optional) Specifies what connection to use.
            By default, this is a matching ``Connection`` subclass provided
            by the ``session`` (i.e. within S3, ``BucketCollection`` would get a
            ``S3Connection`` from the session).
        :type connection: <class boto3.core.connection.Connection> **SUBCLASS**

        :param **kwargs: (Optional) Reserved for future use.
        :type **kwargs: dict
        """
        self._data = {}
        self._connection = connection
        self._active_iter = None
        self._active_offset = 0

        for key, value in kwargs.items():
            self._data[key] = value

        if self._connection is None:
            self._connection = self._details.session.connect_to(
                self._details.service_name
            )

        # Now that we have a connection, we can update docstrings.
        self._update_docstrings()

    def __str__(self):
        return "{0}: {1} in {2}".format(
            self.__class__.__name__,
            self._details.service_name,
            self._connection.region_name
        )

    def __getattr__(self, name):
        """
        Attempts to return instance data for a given name if available.

        :param name: The instance data's name
        :type name: string
        """
        if name in self._data:
            return self._data[name]

        raise AttributeError("No such attribute '{0}'".format(name))

    def __iter__(self):
        self._active_iter = self.each()
        self._active_offset = 0
        return iter(self)

    def __next__(self):
        res = self._active_iter[self._active_offset]
        self._active_offset += 1
        return res

    @classmethod
    def change_resource(cls, resource_class):
        """
        Updates the default ``Resource`` class created when the ``Collection``
        is returning instances.

        Default behavior (without calling this method) is that the class
        will return whatever the ``session`` can provide.

        :param resource_class: The new ``Resource`` class to use during
            construction.
        :type resource_class: class
        """
        cls._res_class = resource_class

    def _update_docstrings(self):
        """
        Runs through the operation methods & updates their docstrings if
        necessary.

        If the method has the default placeholder docstring, this will replace
        it with the docstring from the underlying connection.
        """
        ops = self._details.collection_data['operations']

        for method_name in ops.keys():
            meth = getattr(self.__class__, method_name, None)

            if not meth:
                continue

            if meth.__doc__ != DEFAULT_DOCSTRING:
                # It already has a custom docstring. Leave it alone.
                continue

            # Needs updating. So there's at least *something* vaguely useful
            # there, use the docstring from the underlying ``Connection``
            # method.
            # FIXME: We need to figure out a way to make this more useful, if
            #        possible.
            api_name = ops[method_name]['api_name']
            conn_meth = getattr(self._connection, to_snake_case(api_name))

            # We need to do detection here, because Py2 treats ``.__doc__``
            # as a special read-only attribute. :/
            if six.PY3:
                meth.__doc__ = conn_meth.__doc__
            else:
                meth.__func__.__doc__ = conn_meth.__doc__

    def get_identifiers(self):
        """
        Returns the identifier(s) (if present) from the instance data.

        The identifier name(s) is/are determined from the ``ResourceDetails``
        instance hanging off the class itself.

        :returns: All the identifier information
        :rtype: dict
        """
        data = {}

        for id_info in self._details.identifiers:
            var_name = id_info['var_name']
            data[var_name] = self._data.get(var_name)

        return data

    def set_identifiers(self, data):
        """
        Sets the identifier(s) within the instance data.

        The identifier name(s) is/are determined from the ``ResourceDetails``
        instance hanging off the class itself.

        :param data: The value(s) to be set.
        :param data: dict
        """
        for id_info in self._details.identifiers:
            var_name = id_info['var_name']
            self._data[var_name] = data.get(var_name)

    def full_update_params(self, conn_method_name, params):
        """
        When a API method on the collection is called, this goes through the
        params & run a series of hooks to allow for updating those parameters.

        Typically, this method is **NOT** call by the user. However, the user
        may wish to define other methods (i.e. ``update_params`` to work with
        multiple parameters at once or ``update_params_METHOD_NAME`` to
        manipulate a single parameter) on their class, which this method
        will call.

        :param conn_method_name: The name of the underlying connection method
            about to be called. Typically, this is a "snake_cased" variant of
            the API name (i.e. ``update_bucket`` in place of ``UpdateBucket``).
        :type conn_method_name: string

        :param params: A dictionary of all the key/value pairs passed to the
            method. This dictionary is transformed by this call into the final
            params to be passed to the underlying connection.
        :type params: dict
        """
        # We'll check for custom methods to do addition, specific work.
        custom_method_name = 'update_params_{0}'.format(conn_method_name)
        custom_method = getattr(self, custom_method_name, None)

        if custom_method:
            # Let the specific method further process the data.
            params = custom_method(params)

        # Now that all the method-specific data is there, apply any further
        # service-wide changes here.
        params = self.update_params(conn_method_name, params)
        return params

    def update_params(self, conn_method_name, params):
        """
        A hook to allow manipulation of multiple parameters at once.

        By default, this just ensures the identifier data in in the parameters,
        so that the user doesn't have to provide it.

        You can override/extend this method (typically on your subclass)
        to do additional checks, pre-populate values or remove unwanted data.

        :param conn_method_name: The name of the underlying connection method
            about to be called. Typically, this is a "snake_cased" variant of
            the API name (i.e. ``update_bucket`` in place of ``UpdateBucket``).
        :type conn_method_name: string

        :param params: A dictionary of all the key/value pairs passed to the
            method. This dictionary is transformed by this call into the final
            params to be passed to the underlying connection.
        :type params: dict
        """
        # By default, this just sets the identifier info.
        # We use ``var_name`` instead of ``api_name``. Because botocore.
        params.update(self.get_identifiers())
        return params

    def full_post_process(self, conn_method_name, result):
        """
        When a response from an API method call is received, this goes through
        the returned data & run a series of hooks to allow for handling that
        data.

        Typically, this method is **NOT** call by the user. However, the user
        may wish to define other methods (i.e. ``post_process`` to work with
        all the data at once or ``post_process_METHOD_NAME`` to
        handle a single piece of data) on their class, which this method
        will call.

        :param conn_method_name: The name of the underlying connection method
            about to be called. Typically, this is a "snake_cased" variant of
            the API name (i.e. ``update_bucket`` in place of ``UpdateBucket``).
        :type conn_method_name: string

        :param result: A dictionary of all the key/value pairs passed back
            from the API (server-side). This dictionary is transformed by this
            call into the final data to be passed back to the user.
        :type result: dict
        """
        result = self.post_process(conn_method_name, result)

        # We'll check for custom methods to do addition, specific work.
        custom_method_name = 'post_process_{0}'.format(conn_method_name)
        custom_method = getattr(self, custom_method_name, None)

        if custom_method:
            # Let the specific method further process the data.
            result = custom_method(result)

        return result

    def post_process(self, conn_method_name, result):
        """
        A hook to allow manipulation of the entire returned data at once.

        By default, this goes through & (shallowly) snake-cases all of the
        keys, so that the result is friendlier to use from Python.

        You can override/extend this method (typically on your subclass)
        to do additional checks, alter the result or remove unwanted data.

        :param conn_method_name: The name of the underlying connection method
            about to be called. Typically, this is a "snake_cased" variant of
            the API name (i.e. ``update_bucket`` in place of ``UpdateBucket``).
        :type conn_method_name: string

        :param result: A dictionary of all the key/value pairs passed back
            from the API (server-side). This dictionary is transformed by this
            call into the final data to be passed back to the user.
        :type result: dict
        """
        return result

    def post_process_create(self, result):
        """
        An example of the ``post_process`` extensions, this returns an instance
        of the ``Resource`` created (rather than just a bag of data).

        :param result: The full data handed back from the API.
        :type result: dict

        :returns: A ``Resource`` subclass
        """
        # We need to possibly drill into the response & get out the data here.
        # Check for a result key.
        result_key = self._details.result_key_for('create')

        if not result_key:
            return self.build_resource(result)

        return self.build_resource(result[result_key])

    def post_process_each(self, result):
        """
        An example of the ``post_process`` extensions, this returns a set
        of instances of the ``Resource`` fetched (rather than just a bag of
        data).

        :param result: The full data handed back from the API.
        :type result: dict

        :returns: A list of ``Resource`` subclass
        """
        # We need to possibly drill into the response & get out the data here.
        # Check for a result key.
        result_key = self._details.result_key_for('each')

        if not result_key:
            return result

        return [self.build_resource(res) for res in result[result_key]]

    def build_resource(self, data):
        """
        Given some data, builds the correct/matching ``Resource`` subclass
        for the ``Collection``. Useful in things like ``create`` & ``each``.

        :param result: The data for an instance handed back from the API.
        :type result: dict

        :returns: A ``Resource`` subclass
        """
        if self._res_class is None:
            self._res_class = self._details.session.get_resource(
                self._details.service_name,
                self._details.resource
            )

        final_data = {}

        # Lightly post-process the data, to look more Pythonic.
        for key, value in data.items():
            final_data[to_snake_case(key)] = value

        return self._res_class(connection=self._connection, **final_data)


class CollectionFactory(object):
    """
    Generates the underlying ``Collection`` classes based off the
    ``ResourceJSON`` included in the SDK.

    Usage::

        >>> cf = CollectionFactory()
        >>> BucketCollection = cf.construct_for('s3', 'BucketCollection')

    """
    loader_class = ResourceJSONLoader

    def __init__(self, session=None, loader=None,
                 base_collection_class=Collection,
                 details_class=CollectionDetails):
        """
        Creates a new ``CollectionFactory`` instance.

        :param session: The ``Session`` the factory should use.
        :type session: <class boto3.session.Session> instance

        :param loader: (Optional) An instance of a ``ResourceJSONLoader`` class.
            This can be swapped with a different instance or with a completely
            different class with the same interface.
            By default, this is ``boto3.core.loader.default_loader``.
        :type loader: <class boto3.core.loader.ResourceJSONLoader> instance

        :param base_collection_class: (Optional) The base class to use when
            creating the collection. By default, this is ``Collection``, but
            should you need to globally change the behavior of all collections,
            you'd simply specify this to provide your own class.
        :type base_collection_class: <class boto3.core.collections.Collection>

        :param details_class: (Optional) The metadata class used to store things
            like service name & data. By default, this is ``CollectionDetails``,
            but should you need to globally change the behavior (perhaps
            modifying how the collection data is returned), you simply provide
            your own class here.
        :type details_class: <class boto3.core.collections.CollectionDetails>
        """
        self.session = session
        self.loader = loader
        self.base_collection_class = base_collection_class
        self.details_class = details_class

        if self.session is None:
            # Fallback to the default.
            import boto3
            self.session = boto3.session

        if self.loader is None:
            import boto3.core.loader
            self.loader = boto3.core.loader.default_loader

    def __str__(self):
        return self.__class__.__name__

    def construct_for(self, service_name, collection_name, base_class=None):
        """
        Builds a new, specialized ``Collection`` subclass as part of a given
        service.

        This will load the ``ResourceJSON``, determine the correct
        mappings/methods & constructs a brand new class with those methods on
        it.

        :param service_name: The name of the service to construct a resource
            for. Ex. ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param collection_name: The name of the ``Collection``. Ex.
            ``QueueCollection``, ``NotificationCollection``,
            ``TableCollection``, etc.
        :type collection_name: string

        :returns: A new collection class for that service
        """
        details = self.details_class(
            self.session,
            service_name,
            collection_name,
            loader=self.loader
        )

        attrs = {
            '_details': details,
        }

        # Determine what we should call it.
        klass_name = self._build_class_name(collection_name)

        # Construct what the class ought to have on it.
        attrs.update(self._build_methods(details))

        if base_class is None:
            base_class = self.base_collection_class

        # Create the class.
        return type(
            klass_name,
            (base_class,),
            attrs
        )

    def _build_class_name(self, collection_name):
        return collection_name

    def _build_methods(self, details):
        attrs = {}
        ops = details.collection_data.get('operations', {}).items()

        for method_name, op_data in ops:
            attrs[method_name] = self._create_operation_method(
                method_name,
                op_data
            )

        return attrs

    def _create_operation_method(factory_self, method_name, op_data):
        # Determine the correct name for the method.
        # This is because the method names will be standardized across
        # resources, so we'll have to lean on the ``api_name`` to figure out
        # what the correct underlying method name on the ``Connection`` should
        # be.
        # Map -> map -> unmap -> remap -> map :/
        conn_method_name = to_snake_case(op_data['api_name'])

        if not six.PY3:
            method_name = str(method_name)

        def _new_method(self, **kwargs):
            params = self.full_update_params(method_name, kwargs)
            method = getattr(self._connection, conn_method_name, None)

            if not method:
                msg = "Introspected method named '{0}' not available on " + \
                      "the connection."
                raise NoSuchMethod(msg.format(conn_method_name))

            result = method(**params)
            return self.full_post_process(method_name, result)

        _new_method.__name__ = method_name
        _new_method.__doc__ = DEFAULT_DOCSTRING
        return _new_method

########NEW FILE########
__FILENAME__ = connection
from boto3.core.constants import DEFAULT_REGION
from boto3.core.constants import NOTHING_PROVIDED
from boto3.core.exceptions import ServerError
from boto3.core.introspection import Introspection
from boto3.utils import six


class ConnectionDetails(object):
    """
    A class that encapsulates the metadata about a given ``Connection``.

    Usually hangs off a ``Connection`` as ``Connection._details``.
    """
    service_name = 'unknown'
    session = None

    def __init__(self, service_name, session):
        """
        Creates a ``ConnectionDetails`` instance.

        :param service_name: The service a given ``Connection`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param session: The configured ``Session`` object to refer to.
        :type session: <class boto3.core.session.Session> instance
        """
        super(ConnectionDetails, self).__init__()
        self.service_name = service_name
        self.session = session
        self._api_version = None
        self._loaded_service_data = None

    def __str__(self):
        return u'<{0}: {1} - {2}>'.format(
            self.__class__.__name__,
            self.service_name,
            self.api_version
        )

    @property
    def service_data(self):
        """
        Returns all introspected service data.

        If the data has been previously accessed, a memoized version of the
        data is returned.

        :returns: A dict of introspected service data
        :rtype: dict
        """
        # Lean on the cache first.
        if self._loaded_service_data is not None:
            return self._loaded_service_data

        # We don't have a cache. Build it.
        self._loaded_service_data = self._introspect_service(
            # We care about the ``botocore.session`` here, not the
            # ``boto3.session``.
            self.session.core_session,
            self.service_name
        )
        # Clear out the API version, just in case.
        self._api_version = None
        return self._loaded_service_data

    @property
    def api_version(self):
        """
        Returns API version introspected from the service data.

        If the data has been previously accessed, a memoized version of the
        API version is returned.

        :returns: The service's version
        :rtype: string
        """
        # Lean on the cache first.
        if self._api_version is not None:
            return self._api_version

        # We don't have a cache. Build it.
        self._api_version = self._introspect_api_version(
            self.session.core_session,
            self.service_name
        )
        return self._api_version

    def _introspect_service(self, core_session, service_name):
        # Yes, we could lean on ``self.session|.service_name`` here,
        # but this makes testing/composability easier.
        intro = Introspection(core_session)
        return intro.introspect_service(service_name)

    def _introspect_api_version(self, core_session, service_name):
        intro = Introspection(core_session)
        service = intro.get_service(service_name)
        return service.api_version

    def reload_service_data(self):
        """
        Wipes out & reloads the cached service data.

        :returns: A dict of introspected service data
        :rtype: dict
        """
        self._loaded_service_data = None
        return self.service_data


class Connection(object):
    """
    A common base class for all the ``Connection`` objects.
    """
    def __init__(self, region_name=DEFAULT_REGION):
        """
        Creates a new connection instance.

        :param region_name: (Optional) The name of the region to connect to.
            By default, this is the value from
            ``boto3.core.constants.DEFAULT_REGION``.
        :type region_name: string
        """
        super(Connection, self).__init__()
        self.region_name = region_name

    def __str__(self):
        return u'<{0}: {0}>'.format(
            self.__class__.__name__,
            self.region_name
        )

    def _check_method_params(self, op_params, **kwargs):
        # For now, we don't type-check or anything, just check for required
        # params.
        for param in op_params:
            if param['required'] is True:
                if not param['var_name'] in kwargs:
                    err = "Missing required parameter: '{0}'".format(
                        param['var_name']
                    )
                    raise TypeError(err)

    def _build_service_params(self, op_params, **kwargs):
        # TODO: Maybe build in an extension mechanism (like
        #      ``build_<op_name>_params``)?
        service_params = {}

        for param in op_params:
            value = kwargs.get(param['var_name'], NOTHING_PROVIDED)

            if value is NOTHING_PROVIDED:
                # They didn't give us a value. We should've already checked
                # "required-ness", so just give it a pass & move on.
                continue

            # FIXME: This is weird. I was expecting this to be
            #        ``param['api_name']`` to pass to ``botocore``, but
            #        evidently it expects snake_case here?!
            service_params[param['var_name']] = value

        return service_params

    def _check_for_errors(self, results):
        result_data = results[1]

        if 'Errors' in result_data:
            errs = result_data['Errors']

            if not errs:
                # Skip it if the errors are empty.
                # For instance, S3 will send this key with nothing in it on a
                # successful call.
                return

            if isinstance(errs, (list, tuple)):
                error = errs[0]
            elif hasattr(errs, 'items'):
                error = errs
            else:
                error = {
                    'Message': errs
                }

            raise ServerError(
                code=error.get('Code', 'ConnectionError'),
                message=error.get('Message', 'No details available.'),
                full_response=result_data
            )

    def _post_process_results(self, method_name, output, results):
        # TODO: Maybe build in an extension mechanism (like
        #      ``post_process_<op_name>_results``)?
        return results[1]

    @classmethod
    def connect_to(cls, **kwargs):
        """
        Instantiates the class, passing all ``**kwargs`` along to the
        constructor.

        This is reserved for further extension.

        :returns: An instance of the ``Connection``
        :rtype: <class Connection>
        """
        return cls(**kwargs)

    def _get_operation_data(self, method_name):
        """
        Returns all the introspected operation data for a given method.
        """
        return self._details.service_data[method_name]

    def _get_operation_params(self, method_name):
        return self._get_operation_data(method_name).get('params', [])


class ConnectionFactory(object):
    """
    Builds custom ``Connection`` subclasses based on the service's operations.

    Usage::

        >>> cf = ConnectionFactory()
        >>> S3Connection = cf.construct_for('s3')

    """
    def __init__(self, session, base_connection=Connection,
                 details_class=ConnectionDetails):
        """
        Creates a new ``ConnectionFactory`` instance.

        :param session: The ``Session`` the factory should use.
        :type session: <class boto3.session.Session> instance

        :param base_connection: (Optional) The base class to use when creating
            the connection. By default, this is ``Connection``, but should
            you need to globally change the behavior of all connections,
            you'd simply specify this to provide your own class.
        :type base_connection: <class boto3.core.connection.Connection>

        :param details_class: (Optional) The metadata class used to store things
            like service name & data. By default, this is ``ConnectionDetails``,
            but should you need to globally change the behavior (perhaps
            modifying how the service data is returned), you simply provide
            your own class here.
        :type details_class: <class boto3.core.connection.ConnectionDetails>
        """
        super(ConnectionFactory, self).__init__()
        self.session = session
        self.base_connection = base_connection
        self.details_class = ConnectionDetails

    def __str__(self):
        return self.__class__.__name__

    def construct_for(self, service_name):
        """
        Builds a new, specialized ``Connection`` subclass for a given service.

        This will introspect a service, determine all the API calls it has &
        constructs a brand new class with those methods on it.

        :param service_name: The name of the service to construct a connection
            for. Ex. ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :returns: A new connection class for that service
        """
        # Construct a new ``ConnectionDetails`` (or similar class) for storing
        # the relevant details about the service & its operations.
        details = self.details_class(service_name, self.session)
        # Make sure the new class gets that ``ConnectionDetails`` instance as a
        # ``cls._details`` attribute.
        attrs = {
            '_details': details,
        }

        # Determine what we should call it.
        klass_name = self._build_class_name(service_name)

        # Construct what the class ought to have on it.
        attrs.update(self._build_methods(details))

        # Create the class.
        return type(
            klass_name,
            (self.base_connection,),
            attrs
        )

    def _build_class_name(self, service_name):
        return '{0}Connection'.format(service_name.capitalize())

    def _build_methods(self, details):
        attrs = {}

        for method_name, op_data in details.service_data.items():
            # First we make expand then we defense it.
            # Construct a brand-new method & assign it on the class.
            attrs[method_name] = self._create_operation_method(method_name, op_data)

        return attrs

    def _generate_docstring(self, op_data):
        docstring = op_data['docs']

        for param_data in op_data['params']:
            param_doc = ":param {0}: {1}\n".format(
                param_data['var_name'],
                param_data.get('docs', 'No documentation available')
            )
            type_doc = ":type {0}: {1}\n".format(
                param_data['var_name'],
                param_data['type']
            )

            docstring += '\n'
            docstring += param_doc
            docstring += type_doc

        docstring += '\n'
        docstring += ':returns: The response data received\n'
        docstring += ':rtype: dict\n'
        return docstring

    def _create_operation_method(factory_self, method_name, orig_op_data):
        if not six.PY3:
            method_name = str(method_name)

        def _new_method(self, **kwargs):
            # Fetch the information about the operation.
            op_data = self._get_operation_data(method_name)

            # Check the parameters.
            self._check_method_params(
                op_data['params'],
                **kwargs
            )

            # Prep the service's parameters.
            service_params = self._build_service_params(
                op_data['params'],
                **kwargs
            )

            # Actually call the service.
            service = self._details.session.get_core_service(
                self._details.service_name
            )
            endpoint = service.get_endpoint(self.region_name)
            op = service.get_operation(
                op_data['api_name']
            )
            results = op.call(endpoint, **service_params)

            # Check for error conditions.
            self._check_for_errors(results)

            # Post-process results here
            post_processed = self._post_process_results(
                method_name,
                op_data['output'],
                results
            )
            return post_processed

        # Swap the name, so it looks right.
        _new_method.__name__ = method_name
        # Assign docstring.
        _new_method.__doc__ = factory_self._generate_docstring(orig_op_data)
        # Return the newly constructed method.
        return _new_method

########NEW FILE########
__FILENAME__ = constants
import os
import sys

from boto3 import get_version


# TODO: Assert if this is egg-safe (or if that matters to us)?
BOTO3_ROOT = os.path.dirname(os.path.dirname(__file__))

USER_AGENT_NAME = 'Boto3'
USER_AGENT_VERSION = get_version(full=True)

DEFAULT_REGION = 'us-east-1'

DEFAULT_DOCSTRING = """
Please make an instance of this class to inspect the docstring.

No underlying connection is yet available.
"""

DEFAULT_DATA_DIR = os.path.join(BOTO3_ROOT, 'data', 'aws')
DEFAULT_RESOURCE_JSON_DIR = os.path.join(DEFAULT_DATA_DIR, 'resources')


class NOTHING_PROVIDED(object):
    """
    An identifier for no data provided.

    Never meant to be instantiated.
    """
    pass


class NO_NAME(object):
    """
    An identifier to indicate a method instance hasn't been given a name.

    Never meant to be instantiated.
    """
    pass


class NO_RESOURCE(object):
    """
    An identifier to indicate a method instance hasn't been attached to a
    resource.

    Never meant to be instantiated.
    """
    pass

########NEW FILE########
__FILENAME__ = exceptions
class BotoException(Exception):
    """
    A base exception class for all Boto-related exceptions.
    """
    pass


class ServerError(BotoException):
    """
    Thrown when an error is received within a response.
    """
    fmt = "[{0}]: {1}"

    def __init__(self, code='GeneralError', message='No message',
                 full_response=None, **kwargs):
        self.code = code
        self.message = message
        self.full_response = full_response

        if self.full_response is None:
            self.full_response = {}

        msg = self.fmt.format(
            self.code,
            self.message
        )
        super(ServerError, self).__init__(msg)


class IncorrectImportPath(BotoException):
    pass


class NoSuchMethod(BotoException):
    pass


class NotCached(BotoException):
    pass


class ResourceError(BotoException):
    pass


class NoResourceJSONFound(ResourceError):
    pass


class APIVersionMismatchError(BotoException):
    pass


class NoRelation(ResourceError):
    pass


class ValidationError(BotoException):
    pass


class MD5ValidationError(ValidationError):
    pass

########NEW FILE########
__FILENAME__ = introspection
import re

from boto3.core.constants import DEFAULT_REGION
from boto3.utils import six
from boto3.utils.mangle import html_to_rst


class Introspection(object):
    """
    Used to introspect ``botocore`` objects (``Service``, ``Operation`` &
    ``Endpoint``) to determine what operations/parameters/etc. are available.

    Done here to encapsulate the data needed from ``botocore``, to limit
    API changes elsewhere in ``boto`` should ``botocore`` change.

    Usage::

        >>> from botocore.session import Session
        >>> session = Session()
        >>> intro = Introspection(session)
        >>> intro.introspect_service('s3')
        {
            # ...big bag of operation data...
        }

    """
    tag_re = re.compile(r'<.*?>')

    def __init__(self, session):
        """
        Creates a new ``Introspection`` instance.

        :param session: A ``botocore`` session to introspect with.
        :type session: A ``<botocore.session.Session>`` instance
        """
        super(Introspection, self).__init__()
        # TODO: For now, this is a ``botocore.session.Session``. We may want
        #       to use a ``boto3.core.session.Session`` instead?
        self.session = session

    def get_service(self, service_name):
        """
        Returns a ``botocore.service.Service`` object for a given service.

        :param service_name: The desired service name
        :type service_name: string

        :returns: A <botocore.service.Service> object
        """
        return self.session.get_service(service_name)

    def get_endpoint(self, service, region_name=DEFAULT_REGION):
        """
        Returns a ``botocore.endpoint.Endpoint`` object for a given service.

        :param service: A ``Service`` object
        :type service: A ``<botocore.service.Service>`` instance

        :param region_name: (Optional) The name of the region you'd like to
            connect to. By default, this is
            ``boto3.core.constants.DEFAULT_REGION``.
        :type region_name: string

        :returns: A <botocore.endpoint.Endpoint> object
        """
        return service.get_endpoint(region_name=region_name)

    def get_operation(self, service, operation_name):
        """
        Returns a ``botocore.operation.Operation`` object for a given service
        & operation name.

        :param service_name: The desired service name
        :type service_name: string

        :param operation_name: The API name of the operation you'd like to
            execute. Ex. ``PutBucketCORS``
        :type operation_name: string

        :returns: A <botocore.operation.Operation> object
        """
        return service.get_operation(operation_name)

    def strip_html(self, doc):
        """
        This method removes all HTML from a docstring.

        Lighter than ``convert_docs``, this is intended for the documentation
        on **parameters**, not the overall docs themselves.

        :param doc: The initial docstring
        :type doc: string

        :returns: The stripped/cleaned docstring
        :rtype: string
        """
        if not isinstance(doc, six.string_types):
            return ''

        doc = doc.strip()
        doc = self.tag_re.sub('', doc)
        return doc

    def parse_param(self, core_param):
        """
        Returns data about a specific parameter.

        :param core_param: The ``Parameter`` to introspect
        :type core_param: A ``<botocore.parameters.Parameter>`` subclass

        :returns: A dict of the relevant information
        """
        return {
            'var_name': core_param.py_name,
            'api_name': core_param.name,
            'required': core_param.required,
            'docs': self.strip_html(core_param.documentation),
            'type': core_param.type,
        }

    def parse_params(self, core_params):
        """
        Goes through a set of parameters, extracting information about each.

        :param core_params: The collection of parameters
        :type core_params: A collection of ``<botocore.parameters.Parameter>``
            subclasses

        :returns: A list of dictionaries
        """
        params = []

        for core_param in core_params:
            params.append(self.parse_param(core_param))

        return params

    def convert_docs(self, html):
        """
        Converts the service's HTML docs to reStructured Text.

        :param html: The HTML to convert
        :type html: string

        :returns: The converted text
        :rtype: string
        """
        return html_to_rst(html)

    def introspect_operation(self, operation):
        """
        Introspects an entire operation, returning::

        * the method name (to expose to the user)
        * the API name (used server-side)
        * docs
        * introspected information about the parameters
        * information about the output

        :param operation: The operation to introspect
        :type operation: A <botocore.operation.Operation> object

        :returns: A dict of information
        """
        return {
            'method_name': operation.py_name,
            'api_name': operation.name,
            'docs': self.convert_docs(operation.documentation),
            'params': self.parse_params(operation.params),
            'output': operation.output,
        }

    def introspect_service(self, service_name):
        """
        Introspects all the operations (& related information) about a service.

        :param service_name: The desired service name
        :type service_name: string

        :returns: A dict of all operation names & information
        """
        data = {}
        service = self.get_service(service_name)

        for operation in service.operations:
            # These are ``Operation`` objects, not operation strings.
            op_data = self.introspect_operation(operation)
            data[op_data['method_name']] = op_data

        return data

########NEW FILE########
__FILENAME__ = loader
import glob
import os

from boto3.core.constants import DEFAULT_RESOURCE_JSON_DIR
from boto3.core.exceptions import NoResourceJSONFound
from boto3.utils import json


class ResourceJSONLoader(object):
    """
    Handles the loading of the ResourceJSON. Can be overridden to look up
    user-defined paths first, with fallbacks.

    For optimal efficiency, one loader instance should be used in as many
    places as possible & use the ``__getitem__`` (dictionary-style) lookups.
    This will populate the cache, causing subsequent lookups to be fast & one
    instance will prevent memory bloat.

    Usage::

        >>> rjl = ResourceJSONLoader()
        # Load it no matter what.
        >>> rjl.load('s3')
        {
            # ...S3's ResourceJSON as a dict...
        }
        # Get a cached version (or load it if not present).
        >>> rjl['ec2']
        {
            # ...EC2's ResourceJSON as a dict...
        }

    """
    default_data_dirs = [
        DEFAULT_RESOURCE_JSON_DIR,
    ]

    def __init__(self, data_dirs=None):
        """
        Creates a new ``ResourceJSONLoader`` instance.

        :param data_dirs: (Optional) A list of absolute paths to check for the
            ResourceJSON. By default, this is just
            ``boto3.core.constants.DEFAULT_RESOURCE_JSON_DIR`` as the single
            item in the list.
        :type data_dirs: list
        """
        self.data_dirs = data_dirs
        self._loaded_data = {}

        if self.data_dirs is None:
            self.data_dirs = self.default_data_dirs

    def get_available_options(self, service_name):
        """
        Fetches a collection of all JSON files for a given service.

        This checks user-created files (if present) as well as including the
        default service files.

        Example::

            >>> loader.get_available_options('s3')
            {
                '2013-11-27': [
                    '~/.boto-overrides/s3-2013-11-27.json',
                    '/path/to/boto3/data/aws/resources/s3-2013-11-27.json',
                ],
                '2010-10-06': [
                    '/path/to/boto3/data/aws/resources/s3-2010-10-06.json',
                ],
                '2007-09-15': [
                    '~/.boto-overrides/s3-2007-09-15.json',
                ],
            }

        :param service_name: The name of the desired service
        :type service_name: string

        :returns: A dictionary of api_version keys, with a list of filepaths
            for that version (in preferential order).
        :rtype: dict
        """
        options = {}

        for data_dir in self.data_dirs:
            # Traverse all the directories trying to find the best match.
            service_glob = "{0}-*.json".format(service_name)
            path = os.path.join(data_dir, service_glob)
            found = glob.glob(path)

            for match in found:
                # Rip apart the path to determine the API version.
                base = os.path.basename(match)
                bits = os.path.splitext(base)[0].split('-', 1)

                if len(bits) < 2:
                    continue

                api_version = bits[1]
                options.setdefault(api_version, [])
                options[api_version].append(match)

        return options

    def get_best_match(self, options, service_name, api_version=None):
        """
        Given a collection of possible service options, selects the best match.

        If no API version is provided, the path to the most recent API version
        will be returned. If an API version is provided & there is an exact
        match, the path to that version will be returned. If there is no exact
        match, an attempt will be made to find a compatible (earlier) version.

        In all cases, user-created files (if present) will be given preference
        over the default included versions.

        :param options: A dictionary of options. See
            ``.get_available_options(...)``.
        :type options: dict

        :param service_name: The name of the desired service
        :type service_name: string

        :param api_version: (Optional) The desired API version to load
        :type service_name: string

        :returns: The full path to the best matching JSON file
        """
        if not options:
            msg = "No JSON files provided. Please check your " + \
                  "configuration/install."
            raise NoResourceJSONFound(msg)

        if api_version is None:
            # Give them the very latest option.
            best_version = max(options.keys())
            return options[best_version][0], best_version

        # They've provided an api_version. Try to give them exactly what they
        # requested, falling back to the best compatible match if no exact
        # match can be found.
        if api_version in options:
            return options[api_version][0], api_version

        # Find the best compatible match. Run through in descending order.
        # When we find a version that's lexographically less than the provided
        # one, run with it.
        for key in sorted(options.keys(), reverse=True):
            if key <= api_version:
                return options[key][0], key

        raise NoResourceJSONFound(
            "No compatible JSON could be loaded for {0} ({1}).".format(
                service_name,
                api_version
            )
        )

    def load(self, service_name, api_version=None, cached=True):
        """
        Loads the desired JSON for a service. (uncached)

        This will fall back through all the ``data_dirs`` provided to the
        constructor, returning the **first** one it finds.

        :param service_name: The name of the desired service
        :type service_name: string

        :param api_version: (Optional) The desired API version to load
        :type service_name: string

        :param cached: (Optional) Whether or not the cache should be used
            when attempting to load the data. Default is ``True``.
        :type cached: boolean

        :returns: The loaded JSON as a dict
        """
        # Fetch from the cache first if it's there.
        if cached:
            if service_name in self._loaded_data:
                if api_version in self._loaded_data[service_name]:
                    return self._loaded_data[service_name][api_version]

        data = {}
        options = self.get_available_options(service_name)
        match, version = self.get_best_match(
            options,
            service_name,
            api_version=api_version
        )

        with open(match, 'r') as json_file:
            data = json.load(json_file)
            # Embed where we found it from for debugging purposes.
            data['__file__'] = match
            data['api_version'] = version

        if cached:
            self._loaded_data.setdefault(service_name, {})
            self._loaded_data[service_name][api_version] = data

        return data

    def __contains__(self, service_name):
        return service_name in self._loaded_data


# Default instance for convenience.
default_loader = ResourceJSONLoader()

########NEW FILE########
__FILENAME__ = resources
from boto3.core.constants import DEFAULT_DOCSTRING
from boto3.core.exceptions import NoSuchMethod, NoRelation
from boto3.core.introspection import Introspection
from boto3.core.loader import ResourceJSONLoader
from boto3.utils.mangle import to_snake_case
from boto3.utils import six


class ResourceDetails(object):
    """
    A class that encapsulates the metadata about a given ``Resource``.

    Usually hangs off a ``Resource`` as ``Resource._details``.
    """
    service_name = ''
    resource_name = ''
    session = None

    def __init__(self, session, service_name, resource_name, loader=None):
        """
        Creates a ``ResourceDetails`` instance.

        :param session: The configured ``Session`` object to refer to.
        :type session: <class boto3.core.session.Session> instance

        :param service_name: The service a given ``Resource`` talks to. Ex.
            ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param resource_name: The name of the ``Resource``. Ex.
            ``Queue``, ``Notification``, ``Table``, etc.
        :type resource_name: string

        :param loader: (Optional) An instance of a ``ResourceJSONLoader`` class.
            This can be swapped with a different instance or with a completely
            different class with the same interface.
        :type loader: <class boto3.core.loader.ResourceJSONLoader> instance
        """
        super(ResourceDetails, self).__init__()
        self.session = session
        self.service_name = service_name
        self.resource_name = resource_name
        self.loader = loader
        self._api_version = None
        self._loaded_data = None

    def __str__(self):
        return u'<{0}: {1} - {2}>'.format(
            self.__class__.__name__,
            self.service_name,
            self.resource_name,
            self.api_version
        )

    # Kinda ugly (method within a class definition, but not static/classmethod)
    # but depends on internal state. Grump.
    def requires_loaded(func):
        """
        A decorator to ensure the resource data is loaded.
        """
        def _wrapper(self, *args, **kwargs):
            # If we don't have data, go load it.
            if self._loaded_data is None:
                self._loaded_data = self.loader.load(self.service_name)

            return func(self, *args, **kwargs)

        return _wrapper

    @property
    @requires_loaded
    def service_data(self):
        """
        Returns all introspected service data. This will include things like
        other resources/collections that are part of the service. Typically,
        using ``.resource_data`` is much more useful/relevant.

        If the data has been previously accessed, a memoized version of the
        data is returned.

        :returns: A dict of introspected service data
        :rtype: dict
        """
        return self._loaded_data

    @property
    @requires_loaded
    def resource_data(self):
        """
        Returns all introspected resource data.

        If the data has been previously accessed, a memoized version of the
        data is returned.

        :returns: A dict of introspected resource data
        :rtype: dict
        """
        return self._loaded_data['resources'][self.resource_name]

    @property
    @requires_loaded
    def api_version(self):
        """
        Returns the API version introspected from the resource data.
        This is useful in preventing mismatching API versions between the
        client code & service.

        If the data has been previously accessed, a memoized version of the
        API version is returned.

        :returns: The service's version
        :rtype: string
        """
        self._api_version = self._loaded_data.get('api_version', '')
        return self._api_version

    @property
    @requires_loaded
    def identifiers(self):
        """
        Returns the identifiers.

        If the data has been previously accessed, a memoized version of the
        variable name is returned.

        :returns: The identifiers
        :rtype: list
        """
        return self.resource_data['identifiers']

    @requires_loaded
    def result_key_for(self, op_name):
        """
        Checks for the presence of a ``result_key``, which defines what data
        should make up an instance.

        Returns ``None`` if there is no ``result_key``.

        :param op_name: The operation name to look for the ``result_key`` in.
        :type op_name: string

        :returns: The expected key to look for data within
        :rtype: string or None
        """
        ops = self.resource_data.get('operations', {})
        op = ops.get(op_name, {})
        key = op.get('result_key', None)
        return key

    @property
    @requires_loaded
    def relations(self):
        """
        Returns the relation data read from the resource data.

        Example data::

            {
                'name_on_the_instance_here': {
                    'class_type': 'resource',
                    'class': 'NameOfResource',
                    'required': True,
                    'rel_type': '1-M'
                }
            }

        :returns: The relation data, if any is present
        :rtype: dict
        """
        return self.resource_data.get('relations', {})


class Resource(object):
    """
    A common base class for all the ``Resource`` objects.
    """
    def __init__(self, connection=None, **kwargs):
        """
        Creates a new ``Resource`` instance.

        :param connection: (Optional) Specifies what connection to use.
            By default, this is a matching ``Connection`` subclass provided
            by the ``session`` (i.e. within S3, ``BucketResource`` would get a
            ``S3Connection`` from the session).
        :type connection: <class boto3.core.connection.Connection> **SUBCLASS**

        :param **kwargs: (Optional) Instance data to be specified on the
            instance itself.
        :type **kwargs: dict
        """
        # Tracks the *built* relations (actual instances).
        self._relations = {}
        # Tracks the scalar data on the resource.
        self._data = {}
        self._connection = connection

        for key, value in kwargs.items():
            self._data[key] = value

        if self._connection is None:
            self._connection = self._details.session.connect_to(
                self._details.service_name
            )

        # Now that we have a connection, we can update docstrings.
        self._update_docstrings()

    def __str__(self):
        return "{0}: {1} in {2}".format(
            self.__class__.__name__,
            self._details.service_name,
            self._connection.region_name
        )

    def __getattr__(self, name):
        """
        Attempts to return either the related object or instance data for a
        given name if available.

        :param name: The instance data's name
        :type name: string
        """
        # Check to see if the thing being requested is a known relation.
        if name in self._details.relations:
            # Check if we already have built version.
            if not name in self._relations:
                # There's not a previously built object.
                # Lazily build it & assign it here.
                self._relations[name] = self.build_relation(name)

            return self._relations[name]

        if name in self._data:
            return self._data[name]

        raise AttributeError("No such attribute '{0}'".format(name))

    def _update_docstrings(self):
        """
        Runs through the operation methods & updates their docstrings if
        necessary.

        If the method has the default placeholder docstring, this will replace
        it with the docstring from the underlying connection.
        """
        ops = self._details.resource_data['operations']

        for method_name in ops.keys():
            meth = getattr(self.__class__, method_name, None)

            if not meth:
                continue

            if meth.__doc__ != DEFAULT_DOCSTRING:
                # It already has a custom docstring. Leave it alone.
                continue

            # Needs updating. So there's at least *something* vaguely useful
            # there, use the docstring from the underlying ``Connection``
            # method.
            # FIXME: We need to figure out a way to make this more useful, if
            #        possible.
            api_name = ops[method_name]['api_name']
            conn_meth = getattr(self._connection, to_snake_case(api_name))

            # We need to do detection here, because Py2 treats ``.__doc__``
            # as a special read-only attribute. :/
            if six.PY3:
                meth.__doc__ = conn_meth.__doc__
            else:
                meth.__func__.__doc__ = conn_meth.__doc__

    def get_identifiers(self):
        """
        Returns the identifier(s) (if present) from the instance data.

        The identifier name(s) is/are determined from the ``ResourceDetails``
        instance hanging off the class itself.

        :returns: All the identifier information
        :rtype: dict
        """
        data = {}

        for id_info in self._details.identifiers:
            var_name = id_info['var_name']
            data[var_name] = self._data.get(var_name)

        return data

    def set_identifiers(self, data):
        """
        Sets the identifier(s) within the instance data.

        The identifier name(s) is/are determined from the ``ResourceDetails``
        instance hanging off the class itself.

        :param data: The value(s) to be set.
        :param data: dict
        """
        for id_info in self._details.identifiers:
            var_name = id_info['var_name']
            self._data[var_name] = data.get(var_name)

        # FIXME: This needs to likely kick off invalidating/rebuilding
        #        relations.
        #        For now, just remove them all. This is potentially inefficient
        #        but is nicely lazy if we don't need them & prevents stale data
        #        for the moment.
        self._relations = {}

    def build_relation(self, name, klass=None):
        """
        Constructs a related ``Resource`` or ``Collection``.

        This allows for construction of classes with information prepopulated
        from what the current instance has. This enables syntax like::

            bucket = Bucket(bucket='some-bucket-name')

            for obj in bucket.objects.each():
                print(obj.key)

        :param name: The name of the relation from the ResourceJSON
        :type name: string

        :param klass: (Optional) An overridable class to construct. Typically
            only useful if you need a custom subclass used in place of what
            boto3 provides.
        :type klass: class

        :returns: An instantiated related object
        """
        try:
            rel_data = self._details.relations[name]
        except KeyError:
            msg = "No such relation named '{0}'.".format(name)
            raise NoRelation(msg)

        if klass is None:
            # This is the typical case, where we're not explicitly given a
            # class to build with. Hit the session & look up what we should
            # be loading.
            if rel_data['class_type'] == 'collection':
                klass = self._details.session.get_collection(
                    self._details.service_name,
                    rel_data['class']
                )
            elif rel_data['class_type'] == 'resource':
                klass = self._details.session.get_resource(
                    self._details.service_name,
                    rel_data['class']
                )
            else:
                msg = "Unknown class '{0}' for '{1}'.".format(
                    rel_data['class_type'],
                    name
                )
                raise NoRelation(msg)

        # Instantiate & return it.
        kwargs = {}
        # Just populating identifiers is enough for the 1-M case.
        kwargs.update(self.get_identifiers())

        if rel_data.get('rel_type', '1-M') == '1-1':
            # FIXME: If it's not a collection, we might have some instance data
            #        (i.e. ``bucket``) in ``self._data`` to populate as well.
            #        This seems like a can of worms, so ignore for the moment.
            pass

        return klass(connection=self._connection, **kwargs)

    def full_update_params(self, conn_method_name, params):
        """
        When a API method on the resource is called, this goes through the
        params & run a series of hooks to allow for updating those parameters.

        Typically, this method is **NOT** call by the user. However, the user
        may wish to define other methods (i.e. ``update_params`` to work with
        multiple parameters at once or ``update_params_METHOD_NAME`` to
        manipulate a single parameter) on their class, which this method
        will call.

        :param conn_method_name: The name of the underlying connection method
            about to be called. Typically, this is a "snake_cased" variant of
            the API name (i.e. ``update_bucket`` in place of ``UpdateBucket``).
        :type conn_method_name: string

        :param params: A dictionary of all the key/value pairs passed to the
            method. This dictionary is transformed by this call into the final
            params to be passed to the underlying connection.
        :type params: dict
        """
        # We'll check for custom methods to do addition, specific work.
        custom_method_name = 'update_params_{0}'.format(conn_method_name)
        custom_method = getattr(self, custom_method_name, None)

        if custom_method:
            # Let the specific method further process the data.
            params = custom_method(params)

        # Now that all the method-specific data is there, apply any further
        # service-wide changes here.
        params = self.update_params(conn_method_name, params)
        return params

    def update_params(self, conn_method_name, params):
        """
        A hook to allow manipulation of multiple parameters at once.

        By default, this just ensures the identifier data in in the parameters,
        so that the user doesn't have to provide it.

        You can override/extend this method (typically on your subclass)
        to do additional checks, pre-populate values or remove unwanted data.

        :param conn_method_name: The name of the underlying connection method
            about to be called. Typically, this is a "snake_cased" variant of
            the API name (i.e. ``update_bucket`` in place of ``UpdateBucket``).
        :type conn_method_name: string

        :param params: A dictionary of all the key/value pairs passed to the
            method. This dictionary is transformed by this call into the final
            params to be passed to the underlying connection.
        :type params: dict
        """
        # By default, this just sets the identifier info.
        # We use ``var_name`` instead of ``api_name``. Because botocore.
        params.update(self.get_identifiers())
        return params

    def full_post_process(self, conn_method_name, result):
        """
        When a response from an API method call is received, this goes through
        the returned data & run a series of hooks to allow for handling that
        data.

        Typically, this method is **NOT** call by the user. However, the user
        may wish to define other methods (i.e. ``post_process`` to work with
        all the data at once or ``post_process_METHOD_NAME`` to
        handle a single piece of data) on their class, which this method
        will call.

        :param conn_method_name: The name of the underlying connection method
            about to be called. Typically, this is a "snake_cased" variant of
            the API name (i.e. ``update_bucket`` in place of ``UpdateBucket``).
        :type conn_method_name: string

        :param result: A dictionary of all the key/value pairs passed back
            from the API (server-side). This dictionary is transformed by this
            call into the final data to be passed back to the user.
        :type result: dict
        """
        result = self.post_process(conn_method_name, result)

        # We'll check for custom methods to do addition, specific work.
        custom_method_name = 'post_process_{0}'.format(conn_method_name)
        custom_method = getattr(self, custom_method_name, None)

        if custom_method:
            # Let the specific method further process the data.
            result = custom_method(result)

        return result

    def post_process(self, conn_method_name, result):
        """
        A hook to allow manipulation of the entire returned data at once.

        By default, this does nothing, just passing through the ``result``.

        You can override/extend this method (typically on your subclass)
        to do additional checks, alter the result or remove unwanted data.

        :param conn_method_name: The name of the underlying connection method
            about to be called. Typically, this is a "snake_cased" variant of
            the API name (i.e. ``update_bucket`` in place of ``UpdateBucket``).
        :type conn_method_name: string

        :param result: A dictionary of all the key/value pairs passed back
            from the API (server-side). This dictionary is transformed by this
            call into the final data to be passed back to the user.
        :type result: dict
        """
        # Mostly a hook for post-processing as needed.
        return result

    def post_process_get(self, result):
        """
        Given an object with identifiers, fetches the data for that object
        from the service.

        This alters the data on the object itself & simply passes through what
        was received.

        :param result: The response data
        :type result: dict

        :returns: The unmodified response data
        """
        if not hasattr(result, 'items'):
            # If it's not a dict, give up & just return whatever you get.
            return result

        # We need to possibly drill into the response & get out the data here.
        # Check for a result key.
        result_key = self._details.result_key_for('get')

        if not result_key:
            # There's no result_key. Just use the top-level data.
            data = result
        else:
            data = result[result_key]

        for key, value in data.items():
            self._data[to_snake_case(key)] = value

        return result


class ResourceFactory(object):
    """
    Generates the underlying ``Resource`` classes based off the ``ResourceJSON``
    included in the SDK.

    Usage::

        >>> rf = ResourceFactory()
        >>> Bucket = rf.construct_for('s3', 'Bucket')

    """
    loader_class = ResourceJSONLoader

    def __init__(self, session=None, loader=None,
                 base_resource_class=Resource,
                 details_class=ResourceDetails):
        """
        Creates a new ``ResourceFactory`` instance.

        :param session: The ``Session`` the factory should use.
        :type session: <class boto3.session.Session> instance

        :param loader: (Optional) An instance of a ``ResourceJSONLoader`` class.
            This can be swapped with a different instance or with a completely
            different class with the same interface.
            By default, this is ``boto3.core.loader.default_loader``.
        :type loader: <class boto3.core.loader.ResourceJSONLoader> instance

        :param base_resource_class: (Optional) The base class to use when creating
            the resource. By default, this is ``Resource``, but should
            you need to globally change the behavior of all resources,
            you'd simply specify this to provide your own class.
        :type base_resource_class: <class boto3.core.resources.Resource>

        :param details_class: (Optional) The metadata class used to store things
            like service name & data. By default, this is ``ResourceDetails``,
            but should you need to globally change the behavior (perhaps
            modifying how the resource data is returned), you simply provide
            your own class here.
        :type details_class: <class boto3.core.resources.ResourceDetails>
        """
        self.session = session
        self.loader = loader
        self.base_resource_class = base_resource_class
        self.details_class = details_class

        if self.session is None:
            # Fallback to the default.
            import boto3
            self.session = boto3.session

        if self.loader is None:
            import boto3.core.loader
            self.loader = boto3.core.loader.default_loader

    def __str__(self):
        return self.__class__.__name__

    def construct_for(self, service_name, resource_name, base_class=None):
        """
        Builds a new, specialized ``Resource`` subclass as part of a given
        service.

        This will load the ``ResourceJSON``, determine the correct
        mappings/methods & constructs a brand new class with those methods on
        it.

        :param service_name: The name of the service to construct a resource
            for. Ex. ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param resource_name: The name of the ``Resource``. Ex.
            ``Queue``, ``Notification``, ``Table``, etc.
        :type resource_name: string

        :returns: A new resource class for that service
        """
        details = self.details_class(
            self.session,
            service_name,
            resource_name,
            loader=self.loader
        )

        attrs = {
            '_details': details,
        }

        # Determine what we should call it.
        klass_name = self._build_class_name(resource_name)

        # Construct what the class ought to have on it.
        attrs.update(self._build_methods(details))

        if base_class is None:
            base_class = self.base_resource_class

        # Create the class.
        return type(
            klass_name,
            (base_class,),
            attrs
        )

    def _build_class_name(self, resource_name):
        return resource_name

    def _build_methods(self, details):
        attrs = {}
        ops = details.resource_data.get('operations', {}).items()

        for method_name, op_data in ops:
            attrs[method_name] = self._create_operation_method(
                method_name,
                op_data
            )

        return attrs

    def _create_operation_method(factory_self, method_name, op_data):
        # Determine the correct name for the method.
        # This is because the method names will be standardized across
        # resources, so we'll have to lean on the ``api_name`` to figure out
        # what the correct underlying method name on the ``Connection`` should
        # be.
        # Map -> map -> unmap -> remap -> map :/
        conn_method_name = to_snake_case(op_data['api_name'])

        if not six.PY3:
            method_name = str(method_name)

        def _new_method(self, **kwargs):
            params = self.full_update_params(method_name, kwargs)
            method = getattr(self._connection, conn_method_name, None)

            if not method:
                msg = "Introspected method named '{0}' not available on " + \
                      "the connection."
                raise NoSuchMethod(msg.format(conn_method_name))

            result = method(**params)
            return self.full_post_process(method_name, result)

        _new_method.__name__ = method_name
        _new_method.__doc__ = DEFAULT_DOCSTRING
        return _new_method

########NEW FILE########
__FILENAME__ = session
import botocore.session

from boto3.core.cache import ServiceCache
from boto3.core.constants import USER_AGENT_NAME, USER_AGENT_VERSION
from boto3.core.exceptions import NotCached


class Session(object):
    """
    Stores all the state for a given ``boto3`` session.

    Can dynamically create all the various ``Connection`` classes.

    Usage::

        >>> from boto3.core.session import Session
        >>> session = Session()
        >>> sqs_conn = session.connect_to('sqs', region_name='us-west-2')

    """
    cache_class = ServiceCache

    def __init__(self, session=None, connection_factory=None,
                 resource_factory=None, collection_factory=None):
        """
        Creates a ``Session`` instance.

        :param session: (Optional) Custom instantiated ``botocore`` instance.
            Useful if you have specific needs. If not present, a default
            ``Session`` will be created.
        :type session: <botocore.session.Session> instance

        :param connection_factory: (Optional) Specifies a custom
            ``ConnectionFactory`` to be used. Useful if you need to change how
            ``Connection`` objects are constructed by the session.
        :type connection_factory: <boto3.core.connection.ConnectionFactory>
            instance

        :param resource_factory: (Optional) Specifies a custom
            ``ResourceFactory`` to be used. Useful if you need to change how
            ``Resource`` objects are constructed by the session.
        :type resource_factory: <boto3.core.resources.ResourceFactory>
            instance

        :param collection_factory: (Optional) Specifies a custom
            ``CollectionFactory`` to be used. Useful if you need to change how
            ``Collection`` objects are constructed by the session.
        :type collection_factory: <boto3.core.collections.CollectionFactory>
            instance
        """
        super(Session, self).__init__()
        self.core_session = session
        self.connection_factory = connection_factory
        self.resource_factory = resource_factory
        self.collection_factory = collection_factory

        self.cache = self.cache_class()

        if not self.core_session:
            self.core_session = botocore.session.get_session()

        self.core_session.user_agent_name = USER_AGENT_NAME
        self.core_session.user_agent_version = USER_AGENT_VERSION

        if not self.connection_factory:
            from boto3.core.connection import ConnectionFactory
            self.connection_factory = ConnectionFactory(session=self)

        if not self.resource_factory:
            from boto3.core.resources import ResourceFactory
            self.resource_factory = ResourceFactory(session=self)

        if not self.collection_factory:
            from boto3.core.collections import CollectionFactory
            self.collection_factory = CollectionFactory(session=self)

    def get_connection(self, service_name):
        """
        Returns a ``Connection`` **class** for a given service.

        :param service_name: A string that specifies the name of the desired
            service. Ex. ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :rtype: <boto3.core.connection.Connection subclass>
        """
        try:
            return self.cache.get_connection(service_name)
        except NotCached:
            pass

        # We didn't find it. Construct it.
        new_class = self.connection_factory.construct_for(service_name)
        self.cache.set_connection(service_name, new_class)
        return new_class

    def get_resource(self, service_name, resource_name, base_class=None):
        """
        Returns a ``Resource`` **class** for a given service.

        :param service_name: A string that specifies the name of the desired
            service. Ex. ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param resource_name: A string that specifies the name of the desired
            class. Ex. ``Queue``, ``Notification``, ``Table``, etc.
        :type resource_name: string

        :param base_class: (Optional) The base class of the object. Prevents
            "magically" loading the wrong class (one with a different base).
        :type base_class: class

        :rtype: <boto3.core.resources.Resource subclass>
        """
        try:
            return self.cache.get_resource(
                service_name,
                resource_name,
                base_class=base_class
            )
        except NotCached:
            pass

        # We didn't find it. Construct it.
        new_class = self.resource_factory.construct_for(
            service_name,
            resource_name,
            base_class=base_class
        )
        self.cache.set_resource(service_name, resource_name, new_class)
        return new_class

    def get_collection(self, service_name, collection_name, base_class=None):
        """
        Returns a ``Collection`` **class** for a given service.

        :param service_name: A string that specifies the name of the desired
            service. Ex. ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :param collection_name: A string that specifies the name of the desired
            class. Ex. ``QueueCollection``, ``NotificationCollection``,
            ``TableCollection``, etc.
        :type collection_name: string

        :param base_class: (Optional) The base class of the object. Prevents
            "magically" loading the wrong class (one with a different base).
        :type base_class: class

        :rtype: <boto3.core.collections.Collection subclass>
        """
        try:
            return self.cache.get_collection(
                service_name,
                collection_name,
                base_class=base_class
            )
        except NotCached:
            pass

        # We didn't find it. Construct it.
        new_class = self.collection_factory.construct_for(
            service_name,
            collection_name,
            base_class=base_class
        )
        self.cache.set_collection(service_name, collection_name, new_class)
        return new_class

    def connect_to(self, service_name, **kwargs):
        """
        Shortcut method to make instantiating the ``Connection`` classes
        easier.

        Forwards ``**kwargs`` like region, keys, etc. on to the constructor.

        :param service_name: A string that specifies the name of the desired
            service. Ex. ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :rtype: <boto3.core.connection.Connection> instance
        """
        service_class = self.get_connection(service_name)
        return service_class.connect_to(**kwargs)

    def get_core_service(self, service_name):
        """
        Returns a ``botocore.service.Service``.

        Mostly an abstraction for the ``*Connection`` objects to get what
        they need for introspection.

        :param service_name: A string that specifies the name of the desired
            service. Ex. ``sqs``, ``sns``, ``dynamodb``, etc.
        :type service_name: string

        :rtype: <botocore.service.Service subclass>
        """
        return self.core_session.get_service(service_name)

########NEW FILE########
__FILENAME__ = connection
import boto3


# FIXME: These should be just sane defaults, but they are configured at
#        import-time. :/
ElastictranscoderConnection = boto3.session.get_connection('elastictranscoder')

########NEW FILE########
__FILENAME__ = resources
import boto3
from boto3.core.resources import Resource


PipelineCollection = boto3.session.get_collection(
    'elastictranscoder',
    'PipelineCollection'
)
PresetCollection = boto3.session.get_collection(
    'elastictranscoder',
    'PresetCollection'
)
JobCollection = boto3.session.get_collection(
    'elastictranscoder',
    'JobCollection'
)
Pipeline = boto3.session.get_resource('elastictranscoder', 'Pipeline')
Preset = boto3.session.get_resource('elastictranscoder', 'Preset')
Job = boto3.session.get_resource('elastictranscoder', 'Job')

########NEW FILE########
__FILENAME__ = connection
import boto3


# FIXME: These should be just sane defaults, but they are configured at
#        import-time. :/
IamConnection = boto3.session.get_connection('iam')

########NEW FILE########
__FILENAME__ = constants
from boto3.utils import json


# FIXME: From Boto v2. Perhaps this should move/be assumed elsewhere?
ASSUME_ROLE_POLICY_DOCUMENT = json.dumps({
    'Statement': [
        {
            'Principal': {
                'Service': ['ec2.amazonaws.com']
            },
            'Effect': 'Allow',
            'Action': ['sts:AssumeRole']
        }
    ]
})

########NEW FILE########
__FILENAME__ = resources
import boto3
from boto3.core.resources import Resource


class GroupCustomizations(Resource):
    def update_params_add_user(self, params):
        params.update(self.get_identifiers())
        return params

    def update_params_remove_user(self, params):
        params.update(self.get_identifiers())
        return params


# FIXME: These should be just sane defaults, but they are configured at
#        import-time. :/
AccessKeyCollection = boto3.session.get_collection(
    'iam',
    'AccessKeyCollection'
)
AccountAliasCollection = boto3.session.get_collection(
    'iam',
    'AccountAliasCollection'
)
GroupCollection = boto3.session.get_collection(
    'iam',
    'GroupCollection'
)
InstanceProfileCollection = boto3.session.get_collection(
    'iam',
    'InstanceProfileCollection'
)
LoginProfileCollection = boto3.session.get_collection(
    'iam',
    'LoginProfileCollection'
)
RoleCollection = boto3.session.get_collection('iam', 'RoleCollection')
UserCollection = boto3.session.get_collection('iam', 'UserCollection')
VirtualMFADeviceCollection = boto3.session.get_collection(
    'iam',
    'VirtualMFADeviceCollection'
)
AccessKey = boto3.session.get_resource('iam', 'AccessKey')
AccountAlias = boto3.session.get_resource('iam', 'AccountAlias')
Group = boto3.session.get_resource(
    'iam',
    'Group',
    base_class=GroupCustomizations
)
InstanceProfile = boto3.session.get_resource('iam', 'InstanceProfile')
LoginProfile = boto3.session.get_resource('iam', 'LoginProfile')
Role = boto3.session.get_resource('iam', 'Role')
User = boto3.session.get_resource('iam', 'User')
VirtualMFADevice = boto3.session.get_resource('iam', 'VirtualMFADevice')

########NEW FILE########
__FILENAME__ = connection
import boto3


# FIXME: These should be just sane defaults, but they are configured at
#        import-time. :/
S3Connection = boto3.session.get_connection('s3')

########NEW FILE########
__FILENAME__ = resources
import io

import boto3
from boto3.core.resources import Resource


class S3ObjectCustomizations(Resource):
    def get_content(self):
        if not 'body' in self._data:
            return None

        body = self._data['body']

        if hasattr(body, 'seek'):
            try:
                body.seek(0)
            except io.UnsupportedOperation:
                # Some things are not rewindable. Don't die as a result.
                pass

        if hasattr(body, 'read'):
            return body.read()

        return body

    def set_content(self, content):
        # ``botocore`` handles the details, whether it's a string or a
        # file-like object. This method is mostly here for API reflection.
        self._data['body'] = content


BucketCollection = boto3.session.get_collection(
    's3',
    'BucketCollection'
)
S3ObjectCollection = boto3.session.get_collection(
    's3',
    'S3ObjectCollection'
)
Bucket = boto3.session.get_resource('s3', 'Bucket')
S3Object = boto3.session.get_resource(
    's3',
    'S3Object',
    base_class=S3ObjectCustomizations
)

# Keep it on the collection, not the session-wide cached version.
S3ObjectCollection.change_resource(S3Object)

########NEW FILE########
__FILENAME__ = utils
def force_delete_bucket(conn, bucket_name):
    """
    Deletes a bucket & all of it's contents.

    A convenience method added because the default ``delete_bucket`` method
    only works on **empty** buckets.

    :param conn:
    :type conn:

    :param bucket_name:
    :type bucket_name: string
    """
    marker = None
    keep_deleting = True

    while keep_deleting:
        kwargs = {}

        # botocore won't let us include this if it's ``None``.
        if marker is not None:
            kwargs['marker'] = marker

        resp = conn.list_objects(
            bucket=bucket_name,
            **kwargs
        )
        marker = resp.get('Marker', None)
        keys = [key_info['Key'] for key_info in resp.get('Contents', [])]

        # Bulk delete keys.
        if keys:
            objects = [{'Key': key} for key in keys]
            resp = conn.delete_objects(
                bucket=bucket_name,
                delete={
                    'Objects': objects
                }
            )

        if marker is None:
            keep_deleting = False

    # The bucket should now be empty.
    return conn.delete_bucket(bucket=bucket_name)

########NEW FILE########
__FILENAME__ = connection
import boto3


# FIXME: These should be just sane defaults, but they are configured at
#        import-time. :/
SnsConnection = boto3.session.get_connection('sns')

########NEW FILE########
__FILENAME__ = resources
import boto3


# FIXME: These should be just sane defaults, but they are configured at
#        import-time. :/
PlatformApplicationCollection = boto3.session.get_collection(
    'sns',
    'PlatformApplicationCollection'
)
PlatformEndpointCollection = boto3.session.get_collection(
    'sns',
    'PlatformEndpointCollection'
)
TopicCollection = boto3.session.get_collection(
    'sns',
    'TopicCollection'
)
SubscriptionCollection = boto3.session.get_collection(
    'sns',
    'SubscriptionCollection'
)
PlatformApplication = boto3.session.get_resource('sns', 'PlatformApplication')
PlatformEndpoint = boto3.session.get_resource('sns', 'PlatformEndpoint')
Topic = boto3.session.get_resource('sns', 'Topic')
Subscription = boto3.session.get_resource('sns', 'Subscription')

########NEW FILE########
__FILENAME__ = utils
import hashlib

from boto3.utils import json


def subscribe_sqs_queue(sns_conn, sqs_conn, topic_arn, queue_url, queue_arn):
    """
    Handles all the details around hooking up an SNS topic to a SQS queue.

    Requires a previously created SNS topic & a previously created SQS queue.

    Specifically, this method does the following:

    * creates the subscription
    * checks for an existing policy
    * if there's no policy for the given topic/queue combination, it creates
      a policy allowing ``SendMessage``
    * finally, it updates the policy & returns the output

    :param sns_conn: A ``Connection`` subclass for SNS
    :type sns_conn: A <boto3.core.connection.Connection> subclass

    :param sqs_conn: A ``Connection`` subclass for SQS
    :type sqs_conn: A <boto3.core.connection.Connection> subclass

    :param topic_arn: The ARN for the topic
    :type topic_arn: string

    :param queue_url: The URL for the queue
    :type queue_url: string

    :param queue_arn: The ARN for the queue
    :type queue_arn: string
    """
    to_md5 = topic_arn + queue_arn
    sid = hashlib.md5(to_md5.encode('utf-8')).hexdigest()
    sid_exists = False
    resp = sns_conn.subscribe(
        topic_arn=topic_arn,
        protocol='sqs',
        notification_endpoint=queue_arn
    )
    attr = sqs_conn.get_queue_attributes(
        queue_url=queue_url,
        attribute_names=['Policy']
    )
    policy = {}

    if 'Policy' in attr:
        policy = json.loads(attr['Policy'])

    policy.setdefault('Version', '2008-10-17')
    policy.setdefault('Statement', [])

    # See if a Statement with the Sid exists already.
    for s in policy['Statement']:
        if s['Sid'] == sid:
            sid_exists = True

    if not sid_exists:
        statement = {
            'Action': 'SQS:SendMessage',
            'Effect': 'Allow',
            'Principal': {
                'AWS': '*',
            },
            'Resource': queue_arn,
            'Sid': sid,
            'Condition': {
                'StringLike': {
                    'aws:SourceArn': topic_arn,
                },
            },
        }
        policy['Statement'].append(statement)

    sqs_conn.set_queue_attributes(
        queue_url=queue_url,
        attributes={
            'Policy': json.dumps(policy)
        }
    )
    return resp

########NEW FILE########
__FILENAME__ = connection
import boto3


# FIXME: These should be just sane defaults, but they are configured at
#        import-time. :/
SqsConnection = boto3.session.get_connection('sqs')

########NEW FILE########
__FILENAME__ = resources
import boto3


# FIXME: These should be just sane defaults, but they are configured at
#        import-time. :/
QueueCollection = boto3.session.get_collection('sqs', 'QueueCollection')
MessageCollection = boto3.session.get_collection('sqs', 'MessageCollection')
Queue = boto3.session.get_resource('sqs', 'Queue')
Message = boto3.session.get_resource('sqs', 'Message')

########NEW FILE########
__FILENAME__ = utils
def convert_queue_url_to_arn(conn, url):
    """
    Given a queue's URL, returns the ARN for that queue.

    :param conn: The SQS connection
    :type conn: A <boto3.core.connection.Connection> subclass

    :param url: The URL for the queue
    :type url: string

    :returns: The ARN for the queue
    :rtype: string
    """
    url_bits = url.split('/')[-2:]
    return 'arn:aws:sqs:{0}:{1}:{2}'.format(
        conn.region_name,
        url_bits[0],
        url_bits[1],
    )

########NEW FILE########
__FILENAME__ = import_utils
import importlib

from boto3.core.exceptions import IncorrectImportPath


def import_class(import_path):
    """
    Imports a class dynamically from a full import path.
    """
    if not '.' in import_path:
        raise IncorrectImportPath(
            "Invalid Python-style import path provided: {0}.".format(
                import_path
            )
        )

    path_bits = import_path.split('.')
    mod_path = '.'.join(path_bits[:-1])
    klass_name = path_bits[-1]

    try:
        mod = importlib.import_module(mod_path)
    except ImportError:
        raise IncorrectImportPath(
            "Could not import module '{0}'.".format(mod_path)
        )

    try:
        klass = getattr(mod, klass_name)
    except AttributeError:
        raise IncorrectImportPath(
            "Imported module '{0}' but could not find class '{1}'.".format(
                mod_path,
                klass_name
            )
        )

    return klass

########NEW FILE########
__FILENAME__ = mangle
from bcdoc.restdoc import ReSTDocument

from botocore import xform_name


def to_snake_case(camel_case_name):
    """
    Converts CamelCaseNames to snake_cased_names.

    :param camel_case_name: The name you'd like to convert from.
    :type camel_case_name: string

    :returns: A converted string
    :rtype: string
    """
    return xform_name(camel_case_name)


def to_camel_case(snake_case_name):
    """
    Converts snake_cased_names to CamelCaseNames.

    :param snake_case_name: The name you'd like to convert from.
    :type snake_case_name: string

    :returns: A converted string
    :rtype: string
    """
    bits = snake_case_name.split('_')
    return ''.join([bit.capitalize() for bit in bits])


def html_to_rst(html):
    """
    Converts the service HTML docs to reStructured Text, for use in docstrings.

    :param html: The raw HTML to convert
    :type html: string

    :returns: A reStructured Text formatted version of the text
    :rtype: string
    """
    doc = ReSTDocument()
    doc.include_doc_string(html)
    raw_doc = doc.getvalue()
    return raw_doc.decode('utf-8')

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# boto3 documentation build configuration file, created by
# sphinx-quickstart on Sun Dec  2 07:26:23 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os
import boto3

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'boto3'
copyright = u'2013, Amazon Web Services'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = boto3.get_version()
# The full version, including alpha/beta/rc tags.
release = boto3.get_version(full=True)

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
htmlhelp_basename = 'boto3doc'


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
  ('index', 'boto3.tex', u'boto3 Documentation',
   u'Mitch Garnaat', 'manual'),
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
    ('index', 'boto3', u'boto3 Documentation',
     [u'Mitch Garnaat'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'boto3', u'boto3 Documentation',
   u'Mitch Garnaat', 'boto3', 'One line description of project.',
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
__FILENAME__ = base
# -*- coding: utf-8 -*-
import time

from boto3.core.session import Session

from tests import unittest


class ConnectionTestCase(object):
    """
    A base class to make testing connections a little less verbose/more
    standard.

    This automatically sets up a connection object for the service
    (``self.conn``) & runs a test to ensure the connection has all the right
    API methods.

    Usage::

        from tests.integration.base import ConnectionTestCase
        from tests import unittest


        class MyConnTest(ConnectionTestCase, unittest.TestCase):
            service_name = 's3'
            ops = [
                'abort_multipart_upload',
                'complete_multipart_upload',
                'copy_object',
                'create_bucket',
                'create_multipart_upload',
                # ...
            ]

            # You can add your own test methods here...

    """
    service_name = None
    ops = []

    def setUp(self):
        super(ConnectionTestCase, self).setUp()
        self.session = Session()
        self.conn_class = self.session.get_connection(self.service_name)
        self.conn = self.conn_class()

    def test_op_methods(self):
        if not self.service_name:
            return

        if not len(self.ops):
            self.fail("There are no expected Connection methods supplied.")

        for op_name in self.ops:
            self.assertTrue(
                hasattr(self.conn, op_name),
                msg="{0} is missing.".format(op_name)
            )
            self.assertTrue(
                callable(getattr(self.conn, op_name)),
                msg="{0} is not callable.".format(op_name)
            )

########NEW FILE########
__FILENAME__ = test_connection
# -*- coding: utf-8 -*-
import time

import boto3
from boto3.iam.constants import ASSUME_ROLE_POLICY_DOCUMENT
from boto3.s3.utils import force_delete_bucket

from tests.integration.base import ConnectionTestCase
from tests import unittest


class ElastictranscoderConnectionTestCase(ConnectionTestCase, unittest.TestCase):
    service_name = 'elastictranscoder'
    ops = [
        'cancel_job',
        'create_job',
        'create_pipeline',
        'create_preset',
        'delete_pipeline',
        'delete_preset',
        'list_jobs_by_pipeline',
        'list_jobs_by_status',
        'list_pipelines',
        'list_presets',
        'read_job',
        'read_pipeline',
        'read_preset',
        'test_role',
        'update_pipeline',
        'update_pipeline_notifications',
        'update_pipeline_status'
    ]

    def test_integration(self):
        iam_conn = boto3.session.connect_to('iam')
        s3_conn = boto3.session.connect_to('s3')

        now = int(time.time())
        role_name = 'test-pipeline-{0}'.format(now)
        in_bucket = 'test-pipeline-in-{0}'.format(now)
        out_bucket = 'test-pipeline-out-{0}'.format(now)
        pipeline_name = 'pipeline-{0}'.format(now)

        # Create the surrounding setup.
        resp = iam_conn.create_role(
            role_name=role_name,
            assume_role_policy_document=ASSUME_ROLE_POLICY_DOCUMENT
        )
        self.addCleanup(iam_conn.delete_role, role_name=role_name)
        role_arn = resp['Role']['Arn']

        s3_conn.create_bucket(bucket=in_bucket)
        self.addCleanup(
            force_delete_bucket,
            conn=s3_conn,
            bucket_name=in_bucket
        )
        s3_conn.create_bucket(bucket=out_bucket)
        self.addCleanup(
            force_delete_bucket,
            conn=s3_conn,
            bucket_name=out_bucket
        )

        # Test the pipeline related methods.
        resp = self.conn.list_pipelines()
        initial_pipelines = [pipe['Name'] for pipe in resp['Pipelines']]
        self.assertFalse(pipeline_name in initial_pipelines)

        # Create a pipeline.
        resp = self.conn.create_pipeline(
            name=pipeline_name,
            input_bucket=in_bucket,
            output_bucket=out_bucket,
            role=role_arn,
            notifications={
                'Completed': '',
                'Error': '',
                'Warning': '',
                'Progressing': '',
            }
        )
        pipeline_id = resp['Pipeline']['Id']
        self.addCleanup(self.conn.delete_pipeline, id=pipeline_id)

        # Ensure it appears in the list.
        resp = self.conn.list_pipelines()
        pipelines = [pipe['Name'] for pipe in resp['Pipelines']]
        self.assertTrue(len(pipelines) > len(initial_pipelines))
        self.assertTrue(pipeline_name in pipelines)

        # Read the pipeline.
        resp = self.conn.read_pipeline(id=pipeline_id)
        self.assertEqual(resp['Pipeline']['Name'], pipeline_name)

        # Update the pipeline.
        resp = self.conn.update_pipeline_status(
            id=pipeline_id,
            status='Paused'
        )
        self.assertEqual(resp['Pipeline']['Status'], 'Paused')

########NEW FILE########
__FILENAME__ = test_resources
import time

import boto3
from boto3.elastictranscoder.resources import PipelineCollection
from boto3.elastictranscoder.resources import Pipeline
from boto3.iam.constants import ASSUME_ROLE_POLICY_DOCUMENT
from boto3.iam.resources import RoleCollection
from boto3.s3.resources import BucketCollection
from boto3.s3.utils import force_delete_bucket

from tests import unittest


class ElasticTranscoderIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        super(ElasticTranscoderIntegrationTestCase, self).setUp()
        self.conn = boto3.session.connect_to(
            'elastictranscoder',
            region_name='us-west-2'
        )

    def test_integration(self):
        iam_conn = boto3.session.connect_to('iam')
        s3_conn = boto3.session.connect_to('s3')

        now = int(time.time())
        role_name = 'test-pipeline-{0}'.format(now)
        in_bucket = 'test-pipeline-in-{0}'.format(now)
        out_bucket = 'test-pipeline-out-{0}'.format(now)
        pipeline_name = 'pipeline-{0}'.format(now)

        # Do the requisite setup.
        role = RoleCollection(connection=iam_conn).create(
            role_name=role_name,
            assume_role_policy_document=ASSUME_ROLE_POLICY_DOCUMENT
        )
        # FIXME: This shouldn't be necessary...
        self.addCleanup(role.delete, role_name=role_name)

        resp = BucketCollection(connection=s3_conn).create(bucket=in_bucket)
        self.addCleanup(
            force_delete_bucket,
            conn=s3_conn,
            bucket_name=in_bucket
        )
        resp = BucketCollection(connection=s3_conn).create(bucket=out_bucket)
        self.addCleanup(
            force_delete_bucket,
            conn=s3_conn,
            bucket_name=out_bucket
        )

        # Now list/create/list/read/update the pipeline.
        pipelines = PipelineCollection().each()
        pipeline_names = [pipe.name for pipe in pipelines]
        self.assertFalse(pipeline_name in pipeline_names)

        pipe = PipelineCollection().create(
            name=pipeline_name,
            input_bucket=in_bucket,
            output_bucket=out_bucket,
            role=role.arn,
            notifications={
                'Completed': '',
                'Error': '',
                'Warning': '',
                'Progressing': '',
            }
        )
        pipeline_id = pipe.id

        pipelines = PipelineCollection().each()
        pipeline_names = [pipe.name for pipe in pipelines]
        self.assertTrue(pipeline_name in pipeline_names)

        pipeline = Pipeline(id=pipeline_id)
        pipeline.get()
        self.assertEqual(pipeline.name, pipeline_name)

        resp = pipeline.update_status(status='Paused')
        self.assertEqual(resp['Pipeline']['Status'], 'Paused')

########NEW FILE########
__FILENAME__ = test_connection
# -*- coding: utf-8 -*-
from tests.integration.base import ConnectionTestCase
from tests import unittest


class IamConnectionTestCase(ConnectionTestCase, unittest.TestCase):
    service_name = 'iam'
    ops = [
        'add_role_to_instance_profile',
        'add_user_to_group',
        'change_password',
        'create_access_key',
        'create_account_alias',
        'create_group',
        'create_instance_profile',
        'create_login_profile',
        'create_role',
        'create_user',
        'create_virtual_mfa_device',
        'deactivate_mfa_device',
        'delete_access_key',
        'delete_account_alias',
        'delete_account_password_policy',
        'delete_group',
        'delete_group_policy',
        'delete_instance_profile',
        'delete_login_profile',
        'delete_role',
        'delete_role_policy',
        'delete_server_certificate',
        'delete_signing_certificate',
        'delete_user',
        'delete_user_policy',
        'delete_virtual_mfa_device',
        'enable_mfa_device',
        'get_account_password_policy',
        'get_account_summary',
        'get_group',
        'get_group_policy',
        'get_instance_profile',
        'get_login_profile',
        'get_role',
        'get_role_policy',
        'get_server_certificate',
        'get_user',
        'get_user_policy',
        'list_access_keys',
        'list_account_aliases',
        'list_group_policies',
        'list_groups',
        'list_groups_for_user',
        'list_instance_profiles',
        'list_instance_profiles_for_role',
        'list_mfa_devices',
        'list_role_policies',
        'list_roles',
        'list_server_certificates',
        'list_signing_certificates',
        'list_user_policies',
        'list_users',
        'list_virtual_mfa_devices',
        'put_group_policy',
        'put_role_policy',
        'put_user_policy',
        'remove_role_from_instance_profile',
        'remove_user_from_group',
        'resync_mfa_device',
        'update_access_key',
        'update_account_password_policy',
        'update_assume_role_policy',
        'update_group',
        'update_login_profile',
        'update_server_certificate',
        'update_signing_certificate',
        'update_user',
        'upload_server_certificate',
        'upload_signing_certificate',
    ]

    def test_integration(self):
        user_name = 'test_user'
        group_name = 'test_group'

        resp = self.conn.create_group(
            group_name=group_name
        )

        self.addCleanup(
            self.conn.delete_group,
            group_name=group_name
        )

        resp = self.conn.list_groups()
        groups = [group['GroupName'] for group in resp['Groups']]
        self.assertTrue(group_name in groups)

        resp = self.conn.create_user(
            user_name=user_name
        )

        self.addCleanup(
            self.conn.delete_user,
            user_name=user_name
        )

        resp = self.conn.list_users()
        users = [user['UserName'] for user in resp['Users']]
        self.assertTrue(user_name in users)

        # Make sure there are no users.
        resp = self.conn.get_group(group_name=group_name)
        self.assertEqual(len(resp['Users']), 0)

        # Try adding the user to a group.
        resp = self.conn.add_user_to_group(
            user_name=user_name,
            group_name=group_name
        )
        self.addCleanup(
            self.conn.remove_user_from_group,
            user_name=user_name,
            group_name=group_name
        )

        resp = self.conn.get_group(group_name=group_name)
        self.assertEqual(len(resp['Users']), 1)
        self.assertTrue(resp['Users'][0]['UserName'], user_name)

########NEW FILE########
__FILENAME__ = test_resources
import time

import boto3
from boto3.iam.resources import GroupCollection, UserCollection
from boto3.iam.resources import Group, User

from tests import unittest


class IamIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        super(IamIntegrationTestCase, self).setUp()
        self.conn = boto3.session.connect_to('iam')

    def test_integration(self):
        user_name = 'test_user'
        group_name = 'test_group'

        group = GroupCollection(connection=self.conn).create(
            group_name=group_name
        )
        self.addCleanup(
            group.delete
        )

        groups = GroupCollection(connection=self.conn).each()
        group_names = [group.group_name for group in groups]
        self.assertTrue(group_name in group_names)

        user = UserCollection(connection=self.conn).create(
            user_name=user_name
        )
        self.addCleanup(
            user.delete
        )

        users = UserCollection(connection=self.conn).each()
        user_names = [user.user_name for user in users]
        self.assertTrue(user_name in user_names)

        # Make sure there are no users.
        group = Group(connection=self.conn, group_name=group_name)
        group.get()
        self.assertEqual(len(group.users), 0)

        # Try adding the user to a group.
        resp = group.add_user(
            user_name=user_name
        )
        self.addCleanup(
            group.remove_user,
            user_name=user_name
        )

        # Fetch the updated information
        group = Group(connection=self.conn, group_name=group_name)
        group.get()
        self.assertEqual(len(group.users), 1)
        self.assertTrue(group.users[0]['UserName'], user_name)

########NEW FILE########
__FILENAME__ = test_connection
# -*- coding: utf-8 -*-
import time

from boto3.s3.utils import force_delete_bucket
from boto3.utils import six

from tests.integration.base import ConnectionTestCase
from tests import unittest


class S3ConnectionTestCase(ConnectionTestCase, unittest.TestCase):
    service_name = 's3'
    ops = [
        'abort_multipart_upload',
        'complete_multipart_upload',
        'copy_object',
        'create_bucket',
        'create_multipart_upload',
        'delete_bucket',
        'delete_bucket_cors',
        'delete_bucket_lifecycle',
        'delete_bucket_policy',
        'delete_bucket_tagging',
        'delete_bucket_website',
        'delete_object',
        'delete_objects',
        'get_bucket_acl',
        'get_bucket_cors',
        'get_bucket_lifecycle',
        'get_bucket_location',
        'get_bucket_logging',
        'get_bucket_notification',
        'get_bucket_policy',
        'get_bucket_request_payment',
        'get_bucket_tagging',
        'get_bucket_versioning',
        'get_bucket_website',
        'get_object',
        'get_object_acl',
        'get_object_torrent',
        'head_bucket',
        'head_object',
        'list_buckets',
        'list_multipart_uploads',
        'list_object_versions',
        'list_objects',
        'list_parts',
        'put_bucket_acl',
        'put_bucket_cors',
        'put_bucket_lifecycle',
        'put_bucket_logging',
        'put_bucket_notification',
        'put_bucket_policy',
        'put_bucket_request_payment',
        'put_bucket_tagging',
        'put_bucket_versioning',
        'put_bucket_website',
        'put_object',
        'put_object_acl',
        'restore_object',
        'upload_part',
        'upload_part_copy'
    ]

    def test_integration(self):
        bucket_name = 'boto3_test_s3_{0}'.format(time.time())
        key_name = 'hello.txt'

        resp = self.conn.create_bucket(
            bucket=bucket_name
        )

        self.addCleanup(
            force_delete_bucket,
            conn=self.conn,
            bucket_name=bucket_name
        )

        # FIXME: Needs 100% more waiters.
        time.sleep(5)

        buckets = [buck['Name'] for buck in self.conn.list_buckets()['Buckets']]
        self.assertTrue(bucket_name in buckets)

        self.conn.put_object(
            bucket=bucket_name,
            key=key_name,
            body='Some test data'
            # FIXME: This fails miserably with Unicode. Neither of the following
            #        work. Figure out what the right solution is.
            # body=u'Some test data about ☃'
            # body=u'Some test data about ☃'.encode('utf-8')
        )
        time.sleep(5)

        s3_object = self.conn.get_object(
            bucket=bucket_name,
            key=key_name
        )
        body = s3_object['Body'].read()
        self.assertEqual(body, b'Some test data')
        # body = s3_object['Body'].read().decode('utf-8')
        # self.assertEqual(body, u'Some test data about ☃')

########NEW FILE########
__FILENAME__ = test_resources
import time

import boto3
from boto3.s3.resources import BucketCollection, S3ObjectCollection
from boto3.s3.resources import Bucket, S3Object
from boto3.s3.utils import force_delete_bucket

from tests import unittest


class S3IntegrationTestCase(unittest.TestCase):
    def setUp(self):
        super(S3IntegrationTestCase, self).setUp()
        self.conn = boto3.session.connect_to('s3', region_name='us-west-2')

    def test_integration(self):
        bucket_name = 'boto3-s3-resources-{0}'.format(int(time.time()))
        key_name = 'test_key'

        bucket = BucketCollection(connection=self.conn).create(
            bucket=bucket_name,
            create_bucket_configuration={
                'LocationConstraint': 'us-west-2'
            }
        )
        self.addCleanup(
            force_delete_bucket,
            conn=self.conn,
            bucket_name=bucket_name
        )

        # FIXME: Needs 100% more waiters.
        time.sleep(5)

        self.assertTrue(isinstance(bucket, Bucket))
        # FIXME: This should be assigned to the instance as part of the call
        #        to ``create``.
        #        For now, just assign it the ugly way.
        # self.assertTrue(bucket.bucket, bucket_name)
        bucket._data['bucket'] = bucket_name
        self.assertTrue(bucket_name in bucket.location)

        obj = S3ObjectCollection(
            connection=self.conn,
            # FIXME: This should be passable as an object without having to
            #        pass specific data.
            bucket=bucket_name
        ).create(
            key=key_name,
            body="THIS IS A TRIUMPH"
        )
        self.assertTrue(isinstance(obj, S3Object))

        # FIXME: Needs 100% more waiters.
        time.sleep(5)

        obj = S3Object(
            connection=self.conn,
            # FIXME: This should be passable as an object without having to
            #        pass specific data.
            bucket=bucket_name,
            key=key_name
        )
        # Update from the service.
        resp = obj.get()

        self.assertTrue(isinstance(obj, S3Object))
        # FIXME: We get a bytestring back rather than a Unicode string.
        #        Is this intended behavior?
        self.assertEqual(obj.get_content(), b'THIS IS A TRIUMPH')
        # self.assertEqual(obj.get_content(), 'THIS IS A TRIUMPH')

        # Test travering relations.
        # FIXME: A side-effect of moving ``.get(...)`` to the instance is that
        #        chained relation traversal is a whole lot **less** useful.
        found = False

        for rel_obj in bucket.objects.each():
            if rel_obj.key == key_name:
                found = True
                break

        self.assertTrue(found)
        self.assertTrue(isinstance(rel_obj, S3Object))
        self.assertEqual(rel_obj.e_tag, '"07366f249e11262705e4964e03873078"')

########NEW FILE########
__FILENAME__ = test_connection
import time

from boto3.sns.utils import subscribe_sqs_queue
from boto3.sqs.utils import convert_queue_url_to_arn
from boto3.utils import json

from tests.integration.base import ConnectionTestCase
from tests import unittest


class SNSConnectionTestCase(ConnectionTestCase, unittest.TestCase):
    service_name = 'sns'
    ops = [
        'add_permission',
        'confirm_subscription',
        'connect_to',
        'create_platform_application',
        'create_platform_endpoint',
        'create_topic',
        'delete_endpoint',
        'delete_platform_application',
        'delete_topic',
        'get_endpoint_attributes',
        'get_platform_application_attributes',
        'get_subscription_attributes',
        'get_topic_attributes',
        'list_endpoints_by_platform_application',
        'list_platform_applications',
        'list_subscriptions',
        'list_subscriptions_by_topic',
        'list_topics',
        'publish',
        'remove_permission',
        'set_endpoint_attributes',
        'set_platform_application_attributes',
        'set_subscription_attributes',
        'set_topic_attributes',
        'subscribe',
        'unsubscribe',
    ]

    def test_integration(self):
        name = 'boto3_lives'
        topic_arn = self.conn.create_topic(
            name=name
        )['TopicArn']

        self.addCleanup(self.conn.delete_topic, topic_arn=topic_arn)

        # FIXME: Needs 100% more waiters.
        time.sleep(5)

        arns = [info['TopicArn'] for info in self.conn.list_topics()['Topics']]
        self.assertTrue(topic_arn in arns)

        # Subscribe first, so we get the notification.
        # To get the notification, we'll create an SQS queue it can deliver to.
        sqs = self.session.connect_to('sqs')
        url = sqs.create_queue(queue_name='boto3_sns_test')['QueueUrl']
        self.addCleanup(sqs.delete_queue, queue_url=url)
        queue_arn = convert_queue_url_to_arn(sqs, url)

        # Run the convenience method to do all the kinda-painful SNS/SQS setup.
        subscribe_sqs_queue(
            self.conn,
            sqs,
            topic_arn,
            url,
            queue_arn
        )

        # Now publish a test message.
        self.conn.publish(
            topic_arn=topic_arn,
            message=json.dumps({
                'default': 'This is a test.'
            })
        )
        time.sleep(5)

        # Ensure the publish succeeded.
        messages = sqs.receive_message(
            queue_url=url
        )
        self.assertTrue(len(messages['Messages']) > 0)
        raw_body = messages['Messages'][0]['Body']
        body = json.loads(raw_body)
        msg = json.loads(body.get('Message', '{}'))
        self.assertEqual(msg, {'default': 'This is a test.'})

########NEW FILE########
__FILENAME__ = test_resources
import time

import boto3
from boto3.sns.utils import subscribe_sqs_queue
from boto3.sqs.utils import convert_queue_url_to_arn
from boto3.utils import json

from tests import unittest


class SNSIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        super(SNSIntegrationTestCase, self).setUp()
        self.conn = boto3.session.connect_to('sns', region_name='us-west-2')
        # TODO: We'll use a low-level SQS connection for now, since that will
        #       insulate these tests from failures in the SQS resource layer.
        #       Eventually, we should make sure that the higher-level resources
        #       play together well.
        self.sqs = boto3.session.connect_to('sqs', region_name='us-west-2')

    def test_integration(self):
        TopicCollection = boto3.session.get_collection(
            'sns',
            'TopicCollection'
        )
        Topic = boto3.session.get_resource('sns', 'Topic')
        SubscriptionCollection = boto3.session.get_collection(
            'sns',
            'SubscriptionCollection'
        )
        Subscription = boto3.session.get_resource('sns', 'Subscription')

        topic = TopicCollection(connection=self.conn).create(
            name='my_test_topic'
        )
        self.addCleanup(topic.delete)

        # FIXME: Needs 100% more waiters.
        time.sleep(5)

        self.assertTrue(isinstance(topic, Topic))
        self.assertTrue(':my_test_topic' in topic.topic_arn)

        url = self.sqs.create_queue(queue_name='sns_test')['QueueUrl']
        self.addCleanup(self.sqs.delete_queue, queue_url=url)

        # TODO: For now, we'll lean on the utility method.
        #       This should be built into the resource objects, but more thought
        #       is needed on how to manage extension.
        #       Ideally, this looks like something to the effect of:
        #           subscription = SubscriptionCollection().create_with_sqs(
        #               topic=topic_instance,
        #               queue=queue_instance
        #           )
        queue_arn = convert_queue_url_to_arn(self.sqs, url)
        subscribe_sqs_queue(
            self.conn,
            self.sqs,
            topic.get_identifiers()['topic_arn'],
            url,
            queue_arn
        )

        # Now publish a message to the topic.
        result = topic.publish(
            message=json.dumps({
                'default': 'This is a notification!',
            })
        )

        # FIXME: Needs 100% more waiters.
        time.sleep(5)

        # Then check the queue for the message.
        messages = self.sqs.receive_message(
            queue_url=url
        )
        self.assertTrue(len(messages['Messages']) > 0)
        raw_body = messages['Messages'][0]['Body']
        body = json.loads(raw_body)
        msg = json.loads(body.get('Message', '{}'))
        self.assertEqual(msg, {'default': 'This is a notification!'})

########NEW FILE########
__FILENAME__ = test_connection
import time

from tests.integration.base import ConnectionTestCase
from tests import unittest


class SQSConnectionTestCase(ConnectionTestCase, unittest.TestCase):
    service_name = 'sqs'
    ops = [
        'add_permission',
        'change_message_visibility',
        'change_message_visibility_batch',
        'create_queue',
        'delete_message',
        'delete_message_batch',
        'delete_queue',
        'get_queue_attributes',
        'get_queue_url',
        'list_queues',
        'receive_message',
        'remove_permission',
        'send_message',
        'send_message_batch',
        'set_queue_attributes',
    ]

    def test_integration(self):
        name = 'boto3_lives'
        url = self.conn.create_queue(
            queue_name=name
        )['QueueUrl']

        self.addCleanup(self.conn.delete_queue, queue_url=url)

        # FIXME: Needs 100% more waiters.
        time.sleep(5)

        urls = self.conn.list_queues()['QueueUrls']
        self.assertTrue(url in urls)

        self.conn.send_message(
            queue_url=url,
            message_body='Does it work?'
        )
        time.sleep(5)

        messages = self.conn.receive_message(
            queue_url=url
        )
        self.assertEqual(messages['Messages'][0]['Body'], 'Does it work?')

########NEW FILE########
__FILENAME__ = test_resources
import time

import boto3

from tests import unittest


class SQSIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        super(SQSIntegrationTestCase, self).setUp()
        self.conn = boto3.session.connect_to('sqs', region_name='us-west-2')

    def test_integration(self):
        QueueCollection = boto3.session.get_collection(
            'sqs',
            'QueueCollection'
        )
        Queue = boto3.session.get_resource('sqs', 'Queue')
        MessageCollection = boto3.session.get_collection(
            'sqs',
            'MessageCollection'
        )
        Message = boto3.session.get_resource('sqs', 'Message')

        queue = QueueCollection(connection=self.conn).create(
            queue_name='my_test_queue'
        )
        self.addCleanup(queue.delete)

        # FIXME: Needs 100% more waiters.
        time.sleep(5)

        self.assertTrue(isinstance(queue, Queue))
        self.assertTrue('/my_test_queue' in queue.queue_url)

        msg = MessageCollection(
            connection=self.conn,
            # FIXME: This should be passable as an object without having to
            #        pass specific data.
            queue_url=queue.queue_url
        ).create(
            message_body="THIS IS A TRIUMPH"
        )
        self.assertTrue(isinstance(msg, Message))
        self.assertEqual(
            msg.md5_of_message_body,
            '07366f249e11262705e4964e03873078'
        )

        # FIXME: Needs 100% more waiters.
        time.sleep(5)

        msgs = MessageCollection(
            connection=self.conn,
            queue_url=queue.queue_url
        ).each()
        self.assertTrue(isinstance(msgs[0], Message))
        self.assertEqual(msgs[0].body, "THIS IS A TRIUMPH")

########NEW FILE########
__FILENAME__ = test_utils
import boto3
from boto3.sqs.utils import convert_queue_url_to_arn

from tests import unittest


class SQSUtilsTestCase(unittest.TestCase):
    def test_convert_queue_url_to_arn(self):
        sqs = boto3.session.connect_to('sqs')
        url = 'https://queue.amazonaws.com/099270012/test_test_test'
        self.assertEqual(
            convert_queue_url_to_arn(sqs, url),
            'arn:aws:sqs:us-east-1:099270012:test_test_test'
        )

########NEW FILE########
__FILENAME__ = test_cache
from boto3.core.cache import ServiceCache
from boto3.core.collections import Collection
from boto3.core.exceptions import NotCached
from boto3.core.resources import Resource

from tests import unittest


# Classes for identity tests.
class TestConnection(object): pass
class AnotherTestConnection(TestConnection): pass
class TestResource(Resource): pass
class AnotherTestResource(Resource): pass
class TestCollection(Collection): pass
class AnotherTestCollection(Collection): pass


class ServiceCacheTestCase(unittest.TestCase):
    def setUp(self):
        super(ServiceCacheTestCase, self).setUp()
        self.cache = ServiceCache()

    def test_init(self):
        self.assertEqual(self.cache.services, {})

    def test_str(self):
        self.assertEqual(str(self.cache), 'ServiceCache: ')

        # Now register some stuff.
        self.cache.set_connection('sqs', TestConnection)
        self.cache.set_connection('sns', AnotherTestConnection)

        self.assertEqual(str(self.cache), 'ServiceCache: sns, sqs')

    def test_len(self):
        self.assertEqual(len(self.cache), 0)

        # Now register some stuff.
        self.cache.set_connection('sqs', TestConnection)
        self.cache.set_connection('sns', AnotherTestConnection)

        self.assertEqual(len(self.cache), 2)

        # Registering more under a service doesn't change the count.
        self.cache.set_resource('sqs', 'Test', TestResource)
        self.assertEqual(len(self.cache), 2)

    def test_contains(self):
        self.assertFalse('sqs' in self.cache)

        # Now register some stuff.
        self.cache.set_connection('sqs', TestConnection)
        self.cache.set_connection('sns', AnotherTestConnection)

        self.assertTrue('sqs' in self.cache)

    def test_get_connection(self):
        self.cache.services = {
            'sqs': {
                'connection': TestConnection,
            }
        }

        self.assertEqual(self.cache.get_connection('sqs'), TestConnection)

    def test_get_connection_missing(self):
        self.assertEqual(len(self.cache.services), 0)

        # Unpopulated.
        with self.assertRaises(NotCached):
            self.cache.get_connection('sns')

        # Partially populated.
        self.cache.services['sns'] = {}

        with self.assertRaises(NotCached):
            self.cache.get_connection('sns')

    def test_set_connection(self):
        self.assertEqual(len(self.cache.services), 0)

        self.cache.set_connection('sqs', TestConnection)
        self.assertEqual(self.cache.services, {
            'sqs': {
                'connection': TestConnection,
            },
        })

        # Test a second.
        self.cache.set_connection('sns', AnotherTestConnection)
        self.assertEqual(self.cache.services, {
            'sqs': {
                'connection': TestConnection,
            },
            'sns': {
                'connection': AnotherTestConnection,
            },
        })

    def test_del_connection(self):
        self.cache.services = {
            'sqs': {
                'connection': TestConnection,
            },
            'sns': {
                'connection': AnotherTestConnection,
            },
        }

        self.cache.del_connection('sqs')
        self.assertEqual(self.cache.services, {
            'sqs': {},
            'sns': {
                'connection': AnotherTestConnection,
            },
        })

        # Delete it again. Shouldn't error.
        self.cache.del_connection('sqs')

        # Delete a non-existent service.
        self.cache.del_connection('elastictranscoder')

        self.assertEqual(self.cache.services, {
            'sqs': {},
            'sns': {
                'connection': AnotherTestConnection,
            },
        })

    def test_get_resource(self):
        self.cache.services = {
            'sqs': {
                'resources': {
                    'Test': {
                        'default': TestResource,
                    },
                },
            },
        }

        self.assertEqual(self.cache.get_resource('sqs', 'Test'), TestResource)

    def test_get_resource_missing(self):
        self.assertEqual(len(self.cache.services), 0)

        # Unpopulated.
        with self.assertRaises(NotCached):
            self.cache.get_resource('sns', 'Test')

        # Partially populated.
        self.cache.services['sns'] = {}

        with self.assertRaises(NotCached):
            self.cache.get_resource('sns', 'Test')

        self.cache.services['sns'] = {
            'resources': {},
        }

        with self.assertRaises(NotCached):
            self.cache.get_resource('sns', 'Test')

    def test_set_resource(self):
        self.assertEqual(len(self.cache.services), 0)

        self.cache.set_resource('sqs', 'Test', TestResource)
        self.assertEqual(self.cache.services, {
            'sqs': {
                'resources': {
                    'Test': {
                        'default': TestResource,
                    },
                },
            },
        })

        # Test a second.
        self.cache.set_resource('sns', 'AnotherTest', AnotherTestResource)
        self.assertEqual(self.cache.services, {
            'sqs': {
                'resources': {
                    'Test': {
                        'default': TestResource,
                    },
                },
            },
            'sns': {
                'resources': {
                    'AnotherTest': {
                        'default': AnotherTestResource,
                    },
                },
            },
        })

    def test_del_resource(self):
        self.cache.services = {
            'sqs': {
                'resources': {
                    'Test': {
                        'default': TestResource,
                    },
                },
            },
            'sns': {
                'resources': {
                    'AnotherTest': {
                        'default': AnotherTestResource,
                    },
                },
            },
        }

        self.cache.del_resource('sqs', 'Test')
        self.assertEqual(self.cache.services, {
            'sqs': {
                'resources': {
                    'Test': {},
                },
            },
            'sns': {
                'resources': {
                    'AnotherTest': {
                        'default': AnotherTestResource,
                    },
                },
            },
        })

        # Delete it again. Shouldn't error.
        self.cache.del_resource('sqs', 'Test')

        # Delete a non-existent service.
        self.cache.del_resource('elastictranscoder', 'Pipeline')

        self.assertEqual(self.cache.services, {
            'sqs': {
                'resources': {
                    'Test': {},
                },
            },
            'sns': {
                'resources': {
                    'AnotherTest': {
                        'default': AnotherTestResource,
                    },
                },
            },
        })

    def test_get_collection(self):
        self.cache.services = {
            'sqs': {
                'collections': {
                    'Test': {
                        'default': TestCollection,
                    },
                },
            }
        }

        self.assertEqual(
            self.cache.get_collection('sqs', 'Test'),
            TestCollection
        )

    def test_get_collection_missing(self):
        self.assertEqual(len(self.cache.services), 0)

        # Unpopulated.
        with self.assertRaises(NotCached):
            self.cache.get_collection('sns', 'Test')

        # Partially populated.
        self.cache.services['sns'] = {}

        with self.assertRaises(NotCached):
            self.cache.get_collection('sns', 'Test')

    def test_set_collection(self):
        self.assertEqual(len(self.cache.services), 0)

        self.cache.set_collection('sqs', 'Test', TestCollection)
        self.assertEqual(self.cache.services, {
            'sqs': {
                'collections': {
                    'Test': {
                        'default': TestCollection,
                    },
                },
            },
        })

        # Test a second.
        self.cache.set_collection('sns', 'AnotherTest', AnotherTestCollection)
        self.assertEqual(self.cache.services, {
            'sqs': {
                'collections': {
                    'Test': {
                        'default': TestCollection,
                    },
                },
            },
            'sns': {
                'collections': {
                    'AnotherTest': {
                        'default': AnotherTestCollection,
                    },
                },
            },
        })

    def test_del_collection(self):
        self.cache.services = {
            'sqs': {
                'collections': {
                    'Test': {
                        'default': TestCollection,
                    },
                },
            },
            'sns': {
                'collections': {
                    'AnotherTest': {
                        'default': AnotherTestCollection,
                    },
                },
            },
        }

        self.cache.del_collection('sqs', 'Test')
        self.assertEqual(self.cache.services, {
            'sqs': {
                'collections': {
                    'Test': {},
                },
            },
            'sns': {
                'collections': {
                    'AnotherTest': {
                        'default': AnotherTestCollection,
                    },
                },
            },
        })

        # Delete it again. Shouldn't error.
        self.cache.del_collection('sqs', 'Test')

        # Delete a non-existent service.
        self.cache.del_collection('elastictranscoder', 'Pipeline')

        self.assertEqual(self.cache.services, {
            'sqs': {
                'collections': {
                    'Test': {},
                },
            },
            'sns': {
                'collections': {
                    'AnotherTest': {
                        'default': AnotherTestCollection,
                    },
                },
            },
        })

    def test_integration(self):
        self.assertEqual(len(self.cache.services), 0)

        # Do a bunch of semi-complex things & make sure nothing stomps on
        # each other's toes.
        self.cache.set_connection('sqs', AnotherTestConnection)
        self.cache.set_resource('sqs', 'Queue', TestResource)
        self.cache.set_connection('sqs', TestConnection)
        self.cache.set_resource('sqs', 'Message', AnotherTestResource)
        self.cache.del_resource('sqs', 'Message')
        self.cache.set_collection(
            'sqs',
            'QueueCollection',
            AnotherTestCollection
        )
        self.cache.set_resource('sqs', 'Message', TestResource)

        self.cache.set_connection('sns', TestConnection)
        self.cache.set_connection('sns', AnotherTestConnection)
        self.cache.set_connection('sns', TestConnection)

        self.cache.set_collection(
            'elastictranscoder',
            'PipelineCollection',
            AnotherTestCollection
        )

        self.assertEqual(self.cache.services, {
            'sns': {
                'connection': TestConnection,
            },
            'elastictranscoder': {
                'collections': {
                    'PipelineCollection': {
                        'default': AnotherTestCollection,
                    },
                },
            },
            'sqs': {
                'resources': {
                    'Message': {
                        'default': TestResource,
                    },
                    'Queue': {
                        'default': TestResource,
                    },
                },
                'collections': {
                    'QueueCollection': {
                        'default': AnotherTestCollection,
                    },
                },
                'connection': TestConnection,
            }
        })

########NEW FILE########
__FILENAME__ = test_collections
import mock
import os

from boto3.core.connection import ConnectionFactory
from boto3.core.constants import DEFAULT_DOCSTRING
from boto3.core.exceptions import APIVersionMismatchError, NoSuchMethod
from boto3.core.collections import ResourceJSONLoader, CollectionDetails
from boto3.core.collections import Collection, CollectionFactory
from boto3.core.resources import Resource, ResourceDetails
from boto3.core.session import Session

from tests import unittest
from tests.unit.fakes import FakeParam, FakeOperation, FakeService, FakeSession


class TestCoreService(FakeService):
    api_version = '2013-08-23'
    operations = [
        FakeOperation(
            'CreateQueue',
            " <p>Creates a queue.</p>\n ",
            params=[
                FakeParam('QueueName', required=True, ptype='string'),
                FakeParam('Attributes', required=False, ptype='map'),
            ],
            output={
                'shape_name': 'CreateQueueResult',
                'type': 'structure',
                'members': {
                    'QueueUrl': {
                        'shape_name': 'String',
                        'type': 'string',
                        'documentation': '\n    <p>The URL for the created SQS queue.</p>\n  ',
                    },
                },
            },
            result=(None, {
                'QueueUrl': 'http://example.com',
            })
        ),
        FakeOperation(
            'SendMessage',
            " <p>Sends a message to a queue.</p>\n ",
            params=[
                FakeParam('QueueName', required=True, ptype='string'),
                FakeParam('MessageBody', required=True, ptype='string'),
                FakeParam('MessageType', required=False, ptype='string'),
            ],
            output=True,
            result=(None, True)
        ),
        FakeOperation(
            'ReceiveMessage',
            " something something something ",
            params=[
                FakeParam('QueueUrl', required=True, ptype='string'),
                FakeParam('AttributeNames', required=False, ptype='list'),
                FakeParam('MaxNumberOfMessages', required=False, ptype='integer'),
                FakeParam('VisibilityTimeout', required=False, ptype='integer'),
                FakeParam('WaitTimeSeconds', required=False, ptype='integer'),
            ],
            output={
                'shape_name': 'ReceiveMessageResult',
                'type': 'structure',
                'members': {
                    'Messages': {
                        'shape_name': 'MessageList',
                        'type': 'list',
                        'members': {
                            'shape_name': 'Message',
                            'type': 'structure',
                            'members': {
                                'MessageId': {
                                    'shape_name': 'String',
                                    'type': 'string',
                                    'documentation': None
                                },
                                'ReceiptHandle': {
                                    'shape_name': 'String',
                                    'type': 'string',
                                    'documentation': None
                                },
                                'MD5OfBody': {
                                    'shape_name': 'String',
                                    'type': 'string',
                                    'documentation': None
                                },
                                'Body': {
                                    'shape_name': 'String',
                                    'type': 'string',
                                    'documentation': None
                                },
                                'Attributes': {
                                    'shape_name': 'AttributeMap',
                                    'type': 'map',
                                    'keys': {
                                        'shape_name': 'QueueAttributeName',
                                        'type': 'string',
                                        'enum': [
                                            'Policy',
                                            'VisibilityTimeout',
                                            'MaximumMessageSize',
                                            'MessageRetentionPeriod',
                                            'ApproximateNumberOfMessages',
                                            'ApproximateNumberOfMessagesNotVisible',
                                            'CreatedTimestamp',
                                            'LastModifiedTimestamp',
                                            'QueueArn',
                                            'ApproximateNumberOfMessagesDelayed',
                                            'DelaySeconds',
                                            'ReceiveMessageWaitTimeSeconds'
                                        ],
                                        'documentation': '\n    <p>The name of a queue attribute.</p>\n  ',
                                        'xmlname': 'Name'
                                    },
                                    'members': {
                                        'shape_name': 'String',
                                        'type': 'string',
                                        'documentation': '\n    <p>The value of a queue attribute.</p>\n  ',
                                        'xmlname': 'Value'
                                    },
                                    'flattened': True,
                                    'xmlname': 'Attribute',
                                    'documentation': None,
                                },
                            },
                            'documentation': None,
                            'xmlname': 'Message'
                        },
                        'flattened': True,
                        'documentation': '\n    <p>A list of messages.</p>\n  '
                    }
                },
                'documentation': None
            },
            result=(None, {
                'Messages': [
                    {
                        'MessageId': 'msg-12345',
                        'ReceiptHandle': 'hndl-12345',
                        'MD5OfBody': '6cd3556deb0da54bca060b4c39479839',
                        'Body': 'Hello, world!',
                        'Attributes': {
                            'QueueArn': 'arn:aws:example:example:sqs:something',
                            'ApproximateNumberOfMessagesDelayed': '2',
                            'DelaySeconds': '10',
                            'CreatedTimestamp': '2013-10-17T21:52:46Z',
                            'LastModifiedTimestamp': '2013-10-17T21:52:46Z',
                        },
                    },
                    {
                        'MessageId': 'msg-12346',
                        'ReceiptHandle': 'hndl-12346',
                        'MD5OfBody': '6cd355',
                        'Body': 'Another message!',
                        'Attributes': {},
                    },
                ]
            })
        ),
        FakeOperation(
            'DeleteQueue',
            " <p>Deletes a queue.</p>\n ",
            params=[
                FakeParam('QueueName', required=True, ptype='string'),
            ],
            output=True,
            result=(None, True)
        ),
    ]


class CollectionDetailsTestCase(unittest.TestCase):
    def setUp(self):
        super(CollectionDetailsTestCase, self).setUp()
        self.test_dirs = [
            os.path.join(os.path.dirname(__file__), 'test_data')
        ]
        self.test_loader = ResourceJSONLoader(self.test_dirs)
        self.session = Session(FakeSession(TestCoreService()))

        self.cd = CollectionDetails(
            self.session,
            'test',
            'PipelineCollection',
            loader=self.test_loader
        )

        # Fake some identifiers in.
        self.alt_cd = CollectionDetails(
            self.session,
            'test',
            'JobCollection',
            loader=self.test_loader
        )
        self.alt_cd._loaded_data = {
            'api_version': 'something',
            'collections': {
                'JobCollection': {
                    'resource': 'Job',
                    'identifiers': [
                        {
                            'var_name': 'pipeline',
                            'api_name': '$whatever.Pipeline',
                        },
                        {
                            'var_name': 'id',
                            'api_name': 'Id',
                        },
                    ],
                    'operations': {}
                }
            }
        }

    def test_init(self):
        self.assertEqual(self.cd.session, self.session)
        self.assertEqual(self.cd.service_name, 'test')
        self.assertEqual(self.cd.loader, self.test_loader)
        self.assertEqual(self.cd._loaded_data, None)
        self.assertEqual(self.cd._api_version, None)

    def test_service_data_uncached(self):
        self.assertEqual(self.cd._loaded_data, None)

        data = self.cd.service_data
        self.assertEqual(len(data.keys()), 4)
        self.assertTrue('api_version' in self.cd._loaded_data)

    def test_collection_data_uncached(self):
        self.assertEqual(self.cd._loaded_data, None)

        data = self.cd.collection_data
        self.assertEqual(len(data.keys()), 2)
        self.assertFalse('identifier' in data)
        self.assertTrue('operations' in data)
        self.assertTrue('api_version' in self.cd._loaded_data)

    def test_api_version_uncached(self):
        self.assertEqual(self.cd._api_version, None)

        av = self.cd.api_version
        self.assertEqual(av, '2013-11-27')
        self.assertEqual(self.cd._api_version, '2013-11-27')

    def test_identifiers(self):
        self.assertEqual(self.cd.identifiers, [])

        # Now with something with identifiers.
        self.assertEqual(self.alt_cd.identifiers, [
            {
                'api_name': '$whatever.Pipeline',
                'var_name': 'pipeline',
            },
            {
                'api_name': 'Id',
                'var_name': 'id',
            }
        ])

    def test_result_key_for(self):
        # Non-existent
        self.assertEqual(self.cd.result_key_for('notthere'), None)

        # Now with actual data.
        self.assertEqual(self.cd.result_key_for('create'), 'Pipeline')
        self.assertEqual(self.cd.result_key_for('each'), 'Pipelines')

    def test_resource_uncached(self):
        self.assertEqual(self.cd._loaded_data, None)

        res = self.cd.resource
        self.assertEqual(res, 'Pipeline')
        self.assertTrue('api_version' in self.cd._loaded_data)

    def test_cached(self):
        # Fake in data.
        self.cd._loaded_data = {
            'api_version': '20XX-MM-II',
            'hello': 'world',
        }

        data = self.cd.service_data
        av = self.cd.api_version
        self.assertTrue('hello' in data)
        self.assertTrue('20XX-MM-II' in av)


class FakeConn(object):
    def __init__(self, *args, **kwargs):
        super(FakeConn, self).__init__()

    def create_pipeline(self, *args, **kwargs):
        return {
            'RequestId': '1234-1234-1234-1234',
            'Pipeline': {
                'Id': '1872baf45',
                'Title': 'A pipe',
            }
        }


class OopsConn(object):
    # Used to demonstrate when no API methods are available.
    def __init__(self, *args, **kwargs):
        super(OopsConn, self).__init__()


class FakePipeResource(object):
    def __init__(self, **kwargs):
        # Yuck yuck yuck. Fake fake fake.
        self.__dict__.update(kwargs)


class PipeCollection(Collection):
    def create(self, *args, **kwargs):
        return {}

    def update_params(self, conn_method_name, params):
        params['global'] = True
        return super(PipeCollection, self).update_params(conn_method_name, params)

    def update_params_create(self, params):
        params['created'] = True
        return params

    def post_process(self, conn_method_name, result):
        self.identifier = result.get('Id', None)
        return result

    def post_process_create(self, result):
        self.created = True
        return result


class Pipe(Resource):
    pass


class JobCollection(Collection):
    pass


class CollectionTestCase(unittest.TestCase):
    def setUp(self):
        super(CollectionTestCase, self).setUp()
        self.session = Session(FakeSession(TestCoreService()))
        self.fake_details = CollectionDetails(
            self.session,
            'test',
            'PipeCollection'
        )
        self.fake_alt_details = CollectionDetails(
            self.session,
            'test',
            'JobCollection'
        )
        self.fake_res_details = ResourceDetails(
            self.session,
            'test',
            'Pipe'
        )
        self.fake_details._loaded_data = {
            'api_version': 'something',
            'collections': {
                'PipeCollection': {
                    'resource': 'Pipeline',
                    'operations': {
                        'create': {
                            'api_name': 'CreatePipe',
                            'result_key': 'Pipeline'
                        },
                        'each': {
                            'api_name': 'ListPipes',
                            'result_key': 'Pipelines'
                        }
                    }
                },
                'JobCollection': {
                    'resource': 'Job',
                    'identifiers': [
                        {
                            'var_name': 'pipeline',
                            'api_name': '$whatever.Pipeline',
                        },
                        {
                            'var_name': 'id',
                            'api_name': 'Id',
                        },
                    ],
                    'operations': {}
                }
            },
            'resources': {
                'Pipe': {
                    'identifiers': [
                        {
                            'var_name': 'id',
                            'api_name': 'Id',
                        },
                    ],
                    'operations': {
                        'delete': {
                            'api_name': 'DeletePipe'
                        }
                    }
                }
            }
        }
        self.fake_alt_details._loaded_data = self.fake_details._loaded_data
        self.fake_res_details._loaded_data = self.fake_details._loaded_data
        self.fake_conn = FakeConn()

        PipeCollection._details = self.fake_details
        self.collection = PipeCollection(
            connection=self.fake_conn,
            id='1872baf45'
        )
        JobCollection._details = self.fake_alt_details
        self.alt_collection = JobCollection(
            connection=self.fake_conn,
            pipeline='fake-pipe',
            id='8716fc26a'
        )
        Pipe._details = self.fake_res_details
        PipeCollection.change_resource(Pipe)

    def test_get_identifiers(self):
        # No identifiers.
        self.assertEqual(self.collection.get_identifiers(), {})

        # Has identifiers.
        self.assertEqual(self.alt_collection.get_identifiers(), {
            'id': '8716fc26a',
            'pipeline': 'fake-pipe',
        })

    def test_set_identifiers(self):
        self.assertEqual(self.alt_collection._data, {
            'id': '8716fc26a',
            'pipeline': 'fake-pipe',
        })

        # Only sets things found in the identifiers, not random data.
        self.alt_collection.set_identifiers({
            'pipeline': 'something',
            'id': 'hello!',
            'bucket': 'something',
        })
        self.assertEqual(self.alt_collection._data, {
            'id': 'hello!',
            'pipeline': 'something',
        })

    def test_full_update_params(self):
        params = {
            'notify': True,
        }
        prepped = self.collection.full_update_params('create', params)
        self.assertEqual(prepped, {
            'global': True,
            'created': True,
            'notify': True,
        })

    def test_full_post_process(self):
        results = {
            'Id': '1872baf45',
            'Title': 'A pipe',
        }
        processed = self.collection.full_post_process('create', results)
        self.assertEqual(processed, {
            'Id': '1872baf45',
            'Title': 'A pipe'
        })
        self.assertEqual(self.collection.created, True)

        # Now for iteration.
        results = {
            'Pipelines': [
                {
                    'Id': '1872baf45',
                    'Title': 'A pipe',
                },
                {
                    'Id': '91646aee7',
                    'Title': 'Another pipe',
                },
            ],
        }
        pipes = self.collection.full_post_process('each', results)
        self.assertEqual(len(pipes), 2)
        self.assertEqual(pipes[0].id, '1872baf45')
        self.assertEqual(pipes[1].id, '91646aee7')

    def build_resource(self):
        # Reach in to fake some data.
        # We'll test proper behavior with the integration tests.
        self.session.cache.set_resource('test', 'Pipeline', Pipe)

        res_class = self.collection.build_resource({
            'test': 'data'
        })
        self.assertTrue(isinstance(res_class, Pipe))
        self.assertEqual(res_class.test, 'data')

        # Make sure that keys get converted to snake_case.
        res_class = self.collection.build_resource({
            'Test': 'Data',
            'MoreThingsHereRight': 145,
        })
        self.assertTrue(isinstance(res_class, Pipe))
        self.assertEqual(res_class.test, 'Data')
        self.assertEqual(res_class.more_things_here_right, 145)


class CollectionFactoryTestCase(unittest.TestCase):
    def setUp(self):
        super(CollectionFactoryTestCase, self).setUp()
        self.session = Session(FakeSession(TestCoreService()))
        self.test_dirs = [
            os.path.join(os.path.dirname(__file__), 'test_data')
        ]
        self.test_loader = ResourceJSONLoader(self.test_dirs)
        self.cd = CollectionDetails(
            self.session,
            'test',
            'PipelineCollection',
            loader=self.test_loader
        )
        self.cf = CollectionFactory(
            session=self.session,
            loader=self.test_loader
        )

        # Fake in the class.
        self.session.cache.set_resource('test', 'Pipeline', FakePipeResource)

    def test_init(self):
        self.assertEqual(self.cf.session, self.session)
        self.assertTrue(isinstance(self.cf.loader, ResourceJSONLoader))
        self.assertEqual(self.cf.base_collection_class, Collection)
        self.assertEqual(self.cf.details_class, CollectionDetails)

        # Test overrides (invalid for actual usage).
        import boto3
        cf = CollectionFactory(
            loader=False,
            base_collection_class=PipeCollection,
            details_class=True
        )
        self.assertEqual(cf.session, boto3.session)
        self.assertEqual(cf.loader, False)
        self.assertEqual(cf.base_collection_class, PipeCollection)
        self.assertEqual(cf.details_class, True)

    def test_build_class_name(self):
        self.assertEqual(
            self.cf._build_class_name('PipelineCollection'),
            'PipelineCollection'
        )
        self.assertEqual(
            self.cf._build_class_name('TestName'),
            'TestName'
        )

    def test_build_methods(self):
        attrs = self.cf._build_methods(self.cd)
        self.assertEqual(len(attrs), 3)
        self.assertTrue('create' in attrs)
        self.assertTrue('each' in attrs)
        self.assertTrue('test_role' in attrs)

    def test_create_operation_method(self):
        class StubbyCollection(Collection):
            pass

        class StubbyResource(Resource):
            _details = ResourceDetails(
                self.session,
                'test',
                'Pipeline',
                loader=self.test_loader
            )

        op_method = self.cf._create_operation_method('create', {
            "api_name": "CreatePipeline"
        })
        self.assertEqual(op_method.__name__, 'create')
        self.assertEqual(op_method.__doc__, DEFAULT_DOCSTRING)

        # Assign it & call it.
        StubbyCollection._details = self.cd
        StubbyCollection.create = op_method
        StubbyCollection.change_resource(StubbyResource)
        sr = StubbyCollection(connection=FakeConn())
        fake_pipe = sr.create()
        self.assertEqual(fake_pipe.id, '1872baf45')
        self.assertEqual(fake_pipe.title, 'A pipe')

        # Make sure an exception is raised when the underlying connection
        # doesn't have an analogous method.
        sr = StubbyCollection(connection=OopsConn())

        with self.assertRaises(NoSuchMethod):
            fake_pipe = sr.create()

    def test_construct_for(self):
        col_class = self.cf.construct_for('test', 'PipelineCollection')

########NEW FILE########
__FILENAME__ = test_connection
from boto3.core.connection import ConnectionDetails, ConnectionFactory
from boto3.core.exceptions import ServerError
from boto3.core.session import Session

from tests import unittest
from tests.unit.fakes import FakeParam, FakeOperation, FakeService, FakeSession


class TestCoreService(FakeService):
    api_version = '2013-08-23'
    operations = [
        FakeOperation(
            'CreateQueue',
            " <p>Creates a queue.</p>\n ",
            params=[
                FakeParam(
                    'QueueName',
                    required=True,
                    ptype='string',
                    documentation='\n    <p>The name for the queue to be created.</p>\n  '
                ),
                FakeParam('Attributes', required=False, ptype='map'),
            ],
            output={
                'shape_name': 'CreateQueueResult',
                'type': 'structure',
                'members': {
                    'QueueUrl': {
                        'shape_name': 'String',
                        'type': 'string',
                        'documentation': '\n    <p>The URL for the created SQS queue.</p>\n  ',
                    },
                },
            },
            result=(None, {
                'QueueUrl': 'http://example.com',
            })
        ),
        FakeOperation(
            'DeleteQueue',
            " <p>Deletes a queue.</p>\n ",
            params=[
                FakeParam('QueueName', required=True, ptype='string'),
            ],
            output=True,
            result=(None, {'success': True})
        ),
    ]


class ChangedTestCoreService(TestCoreService):
    operations = TestCoreService.operations[1:2]


class ConnectionDetailsTestCase(unittest.TestCase):
    def setUp(self):
        super(ConnectionDetailsTestCase, self).setUp()
        self.session = Session(FakeSession(TestCoreService()))
        self.sd = ConnectionDetails(
            service_name='test',
            session=self.session
        )

    def test_init(self):
        self.assertEqual(self.sd.service_name, 'test')
        self.assertEqual(self.sd.session, self.session)
        self.assertEqual(self.sd._api_version, None)
        self.assertEqual(self.sd._loaded_service_data, None)

    def test_service_data(self):
        self.assertEqual(self.sd._loaded_service_data, None)

        # Access the property. It should load the data, cache it & return it.
        self.assertEqual(len(self.sd.service_data), 2)

        self.assertNotEqual(self.sd._loaded_service_data, None)
        # Ensure the API version was cleared out as well.
        self.assertEqual(self.sd._api_version, None)

    def test_api_version(self):
        self.assertEqual(self.sd._api_version, None)

        # Access the property. It should load the data, cache it & return it.
        self.assertEqual(self.sd.api_version, '2013-08-23')

        self.assertEqual(self.sd._api_version, '2013-08-23')

        # Test the cached version
        self.sd._api_version += 'a'
        self.assertEqual(self.sd.api_version, '2013-08-23a')

    def test__introspect_service(self):
        service_data = self.sd._introspect_service(
            self.session.core_session,
            'test'
        )
        # We test the introspected data elsewhere, so it's enough that we
        # just check the necessary method names are here.
        self.assertEqual(sorted(list(service_data.keys())), [
            'create_queue',
            'delete_queue'
        ])

    def test_reload_service_data(self):
        service_data = self.sd._introspect_service(
            self.session.core_session,
            'test'
        )
        self.assertEqual(sorted(list(service_data.keys())), [
            'create_queue',
            'delete_queue'
        ])

        # Now it changed.
        self.sd.session = Session(FakeSession(ChangedTestCoreService()))
        self.sd.reload_service_data()
        self.assertEqual(sorted(list(self.sd.service_data.keys())), [
            'delete_queue'
        ])


class ConnectionFactoryTestCase(unittest.TestCase):
    def setUp(self):
        super(ConnectionFactoryTestCase, self).setUp()
        self.session = Session(FakeSession(TestCoreService()))
        self.sf = ConnectionFactory(session=self.session)
        self.test_service_class = self.sf.construct_for('test')

    def test__check_method_params(self):
        _cmp = self.test_service_class()._check_method_params
        op_params = [
            {
                'var_name': 'queue_name',
                'api_name': 'QueueName',
                'required': True,
                'type': 'string',
            },
            {
                'var_name': 'attributes',
                'api_name': 'Attributes',
                'required': False,
                'type': 'map',
            },
        ]
        # Missing the required ``queue_name`` parameter.
        self.assertRaises(TypeError, _cmp, op_params)
        self.assertRaises(TypeError, _cmp, op_params, attributes=1)

        # All required params present.
        self.assertEqual(_cmp(op_params, queue_name='boo'), None)
        self.assertEqual(_cmp(op_params, queue_name='boo', attributes=1), None)

    def test__build_service_params(self):
        _bsp = self.test_service_class()._build_service_params
        op_params = [
            {
                'var_name': 'queue_name',
                'api_name': 'QueueName',
                'required': True,
                'type': 'string',
            },
            {
                'var_name': 'attributes',
                'api_name': 'Attributes',
                'required': False,
                'type': 'map',
            },
        ]
        self.assertEqual(_bsp(op_params, queue_name='boo'), {
            'queue_name': 'boo',
        })
        self.assertEqual(_bsp(op_params, queue_name='boo', attributes=1), {
            'queue_name': 'boo',
            'attributes': 1,
        })

    def test__create_operation_method(self):
        func = self.sf._create_operation_method('test', {
            'method_name': 'test',
            'api_name': 'Test',
            'docs': 'This is a test.',
            'params': [],
            'output': True,
        })
        self.assertEqual(func.__name__, 'test')
        self.assertEqual(
            func.__doc__,
            'This is a test.\n:' + \
            'returns: The response data received\n' + \
            ':rtype: dict\n'
        )

    def test__check_for_errors(self):
        cfe = self.test_service_class()._check_for_errors

        # Make sure a success call doesn't throw an exception.
        cfe((None, {'success': True}))

        # With an empty list of errors (S3-style success.
        cfe((None, {'Errors': [], 'success': True}))

        # With a list of errors.
        with self.assertRaises(ServerError) as cm:
            cfe((None, {'Errors': [{'Message': 'Not much.'}]}))

        self.assertEqual(cm.exception.code, 'ConnectionError')
        self.assertEqual(cm.exception.message, 'Not much.')
        self.assertEqual(cm.exception.full_response, {
            'Errors': [{'Message': 'Not much.'}]
        })

        # With a single, detailed error.
        with self.assertRaises(ServerError) as cm:
            cfe((None, {
                'Errors': {
                    'Code': 'FellApart',
                    'Message': 'The robot serving the request fell apart.'
                }
            }))

        self.assertEqual(cm.exception.code, 'FellApart')
        self.assertEqual(
            cm.exception.message,
            'The robot serving the request fell apart.'
        )

        # With an error string.
        with self.assertRaises(ServerError) as cm:
            cfe((None, {'Errors': 'Sadness.'}))

        self.assertEqual(cm.exception.code, 'ConnectionError')
        self.assertEqual(cm.exception.message, 'Sadness.')

    def test__post_process_results(self):
        ppr = self.test_service_class()._post_process_results
        self.assertEqual(ppr('whatever', {}, (None, True)), True)
        self.assertEqual(ppr('whatever', {}, (None, False)), False)
        self.assertEqual(ppr('whatever', {}, (None, 'abc')), 'abc')
        self.assertEqual(ppr('whatever', {}, (None, ['abc', 1])), [
            'abc',
            1
        ])
        self.assertEqual(ppr('whatever', {}, (None, {'abc': 1})), {
            'abc': 1,
        })

    def test_integration(self):
        # Essentially testing ``_build_methods``.
        # This is a painful integration test. If the other methods don't work,
        # this will certainly fail.
        self.assertTrue(hasattr(self.test_service_class, 'create_queue'))
        self.assertTrue(hasattr(self.test_service_class, 'delete_queue'))

        ts = self.test_service_class()

        # Missing required parameters.
        self.assertRaises(TypeError, ts, 'create_queue')
        self.assertRaises(TypeError, ts, 'delete_queue')

        # Successful calls.
        self.assertEqual(ts.create_queue(queue_name='boo'), {
            'QueueUrl': 'http://example.com'
        })
        self.assertEqual(ts.delete_queue(queue_name='boo'), {'success': True})

        # Test the params.
        create_queue_params = ts._get_operation_params('create_queue')
        self.assertEqual(
            [param['var_name'] for param in create_queue_params],
            ['queue_name', 'attributes']
        )

        # Check the docstring.
        self.assertTrue(
            ':param queue_name: The name' in ts.create_queue.__doc__
        )
        self.assertTrue(
            ':type queue_name: string' in ts.create_queue.__doc__
        )

    def test_late_binding(self):
        # If the ``ConnectionDetails`` data changes, it should be reflected in
        # the dynamic methods.
        ts = self.test_service_class()

        # Successful calls.
        self.assertEqual(ts.create_queue(queue_name='boo'), {
            'QueueUrl': 'http://example.com'
        })

        # Now the required params change underneath us.
        # This is ugly/fragile, but also unlikely.
        sd = ts._details._loaded_service_data
        sd['create_queue']['params'][1]['required'] = True

        # Now this call should fail, since there's a new required parameter.
        self.assertRaises(TypeError, ts, 'create_queue')


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_introspection
from boto3.core.introspection import Introspection

from tests import unittest
from tests.unit.fakes import FakeParam, FakeOperation, FakeService, FakeSession


class TestService(FakeService):
    operations = [
        FakeOperation(
            'CreateQueue',
            " <p>Creates a queue.</p>\n ",
            params=[
                FakeParam(
                    'QueueName',
                    required=True,
                    ptype='string',
                    documentation='\n    <p>The name for the queue to be created.</p>\n  '
                ),
                FakeParam('Attributes', required=False, ptype='map'),
            ],
            output={
                'shape_name': 'CreateQueueResult',
                'type': 'structure',
                'members': {
                    'QueueUrl': {
                        'shape_name': 'String',
                        'type': 'string',
                        'documentation': '\n    <p>The URL for the created SQS queue.</p>\n  ',
                    },
                },
            }
        ),
        # FIXME: More here to fully exercise things.
    ]

class IntrospectionTestCase(unittest.TestCase):
    def setUp(self):
        super(IntrospectionTestCase, self).setUp()
        self.service = TestService()
        self.session = FakeSession(self.service)
        self.introspection = Introspection(self.session)

    def test_parse_param(self):
        param = self.service.operations[0].params[0]
        param_data = self.introspection.parse_param(param)
        self.assertEqual(param_data['var_name'], 'queue_name')
        self.assertEqual(param_data['api_name'], 'QueueName')
        self.assertEqual(
            param_data['docs'],
            'The name for the queue to be created.'
        )
        self.assertEqual(param_data['required'], True)
        self.assertEqual(param_data['type'], 'string')

    def test_parse_params(self):
        params_data = self.introspection.parse_params(
            self.service.operations[0].params
        )
        self.assertEqual(len(params_data), 2)
        self.assertEqual(params_data[0]['var_name'], 'queue_name')
        self.assertEqual(params_data[0]['api_name'], 'QueueName')
        self.assertEqual(params_data[0]['required'], True)
        self.assertEqual(params_data[0]['type'], 'string')
        self.assertEqual(
            params_data[0]['docs'],
            'The name for the queue to be created.'
        )
        self.assertEqual(params_data[1]['var_name'], 'attributes')
        self.assertEqual(params_data[1]['api_name'], 'Attributes')
        self.assertEqual(params_data[1]['required'], False)
        self.assertEqual(params_data[1]['type'], 'map')
        self.assertEqual(params_data[1]['docs'], '')

    def test_get_endpoint(self):
        endpoint = self.introspection.get_endpoint(self.service)
        self.assertEqual(endpoint.region_name, 'us-east-1')

        endpoint = self.introspection.get_endpoint(
            self.service,
            region_name='us-west-2'
        )
        self.assertEqual(endpoint.region_name, 'us-west-2')

    def test_get_operation(self):
        operation = self.introspection.get_operation(
            self.service,
            'CreateQueue'
        )
        self.assertEqual(operation.py_name, 'create_queue')

    def test_introspect_operation(self):
        op_data = self.introspection.introspect_operation(
            self.service.operations[0]
        )
        self.assertEqual(sorted(list(op_data.keys())), [
            'api_name',
            'docs',
            'method_name',
            'output',
            'params'
        ])
        self.assertEqual(op_data['api_name'], 'CreateQueue')
        self.assertEqual(op_data['docs'], ' \n\nCreates a queue.\n\n ')
        self.assertEqual(op_data['method_name'], 'create_queue')
        self.assertEqual(len(op_data['params']), 2)
        self.assertEqual(op_data['params'][0]['var_name'], 'queue_name')
        self.assertEqual(op_data['params'][1]['var_name'], 'attributes')
        self.assertEqual(op_data['output']['shape_name'], 'CreateQueueResult')
        self.assertEqual(op_data['output']['type'], 'structure')
        self.assertEqual(sorted(list(op_data['output']['members'].keys())), [
            'QueueUrl'
        ])

    def test_introspect_service(self):
        service_data = self.introspection.introspect_service('test')
        self.assertEqual(list(service_data.keys()), ['create_queue'])

########NEW FILE########
__FILENAME__ = test_loader
import os

from boto3.core.constants import DEFAULT_RESOURCE_JSON_DIR
from boto3.core.exceptions import NoResourceJSONFound
from boto3.core.loader import ResourceJSONLoader

from tests import unittest


class ResourceJSONLoaderTestCase(unittest.TestCase):
    def setUp(self):
        super(ResourceJSONLoaderTestCase, self).setUp()
        self.default_dirs = [
            DEFAULT_RESOURCE_JSON_DIR,
        ]
        self.test_dirs = [
            os.path.join(os.path.dirname(__file__), 'test_data')
        ] + self.default_dirs
        self.default_loader = ResourceJSONLoader(self.default_dirs)
        self.test_loader = ResourceJSONLoader(self.test_dirs)

    def test_init(self):
        self.assertEqual(self.default_loader.data_dirs, self.default_dirs)
        self.assertEqual(self.default_loader._loaded_data, {})
        self.assertEqual(self.test_loader.data_dirs, self.test_dirs)
        self.assertEqual(self.test_loader._loaded_data, {})

    def test_get_available_options(self):
        opts = self.test_loader.get_available_options('test')
        self.assertTrue('2013-11-27' in opts)
        self.assertTrue(
            'test_data/test-2013-11-27.json' in opts['2013-11-27'][0]
        )

        opts = self.test_loader.get_available_options('s3')
        self.assertTrue('2006-03-01' in opts)
        self.assertTrue(
            'data/aws/resources/s3-2006-03-01.json' in opts['2006-03-01'][0]
        )

    def test_get_best_match(self):
        options = {
            '2013-11-27': [
                '~/.boto-overrides/s3-2013-11-27.json',
                '/path/to/boto3/data/aws/resources/s3-2013-11-27.json',
            ],
            '2010-10-06': [
                '/path/to/boto3/data/aws/resources/s3-2010-10-06.json',
            ],
            '2007-09-15': [
                '~/.boto-overrides/s3-2007-09-15.json',
            ],
        }

        # Latest.
        self.assertEqual(
            self.test_loader.get_best_match(options, 'test'),
            ('~/.boto-overrides/s3-2013-11-27.json', '2013-11-27')
        )
        # Exact match.
        self.assertEqual(
            self.test_loader.get_best_match(
                options,
                'test',
                api_version='2010-10-06'
            ),
            (
                '/path/to/boto3/data/aws/resources/s3-2010-10-06.json',
                '2010-10-06'
            )
        )
        # Best compatible.
        self.assertEqual(
            self.test_loader.get_best_match(
                options,
                'test',
                api_version='2008-02-02'
            ),
            ('~/.boto-overrides/s3-2007-09-15.json', '2007-09-15')
        )

        # No match.
        with self.assertRaises(NoResourceJSONFound):
            self.test_loader.get_best_match(
                options,
                'test',
                api_version='2001-01-01'
            )

    def test_load(self):
        self.assertEqual(len(self.test_loader._loaded_data), 0)

        data = self.test_loader.load('test', cached=False)
        self.assertEqual(len(data.keys()), 4)
        self.assertTrue('api_version' in data)

        # Make sure it didn't get cached here.
        self.assertEqual(len(self.test_loader._loaded_data), 0)

    def test_load_fallback(self):
        # This won't be found in the ``test_data`` directory but is in the
        # main code. Make sure we eventually find it.
        data = self.test_loader.load('elastictranscoder', cached=False)
        self.assertEqual(len(data.keys()), 4)
        self.assertTrue('api_version' in data)

    def test_load_caching(self):
        self.assertEqual(len(self.test_loader._loaded_data), 0)

        # Note the change of calling format here (vs. above).
        data = self.test_loader.load('test')
        self.assertEqual(len(data.keys()), 4)
        self.assertTrue('api_version' in data)

        # Make sure it **DID** get cached.
        self.assertEqual(len(self.test_loader._loaded_data), 1)
        self.assertTrue('test' in self.test_loader._loaded_data)

    def test_load_cached(self):
        # Fake some data into the cache.
        self.test_loader._loaded_data['nonexistent'] = {
            'test': {
                'this is a': 'test',
                'abc': 123,
            },
        }

        # This wouldn't be loadable otherwise (not on the filesystem).
        # However, since we faked it into the cache...
        data = self.test_loader.load('nonexistent', api_version='test')
        self.assertEqual(data['this is a'], 'test')

    def test_contains(self):
        self.test_loader._loaded_data['foo'] = 'bar'
        self.assertEqual(len(self.test_loader._loaded_data), 1)

        self.assertTrue('foo' in self.test_loader)
        self.assertFalse('nopenopenope' in self.test_loader)

    def test_not_found(self):
        with self.assertRaises(NoResourceJSONFound):
            self.test_loader.load('nopenopenope')

########NEW FILE########
__FILENAME__ = test_resources
import os

from boto3.core.constants import DEFAULT_DOCSTRING
from boto3.core.exceptions import APIVersionMismatchError, NoSuchMethod
from boto3.core.exceptions import NoRelation
from boto3.core.resources import ResourceJSONLoader, ResourceDetails
from boto3.core.resources import Resource, ResourceFactory
from boto3.core.session import Session

from tests import unittest
from tests.unit.fakes import FakeParam, FakeOperation, FakeService, FakeSession


class TestCoreService(FakeService):
    api_version = '2013-08-23'
    operations = [
        FakeOperation(
            'CreateQueue',
            " <p>Creates a queue.</p>\n ",
            params=[
                FakeParam('QueueName', required=True, ptype='string'),
                FakeParam('Attributes', required=False, ptype='map'),
            ],
            output={
                'shape_name': 'CreateQueueResult',
                'type': 'structure',
                'members': {
                    'QueueUrl': {
                        'shape_name': 'String',
                        'type': 'string',
                        'documentation': '\n    <p>The URL for the created SQS queue.</p>\n  ',
                    },
                },
            },
            result=(None, {
                'QueueUrl': 'http://example.com',
            })
        ),
        FakeOperation(
            'SendMessage',
            " <p>Sends a message to a queue.</p>\n ",
            params=[
                FakeParam('QueueName', required=True, ptype='string'),
                FakeParam('MessageBody', required=True, ptype='string'),
                FakeParam('MessageType', required=False, ptype='string'),
            ],
            output=True,
            result=(None, True)
        ),
        FakeOperation(
            'ReceiveMessage',
            " something something something ",
            params=[
                FakeParam('QueueUrl', required=True, ptype='string'),
                FakeParam('AttributeNames', required=False, ptype='list'),
                FakeParam('MaxNumberOfMessages', required=False, ptype='integer'),
                FakeParam('VisibilityTimeout', required=False, ptype='integer'),
                FakeParam('WaitTimeSeconds', required=False, ptype='integer'),
            ],
            output={
                'shape_name': 'ReceiveMessageResult',
                'type': 'structure',
                'members': {
                    'Messages': {
                        'shape_name': 'MessageList',
                        'type': 'list',
                        'members': {
                            'shape_name': 'Message',
                            'type': 'structure',
                            'members': {
                                'MessageId': {
                                    'shape_name': 'String',
                                    'type': 'string',
                                    'documentation': None
                                },
                                'ReceiptHandle': {
                                    'shape_name': 'String',
                                    'type': 'string',
                                    'documentation': None
                                },
                                'MD5OfBody': {
                                    'shape_name': 'String',
                                    'type': 'string',
                                    'documentation': None
                                },
                                'Body': {
                                    'shape_name': 'String',
                                    'type': 'string',
                                    'documentation': None
                                },
                                'Attributes': {
                                    'shape_name': 'AttributeMap',
                                    'type': 'map',
                                    'keys': {
                                        'shape_name': 'QueueAttributeName',
                                        'type': 'string',
                                        'enum': [
                                            'Policy',
                                            'VisibilityTimeout',
                                            'MaximumMessageSize',
                                            'MessageRetentionPeriod',
                                            'ApproximateNumberOfMessages',
                                            'ApproximateNumberOfMessagesNotVisible',
                                            'CreatedTimestamp',
                                            'LastModifiedTimestamp',
                                            'QueueArn',
                                            'ApproximateNumberOfMessagesDelayed',
                                            'DelaySeconds',
                                            'ReceiveMessageWaitTimeSeconds'
                                        ],
                                        'documentation': '\n    <p>The name of a queue attribute.</p>\n  ',
                                        'xmlname': 'Name'
                                    },
                                    'members': {
                                        'shape_name': 'String',
                                        'type': 'string',
                                        'documentation': '\n    <p>The value of a queue attribute.</p>\n  ',
                                        'xmlname': 'Value'
                                    },
                                    'flattened': True,
                                    'xmlname': 'Attribute',
                                    'documentation': None,
                                },
                            },
                            'documentation': None,
                            'xmlname': 'Message'
                        },
                        'flattened': True,
                        'documentation': '\n    <p>A list of messages.</p>\n  '
                    }
                },
                'documentation': None
            },
            result=(None, {
                'Messages': [
                    {
                        'MessageId': 'msg-12345',
                        'ReceiptHandle': 'hndl-12345',
                        'MD5OfBody': '6cd3556deb0da54bca060b4c39479839',
                        'Body': 'Hello, world!',
                        'Attributes': {
                            'QueueArn': 'arn:aws:example:example:sqs:something',
                            'ApproximateNumberOfMessagesDelayed': '2',
                            'DelaySeconds': '10',
                            'CreatedTimestamp': '2013-10-17T21:52:46Z',
                            'LastModifiedTimestamp': '2013-10-17T21:52:46Z',
                        },
                    },
                    {
                        'MessageId': 'msg-12346',
                        'ReceiptHandle': 'hndl-12346',
                        'MD5OfBody': '6cd355',
                        'Body': 'Another message!',
                        'Attributes': {},
                    },
                ]
            })
        ),
        FakeOperation(
            'DeleteQueue',
            " <p>Deletes a queue.</p>\n ",
            params=[
                FakeParam('QueueName', required=True, ptype='string'),
            ],
            output=True,
            result=(None, True)
        ),
    ]


class ResourceDetailsTestCase(unittest.TestCase):
    def setUp(self):
        super(ResourceDetailsTestCase, self).setUp()
        self.test_dirs = [
            os.path.join(os.path.dirname(__file__), 'test_data')
        ]
        self.test_loader = ResourceJSONLoader(self.test_dirs)
        self.session = Session(FakeSession(TestCoreService()))

        self.rd = ResourceDetails(
            self.session,
            'test',
            'Preset',
            loader=self.test_loader
        )

    def test_init(self):
        self.assertEqual(self.rd.session, self.session)
        self.assertEqual(self.rd.service_name, 'test')
        self.assertEqual(self.rd.loader, self.test_loader)
        self.assertEqual(self.rd._loaded_data, None)
        self.assertEqual(self.rd._api_version, None)

    def test_service_data_uncached(self):
        self.assertEqual(self.rd._loaded_data, None)

        data = self.rd.service_data
        self.assertEqual(len(data.keys()), 4)
        self.assertTrue('api_version' in self.rd._loaded_data)

    def test_resource_data_uncached(self):
        self.assertEqual(self.rd._loaded_data, None)

        data = self.rd.resource_data
        self.assertEqual(len(data.keys()), 4)
        self.assertTrue('identifiers' in data)
        self.assertTrue('operations' in data)
        self.assertTrue('api_version' in self.rd._loaded_data)

    def test_api_version_uncached(self):
        self.assertEqual(self.rd._api_version, None)

        av = self.rd.api_version
        self.assertEqual(av, '2013-11-27')
        self.assertEqual(self.rd._api_version, '2013-11-27')

    def test_identifiers(self):
        self.assertEqual(self.rd.identifiers, [
            {
                'api_name': '$shape_name.Id',
                'var_name': 'id',
            }
        ])

    def test_result_key_for(self):
        # Non-existent
        self.assertEqual(self.rd.result_key_for('notthere'), None)

        # Now with actual data.
        self.assertEqual(self.rd.result_key_for('get'), 'Preset')

    def test_relations(self):
        # No relations.
        alt_rd = ResourceDetails(
            self.session,
            'test',
            'Job',
            loader=self.test_loader
        )
        self.assertEqual(alt_rd.relations, {})

        # With relations.
        self.assertEqual(self.rd.relations, {
            'pipelines': {
                'class': 'PipelineCollection',
                'class_type': 'collection',
                'rel_type': 'M-M',
                'required': False
            }
        })

    def test_cached(self):
        # Fake in data.
        self.rd._loaded_data = {
            'api_version': '20XX-MM-II',
            'hello': 'world',
        }

        data = self.rd.service_data
        av = self.rd.api_version
        self.assertTrue('hello' in data)
        self.assertTrue('20XX-MM-II' in av)


class FakeConn(object):
    def __init__(self, *args, **kwargs):
        super(FakeConn, self).__init__()

    def delete_pipeline(self, *args, **kwargs):
        return {
            'RequestId': '1234-1234-1234-1234',
            'Id': '1872baf45',
            'Title': 'A pipe',
        }


class OopsConn(object):
    # Used to demonstrate when no API methods are available.
    def __init__(self, *args, **kwargs):
        super(OopsConn, self).__init__()


class PipeResource(Resource):
    def update_params(self, conn_method_name, params):
        params['global'] = True
        return super(PipeResource, self).update_params(conn_method_name, params)

    def update_params_delete(self, params):
        params.update(self.get_identifiers())
        return params

    def post_process(self, conn_method_name, result):
        result = result.copy()
        self.identifier = result.pop('Id', None)
        return result

    def post_process_delete(self, result):
        self.deleted = True
        return result


class FakeJobCollection(object):
    def __init__(self, connection, **kwargs):
        self._data = kwargs

    def get_identifiers(self):
        return self._data


class ResourceTestCase(unittest.TestCase):
    def setUp(self):
        super(ResourceTestCase, self).setUp()
        self.session = Session(FakeSession(TestCoreService()))
        self.fake_details = ResourceDetails(self.session, 'test', 'Pipe')
        self.fake_details._loaded_data = {
            'api_version': 'something',
            'resources': {
                'Pipe': {
                    'identifiers': [
                        {
                            'var_name': 'id',
                            'api_name': 'Id',
                        },
                    ],
                    'operations': {
                        'delete': {
                            'api_name': 'DeletePipe'
                        }
                    },
                    'relations': {
                        'jobs': {
                            'class': 'JobCollection',
                            'class_type': 'collection',
                            'rel_type': '1-M',
                            'required': False
                        },
                        'unknown': {
                            'class': 'Something',
                            'class_type': 'unknown',
                        }
                    }
                }
            }
        }
        self.fake_conn = FakeConn()
        PipeResource._details = self.fake_details
        self.resource = PipeResource(
            connection=self.fake_conn,
            id='1872baf45'
        )

    def tearDown(self):
        del PipeResource._details
        super(ResourceTestCase, self).tearDown()

    def test_get_identifiers(self):
        self.assertEqual(self.resource.get_identifiers(), {'id': '1872baf45'})

    def test_set_identifiers(self):
        self.assertEqual(self.resource._data, {
            'id': '1872baf45',
        })

        # Only sets things found in the identifiers, not random data.
        self.resource.set_identifiers({'id': 'hello!', 'bucket': 'something'})
        self.assertEqual(self.resource._data, {
            'id': 'hello!'
        })

    def test_full_update_params(self):
        params = {
            'notify': True,
        }
        prepped = self.resource.full_update_params('delete', params)
        self.assertEqual(prepped, {
            'global': True,
            'id': '1872baf45',
            'notify': True,
        })

        params['yeah'] = 'yeahyeah'
        prepped = self.resource.full_update_params('get', params)
        self.assertEqual(prepped, {
            'global': True,
            'id': '1872baf45',
            'notify': True,
            'yeah': 'yeahyeah',
        })

    def test_full_post_process(self):
        results = {
            'Id': '1872baf45',
            'Title': 'A pipe',
        }
        processed = self.resource.full_post_process('delete', results)
        self.assertEqual(processed, {
            'Title': 'A pipe'
        })
        self.assertEqual(self.resource.deleted, True)

    def test_full_post_process_get(self):
        # Without a result key.
        results = {
            'Id': '1872baf45',
            'Title': 'A pipe',
        }
        processed = self.resource.full_post_process('get', results)
        self.assertEqual(processed, {
            'Title': 'A pipe'
        })
        # Note that what get's assigned has been snake_cased.
        self.assertEqual(self.resource.id, '1872baf45')
        self.assertEqual(self.resource.title, 'A pipe')

    def test_full_post_process_get_result_key(self):
        orig_fake_data = self.fake_details._loaded_data
        self.addCleanup(
            setattr, self.fake_details, '_loaded_data', orig_fake_data
        )

        result_key_fake_data = orig_fake_data.copy()
        result_key_fake_data['resources']['Pipe']['operations']['get'] = {
            'api_name': 'GetPipe',
            'result_key': 'Pipe',
        }

        resource = PipeResource(
            connection=self.fake_conn,
            id='92aa36e5b'
        )

        # With a result key.
        self.fake_details._loaded_data = result_key_fake_data
        results = {
            'Pipe': {
                'Id': '92aa36e5b',
                'Title': 'Another pipe',
            }
        }
        self.assertEqual(resource._data, {'id': '92aa36e5b'})
        processed = resource.full_post_process('get', results)
        self.assertEqual(processed, {
            'Pipe': {
                'Id': '92aa36e5b',
                'Title': 'Another pipe'
            }
        })
        # Despite being nested in the response, the right data is assigned.
        self.assertEqual(resource.id, '92aa36e5b')
        self.assertEqual(resource.title, 'Another pipe')

    def test_build_relation(self):
        # For testing purposes.
        self.session.cache.services['test'] = {
            'collections': {
                'JobCollection': {
                    'default': FakeJobCollection
                }
            }
        }

        # With an unknown relation name.
        with self.assertRaises(NoRelation) as cm:
            self.resource.build_relation('nopenopenope')

        self.assertTrue('No such relation' in str(cm.exception))

        # With an unknown relation type.
        with self.assertRaises(NoRelation) as cm:
            self.resource.build_relation('unknown')

        self.assertTrue('Unknown class' in str(cm.exception))

        # Introspected from the data.
        rel = self.resource.build_relation('jobs')
        self.assertTrue(isinstance(rel, FakeJobCollection))
        # Should have inherited some identifiers from the the parent
        # ``self.resource``...
        self.assertEqual(rel.get_identifiers(), {
            'id': '1872baf45',
        })

        # If given an explicit class, build with that instead.
        class Whatever(object):
            def __init__(self, *args, **kwargs):
                self._data = kwargs

        rel = self.resource.build_relation('jobs', klass=Whatever)
        self.assertTrue(isinstance(rel, Whatever))


class ResourceFactoryTestCase(unittest.TestCase):
    def setUp(self):
        super(ResourceFactoryTestCase, self).setUp()
        self.session = Session(FakeSession(TestCoreService()))
        self.test_dirs = [
            os.path.join(os.path.dirname(__file__), 'test_data')
        ]
        self.test_loader = ResourceJSONLoader(self.test_dirs)
        self.rd = ResourceDetails(
            self.session,
            'test',
            'Pipeline',
            loader=self.test_loader
        )
        self.rf = ResourceFactory(session=self.session, loader=self.test_loader)

    def test_init(self):
        self.assertEqual(self.rf.session, self.session)
        self.assertTrue(isinstance(self.rf.loader, ResourceJSONLoader))
        self.assertEqual(self.rf.base_resource_class, Resource)
        self.assertEqual(self.rf.details_class, ResourceDetails)

        # Test overrides (invalid for actual usage).
        import boto3
        rf = ResourceFactory(
            loader=False,
            base_resource_class=PipeResource,
            details_class=True
        )
        self.assertEqual(rf.session, boto3.session)
        self.assertEqual(rf.loader, False)
        self.assertEqual(rf.base_resource_class, PipeResource)
        self.assertEqual(rf.details_class, True)

    def test_build_class_name(self):
        self.assertEqual(
            self.rf._build_class_name('Pipeline'),
            'Pipeline'
        )
        self.assertEqual(
            self.rf._build_class_name('TestName'),
            'TestName'
        )

    def test_build_methods(self):
        attrs = self.rf._build_methods(self.rd)
        self.assertEqual(len(attrs), 5)
        self.assertTrue('delete' in attrs)
        self.assertTrue('get' in attrs)
        self.assertTrue('update' in attrs)

    def test_create_operation_method(self):
        class StubbyResource(Resource):
            pass

        op_method = self.rf._create_operation_method('delete', {
            "api_name": "DeletePipeline"
        })
        self.assertEqual(op_method.__name__, 'delete')
        self.assertEqual(op_method.__doc__, DEFAULT_DOCSTRING)

        # Assign it & call it.
        StubbyResource._details = self.rd
        StubbyResource.delete = op_method
        sr = StubbyResource(connection=FakeConn())
        self.assertEqual(sr.delete(), {
            'Id': '1872baf45',
            'RequestId': '1234-1234-1234-1234',
            'Title': 'A pipe'
        })

        # Make sure an exception is raised when the underlying connection
        # doesn't have an analogous method.
        sr = StubbyResource(connection=OopsConn())

        with self.assertRaises(NoSuchMethod):
            fake_pipe = sr.delete()

    def test_construct_for(self):
        res_class = self.rf.construct_for('test', 'Pipeline')

########NEW FILE########
__FILENAME__ = test_session
from botocore.service import Service as BotocoreService

from boto3.core.session import Session

from tests import unittest


class FakeConnection(object): pass


class SessionTestCase(unittest.TestCase):
    def setUp(self):
        super(SessionTestCase, self).setUp()
        self.session = Session()

    def test_get_core_service(self):
        client = self.session.get_core_service('sqs')
        self.assertTrue(isinstance(client, BotocoreService))

    def test_get_connection_exists(self):
        self.assertEqual(len(self.session.cache), 0)
        # Put in a sentinel.
        self.session.cache.set_connection('test', FakeConnection)
        self.assertEqual(len(self.session.cache), 1)

        client = self.session.get_connection('test')
        self.assertTrue(client is FakeConnection)

    def test_get_connection_does_not_exist(self):
        self.assertEqual(len(self.session.cache), 0)
        client = self.session.get_connection('sqs')
        self.assertEqual(client.__name__, 'SqsConnection')
        self.assertEqual(len(self.session.cache), 1)

    def test_get_resource_exists(self):
        self.assertEqual(len(self.session.cache), 0)
        # Put in a sentinel.
        self.session.cache.set_resource('test', 'Test', FakeConnection)
        self.assertEqual(len(self.session.cache), 1)

        # Ugly, but needed due to our faking connections above.
        Test = self.session.get_resource('test', 'Test', base_class=object)
        self.assertTrue(Test is FakeConnection)

    def test_get_resource_does_not_exist(self):
        self.assertEqual(len(self.session.cache), 0)
        Queue = self.session.get_resource('sqs', 'Queue')
        self.assertEqual(Queue.__name__, 'Queue')
        self.assertEqual(len(self.session.cache), 1)

    def test_get_collection_exists(self):
        self.assertEqual(len(self.session.cache), 0)
        # Put in a sentinel.
        self.session.cache.set_collection('test', 'Test', FakeConnection)
        self.assertEqual(len(self.session.cache), 1)

        # Ugly, but needed due to our faking connections above.
        TestCollection = self.session.get_collection(
            'test',
            'Test',
            base_class=object
        )
        self.assertTrue(TestCollection is FakeConnection)

    def test_get_collection_does_not_exist(self):
        self.assertEqual(len(self.session.cache), 0)
        QueueCollection = self.session.get_collection('sqs', 'QueueCollection')
        self.assertEqual(QueueCollection.__name__, 'QueueCollection')
        self.assertEqual(len(self.session.cache), 1)

    def test_connect_to_region(self):
        client = self.session.connect_to('sqs', region_name='us-west-2')
        self.assertEqual(client.__class__.__name__, 'SqsConnection')
        self.assertEqual(client.region_name, 'us-west-2')


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = fakes
from botocore import xform_name


class FakeParam(object):
    def __init__(self, name, required=False, ptype='string',
                 documentation=None):
        self.name = name
        self.py_name = xform_name(name)
        self.required = required
        self.type = ptype
        self.documentation = documentation


class FakeOperation(object):
    def __init__(self, name, docs='', params=None, output=None, result=None):
        self.name = name
        self.py_name = xform_name(name)
        self.documentation = docs
        self.params = params
        self.output = output
        self.result = result

        if self.params is None:
            self.params = []

        if self.params is None:
            self.params = {}

    def call(self, endpoint, **kwargs):
        return self.result


class FakeService(object):
    operations = []
    api_version = 'fake'

    def __init__(self, endpoint=None):
        self.endpoint = endpoint

        if self.endpoint is None:
            self.endpoint = FakeEndpoint()

    def get_endpoint(self, region_name=None):
        if region_name:
            self.endpoint.region_name = region_name

        return self.endpoint

    def get_operation(self, operation_name):
        for op in self.operations:
            if op.name == operation_name:
                return op

        return None


class FakeEndpoint(object):
    def __init__(self, region_name='us-west-1'):
        self.region_name = region_name


class FakeSession(object):
    def __init__(self, service):
        self.service = service

    def get_service(self, service_name):
        return self.service

########NEW FILE########
__FILENAME__ = test_import_utils
from boto3.core.exceptions import IncorrectImportPath
from boto3.core.session import Session
from boto3.utils.import_utils import import_class

from tests import unittest


class ImportUtilsTestCase(unittest.TestCase):
    def test_import_class_empty_string(self):
        with self.assertRaises(IncorrectImportPath) as cm:
            klass = import_class('')

        self.assertTrue('Invalid Python' in str(cm.exception))

    def test_import_class_invalid_path(self):
        with self.assertRaises(IncorrectImportPath) as cm:
            klass = import_class('boto3.nosuchmodule.Nope')

        self.assertTrue('Could not import' in str(cm.exception))

    def test_import_class_invalid_class(self):
        with self.assertRaises(IncorrectImportPath) as cm:
            klass = import_class('boto3.core.session.NopeSession')

        self.assertTrue('could not find' in str(cm.exception))

    def test_import_class(self):
        klass = import_class('boto3.core.session.Session')
        self.assertEqual(klass, Session)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mangle
from boto3.utils.mangle import to_snake_case, to_camel_case

from tests import unittest


class MangleTestCase(unittest.TestCase):
    def test_to_snake_case(self):
        self.assertEqual(to_snake_case('Create'), 'create')
        self.assertEqual(to_snake_case('CreateQueue'), 'create_queue')
        self.assertEqual(to_snake_case('ThisIsReallyLong'), 'this_is_really_long')
        self.assertEqual(to_snake_case('createQueue'), 'create_queue')

    def test_to_camel_case(self):
        self.assertEqual(to_camel_case('create'), 'Create')
        self.assertEqual(to_camel_case('create_queue'), 'CreateQueue')
        self.assertEqual(to_camel_case('this_is_really_long'), 'ThisIsReallyLong')
        self.assertEqual(to_camel_case('Terrible_Snake_Case'), 'TerribleSnakeCase')


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
